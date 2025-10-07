# bot.py
# نسخه ویژه برای حامد افشاری ❤️
# ربات مدیریت پست تلگرام با پشتیبانی فایل‌های مختلف و پرامپت هوشمند + دکمه 📋 کپی پرامپت
# نسخه‌ی نهایی اصلاح‌شده (فقط تغییرات در بخش multi برای چرخهٔ چندپرامپت)

import os
import html
import logging
import urllib.parse
from telegram import (
    Update, InputMediaPhoto, InputMediaVideo, InputMediaDocument,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler, CallbackQueryHandler
)

# ---------------- تنظیمات اصلی ----------------
TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
CHANNEL_ID = os.getenv("CHANNEL_ID")  # آیدی عددی کانال
BOT_USERNAME = os.getenv("BOT_USERNAME")  # مثلاً: hamedaf_bot

FILES, CAPTION, PROMPT = range(3)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# ---------------- تابع ساخت دکمه کپی پرامپت ----------------
def create_prompt_button(prompt_text):
    if not prompt_text:
        return None
    encoded_prompt = urllib.parse.quote(prompt_text)
    # لینک باز به ربات با پارامتر start
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 کپی پرامپت", url=f"https://t.me/{BOT_USERNAME}?start=prompt_{encoded_prompt}")]
    ])

# ---------------- دستور /start ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    user_id = update.effective_user.id

    # 🔹 اگر از لینک پرامپت وارد شد → مجاز برای همه
    if args and args[0].startswith("prompt_"):
        prompt_text = urllib.parse.unquote(args[0][len("prompt_"):])
        await update.message.reply_text(
            f"🧠 <b>پرامپت آماده:</b>\n\n<code>{html.escape(prompt_text)}</code>\n\n📋 برای کپی، روی متن بالا لمس کن.",
            parse_mode="HTML"
        )
        return

    # 🔒 فقط ادمین اجازه دارد از سایر دستورات استفاده کند
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

# ---------------- محدودسازی عمومی ----------------
def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("🚫 فقط ادمین می‌تواند از این دستور استفاده کند.")
            return ConversationHandler.END
        return await func(update, context)
    return wrapper

# ---------------- پست خبری ----------------
@admin_only
async def news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("🖼️ لطفاً فایل یا عکس‌های پست خبری را ارسال کن (اختیاری).")
    return FILES

@admin_only
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

@admin_only
async def news_next(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📝 حالا متن پست را ارسال کن (اختیاری).")
    return CAPTION

@admin_only
async def collect_news_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = update.message.text or ""
    files = context.user_data.get("files", [])

    caption_with_link = f"{caption}\n\n🔗 <a href='https://t.me/hamedaf_ir'>هوش مصنوعی با حامد افشاری</a>"

    if files:
        media_group = []
        first_sent = False
        for ftype, fid in files:
            if ftype == "photo":
                media_group.append(InputMediaPhoto(fid, caption=caption_with_link if not first_sent else None, parse_mode=ParseMode.HTML))
                first_sent = True
            elif ftype == "video":
                media_group.append(InputMediaVideo(fid, caption=caption_with_link if not first_sent else None, parse_mode=ParseMode.HTML))
                first_sent = True
            elif ftype == "document":
                media_group.append(InputMediaDocument(fid, caption=caption_with_link if not first_sent else None, parse_mode=ParseMode.HTML))
                first_sent = True
        await context.bot.send_media_group(chat_id=CHANNEL_ID, media=media_group)
    else:
        if caption:
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=caption_with_link,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )

    context.user_data.clear()
    await update.message.reply_text("✅ پست خبری ارسال شد!")
    return ConversationHandler.END

