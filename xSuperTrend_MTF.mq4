/*------------------------------------------------------------------------------------
   Name: xSuperTrend MTF.mq4
   Copyright ©2011, Xaphod, http://wwww.xaphod.com

   Supertrend formula Copyright © Unknown. Someone on the Internets:
      UpperLevel=(High[i]+Low[i])/2+Multiplier*Atr(Period);
      LowerLevel=(High[i]+Low[i])/2-Multiplier*Atr(Period);

   Description: MTF SuperTrend Indicator.

   Change log:
       2011-12-18. Xaphod, v1.01
          - Removed dependancy on external indicator for iCustom calls
       2011-12-04. Xaphod, v1.00
          - First Release
-------------------------------------------------------------------------------------*/
// Indicator properties
#property copyright "Copyright © 2011, Xaphod"
#property link      "http://wwww.xaphod.com"

#property indicator_chart_window
#property indicator_buffers 3
#property indicator_color1 DimGray
#property indicator_color2 OrangeRed
#property indicator_color3 MediumSeaGreen
#property indicator_width1 1
#property indicator_width2 2
#property indicator_width3 2
#property indicator_style1 STYLE_DOT


// Constant definitions
#define INDICATOR_NAME "xSuperTrend MTF"
#define INDICATOR_VERSION "v1.01, [www.xaphod.com](http://www.xaphod.com)"

// Indicator parameters
extern string Version_Info=INDICATOR_VERSION;
extern string SuperTrend_Settings="——————————————————————————————";
extern int    SuperTrend_Period=10;      // SuperTrend ATR Period
extern double SuperTrend_Multiplier=1.7; // SuperTrend Multiplier
extern int    SuperTrend_TimeFrame=0;    // SuperTrend Timeframe
extern bool   SuperTrend_AutoTF=True;    // Select next higher TF. If TF=M15 then H1 is selected

extern string ATR_Filter_Settings="——————————————————————————————";
extern bool   UseStrengthFilter=True;    // ATR guc filtresi aktif/pasif
extern int    StrengthATR_Period=14;     // Filtre icin ATR periyodu
extern double MinATR_Pips=5.0;          // Sinyal icin minimum ATR (pip cinsinden)


// Global module varables
double gadUpBuf[];
double gadDnBuf[];
double gadSuperTrend[];
int giTimeFrame;
int giRepaintBars;
double gdPipSize;

//-----------------------------------------------------------------------------
// function: init()
// Description: Custom indicator initialization function.
//-----------------------------------------------------------------------------
int init() {
  // Set buffers
  SetIndexStyle(0, DRAW_LINE);
  SetIndexBuffer(0, gadSuperTrend);
  SetIndexLabel(0, "SuperTrend");
  SetIndexStyle(1, DRAW_LINE);
  SetIndexBuffer(1, gadDnBuf);
  SetIndexLabel(1, "SuperTrend Down");
  SetIndexStyle(2, DRAW_LINE);
  SetIndexBuffer(2, gadUpBuf);
  SetIndexLabel(2, "SuperTrend Up");

  // Pip size
  gdPipSize = (Digits == 5 || Digits == 3) ? Point * 10 : Point;

  // Set Timeframe
  if (SuperTrend_TimeFrame==0)
    SuperTrend_TimeFrame=Period();
  if (SuperTrend_AutoTF==True)
    SuperTrend_TimeFrame=NextHigherTF(Period());

  // Calculation call via iCustom
  if (SuperTrend_AutoTF==False && SuperTrend_Settings=="") {
    giRepaintBars=0;
  }
  // Higher Time-frame
  else if (SuperTrend_TimeFrame!=Period()) {
    IndicatorShortName(INDICATOR_NAME+" "+TF2Str(SuperTrend_TimeFrame) +"["+SuperTrend_Period+";"+DoubleToStr(SuperTrend_Multiplier,1)+"]");
    giRepaintBars=SuperTrend_TimeFrame/Period()*2+1;
  }
  // Current Time-frame
  else {
    IndicatorShortName(INDICATOR_NAME+" "+TF2Str(SuperTrend_TimeFrame) +"["+SuperTrend_Period+";"+DoubleToStr(SuperTrend_Multiplier,1)+"]");
    giRepaintBars=0;
  }

  return(0);
}


//-----------------------------------------------------------------------------
// function: deinit()
// Description: Custom indicator deinitialization function.
//-----------------------------------------------------------------------------
int deinit() {
   return (0);
}


