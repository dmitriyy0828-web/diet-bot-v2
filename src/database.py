"""Подключение к базе данных SQLAlchemy."""
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from src.config import config

# Создание движка БД
engine = create_engine(
    config.DATABASE_URL,
    echo=False,  # True для отладки SQL
    connect_args={"check_same_thread": False} if "sqlite" in config.DATABASE_URL else {},
)

# Фабрика сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Базовый класс для моделей
Base = declarative_base()


def init_db() -> None:
    """Создание всех таблиц в БД."""
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_db():
    """Контекстный менеджер для сессий БД.

    Использование:
        with get_db() as db:
            user = db.query(User).first()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
