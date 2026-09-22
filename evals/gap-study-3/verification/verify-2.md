study HEAD: e2979b3143081824aadea73523ec41af30c1ddb1

# Final verification of The Gap Study, round 3, by verifier 2

**Verdict: PASS.**

Every command below was run inside `study/`, a full-depth clone with its remote removed. `git rev-list --count HEAD` returns 990 and `git rev-parse --is-shallow-repository` returns `false`. The handed `prereg.json` and the repository's `evals/gap-study-3/prereg.json` are byte-identical (sha256 a89dd108...). The commit under verification is the one `COMMIT` names, and it is two commits after the one verifier 1 read: amendment 2 and a progress line sit between them.

The verdict is PASS because every check that grades a countable thing graded the number it should have, every published count re-derives from committed bytes, and a single edited record in any of the record files is refused by a named check that CI runs. No finding below would move a criterion, a reading of a take or a count. Two lines are held to what they can honestly mean rather than to their literal wording, and each such ruling is spelled out where it is made. Every finding is classed in the closing table.

## Line 1: copy manifest and workflow diff

```
python3 evals/gap-study-3/copy_manifest.py --check
ok: 44 files trace to bf065feedccc, 13 edited with a reason, 10 pinned byte-identical; round 2, round 1, the pre-study and the parser unchanged
exit=0
```

Graded: 44 files of the 44 the manifest lists, 13 edits each with a reason, 10 pinned byte-identical. That is the manifest's own count, and the README's "thirteen files edited" sentence is held to it by the battery.

The kickoff. CI's own step names `ddf12ebc130e9d18de5ffcb429f7996ebe77baeb` as the kickoff baseline, the parent of slice 01. Against it:

```
git diff ddf12ebc130e9d18de5ffcb429f7996ebe77baeb HEAD --numstat -- .github/workflows/
145	0	.github/workflows/ci.yml
```

The kickoff file is a byte prefix of HEAD's file (212 lines then, 357 now), so the six job blocks that existed at the kickoff (`push`, `pull_request`, `tests`, `gap-study`, `gap-study-2`, `haiku-prestudy`) are byte-identical, which covers the three the line pins and three more. The one hunk sits after line 212 and adds the `gap-study-3` job. Against slice 01's own commit, `0b5e366`, the diff shows 4 removed lines, every one inside round 3's own job: commit `d51646a` rewrote the scan-since-the-kickoff step into the scan-since-the-freeze step. The additive guard therefore reads from the pre-kickoff baseline, and an edit to a line round 3 itself added is invisible to it. That is a wording finding on which commit "kickoff" names, not a change to what the pinned jobs run.

Ruling: PASS.

## Line 2: the freeze is first in the frozen file's history, and every pin hashes

```
git log --oneline --reverse -- evals/gap-study-3/prereg.json
38c0250 slice 20: the freeze — the pre-registration is frozen, seeded by review 5's commit
17e1a29 ruling: amendment 1 excuses one cost-table line the language guard misread as a percentage
07a8110 ruling: amendment 2 publishes the harness version each take ran under, because it is not balanced by model
```

The freeze is the first entry, committed 2026-09-22 12:34:19 -0400. The review commit it names, `ef6168185f5e`, was committed 2026-09-22 12:25:08 -0400 and is an ancestor of the freeze (`git merge-base --is-ancestor` returns 0). The freeze commit's parent is `4b8aae70bcd6...`, the value the frozen file records as `frozen_at_commit_parent`. The line as handed to me names no flag; the pin check that exists is `check_results.py`, which CI runs after every take:

```
python3 evals/gap-study-3/check_results.py
pinned files:
  106 pinned file(s) re-hashed
the frozen file:
  the frozen file compared with its freeze: 2 amendment(s) on record, 0 unrecorded change(s)
  the freeze commit held to its rehearsal and each pin to its committed blob: 0 problem(s)
clean
exit=0
```

