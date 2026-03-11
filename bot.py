import asyncio
import logging
from typing import List, Dict, Any

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

from .config import settings
from .ai_service import generate_response
from .dialog_manager import DialogManager
from .prompts import SYSTEM_PROMPT


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


router = Router()

# Manager that keeps separate dialog histories per Telegram user.
dialog_manager = DialogManager(max_messages=6)


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
    dialog_manager.clear_history(user_id)

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

    # Get current history for this user (separate per telegram_id).
    history = dialog_manager.get_history(user_id)

    # Build messages for OpenAI: system prompt + existing history + current user message.
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *history,
        {"role": "user", "content": user_text},
    ]

    await message.chat.action.typing()

    try:
        reply_text = await generate_response(messages)
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

    # Update dialog history for this user: add user message and assistant reply.
    dialog_manager.append_message(user_id, "user", user_text)
    dialog_manager.append_message(user_id, "assistant", reply_text)

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

