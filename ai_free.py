# ai_free.py
import os
import logging
import requests

# 🧩 Ініціалізація логів
LOGGER = logging.getLogger(__name__)

# 🔑 Твій токен із Render → Environment → HF_TOKEN
HF_TOKEN = os.getenv("HF_TOKEN")
if not HF_TOKEN:
    raise RuntimeError("❌ HF_TOKEN is not set in Render environment variables.")

# 🌐 Новий офіційний endpoint (Hugging Face router API)
BASE_URL = "https://router.huggingface.co/hf-inference/models"

# 🔮 Моделі, що гарантовано підтримуються router API
CANDIDATE_MODELS = [
    "google/gemma-2b-it",             # ✅ стабільна, безкоштовна і швидка
    "HuggingFaceH4/zephyr-7b-beta",   # 🧠 інтелектуальніша, але повільніша
    "tiiuae/falcon-7b-instruct",      # ⚙️ резервна модель
]

# ⚙️ Заголовки запиту
HEADERS = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json",
    "User-Agent": "MysticEnotBot/1.0",
}


# ------------------------- ОСНОВНА ФУНКЦІЯ -------------------------
def _hf_generate(prompt: str, max_new_tokens: int = 220, temperature: float = 0.8) -> str:
    """Генерує текст через Hugging Face router API."""
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": max_new_tokens,
            "temperature": temperature,
            "return_full_text": False,
        },
        "options": {"wait_for_model": True},
    }

    last_err = None

    for model_id in CANDIDATE_MODELS:
        url = f"{BASE_URL}/{model_id}"
        try:
            r = requests.post(url, headers=HEADERS, json=payload, timeout=70)
            if r.status_code == 404:
                LOGGER.warning(f"HF 404 for model {model_id} — пропускаю")
                continue
            if r.status_code in (429, 503):
                msg = "Сервіс Hugging Face тимчасово перевантажений. Спробуй ще раз 🦝✨"
                return f"⚠️ {msg}"

            r.raise_for_status()
            data = r.json()

            # 🔍 Обробка відповіді
            text = None
            if isinstance(data, list) and data and isinstance(data[0], dict):
                text = data[0].get("generated_text")
            elif isinstance(data, dict):
                text = data.get("generated_text")

            if not text:
                text = str(data)

            return text.strip()

        except Exception as e:
            last_err = e
            LOGGER.exception(f"HF error with {model_id}: {e}")
            continue

    # Якщо всі моделі впали
    raise RuntimeError(f"All HF models failed. Last error: {last_err}")


# ------------------------- ПУБЛІЧНІ ФУНКЦІЇ -------------------------
def generate_ai_tarot(name: str, age: int = 25, topic: str = "кохання") -> str:
    prompt = (
        "Ти — містичний єнот-таролог 🦝✨. Пиши українською. "
        f"Створи персональний розклад для {name}, {age} років, тема: {topic}. "
        "Дай 7–10 речень: 1) загальна енергія; 2) поради; 3) попередження; 4) маленький ритуал. "
        "Тон: теплий, підтримуючий, магічний, без токсичного позитиву."
    )
    try:
        return _hf_generate(prompt, max_new_tokens=260, temperature=0.85)
    except Exception as e:
        return f"⚠️ Єнот не зміг зв’язатися з Hugging Face: {e}"


def generate_ai_astrology(name: str, birthdate: str) -> str:
    prompt = (
        "Ти — єнот-астролог 🦝✨. Пиши українською. "
        f"Користувач: {name}, дата народження {birthdate}. "
        "Зроби прогноз на 10–12 речень про характер, кохання, кар’єру, фінанси та енергію місяця. "
        "Дай 3 конкретні поради та 1 обережність."
    )
    try:
        return _hf_generate(prompt, max_new_tokens=280, temperature=0.8)
    except Exception as e:
        return f"⚠️ Єнот не дістав зірки для астрології: {e}"


def generate_ai_numerology(birthdate: str) -> str:
    digits = [int(c) for c in birthdate if c.isdigit()]
    n = sum(digits)
    while n > 9:
        n = sum(int(c) for c in str(n))

    prompt = (
        "Ти — єнот-нумеролог 🦝✨. Пиши українською. "
        f"Число долі користувача — {n}. "
        "Опиши енергію числа, сильні сторони, виклики, місію та пораду. 7–9 речень."
    )
    try:
        return _hf_generate(prompt, max_new_tokens=220, temperature=0.8)
    except Exception as e:
        return f"⚠️ Єнот не порахував зірочки: {e}"


def generate_ai_chiromancy(photo_description: str) -> str:
    prompt = (
        "Ти — містичний єнот-хіромант 🦝✨. Пиши українською. "
        f"На фото видно: {photo_description}. "
        "Опиши долоню: лінії життя/серця/розуму, темперамент, ресурси, поради на 8–12 речень. "
        "Додай м’яке застереження і маленьку практику."
    )
    try:
        return _hf_generate(prompt, max_new_tokens=260, temperature=0.85)
    except Exception as e:
        return f"⚠️ Єнот загубився між лініями долі: {e}"
