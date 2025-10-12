import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date
import random

# 🔹 ID твоєї таблиці Google Sheets
SHEET_ID = "1c5mZaUnlkHH3EGWBbbYwujYXZkM-1bRN_vkNEsQy_5M"

# 🔹 Дозволи для доступу до Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# ✅ Зчитування credentials з секретного файлу (Render → Secret Files → google-credentials.json)
creds = ServiceAccountCredentials.from_json_keyfile_name("/etc/secrets/google-credentials.json", scope)
client = gspread.authorize(creds)

# 🔹 Підключаємо таблиці
users_sheet = client.open_by_key(SHEET_ID).worksheet("users")
history_sheet = client.open_by_key(SHEET_ID).worksheet("history")

# ---------------------------------------------------------------------------
# 🧭 Знайти користувача в таблиці
def find_user_row(user_id: str):
    records = users_sheet.get_all_records()
    for i, row in enumerate(records, start=2):  # start=2 — пропускаємо заголовок
        if str(row.get("id")) == str(user_id):
            return i, row
    return None, None


# ---------------------------------------------------------------------------
# 🪄 Генеруємо унікальний реферальний код
def generate_referral_code(user_id: str) -> str:
    return f"REF{user_id}"


# ---------------------------------------------------------------------------
# 🔍 Знаходимо користувача за реферальним кодом
def find_user_by_referral_code(ref_code: str):
    records = users_sheet.get_all_records()
    for i, row in enumerate(records, start=2):
        if row.get("referral_code") == ref_code:
            return i, row
    return None, None


# ---------------------------------------------------------------------------
# 🧙‍♂️ Додаємо нового користувача (з реферальною системою +3 обом)
def add_user(user_id, username, first_name, referral_code="NONE", referred_by=None):
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    today = str(date.today())

    # Перевіряємо, чи користувач вже є
    row_index, existing_user = find_user_row(user_id)
    if existing_user:
        update_daily_spreads(user_id)
        return

    # Генеруємо власний referral_code
    user_referral_code = generate_referral_code(user_id)

    # Базові значення
    available_spreads = 3
    referrals_count = 0

    # 🧩 Якщо користувач прийшов за реферальним кодом
    if referred_by and referred_by != "NONE":
        ref_row, ref_user = find_user_by_referral_code(referred_by)
        if ref_row and ref_user:
            try:
                # ✅ Додаємо бонус запросившому (+3)
                current_spreads = int(ref_user.get("available_spreads", 3))
                users_sheet.update_cell(ref_row, get_col_index("available_spreads"), current_spreads + 3)

                # ✅ Оновлюємо кількість запрошених
                current_refs = int(ref_user.get("referrals_count", 0))
                users_sheet.update_cell(ref_row, get_col_index("referrals_count"), current_refs + 1)

                # ✅ Новому користувачу теж +3 бонус
                available_spreads += 3

                print(f"🎁 {first_name} приєднався за кодом {referred_by}! Обидва отримали +3 карти!")

            except Exception as e:
                print("⚠️ Помилка при оновленні даних реферала:", e)

    # Створюємо нового користувача
    new_user = [
        str(user_id),
        username,
        first_name,
        user_referral_code,
        referred_by or "NONE",
        available_spreads,  # 🔮 карти з бонусом (3 або 6)
        referrals_count,
        today,  # last_reset
        now,  # created_at
    ]
    users_sheet.append_row(new_user)
    print(f"✅ Новий користувач доданий: {first_name} ({username})")

    # -----------------------------------------------------------------------
    # 🦝 Повідомлення у лог
    if referred_by and 'ref_user' in locals() and ref_user:
        print(f"💫 Бонус! {ref_user.get('first_name')} отримав +3 карти, {first_name} — теж +3.")


# ---------------------------------------------------------------------------
# 🧾 Отримуємо номер колонки за назвою
def get_col_index(name: str) -> int:
    headers = users_sheet.row_values(1)
    return headers.index(name) + 1


# ---------------------------------------------------------------------------
# 🔄 Щоденне оновлення карт (3/день)
def update_daily_spreads(user_id: str):
    row_index, user = find_user_row(user_id)
    if not user:
        return

    today = str(date.today())
    last_reset = str(user.get("last_reset", ""))

    if today != last_reset:
        users_sheet.update_cell(row_index, get_col_index("available_spreads"), 3)
        users_sheet.update_cell(row_index, get_col_index("last_reset"), today)
        print(f"🔄 Оновлено денний ліміт для {user.get('first_name')}")


# ---------------------------------------------------------------------------
# 📦 Отримати інформацію користувача (для “Моя скринька 📦”)
def get_user_info(user_id: str):
    row_index, user = find_user_row(user_id)
    if not user:
        return None

    today = str(date.today())
    last_reset = str(user.get("last_reset", ""))

    # 🕓 Якщо новий день — оновлюємо карти
    if today != last_reset:
        users_sheet.update_cell(row_index, get_col_index("available_spreads"), 3)
        users_sheet.update_cell(row_index, get_col_index("last_reset"), today)
        user["available_spreads"] = 3
        user["last_reset"] = today
        print(f"🌅 Автоматично оновлено 3 карти для {user.get('first_name')}")

    return {
        "first_name": user.get("first_name"),
        "username": user.get("username"),
        "referral_code": user.get("referral_code"),
        "referred_by": user.get("referred_by"),
        "available_spreads": int(user.get("available_spreads", 0)),
        "referrals_count": int(user.get("referrals_count", 0)),
        "last_reset": user.get("last_reset"),
        "row_index": row_index,
        "available_spreads_col": get_col_index("available_spreads"),
    }


# ---------------------------------------------------------------------------
# 🕓 Додаємо запис в історію (карти, категорії)
def add_history(user_id, spread_type, cards):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    row = [user_id, spread_type, cards, today]
    history_sheet.append_row(row)


# ---------------------------------------------------------------------------
# 🔍 Перевіряємо: чи вже видавалась карта дня
def has_received_card_today(user_id: str) -> bool:
    records = history_sheet.get_all_records()
    today = datetime.utcnow().strftime("%Y-%m-%d")

    for row in records:
        if (
            str(row.get("user_id")) == user_id
            and row.get("spread_type") == "Карта дня"
            and row.get("date") == today
        ):
            return True
    return False
