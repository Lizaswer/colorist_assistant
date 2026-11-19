"""Core rules package.

The calculation entry points live in submodules and are resolved lazily, so
that brand profiles (which import the core models) can be imported without a
circular import.
"""

from .models import (
    CalculationStep,
    Component,
    Corrector,
    Direction,
    Formula,
    HairState,
    MasterFormula,
    Risk,
    Target,
    ZoneFormula,
    ZonedFormula,
)
from .errors import CalculationError

__all__ = [
    "CalculationError",
    "CalculationStep",
    "Component",
    "Corrector",
    "Direction",
    "Formula",
    "HairState",
    "MasterFormula",
    "Risk",
    "Target",
    "ZoneFormula",
    "ZonedFormula",
    "calculate_formula",
    "check_formula",
]


def __getattr__(name: str):
    if name == "calculate_formula":
        from .calculator import calculate_formula

        return calculate_formula
    if name == "check_formula":
        from .checker import check_formula

        return check_formula
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
