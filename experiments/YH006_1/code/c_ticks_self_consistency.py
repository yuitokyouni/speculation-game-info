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

v1.1 (2026-06-10): plan §4 の pre-registered 主判定 (funnel gap |Δ slope| ≤ 0.05、
survival) が v1.0 では計算不能だった (n_rt しか記録しない) ため、RT 明細 +
lifetime samples を `data/_s59_cticks/` に永続化し、pooled bin_var_slope と
censored_frac (≈ matched S(T-1)) を phase 間 paired 比較する endpoint を追加。
あわせて Phase B の再々較正値 c_ticks'' を収束診断として表面化 (1 パス再較正の
非収束リスクの定量化)。

S6 (C3_A3) と並走可能: 出力は logs/S5.9_* と data/_s59_cticks/ のみ、C3_A3 と非衝突。

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
import pandas as pd

HERE = Path(__file__).resolve().parent
YH006_1 = HERE.parent
YH006 = YH006_1.parent / "YH006"
for p in (YH006, YH006_1, HERE):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from config import CONDITIONS, ENSEMBLE_SEED_BASE, LOB_PARAMS  # noqa: E402
from parallel import default_n_workers  # noqa: E402

LOGS_DIR = YH006_1 / "logs"
S59_DATA_DIR = YH006_1 / "data" / "_s59_cticks"

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
    phase_label: str = "PhaseA",
    out_suffix: str = "",
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

    # --- round-trip 明細 (run_experiment.py:290-305 と同一フィルタ/正規化) ---
    sgs = [
        a for a in runner.simulator.agents
        if isinstance(a, WInitLoggingSpeculationAgent)
    ]
    all_rt: Dict[str, list] = {
        "agent_idx": [], "open_t": [], "close_t": [],
        "entry_action": [], "entry_quantity": [], "delta_G": [],
    }
    n_rt = 0
    n_traded = 0
    for a in sgs:
        a_rt = 0
        for rt in a.round_trips:
            if rt["open_t"] < warmup_steps or rt["close_t"] < warmup_steps:
                continue
            all_rt["agent_idx"].append(rt["agent_idx"])
            all_rt["open_t"].append(rt["open_t"] - warmup_steps)
            all_rt["close_t"].append(rt["close_t"] - warmup_steps)
            all_rt["entry_action"].append(rt["entry_action"])
            all_rt["entry_quantity"].append(rt["entry_quantity"])
            all_rt["delta_G"].append(rt["delta_G"])
            a_rt += 1
        n_rt += a_rt
        if a_rt > 0:
            n_traded += 1
    n_sg = len(sgs)

    # --- v1.1: RT 明細 + lifetime samples 永続化 (plan §4 funnel/survival 判定用) ---
    from adapter import round_trips_to_df, agent_lifetime_samples_to_df  # type: ignore
    rt_arrays = {
        k: np.asarray(v, dtype=np.int8 if k == "entry_action" else np.int64)
        for k, v in all_rt.items()
    }
    sub_events = []
    for a in sgs:
        for ev in a.substitute_events:
            t, dead_w, new_w = ev
            if t >= warmup_steps:
                sub_events.append(
                    (int(t - warmup_steps), int(a.agent_id), int(dead_w), int(new_w))
                )
    agent_w_init_map = {int(a.agent_id): int(a.w_init) for a in sgs}
    rt_df = round_trips_to_df(
        round_trips=rt_arrays, cond=cond_name, seed=seed,
        agent_w_init=agent_w_init_map, substitute_events=sub_events,
    )
    lt_df = agent_lifetime_samples_to_df(
        cond=cond_name, seed=seed, N_total=n_sg,
        substitute_events=sub_events, T_total=main_steps,
    )
    out_dir = S59_DATA_DIR / f"{phase_label}{out_suffix}"
    out_dir.mkdir(parents=True, exist_ok=True)
    rt_df.to_parquet(out_dir / f"trial_{cond_name}_{seed:04d}.parquet")
    lt_df.to_parquet(out_dir / f"lifetimes_{cond_name}_{seed:04d}.parquet")

    # --- v1.2: mid 価格系列 dump (LOB stylized facts readout 用、proposal Q2) ---
    pd.DataFrame({
        "t": np.arange(arr.size, dtype=np.int64),
        "mid": arr,
    }).to_parquet(out_dir / f"prices_{cond_name}_{seed:04d}.parquet")

    # --- v1.2: SG fill rate proper (README §S5.6 で未測定とされた媒介変数、Q1) ---
    sg_ids = {int(a.agent_id) for a in sgs}
    sg_orders = [o for o in saver.order_logs
                 if o["agent_id"] in sg_ids and o["time"] >= warmup_steps]
    n_sg_orders = len(sg_orders)
    sg_submitted_vol = float(sum(o["volume"] for o in sg_orders))
    # 約定は order_id で post-warmup 提出注文に帰属させる (warmup 提出 →
    # main 約定の境界 leak を排除。これで fill_rate_vol ≤ 1 が保証される)
    sg_order_ids = {o["order_id"] for o in sg_orders}
    # PAMS は 1 約定につき同一内容の ExecutionLog を 2 本 (買い手/売り手 view)
    # 発行する (2026-06-10 診断: 546 log 中 unique 273 = 正確に 2 倍)。dedupe 必須
    seen = set()
    sg_filled_vol = 0.0
    n_sg_exec_sides = 0
    for e in saver.execution_logs:
        key = (e["buy_order_id"], e["sell_order_id"], e["time"],
               e["volume"], e["price"])
        if key in seen:
            continue
        seen.add(key)
        for oid_key in ("buy_order_id", "sell_order_id"):
            if e[oid_key] in sg_order_ids:
                sg_filled_vol += float(e["volume"])
                n_sg_exec_sides += 1

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
        # v1.2: fill rate proper (volume / count の 2 定義を併記。
        # 部分約定・期限切れ未約定を含むため count 系は >1 になりうる)
        "n_sg_orders": int(n_sg_orders),
        "sg_submitted_vol": sg_submitted_vol,
        "sg_filled_vol": sg_filled_vol,
        "sg_fill_rate_vol": float(sg_filled_vol / max(sg_submitted_vol, 1e-9)),
        "n_sg_exec_sides": int(n_sg_exec_sides),
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
    out_suffix: str = "",
) -> List[Dict[str, float]]:
    jobs = [
        (cond, seed, c_ticks_by_cond[cond], warmup_steps, main_steps,
         num_sg, num_fcn, max_normal_orders, label, out_suffix)
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


def _bin_variance_slope_pooled(rt_df: pd.DataFrame, K: int = 15) -> float:
    """analysis.py::bin_variance_slope の逐語 inline 移植 (Mac venv に
    statsmodels が無く analysis.py の module import が通らないため。
    アルゴリズム・定数は analysis.py:54-97 と bit 同一に保つこと)。"""
    from scipy import stats as _sp_stats
    if "horizon" not in rt_df.columns or "delta_g" not in rt_df.columns:
        return float("nan")
    h = rt_df["horizon"].to_numpy(dtype=np.float64)
    dG = rt_df["delta_g"].to_numpy(dtype=np.float64)
    if h.size < K * 5:
        return float("nan")
    log_h = np.log(np.maximum(h, 1.0))
    if log_h.max() <= log_h.min():
        return float("nan")
    bin_edges = np.linspace(log_h.min(), log_h.max(), K + 1)
    bin_centers, bin_vars = [], []
    for i in range(K):
        if i == K - 1:
            mask = (log_h >= bin_edges[i]) & (log_h <= bin_edges[i + 1])
        else:
            mask = (log_h >= bin_edges[i]) & (log_h < bin_edges[i + 1])
        if mask.sum() < 5:
            continue
        bin_centers.append((bin_edges[i] + bin_edges[i + 1]) / 2.0)
        bin_vars.append(float(np.var(np.log(np.maximum(np.abs(dG[mask]), 1e-9)))))
    if len(bin_centers) < 3:
        return float("nan")
    res = _sp_stats.spearmanr(bin_centers, bin_vars)
    return float(res.correlation) if not np.isnan(res.correlation) else float("nan")


def _phase_endpoints(phase_label: str, out_suffix: str) -> Dict[str, Dict[str, float]]:
    """v1.1: 永続化済 RT/lifetime parquet から plan §4 endpoint を計算。

    - pooled_bin_var_slope: 全 seed pool 後の funnel 指標 (analysis.py inline 移植)
    - censored_frac: lifetime samples の censored 率 (≈ matched S(T-1)、
      S3 で C2 0.91 / C3 0.73 に対応する近似量)
    """
    bin_variance_slope_pooled = _bin_variance_slope_pooled
    d = S59_DATA_DIR / f"{phase_label}{out_suffix}"
    out: Dict[str, Dict[str, float]] = {}
    for cond in CONDS:
        rt_files = sorted(d.glob(f"trial_{cond}_*.parquet"))
        lt_files = sorted(d.glob(f"lifetimes_{cond}_*.parquet"))
        if not rt_files or not lt_files:
            out[cond] = {"pooled_bin_var_slope": float("nan"),
                         "censored_frac": float("nan"), "n_rt_total": 0}
            continue
        rt = pd.concat([pd.read_parquet(p) for p in rt_files], ignore_index=True)
        lt = pd.concat([pd.read_parquet(p) for p in lt_files], ignore_index=True)
        out[cond] = {
            "pooled_bin_var_slope": float(bin_variance_slope_pooled(rt)),
            "censored_frac": float(lt["censored"].astype(bool).mean()),
            "n_rt_total": int(len(rt)),
        }
    return out


def _funnel_verdict(delta: float) -> str:
    """plan §4 pre-registered: |Δ| ≤ 0.05 → 主張維持 / |Δ| > 0.10 → 主張修正。"""
    if not np.isfinite(delta):
        return "undetermined"
    if abs(delta) <= 0.05:
        return "maintained"
    if abs(delta) > 0.10:
        return "modified"
    return "intermediate"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-base", type=int, default=ENSEMBLE_SEED_BASE)
    parser.add_argument("--n-seeds", type=int, default=N_SEEDS_DEFAULT)
    parser.add_argument("--n-workers", type=int, default=None)
    parser.add_argument("--main-steps", type=int, default=LOB_PARAMS["main_steps"])
    parser.add_argument("--recal-only", action="store_true",
                        help="Phase A のみ (c_ticks_recal 計測、再走しない)")
    parser.add_argument("--out-suffix", type=str, default="",
                        help="出力 JSON / data subdir の suffix (smoke 用に '_smoke' 等)")
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
                       label="PhaseA", out_suffix=args.out_suffix, **common)
    recal = _pool_by_cond(rows_a, "c_ticks_recal")
    n_rt_base = _pool_by_cond(rows_a, "n_rt")
    fill_a = _pool_by_cond(rows_a, "sg_fill_rate_vol")
    drift = {c: recal[c] / BASELINE_C_TICKS for c in CONDS}
    ep_a = _phase_endpoints("PhaseA", args.out_suffix)
    logger.info(f"[PhaseA] SG fill_rate (vol, pooled median)={fill_a}")
    logger.info(f"[PhaseA] pooled c_ticks_recal={recal} "
                f"(drift vs 28: {drift}) n_rt_base={n_rt_base}")
    logger.info(f"[PhaseA] endpoints={ep_a}")

    summary: Dict = {
        "stage": "S5.9-P2",
        "seeds": seeds,
        "main_steps": args.main_steps,
        "baseline_c_ticks": BASELINE_C_TICKS,
        "phaseA": {
            "c_ticks_recal_pooled": recal,
            "drift_ratio": drift,
            "n_rt_pooled": n_rt_base,
            "sg_fill_rate_vol_pooled": fill_a,
            "endpoints": ep_a,
            "rows": rows_a,
        },
        "timestamp": datetime.now().isoformat(),
    }

    if not args.recal_only:
        # --- Phase B: recal c_ticks で再走 ---
        rows_b = run_phase(recal, seeds, n_workers=n_workers, logger=logger,
                           label="PhaseB", out_suffix=args.out_suffix, **common)
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

        # --- v1.1: plan §4 主判定 (funnel gap) + survival + 収束診断 ---
        ep_b = _phase_endpoints("PhaseB", args.out_suffix)
        funnel_delta = {
            c: ep_b[c]["pooled_bin_var_slope"] - ep_a[c]["pooled_bin_var_slope"]
            for c in CONDS
        }
        funnel_judgment = {c: _funnel_verdict(funnel_delta[c]) for c in CONDS}
        survival_delta = {
            c: ep_b[c]["censored_frac"] - ep_a[c]["censored_frac"] for c in CONDS
        }
        # 収束診断: Phase B 出力からの再々較正値 c_ticks'' / 投入値 c_ticks'
        recal2 = _pool_by_cond(rows_b, "c_ticks_recal")
        convergence_ratio = {
            c: recal2[c] / max(recal[c], 1e-9) for c in CONDS
        }
        logger.info(f"[PhaseB] funnel slope A→B Δ={funnel_delta} "
                    f"judgment={funnel_judgment} (plan §4 主判定)")
        logger.info(f"[PhaseB] survival censored_frac Δ={survival_delta}")
        logger.info(f"[PhaseB] 収束診断 c_ticks''/c_ticks'={convergence_ratio} "
                    f"(1 から遠いほど 1 パス再較正は非収束)")

        summary["phaseB"] = {
            "c_ticks_used": recal,
            "n_rt_pooled": n_rt_recal,
            "sg_fill_rate_vol_pooled": _pool_by_cond(rows_b, "sg_fill_rate_vol"),
            "delta_n_rt": delta,
            "kpi_per_cond": kpi,
            "overall": overall,
            "endpoints": ep_b,
            "funnel_delta_slope": funnel_delta,
            "funnel_judgment_preregistered": funnel_judgment,
            "survival_censored_frac_delta": survival_delta,
            "c_ticks_recal2_pooled": recal2,
            "convergence_ratio": convergence_ratio,
            "rows": rows_b,
        }

    out_json = LOGS_DIR / f"S5.9_c_ticks_recal{args.out_suffix}.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    logger.info(f"summary written: {out_json}")
    logger.info("=" * 70)
    logger.info("S5.9 complete. logs/S5.9_c_ticks_recal.json を確認 → diff.md")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
