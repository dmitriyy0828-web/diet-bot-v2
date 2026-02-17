"""Сервис для логирования AI-запросов и расчёта стоимости."""
import logging
from typing import Optional
from src.database import get_db
from src.models import AIUsageLog

logger = logging.getLogger(__name__)

# Стоимость моделей (USD за 1K токенов)
# OpenRouter возвращает точную стоимость, но на всякий случай — fallback цены
MODEL_PRICING = {
    "openai/gpt-4-vision-preview": {"input": 0.01, "output": 0.03},
    "google/gemma-2b-it": {"input": 0.0001, "output": 0.0001},
}


def log_ai_request(
    user_id: int,
    request_type: str,
    model: str,
    cost_usd: float,
    tokens_input: int = 0,
    tokens_output: int = 0,
    food_name: Optional[str] = None,
) -> None:
    """
    Залогировать AI-запрос с точной стоимостью.
    
    Args:
        user_id: ID пользователя в базе
        request_type: тип запроса (vision, gemma, barcode, ocr)
        model: модель AI
        cost_usd: точная стоимость из ответа API
        tokens_input: входящие токены
        tokens_output: исходящие токены
        food_name: название еды (опционально)
    """
    try:
        with get_db() as db:
            log = AIUsageLog(
                user_id=user_id,
                request_type=request_type,
                model=model,
                cost_usd=cost_usd,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                food_name=food_name,
            )
            db.add(log)
            db.commit()
            logger.info(f"AI usage logged: {request_type} ${cost_usd:.4f} for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to log AI usage: {e}")


def get_user_ai_costs(user_id: int, days: int = 30) -> dict:
    """
    Получить статистику расходов на AI для пользователя.
    
    Args:
        user_id: ID пользователя
        days: период в днях (по умолчанию 30)
    
    Returns:
        dict с total_cost, request_count, breakdown по типам
    """
    from datetime import datetime, timedelta
    
    with get_db() as db:
        start_date = datetime.utcnow() - timedelta(days=days)
        
        logs = db.query(AIUsageLog).filter(
            AIUsageLog.user_id == user_id,
            AIUsageLog.created_at >= start_date,
        ).all()
        
        total_cost = sum(log.cost_usd for log in logs)
        request_count = len(logs)
        
        # Разбивка по типам
        breakdown = {}
        for log in logs:
            breakdown[log.request_type] = breakdown.get(log.request_type, 0) + log.cost_usd
        
        return {
            "total_cost_usd": round(total_cost, 4),
            "total_cost_rub": round(total_cost * 92, 2),  # примерный курс
            "request_count": request_count,
            "breakdown": {k: round(v, 4) for k, v in breakdown.items()},
        }


def get_all_users_costs(days: int = 30) -> list:
    """
    Получить расходы всех пользователей (для админа).
    
    Returns:
        list словарей с user_id, username, total_cost, request_count
    """
    from datetime import datetime, timedelta
    from sqlalchemy import func
    from src.models import User
    
    with get_db() as db:
        start_date = datetime.utcnow() - timedelta(days=days)
        
        results = db.query(
            AIUsageLog.user_id,
            User.username,
            User.first_name,
            func.sum(AIUsageLog.cost_usd).label("total_cost"),
            func.count(AIUsageLog.id).label("request_count"),
        ).join(User).filter(
            AIUsageLog.created_at >= start_date,
        ).group_by(AIUsageLog.user_id, User.username, User.first_name).all()
        
        return [
            {
                "user_id": r.user_id,
                "username": r.username or r.first_name or f"User_{r.user_id}",
                "total_cost_usd": round(r.total_cost, 4),
                "total_cost_rub": round(r.total_cost * 92, 2),
                "request_count": r.request_count,
            }
            for r in results
        ]


def get_total_costs(days: int = 30) -> dict:
    """Получить общие расходы на AI за период."""
    from datetime import datetime, timedelta
    from sqlalchemy import func
    
    with get_db() as db:
        start_date = datetime.utcnow() - timedelta(days=days)
        
        total = db.query(func.sum(AIUsageLog.cost_usd)).filter(
            AIUsageLog.created_at >= start_date,
        ).scalar() or 0
        
        count = db.query(func.count(AIUsageLog.id)).filter(
            AIUsageLog.created_at >= start_date,
        ).scalar() or 0
        
        return {
            "total_cost_usd": round(total, 4),
            "total_cost_rub": round(total * 92, 2),
            "total_requests": count,
        }
