import os
import logging
import html
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
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

# --- دکمه‌های اصلی منو ---
def get_main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📰 پست خبری", callback_data="post_news")],
        [InlineKeyboardButton("📤 ارسال پیام با پرامپت (تکی)", callback_data="post_single")],
        [InlineKeyboardButton("📤 ارسال پیام با پرامپت (چندتایی)", callback_data="post_multiple")],
        [InlineKeyboardButton("❌ لغو تمام فرآیندها", callback_data="cancel_all")]
    ])

# --- لغو تمام فرآیندها ---
async def cancel_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.edit_message_text("✅ تمام داده‌ها پاک شد. برای شروع مجدد، یکی از گزینه‌ها را انتخاب کنید.", reply_markup=get_main_menu())
    return ConversationHandler.END

# --- شروع منو اصلی (بدون /start) ---
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_user(update, context):
        return ConversationHandler.END
    await update.message.reply_text(
        "لطفاً نوع پست مورد نظر خود را انتخاب کنید:",
        reply_markup=get_main_menu()
    )
    return ConversationHandler.END

# --- حالت 1: پست خبری ---
async def handle_post_news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    context.user_data["mode"] = "news"
    await query.edit_message_text(
        "آیا محتوای فایلی (عکس/فایل) دارید؟",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ بله", callback_data="has_file_news")],
            [InlineKeyboardButton("❌ خیر", callback_data="no_file_news")],
            [InlineKeyboardButton("❌ لغو", callback_data="cancel_all")]
        ])
    )
    return WAITING_FOR_FILE

# --- بدون فایل در حالت خبری ---
async def news_no_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "متن خبری را وارد کنید:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ لغو", callback_data="cancel_all")]
        ])
    )
    return WAITING_FOR_DESCRIPTION

# --- دریافت متن خبری ---
async def receive_news_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["description"] = update.message.text
    await publish_news(update, context)
    return ConversationHandler.END

# --- ارسال پست خبری ---
async def publish_news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    desc = context.user_data.get("description", "")
    try:
        await context.bot.send_message(chat_id=CHANNEL_ID, text=desc, parse_mode="HTML")
        await update.message.reply_text("✅ پست خبری با موفقیت ارسال شد!")
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {str(e)}")
    context.user_data.clear()

# --- با فایل در حالت خبری ---
async def news_has_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "لطفاً فایل محتوا را ارسال کنید:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ لغو", callback_data="cancel_all")]
        ])
    )
    return WAITING_FOR_FILE

# --- دریافت فایل در حالت خبری ---
async def receive_news_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = None
    if update.message.photo:
        file = update.message.photo[-1]
    elif update.message.document:
        file = update.message.document
    else:
        await update.message.reply_text("لطفاً فقط عکس یا فایل معتبر ارسال کنید.")
        return WAITING_FOR_FILE

    context.user_data["file"] = file
    await update.message.reply_text(
        "متن خبری را وارد کنید:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ لغو", callback_data="cancel_all")]
        ])
    )
    return WAITING_FOR_DESCRIPTION

# --- ارسال پست خبری با فایل ---
async def publish_news_with_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = context.user_data.get("file")
    desc = context.user_data.get("description", "")

    try:
        if hasattr(file, 'file_unique_id') and not hasattr(file, 'file_name'):
            await context.bot.send_photo(chat_id=CHANNEL_ID, photo=file.file_id, caption=desc, parse_mode="HTML")
        else:
            await context.bot.send_document(chat_id=CHANNEL_ID, document=file.file_id, caption=desc, parse_mode="HTML")
        await update.message.reply_text("✅ پست خبری با موفقیت ارسال شد!")
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {str(e)}")
    context.user_data.clear()

# --- حالت 2: ارسال پیام با پرامپت (تکی) ---
async def handle_post_single(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    context.user_data["mode"] = "single"
    await query.edit_message_text(
        "لطفاً فایل محتوا را ارسال کنید:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ لغو", callback_data="cancel_all")]
        ])
    )
    return WAITING_FOR_FILE

# --- دریافت فایل در حالت تکی ---
async def receive_single_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = None
    if update.message.photo:
        file = update.message.photo[-1]
    elif update.message.document:
        file = update.message.document
    else:
        await update.message.reply_text("لطفاً فقط عکس یا فایل معتبر ارسال کنید.")
        return WAITING_FOR_FILE

    context.user_data["file"] = file
    await update.message.reply_text(
        "متن توضیح را وارد کنید:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ لغو", callback_data="cancel_all")]
        ])
    )
    return WAITING_FOR_DESCRIPTION

# --- دریافت توضیح در حالت تکی ---
async def receive_single_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["description"] = update.message.text
    await update.message.reply_text(
        "پرامپت را وارد کنید:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ لغو", callback_data="cancel_all")]
        ])
    )
    return WAITING_FOR_PROMPT

