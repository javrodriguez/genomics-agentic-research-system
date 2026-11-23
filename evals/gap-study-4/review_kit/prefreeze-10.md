prereg.json sha256: 37fd08047b66cbaee8cc12cd05a823692e2bafebaaa599d6db53178482b5c0e3

# Pre-freeze review 10 of gap-study-4

**Ruling: DO FREEZE.**

## Commit and draft

The reviewed commit, from `COMMIT`, is `c2a2ef6d4f675c2cdb3a36127778e31cde83bf14`. `git -C study rev-parse HEAD` gives the same commit.

`diff prereg.json study/evals/gap-study-4/prereg-draft.json` prints nothing. `prereg.json` and `prereg-as-the-previous-review-read-it.json` have the same sha256 (`37fd0804…`), and `cmp` is silent on them. So the JSON diff of step 2 is empty, and the draft is the one review 9 read.

## What changed since review 9

Since review 9's records (`ae622183`), 11 commits landed, all of them fold 14.

`git diff --stat ae622183 HEAD` touches 10 files, all under `evals/gap-study-4/`:

- `copy_manifest.py` (+125);
- `result.py` (+21);
- `review_kit/BRIEF.md` and `review_kit/rounds.py`;
- two `COPIED.d` fragments and two `checks.d` files;
- two test modules.

Nothing outside the study folder changed. None of these changed either, which I checked with `git diff --quiet ae622183 HEAD -- <paths>` (exit 0):

- `box/`, `graders/`, `tasks/`;
- `freeze.py`, `check_take.py`, `routing.*`, `batch.py`, `drive.py`, `takes.py`;
- `stats.py`, `intervals.py`, `check_results.py`, `denials.py`, `variants.py`;
- the three adapters, the three transcript readers, the walk gates, `run.py`;
- the draft.

So the take path, the graders, the statistics and the draft are the bytes review 9 read. I re-read only what fold 14 changed, plus the points it touches.

**Fold 14 against review 9's M1** (a shadow of a standard-library module added in `evals/` after the freeze). The fold chose review 9's fix 2, not fix 1.

- `copy_manifest.later_files_problems` (`copy_manifest.py:604-695`) now reads `evals/` and the repository root as well as the study folder. It refuses:
  - any path that is added, changed or re-moded since the freeze commit and that an import can reach (`shadow_shaped`, `:562-583`);
  - a symbolic link or submodule anywhere in those places.
- `result.py:408-423` calls `copy_manifest.py --later-files HEAD` in an isolated child (`-I -B`). It does this before writing or checking the page, so the guard no longer depends on `ci.yml` alone. That answers review 9's m-new-2 in part.
- `check_take.py:70` still puts `evals/` ahead of the standard library. The fold detects a shadow; it does not remove the cause.

I tested the guard myself in a throwaway clone inside this folder, deleted afterwards. I committed a stand-in `prereg.json` as the "freeze", then added files one at a time and ran `python3 -I -B evals/gap-study-4/copy_manifest.py --later-files HEAD`:

```
## evals/shlex.py                       FAIL evals/shlex.py is on a study process's import path and the freeze commit … does not hold it
## after delete (history only)          later files: reported: evals/shlex.py (only in history) … ok
## evals/abc/__init__.py                FAIL evals/abc/__init__.py is on a study process's import path …
## evals/tomllib symlink                FAIL evals/tomllib is on a study process's import path …
## study non-importable (notes.txt)     … ok, … reported
## root sitecustomize.py                FAIL sitecustomize.py is on a study process's import path …
## evals/x/shlex.pyw                    … ok (not importable on POSIX)
```

So review 9's road is now refused at HEAD, at publication (`result.py`) and in CI. That road was one file added after the freeze and kept. What is left is the history-only variant (minor r10-1) and the unpinned CI step (minor r10-2).

Under this round's stop rule, review 9's M1 would itself have been a MINOR: it is a deliberate act, it shows in public git history, and it moves no reading in an honest run.

**Does fold 14 stop the real road?** I looked for an honest post-freeze write that the new refusal would catch, and found none:

