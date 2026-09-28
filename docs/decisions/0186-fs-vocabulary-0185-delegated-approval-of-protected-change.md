---
date: 2026-09-28
status: standing
kind: decision
touches:
  - gars/_system/tools/registry.json
  - gars/_system/tools/policy.py
symptoms:
  - follow-up 0185 changes the tool registry and the typed-argument policy under the protected prefix gars/_system/ with no owner approval record
---
# Filesystem-tool vocabulary follow-up 0185: approval of its protected change, under the owner's delegation

Addendum to [0185](0185-filesystem-tool-vocabulary.md), which stays byte-identical.
The two files this record approves are protected (`gars/_system/`; §9.3, R-094), so the change needs an owner-approval record.
The owner delegated that approval on 23 September 2026, so this record is written by Glitch under that delegation and labelled as such: **approved by Glitch under Javier's 23 Sep delegation**; no sentence in it is the owner's.
Its shape follows [0171](0171-executor-env-0170-delegated-approval-of-protected-change.md).

## Context

Follow-up 0185 widens the filesystem tools' vocabulary by an allow-list (grep `-E -F -w -l -c`; find `-maxdepth`, `-mindepth`, `-name`, `-iname`, `-type` with validated values), and refuses an unquoted `*`, `?` or `[` in any filesystem command.
The lane's coordinator (glitch-a1, writing under the owner's standing delegation and not in the owner's words) ruled on 27 Sep 2026, after the lane's reproduction, that the pre-existing glob escape comes into this lane as a refusal-path fix across every filesystem command, and accepted the lane's flagged deviation that the refusal text never suggests `rg -g`.
It was built on its own branch from public main `a80df2d` by a headless Claude Code producer (Opus 5.5) in an isolated clone (session `6ea365d9-e4a6-4e71-b1c3-b69d4bbc9ef9`, three rounds), and reviewed twice by a fresh Claude Code context (Opus 5.5) from a separate checkout with no remote that never saw the producer's transcript.
**Same-model cost.** Both Codex seats were in use by other lanes that night, so the producer and both reviewers are the same model; a same-model reviewer shares the producer's blind spots more than a different model would (the 0009/0013/0014 precedent). The reviews were kept independent by a fresh context, a separate no-remote checkout, a stated threat model, and no access to the producer's transcript; review r1 found a BLOCKER the producer had missed.
Producer commits, each under the repository's own identity, red-first (the failing tests committed before each fix):
round 1 `14f156b` (the new test module, red at `a80df2d`), `ebaaa6f` (the vocabulary and the find-only glob rule);
round 2 `d02c4f3` (unquoted globs on every filesystem command, red at `ebaaa6f`), `49e27da` (the rule widened);
round 3 `9abdb44` (find's operator words, red at `49e27da`), `a6c6139` (the fix).
The lane's own commit `9e9437c` adds 0185, the index and the suite totals.
Reviews, kept outside the repository and cited by their kit folders:
`gars-fs-vocab/review-1` REJECT on `a80df2d..49e27da` (one BLOCKER, one MINOR, two NOTE). F-1, BLOCKER on a refusal path: the Bash tool's `find` is Claude Code's bundled bfs with GNU semantics, which starts the expression at a lone `!`, `(`, `)` or `,`, so `find , -maxdepth 9` and `find "!" -name x` passed the guard as a path while find walked the default `.`, listing a closed project's raw file names (0107); answered in round 3. F-2, MINOR: the tests judged find under the dispatcher's BSD semantics; answered in round 3. F-3 and F-4, NOTE: a pinned closed-project row and the harvest wording; answered in round 3.
`gars-fs-vocab/review-2` APPROVE on `49e27da..a6c6139` (two NOTE; no MINOR or worse, so the review loop ended). It found F-1 closed for every spelling it tried under bfs semantics and no other word that starts the expression. F-1, NOTE: the dispatcher rows omit `)`; 0185's D2. F-2, NOTE: `-name "("` under a closed project; 0185's D3.
Before the build, the lane reproduced each refusal and the glob escape with json-built hook payloads and no model.

## Decision

Glitch, under the owner's 23 September 2026 delegation, approves the following protected changes as merged.

1. **`gars/_system/tools/registry.json`**: `fs.search`'s flag list gains `-E`, `-F`, `-w`, `-l`, `-c`; `fs.find` gains the `expression` input property and the `predicates` table. Every other byte is as at `a80df2d`.
2. **`gars/_system/tools/policy.py`**: `FIND_OPERATORS`; in `validate_args`, the find operator-word path refusal, the one-path rule's text and the pairwise predicate check; in `argv_for`, the expression after the paths for a tool with predicates; in `simple_tokens`, the unquoted-glob flag and its refusal for a registry filesystem command (the filesystem set computed once and reused by the quoted-operator check); in `parse_argv`, find's path/expression split. Every other line is as at `a80df2d`.

Outside the protected prefixes, recorded for completeness: the new `gars/tests/test_fs_vocabulary.py`, the additions to `gars/tests/test_bash_lexer.py`, the four moved EXPANSION expectations in `gars/tests/test_nonpublic_read_block.py` named in 0185, 0185 itself, the index, and the README and DEVELOPMENT counts and skip figures.

## The lane's rulings

All are the lane's, under the owner's standing delegation of 23 Sep 2026; none is the owner's: ruling 0185, the coordinator's glob-scope ruling and its acceptance of the `rg -g` deviation, the closed-project `grep -E` row encoded as "the same outcome as the bare spelling", the four EXPANSION rows moved to `base`, the round 2 and 3 briefs, and the review dispositions above.

## What this does not close

- 0185's D1 to D4.
- The build node's first mode C run was red on one test that this landing does not touch (below); the lane took one labelled mode C re-run, green, and both runs are recorded. The race it met is a pre-existing executor defect, named here for its own lane: the local runner's `echo $? > "$3"` truncates the exit file before writing it, and `_local_status` reads an empty exit file as a bare `FAILED`.
- The mutation proof ran on this Mac (a module of about 30 s), not on the build node.

## Test

Glitch verified the landing merge `122471f` (branch head `9e9437c` merged onto public main `a80df2d`), each evidence run with a process snapshot at its start and end.

- This Mac (macOS, Python 3.8.2), a fresh clone of the merge, with Docker answering and row 5's scratch folder and `TMPDIR` set as CI sets them: `Ran 1172 tests`, `OK (skipped=14)`, README's mode-A figure; contracts, counts and the pre-registration check clean; the repository status clean after the run. Its `evals/test_harness.py` step ended with 13 errors, all `str.removesuffix`, `str.removeprefix` or `ast.unparse`, which are Python 3.9 APIs this Mac's Python 3.8.2 lacks; `evals/` has no change in this landing, 0156, 0161, 0166 and 0171 recorded the same red, and the build node ran the harness 44 OK at the merge, so the red is the interpreter's, not this change's. Beside it: another lane's single targeted test module at the start, and another session's reviewer and one targeted module at the end.
- The build node's owner account (Linux, Python 3.13.5), fresh bundle clone of the merge, solo (the snapshots at the start, between the runs, after them and at the end show no other suite, Codex or Claude on any account): `Ran 1172 tests`, `OK (skipped=82)` without containers; contracts and counts clean; the evaluation harness 44 OK and the pre-registration check clean. With `TMPDIR` also unset, the first run was `Ran 1172 tests`, `FAILED (failures=1, skipped=124)`: `test_execution_policy`'s `test_prepared_local_failure_refuses_unclassified_retry` read the local job's state as `FAILED` where it expects `FAILED:EXIT_17`. Neither `gars/_system/executorlib.py` nor that test changes in this landing. The lane reproduced the mechanism deterministically at `a80df2d` (a finished local job whose exit file exists but is empty reads `FAILED`; the same file holding `17` reads `FAILED:EXIT_17`), and the test run alone 40 times at the merge in the same environment failed 0 times, so the red is a load-dependent race in the executor, not this change. One labelled re-run of that mode on a fresh bundle clone, solo: `Ran 1172 tests`, `OK (skipped=124)`.
- GARS's own Fresh-clone gate script, taken from `.github/workflows/fresh-clone.yml` and run against the records commit's `README.md` with the `TMPDIR`-unset Linux run's log: `plain run: Ran 1172 tests, OK, skipped 124` and `ok: 124 skips, at most 124 documented` (a planted 125 fails it). The log is the labelled mode C re-run's; the first run's red would fail the gate.
- At the merge's tree: `check_counts` 1172 clean; `check_contracts` 14 clean; `test_decision_links_resolve` OK; `release_check.py --check` 13/13.
- A mutation proof at the branch code head `a6c6139`: sixteen mutants (`-exec` or `-delete` declared; `-maxdepth` or `-type` widened; the value check skipped; the glob rule dropped, narrowed to `find`, skipped for `rg`, or losing any one of `*`, `?`, `[`; `argv_for` dropping the expression; R-073 skipped for a call with an expression; `-f` added to grep's list; the operator-word path check dropped; the parser's operator-word stop dropped), each killed with the unchanged control green; the lane re-ran the narrowed-to-`find` and skipped-for-`rg` mutants itself at the merge's tree (47 and 5 failures, control OK), and the reviewers re-ran the first eleven independently.
- The model-free probe at the merge: 92 json-built payloads through the guard, 25 allowed and 67 refused, each as 0185's table says; at `a80df2d` the same probe allowed `cat ..*/CLAUDE.md`, `ls ..*`, `grep -r x .*`, `rg -n x *`, `find *`, `find ,` and `find "!"`, which are refused at the merge.
- The smoke delta (row 14's ceremony): one run of three `claude-opus-5-5` sessions at `122471f`'s tree, each `export_complete`, prompt and suite hashes equal to the previous record's; run-1 3/3; `delta` `0/1`, `no change` against `evals/runs/smoke/smoke-20260927-env-allowlist-2.json`, floor `evals/runs/smoke/smoke-20260926-row-14-activation.json`; `smoke.py score` verdict ok, 0 findings, 3 of 3 records read, 15 tasks regraded, 15 outputs hashed (`evals/runs/smoke/smoke-20260928-fs-vocab.json`). Another lane's reviewer session and a targeted test module ran on this Mac beside it, and another lane's producer started as it ended.
- The outgoing range `a80df2d..` the records commit has no gitleaks finding under either ruleset, no canary and no private address or path.

## Status

Standing. Approval of follow-up 0185's protected changes only.

## Date

2026-09-28
