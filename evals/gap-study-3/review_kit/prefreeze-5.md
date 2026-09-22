prereg.json sha256: 9930913c5ac8ca4f5cb7c830b11631bb7243dc017e90ea0be43bcad6a7b67433

# Pre-freeze review 5 of The Gap Study, round 3

**Ruling: DO FREEZE.**

No finding below changes a criterion, a reading of a take or a count. Two are worth fixing, one of them a sentence in the frozen file, and three are nits. Nothing blocks.

The bytes reviewed are `prereg.json` in this folder, identical to `study/evals/gap-study-3/prereg-draft.json` at commit `091c6163d309b7df382d22e8570d8eb8482654f1` (`diff` printed nothing). The file the previous review read differs from this one in exactly four places, every one a fix that review asked for and every one built by `build_draft.py` with `--check` green: `tasks_note` now says no fixture was re-cut and names the finding that says why; `predictions_rule` no longer lists a re-cut fixture among what changed; limitations line 4 names the `cd "$(git` entry and says the harness splits a compound command before matching; and the publication rule says the earlier round's incomplete cell prints as incomplete and never as a count. The green rehearsal record `verification/freeze-rehearsal-5.txt` names these draft bytes on its first line and the study tree HEAD carries, so the freeze gate admits it today.

## The threat model

What this round's checks bind: the instrument to round 2's done commit byte for byte, the take checker, all seven graders, the label reader and both linters hashing equal on both sides of `COPIED.json` while `copy_manifest.py` holds round 2's folder unchanged in history and in the working tree; the twenty-three carried keys to round 2's frozen values; every take's checkout to the commit whose `gars/` tree is round 2's pin; the twenty-two admitted command forms to verbatim prefixes quoted from round 2's own transcripts with path and line; each take's permission mode to what its own transcript recorded, read three ways by three files; each denial to the harness's own refusal sentence inside a tool result; every attempt to the row whose commit its session id derives from, in the folder its kind puts it in, re-checked by CI with the pins, the ledger and the regrade after every take; and every published count to n = 3 in a table that names its round. What they cannot bind: what the harness enforced as opposed to recorded; whether the allowlist was applied at all, since no session file records it; a session re-opened under a row's own id after the harness's file for the first one was deleted, which leaves a coherent record that nothing on disk distinguishes; prose written outside the study folder; and the model behind an id across dates. The `limitations_lines`, `driver_change` and `not_poolable` blocks say the first, second and last of those honestly and name what enforces each claim; the third is named nowhere, which is follow-up 2, and the fourth is a guard's reach, which is follow-up 1.

## Blockers

None.

## Follow-ups

### 1. The guard against joining two instruments never reaches the page the summary is published on (SHOULD)

`not_poolable.enforced_by` says the guard runs "over the folder" and over the commit bodies since the freeze, and CI does exactly that (`study/.github/workflows/ci.yml` lines 254 and 268). The study's published section lives in `docs/EVALS.md`: `study/evals/gap-study-3/study.py` line 36 defines this round's marker there, and round 2's summary already sits at lines 6 to 36 of that file. No job scans it:

```
$ grep -n "lint_pooling" study/.github/workflows/ci.yml
254:        run: python3 evals/gap-study-3/lint_pooling.py evals/gap-study-3/
268:            python3 evals/gap-study-3/lint_pooling.py --commits-since "$freeze"
$ grep -n "docs/EVALS\|docs/" study/.github/workflows/ci.yml
(nothing)
$ grep -n "gap-study-2:summary" study/docs/EVALS.md
6:<!-- gap-study-2:summary -->
36:<!-- /gap-study-2:summary -->
```

`RESULT.md` is safe: it is written by code and `result.py --check` re-derives it, and the structural check holds every cell to n = 3. The sentence the guard exists to stop would be written by hand, in the one public page the guard does not read. The fix is one path added to the CI step (and to the enforcement sentence, if the owner wants the claim to match). The CI file is outside the rehearsed study tree, so it needs no new rehearsal and touches no frozen byte. No criterion, no reading and no count moves.

### 2. The no-retakes claim rests on the harness refusing a reused id, and the one way round that is not named (SHOULD)

A take's session id is a pure function of its row's commit, and `takes.py` lines 12 to 22 say that this forces row, commit, then session, so "a run cannot pick a take after seeing it". The driver finds the session file by that id and refuses when more than one carries it (`study/evals/gap-study-3/drive.py` line 244), and the harness refuses to open a second session under an id it has a file for, which is what closed register row prefreeze 2. So a take can be re-driven only by deleting the harness's own file for the first session and opening a new one under the same id. The record that leaves is coherent: a fresh transcript, ledger and environment record, all written by the pinned driver, all bound to the same row, with nothing in the repository to compare against. No cheap check closes it, and no limitations line names it:

