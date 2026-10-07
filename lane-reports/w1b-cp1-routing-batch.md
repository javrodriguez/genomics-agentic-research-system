status: done

# Lane w1b-cp1-routing-batch: report

Branch `gap4/w1b-cp1-routing-batch-fold`, built on `68ec902f63bfbe4a18d07e0f564847531898ff95`.
CP1's routing table as code (`routing.json`, `routing.py`), the take loop (`batch.py`), the closed vocabulary (`graders/labels4.py`) and the agent adapter boundary (`agent_adapter.py`), with their four test files, are built, folded through two review rounds and glitch-f3's three rulings of 6 Oct 2026 (fold 3), and green.
This report replaces the cloud build's report (its `status: blocked` was cleared when the owner's routing ruling let round 3's values be read and filled).
Nothing here was pushed or merged by this lane.

## How the lane got here

1. **Cloud build** (`0988c72e`..`cde79889`): the five modules and their tests.
   A classifier denied the cloud session's first read of round 3's files; the lane did not route around it, left round 3's operator reasons and pause cap PENDING, and reported `blocked`.
2. **Review round 1 fold** (fresh claude-opus-5-5; `a00079c1`, `c8fede6a`, `693cec8b`):
   - W1B-1: outside reach and quiescence kill became annotations, decided on every take whatever route wins; every outcome carries mask and events; unreadable records mask fail-closed.
   - W1B-2: every box record required and never coerced; every record leaf type-checked.
   - W1B-3: a failing take never loses its siblings; every take of a block is committed in row order.
   - W1B-4: every API error of a take is read.
   - W1B-5: the agent's first turn starts with completed agent output (the gap4 lane lead's ruling).
   - W1B-6, W1B-7: more oracle scenarios and mutants; the turn ends live in labels4.
   - W1B-8: the fate is decided before the commit and committed with the record.
   - W1B-9, W1B-10: the start gate refuses pending data; a take's pin must be its registered model's pre-registered profile.
3. **The owner's routing ruling** (`49ecfedd` red, `032afca5` filled): under Javier's "gap4 routing: A", round 3's operator-side reasons and pause cap were read with `git show` at `e2979b31` and copied (below).
4. **glitch-f3's rate-limit marker ruling** (`0a964eec` red, `a84d67c8`): structured status/type OR round 3's four text markers, on the harness-side error text only.
   `3fcab58d` (the lane lead's refinement of W1B-5: any timed-out turn starts the agent's turn) also landed here; review round 2 reverted it.
5. **Review round 2 fold** (fresh claude-opus-5-5 on `3fcab58d`: CHANGES, 4 MAJOR; this fold, `2b81d1be`..the report commit):

