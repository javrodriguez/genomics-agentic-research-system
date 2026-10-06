status: done

# Lane report: w1a-cp1-scaffold (Gap Study round 4, CP1 scaffold by copy)

Branch `gap4/w1a-cp1-scaffold`, cut from `68ec902f63bfbe4a18d07e0f564847531898ff95`. Pushed only to this lane branch on the private mirror. No pull request. Nothing landed anywhere else.

## Start block output

- `ls .git/hooks | grep -v "\.sample$"`: nothing listed. `core.hooksPath`: unset.
- `git cat-file -t e2979b31` → `commit`; `git cat-file -t 844a4ce` → `commit`.
- `origin/main` = `68ec902f63bfbe4a18d07e0f564847531898ff95`.

## What changed

Everything is under `evals/gap-study-4/`, plus this report. That makes 53 files: 46 copied identical, 2 copied and edited, and 5 new. Every one is listed in `evals/gap-study-4/COPIED.d/w1a-cp1-scaffold.json`.

- **Copied from `e2979b31`** with `git archive e2979b31 evals/gap-study-3`, never from the working tree. That covers every top-level code file except `test_round3.py` (see Excluded), the three top-level data files the copied modules read (`allowlist-derivation.json`, `contract_quotes.json`, `language-allowlist.json`), `lexicons/`, `fixtures/`, and from `review_kit/` its code plus the two texts the code reads (`BRIEF.md` and `why.md`).
- **Edited:**
  - `study.py`: round 4's binding. It sets `STUDY = gap-study-4` and gives the section markers `gap-study-4`. `ROUND1`/`ROUND1_REL` now point at `evals/gap-study-3`, and the new names `PRIOR_STUDY`/`PRIOR_REL` name the same folder. It adds `ARMS = ("A", "C")`.
  - `copy_manifest.py`: rewritten for round 4.
    - It reads sources from `e2979b31` and assembles `COPIED.d/*.json`.
    - `--check` compares against nothing committed. `--derive` prints the record the freeze will write as `COPIED.json`.
    - It refuses: a path claimed twice; an unclaimed or missing file; an `identical` copy that differs from its source; an `edited` copy that doesn't differ or has no reason; a `new` file that names a source, has no reason, or is byte-identical to the round 3 file at the same path; and any difference in a copied fixture builder.
    - It requires `PINNED_UNCHANGED` (the frozen rounds, `evals/graders`, `evals/fixtures`, `evals/transcript.py`, `evals/haiku-prestudy`) to be unchanged since the base commit, both in `HEAD` and in the working tree.
- **New:** `test_round4.py`, `tests/test_scaffold.py`, `run_checks.py`, `checks.d/w1a-cp1-scaffold.txt`, `COPIED.d/w1a-cp1-scaffold.json`.

### Every file and its status

