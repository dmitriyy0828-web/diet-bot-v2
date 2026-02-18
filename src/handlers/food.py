"""Обработчики добавления еды через фото и текст."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from src.database import get_db
from src.models import FoodLog, Profile
from src.services.user_service import get_user_by_telegram_id, has_profile
from src.services.vision_service import analyze_food_photo_simple
from src.services.fatsecret_service import find_food_in_cache_or_api, calculate_nutrition_for_weight
from src.services.stats_service import get_today_stats
from src.services.nutrition_calc import calculate_food_nutrition
from src.services.table_generator import generate_food_table
import io
import re
import logging

logger = logging.getLogger(__name__)


async def handle_food_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка фото еды: Vision AI → FatSecret → сохранение."""
    user = get_user_by_telegram_id(update.effective_user.id)

    if not user or not has_profile(user):
        await update.message.reply_text("❌ Сначала заполните профиль: /register")
        return

    wait_message = await update.message.reply_text("🔍 Анализирую фото...")

    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)

        photo_bytes = io.BytesIO()
        await file.download_to_memory(photo_bytes)
        photo_bytes.seek(0)
        image_data = photo_bytes.read()

        vision_result = analyze_food_photo_simple(image_data)

        if not vision_result["success"] or not vision_result["foods"]:
            await wait_message.edit_text(
                "❌ Не удалось распознать еду на фото.\n"
                "Попробуйте отправить название текстом, например: «борщ 300г»"
            )
            return

        detected_foods = vision_result["foods"]
        logger.info(f"Detected {len(detected_foods)} foods: {detected_foods}")

        food_entries = []
        total_nutrition = {"calories": 0, "protein": 0, "fat": 0, "carbs": 0}
        not_found_items = []

        await wait_message.edit_text(f"📊 Найдено {len(detected_foods)} продуктов. Считаю...")

        for item in detected_foods:
            food_name = item["food"]
            weight = item["weight"]

            food_data = find_food_in_cache_or_api(food_name)

            if food_data:
                nutrition = calculate_nutrition_for_weight(food_data, weight)
                food_entries.append(nutrition)

                total_nutrition["calories"] += nutrition["calories"]
                total_nutrition["protein"] += nutrition["protein"]
                total_nutrition["fat"] += nutrition["fat"]
                total_nutrition["carbs"] += nutrition["carbs"]
            else:
                not_found_items.append(food_name)
                not_found_entry = {
                    "name": food_name,
                    "grams": weight,
                    "calories": 0,
                    "protein": 0,
                    "fat": 0,
                    "carbs": 0,
                    "fiber": 0,
                }
                food_entries.append(not_found_entry)

        log_ids = []
        with get_db() as db:
            for entry in food_entries:
                food_log = FoodLog(
                    user_id=user.id,
                    food_name=entry["name"],
                    grams=entry["grams"],
                    calories=entry["calories"],
                    protein=entry["protein"],
                    fat=entry["fat"],
                    carbs=entry["carbs"],
                    fiber=entry.get("fiber", 0),
                )
                db.add(food_log)
                db.commit()
                db.refresh(food_log)
                log_ids.append(food_log.id)

        today_stats = get_today_stats(user.id)
        profile = db.query(Profile).filter_by(user_id=user.id).first()
        daily_calories = profile.daily_calories if profile else 2000
        remaining = daily_calories - today_stats["calories"]

        await wait_message.delete()

        await send_food_response(
            update,
            food_entries,
            today_stats,
            daily_calories,
            remaining,
            log_ids[0] if log_ids else None,
            not_found_items if len(food_entries) > 1 else None,
        )

    except Exception as e:
        logger.error(f"Ошибка обработки фото: {e}", exc_info=True)
        await wait_message.edit_text(f"❌ Ошибка при обработке: {e}")


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
    if text.startswith("/"):
        return

    wait_message = await update.message.reply_text("🔍 Считаю...")

    try:
        name, grams = parse_food_text(text)

        food_data = find_food_in_cache_or_api(name)

        if food_data:
            nutrition = calculate_nutrition_for_weight(food_data, grams)
        else:
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
                fiber=nutrition.get("fiber", 0),
            )
            db.add(food_log)
            db.commit()
            db.refresh(food_log)
            log_id = food_log.id

            today_stats = get_today_stats(user.id)
            profile = db.query(Profile).filter_by(user_id=user.id).first()
            daily_calories = profile.daily_calories if profile else 2000
            remaining = daily_calories - today_stats["calories"]

        await wait_message.delete()

        await send_food_response(
            update, [nutrition], today_stats, daily_calories, remaining, log_id
        )

    except Exception as e:
        logger.error(f"Ошибка обработки текста: {e}", exc_info=True)
        await wait_message.edit_text(f"❌ Ошибка: {e}")


