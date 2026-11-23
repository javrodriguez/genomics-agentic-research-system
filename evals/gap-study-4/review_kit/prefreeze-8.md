prereg.json sha256: 37fd08047b66cbaee8cc12cd05a823692e2bafebaaa599d6db53178482b5c0e3

# Pre-freeze review 8 of gap-study-4

**Ruling: DO NOT FREEZE.**

The reviewed commit, from `COMMIT`, is `272d8fe298f8390ecfaa1c3cea72f4389b6b3157`, and `git -C study rev-parse HEAD` gives the same commit. `rounds.json` at this commit holds rows 1-7. Row 8 is expected to land in a later commit with `launch_commit` equal to `COMMIT`. A reader can confirm that from the row.

`diff prereg.json study/evals/gap-study-4/prereg-draft.json` prints nothing. `cmp prereg.json prereg-as-the-previous-review-read-it.json` is also silent, and the two files have the same sha256. The draft has not changed since review 7, so the JSON diff of step 2 is empty.

Since review 7 (`3c31d76b`), 327 commits landed:

- 313 are walk rechecks (`rehearsals/w*/recheck-4.json`, one per graded walk, never counted). They were forced because fold 10 changed a checker-code file.
- The rest are folds 9 and 10, review 7's own records, and one test fix at HEAD. Excluding `rehearsals/`, `git diff --stat 3c31d76b HEAD` lists 26 files: `freeze.py`, `result.py`, `check_results.py`, `review_kit/rounds.py`, `review_kit/commit_review.py`, `review_kit/check_real_sessions.py`, `language-allowlist.json`, four `COPIED.d` fragments, review 7's report, its as-written copy and blindness record, `rounds.json`, and 11 test files.
- No file under `box/` or `graders/` changed, and neither did `routing.json`, `routing.py`, any adapter, transcript reader, `check_take.py`, `batch.py`, `drive.py`, `takes.py`, `stats.py` or `intervals.py`.

Fold 9 answers review 7's M1 in code. `freeze.py` now always writes `PUBLISHED_TIP_LIMIT` into the frozen file as `published_tip_residual`. `result.py` prints it under its own heading, and `result.derive` refuses a frozen file whose field differs (fold 10). Fold 9 also closes review 7's m-new-2: `rounds.py --add` now refuses unless the kit's `COMMIT` is HEAD. Both changes are sound as far as they reach.

But the new guard lives only in the producer (`result.py`), not in the checker (`check_results.py`). Reading why led to the one MAJOR below, which is wider than the tip limit. After the freeze, no checker re-derives that the frozen file is the reviewed draft plus the freeze's own keys, or that a valid review seeded it.

## Threat model, restated and corrected

After the takes exist, the operator could move a count, label or published sentence. They could edit, re-date, re-run, re-route, re-order or misfile a single record. They could choose among commits, seeds or reviews. Or they could change code, configuration or pins after the freeze. Inside a take, the agent could try to reach past its run tree and its one vendor host, to a credential, to the study's files and graders, or to the evidence the graders read. It could also make an untaken step look taken.

One correction, which review 7 also made. A choice among reviews, and the act of freezing itself, happen *before* the takes exist. The operator's threat model must therefore include the window from the last review to the freeze commit. That window includes the step where `freeze.py --write` writes the frozen file and the operator commits it by hand (`freeze.py:1716`: "commit all three in one commit"). Every finding below is judged against that statement.

These stay out of scope, as limitations the draft must name: complete, coherent fabrication across every ledger; what a vendor serves beyond its client's records; and the honesty of the machines and runner beyond what they commit.

Judged on that statement:

- `limitations`, `box_residuals` and `not_poolable` are honest about the take side.
  - `box_residuals` names the visible arm A token and arm G key, the agent-owned graded record, unlogged reads, and watcher overflow.
  - `not_poolable` forbids comparison, pooling and bridging with rounds 1-3, enforced by `lint_pooling.py` and `result.py`.