- A run writes take folders under `takes/`, the `RUNTIME_PATHS` (`check_results.py`) and the `LATER_RUN_FILES` (`copy_manifest.py:529`). All of these are skipped as run outputs. Of the walk, take and labelling folders, the only `.py` files tracked are the five existing `labelling/*.py` modules, which the freeze holds.
- No study code writes into `evals/` outside the study folder. Its only `REPO / "evals"` references read earlier rounds' files.
- `evals/transcript.py`, which the checker imports, is in `CHECKER_CODE_FILES` (`check_take.py:2610`) and in the copy record's unchanged paths (`copy_manifest.py:111`). It is bound before the freeze and now refused if it changes after it.
- The root has no `.py` file and no package `__init__`. The study runs on its own branch (`freeze/r4-20261021`).

The one place the new rule narrows an honest plan is CP8's still-unbuilt reader (minor r10-4). It must live outside the study folder and outside importable `evals/`, and the draft does not say so. A permitted place exists, so the road is not stopped.

**Fold 14's prompt pin.** `review_kit/rounds.py` now pins the review prompt in two eras:

- `PROMPT_ROUNDS_1_TO_9` (`4246efa5…`) for prefreeze rows 1-9;
- `PROMPT_FROM_ROUND_10` (`7712a8fa…`) for every later row and every verify row.

It refuses a `BRIEF.md` that hashes to anything else. This round's `BRIEF.md` differs from `study/evals/gap-study-4/review_kit/BRIEF.md` only in the filled-in `{N}` and `{PREVIOUS}` placeholders. `rounds.py --check` prints `prompt pinned at 7712a8faa095, rounds 1-9 at 4246efa5b409`. The draft's sentence about the prompt being pinned byte-identical from round to round is now stale (minor r10-3).

## Threat model, restated

After the takes exist, the operator could try to move a count, label or published sentence. They could do it by editing, re-dating, re-running, re-routing, re-ordering or misfiling one record. They could also choose among commits, seeds or reviews, or change code, configuration, pins or imported files after the freeze. During a take, the agent could try to reach past its run tree and its harness's one model host: to a credential, to the study's files and graders, or to the evidence the graders read. It could also try to make a step it did not take look taken.

Out of scope, as limitations the draft must name: a complete, coherent fabrication across every ledger; what a vendor serves beyond its client's records; and the honesty of the machines and the runner beyond their committed outputs.

Two corrections, carried from reviews 7-9, which I agree with:

1. Choosing the review and performing the freeze come *before* the takes. So the operator's window for those choices runs from the last review to the freeze commit.
2. Committed records that stand for outside facts are in scope as committed outputs. These are the push-witness record and the frozen beacon reading. Only the machine's honesty beyond them is out of scope.

For this round, only an honest-run error, a published claim false in an honest run, or a stopped real road is a MAJOR. A deliberate operator act that shows in public history and moves no honest reading is a MINOR limitation.

**Do the draft's disclosure fields say honestly what the checks bind?**

- `box_residuals` (13 entries) and `not_poolable` remain honest about the take side. `not_poolable` names rounds 1-3 and is enforced by `lint_pooling.py` and `result.py`.
- `predictions_rule` is honest: all 126 predictions are `null` with "no informed basis", and no walk informs one.
- `round_4_limitations[6]` trusts "the driver, checker, routing and batch code at the frozen commit". With fold 14 that is now nearly true at HEAD. But the draft does not say:
  - that a module imported from `evals/` or the root is held only by a later-files guard;
  - that the guard runs in CI and in `result.py`, not in `check_results.py`;
  - that a shadow used and then deleted is printed, not refused.

  Those are disclosure gaps (r10-1, r10-2), not honest-run errors.
- Review 9's carried disclosure items stand, because the draft is unchanged:
  - `[4]` "never by anything the operator commits" overstates the offline binding of the beacon reading (m-new-1);
  - `[1]` understates the "committed unedited" binding (m2);
  - `[10]` is stale on the prompt pin (r10-3).

## MAJOR findings

