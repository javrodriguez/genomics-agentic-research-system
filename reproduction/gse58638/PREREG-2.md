# PREREG-2: the binding and the report under the recorded IN KIND verdict

_Written Wed 30 Sep 2026, 11:39 EDT, by glitch-14 (the orchestrator), under Javier's standing delegation of build decisions (23 Sep); a ruling, not his words._
_**Written AFTER step 1 read the deposit bytes.** It is a dated rule beside `PREREG.md` (sha256 `1f1a9d59…`), as P9 allows. It changes no verdict: step 1's verdict stays **IN KIND, adopted basis B1** (`VERDICT-step1.md`)._

## Why it exists

P10 says that under IN KIND "the binding asserts the P6 relation against the frozen verdict".
Step 1 measured that P6's thresholds do not hold under B1: the other/GSM1420155 ratios are 4.17, 4.42 and 4.56 at z>1 (P6 asks at least 5) and one is 19.15 at z>2 (P6 asks at least 20).
A binding that asserts P6 would therefore assert something false, and a binding that passes anyway would be a check that cannot fail.
P10 also asks the binding to assert that an addendum's figures equal the recompute exactly; the approved row 3a addendum quotes line 73's figure 0.067, which comes from pyBigWig's approximate tile mean (B6), a basis P4 says the stdlib instrument never implements.

## Rules (they replace P10's IN KIND binding only; P0-P9 stand as frozen)

- **R1. Verdict unchanged.** The report prints `IN KIND` for T1 and T2, never `MATCH`, and names the adopted basis B1.
- **R2. P6 stated, not asserted.** The report prints P6's thresholds and the measured B1 ratios, and says plainly that P6's thresholds are not met under B1 (z>1 ratios 4.17-4.56 against 5; one z>2 ratio 19.15 against 20). No test asserts P6.
- **R3. What the binding asserts on B1** (true by step 1's measurement, and falsifiable by a changed deposit or a broken reader): GSM1420155 has the lowest z>1 fraction and the lowest z>2 fraction of the four deposits; and the recompute's B1 fractions and ratios equal the step-1 values in `step1.md` to the precision printed there (the committed `expected.txt`, written only by the script, is the byte-level pin).
- **R4. B4 reported as the nearest exact basis.** B4 (P4's exact 10-kb tile mean, implementable in the stdlib) is computed and printed beside B1: 0.0074 for GSM1420155 against 0.053-0.083 for the others (P1's T1 prints 0.0073: one rounding step), z>2 ratios 44-108×; and C1 on B4: DKO1 mean 0.068, HCT116 0.045 with GSM1420155 and 0.083 without it. The report says line 73's 0.067 reproduces only under pyBigWig's approximate mean (B6, step 1), and that the direction reverses without GSM1420155 under every tile basis.
- **R5. The addendum binding.** Once the row 3a addendum is in the base, the binding asserts: its 0.083 (healthy HCT116 without GSM1420155) equals the B4 recompute at that precision; the reversal it states (healthy HCT116 above DKO1) holds on B4; and its 0.067 and 0.045 are found verbatim as quotations of line 73, not as recompute outputs. The binding never asserts 0.067 as a recompute figure.
- **R6. Nothing here is edited later.** A further change is a PREREG-3 beside this one.
