"""Обработчики статистики."""
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from src.services.user_service import get_user_by_telegram_id, has_profile
from src.services.stats_service import (
    get_today_stats,
    get_yesterday_stats,
    get_week_stats,
    get_month_stats,
)
from src.services.ai_cost_service import get_all_users_costs, get_total_costs

# ID админа (только этот пользователь может видеть /admin_costs)
ADMIN_TELEGRAM_ID = 310010786


async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Статистика за сегодня."""
    user = get_user_by_telegram_id(update.effective_user.id)

    if not user or not has_profile(user):
        await update.message.reply_text("❌ Сначала заполни профиль: /register")
        return

    stats = get_today_stats(user.id)
    profile = user.profile

    # Прогресс
    remaining = profile.daily_calories - stats["calories"]
    percentage = (
        int((stats["calories"] / profile.daily_calories) * 100) if profile.daily_calories > 0 else 0
    )

    # Формируем список еды
    food_text = "\n".join(stats["food_list"]) if stats["food_list"] else "Нет записей"

    await update.message.reply_text(
        f"📊 <b>Статистика за сегодня</b>\n\n"
        f"🔥 Калории: {stats['calories']} / {profile.daily_calories} ккал\n"
        f"📈 Прогресс: {percentage}%\n"
        f"📉 Осталось: {remaining} ккал\n\n"
        f"🥗 БЖУ:\n"
        f"   Белки: {stats['protein']}г / {profile.daily_protein}г\n"
        f"   Жиры: {stats['fat']}г / {profile.daily_fat}г\n"
        f"   Углеводы: {stats['carbs']}г / {profile.daily_carbs}г\n\n"
        f"🍽️ Съедено ({stats['count']} записей):\n"
        f"{food_text}",
        parse_mode="HTML",
    )


async def stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка callback-кнопок статистики."""
    query = update.callback_query
    await query.answer()

    user = get_user_by_telegram_id(update.effective_user.id)
    if not user or not has_profile(user):
        await query.edit_message_text("❌ Сначала заполни профиль: /register")
        return

    profile = user.profile
    data = query.data

    if data == "stats:today":
        stats = get_today_stats(user.id)
        period_name = "Сегодня"
    elif data == "stats:yesterday":
        stats = get_yesterday_stats(user.id)
        period_name = "Вчера"
    elif data == "stats:week":
        stats = get_week_stats(user.id)
        await query.edit_message_text(
            f"📊 <b>Статистика за неделю</b>\n\n"
            f"🔥 Всего калорий: {stats.get('total_calories', 0)} ккал\n"
            f"📈 Среднее в день: {stats.get('avg_calories', 0)} ккал\n"
            f"📉 Мин: {stats.get('min_cal', 0)} / Макс: {stats.get('max_cal', 0)} ккал\n"
            f"📅 Дней с записями: {stats.get('total_days', 0)}\n\n"
            f"🥗 БЖУ за неделю:\n"
            f"   Белки: {stats.get('protein', 0)}г\n"
            f"   Жиры: {stats.get('fat', 0)}г\n"
            f"   Углеводы: {stats.get('carbs', 0)}г",
            parse_mode="HTML",
        )
        return
    elif data == "stats:month":
        stats = get_month_stats(user.id)
        await query.edit_message_text(
            f"📊 <b>Статистика за месяц</b>\n\n"
            f"🔥 Всего калорий: {stats.get('total_calories', 0)} ккал\n"
            f"📈 Среднее в день: {stats.get('avg_calories', 0)} ккал\n"
            f"📉 Мин: {stats.get('min_cal', 0)} / Макс: {stats.get('max_cal', 0)} ккал\n"
            f"📅 Дней с записями: {stats.get('total_days', 0)}\n\n"
            f"🥗 БЖУ за месяц:\n"
            f"   Белки: {stats.get('protein', 0)}г\n"
            f"   Жиры: {stats.get('fat', 0)}г\n"
            f"   Углеводы: {stats.get('carbs', 0)}г",
            parse_mode="HTML",
        )
        return
    else:
        return

    # Для сегодня и вчера (одинаковый формат)
    remaining = profile.daily_calories - stats["calories"]
    percentage = (
        int((stats["calories"] / profile.daily_calories) * 100) if profile.daily_calories > 0 else 0
    )
    food_text = "\n".join(stats["food_list"]) if stats["food_list"] else "Нет записей"

    await query.edit_message_text(
        f"📊 <b>Статистика: {period_name}</b>\n\n"
        f"🔥 Калории: {stats['calories']} / {profile.daily_calories} ккал\n"
        f"📈 Прогресс: {percentage}%\n"
        f"📉 Осталось: {remaining} ккал\n\n"
        f"🥗 БЖУ:\n"
        f"   Белки: {stats['protein']}г / {profile.daily_protein}г\n"
        f"   Жиры: {stats['fat']}г / {profile.daily_fat}г\n"
        f"   Углеводы: {stats['carbs']}г / {profile.daily_carbs}г\n\n"
        f"🍽️ Съедено ({stats['count']} записей):\n"
        f"{food_text}",
        parse_mode="HTML",
    )


async def admin_costs_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда для админа: статистика расходов на AI."""
    # Проверяем что вызвал только админ
    if update.effective_user.id != ADMIN_TELEGRAM_ID:
        await update.message.reply_text("❌ Нет доступа.")
        return
    
    # Получаем данные за 30 дней
    total = get_total_costs(days=30)
    users = get_all_users_costs(days=30)
    
    # Формируем отчёт
    text = (
        f"💰 <b>Расходы на AI (30 дней)</b>\n\n"
        f"Общие затраты: ${total['total_cost_usd']} (~{total['total_cost_rub']}₽)\n"
        f"Всего запросов: {total['total_requests']}\n\n"
        f"👥 <b>По пользователям:</b>\n"
    )
    
    for user in users:
        text += (
            f"• {user['username']}: ${user['total_cost_usd']} "
            f"({user['request_count']} запр.)\n"
        )
    
    await update.message.reply_text(text, parse_mode="HTML")


def register_handlers(application: Application) -> None:
    """Регистрация обработчиков."""
    application.add_handler(CommandHandler("today", today_command))
    application.add_handler(CommandHandler("admin_costs", admin_costs_command))
    application.add_handler(CallbackQueryHandler(stats_callback, pattern=r"^stats:"))
