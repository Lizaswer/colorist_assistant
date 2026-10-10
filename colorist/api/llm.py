"""Тонкий клиент языковой модели на стандартной библиотеке (без новых зависимостей).

Провайдер выбирается по переменным окружения:
  ANTHROPIC_API_KEY  -> Anthropic Messages API
  OPENAI_API_KEY     -> OpenAI-совместимый Chat Completions API
Необязательно:
  COLORIST_LLM_MODEL     -- название модели
  COLORIST_LLM_BASE_URL  -- другой адрес API (прокси, локальный mock для тестов)
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

DEFAULTS = {
    "anthropic": ("https://api.anthropic.com", "claude-haiku-5-5"),
    "openai": ("https://api.openai.com", "gpt-4o-mini"),
}


class LLMNotConfigured(RuntimeError):
    pass


class LLMError(RuntimeError):
    """Ошибка API с текстом, который вернул провайдер."""


def provider() -> str:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    raise LLMNotConfigured("Задайте ANTHROPIC_API_KEY или OPENAI_API_KEY")


def model_name() -> str:
    return os.environ.get("COLORIST_LLM_MODEL") or DEFAULTS[provider()][1]


def complete(system: str, user: str, max_tokens: int = 600, timeout: float = 60) -> str:
    """Один запрос к модели. Возвращает текст ответа."""
    prov = provider()
    base = os.environ.get("COLORIST_LLM_BASE_URL") or DEFAULTS[prov][0]
    model = model_name()

    if prov == "anthropic":
        url = f"{base}/v1/messages"
        headers = {
            "x-api-key": os.environ["ANTHROPIC_API_KEY"],
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        body = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
    else:
        url = f"{base}/v1/chat/completions"
        headers = {
            "authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
            "content-type": "application/json",
        }
        body = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }

    request = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise LLMError(f"HTTP {exc.code} от {prov}: {detail}") from None

    if prov == "anthropic":
        return "".join(b.get("text", "") for b in data["content"])
    return data["choices"][0]["message"]["content"]