"""
fundamentalist.py – NAV-based mean-reverting agent.

Design: continuous restoring force model.
Each step, the fundamentalist contributes demand proportional to (NAV - p).
No round-trip constraint – they are market makers / long-term holders who
continuously adjust exposure based on current mispricing.

This is consistent with how institutional arbitrageurs actually behave in
REIT markets: they scale position size to the magnitude of the discount/premium.
"""
import numpy as np
from typing import Optional


class FundamentalistAgent:
    def __init__(self, agent_id: int, B: int, rng: np.random.Generator,
                 w0: Optional[float] = None, sensitivity: float = 0.5,
                 fitness_alpha: float = 0.05):
        self.id, self.B, self.rng = agent_id, B, rng
        w_init = w0 if (w0 is not None and np.isfinite(w0)) else B + rng.uniform(0, 100)
        self.w           = float(max(w_init, float(B)))
        self.sensitivity = sensitivity   # κ: scales restoring force
        self._fitness_ema: float   = 0.0
        self._fitness_alpha: float = fitness_alpha
        self._prev_p: float        = 0.0

    def get_demand(self, price: float, nav: float) -> float:
        """
        Returns continuous demand (can be fractional).
        demand = sensitivity * (NAV - price) / NAV * max_qty
        Positive = net buy, Negative = net sell.
        """
        if nav <= 0 or price <= 0:
            return 0.0
        misprice = (nav - price) / nav        # positive when undervalued
        qty_max  = self.order_qty()  # already capped at 50
        demand   = self.sensitivity * misprice * qty_max
        return float(np.clip(demand, -qty_max, qty_max))

    def update_fitness(self, prev_price: float, new_price: float, nav: float):
        """
        Update fitness: fundamentalist profits when price moves toward NAV.
        """
        if prev_price <= 0 or nav <= 0:
            return
        direction = np.sign(nav - prev_price)   # +1 if was undervalued
        price_move = (new_price - prev_price) / prev_price
        roi = direction * price_move             # + if price moved toward NAV
        if np.isfinite(roi):
            self._fitness_ema = ((1 - self._fitness_alpha) * self._fitness_ema
                                 + self._fitness_alpha * roi)

    def order_qty(self) -> int:
        w = self.w if np.isfinite(self.w) else float(self.B)
        return max(1, min(50, int(w // self.B)))

    # Keep round-trip interface for switching compatibility (unused but harmless)
    def open_position(self, action: int, qty: int, cog_price: float, real_price: float):
        pass

    def close_position(self, cog_price: float, real_price: float) -> float:
        return 0.0

    def fitness(self) -> float:
        return self._fitness_ema

    def is_bankrupt(self) -> bool:
        return (not np.isfinite(self.w)) or (self.w < self.B)

    def reset(self, rng: np.random.Generator):
        self.w = float(self.B + rng.uniform(0, 100))
        self._fitness_ema = 0.0
