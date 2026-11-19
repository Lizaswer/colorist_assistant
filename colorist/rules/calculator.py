from __future__ import annotations

from colorist.brands.engine import calculate_formula as _engine_calculate
from colorist.brands.generic import GENERIC_PROFILE
from colorist.rules.errors import CalculationError
from colorist.rules.models import Formula, HairState, Target


def calculate_formula(hair: HairState, target: Target) -> Formula:
    return _engine_calculate(GENERIC_PROFILE, hair, target)
