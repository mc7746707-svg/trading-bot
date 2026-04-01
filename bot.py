import requests
import pandas as pd
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ===== TELEGRAM =====
TOKEN = "8243137774:AAGmJVCcZM0wefrhNhqmeE09s25V4OrbsTE"
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

# ===== CANDLE PATTERN =====
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

# ===== SIGNAL LOGIC =====
def get_signal(df):
    df["RSI"] = rsi(df)
    df = support_resistance(df)

    last = df.iloc[-1]

    # BUY
    if (
        bullish_engulfing(df) and
        last["RSI"] < 30 and
        last["close"] <= last["support"] * 1.002
    ):
        return "BUY 🟢"

    # SELL
    if (
        bearish_engulfing(df) and
        last["RSI"] > 70 and
        last["close"] >= last["resistance"] * 0.998
    ):
        return "SELL 🔴"

    return None

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot Started 🚀", reply_markup=reply_markup)

# ===== HANDLE =====
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "📊 Strong Signal":
        for pair in PAIRS:
            try:
                df = get_data(pair)
                signal = get_signal(df)

                if signal:
                    time_now = datetime.now().strftime("%H:%M:%S")

                    msg = f"""
📊 STRONG SIGNAL

Pair: {pair.replace('=X','')}
Signal: {signal}
Entry: Next Candle
Time: {time_now} IST
"""

                    await update.message.reply_text(msg)
                    return

            except:
                pass

        await update.message.reply_text("No Strong Signal ❌")

# ===== MAIN =====
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, handle))

    print("Bot Running...")

    app.run_polling()
