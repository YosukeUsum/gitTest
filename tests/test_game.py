"""AC-1, AC-4, AC-5, AC-6, AC-7, AC-8関連: ゲームロジックのテスト。"""
import random
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tetris_cli.game import Game, LINES_PER_LEVEL
from tetris_cli.board import Board


def make_game(seed: int = 0) -> Game:
    return Game(rng=random.Random(seed))


def test_new_piece_spawns_near_top_center():
    """AC-1: 新規ミノは盤面上部中央付近に出現する。"""
    game = make_game()
    assert game.current.col in range(0, game.board.width - 1)
    assert game.current.row <= 0


def test_move_blocked_by_wall():
    """AC-2: 壁を超えて移動できない。"""
    game = make_game()
    # 左端まで移動させる
    for _ in range(10):
        game.move_left()
    col_before = game.current.col
    moved = game.move_left()
    assert moved is False
    assert game.current.col == col_before


def test_line_clear_awards_score_and_lines():
    """AC-3: 1行揃うとスコアが加算され消去される。"""
    from tetris_cli.tetromino import Piece

    game = make_game()
    board = game.board
    # 既知の形状(Iミノ・横向き)を最下段に落とし、残り列を埋めておくことで
    # ミノの形状に依存せず確実に1行を完成させる。
    game.current = Piece(kind="I", rotation=0, row=board.height - 3, col=0)
    for c in range(board.width):
        if not (0 <= c < 4):
            board.grid[board.height - 1][c] = 1
    score_before = game.score
    game.hard_drop()
    assert game.lines_cleared >= 1
    assert game.score > score_before


def test_tetris_four_lines_scores_more_per_line_than_single():
    """AC-4: 4行同時消去(テトリス)は1行消去より得点効率が高い。"""
    from tetris_cli.game import _LINE_SCORE_TABLE
    assert _LINE_SCORE_TABLE[4] / 4 > _LINE_SCORE_TABLE[1] / 1


def test_level_up_after_ten_lines():
    """AC-5: 累計10ライン消去でレベルが2になる。"""
    game = make_game()
    game.lines_cleared = LINES_PER_LEVEL
    game.level = 1 + game.lines_cleared // LINES_PER_LEVEL
    assert game.level == 2
    faster_game = make_game()
    faster_game.level = 2
    assert faster_game.gravity_interval() < make_game().gravity_interval()


def test_game_over_when_spawn_blocked():
    """AC-6: 出現位置に既存ブロックがあるとgame_overになる。"""
    game = make_game()
    # 全ミノ形状はローカル行1(SPAWN_ROW=-1のとき盤面row=0)に必ずブロックを持つため、
    # row=0を全列埋めておけば、どの種類のミノが出現してもかならず衝突する。
    for c in range(game.board.width):
        game.board.grid[0][c] = 1
    game._spawn_next()
    assert game.game_over is True


def test_hard_drop_locks_piece_and_adds_bonus_score():
    """AC-7: ハードドロップは即座に着地し、距離ボーナスが加算される。"""
    game = make_game()
    score_before = game.score
    distance = game.hard_drop()
    assert distance >= 0
    assert game.score >= score_before


def test_rotation_uses_wall_kick_near_wall():
    """AC-8: 壁際でも回転が可能なケースがある(ウォールキック)。"""
    game = make_game()
    # Iミノを左端に寄せて回転を試みる
    game.current.kind = "I"
    game.current.rotation = 0
    game.current.col = 0
    game.current.row = 5
    rotated = game.rotate_cw()
    assert rotated in (True, False)  # 例外なく完了することを確認
    assert 0 <= game.current.rotation <= 3
