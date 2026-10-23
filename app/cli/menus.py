"""The screens around a session: choosing what to practise, and the stats report.
"""
import re
import sys

from .. import db
from ..db import analytics
from ..i18n import normalize_language, scenario_name, t
from ..review import REVIEW_SCENARIO
from .state import _random_scenario, drill_form, scenario_catalogue, topic_catalogue
from .terminal import safe_input


def choose_language() -> str:
    while True:
        raw = safe_input('Which language do you want to practice? (e.g., English, Japanese): ',
                         language='English').strip()
        if not raw:
            return 'English'
        language = normalize_language(raw)
        if language is not None:
            return language
        print(t('err_unsupported_language', 'English'))


def choose_mode(language: str) -> str:
    """'scenario', 'review' or 'explain'."""
    while True:
        choice = safe_input(t('prompt_mode', language), language=language).strip()
        if choice in ('', '1'):
            return 'scenario'
        if choice == '2':
            return 'review'
        if choice == '3':
            return 'explain'
        print(t('enter_valid_number', language))


def select_scenario(language: str, conn, user_id: int):
    """Offer one scenario from the least-played band; on a no, list them."""
    catalogue = scenario_catalogue()
    offered = _random_scenario(conn, user_id, catalogue)
    print(f"\n{t('random_scenario', language, name=scenario_name(offered, language))}")
    choice = safe_input(t('prompt_play_scenario', language), language=language).strip().lower()
    if choice in ('y', 'yes', ''):
        return offered

    stats_map = db.get_all_scenario_stats(conn, user_id)
    displayed = catalogue[:15]

    def _print_subset(subset, show_more):
        print(f"\n{t('available_scenarios', language)}")
        for i, s in enumerate(subset):
            s_stats = stats_map.get(s.name)
            if s_stats and s_stats.get('plays', 0) > 0:
                print(t('scenario_item_with_mastery', language, i=i + 1,
                        name=scenario_name(s, language), n=len(s.tasks),
                        mastery=t(s_stats.get('mastery', 'newbie'), language)))
            else:
                print(t('scenario_item', language, i=i + 1,
                        name=scenario_name(s, language), n=len(s.tasks)))
        if show_more and len(subset) < len(catalogue):
            print(t('more_scenarios', language, n=len(catalogue) - len(subset)))

    _print_subset(displayed, show_more=True)
    while True:
        sel = safe_input(f"\n{t('prompt_select_scenario', language)}", language=language).strip()
        if not sel:
            print(t('enter_valid_number', language))
            continue
        lowered = sel.lower()
        if lowered in ('quit', 'exit'):
            print(t('exiting', language))
            sys.exit(0)
        if lowered == 'all':
            displayed = catalogue
            _print_subset(displayed, show_more=False)
            continue
        if re.fullmatch('-?[0-9]+', sel):      # not isdigit(): '²' is a digit int() refuses
            idx = int(sel) - 1
            if 0 <= idx < len(displayed):
                return displayed[idx]
            print(t('invalid_number', language))
            continue
        matches = [s for s in catalogue
                   if lowered in s.name.lower() or lowered in scenario_name(s, language).lower()]
        if not matches:
            print(t('no_matching_scenarios', language, query=sel))
        else:
            displayed = matches
            _print_subset(displayed, show_more=False)


def select_topic(language: str):
    import random
    topics = topic_catalogue()
    offered = random.choice(topics)
    print(f"\n{t('random_topic', language, name=offered.title(language))}")
    choice = safe_input(t('prompt_play_topic', language), language=language).strip().lower()
    if choice in ('y', 'yes', ''):
        return offered
    print(f"\n{t('available_topics', language)}")
    for i, topic in enumerate(topics):
        print(t('topic_item', language, i=i + 1, name=topic.title(language)))
    while True:
        sel = safe_input(f"\n{t('prompt_select_topic', language)}", language=language).strip()
        if re.fullmatch('[0-9]+', sel) and 0 < int(sel) <= len(topics):
            return topics[int(sel) - 1]
        print(t('invalid_number', language))


VOCAB_QUIZ_WORDS = 3


def run_vocab_quiz(conn, user_id: int, language: str, on_exit=None) -> None:
    """Before a roleplay: recall up to three due words from their explanation.

    The other way a word earns times_correct is using it in conversation
    (turns._credit_vocab_use), which waits for the NPC to set it up; this
    asks for it directly. A miss still updates last_seen_at, so the next
    quiz asks other words first.
    """
    words = db.get_vocab_for_review(conn, user_id, language, limit=VOCAB_QUIZ_WORDS)
    if not words:
        return
    print(t('vocab_quiz_header', language))
    for row in words:
        answer = safe_input(t('vocab_quiz_prompt', language, exp=row['explanation']),
                            language=language, on_exit=on_exit).strip()
        if answer.lower() == 'skip':
            break
        correct = drill_form(answer) == drill_form(row['word'])
        print(t('vocab_quiz_correct' if correct else 'vocab_quiz_incorrect', language,
                word=row['word']))
        db.mark_vocab_reviewed(conn, user_id, language, row['word'], correct)


