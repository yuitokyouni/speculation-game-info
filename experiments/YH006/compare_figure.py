"""5 figure × 4 条件 = 20 panel 比較図を生成.

YH005/analysis.py の plot_* を直接流用できる部分は流用、panel grid は
matplotlib の subplots で自前組立て。C0 は phase1_metrics.json から再構成
(生配列がないので、ヒストグラム/統計量を fit 直線で再現)。
"""

from __future__ import annotations

import pickle
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "YH005"))
sys.path.insert(0, str(HERE))

from load_c0 import load_c0_metrics  # noqa: E402


COND_ORDER = ["C0", "C1", "C2", "C3"]
COND_LABEL = {
    "C0": "C0 (aggregate-demand)",
    "C1": "C1 (LOB FCN only)",
    "C2": "C2 (LOB + SG uniform)",
    "C3": "C3 (LOB + SG Pareto)",
}
ROW_LABEL = [
    "Fig A: wealth CCDF",
    "Fig B: round-trip horizon",
    "Fig C: |ΔG| vs horizon",
    "Fig D: hold ratio",
    "Fig E: order size ts",
]


def _load_results(outputs_dir: Path) -> Dict[str, Any]:
    """C1/C2/C3 の pkl + C0 metrics を読む。欠損は None で埋める。"""
    results: Dict[str, Any] = {}
    for cond in ("C1", "C2", "C3"):
        p = outputs_dir / f"{cond}_result.pkl"
        if p.exists():
            with open(p, "rb") as f:
                results[cond] = pickle.load(f)
        else:
            results[cond] = None
    try:
        results["C0"] = load_c0_metrics()
    except FileNotFoundError:
        results["C0"] = None
    return results


# ---------------------------------------------------------------------------
# Panel-level draw functions (C0 vs C1-C3 で入力 schema が違うので分岐)
# ---------------------------------------------------------------------------

def _panel_wealth(ax, cond: str, data, c0_metrics: Optional[Dict]) -> Optional[Dict]:
    if cond == "C0":
        if c0_metrics is None:
            ax.text(0.5, 0.5, "C0 missing", ha="center", transform=ax.transAxes)
            return None
        w = c0_metrics["wealth"]
        alpha = w["alpha_hill_xmin_p90"]
        xmin = w["xmin_p90"]
        n_tail = w["n_tail"]
        n = w["num_agents"]
        # fit line only
        x_line = np.logspace(np.log10(max(xmin, 1)), np.log10(w.get("max_wealth", xmin * 3)), 50)
        y_line = (n_tail / n) * (x_line / max(xmin, 1)) ** (-alpha)
        ax.loglog(x_line, y_line, "r--", linewidth=1.2,
                  label=f"α={alpha:.2f}\nmedian={w['median_wealth']:.0f}\nmax={w['max_wealth']:.0f}")
        ax.legend(loc="upper right", fontsize=8)
        return {"alpha": alpha, "median": w["median_wealth"], "max": w["max_wealth"]}
    if data is None:
        ax.text(0.5, 0.5, f"{cond} missing", ha="center", transform=ax.transAxes)
        return None
    w = np.asarray(data["final_wealth"], dtype=np.float64)
    w_pos = w[w > 0]
    if w_pos.size < 2:
        ax.text(0.5, 0.5, f"no positive wealth\n(min={w.min():.0f})", ha="center", transform=ax.transAxes)
        return {"alpha": float("nan"), "num_positive": int(w_pos.size)}
    sorted_w = np.sort(w_pos)
    n = sorted_w.size
    ccdf = 1.0 - np.arange(n) / n
    ax.loglog(sorted_w, ccdf, marker=".", linestyle="none", markersize=3)
    # Hill α with xmin = p90
    xmin = float(np.percentile(w_pos, 90))
    tail = w_pos[w_pos >= xmin]
    if tail.size >= 2 and xmin > 0:
        log_ratio = np.log(tail / xmin).mean()
        alpha = 1.0 / log_ratio if log_ratio > 0 else float("nan")
        if np.isfinite(alpha):
            x_line = np.logspace(np.log10(xmin), np.log10(sorted_w.max()), 50)
            y_line = (tail.size / n) * (x_line / xmin) ** (-alpha)
            ax.loglog(x_line, y_line, "r--", linewidth=1.0, label=f"α={alpha:.2f}")
            ax.legend(loc="upper right", fontsize=8)
    else:
        alpha = float("nan")
    return {
        "alpha": float(alpha),
        "median": float(np.median(w_pos)),
        "max": float(w_pos.max()),
        "num_positive": int(n),
    }


