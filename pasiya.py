# auto_trader_bot_notify.py
"""
Auto-trader (multi-symbol) with Telegram notifications:
- Sends start message with account wallet snapshot.
- Sends before-each-trade wallet snapshot & short details.
- Sends per-trade result messages.
- Sends profit updates and final "daily target complete" message.
Tagline used in messages: "POWERED_BUY PASIYA-MD FOREX AUTO TRADING BOT"
IMPORTANT: Test on DEMO first.
"""

import time
import threading
from datetime import datetime, timezone
import MetaTrader5 as mt5
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes

# ========== CONFIG ==========
MT5_LOGIN = 265337487                # <-- set
MT5_PASSWORD = "Sampath123$#@"  # <-- set
MT5_SERVER = "Exness-MT5Real38"      # <-- set

TELEGRAM_TOKEN = "7786434709:AAE29u264oOFf9qH0oBSmjfTKQLSlUu_TUo"  # <-- set
ADMINS = {94784548818}                     # <-- admin(s) numeric id(s)

SYMBOLS = ["XAUUSD", "BTCUSD", "EURUSD"]
MIN_LOT = 0.01
RISK_PERCENT = 0.0001         # 0.0001% requested (very small)
STOP_LOSS_PIPS = {"XAUUSD": 50, "BTCUSD": 100, "EURUSD": 20}
TAKE_PROFIT_PIPS = {"XAUUSD": 100, "BTCUSD": 200, "EURUSD": 20}
CHECK_INTERVAL = 30
DAILY_PROFIT_TARGET = 500000.0
MAGIC = 20250918
ORDER_DEVIATION = 50
# ============================

bot = Bot(token=TELEGRAM_TOKEN)
running = False
mode = None  # "safe" or "unlimited"
start_balance = None
lock = threading.Lock()


# ---------- Helpers & MT5 ----------
def is_admin(user_id: int) -> bool:
    return user_id in ADMINS

def init_mt5():
    mt5.shutdown()
    ok = mt5.initialize()
    if not ok:
        return False, "MT5 initialize() failed"
    login_ok = mt5.login(MT5_LOGIN, MT5_PASSWORD, MT5_SERVER)
    if not login_ok:
        return False, "MT5 login failed"
    return True, "MT5 connected"

def get_account_info_dict():
    acc = mt5.account_info()
    if not acc:
        return {}
    return {
        "login": getattr(acc, "login", None),
        "balance": float(getattr(acc, "balance", 0.0)),
        "equity": float(getattr(acc, "equity", 0.0)),
        "margin": float(getattr(acc, "margin", 0.0)),
        "free_margin": float(getattr(acc, "margin_free", 0.0)),
        "leverage": getattr(acc, "leverage", None),
        "currency": getattr(acc, "currency", "USD"),
    }

def format_wallet_snapshot():
    info = get_account_info_dict()
    if not info:
        return "Account info unavailable"
    return (
        f"Wallet Snapshot:\n"
        f"Login: {info['login']}\n"
        f"Balance: ${info['balance']:.2f}\n"
        f"Equity: ${info['equity']:.2f}\n"
        f"Margin: ${info['margin']:.2f}\n"
        f"Free Margin: ${info['free_margin']:.2f}\n"
        f"Leverage: {info['leverage']}\n"
    )

def get_today_profit():
    global start_balance
    acc = mt5.account_info()
    if not acc or start_balance is None:
        return 0.0
    return round(float(acc.balance) - float(start_balance), 2)

def ensure_symbol(symbol):
    si = mt5.symbol_info(symbol)
    if si is None:
        return False
    if not si.visible:
        mt5.symbol_select(symbol, True)
    return True

