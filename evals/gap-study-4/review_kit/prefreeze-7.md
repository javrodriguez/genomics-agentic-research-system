prereg.json sha256: 37fd08047b66cbaee8cc12cd05a823692e2bafebaaa599d6db53178482b5c0e3

# Pre-freeze review 7 of gap-study-4

**Ruling: DO NOT FREEZE.**

The reviewed commit, from `COMMIT`, is `3c31d76b364d1283e00dd6ab9035a164355922b4`. Round 7's `launch_commit` should equal it (see m-new-2).

`diff prereg.json study/evals/gap-study-4/prereg-draft.json` prints nothing. `prereg.json` is also byte-identical to `prereg-as-the-previous-review-read-it.json`: `cmp` is silent and both have the same sha256. So the draft has not changed since review 6. Everything that changed since then is code, tests and records. `git -C study diff --stat 3154459688 HEAD` lists 13 files:

- `freeze.py`
- `review_kit/rounds.py`
- five test files
- two `COPIED.d` fragments
- `language-allowlist.json`
- review 6's report, its blindness record, and `rounds.json`

Fold 8 closes review 6's M1 and M2 well in code (details under "Read and found sound"). One residual it found itself is left out of the pre-registration, and the draft's own sentence about it is now false. That residual is the one MAJOR below.

## Threat model, restated and corrected

The operator could move a reading after the takes exist. They could edit, re-date, re-run, re-route, re-order or misfile one record. They could choose among commits, seeds or reviews. Or they could change code, configuration or pins after the freeze. The agent could, from inside its take, try to reach past its run tree and its one API host, to a credential, to the study's files or graders, or to the evidence the graders read. It could also make a step it did not take look taken.

One correction. The brief scopes the operator to "after the takes exist", but it also lists "a choice among several … reviews". That choice is made *before* the freeze, at the step that seeds it. So the operator's threat model has to include the window between the reviews and the freeze. Every finding below is ruled against that corrected statement. Complete, coherent fabrication across every ledger is still out of scope, as are vendor-side behaviour beyond the client's records and the honesty of the machine and runner. Each of those is a limitation the pre-registration must name.

On that statement, `limitations`, `box_residuals`, `not_poolable` and `predictions_rule` are honest about what the checks bind, with one exception. `round_4_limitations[10]` claims more than the review register binds (M1). `round_4_limitations[1]` claims less (m2, carried).

## MAJOR findings

### M1. A later review can be erased by local history rewriting, the draft says it cannot, and the freeze's admission of this is never recorded

**Where.**

- `prereg.json`, `round_4_limitations[10]` ("review shopping and the ruling line") says: "rounds.py --check refuses while any registered round's report is not committed, so a registered review cannot be dropped."
- `study/evals/gap-study-4/freeze.py:1178-1183` defines `PUBLISHED_TIP_RESIDUAL`. It says itself that "A later review dropped by a rebase, a deleted ref and an expired reflog (or a gc) is seen by no local read here".
- `freeze.py:1648-1652` prints that line to stdout and goes on. It adds nothing to `frozen` (`:1683-1688`), so the frozen file carries no trace of it.
- `COPIED.d/fold8-review-binding.json` calls it "the residual the draft cannot carry". The same fragment's reason also says "so round_4_limitations[10]'s 'a registered review cannot be dropped' holds."
- `grep -c -i 'reflog\|rebase\|published tip\|force-push' prereg.json` finds none of these in the draft.

**Shown in a scratch clone of `study/`** (under a scratch folder beside this report, deleted afterwards). Rows 7 and 8 were committed to `rounds.json`, then a `prefreeze-8.md`. Round 7 was then read as a seed:

```
with round 8 in history: round 8 is registered in evals/gap-study-4/review_kit/rounds.json (at HEAD or in its history, …), so … prefreeze-7.md (round 7) is not the latest review: the freeze seeds from the last ruling
$ git reset -q --hard <row-7 commit>; git reflog expire --expire=now --all; git gc -q --prune=now
after reset, reflog expire, gc: None
published tip: (None, "RESIDUAL (published tip): no remote of this repository is …gars-cloud-mirror, …")
```

