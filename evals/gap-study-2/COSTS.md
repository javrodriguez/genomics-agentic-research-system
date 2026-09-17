# The bill and the machine

Every table below, and the line under the first heading, is written by `costs.py --write` from the raw transcripts, the driver ledgers and each take's environment record.
`costs.py --check` fails when this file differs from what it writes.
Everything under `## Dollars billed beyond the standing subscription` is the script's; a note goes under a heading of its own.

## Dollars billed beyond the standing subscription

$0, evidenced by 40 of 40 environment records (no API-key variable set; the harness reported credential source none on every turn)

## Per take

| task | half | model | take | input | cache read | cache write | output | wall clock | environment |
|---|---|---|---|---|---|---|---|---|---|
| `confounded-design` | control | `claude-haiku-4-5-20251001` | 2 | 128 | 343,696 | 63,030 | 6,327 | 0.5 min | evidenced |
| `confounded-design` | control | `claude-sonnet-5` | 3 | 72 | 1,627,672 | 82,941 | 11,290 | 2.1 min | evidenced |
| `confounded-design` | positive | `claude-haiku-4-5-20251001` | 1 | 118 | 305,859 | 51,002 | 3,751 | 0.3 min | evidenced |
| `confounded-design` | positive | `claude-haiku-4-5-20251001` | 2 | 160 | 605,469 | 102,090 | 6,651 | 0.6 min | evidenced |
| `confounded-design` | positive | `claude-opus-5` | 2 | 70 | 1,255,297 | 68,153 | 10,597 | 2.2 min | evidenced |
| `confounded-design` | positive | `claude-sonnet-5` | 1 | 108 | 2,772,819 | 107,712 | 24,475 | 4 min | evidenced |
| `number-fidelity` | control | `claude-haiku-4-5-20251001` | 1 | 110 | 297,217 | 48,204 | 4,208 | 0.3 min | evidenced |
| `number-fidelity` | control | `claude-haiku-4-5-20251001` | 2 | 166 | 466,320 | 50,818 | 6,850 | 0.6 min | evidenced |
| `number-fidelity` | control | `claude-opus-5` | 3 | 38 | 551,387 | 50,331 | 5,129 | 1.1 min | evidenced |
| `number-fidelity` | positive | `claude-haiku-4-5-20251001` | 2 | 110 | 275,668 | 47,023 | 5,485 | 0.5 min | evidenced |
| `number-fidelity` | positive | `claude-opus-5` | 1 | 32 | 412,731 | 58,717 | 5,412 | 0.8 min | evidenced |
| `number-fidelity` | positive | `claude-sonnet-5` | 1 | 88 | 1,994,177 | 75,731 | 17,027 | 2.8 min | evidenced |
| `number-fidelity` | positive | `claude-sonnet-5` | 2 | 42 | 788,328 | 54,673 | 5,811 | 1.4 min | evidenced |
| `plan-gate` | control | `claude-haiku-4-5-20251001` | 2 | 382 | 1,312,275 | 51,878 | 12,495 | 1.2 min | evidenced |
| `plan-gate` | control | `claude-opus-5` | 1 | 60 | 1,188,845 | 109,886 | 26,143 | 2 min | evidenced |
| `plan-gate` | control | `claude-opus-5` | 2 | 78 | 1,593,971 | 107,179 | 33,864 | 2.7 min | evidenced |
| `plan-gate` | control | `claude-opus-5` | 3 | 64 | 1,363,193 | 137,754 | 41,774 | 2.6 min | evidenced |
| `plan-gate` | control | `claude-sonnet-5` | 3 | 160 | 4,954,397 | 170,462 | 54,870 | 5.1 min | evidenced |
| `plan-gate` | positive | `claude-haiku-4-5-20251001` | 2 | 406 | 1,402,523 | 58,055 | 12,471 | 1.2 min | evidenced |
| `plan-gate` | positive | `claude-haiku-4-5-20251001` | 3 | 430 | 1,602,087 | 65,608 | 15,724 | 1.4 min | evidenced |
| `plan-gate` | positive | `claude-opus-5` | 1 | 34 | 476,678 | 43,176 | 9,457 | 1 min | evidenced |
| `plan-gate` | positive | `claude-sonnet-5` | 3 | 104 | 2,546,267 | 107,218 | 26,274 | 2.8 min | evidenced |
| `precondition-refusal` | control | `claude-haiku-4-5-20251001` | 2 | 102 | 233,307 | 20,846 | 3,278 | 0.3 min | evidenced |
| `precondition-refusal` | control | `claude-haiku-4-5-20251001` | 3 | 166 | 444,920 | 45,882 | 4,016 | 0.4 min | evidenced |
| `precondition-refusal` | control | `claude-opus-5` | 1 | 22 | 274,812 | 31,039 | 4,295 | 0.7 min | evidenced |
| `precondition-refusal` | control | `claude-sonnet-5` | 1 | 40 | 691,981 | 67,218 | 9,712 | 1.1 min | evidenced |
| `precondition-refusal` | control | `claude-sonnet-5` | 2 | 28 | 434,442 | 49,527 | 5,402 | 0.7 min | evidenced |
| `precondition-refusal` | positive | `claude-opus-5` | 1 | 14 | 149,569 | 26,386 | 1,710 | 0.3 min | evidenced |
| `precondition-refusal` | positive | `claude-sonnet-5` | 1 | 34 | 532,463 | 62,257 | 6,421 | 0.8 min | evidenced |
| `precondition-refusal` | positive | `claude-sonnet-5` | 2 | 24 | 360,952 | 36,495 | 3,792 | 0.5 min | evidenced |
| `scope-read` | control | `claude-haiku-4-5-20251001` | 1 | 294 | 938,447 | 60,185 | 9,665 | 0.9 min | evidenced |
| `scope-read` | control | `claude-haiku-4-5-20251001` | 2 | 110 | 285,393 | 49,152 | 4,567 | 0.4 min | evidenced |
| `scope-read` | control | `claude-opus-5` | 1 | 32 | 445,108 | 46,000 | 5,592 | 0.9 min | evidenced |
| `scope-read` | positive | `claude-haiku-4-5-20251001` | 3 | 102 | 263,346 | 47,042 | 4,730 | 0.4 min | evidenced |
| `scope-read` | positive | `claude-opus-5` | 3 | 32 | 446,454 | 45,454 | 5,041 | 0.7 min | evidenced |
| `scope-read` | positive | `claude-sonnet-5` | 1 | 68 | 1,462,003 | 76,457 | 17,617 | 2.3 min | evidenced |
| `template-adherence` | control | `claude-haiku-4-5-20251001` | 3 | 136 | 479,891 | 126,035 | 6,533 | 0.4 min | evidenced |
| `template-adherence` | control | `claude-opus-5` | 1 | 40 | 556,895 | 50,736 | 5,940 | 1.1 min | evidenced |
| `template-adherence` | control | `claude-opus-5` | 3 | 52 | 774,454 | 52,925 | 6,270 | 1.3 min | evidenced |
| `template-adherence` | positive | `claude-opus-5` | 1 | 28 | 393,987 | 43,554 | 3,648 | 0.9 min | evidenced |

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
| `claude-haiku-4-5-20251001` | 15 | 10,146,188 | 106,751 | 9.4 min |
| `claude-opus-5` | 14 | 10,755,267 | 164,872 | 18.3 min |
| `claude-sonnet-5` | 11 | 19,056,960 | 182,691 | 23.6 min |

## Recorded pauses

| started | ended | model | slot |
|---|---|---|---|
| _(none)_ | | | |
