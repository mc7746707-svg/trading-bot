import asyncio
import requests
import pandas as pd
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ===== TELEGRAM =====
TOKEN = "8243137774:AAGhFsJPDmNv4z0WfahLauIcJ3b_kkgc_18"
CHAT ID = "6181352243"
# ===== PAIRS =====
PAIRS = [
    "EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X",
    "EURJPY=X","GBPJPY=X","EURGBP=X","AUDJPY=X"
]

running = False
mode = "REAL"

# ===== BUTTON UI =====
keyboard = [
    ["▶️ Start Real", "🟠 Start OTC"],
    ["⏸ Stop"],
    ["📊 Check Signal"]
]

reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ===== DATA =====
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

def ma(df):
    return df["close"].rolling(20).mean()

# ===== PATTERNS =====
def bullish_engulfing(df):
    return df["close"].iloc[-1] > df["open"].iloc[-1] and df["close"].iloc[-2] < df["open"].iloc[-2]

def bearish_engulfing(df):
    return df["close"].iloc[-1] < df["open"].iloc[-1] and df["close"].iloc[-2] > df["open"].iloc[-2]

def hammer(df):
    body = abs(df["close"].iloc[-1] - df["open"].iloc[-1])
    wick = df["open"].iloc[-1] - df["low"].iloc[-1]
    return wick > body * 2

# ===== FILTER =====
def strong_candle(df):
    body = abs(df["close"].iloc[-1] - df["open"].iloc[-1])
    avg = (df["high"] - df["low"]).mean()
    return body > avg * 0.5

# ===== SIGNAL =====
def check_signal(df):
    df["RSI"] = rsi(df)
    df["MA"] = ma(df)

    last_rsi = df["RSI"].iloc[-1]
    last_close = df["close"].iloc[-1]
    last_ma = df["MA"].iloc[-1]

    # BUY
    if (bullish_engulfing(df) or hammer(df)) and strong_candle(df):
        if last_rsi < 35 and last_close > last_ma:
            return "BUY 📈"

    # SELL
    if bearish_engulfing(df) and strong_candle(df):
        if last_rsi > 65 and last_close < last_ma:
            return "SELL 📉"

    return None

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bot Ready", reply_markup=reply_markup)

# ===== HANDLE =====
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global running, mode
    text = update.message.text

    if text == "▶️ Start Real":
        running = True
        mode = "REAL"
        await update.message.reply_text("📊 Real Market Started")

    elif text == "🟠 Start OTC":
        running = True
        mode = "OTC"
        await update.message.reply_text("🟠 OTC Mode Started (High Filter)")

    elif text == "⏸ Stop":
        running = False
        await update.message.reply_text("Stopped ❌")

    elif text == "📊 Check Signal":
        msg = "📊 Signals:\n\n"
        for pair in PAIRS:
            df = get_data(pair)
            signal = check_signal(df)
            if signal:
                msg += f"{pair} → {signal}\n"
        await update.message.reply_text(msg)

    # ===== AUTO LOOP =====
    while running:
        for pair in PAIRS:
            df = get_data(pair)
            signal = check_signal(df)

            # OTC extra filter
            if mode == "OTC":
                if not strong_candle(df):
                    continue

            if signal:
                time_now = datetime.now().strftime("%H:%M:%S")

                msg = f"""
🔥 {mode} SIGNAL 🔥
Pair: {pair}
Signal: {signal}
Entry: {time_now} (IST)
Expiry: 1 Min
                """

                await update.message.reply_text(msg)

        await asyncio.sleep(60)

# ===== MAIN =====
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT, handle))

print("Bot Running...")
app.run_polling() 
    