This takes three git commands and fabricates no record. `rounds.py --check` then reads the shorter register as its whole history. The mirror binding (`published_tip_problem`) applies only when a mirror remote is present and the dropped commits were pushed. A row commit and its report need not be pushed: athena runs at the launch commit, which comes before the row. Removing the remote takes one command and only produces the printed line.

**Why it is material.** The study may claim that the freeze seeded from the last blind review. Its pre-registration says that claim is enforced. The code says, in its own words, that in this case it is not. The admission is printed to one terminal and lost. This is the "choice among … reviews" the threat model names. It needs no coherent fabrication. The pre-registration does not name it, and a cheap step closes the disclosure gap. On the brief's own rule, that makes it a blocker.

**A cheap fix, verifiable by a command.** Either:

- (a) correct `round_4_limitations[10]` to name this residual in the residual line's own words; or
- (b) have the freeze write the residual line into the frozen file (for example `published_tip_residual`), and have `check_results.py` print it in the publication.

Either one is a change to a pinned path or to the draft, so it needs a new round. Option (a) is the smaller change. Optionally, `review_kit/launch.py` could also refuse to open a round until its row commit is on the mirror's freeze line as last fetched.

**Lean.** MAJOR, with moderate confidence. Against: the attack is deliberate history destruction by the operator, and the code's authors found and documented it. For: the draft states the opposite, and freezing is irreversible. With a one-sentence draft correction this becomes a named limitation, not a defect.

## Other findings

### MINOR

- **m-new-2. The review's launch commit is not bound to the commit the reviewer was handed.**
  - `review_kit/rounds.py:280` writes `launch_commit` as `git rev-parse HEAD` at `--add`.
  - `build_kit.py:148` writes the kit's `COMMIT` from HEAD at build time.
  - `grep -n COMMIT review_kit/rounds.py review_kit/commit_review.py freeze.py` finds nothing that compares the two.
  - The `input_sha256` manifest hashes the folder, which includes `athena/`, so it cannot be re-derived from the repository.
  - So a commit made between the kit build and `--add` becomes the code `launch_binding_problem` (`freeze.py:1440`) binds, though the reviewer never read it.
  - Fix: `--add` refuses unless `folder/COMMIT` equals HEAD. The fix tightens the check. It changes no criterion or reading. It makes the M2 fix's claim exact. A reader can also compare this report's stated commit with row 7.
- **m2 (carried from review 6).** `round_4_limitations[1]` still says "'committed unedited' is not enforced".
  - It is now enforced twice: by the report digest from round 5 on, and by `freeze.committed_once_problem` (`freeze.py:1341`, fold 8).
  - The draft understates the binding. Rewording it tightens disclosure only.
- **m-new-3. The launch binding leaves the walk folders out.**
  - `launch_binding_problem` compares `freeze.PINNED` plus `COPIED.d`. Of the tracked files under `evals/gap-study-4/`, only `rehearsals/w*/` (13,202 files) and most of `tests/` are outside it. I listed every tracked path against `pinned_paths(PINNED)`: no non-test, non-walk file is unpinned, and no pinned module imports an unpinned one.
  - The walks the vendor legs cite are bound through pinned byte-copy fixtures, and the walk gates re-derive the rest at the rehearsal. So an edited walk needs a coherent regrade.
  - Fix: name `rehearsals/` in the binding's spec. The fix tightens the check. It changes no reading.
- **Carried from reviews 5 and 6, unchanged.** None of the files they name changed since review 6 (the diff stat above). I re-checked these directly at `COMMIT`:
  - **m10.** `rehearsals/w255/subagents/` exists, and `fixture_walk.py` has no `subagents` read.
  - **m1c.** The unknown-phase early return is still at `batch.py:512`. The draft names it ("rulings on a take of unknown phase"), and a re-run stands only on an end state with no wrong action. So this stays MINOR.
  - **m7.** `box/take_config.py:79-86` appends the per-take codex trust table to the hashed template.

  These are carried on the unchanged-file evidence:
  - **m1.** Take-path code changed after the take order was public. Fold 8 touched no take-path file.
  - **m3.** Beacon swaps are unbounded and not printed in RESULT.md.
  - **m4.** Two agent-caused driver stops are missing from `[2]`.
  - **m5.** Arm A's account state is missing from the vendor-account residual.
  - **m6.** The settings hot-reload gap is in code but not in the draft.
  - **m8.** Table 6's heading mixes model rows and agent-system rows. This is presentation only, since `check_families` keeps the two apart.

