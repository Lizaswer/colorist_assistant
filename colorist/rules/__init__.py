"""Модуль правил колористики: расчёт и проверка формул.

Чистый Python без внешних зависимостей — его можно тестировать
отдельно от API и мобильного приложения.
"""

from .calculator import OutOfScopeError, calculate_formula
from .checker import check_formula
from .models import (
    Component,
    Direction,
    Formula,
    HairState,
    MasterFormula,
    Note,
    Porosity,
    Service,
    Target,
)

__all__ = [
    "Component",
    "Direction",
    "Formula",
    "HairState",
    "MasterFormula",
    "Note",
    "OutOfScopeError",
    "Porosity",
    "Service",
    "Target",
    "calculate_formula",
    "check_formula",
]
