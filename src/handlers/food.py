"""Обработчики добавления еды."""
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    ConversationHandler, filters, ContextTypes
)
from src.database import get_db
from src.models import FoodLog
from src.services.user_service import get_user_by_telegram_id, has_profile
from src.services.nutrition_calc import calculate_food_nutrition
from src.keyboards.food_menu import get_food_keyboard

# Состояния для ConversationHandler
WAITING_FOOD = 1


async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало добавления еды."""
    user = get_user_by_telegram_id(update.effective_user.id)
    
    if not user or not has_profile(user):
        await update.message.reply_text(
            "❌ Сначала нужно заполнить профиль.\n"
            "Используй: /register"
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        "🍽️ Опиши, что ты съел:\n\n"
        "Примеры:\n"
        "• Курица гриль, 150г\n"
        "• Овсянка с молоком\n"
        "• Яблоко, 200г"
    )
    return WAITING_FOOD


async def process_food(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка введенной еды."""
    text = update.message.text
    user = get_user_by_telegram_id(update.effective_user.id)
    
    # Парсим текст (название и вес)
    # Пример: "Курица гриль, 150г" -> name="Курица гриль", grams=150
    name, grams = parse_food_text(text)
    
    # Рассчитываем нутриенты
    nutrition = calculate_food_nutrition(name, grams)
    
    # Сохраняем в БД
    with get_db() as db:
        food_log = FoodLog(
            user_id=user.id,
            food_name=nutrition["name"],
            grams=nutrition["grams"],
            calories=nutrition["calories"],
            protein=nutrition["protein"],
            fat=nutrition["fat"],
            carbs=nutrition["carbs"]
        )
        db.add(food_log)
        db.commit()
        db.refresh(food_log)
        log_id = food_log.id
    
    # Отправляем результат с кнопками
    keyboard = get_food_keyboard(log_id)
    await update.message.reply_text(
        f"✅ Добавлено:\n\n"
        f"🍽️ {nutrition['name']}\n"
        f"⚖️ {nutrition['grams']}г\n"
        f"🔥 {nutrition['calories']} ккал\n"
        f"🥗 Б: {nutrition['protein']}г | "
        f"Ж: {nutrition['fat']}г | "
        f"У: {nutrition['carbs']}г",
        reply_markup=keyboard
    )
    
    return ConversationHandler.END


def parse_food_text(text: str) -> tuple[str, int]:
    """Парсит текст еды на название и вес.
    
    Returns:
        (название, вес_в_граммах)
    """
    text = text.strip()
    
    # Ищем вес в тексте (число + г/грамм)
    import re
    weight_match = re.search(r'(\d+)\s*(г|грамм|g)', text.lower())
    
    if weight_match:
        grams = int(weight_match.group(1))
        # Убираем вес из названия
        name = re.sub(r'\s*,?\s*\d+\s*(г|грамм|g)\s*$', '', text, flags=re.IGNORECASE)
    else:
        grams = 100  # По умолчанию 100г
        name = text
    
    return name.strip(), grams


def register_handlers(application: Application) -> None:
    """Регистрация обработчиков."""
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("add", add_command)],
        states={
            WAITING_FOOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_food)]
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: u.message.reply_text("Отменено"))]
    )
    application.add_handler(conv_handler)
