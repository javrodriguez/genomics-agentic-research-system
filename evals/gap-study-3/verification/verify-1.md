study HEAD: 20379046effb6c70fb9bb118f6813e88fa5d4d3d

# Final verification of The Gap Study, round 3

**Verdict: PASS.**

Every command below was run inside `study/`, a full-depth clone with its remote removed: `git rev-list --count HEAD` returns 986 and `git rev-parse --is-shallow-repository` returns `false`. The handed `prereg.json` and the repository's `evals/gap-study-3/prereg.json` are byte-identical (`cmp` printed nothing; both hash to `4b807943ef85...`). The tree was clean before and after every mutation test below (`git status --short` printed 0 lines; each mutated file was restored with `git checkout --`).

The verdict is PASS because every check that grades a countable thing graded the number it should have, every published count re-derives from committed bytes, and no finding raised below would move a criterion, a reading of a take or a count. Two checklist lines pass on a corrected reading of their wording rather than as written; each is said so in its section, and the wording is classified in the closing table.

## Line 1 — copy manifest and workflow diff

```
python3 evals/gap-study-3/copy_manifest.py --check
ok: 44 files trace to bf065feedccc, 13 edited with a reason, 10 pinned byte-identical; round 2, round 1, the pre-study and the parser unchanged
exit=0
```

