import requests
import pandas as pd
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ===== TELEGRAM =====
TOKEN = "8243137774:AAHCKkESoXOT-Fy0_8hpkAExeiqFzNOc1MQ"
CHAT_ID = "6181352243"
# ===== PAIRS =====
PAIRS = [
    "EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X",
    "EURJPY=X", "GBPJPY=X", "EURGBP=X", "AUDJPY=X"
]

# ===== KEYBOARD =====
keyboard = [
    ["▶ Start Scan", "⏹ Stop"],
    ["📊 Strong Signal"]
]

reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

running = False

# ===== DATA =====
def get_data(pair):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{pair}?interval=1m&range=1d"
        res = requests.get(url, timeout=10)

        if res.status_code != 200:
            return None

        data = res.json()

        if not data.get("chart") or not data["chart"].get("result"):
            return None

        candles = data["chart"]["result"][0]["indicators"]["quote"][0]

        df = pd.DataFrame({
            "open": candles["open"],
            "close": candles["close"],
            "high": candles["high"],
            "low": candles["low"]
        })

        return df.dropna()

    except:
        return None

# ===== RSI =====
def rsi(df, period=14):
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# ===== SUPPORT / RESISTANCE =====
def support_resistance(df):
    df["support"] = df["low"].rolling(20).min()
    df["resistance"] = df["high"].rolling(20).max()
    return df

# ===== CANDLE PATTERNS =====
def bullish_engulfing(df):
    return (
        df["close"].iloc[-2] < df["open"].iloc[-2] and
        df["close"].iloc[-1] > df["open"].iloc[-1] and
        df["close"].iloc[-1] > df["open"].iloc[-2] and
        df["open"].iloc[-1] < df["close"].iloc[-2]
    )

def bearish_engulfing(df):
    return (
        df["close"].iloc[-2] > df["open"].iloc[-2] and
        df["close"].iloc[-1] < df["open"].iloc[-1] and
        df["open"].iloc[-1] > df["close"].iloc[-2] and
        df["close"].iloc[-1] < df["open"].iloc[-2]
    )

# ===== STRONG CANDLE FILTER =====
def strong_candle(df):
    body = abs(df["close"].iloc[-1] - df["open"].iloc[-1])
    range_ = df["high"].iloc[-1] - df["low"].iloc[-1]
    return body > range_ * 0.4  # relaxed

# ===== SIGNAL LOGIC =====
def get_signal(df):
    df["RSI"] = rsi(df)
    df = support_resistance(df)

    last = df.iloc[-1]

    # BUY
    if (
        bullish_engulfing(df) and
        strong_candle(df) and
        last["RSI"] < 40 and
        last["close"] <= last["support"] * 1.003
    ):
        return "BUY 🟢"

    # SELL
    if (
        bearish_engulfing(df) and
        strong_candle(df) and
        last["RSI"] > 60 and
        last["close"] >= last["resistance"] * 0.997
    ):
        return "SELL 🔴"

    return None

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot Started", reply_markup=reply_markup)

# ===== HANDLE =====
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global running
    text = update.message.text

    if text == "▶ Start Scan":
        running = True
        await update.message.reply_text("🚀 Auto Scan Started")

    elif text == "⏹ Stop":
        running = False
        await update.message.reply_text("⛔ Stopped")

    elif text == "📊 Strong Signal":
        for pair in PAIRS:
            try:
                df = get_data(pair)
                if df is None:
                    continue

                signal = get_signal(df)

                if signal:
                    time_now = datetime.now().strftime("%H:%M:%S")

                    msg = f"""📊 STRONG SIGNAL

Pair: {pair.replace('=X','')}
Signal: {signal}
Entry: Next Candle
Time: {time_now} IST
"""

                    await update.message.reply_text(msg)
                    return

            except Exception as e:
                print(e)

        await update.message.reply_text("❌ No Strong Signal Found")

# ===== MAIN =====
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, handle))

    print("🚀 Bot Running...")
    app.run_polling()
