"""AC-2, AC-3, AC-4関連: 盤面の衝突判定・ライン消去のテスト。"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tetris_cli.board import Board
from tetris_cli.tetromino import Piece


def test_can_place_within_empty_board():
    board = Board()
    piece = Piece(kind="O", rotation=0, row=0, col=4)
    assert board.can_place(piece) is True


def test_cannot_place_beyond_left_wall():
    board = Board()
    piece = Piece(kind="I", rotation=0, row=0, col=-2)
    assert board.can_place(piece) is False


def test_cannot_place_beyond_right_wall():
    board = Board()
    piece = Piece(kind="I", rotation=0, row=0, col=8)
    assert board.can_place(piece) is False


def test_cannot_place_beyond_floor():
    board = Board()
    piece = Piece(kind="O", rotation=0, row=board.height - 1, col=4)
    assert board.can_place(piece) is False


def test_cannot_place_on_existing_block():
    board = Board()
    board.grid[10][4] = 1
    piece = Piece(kind="O", rotation=0, row=9, col=3)
    # OミノはSHAPES上 (0,1)(0,2)(1,1)(1,2) を占有するため row=9,col=3 で (10,4)と重なる
    assert board.can_place(piece) is False


def test_clear_single_full_line():
    board = Board()
    board.grid[19] = [1] * board.width
    cleared = board.clear_lines()
    assert cleared == 1
    assert board.grid[19] == [0] * board.width
    assert all(cell == 0 for cell in board.grid[0])


def test_clear_multiple_lines_simultaneously():
    """AC-4: 同時に複数行を消去できる。"""
    board = Board()
    board.grid[17] = [1] * board.width
    board.grid[18] = [1] * board.width
    board.grid[19] = [1] * board.width
    cleared = board.clear_lines()
    assert cleared == 3


def test_lock_piece_writes_color_into_grid():
    board = Board()
    piece = Piece(kind="T", rotation=0, row=0, col=4)
    board.lock_piece(piece)
    for r, c in piece.cells():
        assert board.grid[r][c] == piece.color()
