# A canned goal file for check_checklist_names.py

## What gets built

1. A class named here is outside the Done section and is not read: `test_harness.py OutsideTheSection`.

## Done means

1. **A line naming one test** — verify: `test_harness.py AlphaCheck` → exit 0.
2. **A line naming two tests and a flag** — verify: `python3 x/test_harness.py BetaCheck GammaCheck --verbose` → exit 0.
3. **A line naming a bare class** — verify: `DeltaCheck` is listed; `test_harness.py --mutations` names nothing; `k of n` is not a name.

## The clock

1. `test_harness.py EpsilonAfterTheSection` is not read.