| Finding | What changed | Test (red first for the MAJORs) | Mutant that turns it red |
|---|---|---|---|
| W1B2-1 MAJOR | Phase back to "completed agent output" in `harness_records` and in routing's consistency check. New row `silent-timeout-before-first-turn` (before-first-turn, `any_of ledger.end eq timed-out`, `none_of` init differs from the pin), route **rehearsal** per glitch-f3's correction; one value in `routing.json`; at rehearsal's level, so every before-first-turn harness row agrees with it. The W1B-5 row's source now states the rule. | `TestSilentTimeout` (both ways, through `harness_records`); oracle scenarios for the review's four probe cases plus the bare timeout, a timeout after output, and two consistency refusals; seam variant "a silent timed-out turn"; `first_turn_problems` in `test_agent_adapter.py` | 3fcab58d's rule restored (adapter and routing); the consistency check dropped; the row's phase widened to any or its route set to graded; a timed-out turn's output never read; the routing mutation sweep over the new row |
| W1B2-2 MAJOR | Annotation `checker-event-reason` (event, mask) when `checker_reasons` carry an id of `checker_reasons_become_events`; `check_table` refuses an event id in `operator_reasons`; `routing.py`'s docstring says what `events.outside_reach` counts; `batch.py` seals every outcome at one commit road (`_seal`): every blocked and failed take is masked fail-closed. | oracle scenarios (each id, both phases); annotation grid; `test_checker_event_reason_masked_on_every_terminal_state` (3 ids x 7 terminal states, through the loop); `test_every_blocked_and_failed_outcome_is_masked` (eight roads to blocked or failed) | `in_checker_events` never holds; the annotation removed; `_seal` removed; each event id dropped from the list; an event id added to `operator_reasons` |
| W1B2-3 MAJOR | `Batch` reads `repo.history()` (or a `history` argument read from it) and rebuilds the re-runs spent per half-cell and per slot, each slot's next attempt and the closed slots; it refuses a final or capped slot, a slot under another half-cell, and untrustworthy history (not a list, a missing key, an unknown state, a slot and attempt twice, two half-cells, an attempt after the final one). | `TestRestart`: stop, restart, no extra re-run (per-slot and per-half-cell harness-error caps, final and capped slots refused, a moved slot refused); a restart after a pause waits; untrustworthy history refused | history never replayed or never checked; re-runs, attempts, closed slots or half-cells forgotten; the pause forgotten; a repo without `history()` read as empty |
| W1B2-4 MAJOR | `TurnResult`'s `init`, `api_errors` and `counters` are required keywords; omission raises `TypeError` naming the field; `init=None` stays legal. | `TestRequiredKeywords` | the requirement switched off; counters defaulted to no rise |
| W1B2-5 | A `register()` failure commits every row of the block already registered as `failed` (masked, nothing launched), sets `stopped`, returns; a `wait_reset()` failure sets `stopped` and returns. | `TestRepoAndWindowFailures` (fails on slot 2, on slot 1, on the window; a restart continues) | errors propagate; registered rows left uncommitted |
| W1B2-6 | `rate_limit_markers_status` = RULED (glitch-f3, 6 Oct; names the CP6 walk check); gated in `start_problems`, required by `check_table`. | gate cases PENDING and missing; `test_rate_limit_markers_status_is_ruled` | the gate ignores it; `check_table` stops requiring it |
| W1B2-7 | `TurnResult.api_errors`, a list, replaces `api_error`; `harness_records` flattens them in order; routing no longer refuses more API errors than turns. | a 529 then a 429 in one turn pauses (record level, both phases, and through `harness_records`); order kept | one API error per turn; the old count refusal restored |
| W1B2-8 | `reasons_only_before_first_turn` = `no-first-agent-turn`; routing refuses records carrying it after the agent's first turn started. | four scenarios; `test_no_first_agent_turn_after_the_first_turn_is_refused` | the refusal dropped; the id swapped for another reason (sweep) |
| W1B2-9 | This report; the `checks.d` comment and the pause-cap comment in `test_batch.py` refreshed (the batch tests now run on the real pause cap and operator reasons, no test-only overrides). | | |
| W1B2-10 | `driver_decided_reasons` (six ids) copied with their source and why no rule of their own is needed; `check_table` requires them, and `reasons_only_before_first_turn`, to be operator reasons, and the event ids to be disjoint from them. | `TestRound3Sources.test_driver_decided_reasons_are_round_3s`, `test_every_emitted_at_line_carries_its_id` (every cited line emits its id, every reason-id line is cited); `test_operator_reasons_and_event_ids_are_disjoint`; `test_driver_decided_reasons_route_by_the_generic_rule` | a cited line shifted, dropped, or moved off the constant; an event id put into `operator_reasons`; an id outside `operator_reasons` |
| W1B2-11 | `caps.pause` quotes drive.py:147-148 and records prereg.json's `pause_cap` = 3 applied per cell by takes.py:280-285; `caps.rehearsal` records `rehearsal_cap` = 3 (takes.py:286-291); both finalize-abort rows record round 3's own treatment (graded `aborted`, drive.py:1408-1409, 1417) beside the plan's re-route. | every quote checked against round 3's file at `e2979b31` | (the quotes are bound to the files: a changed quote or line fails) |

6. **glitch-f3's three rulings** (in-plan, 6 Oct 2026, relayed by the gap4 lane lead; recorded as glitch-f3's, never as the owner's), on open questions 1, 2 and 5 (fold 3: `8514eb7c` red tests, `1319d31d` the fix, `fae0f9cb` the mutants, then this report):

