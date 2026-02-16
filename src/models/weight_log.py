"""Модель записи веса пользователя."""
from sqlalchemy import Column, Integer, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from src.models.base import BaseModel


class WeightLog(BaseModel):
    """История изменения веса."""
    
    __tablename__ = "weight_logs"
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    weight_kg = Column(Float, nullable=False)
    note = Column(Text)
    
    # Relationship
    user = relationship("User", back_populates="weight_logs")
