"""Type C エージェント (Chartist): 過去価格パターンに基づく意思決定

Katahira & Chen (2019) Section 2.1 に準拠。
エージェントは過去 M 期の量子化価格変動 H(t) をキーとして
ストラテジテーブルから {buy, sell} シグナルを取得する。
ラウンドトリップ制約: 反対シグナルが出るまで hold(0)。
"""

from __future__ import annotations

import numpy as np


class TypeCAgent:
    """Chartist エージェント。

    Parameters
    ----------
    n_strategies : int
        各エージェントが保持するストラテジ数 (default: 2)
    memory : int
        参照する過去ステップ数 M
    threshold : float
        量子化閾値 C — |log_return| > C なら ±1, さもなくば 0
    rng : np.random.Generator
        乱数生成器
    """

    def __init__(
        self,
        n_strategies: int = 2,
        memory: int = 3,
        threshold: float = 0.02,
        rng: np.random.Generator | None = None,
    ):
        self.memory = memory
        self.threshold = threshold
        self.rng = rng or np.random.default_rng()

        n_patterns = 3**memory  # 各ステップ {-1, 0, +1}
        # ストラテジテーブル: shape (n_strategies, n_patterns), 値は {-1, +1}
        self.strategies = self.rng.choice(
            [-1, 1], size=(n_strategies, n_patterns)
        )
        self.scores = np.zeros(n_strategies)
        self.active = 0  # 現在使用中のストラテジ index
        self.position = 0  # 0: flat, +1: long, -1: short

    def get_signal(self, history_index: int) -> int:
        """現在のストラテジが示すシグナル。"""
        return int(self.strategies[self.active, history_index])

    def decide(self, history_index: int) -> int:
        """ラウンドトリップ制約を適用した行動を返す。

        Returns
        -------
        int : {-1, 0, +1}
        """
        signal = self.get_signal(history_index)

        if self.position == 0:
            # flat → シグナル通りにエントリ
            self.position = signal
            return signal
        elif self.position == signal:
            # 同方向 → hold
            return 0
        else:
            # 反対シグナル → 手仕舞い
            self.position = 0
            return -signal  # ポジションの反対方向

    def update_scores(self, history_index: int, realized_return: float):
        """仮想スコア更新: 各ストラテジのシグナルと実現リターンの積。"""
        for i in range(len(self.strategies)):
            s = self.strategies[i, history_index]
            self.scores[i] += s * realized_return
        self.active = int(np.argmax(self.scores))
