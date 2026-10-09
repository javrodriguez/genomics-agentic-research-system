status: stopped
RESUME HERE: glitch-f3 rules OPEN quote-lint (R4/R10 versus the mandatory lint gates), then task 1 can resume.
head: 91b8f0ee2a5d46f6b1556bd801101c485387a25e (last code commit; this report is added by the following, separate commit)

Recorded after reading date: 2026-10-09 19:32:59 EDT.

Task 2 is built and its text contract is green. Task 1 stopped before any edit under section 9: the exact R4 and R10 quotations add mandatory lint failures, while the lint policy and its exceptions are outside this lane's ownership. No draft, draft builder, arms, or wave 1 exception was changed. This is not a completed lane or a freeze-ready CI job.

The five pre-launch slots were ruled; none retained its pending marker. V1–V8 were unfilled. Their values were not chosen here. Findings below are this builder's; the brief's rulings remain attributed to glitch-f3 under Javier's delegation.

## Start and history

The required start checks found the exact base and branch, a clean status including ignored paths, and all four old commits. core.hooksPath printed no value. The closing start output was:

```text
commit
commit
commit
commit
hooksPath read
light ok: load1 3.67 < 16.00 (memory pressure unreadable; light does not need it)
light-ok exit 0
Python 3.13.2
```

Read CLAUDE.md. All base readings below ran once before any edit. Every invoked test/check had light-ok immediately before it in the same shell command, one foreground test process at a time, with the prescribed interpreter, bytecode setting and three BLAS settings. No light hold occurred.

Commits, in order:

- 343997d1fa906d0fd102f150e50dc8adfd971295: red contract for the absent job; 13 tests, 3 assertion failures, 0 errors, 0 skipped. Its copy gate passed.
- 91b8f0ee2a5d46f6b1556bd801101c485387a25e: the added job and the correction to the text checker exposed by its duplicate-copy mutation. The 13 tests pass and all 79 whole-file mutations fail by assertion.
- This report's own commit follows the code commit. No prior commit was amended or rewritten. Both code commits used git commit -F with a temporary message file and the exact Codex trailer. Hooks were unchanged and neither commit was refused.

## Changes and ownership

The actual output of git diff --stat 89b54db4..HEAD at the code head:

```text
 .github/workflows/ci.yml                     | 125 ++++++++
 evals/gap-study-4/COPIED.d/w5c-draft-ci.json |  20 ++
 evals/gap-study-4/checks.d/w5c-draft-ci.txt  |   4 +
 evals/gap-study-4/tests/test_ci_job.py       | 413 +++++++++++++++++++++++++++
 4 files changed, 562 insertions(+)
```

This report adds lane-reports/w5c-draft-ci.md. The three added files under the round directory are all claimed new by this lane's fragment.

PL-1 wave 1 changes, line by line: none. build_draft.py was not changed or moved between fragments; study.py lines 14 and 56 were not changed; w1a's fragment was not changed; tests/test_scaffold.py lines 40 and 475 were not changed. Task 1's exception is still available to the resumed builder.

The workflow has 125 added lines and zero removed lines against the lane base. Against kickoff, the staged workflow inventory printed 149 added / 0 removed for ci.yml and 48 added / 0 removed for the existing geo-recompute.yml; those extra changes predate this lane. This lane touched only ci.yml. Removing this lane's one job reproduces the base workflow exactly, which binds the triggers and every sibling job.

The job keeps the required box integration command even though tests/test_box_integration.py is absent, and the required --regrade spelling even though check_results.py does not accept it. The private command is replaced by its exact named message. No workflow, act, gh, vendor executable, model, container or network request was run.

## Why task 1 stopped

R4 (plan 210) requires this exact quote:

