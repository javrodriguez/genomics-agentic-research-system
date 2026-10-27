VERDICT: PASS
lane-tag: other
purpose: round-2

Fresh round-2 review of lane t104-mutation-baseline, range 3d278db9..5c54978c, judging the fold e205a256..5c54978c, on Tue 27 Oct 2026.
The reviewer was assigned by glitch-45, the Lane-orchestrator.
No code was changed.
Tests ran under /usr/local/bin/python3.12 with TMPDIR in the reviewer's scratch folder.
`mac_slot.py light-ok --tests --work gap-study-r4` first refused three times (CPU speed limit 37 to 70, below 80), then said `light ok: load1 4.57 < 16.00, memory pressure normal, CPU speed limit 89 >= 50`; every run below came after that.

## Findings

1. NIT, class: C. The red-first count in the fold's commit message and the COPIED.d fragment ("13 failures and 2 errors at fcf3401d") includes three failures that are not the lane's.
   On a `git archive` of fcf3401d with the head's `test_mutation_baseline.py` copied in, the result is `Ran 22 tests ... FAILED (failures=13, errors=2)`, as stated.
   But the three `runner='test_ci_job'` subtests fail in `test_ci_job.setUpModule` -> `history(REPO)` -> `git rev-parse --is-shallow-repository`, because an archive has no git history.
   The same three fail on a `git archive` of the head itself (`FAILED (failures=3)`), and the head's test file is green in the real worktree (`Ran 22 tests ... OK`).
   So the lane's own red-first evidence is 10 failures and 2 errors, all for the right reasons (listed under Q5).
   Nothing to change in code; the next record of this count should say 10 + 2, or name the three as environment reds.

2. NIT, class: C. `test_native_snapshot`'s new baseline runs both locators on the real imported module (`ns()`), while each witness runs them on an `exec`'d copy of the same source with `SnapshotRefused` swapped for the real one.
   The source bytes are the same, and the witness credits only a raised `SnapshotRefused`, which the baseline's `require_clean` turns into a refusal, so this cannot over-credit.
   Recorded as a small extension of the finding-6 residual, not a defect.

3. NIT, class: C (process). This review file is a new file under `lanes/`; the round-1 review was claimed in the lane's COPIED.d fragment by the fold, and this one will need the same claim when the lane closes.

No MAJOR or BLOCKER.

## Q1: round-1 findings, re-run at the head

- Finding 1 (test_rehearsals --witnesses), closed.
  The round-1 probe `probe_rehearsals.py` (every child, unmutated included, red on `TheRegisterFold.test_folders_match_by_exact_name` with `R5.case`) now exits 3.
  `probe_unwired.py`: `REHEARSALS code ('SystemExit', 3) children 1 argv0 has --mutant: False`, and the line `test_rehearsals witnesses BASELINE RED: exit 1; 1 failing or erroring: FAIL __main__.TheRegisterFold.test_folders_match_by_exact_name; the outcomes line names [...]`.
  One child ran, and it was the unmutated whole file.
  `_all("test_rehearsals")` is in `WITNESS_RUNNERS`.
  The baseline argv is the mutant's argv less `--mutant <name>`: the same file, run whole, with the `test_rehearsals outcomes` tag read.
  The real whole-file run is green: `Ran 9 tests in 65.397s`, OK.
- Finding 2 (test_gemini_adapter --generated-mutants), closed.
  `probe_unwired.py`: `GEMINI sweep ('SystemExit', 3)` with every `all_checks` red.
  `baseline_lines` builds both shapes `run_mutant` builds (transcript_gemini with gemini_adapter over it, and gemini_adapter over the real `tg`), with no mutation.
  On the real code, after `setUpModule` as `__main__` does it, `require_clean` prints `baseline: green, unmutated (no check line)` in 0.5 s.
  A real one-mutant shard, `--generated-mutants --shard 2/2000`, printed the baseline line, then `ran 1, killed 1, ... survived 0, stale 0`, exit 0.
