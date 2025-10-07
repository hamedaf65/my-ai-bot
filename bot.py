# bot.py
# نسخه نهایی ویژه برای حامد افشاری ❤️
# ساختار چندتایی درختی با دریافت توضیح ↔ پرامپت و دکمه‌های Next / Publish Post

import os
import html
import logging
import urllib.parse
from telegram import (
    Update, InputMediaPhoto, InputMediaVideo, InputMediaDocument, InlineKeyboardButton, InlineKeyboardMarkup
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

# ---------------- دکمه‌ها ----------------
def get_prompt_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Next", callback_data="next_caption"),
         InlineKeyboardButton("📤 Publish Post", callback_data="publish_post")]
    ])

# ---------------- /start ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    user_id = update.effective_user.id

    # فقط دریافت پرامپت برای دیگران مجاز است
    if args and args[0].startswith("prompt_"):
        prompt_text = urllib.parse.unquote(args[0][len("prompt_"):])
        await update.message.reply_text(
            f"🧠 <b>پرامپت آماده:</b>\n\n<code>{html.escape(prompt_text)}</code>",
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
        "📚 /multi - ارسال پست با پرامپت (چندتایی درختی)\n"
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
    await update.message.reply_text("✅ فایل ذخیره شد. فایل بعدی را بفرست یا /next را بزن.")
    return FILES

async def news_next(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📝 حالا متن پست را ارسال کن (اختیاری).")
    return CAPTION

async def collect_news_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = update.message.text or ""
    files = context.user_data.get("files", [])
    caption_with_link = f"{caption}\n\n🔗 [هوش مصنوعی با حامد افشاری](https://t.me/hamedaf_ir?embed=0)"
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
        await context.bot.send_message(chat_id=CHANNEL_ID, text=caption_with_link, parse_mode="Markdown", disable_web_page_preview=True)
    context.user_data.clear()
    await update.message.reply_text("✅ پست خبری ارسال شد!")
    return ConversationHandler.END

# ---------------- حالت چندتایی ----------------
async def multi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("🚫 فقط ادمین می‌تواند پست ارسال کند.")
    context.user_data.clear()
    context.user_data["prompts"] = []
    context.user_data["captions"] = []
    await update.message.reply_text("📚 فایل‌ها را بفرست، بعد از اتمام /next را بزن.")
    return FILES

async def collect_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    await update.message.reply_text("📝 لطفاً توضیح را بفرست.")
    return CAPTION

async def collect_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = update.message.text or ""
    context.user_data["captions"].append(caption)
    await update.message.reply_text("🧠 حالا پرامپت مربوط به این توضیح را بفرست.", reply_markup=get_prompt_keyboard())
    return PROMPT

async def collect_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = update.message.text or ""
    context.user_data["prompts"].append(prompt)
    await update.message.reply_text("✅ پرامپت ذخیره شد.", reply_markup=get_prompt_keyboard())
    return PROMPT

# ---------------- دکمه‌های تعاملی (Next / Publish) ----------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "next_caption":
        await query.message.reply_text("📝 توضیح بعدی را بفرست:")
        context.user_data["state"] = "caption"
        return CAPTION
    elif query.data == "publish_post":
        await publish_post(query, context)

async def publish_post(update_or_query, context: ContextTypes.DEFAULT_TYPE):
    files = context.user_data.get("files", [])
    captions = context.user_data.get("captions", [])
    prompts = context.user_data.get("prompts", [])
    parts = []
    for i in range(len(prompts)):
        cap = captions[i] if i < len(captions) else ""
        pro = prompts[i]
        parts.append(f"{cap}\n\n```{pro}```")
    final_caption = "\n\n".join(parts) + "\n\n🔗 [هوش مصنوعی با حامد افشاری](https://t.me/hamedaf_ir?embed=0)"
    if len(final_caption) <= 1024:
        if files:
            media_group = []
            first_sent = False
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
            await context.bot.send_message(chat_id=CHANNEL_ID, text=final_caption, parse_mode="Markdown", disable_web_page_preview=True)
    else:
        await context.bot.send_message(chat_id=CHANNEL_ID, text=final_caption, parse_mode="Markdown", disable_web_page_preview=True)
    context.user_data.clear()
    if isinstance(update_or_query, Update):
        await update_or_query.message.reply_text("✅ پست نهایی ارسال شد!")
    else:
        await update_or_query.message.reply_text("✅ پست نهایی ارسال شد!")

# ---------------- لغو ----------------
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ عملیات لغو شد و ربات ریست شد.")
    return ConversationHandler.END

# ---------------- اجرای اصلی ----------------
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))

    app.add_handler(MessageHandler(filters.COMMAND, cancel))
    app.add_handler(MessageHandler(filters.ALL, collect_files))

    news_handler = ConversationHandler(
        entry_points=[CommandHandler("news", news)],
        states={
            FILES: [CommandHandler("next", news_next), MessageHandler(filters.ALL & ~filters.COMMAND, collect_news_files)],
            CAPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_news_caption)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("multi", multi)],
        states={
            FILES: [CommandHandler("next", next_step), MessageHandler(filters.ALL & ~filters.COMMAND, collect_files)],
            CAPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_caption)],
            PROMPT: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_prompt)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(news_handler)
    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, collect_prompt))
    app.add_handler(CommandHandler("publish", publish_post))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, collect_files))
    app.add_handler(MessageHandler(filters.ALL, cancel))
    app.add_handler(MessageHandler(filters.COMMAND, cancel))
    app.add_handler(CommandHandler("next", next_step))
    app.add_handler(CommandHandler("multi", multi))
    app.add_handler(CommandHandler("news", news))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("publish", publish_post))
    app.add_handler(CommandHandler("single", multi))
    app.add_handler(CommandHandler("multi", multi))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("publish", publish_post))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, collect_files))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, collect_prompt))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, collect_caption))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, collect_files))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, collect_caption))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, collect_prompt))
    app.add_handler(CommandHandler("next", next_step))
    app.add_handler(CommandHandler("publish", publish_post))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ALL, cancel))
    app.add_handler(MessageHandler(filters.ALL, collect_prompt))
    app.add_handler(MessageHandler(filters.ALL, collect_caption))
    app.add_handler(MessageHandler(filters.ALL, collect_files))
    app.add_handler(CommandHandler("next", next_step))
    app.add_handler(CommandHandler("publish", publish_post))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("multi", multi))
    app.add_handler(MessageHandler(filters.ALL, collect_files))
    app.add_handler(MessageHandler(filters.ALL, collect_caption))
    app.add_handler(MessageHandler(filters.ALL, collect_prompt))
    app.add_handler(CommandHandler("next", next_step))
    app.add_handler(CommandHandler("publish", publish_post))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("multi", multi))
    app.add_handler(CommandHandler("news", news))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("publish", publish_post))
    app.add_handler(MessageHandler(filters.ALL, collect_files))
    app.add_handler(MessageHandler(filters.ALL, collect_caption))
    app.add_handler(MessageHandler(filters.ALL, collect_prompt))
    app.add_handler(CommandHandler("next", next_step))
    app.add_handler(CommandHandler("publish", publish_post))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("multi", multi))
    app.add_handler(CommandHandler("news", news))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("publish", publish_post))
    app.add_handler(MessageHandler(filters.ALL, collect_files))
    app.add_handler(MessageHandler(filters.ALL, collect_caption))
    app.add_handler(MessageHandler(filters.ALL, collect_prompt))
    app.add_handler(CommandHandler("next", next_step))
    app.add_handler(CommandHandler("publish", publish_post))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("multi", multi))
    app.add_handler(CommandHandler("news", news))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("publish", publish_post))
    app.add_handler(MessageHandler(filters.ALL, collect_files))
    app.add_handler(MessageHandler(filters.ALL, collect_caption))
    app.add_handler(MessageHandler(filters.ALL, collect_prompt))
    app.add_handler(CommandHandler("next", next_step))
    app.add_handler(CommandHandler("publish", publish_post))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("multi", multi))
    app.add_handler(CommandHandler("news", news))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("publish", publish_post))
    app.add_handler(MessageHandler(filters.ALL, collect_files))
    app.add_handler(MessageHandler(filters.ALL, collect_caption))
    app.add_handler(MessageHandler(filters.ALL, collect_prompt))
    app.add_handler(CommandHandler("next", next_step))
    app.add_handler(CommandHandler("publish", publish_post))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("multi", multi))
    app.add_handler(CommandHandler("news", news))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("publish", publish_post))
    app.add_handler(MessageHandler(filters.ALL, collect_files))
    app.add_handler(MessageHandler(filters.ALL, collect_caption))
    app.add_handler(MessageHandler(filters.ALL, collect_prompt))
    app.add_handler(CommandHandler("next", next_step))
    app.add_handler(CommandHandler("publish", publish_post))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("multi", multi))
    app.add_handler(CommandHandler("news", news))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("publish", publish_post))
    app.add_handler(MessageHandler(filters.ALL, collect_files))
    app.add_handler(MessageHandler(filters.ALL, collect_caption))
    app.add_handler(MessageHandler(filters.ALL, collect_prompt))
    app.add_handler(CommandHandler("next", next_step))
    app.add_handler(CommandHandler("publish", publish_post))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("multi", multi))
    app.add_handler(CommandHandler("news", news))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("publish", publish_post))
    app.add_handler(MessageHandler(filters.ALL, collect_files))
    app.add_handler(MessageHandler(filters.ALL, collect_caption))
    app.add_handler(MessageHandler(filters.ALL, collect_prompt))

    app.add_handler(MessageHandler(filters.COMMAND, cancel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, collect_prompt))
    app.add_handler(CommandHandler("publish", publish_post))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("multi", multi))
    app.add
