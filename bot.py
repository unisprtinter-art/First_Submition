import os
import logging
import google.generativeai as genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# ============================================================
#   الإعدادات - تجي من Environment Variables
# ============================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", "0"))
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

SYSTEM_PROMPT = """
أنت مساعد ذكي ومفيد.
جاوب بالعربي دائماً.
كن مختصراً ومفيداً.
إذا ما عرفت الجواب قل: سأتواصل معك قريباً.

--- أضف معلوماتك هنا ---
"""
# ============================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=SYSTEM_PROMPT
)

user_chats = {}


def get_user_chat(user_id: int):
    if user_id not in user_chats:
        user_chats[user_id] = model.start_chat(history=[])
    return user_chats[user_id]


async def get_ai_response(user_id: int, user_message: str) -> str:
    chat = get_user_chat(user_id)
    response = chat.send_message(user_message)
    return response.text


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أهلاً! كيف أقدر أساعدك؟ 😊")


async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    user_message = update.message.text
    username = f"@{user.username}" if user.username else user.first_name

    if user_id == ADMIN_CHAT_ID:
        return

    try:
        ai_reply = await get_ai_response(user_id, user_message)
    except Exception as e:
        ai_reply = "عذراً، صار خطأ. حاول مرة ثانية."
        logger.error(f"Gemini error: {e}")

    await update.message.reply_text(ai_reply)

    keyboard = [[InlineKeyboardButton("💬 رد على المستخدم", callback_data=f"reply_{user_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    admin_text = (
        f"📨 رسالة جديدة\n"
        f"👤 {username}\n"
        f"🆔 {user_id}\n"
        f"─────────────\n"
        f"💬 {user_message}\n"
        f"─────────────\n"
        f"🤖 رد البوت:\n{ai_reply}"
    )

    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=admin_text,
        reply_markup=reply_markup
    )


async def handle_reply_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    target_user_id = int(query.data.split("_")[1])
    context.user_data["replying_to"] = target_user_id

    await query.message.reply_text("✏️ اكتب ردك - راح يوصل للمستخدم مباشرة:")


async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id != ADMIN_CHAT_ID:
        return

    target_user_id = context.user_data.get("replying_to")

    if not target_user_id:
        return

    try:
        await context.bot.send_message(chat_id=target_user_id, text=update.message.text)
        await update.message.reply_text("✅ تم إرسال ردك!")
    except Exception as e:
        await update.message.reply_text(f"❌ فشل الإرسال: {e}")

    context.user_data.pop("replying_to", None)


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Chat(ADMIN_CHAT_ID) & ~filters.COMMAND,
        handle_admin_reply
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & ~filters.Chat(ADMIN_CHAT_ID),
        handle_user_message
    ))
    app.add_handler(CallbackQueryHandler(handle_reply_button, pattern="^reply_"))

    print("✅ البوت شغال...")
    app.run_polling()


if __name__ == "__main__":
    main()
