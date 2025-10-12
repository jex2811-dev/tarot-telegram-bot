from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from random import choice
from cards import cards
from gsheets_helper import add_history, has_received_card_today


# ---------------------------------------------------------------------------
# 🃏 Отримати карту дня
async def get_daily_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    # 🔹 Перевірка — чи користувач вже отримував карту сьогодні
    if has_received_card_today(user_id):
        await update.message.reply_text(
            "🕘 Ти вже отримав свою карту дня сьогодні.\n"
            "Повернись завтра за новими підказками Всесвіту 🌙"
        )
        return

    # 🔮 Випадкова карта
    card = choice(cards)
    title = card["title"]
    description = card["meanings"]["day"]["description"]
    photo = card["photo_url"]

    # 🗃 Зберігаємо в історію
    add_history(user_id=user_id, spread_type="Карта дня", cards=title)

    # 🔹 Кнопка “Тлумачення від Єнота”
    keyboard = [
        [InlineKeyboardButton("Що думає Єнот 🦝", callback_data="raccoon_interpretation")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # 🖼 Надсилаємо зображення з описом
    try:
        await update.message.reply_photo(
            photo=photo,
            caption=f"<b>{title}</b>\n\n{description}",
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(
            f"⚠️ Не вдалося завантажити зображення для карти: {title}\nПомилка: {e}"
        )
        return

    # 💾 Зберігаємо карту для подальшого тлумачення від Єнота
    context.user_data["last_card"] = card


# ---------------------------------------------------------------------------
# 🦝 Інтерпретація від Єнота
async def raccoon_interpretation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    card = context.user_data.get("last_card")
    if not card:
        await query.edit_message_text(
            "🤷‍♂️ Єнот загубив карту... спробуй витягнути нову 🃏"
        )
        return

    # 🦝 Беремо тлумачення саме з категорії 'day'
    raccoon_text = card["meanings"]["day"]["raccoon"]

    await query.message.reply_text(
        f"🦝 <b>Що думає Єнот:</b>\n\n{raccoon_text}",
        parse_mode="HTML"
    )
