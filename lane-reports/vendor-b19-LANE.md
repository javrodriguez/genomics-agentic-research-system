Status: running

ROUND 1 SUMMARY FOR REVIEW (cloud executor, 2026-10-19 13:56 EDT; glitch-26's rulings B19-1 to B19-4):
- The note (ruling B19-2): lane-reports/B19-DESIGN-NOTE.md (23761cd5), beside batch.py's other design notes (nightly-stop-rule, w1b-cp1-routing-batch, w7c-spend-wiring, B14, B16) and outside evals/gap-study-4/, whose every file is claimed in COPIED.d and bound into the freeze's study tree.
- The proposal: at most BLOCK = 3 drives in flight. The loop commits the oldest open take whenever its drive has finished, then fills the free lanes as one wave (the money gate, registration in row order, then each launch, all three unchanged), and waits for any drive to finish. Tie rule: every drive already finished is committed before a lane is filled, so with equal durations every wave is a block and the history is the block run's, byte for byte. A pause, a stop, a prospective nightly count or a half-cell about to close at the queue's head is read from the finished step's routed state and holds new launches at once; the fate is still decided at the commit.
- The behaviours it lists (each with its line, the rolling behaviour, and what it can move):
  - the block itself (251, 584, 913, 920);
  - the money gate (915, 946-976), now once per wave;
  - registration and a register failure (986-1002);
  - commits in row order and the re-run requeue (926-931);
  - the window events that share one reset (W1B3-5; 925, 1006-1007, 1104-1109, 1222, 1273), now a new event after each wait instead of each block;
  - restart_waits over the last BLOCK outcomes (320-326, 789), now over the last MAX_OPEN;
  - the nightly stop carried by the block's last row (914, 1081-1094), now carried by the last open take;
  - stops for blocked, failed and a leak (1009-1013, 1276-1280);
  - the cap and closed-cell drops (906, 934-944, 1214-1225);
  - the ledger and history records: the same keys and doors, and every replay unchanged.
- Found outside batch.py (each refuses a rolling registration as written):
  - takes.OPEN_LIMIT = BLOCK and RegistrationGuard's finishing-block rule (takes.py 43, 259-264, 292-298);
  - commit_registration's clean-tree check (takes.py 372-373), since an open take's folder takes/<slot>/<k>/ is in the tree;
  - check_results.window_problems' BLOCK span (84-98), which publication calls, and pause_event's block edges (101-150).
- MAX_OPEN: a model of the 1,260 takes (arithmetic only, no drive) gives about 52 h in blocks, 45 h rolling with three open takes, and 29 h with 12 open or with no bound. The note proposes 12.
- The re-rulings it proposes, each with a wording for glitch-26 (note section 7):
  - (1) W7C-gap4-1: the gate runs per wave;
  - (2) W1B3-5's wording: an event is the pauses between two waits;
  - (3) lane w1b decision 11 as bound by W1B3-3: the last MAX_OPEN outcomes;
  - (4) the nightly stop's carrier;
  - (5) glitch-f3's cap ruling: "of the same block" becomes "open", plus the head-of-queue hold;
  - (6) takes.py's open-row rule and clean-tree registration, with MAX_OPEN's value;
  - (7) check_results' window span and the ruled pause counted as its own event; this is the only proposal that can change a published count;
  - (8) routing.json's pause-cap source prose: reword it (the draft's routing sha moves) or leave its bytes.
