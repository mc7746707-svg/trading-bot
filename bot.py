import pandas as pd
import requests
import time
from datetime import datetime
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator

# =========================
# TELEGRAM CONFIG
# =========================
TOKEN = "YOUR_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"

def send_signal(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# =========================
# PAIRS LIST
# =========================

REAL_PAIRS = [
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD",
    "EURJPY", "GBPJPY", "EURGBP", "AUDJPY", "USDCHF"
]

OTC_PAIRS = [
    "EURUSD-OTC", "GBPUSD-OTC", "USDJPY-OTC", "AUDUSD-OTC", "USDCAD-OTC",
    "EURJPY-OTC", "GBPJPY-OTC", "EURGBP-OTC", "AUDJPY-OTC", "USDCHF-OTC"
]

# =========================
# TIME FILTER (IST)
# =========================
def is_good_time():
    now = datetime.now()
    hour = now.hour

    # BEST TIME WINDOWS
    if 13 <= hour <= 16:   # London
        return True
    if 18 <= hour <= 21:   # NY overlap
        return True

    return False

# =========================
# DATA (Replace API)
# =========================
def get_data(pair):
    # Replace with real API
    data = {
        "open":  [100,101,102,101,100,99,100],
        "close": [101,102,101,100,99,100,102],
        "high":  [102,103,103,102,101,101,103],
        "low":   [99,100,100,99,98,98,99]
    }
    return pd.DataFrame(data)

# =========================
# CANDLE LOGIC
# =========================
def is_bullish(c):
    return c['close'] > c['open']

def is_bearish(c):
    return c['close'] < c['open']

def is_small(c):
    body = abs(c['close'] - c['open'])
    rng = c['high'] - c['low']
    return body < rng * 0.3

# =========================
# ANALYSIS
# =========================
def analyze_pair(pair):
    df = get_data(pair)

    df['ema'] = EMAIndicator(df['close'], window=5).ema_indicator()
    df['rsi'] = RSIIndicator(df['close'], window=5).rsi()

    last = df.iloc[-1]

    if is_small(last):
        return

    # BUY
    if is_bullish(last) and last['close'] > last['ema'] and last['rsi'] < 60:
        send_signal(f"🟢 BUY {pair}")

    # SELL
    elif is_bearish(last) and last['close'] < last['ema'] and last['rsi'] > 40:
        send_signal(f"🔴 SELL {pair}")

# =========================
# MAIN LOOP
# =========================
while True:

    if is_good_time():
        print("✅ Trading Time Active")

        # REAL MARKET
        for pair in REAL_PAIRS:
            analyze_pair(pair)

        # OTC (Always optional)
        for pair in OTC_PAIRS:
            analyze_pair(pair)

    else:
        print("⏸️ Waiting for best time...")

    time.sleep(60)
