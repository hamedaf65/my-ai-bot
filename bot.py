# bot.py
# نسخه ویژه برای حامد افشاری ❤️
import os
import html
import logging
from telegram import (
    Update, InputMediaPhoto, InputMediaVideo, InputMediaDocument
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler
)

# ---------------- تنظیمات اصلی ----------------
TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
CHANNEL_ID = os.getenv("CHANNEL_ID")  # آی‌دی کانال شما

# وضعیت‌ها برای مدیریت گفتگو
IMAGES, FILES, CAPTION, PROMPTS = range(4)

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

# ---------------- تابع کمکی برای ساخت کپشن HTML ----------------
def make_html_caption(text: str, prompt: str = "") -> str:
    prompt_box = ""
    if prompt:
        prompt_box = f"""
<b>🧠 پرامپت آموزشی:</b>
<blockquote expandable>
<pre><code>{html.escape(prompt)}</code></pre>
</blockquote>
"""
    final_text = f"{text}\n{prompt_box}\n\n🔗 منبع: <a href='https://t.me/hamedaf_ir'>هوش مصنوعی با حامد افشاری</a>"
    return final_text

# ---------------- حالت ۱: پست خبری ----------------
async def news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text("🖼️ لطفاً فایل‌ها یا عکس‌های پست خبری را ارسال کن (چندتایی می‌تواند باشد).")
    return FILES

async def collect_files_news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # شناسایی نوع فایل
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        media_type = "photo"
    elif update.message.document:
        file_id = update.message.document.file_id
        media_type = "document"
    elif update.message.video:
        file_id = update.message.video.file_id
        media_type = "video"
    elif update.message.audio:
        file_id = update.message.audio.file_id
        media_type = "audio"
    else:
        return await update.message.reply_text("⚠️ نوع فایل پشتیبانی نمی‌شود.")

    if "files" not in context.user_data:
        context.user_data["files"] = []
    context.user_data["files"].append({"id": file_id, "type": media_type})
    await update.message.reply_text("✅ فایل ذخیره شد. فایل بعدی را بفرست یا /next برای ادامه.")
    return FILES

async def next_step_news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📝 حالا متن پست را ارسال کن.")
    return CAPTION

async def collect_caption_news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    context.user_data["caption"] = text

    files = context.user_data.get("files", [])
    media_group = []
    for f in files:
        if f["type"] == "photo":
            media_group.append(InputMediaPhoto(f["id"], caption=text if len(media_group)==0 else None))
        elif f["type"] == "video":
            media_group.append(InputMediaVideo(f["id"], caption=text if len(media_group)==0 else None))
        else:  # document, audio
            # متن در پیام جدا با لینک به فایل
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=f"{text}\n\n🔗 منبع: <a href='https://t.me/hamedaf_ir'>هوش مصنوعی با حامد افشاری</a>",
                parse_mode=ParseMode.HTML
            )

    if media_group:
        await context.bot.send_media_group(chat_id=CHANNEL_ID, media=media_group)

    context.user_data.clear()
    await update.message.reply_text("✅ پست خبری ارسال شد!")
    return ConversationHandler.END

