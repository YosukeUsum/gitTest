"""AC-9関連: テトリミノの形状・7-bagランダマイザのテスト。"""
import random
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tetris_cli.tetromino import ALL_KINDS, SHAPES, Piece
from tetris_cli.game import SevenBag


def test_all_kinds_have_four_rotations_with_four_cells():
    for kind in ALL_KINDS:
        rotations = SHAPES[kind]
        assert len(rotations) == 4
        for cells in rotations:
            assert len(cells) == 4


def test_piece_cells_offset_by_position():
    piece = Piece(kind="O", rotation=0, row=5, col=2)
    cells = piece.cells()
    base = SHAPES["O"][0]
    expected = [(5 + r, 2 + c) for r, c in base]
    assert cells == expected


def test_seven_bag_no_duplicates_within_a_bag():
    """AC-9: 連続する7回の出現に同じ種類の重複がない。"""
    bag = SevenBag(rng=random.Random(42))
    drawn = [bag.next() for _ in range(7)]
    assert sorted(drawn) == sorted(ALL_KINDS)
    assert len(set(drawn)) == 7


def test_seven_bag_refills_after_seven_draws():
    bag = SevenBag(rng=random.Random(1))
    first_bag = [bag.next() for _ in range(7)]
    second_bag = [bag.next() for _ in range(7)]
    assert sorted(first_bag) == sorted(ALL_KINDS)
    assert sorted(second_bag) == sorted(ALL_KINDS)
