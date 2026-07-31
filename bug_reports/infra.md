# Bug Reports — Infrastructure / packaging / error handling

### BUG-031 · OPEN · High (breaks fresh installs)
**First run is broken for a new install.** `main.py:5` sets
`os.environ['HF_HUB_OFFLINE'] = '1'` *before* importing `app.cli` (which
loads the MLX model at import time), but `setup.sh` says: "Setup complete!
The MLX model will be downloaded automatically on first run." Confirmed both
still true in the current working tree — `HF_HUB_OFFLINE=1` blocks any
network fetch, so an uncached model raises `LocalEntryNotFoundError` and the
user sees only "Error: Could not initialize MLX model ... Exiting." with no
indication they need to pre-download ~4GB. *Fix:* either have `setup.sh`
actually pre-pull the model (`python -c "from mlx_lm import load;
load('mlx-community/Qwen2.5-7B-Instruct-4bit')"`) or don't force offline
mode on first run — e.g. only set `HF_HUB_OFFLINE=1` after confirming the
model is cached locally.

### BUG-032 · OPEN · Medium
**`MLX_ERRORS = (Exception,)` is too broad.** Confirmed unchanged in
`app/llm.py`. Any ordinary bug anywhere in the coach→judge→actor call chain
(e.g. a `TypeError` inside `filter_coach_output`) gets caught and reported to
the learner as a generic "⚠️ MLX Engine Error", silently dropping their turn.
This will hide real defects from both users and `qa_agent`'s playtests going
forward. *Fix:* narrow to the actual MLX/runtime exception types the model
load/generate calls can raise; let unrelated bugs propagate and crash loudly
in dev/test.

### BUG-033 · OPEN · Low (UX)
**No latency indicator.** Each turn takes ~20-40s (worst observed 40s;
greeting 18-28s) with the coach and judge calls producing completely silent
dead air — no spinner, no "thinking..." indicator. Breaks conversational
flow. Cheap fix (a spinner/elapsed-time print during the blocking calls in
`app/cli.py`) — verify still applicable given `app/cli.py`'s large diff.

### BUG-035 · FIXED (verified by re-run) · Medium
**`scripts/eval_coach.py` was broken — stale import from a pre-refactor
module layout.** It did `from main import _llm_chat, filter_coach_output,
COACH_SYS, COACH_OPTS`, but `main.py` only does `from app.cli import main`
and never re-exports those names — left over from before the "three-call
pipeline" refactor (commit `22441a8`) split the coach logic into
`app/coach.py` and the model call into `app/llm.py`. It also inserted
`scripts/`'s own directory onto `sys.path` rather than the repo root, so
`import main` couldn't have resolved even if `main.py` did export them.
Net effect: the harness's only automated coach-regression runner has been
non-functional since that refactor — nobody could have been running it to
catch the exact class of regression this bug-report set documents.
*Fixed:* imports now pull `_llm_chat` from `app.llm` and
`filter_coach_output`/`COACH_SYS`/`COACH_OPTS` from `app.coach` directly;
`sys.path` now inserts the repo root. Verified by re-running it — see
`eval/` results referenced from `BACKLOG.md`.

### BUG-034 · OPEN · Low (repo hygiene)
**Stray untracked runtime artifacts in the repo root.** `language_coach.db`
(should be `~/.language-coach/sessions.db` per the app's actual DB path) and
`db_dump.txt` sit untracked in the repo root; `.gitignore` doesn't exclude
`*.db` or `db_dump.txt`. Low risk (untracked, so not yet committed) but worth
adding to `.gitignore` before someone `git add -A`s them by accident.