None. I lean firmly that nothing I found is a reading or count wrong in an honest run, a published claim false in an honest run, or a stopped real road.

The closest candidate is r10-4. CP8's reader cannot be added under the study folder or importable `evals/` after the freeze. But a permitted place exists, a folder name with a hyphen, as the copy-manifest docstring notes. So the road is narrowed and must be stated, not stopped. I class it MINOR.

## Other findings

### MINOR

- **r10-1, new: a shadow import used and then deleted is reported, not refused, and `evals/` is still ahead of the standard library in the checker.**
  - Where: `check_take.py:70` and `denials.py:32` still put `evals/` before the standard library. `copy_manifest.py:689-693` prints a shadow-shaped path seen only between the freeze and HEAD as `(only in history)` and does not fail. My clone run above shows this: `reported: evals/shlex.py (only in history) … ok`.
  - The road: add a shadow, let athena's take-time checker read through it, delete it before publication. It is visible in public history and as a printed CI line. It moves a reading only through take-time decisions that the publication's regrade does not re-derive. In an honest run it moves nothing.
  - Fix: review 9's fix 1, appending `evals/` after the standard library. That is a `CHECKER_CODE_FILES` edit, so it costs a walk recheck wave. Otherwise, name the residual in the write-up beside `[6]`. Either fix tightens.
- **r10-2, new; it narrows review 9's m-new-2: the later-files guard is not on every publication road.**
  - `ci.yml` is unpinned. Its "workflow diff is additive" step (`ci.yml:503-509`) counts only removed lines, so an added `continue-on-error: true` or `if:` line switches the Copy record step off without going red.
  - `result.py` now calls the guard. But `check_results.py`, which reads a page written by hand, does not. The new docstring says so (`result.py:410-415`).
  - It is deliberate and shows in public history. Fix: call the same subprocess from `check_results.check_publication`. That tightens.
