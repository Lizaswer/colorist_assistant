from __future__ import annotations

import re

from colorist.brands.base import BrandProfile
from colorist.logging_config import get_logger

_log = get_logger("engine")
from colorist.rules.errors import CalculationError
from colorist.rules.knowledge import NATURAL_TONE, level_change_issue
from colorist.rules.models import (
    CalculationStep,
    Component,
    Corrector,
    Direction,
    Formula,
    HairState,
    MasterFormula,
    Risk,
    Target,
    ZoneFormula,
    ZonedFormula,
)

# Supports both notations: slash (7/1) and decimal (7.43, 6.112).
_SHADE_RE = re.compile(r"^(?P<level>\d{1,2})[/.](?P<tone>[0-9A-Za-z]+)$")

ZONE_ROOT = "root"
ZONE_LENGTH = "length"
ZONE_ALL = "all"

ZONE_LABELS = {
    ZONE_ROOT: "Корни",
    ZONE_LENGTH: "Длина",
    ZONE_ALL: "Корни и длина",
}

# Rules specific to brand-aware mode, kept in the shared registry in knowledge.py.
RULE_LINE = "W-LINE"
RULE_SHADE_CATALOG = "C-SHADE"


def parse_shades(components) -> list[tuple[int, str]]:
    """(level, tone) for every component whose shade is in the ``7/1`` notation."""
    parsed: list[tuple[int, str]] = []
    for component in components:
        m = _SHADE_RE.match(component.shade.strip())
        if m:
            parsed.append((int(m.group("level")), m.group("tone")))
    return parsed


def calculate_formula(
    profile: BrandProfile,
    hair: HairState,
    target: Target,
    *,
    secondary_tone: str = "",
    target_grams: float = 100.0,
) -> Formula:
    _log.info(
        "calculate_formula: brand=%s line=%s root=%d length=%d grey=%d%% keratin=%s target=%d/%s",
        profile.key, profile.name, hair.root_level, hair.length_level,
        hair.grey_percent, hair.has_keratin, target.level, target.direction.value,
    )
    _check_level_change(profile, hair, target)

    grey = hair.grey_percent
    natural_pct = profile.natural_percent(grey)
    nuance_pct = 100 - natural_pct

    natural_shade = profile.shade(target.level, Direction.NEUTRAL)
    # Preserve an explicitly entered catalogue code such as 9.26. Previously
    # the flat calculator silently replaced it with the direction default.
    nuance_shade = (
        target.shade_code.strip()
        if target.shade_code
        else profile.shade(target.level, target.direction, secondary_tone)
    )

    components: list[Component] = []
    if natural_pct and nuance_pct and natural_shade == nuance_shade:
        components.append(
            Component(natural_shade, round(target_grams * (natural_pct + nuance_pct) / 100, 1))
        )
    else:
        if natural_pct:
            components.append(
                Component(natural_shade, round(target_grams * natural_pct / 100, 1))
            )
        if nuance_pct:
            components.append(
                Component(nuance_shade, round(target_grams * nuance_pct / 100, 1))
            )

    oxide = profile.oxide_for(grey)
    steps = [
        CalculationStep(
            "R-LEVEL",
            f"Целевой уровень {target.level} находится в допустимом диапазоне ({profile.name}).",
        ),
    ]
    if grey >= 20:
        steps.append(
            CalculationStep(
                "R-GREY-HIGH" if grey >= 50 else "R-GREY",
                f"Седина {grey}%: в формулу добавлена натуральная база ({natural_pct}%).",
            )
        )
    else:
        steps.append(
            CalculationStep(
                "R-DIRECTION",
                f"Выбрано направление {target.direction.value} для целевого оттенка.",
            )
        )
    steps.append(
        CalculationStep(
            "R-OXIDE-GREY" if grey >= 20 else "R-OXIDE-SAME",
            f"Выбран оксид {oxide:g}% для условий задачи.",
        )
    )
    steps.append(CalculationStep("R-RATIO", f"Соотношение краски и оксида — {profile.mix_ratio}."))
    steps.append(CalculationStep("R-TIME", f"Расчётное время выдержки — {profile.time_min} мин."))
    for rule_id, text in profile.info_steps:
        steps.append(CalculationStep(rule_id, text))
    if hair.has_keratin:
        steps.append(
            CalculationStep(
                "R-KERATIN",
                "Есть отметка о кератиновой процедуре: перед применением нужен контроль пряди.",
            )
        )

    return Formula(
        components=tuple(components),
        oxide_percent=oxide,
        mix_ratio=profile.mix_ratio,
        time_min=profile.time_min,
        steps=tuple(steps),
    )


