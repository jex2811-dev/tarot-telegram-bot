from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os

TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привіт! Я Таро Бот 🔮")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))

if __name__ == "__main__":
    app.run_polling()
