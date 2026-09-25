"""Find the wrong Japanese objectives with an embedding model. OPEN-42, offline.

The row records two rejected detectors and one untried option — "an embedding
model for the back-translation comparison (a new dependency on a machine
already swapping 5.4GB of 6.1GB)". Two things about that reading were wrong,
and this script is what they change:

  1. THE MEMORY OBJECTION DOES NOT APPLY. The objectives are a FIXED
     catalogue, not something generated per turn. This runs once, with the 7B
     unloaded, and its output is a list of lines for a human to fix by hand.
     Nothing here runs while a learner is playing, so nothing competes for RAM.
  2. THE DEPENDENCY IS DEV-ONLY, and needs no torch: mlx-embeddings loads a
     BERT-based embedder on MLX. `app/` keeps its single runtime dependency.

Measured elsewhere on exactly this task — deciding whether a translation
carries the source meaning — LaBSE reads 87.7% and BGE-M3 89.3% contrastive
accuracy (arXiv 2608.28776), against the 12% our own guards manage on the
80 labelled lines in dev/fixtures/ja_translation_cases.json.

This is a TRIAGE tool, not a gate: it ranks by cosine similarity between the
English objective and its Japanese translation in one shared space. A low
score means "a human should look at this line", never "this line is wrong".
The fixture is here to say how good the ranking is before anyone trusts it:

    python3 dev/tools/audit_ja_objectives.py --calibrate         # embedder
    python3 dev/tools/audit_ja_objectives.py --translate ja.json # the 7B
    python3 dev/tools/audit_ja_objectives.py --score ja.json ranked.json

--calibrate prints how well the score separates the reviewer's `fine` lines
from the `false` ones, as a threshold sweep. If the separation is poor, say
so in OPEN-42 and stop — that is the fourth rejected design, and worth as much
as a working one.

Install (dev only):  pip install mlx-embeddings
"""
import argparse
import json
import os
import sys

# Unlike every other tool here, this one must reach the network on its FIRST
# run: the embedder is not the 7B and is not in the local cache yet. It is a
# one-time download of a few hundred MB, after which HF_HUB_OFFLINE=1 works.

_here = os.path.abspath(__file__)
while not os.path.exists(os.path.join(_here, 'pyproject.toml')):
    _here = os.path.dirname(_here)
sys.path.insert(0, _here)

# Calibrated on the 80 labelled lines: AUC 0.774, and the five worst-scoring
# lines were 5/5 genuinely wrong. multilingual-e5-LARGE reads AUC 0.788 with
# precision@5 of 3/5 — five times the size, inside the noise, worse where a
# human reads. LaBSE (a sentence-transformers Dense head) and BGE-M3 (no
# safetensors) do not load in mlx-embeddings at all.
MODEL = os.environ.get('EMBED_MODEL', 'intfloat/multilingual-e5-small')
CASES = os.path.join(_here, 'dev/fixtures/ja_translation_cases.json')


def _load_embedder():
    try:
        from mlx_embeddings import load
    except ImportError:
        sys.exit("mlx-embeddings is not installed. This is a dev-only tool:\n"
                 "    pip install mlx-embeddings\n"
                 "app/ keeps its single runtime dependency either way.")
    model, tokenizer = load(MODEL)
    return model, tokenizer


def _similarities(pairs):
    """Cosine similarity for each (english, japanese) pair, in one space."""
    import mlx.core as mx
    model, tokenizer = _load_embedder()

    def _embed(texts):
        out = []
        for text in texts:
            ids = tokenizer.encode(text, return_tensors='mlx')
            vec = model(ids).text_embeds[0]
            out.append(vec / mx.linalg.norm(vec))
        return out

    en = _embed([p[0] for p in pairs])
    ja = _embed([p[1] for p in pairs])
    return [float(mx.sum(a * b)) for a, b in zip(en, ja)]


