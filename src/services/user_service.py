"""Сервис для работы с пользователями."""
from typing import Optional
from telegram import User as TelegramUser
from sqlalchemy.orm import joinedload
from src.database import get_db
from src.models import User, Profile


def get_or_create_user(telegram_user: TelegramUser) -> User:
    """Получить или создать пользователя.

    Args:
        telegram_user: Объект пользователя из Telegram

    Returns:
        Объект User из БД
    """
    with get_db() as db:
        # Ищем пользователя с загрузкой профиля
        user = (
            db.query(User)
            .options(joinedload(User.profile))
            .filter(User.telegram_id == telegram_user.id)
            .first()
        )

        if not user:
            # Создаем нового
            user = User(
                telegram_id=telegram_user.id,
                username=telegram_user.username,
                first_name=telegram_user.first_name,
                last_name=telegram_user.last_name,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            # При создании профиля нет, так что объекты простые

        return user


def get_user_by_telegram_id(telegram_id: int) -> Optional[User]:
    """Получить пользователя по Telegram ID.

    Args:
        telegram_id: ID пользователя в Telegram

    Returns:
        Объект User или None
    """
    with get_db() as db:
        return (
            db.query(User)
            .options(joinedload(User.profile))
            .filter(User.telegram_id == telegram_id)
            .first()
        )


def has_profile(user: User) -> bool:
    """Проверить, заполнен ли профиль пользователя."""
    return user.profile is not None
