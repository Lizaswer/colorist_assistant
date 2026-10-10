"""Эталонные случаи: загрузка из data/cases и сравнение с ответом системы.

Используется и тестами (tests/test_cases.py), и скриптом оценки (scripts/evaluate.py).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from colorist.rules import (
    Component,
    Direction,
    Formula,
    HairState,
    MasterFormula,
    OutOfScopeError,
    Porosity,
    Target,
    calculate_formula,
    check_formula,
)

CASES_DIR = Path(__file__).parent.parent / "data" / "cases"


@dataclass
class Case:
    id: str
    source: str
    hair: HairState
    target: Target
    expected: dict | None = None             # эталонная формула мастера
    master_formula: MasterFormula | None = None
    expected_risk_ids: set[str] | None = None
    known_gap: str | None = None             # известное ограничение системы
    expected_refusal: str | None = None      # ID правила, по которому система должна отказать
    verified: bool = False                   # эталон подтверждён колористом


@dataclass
class CaseResult:
    case: Case
    formula: Formula | None = None
    error: str | None = None
    formula_matches: bool | None = None
    risk_ids: set[str] = field(default_factory=set)
    risks_match: bool | None = None
    differences: list[str] = field(default_factory=list)


def _components(items: list[dict]) -> list[Component]:
    return [Component(shade=i["shade"], grams=i["grams"]) for i in items]


def load_case(path: Path) -> Case:
    data = json.loads(path.read_text(encoding="utf-8"))
    hair = data["hair"]
    master = data.get("master_formula")
    return Case(
        id=data["id"],
        source=data.get("source", ""),
        hair=HairState(**{**hair, "porosity": Porosity(hair.get("porosity", "medium"))}),
        target=Target(level=data["target"]["level"], direction=Direction(data["target"]["direction"])),
        expected=data.get("expected"),
        master_formula=(
            MasterFormula(_components(master["components"]), master["oxide_percent"])
            if master else None
        ),
        expected_risk_ids=set(data["expected_risk_ids"]) if "expected_risk_ids" in data else None,
        known_gap=data.get("known_gap"),
        expected_refusal=data.get("expected_refusal"),
        verified=data.get("verified", False),
    )


def load_cases(directory: Path = CASES_DIR) -> list[Case]:
    return [load_case(p) for p in sorted(directory.glob("*.json"))]


def run_case(case: Case) -> CaseResult:
    result = CaseResult(case=case)
    refused_rule = None
    try:
        result.formula = calculate_formula(case.hair, case.target)
    except OutOfScopeError as error:
        result.error = f"{error} [{error.rule_id}]"
        refused_rule = error.rule_id

    if case.expected_refusal is not None:
        result.formula_matches = refused_rule == case.expected_refusal
        if not result.formula_matches:
            result.differences.append(
                f"ожидался отказ по {case.expected_refusal}, система: "
                + (result.error or "посчитала формулу")
            )

    if case.expected is not None:
        if result.formula is None:
            result.formula_matches = False
            result.differences.append(f"система отказалась считать: {result.error}")
        else:
            expected_components = _components(case.expected["components"])
            checks = [
                ("оттенки", result.formula.components, expected_components),
                ("оксид, %", result.formula.oxide_percent, case.expected["oxide_percent"]),
                ("время, мин", result.formula.time_min, case.expected["time_min"]),
            ]
            for name, got, want in checks:
                if got != want:
                    result.differences.append(f"{name}: система {fmt(got)}, эталон {fmt(want)}")
            # Поля эталона, которые система пока вообще не рассчитывает.
            for key, value in case.expected.items():
                if key not in SUPPORTED_EXPECTED_FIELDS:
                    result.differences.append(f"{key}: в эталоне {fmt_raw(value)}, система это не считает")
            result.formula_matches = not result.differences

    if case.master_formula is not None and case.expected_risk_ids is not None:
        risks = check_formula(case.hair, case.target, case.master_formula)
        result.risk_ids = {r.rule_id for r in risks}
        result.risks_match = result.risk_ids == case.expected_risk_ids
        if not result.risks_match:
            missed = case.expected_risk_ids - result.risk_ids
            extra = result.risk_ids - case.expected_risk_ids
            if missed:
                result.differences.append(f"не нашла риски: {', '.join(sorted(missed))}")
            if extra:
                result.differences.append(f"лишние риски: {', '.join(sorted(extra))}")
    return result


SUPPORTED_EXPECTED_FIELDS = {"components", "oxide_percent", "time_min"}


def fmt(value) -> str:
    if isinstance(value, list) and value and isinstance(value[0], Component):
        return " + ".join(f"{c.shade} {c.grams} г" for c in value)
    return str(value)


def fmt_raw(value) -> str:
    """Значение из JSON эталона в читаемом виде."""
    if isinstance(value, list) and value and isinstance(value[0], dict) and "shade" in value[0]:
        return fmt(_components(value))
    if value is True:
        return "да"
    return str(value)
