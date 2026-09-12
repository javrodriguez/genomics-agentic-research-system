# What was done with review 20

Review 20 (`prefreeze-20.md`) read `prereg-draft.json` at sha256
`0b72a9f562965556eeb1f031e4e1d398fe8e566c28665efbd9671597b802b344`, committed at `9b06498`.
It judged the threat model and the thirteen limitations lines first, read Ruling 23's three blockers closed in the code and not only in a test, read its four follow-ups folded as the disposition says, upheld the six layer verdicts, and ruled **do not freeze** on one defect.

It is folded. All seven follow-ups are folded or answered. Nothing is declined.

## Blocker 1 — the outcome binding read one way

**The finding.** Ruling 23 bound a completed take to the driver's record: a non-zero exit code forces an outcome that says the take was cut, and a completed take must end its last reply at the end of a turn. A cut outcome forced nothing. So one edit of `outcome` on a finished take, to `timed-out` or to `aborted — …`, published a behavioural failure as a failure of the harness, with every exit code still zero, the checker valid and the ledger check clean. The same edit through the `no session file` clause did it with a transcript sitting beside the ledger.

This is review 15's first blocker in the other reserved label. `holds` does not move, because both labels count against it, but the published record is the per-cell label list: a cell reading "one timed-out" tells a reader the model would have held but for the budget, where "one invented" tells them it did not.

**What was done.** The cut direction is bound to the driver's own record. A take published as `timed-out` must carry exit 124 on its last turn row, which is what the driver writes on the turn it cut. A take published as `aborted` must carry a non-zero exit on that row, or a failed pre-registered then-step, or the no-session-file clause. And that clause must not sit beside a transcript, because the driver appends it only when it found none.

**The residual, named rather than hidden.** A legitimate cut can land after the agent's last reply has ended, so the transcript cannot refute a claimed cut the way it refutes a claimed finish. Editing the outcome and the last row's exit together is therefore a two-field edit the checks cannot separate from a real cut. The ledger check now names every take published as cut whose last reply ends at the end of a turn, the way it already names every graded take with no transcript, and limitations line 4 says so.

## The seven follow-ups

- **F1 — the generated builder did not refuse before the session.** The carried and copied builders refuse a fixture that differs from their pin before a session opens; this one recorded the hash and left the mismatch to the checker, where it becomes a refusal no record can clear. It refuses now, for symmetry.
- **F2 — the reason id described less than it refuses.** `outcome-binding` now names every case: an outcome off the driver's vocabulary, a turn row with no exit code, a completed take that was cut, and a cut take with no cut behind it. That one line is what a reader of a discarded attempt's note is given.
- **F3 — two claims in `probe_located_by` were wrong, and one was mine.** The carried grader's window starting inside the first operator turn's tool loop is a property of that grader, true in the first study's own committed transcripts, not a consequence of this protocol's recoveries; and the classifier puts a denial above an assertion, so a negated sentence anywhere in the window outranks a later assertion. The label can be lost, not only diluted. Both now say so. The grader is carried verbatim and is not changed for this.
- **F4 — the order bound registration and not driving.** Every row could have been registered first and driven in any order afterwards, and nothing a reader can check would show it. A row is registered only once every committed row before it has been attempted, so the registration order is the drive order.
- **F5 — the freeze could pin a generated fixture by nothing.** It wrote `UNPINNED` into the frozen file and let every take on that task be refused afterwards, which is an amendment where a refusal at the freeze is a retry. It refuses now. This one carries no guard: hosting it needs a scratch repository with git history, a committed review report, every pinned file and a generator that fails, which is a fixture larger than the change. That is recorded in the battery's own not-applicable list rather than left unsaid.
- **F6 — the harness's synthetic model id was published as a model a cell was read under.** The checker and the driver both exclude the harness's own API-error record; this published field did not, and now does.
- **F7 — the pause channel.** The reviewer weighed it as a stated limitation rather than a defect, because a pause is a fabricated coherent record with a published cost: capped at three per cell, counted, and described in limitations line 3. Left as it stands, as the reviewer recommends.

## One thing about the battery

Adding F4's rule made an existing mutation's setup impossible: it registered three takes with nothing driven, which no real run can do. The battery reported its control as red before the mutation rather than passing it, and the setup now leaves the attempt record the driver leaves. A control that goes red on a rule change is the battery working.

## Verified on these bytes

    python3 evals/gap-study/test_harness.py                232 tests, OK
    python3 evals/gap-study/test_harness.py --mutations    92 mutations, every one red when broken, 85 watched green first
    python3 evals/gap-study/lint_language.py evals/gap-study/    clean, 60 inputs, 2 excused lines
    python3 evals/gap-study/costs.py --check               COSTS.md is what the reader writes
    python3 evals/gap-study/check_results.py --ledger      clean
    python3 evals/test_harness.py                          44 tests, OK
    python3 evals/check_results.py --controls --lexicon     clean

No criterion moved.
No take has run.
