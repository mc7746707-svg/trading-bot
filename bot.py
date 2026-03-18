import os
import requests
import pandas as pd
import ta
from datetime import datetime, timedelta
import pytz
import threading
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI

# ===== ENV CONFIG =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
API_KEY = os.getenv("API_KEY")
OPENAI_KEY = os.getenv("OPENAI_KEY")

client = OpenAI(api_key=OPENAI_KEY)

SYMBOLS = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CHF"]

last_signal = {}
auto_users = set()

# ===== FLASK (ANTI-SLEEP) =====
app_web = Flask(__name__)

@app_web.route('/')
def home():
    return "Bot Running ✅"

def run_web():
    app_web.run(host="0.0.0.0", port=10000)

# ===== INDIA TIME =====
def get_entry_time():
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist) + timedelta(minutes=1)
    return now.strftime("%H:%M:%S")

# ===== DATA =====
def get_data(pair):
    url = f"https://api.twelvedata.com/time_series?symbol={pair}&interval=1min&apikey={API_KEY}&outputsize=100"
    res = requests.get(url).json()

    df = pd.DataFrame(res['values'])
    df = df.astype(float)
    df = df.iloc[::-1]
    return df

# ===== SIGNAL LOGIC =====
def check_signal(pair):
    df = get_data(pair)

    df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=7).rsi()
    df['ema9'] = ta.trend.EMAIndicator(df['close'], window=9).ema_indicator()
    df['ema21'] = ta.trend.EMAIndicator(df['close'], window=21).ema_indicator()

    df['body'] = abs(df['close'] - df['open'])
    df['range'] = df['high'] - df['low']
    df['small'] = df['body'] < df['range'] * 0.4

    c0 = df.iloc[-1]
    c1 = df.iloc[-2]
    c2 = df.iloc[-3]

    bullTrend = c0['ema9'] > c0['ema21']
    bearTrend = c0['ema9'] < c0['ema21']

    bullMom = c0['rsi'] > 55
    bearMom = c0['rsi'] < 45

    bullConfirm = c1['close'] > c1['open'] and c1['close'] > c2['high']
    bearConfirm = c1['close'] < c1['open'] and c1['close'] < c2['low']

    if c2['small'] and bullConfirm and bullTrend and bullMom:
        return "BUY"

    if c2['small'] and bearConfirm and bearTrend and bearMom:
        return "SELL"

    return None

# ===== AI =====
def ai_confirm(pair, sig):
    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": f"{pair} {sig} strong or weak?"}]
        )
        return res.choices[0].message.content.strip()
    except:
        return "AI unavailable"

# ===== BUTTON UI =====
keyboard = [
    ["🔥 Get Signal"],
    ["🤖 Auto ON", "⛔ Auto OFF"]
]
markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 BOT READY (IST)", reply_markup=markup)

# ===== HANDLE =====
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    text = update.message.text

    if text == "🔥 Get Signal":
        msg = "🔥 LIVE SIGNAL\n\n"

        for pair in SYMBOLS:
            sig = check_signal(pair)

            if sig:
                ai = ai_confirm(pair, sig)

                if sig == "BUY" and "BUY" not in ai.upper():
                    continue
                if sig == "SELL" and "SELL" not in ai.upper():
                    continue

                entry = get_entry_time()

                msg += f"""📊 {pair}
Signal: {'🟢 BUY' if sig=='BUY' else '🔴 SELL'}
AI: {ai}
⏱ Entry: {entry} (IST)
⏳ Expiry: 2 min

"""

        if msg == "🔥 LIVE SIGNAL\n\n":
            msg += "⚪ No strong signal"

        await update.message.reply_text(msg)
        await context.bot.send_message(chat_id=CHAT_ID, text=msg)

    elif text == "🤖 Auto ON":
        auto_users.add(chat_id)
        await update.message.reply_text("✅ Auto ON")

    elif text == "⛔ Auto OFF":
        auto_users.discard(chat_id)
        await update.message.reply_text("❌ Auto OFF")

# ===== AUTO SIGNAL =====
async def auto_signal(context: ContextTypes.DEFAULT_TYPE):
    app = context.application

    for pair in SYMBOLS:
        sig = check_signal(pair)

        if sig and last_signal.get(pair) != sig:
            last_signal[pair] = sig

            ai = ai_confirm(pair, sig)

            if sig == "BUY" and "BUY" not in ai.upper():
                continue
            if sig == "SELL" and "SELL" not in ai.upper():
                continue

            entry = get_entry_time()

            text = f"""🔥 VIP AUTO SIGNAL

📊 {pair}
Signal: {'🟢 BUY' if sig=='BUY' else '🔴 SELL'}
AI: {ai}
⏱ Entry: {entry} (IST)
⏳ Expiry: 2 min
"""

            for user in auto_users:
                await app.bot.send_message(chat_id=user, text=text)

            await app.bot.send_message(chat_id=int(CHAT_ID), text=text)

# ===== MAIN =====
def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT, handle))

    # Auto every 60 sec
    application.job_queue.run_repeating(auto_signal, interval=60, first=10)

    print("BOT RUNNING SUCCESS ✅")

application.run_polling()

# ===== RUN =====
if __name__ == "__main__":
    print("STARTING BOT 🔥")
    threading.Thread(target=run_web).start()
    main()
