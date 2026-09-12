"""curses を用いたCLI描画・キー入力 (SPEC.md ui_curses.py)。

ロジックは Game クラスに委譲し、本モジュールは描画と入力受付のみを行う。

注意 (SPEC.md NFR-5): 画面へ描画する文字列には日本語を使用してよい。ただし
windows-curses は全角文字を含む文字列を addstr に渡すとカーソルを1桁しか進めず、
全角グリフの右半分に次の文字が重なって表示される既知の不具合がある。これを避けるため、
日本語を含むテキストは _draw_text() 経由で描画し、各文字の表示幅
(unicodedata.east_asian_width: 全角=2桁 / 半角=1桁) を明示計算して、確定した桁位置へ
1文字ずつ描画する。盤面の罫線・セル表現などレイアウトの基準となる部分は ASCII のままとする。

注意 (SPEC.md FR-15, NFR-10): ブロックは輪郭(`[]`)ではなく背景色で塗りつぶした
「ソリッド表示」で描画し、盤面の枠線・タイトル・状態メッセージにも標準8色の範囲で
アクセントカラーを付ける(_init_colors() の UI_ACCENT_PAIRS を参照)。色非対応端末
(`curses.has_colors()` が `False`)では、ブロックは従来通り `[]` の輪郭表示、
枠線・見出し・状態メッセージは無配色のままフォールバックする。

注意 (SPEC.md FR-16, NFR-11): ライン消去エフェクトの点滅は `curses.A_REVERSE`
(反転表示)で表現する。これは色を使わない標準属性のため、色対応・非対応端末の
どちらでも同じロジックで動作する。点滅のタイミング(表示フェーズかどうか)は
`Game.clear_effect_blink_on` が計算し、本モジュールはそれを見て描画するだけにする。
"""
from __future__ import annotations

import curses
import locale
import sys
import time
import unicodedata

from .battle import BattleGame, PLAYER_1, PLAYER_2
from .board import GARBAGE_COLOR
from .game import Game
from .game_loop import FixedTimestepLoop, FrameLimiter
from .tetromino import KIND_TO_COLOR

CELL = "[]"  # 1マスを表す2文字(等幅で正方形に近い見た目にする)
EMPTY = "  "

# ゲームループの目標フレームレート (SPEC.md NFR-8)。
# 描画・入力処理の頻度はこの値で制御し、ゲーム進行(重力tick)の頻度とは分離する。
TARGET_FPS = 50.0

# ミノの色ID(tetromino.KIND_TO_COLOR、1〜7)から curses の色定数への対応 (SPEC.md FR-14)。
# board.grid / Piece.color() が返す色IDをそのまま curses.color_pair() の番号として使う。
# 標準8色にはオレンジが無いため、Lミノは代替として白を割り当てる。
# FR-15により、この色は文字色ではなく「背景色」として使う(ブロックを塗りつぶし表示にする)。
COLOR_ID_TO_CURSES_COLOR = {
    KIND_TO_COLOR["I"]: curses.COLOR_CYAN,
    KIND_TO_COLOR["O"]: curses.COLOR_YELLOW,
    KIND_TO_COLOR["T"]: curses.COLOR_MAGENTA,
    KIND_TO_COLOR["S"]: curses.COLOR_GREEN,
    KIND_TO_COLOR["Z"]: curses.COLOR_RED,
    KIND_TO_COLOR["J"]: curses.COLOR_BLUE,
    KIND_TO_COLOR["L"]: curses.COLOR_WHITE,
}

# UI要素(枠線・タイトル・状態メッセージ)用のアクセントカラー (SPEC.md FR-15)。
# ミノの色ID(1〜7)と重ならないペア番号を割り当てる。値は (pair_id, 前景色) のタプルで、
# 背景は盤面ブロックと違い黒のまま(文字色のみを変える)。
UI_ACCENT_PAIRS = {
    "border": (8, curses.COLOR_CYAN),
    "title": (9, curses.COLOR_MAGENTA),
    "paused": (10, curses.COLOR_YELLOW),
    "game_over": (11, curses.COLOR_RED),
}

# お邪魔行(SPEC.md FR-21)用のcursesカラーペアID。標準8色は既に7ミノ+UI_ACCENT_PAIRSで
# 使い切っているため(NFR-10)、新しい色は割り当てず、Lミノと同じ白背景を流用したうえで
# curses.A_DIM 属性を重ねて通常ブロックと区別する(2章 相殺・お邪魔行、壁打ちログ参照)。
GARBAGE_PAIR_ID = 12

