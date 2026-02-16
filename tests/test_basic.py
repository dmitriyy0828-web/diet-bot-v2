"""Тесты для бота."""
import pytest
from src.config import Config
from src.database import init_db, get_db
from src.models import User, Profile
from src.services.nutrition_calc import calculate_food_nutrition, calculate_daily_needs


def test_config_validation():
    """Тест валидации конфигурации."""
    config = Config(
        BOT_TOKEN="test_token",
        OPENROUTER_API_KEY="test_key",
        DATABASE_URL="sqlite:///test.db",
        ADMIN_ID=None
    )
    # Не должно вызывать ошибку
    config.validate()


def test_food_nutrition_calculation():
    """Тест расчета нутриентов."""
    result = calculate_food_nutrition("Курица", 150)
    
    assert result["name"] == "Курица"
    assert result["grams"] == 150
    assert result["calories"] > 0
    assert result["protein"] > 0


def test_database_creation():
    """Тест создания БД."""
    # Это создаст таблицы во временной БД
    init_db()
    
    # Проверяем, что можем создать сессию
    with get_db() as db:
        assert db is not None


def test_parse_food_text():
    """Тест парсинга текста еды."""
    from src.handlers.food import parse_food_text
    
    # Тест 1: с весом
    name, grams = parse_food_text("Курица гриль, 150г")
    assert name == "Курица гриль"
    assert grams == 150
    
    # Тест 2: без веса
    name, grams = parse_food_text("Овсянка")
    assert name == "Овсянка"
    assert grams == 100  # По умолчанию
    
    # Тест 3: с пробелами
    name, grams = parse_food_text("  Яблоко , 200 г  ")
    assert name == "Яблоко"
    assert grams == 200
