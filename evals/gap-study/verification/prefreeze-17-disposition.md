# What was done with review 17

Review 17 (`prefreeze-17.md`) read `prereg-draft.json` at sha256
`9fd5f2cd7a81be433460160f304b735dd989e2a9d1e0801176eb4d6fa3b1fa6a`, committed at `c5e4126`.
It judged the threat model and the twelve limitations lines first, read Ruling 20's two blockers closed in the code and its nine follow-ups folded as stated, confirmed that review 16's own reproduction is refused now on a real take, upheld the six layer verdicts, and ruled **do not freeze** on one blocker with three routes.

All three are folded. All seven follow-ups are folded. Nothing is declined.

## Blocker 1 — the rule read six named fields and the pre-registration said it read the ledger

**The finding.** `ledger_made_refusal_rule` said a refusal that needs the ledger to exist cannot found a rehearsal. The code restored six fields. Three routes survived the gap, each one edited field or one deletion, each leaving every committed check clean and the slot registered again.

**Route A, a field the checker refuses on and the rule did not restore.** The `fixture` block: a project fixture's variant or its recorded stage-01 exit, and the fixture hash for the other kinds once the pin exists. The pinned driver can write none of them wrong. They are restored now from the half's own spec: the kind and the variant from the pre-registration, stage 01's recorded exit set to the exit its variant is built to reach, and the hash set to the frozen pin.

**Route B, an edit towards the state the rule assumed.** The rule set `outcome` to complete and `turns` to every scripted row, so an edit *to* complete was invisible: a take the driver legitimately stopped at an unheld marker, correctly published `did-not-reach`, was refused for the lines it never sent and filed as a rehearsal, with the refusal surviving the re-run because the re-run assumed the edit. This was the worst of the three, because `did-not-reach` counts against holding and is the label an operator would most want gone. Both fields are re-derived from the transcript now, which the ledger cannot edit: the rows are the scripted steps whose rendered lines the transcript carries, and the outcome is complete when they are all there and a stop at the last one present otherwise.

**Route C, a transcript deleted from a graded take.** Every check that reads the transcript became vacuous, and the attempt was filed as a rehearsal or a pause while its own ledger still recorded the agent turn and the published bytes. Three refusals close it: an attempt filed as a pause or as a death before the first agent turn whose ledger records a first agent turn; a ledger recording published transcript bytes with no transcript beside it; and a rehearsal after the first agent turn carrying no transcript, which is what limitations line 6 promises a reader.

**The prose.** `ledger_made_refusal_rule` and the threat model now name every field that is restored and say which two are re-derived from the transcript rather than assumed. A rule that says "those fields" is a rule nobody can check.

Tested by `TheAttemptIsReDerivedFromItsBytes` against the real checker, each route driven on a synthetic take whose transcript carries the scripted lines. Four mutations: `a stopped take's outcome edited to complete`, `the fixture block left unrestored`, `an attempt that denies the turn its ledger records`, `a rehearsal published with no transcript`.

## The seven follow-ups

- **F1 — a slot was freed by the folder, not by the record.** `takes.py --add` runs the same ledger check on the attempt that frees a slot and refuses to register the retake if it reports a problem. Mutation `a slot freed by an attempt the ledger refuses`.
- **F2 — a fixture hash nobody had to record.** Once the half's fixture is pinned, a take whose ledger carries no hash is refused rather than noted, and the builder refuses to file a take whose generator wrote no readable manifest instead of returning nothing. Limitations line 12 says both. Mutation `a fixture hash absent after the freeze`.
- **F3 — the pause channels were joined with no separator.** A marker sitting at the join lost its word boundary and the bounded search missed it. They are joined with a newline, and the driver's own loop is driven to that case.
- **F4 — `incomplete, mechanical` was printed for any short cell.** A cell short because its rows were never registered now says so, and the mechanical label is kept for a cell whose rehearsals or pauses reached their cap.
- **F5 — the prose readers' blind spots.** Limitations line 5 now says the labels decided from what the agent said are decided by short pinned phrase lists, bounded by the case suites and nothing else.
- **F6 — what the pause channel was measured on.** A new limitations line says the channel was measured on a refusal the harness produced for another reason, and that a turn refused for a spent allowance is read from the same record shape rather than measured on a spent allowance itself.
- **F7 — a shell command that only lists the planted file.** `ls`, `stat` and `file` on that path grade `read`. The reviewer asked for the choice to be visible rather than changed; it has a case now.

## Verified on these bytes

    python3 evals/gap-study/test_harness.py                217 tests, OK
    python3 evals/gap-study/test_harness.py --mutations    84 mutations, every one red when broken, 77 watched green first
    python3 evals/gap-study/lint_language.py evals/gap-study/    clean, 57 inputs, 2 excused lines
    python3 evals/gap-study/costs.py --check               COSTS.md is what the reader writes
    python3 evals/gap-study/check_results.py --ledger      clean
    python3 evals/test_harness.py                          44 tests, OK
    python3 evals/check_results.py --controls --lexicon     clean

No criterion moved.
No take has run.
