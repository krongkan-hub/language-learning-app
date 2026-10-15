"""Conjugating the verbs in the coach's tables, for the verb-form nets.

Only verbs the tables list are ever recognised: a pattern for "anything that
ends like a verb" matched 一つです and 山田ゆうです in review (#53).
"""
import re

from ..tables.japanese import _GODAN_VERBS, _ICHIDAN_VERBS

_I_ROW = dict(zip('うくぐすつぬぶむる', 'いきぎしちにびみり'))
_A_ROW = dict(zip('うくぐすつぬぶむる', 'わかがさたなばまら'))
_E_ROW = dict(zip('うくぐすつぬぶむる', 'えけげせてねべめれ'))
_TE_TAIL = {'う': 'って', 'つ': 'って', 'る': 'って', 'む': 'んで', 'ぶ': 'んで',
            'ぬ': 'んで', 'く': 'いて', 'ぐ': 'いで', 'す': 'して'}

VERB_CLASS = {**{v: 'ichidan' for v in _ICHIDAN_VERBS},
              **{v: 'godan' for v in _GODAN_VERBS},
              'する': 'suru', 'くる': 'kuru', '来る': 'kuru', 'いる': 'ichidan'}

_KANA_ONLY = re.compile('^[\u3041-\u3096]+$')
# What may sit right before a verb spelled in kana alone (ある, いる, わかる):
# without this, いる matches inside はいる and ある inside 歩ある.
_BEFORE_KANA_VERB = 'がはもをにでとへ、。 　'

# Longest first: a regex alternation takes the first branch that matches.
DICT_FORMS = sorted(VERB_CLASS, key=len, reverse=True)


def masu_stem(verb: str) -> str:
    kind = VERB_CLASS[verb]
    if kind == 'ichidan':
        return verb[:-1]
    if kind == 'suru':
        return 'し'
    if kind == 'kuru':
        return '来' if verb == '来る' else 'き'
    return verb[:-1] + _I_ROW[verb[-1]]


def te_form(verb: str) -> str:
    kind = VERB_CLASS[verb]
    if kind in ('ichidan', 'suru', 'kuru'):
        return masu_stem(verb) + 'て'
    if verb == '行く':
        return '行って'
    return verb[:-1] + _TE_TAIL[verb[-1]]


def ta_form(verb: str) -> str:
    te = te_form(verb)
    return te[:-1] + ('だ' if te.endswith('で') else 'た')


def nai_form(verb: str) -> str:
    kind = VERB_CLASS[verb]
    if verb == 'ある':
        return 'ない'
    if kind == 'ichidan':
        return verb[:-1] + 'ない'
    if kind == 'suru':
        return 'しない'
    if kind == 'kuru':
        return '来ない' if verb == '来る' else 'こない'
    return verb[:-1] + _A_ROW[verb[-1]] + 'ない'


def ba_form(verb: str) -> str:
    kind = VERB_CLASS[verb]
    if kind == 'suru':
        return 'すれば'
    if kind == 'kuru':
        return '来れば' if verb == '来る' else 'くれば'
    if kind == 'ichidan':
        return verb[:-1] + 'れば'
    return verb[:-1] + _E_ROW[verb[-1]] + 'ば'


def standalone(text: str, start: int, verb: str) -> bool:
    """False when a kana-only verb is really the tail of a longer word."""
    if not _KANA_ONLY.match(verb):
        return True
    before = text[:start][-1:]
    if verb == 'する' and re.match('[\u4e00-\u9fff\u30a0-\u30ff]', before):
        return True              # 勉強する, コピーする
    return not before or before in _BEFORE_KANA_VERB


def dict_form_pattern() -> str:
    return '(?P<verb>' + '|'.join(DICT_FORMS) + ')'


# The ます stem back to its dictionary form, for the forms a learner puts
# where a plain form belongs (降りますと思います). A stem two verbs share —
# 降り is 降る and 降りる — is left out: which one the learner meant is not
# something a net can know, so it stays silent there.
def _stems():
    seen = {}
    for verb in VERB_CLASS:
        seen.setdefault(masu_stem(verb), []).append(verb)
    return {s: vs[0] for s, vs in seen.items() if len(vs) == 1}


STEM_TO_DICT = _stems()
