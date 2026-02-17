"""Генератор визуальных таблиц для результатов."""
import io
from PIL import Image, ImageDraw, ImageFont
import logging

logger = logging.getLogger(__name__)


def generate_food_table(foods: list[dict], total_calories: int = None) -> bytes:
    """
    Генерирует изображение таблицы с продуктами.
    """
    try:
        # Размеры - компактнее
        width = 700
        row_height = 45
        header_height = 50
        footer_height = 50 if len(foods) > 1 else 0
        padding = 15

        height = header_height + (len(foods) * row_height) + footer_height + padding

        # Создаем изображение с белым фоном
        img = Image.new("RGB", (width, height), color="white")
        draw = ImageDraw.Draw(img)

        # Шрифты
        try:
            font_header = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 15
            )
            font_data = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
            font_cal = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16
            )
            font_footer = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16
            )
        except:
            font_header = ImageFont.load_default()
            font_data = font_header
            font_cal = font_header
            font_footer = font_header

        # Цвета
        color_text = "#333333"
        color_light = "#f5f5f5"
        color_border = "#2196F3"
        color_cal = "#d32f2f"
        color_header_bg = "#e3f2fd"

        # === ШАПКА ТАБЛИЦЫ ===
        y = 10

        # Ширины колонок - добавляем клетчатку
        col_widths = [200, 60, 80, 60, 60, 60, 60]  # Название, гр, ккал, Б, Ж, У, Клетчатка
        col_x = [15]
        for w in col_widths[:-1]:
            col_x.append(col_x[-1] + w)

        # Фон шапки
        draw.rectangle([(0, y), (width, y + 35)], fill=color_header_bg)

        # Заголовки столбцов - компактно
        headers = ["Продукт", "Вес", "Ккал", "Белки", "Жиры", "Углев.", "Клетч."]
        for i, (header, x) in enumerate(zip(headers, col_x)):
            if i == 2:  # Калории выделяем
                draw.text((x + 5, y + 10), header, font=font_header, fill=color_cal)
            else:
                draw.text((x + 5, y + 10), header, font=font_header, fill=color_text)

        y += 35

        # Горизонтальная линия под шапкой
        draw.line([(0, y), (width, y)], fill=color_border, width=2)

        # === СТРОКИ С ДАННЫМЫ ===
        total_protein = 0
        total_fat = 0
        total_carbs = 0
        total_fiber = 0

        for i, food in enumerate(foods):
            # Фон строки (чередуем)
            row_color = "white" if i % 2 == 0 else color_light
            draw.rectangle([(0, y), (width, y + row_height)], fill=row_color)

            # Горизонтальная линия
            draw.line([(0, y + row_height), (width, y + row_height)], fill="#e0e0e0", width=1)

            # Данные
            name = food["name"][:18] if len(food["name"]) > 18 else food["name"]
            draw.text((col_x[0] + 5, y + 12), name, font=font_data, fill=color_text)
            draw.text((col_x[1] + 10, y + 12), f"{food['grams']}г", font=font_data, fill=color_text)

            # Калории - выделены
            draw.text((col_x[2] + 5, y + 10), str(food["calories"]), font=font_cal, fill=color_cal)

            # БЖУ
            draw.text(
                (col_x[3] + 10, y + 12), str(food["protein"]), font=font_data, fill=color_text
            )
            draw.text((col_x[4] + 10, y + 12), str(food["fat"]), font=font_data, fill=color_text)
            draw.text((col_x[5] + 10, y + 12), str(food["carbs"]), font=font_data, fill=color_text)
            
            # Клетчатка
            fiber_val = food.get("fiber", 0)
            draw.text((col_x[6] + 10, y + 12), str(fiber_val), font=font_data, fill=color_text)

            # Считаем итоги
            total_protein += float(food["protein"])
            total_fat += float(food["fat"])
            total_carbs += float(food["carbs"])
            total_fiber += float(fiber_val)

            y += row_height

        # === ИТОГИ ===
        if len(foods) > 1:
            draw.rectangle([(0, y), (width, y + footer_height)], fill="#fff3e0")
            draw.line([(0, y), (width, y)], fill=color_border, width=2)

            # Итоговые значения
            draw.text((col_x[0] + 5, y + 15), "ИТОГО:", font=font_footer, fill=color_text)
            draw.text((col_x[2] + 5, y + 13), f"{total_calories}", font=font_cal, fill=color_cal)
            draw.text(
                (col_x[3] + 10, y + 15), f"{total_protein:.1f}", font=font_data, fill=color_text
            )
            draw.text((col_x[4] + 10, y + 15), f"{total_fat:.1f}", font=font_data, fill=color_text)
            draw.text(
                (col_x[5] + 10, y + 15), f"{total_carbs:.1f}", font=font_data, fill=color_text
            )
            draw.text(
                (col_x[6] + 10, y + 15), f"{total_fiber:.1f}", font=font_data, fill=color_text
            )

        # Внешняя рамка
        draw.rectangle([(0, 0), (width - 1, height - 1)], outline=color_border, width=2)

        # Вертикальные линии между столбцами
        for x in col_x[1:]:
            draw.line(
                [(x, 10), (x, height - (footer_height if len(foods) > 1 else 10))],
                fill="#e0e0e0",
                width=1,
            )

        # Сохраняем
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")
        img_bytes.seek(0)

        return img_bytes.getvalue()

    except Exception as e:
        logger.error(f"Ошибка генерации таблицы: {e}")
        return None
