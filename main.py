#!/usr/bin/env python3
"""Містичний Єнот 🦝✨ — повна версія (sandbox + AI + Stars + реферальна логіка)"""

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

# ✅ Імпорти локальних модулів
from daily_card import get_daily_card, raccoon_interpretation_callback
from gsheets_helper import add_user, get_user_info, users_sheet, find_user_row, get_col_index
from cards import cards
from ai_free import (
    generate_ai_tarot,
    generate_ai_astrology,
    generate_ai_numerology,
    generate_ai_chiromancy,
)

# ---------------------------------------------------------------------------
# ⚙️ Конфігурація
DEVELOPER_ID = 1545533785     # Твій Telegram ID
BETA_MODE = True              # Режим тестування для нових фіч
SANDBOX_MODE = True           # ✅ Не витрачає зірки (імітація оплат)
# ---------------------------------------------------------------------------

LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

# 🏠 Меню
REPLY_KEYBOARD: Final[list[list[str]]] = [
    ["💫 Індивідуальні розклади (BETA)", "🃏 Карта дня"],
    ["🔮 Розкласти карти", "💎 Бонуси та запрошення"],
    ["Як працює бот ❓"],
]

# ---------------------------------------------------------------------------
# 🌐 Keep-alive Flask server
def run_health_server():
    app = Flask(__name__)

    @app.route("/")
    def index():
        return "🦝 MysticEnotBot живий і тасує карти ✨"

    thread = threading.Thread(target=lambda: app.run(host="0.0.0.0", port=8080), daemon=True)
    thread.start()

# ---------------------------------------------------------------------------
# 🎁 Щоденний бонус
def give_daily_bonus_if_needed(user_id: str) -> bool:
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
        return True
    except Exception as e:
        LOGGER.error(f"❌ Помилка bonus: {e}")
        return False

# ---------------------------------------------------------------------------
# 🧠 Перевірка розробника
def is_developer(user_id: int) -> bool:
    return user_id == DEVELOPER_ID

# ---------------------------------------------------------------------------
# ↩️ Назад у головне меню
async def back_to_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    markup = ReplyKeyboardMarkup(REPLY_KEYBOARD, resize_keyboard=True)
    await update.message.reply_text("🔮 Ви повернулися до головного меню.", reply_markup=markup)

# ---------------------------------------------------------------------------
# 🚪 /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    referred_by = args[0] if args and args[0].startswith("REF") else None

    add_user(str(user.id), user.username or "", user.first_name or "", "NONE", referred_by)

    bonus_given = give_daily_bonus_if_needed(str(user.id))
    if bonus_given:
        await update.message.reply_text("🎁 Єнот подарував тобі <b>3 нові карти</b> на сьогодні! 🃏✨", parse_mode="HTML")

    greetings = [
        f"Привіт, {user.first_name or 'друже'}! Єнот радий бачити тебе 🦝✨",
        f"Магічне вітання, {user.first_name or 'друже'} 🌙✨ Готовий до розкладу?",
        "Шурхіт карт і аромат магії... Єнот готовий 🃏",
    ]

    text = (
        f"{random.choice(greetings)}\n\n"
        "Я — <b>Містичний Єнот</b>, твій провідник у світі Таро 🔮\n"
        "🃏 <b>Карта дня</b> — енергія твого сьогодні.\n"
        "🔮 <b>Розкласти карти</b> — обери напрямок: любов, кар’єра чи гроші.\n"
        "💎 <b>Бонуси</b> — отримай +3 карти щодня або за друзів 💫"
    )
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=ReplyKeyboardMarkup(REPLY_KEYBOARD, resize_keyboard=True))