def compute_lot(symbol, stop_loss_pips, risk_percent):
    balance = float(getattr(mt5.account_info(), "balance", 0.0))
    risk_fraction = (risk_percent / 100.0)
    risk_amount = balance * risk_fraction
    si = mt5.symbol_info(symbol)
    if si is None:
        return MIN_LOT
    # conservative pip value fallback
    if symbol == "EURUSD":
        pip_value_1lot = 10.0
    elif symbol == "XAUUSD":
        pip_value_1lot = 100.0
    elif symbol == "BTCUSD":
        pip_value_1lot = 1000.0
    else:
        pip_value_1lot = 10.0
    pip_value_0_01 = pip_value_1lot * 0.01
    denom = stop_loss_pips * pip_value_0_01
    if denom <= 0 or risk_amount <= 0:
        return MIN_LOT
    lot = round(risk_amount / denom, 2)
    if lot < MIN_LOT:
        return MIN_LOT
    return lot

def place_market_order(symbol, side, lot, sl_pips=None, tp_pips=None):
    if not ensure_symbol(symbol):
        return False, "Symbol not available"
    tick = mt5.symbol_info_tick(symbol)
    si = mt5.symbol_info(symbol)
    if tick is None or si is None:
        return False, "No tick/symbol info"
    price = tick.ask if side == "buy" else tick.bid
    point = si.point
    sl = price - sl_pips * point if (sl_pips and side == "buy") else (price + sl_pips * point if (sl_pips and side == "sell") else None)
    tp = price + tp_pips * point if (tp_pips and side == "buy") else (price - tp_pips * point if (tp_pips and side == "sell") else None)
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": float(lot),
        "type": mt5.ORDER_TYPE_BUY if side == "buy" else mt5.ORDER_TYPE_SELL,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": ORDER_DEVIATION,
        "magic": MAGIC,
        "comment": f"AutoTrade {side}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    res = mt5.order_send(request)
    if res is None:
        return False, "Order_send returned None"
    if hasattr(res, "retcode") and res.retcode == mt5.TRADE_RETCODE_DONE:
        return True, f"Order executed: {side} {symbol} lot={lot} price={price:.5f}"
    else:
        err = getattr(res, "comment", str(res))
        return False, f"Order failed: {err}"

# ---------- Simple signal ----------
def simple_signal(symbol):
    TF = mt5.TIMEFRAME_M5
    rates = mt5.copy_rates_from_pos(symbol, TF, 0, 100)
    if rates is None or len(rates) < 30:
        return None
    closes = [r.close for r in rates]
    sma5 = sum(closes[-5:]) / 5
    sma20 = sum(closes[-20:]) / 20
    if sma5 > sma20:
        return "buy"
    elif sma5 < sma20:
        return "sell"
    return None

# ---------- Workers ----------
def trade_worker(mode_local):
    admin_id = list(ADMINS)[0]
    bot.send_message(chat_id=admin_id, text=f"POWERED_BUY PASIYA-MD FOREX AUTO TRADING BOT ON\nMode: {mode_local}\n{format_wallet_snapshot()}")
    while running and mode == mode_local:
        for sym in SYMBOLS:
            if not running or mode != mode_local:
                break
            try:
                # send pre-trade wallet snapshot & short details
                snapshot = format_wallet_snapshot()
                bot.send_message(chat_id=admin_id, text=f"Pre-Trade Snapshot for {sym}:\n{snapshot}\nSymbol: {sym}\nRisk%: {RISK_PERCENT}%")
                sig = simple_signal(sym)
                if sig:
                    sl = STOP_LOSS_PIPS.get(sym, 20)
                    tp = TAKE_PROFIT_PIPS.get(sym, 20)
                    lot = compute_lot(sym, sl, RISK_PERCENT)
                    # quick trade summary before sending order
                    bot.send_message(chat_id=admin_id, text=f"Placing {sig.upper()} {sym} | Lot: {lot} | SL:{sl} pips | TP:{tp} pips")
                    ok, msg = place_market_order(sym, sig, lot, sl_pips=sl, tp_pips=tp)
                    bot.send_message(chat_id=admin_id, text=f"{msg}")
                    # Profit update after order
                    profit = get_today_profit()
                    bot.send_message(chat_id=admin_id, text=f"📊 Current Profit: ${profit:.2f}")
                    # check daily target
                    if profit >= DAILY_PROFIT_TARGET:
                        bot.send_message(chat_id=admin_id, text=(
                            f"💰 DAILY TARGET REACHED: ${profit:.2f}\n"
                            "DAILY TARGET COMPLETE\n"
                            "POWERED_BUY PASIYA-MD FOREX AUTO TRADING BOT"
                        ))
                        # stop bot
                        with lock:
                            global running, mode
                            running = False
                            mode = None
                        break
                else:
                    # no signal: send short note (optional, can be commented out)
                    bot.send_message(chat_id=admin_id, text=f"{sym}: No trade signal at this time.")
                time.sleep(CHECK_INTERVAL)
            except Exception as e:
                bot.send_message(chat_id=admin_id, text=f"⚠️ Error in worker for {sym}: {e}")
                time.sleep(5)
    bot.send_message(chat_id=admin_id, text=f"POWERED_BUY PASIYA-MD FOREX AUTO TRADING BOT STOPPED\nMode was: {mode_local}")

