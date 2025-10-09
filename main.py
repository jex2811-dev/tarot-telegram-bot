import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from gsheets_helper import add_user
from daily_card import get_daily_card, raccoon_interpretation_callback

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(
        user_id=str(user.id),
        username=user.username or "",
        first_name=user.first_name or "",
        referral_code="NONE"
    )
    reply_keyboard = [
        ["🃏 Карта дня", "Категорії розкладів"],
        ["Моя скринька 📦", "Як працює бот ❓"]
    ]
    markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)
    await update.message.reply_text(
        f"Привіт, {user.first_name or 'друже'}! Я Містичний Єнот — твій гід у світі Таро 🦝🔮\n\n"
        "Обери дію нижче 👇",
        reply_markup=markup
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "🃏 Карта дня":
        await get_daily_card(update, context)
    elif text == "Як працює бот ❓":
        await update.message.reply_text("Цей бот витягує карти Таро та дає тобі поради 😉")
    else:
        await update.message.reply_text("Оберіть команду з меню ⬇️")

def main():
    token = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(raccoon_interpretation_callback, pattern="^raccoon_interpretation$"))
    print("✅ Бот запущений!")
    app.run_polling()

if __name__ == "__main__":
    main()
