# Correction, 2026-10-02: the Gap Study token tables count records, not calls

_Written by `evals/gap-study-costs-by-call/costs_by_call.py --write`; never edited by hand. `--check` fails when this page differs from what the script writes, or when a published figure it prints is not in that round's `COSTS.md`. Decision 0271 records why it exists._

## What was wrong

The token tables in `evals/gap-study/COSTS.md`, `evals/gap-study-2/COSTS.md` and `evals/gap-study-3/COSTS.md` add up usage over transcript records, not over model calls.
Claude Code writes one record per content block of a model reply (thinking, text, tool use), and each of those records carries the whole reply's usage, so a reply with three blocks was counted three times.
Across the three rounds, 8,399 usage records hold 4,136 calls, and the tables published 386,064,019 tokens (cache reads included), 1.98 times the 195,353,721 the calls used.
Every duplicate record carries the same usage as the others of its call, so counting each call once is unambiguous.

The published tables stand as published and are not edited; this page gives the figures counted once per call beside them.
A call is counted once per pair of `message.id` and `requestId`.

## What does not change

- No graded result. No grader, label, count, interval or result file reads token usage; the transcript parser the graders use discards it.
- Wall clock, the recorded pauses, and each round's dollar line. None reads usage.
- The published `COSTS.md` tables and the pinned `costs.py` that wrote them.

## Each table, and what is wrong in it

| round | table | what is wrong | corrected below |
|---|---|---|---|
| `gap-study` | Per take | every token cell counts records, not calls | per take |
| `gap-study` | Pre-freeze walks | every token cell counts records, not calls | per walk |
| `gap-study` | Per model | context and output totals are sums of the per-take cells | per model |
| `gap-study` | Recorded pauses | nothing: no token figure | not needed |
| `gap-study-2` | Per take | every token cell counts records, not calls | per take |
| `gap-study-2` | Pre-freeze walks | every token cell counts records, not calls | per walk |
| `gap-study-2` | Per model | context and output totals are sums of the per-take cells | per model |
| `gap-study-2` | Recorded pauses | nothing: no token figure | not needed |
| `gap-study-3` | Per take | every token cell counts records, not calls | per take |
| `gap-study-3` | Pre-freeze walks | every token cell counts records, not calls | per walk |
| `gap-study-3` | Per model | context and output totals are sums of the per-take cells | per model |
| `gap-study-3` | Recorded pauses | nothing: no token figure | not needed |
| `gap-study` | prose notes (walks note; notes recorded before any take) | two quoted ranges of context tokens were read from record sums | prose figures |

## All three rounds

| class | published | counted once per call | published over counted |
|---|---|---|---|
| input | 37,208 | 16,528 | 2.25 |
| cache read | 359,127,510 | 183,766,050 | 1.95 |
| cache write | 23,254,326 | 9,895,281 | 2.35 |
| output | 3,644,975 | 1,675,862 | 2.17 |
| all four classes | 386,064,019 | 195,353,721 | 1.98 |

## `gap-study`

### gap-study: totals of the Per take table

108 transcripts; 2,965 usage records hold 1,435 calls.

| class | published | counted once per call | published over counted |
|---|---|---|---|
| input | 13,728 | 6,112 | 2.25 |
| cache read | 148,739,417 | 74,861,427 | 1.99 |
| cache write | 8,629,392 | 3,605,713 | 2.39 |
| output | 1,345,549 | 600,931 | 2.24 |

### gap-study: totals of the Pre-freeze walks table

11 transcripts; 341 usage records hold 132 calls.

| class | published | counted once per call | published over counted |
|---|---|---|---|
| input | 3,086 | 1,258 | 2.45 |
| cache read | 18,681,076 | 7,367,653 | 2.54 |
| cache write | 2,018,133 | 734,776 | 2.75 |
| output | 209,916 | 74,844 | 2.80 |

### gap-study: per model

| model | graded takes | context tokens, published | context tokens, counted once | output tokens, published | output tokens, counted once |
|---|---|---|---|---|---|
| `claude-haiku-4-5-20251001` | 36 | 39,073,306 | 16,275,898 | 335,618 | 132,331 |
| `claude-opus-5` | 36 | 52,490,593 | 26,370,741 | 512,781 | 221,447 |
| `claude-sonnet-5` | 36 | 65,818,638 | 35,826,613 | 497,150 | 247,153 |

### gap-study: per take

Published cells first, then the same cells counted once per call.

