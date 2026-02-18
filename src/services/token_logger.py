"""Логирование токенов для отслеживания расходов."""
import json
import os
from datetime import datetime
from pathlib import Path

TOKEN_LOG_FILE = Path("/root/.openclaw/workspace/projects/diet-bot-v2/logs/token_usage.jsonl")

# Цены примерные (за 1M токенов)
PRICING = {
    "openrouter/moonshotai/kimi-k2.5": {"input": 0.8, "output": 2.0},
    "gpt-4o-mini": {"input": 0.15, "output": 0.6},
}


def ensure_log_dir():
    """Создаёт директорию для логов если нужно."""
    TOKEN_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)


def log_token_usage(
    operation: str, model: str, input_tokens: int, output_tokens: int, user_id: int = None
) -> dict:
    """Логирует использование токенов.

    Args:
        operation: тип операции (food_lookup, photo_analysis, etc)
        model: название модели
        input_tokens: токены на вход
        output_tokens: токены на выход
        user_id: ID пользователя (опционально)

    Returns:
        dict с информацией о затратах
    """
    ensure_log_dir()

    # Расчёт стоимости
    prices = PRICING.get(model, {"input": 1.0, "output": 3.0})
    input_cost = (input_tokens / 1_000_000) * prices["input"]
    output_cost = (output_tokens / 1_000_000) * prices["output"]
    total_cost = input_cost + output_cost

    entry = {
        "timestamp": datetime.now().isoformat(),
        "operation": operation,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "cost_usd": round(total_cost, 6),
        "user_id": user_id,
    }

    # Дописываем в файл
    with open(TOKEN_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return entry


def get_daily_stats() -> dict:
    """Возвращает статистику за сегодня."""
    if not TOKEN_LOG_FILE.exists():
        return {"total_tokens": 0, "total_cost": 0, "operations": 0}

    today = datetime.now().strftime("%Y-%m-%d")
    total_tokens = 0
    total_cost = 0
    operations = 0

    with open(TOKEN_LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                if entry["timestamp"].startswith(today):
                    total_tokens += entry["total_tokens"]
                    total_cost += entry["cost_usd"]
                    operations += 1
            except:
                continue

    return {
        "total_tokens": total_tokens,
        "total_cost": round(total_cost, 4),
        "operations": operations,
    }


def format_cost_report(stats: dict) -> str:
    """Форматирует отчёт о затратах."""
    return (
        f"📊 Токены сегодня:\n"
        f"Запросов: {stats['operations']}\n"
        f"Токенов: {stats['total_tokens']:,}\n"
        f"Стоимость: ${stats['total_cost']:.4f}"
    )


def estimate_tokens(text: str) -> int:
    """Оценка количества токенов в тексте (приблизительно).

    Для русского: ~1.5 токена на слово, ~4 символа на токен.
    """
    if not text:
        return 0

    # Эвристика: 1 токен ≈ 4 символа для русского/английского смешанного текста
    char_count = len(text)
    return max(1, char_count // 4)


def log_chat_interaction(
    user_message: str, assistant_response: str, model: str = "openrouter/moonshotai/kimi-k2.5"
) -> dict:
    """Логирование диалога пользователя с ассистентом.

    Args:
        user_message: сообщение пользователя
        assistant_response: ответ ассистента
        model: модель

    Returns:
        dict с информацией о затратах
    """
    input_tokens = estimate_tokens(user_message)
    output_tokens = estimate_tokens(assistant_response)

    return log_token_usage(
        operation="chat_session",
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        user_id=310010786,  # Твой ID
    )
