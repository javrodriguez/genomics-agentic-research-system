Status: needs-review

ROUND 3 SUMMARY FOR REVIEW (cloud executor, 2026-10-19 16:46 EDT; glitch-26's rulings B19-12 to B19-17 on REVIEW-vendor-b19-27249de.md):
- Red (B19-14): b18ebbb5, TestNightlyCarrier.test_a_refused_wave_leaves_no_carrier_on_an_uncommitted_row in tests/test_batch_rolling.py, red at 756686f9 in both subtests:
  - money gate refusal: "AssertionError: (5, 1) not found in [(1, 1), (2, 1), (3, 1)] : the nightly stop's carrier names a row never committed";
  - register failure: "AssertionError: (4, 1) not found in [(1, 1), (2, 1), (3, 1)] : the nightly stop's carrier names a row never committed".
- Green (B19-14): 4c5b663d. batch.py's fill sets the carrier after the wave's launches; a refused or unregistered wave leaves the carrier on the last take launched before it (slot 3 carries the stop).
- B19-12: 80fd6788, green on batch.py (the code was right; the holds were unpinned). TestHoldsBehindASlowHead, slot 1 ten times slower, three checks returning problems:
  - stop-hold: slot 2 ends blocked, failed or leaking behind the slow head (slot 3 ends after it): no registration after slot 2's drive end, the loop stops;
  - nightly-hold: slots 2, 3 and 4 end harness-errors behind it, slot 4's reaching NIGHTLY_HARNESS_ERRORS while slot 5 still runs: no registration after slot 4's drive end, and the stop is carried by slot 5, the last take launched;
  - closing-hold: slots 2, 3 and 4 of hc-b rehearse behind it, slot 4's the third (the cap): no hc-b row registered between slot 4's drive end and its commit; hc-b closes and slot 7 is dropped. A pause behind the slow head is not a separate check: any finished pause already holds every launch (test_batch's pause test), so the closing hold cannot be told apart for a pause.
  - Witnesses (TestWitnesses, batch.py compiled in memory with one edit set, bound check green on the tree first), each run alone, each red: held-stops-dropped (stop-hold, 3 problems), held-nightly-dropped (nightly-hold, 1), held-pause-only-stops (the review's pause-only mutant; stop-hold, 3), held-pause-only-nightly (the same mutant; nightly-hold, 1), closing-cells-empty (closing-hold, 2). Each problem is the registration the hold forbids.
- B19-13: a5032928 (fakes) and c936f8ca (the note).
  - World.wait_wave and EqualRepo wait until every future in the loop's open deque is done; no settle sleep is left. World finds the committing loop on the thread's stack; EqualRepo is handed the loop.
  - That alone was not enough: in a loop of runs the nightly scenario still registered slot 5 once, because a reading saw a non-head drive of the wave finished before its head, with no commit between, and filled a lane (the rolling design, as the review says). So TimedDriver, when equal, ends a wave's other drives only once the head's commit has begun, as World already did.
  - TestEqualDurations: 60 runs in a loop, 60 green. The tie-rule mutant (while to if in the commit step) still turns both scenarios red. test_batch: 118 tests in about 4 s (was 64 s), 7 of 7 runs green.
  - Note: section 2 and the Rulings line for B19-6 reworded as ruled. Section 3's opening sentence restated the old claim ("always means the block run is reproduced exactly"), so it now points at the same definition (in the final lane commit).
- B19-15: a6325f36. The drain's docstring (the throwaway queue; a re-run decided while draining is owed by the restart from the history, W1B3-6); run() resets the count of queued re-runs; prose reworded in takes.py's guard_registration docstring, costs.py line 13 and test_batch.py's header comment. Kept, as the review says: outside_live_block, drive.py's TakeRepo docstring and the money gate's refusal text.
- B19-16 (NIT 7), recorded: no test yet runs the production TakeDriver and TakeRepo with a launch overlapping another take's drive. The first run that does will be the run driver's rehearsal walk on athena, which is planned for the freeze rehearsal.
- B19-17 (NIT 8), recorded as ruled: under B19-6, publication counts a ruled pause as its own event, so for a history with a ruled pause the published per-half-cell count can differ from the block-era reading. The equivalence scenarios hold no ruling. Nothing changed.
- Checks (foreground, env -i with PATH, HOME, LANG, TMPDIR from mktemp -d outside the clone), every gap-study-4 test module importing batch.py, takes.py or check_results.py, all OK:
  - test_batch 118, test_batch_rolling 36 (was 26), test_box_integration 61, test_build_draft 49, test_checker_body 30, test_cp6_wiring 5, test_drive_commit 31;
  - test_drive_loop 27, test_drive_ownership 44, test_executed_turn_refusal 10, test_native_snapshot 15, test_night_ruling_history 4, test_nightly_stop 13;
  - test_pending_walk 23, test_pin_for_vendor 2, test_pipeline 85, test_routing 297, test_spend_wiring 25, test_vendor_checker_road 5, test_vendor_pins 5;
  - test_walk_builders 95, test_walk_layout 14, test_walk_runner 89, test_walk_wiring 20, test_walk_launch 49 (29 skipped by its own REAL_SCAN_SKIP class, as before; no skip added);
  - the five witnesses, each run alone: red, as listed above;
  - copy_manifest --check ok (489 files from 60 fragments); build_draft --check ok; lint_language and lint_pooling on evals/gap-study-4/ clean, and with --commits-since 756686f9 clean.
- For glitch-26:
  - tests/mutations/run.py does not exist on this branch, on main or anywhere in the history. The witnesses follow test_spend_wiring's pattern instead: they are registered in test_batch_rolling's WITNESSES and run one at a time through unittest, by naming each witness test.
  - No COPIED.d change: no file was added (test_batch_rolling.py was already claimed in round 2).
  - TimedDriver.wait_idle is now unused; it is left in place.

RESUME HERE: review stop (round 3)

ROUND 2 SUMMARY FOR REVIEW (cloud executor, 2026-10-19 15:34 EDT; glitch-26's rulings B19-5 to B19-11):
- Red (ruling B19-8, B19-9; B19-6's comparison is green on the block loop by design): 22838d85, tests/test_batch_rolling.py now 26 tests, 13 red on 94963ea7, run on a scratch copy of 94963ea7 outside the clone. Failure lines:
  - the 3 round 1 rolling-start tests, as in round 1 ("24 not less than 13", "18 not less than 13", "[] is not true");
  - TestWindowSpan.test_a_rolling_event_spanning_more_than_a_block_is_accepted: "['window event 1 does not fit one block of at most 3 consecutive outcomes'] != []";
  - TestWindowSpan.test_a_rolling_run_shares_one_event_across_the_takes_committed_between: slots 6 and 7 commit window event 2, not 1;
  - TestRuledPauseOwnEvent.test_publication_counts_the_ruled_pause_as_batch_does: "Items in the second set but not the first" (publication shares the block's event);
  - TestLiveSet.test_max_open_is_the_open_row_limit: "None != 12";
  - TestLiveSet.test_a_registration_lands_while_other_rows_are_open: "ValueError: a row is registered with no committed outcome in the finishing block";
  - TestLiveSet.test_twelve_open_and_never_thirteen: "ValueError: at most 3 open rows (three in one live block)";
  - TestCleanTreeRegistration.test_an_open_takes_folder_does_not_refuse_the_next_registration: "ValueError: registration requires a clean committed repository";
  - TestOpenBound.test_open_takes_reach_max_open_and_no_more: "3 != 12";
  - TestRestartOwesTheOpenTakes.test_the_stop_commits_twelve_open_takes_and_the_restart_owes_them_in_row_order: "3 != 12";
  - TestRestartOwesTheOpenTakes.test_the_old_block_span_forgets_the_wait: "restart_waits does not read the last MAX_OPEN outcomes".
- Green (B19-5, B19-8): f477832f. batch.py: MAX_OPEN = 12 beside BLOCK = 3; the rolling loop (commit the oldest finished take first and every finished take before a lane fills; a wave per fill through the money gate, registration in row order and launch; holds read from finished drives: pause, blocked, failed, a leak, the nightly count in prospect, a closing half-cell; one reading of finished drives for the holds and the free lanes); the window event as the pauses between two waits; restart_waits over the last MAX_OPEN outcomes; the nightly stop carried by the last take launched; a register failure commits the open takes first; prose re-worded. takes.py: OPEN_LIMIT = MAX_OPEN, the live set loses a row at its commit, clean-tree registration but for the live set's untracked takes/<slot>/<attempt>/ folders. check_results.py: at most BLOCK pauses within at most MAX_OPEN outcomes per event; pause_event counts a ruled pause as its own event, with STRICT_PAUSE_NOTE when another pause of its half-cell carries a window event (B19-6).
- Tests re-pinned in f477832f, for glitch-26 to check none is loosened:
  - test_batch.py: its fakes model equal durations (World: a wave's drives end together, its head first; a commit waits until no drive is in flight, then SETTLE = 0.05 s; a drive's wave read at its launch); without that the block-shaped tests went red at random (11, then 6, failures). test_commits_land_serially_in_row_order (finish_after, unequal) checks row order over the run with a new rolling_order_problems, plus two can-fail mutations; the restart_waits mutants re-anchored on [-MAX_OPEN:]. 118 tests, about 64 s (was 13 s).
  - test_pipeline.py: test_partly_finished_live_set_allows_another_registration, test_live_set_max_open_restart_requires_reconciliation and test_past_max_open_mutant (were the finishing-block, three-open and four-open tests); test_ruled_pause_counts_as_its_own_event (was ..._its_existing_block_once); test_new_slot_after_legal_pause_ruling_uses_batch_count and test_strict_batch_close_is_named_in_completeness_and_result now see publication close c1 as batch does (the strict-close label still checked on the former block reading, patched in). Mutants finishing-block (restores the block rule), past-max-open (was four-open), pause-count-refusal, pause-event-identity and pause-note-other-cell (was pause-candidate-edges) re-anchored; each run with --mutant goes red (also pause-block and window-span).
  - test_spend_wiring.py: witnesses gate-never-called and gate-after-register re-anchored on the wave; both still red.
- B19-7: 996e767a. routing.json's pause-cap source prose reworded; build_draft.py run, --check ok. routing.json sha256 eccbb54d7bee09d3c10688c12bd33e9bee28b0e8b29c412c77f32a26d55f0c9b -> e69f468e94fd283defda9a7d535eced3b502be29f6363c46d4908c2754e43387; prereg-draft.json sha256 1a1aa53f37960a54fba61baedee7426bcf9c8f409d98709de70be0cd69a3a0d5 -> 0aed2a2cd124266d2464f8d5d4a9181a66c81ddc56230ca8287859144b0257ae.
- B19-10: d8b9d8b9, tests/test_batch_rolling.py claimed in COPIED.d/vendor-admission.json (where vendor-b14 and vendor-b16 claimed theirs). copy_manifest.py has no rule asking Javier's word for a claim (its one such line, 100, is the native-readers acceptance records), so no BLOCKED.
- B19-6 and B19-11: 7cac1d4f, the note's 5.3 sentence and its section 10, Rulings.
- Checks (foreground, env -i with PATH, HOME, LANG, TMPDIR outside the clone), every gap-study-4 test module importing batch.py, takes.py or check_results.py, all OK:
  - test_batch 118, test_batch_rolling 26, test_box_integration 61, test_build_draft 49, test_checker_body 30, test_cp6_wiring 5, test_drive_commit 31;
  - test_drive_loop 27, test_drive_ownership 44, test_executed_turn_refusal 10, test_native_snapshot 15, test_night_ruling_history 4, test_nightly_stop 13;
  - test_pending_walk 23, test_pin_for_vendor 2, test_pipeline 85, test_routing 297, test_spend_wiring 25, test_vendor_checker_road 5, test_vendor_pins 5;
  - test_walk_builders 95, test_walk_layout 14, test_walk_runner 89, test_walk_wiring 20, test_walk_launch 49 (29 skipped by its own REAL_SCAN_SKIP class, the battery's one allowed skip; no skip added);
  - copy_manifest --check ok (489 files); build_draft --check ok; lint_language and lint_pooling on evals/gap-study-4/: clean; check_vendor_sources P2 on the edited files: none is a reader source.
- For glitch-26:
  - lint_language --commits-since 94963ea7 names two commit-body words, which this round may not amend: "100" in d8b9d8b9 (copy_manifest's line number) and "free" in f477832f ("the free lanes"). lint_pooling over the same commits is clean.
  - Prose naming the block outside the three files is left: costs.py line 13 and drive.py's TakeRepo docstring (note 5.4). No departure entries were written in the owning COPIED.d fragments of batch.py, takes.py, check_results.py and the three re-pinned tests.
  - Equal durations reproduce the block run only under the fakes' equal model (a settle of 0.05 s): with real drives an equal end is a tie in time, and the loop fills a lane as soon as any drive's step is seen finished.

RESUME HERE: review stop (round 2)

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
- 2026-10-19 15:21 EDT: routing.json's pause-cap prose and the rebuilt draft 996e767a (ruling B19-7).
- 2026-10-19 15:22 EDT: COPIED.d claim d8b9d8b9 (ruling B19-10); the note's Rulings section 7cac1d4f (rulings B19-6, B19-11).
- 2026-10-19 15:34 EDT: checks done (round 2 summary above); status needs-review; review stop.
- 2026-10-19 16:10 EDT: round 3 begins on lane/vendor-b19 at 756686f9 under glitch-26's rulings B19-12 to B19-17 on REVIEW-vendor-b19-27249de.md; status running.
- 2026-10-19 16:16 EDT: red test b18ebbb5 (ruling B19-14): TestNightlyCarrier, red in both subtests at 756686f9.
- 2026-10-19 16:18 EDT: green 4c5b663d (ruling B19-14): the carrier is set once the wave is launched.
- 2026-10-19 16:20 EDT: 80fd6788 (ruling B19-12): TestHoldsBehindASlowHead (3 checks) and TestWitnesses (5 witnesses, each red alone).
- 2026-10-19 16:28 EDT: a5032928 and c936f8ca (ruling B19-13): the equal model waits on the loop's open futures, its head first; TestEqualDurations 60 of 60 green; the note reworded.
- 2026-10-19 16:29 EDT: a6325f36 (ruling B19-15): drain docstring, run resets the front count, prose.
- 2026-10-19 16:46 EDT: rulings B19-16 and B19-17 recorded; checks done (round 3 summary above); status needs-review; review stop.
