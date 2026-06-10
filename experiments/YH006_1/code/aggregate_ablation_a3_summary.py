"""S6 aggregation — A3 ablation (C3_A3) + KPI L3 判定 + 仮説 A revised direct test.

S6 plan §3.7:
  1. integrity check (C3_A3 400 parquet、lifetime ≤ tau_max + slack assertion)
  2. ensemble_summary.parquet を 600 → 700 行に拡張 (+C3_A3)
  3. A3 interaction = (C3_A3 − C2) − (C0p − C0u) を 5 metrics、bootstrap CI
  4. Shrinkage = S3 interaction − A3 interaction、L3 判定
     (ratio ≤ 0.7 AND shrinkage CI 0 非含有)
  5. Pooled bin_var_slope 7 条件 + 仮説 A revised judgment
  6. 中間予測整合 (forced_retire_rate / wealth_persistence_rho / p25 lifetime)
  7. tab_S6_*.csv × 4、fig_S6_*.png × 2、README §S6、S6_summary_for_diff.json

補助分析 (pre-registered 外、2026-06-10 追加):
  Pooled bin_var_slope に seed-cluster bootstrap CI を付与。
  背景: trial-level interaction は S3/S5 で全 metric CI が 0 跨ぎ (L2 0/5) で
  あり、L3 の ratio 判定は分母 |S3_interaction| ≈ 0 により数値的に不安定。
  一方、仮説判定の物語は pooled slope (点推定、CI なし) に依存している。
  この乖離を埋めるため、pooled 量そのものに trial 単位の resample で
  CI を与え、pooled interaction / pooled shrinkage も CI 付きで report する。

Run (S6 Mac sim 完了後。plan では Windows 担当だが platform 非依存の
pandas/scipy 処理のみ。Mac で実行した場合は Windows 再実行で数値一致を
確認することを推奨 — 本 script は実行 platform をログと JSON に記録する):
  cd experiments/YH006_1
  python -m code.aggregate_ablation_a3_summary
"""

from __future__ import annotations

import argparse
import json
import logging
import platform
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
YH006_1 = HERE.parent
for _p in (str(YH006_1), str(HERE)):
    while _p in sys.path:
        sys.path.remove(_p)
    sys.path.insert(0, _p)

from aggregate_ensemble import aggregate_ensemble_summaries  # noqa: E402
from analysis import bin_variance_slope_pooled  # noqa: E402
from config import ENSEMBLE_SEED_BASE, ENSEMBLE_N_TRIALS, LOB_PARAMS  # noqa: E402
from stats import bootstrap_ci  # noqa: E402

DATA_DIR = YH006_1 / "data"
OUTPUTS_DIR = YH006_1 / "outputs"
LOGS_DIR = YH006_1 / "logs"

A3_COND = "C3_A3"
EXISTING_6_CONDS = ["C0u", "C0p", "C2", "C3", "C2_A1", "C3_A1"]
ALL_7_CONDS = EXISTING_6_CONDS + [A3_COND]
INTERACTION_METRICS = [
    "rho_pearson", "rho_spearman", "tau_kendall",
    "bin_var_slope", "q90_q10_slope_diff",
]
# ablation_a3_ensemble.py::LIFETIME_SLACK と同一に保つこと
LIFETIME_SLACK = LOB_PARAMS["warmup_steps"] + 50


def setup_logger() -> logging.Logger:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    (LOGS_DIR / "runtime").mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("S6-agg")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fh = logging.FileHandler(
        LOGS_DIR / "runtime" / f"{ts}_S6_aggregation.log", encoding="utf-8",
    )
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    return logger


def load_tau_max() -> int:
    with open(LOGS_DIR / "S6_tau_max_calibration.json", encoding="utf-8") as f:
        return int(json.load(f)["tau_max"])


# ---------------------------------------------------------------------------
# §1 integrity
# ---------------------------------------------------------------------------