| task | half | model | take | records | calls | published: input | cache read | cache write | output | counted once: input | cache read | cache write | output |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `confounded-design` | control | `claude-haiku-4-5-20251001` | 1 | 25 | 10 | 208 | 947,608 | 66,429 | 8,748 | 82 | 380,778 | 22,798 | 3,309 |
| `confounded-design` | control | `claude-haiku-4-5-20251001` | 2 | 17 | 6 | 142 | 621,216 | 60,279 | 6,569 | 50 | 222,080 | 21,040 | 2,449 |
| `confounded-design` | control | `claude-haiku-4-5-20251001` | 3 | 15 | 6 | 126 | 552,233 | 55,670 | 6,762 | 50 | 221,881 | 20,787 | 2,810 |
| `confounded-design` | control | `claude-opus-5` | 1 | 42 | 25 | 84 | 2,306,874 | 99,261 | 15,253 | 50 | 1,414,602 | 46,573 | 8,400 |
| `confounded-design` | control | `claude-opus-5` | 2 | 45 | 25 | 90 | 2,417,649 | 93,888 | 16,332 | 50 | 1,388,893 | 43,521 | 8,994 |
| `confounded-design` | control | `claude-opus-5` | 3 | 18 | 9 | 456 | 717,890 | 149,633 | 6,341 | 228 | 393,926 | 56,425 | 3,037 |
| `confounded-design` | control | `claude-sonnet-5` | 1 | 59 | 34 | 118 | 4,242,974 | 117,469 | 30,007 | 68 | 2,503,927 | 61,238 | 16,206 |
| `confounded-design` | control | `claude-sonnet-5` | 2 | 48 | 27 | 96 | 3,141,973 | 97,287 | 18,272 | 54 | 1,824,936 | 50,161 | 9,668 |
| `confounded-design` | control | `claude-sonnet-5` | 3 | 57 | 32 | 114 | 3,825,871 | 99,347 | 20,118 | 64 | 2,178,644 | 51,996 | 10,689 |
| `confounded-design` | positive | `claude-haiku-4-5-20251001` | 1 | 19 | 6 | 160 | 819,245 | 123,484 | 6,666 | 50 | 273,202 | 34,066 | 2,140 |
| `confounded-design` | positive | `claude-haiku-4-5-20251001` | 2 | 12 | 5 | 102 | 416,876 | 49,333 | 4,110 | 42 | 176,443 | 17,991 | 1,661 |
| `confounded-design` | positive | `claude-haiku-4-5-20251001` | 3 | 22 | 9 | 186 | 825,168 | 59,083 | 6,995 | 76 | 340,997 | 22,341 | 2,953 |
| `confounded-design` | positive | `claude-opus-5` | 1 | 50 | 28 | 100 | 2,744,670 | 86,170 | 17,574 | 56 | 1,559,874 | 45,117 | 9,246 |
| `confounded-design` | positive | `claude-opus-5` | 2 | 37 | 25 | 74 | 1,958,398 | 75,312 | 11,065 | 50 | 1,345,859 | 42,990 | 7,224 |
| `confounded-design` | positive | `claude-opus-5` | 3 | 44 | 23 | 88 | 2,364,435 | 107,954 | 17,673 | 46 | 1,288,288 | 45,165 | 8,433 |
| `confounded-design` | positive | `claude-sonnet-5` | 1 | 40 | 21 | 80 | 2,405,291 | 75,108 | 19,684 | 42 | 1,273,803 | 37,379 | 9,120 |
| `confounded-design` | positive | `claude-sonnet-5` | 2 | 64 | 37 | 128 | 4,487,713 | 110,265 | 26,855 | 74 | 2,645,774 | 57,796 | 14,332 |
| `confounded-design` | positive | `claude-sonnet-5` | 3 | 46 | 27 | 92 | 2,968,882 | 93,897 | 15,326 | 54 | 1,789,801 | 49,556 | 8,850 |
| `number-fidelity` | control | `claude-haiku-4-5-20251001` | 1 | 15 | 6 | 126 | 567,977 | 54,651 | 4,312 | 50 | 228,143 | 20,411 | 1,711 |
| `number-fidelity` | control | `claude-haiku-4-5-20251001` | 2 | 12 | 5 | 102 | 428,732 | 52,669 | 3,546 | 42 | 181,654 | 19,128 | 1,366 |
| `number-fidelity` | control | `claude-haiku-4-5-20251001` | 3 | 17 | 6 | 144 | 616,094 | 64,470 | 6,483 | 50 | 222,528 | 21,027 | 2,271 |
| `number-fidelity` | control | `claude-opus-5` | 1 | 31 | 12 | 62 | 1,468,527 | 104,040 | 14,928 | 24 | 590,869 | 34,181 | 6,052 |
| `number-fidelity` | control | `claude-opus-5` | 2 | 20 | 12 | 40 | 878,261 | 61,833 | 6,222 | 24 | 544,191 | 30,024 | 3,369 |
| `number-fidelity` | control | `claude-opus-5` | 3 | 23 | 14 | 46 | 1,051,242 | 50,804 | 5,849 | 28 | 650,114 | 28,356 | 3,602 |
| `number-fidelity` | control | `claude-sonnet-5` | 1 | 22 | 13 | 44 | 1,176,008 | 56,130 | 6,592 | 26 | 712,898 | 29,688 | 3,517 |
| `number-fidelity` | control | `claude-sonnet-5` | 2 | 25 | 12 | 50 | 1,391,490 | 67,902 | 10,805 | 24 | 684,796 | 32,328 | 5,284 |
| `number-fidelity` | control | `claude-sonnet-5` | 3 | 26 | 14 | 52 | 1,445,977 | 61,979 | 11,007 | 28 | 787,037 | 32,607 | 5,670 |
| `number-fidelity` | positive | `claude-haiku-4-5-20251001` | 1 | 12 | 4 | 102 | 337,083 | 139,565 | 4,374 | 34 | 116,081 | 46,036 | 1,442 |
| `number-fidelity` | positive | `claude-haiku-4-5-20251001` | 2 | 17 | 6 | 144 | 621,920 | 61,841 | 5,585 | 50 | 227,967 | 18,832 | 1,803 |
| `number-fidelity` | positive | `claude-haiku-4-5-20251001` | 3 | 12 | 5 | 102 | 418,343 | 49,864 | 4,241 | 42 | 177,054 | 18,246 | 1,682 |
| `number-fidelity` | positive | `claude-opus-5` | 1 | 21 | 11 | 42 | 948,789 | 62,702 | 7,222 | 22 | 513,084 | 28,559 | 3,460 |
| `number-fidelity` | positive | `claude-opus-5` | 2 | 24 | 13 | 48 | 1,112,021 | 54,709 | 8,006 | 26 | 600,464 | 29,014 | 4,027 |
| `number-fidelity` | positive | `claude-opus-5` | 3 | 21 | 14 | 42 | 943,110 | 57,533 | 6,105 | 28 | 659,963 | 28,311 | 3,838 |
| `number-fidelity` | positive | `claude-sonnet-5` | 1 | 34 | 18 | 68 | 1,972,609 | 146,380 | 16,963 | 36 | 1,058,164 | 73,742 | 8,615 |
| `number-fidelity` | positive | `claude-sonnet-5` | 2 | 32 | 16 | 64 | 1,874,858 | 75,394 | 14,541 | 32 | 962,557 | 36,532 | 7,132 |
| `number-fidelity` | positive | `claude-sonnet-5` | 3 | 30 | 16 | 60 | 1,773,867 | 73,769 | 16,087 | 32 | 957,418 | 37,579 | 8,204 |
| `plan-gate` | control | `claude-haiku-4-5-20251001` | 1 | 46 | 21 | 374 | 1,962,728 | 67,532 | 22,029 | 170 | 895,770 | 29,326 | 9,197 |
| `plan-gate` | control | `claude-haiku-4-5-20251001` | 2 | 63 | 28 | 510 | 2,910,755 | 84,048 | 29,282 | 226 | 1,293,050 | 34,608 | 11,447 |
| `plan-gate` | control | `claude-haiku-4-5-20251001` | 3 | 84 | 37 | 684 | 4,010,067 | 92,964 | 32,307 | 300 | 1,768,661 | 37,225 | 13,387 |
| `plan-gate` | control | `claude-opus-5` | 1 | 28 | 11 | 56 | 1,340,151 | 98,699 | 20,184 | 22 | 533,427 | 38,204 | 7,906 |
| `plan-gate` | control | `claude-opus-5` | 2 | 72 | 29 | 144 | 5,207,199 | 217,608 | 86,413 | 58 | 2,207,168 | 84,390 | 32,625 |
| `plan-gate` | control | `claude-opus-5` | 3 | 24 | 10 | 48 | 1,027,729 | 67,106 | 12,426 | 20 | 421,182 | 27,652 | 5,047 |
| `plan-gate` | control | `claude-sonnet-5` | 1 | 12 | 6 | 24 | 566,998 | 47,260 | 6,232 | 12 | 283,499 | 23,630 | 3,116 |
| `plan-gate` | control | `claude-sonnet-5` | 2 | 18 | 10 | 36 | 909,846 | 52,402 | 5,673 | 20 | 511,678 | 26,806 | 2,960 |
| `plan-gate` | control | `claude-sonnet-5` | 3 | 15 | 6 | 30 | 706,987 | 68,542 | 9,132 | 12 | 294,222 | 30,002 | 3,492 |
| `plan-gate` | positive | `claude-haiku-4-5-20251001` | 1 | 53 | 22 | 430 | 2,406,966 | 98,825 | 38,011 | 178 | 1,022,881 | 40,727 | 15,870 |
| `plan-gate` | positive | `claude-haiku-4-5-20251001` | 2 | 52 | 25 | 422 | 2,353,736 | 69,298 | 12,229 | 202 | 1,136,944 | 30,023 | 5,740 |
| `plan-gate` | positive | `claude-haiku-4-5-20251001` | 3 | 44 | 19 | 358 | 1,991,506 | 72,910 | 14,617 | 154 | 861,824 | 29,512 | 5,728 |
| `plan-gate` | positive | `claude-opus-5` | 1 | 32 | 9 | 64 | 1,463,752 | 147,004 | 28,758 | 18 | 429,571 | 39,323 | 7,983 |
| `plan-gate` | positive | `claude-opus-5` | 2 | 32 | 11 | 64 | 1,484,390 | 210,976 | 24,145 | 22 | 523,546 | 70,597 | 8,081 |
| `plan-gate` | positive | `claude-opus-5` | 3 | 49 | 17 | 98 | 2,946,270 | 178,471 | 54,945 | 34 | 1,050,811 | 56,723 | 17,894 |
| `plan-gate` | positive | `claude-sonnet-5` | 1 | 16 | 6 | 32 | 756,038 | 69,258 | 8,314 | 12 | 285,143 | 27,879 | 3,192 |
| `plan-gate` | positive | `claude-sonnet-5` | 2 | 14 | 6 | 28 | 644,388 | 55,880 | 5,712 | 12 | 276,476 | 25,287 | 2,536 |
| `plan-gate` | positive | `claude-sonnet-5` | 3 | 18 | 9 | 36 | 860,506 | 54,859 | 8,527 | 18 | 441,615 | 27,162 | 4,153 |
| `precondition-refusal` | control | `claude-haiku-4-5-20251001` | 1 | 25 | 11 | 208 | 889,962 | 57,026 | 6,259 | 90 | 398,727 | 18,989 | 2,437 |
| `precondition-refusal` | control | `claude-haiku-4-5-20251001` | 2 | 21 | 9 | 174 | 744,730 | 37,745 | 5,796 | 74 | 321,560 | 13,896 | 2,290 |
| `precondition-refusal` | control | `claude-haiku-4-5-20251001` | 3 | 21 | 9 | 174 | 735,445 | 50,740 | 5,572 | 74 | 318,208 | 17,839 | 2,223 |
| `precondition-refusal` | control | `claude-opus-5` | 1 | 21 | 10 | 42 | 885,927 | 68,442 | 9,830 | 20 | 444,738 | 25,894 | 4,282 |
| `precondition-refusal` | control | `claude-opus-5` | 2 | 13 | 6 | 296 | 499,117 | 56,142 | 3,839 | 132 | 230,750 | 22,747 | 1,787 |
| `precondition-refusal` | control | `claude-opus-5` | 3 | 15 | 6 | 360 | 569,393 | 62,187 | 5,123 | 132 | 231,027 | 22,945 | 2,096 |
| `precondition-refusal` | control | `claude-sonnet-5` | 1 | 20 | 10 | 40 | 991,599 | 60,324 | 10,349 | 20 | 510,589 | 26,574 | 4,943 |
| `precondition-refusal` | control | `claude-sonnet-5` | 2 | 23 | 13 | 46 | 1,197,017 | 52,472 | 7,890 | 26 | 682,958 | 26,964 | 3,951 |
| `precondition-refusal` | control | `claude-sonnet-5` | 3 | 18 | 7 | 36 | 872,110 | 71,656 | 11,167 | 14 | 349,960 | 25,901 | 4,852 |
| `precondition-refusal` | positive | `claude-haiku-4-5-20251001` | 1 | 43 | 20 | 350 | 1,714,131 | 55,024 | 8,856 | 162 | 800,913 | 22,937 | 3,955 |
| `precondition-refusal` | positive | `claude-haiku-4-5-20251001` | 2 | 38 | 17 | 310 | 1,582,652 | 74,705 | 9,598 | 138 | 710,050 | 28,863 | 4,196 |
| `precondition-refusal` | positive | `claude-haiku-4-5-20251001` | 3 | 17 | 7 | 142 | 531,654 | 134,881 | 4,056 | 58 | 228,615 | 46,193 | 1,618 |
| `precondition-refusal` | positive | `claude-opus-5` | 1 | 9 | 4 | 198 | 307,385 | 61,438 | 2,512 | 98 | 145,739 | 21,733 | 997 |
| `precondition-refusal` | positive | `claude-opus-5` | 2 | 18 | 9 | 36 | 758,252 | 46,055 | 6,063 | 18 | 373,985 | 24,188 | 2,878 |
| `precondition-refusal` | positive | `claude-opus-5` | 3 | 18 | 7 | 36 | 740,864 | 68,761 | 9,273 | 14 | 295,833 | 23,975 | 3,852 |
| `precondition-refusal` | positive | `claude-sonnet-5` | 1 | 21 | 9 | 42 | 1,061,310 | 69,410 | 13,229 | 18 | 468,380 | 28,925 | 4,756 |
| `precondition-refusal` | positive | `claude-sonnet-5` | 2 | 24 | 12 | 48 | 1,259,431 | 64,552 | 20,250 | 24 | 622,995 | 32,618 | 7,730 |
| `precondition-refusal` | positive | `claude-sonnet-5` | 3 | 18 | 10 | 36 | 864,830 | 44,003 | 7,059 | 20 | 478,833 | 22,197 | 3,559 |
| `scope-read` | control | `claude-haiku-4-5-20251001` | 1 | 11 | 4 | 94 | 371,145 | 48,382 | 5,542 | 34 | 137,892 | 16,338 | 2,111 |
| `scope-read` | control | `claude-haiku-4-5-20251001` | 2 | 21 | 6 | 178 | 924,336 | 141,329 | 11,026 | 50 | 283,331 | 37,525 | 3,220 |
| `scope-read` | control | `claude-haiku-4-5-20251001` | 3 | 18 | 7 | 150 | 665,449 | 59,594 | 6,621 | 58 | 259,577 | 21,736 | 2,545 |
| `scope-read` | control | `claude-opus-5` | 1 | 24 | 10 | 48 | 1,117,490 | 84,699 | 14,049 | 20 | 479,854 | 30,757 | 5,946 |
| `scope-read` | control | `claude-opus-5` | 2 | 23 | 12 | 46 | 1,034,551 | 66,774 | 9,247 | 24 | 566,363 | 29,463 | 4,590 |
| `scope-read` | control | `claude-opus-5` | 3 | 21 | 13 | 42 | 985,140 | 58,931 | 7,013 | 26 | 632,897 | 28,598 | 4,124 |
| `scope-read` | control | `claude-sonnet-5` | 1 | 32 | 16 | 64 | 1,880,094 | 88,540 | 17,533 | 32 | 966,375 | 36,801 | 8,802 |
| `scope-read` | control | `claude-sonnet-5` | 2 | 28 | 15 | 56 | 1,569,666 | 66,413 | 13,430 | 30 | 853,228 | 33,685 | 6,892 |
| `scope-read` | control | `claude-sonnet-5` | 3 | 32 | 16 | 64 | 1,890,535 | 77,863 | 15,693 | 32 | 949,275 | 37,514 | 7,787 |
| `scope-read` | positive | `claude-haiku-4-5-20251001` | 1 | 13 | 6 | 114 | 469,767 | 42,697 | 3,046 | 52 | 221,471 | 18,185 | 1,314 |
| `scope-read` | positive | `claude-haiku-4-5-20251001` | 2 | 11 | 4 | 94 | 369,770 | 48,077 | 5,475 | 34 | 137,338 | 16,329 | 2,078 |
| `scope-read` | positive | `claude-haiku-4-5-20251001` | 3 | 21 | 8 | 174 | 802,697 | 64,432 | 9,301 | 66 | 307,321 | 22,572 | 3,335 |
| `scope-read` | positive | `claude-opus-5` | 1 | 20 | 11 | 40 | 897,700 | 67,687 | 7,703 | 22 | 513,387 | 28,812 | 3,974 |
| `scope-read` | positive | `claude-opus-5` | 2 | 23 | 11 | 526 | 914,545 | 183,450 | 7,824 | 262 | 491,427 | 56,160 | 3,854 |
| `scope-read` | positive | `claude-opus-5` | 3 | 20 | 12 | 40 | 844,544 | 106,087 | 7,330 | 24 | 521,068 | 56,008 | 4,031 |
| `scope-read` | positive | `claude-sonnet-5` | 1 | 37 | 20 | 74 | 2,101,032 | 140,066 | 14,444 | 40 | 1,150,571 | 70,876 | 7,722 |
| `scope-read` | positive | `claude-sonnet-5` | 2 | 34 | 18 | 68 | 1,996,770 | 72,862 | 18,709 | 36 | 1,065,556 | 37,643 | 9,569 |
| `scope-read` | positive | `claude-sonnet-5` | 3 | 23 | 13 | 46 | 1,255,111 | 59,206 | 7,969 | 26 | 721,481 | 31,003 | 4,174 |
| `template-adherence` | control | `claude-haiku-4-5-20251001` | 1 | 12 | 5 | 102 | 416,909 | 49,498 | 3,955 | 42 | 176,457 | 18,071 | 1,549 |
| `template-adherence` | control | `claude-haiku-4-5-20251001` | 2 | 21 | 7 | 176 | 950,943 | 106,196 | 8,746 | 58 | 329,539 | 34,532 | 2,817 |
| `template-adherence` | control | `claude-haiku-4-5-20251001` | 3 | 19 | 7 | 162 | 713,104 | 65,329 | 7,964 | 60 | 268,643 | 23,020 | 3,205 |
| `template-adherence` | control | `claude-opus-5` | 1 | 29 | 20 | 58 | 1,379,636 | 54,190 | 8,187 | 40 | 989,216 | 31,627 | 5,429 |
| `template-adherence` | control | `claude-opus-5` | 2 | 29 | 14 | 58 | 1,416,381 | 75,046 | 13,307 | 28 | 704,142 | 32,389 | 5,846 |
| `template-adherence` | control | `claude-opus-5` | 3 | 28 | 16 | 56 | 1,333,447 | 76,726 | 9,188 | 32 | 802,365 | 31,810 | 4,643 |
| `template-adherence` | control | `claude-sonnet-5` | 1 | 29 | 17 | 58 | 1,636,151 | 136,980 | 11,545 | 34 | 987,551 | 70,083 | 6,112 |
| `template-adherence` | control | `claude-sonnet-5` | 2 | 26 | 15 | 52 | 1,456,856 | 67,912 | 8,005 | 30 | 888,303 | 33,064 | 4,151 |
| `template-adherence` | control | `claude-sonnet-5` | 3 | 41 | 23 | 82 | 2,502,111 | 75,673 | 20,546 | 46 | 1,432,468 | 39,409 | 10,520 |
| `template-adherence` | positive | `claude-haiku-4-5-20251001` | 1 | 12 | 5 | 102 | 432,089 | 49,672 | 3,897 | 42 | 182,791 | 18,153 | 1,522 |
| `template-adherence` | positive | `claude-haiku-4-5-20251001` | 2 | 23 | 9 | 190 | 931,902 | 63,311 | 8,465 | 74 | 365,433 | 23,011 | 3,200 |
| `template-adherence` | positive | `claude-haiku-4-5-20251001` | 3 | 14 | 5 | 118 | 485,948 | 53,433 | 4,577 | 42 | 176,756 | 17,969 | 1,750 |
| `template-adherence` | positive | `claude-opus-5` | 1 | 23 | 8 | 526 | 975,447 | 107,183 | 12,273 | 166 | 362,054 | 29,677 | 3,988 |
| `template-adherence` | positive | `claude-opus-5` | 2 | 22 | 12 | 44 | 980,620 | 61,304 | 8,430 | 24 | 557,936 | 28,231 | 4,331 |
| `template-adherence` | positive | `claude-opus-5` | 3 | 25 | 12 | 50 | 1,155,898 | 79,946 | 12,149 | 24 | 579,775 | 30,302 | 5,581 |
| `template-adherence` | positive | `claude-sonnet-5` | 1 | 29 | 15 | 58 | 1,659,087 | 78,705 | 17,828 | 30 | 872,573 | 35,686 | 8,746 |
| `template-adherence` | positive | `claude-sonnet-5` | 2 | 24 | 13 | 48 | 1,314,905 | 61,377 | 9,820 | 26 | 720,394 | 31,494 | 5,091 |
| `template-adherence` | positive | `claude-sonnet-5` | 3 | 38 | 20 | 76 | 2,359,946 | 84,513 | 21,837 | 40 | 1,256,601 | 43,185 | 11,060 |