### NIT

- **n-new-1.** The athena file name `19-…-legs-i-ii.txt` is truncated. Its command line says "legs i-iii".
- **n-carried.** Review 6's n2 and review 5's n1-n8 and n10 are unchanged. Review 6's n1 (fold 7's unnamed edits) is fixed: `COPIED.d/fold8-review-binding.json` now names them.

### Read and found sound

- **Fold 8 against review 6's M1.**
  - `later_review_problem` (`freeze.py:1214`) reads the highest prefreeze `n` in every version of `rounds.json`, and every `prefreeze-M.md` ever committed. It reads `--all --reflog --full-history`.
  - `grandfathered_seed_problem` (`:1262`) refuses rounds 1-4.
  - `committed_once_problem`, `row_introducer` and `introduced_row_problem` refuse a relabelled or re-introduced row.
  - `rounds.py --check` refuses a cut register.
  - My scratch replay confirmed the refusal while round 8 was still reachable. M1 above is what remains after it is not.
- **Fold 8 against review 6's M2.**
  - `launch_binding_problem` (`freeze.py:1440-1486`) requires every pinned path, the native-readers folder and `COPIED.d` to equal their bytes at the round's `launch_commit`.
  - Only the round's report, its blindness record, `rounds.json`, and appended claims and excusals may differ.
  - This is sound apart from m-new-2 and m-new-3.
- **Copy record (step 6).**
  - `copy_manifest.py --check` reports 863 files from 107 fragments: 22 identical, 29 edited, 812 new, and the native-readers pattern.
  - I compared all 22 identical files byte for byte with their sources: 0 differ.
  - The fold 8 fragment names every file fold 8 touched.
  - The edited files' reasons are cumulative lane lists. Diffs of thousands of lines cannot be matched line by line to them, and I did not try to.
- **System under test.**
  - `variants.PINNED_TREE` is `844a4ce0…`. `git rev-parse 844a4ce0…:gars` gives `8a54e0f8cd91…`, which equals `check_take.GARS_TREE_SHA` (`check_take.py:2027`).
- **Container, vendor arms, outcome, walks, publication (steps 7-11).**
  - The egress hosts in `box/egress/proxy_conf.py:50-52` are one per harness: `api.anthropic.com`, `chatgpt.com` and `generativelanguage.googleapis.com`.
  - No box, adapter, template, lock, price table, routing marker, grader, `routing.json`, `stats.py`, `result.py` or `check_results.py` changed since review 6. On that evidence I adopt its reading of these.
  - All three vendor legs hold (`freeze.py --check`, and the leg check below).
  - Arm G is deferred, and its 0 of 18 walks covered is printed, not required.
  - Every take-side gate says it measured nothing and does not print a pass.
  - `probes4.py --check` grades 1690 cells with 0 defects.

## Step 3: the athena files

Every file names its command, the commit `3c31d76b364d1283e00dd6ab9035a164355922b4` (equal to `COMMIT`), and its exit code. Together they cover `run_checks.py`, each of the 16 `freeze_rehearsal.COMMANDS` (`freeze_rehearsal.py:109-127`), and `freeze.py --check`.