# ---------- Telegram handlers ----------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid):
        return
    await update.message.reply_text("👋 Bot alive. Use /safe or /unlimited to start.")

async def cmd_safe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global running, mode, start_balance
    uid = update.effective_user.id
    if not is_admin(uid):
        return
    with lock:
        if running:
            await update.message.reply_text("⚠️ Bot already running.")
            return
        ok, msg = init_mt5()
        if not ok:
            await update.message.reply_text(f"MT5 connect failed: {msg}")
            return
        start_balance = float(getattr(mt5.account_info(), "balance", 0.0))
        running = True
        mode = "safe"
        admin_id = list(ADMINS)[0]
        bot.send_message(chat_id=admin_id, text=f"POWERED_BUY PASIYA-MD FOREX AUTO TRADING BOT ON\nMode: SAFE\n{format_wallet_snapshot()}")
        t = threading.Thread(target=trade_worker, args=("safe",), daemon=True)
        t.start()
        await update.message.reply_text("Safe mode started.")

async def cmd_unlimited(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global running, mode, start_balance
    uid = update.effective_user.id
    if not is_admin(uid):
        return
    with lock:
        if running:
            await update.message.reply_text("⚠️ Bot already running.")
            return
        ok, msg = init_mt5()
        if not ok:
            await update.message.reply_text(f"MT5 connect failed: {msg}")
            return
        start_balance = float(getattr(mt5.account_info(), "balance", 0.0))
        running = True
        mode = "unlimited"
        admin_id = list(ADMINS)[0]
        bot.send_message(chat_id=admin_id, text=f"POWERED_BUY PASIYA-MD FOREX AUTO TRADING BOT ON\nMode: UNLIMITED\n{format_wallet_snapshot()}")
        t = threading.Thread(target=trade_worker, args=("unlimited",), daemon=True)
        t.start()
        await update.message.reply_text("Unlimited mode started.")

async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global running, mode
    uid = update.effective_user.id
    if not is_admin(uid):
        return
    with lock:
        running = False
        old_mode = mode
        mode = None
        admin_id = list(ADMINS)[0]
        bot.send_message(chat_id=admin_id, text=(
            f"POWERED_BUY PASIYA-MD FOREX AUTO TRADING BOT STOPPED\nStopped by admin.\n{format_wallet_snapshot()}\nMode was: {old_mode}"
        ))
    await update.message.reply_text("Bot stopped.")

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid):
        return
    profit = get_today_profit()
    await update.message.reply_text(
        f"Mode: {mode}\nRunning: {running}\nStartBalance: {start_balance}\nCurrentProfit: ${profit:.2f}"
    )

# ---------- Main ----------
def main():
    # attempt initial MT5 connect so account info can be used (optional)
    ok, msg = init_mt5()
    admin_id = list(ADMINS)[0]
    if ok:
        try:
            bot.send_message(chat_id=admin_id, text=f"Script started. {format_wallet_snapshot()}")
        except Exception:
            pass
    else:
        print("MT5 init failed:", msg)

    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("safe", cmd_safe))
    app.add_handler(CommandHandler("unlimited", cmd_unlimited))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CommandHandler("status", cmd_status))

    print("Bot polling (CTRL+C to exit)...")
    app.run_polling()

if __name__ == "__main__":
    main()
