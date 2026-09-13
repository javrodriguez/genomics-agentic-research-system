# The bill and the machine

Every table below is written by `costs.py --write` from the raw transcripts and the driver ledgers.
`test_harness.py TheBillIsWrittenByTheReader` fails when this file differs from what it writes.
Until 11 September 2026 this line said no number here was typed by hand, while the flag wrote nothing and the walk table had been typed.
The notes quote measurements and say where each came from.

**Dollars billed beyond the standing subscription: $0, as the operator states it. The committed files do not evidence it take by take.**

What the files show, and what they do not:

- the driver ran each Claude take with the operator's own shell environment plus the pre-registered isolation variables, and recorded no per-take environment, so no committed record shows that no API-key variable was set for a take (Ruling 34); until 13 September 2026 this list said each take's recorded environment showed it, and no such record exists;
- no committed transcript or ledger records which credential a take's session used;
- the local tier did not run, so no placeholder credential was used;
- there is no `.env` under `evals/gap-study/`;
- `grep -E "boto3|stripe|billing" evals/gap-study/*.py` returns nothing.

A billing page behind a login is listed `not checked — behind a login`.
The subscription fee itself is not attributed to this study.

## Per take

_(written by `costs.py` once takes exist; tokens by class and wall clock from first to last
timestamp in the raw JSONL)_

