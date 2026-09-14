"""Explain mode: the learner explains something and someone listens.

The roleplay scenarios ask for short transactional turns — a request, a
question, a reply. This mode asks for sustained output: several sentences that
hold together, with sequencing and connectives, which is a different muscle.

The mechanic that makes it work is the listener NOT understanding. When a point
lands vaguely the listener asks about exactly what is missing, and the learner
has to say it again in different words. That is circumlocution practice, and it
buys a second round of output from one moment of confusion.

## Two measured facts this module is built on

**The instruction must be written in the language being studied.** With an
English instruction over Japanese content, the listener asked back on 5 of 6
CLEAR answers — the failure that makes the mode a nag. With the instruction in
Japanese: 2 of 6. English content with an English instruction: 0 of 6.

**Do not split the decision into a bare yes/no call.** It was tried, on the
theory that deciding and replying are two jobs. A tiny "does this tell you X?
YES or NO" call answered YES to almost everything — it let 5 of 6 vague
answers through, the same shape this project already recorded when a 1.5B
judge returned 24/24 false positives. The listener decides and replies in one
call.

A turn here costs TWO model calls, not three: the listener's verdict replaces
the task judge, because deciding whether the point landed IS the grading.
"""
from typing import List, Optional
import json
import os
import re

from .llm import _llm_chat, strip_think_tags, find_wrong_script

LISTENER_OPTS = {'temperature': 0.3, 'num_predict': 120}

# Written per language rather than translated at runtime, for the reason
# measured above: the instruction's own language decides whether the listener
# nags. A runtime translation of this prompt would also put it through
# translate_hints, whose output is 40% wrong (OPEN-42).
LISTENER_SYS = {
    'English': (
        "You are {listener}. Someone is explaining something to you and you "
        "genuinely do not know it.\n\n"
        "THEY ARE EXPLAINING: {topic}\n"
        "THE ONE POINT YOU ARE LISTENING FOR: {point}\n\n"
        "Read what they just said and decide one thing: is that point clear to "
        "you now?\n"
        "- If it IS clear, write CLEAR on the first line, then one short natural "
        "sentence in English showing you followed.\n"
        "- If it is NOT clear, write ASK on the first line, then ONE short "
        "natural question in English about exactly what is missing.\n\n"
        "Never correct their grammar — someone else does that. Never explain it "
        "back to them. You are the one who does not know."
    ),
    'Japanese': (
        "あなたは{listener}です。相手があなたに何かを説明しています。あなたは"
        "それを本当に知りません。\n\n"
        "相手が説明していること：{topic}\n"
        "あなたが今聞き取りたい点：{point}\n\n"
        "相手の発言を読んで、一つだけ判断してください。その点はもう分かりましたか。\n"
        "- 分かった場合：一行目に CLEAR とだけ書き、次の行に短い自然な相づちを"
        "日本語で書いてください。\n"
        "- まだ分からない場合：一行目に ASK とだけ書き、次の行に足りない点を聞く"
        "短い質問を日本語で一つだけ書いてください。\n\n"
        "文法は直さないでください。それは別の人の仕事です。説明し返さないで"
        "ください。分からないのはあなたです。"
    ),
}

_VERDICT = re.compile(r'^\s*(CLEAR|ASK)\b[:：]?\s*', re.IGNORECASE)

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'explain_topics.json')


class ExplainTopic:
    """A thing to explain, and the points the listener must end up understanding."""

    def __init__(self, raw: dict):
        self.id = raw['id']
        self._title = raw['title']
        self._points = raw['points']
        self._listener = raw['listener']

    def title(self, language: str) -> str:
        return self._title.get(language, self._title['English'])

    def points(self, language: str) -> List[str]:
        return self._points.get(language, self._points['English'])

    def listener(self, language: str) -> str:
        return self._listener.get(language, self._listener['English'])

    def __repr__(self):
        return f'<ExplainTopic {self.id}>'


def load_topics(path: Optional[str] = None) -> List[ExplainTopic]:
    with open(path or DATA, encoding='utf-8') as fh:
        return [ExplainTopic(raw) for raw in json.load(fh)]


def listener_system_prompt(topic: ExplainTopic, point: str, language: str) -> str:
    """The listener's instruction, in the language being studied."""
    template = LISTENER_SYS.get(language)
    if template is None:
        raise ValueError(f'explain mode has no listener prompt for {language!r}')
    return template.format(listener=topic.listener(language),
                           topic=topic.title(language), point=point)


def listen(topic: ExplainTopic, point: str, learner_text: str,
           language: str, history: Optional[list] = None):
    """One listener turn. Returns (point_is_clear, what the listener says).

    Falls back to accepting the point when the model gives no usable verdict:
    a learner stuck on a point the listener will not grant cannot progress, and
    this mode has no skip. Being too generous costs a missed practice
    opportunity; being stuck costs the session.
    """
    messages = [{'role': 'system',
                 'content': listener_system_prompt(topic, point, language)}]
    messages += (history or [])
    messages.append({'role': 'user', 'content': learner_text})

    try:
        raw = strip_think_tags(
            _llm_chat(messages=messages, options=LISTENER_OPTS)['message']['content'])
    except Exception:
        return True, ''

    lines = [l.strip() for l in raw.strip().split('\n') if l.strip()]
    if not lines:
        return True, ''

    match = _VERDICT.match(lines[0])
    if match:
        verdict = match.group(1).upper()
        rest = _VERDICT.sub('', lines[0]).strip()
        spoken = ' '.join([rest] + lines[1:]).strip()
    else:
        # No verdict marker. A question mark is the honest tell that the
        # listener did not follow; anything else is treated as acceptance.
        verdict = 'ASK' if re.search(r'[?？]', raw) else 'CLEAR'
        spoken = ' '.join(lines).strip()

    # The same guard every other Japanese surface gets. A listener replying in
    # Chinese is worse than a listener saying nothing.
    if find_wrong_script(spoken, language):
        return True, ''
    return verdict == 'CLEAR', spoken
