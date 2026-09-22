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

## Review round 2 fixes

Date: 2026-09-21. Producer: Codex. Review input: `docs/reviews/row_15_review.md`,
left untracked and unchanged. The owner's September 15 and September 21 rulings
apply: content inherited at `c934f6d` is out of scope and is not removed; living
implementation documents are edited in place; existing records remain append-only.
Decision [0054](../decisions/0054-row-15-review-scan-completeness.md) adds the
mechanism and evidence corrections beside the unchanged 0052 record.

| Finding | Changed files | Test | Result (red-on-fault seen: yes/no, how) |
|---|---|---|---|
| R15-01 BLOCKER: Git binary/attribute suppression | `gars/_system/hooks/pre-commit` (shared by pre-push), `gars/tests/test_hooks_gitleaks.py`, 0054, generated decision index | `GitleaksHookTests.test_real_binary_and_attributes_refused` with real gitleaks 8.30.0; both hooks, NUL and staged `-diff`, plus a clean pushed tip after an earlier contaminated commit | CLOSED by refusing omitted content. **Yes:** removing the completeness guard in the scratch hook lets both variants pass both hooks; each refusal assertion then fails. Existing scanner and prior-hook tests still pass. |
| R15-02 BLOCKER: encoded assignment logs | `gars/tests/secret_support.py`, `gars/tests/test_secret_containment.py`, 0054 | `SecretContainmentTests.test_encoded_assignment_logs_refuse_zero_sinks`, `test_repo_side_nine_sinks`, `test_decoder_nested_and_red_on_fault` | CLOSED. **Yes:** actual base64/hex assignment log plants make the zero-sink assertion fail. Restoring the old decoder in a scratch helper and running the new named test returns `FAILED (failures=1)`. All nine sinks also detect the unquoted forms. |
| R15-03 BLOCKER: incompatible row 3 fixtures | This report and current status documentation only; `gars/tests/test_pre_push.py` unchanged | `python3 tests/run_tests.py` | OPEN, scope decision required below. **Yes:** the full runner still fails the three original clean-pass fixture assertions; no test, enforcement or threshold is relaxed. |
| R15-04 MAJOR: historical count substituted | `README.md`, `DEVELOPMENT.md`, this appended report section, 0054 | `git show c934f6d:README.md`; `python3 tests/check_counts.py`; full suite | CLOSED. September 17 remains **236 tests, 28 skips**; the current run is separately dated with its actual result. **No new fault plant:** historical provenance is checked against parent bytes; the unchanged count guard checks current collection claims. |

Correction to the earlier report's count-only-change claim: the substitutions of
250 into the two dated September 17 measurements were wrong. That claim is not
supporting evidence for 250 tests passing on September 17. The parent command
`git show c934f6d:README.md` shows `236 tests, 28 of them environment skips, on
macOS at the 2026-09-17 merge`. Both living documents restore that measurement and
mark it historical using the count guard's existing marker. Their current count
claims remain enforced. The inherited README cold-clone sentence is preserved,
with an adjacent explicit exception for this branch's failing suite. No inherited
content is removed to close a finding, and no finding is silently dismissed.

The conservative R15-01 fix refuses clean binary changes too, including binary
history on new refs, rather than pretending Git's omitted content was scanned.
The numstat query has a timeout and fails closed; it includes root/merge diffs
and disables rename collapsing. Scanner failures, prior-hook vetoes and the
whole-suite gate still compose as before. Tests invoke production hooks directly
in disposable repositories; this round performs no actual Git push, remote
operation, source-clone hook installation, or agent exfiltration run.

### Validation environment and commands

All command invocations exported `TMPDIR`, `TEMP` and `TMP` to the designated
sibling scratch directory, represented here as `$SCRATCH`. Logs and fault copies
are kept there as `round2-*.log`; no reviewer scripts or outside repository files
were read. The review is the sole outside-sourced input. Python 3.13.2 on macOS
and gitleaks 8.30.0 were used. `GARS_ROW5_SCRATCH` and `CI` remain unset; the
50 suite skips are not passing executions. No tests from row 15 skipped.

