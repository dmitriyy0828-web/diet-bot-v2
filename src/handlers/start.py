"""Обработчики команд /start и /help."""
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from src.services.user_service import get_or_create_user, has_profile, get_user_by_telegram_id


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /start."""
    user = get_or_create_user(update.effective_user)

    if not has_profile(user):
        # Inline-кнопка регистрации
        keyboard = [
            [InlineKeyboardButton("📝 Зарегистрироваться", callback_data="start:register")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "👋 Привет! Я твой персональный диетолог.\n\n"
            "Я помогу отслеживать питание и достигать целей.\n\n"
            "Для начала нужно заполнить профиль:",
            reply_markup=reply_markup,
        )
    else:
        # Inline-кнопки под сообщением
        keyboard = [
            [InlineKeyboardButton("🍽️ Добавить еду", callback_data="start:add_food")],
            [InlineKeyboardButton("📊 Статистика", callback_data="start:stats")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"👋 С возвращением, {user.first_name or 'друг'}!\n\n"
            f"📊 Твоя дневная норма: {user.profile.daily_calories} ккал",
            reply_markup=reply_markup,
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /help."""
    text = (
        "📖 <b>Команды бота:</b>\n\n"
        "🍽️ <b>Еда:</b>\n"
        "/add - Добавить прием пищи\n"
        "/today - Статистика за сегодня\n\n"
        "👤 <b>Профиль:</b>\n"
        "/register - Заполнить профиль\n"
        "/profile - Мои данные\n\n"
        "📊 <b>Статистика:</b>\n"
        "/stats - Подробная статистика\n\n"
        "❓ <b>Помощь:</b>\n"
        "/help - Эта справка\n"
        "/start - Начать сначала"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка inline-кнопок из /start."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "start:register":
        # Запускаем регистрацию
        from src.handlers.registration import start_registration
        await start_registration(update, context)
    elif query.data == "start:add_food":
        await query.edit_message_text(
            "🍽️ Отправь мне:\n"
            "• Фото еды - я распознаю КБЖУ\n"
            "• Фото штрих-кода - найду в базе\n"
            "• Текст - например: '200 грамм гречки'"
        )
    elif query.data == "start:stats":
        user = get_user_by_telegram_id(update.effective_user.id)
        if not user or not has_profile(user):
            await query.edit_message_text("❌ Сначала заполни профиль: /register")
            return

        # Inline-кнопки для выбора периода
        keyboard = [
            [InlineKeyboardButton("📅 Сегодня", callback_data="stats:today")],
            [InlineKeyboardButton("📅 Вчера", callback_data="stats:yesterday")],
            [InlineKeyboardButton("📊 За неделю", callback_data="stats:week")],
            [InlineKeyboardButton("📈 За месяц", callback_data="stats:month")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "📊 Выбери период для статистики:",
            reply_markup=reply_markup,
        )


async def add_food_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка reply-кнопки 'Добавить еду' (для обратной совместимости)."""
    await update.message.reply_text(
        "🍽️ Отправь мне:\n"
        "• Фото еды - я распознаю КБЖУ\n"
        "• Фото штрих-кода - найду в базе\n"
        "• Текст - например: '200 грамм гречки'"
    )


async def stats_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка кнопки 'Статистика'."""
    user = get_user_by_telegram_id(update.effective_user.id)

    if not user or not has_profile(user):
        await update.message.reply_text("❌ Сначала заполни профиль: /register")
        return

    # Inline-кнопки для выбора периода
    keyboard = [
        [InlineKeyboardButton("📅 Сегодня", callback_data="stats:today")],
        [InlineKeyboardButton("📅 Вчера", callback_data="stats:yesterday")],
        [InlineKeyboardButton("📊 За неделю", callback_data="stats:week")],
        [InlineKeyboardButton("📈 За месяц", callback_data="stats:month")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "📊 Выбери период для статистики:",
        reply_markup=reply_markup,
    )


def register_handlers(application: Application) -> None:
    """Регистрация обработчиков."""
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))

    # Обработчик inline-кнопок из /start
    application.add_handler(CallbackQueryHandler(start_callback, pattern=r"^start:"))

    # Обработчики reply-кнопок (для обратной совместимости)
    application.add_handler(MessageHandler(filters.Regex(r"^🍽️ Добавить еду$"), add_food_button))
    application.add_handler(MessageHandler(filters.Regex(r"^📊 Статистика$"), stats_button))
