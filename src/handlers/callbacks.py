"""Обработчики inline кнопок."""
from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes
from src.database import get_db
from src.models import FoodLog


async def food_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка кнопок под записью о еде."""
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
                
                # Удаляем сообщение с таблицей
                try:
                    await query.message.delete()
                except:
                    pass
                
                await query.message.reply_text(
                    f"❌ Запись «{food_name}» удалена."
                )
            else:
                await query.message.reply_text("⚠️ Запись не найдена.")


def register_handlers(application: Application) -> None:
    """Регистрация обработчиков."""
    application.add_handler(
        CallbackQueryHandler(food_callback, pattern="^(delete:)")
    )
