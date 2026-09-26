"""The command-line front end.

    game.py      main(): the session loop, and every call into the model
    menus.py     choosing a scenario, the stats report, vocab review, drill
    terminal.py  the spinner and quit-aware input()

The model functions main() uses (call_coach, evaluate_task, stream_actor...)
are deliberately NOT re-exported here: a test must patch them where main()
looks them up, app.cli.game, and an attribute missing from this package makes
a wrongly aimed patch fail loudly instead of silently patching nothing.
"""
from ..scenarios.builtins import SCENARIOS
from ..vocab_card import (_is_name, _is_trivial_vocab, _is_venue_noun,
                          extract_and_format_vocab, parse_vocab)
from .game import MAX_TASK_ATTEMPTS, _retrieve_review_words, main
from .menus import (choose_scenario, print_stats_report, run_correction_drill,
                    run_vocab_review, select_builtin_scenario)
from .terminal import safe_input

__all__ = ['SCENARIOS', '_is_name', '_is_trivial_vocab', '_is_venue_noun',
           'extract_and_format_vocab', 'parse_vocab', 'MAX_TASK_ATTEMPTS',
           '_retrieve_review_words', 'main', 'choose_scenario',
           'print_stats_report', 'run_correction_drill', 'run_vocab_review',
           'select_builtin_scenario', 'safe_input']
