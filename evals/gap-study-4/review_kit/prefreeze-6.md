prereg.json sha256: 37fd08047b66cbaee8cc12cd05a823692e2bafebaaa599d6db53178482b5c0e3

# Pre-freeze review 6 of gap-study-4

**Ruling: DO NOT FREEZE.**

Two MAJOR findings block the freeze. Both concern the step that joins a blind review to the freeze. Neither concerns how a take is run or graded.

- **M1.** Freeze code says rounds 1 to 4 can no longer seed a freeze. The draft says a registered review cannot be dropped. Neither holds. Review 4 read these exact bytes and approved them, and its report was masked before commit. In a scratch clone, one commit made review 4 the seed: it deleted review 5's report and blindness record and set `spent_without_work` by hand on row 5.
- **M2.** The freeze checks that the seed review read the same `prereg.json`. It never checks that the code being frozen is the code that review read. Since review 4's launch commit, take-path and freeze code have changed with the draft byte-unchanged. A verdict on one commit can freeze another commit's code.

Both fixes are a few lines in `freeze.py`, each checkable by a command. Neither needs a change to the draft.

Everything else is green, or is a carried MINOR or NIT:

- `prereg.json` is byte-identical to `study/evals/gap-study-4/prereg-draft.json`: `diff` printed nothing.
- It is also byte-identical to `prereg-as-the-previous-review-read-it.json`. `cmp` is silent and the step-2 diff is empty.
- What changed since review 5 (`c781e261`) is code and records only:
  - `c781e261..COMMIT` is 347 files: 314 walk-recheck files and the register, and 33 others;
  - the lanes are fold5/report-binding, fold6/kill-leftovers and fold7/battery-reds, plus recheck wave 3.
- `git -C study status --short` printed nothing after my checks. I changed nothing under `study/`.

## Threat model, restated and corrected

The operator controls the machines, the review kit, the commit tools and every commit until it is pushed. After the takes exist, the operator may want to edit, re-date, re-run, re-route or misfile one record or attempt, or change code or pins. Only what is committed, what GitHub's push records witness, and what re-derives at HEAD binds them.

The agent, during a take, may do anything its uid allows in the container:
- use its one vendor host with the credential it holds;
- write its run tree and its config mount;
- start children.

It must not reach the study's files, its graders or the evidence they read, and it must not make a step it did not take look taken.

**Correction.** The brief puts the operator's interest only "after the takes exist". That is too narrow, for two reasons:

- The take order is already computable. Its drand round, 33536472, was published on 2026-10-31.
- The step from a blind verdict to the irreversible freeze is a choice the operator makes now. That covers which review seeds it and which commit is frozen.

A choice among reviews or commits at that step is in scope, as reviews 4 and 5 already said. A deletion or a field flip in committed files is not "a complete, coherent set of fabricated records". It is a single-commit road, so it is a defect, not a limitation.

**Does the draft say honestly what is bound?** Mostly:

- On the take side, `limitations`, `box_residuals`, `round_4_limitations`, `not_poolable` and `predictions_rule` name what the checks bind and what they cannot. That covers the coherent fabricated record set, the trusted machines, what a vendor serves, the arm O and arm G model checks, arm A's empty thinking blocks, and the recheck machine.
- Every prediction is null under "no informed basis", and the 387 walks are named as read and not used.
- `not_poolable` names all three earlier rounds and its two enforcers.

On the review-to-freeze step, the draft claims more than the code binds:

- `round_4_limitations[10]` says "a registered review cannot be dropped" (M1).
- `round_4_limitations[12]` ends "bound by the same review as the code it restates", but nothing binds frozen code to reviewed code (M2).
- `round_4_limitations[1]` is now stale in the other direction (m2).

## MAJOR findings

### M1. A later review can be dropped from HEAD, and then grandfathered review 4 seeds the freeze

**Where.**

- `study/evals/gap-study-4/freeze.py:1106-1111` (`review_file_problems`) takes "the latest review" from the `prefreeze-N.md` files in the tree at HEAD, not from the register or the history.
- `freeze.py:1139` refuses a voided or spent row only for the seed's own row.
- `freeze.py:1166` returns early for `REPORT_DIGEST_GRANDFATHERED = (1, 2, 3, 4)` (`:1185`), so a round-1-to-4 seed needs no report digest. Yet the comment at `:1182` says: "None of them can seed a freeze now: freeze seeds only from the latest review."
- `study/evals/gap-study-4/review_kit/rounds.py:267` skips any row that carries `spent_without_work` or `voided_by`. The rule that a row with a committed report is never closed as spent is enforced only by the `--close-spent` command (`:354`). It is not enforced by `--check`, which reads the register as it is at HEAD.
- The draft's `round_4_limitations[10]` says: "rounds.py --check refuses while any registered round's report is not committed, so a registered review cannot be dropped."

