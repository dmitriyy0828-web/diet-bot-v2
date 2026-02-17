"""Обработчики добавления еды."""
from telegram import Update, InputFile
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)
from src.database import get_db
from src.models import FoodLog
from src.services.user_service import get_user_by_telegram_id, has_profile
from src.services.nutrition_calc import calculate_food_nutrition
from src.services.ai_vision_service import analyze_food_photo
from src.services.table_generator import generate_food_table
from src.keyboards.food_menu import get_food_keyboard, get_ai_vision_keyboard
import requests
import io
from PIL import Image
import logging

logger = logging.getLogger(__name__)


async def handle_barcode_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка фото: штрих-код → AI Vision (OCR отключен)."""
    user = get_user_by_telegram_id(update.effective_user.id)

    if not user or not has_profile(user):
        await update.message.reply_text("❌ Сначала заполните профиль: /register")
        return

    # Одно сообщение ожидания
    wait_message = await update.message.reply_text("⏳ Анализирую фото...")

    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)

    photo_bytes = io.BytesIO()
    await file.download_to_memory(photo_bytes)
    photo_bytes.seek(0)

    try:
        image = Image.open(photo_bytes)
        logger.info(f"Обработка фото от user={user.id}")

        # ШАГ 1: Пробуем найти штрих-код
        from pyzbar.pyzbar import decode

        barcodes = decode(image)
        logger.info(f"Штрих-кодов найдено: {len(barcodes)}")

        if barcodes:
            barcode_data = barcodes[0].data.decode("utf-8")

            url = f"https://world.openfoodfacts.org/api/v0/product/{barcode_data}.json"
            response = requests.get(url, timeout=5)
            data = response.json()

            if data.get("status") == 1 and data.get("product"):
                product = data["product"]
                nutriments = product.get("nutriments", {})

                name = (
                    product.get("product_name")
                    or product.get("product_name_ru")
                    or product.get("product_name_en")
                    or product.get("generic_name")
                    or "Неизвестный продукт"
                )

                # Ищем нутриенты в разных полях
                calories, proteins, fat, carbs = 0, 0, 0, 0
                for key in ["energy-kcal_100g", "energy-kcal", "energy_100g", "energy"]:
                    val = nutriments.get(key)
                    if val:
                        calories = val / 4.184 if key == "energy_100g" and val > 1000 else val
                        break
                for key in ["proteins_100g", "proteins", "protein_100g", "protein"]:
                    val = nutriments.get(key)
                    if val:
                        proteins = val
                        break
                for key in ["fat_100g", "fat"]:
                    val = nutriments.get(key)
                    if val:
                        fat = val
                        break
                for key in ["carbohydrates_100g", "carbohydrates", "carbs_100g", "carbs"]:
                    val = nutriments.get(key)
                    if val:
                        carbs = val
                        break

                await wait_message.delete()

                if calories == 0 and proteins == 0 and fat == 0 and carbs == 0:
                    await update.message.reply_text(
                        f"⚠️ {name}\n\nПродукт найден, но в базе нет данных о калорийности.\n"
                        f"Отправьте название текстом, например: «{name} 100г»"
                    )
                else:
                    # Формируем данные как для таблицы
                    food_data = {
                        "name": name,
                        "grams": 100,
                        "calories": round(calories),
                        "protein": round(proteins, 1),
                        "fat": round(fat, 1),
                        "carbs": round(carbs, 1),
                    }

                    # Генерируем картинку
                    table_img = generate_food_table([food_data])

                    with get_db() as db:
                        food_log = FoodLog(
                            user_id=user.id,
                            food_name=name,
                            grams=100,
                            calories=round(calories),
                            protein=round(proteins, 1),
                            fat=round(fat, 1),
                            carbs=round(carbs, 1),
                        )
                        db.add(food_log)
                        db.commit()
                        db.refresh(food_log)
                        log_id = food_log.id

                    keyboard = get_food_keyboard(log_id)

                    # Отправляем и картинку, и текст
                    if table_img:
                        user_photo_msg_id = update.message.message_id

                        photo_msg = await update.message.reply_photo(
                            photo=InputFile(io.BytesIO(table_img), filename="table.png"),
                            reply_markup=keyboard,
                        )

                        # Сохраняем оба ID для удаления при отмене
                        context.user_data[f"user_photo_{log_id}"] = user_photo_msg_id
                        context.user_data[f"bot_photo_{log_id}"] = photo_msg.message_id
                    else:
                        # Fallback если картинка не сгенерилась
                        await update.message.reply_text(
                            f"🍽️ {name} — 100г\n"
                            f"🔥 {round(calories)} ккал | Б:{round(proteins,1)}г Ж:{round(fat,1)}г У:{round(carbs,1)}г",
                            reply_markup=keyboard,
                        )
                return

        # ШАГ 2: AI Vision (OCR отключен)
        logger.info("Пробуем AI Vision...")
        photo_bytes.seek(0)
        image_bytes = photo_bytes.read()

        ai_result = analyze_food_photo(image_bytes, user_id=user.id)
        logger.info(f"AI Vision результат: {len(ai_result.get('foods', []))} продуктов")

        await wait_message.delete()

        if ai_result["foods"]:
            total_calories = 0
            foods_for_table = []
            foods_saved = []

            for food in ai_result["foods"]:
                with get_db() as db:
                    food_log = FoodLog(
                        user_id=user.id,
                        food_name=food["name"],
                        grams=food["grams"],
                        calories=food["calories"],
                        protein=food["protein"],
                        fat=food["fat"],
                        carbs=food["carbs"],
                    )
                    db.add(food_log)
                    db.commit()
                    db.refresh(food_log)
                    foods_saved.append((food_log.id, food))
                    foods_for_table.append(food)
                    total_calories += food["calories"]

            # Генерируем визуальную таблицу
            table_img = generate_food_table(
                foods_for_table, total_calories if len(foods_for_table) > 1 else None
            )

            # Текстовое описание
            if len(foods_saved) == 1:
                log_id, food = foods_saved[0]
                text_result = (
                    f"🍽️ {food['name']} — {food['grams']}г\n"
                    f"🔥 {food['calories']} ккал | Б:{food['protein']}г Ж:{food['fat']}г У:{food['carbs']}г"
                )
            else:
                text_result = (
                    f"📊 Распознано {len(foods_saved)} продукта, итого {total_calories} ккал"
                )

            keyboard = get_ai_vision_keyboard(foods_saved[0][0])

            # Отправляем картинку и текст
            if table_img:
                # Сохраняем ID сообщения пользователя (для удаления при отмене)
                user_photo_msg_id = update.message.message_id

                photo_msg = await update.message.reply_photo(
                    photo=InputFile(io.BytesIO(table_img), filename="table.png"),
                    caption=text_result,
                    reply_markup=keyboard,
                )

                # Сохраняем оба ID для удаления при отмене
                context.user_data[f"user_photo_{foods_saved[0][0]}"] = user_photo_msg_id
                context.user_data[f"bot_photo_{foods_saved[0][0]}"] = photo_msg.message_id
            else:
                await update.message.reply_text(text_result, reply_markup=keyboard)
        else:
            await update.message.reply_text(
                "❌ Не удалось распознать еду на фото.\n"
                "Отправьте название текстом, например: «гречка 200г»"
            )

    except Exception as e:
        await wait_message.delete()
        logger.error(f"Ошибка обработки фото: {e}")
        await update.message.reply_text(f"❌ Ошибка: {e}")


# Состояния для ConversationHandler
WAITING_FOOD = 1


async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало добавления еды."""
    user = get_user_by_telegram_id(update.effective_user.id)

    if not user or not has_profile(user):
        await update.message.reply_text(
            "❌ Сначала нужно заполнить профиль.\n" "Используй: /register"
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

    name, grams = parse_food_text(text)
    nutrition = calculate_food_nutrition(name, grams)

    with get_db() as db:
        food_log = FoodLog(
            user_id=user.id,
            food_name=nutrition["name"],
            grams=nutrition["grams"],
            calories=nutrition["calories"],
            protein=nutrition["protein"],
            fat=nutrition["fat"],
            carbs=nutrition["carbs"],
        )
        db.add(food_log)
        db.commit()
        db.refresh(food_log)
        log_id = food_log.id

    keyboard = get_food_keyboard(log_id)
    await update.message.reply_text(
        f"✅ Добавлено:\n\n"
        f"🍽️ {nutrition['name']}\n"
        f"⚖️ {nutrition['grams']}г\n"
        f"🔥 {nutrition['calories']} ккал\n"
        f"🥗 Б: {nutrition['protein']}г | "
        f"Ж: {nutrition['fat']}г | "
        f"У: {nutrition['carbs']}г",
        reply_markup=keyboard,
    )

    return ConversationHandler.END


def parse_food_text(text: str) -> tuple[str, int]:
    """Парсит текст еды на название и вес."""
    text = text.strip()
    import re

    weight_match = re.search(r"(\d+)\s*(г|грамм|g)", text.lower())

    if weight_match:
        grams = int(weight_match.group(1))
        name = re.sub(r"\s*,?\s*\d+\s*(г|грамм|g)\s*$", "", text, flags=re.IGNORECASE)
    else:
        grams = 100
        name = text

    return name.strip(), grams


async def handle_text_as_food(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка обычного текста как еды."""
    if context.user_data.get("in_conversation"):
        return

    user = get_user_by_telegram_id(update.effective_user.id)
    if not user or not has_profile(user):
        return
    if update.message.reply_to_message:
        return

    text = update.message.text.strip()
    name, grams = parse_food_text(text)
    nutrition = calculate_food_nutrition(name, grams)

    with get_db() as db:
        food_log = FoodLog(
            user_id=user.id,
            food_name=nutrition["name"],
            grams=nutrition["grams"],
            calories=nutrition["calories"],
            protein=nutrition["protein"],
            fat=nutrition["fat"],
            carbs=nutrition["carbs"],
        )
        db.add(food_log)
        db.commit()
        db.refresh(food_log)
        log_id = food_log.id

    keyboard = get_food_keyboard(log_id)
    await update.message.reply_text(
        f"✅ Добавлено:\n\n"
        f"🍽️ {nutrition['name']}\n"
        f"⚖️ {nutrition['grams']}г\n"
        f"🔥 {nutrition['calories']} ккал\n"
        f"🥗 Б: {nutrition['protein']}г | "
        f"Ж: {nutrition['fat']}г | "
        f"У: {nutrition['carbs']}г",
        reply_markup=keyboard,
    )


def register_handlers(application: Application) -> None:
    """Регистрация обработчиков."""
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("add", add_command)],
        states={WAITING_FOOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_food)]},
        fallbacks=[CommandHandler("cancel", lambda u, c: u.message.reply_text("Отменено"))],
        per_user=True,
    )
    application.add_handler(conv_handler)

    text_handler = MessageHandler(
        filters.TEXT & ~filters.COMMAND & ~filters.REPLY, handle_text_as_food
    )
    application.add_handler(text_handler)

    photo_handler = MessageHandler(filters.PHOTO, handle_barcode_photo)
    application.add_handler(photo_handler)
