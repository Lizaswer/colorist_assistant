"""Pipeline benchmark for the AI-assistant request.

Reproduces the scenario from docs/evaluation/benchmark-results.md: the same
question of a master is asked three times and every stage is timed:

    input -> preprocessing -> model/API -> postprocessing -> result

With OPENAI_API_KEY set the first round is a real API call and the next two
should be served from the cache. Without a key the assistant answers in demo
mode, which is useful only for checking that the script runs.

Usage:  python scripts/benchmark.py [--rounds N] [--no-cache]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from colorist.api import assistant
from colorist.api.main import AssistantIn

STAGES = ("input", "preprocessing", "model/API", "postprocessing", "result")

PAYLOAD = {
    "messages": [{"role": "user", "content": "Почему в этой формуле выбран 6% оксид и натуральная база?"}],
    "context": {
        "исходные_данные": {"root_level": 7, "length_level": 7, "grey_percent": 30, "has_keratin": False},
        "цель": {"level": 7, "direction": "cool"},
        "рассчитанная_формула": [{"shade": "7/0", "grams": 30}, {"shade": "7/1", "grams": 70}],
        "оксид": 6,
        "соотношение": "1:1",
        "выдержка_мин": 35,
    },
}


def run_round() -> tuple[dict[str, float], str]:
    timings: dict[str, float] = {}

    t = time.perf_counter()
    parsed = AssistantIn.model_validate(PAYLOAD)
    timings["input"] = time.perf_counter() - t

    t = time.perf_counter()
    messages = [m.model_dump() for m in parsed.messages]
    instructions = assistant.SYSTEM_PROMPT + assistant._context_block(parsed.context)
    input_items = assistant.build_input(messages)
    timings["preprocessing"] = time.perf_counter() - t

    t = time.perf_counter()
    result = assistant.reply(messages, parsed.context)
    timings["model/API"] = time.perf_counter() - t

    t = time.perf_counter()
    body = {"answer": result.answer, "cached": result.cached, "demo": result.demo}
    timings["postprocessing"] = time.perf_counter() - t

    t = time.perf_counter()
    json.dumps(body, ensure_ascii=False)
    timings["result"] = time.perf_counter() - t

    del instructions, input_items  # built only to time the preprocessing stage honestly
    source = "DEMO" if result.demo else ("CACHE HIT" if result.cached else "API call")
    return timings, source


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--no-cache", action="store_true", help="clear the cache before every round (baseline)")
    args = parser.parse_args()

    mode = "OpenAI API" if os.getenv("OPENAI_API_KEY", "").strip() else "demo mode (no OPENAI_API_KEY)"
    print("Colorist Assistant pipeline benchmark")
    print(f"Mode: {mode}; cache: {'disabled' if args.no_cache else 'enabled'}; rounds: {args.rounds}")
    print()

    header = f"{'Round':5s} {'Result':10s} " + " ".join(f"{s:>15s}" for s in STAGES) + f" {'Total':>12s}"
    print(header)
    print("-" * len(header))

    assistant.clear_cache()
    totals = {s: 0.0 for s in STAGES}
    for i in range(1, args.rounds + 1):
        if args.no_cache:
            assistant.clear_cache()
        try:
            timings, source = run_round()
        except RuntimeError as exc:
            print(f"{i:<5d} ERROR      {exc}")
            print()
            print("The assistant could not reach the model; fix the cause above and rerun.")
            return
        for s in STAGES:
            totals[s] += timings[s]
        total = sum(timings.values())
        print(f"{i:<5d} {source:10s} " + " ".join(f"{timings[s]:>13.6f} s" for s in STAGES) + f" {total:>10.4f} s")

    print()
    print("Average per round:")
    for s in STAGES:
        print(f"  {s:16s} {totals[s] / args.rounds:10.4f} s")
    print(f"  {'pipeline':16s} {sum(totals.values()) / args.rounds:10.4f} s")

    bottleneck = max(STAGES, key=lambda s: totals[s])
    print()
    print(f"Bottleneck: {bottleneck}")


if __name__ == "__main__":
    main()
