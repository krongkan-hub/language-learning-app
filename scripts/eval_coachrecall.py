"""How much of a clear English error does the coach simply not correct?

eval_coach.py's English error cases cover to+gerund, participle-after-is,
plural-after-a-number and progressive. Nothing in it tests subject-verb
agreement, simple past, or an auxiliary followed by a bare verb — the three
classes that read 0/5 when they turned up as a side effect of the OPEN-38
probe. This measures the classes, not the wording.

Every input carries exactly ONE unambiguous error a teacher would mark. The
controls at the end are shapes the suite already passes; if they fall too,
the probe is broken rather than the coach.

Two results are worth carrying with this file, because they narrow what a
future fix can be.

The model KNOWS. Asked plainly, with no coach prompt — "answer CORRECT or
WRONG" — the 7B called every one of these sentences wrong and gave the right
fix, 21/21. That is the opposite of OPEN-07, where the model genuinely did
not know a wrong particle was wrong and a deterministic net was the only
route. Here the knowledge is present and the coach prompt is suppressing it.

Adding worked examples does NOT help. A past-tense example and a do/does
example, plus widening the "bare verb after is/are" rule to cover am/was/were,
moved the score by exactly zero — 25/60 before, 25/60 after, identical in
every class. What moved it was carving determiner-agreement out from under
the "Perfectly natural!" bias: 25/60 -> 30/60. Past tense stayed 0/15 through
all of it.
"""
import json, os, re, sys
os.environ.setdefault('HF_HUB_OFFLINE', '1')
os.environ.setdefault('HF_HUB_DISABLE_PROGRESS_BARS', '1')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.llm import _llm_chat
from app.coach import coach_feedback, coach_system, COACH_OPTS, is_clean_verdict

CASES = [
    ("agreement",  "She don't like the coffee here.",            ["doesn't", "does not"]),
    ("agreement",  "My friends is waiting outside.",             ["are waiting", "are"]),
    ("agreement",  "There is many people in the queue.",         ["are many", "are"]),
    ("past",       "Yesterday I buy a ticket for the train.",    ["bought"]),
    ("past",       "Last week we go to the museum.",             ["went"]),
    ("past",       "I didn't went to the meeting.",              ["didn't go", "did not go"]),
    ("aux+bare",   "I am go to the store now.",                  ["am going", "going"]),
    ("aux+bare",   "He is work at the bank.",                    ["is working", "works"]),
    ("aux+bare",   "They have finish the report.",               ["have finished", "finished"]),
    ("perfect",    "I live in this city since 2020.",            ["have lived", "have been living"]),
    ("ditrans",    "Can you explain me the rules?",              ["explain the rules to me", "to me"]),
    ("determiner", "Every students must sign the form.",         ["every student", "all students"]),
    # controls: classes the shipped suite already handles
    ("CONTROL",    "Can I get two bottle of water, please?",     ["two bottles"]),
    ("CONTROL",    "Is it prohibit here?",                       ["prohibited"]),
]
# The other half of the ledger. Recall is trivially raised by correcting
# everything, and over-correction is the failure this project treats as worst,
# so a recall change is only real if these stay clean. Deliberately NOT taken
# from coach_cases.json — a fixture quoted in a prompt stops being a test.
CLEAN = [
    "Could I have a flat white to take away, please?",
    "I'd like to book a table for two at seven.",
    "Do you know when the next train leaves?",
    "I've been waiting here for about ten minutes.",
    "Sorry, I think there's been a mistake with my order.",
    "Where can I pick up my parcel?",
    "Last week we went to the museum and it was closed.",
    "She doesn't like coffee, so tea is fine.",
]

ITERS = int(os.environ.get('ITERS', '5'))
OUT = sys.argv[1] if len(sys.argv) > 1 else '/dev/null'

