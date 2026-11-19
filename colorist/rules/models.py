from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Any


class Direction(str, Enum):
    NEUTRAL = "neutral"
    WARM = "warm"
    COOL = "cool"


@dataclass(frozen=True)
class HairState:
    root_level: int
    length_level: int
    grey_percent: int = 0
    has_keratin: bool = False

    def __post_init__(self) -> None:
        if not 1 <= self.root_level <= 12 or not 1 <= self.length_level <= 12:
            raise ValueError("Уровень волос должен быть от 1 до 12")
        if not 0 <= self.grey_percent <= 100:
            raise ValueError("Процент седины должен быть от 0 до 100")


@dataclass(frozen=True)
class Target:
    level: int
    direction: Direction = Direction.NEUTRAL
    shade_code: str | None = None

    def __post_init__(self) -> None:
        if not 1 <= self.level <= 12:
            raise ValueError("Целевой уровень должен быть от 1 до 12")
        if self.shade_code:
            match = re.fullmatch(r"(\d{1,2})[/.][0-9A-Za-z]+", self.shade_code.strip())
            if not match:
                raise ValueError("Код оттенка должен иметь формат уровня и тона, например 9.26")
            if int(match.group(1)) != self.level:
                raise ValueError("Уровень в коде оттенка должен совпадать с целевым уровнем")


@dataclass(frozen=True)
class Component:
    shade: str
    grams: float

    def __post_init__(self) -> None:
        if not self.shade:
            raise ValueError("Оттенок не может быть пустым")
        if self.grams <= 0:
            raise ValueError("Количество компонента должно быть положительным")


@dataclass(frozen=True)
class CalculationStep:
    rule_id: str
    text: str


@dataclass(frozen=True)
class Formula:
    components: tuple[Component, ...]
    oxide_percent: float
    mix_ratio: str
    time_min: int
    steps: tuple[CalculationStep, ...] = field(default_factory=tuple)

    @property
    def total_grams(self) -> float:
        return sum(c.grams for c in self.components)


@dataclass(frozen=True)
class MasterFormula:
    """A formula entered by the master for checking. Any iterable of components is accepted."""

    components: tuple[Component, ...]
    oxide_percent: float

    def __post_init__(self) -> None:
        # Normalise so lists from the API/tests become hashable, immutable tuples.
        object.__setattr__(self, "components", tuple(self.components))
        object.__setattr__(self, "oxide_percent", float(self.oxide_percent))
        if not self.components:
            raise ValueError("Формула должна содержать хотя бы один компонент")
        if self.oxide_percent <= 0:
            raise ValueError("Процент оксида должен быть положительным")


@dataclass(frozen=True)
class Risk:
    rule_id: str
    text: str
    severity: str = "warning"

    def as_dict(self) -> dict[str, Any]:
        return {"rule_id": self.rule_id, "text": self.text, "severity": self.severity}


@dataclass(frozen=True)
class Corrector:
    """Mix tone / corrector, dosed in centimetres from the tube."""

    shade: str
    cm: float

    def __post_init__(self) -> None:
        if not self.shade:
            raise ValueError("Оттенок корректора не может быть пустым")
        if self.cm <= 0:
            raise ValueError("Объём корректора должен быть положительным")

    def as_dict(self) -> dict[str, Any]:
        return {"shade": self.shade, "cm": self.cm}


@dataclass(frozen=True)
class ZoneFormula:
    """Formula for a single zone: roots, length, or the whole head."""

    zone: str
    components: tuple[Component, ...]
    oxide_percent: float
    oxide_grams: float
    mix_ratio: str
    time_min: int
    correctors: tuple[Corrector, ...] = field(default_factory=tuple)
    steps: tuple[CalculationStep, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "components", tuple(self.components))
        object.__setattr__(self, "correctors", tuple(self.correctors))
        object.__setattr__(self, "steps", tuple(self.steps))
        if not self.components:
            raise ValueError("Формула зоны должна содержать хотя бы один компонент")

    @property
    def color_grams(self) -> float:
        return sum(c.grams for c in self.components)

    def as_dict(self) -> dict[str, Any]:
        return {
            "zone": self.zone,
            "components": [{"shade": c.shade, "grams": c.grams} for c in self.components],
            "oxide_percent": self.oxide_percent,
            "oxide_grams": self.oxide_grams,
            "mix_ratio": self.mix_ratio,
            "time_min": self.time_min,
            "correctors": [c.as_dict() for c in self.correctors],
            "steps": [{"rule_id": s.rule_id, "text": s.text} for s in self.steps],
        }


@dataclass(frozen=True)
class ZonedFormula:
    """Full head formula split into zones."""

    zones: tuple[ZoneFormula, ...]
    steps: tuple[CalculationStep, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "zones", tuple(self.zones))
        object.__setattr__(self, "steps", tuple(self.steps))
        if not self.zones:
            raise ValueError("Формула должна содержать хотя бы одну зону")

    def zone(self, name: str) -> ZoneFormula | None:
        return next((z for z in self.zones if z.zone == name), None)

    def as_dict(self) -> dict[str, Any]:
        return {
            "zones": [z.as_dict() for z in self.zones],
            "steps": [{"rule_id": s.rule_id, "text": s.text} for s in self.steps],
        }
