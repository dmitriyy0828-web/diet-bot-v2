"""Сервис Vision AI для распознавания еды (только названия и вес)."""
import base64
import json
import logging
from typing import TypedDict, Optional
import requests
from src.config import config

logger = logging.getLogger(__name__)


class DetectedFood(TypedDict):
    """Распознанный продукт (только название и вес)."""

    food: str
    weight: int


class VisionResult(TypedDict):
    """Результат распознавания."""

    foods: list[DetectedFood]
    success: bool
    error: Optional[str]


def analyze_food_photo_simple(photo_bytes: bytes) -> VisionResult:
    """Анализ фото: возвращает только названия продуктов и их вес.

    НЕ считает калории — это делает FatSecret сервис.

    Args:
        photo_bytes: фото в формате bytes

    Returns:
        VisionResult со списком {"food": "название", "weight": граммы}
    """
    try:
        # Кодируем фото в base64
        image_base64 = base64.b64encode(photo_bytes).decode("utf-8")

        # Промпт — строго JSON, без калорий
        system_prompt = """Ты — эксперт по распознаванию еды на фото.
Твоя задача: определить какие продукты видны на фото и их примерный вес.

ПРАВИЛА НАЗВАНИЙ (важно для поиска в базе):
1. ОСНОВНОЕ БЛЮДО — указывай КОНКРЕТНО:
   - "куриные крылья жареные" вместо просто "курица"
   - "куриная грудка гриль" вместо "курица гриль"
   - "говяжий стейк" вместо просто "говядина"
   - "свинина тушеная" вместо просто "свинина"

2. ГАРНИРЫ — простое название:
   - "гречка", "рис белый", "овсянка"
   - "макароны", "спагетти", "картофель пюре"

3. СМЕШАННЫЕ БЛЮДА — ОДНО название:
   - "борщ" (а не свекла, капуста, мясо)
   - "салат оливье" (а не по ингредиентам)
   - "плов" вместо рис+морковь+мясо

4. Части курицы — РАЗУ ПО-РАЗНОМУ:
   - Крылья = "куриные крылья жареные/вареные"
   - Ножки = "куриные ножки"
   - Грудка = "курица грудка"
   - Филе = "курица филе"
   - Целая/кусок = просто "курица"

5. Если видно СПОСОБ ПРИГОТОВЛЕНИЯ — добавляй:
   - "...жареная", "...тушеная", "...вареная", "...гриль"

ВЕС: оценивай визуально по тарелке (обычно 20-25 см)

ФОРМАТ ОТВЕТА (строго JSON):
[
  {"food": "куриные крылья жареные", "weight": 250},
  {"food": "гречка", "weight": 200},
  {"food": "огурец свежий", "weight": 50}
]

Если не уверен — дай ОБЩЕЕ название (не выдумывай).
Если совсем непонятно — пустой массив []."""

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://diet-bot.local",
                "X-Title": "Diet Bot",
            },
            json={
                "model": "openai/gpt-4o-mini",
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
                "max_tokens": 500,
                "temperature": 0.3,
            },
            timeout=30,
        )

        response.raise_for_status()
        data = response.json()

        # Парсим ответ
        ai_content = data["choices"][0]["message"]["content"]

        # Убираем markdown code blocks
        if "```json" in ai_content:
            ai_content = ai_content.split("```json")[1].split("```")[0]
        elif "```" in ai_content:
            ai_content = ai_content.split("```")[1].split("```")[0]

        foods = json.loads(ai_content.strip())

        # Валидация формата
        if not isinstance(foods, list):
            logger.error(f"Invalid AI response format: {foods}")
            return {"foods": [], "success": False, "error": "Invalid response format"}

        # Нормализуем данные
        result = []
        for item in foods:
            if isinstance(item, dict) and "food" in item and "weight" in item:
                result.append(
                    {
                        "food": str(item["food"]).strip(),
                        "weight": int(item["weight"]) if item["weight"] else 100,
                    }
                )

        logger.info(f"Vision detected {len(result)} foods")
        return {"foods": result, "success": True, "error": None}

    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        return {"foods": [], "success": False, "error": f"JSON parse error: {e}"}
    except Exception as e:
        logger.error(f"Vision analysis error: {e}")
        return {"foods": [], "success": False, "error": str(e)}