**What makes it live.** Review 4's report (`c2cb345e`) has line 1 `prereg.json sha256: 37fd0804…`, today's draft. Its verdict line is the canonical approving one, at line 5 of that file. Its committed bytes are the masked ones, which no digest binds.

**Shown in a scratch clone of `study/`** (deleted afterwards):

```
$ python3 -c "import freeze; print(freeze.review_file_problems('c2cb345e'))"
(['evals/gap-study-4/review_kit/prefreeze-4.md is not the latest review committed (prefreeze-5.md is): the freeze seeds from the last ruling, not a chosen one'], None)

$ git rm -q review_kit/prefreeze-5.md review_kit/prefreeze-5-blindness.txt
$ # rounds.json: rows[4]["spent_without_work"] = "x", by hand
$ git commit -qam drop
$ python3 -c "import freeze; print(freeze.review_file_problems('c2cb345e'))"
([], 'evals/gap-study-4/review_kit/prefreeze-4.md')
$ python3 review_kit/rounds.py --check | tail -1
ok: 4 registered round(s) graded, every report committed, 0 voided; prompt pinned at 4246efa5b409
$ python3 copy_manifest.py --check | tail -2
FAIL review_kit/prefreeze-5.md (fold5-report-binding) is claimed but does not exist
FAIL review_kit/prefreeze-5-blindness.txt (fold5-report-binding) is claimed but does not exist
```

The copy record's red goes away by dropping the two claims from `COPIED.d/fold5-report-binding.json` in the same commit. `grep -rn prefreeze-5 --include=*.py` finds only the Mac-only `review_kit/check_real_sessions.py`, which is not in the battery. So one commit of four files is the whole road:

1. delete review 5's report;
2. delete review 5's blindness record;
3. flip one field in `rounds.json`;
4. drop two claims from one fragment.

Review 6 is dropped the same way. A rehearsal of that tree is then green, and `freeze.py --review-commit c2cb345e` seeds. The superseded verdicts stay in git history. But nothing in the freeze or the frozen file refuses or reports them, and a seed chosen this way is the "chosen one" the code's own message says the freeze prevents.

**Why it must be fixed before the freeze.** The freeze is irreversible, and this is the step that starts it.

**A cheap fix, verifiable by a command.** Do any one of these:

- (a) Make `registered_review_problem` refuse every round in `REPORT_DIGEST_GRANDFATHERED` as a seed. That is what `freeze.py:1182` already claims.
- (b) Take "latest" as the highest `n` of any prefreeze row in `rounds.json`, spent or voided rows included. Refuse a row marked spent or voided whose report was ever committed (`git log --all -- <report>`).
- (c) Refuse when any `prefreeze-M.md` with M greater than the seed's number was ever committed.

Then `round_4_limitations[10]`'s sentence becomes true. The test is to repeat the clone steps above and see `review_file_problems` refuse.

**Lean.** MAJOR. It is a one-commit road to the step that starts the irreversible freeze. It contradicts a sentence in the draft and a comment in the freeze code. The fix is cheap and tightens. If the owner holds that deleting committed reviews is on the operator's word anyway, the minimum is still to correct `[10]` and `freeze.py:1182`, which is a draft change.

### M2. The frozen code is not bound to the code the seed review read

**Where.**

- `freeze.py:1071-1115` binds the seed review to the frozen draft only through the report's line 1, the draft's sha256.
- `prepare` (`:256-277`) records `pre_freeze_review_commit` and `frozen_at_commit_parent`. It compares neither with the round's `launch_commit` in `review_kit/rounds.json`, the commit the reviewer was handed.
- The freeze pins 861 paths, as `len(freeze.PINNED)` prints; `freeze.py --check` prints 864 with patterns expanded. They are pinned as they stand at HEAD, and the rehearsal must be of HEAD's tree. Neither has to equal the reviewed commit.