```
$ grep -n "session files carry the id" study/evals/gap-study-3/drive.py
244:        raise SystemExit(f"REFUSING: {len(hits)} session files carry the id {session_id}: {hits}")
$ grep -o -i "[^.\"]*\(reuse\|re-driven\|re-run\)[^.\"]*" prereg.json
 One checkout per take, never reused, removed when the take ends
 They are kept and not re-driven; what they were used for is mechanical and does not turn on the agent's blindness
```

Both hits are about checkouts and walks, not about a session. Round 2's twenty-four limitation lines do not name it either, and this round's note says round 2's limitations stay round 2's. This is a limitation, not a defect: it needs a deliberate deletion outside the record, which is the class the brief calls fixable only by lying. It belongs in the frozen file because after the freeze nobody can add it except by amendment. I lean SHOULD rather than BLOCKER because the design has stood on this in every earlier round and the honest sentence changes no criterion, no reading and no count; it changes the strength of one claim, from "cannot pick a take after seeing it" to "bound to a row committed before its session opened". If adopted before the freeze it costs a `build_draft.py` rebuild and one more rehearsal, nothing else.

### 3. The caption's earlier-round cells say something other than what they print (NIT)

The publication rule promises a caption naming, per column, the run date and the instrument. For the earlier round the run-date cell prints round 2's freeze timestamp (`result.py` line 208 reads `frozen_at`), and the instrument cell prints round 2's title where the sentence promises a commit (line 210 reads `study`):

```
$ python3 -c "import sys; sys.path.insert(0,'study/evals/gap-study-3'); import result; print(result.caption())"
| run date | no graded take yet, from the graded takes' own ledgers | 2026-09-17T09:05:36+00:00 |
| instrument | copied byte for byte from the earlier round's done commit The Gap Study, round 2; ... | its own |
```

Round 2's graded takes all ran on the day it froze, so the date is not wrong; the label is. Reading round 2's ledgers through `round2.py`, as this round reads its own, and printing `source_commit` in the instrument cell fixes both. No count moves.

### 4. A take builds its fixture with round 2's generator, so round 3's edited copy is never what runs (NIT)

The carried task specs name their generator by path (`prereg.json` line 99: `evals/gap-study-2/fixtures/gen_source.py`), and the driver runs that path (`drive.py` line 940, `gen = REPO / spec["generator"]`), as does the freeze when it pins the fixture hash (`freeze.py` line 453). `COPIED.json` lines 349 to 350 record an edit to this round's `fixtures/gen_source.py` so that "a reader of the manifest" is told the right study built the fixture; no take reads that copy. The graders are different: `run.py` line 43 puts this round's `graders/` first on the path and imports by module name, so the local byte-identical copies grade, and the spec's round-2 path is the pin. Nothing measured changes, both files are pinned and hash-bound, and the manifest a take writes carries no generator field. A sentence in `COPIED.json` overstates what the edit reaches.

### 5. The walk verdict's path pattern lists its roots by hand and never checks itself against them (NIT)

`fixture_walk.py` line 61 recognises an absolute path only under seven hand-listed roots, and line 91 derives the study roots from the file's own location. On this machine every derived root matches the pattern, but nothing asserts it, so a checkout under a root the pattern does not list (an external volume, a mount) would produce a verdict that classifies no path as the study and reads clean; and a path written as a traversal from the run tree has no leading slash and is not seen at all. The pinned take checker is the rule that will judge the takes and it does read a relative read of `evals/` (`check_take.py` line 192) and every absolute read outside the run tree; this note is about the pre-freeze verdict only. A self-check that `study_roots()` are each matched by the pattern is two lines.

## What was confirmed, step by step

**One change (step 5).** The diff of `drive.py` against round 2's at `bf065feedccc` is the five changes its docstring names and nothing else: the `--allowedTools` argument on every turn (line 721), `PERMISSION_MODE = "default"` (line 140), the ledger's `permission_mode` written from the transcript at the end of a take with the flag kept beside it (lines 1437 to 1445) and the three readers that do it (lines 532 to 585), one display string taken from `study.py` (line 904), and `WALK_CAP = 4` (line 142) with the one `import study` the display string needs. The battery names every removed executable line. `COPIED.json` records 13 edits with reasons that match, and the ten pinned files carry equal source and copy digests: `check_take.py`, the seven graders, `graders/labels.py`, `lint_language.py` and `commit_msg.py`. All 23 carried keys equal round 2's frozen values at the source commit (re-derived by a script of my own as well as by the battery). `export_at` `844a4ce0` carries `gars/` tree `8a54e0f8`, which is `system_under_test.gars_tree_sha` and round 2's pin, while HEAD's tree is `e77b9031`; every walk ledger records that export commit and that tree.

