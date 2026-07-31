.PHONY: test playtest eval

test:
	./venv/bin/pytest

playtest:
	./venv/bin/python scripts/ai_playtester.py

eval:
	./venv/bin/python scripts/eval_coach.py
	./venv/bin/python scripts/eval_judge.py
	./venv/bin/python scripts/eval_actor.py