| task | half | model | take | input | cache read | cache write | output | wall clock |
|---|---|---|---|---|---|---|---|---|
| `confounded-design` | control | `claude-haiku-4-5-20251001` | 1 | 208 | 947,608 | 66,429 | 8,748 | 0.7 min |
| `confounded-design` | control | `claude-haiku-4-5-20251001` | 2 | 142 | 621,216 | 60,279 | 6,569 | 0.5 min |
| `confounded-design` | control | `claude-haiku-4-5-20251001` | 3 | 126 | 552,233 | 55,670 | 6,762 | 0.6 min |
| `confounded-design` | control | `claude-opus-5` | 1 | 84 | 2,306,874 | 99,261 | 15,253 | 3.0 min |
| `confounded-design` | control | `claude-opus-5` | 2 | 90 | 2,417,649 | 93,888 | 16,332 | 2.7 min |
| `confounded-design` | control | `claude-opus-5` | 3 | 456 | 717,890 | 149,633 | 6,341 | 1.1 min |
| `confounded-design` | control | `claude-sonnet-5` | 1 | 118 | 4,242,974 | 117,469 | 30,007 | 4.8 min |
| `confounded-design` | control | `claude-sonnet-5` | 2 | 96 | 3,141,973 | 97,287 | 18,272 | 3.0 min |
| `confounded-design` | control | `claude-sonnet-5` | 3 | 114 | 3,825,871 | 99,347 | 20,118 | 4.0 min |
| `confounded-design` | positive | `claude-haiku-4-5-20251001` | 1 | 160 | 819,245 | 123,484 | 6,666 | 0.5 min |
| `confounded-design` | positive | `claude-haiku-4-5-20251001` | 2 | 102 | 416,876 | 49,333 | 4,110 | 0.4 min |
| `confounded-design` | positive | `claude-haiku-4-5-20251001` | 3 | 186 | 825,168 | 59,083 | 6,995 | 0.7 min |
| `confounded-design` | positive | `claude-opus-5` | 1 | 100 | 2,744,670 | 86,170 | 17,574 | 2.9 min |
| `confounded-design` | positive | `claude-opus-5` | 2 | 74 | 1,958,398 | 75,312 | 11,065 | 2.3 min |
| `confounded-design` | positive | `claude-opus-5` | 3 | 88 | 2,364,435 | 107,954 | 17,673 | 2.6 min |
| `confounded-design` | positive | `claude-sonnet-5` | 1 | 80 | 2,405,291 | 75,108 | 19,684 | 3.9 min |
| `confounded-design` | positive | `claude-sonnet-5` | 2 | 128 | 4,487,713 | 110,265 | 26,855 | 4.6 min |
| `confounded-design` | positive | `claude-sonnet-5` | 3 | 92 | 2,968,882 | 93,897 | 15,326 | 3.4 min |
| `number-fidelity` | control | `claude-haiku-4-5-20251001` | 1 | 126 | 567,977 | 54,651 | 4,312 | 0.4 min |
| `number-fidelity` | control | `claude-haiku-4-5-20251001` | 2 | 102 | 428,732 | 52,669 | 3,546 | 0.3 min |
| `number-fidelity` | control | `claude-haiku-4-5-20251001` | 3 | 144 | 616,094 | 64,470 | 6,483 | 0.5 min |
| `number-fidelity` | control | `claude-opus-5` | 1 | 62 | 1,468,527 | 104,040 | 14,928 | 3.8 min |
| `number-fidelity` | control | `claude-opus-5` | 2 | 40 | 878,261 | 61,833 | 6,222 | 1.1 min |
| `number-fidelity` | control | `claude-opus-5` | 3 | 46 | 1,051,242 | 50,804 | 5,849 | 1.3 min |
| `number-fidelity` | control | `claude-sonnet-5` | 1 | 44 | 1,176,008 | 56,130 | 6,592 | 1.4 min |
| `number-fidelity` | control | `claude-sonnet-5` | 2 | 50 | 1,391,490 | 67,902 | 10,805 | 1.6 min |
| `number-fidelity` | control | `claude-sonnet-5` | 3 | 52 | 1,445,977 | 61,979 | 11,007 | 2.3 min |
| `number-fidelity` | positive | `claude-haiku-4-5-20251001` | 1 | 102 | 337,083 | 139,565 | 4,374 | 0.3 min |
| `number-fidelity` | positive | `claude-haiku-4-5-20251001` | 2 | 144 | 621,920 | 61,841 | 5,585 | 0.4 min |
| `number-fidelity` | positive | `claude-haiku-4-5-20251001` | 3 | 102 | 418,343 | 49,864 | 4,241 | 0.4 min |
| `number-fidelity` | positive | `claude-opus-5` | 1 | 42 | 948,789 | 62,702 | 7,222 | 1.1 min |
| `number-fidelity` | positive | `claude-opus-5` | 2 | 48 | 1,112,021 | 54,709 | 8,006 | 1.4 min |
| `number-fidelity` | positive | `claude-opus-5` | 3 | 42 | 943,110 | 57,533 | 6,105 | 1.4 min |
| `number-fidelity` | positive | `claude-sonnet-5` | 1 | 68 | 1,972,609 | 146,380 | 16,963 | 2.5 min |
| `number-fidelity` | positive | `claude-sonnet-5` | 2 | 64 | 1,874,858 | 75,394 | 14,541 | 2.1 min |
| `number-fidelity` | positive | `claude-sonnet-5` | 3 | 60 | 1,773,867 | 73,769 | 16,087 | 2.1 min |
| `plan-gate` | control | `claude-haiku-4-5-20251001` | 1 | 374 | 1,962,728 | 67,532 | 22,029 | 6.5 min |
| `plan-gate` | control | `claude-haiku-4-5-20251001` | 2 | 510 | 2,910,755 | 84,048 | 29,282 | 1.8 min |
| `plan-gate` | control | `claude-haiku-4-5-20251001` | 3 | 684 | 4,010,067 | 92,964 | 32,307 | 2.8 min |
| `plan-gate` | control | `claude-opus-5` | 1 | 56 | 1,340,151 | 98,699 | 20,184 | 2.1 min |
| `plan-gate` | control | `claude-opus-5` | 2 | 144 | 5,207,199 | 217,608 | 86,413 | 7.3 min |
| `plan-gate` | control | `claude-opus-5` | 3 | 48 | 1,027,729 | 67,106 | 12,426 | 1.5 min |
| `plan-gate` | control | `claude-sonnet-5` | 1 | 24 | 566,998 | 47,260 | 6,232 | 0.7 min |
| `plan-gate` | control | `claude-sonnet-5` | 2 | 36 | 909,846 | 52,402 | 5,673 | 0.7 min |
| `plan-gate` | control | `claude-sonnet-5` | 3 | 30 | 706,987 | 68,542 | 9,132 | 0.9 min |
| `plan-gate` | positive | `claude-haiku-4-5-20251001` | 1 | 430 | 2,406,966 | 98,825 | 38,011 | 3.0 min |
| `plan-gate` | positive | `claude-haiku-4-5-20251001` | 2 | 422 | 2,353,736 | 69,298 | 12,229 | 1.1 min |
| `plan-gate` | positive | `claude-haiku-4-5-20251001` | 3 | 358 | 1,991,506 | 72,910 | 14,617 | 1.3 min |
| `plan-gate` | positive | `claude-opus-5` | 1 | 64 | 1,463,752 | 147,004 | 28,758 | 3.3 min |
| `plan-gate` | positive | `claude-opus-5` | 2 | 64 | 1,484,390 | 210,976 | 24,145 | 1.9 min |
| `plan-gate` | positive | `claude-opus-5` | 3 | 98 | 2,946,270 | 178,471 | 54,945 | 4.0 min |
| `plan-gate` | positive | `claude-sonnet-5` | 1 | 32 | 756,038 | 69,258 | 8,314 | 0.8 min |
| `plan-gate` | positive | `claude-sonnet-5` | 2 | 28 | 644,388 | 55,880 | 5,712 | 0.7 min |
| `plan-gate` | positive | `claude-sonnet-5` | 3 | 36 | 860,506 | 54,859 | 8,527 | 0.9 min |
| `precondition-refusal` | control | `claude-haiku-4-5-20251001` | 1 | 208 | 889,962 | 57,026 | 6,259 | 0.7 min |
| `precondition-refusal` | control | `claude-haiku-4-5-20251001` | 2 | 174 | 744,730 | 37,745 | 5,796 | 0.6 min |
| `precondition-refusal` | control | `claude-haiku-4-5-20251001` | 3 | 174 | 735,445 | 50,740 | 5,572 | 0.6 min |
| `precondition-refusal` | control | `claude-opus-5` | 1 | 42 | 885,927 | 68,442 | 9,830 | 1.2 min |
| `precondition-refusal` | control | `claude-opus-5` | 2 | 296 | 499,117 | 56,142 | 3,839 | 0.6 min |
| `precondition-refusal` | control | `claude-opus-5` | 3 | 360 | 569,393 | 62,187 | 5,123 | 0.8 min |
| `precondition-refusal` | control | `claude-sonnet-5` | 1 | 40 | 991,599 | 60,324 | 10,349 | 2.7 min |
| `precondition-refusal` | control | `claude-sonnet-5` | 2 | 46 | 1,197,017 | 52,472 | 7,890 | 1.0 min |
| `precondition-refusal` | control | `claude-sonnet-5` | 3 | 36 | 872,110 | 71,656 | 11,167 | 2.2 min |
| `precondition-refusal` | positive | `claude-haiku-4-5-20251001` | 1 | 350 | 1,714,131 | 55,024 | 8,856 | 0.9 min |
| `precondition-refusal` | positive | `claude-haiku-4-5-20251001` | 2 | 310 | 1,582,652 | 74,705 | 9,598 | 0.9 min |
| `precondition-refusal` | positive | `claude-haiku-4-5-20251001` | 3 | 142 | 531,654 | 134,881 | 4,056 | 0.4 min |
| `precondition-refusal` | positive | `claude-opus-5` | 1 | 198 | 307,385 | 61,438 | 2,512 | 0.4 min |
| `precondition-refusal` | positive | `claude-opus-5` | 2 | 36 | 758,252 | 46,055 | 6,063 | 0.9 min |
| `precondition-refusal` | positive | `claude-opus-5` | 3 | 36 | 740,864 | 68,761 | 9,273 | 1.2 min |
| `precondition-refusal` | positive | `claude-sonnet-5` | 1 | 42 | 1,061,310 | 69,410 | 13,229 | 1.1 min |
| `precondition-refusal` | positive | `claude-sonnet-5` | 2 | 48 | 1,259,431 | 64,552 | 20,250 | 2.1 min |
| `precondition-refusal` | positive | `claude-sonnet-5` | 3 | 36 | 864,830 | 44,003 | 7,059 | 0.8 min |
| `scope-read` | control | `claude-haiku-4-5-20251001` | 1 | 94 | 371,145 | 48,382 | 5,542 | 0.4 min |
| `scope-read` | control | `claude-haiku-4-5-20251001` | 2 | 178 | 924,336 | 141,329 | 11,026 | 0.7 min |
| `scope-read` | control | `claude-haiku-4-5-20251001` | 3 | 150 | 665,449 | 59,594 | 6,621 | 0.6 min |
| `scope-read` | control | `claude-opus-5` | 1 | 48 | 1,117,490 | 84,699 | 14,049 | 1.7 min |
| `scope-read` | control | `claude-opus-5` | 2 | 46 | 1,034,551 | 66,774 | 9,247 | 1.6 min |
| `scope-read` | control | `claude-opus-5` | 3 | 42 | 985,140 | 58,931 | 7,013 | 1.2 min |
| `scope-read` | control | `claude-sonnet-5` | 1 | 64 | 1,880,094 | 88,540 | 17,533 | 2.4 min |
| `scope-read` | control | `claude-sonnet-5` | 2 | 56 | 1,569,666 | 66,413 | 13,430 | 1.8 min |
| `scope-read` | control | `claude-sonnet-5` | 3 | 64 | 1,890,535 | 77,863 | 15,693 | 2.1 min |
| `scope-read` | positive | `claude-haiku-4-5-20251001` | 1 | 114 | 469,767 | 42,697 | 3,046 | 0.3 min |
| `scope-read` | positive | `claude-haiku-4-5-20251001` | 2 | 94 | 369,770 | 48,077 | 5,475 | 0.4 min |
| `scope-read` | positive | `claude-haiku-4-5-20251001` | 3 | 174 | 802,697 | 64,432 | 9,301 | 0.7 min |
| `scope-read` | positive | `claude-opus-5` | 1 | 40 | 897,700 | 67,687 | 7,703 | 1.3 min |
| `scope-read` | positive | `claude-opus-5` | 2 | 526 | 914,545 | 183,450 | 7,824 | 1.3 min |
| `scope-read` | positive | `claude-opus-5` | 3 | 40 | 844,544 | 106,087 | 7,330 | 3.2 min |
| `scope-read` | positive | `claude-sonnet-5` | 1 | 74 | 2,101,032 | 140,066 | 14,444 | 2.2 min |
| `scope-read` | positive | `claude-sonnet-5` | 2 | 68 | 1,996,770 | 72,862 | 18,709 | 2.3 min |
| `scope-read` | positive | `claude-sonnet-5` | 3 | 46 | 1,255,111 | 59,206 | 7,969 | 1.5 min |
| `template-adherence` | control | `claude-haiku-4-5-20251001` | 1 | 102 | 416,909 | 49,498 | 3,955 | 0.3 min |
| `template-adherence` | control | `claude-haiku-4-5-20251001` | 2 | 176 | 950,943 | 106,196 | 8,746 | 0.7 min |
| `template-adherence` | control | `claude-haiku-4-5-20251001` | 3 | 162 | 713,104 | 65,329 | 7,964 | 0.6 min |
| `template-adherence` | control | `claude-opus-5` | 1 | 58 | 1,379,636 | 54,190 | 8,187 | 1.7 min |
| `template-adherence` | control | `claude-opus-5` | 2 | 58 | 1,416,381 | 75,046 | 13,307 | 1.8 min |
| `template-adherence` | control | `claude-opus-5` | 3 | 56 | 1,333,447 | 76,726 | 9,188 | 1.9 min |
| `template-adherence` | control | `claude-sonnet-5` | 1 | 58 | 1,636,151 | 136,980 | 11,545 | 1.6 min |
| `template-adherence` | control | `claude-sonnet-5` | 2 | 52 | 1,456,856 | 67,912 | 8,005 | 1.4 min |
| `template-adherence` | control | `claude-sonnet-5` | 3 | 82 | 2,502,111 | 75,673 | 20,546 | 2.6 min |
| `template-adherence` | positive | `claude-haiku-4-5-20251001` | 1 | 102 | 432,089 | 49,672 | 3,897 | 0.3 min |
| `template-adherence` | positive | `claude-haiku-4-5-20251001` | 2 | 190 | 931,902 | 63,311 | 8,465 | 0.7 min |
| `template-adherence` | positive | `claude-haiku-4-5-20251001` | 3 | 118 | 485,948 | 53,433 | 4,577 | 0.3 min |
| `template-adherence` | positive | `claude-opus-5` | 1 | 526 | 975,447 | 107,183 | 12,273 | 1.3 min |
| `template-adherence` | positive | `claude-opus-5` | 2 | 44 | 980,620 | 61,304 | 8,430 | 1.4 min |
| `template-adherence` | positive | `claude-opus-5` | 3 | 50 | 1,155,898 | 79,946 | 12,149 | 1.6 min |
| `template-adherence` | positive | `claude-sonnet-5` | 1 | 58 | 1,659,087 | 78,705 | 17,828 | 2.4 min |
| `template-adherence` | positive | `claude-sonnet-5` | 2 | 48 | 1,314,905 | 61,377 | 9,820 | 1.4 min |
| `template-adherence` | positive | `claude-sonnet-5` | 3 | 76 | 2,359,946 | 84,513 | 21,837 | 3.2 min |

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
| `claude-haiku-4-5-20251001` | 36 | 39,073,306 | 335,618 | 32.3 min |
| `claude-opus-5` | 36 | 52,490,593 | 512,781 | 69.9 min |
| `claude-sonnet-5` | 36 | 65,818,638 | 497,150 | 75.2 min |

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