# ---------------- حالت ۲: پست تکی ----------------
async def single(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✳️ لطفاً فایل مورد نظر را ارسال کن.")
    return FILES

async def collect_files_single(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # شناسایی نوع فایل
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        media_type = "photo"
    elif update.message.document:
        file_id = update.message.document.file_id
        media_type = "document"
    elif update.message.video:
        file_id = update.message.video.file_id
        media_type = "video"
    elif update.message.audio:
        file_id = update.message.audio.file_id
        media_type = "audio"
    else:
        return await update.message.reply_text("⚠️ نوع فایل پشتیبانی نمی‌شود.")

    context.user_data["file"] = {"id": file_id, "type": media_type}
    await update.message.reply_text("📝 حالا متن و پرامپت (اختیاری) را ارسال کن.")
    return CAPTION

async def collect_caption_single(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    context.user_data["caption"] = text
    file_info = context.user_data.get("file")

    # تصمیم گیری بر اساس طول متن
    if len(text) < 4000:  # پیام کوتاه
        caption = make_html_caption(text)
        if file_info["type"] == "photo":
            await context.bot.send_photo(chat_id=CHANNEL_ID, photo=file_info["id"], caption=caption, parse_mode=ParseMode.HTML)
        elif file_info["type"] == "video":
            await context.bot.send_video(chat_id=CHANNEL_ID, video=file_info["id"], caption=caption, parse_mode=ParseMode.HTML)
        else:
            await context.bot.send_document(chat_id=CHANNEL_ID, document=file_info["id"])
            await context.bot.send_message(chat_id=CHANNEL_ID, text=caption, parse_mode=ParseMode.HTML)
    else:  # متن طولانی
        if file_info["type"] in ["photo","video"]:
            await context.bot.send_media_group(chat_id=CHANNEL_ID, media=[InputMediaPhoto(file_info["id"])] if file_info["type"]=="photo" else [InputMediaVideo(file_info["id"])])
        else:
            await context.bot.send_document(chat_id=CHANNEL_ID, document=file_info["id"])
        await context.bot.send_message(chat_id=CHANNEL_ID, text=make_html_caption(text), parse_mode=ParseMode.HTML)

    context.user_data.clear()
    await update.message.reply_text("✅ پست تکی ارسال شد!")
    return ConversationHandler.END

# ---------------- حالت ۳: پیام چندتایی ----------------
async def multi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📸 فایل‌های مورد نظر را یکی‌یکی ارسال کن، بعد از اتمام /next رو بزن.")
    context.user_data["multi_files"] = []
    return FILES

async def collect_files_multi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # شناسایی نوع فایل
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        media_type = "photo"
    elif update.message.document:
        file_id = update.message.document.file_id
        media_type = "document"
    elif update.message.video:
        file_id = update.message.video.file_id
        media_type = "video"
    elif update.message.audio:
        file_id = update.message.audio.file_id
        media_type = "audio"
    else:
        return await update.message.reply_text("⚠️ نوع فایل پشتیبانی نمی‌شود.")

    context.user_data["multi_files"].append({"id": file_id, "type": media_type})
    await update.message.reply_text("✅ فایل ذخیره شد. فایل بعدی را بفرست یا /next برای ادامه.")
    return FILES

async def next_step_multi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📝 حالا متن و پرامپت را ارسال کن.")
    return PROMPTS

async def collect_prompt_multi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    prompt = update.message.text  # می‌توان پرامپت جداگانه گرفت
    files = context.user_data.get("multi_files", [])

    caption = make_html_caption(text, prompt)

    media_group = []
    for f in files:
        if f["type"] == "photo":
            media_group.append(InputMediaPhoto(f["id"], caption=caption if len(media_group)==0 else None))
        elif f["type"] == "video":
            media_group.append(InputMediaVideo(f["id"], caption=caption if len(media_group)==0 else None))
        else:
            await context.bot.send_document(chat_id=CHANNEL_ID, document=f["id"])
    if media_group:
        await context.bot.send_media_group(chat_id=CHANNEL_ID, media=media_group)

    context.user_data.clear()
    await update.message.reply_text("✅ پست چندتایی ارسال شد!")
    return ConversationHandler.END

# ---------------- لغو فرآیند ----------------
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ تمام فرآیندها لغو شد.")
    return ConversationHandler.END

# ---------------- اجرای اصلی ----------------
def main():
    app = Application.builder().token(TOKEN).build()

    conv_handler_news = ConversationHandler(
        entry_points=[CommandHandler("news", news)],
        states={
            FILES: [MessageHandler(filters.ALL & ~filters.COMMAND, collect_files_news),
                    CommandHandler("next", next_step_news)],
            CAPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_caption_news)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    conv_handler_single = ConversationHandler(
        entry_points=[CommandHandler("single", single)],
        states={
            FILES: [MessageHandler(filters.ALL & ~filters.COMMAND, collect_files_single)],
            CAPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_caption_single)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    conv_handler_multi = ConversationHandler(
        entry_points=[CommandHandler("multi", multi)],
        states={
            FILES: [MessageHandler(filters.ALL & ~filters.COMMAND, collect_files_multi),
                    CommandHandler("next", next_step_multi)],
            PROMPTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_prompt_multi)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(conv_handler_news)
    app.add_handler(conv_handler_single)
    app.add_handler(conv_handler_multi)

    print("🤖 Bot is running... (Press CTRL+C to stop)")
    app.run_polling()

if __name__ == "__main__":
    main()
