import asyncio
import logging
from datetime import datetime, timezone
from telegram import Bot
from telegram.constants import ParseMode

from trading_ai.core.config import get_settings
from trading_ai.core.models import TradeSignal, SignalType, SignalStrength
from trading_ai.data_layer.market_data import fetch_ohlcv
from trading_ai.ml_layer.predict import predict, extract_market_state
from trading_ai.llm_layer.analyzer import analyze
from trading_ai.ui_layer.api import _build_trade_signal

settings = get_settings()
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

SIGNAL_EMOJI = {
    SignalType.BUY:     "🟢",
    SignalType.SELL:    "🔴",
    SignalType.NEUTRAL: "⚪",
}

STRENGTH_EMOJI = {
    SignalStrength.STRONG: "🔥🔥🔥",
    SignalStrength.MEDIUM: "⚡⚡",
    SignalStrength.MINOR:  "💧",
}


def format_signal_message(signal: TradeSignal) -> str:
    emoji    = SIGNAL_EMOJI[signal.signal]
    strength = STRENGTH_EMOJI[signal.strength]
    conf     = f"{signal.ml_confidence * 100:.1f}"

    lines = [
        f"{emoji} *{signal.signal.value}* {strength}",
        f"",
        f"📌 *{signal.symbol}* `[{signal.timeframe}]`",
        f"⏰ `{signal.timestamp.strftime('%Y-%m-%d %H:%M')} UTC`",
        f"",
        f"💰 Entry  : `{signal.entry_price:.4f}`",
        f"🛑 SL     : `{signal.stop_loss:.4f}`",
        f"🎯 TP1    : `{signal.take_profit_1:.4f}`",
        f"🎯 TP2    : `{signal.take_profit_2:.4f}`",
        f"📊 R/R    : `1:{signal.risk_reward}`",
        f"🤖 ML     : `%{conf}` güven",
        f"",
    ]

    if signal.llm_analysis:
        lines += [
            f"🧠 *Analiz:*",
            f"{signal.llm_analysis[:600]}",
        ]

    return "\n".join(lines)


async def send_signal(signal: TradeSignal):
    if not settings.telegram_token or not settings.telegram_chat_id:
        log.warning("Telegram token veya chat_id ayarlanmamış.")
        return

    bot     = Bot(token=settings.telegram_token)
    message = format_signal_message(signal)
    await bot.send_message(
        chat_id=settings.telegram_chat_id,
        text=message,
        parse_mode=ParseMode.MARKDOWN,
    )
    log.info(f"Telegram mesajı gönderildi: {signal.signal.value} {signal.symbol}")


async def run_monitor(
    symbol: str = None,
    timeframe: str = None,
    interval_seconds: int = 300,
    only_non_neutral: bool = True,
):
    """
    Belirtilen aralıkta piyasayı izler,
    sinyal oluştuğunda Telegram'a bildirim gönderir.
    """
    symbol    = symbol    or settings.default_symbol
    timeframe = timeframe or settings.default_timeframe

    log.info(f"Monitor başlatıldı: {symbol} {timeframe} | {interval_seconds}s aralık")

    while True:
        try:
            df        = fetch_ohlcv(symbol, timeframe, limit=300)
            ml_pred   = predict(df)
            mkt_state = extract_market_state(df, symbol, timeframe)
            llm_text  = analyze(mkt_state, ml_pred)
            signal    = _build_trade_signal(mkt_state, ml_pred, llm_text)

            if only_non_neutral and signal.signal == SignalType.NEUTRAL:
                log.info(f"[{symbol}] NEUTRAL — bildirim atlandı")
            else:
                await send_signal(signal)

        except Exception as e:
            log.error(f"Monitor hatası: {e}")

        await asyncio.sleep(interval_seconds)


if __name__ == "__main__":
    asyncio.run(run_monitor())
