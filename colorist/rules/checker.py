"""Проверка формулы, составленной мастером («второй взгляд»).

Система не пересчитывает формулу, а ищет в ней известные риски
и объясняет каждый со ссылкой на правило.
"""

from __future__ import annotations

from . import knowledge as kb
from .models import Direction, HairState, MasterFormula, Note, Porosity, Target


def check_formula(hair: HairState, target: Target, formula: MasterFormula) -> list[Note]:
    """Возвращает список рисков. Пустой список — рисков не найдено."""
    if not formula.components:
        raise ValueError("В формуле нет ни одного оттенка")

    parsed = [kb.parse_shade(c.shade) for c in formula.components]
    levels = {level for level, _ in parsed}
    nuances = [nuance for _, nuance in parsed]
    has_natural = any(n.startswith(kb.NUANCE_NATURAL) for n in nuances)
    has_ash = any(n.startswith(kb.NUANCE_ASH) for n in nuances)

    risks: list[Note] = []

    if any(abs(level - target.level) > 1 for level in levels):
        risks.append(Note(
            "C-LEVEL-MISMATCH",
            f"В формуле уровни {sorted(levels)}, а цель — {target.level}. "
            + kb.RULES["C-LEVEL-MISMATCH"],
        ))

    if hair.grey_percent >= kb.GREY_OXIDE_THRESHOLD:
        if formula.oxide_percent < kb.OXIDE_GREY:
            risks.append(Note(
                "C-OX-GREY",
                f"Седина {hair.grey_percent}%, оксид {formula.oxide_percent}%. "
                + kb.RULES["C-OX-GREY"],
            ))
        if not has_natural:
            risks.append(Note("C-GREY-NO-NATURAL", kb.RULES["C-GREY-NO-NATURAL"]))

    if (
        target.direction == Direction.COOL
        and target.level >= kb.WARM_BACKGROUND_FROM_LEVEL
        and not has_ash
    ):
        pigment = kb.UNDERLYING_PIGMENT[target.level]
        risks.append(Note(
            "C-WARM-NO-ASH",
            f"Фон на уровне {target.level} — {pigment}. " + kb.RULES["C-WARM-NO-ASH"],
        ))

    if has_ash and hair.porosity == Porosity.HIGH and hair.length_level >= 8:
        risks.append(Note("C-ASH-POROUS-LIGHT", kb.RULES["C-ASH-POROUS-LIGHT"]))

    if hair.has_henna:
        risks.append(Note("C-HENNA", kb.RULES["C-HENNA"]))

    return risks
