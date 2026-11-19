from colorist.api.assistant import _demo_reply, _fallback_without_key, _context_block


def test_assistant_demo_mode_without_api_key_is_useful():
    text = _fallback_without_key([{"role": "user", "content": "Почему нужна натуральная база при 30% седины?"}])
    assert "демонстрацион" in text.lower()
    assert "седин" in text.lower()
    assert "калькулятор" in text.lower() or "rule-based" in text.lower()


def test_context_is_explicitly_non_authoritative_for_formula():
    text = _context_block({"рассчитанная_формула": [{"shade": "7/0", "grams": 30}]})
    assert "не пересчитывай сам" in text.lower()


def test_demo_reply_uses_current_formula_context():
    text = _demo_reply(
        "Почему здесь нужна натуральная база?",
        {
            "рассчитанная_формула": [{"shade": "7/0", "grams": 30}, {"shade": "7/1", "grams": 70}],
            "оксид": 6,
            "соотношение": "1:1",
            "выдержка_мин": 35,
        },
    )
    assert "7/0 — 30 г" in text
    assert "7/1 — 70 г" in text
    assert "оксид 6%" in text

