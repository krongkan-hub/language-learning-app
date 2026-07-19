import pytest
from main import filter_coach_output, validate

# ---------------------------------------------------------------------------
# filter_coach_output tests
# ---------------------------------------------------------------------------

def test_no_op_filter():
    raw = '''💡 Feedback:
- You said: "I'll pay by card." → Better: "I'll pay by card."
- You said: "Hello." → Better: "Hello"
'''
    filtered = filter_coach_output(raw)
    assert "Perfectly natural!" in filtered

def test_duplicate_filter():
    raw = '''💡 Feedback:
- You said: "Is the drink so sweet?" → Better: "Is the drink very sweet?"
- You said: "Is the drink so sweet?" → Better: "Is the drink really sweet?"
'''
    filtered = filter_coach_output(raw)
    assert 'Better: "Is the drink very sweet?"' in filtered
    assert 'Better: "Is the drink really sweet?"' not in filtered

def test_parse_failure_passthrough():
    raw = '''💡 Feedback:
This sentence is mostly fine but you should say "Hi".
'''
    filtered = filter_coach_output(raw)
    # The substantive text should be passed through
    assert "This sentence is mostly fine" in filtered

def test_normalisation():
    raw = '''💡 Feedback:
You said: "hello" => Better: "Hi"
You said: “world” -> Better: "My World"
'''
    filtered = filter_coach_output(raw)
    assert 'You said: "hello" → Better: "Hi"' in filtered
    assert 'You said: "world" → Better: "My World"' in filtered

def test_preserves_level_up():
    raw = '''💡 Feedback:
You said: "hello" → Better: "hello"

⬆️ Level up:
- You could say "Howdy" instead.
'''
    filtered = filter_coach_output(raw)
    assert "Perfectly natural!" in filtered
    assert "⬆️ Level up:" in filtered
    assert "Howdy" in filtered


# ---------------------------------------------------------------------------
# validate tests
# ---------------------------------------------------------------------------

def test_validate_rejects_four_sentences_default():
    ok, reason = validate("A. B. C. D.")
    assert not ok
    assert "Too many sentences" in reason

def test_validate_accepts_three_sentences_default():
    ok, _ = validate("A. B. C.")
    assert ok

def test_validate_accepts_three_sentences_with_budget():
    ok, reason = validate("A. B. C.", max_sentences=4)
    assert ok

def test_validate_accepts_four_sentences_greeting():
    ok, _ = validate(
        "Welcome to Brew Haven! I'm Jake, your barista today. "
        "We just got some fresh pastries in. What can I get you?",
        max_sentences=4
    )
    assert ok

def test_validate_rejects_five_sentences_greeting():
    ok, reason = validate(
        "Welcome! I'm Jake. This is Brew Haven. We have pastries. "
        "What do you want?",
        max_sentences=4
    )
    assert not ok

def test_validate_rejects_empty():
    ok, _ = validate("")
    assert not ok

def test_validate_rejects_markup():
    ok, _ = validate("Hello *world*")
    assert not ok

def test_validate_rejects_emoji():
    ok, _ = validate("Hello ☕")
    assert not ok


# ---------------------------------------------------------------------------
# closed-question rejection tests
# ---------------------------------------------------------------------------

def test_validate_rejects_closed_yes_no():
    ok, reason = validate("Want a pastry to go with that?")
    assert not ok
    assert "Closed yes/no question" in reason

def test_validate_rejects_do_you_need():
    ok, reason = validate("Do you need anything else?")
    assert not ok
    assert "Closed yes/no question" in reason

def test_validate_accepts_or_question():
    ok, _ = validate("Would you rather have the tart or the croissant?")
    assert ok

def test_validate_accepts_wh_question():
    ok, _ = validate("Can you tell me what brought you in today?")
    assert ok

def test_validate_accepts_open_what():
    ok, _ = validate("What are you in the mood for?")
    assert ok

def test_validate_accepts_non_question():
    ok, _ = validate("Enjoy your coffee.")
    assert ok


if __name__ == '__main__':
    pytest.main(['-v', __file__])
