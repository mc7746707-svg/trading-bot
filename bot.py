
import requests
import pandas as pd
import time
from telegram import Bot
from datetime import datetime, timedelta
import pytz

# ===== SETTINGS =====
TOKEN = "YOUR_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"

bot = Bot(token=TOKEN)

OTC_PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCHF"]
REAL_PAIRS = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]

INTERVAL = "1m"

# ===== TIME =====
def get_time():
    ist = pytz.timezone("Asia/Kolkata")
    return datetime.now(ist)

# ===== DATA =====
def get_data(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={INTERVAL}&limit=100"
    data = requests.get(url).json()

    df = pd.DataFrame(data)
    df = df.iloc[:, :5]
    df.columns = ["time","open","high","low","close"]

    df = df.astype(float)
    return df

# ===== RSI =====
def rsi(df, period=14):
    delta = df["close"].diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta).clip(lower=0).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# ===== EMA =====
def ema(df, period=50):
    return df["close"].ewm(span=period).mean()

# ===== PATTERNS =====
def bullish(df):
    p, c = df.iloc[-2], df.iloc[-1]
    return p.close < p.open and c.close > c.open

def bearish(df):
    p, c = df.iloc[-2], df.iloc[-1]
    return p.close > p.open and c.close < c.open

def hammer(df):
    c = df.iloc[-1]
    return (c.open - c.low) > 2*(c.close - c.open)

def shooting(df):
    c = df.iloc[-1]
    return (c.high - c.open) > 2*(c.open - c.close)

# ===== SIGNAL =====
def signal(df, mode):
    price = df["close"].iloc[-1]

    if mode == "REAL":
        r = rsi(df).iloc[-1]
        e = ema(df).iloc[-1]

        if bullish(df) and r < 40 and price > e:
            return "🔥 BUY (REAL)"

        if bearish(df) and r > 60 and price < e:
            return "🔻 SELL (REAL)"

    if mode == "OTC":
        r = rsi(df,7).iloc[-1]

        if hammer(df) and r < 30:
            return "⚡ BUY (OTC)"

        if shooting(df) and r > 70:
            return "⚡ SELL (OTC)"

    return None

# ===== LOOP =====
last = {}

while True:
    try:
        now = get_time()

        # REAL
        for pair in REAL_PAIRS:
            df = get_data(pair)
            s = signal(df, "REAL")

            if s and last.get(pair) != s:
                entry = now.strftime("%H:%M:%S")
                expiry = (now + timedelta(minutes=3)).strftime("%H:%M:%S")

                msg = f"{pair}\n{s}\nEntry: {entry}\nExpiry: {expiry}"
                bot.send_message(chat_id=CHAT_ID, text=msg)
                last[pair] = s

        # OTC
        for pair in OTC_PAIRS:
            df = get_data("BTCUSDT")
            s = signal(df, "OTC")

            if s and last.get(pair) != s:
                entry = now.strftime("%H:%M:%S")
                expiry = (now + timedelta(minutes=1)).strftime("%H:%M:%S")

                msg = f"{pair} OTC\n{s}\nEntry: {entry}\nExpiry: {expiry}"
                bot.send_message(chat_id=CHAT_ID, text=msg)
                last[pair] = s

        time.sleep(60)

    except Exception as e:
        print(e)
        time.sleep(10)