- `predictions_rule` is honest: every prediction is `null` with "no informed basis", and it says the 387 walks were read and inform nothing.
- `round_4_limitations[6]` trusts "the driver, checker, routing and batch code at the frozen commit". It does not trust a freeze performed by hand, and nothing in the draft says the freeze's gates are checked only once, at the act.
- `[10]` is now qualified by the frozen-file limit, but only on the producer's side (M1).
- `[1]` still understates a binding (m2, carried).

## MAJOR findings

### M1. Nothing after the freeze checks the frozen file against the reviewed draft or its seeding review, so one hand edit at the freeze commit changes the design, the seed review or the tip limit unseen

**Where.**

- `study/evals/gap-study-4/freeze.py:1673-1716` runs every review and design gate: `review_file_problems` (ruling, registration, launch binding, later review, grandfathering) and `keys_outside_the_freeze` (`:1709`). It runs them once, inside `main`, and then writes files the operator commits by hand.
- `check_results.py:891-920` (`check_frozen_content`) is what reads the freeze afterwards, and it compares four things:
  - the frozen file with *later* versions of itself (`frozen_content_problems`, `:461`);
  - the rehearsal record's line 1 with `draft_sha256_at_freeze` (`:813`). Both values sit in the same hand-committed file, so this compares the file with itself;
  - the freeze commit's study tree with the rehearsed tree, where the frozen file is "outside the binding on both sides" (`:576-578`);
  - the take order, reading only the draft's beacon round (`:869-878`).
- No post-freeze code reads `pre_freeze_review_file` or `pre_freeze_review_sha256` (written at `freeze.py:1701-1702`), or `keys_outside_the_freeze`, `read_ruling`, the launch binding or `published_tip_residual`. The only post-freeze reader of `published_tip_residual` is `result.derive` (`result.py:357`, `:384-391`), which is the producer, not the checker. `check_results.main` loads the frozen file with a bare `prereg.require_frozen` (`check_results.py:1066`).

**Shown, read-only, from `study/evals/gap-study-4/`:**

```
$ grep -rn "pre_freeze_review_file\|pre_freeze_review_sha256\|draft_sha256_at_freeze" --include=*.py . | grep -v "^./tests/"
check_results.py:813:    if lines[0] != frozen.get("draft_sha256_at_freeze"):
freeze.py:657:  … (FREEZE_WRITTEN_KEYS)
freeze.py:1701:        frozen.update(draft_sha256_at_freeze=digest, pre_freeze_review_file=review_file,
freeze.py:1702:                      pre_freeze_review_sha256=hashlib.sha256((REPO / review_file).read_bytes()).hexdigest(),

$ python3 -B - <<'E'   # draft with `views` replaced, as a hand-edited frozen file would carry it
…
freeze.keys_outside_the_freeze -> ['views']
check_results.frozen_content_problems(frozen, frozen) -> []
check_results reads keys_outside_the_freeze / pre_freeze_review_file / published_tip_residual: []
```

The suite's own test documents the tip-limit half. In `tests/test_pipeline.py` (`test_frozen_content_reads_the_drafts_amendment_dict`), `check_publication` returns `[]` for a page with no limit when the frozen file carries none. The page is refused only when the frozen file carries the limit and the page drops it.

**What a single edit does.** Between `freeze.py --write` and the operator's commit, one edit to `prereg.json` passes every post-freeze check. It needs no fabricated chain. The edit could:

- change a design key the review read (a `views` or `routes` entry, a `stop_taxonomy` row, a criterion);
- point `pre_freeze_review_file` at a report that found a blocker, or at none;
- delete `published_tip_residual`. Then `check_results.py` accepts a RESULT.md without the review-record limit (made by `result.render` directly). This is exactly the qualification review 7's M1 required, and the operator who erased a later review is the one motivated to drop it.

After that commit, `check_results.py --check` holds every later version to the edited file. The push witness then makes the edit permanent rather than detectable. The review machinery built over folds 5-9 (`later_review_problem`, `launch_binding_problem`, `committed_once_problem`, grandfathering) binds only a freeze that ran `freeze.py` unaltered up to its commit. That is the operator's word, which the draft nowhere names as such.

