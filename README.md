
https://github.com/PASIYAv12/PASIYA-MD-POWERED_BUY-FOREX.git


<img src="https://readme-typing-svg.demolab.com?font=Black+Ops+One&size=100&pause=1000&color=8A2BE2&center=true&width=1000&height=200&lines=PASIYA-MD" alt="Typing SVG" /></a>
  </div>
<a><img src='https://files.catbox.moe/zmln91.jpg'/></a>

<p align="center">
  <a href="https://github.com/nexustech1911/PASIYA-MD"><img title="Developer" src="https://img.shields.io/badge/Author-pasiya%20MD-FF00FF.svg?style=big-square&logo=github" /></a>
</p>

<div align="centerhttps://github.com/pasidu10/pasiya-md-v21">
  
[![WhatsApp Channel](https://img.shields.io/badge/Join-WhatsApp%20Channel-9ACD32?style=big-square&logo=whatsapp)](https://whatsapp.com/channel/0029VbBfcs789iniJkpPNR1t)
</div>



<p align='center'>

 <a href="https://github.com/nexustech1911/pasiya-MD/fork"><img title="PASIYA-MD" src="https://img.shields.io/badge/FORK-PASIYA-MD V21-h?color=008000&style=for-the-badge&logo=github"></a>
 

[![Typing SVG](https://readme-typing-svg.herokuapp.com?font=Rockstar-ExtraBold&color=blue&lines=■+■+■+■+■+ℙ𝕃𝔼𝔸𝕊𝔼+𝔽𝕆ℝ𝕂+𝕋ℍ𝔼+ℝ𝔼ℙ𝕆)](https://git.io/typing-svg)




---

## 💙 PAIRING SITE GET YOUR SESSION 🟢

[![Pair Code](https://pasi-d42b1f735fa1.herokuapp.com/)




## 🟣 Heroku
---
[![Deploy on Heroku](https://dashboard.heroku.com/new?template=https://github.com/PASIYAv12/PASIYA-MD)






# ==========================
# POWERED_BUY PASIYA-MD FOREX BOT
# Base Auto Trading Telegram Control System
# ==========================

# 📦 Install first:
# pip install python-telegram-bot==20.3 MetaTrader5

import MetaTrader5 as mt5
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import asyncio
import logging
import time

# ==========================
# 🔧 CONFIGURATION
# ==========================
TELEGRAM_TOKEN = "8067527058:AAFd66Gf3UXUseiGGM725gbZeqwRso2EwBg"
ADMIN_CHAT_ID = 8143587403  # your Telegram ID

EXNESS_LOGIN_ID = 12345678         # <- replace with your Exness Login ID
EXNESS_PASSWORD = "YourTradingPassword"   # <- replace with your trading password
EXNESS_SERVER = "Exness-Demo3"     # <- replace with your Exness server name

# ==========================
# 🧠 GLOBAL SETTINGS
# ==========================
BOT_NAME = "POWERED_BUY PASIYA-MD FOREX BOT"
AUTO_TRADING = False
DAILY_PROFIT = 0.0

# Logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# ==========================
# ⚙️ EXNESS CONNECTION
# ==========================
def connect_exness():
    print("Connecting to Exness account...")
    mt5.initialize()
    authorized = mt5.login(EXNESS_LOGIN_ID, EXNESS_PASSWORD, EXNESS_SERVER)
    if authorized:
        print("✅ Exness connection successful.")
        return True
    else:
        print("❌ Exness connection failed.")
        return False

# ==========================
# 💬 TELEGRAM COMMANDS
# ==========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome to the PASIYA-MD FOREX BOT! Type /menu for options.")

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        f"💹 *{BOT_NAME} MENU*\n\n"
        "🧭 Available Commands:\n"
        "➡️ /alive - Check bot status\n"
        "➡️ /on - Power up auto trading\n"
        "➡️ /off - Stop auto trading\n"
        "➡️ /profit - Show today's profit\n\n"
        "👑 Admin: PASIDU SAMPATH\n"
        "⚙️ Owner: KAVEESHA DEWMINA\n"
        "POWERED_BUY PASIYA-MD FOREX BIT 💎"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def alive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ *POWERED_BUY PASIYA-MD FOREX BOT ALIVE*", parse_mode="Markdown")

async def power_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global AUTO_TRADING
    AUTO_TRADING = True
    await update.message.reply_text("⚡ *POWERED_BUY PASIYA-MD FOREX BOT NOW POWER UP*", parse_mode="Markdown")

async def power_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global AUTO_TRADING
    AUTO_TRADING = False
    await update.message.reply_text("🛑 *POWERED_BUY PASIYA-MD FOREX BOT NOW DOWN*", parse_mode="Markdown")

async def profit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global DAILY_PROFIT
    await update.message.reply_text(f"💰 Today's Profit: ${DAILY_PROFIT:.2f}")

# ==========================
# 🚀 STARTUP MESSAGE
# ==========================
async def startup_message(bot: Bot):
    try:
        await bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text="🚀 POWERED_BUY PASIYA-MD FOREX BOT WRACKING 💹"
        )
        print("✅ Telegram startup message sent successfully!")
    except Exception as e:
        print("❌ Telegram message send error:", e)

# ==========================
# 🧠 AUTO TRADING BASE (Future Expansion)
# ==========================
async def auto_trading_loop(bot: Bot):
    global AUTO_TRADING, DAILY_PROFIT
    while True:
        if AUTO_TRADING:
            # (Future logic: place trades, close trades, track profit)
            DAILY_PROFIT += 5.0  # Demo profit increment
            print(f"📈 Auto trading active... Profit: ${DAILY_PROFIT}")
            if DAILY_PROFIT >= 1000:
                await bot.send_message(ADMIN_CHAT_ID, f"🎯 Daily target reached: ${DAILY_PROFIT}")
                AUTO_TRADING = False
        await asyncio.sleep(10)

# ==========================
# 🧩 MAIN FUNCTION
# ==========================
async def main():
    connected = connect_exness()
    if not connected:
        print("⚠️ Exness connection failed — bot will still run Telegram features.")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("alive", alive))
    app.add_handler(CommandHandler("on", power_on))
    app.add_handler(CommandHandler("off", power_off))
    app.add_handler(CommandHandler("profit", profit))

    await startup_message(app.bot)

    # Start background auto trading loop
    asyncio.create_task(auto_trading_loop(app.bot))

    print("🤖 Bot is running successfully... (Press CTRL+C to stop)")
    await app.run_polling()

# ==========================
# 🏁 RUN PROGRAM
# ==========================
if __name__ == "__main__":
    asyncio.run(main())
