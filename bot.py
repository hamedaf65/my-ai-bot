import os
import html
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
YOUR_USER_ID = int(os.getenv("YOUR_USER_ID"))

async def check_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != YOUR_USER_ID:
        await update.message.reply_text("❌ شما مجاز نیستید.")
        return False
    return True

# --- منوی اصلی ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_user(update, context):
        return
    context.user_data.clear()
    keyboard = [
        [InlineKeyboardButton("📰 پست خبری", callback_data="news_main")],
        [InlineKeyboardButton("📤 پرامپت (تکی)", callback_data="single_main")],
        [InlineKeyboardButton("📤 پرامپت (چندتایی)", callback_data="multiple_main")],
        [InlineKeyboardButton("❌ لغو", callback_data="cancel")]
    ]
    if update.callback_query:
        await update.callback_query.edit_message_text("انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text("انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))

# --- مدیریت همه دکمه‌ها ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel":
        context.user_data.clear()
        await query.edit_message_text("❌ لغو شد.")
        return
    
    # بازگشت به منوی اصلی
    if query.data == "back_to_main":
        await start(update, context)
        return

    # مرحله اول: انتخاب نوع پست
    if query.data == "news_main":
        context.user_data["mode"] = "news"
        await query.edit_message_text(
            "آیا فایل دارید؟",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ بله", callback_data="news_has_file")],
                [InlineKeyboardButton("❌ خیر", callback_data="news_no_file")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
            ])
        )
    elif query.data == "single_main":
        context.user_data["mode"] = "single"
        await query.edit_message_text("فایل خود را ارسال کنید.")
    elif query.data == "multiple_main":
        context.user_data["mode"] = "multiple"
        context.user_data["files"] = []
        await query.edit_message_text("اولین فایل را ارسال کنید.")

    # مرحله دوم: پست خبری
    elif query.data == "news_has_file":
        context.user_data["news_file_required"] = True
        await query.edit_message_text("فایل خود را ارسال کنید.")
    elif query.data == "news_no_file":
        context.user_data["news_file_required"] = False
        await query.edit_message_text("متن خبری را وارد کنید.")

# --- دریافت فایل ---
async def file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_user(update, context):
        return
    
    file = None
    if update.message.photo:
        file = update.message.photo[-1]
    elif update.message.document:
        file = update.message.document
    else:
        await update.message.reply_text("فقط عکس یا فایل معتبر بفرستید.")
        return

    mode = context.user_data.get("mode")
    if mode == "news":
        context.user_data["file"] = file
        await update.message.reply_text("متن خبری را وارد کنید.")
    elif mode == "single":
        context.user_data["file"] = file
        await update.message.reply_text("متن را وارد کنید.")
    elif mode == "multiple":
        context.user_data["files"].append(file)
        await update.message.reply_text(
            f"فایل ذخیره شد ({len(context.user_data['files'])} فایل).\nادامه؟",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📤 آپلود فایل دیگر", callback_data="multiple_add")],
                [InlineKeyboardButton("➡️ ادامه", callback_data="multiple_finish")],
                [InlineKeyboardButton("❌ لغو", callback_data="cancel")]
            ])
        )

# --- مدیریت فایل‌های چندتایی ---
async def multiple_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "multiple_add":
        await query.edit_message_text("فایل بعدی را ارسال کنید.")
    elif query.data == "multiple_finish":
        context.user_data["step"] = "text"
        await query.edit_message_text("متن را وارد کنید.")

# --- دریافت متن ---
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_user(update, context):
        return
    
    text = update.message.text
    mode = context.user_data.get("mode")
    
    try:
        if mode == "news":
            file = context.user_data.get("file")
            if file:
                if hasattr(file, 'file_unique_id') and not hasattr(file, 'file_name'):
                    await context.bot.send_photo(CHANNEL_ID, photo=file.file_id, caption=text)
                else:
                    await context.bot.send_document(CHANNEL_ID, document=file.file_id, caption=text)
            else:
                await context.bot.send_message(CHANNEL_ID, text=text)
        elif mode == "single":
            file = context.user_data.get("file")
            if file:
                if hasattr(file, 'file_unique_id') and not hasattr(file, 'file_name'):
                    await context.bot.send_photo(CHANNEL_ID, photo=file.file_id)
                else:
                    await context.bot.send_document(CHANNEL_ID, document=file.file_id)
            await context.bot.send_message(
                CHANNEL_ID,
                text=f"<pre>{html.escape(text)}</pre>\n\n🔗 منبع: <a href='https://t.me/hamedaf_ir'>هوش مصنوعی با حامدافشاری</a>",
                parse_mode="HTML"
            )
        elif mode == "multiple":
            files = context.user_data.get("files", [])
            for f in files:
                if hasattr(f, 'file_unique_id') and not hasattr(f, 'file_name'):
                    await context.bot.send_photo(CHANNEL_ID, photo=f.file_id)
                else:
                    await context.bot.send_document(CHANNEL_ID, document=f.file_id)
            await context.bot.send_message(
                CHANNEL_ID,
                text=f"<pre>{html.escape(text)}</pre>\n\n🔗 منبع: <a href='https://t.me/hamedaf_ir'>هوش مصنوعی با حامدافشاری</a>",
                parse_mode="HTML"
            )
        
        await update.message.reply_text("✅ ارسال شد!")
        context.user_data.clear()
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {str(e)}")

# --- راه‌اندازی ---
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(CallbackQueryHandler(multiple_handler, pattern="^multiple_"))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, file_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