### gap-study: per walk

| walk | records | calls | published: input | cache read | cache write | output | counted once: input | cache read | cache write | output |
|---|---|---|---|---|---|---|---|---|---|---|
| `confounded-design` 1 | 41 | 17 | 1,044 | 2,079,813 | 217,311 | 18,535 | 396 | 896,109 | 71,075 | 6,569 |
| `confounded-design` 2 | 42 | 21 | 1,016 | 2,236,924 | 189,522 | 15,448 | 464 | 1,154,358 | 72,070 | 7,395 |
| `number-fidelity` 1 | 31 | 12 | 62 | 1,780,649 | 200,709 | 19,350 | 24 | 674,892 | 91,825 | 7,527 |
| `number-fidelity` 2 | 21 | 9 | 552 | 867,536 | 154,112 | 9,893 | 228 | 388,832 | 56,754 | 3,840 |
| `plan-gate` 1 | 39 | 12 | 78 | 2,388,585 | 202,326 | 31,394 | 24 | 761,752 | 56,834 | 9,990 |
| `plan-gate` 2 | 53 | 17 | 106 | 3,277,805 | 215,951 | 59,732 | 34 | 1,100,732 | 70,463 | 18,136 |
| `precondition-refusal` 1 | 18 | 7 | 36 | 930,085 | 128,454 | 6,691 | 14 | 378,187 | 43,349 | 2,340 |
| `precondition-refusal` 2 | 15 | 6 | 30 | 696,271 | 129,190 | 5,833 | 12 | 301,996 | 36,392 | 2,175 |
| `scope-read` 1 | 31 | 12 | 62 | 1,703,891 | 190,796 | 14,075 | 24 | 661,268 | 86,492 | 5,412 |
| `template-adherence` 1 | 18 | 7 | 36 | 915,246 | 164,547 | 13,175 | 14 | 365,451 | 59,664 | 5,416 |
| `template-adherence` 2 | 32 | 12 | 64 | 1,804,271 | 225,215 | 15,790 | 24 | 684,076 | 89,858 | 6,044 |

