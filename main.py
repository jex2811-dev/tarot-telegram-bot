#!/usr/bin/env python3
"""Entry point for the Tarot Telegram bot."""

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

# 🏠 Головне меню
REPLY_KEYBOARD: Final[list[list[str]]] = [
    ["💫 Індивідуальні розклади (BETA)", "🃏 Карта дня"],
    ["🔮 Розкласти карти", "💎 Бонуси та запрошення"],
    ["Як працює бот ❓"],
]

# ---------------------------------------------------------------------------
# 🌐 Keep-alive Flask server (Render)
def run_health_server():
    app = Flask(__name__)

    @app.route("/")
    def index():
        return "🦝 MysticEnotBot is alive and shuffling cards! ✨"

    thread = threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=8080),
        daemon=True,
    )
    thread.start()
    LOGGER.info("🌐 Flask keep-alive server запущений на порту 8080")

# ---------------------------------------------------------------------------
# 🎁 Щоденний бонус +3 карт/день
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
# ↩️ Коротке повернення в головне меню
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
        "Єнот підморгує: «Кохання чи кар’єра? Обери, поки карти гарячі!» 🔥",
    ]
    await update.message.reply_text(random.choice(phrases), reply_markup=reply_markup)

# ---------------------------------------------------------------------------
# 🃏 Обробка вибору категорії (списання 1 карти)
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
# 🦝 Коментар Єнота (кнопка з reply-keyboard)
async def handle_raccoon_comment_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data.get("last_card")
    if not data:
        await update.message.reply_text("Спершу обери розклад і карту, а потім натисни «🦝 Коментар Єнота».")
        return
    _, _, raccoon_text = data
    await update.message.reply_text(f"🦝 Коментар Єнота:\n{raccoon_text}")