| Command | Verbatim runner summary / result | Exit |
|---|---|---:|
| `python3 tests/run_tests.py` | `Ran 252 tests in 130.113s`; `FAILED (failures=3, skipped=50)`; `canary: 0/9` | 1 |
| `python3 tests/check_contracts.py` | `14 contracts clean: sections, wait points, vocabulary.` | 0 |
| `python3 tests/check_counts.py` | `suite: 252 tests, from unittest's loader`; `enforced=3`; `clean — every current claim matches the suite` | 0 |
| `python3 evals/test_harness.py` | `Ran 44 tests in 149.894s`; `OK` | 0 |
| `python3 evals/check_results.py --controls --lexicon` | `clean — graded=1` | 0 |
| `python3 gars/tests/test_hooks_gitleaks.py` | `Ran 12 tests in 30.692s`; `OK` | 0 |
| `python3 gars/tests/test_secret_containment.py` | `Ran 4 tests in 9.657s`; `OK`; `canary: 0/9`; `committed-tree gitleaks: 0 findings` | 0 |
| `python3 gars/tests/secret_support.py` | No output; helper import/CLI smoke, not a test runner | 0 |
| Scratch old-decoder mutation, named assignment-log test | `Ran 1 test in 0.003s`; `FAILED (failures=1)` (expected fault) | 1 |
| `bash docs/decisions/build_index.sh` | Decision index regenerated | 0 |
| Python `ast.parse(..., feature_version=(3, 6))` | `Python 3.6 syntax: 6 files parsed (runtime not verified)` | 0 |
| `git diff --check` | No output | 0 |
| `python3 gars/_system/hooks/pre-commit` on the round's staged paths | `gitleaks: passed`; `pre-commit: passed` | 0 |

The first documentation count check caught the phrase “row 15 test” as a claimed
suite size of 15. Rephrasing it to “tests from row 15” fixed that documentation
ambiguity; the guard is unchanged. The final count check above is green.
The committed-tree containment test scans pre-round `HEAD`; the staged hook scan
covers this round's new content. Neither is a full agent-containment measurement.

The full-suite failures are the default/custom-directory subtests of
`PrePushTests.test_installer_preserves_both_gates_stdin_and_veto`, and
`PrePushTests.test_whole_suite_passes_directly`. The latter's diagnostic remains
`gitleaks: REFUSED (gitleaks config is unreadable)`. `git diff c934f6d --
gars/tests/test_pre_push.py` produces no output: no fixture edit is hidden here.
The observed failures are the introduced integration gap, not a dismissed
inherited-content finding.

Protected-path evidence command:

```text
git diff --stat c934f6d -- evals/ .github/ gars/_system/guard_hook.py gars/.claude/settings.json gars/_system/executorlib.py gars/_system/wrapperlib.py gars/_system/stage03_analysis.py gars/_system/wrappers/ tests/fixtures/ gars/tests/test_pre_push.py
```

Output: empty; exit 0. Existing decision 0052 and the row 3 fixture are byte-identical
to pre-round HEAD. Earlier report sections are a byte-identical prefix of this
report. The review's Git blob hash remains
`c75c7ca81ba89a1375d9acab1a8f54725fad09bb`; it remains untracked. Added file
content contains no owner name, login or machine path. No review, assessment,
protected tree, sibling-row file or `.gitignore` was edited. Read-only preparation
used repository-local `rg`, `cat`, `sed`, Git status/diff/show/config/hash queries,
and local CLI help/version probes. No outside review conversation was accessed.

## Owner rulings needed

1. **R15-03 — scope authorization, still required.** The review requests repair
   of only the affected `gars/tests/test_pre_push.py` disposable fixture setup:
   add required configuration, valid scratch Git objects and a deterministic
   scanner, preserving all prior assertions and veto behavior, then rerun the
   whole suite to green. If this narrower edit boundary requires a scope
   exception, the owner must resolve it before approval. The recorded choices
   are to authorize that narrow repair, or retain the new-module boundary and
   carry the three failures. The latter leaves R15-03 open and is **not** an
   alternative interpretation of the required green gate. This part is stopped;
   no sibling implementation or fixture is changed to close it.
2. **D-17 — unchanged.** Confirm generated job script, reproducibility manifest
   and Git index as sinks 7–9, or name replacement sinks. These remain the owner's
   supplied defaults; this round does not decide the specification silence.

