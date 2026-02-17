"""Сервис для подсчета статистики."""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import func
from src.database import get_db
from src.models import FoodLog, User


def get_today_stats(user_id: int) -> dict:
    """Получить статистику за сегодня (по Москве UTC+3)."""
    with get_db() as db:
        # Московское время UTC+3
        from datetime import timezone

        msk_offset = timezone(timedelta(hours=3))
        now_msk = datetime.now(msk_offset)
        today_msk = now_msk.date()

        # Конвертируем начало и конец дня по МСК в UTC для сравнения с БД
        today_start_utc = datetime.combine(today_msk, datetime.min.time()) - timedelta(hours=3)
        tomorrow_start_utc = today_start_utc + timedelta(days=1)

        logs = (
            db.query(FoodLog)
            .filter(
                FoodLog.user_id == user_id,
                FoodLog.created_at >= today_start_utc,
                FoodLog.created_at < tomorrow_start_utc,
            )
            .all()
        )

        total_cal = sum(log.calories for log in logs)
        total_protein = sum(log.protein for log in logs)
        total_fat = sum(log.fat for log in logs)
        total_carbs = sum(log.carbs for log in logs)
        total_fiber = sum(log.fiber for log in logs)

        # Список еды
        food_list = [f"• {log.food_name} — {log.calories} ккал" for log in logs]

        return {
            "calories": total_cal,
            "protein": round(total_protein, 1),
            "fat": round(total_fat, 1),
            "carbs": round(total_carbs, 1),
            "fiber": round(total_fiber, 1),
            "food_list": food_list,
            "count": len(logs),
        }


def get_yesterday_stats(user_id: int) -> dict:
    """Получить статистику за вчера (по Москве UTC+3)."""
    with get_db() as db:
        from datetime import timezone

        msk_offset = timezone(timedelta(hours=3))
        now_msk = datetime.now(msk_offset)
        yesterday_msk = now_msk.date() - timedelta(days=1)

        yesterday_start_utc = datetime.combine(yesterday_msk, datetime.min.time()) - timedelta(
            hours=3
        )
        yesterday_end_utc = yesterday_start_utc + timedelta(days=1)

        logs = (
            db.query(FoodLog)
            .filter(
                FoodLog.user_id == user_id,
                FoodLog.created_at >= yesterday_start_utc,
                FoodLog.created_at < yesterday_end_utc,
            )
            .all()
        )

        total_cal = sum(log.calories for log in logs)
        total_protein = sum(log.protein for log in logs)
        total_fat = sum(log.fat for log in logs)
        total_carbs = sum(log.carbs for log in logs)
        total_fiber = sum(log.fiber for log in logs)
        food_list = [f"• {log.food_name} — {log.calories} ккал" for log in logs]

        return {
            "calories": total_cal,
            "protein": round(total_protein, 1),
            "fat": round(total_fat, 1),
            "carbs": round(total_carbs, 1),
            "fiber": round(total_fiber, 1),
            "food_list": food_list,
            "count": len(logs),
        }


def get_week_stats(user_id: int) -> dict:
    """Получить статистику за неделю (по Москве UTC+3)."""
    with get_db() as db:
        from datetime import timezone

        msk_offset = timezone(timedelta(hours=3))
        now_msk = datetime.now(msk_offset)
        week_ago_msk = now_msk.date() - timedelta(days=7)

        week_start_utc = datetime.combine(week_ago_msk, datetime.min.time()) - timedelta(hours=3)

        logs = (
            db.query(FoodLog)
            .filter(
                FoodLog.user_id == user_id,
                FoodLog.created_at >= week_start_utc,
            )
            .all()
        )

        # Группируем по дням
        daily_cal = {}
        total_protein, total_fat, total_carbs, total_fiber = 0, 0, 0, 0

        for log in logs:
            # Конвертируем UTC в МСК
            log_msk = log.created_at + timedelta(hours=3)
            day = log_msk.date()
            daily_cal[day] = daily_cal.get(day, 0) + log.calories
            total_protein += log.protein
            total_fat += log.fat
            total_carbs += log.carbs
            total_fiber += log.fiber

        if not daily_cal:
            return {"avg_calories": 0, "total_days": 0, "message": "Нет данных за неделю"}

        avg_cal = sum(daily_cal.values()) / len(daily_cal)
        total_cal = sum(daily_cal.values())

        return {
            "total_calories": total_cal,
            "avg_calories": int(avg_cal),
            "total_days": len(daily_cal),
            "min_cal": min(daily_cal.values()),
            "max_cal": max(daily_cal.values()),
            "protein": round(total_protein, 1),
            "fat": round(total_fat, 1),
            "carbs": round(total_carbs, 1),
            "fiber": round(total_fiber, 1),
        }


def get_month_stats(user_id: int) -> dict:
    """Получить статистику за месяц (по Москве UTC+3)."""
    with get_db() as db:
        from datetime import timezone

        msk_offset = timezone(timedelta(hours=3))
        now_msk = datetime.now(msk_offset)
        month_ago_msk = now_msk.date() - timedelta(days=30)

        month_start_utc = datetime.combine(month_ago_msk, datetime.min.time()) - timedelta(hours=3)

        logs = (
            db.query(FoodLog)
            .filter(
                FoodLog.user_id == user_id,
                FoodLog.created_at >= month_start_utc,
            )
            .all()
        )

        # Группируем по дням
        daily_cal = {}
        total_protein, total_fat, total_carbs, total_fiber = 0, 0, 0, 0

        for log in logs:
            log_msk = log.created_at + timedelta(hours=3)
            day = log_msk.date()
            daily_cal[day] = daily_cal.get(day, 0) + log.calories
            total_protein += log.protein
            total_fat += log.fat
            total_carbs += log.carbs
            total_fiber += log.fiber

        if not daily_cal:
            return {"avg_calories": 0, "total_days": 0, "message": "Нет данных за месяц"}

        avg_cal = sum(daily_cal.values()) / len(daily_cal)
        total_cal = sum(daily_cal.values())

        return {
            "total_calories": total_cal,
            "avg_calories": int(avg_cal),
            "total_days": len(daily_cal),
            "min_cal": min(daily_cal.values()),
            "max_cal": max(daily_cal.values()),
            "protein": round(total_protein, 1),
            "fat": round(total_fat, 1),
            "carbs": round(total_carbs, 1),
            "fiber": round(total_fiber, 1),
        }


def get_period_stats(user_id: int, days: int) -> dict:
    """Получить статистику за период.

    Args:
        user_id: ID пользователя
        days: Количество дней (7, 30)
    """
    with get_db() as db:
        start_date = datetime.now() - timedelta(days=days)

        logs = (
            db.query(FoodLog)
            .filter(FoodLog.user_id == user_id, FoodLog.created_at >= start_date)
            .all()
        )

        if not logs:
            return {"avg_calories": 0, "total_days": 0, "message": "Нет данных за период"}

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
            "max_cal": max(daily_cal.values()),
        }
