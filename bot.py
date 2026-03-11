import asyncio
import logging
from typing import Dict, List, Any

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram import Router

from .config import settings
from .ai_service import generate_tutor_reply


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


router = Router()

# In-memory storage for last messages per user.
# Key: Telegram user id, Value: list of message dicts [{"role": "user"/"assistant", "content": "..."}]
user_contexts: Dict[int, List[Dict[str, Any]]] = {}

MAX_CONTEXT_MESSAGES = 10  # roughly last 5 exchanges (user + assistant)


def _update_user_context(user_id: int, role: str, content: str) -> List[Dict[str, Any]]:
    history = user_contexts.get(user_id, [])
    history.append({"role": role, "content": content})
    # keep only last N messages
    if len(history) > MAX_CONTEXT_MESSAGES:
        history = history[-MAX_CONTEXT_MESSAGES:]
    user_contexts[user_id] = history
    return history


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    text = (
        "Привет! 👋\n\n"
        "Я бот-помощник для практики английского языка.\n\n"
        "Напиши мне сообщение на английском — я отвечу на английском, "
        "поддержу разговор, задам встречный вопрос и аккуратно исправлю твои ошибки "
        "с короткими объяснениями на русском.\n\n"
        "Просто начни диалог на английском 👇"
    )
    await message.answer(text)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    text = (
        "ℹ️ *Помощь*\n\n"
        "/start — краткое описание бота\n"
        "/help — эта справка\n"
        "/new — начать новый диалог (очистить контекст)\n\n"
        "Дальше просто пиши мне сообщения *на английском языке*.\n"
        "Я буду отвечать на английском, поддерживать разговор и мягко исправлять ошибки "
        "с короткими объяснениями на русском."
    )
    await message.answer(text, parse_mode="Markdown")


@router.message(Command("new"))
async def cmd_new(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else 0
    if user_id in user_contexts:
        user_contexts.pop(user_id, None)

    text = (
        "Начинаем новый диалог. ✨\n\n"
        "Напиши новое сообщение на английском — я буду отвечать как преподаватель, "
        "учитывая уже обновлённый контекст."
    )
    await message.answer(text)


@router.message(F.text)
async def handle_text_message(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else 0
    user_text = message.text or ""

    if not user_text.strip():
        await message.answer("Пожалуйста, отправь осмысленный текст на английском языке.")
        return

    # Update context with the latest user message and get recent history.
    history = _update_user_context(user_id, "user", user_text)

    await message.chat.action.typing()

    try:
        reply_text = await generate_tutor_reply(history[-MAX_CONTEXT_MESSAGES:])
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to get response from OpenAI: %s", exc)
        await message.answer(
            "Произошла ошибка при обращении к нейросети. "
            "Попробуй ещё раз чуть позже."
        )
        return

    if not reply_text:
        await message.answer(
            "Мне не удалось сформировать ответ. "
            "Пожалуйста, попробуй ещё раз или переформулируй сообщение."
        )
        return

    # Save assistant reply to context.
    _update_user_context(user_id, "assistant", reply_text)

    await message.answer(reply_text)


async def main() -> None:
    bot = Bot(token=settings.telegram_bot_token, parse_mode="HTML")
    dp = Dispatcher()
    dp.include_router(router)

    logger.info("Bot is starting polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")

