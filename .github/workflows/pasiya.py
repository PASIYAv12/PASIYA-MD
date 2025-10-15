//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
  {
   Print("SMA Crossover EA started");
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
  }

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
  {
   // Parameters
   int fastSMA_period = 10;  // සුළු SMA
   int slowSMA_period = 30;  // දිගු SMA

   // Calculate SMAs
   double fastSMA = iMA(_Symbol, PERIOD_CURRENT, fastSMA_period, 0, MODE_SMA, PRICE_CLOSE, 0);
   double slowSMA = iMA(_Symbol, PERIOD_CURRENT, slowSMA_period, 0, MODE_SMA, PRICE_CLOSE, 0);
   double prevFastSMA = iMA(_Symbol, PERIOD_CURRENT, fastSMA_period, 0, MODE_SMA, PRICE_CLOSE, 1);
   double prevSlowSMA = iMA(_Symbol, PERIOD_CURRENT, slowSMA_period, 0, MODE_SMA, PRICE_CLOSE, 1);

   // Check for crossover
   if(prevFastSMA < prevSlowSMA && fastSMA > slowSMA)
     {
      // Golden cross - buy signal
      if(PositionSelect(_Symbol)==false)
        {
         // Open buy order
         tradeBuy();
        }
     }
   else if(prevFastSMA > prevSlowSMA && fastSMA < slowSMA)
     {
      // Death cross - sell signal
      if(PositionSelect(_Symbol)==false)
        {
         // Open sell order
         tradeSell();
        }
     }
  }

//+------------------------------------------------------------------+
//| Function to place buy order                                        |
//+------------------------------------------------------------------+
void tradeBuy()
  {
   MqlTradeRequest request;
   MqlTradeResult result;

   request.action = TRADE_ACTION_DEAL;
   request.symbol = _Symbol;
   request.volume = 0.1; // Lot size
   request.type = ORDER_TYPE_BUY;
   request.price = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   request.deviation = 10;

   if(!OrderSend(request,result))
     {
      Print("Trade buy failed: ", GetLastError());
     }
   else
     {
      Print("Buy order placed");
     }
  }

//+------------------------------------------------------------------+
//| Function to place sell order                                       |
//+------------------------------------------------------------------+
void tradeSell()
  {
   MqlTradeRequest request;
   MqlTradeResult result;

   request.action = TRADE_ACTION_DEAL;
   request.symbol = _Symbol;
   request.volume = 0.1; // Lot size
   request.type = ORDER_TYPE_SELL;
   request.price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   request.deviation = 10;

   if(!OrderSend(request,result))
     {
      Print("Trade sell failed: ", GetLastError());
     }
   else
     {
      Print("Sell order placed");
     }
  }
