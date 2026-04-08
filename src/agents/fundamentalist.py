"""
fundamentalist.py – NAV-based mean-reverting agent.

Design: continuous restoring force model.
Each step, the fundamentalist contributes demand proportional to (NAV - p)/NAV.

Theoretical justification:
  - REIT markets have institutional arbitrageurs who scale position size
    proportional to the magnitude of discount/premium to NAV.
  - Single free parameter κ (sensitivity) controls the strength of
    mean-reversion.
"""
import numpy as np
from typing import Optional


class FundamentalistAgent:
    def __init__(self, agent_id: int, B: int, rng: np.random.Generator,
                 w0: Optional[float] = None, sensitivity: float = 1.0,
                 fitness_alpha: float = 0.05, max_qty: int = 500):
        self.id, self.B, self.rng = agent_id, B, rng
        self.max_qty = max_qty
        w_init = w0 if (w0 is not None and np.isfinite(w0)) else B + rng.uniform(0, 100)
        self.w           = float(max(w_init, float(B)))
        self.sensitivity = sensitivity   # κ
        self._fitness_ema: float   = 0.0
        self._fitness_alpha: float = fitness_alpha

    def get_demand(self, price: float, nav: float, n_fund: int = 1) -> float:
        """
        Continuous demand: κ * (NAV - price) / NAV * qty
        Positive = net buy (undervalued), Negative = net sell (overvalued).
        """
        if nav <= 0 or price <= 0:
            return 0.0
        misprice = (nav - price) / nav
        qty_max  = self.order_qty()
        demand   = self.sensitivity * misprice * qty_max
        return float(np.clip(demand, -qty_max, qty_max))

    def update_fitness(self, prev_price: float, new_price: float, nav: float):
        """Fitness: profit when price moves toward NAV."""
        if prev_price <= 0 or nav <= 0:
            return
        direction = np.sign(nav - prev_price)
        price_move = (new_price - prev_price) / prev_price
        roi = direction * price_move
        if np.isfinite(roi):
            self._fitness_ema = ((1 - self._fitness_alpha) * self._fitness_ema
                                 + self._fitness_alpha * roi)

    def order_qty(self) -> int:
        w = self.w if np.isfinite(self.w) else float(self.B)
        return max(1, min(self.max_qty, int(w // self.B)))

    def fitness(self) -> float:
        return self._fitness_ema

    def is_bankrupt(self) -> bool:
        return (not np.isfinite(self.w)) or (self.w < self.B)

    def reset(self, rng: np.random.Generator):
        self.w = float(self.B + rng.uniform(0, 100))
        self._fitness_ema = 0.0
