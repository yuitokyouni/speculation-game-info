"""S7 — freeze→funnel 統合分析: ③符号矛盾解消 → ①dose-response → ②α/β → SF readout.

open point の対応 (Yuito 2026-06-12 指示):
  ③ funnel 指標の符号矛盾 (rho>0 vs bin_var_slope<0) を per-bin 診断で解消し、
     符号一貫な canonical 指標を確定
  ① liquidity dose-response: order_volume {15,30,60,120} × 6 seed (cond=C3) で
     funnel / RT / censoring の単調性 → freeze→funnel 因果リンク
  ② matched-horizon α/β probe: 共通 horizon support で agg vs LOB の per-RT
     dispersion profile を比較 (α=RT 数のみ / β=機構変質)。fill-selection bias
     の交絡があるため secondary
  SF readout: C2/C3 価格系列 (S5.9) vs FCN-only baseline (S7 runs) で
     fat tail / vol clustering の帰属 (proposal Q2)

Run (Mac、s7_doseresponse_runs 完了後):
  cd experiments/YH006_1
  python -m code.s7_freeze_funnel_analysis
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from scipy import stats as sp_stats

HERE = Path(__file__).resolve().parent
YH006_1 = HERE.parent
for _p in (str(YH006_1), str(HERE)):
    while _p in sys.path:
        sys.path.remove(_p)
    sys.path.insert(0, _p)

DATA_DIR = YH006_1 / "data"
OUTPUTS_DIR = YH006_1 / "outputs"
LOGS_DIR = YH006_1 / "logs"

AGG_DIAG_SEEDS = list(range(1000, 1020))   # agg は 20 seed subsample (メモリ対策、明記)
LOB_SEEDS = list(range(1000, 1100))
DOSE_SEEDS = list(range(1000, 1006))       # 各水準 6 seed
ORDER_VOLUMES = [15, 30, 60, 120]
K_BINS = 15


def setup_logger() -> logging.Logger:
    (LOGS_DIR / "runtime").mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("S7")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fh = logging.FileHandler(LOGS_DIR / "runtime" / f"{ts}_S7_analysis.log",
                             encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    return logger


def _load_pooled(cond_dir: Path, seeds: List[int],
                 pattern: str = "trial_{seed:04d}.parquet") -> pd.DataFrame:
    dfs = []
    for seed in seeds:
        f = cond_dir / pattern.format(seed=seed)
        if f.exists():
            dfs.append(pd.read_parquet(f, columns=["horizon", "delta_g"]))
    return (pd.concat(dfs, ignore_index=True) if dfs
            else pd.DataFrame(columns=["horizon", "delta_g"]))


# ---------------------------------------------------------------------------
# ③ per-bin 診断 + canonical 指標
# ---------------------------------------------------------------------------

def _bin_stats(h: np.ndarray, dG: np.ndarray, K: int = K_BINS,
               edges: Optional[np.ndarray] = None) -> pd.DataFrame:
    log_h = np.log(np.maximum(h, 1.0))
    if edges is None:
        if log_h.max() <= log_h.min():
            return pd.DataFrame()
        edges = np.linspace(log_h.min(), log_h.max(), K + 1)
    rows = []
    for i in range(len(edges) - 1):
        if i == len(edges) - 2:
            m = (log_h >= edges[i]) & (log_h <= edges[i + 1])
        else:
            m = (log_h >= edges[i]) & (log_h < edges[i + 1])
        if m.sum() < 5:
            continue
        d = dG[m]
        absd = np.abs(d)
        nz = absd > 0
        rows.append({
            "bin_center_logh": (edges[i] + edges[i + 1]) / 2.0,
            "n": int(m.sum()),
            "frac_zero_dG": float((~nz).mean()),
            "var_log_floor": float(np.var(np.log(np.maximum(absd, 1e-9)))),
            "var_log_nz": (float(np.var(np.log(absd[nz]))) if nz.sum() >= 5
                           else np.nan),
            "iqr_dG": float(np.subtract(*np.percentile(d, [75, 25]))),
            "sd_dG": float(np.std(d)),
        })
    return pd.DataFrame(rows)


def _spear(x, y) -> float:
    x, y = np.asarray(x, float), np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    if m.sum() < 3:
        return float("nan")
    r = sp_stats.spearmanr(x[m], y[m]).correlation
    return float(r) if np.isfinite(r) else float("nan")


def candidate_metrics(rt: pd.DataFrame) -> Dict[str, float]:
    """全候補指標。符号規約: 正 = funnel あり (horizon とともに広がる)。"""
    h = rt["horizon"].to_numpy(float)
    dG = rt["delta_g"].to_numpy(float)
    if h.size < K_BINS * 5:
        return {k: float("nan") for k in
                ["M_bin_var_floor", "M_bin_var_nz", "M_iqr", "M_sd",
                 "rho_pearson_abs", "frac_zero_slope"]}
    bs = _bin_stats(h, dG)
    absd = np.abs(dG)
    return {
        "M_bin_var_floor": _spear(bs["bin_center_logh"], bs["var_log_floor"]),
        "M_bin_var_nz": _spear(bs["bin_center_logh"], bs["var_log_nz"]),
        "M_iqr": _spear(bs["bin_center_logh"], bs["iqr_dG"]),
        "M_sd": _spear(bs["bin_center_logh"], bs["sd_dG"]),
        "rho_pearson_abs": (float(sp_stats.pearsonr(h, absd)[0])
                            if absd.std() > 0 else float("nan")),
        "frac_zero_slope": _spear(bs["bin_center_logh"], bs["frac_zero_dG"]),
    }


def resolve_metric(logger: logging.Logger) -> Dict:
    pooled = {
        "C0u": _load_pooled(DATA_DIR / "C0u", AGG_DIAG_SEEDS),
        "C0p": _load_pooled(DATA_DIR / "C0p", AGG_DIAG_SEEDS),
        "C2": _load_pooled(DATA_DIR / "C2", LOB_SEEDS),
        "C3": _load_pooled(DATA_DIR / "C3", LOB_SEEDS),
    }
    cand_rows = []
    for cond, rt in pooled.items():
        c = candidate_metrics(rt)
        c["cond"] = cond
        c["n_rt"] = len(rt)
        cand_rows.append(c)
        logger.info(f"[③] {cond}: " + " ".join(
            f"{k}={v:+.3f}" for k, v in c.items()
            if k not in ("cond", "n_rt") and isinstance(v, float)))
    cand = pd.DataFrame(cand_rows)

    # per-bin 診断表 (C0u / C3): 符号矛盾の機構を見る
    diag = []
    for cond in ("C0u", "C3"):
        b = _bin_stats(pooled[cond]["horizon"].to_numpy(float),
                       pooled[cond]["delta_g"].to_numpy(float))
        b["cond"] = cond
        diag.append(b)
    diag_df = pd.concat(diag, ignore_index=True)
    diag_df.to_csv(OUTPUTS_DIR / "tables" / "tab_S7_bin_diagnosis.csv", index=False)
    cand.to_csv(OUTPUTS_DIR / "tables" / "tab_S7_metric_candidates.csv", index=False)

    # canonical 選定規則 (pre-stated): agg 2 条件で正、かつ
    # LOB で agg より小さい (= funnel 減衰の向きが #1 と整合) 指標を、
    # 優先順 [M_iqr, M_sd, M_bin_var_nz] で最初に満たすもの
    def _ok(m):
        r = {row["cond"]: row[m] for _, row in cand.iterrows()}
        return (np.isfinite(r["C0u"]) and r["C0u"] > 0 and r["C0p"] > 0
                and r["C2"] < r["C0u"] and r["C3"] < r["C0p"])

    canonical = None
    for m in ("M_iqr", "M_sd", "M_bin_var_nz"):
        if _ok(m):
            canonical = m
            break
    logger.info(f"[③] canonical metric = {canonical}")
    return {"candidates": cand, "canonical": canonical, "pooled": pooled}


# ---------------------------------------------------------------------------
# ① liquidity dose-response (cond=C3)
# ---------------------------------------------------------------------------

def _level_dirs(ov: int, seed: int) -> Path:
    ratio = ov / 30
    label = "mmfcn_05x" if ratio == 0.5 else f"mmfcn_{int(ratio)}x"
    return DATA_DIR / "mmfcn_sensitivity" / f"{label}_{seed}"


def dose_response(canonical: str, pooled_ref: Dict,
                  logger: logging.Logger) -> pd.DataFrame:
    rows = []
    for ov in ORDER_VOLUMES:
        per_seed = []
        pooled_parts = []
        for seed in DOSE_SEEDS:
            if ov == 30:
                rt_f = DATA_DIR / "C3" / f"trial_{seed:04d}.parquet"
                lt_f = DATA_DIR / "C3" / f"lifetimes_{seed:04d}.parquet"
            else:
                d = _level_dirs(ov, seed)
                rt_f = d / f"trial_{seed:04d}.parquet"
                lt_f = d / f"lifetimes_{seed:04d}.parquet"
            if not rt_f.exists():
                continue
            rt = pd.read_parquet(rt_f, columns=["horizon", "delta_g"])
            lt = pd.read_parquet(lt_f, columns=["censored"])
            per_seed.append({
                "ov": ov, "seed": seed, "n_rt": len(rt),
                "censored_frac": float(lt["censored"].astype(bool).mean()),
                "funnel": candidate_metrics(rt)[canonical],
            })
            pooled_parts.append(rt)
        pooled_rt = pd.concat(pooled_parts, ignore_index=True)
        funnel_pooled = candidate_metrics(pooled_rt)[canonical]
        rows.append({
            "order_volume": ov,
            "n_seeds": len(per_seed),
            "n_rt_total": int(sum(p["n_rt"] for p in per_seed)),
            "n_rt_mean": float(np.mean([p["n_rt"] for p in per_seed])),
            "censored_frac_mean": float(np.mean([p["censored_frac"]
                                                 for p in per_seed])),
            "funnel_pooled": funnel_pooled,
            "funnel_per_seed_mean": float(np.nanmean([p["funnel"]
                                                      for p in per_seed])),
            "_per_seed": per_seed,
        })
        logger.info(f"[①] ov={ov}: n_rt_mean={rows[-1]['n_rt_mean']:.0f} "
                    f"censor={rows[-1]['censored_frac_mean']:.3f} "
                    f"funnel_pooled={funnel_pooled:+.3f}")

    # 単調性 (per-seed level): spearman(ov, funnel), (ov, n_rt), (ov, censor)
    flat = [p for r in rows for p in r["_per_seed"]]
    ovs = [p["ov"] for p in flat]
    mono = {
        "spearman_ov_funnel": _spear(ovs, [p["funnel"] for p in flat]),
        "spearman_ov_n_rt": _spear(ovs, [p["n_rt"] for p in flat]),
        "spearman_ov_censored": _spear(ovs, [p["censored_frac"] for p in flat]),
        "n_points": len(flat),
    }
    # agg 参照 (C0p、同 canonical)
    agg_ref = candidate_metrics(pooled_ref["C0p"])[canonical]
    logger.info(f"[①] monotonicity: {mono} | agg(C0p) ref funnel = {agg_ref:+.3f}")

    df = pd.DataFrame([{k: v for k, v in r.items() if k != "_per_seed"}
                       for r in rows])
    df.attrs["mono"] = mono
    df.attrs["agg_ref"] = float(agg_ref)
    df.attrs["per_seed"] = flat
    df.to_csv(OUTPUTS_DIR / "tables" / "tab_S7_doseresponse.csv", index=False)
    return df


# ---------------------------------------------------------------------------
# ② matched-horizon α/β probe (secondary、fill-selection bias 注意)
# ---------------------------------------------------------------------------

def matched_horizon_probe(pooled: Dict, logger: logging.Logger) -> pd.DataFrame:
    edges = np.linspace(np.log(1.0), np.log(1500.0), 13)
    rows = []
    for agg_c, lob_c in (("C0u", "C2"), ("C0p", "C3")):
        for cond in (agg_c, lob_c):
            rt = pooled[cond]
            m = rt["horizon"] <= 1500
            b = _bin_stats(rt.loc[m, "horizon"].to_numpy(float),
                           rt.loc[m, "delta_g"].to_numpy(float), edges=edges)
            b["pair"] = f"{agg_c}-vs-{lob_c}"
            b["cond"] = cond
            rows.append(b)
    out = pd.concat(rows, ignore_index=True)
    out.to_csv(OUTPUTS_DIR / "tables" / "tab_S7_matched_horizon.csv", index=False)
    # α/β 要約: 同一 bin での IQR 比 (LOB/agg) の中央値と、profile slope の差
    summaries = []
    for agg_c, lob_c in (("C0u", "C2"), ("C0p", "C3")):
        pair = f"{agg_c}-vs-{lob_c}"
        a = out[(out["pair"] == pair) & (out["cond"] == agg_c)]
        l = out[(out["pair"] == pair) & (out["cond"] == lob_c)]
        mrg = a.merge(l, on="bin_center_logh", suffixes=("_agg", "_lob"))
        ratio = (mrg["iqr_dG_lob"] / mrg["iqr_dG_agg"]).replace(
            [np.inf, -np.inf], np.nan)
        slope_a = _spear(a["bin_center_logh"], a["iqr_dG"])
        slope_l = _spear(l["bin_center_logh"], l["iqr_dG"])
        summaries.append({
            "pair": pair, "n_common_bins": len(mrg),
            "iqr_ratio_median": float(np.nanmedian(ratio)),
            "iqr_slope_agg": slope_a, "iqr_slope_lob": slope_l,
            "verdict": ("alpha-like (profile 同形)" if
                        np.isfinite(slope_a) and np.isfinite(slope_l)
                        and abs(slope_a - slope_l) < 0.3
                        else "beta-like (profile 変質)"),
        })
        logger.info(f"[②] {pair}: slope agg={slope_a:+.3f} lob={slope_l:+.3f} "
                    f"iqr_ratio_med={summaries[-1]['iqr_ratio_median']:.3f} "
                    f"→ {summaries[-1]['verdict']}")
    return pd.DataFrame(summaries)


# ---------------------------------------------------------------------------
# SF readout (C2/C3 vs FCN-only)
# ---------------------------------------------------------------------------

def _sf_stats(prices: np.ndarray) -> Dict[str, float]:
    r = np.diff(np.log(np.maximum(prices, 1e-9)))
    if r.size < 100:
        return {}
    absr = np.abs(r)

    def _acf(x, lag):
        if x.size <= lag or x.std() == 0:
            return float("nan")
        return float(np.corrcoef(x[:-lag], x[lag:])[0, 1])

    nz = absr[absr > 0]
    hill = float("nan")
    if nz.size >= 100:
        tail = np.sort(nz)[-max(int(0.05 * nz.size), 20):]
        hill = (float(1.0 / np.mean(np.log(tail / tail[0])))
                if tail[0] > 0 else float("nan"))
    return {
        "kurtosis_excess": float(sp_stats.kurtosis(r)),
        "acf_absr_1": _acf(absr, 1), "acf_absr_5": _acf(absr, 5),
        "acf_absr_10": _acf(absr, 10), "acf_absr_20": _acf(absr, 20),
        "acf_r_1": _acf(r, 1),
        "hill_alpha_absr": hill,
        "frac_zero_r": float((absr == 0).mean()),
        "n_obs": int(r.size),
    }


def sf_readout(logger: logging.Logger) -> pd.DataFrame:
    sources = {
        "C2_sg": sorted((DATA_DIR / "_s59_cticks" / "PhaseA").glob("prices_C2_*.parquet")),
        "C3_sg": sorted((DATA_DIR / "_s59_cticks" / "PhaseA").glob("prices_C3_*.parquet")),
        "FCN_only": sorted((DATA_DIR / "_s7_fcn_only").glob("prices_*.parquet")),
    }
    rows = []
    for label, files in sources.items():
        per = []
        for f in files:
            p = pd.read_parquet(f)["mid"].to_numpy(float)
            s = _sf_stats(p)
            if s:
                per.append(s)
        if not per:
            logger.warning(f"[SF] {label}: no data")
            continue
        med = {k: float(np.nanmedian([d[k] for d in per])) for k in per[0]}
        med["source"] = label
        med["n_seeds"] = len(per)
        rows.append(med)
        logger.info(f"[SF] {label} (n={len(per)}): kurt={med['kurtosis_excess']:+.2f} "
                    f"acf|r|(1/5/10)={med['acf_absr_1']:+.3f}/{med['acf_absr_5']:+.3f}/"
                    f"{med['acf_absr_10']:+.3f} hill={med['hill_alpha_absr']:.2f} "
                    f"zero_frac={med['frac_zero_r']:.2f}")
    out = pd.DataFrame(rows)
    out.to_csv(OUTPUTS_DIR / "tables" / "tab_S7_sf_readout.csv", index=False)
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    logger = setup_logger()
    (OUTPUTS_DIR / "tables").mkdir(parents=True, exist_ok=True)
    (OUTPUTS_DIR / "figures").mkdir(parents=True, exist_ok=True)
    logger.info("=" * 70)
    logger.info("S7 — freeze→funnel 統合分析 (③→①→②→SF)")
    logger.info("=" * 70)

    res3 = resolve_metric(logger)
    canonical = res3["canonical"]
    if canonical is None:
        logger.error("[③] canonical 指標が決まらない — 全候補が符号規則を満たさず。"
                     "tab_S7_metric_candidates.csv を確認して手動判定要")
        canonical = "M_iqr"  # 続行用 fallback (診断は出力済み)

    dr = dose_response(canonical, res3["pooled"], logger)
    mh = matched_horizon_probe(res3["pooled"], logger)
    sf = sf_readout(logger)

    # figure: dose-response 2 panel
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    ovs = dr["order_volume"].to_numpy()
    ax = axes[0]
    per_seed = dr.attrs["per_seed"]
    ax.scatter([p["ov"] for p in per_seed], [p["funnel"] for p in per_seed],
               alpha=0.5, s=18, label="per-seed")
    ax.plot(ovs, dr["funnel_pooled"], "o-", color="#d62728", label="pooled")
    ax.axhline(dr.attrs["agg_ref"], color="gray", linestyle="--",
               label=f"agg (C0p) ref = {dr.attrs['agg_ref']:+.2f}")
    ax.set_xscale("log")
    ax.set_xlabel("MMFCN order_volume (liquidity)")
    ax.set_ylabel(f"funnel strength ({canonical})")
    ax.legend(fontsize=8)
    mono = dr.attrs["mono"]
    ax.set_title(f"dose-response: ρ(ov, funnel) = "
                 f"{mono['spearman_ov_funnel']:+.2f}")
    ax = axes[1]
    ax.plot(ovs, dr["n_rt_mean"], "s-", color="#1f77b4", label="n_RT mean")
    ax2 = ax.twinx()
    ax2.plot(ovs, dr["censored_frac_mean"], "^-", color="#2ca02c",
             label="censored frac")
    ax.set_xscale("log")
    ax.set_xlabel("MMFCN order_volume")
    ax.set_ylabel("n_RT / trial", color="#1f77b4")
    ax2.set_ylabel("censored frac", color="#2ca02c")
    ax.set_title(f"mediators: ρ(ov,nRT)={mono['spearman_ov_n_rt']:+.2f}, "
                 f"ρ(ov,censor)={mono['spearman_ov_censored']:+.2f}")
    fig.tight_layout()
    fig.savefig(OUTPUTS_DIR / "figures" / "fig_S7_doseresponse.png",
                dpi=120, bbox_inches="tight")
    plt.close(fig)

    summary = {
        "stage": "S7",
        "canonical_funnel_metric": canonical,
        "metric_candidates": res3["candidates"].to_dict(orient="records"),
        "dose_response": dr.to_dict(orient="records"),
        "monotonicity": dr.attrs["mono"],
        "agg_ref_funnel": dr.attrs["agg_ref"],
        "matched_horizon": mh.to_dict(orient="records"),
        "sf_readout": sf.to_dict(orient="records"),
        "agg_diag_seeds_note": f"agg conds は seed {AGG_DIAG_SEEDS[0]}-"
                               f"{AGG_DIAG_SEEDS[-1]} subsample (メモリ対策)",
        "timestamp": datetime.now().isoformat(),
    }
    with open(LOGS_DIR / "S7_summary_for_diff.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
    logger.info("[output] saved: S7_summary_for_diff.json")
    logger.info("=" * 70)
    logger.info("S7 analysis complete")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
