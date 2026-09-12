"""2人対戦モード: お邪魔行の攻撃力算出・保留キュー・相殺・勝敗判定。

SPEC.md FR-17〜FR-22, NFR-14。`curses` はもちろん `ui_curses.py` にも非依存で、
`pytest` により単体テスト可能な設計とする(NFR-3の方針を踏襲)。
"""
from __future__ import annotations

import random
from typing import Dict, Optional

from .game import Game

# 同時消去行数(0〜4) -> 送信する攻撃力(お邪魔行数) (SPEC.md FR-19)。
# 単発消しは攻撃力0(攻撃にならない)。多消しほど1行あたりの効率が上がる非線形の
# テーブル。
ATTACK_TABLE: Dict[int, int] = {0: 0, 1: 0, 2: 1, 3: 2, 4: 4}

PLAYER_1 = 1
PLAYER_2 = 2


class BattleGame:
    """プレイヤー1・プレイヤー2それぞれの `Game` を保持する2人対戦の進行役。

    各プレイヤーの `Game` にロック時のフック(`on_locked`, `on_before_spawn`)を
    差し込み、お邪魔行の攻撃力算出・相殺・保留・盤面への反映(FR-20)を行う。
    """

    def __init__(self, rng: Optional[random.Random] = None) -> None:
        # お邪魔行の空き列抽選に使う乱数。ミノの出現順(各Gameが個別に持つ7-bag)
        # とは独立させる。
        self._rng = rng or random.Random()

        self.player1 = Game()
        self.player2 = Game()
        # 保留お邪魔行数(まだ盤面に反映されていない攻撃) (SPEC.md 7章 BattleState)。
        self.pending_garbage: Dict[int, int] = {PLAYER_1: 0, PLAYER_2: 0}

        self.player1.on_locked = lambda cleared: self._on_locked(PLAYER_1, cleared)
        self.player2.on_locked = lambda cleared: self._on_locked(PLAYER_2, cleared)
        self.player1.on_before_spawn = lambda: self._on_before_spawn(PLAYER_1)
        self.player2.on_before_spawn = lambda: self._on_before_spawn(PLAYER_2)

    def _game(self, player: int) -> Game:
        return self.player1 if player == PLAYER_1 else self.player2

    @staticmethod
    def _opponent(player: int) -> int:
        return PLAYER_2 if player == PLAYER_1 else PLAYER_1

    def _on_locked(self, player: int, cleared: int) -> None:
        """ロック時の攻撃力算出と相殺 (SPEC.md FR-19, FR-20の手順1・2)。

        消去が無かった(cleared=0)場合も攻撃力は0として同じ手順を通す
        (相殺の有無に関わらず、常にこの手順を適用する)。
        """
        attack = ATTACK_TABLE.get(cleared, 0)
        pending = self.pending_garbage[player]
        cancel = min(attack, pending)
        remaining_pending = pending - cancel
        remaining_attack = attack - cancel
        self.pending_garbage[player] = remaining_pending
        if remaining_attack > 0:
            opponent = self._opponent(player)
            self.pending_garbage[opponent] += remaining_attack

    def _on_before_spawn(self, player: int) -> None:
        """次のミノ出現直前に、残っている保留お邪魔行を盤面へ反映する (FR-20手順3)。"""
        pending = self.pending_garbage[player]
        if pending <= 0:
            return
        self._game(player).board.add_garbage_rows(pending, self._rng)
        self.pending_garbage[player] = 0

    @property
    def is_over(self) -> bool:
        """いずれかのプレイヤーがゲームオーバーになっていれば対戦終了 (FR-22)。"""
        return self.player1.game_over or self.player2.game_over

    @property
    def winner(self) -> Optional[int]:
        """勝者を返す (SPEC.md FR-22)。

        1 または 2 = 勝者のプレイヤー番号、0 = 両者同時にゲームオーバーで引き分け、
        None = 対戦継続中。
        """
        p1_over = self.player1.game_over
        p2_over = self.player2.game_over
        if p1_over and p2_over:
            return 0
        if p1_over:
            return PLAYER_2
        if p2_over:
            return PLAYER_1
        return None

    def update(self, elapsed_seconds: float) -> None:
        """両プレイヤーのライン消去エフェクトの経過時間を進める (FR-16, FR-20)。"""
        self.player1.update(elapsed_seconds)
        self.player2.update(elapsed_seconds)