| Ruling | What changed | Test (red first) | Mutant that turns it red |
|---|---|---|---|
| 1. Cap units match round 3 | Rehearsals and pauses are counted per half-cell, round 3's unit: round 3's cell (task, half, model) is round 4's half-cell (arm, task, half, model), the registered row's `half_cell`, with wording and repeat or pressure as the slot inside it. The batch's counter was already keyed by that half-cell (kept); what it counted changed, from the re-runs it granted to every committed rehearsal (or pause) of the half-cell, the take reaching the cap included. That take is its slot's last (final, `beyond_cap`, never re-run) and its own committed record carries `cell_state` = `labels4.INCOMPLETE_MECHANICAL` (new in labels4, with `CELL_STATES`) and a `cell_reason`; nothing more is registered for the half-cell (queued rows and re-runs dropped, listed in `skipped`); the loop goes on and never stops for a human there. A restart closes half-cells from the committed state and refuses history whose cell state disagrees with the counts. Harness-error's caps and beyond-cap fate are unchanged. Both cap sources in `routing.json` state the ruled unit. | `TestCellCaps` through `Batch.run` with the fake driver (one at a time, three at once, and a restart from the repo's history, for pause and rehearsal); the pause-cap, rehearsal-cap, fate and restart tests now expect the ruled fate; history cases for the cell state; `test_cap_units_are_glitch_f3s_ruling`; `test_incomplete_mechanical_is_round_3s_cell_state`; `test_the_cell_state_is_never_retyped`. Red on the old loop: a fourth attempt registered, the loop stopped for a human, no cell state committed, a restart refused the capped slot, the block re-ran all three. | the old stop for a human; the old per-half-cell count (re-runs granted); the state closed in memory only; a closed half-cell's queued rows kept; the closed half-cells forgotten on a restart; the pre-ruling refusal of the capped slot on a restart; the cell-history walk or the field check off; the closed-cell branch dropped, or without the window; a failed commit keeping the state; the unit sentence dropped from a cap source; the word retyped or out of the vocabulary |
| 2. A missing init on a silent timeout rehearses | New op `present_differs_from_pin` (an init event that is there and differs from the pin). The silent-timeout row's `none_of` uses it, so before the first turn a silent timed-out turn with no init event rehearses, and one whose init names another model, mode or version matches no row and is refused for a human. No tie: the row is before-first-turn and `init-mismatch` after-first-turn, so the two never meet (asserted: the matched rows are the silent-timeout row alone). After the first turn a missing init stays a mismatch (`differs_from_pin`, decision 5). The row's source and `init-mismatch`'s source state it. | `test_missing_init_rehearses_a_differing_init_is_refused` through `harness_records` and `route` (three missing-init cases rehearse; model, mode, version and a mixed case are refused); four oracle scenarios. Red on the old table: every missing-init case matched no row. | (a) the old `none_of` (`differs_from_pin`); (b) the `none_of` dropped, and the new op blind to a difference; the routing mutation sweep's new-op mutant (back to `differs_from_pin`) |
| 3. The `wait_reset` contract, written down | `batch.py`'s THE USAGE WINDOW: `wait_reset()` returns promptly when the usage window has already reset, blocks until it resets otherwise, raises on failure, and the loop then stops as `failed` (W1B2-5). Written in `batch.py`, where the loop's driver, repo and window interface is documented (`agent_adapter.py` holds the agent adapter, not the window). No loop change was needed. | `test_contract_is_written` (red: not written); `test_restart_after_a_pause_waits_once_or_stops_failed`: a restart after a pause calls `wait_reset()` once and goes on when the fake reports the window already reset, and a raising `wait_reset()` stops it `failed` with nothing new registered, launched or committed. The two loop tests passed on the old loop, which already behaved so (W1B2-5, decision 11). | each clause dropped from the docstring; a restart that forgets the pause; a loop waiting before every block; the window's error escaping the loop; a window failure read as a reset |

