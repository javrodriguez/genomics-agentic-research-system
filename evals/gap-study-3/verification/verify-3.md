study HEAD: e2979b3143081824aadea73523ec41af30c1ddb1

# Final verification of The Gap Study, round 3 (verifier 3)

**Verdict: PASS.**

Every command below was run inside `study/`, a full-depth clone with its remote removed: `git rev-list --count HEAD` returns 990 and `git rev-parse --is-shallow-repository` returns `false`. The handed `prereg.json` and the repository's `evals/gap-study-3/prereg.json` are byte-identical (`cmp` printed nothing; both hash to `a89dd1081fc5...`). The tree was clean before and after every mutation test below (`git status --short` printed 0 lines at the end; each mutated file was restored with `git checkout --`).

The verdict is PASS because every check that grades a countable thing graded the number it should have, every published count re-derives from committed bytes, every single-record edit I tried was caught by a named check except one that feeds no count, and no finding raised below would move a criterion, a reading of a take or a count. Two checklist lines pass on a corrected reading of their wording rather than as written; each is said so in its section and classified in the closing table.

## Line 1 — copy manifest and workflow diff

```
python3 evals/gap-study-3/copy_manifest.py --check
ok: 44 files trace to bf065feedccc, 13 edited with a reason, 10 pinned byte-identical; round 2, round 1, the pre-study and the parser unchanged
exit=0
```

