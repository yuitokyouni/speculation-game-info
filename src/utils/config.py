"""
config.py  –  Single source of truth for all model parameters.

Parameter sources:
  - Chartist params (M, S, B, C): Katahira & Chen (2019), Table 1
  - Switching params (beta):      Brock & Hommes (1998)
  - Fundamentalist (f_sensitivity): single free parameter κ
"""
from dataclasses import dataclass


@dataclass
class SimConfig:
    # ── Market participants ────────────────────────────────────────────
    N: int   = 301       # Katahira & Chen (2019): 301 agents
    T: int   = 10_000    # Simulation length

    # ── Chartist (Speculation Game) params ────────────────────────────
    # All from Katahira & Chen (2019)
    M: int   = 3         # Memory length
    S: int   = 2         # Strategies per agent
    B: int   = 9         # Board lot (min wealth unit)
    C: float = 3.0       # Cognitive threshold for quantization

    # ── Fundamentalist params ─────────────────────────────────────────
    # Continuous restoring force: demand = κ * (NAV - p)/NAV * qty
    # κ is the single free parameter for the fundamentalist side.
    NAV: float           = 1000.0   # Fundamental value
    nav_sigma: float     = 0.0      # NAV random walk std (0 = fixed)
    f_sensitivity: float = 1.0      # κ: restoring force scale

    # ── Strategy switching (Brock & Hommes 1998) ──────────────────────
    # β is the intensity of choice — the single free parameter from B&H.
    beta: float          = 1.0      # Intensity of choice
    n_c_init: float      = 0.5      # Initial Chartist fraction
    switching: bool      = True     # False = fixed n_c (exogenous)
    switch_freq: int     = 50       # Steps between switching events
    switch_warmup: int   = 500      # Warm-up before switching starts

    # ── Price dynamics ────────────────────────────────────────────────
    # Numerical safety only — should rarely bind in normal operation
    max_move: float  = 0.05         # Max price change per step (5%)
    p_floor:  float  = 10.0         # Minimum price floor

    # Safety caps on order quantity (prevents NaN from extreme wealth)
    max_qty: int   = 500            # Chartist cap
    f_max_qty: int = 500            # Fundamentalist cap

    # ── Initial conditions ────────────────────────────────────────────
    p0: float     = 1000.0          # Initial market price (= NAV)
    w0_max: float = 100.0           # Initial wealth ~ U[0, w0_max)

    # ── Validation (LightGBM) ─────────────────────────────────────────
    val_window: int      = 500      # Rolling window size
    val_step: int        = 100      # Step size for rolling
    predict_horizon: int = 10       # Days ahead for direction prediction

    # ── Random seed ───────────────────────────────────────────────────
    seed: int = 42