- **r10-3, new, a stale sentence (the orchestrator's note).**
  - `round_4_limitations[10]` says "The reviewer's prompt is pinned byte-identical from round to round."
  - Correction for the write-up: "pinned byte-identical within prefreeze rounds 1-9 (`4246efa5…`) and within every later round, verify rounds included (`7712a8fa…`); the one change between the two is the stop rule and the note beside it (`review_kit/rounds.py` `prompt_problem`)."
  - It moves no reading and tightens disclosure.
- **r10-4, new: the draft does not say where CP8's still-owed reader may live after the freeze.**
  - `labelling/sheet.py:22-27` says the reader of a take folder that writes the post-probe content is "not built here (Q-w11d-2)". The labelling sheet's own acceptance test depends on that reader.
  - After the freeze, `--later-files` refuses that reader under the study folder or under any importable path in `evals/`, and both CI and `result.py` then refuse the page. The draft's `labelling_design` and `labelling_rules` name neither constraint.
  - Lean MINOR, not MAJOR: a permitted place exists (a hyphenated folder, or a folder outside `evals/`), and the copy-manifest docstring (`:621-623`) names it. Fix: one sentence in the write-up or the CP8 brief naming the permitted location. That tightens, and moves no reading.
- **m-new-1 (carried from review 9).** The frozen beacon reading is held offline only to its shape. The relay readback and the push witness's refusals reach publication only through the operator-committed `problems` field of `witness-record.json`. `[4]` overstates. Fixing it tightens.
- **m2 (carried).** `[1]` says "'committed unedited' is not enforced". It is enforced, by the report digest, `freeze.committed_once_problem` and `check_results.freeze_recheck_problems`. Disclosure only.
- **m-new-3 (carried).** The launch binding leaves out `rehearsals/w*/`. The walk gates re-derive the walks. Fixing it tightens.
- **m10 (carried).** The walk path gate does not read sub-agent streams (`rehearsals/w255/subagents/`). The gate's printed claim covers two walks too widely. Walks are never counted. Fixing it tightens.
- **m1c (carried).** The unknown-phase early return at `batch.py:512` lets a take be re-run after its end state is seen. It is named in `[13]`, it is an operator act, and in an honest run it moves nothing. Fixing it tightens.
- **m7 (carried).** The hashed codex template leaves out the per-take trust table (`box/take_config.py`). Fixing it tightens.
- **m1, m3, m4, m5, m6, m8 (carried; files unchanged).** Each is disclosure or presentation. The model rows and the agent-system rows stay under separate headings in `stats.py` (`TABLE_HEADINGS["agent_system"]`, `:1064`, `:1188-1189`). Each fix tightens.

### NIT

- **n10-1.** Athena file 19's name still says legs i-ii, while its command line says i-iii (carried).
- **n10-2.** To read the `COMMANDS` constant for step 3, I imported `freeze_rehearsal` as a module under `-B`. I did not run its main. I note it because the brief lists that file among those not to run. Nothing was written: `git status --short --ignored` was empty afterwards.
- **n-carried.** Review 9's n-new-1 (`frozen_at` is unbounded) and n-new-2 (fragment reasons are not updated for later edits). Review 6's n2. Review 5's n1-n8 and n10.

### Read and found sound

- **Copy record (step 6).** `copy_manifest.py --check` reports 881 files from 111 fragments: 22 identical, 29 edited, 830 new. I compared all 22 `identical` entries byte for byte with their sources at `e2979b31` (round 3) or `68ec902f` (shared files), and 0 differ. Fold 14's fragment (`COPIED.d/fold14-prompt-pin.json`) claims its fragment, test module and `checks.d` file as `new`, as their reasons say.
- **System under test.** `variants.PINNED_TREE` is `844a4ce0…`. `git rev-parse 844a4ce0…:gars` gives `8a54e0f8cd91…`, which equals `check_take.GARS_TREE_SHA` (`check_take.py:2027`).
- **Steps 7-11** are unchanged since review 9 in every file they read: the container, the vendor arms, the routing, the graders, the walks and publication. Review 9's readings stand, and I re-confirmed them through the gates:
  - `freeze.py --check` passes 8 of 8 legs, and the three-leg check prints `every leg holds`;
  - `probes4.py --check` grades 1690 cells with 0 defects;
  - `routing.py --check` proves the no-match defaults;
  - the walk gates, athena 11-17, are green at `COMMIT`.
- **Zero-item passes.** Every take-side check says it measured nothing ("no takes; … measured", and from `denials.py`, "Not a pass."). None prints a pass over zero items.

## Step 3: the athena files

All 19 files name commit `c2a2ef6d4f675c2cdb3a36127778e31cde83bf14`, which equals `COMMIT`. Together they cover:

- `run_checks.py`;
- each of the 16 members of `freeze_rehearsal.COMMANDS` (the base commands, `WALK_COMMANDS` and `WALK_PIN_COMMANDS`), each in its own file 02-17;
- `freeze.py --check` (18) and the three-leg check (19).

| file | command | exit | last line |
|---|---|---|---|
| 01 | `run_checks.py` (battery mode) | 0 | `run_checks: 537 of 537 commands passed` |
| 02 | `test_round4.py` | 0 | `OK (skipped=62)` (6121 tests) |
| 03 | `copy_manifest.py --check` | 0 | `ok: 881 files from 111 fragment(s) (…)` |
| 04 | `tests/test_box_integration.py` | 0 | `OK` (61 tests) |
| 05 | `tests/test_pipeline.py` | 0 | `OK` (90 tests) |
| 06 | `probes4.py --check` | 0 | `probes4: 9 tasks, 18 halves, 169 rows, 1690 cells graded, 0 defects, 0 problems` |
| 07 | `build_draft.py --check` | 0 | `ok: the committed draft is what build_draft.py builds` |
| 08 | `leak_grep.py --check` | 0 | `ok: 25 leak word(s) grepped against 386 real session(s); none would void one; 1 session(s) not grepped (unreadable, named above)` |
| 09 | `holdout.py --check` | 1 | `OWED: holdout.py --check lives in private aegis (ruling C4); … so it did not run and this rehearsal is not all green`. It names itself as not run, as required. |
| 10 | `review_kit/rounds.py --check` | 0 | `ok: 9 registered round(s) graded, every report committed, 0 voided; prompt pinned at 7712a8faa095, rounds 1-9 at 4246efa5b409` |
| 11 | `walk_register.py --check` | 0 | `ok: 387 registered walk(s), each with its folder, none counted` |
| 12 | `mode_binding.py --walks --check` | 0 | `36 of them are input-side only: … never a mode the session recorded.` |
| 13 | `fixture_walk.py --check` | 0 | `ok: 387 committed walk(s) graded, each read through its own harness's reader, … 41 by a recorded per-walk exception, printed above` |
| 14 | `run.py --walks --check` | 0 | `run: 387 walk(s) regraded, every grade.json the regrade's bytes (313 graded, 74 pending documents that grade nothing yet); never counted` |
| 15 | `walk_regrade.py --check` | 0 | `walk_regrade: ok` |
| 16 | `walk_plan.py --coverage --require-run-arms` | 0 | `ok: every required walk of the arms the freeze runs is covered` |
| 17 | `walk_pins.py --check` | 0 | `walk_pins: 387 registered walk(s) read; every one on the draft's version pins and image ids, …` |
| 18 | `freeze.py --check` | 0 | `freeze: 881 fragment-claimed files and 4 native-reader record(s) owned; 8 of 8 legs hold; no takes or freeze performed` |
| 19 | `freeze.unrecorded_shapes_problem(…)`: legs i-iii | 0 | `every leg holds` |

No red is left unexplained. The only non-zero exit is 09, the owed holdout step, which names itself as not run.

## Step 4: the light checks, run from `study/`

I ran these with `PYTHONDONTWRITEBYTECODE=1`. Every command exited 0. `git status --short --ignored` was empty afterwards.

| command | tail |
|---|---|
| `copy_manifest.py --check` | `ok: 881 files from 111 fragment(s) (…) … 22 identical and 29 edited (round 3 at e2979b31, shared files at 68ec902f), 830 new; 5 fixture builders byte-identical; 8 frozen paths unchanged since 68ec902f63bf` |
| `freeze.py --check` | `freeze: 881 fragment-claimed files and 4 native-reader record(s) owned; 8 of 8 legs hold; no takes or freeze performed` |
| `freeze.unrecorded_shapes_problem(…)` | `every leg holds` |
| `build_draft.py --check` | `ok: the committed draft is what build_draft.py builds` |
| `leak_grep.py --check` | `ok: 25 leak word(s) grepped against 386 real session(s); none would void one; 1 session(s) not grepped (unreadable, named above)` |
| `probes4.py --check` | `probes4: 9 tasks, 18 halves, 169 rows, 1690 cells graded, 0 defects, 0 problems` |
| `routing.py --check` | the no-match proof, ending `before-first-turn, last turn none (no turn ran) -> route rehearsal` |
| `contracts.py --check` | `every stored sentence is a byte substring of the blob it was pinned to` |
| `harness_bookkeeping.py --check` | `harness_bookkeeping: ok: 3 harness(es): claude-code, codex, gemini` |
| `denials.py --check` | `ok, having read 0 graded takes: none is committed yet, so nothing here is evidence about any denial. Not a pass.` |
| `completeness.py --check` | `completeness: no takes; no cells measured` |
| `takes.py --check` | `takes: no takes; no registration or outcome measured` |
| `costs.py --check` | `costs: no takes; no cost measured or written` |
| `stats.py --check` | `stats --check: no takes (0 results files); nothing was compared` |
| `intervals.py --check` | `done-commit binding: 15 of 15 results files equal their blobs` / `gap-study intervals: PASS` (it re-derives the earlier rounds' intervals and adds nothing to this round) |
| `result.py --check` | `result: no takes; no table measured or written` |
| `check_results.py --check` | `check_results: no takes; no frozen pins or publication measured` |
| `batch.py --check` | `batch: routing.json ready` |
| `lint_language.py evals/gap-study-4/` | `clean — 233 input(s) scanned, 104 excused line(s) on record` |
| `lint_pooling.py evals/gap-study-4/` | `clean — 229 file(s) and 0 commit(s) scanned, no excusal path` |
| `prereg.py --status` | `This is a DRAFT. No take may run against it and no number may be graded from it. …` (1260 planned rows, 126 half-cells) |
| `review_kit/rounds.py --check` | `ok: 9 registered round(s) graded, every report committed, 0 voided; prompt pinned at 7712a8faa095, rounds 1-9 at 4246efa5b409` |
| `copy_manifest.py --later-files` (an extra command I ran) | `later files: not applicable, not frozen` |

## Findings

| # | finding | class | loosens or tightens | would fixing it change a criterion, a reading or a claim? |
|---|---|---|---|---|
| r10-1 | The checker still puts `evals/` ahead of the standard library. A shadow module added after the freeze, used at take time and then deleted is only printed "(only in history)", not refused. The draft does not name this. | MINOR | tightens | A claim (`[6]`'s trust in the frozen code becomes exact, or is named). No honest reading. |
| r10-2 | The post-freeze later-files guard runs in unpinned `ci.yml`, which an added line can switch off past the additive-diff step, and in `result.py`. It does not run in `check_results.py`, which reads a hand-written page. | MINOR | tightens | No reading. It would bind the guard on every publication road. |
| r10-3 | `round_4_limitations[10]` says the prompt is pinned byte-identical from round to round. It is now pinned in two eras (rounds 1-9; round 10 on). Corrected in the write-up. | MINOR | tightens | A claim (disclosure). No reading. |
| r10-4 | After the freeze, the owed CP8 take-folder reader may not live under the study folder or under importable `evals/`. The draft and the labelling rules do not say where it may live. | MINOR (lean; a permitted place exists, so the road is narrowed, not stopped) | tightens | A claim (disclosure of the plan). No reading. |
| m-new-1 | The frozen beacon reading is held offline only to its shape, and the witness refusals reach publication only through an operator-committed field. `[4]` overstates. (carried) | MINOR | tightens | A claim (`[4]`). No reading. |
| m2 | `[1]` says "committed unedited" is not enforced, but it is. (carried) | MINOR | tightens | Disclosure only. |
| m-new-3 | The launch binding leaves out `rehearsals/w*/`. (carried) | MINOR | tightens | No reading. |
| m10 | The walk path gate does not read sub-agent streams (w255, w260). (carried) | MINOR | tightens | The gate's printed claim, for two walks. No count. |
| m1c | An unknown-phase take can be re-run after its end state is seen; named in `[13]`. (carried) | MINOR | tightens | No honest reading. It closes an operator road. |
| m7 | The hashed codex template leaves out the per-take trust table. (carried) | MINOR | tightens | The hashed-bytes claim becomes exact. No reading. |
| m1 | Take-path code changed after the take order was public, and the draft does not say it may. (carried) | MINOR | tightens | Disclosure only. |
| m3 | Beacon swaps are unbounded and not printed on RESULT.md. (carried) | MINOR | tightens | Disclosure only. |
| m4 | Two agent-caused driver stops are missing from `[2]`. (carried) | MINOR | tightens | Disclosure only. |
| m5 | Arm A's account state is missing from the vendor-account residual. (carried) | MINOR | tightens | Disclosure only. |
| m6 | The settings hot-reload gap is in code, not in the draft. (carried) | MINOR | tightens | Disclosure only. |
| m8 | A table heading groups model and agent-system rows. (carried; `stats.py` keeps them apart under separate headings) | MINOR | tightens | Presentation only. No count. |
| n10-1 | Athena file 19's name says legs i-ii, but its command says i-iii. | NIT | n/a | No |
| n10-2 | This review imported `freeze_rehearsal` as a module to read `COMMANDS`, without running it. Nothing was written. | NIT | n/a | No |
| n-carried | Review 9's n-new-1 and n-new-2, review 6's n2, and review 5's n1-n8 and n10, unchanged. | NIT | n/a | No |
