"""Обработчики статистики."""
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from src.services.user_service import get_user_by_telegram_id, has_profile
from src.services.stats_service import get_today_stats


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


def register_handlers(application: Application) -> None:
    """Регистрация обработчиков."""
    application.add_handler(CommandHandler("today", today_command))
