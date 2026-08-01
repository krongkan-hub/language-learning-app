.PHONY: test playtest eval

RANGE ?= 71-80

test:
	./venv/bin/pytest

playtest:
	./venv/bin/python scripts/ai_playtester.py $(RANGE)

eval:
	./venv/bin/python scripts/eval_coach.py
	./venv/bin/python scripts/eval_judge.py
	./venv/bin/python scripts/eval_actor.py