///-----------------------------------------------------------------------------
// function: start()
// Description: Custom indicator iteration function.
//-----------------------------------------------------------------------------
int start() {
  int iNewBars, iCountedBars, i;
  double dAtr,dUpperLevel, dLowerLevel;

  // Get unprocessed ticks
  iCountedBars=IndicatorCounted();
  if(iCountedBars < 0) return (-1);
  if(iCountedBars>0) iCountedBars--;
  iNewBars=MathMax(giRepaintBars,Bars-iCountedBars);

  for(i=iNewBars; i>=0; i--) {
    // Calc SuperTrend Locally
    if (SuperTrend_TimeFrame==Period()) {
      dAtr = iATR(NULL, 0, SuperTrend_Period, i);
      dUpperLevel=(High[i]+Low[i])/2+SuperTrend_Multiplier*dAtr;
      dLowerLevel=(High[i]+Low[i])/2-SuperTrend_Multiplier*dAtr;

      // Set supertrend levels
      if (Close[i]>gadSuperTrend[i+1] && Close[i+1]<=gadSuperTrend[i+1]) {
        gadSuperTrend[i]=dLowerLevel;
      }
      else if (Close[i]<gadSuperTrend[i+1] && Close[i+1]>=gadSuperTrend[i+1]) {
        gadSuperTrend[i]=dUpperLevel;
      }
      else if (gadSuperTrend[i+1]<dLowerLevel)
         gadSuperTrend[i]=dLowerLevel;
      else if (gadSuperTrend[i+1]>dUpperLevel)
        gadSuperTrend[i]=dUpperLevel;
      else
        gadSuperTrend[i]=gadSuperTrend[i+1];

      // Draw Histo — ATR filtresi gecmeyince EMPTY_VALUE birak
      gadUpBuf[i]=EMPTY_VALUE;
      gadDnBuf[i]=EMPTY_VALUE;
      if (PassesStrengthFilter(i)) {
        if (Close[i]>gadSuperTrend[i] || (Close[i]==gadSuperTrend[i] && Close[i+1]>gadSuperTrend[i+1]))
          gadUpBuf[i]=gadSuperTrend[i];
        else if (Close[i]<gadSuperTrend[i] || (Close[i]==gadSuperTrend[i] && Close[i+1]<gadSuperTrend[i+1]))
          gadDnBuf[i]=gadSuperTrend[i];
      }
    }
    // Calc higher TF SuperTrend via iCustom
    else {
      gadUpBuf[i]=EMPTY_VALUE;
      gadDnBuf[i]=EMPTY_VALUE;
      gadSuperTrend[i]=iCustom(Symbol(),SuperTrend_TimeFrame,WindowExpertName(),"","",SuperTrend_Period,
                        SuperTrend_Multiplier,SuperTrend_TimeFrame,False,0,iBarShift(Symbol(), SuperTrend_TimeFrame, Time[i]));
      gadDnBuf[i]=iCustom(Symbol(),SuperTrend_TimeFrame,WindowExpertName(),"","",SuperTrend_Period,
                        SuperTrend_Multiplier,SuperTrend_TimeFrame,False,1,iBarShift(Symbol(), SuperTrend_TimeFrame, Time[i]));
      gadUpBuf[i]=iCustom(Symbol(),SuperTrend_TimeFrame,WindowExpertName(),"","",SuperTrend_Period,
                        SuperTrend_Multiplier,SuperTrend_TimeFrame,False,2,iBarShift(Symbol(), SuperTrend_TimeFrame, Time[i]));
    }
  }

  return(0);
}
//+------------------------------------------------------------------+


//-----------------------------------------------------------------------------
// function: PassesStrengthFilter()
// Description: ATR min esigini gecip gecmedigini kontrol eder.
//              UseStrengthFilter=False ise her zaman true doner.
//-----------------------------------------------------------------------------
bool PassesStrengthFilter(int i) {
  if (!UseStrengthFilter) return(true);
  double dFilterAtr = iATR(NULL, 0, StrengthATR_Period, i);
  return(dFilterAtr >= MinATR_Pips * gdPipSize);
}


//-----------------------------------------------------------------------------
// function: TF2Str()
// Description: Convert time-frame to a string
//-----------------------------------------------------------------------------
string TF2Str(int iPeriod) {
  switch(iPeriod) {
    case PERIOD_M1: return("M1");
    case PERIOD_M5: return("M5");
    case PERIOD_M15: return("M15");
    case PERIOD_M30: return("M30");
    case PERIOD_H1: return("H1");
    case PERIOD_H4: return("H4");
    case PERIOD_D1: return("D1");
    case PERIOD_W1: return("W1");
    case PERIOD_MN1: return("MN1");
    default: return("M"+iPeriod);
  }
}


//-----------------------------------------------------------------------------
// function: NextHigherTF()
// Description: Select the next higher time-frame.
//              Note: M15 and M30 both select H1 as next higher TF.
//-----------------------------------------------------------------------------
int NextHigherTF(int iPeriod) {
  if (iPeriod==0) iPeriod=Period();
  switch(iPeriod) {
    case PERIOD_M1: return(PERIOD_M5);
    case PERIOD_M5: return(PERIOD_M15);
    case PERIOD_M15: return(PERIOD_H1);
    case PERIOD_M30: return(PERIOD_H1);
    case PERIOD_H1: return(PERIOD_H4);
    case PERIOD_H4: return(PERIOD_D1);
    case PERIOD_D1: return(PERIOD_W1);
    case PERIOD_W1: return(PERIOD_MN1);
    case PERIOD_MN1: return(PERIOD_MN1);
    default: return(Period());
  }
}
