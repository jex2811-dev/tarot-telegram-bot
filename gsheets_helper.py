import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

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

# ➕ Додати нового користувача
def add_user(user_id, username, first_name, referral_code=""):
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    row = [user_id, username, first_name, referral_code, "", 0, now, now]
    users_sheet.append_row(row)

# 🕓 Додати запис у історію (для карти дня, категорій і т.д.)
def add_history(user_id, spread_type, cards):
    today = datetime.utcnow().strftime("%Y-%m-%d")  # тільки дата
    row = [user_id, spread_type, cards, today]
    history_sheet.append_row(row)

# 🔍 Перевірка: чи вже видавалась карта дня сьогодні
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
