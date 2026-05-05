import pandas as pd
import numpy as np
from trading_ai.data_layer.indicators import add_indicators, add_super_signals

# ML modeline gidecek feature sütunları
FEATURE_COLS = [
    # Fiyat ilişkileri
    "close_ret_1", "close_ret_3", "close_ret_5",
    "high_low_ratio", "close_open_ratio",

    # Volatilite
    "atr_pct", "bb_width", "volume_ratio",

    # Momentum
    "rsi", "macd_hist", "wpr", "stoch_k", "stoch_d",

    # Trend
    "ema_ratio",        # ema_fast / ema_slow
    "price_ema_ratio",  # close / ema_fast
    "ema_slope_norm",   # ema_slope / atr
    "adx", "di_pos", "di_neg",

    # SuperSignals (boolean → int)
    "ss_sell_strong", "ss_buy_strong",
    "ss_sell_minor",  "ss_buy_minor",
]


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    df = add_indicators(df)
    df = add_super_signals(df)

    df["close_ret_1"] = df["close"].pct_change(1)
    df["close_ret_3"] = df["close"].pct_change(3)
    df["close_ret_5"] = df["close"].pct_change(5)

    df["high_low_ratio"]  = (df["high"] - df["low"]) / df["close"]
    df["close_open_ratio"] = (df["close"] - df["open"]) / df["open"]

    df["atr_pct"]        = df["atr"] / df["close"]
    df["ema_ratio"]      = df["ema_fast"] / df["ema_slow"]
    df["price_ema_ratio"] = df["close"] / df["ema_fast"]
    df["ema_slope_norm"] = df["ema_slope"] / df["atr"].replace(0, np.nan)

    # Boolean → int
    for col in ["ss_sell_strong", "ss_buy_strong", "ss_sell_minor", "ss_buy_minor"]:
        df[col] = df[col].astype(int)

    return df


def build_target(df: pd.DataFrame, forward_bars: int = 3, threshold_pct: float = 0.005) -> pd.Series:
    """
    3 bar sonraki getiri → sınıf etiketi
      1  = BUY  (fiyat > +0.5% artar)
     -1  = SELL (fiyat > -0.5% düşer)
      0  = NEUTRAL
    """
    fwd_return = df["close"].shift(-forward_bars) / df["close"] - 1
    target = pd.Series(0, index=df.index)
    target[fwd_return >  threshold_pct] = 1
    target[fwd_return < -threshold_pct] = -1
    return target


def get_feature_matrix(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    df_feat = build_features(df)
    available = [c for c in FEATURE_COLS if c in df_feat.columns]
    X = df_feat[available].copy()
    X.replace([np.inf, -np.inf], np.nan, inplace=True)
    X.dropna(inplace=True)
    return X, available
