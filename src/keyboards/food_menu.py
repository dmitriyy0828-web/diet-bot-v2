"""Клавиатуры для работы с едой."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_food_keyboard(log_id: int) -> InlineKeyboardMarkup:
    """Кнопки под записью о приеме пищи.
    
    Args:
        log_id: ID записи в БД
    """
    keyboard = [
        [InlineKeyboardButton("❌ Удалить", callback_data=f"delete:{log_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)