- Finding 3 (five in-process witness runners and native_snapshot), closed.
  `probe_unwired.py`: `test_codex_agents_off witnesses BASELINE RED: 1 check line(s) over the unmutated files: table: red with no mutant`, exit 3.
  The reviewer's own probes (scratch `r2/probes/p2.py`), each with no mutant applied:
  vendor_bookkeeping with a check that raises -> `BaselineRed 3, a check raised on the unmutated code: KeyError`;
  codex_usage_source red only on the compiled unmutated `cus` module -> `BaselineRed 3, cus: U3: probe red on cus`;
  native_snapshot with the gemini locator alone red -> `BaselineRed 3, ... SnapshotRefused: probe gemini red` (the round-1 gap was one red locator; codex-alone is covered by the lane's test);
  codex_started_file_change with its last check red -> `BaselineRed 3`.
  On the real code each runner's `--witnesses` prints `baseline: green, unmutated (no check line)` and its count is what it was: codex_usage_source 9/9, native_snapshot 2/2, codex_agents_off 3/3, vendor_bookkeeping 13/13, codex_patch_reads 15/15, codex_started_file_change 3/3, all exit 0.
- Finding 4 (claims), closed.
  The `mutation_baseline.py` docstring and the fragment now list every user and every exempt runner with its reason; each reason was checked in the code (Q2).
- Finding 5 (test_endstate), closed.
  A not-clean control now calls `mutation_baseline.refuse` before the witness loop.
  Reviewer probe with only the last control red: `BaselineRed 3, a control (the unmutated test file) is not clean`, children `['control:tests/test_endstate.py', 'control:tests/test_sidecar.py']`, no witness child.
- Finding 7 (a raising check), closed.
  `require_clean` wraps `compute()` and turns any exception into the one `BASELINE RED` line and exit 3.
  codex_adapter, labelling, gemini_adapter and every new in-process user call it with a callable, so the check runs inside the wrapper.
  Real one-mutant shards: codex_adapter `--shard 2/2000` baseline green, `1 killed ... 0 survivors, 0 stale`, exit 0; labelling `--shard 2/2000` baseline green, `ran 2, killed 2 ... leaked 0`, exit 0.

## Q2: inventory, re-grepped

Every file under `evals/gap-study-4/tests` carrying `--witnesses`, `--generated-mutants`, `--witness-child`, `--gen-mutant` or `"--mutant"` was listed (28 test files plus `walk_mutation.py` and `mutation_baseline.py`).
Each is either a `mutation_baseline` user or one of the exemptions, and each exemption holds in the code:
- `test_walk_plan --generated-mutants`: `run_generated` re-emits the unmutated module, runs it, and returns 1 with "the sweep is not armed" before choosing a mutant.
- `test_gemini_tool_registry --witnesses`: returns 1 when `r1_problems() + r2_problems() + r4_problems()` is non-empty, before building a mutant.
- `test_gemini_undeclared_args --witnesses`: returns 1 when `u1 + u2 + u3` is non-empty on the real reader, before any witness.
- The `TestWitnesses.kill` of codex_adapter and gemini_adapter asserts `check(mod) == []` on the real module, and labelling asserts `run(check, sm, sh, ag) == []`, before mutating; the `--witnesses` CLI counts only `red by` lines appended after that assertion.
- `test_pf1_freeze_gates`: `__main__` is `unittest.main(verbosity=2)` only, no `--witnesses` command; its 13 witness clauses are exactly the 13 clauses `TestPf1FreezeGates` checks green in the same file, gated by `checks.d/pf1-l1-freeze-gates.txt`.
- `walk_mutation.py` generates mutants and has no runner; `test_pipeline.py --mutant` is invoked by no runner in `tests/` or `checks.d/`.

## Q3: baseline against what the mutant runs

Beyond finding 6 (union baseline vs one method alone, and flakes, recorded in the docstring and the fragment) and NIT 2 above, each new baseline matches its mutant's selection:
rehearsals runs the whole file as each `--mutant` child does;
gemini_adapter builds both module shapes `run_mutant` builds;
codex_usage_source builds each `where` with `_modules(where, ())`, so a mutated `tc` is also the `ca`'s `tc` as in the mutant;
codex_patch_reads builds each target file with `mutant(rel, ())`;
codex_started_file_change builds `mutant(())`;
codex_agents_off and vendor_bookkeeping run the same `CHECKS` on the unpatched modules;
endstate's controls are the same test files the witnesses run under.
Every new baseline checks all of its runner's checks, not just the bound one, which can only refuse more, never credit more.

## Q4: nothing weakened

The fold deletes only: the two fragment reasons (rewritten), the docstring paragraph on in-process sweeps (rewritten), two `require_no_lines(..., <lines>)` calls replaced by `require_clean(..., <callable>)` (the same lines, now also catching a raise), the test file's first docstring line, and the `WITNESS_RUNNERS` line that gains `_all("test_rehearsals")`.
No check, threshold or expected verdict changed.
Real witness counts are unchanged (Q1).
One process ran test_mutation_baseline, test_codex_agents_off, test_codex_patch_reads, test_codex_started_file_change, test_vendor_bookkeeping, test_codex_usage_source, test_native_snapshot, test_ci_job and test_build_draft: `mini: 164 run, 0 failures, 0 errors, 0 skipped`.
`test_round4.module_problems()` returns `[]`.
`evals/gap-study-4/copy_manifest.py --check` at the head: `ok: 794 files from 85 fragment(s)`, exit 0.
The round-1 review file is unchanged between e205a256 and the head.

## Q5: red first

On a `git archive` of fcf3401d (`evals/` whole) with the head's `test_mutation_baseline.py` copied in: `Ran 22 tests ... FAILED (failures=13, errors=2)`.
The lane's reds, each for the right reason:
the two errors are the probe's `RuntimeError: t104: a check that raises on the unmutated code` escaping as a traceback (finding 7);
eight T104Round2 failures show each runner returning a result over a red baseline instead of `BaselineRed` (agents_off's witness list with `key-dropped table True`, patch_reads, started_file_change, usage_source `returned 0`, endstate `returned 1`, gemini sweep returning a dict, native_snapshot `returned 1` after `red codex-root-empty`, vendor_bookkeeping);
two `runner='test_rehearsals'` subtests fail because no baseline ran.
The other three are environment reds (finding 1).
At the head in the worktree: `Ran 22 tests ... OK`.

## Not run

- No full `--witnesses` run of test_rehearsals (9 children at about 65 s each), test_endstate or the review_kit, and no full generated sweep; the baselines were exercised directly and through one-mutant shards.
  Full sweeps belong on athena.
- Nothing on athena, freeze/r4-20261021 or the rehearsal-records clone was touched.
