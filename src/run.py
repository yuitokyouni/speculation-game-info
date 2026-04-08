"""
run.py  –  Entry point. Runs simulation and plots results.

Usage:
    python -m src.run                             # default (switching)
    python -m src.run --no-switching --nc 0.9      # fixed nc
    python -m src.run --N 301 --T 10000 --beta 1.0
"""
import argparse
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import japanize_matplotlib

from .utils.config    import SimConfig
from .simulation      import Simulation
from .analysis.validation import rolling_accuracy_vs_nc


def main():
    parser = argparse.ArgumentParser(description="J-REIT ABM Simulation")
    parser.add_argument("--N",    type=int,   default=301)
    parser.add_argument("--T",    type=int,   default=10_000)
    parser.add_argument("--M",    type=int,   default=3)
    parser.add_argument("--beta", type=float, default=1.0)
    parser.add_argument("--nc",   type=float, default=0.5,
                        help="Initial Chartist fraction")
    parser.add_argument("--f-sens", type=float, default=1.0,
                        help="Fundamentalist sensitivity κ")
    parser.add_argument("--no-switching", action="store_true", default=False)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out",  type=str, default="results/run_output.png")
    args = parser.parse_args()

    cfg = SimConfig(
        N=args.N, T=args.T, M=args.M,
        beta=args.beta, n_c_init=args.nc,
        f_sensitivity=args.f_sens,
        switching=not args.no_switching,
        seed=args.seed,
    )

    print(f"Running: N={cfg.N}, T={cfg.T}, M={cfg.M}, "
          f"β={cfg.beta}, nc_init={cfg.n_c_init}, κ={cfg.f_sensitivity}, "
          f"switching={cfg.switching}, seed={cfg.seed}")

    sim = Simulation(cfg)
    res = sim.run()

    dev = (res.price - res.nav) / res.nav * 100
    print(f"Price range: [{res.price.min():.1f}, {res.price.max():.1f}]")
    print(f"nc range:    [{res.nc.min():.3f}, {res.nc.max():.3f}]")
    print(f"NAV dev:     mean={dev.mean():.2f}%, std={dev.std():.2f}%")

    # ── Validation pipeline ────────────────────────────────────────────
    corr = float('nan')
    print("\nRunning LightGBM validation...")
    val_df = rolling_accuracy_vs_nc(
        res.price, res.nc,
        window=cfg.val_window,
        step=cfg.val_step,
        horizon=cfg.predict_horizon,
    )
    if not val_df.empty:
        corr = val_df["mean_nc"].corr(val_df["accuracy"])
        print(f"Corr(nc, accuracy): {corr:.4f}")
        print(f"Mean accuracy: {val_df['accuracy'].mean():.4f}")

    # ── Plot ──────────────────────────────────────────────────────────
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)

    BG = "#12121e"; AX = "#090915"
    fig, axes = plt.subplots(4, 1, figsize=(14, 14), facecolor=BG)
    fig.patch.set_facecolor(BG)

    t = np.arange(cfg.T)

    # 1. Price vs NAV
    ax = axes[0]; ax.set_facecolor(AX)
    ax.plot(t, res.price, color="#42a5f5", lw=0.8, label="市場価格 p(t)")
    ax.plot(t, res.nav,   color="#ef9a9a", lw=1.2, linestyle="--", label="NAV")
    ax.set_ylabel("価格", color="white")
    ax.legend(facecolor=BG, labelcolor="white")
    ax.tick_params(colors="white")
    for sp in ax.spines.values(): sp.set_edgecolor("#333")

    # 2. NAV deviation
    ax = axes[1]; ax.set_facecolor(AX)
    ax.plot(t, dev, color="#ce93d8", lw=0.8)
    ax.axhline(0, color="white", lw=0.5, linestyle=":")
    ax.set_ylabel("乖離率 (%)", color="white")
    ax.tick_params(colors="white")
    for sp in ax.spines.values(): sp.set_edgecolor("#333")

    # 3. Chartist fraction nc
    ax = axes[2]; ax.set_facecolor(AX)
    ax.plot(t, res.nc, color="#66bb6a", lw=0.8, label="Chartist比率 nc(t)")
    ax.set_ylim(0, 1); ax.set_ylabel("nc", color="white")
    ax.legend(facecolor=BG, labelcolor="white")
    ax.tick_params(colors="white")
    for sp in ax.spines.values(): sp.set_edgecolor("#333")

    # 4. nc vs LightGBM accuracy scatter
    ax = axes[3]; ax.set_facecolor(AX)
    if not val_df.empty:
        sc = ax.scatter(val_df["mean_nc"], val_df["accuracy"],
                        c=val_df["t"], cmap="plasma", alpha=0.7, s=20)
        ax.axhline(0.5, color="white", lw=0.8, linestyle="--", alpha=0.5)
        ax.set_xlabel("平均 nc（Chartist比率）", color="white")
        ax.set_ylabel("LightGBM 正解率", color="white")
        if len(val_df) > 2 and not np.isnan(corr):
            ax.set_title(f"nc × 予測精度  (r = {corr:.3f})",
                         color="white", fontsize=10)
    ax.tick_params(colors="white")
    for sp in ax.spines.values(): sp.set_edgecolor("#333")

    fig.suptitle(
        f"J-REIT ABM (clean)  N={cfg.N} T={cfg.T} β={cfg.beta} "
        f"κ={cfg.f_sensitivity} nc₀={cfg.n_c_init}",
        color="white", fontsize=11)
    plt.tight_layout()
    plt.savefig(args.out, dpi=130, bbox_inches="tight", facecolor=BG)
    plt.close()
    print(f"\nPlot saved -> {args.out}")


if __name__ == "__main__":
    main()
