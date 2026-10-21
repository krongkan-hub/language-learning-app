"""Terminal plumbing: the thinking spinner and an input() that handles quit.
"""
from ..i18n import t
import sys


import threading
import time


class Spinner:
    """A console spinner that always stops.

    `daemon=True` and the context-manager protocol are both deliberate. The
    thread used to be non-daemon and was stopped by name in one handler, so a
    mid-turn MLX error left `eval_spinner` or `coach_spinner` running: it wrote
    over the learner's `You:` prompt for the rest of the session AND blocked
    interpreter exit, so the process never terminated on `quit` (OPEN-24).
    `with Spinner(...)` makes the stop unconditional; `daemon=True` means even a
    leak that escapes it cannot hold the process open.
    """

    def __init__(self, message="Thinking"):
        self.message = message
        self.running = False
        self.spinner = threading.Thread(target=self._spin, daemon=True)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.stop()
        return False

    def _spin(self):
        chars = "|/-\\"
        idx = 0
        while self.running:
            sys.stdout.write(f"\r[{self.message}... {chars[idx % len(chars)]}] ")
            sys.stdout.flush()
            idx += 1
            time.sleep(0.1)

    def start(self):
        self.running = True
        self.spinner.start()

    def stop(self):
        # Idempotent: __exit__ may run after an explicit stop() on the happy path.
        if not self.running and not self.spinner.is_alive():
            return
        self.running = False
        self.spinner.join()
        sys.stdout.write("\r\033[K") # Clear the line
        sys.stdout.flush()


def safe_input(prompt: str = "", language: str = 'English', on_exit=None) -> str:
    """Wrap input() to handle EOFError and KeyboardInterrupt with a clean exit and session cleanup."""
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        print(t('exiting', language or 'English'))
        if on_exit:
            on_exit()
        sys.exit(0)
