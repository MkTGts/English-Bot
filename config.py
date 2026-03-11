import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass
class Settings:
    gemini_api_key: str
    telegram_bot_token: str


def _get_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(
            f"Переменная окружения {name} не задана. "
            f"Создайте файл .env (на основе .env.example) и укажите значение."
        )
    return value

settings = Settings(
    gemini_api_key=_get_env("GEMINI_API_KEY"),
    telegram_bot_token=_get_env("TELEGRAM_BOT_TOKEN"),
)

