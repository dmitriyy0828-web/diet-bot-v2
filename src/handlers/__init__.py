"""Обработчики команд бота."""
from src.handlers.start import register_handlers as register_start_handlers
from src.handlers.registration import register_handlers as register_registration_handlers
from src.handlers.food import register_handlers as register_food_handlers
from src.handlers.stats import register_handlers as register_stats_handlers
from src.handlers.callbacks import register_handlers as register_callback_handlers

__all__ = [
    "register_start_handlers",
    "register_registration_handlers",
    "register_food_handlers",
    "register_stats_handlers",
    "register_callback_handlers",
]