# 2人対戦モードの第2プレイヤー用キー操作ヘルプ(SPEC.md 8章, FR-17, NFR-16)。
BATTLE_KEY_BINDINGS_HELP_P1 = "P1 矢印:移動 上/X:右回転 Z:左回転 Sp:ハードドロップ"
BATTLE_KEY_BINDINGS_HELP_P2 = "P2 A/D:移動 W:右回転 E:左回転 F:ハードドロップ"
BATTLE_COMMON_HELP = "P:一時停止(両者) Q:終了"

# 第2プレイヤーのキー割り当て (SPEC.md 8章, NFR-16)。第1プレイヤー・共通操作
# (P一時停止, Q終了)のいずれとも重複しない。
P2_KEYMAP = {
    "left": (ord("a"), ord("A")),
    "right": (ord("d"), ord("D")),
    "soft_drop": (ord("s"), ord("S")),
    "rotate_cw": (ord("w"), ord("W")),
    "rotate_ccw": (ord("e"), ord("E")),
    "hard_drop": (ord("f"), ord("F")),
}

# 画面に表示する操作ヘルプ。全角文字を含むため _draw_text() 経由で描画する (NFR-5)。
KEY_BINDINGS_HELP = (
    "矢印キー:移動  上/X:右回転  Z:左回転  "
    "スペース:ハードドロップ  P:一時停止  Q:終了"
)


def _char_width(ch: str) -> int:
    """端末上での表示桁数を返す。全角(W)・全角互換(F)は2、それ以外は1。"""
    return 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1


def _draw_text(
    stdscr,
    y: int,
    x: int,
    text: str,
    max_x: int | None = None,
    attr: int = curses.A_NORMAL,
) -> None:
    """表示幅を明示計算し、1文字ずつ確定した桁位置へ描画する (SPEC.md NFR-5)。

    windows-curses が全角文字でカーソルを1桁しか進めず文字が重なる不具合への対策。
    max_x を与えると、その桁を超える文字は描画しない(画面幅での打ち切り)。
    attr で文字色・太字等の表示属性を指定できる (SPEC.md FR-15)。省略時は無配色。
    """
    cur = x
    for ch in text:
        w = _char_width(ch)
        if max_x is not None and cur + w > max_x:
            break
        try:
            stdscr.addstr(y, cur, ch, attr)
        except curses.error:
            # 画面端など描画不能なセルは無視して継続する。
            pass
        cur += w


def _init_colors() -> bool:
    """cursesの色表示を初期化する (SPEC.md FR-14, FR-15, NFR-9, NFR-10)。

    端末が色に対応していない場合は何もせず False を返す。呼び出し側はこれを見て
    モノクロ描画にフォールバックし、色非対応端末でもクラッシュしないようにする。
    """
    if not curses.has_colors():
        return False
    try:
        curses.start_color()
        # FR-15: ブロックは塗りつぶし表示にするため、ミノの色を文字色ではなく
        # 背景色に割り当てる(文字色は黒)。
        for color_id, bg in COLOR_ID_TO_CURSES_COLOR.items():
            curses.init_pair(color_id, curses.COLOR_BLACK, bg)
        # FR-15: 枠線・タイトル・状態メッセージ用のアクセントカラー(文字色のみ、背景は黒)。
        for pair_id, fg in UI_ACCENT_PAIRS.values():
            curses.init_pair(pair_id, fg, curses.COLOR_BLACK)
        # FR-21: お邪魔行はLミノと同じ白背景を流用する(区別はA_DIM属性で行う)。
        curses.init_pair(GARBAGE_PAIR_ID, curses.COLOR_BLACK, curses.COLOR_WHITE)
    except curses.error:
        return False
    return True


