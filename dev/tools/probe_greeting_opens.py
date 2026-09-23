"""Does the NPC's first turn GREET, or does it answer something unsaid? OPEN-41.

「確認いたします。次は何をご希望ですか。」 — *I'll check. What would you like
NEXT?* — on the first screen of a session, to a learner who has said nothing.
Seen twice in play, measured at roughly 2-3 in 10 Japanese turns, and invisible
to every gate: eval_actor.py scores validate(), which counts sentences and
checks script and question shape and has no notion of whether a greeting
greets. This is the missing ruler, not a fix.

TWO numbers, deliberately separate, because they are not opposites:

  GREETS       the turn contains an opening address — いらっしゃいませ, ようこそ,
               hello, welcome, good evening. A turn can greet AND presuppose.
  PRESUPPOSES  the turn treats a request as already made: 確認いたします
               (I'll check — check what?), 次は (next — after what?), "right
               away", "as you asked". These are the shapes seen in play.

Both are deterministic string tests, which is the point: the 7B that writes
these turns is the same 7B that would grade them, and OPEN-42 already measured
where that ends up. A crude ruler nobody can argue with beats a model's
opinion here — it is looking for fixed courtesy formulae, not meaning.

Read the pair per language. English greeted 21/22 when this was first seen by
hand; if that reproduces, the fault is Japanese-specific and the prompt's
greeting instruction is not the lever, since both languages read the same one.

Run it AFTER the eval gates, never beside them: one 7B at a time.

    python3 dev/tools/probe_greeting_opens.py out.json
    ITERS=5 LIMIT=6 python3 dev/tools/probe_greeting_opens.py out.json
"""
import json
import os
import re
import sys

os.environ.setdefault('HF_HUB_OFFLINE', '1')
os.environ.setdefault('HF_HUB_DISABLE_PROGRESS_BARS', '1')
_here = os.path.abspath(__file__)
while not os.path.exists(os.path.join(_here, 'pyproject.toml')):
    _here = os.path.dirname(_here)
sys.path.insert(0, _here)
from app.llm import call_actor, GREETING_SYS                        # noqa: E402
from app.llm.vocab import strip_vocab_block                         # noqa: E402

CASES = json.load(open(os.path.join(_here, 'dev/fixtures/actor_cases.json')))

ITERS = int(os.environ.get('ITERS', '3'))
LIMIT = int(os.environ.get('LIMIT', '0'))
OUT = sys.argv[1] if len(sys.argv) > 1 else '/dev/null'

# Fixed courtesy formulae, not meaning. A shop greeting in Japanese is
# essentially always one of these; いらっしゃいませ alone covers most of them.
_GREETS = {
    'Japanese': re.compile(
        r'いらっしゃいませ|いらっしゃい|ようこそ|こんにちは|こんばんは|'
        r'おはようございます|おはよう|お待たせ|はじめまして|どうも'),
    'English': re.compile(
        r'\b(hello|hi|hey|welcome|good (morning|afternoon|evening)|greetings)\b',
        re.IGNORECASE),
}

# The failure itself: language that only makes sense as a reply. 次 is listed
# with its particles rather than bare, since 次の方 and 次回 are ordinary
# scene-setting rather than a presupposed request.
_PRESUPPOSES = {
    'Japanese': re.compile(
        r'確認いたします|確認します|かしこまりました|承知(いた)?しました|'
        r'少々お待ちください|次は|次に何|ご希望の[^。]*は|まず何から|'
        r'ご注文の品|お伺いしております'),
    'English': re.compile(
        r"\b(right away|as you (asked|requested)|i'?ll check (on )?that|"
        r"let me check that for you|as requested|coming right up|"
        r"what (would you like|can i get you) (next|after that))\b",
        re.IGNORECASE),
}


def _first_turn(case):
    system = GREETING_SYS.format(place=case['place'], role=case['role'],
                                 language=case['language'],
                                 mood=case.get('mood', 'chatty and friendly'),
                                 complication='', task_setup='')
    raw = call_actor([{'role': 'user', 'content': 'Hello!'}], system,
                     speaker=case['speaker'], max_sentences=4,
                     language=case['language'])
    return strip_vocab_block(raw).strip()


def main():
    done = json.load(open(OUT)) if os.path.isfile(OUT) else {}
    cases = CASES[:LIMIT] if LIMIT else CASES

    for case in cases:
        key = case['name']
        if key in done:
            continue
        lang = case['language']
        greets = presupposes = 0
        examples = []
        for _ in range(ITERS):
            text = _first_turn(case)
            g = bool(_GREETS[lang].search(text))
            p = bool(_PRESUPPOSES[lang].search(text))
            greets += g
            presupposes += p
            if not g or p:
                examples.append(text.replace('\n', ' ')[:110])
        done[key] = dict(name=key, language=lang, greets=greets,
                         presupposes=presupposes, iters=ITERS, bad=examples[:2])
        json.dump(done, open(OUT, 'w'), indent=1, ensure_ascii=False)
        print(f"greets {greets}/{ITERS} | presupposes {presupposes}/{ITERS} "
              f"| [{lang}] {key}", flush=True)
        for e in examples[:1]:
            print(f"    {e}", flush=True)

    rows = [done[c['name']] for c in cases if c['name'] in done]
    if len(rows) < len(cases):
        print(f"\nINCOMPLETE — {len(rows)} of {len(cases)}. Re-run to continue.")
        return 0

    print("\nfirst turn, by language:")
    for lang in sorted({r['language'] for r in rows}):
        sub = [r for r in rows if r['language'] == lang]
        n = len(sub) * ITERS
        g = sum(r['greets'] for r in sub)
        p = sum(r['presupposes'] for r in sub)
        print(f"  {lang:<9} greets {g}/{n} ({100.0 * g / n:.0f}%)   "
              f"presupposes {p}/{n} ({100.0 * p / n:.0f}%)")
    print("\nA gap between the two languages means the fault is not the "
          "greeting instruction: both read the same one.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
