"""Модель профиля пользователя (цели и параметры)."""
from sqlalchemy import Column, Integer, Float, String, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum
from src.models.base import BaseModel


class Gender(str, enum.Enum):
    """Пол пользователя."""
    MALE = "male"
    FEMALE = "female"


class Goal(str, enum.Enum):
    """Цель пользователя."""
    LOSE = "lose"
    MAINTAIN = "maintain"
    GAIN = "gain"


class ActivityLevel(str, enum.Enum):
    """Уровень активности."""
    LOW = "low"           # Сидячий образ жизни
    MODERATE = "moderate" # Умеренная активность
    HIGH = "high"         # Высокая активность


class Profile(BaseModel):
    """Профиль пользователя с параметрами и целями."""
    
    __tablename__ = "profiles"
    
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    
    # Личные данные
    gender = Column(Enum(Gender))
    age = Column(Integer)
    height_cm = Column(Integer)
    current_weight_kg = Column(Float)
    target_weight_kg = Column(Float)
    
    # Цель и активность
    goal = Column(Enum(Goal), default=Goal.MAINTAIN)
    activity_level = Column(Enum(ActivityLevel), default=ActivityLevel.MODERATE)
    
    # Рассчитанные дневные нормы
    daily_calories = Column(Integer, default=2000)
    daily_protein = Column(Integer, default=100)
    daily_fat = Column(Integer, default=70)
    daily_carbs = Column(Integer, default=250)
    
    # Relationship
    user = relationship("User", back_populates="profile")
