# What was done with review 18

Review 18 (`prefreeze-18.md`) read `prereg-draft.json` at sha256
`fe02c71e6aaf65bf7208075fbb13dba8a0d127d96a335dea928f592942e10559`, committed at `dc38c8b`.
It judged the threat model and the thirteen limitations lines first, read Ruling 21's three routes closed for the shapes review 17 wrote down and the seven follow-ups folded as the disposition says, upheld the six layer verdicts, and ruled **do not freeze** on two findings.

Both are folded. All four follow-ups are folded. Nothing is declined.

## Blocker 1 — a field deleted is not a field edited

**The finding.** The fixture block was restored field by field, and only where the ledger still carried a field: the block was touched at all only when it was a dictionary, stage 01's exit was copied from the ledger's own record of what it should be, and a hash was set to the pin only where a hash was there. The checker refuses on exactly the absences that skipped. So deleting a field, or the block, produced a `fixture-binding` refusal the second run could not see as the ledger's doing, and it founded an admissible rehearsal with every committed check clean. Before the freeze that reached the eighteen project-fixture takes; after it, the fold for review 17's F2 would have turned the same deletion into a refusal on every one of the 108.

**What was done.** The block is rebuilt from the half's own spec whether or not the ledger carries it. `_driver_fixture` builds the record the pinned driver writes, from the pre-registration alone: the kind, variant and seed the generators take; for a project fixture, stage 01's exit and its expected exit both set to the exit the frozen file records for that branch; and the hash key the kind uses set to the frozen pin. Every value is one the driver refuses to open a session without.

Review 18's F1 rides here: stage 01's recorded exit was bound to the ledger's own copy of what it should be, so both fields edited together passed. Both now come from the spec.

Tested by `test_a_fixture_field_deleted_is_restored_like_one_edited`, which deletes the block, empties it, and deletes the expected exit and the variant in turn, and by `test_the_driver_fixture_is_built_from_the_spec_alone`, which pins the record per kind. Mutation `a fixture field deleted rather than edited`.

## Blocker 2 — a take the driver cut may not publish as one that finished

**The finding.** `timed-out` and `aborted` are assigned from the ledger's outcome alone, before any grader reads a turn, and the checker read that outcome against the transcript in one place: a completed take needs every scripted line, which a cut at the last scripted turn leaves present. So one edit of one field graded a cut reply as if the turn had finished, and the per-turn exit code the driver writes was read by nothing.

**What was done.** Two readings bind a completed take, one from the driver's own record and one from the transcript, so the edit is a single field by neither route. A take published as complete may not carry a non-zero exit code in its own per-turn record, and its transcript's last reply may not stop short of the end of a turn. The refusal is `outcome-binding`, pre-registered in `rehearsal_reasons` and in `driver_decided_reasons`, so a rehearsal founded on it is refused as a record the pinned driver cannot have written.

The transcript reading is measured, not assumed. Every one of the eleven committed walks ends its last assistant record at the end of a turn, and the one timed-out attempt on record ends at a tool call. `test_every_committed_walk_ends_its_last_reply_at_the_end_of_a_turn` re-derives that fact rather than trusting this sentence.

**One thing worth recording.** The first version of this guard was hollow. Its tests called the reading directly, so the mutation that removes the call site came back green with nothing protecting it. The control-first battery caught it, not a reading of the diff; a test that exercises a function and not its call site leaves the call site unguarded. `test_the_checker_itself_carries_the_refusal` drives the checker end to end, and the mutation goes red.

## The four follow-ups

- **F1 — the project fixture's exit was bound to itself.** Folded into Blocker 1: both fields come from the frozen spec.
- **F2 — limitations line 5 said "after the probe".** The line now says `precondition-refusal` reads its refusal marker anywhere in the transcript, and that on its positive half an agent that says it will carry on and writes nothing is read as having refused.
- **F3 — `--add` frees the slot behind a Blocker 1 rehearsal.** Nothing to change beyond Blocker 1; the slot gate runs the same ledger check, which refuses those attempts now.
- **F4 — the threat model's "each of them named" clause.** It now says the fields are restored whether or not the ledger carries them.

## Verified on these bytes

    python3 evals/gap-study/test_harness.py                223 tests, OK
    python3 evals/gap-study/test_harness.py --mutations    86 mutations, every one red when broken, 79 watched green first
    python3 evals/gap-study/lint_language.py evals/gap-study/    clean, 58 inputs, 2 excused lines
    python3 evals/gap-study/costs.py --check               COSTS.md is what the reader writes
    python3 evals/gap-study/check_results.py --ledger      clean
    python3 evals/test_harness.py                          44 tests, OK
    python3 evals/check_results.py --controls --lexicon     clean

No criterion moved.
No take has run.
