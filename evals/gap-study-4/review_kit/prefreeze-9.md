prereg.json sha256: 37fd08047b66cbaee8cc12cd05a823692e2bafebaaa599d6db53178482b5c0e3

# Pre-freeze review 9 of gap-study-4

**Ruling: DO NOT FREEZE.**

The reviewed commit, from `COMMIT`, is `d1f8717821a82d229f97337c31b23a8748d6ac2e`, and `git -C study rev-parse HEAD` gives the same commit. `review_kit/rounds.json` at this commit holds rows 1-8. Row 9 is expected to land in a later commit with `launch_commit` equal to `COMMIT`.

`diff prereg.json study/evals/gap-study-4/prereg-draft.json` prints nothing. `cmp prereg.json prereg-as-the-previous-review-read-it.json` is also silent, and the two files have the same sha256. The draft has not changed since review 8, so the JSON diff of step 2 is empty.

Since review 8 (`272d8fe2`), 335 commits landed:

- 312 are walk rechecks: `recheck-3.json` or `recheck-5.json` in 313 walks, plus `register.json`. Each one moves `checker_constants_sha256` from `42de3630…` to `2686bf79…`, and none is counted.
- The rest are review 8's records and folds 11-13.
- `git diff --stat 272d8fe2 HEAD`, with `rehearsals/` excluded, lists 26 files. They are `check_results.py` (+352), `copy_manifest.py` (+119), `lint_language.py`, `lint_pooling.py`, `language-allowlist.json`, `review_kit/rounds.py`, the new `review_kit/claim_review.py`, `ci.yml`, two `checks.d` files, two fragments, review 8's report and blindness record, and tests.
- Nothing under `box/`, `graders/` or `freeze.py` changed. Nor did `routing.*`, any adapter or transcript reader, `check_take.py`, `batch.py`, `drive.py`, `takes.py`, `result.py`, `stats.py`, `intervals.py`, the walk gates, `tasks/`, `variants*` or the draft. I checked this with `git diff --quiet 272d8fe2 HEAD -- <those paths>`, which exits 0.

**Review 8's M1 is closed.** `check_results.freeze_recheck_problems` (`check_results.py:1221-1310`) runs inside `check_frozen_content` on every post-freeze check. It re-reads the freeze at its own commit and parent, and does the following:

- It refuses a freeze commit that has no parent, more than one parent, or an edited `frozen_at_commit_parent`. It also refuses one that touches any path but freeze.py's three outputs.
- It requires `draft_sha256_at_freeze` to be the sha256 of the draft committed there, and `keys_outside_the_freeze` to be empty. Every written key must be present, and the tip limit must be held (`result.tip_limit_held`).
- It requires the named review to be committed at the parent, with its digest and a DO FREEZE ruling.
- It re-runs `review_file_problems` as of the parent, through a temporary git directory that shares the object store.
- It rebuilds the frozen file with `freeze.prepare` from the parent's committed pins and compares the result byte for byte (`frozen_file_problems`).

Each clause has its own test and mutant in `tests/test_fold11_freeze_recheck.py`, run by `checks.d/fold11-freeze-recheck.txt` inside athena 01's 535 green commands.

Reading the edges of that fix and of fold 13's companion guard against a later file shadowing a module led to the one MAJOR below.

## Threat model, restated and corrected

After the takes exist, the operator could move a count, label or published sentence. They could edit, re-date, re-run, re-route, re-order or misfile one record. They could choose among commits, seeds or reviews. Or they could add or change code, configuration or pins after the freeze. Inside a take, the agent could try to reach past its run tree and its one vendor host, to a credential, to the study's files and graders, or to the evidence they read. It could also make an untaken step look taken.

Two corrections:

1. As reviews 7 and 8 said, choosing a review and performing the freeze happen *before* the takes exist. So the operator's window runs from the last review to the freeze commit.
2. Some records are committed by the operator's own machine but stand for outside facts: the push-witness record (`witness-record.json`) and the beacon reading in the frozen file. The brief puts those committed outputs *in* scope. Only the machine's honesty beyond what it commits is out of scope. The draft (`round_4_limitations[6]`, `[11]`) puts those records under the runner's trust instead. I judge findings against the brief's line, and say where the draft's naming makes a finding a limitation rather than a defect.

These stay out of scope, as limitations the draft must name: a complete, coherent fabrication across every ledger; what a vendor serves beyond its client's records; and the honesty of the machines and runner beyond their committed outputs.

Judged on that statement:

