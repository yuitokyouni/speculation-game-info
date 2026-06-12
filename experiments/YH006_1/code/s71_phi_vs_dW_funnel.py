"""S7.1 — funnel を φ (per-unit 認知利益) と ΔW=φ·q (実損益) で分解測定.

Yuito 指摘 (2026-06-12) の検証:
  「delta_g を除く / 使うことで RT の解釈が変わる」→ 根の問題は funnel を
  q-blind な φ で測っていたこと。富増幅機構は ΔW=φ·q に宿る。

測るもの (4 条件 C0u/C0p/C2/C3、per-seed → mean±95%CI):
  (1) 拡散指数 b: spread(X|τ) ~ τ^b の log-log OLS slope  (X ∈ {φ, ΔW})
      純拡散なら b≈0.5。富増幅があれば b_ΔW > b_φ。
  (2) zero 質量指数 a: P(φ=0|τ) ~ τ^{-a} の log-log OLS slope
      純拡散の原点復帰確率なら a≈0.5。spread と同じ √τ の裏表である事を示す。
  (3) Spearman M_iqr (S7 互換、単調性): φ と ΔW で
  (4) 増幅 = b_ΔW − b_φ、world contrast、wealth×world interaction

zero 除外は cherry-picking でなく、a と b が同じ拡散の裏表である事を数値で示す。

Run:
  cd experiments/YH006_1
  python -m code.s71_phi_vs_dW_funnel
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats as sp_stats

HERE = Path(__file__).resolve().parent
YH006_1 = HERE.parent
DATA_DIR = YH006_1 / "data"
OUTPUTS_DIR = YH006_1 / "outputs"
LOGS_DIR = YH006_1 / "logs"

AGG_SEEDS = list(range(1000, 1020))    # agg は 20 seed subsample (S7 と同じ、メモリ対策)
LOB_SEEDS = list(range(1000, 1100))    # LOB は全 100 seed
COMMON_SEEDS = list(range(1000, 1020))  # interaction の paired ref に使う共通 seed
CONDS = {
    "C0u": ("agg", AGG_SEEDS),
    "C0p": ("agg", AGG_SEEDS),
    "C2":  ("lob", LOB_SEEDS),
    "C3":  ("lob", LOB_SEEDS),
}
K_BINS = 12
MIN_BIN_COUNT = 30
MIN_VALID_BINS = 5


def setup_logger() -> logging.Logger:
    (LOGS_DIR / "runtime").mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("S71")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fh = logging.FileHandler(LOGS_DIR / "runtime" / f"{ts}_S71.log", encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    return logger


def _ols_slope(x: np.ndarray, y: np.ndarray) -> float:
    """log-log OLS slope。NaN/inf 除去後、点 < MIN_VALID_BINS なら NaN。"""
    m = np.isfinite(x) & np.isfinite(y)
    if m.sum() < MIN_VALID_BINS:
        return float("nan")
    sl = np.polyfit(x[m], y[m], 1)[0]
    return float(sl)


def _spear(x, y) -> float:
    x, y = np.asarray(x, float), np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    if m.sum() < 3:
        return float("nan")
    r = sp_stats.spearmanr(x[m], y[m]).correlation
    return float(r) if np.isfinite(r) else float("nan")


# matched support 用の共通 bin (cap=32、agg/LOB の p99 が共に内側に入る範囲)
H_CAP = 32
K_BINS_CAP = 10
COMMON_EDGES = np.linspace(np.log(1.0), np.log(float(H_CAP)), K_BINS_CAP + 1)


def per_seed_metrics(h: np.ndarray, phi: np.ndarray, q: np.ndarray,
                     edges: Optional[np.ndarray] = None,
                     h_cap: Optional[float] = None
                     ) -> Optional[Dict[str, float]]:
    """1 seed 分の bin profile から指数 b (φ/ΔW)、zero 指数 a、Spearman を返す。

    edges=None: 自前の log 等分 bin (full-range adaptive)。
    edges 指定: 共通 bin (matched support 比較用)。h_cap 指定で horizon を cap。
    """
    if h_cap is not None:
        keep = h <= h_cap
        h, phi, q = h[keep], phi[keep], q[keep]
    min_total = (K_BINS if edges is None else K_BINS_CAP) * MIN_BIN_COUNT
    if h.size < min_total:
        return None
    dW = phi * q
    log_h = np.log(np.maximum(h, 1.0))
    if log_h.max() <= log_h.min():
        return None
    if edges is None:
        edges = np.linspace(log_h.min(), log_h.max(), K_BINS + 1)

    centers, fz, iqr_phi, sd_phi, iqr_dW, sd_dW = [], [], [], [], [], []
    for i in range(len(edges) - 1):
        if i == len(edges) - 2:
            mk = (log_h >= edges[i]) & (log_h <= edges[i + 1])
        else:
            mk = (log_h >= edges[i]) & (log_h < edges[i + 1])
        if mk.sum() < MIN_BIN_COUNT:
            continue
        p = phi[mk]
        w = dW[mk]
        centers.append((edges[i] + edges[i + 1]) / 2.0)
        fz.append(float((p == 0).mean()))
        iqr_phi.append(float(np.subtract(*np.percentile(p, [75, 25]))))
        sd_phi.append(float(np.std(p)))
        iqr_dW.append(float(np.subtract(*np.percentile(w, [75, 25]))))
        sd_dW.append(float(np.std(w)))

    centers = np.asarray(centers)
    if centers.size < MIN_VALID_BINS:
        return None
    fz = np.asarray(fz)
    iqr_phi = np.asarray(iqr_phi); sd_phi = np.asarray(sd_phi)
    iqr_dW = np.asarray(iqr_dW); sd_dW = np.asarray(sd_dW)

    def _logy(arr):
        out = np.full_like(arr, np.nan, dtype=float)
        pos = arr > 0
        out[pos] = np.log(arr[pos])
        return out

    return {
        # 拡散指数 b (spread ~ τ^b): IQR / SD × φ / ΔW
        "b_phi_iqr": _ols_slope(centers, _logy(iqr_phi)),
        "b_phi_sd":  _ols_slope(centers, _logy(sd_phi)),
        "b_dW_iqr":  _ols_slope(centers, _logy(iqr_dW)),
        "b_dW_sd":   _ols_slope(centers, _logy(sd_dW)),
        # zero 質量指数 a: P(0)~τ^{-a} → slope = -a
        "a_zero":    -_ols_slope(centers, _logy(fz)),
        # Spearman (S7 互換、単調性)
        "M_iqr_phi": _spear(centers, iqr_phi),
        "M_iqr_dW":  _spear(centers, iqr_dW),
        "n_bins": int(centers.size),
        "n_rt": int(h.size),
    }


def _load_seed(cond: str, seed: int) -> Optional[pd.DataFrame]:
    world, _ = CONDS[cond]
    f = DATA_DIR / cond / f"trial_{seed:04d}.parquet"
    if not f.exists():
        return None
    return pd.read_parquet(f, columns=["horizon", "delta_g", "q"])


POOL_AGG_SEEDS = list(range(1000, 1010))  # pooled matched 用 agg 10 seed (メモリ対策)


def collect(logger: logging.Logger
            ) -> Tuple[pd.DataFrame, pd.DataFrame, Dict]:
    """full(adaptive) と matched(共通bin, cap=32) の per-seed 指標 + pooled matched。"""
    rows_full, rows_match = [], []
    pool = {c: [] for c in CONDS}   # pooled matched 用 (cap 後の h,phi,q)
    for cond, (world, seeds) in CONDS.items():
        for seed in seeds:
            df = _load_seed(cond, seed)
            if df is None:
                continue
            h = df["horizon"].to_numpy(np.float64)
            phi = df["delta_g"].to_numpy(np.float64)
            q = df["q"].to_numpy(np.float64)
            mf = per_seed_metrics(h, phi, q)
            if mf is not None:
                mf["cond"] = cond; mf["seed"] = seed
                rows_full.append(mf)
            mm = per_seed_metrics(h, phi, q, edges=COMMON_EDGES, h_cap=H_CAP)
            if mm is not None:
                mm["cond"] = cond; mm["seed"] = seed
                rows_match.append(mm)
            # pooled matched: LOB 全 seed、agg は 10 seed subsample
            if world == "lob" or seed in POOL_AGG_SEEDS:
                keep = h <= H_CAP
                pool[cond].append(np.column_stack([h[keep], phi[keep], q[keep]]))
        logger.info(f"[load] {cond} ({world}): "
                    f"full={sum(1 for r in rows_full if r['cond']==cond)} "
                    f"match={sum(1 for r in rows_match if r['cond']==cond)} seeds")

    pooled = {}
    for cond in CONDS:
        if not pool[cond]:
            continue
        arr = np.vstack(pool[cond])
        pm = per_seed_metrics(arr[:, 0], arr[:, 1], arr[:, 2], edges=COMMON_EDGES)
        pooled[cond] = pm
        logger.info(f"[pooled-matched cap={H_CAP}] {cond}: "
                    f"b_phi={pm['b_phi_iqr']:+.3f} b_dW={pm['b_dW_iqr']:+.3f} "
                    f"a_zero={pm['a_zero']:+.3f} n_rt={pm['n_rt']}")
    return pd.DataFrame(rows_full), pd.DataFrame(rows_match), pooled


def _mean_ci(vals: np.ndarray) -> Tuple[float, float, float]:
    v = vals[np.isfinite(vals)]
    if v.size < 2:
        return (float(np.mean(v)) if v.size else float("nan"),
                float("nan"), float("nan"))
    mean = float(np.mean(v))
    se = float(np.std(v, ddof=1) / np.sqrt(v.size))
    half = 1.96 * se
    return mean, mean - half, mean + half


def aggregate(df: pd.DataFrame, logger: logging.Logger) -> Dict:
    metrics = ["b_phi_iqr", "b_phi_sd", "b_dW_iqr", "b_dW_sd",
               "a_zero", "M_iqr_phi", "M_iqr_dW"]
    summary = {}
    for cond in CONDS:
        sub = df[df["cond"] == cond]
        rec = {"n_seeds": int(len(sub)),
               "n_rt_mean": float(sub["n_rt"].mean()) if len(sub) else float("nan")}
        for mt in metrics:
            mean, lo, hi = _mean_ci(sub[mt].to_numpy(float))
            rec[mt] = {"mean": mean, "ci_lo": lo, "ci_hi": hi}
        # 増幅 = b_dW − b_phi (per-seed で計算してから集計)
        amp_iqr = (sub["b_dW_iqr"].to_numpy(float) - sub["b_phi_iqr"].to_numpy(float))
        amean, alo, ahi = _mean_ci(amp_iqr)
        rec["amp_iqr"] = {"mean": amean, "ci_lo": alo, "ci_hi": ahi}
        summary[cond] = rec
        logger.info(
            f"[{cond}] b_phi_iqr={rec['b_phi_iqr']['mean']:+.3f} "
            f"b_dW_iqr={rec['b_dW_iqr']['mean']:+.3f} "
            f"amp={amean:+.3f} a_zero={rec['a_zero']['mean']:+.3f} "
            f"M_iqr(φ)={rec['M_iqr_phi']['mean']:+.3f} "
            f"M_iqr(ΔW)={rec['M_iqr_dW']['mean']:+.3f}")
    return summary


def _diff_ci(a: np.ndarray, b: np.ndarray) -> Tuple[float, float, float]:
    """独立 2 群の平均差 mean(a)-mean(b) ± 95%CI (SE 合成)。"""
    a = a[np.isfinite(a)]; b = b[np.isfinite(b)]
    if a.size < 2 or b.size < 2:
        return float("nan"), float("nan"), float("nan")
    d = float(np.mean(a) - np.mean(b))
    se = float(np.sqrt(np.var(a, ddof=1) / a.size + np.var(b, ddof=1) / b.size))
    return d, d - 1.96 * se, d + 1.96 * se


def contrasts(df: pd.DataFrame, logger: logging.Logger) -> Dict:
    def col(cond, mt):
        return df[df["cond"] == cond][mt].to_numpy(float)

    out = {}
    # world contrast on b_dW_iqr: agg vs LOB
    for pair, (agg_c, lob_c) in {"uniform": ("C0u", "C2"),
                                 "pareto": ("C0p", "C3")}.items():
        for mt in ("b_phi_iqr", "b_dW_iqr"):
            d, lo, hi = _diff_ci(col(agg_c, mt), col(lob_c, mt))
            out[f"world_{pair}_{mt}_aggMinusLob"] = {"d": d, "ci_lo": lo, "ci_hi": hi}

    # wealth×world interaction on b_dW_iqr と amp_iqr:
    # (LOB pareto − LOB uniform) − (agg pareto − agg uniform)
    for mt in ("b_phi_iqr", "b_dW_iqr"):
        lob_w = _diff_ci(col("C3", mt), col("C2", mt))
        agg_w = _diff_ci(col("C0p", mt), col("C0u", mt))
        # interaction の点推定と CI (4 群 SE 合成)
        c3, c2 = col("C3", mt), col("C2", mt)
        c0p, c0u = col("C0p", mt), col("C0u", mt)
        finite = [v[np.isfinite(v)] for v in (c3, c2, c0p, c0u)]
        if all(f.size >= 2 for f in finite):
            inter = float((np.mean(finite[0]) - np.mean(finite[1]))
                          - (np.mean(finite[2]) - np.mean(finite[3])))
            se = float(np.sqrt(sum(np.var(f, ddof=1) / f.size for f in finite)))
            out[f"interaction_{mt}"] = {"value": inter,
                                        "ci_lo": inter - 1.96 * se,
                                        "ci_hi": inter + 1.96 * se,
                                        "lob_wealth_effect": lob_w[0],
                                        "agg_wealth_effect": agg_w[0]}
            logger.info(f"[interaction] {mt}: {inter:+.3f} "
                        f"[{inter-1.96*se:+.3f},{inter+1.96*se:+.3f}] "
                        f"(LOB wealth eff={lob_w[0]:+.3f}, agg={agg_w[0]:+.3f})")
    # amp interaction (per-seed amp = b_dW - b_phi)
    amp = {c: (df[df["cond"] == c]["b_dW_iqr"].to_numpy(float)
               - df[df["cond"] == c]["b_phi_iqr"].to_numpy(float)) for c in CONDS}
    fin = {c: amp[c][np.isfinite(amp[c])] for c in CONDS}
    if all(fin[c].size >= 2 for c in CONDS):
        inter = float((np.mean(fin["C3"]) - np.mean(fin["C2"]))
                      - (np.mean(fin["C0p"]) - np.mean(fin["C0u"])))
        se = float(np.sqrt(sum(np.var(fin[c], ddof=1) / fin[c].size for c in CONDS)))
        out["interaction_amp_iqr"] = {"value": inter,
                                      "ci_lo": inter - 1.96 * se,
                                      "ci_hi": inter + 1.96 * se}
        logger.info(f"[interaction] amp_iqr: {inter:+.3f} "
                    f"[{inter-1.96*se:+.3f},{inter+1.96*se:+.3f}]")
    return out


def _pooled_profile(cond: str, seeds: List[int], h_cap: float
                    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """matched bin での pooled (bin_center_logh, IQR_phi, IQR_dW, frac_zero)。"""
    parts = []
    for seed in seeds:
        df = _load_seed(cond, seed)
        if df is None:
            continue
        h = df["horizon"].to_numpy(np.float64)
        keep = h <= h_cap
        parts.append(np.column_stack([h[keep],
                                      df["delta_g"].to_numpy(np.float64)[keep],
                                      df["q"].to_numpy(np.float64)[keep]]))
    arr = np.vstack(parts)
    h, phi, q = arr[:, 0], arr[:, 1], arr[:, 2]
    dW = phi * q
    log_h = np.log(np.maximum(h, 1.0))
    edges = COMMON_EDGES
    c, ip, iw, fz = [], [], [], []
    for i in range(len(edges) - 1):
        mk = ((log_h >= edges[i]) & (log_h <= edges[i + 1]) if i == len(edges) - 2
              else (log_h >= edges[i]) & (log_h < edges[i + 1]))
        if mk.sum() < MIN_BIN_COUNT:
            continue
        c.append((edges[i] + edges[i + 1]) / 2.0)
        ip.append(float(np.subtract(*np.percentile(phi[mk], [75, 25]))))
        iw.append(float(np.subtract(*np.percentile(dW[mk], [75, 25]))))
        fz.append(float((phi[mk] == 0).mean()))
    return (np.array(c), np.array(ip), np.array(iw), np.array(fz))


def make_figure(logger: logging.Logger) -> None:
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6))
    colors = {"C0u": "#1f77b4", "C0p": "#4c9be8",
              "C2": "#d62728", "C3": "#ff9896"}
    labels = {"C0u": "agg uniform", "C0p": "agg pareto",
              "C2": "LOB uniform", "C3": "LOB pareto"}
    profs = {}
    for cond, (world, seeds) in CONDS.items():
        use = POOL_AGG_SEEDS if world == "agg" else seeds
        profs[cond] = _pooled_profile(cond, use, H_CAP)
    def _masklog(arr):
        out = np.full_like(arr, np.nan, dtype=float)
        pos = arr > 0
        out[pos] = np.log(arr[pos])
        return out  # IQR=0 の bin (短 horizon で生じる) は描画しない

    for cond in CONDS:
        c, ip, iw, fz = profs[cond]
        pos = ip > 0
        b = np.polyfit(c[pos], np.log(ip[pos]), 1)[0] if pos.sum() >= 3 else float("nan")
        axes[0].plot(c, _masklog(ip), "o-", color=colors[cond],
                     label=f"{labels[cond]} (b={b:+.2f})")
        posw = iw > 0
        bw = np.polyfit(c[posw], np.log(iw[posw]), 1)[0] if posw.sum() >= 3 else float("nan")
        axes[1].plot(c, _masklog(iw), "o-", color=colors[cond],
                     label=f"{labels[cond]} (b={bw:+.2f})")
        axes[2].plot(c, fz, "o-", color=colors[cond], label=labels[cond])
    for ax, t, yl in zip(
            axes,
            ["funnel on φ (cognitive)", "funnel on ΔW = φ·q (wealth)",
             "zero-ΔG fraction"],
            ["log IQR(φ)", "log IQR(ΔW)", "P(ΔG=0)"]):
        ax.set_xlabel("log horizon (matched support, h≤32)")
        ax.set_ylabel(yl); ax.set_title(t); ax.legend(fontsize=7)
    fig.suptitle("S7.1: funnel exponent — agg steep (b≈0.36) vs LOB flat (b≈0.13), "
                 "matched horizon support", fontsize=11)
    fig.tight_layout()
    out = OUTPUTS_DIR / "figures" / "fig_S71_phi_vs_dW_funnel.png"
    fig.savefig(out, dpi=120, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"[figure] {out}")


def main() -> None:
    logger = setup_logger()
    (OUTPUTS_DIR / "tables").mkdir(parents=True, exist_ok=True)
    logger.info("=" * 70)
    logger.info("S7.1 — φ vs ΔW funnel 分解 (拡散指数 b / zero 指数 a / Spearman)")
    logger.info("=" * 70)

    df_full, df_match, pooled = collect(logger)
    df_full.to_csv(OUTPUTS_DIR / "tables" / "tab_S71_per_seed_full.csv", index=False)
    df_match.to_csv(OUTPUTS_DIR / "tables" / "tab_S71_per_seed_matched.csv", index=False)
    logger.info("--- FULL range (adaptive per-seed bins) ---")
    summ_full = aggregate(df_full, logger)
    cons_full = contrasts(df_full, logger)
    logger.info(f"--- MATCHED support (common bins, horizon<={H_CAP}) ---")
    summ_match = aggregate(df_match, logger)
    cons_match = contrasts(df_match, logger)

    out = {
        "stage": "S7.1",
        "purpose": "funnel を φ(q-blind) と ΔW=φ·q(富増幅) で分解、拡散指数 b と "
                   "zero 指数 a を log-log OLS で測定。full range と "
                   f"matched support (共通bin, horizon<={H_CAP}) の両方。",
        "design": {"K_BINS_full": K_BINS, "K_BINS_cap": K_BINS_CAP,
                   "H_CAP": H_CAP, "MIN_BIN_COUNT": MIN_BIN_COUNT,
                   "agg_seeds": f"{AGG_SEEDS[0]}-{AGG_SEEDS[-1]} (20 subsample)",
                   "lob_seeds": f"{LOB_SEEDS[0]}-{LOB_SEEDS[-1]} (100)"},
        "per_condition_full": summ_full,
        "per_condition_matched": summ_match,
        "pooled_matched": pooled,
        "contrasts_full": cons_full,
        "contrasts_matched": cons_match,
        "interpretation_keys": {
            "b≈0.5": "純拡散 (有界ランダムウォーク Σh の √τ)",
            "b_dW>b_phi": "q による富増幅が funnel を超拡散化",
            "a≈0.5": "zero 質量 P(0)~1/√τ も同じ拡散の裏表 (zero 除外は cherry-pick でない)",
        },
        "timestamp": datetime.now().isoformat(),
    }
    with open(LOGS_DIR / "S71_summary_for_diff.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False, default=str)
    make_figure(logger)
    logger.info("[output] S71_summary_for_diff.json + tab_S71_per_seed_*.csv")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