## Residual gaps after round 2

- Whole-suite green is **NOT met** pending R15-03's scope authorization and repair.
- Full R-096/row 15 exit is **NOT met**: no exfiltration-instructed agent task,
  live memory/prompt/history service, real credential isolation or job-runtime
  environment containment is verified. `canary: 0/9` covers the stated synthetic
  repository preparation only, not an agent-trial rate or sealed performance.
- D-17's three provisional sinks still require the owner's confirmation.
- Binary changes and binary outgoing history are conservatively refused, even
  when clean. Arbitrary encodings/archives and universal scanner completeness
  remain unproven. The new cases invoke the real production hooks and scanner;
  actual commit/push execution through installed hooks was not performed.
- Row 4's export allowlist, agent bypass-switch denies and protected-path agent
  enforcement remain outside this row; no sibling files were touched.
- Python 3.6.8 runtime, cluster/hardware execution, sealed owner evidence, this
  round's independent review, approval and merge remain unverified. The owner's
  restriction on merging only after the separate study's done commit stands;
  that commit was not established here. No push, remote or pull request occurred.


## Review round 3 fixes

Date: 2026-09-22. Producer: Codex. Starting commit: `8b8a7cd`.
Review input: `docs/reviews/row_15_review_round2.md`, left untracked and unchanged.
Its Git blob hash is `6466468b5f926f0d9cd527b3e6278ab131c6eeaa`.
The supplied review is the sole outside-sourced file read this round; no reviewer
conversation or other build/review folder was inspected.

The review reports no new defect and confirms R15-01, R15-02 and R15-04 closed.
R15-03 remains an introduced integration failure, not a disputed finding or an
inherited-content defect dismissed under the owner's ruling. Decisions 0052 and
0054 expressly stop its fixture repair pending an owner scope exception; no such
exception was supplied for this round. The owner's September 15 and September 21
rulings and this round's scope restriction stand. No hook, fixture, assertion,
guard, threshold, protected tree or sibling-row file is changed. DEVELOPMENT's
living status is updated; earlier report bytes and all existing formal records
are preserved.

| Finding | Changed files | Test | Result (red-on-fault seen: yes/no, how) |
|---|---|---|---|
| R15-01 — previously closed binary/attribute suppression | None this round | `GitleaksHookTests.test_real_binary_and_attributes_refused`, standalone hook module and complete suite | Remains closed for the reported bypass. **Yes:** the existing scratch mutation removes the guard and both hooks accept each plant; their refusal assertions fail as expected. Real gitleaks executes. |
| R15-02 — previously closed encoded assignments | None this round | `SecretContainmentTests.test_encoded_assignment_logs_refuse_zero_sinks`, `test_repo_side_nine_sinks`, `test_decoder_nested_and_red_on_fault` | Remains closed. **Yes:** assignment log plants fail zero-sink assertions; the raw-only decoder and fixture positive controls observe detection/assertion failures. These are producer-visible controls, not sealed evidence. |
| R15-03 BLOCKER — incompatible row 3 pre-push fixtures | This report; `DEVELOPMENT.md` status only | `python3 gars/tests/test_pre_push.py`; three consecutive `python3 tests/run_tests.py` runs | OPEN, owner scope ruling required. **No new fault plant:** the actual unfixed integration reproduces three failing assertions in each run. The scanner refuses unreadable configuration; no acceptance criterion is weakened. |
| R15-04 — previously closed historical count substitution | `DEVELOPMENT.md` current status only; historical measurements unchanged | `python3 tests/check_counts.py`; parent-byte comparison | Remains closed. **No new fault plant:** the existing count guard passes; September 17 measurements retain the parent value of 236 with 28 skips. Current collection remains 252. |

### Round 3 validation

