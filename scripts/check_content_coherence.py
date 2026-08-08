"""Content checks that catch defects the band counters cannot see.

check_task_depth.py counts things: 69 tasks, 10-16 scene hints, 4-6 vocab
tasks. Every defect that has actually reached a learner in this project got
past it while it was fully green, because counting a field cannot tell you
whether its contents are any good:

  * Scenario 2 declared itself "Airport Check-in & Security" and served 69
    job-interview tasks for the entire life of the repo. Perfect bands.
  * 'deposit' and 'lease' were each used as a vocabulary target in two
    different scenarios, which the spec forbids.
  * 'pharmacy', 'officer', 'seamstress' and twelve others were vocabulary
    targets naming the venue or the counterparty's own job.
  * A jargon sweep rewrote the goals and left the jargon in the hints.

Each check here corresponds to one of those. They are all cheap string work
over the loaded catalog — no model inference.

Usage:
    python3 scripts/check_content_coherence.py
"""
import re
import sys
from collections import defaultdict

sys.path.insert(0, '.')
from app.scenarios.builtins import SCENARIOS  # noqa: E402

# Words too common to identify a scenario, so they are stripped before a
# scenario's name/place/role are turned into its identity fingerprint.
STOPWORDS = {
    'a', 'an', 'the', 'you', 'are', 'is', 'at', 'in', 'on', 'of', 'for', 'and',
    'or', 'to', 'with', 'your', 'their', 'this', 'that', 'it', 'as', 'by',
}

# Specialist terms that survived earlier cleanups by hiding in hints. A word
# belongs here once it has been judged unusable outside its own trade.
JARGON = [
    'lapel', 'inseam', 'houndstooth', 'herringbone', 'placket', 'armhole',
    'pick stitching', 'basted', 'derailleur', 'gesso', 'impasto', 'diptych',
    'vernissage', 'lithograph', 'fretboard', 'intonation', 'capo', 'headstock',
    'gangway', 'catamaran', 'stateroom', 'mooring', 'aglet', 'pinsetter',
    'soffit', 'bric-a-brac', 'pistil', 'vamp', 'din release', 'wastegate',
    'demurrage', 'harmonized tariff', 'emulsifier', 'commutation',
    'matriculation', 'substrate', 'property irregularity',
]


def _words(text):
    return {w for w in re.findall(r"[a-z']+", text.lower()) if w not in STOPWORDS and len(w) > 2}


def _distinctive_fingerprints():
    """Identity terms per scenario, minus terms that are common everywhere.

    A scenario's name/place/role is a usable fingerprint only after generic
    service-counter vocabulary is stripped out. 'Tourist Info Center' yields
    {city, desk, guide, helpful, info, information, tourist}, and all but the
    last two occur in most scenarios' tasks -- left in, they let any scenario
    "look like" the tourist desk and drown the real signal.
    """
    raw = [_words(f"{s.name} {s.place} {s.role}") for s in SCENARIOS]
    texts = [' '.join(f"{t.goal} {t.hint}" for t in s.tasks).lower() for s in SCENARIOS]
    limit = len(SCENARIOS) * 0.30
    return [
        {w for w in fp if sum(1 for txt in texts if w in txt) <= limit}
        for fp in raw
    ]


def _vocab_targets():
    """Every ("word", scenario_index, task_index) vocabulary target."""
    out = []
    for si, s in enumerate(SCENARIOS):
        for ti, t in enumerate(s.tasks):
            m = re.match(r"Use the word '(.+)'", t.goal)
            if m:
                out.append((m.group(1).lower(), si, ti))
    return out