Graded: 106 nodes carrying a path and a sha256, of which the `pinned_files` list holds one hundred and six more sit elsewhere in the file (fixture and review pins); the walker reads every node, so 106 is the number it should see. The frozen file's second comparison binds each pin to the FREEZE commit's blob, read from the freeze-time copy of the file, not from HEAD. At HEAD, the `git_blob_sha` recorded for `COPIED.json` and `language-allowlist.json` no longer matches either file's blob (`77834aa8` recorded, `81a5063c` at HEAD; `4b47a4ea` recorded, `49df3d7b` at HEAD), because amendment 1 moved both files' bytes and updated their `sha256` pins without touching their blob pins. No check reads `git_blob_sha` at HEAD, so this field is a record nothing grades. It is a finding on what the pin record claims, not on any reading.

Ruling: PASS.

## Line 3: every row binds to its session id and its transcript's first record

I ran `takes.py --session-id <row>` for each of the 56 rows, located the one attempt on disk whose ledger names that row, and compared three things: the ledger's `session_id`, the `sessionId` on the transcript's first record, and the row commit's committer time against the first record's timestamp.

```
python3 evals/gap-study-3/takes.py --session-id 0
row 0: confounded-design / positive / claude-haiku-4-5-20251001 / take 2
  row commit  034cad1813f81c00b7e306592df4ca119504a0e1
  session id  1ab841c9-38c5-5490-b05b-ff1e632cc6ed
(repeated for rows 1 to 55)
rows checked 56; ok 56; bad 0; graded-located 54; rehearsal-located 2; rows in file 56

python3 evals/gap-study-3/takes.py --audit
every row is committed, and no commit introduced more than one
exit=0
```

Graded: 56 rows of 56 in the file. Each derived id equals its ledger's id and its transcript's first-record id, and each row commit is earlier than its transcript's first record. Registered rows: 54 planned plus 2 re-registrations (rows 54 and 55 re-run the slots of rehearsed rows 7 and 40, within the cap of 3). The frozen file records no pre-freeze drop, so 54 graded rows against 54 planned is the equality the line asks for.

Ruling: PASS.

## Line 4: every attempt through the pinned checker

I ran `check_take.py <transcript> --task <id> --half <half> --row <row>` over every attempt on disk, 54 under `transcripts/` and 2 under `rehearsals/`.

```
python3 evals/gap-study-3/check_take.py <transcript> --task confounded-design --half positive --row 22
  turns    61 (7 from the operator)
  declared confounded-design / positive
valid — every operator-side check passed
exit=0

python3 evals/gap-study-3/check_take.py <rehearsal row 40> --task scope-read --half control --row 40
NOT VALID — 1 problem(s):
  - [read-outside-the-checkout] a tool call or its result named a path outside this session's own checkout 1 time(s) -- first: '<tmp>/sel.json'.
Keep it. Do not grade it, and do not edit it into shape.
exit=1

attempts checked 56 graded valid 54
not valid: rehearsal row 40, reasons ['read-outside-the-checkout'], WHY.md names ['read-outside-the-checkout']
not valid: rehearsal row 7, reasons ['read-outside-the-checkout'], WHY.md names ['read-outside-the-checkout']
```

Graded: 56 attempts of 56 on disk; 54 valid, 2 rehearsals whose reason ids match the reason each `WHY.md` names. There are no pauses. The checker's output does not print the permission-mode assertion by name when it passes, so I made it fire. On a copy of one graded take, outside the study, I set the ledger's `permission_mode` to `auto` and re-ran the checker: it returned `NOT VALID` with `[constant-binding] the take ran in permission mode 'auto', not the pre-registered 'default'`. The assertion is live and reads the ledger field the driver fills from the recorded mode. The second, independent reader agrees:

```
python3 evals/gap-study-3/mode_binding.py --check
ok: 56 attempt(s) graded, every one recording the mode its model is pinned to
```

