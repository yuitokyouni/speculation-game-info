"""Brock-Hommes (1998) 型の内生的スイッチング

エージェントは各タイプの直近パフォーマンス（fitness）を比較し、
離散選択モデルで所属タイプを確率的に切り替える。

n_c(t) = exp(β * U_c) / (exp(β * U_c) + exp(β * U_v))

β = 0: 一様分布 (n_c = 0.5)
β → ∞: 勝者総取り
"""

from __future__ import annotations

import numpy as np


def compute_fractions(
    fitness_c: float,
    fitness_v: float,
    beta: float,
) -> float:
    """Type C の比率 n_c を返す。

    Parameters
    ----------
    fitness_c : float
        Type C の fitness (EMA of realized ROI など)
    fitness_v : float
        Type V の fitness
    beta : float
        選択強度 (intensity of choice)

    Returns
    -------
    float : n_c ∈ (0, 1)
    """
    # overflow 防止のため max を引く
    max_f = max(fitness_c, fitness_v)
    exp_c = np.exp(beta * (fitness_c - max_f))
    exp_v = np.exp(beta * (fitness_v - max_f))
    n_c = exp_c / (exp_c + exp_v)
    return float(n_c)


class FitnessTracker:
    """各タイプの fitness を EMA で追跡する。"""

    def __init__(self, alpha: float = 0.05):
        """
        Parameters
        ----------
        alpha : float
            EMA の減衰率。大きいほど直近重視。
        """
        self.alpha = alpha
        self.fitness_c = 0.0
        self.fitness_v = 0.0

    def update(self, roi_c: float, roi_v: float):
        self.fitness_c += self.alpha * (roi_c - self.fitness_c)
        self.fitness_v += self.alpha * (roi_v - self.fitness_v)