A source-mutation sweep over fold 3's guards (29 mutants over `batch.py`, `routing.py`, `routing.json` and `labels4.py`, each applied to a scratch copy of `evals/gap-study-4` and run against its test file) turned every one red; none survived.
Transparency: a tree-wide `git grep` run while preparing fold 3 printed matching lines of round 3's files outside the range this fold may read (`evals/gap-study-3/run.py`, `prereg.json`, `prereg-draft.json` and `review_kit/prefreeze-4.md`, for the strings `incomplete — mechanical` and `reruns_per_half_cell`).
None of them was used: every round 3 value this fold relies on comes from `takes.py:260-295` at `e2979b31` and the brief.

## Rulings, by whose

- **Javier (owner)**: "gap4 routing: A", typed 17:52:33 EDT on 6 Oct 2026 in glitch-f3's window (recorded in the round 4 plan).
  It let round 3's routing values be read with `git show` at `e2979b3143081824aadea73523ec41af30c1ddb1`, within the keys and line ranges the lane lead named, and copied.
- **glitch-f3** (in-plan rulings, recorded as glitch-f3's, never as the owner's):
  - the rate-limit markers (6 Oct): structured status 429 or type `rate_limit_error`, OR round 3's four text markers in the harness-side error text, word-bounded and case-insensitive;
  - "per profile" means one test per pre-registered pin profile;
  - the silent first-turn timeout (6 Oct, relayed by the gap4 lane lead during this fold): **rehearsal**, withdrawing his earlier acceptance that a timed-out silent first turn is the agent's. His reason, in the row's source: "A silent timeout with no completed agent output can't be told apart from a hung API, CLI or egress using harness records, and round 3 already routes it as rehearsal through no-first-agent-turn. 'A timeout stays the agent's' applies once the agent has produced completed output."
  - fold 3 (6 Oct, relayed by the gap4 lane lead in the fold-3 brief), on open questions 1, 2 and 5:
    - **cap units match round 3**: pauses and rehearsals counted per cell, the unit round 3 used (takes.py:280-291 at `e2979b31`); at the cap `batch.py` stops registering that cell and records it `incomplete — mechanical`, never stopping the loop for a human; other cells go on; harness-error's own cap and beyond-cap fate unchanged; the cell's state committed, rebuilt on a restart; the word lives in labels4;
    - **a missing init on a silent timeout routes rehearsal; a differing init is refused**: "A CLI that never printed its init event is harness-side, by the same reason as W1B2-1";
    - **the `wait_reset` contract**: returns promptly when the usage window has already reset, blocks until it resets otherwise, raises on failure, and `batch` then stops as `failed` per W1B2-5.
