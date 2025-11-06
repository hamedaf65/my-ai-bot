# app.py
import os
from flask import Flask, request
from telegram import Update
from telegram.ext import Application
import asyncio

app = Flask(__name__)

TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
CHANNEL_ID = os.getenv("CHANNEL_ID")

bot_app = Application.builder().token(TOKEN).build()

@app.route("/", methods=["GET"])
def home():
    return "🤖 Telegram bot is live on Vercel!"

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json(force=True)
    update_obj = Update.de_json(update, bot_app.bot)
    asyncio.run(bot_app.process_update(update_obj))
    return "ok", 200
