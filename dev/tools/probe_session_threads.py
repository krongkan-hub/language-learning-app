"""How many story threads does a drawn session span? (OPEN-53 (3))

    python3 dev/tools/probe_session_threads.py [--draws 200]

For every labelled scenario, draws sessions the way the app does and counts
the distinct non-general threads in each — once with the thread-aware draw,
once with the labels hidden (every task eligible, the old behaviour). Fewer
threads per session = a visit that tells one story. No model involved.
"""
import argparse
import os
import random
import statistics
import sys

_here = os.path.abspath(__file__)
while not os.path.exists(os.path.join(_here, 'pyproject.toml')):
    _here = os.path.dirname(_here)
sys.path.insert(0, _here)
from dataclasses import replace  # noqa: E402

from app.scenarios.builtins import load_scenarios  # noqa: E402


def spread(session) -> int:
    return len({t.thread for t in session} - {'general', ''})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--draws', type=int, default=200)
    args = ap.parse_args()
    random.seed(0)
    with_threads, without = [], []
    for s in load_scenarios():
        if not s.threads:
            continue
        unlabeled = replace(s, threads={})
        for _ in range(args.draws):
            with_threads.append(spread(s.get_session_tasks(num_tasks=10)))
            without.append(spread(unlabeled.get_session_tasks(num_tasks=10)))
    if not with_threads:
        print('no labelled scenarios')
        return 1
    for name, xs in (('thread-aware', with_threads), ('all tasks (old)', without)):
        dist = {k: xs.count(k) for k in sorted(set(xs))}
        print(f'{name:16s} mean {statistics.mean(xs):.2f} threads/session  dist {dist}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