All shell calls exported `TMPDIR`, `TEMP` and `TMP` to the designated sibling
scratch folder before running commands. Logs, validation script and commit
message stayed there; `$SCRATCH` below denotes that folder without a machine
identifier. Validation used `PYTHONDONTWRITEBYTECODE=1`. Platform: Darwin,
`python3` 3.8.2, `python3.13` 3.13.2, gitleaks 8.30.0. `CI` and
`GARS_ROW5_SCRATCH` were unset. Logs are `$SCRATCH/round3-<name>.log`, using the
names in parentheses below. No tests from row 15 skipped; the 50 full-suite skips
are not successful executions. Three complete runs were made consecutively;
independent hook/containment and harness checks also ran during validation.

| Command (log name) | Verbatim runner summary | Exit |
|---|---|---:|
| `python3 tests/run_tests.py` (full-suite-1) | `canary: 0/9`; `Ran 252 tests in 146.403s`; `FAILED (failures=3, skipped=50)` | 1 |
| `python3 tests/run_tests.py` (full-suite-2) | `canary: 0/9`; `Ran 252 tests in 138.287s`; `FAILED (failures=3, skipped=50)` | 1 |
| `python3 tests/run_tests.py` (full-suite-3) | `canary: 0/9`; `Ran 252 tests in 129.113s`; `FAILED (failures=3, skipped=50)` | 1 |
| `python3 tests/check_contracts.py` (contracts) | `14 contracts clean: sections, wait points, vocabulary.` | 0 |
| `python3 tests/check_counts.py` (counts) | `suite: 252 tests, from unittest's loader`; `enforced=3`; `clean — every current claim matches the suite` | 0 |
| `python3 evals/check_results.py --controls --lexicon` (results) | `clean — graded=1` | 0 |
| `python3 gars/tests/test_hooks_gitleaks.py` (hooks) | `Ran 12 tests in 33.477s`; `OK` | 0 |
| `python3 gars/tests/test_secret_containment.py` (containment) | `canary: 0/9`; `Ran 4 tests in 13.712s`; `OK` | 0 |
| `python3 gars/tests/test_pre_push.py` (pre-push) | `Ran 7 tests in 7.820s`; `FAILED (failures=3)` | 1 |
| `python3 gars/tests/secret_support.py` (helper) | No output; helper smoke only | 0 |
| `python3 evals/test_harness.py` (harness) | `Ran 44 tests in 177.050s`; `FAILED (errors=13)` | 1 |
| `python3.13 evals/test_harness.py` (harness-py313) | `Ran 44 tests in 165.676s`; `OK` | 0 |

The three full-suite failures are
`PrePushTests.test_whole_suite_passes_directly` and the default/custom-directory
subtests of `test_installer_preserves_both_gates_stdin_and_veto`. The standalone
module reproduces them. Its direct clean-pass failure includes
`gitleaks: REFUSED (gitleaks config is unreadable)` even though the miniature
suite passes. Command `git diff c934f6d -- gars/tests/test_pre_push.py` returns
no output (exit 0), corroborating the review's unchanged-fixture evidence.

The Python 3.8 harness errors arise from inherited `ast.unparse` and
`str.removesuffix`/`str.removeprefix` calls. Python 3.13 corroboration does not turn the required
Python 3.8 command into a pass. These eval files are protected and unchanged;
no new finding is claimed against their inherited content. Study checks do not
establish the separate study's done commit or BLOCKED status.

The named containment run prints `canary: 0/9` and
`committed-tree gitleaks: 0 findings`. That scan covers pre-round HEAD;
the final direct staged pre-commit invocation covers this round's documentation.
Neither establishes full agent containment or the row's complete exit.
The direct command `python3 gars/_system/hooks/pre-commit` reports
`gitleaks: passed`; `pre-commit: passed`, exit 0. The final count check after the
documentation edits again reports `clean — every current claim matches the suite`.

### Scope and provenance checks

`bash docs/decisions/build_index.sh` regenerated the index; byte comparison
against HEAD reports `Decision index regenerated; byte-identical to HEAD.`
`ast.parse(..., feature_version=(3, 6))` on the six row-15 Python files reports
`Python 3.6 syntax: 6 files parsed (runtime not verified)`, exit 0.
The historical-line check reports
`Historical measurements: both parent lines retained verbatim.`

The scope audit uses:

```text
git diff --stat c934f6d -- evals/ .github/ gars/_system/guard_hook.py gars/.claude/settings.json gars/_system/executorlib.py gars/_system/wrapperlib.py gars/_system/stage03_analysis.py gars/_system/wrappers/ tests/fixtures/ gars/tests/test_pre_push.py
```