def _panel_horizon(ax, cond: str, data, c0_metrics: Optional[Dict]) -> Optional[Dict]:
    if cond == "C0":
        if c0_metrics is None:
            ax.text(0.5, 0.5, "C0 missing", ha="center", transform=ax.transAxes)
            return None
        h = c0_metrics["horizon"]
        ax.text(0.5, 0.7,
                f"K={h['num_round_trips']:,}\n"
                f"median={h['median_horizon']:.1f}\n"
                f"mean={h['mean_horizon']:.2f}\n"
                f"max={h['max_horizon']}",
                ha="center", va="center", transform=ax.transAxes, fontsize=9)
        ax.set_xticks([]); ax.set_yticks([])
        return h
    if data is None:
        ax.text(0.5, 0.5, f"{cond} missing", ha="center", transform=ax.transAxes)
        return None
    rt = data["round_trips"]
    if rt["open_t"].size == 0:
        ax.text(0.5, 0.5, f"no round-trips", ha="center", transform=ax.transAxes)
        return {"num_round_trips": 0}
    horizon = (rt["close_t"] - rt["open_t"]).astype(np.int64)
    horizon = horizon[horizon > 0]
    k = horizon.size
    if k == 0:
        ax.text(0.5, 0.5, "all horizon <= 0", ha="center", transform=ax.transAxes)
        return {"num_round_trips": 0}
    h_min = max(1, int(horizon.min()))
    h_max = int(horizon.max())
    if h_max <= h_min:
        bins = np.array([h_min, h_min + 1])
    else:
        bins = np.logspace(np.log10(h_min), np.log10(h_max + 1), 30)
    counts, edges = np.histogram(horizon, bins=bins)
    centers = 0.5 * (edges[:-1] + edges[1:])
    nz = counts > 0
    ax.loglog(centers[nz], counts[nz], marker="o", linestyle="-", markersize=3)
    return {
        "num_round_trips": int(k),
        "median_horizon": float(np.median(horizon)),
        "mean_horizon": float(horizon.mean()),
        "max_horizon": int(horizon.max()),
    }


def _panel_deltaG(ax, cond: str, data, c0_metrics: Optional[Dict]) -> Optional[Dict]:
    if cond == "C0":
        if c0_metrics is None:
            ax.text(0.5, 0.5, "C0 missing", ha="center", transform=ax.transAxes)
            return None
        d = c0_metrics["deltaG_vs_horizon"]
        ax.text(0.5, 0.6,
                f"corr(|ΔG|,h)={d['corr_horizon_abs_dG']:.3f}\n"
                f"mean|ΔG|={d['mean_abs_dG']:.2f}\n"
                f"frac+={d['frac_positive_dG']:.3f}\n"
                f"frac-={d['frac_negative_dG']:.3f}",
                ha="center", va="center", transform=ax.transAxes, fontsize=9)
        ax.set_xticks([]); ax.set_yticks([])
        return d
    if data is None:
        ax.text(0.5, 0.5, f"{cond} missing", ha="center", transform=ax.transAxes)
        return None
    rt = data["round_trips"]
    if rt["open_t"].size == 0:
        ax.text(0.5, 0.5, "no round-trips", ha="center", transform=ax.transAxes)
        return {"num_round_trips": 0}
    horizon = (rt["close_t"] - rt["open_t"]).astype(np.int64)
    dG = rt["delta_G"].astype(np.float64)
    mask = horizon > 0
    horizon = horizon[mask]
    dG = dG[mask]
    k = horizon.size
    if k == 0:
        ax.text(0.5, 0.5, "no round-trips", ha="center", transform=ax.transAxes)
        return {"num_round_trips": 0}
    ax.hexbin(horizon, dG, gridsize=30, bins="log", cmap="viridis", mincnt=1)
    ax.axhline(0, color="red", linewidth=0.6, alpha=0.6)
    abs_dG = np.abs(dG)
    corr = float(np.corrcoef(horizon.astype(np.float64), abs_dG)[0, 1]) if k > 1 else float("nan")
    return {
        "num_round_trips": int(k),
        "corr_horizon_abs_dG": corr,
        "mean_abs_dG": float(abs_dG.mean()),
        "frac_positive_dG": float((dG > 0).mean()),
        "frac_negative_dG": float((dG < 0).mean()),
    }


