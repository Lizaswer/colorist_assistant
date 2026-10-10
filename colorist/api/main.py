"""HTTP API на FastAPI.

Запуск:  uvicorn colorist.api.main:app --reload
Интерфейс для мастера:            http://127.0.0.1:8000/
Документация API с формами:       http://127.0.0.1:8000/docs
С телефона в той же Wi-Fi сети:   uvicorn colorist.api.main:app --host 0.0.0.0
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from colorist.rules import (
    Formula,
    HairState,
    MasterFormula,
    Note,
    OutOfScopeError,
    Target,
    calculate_formula,
    check_formula,
)

from .explainer import explain

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="ИИ-ассистент колориста", version="0.1.0")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    """Веб-интерфейс: анкета → формула с объяснением → проверка своей формулы."""
    return FileResponse(STATIC_DIR / "index.html")


class CalculateRequest(BaseModel):
    hair: HairState
    target: Target


class CalculateResponse(BaseModel):
    formula: Formula
    explanation: str


class CheckRequest(BaseModel):
    hair: HairState
    target: Target
    formula: MasterFormula


class CheckResponse(BaseModel):
    ok: bool
    risks: list[Note]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/formula/calculate", response_model=CalculateResponse)
def calculate(request: CalculateRequest) -> CalculateResponse:
    try:
        formula = calculate_formula(request.hair, request.target)
    except OutOfScopeError as error:
        raise HTTPException(422, {"rule_id": error.rule_id, "message": str(error)})
    except ValueError as error:
        raise HTTPException(422, {"message": str(error)})
    return CalculateResponse(formula=formula, explanation=explain(formula))


@app.post("/formula/check", response_model=CheckResponse)
def check(request: CheckRequest) -> CheckResponse:
    try:
        risks = check_formula(request.hair, request.target, request.formula)
    except ValueError as error:
        raise HTTPException(422, {"message": str(error)})
    return CheckResponse(ok=not risks, risks=risks)