def check_topic_coherence():
    """Do a scenario's tasks talk about the scenario it claims to be?

    Builds an identity fingerprint from each scenario's name/place/role, then
    asks how often a scenario's own fingerprint appears in its own task text
    versus how often some *other* scenario's fingerprint does. Job-interview
    tasks sitting under an airport heading score near zero on their own terms
    and light up another scenario's.
    """
    fingerprints = _distinctive_fingerprints()
    failures = []
    for si, s in enumerate(SCENARIOS):
        text = ' '.join(f"{t.goal} {t.hint}" for t in s.tasks).lower()
        own = sum(text.count(w) for w in fingerprints[si])
        best_other, best_score = None, 0
        for oi, fp in enumerate(fingerprints):
            if oi == si:
                continue
            # Only terms unique to the other scenario count, so that shared
            # vocabulary between neighbours cannot manufacture a false alarm.
            score = sum(text.count(w) for w in fp - fingerprints[si])
            if score > best_score:
                best_other, best_score = oi, score
        # Only a scenario that never says its own subject out loud is a
        # failure. A "this looks more like scenario X" ratio rule was tried and
        # removed: it flagged Car Rental as Taxi and Pharmacy as Tourist Info,
        # because domain-adjacent scenarios legitimately share vocabulary. It
        # caught nothing the floor did not already catch, and a check that
        # cries wolf gets ignored. The cross-scenario match is kept only to
        # label a failure once the floor has already tripped.
        if own < 5:
            failures.append((si, s.name, own, best_other, best_score))
    return failures


def check_vocab_uniqueness():
    """No vocabulary word may be a target in two scenarios."""
    seen = defaultdict(list)
    for word, si, ti in _vocab_targets():
        seen[word].append((si, ti))
    return {w: v for w, v in seen.items() if len(v) > 1}


def check_vocab_not_trivial():
    """A vocabulary target must not name the venue or the counterparty's job.

    Learning to say "pharmacy" to a pharmacist teaches nothing; the word is
    already unavoidable in the surrounding conversation.
    """
    failures = []
    for word, si, ti in _vocab_targets():
        s = SCENARIOS[si]
        identity = _words(f"{s.name} {s.place} {s.role} {s.speaker}")
        if word in identity or any(word == w.rstrip('s') or w == word.rstrip('s') for w in identity):
            failures.append((word, si, s.name, ti))
    return failures


def check_no_jargon():
    """Specialist terms must be absent from hints as well as goals."""
    failures = []
    for si, s in enumerate(SCENARIOS):
        for ti, t in enumerate(s.tasks):
            blob = f"{t.goal} {t.hint} {t.done_when}".lower()
            for j in JARGON:
                if j in blob:
                    failures.append((j, si, s.name, ti, t.goal))
    return failures


def check_goal_donewhen_agree():
    """`done_when` must describe the act the goal asks for.

    Only the clearest disagreement is flagged -- a goal that asks the learner
    to *discuss* or *ask about* something while `done_when` demands they
    *agreed* or *confirmed* it. A learner who does exactly as told would fail.
    """
    SOFT = ('discuss', 'inquire', 'ask about', 'talk about', 'mention')
    HARD = ('agreed', 'confirmed', 'negotiated a', 'settled')
    failures = []
    for si, s in enumerate(SCENARIOS):
        for ti, t in enumerate(s.tasks):
            g, d = t.goal.lower(), t.done_when.lower()
            if any(g.startswith(x) for x in SOFT) and any(h in d for h in HARD):
                failures.append((si, s.name, ti, t.goal, t.done_when))
    return failures