- `box_residuals` (13 entries) and `not_poolable` are honest about the take side. `not_poolable` forbids comparison, pooling and bridging with rounds 1-3, enforced by `lint_pooling.py` and `result.py`.
- `predictions_rule` is honest: all 126 predictions are `null`, "no informed basis", and the 387 walks inform none of them.
- `round_4_limitations[6]` trusts "the driver, checker, routing and batch code at the frozen commit". Nothing in the draft says that code can be made to run something that is *not* at the frozen commit, without any pinned file changing. That is M1.
- `[4]` says the order is seeded "never by anything the operator commits". Offline, the frozen beacon reading is held only to its own shape (m-new-1).
- `[1]` still understates a binding (m2, carried).

## MAJOR findings

### M1. A single file added to `evals/` after the freeze replaces a standard-library module inside the take checker and the graders, and no check reads it

**Where.**

- `check_take.py:70` inserts the repository's `evals/` folder at the front of `sys.path`, ahead of the standard library: `sys.path.insert(0, str(REPO / "evals"))`. The study folder goes in front of it at `:71`. `denials.py:32` does the same.
- After that line, `check_take.py` imports these modules for the first time at module level:
  - `shlex` (`:7534`), used to split codex command lines (`:7790`, `:7823`);
  - `tomllib` (`:6302`), used to read the codex config that mode binding checks (`:6660`, `:6872`, `:6931`);
  - `contextvars` and `subprocess` (`:2226-2227`).
- The graders import `shlex` too (`graders/plan_gate.py:161`, `graders/precondition_refusal.py:161`, `graders/new_tasks.py:203`). Once one copy is in `sys.modules`, it is the copy every grader uses.
- Fold 13 added `copy_manifest.py --later-files` because of its own probe: a `fractions.py` committed in the study folder after the freeze ran inside `check_results.py --ledger` and passed. That guard reads only the study folder, and its docstring says so (`copy_manifest.py:568`): "THE LIMITS. Only this folder is read, so the same file one folder up (evals/, the repository root) is not named."
- `freeze.BOUND_OUTSIDE` pins only `CLAUDE.md` and one price table outside the study. `.github/workflows/ci.yml`, which is where the `--later-files` step lives, is not pinned either.
- The draft names a standard-library patch only for the order function hash (`[12]`), never for the checker or graders.

**Shown.** First, read-only on `study/`, with an import logger:

```
$ python3 -B - <<'E'   # log stdlib modules first imported while evals/ is ahead of the stdlib
… import check_take, then the graders, transcript readers, stats, result …
E
dataclasses <- evals/gap-study-4/transcript_view.py:130
decimal <- evals/gap-study-4/stats.py:111
fractions <- evals/gap-study-4/stats.py:111
shlex <- evals/gap-study-4/check_take.py:7534
tomllib <- evals/gap-study-4/check_take.py:6302
unicodedata <- evals/gap-study-4/walk_register.py:75
… (25 modules in all)
```

Then in a throwaway local clone, made inside this review folder and deleted afterwards. In the clone I added four files, `evals/{fractions,shlex,dataclasses,unicodedata}.py`. Each one prints a marker and then loads the real module:

```
$ python3 -B evals/gap-study-4/check_take.py --help      # the command drive.py:904 names
SHADOW: evals/fractions.py was imported in place of the standard library's fractions
SHADOW: evals/dataclasses.py was imported in place of the standard library's dataclasses
SHADOW: evals/shlex.py was imported in place of the standard library's shlex
usage: check_take.py [-h] --task TASK --half {positive,control} [--row ROW]

$ python3 -B -c "import sys; sys.path.insert(0,'evals/gap-study-4')
import check_results, batch, prereg, routing, stats, takes, transcript_view, variants, mode_binding, walk_register, pending_walk
from graders import delegation, labels4
import check_take"                                     # run.py's import order, the publication regrade's road
SHADOW: evals/shlex.py was imported in place of the standard library's shlex
```

**What a single added file does.** Suppose the operator commits `evals/shlex.py` after the freeze and before the takes. Its `split` could, for example, drop one argument pattern. Then:

- The take checker on athena and the graders' forbidden-action readers parse every agent command through it.
- The publication regrade parses through it too, so the committed grades and the regrade agree.
- `check_pins` passes, because no pinned path changed. The copy record passes, because it reads the freeze commit's files. `--later-files` does not read `evals/`.
- `checker_constants_sha256` binds only `CHECKER_CODE_FILES`, so the walks and takes still read as checked under the constants in force.

