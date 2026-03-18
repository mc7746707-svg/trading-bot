import requests
import telebot
import time
import threading

# 🔑 ADD YOUR KEYS HERE
API_KEY = "58f6ae48f9c0492882d9fbfe566e6080"
BOT_TOKEN = "8739755982:AAGmCLaxclmC4l3gSovoIWhxBHBDtOT_oqg"
CHAT_ID = "6181352243"

bot = telebot.TeleBot("8739755982:AAAmcLaxclmC413gSovoIWxBHBDtOT_oqg")

# OTC STYLE PAIRS
SYMBOLS = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD"]

# 📊 DATA FETCH
def get_data(symbol):
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=1min&outputsize=20&apikey={58f6ae48f9c0492882d9fbfe566e6080}"
    data = requests.get(url).json()
    return data['values']

# 🧠 OTC SIGNAL LOGIC
def otc_signal(data):
    c1 = data[1]  # previous candle
    c2 = data[0]  # current candle

    open1 = float(c1['open'])
    close1 = float(c1['close'])
    high1 = float(c1['high'])
    low1 = float(c1['low'])

    body = abs(close1 - open1)
    upper_wick = high1 - max(open1, close1)
    lower_wick = min(open1, close1) - low1

    # 🔴 SELL
    if upper_wick > body * 2.5 and float(c2['close']) < float(c2['open']):
        return f"SELL 🔴\nEntry: {close1}\nStop: {high1}"

    # 🟢 BUY
    if lower_wick > body * 2.5 and float(c2['close']) > float(c2['open']):
        return f"BUY 🟢\nEntry: {close1}\nStop: {low1}"

    return None

# 🔘 START COMMAND + BUTTON
@bot.message_handler(commands=['start'])
def start(msg):
    from telebot.types import ReplyKeyboardMarkup, KeyboardButton
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("GET SIGNAL"))
    bot.send_message(msg.chat.id, "🔥 OTC Signal Bot Ready\nClick GET SIGNAL", reply_markup=kb)

# 📲 MANUAL SIGNAL BUTTON
@bot.message_handler(func=lambda m: m.text == "GET SIGNAL")
def send_signal(msg):
    result = ""

    for pair in SYMBOLS:
        try:
            data = get_data(pair)
            sig = otc_signal(data)
            if sig:
                result += f"{pair}\n{sig}\n\n"
        except:
            pass

    if result == "":
        result = "No strong OTC signal ⚪"

    bot.send_message(msg.chat.id, 6181352243 result)

# 🤖 AUTO SIGNAL FUNCTION
def auto_signal():
    while True:
        result = ""

        for pair in SYMBOLS:
            try:
                data = get_data(pair)
                sig = otc_signal(data)
                if sig:
                    result += f"{pair}\n{sig}\n\n"
            except:
                pass

        if result != "":
            bot.send_message(CHAT_ID, 6181352243"🔥 AUTO SIGNAL\n\n{result}")

        time.sleep(60)  # हर 1 मिनट

# THREAD START
threading.Thread(target=auto_signal).start()

# RUN BOT
bot.polling()
