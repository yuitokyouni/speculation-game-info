"""
history.py  –  Quantized price history H(t) used by Chartist agents.

Katahira & Chen (2019) Eq.6:
    h(t) = 2  if Δp >  C
           1  if 0 < Δp <=  C
           0  if Δp == 0
          -1  if -C <= Δp < 0
          -2  if Δp < -C
"""
import numpy as np
from collections import deque


class PriceHistory:
    """
    Maintains a rolling window of quantized price movements h(t).
    Shared (read-only) by all Chartist agents.
    """

    def __init__(self, M: int, C: float, seed: int = 42):
        self.M = M
        self.C = C
        # Random initialisation as in the original paper
        rng = np.random.default_rng(seed)
        init = rng.integers(-2, 3, size=M)   # values in {-2,-1,0,1,2}
        self._buf: deque[int] = deque(init, maxlen=M)

    # ── Public interface ──────────────────────────────────────────────

    def update(self, delta_p: float) -> int:
        """Quantize delta_p, append to buffer, return h(t)."""
        h = self._quantize(delta_p)
        self._buf.append(h)
        return h

    def get(self) -> tuple[int, ...]:
        """Return current H(t) as a tuple (hashable key for strategy table)."""
        return tuple(self._buf)

    # ── Internal ──────────────────────────────────────────────────────

    def _quantize(self, delta_p: float) -> int:
        if delta_p > self.C:
            return 2
        elif delta_p > 0:
            return 1
        elif delta_p == 0:
            return 0
        elif delta_p >= -self.C:
            return -1
        else:
            return -2