async def send_food_response(
    update: Update,
    food_entries: list,
    today_stats: dict,
    daily_calories: int,
    remaining: int,
    log_id: int,
    not_found_items: list = None,
) -> None:
    """Отправка ответа с таблицей и статистикой."""

    # Прогресс-бар
    progress_bar = generate_progress_bar(today_stats["calories"], daily_calories)
    remaining_text = f"{remaining} ккал" if remaining >= 0 else f"{abs(remaining)} ккал ПРЕВЫШЕНО"

    progress_text = (
        f"📊 Прогресс на сегодня:\n"
        f"{today_stats['calories']} из {daily_calories} ккал\n"
        f"{progress_bar}\n"
        f"Осталось: {remaining_text}"
    )

    # Таблица
    total_calories = sum(e["calories"] for e in food_entries) if len(food_entries) > 1 else None
    table_img = generate_food_table(food_entries, total_calories)

    # Клавиатура
    keyboard = (
        InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("✏️ Изменить", callback_data=f"ai_edit:{log_id}"),
                    InlineKeyboardButton("🗑️ Удалить", callback_data=f"ai_cancel:{log_id}"),
                ]
            ]
        )
        if log_id
        else None
    )

    # Предупреждение о не найденных
    warning_text = ""
    if not_found_items:
        warning_text = f"\n⚠️ Не найдены в базе: {', '.join(not_found_items)}"

    caption = f"{progress_text}{warning_text}"

    if table_img:
        await update.message.reply_photo(
            photo=InputFile(io.BytesIO(table_img), filename="food_table.png"),
            caption=caption,
            reply_markup=keyboard,
        )
    else:
        foods_text = ""
        for i, entry in enumerate(food_entries, 1):
            foods_text += (
                f"{i}. {entry['name']} — {entry['grams']}г\n"
                f"   🔥 {entry['calories']} ккал | "
                f"Б:{entry['protein']}г Ж:{entry['fat']}г У:{entry['carbs']}г\n"
            )
        await update.message.reply_text(
            f"✅ Добавлено:\n\n{foods_text}\n{caption}", reply_markup=keyboard
        )


def parse_food_text(text: str) -> tuple[str, int]:
    """Парсит текст еды на название и вес."""
    text = text.strip()

    weight_match = re.search(r"(\d+)\s*(г|грамм|g)", text.lower())

    if weight_match:
        grams = int(weight_match.group(1))
        name = re.sub(r"\s*,?\s*\d+\s*(г|грамм|g)\s*$", "", text, flags=re.IGNORECASE)
    else:
        grams = 100
        name = text

    return name.strip(), grams


def generate_progress_bar(current: int, total: int, length: int = 25) -> str:
    """Генерирует визуальный прогресс-бар."""
    if total <= 0:
        return "▯" * length

    filled = int(min(current / total, 1.0) * length)
    empty = length - filled

    return "🟩" * filled + "▯" * empty


def register_handlers(application: Application) -> None:
    """Регистрация обработчиков."""
    # Текст как еда
    text_handler = MessageHandler(
        filters.TEXT & ~filters.COMMAND & ~filters.REPLY, handle_text_as_food
    )
    application.add_handler(text_handler)

    # Фото еды
    photo_handler = MessageHandler(filters.PHOTO, handle_food_photo)
    application.add_handler(photo_handler)
