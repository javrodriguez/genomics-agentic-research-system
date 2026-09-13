# Review: task/security-minimal-fix (decision 0042)

## Header

- **Commits reviewed:** `fc4749a..869ab28` (one commit, `869ab28`), on branch `origin/task/security-minimal-fix`, in a separate clone with its origin removed.
- **Reviewer context:** an independent reviewer that had neither the producer's conversation nor its reasoning.
The governing record, the diff, decision 0022, both CLAUDE.md files, every stage contract and the test suite were read in this clone.
- **Memory caveat: this review was NOT memory-blind.**
Glitch memory (MEMORY.md, the auto-memory index, USER.md) was loaded into the session and summarises GARS work in general.
None of it is used as evidence here.
Every finding cites a path:line in this clone or a command I ran, with its output.
- **Spec:** `docs/specs/GARS_Unified_Master_Guideline_v1.0.1_FINAL.md` does not exist in this clone (`ls docs/specs` → No such file or directory).
The change is judged against decision 0042, decision 0022, `CLAUDE.md`, `gars/CLAUDE.md` and the stage 03 contract.
- **Runtime:** macOS, Python 3.13.2.
No Python 3.6.8 interpreter exists on this machine (`which python3.6` → none), so 3.6 compatibility was checked by grammar and by API reading, not by running it.
- **Probe tooling (outside C, not shipped):** `/Users/javrodher/glitch/_local/eval-scratch/gars-fix-review-probe/probe.py` (the hook probes; `HOOK=` selects the hook under test) and `stage03_probe.py` (the approval binding).
The mutant copy was deleted after use.

## Verdict

**APPROVE WITH CHANGES.**

The change is a strict improvement on `fc4749a`.
Every probe that is now denied was allowed at the baseline (the same probe set run against `git show fc4749a:gars/_system/guard_hook.py`).
**No contract-instructed step is denied**: the 44-shape sweep below is all exit 0.
So there is no BLOCKER.

Two findings are MAJOR because the prose claims more than the code does, and on a public security boundary that is the failure a reader cannot see:

1. The inline-interpreter closure can be bypassed *within the interpreters it names* (`python3 -Ic`, `node --eval`, a heredoc on stdin, `"$GARS_PY" -c`), and 0042's "What this does not close" list does not mention these.
2. A write whose destination is a directory (`cp x _system/`, `chmod -R a+w _system`, `cp forged/PLAN.md.approved <analysis dir>/`) escapes every target check, including the new approval-record deny that 0042:49 says covers "any Bash write target".

Required before merge: either close the cheap shapes in MAJ-1 and MAJ-2, or state them in 0042's "What this does not close" and correct the overclaiming sentences.
The MINOR items can follow in the row 4 work.

## Findings

### BLOCKER

None.
Every contract-instructed shape I could enumerate is allowed (see the false-positive sweep table).

### MAJOR

**MAJ-1: The inline-interpreter closure can be bypassed within its own named interpreters, and these residuals are not stated.**

- **Claim.** 0042:39–41: "A write the scanner cannot see is refused when it names a protected path. … `python*`/`perl`/`ruby`/`node`/`Rscript`/`R` with inline code … refused if any of its arguments names `_system/` …".
The docstring at `gars/_system/guard_hook.py:22-26` says the same, without the flag list.
The commit message says "inline interpreter code (python -c, perl -e, Rscript -e, ruby/node -e)" is refused.
- **What I found.** The check fires only on an exact spelling:
  - Python needs the exact token `-c` in its flags (`guard_hook.py:161-162`).
  - Long flags are dropped before the check (`guard_hook.py:156`, `not a.startswith("--")`).
  - Only the interpreter's own argv is inspected, so code fed on stdin is invisible.
  - The interpreter is recognised by basename only (`guard_hook.py:145-148`), so the contracts' own interpreter variable is invisible.

  Each of these writes-into-`_system/` shapes exits 0:

  | Shape | Hook exit (869ab28) |
  |---|---|
  | `python3 -Ic "open('_system/x.py','w')"` (grouped flag; `python3 -Ic "print(...)"` runs, verified) | 0 |
  | `python3 -Bc "open('_system/x.py','w')"` | 0 |
  | `"$GARS_PY" -c "open('_system/x.py','w')"` (`$GARS_PY` is the documented interpreter, `gars/02_bioinformatics/CONTEXT.md:90`) | 0 |
  | `py -c "…_system/…"` (the Windows launcher; Windows is a stated first-class target) | 0 |
  | `node --eval "require('fs').writeFileSync('_system/x','')"` / `node -p …` | 0 |
  | `python3 - <<'EOF'` + `open('_system/x.py','w')` (a heredoc on stdin, the common agent idiom) | 0 |
  | `echo "open('_system/x.py','w')" \| python3` | 0 |
  | `bash <<< 'echo x > _system/y.py'` / `echo '…' \| bash` | 0 |
  | `eval 'echo x > _system/y.py'` | 0 |
  | `ksh -c '…'`, `tcsh -c '…'` (`SHELLS` is `bash, sh, zsh, dash`, `guard_hook.py:64`) | 0 |
  | `sbatch --wrap='echo x > _system/y.py'` (sbatch is an instructed tool) | 0 |
  | `awk 'BEGIN{print "x" > "_system/y.py"}'` | 0 |
  | `find _system -name guard_hook.py -exec touch {} +` | 0 |

  0042:56 lists as not closed only "a script file … then executed, command substitution, or decoded payloads".
  Grouped flags, long flags, stdin, heredocs, here-strings, `eval`, other shells, `--wrap`, `awk` and variable-named interpreters are not in that list.
  They are not decoded payloads or command substitution.
  Obfuscated literals (`'_sys'+'tem/'`, `os.path.join('_system','x')`) also pass; that one arguably falls under "decoded payloads", but it is not said.