## `gap-study-2`

### gap-study-2: totals of the Per take table

106 transcripts; 2,832 usage records hold 1,467 calls.

| class | published | counted once per call | published over counted |
|---|---|---|---|
| input | 10,840 | 5,022 | 2.16 |
| cache read | 106,311,177 | 57,641,062 | 1.84 |
| cache write | 7,078,058 | 3,245,681 | 2.18 |
| output | 1,195,831 | 579,016 | 2.07 |

### gap-study-2: totals of the Pre-freeze walks table

6 transcripts; 176 usage records hold 92 calls.

| class | published | counted once per call | published over counted |
|---|---|---|---|
| input | 352 | 184 | 1.91 |
| cache read | 7,277,723 | 3,941,551 | 1.85 |
| cache write | 456,430 | 212,242 | 2.15 |
| output | 73,019 | 36,667 | 1.99 |

### gap-study-2: per model

| model | graded takes | context tokens, published | context tokens, counted once | output tokens, published | output tokens, counted once |
|---|---|---|---|---|---|
| `claude-haiku-4-5-20251001` | 36 | 23,665,927 | 9,611,849 | 260,712 | 99,521 |
| `claude-opus-5` | 36 | 25,801,507 | 16,018,659 | 314,786 | 166,278 |
| `claude-sonnet-5` | 34 | 63,932,641 | 35,261,257 | 620,333 | 313,217 |

### gap-study-2: per take

Published cells first, then the same cells counted once per call.

