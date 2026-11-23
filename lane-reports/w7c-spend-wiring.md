status: closed (review round 2 PASS; fold W7C-close-2 on top)
head: see RESUME HERE. Base 82cf6ae9 (the wave 7 merge head), branch gap4/w7c-spend-wiring, worktree /Users/javrodher/aegis-builds/gap4-w7c.

# Lane w7c-spend-wiring: Gap Study round 4, wave 7, the spend-guard wiring

_Written Mon 12 Oct 2026 00:28 EDT (`date`) by the lane's sole writer (Claude Opus 5.5 sub-agent), assigned by glitch-1b under Javier's standing delegation, ruling W7C-gap4-1. Spec: the "Spend-marker proposal drafted" and "Wave 7 continued" blocks of plans/gap-study-round-4/next-slices-2026-10-11.md; the verified gaps in sections 3 and 5 of spend-markers-proposal-2026-10-11.md (a PROPOSAL, not in force; its proposed status text is written nowhere); D8 B2 and the month-turn hold (CD8-1) in the plan._

No model was run, no API, vendor, network, Docker or credential was used, and no holdout, brief, saved-output or `.env` path was read.
Nothing was pushed.
`spend_cap_markers_status`, `pin_profiles_status`, every PENDING value and `start_problems` are unchanged; costs.py is not edited.

## What each item does, with its test

- **Item 1, the money gate (batch.py).**
  Before each block is registered, `Batch._money_gate` puts every row whose harness bills money per call (any harness but `routing.NO_MONEY_HARNESSES`, i.e. codex and gemini) through `costs.month_turn_allowed(arm, now, trimmed)`, with the arm from `routing.PAID_HARNESSES`, and `costs.walk_gate(walks, spend, start)`, on one reading of a new `ledger` argument (`ledger.read()`, exactly `LEDGER_KEYS`: now, walks, spend, start, trimmed).
  Anything but an explicit allow from each (False, a raise, a decision other than "within round caps"), an unreadable or misshapen ledger, or a paid harness with no arm stops the loop with `stopped` = blocked and the named reason; nothing of the block is registered or launched, nothing is committed, so a restart puts the block through the gate again.
  A paid row handed to a loop with no ledger is refused by `row_problems` before anything runs.
  claude-code rows (arms A and C) never read the ledger and never call either check.
  Tests (tests/test_spend_wiring.py): G1-claude, G2-month (hold refuses O and G; a recorded trim or a time outside the hold runs; costs' own function is the one called, with the row's arm and the ledger's clock), G3-walk (a spent cap, a projection past a cap, inputs the gate refuses, and any decision but PROCEED refuse), G4-ledger, G5-order (a refused block's claude-code rows wait too; serial blocks read the ledger once each, before each registration).
- **Item 2, no empty paid list (routing.py).**
  `check_table` (so `load_table` and `routing.py --check`) refuses a spend-cap entry naming no marker in any field for every harness except claude-code; claude-code's list stays empty and sound.
  `PAID_HARNESSES` = codex: arm O, openai; gemini: arm G, google. `load_table(path=None)` reads `TABLE_PATH` at call time, so `--check` can be driven on a temporary table.
  Tests R1-nonempty (codex, gemini and a made-up paid harness refused at all three doors; a gemini list holding only status 402 sound) and B1-names (the names bound to box/run_take.py, the arms to build_draft.HARNESSES, the vendors to costs.CAPS).
- **Item 3, still pending.** Test P3-pending: both statuses still start PENDING, pin_profiles is empty, `start_problems` and `batch.py --check` give exactly the base's three lines with exit 1, and `Batch` on routing.json refuses with the base's words even with a ledger.

## Red first, then green (Python 3.13, each command behind `mac_slot.py light-ok` and `timeout -s INT 120`)

- Red on the base code (tests written first): test_spend_wiring exit 1, 18 ran, 16 failures, 0 errors; every failure an AssertionError (the gate tests failed on `Batch(ledger=...)` not existing, reported as an ERROR line inside the check, never a raised error; R1 on the admitted empty lists; B1 on the missing names).
  The two that passed on the base are the sound-test-table test and the witness-registry test.