Output: empty; exit 0. Only this report and DEVELOPMENT's current status change.
The pre-round report is preserved as an exact byte prefix. Existing decisions,
formal reviews and assessments are unchanged, as is the supplied untracked
review hash above. Added content attributes rulings to the owner and contains
no owner login or machine identifier. `git diff --check` returns no output,
exit 0. Read-only preparation used repository-local reads, searches and Git
queries; logs and audit scripts remain in `$SCRATCH`.

## Owner rulings needed

1. **R15-03 — scope exception remains unresolved.** The review requires repair
   only of `gars/tests/test_pre_push.py`'s affected disposable fixture setup:
   required scanner configuration, valid scratch Git objects and a deterministic
   scanner, preserving every existing assertion, stdin check and veto behavior;
   then rerun the complete suite to green. The recorded options remain to
   authorize that narrow fixture repair, or retain the new-module boundary and
   carry the three failures. Carrying failures leaves the BLOCKER open and does
   not satisfy the green gate. This part is stopped; the scope exception is not
   inferred from a request to process this review.
2. **D-17 — unchanged.** Confirm generated job script, reproducibility manifest
   and Git index as sinks 7–9, or name replacement sinks. These remain the
   owner's provisional defaults, not newly approved sink identities.

## Residual gaps after round 3

- R15-03 remains OPEN; whole-suite green and the complete row 15 exit are **NOT met**.
- Full R-096 containment, an exfiltration-instructed agent task, live memory,
  prompt/history services, real credential isolation and job-runtime containment
  remain unverified. The synthetic nine-sink result is limited to repository
  preparation and scanning.
- D-17 sink confirmation, sealed owner evidence, Python 3.6.8 and cluster/Linux
  execution remain unverified. Python 3.13 full-suite execution was not repeated
  this round; the current full-suite evidence is Python 3.8.2.
- Clean binary changes and outgoing binary history remain conservatively refused.
  Universal detection and arbitrary archive/encoding coverage are not established.
- The sibling row's export allowlist, agent bypass-switch denies and protected-path
  enforcement remain out of scope; no sibling file is changed to close a finding.
- The owner's merge hold pending the separate study's done commit remains; that
  commit was not established. No push, remote operation, merge or pull request was
  performed, and no source-clone hook was installed. Independent review of this
  round and approval remain outstanding.

## Review round 4 fixes

Date: 2026-09-22. Producer: Codex. Starting commit: `4725962`.
Review input: `docs/reviews/row_15_review_round3.md`, unchanged and untracked;
Git blob hash: `79e20994b2aef18701dd3de3c8fde6c01191403d`.
This supplied review was the only outside-sourced file read; no reviewer
conversation or other build/review folder was read. The earlier report remains
an exact byte prefix; existing decisions, formal reviews and assessments remain
unchanged. README and DEVELOPMENT are living documents updated in place.

The owner supplied two provisional option-A rulings on 22 September 2026:
R15-03's narrow fixture repair is authorised, and D-17's generated job script,
reproducibility manifest and Git index are confirmed provisionally as sinks 7–9.
Each is recorded in new decision
[0055](../decisions/0055-row-15-provisional-owner-rulings.md), attributed to the
owner and marked **provisional ruling, to be confirmed by the owner**.
Earlier records' pending-ruling wording describes their historical state; this
addendum and the living documents record the current authority to proceed.