def _draw_board(
    stdscr, game: Game, origin_y: int, origin_x: int, colors_enabled: bool
) -> None:
    """盤面を描画する (SPEC.md FR-14, FR-15, FR-16)。

    色対応端末では、ブロックは輪郭(`[]`)ではなく背景色で塗りつぶした「ソリッド表示」で
    描画し、枠線にはアクセントカラーを付ける。色非対応端末では、ブロックは従来通り `[]`
    の輪郭表示、枠線は無配色のままとする (NFR-10)。ライン消去エフェクト表示中
    (`game.clearing_rows`)は、点滅の表示フェーズ(`game.clear_effect_blink_on`)である
    間、対象行を `curses.A_REVERSE` で反転表示する (NFR-11)。
    """
    board = game.board
    if game.game_over or game.clearing_rows:
        # ゲームオーバー時、およびライン消去エフェクト表示中(FR-16)は、既に
        # board.grid に固定済みの内容をそのまま描画すればよいため current は重ねない。
        piece_cells: set[tuple[int, int]] = set()
        piece_color = 0
    else:
        piece_cells = set(game.current.cells())
        piece_color = game.current.color()

    clearing_rows = set(game.clearing_rows)
    blink_on = game.clear_effect_blink_on

    if colors_enabled:
        border_pair_id, _ = UI_ACCENT_PAIRS["border"]
        border_attr = curses.color_pair(border_pair_id) | curses.A_BOLD
    else:
        border_attr = curses.A_NORMAL

    for r in range(board.height):
        stdscr.addstr(origin_y + r, origin_x, "|", border_attr)
        cur_x = origin_x + 1
        row_is_flashing = r in clearing_rows and blink_on
        for c in range(board.width):
            color_id = piece_color if (r, c) in piece_cells else board.grid[r][c]
            if color_id:
                if colors_enabled:
                    # FR-21: お邪魔行(GARBAGE_COLOR)は盤面上の色ID(board.grid由来の
                    # 非curses値)なので、そのままcolor_pair番号として使わず、専用の
                    # GARBAGE_PAIR_IDへ変換したうえでA_DIMを重ねて区別する。
                    if color_id == GARBAGE_COLOR:
                        attr = curses.color_pair(GARBAGE_PAIR_ID) | curses.A_DIM
                    else:
                        attr = curses.color_pair(color_id)
                else:
                    attr = curses.A_NORMAL
                if row_is_flashing:
                    # FR-16: 消去対象行の点滅表示フェーズでは反転表示にする。
                    attr |= curses.A_REVERSE
                text = EMPTY if colors_enabled else CELL
                stdscr.addstr(origin_y + r, cur_x, text, attr)
            else:
                stdscr.addstr(origin_y + r, cur_x, EMPTY)
            cur_x += 2
        stdscr.addstr(origin_y + r, cur_x, "|", border_attr)
    stdscr.addstr(
        origin_y + board.height, origin_x, "+" + "--" * board.width + "+", border_attr
    )


def _accent_attr(colors_enabled: bool, name: str) -> int:
    """UI_ACCENT_PAIRS のアクセントカラー(+太字)を返す。色非対応時は無配色 (NFR-10)。"""
    if not colors_enabled:
        return curses.A_NORMAL
    pair_id, _ = UI_ACCENT_PAIRS[name]
    return curses.color_pair(pair_id) | curses.A_BOLD


def _draw_sidebar(
    stdscr,
    game: Game,
    origin_y: int,
    origin_x: int,
    colors_enabled: bool,
    title: str = "テトリス",
    help_text: str | None = KEY_BINDINGS_HELP,
    max_x: int | None = None,
    pending_garbage: int | None = None,
) -> None:
    """サイドバーを描画する (SPEC.md FR-15)。

    タイトル・一時停止/ゲームオーバーの状態メッセージにアクセントカラーを付ける。
    色非対応端末では従来通り無配色のまま描画する (NFR-10)。

    2人対戦モード(SPEC.md FR-17)では、title/help_text/max_x を各プレイヤー用に
    差し替え、pending_garbage(保留お邪魔行数、FR-20)も併せて表示できるようにする。
    1人用モードの呼び出しはデフォルト引数のみで従来通り動作する。
    """
    if max_x is None:
        max_x = curses.COLS - 1
    _draw_text(
        stdscr, origin_y, origin_x, title, max_x=max_x, attr=_accent_attr(colors_enabled, "title")
    )
    _draw_text(stdscr, origin_y + 2, origin_x, f"スコア: {game.score}", max_x=max_x)
    _draw_text(stdscr, origin_y + 3, origin_x, f"レベル: {game.level}", max_x=max_x)
    _draw_text(stdscr, origin_y + 4, origin_x, f"ライン: {game.lines_cleared}", max_x=max_x)
    if pending_garbage is not None:
        _draw_text(
            stdscr, origin_y + 5, origin_x, f"保留お邪魔行: {pending_garbage}", max_x=max_x
        )
    _draw_text(stdscr, origin_y + 6, origin_x, f"ネクスト: {game.next_kind}", max_x=max_x)
    if game.paused:
        _draw_text(
            stdscr,
            origin_y + 8,
            origin_x,
            "-- 一時停止中 --",
            max_x=max_x,
            attr=_accent_attr(colors_enabled, "paused"),
        )
    if game.game_over:
        go_attr = _accent_attr(colors_enabled, "game_over")
        _draw_text(stdscr, origin_y + 8, origin_x, "ゲームオーバー", max_x=max_x, attr=go_attr)
        _draw_text(stdscr, origin_y + 9, origin_x, "Q キーで終了", max_x=max_x, attr=go_attr)
    if help_text:
        _draw_text(stdscr, origin_y + 11, origin_x, help_text, max_x=max_x)


