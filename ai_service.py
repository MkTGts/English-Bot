import asyncio
from functools import partial
from typing import List, Dict, Any

import google.generativeai as genai

from config import settings


genai.configure(api_key=settings.gemini_api_key)
_model = genai.GenerativeModel("gemini-2.5-flash")


def _build_prompt(messages: List[Dict[str, Any]]) -> str:
    """
    Build a single text prompt for Gemini based on:
    - system prompt (first message with role == "system");
    - previous dialog history;
    - last user message as a new message.
    """
    if not messages:
        raise ValueError("Messages list cannot be empty.")

    # Extract system prompt if present as the first message.
    system_text = ""
    first = messages[0]
    if first.get("role") == "system":
        system_text = str(first.get("content", "")).strip()
        dialog_messages = messages[1:]
    else:
        dialog_messages = messages

    # Determine the last user message (new message from user).
    last_user_index = -1
    for idx, msg in enumerate(dialog_messages):
        if msg.get("role") == "user":
            last_user_index = idx
    if last_user_index == -1:
        raise ValueError("At least one user message is required in messages.")

    new_user_message = str(dialog_messages[last_user_index].get("content", "")).strip()
    history_messages = dialog_messages[:last_user_index]

    lines: List[str] = []
    lines.append("You are a friendly English tutor.")

    if system_text:
        lines.append("")
        lines.append("System instructions:")
        lines.append(system_text)

    lines.append("")
    lines.append("Conversation history:")

    has_history = False
    for msg in history_messages:
        role = msg.get("role")
        content = str(msg.get("content", "")).strip()
        if not content:
            continue
        if role == "user":
            prefix = "User"
        elif role == "assistant":
            prefix = "Assistant"
        else:
            continue
        lines.append(f"{prefix}: {content}")
        has_history = True

    if not has_history:
        lines.append("(no previous messages)")

    lines.append("")
    lines.append("New message from user:")
    lines.append(new_user_message)
    lines.append("")
    lines.append("Reply in English and then show corrections.")

    return "\n".join(lines)


def _call_gemini(messages: List[Dict[str, Any]]) -> str:
    """
    Synchronous call to Google Gemini API using a single text prompt.
    Returns the model reply as a plain string.
    """
    prompt = _build_prompt(messages)
    try:
        response = _model.generate_content(
            prompt,
            generation_config={
                "max_output_tokens": 200,  # ~150–200 tokens
                "temperature": 0.8,
            },
        )
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Gemini API error: {exc}") from exc

    text = getattr(response, "text", "") or ""
    return text


async def generate_response(messages: List[Dict[str, Any]]) -> str:
    """
    Generate a reply from the English tutor model via Google Gemini.

    `messages` must already include the system prompt and dialog context, for example:
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "..."},
            {"role": "user", "content": "last user message"},
        ]
    """
    loop = asyncio.get_running_loop()
    result: str = await loop.run_in_executor(None, partial(_call_gemini, messages))
    return result.strip()