**Why it is material.** The study's central claim is that what ran was the design these reviews read, seeded by a review that found no blocker. A single edited record moves a criterion, a seed or a published sentence, and none of this needs a coherent fabrication. The draft does not name it. `[6]` trusts the checker and driver code, not a hand-made freeze. A cheap check closes it, and it can only be added before the freeze, because `check_results.py` is pinned at the freeze.

**A cheap fix, verifiable by a command.** It changes code only and needs no change to the draft. In `check_results.check_frozen_content`, at `freeze_commit()`:

1. Read `prereg-draft.json` at the freeze commit (already bound to the rehearsed tree) and require its sha256 to equal `draft_sha256_at_freeze`.
2. Require `freeze.keys_outside_the_freeze(draft, frozen) == []`, and every `FREEZE_WRITTEN_KEYS` member present.
3. Require `published_tip_residual == freeze.PUBLISHED_TIP_LIMIT`, by calling `result.tip_limit_held`.
4. Require that `pre_freeze_review_file` at `frozen_at_commit_parent` hashes to `pre_freeze_review_sha256`, that `freeze.read_ruling` reads freeze approval in it, and that `freeze.review_file_problems` is clean when re-run as of that parent.

Add one mutant per clause to the battery. Alternatively, name the gap in the draft. That is weaker, and fold 9 says the draft cannot change.

**Lean.** MAJOR, with moderate-to-high confidence. Against: the act is a deliberate hand edit at the one moment the operator is most watched, and a reader who diffs the frozen file with the draft at its parent would see it. For: no check makes that diff, the brief rules a single edited record a defect, the provenance fields are written and never read, and the fix is small and possible only now.

## Other findings

### MINOR

- **m2 (carried from reviews 6 and 7).** `round_4_limitations[1]` still says "'committed unedited' is not enforced". Since round 5 it is enforced by the report digest and by `freeze.committed_once_problem`. The draft understates a binding. Fixing it tightens disclosure only.
- **m-new-3 (carried from review 7).** `launch_binding_problem` (`freeze.py:1455`) compares `PINNED` and `COPIED.d` and leaves out `rehearsals/w*/`. This round alone added 313 walk files without a new round being needed. The walk gates re-derive them at HEAD (athena 11-17 are green), so an edited walk still needs a coherent regrade. Fixing it tightens the check.
- **m10 (carried).** `rehearsals/w255/subagents/` exists, and `grep -c subagents fixture_walk.py` gives `0`. The walk path gate does not read claude-code sub-agent streams (w255, w260). Fixing it tightens the check.
- **m1c (carried).** The unknown-phase early return is still at `batch.py:512`. It is named in the draft, and a re-run stands only on an end state with no wrong action. Fixing it tightens the check.
- **m7 (carried).** `box/take_config.py:79-86` still appends the per-take codex trust table to the hashed template. Fold 10's `check_results.pinned_bytes` now re-renders templates through `take_config.files_for`, so a publication-time check compares like with like. The draft's "the bytes the draft hashes" is still inexact for the trust table. Fixing it tightens the check.
- **m1, m3, m4, m5, m6, m8 (carried, files unchanged since review 7).**
  - m1: take-path code changed after the take order was public.
  - m3: beacon swaps are unbounded and not printed on RESULT.md.
  - m4: two agent-caused driver stops are missing from `[2]`.
  - m5: arm A's account state is missing from the vendor-account residual.
  - m6: the settings hot-reload gap is in code but not in the draft.
  - m8: table 6's heading mixes model rows and agent-system rows.

  Each fix tightens disclosure or presentation, and none moves a count.

### NIT

- **n-new-1 (carried).** The athena file `19-…-legs-i-ii.txt` is named for legs i-ii, but its command line says "legs i-iii".
- **n-new-2.** HEAD (`272d8fe2`) edits `tests/test_holdout_digests.py` (its keys-not-allowed mutant), and no `COPIED.d` fragment names the edit. The commit body explains it. Review 6's n1 was the same class.
- **n-carried.** Review 6's n2 and review 5's n1-n8 and n10 are unchanged.