| Finding | Changed files | Test | Result (red-on-fault seen: yes/no, how) |
|---|---|---|---|
| R15-03 BLOCKER — incompatible pre-push fixtures | `gars/tests/test_pre_push.py`; 0055; generated decision index; README; DEVELOPMENT; this report | All seven existing `PrePushTests`, including `test_whole_suite_passes_directly` and both default/custom hook-directory subtests of `test_installer_preserves_both_gates_stdin_and_veto`; three consecutive whole-suite runs | CLOSED in producer validation under the provisional scope ruling. **Yes:** before repair the module reproduces three failures; in scratch copies, separately removing config, restoring the fake object ID and removing the scanner each makes the unchanged clean-pass assertion fail. The intact control passes. All original suite-failure, empty-tree, stdin, argument and previous-hook veto checks pass. |
| D-17 — identities of sinks 7–9 | 0055; generated decision index; README; DEVELOPMENT; this report | `SecretContainmentTests.test_repo_side_nine_sinks`; standalone containment module | Provisionally confirmed by the owner, pending later confirmation or reversal. Repository-side `canary: 0/9`. **Yes:** existing per-sink plain/base64/hex positive controls and planted contamination checks run; this is not an agent-containment exit claim. |
| R15-01 — previously closed binary/attribute suppression | None in its implementation or tests | `GitleaksHookTests.test_real_binary_and_attributes_refused`; standalone hook module | Remains closed. **Yes:** scratch guard removal allows both plants through both hooks and their refusal assertions fail. Real gitleaks executes. |
| R15-02 — previously closed encoded assignments | None in its implementation or tests | `SecretContainmentTests.test_encoded_assignment_logs_refuse_zero_sinks`, `test_decoder_nested_and_red_on_fault`, `test_repo_side_nine_sinks` | Remains closed. **Yes:** base64/hex assignment plants fail zero-sink assertions; raw-only decoding fails detection. |
| R15-04 — previously closed historical count substitution | README and DEVELOPMENT current status only | `tests/check_counts.py`; comparison with `c934f6d` | Remains closed. **No new fault plant:** both September 17 lines retain parent bytes apart from the pre-existing historical-count marker; the unchanged count guard passes all three current claims. |

### Every changed fixture line and its reason

Only fixture setup, invocation environment and the expected fixture value change.
The production hooks, scanner policy, shared test helpers and all other test
modules are unchanged. Below, old line numbers refer to pre-round `4725962`;
new numbers refer to the repaired `gars/tests/test_pre_push.py`. Every added or
replaced line is listed individually, including each half of the wrapped call.

| Old line → new line | New line | Reason |
|---|---|---|
| added → 8 | `from secret_support import CONFIG, checked, snapshot, standin` | Reuse the existing row-15 fixture helpers and explicit scanner policy; no helper implementation change. |
| 11 → 12 | `PUSH_INPUT = 'refs/heads/test %s refs/heads/test ' + '0' * 40 + '\n'` | Replace the nonexistent fixed object ID with a slot for a real scratch commit; preserve both ref names, zero remote ID and terminating newline. |
| added → 21 | `shutil.copyfile(str(CONFIG), str(self.root / 'gars/.gitleaks.toml'))` | Supply the repository-local configuration required by the fail-closed scanner. |
| added → 22 | `checked(['git', 'add', '--', 'tests', 'gars'], self.root)` | Stage only the disposable miniature tree and config for creation of valid scratch Git objects. |
| added → 23 | `self.push_input = PUSH_INPUT % snapshot(self.root)` | Generate a real tree/commit with `write-tree`/`commit-tree`, without invoking commit hooks, and substitute its ID into stdin. |
| added → 24 | `self.scanner_env = standin(self.root)` | Provide the existing deterministic scanning stand-in on an isolated Git/Python PATH; use its scanning mode, not its unconditional-clean mode. |
| added → 25 | `(Path(self.scanner_env['PATH']) / 'cat').symlink_to(shutil.which('cat'))` | Keep the unchanged previous-hook script's `cat > previous-input` functional on the isolated PATH. |
| 22 → 28 | `return run([hook, 'fixture-remote', 'fixture-target'], self.root,` | Wrap the same hook call and preserve its arguments and working directory. |
| 22 → 29 | `self.push_input, self.scanner_env)` | Pass the valid stdin fixture and deterministic scanner environment to direct and installed hook invocations. |
| 71 → 78 | `self.assertEqual((self.root / 'previous-input').read_text(), self.push_input)` | Preserve the exact-byte stdin assertion, comparing with the actual valid fixture sent to the hook. |
| 84 → 91 | `self.assertEqual((self.root / 'previous-input').read_text(), self.push_input)` | Preserve the same exact-byte stdin assertion while the whole-suite gate vetoes. |

