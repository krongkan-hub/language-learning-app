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

    python3 dev/tools/audit_ja_objectives.py --calibrate    # score the 80 labelled lines
    python3 dev/tools/audit_ja_objectives.py --catalogue out.json

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

# LaBSE reads 87.7% on exactly this task (translation error detection,
# arXiv 2608.28776) and is BERT-based, which mlx-embeddings loads directly.
# EMBED_MODEL=intfloat/multilingual-e5-small is the small fallback.
MODEL = os.environ.get('EMBED_MODEL', 'sentence-transformers/LaBSE')
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
    pairs = [(s, 1) for s in false] + [(s, 0) for s in fine]
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


def catalogue(out_path):
    """Rank every authored Japanese objective in the catalogue for review."""
    from app.scenarios import builtins
    pairs, meta = [], []
    for scenario in builtins.SCENARIOS:
        for task in scenario.tasks:
            ja = (getattr(task, 'vocab_translations', {}) or {}).get('Japanese')
            if not ja:
                continue
            pairs.append((task.goal, ja[0]))
            meta.append(dict(scenario=scenario.name, goal=task.goal, ja=ja[0]))
    if not pairs:
        sys.exit('No authored Japanese translations found in the catalogue.')

    for row, sim in zip(meta, _similarities(pairs)):
        row['sim'] = sim
    meta.sort(key=lambda r: r['sim'])
    json.dump(meta, open(out_path, 'w'), indent=1, ensure_ascii=False)
    print(f'{len(meta)} pairs scored, lowest first, written to {out_path}\n')
    for row in meta[:25]:
        print(f"  {row['sim']:.3f} {row['goal'][:44]} -> {row['ja'][:30]}")
    print('\nThese are candidates for a human to read, not verdicts.')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--calibrate', action='store_true')
    ap.add_argument('--catalogue', metavar='OUT')
    args = ap.parse_args()
    if args.calibrate:
        calibrate()
    elif args.catalogue:
        catalogue(args.catalogue)
    else:
        ap.print_help()