def _handle_key(game: Game, key: int) -> bool:
    """キー入力をGameに反映する。終了要求ならFalseを返す。"""
    if key in (ord("q"), ord("Q")):
        return False
    if game.game_over:
        return True
    if key in (curses.KEY_LEFT,):
        game.move_left()
    elif key in (curses.KEY_RIGHT,):
        game.move_right()
    elif key in (curses.KEY_DOWN,):
        game.soft_drop()
    elif key in (curses.KEY_UP, ord("x"), ord("X")):
        game.rotate_cw()
    elif key in (ord("z"), ord("Z")):
        game.rotate_ccw()
    elif key == ord(" "):
        game.hard_drop()
    elif key in (ord("p"), ord("P")):
        game.toggle_pause()
    return True


def run(stdscr) -> None:
    """メインのゲームループ (SPEC.md NFR-8)。

    毎フレーム「入力処理 -> 固定タイムステップでの更新 -> 描画 -> フレームレート制御」
    の順に明確に分離して実行する。ゲームの進行(重力によるtick)は
    FixedTimestepLoop により実行環境の処理速度に依存せず一定間隔で保証され、
    描画・入力受付の頻度は FrameLimiter によりTARGET_FPSに制御される。
    """
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.keypad(True)
    colors_enabled = _init_colors()

    game = Game()
    timestep = FixedTimestepLoop(update_interval=game.gravity_interval())
    limiter = FrameLimiter(target_fps=TARGET_FPS)
    last_frame = time.monotonic()

    while True:
        frame_start = time.monotonic()
        elapsed = frame_start - last_frame
        last_frame = frame_start

        # 1. 入力処理
        key = stdscr.getch()
        if key != -1:
            if not _handle_key(game, key):
                break

        # 2. 固定タイムステップでの更新(レベルアップ等で変化する重力間隔を反映)
        # ライン消去エフェクト(FR-16)の経過時間は、重力の固定タイムステップとは独立に
        # 実時間(elapsed)でそのまま進める(点滅を滑らかにするため)。
        game.update(elapsed)
        timestep.update_interval = game.gravity_interval()
        for _ in range(timestep.advance(elapsed)):
            game.tick()

        # 3. 描画
        stdscr.erase()
        _draw_board(stdscr, game, origin_y=1, origin_x=1, colors_enabled=colors_enabled)
        _draw_sidebar(
            stdscr,
            game,
            origin_y=1,
            origin_x=2 + game.board.width * 2 + 3,
            colors_enabled=colors_enabled,
        )
        stdscr.refresh()

        # 4. フレームレート制御
        frame_elapsed = time.monotonic() - frame_start
        time.sleep(limiter.sleep_duration(frame_elapsed))


def _handle_p2_key(game: Game, key: int) -> None:
    """第2プレイヤー用のキー入力をGameに反映する (SPEC.md 8章, FR-17, NFR-16)。

    一時停止(P)・終了(Q)は対戦全体の共通操作として run_battle() 側で扱うため、
    ここでは移動・回転・ドロップのみを扱う。
    """
    if game.game_over:
        return
    for action, keys in P2_KEYMAP.items():
        if key not in keys:
            continue
        if action == "left":
            game.move_left()
        elif action == "right":
            game.move_right()
        elif action == "soft_drop":
            game.soft_drop()
        elif action == "rotate_cw":
            game.rotate_cw()
        elif action == "rotate_ccw":
            game.rotate_ccw()
        elif action == "hard_drop":
            game.hard_drop()
        return