- **Evidence.** `python3 …/gars-fix-review-probe/probe.py bypass` (output in the bypass table below); `python3 -Ic "print('grouped -Ic runs inline code')"` → prints.
- **Recommended change.**
  - At minimum, extend 0042's "What this does not close" to name each residual shape above, and soften `guard_hook.py:22-26` and 0042:39 from "is refused" to "the listed spellings are refused".
  - Cheap closures that keep the false-positive criterion:
    - Treat any single-dash flag group containing `c` as inline for Python.
    - Treat `--eval`/`--print`/`-p` as inline for node.
    - Treat an interpreter or shell token with no script-file operand, or fed by `<<`, `<<<` or `|`, as inline.
    - Resolve `$VAR` interpreter tokens conservatively.
  - The durable fix is the direction 0042 already names (R-092, a typed tool surface): allow-list the instructed shapes rather than enumerate bypass spellings, because each enumerated list leaves the next spelling.

**MAJ-2: A directory destination escapes every target check, including the new approval-record deny.**

- **Claim.** 0042:42: "`dd of=`, `ln`, `install`, `touch`, `truncate`, `chmod`, `chown` join the target scan".
0042:49: "The guard denies writing `projects/*/03_custom_analysis/*/PLAN.md.approved` by Write/Edit **and by any Bash write target**."
- **What I found.** `rel_to_root` normalises `_system/` and `_system` to `_system` (`guard_hook.py:91`, `os.path.normpath`).
The protection test is `rel.startswith("_system/")` (`guard_hook.py:311-312`), so a bare or trailing-slash directory never matches.
The record deny checks `basename(rel) == "PLAN.md.approved"` (`guard_hook.py:316`), so a directory destination never matches either.
The `tee` scan stops at the first flag (`guard_hook.py:191-192`), so `tee -a` has no targets.

  | Shape | Hook exit (869ab28) |
  |---|---|
  | `cp /tmp/forge/PLAN.md.approved projects/p/03_custom_analysis/01_x/` | 0 |
  | `mv PLAN.md.approved projects/p/03_custom_analysis/01_x` | 0 |
  | `echo '{}' \| tee -a projects/p/03_custom_analysis/01_x/PLAN.md.approved` | 0 |
  | `chmod -R a+w _system` (new verb, bare dir) | 0 |
  | `ln -s /tmp/evil.py _system` (new verb, dir destination) | 0 |
  | `cp evil.py _system/` | 0 |
  | `rm -rf _system` (pre-existing since 0022) | 0 |
  | `mv evil.md _references` (pre-existing) | 0 |

  The `rm -rf _system` and `cp … _system/` gaps pre-date this change (both exit 0 at `fc4749a` too).
  The record-directory copy, `tee -a` on the record, and the new verbs with a directory operand are gaps in what *this* change claims.
- **Evidence.** `probe.py bypass` rows "cp into analysis dir (dir target)", "mv tmp to record via dir", "tee -a record", "chmod -R a+w _system (bare dir)", "ln -s evil into _system dir", "touch _system/ (trailing slash dir)".
- **Recommended change.**
  - Treat a resolved target equal to a protected directory name (`rel in ("_system", "_references", "_templates", ".claude")`) as protected.
  - For `cp`/`mv`/`ln`/`install`, also test `destination + "/" + basename(source)` against the record name.
  - Let `tee` skip its flags rather than stop on them.
  - Add the rows above to `test_denies_writes_the_scan_could_not_see`.
  - If this is deferred, 0042:49 must say "by a Bash write target naming the file", and the gap must be listed.

