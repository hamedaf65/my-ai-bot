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
) = range(4)

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
        context.user_data["prompts"] = []  # ذخیره پرامپت‌ها
        context.user_data["descriptions"] = []  # ذخیره توضیحات
        return WAITING_FOR_FILE
    elif query.data == "retry":
        context.user_data.clear()
        await start(update, context)
        return WAITING_FOR_FILE

# --- دریافت فایل اول یا بعدی ---
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

    if file:
        context.user_data["files"].append(file)
        context.user_data["descriptions"].append("")  # توضیح اولیه خالی
        context.user_data["prompts"].append("")      # پرامپت اولیه خالی

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
    else:
        await update.message.reply_text("لطفاً یک فایل معتبر ارسال کنید.")
        return WAITING_FOR_FILE

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
        # اگر فقط یک فایل بود، مستقیماً به توضیح برو
        if len(context.user_data["files"]) == 1:
            await ask_for_description(update, context)
            return WAITING_FOR_DESCRIPTION
        else:
            # اگر چند فایل بود، برای هر فایل توضیح و پرامپت بگیر
            context.user_data["current_index"] = 0
            await ask_for_description_per_file(update, context)
            return WAITING_FOR_DESCRIPTION

# --- درخواست توضیح برای هر فایل ---
async def ask_for_description_per_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    index = context.user_data.get("current_index", 0)
    total = len(context.user_data["files"])
    text = f"📌 فایل {index + 1} از {total}\n\nمتن توضیح برای این فایل را وارد کنید:"
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
    user_id = query.from_user.id
    if user_id != YOUR_USER_ID:
        await query.answer("❌ دسترسی غیرمجاز.", show_alert=True)
        return ConversationHandler.END

    await query.answer()
    index = context.user_data.get("current_index", 0)
    context.user_data["descriptions"][index] = ""
    await ask_for_prompt_per_file(update, context)
    return WAITING_FOR_PROMPT

# --- دریافت توضیح برای فایل فعلی ---
async def receive_description_per_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_user(update, context):
        return ConversationHandler.END

    index = context.user_data.get("current_index", 0)
    context.user_data["descriptions"][index] = update.message.text
    await ask_for_prompt_per_file(update, context)
    return WAITING_FOR_PROMPT

# --- درخواست پرامپت برای فایل فعلی ---
async def ask_for_prompt_per_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    index = context.user_data.get("current_index", 0)
    text = f"📌 فایل {index + 1} از {len(context.user_data['files'])}\n\nلطفاً پرامپتی که با آن این محتوا تولید شده را وارد کنید:"
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 تلاش مجدد", callback_data="retry")]
    ])
    await update.message.reply_text(text, reply_markup=reply_markup)

# --- دریافت پرامپت برای فایل فعلی ---
async def receive_prompt_per_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_user(update, context):
        return ConversationHandler.END

    index = context.user_data.get("current_index", 0)
    context.user_data["prompts"][index] = update.message.text

    # اگر فایل بعدی وجود داشت، برو به فایل بعدی
    if index + 1 < len(context.user_data["files"]):
        context.user_data["current_index"] = index + 1
        await ask_for_description_per_file(update, context)
        return WAITING_FOR_DESCRIPTION
    else:
        # همه فایل‌ها و پرامپت‌ها گرفته شدن — حالا منتشر کن
        await preview_and_publish(update, context)
        return ConversationHandler.END

# --- انتشار نهایی ---
async def preview_and_publish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    files = context.user_data.get("files", [])
    descriptions = context.user_data.get("descriptions", [])
    prompts = context.user_data.get("prompts", [])

    try:
        for i in range(len(files)):
            file = files[i]
            desc = descriptions[i]
            prompt = prompts[i]

            # ارسال عکس
            if hasattr(file, 'file_unique_id') and not hasattr(file, 'file_name'):
                sent_photo = await context.bot.send_photo(
                    chat_id=CHANNEL_ID,
                    photo=file.file_id,
                    caption=desc if desc else "",
                    parse_mode="HTML"
                )
            else:
                if file.file_size > 50 * 1024 * 1024:
                    await update.message.reply_text(f"⚠️ فایل {i+1} بیش از 50 مگابایت است.")
                    continue
                sent_document = await context.bot.send_document(
                    chat_id=CHANNEL_ID,
                    document=file.file_id,
                    caption=desc if desc else "",
                    parse_mode="HTML"
                )

            # ارسال پرامپت در جعبه سبز (blockquote)
            escaped_prompt = html.escape(prompt)
            blockquote = f"<blockquote>{escaped_prompt}</blockquote>"
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=blockquote,
                parse_mode="HTML"
            )

        # ارسال لینک منبع در آخر
        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text='🔗 منبع: <a href="https://t.me/hamedaf_ir">هوش مصنوعی با حامدافشاری</a>',
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
                    filters.Document.ALL | filters.PHOTO | filters.VIDEO | filters.AUDIO | filters.ANIMATION,
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
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == "__main__":
    main()
