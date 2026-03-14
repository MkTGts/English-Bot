"""
Работа с Timeweb AI-агентом (OpenAI-совместимый API).
Модель и системный промпт задаются в панели Timeweb.
Документация: https://agent.timeweb.cloud/docs
"""
from typing import List, Dict, Any

import httpx

from config import settings


TIMEWEB_CHAT_URL = (
    "https://agent.timeweb.cloud/api/v1/cloud-ai/agents"
    "/{agent_id}/v1/chat/completions"
)

# Ограничение длины ответа (экономия токенов пакета). Рекомендуется 250–350.
MAX_COMPLETION_TOKENS = 320


async def generate_response(messages: List[Dict[str, Any]]) -> str:
    """
    Генерация ответа через Timeweb AI-агент (Chat Completions).
    Системный промпт настраивается в панели Timeweb (инструкции агента).
    messages — история диалога: [{"role": "user"|"assistant", "content": "..."}, ...].
    """
    url = TIMEWEB_CHAT_URL.format(agent_id=settings.timeweb_agent_id)
    headers = {
        "Authorization": f"Bearer {settings.timeweb_api_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messages": messages,
        "temperature": 0.8,
        "max_tokens": MAX_COMPLETION_TOKENS,
        "stream": False,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, json=payload, headers=headers)

    if response.status_code != 200:
        raise RuntimeError(
            f"Timeweb AI API error: {response.status_code} — {response.text}"
        )

    data = response.json()
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("Timeweb AI API: пустой ответ (нет choices).")

    message = choices[0].get("message") or {}
    text = (message.get("content") or "").strip()
    return text
