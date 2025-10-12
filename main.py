#!/usr/bin/env python3
"""Entry point for the Tarot Telegram bot."""

from __future__ import annotations
import logging
import os
import random
import time
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

# ✅ Імпорти
from daily_card import get_daily_card, raccoon_interpretation_callback
from gsheets_helper import add_user, get_user_info, users_sheet
from cards import cards

# ---------------------------------------------------------------------------

LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

# 🏠 Головне меню
REPLY_KEYBOARD: Final[list[list[str]]] = [
    ["🃏 Карта дня", "🔮 Розкласти карти"],
    ["Моя скринька 📦", "Як працює бот ❓"],
]

# ---------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Реєстрація нового користувача + перевірка реферального посилання"""
    user = update.effective_user
    args = context.args

    referred_by = None
    if args:
        referred_by = args[0] if args[0].startswith("REF") else None

    add_user(
        user_id=str(user.id),
        username=user.username or "",
        first_name=user.first_name or "",
        referral_code="NONE",
        referred_by=referred_by,
    )

    markup = ReplyKeyboardMarkup(REPLY_KEYBOARD, resize_keyboard=True)

    greetings = [
        f"Привіт, {user.first_name or 'друже'}! Єнот радий бачити тебе знову 🦝✨",
        f"Магічне вітання, {user.first_name or 'друже'} 🌙✨ Готовий розкласти карти?",
        f"Шурхіт карт і привіт від Єнота! 🦝 Готовий до магії?",
    ]

    welcome_text = (
        f"{random.choice(greetings)}\n\n"
        "Я — <b>Містичний Єнот</b>, твій провідник у світі Таро 🔮\n"
        "Разом ми відкриватимемо підказки Всесвіту — про кохання, фінанси й шлях долі 🌙\n\n"
        "🃏 <b>Карта дня</b> — енергія твого сьогодні.\n"
        "🔮 <b>Розкласти карти</b> — обери напрямок: любов, кар’єра чи гроші.\n"
        "📦 <b>Моя скринька</b> — твоя магічна статистика і бонуси.\n\n"
        "Єнот уже потирає лапки і тасує карти... 💫"
    )

    await update.message.reply_text(welcome_text, reply_markup=markup, parse_mode="HTML")

# ---------------------------------------------------------------------------

