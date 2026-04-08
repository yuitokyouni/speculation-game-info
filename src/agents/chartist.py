"""chartist.py – Speculation Game agent (Katahira & Chen 2019)."""
import numpy as np
from itertools import product
from typing import Optional

_HISTORY_CACHE: dict = {}

def _all_histories(M: int) -> list:
    if M not in _HISTORY_CACHE:
        _HISTORY_CACHE[M] = list(product(range(-2, 3), repeat=M))
    return _HISTORY_CACHE[M]


class ChartistAgent:
    def __init__(self, agent_id: int, M: int, S: int, B: int,
                 rng: np.random.Generator, w0: Optional[float] = None,
                 fitness_alpha: float = 0.05, max_qty: int = 50):
        self.id   = agent_id
        self.M, self.S, self.B = M, S, B
        self.max_qty = max_qty
        self.rng  = rng
        w_init = w0 if (w0 is not None and np.isfinite(w0)) else B + rng.uniform(0, 100)
        self.w = float(max(w_init, float(B)))

        self.strategies      = self._init_strategies()
        self.strategy_gains  = np.zeros(S, dtype=float)
        self.active_strategy = 0

        self.position: int          = 0
        self.open_price_cog: float  = 0.0
        self.open_price_real: float = 0.0
        self.open_qty: int          = 0

        # EMA fitness (smoothed recent PnL rate-of-return)
        self._fitness_ema: float   = 0.0
        self._fitness_alpha: float = fitness_alpha

    def decide(self, history: tuple) -> int:
        recommended = int(self.strategies[self.active_strategy].get(history, 0))
        if self.position == 0:
            return recommended
        if recommended == -self.position:
            return recommended
        return 0

    def order_qty(self) -> int:
        w = self.w if np.isfinite(self.w) else float(self.B)
        return max(1, min(self.max_qty, int(w // self.B)))

    def open_position(self, action: int, qty: int,
                      cog_price: float, real_price: float):
        self.position        = action
        self.open_qty        = qty
        self.open_price_cog  = cog_price
        self.open_price_real = real_price

    def close_position(self, cog_price: float, real_price: float) -> float:
        if self.position == 0:
            return 0.0
        cog_gain = self.position * (cog_price - self.open_price_cog)
        self.strategy_gains += cog_gain
        real_gain = self.position * (real_price - self.open_price_real)
        delta_w   = real_gain * self.open_qty
        if np.isfinite(delta_w):
            self.w += delta_w
            # Return-on-investment as fitness signal (normalized by open price)
            if self.open_price_real > 0:
                roi = real_gain / self.open_price_real
                self._fitness_ema = ((1 - self._fitness_alpha) * self._fitness_ema
                                     + self._fitness_alpha * roi)
        self.active_strategy = int(np.argmax(self.strategy_gains))
        self.position = 0
        return delta_w

    def fitness(self) -> float:
        """EMA of realized ROI – used for Brock-Hommes switching."""
        return self._fitness_ema

    def is_bankrupt(self) -> bool:
        return (not np.isfinite(self.w)) or (self.w < self.B)

    def reset(self, rng: np.random.Generator):
        self.w               = float(self.B + rng.uniform(0, 100))
        self.strategies      = self._init_strategies()
        self.strategy_gains  = np.zeros(self.S)
        self.active_strategy = 0
        self.position        = 0
        self._fitness_ema    = 0.0

    def _init_strategies(self) -> list:
        histories = _all_histories(self.M)
        return [
            {h: int(self.rng.integers(-1, 2)) for h in histories}
            for _ in range(self.S)
        ]
