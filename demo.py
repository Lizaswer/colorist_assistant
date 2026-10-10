"""Быстрая проверка модуля правил без API: python demo.py"""

import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from colorist.api.explainer import explain
from colorist.rules import (
    Component,
    Direction,
    HairState,
    MasterFormula,
    Target,
    calculate_formula,
    check_formula,
)

hair = HairState(root_level=7, length_level=7, grey_percent=30, has_keratin=True)
target = Target(level=7, direction=Direction.COOL)

print("=== Расчёт формулы ===")
formula = calculate_formula(hair, target)
for c in formula.components:
    print(f"  {c.shade}: {c.grams} г")
print(f"  Оксид {formula.oxide_percent}%, {formula.mix_ratio}, {formula.time_min} мин\n")
print(explain(formula))

print("\n=== Проверка формулы мастера: 7/3 60 г на 3% ===")
master = MasterFormula([Component("7/3", 60)], oxide_percent=3.0)
for risk in check_formula(hair, target, master):
    print(f"  ⚠ [{risk.rule_id}] {risk.text}")
