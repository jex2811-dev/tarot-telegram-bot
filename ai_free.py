import os
from openai import OpenAI

# ------------------------------------------------------------------------
# 🔑 Підключення API-ключа
# ------------------------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise RuntimeError("❌ OPENAI_API_KEY не знайдено в Environment Variables Render")

client = OpenAI(api_key=OPENAI_API_KEY)

# ------------------------------------------------------------------------
# 🪄 Універсальна функція запиту до ChatGPT
# ------------------------------------------------------------------------
def _ask_openai(prompt: str, temperature: float = 0.85, model: str = "gpt-4o-mini") -> str:
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ти — Містичний Єнот 🦝✨, який говорить українською мовою "
                        "і створює чарівні, теплі та гумористичні передбачення. "
                        "Твій стиль — дружній, магічний, доброзичливий, з легкою містикою."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Єнот не зміг зв’язатись із ChatGPT: {e}"

# ------------------------------------------------------------------------
# 🃏 Індивідуальний AI-розклад
# ------------------------------------------------------------------------
def generate_ai_tarot(name: str, age: int = 25, topic: str = "кохання") -> str:
    prompt = (
        f"Створи персональний магічний розклад для {name}, {age} років. "
        f"Тема: {topic}. "
        "Напиши 7–10 речень: 1) загальна енергія; 2) поради; 3) попередження; "
        "4) маленький ритуал. Тон — теплий, підтримуючий, магічний, без токсичного позитиву."
    )
    return _ask_openai(prompt)

# ------------------------------------------------------------------------
# 🌌 AI-Астрологічний прогноз
# ------------------------------------------------------------------------
def generate_ai_astrology(name: str, birthdate: str) -> str:
    prompt = (
        f"Користувач: {name}, дата народження: {birthdate}. "
        "Зроби прогноз на 10–12 речень про характер, кохання, кар’єру, фінанси "
        "та енергію місяця. Додай 3 конкретні поради та 1 обережність."
    )
    return _ask_openai(prompt)

# ------------------------------------------------------------------------
# 🔢 AI-Нумерологічний портрет
# ------------------------------------------------------------------------
def generate_ai_numerology(birthdate: str) -> str:
    digits = [int(c) for c in birthdate if c.isdigit()]
    n = sum(digits)
    while n > 9:
        n = sum(int(c) for c in str(n))

    prompt = (
        f"Число долі користувача — {n}. "
        "Опиши енергію числа, сильні сторони, виклики, місію та пораду. "
        "Напиши 7–9 речень у стилі єнота-нумеролога 🦝✨."
    )
    return _ask_openai(prompt)

# ------------------------------------------------------------------------
# ✋ AI-Хіромантія (текстовий опис)
# ------------------------------------------------------------------------
def generate_ai_chiromancy(photo_description: str) -> str:
    prompt = (
        f"На фото видно: {photo_description}. "
        "Опиши долоню — лінії життя, серця, розуму; темперамент, ресурси, "
        "поради на 8–12 речень. Додай м’яке застереження і маленьку практику для гармонії."
    )
    return _ask_openai(prompt)

# ------------------------------------------------------------------------
# 📸 AI-Хіромантія з фото (GPT-Vision)
# ------------------------------------------------------------------------
def generate_ai_chiromancy_photo(photo_url: str, user_note: str = "") -> str:
    """
    Аналіз фото долоні через GPT-Vision.
    :param photo_url: URL до фото з Telegram
    :param user_note: короткий опис користувача (опціонально)
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ти — Містичний Єнот 🦝✨, майстер хіромантії. "
                        "Опиши долоню, лінії життя, серця, розуму, потенціал, поради. "
                        "Тон теплий, магічний, з ноткою містики, українською мовою."
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"На фото долоня користувача. {user_note}"},
                        {"type": "image_url", "image_url": {"url": photo_url}},
                    ],
                },
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Єнот не зміг прочитати долоню: {e}"
