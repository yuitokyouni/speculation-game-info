"""
validation.py  –  Reproduce Konishi (2025) analysis on ABM-generated prices.

Steps:
  1. Compute TSF, ATR, DMI_ADX from price series
  2. Build LightGBM classifier (10-day direction prediction)
  3. Roll window through series, record accuracy vs mean nc
  4. Return DataFrame for plotting
"""
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings("ignore")

try:
    import pandas_ta as ta
    _USE_TA = True
except ImportError:
    _USE_TA = False

from lightgbm import LGBMClassifier


# ── Feature Engineering ────────────────────────────────────────────────────

def make_features(prices: np.ndarray, window: int = 14) -> pd.DataFrame:
    """
    Compute Konishi (2025) top-contributor technical indicators.
    Requires at least ~200 rows for MA_200.
    """
    close = pd.Series(prices, name="close")

    # Synthetic OHLC from close only (approximation for ABM data)
    high  = close * 1.002
    low   = close * 0.998
    open_ = close.shift(1).fillna(close)

    df = pd.DataFrame({"open": open_, "high": high, "low": low, "close": close})

    if _USE_TA:
        # TSF – Time Series Forecast: linear regression endpoint (pandas_ta: linreg)
        df["TSF"] = ta.linreg(close, length=14)

        # ATR – Average True Range
        df["ATR"] = ta.atr(high, low, close, length=14)

        # ADX – Average Directional Index (DMI component)
        adx_df = ta.adx(high, low, close, length=14)
        if adx_df is not None:
            df["DMI_ADX"] = adx_df.get("ADX_14", np.nan)
            df["DM_minus"] = adx_df.get("DMN_14", np.nan)
        else:
            df["DMI_ADX"] = np.nan
            df["DM_minus"] = np.nan

        # MACD
        macd_df = ta.macd(close)
        if macd_df is not None:
            cols = macd_df.columns.tolist()
            df["MACD_hist"]   = macd_df[cols[1]] if len(cols) > 1 else np.nan
            df["MACD_signal"] = macd_df[cols[2]] if len(cols) > 2 else np.nan

        # Moving averages
        df["MA_75"]   = ta.sma(close, length=75)
        df["MA_200"]  = ta.sma(close, length=200)
        df["EMA_200"] = ta.ema(close, length=200)
    else:
        # Minimal fallback without pandas_ta
        df["TSF"]     = close.rolling(14).apply(
            lambda x: np.polyval(np.polyfit(range(len(x)), x, 1), len(x) - 1), raw=True)
        df["ATR"]     = (high - low).rolling(14).mean()
        df["DMI_ADX"] = (close.diff().abs()).rolling(14).mean()
        df["MA_75"]   = close.rolling(75).mean()
        df["MA_200"]  = close.rolling(200).mean()
        df["EMA_200"] = close.ewm(span=200).mean()
        df["MACD_hist"]   = close.ewm(12).mean() - close.ewm(26).mean()
        df["MACD_signal"] = df["MACD_hist"].ewm(9).mean()

    feature_cols = ["TSF", "ATR", "DMI_ADX", "MA_75", "MA_200",
                    "EMA_200", "MACD_hist", "MACD_signal"]
    return df[feature_cols].bfill().fillna(0)


# ── Rolling Accuracy vs nc ─────────────────────────────────────────────────

def rolling_accuracy_vs_nc(
    prices: np.ndarray,
    nc_series: np.ndarray,
    window: int = 500,
    step: int   = 100,
    horizon: int = 10,
    gap: int = 50,
) -> pd.DataFrame:
    """
    Slide a window over the ABM price series with proper time-series split.

    For each window position:
      - Train on first 60%, skip a gap, test on last 20%
      - Gap prevents label leakage from horizon overlap
      - Record LightGBM accuracy vs mean nc

    Returns DataFrame with columns: [t, mean_nc, accuracy]
    """
    T = len(prices)
    if T < window + horizon:
        return pd.DataFrame()

    features_all = make_features(prices)

    records = []
    for t_end in range(window, T - horizon, step):
        t_start = t_end - window

        feat_win  = features_all.iloc[t_start:t_end].values
        price_win = prices[t_start:t_end]

        # Labels: 1 if price goes up in next `horizon` steps, else 0
        future_prices = prices[t_start + horizon: t_end + horizon]
        if len(future_prices) != len(price_win):
            continue
        labels = (future_prices > price_win).astype(int)

        n = len(feat_win)
        train_end = int(n * 0.6)
        test_start = train_end + gap  # gap to prevent leakage

        if test_start >= n:
            continue

        X_tr, y_tr = feat_win[:train_end], labels[:train_end]
        X_te, y_te = feat_win[test_start:], labels[test_start:]

        if len(X_te) < 10 or len(np.unique(y_tr)) < 2 or len(np.unique(y_te)) < 2:
            continue

        clf = LGBMClassifier(
            n_estimators=100, max_depth=4, num_leaves=15,
            min_child_samples=20, subsample=0.8,
            verbosity=-1, random_state=42,
        )
        clf.fit(X_tr, y_tr)
        acc = (clf.predict(X_te) == y_te).mean()

        records.append({
            "t": t_end,
            "mean_nc": float(nc_series[t_start:t_end].mean()),
            "accuracy": float(acc),
        })

    return pd.DataFrame(records)
