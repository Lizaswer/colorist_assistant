"""Модели данных модуля правил.

Здесь только описание данных — никакой логики. Поля совпадают с карточкой
эталонного случая из гайда для интервью, чтобы реальные случаи колористов
можно было напрямую превращать в тесты.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Porosity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Direction(str, Enum):
    """Направление желаемого оттенка (упрощённо для MVP)."""

    NATURAL = "natural"  # натуральный, /0
    COOL = "cool"        # холодный, пепельный /1
    WARM = "warm"        # тёплый, золотистый /3


class Service(str, Enum):
    """Тип услуги. Осветления в MVP нет."""

    TONE_ON_TONE = "tone_on_tone"
    DARKER = "darker"


@dataclass
class HairState:
    """Исходное состояние волос клиента."""

    root_level: int                  # уровень тона у корней, 1–10
    length_level: int                # уровень по длине, 1–10
    grey_percent: int = 0            # процент седины, 0–100
    porosity: Porosity = Porosity.MEDIUM
    has_henna: bool = False          # хна или басма в истории
    has_keratin: bool = False        # кератин / ботокс за последние месяцы


@dataclass
class Target:
    """Желаемый результат."""

    level: int
    direction: Direction


@dataclass
class Component:
    """Один оттенок в формуле, например 7/1, 30 г."""

    shade: str
    grams: int


@dataclass
class Note:
    """Шаг объяснения или предупреждение.

    rule_id связывает каждое решение с конкретным правилом из knowledge.py —
    это и есть «объяснимость» системы.
    """

    rule_id: str
    text: str


@dataclass
class Formula:
    service: Service
    components: list[Component]
    oxide_percent: float
    mix_ratio: str                   # краситель : оксид, например "1:1"
    time_min: int
    steps: list[Note] = field(default_factory=list)
    warnings: list[Note] = field(default_factory=list)


@dataclass
class MasterFormula:
    """Формула, которую составил мастер, — для режима проверки."""

    components: list[Component]
    oxide_percent: float