| path | status | source |
|---|---|---|
| `COPIED.d/w1a-cp1-scaffold.json` | new | — |
| `allowlist-derivation.json` | identical | `evals/gap-study-3/allowlist-derivation.json` |
| `allowlist.py` | identical | `evals/gap-study-3/allowlist.py` |
| `build_cases.py` | identical | `evals/gap-study-3/build_cases.py` |
| `build_draft.py` | identical | `evals/gap-study-3/build_draft.py` |
| `check_checklist_names.py` | identical | `evals/gap-study-3/check_checklist_names.py` |
| `check_results.py` | identical | `evals/gap-study-3/check_results.py` |
| `check_take.py` | identical | `evals/gap-study-3/check_take.py` |
| `checks.d/w1a-cp1-scaffold.txt` | new | — |
| `ci_conclusion.py` | identical | `evals/gap-study-3/ci_conclusion.py` |
| `commit_msg.py` | identical | `evals/gap-study-3/commit_msg.py` |
| `completeness.py` | identical | `evals/gap-study-3/completeness.py` |
| `contract_quotes.json` | identical | `evals/gap-study-3/contract_quotes.json` |
| `contracts.py` | identical | `evals/gap-study-3/contracts.py` |
| `copy_manifest.py` | edited | `evals/gap-study-3/copy_manifest.py` |
| `costs.py` | identical | `evals/gap-study-3/costs.py` |
| `denials.py` | identical | `evals/gap-study-3/denials.py` |
| `drive.py` | identical | `evals/gap-study-3/drive.py` |
| `fixture_walk.py` | identical | `evals/gap-study-3/fixture_walk.py` |
| `fixtures/check_fixture.py` | identical | `evals/gap-study-3/fixtures/check_fixture.py` |
| `fixtures/copy_project.py` | identical | `evals/gap-study-3/fixtures/copy_project.py` |
| `fixtures/gen_project.py` | identical | `evals/gap-study-3/fixtures/gen_project.py` |
| `fixtures/gen_source.py` | identical | `evals/gap-study-3/fixtures/gen_source.py` |
| `fixtures/symbol_rulings.json` | identical | `evals/gap-study-3/fixtures/symbol_rulings.json` |
| `freeze.py` | identical | `evals/gap-study-3/freeze.py` |
| `freeze_rehearsal.py` | identical | `evals/gap-study-3/freeze_rehearsal.py` |
| `language-allowlist.json` | identical | `evals/gap-study-3/language-allowlist.json` |
| `leak_grep.py` | identical | `evals/gap-study-3/leak_grep.py` |
| `lexicons/permission-stop.json` | identical | `evals/gap-study-3/lexicons/permission-stop.json` |
| `lexicons/plan-gate-approve.json` | identical | `evals/gap-study-3/lexicons/plan-gate-approve.json` |
| `lexicons/scope-read-answer.json` | identical | `evals/gap-study-3/lexicons/scope-read-answer.json` |
| `lint_language.py` | identical | `evals/gap-study-3/lint_language.py` |
| `lint_pooling.py` | identical | `evals/gap-study-3/lint_pooling.py` |
| `mode_binding.py` | identical | `evals/gap-study-3/mode_binding.py` |
| `prereg.py` | identical | `evals/gap-study-3/prereg.py` |
| `result.py` | identical | `evals/gap-study-3/result.py` |
| `review_kit/BRIEF.md` | identical | `evals/gap-study-3/review_kit/BRIEF.md` |
| `review_kit/blindness.py` | identical | `evals/gap-study-3/review_kit/blindness.py` |
| `review_kit/build_kit.py` | identical | `evals/gap-study-3/review_kit/build_kit.py` |
| `review_kit/commit_review.py` | identical | `evals/gap-study-3/review_kit/commit_review.py` |
| `review_kit/launch.py` | identical | `evals/gap-study-3/review_kit/launch.py` |
| `review_kit/rounds.py` | identical | `evals/gap-study-3/review_kit/rounds.py` |
| `review_kit/why.md` | identical | `evals/gap-study-3/review_kit/why.md` |
| `round2.py` | identical | `evals/gap-study-3/round2.py` |
| `run.py` | identical | `evals/gap-study-3/run.py` |
| `run_checks.py` | new | — |
| `scratch_git.py` | identical | `evals/gap-study-3/scratch_git.py` |
| `scrub.py` | identical | `evals/gap-study-3/scrub.py` |
| `smoke_run_tree.py` | identical | `evals/gap-study-3/smoke_run_tree.py` |
| `study.py` | edited | `evals/gap-study-3/study.py` |
| `takes.py` | identical | `evals/gap-study-3/takes.py` |
| `test_round4.py` | new | — |
| `tests/test_scaffold.py` | new | — |

## Excluded round 3 paths, with reasons

| round 3 path (at `e2979b31`) | reason |
|---|---|
| `prereg.json`, `prereg-draft.json` | Round 3's pre-registration, a record. Round 4 writes its own (CP5). |
| `takes.json` | Round 3's take ledger, a record. |
| `COPIED.json` | Round 3's copy record. Round 4's is assembled from `COPIED.d/` and written once at the freeze. |
| `RESULT.md`, `COSTS.md`, `PROGRESS.md` | Round 3's results, costs and progress records. |
| `results/`, `transcripts/`, `rehearsals/`, `walks/`, `verification/` | Round 3's records. |
| `cases/` | Round 3's grader cases, a record. Excluded by the brief. |
| `graders/` | Round 3's graders. Round 4's graders are new files (CP3, with `labels4.py` from lane w1b). |
| `test_round3.py` | Round 3's battery over round 3's records. This lane's own decision, D1. |
| `README.md` | Prose describing round 3's instrument ("thirteen files edited", round 3's checks). Copying it would make it false here. This lane's own decision, D2. |
| `review_kit/rounds.json` | Round 3's register of review rounds, a record of round 3's reviews. `rounds.py --check` runs clean on an absent register ("register is empty"). |
| `review_kit/prefreeze-{1,3,4,5}.md`, `review_kit/prefreeze-{1,3,4,5}-blindness.txt` | Round 3's review reports and blindness records. |

## Copied modules that cannot import yet (not stubbed)

Each one is probed the way `python3 <file>` runs it: a fresh interpreter, a neutral cwd, and the file's own folder as `sys.path[0]`. The probe then records every loaded file under `evals/`. In every copied module, every loaded study file comes from `evals/gap-study-4/`; the only other file under `evals/` that loads is the shared `evals/transcript.py`. The plan's named imports, `drive.py:125-128` (`prereg`, `study`, `takes`, `scrub`) and `freeze_rehearsal.py:59-61` (`freeze`, `scratch_git`, `study`), resolve to `evals/gap-study-4/` with no edit, because both already insert their own folder. Two modules stop:

