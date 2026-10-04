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
# compared against dev/fixtures/eval_baselines.json and a drop fails the gate. The judge
# additionally gates on its false-negative and false-positive counts, because a
# score that holds while false negatives grow is a regression the percentage
# alone hides — a learner who did the task being told they did not is the
# failure this project treats as worst.
#
# When a change legitimately moves a number, re-measure and edit
# dev/fixtures/eval_baselines.json in the same commit, so the new floor is reviewed
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

BASELINES="${EVAL_BASELINES:-dev/fixtures/eval_baselines.json}"
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
    SUITES=(coach judge actor moods rawactor coachreason coachrecall explain jarecall jalength)
fi

failed=0

# A suite that stops producing output is killed and started again. Seen three
# times on 2026-09-25/26: eval_coach and eval_coachrecall sat at 0% CPU for
# 20+ minutes with the main thread parked on a Metal command buffer that never
# completed, GPU otherwise idle and 54% memory free — an MLX/Metal hang, not
# OOM, and not reproducible on demand. A case takes about a minute, so fifteen
# minutes of silence is a hang, never a slow case.
STALL_SECS="${EVAL_STALL_SECS:-900}"
RETRIES="${EVAL_RETRIES:-1}"
COOLDOWN_SECS="${EVAL_RETRY_COOLDOWN:-180}"
SCRIPT_DIR="${EVAL_SCRIPT_DIR:-dev/evals}"

mtime() { stat -f %m "$1" 2>/dev/null || stat -c %Y "$1"; }

# Run one suite into its log, streaming it, killing it on a stall.
# Returns 0 on success, 124 on a stall, else the script's own exit code.
run_watched() {
    local script="$1" log="$2" pid tailpid last now
    : > "$log"
    PYTHONUNBUFFERED=1 $PYTHON "$script" > "$log" 2>&1 &
    pid=$!
    tail -n +1 -f "$log" &
    tailpid=$!
    last=$(date +%s)
    local seen
    seen=$(mtime "$log")
    while kill -0 "$pid" 2>/dev/null; do
        sleep 2
        now=$(mtime "$log")
        if [ "$now" != "$seen" ]; then
            seen=$now
            last=$(date +%s)
        elif [ $(( $(date +%s) - last )) -ge "$STALL_SECS" ]; then
            # app/llm/client.py dumps every thread's stack on SIGUSR1, so the
            # log records WHERE it hung before the process is gone.
            echo "=== stalled ${STALL_SECS}s: thread dump (SIGUSR1) ===" >> "$log"
            kill -USR1 "$pid" 2>/dev/null; sleep 3
            kill "$pid" 2>/dev/null; sleep 1; kill -9 "$pid" 2>/dev/null
            wait "$pid" 2>/dev/null
            kill "$tailpid" 2>/dev/null; wait "$tailpid" 2>/dev/null
            return 124
        fi
    done
    local rc=0
    wait "$pid" || rc=$?
    sleep 0.5
    kill "$tailpid" 2>/dev/null; wait "$tailpid" 2>/dev/null
    return $rc
}

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
    script="$SCRIPT_DIR/eval_${suite}.py"
    log="$LOGDIR/${suite}.log"

    if [ ! -f "$script" ]; then
        echo "❌ Unknown suite '$suite' (no $script)" >&2
        failed=1
        continue
    fi

    echo "========================================================================"
    echo "Running eval suite: $suite"
    echo "========================================================================"

    attempt=0
    rc=0
    while :; do
        rc=0
        run_watched "$script" "$log" || rc=$?
        if [ "$rc" -eq 124 ] && [ "$attempt" -lt "$RETRIES" ]; then
            attempt=$((attempt + 1))
            echo "⚠️  $suite: no output for ${STALL_SECS}s — killed, retry $attempt/$RETRIES after ${COOLDOWN_SECS}s" >&2
            # Twice (2026-09-27, 2026-09-29) a retry started straight after
            # the kill stalled at once, while a fresh run minutes later passed:
            # give the GPU time to let go of the killed process first.
            sleep "$COOLDOWN_SECS"
            continue
        fi
        break
    done
    if [ "$rc" -eq 124 ]; then
        echo "❌ $suite: stalled (no output for ${STALL_SECS}s) on every attempt" >&2
        failed=1
        continue
    elif [ "$rc" -ne 0 ]; then
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
