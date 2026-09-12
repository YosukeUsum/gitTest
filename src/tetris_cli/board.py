"""盤面の状態管理・衝突判定・ライン消去 (SPEC.md FR-1, FR-4, FR-6)。"""
from __future__ import annotations

import random
from typing import List, Optional

from .tetromino import Piece

WIDTH = 10
HEIGHT = 20

# お邪魔行の色ID (SPEC.md FR-21)。標準8色を7ミノの色分け(FR-14)ですでに
# 使い切っているため(NFR-10)、盤面セルの値としては新しい非0整数を割り当てるに
# とどめ、実際の表示色・属性の割り当てはui_curses.py側で行う。
GARBAGE_COLOR = 8


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

    def find_full_rows(self) -> List[int]:
        """完全に埋まった行のインデックス一覧を返す(消去はしない) (SPEC.md FR-16)。

        ライン消去エフェクト(FR-16)のため、実際の消去を遅延できるように
        「判定」と「消去」を分離している。
        """
        return [r for r in range(self.height) if self.is_row_full(r)]

    def remove_rows(self, rows: List[int]) -> None:
        """指定した行を消去し、上に空行を詰める (SPEC.md FR-6, FR-16)。"""
        rows_set = set(rows)
        remaining = [row for i, row in enumerate(self.grid) if i not in rows_set]
        new_rows = [[0] * self.width for _ in range(len(rows_set))]
        self.grid = new_rows + remaining

    def clear_lines(self) -> int:
        """完全に埋まった行を消去し、詰める。消去した行数を返す (FR-6)。"""
        rows = self.find_full_rows()
        self.remove_rows(rows)
        return len(rows)

    def is_row_full(self, row_index: int) -> bool:
        return all(cell != 0 for cell in self.grid[row_index])

    def add_garbage_rows(self, count: int, rng: Optional[random.Random] = None) -> None:
        """お邪魔行を盤面最下部に追加する (SPEC.md FR-20手順3, FR-21)。

        既存のブロックを上に押し上げるため、盤面上部からcount行を切り捨てる
        (盤面高さは常に一定に保つ)。追加する各行は、ランダムに選んだ1列だけ
        空け、それ以外のマスを `GARBAGE_COLOR` で埋める(1行ごとに独立して
        抽選する)。countが0以下の場合は何もしない。
        """
        if count <= 0:
            return
        rng = rng or random.Random()
        self.grid = self.grid[count:]
        for _ in range(count):
            gap_col = rng.randrange(self.width)
            row = [GARBAGE_COLOR] * self.width
            row[gap_col] = 0
            self.grid.append(row)
