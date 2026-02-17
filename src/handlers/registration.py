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
from src.services.user_service import get_or_create_user
from src.services.nutrition_calc import calculate_daily_needs

# Состояния регистрации
GENDER, AGE, HEIGHT, WEIGHT, TARGET_WEIGHT, GOAL, ACTIVITY = range(7)


async def register_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало регистрации."""
    user = get_or_create_user(update.effective_user)

    # Проверяем, есть ли уже профиль
    if user.profile:
        await update.message.reply_text(
            "⚠️ У тебя уже есть профиль.\n"
            "Используй /profile для просмотра или /delete_profile для удаления."
        )
        return ConversationHandler.END

    # Сохраняем user_id в контекст
    context.user_data["user_id"] = user.id

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Мужской", callback_data="male")],
            [InlineKeyboardButton("Женский", callback_data="female")],
        ]
    )

    await update.message.reply_text(
        "👤 <b>Регистрация профиля</b>\n\n" "Шаг 1/7: Укажи свой пол:",
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
        "✅ Пол сохранен\n\n" "Шаг 2/7: Сколько тебе лет?\n" "Отправь числом (например: 25)"
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
            "✅ Возраст сохранен\n\n"
            "Шаг 3/7: Какой у тебя рост (в см)?\n"
            "Отправь числом (например: 175)"
        )
        return HEIGHT
    except ValueError:
        await update.message.reply_text("❌ Введи корректный возраст (10-100 лет)")
        return AGE


async def height_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ввода роста."""
    try:
        height = int(update.message.text)
        if not (100 <= height <= 250):
            raise ValueError

        context.user_data["height"] = height

        await update.message.reply_text(
            "✅ Рост сохранен\n\n"
            "Шаг 4/7: Какой у тебя текущий вес (в кг)?\n"
            "Отправь числом (например: 70.5)"
        )
        return WEIGHT
    except ValueError:
        await update.message.reply_text("❌ Введи корректный рост (100-250 см)")
        return HEIGHT


async def weight_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ввода веса."""
    try:
        weight = float(update.message.text.replace(",", "."))
        if not (30 <= weight <= 200):
            raise ValueError

        context.user_data["weight"] = weight

        await update.message.reply_text(
            "✅ Вес сохранен\n\n"
            "Шаг 5/7: Какой у тебя целевой вес (в кг)?\n"
            "Отправь числом или напиши '0' если не знаешь"
        )
        return TARGET_WEIGHT
    except ValueError:
        await update.message.reply_text("❌ Введи корректный вес (30-200 кг)")
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
            "✅ Целевой вес сохранен\n\n" "Шаг 6/7: Какая у тебя цель?", reply_markup=keyboard
        )
        return GOAL
    except ValueError:
        await update.message.reply_text("❌ Введи корректный вес или 0")
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
        "✅ Цель сохранена\n\n" "Шаг 7/7: Какой у тебя уровень активности?", reply_markup=keyboard
    )
    return ACTIVITY


async def activity_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка активности и сохранение профиля."""
    query = update.callback_query
    await query.answer()

    context.user_data["activity"] = query.data

    # Создаем профиль
    with get_db() as db:
        profile = Profile(
            user_id=context.user_data["user_id"],
            gender=Gender(context.user_data["gender"]),
            age=context.user_data["age"],
            height_cm=context.user_data["height"],
            current_weight_kg=context.user_data["weight"],
            target_weight_kg=context.user_data.get("target_weight"),
            goal=Goal(context.user_data["goal"]),
            activity_level=ActivityLevel(query.data),
        )

        # Рассчитываем нормы
        needs = calculate_daily_needs(profile)
        profile.daily_calories = needs["calories"]
        profile.daily_protein = needs["protein"]
        profile.daily_fat = needs["fat"]
        profile.daily_carbs = needs["carbs"]

        db.add(profile)
        db.commit()

    # Очищаем контекст
    context.user_data.clear()

    await query.edit_message_text(
        f"🎉 <b>Профиль создан!</b>\n\n"
        f"📊 Твои дневные нормы:\n"
        f"🔥 {needs['calories']} ккал\n"
        f"🥗 Б: {needs['protein']}г | Ж: {needs['fat']}г | У: {needs['carbs']}г\n\n"
        f"Начни отслеживать питание: /add",
        parse_mode="HTML",
    )
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
