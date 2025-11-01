#!/usr/bin/env python3
"""Містичний Єнот 🦝✨ — повна логіка + AI без списання зірок (SANDBOX ai_only)"""

from __future__ import annotations
import logging
import os
import random
import time
import threading
import asyncio
from datetime import datetime
from typing import Final
from flask import Flask

from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)

# ✅ Локальні модулі
from daily_card import get_daily_card, raccoon_interpretation_callback
from gsheets_helper import add_user, get_user_info, users_sheet, find_user_row, get_col_index
from cards import cards
from ai_free import (
    generate_ai_tarot,
    generate_ai_astrology,
    generate_ai_numerology,
    generate_ai_chiromancy,
    generate_ai_chiromancy_photo,
)

# ---------------------------------------------------------------------------
# ⚙️ Конфіг
DEVELOPER_ID = 1545533785
BETA_MODE = True
SANDBOX_MODE = "live"  # 💫 Увімкнено реальну оплату Telegram Stars
# ---------------------------------------------------------------------------

LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

# 🏠 Головне меню
REPLY_KEYBOARD: Final[list[list[str]]] = [
    ["💫 Індивідуальні розклади (BETA)", "🃏 Карта дня"],
    ["🔮 Розкласти карти", "💎 Бонуси та запрошення"],
    ["Як працює бот ❓"],
]

# ---------------------------------------------------------------------------
# 🌐 Keep-alive для Render
def run_health_server():
    app = Flask(__name__)
    @app.route("/")
    def index():
        return "🦝 MysticEnotBot живий і тасує карти ✨"
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=8080), daemon=True).start()

# ---------------------------------------------------------------------------
# ⌛️ Маленькі живі затримки
async def pause_typing(update: Update, seconds: float):
    try:
        await update.effective_chat.send_action("typing")
    except Exception:
        pass
    await asyncio.sleep(seconds)

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
        return True
    except Exception as e:
        LOGGER.error(f"❌ Помилка бонусу: {e}")
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

    if give_daily_bonus_if_needed(str(user.id)):
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
        "💎 <b>Бонуси та запрошення</b> — реферальні подарунки та рівень мага.\n"
        "Натискай кнопку нижче — почнемо магію! ✨"
    )
    await update.message.reply_text(text, parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(REPLY_KEYBOARD, resize_keyboard=True))

# ---------------------------------------------------------------------------
# 🔮 Показ категорій
async def show_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["💞 Любов", "💼 Кар’єра", "💰 Гроші"], ["⬅️ Назад"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        random.choice([
            "Єнот тасує карти... Куди зазирнемо сьогодні? 🔮🦝",
            "Серце, гаманець чи кар’єра? Обери свій шлях 💞💰💼",
            "Любов, гроші чи слава — що підкаже Всесвіт сьогодні? 💫",
        ]),
        reply_markup=reply_markup
    )

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
    meanings = card["meanings"].get(category, {})
    description = random.choice(meanings.get("descriptions", ["Ця карта ще не має опису для цієї категорії."]))
    raccoon = random.choice(meanings.get("raccoons", ["Єнот мовчить, бо ще пише маніфест 🦝🖋️"]))
    context.user_data["last_card"] = (card, category, raccoon)

    await pause_typing(update, 1.2)
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
    await pause_typing(update, 1.0)
    await update.message.reply_text(f"🦝 Коментар Єнота:\n{raccoon_text}")

