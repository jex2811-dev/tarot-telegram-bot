from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import random
from cards import cards
from gsheets_helper import add_history, has_received_card_today

# ---------------------------------------------------------------------------
# 🃏 Карта дня
async def get_daily_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    # 🔹 Перевіряємо, чи вже отримував сьогодні
    if has_received_card_today(user_id):
        await update.message.reply_text(
            "🕘 Ти вже отримав свою карту дня сьогодні.\n"
            "Повернись завтра за новими підказками Всесвіту 🌙"
        )
        return

    # 🔹 Випадкова карта
    card = random.choice(cards)
    title = card["title"]
    photo_url = card["photo_url"]

    # 🔹 Беремо випадковий опис і коментар Єнота
    meanings = card["meanings"].get("day", {})
    if "descriptions" in meanings and "raccoons" in meanings:
        description = random.choice(meanings["descriptions"])
        raccoon = random.choice(meanings["raccoons"])
    else:
        description = "Ця карта ще не має опису для карти дня 🌙"
        raccoon = "Єнот ще не встиг написати тлумачення... але каже, що все буде добре 🦝✨"

    # 🔹 Додаємо запис в історію (Google Sheets)
    add_history(user_id=user_id, spread_type="Карта дня", cards=title)

    # 🔹 Кнопка «Що думає Єнот 🦝»
    keyboard = [[InlineKeyboardButton("Що думає Єнот 🦝", callback_data="raccoon_interpretation")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # 🔹 Відправляємо фото з описом
    await update.message.reply_photo(
        photo=photo_url,
        caption=f"<b>{title}</b>\n\n{description}",
        parse_mode="HTML",
        reply_markup=reply_markup
    )

    # 🔹 Зберігаємо карту й тлумачення в контекст
    context.user_data["last_card"] = {
        "card": card,
        "raccoon": raccoon
    }

# ---------------------------------------------------------------------------
# 🦝 Тлумачення від Єнота (через callback-кнопку)
async def raccoon_interpretation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    last_card_data = context.user_data.get("last_card")
    if not last_card_data:
        await query.edit_message_text("🤷‍♂️ Єнот загубив карту... Спробуй витягнути нову 🃏")
        return

    raccoon_text = last_card_data.get("raccoon", "Єнот задумався... спробуй ще раз 🦝💫")

    # 🔹 Відповідь окремим повідомленням (щоб не затирати карту)
    await query.message.reply_text(
        f"🦝 <b>Що думає Єнот:</b>\n\n{raccoon_text}",
        parse_mode="HTML"
    )
