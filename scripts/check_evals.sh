#!/usr/bin/env bash
#
# LLM-graded regression gate (OPEN-08).
#
# Deliberately NOT wired into check_all.sh or the CI workflow: every suite here
# needs MLX and a loaded 7B, and the four together take minutes, while the
# deterministic gate is expected to stay fast enough to run on every change.
# Run this by hand (or `make check-evals`) before shipping anything that touches
# a prompt, the judge, the coach, or the actor.
#
# Each suite prints one "Final ... Score: NN.N% (p/t)" line. That number is
# compared against eval/eval_baselines.json and a drop fails the gate. The judge
# additionally gates on its false-negative and false-positive counts, because a
# score that holds while false negatives grow is a regression the percentage
# alone hides — a learner who did the task being told they did not is the
# failure this project treats as worst.
#
# When a change legitimately moves a number, re-measure and edit
# eval/eval_baselines.json in the same commit, so the new floor is reviewed
# rather than silently absorbed.
#
# Usage:
#     ./scripts/check_evals.sh              # all suites
#     ./scripts/check_evals.sh coach judge  # only the named suites
set -eo pipefail

cd "$(dirname "$0")/.."

if [ -n "$VIRTUAL_ENV" ]; then
    PYTHON="python3"
elif [ -f "venv/bin/python3" ]; then
    PYTHON="./venv/bin/python3"
else
    PYTHON="python3"
fi

BASELINES="${EVAL_BASELINES:-eval/eval_baselines.json}"
LOGDIR="${EVAL_LOG_DIR:-.eval_logs}"
mkdir -p "$LOGDIR"

if [ ! -f "$BASELINES" ]; then
    echo "❌ No baselines file at $BASELINES" >&2
    exit 1
fi

declare -a SUITES
if [ "$#" -gt 0 ]; then
    SUITES=("$@")
else
    SUITES=(coach judge actor moods)
fi

failed=0

# Read one numeric field for a suite out of the baselines file.
baseline_field() {
    $PYTHON -c "
import json, sys
data = json.load(open('$BASELINES'))
suite = data.get(sys.argv[1])
if suite is None or sys.argv[2] not in suite:
    sys.exit(1)
print(suite[sys.argv[2]])
" "$1" "$2"
}

for suite in "${SUITES[@]}"; do
    script="scripts/eval_${suite}.py"
    log="$LOGDIR/${suite}.log"

    if [ ! -f "$script" ]; then
        echo "❌ Unknown suite '$suite' (no $script)" >&2
        failed=1
        continue
    fi

    echo "========================================================================"
    echo "Running eval suite: $suite"
    echo "========================================================================"

    if ! $PYTHON "$script" 2>&1 | tee "$log"; then
        echo "❌ $suite: suite crashed" >&2
        failed=1
        continue
    fi

    score=$(grep -oE 'Final [A-Za-z]*[ ]?Score: [0-9]+\.[0-9]+' "$log" | tail -1 \
            | grep -oE '[0-9]+\.[0-9]+$' || true)
    if [ -z "$score" ]; then
        echo "❌ $suite: no 'Final ... Score:' line in output" >&2
        failed=1
        continue
    fi

    min_score=$(baseline_field "$suite" min_score) || {
        echo "❌ $suite: no min_score baseline in $BASELINES" >&2
        failed=1
        continue
    }

    if awk "BEGIN{exit !($score + 0.0001 < $min_score)}"; then
        echo "❌ $suite REGRESSED: score ${score}% < baseline ${min_score}%" >&2
        failed=1
        continue
    fi
    echo "✅ $suite score ${score}% (baseline ${min_score}%)"

    # The judge's error *shape* matters as much as its score, so gate on it too.
    if [ "$suite" = "judge" ]; then
        suite_ok=1
        for kind in "false negatives:max_false_negatives" "false positives:max_false_positives"; do
            label="${kind%%:*}"
            field="${kind##*:}"
            actual=$(grep -oE "$label \(should [a-z]+, judged [a-z]+\): [0-9]+" "$log" \
                     | tail -1 | grep -oE '[0-9]+$' || true)
            allowed=$(baseline_field "$suite" "$field") || allowed=""
            if [ -z "$actual" ] || [ -z "$allowed" ]; then
                echo "❌ judge: could not read '$label' from output or baselines" >&2
                suite_ok=0
                continue
            fi
            if [ "$actual" -gt "$allowed" ]; then
                echo "❌ judge REGRESSED: $label $actual > baseline $allowed" >&2
                suite_ok=0
            else
                echo "✅ judge $label $actual (baseline $allowed)"
            fi
        done
        [ "$suite_ok" -eq 1 ] || failed=1
    fi
    echo ""
done

echo "========================================================================"
if [ "$failed" -eq 0 ]; then
    echo "✅ ALL EVAL SUITES MET THEIR BASELINES"
else
    echo "❌ EVAL REGRESSION — see failures above"
fi
echo "========================================================================"
exit "$failed"
