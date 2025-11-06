# app.py
import os
import asyncio
from flask import Flask, request, jsonify
from telegram import Update
from bot import get_app  # باید get_app() در bot.py وجود داشته باشد

app = Flask(__name__)

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise RuntimeError("TOKEN environment variable is not set")

# get_app باید یک Application ساخته‌شده برگرداند (بدون run_polling)
bot_app = get_app()

WEBHOOK_PATH = f"/{TOKEN}"
# Vercel provides VER CEL_URL without scheme in env sometimes; try both
BASE_URL = os.getenv("VERCEL_URL") or os.getenv("VERCEL_APP", "")
if BASE_URL and not BASE_URL.startswith("http"):
    BASE_URL = "https://" + BASE_URL
# fallback (در صورت نداشتن، فقط مسیر محلی کار می‌کند)
WEBHOOK_URL = f"{BASE_URL}{WEBHOOK_PATH}" if BASE_URL else None

@app.route("/", methods=["GET"])
def home():
    return "🤖 Telegram bot (Vercel) - OK", 200

@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    """Webhook endpoint: تبدیل JSON به Update و پردازش آن با python-telegram-bot."""
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({"ok": False, "error": "invalid json"}), 400

    # تبدیل به Update
    try:
        update_obj = Update.de_json(data, bot_app.bot)
    except Exception as e:
        return jsonify({"ok": False, "error": f"bad update json: {e}"}), 400

    # پردازش همزمان (هر درخواست یک run جدید از async loop)
    try:
        # اجرا کردن coroutine پردازش آپدیت
        asyncio.run(bot_app.process_update(update_obj))
    except Exception as e:
        # لاگ خطا
        print("Error processing update:", e)
        return jsonify({"ok": False, "error": str(e)}), 500

    return jsonify({"ok": True}), 200

# نکته: ما در Vercel این را اجرا نمی‌کنیم (Vercel خودش سرور را بالا می‌آورد).
# اما برای تست لوکال می‌توانید این فایل را اجرا کنید:
if __name__ == "__main__":
    if WEBHOOK_URL:
        try:
            # ست کردن webhook یک‌باره وقتی با python app.py محلی اجرا می‌کنیم
            bot_app.bot.set_webhook(WEBHOOK_URL)
            print("Webhook set to:", WEBHOOK_URL)
        except Exception as e:
            print("Warning: set_webhook failed:", e)
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
