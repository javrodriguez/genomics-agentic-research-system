---
date: 2026-09-30
status: standing
kind: decision
touches:
  - docs/validity/
  - docs/EVALS.md
  - .github/workflows/ci.yml
symptoms:
  - the six Gap Study validity arguments still read as drafts after the owner has read them
  - docs/EVALS.md says its graders under-report rather than over-report, while probe P7 shows the first study's classifier reading a question-form caution as asserted
  - python3 docs/validity/probes.py --check runs in no CI job
---
# Gap Study validity: the owner's sign-off, six signatures and five decisions

Addendum to [0216](0216-gap-study-validity-drafts.md).
The decisions below are **the owner's**, typed by him in one review sitting on 30 September 2026 and quoted exactly as they were recorded.
The pages, this record and every change it lists were written by the E2 build lane; the owner wrote none of their text.
He signed arguments that the lane drafted and a reviewer checked; signing makes each his position, not his writing.

## Context

[0216](0216-gap-study-validity-drafts.md) added `docs/validity/`: six per-task validity arguments, the Agentic Benchmark Checklist run over the Gap Study's graders, a follow-ups table and `probes.py`, all labelled drafts for the owner's review.
It left to him, per argument, whether to sign it, amend it or reject it; whether to accept the checklist's statuses; the follow-ups' order; and whether and where `docs/EVALS.md` links the folder.
Its rejected alternatives left wiring `probes.py --check` into CI to him at sign-off, because `.github/workflows/ci.yml` is a protected path (§9.3, R-094).

The sitting ran from 10:20 EDT on 30 September 2026, in the orchestrating session (glitch-14), on the drafts at commit `3c6671a`.
Before the first signature, that session re-ran `python3 docs/validity/probes.py --check`: 28 run, 28 as stated, exit 0.
The session presented each argument in turn with its recommendation, and then five further decisions, each with a recommendation.

## Decision

**The six signatures.** Each is his typed word, verbatim, with the time it was recorded.

1. 10:27 EDT, `template-adherence.md`: "Sign".
2. 10:35 EDT, `precondition-refusal.md`: "Sign it."
3. 10:37 EDT, `number-fidelity.md`, `scope-read.md`, `plan-gate.md` and `confounded-design.md`: "sign 3-6", which names the third to sixth arguments in the order the session presented them.
   On `scope-read` that signature includes the question the page leaves to him under "Construct validity", which was put to him with a yes recommended: the construct he defends is the one the page names.

No argument was amended and none was rejected.

**The five decisions.** At 10:38 EDT he answered the remaining five with one word, "defaults", which took the session's five recommendations as they were presented to him:

1. The checklist's statuses are accepted as scored; with the six signatures, R.5 and R.11 read met, as F-17 states.
2. The follow-ups' order: a first tier that needs no owner time and no spend, F-10 (the no-model oracle and trivial-reply table), then the read-only counts F-01, F-07, F-06 and F-04, then F-05 (an erratum record); deferred, F-09 (blind human labelling, which needs his hours) and F-18 (new model runs, which need spend); the others proposed, in no order.
3. `docs/EVALS.md`: a dated correction note beside its sentence "The graders under-report rather than over-report, on purpose." (line 365 at `37a8d94`), with that sentence kept, citing `docs/validity/confounded-design.md` and F-08.
   The recommendation, as recorded, quoted that line as "can never over-report", which are the words of the classifier's own docstring (`evals/graders/confounded_refusal.py`, lines 17-20); the note quotes the page's sentence as it stands.
4. `docs/EVALS.md` links `docs/validity/`, in one line.
5. `python3 docs/validity/probes.py --check` is wired into CI.

**What the lane changed on those decisions.**

- The six arguments: the draft banner of each is replaced by a dated statement that the owner read and signed it; the argument text is the text he signed, unchanged.
  Two banners carry one more line: `scope-read`'s records his answer to its construct question, and `confounded-design`'s says that the `docs/EVALS.md` line it cites has moved.
- `docs/validity/README.md`: its banner says the same, its section for the owner's review becomes the record of what he decided, and its citation note names the one cited file that has moved since `37a8d94`.
- `docs/validity/abc-checklist.md`: accepted banner; R.5 and R.11 read met, their evidence names the signed arguments, and F-17 is marked closed on the sign-off.
  The result becomes: of 43 items, 15 met, 12 met in part, 5 not met, 11 not applicable, so 17 findings; the page keeps the draft's totals (13 met, 14 met in part, 19 findings) in a dated sentence.
- `docs/validity/follow-ups.md`: the owner's order, above the unchanged table; F-17 is listed as closed.
- `docs/EVALS.md`: one paragraph linking `docs/validity/`, after the intervals paragraph near the top; and the dated correction note, directly after the paragraph it corrects, whose sentences are unchanged.
- [0216](0216-gap-study-validity-drafts.md): a dated addendum that points here and gives the new totals; its original text is unchanged.

**Approval of the protected change.**
The owner's decision 5 is the approval this record gives for one change to a protected path (§9.3, R-094):

1. **`.github/workflows/ci.yml`**: one new step, `Gap Study validity probes (decision 0217)`, appended as the last step of the `tests` job, which runs at the pushed commit: `python3 docs/validity/probes.py --check`.
   Four lines added, zero removed; every other job and step is as at `37a8d94`.

The step's commit is the lane's, under this approval, as with the CI steps approved in [0211](0211-gap-study-intervals-0210-delegated-approval-of-protected-change.md) and [0201](0201-small-fixes-0200-delegated-approval-of-protected-change.md); the difference is that here the approval is the owner's own decision, not one made under his delegation.

## What this does not close

- **The follow-ups.** None has run; the order is the owner's, and each is pre-registered before it runs.
- **F-08 itself.** The correction note says the first study's classifier can over-report; how many published sentences it misread is what F-08 would measure, and no result is regraded.
- **The public push.** It waits on the owner's own typed word, after he has seen this final candidate.
- **Whether an argument is right.** The owner's signature makes each his to defend; the checks bind the citations, the checklist's text and the probes' labels, not the reasoning.

## Test

`python3 docs/validity/probes.py --check` runs 28 probes and exits 0 only when every probe returns the label the signed pages state; CI now runs it on every push to main and every pull request.
The fault that must make the new step fail is any edit to a cited grader that changes one of those labels, or any change to a probe's stated label.
`git diff 3c6671a -- docs/validity/*.md` shows, on each of the six arguments, only the banner lines changed.
The checklist's four status counts, read from its table, are 15, 12, 5 and 11, and sum to 43.

## Status

Standing.
The six arguments are the owner's, signed; the checklist is accepted; the public push waits on his word.

## Date

2026-09-30