- **gap4 lane lead** (in-spec, under glitch-f3's delegation): the W1B-5 phase rule (completed agent output); the 3fcab58d refinement (reverted by W1B2-1); the round 2 brief's shape for the silent-timeout row (its own row, `none_of` init differs from the pin, the route one value in `routing.json`); the interfaces pinned for all lanes.

## Round 3's values in `routing.json`, and how each is bound

All read with `git show e2979b31:<path>` only, within: prereg.json's keys `rehearsal_reasons`, `driver_decided_reasons`, `pause_cap`, `rehearsal_cap`; check_take.py's reason-id lines and lines 80-95; drive.py lines 140-160, 857-923 and 1405-1420; takes.py lines 268-292.
`tests/test_routing.py` `TestRound3Sources` re-derives every one, reading only those ranges (its `round3_lines` refuses any other).

| Value | Copied | Source |
|---|---|---|
| `operator_reasons` | round 3's 24 `rehearsal_reasons`, less the three the plan makes events: 21 ids, each with file, commit, key, meaning and emitting lines | prereg.json; check_take.py |
| `checker_reasons_become_events` | `study-materials-reached`, `account-email`, `read-outside-the-checkout` | plan CP2; check_take.py:1682, 714, 1691 |
| `driver_decided_reasons` | `environment-record`, `invocation`, `outcome-binding`, `project-name`, `script-not-a-list`, `session-binding` (each also an operator reason, so routed by the generic rows) | prereg.json |
| `reasons_only_before_first_turn` | `no-first-agent-turn` | check_take.py:83; its prereg.json meaning |
| `caps.pause.events_per_half_cell` | 3, the half-cell's count of pauses (round 3's unit, glitch-f3's ruling; renamed by his call) | prereg.json `pause_cap`; takes.py:280-285 (drive.py:147-148 says a pause is uncapped; the pre-registration and takes.py cap it) |
| `caps.rehearsal.events_per_half_cell` | 3 (the plan's "round 3's cap"), the half-cell's count of rehearsals (round 3's unit, glitch-f3's ruling) | prereg.json `rehearsal_cap`; takes.py:286-291 |
| `rate_limit_markers.text` | `rate limit`, `usage limit`, `weekly limit`, `429`, in order, matched by round 3's own bounded search | drive.py:149, 912-919 |
| finalize abort | round 3 graded it `aborted`; the plan re-routes it (rehearsal before the first turn, harness-error after) | drive.py:1408-1409, 1417 |

## Tests and checks (outputs)

Each file run alone with `PYTHONDONTWRITEBYTECODE=1 python3 -W ignore <file>`, each batch of runs after `mac_slot.py light-ok` (and held while it said hold):

```
tests/test_labels4.py         Ran 7 tests    OK
tests/test_agent_adapter.py   Ran 30 tests   OK
tests/test_routing.py         Ran 228 tests  OK   (the mutation sweep inside it has no survivor)
tests/test_batch.py           Ran 83 tests   OK
routing.py --check            routing.json: 20 rows, 3 annotations, sound
batch.py --check              exit 1: "pin_profiles is empty in routing.json (CP5 pre-registers them)",
                              "pin_profiles_status is PENDING in routing.json" (nothing else)
batch.py --states             {"routes": ["graded", "rehearsal", "pause", "harness-error", "aborted"], "batch": ["blocked", "failed"]}
```

- Fold 3's red tests (`8514eb7c`) ran red for the right reasons before the fix: labels4 had no cell state; on the old table every silent first-turn timeout with no init event matched no row (and the purity and cap checks crashed on that refused oracle scenario); on the old loop a half-cell's slot met its route four times, a fourth attempt was registered, the loop stopped for a human with the other half-cell unrun, no cell state was committed, a restart refused the capped slot, and three slots meeting the route at once were all re-run; the `wait_reset` contract was not written. The two `wait_reset` loop tests passed on the old loop (its behaviour since W1B2-5 and decision 11); their red comes from their mutants.
- The red tests for the four MAJORs were committed first (`2b81d1be`) and ran red for the right reasons: the bare silent timeout graded and the probe cases routed harness-error; event ids arriving as reasons were committed with mask=False; a restart re-drove slot 1 from attempt 1 (attempts 1 and 2 committed twice, 2 harness-error re-runs past the per-slot cap of 1, 3 past the half-cell cap of 2); omitted counters were accepted.
- The minors' tests were run red before their fixes too (register and window failures raised; the markers' status, `driver_decided_reasons` and the round 3 quotes were missing; two API errors in one turn and no-first-agent-turn after the first turn were mis-routed).
- The review's four probes, repointed at this branch: every silent-timeout case routes rehearsal (a silent timeout with no init event is refused for a human), event ids arriving as reasons are committed blocked with mask=True and the event, and a restart refuses the already final slot.
- An in-memory source mutant for every guard this fold added (20 mutants over `routing.py`, `agent_adapter.py`, `batch.py`) turns at least one test red; the one survivor of the first run (routing's consistency check) got two scenarios and is now killed.
- The review's own eight mutants, rerun on this branch: seven go red. The eighth ("adapter: refinement reverted in harness_records only") is now the identity, since W1B2-1 reverted that refinement. Its first, "fail-closed mask removed", had survived at first because `_seal` also masked unreadable records; the two mask rules now each live in one place (`_annotations` for unreadable records, `_seal` for blocked and failed takes), each with its own test (`test_unreadable_annotations_mask_a_routed_take`, `test_every_blocked_and_failed_outcome_is_masked`) and both mutants are red.
- Every non-test line of `checks.d/w1b-cp1-routing-batch.txt` passes under `/bin/sh` from the repository root; its `batch.py --check` line was shown to fail on a ready table and on a table with another gap.
- The import boundary: `batch.py` and `routing.py` import no driver, Claude Code or adapter (AST test and the `checks.d` grep).
- Not run: `tests/run_tests.py`, `test_round4.py` and `run_checks.py` (the home session runs them on athena on the exact head).

## Decisions (this lane's own)

1. Rehearsal shares harness-error's precedence level (both harness faults, split by phase); a double match between them is refused.
2. A tie is matched rows at the winning level naming different routes; rows naming the same route are one answer, all reported.
3. Graded is a row (`end-turn`, `timed-out`), never a default: an unexplained `error` end is refused.
4. A timed-out turn's exit code is not read by `nonzero-exec-exit` (the host's own kill exits non-zero).
5. After the agent's first turn, a turn with no init event is an init mismatch (`differs_from_pin`). Before it, glitch-f3's ruling (fold 3) applies, not this decision: a silent timeout with no init event rehearses on the silent-timeout row, and one whose init event differs from the pin matches no row and is refused for a human (`present_differs_from_pin`).
6. Box-only rows: a watcher fault before the first turn is a rehearsal; a container that died before the first turn is a start failure; a quiescence kill is an event.
7. Records are a closed, type-checked schema: extra or missing keys, wrong types, committed takes, a preflight failure with a turn, and unlisted reasons are refused.
8. An API error with no turn at all is still refused (W1B2-7 dropped only the count rule).
9. `api_errors=None` is refused: the explicit "no API error" is `[]`.
10. Superseded by glitch-f3's cap ruling (fold 3). It was: beyond the rehearsal or pause cap the plan names no fate, so the slot ends and the loop stops for a human, and on a restart that slot is refused. Now the half-cell closes `incomplete — mechanical` at the cap and the loop goes on (see How the lane got here, 6).
11. A restart waits for the usage window first when any of the last three committed outcomes is a pause; it relies on the `wait_reset()` contract glitch-f3 ruled (fold 3), now written in `batch.py`.
12. A failed `register` stops the loop with the failing row named in `stopped`; the rows after it in the block stay unregistered.
13. The rehearsal cap's value is also bound to prereg.json's `rehearsal_cap` (the plan says "round 3's cap").
14. The `checks.d` pins-only line goes red on purpose once CP5 fills the pin profiles, so the check is replaced, not forgotten.
15. Every `emitted_at` check reads only check_take.py's reason-id lines and lines 80-95; any other line is dropped unread.
16. (fold 3, then glitch-f3's call) For rehearsal and pause the cap key is renamed `events_per_half_cell`: its value counts that route's committed outcomes per half-cell, this one included, so it allows at most cap-1 re-runs. `routing.check_table` refuses the old name `reruns_per_half_cell` there (tested, with a red mutant); harness-error, aborted and graded keep `reruns_per_half_cell`, whose meaning did not change. One accessor, `batch.half_cell_cap`, reads both.
17. (fold 3) The take that brings its half-cell to the cap is committed `final` (its slot's last record), with `beyond_cap` and no `stop`; harness-error beyond its cap was already final.
18. (fold 3) The cell state is two outcome keys, `cell_state` (None or `labels4.INCOMPLETE_MECHANICAL`) and `cell_reason` (the count and the cap). Every outcome of the half-cell committed after it closed carries them too, so a committed record always says its cell's state at commit time.
19. (fold 3) A drive of the same block already running when its half-cell closed is committed as its route says, but never re-run (a harness-error there included, since nothing more may be registered for the cell), and a pause there still holds the next launch for the usage window. A re-run granted earlier in that block to another slot of the half-cell is dropped unregistered; its record keeps `rerun: true` (true when committed), and the closing take's record is why.
20. (fold 3) A restart drops a closed half-cell's rows unregistered, its capped and final slots included, instead of refusing them, so a caller passing the remaining queue is never stopped for a human by a closed cell; a final slot of an open half-cell is still refused.
21. (fold 3) A half-cell closes only by a committed record: when the closing take's commit fails, the take is `failed` with no cell state and the half-cell stays open for the restart to decide from history.
22. (fold 3) A restart refuses history whose cell state disagrees with the counts (the take reaching a cap must carry it, every later take of the half-cell too, no other, and none re-run), and a cell state that is not labels4's or lacks its reason.
23. (fold 3) The `wait_reset()` contract lives in `batch.py`'s docstring (THE USAGE WINDOW) beside the driver, repo and window interface; `agent_adapter.py` is unchanged.

## Open questions

1. **RULED by glitch-f3** (in-plan, 6 Oct 2026; glitch-f3's, not the owner's): cap units match round 3. Was: round 3 counts the pauses (or rehearsals) in a cell and registers nothing more once the count reaches the cap (takes.py:280-291), publishing the cell `incomplete — mechanical`, while `batch.py` counted the re-runs it granted per half-cell and stopped for a human. What changed: `batch.py` counts every committed pause (or rehearsal) of the half-cell, round 4's (arm, task, half, model) for round 3's (task, half, model); the take reaching the cap is committed with the cell state `incomplete — mechanical` (`labels4.INCOMPLETE_MECHANICAL`) and its reason; nothing more is registered for the half-cell; the loop goes on; a restart rebuilds the closure from history (How the lane got here, 6; decisions 16-22).
2. **RULED by glitch-f3** (in-plan, 6 Oct 2026; glitch-f3's, not the owner's): a missing init on a silent timeout routes rehearsal; a differing init is refused. Was: a silent timeout with no init event was refused (the row's `none_of` counted a missing init as a mismatch). What changed: the silent-timeout row's `none_of` is `present_differs_from_pin`, so a missing init rehearses and a differing one is refused for a human, with no tie against `init-mismatch` (decision 5).
3. **`no-first-agent-turn` against round 4's phase.** Round 3 emits it when "the transcript holds no agent text"; round 4's phase starts with any completed agent message, a tool call included. A first turn of tool calls only would carry it after the first turn, which routing now refuses (W1B2-8). CP2's checker copy must align the two, or such takes block.
4. **A registration with no committed outcome** (a crash between `register` and `commit_records`) is not in the outcome history, so a restart would register that attempt number again. CP5's `takes.py` (round 3 refuses to register while a row is registered and not yet attempted, takes.py:268-272) must refuse or reconcile it.
5. **RULED by glitch-f3** (in-plan, 6 Oct 2026; glitch-f3's, not the owner's): the `wait_reset()` contract. Was: the restart's wait after a pause relied on CP2's `wait_reset()` returning once the window has reset, rather than waiting a full window again, and nothing wrote that down. What changed: `batch.py` states the contract (returns promptly when the usage window has already reset; blocks until it resets otherwise; raises on failure, and the loop then stops as `failed` per W1B2-5), and fake-driven tests bind the loop's side of it (decisions 11, 23). CP2's real window must keep it.
6. Still open from the cloud build: the tie rule (decision 2) against the plan's "refuses a double match at equal precedence"; CP5's at-most-three-open-rows rule in `takes.py`; `graders/` has no `__init__.py` (imported as a namespace package).
7. CP6 walk check named in `rate_limit_markers_status`: replay a real recorded usage-limit refusal through `harness_records` and see it route pause.
8. RULED (glitch-f3, 6 Oct 2026): rename the key. Done: `events_per_half_cell` for rehearsal and pause, the old name refused there (decision 16).

## Lessons worth keeping

- A mutation run over the fold's own guards found one that no test could fail (the phase consistency check): every scenario was consistent by construction. Bind a consistency check with a record that violates it in each direction.
- A rule that widens one phase (3fcab58d) silently re-routes every row of the other phase that the new case touches; the seam needs a variant for every kind of turn the new rule reads.
- Caps that live only in memory reset on every restart; rebuild them from what was committed, and refuse history that cannot be trusted rather than reading it as empty.
- (fold 3) A tree-wide grep crosses read fences: it printed lines of round 3's files this lane may not read. Scope every search to the lane's own folders.
- (fold 3) A per-slot refusal on a restart turns a closed cell back into a stop for a human; a cell-level fate is applied where the queue is drawn, not where rows are checked.
