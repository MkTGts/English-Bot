import asyncio
from functools import partial
from typing import List, Dict, Any

from openai import OpenAI, OpenAIError

from .config import settings
from .prompts import SYSTEM_PROMPT


client = OpenAI(api_key=settings.openai_api_key)


def _call_openai(messages: List[Dict[str, Any]]) -> str:
    """
    Synchronous call to OpenAI Chat Completions API.
    Returns the assistant message content as a string.
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=150,
        temperature=0.8,
    )
    choice = response.choices[0]
    return choice.message.content or ""


async def generate_tutor_reply(user_history: List[Dict[str, str]]) -> str:
    """
    Generate a reply from the English tutor model.

    `user_history` is a list of messages like:
    [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
    Only the last few messages (context) should be passed in.
    """
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *user_history,
    ]

    loop = asyncio.get_running_loop()
    try:
        result: str = await loop.run_in_executor(None, partial(_call_openai, messages))
        return result.strip()
    except OpenAIError as exc:
        # Reraise as a generic exception so the bot layer can decide how to handle it.
        raise RuntimeError(f"OpenAI API error: {exc}") from exc

