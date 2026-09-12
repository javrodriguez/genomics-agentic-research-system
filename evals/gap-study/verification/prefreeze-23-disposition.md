# What was done with review 23

Review 23 (`prefreeze-23.md`) read `prereg-draft.json` at sha256
`18d65c17488f4114ac17c7d760491ff7300834ba0c4f35f5302d183ca0434d08`, committed at `dff876e`.
It judged the threat model and the thirteen limitations lines first, read Ruling 26's blocker closed in the code and not only in a test, reproduced review 22's own scenario end to end in a clone and found the pinned ledger check clean, repeated it with a cell exhausted by pauses and with a hand-appended row in an exhausted cell, read the five follow-ups folded as the disposition says, upheld the six layer verdicts as `silent`, and ruled **do freeze**.

It is the first do-freeze ruling in twelve reviews. Reviews 12 to 22 each ruled do not freeze, and every blocker they raised is folded and pushed (Rulings 16 to 26).

## Its four follow-ups were not folded, and why

All four touch files the freeze pins. Folding any of them would have meant the frozen study is not the study a reviewer approved, and the point of a pre-registration reviewed and then frozen is that those are the same bytes. They are recorded here as known and unfolded.

- **F1 — the registration command does not compare the slot with the permutation.** The order is enforced when the ledger is read, after the row is committed, so an operator slip is on the record until the registrations pass it. The reviewer showed it resynchronises and called it a follow-up: it needs an operator error, moves no label and no count. A helper that only prints the next expected slot would answer it without touching a pinned file.
- **F2 — a retry of a freed slot may be registered later rather than next.** Prose: the note says "exempt" and the protocol reads as "next".
- **F3 — the cut naming will fire on the carried task's abort by the then-step.** That abort is proven by the failed then-step in the last turn row, and no reply was cut, so a reader would weigh a named take as the two-field residual when the record shows it is not.
- **F4 — the test runner reads every argument as a test name**, so a verbosity flag errors. Cosmetic.

## The freeze

    prereg.json             sha256 faefa7a89901ca37af6930b2741f397d0159bfbc62e91f6fccf491b552e8d97f
    frozen_at               2026-09-12T03:25:19+00:00
    take_order_seed         c44c27e989b44ac0189352d5d9ffd75e5cb67d13
    draft_sha256_at_freeze  18d65c17488f4114ac17c7d760491ff7300834ba0c4f35f5302d183ca0434d08
    pinned files            42          take order 108 cells          unaccounted nulls 0

The draft is byte-identical to what review 23 read.

**The freeze refused once, and it was right to.** `first_study_marker` was null on the carried task's sixth operator line in both halves, and nothing accounted for it. It is null there for the reason `marker` is: that turn has no wait point, in this study and in the first, and the field records the marker as the first study wrote it. The account was added to `freeze.py`, the one file the freeze deliberately does not pin because it produces the pins, and it is conditional: the field is accounted only where that step's own marker is also null, so a first-study marker missing from a turn that has a wait point would still be refused. The claim was checked against the draft before the freeze ran.

## What freezing revealed about the study's own instrument

The freeze switches on code paths that were dormant, and two of them are read by the harness itself.

    test_harness.py    243 tests, 2 failures
    mutations.py       103 mutations, 24 did not go red

Both failures assert pre-freeze behaviour. One expects a note where a half's fixture carries no pin, which freezing turns into a refusal by review 19's own fold; the other expects the normalised fixture block to carry no hash, and the frozen spec carries a real one.

The twenty-four fall into three groups, established rather than assumed:

- **Sixteen** are controlled by a class holding one of those two failing tests. The battery sees the guard red before any mutation and reports it as not firing. Fixing the two tests restores all sixteen.
- **Seven** are inert. The sandbox now carries `prereg.json`, the code there reads the frozen file, and those mutations edit `prereg-draft.json`. Demonstrated on one: its control is green before the mutation and green after it.
- **One** has lost its premise. It existed to prove the runner refuses a draft.

`test_harness.py` and `mutations.py` are both pinned, so every remedy is an amendment to a frozen study, published with before and after and never corrected in place. No take has run, so any amendment is provably before any number exists.

**Why no review caught it.** A reviewer may not run the freeze, and until this pass neither had I. The study has no dry run of its own freeze, so the effect of freezing on its harness was never exercised until it was irreversible. That is a defect in the sequencing, not in the reviews, and it is the one thing a later study should copy differently: run the freeze into a scratch tree first and put the whole gate through it.

No criterion moved.
No take has run.
