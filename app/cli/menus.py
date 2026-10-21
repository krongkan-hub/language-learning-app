"""The screens around a session: choosing what to practise, and the stats report.
"""
import sys

from .. import db
from ..i18n import normalize_language, scenario_name, t
from ..review import REVIEW_SCENARIO
from .state import _random_scenario, scenario_catalogue, topic_catalogue
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
        if sel.lstrip('-').isdigit():
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
        if sel.isdigit() and 0 < int(sel) <= len(topics):
            return topics[int(sel) - 1]
        print(t('invalid_number', language))


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
    print('=' * 50 + '\n')
