#!/usr/bin/env python3
"""Entry point for the Tarot Telegram bot (OpenAI edition)."""

from __future__ import annotations
import logging
import os
import random
import time
import threading
from datetime import datetime
from typing import Final
from flask import Flask

from telegram import ReplyKeyboardMarkup, Update, LabeledPrice
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)

# ✅ Імпорти функцій
from daily_card import get_daily_card, raccoon_interpretation_callback
from gsheets_helper import add_user, get_user_info, users_sheet, find_user_row, get_col_index
from cards import cards

# 🧠 AI функції
from ai_free import (
    generate_ai_tarot,
    generate_ai_astrology,
    generate_ai_numerology,
    generate_ai_chiromancy,
)

# 🔧 Dev / Beta конфіг
from config import DEVELOPER_ID, BETA_MODE

# ---------------------------------------------------------------------------
LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

REPLY_KEYBOARD: Final[list[list[str]]] = [
    ["💫 Індивідуальні розклади (BETA)", "🃏 Карта дня"],
    ["🔮 Розкласти карти", "💎 Бонуси та запрошення"],
    ["Як працює бот ❓"],
]

# ---------------------------------------------------------------------------
# 🌐 Keep-alive Flask server (Render)
def run_health_server():
    """🦝 Flask-сервер для keep-alive."""
    app = Flask(__name__)

    @app.route("/")
    def index():
        return "🦝 MysticEnotBot is alive and shuffling cards! ✨"

    thread = threading.Thread(target=lambda: app.run(host="0.0.0.0", port=8080), daemon=True)
    thread.start()
    LOGGER.info("🌐 Flask keep-alive server запущений на порту 8080")

# ---------------------------------------------------------------------------
# 🎁 Щоденний бонус +3 карт/день
def give_daily_bonus_if_needed(user_id: str) -> bool:
    """Автоматично додає +3 карти раз на день."""
    try:
        user_info = get_user_info(user_id)
        today = datetime.now().strftime("%Y-%m-%d")
        if str(user_info.get("last_daily_bonus", "")) == today:
            return False

        current_spreads = int(user_info.get("available_spreads", 0))
        new_spreads = current_spreads + 3
        row_index, _ = find_user_row(user_id)
        users_sheet.update_cell(row_index, get_col_index("available_spreads"), new_spreads)
        users_sheet.update_cell(row_index, get_col_index("last_daily_bonus"), today)
        LOGGER.info(f"🎁 {user_id}: щоденний бонус +3 карт (тепер {new_spreads})")
        return True
    except Exception as e:
        LOGGER.error(f"❌ Помилка в give_daily_bonus_if_needed: {e}")
        return False

# ---------------------------------------------------------------------------
# 🧠 Перевірка розробника
def is_developer(user_id: int) -> bool:
    return BETA_MODE and user_id == DEVELOPER_ID

# ---------------------------------------------------------------------------
# ↩️ Повернення в головне меню
async def back_to_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    markup = ReplyKeyboardMarkup(REPLY_KEYBOARD, resize_keyboard=True)
    if update.message:
        await update.message.reply_text("🔮 Ви повернулися до головного меню.", reply_markup=markup)
    elif update.callback_query:
        q = update.callback_query
        await q.answer()
        await q.message.reply_text("🔮 Ви повернулися до головного меню.", reply_markup=markup)

# ---------------------------------------------------------------------------
# 🚪 /start
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

    # ✅ щоденний бонус
    bonus_given = give_daily_bonus_if_needed(str(user.id))
    if bonus_given and update.message:
        await update.message.reply_text(
            "🎁 Єнот подарував тобі <b>3 нові карти</b> на сьогодні! 🃏✨",
            parse_mode="HTML"
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

    if update.message:
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
    ]
    await update.message.reply_text(random.choice(phrases), reply_markup=reply_markup)