HARDEST_SHOWN = 5
LATENCY_DAYS = 30
# Pipeline order, not slowest-first: the learner waits for `turn`, which is
# judge + actor + coach; llm.generate is each model call inside them.
STAGE_ORDER = ('turn', 'judge', 'actor', 'coach', 'greeting', 'llm.generate')
TARGET_TURN_P50_MS = 8000          # the roadmap KPI in issue #43


def print_stats_report(conn, language: str = 'English') -> None:
    # Profiles are keyed on (display_name, target_lang); looking one up by
    # language is what keeps --lang Japanese from reporting the English
    # learner's numbers (OPEN-29). find_user, not get_or_create: looking
    # creates no learner.
    user_id = db.find_user(conn, target_lang=language) or db.NO_USER

    overall = db.get_overall_stats(conn, user_id)
    vocab = db.get_vocab_stats(conn, user_id)
    scenario_stats = db.get_all_scenario_stats(conn, user_id)
    topic_stats = db.get_all_topic_stats(conn, user_id)

    shown = {s.name: scenario_name(s, language) for s in scenario_catalogue()}
    shown[REVIEW_SCENARIO] = '間違えたところを練習' if language == 'Japanese' else REVIEW_SCENARIO

    print('=' * 50)
    print(t('stats_header', language))
    print('=' * 50)

    print(t('stats_overall_header', language))
    print(t('stats_sessions_played', language, n=overall['sessions_played']))
    print(t('stats_tasks_attempted', language, n=overall['tasks_attempted']))
    print(t('stats_tasks_completed', language, n=overall['tasks_completed']))
    print(t('stats_overall_rate', language, pct=overall['completion_rate']))

    for header, stats in (('stats_scenarios_header', scenario_stats),
                          ('stats_topics_header', topic_stats)):
        played = [s for s in stats.values() if s.get('plays', 0) > 0]   # newest first
        if header == 'stats_topics_header' and not played:
            continue
        print(f"\n{t(header, language)}")
        if not played:
            print(t('stats_no_scenarios_played', language))
        for s_info in played:
            raw_name = s_info.get('scenario_name') or s_info['topic_name']
            print(t('stats_scenario_item', language, name=shown.get(raw_name, raw_name),
                    plays=s_info['plays'], best_pct=s_info['best_pct'],
                    mastery=t(s_info['mastery'], language)))

    print(f"\n{t('stats_vocab_header', language)}")
    print(t('stats_vocab_total', language, n=vocab['total_words']))
    print(t('stats_vocab_learned', language, n=vocab['learned_words']))
    print(t('stats_vocab_due', language, n=vocab['due_words']))

    print(f"\n{t('stats_mistakes_header', language)}")
    repeated = db.repeated_mistakes(conn, user_id, language)
    if not repeated:
        print(t('stats_no_repeated_mistakes', language))
    for m in repeated:
        print(t('stats_mistake_item', language, n=m['occurrences'],
                quoted=m['example_quoted'], correction=m['example_correction']))

    weeks = analytics.weekly(conn, user_id)
    if any(w['sessions'] for w in weeks):
        print(f"\n{t('stats_weekly_header', language, n=len(weeks))}")
        for w in weeks:
            print(t('stats_weekly_item', language, week=w['week'], sessions=w['sessions'],
                    completed=w['completed'], attempted=w['attempted']))

    hardest = [r for r in analytics.by_scenario(conn, user_id) if r['attempted']][:HARDEST_SHOWN]
    if hardest:
        print(f"\n{t('stats_hardest_header', language)}")
        for r in hardest:
            print(t('stats_hardest_item', language,
                    name=shown.get(r['scenario_name'], r['scenario_name']),
                    pct=r['completion_rate'], completed=r['completed'],
                    attempted=r['attempted'], tries=r['avg_attempts']))

    print_latency(conn, language)
    print('=' * 50 + '\n')


def print_latency(conn, language: str) -> None:
    """Per-stage p50/p95 from the recorded spans (#43). The spans measure the
    app, not the learner, so this is the same for every profile."""
    rows = {r['name']: r for r in analytics.performance(conn, days=LATENCY_DAYS)}
    print(f"\n{t('stats_latency_header', language, days=LATENCY_DAYS)}")
    if not rows:
        print(t('stats_latency_none', language))
        return
    for name in (n for n in STAGE_ORDER if n in rows):
        r = rows[name]
        print(t('stats_latency_item', language, stage=f'{name:<13}', n=r['count'],
                p50=f"{r['p50_ms'] / 1000:5.1f}", p95=f"{r['p95_ms'] / 1000:5.1f}"))
    if 'turn' in rows:
        key = 'stats_latency_meets' if rows['turn']['p50_ms'] <= TARGET_TURN_P50_MS else 'stats_latency_misses'
        print(t(key, language, p50=f"{rows['turn']['p50_ms'] / 1000:.1f}",
                target=f'{TARGET_TURN_P50_MS / 1000:.0f}'))