def run_battle(stdscr) -> None:
    """2人対戦モードのメインループ (SPEC.md FR-17〜FR-22)。

    盤面を左右に画面分割して同時に描画し、共有キーボードで2人を操作する
    (第1プレイヤー: 矢印キー等、第2プレイヤー: A/D/S/W/E/F、8章)。一時停止(P)・
    終了(Q)は対戦全体に対する共通操作として扱う。ゲーム進行の更新方式は run()
    と同様、固定タイムステップ+フレームレート制御(NFR-8)を各プレイヤーの
    Gameに対して独立に適用する。お邪魔行の攻撃力算出・相殺・盤面反映・勝敗判定
    (FR-19〜FR-22)は BattleGame(battle.py, NFR-14)に委譲し、本関数は描画と
    入力の振り分けのみを行う(NFR-15)。

    盤面2枚を横に並べるため、画面幅の広い端末(目安: 100桁以上)での実行を
    想定する。
    """
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.keypad(True)
    colors_enabled = _init_colors()

    battle = BattleGame()
    game1 = battle.player1
    game2 = battle.player2
    timestep1 = FixedTimestepLoop(update_interval=game1.gravity_interval())
    timestep2 = FixedTimestepLoop(update_interval=game2.gravity_interval())
    limiter = FrameLimiter(target_fps=TARGET_FPS)
    last_frame = time.monotonic()

    board_total_width = game1.board.width * 2 + 2  # 枠(左右2)を含む盤面の桁数
    gap = 3
    sidebar_width = 20
    p1_board_x = 1
    p1_sidebar_x = p1_board_x + board_total_width + gap
    p2_board_x = p1_sidebar_x + sidebar_width + gap
    p2_sidebar_x = p2_board_x + board_total_width + gap

    while True:
        frame_start = time.monotonic()
        elapsed = frame_start - last_frame
        last_frame = frame_start

        # 1. 入力処理(共有キーボード。P/Qは対戦全体への共通操作)
        key = stdscr.getch()
        if key != -1:
            if key in (ord("q"), ord("Q")):
                break
            if key in (ord("p"), ord("P")):
                if not battle.is_over:
                    paused = not game1.paused
                    game1.paused = paused
                    game2.paused = paused
            elif not battle.is_over:
                _handle_key(game1, key)
                _handle_p2_key(game2, key)

        # 2. 固定タイムステップでの更新(重力間隔はプレイヤーごとに独立)
        if not battle.is_over:
            battle.update(elapsed)
            timestep1.update_interval = game1.gravity_interval()
            timestep2.update_interval = game2.gravity_interval()
            for _ in range(timestep1.advance(elapsed)):
                game1.tick()
            for _ in range(timestep2.advance(elapsed)):
                game2.tick()

        # 3. 描画
        stdscr.erase()
        _draw_text(stdscr, 0, p1_board_x, BATTLE_COMMON_HELP, max_x=curses.COLS - 1)
        _draw_board(
            stdscr, game1, origin_y=1, origin_x=p1_board_x, colors_enabled=colors_enabled
        )
        _draw_sidebar(
            stdscr,
            game1,
            origin_y=1,
            origin_x=p1_sidebar_x,
            colors_enabled=colors_enabled,
            title="プレイヤー1",
            help_text=BATTLE_KEY_BINDINGS_HELP_P1,
            max_x=min(p2_board_x - 1, curses.COLS - 1),
            pending_garbage=battle.pending_garbage[PLAYER_1],
        )
        _draw_board(
            stdscr, game2, origin_y=1, origin_x=p2_board_x, colors_enabled=colors_enabled
        )
        _draw_sidebar(
            stdscr,
            game2,
            origin_y=1,
            origin_x=p2_sidebar_x,
            colors_enabled=colors_enabled,
            title="プレイヤー2",
            help_text=BATTLE_KEY_BINDINGS_HELP_P2,
            max_x=curses.COLS - 1,
            pending_garbage=battle.pending_garbage[PLAYER_2],
        )
        if battle.is_over:
            winner = battle.winner
            if winner == 0:
                message = "引き分け! Qキーで終了"
            else:
                message = f"プレイヤー{winner}の勝ち! Qキーで終了"
            _draw_text(
                stdscr,
                game1.board.height + 2,
                p1_board_x,
                message,
                max_x=curses.COLS - 1,
                attr=_accent_attr(colors_enabled, "game_over"),
            )
        stdscr.refresh()

        # 4. フレームレート制御
        frame_elapsed = time.monotonic() - frame_start
        time.sleep(limiter.sleep_duration(frame_elapsed))


def main() -> None:
    # 全角文字を正しく扱うためロケールを環境に合わせる (SPEC.md NFR-5)。
    locale.setlocale(locale.LC_ALL, "")
    # SPEC.md FR-17: "--2p" 指定時は2人対戦モード、未指定時は従来通り1人用モード。
    two_player = "--2p" in sys.argv[1:]
    curses.wrapper(run_battle if two_player else run)
