import json
import numpy as np
import pandas as pd
from pathlib import Path
from xgboost import XGBClassifier

from trading_ai.core.config import get_settings
from trading_ai.core.models import MLPrediction, SignalType, MarketState
from trading_ai.data_layer.feature_engineer import build_features, FEATURE_COLS

settings = get_settings()

_model: XGBClassifier | None = None
_meta: dict | None = None


def _load_model():
    global _model, _meta
    path = settings.model_path
    meta_path = path.replace(".json", "_meta.json")

    if not Path(path).exists():
        raise FileNotFoundError(
            f"Model bulunamadı: {path}\n"
            "Önce 'python -m trading_ai.ml_layer.train' komutunu çalıştır."
        )

    _model = XGBClassifier()
    _model.load_model(path)

    with open(meta_path) as f:
        _meta = json.load(f)


def get_model() -> tuple[XGBClassifier, dict]:
    if _model is None:
        _load_model()
    return _model, _meta


def predict(df: pd.DataFrame) -> MLPrediction:
    """Son barın feature vektörünü kullanarak sinyal tahmin eder."""
    model, meta = get_model()
    feature_cols = meta["feature_cols"]
    label_classes = meta["label_classes"]   # [-1, 0, 1]

    df_feat = build_features(df)
    available = [c for c in feature_cols if c in df_feat.columns]
    X = df_feat[available].replace([np.inf, -np.inf], np.nan)

    # Son geçerli satırı al
    last_row = X.dropna().iloc[[-1]]
    if last_row.empty:
        return MLPrediction(
            signal=SignalType.NEUTRAL,
            confidence=0.0,
            buy_prob=0.333,
            sell_prob=0.333,
            neutral_prob=0.334,
        )

    proba = model.predict_proba(last_row)[0]

    # label_classes sırası: [-1, 0, 1] → [SELL, NEUTRAL, BUY]
    class_map = {str(c): i for i, c in enumerate(label_classes)}
    sell_prob    = float(proba[class_map.get("-1", 0)])
    neutral_prob = float(proba[class_map.get("0",  1)])
    buy_prob     = float(proba[class_map.get("1",  2)])

    # Sinyal kararı
    if buy_prob >= settings.buy_threshold and buy_prob > sell_prob:
        signal     = SignalType.BUY
        confidence = buy_prob
    elif sell_prob >= settings.sell_threshold and sell_prob > buy_prob:
        signal     = SignalType.SELL
        confidence = sell_prob
    else:
        signal     = SignalType.NEUTRAL
        confidence = neutral_prob

    # Feature importance (sadece son tahmin için)
    importance = dict(zip(available, model.feature_importances_))

    return MLPrediction(
        signal=signal,
        confidence=confidence,
        buy_prob=buy_prob,
        sell_prob=sell_prob,
        neutral_prob=neutral_prob,
        feature_importance=importance,
    )


def extract_market_state(df: pd.DataFrame, symbol: str, timeframe: str) -> MarketState:
    """Son barın piyasa durumunu çıkarır."""
    df_feat = build_features(df)
    last = df_feat.dropna(subset=["rsi", "atr"]).iloc[-1]

    return MarketState(
        symbol=symbol,
        timeframe=timeframe,
        timestamp=last.name.to_pydatetime(),
        open=float(last["open"]),
        high=float(last["high"]),
        low=float(last["low"]),
        close=float(last["close"]),
        volume=float(last["volume"]),
        atr=float(last["atr"]),
        rsi=float(last["rsi"]),
        adx=float(last.get("adx", 0)),
        ema_fast=float(last["ema_fast"]),
        ema_slow=float(last["ema_slow"]),
        ema_slope=float(last["ema_slope"]),
        wpr=float(last.get("wpr", 0)),
        super_sell_strong=bool(last.get("ss_sell_strong", False)),
        super_buy_strong=bool(last.get("ss_buy_strong", False)),
        super_sell_minor=bool(last.get("ss_sell_minor", False)),
        super_buy_minor=bool(last.get("ss_buy_minor", False)),
    )