# ---------------------------------------------------------------------------
# 💫 Меню платних сервісів (доступне лише в BETA для розробника)
async def show_paid_services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_developer(user.id):
        await update.message.reply_text("🧪 Ця магічна функція ще тестується Єнотом 🦝✨")
        return
    keyboard = [
        ["💫 Індивідуальний AI-розклад (10⭐️)"],
        ["🖐 AI-Хіромантія (15⭐️)"],
        ["🌌 AI-Астрологічний прогноз (12⭐️)"],
        ["🔢 AI-Нумерологічний портрет (10⭐️)"],
        ["⬅️ Назад"],
    ]
    await update.message.reply_text("🪄 Обери магічну послугу 🌙",
                                    reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

# ---------------------------------------------------------------------------
# 🧾 Надсилання інвойсу в XTR (Stars). provider_token порожній — це НОРМАЛЬНО для цифрових товарів.
async def send_payment_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text
    services = {
        "💫 Індивідуальний AI-розклад (10⭐️)": ("ai_tarot", 10),
        "🖐 AI-Хіромантія (15⭐️)": ("chiromancy", 15),
        "🌌 AI-Астрологічний прогноз (12⭐️)": ("astrology", 12),
        "🔢 AI-Нумерологічний портрет (10⭐️)": ("numerology", 10),
    }
    if text not in services:
        return

    product, amount = services[text]
    title = text.split("(")[0].strip()
    prices = [LabeledPrice(label=title, amount=amount)]

    LOGGER.info(f"🧾 Надсилаю інвойс: product={product}, amount={amount}⭐️, chat={chat_id}")

    await context.bot.send_invoice(
        chat_id=chat_id,
        title=title,
        description="Магічна послуга від Єнота 🦝✨",
        payload=product,
        provider_token="",          # ✅ для Stars та цифрових товарів
        currency="XTR",              # ✅ обов’язково
        prices=prices,
        start_parameter="mystic_enot_stars",
    )

# ---------------------------------------------------------------------------
# ✅ ОБОВ’ЯЗКОВО для Stars: підтвердити pre_checkout_query (інакше “Loading…”)
async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    try:
        LOGGER.info(f"🟡 pre_checkout_query: {query.invoice_payload} від {query.from_user.id}")
        await query.answer(ok=True)
    except Exception as e:
        LOGGER.error(f"❌ pre_checkout_query error: {e}")
        await query.answer(ok=False, error_message="Єнот не зміг підтвердити оплату 🦝💫")

# ---------------------------------------------------------------------------
# 💳 Успішна оплата → запускаємо відповідну AI-функцію
async def handle_successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name or "Друже"
    payment = update.message.successful_payment
    product = payment.invoice_payload

    LOGGER.info(f"✅ successful_payment: user={user_id}, product={product}, total={payment.total_amount} XTR")

    if BETA_MODE and user_id != DEVELOPER_ID:
        await update.message.reply_text("⚠️ Оплата тимчасово недоступна. Єнот тестує магію 🦝✨")
        return

    await update.message.reply_text("✅ Оплата успішна! Єнот уже готує твою магію... 🦝✨")

    try:
        if product == "ai_tarot":
            await update.message.reply_text("💫 Єнот розкладає карти спеціально для тебе... 🦝✨")
            text = generate_ai_tarot(user_name, 25, "кар'єра")
            await update.message.reply_text(text)
        elif product == "chiromancy":
            await update.message.reply_text("🖐 Єнот розглядає твою долоню... 🦝✨")
            text = generate_ai_chiromancy("долоня з м’якими лініями життя і серця")
            await update.message.reply_text(text)
        elif product == "astrology":
            await update.message.reply_text("🌌 Єнот дивиться на твої зірки... ✨")
            text = generate_ai_astrology(user_name, "01.01.2000")
            await update.message.reply_text(text)
        elif product == "numerology":
            await update.message.reply_text("🔢 Єнот обчислює твоє космічне число долі...")
            text = generate_ai_numerology("01.01.2000")
            await update.message.reply_text(text)
        else:
            await update.message.reply_text("🤔 Єнот ще не знає цієї магії...")
    except Exception as e:
        LOGGER.error(f"❌ Помилка при генерації AI-тексту: {e}")
        await update.message.reply_text("⚠️ Єнот заплутався у зорях... спробуй пізніше 🌙")

# ---------------------------------------------------------------------------
# 💎 Магічна скринька
async def show_my_chest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        user_data = get_user_info(str(user.id))
        if not user_data:
            await update.message.reply_text("Єнот не може знайти твою скриньку... 🦝 Спробуй /start ще раз.")
            return

        available_spreads = user_data["available_spreads"]
        referrals_count = user_data["referrals_count"]
        referral_code = user_data["referral_code"]
        referral_link = f"https://t.me/TaroEnotBot?start={referral_code}"

        rank = "🌱 Молодий шаман" if referrals_count < 3 else \
               "🔮 Магічний учень" if referrals_count < 6 else "🦝 Майстер Єнотової магії"

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
        await update.message.reply_text(chest_text, parse_mode="HTML",
                                        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
    except Exception as e:
        await update.message.reply_text("⚠️ Єнот заплутався у магії Google Sheets... 🦝✨")
        LOGGER.error(f"Помилка в show_my_chest: {e}")

# ---------------------------------------------------------------------------
# 📘 Як працює бот
async def send_how_it_works(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "✨ <b>Як працює Містичний Єнот</b> 🦝🔮\n\n"
        "💫 <b>Індивідуальні розклади</b> — персональні AI-передбачення.\n"
        "🃏 <b>Карта дня</b> — щоденна підказка Всесвіту.\n"
        "🔮 <b>Розкласти карти</b> — любов, кар’єра, гроші.\n"
        "💎 <b>Бонуси та запрошення</b> — твої подарунки та рівень мага.\n"
        "🎁 <b>Щодня</b> — отримуй 3 нові карти безкоштовно 🌙\n\n"
        "<i>Єнот шепоче: навіть випадкові карти — не випадковість 🌙</i>"
    )
    await update.message.reply_text(text, parse_mode="HTML")

# ---------------------------------------------------------------------------
# 📜 /terms і /paysupport — базові вимоги Telegram для продажів
async def terms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📜 Умови користування: цифрові розклади та поради є розважальним контентом.\n"
        "Повернення можливе у разі технічної помилки. Пишіть у /paysupport."
    )

async def paysupport(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛟 Підтримка оплат: напишіть @TaroEnotBot (DM) із деталями чека або скриншотом."
    )

# ---------------------------------------------------------------------------
# 🧭 Роутер повідомлень
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "💫 Індивідуальні розклади (BETA)":
        await show_paid_services(update, context)
    elif text in [
        "💫 Індивідуальний AI-розклад (10⭐️)",
        "🖐 AI-Хіромантія (15⭐️)",
        "🌌 AI-Астрологічний прогноз (12⭐️)",
        "🔢 AI-Нумерологічний портрет (10⭐️)",
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
        await update.message.reply_text("Оберіть команду з меню ⬇️")

# ---------------------------------------------------------------------------
def build_application(token: str) -> Application:
    app = Application.builder().token(token).build()

    # Команди
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("terms", terms))
    app.add_handler(CommandHandler("paysupport", paysupport))

    # Повідомлення (reply-кнопки)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Інлайн-кнопка для daily_card
    app.add_handler(CallbackQueryHandler(raccoon_interpretation_callback, pattern="^raccoon_interpretation$"))

    # Платежі Stars
    app.add_handler(PreCheckoutQueryHandler(precheckout_callback))                  # ✅ обов’язково
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, handle_successful_payment))

    return app

# ---------------------------------------------------------------------------
def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

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
