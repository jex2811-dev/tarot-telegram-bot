import os
import requests

# 🔑 Беремо токен із Render Environment Variables
HF_TOKEN = os.getenv("HF_TOKEN")

def get_ai_reading(prompt: str, model: str = "mistralai/Mistral-7B-Instruct-v0.1") -> str:
    """Отримуємо текстову відповідь від Hugging Face API."""
    try:
        headers = {
            "Authorization": f"Bearer {HF_TOKEN}",
            "Content-Type": "application/json",
        }
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 300,
                "temperature": 0.8,
                "top_p": 0.95,
            },
        }

        response = requests.post(
            f"https://api-inference.huggingface.co/models/{model}",
            headers=headers,
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()

        if isinstance(data, list) and "generated_text" in data[0]:
            return data[0]["generated_text"].strip()
        elif isinstance(data, dict) and "generated_text" in data:
            return data["generated_text"].strip()
        else:
            return "🦝 Єнот задумався... AI зараз у тумані. Спробуй пізніше ✨"

    except Exception as e:
        return f"⚠️ Єнот не зміг зв’язатись із Всесвітом Hugging Face: {e}"

# 💫 Індивідуальний AI-розклад
def generate_ai_tarot(name: str, age: int = None, topic: str = None) -> str:
    prompt = (
        f"Ти — містичний єнот-таролог 🦝✨. "
        f"Створи персональний розклад для {name}"
        f"{', ' + str(age) + ' років' if age else ''}"
        f"{', тема: ' + topic if topic else ''}. "
        f"7–10 речень у теплій і магічній манері, з позитивним фіналом."
    )
    return get_ai_reading(prompt)

# 🌌 AI-Астрологічний прогноз
def generate_ai_astrology(name: str, birthdate: str) -> str:
    prompt = (
        f"Ти — єнот-астролог 🦝✨. "
        f"На основі дати народження {birthdate} створи прогноз (10–12 речень) "
        f"про характер, кохання, кар’єру й енергію для {name}."
    )
    return get_ai_reading(prompt)

# 🔢 AI-Нумерологічний портрет
def generate_ai_numerology(birthdate: str) -> str:
    digits = [int(d) for d in birthdate if d.isdigit()]
    destiny = sum(digits)
    while destiny > 9:
        destiny = sum(int(d) for d in str(destiny))
    prompt = (
        f"Ти — єнот-нумеролог 🦝✨. "
        f"Число долі користувача — {destiny}. "
        "Опиши його енергію, характер і життєву місію у 7–9 реченнях."
    )
    return get_ai_reading(prompt, model="gpt2")

# 🖐 AI-Хіромантія (із фото)
def generate_ai_chiromancy(photo_caption: str) -> str:
    prompt = (
        f"Ти — містичний єнот-хіромант 🦝✨. Фото показує: {photo_caption}. "
        "Опиши долоню детально (8–12 речень): лінії життя, серця, розуму, "
        "характер і майбутнє, у магічному та теплому стилі."
    )
    return get_ai_reading(prompt)
