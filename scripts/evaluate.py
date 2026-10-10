"""Прогон всех эталонных случаев и отчёт для документации.

Запуск:  python scripts/evaluate.py
Результат: docs/evaluation/report.md (перезаписывается при каждом запуске).
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from colorist.cases import fmt, load_cases, run_case  # noqa: E402

REPORT = ROOT / "docs" / "evaluation" / "report.md"


def status(result) -> str:
    case = result.case
    ok = result.formula_matches is not False and result.risks_match is not False
    if case.expected_refusal and ok:
        return "✅ корректный отказ"
    if ok:
        return "✅ совпало"
    if case.known_gap:
        return "⚠️ известное ограничение"
    return "❌ ошибка"


def system_answer(result) -> str:
    if result.formula is None:
        return f"отказ: {result.error}"
    f = result.formula
    return f"{fmt(f.components)}, {f.oxide_percent}%, {f.time_min} мин"


def main() -> None:
    results = [run_case(case) for case in load_cases()]
    statuses = [status(r) for r in results]
    ok = sum(s.startswith("✅") for s in statuses)
    gaps = sum(s.startswith("⚠️") for s in statuses)
    errors = sum(s.startswith("❌") for s in statuses)
    verified = sum(r.case.verified for r in results)

    lines = [
        "# Отчёт о прогоне эталонных случаев",
        "",
        f"Дата: {date.today():%d.%m.%Y}. Случаев: {len(results)}, "
        f"из них подтверждено колористами: {verified}.",
        "",
        f"**Итог:** совпало {ok}, известные ограничения {gaps}, ошибки {errors}.",
        "",
    ]
    if verified == 0:
        lines += [
            "> Все случаи пока синтетические: эталон составлен по общим правилам,",
            "> а не колористом. Отчёт показывает, что сквозной сценарий работает и где",
            "> у системы границы, но не говорит о точности. Точность (цель — не менее 80%",
            "> формул «верно» или «допустимо») измеряется на реальных случаях слепой оценкой.",
            "",
        ]
    lines += [
        "| Случай | Ответ системы | Результат | Расхождения |",
        "| --- | --- | --- | --- |",
    ]
    for result, st in zip(results, statuses):
        diffs = "; ".join(result.differences) or "—"
        lines.append(f"| {result.case.id} | {system_answer(result)} | {st} | {diffs} |")

    gap_cases = [r.case for r in results if r.case.known_gap]
    if gap_cases:
        lines += ["", "## Известные ограничения", ""]
        lines += [f"- **{c.id}** — {c.known_gap}" for c in gap_cases]

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nОтчёт сохранён: {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
