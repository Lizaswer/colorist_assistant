import pytest

from colorist.brands import (
    BRANDS,
    DEFAULT_BRAND,
    WELLA_COLOR_TOUCH,
    WELLA_ILLUMINA,
    WELLA_KOLESTON_PERFECT,
    list_brands,
    resolve_profile,
)
from colorist.brands.engine import calculate_formula, check_formula
from colorist.rules import Component, Direction, HairState, MasterFormula, Target
from colorist.rules.errors import CalculationError
from colorist.rules.knowledge import RULES


def test_default_brand_is_wella():
    assert DEFAULT_BRAND == "wella"
    assert resolve_profile().key == WELLA_KOLESTON_PERFECT.key


def test_registry_exposes_generic_and_wella_lines():
    assert set(BRANDS) == {"generic", "wella"}
    assert set(BRANDS["wella"]) == {"koleston_perfect", "illumina", "color_touch"}


def test_list_brands_is_serialisable():
    data = list_brands()
    assert {b["brand"] for b in data} == {"generic", "wella"}
    wella = next(b for b in data if b["brand"] == "wella")
    assert {line["key"] for line in wella["lines"]} == {
        "koleston_perfect",
        "illumina",
        "color_touch",
    }


def test_unknown_brand_raises_calculation_error():
    with pytest.raises(CalculationError):
        resolve_profile("loreal")


def test_unknown_line_raises_calculation_error():
    with pytest.raises(CalculationError):
        resolve_profile("wella", "no_such_line")


def test_line_parameters_differ_between_wella_lines():
    assert WELLA_KOLESTON_PERFECT.mix_ratio == "1:1"
    assert WELLA_COLOR_TOUCH.mix_ratio == "1:2"
    assert WELLA_COLOR_TOUCH.time_min < WELLA_KOLESTON_PERFECT.time_min
    assert WELLA_ILLUMINA.high_grey_oxide == 9.0


@pytest.mark.parametrize(
    "line_key,expected_oxide,expected_ratio",
    [
        ("koleston_perfect", 6.0, "1:1"),
        ("illumina", 6.0, "1:1"),
        ("color_touch", 4.0, "1:2"),
    ],
)
def test_grey_formula_uses_line_parameters(line_key, expected_oxide, expected_ratio):
    profile = resolve_profile("wella", line_key)
    formula = calculate_formula(
        profile,
        HairState(root_level=7, length_level=7, grey_percent=30),
        Target(level=7, direction=Direction.COOL),
    )
    assert [(c.shade, c.grams) for c in formula.components] == [("7/0", 30.0), ("7/1", 70.0)]
    assert formula.oxide_percent == expected_oxide
    assert formula.mix_ratio == expected_ratio


def test_no_grey_uses_line_default_oxide():
    formula = calculate_formula(
        WELLA_KOLESTON_PERFECT,
        HairState(root_level=7, length_level=7, grey_percent=0),
        Target(level=7, direction=Direction.WARM),
    )
    assert [c.shade for c in formula.components] == ["7/3"]
    assert formula.oxide_percent == WELLA_KOLESTON_PERFECT.default_oxide


def test_neutral_target_with_grey_merges_duplicate_shade():
    formula = calculate_formula(
        WELLA_ILLUMINA,
        HairState(root_level=6, length_level=6, grey_percent=50),
        Target(level=6, direction=Direction.NEUTRAL),
    )
    assert [(c.shade, c.grams) for c in formula.components] == [("6/0", 100.0)]


def test_every_wella_step_points_to_a_known_rule():
    for profile in BRANDS["wella"].values():
        formula = calculate_formula(
            profile,
            HairState(root_level=7, length_level=7, grey_percent=30, has_keratin=True),
            Target(level=7, direction=Direction.COOL),
        )
        assert formula.steps
        unknown = [s.rule_id for s in formula.steps if s.rule_id not in RULES]
        assert not unknown, f"{profile.key}: неизвестные правила {unknown}"


def test_lightening_is_rejected_for_every_wella_line():
    for profile in BRANDS["wella"].values():
        with pytest.raises(CalculationError):
            calculate_formula(
                profile,
                HairState(root_level=6, length_level=6),
                Target(level=8, direction=Direction.COOL),
            )


def test_root_darker_than_length_is_allowed():
    formula = calculate_formula(
        WELLA_KOLESTON_PERFECT,
        HairState(root_level=6, length_level=7, grey_percent=30),
        Target(level=7, direction=Direction.COOL),
    )
    assert [(c.shade, c.grams) for c in formula.components] == [("7/0", 30.0), ("7/1", 70.0)]


def test_decimal_notation_is_parsed_by_checker():
    risks = check_formula(
        WELLA_KOLESTON_PERFECT,
        HairState(root_level=7, length_level=7, grey_percent=30),
        Target(level=7, direction=Direction.COOL),
        MasterFormula([Component("7.43", 60)], 6.0),
    )
    assert {r.rule_id for r in risks} == {"C-COVERAGE", "C-DIRECTION"}


def test_full_target_tone_satisfies_direction():
    risks = check_formula(
        WELLA_KOLESTON_PERFECT,
        HairState(root_level=9, length_level=9),
        Target(level=9, direction=Direction.COOL, shade_code="9.26"),
        MasterFormula([Component("9.26", 100)], 4.0),
    )
    assert "C-DIRECTION" not in {r.rule_id for r in risks}


def test_checker_flags_oxide_outside_line_range():
    risks = check_formula(
        WELLA_KOLESTON_PERFECT,
        HairState(root_level=7, length_level=7, grey_percent=0),
        Target(level=7, direction=Direction.COOL),
        MasterFormula([Component("7/1", 60)], 3.0),
    )
    oxide_risks = [r for r in risks if r.rule_id == "C-OXIDE"]
    assert oxide_risks
    assert "ожидается" in oxide_risks[0].text.lower()


def test_checker_flags_shade_outside_palette_level():
    # Color Touch палитра ограничена уровнями 1-10, поэтому 12/0 вне каталога.
    risks = check_formula(
        WELLA_COLOR_TOUCH,
        HairState(root_level=12, length_level=12, grey_percent=0),
        Target(level=12, direction=Direction.NEUTRAL),
        MasterFormula([Component("12/0", 60)], 1.9),
    )
    assert any(r.rule_id == "C-SHADE" for r in risks)
    assert not [r for r in risks if r.rule_id == "C-LEVEL"]


def test_levels_up_to_twelve_are_supported():
    hair = HairState(root_level=11, length_level=12, grey_percent=0)
    target = Target(level=11, direction=Direction.COOL)
    formula = calculate_formula(WELLA_KOLESTON_PERFECT, hair, target)
    assert [c.shade for c in formula.components] == ["11/1"]


def test_level_above_twelve_is_rejected():
    with pytest.raises(ValueError):
        HairState(root_level=13, length_level=7)
    with pytest.raises(ValueError):
        Target(level=13)
