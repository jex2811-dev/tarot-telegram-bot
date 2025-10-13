#!/usr/bin/env python3
"""Entry point for the Tarot Telegram bot."""

from __future__ import annotations
import logging
import os
import random
import time
import threading
from typing import Final
from flask import Flask

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
    ["💎 Бонуси та запрошення", "Як працює бот ❓"],
]

# ---------------------------------------------------------------------------
# 🌐 Flask Keep-Alive Server
def run_health_server():
    """🦝 Flask-сервер для keep-alive, щоб Render не засинав."""
    app = Flask(__name__)

    @app.route("/")
    def index():
        return "🦝 MysticEnotBot is alive and shuffling cards! ✨"

    # Запуск у фоні
    thread = threading.Thread(target=lambda: app.run(host="0.0.0.0", port=8080), daemon=True)
    thread.start()
    LOGGER.info("🌐 Flask keep-alive server запущений на порту 8080")

# ---------------------------------------------------------------------------
# 🪄 Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    referred_by = args[0] if args and args[0].startswith("REF") else None

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
        "💎 <b>Бонуси та запрошення</b> — твоя магічна скринька і реферальні подарунки.\n\n"
        "Єнот уже потирає лапки і тасує карти... 💫"
    )

    await update.message.reply_text(welcome_text, reply_markup=markup, parse_mode="HTML")

# ---------------------------------------------------------------------------
# 🔮 Показ категорій
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
# 🃏 Обробка категорії
async def handle_category_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_info = get_user_info(str(user.id))
    available_spreads = int(user_info.get("available_spreads", 0))

    if available_spreads <= 0:
        await update.message.reply_text(
            "🃏 У тебе закінчились карти на сьогодні!\n\n"
            "Повертайся завтра 🌙 або запроси друга, щоб отримати +3 бонусні карти 💫\n\n"
            "Натисни 💎 <b>Бонуси та запрошення</b>, щоб дізнатись більше.",
            parse_mode="HTML",
        )
        return

    from gsheets_helper import find_user_row, get_col_index
    row_index, _ = find_user_row(str(user.id))
    users_sheet.update_cell(row_index, get_col_index("available_spreads"), available_spreads - 1)

    user_choice = update.message.text
    if user_choice == "💞 Любов":
        category = "love"
    elif user_choice == "💼 Кар’єра":
        category = "career"
    elif user_choice == "💰 Гроші":
        category = "money"
    else:
        return

    card = random.choice(cards)
    meanings = card["meanings"].get(category)

    if meanings and "descriptions" in meanings and "raccoons" in meanings:
        description = random.choice(meanings["descriptions"])
        raccoon = random.choice(meanings["raccoons"])
    else:
        description = "Ця карта ще не має опису для цієї категорії."
        raccoon = "Єнот мовчить, бо ще пише маніфест 🦝🖋️"

    context.user_data["last_card"] = (card, category, raccoon)

    await update.message.reply_photo(
        photo=card["photo_url"],
        caption=f"<b>{card['title']}</b>\n\n{description}",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup([["🦝 Коментар Єнота"], ["⬅️ Назад"]], resize_keyboard=True),
    )

# ---------------------------------------------------------------------------
# 🦝 Коментар від Єнота
async def show_raccoon_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "last_card" not in context.user_data:
        await update.message.reply_text("Спочатку обери категорію 💫")
        return
    _, _, raccoon = context.user_data["last_card"]
    await update.message.reply_text(f"🦝 {raccoon}")

