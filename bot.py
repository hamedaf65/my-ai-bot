# bot.py
import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes,
    ConversationHandler, CallbackQueryHandler
)

# ---------------- تنظیمات ----------------
TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
CHANNEL_ID = "@hamedaf_ir"  # آدرس کانال

# وضعیت‌ها
FILES, CAPTION = range(2)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# ---------------- منو ----------------
def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("📰 پست خبری", callback_data='news')],
        [InlineKeyboardButton("💬 پیام تکی", callback_data='single')],
        [InlineKeyboardButton("📚 پیام چندتایی", callback_data='multi')],
        [InlineKeyboardButton("❌ لغو", callback_data='cancel')]
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("🚫 فقط ادمین می‌تواند از این ربات استفاده کند.")
    await update.message.reply_text(
        "سلام حامد 👋\nاز منوی پایین یکی از گزینه‌ها را انتخاب کن:",
        reply_markup=get_main_menu()
    )

# ---------------- Callback دکمه‌ها ----------------
async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == 'news':
        return await news(update, context)
    elif data == 'single':
        return await single(update, context)
    elif data == 'multi':
        return await multi(update, context)
    elif data == 'cancel':
        return await cancel(update, context)

# ---------------- حالت پست خبری ----------------
async def news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.effective_message.reply_text("📤 لطفاً فایل یا فایل‌های پست خبری را ارسال کن.")
    return FILES

# ---------------- جمع‌آوری فایل ----------------
async def collect_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # بررسی نوع فایل
    file_id = None
    file_type = None

    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        file_type = "photo"
    elif update.message.document:
        file_id = update.message.document.file_id
        file_type = "document"
    elif update.message.video:
        file_id = update.message.video.file_id
        file_type = "video"
    elif update.message.audio:
        file_id = update.message.audio.file_id
        file_type = "audio"
    else:
        await update.message.reply_text("❌ این نوع فایل پشتیبانی نمی‌شود.")
        return FILES

    if "files" not in context.user_data:
        context.user_data["files"] = []
    context.user_data["files"].append({"id": file_id, "type": file_type})

    await update.message.reply_text("✅ فایل ذخیره شد. فایل بعدی را بفرست یا /next برای ادامه متن ارسال کن.")
    return FILES

async def next_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📝 حالا متن پست را ارسال کن.")
    return CAPTION

# ---------------- جمع‌آوری متن و ارسال ----------------
async def collect_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    text += "\n\n🧠 هوش مصنوعی با حامد افشاری\n🔗 https://t.me/hamedaf_ir"

    files = context.user_data.get("files", [])
    for f in files:
        if f["type"] == "photo":
            await context.bot.send_photo(chat_id=CHANNEL_ID, photo=f["id"], caption=text)
        elif f["type"] == "document":
            await context.bot.send_document(chat_id=CHANNEL_ID, document=f["id"], caption=text)
        elif f["type"] == "video":
            await context.bot.send_video(chat_id=CHANNEL_ID, video=f["id"], caption=text)
        elif f["type"] == "audio":
            await context.bot.send_audio(chat_id=CHANNEL_ID, audio=f["id"], caption=text)

    await update.message.reply_text("✅ پست به کانال ارسال شد.", reply_markup=get_main_menu())
    context.user_data.clear()
    return ConversationHandler.END

# ---------------- پیام تکی و چندتایی ----------------
async def single(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text("✳️ لطفاً فایل مورد نظر را ارسال کن.")
    return FILES

async def multi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text("📸 فایل‌ها را یکی‌یکی ارسال کن، بعد از اتمام /next را بزن.")
    return FILES

# ---------------- لغو ----------------
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.effective_message.reply_text("❌ تمام فرآیندها لغو شد.", reply_markup=get_main_menu())
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
            FILES: [
                MessageHandler(filters.ALL & ~filters.COMMAND, collect_files),
                CommandHandler("next", next_step)
            ],
            CAPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_caption)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(menu_callback))
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("cancel", cancel))

    print("🤖 Bot is running... (Press CTRL+C to stop)")
    app.run_polling()

if __name__ == "__main__":
    main()