Ruling: PASS.

## Line 5: the result and completeness re-derive

```
python3 evals/gap-study-3/result.py --check
graded 54 of 54
complete cells 18 of 18
ok: the result re-derives from the committed takes
exit=0

python3 evals/gap-study-3/completeness.py --check
(18 cell lines, each `3 of 3   complete`)
complete cells 18 of 18; 0 unmeasured, every one of them named with a reason
exit=0
```

Graded: 54 takes of 54 planned and 18 cells of 18 planned. No cell is unmeasured, so the reason clause has nothing to name. `check_results.py --regrade` re-derived the 3 results files byte for byte, and `costs.py --check` re-derived `COSTS.md`.

Ruling: PASS.

## Line 6: the language guards, the commit bodies, the commit-message guard, the mutation proof

```
python3 evals/gap-study-3/lint_language.py evals/gap-study-3/
clean — 57 input(s) scanned, 2 excused line(s) on record
python3 evals/gap-study-3/lint_pooling.py evals/gap-study-3/
clean — 54 file(s) and 0 commit(s) scanned, no excusal path
python3 evals/gap-study-3/lint_language.py --commits-since 38c0250612993cde0a48297ddad007fa84f58349
clean — 125 input(s) scanned, 2 excused line(s) on record
python3 evals/gap-study-3/lint_pooling.py --commits-since 38c0250612993cde0a48297ddad007fa84f58349
clean — 0 file(s) and 125 commit(s) scanned, no excusal path
```

Graded: 57 inputs and 54 files over the folder, 125 commit bodies of the 125 commits since the freeze (`git log 38c0250..HEAD | wc -l` gives 125). The copied linter's exclusion list skips pre-freeze review reports and dated verifier reports by name, and I confirmed `verify-1.md` is read (1 input scanned when passed alone), so this report will be read too.

Commit messages. I wrote each of the 125 post-freeze commit messages to a file and ran `commit_msg.py` on it: 125 checked, 0 refused; the freeze commit's own message also reads `clean`. Whether each commit was made only after its message passed is a process claim the repository cannot evidence; what it evidences is that no committed message since the freeze would have been refused.

The excusal path. The second guard has none: its file says so, it takes no allowlist, and the battery's test that feeds each forbidden sentence to it and expects exit 1 passed (`test_round3.py`: 156 tests, OK, 2 skipped). The copied language linter is a different matter. Its `excused()` function honours an allowlist entry for ANY pattern name, banned words included, and the allowlist on record carries two entries: one excuses a banned word inside a byte-exact quotation in `contract_quotes.json` (the linter's pattern for a cost claim about a local model), the other excuses the `hundred` pattern on one `COSTS.md` row. The line's sentence "the banned words ... carry no excusal path" is therefore wider than the guard: the path exists and is used, and what closes it is the per-line pin and the fact that the linter and the allowlist are both pinned, not the guard's own code. Classed below as a claim finding.

The page scan. CI also runs `lint_pooling.py --section-of docs/EVALS.md`. At HEAD it prints `no section yet ... this scan has read nothing and claims nothing. Not a pass.` and exits 0. `docs/EVALS.md` carries the `gap-study-2` and `gap-study` summary blocks and no `gap-study-3` block. That step graded 0 items of the 1 section it exists to read, and says so. The line as written scopes the guard to the folder and the commit bodies, both of which graded their full count, so the line holds; the empty page scan is a finding of its own, because the README says the limitation the frozen file cannot carry lives "in the owner's `docs/EVALS.md` section", and at this commit no such section exists.

Ruling: PASS, with two findings.

## Line 7: CI green at the commit

```
python3 evals/gap-study-3/ci_conclusion.py e2979b3143081824aadea73523ec41af30c1ddb1 --gh-json ci-at-commit.json
  completed    success          CI
e2979b314308: 1 run(s), every one completed with success (exit 0)
```