| task | half | model | take | records | calls | published: input | cache read | cache write | output | counted once: input | cache read | cache write | output |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `confounded-design` | control | `claude-haiku-4-5-20251001` | 1 | 16 | 6 | 134 | 391,738 | 52,652 | 5,330 | 50 | 148,031 | 18,547 | 2,055 |
| `confounded-design` | control | `claude-haiku-4-5-20251001` | 2 | 15 | 5 | 128 | 343,696 | 63,030 | 6,327 | 42 | 120,348 | 20,117 | 2,114 |
| `confounded-design` | control | `claude-haiku-4-5-20251001` | 3 | 26 | 11 | 214 | 653,017 | 59,692 | 7,203 | 90 | 272,459 | 22,785 | 2,893 |
| `confounded-design` | control | `claude-opus-5` | 1 | 31 | 22 | 64 | 1,116,716 | 68,029 | 10,587 | 46 | 798,841 | 43,140 | 7,011 |
| `confounded-design` | control | `claude-opus-5` | 2 | 31 | 22 | 64 | 1,115,016 | 68,740 | 11,018 | 46 | 802,892 | 43,360 | 7,078 |
| `confounded-design` | control | `claude-opus-5` | 3 | 38 | 23 | 78 | 1,383,547 | 72,947 | 12,096 | 48 | 852,480 | 42,588 | 6,758 |
| `confounded-design` | control | `claude-sonnet-5` | 1 | 67 | 37 | 134 | 3,780,949 | 115,931 | 28,484 | 74 | 2,145,772 | 60,699 | 15,261 |
| `confounded-design` | control | `claude-sonnet-5` | 2 | 49 | 28 | 98 | 2,453,898 | 109,432 | 24,896 | 56 | 1,454,105 | 52,941 | 13,125 |
| `confounded-design` | control | `claude-sonnet-5` | 3 | 36 | 21 | 72 | 1,627,672 | 82,941 | 11,290 | 42 | 982,232 | 43,837 | 6,117 |
| `confounded-design` | positive | `claude-haiku-4-5-20251001` | 1 | 14 | 5 | 118 | 305,859 | 51,002 | 3,751 | 42 | 112,386 | 17,171 | 1,300 |
| `confounded-design` | positive | `claude-haiku-4-5-20251001` | 2 | 19 | 7 | 160 | 605,469 | 102,090 | 6,651 | 58 | 236,868 | 33,308 | 2,412 |
| `confounded-design` | positive | `claude-haiku-4-5-20251001` | 3 | 13 | 5 | 110 | 297,210 | 48,534 | 4,564 | 42 | 115,657 | 17,762 | 1,717 |
| `confounded-design` | positive | `claude-opus-5` | 1 | 34 | 23 | 70 | 1,210,015 | 78,969 | 10,183 | 48 | 845,077 | 43,297 | 6,712 |
| `confounded-design` | positive | `claude-opus-5` | 2 | 34 | 23 | 70 | 1,255,297 | 68,153 | 10,597 | 48 | 860,091 | 42,808 | 6,592 |
| `confounded-design` | positive | `claude-opus-5` | 3 | 34 | 23 | 70 | 1,239,743 | 69,948 | 10,986 | 48 | 855,679 | 42,230 | 6,703 |
| `confounded-design` | positive | `claude-sonnet-5` | 1 | 54 | 31 | 108 | 2,772,819 | 107,712 | 24,475 | 62 | 1,681,330 | 56,263 | 13,249 |
| `confounded-design` | positive | `claude-sonnet-5` | 2 | 52 | 32 | 104 | 2,622,746 | 97,881 | 23,792 | 64 | 1,677,739 | 52,853 | 13,112 |
| `confounded-design` | positive | `claude-sonnet-5` | 3 | 47 | 28 | 94 | 2,357,211 | 100,147 | 22,624 | 56 | 1,468,015 | 52,252 | 12,117 |
| `number-fidelity` | control | `claude-haiku-4-5-20251001` | 1 | 13 | 5 | 110 | 297,217 | 48,204 | 4,208 | 42 | 115,665 | 17,579 | 1,645 |
| `number-fidelity` | control | `claude-haiku-4-5-20251001` | 2 | 20 | 8 | 166 | 466,320 | 50,818 | 6,850 | 66 | 188,133 | 17,742 | 2,660 |
| `number-fidelity` | control | `claude-haiku-4-5-20251001` | 3 | 27 | 9 | 224 | 912,317 | 129,332 | 10,537 | 74 | 322,611 | 35,422 | 3,401 |
| `number-fidelity` | control | `claude-opus-5` | 1 | 16 | 10 | 32 | 437,281 | 48,901 | 4,494 | 20 | 286,108 | 26,023 | 2,820 |
| `number-fidelity` | control | `claude-opus-5` | 2 | 19 | 11 | 38 | 530,693 | 49,691 | 5,061 | 22 | 316,376 | 26,081 | 2,989 |
| `number-fidelity` | control | `claude-opus-5` | 3 | 19 | 12 | 38 | 551,387 | 50,331 | 5,129 | 24 | 360,820 | 27,065 | 3,251 |
| `number-fidelity` | control | `claude-sonnet-5` | 1 | 26 | 15 | 52 | 1,036,569 | 59,698 | 12,669 | 30 | 608,974 | 32,749 | 6,580 |
| `number-fidelity` | control | `claude-sonnet-5` | 2 | 21 | 12 | 42 | 764,158 | 63,136 | 7,429 | 24 | 451,663 | 29,150 | 3,648 |
| `number-fidelity` | control | `claude-sonnet-5` | 3 | 29 | 16 | 58 | 1,158,323 | 60,596 | 9,838 | 32 | 651,672 | 31,475 | 5,068 |
| `number-fidelity` | positive | `claude-haiku-4-5-20251001` | 1 | 15 | 7 | 130 | 345,429 | 40,873 | 3,672 | 60 | 165,395 | 17,712 | 1,651 |
| `number-fidelity` | positive | `claude-haiku-4-5-20251001` | 2 | 13 | 5 | 110 | 275,668 | 47,023 | 5,485 | 42 | 108,605 | 16,250 | 1,964 |
| `number-fidelity` | positive | `claude-haiku-4-5-20251001` | 3 | 14 | 4 | 122 | 286,260 | 65,000 | 6,373 | 34 | 89,256 | 17,150 | 1,745 |
| `number-fidelity` | positive | `claude-opus-5` | 1 | 16 | 9 | 32 | 412,731 | 58,717 | 5,412 | 18 | 252,506 | 26,952 | 2,900 |
| `number-fidelity` | positive | `claude-opus-5` | 2 | 19 | 12 | 38 | 544,574 | 50,279 | 4,535 | 24 | 358,162 | 26,996 | 2,911 |
| `number-fidelity` | positive | `claude-opus-5` | 3 | 17 | 10 | 34 | 427,178 | 63,164 | 4,955 | 20 | 287,062 | 27,931 | 2,782 |
| `number-fidelity` | positive | `claude-sonnet-5` | 1 | 44 | 23 | 88 | 1,994,177 | 75,731 | 17,027 | 46 | 1,066,567 | 38,450 | 8,820 |
| `number-fidelity` | positive | `claude-sonnet-5` | 2 | 21 | 13 | 42 | 788,328 | 54,673 | 5,811 | 26 | 510,907 | 29,949 | 3,425 |
| `number-fidelity` | positive | `claude-sonnet-5` | 3 | 32 | 18 | 64 | 1,366,676 | 71,014 | 18,153 | 36 | 786,501 | 37,098 | 9,331 |
| `plan-gate` | control | `claude-haiku-4-5-20251001` | 1 | 60 | 21 | 488 | 2,040,912 | 99,178 | 22,188 | 170 | 734,377 | 32,601 | 7,776 |
| `plan-gate` | control | `claude-haiku-4-5-20251001` | 2 | 47 | 22 | 382 | 1,312,275 | 51,878 | 12,495 | 178 | 614,756 | 21,991 | 5,611 |
| `plan-gate` | control | `claude-haiku-4-5-20251001` | 3 | 53 | 24 | 430 | 1,590,449 | 66,965 | 16,120 | 194 | 718,229 | 27,331 | 6,777 |
| `plan-gate` | control | `claude-opus-5` | 1 | 30 | 16 | 60 | 1,188,845 | 109,886 | 26,143 | 32 | 650,642 | 54,259 | 11,710 |
| `plan-gate` | control | `claude-opus-5` | 2 | 39 | 20 | 78 | 1,593,971 | 107,179 | 33,864 | 40 | 821,984 | 52,325 | 14,179 |
| `plan-gate` | control | `claude-opus-5` | 3 | 32 | 16 | 64 | 1,363,193 | 137,754 | 41,774 | 32 | 677,737 | 62,851 | 15,368 |
| `plan-gate` | control | `claude-sonnet-5` | 1 | 65 | 33 | 130 | 3,750,818 | 149,644 | 35,484 | 66 | 2,017,262 | 65,870 | 17,249 |
| `plan-gate` | control | `claude-sonnet-5` | 2 | 100 | 50 | 200 | 7,033,625 | 204,923 | 74,590 | 100 | 3,708,552 | 93,985 | 36,216 |
| `plan-gate` | control | `claude-sonnet-5` | 3 | 80 | 40 | 160 | 4,954,397 | 170,462 | 54,870 | 80 | 2,601,873 | 75,895 | 27,423 |
| `plan-gate` | positive | `claude-haiku-4-5-20251001` | 1 | 45 | 18 | 366 | 1,229,981 | 60,342 | 15,947 | 146 | 493,285 | 22,478 | 6,040 |
| `plan-gate` | positive | `claude-haiku-4-5-20251001` | 2 | 50 | 22 | 406 | 1,402,523 | 58,055 | 12,471 | 178 | 622,999 | 22,652 | 5,420 |
| `plan-gate` | positive | `claude-haiku-4-5-20251001` | 3 | 53 | 24 | 430 | 1,602,087 | 65,608 | 15,724 | 194 | 721,263 | 27,475 | 6,628 |
| `plan-gate` | positive | `claude-opus-5` | 1 | 17 | 10 | 34 | 476,678 | 43,176 | 9,457 | 20 | 275,470 | 27,055 | 4,930 |
| `plan-gate` | positive | `claude-opus-5` | 2 | 20 | 12 | 40 | 612,965 | 51,901 | 13,065 | 24 | 359,416 | 34,312 | 5,750 |
| `plan-gate` | positive | `claude-opus-5` | 3 | 17 | 10 | 34 | 493,150 | 46,073 | 8,273 | 20 | 285,126 | 28,502 | 5,308 |
| `plan-gate` | positive | `claude-sonnet-5` | 1 | 61 | 29 | 122 | 3,341,063 | 143,386 | 35,843 | 58 | 1,689,188 | 66,111 | 16,687 |
| `plan-gate` | positive | `claude-sonnet-5` | 2 | 45 | 21 | 90 | 1,975,441 | 98,227 | 27,604 | 42 | 967,330 | 44,401 | 12,731 |
| `plan-gate` | positive | `claude-sonnet-5` | 3 | 52 | 27 | 104 | 2,546,267 | 107,218 | 26,274 | 54 | 1,338,870 | 56,512 | 13,348 |
| `precondition-refusal` | control | `claude-haiku-4-5-20251001` | 1 | 26 | 10 | 216 | 729,471 | 109,606 | 8,520 | 82 | 297,691 | 32,327 | 3,083 |
| `precondition-refusal` | control | `claude-haiku-4-5-20251001` | 2 | 12 | 5 | 102 | 233,307 | 20,846 | 3,278 | 42 | 98,679 | 7,509 | 1,307 |
| `precondition-refusal` | control | `claude-haiku-4-5-20251001` | 3 | 20 | 9 | 166 | 444,920 | 45,882 | 4,016 | 74 | 202,760 | 17,020 | 1,672 |
| `precondition-refusal` | control | `claude-opus-5` | 1 | 11 | 7 | 22 | 274,812 | 31,039 | 4,295 | 14 | 171,632 | 22,259 | 2,515 |
| `precondition-refusal` | control | `claude-opus-5` | 2 | 8 | 5 | 16 | 169,963 | 36,438 | 3,344 | 10 | 108,704 | 19,628 | 1,843 |
| `precondition-refusal` | control | `claude-opus-5` | 3 | 14 | 6 | 28 | 312,825 | 59,691 | 5,961 | 12 | 145,970 | 20,504 | 2,638 |
| `precondition-refusal` | control | `claude-sonnet-5` | 1 | 20 | 9 | 40 | 691,981 | 67,218 | 9,712 | 18 | 332,835 | 27,737 | 4,074 |
| `precondition-refusal` | control | `claude-sonnet-5` | 2 | 14 | 6 | 28 | 434,442 | 49,527 | 5,402 | 12 | 189,654 | 22,900 | 2,406 |
| `precondition-refusal` | control | `claude-sonnet-5` | 3 | 23 | 11 | 46 | 793,031 | 70,600 | 8,340 | 22 | 406,724 | 27,868 | 3,926 |
| `precondition-refusal` | positive | `claude-haiku-4-5-20251001` | 1 | 15 | 6 | 126 | 301,955 | 22,075 | 3,278 | 50 | 122,031 | 7,915 | 1,283 |
| `precondition-refusal` | positive | `claude-haiku-4-5-20251001` | 2 | 16 | 7 | 134 | 323,945 | 28,231 | 4,280 | 58 | 143,611 | 11,218 | 1,762 |
| `precondition-refusal` | positive | `claude-haiku-4-5-20251001` | 3 | 11 | 5 | 94 | 211,807 | 20,242 | 2,449 | 42 | 98,584 | 7,402 | 1,045 |
| `precondition-refusal` | positive | `claude-opus-5` | 1 | 7 | 5 | 14 | 149,569 | 26,386 | 1,710 | 10 | 108,525 | 19,321 | 1,084 |
| `precondition-refusal` | positive | `claude-opus-5` | 2 | 7 | 4 | 14 | 129,678 | 46,229 | 1,452 | 8 | 78,742 | 19,412 | 773 |
| `precondition-refusal` | positive | `claude-opus-5` | 3 | 6 | 4 | 12 | 109,349 | 35,498 | 1,004 | 8 | 78,391 | 19,023 | 620 |
| `precondition-refusal` | positive | `claude-sonnet-5` | 1 | 17 | 8 | 34 | 532,463 | 62,257 | 6,421 | 16 | 261,513 | 22,811 | 2,907 |
| `precondition-refusal` | positive | `claude-sonnet-5` | 2 | 12 | 7 | 24 | 360,952 | 36,495 | 3,792 | 14 | 214,698 | 19,692 | 1,976 |
| `precondition-refusal` | positive | `claude-sonnet-5` | 3 | 19 | 9 | 38 | 613,181 | 57,989 | 8,894 | 18 | 296,648 | 24,854 | 4,220 |
| `scope-read` | control | `claude-haiku-4-5-20251001` | 1 | 36 | 16 | 294 | 938,447 | 60,185 | 9,665 | 130 | 410,231 | 24,170 | 3,948 |
| `scope-read` | control | `claude-haiku-4-5-20251001` | 2 | 13 | 5 | 110 | 285,393 | 49,152 | 4,567 | 42 | 112,248 | 17,256 | 1,779 |
| `scope-read` | control | `claude-haiku-4-5-20251001` | 3 | 26 | 12 | 212 | 645,801 | 48,981 | 6,261 | 98 | 292,751 | 20,695 | 2,808 |
| `scope-read` | control | `claude-opus-5` | 1 | 16 | 10 | 32 | 445,108 | 46,000 | 5,592 | 20 | 282,031 | 25,618 | 3,265 |
| `scope-read` | control | `claude-opus-5` | 2 | 18 | 11 | 36 | 511,767 | 50,929 | 5,896 | 22 | 322,950 | 26,835 | 3,549 |
| `scope-read` | control | `claude-opus-5` | 3 | 18 | 11 | 36 | 508,905 | 49,702 | 4,613 | 22 | 322,360 | 26,429 | 2,882 |
| `scope-read` | control | `claude-sonnet-5` | 1 | 20 | 12 | 40 | 719,164 | 51,566 | 4,802 | 24 | 449,585 | 27,452 | 2,983 |
| `scope-read` | control | `claude-sonnet-5` | 2 | 23 | 12 | 46 | 839,411 | 69,787 | 6,881 | 24 | 468,934 | 28,696 | 3,375 |
| `scope-read` | control | `claude-sonnet-5` | 3 | 35 | 19 | 70 | 1,538,145 | 79,886 | 20,216 | 38 | 857,064 | 41,108 | 10,255 |
| `scope-read` | positive | `claude-haiku-4-5-20251001` | 1 | 18 | 6 | 152 | 420,142 | 68,363 | 7,117 | 50 | 146,526 | 22,154 | 2,143 |
| `scope-read` | positive | `claude-haiku-4-5-20251001` | 2 | 12 | 5 | 102 | 264,034 | 46,917 | 3,567 | 42 | 112,537 | 17,224 | 1,392 |
| `scope-read` | positive | `claude-haiku-4-5-20251001` | 3 | 12 | 5 | 102 | 263,346 | 47,042 | 4,730 | 42 | 112,260 | 17,280 | 1,896 |
| `scope-read` | positive | `claude-opus-5` | 1 | 20 | 11 | 40 | 573,676 | 49,786 | 6,341 | 22 | 319,577 | 26,037 | 3,311 |
| `scope-read` | positive | `claude-opus-5` | 2 | 19 | 12 | 38 | 555,246 | 50,799 | 5,459 | 24 | 363,260 | 27,281 | 3,407 |
| `scope-read` | positive | `claude-opus-5` | 3 | 16 | 10 | 32 | 446,454 | 45,454 | 5,041 | 20 | 282,413 | 25,503 | 2,847 |
| `scope-read` | positive | `claude-sonnet-5` | 1 | 34 | 17 | 68 | 1,462,003 | 76,457 | 17,617 | 34 | 757,600 | 38,149 | 8,682 |
| `scope-read` | positive | `claude-sonnet-5` | 2 | 28 | 15 | 56 | 1,083,404 | 65,296 | 8,547 | 30 | 594,151 | 29,534 | 4,097 |
| `scope-read` | positive | `claude-sonnet-5` | 3 | 27 | 14 | 54 | 1,045,687 | 58,550 | 7,565 | 28 | 547,311 | 29,537 | 3,931 |
| `template-adherence` | control | `claude-haiku-4-5-20251001` | 1 | 18 | 8 | 150 | 404,306 | 50,432 | 5,619 | 66 | 181,931 | 18,930 | 2,215 |
| `template-adherence` | control | `claude-haiku-4-5-20251001` | 2 | 12 | 5 | 102 | 264,354 | 47,283 | 4,620 | 42 | 112,698 | 17,372 | 1,831 |
| `template-adherence` | control | `claude-haiku-4-5-20251001` | 3 | 16 | 5 | 136 | 479,891 | 126,035 | 6,533 | 42 | 164,516 | 34,404 | 1,950 |
| `template-adherence` | control | `claude-opus-5` | 1 | 19 | 13 | 40 | 556,895 | 50,736 | 5,940 | 28 | 404,446 | 27,889 | 3,658 |
| `template-adherence` | control | `claude-opus-5` | 2 | 21 | 13 | 42 | 618,104 | 51,667 | 6,211 | 26 | 395,805 | 27,577 | 3,907 |
| `template-adherence` | control | `claude-opus-5` | 3 | 25 | 17 | 52 | 774,454 | 52,925 | 6,270 | 36 | 550,746 | 29,220 | 4,232 |
| `template-adherence` | control | `claude-sonnet-5` | 1 | 36 | 19 | 72 | 1,517,258 | 79,588 | 20,362 | 38 | 856,119 | 36,322 | 9,964 |
| `template-adherence` | positive | `claude-haiku-4-5-20251001` | 1 | 14 | 5 | 120 | 317,046 | 51,109 | 5,492 | 42 | 117,619 | 16,296 | 1,787 |
| `template-adherence` | positive | `claude-haiku-4-5-20251001` | 2 | 18 | 6 | 152 | 394,944 | 63,996 | 6,649 | 50 | 137,658 | 19,438 | 2,195 |
| `template-adherence` | positive | `claude-haiku-4-5-20251001` | 3 | 12 | 5 | 102 | 263,733 | 47,205 | 4,175 | 42 | 112,421 | 17,353 | 1,616 |
| `template-adherence` | positive | `claude-opus-5` | 1 | 14 | 10 | 28 | 393,987 | 43,554 | 3,648 | 20 | 289,810 | 25,877 | 2,508 |
| `template-adherence` | positive | `claude-opus-5` | 2 | 25 | 14 | 50 | 726,217 | 62,338 | 8,745 | 28 | 438,598 | 28,286 | 4,505 |
| `template-adherence` | positive | `claude-opus-5` | 3 | 18 | 10 | 36 | 507,050 | 49,953 | 5,635 | 20 | 286,662 | 26,164 | 2,982 |
| `template-adherence` | positive | `claude-sonnet-5` | 1 | 27 | 15 | 54 | 1,068,632 | 66,821 | 13,799 | 30 | 600,675 | 34,144 | 7,400 |
| `template-adherence` | positive | `claude-sonnet-5` | 2 | 23 | 14 | 46 | 885,170 | 54,157 | 6,121 | 28 | 556,641 | 29,257 | 3,639 |
| `template-adherence` | positive | `claude-sonnet-5` | 3 | 28 | 16 | 56 | 1,138,808 | 62,292 | 10,709 | 32 | 668,192 | 32,456 | 5,875 |