A forbidden action can then read as not taken, or the reverse, in every view, and every check stays green. Adding the file after some takes already ran is no better for the operator: the regrade would differ from the committed reading and publication would be refused. So the road is "add one file right after the freeze". It needs no fabricated chain of records, only one file in public history that no check looks at. This is the same class as fold 13's own probe, one folder up.

**Why it is material.** The claim that every reading is the reviewed checker's verdict rests on code the freeze pins. Here the reading moves by an import that no pin covers. The draft does not name it, and a docstring is not the draft. `copy_manifest.py`, `check_take.py`, `denials.py` and `check_results.py` are pinned, and CI runs the freeze commit's copy of the copy record. So the fix can land only before the freeze.

**Cheap fixes, each verifiable by a command. Any one closes it:**

1. Put `evals/` *after* the standard library rather than in front of it. In `check_take.py:70` and `denials.py:32`, use `sys.path.append` or insert after the stdlib entries, and keep the study folder first.
2. Extend `later_files_problems` to every folder the study puts on `sys.path` (`evals/`, and the repository root for safety), and call it from `check_results.py` itself, not only from unpinned `ci.yml`.
3. Add a module-origin audit in `check_results.main` and at the end of `check_take`. It would refuse when any module in `sys.modules` has a `__file__` outside the standard library and outside the pinned paths.

Add a mutant that commits `evals/shlex.py` in a scratch frozen tree and expects red.

**Lean.** MAJOR, moderate-to-high confidence.

- Against: the file is in public history, and the operator has to write a deliberate shadow module.
- For: review 8's M1 was the same kind of visible single edit and was ruled MAJOR. The study's own probe found this class and fixed only half of it. The brief names "a change to code … after the freeze" as in scope. And the fix is a line or a short function that can be made only now.

## Other findings

### MINOR

- **m-new-1, new: the frozen beacon reading and the push witness are bound offline only by records the operator writes.**
  - `frozen_file_problems` rebuilds the frozen file with `beacon=frozen.get("take_order_beacon_reading")` (`check_results.py:1139`). `order_beacon.reading_problems` checks only the reading's shape, round, time and `randomness == sha256(signature)` (`order_beacon.py:433-452`). So in the review-to-freeze-commit window, a hand-written signature for the registered round, round 33536472, passes every offline check, and gives another seed and another order. The new docstring at `check_results.py:1180-1183` says as much.
  - Only `frozen_network_problems` reads the relays back, and only under `--witness`. Its result reaches publication solely through `witness-record.json`'s `problems` field. `witness_publication_problems` (`:739-785`) re-derives the counts in that record but not its `problems`. The same field is all that carries the push witness's "abandoned history" refusal.
  - The draft names the record as on the runner's trust (`[6]`, `[11]`). `[4]`'s "never by anything the operator commits" overstates it.
  - Why only MINOR: the order is chosen before any take exists, so it gives no outcome-informed leverage. And an unpushed reset is already a named, wider road around the push witness.
  - A CI step running `check_results.py --witness`, without `--record`, on GitHub's own runner would bind both. Fixing it tightens the check and corrects `[4]`.
- **m-new-2, new.** `ci.yml` is not pinned (`freeze.BOUND_OUTSIDE` is `('CLAUDE.md', 'lane-reports/…/price-table.json')`). Fold 13's only post-freeze call of `--later-files` is in `ci.yml`, and `checks.d` runs it at HEAD only when the battery is run. So the post-freeze shadow guard for the study folder itself can be switched off by editing an unpinned file. It overlaps with M1's fix 2. Fixing it tightens the check.
- **m2 (carried from reviews 6-8).** `round_4_limitations[1]` still says "'committed unedited' is not enforced". It is enforced by the report digest and by `freeze.committed_once_problem`, and now also by `freeze_recheck_problems`. Fixing it tightens disclosure only.
- **m-new-3 (carried).** `launch_binding_problem` leaves out `rehearsals/w*/`. 313 walk files were added again this round without a new round being needed. The walk gates (athena 11-17) re-derive them, so an edited walk still needs a coherent regrade. Fixing it tightens the check.
- **m10 (carried).** `rehearsals/w255/subagents/` exists, and `grep -c subagents fixture_walk.py` gives `0`. Fixing it tightens the check.
- **m1c (carried).** The unknown-phase early return is still at `batch.py:512`. It is named in `[13]`. Fixing it tightens the check.
- **m7 (carried).** The hashed codex template leaves out the per-take trust table (`box/take_config.py`). Fixing it tightens the check.
- **m1, m3, m4, m5, m6, m8 (carried; files unchanged since review 8).** Each fix tightens disclosure or presentation, and none moves a count.

