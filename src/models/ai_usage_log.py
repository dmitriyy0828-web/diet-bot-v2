"""Модель для логирования AI-запросов и их стоимости."""
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.models.base import BaseModel


class AIUsageLog(BaseModel):
    """Лог использования AI-сервисов с точной стоимостью."""

    __tablename__ = "ai_usage_logs"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Тип запроса
    request_type = Column(String(50), nullable=False)  # vision, gemma, barcode, ocr
    
    # Модель AI
    model = Column(String(100), nullable=False)  # gpt-4-vision, gemma-2b, etc
    
    # Точная стоимость из ответа API (USD)
    cost_usd = Column(Float, nullable=False, default=0.0)
    
    # Токены для детализации
    tokens_input = Column(Integer, default=0)
    tokens_output = Column(Integer, default=0)
    
    # Контекст запроса (опционально)
    food_name = Column(String(200))  # что распознавалось
    
    # Relationship
    user = relationship("User", back_populates="ai_usage_logs")

    def __repr__(self):
        return f"<AIUsageLog {self.request_type} ${self.cost_usd:.4f}>"
