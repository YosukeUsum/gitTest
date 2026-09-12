"""SPEC.md FR-16・NFR-11関連: ライン消去エフェクトの描画(点滅表現)のテスト。

curses.start_color() 等の実際の色初期化は実端末が必要なため、ここではモノクロ
(colors_enabled=False)での描画を、実端末を必要としない偽のstdscr(_FakeStdscr)で
検証する。curses.A_REVERSE は色初期化なしで参照できる単純な属性定数のため、
実端末が無くても検証可能。
"""
import random
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import curses

from tetris_cli.game import Game, LINE_CLEAR_EFFECT_SECONDS, LINE_CLEAR_BLINK_INTERVAL
from tetris_cli.tetromino import Piece
from tetris_cli.ui_curses import CELL, _draw_board


class _FakeStdscr:
    """_draw_board() の描画内容(位置・文字・属性)を記録するだけの代用品。"""

    def __init__(self):
        self.calls = []

    def addstr(self, y, x, ch, attr=curses.A_NORMAL):
        self.calls.append((y, x, ch, attr))


def _make_game_with_clearing_row():
    """1行を完成させ、hard_dropでロックしてライン消去エフェクトを開始させる。"""
    game = Game(rng=random.Random(0))
    board = game.board
    target_row = board.height - 1
    game.current = Piece(kind="I", rotation=0, row=board.height - 3, col=0)
    for c in range(board.width):
        if not (0 <= c < 4):
            board.grid[target_row][c] = 1
    game.hard_drop()
    assert game.clearing_rows == [target_row]
    return game, target_row


def test_draw_board_applies_reverse_attr_on_flashing_row_when_blink_on():
    """点滅の表示フェーズでは、対象行のセルに A_REVERSE が付く (FR-16)。"""
    game, target_row = _make_game_with_clearing_row()
    game.clear_effect_remaining = LINE_CLEAR_EFFECT_SECONDS  # elapsed=0 -> 表示フェーズ
    assert game.clear_effect_blink_on is True

    stdscr = _FakeStdscr()
    _draw_board(stdscr, game, origin_y=0, origin_x=0, colors_enabled=False)

    row_calls = [c for c in stdscr.calls if c[0] == target_row and c[2] == CELL]
    assert row_calls
    assert all(call[3] & curses.A_REVERSE == curses.A_REVERSE for call in row_calls)


def test_draw_board_does_not_apply_reverse_attr_when_blink_off():
    """点滅の非表示フェーズでは、対象行に A_REVERSE を付けない (NFR-11)。"""
    game, target_row = _make_game_with_clearing_row()
    game.clear_effect_remaining = LINE_CLEAR_EFFECT_SECONDS - LINE_CLEAR_BLINK_INTERVAL
    assert game.clear_effect_blink_on is False

    stdscr = _FakeStdscr()
    _draw_board(stdscr, game, origin_y=0, origin_x=0, colors_enabled=False)

    row_calls = [c for c in stdscr.calls if c[0] == target_row and c[2] == CELL]
    assert row_calls
    assert all(call[3] & curses.A_REVERSE == 0 for call in row_calls)


def test_draw_board_does_not_flash_non_clearing_rows():
    """消去対象でない行には、エフェクト中でも A_REVERSE を付けない。"""
    game, target_row = _make_game_with_clearing_row()
    game.clear_effect_remaining = LINE_CLEAR_EFFECT_SECONDS
    assert game.clear_effect_blink_on is True

    stdscr = _FakeStdscr()
    _draw_board(stdscr, game, origin_y=0, origin_x=0, colors_enabled=False)

    other_row_calls = [c for c in stdscr.calls if c[0] == 0]
    assert other_row_calls
    assert all(call[3] & curses.A_REVERSE == 0 for call in other_row_calls)
