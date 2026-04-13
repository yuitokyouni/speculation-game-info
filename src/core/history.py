"""履歴ビット列管理

Speculation Game では過去 M 期の量子化価格変動を
3進数のインデックスに変換してストラテジテーブルを引く。

量子化:
  log_return > +C  → +1
  log_return < -C  → -1
  otherwise        →  0
"""

from __future__ import annotations

from collections import deque


class History:
    """過去 M 期の量子化リターンを保持し、テーブルインデックスを返す。

    Parameters
    ----------
    memory : int
        参照する過去ステップ数 M
    threshold : float
        量子化閾値 C
    """

    def __init__(self, memory: int = 3, threshold: float = 0.02):
        self.memory = memory
        self.threshold = threshold
        self.buffer: deque[int] = deque([0] * memory, maxlen=memory)

    def quantize(self, log_return: float) -> int:
        if log_return > self.threshold:
            return 1
        elif log_return < -self.threshold:
            return -1
        else:
            return 0

    def update(self, log_return: float):
        self.buffer.append(self.quantize(log_return))

    @property
    def index(self) -> int:
        """現在の履歴を 3 進数インデックスに変換。

        {-1, 0, +1} → {0, 1, 2} にシフトしてから 3 進展開。
        """
        idx = 0
        for i, val in enumerate(self.buffer):
            idx += (val + 1) * (3**i)
        return idx
