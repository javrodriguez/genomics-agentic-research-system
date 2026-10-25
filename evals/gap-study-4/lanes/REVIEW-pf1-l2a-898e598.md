VERDICT: CHANGES

# Closure review of lane pf1-l2a, head 898e598c (and 77e4aa69)

Reviewer: the same fresh reviewer as REVIEW-pf1-l2a-5afd80a.md, Sat 24 Oct 2026, 20:00-20:03 EDT by `date`.
Read: `git log 5afd80a7..HEAD`, which gives 3ce70d37 (the first review, committed), 898e598c (the fold) and 77e4aa69 (one exact-line allowlist entry for the first review's line 29).
Probes: probe.py again, plus probe2.py, which drives `takes.ruling_door_problems` with stub readers and `takes.driver_refusal_record` against real scratch git repos.
Both are at /private/tmp/claude-501/-Users-javrodher-glitch/5da39513-9adc-4587-8d29-3722641cf776/scratchpad/l2a/.
They ran with python3.12 behind `mac_slot.py light-ok`.
At 77e4aa69, on the Mac:
- test_pf1_routing_rulings: OK.
- test_drive_commit: OK.
- `routing.py --check`: sound, with 21 no-match classes, each with its default.

## The first review's findings, closed

1. **Closed (counter rise).** `cgroup-kill` is no longer in `RERUN_FAULT_ROWS`.
   An out-of-memory rise with an unlisted reason is now refused for both re-run and harness-error (probe 2, 2b, d1).
2. **Closed (the door reads the end state).** `commit_ruling` calls `ruling_door_problems`, which runs `check_results.ruled_rerun_problems` with the real reader (`run.grade_committed`) before anything is written.
   - A re-run with an end state that reads wrong is refused at the door (a3, c4).
   - The real reader imports and fails with ValueError, which reads as wrong and so fails closed (e1).
   - Door and publication call the same function with the same row and table, so they agree on any end state that does not change after the ruling.
   - I found no history that the door passes and publication then refuses.
3. **Closed (no records).** A take that left no records is accepted only as aborted, or as a re-run or rehearsal when the driver's refusal record is present and the end state is clean.
   - Refused: re-run without the record (a1), graded (a5), and a wrong end state (a3).
   - `driver_refusal_record` against real git:
     - The record added in the outcome's own commit is counted (f1).
     - Added in a later commit, copied from s2 in a later commit, edited later, committed with two outcomes at once, or with an empty `refused`: all return None (f2, f3, f6, f5, f7).
4. **Closed (pin block).** A genuine pin block can be re-run on a clean end state (c3), but not on a wrong one (c4).
   A forged pin block, whose pin equals the registered profile, is refused at the door (c1).
5. **Closed (agent_event_rows).** It is now exactly the two ids, and adding a harness-error row or `end-turn` is refused (probe 8, 8b).

## New findings

### 1. MINOR (claim): two parts of the ruling rule are checked at the door only, but the rule says publication checks all of it

`ruling_door_problems` runs only inside `takes.commit_ruling`.
`history_problems` (each restart) and `ruled_rerun_problems` (publication) do not check the refusal-record condition or the forged-pin condition.
- a7: a no-records take with a re-run and no refusal record passes `history_problems`.
- c2: a forged pin block passes `history_problems`.

So a ruling committed into rulings.json without going through the door gets past those two conditions at restart and at publication.
The end-state reading at publication still holds, so a wrong action is never discarded.
The integrity claim is therefore intact, and the stray part is the claim.
The registered text (batch.RULING_RULE, prereg-draft.json ruling_rule) says: "The ruling door (takes.commit_ruling) checks all of this before anything is written, and the publication check refuses the record set again otherwise."
For those two conditions, the second half of that sentence is not true.

Fix, either:
- reword the sentence to say the refusal-record and pin conditions are checked at the door alone; or
- call the pin and refusal checks from `run.produce` too.

The data is there: `produce` holds the rows, and `driver_refusal_record` reads git.

### 2. NIT: a pin block that also leaks its container loses its pin fault

`Batch._drive_step` rewrites the reason of a take whose container removal failed, so it opens with "container ... leaked".
`pin_block` then reads False, and `history_problems` refuses a re-run, because no fault row matches.
The door function alone accepts it (c5).
This is rare, and it fails toward aborted or graded.
Matching the prefix inside "(after: ...)", or keeping the original reason in its own field, would close it.

### 3. NIT (scope note): the guard on the refusal record binds the commit, not who made it

When s2's refusal record is moved into s1's folder inside the commit that appends s1's outcome, it is counted (f4).
That needs a hand-made outcome commit, so it falls under forged outcomes, outside the ruling threat.
The guard refuses every later-commit road (f2, f3, f6), as ruled.

## Not re-checked

- I did not re-run the athena battery.
- I did not drive the 77e4aa69 allowlist entry through `lint_language`.