An AST comparison of all seven existing test method bodies against pre-round
HEAD, normalizing only `self.push_input` to the old `PUSH_INPUT` reference,
reports: `Existing test bodies: all 7 preserved after normalizing the valid stdin fixture reference.`
No assertion is removed, added or weakened; no stdin check or veto is dropped.
The fake-object fault still uses the actual repaired setup otherwise, proving
that the scanner continues to refuse an unavailable object. Fault copies and
all their logs stay in `$SCRATCH`; these are producer-visible controls, not
sealed mutation evidence.

### Round 4 validation

Every shell call exported `TMPDIR`, `TEMP` and `TMP` to the designated sibling
scratch folder before running commands. `$SCRATCH` denotes that directory;
no machine path or identifier is committed. Test runs also set
`PYTHONDONTWRITEBYTECODE=1`. Platform: Darwin; `python3` 3.8.2;
`python3.13` 3.13.2; gitleaks 8.30.0. `CI` and `GARS_ROW5_SCRATCH` were unset.
The three Python 3.8 complete runs ran consecutively, followed by the Python 3.13
complete run. Standalone checks ran independently alongside that sequence.
The 50 skips represent existing unavailable pipeline/reference/library or
owner-evidence inputs and the unset row-5 scratch variable; they are not passing
executions. No tests from row 15 skipped.

Logs use `$SCRATCH/round4-<name>.log`, with names given below. Read-only preparation
used repository-local `rg`, `cat`, `sed`, `nl` and Git queries; versions were
queried locally. No network, remote operation or source-hook installation occurred.

| Command (log name) | Verbatim runner summary | Exit |
|---|---|---:|
| `python3 gars/tests/test_pre_push.py` (pre-push-before) | `Ran 7 tests in 4.210s`; `FAILED (failures=3)` | 1 |
| `python3 gars/tests/test_pre_push.py` (pre-push) | `Ran 7 tests in 8.342s`; `OK` | 0 |
| `python3 tests/run_tests.py` (full-suite-1) | `canary: 0/9`; `Ran 252 tests in 144.562s`; `OK (skipped=50)` | 0 |
| `python3 tests/run_tests.py` (full-suite-2) | `canary: 0/9`; `Ran 252 tests in 135.904s`; `OK (skipped=50)` | 0 |
| `python3 tests/run_tests.py` (full-suite-3) | `canary: 0/9`; `Ran 252 tests in 136.085s`; `OK (skipped=50)` | 0 |
| `python3.13 tests/run_tests.py` (suite-py313) | `canary: 0/9`; `Ran 252 tests in 143.837s`; `OK (skipped=50)` | 0 |
| `python3 tests/check_contracts.py` (contracts) | `14 contracts clean: sections, wait points, vocabulary.` | 0 |
| `python3 tests/check_counts.py` (counts) | `suite: 252 tests, from unittest's loader`; `enforced=3`; `clean — every current claim matches the suite` | 0 |
| `python3 evals/check_results.py --controls --lexicon` (results) | `clean — graded=1` | 0 |
| `python3 gars/tests/test_hooks_gitleaks.py` (hooks) | `Ran 12 tests in 28.190s`; `OK` | 0 |
| `python3 gars/tests/test_secret_containment.py` (containment) | `canary: 0/9`; `Ran 4 tests in 11.557s`; `OK` | 0 |
| `python3 gars/tests/secret_support.py` (helper) | No output; helper smoke only | 0 |
| `python3 evals/test_harness.py` (harness) | `Ran 44 tests in 167.038s`; `FAILED (errors=13)` | 1 |
| `python3.13 evals/test_harness.py` (harness-py313) | `Ran 44 tests in 155.900s`; `OK` | 0 |
| `python3 tests/check_counts.py` (counts-final) | `suite: 252 tests, from unittest's loader`; `enforced=3`; `clean — every current claim matches the suite` | 0 |
| Scratch fixture faults (`round4-faults.py`) | `intact: exit 0; OK`; each of missing-config, fake-object and missing-scanner: `FAILED (failures=1)` | 0 for driver; each fault 1 as expected |
| `bash docs/decisions/build_index.sh` | Index regenerated; one new 0055 row | 0 |
| Python 3.6 syntax parse and scope audit (`round4-audit.py`) | `Python 3.6 syntax: 7 files parsed (runtime not verified).`; prior records/report and review preserved; protected diff empty | 0 |
| `git diff --check`; `git diff --cached --check` | No output | 0 |
| `python3 gars/_system/hooks/pre-commit` (staged-scan) | `gitleaks: passed`; `pre-commit: passed` | 0 |

