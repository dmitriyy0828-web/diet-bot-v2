"""Модель пользователя Telegram."""
from sqlalchemy import Column, BigInteger, String
from sqlalchemy.orm import relationship
from src.models.base import BaseModel


class User(BaseModel):
    """Пользователь бота."""

    __tablename__ = "users"

    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(50))
    first_name = Column(String(100))
    last_name = Column(String(100))

    # Relationships
    profile = relationship("Profile", back_populates="user", uselist=False)
    food_logs = relationship("FoodLog", back_populates="user", lazy="dynamic")
    weight_logs = relationship("WeightLog", back_populates="user", lazy="dynamic")
