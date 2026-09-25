"""Does the NPC actually reuse a word the retrieval handed it? And at what cost?

app/retrieval.py picks previously-taught words that fit the scenario, and
app/session.py offers them to the actor in two sentences. Neither of those is
evidence that anything changed: the model may ignore the block entirely, or —
the failure this project has already measured twice — it may obey it at the
expense of the vocabulary card the learner actually reads (OPEN-21, and
OPEN-14's rejected greeting rule).

So this is a CONTROLLED pair on the same scenarios, same moods, same seeds:

    control    the actor prompt as it was, no review block
    treatment  the same prompt plus the three retrieved words

and it reports three numbers, not one:

    REUSE       treatment turns that contain a retrieved word (control turns
                that contain one are the baseline rate — the word may simply
                be common for that setting, and that share is not the feature)
    CARD        turns carrying a parsable <vocab> card, both arms. A reuse
                gain paid for with cards is a loss.
    VALID       turns passing validate(): sentence count, script, question
                shape. Also both arms.

The candidate pool stands in for a learner's vocabulary log: real advanced
words, most of them wrong for any given scenario, so the retrieval has to
choose rather than just hand over whatever it has. Ranking runs through the
real app/retrieval.py, so a bad ranking shows up here as a bad reuse rate
rather than being assumed away.

Run it after the eval gates, never beside them: one 7B at a time.

    python3 dev/tools/probe_review_reuse.py out.json
    ITERS=2 LIMIT=8 python3 dev/tools/probe_review_reuse.py out.json
"""
import json
import os
import sys

os.environ.setdefault('HF_HUB_OFFLINE', '1')
os.environ.setdefault('HF_HUB_DISABLE_PROGRESS_BARS', '1')
_here = os.path.abspath(__file__)
while not os.path.exists(os.path.join(_here, 'pyproject.toml')):
    _here = os.path.dirname(_here)
sys.path.insert(0, _here)
from app import retrieval                                           # noqa: E402
from app.llm import call_actor, validate                            # noqa: E402
from app.llm.vocab import strip_vocab_block                         # noqa: E402
from app.scenarios.builtins import SCENARIOS                        # noqa: E402
from app.session import build_actor_system_prompt                   # noqa: E402
from app.cli import parse_vocab                                     # noqa: E402

CASES = json.load(open(os.path.join(_here, 'dev/fixtures/actor_cases.json')))

# The wording of the ask is the variable. The shipped version works, but not
# often: 7 of 40 treatment turns against 0 of 40 control, with the vocabulary
# card intact (39/40 against 36/40). Three other rows in BACKLOG record a
# prompt lever measuring inert on this model, so alternatives are MEASURED
# here rather than argued about.
#
#   soft   permission, three words  — what ships: 7/40 reuse, 0/40 control
#   firm   instruction, ONE word, named twice
#   slot   the word handed to the vocabulary section it competes with
MODE = os.environ.get('MODE', 'soft')
ITERS = int(os.environ.get('ITERS', '2'))
LIMIT = int(os.environ.get('LIMIT', '0'))
OUT = sys.argv[1] if len(sys.argv) > 1 else '/dev/null'

# A stand-in vocabulary log: words a learner could plausibly have been taught
# across the catalogue. Most are wrong for any one scenario, which is the
# point — the retrieval has to pick, and a pool that fits everything would
# measure nothing.
POOL_EN = [
    ('decant', 'to pour wine off its sediment before serving'),
    ('sommelier', 'a waiter trained in wine'),
    ('itemised', 'listed line by line, as on a bill'),
    ('deductible', 'the amount you pay before insurance starts'),
    ('turbulence', 'rough air that shakes an aircraft'),
    ('concierge', 'a hotel employee who arranges things for guests'),
    ('perennial', 'a plant that comes back every year'),
    ('tourniquet', 'a tight band used to stop bleeding'),
    ('escrow', 'money held by a third party until a deal closes'),
    ('sourdough', 'bread leavened with a fermented starter'),
    ('upholstery', 'the padded fabric covering furniture'),
    ('prognosis', "a doctor's forecast of how an illness will go"),
    ('layover', 'a wait between connecting flights'),
    ('collateral', 'property pledged as security for a loan'),
    ('bouquet', 'an arranged bunch of flowers'),
    ('vintage', 'the year a wine was produced'),
]
POOL_JA = [
    ('保証期間', 'product warranty period'),
    ('診察券', 'a clinic registration card'),
    ('搭乗口', 'a boarding gate'),
    ('頭金', 'a down payment'),
    ('花束', 'a bouquet of flowers'),
    ('在庫', 'stock held in a shop'),
    ('領収書', 'an itemised receipt'),
    ('処方箋', "a doctor's prescription"),
    ('乗り換え', 'changing trains'),
    ('築年数', 'the age of a building'),
    ('定期券', 'a commuter pass'),
    ('香ばしい', 'pleasantly toasted in aroma'),
]


def _pool(language):
    return POOL_JA if language == 'Japanese' else POOL_EN


