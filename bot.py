import requests
import telebot
import time
import threading
from datetime import datetime
import pytz
from telebot.types import ReplyKeyboardMarkup
from http.server import BaseHTTPRequestHandler, HTTPServer
from openai import OpenAI
import os

# ===== ENV =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
API_KEY = os.getenv("TWELVE_API")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

bot = telebot.TeleBot(BOT_TOKEN)
client = OpenAI(api_key=OPENAI_KEY)

SYMBOLS = ["EUR/USD", "GBP/USD", "USD/JPY"]
last_signal = {}
user_time = {}

# ===== IST TIME =====
def get_ist_time():
    ist = pytz.timezone("Asia/Kolkata")
    return datetime.now(ist).strftime("%H:%M:%S")

# ===== MENU =====
def menu():
    m = ReplyKeyboardMarkup(resize_keyboard=True)
    m.add("🔥 Get Signal", "⏱ Set Time")
    return m

def time_menu():
    m = ReplyKeyboardMarkup(resize_keyboard=True)
    m.add("5 sec", "10 sec")
    m.add("15 sec", "1 min")
    return m

# ===== START =====
@bot.message_handler(commands=['start'])
def start(msg):
    bot.send_message(msg.chat.id, "🤖 PRO BOT READY", reply_markup=menu())

# ===== TIME =====
@bot.message_handler(func=lambda m: m.text == "⏱ Set Time")
def set_time(msg):
    bot.send_message(msg.chat.id, "Select Time", reply_markup=time_menu())

@bot.message_handler(func=lambda m: m.text in ["5 sec","10 sec","15 sec","1 min"])
def save_time(msg):
    user_time[msg.chat.id] = msg.text
    bot.send_message(msg.chat.id, f"✅ Time set: {msg.text}", reply_markup=menu())

# ===== DATA =====
def get_data(symbol):
    try:
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=1min&outputsize=20&apikey={API_KEY}"
        res = requests.get(url).json()
        return res.get("values", [])
    except:
        return []

# ===== EMA =====
def ema(data, period):
    if len(data) < period:
        return 0
    k = 2 / (period + 1)
    ema_val = data[0]
    for price in data:
        ema_val = price * k + ema_val * (1 - k)
    return ema_val

# ===== RSI =====
def rsi(data):
    gains, losses = [], []
    for i in range(1, len(data)):
        diff = data[i] - data[i-1]
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

# ===== SIGNAL (PRO LOGIC) =====
def check_signal(symbol):
    data = get_data(symbol)

    if len(data) < 10:
        return None

    closes = [float(x["close"]) for x in data]

    ema9 = ema(closes, 9)
    ema21 = ema(closes, 21)
    r = rsi(closes)

    c1, c2, c3 = data[2], data[1], data[0]

    o1, c1v = float(c1['open']), float(c1['close'])
    o2, c2v = float(c2['open']), float(c2['close'])
    o3, c3v = float(c3['open']), float(c3['close'])

    h3 = float(c3['high'])
    l3 = float(c3['low'])

    body = abs(c3v - o3)
    rng = abs(h3 - l3)

    if body < (rng * 0.5):
        return None

    bullish = c3v > o3 and c2v < o2 and c3v > o2
    bearish = c3v < o3 and c2v > o2 and c3v < o2

    if (c1v > o1 and c2v > o2 and c3v > o3) or bullish:
        if ema9 > ema21 and r < 65:
            return "📈 BUY (STRONG)"

    if (c1v < o1 and c2v < o2 and c3v < o3) or bearish:
        if ema9 < ema21 and r > 35:
            return "📉 SELL (STRONG)"

    return None

# ===== AI =====
def ai_confirm(pair, sig):
    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": f"{pair} {sig} strong or weak? one word"}
            ]
        )
        return res.choices[0].message.content.strip()
    except:
        return "AI error"

# ===== MANUAL BUTTON =====
@bot.message_handler(func=lambda m: m.text == "🔥 Get Signal")
def manual_signal(msg):
    text = "🔥 LIVE SIGNAL\n\n"

    for pair in SYMBOLS:
        sig = check_signal(pair)

        if sig:
            ai = ai_confirm(pair, sig)
            now = get_ist_time()
            expiry = user_time.get(msg.chat.id, "1 min")

            text += f"""
Pair: {pair}
Signal: {sig}
AI: {ai}
Entry: {now} (IST)
Expiry: {expiry}

"""

    if text == "🔥 LIVE SIGNAL\n\n":
        text += "No strong signal ⚪"

    bot.send_message(msg.chat.id, text)

# ===== AUTO =====
def live_loop():
    while True:
        for pair in SYMBOLS:
            sig = check_signal(pair)

            if sig and last_signal.get(pair) != sig:
                last_signal[pair] = sig

                ai = ai_confirm(pair, sig)
                now = get_ist_time()

                text = f"""
🔥 VIP AUTO SIGNAL
Pair: {pair}
Signal: {sig}
AI: {ai}

⏱ Entry: {now} (IST)
⌛ Expiry: 1 min
"""

                try:
                    bot.send_message(int(CHAT_ID), text)
                except:
                    pass

        time.sleep(10)

# ===== WEB FIX =====
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot Running")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()

# ===== START =====
threading.Thread(target=run_server).start()
threading.Thread(target=live_loop).start()

print("🔥 PRO BOT RUNNING...")

bot.polling()
