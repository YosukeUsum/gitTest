"""SPEC.md FR-14・FR-15関連: ブロックの色分け・UIアクセントカラーのテスト。

curses.start_color() 等の実際の色初期化は実端末が必要なため対象外とし、
ここでは curses モジュールのインポートのみで完結する「色IDの対応表」の
妥当性のみを検証する(curses定数の参照自体は実端末を必要としない)。
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import curses

from tetris_cli.tetromino import ALL_KINDS, KIND_TO_COLOR
from tetris_cli.ui_curses import (
    COLOR_ID_TO_CURSES_COLOR,
    UI_ACCENT_PAIRS,
    _accent_attr,
    _draw_text,
)


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


def test_ui_accent_pairs_do_not_collide_with_block_color_ids():
    """UI要素(枠線・タイトル・状態メッセージ)のペア番号は、ミノの色ID(1〜7)と
    重複しないこと (SPEC.md FR-15)。"""
    block_color_ids = set(COLOR_ID_TO_CURSES_COLOR.keys())
    ui_pair_ids = {pair_id for pair_id, _ in UI_ACCENT_PAIRS.values()}
    assert block_color_ids.isdisjoint(ui_pair_ids)


def test_ui_accent_pairs_have_unique_pair_ids():
    """UI要素同士のペア番号も重複しないこと。"""
    ui_pair_ids = [pair_id for pair_id, _ in UI_ACCENT_PAIRS.values()]
    assert len(ui_pair_ids) == len(set(ui_pair_ids))


def test_ui_accent_pairs_values_are_valid_curses_color_constants():
    """アクセントカラーの前景色がcursesの正当な色定数(0〜7の整数)であること。"""
    for pair_id, fg in UI_ACCENT_PAIRS.values():
        assert isinstance(pair_id, int)
        assert isinstance(fg, int)
        assert 0 <= fg <= 7


def test_ui_accent_pairs_covers_expected_ui_elements():
    """枠線・タイトル・一時停止・ゲームオーバーの4要素が定義されていること (FR-15)。"""
    assert set(UI_ACCENT_PAIRS.keys()) == {"border", "title", "paused", "game_over"}


def test_accent_attr_returns_normal_when_colors_disabled():
    """色非対応端末では、どのUI要素も無配色(A_NORMAL)にフォールバックする (NFR-10)。"""
    for name in UI_ACCENT_PAIRS:
        assert _accent_attr(False, name) == curses.A_NORMAL


def test_accent_attr_returns_bold_color_pair_when_colors_enabled():
    """色対応端末では、対応するペア番号のcolor_pair()に太字を重ねた値を返す (FR-15)。

    curses.color_pair() は実端末での初期化(initscr)が無いと呼び出せないため、
    ここでは curses.color_pair 自体を実端末不要な単純な関数に一時的に差し替えて
    (_accent_attr()のロジックだけを検証する)。
    """
    original_color_pair = curses.color_pair
    curses.color_pair = lambda pair_id: pair_id * 1000  # 実端末不要なダミー実装
    try:
        for name, (pair_id, _) in UI_ACCENT_PAIRS.items():
            expected = (pair_id * 1000) | curses.A_BOLD
            assert _accent_attr(True, name) == expected
    finally:
        curses.color_pair = original_color_pair


class _FakeStdscr:
    """_draw_text() の描画内容(属性込み)を記録するだけのcursesスクリーンの代用品。

    実端末を必要とせず、addstr呼び出しの引数(位置・文字・属性)を検証するために使う。
    """

    def __init__(self):
        self.calls = []

    def addstr(self, y, x, ch, attr=curses.A_NORMAL):
        self.calls.append((y, x, ch, attr))


def test_draw_text_applies_given_attribute_to_every_character():
    """attr引数を渡すと、描画される全文字にその属性が適用される (FR-15)。

    curses.color_pair() は実端末での初期化が無いと呼び出せないため、ここでは
    curses.A_BOLD (実端末不要な単純なビットフラグ定数) をそのまま attr として使う。
    """
    stdscr = _FakeStdscr()
    attr = curses.A_BOLD
    _draw_text(stdscr, 0, 0, "AB", attr=attr)
    assert len(stdscr.calls) == 2
    assert all(call[3] == attr for call in stdscr.calls)


def test_draw_text_defaults_to_normal_attribute():
    """attr省略時は無配色(A_NORMAL)で描画される(既存の呼び出しとの後方互換性)。"""
    stdscr = _FakeStdscr()
    _draw_text(stdscr, 0, 0, "A")
    assert stdscr.calls[0][3] == curses.A_NORMAL