async def show_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["💞 Любов", "💼 Кар’єра", "💰 Гроші"], ["⬅️ Назад"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    phrases = [
        "Єнот тасує карти... Куди зазирнемо сьогодні? 🔮🦝",
        "Серце, гаманець чи кар’єра? Обери свій шлях 💞💰💼",
        "Любов, гроші чи слава — що підкаже Всесвіт сьогодні? 💫",
        "Єнот підморгує: «Кохання чи кар’єра? Обери, поки карти гарячі!» 🔥",
    ]

    await update.message.reply_text(random.choice(phrases), reply_markup=reply_markup)

# ---------------------------------------------------------------------------

async def handle_category_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_info = get_user_info(str(user.id))
    available_spreads = int(user_info.get("available_spreads", 0))

    if available_spreads <= 0:
        await update.message.reply_text(
            "🃏 У тебе закінчились карти на сьогодні!\n\n"
            "Повертайся завтра 🌙 або запроси друга, щоб отримати +3 бонусні карти 💫\n\n"
            "Натисни 📦 <b>Моя скринька</b>, щоб дізнатись більше.",
            parse_mode="HTML",
        )
        return

    # 🔄 Зменшуємо кількість карт
    from gsheets_helper import find_user_row, get_col_index
    row_index, _ = find_user_row(str(user.id))
    users_sheet.update_cell(row_index, get_col_index("available_spreads"), available_spreads - 1)

    # 🧩 Визначаємо категорію
    user_choice = update.message.text
    if user_choice == "💞 Любов":
        category = "love"
        phrases = [
            "Єнот чує биття серця… любов наближається 💞",
            "Шурхіт карт шепоче про почуття, які пробуджують душу 💕",
            "Єнот підморгує: «Любов — це завжди трохи ризик і багато магії!» 💌",
        ]
    elif user_choice == "💼 Кар’єра":
        category = "career"
        phrases = [
            "Єнот поправляє краватку: «Працюємо на успіх!» 💼",
            "Повітря наповнюється амбіціями... Всесвіт готує підвищення ✨",
            "Карти блищать діловим настроєм — настав час діяти впевнено 💪",
        ]
    elif user_choice == "💰 Гроші":
        category = "money"
        phrases = [
            "Єнот потирає лапки: «Пахне фінансовими можливостями!» 💰",
            "Монетки дзвенять у повітрі... Всесвіт готує нагороду ✨",
            "Єнот шепоче: «Гроші — це енергія, давай побачимо, як вона тече сьогодні.» 🪙",
        ]
    else:
        return

    await update.message.reply_text(random.choice(phrases))

    card = random.choice(cards)
    context.user_data["last_card"] = (card, category)

    await update.message.reply_photo(
        photo=card["photo_url"],
        caption=f"<b>{card['title']}</b>\n\n{card['meanings'][category]['description']}",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup([["🦝 Коментар Єнота"], ["⬅️ Назад"]], resize_keyboard=True),
    )

# ---------------------------------------------------------------------------

async def show_raccoon_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "last_card" not in context.user_data:
        await update.message.reply_text("Спочатку обери категорію 💫")
        return
    card, category = context.user_data["last_card"]
    await update.message.reply_text(f"🦝 {card['meanings'][category]['raccoon']}")

# ---------------------------------------------------------------------------

async def show_my_chest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        user_data = get_user_info(str(user.id))
        if not user_data:
            await update.message.reply_text("Єнот не може знайти твою скриньку... 🦝 Спробуй натиснути /start ще раз.")
            return

        available_spreads = user_data["available_spreads"]
        referrals_count = user_data["referrals_count"]
        referral_code = user_data["referral_code"]
        referral_link = f"https://t.me/TaroEnotBot?start={referral_code}"

        # 🏅 Рівень користувача
        if referrals_count < 3:
            rank = "🌱 Молодий шаман"
        elif referrals_count < 6:
            rank = "🔮 Магічний учень"
        else:
            rank = "🦝 Майстер Єнотової магії"

        moons = ["🌑🌑🌑", "🌕🌑🌑", "🌕🌕🌑", "🌕🌕🌕"]
        moon = moons[min(available_spreads, 3)]

        chest_text = (
            f"📦 <b>Моя магічна скринька</b>\n\n"
            f"🔮 <b>Доступних розкладів:</b> {available_spreads} {moon}\n"
            f"💞 <b>Запрошено друзів:</b> {referrals_count}\n"
            f"🏅 <b>Рівень:</b> {rank}\n\n"
            f"🔗 <b>Твій реферальний код:</b> <code>{referral_code}</code>\n\n"
            f"✨ <b>Посилання для друзів:</b>\n{referral_link}\n\n"
            "Єнот каже: «Ділися магією — і вона повернеться втричі!» 🦝💫"
        )

        keyboard = [["🔗 Скопіювати реферальне посилання"], ["⬅️ Назад"]]
        await update.message.reply_text(chest_text, parse_mode="HTML",
                                        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
    except Exception as e:
        await update.message.reply_text("⚠️ Єнот заплутався у магії Google Sheets... Спробуй ще раз 🦝✨")
        print("❌ Помилка в show_my_chest:", e)

# ---------------------------------------------------------------------------

async def go_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Повертаємось у головне меню 🦝",
                                    reply_markup=ReplyKeyboardMarkup(REPLY_KEYBOARD, resize_keyboard=True))

# ---------------------------------------------------------------------------

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Головна логіка — з антидублюванням"""
    if context.user_data.get("is_processing", False):
        return
    context.user_data["is_processing"] = True

    try:
        text = update.message.text

        if text == "🃏 Карта дня":
            await get_daily_card(update, context)
        elif text == "Моя скринька 📦":
            await show_my_chest(update, context)
        elif text == "🔗 Скопіювати реферальне посилання":
            user = update.effective_user
            user_data = get_user_info(str(user.id))
            link = f"https://t.me/TaroEnotBot?start={user_data['referral_code']}"
            await update.message.reply_text(
                f"🔗 Ось твоє посилання, щоб запросити друзів:\n{link}\n\n"
                "Єнот каже: «Кидай його друзям і отримай +3 карти за кожного!» 🦝💫"
            )
        elif text == "Як працює бот ❓":
            await update.message.reply_text(
                "✨ <b>Як працює Містичний Єнот</b> 🦝🔮\n\n"
                "🃏 Карта дня — щоденний гід.\n"
                "🔮 Розкласти карти — любов, кар’єра, гроші.\n"
                "📦 Моя скринька — бонуси та статистика.\n"
                "🎁 Запрошуй друзів і отримуй карти!\n\n"
                "<i>Єнот шепоче: навіть випадкові карти — це не випадковість 🌙</i>",
                parse_mode="HTML",
            )
        elif text == "🔮 Розкласти карти":
            await show_categories(update, context)
        elif text in ["💞 Любов", "💼 Кар’єра", "💰 Гроші"]:
            await handle_category_choice(update, context)
        elif text == "🦝 Коментар Єнота":
            await show_raccoon_comment(update, context)
        elif text == "⬅️ Назад":
            await go_back(update, context)
        else:
            await update.message.reply_text("Оберіть команду з меню ⬇️")
    finally:
        context.user_data["is_processing"] = False

# ---------------------------------------------------------------------------

def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# ---------------------------------------------------------------------------

def build_application(token: str) -> Application:
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(raccoon_interpretation_callback, pattern="^raccoon_interpretation$"))
    return app

# ---------------------------------------------------------------------------

def main() -> None:
    configure_logging()
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN environment variable is not set")

    app = build_application(token)
    LOGGER.info("✅ Бот запущений та очікує оновлення")

    # 🔁 Автоматичний перезапуск polling при збоях
    while True:
        try:
            app.run_polling()
        except Exception as e:
            LOGGER.error(f"❌ Помилка виконання polling: {e}")
            time.sleep(10)  # перезапуск через 10 секунд

# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()
