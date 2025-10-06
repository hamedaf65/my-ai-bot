# bot.py
# نسخه ویژه برای حامد افشاری ❤️
# ربات مدیریت پست تلگرام با پرامپت هوشمند و دکمه 📋 کپی پرامپت
# نسخه پایدار نهایی برای استقرار در Railway (بدون تداخل polling/webhook)

import os
import html
import urllib.parse
import logging
from telegram import (
    Update, InputMediaPhoto, InputMediaVideo, InputMediaDocument,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler
)

# ---------------- تنظیمات ----------------
TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
CHANNEL_ID = os.getenv("CHANNEL_ID")
BOT_USERNAME = os.getenv("BOT_USERNAME")

FILES, CAPTION, PROMPT = range(3)

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)

# ---------------- ساخت دکمه کپی پرامپت ----------------
def create_prompt_button(prompt_text):
    if not prompt_text:
        return None
    encoded_prompt = urllib.parse.quote(prompt_text)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 کپی پرامپت", url=f"https://t.me/{BOT_USERNAME}?start=prompt_{encoded_prompt}")]
    ])

# ---------------- /start ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    user_id = update.effective_user.id

    # اگر با لینک پرامپت وارد شده
    if args and args[0].startswith("prompt_"):
        prompt_text = urllib.parse.unquote(args[0][len("prompt_"):])
        await update.message.reply_text(
            f"🧠 <b>پرامپت آماده:</b>\n\n<code>{html.escape(prompt_text)}</code>\n\n📋 برای کپی، روی متن بالا لمس کن.",
            parse_mode="HTML"
        )
        return

    # /start برای همه مجاز است
    if user_id != ADMIN_ID:
        await update.message.reply_text(
            "👋 سلام!\n"
            "این ربات مخصوص مدیریت پست‌های هوش مصنوعی است.\n"
            "شما فقط می‌توانید از لینک‌های پرامپت استفاده کنید 📋"
        )
        return

    await update.message.reply_text(
        "سلام حامد 👋\n"
        "از منوی پایین یکی از گزینه‌ها رو انتخاب کن:\n\n"
        "📰 /news - پست خبری\n"
        "💬 /single - پست تکی با پرامپت\n"
        "📚 /multi - پست چندتایی با پرامپت\n"
        "❌ /cancel - لغو عملیات"
    )

# ---------------- پست خبری ----------------
async def news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    context.user_data.clear()
    await update.message.reply_text("🖼️ لطفاً فایل/عکس پست خبری را ارسال کن (اختیاری).")
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
    await update.message.reply_text("✅ فایل ذخیره شد یا /next را بزن.")
    return FILES

async def news_next(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📝 حالا متن پست خبری را بفرست.")
    return CAPTION

async def collect_news_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = update.message.text or ""
    files = context.user_data.get("files", [])
    caption += "\n\n🔗 <a href='https://t.me/hamedaf_ir'>هوش مصنوعی با حامد افشاری</a>"

    if files:
        media = []
        sent = False
        for ftype, fid in files:
            if ftype == "photo":
                media.append(InputMediaPhoto(fid, caption=caption if not sent else None, parse_mode="HTML"))
            elif ftype == "video":
                media.append(InputMediaVideo(fid, caption=caption if not sent else None, parse_mode="HTML"))
            elif ftype == "document":
                media.append(InputMediaDocument(fid, caption=caption if not sent else None, parse_mode="HTML"))
            sent = True
        await context.bot.send_media_group(CHANNEL_ID, media)
    else:
        await context.bot.send_message(CHANNEL_ID, caption, parse_mode="HTML")

    await update.message.reply_text("✅ پست خبری ارسال شد.")
    context.user_data.clear()
    return ConversationHandler.END

# ---------------- پست‌های تکی و چندتایی ----------------
async def single(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 فقط ادمین می‌تواند از این بخش استفاده کند.")
        return ConversationHandler.END
    context.user_data.clear()
    await update.message.reply_text("💬 فایل‌ها را ارسال کن (اختیاری).")
    return FILES

async def multi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 فقط ادمین می‌تواند از این بخش استفاده کند.")
        return ConversationHandler.END
    context.user_data.clear()
    await update.message.reply_text("📚 فایل‌ها را یکی‌یکی ارسال کن، سپس /next را بزن.")
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
    await update.message.reply_text("✅ فایل ذخیره شد یا /next را بزن.")
    return FILES

async def next_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📝 متن توضیحی پست را ارسال کن (اختیاری).")
    return CAPTION

async def collect_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["caption"] = update.message.text or ""
    await update.message.reply_text("🧠 پرامپت را بفرست (اختیاری).")
    return PROMPT

async def collect_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["prompt"] = update.message.text or ""
    files = context.user_data.get("files", [])
    caption = context.user_data.get("caption", "")
    prompt = context.user_data.get("prompt", "")

    total_length = len(caption) + len(prompt)
    keyboard = create_prompt_button(prompt)

    prompt_box = f"""
<blockquote style="background-color:#d0e7ff;padding:10px;border-radius:5px;">
<pre><code>{html.escape(prompt)}</code></pre>
</blockquote>
""" if prompt else ""

    final_caption = f"{caption}\n\n{prompt_box}\n\n🔗 <a href='https://t.me/hamedaf_ir'>هوش مصنوعی با حامد افشاری</a>"

    if total_length <= 1024:
        if files:
            sent = False
            media = []
            for ftype, fid in files:
                if ftype == "photo":
                    media.append(InputMediaPhoto(fid, caption=final_caption if not sent else None, parse_mode="HTML"))
                elif ftype == "video":
                    media.append(InputMediaVideo(fid, caption=final_caption if not sent else None, parse_mode="HTML"))
                elif ftype == "document":
                    media.append(InputMediaDocument(fid, caption=final_caption if not sent else None, parse_mode="HTML"))
                sent = True
            msg_list = await context.bot.send_media_group(CHANNEL_ID, media)
            if keyboard:
                await context.bot.edit_message_reply_markup(CHANNEL_ID, msg_list[0].message_id, reply_markup=keyboard)
        else:
            await context.bot.send_message(CHANNEL_ID, final_caption, parse_mode="HTML", reply_markup=keyboard)
    else:
        if files:
            media = [InputMediaPhoto(fid) if ftype == "photo"
                     else InputMediaVideo(fid) if ftype == "video"
                     else InputMediaDocument(fid)
                     for ftype, fid in files]
            await context.bot.send_media_group(CHANNEL_ID, media)
        await context.bot.send_message(CHANNEL_ID, final_caption, parse_mode="HTML", reply_markup=keyboard)

    await update.message.reply_text("✅ پست ارسال شد.")
    context.user_data.clear()
    return ConversationHandler.END

# ---------------- لغو ----------------
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ عملیات لغو شد.")
    return ConversationHandler.END

# ---------------- اجرای اصلی ----------------
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))

    news_conv = ConversationHandler(
        entry_points=[CommandHandler("news", news)],
        states={
            FILES: [MessageHandler(filters.ALL & ~filters.COMMAND, collect_news_files),
                    CommandHandler("next", news_next)],
            CAPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_news_caption)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    post_conv = ConversationHandler(
        entry_points=[CommandHandler("single", single), CommandHandler("multi", multi)],
        states={
            FILES: [MessageHandler(filters.ALL & ~filters.COMMAND, collect_files),
                    CommandHandler("next", next_step)],
            CAPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_caption)],
            PROMPT: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_prompt)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(news_conv)
    app.add_handler(post_conv)

    print("🤖 Bot is running... ✅")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
