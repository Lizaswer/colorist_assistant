"""API: проверка эндпоинтов через тестовый клиент FastAPI."""

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from colorist.api.main import app  # noqa: E402

client = TestClient(app)

HAIR = {"root_level": 7, "length_level": 7, "grey_percent": 30}
TARGET = {"level": 7, "direction": "cool"}


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_calculate_returns_formula_and_explanation():
    response = client.post("/formula/calculate", json={"hair": HAIR, "target": TARGET})
    assert response.status_code == 200
    body = response.json()
    assert body["formula"]["oxide_percent"] == 6.0
    assert "R-OX-GREY" in body["explanation"]


def test_calculate_lightening_is_422():
    response = client.post(
        "/formula/calculate",
        json={"hair": HAIR, "target": {"level": 9, "direction": "natural"}},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["rule_id"] == "R-SCOPE-LIGHTEN"


def test_check_finds_risks():
    response = client.post(
        "/formula/check",
        json={
            "hair": HAIR,
            "target": TARGET,
            "formula": {"components": [{"shade": "7/0", "grams": 60}], "oxide_percent": 3},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert {r["rule_id"] for r in body["risks"]} >= {"C-OX-GREY", "C-WARM-NO-ASH"}


def test_index_page_is_served():
    response = client.get("/")
    assert response.status_code == 200
    assert "Ассистент колориста" in response.text
