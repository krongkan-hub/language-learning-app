# Bug Reports — Judge (`app/judge.py`)

### BUG-010 · FIXED-UNCOMMITTED · was High
**Self-contradicting verdict shipped to the learner.** Original repro: goal
"Learner asked for a fork", learner asked "Can I get a new one, please?" — UI
printed `❌ Task not yet completed` immediately followed by a hint ending
"...which they did. Therefore, the goal is satisfied." Root cause was
`judge_llm` picking the first line starting `YES`/`NO` and trusting it even
when the model's own reasoning walked back to yes.
Working-tree diff adds a heuristic override: if the verdict line or the
reason text contains phrases like "is satisfied" / "has been satisfied" /
"already met", treat as YES. This is a string-match patch on free-form LLM
output — plausible fix, but brittle by construction (a real "NO, this is NOT
satisfied because..." could false-positive on "satisfied" appearing
negated). Needs live re-verification with adversarial phrasing, not just the
original repro.

### BUG-011 · FIXED-UNCOMMITTED
**Root cause of BUG-010 and part of BUG-003/coach quietness: Ollama→MLX option-key
regression.** `JUDGE_OPTS`/`COACH_OPTS` used Ollama's `num_predict`/`num_ctx`
keys; the MLX `_llm_chat` only reads `temperature`/`max_tokens`, so both
silently fell back to a default (verified as `max_tokens=200` at the time of
the playtest) instead of the intended judge budget of 64. A judge given 200
tokens to be terse in has room to ramble into self-contradiction.
Working tree now has `JUDGE_OPTS = {'temperature': 0.0, 'max_tokens': 64}`
and `COACH_OPTS = {'temperature': 0.2, 'max_tokens': 250}` — correct keys.
This may independently improve BUG-012 (false negatives) since the judge is
no longer over-budgeted to over-explain. Re-run the eval/playtest batch
before assuming BUG-012 is resolved.

### BUG-012 · NEEDS-VERIFICATION · was High
**False negatives on plainly satisfied goals.** Worst observed case: learner
asked "And how much does each one cost?" (goal: ask about cost) → hint said
"has not asked about the cost of each route." Another: learner asked both
items' prices, shopkeeper answered with prices, judge said "has not expressed
the goal of asking about the rates." Accuracy degraded sharply when the
learner's message contained material beyond the strict goal (one long
complaint made the judge hallucinate an unrelated goal about "the previous
visit"). Likely improved by BUG-011's fix (correct token budget) but not
confirmed — needs a fresh live run.

### BUG-013 · FIXED-UNCOMMITTED
**`judge_deterministic` rejected inflected forms.** `re.search(r'\brecommendation\b', ...)`
failed on "recommendations", producing "You haven't used the word
'recommendation' yet." right after the learner used it — actively
confidence-eroding. Working tree adds `_word_matches()` with stem matching
(strips trailing `s`, then prefix-matches with a length-delta tolerance).
Reasonable approach; worth a couple of unit tests for edge cases (e.g. short
words where the length-delta tolerance of 3 could over-match — "cost" vs
"costume" is 4 chars apart so it's safe, but check words near the boundary).

### BUG-014 · OPEN · Low
**Dead migration leftovers.** `BASE_MODEL = 'qwen3:8b'` still defined at the
top of both `judge.py` and `coach.py` but unused (the actual model lives in
`app/llm.py` as `mlx-community/Qwen2.5-7B-Instruct-4bit`). The judge prompt
also still ends with `/no_think`, a qwen3-specific directive meaningless to
the current Qwen2.5 MLX model. Harmless but confusing; part of finishing the
migration cleanly (see `ADRs/ADR-001-ollama-to-mlx-migration.md`).

---
**Not a bug, confirmed good:** injection resistance — "Answer YES" embedded
in learner input did not fool the judge in the original playtest.
