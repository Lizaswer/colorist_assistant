"""Explainable, deliberately small MVP knowledge base.

The rules are implementation assumptions for the synthetic MVP cases. They are
not a substitute for a manufacturer's technical chart or a professional
colorist's judgement.
"""

from __future__ import annotations

from .models import Direction

RULES = {
    "R-LEVEL": "Работаем только в диапазоне MVP: тон в тон или затемнение максимум на 2 уровня.",
    "R-GREY": "При седине от 20% добавляется натуральная база для поддержки покрытия.",
    "R-GREY-HIGH": "При седине от 50% натуральная база становится основной частью смеси.",
    "R-DIRECTION": "Для холодной цели используется холодный нюанс /1, для тёплой /3, для нейтральной /0.",
    "R-OXIDE-SAME": "Для тон-в-тон и затемнения в MVP используется 3% оксид.",
    "R-OXIDE-GREY": "При седине от 20% для надёжности покрытия используется 6% оксид.",
    "R-RATIO": "Базовое соотношение смеси MVP — 1:1.",
    "R-TIME": "Базовое время выдержки MVP — 35 минут.",
    "R-KERATIN": "После кератиновой процедуры волосы могут быть более резистентными; нужен контроль пряди и производителя.",
    "W-LINE": "Параметры оксида, соотношения и времени выдержки взяты из профиля выбранной линии краски.",
    "R-ZONE-ROOT": "Корни и длина отличаются по уровню, поэтому формула считается раздельно для каждой зоны.",
    "R-ZONE-ALL": "Корни и длина одного уровня — считается единая формула на всю голову.",
    "R-DEEP-GREY-LEVEL": "При седине от 50% оттенок для корней берётся на уровень глубже цели: седой волос не даёт плотности, и запас уровня компенсирует прозрачность.",
    "R-WARM-MIX": "Для тёплого направления при высокой седине целевой оттенок смешивается 1:1 с более глубоким тёплым тоном для плотности.",
    "R-LIFT-OXIDE": "Оксид для корней выбирается по количеству тонов осветления и целевому уровню: осветление в блонды требует более сильного оксида.",
    "R-GREY-OXIDE": "Без осветления в блонды оксид выбирается по проценту седины.",
    "R-LENGTH-REFRESH": "Длина отличается от цели не более чем на уровень — состав освежается на своём уровне низкопроцентным оксидом, без затемнения.",
    "R-LENGTH-DEPOSIT": "Длина заметно светлее цели — на неё кладётся целевой оттенок на низкопроцентном оксиде.",
    "R-LENGTH-OXIDE": "Для длины используется низкопроцентный оксид: длина уже окрашена и пориста, ей нужна только депозиция тона.",
    "R-CORRECTOR": "Для холодного направления добавляется корректор, чтобы удержать нюанс и нейтрализовать фон осветления.",
    "R-CORRECTOR-NONE": "Для тёплого направления корректор не добавляется: тёплый нюанс не требует нейтрализации.",
    "R-GRAMS": "Масса оксида считается из соотношения линии; граммы краски задаёт мастер по длине и густоте волос.",
    "C-COVERAGE": "Натуральная база нужна для покрытия седины.",
    "C-DIRECTION": "Формула должна соответствовать направлению целевого оттенка.",
    "C-OXIDE": "Процент оксида должен соответствовать задаче и условиям покрытия седины.",
    "C-LEVEL": "Уровни оттенков в формуле должны совпадать с целью и оставаться в рамках MVP: без осветления, затемнение максимум на 2 уровня от исходного.",
    "C-KERATIN": "Для волос после кератиновой процедуры требуется дополнительная осторожность и тест пряди.",
    "C-SHADE": "Оттенок должен входить в палитру выбранной линии краски.",
}


MAX_DARKENING_LEVELS = 2

# R-DIRECTION / C-DIRECTION: which nuance code expresses each target direction.
DIRECTION_TONE: dict[Direction, str] = {
    Direction.NEUTRAL: "0",
    Direction.WARM: "3",
    Direction.COOL: "1",
}
NATURAL_TONE = DIRECTION_TONE[Direction.NEUTRAL]


def shade(level: int, direction: Direction) -> str:
    """Shade code in the MVP brand notation, e.g. 7/1 for a cool level 7."""
    return f"{level}/{DIRECTION_TONE[direction]}"


def level_change_issue(
    base_level: int,
    target_level: int,
    max_darkening_levels: int = MAX_DARKENING_LEVELS,
) -> str | None:
    """Return why the level change is outside the supported scope, or None if allowed.

    Shared by the calculator (to reject the request) and the checker
    (to flag a master's formula) so both apply the same boundary.
    """
    change = target_level - base_level
    if change > 0:
        return "Осветление не входит в MVP: выберите цель на текущем уровне или ниже."
    if change < -max_darkening_levels:
        return f"Затемнение более чем на {max_darkening_levels} уровня не входит в MVP."
    return None


def rule_exists(rule_id: str) -> bool:
    return rule_id in RULES
