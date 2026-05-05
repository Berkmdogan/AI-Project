from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
from typing import Optional


class SignalType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    NEUTRAL = "NEUTRAL"


class SignalStrength(str, Enum):
    STRONG = "STRONG"    # Her iki pencere (dist1 + dist2) aynı anda
    MEDIUM = "MEDIUM"    # Sadece dist2
    MINOR = "MINOR"      # Sadece dist1


class MarketState(BaseModel):
    symbol: str
    timeframe: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

    # Teknik göstergeler
    atr: float
    rsi: float
    adx: float
    ema_fast: float
    ema_slow: float
    ema_slope: float           # FastEMA'nın 3 barlık eğimi

    # WPR
    wpr: float

    # SuperSignals
    super_sell_strong: bool = False    # dist2 satış
    super_buy_strong: bool = False     # dist2 alış
    super_sell_minor: bool = False     # dist1 satış
    super_buy_minor: bool = False      # dist1 alış


class MLPrediction(BaseModel):
    signal: SignalType
    confidence: float = Field(ge=0.0, le=1.0)
    buy_prob: float
    sell_prob: float
    neutral_prob: float
    feature_importance: dict[str, float] = {}


class TradeSignal(BaseModel):
    id: str
    symbol: str
    timeframe: str
    timestamp: datetime
    signal: SignalType
    strength: SignalStrength
    ml_confidence: float
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    risk_reward: float
    llm_analysis: Optional[str] = None
    market_state: Optional[MarketState] = None


class AnalysisRequest(BaseModel):
    symbol: str = "BTC/USDT"
    timeframe: str = "1h"
    bars: int = 200


class AnalysisResponse(BaseModel):
    signal: TradeSignal
    raw_market_state: MarketState
    ml_prediction: MLPrediction
    generated_at: datetime
