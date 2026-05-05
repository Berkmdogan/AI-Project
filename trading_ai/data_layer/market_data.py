import ccxt
import pandas as pd
from datetime import datetime, timezone
from typing import Optional
from trading_ai.core.config import get_settings

settings = get_settings()


def get_exchange() -> ccxt.Exchange:
    exchange_class = getattr(ccxt, settings.exchange_id)
    params = {"enableRateLimit": True}
    if settings.exchange_api_key:
        params["apiKey"] = settings.exchange_api_key
        params["secret"] = settings.exchange_secret
    return exchange_class(params)


def fetch_ohlcv(
    symbol: str = None,
    timeframe: str = None,
    limit: int = 500,
    since: Optional[datetime] = None,
) -> pd.DataFrame:
    symbol    = symbol    or settings.default_symbol
    timeframe = timeframe or settings.default_timeframe

    exchange = get_exchange()
    since_ms = int(since.timestamp() * 1000) if since else None
    raw      = exchange.fetch_ohlcv(symbol, timeframe, since=since_ms, limit=limit)

    df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df.set_index("timestamp", inplace=True)
    df.sort_index(inplace=True)
    return df


def get_current_price(symbol: str = None) -> float:
    symbol   = symbol or settings.default_symbol
    exchange = get_exchange()
    ticker   = exchange.fetch_ticker(symbol)
    return float(ticker["last"])
