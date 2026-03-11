import asyncio
import logging
from typing import List, Dict, Any

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

from .config import settings
from .ai_service import generate_response
from .database import (
    create_user_if_not_exists,
    save_message,
    get_last_messages,
    clear_dialog,
)
from .prompts import SYSTEM_PROMPT


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


router = Router()


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
    clear_dialog(user_id)

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

    # 1–2. Ensure user exists in DB.
    create_user_if_not_exists(user_id)

    # 3. Save user's message.
    save_message(user_id, "user", user_text)

    # 4. Get last N messages for this user (context limited in DB).
    history = get_last_messages(user_id, limit=6)

    # 5. Build messages for OpenAI: system prompt + existing history.
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *history,
    ]

    await message.chat.action.typing()

    try:
        # 5–6. Get AI response based on last messages.
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

    # 7. Save assistant reply to DB.
    save_message(user_id, "assistant", reply_text)

    # 8. Send reply to user.
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


