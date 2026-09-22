# Row 15 repository-side change report

Producer: Codex. Branch: `build/gars-row-15-secrets`. Parent: `c934f6d`.
Decision: [0052](../decisions/0052-row-15-secrets-canary-and-gitleaks-hooks.md).
No approval, merge, remote addition or push was performed.

The repository-side containment runner printed:

```text
canary: 0/9
```

This is **not** the full R-096/row 15 exit. The exfiltration-instructing agent
run is **NOT met**. Whole-suite green is also **NOT met**: the unchanged row 3
fixture setup is incompatible with the required fail-closed scanner; see below.

| Requirement | Changed files | Acceptance test | Result; red-on-fault seen |
|---|---|---|---|
| R-096, R-161: staged secrets gate | `gars/_system/hooks/pre-commit`, `gars/.gitleaks.toml`, `gars/tests/test_hooks_gitleaks.py` | Clean acceptance; plaintext/base64/hex refusals; clean working copy over a secret-bearing index; explicit config; missing tool/config, outside config, unknown exit and timeout refusals | PASS. **Yes:** missing-tool fail-open mutation accepted and the refusal assertion failed. Real gitleaks 8.30.0 clean and refusal cases executed. |
| R-096, R-161: pushed ranges beside row 3's gate | `gars/_system/hooks/pre-push`, shared scanner in `pre-commit`, `test_hooks_gitleaks.py` | Existing-ref range, new-ref reachable history, deletion, invalid input/object ID; prior-hook stdin/arguments and veto | PASS for new direct-invocation cases. **Yes:** ignoring the previous hook's nonzero exit made the refusal assertion fail, for both hooks. The unchanged suite invocation still runs after the scanner. |
| R-096: repository configuration and containment | `gars/.gitleaks.toml`, `gars/tests/test_secret_containment.py`, `gars/tests/secret_support.py` | Committed-tree real gitleaks scan; nine sinks and three representations per sink; existing artifact writers with an ambient canary | PASS for the stated repo-side scope, `canary: 0/9`; committed tree has zero findings. **Yes:** raw-only decoding missed a base64 log, failing detection; a fixture plant failed the zero-sink assertion. No complete canary is printed or committed. |
| R-096, R-161: preserve existing hooks | `gars/_system/hooks/install.py`, `test_hooks_gitleaks.py` | Both hooks installed in disposable `.githooks`, repeat installation, prior content retained, differing markers refused unchanged | PASS. **Yes:** removing marker checks overwrote differing content and the preservation assertion failed. No source-clone hooks were armed. |
| R-096: configuration containment | `pre-commit`, `test_hooks_gitleaks.py` | Config symlink resolves outside scratch repository | PASS. **Yes:** disabling the containment refusal made the same acceptance assertion fail. |
| R-094, `.githooks/*` only | Installer preserves Git's selected hook location; 0052 records protected-path scope | Configured `.githooks` integration and marker-content preservation | Repository installation behavior PASS; agent write enforcement **NOT met here**, carried by row 4. No guard or settings change. |
| R-096/R-161 record and test discovery | 0052, generated `docs/decisions/CONTEXT.md`, this report; count-only changes to `README.md` and `DEVELOPMENT.md` | Existing unittest discovery, decision-index rebuild and `check_counts.py` | Discovery needed no runner edit. Three current count claims updated to the runner's 250, with no other edits to those documents. |

Every changed path under `gars/` is in the authorized hook/config/new-test list:
`_system/hooks/install.py`, `_system/hooks/pre-commit`, `_system/hooks/pre-push`
(R-096/R-161, R-094 for selected `.githooks` installation);
`.gitleaks.toml`, `tests/secret_support.py`, `tests/test_hooks_gitleaks.py`,
`tests/test_secret_containment.py` (R-096/R-161). No other `gars/` file changes.
The allowlist's eight exact paths and package-pin justification are listed in
0052; only the generic API-key rule and the specific false-positive text are
exempted. A real-binary refusal also places the canary in an allowlisted
reference-document path to prove the canary rule stays active there.

## Planted faults observed red

These are producer-visible controls in disposable scratch copies. Each executes
the broken behavior, observes an actual failed acceptance assertion, and catches
that expected AssertionError so the control test itself can pass. They are not
sealed mutation evidence. Verbatim runner messages:

```text
red-on-fault: missing-gitleaks hook exits 0 -> refusal assertion FAILED
red-on-fault: previous-hook veto ignored -> refusal assertion FAILED
red-on-fault: outside-repository config accepted -> refusal assertion FAILED
red-on-fault: base64 log missed by raw-only scanner -> detection assertion FAILED
red-on-fault: canary in fixture -> zero-sink assertion FAILED
red-on-fault: differing marker hook overwritten -> preservation assertion FAILED
```

The first new-hook run exposed a defect in the scanner stand-in: it attempted to
decode the diff's leading `+` with a base64 value. That test failed; the stand-in
now removes diff prefixes before decoding. Neither enforcement nor its assertions
were weakened. The real-binary cases already rejected those encodings.

## Commands and environment

All producer shell commands ran from the repository root. Before every command,
`TMPDIR`, `TEMP` and `TMP` were exported to the owner-designated sibling scratch
directory, represented here as `$SCRATCH` to avoid committing a machine path.
No system-temp fallback or outside-tree inspection was requested. Logs, commit
message, exported trees, scanner reports, credential plants and disposable Git
repositories stayed in that scratch directory. Test subprocesses use their
scratch repository as cwd; source checks use the repository root.