# ---------------- پیام تکی و چندتایی ----------------
@admin_only
async def single(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # حالت تکی — رفتار همانند قبل
    context.user_data.clear()
    # مشخص کنیم multi_mode خاموش است (تا collect_prompt شعبهٔ single را اجرا کند)
    context.user_data["multi_mode"] = False
    await update.message.reply_text("💬 لطفاً فایل‌ها را ارسال کن (اختیاری).")
    return FILES

@admin_only
async def multi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # حالت چندتایی — تنها این تابع را تغییر دادیم تا حالت multi_mode روشن شود
    context.user_data.clear()
    context.user_data["multi_mode"] = True
    context.user_data["segments"] = []  # لیستی از {'desc':..., 'prompt':...}
    await update.message.reply_text("📚 فایل‌ها را یکی‌یکی ارسال کن، بعد از اتمام /next را بزن.")
    return FILES

@admin_only
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

@admin_only
async def next_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # شروع مرحلهٔ توضیحات (CAPTION). برای multi این بعد از فایل‌ها اجرا می‌شود.
    await update.message.reply_text("📝 حالا متن توضیحی پست را ارسال کن (اختیاری).")
    return CAPTION

@admin_only
async def collect_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # در حالت multi ما توضیح فعلی را در current_desc نگه می‌داریم تا با پرامپت جفت شود
    if context.user_data.get("multi_mode"):
        context.user_data["current_desc"] = update.message.text or ""
    else:
        context.user_data["caption"] = update.message.text or ""
    await update.message.reply_text("🧠 پرامپت را ارسال کن (اختیاری).")
    return PROMPT

# ---------- جدید: handler ها برای حالت multi (Publish / Next) ----------
@admin_only
async def collect_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اگر در حالت multi هستیم: پرامپت را ذخیره کن و دکمه‌های Publish / Next را نمایش بده.
       در غیر اینصورت: رفتار قدیمی (single) را اجرا کن."""
    text = update.message.text or ""
    if context.user_data.get("multi_mode"):
        # multi: ذخیرهٔ جفت توضیح فعلی و پرامپت
        desc = context.user_data.pop("current_desc", "")
        if "segments" not in context.user_data:
            context.user_data["segments"] = []
        context.user_data["segments"].append({"desc": desc, "prompt": text})

        # دکمه‌های Publish و Next
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 Publish Post", callback_data="publish_post")],
            [InlineKeyboardButton("➡️ Next", callback_data="next_prompt")]
        ])

        await update.message.reply_text("✅ پرامپت ذخیره شد. می‌تونی Publish بزن یا با Next ادامه بدی.", reply_markup=keyboard)
        # منتظر اکشن دکمه‌ها بمان (در همان حالت PROMPT)
        return PROMPT

    # ↪️ شاخهٔ single (رفتار قبلی)
    # (کد زیر کپی مستقیم از نسخهٔ قبلیِ collect_prompt برای حالت single)
    context.user_data["prompt"] = text or ""
    files = context.user_data.get("files", [])
    caption = context.user_data.get("caption", "")
    prompt = context.user_data.get("prompt", "")

    total_length = len(caption) + len(prompt)
    keyboard = create_prompt_button(prompt)

    # 🔷 جعبه آبی پرامپت
    prompt_box = f"""
<blockquote expandable style="background-color:#d0e7ff;padding:10px;border-radius:5px;">
<pre><code>{html.escape(prompt)}</code></pre>
</blockquote>
""" if prompt else ""

    final_caption = f"{caption}\n\n{prompt_box}\n\n🔗 <a href='https://t.me/hamedaf_ir'>هوش مصنوعی با حامد افشاری</a>"

    if total_length <= 1024:  # کپشن کوتاه → همه در یک پست
        if files:
            first_sent = False
            media_group = []
            for ftype, fid in files:
                if ftype == "photo":
                    media_group.append(InputMediaPhoto(fid, caption=final_caption if not first_sent else None, parse_mode=ParseMode.HTML))
                    first_sent = True
                elif ftype == "video":
                    media_group.append(InputMediaVideo(fid, caption=final_caption if not first_sent else None, parse_mode=ParseMode.HTML))
                    first_sent = True
                elif ftype == "document":
                    media_group.append(InputMediaDocument(fid, caption=final_caption if not first_sent else None, parse_mode=ParseMode.HTML))
                    first_sent = True

            msg_list = await context.bot.send_media_group(chat_id=CHANNEL_ID, media=media_group)
            if keyboard:
                try:
                    await context.bot.edit_message_reply_markup(CHANNEL_ID, msg_list[0].message_id, reply_markup=keyboard)
                except Exception:
                    # اگر نتوانستیم کیبورد را الصاق کنیم، متن جدا با کیبورد بفرست
                    if keyboard:
                        await context.bot.send_message(chat_id=CHANNEL_ID, text="📋 کپی پرامپت:", reply_markup=keyboard)
        else:
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=final_caption,
                parse_mode="HTML",
                disable_web_page_preview=True,
                reply_markup=keyboard
            )

    else:  # کپشن طولانی → فایل جدا، متن جدا
        if files:
            media_group = []
            for ftype, fid in files:
                if ftype == "photo":
                    media_group.append(InputMediaPhoto(fid))
                elif ftype == "video":
                    media_group.append(InputMediaVideo(fid))
                elif ftype == "document":
                    media_group.append(InputMediaDocument(fid))
            await context.bot.send_media_group(chat_id=CHANNEL_ID, media=media_group)

        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=final_caption,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=keyboard
        )

    context.user_data.clear()
    await update.message.reply_text("✅ پست ارسال شد!")
    return ConversationHandler.END

# ---------- CallbackQuery handlers برای multi ----------
@admin_only
async def handle_next_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """وقتی Next زده شد: به مرحلهٔ دریافت توضیح بعدی برو."""
    query = update.callback_query
    await query.answer()
    # از کاربر بخواه توضیح بعدی را ارسال کند
    await query.message.reply_text("📝 لطفاً متن توضیحی بعدی را ارسال کن.")
    return CAPTION

@admin_only
async def handle_publish_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """وقتی Publish زده شد: همهٔ اجزا را جمع کن و به کانال ارسال کن."""
    query = update.callback_query
    await query.answer()

    segments = context.user_data.get("segments", [])
    files = context.user_data.get("files", [])
    # ساخت متن نهایی از تمام جفت‌های توضیح/پرامپت
    parts = []
    for idx, seg in enumerate(segments, start=1):
        desc = seg.get("desc", "")
        prompt = seg.get("prompt", "")
        if desc:
            parts.append(desc)
        if prompt:
            prompt_box = f"\n<blockquote expandable style=\"background-color:#d0e7ff;padding:10px;border-radius:5px;\"><pre><code>{html.escape(prompt)}</code></pre></blockquote>\n"
            parts.append(prompt_box)

    final_caption = "\n\n".join(parts).strip()

    # اگر متن خالی بود، حداقلیست قرار بده
    if not final_caption:
        final_caption = " "  # نباشه خالی بفرسته

    # ساخت کیبورد برای کپی هر پرامپت (هر پرامپت یک دکمه)
    prompt_buttons = []
    for idx, seg in enumerate(segments, start=1):
        p = seg.get("prompt", "")
        if p:
            encoded = urllib.parse.quote(p)
            prompt_buttons.append([InlineKeyboardButton(f"📋 کپی پرامپت {idx}", url=f"https://t.me/{BOT_USERNAME}?start=prompt_{encoded}")])

    keyboard = InlineKeyboardMarkup(prompt_buttons) if prompt_buttons else None

    # ارسال فایل‌ها (بدون قرار دادن لینک تبلیغ در caption فایل تا از preview جلوگیری شود)
    if files:
        media_group = []
        first_sent = False
        for ftype, fid in files:
            if ftype == "photo":
                media_group.append(InputMediaPhoto(fid, caption=final_caption if not first_sent else None, parse_mode=ParseMode.HTML if not first_sent else None))
                first_sent = True
            elif ftype == "video":
                media_group.append(InputMediaVideo(fid, caption=final_caption if not first_sent else None, parse_mode=ParseMode.HTML if not first_sent else None))
                first_sent = True
            elif ftype == "document":
                media_group.append(InputMediaDocument(fid, caption=final_caption if not first_sent else None, parse_mode=ParseMode.HTML if not first_sent else None))
                first_sent = True

        # اگر محتوای چندتایی داریم: برای اطمینان از عدم ایجاد preview، بهتر است caption جدا ارسال کنیم
        try:
            await context.bot.send_media_group(chat_id=CHANNEL_ID, media=media_group)
        except Exception:
            # اگر خطا شد، سعی کن فایل‌ها را یکی‌یکی ارسال کنی (فقط برای مقاومت)
            for item in media_group:
                if isinstance(item, InputMediaPhoto):
                    await context.bot.send_photo(chat_id=CHANNEL_ID, photo=item.media)
                elif isinstance(item, InputMediaVideo):
                    await context.bot.send_video(chat_id=CHANNEL_ID, video=item.media)
                elif isinstance(item, InputMediaDocument):
                    await context.bot.send_document(chat_id=CHANNEL_ID, document=item.media)

        # سپس متن نهایی را جدا بفرست (با کیبورد کپی پرامپت‌ها)
        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=final_caption,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=keyboard
        )
    else:
        # بدون فایل، متن را مستقیم با کیبورد بفرست
        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=final_caption,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=keyboard
        )

    # ارسال تبلیغِ آخر به صورت یک خط و بدون پیش‌نمایش (تا هیچ عکس پروفایلی نمایش داده نشود)
    try:
        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text="🔗 https://t.me/hamedaf_ir",
            disable_web_page_preview=True
        )
    except Exception:
        # اگر خطا شد (به هر دلیلی)، ایمیل کوتاه یا متن جایگزین بفرست
        try:
            await context.bot.send_message(chat_id=CHANNEL_ID, text="🔗 هوش مصنوعی با حامد افشاری")
        except Exception:
            pass

    # پایان و پاکسازی
    context.user_data.clear()
    await query.message.reply_text("✅ پست منتشر شد!")
    return ConversationHandler.END

# ---------------- لغو و ریست کامل ----------------
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ عملیات لغو شد و ربات ریست شد.")
    return ConversationHandler.END

# ---------------- اجرای اصلی ----------------
def main():
    app = Application.builder().token(TOKEN).build()

    # --- بخش خبری ---
    news_handler = ConversationHandler(
        entry_points=[CommandHandler("news", news)],
        states={
            FILES: [
                CommandHandler("next", news_next),
                MessageHandler(filters.ALL & ~filters.COMMAND, collect_news_files)
            ],
            CAPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_news_caption)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # --- پست با پرامپت ---
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("single", single),
            CommandHandler("multi", multi)
        ],
        states={
            FILES: [
                CommandHandler("next", next_step),
                MessageHandler(filters.ALL & ~filters.COMMAND, collect_files)
            ],
            CAPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_caption)],
            PROMPT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, collect_prompt),
                CallbackQueryHandler(handle_publish_post, pattern="^publish_post$"),
                CallbackQueryHandler(handle_next_prompt, pattern="^next_prompt$")
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(news_handler)
    app.add_handler(conv_handler)

    print("🤖 Bot is running... (Press CTRL+C to stop)")
    app.run_polling()

if __name__ == "__main__":
    main()