### Read and found sound

- **Fold 9 and fold 10 against review 7.**
  - `PUBLISHED_TIP_LIMIT` (`freeze.py:1190-1198`) names the residual in plain words and cites `[10]`. It is written always (`:1706`) and is a freeze-written key (`:662`).
  - `result.tip_limit_held` refuses a missing, empty, edited or padded value (`tests/test_fold10_rehearsal_road.py`).
  - `rounds.py --add` refuses a kit whose `COMMIT` is not HEAD (`review_kit/rounds.py:267-276`).
  - Round 7 is grandfathered (`freeze.py:1566`). Its report differs from the as-written copy by one line, line 109, "This sound" to "This is sound", as the correction record says: `diff review_kit/prefreeze-7.as-written.md review_kit/prefreeze-7.md`.
  - The commit_review door (`UNBOUND_REPORTS`) admits only round 7, by exact digests.
  - The draft's line citations still land. I spot-checked 13, among them `freeze.py` 690/700/709/876/880/184/233, `result.py` 122/361 and `check_results.py` 153/624/739/863: all hit.
- **Fold 10's `check_pins`.** Before fold 10, `image_locks` and `config_templates` pins were read from the repository root, where those paths do not exist. So any publication would have been refused, failing closed. Fold 10 reads them where their writer can. A name the render does not make is `None` and is refused, never dropped.
- **Copy record (step 6).** `copy_manifest.py --check` gives 870 files from 109 fragments: 819 new, 29 edited, 22 identical and 1 acceptance-records entry. I compared all 22 identical files with their sources byte for byte, and 0 differ. Fold 9 and fold 10 name every file they touched, except n-new-2.
- **System under test.** `variants.PINNED_TREE` is `844a4ce0d894…`. `git rev-parse 844a4ce0…:gars` gives `8a54e0f8cd91…`, which equals `check_take.GARS_TREE_SHA`.
- **Container (step 7), unchanged since review 7, re-read at the points that matter.**
  - Entry: `docker create` with a keep-alive PID 1, then every agent action is a `docker exec --user AGENT_USER` (`box/run_take.py:16`, `:1282`).
  - Mounts: exactly two bind mounts, the run tree and the per-take config folder. The rest is a read-only root and tmpfs (`:937-954`), with all capabilities dropped and no-new-privileges.
  - Hosts: one per harness through the squid proxy on the internal network: `api.anthropic.com`, `chatgpt.com` and `generativelanguage.googleapis.com` (`box/egress/proxy_conf.py`, `HOSTS`).
  - Credentials:
    - arm A: `CLAUDE_CODE_OAUTH_TOKEN` in the environment;
    - arm O: a ChatGPT `auth.json` lease in `CODEX_HOME` on the config mount, and no environment credential;
    - arm G: `GEMINI_API_KEY` in the environment (`run_take.py:163-175`).
  - Each of these is named in `box_residuals`, as is the agent-writable graded record. I found no difference from the draft.
- **Vendor arms (step 8).** `freeze.py --check` and the three-leg check both pass. Arm G is deferred, and its walk coverage is printed as recorded, not required. `stats.check_families` keeps within-harness model rows apart from between-harness agent-system rows (`stats.py:893-907`, `:1176-1189`). The adapters, templates, locks, price tables and routing markers are unchanged since review 7, and `freeze.py --check` pins all 876 paths.
- **Outcome, walks, publication (steps 9-11).** `routing.py --check` proves the no-match defaults. `probes4.py --check` grades 1690 cells with 0 defects. Every take-side gate says it measured nothing rather than printing a pass. `lint_language` and `lint_pooling` are clean. `result.py` has no rate or model-comparison sentence that I could find (grep for `%`, "better than", "outperform": none outside comments).

## Step 3: the athena files

All 19 files name commit `272d8fe298f8390ecfaa1c3cea72f4389b6b3157`, which equals `COMMIT`. Together they cover `run_checks.py`, every member of `freeze_rehearsal.COMMANDS` (base, `WALK_COMMANDS` and `WALK_PIN_COMMANDS`) and `freeze.py --check`.