| file | commit | last line |
|---|---|---|
| 01-run-checks-py-… | 3c31d76b | `run_checks: 530 of 530 commands passed` |
| 02-test-round4-py.txt | 3c31d76b | `OK (skipped=62)` (5999 tests) |
| 03-copy-manifest-py-check.txt | 3c31d76b | `ok: 863 files from 107 fragment(s) (…) … 8 frozen paths unchanged since 68ec902f63bf` |
| 04-tests-test-box-integration-py.txt | 3c31d76b | `OK` (61 tests) |
| 05-tests-test-pipeline-py.txt | 3c31d76b | `OK` (88 tests) |
| 06-probes4-py-check.txt | 3c31d76b | `probes4: 9 tasks, 18 halves, 169 rows, 1690 cells graded, 0 defects, 0 problems` |
| 07-build-draft-py-check.txt | 3c31d76b | `ok: the committed draft is what build_draft.py builds` |
| 08-leak-grep-py-check.txt | 3c31d76b | `ok: 25 leak word(s) grepped against 386 real session(s); none would void one; 1 session(s) not grepped (unreadable, named above)` |
| 09-holdout-py-check.txt | 3c31d76b | `OWED: holdout.py --check lives in private aegis (ruling C4); … so it did not run and this rehearsal is not all green` (exit 1: names itself as not run, correctly) |
| 10-review-kit-rounds-py-check.txt | 3c31d76b | `ok: 6 registered round(s) graded, every report committed, 0 voided; prompt pinned at 4246efa5b409` |
| 11-walk-register-py-check.txt | 3c31d76b | `ok: 387 registered walk(s), each with its folder, none counted` |
| 12-mode-binding-py-walks-check.txt | 3c31d76b | `36 of them are input-side only: their CLI writes no mode record, so the launch argv is what was checked, …` |
| 13-fixture-walk-py-check.txt | 3c31d76b | `ok: 387 committed walk(s) graded, each read through its own harness's reader, …; 41 by a recorded per-walk exception, printed above` |
| 14-run-py-walks-check.txt | 3c31d76b | `run: 387 walk(s) regraded, every grade.json the regrade's bytes (313 graded, 74 pending documents that grade nothing yet); never counted` |
| 15-walk-regrade-py-check.txt | 3c31d76b | `walk_regrade: ok` |
| 16-walk-plan-py-coverage-require-run-arms.txt | 3c31d76b | `ok: every required walk of the arms the freeze runs is covered` |
| 17-walk-pins-py-check.txt | 3c31d76b | `walk_pins: 387 registered walk(s) read; every one on the draft's version pins and image ids, … (a walk records the pin, so this compares the pin with itself: …)` |
| 18-freeze-py-check.txt | 3c31d76b | `freeze: 863 fragment-claimed files and 4 native-reader record(s) owned; 8 of 8 legs hold; no takes or freeze performed` |
| 19-freeze-unrecorded-shapes-problem-…-legs-i-ii.txt | 3c31d76b | `every leg holds` |

No red is unexplained. The 62 skipped tests in 02 equal review 6's count. The only non-zero exit is holdout's, which is owed as designed.

## Step 4: the light checks, run from `study/`

Every command exited 0, and `git status --short` under `study/` was empty afterwards.

| command | tail of output |
|---|---|
| `python3 evals/gap-study-4/copy_manifest.py --check` | `ok: 863 files from 107 fragment(s) (…) … 22 identical and 29 edited (…), 812 new; 5 fixture builders byte-identical; 8 frozen paths unchanged since 68ec902f63bf` |
| `python3 evals/gap-study-4/freeze.py --check` | `pins (869 paths, patterns expanded): ok` / `vendor legs i-iii: ok` / `walk coverage of the arms the freeze runs: ok` / `take-order function: ok` / `prepare (dummy review, synthetic beacon reading): ok` / `freeze: 863 fragment-claimed files and 4 native-reader record(s) owned; 8 of 8 legs hold; no takes or freeze performed` |
| `(cd evals/gap-study-4 && python3 -c "… freeze.unrecorded_shapes_problem …")` | `every leg holds` |
| `build_draft.py --check` | `ok: the committed draft is what build_draft.py builds` |
| `leak_grep.py --check` | `ok: 25 leak word(s) grepped against 386 real session(s); none would void one; 1 session(s) not grepped (unreadable, named above)` |
| `probes4.py --check` | `probes4: 9 tasks, 18 halves, 169 rows, 1690 cells graded, 0 defects, 0 problems` |
| `routing.py --check` | `routing.json: 27 rows, 3 annotations, sound` / … `before-first-turn, last turn none (no turn ran) -> route rehearsal` |
| `contracts.py --check` | `every stored sentence is a byte substring of the blob it was pinned to` |
| `harness_bookkeeping.py --check` | `harness_bookkeeping: ok: 3 harness(es): claude-code, codex, gemini` |
| `denials.py --check` | `ok, having read 0 graded takes: none is committed yet, so nothing here is evidence about any denial. Not a pass.` |
| `completeness.py --check` | `completeness: no takes; no cells measured` |
| `takes.py --check` | `takes: no takes; no registration or outcome measured` |
| `costs.py --check` | `costs: no takes; no cost measured or written` |
| `stats.py --check` | `stats --check: no takes (0 results files); nothing was compared` |
| `intervals.py --check` | `done-commit binding: 15 of 15 results files equal their blobs` / `gap-study intervals: PASS` |
| `result.py --check` | `result: no takes; no table measured or written` |
| `check_results.py --check` | `check_results: no takes; no frozen pins or publication measured` |
| `batch.py --check` | `batch: routing.json ready` |
| `python3 evals/gap-study-4/lint_language.py evals/gap-study-4/` | `clean — 226 input(s) scanned, 95 excused line(s) on record` |
| `python3 evals/gap-study-4/lint_pooling.py evals/gap-study-4/` | three `not scanned: … a bound review record (BOUND_REVIEW_RECORDS)` lines / `clean — 223 file(s) and 0 commit(s) scanned, no excusal path` |
| `python3 evals/gap-study-4/prereg.py --status` | `This is a DRAFT. No take may run against it and no number may be graded from it. The walks are what turn it into the frozen file.` |
| `python3 evals/gap-study-4/review_kit/rounds.py --check` | `ok: 6 registered round(s) graded, every report committed, 0 voided; prompt pinned at 4246efa5b409` |