### gap-study-2: per walk

| walk | records | calls | published: input | cache read | cache write | output | counted once: input | cache read | cache write | output |
|---|---|---|---|---|---|---|---|---|---|---|
| `confounded-design` 1 | 37 | 22 | 74 | 1,628,503 | 86,139 | 10,063 | 44 | 1,000,419 | 41,435 | 5,787 |
| `number-fidelity` 1 | 27 | 15 | 54 | 1,071,105 | 67,322 | 11,990 | 30 | 621,833 | 32,187 | 6,319 |
| `plan-gate` 1 | 39 | 19 | 78 | 1,680,927 | 104,397 | 19,659 | 38 | 858,686 | 45,535 | 9,282 |
| `precondition-refusal` 1 | 10 | 4 | 20 | 293,559 | 56,688 | 3,776 | 8 | 118,103 | 21,467 | 1,552 |
| `scope-read` 1 | 34 | 17 | 68 | 1,435,740 | 69,697 | 13,630 | 34 | 718,980 | 35,172 | 6,739 |
| `template-adherence` 1 | 29 | 15 | 58 | 1,167,889 | 72,187 | 13,901 | 30 | 623,530 | 36,446 | 6,988 |

## `gap-study-3`

### gap-study-3: totals of the Per take table

54 transcripts; 1,868 usage records hold 918 calls.

| class | published | counted once per call | published over counted |
|---|---|---|---|
| input | 7,798 | 3,402 | 2.29 |
| cache read | 71,066,178 | 36,829,214 | 1.93 |
| cache write | 4,445,191 | 1,864,229 | 2.38 |
| output | 736,755 | 349,711 | 2.11 |

### gap-study-3: totals of the Pre-freeze walks table

8 transcripts; 217 usage records hold 92 calls.

| class | published | counted once per call | published over counted |
|---|---|---|---|
| input | 1,404 | 550 | 2.55 |
| cache read | 7,051,939 | 3,125,143 | 2.26 |
| cache write | 627,122 | 232,640 | 2.70 |
| output | 83,905 | 34,693 | 2.42 |

### gap-study-3: per model

| model | graded takes | context tokens, published | context tokens, counted once | output tokens, published | output tokens, counted once |
|---|---|---|---|---|---|
| `claude-haiku-4-5-20251001` | 18 | 23,112,300 | 9,049,159 | 196,704 | 71,465 |
| `claude-opus-5` | 18 | 21,217,896 | 12,318,891 | 215,417 | 112,715 |
| `claude-sonnet-5` | 18 | 31,188,971 | 17,328,795 | 324,634 | 165,531 |

### gap-study-3: per take

Published cells first, then the same cells counted once per call.

