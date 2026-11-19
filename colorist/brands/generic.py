from __future__ import annotations

from colorist.brands.base import BrandProfile
from colorist.rules.knowledge import DIRECTION_TONE, NATURAL_TONE
from colorist.rules.models import Direction

#: The original brand-agnostic MVP profile. Kept so the original demo, tests
#: and reference cases keep working exactly as before.
GENERIC_PROFILE = BrandProfile(
    key="generic",
    name="Универсальный MVP",
    tones=DIRECTION_TONE,
    natural_tone=NATURAL_TONE,
    mix_ratio="1:1",
    time_min=35,
    time_max=40,
    default_oxide=3.0,
    grey_oxide=6.0,
    high_grey_oxide=6.0,
    available_oxides=(3.0, 6.0, 9.0),
    levels=tuple(range(1, 11)),
    tone_codes=("0", "1", "3"),
    validate_catalog=False,
    max_darkening_levels=2,
    supports_lightening=False,
    notes="Базовый профиль без привязки к бренду. Значения — допущения MVP.",
)
