import requests
import pandas as pd
import ta
from datetime import datetime, timedelta
import pytz
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI

# ===== CONFIG =====
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"
API_KEY = "YOUR_TWELVE_DATA_API_KEY"
OPENAI_KEY = "YOUR_OPENAI_API_KEY"

client = OpenAI(api_key=OPENAI_KEY)

SYMBOLS = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CHF"]
INTERVAL = "1min"

last_signal = {}
auto_users = set()

# ===== INDIA TIME =====
def get_entry_time():
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist) + timedelta(minutes=1)
    return now.strftime("%H:%M:%S")

# ===== DATA =====
def get_data(pair):
    url = f"https://api.twelvedata.com/time_series?symbol={pair}&interval={INTERVAL}&apikey={API_KEY}&outputsize=100"
    res = requests.get(url).json()

    df = pd.DataFrame(res['values'])
    df = df.astype(float)
    df = df.iloc[::-1]

    return df

# ===== STRONG SIGNAL LOGIC =====
def check_signal(pair):
    df = get_data(pair)

    # Indicators
    df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=7).rsi()
    df['ema9'] = ta.trend.EMAIndicator(df['close'], window=9).ema_indicator()
    df['ema21'] = ta.trend.EMAIndicator(df['close'], window=21).ema_indicator()

    df['body'] = abs(df['close'] - df['open'])
    df['range'] = df['high'] - df['low']
    df['small'] = df['body'] < df['range'] * 0.4

    c0 = df.iloc[-1]
    c1 = df.iloc[-2]
    c2 = df.iloc[-3]

    # Trend
    bullTrend = c0['ema9'] > c0['ema21']
    bearTrend = c0['ema9'] < c0['ema21']

    # Momentum strong filter
    bullMom = c0['rsi'] > 55
    bearMom = c0['rsi'] < 45

    # Strong breakout candle
    bullConfirm = c1['close'] > c1['open'] and (c1['close'] - c1['open']) > (c2['range'] * 0.6) and c1['close'] > c2['high']
    bearConfirm = c1['close'] < c1['open'] and (c1['open'] - c1['close']) > (c2['range'] * 0.6) and c1['close'] < c2['low']

    # FINAL SIGNAL
    if c2['small'] and bullConfirm and bullTrend and bullMom:
        return "BUY"

    if c2['small'] and bearConfirm and bearTrend and bearMom:
        return "SELL"

    return None

# ===== AI CONFIRM =====
def ai_confirm(pair, sig):
    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": f"{pair} {sig} strong or weak trading signal?"}]
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
    await update.message.reply_text("🤖 PRO BOT READY (IST TIME)", reply_markup=markup)

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

                # AI filter
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
async def auto_signal(app):
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
                await app.bot.send_message(user, text)

            await app.bot.send_message(chat_id=CHAT_ID, text=text)

# ===== RUN =====
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT, handle))

app.job_queue.run_repeating(lambda ctx: ctx.application.create_task(auto_signal(app)), interval=60, first=10)

print("BOT RUNNING (IST)...")

app.run_polling()