## Findings

| # | finding | class | loosens or tightens | would fixing it change a criterion, a reading or a claim? |
|---|---|---|---|---|
| M1 | Resetting, expiring the reflog and running gc erases a later unpushed review. The freeze then seeds from an earlier one. The draft's `[10]` says a registered review cannot be dropped. The freeze's own residual line saying otherwise is printed and never recorded. | MAJOR (lean MAJOR, moderate confidence: deliberate history destruction, but the draft states the opposite and it is cheap to name) | tightens | A claim: `[10]` becomes true, as a named limitation or a recorded residual. No criterion or reading. |
| m-new-2 | `launch_commit` is HEAD at `--add`, and nothing compares it with the kit's `COMMIT`. A commit between building the kit and registering the row becomes the bound code, unread by the reviewer. | MINOR | tightens | Makes the claim exact that the frozen code is the code reviewed. No criterion or reading. |
| m2 | `[1]` still says "committed unedited" is not enforced, though it now is (digest and committed-once). | MINOR | tightens | Disclosure only. The draft understates a binding. |
| m-new-3 | The launch binding leaves out `rehearsals/w*/`, though the freeze rests on the walks. | MINOR | tightens | No reading. It closes a road that needs a coherent regrade. |
| m10 | The walk path gate does not read claude-code sub-agent streams (w255, w260). (carried) | MINOR | tightens | Corrects the gate's printed claim for two walks. |
| m1c | An unknown-phase stopped take can be re-run after its end state is seen. It is named, and bound to an end state with no wrong action. (carried) | MINOR | tightens | Could change a reading in a cell where it happens. No criterion. |
| m1 | Take-path code changed after the take order was public, and the draft does not say it may. (carried) | MINOR | tightens | Disclosure only. |
| m3 | Beacon swaps are unbounded and not printed in RESULT.md. (carried) | MINOR | tightens | Disclosure only. |
| m4 | Two agent-caused driver stops are missing from `[2]`. (carried) | MINOR | tightens | Disclosure only. |
| m5 | Arm A's account state is missing from the vendor-account residual. (carried) | MINOR | tightens | Disclosure only. |
| m6 | The settings hot-reload gap is in code, not in the draft. (carried) | MINOR | tightens | Disclosure only. |
| m7 | The hashed codex template leaves out the per-take trust table. (carried) | MINOR | tightens | Makes the hashed-bytes claim exact. No reading. |
| m8 | Table 6 puts model and agent-system rows under one heading. (carried) | MINOR | tightens | Presentation only, no count. |
| n-new-1 | Athena file 19's name says legs i-ii, but its command says i-iii. | NIT | n/a | No |
| n-carried | Review 6's n2 and review 5's n1-n8 and n10, unchanged. | NIT | n/a | No |
