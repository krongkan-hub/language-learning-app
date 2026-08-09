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
run_check "pyflakes" $PYFLAKES app/ scripts/ main.py
run_check "check_task_depth" $PYTHON scripts/check_task_depth.py 1-80 --expect-total=5520
run_check "check_scenario_parity" $PYTHON scripts/check_scenario_parity.py 1-80
run_check "check_content_coherence" $PYTHON scripts/check_content_coherence.py
run_check "check_catalog_roundtrip" $PYTHON scripts/check_catalog_roundtrip.py

echo "========================================================================"
echo "Running check: coverage_floor"
echo "========================================================================"
if $PYTHON -m coverage run --source=app -m pytest -q && $PYTHON -m coverage report --fail-under=80; then
    echo "✅ coverage_floor PASSED"
    echo ""
else
    echo "❌ CHECK FAILED: coverage_floor" >&2
    exit 1
fi

echo "========================================================================"
echo "✅ ALL CHECKS PASSED"
echo "========================================================================"
