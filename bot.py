# bot.py
# نسخه ویژه برای حامد افشاری ❤️
# ربات مدیریت پست تلگرام با منوی ۴ نقطه‌ای و پرامپت اسکرولی HTML

import logging
from telegram import (
    Update, InputMediaPhoto
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler
)

# ---------------- تنظیمات اصلی ----------------
TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))       

# وضعیت‌ها برای مدیریت گفتگو
IMAGES, CAPTION, PROMPTS = range(3)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# ---------------- دستورات منو ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("🚫 فقط ادمین می‌تواند از این ربات استفاده کند.")
    await update.message.reply_text(
        "سلام حامد 👋\n"
        "از منوی پایین (دکمه چهار نقطه کنار سنجاق 📎) یکی از گزینه‌ها رو انتخاب کن:\n\n"
        "📰 /news - پست خبری\n"
        "💬 /single - ارسال پیام با پرامپت (تکی)\n"
        "📚 /multi - ارسال پیام با پرامپت (چندتایی)\n"
        "❌ /cancel - لغو تمام فرآیندها"
    )


# ---------------- حالت ۱: پست خبری ----------------
async def news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text("🖼️ لطفاً عکس‌های پست خبری را ارسال کن (می‌تونی چندتا بفرستی).")
    return IMAGES


async def collect_images(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file_id = photo.file_id
    if "images" not in context.user_data:
        context.user_data["images"] = []
    context.user_data["images"].append(file_id)
    await update.message.reply_text("✅ عکس ذخیره شد. عکس بعدی رو بفرست یا /next رو بزن برای ادامه.")
    return IMAGES


async def next_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📝 حالا توضیح پستت رو بنویس (متن کپشن).")
    return CAPTION


async def collect_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["caption"] = update.message.text
    await update.message.reply_text("📦 حالا پرامپت (Prompt) رو بفرست.")
    return PROMPTS


async def collect_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["prompt"] = update.message.text

    images = context.user_data.get("images", [])
    caption = context.user_data.get("caption", "")
    prompt = context.user_data.get("prompt", "")

    # قالب HTML برای جعبه پرامپت
    prompt_box = f"""
<b>🧠 پرامپت آموزشی:</b>

<blockquote expandable>
<pre><code>{prompt}</code></pre>
</blockquote>
"""

    # ساخت متن نهایی
    final_text = f"{caption}\n\n{prompt_box}"

    # ارسال نهایی در چت ربات
    if images:
        media_group = [InputMediaPhoto(img) for img in images]
        await context.bot.send_media_group(chat_id=update.effective_chat.id, media=media_group)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=final_text,
        parse_mode=ParseMode.HTML
    )

    # پاک کردن داده‌ها
    context.user_data.clear()
    await update.message.reply_text("✅ پست آماده شد! حالا می‌تونی اونو فوروارد کنی به کانالت.")
    return ConversationHandler.END


# ---------------- حالت ۲ و ۳: پیام تکی و چندتایی ----------------
async def single(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✳️ لطفاً تصویر مورد نظر را ارسال کن.")
    return IMAGES

async def multi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📸 تصاویر مورد نظر را یکی‌یکی ارسال کن، بعد از اتمام /next رو بزن.")
    return IMAGES


# ---------------- لغو فرآیند ----------------
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ تمام فرآیندها لغو شد.")
    return ConversationHandler.END


# ---------------- اجرای اصلی ----------------
def main():
    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("news", news),
            CommandHandler("single", single),
            CommandHandler("multi", multi)
        ],
        states={
            IMAGES: [
                MessageHandler(filters.PHOTO, collect_images),
                CommandHandler("next", next_step)
            ],
            CAPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_caption)],
            PROMPTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_prompt)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(conv_handler)

    print("🤖 Bot is running... (Press CTRL+C to stop)")
    app.run_polling()


if __name__ == "__main__":
    main()
