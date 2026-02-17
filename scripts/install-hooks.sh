#!/bin/bash
# Установка pre-commit hooks для Diet Bot v2

echo "Установка pre-commit..."

# Устанавливаем pre-commit
pip install pre-commit

# Устанавливаем хуки
cd /root/.openclaw/workspace/projects/diet-bot-v2
pre-commit install

# Создаем baseline для detect-secrets (если его нет)
if [ ! -f .secrets.baseline ]; then
    echo "Создание baseline для проверки секретов..."
    detect-secrets scan > .secrets.baseline
fi

echo "Pre-commit hooks установлены!"
echo ""
echo "Теперь перед каждым коммитом будут выполняться проверки:"
echo "  ✅ Синтаксис Python"
echo "  ✅ Отсутствие API ключей и секретов"
echo "  ✅ Форматирование кода (Black)"
echo "  ✅ Линтинг (Flake8)"
echo "  ✅ Базовая безопасность (Bandit)"
echo ""
echo "Для ручного запуска проверок: pre-commit run --all-files"
