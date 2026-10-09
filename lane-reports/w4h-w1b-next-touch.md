status: done

# Lane w4h-w1b-next-touch: w1b's next touch and CP2 ruling C3

Written Thu 8 Oct 2026, 18:37 EDT, by the lane's builder (opus-medium).
Branch `gap4/w4h-w1b-next-touch`, base `48f10056` (gap4/wave3-merge).
Nothing was pushed or merged, and no model ran.
No reviewer was spawned (the lane lead's process rule, relayed mid-lane).

## Fold

**The C3 names and row ids (fixed; the CP2 lanes build against them):**

- Box key and record key `unreadable_consequential` (in `agent_adapter.BOX_KEYS` and `routing.RECORD_SCHEMA`): a list of run-tree paths (non-empty strings), from the sidecar reply's field of the same name.
  Row id `unreadable-consequential-path`: phase `after-first-turn`, route `harness-error`, matching `nonempty`.
  Before the first turn a non-empty list is refused by `routing.check_records` (the take is `blocked`); CP2 folds that case into `preflight_ok: false`.
- Box key and record key `quiescence_cap_survivors`: an int >= 0, the processes still alive at the quiescence cap (W2A2-6).
  Row id `quiescence-cap-reached`: phase `after-first-turn`, route `harness-error`, matching `> 0`.
  `operator-diff-unexplained-after-first-turn` gains `none_of: [quiescence_cap_survivors > 0]`, so a take with survivors reads exactly `rows == ["quiescence-cap-reached"]`.
  The `quiescence_kill` key and its annotation are unchanged.
- `harness_records` copies both keys as given; `check_records` type-checks both, and refuses None or a wrong type without coercing it.

**Other names CP2 needs:**

- Routing pin: `{"harness", "model", "permission_mode", "version"}` (`routing.PIN_KEYS`). Init events still carry only the plan's three fields.
- `pin_profiles` is keyed `{<harness>: {<model>: {permission_mode, version}}}`. It is still `{}` and PENDING (CP5).
- Registered rows require `agent: {"harness", "version"}` (`batch.AGENT_KEYS`).
- `rate_limit_markers` is keyed `{<harness>: {status, type, text, reset_wait, source}}`.
  Claude Code's entry has the base's values exactly and `reset_wait: null`, which CP2's `wait_reset` must read.
- `spend_cap_markers` is keyed `{<harness>: {status, type, text, source}}`, and `spend_cap_markers_status` is a top-level key.
- `spend_cap_refusal` (id `spend-cap-reached`) is a closed rule: `when: any`, `outranked_by: []`, conditions `in_spend_cap_markers` on `api_errors.status|type|text`.
- The D8 entries go into these shapes with their adapters.

## Inventory as verified at 48f10056

All five items were open, as the lane lead read them, at the lines named in the brief:

- `agent_adapter.py:126-127` had no `isfinite` check.
- `tests/test_routing.py:1769` had `TAKES: ((268, 292),)`, while `batch.py:104` quotes `:260`.
- `batch.py:351-357` used a `history` argument as given.
- `routing.json:8-13` held a flat `rate_limit_markers` and no spend key.
- `PLAN_PIN_FIELDS` and `expected_pin` were keyed by model alone.

None was dropped.
`takes.py:260` at e2979b31 reads `f"or a pause; there are no retakes.")` (lines 255-295 read with `git show`).
`drive.py:140-160` at e2979b31 states no reset wait: line 146 is `FINALIZE_WAIT_S = 180` (stage 00's finalize wait) and line 149 is `RATE_LIMIT_MARKERS`.
`test_batch.py`'s "5 references" are all `rate_limit_markers_status`, so none needed re-keying.

## What was built (commits, red first)

| Item | Red | Green | Mutants asserted red (in the committed tests) |
|---|---|---|---|
| 2 `_clock` isfinite | 109a52e0 | dc6ab5f5 | `_clock` without isfinite |
| 3 fence and the :260 quote | 59dc19e5 | f6d941ef | the quote's line shifted to 261; the fence narrowed back to 268-292 |
| 4 history argument | a8b3f076 | a81194e0 | the comparison dropped (`history_difference` returning None) |
| 5 agent on the pin and the rows | e7cea099 | 4d3c6ab4 | `expected_pin` by model alone; agent not required; version check dropped; profile lookup ignoring the harness; PIN_KEYS without harness; init events allowed to carry the harness |
| 1 spend cap, markers per harness | 4e2cce97 | 9d6815b2, 9e20ef1e | refusal outranked by pause; refusal in one phase only; refusal removed; each fake-second spend type dropped; markers not keyed by harness; unknown harness let through; start gate ignoring the PENDING spend status |
| C3 (a), (b) | 4cede0eb | 514c3b68, 3778bef8 | every C3 row's route, removal and condition, and the operator-diff row's new none_of (through the plan's oracle in the mutation sweep); the before-first-turn refusals dropped |

The lane's files are 109a52e0 through eb071835 (the checks file and the copy-record fragment).

## Every test and check run, with the runner's counts (final head eb071835, 18:36 EDT)

Each run was gated on `mac_slot.py light-ok` (on a hold it waited), used single-threaded BLAS, and ran in the foreground:

- `tests/test_agent_adapter.py`: Ran 35, OK. (Base: 31.)
- `tests/test_routing.py`: Ran 274, OK.
- `tests/test_batch.py`: Ran 110, OK. (Base: 102.)
- `tests/test_endstate.py`: Ran 64, OK.
- `tests/test_labels4.py`: OK.
- `routing.py --check`: `routing.json: 22 rows, 3 annotations, sound`.
- `copy_manifest.py --check` (after `git add`): `ok: 107 files from 8 fragment(s) ... 8 frozen paths unchanged since 68ec902f63bf`.
- The edited last line of `checks.d/w1b-cp1-routing-batch.txt`, run from the worktree with absolute paths: exit 0. The old line on the same head exits 1.
- Red runs before each fix: item 2, 33 ran with 1 failure; item 3, 14 ran with 3 failures; item 4, 1 ran with 1 failure; item 5, 3 ran with 3 failures (routing) and 1 with 1 (batch); item 1, 23 ran with 9 errors (routing) and 1 with 1 failure (batch); C3, 4 ran with 2 failures and 1 error (routing) and 1 with 1 failure (adapter).
- Not run (whole suites are athena's): `test_round4.py`, `run_checks.py`, and `tests/run_tests.py`.

## Edits to existing test code, per test (each is fixture-only or accessor-only unless marked DEVIATION)

`tests/test_endstate.py`, under ruling 1 of 17:42:

- Fixture (lines 182-206):
  - `TEST_PIN` gains `"harness": CC`.
  - `pin_profiles` nests under `CC`, as `{CC: {TEST_PIN["model"]: {...}}}`.
  - The box gains `"unreadable_consequential": [], "quiescence_cap_survivors": 0`.
- The named assertion (now lines 343-351), in `test_a_write_after_the_end_rides_the_operator_diff_row_and_names_its_own_cause`:
  - It was `self.assertEqual(route_result(e)["rows"], ["operator-diff-unexplained-after-first-turn"])`.
  - It is now `self.assertEqual(route_result(e, box_extra={"quiescence_cap_survivors": 1})["rows"], ["quiescence-cap-reached"])`.
  - Its comment now explains W2A2-6 and C3.
  - The test's name is unchanged.

`tests/test_agent_adapter.py`:

- Fixture: `BOX` gains both C3 keys; `BOX_LANDS` gains both, each landing at its own top-level record.

`tests/test_batch.py`:

- Fixture:
  - `PROFILES` nests under `HARNESS = hb.CLAUDE_CODE`.
  - `PIN` and `OTHER_PIN` gain `harness`.
  - `test_table()` sets `spend_cap_markers_status` to a TEST-ONLY value.
  - `_box` gains both C3 keys.
  - `FakeDriver.drive`'s pin reads `row["agent"]["harness"]`.
  - `rows()` and `row()` gain `agent` through a new helper, `agent_of(model)`. A model with no profile gets a made-up version, so the row is still refused on its model.
  - A `harness_bookkeeping` import is added.
- **DEVIATION (commit 9e20ef1e, kept on its own):** `TestStartGate.test_check_cli_exits_1_while_pending` asserted that every `--check` line names `pin_profiles`. It now allows `pin_profiles` or `spend_cap_markers_status`, the same allowance ruling 3 made for the checks-file line. Without it, the PENDING spend status, which the brief requires, turns this assertion red.

`tests/test_routing.py`:

- Fixture:
  - `TEST_PROFILES` nests under `TEST_HARNESS = hb.CLAUDE_CODE`, and `PIN` gains `harness`.
  - New `INIT_FIELDS`, `init_of(pin)` and `INIT` build an init event from the pin's three fields.
  - The direct records' init events now use `init_of`/`INIT` in place of `dict(pin)`/`dict(PIN, ...)`: `baseline`, `silent_turn`, `apply_witness` (differs), `_mismatch`, `pin_refusal_grid_problems`, `_multi_turn`, `_differs`, scenarios at former lines 885/893/895/898/938-940, and `profile_problems`.
  - The loop that builds the `TestProfiles` tests iterates `TEST_PROFILES[TEST_HARNESS]`.
  - `baseline` and `full_box` gain both C3 keys.
  - New imports: `harness_bookkeeping` and `transcript_view`.
- Accessor-only (ruling 3 of 17:42): `table["rate_limit_markers"][k]` became `[...][TEST_HARNESS][k]` at former lines 192, 735, 1177, 1181, 1185, 1188, 1556, 1562, 1565, 1787, 1788, 1801, 2018, 2026 and 2114. The mutation sweep's skip also covers `reset_wait`, which is not a marker list.
  - `TestNextTouchSpendCap.test_the_rekeyed_claude_code_values_are_the_old_flat_ones` reads the base's flat entry from `48f10056` with `git show` and asserts that status, type and text are equal and that the old source is a prefix of the new one.
- Helper addition: `apply_witness` gains a witness for `nonempty` on `unreadable_consequential`. Without it, the derived grid could not build a witness for the new row.
- Fence: `TestRound3Sources.ALLOWED[TAKES]` widens from 268-292 to 255-295 (item 3, as the brief prescribes).
- **DEVIATION (commit 3778bef8, kept on its own):** `TestRecordKeys.test_leaf_list_covers_the_schema` pinned the number of count leaves at 5. C3's `quiescence_cap_survivors` is a sixth, so the 5 is now 6. The alternative, giving the leaf a different type description to keep it out of `COUNT_LEAVES`, would have kept the count-confusion check off the new leaf, so I did not take it.

## Corrections to w1b's lane report (that record is not edited)

- The round 3 fence: w1b's report and the test said `takes.py` 268-292, but `batch.py` quotes `:260`, and the fold read 255-295.
  The fence is now 255-295, and the `:260` quote is bound in `TestRound3Sources`.
- `agent_adapter.py`'s docstring line "Graders read it" is unchanged here; interface 8 leaves that correction to CP2.

## Decisions (this lane's own)

1. A row whose `agent.version` differs from its pin's version is refused before it is registered (`BatchConfigError`), so nothing is driven.
   The brief says it "is blocked".
   I made it a start refusal because a `_route`-time check would also block the existing `TrustingBatch` mutant and turn `TestPins.test_pin_check_can_fail`'s assertion green-to-red.
   It is also stricter, since nothing runs.
2. `quiescence_cap_survivors > 0` before the agent's first turn is refused, as C3 does for a non-empty unreadable list (default-deny).
3. The spend-cap lists and the refusal also match `status`, so Google's HTTP 402 has a place when D8 lands.
   Claude Code's status list is empty.
4. `check_table` makes the spend-cap and rate-limit markers of the same harness disjoint (status, type and text), so a spend cap can never also be a rate limit.
5. There is no adapter table in `agent_adapter.py` at the base (only the base class and `ScriptedAdapter`).
   The "every harness key is a registered name" test checks against the seam's tables `harness_bookkeeping.TABLE` and `transcript_view.PARSERS`. A test-only table may add `fake-second`.
   `routing.py` cannot import the seam (the w1b checks forbid it), so at run time an unknown harness is refused through the table itself: a pin whose harness has no markers, spend list or profile.
6. The spend refusal's id is `spend-cap-reached`.
7. `reset_wait` must be null or a finite positive number.

## Claude Code's spend-cap list: open (PENDING, glitch-f3)

Source read: https://platform.claude.com/docs/en/api/errors (fetched 8 Oct 2026; docs.claude.com redirects there).

- The candidate is `402 billing_error`: "There's an issue with your billing or payment information."
- **Finding for glitch-f3's ruling:** the same page says `429 rate_limit_error` is also returned when the organization "reached its usage tier's monthly spend cap, or reached a spend limit on the Claude Code workspace". It adds: "A tier spend-cap 429 has no retry-after header and keeps failing until access resumes".
  An org or workspace spend limit returns `400 invalid_request_error`.
  So for Claude Code, a spend cap can arrive with exactly the structured fields the rate-limit row pauses on, and no type tells it apart.
- Nothing was added. Arm A runs on a subscription login (D4 A), and the list waits for the ruling.

## Open questions for the lane lead

1. Ratify or revert the two DEVIATION commits (9e20ef1e, 3778bef8). Each is one assertion, and each is the forced consequence of a ruled change.
2. Ratify decision 1, a version mismatch refused at start instead of blocked.
3. When CP2 adds a real adapter table to `agent_adapter.py`, should the registered-names test switch to it?
4. The finding above: Claude Code's spend caps can share `429 rate_limit_error`. Does glitch-f3 want a CP2 signal (for example, a missing retry-after) carried in the API-error record?

## Deferred to Javier

- The spend caps themselves ($400 total; OpenAI $260, Google $140) and the vendor keys, due Fri 23 Oct. No cap value, key name or vendor host was written.

## Lessons worth keeping

- A second guard can hide a mutant. Item 1's markers check also refuses an unknown harness, so the item 5 profile mutant needed a table that has fake-second's markers and no profile before it could go red.
- Adding a scenario dict after the per-scenario test loop still reaches the mutation sweep through `scenario_problems`, but it creates no per-scenario tests of its own.
- An existing "count of leaves" pin turns every new record key into an assertion change. A future brief that adds a key should name that assertion.

## Fold 1 (lane review round 1)

Written Thu 8 Oct 2026, 20:40 EDT.
Source: `scratchpad/w4-review/w4h_r1_findings.md`.
The decisions are the lane lead's, except W4H1-1's extension to all four status lines, which is glitch-f3's ruling under Javier's delegation (relayed by the lane lead).
Commits, in order: 00047846 (red), 397c7ce0 (fixes), eb6127e6 (red, the sibling status lines), 17873120 (the sibling fix), then this section.

Every mutant below was proved red by one whole-file swap of the source file in the worktree.
Each swap was gated by light-ok, ran the whole test file, and was restored byte for byte, checked by comparison.

| Finding | Severity | Fix | Test | Mutant (whole-file run) |
|---|---|---|---|---|
| W4H1-5 | MAJOR | test entries only | `test_the_lists_are_checked`: a spend status that is no int ("402"), and a rate-limit status that is no int ("429") | M23 (the status-int clause off): test_routing, Ran 276, FAILED (failures=1), test_the_lists_are_checked |
| W4H1-6 | MAJOR | test entry only | `test_the_lists_are_checked`: an infinite reset_wait | R35 (isfinite dropped): Ran 276, FAILED (failures=1), test_the_lists_are_checked |
| W4H1-7 | MINOR | the "names no marker" clause kept, with a comment that it is a backstop | `test_the_lists_are_checked`: an empty rate-limit status list | R42 (nonempty=False): Ran 276, FAILED (failures=1), test_the_lists_are_checked |
| W4H1-8 | NIT | test entries only | `test_the_lists_are_checked`: a markers entry with an empty source; `test_the_refusal_is_a_closed_rule`: a spend condition on ledger.end | R43: Ran 276, FAILED (failures=1), test_the_lists_are_checked. R38: Ran 276, FAILED (failures=1), test_the_refusal_is_a_closed_rule |
| W4H1-2 | NIT | `route()` checks the spend refusal unconditionally | `TestNextTouchFold1`: a hand-built table whose refusal is outranked by pause still refuses every spend case; plus an in-memory mutant test | the outranked_by gate put back: Ran 276, FAILED (failures=1), test_the_spend_refusal_ignores_outranked_by |
| W4H1-1 | MINOR | `batch.is_pending(status)` strips and upper-cases before the PENDING test, on all four status lines | `TestNextTouchFold1Gate` (spend); `TestNextTouchFold1Siblings` (one test per sibling line); plus an in-memory mutant test for each | prefix rule back on each line, test_batch, Ran 116, FAILED (failures=1) for each: the spend line (Ran 112 at the time), operator_reasons_status, pin_profiles_status and rate_limit_markers_status, each failing only its own test |
| W4H1-3 | NIT | none; carried to CP2 | | |
| W4H1-4 | NIT | none needed | | |
| W4H1-9 | NIT | none; carried to CP2 | | |

**W4H1-3, carried to CP2.** A Claude Code spend-cap 429 is `rate_limit_error` with no retry-after header, and it routes pause today. The PENDING gate keeps the batch from starting. The API-error record may need a retry-after-present signal before Claude Code's list is ruled.
Correction to the report above, from the review: the page says org and workspace spend limits return 400 `invalid_request_error`, "except limits on the Claude Code workspace, which can return a 429 instead".

**W4H1-9, carried to CP2.** The sidecar owns `unreadable_consequential`'s source, and with it whether an absolute path or a ".." segment is refused.

**W4H1-4, no change needed.** test_routing holds the survivors=0 path; the review's M11 is red there.

**Own-test change.** `test_spend_check_can_fail`'s first case, the refusal put below pause in a hand-built table, no longer pauses now that W4H1-2 is fixed. Its assertion was removed, and `TestNextTouchFold1` holds that case as a refusal.

**Gates on head 17873120**, all run before 20:45 EDT:
- test_routing: Ran 276, OK.
- test_batch: Ran 116, OK.
- test_agent_adapter: Ran 35, OK.
- test_endstate: Ran 64, OK.
- test_pause_adherence: Ran 30, OK.
- `routing.py --check`: "22 rows, 3 annotations, sound".
- `copy_manifest.py --check`: "ok: 107 files from 8 fragment(s)".

## Fold 2 (lane review round 2: PASS, no MAJOR)

Written Thu 8 Oct 2026, about 20:55 EDT, while the Mac hold was on. **Gates are pending the lift:** none of this fold's commits has been run.
The decisions are the lane lead's.
Commits: 2217cada (red tests), 163ea719 (the fix and the prose), then this section.

| Finding | Severity | Decision | Fix | Test and mutants |
|---|---|---|---|---|
| W4H2-1 | MINOR | fold: an allow-list | `batch.is_pending` returns True unless the status, stripped and upper-cased, starts with `RULED` or `FILLED` (`RULED_WORDS`) and holds no `PENDING` anywhere. All four start_problems status lines use it (glitch-f3's W4H1-1 ruling). | `TestNextTouchFold2Gate`. On each of the four keys, the reviewer's cases are pending: a zero-width space before PENDING, a BOM before it, `'PENDING'`, `Status: PENDING`, `RULED for codex; PENDING for claude-code`, `TBD`, `not yet ruled`. Pending too: `FILLED, pending a re-read`, the empty string, and `TEST-ONLY: ...`. Ruled: `RULED ...`, `FILLED ...`, `  ruled (test-only)`, `Filled`. Two committed mutants, one per rule half: the prefix alone (the composite D8 string starts the loop) and PENDING-anywhere alone (`TBD` and `not yet ruled` start it). |
| W4H2-3 | NIT | fold | The batch.py START GATE prose and the is_pending docstring say the new rule, with no double negative. In routing.json, line 17's sentence and the spend source and status sentences (lines 23 and 26) are rewritten. No test pins those sentences. | text only |
| W4H2-2 | NIT | left | spend_cap_holds still reads `when` at run time. check_table refuses such a table. | none |
| W4H2-4 | NIT | left | Each line's own guard is shown by the per-line whole-file swaps (w4h_swaps2.py). | none |

**One change that is not prose.** `rate_limit_markers_status` had said "batch.py refuses to start while this status starts with PENDING". Under the new rule, a status holding PENDING anywhere is not ruled, so that sentence would have kept the loop from starting on the ruled rate-limit markers. It is reworded without the word PENDING.

**Fixture change, test_batch.py `test_table()`.** `pin_profiles_status` and `spend_cap_markers_status` change from "TEST-ONLY: ..." (now pending) to "RULED (TEST-ONLY): ...". Every test that starts the loop through `test_table()` needs this: TestTerminalStates, TestPins, TestCaps, TestRestart and the rest, and `test_check_cli_exits_1_while_pending`'s "ready" half. No assertion changed.

**Still to run after the lift:**
- the four lane test files, each alone;
- test_pause_adherence;
- `routing.py --check`;
- `copy_manifest.py --check`;
- one whole-file swap per new mutant: the RULED-prefix half dropped, and the no-PENDING half dropped.
