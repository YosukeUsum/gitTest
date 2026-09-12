"""AC-14〜AC-19関連: 2人対戦モード(お邪魔行攻撃)のテスト。"""
import random
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tetris_cli.battle import ATTACK_TABLE, BattleGame, PLAYER_1, PLAYER_2
from tetris_cli.board import GARBAGE_COLOR, Board
from tetris_cli.game import LINE_CLEAR_EFFECT_SECONDS
from tetris_cli.tetromino import Piece


def make_battle(seed: int = 0) -> BattleGame:
    return BattleGame(rng=random.Random(seed))


def test_attack_table_matches_spec():
    """AC-14: 1/2/3/4行消去に対する攻撃力がそれぞれ0/1/2/4であること。"""
    assert ATTACK_TABLE[1] == 0
    assert ATTACK_TABLE[2] == 1
    assert ATTACK_TABLE[3] == 2
    assert ATTACK_TABLE[4] == 4


def test_cancel_partial_reduces_pending_without_new_attack():
    """AC-15: 保留3、2行消去(攻撃力1)で保留は2に減り、相手への新規攻撃は無い。"""
    battle = make_battle()
    battle.pending_garbage[PLAYER_1] = 3
    battle._on_locked(PLAYER_1, 2)
    assert battle.pending_garbage[PLAYER_1] == 2
    assert battle.pending_garbage[PLAYER_2] == 0


def test_cancel_overflow_sends_remaining_attack_to_opponent():
    """AC-16: 保留1、4行消去(攻撃力4)で保留は0になり、相手へ3行送信される。"""
    battle = make_battle()
    battle.pending_garbage[PLAYER_1] = 1
    battle._on_locked(PLAYER_1, 4)
    assert battle.pending_garbage[PLAYER_1] == 0
    assert battle.pending_garbage[PLAYER_2] == 3


def test_cancel_exact_match_results_in_zero_pending_and_zero_new_attack():
    """AC-16の境界: 保留4、4行消去(攻撃力4)で保留・新規攻撃とも0になる。"""
    battle = make_battle()
    battle.pending_garbage[PLAYER_1] = 4
    battle._on_locked(PLAYER_1, 4)
    assert battle.pending_garbage[PLAYER_1] == 0
    assert battle.pending_garbage[PLAYER_2] == 0


def test_pending_garbage_accumulates_across_multiple_opponent_attacks():
    """相手が自分のロック前に複数回攻撃した場合、保留は単純加算で積み上がる。"""
    battle = make_battle()
    battle._on_locked(PLAYER_1, 3)  # 攻撃力2 -> PLAYER_2の保留に加算
    battle._on_locked(PLAYER_1, 4)  # 攻撃力4 -> PLAYER_2の保留にさらに加算
    assert battle.pending_garbage[PLAYER_2] == 6


def test_no_clear_still_runs_cancel_step_as_noop():
    """消去が無い(cleared=0)ロックでも手順自体は適用され、保留は変化しない。"""
    battle = make_battle()
    battle.pending_garbage[PLAYER_1] = 2
    battle._on_locked(PLAYER_1, 0)
    assert battle.pending_garbage[PLAYER_1] == 2
    assert battle.pending_garbage[PLAYER_2] == 0


def test_before_spawn_applies_remaining_pending_and_resets_to_zero():
    """AC-17: 次のミノ出現直前に、相殺後の残り保留分が盤面に反映され0になる。"""
    battle = make_battle()
    battle.pending_garbage[PLAYER_1] = 2
    battle._on_before_spawn(PLAYER_1)
    assert battle.pending_garbage[PLAYER_1] == 0
    bottom_two = battle.player1.board.grid[-2:]
    for row in bottom_two:
        assert row.count(0) == 1


def test_before_spawn_does_nothing_when_no_pending():
    battle = make_battle()
    grid_before = [row[:] for row in battle.player1.board.grid]
    battle._on_before_spawn(PLAYER_1)
    assert battle.player1.board.grid == grid_before


def test_garbage_row_shape_has_exactly_one_gap_and_garbage_color():
    """AC-18: 追加されたお邪魔行は1列だけ空き、他9マスは固定ブロックで埋まる。"""
    board = Board()
    board.add_garbage_rows(3, rng=random.Random(0))
    for row in board.grid[-3:]:
        assert row.count(0) == 1
        filled = [cell for cell in row if cell != 0]
        assert len(filled) == board.width - 1
        assert all(cell == GARBAGE_COLOR for cell in filled)


def test_add_garbage_rows_preserves_board_height_in_normal_case():
    """盤面の高さ不変条件(len(grid) == height)は通常のcountでも保たれる。"""
    board = Board()
    board.add_garbage_rows(3, rng=random.Random(0))
    assert len(board.grid) == board.height


def test_add_garbage_rows_count_exceeding_height_is_clamped():
    """countが盤面の高さ以上でも、高さで切り詰められ盤面全体がお邪魔行になる。"""
    board = Board()
    board.add_garbage_rows(board.height + 5, rng=random.Random(0))
    assert len(board.grid) == board.height
    for row in board.grid:
        assert row.count(0) == 1
        filled = [cell for cell in row if cell != 0]
        assert len(filled) == board.width - 1


def test_add_garbage_rows_count_equal_to_height_fills_whole_board():
    """countがちょうど盤面の高さと一致する境界値でも高さ不変条件が保たれる。"""
    board = Board()
    board.add_garbage_rows(board.height, rng=random.Random(0))
    assert len(board.grid) == board.height
    for row in board.grid:
        assert row.count(0) == 1


def test_winner_none_while_both_players_ongoing():
    battle = make_battle()
    assert battle.winner is None
    assert battle.is_over is False


