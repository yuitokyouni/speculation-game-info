"""S7.2 — 認知価格 P(t) の無条件 structure function で β vs selection を分離.

Yuito 指示 (2026-06-12): S7.1 の「LOB funnel slope ~3倍圧縮 (β寄り)」は
completion-selection (凍結で長 RT の完了 RT が fill-lucky 部分集合に偏る) と
同型の signature。分離が #2(i) を finding にするゲート。

faithful な位置依存版 (全 open position の未実現 |Δφ|) は P(t)・凍結 position が
parquet に永続化されておらず、LOB は PAMS (=Mac) 再走が要る。
本 stage はその前に Windows で決着できる **無条件 structure function** で gate を引く:

  S(h) = IQR_t( P(t+h) − P(t) )   全 t 窓、position を一切参照しない

P(t) = 認知価格 (global、cumsum of quantized price move)。
position を参照しないので completion-selection も fill-luck も原理的に入らない。
funnel φ = a·(P(t_close)−P(t_open)) は S(h) 母集団の (選択された) 部分標本なので、
S(h) の指数 b_struct を agg/LOB で比べれば「認知価格過程そのものが違うか」が分かる:

  - b_struct(LOB) ≈ b_struct(agg)         → 完了RT の圧縮 (0.13) は selection → α
  - b_struct(LOB) ≪ b_struct(agg) ≈ 0.13  → 認知過程が本当にフラット        → β

データ源:
  agg (C0u/C0p): simulate_aggregate を再走 (Windows OK, PAMS 不要, 決定的) → cognitive_prices
  LOB (C2/C3):   既存 data/_s59_cticks/PhaseA/prices_*.parquet (6 seed, c_ticks=28)
                 から P(t)=cumsum(quantize(Δmid, 28)) を再構成

Run:
  cd experiments/YH006_1
  python -m code.s72_cognitive_structure_function
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

HERE = Path(__file__).resolve().parent
YH006_1 = HERE.parent
YH006 = YH006_1.parent / "YH006"
for _p in (str(HERE), str(YH006_1), str(YH006)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from aggregate_sim import simulate_aggregate  # noqa: E402
from config import AGG_PARAMS, PARETO_ALPHA, PARETO_XMIN  # noqa: E402

DATA_DIR = YH006_1 / "data"
OUTPUTS_DIR = YH006_1 / "outputs"
LOGS_DIR = YH006_1 / "logs"
PRICE_DIR = DATA_DIR / "_s59_cticks" / "PhaseA"

SEEDS = list(range(1000, 1006))     # LOB 価格ファイルが存在する 6 seed に揃える
C_TICKS_LOB = 28.0                  # LOB price 系列の生成時 c_ticks (baseline, S5.9 c_ticks_in)
C_AGG = 3.0
H_MAX = 32                          # matched support (S7.1 と同じ cap)
LAGS = list(range(1, H_MAX + 1))


def setup_logger() -> logging.Logger:
    (LOGS_DIR / "runtime").mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("S72")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    sh = logging.StreamHandler(); sh.setFormatter(fmt); logger.addHandler(sh)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fh = logging.FileHandler(LOGS_DIR / "runtime" / f"{ts}_S72.log", encoding="utf-8")
    fh.setFormatter(fmt); logger.addHandler(fh)
    return logger


def quantize(dp: np.ndarray, C: float) -> np.ndarray:
    """history.quantize_price_change のベクトル版 (>C→2, >0→1, ==0→0, >=-C→-1, else -2)."""
    out = np.zeros_like(dp, dtype=np.int8)
    out[dp > C] = 2
    out[(dp > 0) & (dp <= C)] = 1
    out[(dp < 0) & (dp >= -C)] = -1
    out[dp < -C] = -2
    return out


def structure_function(P: np.ndarray, lags: List[int]) -> Tuple[np.ndarray, np.ndarray]:
    """S(h) = IQR_t(P(t+h)−P(t))、および SD 版。lags ごとに返す。"""
    iqr = np.full(len(lags), np.nan)
    sd = np.full(len(lags), np.nan)
    for i, h in enumerate(lags):
        if P.size <= h:
            continue
        d = P[h:].astype(np.float64) - P[:-h].astype(np.float64)
        iqr[i] = float(np.subtract(*np.percentile(d, [75, 25])))
        sd[i] = float(np.std(d))
    return iqr, sd


def fit_exponent(lags: List[int], spread: np.ndarray) -> float:
    """log spread = b·log h + c の OLS slope b。spread<=0 の lag は除外。"""
    x = np.log(np.asarray(lags, float))
    y = spread.copy()
    m = np.isfinite(y) & (y > 0)
    if m.sum() < 5:
        return float("nan")
    return float(np.polyfit(x[m], np.log(y[m]), 1)[0])


def agg_cognitive_price(cond: str, seed: int) -> np.ndarray:
    kwargs = dict(AGG_PARAMS)
    kwargs["wealth_mode"] = "uniform" if cond == "C0u" else "pareto"
    if kwargs["wealth_mode"] == "pareto":
        kwargs["pareto_alpha"] = PARETO_ALPHA
        kwargs["pareto_xmin"] = PARETO_XMIN
    res = simulate_aggregate(seed=seed, **kwargs)
    return res["cognitive_prices"].astype(np.int64), res["round_trips"]


def lob_cognitive_price(cond: str, seed: int) -> Optional[np.ndarray]:
    f = PRICE_DIR / f"prices_{cond}_{seed}.parquet"
    if not f.exists():
        return None
    mid = pd.read_parquet(f)["mid"].to_numpy(np.float64)
    dmid = np.diff(mid, prepend=mid[0])    # Δmid(t), t=0 は 0
    h = quantize(dmid, C_TICKS_LOB)
    return np.cumsum(h).astype(np.int64)


def _mean_ci(vals: np.ndarray) -> Tuple[float, float, float]:
    v = vals[np.isfinite(vals)]
    if v.size < 2:
        return (float(np.mean(v)) if v.size else float("nan"), float("nan"), float("nan"))
    m = float(np.mean(v)); se = float(np.std(v, ddof=1) / np.sqrt(v.size))
    return m, m - 1.96 * se, m + 1.96 * se


def parity_check_lob(logger: logging.Logger) -> Dict:
    """再構成 P(t) が in-sim 認知と一致するか: 完了RT delta_g と照合 (同一 run 前提が要)。"""
    out = {}
    for cond in ("C2", "C3"):
        P = lob_cognitive_price(cond, 1000)
        tf = DATA_DIR / cond / "trial_1000.parquet"
        if P is None or not tf.exists():
            continue
        rt = pd.read_parquet(tf, columns=["t_open", "t_close", "direction", "delta_g"])
        rt = rt[rt["t_close"] < P.size]
        recon = rt["direction"].to_numpy() * (P[rt["t_close"].to_numpy()]
                                              - P[rt["t_open"].to_numpy()])
        match = float(np.mean(recon == rt["delta_g"].to_numpy()))
        out[cond] = {"frac_match": match, "n": int(len(rt))}
        logger.info(f"[parity] {cond}: 再構成 P vs trial delta_g 一致率 = {match:.3f} "
                    f"(n={len(rt)}) — 1.0 なら S5.9 prices と S3 RT が同一 run")
    return out


def run_condition(cond: str, world: str, logger: logging.Logger) -> Dict:
    per_seed_b_iqr, per_seed_b_sd = [], []
    pooled_iqr = np.zeros(len(LAGS)); pooled_iqr_cnt = np.zeros(len(LAGS))
    # pooled は per-seed の S(h) を平均 (lag ごと)
    s_iqr_stack = []
    for seed in SEEDS:
        if world == "agg":
            P, _ = agg_cognitive_price(cond, seed)
        else:
            P = lob_cognitive_price(cond, seed)
        if P is None:
            continue
        iqr, sd = structure_function(P, LAGS)
        s_iqr_stack.append(iqr)
        per_seed_b_iqr.append(fit_exponent(LAGS, iqr))
        per_seed_b_sd.append(fit_exponent(LAGS, sd))
    s_iqr_mean = np.nanmean(np.vstack(s_iqr_stack), axis=0) if s_iqr_stack else None
    b_pooled = fit_exponent(LAGS, s_iqr_mean) if s_iqr_mean is not None else float("nan")
    m_iqr, lo_iqr, hi_iqr = _mean_ci(np.asarray(per_seed_b_iqr))
    m_sd, _, _ = _mean_ci(np.asarray(per_seed_b_sd))
    logger.info(f"[{cond}] b_struct(IQR) per-seed mean = {m_iqr:+.3f} "
                f"[{lo_iqr:+.3f},{hi_iqr:+.3f}]  pooled = {b_pooled:+.3f}  "
                f"b_struct(SD) = {m_sd:+.3f}  (n_seed={len(per_seed_b_iqr)})")
    return {"cond": cond, "world": world,
            "b_struct_iqr_mean": m_iqr, "b_struct_iqr_ci": [lo_iqr, hi_iqr],
            "b_struct_iqr_pooled": b_pooled, "b_struct_sd_mean": m_sd,
            "n_seed": len(per_seed_b_iqr),
            "S_iqr_pooled_by_lag": (s_iqr_mean.tolist() if s_iqr_mean is not None else None)}


def main() -> None:
    logger = setup_logger()
    (OUTPUTS_DIR / "tables").mkdir(parents=True, exist_ok=True)
    (OUTPUTS_DIR / "figures").mkdir(parents=True, exist_ok=True)
    logger.info("=" * 70)
    logger.info("S7.2 — 認知価格 structure function (β vs selection 分離 gate)")
    logger.info("=" * 70)

    parity = parity_check_lob(logger)
    results = {}
    for cond, world in (("C0u", "agg"), ("C0p", "agg"), ("C2", "lob"), ("C3", "lob")):
        results[cond] = run_condition(cond, world, logger)

    # 判定
    b = {c: results[c]["b_struct_iqr_mean"] for c in results}
    agg_ref = np.nanmean([b["C0u"], b["C0p"]])
    lob_ref = np.nanmean([b["C2"], b["C3"]])
    ratio = lob_ref / agg_ref if agg_ref else float("nan")
    if ratio >= 0.75:
        verdict = ("α 寄り: 認知過程の structure function 指数が agg/LOB でほぼ同じ "
                   "→ 完了RT funnel の圧縮 (S7.1 の 0.13) は selection 由来の公算大")
    elif ratio <= 0.5:
        verdict = ("β 寄り: LOB の認知価格過程そのものが agg より大幅にフラット "
                   "→ S7.1 の slope 圧縮は selection だけでは説明できない (機構変質)")
    else:
        verdict = "中間: selection と機構の両方が寄与している可能性"
    logger.info("-" * 70)
    logger.info(f"[判定] b_struct: agg={agg_ref:+.3f} LOB={lob_ref:+.3f} "
                f"ratio(LOB/agg)={ratio:.2f}")
    logger.info(f"[判定] {verdict}")
    logger.info(f"[参照] S7.1 完了RT b_φ: agg≈0.36 / LOB≈0.13 (ratio≈0.36)")

    # figure: S(h) log-log, 4 cond
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7, 5.2))
    colors = {"C0u": "#1f77b4", "C0p": "#4c9be8", "C2": "#d62728", "C3": "#ff9896"}
    labels = {"C0u": "agg uniform", "C0p": "agg pareto",
              "C2": "LOB uniform", "C3": "LOB pareto"}
    for cond in results:
        s = results[cond]["S_iqr_pooled_by_lag"]
        if s is None:
            continue
        s = np.asarray(s, float)
        msk = np.isfinite(s) & (s > 0)
        ax.plot(np.asarray(LAGS)[msk], s[msk], "o-", color=colors[cond],
                label=f"{labels[cond]} (b={results[cond]['b_struct_iqr_mean']:+.2f})")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("lag h (cognitive-price steps, matched support h≤32)")
    ax.set_ylabel("IQR( P(t+h) − P(t) )  [structure function]")
    ax.set_title(f"S7.2 unconditional cognitive structure function\n"
                 f"agg b≈{agg_ref:.2f} vs LOB b≈{lob_ref:.2f} "
                 f"(ratio {ratio:.2f}); cf S7.1 completed-RT ratio 0.36")
    ax.legend(fontsize=8)
    fig.tight_layout()
    figpath = OUTPUTS_DIR / "figures" / "fig_S72_structure_function.png"
    fig.savefig(figpath, dpi=120, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"[figure] {figpath}")

    summary = {
        "stage": "S7.2",
        "purpose": "認知価格 P(t) の無条件 structure function で β vs selection を分離",
        "design": {"seeds": SEEDS, "H_MAX": H_MAX, "c_ticks_lob": C_TICKS_LOB,
                   "agg_source": "simulate_aggregate 再走 (cognitive_prices)",
                   "lob_source": "data/_s59_cticks/PhaseA/prices_*.parquet 再構成"},
        "parity_lob_recon_vs_trial": parity,
        "per_condition": {c: {k: v for k, v in results[c].items()
                              if k != "S_iqr_pooled_by_lag"} for c in results},
        "b_struct_agg": agg_ref, "b_struct_lob": lob_ref, "ratio_lob_agg": ratio,
        "s71_completed_rt_ratio": 0.36,
        "verdict": verdict,
        "caveat": "無条件 structure function は position を参照しない (完全 de-selection)。"
                  "位置依存の faithful 版 (全 open position の未実現 |Δφ|、凍結含む) は "
                  "P(t)・凍結 entry が未永続化のため LOB=Mac 再走が要る (#4 継続)。",
        "timestamp": datetime.now().isoformat(),
    }
    with open(LOGS_DIR / "S72_summary_for_diff.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
    logger.info("[output] S72_summary_for_diff.json")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