Graded: 1 run of the 1 the record holds, and that record is the run's, read from GitHub before I opened, not mine: I have no network remote and could not query the forge. The record names the workflow `CI` and its conclusion; it does not name the `gap-study-3` job, so "green on the study's own job" is inferred from the workflow being green, which requires every job to be. The full-depth claim rests on the workflow file, which sets `fetch-depth: 0` for the round 3 job and on `check_results.py`, which refuses a shallow clone by name. I ran every step of the round 3 job locally that does not need the forge (copy, additive diff, suite, both guards, page scan, commit bodies, derivation, draft, leak verdict, leak list, permission mode, review register, pins, ledger, regrade, result, completeness, costs, denials) and each exited 0.

Ruling: PASS on the run's record.

## Line 8: prose files, status lines, and the keys named "at freeze"

```
grep -rn "^status:" --include=*.md evals/gap-study-3/
(no output)
find evals/gap-study-3 -name '*.md' | wc -l
16
grep -n "status:" evals/gap-study-3/test_round3.py
(no output)
```

Graded literally: 0 prose files of 16 carry a `status:` line, and no test in the pinned battery asserts one. The battery is among the one hundred pinned files, so no such test could have been added after the freeze without failing line 2. The line cannot honestly mean a literal status line. What it can mean, and what I graded:

- Code-written prose re-derives. `RESULT.md` by `result.py --check` and `COSTS.md` by `costs.py --check`, both exit 0 above. The `WHY.md` beside each rehearsal is written by the driver and its reason ids match the checker's output (line 4).
- Hand-written prose is held sentence by sentence by the pinned battery, not by a status line. The battery asserts named sentences of `README.md` (the edited-file count, the five driver changes, the byte-identical usage-line warning, the limitation section), the enforcement text of the frozen file, and `verification/finding.md` against `fixture_walk.py --finding`. `PROGRESS.md`, the review reports, the gate card and the commit-body note are append-only records that no check re-derives and no test binds; the line's demand that they carry an asserted status is unmet and unmeetable at this commit.
- The keys named "at freeze". Four exist. `system_under_test.gars_tree_sha_at_freeze` equals `git rev-parse 38c0250:gars` (e77b9031...), and the tree is unchanged at HEAD. `harness.claude_version_at_freeze` is `2.1.267 (Claude Code)`, the version the freeze rehearsal recorded, and it keeps that value although 24 of 54 takes later ran on 2.1.280, which is what "at freeze" should mean. `draft_sha256_at_freeze` equals the sha256 of `prereg-draft.json` at HEAD (9930913c...), and a battery test holds it there. `nulls_at_freeze` is the freeze's own count of 22 with an empty `unaccounted` list.

Ruling: PASS on that reading, with the wording classed as a finding below.

## Line 9: this verification

- A fresh clone. `COMMIT` records the source address and the sha; the clone has 990 commits, is not shallow, has no remote, and its HEAD is the sha `COMMIT` names. The handed `prereg.json` matches the repository's copy byte for byte.
- A committed blindness record and a report committed unedited. For verifier 1 both are in the history: register row `946503d` committed alone, then `8667eb7` carrying `verify-1.md` and `verify-1-blindness.txt` together, with the blindness record reading 0 unexplained on every marker. For this verification the row, the report and the blindness record are commits that come after the commit I read, so I cannot verify them from here; I can only say that this report is what I wrote.
- The two verifiers did not read the same commit. Verifier 1's report opens `study HEAD: 20379046effb...`; mine opens with `e2979b3143...`. Between them sit amendment 2 (`07a8110`) and a progress line (`e2979b3`), and the checklist's own note says both verifiers verify the SAME commit. That note is wrong at this commit, for a good reason: verifier 1's first finding became amendment 2, and the owner's ruling was to re-verify the amended bytes. The sequence after verifier 1's commit is amendment, progress line, and then the commits this round adds. Whether that satisfies "the only commits after the verified commit are the two reports" depends on which commit is "the verified commit". Read as the commit I verify, the sequence that follows is forced by the register to be row, report, blindness, and I cannot see past HEAD. Read as verifier 1's commit, the line is not met, and the study's own record says so in slice 26. Classed below.
- The register's prompt pin. `rounds.py` records `prompt_sha256` as the hash of `review_kit/BRIEF.md`, the pre-freeze reviewer brief, for verify rows too. The brief a verifier is handed is a different document (mine hashes to 26e675d3..., the pinned one to 0910589c...). The verifier's brief is bound only through `input_sha256`, the digest of the whole handed folder, so nothing is unbound, but the field is mislabelled for verify rows.

