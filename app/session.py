from typing import Optional, Union, Callable
from app.llm import GREETING_SYS, ACTOR_SYS, build_task_setup_block, call_actor
from app.scenarios.models import Scenario, Task

GREETING_MAX_SENTENCES = 4
ACTOR_MAX_SENTENCES = 3


def _build_complication_block(complication: Optional[str]) -> str:
    return f" Also, there is a minor issue today: {complication}." if complication else ""


def build_greeting_system_prompt(
    scenario: Scenario,
    task: Union[Task, str],
    language: str = 'English',
    mood: str = 'neutral',
    complication: Optional[str] = None
) -> str:
    """Build the greeting system prompt for a scenario and task."""
    if isinstance(task, str):
        task_setup = task
    elif hasattr(task, 'goal'):
        task_setup = build_task_setup_block(task)
    else:
        task_setup = str(task)

    return GREETING_SYS.format(
        place=scenario.place,
        role=scenario.role,
        language=language,
        mood=mood,
        complication=_build_complication_block(complication),
        task_setup=task_setup
    )


def build_actor_system_prompt(
    scenario: Scenario,
    task: Union[Task, str],
    language: str = 'English',
    mood: str = 'neutral',
    complication: Optional[str] = None
) -> str:
    """Build the actor system prompt for a scenario and task."""
    if isinstance(task, str):
        task_setup = task
    elif hasattr(task, 'goal'):
        task_setup = build_task_setup_block(task)
    else:
        task_setup = str(task)

    return ACTOR_SYS.format(
        place=scenario.place,
        role=scenario.role,
        language=language,
        mood=mood,
        complication=_build_complication_block(complication),
        task_setup=task_setup
    )


# How many messages of conversation history the actor sees. The full list is
# kept — the judge slices it by absolute index (`messages[task_start_idx:]`) and
# the session log needs it whole — so only the actor's view is bounded.
#
# It was unbounded, and a Japanese ACTOR_SYS prompt starts at 853 tokens and
# grows about 49 per turn, crossing PROMPT_CACHE_MAX_KV_SIZE (4096) around turn
# 67 against a 69-task scenario. Past that the KV cache stops being trimmable
# and is rebuilt every turn, on top of a turn that already costs ~9-11s
# (OPEN-20). 20 messages is ten exchanges, which keeps the prompt near 1,300
# tokens for a whole session while leaving the NPC more recent context than it
# can usually use — the scenario, role and task live in the system prompt, not
# in the history.
ACTOR_HISTORY_MESSAGES = 20


def recent_history(messages: list, limit: int = ACTOR_HISTORY_MESSAGES) -> list:
    """The last `limit` messages, as the actor's view of the conversation."""
    if limit <= 0 or len(messages) <= limit:
        return messages
    return messages[-limit:]


def produce_actor_turn(
    messages: list,
    system_prompt: str,
    speaker: Optional[str] = None,
    max_sentences: int = ACTOR_MAX_SENTENCES,
    actor_fn: Optional[Callable] = None,
    **kwargs
) -> str:
    """Produce one actor turn using actor_fn (defaults to call_actor), enforcing the sentence budget."""
    kwargs.pop('max_sentences', None)
    if actor_fn is None:
        actor_fn = call_actor
    return actor_fn(messages, system_prompt, speaker=speaker, max_sentences=max_sentences, **kwargs)


def produce_greeting_turn(
    messages: list,
    system_prompt: str,
    speaker: Optional[str] = None,
    max_sentences: int = GREETING_MAX_SENTENCES,
    actor_fn: Optional[Callable] = None,
    **kwargs
) -> str:
    """Produce initial greeting turn using GREETING_MAX_SENTENCES budget."""
    kwargs.pop('max_sentences', None)
    return produce_actor_turn(
        messages,
        system_prompt,
        speaker=speaker,
        max_sentences=max_sentences,
        actor_fn=actor_fn,
        **kwargs
    )