| task | half | model | take | records | calls | published: input | cache read | cache write | output | counted once: input | cache read | cache write | output |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `confounded-design` | control | `claude-haiku-4-5-20251001` | 1 | 21 | 10 | 180 | 592,278 | 52,137 | 5,477 | 86 | 283,983 | 22,558 | 2,524 |
| `confounded-design` | control | `claude-haiku-4-5-20251001` | 2 | 79 | 35 | 662 | 2,839,962 | 95,372 | 18,642 | 294 | 1,278,579 | 37,513 | 8,219 |
| `confounded-design` | control | `claude-haiku-4-5-20251001` | 3 | 16 | 5 | 138 | 349,018 | 70,782 | 8,317 | 42 | 117,741 | 20,510 | 2,463 |
| `confounded-design` | control | `claude-opus-5` | 1 | 42 | 23 | 84 | 1,624,799 | 111,177 | 16,566 | 46 | 933,092 | 46,316 | 8,422 |
| `confounded-design` | control | `claude-opus-5` | 2 | 45 | 27 | 90 | 1,758,931 | 94,627 | 14,970 | 54 | 1,112,553 | 46,398 | 8,509 |
| `confounded-design` | control | `claude-opus-5` | 3 | 42 | 27 | 84 | 1,640,049 | 90,897 | 14,225 | 54 | 1,098,686 | 45,122 | 8,677 |
| `confounded-design` | control | `claude-sonnet-5` | 1 | 55 | 31 | 110 | 2,791,339 | 103,243 | 24,941 | 62 | 1,634,859 | 53,153 | 13,141 |
| `confounded-design` | control | `claude-sonnet-5` | 2 | 60 | 35 | 120 | 3,037,446 | 108,153 | 26,734 | 70 | 1,833,033 | 55,177 | 14,810 |
| `confounded-design` | control | `claude-sonnet-5` | 3 | 39 | 23 | 78 | 1,741,774 | 87,767 | 13,133 | 46 | 1,046,793 | 42,139 | 7,149 |
| `confounded-design` | positive | `claude-haiku-4-5-20251001` | 1 | 54 | 24 | 466 | 1,909,241 | 101,711 | 18,496 | 206 | 883,863 | 35,537 | 7,709 |
| `confounded-design` | positive | `claude-haiku-4-5-20251001` | 2 | 38 | 14 | 312 | 1,593,914 | 106,755 | 12,791 | 114 | 592,945 | 40,410 | 4,468 |
| `confounded-design` | positive | `claude-haiku-4-5-20251001` | 3 | 34 | 13 | 280 | 985,329 | 81,792 | 11,370 | 106 | 396,823 | 24,521 | 3,918 |
| `confounded-design` | positive | `claude-opus-5` | 1 | 50 | 29 | 100 | 2,006,990 | 102,010 | 20,625 | 58 | 1,210,075 | 48,254 | 11,146 |
| `confounded-design` | positive | `claude-opus-5` | 2 | 48 | 24 | 96 | 1,867,267 | 126,818 | 17,889 | 48 | 993,342 | 46,082 | 8,495 |
| `confounded-design` | positive | `claude-opus-5` | 3 | 47 | 25 | 94 | 1,931,457 | 102,215 | 17,762 | 50 | 1,057,381 | 46,580 | 9,169 |
| `confounded-design` | positive | `claude-sonnet-5` | 1 | 32 | 17 | 64 | 1,319,598 | 74,304 | 24,910 | 34 | 711,791 | 39,119 | 13,003 |
| `confounded-design` | positive | `claude-sonnet-5` | 2 | 58 | 32 | 116 | 3,282,647 | 141,366 | 28,475 | 64 | 1,900,022 | 60,930 | 14,362 |
| `confounded-design` | positive | `claude-sonnet-5` | 3 | 19 | 10 | 38 | 674,302 | 53,989 | 4,151 | 20 | 360,490 | 27,233 | 2,219 |
| `scope-read` | control | `claude-haiku-4-5-20251001` | 1 | 21 | 7 | 176 | 534,515 | 63,818 | 8,341 | 58 | 184,523 | 19,657 | 2,682 |
| `scope-read` | control | `claude-haiku-4-5-20251001` | 2 | 43 | 16 | 352 | 1,238,982 | 73,396 | 12,913 | 130 | 460,729 | 25,018 | 4,481 |
| `scope-read` | control | `claude-haiku-4-5-20251001` | 3 | 26 | 11 | 226 | 715,165 | 70,203 | 10,464 | 94 | 322,849 | 23,416 | 3,688 |
| `scope-read` | control | `claude-opus-5` | 1 | 23 | 13 | 46 | 677,085 | 66,697 | 8,029 | 26 | 425,344 | 28,943 | 4,440 |
| `scope-read` | control | `claude-opus-5` | 2 | 25 | 11 | 50 | 767,320 | 80,985 | 10,904 | 22 | 358,192 | 29,689 | 4,839 |
| `scope-read` | control | `claude-opus-5` | 3 | 19 | 10 | 38 | 541,420 | 69,840 | 7,757 | 20 | 312,706 | 30,669 | 3,831 |
| `scope-read` | control | `claude-sonnet-5` | 1 | 32 | 17 | 64 | 1,322,560 | 73,546 | 15,549 | 34 | 730,283 | 35,452 | 7,752 |
| `scope-read` | control | `claude-sonnet-5` | 2 | 33 | 15 | 66 | 1,363,112 | 94,920 | 20,589 | 30 | 657,010 | 36,812 | 9,507 |
| `scope-read` | control | `claude-sonnet-5` | 3 | 40 | 22 | 80 | 1,796,526 | 89,869 | 28,371 | 44 | 1,038,619 | 44,075 | 14,723 |
| `scope-read` | positive | `claude-haiku-4-5-20251001` | 1 | 32 | 13 | 276 | 909,017 | 70,142 | 8,760 | 112 | 389,066 | 23,138 | 3,358 |
| `scope-read` | positive | `claude-haiku-4-5-20251001` | 2 | 21 | 9 | 184 | 774,723 | 87,289 | 6,473 | 78 | 354,028 | 34,528 | 2,531 |
| `scope-read` | positive | `claude-haiku-4-5-20251001` | 3 | 41 | 16 | 334 | 1,249,913 | 66,263 | 9,596 | 130 | 482,633 | 24,306 | 3,618 |
| `scope-read` | positive | `claude-opus-5` | 1 | 23 | 12 | 46 | 704,783 | 67,423 | 10,942 | 24 | 396,364 | 30,282 | 5,416 |
| `scope-read` | positive | `claude-opus-5` | 2 | 22 | 11 | 44 | 645,920 | 77,441 | 10,711 | 22 | 353,633 | 29,440 | 5,160 |
| `scope-read` | positive | `claude-opus-5` | 3 | 28 | 15 | 56 | 882,515 | 75,823 | 10,858 | 30 | 516,262 | 31,089 | 5,564 |
| `scope-read` | positive | `claude-sonnet-5` | 1 | 38 | 20 | 76 | 1,679,784 | 81,642 | 24,468 | 40 | 917,369 | 41,818 | 12,414 |
| `scope-read` | positive | `claude-sonnet-5` | 2 | 39 | 20 | 78 | 1,670,964 | 73,972 | 16,264 | 40 | 862,774 | 37,303 | 8,138 |
| `scope-read` | positive | `claude-sonnet-5` | 3 | 30 | 16 | 60 | 1,332,096 | 74,417 | 14,881 | 32 | 733,850 | 36,955 | 7,730 |
| `template-adherence` | control | `claude-haiku-4-5-20251001` | 1 | 65 | 21 | 528 | 2,824,887 | 123,463 | 17,439 | 170 | 921,816 | 39,460 | 5,687 |
| `template-adherence` | control | `claude-haiku-4-5-20251001` | 2 | 35 | 14 | 286 | 1,030,846 | 63,302 | 10,027 | 114 | 407,170 | 23,396 | 3,719 |
| `template-adherence` | control | `claude-haiku-4-5-20251001` | 3 | 45 | 16 | 368 | 1,889,272 | 123,460 | 12,720 | 130 | 686,001 | 40,055 | 4,310 |
| `template-adherence` | control | `claude-opus-5` | 1 | 28 | 16 | 56 | 898,664 | 68,887 | 9,915 | 32 | 552,641 | 31,159 | 5,411 |
| `template-adherence` | control | `claude-opus-5` | 2 | 26 | 13 | 52 | 782,884 | 80,919 | 9,991 | 26 | 434,604 | 30,207 | 4,621 |
| `template-adherence` | control | `claude-opus-5` | 3 | 30 | 18 | 60 | 970,829 | 69,574 | 8,879 | 36 | 631,059 | 31,755 | 5,109 |
| `template-adherence` | control | `claude-sonnet-5` | 1 | 30 | 15 | 60 | 1,207,127 | 71,412 | 16,816 | 30 | 607,980 | 34,732 | 7,359 |
| `template-adherence` | control | `claude-sonnet-5` | 2 | 28 | 17 | 56 | 1,142,913 | 59,687 | 8,346 | 34 | 717,421 | 31,722 | 4,513 |
| `template-adherence` | control | `claude-sonnet-5` | 3 | 35 | 18 | 70 | 1,452,859 | 72,690 | 14,092 | 36 | 788,191 | 35,741 | 7,115 |
| `template-adherence` | positive | `claude-haiku-4-5-20251001` | 1 | 14 | 5 | 118 | 305,330 | 52,179 | 4,300 | 42 | 112,186 | 17,795 | 1,612 |
| `template-adherence` | positive | `claude-haiku-4-5-20251001` | 2 | 19 | 7 | 158 | 459,055 | 52,842 | 6,980 | 58 | 170,393 | 18,025 | 2,457 |
| `template-adherence` | positive | `claude-haiku-4-5-20251001` | 3 | 36 | 12 | 298 | 1,417,000 | 133,605 | 13,598 | 98 | 492,987 | 38,939 | 4,021 |
| `template-adherence` | positive | `claude-opus-5` | 1 | 22 | 13 | 44 | 655,434 | 63,354 | 7,965 | 26 | 423,344 | 29,064 | 4,431 |
| `template-adherence` | positive | `claude-opus-5` | 2 | 23 | 13 | 46 | 706,841 | 65,935 | 8,567 | 26 | 432,416 | 29,638 | 4,613 |
| `template-adherence` | positive | `claude-opus-5` | 3 | 22 | 13 | 44 | 672,582 | 66,374 | 8,862 | 26 | 435,720 | 30,164 | 4,862 |
| `template-adherence` | positive | `claude-sonnet-5` | 1 | 37 | 19 | 74 | 1,541,576 | 77,481 | 14,979 | 38 | 817,677 | 35,326 | 7,309 |
| `template-adherence` | positive | `claude-sonnet-5` | 2 | 34 | 19 | 68 | 1,448,683 | 67,344 | 14,411 | 38 | 827,222 | 35,380 | 7,745 |
| `template-adherence` | positive | `claude-sonnet-5` | 3 | 24 | 11 | 48 | 906,655 | 69,882 | 13,524 | 22 | 428,101 | 31,529 | 6,542 |

