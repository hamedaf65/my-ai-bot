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
    WAITING_FOR_DESCRIPTION,
    WAITING_FOR_PROMPT,
) = range(3)

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

# --- دکمه تلاش مجدد ---
def get_retry_button():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 تلاش مجدد", callback_data="retry")]
    ])

# --- مدیریت تلاش مجدد ---
async def handle_retry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await start(update, context)
    return WAITING_FOR_FILE

# --- مرحله 1: فایل یا بدون فایل ---
async def handle_file_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    if user_id != YOUR_USER_ID:
        await query.answer("❌ دسترسی غیرمجاز.", show_alert=True)
        return ConversationHandler.END

    await query.answer()

    if query.data == "start_upload":
        keyboard = [
            [InlineKeyboardButton("✅ فایل دارم (ارسال کن)", callback_data="has_file")],
            [InlineKeyboardButton("❌ فایل ندارم (ادامه بدون فایل)", callback_data="no_file")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "آیا فایلی (تصویر، ویدیو، PDF، ZIP و ...) برای ارسال دارید؟",
            reply_markup=reply_markup,
        )
        return WAITING_FOR_FILE
    elif query.data == "retry":
        await start(update, context)
        return WAITING_FOR_FILE

# --- تصمیم درباره فایل ---
async def file_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    if user_id != YOUR_USER_ID:
        await query.answer("❌ دسترسی غیرمجاز.", show_alert=True)
        return ConversationHandler.END

    await query.answer()

    if query.data == "has_file":
        await query.edit_message_text(
            "لطفاً فایل محتوا را ارسال کنید:",
            reply_markup=get_retry_button()
        )
        return WAITING_FOR_FILE
    elif query.data == "no_file":
        context.user_data["file"] = None
        await ask_for_description(update, context)
        return WAITING_FOR_DESCRIPTION

# --- دریافت فایل ---
async def receive_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_user(update, context):
        return ConversationHandler.END

    file = None
    if update.message.document:
        file = update.message.document
    elif update.message.photo:
        file = update.message.photo[-1]
    elif update.message.video:
        file = update.message.video
    elif update.message.audio:
        file = update.message.audio
    elif update.message.animation:
        file = update.message.animation

    context.user_data["file"] = file
    await ask_for_description(update, context)
    return WAITING_FOR_DESCRIPTION

# --- درخواست توضیح ---
async def ask_for_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "متن توضیح در مورد محتوا را وارد کنید (یا اگر نمی‌خواهید، دکمه زیر را بزنید):"
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("➡️ بدون متن توضیح ادامه بده", callback_data="no_desc")],
        [InlineKeyboardButton("🔄 تلاش مجدد", callback_data="retry")]
    ])
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)

# --- بدون توضیح ---
async def description_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    if user_id != YOUR_USER_ID:
        await query.answer("❌ دسترسی غیرمجاز.", show_alert=True)
        return ConversationHandler.END

    await query.answer()
    context.user_data["description"] = ""
    await ask_for_prompt(update, context)
    return WAITING_FOR_PROMPT

# --- دریافت توضیح ---
async def receive_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_user(update, context):
        return ConversationHandler.END

    context.user_data["description"] = update.message.text
    await ask_for_prompt(update, context)
    return WAITING_FOR_PROMPT

# --- درخواست پرامپت ---
async def ask_for_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "لطفاً پرامپتی که با آن این محتوا تولید شده را وارد کنید:"
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 تلاش مجدد", callback_data="retry")]
    ])
    await update.message.reply_text(text, reply_markup=reply_markup)

# --- دریافت پرامپت ---
async def receive_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_user(update, context):
        return ConversationHandler.END

    context.user_data["prompt"] = update.message.text
    await preview_and_publish(update, context)
    return ConversationHandler.END

# --- انتشار نهایی ---
async def preview_and_publish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = context.user_data.get("file")
    desc = context.user_data.get("description", "")
    prompt = context.user_data.get("prompt", "")

    escaped_desc = html.escape(desc) if desc else ""
    escaped_prompt = html.escape(prompt)

    final_parts = []
    if escaped_desc:
        final_parts.append(escaped_desc)
        final_parts.append("")

    final_parts.append(f"<pre>{escaped_prompt}</pre>")
    final_parts.append("")
    final_parts.append('🔗 منبع: <a href="https://t.me/hamedaf_ir">هوش مصنوعی با حامدافشاری</a>')

    final_text = "\n".join(final_parts)

    try:
        if file is None:
            await context.bot.send_message(chat_id=CHANNEL_ID, text=final_text, parse_mode="HTML")
        else:
            if hasattr(file, 'file_unique_id') and not hasattr(file, 'file_name'):
                # عکس است
                await context.bot.send_photo(
                    chat_id=CHANNEL_ID,
                    photo=file.file_id,
                    caption=final_text,
                    parse_mode="HTML"
                )
            else:
                # سایر فایل‌ها
                if file.file_size > 50 * 1024 * 1024:
                    await update.message.reply_text("⚠️ فایل شما بیش از 50 مگابایت است.")
                    return ConversationHandler.END

                await context.bot.send_document(
                    chat_id=CHANNEL_ID,
                    document=file.file_id,
                    caption=final_text,
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
                CallbackQueryHandler(file_decision, pattern="^(has_file|no_file)$"),
                MessageHandler(
                    filters.Document.ALL | filters.PHOTO | filters.VIDEO | filters.AUDIO | filters.ANIMATION,
                    receive_file
                ),
            ],
            WAITING_FOR_DESCRIPTION: [
                CallbackQueryHandler(description_decision, pattern="^no_desc$"),
                CallbackQueryHandler(handle_retry, pattern="^retry$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_description),
            ],
            WAITING_FOR_PROMPT: [
                CallbackQueryHandler(handle_retry, pattern="^retry$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_prompt),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == "__main__":
    main()