- Green: test_spend_wiring exit 0 (19 ran, OK); test_routing exit 0 (276); test_batch exit 0 (118); test_check_take 0 (15); test_drive_loop 0 (27); test_walk_wiring 0 (20); test_build_draft 0 (45).
  test_box_integration does not finish in one 120 s cap (exit 124 by SIGINT, 43 passed, 0 failures when cut), so it ran class by class: TestGuardArmed 0 (2), TestTheTakePath 0 (17), TestBoundChecks 0 (19), TestRealBoxStub 0 (1); its TestWitnesses (drive.py whole-file witnesses, untouched here) was cut at 120 s with 18 ok and 0 failures. Athena's run is the evidence for the rest.
- Script checks: `routing.py --check` exit 0 (22 rows, 3 annotations, sound); `batch.py --check` exit 1 with the base's three lines; `copy_manifest.py --check` exit 0 (264 files, 40 fragments); `freeze.py --check` exit 0 (264 owned paths); w1b's import guard holds (costs is imported inside `money_gate_problems`, since costs imports batch).

## Witnesses (rule B: the bound check green on the tree first, then killed by its own line, 0 errors, collateral listed)

gate-never-called (G2-month, 10 own), month-check-dropped (G2-month, 10), walk-check-dropped (G3-walk, 16), claude-gated (G1-claude, 6), no-ledger-passes (G4-ledger, 2), gate-after-register (G5-order, 3), spend-status-ungated (P3-pending, 3), empty-paid-list-admitted (R1-nonempty, 9), paid-arm-renamed (B1-names, 1): 9 of 9 red, 0 collateral, 0 errors.

## Ownership (ruling W7C-gap4-1)

