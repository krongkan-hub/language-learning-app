import pytest
from main import filter_coach_output

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

if __name__ == '__main__':
    pytest.main(['-v', __file__])
