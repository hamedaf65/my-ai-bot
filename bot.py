# bot.py
# نسخه ویژه برای حامد افشاری ❤️
# ربات مدیریت پست تلگرام با پشتیبانی فایل‌های مختلف و پرامپت چندتایی در حالت چندتایی (multi)

import os
import html
import logging
import urllib.parse
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
CHANNEL_ID = os.getenv("CHANNEL_ID")

FILES, CAPTION, PROMPT = range(3)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# ---------------- دستور /start ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    user_id = update.effective_user.id

    # فقط لینک‌های پرامپت برای همه مجاز است
    if args and args[0].startswith("prompt_"):
        prompt_text = urllib.parse.unquote(args[0][len("prompt_"):])
        await update.message.reply_text(
            f"🧠 <b>پرامپت آماده:</b>\n\n<code>{html.escape(prompt_text)}</code>\n\n📋 برای کپی، روی متن بالا لمس کن.",
            parse_mode="HTML"
        )
        return

    if user_id != ADMIN_ID:
        await update.message.reply_text(
            "🚫 شما اجازه‌ی استفاده از این ربات را ندارید.\n"
            "فقط می‌توانید از لینک‌های پرامپت استفاده کنید."
        )
        return

    await update.message.reply_text(
        "سلام حامد 👋\n"
        "از منوی پایین یکی از گزینه‌ها رو انتخاب کن:\n\n"
        "📰 /news - پست خبری\n"
        "💬 /single - ارسال پست با پرامپت (تکی)\n"
        "📚 /multi - ارسال پست با پرامپت (چندتایی)\n"
        "❌ /cancel - لغو و ریست کامل"
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
    msg = update.message

    if msg.photo:
        context.user_data["files"].append(("photo", msg.photo[-1].file_id))
    elif msg.video:
        context.user_data["files"].append(("video", msg.video.file_id))
    elif msg.document:
        context.user_data["files"].append(("document", msg.document.file_id))

    await update.message.reply_text("✅ فایل ذخیره شد. فایل بعدی را بفرست یا /next را بزن برای ادامه.")
    return FILES

async def news_next(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📝 حالا متن پست را ارسال کن (اختیاری).")
    return CAPTION

async def collect_news_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = update.message.text or ""
    files = context.user_data.get("files", [])

    caption_with_link = f"{caption}\n\n🔗 [هوش مصنوعی با حامد افشاری](https://t.me/hamedaf_ir)\n📸 [صفحه اینستاگرام](https://www.instagram.com/hamedafshar.ir?igsh=MTA1cmR5eTZjdjRxYQ==)\n💬 [ارتباط با من](https://t.me/hamedafshari_ir)"

    if files:
        media_group = []
        first_sent = False
        for ftype, fid in files:
            if ftype == "photo":
                media_group.append(InputMediaPhoto(fid, caption=caption_with_link if not first_sent else None, parse_mode=ParseMode.MARKDOWN))
            elif ftype == "video":
                media_group.append(InputMediaVideo(fid, caption=caption_with_link if not first_sent else None, parse_mode=ParseMode.MARKDOWN))
            elif ftype == "document":
                media_group.append(InputMediaDocument(fid, caption=caption_with_link if not first_sent else None, parse_mode=ParseMode.MARKDOWN))
            first_sent = True
        await context.bot.send_media_group(chat_id=CHANNEL_ID, media=media_group)
    else:
        if caption:
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=caption_with_link,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )

    context.user_data.clear()
    await update.message.reply_text("✅ پست خبری ارسال شد!")
    return ConversationHandler.END

# ---------------- پیام تکی و چندتایی ----------------
async def single(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("🚫 فقط ادمین می‌تواند پست ارسال کند.")
    context.user_data.clear()
    await update.message.reply_text("💬 لطفاً فایل‌ها را ارسال کن (اختیاری).")
    return FILES

async def multi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("🚫 فقط ادمین می‌تواند پست ارسال کند.")
    context.user_data.clear()
    context.user_data["prompts"] = []
    await update.message.reply_text("📚 فایل‌ها را یکی‌یکی ارسال کن، بعد از اتمام /next را بزن.")
    return FILES

async def collect_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if "files" not in context.user_data:
        context.user_data["files"] = []
    msg = update.message

    if msg.photo:
        context.user_data["files"].append(("photo", msg.photo[-1].file_id))
    elif msg.video:
        context.user_data["files"].append(("video", msg.video.file_id))
    elif msg.document:
        context.user_data["files"].append(("document", msg.document.file_id))

    await update.message.reply_text("✅ فایل ذخیره شد یا /next را بزن برای ادامه.")
    return FILES

async def next_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📝 لطفاً متن توضیحی پست را بفرست (اختیاری).")
    return CAPTION

async def collect_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["caption"] = update.message.text or ""
    await update.message.reply_text("🧠 حالا پرامپت را بفرست. (یا دستور /publish برای انتشار)")
    return PROMPT

async def collect_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.strip().lower() == "/publish":
        return await publish_post(update, context)

    prompt = update.message.text or ""
    if prompt:
        context.user_data.setdefault("prompts", []).append(prompt)
    await update.message.reply_text("✅ پرامپت ذخیره شد. پرامپت بعدی؟ یا /publish برای انتشار.")
    return PROMPT

async def publish_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    files = context.user_data.get("files", [])
    caption = context.user_data.get("caption", "")
    prompts = context.user_data.get("prompts", [])

    # همه پرامپت‌ها با backtick جداگانه
    prompt_text = "\n\n".join([f"```{p}```" for p in prompts])
    final_caption = f"{caption}\n\n{prompt_text}\n\n🔗 [هوش مصنوعی با حامد افشاری](https://t.me/hamedaf_ir)\n📸 [صفحه اینستاگرام](https://www.instagram.com/hamedafshar.ir?igsh=MTA1cmR5eTZjdjRxYQ==)\n💬 [ارتباط با من](https://t.me/hamedafshari_ir)"

    if len(final_caption) <= 1024:
        if files:
            first_sent = False
            media_group = []
            for ftype, fid in files:
                if ftype == "photo":
                    media_group.append(InputMediaPhoto(fid, caption=final_caption if not first_sent else None, parse_mode=ParseMode.MARKDOWN))
                elif ftype == "video":
                    media_group.append(InputMediaVideo(fid, caption=final_caption if not first_sent else None, parse_mode=ParseMode.MARKDOWN))
                elif ftype == "document":
                    media_group.append(InputMediaDocument(fid, caption=final_caption if not first_sent else None, parse_mode=ParseMode.MARKDOWN))
                first_sent = True
            await context.bot.send_media_group(chat_id=CHANNEL_ID, media=media_group)
        else:
            await context.bot.send_message(chat_id=CHANNEL_ID, text=final_caption, parse_mode="Markdown", disable_web_page_preview=True )
    else:
        if files:
            await context.bot.send_media_group(chat_id=CHANNEL_ID, media=[InputMediaPhoto(fid) for _, fid in files])
        await context.bot.send_message(chat_id=CHANNEL_ID, text=final_caption, parse_mode="Markdown", disable_web_page_preview=True )

    context.user_data.clear()
    await update.message.reply_text("✅ پست نهایی ارسال شد!")
    return ConversationHandler.END

# ---------------- لغو ----------------
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ عملیات لغو شد و ربات ریست شد.")
    return ConversationHandler.END

# ---------------- اجرای اصلی ----------------
def main():
    app = Application.builder().token(TOKEN).build()

    news_handler = ConversationHandler(
        entry_points=[CommandHandler("news", news)],
        states={
            FILES: [CommandHandler("next", news_next), MessageHandler(filters.ALL & ~filters.COMMAND, collect_news_files)],
            CAPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_news_caption)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("single", single), CommandHandler("multi", multi)],
        states={
            FILES: [CommandHandler("next", next_step), MessageHandler(filters.ALL & ~filters.COMMAND, collect_files)],
            CAPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_caption)],
            PROMPT: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_prompt)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("publish", publish_post),
        ],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(news_handler)
    app.add_handler(conv_handler)

    print("🤖 Bot is running... (Press CTRL+C to stop)")
    app.run_polling()

if __name__ == "__main__":
    main()
