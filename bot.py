import requests
import telebot
import time
import threading
import os
from telebot.types import ReplyKeyboardMarkup
from openai import OpenAI

# 🔐 ENV KEYS (Render me dalna hai)
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
TWELVE_API_KEY = os.getenv("TWELVE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

bot = telebot.TeleBot(BOT_TOKEN)
client = OpenAI(api_key=OPENAI_API_KEY)

SYMBOLS = ["EUR/USD", "GBP/USD", "USD/JPY"]

last_signal = {}

# 📡 DATA
def get_data(symbol):
    try:
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=1min&outputsize=50&apikey={TWELVE_API_KEY}"
        data = requests.get(url).json()

        if "values" not in data:
            return []

        return data["values"]

    except:
        return []


# 📊 EMA
def ema(values, period):
    if not values or len(values) < period:
        return None

    k = 2 / (period + 1)
    ema_val = float(values[0])

    for v in values[1:]:
        ema_val = (float(v) * k) + (ema_val * (1 - k))

    return ema_val


# 📊 RSI
def rsi(values):
    if not values or len(values) < 2:
        return None

    gains, losses = [], []

    for i in range(1, len(values)):
        diff = float(values[i]) - float(values[i-1])
        if diff >= 0:
            gains.append(diff)
        else:
            losses.append(abs(diff))

    if not gains or not losses:
        return None

    avg_gain = sum(gains) / len(gains)
    avg_loss = sum(losses) / len(losses)

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))
# 🔥 REAL SIGNAL
def check_signal(symbol):

    data = get_data(symbol)

    if not data or len(data) < 10:
        return None

    closes = [x["close"] for x in data if "close" in x]

    ema9 = ema(closes[:9], 9)
    ema21 = ema(closes[:21], 21)
    r = rsi(closes[:14])

    if ema9 is None or ema21 is None or r is None:
        return None

    c1, c2, c3 = data[2], data[1], data[0]

    o1, c1v = float(c1['open']), float(c1['close'])
    o2, c2v = float(c2['open']), float(c2['close'])
    o3, c3v = float(c3['open']), float(c3['close'])

    body = abs(c3v - o3)

    if "high" not in c3 or "low" not in c3:
        return None

    rng = abs(float(c3['high']) - float(c3['low']))

    if body < (rng * 0.4):
        return None

    # 🟢 BUY
    if c1v > o1 and c2v > o2 and c3v > o3 and ema9 > ema21 and r > 50:
        return "📈 BUY"

    # 🔴 SELL
    if c1v < o1 and c2v < o2 and c3v < o3 and ema9 < ema21 and r < 50:
        return "📉 SELL"

    return None

    # 🟢 BUY
    if c1v > o1 and c2v > o2 and c3v > o3 and ema9 > ema21 and r < 65:
        return "📈 BUY"

    # 🔴 SELL
    if c1v < o1 and c2v < o2 and c3v < o3 and ema9 < ema21 and r > 35:
        return "📉 SELL"

    return None

# 🤖 AI CONFIRMATION
def ai_confirm(pair, signal):
    try:
        prompt = f"Confirm this binary trading signal: {pair} {signal}. Reply BUY or SELL with confidence %."
        res = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": prompt}]
        )
        return res.choices[0].message.content
    except:
        return "AI error"

# 🎯 MENU
def menu():
    m = ReplyKeyboardMarkup(resize_keyboard=True)
    m.add("🔥 Get Signal")
    return m

# START
@bot.message_handler(commands=['start'])
def start(msg):
    bot.send_message(msg.chat.id, "🤖 REAL AI BOT READY", reply_markup=menu())

# BUTTON SIGNAL
@bot.message_handler(func=lambda m: m.text == "🔥 Get Signal")
def signal(msg):
    text = "📊 REAL SIGNAL\n\n"

    for pair in SYMBOLS:
        sig = check_signal(pair)

        if sig:
            ai = ai_confirm(pair, sig)
            text += f"{pair}\n{sig}\n🤖 {ai}\n\n"

    if text == "📊 REAL SIGNAL\n\n":
        text += "No strong signal ⚪"

    text += "\n⏱ Entry: 5-10 sec"
    text += "\n⏳ Expiry: 30-60 sec"

    bot.send_message(msg.chat.id, text)

# LIVE ALERT
def live_loop():
    while True:
        for pair in SYMBOLS:
            sig = check_signal(pair)

            if sig and last_signal.get(pair) != sig:
                last_signal[pair] = sig

                ai = ai_confirm(pair, sig)

                try:
                    bot.send_message(
                        int(CHAT_ID),
                        f"🔥 LIVE ALERT\n\n{pair}\n{sig}\n🤖 {ai}"
                    )
                except:
                    pass

        time.sleep(10)

threading.Thread(target=live_loop).start()

print("BOT RUNNING...")
bot.polling()
