"""Расчет калорий и нутриентов через Open Food Facts API."""
import requests
from typing import Optional
from src.models import Profile, Gender, Goal, ActivityLevel


def calculate_daily_needs(profile: Profile) -> dict:
    """Рассчитать дневные потребности в калориях и БЖУ.

    Используем формулу Mifflin-St Jeor + коэффициент активности.
    """
    # Базовый метаболизм (BMR)
    if profile.gender == Gender.MALE:
        bmr = 10 * profile.current_weight_kg + 6.25 * profile.height_cm - 5 * profile.age + 5
    else:
        bmr = 10 * profile.current_weight_kg + 6.25 * profile.height_cm - 5 * profile.age - 161

    # Коэффициент активности
    activity_multipliers = {
        ActivityLevel.LOW: 1.2,
        ActivityLevel.MODERATE: 1.55,
        ActivityLevel.HIGH: 1.725,
    }

    multiplier = activity_multipliers.get(profile.activity_level, 1.55)
    tdee = int(bmr * multiplier)

    # Корректировка под цель
    if profile.goal == Goal.LOSE:
        calories = tdee - 500  # Дефицит 500 ккал
    elif profile.goal == Goal.GAIN:
        calories = tdee + 300  # Профицит 300 ккал
    else:
        calories = tdee

    # Расчет БЖУ (30/30/40%)
    protein = int(calories * 0.30 / 4)  # 4 ккал/г
    fat = int(calories * 0.30 / 9)  # 9 ккал/г
    carbs = int(calories * 0.40 / 4)  # 4 ккал/г
    fiber = 30  # Клетчатка 20-40г, берем 30г по умолчанию

    return {"calories": calories, "protein": protein, "fat": fat, "carbs": carbs, "fiber": fiber}


def get_food_from_openfoodfacts(food_name: str) -> Optional[dict]:
    """Поиск продукта в Open Food Facts.

    Returns:
        dict с полями: name, calories, protein, fat, carbs
        или None если не найдено
    """
    try:
        # Сначала пробуем русскую версию
        url = "https://ru.openfoodfacts.org/cgi/search.pl"
        params = {
            "search_terms": food_name,
            "search_simple": 1,
            "action": "process",
            "json": 1,
            "page_size": 1,
        }

        response = requests.get(url, params=params, timeout=5)
        data = response.json()

        products = data.get("products", [])
        if products:
            product = products[0]
            nutriments = product.get("nutriments", {})

            # Получаем калории (разные поля возможны)
            calories = (
                nutriments.get("energy-kcal_100g")
                or nutriments.get("energy-kcal")
                or nutriments.get("energy_100g", 0) / 4.184
            )  # кДж в ккал

            return {
                "name": product.get("product_name", food_name),
                "calories": round(calories) if calories else 0,
                "protein": nutriments.get("proteins_100g", 0) or nutriments.get("proteins", 0),
                "fat": nutriments.get("fat_100g", 0) or nutriments.get("fat", 0),
                "carbs": nutriments.get("carbohydrates_100g", 0)
                or nutriments.get("carbohydrates", 0),
                "fiber": nutriments.get("fiber_100g", 0) or nutriments.get("fiber", 0),
            }

        # Если не нашли, пробуем английскую версию
        url = "https://world.openfoodfacts.org/cgi/search.pl"
        response = requests.get(url, params=params, timeout=5)
        data = response.json()

        products = data.get("products", [])
        if products:
            product = products[0]
            nutriments = product.get("nutriments", {})

            calories = (
                nutriments.get("energy-kcal_100g")
                or nutriments.get("energy-kcal")
                or nutriments.get("energy_100g", 0) / 4.184
            )

            return {
                "name": product.get("product_name", food_name),
                "calories": round(calories) if calories else 0,
                "protein": nutriments.get("proteins_100g", 0) or nutriments.get("proteins", 0),
                "fat": nutriments.get("fat_100g", 0) or nutriments.get("fat", 0),
                "carbs": nutriments.get("carbohydrates_100g", 0)
                or nutriments.get("carbohydrates", 0),
                "fiber": nutriments.get("fiber_100g", 0) or nutriments.get("fiber", 0),
            }

        return None

    except Exception as e:
        print(f"Ошибка при запросе к Open Food Facts: {e}")
        return None


def calculate_food_nutrition(food_name: str, grams: int) -> dict:
    """Рассчитать нутриенты для конкретного продукта.

    Использует Open Food Facts API, если не найдено — использует
    примерные значения из локальной базы.
    """
    # Пробуем найти в Open Food Facts
    api_result = get_food_from_openfoodfacts(food_name)

    if api_result:
        # Пересчитываем на указанный вес
        ratio = grams / 100
        return {
            "name": api_result["name"],
            "grams": grams,
            "calories": round(api_result["calories"] * ratio),
            "protein": round(api_result["protein"] * ratio, 1),
            "fat": round(api_result["fat"] * ratio, 1),
            "carbs": round(api_result["carbs"] * ratio, 1),
            "fiber": round(api_result.get("fiber", 0) * ratio, 1),
        }

    # Fallback: локальная база для популярных продуктов
    food_db = {
        "курица": {"cal": 165, "protein": 31, "fat": 3.6, "carbs": 0, "fiber": 0},
        "рис": {"cal": 130, "protein": 2.7, "fat": 0.3, "carbs": 28, "fiber": 0.4},
        "гречка": {"cal": 132, "protein": 4.5, "fat": 1.6, "carbs": 24, "fiber": 10},
        "овсянка": {"cal": 68, "protein": 2.4, "fat": 1.4, "carbs": 12, "fiber": 1.7},
        "яйцо": {"cal": 155, "protein": 13, "fat": 11, "carbs": 1, "fiber": 0},
        "яблоко": {"cal": 52, "protein": 0.3, "fat": 0.2, "carbs": 14, "fiber": 2.4},
        "банан": {"cal": 89, "protein": 1.1, "fat": 0.3, "carbs": 23, "fiber": 2.6},
        "творог": {"cal": 159, "protein": 18, "fat": 5, "carbs": 3, "fiber": 0},
        "кефир": {"cal": 51, "protein": 3, "fat": 2.5, "carbs": 4, "fiber": 0},
    }

    # Ищем по первому слову
    base_name = food_name.lower().split()[0]
    data = food_db.get(base_name, {"cal": 100, "protein": 5, "fat": 3, "carbs": 15, "fiber": 0})

    ratio = grams / 100
    return {
        "name": food_name,
        "grams": grams,
        "calories": round(data["cal"] * ratio),
        "protein": round(data["protein"] * ratio, 1),
        "fat": round(data["fat"] * ratio, 1),
        "carbs": round(data["carbs"] * ratio, 1),
        "fiber": round(data.get("fiber", 0) * ratio, 1),
    }
