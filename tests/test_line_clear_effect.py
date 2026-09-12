"""SPEC.md FR-16・NFR-11・AC-13関連: ライン消去エフェクトのテスト。"""
import random
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tetris_cli.game import Game, LINE_CLEAR_EFFECT_SECONDS, LINE_CLEAR_BLINK_INTERVAL
from tetris_cli.tetromino import Piece


def make_game(seed: int = 0) -> Game:
    return Game(rng=random.Random(seed))


def _complete_one_line(game: Game) -> int:
    """1行を確実に完成させ、hard_dropで固定する。完成した行のインデックスを返す。

    tests/test_game.py の test_line_clear_awards_score_and_lines と同様の手法で、
    ミノの形状に依存せず確実に1行を完成させる。
    """
    board = game.board
    target_row = board.height - 1
    game.current = Piece(kind="I", rotation=0, row=board.height - 3, col=0)
    for c in range(board.width):
        if not (0 <= c < 4):
            board.grid[target_row][c] = 1
    game.hard_drop()
    return target_row


def test_completing_a_line_starts_clear_effect_without_removing_it_immediately():
    """AC-13: 行が完成しても即座には盤面から消去されない。"""
    game = make_game()
    target_row = _complete_one_line(game)
    assert game.clearing_rows == [target_row]
    assert game.clear_effect_remaining == LINE_CLEAR_EFFECT_SECONDS
    # 消去されていないので、対象行はまだ埋まったまま。
    assert all(cell != 0 for cell in game.board.grid[target_row])


def test_score_and_lines_cleared_update_immediately_even_during_effect():
    """行が完成した時点でスコア・消去ライン数は即座に更新される(演出とは独立)。"""
    game = make_game()
    score_before = game.score
    lines_before = game.lines_cleared
    _complete_one_line(game)
    assert game.score > score_before
    assert game.lines_cleared == lines_before + 1


def test_player_actions_and_gravity_are_ignored_while_clear_effect_active():
    """AC-13: エフェクト表示中は移動・回転・ドロップ・重力が反映されない。"""
    game = make_game()
    _complete_one_line(game)
    assert game.clearing_rows

    row_before, col_before = game.current.row, game.current.col
    assert game.move_left() is False
    assert game.move_right() is False
    assert game.rotate_cw() is False
    assert game.soft_drop() is False
    assert game.hard_drop() == 0
    assert (game.current.row, game.current.col) == (row_before, col_before)

    game.tick()
    assert game.clearing_rows  # tick()では消去が進行しない


def test_update_with_insufficient_time_keeps_effect_active():
    """経過時間がエフェクト時間未満なら、まだ消去されない。"""
    game = make_game()
    target_row = _complete_one_line(game)
    game.update(LINE_CLEAR_EFFECT_SECONDS / 2)
    assert game.clearing_rows == [target_row]


def test_update_after_effect_duration_clears_row_and_spawns_next_piece():
    """AC-13: エフェクト時間の経過後、実際に行が消去され次のミノが出現する。"""
    game = make_game()
    target_row = _complete_one_line(game)
    game.update(LINE_CLEAR_EFFECT_SECONDS)
    assert game.clearing_rows == []
    assert game.clear_effect_remaining == 0.0
    assert all(cell == 0 for cell in game.board.grid[target_row])
    # ビジー状態が解除され、再び操作を受け付ける。
    assert game.move_left() in (True, False)


def test_update_does_nothing_when_not_clearing():
    """エフェクト中でなければ update() は何もしない。"""
    game = make_game()
    row_before, col_before = game.current.row, game.current.col
    game.update(1.0)
    assert (game.current.row, game.current.col) == (row_before, col_before)


def test_update_ignored_while_paused():
    """一時停止中はエフェクトの残り時間が進まない。"""
    game = make_game()
    _complete_one_line(game)
    remaining_before = game.clear_effect_remaining
    game.paused = True
    game.update(LINE_CLEAR_EFFECT_SECONDS)
    assert game.clearing_rows
    assert game.clear_effect_remaining == remaining_before


def test_clear_effect_blink_on_is_false_when_not_clearing():
    game = make_game()
    assert game.clear_effect_blink_on is False


def test_clear_effect_blink_on_toggles_with_elapsed_time():
    """NFR-11: 点滅の表示フェーズが、経過時間に応じて交互に切り替わる。"""
    game = make_game()
    _complete_one_line(game)  # clearing_rows・clear_effect_remaining を設定させる

    # elapsed=0 (remaining=満タン) は表示フェーズ(True)から始まる。
    game.clear_effect_remaining = LINE_CLEAR_EFFECT_SECONDS
    assert game.clear_effect_blink_on is True

    game.clear_effect_remaining = LINE_CLEAR_EFFECT_SECONDS - LINE_CLEAR_BLINK_INTERVAL
    assert game.clear_effect_blink_on is False

    game.clear_effect_remaining = LINE_CLEAR_EFFECT_SECONDS - 2 * LINE_CLEAR_BLINK_INTERVAL
    assert game.clear_effect_blink_on is True

    game.clear_effect_remaining = LINE_CLEAR_EFFECT_SECONDS - 3 * LINE_CLEAR_BLINK_INTERVAL
    assert game.clear_effect_blink_on is False
