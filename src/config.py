"""Конфигурация бота из переменных окружения."""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    """Настройки бота."""

    BOT_TOKEN: str
    OPENROUTER_API_KEY: str
    DATABASE_URL: str
    ADMIN_ID: int | None

    @classmethod
    def from_env(cls) -> "Config":
        """Загрузка конфигурации из окружения."""
        return cls(
            BOT_TOKEN=os.getenv("BOT_TOKEN", ""),
            OPENROUTER_API_KEY=os.getenv("OPENROUTER_API_KEY", ""),
            DATABASE_URL=os.getenv("DATABASE_URL", "sqlite:///diet_bot.db"),
            ADMIN_ID=int(os.getenv("ADMIN_ID")) if os.getenv("ADMIN_ID") else None,
        )

    def validate(self) -> None:
        """Проверка обязательных настроек."""
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN не установлен в .env")
        if not self.OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY не установлен в .env")


# Глобальный экземпляр конфигурации
config = Config.from_env()