Build interpreter: Python 3.13.2; `python3.6` absent from PATH. Six changed/new
Python files also parsed with `ast.parse(..., feature_version=(3, 6))`; this is
syntax evidence, not a Python 3.6.8 execution claim. New code uses stdlib only.
Gitleaks: 8.30.0 on the original PATH. Tests use isolated stand-in PATHs containing
Git, this interpreter, and either a scanner stand-in or no gitleaks. The two
real hook cases use the real binary; a separate committed-tree case also uses it.
On a machine without gitleaks these three cases skip with distinct named reasons;
all deterministic cases remain runnable.

`CI` and `GARS_ROW5_SCRATCH` were unset. The suite's 50 skips are existing missing
pipeline/reference/library/owner-evidence or explicit row-5-scratch skips; no
row 15 test skipped. No container service or cluster execution is claimed.
The new canary is planted in `GARS_TEST_CANARY` only within a test context that
restores the environment afterward. Hook scanner subprocesses remove inherited
`GITLEAKS_*` settings and request full output redaction.

Preparation used `rg`, `cat`, `sed`, Git read-only status/log/config/diff queries,
and CLI help/version queries, with the same cwd/temp exports. Edits used shell
heredocs and stdlib Python. An initial real scan of an exported HEAD identified
the eight documented package-pin false-positive files; the explicit policy scan
then measured zero. No external documentation or network search was used.

Validation commands, run from the repository root with the environment above:

- `python3 tests/run_tests.py`
- `python3 tests/check_contracts.py`
- `python3 tests/check_counts.py`
- `python3 evals/test_harness.py`
- `python3 evals/check_results.py --controls --lexicon`
- `python3 gars/tests/test_hooks_gitleaks.py`
- `python3 gars/tests/test_secret_containment.py`
- `python3 gars/tests/secret_support.py` (helper import/CLI smoke; no test runner)
- `bash docs/decisions/build_index.sh` (index generated, never hand-edited)
- `git diff --check` and the owner-specified protected-path diff-stat command.

Tests construct disposable objects with `git init`, explicit `git add`,
`git write-tree`, `git commit-tree` and `git update-ref`. They call scripts
directly with fake Git stdin, never commit or push through hooks. Installation
occurs only in disposable repositories. This clone has only sample hooks and
no configured `core.hooksPath`; its single final commit cannot run these hooks.
Staging is path-limited; the commit message is read from a scratch file.

## Runner summaries

`python3 tests/run_tests.py`

```text
canary: 0/9
Ran 250 tests in 125.186s
FAILED (failures=3, skipped=50)
```

`python3 tests/check_contracts.py`

```text
14 contracts clean: sections, wait points, vocabulary.
```

`python3 tests/check_counts.py`

```text
suite: 250 tests, from unittest's loader
enforced=3
clean — every current claim matches the suite
```

`python3 evals/test_harness.py`

```text
Ran 44 tests in 147.710s
OK
```

`python3 evals/check_results.py --controls --lexicon`

```text
clean — graded=1
```

`python3 gars/tests/test_hooks_gitleaks.py`

```text
Ran 11 tests in 20.596s
OK
```

`python3 gars/tests/test_secret_containment.py`

```text
canary: 0/9
Ran 3 tests in 10.445s
OK
```

The three whole-suite failures are two subtests of
`PrePushTests.test_installer_preserves_both_gates_stdin_and_veto` (default and
custom hook directories) and `PrePushTests.test_whole_suite_passes_directly`.
Their fixture omits `gars/.gitleaks.toml` and supplies a nonexistent push object ID.
The fail-closed gate correctly refuses. The existing `test_pre_push.py` module is
outside the new-module edit boundary. Permission to update just that setup,
retaining all assertions, was requested but not received. No silent fixture patch,
scanner bypass, assertion removal or acceptance-threshold change was made.
This means the whole-suite pre-push gate remains red on this branch until the
owner permits that fixture update. This is an explicit unresolved integration gap.

The requested diff against `c934f6d` for `evals/`, `.github/`, the guard, Claude
settings, executor, wrapper library, stage-03 helper, wrappers and `tests/fixtures`
was empty. `.gitignore` is unchanged. The study checks invoked here passed;
that does not release the owner's standing restriction: this row merges only
after the separate study's done commit. Its additional source-byte controls may
still go red because the authorized `gars/` changes are intentional.

The final staged content was also scanned directly with `gitleaks git .
--pre-commit --staged --config gars/.gitleaks.toml --redact=100 --no-banner
--ignore-gitleaks-allow --max-decode-depth=5`: exit 0, no leaks found.

## Residual gaps and hours

- **NOT met:** the exfiltration-instructing agent task and full R-096 containment
  claim. Memory, prompt and history adapters are representative, not live agent
  or memory-service evidence. Generated scripts are inspected, not submitted.
- **NOT met:** confirmation of generated job script, reproducibility manifest and
  Git index as D-17's remaining three sinks. These are the owner's supplied defaults.
- **NOT met here; carried by row 4:** the executor `--export=` allowlist.
- **NOT met here; carried by row 4:** agent bypass-switch denies and protected-path
  enforcement, including `.githooks/*`. This row makes no guard/settings edits.
- **NOT met:** whole-suite green until the existing row 3 fixture update is authorized.
- **NOT met:** Python 3.6.8/cluster execution, independent review, approval or merge.

Producer time: approximately 0.75 hours elapsed effort (estimate, not a session-registry
measurement); no cluster queue time. No ledger or acceptance threshold was changed.
