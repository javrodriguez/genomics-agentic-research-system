# The bill and the machine

Every table below, and the line under the first heading, is written by `costs.py --write` from the raw transcripts, the driver ledgers and each take's environment record.
`costs.py --check` fails when this file differs from what it writes.
Everything under `## Dollars billed beyond the standing subscription` is the script's; a note goes under a heading of its own.

## Dollars billed beyond the standing subscription

$0, evidenced by 2 of 2 environment records (no API-key variable set; the harness reported credential source none on every turn)

## Per take

| task | half | model | take | input | cache read | cache write | output | wall clock | environment |
|---|---|---|---|---|---|---|---|---|---|
| `number-fidelity` | positive | `claude-opus-5` | 1 | 32 | 412,731 | 58,717 | 5,412 | 0.8 min | evidenced |
| `plan-gate` | control | `claude-opus-5` | 1 | 60 | 1,188,845 | 109,886 | 26,143 | 2.0 min | evidenced |

## Pre-freeze walks

| walk | model | input | cache read | cache write | output | wall clock |
|---|---|---|---|---|---|---|
| `confounded-design` 1 | `claude-sonnet-5` | 74 | 1,628,503 | 86,139 | 10,063 | 1.8 min |
| `number-fidelity` 1 | `claude-sonnet-5` | 54 | 1,071,105 | 67,322 | 11,990 | 1.6 min |
| `plan-gate` 1 | `claude-sonnet-5` | 78 | 1,680,927 | 104,397 | 19,659 | 1.7 min |
| `precondition-refusal` 1 | `claude-sonnet-5` | 20 | 293,559 | 56,688 | 3,776 | 0.6 min |
| `scope-read` 1 | `claude-sonnet-5` | 68 | 1,435,740 | 69,697 | 13,630 | 1.6 min |
| `template-adherence` 1 | `claude-sonnet-5` | 58 | 1,167,889 | 72,187 | 13,901 | 2.4 min |

## Per model

| model | graded takes | context tokens | output tokens | wall clock |
|---|---|---|---|---|
| `claude-opus-5` | 2 | 1,770,271 | 31,555 | 2.8 min |

## Recorded pauses

| started | ended | model | slot |
|---|---|---|---|
| _(none)_ | | | |