def test_winner_is_opponent_of_the_player_who_topped_out():
    """AC-19: 一方がゲームオーバーになると、もう一方が勝者と判定される。"""
    battle = make_battle()
    battle.player1.game_over = True
    assert battle.is_over is True
    assert battle.winner == PLAYER_2


def test_winner_is_draw_when_both_game_over_simultaneously():
    battle = make_battle()
    battle.player1.game_over = True
    battle.player2.game_over = True
    assert battle.winner == 0


def test_winner_is_player1_when_player2_tops_out():
    """AC-19の対称ケース: PLAYER_2が先にトップアウトした場合はPLAYER_1が勝者。"""
    battle = make_battle()
    battle.player2.game_over = True
    assert battle.is_over is True
    assert battle.winner == PLAYER_1


def test_garbage_reflection_can_cause_game_over_by_collision():
    """FR-22: お邪魔行反映で出現位置に衝突すると、通常のゲームオーバー判定と
    同様にゲームオーバーになる(壁打ちログの決定事項)。"""
    battle = make_battle()
    game = battle.player1
    board = game.board
    pending = 5
    # 反映後にrow=0となる行(現在のrow=pending)を全列埋めておき、どの形状の
    # ミノが出現しても必ず衝突するようにする。
    board.grid[pending] = [1] * board.width
    battle.pending_garbage[PLAYER_1] = pending
    battle._on_before_spawn(PLAYER_1)
    assert battle.pending_garbage[PLAYER_1] == 0
    game._spawn_next()
    assert game.game_over is True
    assert battle.is_over is True
    assert battle.winner == PLAYER_2


def test_each_player_has_independent_game_board_and_score():
    """FR-18: 各プレイヤーが独立した盤面・スコアを持つ(片方の変更が他方に
    波及しない)。"""
    battle = make_battle()
    assert battle.player1 is not battle.player2
    assert battle.player1.board is not battle.player2.board
    battle.player1.score += 100
    assert battle.player2.score == 0
    battle.player1.board.grid[0][0] = 1
    assert battle.player2.board.grid[0][0] == 0


def test_garbage_not_applied_until_line_clear_effect_completes():
    """FR-20手順3: ライン消去エフェクト完了前はupdate()を呼んでもお邪魔行は
    盤面に反映されず、エフェクト完了で初めて反映される。"""
    battle = make_battle()
    battle.pending_garbage[PLAYER_1] = 2
    game = battle.player1
    board = game.board
    game.current = Piece(kind="I", rotation=0, row=board.height - 3, col=0)
    for c in range(board.width):
        if not (0 <= c < 4):
            board.grid[board.height - 1][c] = 1
    game.hard_drop()
    assert game.clearing_rows  # エフェクト表示中

    grid_snapshot = [row[:] for row in board.grid]
    battle.update(LINE_CLEAR_EFFECT_SECONDS / 2)
    assert battle.pending_garbage[PLAYER_1] == 2
    assert board.grid == grid_snapshot

    battle.update(LINE_CLEAR_EFFECT_SECONDS)
    assert battle.pending_garbage[PLAYER_1] == 0
    assert board.grid != grid_snapshot


def test_real_line_clear_sends_attack_through_game_hooks():
    """Game.hard_drop() からのロックが、実際にBattleGame経由で相手へ攻撃を送ること
    を確認する結合テスト(FR-19, FR-20)。"""
    battle = make_battle()
    game = battle.player1
    board = game.board
    # 既知の形状(Iミノ・横向き)を最下段に落とし、残り列を埋めて1行を確実に
    # 完成させる(test_game.py の手法を踏襲)。
    game.current = Piece(kind="I", rotation=0, row=board.height - 3, col=0)
    for c in range(board.width):
        if not (0 <= c < 4):
            board.grid[board.height - 1][c] = 1
    game.hard_drop()
    assert game.lines_cleared >= 1
    # 1行消去の攻撃力は0(ATTACK_TABLE[1] == 0)のため、相手への新規攻撃は発生しない。
    assert battle.pending_garbage[PLAYER_2] == 0


def test_real_two_line_clear_sends_nonzero_attack_through_game_hooks():
    """2行同時消去(攻撃力1)が、実際にBattleGame経由で相手の保留に積まれる
    ことを確認する結合テスト(FR-19, FR-20)。1行消去のみを確認する
    上記テストでは検出できない、実際に攻撃が発生する経路を検証する。"""
    battle = make_battle()
    game = battle.player1
    board = game.board
    # Oミノ(2x2)を2列(col=1,2)だけ空けた最下段2行に落とし、両方を同時に
    # 完成させる。
    game.current = Piece(kind="O", rotation=0, row=board.height - 2, col=0)
    for r in (board.height - 2, board.height - 1):
        for c in range(board.width):
            if c not in (1, 2):
                board.grid[r][c] = 1
    game.hard_drop()
    assert game.lines_cleared >= 2
    assert battle.pending_garbage[PLAYER_2] == 1


def test_real_two_line_clear_from_player2_sends_attack_through_game_hooks():
    """PLAYER_2側のフック配線(on_locked/on_before_spawn)がPLAYER_1と対称に
    機能することを確認する結合テスト(対称なラムダ定義のコピペミス検出)。"""
    battle = make_battle()
    game = battle.player2
    board = game.board
    game.current = Piece(kind="O", rotation=0, row=board.height - 2, col=0)
    for r in (board.height - 2, board.height - 1):
        for c in range(board.width):
            if c not in (1, 2):
                board.grid[r][c] = 1
    game.hard_drop()
    assert game.lines_cleared >= 2
    assert battle.pending_garbage[PLAYER_1] == 1
