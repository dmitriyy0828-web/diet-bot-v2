"""Сервис Gemma 2B для понимания естественного языка при редактировании."""
import json
import logging
import requests
from src.config import config

logger = logging.getLogger(__name__)


def parse_edit_command(text: str, available_foods: list[str] = None) -> dict:
    """
    Анализирует текст редактирования через Gemma 2B.

    Args:
        text: Текст от пользователя (голос или сообщение)
        available_foods: Список названий продуктов в текущей записи (для пункт 7)

    Returns:
        dict: {"action": "change_grams"|"change_calories"|"change_product"|"unclear",
               "value": число,
               "target": название_продукта или None,
               "new_product": новый_продукт или None,
               "clarification_needed": True/False}

    Примеры:
    - "150 граммов" → {"action": "change_grams", "value": 150, "target": null}
    - "300 калорий" → {"action": "change_calories", "value": 300, "target": null}
    - "измени гречку на 200 грамм" → {"action": "change_grams", "value": 200, "target": "гречка"}
    - "хочу рис вместо гречки" → {"action": "change_product", "new_product": "рис", "target": "гречка"}
    - "сто пятьдесят грамм" → {"action": "change_grams", "value": 150}
    """

    system_prompt = """Ты — ассистент по учету калорий. Проанализируй текст пользователя, который хочет изменить запись о еде.

ПРАВИЛА:
1. Числа прописью преобразуй в цифры ("сто пятьдесят" → 150)
2. Если есть конкретное число + "грамм/г" → action: change_grams
3. Если есть конкретное число + "калор/ккал" → action: change_calories
4. Если упоминается смена продукта ("вместо", "не ... а ...") → action: change_product
5. Если упоминается порядковый номер ("первое", "второй", "последний") → target: по порядку
6. Если непонятно что менять → clarification_needed: true

ФОРМАТ ОТВЕТА (строго JSON, без markdown):
{
  "action": "change_grams"|"change_calories"|"change_product"|"unclear",
  "value": число или null,
  "target": "название продукта" или "первое"|"второй"|"третий" или null,
  "new_product": "новый продукт" или null,
  "clarification_needed": false
}

ЕСЛИ target null и доступно несколько продуктов — clarification_needed: true"""

    foods_context = ""
    if available_foods:
        foods_context = f"\nДоступные продукты: {', '.join(available_foods)}"

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://diet-bot.local",
                "X-Title": "Diet Bot",
            },
            json={
                "model": "google/gemma-2-9b-it",
                "messages": [
                    {"role": "system", "content": system_prompt + foods_context},
                    {"role": "user", "content": f'"{text}"'},
                ],
                "max_tokens": 200,
                "temperature": 0.1,
            },
            timeout=10,
        )

        response.raise_for_status()
        data = response.json()

        ai_content = data["choices"][0]["message"]["content"]

        # Убираем markdown code blocks если есть
        if "```json" in ai_content:
            ai_content = ai_content.split("```json")[1].split("```")[0]
        elif "```" in ai_content:
            ai_content = ai_content.split("```")[1].split("```")[0]

        result = json.loads(ai_content.strip())

        # Валидация
        if result.get("action") not in [
            "change_grams",
            "change_calories",
            "change_product",
            "unclear",
        ]:
            result["action"] = "unclear"

        return {
            "action": result.get("action", "unclear"),
            "value": result.get("value"),
            "target": result.get("target"),
            "new_product": result.get("new_product"),
            "clarification_needed": result.get("clarification_needed", False),
        }

    except Exception as e:
        logger.error(f"Gemma error: {e}")
        return {
            "action": "unclear",
            "value": None,
            "target": None,
            "new_product": None,
            "clarification_needed": True,
        }


def number_to_int(text: str) -> int | None:
    """
    Преобразует числа прописью в цифры.
    fallback для Gemma если она не справилась.
    """
    numbers = {
        "ноль": 0,
        "один": 1,
        "одна": 1,
        "два": 2,
        "две": 2,
        "три": 3,
        "четыре": 4,
        "пять": 5,
        "шесть": 6,
        "семь": 7,
        "восемь": 8,
        "девять": 9,
        "десять": 10,
        "одиннадцать": 11,
        "двенадцать": 12,
        "тринадцать": 13,
        "четырнадцать": 14,
        "пятнадцать": 15,
        "шестнадцать": 16,
        "семнадцать": 17,
        "восемнадцать": 18,
        "девятнадцать": 19,
        "двадцать": 20,
        "тридцать": 30,
        "сорок": 40,
        "пятьдесят": 50,
        "шестьдесят": 60,
        "семьдесят": 70,
        "восемьдесят": 80,
        "девяносто": 90,
        "сто": 100,
        "двести": 200,
        "триста": 300,
        "четыреста": 400,
        "пятьсот": 500,
        "шестьсот": 600,
        "семьсот": 700,
        "восемьсот": 800,
        "девятьсот": 900,
        "тысяча": 1000,
    }

    text_lower = text.lower()
    total = 0

    for word, num in numbers.items():
        if word in text_lower:
            total += num

    return total if total > 0 else None
