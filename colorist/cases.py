from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from colorist.brands import resolve_profile
from colorist.brands.engine import calculate_formula, check_formula, calculate_zoned_formula
from colorist.rules import (
    CalculationError,
    Component,
    Corrector,
    Direction,
    HairState,
    MasterFormula,
    Target,
)


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    verified: bool
    formula_match: bool | None
    risk_match: bool | None
    known_gap: str | None = None
    error: str | None = None
    skipped_reason: str | None = None
    """Why the engine cannot evaluate this case yet (real colorist case)."""


def _hair(data: dict) -> HairState:
    return HairState(**data)


def _target(data: dict) -> Target:
    payload = {"level": data["level"], "direction": Direction(data.get("direction", "neutral"))}
    if data.get("shade_code"):
        payload["shade_code"] = data["shade_code"]
    return Target(**payload)


def _components(data: list[dict]) -> tuple[Component, ...]:
    return tuple(Component(x["shade"], x["grams"]) for x in data)


def load_cases(directory: str | Path = "data/cases") -> list[dict]:
    path = Path(directory)
    cases = []
    for file in sorted(path.glob("*.json")):
        cases.append(json.loads(file.read_text(encoding="utf-8")))
    return cases


def _formula_matches(case: dict, hair: HairState, target: Target) -> tuple[bool, str | None]:
    try:
        profile = resolve_profile(case.get("brand"), case.get("line"))
        formula = calculate_formula(profile, hair, target)
    except CalculationError as exc:
        return False, str(exc)

    expected = case.get("expected", {})
    actual_components = {(c.shade, c.grams) for c in formula.components}
    expected_components = {(c["shade"], float(c["grams"])) for c in expected.get("components", [])}
    matches = (
        actual_components == expected_components
        and formula.oxide_percent == float(expected.get("oxide_percent", formula.oxide_percent))
        and formula.mix_ratio == expected.get("mix_ratio", formula.mix_ratio)
        and formula.time_min == int(expected.get("time_min", formula.time_min))
    )
    return matches, None


def _risks_match(case: dict, hair: HairState, target: Target) -> bool:
    if "master_formula" not in case:
        return True
    profile = resolve_profile(case.get("brand"), case.get("line"))
    mf = case["master_formula"]
    risks = check_formula(profile, hair, target, MasterFormula(_components(mf["components"]), mf["oxide_percent"]))
    return {r.rule_id for r in risks} == set(case.get("expected_risk_ids", []))


def _zone_matches(actual, expected: dict) -> bool:
    actual_components = {(c.shade, float(c.grams)) for c in actual.components}
    expected_components = {(c["shade"], float(c["grams"])) for c in expected.get("components", [])}
    actual_correctors = {(c.shade, float(c.cm)) for c in actual.correctors}
    expected_correctors = {(c["shade"], float(c["cm"])) for c in expected.get("correctors", [])}
    return (
        actual_components == expected_components
        and actual_correctors == expected_correctors
        and actual.oxide_percent == float(expected.get("oxide_percent", actual.oxide_percent))
        and actual.oxide_grams == float(expected.get("oxide_grams", actual.oxide_grams))
        and actual.mix_ratio == expected.get("mix_ratio", actual.mix_ratio)
    )


def _zoned_matches(case: dict, hair: HairState, target: Target) -> tuple[bool, str | None]:
    """Compare the zone-aware engine output with the colorist's verified zones."""
    amounts = case.get("amounts", {})
    try:
        formula = calculate_zoned_formula(
            resolve_profile(case.get("brand"), case.get("line")),
            hair,
            target,
            root_grams=amounts.get("root_grams"),
            length_grams=amounts.get("length_grams"),
        )
    except CalculationError as exc:
        return False, str(exc)

    expected_zones = case.get("expected_zones", [])
    for expected in expected_zones:
        actual = formula.zone(expected["zone"])
        if actual is None or not _zone_matches(actual, expected):
            return False, None
    return True, None


def evaluate_case(case: dict) -> CaseResult:
    case_id = case.get("id", "unknown")
    verified = bool(case.get("verified", False))
    known_gap = case.get("known_gap")

    # Zone-aware cases (real colorist formulas) are compared zone by zone.
    if "expected_zones" in case:
        try:
            hair = _hair(case["hair"])
            target = _target(case["target"])
        except ValueError as exc:
            return CaseResult(
                case_id=case_id,
                verified=verified,
                formula_match=None,
                risk_match=None,
                known_gap=known_gap,
                error=str(exc),
            )
        formula_match, error = _zoned_matches(case, hair, target)
        return CaseResult(
            case_id=case_id,
            verified=verified,
            formula_match=formula_match,
            risk_match=None,
            known_gap=known_gap,
            error=error,
        )

    # Cases without a machine-readable expectation are recorded but not
    # compared — see known_gap for what is missing.
    if "expected" not in case:
        reason = "Формула колориста описана по зонам (корни/длина) и с корректорами — движок это ещё не считает."
        if case.get("colorist_solution"):
            return CaseResult(
                case_id=case_id,
                verified=verified,
                formula_match=None,
                risk_match=None,
                known_gap=known_gap,
                skipped_reason=reason,
            )

    try:
        hair = _hair(case["hair"])
        target = _target(case["target"])
    except ValueError as exc:
        return CaseResult(
            case_id=case_id,
            verified=verified,
            formula_match=None,
            risk_match=None,
            known_gap=known_gap,
            error=str(exc),
        )

    formula_match, error = _formula_matches(case, hair, target)
    risk_match = _risks_match(case, hair, target) if "master_formula" in case else None
    return CaseResult(
        case_id=case_id,
        verified=verified,
        formula_match=formula_match,
        risk_match=risk_match,
        known_gap=known_gap,
        error=error,
    )
