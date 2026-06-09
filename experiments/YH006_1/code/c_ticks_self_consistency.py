"""S5.9 P2 — c_ticks self-consistency robustness (Mac 側専用).

c_ticks=28 は C1 (FCN only、SG 投入前) の mid 揺らぎで較正された値
(`experiments/YH006/calibrate_c_ticks.py`、3 × median|Δmid|_nz)。SG 投入後の
C2/C3 market では price dynamics が変わるため、この閾値は post-SG market と
自己無撞着とは限らない (固定点問題)。

本 script は共有コード (run_experiment.py / config.py / speculation_agent.py) を
**一切変更せず**、config 構築のみ run_lob_trial_smoke (run_experiment.py:232-275) を
mirror した self-contained runner で:
  Phase A: c_ticks=28 で C2/C3 を走らせ post-SG price から c_ticks_recal を計測
  Phase B: pooled c_ticks_recal で再走、round-trip 活動量 n_rt の変化を計測
Δn_rt で H_friction (S5.8 主張: fill/matching 律速) / H_trigger を判別する。

S6 (C3_A3) と並走可能: 出力は logs/S5.9_* のみ、C3_A3 と非衝突。

Run (Mac):
  cd experiments/YH006_1
  python -m code.c_ticks_self_consistency --recal-only   # Phase A のみ (一次判定)
  python -m code.c_ticks_self_consistency                # Phase A + B + KPI
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

HERE = Path(__file__).resolve().parent
YH006_1 = HERE.parent
YH006 = YH006_1.parent / "YH006"
for p in (YH006, YH006_1, HERE):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from config import CONDITIONS, ENSEMBLE_SEED_BASE, LOB_PARAMS  # noqa: E402
from parallel import default_n_workers  # noqa: E402

LOGS_DIR = YH006_1 / "logs"

CONDS = ["C2", "C3"]
N_SEEDS_DEFAULT = 6
BASELINE_C_TICKS = LOB_PARAMS["c_ticks"]  # 28.0


def setup_logger() -> logging.Logger:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    (LOGS_DIR / "runtime").mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("S5.9")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fh = logging.FileHandler(
        LOGS_DIR / "runtime" / f"{ts}_S5.9_c_ticks.log", encoding="utf-8",
    )
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    return logger


# ---------------------------------------------------------------------------
# self-contained capture run — run_lob_trial_smoke (run_experiment.py:232-275)
# の config 構築を mirror し、saver から price 系列も取得する
# ---------------------------------------------------------------------------

def _capture_run(
    cond_name: str,
    seed: int,
    c_ticks: float,
    warmup_steps: int,
    main_steps: int,
    num_sg: int,
    num_fcn: int,
    max_normal_orders: int,
) -> Dict[str, float]:
    import random as _stdlib_random
    from pams.runners import SequentialRunner  # type: ignore

    cond = CONDITIONS[cond_name]
    assert cond.world == "lob", f"{cond_name} is not LOB"
    assert cond.q_rule == "wealth" and not cond.lifetime_cap, \
        f"{cond_name}: S5.9 は baseline C2/C3 のみ (ablation 非対象)"

    if cond.wealth_mode == "uniform":
        from configs.c2 import make_config as _make_cfg  # type: ignore
    else:
        from configs.c3 import make_config as _make_cfg  # type: ignore
    cfg = _make_cfg(
        warmup_steps=warmup_steps, main_steps=main_steps,
        num_sg_agents=num_sg, c_ticks=c_ticks,
        max_normal_orders=max_normal_orders,
    )
    cfg["FCNAgents"]["numAgents"] = num_fcn
    cfg["SGAgents"]["class"] = "WInitLoggingSpeculationAgent"

    from custom_saver import OrderTrackingSaver  # type: ignore
    from mm_fcn_agent import MMFCNAgent  # type: ignore
    from sg_agent import WInitLoggingSpeculationAgent  # type: ignore

    saver = OrderTrackingSaver()
    runner = SequentialRunner(
        settings=cfg, prng=_stdlib_random.Random(seed), logger=saver,
    )
    runner.class_register(WInitLoggingSpeculationAgent)
    runner.class_register(MMFCNAgent)
    runner.main()

    # --- post-SG price 系列から c_ticks_recal (calibrate_c_ticks.py:53-65 と同) ---
    prices = [
        log["market_price"]
        for log in sorted(saver.market_step_logs, key=lambda x: x["market_time"])
        if log["market_time"] >= warmup_steps
    ]
    arr = np.asarray(prices, dtype=np.float64)
    abs_diffs = np.abs(np.diff(arr)) if arr.size > 1 else np.array([])
    nz = abs_diffs[abs_diffs > 0]
    median_nz = float(np.median(nz)) if nz.size > 0 else 0.0
    median_all = float(np.median(abs_diffs)) if abs_diffs.size > 0 else 0.0
    c_ticks_recal = 3.0 * (median_nz if median_nz > 0 else max(median_all, 1e-6))

    # --- round-trip 活動量 (run_experiment.py:296-297 と同一フィルタ) ---
    sgs = [
        a for a in runner.simulator.agents
        if isinstance(a, WInitLoggingSpeculationAgent)
    ]
    n_rt = 0
    n_traded = 0
    for a in sgs:
        a_rt = 0
        for rt in a.round_trips:
            if rt["open_t"] < warmup_steps or rt["close_t"] < warmup_steps:
                continue
            a_rt += 1
        n_rt += a_rt
        if a_rt > 0:
            n_traded += 1
    n_sg = len(sgs)

    return {
        "cond": cond_name,
        "seed": seed,
        "c_ticks_in": float(c_ticks),
        "c_ticks_recal": c_ticks_recal,
        "median_abs_dmid_nz": median_nz,
        "n_rt": int(n_rt),
        "n_traded": int(n_traded),
        "n_sg": int(n_sg),
        "no_trade_frac": float((n_sg - n_traded) / max(n_sg, 1)),
        "price_mean": float(arr.mean()) if arr.size else 0.0,
    }


def _worker(args: Tuple) -> Dict[str, float]:
    return _capture_run(*args)


def run_phase(
    c_ticks_by_cond: Dict[str, float],
    seeds: List[int],
    warmup_steps: int,
    main_steps: int,
    num_sg: int,
    num_fcn: int,
    max_normal_orders: int,
    n_workers: int,
    logger: logging.Logger,
    label: str,
) -> List[Dict[str, float]]:
    jobs = [
        (cond, seed, c_ticks_by_cond[cond], warmup_steps, main_steps,
         num_sg, num_fcn, max_normal_orders)
        for cond in CONDS for seed in seeds
    ]
    logger.info(f"[{label}] {len(jobs)} run, n_workers={n_workers}, "
                f"c_ticks={c_ticks_by_cond}")
    out: List[Dict[str, float]] = []
    with ProcessPoolExecutor(max_workers=n_workers) as ex:
        futs = {ex.submit(_worker, j): j for j in jobs}
        for fut in as_completed(futs):
            r = fut.result()
            out.append(r)
            logger.info(
                f"[{label}] {r['cond']} seed={r['seed']} "
                f"c_ticks_in={r['c_ticks_in']:.3f} recal={r['c_ticks_recal']:.3f} "
                f"n_rt={r['n_rt']} no_trade={r['no_trade_frac']:.2f}"
            )
    return out


def _pool_by_cond(rows: List[Dict[str, float]], key: str) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for cond in CONDS:
        vals = [r[key] for r in rows if r["cond"] == cond]
        out[cond] = float(np.median(vals)) if vals else 0.0
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-base", type=int, default=ENSEMBLE_SEED_BASE)
    parser.add_argument("--n-seeds", type=int, default=N_SEEDS_DEFAULT)
    parser.add_argument("--n-workers", type=int, default=None)
    parser.add_argument("--main-steps", type=int, default=LOB_PARAMS["main_steps"])
    parser.add_argument("--recal-only", action="store_true",
                        help="Phase A のみ (c_ticks_recal 計測、再走しない)")
    args = parser.parse_args()

    logger = setup_logger()
    n_workers = args.n_workers or default_n_workers()
    seeds = list(range(args.seed_base, args.seed_base + args.n_seeds))
    p = LOB_PARAMS
    common = dict(
        warmup_steps=p["warmup_steps"], main_steps=args.main_steps,
        num_sg=p["N_sg"], num_fcn=p["num_fcn"],
        max_normal_orders=p["max_normal_orders"],
    )

    logger.info("=" * 70)
    logger.info(f"S5.9 c_ticks self-consistency — conds={CONDS}, seeds={seeds}, "
                f"main_steps={args.main_steps}, baseline c_ticks={BASELINE_C_TICKS}")
    logger.info("=" * 70)

    # --- Phase A: baseline c_ticks=28 で recal 計測 ---
    base_ct = {c: BASELINE_C_TICKS for c in CONDS}
    rows_a = run_phase(base_ct, seeds, n_workers=n_workers, logger=logger,
                       label="PhaseA", **common)
    recal = _pool_by_cond(rows_a, "c_ticks_recal")
    n_rt_base = _pool_by_cond(rows_a, "n_rt")
    drift = {c: recal[c] / BASELINE_C_TICKS for c in CONDS}
    logger.info(f"[PhaseA] pooled c_ticks_recal={recal} "
                f"(drift vs 28: {drift}) n_rt_base={n_rt_base}")

    summary: Dict = {
        "stage": "S5.9-P2",
        "seeds": seeds,
        "main_steps": args.main_steps,
        "baseline_c_ticks": BASELINE_C_TICKS,
        "phaseA": {
            "c_ticks_recal_pooled": recal,
            "drift_ratio": drift,
            "n_rt_pooled": n_rt_base,
            "rows": rows_a,
        },
        "timestamp": datetime.now().isoformat(),
    }

    if not args.recal_only:
        # --- Phase B: recal c_ticks で再走 ---
        rows_b = run_phase(recal, seeds, n_workers=n_workers, logger=logger,
                           label="PhaseB", **common)
        n_rt_recal = _pool_by_cond(rows_b, "n_rt")
        delta = {c: (n_rt_recal[c] - n_rt_base[c]) / max(n_rt_base[c], 1)
                 for c in CONDS}

        def verdict(d: float) -> str:
            if abs(d) <= 0.20:
                return "H_friction"
            if d >= 0.50:
                return "H_trigger"
            return "intermediate"

        kpi = {c: verdict(delta[c]) for c in CONDS}
        overall = ("H_friction" if all(v == "H_friction" for v in kpi.values())
                   else "H_trigger" if any(v == "H_trigger" for v in kpi.values())
                   else "intermediate")
        logger.info(f"[PhaseB] n_rt_recal={n_rt_recal} Δn_rt={delta} "
                    f"KPI={kpi} overall={overall}")
        summary["phaseB"] = {
            "c_ticks_used": recal,
            "n_rt_pooled": n_rt_recal,
            "delta_n_rt": delta,
            "kpi_per_cond": kpi,
            "overall": overall,
            "rows": rows_b,
        }

    out_json = LOGS_DIR / "S5.9_c_ticks_recal.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    logger.info(f"summary written: {out_json}")
    logger.info("=" * 70)
    logger.info("S5.9 complete. logs/S5.9_c_ticks_recal.json を確認 → diff.md")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
