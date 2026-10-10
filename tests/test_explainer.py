"""Объяснение: защита от искажения цифр и откат на шаблон."""

from colorist.api.explainer import build_prompt, explain, find_foreign_numbers
from colorist.rules import Direction, HairState, Target, calculate_formula

FORMULA = calculate_formula(
    HairState(root_level=7, length_level=7, grey_percent=30),
    Target(level=7, direction=Direction.COOL),
)


def test_numbers_from_prompt_are_allowed():
    prompt = build_prompt(FORMULA)
    assert find_foreign_numbers(prompt, "Время 45 мин, оксид 6.0%, седина 30%") == set()


def test_invented_number_is_detected():
    prompt = build_prompt(FORMULA)
    assert find_foreign_numbers(prompt, "Выдержка 50 мин") == {"50"}


def test_list_numbering_is_ignored():
    assert find_foreign_numbers("45 мин", "1. Выдержка 45 мин\n2. Готово") == set()


def test_default_mode_is_template(monkeypatch):
    monkeypatch.delenv("COLORIST_USE_LLM", raising=False)
    assert "R-OX-GREY" in explain(FORMULA)


def test_llm_failure_falls_back_to_template(monkeypatch):
    monkeypatch.setenv("COLORIST_USE_LLM", "1")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert "R-OX-GREY" in explain(FORMULA)


# ---- кэш ответов модели ----

def _count_calls(monkeypatch, answer_fn):
    """Подменяет вызов модели и считает, сколько раз он случился."""
    from colorist.api import explainer, llm

    explainer._ask_cached.cache_clear()
    calls = {"n": 0}

    def fake_complete(system, prompt, **kwargs):
        calls["n"] += 1
        return answer_fn(prompt)

    monkeypatch.setenv("COLORIST_USE_LLM", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "fake")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("COLORIST_LLM_CACHE", raising=False)
    monkeypatch.setattr(llm, "complete", fake_complete)
    return calls


def test_cache_calls_model_once_for_same_formula(monkeypatch):
    calls = _count_calls(monkeypatch, lambda prompt: "Выдержка 45 мин")
    first, second = explain(FORMULA), explain(FORMULA)
    assert first == second == "Выдержка 45 мин"
    assert calls["n"] == 1


def test_cache_can_be_disabled(monkeypatch):
    calls = _count_calls(monkeypatch, lambda prompt: "Выдержка 45 мин")
    monkeypatch.setenv("COLORIST_LLM_CACHE", "0")
    explain(FORMULA), explain(FORMULA)
    assert calls["n"] == 2


def test_bad_answer_is_not_cached(monkeypatch):
    calls = _count_calls(monkeypatch, lambda prompt: "Выдержка 99 мин")
    assert "R-OX-GREY" in explain(FORMULA)   # откат на шаблон
    explain(FORMULA)
    assert calls["n"] == 2                    # модель спрошена снова, искажённый ответ не закэширован