prereg.json sha256: 257434a5ddd4208cd61f1a359f956ce9a0f41878f0de6f3ff8765baa51b2c244

# Pre-freeze review 4 of The Gap Study, round 3

**Ruling: DO FREEZE.**

No finding below changes a criterion, a reading of a take, or a claim about a model. Three findings are worth fixing at source before the freeze commit, and each is a wording or a wiring edit that a command in this report re-checks. Nothing blocks.

The bytes reviewed are `prereg.json` in this folder, identical to `study/evals/gap-study-3/prereg-draft.json` at commit `2653f862a785a9fe836a0b5065671b9a1e855eb3` (`diff` printed nothing). The previous review read a file that differs from this one in exactly the places review 2's three blockers named: `constant-binding` is off `driver_decided_reasons` with round 2's list kept beside it, the permission-mode binding paragraph now says the drift rehearsal is admissible and why, the sentence naming what enforces `not_poolable` now names the since-the-freeze scan, and limitations line 4 names the two semicolon entries and `find .`. Every one of those changes is built by `build_draft.py` and `--check` re-derives it.

## The threat model

What this round's checks bind: the instrument to round 2's done commit, byte for byte for the take checker, every grader and the label reader (`copy_manifest.py --check`, and the source and copy sha256 fields in `COPIED.json` are equal for all ten); the twenty-three carried keys to round 2's frozen values at that commit; the export commit to round 2's pinned system tree; the permission condition to command forms quoted from round 2's own transcripts with path and line; each take's permission mode to what its own transcript recorded; each denial to the harness's own sentence inside a tool result; and every published count to n = 3 in a table that names its round. What they cannot bind: what the harness enforced as opposed to what it recorded (limitations line 9), whether the harness applied the allowlist at all since no session file records it (line 3), the model behind an id across dates (line 7), the semantics of a compound command under the harness's own splitting, and a coherent set of fabricated records across transcript, ledger, sidecar and results file. The `limitations_lines`, `driver_change` and `not_poolable` blocks say all of that honestly, and say what enforces each claim. Two places in the same file overstate what changed, and one guard the file leans on is not wired to run after a take; those are the findings below, and none of them is a way for a take to be misread.

## Blockers

None.

## Follow-ups

### 1. The pins and the ledger-made rule are not run by the post-freeze gate (SHOULD)

The pre-registration's `permission_mode_binding` and `driver_decided_reasons_note` both rest on `check_results.py --ledger` to refuse a rehearsal founded on an edited ledger field, and `--ledger` is also the only check that binds a published transcript's bytes to its ledger (`study/evals/gap-study-3/check_results.py` lines 696 to 699). The held count per cell is read from `results/<task>.json`, which the freeze deliberately does not pin (`freeze.py` line 67, `RECORD_ROOTS`), and the only check that re-derives that file from the graders is `check_results.py --regrade` (lines 931 to 954). Round 2's CI job ran `--ledger`; this round's job runs neither, nor the bare pin check:

```
$ grep -n "gap-study-2/check_results" study/.github/workflows/ci.yml
144:        run: python3 evals/gap-study-2/check_results.py --ledger
150:          python3 evals/gap-study-2/check_results.py --controls > "$RUNNER_TEMP/controls.txt" 2>&1
$ grep -n "gap-study-3/check_results" study/.github/workflows/ci.yml
(nothing)
```

The post-freeze steps at lines 305 to 338 of that file run `check_take.py` per graded take, `result.py --check` and `completeness.py --check`. All three read `results/` only through `result.held_counts`, which re-renders from the file rather than re-grading. So after the takes exist, a one-field edit to a `k` in a results file moves a published held count with every automatic check green, and only a person typing `--regrade` would see it. The same holds for a misfiled attempt or an edited `published.sha256_after`: `takes.py --add` runs the attempt check only when a freed slot is registered again (lines 225 to 250), so the last attempt of every cell is never re-checked by anything automatic. The freeze rehearsal runs both modes, but on a record with zero rows.

This is a guard that reads less than the file says it does, and a single edited record could move a reading through it. It is not a blocker: the two checks exist and are green, the CI file is not a frozen byte, and the fix is to add `check_results.py`, `check_results.py --ledger` and `check_results.py --regrade` to the post-freeze block and to the README's table of checks. Fixing it changes no criterion and no reading; it makes the pre-registration's own claim about `--ledger` true after a take rather than only before one.

### 2. The frozen file says a fixture was re-cut, and none was (SHOULD)

`tasks_note` reads "byte-identical to the source file bar template-adherence's fixture, whose re-cut is recorded under fixture_recut", and `predictions_rule` lists "the re-cut fixture" among the things round 3 changed. No such key exists and no re-cut happened: the three tasks are byte-identical to round 2's frozen copy (`test_round3.py` `test_the_three_tasks_are_round_twos_own` passes), `verification/finding.md` records why a re-cut was not made, and limitations line 10 says the checker and the fixture stand as round 2's.

