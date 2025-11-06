import os
from flask import Flask, request
from telegram import Update
from bot import get_app  # استفاده از همان get_app در bot.py

app = Flask(__name__)
bot_app = get_app()

TOKEN = os.getenv("TOKEN")
WEBHOOK_PATH = f"/{TOKEN}"
BASE_URL = os.getenv("VERCEL_URL", "https://yourappname.vercel.app")
WEBHOOK_URL = f"https://{BASE_URL}{WEBHOOK_PATH}"

@app.route("/", methods=["GET"])
def home():
    return "🤖 Telegram Bot is running on Vercel!"

@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot_app.bot)
    bot_app.update_queue.put(update)
    return "OK", 200

# ست کردن webhook فقط وقتی locally یا از CLI اجرا می‌کنیم
if __name__ == "__main__":
    bot_app.bot.set_webhook(url=WEBHOOK_URL)
    print(f"Webhook set to {WEBHOOK_URL}")
