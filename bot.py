# bot.py
# نسخه ویژه برای حامد افشاری ❤️
# ربات مدیریت پست تلگرام با پشتیبانی از پرامپت چندتایی با چرخه توضیح ↔ پرامپت

import os
import html
import logging
import urllib.parse
from telegram import (
    Update, InputMediaPhoto, InputMediaVideo, InputMediaDocument, InlineKeyboardMarkup, InlineKeyboardButton
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
    caption_with_link = f"{caption}\n\n🔗 هوش مصنوعی با حامد افشاری"

    if files:
        media_group = []
        first_sent = False
        for ftype, fid in files:
            if ftype == "photo":
                media_group.append(InputMediaPhoto(fid, caption=caption_with_link if not first_sent else None))
            elif ftype == "video":
                media_group.append(InputMediaVideo(fid, caption=caption_with_link if not first_sent else None))
            elif ftype == "document":
                media_group.append(InputMediaDocument(fid, caption=caption_with_link if not first_sent else None))
            first_sent = True
        await context.bot.send_media_group(chat_id=CHANNEL_ID, media=media_group)
    else:
        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=caption_with_link,
            disable_web_page_preview=True
        )

    context.user_data.clear()
    await update.message.reply_text("✅ پست خبری ارسال شد!")
    return ConversationHandler.END


# ---------------- پیام تکی ----------------
async def single(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("🚫 فقط ادمین می‌تواند پست ارسال کند.")
    context.user_data.clear()
    await update.message.reply_text("💬 لطفاً فایل‌ها را ارسال کن (اختیاری).")
    return FILES


# ---------------- پیام چندتایی ----------------
async def multi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("🚫 فقط ادمین می‌تواند پست ارسال کند.")
    context.user_data.clear()
    context.user_data["prompts"] = []
    context.user_data["captions"] = []
    await update.message.reply_text("📚 فایل‌ها را یکی‌یکی ارسال کن، بعد از اتمام /next را بزن.")
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
    await update.message.reply_text("📝 لطفاً توضیح مربوط به این مرحله را بفرست.")
    return CAPTION


async def collect_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = update.message.text or ""
    context.user_data["captions"].append(caption)

    # بعد از هر توضیح می‌ره برای پرامپت
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Next", callback_data="next_prompt"),
         InlineKeyboardButton("🚀 Publish Post", callback_data="publish_post")]
    ])
    await update.message.reply_text("🧠 حالا پرامپت مربوط به این توضیح رو بفرست.", reply_markup=keyboard)
    return PROMPT


async def handle_prompt_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "publish_post":
        return await publish_post(query, context)
    elif query.data == "next_prompt":
        await query.edit_message_text("📝 لطفاً توضیح بعدی را بفرست.")
        return CAPTION


async def collect_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = update.message.text or ""
    context.user_data["prompts"].append(prompt)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Next", callback_data="next_prompt"),
         InlineKeyboardButton("🚀 Publish Post", callback_data="publish_post")]
    ])
    await update.message.reply_text("✅ پرامپت ذخیره شد. ادامه بده یا منتشر کن:", reply_markup=keyboard)
    return PROMPT


async def publish_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if isinstance(update, Update) and update.callback_query:
        query = update.callback_query
        await query.answer()
        user = query.from_user
        msg_func = query.message.reply_text
    else:
        user = update.effective_user
        msg_func = update.message.reply_text

    if user.id != ADMIN_ID:
        return await msg_func("🚫 فقط ادمین می‌تواند پست ارسال کند.")

    files = context.user_data.get("files", [])
    captions = context.user_data.get("captions", [])
    prompts = context.user_data.get("prompts", [])

    content = ""
    for i, (c, p) in enumerate(zip(captions, prompts), start=1):
        content += f"📝 <b>بخش {i}</b>\n{html.escape(c)}\n\n<pre><code>{html.escape(p)}</code></pre>\n\n"

    final_text = f"{content}\n🔗 هوش مصنوعی با حامد افشاری"

    if len(final_text) <= 1024 and files:
        first_sent = False
        media_group = []
        for ftype, fid in files:
            if ftype == "photo":
                media_group.append(InputMediaPhoto(fid, caption=final_text if not first_sent else None, parse_mode=ParseMode.HTML))
            elif ftype == "video":
                media_group.append(InputMediaVideo(fid, caption=final_text if not first_sent else None, parse_mode=ParseMode.HTML))
            elif ftype == "document":
                media_group.append(InputMediaDocument(fid, caption=final_text if not first_sent else None, parse_mode=ParseMode.HTML))
            first_sent = True
        await context.bot.send_media_group(chat_id=CHANNEL_ID, media=media_group)
    else:
        if files:
            await context.bot.send_media_group(chat_id=CHANNEL_ID, media=[InputMediaPhoto(fid) for _, fid in files])
        await context.bot.send_message(chat_id=CHANNEL_ID, text=final_text, parse_mode="HTML", disable_web_page_preview=True)

    context.user_data.clear()
    await msg_func("✅ پست نهایی ارسال شد!")
    return ConversationHandler.END


# ---------------- لغو ----------------
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ عملیات لغو شد و ربات ریست شد.")
    return ConversationHandler.END


# ---------------- اجرای اصلی ----------------
def main():
    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("single", single), CommandHandler("multi", multi)],
        states={
            FILES: [CommandHandler("next", next_step), MessageHandler(filters.ALL & ~filters.COMMAND, collect_files)],
            CAPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_caption)],
            PROMPT: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_prompt)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CallbackQueryHandler(handle_prompt_input))

    print("🤖 Bot is running... (Press CTRL+C to stop)")
    app.run_polling()


from telegram.ext import CallbackQueryHandler

if __name__ == "__main__":
    main()
