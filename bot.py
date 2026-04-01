import time
import requests
import pandas as pd
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ===== TELEGRAM =====
TOKEN = "8243137774:AAFPyFcalKy1hdQ3ir9pE-R-8XN7WfGR_Nw"
CHAT_ID = "6181352243"

# ===== PAIRS =====
PAIRS = [
    "EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X",
    "EURJPY=X","GBPJPY=X","EURGBP=X","AUDJPY=X"
]

running = False

keyboard = [
    ["▶️ Start Scan", "⏸ Stop Scan"],
    ["📊 Check Signal"]
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

# ===== CANDLE PATTERNS =====

def bullish_engulfing(df):
    return df["close"].iloc[-1] > df["open"].iloc[-1] and df["close"].iloc[-2] < df["open"].iloc[-2]

def bearish_engulfing(df):
    return df["close"].iloc[-1] < df["open"].iloc[-1] and df["close"].iloc[-2] > df["open"].iloc[-2]

def hammer(df):
    body = abs(df["close"].iloc[-1] - df["open"].iloc[-1])
    lower_wick = df["open"].iloc[-1] - df["low"].iloc[-1]
    return lower_wick > body * 2

def shooting_star(df):
    body = abs(df["close"].iloc[-1] - df["open"].iloc[-1])
    upper_wick = df["high"].iloc[-1] - df["close"].iloc[-1]
    return upper_wick > body * 2

def doji(df):
    return abs(df["close"].iloc[-1] - df["open"].iloc[-1]) < 0.0002

# ===== SIGNAL LOGIC =====
def check_signal(pair):
    df = get_data(pair)
    
    if bullish_engulfing(df) or hammer(df):
        return "BUY 📈"
    
    elif bearish_engulfing(df) or shooting_star(df):
        return "SELL 📉"
    
    elif doji(df):
        return "WAIT ⚠️"
    
    return None

# ===== BOT START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot Ready 🔥", reply_markup=reply_markup)

# ===== HANDLE BUTTON =====
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global running
    text = update.message.text

    if text == "▶️ Start Scan":
        running = True
        await update.message.reply_text("Scanning Started 🔥")

        while running:
            for pair in PAIRS:
                signal = check_signal(pair)

                if signal:
                    time_now = datetime.now().strftime("%H:%M:%S")
                    
                    msg = f"""
🔥 SIGNAL ALERT 🔥

Pair: {pair}
Signal: {signal}
Time: {time_now} (India)

Expiry: 1 Min ⏳
                    """

                    await update.message.reply_text(msg)

            await asyncio.sleep(60)

    elif text == "⏸ Stop Scan":
        running = False
        await update.message.reply_text("Scanning Stopped ❌")

    elif text == "📊 Check Signal":
        msg = "📊 Current Signals:\n\n"
        
        for pair in PAIRS:
            signal = check_signal(pair)
            if signal:
                msg += f"{pair} → {signal}\n"
        
        await update.message.reply_text(msg)

# ===== MAIN =====
import asyncio

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT, handle))

print("Bot Running...")
app.run_polling()
