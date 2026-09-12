"""固定タイムステップ(アキュムレータ方式)のゲームループ制御 (SPEC.md NFR-8)。

curses等のUIには依存しない純粋なロジック。
「ゲームロジックの更新頻度」と「画面描画の頻度」を分離することで、
実行環境の処理速度やフレームレートのばらつきに関わらず、
ゲームの進行(重力による自然落下など)を一定間隔で保証する
(いわゆる Fix Your Timestep パターンの簡易実装)。
"""
from __future__ import annotations

from dataclasses import dataclass, field

# 1フレームで蓄積される経過時間が大きすぎる場合、更新処理が延々と
# 追いつこうとして画面が固まって見える「スパイラル・オブ・デス」を防ぐため、
# アキュムレータに加算する経過時間には上限を設ける。
MAX_FRAME_TIME = 0.25  # 秒


@dataclass
class FixedTimestepLoop:
    """固定タイムステップでの更新(tick)回数を計算するアキュムレータ。

    使い方:
        loop = FixedTimestepLoop(update_interval=game.gravity_interval())
        ...メインループ内で毎フレーム...
        loop.update_interval = game.gravity_interval()  # レベルアップ等で変化しうる
        for _ in range(loop.advance(elapsed_seconds)):
            game.tick()
    """

    update_interval: float
    _accumulator: float = field(default=0.0, repr=False)

    def advance(self, elapsed_seconds: float) -> int:
        """経過時間を蓄積し、今回実行すべき更新(tick)回数を返す。

        呼び出し時点の `update_interval` を用いて計算するため、
        呼び出し前に `update_interval` を書き換えれば、次のadvance呼び出しから
        新しい間隔が反映される(例: レベルアップで重力が速くなるケース)。
        """
        if elapsed_seconds < 0:
            elapsed_seconds = 0.0
        # スパイラル・オブ・デス対策: 1回に蓄積できる経過時間を制限する。
        elapsed_seconds = min(elapsed_seconds, MAX_FRAME_TIME)

        self._accumulator += elapsed_seconds
        interval = max(self.update_interval, 1e-6)

        steps = 0
        while self._accumulator >= interval:
            self._accumulator -= interval
            steps += 1
        return steps

    def reset(self) -> None:
        """アキュムレータをゼロに戻す(一時停止からの復帰時などに使用)。"""
        self._accumulator = 0.0


@dataclass
class FrameLimiter:
    """目標フレームレートを維持するための「眠るべき時間」を計算する。

    実際の time.sleep 呼び出しは行わず、値の計算のみを行う(テスト容易性のため)。
    """

    target_fps: float = 50.0

    @property
    def frame_budget(self) -> float:
        """1フレームあたりに許容される時間(秒)。"""
        return 1.0 / max(self.target_fps, 1e-6)

    def sleep_duration(self, elapsed_this_frame: float) -> float:
        """このフレームの処理に `elapsed_this_frame` 秒かかった場合に、
        目標フレームレートを維持するために眠るべき時間(秒)を返す。

        処理が予算(frame_budget)を超えていた場合は0を返す(負値にはしない)。
        """
        if elapsed_this_frame < 0:
            elapsed_this_frame = 0.0
        return max(0.0, self.frame_budget - elapsed_this_frame)