def _retrieve(case, scenario, k=3):
    """The real ranking path, over the stand-in pool."""
    pool = _pool(case['language'])
    goals = [t.goal for t in scenario.tasks[:5]] if scenario else []
    query = retrieval.embed(retrieval.scenario_query(
        case['place'], case['role'], goals))
    if query is None:
        return [w for w, _e in pool[:k]]        # embedder off: first k, as the app would
    scored = []
    for word, explanation in pool:
        vector = retrieval.unpack(retrieval.embed_vocab(word, explanation))
        if vector:
            scored.append((retrieval.cosine(query, vector), word))
    scored.sort(reverse=True)
    return [word for _s, word in scored[:k]]


def _block(words):
    """The review instruction under test. Returns text appended to task_setup,
    which is where build_review_block's output lands in production."""
    if not words:
        return ''
    if MODE == 'soft':
        return None                     # use the shipped build_review_block
    if MODE == 'firm':
        word = words[0]
        return (f'USE THIS WORD: say "{word}" naturally somewhere in your '
                f'dialogue this turn. The learner was taught "{word}" earlier '
                f'and needs to meet it again in use. Do not explain it, do not '
                f'mention this instruction, and still teach a DIFFERENT new '
                f'word in the vocabulary block.')
    if MODE == 'slot':
        word = words[0]
        return (f'The learner already met the word "{word}". Work it into your '
                f'spoken dialogue this turn — it is ordinary for this setting — '
                f'and pick a different, harder word for the vocabulary block '
                f'below.')
    raise SystemExit(f'unknown MODE {MODE!r}')


def _turn(case, scenario, review_words):
    """One actor turn, built the way a session builds it."""
    task = scenario.tasks[0] if scenario else 'Serve the customer.'
    override = _block(review_words)
    if override is None:
        system = build_actor_system_prompt(
            scenario or _FakeScenario(case), task, language=case['language'],
            mood=case.get('mood', 'chatty and friendly'), complication=None,
            review_words=review_words)
    else:
        system = build_actor_system_prompt(
            scenario or _FakeScenario(case),
            f'{task}\n\n{override}'.strip() if isinstance(task, str) else task,
            language=case['language'],
            mood=case.get('mood', 'chatty and friendly'), complication=None)
        if not isinstance(task, str) and override:
            system = system.replace('STOP AND THINK FIRST',
                                    f'{override}\n\nSTOP AND THINK FIRST', 1)
    raw = call_actor([{'role': 'user', 'content': 'Hello.'}], system,
                     speaker=case['speaker'], max_sentences=3,
                     language=case['language'])
    spoken = strip_vocab_block(raw)
    ok, _reason = validate(raw, 3, case['language'])
    return dict(spoken=spoken.strip(), card=bool(parse_vocab(raw)), valid=bool(ok))


class _FakeScenario:
    """The actor fixtures name a place and role that may not be a catalogue
    scenario; the prompt builder only reads these four fields."""
    def __init__(self, case):
        self.place = case['place']
        self.role = case['role']
        self.speaker = case['speaker']
        self.name = case.get('name', case['place'])
        self.tasks = []


def main():
    cases = CASES[:LIMIT] if LIMIT else CASES
    by_name = {s.name: s for s in SCENARIOS}
    done = json.load(open(OUT)) if os.path.isfile(OUT) else {}
    print(f'{len(cases)} cases x {ITERS} iteration(s), control vs treatment '
          f'[MODE={MODE}]\n', flush=True)

    for case in cases:
        key = case['name']
        if key in done:
            continue
        scenario = by_name.get(case['place']) or by_name.get(case.get('name', ''))
        words = _retrieve(case, scenario)
        rows = dict(name=key, language=case['language'], words=words,
                    control=[], treatment=[])
        for _ in range(ITERS):
            rows['control'].append(_turn(case, scenario, []))
            rows['treatment'].append(_turn(case, scenario, words))
        for arm in ('control', 'treatment'):
            for turn in rows[arm]:
                turn['reused'] = any(w.lower() in turn['spoken'].lower()
                                     for w in words)
        done[key] = rows
        json.dump(done, open(OUT, 'w'), indent=1, ensure_ascii=False)
        c = sum(t['reused'] for t in rows['control'])
        t_ = sum(t['reused'] for t in rows['treatment'])
        print(f"reuse control {c}/{ITERS}  treatment {t_}/{ITERS} | "
              f"[{case['language']}] {key} -> {', '.join(words)}", flush=True)

    rows = [done[c['name']] for c in cases if c['name'] in done]
    if len(rows) < len(cases):
        print(f'\nINCOMPLETE — {len(rows)} of {len(cases)}. Re-run to continue.')
        return 0

    n = len(rows) * ITERS
    print(f'\n{"":<12}{"control":>10}{"treatment":>12}')
    for label, field in (('reuse', 'reused'), ('vocab card', 'card'),
                         ('valid turn', 'valid')):
        c = sum(t[field] for r in rows for t in r['control'])
        t_ = sum(t[field] for r in rows for t in r['treatment'])
        print(f'{label:<12}{c:>7}/{n:<4}{t_:>7}/{n}')
    print('\nReuse is the feature. The card and validity rows are the price: '
          'OPEN-21 and OPEN-14 both measured added prompt text suppressing the '
          'vocabulary card, so a reuse gain that costs cards is not a gain.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
