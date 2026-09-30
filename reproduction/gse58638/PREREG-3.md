# PREREG-3: two printed step-1 figures, bound at one rounding

_Written Wed 30 Sep 2026, 15:33 EDT, by glitch-14 (the orchestrator), under Javier's standing delegation of build decisions (23 Sep); a ruling, not his words._
_**Written AFTER step 1 and after the recompute's first full runs.** It is a dated rule beside `PREREG.md` (sha256 `1f1a9d59…`) and `PREREG-2.md`, as P9 allows. It changes no verdict: step 1's verdict stays **IN KIND, adopted basis B1**._

## Why it exists

PREREG-2 R3 asks the recompute's B1 fractions and ratios to equal step 1's values "to the precision printed there".
Two printed step-1 figures were the exact count rounded twice (first to one more figure, then again), so a correct recompute printed once from the exact rational differs from them by one step:
- GSM1420155's B1 z>2 fraction: step 1 printed 0.00200; the exact rational is 0.0020050…, which rounds once, half-up, to 0.00201.
- The B4 z>2 ratio range: PREREG-2 R4 wrote "44-108×"; step 1's three-figure ratios are 43.5, 101.1 and 108.2, so the range printed at step 1's own precision is 43.5-108×.
The recompute found no bin in (2, 2.00005] for GSM1420155, so the difference is in the printing, not in the counts.

## Rules

- **Q1.** R3's comparison with step 1 is made on the exact counts, and each printed figure is rounded once, half-up, from the exact rational. Where a step-1 printed figure differs from that single rounding, the binding asserts the exact-count equality and names the cell and the reason (double rounding), never the step-1 printed digit.
- **Q2.** R4's range reads "43.5-108×" at step 1's three-figure precision.
- **Q3.** Nothing here is edited later. A further change is a PREREG-4 beside this one.
