"""ゲームロジック本体 (SPEC.md game.py)。UI(curses)には非依存。"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import List, Optional

from .board import Board
from .tetromino import ALL_KINDS, WALL_KICK_OFFSETS, Piece

# レベルごとの落下間隔(秒)。レベルが上がるほど短くなる (FR-9)。
_BASE_GRAVITY_SECONDS = 0.8
_GRAVITY_DECAY_PER_LEVEL = 0.07
_MIN_GRAVITY_SECONDS = 0.08

# ライン数によるスコア係数 (FR-7)。index = 同時消去行数。
_LINE_SCORE_TABLE = {1: 100, 2: 300, 3: 500, 4: 800}

LINES_PER_LEVEL = 10  # AC-5: 10ラインごとにレベルアップ
SPAWN_COL = 3  # 盤面幅10・4x4グリッド基準でおおよそ中央 (AC-1)
SPAWN_ROW = -1  # 上部からわずかに見えない状態で出現させる。
# 全ミノ形状は4x4グリッドのローカル行1に必ずブロックを持つため、
# SPAWN_ROW=-1 のとき盤面row=0が出現位置の衝突判定対象になる (FR-11, AC-6)。


class SevenBag:
    """7-bagランダマイザ (SPEC.md FR-2, AC-9)。

    7種のミノを1つずつ含む袋からシャッフルして払い出す。
    袋が空になったら再充填する。
    """

    def __init__(self, rng: Optional[random.Random] = None) -> None:
        self._rng = rng or random.Random()
        self._bag: List[str] = []

    def _refill(self) -> None:
        self._bag = list(ALL_KINDS)
        self._rng.shuffle(self._bag)

    def next(self) -> str:
        if not self._bag:
            self._refill()
        return self._bag.pop()


@dataclass
class GameState:
    board: Board = field(default_factory=Board)
    score: int = 0
    level: int = 1
    lines_cleared: int = 0
    game_over: bool = False
    paused: bool = False


class Game:
    """テトリスのゲームロジック本体。UIから呼び出される公開APIを提供する。"""

    def __init__(self, rng: Optional[random.Random] = None) -> None:
        self.board = Board()
        self._bag = SevenBag(rng)
        self.score = 0
        self.level = 1
        self.lines_cleared = 0
        self.game_over = False
        self.paused = False

        self.current: Piece = self._spawn_piece(self._bag.next())
        self.next_kind: str = self._bag.next()
        # 出現時点で衝突していればゲームオーバー (FR-11, AC-6)
        if not self.board.can_place(self.current):
            self.game_over = True

    # ------------------------------------------------------------------
    # 出現・重力
    # ------------------------------------------------------------------
    def _spawn_piece(self, kind: str) -> Piece:
        return Piece(kind=kind, rotation=0, row=SPAWN_ROW, col=SPAWN_COL)

    def gravity_interval(self) -> float:
        """現在のレベルに応じた落下間隔(秒) (FR-9)。"""
        interval = _BASE_GRAVITY_SECONDS - (self.level - 1) * _GRAVITY_DECAY_PER_LEVEL
        return max(interval, _MIN_GRAVITY_SECONDS)

    def _spawn_next(self) -> None:
        kind = self.next_kind
        self.next_kind = self._bag.next()
        self.current = self._spawn_piece(kind)
        if not self.board.can_place(self.current):
            self.game_over = True

    # ------------------------------------------------------------------
    # 操作 (FR-3)
    # ------------------------------------------------------------------
    def move_left(self) -> bool:
        return self._try_move(0, -1)

    def move_right(self) -> bool:
        return self._try_move(0, 1)

    def _try_move(self, row_offset: int, col_offset: int) -> bool:
        if self.game_over or self.paused:
            return False
        if self.board.can_place(self.current, row_offset=row_offset, col_offset=col_offset):
            self.current.row += row_offset
            self.current.col += col_offset
            return True
        return False

    def soft_drop(self) -> bool:
        """1マス下に移動できればスコアを加算して移動する (FR-8)。

        移動できない(着地)場合はロック処理を行う。
        """
        if self.game_over or self.paused:
            return False
        if self.board.can_place(self.current, row_offset=1):
            self.current.row += 1
            self.score += 1
            return True
        self._lock_and_advance()
        return False

    def hard_drop(self) -> int:
        """即座に着地位置まで落下させ、距離に応じたボーナスを加算する (FR-8, AC-7)。"""
        if self.game_over or self.paused:
            return 0
        distance = 0
        while self.board.can_place(self.current, row_offset=1):
            self.current.row += 1
            distance += 1
        self.score += distance * 2
        self._lock_and_advance()
        return distance

    def rotate_cw(self) -> bool:
        return self._try_rotate(+1)

    def rotate_ccw(self) -> bool:
        return self._try_rotate(-1)

    def _try_rotate(self, direction: int) -> bool:
        """回転を試み、必要なら簡易ウォールキックを行う (FR-5, AC-8)。"""
        if self.game_over or self.paused:
            return False
        new_rotation = (self.current.rotation + direction) % 4
        for row_kick, col_kick in WALL_KICK_OFFSETS:
            if self.board.can_place(
                self.current,
                rotation=new_rotation,
                row_offset=row_kick,
                col_offset=col_kick,
            ):
                self.current.rotation = new_rotation
                self.current.row += row_kick
                self.current.col += col_kick
                return True
        return False

    def toggle_pause(self) -> None:
        if not self.game_over:
            self.paused = not self.paused

    # ------------------------------------------------------------------
    # 内部: ロック・ライン消去・スコア・レベル
    # ------------------------------------------------------------------
    def _lock_and_advance(self) -> None:
        self.board.lock_piece(self.current)
        cleared = self.board.clear_lines()
        if cleared:
            self.score += _LINE_SCORE_TABLE.get(cleared, 0) * self.level
            self.lines_cleared += cleared
            self.level = 1 + self.lines_cleared // LINES_PER_LEVEL
        self._spawn_next()

    def tick(self) -> None:
        """重力による自然落下を1ステップ進める。着地していればロックする。"""
        if self.game_over or self.paused:
            return
        if self.board.can_place(self.current, row_offset=1):
            self.current.row += 1
        else:
            self._lock_and_advance()
