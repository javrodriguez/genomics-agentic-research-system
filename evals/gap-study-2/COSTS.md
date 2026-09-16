# The bill and the machine

Every table below, and the line under the first heading, is written by `costs.py --write` from the raw transcripts, the driver ledgers and each take's environment record.
`costs.py --check` fails when this file differs from what it writes.
Everything under `## Dollars billed beyond the standing subscription` is the script's; a note goes under a heading of its own.

## Dollars billed beyond the standing subscription

$0 as the operator states it; evidenced by 0 of 0; not evidenced: no graded take is on disk, so no environment record exists to evidence it

## Per take

| task | half | model | take | input | cache read | cache write | output | wall clock | environment |
|---|---|---|---|---|---|---|---|---|---|
| _(no take has run)_ | | | | | | | | | |

## Pre-freeze walks

| walk | model | input | cache read | cache write | output | wall clock |
|---|---|---|---|---|---|---|
| `confounded-design` 1 | `claude-sonnet-5` | 74 | 1,628,503 | 86,139 | 10,063 | 1.8 min |
| `number-fidelity` 1 | `claude-sonnet-5` | 54 | 1,071,105 | 67,322 | 11,990 | 1.6 min |
| `precondition-refusal` 1 | `claude-sonnet-5` | 20 | 293,559 | 56,688 | 3,776 | 0.6 min |
| `scope-read` 1 | `claude-sonnet-5` | 68 | 1,435,740 | 69,697 | 13,630 | 1.6 min |
| `template-adherence` 1 | `claude-sonnet-5` | 58 | 1,167,889 | 72,187 | 13,901 | 2.4 min |

## Per model

| model | graded takes | context tokens | output tokens | wall clock |
|---|---|---|---|---|
| _(no take has run)_ | | | | |

## Recorded pauses

| started | ended | model | slot |
|---|---|---|---|
| _(none)_ | | | |