- Pre-registered elements: no prereg.json yet. routing.json's bytes (bound by sha in prereg-draft.json) are unchanged by the proposal. The change must land before the freeze rehearsal (freeze.py study_tree_sha).
- Red tests (ruling B19-3), evals/gap-study-4/tests/test_batch_rolling.py (cf74278a), stub drives on the scripted adapter, slot 1 ten times slower. 11 tests, 3 red on 7dc0cf9e:
  - TestRollingStart.test_the_next_row_starts_before_the_slow_drive_ends: "AssertionError: 24 not less than 13 : slot 4's drive starts only after slot 1's slow drive ends: the block waits for its slowest"
  - TestRollingStart.test_both_freed_slots_are_filled_while_the_slow_drive_runs: "AssertionError: 18 not less than 13 : slot 4 is registered only after slot 1 ends"
  - TestRollingStart.test_three_drives_run_beside_the_slow_one_after_its_block_mates_end: "AssertionError: [] is not true : no third drive runs beside slot 1 once slots 2 and 3 have ended"
  - Green and pinned: at most three drives at once; commits in row order (a finished drive waits for an older row); registrations in row order, each before its launch, never overlapping a commit; a re-run is the next registration after its commit; the equal-duration equivalence on two scenarios (re-runs, a shared pause and an abort; the nightly stop on the wave's last row), compared with the block run's trace read from 7dc0cf9e, plus a check that the comparison can fail.
- Batch.py is unchanged (ruling B19-4).
- Checks, each run under env -i (PATH, HOME, LANG, TMPDIR outside the clone), on every gap-study-4 test module that imports batch.py. All OK except the new module (3 failures, above):
  - test_batch 118, test_routing 297, test_nightly_stop 13, test_night_ruling_history 4, test_spend_wiring 25;
  - test_cp6_wiring 5, test_drive_commit 31, test_drive_ownership 44, test_executed_turn_refusal 10, test_native_snapshot 15;
  - test_pin_for_vendor 2, test_vendor_checker_road 5, test_vendor_pins 5, test_drive_loop 27;
  - test_pipeline 85, test_walk_builders 95, test_walk_wiring 20, test_box_integration 61.
  - lint_language and lint_pooling: clean.
- For glitch-26:
  - copy_manifest --check names tests/test_batch_rolling.py as unclaimed. The B16 claim was made on the owner's word, so this round wrote no claim.
  - The red module keeps test_round4's discovered battery red until the green lands.

Goal: the measured run's take loop (evals/gap-study-4/batch.py) moves from fixed blocks of three drives to a rolling window of at most three drives, with registration and commits still serial and in row order, so that slow Gemini-arm drives no longer hold two finished slots idle; round 1 is design and red tests only.

Plan:
- Round 1 (rulings B19-1 to B19-4): a design note listing every block-dependent behaviour of batch.py, with its source line, the proposed rolling behaviour, what it can move, and the re-rulings it needs; red tests against stub drives; no change to batch.py; the checks; then stop for glitch-26's rulings.

RESUME HERE: rulings stop (round 1)

Clock: 2026-10-19 13:39 EDT (lane vendor-b19, cloud executor, branch from lane/vendor-admission at 7dc0cf9e).

Progress:
- 2026-10-19 13:39 EDT: branch lane/vendor-b19 created at 7dc0cf9e (rev-parse verified); round 1 under glitch-26's rulings B19-1 (the goal), B19-2 (the design note), B19-3 (red tests) and B19-4 (batch.py unchanged).
- 2026-10-19 13:51 EDT: red tests cf74278a (ruling B19-3): tests/test_batch_rolling.py, 11 tests, 3 red on 7dc0cf9e (the rolling start), 8 green (row order, the bound, the requeue, the equal-duration equivalence); batch.py unchanged (ruling B19-4).
- 2026-10-19 13:51 EDT: design note 23761cd5 (ruling B19-2): lane-reports/B19-DESIGN-NOTE.md.
- 2026-10-19 13:56 EDT: checks done (summary above); status needs-review; rulings stop.
- 2026-10-19 14:18 EDT: round 2 begins on lane/vendor-b19 at 94963ea7 under glitch-26's rulings B19-5 to B19-11; status running.
- 2026-10-19 15:02 EDT: red tests 22838d85 (rulings B19-6, B19-8, B19-9): tests/test_batch_rolling.py now 26 tests, 13 red on 94963ea7 (the 3 rolling-start tests of round 1 and 10 new), run on a scratch copy of 94963ea7 outside the clone.
- 2026-10-19 15:20 EDT: green f477832f (rulings B19-5, B19-8): batch.py's rolling loop, takes.py's live set and clean-tree registration, check_results' window span and ruled pause; test_batch_rolling 26 of 26 green; test_batch, test_pipeline and test_spend_wiring re-pinned (see the round 2 summary).
