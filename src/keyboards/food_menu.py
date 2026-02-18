"""Клавиатуры для работы с едой."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_food_keyboard(log_id: int) -> InlineKeyboardMarkup:
    """Кнопки под записью о приеме пищи (только Изменить и Удалить).

    Args:
        log_id: ID записи в БД
    """
    keyboard = [
        [
            InlineKeyboardButton("✏️ Изменить", callback_data=f"ai_edit:{log_id}"),
            InlineKeyboardButton("🗑️ Удалить", callback_data=f"ai_cancel:{log_id}"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_ai_vision_keyboard(log_id: int) -> InlineKeyboardMarkup:
    """Кнопки для результата AI Vision (Изменить и Удалить).

    Args:
        log_id: ID записи в БД
    """
    keyboard = [
        [
            InlineKeyboardButton("✏️ Изменить", callback_data=f"ai_edit:{log_id}"),
            InlineKeyboardButton("🗑️ Удалить", callback_data=f"ai_cancel:{log_id}"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_edit_confirm_keyboard(log_id: int) -> InlineKeyboardMarkup:
    """Кнопки подтверждения изменений.

    Args:
        log_id: ID записи в БД
    """
    keyboard = [
        [
            InlineKeyboardButton("✅ Сохранить", callback_data=f"ai_save:{log_id}"),
            InlineKeyboardButton("◀️ Назад", callback_data=f"ai_back:{log_id}"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