### MINOR

**MIN-1: Two crash paths still exit 1, which Claude Code treats as a non-blocking error (the call proceeds).**

- **Claim.** 0042:38: "A hook that crashes must not become a hook that allows."
- **What I found.** Only the checks are inside `try` (`guard_hook.py:339-348`).
  - Parsing catches only `ValueError` (`guard_hook.py:328-331`). A deeply nested JSON payload raises `RecursionError` → traceback → exit 1.
  - `workspace_root()` (`guard_hook.py:337`, which calls `os.getcwd()` when `CLAUDE_PROJECT_DIR` is unset) sits outside the `try`. Run from a deleted cwd, it raises `FileNotFoundError` → exit 1.

  The docstring's own contract (`guard_hook.py:9`) is "Exit 2 blocks it", so exit 1 does not block.
  Both need a malformed harness payload or environment, so they are unlikely to be agent-reachable.
- **Evidence.** `probe.py raw` → `exit=1 | deeply nested JSON (RecursionError) | Traceback`; `probe.py env` → `exit=1 | hook run with no CLAUDE_PROJECT_DIR from a deleted cwd | FileNotFoundError`.
- **Recommended change.** Wrap the whole of `main()` in `except BaseException` that re-raises `SystemExit` and otherwise denies.

**MIN-2: The new scans deny reads that were allowed before (the pre-existing "verb anywhere" class, widened).**

- **Claim.** Decision 0022, "The line that keeps this safe": "This is why the hook does not try to restrict *reads*".
0042:36: "Decision 0022's stance is unchanged".
- **What I found.** `bash_write_targets` treats `touch`/`chmod`/`install`/… as a verb wherever the word appears (`guard_hook.py:229-247`), not only in command position.
The inline check denies on any mention of a protected path, reads included (`guard_hook.py:298`).
Each of these read-only commands was exit 0 at `fc4749a` and is exit 2 now:
  - `grep -n touch _system/workspace.py _system/stage00_register.py`
  - `grep chmod _system/stage00_register.py`
  - `grep -n install _references/environment.md _references/assay_stage_skill_map.md`
  - `python3 -c "print(open('_references/VERSION').read())"`
  - an unparseable `grep … _system/guard_hook.py '`

  None is contract-instructed, so this is not a BLOCKER.
  But the bounded-voice rule (`gars/CLAUDE.md:20-22`) lets the agent answer from `_references/` read-only, and grep is a natural way to do it.
  0042's own inline-code denial of reads is stated (0042:41); the grep denials are not.
- **Evidence.** `probe.py reads` against both hooks (0/0/0/0/0/0 at `fc4749a`; 2/2/2/2/0/2 at `869ab28`).
- **Recommended change.** Only treat these words as verbs in command position (the first token, or the first after a separator), and state in 0042 that an inline read naming a protected path is refused.

**MIN-3: Two mutations survive the new tests.**

- **Claim.** 0042 "Test": the tests pin the change.
The commit message says "chmod and chown join the scan".
- **What I found.**
  - Mutation M1 removed the `tool_input`-is-an-object check (`guard_hook.py:332`). `test_unreadable_call_is_refused` stays green, because the string `tool_input` then crashes in `check_bash` (`AttributeError: 'str' object has no attribute 'get'`) and the crash handler denies. The test cannot tell the intended path from the fallback.
  - Mutation M3 removed `chmod`/`chown` from the operand scan (`guard_hook.py:239`). All five guard tests stay green, because no test covers `chmod`, `chown`, `truncate` or `install` as a target.
  - No test pins `approve`'s `already_approved` idempotency (`stage03_analysis.py:231-236`). It does hold: see probe A.
- **Evidence.** The mutation log below (M1, M3: `Ran 5 tests … OK`); the M1 stderr shows the `AttributeError` path.
- **Recommended change.**
  - Assert the UNREADABLE message text (not only "Blocked") for a non-object `tool_input`.
  - Add `chmod 644 _system/x`, `chown u _references/x`, `truncate -s 0 _system/x` and `install x _system/y` to the deny test.
  - Add a second-`approve` assertion to `test_12d`.

**MIN-4: An edit after approval can be laundered by reverting the stamp and re-running `approve`; the record is silently overwritten.**

