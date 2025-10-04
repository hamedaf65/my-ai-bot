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

# --- دکمه تلاش مجدد ---
def get_retry_button():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 تلاش مجدد", callback_data="retry")]
    ])

# --- منوی اصلی ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_user(update, context):
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton("📤 ارسال پیام با پرامپت", callback_data="start_upload")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "فعالیت مورد نظر را انتخاب کنید:",
        reply_markup=reply_markup,
    )
    return WAITING_FOR_FILE

# --- مدیریت تلاش مجدد ---
async def handle_retry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await start(update, context)
    return WAITING_FOR_FILE

# --- مرحله 1: شروع آپلود ---
async def handle_file_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    if user_id != YOUR_USER_ID:
        await query.answer("❌ دسترسی غیرمجاز.", show_alert=True)
        return ConversationHandler.END

    await query.answer()

    if query.data == "start_upload":
        await query.edit_message_text(
            "لطفاً اولین فایل محتوا را ارسال کنید (تصویر، ویدیو، PDF و ...):",
            reply_markup=get_retry_button()
        )
        context.user_data["files"] = []
        context.user_data["descriptions"] = []
        context.user_data["prompts"] = []
        return WAITING_FOR_FILE
    elif query.data == "retry":
        context.user_data.clear()
        await start(update, context)
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
        await update.message.reply_text("لطفاً فقط عکس یا فایل معتبر ارسال کنید.")
        return WAITING_FOR_FILE

    context.user_data["files"].append(file)
    keyboard = [
        [InlineKeyboardButton("📤 آپلود فایل دیگر", callback_data="add_more")],
        [InlineKeyboardButton("➡️ ادامه (بدون فایل بیشتر)", callback_data="finish_files")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"فایل ذخیره شد. ({len(context.user_data['files'])} فایل)\n"
        "آیا فایل دیگری دارید؟",
        reply_markup=reply_markup
    )
    return WAITING_FOR_MORE_FILES

# --- تصمیم درباره فایل بیشتر ---
async def handle_more_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    if user_id != YOUR_USER_ID:
        await query.answer("❌ دسترسی غیرمجاز.", show_alert=True)
        return ConversationHandler.END

    await query.answer()
    if query.data == "add_more":
        await query.edit_message_text("لطفاً فایل بعدی را ارسال کنید:")
        return WAITING_FOR_FILE
    elif query.data == "finish_files":
        context.user_data["current_index"] = 0
        await ask_for_description_per_file(update, context)
        return WAITING_FOR_DESCRIPTION

# --- درخواست توضیح برای هر فایل ---
async def ask_for_description_per_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idx = context.user_data["current_index"]
    total = len(context.user_data["files"])
    text = f"📌 فایل {idx + 1} از {total}\n\nمتن توضیح برای این فایل را وارد کنید:"
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("➡️ بدون متن توضیح ادامه بده", callback_data="no_desc_per_file")],
        [InlineKeyboardButton("🔄 تلاش مجدد", callback_data="retry")]
    ])
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)

# --- بدون توضیح برای فایل فعلی ---
async def description_decision_per_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    idx = context.user_data["current_index"]
    context.user_data["descriptions"].append("")
    await ask_for_prompt_per_file(update, context)
    return WAITING_FOR_PROMPT

# --- دریافت توضیح برای فایل فعلی ---
async def receive_description_per_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idx = context.user_data["current_index"]
    context.user_data["descriptions"][idx] = update.message.text
    await ask_for_prompt_per_file(update, context)
    return WAITING_FOR_PROMPT

# --- درخواست پرامپت برای فایل فعلی ---
async def ask_for_prompt_per_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idx = context.user_data["current_index"]
    text = f"📌 فایل {idx + 1} از {len(context.user_data['files'])}\n\nلطفاً پرامپتی که با آن این محتوا تولید شده را وارد کنید:"
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 تلاش مجدد", callback_data="retry")]
    ])
    await update.message.reply_text(text, reply_markup=reply_markup)

# --- دریافت پرامپت برای فایل فعلی ---
async def receive_prompt_per_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idx = context.user_data["current_index"]
    context.user_data["prompts"][idx] = update.message.text

    # اگر فایل بعدی وجود داشت، برو به فایل بعدی
    if idx + 1 < len(context.user_data["files"]):
        context.user_data["current_index"] = idx + 1
        await ask_for_description_per_file(update, context)
        return WAITING_FOR_DESCRIPTION
    else:
        # همه فایل‌ها و پرامپت‌ها گرفته شدن — حالا توضیح پایانی
        text = "📌 توضیح پایانی (اختیاری):\n(مثلاً لینک بات، دعوت به اشتراک گذاری و ...)"
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("➡️ بدون توضیح پایانی", callback_data="no_final_note")],
            [InlineKeyboardButton("🔄 تلاش مجدد", callback_data="retry")]
        ])
        await update.message.reply_text(text, reply_markup=reply_markup)
        return WAITING_FOR_FINAL_NOTE

