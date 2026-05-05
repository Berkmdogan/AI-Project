from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone
import uuid

from trading_ai.core.models import AnalysisRequest, AnalysisResponse, TradeSignal, SignalType, SignalStrength
from trading_ai.core.config import get_settings
from trading_ai.data_layer.market_data import fetch_ohlcv, get_current_price
from trading_ai.ml_layer.predict import predict, extract_market_state
from trading_ai.llm_layer.analyzer import analyze

settings = get_settings()
app = FastAPI(title="AI Trading Signal API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_market(req: AnalysisRequest):
    try:
        df = fetch_ohlcv(req.symbol, req.timeframe, limit=req.bars)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Veri çekilemedi: {e}")

    ml_pred    = predict(df)
    mkt_state  = extract_market_state(df, req.symbol, req.timeframe)
    llm_text   = analyze(mkt_state, ml_pred)

    signal = _build_trade_signal(mkt_state, ml_pred, llm_text)

    return AnalysisResponse(
        signal=signal,
        raw_market_state=mkt_state,
        ml_prediction=ml_pred,
        generated_at=datetime.now(timezone.utc),
    )


@app.get("/price/{symbol:path}")
def current_price(symbol: str):
    try:
        price = get_current_price(symbol.replace("-", "/").upper())
        return {"symbol": symbol, "price": price}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.post("/train")
async def trigger_training(background_tasks: BackgroundTasks, symbol: str = "BTC/USDT", timeframe: str = "1h"):
    from trading_ai.ml_layer.train import train
    background_tasks.add_task(train, symbol=symbol, timeframe=timeframe)
    return {"status": "training_started", "symbol": symbol, "timeframe": timeframe}


def _build_trade_signal(mkt_state, ml_pred, llm_text: str) -> TradeSignal:
    atr   = mkt_state.atr
    price = mkt_state.close

    # Sinyal gücü: iki pencere aynı yönde mi?
    both_buy  = mkt_state.super_buy_strong  and mkt_state.super_buy_minor
    both_sell = mkt_state.super_sell_strong and mkt_state.super_sell_minor

    if both_buy or both_sell:
        strength = SignalStrength.STRONG
    elif mkt_state.super_buy_strong or mkt_state.super_sell_strong:
        strength = SignalStrength.MEDIUM
    else:
        strength = SignalStrength.MINOR

    # SL / TP (ATR tabanlı)
    sl_dist  = atr * 1.5
    tp1_dist = atr * 2.0
    tp2_dist = atr * 4.0

    if ml_pred.signal == SignalType.BUY:
        sl  = price - sl_dist
        tp1 = price + tp1_dist
        tp2 = price + tp2_dist
    elif ml_pred.signal == SignalType.SELL:
        sl  = price + sl_dist
        tp1 = price - tp1_dist
        tp2 = price - tp2_dist
    else:
        sl = tp1 = tp2 = price

    rr = tp1_dist / sl_dist if sl_dist > 0 else 0

    return TradeSignal(
        id=str(uuid.uuid4()),
        symbol=mkt_state.symbol,
        timeframe=mkt_state.timeframe,
        timestamp=mkt_state.timestamp,
        signal=ml_pred.signal,
        strength=strength,
        ml_confidence=ml_pred.confidence,
        entry_price=price,
        stop_loss=round(sl, 8),
        take_profit_1=round(tp1, 8),
        take_profit_2=round(tp2, 8),
        risk_reward=round(rr, 2),
        llm_analysis=llm_text,
        market_state=mkt_state,
    )
