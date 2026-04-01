import requests
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "8243137774:AAHCKkESoXOT-Fy0_8hpkAExeiqFzNOc1MQ"
CHAT_ID = "6181352243"
PAIRS = [
    "EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X",
    "EURJPY=X","GBPJPY=X","EURGBP=X","AUDJPY=X"
]

keyboard = [
    ["▶ Start Scan","⏹ Stop"],
    ["📊 Strong Signal"]
]

reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ===== GET DATA =====
def get_data(pair):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{pair}?interval=1m&range=1d"
        data = requests.get(url).json()

        candles = data["chart"]["result"][0]["indicators"]["quote"][0]

        return candles

    except:
        return None

# ===== RSI =====
def rsi(close, period=14):
    gains, losses = [], []

    for i in range(1, len(close)):
        diff = close[i] - close[i-1]
        gains.append(max(diff,0))
        losses.append(abs(min(diff,0)))

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period if sum(losses[-period:]) != 0 else 1

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# ===== SUPPORT / RESISTANCE =====
def support_resistance(low, high):
    support = min(low[-20:])
    resistance = max(high[-20:])
    return support, resistance

# ===== ENGULFING =====
def bullish_engulfing(o,c):
    return c[-2]<o[-2] and c[-1]>o[-1] and c[-1]>o[-2] and o[-1]<c[-2]

def bearish_engulfing(o,c):
    return c[-2]>o[-2] and c[-1]<o[-1] and o[-1]>c[-2] and c[-1]<o[-2]

# ===== SIGNAL =====
def get_signal(data):
    close = data["close"]
    open_ = data["open"]
    high = data["high"]
    low = data["low"]

    if None in close[-20:]:
        return None

    rsi_val = rsi(close)
    support, resistance = support_resistance(low, high)

    last_close = close[-1]

    # BUY
    if bullish_engulfing(open_,close) and rsi_val < 40 and last_close <= support*1.003:
        return "BUY 🟢"

    # SELL
    if bearish_engulfing(open_,close) and rsi_val > 60 and last_close >= resistance*0.997:
        return "SELL 🔴"

    return None

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot Started", reply_markup=reply_markup)

# ===== HANDLE =====
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "📊 Strong Signal":
        for pair in PAIRS:
            data = get_data(pair)
            if not data:
                continue

            signal = get_signal(data)

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

        await update.message.reply_text("❌ No Signal")

# ===== MAIN =====
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, handle))

    print("Bot Running...")
    app.run_polling()