def calibrate():
    """How well does similarity separate the reviewer's labels?"""
    cases = json.load(open(CASES))
    scores = _similarities([(c['en'], c['ja']) for c in cases])
    for case, score in zip(cases, scores):
        case['sim'] = score

    by = {}
    for c in cases:
        by.setdefault(c['label'], []).append(c['sim'])
    print(f'{MODEL}\n')
    for label in sorted(by):
        vals = sorted(by[label])
        mid = vals[len(vals) // 2]
        print(f'  {label:<10} n={len(vals):<3} median {mid:.3f}  '
              f'min {vals[0]:.3f}  max {vals[-1]:.3f}')

    fine = [c['sim'] for c in cases if c['label'] == 'fine']
    false = [c['sim'] for c in cases if c['label'] == 'false']

    # Absolute cosine values cluster in a narrow band (0.84-0.96 for
    # multilingual-e5-small), so a fixed cutoff says almost nothing and the
    # first version of this script reported exactly that non-answer. What a
    # TRIAGE tool is actually judged on is its ORDER: read the worst N lines,
    # how many real errors do you find? So: AUC, and precision@N.
    wins = ties = 0
    for bad in false:
        for ok in fine:
            wins += bad < ok
            ties += bad == ok
    auc = (wins + 0.5 * ties) / (len(false) * len(fine))
    print(f'\nAUC (a random wrong line ranks below a random fine one): {auc:.3f}')
    print('  0.50 is a coin flip. Higher is better; this is the number that '
          'says whether the ORDER is worth reading down.')

    ranked = sorted(cases, key=lambda c: c['sim'])
    print('\nprecision@N — read the N worst-scoring lines, how many are '
          'really wrong?')
    print('  N     wrong found   of N     (26 wrong lines in 80)')
    for k in (5, 10, 20, 26, 40):
        hits = sum(1 for c in ranked[:k] if c['label'] == 'false')
        print(f'  {k:<5} {hits:>2}            {k}       '
              f'{100.0 * hits / k:.0f}%')
    print(f'  chance rate is {100.0 * len(false) / len(cases):.0f}%')
    json.dump([{k: c[k] for k in ("en", "ja", "label", "sim")} for c in ranked],
              open('/tmp/ja_calibration.json', 'w'), indent=1, ensure_ascii=False)
    print('  (all 80 scored lines written to /tmp/ja_calibration.json)')
    print('\nEvery guard this project already has catches 3/26 with 0 false '
          'positives. A cutoff that beats that pair is worth shipping; one '
          'that does not goes into OPEN-42 as rejected, with these numbers.')
    worst = sorted(cases, key=lambda c: c['sim'])[:10]
    print('\nlowest ten, whatever their label:')
    for c in worst:
        print(f"  {c['sim']:.3f} [{c['label']:<9}] {c['en'][:44]} -> {c['ja'][:28]}")


def translate(out_path, limit=0):
    """STEP 1 (needs the 7B, not the embedder): translate the catalogue's
    objectives exactly the way a live session does, and save them.

    The wrong Japanese a learner sees is NOT stored anywhere — `translate_hints`
    produces it per session, per scenario, in a batch call, and it is thrown
    away when the session ends. So there is nothing on disk to audit until this
    runs. It deliberately calls the real function, batched per scenario like
    the app does, because a line translated alone is not the line the learner
    was shown.

    The 7B must be loaded for this and the embedder must NOT be, which is why
    this is a separate step from --score on a 16GB machine.
    """
    from app.llm import translate_hints
    from app.scenarios import builtins

    # BATCH SIZE IS THE MEASUREMENT. A live session translates the ten tasks
    # it selected, so the model sees about twenty numbered lines. Handing it
    # all 69 of a scenario's tasks at once — the first version of this
    # function — is ~138 lines against max_tokens=1024: the tail is truncated
    # mid-word and the numbering drifts, so goal 40 comes back wearing goal
    # 51's translation. That looked exactly like a catalogue full of swapped
    # translations, and it was this tool's bug, not the app's. Anything
    # measured here must be measured at the size the learner actually meets.
    SESSION_BATCH = 10

    # Resumable: 80 scenarios x 7 batches is hours of exclusive 7B time, and
    # the model is shared with every eval in this repo. Re-running picks up
    # where it stopped rather than paying for the finished scenarios again.
    rows = json.load(open(out_path)) if os.path.isfile(out_path) else []
    seen = {r['scenario'] for r in rows}
    if seen:
        print(f'resuming: {len(rows)} objectives from '
              f'{len(seen)} finished scenarios', flush=True)

    scenarios = builtins.SCENARIOS[:limit] if limit else builtins.SCENARIOS
    for n, scenario in enumerate(scenarios, 1):
        if scenario.name in seen:
            continue
        tasks = list(scenario.tasks)
        for start in range(0, len(tasks), SESSION_BATCH):
            chunk = tasks[start:start + SESSION_BATCH]
            mapping = translate_hints(chunk, 'Japanese')
            for i, task in enumerate(chunk):
                ja = mapping.get((i, task.goal))
                if ja and ja != task.goal:      # untranslated lines fell back
                    rows.append(dict(scenario=scenario.name, en=task.goal, ja=ja))
        print(f'[{n}/{len(scenarios)}] {scenario.name}: '
              f'{len(tasks)} goals', flush=True)
        json.dump(rows, open(out_path, 'w'), indent=1, ensure_ascii=False)
    print(f'\n{len(rows)} translated objectives written to {out_path}')
    print('Now run:  --score ' + out_path + ' ranked.json')


def score(in_path, out_path):
    """STEP 2 (needs the embedder, not the 7B): rank them worst-first."""
    rows = json.load(open(in_path))
    for row, sim in zip(rows, _similarities([(r['en'], r['ja']) for r in rows])):
        row['sim'] = sim
    rows.sort(key=lambda r: r['sim'])
    json.dump(rows, open(out_path, 'w'), indent=1, ensure_ascii=False)
    print(f'{len(rows)} pairs scored, lowest first, written to {out_path}\n')
    for row in rows[:25]:
        print(f"  {row['sim']:.3f} {row['en'][:44]} -> {row['ja'][:30]}")
    print('\nCandidates for a human to read, not verdicts. Calibration says '
          'the five worst were all genuinely wrong and the worst forty held '
          'twenty of twenty-six.')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--calibrate', action='store_true',
                    help='score the 80 labelled lines (embedder)')
    ap.add_argument('--translate', metavar='OUT',
                    help='step 1: translate the catalogue with the 7B')
    ap.add_argument('--limit', type=int, default=0,
                    help='with --translate: only the first N scenarios')
    ap.add_argument('--score', nargs=2, metavar=('IN', 'OUT'),
                    help='step 2: rank a translated file (embedder)')
    args = ap.parse_args()
    if args.calibrate:
        calibrate()
    elif args.translate:
        translate(args.translate, args.limit)
    elif args.score:
        score(*args.score)
    else:
        ap.print_help()
