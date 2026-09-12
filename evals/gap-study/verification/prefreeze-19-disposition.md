# What was done with review 19

Review 19 (`prefreeze-19.md`) read `prereg-draft.json` at sha256
`0325344cfa0abcc9eaa93f595da6e555404b2f25c4a58c6c325c79522824764b`, committed at `d181a28`.
It judged the threat model and the thirteen limitations lines first, read Ruling 22's two blockers closed for the shapes review 18 wrote down and its four follow-ups folded as the disposition says, upheld the six layer verdicts, and ruled **do not freeze** on three findings.

All three are folded. All four follow-ups are folded. Nothing is declined.

## The class, stated plainly

Reviews 16, 17, 18 and 19 each found the previous fold one spelling short: a value edited, then a value deleted, then a value added, then a field whose name the check did not test for. Each fold enumerated the shapes the last reviewer wrote down, so each left the next shape open.

This fold stops enumerating and inverts the reading. The outcome is checked against the vocabulary the pinned driver writes, pre-registered as `driver_outcome_shapes`, and anything outside it is refused. The fixture block is replaced by what the driver writes rather than merged with it, so edited, deleted and added are one case. Neither reading has a list of bad shapes to keep current.

## Blocker 1 — the outcome was read only where it said `complete`

**The finding.** `completion_problems` returned nothing unless the outcome opened with `complete`, and nothing else in the graded route reads that field's value: the take checker requires the lines the ledger's turn rows say were sent, which a cut at the last scripted turn leaves whole, and the grader returns no reserved label for an outcome it does not recognise. So deleting the field, blanking it, miscasing it or writing any other word graded a take the driver cut at its probe turn from its partial reply, with the checker valid, the ledger check clean and the grader printing a correct label. On every task the probe is the last scripted turn and the longest, so the turn most likely to be cut is the one whose partial reply would be graded.

**What was done.** The outcome must open with one of the shapes the pinned driver writes, and anything else, absence included, is refused as `outcome-binding`. The shapes are pre-registered, so a reader can check them against the driver rather than against prose. Both directions are bound: a turn row carries an exit code, a non-zero one means the driver cut the take and the outcome must say so, and a take not recorded as cut must end its last reply at the end of a turn. Review 19's F2 rides here, because a row with no exit code at all is refused; the driver writes one for every turn it sends. As a belt on the grading side, `run.py` refuses to grade a ledger whose outcome the driver never wrote.

## Blocker 2 — the fixture block was merged with the spec, not rebuilt from it

**The finding.** The merge kept every key the ledger carried, and the checker reads the three hash keys in a fixed order, so a `tree_sha256_name_invariant` added to a generated take's block is read before the real hash, refuses once the half is pinned, and survives the second run. After the freeze that founds a rehearsal on any of the 54 generated-fixture takes, with the ledger check clean and the slot registered again.

**What was done.** The block is replaced by what the driver writes: `out["fixture"] = _driver_fixture(spec_fx)`. Edited, deleted and added are the same case now, and no key the operator adds reaches the second run.

## Blocker 3 — the copied-tree fixture was bound by nothing after the freeze

**The finding.** The checker read the pin from `sha256`, which the freeze leaves null for a copied-tree fixture by design, because that kind is pinned by its tree hash. So after the freeze all eighteen `plan-gate` takes would have printed "unpinned until the freeze" and been bound to no fixture at all, under a spec that says the fixture is pinned there. The one comparison on record is a test that skips off the machine where the origin lives.

**What was done.** The pin is read as the file hash or the tree hash, whichever the kind carries. The driver's copied-tree branch refuses a tree that differs from the pin before a session opens, as the carried task's builder already did. And a frozen file that pins no fixture for a half is a refusal rather than a note: a binding the freeze was meant to fill and did not is a check that passes having measured nothing.

## The four follow-ups

- **F1 — an attempt refused only on the transcript reading has no route.** Because `outcome-binding` is driver-decided, such an attempt cannot be filed as a rehearsal either. The consequence is stated in `driver_decided_reasons_note` rather than left for the next reviewer, together with the sample the reading rests on.
- **F2 — a turn row with no exit code.** Folded into Blocker 1.
- **F3 — the stale harness note.** It said the harness "has since moved to 2.1.265" while the built-checkout walks record 2.1.267. The note now says the range is read from the takes' own ledgers, which is what limitations line 9 promises.
- **F4 — the threat model's clause.** It now says a graded take's outcome is bound to the driver's vocabulary and to its own per-turn record.

## Two mutations were repointed

`the fixture block left unrestored` and `a fixture field deleted rather than edited` both edit the line this fold replaced, so both stopped applying and the battery said so rather than reporting a pass. They are repointed at the new line. A mutation that cannot apply is reported as a guard that did not go red, which is the behaviour that caught it.

## Verified on these bytes

    python3 evals/gap-study/test_harness.py                228 tests, OK
    python3 evals/gap-study/test_harness.py --mutations    89 mutations, every one red when broken, 82 watched green first
    python3 evals/gap-study/lint_language.py evals/gap-study/    clean, 59 inputs, 2 excused lines
    python3 evals/gap-study/costs.py --check               COSTS.md is what the reader writes
    python3 evals/gap-study/check_results.py --ledger      clean
    python3 evals/test_harness.py                          44 tests, OK
    python3 evals/check_results.py --controls --lexicon     clean

No criterion moved.
No take has run.
