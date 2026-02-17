"""Обработчики команд /start и /help."""
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from src.services.user_service import get_or_create_user, has_profile


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /start."""
    user = get_or_create_user(update.effective_user)

    if not has_profile(user):
        await update.message.reply_text(
            "👋 Привет! Я твой персональный диетолог.\n\n"
            "Я помогу отслеживать питание и достигать целей.\n\n"
            "Для начала нужно заполнить профиль:\n"
            "👉 /register"
        )
    else:
        await update.message.reply_text(
            f"👋 С возвращением, {user.first_name or 'друг'}!\n\n"
            f"📊 Твоя дневная норма: {user.profile.daily_calories} ккал\n"
            f"🍽️ Добавить еду: /add\n"
            f"📈 Статистика: /today"
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /help."""
    text = (
        "📖 <b>Команды бота:</b>\n\n"
        "🍽️ <b>Еда:</b>\n"
        "/add — Добавить прием пищи\n"
        "/today — Статистика за сегодня\n\n"
        "👤 <b>Профиль:</b>\n"
        "/register — Заполнить профиль\n"
        "/profile — Мои данные\n\n"
        "📊 <b>Статистика:</b>\n"
        "/stats — Подробная статистика\n\n"
        "❓ <b>Помощь:</b>\n"
        "/help — Эта справка\n"
        "/start — Начать сначала"
    )
    await update.message.reply_text(text, parse_mode="HTML")


def register_handlers(application: Application) -> None:
    """Регистрация обработчиков."""
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