Ruling: PASS on what a verifier can see, with two wording findings.

## The four answers

**1. Takes graded of planned, and cells complete of planned.** From `result.py --check`: graded 54 of 54, complete cells 18 of 18. From `completeness.py --check`: 0 unmeasured. No cell publishes as anything but complete, so there is no cell to name and no reason to quote. Two slots were rehearsed and re-registered (rows 7 and 40, re-run as rows 54 and 55), each for `read-outside-the-checkout`, each the session's own scratch file under the system temp root, the case limitation 10 names. 22 of 54 graded takes carry a harness denial with the command quoted; `denials.py --check` reads 54 graded takes and prints each.

**2. Every amendment to the frozen file.** `check_results.py` reports 2 amendments on record and 0 unrecorded changes.

- Amendment 1 (`17e1a29`, Ruling 13). Before: the language guard refused one `COSTS.md` row under its `hundred` rule, a take that sent exactly one hundred input tokens. After: that exact line is excused. What it changed in the frozen file: two `sha256` values inside `pinned_files` were rewritten in place (`COPIED.json` and `language-allowlist.json`), and the `amendments` list was appended. Outside the frozen file, one `copy_sha256` field in `COPIED.json`, one allowlist entry, and the amendments section of `RESULT.md`. Did it change a reading: no. The language guard feeds no grader; I re-ran the regrade, the result and completeness at HEAD and each re-derives. The two `git_blob_sha` values beside the rewritten `sha256` values were left at their freeze-time values, which is the stale-field finding under line 2.
- Amendment 2 (`07a8110`, Ruling 14). Before: the frozen file names 2.1.267 as the harness and nothing published said part of the takes ran on another version. After: the version each graded take ran under is published by model and by cell. What it changed in the frozen file: an appended amendment only, 44 added lines and 0 deleted. I re-derived its numbers from the 54 driver ledgers: 30 takes on 2.1.267 and 24 on 2.1.280; by model, the smallest model 15 and 3, the largest 7 and 11, the middle one 8 and 10; 4 cells on one version, 14 on both, the same four cells the amendment names. By order position, the last 2.1.267 take is position 30 and every position from 31 ran on 2.1.280, as the amendment says; position 7's re-drive (row 54) also ran on 2.1.280, which agrees with the restart time, since that slot was driven last. Did it change a reading: no. No count moved, and the frozen `harness` key still says a later harness version "is a limitations line printing the range, never an amendment". The amendment records more than that note promised, not less, but the frozen file now disagrees with itself about the form such a record takes. Classed below.

**3. Every language excusal on record, and the exact line each forgives.** Two, both in `language-allowlist.json`, both pinned to a file, a pattern name and the exact line text.

- `contract_quotes.json`, line 134, the linter's pattern for a cost claim about a local model. The line is a byte-exact quotation of the system under test's own contract about its plan gate, pinned by blob sha. The pinned text matches exactly one line of the file at HEAD.
- `COSTS.md`, line 27, pattern `hundred`. The per-take cost row for confounded-design, positive half, claude-opus-5, take 1, whose input column reads one hundred tokens. The pinned text matches exactly one line of the file at HEAD, and `costs.py --check` re-derives the file, so the line is the transcript's own count.

