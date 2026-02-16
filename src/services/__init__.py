"""Сервисы бизнес-логики."""
from src.services.user_service import get_or_create_user, get_user_by_telegram_id, has_profile
from src.services.nutrition_calc import calculate_daily_needs, calculate_food_nutrition
from src.services.stats_service import get_today_stats, get_period_stats

__all__ = [
    "get_or_create_user",
    "get_user_by_telegram_id",
    "has_profile",
    "calculate_daily_needs",
    "calculate_food_nutrition",
    "get_today_stats",
    "get_period_stats",
]
