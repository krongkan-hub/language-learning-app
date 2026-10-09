"""Practise your own mistakes: a short session built from the corrections the
coach has made to THIS learner.

The coach has logged every correction since OPEN-34 (app/db/mistakes.py),
and the dashboard shows the ones that repeat — but nothing asked the learner
to use the right form again. This turns the most-repeated corrections into
a small scenario: a relaxed chat with a friend, where each task is "use
'two bottles' correctly", hinted with what they wrote last time.

Everything downstream is the ordinary scenario path: the NPC, the coach, the
drill and the summary. Each task's done_when is shaped "Learner used the word
'X'", so the judge decides it deterministically (English by word match,
Japanese through vocab_translations) and no extra model call is spent.
"""
from typing import Optional

from .scenarios.models import Scenario, Task

REVIEW_SCENARIO = 'Practice Your Mistakes'   # the database key, like any scenario's name
MAX_TASKS = 5
# A correction the learner can be asked to say again has to be a phrase, not
# a rewritten paragraph: "two bottles", 「値段を教えて」 — not a whole sentence
# the coach rephrased.
_MAX_WORDS = 6
_MAX_JA_CHARS = 16


def _usable(correction: Optional[str], language: str) -> bool:
    if not correction or not correction.strip():
        return False
    text = correction.strip()
    if language == 'Japanese':
        return len(text) <= _MAX_JA_CHARS
    return len(text.split()) <= _MAX_WORDS


def _task(was: str, fix: str, language: str) -> Task:
    fix = fix.strip().rstrip('.。!?！？')
    return Task(
        goal=f'Use “{fix}” correctly',
        hint=f'Last time you wrote “{was}”. Say it the right way this time: “{fix}”.',
        done_when=f"Learner used the word '{fix}'.",
        difficulty='standard', phase=2,
        # Japanese: the judge's deterministic path reads the accepted forms here
        vocab_translations={'Japanese': [fix]} if language == 'Japanese' else {},
        translations={'Japanese': {
            'goal': f'「{fix}」を正しく使う',
            'hint': f'前は「{was}」と書きました。今度は「{fix}」を使って言ってみましょう。'}},
    )


def review_items(mistakes: list, language: str) -> list:
    """The corrections a review session would practise, in order: what the
    learner wrote and the fix, most-repeated first, short phrases only, each
    fix once. The Today page shows exactly these, so its "Up next" never
    promises a mistake the session would then leave out."""
    items, seen = [], set()
    for m in mistakes:
        fix = (m.get('example_correction') or '').strip()
        was = (m.get('example_quoted') or '').strip()
        if not _usable(fix, language) or fix.lower() in seen or not was:
            continue
        seen.add(fix.lower())
        items.append({'was': was, 'fix': fix, 'occurrences': m.get('occurrences', 1)})
        if len(items) == MAX_TASKS:
            break
    return items


def build_review_scenario(mistakes: list, language: str) -> Optional[Scenario]:
    """A scenario from the learner's mistakes (most-repeated first), or None
    when none of them is a phrase short enough to practise."""
    tasks = [_task(i['was'], i['fix'], language) for i in review_items(mistakes, language)]
    if not tasks:
        return None
    return Scenario(
        name=REVIEW_SCENARIO,
        place='A quiet café, catching up with a friend',
        role='You are the learner\'s friend, chatting over coffee about their week. '
             'Keep the conversation easy and personal, and ask about what they have been doing.',
        speaker='Friend',
        tasks=tasks,
        complications=[],
        name_translations={'Japanese': '間違えたところを練習'},
        place_translations={'Japanese': '静かなカフェで友達とおしゃべり'},
    )
