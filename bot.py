# bot.py
# نسخه نهایی ویژه برای حامد افشاری ❤️
# ربات مدیریت پست تلگرام با پشتیبانی کامل از فایل‌ها و پرامپت‌های Markdown (با دکمه Copy Code تلگرام)

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
CHANNEL_ID = os.getenv("CHANNEL_ID")  # آیدی عددی یا @channelusername
BOT_USERNAME = os.getenv("BOT_USERNAME")

FILES, CAPTION, PROMPT = range(3)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# ---------------- دستور /start ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    # حالت فقط دریافت پرامپت برای کاربران
    if args and args[0].startswith("prompt_"):
        prompt_text = args[0][len("prompt_"):]
        await update.message.reply_text(
            f"🧠 پرامپت آماده:\n\n```{prompt_text}```\n\n📋 برای کپی، روی بخش بالا بزن.",
            parse_mode="Markdown"
        )
        return

    # محدودیت فقط برای ادمین
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("🚫 این ربات فقط برای استفاده ادمین فعال است.")

    await update.message.reply_text(
        "سلام حامد 👋\n"
        "از منوی پایین یکی از گزینه‌ها رو انتخاب کن:\n\n"
        "📰 /news - پست خبری\n"
        "💬 /single - پست با پرامپت (تکی)\n"
        "📚 /multi - پست با چند پرامپت (چندتایی)\n"
        "❌ /cancel - لغو عملیات"
    )

# ---------------- پست خبری ----------------
async def news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    context.user_data.clear()
    await update.message.reply_text("🖼️ لطفاً فایل‌ها را ارسال کن (اختیاری).")
    return FILES

async def collect_news_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "files" not in context.user_data:
        context.user_data["files"] = []
    msg = update.message
    if msg.photo:
        context.user_data["files"].append(("photo", msg.photo[-1].file_id))
    elif msg.video:
        context.user_data["files"].append(("video", msg.video.file_id))
    elif msg.document:
        context.user_data["files"].append(("document", msg.document.file_id))

    await update.message.reply_text("✅ فایل ذخیره شد. فایل بعدی یا /next برای ادامه.")
    return FILES

async def news_next(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📝 متن پست خبری را بفرست (اختیاری).")
    return CAPTION

async def collect_news_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = update.message.text or ""
    files = context.user_data.get("files", [])
    caption_with_link = f"{caption}\n\n🔗 هوش مصنوعی با [حامد افشاری](https://t.me/hamedaf_ir)"
    if files:
        media_group = []
        first_sent = False
        for ftype, fid in files:
            if ftype == "photo":
                media_group.append(InputMediaPhoto(fid, caption=caption_with_link if not first_sent else None, parse_mode=ParseMode.MARKDOWN))
                first_sent = True
            elif ftype == "video":
                media_group.append(InputMediaVideo(fid, caption=caption_with_link if not first_sent else None, parse_mode=ParseMode.MARKDOWN))
                first_sent = True
            elif ftype == "document":
                media_group.append(InputMediaDocument(fid, caption=caption_with_link if not first_sent else None, parse_mode=ParseMode.MARKDOWN))
                first_sent = True
        await context.bot.send_media_group(chat_id=CHANNEL_ID, media=media_group)
    else:
        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=caption_with_link,
            parse_mode="Markdown",
            disable_web_page_preview=True
        )

    context.user_data.clear()
    await update.message.reply_text("✅ پست خبری ارسال شد!")
    return ConversationHandler.END

