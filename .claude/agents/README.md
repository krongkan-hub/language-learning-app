# The team

Four seats, matching the roles a small company would actually staff this with.
Each one is scoped so that it owns something and refuses things outside it —
an agent that will touch anything gives you no signal when it says "done".

| agent | owns | model |
|---|---|---|
| `llm-eval-lead` | the three prompts, the deterministic nets, every eval suite and its floors | opus |
| `web-dev` | web UI, CLI, session state machine, SQLite, i18n plumbing | sonnet |
| `ja-reviewer` | the Japanese the learner actually sees — **read-only** | opus |
| `qa-playtester` | playing the app and reporting what breaks — **does not fix** | sonnet |

## The seat that is deliberately missing

There is no PM or product-design agent, on purpose. The decisions that seat
makes — is the drill mandatory, is the scenario random, does the UI follow the
language being studied, what does 0/10 look like — are the owner's, and they
have been made well. An agent filling that seat would guess at them and the
project would lose the judgement it is currently strongest on.

## What these agents cannot do

`ja-reviewer` is the closest thing here to a native speaker, and it is not one.
It is far better at Japanese than the 7B whose output it reviews, which is why
it is worth having, but a real reviewer would still be the highest-value hire
for this project.

None of them can be trusted on their own report. Every one of them is
instructed to say what it did not run — hold them to it, and re-run the check
yourself when the claim matters.
