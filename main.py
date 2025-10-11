#!/usr/bin/env python3
"""Entry point for the Tarot Telegram bot."""

from __future__ import annotations

import logging
import os
import random
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
from cards import cards  # ✅ Імпортуємо наш список карт

# ---------------------------------------------------------------------------

LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

# 🏠 Головне меню
REPLY_KEYBOARD: Final[list[list[str]]] = [
    ["🃏 Карта дня", "Категорії розкладів"],
    ["Моя скринька 📦", "Як працює бот ❓"],
]

# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------

# 🧭 Меню категорій
async def show_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["💞 Любов", "💼 Кар’єра", "💰 Гроші"],
        ["⬅️ Назад"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    # 🎭 Випадкові фрази для атмосфери
    phrases = [
        "Серце чи гаманець? А може, кар’єрна магія? Обирай свій шлях! 💞💰💼",
        "Єнот розкладає карти... Куди зазирнемо сьогодні? 🔮🦝",
        "Любов, гроші чи слава? Всесвіт чекає на твій вибір 💫",
        "Твоя інтуїція не помиляється — просто обери напрямок 🌙",
        "Єнот підморгує: «Кохання чи кар’єра? Обери, поки карти гарячі!» 🔥"
    ]

    text = random.choice(phrases)
    await update.message.reply_text(text, reply_markup=reply_markup)

# ---------------------------------------------------------------------------

# 🎴 Обробка вибору категорії
async def handle_category_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_choice = update.message.text

    # 🩷 Категорія: Любов
    if user_choice == "💞 Любов":
        category = "love"
        phrases = [
            "Єнот чує биття серця… любов наближається 💞",
            "Шурхіт карт шепоче про почуття, які пробуджують душу 💕",
            "Єнот підморгує: «Любов — це завжди трохи ризик і багато магії!» 💌",
        ]

    # 💼 Категорія: Кар’єра
    elif user_choice == "💼 Кар’єра":
        category = "career"
        phrases = [
            "Єнот поправляє краватку: «Працюємо на успіх!» 💼",
            "Повітря наповнюється амбіціями... Всесвіт готує підвищення ✨",
            "Карти блищать діловим настроєм — настав час діяти впевнено 💪",
        ]

    # 💰 Категорія: Гроші
    elif user_choice == "💰 Гроші":
        category = "money"
        phrases = [
            "Єнот потирає лапки: «Пахне фінансовими можливостями!» 💰",
            "Монетки дзвенять у повітрі... Всесвіт готує нагороду ✨",
            "Єнот шепоче: «Гроші — це енергія, давай побачимо, як вона тече сьогодні.» 🪙",
        ]

    else:
        return

    # ✨ Передмова перед картою
    intro_text = random.choice(phrases)
    await update.message.reply_text(intro_text)

    # 🎴 Випадкова карта
    card = random.choice(cards)
    context.user_data["last_card"] = (card, category)

    title = card["title"]
    description = card["meanings"][category]["description"]
    photo = card["photo_url"]

    keyboard = [["🦝 Коментар Єнота"], ["⬅️ Назад"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_photo(
        photo=photo,
        caption=f"<b>{title}</b>\n\n{description}",
        parse_mode="HTML",
        reply_markup=reply_markup
    )

# ---------------------------------------------------------------------------

# 🦝 Тлумачення від Єнота
async def show_raccoon_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "last_card" not in context.user_data:
        await update.message.reply_text("Спочатку обери категорію 💫")
        return

    card, category = context.user_data["last_card"]
    raccoon_comment = card["meanings"][category]["raccoon"]

    await update.message.reply_text(f"🦝 {raccoon_comment}")

# ---------------------------------------------------------------------------

# 🔙 Назад у головне меню
async def go_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_markup = ReplyKeyboardMarkup(REPLY_KEYBOARD, resize_keyboard=True)
    await update.message.reply_text("Повертаємось у головне меню 🦝", reply_markup=reply_markup)

# ---------------------------------------------------------------------------

# 🧩 Основний обробник повідомлень
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text

    if text == "🃏 Карта дня":
        await get_daily_card(update, context)
    elif text == "Як працює бот ❓":
        await update.message.reply_text("Цей бот витягує карти Таро та дає тобі поради 😉")
    elif text == "Категорії розкладів":
        await show_categories(update, context)
    elif text in ["💞 Любов", "💼 Кар’єра", "💰 Гроші"]:
        await handle_category_choice(update, context)
    elif text == "🦝 Коментар Єнота":
        await show_raccoon_comment(update, context)
    elif text == "⬅️ Назад":
        await go_back(update, context)
    else:
        await update.message.reply_text("Оберіть команду з меню ⬇️")

# ---------------------------------------------------------------------------

def configure_logging() -> None:
    """Configure application-wide logging once."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------

def main() -> None:
    configure_logging()

    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN environment variable is not set")

    app = build_application(token)

    LOGGER.info("✅ Бот запущений та очікує оновлення")
    app.run_polling()

# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()
