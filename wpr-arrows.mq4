//+------------------------------------------------------------------+
//|                                                  wpr-arrows.mq4 |
//|                         [www.forex-station.com]                 |
//|          Modernized: #property strict, OnCalculate, bug fixes   |
//+------------------------------------------------------------------+
#property copyright "[www.forex-station.com]"
#property link      "[www.forex-station.com]"
#property version   "2.0"
#property strict
#property indicator_chart_window
#property indicator_buffers 2
#property indicator_color1 DarkOrange
#property indicator_color2 LightBlue
#property indicator_width1 1
#property indicator_width2 1

//+------------------------------------------------------------------+
enum enPrices
{
   pr_close,       // Close
   pr_open,        // Open
   pr_high,        // High
   pr_low,         // Low
   pr_median,      // Median
   pr_typical,     // Typical
   pr_weighted,    // Weighted
   pr_average,     // Average (high+low+open+close)/4
   pr_medianb,     // Average median body (open+close)/2
   pr_tbiased,     // Trend biased price
   pr_tbiased2,    // Trend biased (extreme) price
   pr_haclose,     // Heiken ashi close
   pr_haopen,      // Heiken ashi open
   pr_hahigh,      // Heiken ashi high
   pr_halow,       // Heiken ashi low
   pr_hamedian,    // Heiken ashi median
   pr_hatypical,   // Heiken ashi typical
   pr_haweighted,  // Heiken ashi weighted
   pr_haaverage,   // Heiken ashi average
   pr_hamedianb,   // Heiken ashi median body
   pr_hatbiased,   // Heiken ashi trend biased price
   pr_hatbiased2,  // Heiken ashi trend biased (extreme) price
   pr_habclose,    // Heiken ashi (better formula) close
   pr_habopen,     // Heiken ashi (better formula) open
   pr_habhigh,     // Heiken ashi (better formula) high
   pr_hablow,      // Heiken ashi (better formula) low
   pr_habmedian,   // Heiken ashi (better formula) median
   pr_habtypical,  // Heiken ashi (better formula) typical
   pr_habweighted, // Heiken ashi (better formula) weighted
   pr_habaverage,  // Heiken ashi (better formula) average
   pr_habmedianb,  // Heiken ashi (better formula) median body
   pr_habtbiased,  // Heiken ashi (better formula) trend biased price
   pr_habtbiased2  // Heiken ashi (better formula) trend biased (extreme) price
};

//=== Inputs ===
input ENUM_TIMEFRAMES TimeFrame       = PERIOD_CURRENT;
input double          x1              = 67;
input double          x2              = 33;
input enPrices        WprPrice        = pr_close;
input int             Risk            = 3;
input double          ArrowsGap       = 1.0;
input bool            ArrowOnFirst    = true;
input bool            alertsOn        = false;
input bool            alertsOnCurrent = true;
input bool            alertsMessage   = true;
input bool            alertsSound     = false;
input bool            alertsEmail     = false;
input bool            alertsNotify    = false;

//=== Buffers ===
double arrDn[];
double arrUp[];
double wpr[];
double price[];

string         indicatorFileName;
bool           returnBars;
datetime       LastAlertTime  = 0;
ENUM_TIMEFRAMES effectiveTF;   // input TimeFrame kopyası — strict modda input değiştirilemez

