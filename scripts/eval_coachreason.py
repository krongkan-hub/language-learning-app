"""Does the coach's REASON describe the change it actually made?

`eval_coach.py` scores whether the correction is right and never reads the
bracketed reason. That left room for OPEN-38: the coach corrected
"how much it cost" → "how much it costs" and explained it as "use the base
form of the verb", which is backwards — `costs` is the third-person -s — so a
learner who reads the explanation learns the opposite rule. Measured at 10/30
before the fix, and it was not flaky: 5/5 on each of the two shapes.

The check is a per-case predicate, NOT one shared word list. "base form" is a
false claim about `costs` and a TRUE one about `open` in "want to open", so
the missing-"to" case is graded on circularity instead: a reason saying
"after 'to' ..." presupposes the very word the learner left out, while
"'want' takes 'to' before the verb" names it. An earlier version of this
probe used one word list for every case, called that true reason a failure,
and reported the fix as 4/30 rather than 0/30.

Only runs that REACHED the correction can be graded — a reason cannot be
wrong about a correction that was never made — so the denominator moves with
the coach's hit rate. GRADED_FLOOR fails the suite loudly rather than let a
shrinking denominator flatter the score.

The last two cases are controls where the "base verb" / "plural" template is
the true rule. They are not part of the percentage; losing one of those
corrections fails the suite outright, because a fix that silenced the
template everywhere would score 100% here while making the coach worse.
"""
import os
import re
import sys

os.environ.setdefault('HF_HUB_OFFLINE', '1')
os.environ.setdefault('HF_HUB_DISABLE_PROGRESS_BARS', '1')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.llm import _llm_chat
from app.coach import coach_feedback, coach_system, COACH_OPTS

ITERS = 5
GRADED_FLOOR = 10

BASE_CLAIM = re.compile(r'base\s+(form|verb)', re.I)
PRESUPPOSES_TO = re.compile(r'after\s*["“‘]?(?:want\s+)?to["”’]?[,\s]', re.I)

# input, correction the run must reach, predicate that marks the reason wrong
PROBES = [
    ("I want to know how much it cost?", "costs", BASE_CLAIM,
     "third-person -s is not a base form"),
    ("I want open a checking account.", "want to open", PRESUPPOSES_TO,
     '"after to" presupposes the word that was missing'),
    ("She don't like the coffee here.", "doesn't", BASE_CLAIM,
     "auxiliary agreement, not a base form"),
    ("Yesterday I buy a ticket for the train.", "bought", BASE_CLAIM,
     "a past tense is the opposite of a base form"),
    ("He have two brother.", "has", BASE_CLAIM,
     "third-person -s again"),
    ("I am go to the store now.", "going", BASE_CLAIM,
     'after "am" it is the -ing form'),
]
CONTROLS = [
    ("I want to finding a book.", "want to find", 'base verb IS the rule here'),
    ("Can I get two bottle of water?", "two bottles", 'the plural IS the rule here'),
]

_last_exit_reason = ''

BULLET = re.compile(r'❌\s*"([^"]*)"\s*→\s*✅\s*"([^"]*)"\s*(?:\(([^)]*)\))?')


def reason_for(text, correction):
    """The bracketed reason on the bullet that made this correction, or ''."""
    for m in BULLET.finditer(text):
        if correction.lower() in (m.group(2) or '').lower():
            return (m.group(3) or '').strip()
    return ''


def run_once(text):
    raw = _llm_chat(messages=[{"role": "system", "content": coach_system("English", "")},
                              {"role": "user", "content": text}],
                    options=COACH_OPTS)['message']['content']
    out = coach_feedback(raw, text, "English", promote_fit=False)
    return re.split(r'⬆️\s*Level up:', out)[0]


def main():
    print(f"Running reason check on {len(PROBES)} probes + {len(CONTROLS)} "
          f"controls, {ITERS} iterations each...")
    print("=" * 78)

    graded = wrong = missing = 0
    for text, correction, is_wrong, note in PROBES:
        reached = case_wrong = case_missing = 0
        example = ''
        for _ in range(ITERS):
            feedback = run_once(text)
            if correction.lower() not in feedback.lower():
                continue
            reached += 1
            reason = reason_for(feedback, correction)
            if not reason:
                case_missing += 1
            elif is_wrong.search(reason):
                case_wrong += 1
                example = example or reason
        graded += reached
        wrong += case_wrong
        missing += case_missing
        print(f"{reached}/{ITERS} corrected | {case_wrong} wrong reason | "
              f"{case_missing} no reason | {text}")
        print(f"    ({note})")
        if example:
            print(f"    WRONG: {example}")

    print("-" * 78)
    lost = []
    for text, correction, note in CONTROLS:
        reached = sum(correction.lower() in run_once(text).lower() for _ in range(ITERS))
        print(f"{reached}/{ITERS} corrected | control | {text}")
        print(f"    ({note})")
        if reached == 0:
            lost.append(text)

    print("=" * 78)
    print(f"Graded runs (correction reached): {graded}")
    print(f"Wrong reasons: {wrong}    Missing reasons: {missing}")

    def die(reason):
        # Recorded as well as printed: both failure paths exit 1, so a test
        # asserting only the code cannot tell which one fired.
        global _last_exit_reason
        _last_exit_reason = reason
        print(f"\n❌ {reason}")
        sys.exit(1)

    if graded < GRADED_FLOOR:
        # Not scored as a pass: with too few graded runs the percentage says
        # nothing, and a coach that stopped correcting would read as 100%.
        die(f"only {graded} graded runs, need {GRADED_FLOOR} — the coach stopped "
            f"reaching these corrections, so the reason score is meaningless. "
            f"Fix that first.")
    if lost:
        die(f"a control lost its correction entirely: {lost}. The template is "
            f"the TRUE rule in these cases — suppressing it everywhere is a "
            f"regression, not a fix.")

    score = 100.0 * (graded - wrong - missing) / graded
    print(f"\nFinal Reason Score: {score:.1f}% ({graded - wrong - missing}/{graded})")


if __name__ == '__main__':
    main()
