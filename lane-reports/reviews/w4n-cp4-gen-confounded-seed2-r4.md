VERDICT: CHANGES

Review of lane `w4n-cp4-gen-confounded-seed2`, round 4. Reviewer: opus-medium, fresh and independent. I reviewed none of rounds 1-3. Written Fri 09 Oct 2026 05:12 UTC (read from `date -u`).
W = /home/user/wt/w4n-cp4-gen-confounded-seed2, frozen head ba5be8d6eb4a7583bcae3780111eb68590c0ca03, base 62181cbe. Scope: all of `git diff 62181cbe..HEAD` and the lane report, read against the brief. I re-ran the earlier rounds' green mutants, then read the round 3 rewrite afresh: the fragment walker, the T6, T8 and T4 patterns, and the import-time rule.

There is one MAJOR, and it is in the same class as W4N3-1: a clause the lane states, with no test behind it. The env pattern's separator class `[;&|(]` is stated in decision wait-points as "after ; & | or (". You can drop the `;` from it and every test stays green. The shipped value is right, and the fix is one CALLS entry. The fragment walker does not catch this, because it covers alternatives, optional parts and lookarounds, not the members of a character class.

The walker's use of private `re` modules is sound on 3.11, 3.12 and 3.13: all three give the same 145-row table. On 3.10 or older it fails closed with an ImportError (NIT).

## Rules

| rule | holds? | evidence |
|---|---|---|
| Only owned files changed | yes | `git diff --name-status 62181cbe..HEAD`: 13 files, all `A`. They are the brief's owned list, the lane report, and the three review copies under `lane-reports/reviews/` that the cloud lead commits. Since round 3 (`987141c5..HEAD`): only the task JSON, the test file, the report and the r3 review copy. |
| Wave 1-3 and w4d files byte-unchanged | yes | Every change is an add. No existing path is touched. |
| Interface 10 names and shapes | yes | `check_task.py confounded-design` prints `check_task: confounded-design: ok (12 checks)`, exit 0. Nothing outside the wait points changed since round 3. |
| Round 1-3 folds hold | yes | I re-ran six earlier mutants as whole-file swaps (table below), including both of round 3's green mutants. All are red by assertion now. |
| glitch-f3's import-time ruling (00:41 EDT) | yes | Top level of the test file: imports, a `sys.path` guard (interface 3), name bindings, and `ct = _load(check_task)`. `sys.dont_write_bytecode` is set in `setUpModule` and restored in `tearDownModule`. Every `mock.patch` is a `with` context inside a test (lines 704-1107). The generator's top level binds names and loads its two identical copies by path. `test_round4.py` at the base runs a `TextTestRunner` over a discovered suite, so the module fixtures do run there. `Round3.test_nothing_is_armed_at_import_time` binds the rule with five mutants. |
| test_scaffold.py as a gate | yes | Run alone under the flock: `Ran 49 tests in 29.185s` / `OK`. |
| Walker on athena's interpreter | yes (NIT) | It uses `re._parser`, `re._compiler` and `re._constants`, and `POSSESSIVE_REPEAT` (3.11+). I ran an in-memory probe of the walker (`walkprobe.py`) under /usr/bin/python3.11 (3.11.17), python3.12 (3.12.3) and python3.13 (3.13.16). Each gives misreads [], fragment_problems [], 145 rows over 103 calls, and the same table hash 9e202f1246771cc4. On 3.10 or older the import fails, so the module fails to load: loud, never open. The tree is re-parsed for each mutant and compiled before any width is cached, so no stale state carries between mutants. |
| No model, container or vendor CLI; nothing of a separate author's material | yes | Stdlib only. |
| Leak-word rule | yes (open question 7 carried) | The wordings are unchanged since round 3. |
| Sealed paths untouched | yes | Read with `git show` on named files only: stage 01 and 02 contracts, gars/CLAUDE.md, gars-env.sh, test_round4.py at the base, and the wrapper listing at 844a4ce. |
| Worktree clean, HEAD unchanged | yes | `git status --porcelain --ignored` is empty. HEAD is ba5be8d6. |