def _check_level_change(profile: BrandProfile, hair: HairState, target: Target) -> None:
    if target.level > hair.length_level:
        raise CalculationError(
            f"Осветление не входит в расчёт ({profile.name}): "
            f"цель {target.level} выше уровня длины {hair.length_level}."
        )
    darkening = hair.root_level - target.level
    if darkening > profile.max_darkening_levels:
        _log.warning(
            "Rejected: darkening root=%d target=%d delta=%d > max=%d (brand=%s)",
            hair.root_level, target.level, darkening, profile.max_darkening_levels, profile.key,
        )
        raise CalculationError(
            f"Затемнение корней более чем на {profile.max_darkening_levels} уровня "
            f"не входит в расчёт ({profile.name}): корни {hair.root_level} → цель {target.level}."
        )


def _level_change_risks(hair: HairState, level: int, profile: BrandProfile) -> list[Risk]:
    risks: list[Risk] = []
    if level > hair.length_level:
        risks.append(Risk(
            "C-LEVEL",
            f"Оттенок уровня {level} выше уровня длины {hair.length_level}: "
            f"осветление не входит в расчёт ({profile.name}).",
            "error",
        ))
    darkening = hair.root_level - level
    if darkening > profile.max_darkening_levels:
        risks.append(Risk(
            "C-LEVEL",
            f"Затемнение корней {hair.root_level} → {level} "
            f"(более {profile.max_darkening_levels} уровней) не поддерживается ({profile.name}).",
            "error",
        ))
    return risks