def _panel_hold(ax, cond: str, data, c0_metrics: Optional[Dict]) -> Optional[Dict]:
    if cond == "C0":
        if c0_metrics is None:
            ax.text(0.5, 0.5, "C0 missing", ha="center", transform=ax.transAxes)
            return None
        h = c0_metrics["hold_ratio"]
        ratios = {k: float(h.get(k, 0.0)) for k in ["idle", "active_hold", "passive_hold", "buy", "sell"]}
    elif data is None:
        ax.text(0.5, 0.5, f"{cond} missing", ha="center", transform=ax.transAxes)
        return None
    else:
        num_buy = np.asarray(data["num_buy"], dtype=np.float64)
        num_sell = np.asarray(data["num_sell"], dtype=np.float64)
        num_act = np.asarray(data["num_active_hold"], dtype=np.float64)
        num_pas = np.asarray(data["num_passive_hold"], dtype=np.float64)
        N_est = int((num_buy + num_sell + num_act + num_pas).max()) if num_buy.size else 0
        if N_est == 0:
            ax.text(0.5, 0.5, "no SG activity", ha="center", transform=ax.transAxes)
            return {"N_est": 0}
        num_idle = np.clip(N_est - (num_buy + num_sell + num_act + num_pas), 0.0, None)
        ratios = {
            "idle": float(num_idle.mean() / N_est),
            "active_hold": float(num_act.mean() / N_est),
            "passive_hold": float(num_pas.mean() / N_est),
            "buy": float(num_buy.mean() / N_est),
            "sell": float(num_sell.mean() / N_est),
        }
    labels = ["idle", "active_hold", "passive_hold", "buy", "sell"]
    colors = ["#cccccc", "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]
    bottom = 0.0
    for lab, col in zip(labels, colors):
        v = ratios[lab]
        ax.bar(0, v, bottom=bottom, color=col, width=0.5)
        bottom += v
    ax.set_xticks([])
    ax.set_ylim(0, 1)
    ax.text(1.1, 0.5,
            "\n".join([f"{k[:7]}: {v:.2f}" for k, v in ratios.items()]),
            transform=ax.transAxes, fontsize=7, va="center")
    return ratios


def _panel_order_ts(ax, cond: str, data, c0_metrics: Optional[Dict]) -> Optional[Dict]:
    if cond == "C0":
        if c0_metrics is None:
            ax.text(0.5, 0.5, "C0 missing", ha="center", transform=ax.transAxes)
            return None
        o = c0_metrics["order_size"]
        ax.text(0.5, 0.6,
                f"mean(small)={o['mean_small']:.0f}\n"
                f"mean(medium)={o['mean_medium']:.1f}\n"
                f"mean(large)={o['mean_large']:.2f}\n"
                f"peak(large)={o['peak_large']}",
                ha="center", va="center", transform=ax.transAxes, fontsize=9)
        ax.set_xticks([]); ax.set_yticks([])
        return o
    if data is None:
        ax.text(0.5, 0.5, f"{cond} missing", ha="center", transform=ax.transAxes)
        return None
    sz = data["num_orders_by_size"]  # (T, 3)
    T = sz.shape[0]
    x = np.arange(T)
    ax.plot(x, sz[:, 0], color="#1f77b4", linewidth=0.4, label="small")
    ax.plot(x, sz[:, 1], color="#ff7f0e", linewidth=0.4, label="medium")
    ax.plot(x, sz[:, 2], color="#d62728", linewidth=0.6, label="large")
    ax.legend(fontsize=7, loc="upper right")
    return {
        "mean_small": float(sz[:, 0].mean()),
        "mean_medium": float(sz[:, 1].mean()),
        "mean_large": float(sz[:, 2].mean()),
        "peak_small": int(sz[:, 0].max()),
        "peak_medium": int(sz[:, 1].max()),
        "peak_large": int(sz[:, 2].max()),
    }


PANEL_FNS = [_panel_wealth, _panel_horizon, _panel_deltaG, _panel_hold, _panel_order_ts]


def main() -> None:
    outputs_dir = HERE / "outputs"
    outputs_dir.mkdir(exist_ok=True)
    results = _load_results(outputs_dir)
    c0_metrics = results["C0"]

    fig, axes = plt.subplots(5, 4, figsize=(18, 20))
    metrics_summary: Dict[str, Dict[str, Any]] = {cond: {} for cond in COND_ORDER}

    for row_idx, fn in enumerate(PANEL_FNS):
        for col_idx, cond in enumerate(COND_ORDER):
            ax = axes[row_idx, col_idx]
            data = results[cond] if cond != "C0" else None
            try:
                m = fn(ax, cond, data, c0_metrics)
            except Exception as e:
                ax.text(0.5, 0.5, f"error:\n{e}", ha="center", transform=ax.transAxes, fontsize=7)
                m = {"error": str(e)}
            if m is not None:
                metrics_summary[cond][ROW_LABEL[row_idx]] = m
            if row_idx == 0:
                ax.set_title(COND_LABEL[cond], fontsize=11)
            if col_idx == 0:
                ax.set_ylabel(ROW_LABEL[row_idx], fontsize=10)

    fig.suptitle("YH006: Speculation Game on LOB — 5 figures × 4 conditions", fontsize=14)
    fig.tight_layout(rect=[0, 0, 1, 0.98])
    out_png = outputs_dir / "yh006_comparison_5x4.png"
    fig.savefig(out_png, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"[compare] saved: {out_png}")

    # JSON dump of metrics
    import json

    def _clean(o):
        if isinstance(o, dict):
            return {k: _clean(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [_clean(v) for v in o]
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            v = float(o)
            return v if np.isfinite(v) else None
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, float) and not np.isfinite(o):
            return None
        return o

    out_json = outputs_dir / "yh006_metrics.json"
    with open(out_json, "w") as f:
        json.dump(_clean(metrics_summary), f, indent=2, default=str)
    print(f"[compare] saved: {out_json}")


if __name__ == "__main__":
    main()
