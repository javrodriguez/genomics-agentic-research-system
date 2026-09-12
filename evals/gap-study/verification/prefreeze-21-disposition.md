# What was done with review 21

Review 21 (`prefreeze-21.md`) read `prereg-draft.json` at sha256
`e17cc55efbd557839325e55160e547f3c79b8fdecfdd97f8292e44eceafa1c22`, committed at `85c0451`.
It judged the threat model and the thirteen limitations lines first, built a graded take in a clone that passes every committed check, confirmed each of review 20's one-edit routes is refused now, read the seven follow-ups folded or answered as the disposition says, found no route opened by those folds, upheld the six layer verdicts, and ruled **do not freeze** on one defect.

It is folded. All six follow-ups are folded. Nothing is declined.

## Blocker 1 — the order check went red for the rest of the run once a cell exhausted its cap

**The finding.** This one is not a way to move a label or a count, and it moves neither. It is a defect on the path the pre-registration itself prescribes. When a cell reaches its rehearsal cap or its pause cap, the registration command refuses every further take in that cell and the cell publishes short: its remaining slots are never registered. The order check compared the next registration with the permutation's next entry regardless, so from the first exhausted cell onward every later first registration on that axis was reported, the ledger check stayed red for the rest of the run, and the only remedy would have been an amendment to a pinned checker with numbers already on the table. That is the shape a sceptical reader is told to distrust, which is why the reviewer leaned to blocker and why it is folded here rather than noted.

The trigger is not exotic. Three pauses on one slot is a spent weekly allowance retried three times, which a subscription-driven run of 108 takes anticipates. Three rehearsals is one systematic operator-side refusal.

**What was done.** The order check now passes over the unregistered slots of a cell that has reached a cap, the way it already passes over a retry. It reads the per-row attempt kinds the ledger check already computes, so the caps it applies are the pre-registered ones and the counting is the same counting. `take_order_note` says so.

The test carries its own negative control: the same rows with the kinds withheld are still reported, so the skip is what clears them and not the rows. A third case keeps a genuinely out-of-order registration reported.

## The six follow-ups

- **F1 — the cut naming was promised to a reader and printed on a screen.** Limitations line 4 tells a reader that a take published as cut whose last reply ended is named. It was named by the ledger check and by nothing a reader of the published files would meet. Each take's own record now carries `cut_after_end_turn`, with a test and a mutation.
- **F2 — the finish binding could pass having read nothing.** With no assistant record carrying a stop reason, the reading was skipped and the naming never fired. A graded take with an agent turn must now carry one, the same shape as the prompt-snapshot rule.
- **F3 — the cut binding had one mutation for three clauses.** The aborted branch, the no-session clause and the stop-reason requirement each have their own now.
- **F4 — the order note described registration only.** It now states that a row is registered only once every row before it has been attempted, that this makes the registration order the drive order, and that the rule is enforced where rows are written rather than where they are read.
- **F5 — two sentences said more or less than the code.** Limitations line 4 now names what the driver writes for each cut: exit 124 for a timeout, and for an abort either a non-zero exit, the failed then-step the frozen file names, or the no-session clause. And `for_reviewers` now says "a single edited field", with the two-field residual named as what the record reports rather than refuses, so the rule and the code read the same.
- **F6 — a turn row that is not a line on the script was accepted.** The ledger's turn list is a record of the script rather than a list the operator writes at will, and a row whose number is not a line this half sends is refused.

## One defect of my own, found by a test

The runner's loader for the take checker followed a path the tests repoint at a scratch tree, so it raised instead of reading the checker. It loads from beside its own file now. This is the third time that shape has appeared in this study, after the same fix in the registration command and in the driver's attempt routing. It was reproduced before it was fixed, and the traceback named the cause rather than the symptom.

## Verified on these bytes

    python3 evals/gap-study/test_harness.py                238 tests, OK
    python3 evals/gap-study/test_harness.py --mutations    98 mutations, every one red when broken, 91 watched green first
    python3 evals/gap-study/lint_language.py evals/gap-study/    clean, 61 inputs, 2 excused lines
    python3 evals/gap-study/costs.py --check               COSTS.md is what the reader writes
    python3 evals/gap-study/check_results.py --ledger      clean
    python3 evals/test_harness.py                          44 tests, OK
    python3 evals/check_results.py --controls --lexicon     clean

No criterion moved.
No take has run.
