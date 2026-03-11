import asyncio
from functools import partial
from typing import List, Dict, Any

from openai import OpenAI, OpenAIError

from .config import settings


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


async def generate_response(messages: List[Dict[str, Any]]) -> str:
    """
    Generate a reply from the English tutor model.

    `messages` must already include the system prompt and full dialog context, for example:
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "..."},
            {"role": "user", "content": "last user message"},
        ]
    """
    loop = asyncio.get_running_loop()
    try:
        result: str = await loop.run_in_executor(None, partial(_call_openai, messages))
        return result.strip()
    except OpenAIError as exc:
        # Reraise as a generic exception so the bot layer can decide how to handle it.
        raise RuntimeError(f"OpenAI API error: {exc}") from exc

