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

CELL = "[]"  # 1マスを表す2文字(等幅で正方形に近い見た目にする)
EMPTY = "  "

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


def _draw_board(stdscr, game: Game, origin_y: int, origin_x: int) -> None:
    board = game.board
    piece_cells = set(game.current.cells()) if not game.game_over else set()

    for r in range(board.height):
        line_chars = []
        for c in range(board.width):
            if (r, c) in piece_cells:
                line_chars.append(CELL)
            elif board.grid[r][c]:
                line_chars.append(CELL)
            else:
                line_chars.append(EMPTY)
        stdscr.addstr(origin_y + r, origin_x, "|" + "".join(line_chars) + "|")
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
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.keypad(True)

    game = Game()
    last_tick = time.monotonic()

    while True:
        stdscr.erase()
        _draw_board(stdscr, game, origin_y=1, origin_x=1)
        _draw_sidebar(stdscr, game, origin_y=1, origin_x=2 + game.board.width * 2 + 3)
        stdscr.refresh()

        key = stdscr.getch()
        if key != -1:
            if not _handle_key(game, key):
                break

        now = time.monotonic()
        if now - last_tick >= game.gravity_interval():
            game.tick()
            last_tick = now

        time.sleep(0.02)


def main() -> None:
    # 全角文字を正しく扱うためロケールを環境に合わせる (SPEC.md NFR-5)。
    locale.setlocale(locale.LC_ALL, "")
    curses.wrapper(run)
