"""Базовые классы для моделей SQLAlchemy."""
from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.sql import func
from src.database import Base


class TimestampMixin:
    """Миксин для автоматического создания временных меток."""
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class BaseModel(Base, TimestampMixin):
    """Базовая модель для всех таблиц."""
    
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, index=True)
