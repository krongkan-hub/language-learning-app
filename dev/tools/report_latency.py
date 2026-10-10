"""How long a turn takes, stage by stage, from the spans the app records (#43).

app/telemetry.py writes one row per finished span to the `spans` table of
the schema in use. This reads them back: p50 / p95 / n per stage, so the
roadmap's latency KPI (a turn under 8 s at p50) is a query, not a guess.

    python3 dev/tools/report_latency.py                 # the learner's data
    LANGUAGE_COACH_DB=playtest python3 dev/tools/report_latency.py --days 7

Stages: turn (judge + reply + coach as the learner waits), judge, actor
(the NPC reply), coach, greeting, and llm.generate (each model call).
Spans recorded while the Mac slept stretch the tail; read p95 with that in
mind, and prefer p50 for the KPI.
"""
import argparse
import os
import sys

_here = os.path.abspath(__file__)
while not os.path.exists(os.path.join(_here, 'pyproject.toml')):
    _here = os.path.dirname(_here)
sys.path.insert(0, _here)
from app import db                                                       # noqa: E402

ORDER = ('turn', 'judge', 'actor', 'coach', 'greeting', 'llm.generate')
TARGET_TURN_P50_MS = 8000          # docs/ROADMAP / issue #43


def report(conn, days: int) -> list:
    return conn.execute(
        """SELECT name, COUNT(*) AS n,
                  percentile_cont(0.5) WITHIN GROUP (ORDER BY duration_ms) AS p50,
                  percentile_cont(0.95) WITHIN GROUP (ORDER BY duration_ms) AS p95
           FROM spans WHERE started_at >= now() - %s * interval '1 day'
           GROUP BY name""", (days,)).fetchall()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--days', type=int, default=30, help='look back this many days (default 30)')
    args = ap.parse_args()
    conn = db.init_db()
    rows = {r['name']: r for r in report(conn, args.days)}
    if not rows:
        print(f'No spans in the last {args.days} days — play a session with the web app first.')
        return
    print(f'{"stage":<14}{"n":>6}{"p50":>10}{"p95":>10}')
    for name in [n for n in ORDER if n in rows] + sorted(set(rows) - set(ORDER)):
        r = rows[name]
        print(f'{name:<14}{r["n"]:>6}{r["p50"] / 1000:>9.1f}s{r["p95"] / 1000:>9.1f}s')
    if 'turn' in rows:
        p50 = rows['turn']['p50']
        verdict = 'meets' if p50 <= TARGET_TURN_P50_MS else 'misses'
        print(f'\nturn p50 {p50 / 1000:.1f}s {verdict} the {TARGET_TURN_P50_MS / 1000:.0f}s target')


if __name__ == '__main__':
    main()
