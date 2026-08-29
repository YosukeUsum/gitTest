"""盤面の状態管理・衝突判定・ライン消去 (SPEC.md FR-1, FR-4, FR-6)。"""
from __future__ import annotations

from typing import List

from .tetromino import Piece

WIDTH = 10
HEIGHT = 20


class Board:
    """幅WIDTH x 高さHEIGHTのグリッド。0=空、非0=固定ブロックの色ID。"""

    def __init__(self, width: int = WIDTH, height: int = HEIGHT) -> None:
        self.width = width
        self.height = height
        self.grid: List[List[int]] = [[0] * width for _ in range(height)]

    def is_inside(self, row: int, col: int) -> bool:
        return 0 <= col < self.width and row < self.height

    def is_cell_free(self, row: int, col: int) -> bool:
        """指定セルが移動先として有効か(盤面内かつ空、または上部見えない領域)。"""
        if col < 0 or col >= self.width:
            return False
        if row >= self.height:
            return False
        if row < 0:
            # 盤面上部(見えない領域)は自由に通過可能
            return True
        return self.grid[row][col] == 0

    def can_place(self, piece: Piece, rotation: int | None = None,
                   row_offset: int = 0, col_offset: int = 0) -> bool:
        """指定のオフセット・回転でpieceを配置可能か判定する (FR-4)。"""
        for r, c in piece.cells(rotation):
            r += row_offset
            c += col_offset
            if not self.is_cell_free(r, c):
                return False
        return True

    def lock_piece(self, piece: Piece) -> None:
        """ミノを盤面に固定する。"""
        color = piece.color()
        for r, c in piece.cells():
            if 0 <= r < self.height and 0 <= c < self.width:
                self.grid[r][c] = color

    def clear_lines(self) -> int:
        """完全に埋まった行を消去し、詰める。消去した行数を返す (FR-6)。"""
        remaining = [row for row in self.grid if any(cell == 0 for cell in row)]
        cleared = self.height - len(remaining)
        new_rows = [[0] * self.width for _ in range(cleared)]
        self.grid = new_rows + remaining
        return cleared

    def is_row_full(self, row_index: int) -> bool:
        return all(cell != 0 for cell in self.grid[row_index])