# ---------------------------------------------------------------------------
# 🔮 Категорії
async def show_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["💞 Любов", "💼 Кар’єра", "💰 Гроші"], ["⬅️ Назад"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    phrases = [
        "Єнот тасує карти... Куди зазирнемо сьогодні? 🔮🦝",
        "Серце, гаманець чи кар’єра? Обери свій шлях 💞💰💼",
    ]
    await update.message.reply_text(random.choice(phrases), reply_markup=reply_markup)

# ---------------------------------------------------------------------------
# 🃏 Обробка категорії
async def handle_category_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_info = get_user_info(str(user.id))
    available_spreads = int(user_info.get("available_spreads", 0))
    if available_spreads <= 0:
        await update.message.reply_text("🃏 У тебе закінчились карти на сьогодні! Повертайся завтра 🌙 або запроси друга 💫")
        return

    row_index, _ = find_user_row(str(user.id))
    users_sheet.update_cell(row_index, get_col_index("available_spreads"), available_spreads - 1)

    category_map = {"💞 Любов": "love", "💼 Кар’єра": "career", "💰 Гроші": "money"}
    category = category_map.get(update.message.text)
    if not category:
        return

    card = random.choice(cards)
    meanings = card["meanings"].get(category, {})
    description = random.choice(meanings.get("descriptions", ["Ця карта ще не має опису для цієї категорії."]))
    raccoon = random.choice(meanings.get("raccoons", ["Єнот мовчить, бо ще пише маніфест 🦝🖋️"]))
    context.user_data["last_card"] = (card, raccoon)

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
    _, raccoon_text = data
    await update.message.reply_text(f"🦝 Коментар Єнота:\n{raccoon_text}")

# ---------------------------------------------------------------------------
# 💫 AI-розклади
async def show_paid_services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_developer(user.id):
        await update.message.reply_text("⚠️ Цей розділ поки що доступний лише розробнику 🦝")
        return
    keyboard = [
        ["💫 Індивідуальний AI-розклад (10⭐️)"],
        ["🌌 AI-Астрологічний прогноз (12⭐️)"],
        ["🔢 AI-Нумерологічний портрет (10⭐️)"],
        ["✋ AI-Хіромантія (15⭐️)"],
        ["⬅️ Назад"],
    ]
    await update.message.reply_text("🪄 Обери магічну послугу 🌙", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

# ---------------------------------------------------------------------------
# 💳 Оплата Stars
async def send_payment_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    services = {
        "💫 Індивідуальний AI-розклад (10⭐️)": ("ai_tarot", 10),
        "🌌 AI-Астрологічний прогноз (12⭐️)": ("ai_astrology", 12),
        "🔢 AI-Нумерологічний портрет (10⭐️)": ("ai_numerology", 10),
        "✋ AI-Хіромантія (15⭐️)": ("ai_chiromancy", 15),
    }
    if text not in services:
        return

    product, amount = services[text]
    if SANDBOX_MODE:
        await update.message.reply_text(f"🧪 Тестовий режим: {product} — {amount}⭐️ не списано.\nЄнот підтверджує, все працює ✨")
        return

    prices = [LabeledPrice(label=text, amount=amount)]
    await context.bot.send_invoice(
        chat_id=update.effective_chat.id,
        title=text,
        description="Магічна послуга від Єнота 🦝✨",
        payload=product,
        provider_token="",
        currency="XTR",
        prices=prices,
        start_parameter="mystic_enot_stars",
    )

# ---------------------------------------------------------------------------
async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    await query.answer(ok=True)

# ---------------------------------------------------------------------------
async def handle_successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    product = update.message.successful_payment.invoice_payload
    user = update.effective_user
    await update.message.reply_text("✅ Оплата успішна! Єнот уже готує твою магію... 🦝✨")
    try:
        if product == "ai_tarot":
            await update.message.reply_text(generate_ai_tarot(user.first_name))
        elif product == "ai_astrology":
            await update.message.reply_text(generate_ai_astrology(user.first_name, "1995-01-01"))
        elif product == "ai_numerology":
            await update.message.reply_text(generate_ai_numerology("1995-01-01"))
        elif product == "ai_chiromancy":
            await update.message.reply_text(generate_ai_chiromancy("долоня з чіткими лініями життя"))
    except Exception as e:
        await update.message.reply_text(f"⚠️ Помилка AI: {e}")

# ---------------------------------------------------------------------------
# 💎 Моя скринька
async def show_my_chest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = get_user_info(str(user.id))
    if not user_data:
        await update.message.reply_text("Єнот не знайшов твою скриньку 🦝 Спробуй /start ще раз.")
        return

    available_spreads = user_data.get("available_spreads", 0)
    referrals_count = user_data.get("referrals_count", 0)
    referral_code = user_data.get("referral_code", "")
    referral_link = f"https://t.me/TaroEnotBot?start={referral_code}"

    rank = "🌱 Молодий шаман" if referrals_count < 3 else "🔮 Магічний учень" if referrals_count < 6 else "🦝 Майстер Єнотової магії"

    text = (
        f"💎 <b>Твоя магічна скринька</b>\n\n"
        f"🔮 <b>Доступних розкладів:</b> {available_spreads}\n"
        f"💞 <b>Запрошено друзів:</b> {referrals_count}\n"
        f"🏅 <b>Рівень:</b> {rank}\n\n"
        f"🔗 <b>Реферальне посилання:</b>\n{referral_link}\n\n"
        "Поділися з другом — отримай +3 карти 💫"
    )
    await update.message.reply_text(text, parse_mode="HTML")

# ---------------------------------------------------------------------------
# 📘 Як працює бот
async def send_how_it_works(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "✨ <b>Як працює Містичний Єнот</b> 🦝🔮\n\n"
        "💫 Індивідуальні розклади — персональні AI-передбачення.\n"
        "🃏 Карта дня — щоденна підказка Всесвіту.\n"
        "🔮 Розкласти карти — любов, кар’єра, гроші.\n"
        "💎 Бонуси — +3 карти щодня або за друзів.\n"
        "🎁 Усе це — з любов’ю від Єнота 🦝✨"
    )
    await update.message.reply_text(text, parse_mode="HTML")

# ---------------------------------------------------------------------------
async def terms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📜 Умови користування: всі розклади є розважальним контентом 🌙")

async def paysupport(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛟 Підтримка оплат: напишіть @TaroEnotBot (DM) з чеком або скрином.")

# ---------------------------------------------------------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "💫 Індивідуальні розклади (BETA)":
        await show_paid_services(update, context)
    elif text in [
        "💫 Індивідуальний AI-розклад (10⭐️)",
        "🌌 AI-Астрологічний прогноз (12⭐️)",
        "🔢 AI-Нумерологічний портрет (10⭐️)",
        "✋ AI-Хіромантія (15⭐️)",
    ]:
        await send_payment_invoice(update, context)
    elif text == "🃏 Карта дня":
        await get_daily_card(update, context)
    elif text == "🔮 Розкласти карти":
        await show_categories(update, context)
    elif text in ["💞 Любов", "💼 Кар’єра", "💰 Гроші"]:
        await handle_category_choice(update, context)
    elif text == "🦝 Коментар Єнота":
        await handle_raccoon_comment_text(update, context)
    elif text == "💎 Бонуси та запрошення":
        await show_my_chest(update, context)
    elif text == "Як працює бот ❓":
        await send_how_it_works(update, context)
    elif text == "⬅️ Назад":
        await back_to_main_menu(update, context)
    else:
        await update.message.reply_text("🦝 Єнот не розуміє цю команду. Вибери з меню нижче.")

# ---------------------------------------------------------------------------
def build_application(token: str) -> Application:
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("terms", terms))
    app.add_handler(CommandHandler("paysupport", paysupport))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(raccoon_interpretation_callback, pattern="^raccoon_interpretation$"))
    app.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, handle_successful_payment))
    return app

# ---------------------------------------------------------------------------
def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN environment variable is not set")

    run_health_server()
    app = build_application(token)
    LOGGER.info("✅ Містичний Єнот запущений і готовий до магії!")
    while True:
        try:
            app.run_polling()
        except Exception as e:
            LOGGER.error(f"❌ Polling error: {e}")
            time.sleep(10)

# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()
