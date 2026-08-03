"""Stratified random playtest across the whole scenario catalog.

`ai_playtester.py` walks every task in a scenario, which at 69 tasks each and
~14s per task means ~21 hours for all 5,520.  That is the wrong shape for the
question "is this content winnable?", which a random sample answers far more
cheaply: n=200 gives roughly a +/-4% margin of error on the pass rate.

Sampling is stratified so every scenario is represented, and seeded so a run is
reproducible.  Results stream to JSON after each task, so an interrupted run
resumes where it stopped rather than starting over.

    ./venv/bin/python scripts/playtest_sample.py            # n=200, seed 42
    ./venv/bin/python scripts/playtest_sample.py 300        # n=300
    ./venv/bin/python scripts/playtest_sample.py 200 --seed 7
    ./venv/bin/python scripts/playtest_sample.py --out results.json

Each record carries the task's full definition and the conversation transcript,
so failures can be triaged into genuine content bugs versus harness artifacts
without re-running anything.
"""

import json
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.scenarios.builtins import SCENARIOS

DEFAULT_N = 200
DEFAULT_SEED = 42
DEFAULT_OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           '..', 'scratch', 'playtest_sample_results.json')


def build_sample(n, seed):
    """Pick n (scenario_index, task_index) pairs, spread across all scenarios.

    Every scenario contributes at least floor(n / len(SCENARIOS)) tasks; the
    remainder is handed to a random subset so the total lands exactly on n.
    """
    rng = random.Random(seed)
    num_scenarios = len(SCENARIOS)
    base, extra = divmod(n, num_scenarios)

    gets_extra = set(rng.sample(range(num_scenarios), extra)) if extra else set()

    picks = []
    for s_idx, scenario in enumerate(SCENARIOS):
        want = base + (1 if s_idx in gets_extra else 0)
        want = min(want, len(scenario.tasks))
        for t_idx in rng.sample(range(len(scenario.tasks)), want):
            picks.append((s_idx, t_idx))

    rng.shuffle(picks)  # interleave scenarios so partial runs stay representative
    return picks


def load_done(path):
    """Return prior results keyed by (scenario_index, task_index)."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return {}
    return {(r['scenario_index'], r['task_index']): r
            for r in data.get('results', [])}


def save(path, meta, done):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    payload = dict(meta)
    payload['results'] = sorted(
        done.values(), key=lambda r: (r['scenario_index'], r['task_index']))
    passed = sum(1 for r in payload['results'] if r['passed'])
    payload['completed'] = len(payload['results'])
    payload['passed'] = passed
    payload['pass_rate'] = round(passed / len(payload['results']) * 100, 1) if payload['results'] else None
    tmp = path + '.tmp'
    with open(tmp, 'w') as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    os.replace(tmp, path)  # atomic, so an interrupt cannot truncate the file


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    flags = {a.split('=')[0]: a.split('=', 1)[1] if '=' in a else True
             for a in sys.argv[1:] if a.startswith('--')}

    n = int(args[0]) if args else DEFAULT_N
    seed = int(flags.get('--seed', DEFAULT_SEED))
    out = os.path.abspath(flags.get('--out', DEFAULT_OUT))

    from scripts.ai_playtester import playtest_task

    picks = build_sample(n, seed)
    done = load_done(out)
    meta = {'n_requested': n, 'seed': seed,
            'catalog_tasks': sum(len(s.tasks) for s in SCENARIOS),
            'scenarios': len(SCENARIOS)}

    remaining = [p for p in picks if p not in done]
    print(f"sample n={len(picks)} across {len(SCENARIOS)} scenarios (seed {seed})", flush=True)
    if done:
        print(f"resuming: {len(done)} already done, {len(remaining)} to go", flush=True)
    print(f"writing to {out}", flush=True)
    print("-" * 78, flush=True)

    started = time.time()
    for i, (s_idx, t_idx) in enumerate(remaining, 1):
        scenario = SCENARIOS[s_idx]
        task = scenario.tasks[t_idx]
        t0 = time.time()
        try:
            passed, history = playtest_task(scenario, task, max_attempts=3)
            error = None
        except Exception as exc:                      # keep the run alive
            passed, history, error = False, [], f"{type(exc).__name__}: {exc}"

        done[(s_idx, t_idx)] = {
            'scenario_index': s_idx,
            'scenario_number': s_idx + 1,
            'scenario_name': scenario.name,
            'place': scenario.place,
            'speaker': scenario.speaker,
            'task_index': t_idx,
            'goal': task.goal,
            'hint': task.hint,
            'done_when': task.done_when,
            'difficulty': task.difficulty,
            'phase': task.phase,
            'reactive': task.reactive,
            'scene_hint': task.scene_hint,
            'passed': bool(passed),
            'error': error,
            'seconds': round(time.time() - t0, 1),
            'transcript': history,
        }
        save(out, meta, done)

        elapsed = time.time() - started
        rate = elapsed / i
        eta = rate * (len(remaining) - i)
        tally = sum(1 for r in done.values() if r['passed'])
        print(f"[{len(done):>3}/{len(picks)}] {'PASS' if passed else 'FAIL'} "
              f"Sc{s_idx+1:<3} {task.goal[:44]:<46} "
              f"({tally}/{len(done)} = {tally/len(done)*100:.0f}%) eta {eta/60:.0f}m",
              flush=True)

    results = list(done.values())
    passed = sum(1 for r in results if r['passed'])
    print("-" * 78, flush=True)
    print(f"PASS RATE: {passed}/{len(results)} = {passed/len(results)*100:.1f}%", flush=True)
    fails = [r for r in results if not r['passed']]
    if fails:
        print(f"\n{len(fails)} failure(s) — full transcripts in {out}:", flush=True)
        for r in fails:
            print(f"  Sc{r['scenario_number']:<3} [{'reactive' if r['reactive'] else '        '}] "
                  f"{r['goal'][:56]}", flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
