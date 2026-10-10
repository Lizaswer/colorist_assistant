"""Объяснение формулы человеческим языком.

Главный принцип проекта: LLM получает ГОТОВУЮ формулу и шаги с ID правил
и только пересказывает их. Цифры она не придумывает и не меняет.

Режимы:
  - по умолчанию — шаблон из шагов модуля правил (быстро, без сети);
  - COLORIST_USE_LLM=1 и задан ключ API — пересказ языковой моделью.
    Если модель недоступна или исказила цифры, возвращается шаблон.

Ответы модели кэшируются (отключить: COLORIST_LLM_CACHE=0).
Работа разбита на этапы (build_prompt → llm.complete → find_foreign_numbers),
чтобы каждый можно было измерить отдельно: см. scripts/benchmark.py.
"""

from __future__ import annotations

import os
import re
from functools import lru_cache

from colorist.rules import Formula

LLM_SYSTEM_PROMPT = """\
Ты помощник колориста. Тебе дают готовую формулу окрашивания и шаги расчёта
с ID правил. Объясни мастеру простыми словами, почему выбраны эти оттенки,
оксид и время. Не меняй и не добавляй цифры. Ссылайся на ID правил в скобках.
"""


def explain_template(formula: Formula) -> str:
    lines = ["Как получена формула:"]
    lines += [f"- {step.text} [{step.rule_id}]" for step in formula.steps]
    if formula.warnings:
        lines.append("Обратите внимание:")
        lines += [f"- {w.text} [{w.rule_id}]" for w in formula.warnings]
    return "\n".join(lines)


def build_prompt(formula: Formula) -> str:
    """Этап preprocessing: формула → текст запроса к модели."""
    parts = ["Формула:"]
    parts += [f"- {c.shade}: {c.grams} г" for c in formula.components]
    parts.append(
        f"- оксид {formula.oxide_percent}%, пропорция {formula.mix_ratio}, "
        f"выдержка {formula.time_min} мин"
    )
    parts.append("\nШаги расчёта:")
    parts += [f"- {s.text} [{s.rule_id}]" for s in formula.steps]
    if formula.warnings:
        parts.append("\nПредупреждения:")
        parts += [f"- {w.text} [{w.rule_id}]" for w in formula.warnings]
    return "\n".join(parts)


_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
_LIST_MARKER = re.compile(r"^\s*\d+[.)]\s", re.MULTILINE)


def _numbers(text: str) -> set[str]:
    return {n.replace(",", ".") for n in _NUMBER.findall(text)}


def find_foreign_numbers(prompt: str, answer: str) -> set[str]:
    """Этап postprocessing: числа в ответе модели, которых не было в запросе.

    Нумерацию списка («1. ...») не считаем. Пустое множество — цифры не искажены.
    """
    return _numbers(_LIST_MARKER.sub("", answer)) - _numbers(prompt)


def _ask(model: str, system: str, prompt: str) -> str:
    """Один вызов модели с проверкой цифр. Искажённый ответ — ошибка."""
    from . import llm

    answer = llm.complete(system, prompt)
    if find_foreign_numbers(prompt, answer):
        raise ValueError("Модель изменила или добавила цифры")
    return answer


# Кэш: одинаковая формула → одинаковый запрос → тот же пересказ (правила детерминированы).
# lru_cache не запоминает исключения, поэтому в кэш попадают только проверенные ответы;
# откат на шаблон тоже не кэшируется. Ключ включает модель и системный промпт.
# Кэш живёт в памяти одного процесса и сбрасывается при перезапуске.
_ask_cached = lru_cache(maxsize=256)(_ask)


def explain_llm(formula: Formula) -> str:
    from . import llm

    prompt = build_prompt(formula)
    ask = _ask if os.environ.get("COLORIST_LLM_CACHE") == "0" else _ask_cached
    return ask(llm.model_name(), LLM_SYSTEM_PROMPT, prompt)


def explain(formula: Formula) -> str:
    if os.environ.get("COLORIST_USE_LLM") == "1":
        try:
            return explain_llm(formula)
        except Exception:
            pass  # любая проблема с моделью — безопасный откат на шаблон
    return explain_template(formula)