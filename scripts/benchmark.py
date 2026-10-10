"""Замер времени по этапам пайплайна:
input → preprocessing → rules → LLM → postprocessing → result

Запуск (нужен ключ API):
    python scripts/benchmark.py --runs 3 --pause 2 --label before
    python scripts/benchmark.py --runs 3 --pause 2 --label after --cache

В режиме --cache вызов модели идёт через кэш ответов. Первый прогон каждого
случая — промах (miss), остальные — попадания (hit). Они считаются ОТДЕЛЬНО:
общая медиана при --runs 3 была бы искусственно хорошей (2 из 3 — повторы).
Результат: таблица в консоли + docs/evaluation/perf-<label>.json
"""

from __future__ import annotations

import argparse
import json
import statistics as st
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from colorist.api import explainer, llm  # noqa: E402
from colorist.cases import CASES_DIR, load_case  # noqa: E402
from colorist.rules import OutOfScopeError, calculate_formula  # noqa: E402

STAGES = ["input", "preprocessing", "rules", "llm", "postprocessing"]


def run_once(path: Path, cached: bool) -> dict | None:
    clock = time.perf_counter
    t: dict = {"_foreign_numbers": 0, "_hit": False}

    s = clock()
    case = load_case(path)                       # input: чтение и разбор карточки
    t["input"] = clock() - s

    s = clock()
    try:
        formula = calculate_formula(case.hair, case.target)   # rules
    except OutOfScopeError:
        return None                              # отказ по правилам — LLM не вызывается
    t["rules"] = clock() - s

    s = clock()
    prompt = explainer.build_prompt(formula)     # preprocessing
    t["preprocessing"] = clock() - s

    s = clock()
    if cached:                                   # model/API через кэш (проверка цифр внутри)
        hits_before = explainer._ask_cached.cache_info().hits
        try:
            answer = explainer._ask_cached(llm.model_name(), explainer.LLM_SYSTEM_PROMPT, prompt)
        except ValueError:
            answer = ""
            t["_foreign_numbers"] = 1
        t["_hit"] = explainer._ask_cached.cache_info().hits > hits_before
    else:                                        # model/API напрямую
        answer = llm.complete(explainer.LLM_SYSTEM_PROMPT, prompt)
    t["llm"] = clock() - s

    s = clock()
    if not cached:                               # postprocessing: проверка цифр в ответе
        t["_foreign_numbers"] = len(explainer.find_foreign_numbers(prompt, answer))
    t["postprocessing"] = clock() - s
    t["_answer_chars"] = len(answer)
    return t


def summarize(rows: list[dict]) -> dict:
    out = {k: st.median(r[k] for r in rows) for k in STAGES}
    out["total"] = st.median(sum(r[k] for k in STAGES) for r in rows)
    return out


def print_table(title: str, rows: list[dict]) -> dict:
    summ = summarize(rows)
    totals = sorted(sum(r[k] for k in STAGES) for r in rows)
    print(f"\n{title} — замеров: {len(rows)}, медиана, сек\n")
    print(f"{'этап':16s}{'сек':>9s}{'доля':>8s}")
    for k in STAGES:
        print(f"{k:16s}{summ[k]:9.4f}{summ[k] / summ['total']:8.1%}")
    print(f"{'ИТОГО':16s}{summ['total']:9.4f}   (p95: {totals[max(int(len(totals) * 0.95) - 1, 0)]:.3f})")
    return summ


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--label", default="before")
    ap.add_argument("--pause", type=float, default=0, help="пауза между вызовами, сек (вне замера)")
    ap.add_argument("--cache", action="store_true", help="вызывать модель через кэш ответов")
    args = ap.parse_args()

    print(f"Провайдер: {llm.provider()}, модель: {llm.model_name()}, кэш: {'вкл' if args.cache else 'выкл'}")
    rows, per_case = [], {}
    for path in sorted(CASES_DIR.glob("*.json")):
        runs = []
        for _ in range(args.runs):
            r = run_once(path, args.cache)
            if r:
                runs.append(r)
                if not r["_hit"]:                # пауза нужна только после реального вызова
                    time.sleep(args.pause)
        if not runs:
            print(f"{path.stem}: отказ по правилам, LLM не вызывается")
            continue
        rows += runs
        per_case[path.stem] = round(st.median(sum(r[k] for k in STAGES) for r in runs), 4)

    result: dict = {"provider": llm.provider(), "model": llm.model_name(),
                    "cache": args.cache, "runs": len(rows)}
    if args.cache:
        miss = [r for r in rows if not r["_hit"]]
        hit = [r for r in rows if r["_hit"]]
        result["miss"] = {k: round(v, 4) for k, v in print_table("ПРОМАХ КЭША (miss)", miss).items()}
        if hit:
            result["hit"] = {k: round(v, 4) for k, v in print_table("ПОПАДАНИЕ (hit)", hit).items()}
            m, h = result["miss"]["total"], result["hit"]["total"]
            print("\nПрогноз (расчёт, НЕ замер) при разной доле повторных запросов:")
            for share in (0.3, 0.5, 0.8):
                print(f"  {share:>4.0%} повторов → {m * (1 - share) + h * share:.3f} сек в среднем")
    else:
        result["median_sec"] = {k: round(v, 4) for k, v in print_table("БЕЗ КЭША", rows).items()}

    print(f"\nИскажённых цифр в ответах: {sum(r['_foreign_numbers'] for r in rows)}")
    answers = [r["_answer_chars"] for r in rows if r["_answer_chars"]]
    if answers:
        print(f"Длина ответа модели: медиана {int(st.median(answers))} символов")
    result["median_total_per_case"] = per_case

    out = ROOT / "docs" / "evaluation" / f"perf-{args.label}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Сохранено: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()