```
$ grep -c "fixture_recut" prereg.json
1
$ grep -n "re-cut" prereg.json | cut -c1-120
779:  "tasks_note": "The three tasks as frozen in round 2, both halves, byte-identical to the source file bar template-adh
1183:  "predictions_rule": "One prediction per planned cell, derived by code and fixed before any take. For each cell, ro
```

Both strings are in `build_draft.py` (lines 342 to 343 and 291 to 293). After the freeze nobody can ask which of the two contradictory sentences is the record, and the false one says the instrument changed in a second place. Fixing it removes a false claim from the frozen file and touches no criterion, no reading and no count.

### 3. The walk transcripts are not pinned, and the freeze says they are (SHOULD)

`freeze.py` line 73 says "The walks ARE pinned: the freeze rests on their leak verdicts." The pin list is derived over the suffixes `.py`, `.json` and `.sh` (line 68), and a transcript's suffix is `.jsonl`:

```
$ python3 -c "import sys; sys.path.insert(0,'study/evals/gap-study-3'); import freeze; print(sum('/walks/' in p for p in freeze.PINNED), [p for p in freeze.PINNED if p.endswith('.jsonl')])"
24 []
```

Twenty-four sidecar files are pinned; the eight transcripts that `fixture_walk.py --check` and `mode_binding.py --walks --check` actually read are not. The rehearsed study tree binds them at the freeze commit and nothing binds them afterwards. Adding `.jsonl` to `PINNED_SUFFIXES` pins the walks and nothing else, because graded transcripts sit under `RECORD_ROOTS` and are excluded first. No reading changes.

### 4. Two definitions of the not-pinned set (NIT)

`freeze.py` defines `NOT_PINNED_AND_WHY` at line 86 with three entries and again at line 114 with one. The first builds `PINNED`; the second overwrites it afterwards, so the reasons for leaving `prereg.json` and `rounds.json` unpinned live in code that is dead by the time anyone reads the name. Nothing functional turns on it.

### 5. The publication rule promises a count the page does not print (NIT)

`publication.rule` says the earlier round's incomplete cell is marked "incomplete with its graded-take count". `result.py` line 302 prints the word `incomplete` alone, and the battery asserts the row carries no count. Round 2's own state string for that cell reads `incomplete — mechanical, 1 of 3`. Either print that string or drop the clause from the rule. No count of this round moves.

### 6. The mode reading's precedence is the pre-study's, where `default` was the anomaly (NIT)

`drive.py` `mode_recorded`, `mode_binding.mode_of` and `check_results.recorded_permission_mode` read a transcript as `default` if any record says so, whatever other records say. Under this round `default` is the expectation, so a session that recorded `default` in one record and another mode elsewhere would pass the constant-binding rule. No transcript on record has two values:

```
$ (script over 117 transcripts: round 2's, the walks', the pre-study's)
distinct permissionMode value-sets across transcripts: {('default',): 44, ('auto',): 73}
mixed: 0
```

Producing one would need a turn driven outside the pinned driver, which is the fabricated-record class. Recorded as a limitation-shaped note; a stricter reading (any value other than `default` wins) is one line in each of the three readers.

### 7. One more entry is wider than it looks, and the width of the semicolon entries is asserted rather than measured (NIT)

Limitations line 4 names the two entries ending in a semicolon and `find .`. The entry `Bash(cd "$(git:*)` admits any `git` subcommand inside the substitution and whatever follows the closing quote, and `git` is on no other entry. Separately, the claim that a semicolon entry "admits whatever follows it" is read off the entry's text; the harness splits a compound command before matching (`PROGRESS.md` slice 2 says so), under which such an entry may admit nothing at all. Either way the published denials show what the harness did, so no count is misread. `fixture_walk.py` line 61 likewise lists the roots it matches by hand; a checkout under a root not on that list would not be seen. Both are notes, not defects.

### A fact for the owner, not a finding

The green rehearsal record names the draft's sha256 correctly, but the slice-closing commit appended a line to `PROGRESS.md` after it, and the tree binding counts that file:

```
$ python3 -c "... freeze.rehearsal_problems(<draft sha>, verification, freeze.study_tree_sha('HEAD'))"
['the green rehearsal of these draft bytes (freeze-rehearsal-4.txt) ran on another study tree (f6f831851646), not this one (da485db9d5c1): a code edit after the rehearsal is a state never exercised. Run freeze_rehearsal.py again.']
```

The gate refuses honestly, and a fresh rehearsal is needed after the fixes above in any case. A line that records a green rehearsal will invalidate it every time unless `PROGRESS.md` is excluded from the binding or the line is appended before the final rehearsal.

## What was confirmed, step by step

**One change (step 5).** The driver diff against round 2's `drive.py` at `bf065fe` is exactly the five changes its docstring names: the `--allowedTools` argument on every turn, `PERMISSION_MODE = "default"`, the ledger's `permission_mode` written from the transcript with `permission_mode_passed` beside it, one display string taken from `study.py`, and `WALK_CAP = 4`. `test_nothing_is_removed_from_round_twos_driver` names every removed executable line. `COPIED.json` records 13 edits, each with a reason that matches the diff, and the ten pinned files carry equal source and copy sha256 fields: `check_take.py`, all seven graders, `graders/labels.py`, `lint_language.py` and `commit_msg.py`. The 23 keys in `carried_from_round_2` equal round 2's frozen values at the source commit (`test_it_carries_round_twos_keys_byte_for_byte`). `export_at` `844a4ce0` carries gars tree `8a54e0f8`, which is `system_under_test.gars_tree_sha`; every one of the eight walk ledgers records that tree and that export commit, harness `2.1.267`, and an `allowed_tools` list equal to the pre-registration's.

