from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from colorist.rules.models import Direction


@dataclass(frozen=True)
class CorrectorRule:
    """When a mix tone is added, which one, and how many centimetres.

    Rules are evaluated in order; the first match wins. ``None`` in a field
    means "any value". The table is knowledge-base data: it grows with every
    verified colorist case and must be checked against the brand chart.
    """

    shade: str
    cm: float
    direction: Direction | None = None
    tone: str | None = None
    requires_lightening: bool | None = None
    min_grey: int = 0
    note: str = ""


@dataclass(frozen=True)
class BrandProfile:
    """Everything a brand-specific calculation needs.

    The engine in :mod:`colorist.brands.engine` is brand-agnostic: it only
    reads this profile. Adding a brand means describing it here, not writing
    new calculation code.
    """

    key: str
    name: str
    tones: Mapping[Direction, str]
    natural_tone: str
    mix_ratio: str
    time_min: int
    time_max: int
    default_oxide: float
    grey_oxide: float
    high_grey_oxide: float
    available_oxides: tuple[float, ...] = ()
    levels: tuple[int, ...] = tuple(range(1, 11))
    tone_codes: tuple[str, ...] = ("0",)
    validate_catalog: bool = False
    max_darkening_levels: int = 2
    supports_lightening: bool = False
    info_steps: tuple[tuple[str, str], ...] = ()
    notes: str = ""

    # --- Zone-aware calculation -------------------------------------------------
    max_lightening_levels: int = 0
    blonde_threshold: int = 9
    lightening_oxides: Mapping[int, float] = None  # type: ignore[assignment]
    length_oxide: float = 3.0
    length_refresh_tolerance: int = 1
    deep_grey_threshold: int = 50
    warm_base_tone: str = "3"
    corrector_rules: tuple[CorrectorRule, ...] = ()
    shade_catalog: Mapping[tuple[int, str], str] = None  # type: ignore[assignment]
    default_root_grams: float = 30.0
    default_length_grams: float = 30.0

    def __post_init__(self) -> None:
        if self.lightening_oxides is None:
            object.__setattr__(self, "lightening_oxides", {})
        if self.shade_catalog is None:
            object.__setattr__(self, "shade_catalog", {})

    # --- Shades -----------------------------------------------------------------

    def tone_for(self, direction: Direction) -> str:
        return self.tones[direction]

    def shade(self, level: int, direction: Direction, secondary: str = "") -> str:
        return f"{level}/{self.tone_for(direction)}{secondary}"

    def catalog_shade(self, level: int, tone_key: str, direction: Direction) -> str:
        """Exact brand shade code, or a derived notation when not catalogued.

        The catalog holds the real codes from the brand's technical chart (and
        from verified colorist cases). Anything missing falls back to
        ``level.tone`` so the engine still answers for arbitrary parameters.
        """
        key = (level, tone_key)
        if key in self.shade_catalog:
            return self.shade_catalog[key]
        if tone_key:
            return f"{level}.{tone_key}"
        return f"{level}/{self.tone_for(direction)}"

    # --- Grey -------------------------------------------------------------------

    def natural_percent(self, grey_percent: int) -> int:
        """Share of the natural base in the mix.

        Below 20% grey no base is needed; from 20% the base covers the grey
        and grows with it (30% at 20-29% grey, 50% at 50% grey, and so on).
        This curve is an implementation assumption to be confirmed by a colorist.
        """
        if grey_percent < 20:
            return 0
        return min(100, max(30, grey_percent))

    def is_deep_grey(self, grey_percent: int) -> bool:
        return grey_percent >= self.deep_grey_threshold

    # --- Oxides -----------------------------------------------------------------

    def oxide_for(self, grey_percent: int) -> float:
        if grey_percent >= 50:
            return self.high_grey_oxide
        if grey_percent >= 20:
            return self.grey_oxide
        return self.default_oxide

    def oxide_for_roots(self, lift: int, target_level: int, grey_percent: int) -> float:
        """Oxide for the root zone.

        Lifting into the blonde range (target >= ``blonde_threshold``) needs the
        stronger developers from ``lightening_oxides``. Below that range the
        lift is covered by the standard developer, chosen by grey coverage.
        """
        if lift > 0 and target_level >= self.blonde_threshold:
            return self.lightening_oxides.get(lift, self.default_oxide)
        return self.oxide_for(grey_percent)

    def ratio_multiplier(self) -> float:
        """Oxide grams per gram of colour, parsed from ``mix_ratio`` (``1:2`` -> 2.0)."""
        left, _, right = self.mix_ratio.partition(":")
        try:
            l, r = float(left), float(right)
        except ValueError:
            return 1.0
        return r / l if l else 1.0

    # --- Correctors -------------------------------------------------------------

    def corrector_for(
        self,
        direction: Direction,
        lift: int,
        grey_percent: int,
        tone_key: str = "",
    ) -> tuple[str, float] | None:
        """(shade, cm) of the mix tone for this task, or None.

        ``tone_key`` is the target's tone as written by the colorist (``26``,
        ``1``, ``43``); rules may match it exactly.
        """
        lightening = lift > 0
        for rule in self.corrector_rules:
            if rule.direction is not None and rule.direction is not direction:
                continue
            if rule.tone is not None and rule.tone != tone_key:
                continue
            if rule.requires_lightening is not None and rule.requires_lightening != lightening:
                continue
            if grey_percent < rule.min_grey:
                continue
            return rule.shade, rule.cm
        return None

    # --- Catalog validation -----------------------------------------------------

    def has_level(self, level: int) -> bool:
        return level in self.levels

    def has_tone(self, tone: str) -> bool:
        """Accept the full tone code or its primary family.

        Decimal notation stacks several digits (``6.112`` = primary 1, then 1
        and 2), so a multi-digit tone is valid when its first digit is a known
        primary tone of the line.
        """
        if tone in self.tone_codes:
            return True
        return bool(tone) and tone[0] in self.tone_codes
