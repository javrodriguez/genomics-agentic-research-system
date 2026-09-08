# The bill and the machine

Every number in this file is read from a raw transcript or a server record by `costs.py`.
None is typed by hand.

**Dollars billed beyond the standing subscription: $0.**

The evidence for that claim, rather than the claim alone:

- each take's recorded environment shows no API-key variable, so no per-token API billing path was
  configured;
- the subscription login is the only Claude credential, and a placeholder is the only local one;
- there is no `.env` under `evals/gap-study/`;
- `grep -E "boto3|stripe|billing" evals/gap-study/*.py` returns nothing.

A billing page behind a login is listed `not checked — behind a login`.
The subscription fee itself is not attributed to this study.

## Per take

_(written by `costs.py` once takes exist; tokens by class and wall clock from first to last
timestamp in the raw JSONL)_

| task | half | model | take | input | cache read | cache write | output | wall clock |
|---|---|---|---|---|---|---|---|---|
| _(no take has run)_ | | | | | | | | |

## Pre-freeze walks

Read from the raw JSONL of each committed walk transcript. A walk is not a take and is never
graded; it is recorded here because it spends the same subscription.

| walk | model | input | cache read | cache write | output | wall clock |
|---|---|---|---|---|---|---|
| `template-adherence` 1 | `claude-opus-5` | 36 | 915,246 | 164,547 | 13,175 | 1.4 min |
| `template-adherence` 2 | `claude-opus-5` | 64 | 1,804,271 | 225,215 | 15,790 | 1.6 min |

**What this changes about the estimate.** The protocol's assumption sized the Claude axis from a
six-turn take of the first study: about 5.3 minutes and 5.5 to 6.4 M context tokens each, so about
9.5 hours serial for 108 takes.

Five of this study's task pairs use a two or three turn script rather than six. A two-turn walk
measures at 1.4 to 1.6 minutes and 1.1 to 2.0 M context tokens, of which the large majority are
cache reads. A three-turn take should land above that and well below the six-turn figure, which
puts the Claude axis nearer four to six hours than nine and a half.

That is an observation from two walks on one task, not a measurement of a take, and it is written
here so the estimate can be corrected against real takes rather than carried forward unexamined.

## Per model

_(totals, written by `costs.py`)_

| model | graded takes | context tokens | output tokens | wall clock |
|---|---|---|---|---|
| _(no take has run)_ | | | | |

## Recorded pauses

A pause is a rate-limit refusal before a take's first agent turn.
The driver waits for the window to reset and retries the same slot.
The study clock is paused across each interval below.

| started | ended | model | slot |
|---|---|---|---|
| _(none)_ | | | |

## Machine time

Local takes record measured wall clock rather than an estimate.
After each local block the driver commits the output of `ollama ps` and the Ollama entries of
`launchctl list`, both expected empty.

| block | model | window | wall clock | server left as found |
|---|---|---|---|---|
| _(none)_ | | | | |

## Notes recorded before any take

- One completed take of the first study's pair 2 on `claude-opus-5` measured 5.3 minutes wall and
  5.5 to 6.4 M context tokens, of which the large majority were cache reads. That shape is what the
  Claude axis estimate rests on.
- The cost of a local take is unmeasured until the fit walk measures it. The per-turn budget for a
  local model's cells is three times its slowest fit-walk turn, capped at 30 minutes.
- On 8 September 2026 the Opus **sub-agent** path returned a weekly-limit refusal while headless
  `claude -p` sessions on `claude-haiku-4-5-20251001`, `claude-sonnet-5` and `claude-opus-5` each
  answered a probe. Walks and takes use the headless path.
