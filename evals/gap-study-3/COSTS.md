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
| `confounded-design` 1 | `claude-haiku-4-5-20251001` | 342 | 1,260,713 | 79,501 | 10,306 | 1.3 min |
| `confounded-design` 2 | `claude-haiku-4-5-20251001` | 130 | 332,412 | 56,729 | 7,640 | 0.5 min |
| `scope-read` 1 | `claude-haiku-4-5-20251001` | 258 | 917,293 | 69,760 | 12,537 | 1.1 min |
| `scope-read` 2 | `claude-haiku-4-5-20251001` | 272 | 1,316,938 | 136,720 | 10,400 | 0.8 min |
| `template-adherence` 1 | `claude-sonnet-5` | 50 | 983,459 | 70,225 | 17,498 | 1.9 min |
| `template-adherence` 2 | `claude-haiku-4-5-20251001` | 268 | 910,107 | 72,949 | 10,566 | 0.7 min |
| `template-adherence` 3 | `claude-sonnet-5` | 44 | 797,568 | 57,458 | 6,923 | 0.9 min |
| `template-adherence` 4 | `claude-opus-5` | 40 | 533,449 | 83,780 | 8,035 | 0.8 min |

## Per model

| model | graded takes | context tokens | output tokens | wall clock |
|---|---|---|---|---|
| _(no take has run)_ | | | | |

## Recorded pauses

| started | ended | model | slot |
|---|---|---|---|
| _(none)_ | | | |
