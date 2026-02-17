"""Обработчики регистрации профиля."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)
from src.database import get_db
from src.models import User, Profile, Gender, Goal, ActivityLevel
from src.services.user_service import get_or_create_user, get_user_by_telegram_id
from src.services.nutrition_calc import calculate_daily_needs

# Состояния регистрации
GENDER, AGE, HEIGHT, WEIGHT, TARGET_WEIGHT, GOAL, ACTIVITY, CONFIRM = range(8)


async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало регистрации (вызывается из start_callback)."""
    query = update.callback_query
    await query.answer()
    
    user = get_or_create_user(update.effective_user)
    context.user_data["user_id"] = user.id
    
    return await ask_gender(update, context)


async def register_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало регистрации через команду /register."""
    user = get_or_create_user(update.effective_user)

    if user.profile:
        await update.message.reply_text(
            "⚠️ У тебя уже есть профиль.\n"
            "Используй /profile для просмотра."
        )
        return ConversationHandler.END

    context.user_data["user_id"] = user.id
    
    return await ask_gender(update, context)


async def ask_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Шаг 1: Запрос пола."""
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("М", callback_data="male"),
                InlineKeyboardButton("Ж", callback_data="female"),
            ]
        ]
    )

    await update.message.reply_text(
        "👤 <b>Регистрация профиля</b>\n\n"
        "Шаг 1/7: Укажи свой пол:",
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    return GENDER


async def gender_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора пола."""
    query = update.callback_query
    await query.answer()

    context.user_data["gender"] = query.data

    await query.edit_message_text(
        "👤 <b>Регистрация профиля</b>\n\n"
        "Шаг 2/7: Сколько тебе лет?\n"
        "<i>(отправь числом, например: 25)</i>",
        parse_mode="HTML",
    )
    return AGE


async def age_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ввода возраста."""
    try:
        age = int(update.message.text)
        if not (10 <= age <= 100):
            raise ValueError

        context.user_data["age"] = age

        await update.message.reply_text(
            "👤 <b>Регистрация профиля</b>\n\n"
            "Шаг 3/7: Какой у тебя рост (в см)?\n"
            "<i>(отправь числом, например: 175)</i>",
            parse_mode="HTML",
        )
        return HEIGHT
    except ValueError:
        await update.message.reply_text(
            "❌ Введи корректный возраст (10-100 лет)\n"
            "<i>(отправь числом, например: 25)</i>",
            parse_mode="HTML",
        )
        return AGE


async def height_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ввода роста."""
    try:
        height = int(update.message.text)
        if not (100 <= height <= 250):
            raise ValueError

        context.user_data["height"] = height

        await update.message.reply_text(
            "👤 <b>Регистрация профиля</b>\n\n"
            "Шаг 4/7: Какой у тебя текущий вес (в кг)?\n"
            "<i>(отправь числом, например: 70.5)</i>",
            parse_mode="HTML",
        )
        return WEIGHT
    except ValueError:
        await update.message.reply_text(
            "❌ Введи корректный рост (100-250 см)\n"
            "<i>(отправь числом, например: 175)</i>",
            parse_mode="HTML",
        )
        return HEIGHT


async def weight_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ввода веса."""
    try:
        weight = float(update.message.text.replace(",", "."))
        if not (30 <= weight <= 200):
            raise ValueError

        context.user_data["weight"] = weight

        await update.message.reply_text(
            "👤 <b>Регистрация профиля</b>\n\n"
            "Шаг 5/7: Какой у тебя целевой вес (в кг)?\n"
            "<i>К какой цели хочешь прийти? Сколько хочешь весить по итогу?</i>\n"
            "<i>(отправь числом или 0, если просто хочешь похудеть без конкретной цели)</i>",
            parse_mode="HTML",
        )
        return TARGET_WEIGHT
    except ValueError:
        await update.message.reply_text(
            "❌ Введи корректный вес (30-200 кг)\n"
            "<i>(отправь числом, например: 70.5)</i>",
            parse_mode="HTML",
        )
        return WEIGHT


async def target_weight_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка целевого веса."""
    try:
        target = float(update.message.text.replace(",", "."))
        if target == 0:
            target = None
        elif not (30 <= target <= 200):
            raise ValueError

        context.user_data["target_weight"] = target

        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Похудеть", callback_data="lose")],
                [InlineKeyboardButton("Поддерживать вес", callback_data="maintain")],
                [InlineKeyboardButton("Набрать массу", callback_data="gain")],
            ]
        )

        await update.message.reply_text(
            "👤 <b>Регистрация профиля</b>\n\n" 
            "Шаг 6/7: Какая у тебя цель?",
            reply_markup=keyboard,
            parse_mode="HTML",
        )
        return GOAL
    except ValueError:
        await update.message.reply_text(
            "❌ Введи корректный вес (30-200 кг) или 0\n"
            "<i>(0 — если просто хочешь похудеть без конкретной цели)</i>",
            parse_mode="HTML",
        )
        return TARGET_WEIGHT


async def goal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора цели."""
    query = update.callback_query
    await query.answer()

    context.user_data["goal"] = query.data

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Низкая (сидячий образ)", callback_data="low")],
            [InlineKeyboardButton("Средняя (спорт 3-5 раз)", callback_data="moderate")],
            [InlineKeyboardButton("Высокая (спорт 6-7 раз)", callback_data="high")],
        ]
    )

    await query.edit_message_text(
        "👤 <b>Регистрация профиля</b>\n\n" 
        "Шаг 7/7: Какой у тебя уровень активности?",
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    return ACTIVITY


def get_activity_multiplier(level: str) -> float:
    """Получить коэффициент активности."""
    multipliers = {
        "low": 1.2,
        "moderate": 1.55,
        "high": 1.725,
    }
    return multipliers.get(level, 1.2)


async def activity_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка активности и финал."""
    query = update.callback_query
    await query.answer()

    context.user_data["activity"] = query.data
    
    # Создаем профиль и показываем сводку
    data = context.user_data
    
    with get_db() as db:
        profile = Profile(
            user_id=data["user_id"],
            gender=Gender(data["gender"]),
            age=data["age"],
            height_cm=data["height"],
            current_weight_kg=data["weight"],
            target_weight_kg=data.get("target_weight"),
            goal=Goal(data["goal"]),
            activity_level=ActivityLevel(data["activity"]),
        )
        
        # Рассчитываем нормы
        needs = calculate_daily_needs(profile)
        profile.daily_calories = needs["calories"]
        profile.daily_protein = needs["protein"]
        profile.daily_fat = needs["fat"]
        profile.daily_carbs = needs["carbs"]
        
        db.add(profile)
        db.commit()
    
    # Формируем сводку
    gender_text = "М" if data["gender"] == "male" else "Ж"
    goal_text = {
        "lose": "Похудеть",
        "maintain": "Поддерживать",
        "gain": "Набрать массу",
    }.get(data["goal"], data["goal"])
    activity_text = {
        "low": "Низкая",
        "moderate": "Средняя",
        "high": "Высокая",
    }.get(data["activity"], data["activity"])
    
    target_weight_text = f"{data.get('target_weight')} кг" if data.get('target_weight') else "-"
    activity_multiplier = get_activity_multiplier(data["activity"])
    
    await query.edit_message_text(
        f"✅ <b>Профиль создан!</b>\n\n"
        f"📋 <b>Ваши данные:</b>\n"
        f"• Пол: {gender_text}\n"
        f"• Возраст: {data['age']} лет\n"
        f"• Рост: {data['height']} см\n"
        f"• Вес: {data['weight']} кг\n"
        f"• Целевой вес: {target_weight_text}\n"
        f"• Цель: {goal_text}\n"
        f"• Активность: {activity_text}\n\n"
        f"📊 <b>Дневная норма:</b>\n"
        f"🔥 {needs['calories']} ккал\n"
        f"🥗 Б: {needs['protein']}г | Ж: {needs['fat']}г | У: {needs['carbs']}г\n\n"
        f"📝 <i>Как считается:</i>\n"
        f"<i>Mifflin-St Jeor: базовый обмен × {activity_multiplier}</i>\n"
        f"<i>(БО: ~{needs['calories'] // activity_multiplier} ккал)</i>\n"
        f"<i>+ корректировка под цель «{goal_text}»</i>",
        parse_mode="HTML",
    )
    
    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена регистрации."""
    await update.message.reply_text("❌ Регистрация отменена.")
    context.user_data.clear()
    return ConversationHandler.END


def register_handlers(application: Application) -> None:
    """Регистрация обработчиков."""
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("register", register_start)],
        states={
            GENDER: [CallbackQueryHandler(gender_handler, pattern="^(male|female)$")],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, age_handler)],
            HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, height_handler)],
            WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, weight_handler)],
            TARGET_WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, target_weight_handler)],
            GOAL: [CallbackQueryHandler(goal_handler, pattern="^(lose|maintain|gain)$")],
            ACTIVITY: [CallbackQueryHandler(activity_handler, pattern="^(low|moderate|high)$")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(conv_handler)