Graded 44 of 44 copied files (the manifest's own count), 13 of 13 edits with a reason, 10 of 10 pinned files byte-identical.

The workflow diff, against the commit CI's own step names as the kickoff (`ddf12ebc…`, the parent of slice 01):

```
git diff --numstat ddf12ebc130e9d18de5ffcb429f7996ebe77baeb HEAD -- .github/workflows/
145	0	.github/workflows/ci.yml
```

Added lines only. I split both versions of `ci.yml` into job blocks and compared them: the four jobs that existed before this round (`tests`, `gap-study`, `gap-study-2`, `haiku-prestudy`) are byte-identical from that kickoff to HEAD, and the header is too. So the three pinned blocks the line names are byte-identical, and a fourth is as well. Measured from slice 01's own commit instead, the diff shows 4 removed lines, every one inside round 3's own job (the scoping of the commit-body scan that PROGRESS.md records at slice 8); none touches a pinned block. **Ruling: PASS.** The 4 removed lines are a NIT about which commit "kickoff" names, ruled below.

## Line 2 — the freeze is first, and every pin hashes

```
git log --oneline --reverse -- evals/gap-study-3/prereg.json
38c0250 slice 20: the freeze — the pre-registration is frozen, seeded by review 5's commit
17e1a29 ruling: amendment 1 excuses one cost-table line the language guard misread as a percentage
```

The freeze is the first entry. It names review 5's commit `ef61681`; `git merge-base --is-ancestor ef6168185f5e 38c0250` succeeds, and the committer dates read 12:25 for the review and 12:34 for the freeze on 2026-09-22. The frozen file's `frozen_at_commit_parent` is `4b8aae7`, the sixth rehearsal, which sits between them.

The line names `freeze.py --verify-pins`, and the frozen `freeze.py` carries no such flag. The pin check that exists is `check_results.py`:

```
python3 evals/gap-study-3/check_results.py
pinned files:
  106 pinned file(s) re-hashed
the frozen file:
  the frozen file compared with its freeze: 1 amendment(s) on record, 0 unrecorded change(s)
  the freeze commit held to its rehearsal and each pin to its committed blob: 0 problem(s)
clean
exit=0
```

Graded 106 of 106 nodes carrying a path and a sha256 (the frozen file's `pinned_files` list holds one hundred entries; six more such nodes sit elsewhere in the file and are walked too). The amended pins are checked through the amendment chain, sha256 before to sha256 after, and the rest of the frozen file is compared key for key with the freeze commit's bytes. **Ruling: PASS on the code; the checklist's wording is what failed.** The pin check the line means is `check_results.py`, which CI runs after every take and the sixth rehearsal ran before the freeze. The wording is classified as a NIT below.

One finding from reading the amended pins: after amendment 1, the entries for `language-allowlist.json` and `COPIED.json` carry the new sha256 but still carry the freeze-time `git_blob_sha` (`4b47a4ea…` and `77834aa9…`), while the files' blobs at HEAD are `49df3d7b…` and `81a5063c…`. The pin check reads the blob field only at the freeze commit, where it is right, so nothing goes red; but the frozen file now names a blob for each of those two files that is not the file's. Classified SHOULD below.

## Line 3 — every row, its session id, and its order

`takes.py --audit`:

```
python3 evals/gap-study-3/takes.py --audit
56 row(s), 56 commit(s)
...
every row is committed, and no commit introduced more than one
exit=0
```

Then, for each of the 56 rows, I ran `python3 evals/gap-study-3/takes.py --session-id <row>` and searched that row's transcript (under `transcripts/` for a graded row, under `rehearsals/<task>/<half>/<model>/row-<n>/` for a rehearsed one) for a record whose `sessionId` equals the derived id, and compared the committer date of the commit that introduced the row with the earliest timestamp on such a record:

```
rows checked 56 kinds {'graded': 54, 'rehearsal': 2}
rows whose commit is NOT earlier than transcript's first record: []
```

Graded 56 of 56 rows; 56 of 56 carry a transcript recording the derived id; 56 of 56 have their row committed before the transcript's first record. Registered rows are 56 against a planned 54. The frozen file records no pre-freeze drop; the two extra rows are rows 54 and 55, which re-register the slots of rows 7 and 40 after each became a rehearsal, exactly as the frozen `attempt_layout.rule` admits ("a slot is registered again only after an attempt that became a rehearsal or a pause"). Graded rows are 54 of 54 planned. **Ruling: PASS.**

## Line 4 — the take checker over every attempt

The loop CI runs, reading task, half and row from each take's own ledger:

```
for t in evals/gap-study-3/transcripts/*/*/*/*/transcript.jsonl; do ... python3 evals/gap-study-3/check_take.py "$t" --task "$task" --half "$half" --row "$row"; done
graded transcripts checked: 54, failed: 0
```

Each prints `valid — every operator-side check passed`. Graded 54 of 54.

The two rehearsals, which CI's loop does not visit, run the same way:

```
python3 evals/gap-study-3/check_take.py evals/gap-study-3/rehearsals/scope-read/control/claude-opus-5/row-40/transcript.jsonl --task scope-read --half control --row 40
NOT VALID — 1 problem(s):
  - [read-outside-the-checkout] a tool call or its result named a path outside this session's own checkout 1 time(s) -- first: '<tmp>/sel.json'.
exit=1
```

Row 7 reads the same with reason `read-outside-the-checkout`, first path `<tmp>/gars_finalize_run-….json`. Each rehearsal's `WHY.md` carries that one reason id and the command that reproduces it. Pauses: 0, and the ledger check agrees. So 2 of 2 rehearsals carry their reason ids, and 0 of 0 pauses.

The permission-mode assertion is live, not assumed. I set `permission_mode` to `auto` in one graded take's ledger and re-ran the checker:

```
  - [constant-binding] the take ran in permission mode 'auto', not the pre-registered 'default'
exit=1
```

then restored the file. The transcript beside it records `permissionMode` as `default` on each of its 3 operator turns, and `mode_binding.py --check` reads `passed=default recorded=default expected=default` on 56 of 56 attempts. **Ruling: PASS.**

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
clean — 56 input(s) scanned, 2 excused line(s) on record
exit=0

python3 evals/gap-study-3/lint_pooling.py evals/gap-study-3/
clean — 53 file(s) and 0 commit(s) scanned, no excusal path
exit=0
```

Commit bodies since the freeze, three ways. `git rev-list 38c0250..HEAD` lists 121 commits. I wrote each body to a file and ran `commit_msg.py` on it: 121 checked, 0 refused. I ran `lint_language.py` on each body the same way: 121 scanned, 0 refused; and to prove the linter was reading them I appended one line carrying a banned word and a slashed count to a copy of HEAD's body, which it refused with exit 1. The scan CI itself runs:

```
python3 evals/gap-study-3/lint_language.py --commits-since 38c0250612993cde0a48297ddad007fa84f58349
clean — 121 input(s) scanned, 2 excused line(s) on record
python3 evals/gap-study-3/lint_pooling.py --commits-since 38c0250 evals/gap-study-3/
clean — 53 file(s) and 121 commit(s) scanned, no excusal path
```

Graded 121 of 121 commit bodies under each guard, and 56 of 56 inputs in the folder under the copied linter (53 of 53 files under the second guard, which skips code and the two never-scanned files).

The second guard is mutation-proved: the battery's class `ThePoolingGuardIsMutationProved` passes within `test_round3.py` (156 tests ran, OK, 2 skipped, both skips being draft-only rules the freeze retires), and my own sentence, one that joined the two rounds' counts into a single figure of 54, was refused with `[both-rounds]` and `There is no allowlist for these`.

The claim that the banned words carry no excusal path reads more than the guard does. The copied linter's `excused()` consults the allowlist for every pattern name, banned words included; what stands between an excusal for a banned-word pattern and a green scan is that `language-allowlist.json` is a pinned file that only a recorded amendment can move, not the linter. No battery test bars a banned-word pattern from the allowlist. Today the allowlist holds 2 entries, one for the plan-gate quotation and one for the `hundred` rule, neither a banned word. Classified SHOULD below. **Ruling: PASS**, with that overstatement on record.

## Line 7 — CI green at full depth

This is the run's record, not mine: `ci-at-commit.json` was read from GitHub before I opened, and I have no network. The study's own reader on it:

```
python3 evals/gap-study-3/ci_conclusion.py 20379046effb6c70fb9bb118f6813e88fa5d4d3d --gh-json ../ci-at-commit.json
  completed    success          CI
20379046effb: 1 run(s), every one completed with success (exit 0)
```

Graded 1 of 1 run at the verified sha (workflow `CI`, event `push`, run 35786588781, created 2026-09-22T21:25:47Z). The record is workflow-level; the workflow holds five jobs and a success conclusion requires each of them, so the study's own job `gap-study-3` succeeded. That job checks out with `fetch-depth: 0`, as `ci.yml` shows, and its steps are the commands of lines 1, 4, 5 and 6 plus the pins, ledger and regrade. **Ruling: PASS on the run's record.**

## Line 8 — every prose file re-derived or asserted

Prose files in the study folder (`.md` and `.txt`, excluding cases, fixtures and walks): 25. Lines matching `status:` in them:

```
grep -rn "^status:\|status: " --include=*.md evals/gap-study-3 | grep -v "/cases/\|/fixtures/"
(no output)
```

So 0 of 25 prose files carry a `status:` line, and no test in the battery, pinned at the freeze, asserts one. As written, the line's second clause graded nothing.

What the line can honestly mean here, and what I ran for it: the files code writes re-derive by a check, and I ran each. `RESULT.md` by `result.py --check` (clean; and when I changed one published count from `0 of 3` to `1 of 3` it failed with `RESULT.md is not what this file writes from the committed takes`, then I restored it). `COSTS.md` by `costs.py --check` (`COSTS.md is what the reader writes`). The two rehearsal `WHY.md` files by `check_take.py`, whose output each reproduces. That is 4 of 25 prose files re-derived. The other 21 are hand-written or are records the run wrote once (the six rehearsal transcripts of the freeze, four pre-freeze reports with their blindness records, the review brief and its `why.md`, the gate card, the finding note, the commit-body note, `README.md`, `PROGRESS.md`). Of those, the battery binds sentences in `README.md` by name (its manifest sentence, its five-change list, its missing-limitation section); nothing binds `PROGRESS.md` or the notes.

Keys named "at freeze": `system_under_test.gars_tree_sha_at_freeze` is `e77b9031…`, and `git rev-parse 38c0250:gars` returns the same; `draft_sha256_at_freeze` equals the sha256 of `prereg-draft.json` on disk; `nulls_at_freeze` declares 22 with an empty `unaccounted` list; `harness.claude_version_at_freeze` is `2.1.267`, which is what the freeze recorded. So 4 of 4 hold their freeze value.

That last key surfaces a finding. The take ledgers record two harness versions: 30 takes on `2.1.267` and 24 on `2.1.280`. The frozen `harness.version_range_note` says a version later than the freeze's "is a limitations line printing the range, never an amendment", read from the takes' own ledgers. No file prints that range: `RESULT.md`, `COSTS.md`, `README.md` and `PROGRESS.md` carry no `2.1.280`, and only the three `results/*.json` files hold it, per cell under `harness_versions`. Classified SHOULD below.

**Ruling: PASS on the honest reading** (code-written files re-derive, and the "at freeze" keys hold), **not met as written** (0 status lines). The wording is classified below and does not move a reading.

## Line 9 — this verification

A fresh clone: yes, full depth, 986 commits, remote removed, HEAD at the sha on line 1 of this report, matching `COMMIT`. A committed blindness record and a report committed unedited: neither can exist at the commit I verify, because the register's rule commits my row after it and my report after that. The register at HEAD holds 5 `prefreeze` rows and no `verify` row:

```
python3 evals/gap-study-3/review_kit/rounds.py --check
1 row(s) closed as spent without work (a rate limit or an interruption before the first agent turn). Not voids: they do not count against the two-void rule.
ok: 4 registered round(s) graded, every report committed, 0 voided; prompt pinned at 0910589c8290
exit=0
```

Graded 4 of 4 registered rounds with a report, and 1 of 1 row spent without work (row 2, a rate limit before the first turn), which is why `review_kit/` holds reports 1, 3, 4 and 5. What binds my own row is the same code: `rounds.py` refuses a report whose blindness record is missing or does not name the session id its row derives, so my report cannot stand without the record. **Ruling: PASS on what can be checked from inside the verified commit; the rest is the run's to commit and this same check's to hold.**

On the forced sequence the run asks about: the line says the only commits after the verified commit are the two reports. The register mandates row, report with its blindness record, row, report. Each of those commits is a verifier's own record and none touches a take, a result, a pin or a criterion; the second verifier's row is refused while the first has no report, so the sequence is the register's, not the run's choice; and both verifiers rule on the same sha. I read that as satisfying the line's purpose, and not its letter. The letter should say "the two reports, each with its register row and its blindness record". NIT below.

One more thing I found in that check. `rounds.py` prints a MATERIAL FINDING when two `verify` rows share a `launch_commit`, saying a second verifier run on the same commit is itself a finding. But `launch_commit` is `git rev-parse HEAD` at the moment the row is added, which the forced sequence makes different for the two verifiers even though both verify the same sha. The rule cannot fire on the case its sentence names, and would fire only on a case the register already refuses. NIT below.

## The four answers

**1. Takes graded of planned, cells complete of planned.** From `result.py --check`: graded 54 of 54, complete cells 18 of 18. From `completeness.py --check`: 18 of 18 complete, 0 unmeasured. No cell publishes unmeasured, so there is no cell to name. The attempts behind them: 56 rows, 54 graded, 2 rehearsals (rows 7 and 40, each refused for `read-outside-the-checkout` and re-registered as rows 54 and 55), 0 pauses; 22 of 54 graded takes met a harness denial, each printed with its command under the result's Denials heading.

**2. Every amendment to the frozen file.** One. Amendment 1 (Ruling 13, 2026-09-22, after 54 of 54 takes) appended one line-exact excusal to `language-allowlist.json` for a row of `COSTS.md` whose `input` column reads exactly one hundred tokens, which the copied linter's `hundred` rule had refused as a percentage. It moved that file's pin from `c9acc416…` to `460b4857…` and the one field of `COPIED.json` that records the allowlist's copy hash, from `acaea2a5…` to `12ce6455…`; the amendment commit `17e1a29` touched those two files, `prereg.json` and `RESULT.md`. `check_results.py` reads the chain clean: `1 amendment(s) on record, 0 unrecorded change(s)`. Did it change a reading? No. The language guard feeds no grader; at HEAD `result.py --check`, `completeness.py --check` and `check_results.py --regrade` read clean and the regrade re-derives 3 of 3 results files byte-identically, and the amendment's own `graded_takes_at_the_time` is 54 of 54, so no take was graded under a different rule. The stale `git_blob_sha` on the two moved pins is the residue, named as a finding.

**3. Every language excusal on record.** Two, both in `language-allowlist.json`, and I confirmed each pinned line is still present verbatim:

- `contract_quotes.json`, the pattern named for the word the system under test uses of drafting a plan, ruled 2026-09-19: forgives the line quoting that plan-gate sentence byte for byte, the one that says drafting is not gated and running is. `grep -c -F` of the pinned text returns 1.
- `COSTS.md`, pattern `hundred`, ruled 2026-09-22 by amendment 1: forgives line 27, the per-take cost row for confounded-design, positive half, claude-opus-5, take 1, whose `input` column reads exactly one hundred. `grep -n -F` of the pinned text returns line 27.

Neither excusal's text has moved. The linter's `excused()` matches file, pattern name and exact line text together, so a moved line would bring its finding back rather than hide; the battery's `test_the_excusal_list_is_this_studys_own` asserts the text is present. The count the linter prints, `2 excused line(s) on record`, is the size of the allowlist, not the number of excusals it applied on that scan.

**4. Could a single edited record move a published count?** I tried three edits, restoring each with `git checkout --`:

- One cell's `k` in `results/scope-read.json`, 0 to 1: `result.py --check` failed (`RESULT.md is not what this file writes from the committed takes`) and `check_results.py --regrade` failed (`scope-read.json did not re-derive byte-identically`).
- One published count in `RESULT.md`, `0 of 3` to `1 of 3`: `result.py --check` failed with the same sentence.
- One byte appended to a graded transcript: `check_results.py --ledger` failed (`row 11: the transcript's bytes are not the ones its ledger records as published`).
- One ledger field, `permission_mode` to `auto`: `check_take.py` refused with `[constant-binding]`.

So a count can be moved only by editing a results record, the result file or a transcript, and each of those is caught by the named check, which CI runs after every take. The one edit no check on disk catches is the one the README's limitation names: a take re-driven under its row's own session id after the harness's file was deleted, which leaves a coherent record. That is a limitation, not a finding, because closing it needs files this repository does not carry.

## What the checks bind, and what they cannot

I read the frozen file's 11 limitations lines first. Each of the weaknesses below is placed on one side.

- **Recorded mode is not enforced mode** (limitation 9). Every check reads the mode a session recorded. A harness that recorded `default` and applied something else would pass. Limitation, and stated as one.
- **No session file records the allowlist** (limitation 3). The evidence the list applied is that route commands ran without a denial, and 22 of 54 graded takes did meet a denial, each quoted. Limitation, and stated.
- **Re-driving under a spent id** (README's section, not in the frozen file). Limitation; the run put it where an amendment cannot reach, and said why.
- **The model behind an id across dates** (limitation 7). Limitation.
- **The harness version moved during the run.** Not stated anywhere a reader of the result would see it, though the frozen file says it must be. Finding, SHOULD.
- **The public page has no round 3 section.** `lint_pooling.py --section-of docs/EVALS.md` prints `no section yet ... this scan has read nothing and claims nothing. Not a pass.` and exits 0. The guard is honest about grading zero items, and the outcome paragraph asks for one committed round in the repository, which `RESULT.md` is; the page is the owner's to write. Observation, NIT.
- **The results files name round 2's grader path.** Each `results/*.json` records `"grader": "evals/gap-study-2/graders/…"`, carried from the frozen task spec, while `run.py` loads the grader beside its own file. The bytes are identical by manifest, so no reading depends on it, but the README's sentence that no string this study prints names round 2's folder is one file wider than true. NIT.
- **Line 6's "no excusal path" for banned words.** The guard reads less than the claim. Finding, SHOULD, not a limitation, since a test could bind it if the battery were not pinned; the honest fix is the sentence.

## Findings

| # | Finding | Class | Would fixing it change a criterion, a reading or a claim? |
|---|---|---|---|
| 1 | The frozen file says a harness version later than the freeze's is published as a limitations line printing the range; 24 of 54 takes ran on 2.1.280 against a freeze at 2.1.267 and no published file prints the range | SHOULD | A claim: it adds a limitation the frozen file already promised. No criterion and no reading. |
| 2 | Line 6 says the banned words carry no excusal path; the copied linter honors an allowlist entry for any pattern name, and only the allowlist's pin stands in the way | SHOULD | A claim: the sentence should say the path is closed by the pin, not by the guard. No criterion and no reading. |
| 3 | After amendment 1, the pins for `language-allowlist.json` and `COPIED.json` carry the freeze-time `git_blob_sha`, which no longer matches either file's blob at HEAD; no check reads that field at HEAD | SHOULD | Neither: an amendment recording the new blob moves no criterion and no reading, and no claim rests on the field. |
| 4 | Line 8 asks every prose file for a `status:` line asserted by a named test; 0 of 25 carry one, and the pinned battery cannot gain such a test | SHOULD | The line's wording only; the code-written files already re-derive and the "at freeze" keys hold. No reading. |
| 5 | Line 2 names `freeze.py --verify-pins`, a flag the frozen code lacks; the pin check that exists is `check_results.py` | NIT | The line's wording only. |
| 6 | Line 1's "added lines only" holds against the parent of slice 01, the sha CI's step names; against slice 01's own commit there are 4 removed lines, every one in round 3's own job | NIT | The line's wording only, to name which commit "kickoff" is. |
| 7 | DONE says the only commits after the verified commit are the two reports; the register forces row, report, row, report, with a blindness record beside each report | NIT | The line's wording only. |
| 8 | `rounds.py` flags two verify rows sharing a `launch_commit` as a material finding, but that field is HEAD at row time, which the forced sequence makes different for two verifiers of one sha | NIT | Neither; the case it means is already refused by the register. |
| 9 | `results/*.json` record a round 2 path as the grader while the grader that ran is this folder's byte-identical copy; the README's "no printed string names round 2's folder" is one file wider than true | NIT | A claim in the README only. No reading, since the bytes are identical by manifest. |
| 10 | `docs/EVALS.md` has no round 3 section, so the second guard's scan of the public page grades 0 items and says so | NIT | Neither; the guard is honest, and the section is the owner's to write after this report. |
