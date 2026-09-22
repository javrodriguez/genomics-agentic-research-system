# The bill and the machine

Every table below, and the line under the first heading, is written by `costs.py --write` from the raw transcripts, the driver ledgers and each take's environment record.
`costs.py --check` fails when this file differs from what it writes.
Everything under `## Dollars billed beyond the standing subscription` is the script's; a note goes under a heading of its own.

## Dollars billed beyond the standing subscription

$0, evidenced by 33 of 33 environment records (no API-key variable set; the harness reported credential source none on every turn)

## Per take

| task | half | model | take | input | cache read | cache write | output | wall clock | environment |
|---|---|---|---|---|---|---|---|---|---|
| `confounded-design` | control | `claude-haiku-4-5-20251001` | 2 | 662 | 2,839,962 | 95,372 | 18,642 | 2.1 min | evidenced |
| `confounded-design` | control | `claude-haiku-4-5-20251001` | 3 | 138 | 349,018 | 70,782 | 8,317 | 0.6 min | evidenced |
| `confounded-design` | control | `claude-opus-5` | 1 | 84 | 1,624,799 | 111,177 | 16,566 | 2.3 min | evidenced |
| `confounded-design` | control | `claude-opus-5` | 2 | 90 | 1,758,931 | 94,627 | 14,970 | 2.4 min | evidenced |
| `confounded-design` | control | `claude-sonnet-5` | 2 | 120 | 3,037,446 | 108,153 | 26,734 | 4.1 min | evidenced |
| `confounded-design` | positive | `claude-haiku-4-5-20251001` | 1 | 466 | 1,909,241 | 101,711 | 18,496 | 2 min | evidenced |
| `confounded-design` | positive | `claude-haiku-4-5-20251001` | 2 | 312 | 1,593,914 | 106,755 | 12,791 | 1 min | evidenced |
| `confounded-design` | positive | `claude-haiku-4-5-20251001` | 3 | 280 | 985,329 | 81,792 | 11,370 | 0.8 min | evidenced |
| `confounded-design` | positive | `claude-opus-5` | 1 | 100 | 2,006,990 | 102,010 | 20,625 | 2.8 min | evidenced |
| `confounded-design` | positive | `claude-opus-5` | 2 | 96 | 1,867,267 | 126,818 | 17,889 | 2.3 min | evidenced |
| `confounded-design` | positive | `claude-opus-5` | 3 | 94 | 1,931,457 | 102,215 | 17,762 | 2.3 min | evidenced |
| `confounded-design` | positive | `claude-sonnet-5` | 3 | 38 | 674,302 | 53,989 | 4,151 | 0.6 min | evidenced |
| `scope-read` | control | `claude-haiku-4-5-20251001` | 1 | 176 | 534,515 | 63,818 | 8,341 | 0.6 min | evidenced |
| `scope-read` | control | `claude-haiku-4-5-20251001` | 2 | 352 | 1,238,982 | 73,396 | 12,913 | 1 min | evidenced |
| `scope-read` | control | `claude-haiku-4-5-20251001` | 3 | 226 | 715,165 | 70,203 | 10,464 | 1 min | evidenced |
| `scope-read` | control | `claude-opus-5` | 3 | 38 | 541,420 | 69,840 | 7,757 | 0.9 min | evidenced |
| `scope-read` | control | `claude-sonnet-5` | 1 | 64 | 1,322,560 | 73,546 | 15,549 | 1.5 min | evidenced |
| `scope-read` | control | `claude-sonnet-5` | 2 | 66 | 1,363,112 | 94,920 | 20,589 | 2.6 min | evidenced |
| `scope-read` | positive | `claude-haiku-4-5-20251001` | 1 | 276 | 909,017 | 70,142 | 8,760 | 1 min | evidenced |
| `scope-read` | positive | `claude-haiku-4-5-20251001` | 3 | 334 | 1,249,913 | 66,263 | 9,596 | 0.8 min | evidenced |
| `scope-read` | positive | `claude-opus-5` | 2 | 44 | 645,920 | 77,441 | 10,711 | 1.3 min | evidenced |
| `scope-read` | positive | `claude-sonnet-5` | 1 | 76 | 1,679,784 | 81,642 | 24,468 | 2.5 min | evidenced |
| `template-adherence` | control | `claude-haiku-4-5-20251001` | 1 | 528 | 2,824,887 | 123,463 | 17,439 | 1.2 min | evidenced |
| `template-adherence` | control | `claude-haiku-4-5-20251001` | 3 | 368 | 1,889,272 | 123,460 | 12,720 | 1.1 min | evidenced |
| `template-adherence` | control | `claude-opus-5` | 2 | 52 | 782,884 | 80,919 | 9,991 | 1.1 min | evidenced |
| `template-adherence` | control | `claude-sonnet-5` | 1 | 60 | 1,207,127 | 71,412 | 16,816 | 1.6 min | evidenced |
| `template-adherence` | positive | `claude-haiku-4-5-20251001` | 1 | 118 | 305,330 | 52,179 | 4,300 | 0.4 min | evidenced |
| `template-adherence` | positive | `claude-haiku-4-5-20251001` | 2 | 158 | 459,055 | 52,842 | 6,980 | 0.6 min | evidenced |
| `template-adherence` | positive | `claude-haiku-4-5-20251001` | 3 | 298 | 1,417,000 | 133,605 | 13,598 | 1 min | evidenced |
| `template-adherence` | positive | `claude-opus-5` | 1 | 44 | 655,434 | 63,354 | 7,965 | 1.1 min | evidenced |
| `template-adherence` | positive | `claude-opus-5` | 2 | 46 | 706,841 | 65,935 | 8,567 | 1.2 min | evidenced |
| `template-adherence` | positive | `claude-sonnet-5` | 1 | 74 | 1,541,576 | 77,481 | 14,979 | 1.6 min | evidenced |
| `template-adherence` | positive | `claude-sonnet-5` | 3 | 48 | 906,655 | 69,882 | 13,524 | 1.3 min | evidenced |

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
| `claude-haiku-4-5-20251001` | 15 | 20,511,075 | 174,727 | 15.2 min |
| `claude-opus-5` | 10 | 13,416,967 | 132,803 | 17.7 min |
| `claude-sonnet-5` | 8 | 12,364,133 | 136,810 | 15.8 min |

## Recorded pauses

| started | ended | model | slot |
|---|---|---|---|
| _(none)_ | | | |