> Counts with exact Clopper-Pearson 95% bounds per half-cell, rounded outward (lane E1's method); never a rate in a headline.

R10 (plan 140) requires this exact quote:

> Round 4 is a fresh baseline: it is never compared with or pooled with round 3, or with any earlier round (the study's `not_poolable` rule), so it needs no bridge back to them (D3, decided).

The existing lint_language.scan_text rejects the first with percentage. The existing lint_pooling.scan_text rejects the second with pooled. Both JSON strings were passed in memory to the existing functions under the exact future draft path, using the existing language exceptions. No draft file was written. The quoted output was:

```text
R4 plan 210: {"language": ["percentage"], "pooling": []}
R10 plan 140: {"language": [], "pooling": ["pooled"]}
quoted requirements: 2 of 2 rejected by unchanged mandatory linters; no file written
```

The language linter scans .json by default and its exception matching requires the exact path, pattern and line. The only existing excusal names an older round's contract_quotes.json. The other linter has no excusal path. PL-4 settles the leak-word conflict, not these publication lint conflicts. Section 5 owns neither linter nor language-allowlist.json, and section 3.1 preserves their wave 1 bytes. Section 8 requires both gates and section 9 forbids resolving a new conflict without a ruling.

The base also had 25 language findings and 8 pooling findings. They remain exactly the same at the code head, including paths, lines, patterns and excerpts; only the number of inputs grew from 59 to 60 because of this lane's fragment. This lane added no lint findings.

Task 2 started under section 9's separate-files provision after task 1 stopped without editing anything. This lane's reading: section 8 explicitly preserves and reports pre-existing reds, so the inherited lint failures were reported rather than treated as new failures caused by task 1. The task 2 work and its applicable deterministic gates are green; the whole lane is stopped.

## Requirement accounting

For R1–R34, “not built” means the task 1 stop applies, not that the requirement is waived. There is no new test_build_draft.py and no generated prereg-draft.json. A row below with an OPEN-value dependency does not claim its mechanism was implemented.

| Requirement | Test name | Mutant | Red proven / out of scope / OPEN |
|---|---|---|---|
| R1: Assembly, committed draft and source hashes | Not built; task 1 stopped | Not run | OPEN quote-lint |
| R2: Models, arms, wordings, factors, seeds and n | Not built; task 1 stopped | Not run | OPEN quote-lint; OPEN-value V1–V4 |
| R3: Whole-row take order | Not built; task 1 stopped | Not run | OPEN quote-lint |
| R4: Outcomes, stops, reporting and estimand | Not built; task 1 stopped | Not run | OPEN quote-lint |
| R5: Fresh-baseline predictions | Not built; task 1 stopped | Not run | OPEN quote-lint |
| R6: Locks and version pins | Not built; task 1 stopped | Not run | OPEN quote-lint; OPEN-value pins |
| R7: Salted digest shape | Not built; task 1 stopped | Not run | OPEN quote-lint; OPEN-value digests |
| R8: Eleven limitations and box residuals | Not built; task 1 stopped | Not run | OPEN quote-lint; OPEN-value V8, preflight |
| R9: Leak list and transcript check | Not built; task 1 stopped | Not run | OPEN quote-lint; OPEN-value first-walk |
| R10: Earlier-round separation | Not built; task 1 stopped | Not run | OPEN quote-lint |
| R11: Agent on every row | Not built; task 1 stopped | Not run | OPEN quote-lint |
| R12: Harness in cell keys | Not built; task 1 stopped | Not run | OPEN quote-lint |
| R13: Arms O/G and amendment | Not built; task 1 stopped | Not run | OPEN quote-lint |
| R14: Vendor model identities | Not built; task 1 stopped | Not run | OPEN quote-lint |
| R15: Config, effort, mapping, prices, markers and furniture | Not built; task 1 stopped | Not run | OPEN quote-lint; OPEN-value instrument-values, routing |
| R16: Caps | Not built; task 1 stopped | Not run | OPEN quote-lint |
| R17: Comparison families and design | Not built; task 1 stopped | Not run | OPEN quote-lint; OPEN-value V1–V5 |
| R18: Blind sample | Not built; task 1 stopped | Not run | OPEN quote-lint |
| R19: Tree-derived tasks | Not built; task 1 stopped | Not run | OPEN quote-lint |
| R20: Derived counts | Not built; task 1 stopped | Not run | OPEN quote-lint |
| R21: Cost estimates | Not built; task 1 stopped | Not run | OPEN quote-lint |
| R22: Unused reserved label | Not built; task 1 stopped | Not run | OPEN quote-lint |
| R23: Stage actions and three answers | Not built; task 1 stopped | Not run | OPEN quote-lint; OPEN-value V6 |
| R24: Number-fidelity principle and fixture hash | Not built; task 1 stopped | Not run | OPEN quote-lint; OPEN-value source-text |
| R25: Number-fidelity limits and audit | Not built; task 1 stopped | Not run | OPEN quote-lint; OPEN-value source-text |
| R26: Inspect-arrival record | Not built; task 1 stopped | Not run | OPEN quote-lint |
| R27: Wave 3 definitions and residuals | Not built; task 1 stopped | Not run | OPEN quote-lint; OPEN-value V7, source-text |
| R28: Closer/offer counts | Not built; task 1 stopped | Not run | OPEN quote-lint; OPEN-value source-text, walk-counts |
| R29: W3B2-7 question | Not built; task 1 stopped | Not run | OPEN quote-lint; OPEN-value V7, source-text |
| R30: Two inherited shapes | Not built; task 1 stopped | Not run | OPEN quote-lint; OPEN-value source-text, walk-counts |
| R31: Canonical alpha | Not built; task 1 stopped | Not run | OPEN quote-lint; OPEN-value V2 |
| R32: Fail-closed draft | Not built; task 1 stopped | Not run | OPEN quote-lint |
| R33: Session namespace | Not built; task 1 stopped | Not run | OPEN quote-lint |
| R34: Honest draft ownership | Not built; task 1 stopped | Not run | OPEN quote-lint |
| R35: Job shape, history, maintenance and scope | JobContract.test_outline | runner; all clauses listed below | Red: `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` |
| R36: Checkout pin and CP8 comment | JobContract.test_pin | floating-ref; all clauses listed below | Red: `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` |
| R37: Only the new job; no new external action | JobContract.test_boundary | secret; all clauses listed below | Red: `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` |
| R38: Every command, its own step and conditional output | JobContract.test_commands | command-05; all clauses listed below | Red: `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped`; OPEN-value regrade-flag; OPEN box-integration |
| R39: Exact private message | JobContract.test_private_message | private-message; all clauses listed below | Red: `test_ci_job: 13 run, 2 failures, 0 errors, 0 skipped` |
| R40: Local freeze check location | JobContract.test_freeze_location | freeze-comment; all clauses listed below | Red: `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` |
| R41: New local workflow binding | JobContract.test_local_binding | local-suite; all clauses listed below | Red: `test_ci_job: 13 run, 3 failures, 0 errors, 0 skipped`; repository suite owed to athena (PL-5(a)) |
| R42: Copy gate at build/freeze only | JobContract.test_copy_boundary | copy-after; all clauses listed below | Red: `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` |
| R43: Zero rule and nonzero records | JobContract.test_zero | empty-1; all clauses listed below | Red: `test_ci_job: 13 run, 2 failures, 0 errors, 0 skipped` |
| R44: Additive workflow and actual kickoff | JobContract.test_additions | removed-line; all clauses listed below | Red: `test_ci_job: 13 run, 2 failures, 0 errors, 0 skipped` |

All requirement tests above are in evals/gap-study-4/tests/test_ci_job.py. test_mutations asserts each named alteration is rejected by its specific clause. test_future_pin accepts no current ref and a later full 40-hex ref, including uppercase hex. test_absent_history creates a disposable repository with a fixed fake local identity and asserts a missing source commit fails loudly. No new test commits; the HOME-empty committing case remains covered by the passing pipeline file.

## Mutant table

Every row below ran the WHOLE 13-test file with only workflow text altered in memory by setUpModule. All exited 1 with AssertionError, zero errors and zero skips. No mutant workflow was written to disk or executed. These are mutations of this text contract's own inputs, not probes of a guard or sandbox.

| Clause | Mutant | Whole-file result and exact closing line | Test name |
|---|---|---|---|
| R35 | duplicate-job | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_outline; test_mutations |
| R35 | runner | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_outline; test_mutations |
| R35 | checkout | red — `test_ci_job: 13 run, 2 failures, 0 errors, 0 skipped` | JobContract.test_outline; test_mutations |
| R35 | python-action | red — `test_ci_job: 13 run, 2 failures, 0 errors, 0 skipped` | JobContract.test_outline; test_mutations |
| R35 | depth | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_outline; test_mutations |
| R35 | history-comment | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_outline; test_mutations |
| R35 | python-version | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_outline; test_mutations |
| R35 | maintenance | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_outline; test_mutations |
| R35 | gc | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_outline; test_mutations |
| R35 | step-comment | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_outline; test_mutations |
| R35 | job-condition | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_outline; test_mutations |
| R35 | step-condition | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_outline; test_mutations |
| R35 | ignored-exit | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_outline; test_mutations |
| R35 | interval-comment | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_outline; test_mutations |
| R36 | floating-ref | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_pin; test_mutations |
| R36 | ref-location | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_pin; test_mutations |
| R36 | publication-comment | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_pin; test_mutations |
| R37 | secret | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_boundary; test_mutations |
| R37 | permissions | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_boundary; test_mutations |
| R37 | extra-action | red — `test_ci_job: 13 run, 2 failures, 0 errors, 0 skipped` | JobContract.test_boundary; test_mutations |
| R39 | private-message | red — `test_ci_job: 13 run, 2 failures, 0 errors, 0 skipped` | JobContract.test_private_message; test_mutations |
| R39 | private-command | red — `test_ci_job: 13 run, 2 failures, 0 errors, 0 skipped` | JobContract.test_private_message; test_mutations |
| R40 | freeze-comment | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_freeze_location; test_mutations |
| R40 | freeze-command | red — `test_ci_job: 13 run, 2 failures, 0 errors, 0 skipped` | JobContract.test_freeze_location; test_mutations |
| R41 | local-suite | red — `test_ci_job: 13 run, 3 failures, 0 errors, 0 skipped` | JobContract.test_local_binding; test_mutations |
| R42 | copy-before | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_copy_boundary; test_mutations |
| R42 | copy-head | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_copy_boundary; test_mutations |
| R42 | copy-recent | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_copy_boundary; test_mutations |
| R42 | copy-empty | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_copy_boundary; test_mutations |
| R42 | copy-location | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_copy_boundary; test_mutations |
| R42 | copy-after | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_copy_boundary; test_mutations |
| R42 | copy-print | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_copy_boundary; test_mutations |
| R42 | copy-head-print | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_copy_boundary; test_mutations |
| R42 | copy-cleanup | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_copy_boundary; test_mutations |
| R42 | copy-extra | red — `test_ci_job: 13 run, 4 failures, 0 errors, 0 skipped` | JobContract.test_copy_boundary; test_mutations |
| R43 | zero-comment | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_zero; test_mutations |
| R44 | kickoff | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_additions; test_mutations |
| R44 | additive-assertion | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_additions; test_mutations |
| R38 | before-wrapper | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_commands; test_mutations |
| R38 | combined-steps | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_commands; test_mutations |
| R38 | extra-step | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_commands; test_mutations |
| R37 | push | red — `test_ci_job: 13 run, 3 failures, 0 errors, 0 skipped` | JobContract.test_boundary; test_mutations |
| R37 | gh | red — `test_ci_job: 13 run, 3 failures, 0 errors, 0 skipped` | JobContract.test_boundary; test_mutations |
| R37 | deploy | red — `test_ci_job: 13 run, 3 failures, 0 errors, 0 skipped` | JobContract.test_boundary; test_mutations |
| R37 | upload | red — `test_ci_job: 13 run, 3 failures, 0 errors, 0 skipped` | JobContract.test_boundary; test_mutations |
| R37 | release | red — `test_ci_job: 13 run, 3 failures, 0 errors, 0 skipped` | JobContract.test_boundary; test_mutations |
| R37 | network | red — `test_ci_job: 13 run, 3 failures, 0 errors, 0 skipped` | JobContract.test_boundary; test_mutations |
| R38 | command-01 | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_commands; test_mutations |
| R38 | command-02 | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_commands; test_mutations |
| R38 | command-03 | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_commands; test_mutations |
| R38 | command-04 | red — `test_ci_job: 13 run, 2 failures, 0 errors, 0 skipped` | JobContract.test_commands; test_mutations |
| R38 | command-05 | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_commands; test_mutations |
| R38 | command-06 | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_commands; test_mutations |
| R38 | command-07 | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_commands; test_mutations |
| R38 | command-08 | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_commands; test_mutations |
| R38 | command-09 | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_commands; test_mutations |
| R38 | command-10 | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_commands; test_mutations |
| R38 | command-11 | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_commands; test_mutations |
| R38 | command-12 | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_commands; test_mutations |
| R38 | command-13 | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_commands; test_mutations |
| R38 | command-14 | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_commands; test_mutations |
| R38 | command-15 | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_commands; test_mutations |
| R38 | after-1 | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_commands; test_mutations |
| R43 | empty-1 | red — `test_ci_job: 13 run, 2 failures, 0 errors, 0 skipped` | JobContract.test_zero; test_mutations |
| R38 | message-1 | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_commands; test_mutations |
| R38 | after-2 | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_commands; test_mutations |
| R43 | empty-2 | red — `test_ci_job: 13 run, 2 failures, 0 errors, 0 skipped` | JobContract.test_zero; test_mutations |
| R38 | message-2 | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_commands; test_mutations |
| R38 | after-3 | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_commands; test_mutations |
| R43 | empty-3 | red — `test_ci_job: 13 run, 2 failures, 0 errors, 0 skipped` | JobContract.test_zero; test_mutations |
| R38 | message-3 | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_commands; test_mutations |
| R38 | after-4 | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_commands; test_mutations |
| R43 | empty-4 | red — `test_ci_job: 13 run, 2 failures, 0 errors, 0 skipped` | JobContract.test_zero; test_mutations |
| R38 | message-4 | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_commands; test_mutations |
| R38 | after-5 | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_commands; test_mutations |
| R43 | empty-5 | red — `test_ci_job: 13 run, 2 failures, 0 errors, 0 skipped` | JobContract.test_zero; test_mutations |
| R38 | message-5 | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_commands; test_mutations |
| R37 | trigger | red — `test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped` | JobContract.test_boundary; test_mutations |
| R44 | removed-line | red — `test_ci_job: 13 run, 2 failures, 0 errors, 0 skipped` | JobContract.test_additions; test_mutations |

The exact invocations for those whole-file runs were:

```bash
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant duplicate-job
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant runner
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant checkout
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant python-action
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant depth
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant history-comment
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant python-version
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant maintenance
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant gc
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant step-comment
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant job-condition
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant step-condition
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant ignored-exit
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant interval-comment
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant floating-ref
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant ref-location
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant publication-comment
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant secret
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant permissions
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant extra-action
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant private-message
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant private-command
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant freeze-comment
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant freeze-command
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant local-suite
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant copy-before
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant copy-head
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant copy-recent
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant copy-empty
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant copy-location
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant copy-after
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant copy-print
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant copy-head-print
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant copy-cleanup
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant copy-extra
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant zero-comment
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant kickoff
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant additive-assertion
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant before-wrapper
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant combined-steps
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant extra-step
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant push
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant gh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant deploy
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant upload
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant release
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant network
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant command-01
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant command-02
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant command-03
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant command-04
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant command-05
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant command-06
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant command-07
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant command-08
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant command-09
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant command-10
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant command-11
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant command-12
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant command-13
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant command-14
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant command-15
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant after-1
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant empty-1
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant message-1
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant after-2
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant empty-2
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant message-2
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant after-3
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant empty-3
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant message-3
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant after-4
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant empty-4
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant message-4
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant after-5
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant empty-5
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant message-5
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant trigger
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant removed-line
```

The initial red job contract was run twice before its commit, both with the same closing line:

```text
FAILED (failures=3)
test_ci_job: 13 run, 3 failures, 0 errors, 0 skipped
```

After adding the job, the first run exposed a defect in the checker's mutation witness: the extra-copy clause was only evaluated when a unique copy step had already been selected. Its closing line was test_ci_job: 13 run, 1 failures, 0 errors, 0 skipped. Moving the occurrence count outside that branch made the extra-copy alteration hit its own clause. The final 79 whole-file runs include that correction.

## Gates, commands and closing lines

These final gates ran after git add on the exact code tree committed as 91b8f0ee2a5d46f6b1556bd801101c485387a25e. No code changed after them. Base means the clean starting commit. No test below was skipped by a runner. “Not run” below identifies an unfinished or forbidden lane operation, not a skipped unittest.

### tests/test_ci_job.py

```bash
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py
```

Head tree (exit 0):

```text
Ran 13 tests in 0.384s

OK
test_ci_job: 13 run, 0 failures, 0 errors, 0 skipped
```

### copy_manifest.py --check

```bash
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/copy_manifest.py --check
```

Base (exit 0):

```text
ok: 218 files from 27 fragment(s) (w1a-cp1-scaffold, w1b-cp1-routing-batch, w2a-cp3-endstate, w2b-cp3-text-graders, w3a-cp3-graders-scope-template, w3b-cp3-graders-refusal-plangate, w3c-cp3-graders-confound-newtasks, w4a-cp2-image-egress, w4b-cp2-runtake-preflight, w4c-cp2-sidecar-scan, w4d-cp4-variants, w4e-cp5-stats, w4f-cp5-coverage, w4g-cp4-declarations-eligibility, w4h-w1b-next-touch, w4i-cp4-task-scope-read, w4j-cp4-task-template-adherence, w4k-cp4-task-number-fidelity, w4l-cp4-task-precondition-refusal, w4m-cp4-gen-plan-gate, w4n-cp4-gen-confounded-seed2, w4o-cp4-gen-explain-not-act, w4p-cp4-gen-approval-scope, w4q-cp4-gen-conditional-yes, w5a-cp5-probes4, w5b-cp5-pipeline, wave4-merge): 40 identical and 13 edited (round 3 at e2979b31, shared files at 68ec902f), 165 new; 5 fixture builders byte-identical; 8 frozen paths unchanged since 68ec902f63bf
```

Head tree (exit 0):

```text
ok: 221 files from 28 fragment(s) (w1a-cp1-scaffold, w1b-cp1-routing-batch, w2a-cp3-endstate, w2b-cp3-text-graders, w3a-cp3-graders-scope-template, w3b-cp3-graders-refusal-plangate, w3c-cp3-graders-confound-newtasks, w4a-cp2-image-egress, w4b-cp2-runtake-preflight, w4c-cp2-sidecar-scan, w4d-cp4-variants, w4e-cp5-stats, w4f-cp5-coverage, w4g-cp4-declarations-eligibility, w4h-w1b-next-touch, w4i-cp4-task-scope-read, w4j-cp4-task-template-adherence, w4k-cp4-task-number-fidelity, w4l-cp4-task-precondition-refusal, w4m-cp4-gen-plan-gate, w4n-cp4-gen-confounded-seed2, w4o-cp4-gen-explain-not-act, w4p-cp4-gen-approval-scope, w4q-cp4-gen-conditional-yes, w5a-cp5-probes4, w5b-cp5-pipeline, w5c-draft-ci, wave4-merge): 40 identical and 13 edited (round 3 at e2979b31, shared files at 68ec902f), 168 new; 5 fixture builders byte-identical; 8 frozen paths unchanged since 68ec902f63bf
```

### tests/test_scaffold.py

```bash
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_scaffold.py
```

Base (exit 0):

```text
Ran 49 tests in 243.384s

OK
```

Head tree (exit 0):

```text
Ran 49 tests in 241.382s

OK
```

### tests/test_pipeline.py

```bash
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_pipeline.py
```

Base (exit 0):

```text
Ran 85 tests in 24.805s

OK
test_pipeline: 85 run, 0 failures, 0 errors, 0 skipped
```

Head tree (exit 0):

```text
Ran 85 tests in 22.987s

OK
test_pipeline: 85 run, 0 failures, 0 errors, 0 skipped
```

### tests/test_stats.py

```bash
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_stats.py
```

Head tree (exit 0):

```text
Ran 98 tests in 4.891s

OK
```

### tests/test_batch.py

```bash
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_batch.py
```

Head tree (exit 0):

```text
Ran 118 tests in 2.336s

OK
```

### tests/test_pause_adherence.py

```bash
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_pause_adherence.py
```

Head tree (exit 0):

```text
Ran 30 tests in 2.274s

OK
```

### test_round4.module_problems()

```bash
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore -c "import sys; sys.path.insert(0, '/Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4'); import test_round4; p = test_round4.module_problems(); print(p); raise SystemExit(1 if p else 0)"
```

Head tree (exit 0):

```text
[]
```

### lint_language.py evals/gap-study-4/

```bash
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/lint_language.py evals/gap-study-4/
```

Base (exit 1):

```text
25 finding(s) across 59 input(s):
Fix the text, or excuse the exact line in language-allowlist.json with a reason.
```

Head tree (exit 1):

```text
25 finding(s) across 60 input(s):
Fix the text, or excuse the exact line in language-allowlist.json with a reason.
```

### lint_pooling.py evals/gap-study-4/

```bash
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/lint_pooling.py evals/gap-study-4/
```

Base (exit 1):

```text
8 finding(s) across 59 file(s) and 0 commit(s):
There is no allowlist for these. Write the sentence a different way.
```

Head tree (exit 1):

```text
8 finding(s) across 60 file(s) and 0 commit(s):
There is no allowlist for these. Write the sentence a different way.
```

### leak_grep.py --check

```bash
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/leak_grep.py --check
```

Head tree (exit 1):

```text
no pre-registration: neither prereg.json nor prereg-draft.json exists. Nothing in this study can be read without it.
```

### Unrun gates and the quote reproduction

tests/test_build_draft.py and build_draft.py --check were not run as final gates: task 1 stopped before its implementation and generated draft existed. Running the inherited builder would not verify a lane deliverable. Their two checks.d commands were consequently not added. The checks file contains the working task 2 command only; OPEN checks-list records the remaining section 5 obligation.

The full test_round4.py, run_checks.py, tests/run_tests.py and every whole-file audit are owed to glitch-f3 on athena. They were not run on the Mac. The permitted module_problems() substitute returned [] as recorded above. freeze_rehearsal.py itself, the freeze, ledger/ruling doors in W, model calls, walks and every --against invocation were not run.

leak_grep.py --check ran exactly once, without expecting a pass. It accepts no path argument (main, lines 115–119). Because task 1 produced no draft, it stopped before reaching its zero-session report; the exact actual closing line is above. No result for a real box transcript is claimed.

The exact in-memory quote check used before any edit was:

```bash
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore - <<'PY'
import json, sys
sys.path.insert(0, '/Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4')
import lint_language as ll
import lint_pooling as lp
rel = 'evals/gap-study-4/prereg-draft.json'
quotes = {
    'R4 plan 210': 'Counts with exact Clopper-Pearson 95% bounds per half-cell, rounded outward (lane E1\'s method); never a rate in a headline.',
    'R10 plan 140': "Round 4 is a fresh baseline: it is never compared with or pooled with round 3, or with any earlier round (the study's `not_poolable` rule), so it needs no bridge back to them (D3, decided).",
}
for requirement, quote in quotes.items():
    text = json.dumps({'source': requirement, 'quote': quote}, indent=2, ensure_ascii=False)
    language = ll.scan_text(text, rel, ll.load_allowlist())
    pooling = lp.scan_text(text, rel)
    print(requirement + ': ' + json.dumps({'language': [f['pattern'] for f in language], 'pooling': [f['pattern'] for f in pooling]}))
    assert language or pooling
print('quoted requirements: 2 of 2 rejected by unchanged mandatory linters; no file written')
PY
```

The base and head lint finding bodies were compared in memory and were identical after removing light-ok's changing load line and accounting for the input count changing from 59 to 60. No exception was added to either linter.

## Decisions, readings and remaining interfaces

This lane's own implementation choices:

- Append the one job at the end of ci.yml, preserving every existing byte and avoiding edits to siblings.
- Use a stdlib text contract tailored to the job's shape. It validates commands and their surrounding branches; it is not a general YAML parser or an Actions execution.
- Add a record-count check inside each after-freeze step, before its command. check_results, result and completeness otherwise can return 0 while printing that no records were measured; R43 requires these CI steps to fail at zero after the freeze. The check reads this round's stats.load_results.
- Keep a freeze worktree at RUNNER_TEMP/frozen-tree, print the checked commit in both branches, reject an empty freeze ref, and remove the worktree using an EXIT trap. These commands were written as workflow text only.
- Reject job/step conditions, ignored exits, custom shell and working-directory changes that could defeat the specified command steps.
- Keep only the completed task 2 command in checks.d pending the stopped draft work. That is an explicit incomplete obligation, OPEN checks-list, not a ruling changing section 5.
- The real repository is read only to bind the named baseline blob and introducing commit, as R44 requires. The failure case creates its own scratch repository with a fixed fake local identity. No new test commits, so no new HOME-empty committing test is needed; the prescribed pipeline file's existing HOME-empty case passed.

No slot or half_cell id scheme was selected. No draft pending map or keys were constructed. No owner approval, reaffirmation, price, real version, digest or study wording was supplied.

The brief's reading of plan 299 (reuse maintenance.auto=false and gc.auto=0 because scratch repositories are used) is implemented and labelled in the job comment. The validity-probes lines are mirrored by probes4.py --check. The sibling intervals job is byte-identical; this round's intervals remain stats.py's, with publication at CP8.

The brief's reading of R7, “per version” as one v4 version per task, remains a future task 1 requirement; no digests or words were read or generated here.

The named scripts' argument parsers were read before writing their steps. check_results.py accepts --check, --ledger and --rehearsal-plan, not --regrade. No alternative flag was substituted. tests/test_box_integration.py and holdout.py are absent at this head. The box command remains in the job. The private step prints only its specified message; it does not claim to have run its local check.

## OPEN items

OPEN: quote-lint: How should the exact required R4 plan 210 quotation and R10 plan 140 quotation coexist with section 8's mandatory lint gates, given section 5 excludes both lint modules and language-allowlist.json and section 3.1 preserves their bytes? PL-4 rules on leak words only. A named ruling is needed before task 1 resumes.

OPEN: baseline-lints: The clean base and code head both have the same 25 language and 8 pooling findings. Section 8 requires them reported, section 5 bars this lane from fixing their files, and section 9's done condition requires green gates. The findings need an owned later touch or a ruling; none was inferred here.

OPEN: checks-list: Section 5 requires test_build_draft.py and build_draft.py --check alongside test_ci_job.py in this lane's checks file. The first two await the stopped task 1. Add them with that implementation and generated draft; this head intentionally contains only the runnable CI contract.

OPEN: box-integration: R38/plan 1013–1036 retains tests/test_box_integration.py, absent at this head and outside section 5. Its owner must land the file before CI can pass.

OPEN: athena-gates: Section 8 gate 9 and PL-5(a)/R41 owe test_round4.py, run_checks.py and tests/run_tests.py to glitch-f3's athena run on this head. No whole suite or whole-file audit ran on the Mac.

## OPEN-value items

The draft interfaces below remain unbuilt because task 1 stopped. These entries record the brief's missing inputs; they do not imply a PENDING mechanism or a placeholder draft was committed.

OPEN-value: V1: stats_design.stronger_weaker for Claude Code needs the weaker model chosen by glitch-f3; CP5-req 60–61, stats.py 474–480, section 0b V1.

OPEN-value: V2: stats_design.alpha needs glitch-f3's chosen value; CP5-req 194 and section 0b V2. Its writer must enforce the shortest spelling when task 1 resumes.

OPEN-value: V3: stats_design.bootstrap seed and reps need glitch-f3; stats.py 421, 488–491 and section 0b V3.

OPEN-value: V4: stats_design.power seed, sims, bootstrap_reps and grid need glitch-f3; stats.py 422–423, 492–501 and section 0b V4. wordings and repeats must come from variants, not a value chosen here.

OPEN-value: V5: stats_design.floors needs the probes floor text from glitch-f3; stats.py 502–505, 619 and section 0b V5. The future default is null as ruled, not an invented floor.

OPEN-value: V6: Answers to R23's three questions need glitch-f3; CP5-req 92–95, 146 and section 0b V6.

OPEN-value: V7: scope_read's documented reply, plan_gate's two answers and W3B2-7's answer need glitch-f3; CP5-req 151, 153, 173 and section 0b V7.

OPEN-value: V8: Each of the eleven round 3 limitations needs its round_4_reading from glitch-f3; plan 830 and section 0b V8.

OPEN-value: source-text: R24, R25, R27, R28, R29 and R30 require verbatim CP5-req 101–120, 122–139, 149–160, 162–169, 171–173 and 175–182 text, but the brief gives descriptions or partial quotes instead of all of those passages. The external sources are forbidden to this lane. glitch-f3 must supply the missing exact text, especially the offer phrase set, W3B2-7's question, the counting rule and the two shapes. No text was invented or fetched.

OPEN-value: pins: R6/R14 need measured image lock pins, harness versions and the matching routing pin_profiles from the box/walk owners; plan 828 and CP5-req 43, 49. No real version was chosen.

OPEN-value: digests: holdout_salted_digests needs only the separate author's published salted digest values through glitch-f3; R7/plan 175, 829. No private wording, path or salt was read, named, guessed or generated.

OPEN-value: preflight: R8's conditional child-process token finding needs the actual box preflight; plan 830 and CP6. No finding was invented.

OPEN-value: first-walk: R9 checked_against needs the first committed real box session; plan 831, PL-4(b). This head has no draft and the one leak check stopped before reading sessions.

OPEN-value: instrument-values: R15's renderable config hashes, explicit default effort values, served-model rules, dated price_table and per-harness furniture need the corresponding CP2 owners, pinned-version walks and Javier; CP5-req 50–56. No price or value was supplied from memory.

OPEN-value: walk-counts: R28/R30 closer/offer and inherited-shape counts await Javier's CP6 walks; CP5-req 162–169 and 175–182. They must remain null in the future draft until measured.

OPEN-value: regrade-flag: R38/plan 1036 requires check_results.py --regrade, which check_results.py 542–544 does not accept. The job retains the exact command. Its owner must implement the flag or glitch-f3 must rule on dropping the line.

## OPEN carries for other lanes

OPEN: routing: R6/R12/R15 and section 7 carry routing.json pin_profiles and the missing Codex/Gemini rate-limit and spend-cap marker entries to the routing/adapters owners. This lane did not edit routing.json.

OPEN: driver-keys: Section 4.3 carries driver_constants, driver_change, rehearsal_reasons, budgets, run_location, system_under_test, source_by_fixture_kind, harness_delivered_user_records, environment_record and driver_outcome_shapes to CP2's drive-step owners. The current drive.py line 225 uses (prereg.load().get("driver_constants") or {}).get("stripped_env") or (), so a later draft without those keys permits import with an empty stripping list. That default-open read needs CP2's owned closure. No driver key was invented here.

OPEN: per-axis-order: R3/plan 174 and section 4.3 carry prereg.py --order to its next owner. The inherited per-axis positive/control order is not freeze.planned_order's round 4 whole-row order.

## Deferred to Javier

The walks, real box, keys, prices, real versions, caps-trimmed record, spend, public pushes, the push word that lands the job on main at CP8, and Javier's word on any ruling remain deferred. No such action occurred. The real freeze and rehearsal remain CP6 work; the final sha pin and publication remain CP8 work. The number_fidelity field-set closure remains its next owned touch (section 7, CP5-req 184–189).

## Refusals and limits

No classifier block, sandbox denial, automatic approval rejection or hook refusal occurred. No retry or workaround of such a denial occurred. The deliberate negative cases are the mutation assertions, empty scratch history, the in-memory quote rejection and the reported script failures.

The one real leak command stopped with the exact no-pre-registration message recorded above. The two existing lints returned 1 as at the base. No new test was skipped. This head is not represented as fully green or ready to freeze. The remaining work and every unresolved value are named above.