# ---------------------------------------------------------------------------
# 💎 Магічна скринька (оновлено)
async def show_my_chest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        user_data = get_user_info(str(user.id))
        if not user_data:
            await update.message.reply_text(
                "Єнот не може знайти твою скриньку... 🦝 Спробуй натиснути /start ще раз."
            )
            return

        available_spreads = user_data["available_spreads"]
        referrals_count = user_data["referrals_count"]
        referral_code = user_data["referral_code"]
        referral_link = f"https://t.me/TaroEnotBot?start={referral_code}"

        if referrals_count < 3:
            rank = "🌱 Молодий шаман"
        elif referrals_count < 6:
            rank = "🔮 Магічний учень"
        else:
            rank = "🦝 Майстер Єнотової магії"

        moons = ["🌑🌑🌑", "🌕🌑🌑", "🌕🌕🌑", "🌕🌕🌕"]
        moon = moons[min(available_spreads, 3)]

        chest_text = (
            f"💎 <b>Твоя магічна скринька</b>\n\n"
            f"🔮 <b>Доступних розкладів:</b> {available_spreads} {moon}\n"
            f"💞 <b>Запрошено друзів:</b> {referrals_count}\n"
            f"🏅 <b>Рівень:</b> {rank}\n\n"
            "───────────────\n"
            "🪄 <b>Хочеш більше карт?</b>\n"
            "Запроси друзів і отримай +3 розклади за кожного 💫\n\n"
            "🔗 <b>Твоє реферальне посилання:</b>\n"
            f"{referral_link}\n\n"
            "Поділися ним у Telegram або сторіз —\n"
            "і нехай Єнот віддячить магією 🦝✨"
        )

        keyboard = [["📤 Поділитися запрошенням"], ["⬅️ Назад"]]
        await update.message.reply_text(
            chest_text,
            parse_mode="HTML",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        )

    except Exception as e:
        await update.message.reply_text(
            "⚠️ Єнот заплутався у магії Google Sheets... Спробуй ще раз 🦝✨"
        )
        print("❌ Помилка в show_my_chest:", e)

# ---------------------------------------------------------------------------
# 📘 Як працює бот
async def send_how_it_works(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "✨ <b>Як працює Містичний Єнот</b> 🦝🔮\n\n"
        "🃏 <b>Карта дня</b> — щоденна підказка Всесвіту.\n"
        "🔮 <b>Розкласти карти</b> — любов, кар’єра, гроші.\n"
        "💎 <b>Бонуси та запрошення</b> — твої подарунки та рівень мага.\n"
        "🎁 <b>Запрошуй друзів</b> — отримуй карти за рефералів.\n\n"
        "<i>Єнот шепоче: навіть випадкові карти — не випадковість 🌙</i>"
    )
    await update.message.reply_text(text, parse_mode="HTML")

# ---------------------------------------------------------------------------
# 🧭 Головний обробник повідомлень
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "🃏 Карта дня":
        await get_daily_card(update, context)
    elif text == "🔮 Розкласти карти":
        await show_categories(update, context)
    elif text in ["💞 Любов", "💼 Кар’єра", "💰 Гроші"]:
        await handle_category_choice(update, context)
    elif text == "🦝 Коментар Єнота":
        await show_raccoon_comment(update, context)
    elif text == "💎 Бонуси та запрошення":
        await show_my_chest(update, context)
    elif text == "Як працює бот ❓":
        await send_how_it_works(update, context)
    elif text == "⬅️ Назад":
        await update.message.reply_text(
            "Повертаємось у головне меню 🦝",
            reply_markup=ReplyKeyboardMarkup(REPLY_KEYBOARD, resize_keyboard=True),
        )
    else:
        await update.message.reply_text("Оберіть команду з меню ⬇️")

# ---------------------------------------------------------------------------
def build_application(token: str) -> Application:
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(raccoon_interpretation_callback, pattern="^raccoon_interpretation$"))
    return app

# ---------------------------------------------------------------------------
def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN environment variable is not set")

    run_health_server()
    app = build_application(token)
    LOGGER.info("✅ Бот запущений та очікує оновлення")

    while True:
        try:
            app.run_polling()
        except Exception as e:
            LOGGER.error(f"❌ Помилка виконання polling: {e}")
            time.sleep(10)

# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()
