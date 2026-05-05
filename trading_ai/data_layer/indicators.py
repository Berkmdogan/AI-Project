import pandas as pd
import pandas_ta as ta
import numpy as np


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """OHLCV DataFrame'ine tüm teknik göstergeleri ekler."""
    df = df.copy()

    # === Trend ===
    df["ema_fast"] = ta.ema(df["close"], length=50)
    df["ema_slow"] = ta.ema(df["close"], length=200)
    df["ema_slope"] = df["ema_fast"].diff(3)           # 3 barlık EMA eğimi

    # === Momentum ===
    df["rsi"] = ta.rsi(df["close"], length=14)
    macd_df   = ta.macd(df["close"], fast=12, slow=26, signal=9)
    df["macd"]        = macd_df["MACD_12_26_9"]
    df["macd_signal"] = macd_df["MACDs_12_26_9"]
    df["macd_hist"]   = macd_df["MACDh_12_26_9"]

    # === Volatilite ===
    df["atr"]    = ta.atr(df["high"], df["low"], df["close"], length=50)
    df["atr_14"] = ta.atr(df["high"], df["low"], df["close"], length=14)
    bb           = ta.bbands(df["close"], length=20, std=2)
    df["bb_upper"]  = bb["BBU_20_2.0"]
    df["bb_lower"]  = bb["BBL_20_2.0"]
    df["bb_width"]  = (df["bb_upper"] - df["bb_lower"]) / df["close"]

    # === Trend Gücü ===
    adx_df      = ta.adx(df["high"], df["low"], df["close"], length=14)
    df["adx"]   = adx_df["ADX_14"]
    df["di_pos"] = adx_df["DMP_14"]
    df["di_neg"] = adx_df["DMN_14"]

    # === Hacim ===
    df["volume_ma"]    = ta.sma(df["volume"], length=20)
    df["volume_ratio"] = df["volume"] / df["volume_ma"]

    # === WPR (Williams Percent Range) ===
    df["wpr"] = ta.willr(df["high"], df["low"], df["close"], length=14)

    # === Stochastic ===
    stoch_df      = ta.stoch(df["high"], df["low"], df["close"])
    df["stoch_k"] = stoch_df["STOCHk_14_3_3"]
    df["stoch_d"] = stoch_df["STOCHd_14_3_3"]

    return df


def add_super_signals(df: pd.DataFrame, dist1: int = 14, dist2: int = 21) -> pd.DataFrame:
    """SuperSignals v2.2 pivot mantığını Python'da uygular."""
    df = df.copy()
    df["ss_sell_strong"] = False
    df["ss_buy_strong"]  = False
    df["ss_sell_minor"]  = False
    df["ss_buy_minor"]   = False

    atr = df["atr"].values
    high = df["high"].values
    low  = df["low"].values
    close = df["close"].values
    ema_fast = df["ema_fast"].values
    ema_slow = df["ema_slow"].values

    n = len(df)

    for i in range(dist2 + dist2, n):
        if pd.isna(atr[i]) or pd.isna(ema_fast[i]):
            continue

        s2 = max(0, i - dist2 // 2)
        s1 = max(0, i - dist1 // 2)

        end2 = min(n, s2 + dist2)
        end1 = min(n, s1 + dist1)

        hhb  = s2 + int(np.argmax(high[s2:end2]))
        llb  = s2 + int(np.argmin(low[s2:end2]))
        hhb1 = s1 + int(np.argmax(high[s1:end1]))
        llb1 = s1 + int(np.argmin(low[s1:end1]))

        # EMA slope filtresi
        ema_rising  = (not pd.isna(ema_fast[i-3])) and (ema_fast[i] > ema_fast[i-3])
        ema_falling = (not pd.isna(ema_fast[i-3])) and (ema_fast[i] < ema_fast[i-3])

        if i == hhb and ema_rising:
            df.iloc[i, df.columns.get_loc("ss_sell_strong")] = True
        if i == llb and ema_falling:
            df.iloc[i, df.columns.get_loc("ss_buy_strong")] = True
        if i == hhb1 and ema_rising:
            df.iloc[i, df.columns.get_loc("ss_sell_minor")] = True
        if i == llb1 and ema_falling:
            df.iloc[i, df.columns.get_loc("ss_buy_minor")] = True

    return df
