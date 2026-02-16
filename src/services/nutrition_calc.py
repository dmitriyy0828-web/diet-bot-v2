"""Расчет калорий и нутриентов."""
from src.models import Profile, Gender, Goal, ActivityLevel


def calculate_daily_needs(profile: Profile) -> dict:
    """Рассчитать дневные потребности в калориях и БЖУ.
    
    Используем формулу Mifflin-St Jeor + коэффициент активности.
    """
    # Базовый метаболизм (BMR)
    if profile.gender == Gender.MALE:
        bmr = (10 * profile.current_weight_kg +
               6.25 * profile.height_cm -
               5 * profile.age +
               5)
    else:
        bmr = (10 * profile.current_weight_kg +
               6.25 * profile.height_cm -
               5 * profile.age -
               161)
    
    # Коэффициент активности
    activity_multipliers = {
        ActivityLevel.LOW: 1.2,
        ActivityLevel.MODERATE: 1.55,
        ActivityLevel.HIGH: 1.725
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
    fat = int(calories * 0.30 / 9)      # 9 ккал/г
    carbs = int(calories * 0.40 / 4)    # 4 ккал/г
    
    return {
        "calories": calories,
        "protein": protein,
        "fat": fat,
        "carbs": carbs
    }


def calculate_food_nutrition(food_name: str, grams: int) -> dict:
    """Рассчитать нутриенты для конкретного продукта.
    
    Пока используем упрощенную базу данных.
    В будущем — интеграция с реальной API или AI.
    """
    # Упрощенная база: калорийность на 100г
    food_db = {
        "курица": {"cal": 165, "protein": 31, "fat": 3.6, "carbs": 0},
        "рис": {"cal": 130, "protein": 2.7, "fat": 0.3, "carbs": 28},
        "гречка": {"cal": 132, "protein": 4.5, "fat": 1.6, "carbs": 24},
        "овсянка": {"cal": 68, "protein": 2.4, "fat": 1.4, "carbs": 12},
        "яйцо": {"cal": 155, "protein": 13, "fat": 11, "carbs": 1},
        "яблоко": {"cal": 52, "protein": 0.3, "fat": 0.2, "carbs": 14},
        "банан": {"cal": 89, "protein": 1.1, "fat": 0.3, "carbs": 23},
    }
    
    # Ищем в базе (по первому слову)
    base_name = food_name.lower().split()[0]
    data = food_db.get(base_name, {"cal": 100, "protein": 5, "fat": 3, "carbs": 15})
    
    # Пересчитываем на указанный вес
    ratio = grams / 100
    return {
        "name": food_name,
        "grams": grams,
        "calories": int(data["cal"] * ratio),
        "protein": round(data["protein"] * ratio, 1),
        "fat": round(data["fat"] * ratio, 1),
        "carbs": round(data["carbs"] * ratio, 1)
    }