```
$ grep -n "launch_commit" study/evals/gap-study-4/freeze.py
$                                   # (nothing)
$ git -C study diff --stat 4163754f HEAD -- evals/gap-study-4 ':!…rehearsals' ':!…tests' ':!…review_kit' ':!…COPIED.d' ':!…native-readers' ':!…language-allowlist.json'
 evals/gap-study-4/box/ownership.py |  12 ++++----
 evals/gap-study-4/box/preflight.py |  59 ++++++++++++++++++++++++++++++++++----
 evals/gap-study-4/drive.py         |   2 +-
 evals/gap-study-4/freeze.py        |  34 +++++++++++++++++++++-
 evals/gap-study-4/lint_pooling.py  |   9 +++++-
 evals/gap-study-4/order_beacon.py  |   2 +-
```

`4163754f` is review 4's launch commit. Every file listed except `lint_pooling.py` is in `freeze.PINNED`. Today the draft is byte-identical to what reviews 4, 5 and 6 read. So the binding the freeze checks is one these code changes cannot touch. Any later commit can be frozen under any approving review of these bytes, including:

- review 4's, through M1;
- this one's, if it approved, with code changed after it.

The draft relies on the review for code. `round_4_limitations[12]` ends: "The recompute restates the seed rule and the permutation, so it is bound by the same review as the code it restates."

**Why it is material.** The study's claim is that a blind pre-freeze review read the instrument that ran. Today that holds only for `prereg.json`. The graders, the routing code, `check_take.py`, the box and the publication code can change between the verdict and the freeze, and no check goes red. The take order has been computable since 2026-10-31, so a change in that window can be aimed at known positions.

The record shows the window is used. After review 5's commit, `box/preflight.py` and `drive.py` changed on 2026-11-01, on the take path, with the draft unchanged. That was benign, and this review reads it (see m1). But nothing would have stopped a freeze at that commit had review 5 approved.

**A cheap fix, verifiable by a command.** In the real freeze, refuse unless every path in `freeze.PINNED` has at HEAD the bytes it had at the seed round's `launch_commit`:

```
git diff --quiet <launch_commit> HEAD -- <pinned paths>
```

Only the round's own report, its blindness record and `rounds.json` may differ. The check should print the first differing path. A code change after a review then needs a new round, which is this project's practice already. This closes most of M1 too, since review 4's launch commit no longer matches.

**Lean.** MAJOR, with less certainty than M1. Against it: the brief names `prereg.json` as "the bytes under review", and the operator's workflow has re-reviewed after every fold. For it: that is a convention, not a check. The draft's own text treats the review as binding code. And this is the one step the brief asks a guard for: "a change to code … that moves … a published sentence", the sentence being that a blind review approved what ran. If the owner judges code between review and freeze to be on the operator's word, the minimum is a named limitation and `[12]`'s sentence corrected.

## Other findings

### MINOR