def check_formula(
    profile: BrandProfile,
    hair: HairState,
    target: Target,
    master: MasterFormula,
) -> list[Risk]:
    _log.info(
        "check_formula: brand=%s root=%d length=%d grey=%d%% target=%d/%s oxide=%.1f%% components=%s",
        profile.key, hair.root_level, hair.length_level, hair.grey_percent,
        target.level, target.direction.value, master.oxide_percent,
        [(c.shade, c.grams) for c in master.components],
    )
    risks: list[Risk] = []
    shades = parse_shades(master.components)
    levels = [level for level, _ in shades]
    tones = [tone for _, tone in shades]

    if not levels:
        risks.append(Risk("C-LEVEL", "Не удалось определить уровень ни одного оттенка в формуле.", "error"))
        return risks

    for level in sorted(set(levels)):
        risks.extend(_level_change_risks(hair, level, profile))
        if profile.validate_catalog and not profile.has_level(level):
            risks.append(
                Risk(
                    RULE_SHADE_CATALOG,
                    f"Оттенок уровня {level} не входит в палитру линии «{profile.name}».",
                    "error",
                )
            )

    if any(level != target.level for level in levels):
        risks.append(
            Risk(
                "C-LEVEL",
                f"В формуле есть уровень, отличный от целевого {target.level}.",
            )
        )

    if profile.validate_catalog:
        for tone in set(tones):
            if not profile.has_tone(tone):
                risks.append(
                    Risk(
                        RULE_SHADE_CATALOG,
                        f"Тона /{tone} нет в палитре линии «{profile.name}». Проверьте техническую карту бренда.",
                    )
                )

    if hair.grey_percent >= 20 and profile.natural_tone not in tones:
        risks.append(
            Risk(
                "C-COVERAGE",
                f"При седине {hair.grey_percent}% в формуле нет натуральной базы /{profile.natural_tone}.",
            )
        )

    expected_oxide = profile.oxide_for(hair.grey_percent)
    if master.oxide_percent != expected_oxide:
        extra = ""
        if profile.available_oxides and master.oxide_percent not in profile.available_oxides:
            extra = f" Кроме того, этого оксида нет в линейке «{profile.name}»."
        risks.append(
            Risk(
                "C-OXIDE",
                f"Для этой задачи ожидается {expected_oxide:g}% оксид, указано {master.oxide_percent:g}%.{extra}",
            )
        )
    elif profile.available_oxides and master.oxide_percent not in profile.available_oxides:
        risks.append(
            Risk(
                "C-OXIDE",
                f"Указанный оксид {master.oxide_percent:g}% не входит в линейку оксидов «{profile.name}».",
            )
        )

    desired_tone = profile.tone_for(target.direction)
    target_tone = tone_key_of(target)
    target_satisfies_direction = bool(target_tone and target_tone in tones)
    family_satisfies_direction = any(
        tone.startswith(desired_tone) for tone in tones
    )
    if (
        target.direction is not Direction.NEUTRAL
        and not target_satisfies_direction
        and not family_satisfies_direction
    ):
        risks.append(
            Risk(
                "C-DIRECTION",
                f"В формуле не найден основной нюанс /{desired_tone} для направления {target.direction.value}.",
            )
        )

    if hair.has_keratin:
        risks.append(
            Risk(
                "C-KERATIN",
                "Волосы после кератиновой процедуры: требуется контроль пряди и сверка с инструкцией бренда.",
            )
        )

    _log.info("check_formula: %d risks found: %s", len(risks), [r.rule_id for r in risks])
    return risks


# --- Zone-aware calculation ---------------------------------------------------
#
# A real salon service treats roots and length separately: they differ in
# level, porosity and history. This block implements that, plus correctors
# (mix tones dosed in centimetres) and controlled lightening.


def tone_key_of(target: Target) -> str:
    """Tone part of the target shade code (``7.43`` -> ``43``), or "" if absent."""
    if not target.shade_code:
        return ""
    m = _SHADE_RE.match(target.shade_code.strip())
    return m.group("tone") if m else ""


def _check_zoned_levels(profile: BrandProfile, hair: HairState, target: Target) -> None:
    lift = target.level - hair.root_level
    if lift > 0 and not profile.supports_lightening:
        raise CalculationError(
            f"Осветление не поддерживается линией «{profile.name}»: "
            f"цель {target.level} выше уровня корней {hair.root_level}."
        )
    if lift > profile.max_lightening_levels:
        raise CalculationError(
            f"Осветление на {lift} тонов выходит за предел линии «{profile.name}» "
            f"({profile.max_lightening_levels}). Нужна обесцвечивающая пудра."
        )
    darkening = hair.root_level - target.level
    if darkening > profile.max_darkening_levels:
        raise CalculationError(
            f"Затемнение корней более чем на {profile.max_darkening_levels} уровня "
            f"не входит в расчёт ({profile.name}): корни {hair.root_level} → цель {target.level}."
        )


