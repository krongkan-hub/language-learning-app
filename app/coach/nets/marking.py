"""Topic and particle slips the case-particle net does not read: a question
word as topic (どこは痛いですか), も stacked on は/が (私はも), a clock time
without に (七時起きます), an owner without の (私本).

All four were called natural by the model on the held-out eval (issue #40,
dev/evals/eval_jalearner.py).

Only ever overturns a CLEAN verdict — a real model correction always wins.
"""
import re

from ..tables.japanese import (_CLOCK_VERB_STEMS, _I_ADJECTIVES, _OWNED, _OWNERS,
                               _WH_WORDS)
from ..verdict import is_clean_verdict
from .ja_text import _CLAUSE_END

# A question word takes が, never は. Fixed to が only where が is certainly
# the particle meant: 誰 with the clause's を already there (誰はかばんを忘れ
# ましたか — 誰 is the subject), or a predicate that is a listed い-adjective
# or a noun/な-adjective + です (どこは痛いですか, 誰は先生ですか). A verb in
# たい/ない is not an adjective here: どこは行きたくないですか wants どこに,
# 何は食べたいですか wants 何を, and どこは本を買いますか wants どこで.
_WH_WA = re.compile(
    '(?:^|(?<=[、。！？!?\\s]))(?P<wh>' + '|'.join(_WH_WORDS) + ')は')
_WH_AGENTS = ('誰', 'だれ')
_PREDICATE = re.compile('(?P<pred>.*?)(?:です|でした)?か?[よね]?$')


def _adjective_or_noun_predicate(clause: str) -> bool:
    pred = _PREDICATE.match(clause).group('pred')
    if not pred or pred.endswith(('ない', 'たい', 'なかった', 'たかった')):
        return False
    if pred.endswith(('い', 'かった')):
        return pred.endswith(_I_ADJECTIVES)
    return clause.endswith(('です', 'ですか', 'でした', 'でしたか'))

# 私はも / シャツがも: も replaces は and が. Only before a kanji, a katakana
# word or ほしい, because はもう, はもっと, はもちろん and がもらえる are all
# correct. Not before 少し or 一度 either: 今日はも少し is a casual もう少し.
_MO_STACK = re.compile(
    '(?P<noun>[^\\s、。「」『』！？!?をはがにでともへや]{1,8})(?P<p>[はが])も'
    '(?=[\\u4e00-\\u9fff\\u30a0-\\u30ff]|ほしい)(?!少し|一度|一回|一つ|一人)')

_NUM = '[0-9０-９一二三四五六七八九十]+'
_CLOCK_NO_NI = re.compile(
    '(?P<time>' + _NUM + '時(?:半|' + _NUM + '分)?)'
    '(?P<verb>(?:' + '|'.join(sorted(_CLOCK_VERB_STEMS, key=len, reverse=True)) + ')'
    '(?=ま|る|た|て|ない)[^\\s、。！？!?]*)')

# Only in これは〜です: elsewhere 私車で来ました is 私、車で来ました with the
# comma dropped, and 私車が好き is casual for 私は車が好き.
_OWNER_NO_NO = re.compile(
    '(?<=これは|それは|あれは)'
    '(?P<owner>' + '|'.join(sorted(_OWNERS, key=len, reverse=True)) + ')'
    '(?P<owned>' + '|'.join(sorted(_OWNED, key=len, reverse=True)) + ')'
    '(?=です|でした|じゃ|では)')


def _clause_end(text: str, start: int) -> int:
    cuts = [text.find(c, start) for c in _CLAUSE_END]
    cuts = [c for c in cuts if c != -1]
    return min(cuts) if cuts else len(text)


def _short(clause_wrong, clause_right, pair_wrong, pair_right):
    """The clause when it is short enough to retype, else the bare pair —
    the drill asks the learner to type the ✅ side back."""
    if len(clause_wrong) <= 14:
        return clause_wrong, clause_right
    return pair_wrong, pair_right


def marking_error(text: str):
    """(wrong, right, reason) for the first topic/particle slip, or None."""
    for match in _WH_WA.finditer(text):
        wh = match.group('wh')
        clause = text[match.end():_clause_end(text, match.end())]
        if (wh in _WH_AGENTS and 'を' in clause) or _adjective_or_noun_predicate(clause):
            wrong, right = _short(f'{wh}は{clause}', f'{wh}が{clause}', f'{wh}は', f'{wh}が')
            return (wrong, right, f'疑問詞「{wh}」は「は」ではなく「が」で示します')

    match = _MO_STACK.search(text)
    if match:
        noun, p = match.group('noun'), match.group('p')
        clause = text[match.end():_clause_end(text, match.end())]
        wrong, right = _short(f'{noun}{p}も{clause}', f'{noun}も{clause}',
                              f'{noun}{p}も', f'{noun}も')
        return (wrong, right,
                f'「も」は「{p}」の代わりに使うので、「{p}も」とは言いません')

    match = _CLOCK_NO_NI.search(text)
    # 一時 is also "for a while": 一時閉まります.
    if match and match.group('time') != '一時':
        time, verb = match.group('time'), match.group('verb')
        return (time + verb, f'{time}に{verb}', '時刻を表すときは「に」が必要です')

    match = _OWNER_NO_NO.search(text)
    if match:
        owner, owned = match.group('owner'), match.group('owned')
        return (owner + owned, f'{owner}の{owned}',
                '持ち主を表すときは「の」でつなぎます')
    return None


def apply_marking_net(feedback: str, user_input: str, language: str) -> str:
    """Overturn a clean verdict on a question-word topic, a stacked も, a clock
    time without に, or an owner without の."""
    if language != 'Japanese' or not is_clean_verdict(feedback, language):
        return feedback
    error = marking_error(user_input)
    if not error:
        return feedback
    wrong, right, reason = error
    return f'💡 Feedback:\n- ❌ "{wrong}" → ✅ "{right}" ({reason})'
