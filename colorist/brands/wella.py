"""Wella brand profiles for the universal calculation engine.

Each Wella line is described by a :class:`BrandProfile`: the engine reads the
profile instead of hard-coding brand behaviour, so adding a line (or another
brand) means describing it here, not writing new calculation code.

Values are taken from public brand guidance for the MVP and still need to be
confirmed against the manufacturer's technical chart by a practising colorist.
"""

from __future__ import annotations

from typing import Mapping

from colorist.brands.base import BrandProfile, CorrectorRule
from colorist.brands.engine import calculate_formula, check_formula
from colorist.rules.errors import CalculationError
from colorist.rules.models import Direction, Formula, HairState, MasterFormula, Risk, Target

WELLA_TONES: Mapping[Direction, str] = {
    Direction.NEUTRAL: "0",
    Direction.COOL: "1",
    Direction.WARM: "3",
}

WELLA_NATURAL_TONE = "0"

# Wella Koleston Perfect / Illumina / Color Touch use a slash-based code,
# e.g. 7/1. Tone digits 0-9 cover the main families.
WELLA_TONE_CODES = tuple(str(d) for d in range(10))

#: Backwards-compatible alias for the earlier Wella-specific type.
WellaLine = BrandProfile


WELLA_KOLESTON_PERFECT = BrandProfile(
    key="koleston_perfect",
    name="Koleston Perfect",
    tones=WELLA_TONES,
    natural_tone=WELLA_NATURAL_TONE,
    mix_ratio="1:1",
    time_min=35,
    time_max=40,
    default_oxide=4.0,
    grey_oxide=6.0,
    high_grey_oxide=6.0,
    available_oxides=(3.0, 4.0, 6.0, 8.0, 9.0, 12.0),
    levels=tuple(range(1, 13)),
    tone_codes=WELLA_TONE_CODES,
    validate_catalog=True,
    max_darkening_levels=2,
    supports_lightening=True,
    max_lightening_levels=2,
    blonde_threshold=9,
    lightening_oxides={1: 6.0, 2: 8.0, 3: 9.0, 4: 12.0},
    length_oxide=3.0,
    length_refresh_tolerance=1,
    deep_grey_threshold=50,
    warm_base_tone="3",
    corrector_rules=(
        CorrectorRule(
            shade="0.25",
            cm=2,
            direction=Direction.COOL,
            tone="26",
            requires_lightening=True,
            note="Кейс 12: осветление корней 7→9 на 9.26 — корректор 0.25, 2 см.",
        ),
        CorrectorRule(
            shade="0.82",
            cm=3,
            direction=Direction.COOL,
            tone="1",
            requires_lightening=False,
            min_grey=50,
            note="Кейс 11: тон-в-тон 7.1 при седине 50% — корректор 0.82, 3 см.",
        ),
    ),
    shade_catalog={
        (6, "1"): "6.112",
        (8, "26"): "8.25",
    },
    info_steps=(
        ("W-LINE", "Линия Koleston Perfect: соотношение 1:1, оксиды 3/4/6/8/9/12%."),
    ),
    notes=(
        "Перманентная линия Wella. Соотношение 1:1. Оксиды: 3% и 4% — тон-в-тон и "
        "депозиция на длине, 6% — покрытие седины и осветление на 1–2 тона ниже "
        "блонда, 8% — осветление в блонды (уровень 9+), 9/12% — сильное осветление. "
        "Правила зон, корректоров и каталог оттенков выведены из кейсов колориста "
        "(data/cases/11..13) и требуют сверки с технической картой бренда."
    ),
)

WELLA_ILLUMINA = BrandProfile(
    key="illumina",
    name="Illumina Color",
    tones=WELLA_TONES,
    natural_tone=WELLA_NATURAL_TONE,
    mix_ratio="1:1",
    time_min=35,
    time_max=45,
    default_oxide=6.0,
    grey_oxide=6.0,
    high_grey_oxide=9.0,
    available_oxides=(6.0, 9.0, 12.0),
    levels=tuple(range(1, 11)),
    tone_codes=WELLA_TONE_CODES,
    validate_catalog=True,
    max_darkening_levels=2,
    supports_lightening=False,
    info_steps=(
        ("W-LINE", "Линия Illumina Color: соотношение 1:1, оксид 6% (9% при высокой седине)."),
    ),
    notes=(
        "Перманентная линия Wella с мягкой пигментацией. Соотношение 1:1, "
        "оксиды 6/9/12%, время выдержки 35–45 минут."
    ),
)

WELLA_COLOR_TOUCH = BrandProfile(
    key="color_touch",
    name="Color Touch",
    tones=WELLA_TONES,
    natural_tone=WELLA_NATURAL_TONE,
    mix_ratio="1:2",
    time_min=20,
    time_max=30,
    default_oxide=1.9,
    grey_oxide=4.0,
    high_grey_oxide=4.0,
    available_oxides=(1.9, 4.0),
    levels=tuple(range(1, 11)),
    tone_codes=WELLA_TONE_CODES,
    validate_catalog=True,
    max_darkening_levels=2,
    supports_lightening=False,
    info_steps=(
        ("W-LINE", "Линия Color Touch: соотношение 1:2, оксид 1.9% или 4%; полуперманент — седина не покрывается полностью."),
    ),
    notes=(
        "Полуперманентная (безаммиачная) линия Wella. Соотношение 1:2 с "
        "оксидами 1.9% или 4%, время выдержки 20–30 минут. Полного покрытия "
        "седины не даёт — только маскировку до 50%."
    ),
)

WELLA_LINES: dict[str, BrandProfile] = {
    line.key: line for line in (WELLA_KOLESTON_PERFECT, WELLA_ILLUMINA, WELLA_COLOR_TOUCH)
}

DEFAULT_WELLA_LINE = WELLA_KOLESTON_PERFECT.key


def resolve_wella_line(line: BrandProfile | str | None = None) -> BrandProfile:
    """Return the requested Wella line profile, by key or instance."""
    if line is None:
        return WELLA_LINES[DEFAULT_WELLA_LINE]
    if isinstance(line, BrandProfile):
        return line
    try:
        return WELLA_LINES[str(line).strip().lower()]
    except KeyError:
        raise CalculationError(
            "Неизвестная линия Wella: "
            f"{line}. Доступные: {', '.join(WELLA_LINES)}."
        ) from None


def calculate_wella_formula(
    hair: HairState,
    target: Target,
    line: BrandProfile | str | None = None,
    *,
    secondary_tone: str = "",
    target_grams: float = 100.0,
) -> Formula:
    """Universal Wella formula calculation for any supported line."""
    return calculate_formula(
        resolve_wella_line(line),
        hair,
        target,
        secondary_tone=secondary_tone,
        target_grams=target_grams,
    )


def check_wella_formula(
    hair: HairState,
    target: Target,
    master: MasterFormula,
    line: BrandProfile | str | None = None,
) -> list[Risk]:
    """Universal Wella formula check for any supported line."""
    return check_formula(resolve_wella_line(line), hair, target, master)
