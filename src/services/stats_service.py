"""Сервис для подсчета статистики."""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import func
from src.database import get_db
from src.models import FoodLog, User


def get_today_stats(user_id: int) -> dict:
    """Получить статистику за сегодня."""
    with get_db() as db:
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        
        logs = db.query(FoodLog).filter(
            FoodLog.user_id == user_id,
            FoodLog.created_at >= today,
            FoodLog.created_at < tomorrow
        ).all()
        
        total_cal = sum(log.calories for log in logs)
        total_protein = sum(log.protein for log in logs)
        total_fat = sum(log.fat for log in logs)
        total_carbs = sum(log.carbs for log in logs)
        
        # Список еды
        food_list = [
            f"• {log.food_name} — {log.calories} ккал"
            for log in logs
        ]
        
        return {
            "calories": total_cal,
            "protein": round(total_protein, 1),
            "fat": round(total_fat, 1),
            "carbs": round(total_carbs, 1),
            "food_list": food_list,
            "count": len(logs)
        }


def get_period_stats(user_id: int, days: int) -> dict:
    """Получить статистику за период.
    
    Args:
        user_id: ID пользователя
        days: Количество дней (7, 30)
    """
    with get_db() as db:
        start_date = datetime.now() - timedelta(days=days)
        
        logs = db.query(FoodLog).filter(
            FoodLog.user_id == user_id,
            FoodLog.created_at >= start_date
        ).all()
        
        if not logs:
            return {
                "avg_calories": 0,
                "total_days": 0,
                "message": "Нет данных за период"
            }
        
        # Группируем по дням
        daily_cal = {}
        for log in logs:
            day = log.created_at.date()
            daily_cal[day] = daily_cal.get(day, 0) + log.calories
        
        avg_cal = sum(daily_cal.values()) / len(daily_cal)
        
        return {
            "avg_calories": int(avg_cal),
            "total_days": len(daily_cal),
            "days_tracked": len(daily_cal),
            "min_cal": min(daily_cal.values()),
            "max_cal": max(daily_cal.values())
        }
