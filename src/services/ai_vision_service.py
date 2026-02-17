"""Сервис AI Vision для распознавания еды по фото."""
import base64
import json
import logging
from typing import TypedDict, Optional
import requests
from src.config import config
from src.services.ai_cost_service import log_ai_request

logger = logging.getLogger(__name__)


class FoodItem(TypedDict):
    """Структура распознанного продукта."""

    name: str
    grams: int
    calories: int
    protein: float
    fat: float
    carbs: float


class AIVisionResult(TypedDict):
    """Результат распознавания AI Vision."""

    foods: list[FoodItem]
    is_mixed_dish: bool
    confidence: str  # high, medium, low


def analyze_food_photo(photo_bytes: bytes, user_id: Optional[int] = None) -> AIVisionResult:
    """
    Анализ фото еды через GPT-4 Vision.

    Args:
        photo_bytes: фото в формате bytes
        user_id: ID пользователя для логирования стоимости

    Returns:
        AIVisionResult со списком продуктов и их КБЖУ
    """
    # Кодируем фото в base64
    image_base64 = base64.b64encode(photo_bytes).decode("utf-8")

    # Промпт для AI
    system_prompt = """Ты — эксперт по питанию и распознаванию еды.
Проанализируй фото и определи, что изображено.

ПРАВИЛА:
1. Если это смешанное блюдо (салат, суп, плов, каша) — верни ОДИН продукт
2. Если это раздельные продукты (котлета + гречка + овощи) — верни НЕСКОЛЬКО продуктов
3. Оцени граммовку по визуальному размеру порции
4. Укажи КБЖУ на 100г (калории, белки, жиры, углеводы)

ФОРМАТ ОТВЕТА (строго JSON):
{
  "is_mixed_dish": true/false,
  "confidence": "high/medium/low",
  "foods": [
    {
      "name": "Название продукта",
      "grams": 250,
      "calories_per_100g": 120,
      "protein_per_100g": 5.2,
      "fat_per_100g": 3.1,
      "carbs_per_100g": 18.5
    }
  ]
}

Оценка confidence:
- high: чётко видно продукты, стандартная порция
- medium: видно, но есть неопределённость
- low: непонятно что это"""

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
                "model": "openai/gpt-4o",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"},
                            }
                        ],
                    },
                ],
                "max_tokens": 1000,
                "temperature": 0.3,
            },
            timeout=30,
        )

        response.raise_for_status()
        data = response.json()

        # Логируем стоимость запроса
        if user_id:
            try:
                usage = data.get("usage", {})
                # OpenRouter возвращает cost в поле usage.cost или считаем по токенам
                cost = data.get("cost", 0)  # OpenRouter иногда добавляет поле cost
                if not cost and usage:
                    # Приблизительный расчет: $0.005/1K input, $0.015/1K output для GPT-4o
                    input_tokens = usage.get("prompt_tokens", 0)
                    output_tokens = usage.get("completion_tokens", 0)
                    cost = (input_tokens * 0.000005) + (output_tokens * 0.000015)
                
                log_ai_request(
                    user_id=user_id,
                    request_type="vision",
                    model="openai/gpt-4o",
                    cost_usd=cost,
                    tokens_input=usage.get("prompt_tokens", 0),
                    tokens_output=usage.get("completion_tokens", 0),
                )
            except Exception as e:
                logger.error(f"Failed to log AI cost: {e}")

        # Парсим ответ AI
        ai_content = data["choices"][0]["message"]["content"]

        # Убираем markdown code blocks если есть
        if "```json" in ai_content:
            ai_content = ai_content.split("```json")[1].split("```")[0]
        elif "```" in ai_content:
            ai_content = ai_content.split("```")[1].split("```")[0]

        ai_result = json.loads(ai_content.strip())

        # Конвертируем в наш формат
        foods = []
        for item in ai_result.get("foods", []):
            calories_per_100g = item.get("calories_per_100g", 0)
            grams = item.get("grams", 100)

            foods.append(
                {
                    "name": item.get("name", "Неизвестный продукт"),
                    "grams": grams,
                    "calories": round(calories_per_100g * grams / 100),
                    "protein": round(item.get("protein_per_100g", 0) * grams / 100, 1),
                    "fat": round(item.get("fat_per_100g", 0) * grams / 100, 1),
                    "carbs": round(item.get("carbs_per_100g", 0) * grams / 100, 1),
                }
            )

        return {
            "foods": foods,
            "is_mixed_dish": ai_result.get("is_mixed_dish", False),
            "confidence": ai_result.get("confidence", "medium"),
        }

    except Exception as e:
        logger.error(f"AI Vision error: {e}")
        return {"foods": [], "is_mixed_dish": False, "confidence": "low"}


def recalculate_nutrition(
    foods: list[FoodItem], change_type: str, change_value: str
) -> list[FoodItem]:
    """
    Пересчёт КБЖУ при изменении.

    Args:
        foods: список продуктов
        change_type: "grams" или "calories"
        change_value: новое значение (например "250" или "300")

    Returns:
        Обновлённый список продуктов
    """
    if not foods:
        return foods

    # Работаем с первым продуктом (обычно один при смешанном блюде)
    food = foods[0].copy()
    new_value = int(change_value)

    if change_type == "grams":
        # Пересчёт пропорционально новой граммовке
        old_grams = food["grams"]
        ratio = new_value / old_grams if old_grams > 0 else 1

        food["grams"] = new_value
        food["calories"] = round(food["calories"] * ratio)
        food["protein"] = round(food["protein"] * ratio, 1)
        food["fat"] = round(food["fat"] * ratio, 1)
        food["carbs"] = round(food["carbs"] * ratio, 1)

    elif change_type == "calories":
        # Меняем только калории, без пересчёта БЖУ
        food["calories"] = new_value

    return [food]