# ---------------------------------------------------------------------------
# 🃏 Обробка вибору категорії
async def handle_category_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_info = get_user_info(str(user.id))
    available_spreads = int(user_info.get("available_spreads", 0))

    if available_spreads <= 0:
        await update.message.reply_text(
            "🃏 У тебе закінчились карти на сьогодні!\n\n"
            "Повертайся завтра 🌙 або запроси друга, щоб отримати +3 бонусні карти 💫",
            parse_mode="HTML",
        )
        return

    row_index, _ = find_user_row(str(user.id))
    users_sheet.update_cell(row_index, get_col_index("available_spreads"), available_spreads - 1)

    category_map = {"💞 Любов": "love", "💼 Кар’єра": "career", "💰 Гроші": "money"}
    category = category_map.get(update.message.text)
    if not category:
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
# 🦝 Коментар Єнота
async def handle_raccoon_comment_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data.get("last_card")
    if not data:
        await update.message.reply_text("Спершу обери розклад і карту, а потім натисни «🦝 Коментар Єнота».")
        return
    _, _, raccoon_text = data
    await update.message.reply_text(f"🦝 Коментар Єнота:\n{raccoon_text}")

# ---------------------------------------------------------------------------
# 💫 Меню платних сервісів
async def show_paid_services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_developer(user.id):
        await update.message.reply_text("⚠️ Цей розділ поки що доступний лише розробнику 🦝")
        return

    keyboard = [
        ["💫 AI-Індивідуальний розклад (20⭐️)"],
        ["🔮 AI-Астрологічний прогноз (15⭐️)"],
        ["🔢 AI-Нумерологічний портрет (10⭐️)"],
        ["✋ AI-Хіромантія (25⭐️)"],
        ["⬅️ Назад"],
    ]
    await update.message.reply_text("🪄 Обери магічну послугу 🌙", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

# ---------------------------------------------------------------------------
# ✅ Stars оплата
async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    try:
        await query.answer(ok=True)
    except Exception as e:
        LOGGER.error(f"❌ pre_checkout_query error: {e}")
        await query.answer(ok=False, error_message="Єнот не зміг підтвердити оплату 🦝💫")

# ---------------------------------------------------------------------------
# 🪄 AI функції після оплати
async def handle_successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    payment = update.message.successful_payment
    product = payment.invoice_payload
    LOGGER.info(f"✅ successful_payment: {user.id}, {product}")

    if product == "ai_tarot":
        await update.message.reply_text(generate_ai_tarot(user.first_name))
    elif product == "ai_astrology":
        await update.message.reply_text(generate_ai_astrology(user.first_name, "1995-01-01"))
    elif product == "ai_numerology":
        await update.message.reply_text(generate_ai_numerology("1995-01-01"))
    elif product == "ai_chiromancy":
        await update.message.reply_text(generate_ai_chiromancy("На фото видно долоню з чіткими лініями..."))
    else:
        await update.message.reply_text("⚠️ Невідомий тип послуги.")

# ---------------------------------------------------------------------------
# 📜 /terms і /paysupport
async def terms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📜 Умови користування: цифрові розклади є розважальним контентом.\n"
        "Повернення можливе у разі технічної помилки. Пишіть у /paysupport."
    )

async def paysupport(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛟 Підтримка оплат: напишіть @TaroEnotBot (DM) із чеком або скрином.")

# ---------------------------------------------------------------------------
def build_application(token: str) -> Application:
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("terms", terms))
    app.add_handler(CommandHandler("paysupport", paysupport))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_raccoon_comment_text))
    app.add_handler(CallbackQueryHandler(raccoon_interpretation_callback, pattern="^raccoon_interpretation$"))
    app.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, handle_successful_payment))
    return app

# ---------------------------------------------------------------------------
def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN is not set")

    run_health_server()
    app = build_application(token)
    LOGGER.info("✅ Бот запущений та очікує оновлення")

    while True:
        try:
            app.run_polling()
        except Exception as e:
            LOGGER.error(f"❌ Polling error: {e}")
            time.sleep(10)

# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()