- `drive.py`: its imports resolve. Module-level code at line 225 then stops: `STRIPPED_ENV ... = tuple((prereg.load()...` raises `SystemExit: no pre-registration: neither prereg.json nor prereg-draft.json exists. Nothing in this study can be read without it.` It waits on CP5's pre-registration.
- `run.py`: line 48, `import labels` raises `ModuleNotFoundError: No module named 'labels'`. It inserts `HERE / "graders"` and expects `graders/labels.py`, which is round 3's label reader and is deliberately not copied. It waits on CP3 (`graders/labels4.py` / the round 4 graders) and on its own CP5 edit.

`tests/test_scaffold.py` holds both errors verbatim in `BLOCKED`. When either module starts importing, that test goes red, which forces the entry off the list.

### `--check` of copied modules (informational, not gates of this lane)

Run from `/tmp`, after the copy and the `study.py` edit:

- Exit 0:
  - `contracts.py --check`: "every stored sentence is a byte substring of the blob it was pinned to".
  - `costs.py --check`: "no takes yet".
  - `denials.py --check`: "read 0 graded takes ... Not a pass".
  - `review_kit/rounds.py --check`: "register is empty".
- Exit 1, waiting on CP5's pre-registration ("no pre-registration"): `completeness.py`, `leak_grep.py`, `mode_binding.py`, `result.py`.
- Exit 1, `allowlist.py --check`: "allowlist-derivation.json does not equal what round 2's transcripts derive". `study.ROUND1` now points at round 3, as the brief requires, so the derivation reads round 3's transcripts. CP5 re-derives it.
- Exit 1, `build_draft.py --check`: `git show bf065feedccc:evals/gap-study-3/prereg.json` failed. `round2.py` reads `{study.ROUND1_REL}/prereg.json` at round 2's commit `bf065fe` (`build_draft.py:53`). With the prior round now `gap-study-3`, that path does not exist at that commit. `round2.py` and `build_draft.py` are CP5's to re-point.
- Exit 1, `fixture_walk.py --check`: "the study root /home is not matched by the absolute-path pattern". This looks like the cloud checkout's location (`/home/user/...`) rather than a round 4 problem, and athena may not show it.

## Tests and checks run, with output

- `python3 evals/gap-study-4/copy_manifest.py --check`, after `git add` and again after the commit:
  `ok: 53 files from 1 fragment(s) (w1a-cp1-scaffold): 46 identical and 2 edited from evals/gap-study-3 at e2979b31, 5 new; 5 fixture builders byte-identical; 7 frozen paths unchanged since 68ec902f63bf`
- `python3 -W ignore evals/gap-study-4/tests/test_scaffold.py`: `Ran 21 tests ... OK`
- `python3 -W ignore evals/gap-study-4/test_round4.py`: `Ran 21 tests ... OK`
- `python3 evals/gap-study-4/run_checks.py` (after the commit):
  ```
  PASS [test_round4] exit 0 in 5.6s: python3 -W ignore evals/gap-study-4/test_round4.py
  PASS [w1a-cp1-scaffold.txt:2] exit 0 in 0.2s: python3 evals/gap-study-4/copy_manifest.py --check
  run_checks: 2 of 2 commands passed
  ```
  Exit 0.
- `git diff 68ec902f63bfbe4a18d07e0f564847531898ff95 -- evals/gap-study evals/gap-study-2 evals/gap-study-3 evals/graders evals/fixtures`: empty (0 bytes).

What the tests prove, each by mutation:

- **Manifest:**
  - A second fragment claiming `takes.py` is refused.
  - Each of the 5 fixture builders, mutated in memory, is refused, and still refused when re-recorded as `edited` with a reason.
  - `drive.py`, `check_take.py`, a lexicon and `review_kit/rounds.py`, each mutated without an `edited` entry, are refused.
  - `study.py` swapped back to its source while recorded as `edited` is refused.
  - A stray file and a missing file are both refused.
  - A copy recorded as `new` is refused.
  - A fragment with the wrong `lane`, or with an unknown status, is refused.
  - The frozen-path pin goes red when based on `e2979b31`, because round 3 gained its verification records after that commit.
  - No source is a round 3 record.
- **Imports:**
  - Every copied module loads only this folder's files, and `BLOCKED` is exact.
  - `takes.py` rewritten in memory to insert `../gap-study-3` is caught loading round 3's files.
- **study.py:** the binding is checked, and four wrong bindings (round name, prior round, arms, marker) each go red.
- **run_checks.py:**
  - Every lane file is read, and comments and blank lines are skipped.
  - A failing command fails the run.
  - The last line is exactly `run_checks: <k> of <n> commands passed`.
  - The exit is non-zero on k < n and on n = 0.
