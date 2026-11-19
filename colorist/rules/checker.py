from __future__ import annotations

from colorist.brands.engine import check_formula as _engine_check
from colorist.brands.generic import GENERIC_PROFILE
from colorist.rules.models import HairState, MasterFormula, Risk, Target


def check_formula(hair: HairState, target: Target, master: MasterFormula) -> list[Risk]:
    return _engine_check(GENERIC_PROFILE, hair, target, master)
