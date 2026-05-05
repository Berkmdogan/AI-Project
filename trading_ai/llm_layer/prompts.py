from trading_ai.core.models import MarketState, MLPrediction

SYSTEM_PROMPT = """Sen uzman bir kripto ve forex piyasası analistisin.
Görevin: teknik gösterge verilerini ve ML model tahminini birlikte değerlendirerek
net, uygulanabilir bir trading analizi sunmak.

Analiz formatın şu başlıkları içermeli:
1. PIYASA DURUMU — Trend yönü ve güç
2. SINYAL DEĞERLENDİRMESİ — Sinyallerin tutarlılığı
3. GİRİŞ/ÇIKIŞ — Entry, Stop-Loss, TP seviyeleri
4. RİSK — Setup'ın zayıf noktaları
5. KARAR — BUY / SELL / BEKLE (tek kelime + kısa gerekçe)

Kurallar:
- Kesin ve kısa ol, 200 kelimeyi geçme
- Spekülatif tahminlerden kaçın, sadece mevcut veriyi yorumla
- Risk/ödül oranı 1:2'nin altındaysa işlem önerme"""


def build_user_prompt(state: MarketState, pred: MLPrediction) -> str:
    trend = "YUKARI" if state.ema_fast > state.ema_slow else "AŞAĞI"
    ema_slope_dir = "yükseliyor" if state.ema_slope > 0 else "düşüyor"

    ss_signals = []
    if state.super_sell_strong: ss_signals.append("SuperSignals Güçlü SATIŞ")
    if state.super_buy_strong:  ss_signals.append("SuperSignals Güçlü ALIŞ")
    if state.super_sell_minor:  ss_signals.append("SuperSignals Minor SATIŞ")
    if state.super_buy_minor:   ss_signals.append("SuperSignals Minor ALIŞ")
    ss_text = ", ".join(ss_signals) if ss_signals else "Sinyal yok"

    return f"""## Piyasa Verisi
Sembol   : {state.symbol} [{state.timeframe}]
Zaman    : {state.timestamp.strftime('%Y-%m-%d %H:%M')} UTC
Fiyat    : {state.close:.4f}

## Teknik Göstergeler
Trend    : EMA50={state.ema_fast:.2f} / EMA200={state.ema_slow:.2f} → {trend} TREND
EMA Eğim : {ema_slope_dir} ({state.ema_slope:+.4f})
RSI(14)  : {state.rsi:.1f}
ADX(14)  : {state.adx:.1f}
WPR(14)  : {state.wpr:.1f}
ATR(50)  : {state.atr:.4f}

## SuperSignals
{ss_text}

## ML Model Tahmini
Sinyal     : {pred.signal.value}
Güven      : %{pred.confidence * 100:.1f}
BUY  olasılığı : %{pred.buy_prob * 100:.1f}
SELL olasılığı : %{pred.sell_prob * 100:.1f}
NEUTRAL    : %{pred.neutral_prob * 100:.1f}

## Önemli Feature'lar (Top 3)
{_top_features(pred, n=3)}

Yukarıdaki verilere dayanarak trading analizi yap."""


def _top_features(pred: MLPrediction, n: int = 3) -> str:
    if not pred.feature_importance:
        return "Bilgi yok"
    top = sorted(pred.feature_importance.items(), key=lambda x: x[1], reverse=True)[:n]
    return "\n".join(f"  - {k}: {v:.4f}" for k, v in top)
