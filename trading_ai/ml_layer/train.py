import json
import numpy as np
import pandas as pd
from pathlib import Path
from xgboost import XGBClassifier
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import classification_report
from sklearn.preprocessing import LabelEncoder

from trading_ai.core.config import get_settings
from trading_ai.data_layer.market_data import fetch_ohlcv
from trading_ai.data_layer.feature_engineer import get_feature_matrix, build_features, build_target

settings = get_settings()

# XGBoost parametreleri — crypto/forex için dengeli
XGB_PARAMS = {
    "n_estimators": 300,
    "max_depth": 5,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 3,
    "gamma": 0.1,
    "reg_alpha": 0.1,
    "reg_lambda": 1.0,
    "use_label_encoder": False,
    "eval_metric": "mlogloss",
    "random_state": 42,
    "n_jobs": -1,
}


def train(
    symbol: str = None,
    timeframe: str = None,
    bars: int = 1000,
    forward_bars: int = 3,
    threshold_pct: float = 0.005,
    save_path: str = None,
) -> dict:
    symbol    = symbol    or settings.default_symbol
    timeframe = timeframe or settings.default_timeframe
    save_path = save_path or settings.model_path

    print(f"[TRAIN] {symbol} {timeframe} | {bars} bars")
    df = fetch_ohlcv(symbol, timeframe, limit=bars)

    df_feat   = build_features(df)
    target    = build_target(df_feat, forward_bars=forward_bars, threshold_pct=threshold_pct)

    X, feature_cols = get_feature_matrix(df)
    y = target.loc[X.index]
    y = y.dropna()
    X = X.loc[y.index]

    # Etiket encode: -1,0,1 → 0,1,2
    le = LabelEncoder()
    y_enc = le.fit_transform(y)

    # Zaman serisi cross-validation
    tscv   = TimeSeriesSplit(n_splits=5)
    scores = []
    for fold, (tr_idx, val_idx) in enumerate(tscv.split(X)):
        X_tr, X_val = X.iloc[tr_idx], X.iloc[val_idx]
        y_tr, y_val = y_enc[tr_idx], y_enc[val_idx]

        model = XGBClassifier(**XGB_PARAMS)
        model.fit(X_tr, y_tr, eval_set=[(X_val, y_val)], verbose=False)

        acc = (model.predict(X_val) == y_val).mean()
        scores.append(acc)
        print(f"  Fold {fold+1}: accuracy={acc:.3f}")

    print(f"[TRAIN] Ortalama CV accuracy: {np.mean(scores):.3f}")

    # Son modeli tüm veri ile eğit
    final_model = XGBClassifier(**XGB_PARAMS)
    final_model.fit(X, y_enc, verbose=False)

    # Feature importance
    importance = dict(zip(feature_cols, final_model.feature_importances_))
    importance = dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))

    # Kaydet
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    final_model.save_model(save_path)

    meta = {
        "symbol": symbol,
        "timeframe": timeframe,
        "feature_cols": feature_cols,
        "label_classes": le.classes_.tolist(),
        "cv_accuracy_mean": float(np.mean(scores)),
        "cv_accuracy_std": float(np.std(scores)),
        "top_features": dict(list(importance.items())[:10]),
        "trained_bars": len(X),
    }
    meta_path = save_path.replace(".json", "_meta.json")
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    print(f"[TRAIN] Model kaydedildi → {save_path}")
    print("[TRAIN] Top 5 feature:")
    for feat, imp in list(importance.items())[:5]:
        print(f"  {feat}: {imp:.4f}")

    return meta
