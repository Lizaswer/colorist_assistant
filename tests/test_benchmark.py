"""The optimisation described in docs/evaluation/optimization.md: identical
assistant requests are served from cache instead of a second LLM call."""

import pytest
from fastapi.testclient import TestClient

from colorist.api import assistant
from colorist.api.main import app

QUESTION = [{"role": "user", "content": "Почему выбран 6% оксид?"}]
CONTEXT = {"рассчитанная_формула": [{"shade": "7/0", "grams": 30}], "оксид": 6}


@pytest.fixture
def fake_llm(monkeypatch):
    """Replace the network call with a counter; no request leaves the machine."""
    calls: list[list[dict[str, str]]] = []

    def _fake(api_key, model, instructions, input_items):
        calls.append(input_items)
        return f"answer #{len(calls)}"

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(assistant, "_call_model", _fake)
    assistant.clear_cache()
    yield calls
    assistant.clear_cache()


def test_repeated_question_hits_cache(fake_llm):
    first = assistant.reply(QUESTION, CONTEXT)
    second = assistant.reply(QUESTION, CONTEXT)
    third = assistant.reply(QUESTION, CONTEXT)

    assert len(fake_llm) == 1, "3 identical requests must cost 1 LLM call"
    assert (first.cached, second.cached, third.cached) == (False, True, True)
    assert first.answer == second.answer == third.answer == "answer #1"


def test_different_context_is_a_cache_miss(fake_llm):
    assistant.reply(QUESTION, CONTEXT)
    other = assistant.reply(QUESTION, {**CONTEXT, "оксид": 3})
    assert len(fake_llm) == 2
    assert other.cached is False


def test_errors_are_not_cached(monkeypatch):
    attempts = {"n": 0}

    def _flaky(api_key, model, instructions, input_items):
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise RuntimeError("Внешний ИИ сейчас недоступен.")
        return "ok"

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(assistant, "_call_model", _flaky)
    assistant.clear_cache()
    with pytest.raises(RuntimeError):
        assistant.reply(QUESTION)
    assert assistant.reply(QUESTION).answer == "ok"
    assert attempts["n"] == 2
    assistant.clear_cache()


def test_cache_is_bounded(fake_llm, monkeypatch):
    monkeypatch.setattr(assistant, "CACHE_MAX_SIZE", 2)
    for i in range(3):
        assistant.reply([{"role": "user", "content": f"вопрос {i}"}])
    # The oldest entry was evicted, so asking it again costs a new call.
    assistant.reply([{"role": "user", "content": "вопрос 0"}])
    assert len(fake_llm) == 4


def test_chat_endpoint_reports_cache_status(fake_llm):
    client = TestClient(app)
    payload = {"messages": QUESTION, "context": CONTEXT}
    first = client.post("/assistant/chat", json=payload).json()
    second = client.post("/assistant/chat", json=payload).json()
    assert first == {"answer": "answer #1", "cached": False, "demo": False}
    assert second == {"answer": "answer #1", "cached": True, "demo": False}


@pytest.mark.parametrize(
    "status, code, expected",
    [
        (403, "unsupported_country_region_territory", "OPENAI_BASE_URL"),
        (401, None, "OPENAI_API_KEY"),
        (401, "expired_secret_key", "истёк"),
        (401, "expired_secret_key", "истёк"),
        (404, "model_not_found", "OPENAI_MODEL"),
        (429, None, "лимит"),
        (None, None, "соединения"),
        (500, None, "500"),
    ],
)
def test_api_errors_are_explained_without_leaking_details(status, code, expected):
    class FakeError(Exception):
        pass

    exc = FakeError("sk-secret should never appear")
    exc.status_code = status
    exc.code = code
    text = assistant._describe_api_error(exc, "gpt-4o-mini")
    assert expected in text
    assert "sk-secret" not in text


def test_chat_endpoint_demo_mode_without_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = TestClient(app)
    data = client.post("/assistant/chat", json={"messages": QUESTION}).json()
    assert data["demo"] is True
    assert "демонстрацион" in data["answer"].lower()
