"""Модель кеша продуктов из FatSecret."""
from sqlalchemy import Column, Integer, String, Float
from src.models.base import BaseModel


class FoodCache(BaseModel):
    """Кеш продуктов из FatSecret API.

    При запросе сначала проверяем эту таблицу,
    если нет — идём в FatSecret и сохраняем сюда.
    """

    __tablename__ = "food_cache"

    # Название продукта (нормализованное, lowercase)
    name = Column(String(200), nullable=False, index=True)

    # Нутриенты на 100г
    calories = Column(Float, nullable=False)  # ккал
    protein = Column(Float, default=0.0)  # белки
    fat = Column(Float, default=0.0)  # жиры
    carbs = Column(Float, default=0.0)  # углеводы
    fiber = Column(Float, default=0.0)  # клетчатка

    # Источник данных
    source = Column(String(50), default="fatsecret")  # fatsecret, manual, etc.

    # FatSecret specific (опционально)
    fatsecret_food_id = Column(String(50))

    # Счётчик использования (для статистики)
    usage_count = Column(Integer, default=1)

    def to_dict(self) -> dict:
        """Преобразовать в словарь для расчётов."""
        return {
            "name": self.name,
            "calories": self.calories,
            "protein": self.protein,
            "fat": self.fat,
            "carbs": self.carbs,
            "fiber": self.fiber,
        }