def integrity_check(seeds: List[int], tau_max: int, logger: logging.Logger) -> bool:
    cond_dir = DATA_DIR / A3_COND
    expected = 4 * len(seeds)
    actual = sum(1 for _ in cond_dir.glob("*.parquet"))
    logger.info(f"[integrity] {A3_COND}: {actual} / {expected} parquet files")
    if actual != expected:
        logger.error(f"[integrity] FAIL: expected {expected}, got {actual}")
        return False
    # sample seed で cap assertion (plan §3.7 item 1)
    for sample_seed in (seeds[0], seeds[len(seeds) // 2], seeds[-1]):
        lt = pd.read_parquet(cond_dir / f"lifetimes_{sample_seed:04d}.parquet")
        life_max = int(lt["lifetime"].max())
        if life_max > tau_max + LIFETIME_SLACK:
            logger.error(
                f"[integrity] FAIL: seed={sample_seed} lifetime max {life_max} > "
                f"tau_max {tau_max} + slack {LIFETIME_SLACK}"
            )
            return False
        logger.info(
            f"[integrity] seed={sample_seed}: lifetime max {life_max} "
            f"≤ {tau_max + LIFETIME_SLACK} ✓ (n={len(lt)})"
        )
    logger.info(f"[integrity] {A3_COND}: OK")
    return True


# ---------------------------------------------------------------------------
# §2 combine 600 → 700 rows
# ---------------------------------------------------------------------------

def combine_to_700_rows(seeds: List[int], logger: logging.Logger) -> pd.DataFrame:
    existing_path = DATA_DIR / "ensemble_summary.parquet"
    df_existing = pd.read_parquet(existing_path)
    logger.info(f"[load] ensemble_summary: {len(df_existing)} rows, "
                f"conds={sorted(df_existing['cond'].unique().tolist())}")
    df_existing = df_existing[df_existing["cond"].isin(EXISTING_6_CONDS)].copy()

    T_lob = LOB_PARAMS["main_steps"]
    logger.info(f"[A3] computing ensemble_summary for {A3_COND} (T={T_lob})...")
    df_a3 = aggregate_ensemble_summaries(A3_COND, seeds, DATA_DIR / A3_COND, T_lob, logger)
    logger.info(f"[A3] {A3_COND}: {len(df_a3)} rows")

    df_full = pd.concat([df_existing, df_a3], ignore_index=True)
    df_full.to_parquet(existing_path, index=False)
    cnt = df_full.groupby("cond").size().to_dict()
    logger.info(f"[save] {existing_path}: {len(df_full)} rows, per-cond: {cnt}")
    return df_full


# ---------------------------------------------------------------------------
# §3-§4 A3 interaction + shrinkage (seed-paired)
# ---------------------------------------------------------------------------

def _seed_paired(df: pd.DataFrame, conds: List[str], metric: str) -> pd.DataFrame:
    """seed で内部結合した wide DataFrame を返す (列 = cond 名)。

    S5 (A1) の positional alignment は dropna 後に seed ペアがずれる潜在
    バグがあったため、本 stage では明示的に seed merge する。NaN 落ちが
    無い場合は positional と同値。
    """
    out = None
    for cond in conds:
        sub = df[df["cond"] == cond][["seed", metric]].dropna()
        sub = sub.rename(columns={metric: cond})
        out = sub if out is None else out.merge(sub, on="seed", how="inner")
    return out


def compute_a3_interactions(df: pd.DataFrame, n_resample: int = 10_000) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    rows = []
    for metric in INTERACTION_METRICS:
        wide = _seed_paired(df, ["C0u", "C0p", "C2", A3_COND], metric)
        n = 0 if wide is None else len(wide)
        if n == 0:
            rows.append({"metric": metric, "interaction_mean": float("nan"),
                         "ci_lo": float("nan"), "ci_hi": float("nan"), "n": 0})
            continue
        inter = ((wide[A3_COND] - wide["C2"]) - (wide["C0p"] - wide["C0u"])).to_numpy()
        m, lo, hi = bootstrap_ci(inter, n_resample=n_resample, ci=0.95, rng=rng)
        rows.append({"metric": metric, "interaction_mean": float(m),
                     "ci_lo": float(lo), "ci_hi": float(hi), "n": int(n)})
    return pd.DataFrame(rows)


def compute_shrinkage_l3(
    df: pd.DataFrame, s3_inter: pd.DataFrame, a3_inter: pd.DataFrame,
    n_resample: int = 10_000,
) -> pd.DataFrame:
    """L3: shrinkage ratio ≤ 0.7 AND shrinkage CI 0 非含有 (plan §0.4)。"""
    rng = np.random.default_rng(0)
    rows = []
    for metric in INTERACTION_METRICS:
        wide = _seed_paired(df, ["C0u", "C0p", "C2", "C3", A3_COND], metric)
        n = 0 if wide is None else len(wide)
        if n == 0:
            rows.append({"metric": metric, "s3_mean": float("nan"),
                         "a3_mean": float("nan"), "shrinkage_mean": float("nan"),
                         "shrinkage_lo": float("nan"), "shrinkage_hi": float("nan"),
                         "shrinkage_ratio": float("nan"),
                         "ci_excludes_zero": False, "L3_pass": False, "n": 0})
            continue
        base = (wide["C0p"] - wide["C0u"]).to_numpy()
        s3_arr = (wide["C3"] - wide["C2"]).to_numpy() - base
        a3_arr = (wide[A3_COND] - wide["C2"]).to_numpy() - base
        delta = s3_arr - a3_arr  # = C3 − C3_A3 (seed-paired)
        s3_mean = float(s3_arr.mean())
        a3_mean = float(a3_arr.mean())
        d_m, d_lo, d_hi = bootstrap_ci(delta, n_resample=n_resample, ci=0.95, rng=rng)
        ratio = abs(a3_mean) / abs(s3_mean) if abs(s3_mean) > 1e-10 else float("nan")
        ci_excludes_zero = (d_lo > 0) or (d_hi < 0)
        l3_pass = bool((not np.isnan(ratio)) and ratio <= 0.7 and ci_excludes_zero)
        rows.append({
            "metric": metric, "s3_mean": s3_mean, "a3_mean": a3_mean,
            "shrinkage_mean": float(d_m), "shrinkage_lo": float(d_lo),
            "shrinkage_hi": float(d_hi), "shrinkage_ratio": ratio,
            "ci_excludes_zero": bool(ci_excludes_zero),
            "L3_pass": l3_pass, "n": int(n),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# §5 pooled bin_var 7 cond + seed-cluster bootstrap CI (補助分析)
# ---------------------------------------------------------------------------

def _load_rt_arrays(cond: str, seeds: List[int]) -> Dict[int, pd.DataFrame]:
    cond_dir = DATA_DIR / cond
    out: Dict[int, pd.DataFrame] = {}
    for seed in seeds:
        p = cond_dir / f"trial_{seed:04d}.parquet"
        if p.exists():
            out[seed] = pd.read_parquet(p, columns=["horizon", "delta_g"])
    return out


def compute_pooled_7cond_with_ci(
    seeds: List[int], n_boot: int, logger: logging.Logger,
) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    rows = []
    boot_samples: Dict[str, np.ndarray] = {}
    for cond in ALL_7_CONDS:
        trials = _load_rt_arrays(cond, seeds)
        if not trials:
            logger.warning(f"[pooled] {cond}: no data, skip")
            rows.append({"cond": cond, "pooled_bin_var_slope": float("nan"),
                         "ci_lo": float("nan"), "ci_hi": float("nan"),
                         "n_rt": 0, "n_trials": 0})
            boot_samples[cond] = np.full(n_boot, np.nan)
            continue
        keys = list(trials.keys())
        pooled_rt = pd.concat(trials.values(), ignore_index=True)
        point = float(bin_variance_slope_pooled(pooled_rt, K=15))
        # seed-cluster bootstrap: trial を resample して pooled slope を再計算
        bs = np.empty(n_boot)
        for b in range(n_boot):
            pick = rng.choice(len(keys), size=len(keys), replace=True)
            sample = pd.concat([trials[keys[i]] for i in pick], ignore_index=True)
            bs[b] = bin_variance_slope_pooled(sample, K=15)
        boot_samples[cond] = bs
        lo, hi = np.nanpercentile(bs, [2.5, 97.5])
        rows.append({"cond": cond, "pooled_bin_var_slope": point,
                     "ci_lo": float(lo), "ci_hi": float(hi),
                     "n_rt": int(len(pooled_rt)), "n_trials": len(keys)})
        logger.info(f"[pooled] {cond}: slope={point:+.4f} "
                    f"[{lo:+.4f}, {hi:+.4f}] (n_rt={len(pooled_rt):,})")
    df = pd.DataFrame(rows)

    # pooled interaction / shrinkage (bootstrap 分布の差で CI)
    s3_pool = (boot_samples["C3"] - boot_samples["C2"]) \
        - (boot_samples["C0p"] - boot_samples["C0u"])
    a3_pool = (boot_samples[A3_COND] - boot_samples["C2"]) \
        - (boot_samples["C0p"] - boot_samples["C0u"])
    shrink_pool = s3_pool - a3_pool

    def _ci(arr: np.ndarray) -> Dict[str, float]:
        return {"mean": float(np.nanmean(arr)),
                "lo": float(np.nanpercentile(arr, 2.5)),
                "hi": float(np.nanpercentile(arr, 97.5))}

    pooled_extra = {
        "pooled_interaction_S3": _ci(s3_pool),
        "pooled_interaction_A3": _ci(a3_pool),
        "pooled_shrinkage": _ci(shrink_pool),
        "n_boot": n_boot,
        "note": ("seed-cluster bootstrap。同一 resample 列を条件間で共有しない"
                 "独立 resample のため paired 構造は未利用 (保守的)"),
    }
    logger.info(f"[pooled] interaction S3={pooled_extra['pooled_interaction_S3']} "
                f"A3={pooled_extra['pooled_interaction_A3']} "
                f"shrinkage={pooled_extra['pooled_shrinkage']}")
    df.attrs["pooled_extra"] = pooled_extra
    return df


def compute_matched_horizon_pooled(
    seeds: List[int], tau_max: int, logger: logging.Logger,
) -> pd.DataFrame:
    """補助分析 (2026-06-10 design review 指摘 #2 対応): matched-horizon slope。

    A3 は cap により horizon > ~τ_max の RT が構造的に生成されないため、
    C3_A3 と C3 の pooled bin_var_slope は異なる horizon support 上の量で、
    直接比較は打ち切り artifact を含みうる。全条件を h ≤ τ_max に制限して
    同一 support で再計算し、gap が保たれるかを確認する。
    """
    rows = []
    for cond in ALL_7_CONDS:
        trials = _load_rt_arrays(cond, seeds)
        if not trials:
            rows.append({"cond": cond,
                         "pooled_bin_var_slope_matched": float("nan"),
                         "n_rt_matched": 0, "frac_rt_dropped": float("nan")})
            continue
        pooled_rt = pd.concat(trials.values(), ignore_index=True)
        n_all = len(pooled_rt)
        matched = pooled_rt[pooled_rt["horizon"] <= tau_max]
        slope = float(bin_variance_slope_pooled(matched, K=15))
        rows.append({"cond": cond,
                     "pooled_bin_var_slope_matched": slope,
                     "n_rt_matched": int(len(matched)),
                     "frac_rt_dropped": float(1.0 - len(matched) / max(n_all, 1))})
        logger.info(f"[matched-h] {cond}: slope(h≤{tau_max})={slope:+.4f} "
                    f"(dropped {rows[-1]['frac_rt_dropped']:.1%} of RT)")
    return pd.DataFrame(rows)


def hypothesis_a_revised_judgment(pooled_df: pd.DataFrame) -> Dict[str, object]:
    """仮説 A revised judgment (plan §3.7 item 8)。

    λ = (slope(C3_A3) − slope(C3)) / (slope(ref) − slope(C3)) で C3 → ref
    方向への相対シフト量を定量化 (ref = C2_A1 と C0u の両方を report)。
    閾値 (λ ≥ 0.7 → shifted / λ ≤ 0.3 → stayed / 中間 → partial) は
    pre-registered ではない記述的区分であることに注意。
    """
    s = {r["cond"]: r["pooled_bin_var_slope"] for _, r in pooled_df.iterrows()}
    out: Dict[str, object] = {"slope_C3_A3": s.get(A3_COND, float("nan"))}
    for ref in ("C2_A1", "C0u"):
        denom = s[ref] - s["C3"]
        lam = (s[A3_COND] - s["C3"]) / denom if abs(denom) > 1e-12 else float("nan")
        out[f"lambda_vs_{ref}"] = float(lam)
    lam = out["lambda_vs_C2_A1"]
    if np.isnan(lam):
        cat = "undetermined"
    elif lam >= 0.7:
        cat = "shifted_to_agg_side (仮説A revised 支持)"
    elif lam <= 0.3:
        cat = "stayed_at_C3 (仮説A revised fail)"
    else:
        cat = "partial"
    out["judgment"] = cat
    return out


# ---------------------------------------------------------------------------
# §6 中間予測整合性 (manipulation check、成功条件ではない — plan §0.4)
# ---------------------------------------------------------------------------

def intermediate_predictions(
    df: pd.DataFrame, seeds: List[int], tau_max: int, logger: logging.Logger,
) -> pd.DataFrame:
    rows = []

    def _mean(cond: str, col: str) -> float:
        v = df[df["cond"] == cond][col].dropna()
        return float(v.mean()) if len(v) else float("nan")

    frr_c3 = _mean("C3", "forced_retire_rate")
    frr_a3 = _mean(A3_COND, "forced_retire_rate")
    ratio = frr_a3 / frr_c3 if frr_c3 > 0 else float("inf")
    rows.append({"check": "forced_retire_rate", "C3": frr_c3, "C3_A3": frr_a3,
                 "criterion": ">= 5x 上昇", "value": ratio,
                 "consistent": bool(ratio >= 5.0)})

    wpr_c3 = _mean("C3", "wealth_persistence_rho")
    wpr_a3 = _mean(A3_COND, "wealth_persistence_rho")
    wpr_c2 = _mean("C2", "wealth_persistence_rho")
    rows.append({"check": "wealth_persistence_rho", "C3": wpr_c3, "C3_A3": wpr_a3,
                 "criterion": f"C2 ({wpr_c2:+.4f}) 側へ移動 (方向性、参考)",
                 "value": wpr_a3 - wpr_c3,
                 "consistent": bool(abs(wpr_a3 - wpr_c2) < abs(wpr_c3 - wpr_c2))})

    # p25 lifetime: pooled lifetimes parquet から
    lts = []
    for seed in seeds:
        p = DATA_DIR / A3_COND / f"lifetimes_{seed:04d}.parquet"
        if p.exists():
            lts.append(pd.read_parquet(p, columns=["lifetime"]))
    p25 = float(np.percentile(pd.concat(lts)["lifetime"], 25)) if lts else float("nan")
    rows.append({"check": "p25_lifetime", "C3": 241.0, "C3_A3": p25,
                 "criterion": f"tau_max={tau_max} 以下に集中 (manipulation check)",
                 "value": p25, "consistent": bool(p25 <= tau_max)})

    cap_mean = _mean(A3_COND, "n_lifetime_capped")
    rows.append({"check": "n_lifetime_capped_mean",
                 "C3": _mean("C3", "n_lifetime_capped"),
                 "C3_A3": cap_mean, "criterion": "> 0 (cap 発火の確認)",
                 "value": cap_mean, "consistent": bool(cap_mean > 0)})

    out = pd.DataFrame(rows)
    for _, r in out.iterrows():
        logger.info(f"[intermediate] {r['check']}: C3={r['C3']} → C3_A3={r['C3_A3']} "
                    f"({r['criterion']}) consistent={r['consistent']}")
    return out


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------

def plot_pooled_7cond(pooled_df: pd.DataFrame, judgment: Dict, out_path: Path,
                      logger: logging.Logger) -> None:
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(ALL_7_CONDS))
    vals = [float(pooled_df[pooled_df["cond"] == c]["pooled_bin_var_slope"].iloc[0])
            for c in ALL_7_CONDS]
    lo = [float(pooled_df[pooled_df["cond"] == c]["ci_lo"].iloc[0]) for c in ALL_7_CONDS]
    hi = [float(pooled_df[pooled_df["cond"] == c]["ci_hi"].iloc[0]) for c in ALL_7_CONDS]
    err = [np.array(vals) - np.array(lo), np.array(hi) - np.array(vals)]
    colors = ["#777777", "#777777", "#1f77b4", "#1f77b4",
              "#2ca02c", "#2ca02c", "#d62728"]
    ax.bar(x, vals, yerr=err, capsize=4, color=colors, alpha=0.85)
    ax.axhline(0, color="black", linewidth=0.4)
    ax.set_xticks(x)
    ax.set_xticklabels(ALL_7_CONDS, rotation=15)
    ax.set_ylabel("pooled bin_var_slope (seed-cluster bootstrap 95% CI)")
    lam = judgment.get("lambda_vs_C2_A1", float("nan"))
    ax.set_title(
        "S6 — pooled bin_var_slope, 7 conditions\n"
        f"C3_A3 shift λ(vs C2_A1) = {lam:.2f} → {judgment.get('judgment', '')}"
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"[output] saved: {out_path}")


def plot_shrinkage_3way(
    s3_inter: pd.DataFrame, a3_inter: pd.DataFrame, shrinkage_df: pd.DataFrame,
    out_path: Path, logger: logging.Logger,
) -> None:
    import matplotlib.pyplot as plt
    # A1 interaction (S5) も読み込んで 3-way 比較 (plan §3.7 fig 指定)
    a1_path = OUTPUTS_DIR / "tables" / "tab_S5_ablation_interaction.csv"
    a1_inter = pd.read_csv(a1_path) if a1_path.exists() else None
    metrics = INTERACTION_METRICS
    n = len(metrics)
    fig, ax = plt.subplots(figsize=(max(8, 1.4 * n + 5), 5))
    x = np.arange(n)
    width = 0.25

    def _vals(t: pd.DataFrame):
        m_ = [float(t[t["metric"] == m]["interaction_mean"].iloc[0])
              if (t["metric"] == m).any() else np.nan for m in metrics]
        lo_ = [float(t[t["metric"] == m]["ci_lo"].iloc[0])
               if (t["metric"] == m).any() else np.nan for m in metrics]
        hi_ = [float(t[t["metric"] == m]["ci_hi"].iloc[0])
               if (t["metric"] == m).any() else np.nan for m in metrics]
        return (np.array(m_), [np.array(m_) - np.array(lo_),
                               np.array(hi_) - np.array(m_)])

    s3_m, s3_e = _vals(s3_inter)
    ax.bar(x - width, s3_m, width, yerr=s3_e, capsize=3, color="#1f77b4",
           alpha=0.85, label="S3 baseline (C3−C2)−(C0p−C0u)")
    if a1_inter is not None:
        a1_m, a1_e = _vals(a1_inter)
        ax.bar(x, a1_m, width, yerr=a1_e, capsize=3, color="#2ca02c",
               alpha=0.85, label="A1 (C3_A1−C2_A1)−(C0p−C0u)")
    a3_m, a3_e = _vals(a3_inter)
    ax.bar(x + width, a3_m, width, yerr=a3_e, capsize=3, color="#d62728",
           alpha=0.85, label="A3 (C3_A3−C2)−(C0p−C0u)")
    ax.axhline(0, color="black", linewidth=0.4)
    ax.set_xticks(x)
    ax.set_xticklabels(metrics, rotation=20, ha="right")
    ax.set_ylabel("Interaction value")
    for i, m in enumerate(metrics):
        row = shrinkage_df[shrinkage_df["metric"] == m]
        if len(row) > 0:
            l3 = bool(row["L3_pass"].iloc[0])
            ratio = float(row["shrinkage_ratio"].iloc[0])
            top = np.nanmax([s3_m[i], a3_m[i]])
            ax.annotate(f"L3 {'PASS' if l3 else 'fail'}\nratio={ratio:.2f}",
                        xy=(i, top if np.isfinite(top) else 0),
                        xytext=(0, 8), textcoords="offset points",
                        ha="center", fontsize=8,
                        color="green" if l3 else "gray")
    ax.legend(loc="best", fontsize=9)
    ax.set_title("S6 — ablation interaction: S3 vs A1 vs A3\n"
                 "(L3 pass = shrinkage ratio ≤ 0.7 AND CI excludes 0)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"[output] saved: {out_path}")


# ---------------------------------------------------------------------------
# README append
# ---------------------------------------------------------------------------

def append_readme(
    df: pd.DataFrame, tau_max: int, pooled_df: pd.DataFrame, judgment: Dict,
    s3_inter: pd.DataFrame, a3_inter: pd.DataFrame, shrinkage_df: pd.DataFrame,
    inter_pred: pd.DataFrame, pooled_extra: Dict, readme_path: Path,
) -> None:
    lines: List[str] = ["", "---", ""]
    lines.append("## Stage S6 — A3 ablation (C3_A3) + 仮説 A revised direct test + KPI L3 判定")
    lines.append("")
    n_per_cond = df.groupby("cond").size().to_dict()
    lines.append("**実行範囲**: " + ", ".join(f"{c}: {n}" for c, n in sorted(n_per_cond.items())))
    lines.append("")
    lines.append(f"**τ_max = {tau_max}** (C3 pooled lifetime p25=241 × 0.5、"
                 "`logs/S6_tau_max_calibration.json`)")
    lines.append("")
    lines.append("### Pooled bin_var_slope (7 条件、seed-cluster bootstrap 95% CI)")
    lines.append("")
    lines.append("| cond | pooled bin_var_slope | 95% CI |")
    lines.append("|---|---:|---|")
    for _, r in pooled_df.iterrows():
        lines.append(f"| {r['cond']} | {r['pooled_bin_var_slope']:+.4f} | "
                     f"[{r['ci_lo']:+.4f}, {r['ci_hi']:+.4f}] |")
    lines.append("")
    lines.append(f"**仮説 A revised judgment**: λ(vs C2_A1) = "
                 f"{judgment['lambda_vs_C2_A1']:.3f}, λ(vs C0u) = "
                 f"{judgment['lambda_vs_C0u']:.3f} → **{judgment['judgment']}** "
                 "(λ 閾値 0.3/0.7 は記述的区分で pre-registered ではない)")
    lines.append("")
    pe = pooled_extra
    lines.append("**Pooled interaction (補助分析、bootstrap CI)**: "
                 f"S3 = {pe['pooled_interaction_S3']['mean']:+.4f} "
                 f"[{pe['pooled_interaction_S3']['lo']:+.4f}, {pe['pooled_interaction_S3']['hi']:+.4f}], "
                 f"A3 = {pe['pooled_interaction_A3']['mean']:+.4f} "
                 f"[{pe['pooled_interaction_A3']['lo']:+.4f}, {pe['pooled_interaction_A3']['hi']:+.4f}], "
                 f"shrinkage = {pe['pooled_shrinkage']['mean']:+.4f} "
                 f"[{pe['pooled_shrinkage']['lo']:+.4f}, {pe['pooled_shrinkage']['hi']:+.4f}]")
    lines.append("")
    lines.append("### A3 interaction shrinkage vs S3 baseline (trial-level、pre-registered L3)")
    lines.append("")
    lines.append("| metric | S3 mean [CI] | A3 mean [CI] | shrinkage [CI] | ratio | L3 |")
    lines.append("|---|---|---|---|---:|---|")
    s3_map = {r["metric"]: r for _, r in s3_inter.iterrows()}
    a3_map = {r["metric"]: r for _, r in a3_inter.iterrows()}
    for _, r in shrinkage_df.iterrows():
        m = r["metric"]
        s3 = s3_map.get(m)
        a3 = a3_map.get(m)
        s3_cell = (f"{s3['interaction_mean']:+.4f} [{s3['ci_lo']:+.4f}, {s3['ci_hi']:+.4f}]"
                   if s3 is not None else "—")
        a3_cell = (f"{a3['interaction_mean']:+.4f} [{a3['ci_lo']:+.4f}, {a3['ci_hi']:+.4f}]"
                   if a3 is not None else "—")
        sh = (f"{r['shrinkage_mean']:+.4f} "
              f"[{r['shrinkage_lo']:+.4f}, {r['shrinkage_hi']:+.4f}]")
        ratio_str = (f"{r['shrinkage_ratio']:.3f}"
                     if not np.isnan(r["shrinkage_ratio"]) else "—")
        l3 = "**PASS**" if r["L3_pass"] else "fail"
        lines.append(f"| {m} | {s3_cell} | {a3_cell} | {sh} | {ratio_str} | {l3} |")
    lines.append("")
    l3_count = int(shrinkage_df["L3_pass"].sum())
    lines.append(f"**L3 pass 件数: {l3_count} / {len(INTERACTION_METRICS)}** "
                 "(注意: S3 trial-level interaction は全 metric で CI が 0 を跨ぐため "
                 "ratio 分母が不安定。pooled 補助分析を併読のこと)")
    lines.append("")
    lines.append("### 中間予測整合性 (manipulation check、成功条件ではない)")
    lines.append("")
    lines.append("| check | C3 | C3_A3 | criterion | consistent |")
    lines.append("|---|---:|---:|---|---|")
    for _, r in inter_pred.iterrows():
        lines.append(f"| {r['check']} | {r['C3']:.4g} | {r['C3_A3']:.4g} | "
                     f"{r['criterion']} | {'✓' if r['consistent'] else '✗'} |")
    lines.append("")
    lines.append("### Layer 2 timescale concern (再掲) + A3 固有の解釈上の注意")
    lines.append("")
    lines.append("T=1500 は Katahira 標準 T=50000 の 1/33。さらに A3 は τ_max=121 の "
                 "cap により horizon > ~121 の RT が構造的に生成されない (agent が"
                 "ポジションを cap を超えて保持できない) ため、bin_var_slope の "
                 "horizon support が C3 と異なる。pooled slope のシフトのうち "
                 "「wealth persistence の破壊」由来と「horizon 打ち切り」由来の"
                 "切り分けは matched-horizon (h ≤ τ_max) 再計算で確認が必要 "
                 "(2026-06-10 design review 指摘 #2)。")
    lines.append("")
    with open(readme_path, "a", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-base", type=int, default=ENSEMBLE_SEED_BASE)
    parser.add_argument("--n-trials", type=int, default=ENSEMBLE_N_TRIALS)
    parser.add_argument("--n-boot-pooled", type=int, default=500,
                        help="pooled slope の seed-cluster bootstrap 回数")
    parser.add_argument("--skip-readme", action="store_true")
    args = parser.parse_args()

    logger = setup_logger()
    seeds = list(range(args.seed_base, args.seed_base + args.n_trials))
    tau_max = load_tau_max()

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUTS_DIR / "tables").mkdir(parents=True, exist_ok=True)
    (OUTPUTS_DIR / "figures").mkdir(parents=True, exist_ok=True)

    logger.info("=" * 70)
    logger.info(f"S6 aggregation — {A3_COND} (tau_max={tau_max}) + L3 judgment "
                f"| platform={platform.system()} {platform.machine()}")
    logger.info("=" * 70)

    if not integrity_check(seeds, tau_max, logger):
        logger.error("integrity failed, aborting")
        return

    df = combine_to_700_rows(seeds, logger)

    pooled_df = compute_pooled_7cond_with_ci(seeds, args.n_boot_pooled, logger)
    pooled_extra = pooled_df.attrs["pooled_extra"]
    judgment = hypothesis_a_revised_judgment(pooled_df)
    logger.info(f"[judgment] {judgment}")
    pooled_out = pooled_df.copy()
    pooled_out["judgment"] = str(judgment["judgment"])
    pooled_out.to_csv(OUTPUTS_DIR / "tables" / "tab_S6_pooled_bin_var_7cond.csv",
                      index=False)

    a3_inter = compute_a3_interactions(df)
    a3_inter.to_csv(OUTPUTS_DIR / "tables" / "tab_S6_ablation_interaction.csv",
                    index=False)
    s3_inter = pd.read_csv(OUTPUTS_DIR / "tables" / "tab_S3_interaction.csv")
    shrinkage_df = compute_shrinkage_l3(df, s3_inter, a3_inter)
    shrinkage_df.to_csv(OUTPUTS_DIR / "tables" / "tab_S6_shrinkage.csv", index=False)
    for _, r in shrinkage_df.iterrows():
        ratio_str = (f"{r['shrinkage_ratio']:.3f}"
                     if not np.isnan(r["shrinkage_ratio"]) else "nan")
        logger.info(
            f"[L3] {r['metric']}: S3={r['s3_mean']:+.4f} → A3={r['a3_mean']:+.4f}, "
            f"shrinkage={r['shrinkage_mean']:+.4f} "
            f"[{r['shrinkage_lo']:+.4f}, {r['shrinkage_hi']:+.4f}], "
            f"ratio={ratio_str}, L3={'PASS' if r['L3_pass'] else 'fail'}"
        )

    inter_pred = intermediate_predictions(df, seeds, tau_max, logger)
    inter_pred.to_csv(OUTPUTS_DIR / "tables" / "tab_S6_intermediate_predictions.csv",
                      index=False)

    matched_df = compute_matched_horizon_pooled(seeds, tau_max, logger)
    matched_df.to_csv(
        OUTPUTS_DIR / "tables" / "tab_S6_pooled_bin_var_matched_horizon.csv",
        index=False)

    plot_pooled_7cond(pooled_df, judgment,
                      OUTPUTS_DIR / "figures" / "fig_S6_pooled_bin_var_7cond.png",
                      logger)
    plot_shrinkage_3way(s3_inter, a3_inter, shrinkage_df,
                        OUTPUTS_DIR / "figures" / "fig_S6_ablation_shrinkage.png",
                        logger)

    if not args.skip_readme:
        append_readme(df, tau_max, pooled_df, judgment, s3_inter, a3_inter,
                      shrinkage_df, inter_pred, pooled_extra,
                      YH006_1 / "README.md")
        logger.info("[output] appended README §S6")

    summary = {
        "stage": "S6",
        "tau_max": tau_max,
        "platform": f"{platform.system()} {platform.machine()}",
        "n_trials_per_cond": {c: int((df["cond"] == c).sum()) for c in ALL_7_CONDS},
        "pooled_bin_var_7cond": pooled_out.to_dict(orient="records"),
        "pooled_extra": pooled_extra,
        "hypothesis_a_revised": {k: (str(v) if isinstance(v, str) else v)
                                 for k, v in judgment.items()},
        "a3_interaction": a3_inter.to_dict(orient="records"),
        "shrinkage_L3": shrinkage_df.to_dict(orient="records"),
        "L3_pass_count": int(shrinkage_df["L3_pass"].sum()),
        "L3_total_metrics": len(INTERACTION_METRICS),
        "intermediate_predictions": inter_pred.to_dict(orient="records"),
        "matched_horizon_pooled": matched_df.to_dict(orient="records"),
        "timestamp": datetime.now().isoformat(),
    }
    with open(LOGS_DIR / "S6_summary_for_diff.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
    logger.info("[output] saved: S6_summary_for_diff.json")

    logger.info("=" * 70)
    logger.info(f"S6 aggregation complete. L3 pass: {summary['L3_pass_count']}/"
                f"{summary['L3_total_metrics']} | judgment: {judgment['judgment']}")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
