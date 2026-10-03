"""Merge story-thread labels into the scenario catalogue (OPEN-53 (3)).

    python3 dev/tools/import_task_threads.py DIR [--check]

DIR holds one file per scenario (scenario_01.json ...), each
{"threads": {id: description}, "task_threads": [id, ... one per task]}.
Validated before writing: one label per task, every label a declared thread
or 'general', 3-6 threads, each holding at least 8 tasks. The scenario gets
"threads", each task "thread"; Scenario.get_session_tasks then draws a
session from one or two threads plus 'general'.
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOGUE = ROOT / 'app' / 'scenarios' / 'data'
_ID = re.compile(r'^[a-z_]+$')


def problems(labels: dict, tasks: list) -> list:
    threads = labels.get('threads') or {}
    per_task = labels.get('task_threads') or []
    out = []
    if len(per_task) != len(tasks):
        return [f'{len(per_task)} labels for {len(tasks)} tasks']
    declared = set(threads) - {'general'}
    if not 3 <= len(declared) <= 6:
        out.append(f'{len(declared)} threads (want 3-6)')
    for tid in declared:
        if not _ID.match(tid):
            out.append(f'bad thread id {tid!r}')
    for k, tid in enumerate(per_task):
        if tid != 'general' and tid not in declared:
            out.append(f'task {k}: undeclared thread {tid!r}')
    counts = Counter(per_task)
    for tid in declared:
        if counts[tid] < 8:
            out.append(f'thread {tid!r} has {counts[tid]} tasks (want 8+)')
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('dir', type=Path)
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args(argv)
    bad = written = 0
    for path in sorted(args.dir.glob('scenario_*.json')):
        target = CATALOGUE / path.name
        data = json.loads(target.read_text(encoding='utf-8'))
        labels = json.loads(path.read_text(encoding='utf-8'))
        issues = problems(labels, data['tasks'])
        if issues:
            bad += 1
            print(f'✗ {path.name}: ' + '; '.join(issues[:6]))
            continue
        if args.check:
            continue
        data['threads'] = {k: v for k, v in labels['threads'].items() if k != 'general'}
        for task, tid in zip(data['tasks'], labels['task_threads']):
            task['thread'] = tid
        target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        written += 1
    print(f'{written} written, {bad} with problems')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
