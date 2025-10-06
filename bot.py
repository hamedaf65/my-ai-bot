# bot.py
# نسخه ویژه برای حامد افشاری ❤️
# ربات مدیریت پست تلگرام با پشتیبانی فایل‌های مختلف و پرامپت هوشمند

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

TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
CHANNEL_ID = os.getenv("CHANNEL_ID")  # آیدی کانال به صورت عددی

FILES, CAPTION, PROMPT = range(3)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# ---------------- دستورات اصلی ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("🚫 فقط ادمین می‌تواند از این ربات استفاده کند.")
    await update.message.reply_text(
        "سلام حامد 👋\n"
        "از منوی پایین یکی از گزینه‌ها رو انتخاب کن:\n\n"
        "📰 /news - پست خبری\n"
        "💬 /single - ارسال پیام با پرامپت (تکی)\n"
        "📚 /multi - ارسال پیام با پرامپت (چندتایی)\n"
        "❌ /cancel - لغو تمام فرآیندها"
    )

# ---------------- پست خبری ----------------
async def news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    context.user_data.clear()
    await update.message.reply_text("🖼️ لطفاً فایل/عکس‌های پست خبری را ارسال کن (اختیاری).")
    return FILES

async def collect_news_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "files" not in context.user_data:
        context.user_data["files"] = []

    if update.message.photo:
        context.user_data["files"].append(("photo", update.message.photo[-1].file_id))
    elif update.message.video:
        context.user_data["files"].append(("video", update.message.video.file_id))
    elif update.message.document:
        context.user_data["files"].append(("document", update.message.document.file_id))

    await update.message.reply_text("✅ فایل ذخیره شد. فایل بعدی را بفرست یا /next را بزن برای ادامه.")
    return FILES

async def news_next(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📝 حالا متن پست را ارسال کن (اختیاری).")
    return CAPTION

async def collect_news_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["caption"] = update.message.text if update.message.text else ""
    files = context.user_data.get("files", [])
    caption = context.user_data.get("caption", "")

    # ✅ افزودن کد تبلیغی بدون نمایش تصویر کانال
    caption_with_link = f"{caption}\n\n🔗 <a href='https://t.me/hamedaf_ir?embed=1'>هوش مصنوعی با حامد افشاری</a>"

    if files:
        media_group = []
        first_sent = False
        for ftype, fid in files:
            if ftype == "photo":
                media_group.append(InputMediaPhoto(fid, caption=caption_with_link if not first_sent else None, parse_mode=ParseMode.HTML))
                first_sent = True
            elif ftype == "video":
                media_group.append(InputMediaVideo(fid, caption=caption_with_link if not first_sent else None, parse_mode=ParseMode.HTML))
                first_sent = True
            elif ftype == "document":
                media_group.append(InputMediaDocument(fid, caption=caption_with_link if not first_sent else None, parse_mode=ParseMode.HTML))
                first_sent = True
        await context.bot.send_media_group(chat_id=CHANNEL_ID, media=media_group)
    else:
        if caption:
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=caption_with_link,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True  # 🚫 جلوگیری از نمایش تصویر کانال
            )

    context.user_data.clear()
    await update.message.reply_text("✅ پست خبری ارسال شد!")
    return ConversationHandler.END

# ---------------- پیام تکی و چندتایی ----------------
async def single(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("💬 لطفاً فایل‌ها را ارسال کن (اختیاری).")
    return FILES

async def multi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("📚 فایل‌ها را یکی‌یکی ارسال کن، بعد از اتمام /next را بزن.")
    return FILES

async def collect_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "files" not in context.user_data:
        context.user_data["files"] = []

    if update.message.photo:
        context.user_data["files"].append(("photo", update.message.photo[-1].file_id))
    elif update.message.video:
        context.user_data["files"].append(("video", update.message.video.file_id))
    elif update.message.document:
        context.user_data["files"].append(("document", update.message.document.file_id))

    await update.message.reply_text("✅ فایل ذخیره شد یا /next را بزن برای ادامه.")
    return FILES

async def next_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📝 حالا متن توضیحی پست را ارسال کن (اختیاری).")
    return CAPTION

async def collect_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["caption"] = update.message.text if update.message.text else ""
    await update.message.reply_text("🧠 پرامپت را ارسال کن (اختیاری).")
    return PROMPT

async def collect_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["prompt"] = update.message.text if update.message.text else ""
    files = context.user_data.get("files", [])
    caption = context.user_data.get("caption", "")
    prompt = context.user_data.get("prompt", "")

    total_length = len(caption) + len(prompt)

    # ✅ قالب پرامپت قابل انتخاب آسان برای کپی
    prompt_box = f"""
<blockquote expandable style="background-color:#d0e7ff;padding:10px;border-radius:5px;">
<pre><code>{html.escape(prompt)}</code></pre>
</blockquote>
""" if prompt else ""

    # ✅ تبلیغ با غیرفعال بودن پیش‌نمایش
    final_caption = f"{caption}\n\n{prompt_box}\n\n🔗 <a href='https://t.me/hamedaf_ir?embed=1'>هوش مصنوعی با حامد افشاری</a>"

    if total_length <= 1024:  # کپشن کوتاه
        if files:
            first_sent = False
            media_group = []
            for ftype, fid in files:
                if ftype == "photo":
                    media_group.append(InputMediaPhoto(fid, caption=final_caption if not first_sent else None, parse_mode=ParseMode.HTML))
                    first_sent = True
                elif ftype == "video":
                    media_group.append(InputMediaVideo(fid, caption=final_caption if not first_sent else None, parse_mode=ParseMode.HTML))
                    first_sent = True
                elif ftype == "document":
                    media_group.append(InputMediaDocument(fid, caption=final_caption if not first_sent else None, parse_mode=ParseMode.HTML))
                    first_sent = True
            await context.bot.send_media_group(chat_id=CHANNEL_ID, media=media_group)
        else:
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=final_caption,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True  # 🚫 جلوگیری از تصویر کانال
            )
    else:  # کپشن طولانی
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

        if caption or prompt:
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=final_caption,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True  # 🚫 جلوگیری از نمایش تصویر کانال
            )

    context.user_data.clear()
    await update.message.reply_text("✅ پست ارسال شد!")
    return ConversationHandler.END

# ---------------- لغو ----------------
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ تمام فرآیندها لغو شد.")
    return ConversationHandler.END

# ---------------- اجرای اصلی ----------------
def main():
    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("single", single),
            CommandHandler("multi", multi)
        ],
        states={
            FILES: [
                CommandHandler("next", next_step),
                MessageHandler(filters.ALL & ~filters.COMMAND, collect_files)
            ],
            CAPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_caption)],
            PROMPT: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_prompt)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # ✅ پست خبری بدون مرحله پرامپت و با لینک تبلیغی بدون پیش‌نمایش
    news_handler = ConversationHandler(
        entry_points=[CommandHandler("news", news)],
        states={
            FILES: [
                CommandHandler("next", news_next),
                MessageHandler(filters.ALL & ~filters.COMMAND, collect_news_files)
            ],
            CAPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_news_caption)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(news_handler)
    app.add_handler(conv_handler)

    print("🤖 Bot is running... (Press CTRL+C to stop)")
    app.run_polling()

if __name__ == "__main__":
    main()