//+------------------------------------------------------------------+
int OnInit()
{
   IndicatorBuffers(4);
   SetIndexBuffer(0, arrDn); SetIndexStyle(0, DRAW_ARROW); SetIndexArrow(0, 234);
   SetIndexBuffer(1, arrUp); SetIndexStyle(1, DRAW_ARROW); SetIndexArrow(1, 233);
   SetIndexBuffer(2, wpr);
   SetIndexBuffer(3, price);

   SetIndexEmptyValue(0, EMPTY_VALUE);
   SetIndexEmptyValue(1, EMPTY_VALUE);
   SetIndexLabel(0, "WPR Sell");
   SetIndexLabel(1, "WPR Buy");

   indicatorFileName = WindowExpertName();
   returnBars        = (TimeFrame == -99);
   effectiveTF       = returnBars ? TimeFrame
                                  : (ENUM_TIMEFRAMES)MathMax((int)TimeFrame, (int)_Period);

   IndicatorShortName("WPR Arrows [TF:" + IntegerToString(effectiveTF) +
                      " Risk:" + IntegerToString(Risk) + "]");
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason) { Comment(""); }

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
   if(rates_total < 20) return(0);

   int limit;
   if(prev_calculated <= 0)
      limit = rates_total - 1;
   else
      limit = MathMin(rates_total - prev_calculated + 1, rates_total - 1);

   if(returnBars) { arrDn[0] = limit + 1; return(rates_total); }

   //--- Multi-timeframe modu
   if(effectiveTF != Period())
   {
      int mtfBars = (int)MathMax(limit, MathMin(rates_total - 1,
                   iCustom(NULL, effectiveTF, indicatorFileName, -99, 0, 0)
                   * effectiveTF / Period()));

      for(int i = mtfBars; i >= 0; i--)
      {
         int y = iBarShift(NULL, effectiveTF, time[i]);
         int x = y;
         if(ArrowOnFirst)
            { if(i < rates_total - 1) x = iBarShift(NULL, effectiveTF, time[i + 1]); }
         else
            { if(i > 0) x = iBarShift(NULL, effectiveTF, time[i - 1]); else x = -1; }

         arrDn[i] = EMPTY_VALUE;
         arrUp[i] = EMPTY_VALUE;

         if(y != x)
         {
            arrDn[i] = iCustom(NULL, effectiveTF, indicatorFileName,
                               PERIOD_CURRENT, x1, x2, WprPrice, Risk, ArrowsGap,
                               alertsOn, alertsOnCurrent, alertsMessage,
                               alertsSound, alertsEmail, alertsNotify, 0, y);
            arrUp[i] = iCustom(NULL, effectiveTF, indicatorFileName,
                               PERIOD_CURRENT, x1, x2, WprPrice, Risk, ArrowsGap,
                               alertsOn, alertsOnCurrent, alertsMessage,
                               alertsSound, alertsEmail, alertsNotify, 1, y);
         }
      }
      if(alertsOn) ProcessAlerts();
      return(rates_total);
   }

   //--- Ana hesaplama döngüsü
   for(int i = limit; i >= 0; i--)
   {
      arrDn[i] = EMPTY_VALUE;
      arrUp[i] = EMPTY_VALUE;

      // FIX 1: k tüm döngülerden önce tek bir yerde tanımlandı (strict mod uyumu)
      int k = 0;

      // Ortalama range hesabı (10 bar)
      double range = 0;
      for(k = 0; k < 10 && i + k < rates_total; k++)
         range += high[i + k] - low[i + k];
      range /= 10.0;
      if(range <= 0) continue;

      // Volatilite spike tespiti → dinamik periyot
      int period = 3 + Risk * 2;

      bool found1 = false;
      for(k = 0; k < 6 && !found1 && i + k + 1 < rates_total; k++)
         found1 = (MathAbs(open[i + k] - close[i + k + 1]) >= range * 2.0);

      bool found2 = false;
      for(k = 0; k < 9 && !found2 && i + k + 3 < rates_total; k++)
         found2 = (MathAbs(close[i + k + 3] - close[i + k]) >= range * 4.6);

      if(found1) period = 3;
      if(found2) period = 4;

      if(i + period >= rates_total) continue;

      price[i]    = getPrice(WprPrice, open, close, high, low, i, rates_total);
      double hi   = high[iHighest(NULL, 0, MODE_HIGH, period, i)];
      double lo   = low [iLowest (NULL, 0, MODE_LOW,  period, i)];

      wpr[i] = (hi != lo) ? 100.0 + (-100.0) * (hi - price[i]) / (hi - lo) : 0;

      // Sinyal: WPR oversold bölgesine girdi, öncesinde overbought'tı → arrDn
      if(wpr[i] < x2 - Risk)
      {
         for(k = 1; i + k < rates_total &&
             wpr[i + k] >= x2 - Risk && wpr[i + k] <= x1 + Risk; k++) {}
         // FIX 2: sınır dışı erişim koruması eklendi
         if(i + k < rates_total && wpr[i + k] > x1 + Risk)
            arrDn[i] = high[i] + range * ArrowsGap;
      }

      // Sinyal: WPR overbought bölgesine girdi, öncesinde oversold'du → arrUp
      if(wpr[i] > x1 + Risk)
      {
         for(k = 1; i + k < rates_total &&
             wpr[i + k] >= x2 - Risk && wpr[i + k] <= x1 + Risk; k++) {}
         // FIX 2: sınır dışı erişim koruması eklendi
         if(i + k < rates_total && wpr[i + k] < x2 - Risk)
            arrUp[i] = low[i] - range * ArrowsGap;
      }
   }

   if(alertsOn) ProcessAlerts();
   return(rates_total);
}

