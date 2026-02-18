"""Точка входа для Diet Bot v2."""
import logging
from telegram.ext import Application, MessageHandler, filters
from telegram import Update
from src.config import config
from src.database import init_db
from src.handlers import (
    register_start_handlers,
    register_registration_handlers,
    register_food_handlers,
    register_stats_handlers,
    register_callback_handlers,
)
from src.services.token_logger import log_token_usage, get_daily_stats
import time

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Запуск бота."""
    # Проверка конфигурации
    try:
        config.validate()
    except ValueError as e:
        logger.error(f"Ошибка конфигурации: {e}")
        return

    # Инициализация БД
    logger.info("Инициализация базы данных...")
    init_db()

    # Создание приложения
    logger.info("Запуск бота...")
    application = Application.builder().token(config.BOT_TOKEN).build()

    # Регистрация обработчиков
    register_start_handlers(application)
    register_registration_handlers(application)
    register_food_handlers(application)
    register_stats_handlers(application)
    register_callback_handlers(application)

    # Запуск с логированием токенов
    logger.info(f"📊 Token logging enabled. Daily stats will be tracked.")
    application.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