def _root_components(
    profile: BrandProfile, target: Target, tone_key: str, grey: int, grams: float
) -> tuple[list[Component], list[CalculationStep]]:
    """Colour components for the root zone.

    At deep grey the root shade goes one level deeper than the target: grey
    hair has no pigment of its own, so a deeper base restores density. Warm
    targets mix the deeper shade in 1:1 instead of a corrector.
    """
    steps: list[CalculationStep] = []
    target_shade = profile.catalog_shade(target.level, tone_key, target.direction)

    if not profile.is_deep_grey(grey):
        steps.append(
            CalculationStep(
                "R-LEVEL",
                f"Седина {grey}% ниже {profile.deep_grey_threshold}%: корни красятся в целевой оттенок {target_shade}.",
            )
        )
        return [Component(target_shade, round(grams, 1))], steps

    deeper_level = max(1, target.level - 1)

    if target.direction is Direction.WARM:
        deep_shade = profile.catalog_shade(
            deeper_level, profile.warm_base_tone, Direction.WARM
        )
        half = round(grams / 2, 1)
        steps.append(
            CalculationStep(
                "R-DEEP-GREY-LEVEL",
                f"Седина {grey}%: целевой {target_shade} смешан 1:1 с более глубоким {deep_shade} для плотности.",
            )
        )
        steps.append(
            CalculationStep(
                "R-WARM-MIX",
                "Тёплое направление: плотность седины добирается смесью, корректор не требуется.",
            )
        )
        return [
            Component(target_shade, half),
            Component(deep_shade, round(grams - half, 1)),
        ], steps

    deep_shade = profile.catalog_shade(deeper_level, tone_key, target.direction)
    steps.append(
        CalculationStep(
            "R-DEEP-GREY-LEVEL",
            f"Седина {grey}%: для корней взят {deep_shade} — на уровень глубже цели {target.level} для плотности покрытия.",
        )
    )
    return [Component(deep_shade, round(grams, 1))], steps


def _length_components(
    profile: BrandProfile, hair: HairState, target: Target, tone_key: str, grams: float
) -> tuple[list[Component], list[CalculationStep]]:
    """Colour components for the length zone."""
    gap = hair.length_level - target.level
    if 0 <= gap <= profile.length_refresh_tolerance:
        shade = profile.catalog_shade(hair.length_level, tone_key, target.direction)
        step = CalculationStep(
            "R-LENGTH-REFRESH",
            f"Длина {hair.length_level} отличается от цели {target.level} на {gap} тон: "
            f"освежается на своём уровне оттенком {shade}, без затемнения.",
        )
    else:
        shade = profile.catalog_shade(target.level, tone_key, target.direction)
        if gap > profile.length_refresh_tolerance:
            step = CalculationStep(
                "R-LENGTH-DEPOSIT",
                f"Длина {hair.length_level} заметно светлее цели {target.level}: "
                f"кладётся целевой оттенок {shade}.",
            )
        else:
            step = CalculationStep(
                "R-LENGTH-DEPOSIT",
                f"Длина {hair.length_level} темнее цели {target.level}: кладётся целевой оттенок {shade}.",
            )
    return [Component(shade, round(grams, 1))], [step]


def _corrector_steps(profile: BrandProfile, corrector: Corrector | None) -> list[CalculationStep]:
    if corrector is not None:
        return [
            CalculationStep(
                "R-CORRECTOR",
                f"Добавлен корректор {corrector.shade} — {corrector.cm:g} см для удержания холодного нюанса.",
            )
        ]
    return [
        CalculationStep(
            "R-CORRECTOR-NONE",
            "Корректор не добавляется: направление не требует нейтрализации.",
        )
    ]


def _build_zone(
    profile: BrandProfile,
    zone: str,
    components: list[Component],
    steps: list[CalculationStep],
    oxide: float,
    corrector: Corrector | None,
    oxide_rule_id: str,
    oxide_text: str,
) -> ZoneFormula:
    color_grams = round(sum(c.grams for c in components), 1)
    oxide_grams = round(color_grams * profile.ratio_multiplier(), 1)
    all_steps = list(steps)
    all_steps.append(CalculationStep(oxide_rule_id, oxide_text))
    all_steps.append(
        CalculationStep(
            "R-GRAMS",
            f"Краска {color_grams:g} г + оксид {oxide_grams:g} г (соотношение {profile.mix_ratio}).",
        )
    )
    all_steps.extend(_corrector_steps(profile, corrector))
    for rule_id, text in profile.info_steps:
        all_steps.append(CalculationStep(rule_id, text))
    return ZoneFormula(
        zone=zone,
        components=tuple(components),
        oxide_percent=oxide,
        oxide_grams=oxide_grams,
        mix_ratio=profile.mix_ratio,
        time_min=profile.time_min,
        correctors=(corrector,) if corrector else (),
        steps=tuple(all_steps),
    )


