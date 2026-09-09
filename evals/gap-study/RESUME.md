# Where the Gap Study stands — written to be picked up on a different machine

**Parked for the laptop migration, 2026-09-09. Nothing is frozen. No take has run. Spend $0.**

Every byte of this study is inside the Brain and travels with it. Nothing needed is in a temp
directory: the eleven review reports were the one thing that was, and they are committed under
`reviews/`.

## The one thing to do first on the new Mac

Review 11 ruled **DO NOT FREEZE — four blockers**, and its first one is against the fix that was made
the same day. Read `reviews/review-11.md` before touching anything.

`drive.py`'s `clean_run_tree()` clones this repository and deletes `evals/` from the working tree.
A clone carries history: the pre-registration, the protocol, the cases and the graders stay readable
with one `git show`, and the deletion shows up in `git status` — which the harness puts in front of
the agent on its first turn. Closing one leak opened two more in the same direction. The other three
blockers are in the same report.

The fix is not written. Nothing was papered over to reach a stopping point.

## What the study is, in one paragraph

Six task pairs, five models, three takes per half per model. The central question is where the
deterministic layer does not cover a failure mode, which model catches it, and in how many takes.
The answer already established and confirmed by every review is that the layer is SILENT for the
behaviour all six probes elicit — the finding unflattering to the design argument, which the
protocol pre-commits to publishing.

## State

- 6 task pairs · 8 walks · 120 hand-labelled cases · 60 tests · 15 mutations · 11 reviews
- 0 takes graded · not frozen · `gars/` and the first study unchanged by this work
- The local tier was dropped by the repository owner at gate 2; `local-model/DROPPED.md` is the record
- Rulings 1–8 in `PROTOCOL.md`; ruling 8 is the leak and is the live one
- `RESIDUAL.md` was written at the slice cap and is kept deliberately, even though the cap was lifted

## What happened on the last day, in order

1. Reviews 9 and 10 closed out the pre-registration's prose. Review 10 ruled **freeze, no blocker**.
2. That ruling was not acted on. Reading the folder being prepared for review 11 showed the driver
   had been running the agent inside the operator's personal assistant tree, so Claude Code loaded
   that tree's instruction file and the profile and memory it imports into the agent under test. One
   line of that memory names this study. The leak check swept operator turns only and reported clean
   on a transcript containing two words from its own list.
3. The operator's private material was redacted from all thirteen published transcripts, the four
   published results were re-bound by re-derived hash, and Amendment 4 in `../PROTOCOL.md` plus a
   fourth limitation in `../../docs/EVALS.md` disclose the confound beside the result.
4. The leak check now reads the loaded context, on word boundaries, with pinned excusals. The driver
   refuses to run without a checkout proven to have nothing above it. Both are tested and both were
   watched failing.
5. Review 11 said the checkout is not clean enough. That is where this stops.

## Not done, in the order it matters

- [ ] Review 11's four blockers, starting with the run tree carrying history
- [ ] Re-review after the fix, then freeze (`freeze.py --review-commit <sha> --write`)
- [ ] Then, and only then, the 108 takes

## Two things that are Javier's

- **Five commits are unpushed.** This is a public repository and the migration deliberately does not
  push it. The redaction in them is therefore not live on GitHub yet; the private material is still
  in the published transcripts there until a push happens. That is his call and his word.
- **`git config --global user.email` was set to his GitHub noreply address** so future commits stop
  carrying his personal address. `~/.gitconfig` is on the migration's deliberately-not-carried list,
  so this does not travel and must be set again on the new Mac.

## Carried follow-ups, most valuable first

Nothing tests the driver's outcome strings against the reader that consumes them · enumerate takes
by driver ledger · bind the plant to counts per field rather than per dict · index the verdict field
rather than reaching for it with a default · record `held` on an aborted turn · render the carried
task's lines before its first take · re-drive the eight walks in a clean checkout, since they were
driven under the leak.

## The migration's re-key will touch this study's evidence — expect it, and repair it

The laptop migration rewrites `/Users/rodrij92` to `/Users/javrodher` in every machine-read file its
search finds. Its search deliberately excludes `*.jsonl`, so the transcripts are safe. It does not
exclude anything else here, and **20 tracked files under `evals/` carry that path**: the published
results, the driver ledgers, `cases/scope-read.json`, the fresh-context verification reports, and
`../PROTOCOL.md`.

Three of those matter, and none of them should be re-keyed:

- **`evals/results/*.json`** hold `sentence` fields that are the agent's own words, quoted verbatim.
  The agent said `/Users/rodrij92/…`. Rewriting that makes the file claim it said something it did
  not, in a published record that exists to be checked.
- **The binding breaks either way.** `check_results.py` re-derives each published cell from the
  pinned graders and the transcripts. The transcripts are excluded from the re-key and the results
  are not, so the re-derived sentence would no longer match the committed file. This is the same
  failure the redaction caused, and it is loud rather than silent: CI catches it.
- **`cases/scope-read.json`** binds each case to a message's sha256. Re-keying the quoted text
  detaches the case from the walk it came from, and `test_harness.py` says so by name.

**The repair, on the new Mac, after Phase B's re-key:**

    git -C workspaces/genomics-agentic-research-system checkout -- evals/
    python3 evals/check_results.py --controls --lexicon      # expect: clean — graded=1
    python3 evals/gap-study/test_harness.py                  # expect: 60 tests, OK

Every one of the 20 is committed, so git holds the correct bytes; the migration's own
`rekey-backups/` holds a second copy. Restoring is not discarding work — these are records of runs
that happened on the old machine at those paths, and the old path is the true one.

The other 31 files the search finds here are untracked `gars/projects/*` run scratch, which is
gitignored. Re-keying those changes nothing that matters.

**One consequence for Phase B:** until this repair runs, `git status` in this workspace shows those
20 as modified, which will not equal the ledger's empty dirty list for this slug. That is expected
and is not a migration defect.
