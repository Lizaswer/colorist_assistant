"""Модуль правил: проверка формулы мастера."""

import pytest

from colorist.rules import (
    Component,
    Direction,
    HairState,
    MasterFormula,
    Porosity,
    Target,
    check_formula,
)


def risk_ids(risks):
    return {risk.rule_id for risk in risks}


def test_good_formula_has_no_risks():
    risks = check_formula(
        HairState(root_level=7, length_level=7, grey_percent=40),
        Target(level=7, direction=Direction.COOL),
        MasterFormula([Component("7/1", 40), Component("7/0", 20)], oxide_percent=6.0),
    )
    assert risks == []


def test_low_oxide_and_no_natural_on_grey():
    risks = check_formula(
        HairState(root_level=7, length_level=7, grey_percent=50),
        Target(level=7, direction=Direction.NATURAL),
        MasterFormula([Component("7/3", 60)], oxide_percent=3.0),
    )
    assert {"C-OX-GREY", "C-GREY-NO-NATURAL"} <= risk_ids(risks)


def test_cool_target_without_ash_warns_about_orange():
    risks = check_formula(
        HairState(root_level=7, length_level=7),
        Target(level=7, direction=Direction.COOL),
        MasterFormula([Component("7/0", 60)], oxide_percent=3.0),
    )
    assert "C-WARM-NO-ASH" in risk_ids(risks)


def test_ash_on_light_porous_hair_warns_about_green():
    risks = check_formula(
        HairState(root_level=8, length_level=9, porosity=Porosity.HIGH),
        Target(level=8, direction=Direction.COOL),
        MasterFormula([Component("8/1", 60)], oxide_percent=3.0),
    )
    assert "C-ASH-POROUS-LIGHT" in risk_ids(risks)


def test_level_mismatch_and_henna():
    risks = check_formula(
        HairState(root_level=7, length_level=7, has_henna=True),
        Target(level=7, direction=Direction.NATURAL),
        MasterFormula([Component("5/0", 60)], oxide_percent=3.0),
    )
    assert {"C-LEVEL-MISMATCH", "C-HENNA"} <= risk_ids(risks)


def test_unreadable_shade_raises():
    with pytest.raises(ValueError):
        check_formula(
            HairState(root_level=7, length_level=7),
            Target(level=7, direction=Direction.NATURAL),
            MasterFormula([Component("семь-ноль", 60)], oxide_percent=3.0),
        )
