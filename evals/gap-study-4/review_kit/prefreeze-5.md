prereg.json sha256: 37fd08047b66cbaee8cc12cd05a823692e2bafebaaa599d6db53178482b5c0e3

# Pre-freeze review 5 of gap-study-4

**Ruling: DO NOT FREEZE.**

The blocking reason is one MAJOR (M1). No check binds a committed review report to the bytes its reviewer wrote. The freeze is seeded from that report's ruling line. The record shows this gap has already been used once: review 4's report was edited by hand before commit, its true sha256 is kept outside the repository, and the commit message the tool generated says "committed unedited". The edit was benign and the copy record discloses it. But a single edit to one file could turn this report's ruling into the other one, and the draft does not name that road.

Everything else is either green or carried. `prereg.json` is byte-identical to `study/evals/gap-study-4/prereg-draft.json`; `diff` printed nothing. It is also byte-identical to `prereg-as-the-previous-review-read-it.json` (same sha256, and `cmp` reports no difference), so the step-2 diff is empty and the draft has not changed since review 4. What changed is code and records: 10 commits from `c2cb345e` (review 4's commit) to `COMMIT` = `c781e26107496c1ac1dbe21e4583e782223d307b`. `git status --short` in `study/` prints nothing, and I changed nothing in it.

## Threat model, restated

The operator holds the machines, the review kit, the commit tooling and every unpushed commit. Before the freeze they choose the seed review and the beacon round. After the takes exist they may want to edit, re-date, re-run, re-route or misfile any single record or attempt, or change code or pins. The checks bind them only through what is committed here, what GitHub's push records witness, and what re-derives at HEAD. The agent, during a take, may do anything its uid allows inside the container: use its one vendor host with the credential it holds, write its run tree and config mount, and start children. It must not reach the study's files, graders or evidence, or make an untaken step look taken.

I make one correction beyond review 4's two (the pre-freeze choice of review and round, and the outcome-informed go for deferred arm G, which stand). **The review report is an operator-carried record, and it is in scope.** The reviewer writes it into a folder the operator controls. The operator's tool copies it into the repository, and the freeze reads its ruling. Choosing among reviews is in scope, and so is editing one. A single edit to the report is a single-record road, not a coherent fabrication. Binding the report to a reviewer-side digest would turn it into a two-record edit, which is then a limitation to name.

**Does the draft say this honestly?** Mostly yes:
- `limitations`, `box_residuals`, `round_4_limitations`, `not_poolable` and `predictions_rule` say what the checks bind on the take side;
- every prediction is null under the "no informed basis" rule;
- the out-of-scope trust in the machines and the runner is named.

There are three gaps:
- the report-integrity road (M1);
- the carried disclosure gaps m3 to m6;
- take-path code changing after the beacon round was public (m11, below).

## MAJOR findings

### M1. A committed review report is not bound to what its reviewer wrote

**Where.**
- `study/evals/gap-study-4/review_kit/commit_review.py:40-49` checks only three things about a report: its line 1, an absolute-path regex (`ABS_PATH`, line 37) and a person regex. It then copies the file from the review folder as found (`:80`) and writes the commit message "The report and its blindness record are committed unedited" (`:89`) without checking that claim.
- `study/evals/gap-study-4/freeze.py:1092-1162` (`review_file_problems`, `registered_review_problem`) reads the ruling from the committed report. It binds the report to its registered round only through the session id named in the blindness record.
- The blindness record (`review_kit/blindness.py`) carries no digest of the report as the reviewer's session wrote it:

```
$ grep -n "sha256\|hashlib" review_kit/blindness.py
55:import hashlib
104:# launch.py's per-file record of the folder at launch ...
528:    """rounds.py's input_sha256, computed from the manifest's own lines ...
```

Every hash in that file is of the input folder. None is of the report.

**It has already happened.** `COPIED.d/freeze-review-r4.json` records it:

> "committed by c2cb345e as its reviewer wrote it from the kit except for five lines the Lane-orchestrator masked before commit ... The report as written has sha256 27f6afb8ae52e91bb5256ad508135b50d16a259322ccf902fcbce44fb47be9d8, and its bytes are kept outside this repository by the orchestrator."

```
$ shasum -a 256 study/evals/gap-study-4/review_kit/prefreeze-4.md
27fdd7252ec4c7e959609c553e57421dc8107af7c93c52e85ec3469c4f81df8c
$ git -C study show c2cb345e --format=%B | sed -n 3p
One fresh reviewer, ... ruled: DO FREEZE. The report and its blindness record are committed unedited.
$ grep -c "\[/\]" study/evals/gap-study-4/review_kit/prefreeze-4.md
5
```

Three things follow:
- The commit's sentence is false.
- The as-written digest cannot be checked from the repository.
- `lint_pooling.py`'s `BOUND_REVIEW_RECORDS` binds review 4 to the *masked* bytes (`27fdd725…`). So the "bound record" is bound to the operator's version.

**Why it is in scope and material.** Under the corrected threat model, one edit to `prefreeze-5.md`'s ruling line in the review folder, before `commit_review.py` runs, passes every check that exists:
- line 1 still holds;
- the blindness record still names the registered session id;
- `read_ruling` reads exactly one canonical line;
- the freeze then seeds.

The draft's own text on this step (`round_4_limitations[10]`, "review shopping and the ruling line") names the unregistered-review road. It ends "this cannot produce a freeze the review did not rule for", which a reader will take as covering the report's integrity. It does not cover it. What the study may claim is that a blind review ruled for these bytes. Today that rests on the operator's word alone, and the draft does not say so.

**Why it must be fixed before the freeze.** The freeze consumes this very report and is irreversible. A fix after the freeze cannot reach the seed.

**A cheap fix, verifiable by a command.**
1. `blindness.py` records the sha256 of the report's last state as the reviewer's own session wrote it. That state can be rebuilt from the Write and Edit tool inputs in the session file it already reads.
2. `commit_review.py` refuses unless the folder's report has that digest. A needed mask is not done by hand. It is committed as a separate, listed diff on top of the as-written bytes, and those bytes are committed too, or at least their digest is.
3. `registered_review_problem` refuses a seed whose report is neither the recorded digest nor that digest plus the listed mask.
4. Also, or at least, name the residual in `round_4_limitations[10]`.

The root cause of review 4's mask is also cheap to remove. `ABS_PATH` matches placeholders such as a slash-home-slash-angle-bracket string. The kit could tell reviewers to avoid them, or the regex could exempt placeholder forms.

**Lean.** MAJOR. It is a single-record road to the one label that starts the irreversible step, it has been exercised, and the fix is a few lines. If the owner judges the review record to sit wholly inside the operator trust that the draft already names, the minimum fix is still a sentence in `round_4_limitations[10]` and a corrected commit-message template. That is a draft change, and so a new review either way.

## Other findings

### MINOR

**m11 (new; review 4's n9, now on the take path). Take-path code changed after the take order was public.**

Beacon round 33536472 published at 2026-10-31T02:13:00Z (genesis 1692803367 plus 3 s per round). `996ce358` (2026-10-31T12:40:30Z) changed `box/ownership.py:67`, the restore walk that runs after every take's teardown. `4d83d5b1` (13:20:50Z) changed `order_beacon.py:456`. The push witness binds only the registering commit and the last draft-changing commit (`take_order_beacon.seed_rule`). The draft does not say that other code, the take path included, may change while the order is computable.

Both edits are benign:
- the restore now lchowns a Unix socket in place, never following it, with no change to the grant;
- `_open` now sends a User-Agent;
- `freeze.py --check` prints "take-order function: ok".

The freeze's pins and this review bind the result. A uniform code change cannot target order positions without showing in the diff, so I class this MINOR. Fix: one sentence in `take_order_beacon.residual`. That tightens disclosure and changes no criterion, reading or claim.

**Carried, unchanged at `COMMIT`.** The draft is byte-unchanged, and `git -C study log -1 -- fixture_walk.py batch.py stats.py result.py` gives `985ac307`, which predates review 4's commit. So each of these still stands as review 4 read it:

- **m10.** `fixture_walk.py` reads only `transcript.jsonl` for a claude-code walk. The sub-agent streams of w255 and w260 (`rehearsals/w255/subagents/`, `rehearsals/w260/subagents/`, still present) go unread and uncounted.
- **m1.** An unknown-phase take that stopped can be re-run after its end state is seen. The early return is still at `batch.py:512`.
- **m3.** Beacon swaps are unbounded and not printed in RESULT.md.
- **m4.** Two agent-caused driver stops are missing from the agent-caused-routes limitation.
- **m5.** Arm A's account state is missing from the account-state residual.
- **m6.** The settings hot-reload gap is named in `box/settings_guard.py` but not in the draft.
- **m7.** The hashed codex `config.toml` template leaves out the per-take trust table that `box/take_config.py` appends.
- **m8.** Table 6 (`stats.py`, `render_across`) puts within-harness model rows and cross-harness agent-system rows under one heading. The families stay separate (`check_families`), so this is presentation only.

### NIT

- **n11 (new).** `box/ownership.py` lines 16-18 and 45-46 still say a socket refuses. The restore branch at line 67 now chowns one.
- **n12 (new).** The copy record does not name every fold4 edit:
  - `language-allowlist.json` (status edited, owned by `w1a-cp1-scaffold`) gained five review-4 excusals, which neither its own reason nor the fold4 text in `fold3-m1.json` names;
  - the child-timeout raises in `tests/test_build_draft.py`, `tests/test_holdout_digests.py` and `tests/test_walk_layout.py` (180 s to 3600 s, 110 s to 3000 s, 110 s to 900 s) are not named either. These files are status new, so this is a wording gap only.

  `freeze-review-r4.json` says it "changes no byte of any" file, and that is true of the fragment itself.
- **n1-n8, n10 (carried).** They cover:
  - "re-tested at its first real walk";
  - legs i and ii not reading the register;
  - "in none of the three views";
  - the self-attested recheck machine;
  - stale docs;
  - lints that scan files, not rendered pages;
  - arm A's config mount not being censused;
  - codex native rollout files not read by the path gate;
  - the `lint_pooling.py` exemption list. That list now holds review 4 as well, and it will grow by one file per review.

### Read and found sound

- **Copy record (step 6).** `copy_manifest.py --check` gives 850 files from 103 fragments: 22 identical, 29 edited, 799 new, 1 acceptance-records. I compared all 22 "identical" entries byte for byte with their named sources, and 0 differ. Every code edit in `git diff c2cb345e HEAD` is named by the fold4 text in `COPIED.d/fold3-m1.json`, except the n12 items.
- **System under test.** `variants.PINNED_TREE` is `844a4ce0d894…`. `git rev-parse 844a4ce0…:gars` gives `8a54e0f8cd91…`, which equals `check_take.GARS_TREE_SHA` (`check_take.py:2027`).
- **The freeze pins the take path.** `freeze.PINNED` holds 853 paths, `box/ownership.py`, `box/run_take.py`, `box/take_config.py`, the egress and sidecar files and `order_beacon.py` among them. The freeze also requires HEAD's study tree to equal the rehearsed one (`REHEARSAL_TREE_PREFIX`).
- **Container (step 7).** The egress template allows one CONNECT host on port 443 per take's harness (`box/egress/proxy.conf:5-10`, `proxy_conf.HOSTS`, with `-n` so reverse lookups are off). The credentials per harness are a subscription token in the environment (claude-code), `GEMINI_API_KEY` in the environment (gemini), and an `auth.json` lease in the config mount (codex). Those are what `run_take.py:160-176` and `:360-376` set up, and the draft's `box_residuals` names each one and its reach. No box file but `ownership.py` changed since review 4. Its change runs only after teardown, and `restore` refuses while any take container is present, so the agent cannot use it.
- **Vendor arms, outcome and publication (steps 8-11).** None of the adapters, config templates, image locks, price table, routing markers, `routing.json`, graders, `stats.py`, `result.py` or `check_results.py` changed since review 4, and the draft that hashes them is byte-unchanged. `freeze.py --check` re-verifies the pins and legs i-iii. `probes4.py --check` grades 1690 cells with 0 defects. Every take-side gate says plainly that it measured nothing and prints no pass.
- **Walks (step 10).** 387 walks are registered, none counted. Every gate in step 3 re-derives them at `COMMIT`, apart from the m10 gap.

## Step 3: the athena files

Every file names commit `c781e26107496c1ac1dbe21e4583e782223d307b`, which equals `COMMIT`. Together they cover:
- `run_checks.py` (01), which includes the battery and every lane's checks;
- each entry of `freeze_rehearsal.COMMANDS`, run directly: `test_round4.py`, `copy_manifest.py --check`, `tests/test_box_integration.py`, `tests/test_pipeline.py`, `probes4.py --check`, `build_draft.py --check`, `leak_grep.py --check`, `holdout.py --check`, `review_kit/rounds.py --check`, the five `WALK_COMMANDS`, and the two `WALK_PIN_COMMANDS` (02-17);
- `freeze.py --check` (18);
- the three legs (19).

| file | commit | last line |
|---|---|---|
| 01-run-checks-py-its-lines-24-at-a-time-by-the-remote-suite-s-b.txt | c781e261 | `run_checks: 530 of 530 commands passed` |
| 02-test-round4-py.txt | c781e261 | `OK (skipped=62)` (5921 tests) |
| 03-copy-manifest-py-check.txt | c781e261 | `ok: 850 files from 103 fragment(s) (…) … 8 frozen paths unchanged since 68ec902f63bf` |
| 04-tests-test-box-integration-py.txt | c781e261 | `OK` (61 tests) |
| 05-tests-test-pipeline-py.txt | c781e261 | `OK` (88 tests) |
| 06-probes4-py-check.txt | c781e261 | `probes4: 9 tasks, 18 halves, 169 rows, 1690 cells graded, 0 defects, 0 problems` |
| 07-build-draft-py-check.txt | c781e261 | `ok: the committed draft is what build_draft.py builds` |
| 08-leak-grep-py-check.txt | c781e261 | `ok: 25 leak word(s) grepped against 386 real session(s); none would void one; 1 session(s) not grepped (unreadable, named above)` |
| 09-holdout-py-check.txt | c781e261 | `OWED: holdout.py --check lives in private aegis (ruling C4); … so it did not run and this rehearsal is not all green` (exit 1: it names itself as not run, never a pass) |
| 10-review-kit-rounds-py-check.txt | c781e261 | `ok: 4 registered round(s) graded, every report committed, 0 voided; prompt pinned at 4246efa5b409` |
| 11-walk-register-py-check.txt | c781e261 | `ok: 387 registered walk(s), each with its folder, none counted` |
| 12-mode-binding-py-walks-check.txt | c781e261 | `36 of them are input-side only: their CLI writes no mode record, so the launch argv is what was checked, never a mode the session recorded.` |
| 13-fixture-walk-py-check.txt | c781e261 | `ok: 387 committed walk(s) graded, each read through its own harness's reader, none names this checkout and every path each named is placed; 41 by a recorded per-walk exception, printed above` (see m10) |
| 14-run-py-walks-check.txt | c781e261 | `run: 387 walk(s) regraded, every grade.json the regrade's bytes (313 graded, 74 pending documents that grade nothing yet); never counted` |
| 15-walk-regrade-py-check.txt | c781e261 | `walk_regrade: ok` |
| 16-walk-plan-py-coverage-require-run-arms.txt | c781e261 | `ok: every required walk of the arms the freeze runs is covered` |
| 17-walk-pins-py-check.txt | c781e261 | `walk_pins: 387 registered walk(s) read; every one on the draft's version pins and image ids, … (a walk records the pin, so this compares the pin with itself: …)` |
| 18-freeze-py-check.txt | c781e261 | `freeze: 850 fragment-claimed files and 4 native-reader record(s) owned; 8 of 8 legs hold; no takes or freeze performed` |
| 19-freeze-unrecorded-shapes-problem-prereg-draft-json-legs-i-ii.txt | c781e261 | `every leg holds` |

The only red is 09, and it names itself as owed and not run. File 01 holds only the last 200 lines of its output, so I read its count line rather than all 530 commands.

## Step 4: the light checks, run from `study/`

Every command exited 0.

| command | tail of output |
|---|---|
| `python3 evals/gap-study-4/copy_manifest.py --check` | `ok: 850 files from 103 fragment(s) (…)` |
| `python3 evals/gap-study-4/freeze.py --check` | `… walk coverage …: ok` / `take-order function: ok` / `prepare (dummy review, synthetic beacon reading): ok` / `freeze: 850 fragment-claimed files and 4 native-reader record(s) owned; 8 of 8 legs hold; no takes or freeze performed` |
| `(cd evals/gap-study-4 && python3 -c "… freeze.unrecorded_shapes_problem …")` | `every leg holds` |
| `build_draft.py --check` | `ok: the committed draft is what build_draft.py builds` |
| `leak_grep.py --check` | `ok: 25 leak word(s) grepped against 386 real session(s); none would void one; 1 session(s) not grepped (unreadable, named above)` |
| `probes4.py --check` | `probes4: 9 tasks, 18 halves, 169 rows, 1690 cells graded, 0 defects, 0 problems` |
| `routing.py --check` | `before-first-turn, last turn none (no turn ran) -> route rehearsal` |
| `contracts.py --check` | `every stored sentence is a byte substring of the blob it was pinned to` |
| `harness_bookkeeping.py --check` | `harness_bookkeeping: ok: 3 harness(es): claude-code, codex, gemini` |
| `denials.py --check` | `ok, having read 0 graded takes: none is committed yet, so nothing here is evidence about any denial. Not a pass.` |
| `completeness.py --check` | `completeness: no takes; no cells measured` |
| `takes.py --check` | `takes: no takes; no registration or outcome measured` |
| `costs.py --check` | `costs: no takes; no cost measured or written` |
| `stats.py --check` | `stats --check: no takes (0 results files); nothing was compared` |
| `intervals.py --check` | `gap-study intervals: PASS` |
| `result.py --check` | `result: no takes; no table measured or written` |
| `check_results.py --check` | `check_results: no takes; no frozen pins or publication measured` |
| `batch.py --check` | `batch: routing.json ready` |
| `python3 evals/gap-study-4/lint_language.py evals/gap-study-4/` | `clean — 219 input(s) scanned, 89 excused line(s) on record` |
| `python3 evals/gap-study-4/lint_pooling.py evals/gap-study-4/` | `not scanned: …prefreeze-3.md …` / `not scanned: …prefreeze-4.md …` / `clean — 217 file(s) and 0 commit(s) scanned, no excusal path` |
| `python3 evals/gap-study-4/prereg.py --status` | `This is a DRAFT. No take may run against it and no number may be graded from it. The walks are what turn it into the frozen file.` |
| `python3 evals/gap-study-4/review_kit/rounds.py --check` | `ok: 4 registered round(s) graded, every report committed, 0 voided; prompt pinned at 4246efa5b409` |

`rounds.json` holds rows 1-4 at `COMMIT`, and this review's row is not in it. That matches review 4's case: its row was committed after its launch commit.

## Findings

| # | finding | class | loosens or tightens | would fixing it change a criterion, a reading or a claim? |
|---|---|---|---|---|
| M1 | No check binds a committed review report to the bytes its reviewer wrote. The freeze seeds from that report's ruling, review 4's report was hand-edited before commit with its true digest kept off-repo, and the auto-written commit message says unedited. | MAJOR (I lean MAJOR: a single-record road to the label that starts the irreversible step, already exercised, cheap to close) | tightens | Yes, a claim: that the freeze followed a blind review's own ruling becomes checkable rather than taken on the operator's word. No criterion or reading. |
| m11 | Take-path code (`box/ownership.py`) and `order_beacon.py` changed after the beacon round was public. The draft's residual does not say other code may change then. | MINOR | tightens | Disclosure only; no criterion or reading |
| m10 | The walk path gate does not read Claude sub-agent streams (w255, w260) (carried) | MINOR | tightens | Corrects the gate's printed claim for two walks; no criterion or reading |
| m1 | An unknown-phase take that stopped can be re-run after its end state is seen, and the discarded reading is not published (carried) | MINOR | tightens | No criterion; could change a reading in a cell where it happens |
| m3 | Beacon swaps are unbounded and not printed in RESULT.md (carried) | MINOR | tightens | Disclosure of the order's provenance only |
| m4 | Two agent-caused driver stops are missing from the agent-caused-routes limitation (carried) | MINOR | tightens | Disclosure only |
| m5 | Arm A's account state is missing from the account-state residual (carried) | MINOR | tightens | Disclosure only |
| m6 | The hot-reload gap is in code, not in the draft (carried) | MINOR | tightens | Disclosure only |
| m7 | The hashed codex template leaves out the per-take trust table (carried) | MINOR | tightens | Makes the hashed-bytes claim exact; no reading |
| m8 | Table 6 puts the model and agent-system kinds under one heading (carried) | MINOR | tightens | Presentation only, no count |
| n11 | The `ownership.py` docstring and comment still say a socket refuses | NIT | n/a | No |
| n12 | The copy record does not name the review-4 language excusals or the three test child-timeout raises | NIT | n/a | No |
| n1 | "re-tested at its first real walk" overstates what the freeze runs (carried) | NIT | n/a | Wording only |
| n2 | Vendor legs i and ii do not read the walk register (carried) | NIT | n/a | No |
| n3 | "in none of the three views" is wrong for the failures view (carried) | NIT | n/a | Wording only |
| n4 | The recheck machine is self-attested (carried; named) | NIT | n/a | No |
| n5 | Stale docs (carried) | NIT | n/a | No |
| n6 | The lints do not scan rendered result pages (carried) | NIT | n/a | No |
| n7 | Arm A's config mount is not censused (carried) | NIT | n/a | No |
| n8 | Codex native rollout files are not read by the path gate (carried; stated in code) | NIT | n/a | No |
| n10 | `lint_pooling.py` exempts bound review records by sha256, now two, growing by one per review (carried) | NIT | n/a | No |

The table holds one MAJOR, M1, so the ruling is DO NOT FREEZE. Apart from M1, nothing I found blocks a freeze. With M1 closed, either by the digest binding or at minimum by naming the residual in the draft and correcting the commit-message template, I would expect the remaining rows to permit DO FREEZE.
