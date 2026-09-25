"""Read an experiment this repo already ran, and say what it is allowed to claim.

Every probe here writes per-case JSON as it goes, which means the experiments
are re-analysable without spending another second of 7B time. This turns that
JSON into a paired comparison with confidence intervals and an exact test —
see dev/evals/abstats.py for why those and not a t-test.

    python3 dev/tools/ab_report.py reuse.json --field reused
    python3 dev/tools/ab_report.py reuse.json --field card --label 'vocab card'
    python3 dev/tools/ab_report.py a.json b.json --field reused --arm treatment

One file compares its own two arms (control vs treatment). Two files compare
the SAME arm across them — that is how two prompt wordings are weighed against
each other, since each was run with its own control on the same scenarios.

Pairing is by (case name, iteration index). A case present in one file and
missing from the other is dropped and reported, rather than being quietly
paired with something else.
"""
import argparse
import json
import os
import sys

_here = os.path.abspath(__file__)
while not os.path.exists(os.path.join(_here, 'pyproject.toml')):
    _here = os.path.dirname(_here)
sys.path.insert(0, os.path.join(_here, 'dev', 'evals'))
from abstats import paired_counts, verdict                          # noqa: E402


def _series(path, arm, field):
    """{(case, iteration): bool} for one arm of one probe output."""
    data = json.load(open(path))
    out = {}
    for name, row in data.items():
        turns = row.get(arm)
        if not isinstance(turns, list):
            continue
        for i, turn in enumerate(turns):
            if field in turn:
                out[(name, i)] = bool(turn[field])
    if not out:
        fields = sorted({k for row in data.values()
                         for arm_name in ('control', 'treatment')
                         for turn in (row.get(arm_name) or []) for k in turn})
        sys.exit(f'{path}: no arm {arm!r} carrying field {field!r}. '
                 f'Fields present: {fields}')
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('files', nargs='+', help='one or two probe JSON files')
    ap.add_argument('--field', default='reused',
                    help='the per-turn boolean to compare (reused, card, valid)')
    ap.add_argument('--arm', default='treatment',
                    help='with two files: which arm to compare across them')
    ap.add_argument('--label', default=None)
    args = ap.parse_args()
    label = args.label or args.field

    if len(args.files) == 1:
        path = args.files[0]
        a = _series(path, 'control', args.field)
        b = _series(path, 'treatment', args.field)
        a_name, b_name = 'control', 'treatment'
    else:
        first, second = args.files[:2]
        a = _series(first, args.arm, args.field)
        b = _series(second, args.arm, args.field)
        a_name = os.path.basename(first).replace('.json', '')
        b_name = os.path.basename(second).replace('.json', '')

    shared = sorted(set(a) & set(b))
    dropped = (set(a) ^ set(b))
    if not shared:
        sys.exit('nothing to compare: the two sides share no case')
    a_list = [a[k] for k in shared]
    b_list = [b[k] for k in shared]
    a_only, b_only = paired_counts(a_list, b_list)

    print(f'{label}, paired on {len(shared)} turns'
          + (f' ({len(dropped)} unpaired turns dropped)' if dropped else ''))
    print(verdict(a_name, sum(a_list), b_name, sum(b_list), len(shared),
                  a_only, b_only))
    if dropped:
        cases = sorted({name for name, _i in dropped})
        print(f'  dropped cases: {", ".join(cases[:6])}'
              + (' ...' if len(cases) > 6 else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