| file | command | exit | last line |
|---|---|---|---|
| 01 | `run_checks.py` (battery mode) | 0 | `run_checks: 530 of 530 commands passed` |
| 02 | `test_round4.py` | 0 | `OK (skipped=62)` (6025 tests) |
| 03 | `copy_manifest.py --check` | 0 | `ok: 870 files from 109 fragment(s) (…)` |
| 04 | `tests/test_box_integration.py` | 0 | `OK` (61 tests) |
| 05 | `tests/test_pipeline.py` | 0 | `OK` (89 tests) |
| 06 | `probes4.py --check` | 0 | `probes4: 9 tasks, 18 halves, 169 rows, 1690 cells graded, 0 defects, 0 problems` |
| 07 | `build_draft.py --check` | 0 | `ok: the committed draft is what build_draft.py builds` |
| 08 | `leak_grep.py --check` | 0 | `ok: 25 leak word(s) grepped against 386 real session(s); none would void one; 1 session(s) not grepped (unreadable, named above)` |
| 09 | `holdout.py --check` | 1 | `OWED: holdout.py --check lives in private aegis (ruling C4); … so it did not run and this rehearsal is not all green`. It names itself as not run, as required. |
| 10 | `review_kit/rounds.py --check` | 0 | `ok: 7 registered round(s) graded, every report committed, 0 voided; prompt pinned at 4246efa5b409` |
| 11 | `walk_register.py --check` | 0 | `ok: 387 registered walk(s), each with its folder, none counted` |
| 12 | `mode_binding.py --walks --check` | 0 | `36 of them are input-side only: … never a mode the session recorded.` |
| 13 | `fixture_walk.py --check` | 0 | `ok: 387 committed walk(s) graded, each read through its own harness's reader, … 41 by a recorded per-walk exception, printed above` |
| 14 | `run.py --walks --check` | 0 | `run: 387 walk(s) regraded, every grade.json the regrade's bytes (313 graded, 74 pending documents that grade nothing yet); never counted` |
| 15 | `walk_regrade.py --check` | 0 | `walk_regrade: ok` |
| 16 | `walk_plan.py --coverage --require-run-arms` | 0 | `ok: every required walk of the arms the freeze runs is covered` |
| 17 | `walk_pins.py --check` | 0 | `walk_pins: 387 registered walk(s) read; every one on the draft's version pins and image ids, …` |
| 18 | `freeze.py --check` | 0 | `freeze: 870 fragment-claimed files and 4 native-reader record(s) owned; 8 of 8 legs hold; no takes or freeze performed` |
| 19 | `freeze.unrecorded_shapes_problem(…)`: legs i-iii | 0 | `every leg holds` |

No red is left unexplained. The only non-zero exit is 09, the owed holdout step, which names itself.

## Step 4: the light checks, run from `study/`

Every command exited 0. `git -C study status --short` was empty before and after.

