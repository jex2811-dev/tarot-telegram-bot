#!/usr/bin/env python3
"""Entry point for the Tarot Telegram bot."""
from __future__ import annotations

import logging
import os
from typing import Final

from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from daily_card import get_daily_card, raccoon_interpretation_callback
from gsheets_helper import add_user

LOGGER: Final[logging.Logger] = logging.getLogger(__name__)
REPLY_KEYBOARD: Final[list[list[str]]] = [
    ["🃏 Карта дня", "Категорії розкладів"],
    ["Моя скринька 📦", "Як працює бот ❓"],
]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Register a new user and show the reply keyboard."""
    user = update.effective_user

    add_user(
        user_id=str(user.id),
        username=user.username or "",
        first_name=user.first_name or "",
        referral_code="NONE",
    )

    markup = ReplyKeyboardMarkup(REPLY_KEYBOARD, resize_keyboard=True)

    await update.message.reply_text(
        f"Привіт, {user.first_name or 'друже'}! Я Містичний Єнот — твій гід у світі Таро 🦝🔮\n\n"
        "Обери дію нижче 👇",
        reply_markup=markup,
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages that match the reply keyboard options."""
    text = update.message.text

    if text == "🃏 Карта дня":
        await get_daily_card(update, context)
    elif text == "Як працює бот ❓":
        await update.message.reply_text("Цей бот витягує карти Таро та дає тобі поради 😉")
    else:
        await update.message.reply_text("Оберіть команду з меню ⬇️")


def configure_logging() -> None:
    """Configure application-wide logging once."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def build_application(token: str) -> Application:
    """Create and configure the Telegram application instance."""
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(
        CallbackQueryHandler(
            raccoon_interpretation_callback,
            pattern="^raccoon_interpretation$",
        )
    )
    return app


def main() -> None:
    configure_logging()

    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN environment variable is not set")

    app = build_application(token)

    LOGGER.info("✅ Бот запущений та очікує оновлення")
    app.run_polling()


if __name__ == "__main__":
    main()
