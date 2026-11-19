"""Проверка универсальной функции Wella: python demo_wella.py"""

import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from colorist.api.explainer import explain
from colorist.brands import (
    WELLA_KOLESTON_PERFECT,
    WELLA_ILLUMINA,
    WELLA_COLOR_TOUCH,
    calculate_wella_formula,
)
from colorist.rules import Direction, HairState, Target

hair = HairState(root_level=7, length_level=7, grey_percent=30, has_keratin=True)
target = Target(level=7, direction=Direction.COOL)

for line in (WELLA_KOLESTON_PERFECT, WELLA_ILLUMINA, WELLA_COLOR_TOUCH):
    print(f"\n=== {line.name} ===")
    formula = calculate_wella_formula(hair, target, line)
    for c in formula.components:
        print(f"  {c.shade}: {c.grams} г")
    print(f"  Оксид {formula.oxide_percent}%, {formula.mix_ratio}, {formula.time_min} мин")
    print(explain(formula))

print("\n=== Koleston с затемнением 7->5, без седины ===")
hair2 = HairState(root_level=7, length_level=7, grey_percent=0, has_keratin=False)
target2 = Target(level=5, direction=Direction.WARM)
formula2 = calculate_wella_formula(hair2, target2, WELLA_KOLESTON_PERFECT)
for c in formula2.components:
    print(f"  {c.shade}: {c.grams} г")
print(f"  Оксид {formula2.oxide_percent}%, {formula2.mix_ratio}, {formula2.time_min} мин")
