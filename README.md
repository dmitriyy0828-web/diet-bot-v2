# Diet Bot v2

Персональный диетолог в Telegram. Отслеживание питания, расчет калорий и статистика.

## Структура проекта

```
diet-bot-v2/
├── bot.py              # Точка входа
├── src/
│   ├── config.py       # Конфигурация из .env
│   ├── database.py     # Подключение к БД
│   ├── models/         # SQLAlchemy модели
│   ├── handlers/       # Обработчики команд
│   ├── services/       # Бизнес-логика
│   ├── keyboards/      # Клавиатуры Telegram
│   └── utils/          # Вспомогательные функции
└── tests/              # Тесты
```

## Установка

1. Клонировать репозиторий
2. Создать виртуальное окружение:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # или venv\Scripts\activate  # Windows
   ```
3. Установить зависимости:
   ```bash
   pip install -r requirements.txt
   ```
4. Создать `.env` файл (скопировать из `.env.example`)
5. Запустить:
   ```bash
   python bot.py
   ```

## Команды

- `/start` — Начало работы
- `/register` — Регистрация профиля
- `/add` — Добавить еду
- `/today` — Статистика за сегодня
- `/stats` — Подробная статистика
- `/help` — Справка