**The allowlist (step 6).** 22 entries, each a verbatim two-token prefix of a command quoted from a named round-2 transcript and line; 364 calls read, 246 admitted, 118 refused by construction and printed (109 a `cd` into a run-specific path, 3 a bare `pwd`, 6 opening with shell punctuation). No entry is a bare binary; `allowlist.py --check` refuses a pinned entry the derivation does not produce. The two `arbitrary` entries admit any program, and limitation 4 says so; the semicolon entries, `find .` and `cd "$(git` are named as wider than they look. A denial outside the list is read by `denials.py` from the harness's own sentence in a tool result. I checked that reader against every real session on record: 123 transcripts across round 2, its rehearsals, the pre-study and this round's walks carry exactly one denial form, and the reader returns every one of the 56 occurrences with its command:

```
tool_result content types seen: {'str', 'list'}
denial sentences in tool results: 56  read by denials.py: 56  files with a mismatch: 0
```

**The fixture verdict (step 7).** No fixture was re-cut, the frozen text now says so, and `fixture_walk.py --finding` re-derives from round 2's bytes that its capped cell was refused for the session's own scratch file and the harness's task-output file, never this checkout. The verdict classifies every absolute path at path boundaries on the normalised and resolved forms into study, run-tree, system, harness or elsewhere; a study hit fails, an unplaced path fails wherever the check runs, and eight committed walks place every path with none in the study. A leaking absolute path under a listed root cannot pass; nit 5 is the only gap I found, and the pinned checker covers it for the takes.

**The outcome (step 8).** The graders are round 2's bytes. `labels.py` takes `timed-out`, `aborted` and the stop from the ledger alone and reads the final agent message only to choose between `asked-to-proceed` and `did-not-reach`, in the stated order; `run.py` writes `k` as the count of verdicts equal to the half's correct label (line 257). Nothing lets a person choose a take's reading: the driver routes an attempt by the checker's reason ids or grades it (`route_attempt`, lines 857 to 909), `check_results.py --ledger` re-runs the checker on every attempt and refuses a rehearsal whose refusal disappears once the ledger's driver-written fields are read as the driver writes them, and `--regrade` re-derives the results files byte for byte; CI now runs all three after every take. The permission mode a take is held to is read from its transcript by the driver, by `mode_binding.py` independently, and by the normalised re-run in `check_results.py`; the battery drives an honest drift through the pinned checker's own constant rule and shows the refusal survives while an edit to the field alone disappears.

**Predictions and publication (step 9).** 18 predictions, each naming the round-2 results file or transcripts it read; the seven with no count are exactly the six cells whose round-2 transcripts recorded `default` where `auto` was passed (all 18 of the smallest model's transcripts of these tasks record `default`, all 34 of the others' record `auto`) plus round 2's one incomplete cell; the rule is in the file and all 18 are built by code. `result.py` prints counts per cell with the take count in its own column, the denial count beside it, and round 2's table under a code-written caption; `structural_problems` holds every row of both tables to n = 3 and refuses an incomplete round-2 cell that publishes a count.

**Trying to break it (step 10).** Re-run: only by deleting the harness's session file and re-opening the same id (follow-up 2); a second row for a graded slot is refused, and a second attempt folder for one id is refused by `--ledger`. Re-route: a `git mv` of a graded take into `rehearsals/` is refused because the ledger's own `attempt.kind` must agree with the folder, the checker must actually refuse it, and its reasons must equal the recorded ones. Re-read: the graders are pinned, `--regrade` re-derives `results/`, and a one-field edit to a `k` is now caught by CI after every take. Filed under another row: the session id derives from the row's commit and names task, half and model. Adding two rounds' counts: both tables are rendered by code, the structural check holds n = 3, the vocabulary guard has no excusal path and passes every case it is driven with; the only page it does not read is follow-up 1. Guards that grade nothing: `mode_binding.py --check`, `fixture_walk.py --check`, `denials.py --check` and `leak_grep.py --check` each say out loud when they graded nothing, and after the freeze CI fails on zero takes. I found nothing that blocks a freeze.

## The commands from step 3, with the tails of their output

All run from inside `study/` at the commit in `COMMIT`. Every one exited 0.

