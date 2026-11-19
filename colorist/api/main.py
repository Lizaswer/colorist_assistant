from __future__ import annotations

from pathlib import Path

from colorist.logging_config import get_logger, setup_logging

setup_logging()
_log = get_logger("api")

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, FiniteFloat, model_validator

from colorist import __version__
from colorist.api.explainer import explain
from colorist.api.assistant import reply as assistant_reply
from colorist.brands import DEFAULT_BRAND, list_brands, resolve_profile
from colorist.brands.engine import (
    ZONE_LABELS,
    calculate_formula,
    calculate_zoned_formula,
    check_formula,
)
from colorist.rules import (
    Component,
    Direction,
    Formula,
    HairState,
    MasterFormula,
    Target,
    ZonedFormula,
)
from colorist.rules.errors import CalculationError

app = FastAPI(title="Colorist Assistant", version=__version__)
STATIC = Path(__file__).parent / "static"


class HairIn(BaseModel):
    root_level: int = Field(ge=1, le=12)
    length_level: int = Field(ge=1, le=12)
    grey_percent: int = Field(default=0, ge=0, le=100)
    has_keratin: bool = False


class TargetIn(BaseModel):
    level: int = Field(ge=1, le=12)
    direction: Direction = Direction.NEUTRAL
    shade_code: str | None = Field(
        default=None,
        max_length=12,
        pattern=r"^\d{1,2}[/.][0-9A-Za-z]+$",
    )

    @model_validator(mode="after")
    def validate_shade_level(self):
        if self.shade_code:
            shade_level = int(self.shade_code.replace("/", ".").split(".", 1)[0])
            if shade_level != self.level:
                raise ValueError("Уровень в коде оттенка должен совпадать с целевым уровнем")
        return self


class CalculateIn(BaseModel):
    hair: HairIn
    target: TargetIn
    brand: str | None = None
    line: str | None = None
    root_grams: FiniteFloat | None = Field(default=None, gt=0)
    length_grams: FiniteFloat | None = Field(default=None, gt=0)
    zoned: bool = False


class ComponentIn(BaseModel):
    shade: str = Field(min_length=1, max_length=32)
    grams: FiniteFloat = Field(gt=0)


class AssistantMessage(BaseModel):
    role: str
    content: str = Field(min_length=1, max_length=12000)


class AssistantIn(BaseModel):
    messages: list[AssistantMessage] = Field(default_factory=list, max_length=30)
    context: dict | None = None


class CheckIn(BaseModel):
    hair: HairIn
    target: TargetIn
    master_formula: list[ComponentIn] = Field(min_length=1)
    oxide_percent: FiniteFloat = Field(gt=0)
    brand: str | None = None
    line: str | None = None


def _hair(value: HairIn) -> HairState:
    return HairState(**value.model_dump())


def _target(value: TargetIn) -> Target:
    data = {"level": value.level, "direction": value.direction}
    if value.shade_code:
        data["shade_code"] = value.shade_code
    return Target(**data)


def _flatten_zoned(zoned: ZonedFormula) -> Formula:
    """Merge zones into a flat formula for backwards compat."""
    components = []
    oxides = []
    for z in zoned.zones:
        components.extend(z.components)
        oxides.append(z.oxide_percent)
    return Formula(
        components=tuple(components),
        oxide_percent=round(sum(oxides) / len(oxides), 1) if oxides else 0,
        mix_ratio=zoned.zones[0].mix_ratio if zoned.zones else "1:1",
        time_min=max(z.time_min for z in zoned.zones) if zoned.zones else 35,
        steps=zoned.steps,
    )


def explain_zoned(zoned: ZonedFormula) -> str:
    lines = ["Зональный расчёт:"]
    for z in zoned.zones:
        lines.append(f"  {ZONE_LABELS.get(z.zone, z.zone)}:")
        for c in z.components:
            lines.append(f"    {c.shade}: {c.grams} г")
        lines.append(f"    Оксид {z.oxide_percent:g}% ({z.oxide_grams:g} г), {z.mix_ratio}, {z.time_min} мин")
        for c in z.correctors:
            lines.append(f"    Корректор {c.shade}: {c.cm:g} см")
    for s in zoned.steps:
        lines.append(f"  [{s.rule_id}] {s.text}")
    return "\n".join(lines)


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (STATIC / "index.html").read_text(encoding="utf-8")


@app.get("/brands")
def brands():
    return {"brands": list_brands()}


@app.post("/formula/calculate")
def calculate(payload: CalculateIn):
    _log.info("POST /formula/calculate brand=%s line=%s zoned=%s", payload.brand, payload.line, payload.zoned)
    try:
        profile = resolve_profile(payload.brand, payload.line)
        hair = _hair(payload.hair)
        target = _target(payload.target)
        zoned = None
        if payload.zoned:
            zoned = calculate_zoned_formula(
                profile,
                hair,
                target,
                root_grams=payload.root_grams,
                length_grams=payload.length_grams,
            )
            formula = _flatten_zoned(zoned)
        else:
            formula = calculate_formula(profile, hair, target)
    except (CalculationError, ValueError, KeyError) as exc:
        _log.warning("calculate rejected: %s", exc)
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    body = {
        "components": [{"shade": c.shade, "grams": c.grams} for c in formula.components],
        "oxide_percent": formula.oxide_percent,
        "mix_ratio": formula.mix_ratio,
        "time_min": formula.time_min,
        "steps": [{"rule_id": s.rule_id, "text": s.text} for s in formula.steps],
        "explanation": explain(formula),
        "brand": payload.brand or DEFAULT_BRAND,
        "line": profile.key,
        "line_name": profile.name,
    }
    if zoned is not None:
        body["zones"] = zoned.as_dict()["zones"]
        body["steps"] = [{"rule_id": s.rule_id, "text": s.text} for s in zoned.steps]
        body["explanation"] = explain_zoned(zoned)
    return body


@app.post("/formula/check")
def check(payload: CheckIn):
    try:
        profile = resolve_profile(payload.brand, payload.line)
        master = MasterFormula(
            [Component(c.shade, c.grams) for c in payload.master_formula],
            payload.oxide_percent,
        )
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    risks = check_formula(profile, _hair(payload.hair), _target(payload.target), master)
    return {"risks": [risk.as_dict() for risk in risks]}


@app.post("/assistant/chat")
def assistant(payload: AssistantIn):
    messages = [m.model_dump() for m in payload.messages]
    try:
        result = assistant_reply(messages, payload.context)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"answer": result.answer, "cached": result.cached, "demo": result.demo}


@app.get("/health")
def health():
    return {"status": "ok"}