# ---------------- پست تکی با پرامپت Markdown ----------------
async def single(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("🚫 این دستور فقط برای ادمین فعال است.")
    context.user_data.clear()
    await update.message.reply_text("💬 لطفاً فایل را ارسال کن (اختیاری).")
    return FILES

async def collect_single_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if msg.photo:
        context.user_data["file"] = ("photo", msg.photo[-1].file_id)
    elif msg.video:
        context.user_data["file"] = ("video", msg.video.file_id)
    elif msg.document:
        context.user_data["file"] = ("document", msg.document.file_id)
    else:
        context.user_data["file"] = None
    await update.message.reply_text("📝 لطفاً توضیح پست را بفرست.")
    return CAPTION

async def collect_single_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["caption"] = update.message.text or ""
    await update.message.reply_text("🧠 لطفاً پرامپت را بفرست.")
    return PROMPT

async def collect_single_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = context.user_data.get("caption", "")
    file_data = context.user_data.get("file")
    prompt = update.message.text or ""

    prompt_block = f"```{prompt}```"
    final_text = f"{caption}\n\n{prompt_block}\n\n🔗 هوش مصنوعی با [حامد افشاری](https://t.me/hamedaf_ir)"

    if file_data:
        ftype, fid = file_data
        if ftype == "photo":
            await context.bot.send_photo(CHANNEL_ID, fid, caption=final_text, parse_mode="Markdown", disable_web_page_preview=True)
        elif ftype == "video":
            await context.bot.send_video(CHANNEL_ID, fid, caption=final_text, parse_mode="Markdown", disable_web_page_preview=True)
        elif ftype == "document":
            await context.bot.send_document(CHANNEL_ID, fid, caption=final_text, parse_mode="Markdown", disable_web_page_preview=True)
    else:
        await context.bot.send_message(CHANNEL_ID, text=final_text, parse_mode="Markdown", disable_web_page_preview=True)

    context.user_data.clear()
    await update.message.reply_text("✅ پست ارسال شد!")
    return ConversationHandler.END

# ---------------- پست چندتایی با چند پرامپت ----------------
async def multi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("🚫 این دستور فقط برای ادمین فعال است.")
    context.user_data.clear()
    context.user_data["files"] = []
    context.user_data["prompts"] = []
    await update.message.reply_text("📚 فایل‌ها را بفرست. هر زمان تمام شد، /next را بزن.")
    return FILES

async def collect_multi_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if msg.photo:
        context.user_data["files"].append(("photo", msg.photo[-1].file_id))
    elif msg.video:
        context.user_data["files"].append(("video", msg.video.file_id))
    elif msg.document:
        context.user_data["files"].append(("document", msg.document.file_id))
    await update.message.reply_text("✅ فایل ذخیره شد یا /next را بزن.")
    return FILES

async def multi_next_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📝 توضیح اول را بفرست.")
    return CAPTION

async def collect_multi_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["current_caption"] = update.message.text or ""
    await update.message.reply_text("🧠 حالا پرامپت را بفرست یا /publish برای انتشار نهایی.")
    return PROMPT

async def collect_multi_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = update.message.text or ""
    caption = context.user_data.get("current_caption", "")
    context.user_data["prompts"].append((caption, prompt))
    await update.message.reply_text("✅ پرامپت ذخیره شد. /next برای پرامپت بعدی یا /publish برای انتشار.")
    return PROMPT

async def publish_multi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    files = context.user_data.get("files", [])
    prompts = context.user_data.get("prompts", [])

    if not prompts:
        await update.message.reply_text("⚠️ هیچ پرامپتی ثبت نشده است.")
        return ConversationHandler.END

    # ارسال همه فایل‌ها در یک گروه
    if files:
        media_group = []
        for ftype, fid in files:
            if ftype == "photo":
                media_group.append(InputMediaPhoto(fid))
            elif ftype == "video":
                media_group.append(InputMediaVideo(fid))
            elif ftype == "document":
                media_group.append(InputMediaDocument(fid))
        await context.bot.send_media_group(chat_id=CHANNEL_ID, media=media_group)

    # ساخت پیام نهایی
    full_text = ""
    for caption, prompt in prompts:
        prompt_block = f"```{prompt}```"
        full_text += f"{caption}\n\n{prompt_block}\n\n"
    full_text += "🔗 هوش مصنوعی با [حامد افشاری](https://t.me/hamedaf_ir)"

    await context.bot.send_message(CHANNEL_ID, text=full_text, parse_mode="Markdown", disable_web_page_preview=True)
    context.user_data.clear()
    await update.message.reply_text("✅ پست چندتایی منتشر شد!")
    return ConversationHandler.END

# ---------------- لغو ----------------
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ عملیات لغو شد.")
    return ConversationHandler.END

# ---------------- اجرای اصلی ----------------
def main():
    app = Application.builder().token(TOKEN).build()

    # پست خبری
    news_handler = ConversationHandler(
        entry_points=[CommandHandler("news", news)],
        states={
            FILES: [
                CommandHandler("next", news_next),
                MessageHandler(filters.ALL & ~filters.COMMAND, collect_news_files),
            ],
            CAPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_news_caption)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # پست تکی
    single_handler = ConversationHandler(
        entry_points=[CommandHandler("single", single)],
        states={
            FILES: [MessageHandler(filters.ALL & ~filters.COMMAND, collect_single_files)],
            CAPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_single_caption)],
            PROMPT: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_single_prompt)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # پست چندتایی
    multi_handler = ConversationHandler(
        entry_points=[CommandHandler("multi", multi)],
        states={
            FILES: [
                CommandHandler("next", multi_next_caption),
                MessageHandler(filters.ALL & ~filters.COMMAND, collect_multi_files),
            ],
            CAPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_multi_caption)],
            PROMPT: [
                CommandHandler("next", multi_next_caption),
                CommandHandler("publish", publish_multi),
                MessageHandler(filters.TEXT & ~filters.COMMAND, collect_multi_prompt),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(news_handler)
    app.add_handler(single_handler)
    app.add_handler(multi_handler)

    print("🤖 Bot is running... (Press CTRL+C to stop)")
    app.run_polling()

if __name__ == "__main__":
    main()