def check_no_near_duplicate_goals():
    """Two goals in one scenario must not be the same request twice.

    check_task_depth only counts exact duplicates, so "Ask for a wake-up call"
    and "Request a wake-up call" both survived in Hotel Check-in. Comparison
    is on content words with the opening verb dropped, since the opening verb
    is exactly what tends to differ between a duplicated pair.
    """
    OPENERS = {'ask', 'request', 'inquire', 'confirm', 'explain', 'discuss',
               'state', 'say', 'tell', 'mention', 'negotiate', 'clarify',
               'verify', 'check', 'about', 'for', 'the', 'your', 'and', 'if'}
    failures = []
    for si, s in enumerate(SCENARIOS):
        sigs = []
        for ti, t in enumerate(s.tasks):
            # Short tokens are dropped as well as stopwords: "item's" splits
            # into {item, s}, and stray one-letter tokens inflate the overlap
            # ratio enough to pair genuinely different acts.
            words = {w.rstrip('s') for w in re.findall(r"[a-z]+", t.goal.lower())
                     if len(w) > 2 and w not in STOPWORDS}
            sigs.append((ti, t.goal, words - OPENERS))
        for i in range(len(sigs)):
            for j in range(i + 1, len(sigs)):
                a, b = sigs[i][2], sigs[j][2]
                if not a or not b:
                    continue
                overlap = len(a & b) / max(len(a), len(b))
                if overlap >= 0.8:
                    failures.append((si, s.name, sigs[i][0], sigs[i][1], sigs[j][0], sigs[j][1]))
    return failures


def main():
    print("=" * 78)
    print("CONTENT COHERENCE CHECK")
    print("=" * 78)
    ok = True

    topic = check_topic_coherence()
    if topic:
        ok = False
        print(f"\n❌ TOPIC COHERENCE — {len(topic)} scenario(s) do not discuss their own subject:")
        for si, name, own, other, score in topic:
            alt = f"looks like '{SCENARIOS[other].name}' ({score} hits)" if other is not None else ""
            print(f"   Sc{si + 1} '{name}': only {own} own-topic hits. {alt}")
    else:
        print("\n✅ Topic coherence: every scenario's tasks match its own setting.")

    dupes = check_vocab_uniqueness()
    if dupes:
        ok = False
        print(f"\n❌ VOCABULARY UNIQUENESS — {len(dupes)} word(s) targeted in more than one scenario:")
        for w, v in sorted(dupes.items()):
            where = ', '.join(f"Sc{si + 1} task {ti}" for si, ti in v)
            print(f"   '{w}': {where}")
    else:
        print("✅ Vocabulary uniqueness: no word is a target in two scenarios.")

    trivial = check_vocab_not_trivial()
    if trivial:
        ok = False
        print(f"\n❌ TRIVIAL VOCABULARY — {len(trivial)} target(s) name the venue or the counterparty:")
        for w, si, name, ti in trivial:
            print(f"   Sc{si + 1} task {ti} '{w}' in '{name}'")
    else:
        print("✅ Vocabulary substance: no target names its own venue or role.")

    jargon = check_no_jargon()
    if jargon:
        ok = False
        print(f"\n❌ JARGON — {len(jargon)} occurrence(s) in a goal, hint, or done_when:")
        for j, si, name, ti, goal in jargon:
            print(f"   Sc{si + 1} task {ti} '{j}' — {goal[:56]}")
    else:
        print("✅ Jargon: no blacklisted specialist term in any field.")

    drift = check_goal_donewhen_agree()
    if drift:
        ok = False
        print(f"\n❌ GOAL/DONE_WHEN DISAGREEMENT — {len(drift)}:")
        for si, name, ti, goal, done in drift:
            print(f"   Sc{si + 1} task {ti}: goal '{goal[:44]}' vs done_when '{done[:44]}'")
    else:
        print("✅ Goal/done_when: no soft goal graded against a hard outcome.")

    neardup = check_no_near_duplicate_goals()
    if neardup:
        ok = False
        print(f"\n❌ NEAR-DUPLICATE GOALS — {len(neardup)} pair(s) asking the same thing twice:")
        for si, name, ti, gi, tj, gj in neardup:
            print(f"   Sc{si + 1} task {ti} '{gi}'")
            print(f"        vs task {tj} '{gj}'")
    else:
        print("✅ Near-duplicates: no scenario asks for the same act twice.")

    print("\n" + "=" * 78)
    print("✅ CONTENT COHERENCE VERIFIED" if ok else "❌ CONTENT COHERENCE FAILED")
    return ok


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
