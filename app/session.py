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
