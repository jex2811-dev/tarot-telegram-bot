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
from gsheets_helper import add_user, get_user_info
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
    """Реєстрація нового користувача + перевірка реферального посилання"""
    user = update.effective_user
    args = context.args

    # 🧩 Перевіряємо, чи користувач прийшов за реферальним кодом
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

    welcome_text = (
        f"Привіт, {user.first_name or 'друже'}! 🦝✨\n\n"
        "Я — <b>Містичний Єнот</b>, твій магічний провідник у світі карт Таро 🔮\n"
        "Разом ми будемо відкривати підказки Всесвіту — про почуття, фінанси, кар’єру та щоденні знаки долі 🌙\n\n"
        "🃏 <b>Карта дня</b> — твій щоденний супутник. Вона допоможе зрозуміти енергію дня, "
        "налаштуватися на потрібну хвилю та побачити приховані можливості.\n\n"
        "🔮 <b>Категорії розкладів</b> — обери, про що хочеш дізнатися:\n"
        "   💞 Кохання — підкаже, що відбувається у серці;\n"
        "   💼 Кар’єра — розповість, куди веде твій професійний шлях;\n"
        "   💰 Гроші — відкриє фінансову перспективу й поради для достатку.\n\n"
        "📦 <b>Моя скринька</b> — тут зберігається твоя магічна статистика: "
        "скільки друзів ти запросив, скільки розкладів залишилось і які бонуси вже отримав ✨\n\n"
        "❓ <b>Як працює бот</b> — коротка інструкція, якщо хочеш освіжити пам’ять про всі можливості.\n\n"
        "Ну що, готовий до магії? Єнот уже потирає лапки і тасує карти... 🃏💫"
    )

    await update.message.reply_text(
        welcome_text,
        reply_markup=markup,
        parse_mode="HTML"
    )

# ---------------------------------------------------------------------------

# 🧭 Меню категорій
async def show_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["💞 Любов", "💼 Кар’єра", "💰 Гроші"],
        ["⬅️ Назад"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

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
# 🎴 Обробка вибору категорії (з перевіркою доступних карт)
from gsheets_helper import users_sheet

async def handle_category_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_info = get_user_info(str(user.id))

    # 🔍 Перевірка кількості карт
    available_spreads = int(user_info.get("available_spreads", 0))

    if available_spreads <= 0:
        await update.message.reply_text(
            "🃏 У тебе закінчились карти на сьогодні!\n\n"
            "Повертайся завтра 🌙 або запроси друга, щоб отримати +3 бонусні карти 💫\n\n"
            "Натисни 📦 <b>Моя скринька</b>, щоб дізнатись більше.",
            parse_mode="HTML"
        )
        return

    # Зменшуємо кількість карт після використання
    user_row = user_info["row_index"]
    new_value = available_spreads - 1
    users_sheet.update_cell(user_row, user_info["available_spreads_col"], new_value)

    # 🔮 Далі стандартна логіка
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

    intro_text = random.choice(phrases)
    await update.message.reply_text(intro_text)

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
# 📦 Моя скринька
async def show_my_chest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = get_user_info(str(user.id))

    if not user_data:
        await update.message.reply_text("Єнот не може знайти твою скриньку... 🦝 Спробуй натиснути /start ще раз.")
        return

    available_spreads = user_data["available_spreads"]
    referrals_count = user_data["referrals_count"]
    referral_code = user_data["referral_code"]
    referral_link = f"https://t.me/TaroEnotBot?start={referral_code}"

    # 🌕🌗🌑 Візуальний індикатор
    if available_spreads == 3:
        moon = "🌕🌕🌕"
    elif available_spreads == 2:
        moon = "🌕🌕🌑"
    elif available_spreads == 1:
        moon = "🌕🌑🌑"
    else:
        moon = "🌑🌑🌑"

    chest_text = (
        f"📦 <b>Моя магічна скринька</b>\n\n"
        f"🔮 <b>Доступних розкладів:</b> {available_spreads} {moon}\n"
        f"💞 <b>Запрошено друзів:</b> {referrals_count}\n"
        f"🔗 <b>Твій реферальний код:</b> <code>{referral_code}</code>\n\n"
        f"✨ <b>Посилання для друзів:</b>\n{referral_link}\n\n"
        "Єнот каже: «Ділися магією — і вона повернеться втричі!» 🦝💫"
    )

    keyboard = [
        ["🔗 Скопіювати реферальне посилання"],
        ["⬅️ Назад"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(chest_text, parse_mode="HTML", reply_markup=reply_markup)

# ---------------------------------------------------------------------------
# 🔙 Назад
async def go_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_markup = ReplyKeyboardMarkup(REPLY_KEYBOARD, resize_keyboard=True)
    await update.message.reply_text("Повертаємось у головне меню 🦝", reply_markup=reply_markup)

# ---------------------------------------------------------------------------
# 🧩 Основний обробник повідомлень
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text

    if text == "🃏 Карта дня":
        await get_daily_card(update, context)

    elif text == "Моя скринька 📦":
        await show_my_chest(update, context)

    elif text == "🔗 Скопіювати реферальне посилання":
        user = update.effective_user
        user_data = get_user_info(str(user.id))
        referral_code = user_data["referral_code"]
        referral_link = f"https://t.me/TaroEnotBot?start={referral_code}"

        await update.message.reply_text(
            f"🔗 Ось твоє посилання, щоб запросити друзів:\n{referral_link}\n\n"
            "Єнот каже: «Кидай його своїм друзям і отримай 3 додаткові карти за кожного, хто приєднається!» 🦝💫"
        )

    elif text == "Як працює бот ❓":
        how_it_works_text = (
            "✨ <b>Як працює Містичний Єнот</b> 🦝🔮\n\n"
            "🃏 <b>Карта дня</b> — твій щоденний гід.\n"
            "🔮 <b>Категорії розкладів</b> — любов, кар’єра, гроші.\n"
            "📦 <b>Моя скринька</b> — бонуси та статистика.\n"
            "🎁 Запрошуй друзів і отримуй карти!\n\n"
            "<i>Єнот шепоче: навіть випадкові карти — це не випадковість 🌙</i>"
        )
        await update.message.reply_text(how_it_works_text, parse_mode="HTML")

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
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

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
    app.run_polling()

# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()