Graded 44 of 44 copied files (the manifest's own count, and `COPIED.json` holds 44 entries with 13 marked edited), 13 of 13 edits with a reason, 10 of 10 pinned files byte-identical.

The workflow diff, measured from the commit CI's own step names as the kickoff (`ddf12ebc...`, the parent of slice 01):

```
git diff --numstat ddf12ebc130e9d18de5ffcb429f7996ebe77baeb HEAD -- .github/workflows/
145	0	.github/workflows/ci.yml
```

Added lines only. I split both versions of `ci.yml` into job blocks by code and compared them: the header and the `tests`, `gap-study` and `gap-study-2` blocks are byte-identical between that commit and HEAD, and the `haiku-prestudy` block differs by exactly one added trailing blank line, the one that now separates it from the block below it. So 4 of 4 pre-existing blocks are unchanged in content and the three pinned blocks the line names are byte-identical whichever three it means. Measured from slice 01's own commit (`0b5e366...`) instead, the diff is 69 added and 4 removed, and all 4 removed lines sit inside round 3's own job, being slice 8's scoping of the commit-body scan. **Ruling: PASS.** Which commit "kickoff" names is a NIT in the table.

## Line 2 — the freeze is first, and every pin hashes

```
git log --format='%h %ci %s' --reverse -- evals/gap-study-3/prereg.json
38c0250 2026-09-22 12:34:19 -0400 slice 20: the freeze — the pre-registration is frozen, seeded by review 5's commit
17e1a29 2026-09-22 17:17:05 -0400 ruling: amendment 1 excuses one cost-table line the language guard misread as a percentage
07a8110 2026-09-22 18:07:25 -0400 ruling: amendment 2 publishes the harness version each take ran under, because it is not balanced by model
```

The freeze is the first entry. It names review 5's commit `ef61681`; `git merge-base --is-ancestor ef6168185f5e 38c0250` succeeds, and the committer dates read 12:25:08 for the review and 12:34:19 for the freeze on 2026-09-22. The frozen file's `frozen_at_commit_parent`, `4b8aae7`, is the freeze commit's parent (`git rev-parse 38c0250^` agrees) and is the sixth rehearsal, committed at 12:33:37 between them.

The line names a flag the frozen code does not carry. The pin check that exists is `check_results.py`:

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

Graded 106 of 106 nodes carrying a path and a sha256 (the `pinned_files` list holds one hundred entries; six more such nodes sit elsewhere in the frozen file). Comparing the frozen file at HEAD with its bytes at the freeze commit by code, the only top-level keys that differ are `amendments` and `pinned_files`, and within `pinned_files` only the two entries amendment 1 records. **Ruling: PASS on the code; the checklist's wording is what failed.** The pin check the line means is `check_results.py`, which CI runs after every take and the sixth rehearsal ran before the freeze. The wording is a NIT below.

Carried from verifier 1 and still true after amendment 2: the pins for `language-allowlist.json` and `COPIED.json` carry the new sha256 but the freeze-time `git_blob_sha`, and my own comparison of every pinned entry against `git rev-parse HEAD:<path>` finds exactly those 2 of one hundred with a blob that is not the file's blob at HEAD. The pin check reads the blob field at the freeze commit, where it is right. SHOULD below.

## Line 3 — every row, its session id, and its order

```
python3 evals/gap-study-3/takes.py --audit
   55  scope-read             control  claude-opus-5                take 1  d30ae88c547f  1df163f4-8c09-55bb-b112-c2427747c990  graded
every row is committed, and no commit introduced more than one
```

Then, by my own code, for each of the 56 rows: read the commit that introduced the row by walking every commit touching `takes.json` oldest-first; run `python3 evals/gap-study-3/takes.py --session-id <row>`; find the folder whose `driver-ledger.json` names that row, under `transcripts/` for a graded row or `rehearsals/` for a rehearsed one; read every `sessionId` and `timestamp` in that transcript; and compare the row commit's committer date with the earliest record:

```
rows 56 row commits 56 kinds {'graded': 54, 'rehearsal': 2}
rows with no transcript carrying their row number: []
rows whose derived id is NOT in their transcript: []
rows whose commit is NOT earlier than transcript first record: []
```

Graded 56 of 56 rows; 56 of 56 carry a transcript recording the derived id; 56 of 56 have their row committed before the transcript's first record. Registered rows are 56 against a planned 54. The frozen file records no pre-freeze drop of a take (its only key with "dropped" in the name is a leak word). The two extra rows are 54 and 55, which re-register the slots of rows 7 and 40 after each became a rehearsal, exactly as the frozen `attempt_layout.rule` admits: "a slot is registered again only after an attempt that became a rehearsal or a pause". Graded rows are 54 of 54 planned. **Ruling: PASS.**

## Line 4 — the take checker over every attempt

The loop CI runs, reading task, half and row from each take's own ledger:

```
for t in evals/gap-study-3/transcripts/*/*/*/*/transcript.jsonl; do ... python3 evals/gap-study-3/check_take.py "$t" --task "$task" --half "$half" --row "$row"; done
graded transcripts checked: 54, failed: 0
valid — every operator-side check passed
```

Graded 54 of 54. The two rehearsals, which CI's loop does not visit, run the same way:

```
python3 evals/gap-study-3/check_take.py evals/gap-study-3/rehearsals/scope-read/control/claude-opus-5/row-40/transcript.jsonl --task scope-read --half control --row 40
NOT VALID — 1 problem(s):
  - [read-outside-the-checkout] a tool call or its result named a path outside this session's own checkout 1 time(s) -- first: '<tmp>/sel.json'.
exit=1
```

Row 7 reads the same with reason `read-outside-the-checkout`, first path `<tmp>/gars_finalize_run-37bf736b.json`. Each rehearsal's ledger records `{'kind': 'rehearsal', 'reasons': ['read-outside-the-checkout']}` and its `WHY.md` names that one reason id with the command that reproduces it. Pauses: 0, and `check_results.py --ledger` agrees (`54 graded, 2 rehearsal(s), 0 pause(s), 0 not attempted`). So 2 of 2 rehearsals carry their reason ids, and 0 of 0 pauses.

The permission-mode assertion is live. I set `permission_mode` to `auto` in the ledger of scope-read, control, claude-opus-5, take 1 and re-ran the checker:

```
  - [constant-binding] the take ran in permission mode 'auto', not the pre-registered 'default'
exit=1
```

then restored the file. `mode_binding.py --check` reads `passed=default recorded=default expected=default` on 56 of 56 attempts. **Ruling: PASS.**

## Line 5 — the result and completeness

```
python3 evals/gap-study-3/result.py --check
graded 54 of 54
complete cells 18 of 18
ok: the result re-derives from the committed takes
exit=0

python3 evals/gap-study-3/completeness.py --check
  ... 18 rows, each `3 of 3   complete`
complete cells 18 of 18; 0 unmeasured, every one of them named with a reason
exit=0
```

Graded 54 of 54 planned takes and 18 of 18 planned cells. **Ruling: PASS.**

## Line 6 — the language guards, the commit messages, the second guard's proof

```
python3 evals/gap-study-3/lint_language.py evals/gap-study-3/
clean — 57 input(s) scanned, 2 excused line(s) on record
exit=0

python3 evals/gap-study-3/lint_pooling.py evals/gap-study-3/
clean — 54 file(s) and 0 commit(s) scanned, no excusal path
exit=0
```

Commit bodies since the freeze, three ways. `git rev-list 38c0250..HEAD` lists 125 commits. The scan CI itself runs:

```
python3 evals/gap-study-3/lint_language.py --commits-since 38c0250612993cde0a48297ddad007fa84f58349
clean — 125 input(s) scanned, 2 excused line(s) on record
python3 evals/gap-study-3/lint_pooling.py --commits-since 38c0250612993cde0a48297ddad007fa84f58349 evals/gap-study-3/
clean — 54 file(s) and 125 commit(s) scanned, no excusal path
```

I also wrote each body to a scratch file and ran `commit_msg.py` on it: 125 checked, 0 refused. And `lint_language.py` on each body the same way: 125 scanned, 0 refused. To prove the linter reads a body file I appended one line carrying a slashed count and a banned absolute to a copy of HEAD's body, and it was refused with exit 1 under `[ratio-slash]` and the rule against the banned absolute. Graded 125 of 125 commit bodies under each guard, 57 of 57 inputs in the folder under the copied linter, and 54 of 54 files under the second guard.

"Every commit is made after its message passes `commit_msg.py`": the repository wires that check into `review_kit/commit_review.py` for review commits; the take commits were made by an operator script the repository does not carry. What I can verify is that 125 of 125 messages pass it now; that each passed before its commit is the run's word. NIT below.

The second guard is mutation-proved: the battery's class `ThePoolingGuardIsMutationProved` passes within `test_round3.py` (`Ran 156 tests ... OK (skipped=2)`, both skips being draft-only rules the freeze retires), and my own sentence joining the two rounds' counts into one figure was refused with `[both-rounds]` and `There is no allowlist for these.`

The claim that the banned words carry no excusal path reads more than the copied guard does, and I proved it by mutation. A scratch line carrying a banned absolute was refused; I then appended an allowlist entry for that file, that pattern and that line to `language-allowlist.json` and the same scan read `clean — 1 input(s) scanned, 3 excused line(s) on record`; `check_results.py` then went red with `language-allowlist.json does not match its pinned sha256`, and I restored the file. So what closes the path is the pin on the allowlist, not the linter; `commit_msg.py` alone consults no allowlist. SHOULD below. **Ruling: PASS**, with that overstatement on record.

The count the linter prints, `2 excused line(s) on record`, is the size of the allowlist, not the number applied on that scan. Both pinned lines are present: `grep -c -F` of the contract quotation returns 1 in `contract_quotes.json`, and the cost row is line 27 of `COSTS.md`.

## Line 7 — CI green at full depth

This is the run's record, not mine: `ci-at-commit.json` was read from GitHub before I opened, and I have no network. The study's own reader on it:

```
python3 evals/gap-study-3/ci_conclusion.py e2979b3143081824aadea73523ec41af30c1ddb1 --gh-json ../ci-at-commit.json
  completed    success          CI
e2979b314308: 1 run(s), every one completed with success (exit 0)
```

Graded 1 of 1 run at the verified sha (workflow `CI`, event `push`, run 35790998543, created 2026-09-22T22:11:26Z). The record is workflow-level; the workflow holds five jobs and a success conclusion requires each, so the study's own job `gap-study-3` succeeded. That job checks out with `fetch-depth: 0`. To corroborate the record rather than rely on it alone, I ran every step of that job locally at HEAD: the copy check, the workflow diff, the battery, both guards over the folder, the section scan of the public page, the commit-body scans, `allowlist.py --check` (22 of 22 entries re-derive from 364 pre-probe calls in 52 transcripts), `build_draft.py --check`, the three `fixture_walk.py` verdicts (8 of 8 walks placed), `leak_grep.py --check` (23 words against 64 sessions, none would void one), both `mode_binding.py` checks, `rounds.py --check`, the take loop, the pins, ledger and regrade, and the result and completeness checks. Every one exited 0. **Ruling: PASS on the run's record, corroborated locally.**

## Line 8 — every prose file re-derived or asserted

Prose files in the study folder (`.md` and `.txt`, excluding cases, fixtures and walks): 27. Lines matching `status:` in them:

```
grep -rn "^status:\|status: " --include=*.md --include=*.txt evals/gap-study-3 | grep -v "/cases/\|/fixtures/\|/walks/"
(no output)
```

So 0 of 27 prose files carry a `status:` line, and no test in the battery, pinned at the freeze, asserts one. As written, the line's second clause graded nothing.

What the line can honestly mean here, and what I ran for it. Files code writes re-derive by a check: `RESULT.md` by `result.py --check` (clean; and when I changed one published count from `0 of 3` to `1 of 3` it failed with `RESULT.md is not what this file writes from the committed takes`, then I restored it); `COSTS.md` by `costs.py --check` (clean; and when I changed one token count it failed with `COSTS.md is NOT what the reader writes`); the two rehearsal `WHY.md` files by `check_take.py`, whose output each reproduces. That is 4 of 27 re-derived. Three more are bound by a named check against a commit: `freeze-rehearsal-6.txt` by `check_results.py` ("the freeze commit held to its rehearsal"), `verify-1-blindness.txt` by `rounds.py --check`, which requires it to name the session id its row's commit derives, and `README.md` by three battery tests that read its manifest sentence, its five-change list and its check list. The other 20 are hand-written records the run wrote once and nothing binds: `PROGRESS.md`, the four pre-freeze reports with their blindness records, the review brief and its purpose page, the gate card, the finding note, the commit-body note, the first five freeze rehearsals, and verifier 1's report.

Keys named "at freeze", each compared by code with its value in the freeze commit's bytes: `system_under_test.gars_tree_sha_at_freeze` is `e77b9031...` and equals `git rev-parse 38c0250:gars`; `draft_sha256_at_freeze` equals the sha256 of `prereg-draft.json` on disk; `harness.claude_version_at_freeze` is `2.1.267 (Claude Code)` in both; `nulls_at_freeze` is identical in both, 22 declared with an empty `unaccounted` list. So 4 of 4 hold their freeze value.

**Ruling: PASS on the honest reading** (code-written files re-derive, the bound records are bound, and the "at freeze" keys hold), **not met as written** (0 status lines). The wording is classified below and does not move a reading.

## Line 9 — this verification

A fresh clone: yes, full depth, 990 commits, remote removed, HEAD at the sha on line 1 of this report, matching `COMMIT`. A committed blindness record and a report committed unedited: neither can exist at the commit I verify, because the register's rule commits my row after it and my report after that. The register at HEAD holds 5 `prefreeze` rows and 1 `verify` row:

```
python3 evals/gap-study-3/review_kit/rounds.py --check
1 row(s) closed as spent without work (a rate limit or an interruption before the first agent turn). Not voids: they do not count against the two-void rule.
ok: 5 registered round(s) graded, every report committed, 0 voided; prompt pinned at 0910589c8290
exit=0
```

Graded 5 of 5 live rounds with a committed report and 1 of 1 row spent without work. For verifier 1's round I re-derived the binding by hand: its row was committed alone in `946503d` (one file, 9 insertions) after the commit it verified, `2037904`; `uuid5` of the study's namespace and that row commit's sha is `22f1eedb-eda7-5268-807a-a5b4519d0844`, which is the session id on line 2 of `verify-1-blindness.txt`; and `git log -- verification/verify-1.md` shows exactly one commit, `8667eb7`, so the report has not been edited since it was committed. What binds my own row is the same code. **Ruling: PASS on what can be checked from inside the verified commit; the rest is the run's to commit and this same check's to hold.**

## The three things the run already knows

**Line 2's flag.** The frozen `freeze.py` carries no `--verify-pins`; `check_results.py` with no arguments is the pin check, it ran clean above over 106 nodes, the sixth rehearsal ran it before the freeze and CI runs it after every take. The wording failed, not the code. It changes no reading.

**Line 8's status lines.** No prose file carries one and the pinned battery cannot gain a test, so the line can only honestly mean what its first clause says: a code-written file re-derives by a `--check`, and a record that is not code-written is bound by a named check to a commit where such a check exists. I ruled on that reading above and named the 20 files nothing binds. It changes no reading: none of the 20 carries a count.

**The commits after the verified commit.** DONE asks that the only commits after it be the two reports. The register forces row, report with its blindness record, row, report, and verifier 1's earlier round means three verifier reports exist in the end rather than two. Every one of those commits is a verifier's own record; none touches a take, a result, a pin or a criterion, and `rounds.py` refuses a second row while the first has no report, so the sequence is the register's, not the run's choice. My clone ends at the verified commit, so I cannot see verifier 2's row or report and take their existence from the checklist's own statement. I read the sequence as satisfying the line's purpose and not its letter; the letter should say "the verifier rows, reports and blindness records". NIT below. It changes no reading.

## The four answers

**1. Takes graded of planned, cells complete of planned.** From `result.py --check`: graded 54 of 54, complete cells 18 of 18. From `completeness.py --check`: 18 of 18 complete, 0 unmeasured. No cell publishes unmeasured, so there is no cell to name. Behind them: 56 rows, 54 graded, 2 rehearsals (rows 7 and 40, each refused for `read-outside-the-checkout` on the session's own scratch path and re-registered as rows 54 and 55), 0 pauses; and `denials.py --check` reads 22 of 54 graded takes met a harness denial, each printed with its command under the result's Denials heading.

**2. Every amendment to the frozen file.** Two, and `check_results.py` reads `2 amendment(s) on record, 0 unrecorded change(s)`.

- Amendment 1 (Ruling 13, 2026-09-22, at 54 of 54 takes, commit `17e1a29`) appended one line-exact excusal to `language-allowlist.json` for line 27 of `COSTS.md`, whose input column reads exactly one hundred tokens, which the copied linter's `hundred` rule had refused as a percentage. It moved that file's pin from `c9acc416...` to `460b4857...` and the one field of `COPIED.json` that records the allowlist's copy hash, from `acaea2a5...` to `12ce6455...`; the commit touched those two files, the frozen file and `RESULT.md`. Did it change a reading? No. The language guard feeds no grader; at HEAD the result, completeness, ledger and regrade checks read clean and the regrade re-derives 3 of 3 results files byte-identically.
- Amendment 2 (Ruling 14, 2026-09-22, at 54 of 54 takes, commit `07a8110`) records that the harness was restarted between order positions 30 and 31 and installed Claude Code 2.1.280, so 30 graded takes ran on the frozen 2.1.267 and 24 on 2.1.280, unbalanced by model. It touched the frozen file and one line of `RESULT.md`, moved no pin (`files: []`) and no transcript byte. Did it change a reading? No: no grader, label, route or checker is touched, and the three checks above read the same. I re-derived every figure in its `harness_versions` block from the 54 graded ledgers' own `claude_version` field by code: 30 and 24; by model 15 and 3, 8 and 10, 7 and 11; the 4 cells on one version and the 14 on both, named identically; and the switch falling exactly between row 30 and row 31. Every figure matches. Two residues are findings: no committed check re-derives that block, though its text says "derived from those ledgers by code", so the table is bound by my re-derivation and not by the repository's; and the frozen `harness.note` says a later version is "a limitations line printing the range, never an amendment", while the pinned result writer prints no such line, so the amendment path was the only one left and the frozen file's own rule on the vehicle was departed from in form. Both are SHOULD below; neither moves a count.

**3. Every language excusal on record.** Two, both in `language-allowlist.json`, and I confirmed each pinned line is still present verbatim:

- `contract_quotes.json`, the pattern named for the word the system under test uses of drafting a plan, ruled 2026-09-19: forgives the line quoting the plan-gate sentence byte for byte, the one that says drafting is not gated and running is. `grep -c -F` of the pinned text returns 1.
- `COSTS.md`, pattern `hundred`, ruled 2026-09-22 by amendment 1: forgives line 27, the per-take cost row for confounded-design, positive half, claude-opus-5, take 1, whose input column reads exactly one hundred. `grep -n -F` of the pinned text returns line 27.

Neither excusal's text has moved. The linter's `excused()` matches file, pattern name and exact line text together, so a moved line brings its finding back rather than hiding it; when I changed that cost row's count the linter still read clean on the edited line only because the new number no longer matched the `hundred` rule, and `costs.py --check` refused the edit.

**4. Could a single edited record move a published count?** I tried ten single-record edits, restoring each with `git checkout --`:

- One cell's `k` in `results/scope-read.json`: `result.py --check` failed (`RESULT.md is not what this file writes from the committed takes`) and `check_results.py --regrade` failed (`scope-read.json did not re-derive byte-identically`).
- One published count in `RESULT.md`, `0 of 3` to `1 of 3`: `result.py --check` failed with the same sentence.
- One token count in `COSTS.md`: `costs.py --check` failed.
- One byte appended to a graded transcript: `check_results.py --ledger` failed (`row 55: the transcript's bytes are not the ones its ledger records as published`).
- One field of a row in `takes.json`, take 1 to take 2: `--ledger` failed (`its graded attempt sits at ... which is not the folder its row names`).
- One ledger field, `permission_mode` to `auto`: `check_take.py` refused with `[constant-binding]`, and `--ledger` refused the take as not passing the checker.
- One ledger field, `claude_version` from 2.1.280 to 2.1.267: `--ledger` failed through the environment record (`environment.json records harness '2.1.280 (Claude Code)' and the ledger records '2.1.267 (Claude Code)'`); the pin check, the take checker's verdict and `result.py --check` did not notice, which is right, since none of them reads that field.
- One rehearsal ledger's reasons changed to a driver-decided reason: `--ledger` failed twice over (`cannot have written this record`; `the checker's reasons ... are not the recorded`).
- One rehearsal `WHY.md` reason id changed: nothing failed. `--ledger` checks that `WHY.md` exists, not what it says; the ledger's reasons are what it binds. `WHY.md` feeds no count. NIT below.

So a count can be moved only by editing a results record, the result file, the cost file, a transcript, a row or a ledger, and each of those is caught by a named check that CI runs after every take. The one edit no check on disk catches is the one the README's limitation names: a take re-driven under its row's own session id after the harness's file was deleted, which leaves a coherent record. That is a limitation, not a finding, because closing it needs files this repository does not carry.

## What the checks bind, and what they cannot

I read the frozen file's 11 limitations lines first. Each weakness below is placed on one side.

- **Recorded mode is not enforced mode** (limitation 9). Every check reads the mode a session recorded. A harness that recorded `default` and applied something else would pass. Limitation, and stated as one.
- **No session file records the allowlist** (limitation 3). The evidence the list applied is that route commands ran without a denial, and 22 of 54 graded takes did meet a denial, each quoted. Limitation, and stated.
- **Re-driving under a spent id** (README's section, not in the frozen file). Limitation; the run put it where an amendment cannot reach, and said why.
- **The model behind an id across dates** (limitation 7). Limitation.
- **The harness version moved during the run.** Verifier 1 found it unpublished; amendment 2 now publishes it beside the counts, and I re-derived its every figure. What remains is that no committed check binds the block and the frozen file's own note named a different vehicle. Findings, SHOULD, not limitations, since a sentence fixes each.
- **The "before its commit" half of line 6's message rule.** The take commits were made by a script outside the repository, so the repository can bind only that every message passes now. A weakness that only lying could exploit, and the messages do pass, 125 of 125. NIT.
- **The public page has no round 3 section.** `lint_pooling.py --section-of docs/EVALS.md` prints `no section yet ... this scan has read nothing and claims nothing. Not a pass.` and exits 0. The guard is honest about grading zero items, and the outcome paragraph asks for one committed round in the repository, which `RESULT.md` is; the page is the owner's to write. NIT.
- **The results files name round 2's grader path.** Each `results/*.json` records `"grader": "evals/gap-study-2/graders/..."`, carried from the frozen task spec, while `run.py` loads the grader beside its own file. The bytes are identical by manifest, so no reading depends on it. NIT.
- **The workflow comment says eleven edited files.** The comment above round 3's job in `ci.yml` says the copy carries eleven edited files; `COPIED.json`, the README and the manifest check say 13. A comment no check reads. NIT.
- **`rounds.py` cannot fire its own material-finding rule.** It flags two `verify` rows sharing a `launch_commit`, but that field is HEAD at row time, which the forced sequence makes different for two verifiers of one sha. Carried from verifier 1. NIT.

## Findings

| # | Finding | Class | Would fixing it change a criterion, a reading or a claim? |
|---|---|---|---|
| 1 | Amendment 2's `harness_versions` block says its counts are derived from the ledgers by code, but no committed check re-derives it; my own re-derivation from the 54 ledgers matches every figure | SHOULD | A claim: the sentence should say the block was derived once and is bound by a verifier's re-derivation, or a check should be added. No criterion and no reading. |
| 2 | The frozen `harness.note` says a later harness version is a limitations line printing the range, never an amendment; the pinned result writer prints no such line, so the run recorded it as amendment 2 | SHOULD | A claim: the amendment should say it departs from the note's vehicle and why. No count moves and nothing is re-graded, which is what the note guards. |
| 3 | After amendment 1, the pins for `language-allowlist.json` and `COPIED.json` carry the freeze-time `git_blob_sha`, which matches neither file's blob at HEAD; amendment 2 left them so, and no check reads that field at HEAD | SHOULD | Neither: an amendment recording the new blobs moves no criterion and no reading, and no claim rests on the field. |
| 4 | Line 6 says the banned words carry no excusal path; the copied linter honours an allowlist entry for any pattern name, proved by mutation, and only the allowlist's pin stands in the way | SHOULD | A claim: the sentence should say the path is closed by the pin, not by the guard. No criterion and no reading. |
| 5 | Line 8 asks every prose file for a `status:` line asserted by a named test; 0 of 27 carry one, and the pinned battery cannot gain such a test | SHOULD | The line's wording only; the code-written files re-derive, the bound records are bound, and the "at freeze" keys hold. No reading. |
| 6 | A rehearsal's `WHY.md` reason id can be edited without any check noticing; `--ledger` binds the ledger's reasons to the checker's and only checks that `WHY.md` exists | NIT | Neither: `WHY.md` feeds no count, and the ledger beside it is bound. A claim in `attempt_layout.rule` reads wider than the check. |
| 7 | Line 6's "every commit is made after its message passes `commit_msg.py`" is bound in the repository only for review commits; the take commits' script is outside it. 125 of 125 messages pass now | NIT | A claim only. |
| 8 | Line 2 names a flag the frozen code lacks; the pin check that exists is `check_results.py` | NIT | The line's wording only. |
| 9 | Line 1's "added lines only" holds against the parent of slice 01, the sha CI's step names; against slice 01's own commit there are 4 removed lines, every one in round 3's own job | NIT | The line's wording only, to name which commit "kickoff" is. |
| 10 | DONE says the only commits after the verified commit are the two reports; the register forces row, report, row, report, each report with a blindness record, and three verifier reports exist across the two verified commits | NIT | The line's wording only. |
| 11 | `rounds.py` flags two verify rows sharing a `launch_commit` as a material finding, but that field is HEAD at row time, which the forced sequence makes different for two verifiers of one sha | NIT | Neither; the case it means is already refused by the register. |
| 12 | `results/*.json` record a round 2 path as the grader while the grader that ran is this folder's byte-identical copy | NIT | A claim in the README only. No reading, since the bytes are identical by manifest. |
| 13 | The `ci.yml` comment above round 3's job says eleven edited files; the manifest, its check and the README say 13 | NIT | A claim in a comment only. |
| 14 | `docs/EVALS.md` has no round 3 section, so the second guard's scan of the public page grades 0 items and says so | NIT | Neither; the guard is honest, and the section is the owner's to write after this report. |