//+------------------------------------------------------------------+
void ProcessAlerts()
{
   int      bar     = alertsOnCurrent ? 0 : 1;
   datetime barTime = Time[bar];
   if(barTime == LastAlertTime) return;

   string signal = "";
   if(arrUp[bar] != EMPTY_VALUE) signal = "BUY";
   if(arrDn[bar] != EMPTY_VALUE) signal = (signal == "" ? "SELL" : "BUY & SELL");
   if(signal == "") return;

   LastAlertTime = barTime;
   string message = Symbol() + " [TF:" + IntegerToString(Period()) + "m] at " +
                    TimeToStr(TimeLocal(), TIME_SECONDS) +
                    "  WPR Signal: " + signal +
                    "  Bid:" + DoubleToStr(Bid, Digits);

   if(alertsMessage) Alert(message);
   if(alertsNotify)  SendNotification(message);
   if(alertsEmail)   SendMail(Symbol() + " WPR Signal", message);
   if(alertsSound)   PlaySound("alert2.wav");
}

//+------------------------------------------------------------------+
#define _prHABF(_t) (_t >= pr_habclose && _t <= pr_habtbiased2)
#define _priceInstances     1
#define _priceInstancesSize 4
double workHa[][_priceInstances * _priceInstancesSize];

double getPrice(int tprice,
                const double &open[], const double &close[],
                const double &high[], const double &low[],
                int i, int bars, int instanceNo = 0)
{
   if(tprice >= pr_haclose)
   {
      if(ArrayRange(workHa, 0) != bars) ArrayResize(workHa, bars);
      instanceNo *= _priceInstancesSize;
      int r = bars - i - 1;

      double haOpen  = (r > 0) ? (workHa[r-1][instanceNo+2] + workHa[r-1][instanceNo+3]) / 2.0
                                : (open[i] + close[i]) / 2.0;
      double haClose = (open[i] + high[i] + low[i] + close[i]) / 4.0;

      if(_prHABF(tprice))
      {
         if(high[i] != low[i])
            haClose = (open[i] + close[i]) / 2.0 +
                      (((close[i] - open[i]) / (high[i] - low[i])) *
                       MathAbs((close[i] - open[i]) / 2.0));
         else
            haClose = (open[i] + close[i]) / 2.0;
      }

      double haHigh = MathMax(high[i], MathMax(haOpen, haClose));
      double haLow  = MathMin(low[i],  MathMin(haOpen, haClose));

      if(haOpen < haClose) { workHa[r][instanceNo+0] = haLow;  workHa[r][instanceNo+1] = haHigh; }
      else                 { workHa[r][instanceNo+0] = haHigh; workHa[r][instanceNo+1] = haLow;  }
      workHa[r][instanceNo+2] = haOpen;
      workHa[r][instanceNo+3] = haClose;

      switch(tprice)
      {
         case pr_haclose:    case pr_habclose:    return(haClose);
         case pr_haopen:     case pr_habopen:     return(haOpen);
         case pr_hahigh:     case pr_habhigh:     return(haHigh);
         case pr_halow:      case pr_hablow:      return(haLow);
         case pr_hamedian:   case pr_habmedian:   return((haHigh + haLow) / 2.0);
         case pr_hamedianb:  case pr_habmedianb:  return((haOpen + haClose) / 2.0);
         case pr_hatypical:  case pr_habtypical:  return((haHigh + haLow + haClose) / 3.0);
         case pr_haweighted: case pr_habweighted: return((haHigh + haLow + haClose + haClose) / 4.0);
         case pr_haaverage:  case pr_habaverage:  return((haHigh + haLow + haClose + haOpen) / 4.0);
         case pr_hatbiased:  case pr_habtbiased:
            return(haClose > haOpen ? (haHigh + haClose) / 2.0 : (haLow + haClose) / 2.0);
         case pr_hatbiased2: case pr_habtbiased2:
            if(haClose > haOpen) return(haHigh);
            if(haClose < haOpen) return(haLow);
            return(haClose);
      }
   }

   switch(tprice)
   {
      case pr_close:    return(close[i]);
      case pr_open:     return(open[i]);
      case pr_high:     return(high[i]);
      case pr_low:      return(low[i]);
      case pr_median:   return((high[i] + low[i]) / 2.0);
      case pr_medianb:  return((open[i] + close[i]) / 2.0);
      case pr_typical:  return((high[i] + low[i] + close[i]) / 3.0);
      case pr_weighted: return((high[i] + low[i] + close[i] + close[i]) / 4.0);
      case pr_average:  return((high[i] + low[i] + close[i] + open[i]) / 4.0);
      case pr_tbiased:
         return(close[i] > open[i] ? (high[i] + close[i]) / 2.0 : (low[i] + close[i]) / 2.0);
      case pr_tbiased2:
         if(close[i] > open[i]) return(high[i]);
         if(close[i] < open[i]) return(low[i]);
         return(close[i]);
   }
   return(0);
}
//+------------------------------------------------------------------+
