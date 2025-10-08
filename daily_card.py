from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from random import choice
from cards import cards
from gsheets_helper import add_history, has_received_card_today
import os


async def get_daily_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    # 🔹 Перевірка — чи вже отримував сьогодні
    if has_received_card_today(user_id):
        await update.message.reply_text(
            "🕘 Ви вже отримали карту дня сьогодні.\nПоверніться завтра за новою мудрістю 🌞"
        )
        return

    # 🔹 Випадкова карта
    card = choice(cards)
    add_history(user_id=user_id, spread_type="Карта дня", cards=card["title"])

    # 🔹 Кнопка "Що думає Єнот 🦝"
    keyboard = [
        [InlineKeyboardButton("Що думає Єнот 🦝", callback_data="raccoon_interpretation")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # 🔹 Повний шлях до зображення (використовуємо правильний ключ 'images')
    image_path = os.path.join(os.getcwd(), card["images"])

    try:
        with open(image_path, "rb") as photo:
            await update.message.reply_photo(
                photo=photo,
                caption=f"<b>{card['title']}</b>\n\n{card['description']}",
                reply_markup=reply_markup,
                parse_mode="HTML",
            )
    except FileNotFoundError:
        await update.message.reply_text(
            f"⚠️ Не вдалося знайти зображення для карти: {card['title']}\n"
            f"🔍 Шлях: {image_path}"
        )
        return

    # 🔹 Зберігаємо карту для інтерпретації Єнота
    context.user_data["last_card"] = card


async def raccoon_interpretation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    card = context.user_data.get("last_card")
    if not card:
        await query.edit_message_text(
            "🤷‍♂️ Не можу знайти картку. Спробуйте ще раз отримати карту дня."
        )
        return

    await query.message.reply_text(
        f"🦝 <b>Що думає Єнот:</b>\n\n{card['raccoon_interpretation']}",
        parse_mode="HTML",
    )
