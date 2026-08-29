"""テトリミノの形状・回転定義 (SPEC.md 6章, 7章)。

curses等のUIには依存しない純粋なロジック。
各ミノは 4x4 のグリッド上での占有マス (row, col) の集合を
回転状態 (0-3) ごとに定義する簡易SRS方式。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

Coord = Tuple[int, int]  # (row, col) 0-3 の4x4グリッド内座標

# 各ミノ種別の基準(回転0)形状。4x4グリッド内の占有セル。
_BASE_SHAPES: Dict[str, List[Coord]] = {
    "I": [(1, 0), (1, 1), (1, 2), (1, 3)],
    "O": [(0, 1), (0, 2), (1, 1), (1, 2)],
    "T": [(0, 1), (1, 0), (1, 1), (1, 2)],
    "S": [(0, 1), (0, 2), (1, 0), (1, 1)],
    "Z": [(0, 0), (0, 1), (1, 1), (1, 2)],
    "J": [(0, 0), (1, 0), (1, 1), (1, 2)],
    "L": [(0, 2), (1, 0), (1, 1), (1, 2)],
}

ALL_KINDS: Tuple[str, ...] = ("I", "O", "T", "S", "Z", "J", "L")

# 各ミノの色ID (盤面セルに書き込む非0整数値)。1始まり。
KIND_TO_COLOR: Dict[str, int] = {kind: i + 1 for i, kind in enumerate(ALL_KINDS)}


def _rotate_cw(cells: List[Coord]) -> List[Coord]:
    """4x4グリッド内で時計回りに90度回転させる。"""
    # (r, c) -> (c, 3 - r)
    return [(c, 3 - r) for r, c in cells]


def _build_rotations(base: List[Coord]) -> List[List[Coord]]:
    rotations = [base]
    current = base
    for _ in range(3):
        current = _rotate_cw(current)
        rotations.append(current)
    return rotations


# kind -> [rotation0, rotation1, rotation2, rotation3] の占有セルリスト
SHAPES: Dict[str, List[List[Coord]]] = {
    kind: _build_rotations(cells) for kind, cells in _BASE_SHAPES.items()
}

# 簡易ウォールキックのオフセット候補 (SPEC.md FR-5)。
# 左右±1, ±2マスの順に試す。
WALL_KICK_OFFSETS: Tuple[Tuple[int, int], ...] = (
    (0, 0),
    (0, -1),
    (0, 1),
    (0, -2),
    (0, 2),
    (-1, 0),  # 天井付近での回転救済(上に1マス)
)


@dataclass
class Piece:
    """盤面上のテトリミノの状態。"""

    kind: str
    rotation: int = 0
    # 盤面座標系での基準位置(4x4グリッドの左上が (row, col))
    row: int = 0
    col: int = 3

    def cells(self, rotation: int | None = None) -> List[Coord]:
        """指定回転状態(省略時は現在の回転)における、盤面座標系でのセル一覧。"""
        rot = self.rotation if rotation is None else rotation
        shape = SHAPES[self.kind][rot % 4]
        return [(self.row + r, self.col + c) for r, c in shape]

    def color(self) -> int:
        return KIND_TO_COLOR[self.kind]
