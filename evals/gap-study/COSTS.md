# The bill and the machine

Every table below is written by `costs.py --write` from the raw transcripts and the driver ledgers.
`test_harness.py TheBillIsWrittenByTheReader` fails when this file differs from what it writes.
Until 11 September 2026 this line said no number here was typed by hand, while the flag wrote nothing and the walk table had been typed.
The notes quote measurements and say where each came from.

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
| `confounded-design` 1 | `claude-opus-5` | 1,044 | 2,079,813 | 217,311 | 18,535 | 2.1 min |
| `confounded-design` 2 | `claude-opus-5` | 1,016 | 2,236,924 | 189,522 | 15,448 | 2.3 min |
| `number-fidelity` 1 | `claude-opus-5` | 62 | 1,780,649 | 200,709 | 19,350 | 2.0 min |
| `number-fidelity` 2 | `claude-opus-5` | 552 | 867,536 | 154,112 | 9,893 | 1.3 min |
| `plan-gate` 1 | `claude-opus-5` | 78 | 2,388,585 | 202,326 | 31,394 | 2.4 min |
| `plan-gate` 2 | `claude-opus-5` | 106 | 3,277,805 | 215,951 | 59,732 | 4.0 min |
| `precondition-refusal` 1 | `claude-opus-5` | 36 | 930,085 | 128,454 | 6,691 | 0.6 min |
| `precondition-refusal` 2 | `claude-opus-5` | 30 | 696,271 | 129,190 | 5,833 | 0.6 min |
| `scope-read` 1 | `claude-opus-5` | 62 | 1,703,891 | 190,796 | 14,075 | 1.5 min |
| `template-adherence` 1 | `claude-opus-5` | 36 | 915,246 | 164,547 | 13,175 | 1.4 min |
| `template-adherence` 2 | `claude-opus-5` | 64 | 1,804,271 | 225,215 | 15,790 | 1.6 min |

**What this changed about the estimate, written on 8 September 2026 from the first two walks.** The protocol's assumption sized the Claude axis from a
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
