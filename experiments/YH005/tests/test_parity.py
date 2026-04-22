"""YH005: Reference ↔ Vectorized bit-parity tests + invariants.

§8.1 の受け入れ基準に従い、以下を検証:
  - 5 seeds × (N=30, M=3, S=2, T=300, B=9, C=3.0) で全出力キーが np.array_equal
  - S=1 の parity (3 seeds)
  - Null A (history_mode='exogenous') の parity
  - Null B (decision_mode='random')  の parity
  - 毎ステップ buy+sell+active+passive+idle == N の不変条件
  - cognitive_prices == cumsum(h_series) の不変条件
  - 同一 seed での決定性
  - seed 感度 (seed を変えると prices が変わる)

pytest 実行:
  cd experiments/YH005
  python -m pytest tests/ -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from model import run_reference
from simulate import simulate


PARAMS_DEFAULT = dict(N=30, M=3, S=2, T=300, B=9, C=3.0)
PARITY_KEYS = (
    "prices",
    "h_series",
    "cognitive_prices",
    "final_wealth",
    "num_buy",
    "num_sell",
    "num_active_hold",
    "num_passive_hold",
)


def _assert_parity(ref: dict, vec: dict, ctx: str):
    for k in PARITY_KEYS:
        assert np.array_equal(ref[k], vec[k]), (
            f"{ctx}: key '{k}' mismatch; "
            f"ref[{k}][:5]={ref[k][:5] if hasattr(ref[k], '__len__') else ref[k]}, "
            f"vec[{k}][:5]={vec[k][:5] if hasattr(vec[k], '__len__') else vec[k]}"
        )
    assert ref["num_substitutions"] == vec["num_substitutions"], (
        f"{ctx}: num_substitutions mismatch "
        f"ref={ref['num_substitutions']} vec={vec['num_substitutions']}"
    )
    assert ref["total_wealth"] == vec["total_wealth"], (
        f"{ctx}: total_wealth mismatch "
        f"ref={ref['total_wealth']} vec={vec['total_wealth']}"
    )


@pytest.mark.parametrize("seed", [1, 2, 7, 42, 100])
def test_parity_default(seed: int):
    ref = run_reference(seed=seed, **PARAMS_DEFAULT)
    vec = simulate(seed=seed, **PARAMS_DEFAULT)
    _assert_parity(ref, vec, f"default seed={seed}")


@pytest.mark.parametrize("seed", [1, 2, 7])
def test_parity_S1(seed: int):
    params = dict(PARAMS_DEFAULT)
    params["S"] = 1
    ref = run_reference(seed=seed, **params)
    vec = simulate(seed=seed, **params)
    _assert_parity(ref, vec, f"S=1 seed={seed}")


def test_parity_null_a():
    ref = run_reference(seed=1, history_mode="exogenous", **PARAMS_DEFAULT)
    vec = simulate(seed=1, history_mode="exogenous", **PARAMS_DEFAULT)
    _assert_parity(ref, vec, "Null A")


def test_parity_null_b():
    ref = run_reference(seed=1, decision_mode="random", **PARAMS_DEFAULT)
    vec = simulate(seed=1, decision_mode="random", **PARAMS_DEFAULT)
    _assert_parity(ref, vec, "Null B")


def test_action_invariant():
    """buy + sell + active_hold + passive_hold + idle == N, idle >= 0"""
    res = simulate(seed=42, **PARAMS_DEFAULT)
    N = PARAMS_DEFAULT["N"]
    total_non_idle = (
        res["num_buy"] + res["num_sell"] + res["num_active_hold"] + res["num_passive_hold"]
    )
    assert (total_non_idle <= N).all(), "sum of 4 action kinds exceeds N"
    idle = N - total_non_idle
    assert (idle >= 0).all(), "idle count went negative"


def test_cognitive_cumsum():
    """cognitive_prices[t] == cumsum(h_series)[t]"""
    res = simulate(seed=42, **PARAMS_DEFAULT)
    expected = np.cumsum(res["h_series"].astype(np.int64))
    assert np.array_equal(res["cognitive_prices"], expected)


def test_determinism():
    """Same seed → identical output."""
    r1 = simulate(seed=42, **PARAMS_DEFAULT)
    r2 = simulate(seed=42, **PARAMS_DEFAULT)
    for k in PARITY_KEYS:
        assert np.array_equal(r1[k], r2[k]), f"non-determinism in {k}"


def test_seed_sensitivity():
    """Different seed → different prices."""
    r1 = simulate(seed=42, **PARAMS_DEFAULT)
    r2 = simulate(seed=43, **PARAMS_DEFAULT)
    assert not np.array_equal(r1["prices"], r2["prices"])
