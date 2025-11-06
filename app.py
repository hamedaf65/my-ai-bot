# app.py
# سرور ساده برای webhook ربات تلگرام

import os
from flask import Flask, request
from bot import get_app

app = Flask(__name__)
bot_app = get_app()

TOKEN = os.getenv("TOKEN")
WEBHOOK_PATH = f"/{TOKEN}"
BASE_URL = os.getenv("RENDER_EXTERNAL_URL", "https://yourappname.onrender.com")
WEBHOOK_URL = f"{BASE_URL}{WEBHOOK_PATH}"

@app.route("/", methods=["GET"])
def home():
    return "🤖 Telegram Bot is running!"

@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    update = request.get_json(force=True)
    bot_app.update_queue.put(update)
    return "OK", 200

if __name__ == "__main__":
    import asyncio
    from telegram import Update

    async def run():
        await bot_app.bot.set_webhook(url=WEBHOOK_URL)
        print(f"Webhook set to: {WEBHOOK_URL}")
        app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))

    asyncio.run(run())
