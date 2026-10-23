"""The command-line front end — the only one since 2026-10-21 (ADR-006).

    game.py      main(): setup, the session loop, and printing its events
    menus.py     choosing a language, a mode, a scenario or topic; --stats
    state.py     a session's state, how one starts, skip and the drill check
    turns.py     everything that calls the model (judge -> actor -> coach)
    terminal.py  the spinner and quit-aware input()

The model functions (call_coach, evaluate_task, stream_actor...) are looked up
on app.cli.turns, so that is where a test patches them.
"""
from .game import main

__all__ = ['main']
