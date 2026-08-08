"""Prove the loaded catalog is byte-identical to a known-good snapshot.

Content lives in JSON files now rather than as Python literals. That move
must not alter a single task. This serialises whatever `SCENARIOS` currently
loads to, in a canonical form, and compares its SHA-256 against the snapshot
taken before the migration.

Regenerate the snapshot ONLY when the catalog is deliberately changed:

    python3 scripts/check_catalog_roundtrip.py --update

Usage:
    python3 scripts/check_catalog_roundtrip.py
"""
import hashlib
import json
import os
import sys

sys.path.insert(0, '.')
from app.scenarios.builtins import SCENARIOS  # noqa: E402

SNAPSHOT = os.path.join('eval', 'catalog_snapshot.json')


def canonical_blob() -> str:
    """Serialise the catalog so equal content always yields an equal string."""
    out = []
    for s in SCENARIOS:
        out.append({
            'name': s.name,
            'place': s.place,
            'role': s.role,
            'speaker': s.speaker,
            'complications': list(getattr(s, 'complications', []) or []),
            'tasks': [{
                'goal': t.goal,
                'hint': t.hint,
                'done_when': t.done_when,
                'difficulty': t.difficulty,
                'scene_hint': t.scene_hint,
                'phase': t.phase,
                'reactive': t.reactive,
            } for t in s.tasks],
        })
    return json.dumps(out, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def main() -> bool:
    blob = canonical_blob()
    digest = hashlib.sha256(blob.encode()).hexdigest()

    if '--update' in sys.argv:
        with open(SNAPSHOT, 'w') as fh:
            fh.write(blob)
        print(f"Snapshot updated: {len(SCENARIOS)} scenarios, "
              f"{sum(len(s.tasks) for s in SCENARIOS)} tasks, sha256 {digest}")
        return True

    if not os.path.exists(SNAPSHOT):
        print(f"❌ No snapshot at {SNAPSHOT}. Run with --update to create one.")
        return False

    with open(SNAPSHOT) as fh:
        expected = fh.read()
    expected_digest = hashlib.sha256(expected.encode()).hexdigest()

    if digest == expected_digest:
        print(f"✅ CATALOG ROUND-TRIP VERIFIED — {len(SCENARIOS)} scenarios, "
              f"{sum(len(s.tasks) for s in SCENARIOS)} tasks, sha256 {digest[:16]}...")
        return True

    print("❌ CATALOG ROUND-TRIP FAILED — loaded content differs from the snapshot.")
    print(f"   expected sha256 {expected_digest}")
    print(f"   actual   sha256 {digest}")

    # Locate the divergence so the failure names a scenario rather than a hash.
    try:
        got, want = json.loads(blob), json.loads(expected)
    except json.JSONDecodeError:
        return False
    if len(got) != len(want):
        print(f"   scenario count: expected {len(want)}, got {len(got)}")
        return False
    for i, (g, w) in enumerate(zip(got, want), start=1):
        if g == w:
            continue
        print(f"   first difference in Scenario {i} '{w['name']}'")
        for key in ('name', 'place', 'role', 'speaker', 'complications'):
            if g[key] != w[key]:
                print(f"     {key}: expected {w[key]!r}, got {g[key]!r}")
        if len(g['tasks']) != len(w['tasks']):
            print(f"     task count: expected {len(w['tasks'])}, got {len(g['tasks'])}")
        for ti, (gt, wt) in enumerate(zip(g['tasks'], w['tasks'])):
            if gt != wt:
                for key in wt:
                    if gt[key] != wt[key]:
                        print(f"     task {ti} {key}: expected {wt[key]!r}, got {gt[key]!r}")
                break
        break
    return False


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
