"""Type V エージェント (Value-signal agent): 外部バリューシグナルに基づく意思決定

Chartist が過去の価格パターンのみを使うのに対し、
Type V は外部の「ファンダメンタル価値」シグナルと現在価格の乖離を利用する。

情報構造の対比:
  Type C — 内生的情報 (過去価格)
  Type V — 外生的情報 (バリューシグナル)
"""

from __future__ import annotations

import numpy as np


class TypeVAgent:
    """Value-signal エージェント。

    Parameters
    ----------
    sensitivity : float
        乖離に対する反応感度。demand ∝ sensitivity * (value - price) / price
    noise_std : float
        シグナルのノイズ標準偏差（情報の不完全性）
    rng : np.random.Generator
        乱数生成器
    """

    def __init__(
        self,
        sensitivity: float = 0.05,
        noise_std: float = 0.01,
        rng: np.random.Generator | None = None,
    ):
        self.sensitivity = sensitivity
        self.noise_std = noise_std
        self.rng = rng or np.random.default_rng()

    def decide(self, price: float, value_signal: float) -> int:
        """バリューシグナルと価格の乖離から行動を決定。

        Returns
        -------
        int : {-1, 0, +1}
        """
        perceived_value = value_signal * (
            1.0 + self.rng.normal(0, self.noise_std)
        )
        gap = (perceived_value - price) / price
        demand = self.sensitivity * gap

        if demand > 0.01:
            return 1
        elif demand < -0.01:
            return -1
        else:
            return 0