# --- دریافت پرامپت در حالت تکی ---
async def receive_single_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["prompt"] = update.message.text
    await publish_single(update, context)
    return ConversationHandler.END

# --- ارسال پست تکی ---
async def publish_single(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = context.user_data.get("file")
    desc = context.user_data.get("description", "")
    prompt = context.user_data.get("prompt", "")

    try:
        escaped_prompt = html.escape(prompt)
        full_text_parts = []
        if desc:
            full_text_parts.append(desc)
        # اگر پرامپت کوتاه باشد، با فایل ارسال شود
        if len(escaped_prompt) <= 1024:
            if hasattr(file, 'file_unique_id') and not hasattr(file, 'file_name'):
                await context.bot.send_photo(
                    chat_id=CHANNEL_ID,
                    photo=file.file_id,
                    caption=f"{desc}\n\n<pre>{escaped_prompt}</pre>\n\n🔗 منبع: <a href='https://t.me/hamedaf_ir'>هوش مصنوعی با حامدافشاری</a>",
                    parse_mode="HTML"
                )
            else:
                await context.bot.send_document(
                    chat_id=CHANNEL_ID,
                    document=file.file_id,
                    caption=f"{desc}\n\n<pre>{escaped_prompt}</pre>\n\n🔗 منبع: <a href='https://t.me/hamedaf_ir'>هوش مصنوعی با حامدافشاری</a>",
                    parse_mode="HTML"
                )
        else:
            # اگر پرامپت بلند باشد، فایل جدا و پرامپت جدا ارسال شود
            if hasattr(file, 'file_unique_id') and not hasattr(file, 'file_name'):
                await context.bot.send_photo(chat_id=CHANNEL_ID, photo=file.file_id)
            else:
                await context.bot.send_document(chat_id=CHANNEL_ID, document=file.file_id)
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=f"{desc}\n\n<pre>{escaped_prompt}</pre>\n\n🔗 منبع: <a href='https://t.me/hamedaf_ir'>هوش مصنوعی با حامدافشاری</a>",
                parse_mode="HTML"
            )

        await update.message.reply_text("✅ پست با موفقیت ارسال شد!")
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {str(e)}")
    context.user_data.clear()

# --- حالت 3: ارسال پیام با پرامپت (چندتایی) ---
async def handle_post_multiple(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    context.user_data["mode"] = "multiple"
    context.user_data["files"] = []
    context.user_data["prompts"] = []
    context.user_data["descriptions"] = []
    await query.edit_message_text(
        "لطفاً اولین فایل محتوا را ارسال کنید:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ لغو", callback_data="cancel_all")]
        ])
    )
    return WAITING_FOR_FILE

# --- دریافت فایل در حالت چندتایی ---
async def receive_multiple_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        [InlineKeyboardButton("📤 آپلود فایل دیگر", callback_data="add_more_multiple")],
        [InlineKeyboardButton("➡️ ادامه", callback_data="finish_files_multiple")],
        [InlineKeyboardButton("❌ لغو", callback_data="cancel_all")]
    ]
    await update.message.reply_text(
        f"فایل ذخیره شد ({len(context.user_data['files'])} فایل). ادامه؟",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return WAITING_FOR_MORE_FILES

# --- اضافه کردن فایل بعدی در حالت چندتایی ---
async def add_more_multiple(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "فایل بعدی را ارسال کنید:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ لغو", callback_data="cancel_all")]
        ])
    )
    return WAITING_FOR_FILE

# --- اتمام ارسال فایل‌ها در حالت چندتایی ---
async def finish_files_multiple(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["current_index"] = 0
    await ask_for_description_multiple(update, context)
    return WAITING_FOR_DESCRIPTION

# --- درخواست توضیح در حالت چندتایی ---
async def ask_for_description_multiple(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idx = context.user_data["current_index"]
    total = len(context.user_data["files"])
    text = f"📌 فایل {idx + 1} از {total}\n\nمتن توضیح را وارد کنید:"
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("➡️ بدون توضیح", callback_data="no_desc_multiple")],
        [InlineKeyboardButton("❌ لغو", callback_data="cancel_all")]
    ]))
    return WAITING_FOR_DESCRIPTION