batch.py and routing.py move from w1b-cp1-routing-batch to COPIED.d/w7c-spend-wiring.json (w1b's own fragment entry names the transfer); tests/test_spend_wiring.py is new and claimed there; tests/test_batch.py and tests/test_routing.py were not edited and stay with w1b, whose checks.d keeps running them.
checks.d/w7c-spend-wiring.txt runs the new module, `routing.py --check`, and the pending `batch.py --check` line (red on purpose once either status is ruled, as w1b's).

## Open questions and carried items

- Q-w7c-1: the month-turn clock is the ledger's `now`; CP2's ledger must read a real aware UTC clock (a naive one refuses). Should batch take its own clock instead?
- Q-w7c-2: a refused block stops the whole loop, so a held O/G row also holds later claude-code rows (frozen order kept, as a pause holds every arm). Confirm that is wanted, against skipping only the paid rows.
- Carried: no production ledger exists (CP2: vendor spend reads, the walks' remaining tries and cost per try, the recorded trim); until one is passed every O/G row is refused.
- Carried (not mine to edit): costs.py's docstring still says "the driver owns invoking them before a take"; it is now the loop. Owner: w5b's fragment.
- The proposal's status text, his option 1/2/3 letters and test_routing.py:2490 stay untouched until Javier rules.

Code commit: 0c980a0a (base 82cf6ae9). After the commit, copy_manifest.py --check exit 0 (264 files, 40 fragments) and freeze.py --check exit 0 on the committed index.

RESUME HERE: hand-back at 0c980a0a

## Fold Q-w7c-1 (glitch-1b's rulings, 12 Oct 2026, recorded in next-slices)

_Written Mon 12 Oct 2026 (`date`)._
Q-w7c-1: the month-turn hold now reads batch's OWN clock: `Batch(clock=...)`, default `utc_now()` (aware UTC, read at each block's check), passed to `money_gate_problems`; the ledger's `now` stays in LEDGER_KEYS (recorded) but never decides the hold.
A clock that raises or reads naive refuses the paid block.
Q-w7c-2: kept as built (a refused paid row stops the whole loop).
Test G6-clock: the ledger says 15 Oct while batch's clock is 31 Oct 23:45 UTC -> refused; the ledger says inside the hold while the clock says 15 Oct -> runs; the clock is read for a paid block. Witness ledger-clock (the hold reads `snap["now"]`) red by G6-clock (6 own, 0 collateral, 0 errors); month-check-dropped's anchor follows the new line.
Red first: test_spend_wiring exit 1, 21 ran, 13 failures, 0 errors (all AssertionError; `clock=` did not exist).
Green: test_spend_wiring exit 0 (21, 10 of 10 witnesses red); test_batch exit 0 (118); batch.py --check exit 1 on the base's three lines; copy_manifest and freeze --check exit 0; import guard holds.

Code commit (fold): bd60d8da on 66fb0dac.

RESUME HERE: hand-back at bd60d8da

## Review fold W7C-close-1 (round 1: CHANGES, 1 MAJOR; table plans/gap-study-round-4/w7c-review-r1-2026-10-12.md)

_Written Mon 12 Oct 2026 (`date`)._
- W7C-R1-1 (MAJOR): `ledger_shape_problems` refuses walks or spend that are not exactly `list` (so "", {}, a tuple, None), any element that is not a dict, and a start that is neither a str nor an aware datetime. G4 adds ten cases; witness shape-unchecked red by G4-ledger (24 own, 0 collateral, 0 errors).
- W7C-R1-2: a start after the loop's clock (the same reading the hold uses) is refused; G3 case $300 OpenAI with start 2027-01-01. Witness start-after-clock-admitted red by G3-walk (4 own, 0 errors).
- W7C-R1-3: `_launch_paid_checked` calls `costs.month_turn_allowed` again on a fresh `clock()` reading just before each paid launch (the block's trim); a refusal launches nothing, commits that take `failed` with drive_started false (a restart re-drives it, no ruling), and stops blocked naming the hold; no later take of the block is launched. G6 cases: a clock reading 23:29:59 at the gate and 23:30:30 after, for [codex] and [claude, gemini, claude]. Witness launch-recheck-dropped red by G6-clock (7 own, 0 errors). G2's spy now expects two hold calls per paid take (gate, launch).
- W7C-R1-4 not mine (recorded as a CP2 ledger-contract item); the reviewer's "baseline codex, empty ledger lists" probe still PASSes for that reason.
- Red first (tests before code): test_spend_wiring exit 1, 21 ran, 6 failures, 0 errors, all AssertionError (G3, G4, G6 and the three witnesses bound to them). Green: exit 0, 24 ran, 13 of 13 witnesses red, 0 errors; test_batch exit 0 (118); batch.py --check exit 1 on the base's three lines; routing --check 0; copy_manifest and freeze --check 0; import guard holds.
- The reviewer's probe.py re-run on the tree: every money finding now REFUSEs (spend/walks "", {}, None, a non-empty dict, a future start, an int or naive start, a naive clock); the boundary cases are unchanged.

Code commit (review fold): 8b8fe21f on 1dd7e2e9.

RESUME HERE: hand-back for review round 2 at 8b8fe21f

## Review fold W7C-close-2 (round 2: PASS; four cheap items, because this is money)

_Written Mon 12 Oct 2026 (`date`)._
- W7C-R2-1: the ledger reading must be exactly `dict` (a subclass is refused, OrderedDict included) and, from the reviewer's probe2, every key exactly `str` (a key equal to every key, hashing as "walks", is refused). This key-type check goes one step past the ruling's text and is flagged here. G4 cases: ShiftingDict (spend a list at the check and "" after; it ran graded on 0da15d7d) and KeyLike.
- W7C-R2-2: in w7c's own shape check, each spend `usd` must be exactly str, int or float. G4 cases: LyingFloat(300), whose str() says "0" (it ran graded on 0da15d7d), and a bool. costs.py not edited.
- W7C-R2-4: witness stopped-guard-dropped (the `if self.stopped is not None` guard in `_launch_paid_checked`), red by G6-clock (1 own, 0 collateral, 0 errors).
- W7C-R2-3, red-first counts restated: on 1dd7e2e9 the round-1 fold's test file (24 tests) ran 24, 12 failures, 0 errors, G2 included (the reviewer's count). My report said "21 ran, 6 failures" because I ran it before the three witnesses and G2's two-call expectation were added; the 24-test count is the right record.
  This fold, red first on 0da15d7d: 25 ran, 3 failures (G4 and the two witnesses bound to G4, which need G4 green first), 0 errors, all AssertionError.
- Green: test_spend_wiring exit 0 (25 ran, 14 of 14 witnesses red, 0 errors); test_batch exit 0 (118); batch.py --check exit 1 on the base's three lines; routing, copy_manifest and freeze --check exit 0; import guard holds. probe2.py: every subclass/lying case REFUSEs; probe3.py: head 0 bad runs, and the stopped-guard mutant is caught by G6.

Code commit (fold 2): 54772733 on 0da15d7d.

RESUME HERE: w7c closed at 54772733