# --- بدون توضیح پایانی ---
async def final_note_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["final_note"] = ""
    await preview_and_publish(update, context)
    return ConversationHandler.END

# --- دریافت توضیح پایانی ---
async def receive_final_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["final_note"] = update.message.text
    await preview_and_publish(update, context)
    return ConversationHandler.END

# --- انتشار نهایی ---
async def preview_and_publish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    files = context.user_data.get("files", [])
    descriptions = context.user_data.get("descriptions", [])
    prompts = context.user_data.get("prompts", [])
    final_note = context.user_data.get("final_note", "")

    try:
        # اگر فقط یک عکس باشه → ارسال با caption (تا 1024 کاراکتر)
        if len(files) == 1 and hasattr(files[0], 'file_unique_id') and not hasattr(files[0], 'file_name'):
            # فقط یک عکس است
            desc = descriptions[0] if descriptions else ""
            prompt = prompts[0] if prompts else ""

            # ساخت متن caption
            final_parts = []
            if desc:
                final_parts.append(desc)
                final_parts.append("")

            # اگر طول متن کمتر از 1024 باشه، در caption قرار بده
            escaped_prompt = html.escape(prompt)
            blockquote = f"<blockquote>{escaped_prompt}</blockquote>"
            full_text = "\n".join(final_parts + [f"<pre>{escaped_prompt}</pre>", "", '🔗 منبع: <a href="https://t.me/hamedaf_ir">هوش مصنوعی با حامدافشاری</a>'])

            if len(full_text) <= 1024:
                # ارسال با caption
                await context.bot.send_photo(
                    chat_id=CHANNEL_ID,
                    photo=files[0].file_id,
                    caption=full_text,
                    parse_mode="HTML"
                )
            else:
                # ارسال بدون caption + متن جداگانه
                await context.bot.send_photo(chat_id=CHANNEL_ID, photo=files[0].file_id)
                await context.bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=full_text,
                    parse_mode="HTML"
                )

        else:
            # چند عکس یا فایل دیگر
            # ارسال آلبوم عکس (فقط عکس‌ها)
            photo_files = []
            for file in files:
                if hasattr(file, 'file_unique_id') and not hasattr(file, 'file_name'):
                    photo_files.append(InputMediaPhoto(media=file.file_id))

            if photo_files:
                await context.bot.send_media_group(chat_id=CHANNEL_ID, media=photo_files)

            # ساخت متن کامل با جعبه‌های سبز
            full_text_parts = []

            for i in range(len(descriptions)):
                desc = descriptions[i]
                prompt = prompts[i]
                if desc:
                    full_text_parts.append(desc)
                # جعبه سبز برای پرامپت
                escaped_prompt = html.escape(prompt)
                full_text_parts.append(f"<blockquote>{escaped_prompt}</blockquote>")
                full_text_parts.append("")  # خط خالی

            if final_note:
                full_text_parts.append(final_note)

            # اضافه کردن لینک کانال
            full_text_parts.append('🔗 منبع: <a href="https://t.me/hamedaf_ir">هوش مصنوعی با حامدافشاری</a>')

            full_text = "\n".join(full_text_parts)

            # ارسال متن کامل
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=full_text,
                parse_mode="HTML"
            )

        await update.message.reply_text("✅ پست با موفقیت در کانال منتشر شد!")
    except Exception as e:
        await update.message.reply_text(
            f"❌ خطا در انتشار: {str(e)}",
            reply_markup=get_retry_button()
        )
        return ConversationHandler.END

    return ConversationHandler.END

# --- لغو ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_user(update, context):
        return ConversationHandler.END
    await update.message.reply_text("❌ عملیات لغو شد.")
    return ConversationHandler.END

# --- راه‌اندازی ---
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            WAITING_FOR_FILE: [
                CallbackQueryHandler(handle_file_step, pattern="^(start_upload|retry)$"),
                MessageHandler(
                    filters.PHOTO | filters.Document.IMAGE,
                    receive_file
                ),
            ],
            WAITING_FOR_MORE_FILES: [
                CallbackQueryHandler(handle_more_files, pattern="^(add_more|finish_files)$"),
                CallbackQueryHandler(handle_retry, pattern="^retry$"),
            ],
            WAITING_FOR_DESCRIPTION: [
                CallbackQueryHandler(description_decision_per_file, pattern="^no_desc_per_file$"),
                CallbackQueryHandler(handle_retry, pattern="^retry$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_description_per_file),
            ],
            WAITING_FOR_PROMPT: [
                CallbackQueryHandler(handle_retry, pattern="^retry$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_prompt_per_file),
            ],
            WAITING_FOR_FINAL_NOTE: [
                CallbackQueryHandler(final_note_decision, pattern="^no_final_note$"),
                CallbackQueryHandler(handle_retry, pattern="^retry$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_final_note),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == "__main__":
    main()
