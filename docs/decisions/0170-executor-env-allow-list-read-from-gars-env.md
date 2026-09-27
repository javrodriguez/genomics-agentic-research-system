---
date: 2026-09-27
status: standing
kind: defect
touches:
  - gars/_system/executorlib.py
  - gars/_system/gars-env.sh
  - gars/tests/test_executor_env.py
  - gars/tests/test_rerun_check.py
  - gars/tests/test_execution_policy.py
  - tests/run_tests.py
symptoms:
  - a job dies in gars-env.sh with "GARS_BIO is unset or missing" although the operator exported GARS_BIO and GARS_NXF and every interactive check passed
  - a Slurm job runs with $GARS_ROOT/.nextflow_gars although the operator exported their own NXF_HOME
---
# The executor's environment allow-list is read from gars-env.sh, not kept by hand

Follow-up to [0058](0058-row-4-typed-surface-and-attack-list.md) (R-096's executor half), whose bytes are unchanged.
Every ruling here is **the lane's**, made under the owner's standing delegation of 23 September 2026 and ruled by the lane's coordinator on 27 September 2026; no sentence in this record is the owner's.
0171 is the lane's delegated approval of the protected change; this record does not write it.

## Context

The launch pad's session (27 Sep 2026, at public main `4597dd4`) installed the two environments away from the default path and exported `GARS_BIO` and `GARS_NXF`, as `gars/_system/gars-env.sh` and `gars/_references/environment.md` ("an operator's own exports win") say to.
Every interactive check passed, because the agent's own shell holds the variables; the first real submit then died in `gars-env.sh`'s fail-fast with "GARS_BIO is unset or missing", naming a path the operator never chose.
Reproduced without a model on `4597dd4`: a fake `GARS_ROOT` whose two environment folders sit at non-default paths, all three variables exported, a generated-style `submit.sh` through the real local backend: `execution_env()` dropped `GARS_BIO` and `GARS_NXF`, the job exited 1 with the FATAL line, and Slurm's argv read `--export=PATH,HOME,USER,LOGNAME,LANG,LC_ALL,TMPDIR,TEMP,TMP,GARS_ROOT,GARS_PIPELINES`.

The cause was a second, hand-kept list.
R-096's executor half passes a job only named variables (`EXPORT_NAMES` in `executorlib.py`), and that tuple fed every executor subprocess and Slurm's `--export=`.
`gars-env.sh` reads eight names from the environment before defaulting them (`GARS_ROOT` by `${…:?}`, the other seven by `NAME="${NAME:-default}"`): `APPTAINER_CACHEDIR GARS_BIO GARS_NXF GARS_PIPELINES GARS_REFS GARS_ROOT GARS_WRAPPERS NXF_HOME`.
The tuple carried two of them, so an operator's own value for the other six never reached the job; on a cluster whose `~/.bashrc` exports `NXF_HOME` (the validated setup in `environment.md`), a Slurm job silently got the GARS-local default instead.

## Decision

**Ruling 0170 (the lane's).**

1. **The list is read, not kept** (`gars/_system/executorlib.py`).
   `EXPORT_NAMES` is the sorted union of `BASE_NAMES` (`PATH HOME USER LOGNAME LANG LC_ALL TMPDIR TEMP TMP`, process basics) and the names `overridable_names()` reads from the `gars-env.sh` beside `executorlib.py`.
   The grammar is exactly a line `NAME="${NAME:-…}"` or `NAME="${NAME:?…}"`, optionally `export `-prefixed, with the same name on both sides.
   All eight overridables pass, locally and in Slurm's `--export=` (one list).
   Each is a path (the operator's own, or `gars-env.sh`'s exported default), not a credential; nothing outside the base names and `gars-env.sh`'s own overridables passes, so R-096 holds.
   An agent session cannot set these variables for the executor: the guard refuses an env-prefixed command (`GARS_BIO=/x ls .`, `env …`, `export …`) as an unregistered executable (R-092), checked with json-built hook payloads while `ls .` passed.
2. **Fail loud, never narrower.**
   Importing `executorlib` never raises.
   If the sibling file cannot be read or decoded, or the parse finds no name, `execution_env()`, `submit_argv()` and `submit()` raise `ExecutionEnvError` ("gars-env.sh could not be read, so the executor cannot tell which variables it may pass (R-096)"), never a fallback list.
   `submit()` checks before it creates the records folder, takes the lock or saves the R-076 reservation, so a failed read strands no reservation (review r1).
3. **`gars-env.sh` is unchanged**; it is the source of truth.

Three tests that asserted the old literal list were changed with it: `tests/run_tests.py`'s recorded-submission line and `test_execution_policy.py`'s `--export=` argument now expect `','.join(EXPORT_NAMES)` (every other assertion kept), and `test_rerun_check.py`'s workspace stub, which replaced the copied `gars-env.sh` with `:` and so met the new refusal in all 17 `RerunCheckTests`, now writes one `NAME="${NAME:-}"` line per name the real file declares, with an assertion that both parse to the same names.

Rejected alternatives: extending the hand tuple (the second list that drifted, and would drift again); passing `os.environ` whole (breaks R-096); falling back to the base names when the file is unreadable (a silent narrower list is this defect again).

## What this does not close

- **R1** An override written outside the `${NAME:<op>` shape (an if-block assignment, a non-colon `${X-…}`) would not be passed and is not caught by the drift test. Both reviews read `gars-env.sh` and found none today; `JAVA_HOME`, `NXF_APPTAINER_CACHEDIR`, `GARS_PY` and `GARS_SKILLS` are assigned unconditionally, so an operator's value for them is ignored and not passing them is consistent.
- **R2** Slurm's handling of a listed name that is unset is not observed live (the live scheduler acceptance is parked). Both reviewers, from sbatch's documented behaviour, expect it to be skipped silently so the `:-` default applies, as on the local backend.
- **D1** (review r2) No test binds the environment the local job actually receives beyond the operator paths: `_local_submit` passes `env=execution_env()` (unchanged), but a mutation to `dict(os.environ, **execution_env())` stays green. A canary in the C1 test's child dump would bind it.
- **D2** (review r2) The literal grammar fixture does not pin the line anchor: a parser that also accepts indented assignments stays green (no indented overridable exists today).
- **D3** (review r2) The reservation test runs with the ambient PATH; a double regression could hand its fixture to a real `sbatch`. A stub `sbatch` first on PATH would close it.
- **D4** (review r1) `GARS_WRAPPERS` and the cache paths are exported defaults, so a shell that once sourced one workspace's `gars-env.sh` forwards that workspace's wrappers path into a job from another. Inert today: no job body runs through `$GARS_WRAPPERS`.

## Test

`gars/tests/test_executor_env.py` is new, 6 tests: a real local job with non-default `GARS_BIO`/`GARS_NXF` sees both and sources `gars-env.sh` cleanly (stub `nextflow`/`apptainer` first on PATH); every parsed name reaches `execution_env()` and Slurm's `--export=`; an independent wider scan of every `${NAME:<op>` expansion equals the parser's result, and an added `export FOO="${FOO:-x}"` line is followed by both consumers; a synthetic secret and an unlisted `GARS_*` never pass, against a literal base set pinned in the test; a missing, empty or undecodable source makes both consumers raise; and a submit with an unreadable source raises before any reservation, on both backends.
They must fail when the hand tuple returns, when the parser drops the `export ` prefix, accepts only `:-`, or drops the same-name rule, when a failed read falls back or an empty parse is accepted, when `execution_env()` passes everything, when `submit_argv()` or `submit()` skips the check, when Slurm's list is the base names only, or when a credential name joins `BASE_NAMES`; the lane's mutation proof killed all 11.
The landing's evidence is recorded in 0171.

## Status

Standing. The change record for the executor env allow-list follow-up; its protected-change approval is 0171.

## Date

2026-09-27
