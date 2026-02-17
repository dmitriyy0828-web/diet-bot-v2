"""Обработчики inline кнопок."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    CommandHandler,
    filters,
    ContextTypes,
)
from src.database import get_db
from src.models import FoodLog
from src.keyboards.food_menu import get_ai_vision_keyboard
from src.services.gemma_service import parse_edit_command
from src.services.nutrition_calc import calculate_food_nutrition
import time
import logging

logger = logging.getLogger(__name__)

# Состояния для редактирования
WAITING_EDIT_INPUT = 1

# Таймаут редактирования в секундах (5 минут)
EDIT_TIMEOUT = 300


async def food_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка кнопок под записью о еде (delete и ai_cancel)."""
    query = update.callback_query
    await query.answer()

    data = query.data

    if data.startswith("delete:"):
        log_id = int(data.split(":")[1])

        with get_db() as db:
            food_log = db.query(FoodLog).filter_by(id=log_id).first()
            if food_log:
                food_name = food_log.food_name
                db.delete(food_log)
                db.commit()

                try:
                    await query.message.delete()
                except:
                    pass
                # Без уведомления - просто молча удаляем
            else:
                await query.message.reply_text("⚠️ Запись не найдена.")

    elif data.startswith("ai_cancel:"):
        log_id = int(data.split(":")[1])
        chat_id = query.message.chat_id

        with get_db() as db:
            food_log = db.query(FoodLog).filter_by(id=log_id).first()
            if food_log:
                db.delete(food_log)
                db.commit()

                # Удаляем сообщение бота (фото таблицы с кнопками)
                try:
                    await query.message.delete()
                except:
                    pass

                # Удаляем фото пользователя (исходное)
                user_photo_id = context.user_data.get(f"user_photo_{log_id}")
                if user_photo_id:
                    try:
                        await context.bot.delete_message(chat_id=chat_id, message_id=user_photo_id)
                    except:
                        pass

                # Очищаем контекст
                for key in [f"user_photo_{log_id}", f"bot_photo_{log_id}"]:
                    if key in context.user_data:
                        del context.user_data[key]

                # Без уведомления - просто молча удаляем
            else:
                await query.message.reply_text("⚠️ Запись не найдена.")


async def edit_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало редактирования."""
    query = update.callback_query
    await query.answer()

    data = query.data
    log_id = int(data.split(":")[1])

    # Сохраняем log_id и timestamp для таймаута
    context.user_data["editing_log_id"] = log_id
    context.user_data["edit_start_time"] = time.time()

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("◀️ Назад", callback_data=f"ai_back:{log_id}")]]
    )

    await query.message.reply_text(
        "✏️ Что хотите изменить?\n\n"
        "Напишите голосом или текстом, например:\n"
        "• «250 грамм» или «сто пятьдесят граммов»\n"
        "• «300 калорий»\n"
        "• «хочу рис вместо гречки»",
        reply_markup=keyboard,
    )

    return WAITING_EDIT_INPUT


async def back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка кнопки Назад."""
    query = update.callback_query
    await query.answer()

    # Очищаем контекст
    clear_edit_context(context)

    # Удаляем сообщение "Что хотите изменить?"
    await query.message.delete()
    # Без подтверждения "Возврат к результату" - просто молча закрываем
    return ConversationHandler.END


