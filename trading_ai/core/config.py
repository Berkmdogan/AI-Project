from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # === Anthropic ===
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-6"

    # === Exchange (CCXT) ===
    exchange_id: str = "binance"          # binance, bybit, okx ...
    exchange_api_key: str = ""
    exchange_secret: str = ""
    default_symbol: str = "BTC/USDT"
    default_timeframe: str = "1h"

    # === ML ===
    model_path: str = "trading_ai/ml_layer/models/xgboost_model.json"
    lookback_bars: int = 100              # Feature hesabı için geriye bakış
    retrain_every_n_bars: int = 500

    # === Signal Thresholds ===
    buy_threshold: float = 0.60           # ML skoru bu değerin üstü → BUY
    sell_threshold: float = 0.60          # ML skoru bu değerin üstü → SELL

    # === Telegram ===
    telegram_token: str = ""
    telegram_chat_id: str = ""

    # === FastAPI ===
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
