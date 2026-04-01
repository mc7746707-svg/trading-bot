import asyncio
import requests
import pandas as pd
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "8243137774:AAF9g2vkBNVLY8_hgCbdDE41-n70qN8hzuE"
CHAT_ID = "6181352243"

PAIRS = [
"EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X",
"EURJPY=X","GBPJPY=X","EURGBP=X","AUDJPY=X"
]

running = False

keyboard = [
["▶ Start Scan", "⏹ Stop"],
["📊 Strong Signal"]
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
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def ema(df, period=20):
return df["close"].ewm(span=period).mean()

# ===== CANDLE PATTERNS =====
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

def hammer(df):
body = abs(df["close"].iloc[-1] - df["open"].iloc[-1])
lower_wick = df["open"].iloc[-1] - df["low"].iloc[-1]
return lower_wick > body * 2

def shooting_star(df):
body = abs(df["close"].iloc[-1] - df["open"].iloc[-1])
upper_wick = df["high"].iloc[-1] - df["close"].iloc[-1]
return upper_wick > body * 2

# ===== SIGNAL LOGIC =====
def get_signal(df):
df["RSI"] = rsi(df)
df["EMA"] = ema(df)

rsi_val = df["RSI"].iloc[-1]
price = df["close"].iloc[-1]
ema_val = df["EMA"].iloc[-1]

# BUY
if (
(bullish_engulfing(df) or hammer(df)) and
rsi_val < 30 and
price > ema_val
):
return "BUY"

# SELL
if (
(bearish_engulfing(df) or shooting_star(df)) and
rsi_val > 70 and
price < ema_val
):
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
🔥 STRONG SIGNAL

Pair: {pair.replace('=X','')}
Signal: {signal}
Time: {time_now} (India)
Expiry: 1 min
"""
await update.message.reply_text(msg)

except:
pass

await asyncio.sleep(60)

# ===== HANDLERS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
await update.message.reply_text("PRO Bot Started 🚀", reply_markup=reply_markup)

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

elif text == "📊 Strong Signal":
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
Time: {time_now}
"""
await update.message.reply_text(msg)
return
except:
pass

await update.message.reply_text("No strong signal ❌")

# ===== MAIN =====
if __name__ == "__main__":
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT, handle))
print("Bot Running...")
app.run_polling()