- **m1 (review 5's m11, extended).** Take-path code changed after the take order became public, and the draft does not say it may.
  - Round 33536472 was published on 2026-10-31.
  - `8c95a4fb` (2026-11-01) changed `box/preflight.py` `postflight` and `drive.py:2438`. A killed claude-code take's `sessions/N.json` and `N.<64 hex>.key` pair is now admitted when it names the take's own session and socket, where before it stopped the take.
  - The change is uniform, producer-bound and tested (`tests/test_fold6_kill_leftovers.py`), and it is pinned at the freeze. So it cannot target positions without showing in the diff.
  - Fix: one sentence in `take_order_beacon.residual`. That tightens disclosure.
- **m2 (new).** `round_4_limitations[1]` ("seed review line 1") still says "'committed unedited' is not enforced".
  - Since fold5 it is enforced from round 5 on: `review_kit/commit_review.py` and `freeze.py:1166-1176` check the report against the digest `review_kit/blindness.py` rebuilds from the reviewer's session.
  - The draft understates that binding. It also does not name the road that remains: editing the session file and the report together, or both committed files, which is a two-record edit.
  - Fix: reword `[1]`. That is disclosure only.
- **Carried from review 5, unchanged at `COMMIT`.** The draft is byte-identical, and `git log -1` over `batch.py`, `fixture_walk.py`, `stats.py`, `result.py`, `box/settings_guard.py`, `box/take_config.py`, `check_results.py`, `routing.json` and `graders/` gives `985ac307`, which predates review 5. I re-checked m1 and m10 directly and carry the rest on that evidence:
  - **m10.** `fixture_walk.py` does not read the claude-code sub-agent streams. `rehearsals/w255/subagents/` and `rehearsals/w260/subagents/` are present.
  - **m1.** An unknown-phase take that stopped can be re-run after its end state is seen. The early return is still at `batch.py:512`.
  - **m3.** Beacon swaps are unbounded and not printed in RESULT.md.
  - **m4.** Two agent-caused driver stops are missing from `round_4_limitations[2]`.
  - **m5.** Arm A's account state is missing from the vendor-account residual.
  - **m6.** The settings hot-reload gap is in `box/settings_guard.py` but not in the draft.
  - **m7.** The hashed codex `config.toml` template leaves out the per-take trust table `box/take_config.py` appends.
  - **m8.** Table 6 puts the within-harness model rows and the cross-harness agent-system rows under one heading. The families stay apart in the statistics (`check_families`), so this is presentation only.

### NIT

- **n1 (new).** fold7's edits to `language-allowlist.json` (`6572968b`, `31544596`) and `tests/test_run_take.py` (`d77da30d`, `31544596`) are not named in any copy fragment's reason. Only `COPIED.d/pf1-l6c.json` names fold7. This is review 5's n12 again.
- **n2 (new).** The postflight admission of the session pair (m1) is in no `box_residuals` entry. The key is never read, the config folder is removed after the commit, and nothing from `sessions/` is committed.
- **Resolved.** Review 5's n11 is fixed: the `box/ownership.py` docstring now says a socket is chowned on a restore.
- **Carried, unchanged.** Review 5's n1 to n8 and n10. That review lists them, and the files and the draft they name are unchanged. The `lint_pooling.py` exemption list now holds three bound review records.

### Read and found sound

- **Copy record (step 6).**
  - `copy_manifest.py --check` reports 858 files from 105 fragments: 22 identical, 29 edited, 807 new, and the native-readers pattern.
  - I compared all 22 "identical" files byte for byte with their named sources: 0 differ.
  - The fold5 and fold6 fragments name their code edits: `blindness.py`, `commit_review.py`, `freeze.py`, `lint_pooling.py`, `box/preflight.py` and `drive.py`. The exceptions are n1.
- **System under test.** `variants.PINNED_TREE` is `844a4ce0…`, and `git rev-parse 844a4ce0…:gars` gives `8a54e0f8cd91…`, equal to `check_take.GARS_TREE_SHA` (`check_take.py:2027`). Takes read their gars tree at export (`run_builders.exported_gars_tree`).
- **Container (step 7).**
  - The egress template (`box/egress/proxy.conf`) allows a CONNECT to one host on 443, with `-n`. `proxy_conf.HOSTS` gives that host per harness: `api.anthropic.com`, `chatgpt.com` and `generativelanguage.googleapis.com`.
  - The credentials (`box/run_take.py:163-174`, `TAKE_ENV`):
    - claude-code: `CLAUDE_CODE_OAUTH_TOKEN` in the environment;
    - gemini: `GEMINI_API_KEY` in the environment;
    - codex: an `auth.json` lease in the config mount at `/opt/cfg`.
  - Each is named, with its reach, in `box_residuals`. The read-only root and the two bind mounts are named in `box_residuals[4]`.
  - The only box changes since review 5 are `ownership.py`'s comment and the postflight admission (m1). Both run after teardown, outside the agent's reach.
- **Vendor arms, outcome, publication (steps 8 to 11).**
  - `git diff --stat c2cb345e..HEAD` (review 4's commit to now), outside rehearsals, tests, review_kit and COPIED.d, touches only the six files under M2, `language-allowlist.json` and the two native-reader acceptances and their reviews.
  - The two acceptances were re-accepted on new `reader_sources_sha256` values after the one-line `drive.py` change. `freeze.py --check` and the three-leg check say every leg holds.
  - No adapter, config template, image lock, price table, routing marker, `routing.json`, grader, `stats.py`, `result.py` or `check_results.py` changed.
  - `probes4.py --check` grades 1690 cells with 0 defects.
  - Every take-side gate says it measured nothing and prints no pass.
  - Arm G is deferred. Its coverage of 0 of 18 is printed and not required, and the draft names the later go as an owner choice made after the Claude and Codex results.
- **Walks (step 10).**
  - 387 walks are registered, none counted.
  - Recheck wave 3 added `recheck-1.json` to most arm A walks. Most now carry `nested-agent` or `harness-condition-violated` under the checker constants in force, because they predate `session-store.json` and the box condition. They are printed as not counted, and the coverage of the run arms still holds (athena 16: 18/18, 18/18, 90/90, 18/18, 18/18).
  - `walk_regrade.py --check` re-derives the recheck chains of 313 walks.

## Step 3: the athena files

Every file names commit `3154459688dbafdcf9dac7f1c80626af3c09247e`, equal to `COMMIT`. Together they cover:

- `run_checks.py`;
- each of `freeze_rehearsal.COMMANDS` (the nine base commands, the five `WALK_COMMANDS` and the two `WALK_PIN_COMMANDS`);
- `freeze.py --check`;
- the three-leg check.

`holdout.py --check` names itself as OWED, exit 1, and does not pass. `freeze.rehearsal_required_steps` requires the real `--holdout-tool` run and the live-box pass line before any real freeze.

| file | commit | last line |
|---|---|---|
| 01-run-checks-py-its-lines-24-at-a-time-by-the-remote-suite-s-b.txt | 31544596 | `run_checks: 530 of 530 commands passed` |
| 02-test-round4-py.txt | 31544596 | `OK (skipped=62)` (5953 tests) |
| 03-copy-manifest-py-check.txt | 31544596 | `ok: 858 files from 105 fragment(s) (…) … 8 frozen paths unchanged since 68ec902f63bf` |
| 04-tests-test-box-integration-py.txt | 31544596 | `OK` (61 tests) |
| 05-tests-test-pipeline-py.txt | 31544596 | `OK` (88 tests) |
| 06-probes4-py-check.txt | 31544596 | `probes4: 9 tasks, 18 halves, 169 rows, 1690 cells graded, 0 defects, 0 problems` |
| 07-build-draft-py-check.txt | 31544596 | `ok: the committed draft is what build_draft.py builds` |
| 08-leak-grep-py-check.txt | 31544596 | `ok: 25 leak word(s) grepped against 386 real session(s); none would void one; 1 session(s) not grepped (unreadable, named above)` |
| 09-holdout-py-check.txt | 31544596 | `OWED: holdout.py --check lives in private aegis (ruling C4); … so it did not run and this rehearsal is not all green` (exit 1) |
| 10-review-kit-rounds-py-check.txt | 31544596 | `ok: 5 registered round(s) graded, every report committed, 0 voided; prompt pinned at 4246efa5b409` |
| 11-walk-register-py-check.txt | 31544596 | `ok: 387 registered walk(s), each with its folder, none counted` |
| 12-mode-binding-py-walks-check.txt | 31544596 | `36 of them are input-side only: their CLI writes no mode record, so the launch argv is what was checked, never a mode the session recorded.` |
| 13-fixture-walk-py-check.txt | 31544596 | `ok: 387 committed walk(s) graded, each read through its own harness's reader, …; 41 by a recorded per-walk exception, printed above` |
| 14-run-py-walks-check.txt | 31544596 | `run: 387 walk(s) regraded, every grade.json the regrade's bytes (313 graded, 74 pending documents that grade nothing yet); never counted` |
| 15-walk-regrade-py-check.txt | 31544596 | `walk_regrade: ok` |
| 16-walk-plan-py-coverage-require-run-arms.txt | 31544596 | `ok: every required walk of the arms the freeze runs is covered` |
| 17-walk-pins-py-check.txt | 31544596 | `walk_pins: 387 registered walk(s) read; every one on the draft's version pins and image ids, … (a walk records the pin, so this compares the pin with itself: …)` |
| 18-freeze-py-check.txt | 31544596 | `freeze: 858 fragment-claimed files and 4 native-reader record(s) owned; 8 of 8 legs hold; no takes or freeze performed` |
| 19-freeze-unrecorded-shapes-problem-prereg-draft-json-legs-i-ii.txt | 31544596 | `every leg holds` |

No red needed explaining apart from the holdout line. Athena 10 counts 5 rounds: this round's row is committed after `COMMIT`, as row 5's was after review 5's launch commit.

## Step 4: the light checks, run from `study/`

Every command exited 0.

| command | tail of output |
|---|---|
| `python3 evals/gap-study-4/copy_manifest.py --check` | `ok: 858 files from 105 fragment(s) (…)` |
| `python3 evals/gap-study-4/freeze.py --check` | `… walk coverage of the arms the freeze runs: ok` / `take-order function: ok` / `prepare (dummy review, synthetic beacon reading): ok` / `freeze: 858 fragment-claimed files and 4 native-reader record(s) owned; 8 of 8 legs hold; no takes or freeze performed` |
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
| `intervals.py --check` | `done-commit binding: 15 of 15 results files equal their blobs` / `gap-study intervals: PASS` |
| `result.py --check` | `result: no takes; no table measured or written` |
| `check_results.py --check` | `check_results: no takes; no frozen pins or publication measured` |
| `batch.py --check` | `batch: routing.json ready` |
| `python3 evals/gap-study-4/lint_language.py evals/gap-study-4/` | `clean — 223 input(s) scanned, 94 excused line(s) on record` |
| `python3 evals/gap-study-4/lint_pooling.py evals/gap-study-4/` | three `not scanned: … a bound review record (BOUND_REVIEW_RECORDS)` lines / `clean — 220 file(s) and 0 commit(s) scanned, no excusal path` |
| `python3 evals/gap-study-4/prereg.py --status` | `This is a DRAFT. No take may run against it and no number may be graded from it. The walks are what turn it into the frozen file.` |
| `python3 evals/gap-study-4/review_kit/rounds.py --check` | `ok: 5 registered round(s) graded, every report committed, 0 voided; prompt pinned at 4246efa5b409` |

## Findings

| # | finding | class | loosens or tightens | would fixing it change a criterion, a reading or a claim? |
|---|---|---|---|---|
| M1 | The freeze takes "latest review" from the files at HEAD and lets rounds 1-4 seed without a digest. Deleting review 5's pair and flipping one register field (one commit, four files) made review 4's masked, approving report the seed in a scratch clone. The draft says a registered review cannot be dropped. | MAJOR (I lean MAJOR: a one-commit road to the irreversible step, contradicting the draft and the code's own comment, cheap to close) | tightens | A claim: `round_4_limitations[10]` and `freeze.py:1182` become true. No criterion or reading. |
| M2 | Nothing binds the code frozen to the code the seed review read. Only `prereg.json`'s sha256 is compared, and take-path and freeze code have changed since review 4 with the draft unchanged. | MAJOR (lean MAJOR, less sure than M1: the review's named subject is the draft; the draft's own text relies on the review for code) | tightens | A claim: that the instrument that ran is the one a blind review read, which `round_4_limitations[12]` implies. No criterion or reading. |
| m1 | Take-path code (`box/preflight.py` postflight, `drive.py:2438`) changed on 1 Nov, after the take order was public (31 Oct). The draft's residual does not say code may change then (review 5's m11, extended). | MINOR | tightens | Disclosure only |
| m2 | `round_4_limitations[1]` still says "committed unedited" is not enforced. It is now enforced by digest from round 5 on, and the two-record road that remains is unnamed. | MINOR | tightens | Disclosure only; the draft now understates a binding |
| m10 | The walk path gate does not read claude-code sub-agent streams (w255, w260) (carried) | MINOR | tightens | Corrects the gate's printed claim for two walks |
| m1c | A stopped take of unknown phase can be re-run after its end state is seen, and the discarded reading is not published (`batch.py:512`, carried) | MINOR | tightens | Could change a reading in a cell where it happens; no criterion |
| m3 | Beacon swaps are unbounded and not printed in RESULT.md (carried) | MINOR | tightens | Disclosure only |
| m4 | Two agent-caused driver stops are missing from the agent-caused-routes limitation (carried) | MINOR | tightens | Disclosure only |
| m5 | Arm A's account state is missing from the vendor-account residual (carried) | MINOR | tightens | Disclosure only |
| m6 | The settings hot-reload gap is in code, not in the draft (carried) | MINOR | tightens | Disclosure only |
| m7 | The hashed codex template leaves out the per-take trust table (carried) | MINOR | tightens | Makes the hashed-bytes claim exact; no reading |
| m8 | Table 6 puts model and agent-system rows under one heading (carried) | MINOR | tightens | Presentation only, no count |
| n1 | fold7's edits to `language-allowlist.json` and `tests/test_run_take.py` are named in no copy fragment | NIT | n/a | No |
| n2 | The postflight session-pair admission is not in `box_residuals` | NIT | n/a | No |
| n-carried | Review 5's n1-n8 and n10 (wording, stale docs, lint scope, censuses, exemption list), unchanged | NIT | n/a | No |