### NIT

- **n-new-1.** `frozen_at` is taken from the frozen file into the rebuild, and nothing bounds it. It could be held between the parent's and the freeze commit's committer times. No code reads it.
- **n-new-2 (carried class).** Fold 11-13 edits to files first claimed `new` (`check_results.py`, `copy_manifest.py`, `lint_language.py`, and others) leave their fragment reasons unchanged. The commit bodies explain the edits.
- **n-new-3.** Athena file 19's name still says legs i-ii, while its command line says i-iii.
- **n-carried.** Review 6's n2 and review 5's n1-n8 and n10 are unchanged.

### Read and found sound

- **Fold 11 against review 8's M1.** Read in full, as summarised above. The `NOT CHECKED` exits are a non-repository copy, a root commit under `--rehearsal-plan`, and a parent mismatch in `frozen_commit_problems`. The first two print and pass only for a disposable rehearsal. The parent mismatch is now refused by `freeze_recheck_problems`. CI runs `check_results.py` and `--ledger` without `--rehearsal-plan` (`ci.yml:545`, `:554`), with `fetch-depth: 0`.
- **The lint exemption by rule from round 9 on** (`lint_language.is_bound_review_report`). It needs only a sibling blindness file stating the report's digest. But after the freeze, any committed `prefreeze-N.md` beyond the seed makes the parent-side `later_review_problem` (reading `--all --reflog`) refuse publication. So a self-certified report cannot carry unscanned words into a publishable tree.
- **`register_growth_problem`.** After the freeze it admits only appended, numbered verify rows whose launch commit is on the line. `rounds.py --add --kind prefreeze` refuses once frozen.
- **Copy record (step 6).** `copy_manifest.py --check` gives 876 files from 110 fragments: 22 identical, 29 edited and 825 new. I compared all 22 identical entries byte for byte with their sources at `e2979b31` or `68ec902f`, and 0 differ. Fold 11's fragment names its four new files.
- **System under test.** `variants.PINNED_TREE` is `844a4ce0d894…`. `git rev-parse 844a4ce0…:gars` gives `8a54e0f8cd91…`, which equals `check_take.GARS_TREE_SHA`.
- **Container (step 7), unchanged since review 8 and re-read at the points that matter.**
  - Entry: `docker create` with a keep-alive PID 1, then every agent action is a `docker exec`.
  - Isolation: `--cap-drop ALL`, `no-new-privileges` and `--read-only` with tmpfs (`box/run_take.py:935-950`).
  - Mounts: exactly two bind mounts, the run tree and the config folder.
  - Hosts: one per harness through the proxy: `api.anthropic.com`, `chatgpt.com` and `generativelanguage.googleapis.com` (`box/egress/proxy_conf.py:49-52`).
  - Credentials: `CLAUDE_CODE_OAUTH_TOKEN` (arm A); an `auth.json` lease under `CODEX_HOME` (arm O); `GEMINI_API_KEY` (arm G) (`run_take.py:163-175`, `:376`). Each is named in `box_residuals`.
- **Vendor arms (step 8).** `freeze.py --check` passes 8 of 8 legs, and the three-leg check prints "every leg holds". Arm G is deferred, and its 0-of-18 coverage is printed as recorded, not required. No adapter, template, lock, price table or routing marker changed since review 8. `stats.py` and `result.py` are unchanged, and so is review 8's reading that model rows and agent-system rows are kept apart.
- **Outcome, walks, publication (steps 9-11).** `routing.py --check` proves the no-match defaults. `probes4.py --check` grades 1690 cells with 0 defects. Every take-side gate says it measured nothing, and none prints a pass over zero items. Both lints are clean. The walk gates are green at `COMMIT` (athena 11-17).

## Step 3: the athena files

All 19 files name commit `d1f8717821a82d229f97337c31b23a8748d6ac2e`, which equals `COMMIT`. Together they cover `run_checks.py` (534 `checks.d` lines plus the battery make the 535), every member of `freeze_rehearsal.COMMANDS` (base, `WALK_COMMANDS` and `WALK_PIN_COMMANDS`) and `freeze.py --check`.

