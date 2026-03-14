import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass
class Settings:
    timeweb_agent_id: str
    timeweb_api_token: str
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
    timeweb_agent_id=_get_env("TIMEWEB_AGENT_ID"),
    timeweb_api_token=_get_env("TIMEWEB_API_TOKEN"),
    telegram_bot_token=_get_env("TELEGRAM_BOT_TOKEN"),
)
