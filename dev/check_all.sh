#!/usr/bin/env bash
set -eo pipefail

if [ -n "$VIRTUAL_ENV" ]; then
    PYTHON="python3"
    PYTEST="pytest"
    PYFLAKES="pyflakes"
elif [ -f "venv/bin/python3" ]; then
    PYTHON="./venv/bin/python3"
    PYTEST="./venv/bin/pytest"
    PYFLAKES="./venv/bin/pyflakes"
else
    PYTHON="python3"
    PYTEST="pytest"
    PYFLAKES="pyflakes"
fi

run_check() {
    local name="$1"
    shift
    echo "========================================================================"
    echo "Running check: $name"
    echo "========================================================================"
    if "$@"; then
        echo "✅ $name PASSED"
        echo ""
    else
        echo "❌ CHECK FAILED: $name" >&2
        exit 1
    fi
}

run_check "pytest" $PYTEST
run_check "pyflakes" $PYFLAKES app/ dev/ dev/tests/ main.py
run_check "check_task_depth" $PYTHON dev/checks/check_task_depth.py 1-80 --expect-total=5520
run_check "check_scenario_parity" $PYTHON dev/checks/check_scenario_parity.py 1-80
run_check "check_content_coherence" $PYTHON dev/checks/check_content_coherence.py
run_check "check_catalog_roundtrip" $PYTHON dev/checks/check_catalog_roundtrip.py
run_check "check_fixture_contamination" $PYTHON dev/checks/check_fixture_contamination.py
run_check "check_rule_vacuity" $PYTHON dev/checks/check_rule_vacuity.py
run_check "actor_path_parity" $PYTHON dev/checks/check_actor_path_parity.py

echo "========================================================================"
echo "Running check: coverage_floor"
echo "========================================================================"
# 80.0 was set when the suite measured 84; it has read 92 since, and a floor
# 12 points under the measurement stops being a floor — untested code walks
# in without the gate saying a word. 90 keeps two points of slack, which is
# more than this number moves: the tests are deterministic, so it only
# changes when someone adds or removes code.
if $PYTHON -m coverage run --source=app -m pytest -q && $PYTHON -m coverage report --fail-under=90; then
    echo "✅ coverage_floor PASSED"
    echo ""
else
    echo "❌ CHECK FAILED: coverage_floor" >&2
    exit 1
fi

echo "========================================================================"
echo "✅ ALL CHECKS PASSED"
echo "========================================================================"