- **Claim.** `gars/03_custom_analysis/CONTEXT.md:61-62`: "`verify` refuses a plan that was edited after approval".
The `stage03_analysis.py:19-21` docstring says the same.
- **What I found.** Approve, then edit the Method and turn `Status: APPROVED …` back into `Status: DRAFT` (an Edit the guard allows on PLAN.md).
`approve` then exits 0 and overwrites `PLAN.md.approved` with the new hash (`stage03_analysis.py:302`, no existing-record check), and `verify` exits 0.
In substance this is 0042:55's listed residual ("the agent can still run `approve` itself").
But the record's existence is exactly the evidence of a prior approval, and `approve` destroys it.
- **Evidence.** `stage03_probe.py` section E: `re-approve: 0 … | record overwritten: True` then `verify: 0`.
- **Recommended change.** `approve` refuses when `PLAN.md.approved` already exists and the plan carries no stamp.
A changed mind is `create` (the contract's own rule, CONTEXT.md:39-40).
Also scope the CONTEXT.md sentence to "unless `approve` is run again".

**MIN-5: `approve` detects the stamp by substring, so plan prose containing "Status: APPROVED" is refused with a forgery message.**

- **What I found.** `approve` tests `"Status: APPROVED" in text` (`stage03_analysis.py:231`), while `verify` uses the anchored `^Status: APPROVED( .*)?$` (`stage03_analysis.py:322`).
A DRAFT plan whose Method says "Filter rows whose Status: APPROVED flag is set." is refused with "either this stamp was not written by `approve` or the plan changed after approval".
The substring check pre-dates this change, but it used to return `already_approved` (a silent wrong success).
It now yields a wrong accusation that the T3 template relays to the user.
- **Evidence.** `stage03_probe.py` section F: `approve: 2 {'error': 'PLAN.md carries an approval stamp, but there is no PLAN.md.approved …'}`.
- **Recommended change.** Use the same anchored regex in `approve`.

**MIN-6: An unreadable record makes `verify` crash with exit 1, which the contract reads as "outputs missing".**

- **What I found.** `approval_holds` catches `ValueError`, `KeyError` and `TypeError` (`stage03_analysis.py:204-207`), but not `OSError`.
A record at mode 000 raises `PermissionError` out of `verify`.
Contract step 9 maps `verify` exit 1 to "declared outputs are missing or empty: write STATUS as FAILED" (`gars/03_custom_analysis/CONTEXT.md:115-116`), which misreports the cause.
- **Evidence.** `stage03_probe.py` section H: `verify (unreadable record, mode 000) raised: PermissionError`.
- **Recommended change.** Catch `OSError` in `approval_holds` and return `(False, "… is unreadable")` (exit 2).

**MIN-7: The decision record's Test section overclaims.**

- **Claim.** 0042:61: "each red at `fc4749a` and green at this change", listing `test_allows_after_hardening` (0042:65).
- **What I found.** With the whole hook at `fc4749a` (mutation M5), `test_allows_after_hardening` passes: only `test_unreadable_call_is_refused` and `test_denies_writes_the_scan_could_not_see` fail.
The commit message says this correctly ("passes on both, as a regression guard"); the record does not.
- **Evidence.** Mutation log M5.
- **Recommended change.** Reword 0042:61 to match the commit message.

**MIN-8: The record describes the Bash scan as covering redirections, but several redirection spellings and `cd` are unscanned, and none are listed as residuals.**

- **Claim.** 0042:25: "The Bash target scan covers redirections, `tee`, `rm`, `mv`, `cp` and `sed -i`."
- **What I found.** Each of these exits 0, at `fc4749a` and at `869ab28`:
  - `echo x>_system/y.py` (no space: one shlex token)
  - `echo x >| _system/y.py`
  - `echo x 1>> _system/y.py`
  - `echo x | tee -a _system/y.py`
  - `cd _system && echo x > guard_hook.py` (cwd is not modelled)

  They are pre-existing, not introduced, but they sit in the scanner this record hardens and describes.
- **Evidence.** `probe.py bypass` rows "redirect …", "tee -a", "cd then write".
- **Recommended change.** List them under "What this does not close", or fix the tokenizer (`shlex.shlex(punctuation_chars=True)` exists since 3.6).

### NOTE

- **N-1: Falsy non-object `tool_input` or `command` is allowed.**
`{"tool_input": ""}`, `{"tool_input": 0}` and `{"command": 0}` exit 0 because `or {}` / `or ""` coerce them (`guard_hook.py:258, 332, 335`).
This is harmless (there is nothing to run), but 0042:38 reads as "a `tool_input` that is not an object → exit 2".
- **N-2: Cross-OS newline handling holds.**
`approve` hashes the bytes on disk after `atomic_open(…, newline=None)` has done its translation (`stage03_analysis.py:286-296`), and `verify` hashes `read_bytes()` (`stage03_analysis.py:208`).
With `atomic_open` forced to CRLF (simulating Windows), `approve` then `verify` both exit 0 (probe B).
A byte-normalising transfer between approve and verify (CRLF→LF) is refused as "changed after approval" (probe C).
That is the safe direction, but the message will mislead someone who moved a project between Windows and the cluster.
- **N-3: The crash window between stamp and record behaves as documented.**
With a fault injected after the stamp, the plan is stamped and has no record.
`approve` again → exit 2, `verify` → exit 2 (probe D), and the recovery is `create`, as 0042:51 and the comment at `stage03_analysis.py:288-290` say.
The refusal text names only forgery or an edit; a crash could be named too.
- **N-4: `approve` idempotency holds.**
A second `approve` on an intact approval returns `already_approved`, and the record is byte-unchanged (probe A).
- **N-5: Python 3.6.**
`ast.parse(…, feature_version=(3,6))` accepts both changed helpers.
No stdlib use newer than 3.6 was found: `getpass.getuser`, `hashlib.sha256`, `Path.read_bytes` (3.5) and `json.loads` on `str` are all fine.
Not executed on 3.6.8 (no interpreter available).
- **N-6: `PLAN.md.approved` is written at mode 0644** (`stage03_analysis.py:302`, no `mode=`).
Machine-owned files elsewhere use `MACHINE_OWNED_MODE` (decision 0018).
0444 would add the filesystem layer to the guard deny.
- **N-7: The WorkspaceFixture stage 03 tests depend on test order.**
`test_12a`, `12c` and `12d` fail when run alone ("no such project: projects/tall-test") and pass as part of the class.
This is the fixture's existing pattern; the brief's command, which runs the whole class, is green.
- **N-8: Scope is clean.**
The diff touches exactly `guard_hook.py`, `stage03_analysis.py`, the stage 03 CONTEXT.md, `tests/run_tests.py`, decision 0042 and its index row, and the 113→118 counts in README.md and DEVELOPMENT.md.
The runner reports 118 and `check_counts.py` is clean.
- **N-9: 0042:41's grep claim holds.**
"No contract runs inline interpreter code" is confirmed: `grep -rnE "python3? -c|Rscript -e|perl -e|bash -c|sh -c|node -e"` over `gars/` (md/sh/py/yaml, excluding projects) matches only the docstring at `guard_hook.py:141-142`.

## False-positive sweep (contract-instructed shapes, expect exit 0)

The hook ran with `CLAUDE_PROJECT_DIR=C/gars` and `cwd` set to `C/gars`.
Shapes come from every `CONTEXT.md` under `gars/` (backticked and fenced commands), `gars/CLAUDE.md` and `CLAUDE.md`.

| Command shape | Contract source | Hook exit |
|---|---|---|
| `python3 _system/stage00_register.py assays` | 00 CONTEXT.md:173 | 0 |
| `… assays --select "01 03"` | 00 CONTEXT.md:183 | 0 |
| `… create --title "T-ALL Leukemia's cohort" --assays rnaseq_bulk atacseq_bulk` | 00 CONTEXT.md:194 | 0 |
| `… inspect --assay rnaseq_bulk --source /gpfs/…` | 00 CONTEXT.md:209 | 0 |
| `… link --project projects/p --assay rnaseq_bulk --source /gpfs/…` | 00 CONTEXT.md:221 | 0 |
| `… finalize --project projects/p --model "claude-opus-5"` | 00 CONTEXT.md:233 | 0 |
| `sbatch projects/p/00_data/check.sh` (full check over ~10 GB) | 00 CONTEXT.md:112 | 0 |
| `python3 _system/stage01_samplesheet.py --list-formats` | 01 CONTEXT.md:95 | 0 |
| `… --project projects/p --check` | 01 CONTEXT.md:177 | 0 |
| `… --project projects/p --model "…" --confirm-exclusions --force` | 01 CONTEXT.md:198 | 0 |
| `source "$WS/_system/gars-env.sh"` | 02 CONTEXT.md:95 | 0 |
| `source … && python3 "$GARS_WRAPPERS/…/nfcore_atacseq_wrapper.py" check …` | 02 CONTEXT.md:95-96 | 0 |
| `python3 _system/configure.py genomes --assay …` / `contrasts …` / `peaks` | 02 CONTEXT.md:114-116 | 0 / 0 / 0 |
| `python3 _system/configure.py apply … \` + continuation line | 02 CONTEXT.md:123 | 0 |
| `python3 _system/resolve_artifact.py … \` + continuation line | 02 CONTEXT.md:146 | 0 |
| `python3 "${GARS_WRAPPERS:-_system/wrappers}"/nfcore-rnaseq-wrapper/… prepare \` … | 02.01 rnaseq CONTEXT.md:49 | 0 |
| `python3 "${GARS_WRAPPERS:-_system/wrappers}"/scrna-qc-cluster/… check …` | 02.02 scrna CONTEXT.md:50 | 0 |
| `python3 "${GARS_WRAPPERS:-_system/wrappers}"/spatial-cluster-count/… collect …` | 02.02 spatial CONTEXT.md:62 | 0 |
| `python3 <ws>/_system/executorlib.py submit --workspace projects/p …/submit.sh` | 02.01 rnaseq CONTEXT.md:95 | 0 |
| `python3 <ws>/_system/executorlib.py status --workspace projects/p 12345` | 02.01 rnaseq CONTEXT.md:137 | 0 |
| `sbatch projects/p/02_bioinformatics/scrnaseq/01_…/submit.sh` | 02.01 scrnaseq CONTEXT.md:121 | 0 |
| `squeue -j 12345; sacct -j 12345 --format=State` | `_references/environment.md:14` | 0 |
| `python3 _system/resolve_artifact.py --project projects/p --assay … --list` | 03 CONTEXT.md:84 | 0 |
| `python3 _system/stage03_analysis.py create --project projects/p --slug de-heatmap` | 03 CONTEXT.md:87 | 0 |
| `python3 _system/stage03_analysis.py approve --project projects/p --analysis 01_de-heatmap` | 03 CONTEXT.md:100 | 0 |
| `python3 <ws>/_system/executorlib.py submit --workspace projects/p …/scripts/run.sh` | 03 CONTEXT.md:105 | 0 |
| `python3 _system/stage03_analysis.py verify … --model "claude-opus-5[1m]"` | 03 CONTEXT.md:113 | 0 |
| `echo "FAILED 2026-09-13T10:00:00" > projects/p/03_custom_analysis/01_x/STATUS` | 03 CONTEXT.md:109 | 0 |
| Write `projects/p/03_custom_analysis/01_x/PLAN.md` (draft) | 03 CONTEXT.md:89, 96 | 0 |
| Write `projects/p/03_custom_analysis/01_x/scripts/run.py` | 03 CONTEXT.md:103 | 0 |
| `chmod +x projects/p/03_custom_analysis/01_x/scripts/run.sh` | 03 CONTEXT.md:103 (writing scripts) | 0 |
| `bash _system/build_projects_index.sh` / `… .` | `gars/CLAUDE.md` State table; `CLAUDE.md` Generated files | 0 / 0 |
| `bash _system/session_state.sh`; `python3 _system/project_state.py` | `gars/CLAUDE.md` State | 0 / 0 |
| `git pull && git checkout v0.10.0 && git describe --tags && git rev-parse HEAD && git diff` | `gars/CLAUDE.md` Using this workspace | 0 |
| `cat >> projects/p/HISTORY.md <<'EOF'` … `EOF` (append history_entry) | 03 CONTEXT.md:118 | 0 |
| `ln -s /gpfs/data/raw/S1_R1.fastq.gz projects/p/00_data/rnaseq_bulk/raw/` | 00 CONTEXT.md:394 (symlinks; done by `link`) | 0 |
| `mkdir -p …/results && touch …/results/.keep` | 03 CONTEXT.md:49 | 0 |
| `cat _references/artifact_types.md` | 03 CONTEXT.md:21 | 0 |
| `bash -lc 'source _system/gars-env.sh && "$GARS_PY" …/scripts/run.py'` (plausible) | 03 CONTEXT.md:24, 106 | 0 |
| `python3 _system/resolve_artifact.py … --list \| python3 -c "import json,sys; …"` (plausible) | 03 CONTEXT.md:84 | 0 |

Result: 44 of 44 shapes allowed.
The non-instructed read shapes that are now denied are listed under MIN-2.

## Attempted bypasses

"Closed by 0042?": **yes** = within what 0042 says is closed; **listed** = named in 0042's "What this does not close"; **no** = neither closed nor listed; **pre** = pre-existing and outside 0042's claims.
The `fc4749a` column is the same probe against the baseline hook.

| Shape | Closed by 0042? | Exit 869ab28 | Exit fc4749a |
|---|---|---|---|
| non-JSON stdin / empty stdin | yes | 2 / 2 | 0 / 0 |
| JSON array / string / null | yes | 2 / 2 / 2 | 1 / 1 / 1 |
| `tool_input` string / list | yes | 2 / 2 | 1 / 1 |
| `tool_input` `""` / `0` (falsy) | yes (N-1) | 0 / 0 | 0 / 0 |
| `command` as a list | yes | 2 | 1 |
| `file_path` int; `cwd` int with a write target | yes (crash handler) | 2 / 2 | 1 / 1 |
| deeply nested JSON (RecursionError) | yes (MIN-1) | **1** | 0 |
| no `CLAUDE_PROJECT_DIR`, deleted cwd | yes (MIN-1) | **1** | n/a |
| invalid UTF-8 in a command writing `_system/y` | yes | 2 | 0 |
| lone surrogate in `python3 -c` naming `_system/` | yes | 2 | 0 |
| `python3 -c "open('_system/x.py','w')"` (test shape) | yes | 2 | 0 |
| `python3 -Ic …` / `python3 -Bc …` | yes (MAJ-1) | **0 / 0** | 0 / 0 |
| `"$GARS_PY" -c …` | yes (MAJ-1) | **0** | 0 |
| `py -c …` | yes (MAJ-1) | **0** | 0 |
| `node --eval …` / `node -p …` | yes (MAJ-1) | **0 / 0** | 0 / 0 |
| `python3 - <<'EOF'` heredoc / `echo code \| python3` | no (MAJ-1) | 0 / 0 | 0 / 0 |
| `python3 -c` with `'_sys'+'tem/'` / `os.path.join` | listed-ish ("decoded payloads") | 0 / 0 | 0 / 0 |
| `bash <<< '…'` / `echo '…' \| bash` / `eval '…'` | no (MAJ-1) | 0 / 0 / 0 | 0 / 0 / 0 |
| `ksh -c` / `tcsh -c` | no (MAJ-1) | 0 / 0 | 0 / 0 |
| `sbatch --wrap='echo x > _system/y.py'` | no (MAJ-1) | 0 | 0 |
| `awk 'BEGIN{print "x" > "_system/y.py"}'` | no (MAJ-1) | 0 | 0 |
| `find _system … -exec touch {} +` | no (MAJ-1) | 0 | 0 |
| `bash -c` nested four deep, writing `_system/y` | yes | 2 | 0 |
| `install -m 644 evil.py _system/guard_hook.py` | yes | 2 | 0 |
| `truncate -s 0 _system/guard_hook.py` | yes | 2 | 0 |
| `chown me _references/genomes.md` | yes | 2 | 0 |
| `dd of=_system/x bs=1 count=0` | yes | 2 | 0 |
| `chmod -R a+w _system` (bare dir) | yes (MAJ-2) | **0** | 0 |
| `ln -s /tmp/evil.py _system` (dir destination) | yes (MAJ-2) | **0** | 0 |
| `cp evil.py _system/` | pre (MAJ-2) | 0 | 0 |
| `rm -rf _system` / `mv evil.md _references` | pre (MAJ-2) | 0 / 0 | 0 / 0 |
| `cd _system && echo x > guard_hook.py` | pre (MIN-8) | 0 | 0 |
| `echo x>_system/y.py` / `>|` / `1>>` / `tee -a _system/y.py` | pre (MIN-8) | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| Write / Edit / NotebookEdit `…/PLAN.md.approved` | yes | 2 / 2 / 2 | 0 / 0 / 0 |
| `echo '{}' > …/PLAN.md.approved` | yes | 2 | 0 |
| `cd <analysis dir> && echo '{}' > PLAN.md.approved` | yes | 2 | 0 |
| `python3 -c "open('…/PLAN.md.approved','w')"` | yes | 2 | 0 |
| `cp /tmp/forge/PLAN.md.approved <analysis dir>/` | yes, "any Bash write target" (MAJ-2) | **0** | 0 |
| `mv PLAN.md.approved <analysis dir>` | yes (MAJ-2) | **0** | 0 |
| `echo '{}' \| tee -a …/PLAN.md.approved` | yes (MAJ-2) | **0** | 0 |
| `python3 -c "open('…/PLAN.md'+'.approved','w')"` | listed-ish ("decoded payloads") | 0 | 0 |
| stage 03: hand-written `Status: APPROVED`, then `verify` | yes | verify 2 (12c) | verify 0 |
| stage 03: plan edited after approval, then `verify` | yes | verify 2 (12d) | verify 0 |
| stage 03: stamp reverted to DRAFT, re-`approve`, then `verify` | listed (0042:55), MIN-4 | approve 0, verify 0 | n/a |

## Stage 03 probe (`stage03_probe.py`, a throwaway workspace outside C)

| Section | Scenario | Observed |
|---|---|---|
| A | approve twice | `0`, then `0 already_approved`; record byte-unchanged; verify `0` |
| B | `atomic_open` forced to CRLF during approve | plan has CRLF; record sha = disk sha; verify `0` |
| C | CRLF→LF after approval | verify `2` "changed after approval" |
| D | fault after stamp, before record | stamp yes, record no; approve `2`; verify `2` |
| E | stamp reverted + method edited, re-approve | verify before re-approve `2`; re-approve `0`, record overwritten; verify `0` |
| F | "Status: APPROVED" inside Method prose | approve `2`, forgery message |
| G | record present, stamp removed | verify `2` |
| H | record `{"plan_sha256": 5}` / `[1]` / mode 000 | verify `2` / `2` / `PermissionError` raised |

## Mutation proofs (in `/Users/javrodher/glitch/_local/eval-scratch/gars-fix-review-mutant`, byte-backed and restored, then deleted)

The mutant was restored byte-identical after each step (`cmp` → equal; `git status --short` → empty).

| Id | Mutation | Tests run | Result |
|---|---|---|---|
| M0 | none | the 5 GuardHookTests | OK |
| M1 | drop the `tool_input`-is-object check (`guard_hook.py:332`) | the 5 GuardHookTests | **OK: survives** (the crash handler denies instead; MIN-3) |
| M2 | no recursion into shell `-c` (`guard_hook.py:297` → `pass`) | the 5 GuardHookTests | FAIL `test_denies_writes_the_scan_could_not_see` |
| M3 | remove chmod/chown from the operand scan (`guard_hook.py:239`) | the 5 GuardHookTests | **OK: survives** (MIN-3) |
| M4 | parse error returns `[]` again (`guard_hook.py:180`) | the 5 GuardHookTests | FAIL `test_allows_after_hardening` |
| M5 | whole hook at `fc4749a` | the 5 GuardHookTests | FAIL `test_unreadable_call_is_refused`, `test_denies_writes_the_scan_could_not_see` (`test_allows_after_hardening` green; MIN-7) |
| M6 | `verify` skips `approval_holds` | WorkspaceFixture (19) | FAIL 12c, 12d |
| M7 | `approve` writes no record | WorkspaceFixture (19) | FAIL 12a; ERROR 12d |
| M8 | a stamp without a record reports `already_approved` | WorkspaceFixture (19) | FAIL 12c |

At least one guard test is proven red (M2, M4, M5), and each stage 03 claim is proven red (M6, M7, M8).

## Commands and exit codes

| Command (in C unless noted) | Exit | Count / output |
|---|---|---|
| `git clone --quiet …/genomics-agentic-research-system …/gars-fix-review` | 0 | |
| `git -C C checkout -q -b review origin/task/security-minimal-fix` | 0 | |
| `git -C C remote remove origin` | 0 | |
| `git -C C log --oneline -2` | 0 | `869ab28` on `fc4749a` |
| `python3 tests/run_tests.py` | 0 | Ran 118 tests, OK (skipped=9) |
| `python3 tests/check_contracts.py` | 0 | 14 contracts clean |
| `python3 tests/check_counts.py` | 0 | enforced=3, clean |
| `python3 evals/test_harness.py` | 0 | Ran 44 tests, OK |
| `python3 evals/check_results.py --controls --lexicon` | 0 | lexicon 24/24, 21/21, 69/69; clean, graded=1 |
| `python3 tests/run_tests.py WorkspaceFixture` | 0 | Ran 19 tests, OK (skipped=1) |
| `python3 -c "ast.parse(…, feature_version=(3,6))"` on both helpers | 0 | 3.6 grammar ok ×2 |
| `python3 …/gars-fix-review-probe/probe.py fp reads bypass raw env` | 0 | tables above |
| `HOOK=…/old_guard_hook.py python3 …/probe.py reads bypass raw` (baseline) | 0 | tables above |
| `python3 …/gars-fix-review-probe/stage03_probe.py` | 0 | stage 03 table above |
| `python3 -Ic "print(…)"`; `python3 -Bc "print(…)"` | 0 | both ran inline code |
| mutation script M0–M8 in the mutant copy | 0 | mutation table above |
| `git -C C diff --stat fc4749a..869ab28` | 0 | 8 files, +411 −30 |

## Summary counts

BLOCKER 0 · MAJOR 2 · MINOR 8 · NOTE 9
