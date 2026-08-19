#!/usr/bin/env python3
"""Fail if an eval fixture is quoted verbatim inside the prompt it grades.

A fixture whose input appears in its own system prompt is not measuring the
model, it is measuring copy-paste: the answer is handed over in the examples
block, so the case cannot fail no matter how the model behaves.

This was found by accident. Deleting one worked example from COACH_SYS dropped
its twin fixture from 5/5 to 0/5, which turned out to mean 6 of the 46 coach
cases were verbatim prompt examples and could never have failed. Excluding
them moved the honest coach score from 63.0% to 57.5%.

Cases deliberately kept as a documented control are tagged `prompt_example`
in the fixture file and skipped here. Everything else must be novel.

Deterministic, no model required, runs in milliseconds — which is why it sits
in check_all.sh rather than in the LLM eval gate.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.coach import COACH_SYS
from app.llm import GREETING_SYS
from app.judge import _judge_prompt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Short strings collide by accident rather than by contamination: a two-word
# fixture may legitimately share wording with a prompt rule.
MIN_LENGTH = 12


def _fixture_path(name):
    return os.path.join(ROOT, 'eval', name)


def _texts(case):
    """The learner-authored fields of a case — what the model is asked to judge."""
    for key in ('input', 'user_input', 'learner', 'done_when'):
        value = case.get(key)
        if isinstance(value, str) and len(value.strip()) >= MIN_LENGTH:
            yield key, value.strip()


def check(fixture_name, prompt_text, label):
    path = _fixture_path(fixture_name)
    if not os.path.exists(path):
        return []
    with open(path, encoding='utf-8') as fh:
        cases = json.load(fh)

    findings = []
    for index, case in enumerate(cases, 1):
        if case.get('prompt_example'):
            continue
        for key, text in _texts(case):
            if text in prompt_text:
                findings.append((label, index, key, text))
    return findings


def main():
    judge_prompt = _judge_prompt('', '', '', 'English')
    checks = [
        ('coach_cases.json', COACH_SYS, 'coach'),
        ('judge_cases.json', judge_prompt, 'judge'),
        ('actor_cases.json', GREETING_SYS, 'actor'),
    ]

    findings = []
    for fixture_name, prompt_text, label in checks:
        findings.extend(check(fixture_name, prompt_text, label))

    print('=' * 78)
    print('FIXTURE CONTAMINATION CHECK')
    print('=' * 78)

    if findings:
        print()
        for label, index, key, text in findings:
            print(f'❌ {label} case {index}: `{key}` appears verbatim in the prompt')
            print(f'   {text[:90]}')
        print()
        print(f'{len(findings)} contaminated fixture(s). Such a case cannot fail —')
        print('the prompt hands the model the answer, so it grades copy-paste.')
        print('Rewrite the fixture with a novel sentence testing the same error')
        print('class, or tag it `"prompt_example": true` if it is kept on purpose')
        print('as a documented control.')
        return 1

    for _, _, label in checks:
        print(f'✅ {label}: no fixture is quoted in its own prompt')
    print()
    print('=' * 78)
    print('✅ FIXTURE CONTAMINATION CHECK PASSED')
    print('=' * 78)
    return 0


if __name__ == '__main__':
    sys.exit(main())