### gap-study-3: per walk

| walk | records | calls | published: input | cache read | cache write | output | counted once: input | cache read | cache write | output |
|---|---|---|---|---|---|---|---|---|---|---|
| `confounded-design` 1 | 40 | 17 | 342 | 1,260,713 | 79,501 | 10,306 | 146 | 544,625 | 29,279 | 4,306 |
| `confounded-design` 2 | 15 | 5 | 130 | 332,412 | 56,729 | 7,640 | 42 | 119,107 | 18,241 | 2,436 |
| `scope-read` 1 | 30 | 12 | 258 | 917,293 | 69,760 | 12,537 | 102 | 365,371 | 25,997 | 4,810 |
| `scope-read` 2 | 33 | 11 | 272 | 1,316,938 | 136,720 | 10,400 | 90 | 457,298 | 38,844 | 3,279 |
| `template-adherence` 1 | 25 | 14 | 50 | 983,459 | 70,225 | 17,498 | 28 | 572,382 | 37,087 | 9,180 |
| `template-adherence` 2 | 32 | 12 | 268 | 910,107 | 72,949 | 10,566 | 100 | 350,897 | 23,717 | 3,586 |
| `template-adherence` 3 | 22 | 12 | 44 | 797,568 | 57,458 | 6,923 | 24 | 445,483 | 29,576 | 3,578 |
| `template-adherence` 4 | 20 | 9 | 40 | 533,449 | 83,780 | 8,035 | 18 | 269,980 | 29,899 | 3,518 |

## Prose figures

| where | published words | published, exact | counted once per call |
|---|---|---|---|
| evals/gap-study/COSTS.md, the walks note and the notes recorded before any take | "5.5 to 6.4 M context tokens" | 5,463,264 and 6,439,228 | 2.5 to 2.9 M (2,472,062 and 2,925,308) |
| evals/gap-study/COSTS.md, the walks note | "1.1 to 2.0 M context tokens" | 1,079,829 and 2,029,550 | 0.4 to 0.8 M (425,129 and 773,958) |

## Where the published figures are cited

Each line below quotes or describes a published token figure, or names the tables as the token record.
None is edited: each sits inside a finished study's folder (the three rounds, and the pre-study whose lint file round 2 copied), which is a record, and rounds 1 and 2 are also bound byte for byte by the copy checks of rounds 2 and 3.
The input cell quoted as one hundred is the published figure for `confounded-design`, positive, `claude-opus-5`, take 1, in round 1 and again in round 3; counted once per call it is 56 and 58.
Outside the three study folders, one copy of round 2's lint comment lives in `evals/haiku-prestudy/`; no `README.md`, `docs/` or `DEVELOPMENT.md` page quoted these figures before this correction, and `docs/EVALS.md` now points here.
The list is complete as of a sweep of every tracked file at `a272d95`: `git grep -w -F` for each distinct comma-grouped figure in the three tables (re-run by this correction's tests, which fail on any hit not listed), and `git grep -i "one hundred"`, read line by line.

| where | what it quotes |
|---|---|
| `evals/gap-study/COSTS.md:21` | the per-take table |
| `evals/gap-study/COSTS.md:137` | the walks table |
| `evals/gap-study/COSTS.md:157` | prose: a take of the earlier Layer B evaluation |
| `evals/gap-study/COSTS.md:161` | prose: the first two walks |
| `evals/gap-study/COSTS.md:168` | the per-model table |
| `evals/gap-study/COSTS.md:201` | prose: the same Layer B take |
| `evals/gap-study/README.md:43` | names COSTS.md as the token record |
| `evals/gap-study/language-allowlist.json:21` | an excusal quoting a published row |
| `evals/gap-study/language-allowlist.json:23` | the input cell published as one hundred |
| `evals/gap-study/language-allowlist.json:28` | an excusal quoting a published row |
| `evals/gap-study/verification/2026-09-12-95c4923.md:947` | a verifier report quoting a published row |
| `evals/gap-study/verification/2026-09-12-95c4923.md:948` | a verifier report quoting a published row |
| `evals/gap-study/verification/2026-09-12-95c4923.md:958` | a verifier report quoting a published row |
| `evals/gap-study/verification/2026-09-12-95c4923.md:959` | a verifier report quoting a published row |
| `evals/gap-study/verification/2026-09-12-95c4923.md:960` | a verifier report quoting a published row |
| `evals/gap-study/verification/2026-09-12-a463ed5.md:948` | a verifier report quoting a published row |
| `evals/gap-study/verification/2026-09-12-a463ed5.md:949` | a verifier report quoting a published row |
| `evals/gap-study/verification/2026-09-12-a463ed5.md:961` | a verifier report quoting a published row |
| `evals/gap-study/verification/2026-09-12-a463ed5.md:962` | a verifier report quoting a published row |
| `evals/gap-study/verification/2026-09-12-a463ed5.md:963` | a verifier report quoting a published row |
| `evals/gap-study-2/COSTS.md:11` | the per-take table |
| `evals/gap-study-2/COSTS.md:122` | the walks table |
| `evals/gap-study-2/COSTS.md:133` | the per-model table |
| `evals/gap-study-2/lint_language.py:67` | a lint comment quoting a published cache-write cell |
| `evals/gap-study-2/test_harness.py:2216` | a test docstring quoting the same cell |
| `evals/gap-study-2/test_harness.py:2222` | a test quoting two published cells |
| `evals/gap-study-2/PROTOCOL.md:1656` | describes the same cell, no number |
| `evals/gap-study-2/prereg.json:3699` | describes the same cell, no number |
| `evals/gap-study-2/verification/verifier-1.md:375` | a verifier report quoting a published row |
| `evals/gap-study-2/verification/verifier-1.md:379` | a verifier report quoting a published row |
| `evals/gap-study-2/verification/verifier-1.md:380` | a verifier report quoting a published row |
| `evals/gap-study-2/verification/verifier-1.md:381` | a verifier report quoting a published row |
| `evals/gap-study-2/verification/verifier-2.md:448` | a verifier report quoting a published row |
| `evals/gap-study-2/verification/verifier-2.md:452` | a verifier report quoting a published row |
| `evals/gap-study-2/verification/verifier-2.md:453` | a verifier report quoting a published row |
| `evals/gap-study-2/verification/verifier-2.md:454` | a verifier report quoting a published row |
| `evals/gap-study-3/COSTS.md:11` | the per-take table |
| `evals/gap-study-3/COSTS.md:70` | the walks table |
| `evals/gap-study-3/COSTS.md:83` | the per-model table |
| `evals/gap-study-3/lint_language.py:67` | a lint comment quoting a published cache-write cell |
| `evals/gap-study-3/language-allowlist.json:14` | an excusal quoting a published row |
| `evals/gap-study-3/language-allowlist.json:16` | the input cell published as one hundred |
| `evals/gap-study-3/prereg.json:2616` | the input cell published as one hundred |
| `evals/gap-study-3/RESULT.md:206` | the input cell published as one hundred |
| `evals/gap-study-3/PROGRESS.md:42` | the input cell published as one hundred |
| `evals/gap-study-3/verification/verify-1.md:205` | the input cell published as one hundred |
| `evals/gap-study-3/verification/verify-1.md:210` | the input cell published as one hundred |
| `evals/gap-study-3/verification/verify-2.md:198` | the input cell published as one hundred |
| `evals/gap-study-3/verification/verify-2.md:204` | the input cell published as one hundred |
| `evals/gap-study-3/verification/verify-3.md:211` | the input cell published as one hundred |
| `evals/gap-study-3/verification/verify-3.md:217` | the input cell published as one hundred |
| `evals/haiku-prestudy/lint_language.py:67` | a lint comment quoting a published cache-write cell (round 2's copy) |
