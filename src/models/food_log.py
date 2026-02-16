"""Модель записи о приеме пищи."""
from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from src.models.base import BaseModel


class FoodLog(BaseModel):
    """Запись о съеденной еде."""
    
    __tablename__ = "food_logs"
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Информация о еде
    food_name = Column(String(200), nullable=False)
    grams = Column(Integer, default=100)
    
    # Нутриенты
    calories = Column(Integer, nullable=False)
    protein = Column(Float, default=0.0)
    fat = Column(Float, default=0.0)
    carbs = Column(Float, default=0.0)
    
    # Опционально: ID фото в Telegram
    photo_file_id = Column(String(200))
    
    # Relationship
    user = relationship("User", back_populates="food_logs")