| file | command | exit | last line |
|---|---|---|---|
| 01 | `run_checks.py` (battery mode) | 0 | `run_checks: 535 of 535 commands passed` |
| 02 | `test_round4.py` | 0 | `OK (skipped=62)` (6101 tests) |
| 03 | `copy_manifest.py --check` | 0 | `ok: 876 files from 110 fragment(s) (…)` |
| 04 | `tests/test_box_integration.py` | 0 | `OK` (61 tests) |
| 05 | `tests/test_pipeline.py` | 0 | `OK` (90 tests) |
| 06 | `probes4.py --check` | 0 | `probes4: 9 tasks, 18 halves, 169 rows, 1690 cells graded, 0 defects, 0 problems` |
| 07 | `build_draft.py --check` | 0 | `ok: the committed draft is what build_draft.py builds` |
| 08 | `leak_grep.py --check` | 0 | `ok: 25 leak word(s) grepped against 386 real session(s); none would void one; 1 session(s) not grepped (unreadable, named above)` |
| 09 | `holdout.py --check` | 1 | `OWED: holdout.py --check lives in private aegis (ruling C4); … so it did not run and this rehearsal is not all green`. It names itself as not run, as required. |
| 10 | `review_kit/rounds.py --check` | 0 | `ok: 8 registered round(s) graded, every report committed, 0 voided; prompt pinned at 4246efa5b409` |
| 11 | `walk_register.py --check` | 0 | `ok: 387 registered walk(s), each with its folder, none counted` |
| 12 | `mode_binding.py --walks --check` | 0 | `36 of them are input-side only: … never a mode the session recorded.` |
| 13 | `fixture_walk.py --check` | 0 | `ok: 387 committed walk(s) graded, each read through its own harness's reader, … 41 by a recorded per-walk exception, printed above` |
| 14 | `run.py --walks --check` | 0 | `run: 387 walk(s) regraded, every grade.json the regrade's bytes (313 graded, 74 pending documents that grade nothing yet); never counted` |
| 15 | `walk_regrade.py --check` | 0 | `walk_regrade: ok` |
| 16 | `walk_plan.py --coverage --require-run-arms` | 0 | `ok: every required walk of the arms the freeze runs is covered` |
| 17 | `walk_pins.py --check` | 0 | `walk_pins: 387 registered walk(s) read; every one on the draft's version pins and image ids, …` |
| 18 | `freeze.py --check` | 0 | `freeze: 876 fragment-claimed files and 4 native-reader record(s) owned; 8 of 8 legs hold; no takes or freeze performed` |
| 19 | `freeze.unrecorded_shapes_problem(…)`: legs i-iii | 0 | `every leg holds` |

No red is left unexplained. The only non-zero exit is 09, the owed holdout step, which names itself.

## Step 4: the light checks, run from `study/`

Every command exited 0. `git -C study status --short` was empty afterwards. The runs left ignored `__pycache__` folders, all dated after this session began, and I deleted them.