No excusal's pinned text has moved: each matches exactly one line, and the guard reports both as on record with 0 findings.

**4. Whether any published count could be moved by a single edited record.** No, not without a named check going red. I copied the clone to a scratch folder beside it, edited one record at a time, ran the check that should catch it, and restored the copy each time. The scratch folder is deleted.

| edited record | check | what it printed |
|---|---|---|
| a cell's `k` in `results/scope-read.json`, 0 to 1 | `check_results.py --regrade` | `scope-read.json did not re-derive byte-identically`, exit 1; and `result.py --check` printed `complete cells 17 of 18` and `FAIL RESULT.md is not what this file writes`, exit 1 |
| one held count in `RESULT.md` | `result.py --check` | `FAIL RESULT.md is not what this file writes from the committed takes`, exit 1 |
| a ledger's `claude_version` | `check_results.py --ledger` | `row 55: the graded take carries no valid environment record ... environment.json records harness '2.1.280' and the ledger records '2.1.267'`, exit 1 |
| a ledger's `permission_mode` alone, to `auto` | `check_results.py --ledger` | `row 55: the graded take does not pass the take checker (['constant-binding'])`, exit 1: the checker re-runs and the edit is refused as ledger-made |
| one appended byte on a transcript | `check_results.py --ledger` | `row 55: the transcript's bytes are not the ones its ledger records as published`, exit 1 |
| a row's `take` number in `takes.json` | `check_results.py --ledger` | two problems: the attempt's folder is not the one the row names, and the row is not the one the pre-registered order puts at that position, exit 1. Note that `takes.py --audit` alone still printed `every row is committed`, exit 0: the audit binds rows to commits, not to the order, so the ledger check is the one that catches this |
| a graded attempt moved under `rehearsals/` | `check_results.py --ledger` | `the attempt sits under the rehearsal folder and its ledger records 'graded'`, `a rehearsal carries no WHY.md`, `the take checker passes this attempt, so it is a graded take filed as a rehearsal`, exit 1 |

Each of these runs in CI's "Round 3 pins, ledger and regrade" and "Round 3 result" steps after every take.

## The three things the run already knew it must answer for

- **Line 2 and the flag.** The line handed to me names no flag; it asks that "every pinned file hashes as the freeze recorded it", and `check_results.py` is the command that does that, run above. If the goal file's own wording names a flag the frozen code lacks, the wording is what failed, not the code: the code's pin check exists, runs in CI after every take, ran in every freeze rehearsal, and reads 106 nodes. Neither changes a reading.
- **Line 8 and the status line.** Ruled above: a literal status line asserted by a named test cannot exist because the battery is pinned, so the line can only mean that code-written prose re-derives and hand-written prose is held sentence by sentence by tests that predate the freeze. That is what the commit does, and the "at freeze" keys hold their freeze values. Neither changes a reading.
- **Line 9 and the forced sequence.** The register forces row, report, row, report, and that alone would satisfy the line's intent. But the two verifiers did not read the same commit: an amendment and a progress line sit between verifier 1's commit and mine, by the owner's ruling to re-verify amended bytes. The line as written is not met for verifier 1's commit and cannot be checked for mine from inside it. It changes no reading, because amendment 2 moved no count, and I re-derived that at HEAD.

## What the checks bind and what they cannot

Read against the frozen file's eleven limitations and the README's twelfth, these are limitations, not findings, because each could only be closed by a record this repository cannot carry:

