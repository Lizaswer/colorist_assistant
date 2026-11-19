from __future__ import annotations

import json
import os
from collections import OrderedDict
from dataclasses import dataclass
from threading import Lock
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional when package is used without extras
    load_dotenv = None

if load_dotenv:
    load_dotenv()

DEFAULT_MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = """
Ты — ИИ-ассистент профессионального колориста.

Твоя роль — помогать мастеру понимать ситуацию, объяснять расчёты, разбирать варианты,
формулировать вопросы к клиенту и напоминать о проверках перед окрашиванием.

ВАЖНЫЕ ОГРАНИЧЕНИЯ:
1. Не выдавай себя за замену мастеру.
2. Не придумывай формулу окрашивания и не меняй формулу, которую рассчитал движок правил.
3. Когда в контексте есть рассчитанная формула, воспринимай её как результат rule-based калькулятора.
   Можно объяснить, почему она получилась такой, но для изменения параметров попроси мастера
   заново выполнить расчёт через калькулятор.
4. Чётко отделяй известные данные от предположений. Если данных не хватает — задай уточняющий вопрос.
5. Не утверждай медицинские или гарантированные результаты. Для процедур, аллергии и состояния волос
   напоминай о необходимости следовать инструкции конкретного бренда и профессиональной практике.
6. Отвечай по-русски, дружелюбно, профессионально и понятно.
7. Не используй технический JSON или внутренние структуры API в ответе мастеру.
""".strip()


def _format_formula(context: dict[str, Any] | None) -> str:
    """Human-readable summary of the calculator result stored in the chat context."""
    if not context:
        return ""
    components = context.get("рассчитанная_формула") or []
    parts = [
        f"{c.get('shade')} — {c.get('grams'):g} г"
        for c in components
        if isinstance(c, dict) and c.get("shade") is not None and c.get("grams") is not None
    ]
    if not parts:
        return ""
    details = [", ".join(parts)]
    if context.get("оксид") is not None:
        details.append(f"оксид {context['оксид']:g}%")
    if context.get("соотношение"):
        details.append(f"соотношение {context['соотношение']}")
    if context.get("выдержка_мин") is not None:
        details.append(f"выдержка {context['выдержка_мин']} мин")
    return "; ".join(details)


def _demo_reply(question: str, context: dict[str, Any] | None) -> str:
    """Rule-of-thumb answer used when no LLM is available.

    It only restates what the rule-based calculator produced and gives short
    general hints by topic; it never proposes a formula of its own.
    """
    q = question.lower()
    lines: list[str] = []

    formula = _format_formula(context)
    if formula:
        lines.append(f"Текущий расчёт калькулятора: {formula}.")

    if "седин" in q or "натуральн" in q or "/0" in q:
        lines.append(
            "Натуральная база /0 нужна для покрытия седины: седой волос не имеет собственного "
            "пигмента, и чистый нюанс (например, /1 или /3) на нём ложится прозрачно и неровно. "
            "В правилах калькулятора база добавляется от 20% седины, а от 50% становится основной частью смеси."
        )
    if "оксид" in q or "окислител" in q or "%" in q:
        lines.append(
            "Процент оксида в расчёте зависит от задачи: для тон-в-тон и затемнения используется 3%, "
            "при седине от 20% — 6% для более надёжного покрытия."
        )
    if "время" in q or "выдерж" in q or "минут" in q:
        lines.append("Время выдержки в MVP фиксированное — 35 минут; сверяйтесь с инструкцией бренда.")
    if "кератин" in q:
        lines.append(
            "После кератиновой процедуры волосы могут быть более резистентными: обязательно сделайте "
            "контроль пряди и проверьте рекомендации производителя."
        )
    if "направлен" in q or "холодн" in q or "тёпл" in q or "тепл" in q or "нюанс" in q:
        lines.append(
            "Направление цели задаёт нюанс: холодная — /1, тёплая — /3, нейтральная — /0. "
            "Чтобы изменить направление, пересчитайте формулу через калькулятор."
        )

    if len(lines) <= (1 if formula else 0):
        lines.append(
            "Я могу объяснить, почему калькулятор выбрал базу, нюанс, оксид или время, "
            "и напомнить о проверках перед окрашиванием. Саму формулу я не меняю — "
            "для этого выполните новый расчёт."
        )
    lines.append("Перед процедурой обязателен тест на аллергию и контроль пряди.")
    return "\n\n".join(lines)


def _last_user_question(messages: list[dict[str, str]]) -> str:
    for msg in reversed(messages):
        if msg.get("role") == "user" and msg.get("content", "").strip():
            return msg["content"].strip()
    return ""


def _fallback_without_key(
    messages: list[dict[str, str]] | None = None,
    context: dict[str, Any] | None = None,
) -> str:
    notice = (
        "ИИ-ассистент работает в демонстрационном режиме: OPENAI_API_KEY пока не подключён. "
        "Добавьте ключ в файл .env, чтобы ответы начали поступать от внешней модели. "
        "Калькулятор правил при этом работает отдельно и полностью."
    )
    question = _last_user_question(messages or [])
    if not question and not context:
        return notice
    return notice + "\n\n" + _demo_reply(question, context)


