"""curses を用いたCLI描画・キー入力 (SPEC.md ui_curses.py)。

ロジックは Game クラスに委譲し、本モジュールは描画と入力受付のみを行う。
"""
from __future__ import annotations

import curses
import time

from .game import Game

CELL = "[]"  # 1マスを表す2文字(等幅で正方形に近い見た目にする)
EMPTY = "  "

KEY_BINDINGS_HELP = (
    "矢印キー: 移動  ↑/X: 回転(右)  Z: 回転(左)  "
    "Space: ハードドロップ  P: 一時停止  Q: 終了"
)


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
    stdscr.addstr(origin_y, origin_x, "TETRIS")
    stdscr.addstr(origin_y + 2, origin_x, f"Score: {game.score}")
    stdscr.addstr(origin_y + 3, origin_x, f"Level: {game.level}")
    stdscr.addstr(origin_y + 4, origin_x, f"Lines: {game.lines_cleared}")
    stdscr.addstr(origin_y + 6, origin_x, f"Next:  {game.next_kind}")
    if game.paused:
        stdscr.addstr(origin_y + 8, origin_x, "-- PAUSED --")
    if game.game_over:
        stdscr.addstr(origin_y + 8, origin_x, "GAME OVER")
        stdscr.addstr(origin_y + 9, origin_x, "Qで終了")
    stdscr.addstr(origin_y + 11, origin_x, KEY_BINDINGS_HELP[: max(1, curses.COLS - origin_x - 1)])


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
    curses.wrapper(run)
