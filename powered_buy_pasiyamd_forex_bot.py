# powered_buy_pasiyamd_forex_bot.py
# Python 3.10+
# Usage: python powered_buy_pasiyamd_forex_bot.py

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

from telegram import Update, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

# ========== CONFIG ==========
TELEGRAM_BOT_TOKEN = "8067527058:AAFd66Gf3UXUseiGGM725gbZeqwRso2EwBg"  # you provided; consider regenerating
ADMIN_PHONE = "+94784548818"   # display to users, not used for auth
ADMIN_TELEGRAM_ID = 8143587403  # you gave chat id

# Replace with your broker integration settings (MT5 / MetaApi / broker REST)
BROKER_USE_METAAPI = True
METAAPI_TOKEN = "<YOUR_METAAPI_TOKEN>"  # example placeholder
DEMO_ACCOUNT_ID = "<YOUR_DEMO_ACCOUNT_ID>"

# Trading settings (example placeholders)
TRADE_SYMBOL = "EURUSD"
TRADE_VOLUME = 0.01
DAILY_PROFIT_TARGET_USD = 1000000  # user requested unrealistic target; keep for config

# ========== STATE (in-memory; persist to DB in prod) ==========
STATE = {
    "auto_trading": False,
    "last_daily_profit_usd": 0.0,
    "wallet_balance_usd": 0.0,
    "trade_history": [],  # list of dicts
}

# ========== LOGGING ==========
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("powered_buy_bot")

# ========== HELPERS ==========
async def send_admin_message(app, text: str):
    try:
        await app.bot.send_message(chat_id=ADMIN_TELEGRAM_ID, text=text)
    except Exception as e:
        logger.exception("Failed to message admin: %s", e)

def format_main_menu():
    return (
        "POWERED_BUY  PASIYA-MD  FOREX BIT  MENU\n\n"
        "Commands:\n"
        "/menu - Show this menu\n"
        "/alive - Check bot alive\n"
        "/on - Power UP auto trading\n"
        "/of - Power DOWN auto trading\n"
        "/status - Wallet & daily profit\n\n"
        "Admin Contact: " + ADMIN_PHONE
    )

# Simulated broker interface (replace with MetaApi or MT5 calls)
class BrokerClient:
    def __init__(self):
        # init real connection here (MetaApi/MT5/REST)
        pass

    async def connect(self):
        # connect to broker / stream
        logger.info("Broker client connected (simulated).")

    async def get_balance(self) -> float:
        # replace with real API call
        return STATE["wallet_balance_usd"]

    async def place_order(self, symbol: str, volume: float, side: str) -> Dict[str, Any]:
        # side = "buy" or "sell"
        # perform order on broker and return order object
        order = {
            "id": f"sim-{int(datetime.now().timestamp())}",
            "symbol": symbol,
            "volume": volume,
            "side": side,
            "price": 1.0,  # simulated
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pnl": 0.0
        }
        # store trade
        STATE["trade_history"].append(order)
        logger.info("Placed simulated order: %s", order)
        return order

    async def subscribe_market_stream(self, on_tick_callback):
        # in real mode, use websocket or streaming API to call on_tick_callback
        # Here we simulate periodic ticks
        async def _sim_loop():
            while True:
                tick = {
                    "symbol": TRADE_SYMBOL,
                    "bid": 1.1000,
                    "ask": 1.1002,
                    "time": datetime.now(timezone.utc).isoformat()
                }
                await on_tick_callback(tick)
                await asyncio.sleep(10)  # simulated tick every 10s
        asyncio.create_task(_sim_loop())

# ========== BOT COMMAND HANDLERS ==========
async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(format_main_menu())

async def cmd_alive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("POWERED_BUY  PASIYA-MD  FOREX BOT ALIVE")

async def cmd_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    STATE["auto_trading"] = True
    await update.message.reply_text("POWERED_BUY  PASIYA-MD   FOREX BOT NOW POWER UP")
    await send_admin_message(context.application, f"Auto-trading ENABLED by user {update.effective_user.id}")

async def cmd_of(update: Update, context: ContextTypes.DEFAULT_TYPE):
    STATE["auto_trading"] = False
    await update.message.reply_text("POWERED_BUY  PASIYA-MD  FOREX BOT NOW DAWUN")
    await send_admin_message(context.application, f"Auto-trading DISABLED by user {update.effective_user.id}")

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    balance = await broker.get_balance()
    last_profit = STATE["last_daily_profit_usd"]
    text = (
        f"POWERED_BUY  PASIYA-MD  WALLET REPORT\n\n"
        f"Balance: ${balance:.2f}\n"
        f"Today's Profit: ${last_profit:.2f}\n"
        f"Auto-trading: {'ON' if STATE['auto_trading'] else 'OFF'}\n"
    )
    await update.message.reply_text(text)

# Admin-only command example (start a demo trade)
async def cmd_demo_trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_TELEGRAM_ID:
        await update.message.reply_text("Not authorized.")
        return
    # place a simulated buy
    order = await broker.place_order(TRADE_SYMBOL, TRADE_VOLUME, "buy")
    await update.message.reply_text(f"Demo order placed: {order['id']} {order['symbol']}")

# ========== MARKET HANDLERS / STRATEGY ==========
async def on_market_tick(tick):
    # tick: {"symbol","bid","ask","time"}
    logger.debug("Tick: %s", tick)
    # simple example strategy (demo): if auto_trading ON, place a buy every N ticks (for demo only)
    if STATE["auto_trading"]:
        # Very simple rule for demo — DO NOT USE IN PRODUCTION
        now = datetime.now(timezone.utc)
        if now.second % 30 == 0:  # every 30s approximately, simulated
            order = await broker.place_order(tick["symbol"], TRADE_VOLUME, "buy")
            # Immediately notify admin + channel
            msg = (
                f"TRADE EXECUTED\n"
                f"Symbol: {order['symbol']}\n"
                f"Volume: {order['volume']}\n"
                f"OrderID: {order['id']}\n"
                f"Time: {order['timestamp']}"
            )
            await send_admin_message(app, msg)

# ========== NEWS ALERTS (example hook) ==========
async def publish_news_alert(title: str, body: str):
    text = f"MARKET NEWS: {title}\n\n{body}"
    try:
        # broadcast to admin & optionally a channel
        await send_admin_message(app, text)
    except Exception as e:
        logger.exception("Failed to send news alert: %s", e)

# ========== STARTUP / MAIN ==========
broker = BrokerClient()
app = None  # will be set in main

async def main():
    global app
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # commands
    app.add_handler(CommandHandler("menu", cmd_menu))
    app.add_handler(CommandHandler("alive", cmd_alive))
    app.add_handler(CommandHandler("on", cmd_on))
    app.add_handler(CommandHandler("of", cmd_of))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("demo_trade", cmd_demo_trade))

    # set bot commands for UI
    try:
        await app.bot.set_my_commands([
            BotCommand("menu", "Show menu"),
            BotCommand("alive", "Bot alive check"),
            BotCommand("on", "Turn auto trading ON"),
            BotCommand("of", "Turn auto trading OFF"),
            BotCommand("status", "Show wallet & daily profit"),
        ])
    except Exception:
        pass

    # connect to broker & start market stream
    await broker.connect()
    await broker.subscribe_market_stream(on_market_tick)

    # start polling (telegram)
    logger.info("Starting Telegram polling...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    # keep running
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
