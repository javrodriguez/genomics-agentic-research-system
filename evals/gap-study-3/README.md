# The Gap Study, round 3

The three tasks round 2 measured on no model — `scope-read`, `template-adherence`, `confounded-design` —
measured again on both halves and all three Claude models at n = 3, under one permission condition
pre-registered for the whole model axis.

Round 2's counts for the same three tasks print beside round 3's under a caption that names, per column, the
permission condition, the run date and the instrument.
The two are never added together: the instrument changed between them, and a figure that joined them would
describe neither.

Status, slice by slice, is in `PROGRESS.md`. The design is `prereg-draft.json` until it is frozen, and
`prereg.json` afterwards; `prereg.py --status` says which is in force.

## What this folder is

A byte copy of round 2's instrument as it stood at its done commit `bf065fe`, with thirteen files edited and
each edit recorded with its reason in `COPIED.json` (the count is `COPIED.json`'s own, and the battery holds this
sentence to it). `copy_manifest.py --check` re-derives all of it from
`git show` and exits non-zero on any difference.

Ten of the copied files are pinned **byte-identical** by the goal that drives this round: `check_take.py`,
every grader under `graders/`, the label reader `graders/labels.py`, `lint_language.py` and `commit_msg.py`.
An edit to one of those is a failure of this round, not a manifest entry — a study that may change its grader
between rounds is not measuring the same thing twice.

**A consequence worth knowing before you run anything.** Those ten files were copied with their usage lines
intact, so a docstring in `check_take.py` still spells `python3 evals/gap-study-2/check_take.py`. That is the
round it was copied from, not the round you are in. Read every path from this folder; `test_round3.py` proves
that no string this study *executes or prints* names round 2's folder, and that only docstrings still can.

## The change from round 2, in one place

`drive.py` carries five changes and its own docstring names them, in this order:

1. **The permission condition.** Every turn passes `--allowedTools` with the entries the pre-registration
   pins, derived by code from the command forms each task's route uses before its probe, read from round 2's
   own committed transcripts. Round 2 passed `--permission-mode auto` to all three models; the pre-study
   (`evals/haiku-prestudy/`) found 34 of Haiku's 36 sessions had recorded `default` instead, with its first
   command denied in every take of the cell it re-ran.
2. **The mode passed is `default`, not `auto`** (Ruling 7). Under `default` no classifier admits a command the
   list does not, so the list of change 1 is the entire permission surface, identically for all three models.
   This is the one executable constant the round changes.
3. **The mode is read, not assumed.** The ledger's `permission_mode` is now what the session *recorded*, read
   from the take's own published transcript, with the flag that was passed kept beside it as
   `permission_mode_passed`. Round 2 wrote the constant into both places, so `check_take.py`'s
   constant-binding rule compared a constant with itself. The rule is unchanged and byte-identical; this is
   what gives it a session to measure. A session that recorded another mode is routed by that rule as a
   rehearsal with reason `constant-binding`, and that rehearsal is admissible: `constant-binding` is not
   among this round's `driver_decided_reasons`, and `check_results.py --ledger` re-derives the field from the
   transcript when it re-runs the checker, so only an edit to the field alone is refused as ledger-made.
4. One display string takes its path from `study.py`, as round 2's own design says a path must.
5. The per-task walk cap is four rather than two (Ruling 8): round 2's cap counts operator-script revisions
   and this round revises no script.

## The checks, and what each grades

| Command | What it grades |
|---|---|
| `python3 evals/gap-study-3/copy_manifest.py --check` | every copied file against its blob at the source commit, every edit against its reason, every pinned file byte-identical |
| `python3 -W ignore evals/gap-study-3/test_round3.py` | this round's own battery; each test mutates what it guards and watches it go red |
| `python3 evals/gap-study-3/lint_language.py evals/gap-study-3/` | round 2's word and number-shape guard, copied byte-identical |
| `python3 evals/gap-study-3/lint_pooling.py evals/gap-study-3/` | round 3's own guard against a sentence that adds two instruments together; **no excusal path** |
| `python3 evals/gap-study-3/review_kit/rounds.py --check` | every registered round of review has a committed report; an open round blocks the freeze |
| `python3 evals/gap-study-3/denials.py --check` | every call the harness refused in a graded take, with the command quoted; `result.py` prints the count beside each cell |

Round 2's language linter carries no pattern for this, because round 2 had no second instrument to add itself
to. `lint_pooling.py` is round 3's own, run beside the copied one rather than folded into it, so the copied one
stays exactly as it was.

## The record

`transcripts/`, `rehearsals/`, `pauses/`, `verification/`, `review_kit/` reports, `takes.json`, `prereg.json`,
`COPIED.json` and `PROGRESS.md` are append-only. They change by appending, or through a recorded amendment
that carries its own regrade — never by an edit and never by a delete.

Pre-freeze review reports live in `review_kit/` as `prefreeze-<n>.md` with `prefreeze-<n>-blindness.txt`
beside each; final verification reports live in `verification/` as `verify-<n>.md` with
`verify-<n>-blindness.txt`. Two folders, so a fresh reader counts either from `ls` alone.
