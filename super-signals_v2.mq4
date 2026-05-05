#property copyright "Super Signals v2.2"
#property link      ""
#property version   "2.2"
#property strict
#property indicator_chart_window
#property indicator_buffers 4
#property indicator_color1 Yellow   // Strong Sell
#property indicator_color2 Lime     // Strong Buy
#property indicator_color3 Red      // Minor  Sell
#property indicator_color4 Aqua     // Minor  Buy
#property indicator_width1 2
#property indicator_width2 2
#property indicator_width3 1
#property indicator_width4 1

//=== Core ===
input int    dist2            = 21;
input int    dist1            = 14;
input int    ATR_Period       = 50;
input double ATR_Multi_Main   = 1.0;
input double ATR_Multi_Minor  = 0.5;

//=== EMA Trend Filter ===
// Yalnızca trendin yönünde sinyal üretir.
// EMA50 > EMA200 → sadece BUY, EMA50 < EMA200 → sadece SELL.
input bool   UseTrendFilter   = true;
input int    FastEMA          = 50;
input int    SlowEMA          = 200;

//=== RSI Filter ===
input bool   UseRSIFilter     = false;
input int    RSIPeriod        = 14;
input int    RSI_OB           = 65;   // RSI bu değerin ALTINDA olmalı → SELL onayı
input int    RSI_OS           = 35;   // RSI bu değerin ÜSTÜNDE olmalı → BUY  onayı

//=== ADX Filter ===
input bool   UseADXFilter     = false;
input int    ADX_Period       = 14;
input int    ADX_MinLevel     = 20;

//=== Alerts ===
input bool   alertsOn         = false;
input bool   alertsOnCurrent  = false;
input bool   alertsMessage    = true;
input bool   alertsSound      = false;
input bool   alertsEmail      = false;
input bool   alertsPush       = false;

//═══════════════════════════════════════════════════════════════════
double b1[];   // Strong Sell
double b2[];   // Strong Buy
double b3[];   // Minor  Sell
double b4[];   // Minor  Buy

datetime LastAlertTime = 0;

//+------------------------------------------------------------------+
int OnInit()
{
   SetIndexBuffer(0, b1);
   SetIndexBuffer(1, b2);
   SetIndexBuffer(2, b3);
   SetIndexBuffer(3, b4);

   SetIndexStyle(0, DRAW_ARROW, STYLE_SOLID, 2, Yellow); SetIndexArrow(0, 234);
   SetIndexStyle(1, DRAW_ARROW, STYLE_SOLID, 2, Lime);   SetIndexArrow(1, 233);
   SetIndexStyle(2, DRAW_ARROW, STYLE_SOLID, 1, Red);    SetIndexArrow(2, 234);
   SetIndexStyle(3, DRAW_ARROW, STYLE_SOLID, 1, Aqua);   SetIndexArrow(3, 233);

   SetIndexEmptyValue(0, EMPTY_VALUE);
   SetIndexEmptyValue(1, EMPTY_VALUE);
   SetIndexEmptyValue(2, EMPTY_VALUE);
   SetIndexEmptyValue(3, EMPTY_VALUE);

   SetIndexLabel(0, "Strong Sell");
   SetIndexLabel(1, "Strong Buy");
   SetIndexLabel(2, "Minor Sell");
   SetIndexLabel(3, "Minor Buy");

   string filters = "";
   if(UseTrendFilter) filters += " EMA";
   if(UseRSIFilter)   filters += " RSI";
   if(UseADXFilter)   filters += " ADX";
   if(filters == "")  filters  = " None";
   IndicatorShortName("SuperSignals v2.2 [Filters:" + filters + " ]");

   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   Comment("");
}

