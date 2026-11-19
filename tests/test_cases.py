from colorist.cases import evaluate_case, load_cases


def test_example_case():
    cases = load_cases("data/cases")
    assert len(cases) >= 1
    result = evaluate_case(cases[0])
    assert result.formula_match
    assert result.risk_match
    assert result.error is None


def test_out_of_scope_case_is_reported_not_raised():
    case = {
        "id": "lightening",
        "brand": "generic",
        "hair": {"root_level": 6, "length_level": 6},
        "target": {"level": 8, "direction": "cool"},
        "expected": {"components": [{"shade": "8/1", "grams": 100}]},
        "master_formula": {"components": [{"shade": "8/1", "grams": 60}], "oxide_percent": 3},
        "expected_risk_ids": ["C-LEVEL"],
    }
    result = evaluate_case(case)
    assert not result.formula_match
    assert "Осветление" in (result.error or "")
    # The checker still runs and must flag the lightening attempt.
    assert result.risk_match