def clear_edit_context(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Очистка контекста редактирования."""
    for key in ["editing_log_id", "edit_start_time", "available_foods"]:
        if key in context.user_data:
            del context.user_data[key]


async def process_edit_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ввода изменений через Gemma."""
    text = update.message.text
    log_id = context.user_data.get("editing_log_id")
    start_time = context.user_data.get("edit_start_time")

    # Проверка таймаута (пункт 6)
    if start_time and (time.time() - start_time > EDIT_TIMEOUT):
        clear_edit_context(context)
        await update.message.reply_text(
            "⏰ Время редактирования истекло (5 минут).\n" "Начните заново, если нужно изменить."
        )
        return ConversationHandler.END

    if not log_id:
        await update.message.reply_text("⚠️ Ошибка: сессия редактирования не найдена.")
        return ConversationHandler.END

    # Получаем запись из БД
    with get_db() as db:
        food_log = db.query(FoodLog).filter_by(id=log_id).first()
        if not food_log:
            clear_edit_context(context)
            await update.message.reply_text("⚠️ Запись не найдена.")
            return ConversationHandler.END

        # Получаем все продукты пользователя за сегодня (для пункта 7)
        from datetime import datetime, timedelta

        today = datetime.now().date()
        today_logs = (
            db.query(FoodLog)
            .filter(
                FoodLog.user_id == food_log.user_id,
                FoodLog.created_at >= today,
                FoodLog.created_at < today + timedelta(days=1),
            )
            .all()
        )

        available_foods = [log.food_name for log in today_logs]

        # Отправляем в Gemma для анализа
        await update.message.reply_text("🤔 Думаю...")
        gemma_result = parse_edit_command(text, available_foods)

        # Проверяем нужно ли уточнение (пункт 7-B)
        if gemma_result.get("clarification_needed"):
            foods_list = "\n".join([f"• {name}" for name in available_foods[:10]])
            await update.message.reply_text(
                f"❓ Какой продукт вы хотите изменить?\n\n"
                f"Доступные:\n{foods_list}\n\n"
                f"Напишите название или номер (первое, второе...)"
            )
            # Не очищаем контекст, ждём уточнения
            return WAITING_EDIT_INPUT

        action = gemma_result.get("action")

        # Обработка смены продукта (новый функционал)
        if action == "change_product":
            new_product = gemma_result.get("new_product")
            if not new_product:
                await update.message.reply_text("❌ Не понял, на что меняем.")
                return WAITING_EDIT_INPUT

            # Сохраняем вес от старой записи
            old_grams = food_log.grams if food_log.grams > 0 else 100  # защита от 0

            # Ищем новый продукт (Open Food Facts + fallback)
            nutrition = calculate_food_nutrition(new_product, old_grams)

            # Удаляем старую запись
            db.delete(food_log)

            # Создаём новую
            new_log = FoodLog(
                user_id=food_log.user_id,
                food_name=nutrition["name"],
                grams=nutrition["grams"],
                calories=nutrition["calories"],
                protein=nutrition["protein"],
                fat=nutrition["fat"],
                carbs=nutrition["carbs"],
            )
            db.add(new_log)
            db.commit()
            db.refresh(new_log)

            clear_edit_context(context)

            keyboard = get_ai_vision_keyboard(new_log.id)
            await update.message.reply_text(
                f"✅ Продукт изменён:\n\n"
                f"🍽️ {nutrition['name']} — {nutrition['grams']}г\n"
                f"🔥 {nutrition['calories']} ккал | "
                f"Б:{nutrition['protein']}г Ж:{nutrition['fat']}г У:{nutrition['carbs']}г",
                reply_markup=keyboard,
            )
            return ConversationHandler.END

        # Обработка изменения граммовки
        if action == "change_grams":
            new_grams = gemma_result.get("value")
            if not new_grams:
                await update.message.reply_text("❌ Не удалось распознать число.")
                return WAITING_EDIT_INPUT

            # Защита от деления на ноль (пункт 1)
            old_grams = food_log.grams if food_log.grams > 0 else 100

            ratio = new_grams / old_grams

            food_log.grams = new_grams
            food_log.calories = round(food_log.calories * ratio)
            food_log.protein = round(food_log.protein * ratio, 1)
            food_log.fat = round(food_log.fat * ratio, 1)
            food_log.carbs = round(food_log.carbs * ratio, 1)

            db.commit()
            clear_edit_context(context)

            await update.message.reply_text(
                f"✅ Изменено: {new_grams}г\n\n"
                f"🍽️ {food_log.food_name}\n"
                f"🔥 {food_log.calories} ккал\n"
                f"🥗 Б:{food_log.protein}г Ж:{food_log.fat}г У:{food_log.carbs}г"
            )
            return ConversationHandler.END

        # Обработка изменения калорий
        if action == "change_calories":
            new_calories = gemma_result.get("value")
            if not new_calories:
                await update.message.reply_text("❌ Не удалось распознать число.")
                return WAITING_EDIT_INPUT

            food_log.calories = new_calories
            db.commit()
            clear_edit_context(context)

            await update.message.reply_text(
                f"✅ Изменено: {new_calories} ккал\n\n"
                f"🍽️ {food_log.food_name} ({food_log.grams}г)\n"
                f"🔥 {food_log.calories} ккал\n"
                f"🥗 Б:{food_log.protein}г Ж:{food_log.fat}г У:{food_log.carbs}г"
            )
            return ConversationHandler.END

        # Если не поняли
        await update.message.reply_text(
            "❓ Не понял команду. Попробуйте:\n"
            "• «250 грамм»\n"
            "• «300 калорий»\n"
            "• «хочу рис вместо гречки»"
        )
        return WAITING_EDIT_INPUT


def register_handlers(application: Application) -> None:
    """Регистрация обработчиков."""
    edit_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(edit_start_callback, pattern="^ai_edit:")],
        states={
            WAITING_EDIT_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_edit_input),
                CallbackQueryHandler(back_callback, pattern="^ai_back:"),
            ]
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: u.message.reply_text("Отменено"))],
    )
    application.add_handler(edit_conv_handler)

    application.add_handler(CallbackQueryHandler(food_callback, pattern="^(delete:|ai_cancel:)"))