# ---------------------------------------------------------------------------
# 💫 Меню AI-сервісів (у BETA для тебе доступне одразу)
async def show_paid_services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # якщо захочеш знову обмежити — розкоментуй блок:
    # if not is_developer(update.effective_user.id):
    #     await update.message.reply_text("🧪 Ця магічна функція ще тестується Єнотом 🦝✨")
    #     return
    keyboard = [
        ["💫 Індивідуальний AI-розклад"],
        ["🌌 AI-Астрологічний прогноз"],
        ["🔢 AI-Нумерологічний портрет"],
        ["✋ AI-Хіромантія"],
        ["⬅️ Назад"],
    ]
    await update.message.reply_text("🪄 Обери магічну послугу 🌙",
                                    reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

# ---------------------------------------------------------------------------
# 🧾 “Оплата” у SANDBOX: запускаємо діалог збору даних
async def send_payment_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "💫 Індивідуальний AI-розклад":
        await update.message.reply_text("✨ Напиши, будь ласка, своє ім’я:")
        context.user_data["mode"] = "ai_tarot_name"

    elif text == "🌌 AI-Астрологічний прогноз":
        await update.message.reply_text("🌙 Як тебе звати?")
        context.user_data["mode"] = "ai_astrology_name"

    elif text == "🔢 AI-Нумерологічний портрет":
        await update.message.reply_text("🔢 Напиши своє ім’я:")
        context.user_data["mode"] = "ai_numerology_name"

    elif text == "✋ AI-Хіромантія":
        await update.message.reply_text("🖐️ Як тебе звати?")
        context.user_data["mode"] = "ai_chiromancy_name"

# ---------------------------------------------------------------------------
# 🧭 Діалоги збору даних (UX)
async def handle_ai_dialog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get("mode")
    if not mode:
        return
    user_input = update.message.text

    # --- Індивідуальний AI-розклад
    if mode == "ai_tarot_name":
        context.user_data["name"] = user_input.strip()
        await update.message.reply_text("🔢 Скільки тобі років?")
        context.user_data["mode"] = "ai_tarot_age"
        return

    if mode == "ai_tarot_age":
        # простий захист від нечислових значень
        try:
            age = int(user_input.strip())
            if not (5 <= age <= 120):
                raise ValueError
        except Exception:
            await update.message.reply_text("Введи, будь ласка, реальний вік цифрами 😊")
            return
        context.user_data["age"] = age
        await update.message.reply_text("💭 Про що саме зробити розклад?")
        context.user_data["mode"] = "ai_tarot_topic"
        return

    if mode == "ai_tarot_topic":
        name = context.user_data["name"]
        age = context.user_data["age"]
        topic = user_input.strip()
        await pause_typing(update, 1.2)
        await update.message.reply_text("🌙 Єнот налаштовується на твою енергію… 🦝✨")
        await pause_typing(update, 2.0)
        await update.message.reply_text("🔮 Карти шепочуть... здається, я бачу дещо цікаве 👁️‍🗨️")
        await pause_typing(update, 1.0)
        result = generate_ai_tarot(name, age, topic)
        await update.message.reply_text(result)
        context.user_data.clear()
        return

    # --- Астрологія
    if mode == "ai_astrology_name":
        context.user_data["name"] = user_input.strip()
        await update.message.reply_text("📅 Напиши дату народження (РРРР-ММ-ДД):")
        context.user_data["mode"] = "ai_astrology_birth"
        return

    if mode == "ai_astrology_birth":
        name = context.user_data["name"]
        birth = user_input.strip()
        await pause_typing(update, 1.0)
        await update.message.reply_text("🌌 Єнот вдивляється у зоряне небо... ✨")
        await pause_typing(update, 1.8)
        await update.message.reply_text("⭐️ Зорі шепочуть свої таємниці...")
        await pause_typing(update, 1.0)
        result = generate_ai_astrology(name, birth)
        await update.message.reply_text(result)
        context.user_data.clear()
        return

    # --- Нумерологія
    if mode == "ai_numerology_name":
        context.user_data["name"] = user_input.strip()
        await update.message.reply_text("📅 Напиши дату народження (РРРР-ММ-ДД):")
        context.user_data["mode"] = "ai_numerology_date"
        return

    if mode == "ai_numerology_date":
        birth = user_input.strip()
        name = context.user_data["name"]
        await pause_typing(update, 1.0)
        await update.message.reply_text("🔢 Єнот рахує твої числа... 🧮✨")
        await pause_typing(update, 1.8)
        await update.message.reply_text("💫 Енергії цифр починають рухатись...")
        await pause_typing(update, 1.0)
        result = generate_ai_numerology(birth)
        await update.message.reply_text(f"{name}, ось твій нумерологічний портрет:\n\n{result}")
        context.user_data.clear()
        return

    # --- Хіромантія
    if mode == "ai_chiromancy_name":
        context.user_data["name"] = user_input.strip()
        await update.message.reply_text(
            "📸 Надішли фото своєї долоні або опиши її словами (форма, лінії, текстура) 🌙"
        )
        context.user_data["mode"] = "ai_chiromancy_wait_input"
        return

    if mode == "ai_chiromancy_wait_input":
        # якщо прийшов текст (а не фото)
        desc = user_input.strip()
        if desc:
            name = context.user_data.get("name", "друже")
            await pause_typing(update, 1.0)
            await update.message.reply_text("🖐️ Єнот уявляє лінії та рельєфи долоні... ✨")
            await pause_typing(update, 1.5)
            result = generate_ai_chiromancy(desc)
            await update.message.reply_text(f"{name}, ось що бачить Єнот:\n\n{result}")
            context.user_data.clear()
        return

# ---------------------------------------------------------------------------
# Обробка фото для хіромантії (Vision)
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # працюємо тільки коли чекаємо вхід від хіромантії
    if context.user_data.get("mode") != "ai_chiromancy_wait_input":
        return
    photo = update.message.photo[-1]
    file = await photo.get_file()
    photo_url = file.file_path
    name = context.user_data.get("name", "друже")

    await pause_typing(update, 1.0)
    await update.message.reply_text("🖐️ Єнот уважно вдивляється у твою долоню... 🌙")
    await pause_typing(update, 2.0)
    await update.message.reply_text("🔮 Лінії життя починають світитися... 🦝✨")
    await pause_typing(update, 1.0)
    result = generate_ai_chiromancy_photo(photo_url)
    await update.message.reply_text(f"{name}, ось що бачить Єнот:\n\n{result}")
    context.user_data.clear()

# ---------------------------------------------------------------------------
# 💎 Магічна скринька (реферальна логіка зберігається)
async def show_my_chest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        user_data = get_user_info(str(user.id))
        if not user_data:
            await update.message.reply_text("Єнот не може знайти твою скриньку... 🦝 Спробуй /start ще раз.")
            return

        available_spreads = user_data.get("available_spreads", 0)
        referrals_count = user_data.get("referrals_count", 0)
        referral_code = user_data.get("referral_code", "")
        referral_link = f"https://t.me/TaroEnotBot?start={referral_code}"

        rank = "🌱 Молодий шаман" if referrals_count < 3 else \
               "🔮 Магічний учень" if referrals_count < 6 else "🦝 Майстер Єнотової магії"

        moons = ["🌑🌑🌑", "🌕🌑🌑", "🌕🌕🌑", "🌕🌕🌕"]
        moon = moons[min(int(available_spreads), 3)]

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
            "Поділися ним у Telegram або сторіз — і нехай Єнот віддячить магією 🦝✨"
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
# 📜 /terms і /paysupport — вимоги Telegram (залишаємо)
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

    # якщо триває діалог із користувачем — обробляємо його
    if context.user_data.get("mode"):
        await handle_ai_dialog(update, context)
        return

    if text == "💫 Індивідуальні розклади (BETA)":
        await show_paid_services(update, context)
    elif text in [
        "💫 Індивідуальний AI-розклад",
        "🌌 AI-Астрологічний прогноз",
        "🔢 AI-Нумерологічний портрет",
        "✋ AI-Хіромантія",
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

    # Фото для хіромантії
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # Повідомлення (reply-кнопки)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Інлайн-кнопка для daily_card
    app.add_handler(CallbackQueryHandler(raccoon_interpretation_callback, pattern="^raccoon_interpretation$"))

    # Платежі Stars — залишаємо заглушку (на майбутнє релізи)
    app.add_handler(PreCheckoutQueryHandler(lambda u, c: u.pre_checkout_query.answer(ok=True)))

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
            LOGGER.error(f"❌ Помилка виконання polling: {e}")
            time.sleep(10)

# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()