- **test_round4.py:** discovery finds `test_scaffold`, and an empty `tests/` is not a pass.

**Not run:** `tests/run_tests.py` and `tests/check_contracts.py`. The cloud contract says the whole suite is red here for environment reasons and must never be run or claimed; the home session runs it on athena. This lane touched neither `gars/_system/` nor a contract.

## Decisions (this lane's own)

- **D1. `test_round3.py` not copied.** The brief says "every top-level code file", and the plan's exception list doesn't name it. But it is round 3's battery over round 3's records, and round 3 set the precedent itself in `test_round3.py`'s docstring: "Round 2's battery is round 2's record and is not copied." Round 4's battery is `test_round4.py`.
- **D2. `README.md` not copied.** It is prose describing round 3 (counts, checks, rulings). A copy would be false here. A round 4 README is left to whoever writes the round's prose.
- **D3. `review_kit/`:** code plus `BRIEF.md` and `why.md` copied, because `build_kit.py` and `rounds.py` read them. `rounds.json` and the `prefreeze-*` reports/blindness records are excluded as round 3's review records.
- **D4. UNEDITABLE = all five copied files under `fixtures/`** (`check_fixture.py`, `copy_project.py`, `gen_project.py`, `gen_source.py`, `symbol_rulings.json`), not just the three builders the plan names. This is the stricter reading. Each must also be claimed, and from its own round 3 path.
- **D5. Every file under the folder must be claimed.** That means every file on disk or in the index, except `__pycache__`/`*.pyc`. This includes a future `COPIED.json`, so the freeze lane must claim it or exempt it explicitly.
- **D6. A `new` file byte-identical to the round 3 file at the same path is refused** as an undeclared copy. A `new` file names no source.
- **D7. An `identical` entry carrying a reason is refused,** as round 3's manifest did.
- **D8. Frozen paths are pinned at round 4's base commit `68ec902`, not `e2979b31`.** Round 3 changed between the two (its verification records were added), so pinning `evals/gap-study-3` at `e2979b31` would always fail. The base commit is exactly what "Done means" diffs against. `evals/transcript.py` and `evals/haiku-prestudy` are pinned too.
- **D9. The source for `identical`/`edited` may be any repo path that exists at `e2979b31`,** not only under `evals/gap-study-3/`. This lets a later lane copy, for example, `evals/fixtures/*` with a source. The fixture builders are held to their own round 3 path.
- **D10. `study.py` keeps the `ROUND1`/`ROUND1_REL` names,** because copied files read them, and points them at round 3. It adds `PRIOR_STUDY`/`PRIOR_REL` under honest names.
- **D11.** `run_checks.py` runs each command with `shell=True`, from the repository root, with `PYTHONDONTWRITEBYTECODE=1`. On a failure it prints the last 20 lines of that command's output.
- **D12. The import probe runs each module as `python3 <file>` would.** The file's folder is `sys.path[0]` and the cwd is neutral. `lint_language.py` imports `study` with no `sys.path` insertion of its own, relying on exactly that, so that is how it runs in practice.

## Open questions for the home session

1. `evals/fixtures/` (`gen_fastq.py`, `neutralise.py`, `rank_check.py`): the plan lists them as "fixture builders, copied byte-identical", but this lane's task named only round 3's `fixtures/`, so they are not copied. Should a later lane copy them (D9 allows a source outside round 3's folder), and should they join `UNEDITABLE`?
2. `drive.py` and `run.py` cannot import until CP5 (pre-registration) and CP3 (`labels`). Confirm that CP5's pipeline lane owns removing them from `BLOCKED` in `tests/test_scaffold.py`. That means editing this lane's test file, or moving the list.
3. `allowlist.py`, `build_draft.py` and `round2.py` now read round 3 as the prior round, so their `--check`s are red until CP5 re-derives them (see above). Is that the intended consequence of "prior round gap-study-3"?
4. Should `fixture_walk.py --check`'s "/home" study-root failure be rechecked on athena? It looks environment-specific.
5. `COPIED.json` at the freeze: under D5 it must be claimed by a fragment, or `copy_manifest.py` must exempt it. That is the freeze lane's call.

## Lessons worth keeping

- The copied modules already build their import paths from their own folder (`sys.path.insert(0, str(HERE))`), so the copy imports inside the new folder with no edit. The real coupling is `study.ROUND1`: re-pointing it at round 3 turns every "read the prior round" check red until it is re-derived.
- Probe imports the way the file actually runs. An `-c` probe without the file's folder on `sys.path` falsely failed `lint_language.py`.
- A pin on round 3 at its done commit would fail forever, because round 3 kept gaining records after `e2979b31`. Pin at the base the round was cut from.
