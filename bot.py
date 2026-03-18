
import requests
import telebot
import time
import threading
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from openai import OpenAI

# 🔑 ENV VARIABLES
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
API_KEY = os.getenv("TWELVE_API_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

bot = telebot.TeleBot(BOT_TOKEN)
client = OpenAI(api_key=OPENAI_KEY)

SYMBOLS = ["EUR/USD", "GBP/USD", "USD/JPY"]
last_signal = {}

# 📡 GET DATA
def get_data(symbol):
    try:
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=1min&outputsize=50&apikey={API_KEY}"
        data = requests.get(url).json()
        return data.get("values", [])
    except:
        return []

# 📊 EMA
def ema(values, period):
    if len(values) < period:
        return None
    k = 2 / (period + 1)
    ema_val = float(values[0])
    for v in values[1:]:
        ema_val = (float(v) * k) + (ema_val * (1 - k))
    return ema_val

# 📊 RSI
def rsi(values):
    gains, losses = [], []
    for i in range(1, len(values)):
        diff = float(values[i]) - float(values[i-1])
        if diff > 0:
            gains.append(diff)
        else:
            losses.append(abs(diff))

    if not gains or not losses:
        return 50

    avg_gain = sum(gains)/len(gains)
    avg_loss = sum(losses)/len(losses)

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# 🔥 SIGNAL LOGIC
def check_signal(symbol):
    data = get_data(symbol)
    if len(data) < 10:
        return None

    closes = [x["close"] for x in data if "close" in x]

    ema9 = ema(closes[:9], 9)
    ema21 = ema(closes[:21], 21)
    r = rsi(closes[:14])

    c1, c2, c3 = data[2], data[1], data[0]

    o1, c1v = float(c1['open']), float(c1['close'])
    o2, c2v = float(c2['open']), float(c2['close'])
    o3, c3v = float(c3['open']), float(c3['close'])

    body = abs(c3v - o3)
    rng = abs(float(c3['high']) - float(c3['low']))

    if body < (rng * 0.4):
        return None

    # BUY
    if c1v > o1 and c2v > o2 and c3v > o3 and ema9 > ema21 and r < 65:
        return "📈 BUY"

    # SELL
    if c1v < o1 and c2v < o2 and c3v < o3 and ema9 < ema21 and r > 35:
        return "📉 SELL"

    return None

# 🤖 AI CONFIRM
def ai_confirm(pair, signal):
    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": f"{pair} {signal} confirm strong or weak? one word"}
            ]
        )
        return res.choices[0].message.content
    except:
        return "AI error"

# 🔁 LIVE LOOP
def live_loop():
    while True:
        for pair in SYMBOLS:
            sig = check_signal(pair)

            if sig and last_signal.get(pair) != sig:
                last_signal[pair] = sig

                ai = ai_confirm(pair, sig)

                text = f"""
🔥 VIP SIGNAL
Pair: {pair}
Signal: {sig}
AI: {ai}

⏱ Entry: 5-10 sec
⌛ Expiry: 30-60 sec
"""

                try:
                    bot.send_message(int(CHAT_ID), text)
                except:
                    pass

        time.sleep(10)

# 🤖 START
@bot.message_handler(commands=['start'])
def start(msg):
    bot.send_message(msg.chat.id, "🤖 BOT STARTED\n🔥 Use Get Signal")

@bot.message_handler(func=lambda m: "signal" in m.text.lower())
def manual(msg):
    text = "📊 SIGNAL\n\n"
    for pair in SYMBOLS:
        sig = check_signal(pair)
        if sig:
            text += f"{pair} → {sig}\n"

    if text == "📊 SIGNAL\n\n":
        text += "No signal"

    bot.send_message(msg.chat.id, text)

# 🌐 SERVER FIX (Render)
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Bot Running')

def run_server():
    server = HTTPServer(('0.0.0.0', 10000), Handler)
    server.serve_forever()

# 🚀 START ALL
threading.Thread(target=run_server).start()
threading.Thread(target=live_loop).start()

print("BOT RUNNING...")
bot.polling()