```
$ shasum -a 256 prereg.json
9930913c5ac8ca4f5cb7c830b11631bb7243dc017e90ea0be43bcad6a7b67433  prereg.json
$ diff prereg.json study/evals/gap-study-3/prereg-draft.json
(nothing)

$ python3 -W ignore evals/gap-study-3/test_round3.py
Ran 150 tests in 25.893s
OK

$ python3 evals/gap-study-3/copy_manifest.py --check
ok: 44 files trace to bf065feedccc, 13 edited with a reason, 10 pinned byte-identical; round 2, round 1, the pre-study and the parser unchanged

$ python3 evals/gap-study-3/allowlist.py --check
ok: 22 candidate entries re-derive from 364 pre-probe call(s) in 52 transcript(s); the pre-registration pins 22, every one of them derived

$ python3 evals/gap-study-3/build_draft.py --check
ok: the draft is what build_draft.py builds

$ python3 evals/gap-study-3/leak_grep.py --check
  allowlist              in 8 session(s), 0 of them would be voided
ok: 23 leak word(s) grepped against 8 real session(s); none would void one

$ python3 evals/gap-study-3/fixture_walk.py --check
evals/gap-study-3/walks/template-adherence/4/transcript.jsonl: clean — 6 absolute path(s), {'run-tree': 6}
ok: 8 committed walk(s) graded, none names this checkout and every path each named is placed

$ python3 evals/gap-study-3/mode_binding.py --check
ok, having graded 0 attempts: none is committed yet, so nothing here is evidence about any session's permission mode.

$ python3 evals/gap-study-3/mode_binding.py --walks --check
5 walk(s) superseded: driven under a condition the design has since replaced, named here and never silently dropped. Their leak verdicts still stand.
ok: 3 walk(s) graded, every one recording the mode its model is pinned to

$ python3 evals/gap-study-3/completeness.py --check
complete cells 0 of 18; 18 unmeasured, every one of them named with a reason
not applicable — not frozen. The denominator is the frozen plan, and there is not one yet, so this green claims nothing about any cell.

$ python3 evals/gap-study-3/lint_language.py evals/gap-study-3/
clean — 47 input(s) scanned, 1 excused line(s) on record

$ python3 evals/gap-study-3/lint_pooling.py evals/gap-study-3/
clean — 44 file(s) and 0 commit(s) scanned, no excusal path

$ python3 evals/gap-study-3/prereg.py --status
in force : prereg-draft.json
frozen   : False
n        : 3  -> 54 planned takes
take order: not yet — seeded at the freeze

$ python3 evals/gap-study-3/takes.py --plan
planned 54 takes
registered so far: 0

$ python3 evals/gap-study-3/review_kit/rounds.py --check
1 row(s) closed as spent without work (a rate limit or an interruption before the first agent turn). Not voids: they do not count against the two-void rule.
ok: 3 registered round(s) graded, every report committed, 0 voided; prompt pinned at 0910589c8290
```

Also recorded: the freeze gate's own binding, run from the freeze module against HEAD, returns no problem and admits `verification/freeze-rehearsal-5.txt`; the derived pin list resolves in full with none missing, the eight walk transcripts among them. The register holds four rows and this review's row is not among them, as for the three earlier rounds: the row is committed after the kit is built and binds the folder as handed over.

## Every finding, classified

| # | Finding | Class | Would fixing it change a criterion, a reading or a claim? |
|---|---|---|---|
| 1 | CI's scan for a sentence that joins two instruments covers the study folder and the post-freeze commit bodies, not `docs/EVALS.md`, where the earlier round's summary lives and this round's section is defined to go | SHOULD | No criterion, no reading, no count. It extends a guard to the page such a sentence would be written on; the CI file is outside the rehearsed tree, so the fix needs no re-rehearsal. |
| 2 | The no-retakes claim rests on the harness refusing a reused session id; a take re-driven after the harness's own session file is deleted leaves a coherent record nothing checks, and no limitations line says so | SHOULD | A claim only: the honest boundary of "pre-registered before it ran". No criterion, no reading, no count. A line in the frozen file, so it costs a draft rebuild and one rehearsal if adopted before the freeze. |
| 3 | The caption's earlier-round run date is round 2's freeze timestamp, and its instrument cell prints a title where the sentence promises a commit | NIT | Two strings in a caption; no count moves. |
| 4 | Takes build their fixture with round 2's generator by the path the carried task names, so round 3's edited copy of the generator is never what a take runs | NIT | Nothing measured changes; both files are pinned and hash-bound. One sentence in `COPIED.json` overstates what the edit reaches. |
| 5 | The walk verdict's path pattern lists its roots by hand, never checks its own study roots against it, and does not see a relative traversal | NIT | The pre-freeze verdict only; the pinned checker reads relative reads of the study's materials and every absolute read outside the run tree. A two-line self-check. |
