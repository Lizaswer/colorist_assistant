"""Расчёт формулы окрашивания.

Детерминированная функция: одни и те же входные данные всегда дают
одну и ту же формулу. Никакой языковой модели здесь нет.
"""

from __future__ import annotations

from . import knowledge as kb
from .models import (
    Component,
    Direction,
    Formula,
    HairState,
    Note,
    Porosity,
    Service,
    Target,
)


class OutOfScopeError(ValueError):
    """Случай вне рамок MVP (например, осветление)."""

    def __init__(self, rule_id: str, message: str):
        super().__init__(message)
        self.rule_id = rule_id


def validate(hair: HairState, target: Target) -> None:
    for name, value in [
        ("root_level", hair.root_level),
        ("length_level", hair.length_level),
        ("target.level", target.level),
    ]:
        if not 1 <= value <= 10:
            raise ValueError(f"{name} должен быть от 1 до 10, получено {value}")
    if not 0 <= hair.grey_percent <= 100:
        raise ValueError("grey_percent должен быть от 0 до 100")


def choose_service(hair: HairState, target: Target, steps: list[Note]) -> Service:
    diff = hair.root_level - target.level  # > 0 — затемнение, < 0 — осветление
    if diff < 0:
        raise OutOfScopeError("R-SCOPE-LIGHTEN", kb.RULES["R-SCOPE-LIGHTEN"])
    if diff > kb.MAX_LEVELS_DARKER:
        raise OutOfScopeError(
            "R-DARK-MAX",
            f"Затемнение на {diff} тона: {kb.RULES['R-DARK-MAX']}",
        )
    service = Service.TONE_ON_TONE if diff == 0 else Service.DARKER
    label = "тон в тон" if diff == 0 else f"затемнение на {diff} тон(а)"
    steps.append(Note("R-SERVICE", f"Корни {hair.root_level}, цель {target.level}: {label}."))
    return service


def choose_nuance(hair: HairState, target: Target, steps: list[Note]) -> str:
    pigment = kb.UNDERLYING_PIGMENT[target.level]
    steps.append(Note("R-PIGMENT", f"Фон осветления на уровне {target.level} — {pigment}."))

    if target.direction == Direction.COOL:
        if target.level >= kb.WARM_BACKGROUND_FROM_LEVEL:
            steps.append(Note(
                "R-NEUTRAL-COOL",
                f"Цель холодная, фон {pigment} — берём пепельный нюанс /{kb.NUANCE_ASH} "
                "для нейтрализации.",
            ))
        else:
            steps.append(Note("R-DIRECTION", f"Холодный результат — нюанс /{kb.NUANCE_ASH}."))
        return kb.NUANCE_ASH
    if target.direction == Direction.WARM:
        steps.append(Note("R-DIRECTION", f"Тёплый результат — нюанс /{kb.NUANCE_GOLD}."))
        return kb.NUANCE_GOLD
    steps.append(Note("R-DIRECTION", f"Натуральный результат — нюанс /{kb.NUANCE_NATURAL}."))
    return kb.NUANCE_NATURAL


def build_components(
    hair: HairState, target: Target, nuance: str, steps: list[Note]
) -> list[Component]:
    main_shade = f"{target.level}/{nuance}"
    natural_shade = f"{target.level}/{kb.NUANCE_NATURAL}"
    share = kb.grey_natural_share(hair.grey_percent)

    if share == 0 or nuance == kb.NUANCE_NATURAL:
        return [Component(main_shade, kb.DEFAULT_DYE_GRAMS)]

    natural_g = round(kb.DEFAULT_DYE_GRAMS * share)
    main_g = kb.DEFAULT_DYE_GRAMS - natural_g
    steps.append(Note(
        "R-GREY-NATURAL",
        f"Седина {hair.grey_percent}% — добавляем {natural_shade} "
        f"({natural_g} г из {kb.DEFAULT_DYE_GRAMS} г).",
    ))
    return [Component(main_shade, main_g), Component(natural_shade, natural_g)]


def choose_oxide(hair: HairState, service: Service, steps: list[Note]) -> float:
    if hair.grey_percent >= kb.GREY_OXIDE_THRESHOLD:
        steps.append(Note("R-OX-GREY", f"Седина {hair.grey_percent}% — оксид {kb.OXIDE_GREY}%."))
        return kb.OXIDE_GREY
    oxide = kb.OXIDE_TONE_ON_TONE if service == Service.TONE_ON_TONE else kb.OXIDE_DARKER
    steps.append(Note("R-OX-BASE", f"Без значимой седины — оксид {oxide}%."))
    return oxide


def choose_time(hair: HairState, steps: list[Note]) -> int:
    grey = hair.grey_percent >= kb.GREY_OXIDE_THRESHOLD
    minutes = kb.TIME_GREY_MIN if grey else kb.TIME_DEFAULT_MIN
    steps.append(Note("R-TIME", f"Время выдержки — {minutes} мин."))
    return minutes


def collect_warnings(hair: HairState) -> list[Note]:
    warnings: list[Note] = []
    if hair.has_henna:
        warnings.append(Note("R-WARN-HENNA", kb.RULES["R-WARN-HENNA"]))
    if hair.has_keratin:
        warnings.append(Note("R-WARN-KERATIN", kb.RULES["R-WARN-KERATIN"]))
    if hair.porosity == Porosity.HIGH:
        warnings.append(Note("R-WARN-POROSITY", kb.RULES["R-WARN-POROSITY"]))
    warnings.append(Note("R-SAFETY", kb.RULES["R-SAFETY"]))
    return warnings


def calculate_formula(hair: HairState, target: Target) -> Formula:
    """Главная функция: анкета → формула с объяснением."""
    validate(hair, target)
    steps: list[Note] = []
    service = choose_service(hair, target, steps)
    nuance = choose_nuance(hair, target, steps)
    components = build_components(hair, target, nuance, steps)
    oxide = choose_oxide(hair, service, steps)
    minutes = choose_time(hair, steps)
    return Formula(
        service=service,
        components=components,
        oxide_percent=oxide,
        mix_ratio=kb.DEFAULT_MIX_RATIO,
        time_min=minutes,
        steps=steps,
        warnings=collect_warnings(hair),
    )
