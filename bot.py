import os
import logging
import html
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    ConversationHandler,
)

# --- تنظیمات ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
YOUR_USER_ID = int(os.getenv("YOUR_USER_ID"))

# --- وضعیت‌ها ---
WAITING_FOR_FILE, WAITING_FOR_DESCRIPTION, WAITING_FOR_PROMPT, WAITING_FOR_FINAL = range(4)

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# --- دسترسی فقط برای تو ---
async def check_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != YOUR_USER_ID:
        await update.message.reply_text("❌ شما مجاز نیستید.")
        return False
    return True

# --- منوی اصلی ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_user(update, context):
        return ConversationHandler.END
    context.user_data.clear()
    keyboard = [[InlineKeyboardButton("📤 ارسال پیام با پرامپت", callback_data="start")]]
    await update.message.reply_text("فعالیت مورد نظر را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))
    return WAITING_FOR_FILE

# --- مرحله ۱: فایل یا بدون فایل؟ ---
async def ask_for_file(update: Update, context: Update):
    query = update.callback_query
    await query.answer()
    if query.data == "start":
        keyboard = [
            [InlineKeyboardButton("✅ آپلود فایل", callback_data="upload")],
            [InlineKeyboardButton("➡️ بدون محتوا", callback_data="no_file")]
        ]
        await query.edit_message_text("آیا محتوایی دارید؟", reply_markup=InlineKeyboardMarkup(keyboard))
        return WAITING_FOR_FILE
    return WAITING_FOR_FILE

# --- بدون محتوا → برو به توضیح ---
async def handle_no_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["files"] = []
    await query.edit_message_text("متن توضیح را وارد کنید (یا «بدون توضیح» را بزنید):", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("➡️ بدون توضیح", callback_data="no_desc")]
    ]))
    return WAITING_FOR_DESCRIPTION

# --- آپلود فایل ---
async def handle_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("فایل خود را ارسال کنید.")
    return WAITING_FOR_FILE

# --- دریافت فایل ---
async def receive_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_user(update, context):
        return ConversationHandler.END

    file = None
    if update.message.photo:
        file = update.message.photo[-1]
    elif update.message.document:
        file = update.message.document
    else:
        await update.message.reply_text("لطفاً فقط عکس یا فایل معتبر بفرستید.")
        return WAITING_FOR_FILE

    context.user_data["files"] = [file]
    await update.message.reply_text(
        "فایل ذخیره شد. ادامه؟",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➡️ ادامه", callback_data="go_to_desc")]])
    )
    return WAITING_FOR_FILE

# --- ادامه → برو به توضیح ---
async def go_to_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("متن توضیح را وارد کنید (یا «بدون توضیح» را بزنید):", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("➡️ بدون توضیح", callback_data="no_desc")]
    ]))
    return WAITING_FOR_DESCRIPTION

# --- بدون توضیح → برو به پرامپت ---
async def handle_no_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["description"] = ""
    await query.edit_message_text("پرامپت خود را وارد کنید:")
    return WAITING_FOR_PROMPT

# --- دریافت توضیح ---
async def receive_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["description"] = update.message.text
    await update.message.reply_text("پرامپت خود را وارد کنید:")
    return WAITING_FOR_PROMPT

# --- دریافت پرامپت ---
async def receive_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["prompt"] = update.message.text
    await update.message.reply_text(
        "توضیح پایانی (اختیاری)؟",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➡️ بدون توضیح پایانی", callback_data="no_final")]])
    )
    return WAITING_FOR_FINAL

# --- بدون توضیح پایانی → منتشر کن ---
async def handle_no_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["final_note"] = ""
    return await publish(update, context)

# --- دریافت توضیح پایانی ---
async def receive_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["final_note"] = update.message.text
    return await publish(update, context)

# --- انتشار ---
async def publish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    files = context.user_data.get("files", [])
    desc = context.user_data.get("description", "")
    prompt = context.user_data.get("prompt", "")
    final = context.user_data.get("final_note", "")

    try:
        # ارسال فایل (اگر وجود داشت)
        if files:
            file = files[0]
            if hasattr(file, 'file_unique_id') and not hasattr(file, 'file_name'):
                await context.bot.send_photo(chat_id=CHANNEL_ID, photo=file.file_id)
            else:
                await context.bot.send_document(chat_id=CHANNEL_ID, document=file.file_id)

        # ساخت متن
        parts = []
        if desc: parts.append(desc)
        parts.append(f"<pre>{html.escape(prompt)}</pre>")
        if final: parts.append(final)
        parts.append('🔗 منبع: <a href="https://t.me/hamedaf_ir">هوش مصنوعی با حامدافشاری</a>')
        text = "\n\n".join(parts)

        await context.bot.send_message(chat_id=CHANNEL_ID, text=text, parse_mode="HTML")
        await update.message.reply_text("✅ پست منتشر شد!")
        context.user_data.clear()
        return ConversationHandler.END

    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {e}")
        return ConversationHandler.END

# --- لغو ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ لغو شد.")
    return ConversationHandler.END

# --- راه‌اندازی ---
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            WAITING_FOR_FILE: [
                CallbackQueryHandler(ask_for_file, pattern="^start$"),
                CallbackQueryHandler(handle_upload, pattern="^upload$"),
                CallbackQueryHandler(handle_no_file, pattern="^no_file$"),
                CallbackQueryHandler(go_to_description, pattern="^go_to_desc$"),
                MessageHandler(filters.PHOTO | filters.Document.IMAGE, receive_file),
            ],
            WAITING_FOR_DESCRIPTION: [
                CallbackQueryHandler(handle_no_desc, pattern="^no_desc$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_description),
            ],
            WAITING_FOR_PROMPT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_prompt),
            ],
            WAITING_FOR_FINAL: [
                CallbackQueryHandler(handle_no_final, pattern="^no_final$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_final),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv)
    app.run_polling()

if __name__ == "__main__":
    main()
