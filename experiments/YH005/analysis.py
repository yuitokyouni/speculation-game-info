"""YH005: Stylized facts 計算関数.

Cont (2001) "Empirical properties of asset returns" のうち以下 5 項目を計算:
  1. log_returns_from_prices  — 価格 → log-return (p<=0 は NaN でマスク)
  2. return_acf               — Corr(r(t+τ), r(t))
  3. volatility_acf           — Corr(|r(t+τ)|, |r(t)|)
  4. ccdf + Hill MLE          — 補完累積分布 + tail index
  5. kurtosis_windowed        — aggregational Gaussianity 用の window-sum kurtosis
"""

from __future__ import annotations

import numpy as np


def log_returns_from_prices(prices: np.ndarray) -> np.ndarray:
    """Log-return。p<=0 の index は NaN。長さ len(prices)-1。"""
    p = np.asarray(prices, dtype=np.float64)
    safe = np.where(p > 0, p, np.nan)
    logp = np.log(safe)
    return np.diff(logp)


def _acf(series: np.ndarray, max_lag: int) -> np.ndarray:
    """NaN を除外した上での自己相関 ACF[1..max_lag]。"""
    x = np.asarray(series, dtype=np.float64)
    mask = ~np.isnan(x)
    if mask.sum() < 2:
        return np.full(max_lag, np.nan)
    xc = x[mask]
    xc = xc - xc.mean()
    var = (xc ** 2).mean()
    if var == 0:
        return np.zeros(max_lag)
    out = np.empty(max_lag, dtype=np.float64)
    # NaN を含む場合は lag ごとに pair-wise で再計算する必要があるが、
    # p>0 が圧倒的多数なら簡便化のため全体 demean → pair product → mean でよい。
    # ただし NaN があるとペアのうち 1 つでも NaN なら積も NaN、np.nanmean で scraping。
    x_demeaned = np.where(mask, x - x[mask].mean(), np.nan)
    for lag in range(1, max_lag + 1):
        prod = x_demeaned[:-lag] * x_demeaned[lag:]
        m = np.nanmean(prod)
        out[lag - 1] = m / var
    return out


def return_acf(returns: np.ndarray, max_lag: int = 50) -> np.ndarray:
    """r(t) 自己相関 ACF[1..max_lag]。"""
    return _acf(returns, max_lag)


def volatility_acf(returns: np.ndarray, max_lag: int = 500) -> np.ndarray:
    """|r(t)| 自己相関 ACF[1..max_lag]。"""
    return _acf(np.abs(returns), max_lag)


def ccdf(values: np.ndarray, normalize: bool = True) -> tuple[np.ndarray, np.ndarray]:
    """補完累積分布 P(|X| >= x) を (x_sorted, ccdf_values) で返す。

    normalize=True のとき |r| を (|r| - mean) / std ではなく、絶対値を std で割った
    正規化（mean-0, std-1 ではなく scale-only）を使う。テール比較が目的なので。
    """
    x = np.asarray(values, dtype=np.float64)
    x = x[~np.isnan(x)]
    ax = np.abs(x)
    if normalize:
        s = ax.std()
        if s > 0:
            ax = ax / s
    ax = np.sort(ax)
    n = len(ax)
    ccdf_vals = 1.0 - np.arange(n) / n
    return ax, ccdf_vals


def hill_mle_tail_index(values: np.ndarray, k: int | None = None) -> float:
    """Hill MLE tail index α。上位 k 個を使う。None なら sqrt(len) を既定とする。"""
    x = np.asarray(values, dtype=np.float64)
    x = x[~np.isnan(x)]
    ax = np.abs(x)
    ax = ax[ax > 0]
    if ax.size < 4:
        return float("nan")
    sorted_desc = np.sort(ax)[::-1]
    if k is None:
        k = int(np.sqrt(sorted_desc.size))
    k = min(max(k, 2), sorted_desc.size - 1)
    log_ratios = np.log(sorted_desc[:k]) - np.log(sorted_desc[k])
    mean_log_ratio = log_ratios.mean()
    if mean_log_ratio <= 0:
        return float("nan")
    return float(1.0 / mean_log_ratio)


def kurtosis_windowed(returns: np.ndarray, window: int) -> float:
    """window 幅で集計した return の excess kurtosis。window=1 が生リターン。"""
    r = np.asarray(returns, dtype=np.float64)
    r = r[~np.isnan(r)]
    if window > 1:
        n = (len(r) // window) * window
        r = r[:n].reshape(-1, window).sum(axis=1)
    if r.size < 4:
        return float("nan")
    m = r.mean()
    s = r.std()
    if s == 0:
        return float("nan")
    z = (r - m) / s
    return float((z ** 4).mean() - 3.0)


def stylized_facts_summary(
    returns: np.ndarray,
    acf_lags: tuple[int, ...] = (1, 14, 50, 200),
    kurt_windows: tuple[int, ...] = (1, 16, 64, 256, 640),
) -> dict:
    """stylized facts の単一サマリ dict。"""
    max_ret_lag = max(acf_lags) + 1
    ret_acf_series = return_acf(returns, max_lag=max_ret_lag)
    vol_acf_series = volatility_acf(returns, max_lag=max_ret_lag)
    return {
        "n_valid": int((~np.isnan(returns)).sum()),
        "std": float(np.nanstd(returns)),
        "ret_acf": {lag: float(ret_acf_series[lag - 1]) for lag in acf_lags},
        "vol_acf": {lag: float(vol_acf_series[lag - 1]) for lag in acf_lags},
        "kurt": {w: kurtosis_windowed(returns, w) for w in kurt_windows},
        "hill_alpha": hill_mle_tail_index(returns),
    }