def _context_block(context: dict[str, Any] | None) -> str:
    if not context:
        return ""
    return (
        "\n\nКОНТЕКСТ ТЕКУЩЕЙ РАБОТЫ (используй только для объяснения, не пересчитывай сам):\n"
        f"{context}\n"
    )


def build_input(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    """Keep only the latest conversation messages supported by the UI contract."""
    input_items: list[dict[str, str]] = []
    for msg in messages[-20:]:
        role = msg.get("role")
        content = msg.get("content", "").strip()
        if role in {"user", "assistant"} and content:
            input_items.append({"role": role, "content": content})
    if not input_items:
        input_items.append(
            {"role": "user", "content": "Представься и предложи помощь мастеру."}
        )
    return input_items


def _call_model(api_key: str, model: str, instructions: str, input_items: list[dict[str, str]]) -> str:
    """Single network round-trip to the OpenAI Responses API. Patched in tests and benchmarks."""
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            'Пакет openai не установлен. Выполните: pip install -e ".[dev]"'
        ) from exc

    # OPENAI_BASE_URL lets the app talk to any OpenAI-compatible gateway
    # (proxy, OpenRouter, a local model) when api.openai.com is unreachable.
    base_url = os.getenv("OPENAI_BASE_URL", "").strip() or None
    client = OpenAI(api_key=api_key, base_url=base_url)
    try:
        response = client.responses.create(model=model, instructions=instructions, input=input_items)
    except Exception as exc:
        # Explain the cause to the master, but never leak the key or raw payloads.
        raise RuntimeError(_describe_api_error(exc, model)) from exc
    return (response.output_text or "").strip()


def _describe_api_error(exc: Exception, model: str) -> str:
    status = getattr(exc, "status_code", None)
    code = getattr(exc, "code", None)
    if code == "unsupported_country_region_territory":
        return (
            "OpenAI не обслуживает запросы из вашего региона (403). Используйте VPN/прокси "
            "или OpenAI-совместимый шлюз, указав его адрес в OPENAI_BASE_URL."
        )
    if code == "expired_secret_key":
        return "Срок действия API-ключа истёк (401). Создайте новый ключ в панели OpenAI и обновите OPENAI_API_KEY в .env."
    if status == 401:
        return "OpenAI не принял API-ключ (401). Проверьте OPENAI_API_KEY в файле .env."
    if status == 404 or code == "model_not_found":
        return f"Модель «{model}» не найдена (404). Проверьте OPENAI_MODEL в файле .env."
    if status == 429:
        return "Превышен лимит запросов или исчерпан баланс OpenAI (429). Попробуйте позже."
    if status is None:
        return "Нет соединения с сервером ИИ. Проверьте интернет и OPENAI_BASE_URL, если он задан."
    return f"Внешний ИИ сейчас недоступен (ошибка {status}). Попробуйте позже."


# --- Response cache -----------------------------------------------------------
# The external LLM call is the measured bottleneck of the pipeline
# (see docs/evaluation/optimization.md). Identical question + identical
# context -> identical prompt, so the reply is reused instead of a new call.

CACHE_MAX_SIZE = 256
_cache: OrderedDict[str, str] = OrderedDict()
_cache_lock = Lock()


def _cache_key(model: str, instructions: str, input_items: list[dict[str, str]]) -> str:
    payload = {"model": model, "instructions": instructions, "input": input_items}
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _cache_get(key: str) -> str | None:
    with _cache_lock:
        answer = _cache.get(key)
        if answer is not None:
            _cache.move_to_end(key)
        return answer


def _cache_put(key: str, answer: str) -> None:
    with _cache_lock:
        _cache[key] = answer
        _cache.move_to_end(key)
        while len(_cache) > CACHE_MAX_SIZE:
            _cache.popitem(last=False)


def clear_cache() -> None:
    with _cache_lock:
        _cache.clear()


@dataclass(frozen=True)
class ChatReply:
    answer: str
    cached: bool = False
    demo: bool = False


def reply(messages: list[dict[str, str]], context: dict[str, Any] | None = None) -> ChatReply:
    """Return an assistant reply plus where it came from (cache / API / demo mode).

    If no API key is configured, the app remains usable in demo mode.
    The calculator remains a separate source of truth for formulas.
    """
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return ChatReply(_fallback_without_key(messages, context), demo=True)

    model = os.getenv("OPENAI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    instructions = SYSTEM_PROMPT + _context_block(context)
    input_items = build_input(messages)

    key = _cache_key(model, instructions, input_items)
    cached = _cache_get(key)
    if cached is not None:
        return ChatReply(cached, cached=True)

    text = _call_model(api_key, model, instructions, input_items)
    if text:
        # Only successful answers are cached; errors and empty replies are retried next time.
        _cache_put(key, text)
    return ChatReply(text or "Не удалось получить текстовый ответ. Попробуйте ещё раз.")


def chat(messages: list[dict[str, str]], context: dict[str, Any] | None = None) -> str:
    """Convenience wrapper returning just the answer text."""
    return reply(messages, context).answer