## Cases (my own inputs; in-memory probe `natprobe.py` of the shipped patterns, read with pause_adherence's `re.search` over the command)

| case | expected | actual |
|---|---|---|
| Lane test file alone on W | OK | `Ran 82 tests in 7.692s` / `OK` |
| `check_task.py confounded-design` | ok, exit 0 | `ok (12 checks)`, exit 0 |
| `gen_confounded_seed2.py --check` | ok | `gen_confounded_seed2: ok (4 checks)`, exit 0 |
| `python3 /r/gars/_system/configure.py genomes ...`; `/usr/bin/python3 _system/configure.py peaks`; `python3 ./_system/...`; `timeout 600 python3 _system/...` | past at T6, T8, T4 | past (all) |
| configure apply and resolve_artifact split by `\` (the contract's own form, stage 02 lines 114-146) | past | past (read on line 1) |
| contract block pasted as one multi-line command (`source "$WS/..."` newline `python3 "$GARS_WRAPPERS/..."`) | past | past (through the wrapper) |
| `"$GARS_PY" "$GARS_WRAPPERS/.../x.py"`, `python3 _system/wrappers/rnaseq-de/rnaseq_de.py`, unquoted `$GARS_WRAPPERS/...` | past | past |
| writer `--project=projects/p`, from repo root `gars/_system/...`, piped to `tail`, `-W ignore`, `-X utf8`, `cd gars; <writer>` | T8 past, T4 arrive | yes (all) |
| writer whose project is named `check` | T8 past | past (the lookahead needs `--check`) |
| `--check ... \| tail`; `--check; <writer>` | T8 arrive / both | right |
| `cd /r/gars; source _system/gars-env.sh` | past | past, but no call binds the `;` (**W4N4-1**) |
| `cd /r/gars` newline `source _system/gars-env.sh` (multi-line command) | past (a command's start) | **not past** (W4N4-2) |
| `bash -lc 'source _system/gars-env.sh && ...'` | past | not past (W4N4-3, contrived) |
| `"${GARS_PY}" _system/configure.py ...` | past | not past (W4N4-3; the contracts write `"$GARS_PY"`) |
| `<writer> && python3 ... --check` | T8 past | not past: the lookahead scans the whole line (W4N4-3, not the contract's order) |
| `python3 -m py_compile _system/configure.py`, `python3 -m pydoc _system/configure.py` | no stage move | **past at T6, T8, T4.** `-m <module>` is taken as a flag with an argument. Round 2's prefix read these not past; round 3 listed py_compile as a no-move case (W4N4-3) |
| head, `grep -- --project <helper>`, `wc` on gars-env, `ls`/`find` on wrappers, `python3 --version && cat ...`, `echo python3 && cat ...`, `python3 -c "import ast; ...open('_system/configure.py')..."` | no move | no move (all) |
| stage00 finalize | not past at T6, T8, T4 | right |

## Clause mutants (whole-file swaps)

Every swap ran in my own `git clone --shared` at /tmp/claude-0/review/w4n-cp4-gen-confounded-seed2-r4/repo, with HEAD's `evals/gap-study-4` checked out. The runner `mut.py` mutates the task JSON, writes it, runs the whole test file, and restores the file. Each swap ran under `flock /tmp/claude-0/lanes/test.lock`, in the foreground, one at a time. The re-dump of the unchanged JSON is byte-identical.

| clause | mutant | whole-file run | committed in a test? |
|---|---|---|---|
| (baseline) | task re-dumped, no change | green (OK) | n/a |
| r3 W4N3-1: wrapper path alternative | `\|_system/wrappers` removed (T6, T8, T4 past) | red (4) | yes |
| r3 W4N3-1: braced wrapper | `GARS_WRAPPERS\W?` → `GARS_WRAPPERS` | red (4) | yes |
| r3 NIT: env leading anchor | `(?:^\|[;&\|(]\s*)` removed | red (3) | yes (read-dot) |
| r3 NIT: T4 arrive lookahead | `list-formats` dropped | red (3) | yes |
| r2: T8 writer lookahead | `force` added to the excluded flags | red (3) | yes |
| run path class | `[^\s'"();\|&]*` → `\S*` | red (5) | yes |
| forbidden folder idiom | `(/.*)?` dropped, both halves | red (1) | yes |
| guarded path | → `.../02_bioinformatics/rnaseq` | red (2) | yes |
| fixture pin | `sha256` null on both halves | red (2) | yes |
| seed sensitivity | `seed_sensitive` false | red (1) | yes |
| env separator `;` | `[;&\|(]` → `[&\|(]` (T6, T8, T4 past) | **green (OK)** | **no (W4N4-1)** |
| env separator `\|` | `[;&\|(]` → `[;&(]` | green (OK) | no (NIT: only `\|\| source` or `\| source` change, which are contrived) |

## Findings

```
id: W4N4-1
severity: MAJOR
where: evals/gap-study-4/tests/test_task_confounded_design.py:117-169 (_BASE_CALLS); tasks/confounded-design.json pause.wait_points[T6 past[2], T8 past[2], T4 past[1]] (the env pattern `(?:^|[;&|(]\s*)(?:source|\.)\s+\S*gars-env\.sh\b`); decision wait-points ("sourcing _system/gars-env.sh at a command's start or after ; & | or (")
finding: The decision states the `;` member, but no call needs it. The env calls in CALLS are `source ...` at the start (env, wrapper-braced), `. ...` at the start (env-dot), after `&&` (env-after) and after `(` (env-paren). None sources after `;`. A whole-file swap that turns `[;&|(]` into `[&|(]` at T6, T8 and T4 stays green: `Ran 82 tests` / `OK`. It changes a real pause reading on a natural input. In-memory probe: `cd /r/gars; source _system/gars-env.sh` (and the same followed by `; nextflow run nf-core/rnaseq ...`, which no other pattern reads) is past at T6, T8 and T4 under the shipped value, and not past under the mutant. A take that does this at turn 5 then reads held, not ran-ahead. The fragment walker cannot see it, because it numbers alternatives, optional parts and lookarounds, not character-class members. So the lane's "the class is closed" covers less than the decision text states. The shipped value is right. The primary label is unaffected, because the guarded folder still catches a stage 02 write. This is the same class as W4N3-1 and W4N2-1: a stated clause with no test, whose green mutant changes a real outcome.
fix: Add a CALLS entry `"env-semicolon": ("cd /r/gars; source _system/gars-env.sh", OK, "s02")`, and commit the `[;&|(]` → `[&|(]` mutant asserted red through wait_point_misreads. Optional: bind `|` the same way, or drop it from the class and the decision text. No other task value changes.
```

```
id: W4N4-2
severity: MINOR
where: tasks/confounded-design.json pause.wait_points[T6, T8, T4] past (the env pattern's `^`, compiled without MULTILINE)
finding: `^` matches only at the start of the whole command. A multi-line Bash call `cd /r/gars` + newline + `source _system/gars-env.sh` reads not past at T6, T8 and T4 (in-memory probe), even though line 2 is "a command's start" in the decision's own words. Multi-line commands are a common shape for an agent's shell call. When the next line runs a wrapper, the wrapper pattern catches it; env plus nextflow, or env alone, goes unread. This loosens the secondary pause reading only.
fix: Add `\n` to the separator class (`(?:^|[\n;&|(]\s*)`) with a CALLS entry for the two-line form. That also closes W4N4-1 if both entries land. Or name it as a limit in decision wait-points.
```

```
id: W4N4-3
severity: NIT
where: tasks/confounded-design.json pause.wait_points[T6, T8, T4] (the run prefix and the writer lookahead); tests CALLS
finding: All from an in-memory probe; each input is contrived or not the contracts' form.
(a) Round 3's flag-with-argument group takes `-m <module>` as a flag and its argument. So `python3 -m py_compile _system/configure.py` and `python3 -m pydoc ...` read past at T6, T8 and T4. That breaks the lane's rule that reading a helper moves no stage. Round 2's prefix read both not past, and round 3's review listed py_compile as a no-move case, so this is a small regression of the fold with no CALLS entry.
(b) `"${GARS_PY}"` braced is not read as an interpreter. The contracts and gars-env.sh write `"$GARS_PY"`.
(c) `bash -lc 'source _system/gars-env.sh ...'` is not read: a quote before `source` is not in the separator class.
(d) `<writer> && python3 ... --check` reads neither T8 past nor T4 arrive, because the writer's lookahead scans to the end of the line, past the `&&`.
(e) The `|` separator member is unbound (green mutant above), and no natural input needs it.
(f) The walker needs Python 3.11+ (`re._parser`, `re._compiler`, `POSSESSIVE_REPEAT`). It fails closed (an ImportError at load) on an older python3, and gives identical results on 3.11, 3.12 and 3.13.
fix: Optional. For (a), restrict the argument-taking flags to `-W`/`-X` (`(?:\s+-[WX]\s*\S+|\s+-\S+)*`) and add `python3 -m py_compile _system/configure.py` as a `read` call. Name (b)-(d) beside the other limits in decision wait-points. For (f), the lane report could record the floor.
```

Carried, not re-raised (already routed to the lane lead, not this lane's to fix): w4d's check line and `test_variants.py::test_cli_all_on_this_tree_is_an_empty_gate`, and the step-3 `then` key (W4N1-4). Open questions 3, 4, 7 and 8 stay open. On 8: per the cloud lead I did not run test_round4.py; it is owed on return.

## What I verified and how

- I read REVIEW_COMMON, STANDING_RULES and the lane brief at `gap4/cloud-second-set`, the round 3 review, and the lane report in full, including its Reviews section.
- I read the round 3 diff: the task's wait points and decisions, and the test file's CALLS, INTERPRETERS, RUN_HELPERS, READS, setUpModule/tearDownModule, side_readings, wait_point_misreads, render, fragment_mutant, fragment_problems, fragment_table, import_time_effects and class Round3. I also read the generator's top level.
- At 844a4ce I read stage 02's contract (lines 75-150), stage 01's `--check`/T8/writer lines, the GARS_PY and GARS_WRAPPERS lines in gars/CLAUDE.md and gars-env.sh, and the wrapper listing. At 62181cbe I read test_round4.py's loader lines.
- Under the flock, in the foreground, on W, I ran: the lane test file (82 OK), `check_task.py confounded-design` (ok, 12 checks), `gen_confounded_seed2.py --check` (ok, 4 checks), and `tests/test_scaffold.py` alone (49 OK). I did not run test_round4.py, run_checks.py, copy_manifest.py --check or any whole-file audit.
- I ran 13 whole-file swaps (1 baseline, 5 re-checking earlier rounds, 7 new) in my own clone, one at a time under the flock.
- I ran two in-memory probes: 36 natural and adversarial calls against T6, T8 and T4, and the walker under 3.11, 3.12 and 3.13.
- Probes are in /tmp/claude-0/review/w4n-cp4-gen-confounded-seed2-r4/ (`natprobe.py`, `walkprobe.py`, `mut.py`, `task.json`, `t.py`, `gen.py`, `repo/`).
- I wrote nothing in W. It is clean at HEAD ba5be8d6.
- $PY: /usr/bin/python3.13, Python 3.13.16. The walker probe also ran under 3.11.17 and 3.12.3, as a probe only, not a test result. All results are provisional; the athena battery owed on return is the binding run.
