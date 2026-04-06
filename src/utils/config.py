"""
config.py  –  Single source of truth for all model parameters.
"""
from dataclasses import dataclass, field


@dataclass
class SimConfig:
    # ── Market participants ────────────────────────────────────────────
    N: int   = 1000      # Total number of agents
    T: int   = 50_000   # Time steps

    # ── Chartist (Speculation Game) params ────────────────────────────
    M: int   = 5         # Memory length (history window)
    S: int   = 2         # Number of strategies per Chartist agent
    B: int   = 9         # Board lot (min wealth unit for 1 order)
    C: float = 3.0       # Cognitive threshold for history quantization

    # ── Fundamentalist params ─────────────────────────────────────────
    NAV: float        = 1000.0   # Fixed fundamental value (Phase 1)
    nav_sigma: float  = 0.0      # NAV random walk std (0 = fixed)
    f_threshold: float = 0.0    # (unused in v3 continuous model)
    f_sensitivity: float = 0.5  # κ: restoring force scale

    # ── Strategy switching (Brock & Hommes 1998) ──────────────────────
    beta: float          = 2.0    # Intensity of choice (lower = smoother)
    n_c_init: float      = 0.5   # Initial Chartist fraction
    switching: bool      = True  # False = fixed n_c (exogenous)
    switch_freq: int     = 200   # Steps between switching events
    switch_warmup: int   = 1000  # Warm-up steps before switching activates
    switch_max_delta: float = 0.05  # Max nc change per switching event

    # ── Price dynamics ────────────────────────────────────────────────
    max_move: float  = 0.02   # Max price change per step (fraction of p)
    p_floor:  float  = 10.0  # Minimum price floor

    max_qty: int = 50         # Hard cap on per-agent order quantity

    # ── Initial conditions ────────────────────────────────────────────
    p0: float  = 1000.0       # Initial market price (= NAV)
    w0_max: float = 100.0     # Uniform initial wealth U[0, w0_max)

    # ── Validation (LightGBM) ─────────────────────────────────────────
    val_window: int   = 250   # Rolling window for accuracy calculation
    val_step: int     = 50    # Step size for rolling window
    predict_horizon: int = 10 # Days ahead for direction prediction

    # ── Random seed ───────────────────────────────────────────────────
    seed: int = 42
