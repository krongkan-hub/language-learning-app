.PHONY: test check check-evals playtest eval

RANGE ?= 71-80
# Suites for check-evals; override to gate one at a time, e.g. SUITES=coach
SUITES ?=

test:
	./venv/bin/pytest

# Fast deterministic gate — the one CI runs.
check:
	./scripts/check_all.sh

# LLM-graded gate. Needs MLX and takes minutes, so it is kept out of `check`
# and out of CI on purpose (OPEN-08); run it before shipping prompt changes.
check-evals:
	./scripts/check_evals.sh $(SUITES)

playtest:
	./venv/bin/python scripts/ai_playtester.py $(RANGE)

eval:
	./venv/bin/python scripts/eval_coach.py
	./venv/bin/python scripts/eval_judge.py
	./venv/bin/python scripts/eval_actor.py
