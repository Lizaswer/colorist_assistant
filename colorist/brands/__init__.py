from __future__ import annotations

from colorist.brands.base import BrandProfile
from colorist.brands.generic import GENERIC_PROFILE
from colorist.brands.wella import (
    WELLA_COLOR_TOUCH,
    WELLA_ILLUMINA,
    WELLA_KOLESTON_PERFECT,
    WELLA_LINES,
    WellaLine,
    calculate_wella_formula,
    check_wella_formula,
    resolve_wella_line,
)
from colorist.brands.engine import calculate_formula, check_formula
from colorist.rules.errors import CalculationError

BRANDS: dict[str, dict[str, BrandProfile]] = {
    "generic": {"default": GENERIC_PROFILE},
    "wella": WELLA_LINES,
}

DEFAULT_BRAND = "wella"
DEFAULT_LINE_KEY = "koleston_perfect"


def resolve_profile(brand: str | None = None, line: str | None = None) -> BrandProfile:
    brand_key = (brand or DEFAULT_BRAND).strip().lower()
    if brand_key == "generic":
        return GENERIC_PROFILE
    if brand_key == "wella":
        return resolve_wella_line(line)
    raise CalculationError(
        f"Неизвестный бренд: {brand_key}. Доступные: {', '.join(sorted(BRANDS))}."
    )


def list_brands() -> list[dict]:
    result = []
    for brand_key, lines in BRANDS.items():
        line_list = []
        for key, profile in lines.items():
            line_list.append({
                "key": key,
                "name": profile.name,
                "mix_ratio": profile.mix_ratio,
                "time_min": profile.time_min,
                "time_max": profile.time_max,
                "available_oxides": list(profile.available_oxides),
            })
        result.append({"brand": brand_key, "lines": line_list})
    return result


__all__ = [
    "BRANDS",
    "BrandProfile",
    "DEFAULT_BRAND",
    "DEFAULT_LINE_KEY",
    "GENERIC_PROFILE",
    "WELLA_COLOR_TOUCH",
    "WELLA_ILLUMINA",
    "WELLA_KOLESTON_PERFECT",
    "WELLA_LINES",
    "WellaLine",
    "calculate_formula",
    "calculate_wella_formula",
    "check_formula",
    "check_wella_formula",
    "list_brands",
    "resolve_profile",
    "resolve_wella_line",
]