The inherited Python 3.8 eval-harness errors use `ast.unparse` and
`str.removesuffix`/`str.removeprefix` in unchanged protected eval code. They are
reported as failures; the separate Python 3.13 pass does not convert that command
into a pass. No protected eval file or CI setting is edited. The whole-suite
runner is separately green in this run; these commands test different scopes.
Study checks do not establish the separate study's done commit or BLOCKED status.

The containment module's committed-tree scan covers pre-round HEAD; its exact
message is `committed-tree gitleaks: 0 findings`. The direct staged pre-commit
invocation covers the six final paths in this round. Neither scan establishes
full agent containment or releases the merge hold. The source clone remains
unarmed; tests invoke hooks directly in disposable repositories without a push.

### Scope and provenance checks

`bash docs/decisions/build_index.sh` regenerates the index with the single new
0055 row; earlier decision records retain their exact bytes, including 0052/0054.
The final audit confirms the pre-round change report is an exact byte prefix,
the supplied review hash is unchanged and the review remains untracked.
Historical measurements retain both parent lines, and seven Python files parse
with `feature_version=(3, 6)`; this is syntax evidence, not runtime verification.

The protected-path command is:

```text
git diff --stat c934f6d -- evals/ .github/ gars/_system/guard_hook.py gars/.claude/settings.json gars/_system/executorlib.py gars/_system/wrapperlib.py gars/_system/stage03_analysis.py gars/_system/wrappers/ tests/fixtures/
```

Output: empty; exit 0. `test_pre_push.py` is the sole newly changed `gars/` path
this round and is explicitly authorised by 0055; its entire diff is accounted
for line by line above. The other five changed paths are this report, README,
DEVELOPMENT, the generated index and the new decision addendum. No guard,
threshold, test runner, count checker, unrelated inherited content, prior formal
record, assessment, review, protected tree or sibling-row implementation is
changed to close a finding. Added content attributes both rulings only to the
owner and contains no personal name, login or machine identifier.
`git diff --check` returns no output, exit 0. Staging is limited to these six
paths; the single round commit uses a message file in `$SCRATCH` and a generic
producer identity. All supplied review files remain untracked.

## Owner rulings needed

No unresolved implementation choice blocks this round. The owner must later
confirm or reverse **both** option-A provisional rulings recorded in 0055:
R15-03's narrow fixture scope exception and D-17's sink identities. Each is a
**provisional ruling, to be confirmed by the owner**; no final confirmation is
claimed. The previously recorded alternatives remain historical: retain the
new-module boundary and carry the three failures for R15-03, or name replacement
sinks for D-17. The owner has provisionally selected option A for each, so the
authorised repair and documentation updates proceed now.

## Residual gaps after round 4

- R15-03's integration blocker is closed in producer validation; R15-01, R15-02
  and R15-04 remain closed. Independent review of this round remains outstanding.
- Full R-096/row 15 exit is **NOT met**. The exfiltration-instructed agent task,
  live memory/prompt/history services, real credential isolation and generated-job
  runtime containment remain unverified. `canary: 0/9` measures representative
  repository preparation and scanning, not an agent-trial rate or sealed evidence.
- Both owner rulings await later confirmation or reversal. Sealed owner evidence,
  Python 3.6.8 runtime, Linux/cluster execution and the 50 skipped cases remain
  unverified. The required Python 3.8 eval-harness command retains 13 inherited
  errors; Python 3.13's separate pass is recorded with that limitation.
- Clean binary changes and outgoing binary history remain conservatively refused.
  Universal secret detection and arbitrary archive/encoding coverage are unproven.
- Row 4's export allowlist, bypass-switch denies and protected-path agent
  enforcement remain out of scope and unchanged.
- The owner's merge hold pending the separate study's done commit remains; that
  commit or BLOCKED status was not established. No push, remote, merge or pull
  request was performed. Final approval is not claimed.