| command | tail |
|---|---|
| `copy_manifest.py --check` | `ok: 870 files from 109 fragment(s) (…)` |
| `freeze.py --check` | `freeze: 870 fragment-claimed files and 4 native-reader record(s) owned; 8 of 8 legs hold; no takes or freeze performed` |
| `freeze.unrecorded_shapes_problem(…)` | `every leg holds` |
| `build_draft.py --check` | `ok: the committed draft is what build_draft.py builds` |
| `leak_grep.py --check` | `ok: 25 leak word(s) grepped against 386 real session(s); none would void one; 1 session(s) not grepped (unreadable, named above)` |
| `probes4.py --check` | `probes4: 9 tasks, 18 halves, 169 rows, 1690 cells graded, 0 defects, 0 problems` |
| `routing.py --check` | `routing.json: 27 rows, 3 annotations, sound`, then the no-match proof: 21 input classes, each with its default |
| `contracts.py --check` | `every stored sentence is a byte substring of the blob it was pinned to` |
| `harness_bookkeeping.py --check` | `harness_bookkeeping: ok: 3 harness(es): claude-code, codex, gemini` |
| `denials.py --check` | `ok, having read 0 graded takes: none is committed yet, so nothing here is evidence about any denial. Not a pass.` |
| `completeness.py --check` | `completeness: no takes; no cells measured` |
| `takes.py --check` | `takes: no takes; no registration or outcome measured` |
| `costs.py --check` | `costs: no takes; no cost measured or written` |
| `stats.py --check` | `stats --check: no takes (0 results files); nothing was compared` |
| `intervals.py --check` | `gap-study intervals: PASS` (re-derives the earlier rounds' published intervals; it adds nothing to round 4) |
| `result.py --check` | `result: no takes; no table measured or written` |
| `check_results.py --check` | `check_results: no takes; no frozen pins or publication measured` |
| `batch.py --check` | `batch: routing.json ready` |
| `lint_language.py evals/gap-study-4/` | `clean — 230 input(s) scanned, 99 excused line(s) on record` |
| `lint_pooling.py evals/gap-study-4/` | `clean — 227 file(s) and 0 commit(s) scanned, no excusal path` |
| `prereg.py --status` | `This is a DRAFT. No take may run against it and no number may be graded from it. …` (1260 planned rows, 126 half-cells; arm G deferred) |
| `review_kit/rounds.py --check` | `ok: 7 registered round(s) graded, every report committed, 0 voided; prompt pinned at 4246efa5b409` |

Every take-side check says it measured nothing. None of them prints a pass over zero items.

## Findings

| # | finding | class | loosens or tightens | would fixing it change a criterion, a reading or a claim? |
|---|---|---|---|---|
| M1 | No post-freeze check holds the frozen file to the draft at its parent, to its seeding review, or to the tip limit. The freeze's gates run once, inside `freeze.py`, before a hand commit, and `check_results.py` never re-derives them. One edit at the freeze commit can change a design key, the seed review or the published review-record limit, and every later check passes. | MAJOR (lean MAJOR, moderate-to-high confidence: a deliberate edit at a watched moment, but no check looks, the provenance fields are never read, and the fix is cheap and possible only before the freeze) | tightens | A claim: "what ran is the reviewed design, seeded by a review that found no blocker" becomes checked rather than asserted. It changes no criterion or reading. |
| m2 | `[1]` says "committed unedited" is not enforced, but it is. (carried) | MINOR | tightens | Disclosure only. |
| m-new-3 | The launch binding leaves out `rehearsals/w*/`. (carried) | MINOR | tightens | No reading. It closes a road that needs a coherent regrade. |
| m10 | The walk path gate does not read sub-agent streams (w255, w260). (carried) | MINOR | tightens | It corrects the gate's printed claim for two walks. |
| m1c | An unknown-phase stopped take can be re-run after its end state is seen. It is named in the draft. (carried) | MINOR | tightens | It could change a reading in a cell where it happens. No criterion. |
| m7 | The hashed codex template leaves out the per-take trust table. (carried) | MINOR | tightens | It makes the hashed-bytes claim exact. No reading. |
| m1 | Take-path code changed after the take order was public, and the draft does not say it may. (carried) | MINOR | tightens | Disclosure only. |
| m3 | Beacon swaps are unbounded and not printed on RESULT.md. (carried) | MINOR | tightens | Disclosure only. |
| m4 | Two agent-caused driver stops are missing from `[2]`. (carried) | MINOR | tightens | Disclosure only. |
| m5 | Arm A's account state is missing from the vendor-account residual. (carried) | MINOR | tightens | Disclosure only. |
| m6 | The settings hot-reload gap is in code, not in the draft. (carried) | MINOR | tightens | Disclosure only. |
| m8 | Table 6 puts model and agent-system rows under one heading. (carried) | MINOR | tightens | Presentation only, no count. |
| n-new-1 | Athena file 19's name says legs i-ii, but its command says i-iii. (carried) | NIT | n/a | No |
| n-new-2 | HEAD's edit to `tests/test_holdout_digests.py` is named in no fragment. | NIT | n/a | No |
| n-carried | Review 6's n2 and review 5's n1-n8 and n10, unchanged. | NIT | n/a | No |
