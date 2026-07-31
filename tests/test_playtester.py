import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.ai_playtester import playtest_task, clean_msg
from app.scenarios.builtins import SCENARIOS

def test_clean_msg():
    raw = '  "Hello *waves hand* world!"  '
    cleaned = clean_msg(raw)
    assert cleaned == "Hello  world!"

def test_ai_playtester_module_importable():
    from scripts.ai_playtester import LEARNER_SYS, playtest_task
    assert "LEARNER_SYS" in locals() or LEARNER_SYS is not None
    assert callable(playtest_task)

def test_ai_playtester_runs_single_turn_mock(monkeypatch):
    scenario = SCENARIOS[0]
    task = scenario.tasks[0]
    
    # Mock LLM calls to test playtest_task flow deterministically in pytest
    def mock_llm_chat(messages, options):
        return {'message': {'content': "Hello, I am looking for a black coffee."}}

    def mock_call_actor(messages, system_prompt, speaker=None, max_sentences=3):
        return "Welcome to our coffee shop! What can I get for you today?"

    monkeypatch.setattr("scripts.ai_playtester._llm_chat", mock_llm_chat)
    monkeypatch.setattr("scripts.ai_playtester.call_actor", mock_call_actor)

    success, history = playtest_task(scenario, task, max_attempts=1)
    assert isinstance(success, bool)
    assert len(history) > 0