- The recorded permission mode binds what the session reported, not what the harness enforced (limitation 9). `mode_binding.py` reads 56 attempts and every one records `default`; a harness that recorded one mode and applied another would pass it.
- No session file records `--allowedTools` (limitation 3); the evidence that the list applied is that 22 of 54 graded takes met a denial with the command quoted and 32 did not.
- A take re-driven after the harness's own session file was deleted would leave a record nothing here distinguishes from the first (README, Ruling 12). The line 3 binding I ran proves "committed before its session opened", and no more.
- 22 graded takes carry a harness denial, and several cells hold 0 of 3. A denial is published as a condition of the harness with its command quoted (limitation 8), and whether a held count would differ under another condition is not a question this round's instrument can answer.
- Amendment 2's harness split is now published; that a difference between models may carry a difference of harness is the amendment's own sentence and is not a finding beyond it.

## Findings

| # | Finding | Class | Would fixing it change a criterion, a reading or a claim? |
|---|---|---|---|
| 1 | Line 6 says the banned words carry no excusal path; the copied linter's `excused()` honours an allowlist entry for any pattern name, and two such entries are on record, one on a banned word. What closes the path is the per-line pin plus the pinned linter and allowlist, not the guard. | SHOULD | A claim only: the sentence should say what closes the path. No criterion, no reading. |
| 2 | After amendment 1, the `git_blob_sha` pins for `COPIED.json` and `language-allowlist.json` in the HEAD frozen file are freeze-time blobs that match neither file at HEAD, and no check reads that field at HEAD; the pin record claims more than any guard grades. | SHOULD | A claim in the pin record; an amendment recording the new blobs would move no criterion and no reading. |
| 3 | The README says the limitation the frozen file cannot carry lives in the owner's `docs/EVALS.md` section; at this commit the page has no round 3 section, and CI's page scan grades 0 items and prints "Not a pass". | SHOULD | A claim in the README, false at this commit; writing the section changes no criterion and no reading. |
| 4 | Line 8 asks every prose file for a `status:` line asserted by a named test; 0 of 16 carry one and the pinned battery cannot gain such a test. Hand-written records (`PROGRESS.md`, the review reports, the gate card, the commit-body note) are bound by nothing but append-only convention. | SHOULD | The line's wording; the code-written files re-derive and the "at freeze" keys hold. No reading. |
| 5 | The checklist's note that both verifiers verify the same commit is false at this commit: verifier 1 read `20379046effb` and this report reads `e2979b3143...`, with amendment 2 and a progress line between them. | SHOULD | A claim in the checklist's note and in line 9's wording; the amendment between the two commits moved no count. |
| 6 | The frozen `harness` key says a later harness version is "a limitations line printing the range, never an amendment"; amendment 2 records exactly that as an amendment, and no limitations line prints the range. The frozen file disagrees with itself about the form. | NIT | A claim about form; the amendment publishes more than the note promised. No reading. |
| 7 | Line 1's "added lines only" holds from the parent of slice 01, the sha CI names; from slice 01 itself, 4 lines were removed inside round 3's own job, so the additive guard cannot see an edit to a line round 3 added. | NIT | The line's wording, to name which commit "kickoff" is; the six pre-existing job blocks are byte-identical either way. |
| 8 | `RESULT.md`'s caption says "The instrument is the same and the permission condition is not", while the Outcome paragraph and the README call the earlier round "a different instrument"; the word carries two meanings across the study's own prose. | NIT | A claim in wording; the two tables print apart under either meaning. |
| 9 | Each `results/*.json` records `evals/gap-study-2/graders/...` as its `grader`; the README says only docstrings still name round 2's folder, which is one printed field wider than true. The grader that ran is this folder's byte-identical copy. | NIT | A claim in the README; the bytes are identical by manifest, so no reading. |
| 10 | The register's `prompt_sha256` for verify rows is the hash of the pre-freeze reviewer brief, not the verifier brief handed; the verifier brief is bound only through `input_sha256` of the whole folder. | NIT | A claim in the register's field name; nothing is unbound. |
| 11 | `takes.py --audit` passes a row whose `take` number was edited; only `check_results.py --ledger` refuses it. The audit's own print reads wider than what it binds (rows to commits). | NIT | Neither: the ledger check runs in CI after every take and catches it. |