//+------------------------------------------------------------------+
int OnCalculate(const int rates_total,
                const int prev_calculated,
                const datetime &time[],
                const double   &open[],
                const double   &high[],
                const double   &low[],
                const double   &close[],
                const long     &tick_volume[],
                const long     &volume[],
                const int      &spread[])
{
   // DEĞİŞİKLİK 2: lastBarTime erken-çıkış bloğu kaldırıldı.
   // Yeniden yükleme / TF değişimi sonrası geçmiş barlar boş kalıyordu.
   // prev_calculated mekanizması başlangıç barını zaten doğru belirliyor.

   int minBars = MathMax(dist2 * 2, MathMax(ATR_Period + 5, SlowEMA + 5));
   if(rates_total < minBars) return(0);

   int start;
   if(prev_calculated <= 0)
      start = rates_total - 1;
   else
      start = MathMin(rates_total - 1, rates_total - prev_calculated + dist2 + 1);

   for(int i = start; i >= 0; i--)
   {
      b1[i] = EMPTY_VALUE;
      b2[i] = EMPTY_VALUE;
      b3[i] = EMPTY_VALUE;
      b4[i] = EMPTY_VALUE;

      int start2 = i - dist2 / 2;
      int start1 = i - dist1 / 2;
      if(start2 < 0 || start1 < 0) continue;

      int hhb  = Highest(NULL, 0, MODE_HIGH, dist2, start2);
      int llb  = Lowest (NULL, 0, MODE_LOW,  dist2, start2);
      int hhb1 = Highest(NULL, 0, MODE_HIGH, dist1, start1);
      int llb1 = Lowest (NULL, 0, MODE_LOW,  dist1, start1);

      double tr = iATR(NULL, 0, ATR_Period, i);
      if(tr <= 0) continue;

      if(i == hhb  && CheckFilters(i, false, close)) b1[i] = High[hhb]  + tr * ATR_Multi_Main;
      if(i == llb  && CheckFilters(i, true,  close)) b2[i] = Low[llb]   - tr * ATR_Multi_Main;
      if(i == hhb1 && CheckFilters(i, false, close)) b3[i] = High[hhb1] + tr * ATR_Multi_Minor;
      if(i == llb1 && CheckFilters(i, true,  close)) b4[i] = Low[llb1]  - tr * ATR_Multi_Minor;
   }

   if(alertsOn) ProcessAlerts();
   return(rates_total);
}

//+------------------------------------------------------------------+
bool CheckFilters(int bar, bool isBuy, const double &close[])
{
   // DEĞİŞİKLİK 3: EMA trend filtresi eklendi.
   // Yükselen trendde (EMA50 > EMA200) yalnızca BUY, düşen trendde yalnızca SELL.
   if(UseTrendFilter)
   {
      double emaFast = iMA(NULL, 0, FastEMA, 0, MODE_EMA, PRICE_CLOSE, bar);
      double emaSlow = iMA(NULL, 0, SlowEMA, 0, MODE_EMA, PRICE_CLOSE, bar);
      // Sadece EMA yönüne bak: fiyatın EMA'ya göre konumu şart değil.
      // Bu sayede güçlü trendlerde karşı-taraf sinyaller de oluşabilir.
      if( isBuy && emaFast < emaSlow) return false;
      if(!isBuy && emaFast > emaSlow) return false;
   }

   // DEĞİŞİKLİK 1: RSI filtre yönü düzeltildi.
   // Eski: BUY için rsi < RSI_OS şartı → trendlerde sinyal üretmiyordu.
   // Yeni: BUY için rsi > RSI_OS (yukarı momentum var), SELL için rsi < RSI_OB.
   if(UseRSIFilter)
   {
      double rsi = iRSI(NULL, 0, RSIPeriod, PRICE_CLOSE, bar);
      if( isBuy && rsi < RSI_OS) return false;
      if(!isBuy && rsi > RSI_OB) return false;
   }

   if(UseADXFilter)
   {
      double adx = iADX(NULL, 0, ADX_Period, PRICE_CLOSE, MODE_MAIN, bar);
      if(adx < ADX_MinLevel) return false;
   }

   return true;
}

//+------------------------------------------------------------------+
void ProcessAlerts()
{
   int forBar = alertsOnCurrent ? 0 : 1;
   datetime barTime = Time[forBar];
   if(barTime == LastAlertTime) return;

   string signal = "";
   if     (b1[forBar] != EMPTY_VALUE && b3[forBar] != EMPTY_VALUE) signal = "strong sell";
   else if(b1[forBar] != EMPTY_VALUE)                               signal = "sell";
   else if(b3[forBar] != EMPTY_VALUE)                               signal = "minor sell or exit buy";
   else if(b2[forBar] != EMPTY_VALUE && b4[forBar] != EMPTY_VALUE) signal = "strong buy";
   else if(b2[forBar] != EMPTY_VALUE)                               signal = "buy";
   else if(b4[forBar] != EMPTY_VALUE)                               signal = "minor buy or exit sell";
   if(signal == "") return;

   LastAlertTime = barTime;
   string message = Symbol() + " [TF:" + (string)Period() + "m] at " +
                    TimeToStr(TimeLocal(), TIME_SECONDS) +
                    "  Super Signal: " + signal +
                    "  Bid:" + DoubleToStr(Bid, Digits);

   if(alertsMessage) Alert(message);
   if(alertsSound)   PlaySound("alert2.wav");
   if(alertsEmail)   SendMail(Symbol() + " Super Signal", message);
   if(alertsPush)    SendNotification(message);
}
//+------------------------------------------------------------------+
