"""nav.py – NAV process (fixed or Gaussian random walk)."""
import numpy as np


class NAVProcess:
    def __init__(self, nav0: float = 1000.0, sigma: float = 0.0, seed: int = 42):
        self.nav    = nav0
        self.sigma  = sigma
        self.rng    = np.random.default_rng(seed)

    def step(self) -> float:
        if self.sigma > 0:
            self.nav *= np.exp(self.rng.normal(0, self.sigma))
        return self.nav
