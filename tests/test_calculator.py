"""Модуль правил: расчёт формулы."""

import pytest

from colorist.rules import (
    Direction,
    HairState,
    OutOfScopeError,
    Porosity,
    Service,
    Target,
    calculate_formula,
)


def rule_ids(notes):
    return {note.rule_id for note in notes}


def test_tone_on_tone_natural_without_grey():
    formula = calculate_formula(
        HairState(root_level=6, length_level=6),
        Target(level=6, direction=Direction.NATURAL),
    )
    assert formula.service == Service.TONE_ON_TONE
    assert [c.shade for c in formula.components] == ["6/0"]
    assert formula.oxide_percent == 3.0


def test_cool_target_on_warm_background_uses_ash():
    formula = calculate_formula(
        HairState(root_level=7, length_level=7),
        Target(level=7, direction=Direction.COOL),
    )
    assert formula.components[0].shade == "7/1"
    assert "R-NEUTRAL-COOL" in rule_ids(formula.steps)


def test_grey_adds_natural_shade_and_6_percent():
    formula = calculate_formula(
        HairState(root_level=7, length_level=7, grey_percent=50),
        Target(level=7, direction=Direction.COOL),
    )
    shades = [c.shade for c in formula.components]
    assert shades == ["7/1", "7/0"]
    assert sum(c.grams for c in formula.components) == 60
    assert formula.oxide_percent == 6.0
    assert {"R-GREY-NATURAL", "R-OX-GREY"} <= rule_ids(formula.steps)


def test_darker_by_two_levels_is_allowed():
    formula = calculate_formula(
        HairState(root_level=8, length_level=8),
        Target(level=6, direction=Direction.WARM),
    )
    assert formula.service == Service.DARKER
    assert formula.components[0].shade == "6/3"


def test_lightening_is_out_of_scope():
    with pytest.raises(OutOfScopeError) as error:
        calculate_formula(
            HairState(root_level=6, length_level=6),
            Target(level=8, direction=Direction.NATURAL),
        )
    assert error.value.rule_id == "R-SCOPE-LIGHTEN"


def test_darker_by_three_levels_is_out_of_scope():
    with pytest.raises(OutOfScopeError) as error:
        calculate_formula(
            HairState(root_level=9, length_level=9),
            Target(level=6, direction=Direction.NATURAL),
        )
    assert error.value.rule_id == "R-DARK-MAX"


def test_invalid_level_raises():
    with pytest.raises(ValueError):
        calculate_formula(
            HairState(root_level=12, length_level=6),
            Target(level=6, direction=Direction.NATURAL),
        )


def test_warnings_for_history_and_always_allergy_test():
    formula = calculate_formula(
        HairState(
            root_level=6,
            length_level=6,
            porosity=Porosity.HIGH,
            has_henna=True,
            has_keratin=True,
        ),
        Target(level=6, direction=Direction.NATURAL),
    )
    assert rule_ids(formula.warnings) == {
        "R-WARN-HENNA",
        "R-WARN-KERATIN",
        "R-WARN-POROSITY",
        "R-SAFETY",
    }


def test_every_step_points_to_a_known_rule():
    from colorist.rules.knowledge import RULES

    formula = calculate_formula(
        HairState(root_level=7, length_level=7, grey_percent=40, has_henna=True),
        Target(level=6, direction=Direction.COOL),
    )
    assert rule_ids(formula.steps + formula.warnings) <= set(RULES)
