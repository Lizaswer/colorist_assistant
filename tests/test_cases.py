"""Эталонные случаи из data/cases/*.json.

Каждый JSON-файл автоматически становится тестом.
Случай с полем "known_gap" — известное ограничение системы: пока система
с ним не справляется, тест помечается xfail (ожидаемая ошибка) и не ломает сборку.
Если система начала справляться — тест упадёт с просьбой убрать known_gap.
"""

import pytest

from colorist.cases import CASES_DIR, load_case, run_case

CASE_FILES = sorted(CASES_DIR.glob("*.json"))


@pytest.mark.parametrize("path", CASE_FILES, ids=lambda p: p.stem)
def test_case(path):
    case = load_case(path)
    result = run_case(case)
    passed = result.formula_matches is not False and result.risks_match is not False
    if case.known_gap:
        if passed:
            pytest.fail(f"{case.id}: ограничение исправлено — уберите known_gap из JSON")
        pytest.xfail(case.known_gap)
    assert passed, result.differences
