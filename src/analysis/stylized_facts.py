"""Stylized facts verification.

Reproduces Katahira et al. (2019) Table 2 checks.
Run after Phase 1 (pure Chartist) to confirm baseline is working.
"""
from __future__ import annotations
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats

from ..simulation import SimResult


def check_all(result: SimResult, out_dir: str = "results/figures") -> dict:
    """Run all stylized fact checks and return a report dict."""
    r = result.log_return[1:]   # skip t=0
    report = {}

    report['volatility_clustering'] = _check_vol_clustering(r)
    report['heavy_tails']           = _check_heavy_tails(r)
    report['no_autocorr_returns']   = _check_no_autocorr(r)
    report['slow_decay_vol_autocorr'] = _check_slow_vol_autocorr(r)

    _plot_overview(result, out_dir)
    _print_report(report)
    return report


def _check_vol_clustering(r: np.ndarray) -> bool:
    """Autocorrelation of |r| should be positive up to lag ~100."""
    abs_r = np.abs(r)
    acf_50 = float(np.corrcoef(abs_r[50:], abs_r[:-50])[0, 1])
    return acf_50 > 0.05


def _check_heavy_tails(r: np.ndarray, alpha_lo=2.0, alpha_hi=5.0) -> bool:
    """Tail index should be in (2, 5) — inverse cubic law."""
    pos_tail = r[r > 0]
    if len(pos_tail) < 100:
        return False
    # Simple Hill estimator on top 10% of returns
    threshold = np.quantile(pos_tail, 0.90)
    exceedances = pos_tail[pos_tail > threshold]
    if len(exceedances) < 10:
        return False
    alpha_hat = len(exceedances) / np.sum(np.log(exceedances / threshold))
    return alpha_lo < alpha_hat < alpha_hi


def _check_no_autocorr(r: np.ndarray, max_lag: int = 20,
                        threshold: float = 0.05) -> bool:
    """Returns should have no significant autocorrelation up to lag 20."""
    sig_count = sum(
        abs(float(np.corrcoef(r[lag:], r[:-lag])[0, 1])) > threshold
        for lag in range(1, max_lag + 1)
    )
    return sig_count <= 3   # Allow up to 3 marginally significant lags


def _check_slow_vol_autocorr(r: np.ndarray, lag: int = 100,
                              threshold: float = 0.01) -> bool:
    """Autocorrelation of |r| at lag 100 should still be positive."""
    abs_r = np.abs(r)
    if len(abs_r) <= lag:
        return False
    acf = float(np.corrcoef(abs_r[lag:], abs_r[:-lag])[0, 1])
    return acf > threshold


def _plot_overview(result: SimResult, out_dir: str) -> None:
    """Four-panel overview plot."""
    import os
    os.makedirs(out_dir, exist_ok=True)

    r   = result.log_return[1:]
    p   = result.price
    nav = result.nav
    nc  = result.nc
    T   = len(r)
    t   = np.arange(T)

    fig, axes = plt.subplots(4, 1, figsize=(14, 12))
    fig.patch.set_facecolor('#0f0f1a')

    def ax_style(ax, ylabel):
        ax.set_facecolor('#07070f')
        ax.tick_params(colors='white', labelsize=8)
        ax.set_ylabel(ylabel, color='white', fontsize=9)
        for sp in ax.spines.values():
            sp.set_edgecolor('#333')

    # Panel 1: price vs NAV
    axes[0].plot(p, color='#42a5f5', lw=0.8, label='price p(t)')
    axes[0].plot(nav, color='#ff7043', lw=1.2, linestyle='--', label='NAV')
    axes[0].legend(fontsize=8, facecolor='#0f0f1a', labelcolor='white')
    ax_style(axes[0], 'Price / NAV')

    # Panel 2: log returns
    axes[1].plot(r, color='#66bb6a', lw=0.5, alpha=0.9)
    ax_style(axes[1], 'Log return r(t)')

    # Panel 3: Chartist fraction nc
    axes[2].fill_between(np.arange(len(nc)), nc,
                         alpha=0.7, color='#ce93d8')
    axes[2].axhline(0.5, color='white', lw=0.5, linestyle=':')
    ax_style(axes[2], 'Chartist fraction nc')

    # Panel 4: P/NAV ratio
    pnav = p / nav
    axes[3].plot(pnav, color='#ffa726', lw=0.8)
    axes[3].axhline(1.0, color='white', lw=0.8, linestyle='--')
    ax_style(axes[3], 'P/NAV ratio')
    axes[3].set_xlabel('Time step', color='white', fontsize=9)

    fig.suptitle('J-REIT Speculation Game — Simulation Overview',
                 color='white', fontsize=12)
    plt.tight_layout()
    plt.savefig(f'{out_dir}/simulation_overview.png',
                dpi=150, facecolor=fig.get_facecolor())
    plt.close()
    print(f"Plot saved → {out_dir}/simulation_overview.png")


def _print_report(report: dict) -> None:
    print("\n── Stylized Facts Check ──────────────────────")
    for k, v in report.items():
        status = "✓ PASS" if v else "✗ FAIL"
        print(f"  {status}  {k}")
    print("──────────────────────────────────────────────\n")
