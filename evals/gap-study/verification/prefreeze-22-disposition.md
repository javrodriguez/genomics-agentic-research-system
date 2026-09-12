# What was done with review 22

Review 22 (`prefreeze-22.md`) read `prereg-draft.json` at sha256
`01b5a02bb28a4cf87ad8bcb4c54fc7a2782921b800381025e72f8ab8b1d23669`, committed at `ea54bf0`.
It judged the threat model and the thirteen limitations lines first, read review 21's six follow-ups folded as the disposition says, found no route opened by them, upheld the six layer verdicts, and ruled **do not freeze** on one finding.

It is folded. All five follow-ups are folded. Nothing is declined.

## Blocker 1 — the fold was closed in a test and open in the code

**The finding.** Ruling 25 said an exhausted cell's unregistered slots are passed over. The skip exists in `order_problems` and is dead at the one call site that runs it. The ledger check builds a map from row index to attempt kind and hands it to the order check, and between those two lines the per-cell cap loop uses the same name for its target. A `for` target assigns to the function's local, so what arrived was the last cell's per-kind counts, every row index looked up as missing, and the skip never fired. On the prescribed path the ledger check went red for the rest of the run, exactly as review 21 described.

The reviewer reproduced it end to end: thirty-five rows registered by the registration command in the permutation's own order, the fourth slot of the first cell refused at the cap as the rules say, and the next two registrations reported. One rename clears them.

**Why the guard did not catch it.** Every order test called the function directly with a map it built. The ledger check's own fakes report the file unfrozen, so the whole post-freeze branch ran in no end-to-end test. And the mutation edited the function body, which the direct-call tests see, so it went red while the call site was dead. Ruling 22 recorded this exact shape as a lesson two slices earlier, and the fold repeated it.

**What was done.** The loop target is renamed, so nothing shadows the map. A new test drives the ledger check itself, with the file reported frozen, a real permutation and a cell taken to its cap, and asserts clean; a second case keeps a genuinely out-of-order registration reported. And a second mutation blanks the argument at the call site rather than the body, so the wiring is attacked as well as the reading. Review 22's F1 is folded here: that end-to-end case is what was missing.

## The five follow-ups

- **F1 — no test reached the order path through the ledger check.** Folded with the blocker, above.
- **F2 — the ledger check accepted a first registration inside a cell that had already reached a cap.** The registration command refuses it at write time and the read side accepted it, so a row appended by hand there would have been graded and counted. The order check reports it now: a rule enforced only where rows are written is not in the record.
- **F3 — the cut count stopped at the results file.** Each take's record carried it and the comparison a reader is shown did not. The analysis counts it per model and prints it beside the cell.
- **F4 — the threat model said more than the checks read.** It now says a hand edit to the fields of a take ledger's row that a check reads, naming them, and that a row's other fields are read by nothing and decide no label and no count.
- **F5 — the turn-list binding was one shape short.** A recovery row for a line the frozen file attaches none to, and the same row twice, are refused.

## What the battery did

Four guards stopped firing during this fold and the battery reported every one rather than passing it: three mutations edited lines this fold rewrote or renamed, and one pointed its control at a class that does not exercise the behaviour, so blanking the check left that class green. One control also needed a git repository, because it drives the ledger check, which reads the system tree from git. Each is repointed. A guard that cannot apply is reported as a guard that did not go red, which is what made all four visible.

## Verified on these bytes

    python3 evals/gap-study/test_harness.py                243 tests, OK
    python3 evals/gap-study/test_harness.py --mutations    103 mutations, every one red when broken, 96 watched green first
    python3 evals/gap-study/lint_language.py evals/gap-study/    clean, 62 inputs, 2 excused lines
    python3 evals/gap-study/costs.py --check               COSTS.md is what the reader writes
    python3 evals/gap-study/check_results.py --ledger      clean
    python3 evals/test_harness.py                          44 tests, OK
    python3 evals/check_results.py --controls --lexicon     clean

No criterion moved.
No take has run.