| command | tail |
|---|---|
| `copy_manifest.py --check` | `ok: 876 files from 110 fragment(s) (…) … 22 identical and 29 edited …, 825 new; 5 fixture builders byte-identical; 8 frozen paths unchanged since 68ec902f63bf` |
| `freeze.py --check` | `freeze: 876 fragment-claimed files and 4 native-reader record(s) owned; 8 of 8 legs hold; no takes or freeze performed` |
| `freeze.unrecorded_shapes_problem(…)` | `every leg holds` |
| `build_draft.py --check` | `ok: the committed draft is what build_draft.py builds` |
| `leak_grep.py --check` | `ok: 25 leak word(s) grepped against 386 real session(s); none would void one; 1 session(s) not grepped (unreadable, named above)` |
| `probes4.py --check` | `probes4: 9 tasks, 18 halves, 169 rows, 1690 cells graded, 0 defects, 0 problems` |
| `routing.py --check` | `routing.json: 27 rows, 3 annotations, sound`, then the no-match proof: 21 input classes, each with its pre-registered default |
| `contracts.py --check` | `every stored sentence is a byte substring of the blob it was pinned to` |
| `harness_bookkeeping.py --check` | `harness_bookkeeping: ok: 3 harness(es): claude-code, codex, gemini` |
| `denials.py --check` | `ok, having read 0 graded takes: none is committed yet, so nothing here is evidence about any denial. Not a pass.` |
| `completeness.py --check` | `completeness: no takes; no cells measured` |
| `takes.py --check` | `takes: no takes; no registration or outcome measured` |
| `costs.py --check` | `costs: no takes; no cost measured or written` |
| `stats.py --check` | `stats --check: no takes (0 results files); nothing was compared` |
| `intervals.py --check` | `done-commit binding: 15 of 15 results files equal their blobs` / `gap-study intervals: PASS` (it re-derives the earlier rounds' published intervals and adds nothing to round 4) |
| `result.py --check` | `result: no takes; no table measured or written` |
| `check_results.py --check` | `check_results: no takes; no frozen pins or publication measured` |
| `batch.py --check` | `batch: routing.json ready` |
| `lint_language.py evals/gap-study-4/` | `clean — 232 input(s) scanned, 104 excused line(s) on record` |
| `lint_pooling.py evals/gap-study-4/` | `clean — 228 file(s) and 0 commit(s) scanned, no excusal path` |
| `prereg.py --status` | `This is a DRAFT. No take may run against it and no number may be graded from it. …` (9 tasks; arms A, O, G planned, C optional, G deferred) |
| `review_kit/rounds.py --check` | `ok: 8 registered round(s) graded, every report committed, 0 voided; prompt pinned at 4246efa5b409` |

Every take-side check says it measured nothing. None of them prints a pass over zero items.

## Findings

| # | finding | class | loosens or tightens | would fixing it change a criterion, a reading or a claim? |
|---|---|---|---|---|
| M1 | `check_take.py:70` and `denials.py:32` put `evals/` ahead of the standard library. So one file such as `evals/shlex.py`, added after the freeze, replaces the module the take checker and three graders use to split agent commands, and the regrade uses it too. Nothing pins, scans or names `evals/`: fold 13's later-files guard reads only the study folder, as its docstring admits. Shown in a scratch clone. | MAJOR (lean MAJOR, moderate-to-high confidence: a visible commit, but a single file, the class the study's own probe found, unnamed in the draft, and fixable only before the freeze) | tightens | A claim, and possibly readings: every reading would become the frozen checker's own, rather than whatever an added import supplies. No criterion changes. |
| m-new-1 | The frozen beacon reading is held offline only to its shape. The relay readback and the push witness's refusals reach publication only through the `problems` field the operator commits in `witness-record.json`, and nothing re-derives that field. | MINOR | tightens | A claim: `[4]`'s "never by anything the operator commits" becomes true, or is corrected. No reading. |
| m-new-2 | `ci.yml` is unpinned, and it is the only post-freeze caller of `copy_manifest.py --later-files`. | MINOR | tightens | No reading. It keeps the study-folder shadow guard from being switched off. |
| m2 | `[1]` says "committed unedited" is not enforced, but it is. (carried) | MINOR | tightens | Disclosure only. |
| m-new-3 | The launch binding leaves out `rehearsals/w*/`. (carried) | MINOR | tightens | No reading. It closes a road that needs a coherent regrade. |
| m10 | The walk path gate does not read sub-agent streams (w255, w260). (carried) | MINOR | tightens | It corrects the gate's printed claim for two walks. |
| m1c | An unknown-phase take can be re-run after its end state is seen. It is named in `[13]`. (carried) | MINOR | tightens | It could change a reading in a cell where it happens. No criterion. |
| m7 | The hashed codex template leaves out the per-take trust table. (carried) | MINOR | tightens | It makes the hashed-bytes claim exact. No reading. |
| m1 | Take-path code changed after the take order was public, and the draft does not say it may. (carried) | MINOR | tightens | Disclosure only. |
| m3 | Beacon swaps are unbounded and not printed on RESULT.md. (carried) | MINOR | tightens | Disclosure only. |
| m4 | Two agent-caused driver stops are missing from `[2]`. (carried) | MINOR | tightens | Disclosure only. |
| m5 | Arm A's account state is missing from the vendor-account residual. (carried) | MINOR | tightens | Disclosure only. |
| m6 | The settings hot-reload gap is in code, not in the draft. (carried) | MINOR | tightens | Disclosure only. |
| m8 | Table 6 puts model and agent-system rows under one heading. (carried) | MINOR | tightens | Presentation only, no count. |
| n-new-1 | `frozen_at` is not bounded by the commit times. | NIT | n/a | No |
| n-new-2 | Fold 11-13's edits to files first claimed `new` keep their old fragment reasons. | NIT | n/a | No |
| n-new-3 | Athena file 19's name says legs i-ii, but its command says i-iii. (carried) | NIT | n/a | No |
| n-carried | Review 6's n2 and review 5's n1-n8 and n10, unchanged. | NIT | n/a | No |
