"""Market engine: price formation and NAV process.

Price formation follows Katahira (2019) Eq.4:
    Δp = D(t) / N
where D(t) = Σ_i  action_i(t) × qty_i(t)

NAV process (Phase 1): fixed constant.
NAV process (Phase 2, future): geometric random walk.
"""
from __future__ import annotations
import numpy as np


def quantize_price_change(delta_p: float, C: float) -> int:
    """Map real price change to cognitive signal h(t) ∈ {-2,-1,0,1,2}.

    Implements Katahira (2019) Eq.6.
    """
    if   delta_p >  C:  return  2
    elif delta_p >  0:  return  1
    elif delta_p == 0:  return  0
    elif delta_p >= -C: return -1
    else:               return -2


class MarketEngine:
    """Handles price formation from excess demand.

    Args:
        N:   Number of agents (market depth denominator).
        p0:  Initial market price.
        C:   Cognitive threshold for price quantization.
        rng: Random generator (for future stochastic NAV).
    """

    def __init__(self, N: int, p0: float, C: float,
                 rng: np.random.Generator):
        self.N   = N
        self.C   = C
        self.rng = rng
        self.price     = p0
        self.cog_price = 0.0   # P(0) = 0

        # History ring-buffer: stores last M quantized changes
        self._history: list[int] = []

    # ------------------------------------------------------------------
    # Step
    # ------------------------------------------------------------------

    def step(self, orders: list[tuple[int, int]]) -> tuple[float, float, int]:
        """Process one time step.

        Args:
            orders: List of (action, qty) for every agent this step.
                    action ∈ {-1, 0, 1}, qty ≥ 0.

        Returns:
            (new_price, delta_p, h_t) where h_t is the quantized signal.
        """
        # Excess demand D(t) = Σ action_i × qty_i
        D = sum(a * q for a, q in orders)

        # Price formation (Eq.4) + floor to prevent negative prices
        delta_p = D / self.N
        self.price = max(1.0, self.price + delta_p)

        # Cognitive world update (Eq.6-7)
        h_t = quantize_price_change(delta_p, self.C)
        self.cog_price += h_t
        self._history.append(h_t)

        return self.price, delta_p, h_t

    def get_history(self, M: int) -> tuple[int, ...]:
        """Return the last M quantized price changes as a tuple.

        If fewer than M steps have elapsed, pad with zeros on the left.
        """
        hist = self._history[-M:] if len(self._history) >= M else (
            [0] * (M - len(self._history)) + self._history
        )
        return tuple(hist)


