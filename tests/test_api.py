from fastapi.testclient import TestClient

from colorist.api.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_calculate_endpoint():
    response = client.post(
        "/formula/calculate",
        json={
            "hair": {"root_level": 7, "length_level": 7, "grey_percent": 30, "has_keratin": False},
            "target": {"level": 7, "direction": "cool"},
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["oxide_percent"] == 6
    assert data["components"][0]["shade"] == "7/0"


def test_calculate_preserves_explicit_shade_code():
    response = client.post(
        "/formula/calculate",
        json={
            "hair": {"root_level": 7, "length_level": 7},
            "target": {"level": 7, "direction": "warm", "shade_code": "7.43"},
        },
    )
    assert response.status_code == 200
    assert response.json()["components"] == [{"shade": "7.43", "grams": 100.0}]


def test_calculate_rejects_invalid_zone_grams():
    response = client.post(
        "/formula/calculate",
        json={
            "hair": {"root_level": 7, "length_level": 6},
            "target": {"level": 6},
            "zoned": True,
            "root_grams": 0,
        },
    )
    assert response.status_code == 422


def test_calculate_rejects_non_finite_zone_grams():
    response = client.post(
        "/formula/calculate",
        json={
            "hair": {"root_level": 7, "length_level": 6},
            "target": {"level": 6},
            "zoned": True,
            "root_grams": "Infinity",
        },
    )
    assert response.status_code == 422


def test_check_endpoint():
    response = client.post(
        "/formula/check",
        json={
            "hair": {"root_level": 7, "length_level": 7, "grey_percent": 30, "has_keratin": False},
            "target": {"level": 7, "direction": "cool"},
            "master_formula": [{"shade": "7/3", "grams": 60}],
            "oxide_percent": 3,
        },
    )
    assert response.status_code == 200
    assert {x["rule_id"] for x in response.json()["risks"]} == {"C-COVERAGE", "C-OXIDE", "C-DIRECTION"}
