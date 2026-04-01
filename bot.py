import time
import requests
import pandas as pd
from datetime import datetime
from telegram import Bot

# TELEGRAM
TOKEN = "YOUR_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"
bot = Bot(token=TOKEN)

# 8 PAIRS
PAIRS = [
    "EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X",
    "EURJPY=X","GBPJPY=X","EURGBP=X","AUDJPY=X"
]

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

def rsi(df, period=14):
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def bullish_engulfing(p, c):
    return p["close"] < p["open"] and c["close"] > c["open"] and c["close"] > p["open"]

def bearish_engulfing(p, c):
    return p["close"] > p["open"] and c["close"] < c["open"] and c["close"] < p["open"]

def support_resistance(df):
    support = df["low"].rolling(10).min().iloc[-1]
    resistance = df["high"].rolling(10).max().iloc[-1]
    return support, resistance

def check_pair(pair):
    df = get_data(pair)
    df["RSI"] = rsi(df)

    p = df.iloc[-2]
    c = df.iloc[-1]

    support, resistance = support_resistance(df)

    if bullish_engulfing(p, c) and c["RSI"] < 35:
        return "BUY 📈"

    if bearish_engulfing(p, c) and c["RSI"] > 65:
        return "SELL 📉"

    return None

# LOOP
while True:
    for pair in PAIRS:
        try:
            signal = check_pair(pair)

            if signal:
                now = datetime.now().strftime("%I:%M:%S %p")

                msg = f"""
🔥 STRONG SIGNAL
PAIR: {pair.replace('=X','')}
SIGNAL: {signal}
ENTRY: NEXT CANDLE
TIME (IST): {now}
EXPIRY: 1 MIN
"""

                bot.send_message(chat_id=CHAT_ID, text=msg)
                print(msg)

        except:
            continue

    time.sleep(60)
