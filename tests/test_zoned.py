import json
from pathlib import Path

import pytest

from colorist.brands import WELLA_KOLESTON_PERFECT, resolve_profile
from colorist.brands.engine import calculate_zoned_formula, tone_key_of
from colorist.rules import Direction, HairState, Target
from colorist.rules.errors import CalculationError
from colorist.rules.knowledge import RULES

KOLESTON = WELLA_KOLESTON_PERFECT


def _zone_formula(hair, target, **kwargs):
    return calculate_zoned_formula(KOLESTON, hair, target, **kwargs)


# --- Case 11: tone-on-tone, 50% grey, cool target -----------------------------


def test_case11_single_zone_deep_grey_cool():
    formula = _zone_formula(
        HairState(root_level=7, length_level=7, grey_percent=50),
        Target(level=7, direction=Direction.COOL, shade_code="7.1"),
    )
    assert len(formula.zones) == 1
    zone = formula.zones[0]
    assert zone.zone == "all"
    assert [(c.shade, c.grams) for c in zone.components] == [("6.112", 30.0)]
    assert zone.oxide_percent == 6.0
    assert zone.oxide_grams == 30.0
    assert [(c.shade, c.cm) for c in zone.correctors] == [("0.82", 3.0)]


# --- Case 12: roots 7 / length 11, lightening to 9.26 ------------------------


def test_case12_two_zones_with_lightening():
    formula = _zone_formula(
        HairState(root_level=7, length_level=11, grey_percent=60),
        Target(level=9, direction=Direction.COOL, shade_code="9.26"),
    )
    assert [z.zone for z in formula.zones] == ["root", "length"]

    root = formula.zone("root")
    assert [(c.shade, c.grams) for c in root.components] == [("8.25", 30.0)]
    assert root.oxide_percent == 8.0
    assert root.oxide_grams == 30.0
    assert [(c.shade, c.cm) for c in root.correctors] == [("0.25", 2.0)]

    length = formula.zone("length")
    assert [(c.shade, c.grams) for c in length.components] == [("9.26", 30.0)]
    assert length.oxide_percent == 3.0
    assert length.oxide_grams == 30.0
    assert [(c.shade, c.cm) for c in length.correctors] == [("0.25", 2.0)]


# --- Case 13: roots 5 / length 8, warm target 7.43 ---------------------------


def test_case13_warm_mix_without_corrector():
    formula = _zone_formula(
        HairState(root_level=5, length_level=8, grey_percent=60),
        Target(level=7, direction=Direction.WARM, shade_code="7.43"),
        root_grams=30,
        length_grams=15,
    )

    root = formula.zone("root")
    assert [(c.shade, c.grams) for c in root.components] == [("7.43", 15.0), ("6.3", 15.0)]
    assert root.oxide_percent == 6.0
    assert root.oxide_grams == 30.0
    assert root.correctors == ()

    length = formula.zone("length")
    assert [(c.shade, c.grams) for c in length.components] == [("8.43", 15.0)]
    assert length.oxide_percent == 3.0
    assert length.oxide_grams == 15.0
    assert length.correctors == ()


# --- Structure and rules ------------------------------------------------------


def test_same_level_gives_single_zone():
    formula = _zone_formula(
        HairState(root_level=6, length_level=6, grey_percent=0),
        Target(level=6, direction=Direction.NEUTRAL),
    )
    assert [z.zone for z in formula.zones] == ["all"]


def test_different_levels_give_two_zones():
    formula = _zone_formula(
        HairState(root_level=5, length_level=8, grey_percent=0),
        Target(level=7, direction=Direction.COOL),
    )
    assert [z.zone for z in formula.zones] == ["root", "length"]


def test_every_zoned_step_points_to_a_known_rule():
    formula = _zone_formula(
        HairState(root_level=5, length_level=8, grey_percent=60, has_keratin=True),
        Target(level=7, direction=Direction.WARM, shade_code="7.43"),
    )
    unknown = [s.rule_id for s in formula.steps if s.rule_id not in RULES]
    for zone in formula.zones:
        unknown += [s.rule_id for s in zone.steps if s.rule_id not in RULES]
    assert not unknown


def test_lightening_breaks_through_grey_rule_into_blonde_range():
    # Lifting to a blonde target uses the stronger developer from the table.
    formula = _zone_formula(
        HairState(root_level=7, length_level=11, grey_percent=0),
        Target(level=9, direction=Direction.COOL),
    )
    assert formula.zone("root").oxide_percent == 8.0


def test_lightening_below_blonde_range_uses_grey_oxide():
    # Same lift, but the target is not a blonde: standard developer is enough.
    formula = _zone_formula(
        HairState(root_level=5, length_level=8, grey_percent=60),
        Target(level=7, direction=Direction.COOL),
    )
    assert formula.zone("root").oxide_percent == 6.0


def test_lightening_beyond_limit_is_rejected():
    with pytest.raises(CalculationError):
        _zone_formula(
            HairState(root_level=4, length_level=4),
            Target(level=9, direction=Direction.COOL),
        )


def test_length_refreshed_when_within_tolerance():
    formula = _zone_formula(
        HairState(root_level=5, length_level=8, grey_percent=0),
        Target(level=7, direction=Direction.WARM, shade_code="7.43"),
    )
    length = formula.zone("length")
    assert [c.shade for c in length.components] == ["8.43"]
    assert any(s.rule_id == "R-LENGTH-REFRESH" for s in length.steps)


def test_length_deposits_target_when_far_off():
    formula = _zone_formula(
        HairState(root_level=7, length_level=11, grey_percent=0),
        Target(level=9, direction=Direction.COOL, shade_code="9.26"),
    )
    length = formula.zone("length")
    assert [c.shade for c in length.components] == ["9.26"]
    assert any(s.rule_id == "R-LENGTH-DEPOSIT" for s in length.steps)


def test_unknown_shade_falls_back_to_derived_notation():
    formula = _zone_formula(
        HairState(root_level=6, length_level=6, grey_percent=0),
        Target(level=6, direction=Direction.WARM, shade_code="6.5"),
    )
    assert [c.shade for c in formula.zones[0].components] == ["6.5"]


def test_tone_key_parsing():
    assert tone_key_of(Target(7, Direction.COOL, "7.43")) == "43"
    assert tone_key_of(Target(7, Direction.COOL, "7/1")) == "1"
    assert tone_key_of(Target(7, Direction.COOL)) == ""


# --- Reference cases on disk --------------------------------------------------


@pytest.mark.parametrize(
    "filename",
    [
        "11-colorist-grey50-cool.json",
        "12-colorist-root7-length11-blond.json",
        "13-colorist-root5-length843-warm.json",
    ],
)
def test_colorist_reference_case_matches_engine(filename):
    from colorist.cases import evaluate_case

    path = Path("data/cases") / filename
    case = json.loads(path.read_text(encoding="utf-8"))
    result = evaluate_case(case)
    assert result.error is None, result.error
    assert result.formula_match is True
