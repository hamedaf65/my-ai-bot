import os
import logging
import html
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
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
(
    WAITING_FOR_FILE,
    WAITING_FOR_MORE_FILES,
    WAITING_FOR_DESCRIPTION,
    WAITING_FOR_PROMPT,
    WAITING_FOR_FINAL_NOTE,
) = range(5)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# --- بررسی دسترسی ---
async def check_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != YOUR_USER_ID:
        await update.message.reply_text("❌ شما مجاز به استفاده از این ربات نیستید.")
        return False
    return True

# --- دکمه‌ها ---
def get_buttons(include_skip=False, skip_text="➡️ بدون محتوا"):
    buttons = []
    if include_skip:
        buttons.append([InlineKeyboardButton(skip_text, callback_data="skip")])
    buttons.extend([
        [InlineKeyboardButton("🔄 تلاش مجدد", callback_data="retry")],
        [InlineKeyboardButton("❌ لغو", callback_data="cancel_now")]
    ])
    return InlineKeyboardMarkup(buttons)

# --- شروع ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_user(update, context):
        return ConversationHandler.END
    context.user_data.clear()
    keyboard = [[InlineKeyboardButton("📤 ارسال پیام با پرامپت", callback_data="start_upload")]]
    await update.message.reply_text("فعالیت مورد نظر را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))
    return WAITING_FOR_FILE

# --- لغو ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_user(update, context):
        return ConversationHandler.END
    context.user_data.clear()
    await update.message.reply_text("❌ عملیات لغو شد. برای شروع مجدد /start را بزنید.")
    return ConversationHandler.END

async def cancel_via_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.edit_message_text("❌ عملیات لغو شد. برای شروع مجدد /start را بزنید.")
    return ConversationHandler.END

# --- شروع آپلود ---
async def handle_file_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "start_upload":
        await query.edit_message_text(
            "آیا محتوایی برای ارسال دارید؟",
            reply_markup=get_buttons(include_skip=True)
        )
        return WAITING_FOR_FILE
    elif query.data == "retry":
        return await start(update, context)
    elif query.data == "skip":
        # بدون محتوا → مستقیماً به توضیح پایانی برو
        context.user_data["files"] = []
        context.user_data["descriptions"] = [""]
        context.user_data["prompts"] = [""]
        return await ask_for_final_note(update, context)

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
        await update.message.reply_text("لطفاً فقط عکس یا فایل معتبر ارسال کنید.")
        return WAITING_FOR_FILE

    context.user_data["files"] = [file]
    keyboard = [
        [InlineKeyboardButton("📤 آپلود فایل دیگر", callback_data="add_more")],
        [InlineKeyboardButton("➡️ ادامه", callback_data="finish_files")],
        [InlineKeyboardButton("❌ لغو", callback_data="cancel_now")]
    ]
    await update.message.reply_text("فایل ذخیره شد.", reply_markup=InlineKeyboardMarkup(keyboard))
    return WAITING_FOR_MORE_FILES

# --- تصمیم درباره فایل بیشتر ---
async def handle_more_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "add_more":
        await query.edit_message_text("فایل بعدی را ارسال کنید:", reply_markup=get_buttons())
        return WAITING_FOR_FILE
    elif query.data == "finish_files":
        context.user_data["current_index"] = 0
        return await ask_for_description(update, context)
    elif query.data == "cancel_now":
        return await cancel_via_button(update, context)

# --- درخواست توضیح ---
async def ask_for_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idx = context.user_data["current_index"]
    total = len(context.user_data["files"])
    text = f"📌 فایل {idx + 1} از {total}\n\nمتن توضیح را وارد کنید:"
    await update.message.reply_text(text, reply_markup=get_buttons(include_skip=True, skip_text="➡️ بدون توضیح"))
    return WAITING_FOR_DESCRIPTION

# --- بدون توضیح ---
async def skip_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["descriptions"].append("")
    return await ask_for_prompt(update, context)

# --- دریافت توضیح ---
async def receive_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["descriptions"].append(update.message.text)
    return await ask_for_prompt(update, context)

# --- درخواست پرامپت ---
async def ask_for_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idx = context.user_data["current_index"]
    total = len(context.user_data["files"])
    text = f"📌 پرامپت برای فایل {idx + 1} از {total}:\n(پرامپت را وارد کنید)"
    await update.message.reply_text(text, reply_markup=get_buttons(include_skip=True, skip_text="➡️ بدون پرامپت"))
    return WAITING_FOR_PROMPT

# --- بدون پرامپت ---
async def skip_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["prompts"].append("")
    idx = context.user_data["current_index"]
    if idx + 1 < len(context.user_data["files"]):
        context.user_data["current_index"] += 1
        return await ask_for_description(update, context)
    else:
        return await ask_for_final_note(update, context)

# --- دریافت پرامپت ---
async def receive_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["prompts"].append(update.message.text)
    idx = context.user_data["current_index"]
    if idx + 1 < len(context.user_data["files"]):
        context.user_data["current_index"] += 1
        return await ask_for_description(update, context)
    else:
        return await ask_for_final_note(update, context)

# --- درخواست توضیح پایانی ---
async def ask_for_final_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "📌 توضیح پایانی (اختیاری):\n(مثل لینک بات یا CTA)"
    await update.message.reply_text(text, reply_markup=get_buttons(include_skip=True, skip_text="➡️ بدون توضیح پایانی"))
    return WAITING_FOR_FINAL_NOTE

# --- بدون توضیح پایانی → منتشر کن ---
async def skip_final_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["final_note"] = ""
    return await publish(update, context)

# --- دریافت توضیح پایانی ---
async def receive_final_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["final_note"] = update.message.text
    return await publish(update, context)

# --- انتشار نهایی ---
async def publish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    files = context.user_data.get("files", [])
    descriptions = context.user_data.get("descriptions", [])
    prompts = context.user_data.get("prompts", [])
    final_note = context.user_data.get("final_note", "")

    try:
        # ارسال آلبوم عکس (اگر وجود داشت)
        photos = [InputMediaPhoto(media=f.file_id) for f in files if hasattr(f, 'file_unique_id') and not hasattr(f, 'file_name')]
        if photos:
            await context.bot.send_media_group(chat_id=CHANNEL_ID, media=photos)

        # ساخت متن کامل
        full_text_parts = []
        for i in range(len(descriptions)):
            d = descriptions[i]
            p = prompts[i]
            if d.strip():
                full_text_parts.append(d)
            if p.strip():
                full_text_parts.append(f"<pre>{html.escape(p)}</pre>")
            full_text_parts.append("")

        if final_note.strip():
            full_text_parts.append(final_note)

        full_text_parts.append('🔗 منبع: <a href="https://t.me/hamedaf_ir">هوش مصنوعی با حامدافشاری</a>')
        full_text = "\n".join(full_text_parts)

        await context.bot.send_message(chat_id=CHANNEL_ID, text=full_text, parse_mode="HTML")
        await update.message.reply_text("✅ پست با موفقیت در کانال منتشر شد!")
        context.user_data.clear()
        return ConversationHandler.END

    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {str(e)}", reply_markup=get_buttons())
        return ConversationHandler.END

# --- راه‌اندازی ---
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            WAITING_FOR_FILE: [
                CallbackQueryHandler(handle_file_step, pattern="^(start_upload|retry|skip)$"),
                MessageHandler(filters.PHOTO | filters.Document.IMAGE, receive_file),
            ],
            WAITING_FOR_MORE_FILES: [
                CallbackQueryHandler(handle_more_files, pattern="^(add_more|finish_files|cancel_now)$"),
            ],
            WAITING_FOR_DESCRIPTION: [
                CallbackQueryHandler(skip_description, pattern="^skip$"),
                CallbackQueryHandler(cancel_via_button, pattern="^cancel_now$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_description),
            ],
            WAITING_FOR_PROMPT: [
                CallbackQueryHandler(skip_prompt, pattern="^skip$"),
                CallbackQueryHandler(cancel_via_button, pattern="^cancel_now$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_prompt),
            ],
            WAITING_FOR_FINAL_NOTE: [
                CallbackQueryHandler(skip_final_note, pattern="^skip$"),
                CallbackQueryHandler(cancel_via_button, pattern="^cancel_now$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_final_note),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("stop", cancel),
        ],
    )
    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()
