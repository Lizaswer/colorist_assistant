from colorist.rules import Component, Direction, HairState, MasterFormula, Target, calculate_formula, check_formula
from colorist.rules.knowledge import RULES


def test_every_step_points_to_a_known_rule():
    formula = calculate_formula(
        HairState(root_level=7, length_level=7, grey_percent=30),
        Target(level=7, direction=Direction.COOL),
    )
    assert formula.steps
    assert all(step.rule_id in RULES for step in formula.steps)


def test_every_risk_points_to_a_known_rule():
    risks = check_formula(
        HairState(7, 7, grey_percent=30, has_keratin=True),
        Target(8, Direction.COOL),
        MasterFormula([Component("8/3", 60)], 3),
    )
    assert risks
    assert all(risk.rule_id in RULES for risk in risks)


def test_grey_formula_contains_natural_base_and_6_percent():
    formula = calculate_formula(
        HairState(root_level=7, length_level=7, grey_percent=30),
        Target(level=7, direction=Direction.COOL),
    )
    assert [(x.shade, x.grams) for x in formula.components] == [("7/0", 30), ("7/1", 70)]
    assert formula.oxide_percent == 6


def test_master_formula_normalises_components_and_validates():
    import pytest
    master = MasterFormula([Component("7/0", 50)], 3)
    assert isinstance(master.components, tuple)
    assert master.oxide_percent == 3.0
    with pytest.raises(ValueError):
        MasterFormula([], 3)
    with pytest.raises(ValueError):
        MasterFormula([Component("7/0", 50)], 0)


def test_outside_mvp_lightening_is_rejected():
    import pytest
    with pytest.raises(ValueError):
        calculate_formula(HairState(7, 7), Target(8, Direction.COOL))


def test_checker_finds_expected_risks():
    hair = HairState(7, 7, grey_percent=30, has_keratin=False)
    target = Target(7, Direction.COOL)
    master = MasterFormula([Component("7/3", 60)], 3)
    risks = check_formula(hair, target, master)
    assert {r.rule_id for r in risks} == {"C-COVERAGE", "C-OXIDE", "C-DIRECTION"}
    assert any("/1" in r.text for r in risks if r.rule_id == "C-DIRECTION")


def test_checker_flags_lightening_even_when_target_matches():
    # Hair at level 7, master wants 8/1: lightening is outside MVP, same as in the calculator.
    risks = check_formula(HairState(7, 7), Target(8, Direction.COOL), MasterFormula([Component("8/1", 60)], 3))
    level_risks = [r for r in risks if r.rule_id == "C-LEVEL"]
    assert level_risks and level_risks[0].severity == "error"
    assert "осветление" in level_risks[0].text.lower()


def test_checker_flags_darkening_more_than_two_levels():
    risks = check_formula(HairState(8, 8), Target(5, Direction.NEUTRAL), MasterFormula([Component("5/0", 60)], 3))
    assert any(r.rule_id == "C-LEVEL" and r.severity == "error" for r in risks)


def test_checker_accepts_darkening_within_two_levels():
    risks = check_formula(HairState(7, 7), Target(5, Direction.NEUTRAL), MasterFormula([Component("5/0", 60)], 3))
    assert not [r for r in risks if r.rule_id == "C-LEVEL"]
