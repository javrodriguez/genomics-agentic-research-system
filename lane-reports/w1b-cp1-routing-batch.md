status: done

# Lane w1b-cp1-routing-batch: report

Branch `gap4/w1b-cp1-routing-batch-fold`, built on `68ec902f63bfbe4a18d07e0f564847531898ff95`.
CP1's routing table as code (`routing.json`, `routing.py`), the take loop (`batch.py`), the closed vocabulary (`graders/labels4.py`) and the agent adapter boundary (`agent_adapter.py`), with their four test files, are built, folded through two review rounds, and green.
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

## Rulings, by whose

- **Javier (owner)**: "gap4 routing: A", typed 17:52:33 EDT on 6 Oct 2026 in glitch-f3's window (recorded in the round 4 plan).
  It let round 3's routing values be read with `git show` at `e2979b3143081824aadea73523ec41af30c1ddb1`, within the keys and line ranges the lane lead named, and copied.
- **glitch-f3** (in-plan rulings, recorded as glitch-f3's, never as the owner's):
  - the rate-limit markers (6 Oct): structured status 429 or type `rate_limit_error`, OR round 3's four text markers in the harness-side error text, word-bounded and case-insensitive;
  - "per profile" means one test per pre-registered pin profile;
  - the silent first-turn timeout (6 Oct, relayed by the gap4 lane lead during this fold): **rehearsal**, withdrawing his earlier acceptance that a timed-out silent first turn is the agent's. His reason, in the row's source: "A silent timeout with no completed agent output can't be told apart from a hung API, CLI or egress using harness records, and round 3 already routes it as rehearsal through no-first-agent-turn. 'A timeout stays the agent's' applies once the agent has produced completed output."
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
| `caps.pause.reruns_per_half_cell` | 3 | prereg.json `pause_cap`; takes.py:280-285 (drive.py:147-148 says a pause is uncapped; the pre-registration and takes.py cap it) |
| `caps.rehearsal.reruns_per_half_cell` | 3 (the plan's "round 3's cap") | prereg.json `rehearsal_cap`; takes.py:286-291 |
| `rate_limit_markers.text` | `rate limit`, `usage limit`, `weekly limit`, `429`, in order, matched by round 3's own bounded search | drive.py:149, 912-919 |
| finalize abort | round 3 graded it `aborted`; the plan re-routes it (rehearsal before the first turn, harness-error after) | drive.py:1408-1409, 1417 |

## Tests and checks (outputs)

Each file run alone with `PYTHONDONTWRITEBYTECODE=1 python3 -W ignore <file>`, each batch of runs after `mac_slot.py light-ok` (and held while it said hold):

```
tests/test_labels4.py         Ran 5 tests    OK
tests/test_agent_adapter.py   Ran 30 tests   OK
tests/test_routing.py         Ran 220 tests  OK   (the mutation sweep inside it has no survivor)
tests/test_batch.py           Ran 69 tests   OK
routing.py --check            routing.json: 20 rows, 3 annotations, sound
batch.py --check              exit 1: "pin_profiles is empty in routing.json (CP5 pre-registers them)",
                              "pin_profiles_status is PENDING in routing.json" (nothing else)
batch.py --states             {"routes": ["graded", "rehearsal", "pause", "harness-error", "aborted"], "batch": ["blocked", "failed"]}
```

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
5. A turn with no init event is an init mismatch; before the first turn it keeps a silent timeout off the rehearsal row, so it is refused for a human.
6. Box-only rows: a watcher fault before the first turn is a rehearsal; a container that died before the first turn is a start failure; a quiescence kill is an event.
7. Records are a closed, type-checked schema: extra or missing keys, wrong types, committed takes, a preflight failure with a turn, and unlisted reasons are refused.
8. An API error with no turn at all is still refused (W1B2-7 dropped only the count rule).
9. `api_errors=None` is refused: the explicit "no API error" is `[]`.
10. Beyond the rehearsal or pause cap the plan names no fate: the slot ends and the loop stops for a human; on a restart that slot is refused (closed), like a final one.
11. A restart waits for the usage window first when any of the last three committed outcomes is a pause.
12. A failed `register` stops the loop with the failing row named in `stopped`; the rows after it in the block stay unregistered.
13. The rehearsal cap's value is also bound to prereg.json's `rehearsal_cap` (the plan says "round 3's cap").
14. The `checks.d` pins-only line goes red on purpose once CP5 fills the pin profiles, so the check is replaced, not forgotten.
15. Every `emitted_at` check reads only check_take.py's reason-id lines and lines 80-95; any other line is dropped unread.

## Open questions

1. **Cap units differ from round 3's.** Round 3 counts the pauses (or rehearsals) in a cell and registers nothing more once the count reaches the cap (takes.py:280-291), publishing the cell `incomplete — mechanical`. `batch.py` counts the re-runs it grants per half-cell, so a half-cell can see one pause or rehearsal more than round 3 allowed before the loop stops, and it stops for a human instead of publishing the cell incomplete. Which reading the plan's "round 3's cap" and "under round 3's pause_cap" mean is a ruling for the lane lead or glitch-f3.
2. **A silent timeout with no init event is refused, not rehearsed** (the row's `none_of`). A hung CLI that never printed its init event would stop the loop for a human. Keep, or let a missing init (not a differing one) rehearse?
3. **`no-first-agent-turn` against round 4's phase.** Round 3 emits it when "the transcript holds no agent text"; round 4's phase starts with any completed agent message, a tool call included. A first turn of tool calls only would carry it after the first turn, which routing now refuses (W1B2-8). CP2's checker copy must align the two, or such takes block.
4. **A registration with no committed outcome** (a crash between `register` and `commit_records`) is not in the outcome history, so a restart would register that attempt number again. CP5's `takes.py` (round 3 refuses to register while a row is registered and not yet attempted, takes.py:268-272) must refuse or reconcile it.
5. The restart's wait after a pause relies on CP2's `wait_reset()` returning once the window has reset, rather than waiting a full window again.
6. Still open from the cloud build: the tie rule (decision 2) against the plan's "refuses a double match at equal precedence"; CP5's at-most-three-open-rows rule in `takes.py`; `graders/` has no `__init__.py` (imported as a namespace package).
7. CP6 walk check named in `rate_limit_markers_status`: replay a real recorded usage-limit refusal through `harness_records` and see it route pause.

## Lessons worth keeping

- A mutation run over the fold's own guards found one that no test could fail (the phase consistency check): every scenario was consistent by construction. Bind a consistency check with a record that violates it in each direction.
- A rule that widens one phase (3fcab58d) silently re-routes every row of the other phase that the new case touches; the seam needs a variant for every kind of turn the new rule reads.
- Caps that live only in memory reset on every restart; rebuild them from what was committed, and refuse history that cannot be trusted rather than reading it as empty.
