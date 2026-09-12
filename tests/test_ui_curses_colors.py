"""SPEC.md FR-14関連: ブロックの色分けマッピングのテスト。

curses.start_color() 等の実際の色初期化は実端末が必要なため対象外とし、
ここでは curses モジュールのインポートのみで完結する「色IDの対応表」の
妥当性のみを検証する(curses定数の参照自体は実端末を必要としない)。
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tetris_cli.tetromino import ALL_KINDS, KIND_TO_COLOR
from tetris_cli.ui_curses import COLOR_ID_TO_CURSES_COLOR


def test_color_mapping_covers_every_tetromino_kind():
    """全7種のミノに対応する色IDがすべてマッピングされている。"""
    expected_color_ids = set(KIND_TO_COLOR.values())
    assert set(COLOR_ID_TO_CURSES_COLOR.keys()) == expected_color_ids
    assert len(COLOR_ID_TO_CURSES_COLOR) == len(ALL_KINDS) == 7


def test_color_mapping_has_no_duplicate_curses_colors():
    """各ミノの色は重複せず、視認性のため色が衝突しないこと。"""
    curses_colors = list(COLOR_ID_TO_CURSES_COLOR.values())
    assert len(curses_colors) == len(set(curses_colors))


def test_color_mapping_values_are_valid_curses_color_constants():
    """マッピング先がcursesの正当な色定数(0〜7の整数)であること。"""
    for curses_color in COLOR_ID_TO_CURSES_COLOR.values():
        assert isinstance(curses_color, int)
        assert 0 <= curses_color <= 7
