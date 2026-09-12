"""curses を用いたCLI描画・キー入力 (SPEC.md ui_curses.py)。

ロジックは Game クラスに委譲し、本モジュールは描画と入力受付のみを行う。

注意 (SPEC.md NFR-5): 画面へ描画する文字列には日本語を使用してよい。ただし
windows-curses は全角文字を含む文字列を addstr に渡すとカーソルを1桁しか進めず、
全角グリフの右半分に次の文字が重なって表示される既知の不具合がある。これを避けるため、
日本語を含むテキストは _draw_text() 経由で描画し、各文字の表示幅
(unicodedata.east_asian_width: 全角=2桁 / 半角=1桁) を明示計算して、確定した桁位置へ
1文字ずつ描画する。盤面の罫線・セル表現などレイアウトの基準となる部分は ASCII のままとする。
"""
from __future__ import annotations

import curses
import locale
import time
import unicodedata

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
COLOR_ID_TO_CURSES_COLOR = {
    KIND_TO_COLOR["I"]: curses.COLOR_CYAN,
    KIND_TO_COLOR["O"]: curses.COLOR_YELLOW,
    KIND_TO_COLOR["T"]: curses.COLOR_MAGENTA,
    KIND_TO_COLOR["S"]: curses.COLOR_GREEN,
    KIND_TO_COLOR["Z"]: curses.COLOR_RED,
    KIND_TO_COLOR["J"]: curses.COLOR_BLUE,
    KIND_TO_COLOR["L"]: curses.COLOR_WHITE,
}

# 画面に表示する操作ヘルプ。全角文字を含むため _draw_text() 経由で描画する (NFR-5)。
KEY_BINDINGS_HELP = (
    "矢印キー:移動  上/X:右回転  Z:左回転  "
    "スペース:ハードドロップ  P:一時停止  Q:終了"
)


def _char_width(ch: str) -> int:
    """端末上での表示桁数を返す。全角(W)・全角互換(F)は2、それ以外は1。"""
    return 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1


def _draw_text(stdscr, y: int, x: int, text: str, max_x: int | None = None) -> None:
    """表示幅を明示計算し、1文字ずつ確定した桁位置へ描画する (SPEC.md NFR-5)。

    windows-curses が全角文字でカーソルを1桁しか進めず文字が重なる不具合への対策。
    max_x を与えると、その桁を超える文字は描画しない(画面幅での打ち切り)。
    """
    cur = x
    for ch in text:
        w = _char_width(ch)
        if max_x is not None and cur + w > max_x:
            break
        try:
            stdscr.addstr(y, cur, ch)
        except curses.error:
            # 画面端など描画不能なセルは無視して継続する。
            pass
        cur += w


def _init_colors() -> bool:
    """cursesの色表示を初期化する (SPEC.md FR-14, NFR-9)。

    端末が色に対応していない場合は何もせず False を返す。呼び出し側はこれを見て
    モノクロ描画にフォールバックし、色非対応端末でもクラッシュしないようにする。
    """
    if not curses.has_colors():
        return False
    try:
        curses.start_color()
        for color_id, fg in COLOR_ID_TO_CURSES_COLOR.items():
            curses.init_pair(color_id, fg, curses.COLOR_BLACK)
    except curses.error:
        return False
    return True


def _draw_board(
    stdscr, game: Game, origin_y: int, origin_x: int, colors_enabled: bool
) -> None:
    """盤面を描画する。ブロックはミノの種類ごとに色分けする (SPEC.md FR-14)。"""
    board = game.board
    if game.game_over:
        piece_cells: set[tuple[int, int]] = set()
        piece_color = 0
    else:
        piece_cells = set(game.current.cells())
        piece_color = game.current.color()

    for r in range(board.height):
        stdscr.addstr(origin_y + r, origin_x, "|")
        cur_x = origin_x + 1
        for c in range(board.width):
            color_id = piece_color if (r, c) in piece_cells else board.grid[r][c]
            if color_id:
                attr = curses.color_pair(color_id) if colors_enabled else curses.A_NORMAL
                stdscr.addstr(origin_y + r, cur_x, CELL, attr)
            else:
                stdscr.addstr(origin_y + r, cur_x, EMPTY)
            cur_x += 2
        stdscr.addstr(origin_y + r, cur_x, "|")
    stdscr.addstr(origin_y + board.height, origin_x, "+" + "--" * board.width + "+")


def _draw_sidebar(stdscr, game: Game, origin_y: int, origin_x: int) -> None:
    _draw_text(stdscr, origin_y, origin_x, "テトリス")
    _draw_text(stdscr, origin_y + 2, origin_x, f"スコア: {game.score}")
    _draw_text(stdscr, origin_y + 3, origin_x, f"レベル: {game.level}")
    _draw_text(stdscr, origin_y + 4, origin_x, f"ライン: {game.lines_cleared}")
    _draw_text(stdscr, origin_y + 6, origin_x, f"ネクスト: {game.next_kind}")
    if game.paused:
        _draw_text(stdscr, origin_y + 8, origin_x, "-- 一時停止中 --")
    if game.game_over:
        _draw_text(stdscr, origin_y + 8, origin_x, "ゲームオーバー")
        _draw_text(stdscr, origin_y + 9, origin_x, "Q キーで終了")
    _draw_text(stdscr, origin_y + 11, origin_x, KEY_BINDINGS_HELP, max_x=curses.COLS - 1)


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
        timestep.update_interval = game.gravity_interval()
        for _ in range(timestep.advance(elapsed)):
            game.tick()

        # 3. 描画
        stdscr.erase()
        _draw_board(stdscr, game, origin_y=1, origin_x=1, colors_enabled=colors_enabled)
        _draw_sidebar(stdscr, game, origin_y=1, origin_x=2 + game.board.width * 2 + 3)
        stdscr.refresh()

        # 4. フレームレート制御
        frame_elapsed = time.monotonic() - frame_start
        time.sleep(limiter.sleep_duration(frame_elapsed))


def main() -> None:
    # 全角文字を正しく扱うためロケールを環境に合わせる (SPEC.md NFR-5)。
    locale.setlocale(locale.LC_ALL, "")
    curses.wrapper(run)