# --- بدون توضیح در حالت چندتایی ---
async def no_desc_multiple(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["descriptions"].append("")
    await ask_for_prompt_multiple(update, context)
    return WAITING_FOR_PROMPT

# --- دریافت توضیح در حالت چندتایی ---
async def receive_description_multiple(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["descriptions"].append(update.message.text)
    await ask_for_prompt_multiple(update, context)
    return WAITING_FOR_PROMPT

# --- درخواست پرامپت در حالت چندتایی ---
async def ask_for_prompt_multiple(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idx = context.user_data["current_index"]
    total = len(context.user_data["files"])
    text = f"📌 پرامپت برای فایل {idx + 1} از {total}:\n(پرامپت را وارد کنید)"
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("➡️ بدون پرامپت", callback_data="no_prompt_multiple")],
        [InlineKeyboardButton("➡️ ادامه (همه فایل‌ها یک پرامپت دارند)", callback_data="same_prompt_multiple")],
        [InlineKeyboardButton("❌ لغو", callback_data="cancel_all")]
    ]))
    return WAITING_FOR_PROMPT

# --- بدون پرامپت در حالت چندتایی ---
async def no_prompt_multiple(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["prompts"].append("")
    idx = context.user_data["current_index"]
    if idx + 1 < len(context.user_data["files"]):
        context.user_data["current_index"] += 1
        return await ask_for_description_multiple(update, context)
    else:
        return await publish_multiple(update, context)

# --- همه فایل‌ها یک پرامپت دارند ---
async def same_prompt_multiple(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "پرامپت مشترک را وارد کنید:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ لغو", callback_data="cancel_all")]
        ])
    )
    return WAITING_FOR_FINAL_NOTE

# --- دریافت پرامپت مشترک ---
async def receive_same_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = update.message.text
    for i in range(len(context.user_data["files"])):
        context.user_data["prompts"].append(prompt)
    return await publish_multiple(update, context)

# --- دریافت پرامپت جداگانه ---
async def receive_prompt_multiple(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["prompts"].append(update.message.text)
    idx = context.user_data["current_index"]
    if idx + 1 < len(context.user_data["files"]):
        context.user_data["current_index"] += 1
        return await ask_for_description_multiple(update, context)
    else:
        return await publish_multiple(update, context)

# --- ارسال پست چندتایی ---
async def publish_multiple(update: Update, context: ContextTypes.DEFAULT_TYPE):
    files = context.user_data.get("files", [])
    descriptions = context.user_data.get("descriptions", [])
    prompts = context.user_data.get("prompts", [])

    try:
        # ارسال آلبوم عکس
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

        full_text_parts.append('🔗 منبع: <a href="https://t.me/hamedaf_ir">هوش مصنوعی با حامدافشاری</a>')
        full_text = "\n".join(full_text_parts)

        await context.bot.send_message(chat_id=CHANNEL_ID, text=full_text, parse_mode="HTML")
        await update.message.reply_text("✅ پست با موفقیت ارسال شد!")
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {str(e)}")
    context.user_data.clear()

# --- راه‌اندازی ---
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # این دستور به جای /start، وقتی کاربر دکمه ۴ نقطه‌ای را لمس کرد، منو را نمایش می‌ده
    application.add_handler(MessageHandler(filters.COMMAND & filters.Regex(r'^/'), show_main_menu))

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, show_main_menu)],
        states={
            WAITING_FOR_FILE: [
                CallbackQueryHandler(handle_post_news, pattern="^post_news$"),
                CallbackQueryHandler(handle_post_single, pattern="^post_single$"),
                CallbackQueryHandler(handle_post_multiple, pattern="^post_multiple$"),
                CallbackQueryHandler(cancel_all, pattern="^cancel_all$"),
                MessageHandler(filters.PHOTO | filters.Document.IMAGE, receive_news_file),
                MessageHandler(filters.PHOTO | filters.Document.IMAGE, receive_single_file),
                MessageHandler(filters.PHOTO | filters.Document.IMAGE, receive_multiple_file),
            ],
            WAITING_FOR_MORE_FILES: [
                CallbackQueryHandler(add_more_multiple, pattern="^add_more_multiple$"),
                CallbackQueryHandler(finish_files_multiple, pattern="^finish_files_multiple$"),
                CallbackQueryHandler(cancel_all, pattern="^cancel_all$"),
            ],
            WAITING_FOR_DESCRIPTION: [
                CallbackQueryHandler(news_no_file, pattern="^no_file_news$"),
                CallbackQueryHandler(no_desc_multiple, pattern="^no_desc_multiple$"),
                CallbackQueryHandler(cancel_all, pattern="^cancel_all$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_news_text),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_single_description),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_description_multiple),
            ],
            WAITING_FOR_PROMPT: [
                CallbackQueryHandler(no_prompt_multiple, pattern="^no_prompt_multiple$"),
                CallbackQueryHandler(same_prompt_multiple, pattern="^same_prompt_multiple$"),
                CallbackQueryHandler(cancel_all, pattern="^cancel_all$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_single_prompt),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_prompt_multiple),
            ],
            WAITING_FOR_FINAL_NOTE: [
                CallbackQueryHandler(cancel_all, pattern="^cancel_all$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_same_prompt),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_all)],
    )

    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == "__main__":
    main()