def calculate_zoned_formula(
    profile: BrandProfile,
    hair: HairState,
    target: Target,
    *,
    root_grams: float | None = None,
    length_grams: float | None = None,
) -> ZonedFormula:
    """Zone-aware calculation: roots and length separately, with correctors.

    Unlike :func:`calculate_formula`, controlled lightening of the roots is
    allowed up to ``profile.max_lightening_levels``.
    """
    root_grams = profile.default_root_grams if root_grams is None else root_grams
    length_grams = profile.default_length_grams if length_grams is None else length_grams

    _log.info(
        "calculate_zoned_formula: brand=%s line=%s root=%d length=%d grey=%d%% target=%s/%s "
        "root_grams=%s length_grams=%s",
        profile.key, profile.name, hair.root_level, hair.length_level, hair.grey_percent,
        target.level, target.shade_code or target.direction.value, root_grams, length_grams,
    )

    _check_zoned_levels(profile, hair, target)

    tone_key = tone_key_of(target)
    grey = hair.grey_percent
    lift = target.level - hair.root_level

    # The corrector is decided once for the whole head, from the root task.
    found = profile.corrector_for(target.direction, lift, grey, tone_key)
    corrector = Corrector(found[0], found[1]) if found else None

    head_steps: list[CalculationStep] = []
    zones: list[ZoneFormula] = []

    if hair.root_level == hair.length_level:
        head_steps.append(
            CalculationStep(
                "R-ZONE-ALL",
                f"Корни и длина одного уровня ({hair.root_level}) — единая формула на всю голову.",
            )
        )
        components, steps = _root_components(profile, target, tone_key, grey, root_grams)
        oxide = profile.oxide_for_roots(lift, target.level, grey)
        zones.append(
            _build_zone(
                profile, ZONE_ALL, components, steps, oxide, corrector,
                "R-LIFT-OXIDE" if lift > 0 else "R-GREY-OXIDE",
                f"Оксид {oxide:g}%: подъём на {lift} тон., цель {target.level}, седина {grey}%.",
            )
        )
    else:
        head_steps.append(
            CalculationStep(
                "R-ZONE-ROOT",
                f"Корни {hair.root_level} и длина {hair.length_level} разного уровня — расчёт по зонам.",
            )
        )

        root_components, root_steps = _root_components(profile, target, tone_key, grey, root_grams)
        root_oxide = profile.oxide_for_roots(lift, target.level, grey)
        zones.append(
            _build_zone(
                profile, ZONE_ROOT, root_components, root_steps, root_oxide, corrector,
                "R-LIFT-OXIDE" if lift > 0 else "R-GREY-OXIDE",
                f"Оксид {root_oxide:g}% для корней: подъём на {lift} тон., цель {target.level}, седина {grey}%.",
            )
        )

        length_components, length_steps = _length_components(
            profile, hair, target, tone_key, length_grams
        )
        zones.append(
            _build_zone(
                profile, ZONE_LENGTH, length_components, length_steps,
                profile.length_oxide, corrector,
                "R-LENGTH-OXIDE",
                f"Оксид {profile.length_oxide:g}% для длины: пористые окрашенные волосы, только депозиция тона.",
            )
        )

    if hair.has_keratin:
        head_steps.append(
            CalculationStep(
                "R-KERATIN",
                "Есть отметка о кератиновой процедуре: перед применением нужен контроль пряди.",
            )
        )

    result = ZonedFormula(zones=tuple(zones), steps=tuple(head_steps))
    _log.info(
        "calculate_zoned_formula: %d zones: %s",
        len(result.zones),
        [(z.zone, [c.shade for c in z.components], z.oxide_percent) for z in result.zones],
    )
    return result