**The allowlist (step 6).** 22 entries, each a verbatim prefix of a command quoted from a named round-2 transcript and line; none a bare binary; 364 calls read, 246 admitted, 118 refused by construction and printed (109 a `cd` into a run-specific path, 3 bare `pwd`, 6 opening with shell punctuation). `allowlist.py --check` refuses a pinned entry the derivation does not produce. The two `arbitrary` entries are named as such in the file and the limitation. A denial outside the list is read by `denials.py` from the harness's own sentence in a tool result; I checked that sentence against round 2's record, where 36 transcripts carry it, and the reader returns 3 denied calls with their commands on the first of them and 0 on the walk driven under `default`.

**The fixture verdict (step 7).** `fixture_walk.py` classifies every absolute path at path boundaries, on the normalised and the resolved form, into study, run-tree, system, harness or elsewhere; `elsewhere` fails the verdict wherever it runs. Eight committed walks, every path placed, none in the study. The finding that round 2's capped cell was refused for the session's own scratch file and the harness's task-output file re-derives from round 2's bytes.

**The outcome (step 8).** The graders are round 2's bytes. `labels.reserved` takes `timed-out`, `aborted` and the stop from the ledger, and reads the final agent message only to choose between `asked-to-proceed` and `did-not-reach`, in the stated order. `run.py` writes `k` as the count of verdicts equal to the half's correct label. The permission mode a take is held to is read from its transcript by the driver, by `mode_binding.py` independently, and by the normalised re-run in `check_results.py`; the battery drives an honest drift through the pinned checker's own rule and shows the refusal survives, and shows an edit to the field alone disappears.

**Predictions and publication (step 9).** 18 predictions, each naming the round-2 results file or transcripts it read; 7 carry no count with the basis stated; the rule is in the file; all are built by code before any take. `result.py` prints counts per cell, the round-2 table beside under a caption naming condition, run date and instrument per column, and `structural_problems` holds every row of both tables to n = 3 and refuses an incomplete round-2 cell that publishes a count.

## The commands from step 3, with the tails of their output

All run from inside `study/` at the commit in `COMMIT`. Every one exited 0.

```
$ python3 -W ignore evals/gap-study-3/test_round3.py
Ran 139 tests in 44.059s
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
clean — 46 input(s) scanned, 1 excused line(s) on record

$ python3 evals/gap-study-3/lint_pooling.py evals/gap-study-3/
clean — 43 file(s) and 0 commit(s) scanned, no excusal path

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
ok: 2 registered round(s) graded, every report committed, 0 voided; prompt pinned at 0910589c8290
```

Also recorded: `shasum -a 256 prereg.json` printed the digest on line 1 of this report, and `diff prereg.json study/evals/gap-study-3/prereg-draft.json` printed nothing. The prompt sha the register pins matches `study/evals/gap-study-3/review_kit/BRIEF.md`; the brief in this folder differs from it only where the kit builder substituted the round number and the previous file's name.

## Every finding, classified

| # | Finding | Class | Would fixing it change a criterion, a reading or a claim? |
|---|---|---|---|
| 1 | The post-freeze CI gate runs neither the pin check, the ledger check nor the regrade, so a results-file edit or a misfiled last attempt moves a published count with every automatic check green; round 2's job ran the ledger check | SHOULD | No criterion, no reading. It makes the file's claim about `--ledger` true after a take, and lets the study claim its result re-derives from the takes rather than from a file. |
| 2 | `tasks_note` and `predictions_rule` say template-adherence's fixture was re-cut and name a key that does not exist; the tasks are byte-identical to round 2's | SHOULD | No criterion, no reading. Removes a false claim about a second change to the instrument from the frozen file. |
| 3 | `freeze.py` says the walks are pinned; the eight walk transcripts are not, only their sidecars | SHOULD | No criterion, no reading, no claim about a model. Makes the guard read what it says. |
| 4 | `NOT_PINNED_AND_WHY` is defined twice and the second definition is dead for pinning | NIT | Nothing. |
| 5 | The publication rule promises the earlier round's incomplete cell prints with its graded-take count; the page prints `incomplete` alone | NIT | A wording in the rule or one string on the page; no count moves. |
| 6 | `default` wins the mode reading whatever other records say; no mixed transcript exists in 117 read, and making one needs a turn outside the pinned driver | NIT | A reading only for a session shape not on record; otherwise nothing. |
| 7 | `cd "$(git` is wider than the limitation names; the semicolon entries' width is asserted from text, not measured; the path regex lists its roots by hand | NIT | A sentence in limitations line 4; no count, since denials print either way. |
