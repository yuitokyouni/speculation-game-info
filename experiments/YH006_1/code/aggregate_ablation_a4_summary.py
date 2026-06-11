"""S6r aggregation — A4 (wealth shuffle) 対称 DiD + plan §0.4 KPI 判定.

S6r plan §0.4 (pre-registered):
  Primary:   pooled bin_var_slope (seed-cluster bootstrap CI)。
             A4 interaction = (C3_A4 − C2_A4) − (C0p − C0u)、
             pooled shrinkage = S3_int − A4_int の CI が 0 を排除 + |A4| < |S3|
             → 仮説 A revised 支持
  Secondary: trial-level seed-paired shrinkage の bootstrap CI (0 排除 + 縮小方向)
  参考:      旧 L3 ratio (分母不安定のため判定に使わない)
  Manipulation check (成功条件ではない): wealth_persistence_rho、corr_winit_wt_Tk
  非特異的効果の監視: C2_A4 − C2

Run (Mac、ensemble 完走後):
  cd experiments/YH006_1
  python -m code.aggregate_ablation_a4_summary
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

A4_CONDS = ["C2_A4", "C3_A4"]
EXISTING_6_CONDS = ["C0u", "C0p", "C2", "C3", "C2_A1", "C3_A1"]
ALL_8_CONDS = EXISTING_6_CONDS + A4_CONDS
INTERACTION_METRICS = [
    "rho_pearson", "rho_spearman", "tau_kendall",
    "bin_var_slope", "q90_q10_slope_diff",
]


def setup_logger() -> logging.Logger:
    (LOGS_DIR / "runtime").mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("S6r-agg")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fh = logging.FileHandler(
        LOGS_DIR / "runtime" / f"{ts}_S6r_aggregation.log", encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    return logger


def integrity_check(seeds: List[int], logger: logging.Logger) -> bool:
    for cond in A4_CONDS:
        cond_dir = DATA_DIR / cond
        actual = sum(1 for _ in cond_dir.glob("*.parquet"))
        expected = 4 * len(seeds)
        logger.info(f"[integrity] {cond}: {actual} / {expected} parquet")
        if actual != expected:
            logger.error(f"[integrity] FAIL: {cond}")
            return False
    return True


def combine_to_800_rows(seeds: List[int], logger: logging.Logger) -> pd.DataFrame:
    p = DATA_DIR / "ensemble_summary.parquet"
    df = pd.read_parquet(p)
    df = df[df["cond"].isin(EXISTING_6_CONDS)].copy()
    T_lob = LOB_PARAMS["main_steps"]
    new = []
    for cond in A4_CONDS:
        logger.info(f"[combine] computing ensemble_summary for {cond}...")
        new.append(aggregate_ensemble_summaries(cond, seeds, DATA_DIR / cond,
                                                T_lob, logger))
    full = pd.concat([df] + new, ignore_index=True)
    full.to_parquet(p, index=False)
    logger.info(f"[combine] saved {len(full)} rows: "
                f"{full.groupby('cond').size().to_dict()}")
    return full


def _load_rt_arrays(cond: str, seeds: List[int]) -> Dict[int, pd.DataFrame]:
    out = {}
    for seed in seeds:
        f = DATA_DIR / cond / f"trial_{seed:04d}.parquet"
        if f.exists():
            out[seed] = pd.read_parquet(f, columns=["horizon", "delta_g"])
    return out


def pooled_with_ci(seeds: List[int], n_boot: int,
                   logger: logging.Logger) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    rows, boot = [], {}
    for cond in ALL_8_CONDS:
        trials = _load_rt_arrays(cond, seeds)
        keys = list(trials.keys())
        pooled = pd.concat(trials.values(), ignore_index=True)
        point = float(bin_variance_slope_pooled(pooled, K=15))
        bs = np.empty(n_boot)
        for b in range(n_boot):
            pick = rng.choice(len(keys), size=len(keys), replace=True)
            bs[b] = bin_variance_slope_pooled(
                pd.concat([trials[keys[i]] for i in pick], ignore_index=True), K=15)
        boot[cond] = bs
        lo, hi = np.nanpercentile(bs, [2.5, 97.5])
        rows.append({"cond": cond, "pooled_bin_var_slope": point,
                     "ci_lo": float(lo), "ci_hi": float(hi),
                     "n_rt": int(len(pooled)), "n_trials": len(keys)})
        logger.info(f"[pooled] {cond}: {point:+.4f} [{lo:+.4f}, {hi:+.4f}] "
                    f"(n_rt={len(pooled):,})")
    df = pd.DataFrame(rows)

    def _ci(arr):
        return {"mean": float(np.nanmean(arr)),
                "lo": float(np.nanpercentile(arr, 2.5)),
                "hi": float(np.nanpercentile(arr, 97.5))}

    base = boot["C0p"] - boot["C0u"]
    s3_pool = (boot["C3"] - boot["C2"]) - base
    a4_pool = (boot["C3_A4"] - boot["C2_A4"]) - base
    extra = {
        "pooled_interaction_S3": _ci(s3_pool),
        "pooled_interaction_A4": _ci(a4_pool),
        "pooled_shrinkage": _ci(s3_pool - a4_pool),
        "nonspecific_C2A4_minus_C2": _ci(boot["C2_A4"] - boot["C2"]),
        "n_boot": n_boot,
    }
    logger.info(f"[pooled] S3 int={extra['pooled_interaction_S3']}")
    logger.info(f"[pooled] A4 int={extra['pooled_interaction_A4']}")
    logger.info(f"[pooled] shrinkage={extra['pooled_shrinkage']} "
                f"(primary KPI: CI 0 排除 + |A4|<|S3| で支持)")
    logger.info(f"[pooled] 非特異的効果 C2_A4−C2={extra['nonspecific_C2A4_minus_C2']}")
    df.attrs["extra"] = extra
    return df


def _seed_paired(df: pd.DataFrame, conds: List[str], metric: str) -> pd.DataFrame:
    out = None
    for cond in conds:
        sub = df[df["cond"] == cond][["seed", metric]].dropna()
        sub = sub.rename(columns={metric: cond})
        out = sub if out is None else out.merge(sub, on="seed", how="inner")
    return out


def trial_level_secondary(df: pd.DataFrame, n_resample: int = 10_000) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    rows = []
    for metric in INTERACTION_METRICS:
        wide = _seed_paired(df, ["C0u", "C0p", "C2", "C3", "C2_A4", "C3_A4"], metric)
        n = 0 if wide is None else len(wide)
        if n == 0:
            continue
        base = (wide["C0p"] - wide["C0u"]).to_numpy()
        s3 = (wide["C3"] - wide["C2"]).to_numpy() - base
        a4 = (wide["C3_A4"] - wide["C2_A4"]).to_numpy() - base
        delta = s3 - a4
        d_m, d_lo, d_hi = bootstrap_ci(delta, n_resample=n_resample, ci=0.95, rng=rng)
        s3_m, a4_m = float(s3.mean()), float(a4.mean())
        ratio = abs(a4_m) / abs(s3_m) if abs(s3_m) > 1e-10 else float("nan")
        rows.append({
            "metric": metric, "s3_mean": s3_m, "a4_mean": a4_m,
            "shrinkage_mean": float(d_m), "shrinkage_lo": float(d_lo),
            "shrinkage_hi": float(d_hi),
            "ci_excludes_zero": bool((d_lo > 0) or (d_hi < 0)),
            "shrinks": bool(abs(a4_m) < abs(s3_m)),
            "ratio_reference_only": ratio, "n": int(n),
        })
    return pd.DataFrame(rows)


def manipulation_checks(df: pd.DataFrame, logger: logging.Logger) -> pd.DataFrame:
    rows = []

    def _mean(cond, col):
        v = df[df["cond"] == cond][col].dropna()
        return float(v.mean()) if len(v) else float("nan")

    for col in ["wealth_persistence_rho"] + [f"corr_winit_wt_T{k}" for k in (1, 5, 10)]:
        rows.append({"check": col,
                     "C2": _mean("C2", col), "C3": _mean("C3", col),
                     "C2_A4": _mean("C2_A4", col), "C3_A4": _mean("C3_A4", col)})
    out = pd.DataFrame(rows)
    for _, r in out.iterrows():
        logger.info(f"[manip] {r['check']}: C3={r['C3']:+.4f} → "
                    f"C3_A4={r['C3_A4']:+.4f} (C2={r['C2']:+.4f})")
    return out


def judgment(extra: Dict) -> Dict[str, object]:
    sh = extra["pooled_shrinkage"]
    s3 = extra["pooled_interaction_S3"]
    a4 = extra["pooled_interaction_A4"]
    ci_excl = (sh["lo"] > 0) or (sh["hi"] < 0)
    shrinks = abs(a4["mean"]) < abs(s3["mean"])
    if ci_excl and shrinks:
        cat = "supported (仮説A revised 支持: persistence 破壊で interaction 縮小)"
    elif not shrinks:
        cat = "fail (A4 interaction が縮小しない → persistence は dominant でない)"
    else:
        cat = "inconclusive (縮小方向だが CI が 0 を跨ぐ)"
    return {"primary_ci_excludes_zero": bool(ci_excl),
            "primary_shrinks": bool(shrinks), "judgment": cat}


def append_readme(pooled_df, extra, jdg, secondary, manip, readme_path: Path) -> None:
    L = ["", "---", "",
         "## Stage S6r — A4 ablation (wealth shuffle、C2_A4/C3_A4) + 仮説 A revised 判定", "",
         "A3 凍結 (性能スパイラル + substitute wealth 非 Pareto、"
         "`plans/design_review_20260610.md` 追記) を受けた差し替え。"
         "K=121、対称 DiD、KPI は pooled bootstrap CI primary "
         "(`plans/stage_S6r_plan.md` §0.4)。", "",
         "### Pooled bin_var_slope (8 条件、seed-cluster bootstrap 95% CI)", "",
         "| cond | slope | 95% CI |", "|---|---:|---|"]
    for _, r in pooled_df.iterrows():
        L.append(f"| {r['cond']} | {r['pooled_bin_var_slope']:+.4f} | "
                 f"[{r['ci_lo']:+.4f}, {r['ci_hi']:+.4f}] |")
    s3, a4, sh = (extra["pooled_interaction_S3"], extra["pooled_interaction_A4"],
                  extra["pooled_shrinkage"])
    L += ["",
          f"**Pooled interaction**: S3 = {s3['mean']:+.4f} [{s3['lo']:+.4f}, {s3['hi']:+.4f}], "
          f"A4 = {a4['mean']:+.4f} [{a4['lo']:+.4f}, {a4['hi']:+.4f}], "
          f"shrinkage = {sh['mean']:+.4f} [{sh['lo']:+.4f}, {sh['hi']:+.4f}]",
          "",
          f"**Primary KPI 判定: {jdg['judgment']}**",
          "",
          "### Secondary (trial-level seed-paired shrinkage)", "",
          "| metric | S3 | A4 | shrinkage [CI] | CI 0 排除 | 縮小 |",
          "|---|---:|---:|---|---|---|"]
    for _, r in secondary.iterrows():
        L.append(f"| {r['metric']} | {r['s3_mean']:+.4f} | {r['a4_mean']:+.4f} | "
                 f"{r['shrinkage_mean']:+.4f} [{r['shrinkage_lo']:+.4f}, "
                 f"{r['shrinkage_hi']:+.4f}] | "
                 f"{'✓' if r['ci_excludes_zero'] else '✗'} | "
                 f"{'✓' if r['shrinks'] else '✗'} |")
    ns = extra["nonspecific_C2A4_minus_C2"]
    L += ["",
          f"**非特異的効果 (C2_A4 − C2)**: {ns['mean']:+.4f} "
          f"[{ns['lo']:+.4f}, {ns['hi']:+.4f}]",
          "", "### Manipulation check (成功条件ではない)", "",
          "| check | C2 | C3 | C2_A4 | C3_A4 |", "|---|---:|---:|---:|---:|"]
    for _, r in manip.iterrows():
        L.append(f"| {r['check']} | {r['C2']:+.4f} | {r['C3']:+.4f} | "
                 f"{r['C2_A4']:+.4f} | {r['C3_A4']:+.4f} |")
    L += ["", "注意: A4 条件の rt parquet の `w_open`/`w_close` 列は shuffle を"
          "考慮しない再構成のため無効 (plan §0.2)。Layer 2 timescale concern "
          "(T=1500) は継続。", ""]
    with open(readme_path, "a", encoding="utf-8") as f:
        f.write("\n".join(L))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-base", type=int, default=ENSEMBLE_SEED_BASE)
    parser.add_argument("--n-trials", type=int, default=ENSEMBLE_N_TRIALS)
    parser.add_argument("--n-boot-pooled", type=int, default=500)
    parser.add_argument("--skip-readme", action="store_true")
    args = parser.parse_args()

    logger = setup_logger()
    seeds = list(range(args.seed_base, args.seed_base + args.n_trials))
    (OUTPUTS_DIR / "tables").mkdir(parents=True, exist_ok=True)
    (OUTPUTS_DIR / "figures").mkdir(parents=True, exist_ok=True)

    logger.info("=" * 70)
    logger.info(f"S6r aggregation — A4 対称 DiD | platform={platform.system()}")
    logger.info("=" * 70)

    if not integrity_check(seeds, logger):
        return
    df = combine_to_800_rows(seeds, logger)

    pooled_df = pooled_with_ci(seeds, args.n_boot_pooled, logger)
    extra = pooled_df.attrs["extra"]
    jdg = judgment(extra)
    logger.info(f"[judgment] {jdg}")
    pooled_df.to_csv(OUTPUTS_DIR / "tables" / "tab_S6r_pooled_bin_var_8cond.csv",
                     index=False)

    secondary = trial_level_secondary(df)
    secondary.to_csv(OUTPUTS_DIR / "tables" / "tab_S6r_interaction.csv", index=False)
    for _, r in secondary.iterrows():
        logger.info(f"[secondary] {r['metric']}: S3={r['s3_mean']:+.4f} → "
                    f"A4={r['a4_mean']:+.4f}, shrink={r['shrinkage_mean']:+.4f} "
                    f"[{r['shrinkage_lo']:+.4f}, {r['shrinkage_hi']:+.4f}] "
                    f"excl0={r['ci_excludes_zero']} shrinks={r['shrinks']}")

    manip = manipulation_checks(df, logger)
    manip.to_csv(OUTPUTS_DIR / "tables" / "tab_S6r_manipulation.csv", index=False)

    # figure: 8-cond bar
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(ALL_8_CONDS))
    vals = pooled_df["pooled_bin_var_slope"].to_numpy()
    err = [vals - pooled_df["ci_lo"].to_numpy(),
           pooled_df["ci_hi"].to_numpy() - vals]
    colors = ["#777777", "#777777", "#1f77b4", "#1f77b4",
              "#2ca02c", "#2ca02c", "#d62728", "#d62728"]
    ax.bar(x, vals, yerr=err, capsize=4, color=colors, alpha=0.85)
    ax.axhline(0, color="black", linewidth=0.4)
    ax.set_xticks(x)
    ax.set_xticklabels(ALL_8_CONDS, rotation=15)
    ax.set_ylabel("pooled bin_var_slope (bootstrap 95% CI)")
    ax.set_title(f"S6r — A4 wealth shuffle (K=121)\n{jdg['judgment']}")
    fig.tight_layout()
    fig.savefig(OUTPUTS_DIR / "figures" / "fig_S6r_pooled_bin_var_8cond.png",
                dpi=120, bbox_inches="tight")
    plt.close(fig)

    if not args.skip_readme:
        append_readme(pooled_df, extra, jdg, secondary, manip,
                      YH006_1 / "README.md")
        logger.info("[output] appended README §S6r")

    summary = {
        "stage": "S6r",
        "shuffle_period": 121,
        "platform": f"{platform.system()} {platform.machine()}",
        "pooled_bin_var_8cond": pooled_df.to_dict(orient="records"),
        "pooled_extra": extra,
        "judgment": jdg,
        "secondary_trial_level": secondary.to_dict(orient="records"),
        "manipulation": manip.to_dict(orient="records"),
        "timestamp": datetime.now().isoformat(),
    }
    with open(LOGS_DIR / "S6r_summary_for_diff.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
    logger.info("[output] saved: S6r_summary_for_diff.json")
    logger.info("=" * 70)
    logger.info(f"S6r aggregation complete | {jdg['judgment']}")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
