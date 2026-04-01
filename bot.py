    import asyncio
import requests
import pandas as pd
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ===== TELEGRAM =====
TOKEN = "8243137774:AAGhFsJPDmNv4z0WfahLauIcJ3b_kkgc_18"
CHAT_ID = "6181352243"
# ===== PAIRS =====
PAIRS = [
    "EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X",
    "EURJPY=X","GBPJPY=X","EURGBP=X","AUDJPY=X"
]

running = False

# ===== BUTTONS =====
keyboard = [
    ["▶ Start Scan", "⏹ Stop"],
    ["📊 Signal"]
]
reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ===== DATA FETCH =====
def get_data(pair):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{pair}?interval=1m&range=1d"
    data = requests.get(url).json()

    candles = data["chart"]["result"][0]["indicators"]["quote"][0]

    df = pd.DataFrame({
        "open": candles["open"],
        "close": candles["close"],
        "high": candles["high"],
        "low": candles["low"]
    })

    return df.dropna()

# ===== INDICATORS =====
def rsi(df, period=14):
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def ma(df, period=20):
    return df["close"].rolling(period).mean()

# ===== PATTERN =====
def bullish_engulfing(df):
    return (
        df["close"].iloc[-2] < df["open"].iloc[-2] and
        df["close"].iloc[-1] > df["open"].iloc[-1] and
        df["close"].iloc[-1] > df["open"].iloc[-2]
    )

def bearish_engulfing(df):
    return (
        df["close"].iloc[-2] > df["open"].iloc[-2] and
        df["close"].iloc[-1] < df["open"].iloc[-1] and
        df["close"].iloc[-1] < df["open"].iloc[-2]
    )

# ===== SIGNAL =====
def get_signal(df):
    df["RSI"] = rsi(df)
    df["MA"] = ma(df)

    if bullish_engulfing(df) and df["RSI"].iloc[-1] < 30:
        return "BUY"
    elif bearish_engulfing(df) and df["RSI"].iloc[-1] > 70:
        return "SELL"
    return None

# ===== SCAN =====
async def scan(update):
    global running
    while running:
        for pair in PAIRS:
            try:
                df = get_data(pair)
                signal = get_signal(df)

                if signal:
                    time_now = datetime.now().strftime("%H:%M:%S")

                    msg = f"""
🔥 SIGNAL ALERT

Pair: {pair.replace('=X','')}
Signal: {signal}
Time (India): {time_now}
Expiry: 1 min
"""
                    await update.message.reply_text(msg)

            except:
                pass

        await asyncio.sleep(60)

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot Started ✅", reply_markup=reply_markup)

# ===== HANDLE BUTTON =====
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global running
    text = update.message.text

    if text == "▶ Start Scan":
        running = True
        await update.message.reply_text("Scanning started 🔍")
        asyncio.create_task(scan(update))

    elif text == "⏹ Stop":
        running = False
        await update.message.reply_text("Stopped ❌")

    elif text == "📊 Signal":
        for pair in PAIRS:
            try:
                df = get_data(pair)
                signal = get_signal(df)

                if signal:
                    time_now = datetime.now().strftime("%H:%M:%S")

                    msg = f"""
📊 QUICK SIGNAL

Pair: {pair.replace('=X','')}
Signal: {signal}
Time: {time_now}
"""
                    await update.message.reply_text(msg)
                    return
            except:
                pass

        await update.message.reply_text("No signal ❌")

# ===== MAIN =====
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, handle))

    print("Bot Running...")

    app.run_polling()
