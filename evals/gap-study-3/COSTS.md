# The bill and the machine

Every table below, and the line under the first heading, is written by `costs.py --write` from the raw transcripts, the driver ledgers and each take's environment record.
`costs.py --check` fails when this file differs from what it writes.
Everything under `## Dollars billed beyond the standing subscription` is the script's; a note goes under a heading of its own.

## Dollars billed beyond the standing subscription

$0, evidenced by 8 of 8 environment records (no API-key variable set; the harness reported credential source none on every turn)

## Per take

| task | half | model | take | input | cache read | cache write | output | wall clock | environment |
|---|---|---|---|---|---|---|---|---|---|
| `confounded-design` | control | `claude-haiku-4-5-20251001` | 3 | 138 | 349,018 | 70,782 | 8,317 | 0.6 min | evidenced |
| `confounded-design` | control | `claude-opus-5` | 1 | 84 | 1,624,799 | 111,177 | 16,566 | 2.3 min | evidenced |
| `confounded-design` | control | `claude-opus-5` | 2 | 90 | 1,758,931 | 94,627 | 14,970 | 2.4 min | evidenced |
| `confounded-design` | control | `claude-sonnet-5` | 2 | 120 | 3,037,446 | 108,153 | 26,734 | 4.1 min | evidenced |
| `confounded-design` | positive | `claude-haiku-4-5-20251001` | 2 | 312 | 1,593,914 | 106,755 | 12,791 | 1 min | evidenced |
| `scope-read` | control | `claude-haiku-4-5-20251001` | 2 | 352 | 1,238,982 | 73,396 | 12,913 | 1 min | evidenced |
| `template-adherence` | control | `claude-haiku-4-5-20251001` | 3 | 368 | 1,889,272 | 123,460 | 12,720 | 1.1 min | evidenced |
| `template-adherence` | positive | `claude-opus-5` | 2 | 46 | 706,841 | 65,935 | 8,567 | 1.2 min | evidenced |

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
| `claude-haiku-4-5-20251001` | 4 | 5,446,749 | 46,741 | 3.7 min |
| `claude-opus-5` | 3 | 4,362,530 | 40,103 | 5.9 min |
| `claude-sonnet-5` | 1 | 3,145,719 | 26,734 | 4.1 min |

## Recorded pauses

| started | ended | model | slot |
|---|---|---|---|
| _(none)_ | | | |
