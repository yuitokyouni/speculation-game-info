"""市場メカニズム: 価格決定とラウンドトリップ取引制約

Katahira & Chen (2019) Section 2.2 に準拠。
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass


@dataclass
class MarketState:
    price: float
    log_return: float
    excess_demand: int


class Market:
    """Speculation Game の市場。

    価格更新:
        P(t+1) = P(t) * exp(excess_demand / liquidity)
    """

    def __init__(self, initial_price: float = 1000.0, liquidity: float = 1e4):
        self.price = initial_price
        self.liquidity = liquidity
        self.log_return = 0.0

    def update(self, actions: np.ndarray) -> MarketState:
        """エージェント行動の集計 → 価格更新。

        Parameters
        ----------
        actions : array of {-1, 0, +1}
            各エージェントの行動 (sell, hold, buy)

        Returns
        -------
        MarketState
        """
        excess_demand = int(actions.sum())
        old_price = self.price
        self.price = old_price * np.exp(excess_demand / self.liquidity)
        self.log_return = np.log(self.price / old_price)
        return MarketState(
            price=self.price,
            log_return=self.log_return,
            excess_demand=excess_demand,
        )
