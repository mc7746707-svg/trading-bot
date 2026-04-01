import time
import requests
import pandas as pd
from datetime import datetime

# 8 PAIRS
PAIRS = [
    "EURUSD=X",
    "GBPUSD=X",
    "USDJPY=X",
    "AUDUSD=X",
    "EURJPY=X",
    "GBPJPY=X",
    "EURGBP=X",
    "AUDJPY=X"
]

# DATA FETCH
def get_data(pair):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{pair}?interval=1m&range=1d"
    data = requests.get(url).json()
    candles = data["chart"]["result"][0]["indicators"]["quote"][0]

    df = pd.DataFrame({
        "open": candles["open"],
        "high": candles["high"],
        "low": candles["low"],
        "close": candles["close"]
    }).dropna()

    return df

# RSI
def rsi(df, period=14):
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# PATTERNS
def bullish_engulfing(p, c):
    return p["close"] < p["open"] and c["close"] > c["open"] and c["close"] > p["open"]

def bearish_engulfing(p, c):
    return p["close"] > p["open"] and c["close"] < c["open"] and c["close"] < p["open"]

def hammer(c):
    body = abs(c["close"] - c["open"])
    lower = min(c["open"], c["close"]) - c["low"]
    upper = c["high"] - max(c["open"], c["close"])
    return lower > body * 2 and upper < body

def shooting_star(c):
    body = abs(c["close"] - c["open"])
    upper = c["high"] - max(c["open"], c["close"])
    lower = min(c["open"], c["close"]) - c["low"]
    return upper > body * 2 and lower < body

# SUPPORT / RESISTANCE
def support_resistance(df):
    support = df["low"].rolling(10).min().iloc[-1]
    resistance = df["high"].rolling(10).max().iloc[-1]
    return support, resistance

# FAKE BREAKOUT
def fake_breakout(c, support, resistance):
    if c["low"] < support and c["close"] > support:
        return "BUY"
    if c["high"] > resistance and c["close"] < resistance:
        return "SELL"
    return None

# SIGNAL CHECK
def check_pair(pair):
    df = get_data(pair)
    df["RSI"] = rsi(df)

    p = df.iloc[-2]
    c = df.iloc[-1]

    support, resistance = support_resistance(df)
    fake = fake_breakout(c, support, resistance)

    # BUY
    if bullish_engulfing(p, c) and c["RSI"] < 35 and c["close"] > support:
        return "BUY 📈 (Engulfing)"

    if hammer(c) and c["RSI"] < 30 and fake == "BUY":
        return "BUY 📈 (Hammer + Fake Breakout)"

    # SELL
    if bearish_engulfing(p, c) and c["RSI"] > 65 and c["close"] < resistance:
        return "SELL 📉 (Engulfing)"

    if shooting_star(c) and c["RSI"] > 70 and fake == "SELL":
        return "SELL 📉 (Shooting Star + Fake Breakout)"

    return None

# MAIN LOOP
while True:
    print("\n🔍 SCANNING MARKET...\n")

    for pair in PAIRS:
        try:
            signal = check_pair(pair)

            if signal:
                now = datetime.now().strftime("%I:%M:%S %p")

                print(f"""
🔥 STRONG SIGNAL
PAIR: {pair.replace('=X','')}
SIGNAL: {signal}
ENTRY: NEXT CANDLE
TIME (IST): {now}
EXPIRY: 1 MIN
""")

        except Exception as e:
            print(f"Error in {pair}: {e}")

    time.sleep(60)
