"""How long does the coach take per turn, and where? (OPEN-53 (1))

    python3 dev/tools/probe_coach_latency.py [--rounds 2]

Runs call_coach (both passes, with a situation, as a scenario turn does) on
a fixed set of learner messages, in order, like one session — the prompt
cache warms over the session exactly as it does in play. Prints per-message
wall time and the median; the first round includes model load and cold
caches and is reported separately. Output text is printed too, so a change
meant only to speed things up can be checked for changing nothing else.
"""
import argparse
import os
import statistics
import sys
import time

_here = os.path.abspath(__file__)
while not os.path.exists(os.path.join(_here, 'pyproject.toml')):
    _here = os.path.dirname(_here)
sys.path.insert(0, _here)
from app.coach import call_coach  # noqa: E402
from app.coach.prompt import describe_situation  # noqa: E402

# One language, as one session is: switching language changes the system
# prompt and rebuilds every cache, which play never does mid-session.
MESSAGES = [
    ('English', 'Hi, could I get a table for two near the window?'),
    ('English', 'I want know if you have vegetarian option on the menu.'),
    ('English', 'Yesterday I go to the shop and buyed two bottle of milk.'),
    ('English', 'Could you bring the bill, please? We are in a bit of a hurry.'),
    ('English', 'Is the fish today fresh or frozen?'),
    ('English', 'Thank you so much, everything was delicious.'),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--rounds', type=int, default=2)
    args = ap.parse_args()
    situation = describe_situation('A fine dining restaurant', 'You are a polite waiter.', 'Waiter')
    for r in range(args.rounds):
        times = []
        for language, text in MESSAGES:
            t = time.time()
            out = call_coach(text, language, situation=situation)
            times.append(time.time() - t)
            print(f'  {times[-1]:5.1f}s  {text[:40]:40s} -> {out.splitlines()[-1][:70]}')
        label = 'cold (round 1)' if r == 0 else f'warm (round {r + 1})'
        print(f'{label}: median {statistics.median(times):.1f}s  total {sum(times):.1f}s')
    return 0


if __name__ == '__main__':
    sys.exit(main())
