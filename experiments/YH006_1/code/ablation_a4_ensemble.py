"""S6r A4 ablation runner — C2_A4 / C3_A4 × 100 trial (Mac 側専用).

S6r plan §1:
  0. C3 等価チェック (fail-fast): shuffle-off 経路 (素の OrderTrackingSaver) が
     既存挙動と semantic 一致するか、seed=1000 で 1 run 確認。
     A4 は saver hook 方式で Phase 1 非改変だが、run_experiment.py の分岐追加が
     既存経路を壊していないことをデータで確定する
  1. A4 smoke: C3_A4 seed=1000 を 1 run —
     n_shuffles == main_steps // K (=12)、runtime < 1200s (stop trigger)、
     q 多様性が退化しない
  2. determinism guard: C3_A4 seed=1000 × 2 独立 run、semantic 一致
     (shuffle RNG が seed 派生で再現することの検証)
  3. C2_A4 / C3_A4 × seed 1000-1099 並列実行 → data/C2_A4/, data/C3_A4/

K (shuffle_period) = 121 (plan §0.3、= S6 τ_max)。

Run (Mac):
  cd experiments/YH006_1
  python -m code.ablation_a4_ensemble --determinism-only   # §0-§2 のみ
  python -m code.ablation_a4_ensemble                      # 200 trial
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
YH006_1 = HERE.parent
for _p in (str(YH006_1), str(HERE)):
    while _p in sys.path:
        sys.path.remove(_p)
    sys.path.insert(0, _p)

from config import CONDITIONS, ENSEMBLE_SEED_BASE, ENSEMBLE_N_TRIALS, LOB_PARAMS  # noqa: E402
from parallel import run_parallel_trials, default_n_workers  # noqa: E402

DATA_DIR = YH006_1 / "data"
LOGS_DIR = YH006_1 / "logs"

A4_CONDS = ["C2_A4", "C3_A4"]
BASELINE_COND = "C3"
SHUFFLE_PERIOD = 121  # plan §0.3 (= S6 τ_max、persistence と同 timescale)
EXPECTED_SHUFFLES = LOB_PARAMS["main_steps"] // SHUFFLE_PERIOD  # 1500//121 = 12
SMOKE_RUNTIME_LIMIT = 1200.0  # plan §2 stop trigger
ENSEMBLE_MEAN_RUNTIME_LIMIT = 900.0  # plan §2 (= ~2x C3 mean)


def setup_logger() -> logging.Logger:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    (LOGS_DIR / "runtime").mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("S6r")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fh = logging.FileHandler(
        LOGS_DIR / "runtime" / f"{ts}_S6r_a4_ensemble.log", encoding="utf-8",
    )
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    return logger


# ---------------------------------------------------------------------------
# §0 C3 等価チェック — shuffle-off 経路の非破壊確認 (S6 と同 pattern)
# ---------------------------------------------------------------------------

def c3_equivalence_check(seed: int, logger: logging.Logger) -> bool:
    from run_experiment import run_lob_trial
    ref_dir = DATA_DIR / BASELINE_COND
    if not (ref_dir / f"trial_{seed:04d}.parquet").exists():
        logger.error(f"[c3-check] archived C3 data なし: {ref_dir}")
        return False

    logger.info(f"[c3-check] {BASELINE_COND} seed={seed} を A4 分岐追加後 code で実行")
    out_dir = DATA_DIR / "_guard_a4_c3_equiv"
    out_dir.mkdir(parents=True, exist_ok=True)
    run_lob_trial(BASELINE_COND, seed).to_parquets(out_dir)

    cols_rt = ["agent_id", "rt_idx", "t_open", "t_close", "horizon",
               "direction", "q", "delta_g"]
    rt_new = pd.read_parquet(out_dir / f"trial_{seed:04d}.parquet")[cols_rt].to_numpy()
    rt_ref = pd.read_parquet(ref_dir / f"trial_{seed:04d}.parquet")[cols_rt].to_numpy()
    rt_match = np.array_equal(rt_new, rt_ref)

    cols_lt = ["t_birth", "t_end", "censored"]
    lt_new = pd.read_parquet(out_dir / f"lifetimes_{seed:04d}.parquet")
    lt_ref = pd.read_parquet(ref_dir / f"lifetimes_{seed:04d}.parquet")
    lt_match = (
        sorted(map(tuple, lt_new[cols_lt].to_numpy().tolist()))
        == sorted(map(tuple, lt_ref[cols_lt].to_numpy().tolist()))
    )
    logger.info(
        f"[c3-check] rt_df: {'MATCH' if rt_match else 'MISMATCH'} | "
        f"lifetimes: {'MATCH' if lt_match else 'MISMATCH'}"
    )
    return rt_match and lt_match


# ---------------------------------------------------------------------------
# §1 A4 smoke — shuffle 発火 + runtime stop trigger (plan §1.4 / §2)
# ---------------------------------------------------------------------------

def a4_smoke(seed: int, logger: logging.Logger):
    from run_experiment import run_lob_trial
    logger.info(f"[smoke] C3_A4 seed={seed} K={SHUFFLE_PERIOD} を 1 run")
    res = run_lob_trial("C3_A4", seed, shuffle_period=SHUFFLE_PERIOD)
    # (1) shuffle 発火回数 = main_steps // K
    assert res.n_shuffles == EXPECTED_SHUFFLES, \
        f"n_shuffles {res.n_shuffles} != expected {EXPECTED_SHUFFLES} — 発火規則の実装ミス疑い"
    # (2) runtime stop trigger (A3 型スパイラルの検知)
    assert res.runtime_sec < SMOKE_RUNTIME_LIMIT, \
        f"runtime {res.runtime_sec:.0f}s >= {SMOKE_RUNTIME_LIMIT:.0f}s — plan §2 stop trigger"
    # (3) q 多様性が退化しない (wealth → q 経路が生きている)
    if len(res.rt_df) > 0:
        n_q = res.rt_df["q"].nunique()
        assert n_q >= 2, f"q unique {n_q} < 2 — q 経路退化疑い"
    logger.info(
        f"[smoke] PASS: runtime={res.runtime_sec:.1f}s n_rt={res.n_round_trips} "
        f"n_sub={res.n_substitutions} n_shuffles={res.n_shuffles}"
    )
    return res


# ---------------------------------------------------------------------------
# §2 determinism guard — C3_A4 seed=1000 × 2 semantic 一致
# ---------------------------------------------------------------------------

def determinism_guard_a4(seed: int, logger: logging.Logger) -> bool:
    from run_experiment import run_lob_trial
    a_dir = DATA_DIR / "_guard_a4_a"
    b_dir = DATA_DIR / "_guard_a4_b"
    a_dir.mkdir(parents=True, exist_ok=True)
    b_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"[guard] C3_A4 seed={seed} × 2 runs (K={SHUFFLE_PERIOD})")
    run_lob_trial("C3_A4", seed, shuffle_period=SHUFFLE_PERIOD).to_parquets(a_dir)
    run_lob_trial("C3_A4", seed, shuffle_period=SHUFFLE_PERIOD).to_parquets(b_dir)

    cols_rt = ["agent_id", "rt_idx", "t_open", "t_close", "horizon",
               "direction", "q", "delta_g"]
    rt_a = pd.read_parquet(a_dir / f"trial_{seed:04d}.parquet")[cols_rt].to_numpy()
    rt_b = pd.read_parquet(b_dir / f"trial_{seed:04d}.parquet")[cols_rt].to_numpy()
    rt_match = np.array_equal(rt_a, rt_b)
    lt_a = pd.read_parquet(a_dir / f"lifetimes_{seed:04d}.parquet")
    lt_b = pd.read_parquet(b_dir / f"lifetimes_{seed:04d}.parquet")
    lt_match = lt_a.equals(lt_b)
    logger.info(
        f"[guard] rt_df: {'MATCH' if rt_match else 'MISMATCH'} | "
        f"lifetimes: {'MATCH' if lt_match else 'MISMATCH'}"
    )
    return rt_match and lt_match


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-base", type=int, default=ENSEMBLE_SEED_BASE)
    parser.add_argument("--n-trials", type=int, default=ENSEMBLE_N_TRIALS)
    parser.add_argument("--n-workers", type=int, default=None)
    parser.add_argument("--skip-c3-check", action="store_true")
    parser.add_argument("--skip-determinism", action="store_true")
    parser.add_argument("--determinism-only", action="store_true")
    args = parser.parse_args()

    logger = setup_logger()
    n_workers = args.n_workers or default_n_workers()
    seeds: List[int] = list(range(args.seed_base, args.seed_base + args.n_trials))
    for c in A4_CONDS:
        assert CONDITIONS[c].wealth_shuffle, f"{c} is not A4 cond"

    logger.info("=" * 70)
    logger.info(
        f"S6r A4 ablation — conds={A4_CONDS}, K={SHUFFLE_PERIOD}, "
        f"n_trials={args.n_trials}, n_workers={n_workers}"
    )
    logger.info("=" * 70)

    # §0 C3 等価チェック (shuffle-off 経路の非破壊、fail-fast)
    c3_pass = True
    if not args.skip_c3_check:
        c3_pass = c3_equivalence_check(args.seed_base, logger)
        if not c3_pass:
            logger.error(
                "[c3-check] FAILED — A4 分岐追加が既存経路を破壊。"
                "ensemble を中止して Yuito 相談 (plan §2 stop trigger)"
            )
            return

    # §1 A4 smoke (assertion fail は例外で停止 = plan §2 stop trigger)
    a4_smoke(args.seed_base, logger)

    # §2 determinism guard
    determinism_pass = True
    if not args.skip_determinism:
        determinism_pass = determinism_guard_a4(args.seed_base, logger)
        if not determinism_pass:
            logger.error("[guard] FAILED — shuffle RNG 配線ミス疑い、Yuito 相談")
            return

    if args.determinism_only:
        logger.info("--determinism-only mode、§0-§2 完了して終了")
        return

    # §3 ensemble (C2_A4 → C3_A4 の順、各 100 trial)
    all_results = {}
    for cond in A4_CONDS:
        cond_dir = DATA_DIR / cond
        results = run_parallel_trials(
            cond, seeds, cond_dir, n_workers, logger,
            shuffle_period=SHUFFLE_PERIOD,
        )
        errs = [(s, err) for (s, rt, _, _, err) in results if err]
        if errs:
            logger.error(f"[main] {cond}: {len(errs)} trial errored — 確認要")
        runtimes = [rt for (s, rt, _, _, err) in results if err is None]
        mean_rt = float(np.mean(runtimes)) if runtimes else 0.0
        if mean_rt > ENSEMBLE_MEAN_RUNTIME_LIMIT:
            logger.error(
                f"[main] {cond}: mean runtime {mean_rt:.0f}s > "
                f"{ENSEMBLE_MEAN_RUNTIME_LIMIT:.0f}s — plan §2 stop trigger 該当、"
                "diff に記録して Yuito 相談"
            )
        all_results[cond] = {
            "n_errors": len(errs),
            "mean_runtime_sec": mean_rt,
            "runtimes_sec": {str(s): rt for (s, rt, _, _, err) in results
                             if err is None},
        }

    summary = {
        "stage": "S6r-mac",
        "conds": A4_CONDS,
        "shuffle_period": SHUFFLE_PERIOD,
        "expected_shuffles_per_trial": EXPECTED_SHUFFLES,
        "n_trials": args.n_trials,
        "seed_base": args.seed_base,
        "n_workers": n_workers,
        "c3_equivalence_pass": c3_pass,
        "determinism_pass": determinism_pass,
        "results": all_results,
        "timestamp": datetime.now().isoformat(),
    }
    with open(LOGS_DIR / "S6r_mac_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    logger.info(f"summary written: {LOGS_DIR / 'S6r_mac_summary.json'}")

    logger.info("=" * 70)
    logger.info("S6r A4 ensemble (sim part) complete. git add data/ logs/ && commit && push")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
