.PHONY: run stats test check check-evals playtest eval

RANGE ?= 71-80
# Extra arguments for `make run`, e.g. ARGS="--lang Japanese --tasks 5"
ARGS ?=

# A practice session in the terminal (python3 main.py).
run:
	./venv/bin/python main.py $(ARGS)

stats:
	./venv/bin/python main.py --stats $(ARGS)

# Suites for check-evals; override to gate one at a time, e.g. SUITES=coach
SUITES ?=

test:
	./venv/bin/pytest

# Fast deterministic gate — the one CI runs.
check:
	./dev/check_all.sh

# LLM-graded gate. Needs MLX and takes minutes, so it is kept out of `check`
# and out of CI on purpose (OPEN-08); run it before shipping prompt changes.
check-evals:
	./dev/check_evals.sh $(SUITES)

playtest:
	./venv/bin/python dev/playtest/ai_playtester.py $(RANGE)

# `make eval` used to run coach, judge and actor directly. That listed the
# suites in a second place, which is the drift CI already had once (two
# checks lived in check_all.sh and never in the workflow), and it compared
# nothing to dev/fixtures/eval_baselines.json — a suite could drop ten points
# and still print a cheerful score. It is now the gate, with the suite list
# in one place only.
eval: check-evals
