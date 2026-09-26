"""The screens around a session: choosing a scenario, the stats report,
vocabulary review, and the correction drill.
"""
from ..i18n import t, scenario_name
from ..coach import correction_targets, is_clean_verdict, _normalize_phrase
from ..scenarios.builtins import SCENARIOS
import random
import sys
from .. import db


from .terminal import safe_input


def run_vocab_review(conn, user_id: int, language: str, on_exit=None) -> None:
    """Run a short recall quiz for up to 3 words due for review."""
    words = db.get_vocab_for_review(conn, user_id, language, limit=3)
    if not words:
        return

    print(t('review_header', language))
    for row in words:
        word = row['word']
        exp = row['explanation']
        ans = safe_input(t('review_prompt', language, exp=exp), language=language, on_exit=on_exit).strip()
        if ans.lower() == 'skip':
            break
        correct = (ans.lower() == word.strip().lower())
        if correct:
            print(t('review_correct', language, word=word))
        else:
            print(t('review_incorrect', language, word=word))
        db.mark_vocab_reviewed(conn, user_id, language, word, correct)


def run_correction_drill(feedback: str, language: str, on_exit=None) -> None:
    """Make the learner retype each corrected form before the session moves on.

    One prompt per Feedback bullet, not one for a rebuilt sentence: a ✅ form is
    routinely a fragment ("two bottles"), and splicing it back into the
    learner's line would mean guessing where it goes — the ❌ quote is the
    model's paraphrase and need not appear verbatim in what they typed. Asking
    for exactly the text on screen is always achievable, which is what makes a
    no-skip loop fair.
    """
    if is_clean_verdict(feedback, language):
        return
    for target in correction_targets(feedback):
        wanted = _normalize_phrase(target)
        print(f"\n{t('drill_intro', language, correction=target)}")
        while True:
            typed = safe_input(t('drill_prompt', language), language=language, on_exit=on_exit)
            if _normalize_phrase(typed) == wanted:
                print(t('drill_correct', language))
                break
            print(t('drill_retry', language, correction=target))


def print_stats_report(conn, language: str = 'English') -> None:
    """Print progress report for user."""
    # Resolve the profile the same way every other call site does — profiles are
    # keyed on (display_name, target_lang), so picking the most recently active
    # row regardless of language reported the English learner's numbers under
    # --lang Japanese and made the Japanese profile unreachable (OPEN-29).
    user_id = db.get_or_create_user(conn, target_lang=language)

    overall = db.get_overall_stats(conn, user_id)
    vocab = db.get_vocab_stats(conn, user_id)
    scenario_stats = db.get_all_scenario_stats(conn, user_id)

    played = [s for s in scenario_stats.values() if s.get('plays', 0) > 0]
    played.sort(key=lambda x: x.get('last_played') or '', reverse=True)

    sc_by_name = {s.name: s for s in SCENARIOS}

    print('=' * 50)
    print(t('stats_header', language))
    print('=' * 50)

    print(t('stats_overall_header', language))
    print(t('stats_sessions_played', language, n=overall['sessions_played']))
    print(t('stats_tasks_attempted', language, n=overall['tasks_attempted']))
    print(t('stats_tasks_completed', language, n=overall['tasks_completed']))
    print(t('stats_overall_rate', language, pct=overall['completion_rate']))

    print(f"\n{t('stats_scenarios_header', language)}")
    if not played:
        print(t('stats_no_scenarios_played', language))
    else:
        for s_info in played:
            raw_name = s_info['scenario_name']
            sc_obj = sc_by_name.get(raw_name)
            disp_name = scenario_name(sc_obj, language) if sc_obj else raw_name
            mastery_str = t(s_info['mastery'], language)
            print(t('stats_scenario_item', language,
                    name=disp_name,
                    plays=s_info['plays'],
                    best_pct=s_info['best_pct'],
                    mastery=mastery_str))

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


def select_builtin_scenario(language: str = 'English', conn=None, user_id: int = None):
    """Pick from the hardcoded SCENARIOS list (original behaviour)."""
    valid_scenarios = [s for s in SCENARIOS if len(s.tasks) > 0]
    if not valid_scenarios:
        print(t('err_no_scenarios', language))
        sys.exit(1)
    random_scenario = random.choice(valid_scenarios)
    print(f"\n{t('random_scenario', language, name=scenario_name(random_scenario, language))}")
    choice = safe_input(t('prompt_play_scenario', language), language=language).strip().lower()
    if choice in ('y', ''):
        return random_scenario

    stats_map = {}
    if conn is not None and user_id is not None:
        stats_map = db.get_all_scenario_stats(conn, user_id)

    total_valid = len(valid_scenarios)
    displayed = valid_scenarios[:15]

    def _print_subset(subset, show_more=True):
        print(f"\n{t('available_scenarios', language)}")
        for (i, s) in enumerate(subset):
            s_stats = stats_map.get(s.name) if stats_map else None
            if s_stats and s_stats.get('plays', 0) > 0:
                mastery_key = s_stats.get('mastery', 'newbie')
                mastery_str = t(mastery_key, language)
                print(t('scenario_item_with_mastery', language, i=i + 1, name=scenario_name(s, language), n=len(s.tasks), mastery=mastery_str))
            else:
                print(t('scenario_item', language, i=i + 1, name=scenario_name(s, language), n=len(s.tasks)))
        if show_more and len(subset) < total_valid:
            more_count = total_valid - len(subset)
            print(t('more_scenarios', language, n=more_count))

    _print_subset(displayed, show_more=True)

    while True:
        sel = safe_input(f"\n{t('prompt_select_scenario', language)}", language=language).strip()
        if not sel:
            print(t('enter_valid_number', language))
            continue
        sel_lower = sel.lower()
        if sel_lower in ('quit', 'exit'):
            print(t('exiting', language))
            sys.exit(0)
        if sel_lower == 'all':
            displayed = valid_scenarios
            _print_subset(displayed, show_more=False)
            continue

        if sel.isdigit() or (sel.startswith('-') and sel[1:].isdigit()):
            idx = int(sel) - 1
            if 0 <= idx < len(displayed):
                return displayed[idx]
            else:
                print(t('invalid_number', language))
            continue

        query = sel_lower
        matches = [
            s for s in valid_scenarios
            if query in s.name.lower() or query in scenario_name(s, language).lower()
        ]
        if not matches:
            print(t('no_matching_scenarios', language, query=sel))
        else:
            displayed = matches
            _print_subset(displayed, show_more=False)


def choose_scenario(language: str, conn, user_id: int):
    """Pick a built-in scenario. Sessions are keyed by scenario name, so
    nothing needs persisting up front."""
    return select_builtin_scenario(language, conn=conn, user_id=user_id)
