"""SPEC.md NFR-8 / AC-10, AC-11関連: 固定タイムステップループのテスト。"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tetris_cli.game_loop import FixedTimestepLoop, FrameLimiter, MAX_FRAME_TIME


def test_advance_returns_zero_when_elapsed_less_than_interval():
    loop = FixedTimestepLoop(update_interval=0.1)
    assert loop.advance(0.05) == 0


def test_advance_returns_expected_steps_for_multiple_intervals():
    # elapsed(0.22s)はMAX_FRAME_TIME(0.25s)未満に収め、クランプの影響を受けない値にする。
    loop = FixedTimestepLoop(update_interval=0.05)
    assert loop.advance(0.22) == 4  # 0.02秒はアキュムレータに残る


def test_advance_accumulates_partial_time_across_calls():
    """AC-10: フレームレートに依存せず、蓄積した経過時間から正しい回数を返す。"""
    loop = FixedTimestepLoop(update_interval=0.1)
    assert loop.advance(0.06) == 0
    assert loop.advance(0.06) == 1  # 合計0.12秒蓄積 -> 1回、0.02秒残る


def test_advance_clamps_large_elapsed_time_to_avoid_spiral_of_death():
    """AC-11: 極端に大きな経過時間でもMAX_FRAME_TIMEでクランプされる。"""
    loop = FixedTimestepLoop(update_interval=0.1)
    steps = loop.advance(10.0)
    assert steps == int(MAX_FRAME_TIME / 0.1)


def test_advance_ignores_negative_elapsed_time():
    loop = FixedTimestepLoop(update_interval=0.1)
    assert loop.advance(-1.0) == 0


def test_reset_clears_accumulator():
    loop = FixedTimestepLoop(update_interval=0.1)
    loop.advance(0.09)
    loop.reset()
    assert loop.advance(0.09) == 0


def test_update_interval_change_takes_effect_on_next_advance():
    """レベルアップ等でupdate_intervalが変化しても、次回advanceに反映される。"""
    loop = FixedTimestepLoop(update_interval=1.0)
    # 0.5秒をMAX_FRAME_TIME(0.25s)以下の2回に分けて蓄積する(1回あたりのクランプを回避)。
    assert loop.advance(0.25) == 0
    assert loop.advance(0.25) == 0  # accumulator=0.5, interval=1.0
    loop.update_interval = 0.2
    assert loop.advance(0.0) == 2  # accumulator=0.5, interval=0.2 -> 2回、0.1残る


def test_frame_limiter_sleep_duration_is_never_negative():
    limiter = FrameLimiter(target_fps=50.0)
    assert limiter.sleep_duration(1.0) == 0.0


def test_frame_limiter_sleep_duration_fills_remaining_budget():
    limiter = FrameLimiter(target_fps=50.0)  # frame_budget = 0.02s
    remaining = limiter.sleep_duration(0.005)
    assert abs(remaining - 0.015) < 1e-9


def test_frame_limiter_frame_budget_matches_target_fps():
    limiter = FrameLimiter(target_fps=25.0)
    assert abs(limiter.frame_budget - 0.04) < 1e-9