rows, done = [], (json.load(open(OUT)) if os.path.exists(OUT) else {})
for cls, text, wants in CASES:
    if text in done:
        rows.append(done[text]); continue
    hit = clean = 0
    misses = []
    for _ in range(ITERS):
        raw = _llm_chat(messages=[{"role": "system", "content": coach_system("English", "")},
                                  {"role": "user", "content": text}],
                        options=COACH_OPTS)['message']['content']
        out = coach_feedback(raw, text, "English", promote_fit=False)
        fb = re.split(r'⬆️\s*Level up:', out)[0]
        if any(w.lower() in fb.lower() for w in wants):
            hit += 1
        else:
            if is_clean_verdict(fb, "English"):
                clean += 1
            misses.append(fb.replace('\n', ' | ')[:110])
    row = dict(cls=cls, text=text, hit=hit, clean=clean, iters=ITERS, miss=misses[:1])
    rows.append(row); done[text] = row
    json.dump(done, open(OUT, 'w'), indent=1, ensure_ascii=False)
    print(f"{hit}/{ITERS} corrected | {clean} said 'natural' | [{cls}] {text}", flush=True)
    if row['miss']:
        print(f"    missed as: {row['miss'][0]}", flush=True)

clean_kept = 0
for text in CLEAN:
    key = 'CLEAN::' + text
    if key in done:
        clean_kept += done[key]['hit']; continue
    kept = 0
    flagged = []
    for _ in range(ITERS):
        raw = _llm_chat(messages=[{"role": "system", "content": coach_system("English", "")},
                                  {"role": "user", "content": text}],
                        options=COACH_OPTS)['message']['content']
        out = coach_feedback(raw, text, "English", promote_fit=False)
        fb = re.split(r'⬆️\s*Level up:', out)[0]
        if is_clean_verdict(fb, "English"):
            kept += 1
        else:
            flagged.append(fb.replace('\n', ' | ')[:110])
    done[key] = dict(cls='CLEAN', text=text, hit=kept, clean=kept, iters=ITERS, miss=flagged[:1])
    json.dump(done, open(OUT, 'w'), indent=1, ensure_ascii=False)
    clean_kept += kept
    print(f"{kept}/{ITERS} left alone | [clean] {text}", flush=True)
    if flagged:
        print(f"    over-corrected as: {flagged[0]}", flush=True)

probes = [r for r in rows if r['cls'] != 'CONTROL']
ctrl = [r for r in rows if r['cls'] == 'CONTROL']
print(f"\nRECALL (12 probes) : {sum(r['hit'] for r in probes)}/{len(probes)*ITERS}")
print(f"  said 'natural'   : {sum(r['clean'] for r in probes)}/{len(probes)*ITERS}")
print(f"controls           : {sum(r['hit'] for r in ctrl)}/{len(ctrl)*ITERS}")
print(f"CLEAN left alone   : {clean_kept}/{len(CLEAN)*ITERS}")
if sum(r['hit'] for r in ctrl) < len(ctrl) * ITERS:
    print("\n\u274c a control lost its correction \u2014 the probe or the coach is broken, "
          "and either way the recall number below means nothing.")
    sys.exit(1)
if clean_kept < len(CLEAN) * ITERS:
    # Recall is trivially raised by correcting everything. Over-correction is
    # the failure this project treats as worst, so it fails the suite outright
    # rather than being traded against the headline.
    print(f"\n\u274c over-correction: {len(CLEAN)*ITERS - clean_kept} clean sentence(s) "
          f"were 'corrected'. A recall gain bought with these is not a gain.")
    sys.exit(1)

by = {}
for r in probes:
    a = by.setdefault(r['cls'], [0, 0]); a[0] += r['hit']; a[1] += ITERS
for k in sorted(by):
    print(f"  {k:<11} {by[k][0]:>2}/{by[k][1]:<2}")

score = 100.0 * sum(r['hit'] for r in probes) / (len(probes) * ITERS)
print(f"\nFinal Recall Score: {score:.1f}% ({sum(r['hit'] for r in probes)}/{len(probes)*ITERS})")
