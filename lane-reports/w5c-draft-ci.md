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

## Resume from a0cd341: section 10 rulings

status: stopped
RESUME HERE: glitch-f3 rules OPEN quote-lint for R10 versus lint_pooling.py's absent excusal path; then resume task 1.
head: 8bd75c85720931020af1c4ca8e982e386ccd49e0 (last code commit; the append-only report commit follows it)

Recorded after reading date: 2026-10-09 20:07:46 EDT.

This appendix is the current disposition. Everything above is preserved as the earlier handoff; its historical OPEN entries are updated below, not erased. The original first two lines remain unchanged as instructed. Task 1 resumed with the new rulings, but stopped before edits because w5c-2 cannot make the required R10 quotation pass the unchanged pooling linter. Task 2's independent box-integration ruling is implemented and green. No draft or owner-value mechanism was built, and this is not a completed lane.

### Start and commits on this resume

The resume-head check found exactly a0cd341dbd82454ed4d4d41c0b6ac169ead8f461 on gap4/w5c-draft-ci, with an empty status including ignored paths. All four named old commits were present. core.hooksPath had no value and was left unchanged. The start block's remaining closing output was:

```text
commit
commit
commit
commit
hooksPath read
light ok: load1 2.82 < 16.00 (memory pressure unreadable; light does not need it)
light-ok exit 0
Python 3.13.2
```

The user's resume instruction replaces only the old base-HEAD equality check. The base readings already recorded above were retained, not repeated on a falsely labelled base. CLAUDE.md was read again. No external source, sealed path, login file, private wording or other lane's worktree was read. No sub-agent was spawned.

The visible red-then-green history is:

- 0f124a787dacbce90bd0a5e0db28758889a87934: added JobContract.test_box_ownership while the old box step remained; the whole file failed by assertion, with closing line `test_ci_job: 14 run, 1 failures, 0 errors, 0 skipped`. The staged copy gate passed.
- 8bd75c85720931020af1c4ca8e982e386ccd49e0: omitted that step until CP2's file exists, recorded its owner and ruling, and bound both presence states in the text contract. The whole file passes, and all 83 whole-file mutations fail by assertion.
- The separate report commit appends this evidence. Neither earlier commit was amended or rewritten; both used git commit -F with a system-temp message file and the exact Codex trailer. No hook was changed or refused a commit.

Actual diff at the last code commit, before this appendix:

```text
.github/workflows/ci.yml                     | 124 ++++++
 evals/gap-study-4/COPIED.d/w5c-draft-ci.json |  20 +
 evals/gap-study-4/checks.d/w5c-draft-ci.txt  |   4 +
 evals/gap-study-4/tests/test_ci_job.py       | 471 ++++++++++++++++++++
 lane-reports/w5c-draft-ci.md                 | 616 +++++++++++++++++++++++++++
 5 files changed, 1235 insertions(+)
124	0	.github/workflows/ci.yml
```

Only .github/workflows/ci.yml and evals/gap-study-4/tests/test_ci_job.py changed on this resume before the report. The workflow's net change against 89b54db4 is 124 added lines and zero removed lines; the two omission comments replace three lines added by this lane's earlier commit, as the new ruling directs. All sibling jobs and the on: block remain byte-identical to the base.

PL-1 changes to wave 1 files, line by line: none. study.py lines 14 and 56, tests/test_scaffold.py lines 40 and 475, and the build_draft.py/study.py claims in w1a's fragment remain unchanged. build_draft.py, language-allowlist.json and both linter modules also remain unchanged. No new file was added under evals/gap-study-4, so the existing copy fragment still claims the three task 2 files correctly.

### Why the new quote ruling does not complete task 1

The allowlist format CAN hold an exact, cited line: lint_language.excused compares file, pattern and exact line text. The in-memory R4 entry removes its percentage finding, and a one-word change to that quotation brings the finding back.

However, lint_pooling.scan_text accepts only text and path. It reads its own patterns and never reads language-allowlist.json. Its main function likewise calls scan_text without an excusal mechanism. R10's exact required sentence still produces `pooled` even when the two w5c-2 entries are supplied to the language linter's loader in memory. This is a new finding, not one of the 8 baseline pooling findings. w5c-2 explicitly preserves both lint modules, and baseline-lints permits no finding beyond the base. No authorized edit can reconcile those facts here.

This is a construction/quotation check, not a guard-evasion probe. It neither writes a draft nor edits a linter or allowlist. Its exact command and output were:

```bash
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore - <<'PY'
import json, sys
from unittest.mock import patch
sys.path.insert(0, '/Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4')
import lint_language as ll
import lint_pooling as lp
rel = 'evals/gap-study-4/prereg-draft.json'
quotes = [
    ('R4 plan 210', "Counts with exact Clopper-Pearson 95% bounds per half-cell, rounded outward (lane E1's method); never a rate in a headline.", 'percentage'),
    ('R10 plan 140', "Round 4 is a fresh baseline: it is never compared with or pooled with round 3, or with any earlier round (the study's `not_poolable` rule), so it needs no bridge back to them (D3, decided).", 'pooled'),
]
entries = ll.load_allowlist() + [
    {'file': rel, 'pattern': pattern, 'line_text': json.dumps(quote, ensure_ascii=False),
     'ruled': 'glitch-f3, section 10, w5c-2', 'why': source}
    for source, quote, pattern in quotes
]
for source, quote, pattern in quotes:
    line = json.dumps(quote, ensure_ascii=False)
    with patch.object(ll, 'load_allowlist', return_value=entries):
        language = [f['pattern'] for f in ll.scan_text(line, rel, ll.load_allowlist())]
        pooling = [f['pattern'] for f in lp.scan_text(line, rel)]
    print(source + ': ' + json.dumps({'language': language, 'pooling': pooling}))
    assert language == []
    assert pooling == (['pooled'] if pattern == 'pooled' else [])
changed = json.dumps(quotes[0][1].replace('Counts', 'Figures'), ensure_ascii=False)
assert [f['pattern'] for f in ll.scan_text(changed, rel, entries)] == ['percentage']
print('proposed exact entries: 1 of 2 quotations still rejected; R4 one-word change rejected; no file written')
PY
```

```text
light ok: load1 3.61 < 16.00 (memory pressure unreadable; light does not need it)
R4 plan 210: {"language": [], "pooling": []}
R10 plan 140: {"language": [], "pooling": ["pooled"]}
proposed exact entries: 1 of 2 quotations still rejected; R4 one-word change rejected; no file written
```

OPEN: quote-lint: Section 10 w5c-2 authorizes exactly two entries in language-allowlist.json and no lint-module change, but R10/plan 140's verbatim sentence is rejected by lint_pooling.py, which has no allowlist path (scan_text and main). Section 10 baseline-lints rejects new findings. What named change permits that exact R10 sentence while retaining a binding pooling gate? Task 1 stopped under section 9; no encoded wording, changed quotation, widened entry or lint bypass was attempted.

The committed w5c-2 one-word/widened-entry tests and the two allowlist entries remain unbuilt with task 1. The in-memory R4 evidence above is not represented as their completion. V1–V8 and all previously listed OPEN-value inputs remain unfilled; no mechanism for them is falsely claimed.

### Task 2 change and this lane's decisions

The job omits tests/test_box_integration.py while the file is absent, with these exact comments:

```yaml
      # CP2 owns tests/test_box_integration.py; omitted until it exists
      # under glitch-f3's section 10 box-integration ruling.
```

This lane's implementation choices:

- Determine the command's presence requirement from the owned test file's existence at runtime. The original PLAN_COMMANDS tuple retains the plan's verbatim command; the effective list excludes only that command while its file is absent.
- Require both the CP2 ownership comment and the named ruling comment while omitting the step. Reject an active invocation while the file is absent.
- Pass fake file-presence states as in-memory arguments to the text checker. With the file present, the missing command is an assertion failure; with both file and command present, the text contract passes. No fake file is written into W.
- Arm the whole-file box-landed input only in setUpModule and clear it in tearDownModule. No import-time patch or guard was added.
- Stop YAML literal run text at a dedented nonblank line. The new job-level comments exposed that the previous reader included trailing comments in the preceding shell body. The box-indented mutation proves that moving those comments into that body is rejected.
- Retain the prior row/half-cell and pending-map non-decisions: none were selected or constructed because task 1 stopped before implementation. The brief's R7 reading remains unimplemented. The brief's plan 299 reading and unchanged intervals job remain as documented in the first report.
- Keep the checks file's existing task 2 command. Section 10 checks-list authorizes adding both task 1 commands together with task 1; neither nonexistent deliverable is claimed by this head.

No workflow, CI service, model, vendor CLI, container, freeze, rehearsal, ledger/ruling write, --against run or whole suite was invoked. The --regrade command remains as the plan spells it, with its prior OPEN-value dependency.

### Current requirement disposition

The original R1–R44 table remains above as historical evidence. The following table updates every row for this resumed head. Task 1 rows are incomplete because of the named conflict, not waived. OPEN-value ids and exact source lines remain as recorded above.

| Requirement | Current test or disposition | Mutant / red evidence | Remaining item |
|---|---|---|---|
| R1 | Not built; task 1 stopped before edits | No implementation or committed mutant claimed | OPEN quote-lint; applicable OPEN-value dependencies retained above |
| R2 | Not built; task 1 stopped before edits | No implementation or committed mutant claimed | OPEN quote-lint; applicable OPEN-value dependencies retained above |
| R3 | Not built; task 1 stopped before edits | No implementation or committed mutant claimed | OPEN quote-lint; applicable OPEN-value dependencies retained above |
| R4 | Not built; task 1 stopped before edits | No implementation or committed mutant claimed | OPEN quote-lint; applicable OPEN-value dependencies retained above |
| R5 | Not built; task 1 stopped before edits | No implementation or committed mutant claimed | OPEN quote-lint; applicable OPEN-value dependencies retained above |
| R6 | Not built; task 1 stopped before edits | No implementation or committed mutant claimed | OPEN quote-lint; applicable OPEN-value dependencies retained above |
| R7 | Not built; task 1 stopped before edits | No implementation or committed mutant claimed | OPEN quote-lint; applicable OPEN-value dependencies retained above |
| R8 | Not built; task 1 stopped before edits | No implementation or committed mutant claimed | OPEN quote-lint; applicable OPEN-value dependencies retained above |
| R9 | Not built; task 1 stopped before edits | No implementation or committed mutant claimed | OPEN quote-lint; applicable OPEN-value dependencies retained above |
| R10 | Not built; task 1 stopped before edits | No implementation or committed mutant claimed | OPEN quote-lint; applicable OPEN-value dependencies retained above |
| R11 | Not built; task 1 stopped before edits | No implementation or committed mutant claimed | OPEN quote-lint; applicable OPEN-value dependencies retained above |
| R12 | Not built; task 1 stopped before edits | No implementation or committed mutant claimed | OPEN quote-lint; applicable OPEN-value dependencies retained above |
| R13 | Not built; task 1 stopped before edits | No implementation or committed mutant claimed | OPEN quote-lint; applicable OPEN-value dependencies retained above |
| R14 | Not built; task 1 stopped before edits | No implementation or committed mutant claimed | OPEN quote-lint; applicable OPEN-value dependencies retained above |
| R15 | Not built; task 1 stopped before edits | No implementation or committed mutant claimed | OPEN quote-lint; applicable OPEN-value dependencies retained above |
| R16 | Not built; task 1 stopped before edits | No implementation or committed mutant claimed | OPEN quote-lint; applicable OPEN-value dependencies retained above |
| R17 | Not built; task 1 stopped before edits | No implementation or committed mutant claimed | OPEN quote-lint; applicable OPEN-value dependencies retained above |
| R18 | Not built; task 1 stopped before edits | No implementation or committed mutant claimed | OPEN quote-lint; applicable OPEN-value dependencies retained above |
| R19 | Not built; task 1 stopped before edits | No implementation or committed mutant claimed | OPEN quote-lint; applicable OPEN-value dependencies retained above |
| R20 | Not built; task 1 stopped before edits | No implementation or committed mutant claimed | OPEN quote-lint; applicable OPEN-value dependencies retained above |
| R21 | Not built; task 1 stopped before edits | No implementation or committed mutant claimed | OPEN quote-lint; applicable OPEN-value dependencies retained above |
| R22 | Not built; task 1 stopped before edits | No implementation or committed mutant claimed | OPEN quote-lint; applicable OPEN-value dependencies retained above |
| R23 | Not built; task 1 stopped before edits | No implementation or committed mutant claimed | OPEN quote-lint; applicable OPEN-value dependencies retained above |
| R24 | Not built; task 1 stopped before edits | No implementation or committed mutant claimed | OPEN quote-lint; applicable OPEN-value dependencies retained above |
| R25 | Not built; task 1 stopped before edits | No implementation or committed mutant claimed | OPEN quote-lint; applicable OPEN-value dependencies retained above |
| R26 | Not built; task 1 stopped before edits | No implementation or committed mutant claimed | OPEN quote-lint; applicable OPEN-value dependencies retained above |
| R27 | Not built; task 1 stopped before edits | No implementation or committed mutant claimed | OPEN quote-lint; applicable OPEN-value dependencies retained above |
| R28 | Not built; task 1 stopped before edits | No implementation or committed mutant claimed | OPEN quote-lint; applicable OPEN-value dependencies retained above |
| R29 | Not built; task 1 stopped before edits | No implementation or committed mutant claimed | OPEN quote-lint; applicable OPEN-value dependencies retained above |
| R30 | Not built; task 1 stopped before edits | No implementation or committed mutant claimed | OPEN quote-lint; applicable OPEN-value dependencies retained above |
| R31 | Not built; task 1 stopped before edits | No implementation or committed mutant claimed | OPEN quote-lint; applicable OPEN-value dependencies retained above |
| R32 | Not built; task 1 stopped before edits | No implementation or committed mutant claimed | OPEN quote-lint; applicable OPEN-value dependencies retained above |
| R33 | Not built; task 1 stopped before edits | No implementation or committed mutant claimed | OPEN quote-lint; applicable OPEN-value dependencies retained above |
| R34 | Not built; task 1 stopped before edits | No implementation or committed mutant claimed | OPEN quote-lint; applicable OPEN-value dependencies retained above |
| R35 | JobContract.test_outline | runner: `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` | Built; earlier detailed clause accounting retained |
| R36 | JobContract.test_pin | floating-ref: `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` | Built; earlier detailed clause accounting retained |
| R37 | JobContract.test_boundary | secret: `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` | Built; earlier detailed clause accounting retained |
| R38 | JobContract.test_commands, test_box_ownership, test_box_transition | box-landed: `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` | OPEN-value regrade-flag; box omission ruled and implemented |
| R39 | JobContract.test_private_message | private-message: `test_ci_job: 15 run, 2 failures, 0 errors, 0 skipped` | Built; earlier detailed clause accounting retained |
| R40 | JobContract.test_freeze_location | freeze-comment: `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` | Built; earlier detailed clause accounting retained |
| R41 | JobContract.test_local_binding | local-suite: `test_ci_job: 15 run, 3 failures, 0 errors, 0 skipped` | Repository suite owed to athena under PL-5(a) and section 10 |
| R42 | JobContract.test_copy_boundary | copy-after: `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` | Built; earlier detailed clause accounting retained |
| R43 | JobContract.test_zero | empty-1: `test_ci_job: 15 run, 2 failures, 0 errors, 0 skipped` | Built; earlier detailed clause accounting retained |
| R44 | JobContract.test_additions | removed-line: `test_ci_job: 15 run, 2 failures, 0 errors, 0 skipped` | Built; earlier detailed clause accounting retained |

### New clause mutants and whole-file results

All mutation inputs are in memory and the complete test_ci_job.py file ran each time. No test was skipped and every red was an assertion failure, not an import or execution error. The first four mutations are also asserted by test_mutations; test_box_transition asserts the future-file failure as well as both accepted presence states.

| Clause | Mutation | Binding test | Whole-file closing line |
|---|---|---|---|
| R38.box-owner | box-owner | JobContract.test_commands; test_box_ownership | `test_ci_job: 15 run, 2 failures, 0 errors, 0 skipped` |
| R38.box-ruling | box-ruling | JobContract.test_commands; test_box_ownership | `test_ci_job: 15 run, 2 failures, 0 errors, 0 skipped` |
| R38.box-absent | box-premature | JobContract.test_commands; test_box_ownership | `test_ci_job: 15 run, 2 failures, 0 errors, 0 skipped` |
| Literal body ends on dedent / R44.step | box-indented | JobContract.test_additions; test_commands | `test_ci_job: 15 run, 2 failures, 0 errors, 0 skipped` |
| CP2 file present requires its command | box-landed | JobContract.test_commands; test_box_transition | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |

For each name below, the exact invocation was the following command with NAME replaced by that row's literal name. Each invocation separately ran light-ok immediately before the one test process. The pre-existing command-05 mutation is absent because its command is now deliberately omitted; the future-file obligation is box-landed. All other earlier mutations were repeated because the command-list and run-block reader changed.

```bash
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py --mutant NAME
```

| NAME | Exit | Exact closing line |
|---|---|---|
| duplicate-job | 1 (assertion red) | `test_ci_job: 15 run, 2 failures, 0 errors, 0 skipped` |
| runner | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| checkout | 1 (assertion red) | `test_ci_job: 15 run, 2 failures, 0 errors, 0 skipped` |
| python-action | 1 (assertion red) | `test_ci_job: 15 run, 2 failures, 0 errors, 0 skipped` |
| depth | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| history-comment | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| python-version | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| maintenance | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| gc | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| step-comment | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| job-condition | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| step-condition | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| ignored-exit | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| interval-comment | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| floating-ref | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| ref-location | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| publication-comment | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| secret | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| permissions | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| extra-action | 1 (assertion red) | `test_ci_job: 15 run, 2 failures, 0 errors, 0 skipped` |
| private-message | 1 (assertion red) | `test_ci_job: 15 run, 2 failures, 0 errors, 0 skipped` |
| private-command | 1 (assertion red) | `test_ci_job: 15 run, 2 failures, 0 errors, 0 skipped` |
| freeze-comment | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| freeze-command | 1 (assertion red) | `test_ci_job: 15 run, 2 failures, 0 errors, 0 skipped` |
| local-suite | 1 (assertion red) | `test_ci_job: 15 run, 3 failures, 0 errors, 0 skipped` |
| copy-before | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| copy-head | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| copy-recent | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| copy-empty | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| copy-location | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| copy-after | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| copy-print | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| copy-head-print | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| copy-cleanup | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| copy-extra | 1 (assertion red) | `test_ci_job: 15 run, 4 failures, 0 errors, 0 skipped` |
| zero-comment | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| kickoff | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| additive-assertion | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| box-owner | 1 (assertion red) | `test_ci_job: 15 run, 2 failures, 0 errors, 0 skipped` |
| box-ruling | 1 (assertion red) | `test_ci_job: 15 run, 2 failures, 0 errors, 0 skipped` |
| box-premature | 1 (assertion red) | `test_ci_job: 15 run, 2 failures, 0 errors, 0 skipped` |
| box-indented | 1 (assertion red) | `test_ci_job: 15 run, 2 failures, 0 errors, 0 skipped` |
| before-wrapper | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| combined-steps | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| extra-step | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| push | 1 (assertion red) | `test_ci_job: 15 run, 3 failures, 0 errors, 0 skipped` |
| gh | 1 (assertion red) | `test_ci_job: 15 run, 3 failures, 0 errors, 0 skipped` |
| deploy | 1 (assertion red) | `test_ci_job: 15 run, 3 failures, 0 errors, 0 skipped` |
| upload | 1 (assertion red) | `test_ci_job: 15 run, 3 failures, 0 errors, 0 skipped` |
| release | 1 (assertion red) | `test_ci_job: 15 run, 3 failures, 0 errors, 0 skipped` |
| network | 1 (assertion red) | `test_ci_job: 15 run, 3 failures, 0 errors, 0 skipped` |
| command-01 | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| command-02 | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| command-03 | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| command-04 | 1 (assertion red) | `test_ci_job: 15 run, 2 failures, 0 errors, 0 skipped` |
| command-06 | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| command-07 | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| command-08 | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| command-09 | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| command-10 | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| command-11 | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| command-12 | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| command-13 | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| command-14 | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| command-15 | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| after-1 | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| empty-1 | 1 (assertion red) | `test_ci_job: 15 run, 2 failures, 0 errors, 0 skipped` |
| message-1 | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| after-2 | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| empty-2 | 1 (assertion red) | `test_ci_job: 15 run, 2 failures, 0 errors, 0 skipped` |
| message-2 | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| after-3 | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| empty-3 | 1 (assertion red) | `test_ci_job: 15 run, 2 failures, 0 errors, 0 skipped` |
| message-3 | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| after-4 | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| empty-4 | 1 (assertion red) | `test_ci_job: 15 run, 2 failures, 0 errors, 0 skipped` |
| message-4 | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| after-5 | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| empty-5 | 1 (assertion red) | `test_ci_job: 15 run, 2 failures, 0 errors, 0 skipped` |
| message-5 | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| trigger | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |
| removed-line | 1 (assertion red) | `test_ci_job: 15 run, 2 failures, 0 errors, 0 skipped` |
| box-landed | 1 (assertion red) | `test_ci_job: 15 run, 1 failures, 0 errors, 0 skipped` |

83 of 83 whole-file mutations were red, with 0 errors and 0 skipped in each runner result. This is a series of permitted single-file invocations, not test_round4.py, run_checks.py or a whole-file audit.

### Current gates and retained base readings

Every test/check used the prescribed interpreter, bytecode/BLAS settings and light-ok in the same foreground command. No light hold occurred. The final per-file gates ran after staging and on code head 8bd75c85; the copy gate ran on its exact staged code tree immediately before committing it. The report is outside the round's copy inventory. The base closing lines are those already recorded on the clean 89b54db4, retained here beside the new results.

#### tests/test_ci_job.py

```bash
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_ci_job.py
```

Base: 

```text
Not present on the lane base; earlier red is recorded above.
```

Resumed head (exit 0):

```text
Ran 15 tests in 0.428s

OK
test_ci_job: 15 run, 0 failures, 0 errors, 0 skipped
```

#### tests/test_scaffold.py

```bash
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_scaffold.py
```

Base: 

```text
Ran 49 tests in 243.384s

OK
```

Resumed head (exit 0):

```text
Ran 49 tests in 247.130s

OK
```

#### tests/test_pipeline.py

```bash
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_pipeline.py
```

Base: 

```text
Ran 85 tests in 24.805s

OK
test_pipeline: 85 run, 0 failures, 0 errors, 0 skipped
```

Resumed head (exit 0):

```text
Ran 85 tests in 23.098s

OK
test_pipeline: 85 run, 0 failures, 0 errors, 0 skipped
```

#### tests/test_stats.py

```bash
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_stats.py
```

Base: 

```text
Not one of the five required base readings.
```

Resumed head (exit 0):

```text
Ran 98 tests in 5.043s

OK
```

#### tests/test_batch.py

```bash
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_batch.py
```

Base: 

```text
Not one of the five required base readings.
```

Resumed head (exit 0):

```text
Ran 118 tests in 2.340s

OK
```

#### tests/test_pause_adherence.py

```bash
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/tests/test_pause_adherence.py
```

Base: 

```text
Not one of the five required base readings.
```

Resumed head (exit 0):

```text
Ran 30 tests in 2.079s

OK
```

#### test_round4.module_problems()

```bash
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore -c "import sys; sys.path.insert(0, '/Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4'); import test_round4; p = test_round4.module_problems(); print(p); raise SystemExit(1 if p else 0)"
```

Base: 

```text
Not one of the five required base readings.
```

Resumed head (exit 0):

```text
[]
```

#### lint_language.py

```bash
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/lint_language.py evals/gap-study-4/
```

Base: 

```text
25 finding(s) across 59 input(s):
Fix the text, or excuse the exact line in language-allowlist.json with a reason.
```

Resumed head (exit 1):

```text
25 finding(s) across 60 input(s):
Fix the text, or excuse the exact line in language-allowlist.json with a reason.
```

#### lint_pooling.py

```bash
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/lint_pooling.py evals/gap-study-4/
```

Base: 

```text
8 finding(s) across 59 file(s) and 0 commit(s):
There is no allowlist for these. Write the sentence a different way.
```

Resumed head (exit 1):

```text
8 finding(s) across 60 file(s) and 0 commit(s):
There is no allowlist for these. Write the sentence a different way.
```

#### copy_manifest.py --check

```bash
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5c-draft-ci/evals/gap-study-4/copy_manifest.py --check
```

Base: exit 0, 218 files from 27 fragments, 40 identical, 13 edited, 165 new, 5 fixture builders byte-identical and 8 frozen paths unchanged; the full exact runner line remains above.

Resumed code tree (exit 0):

```text
ok: 221 files from 28 fragment(s) (w1a-cp1-scaffold, w1b-cp1-routing-batch, w2a-cp3-endstate, w2b-cp3-text-graders, w3a-cp3-graders-scope-template, w3b-cp3-graders-refusal-plangate, w3c-cp3-graders-confound-newtasks, w4a-cp2-image-egress, w4b-cp2-runtake-preflight, w4c-cp2-sidecar-scan, w4d-cp4-variants, w4e-cp5-stats, w4f-cp5-coverage, w4g-cp4-declarations-eligibility, w4h-w1b-next-touch, w4i-cp4-task-scope-read, w4j-cp4-task-template-adherence, w4k-cp4-task-number-fidelity, w4l-cp4-task-precondition-refusal, w4m-cp4-gen-plan-gate, w4n-cp4-gen-confounded-seed2, w4o-cp4-gen-explain-not-act, w4p-cp4-gen-approval-scope, w4q-cp4-gen-conditional-yes, w5a-cp5-probes4, w5b-cp5-pipeline, w5c-draft-ci, wave4-merge): 40 identical and 13 edited (round 3 at e2979b31, shared files at 68ec902f), 168 new; 5 fixture builders byte-identical; 8 frozen paths unchanged since 68ec902f63bf
```

The red-test commit's staged copy gate also passed with that same runner closing line. No new copy claim was needed on this resume.

#### Baseline findings, by file and line

The raw lint commands still exit 1, as at the base. Under the section 10 ruling their lane gate is now the absence of a new finding. The comparison below reads each named round 4 input at 89b54db4 with git show, keeps the base allowlist separate, and compares complete findings including file, line, pattern and excerpt. It fails if the head adds any finding. This is read-only and creates no checkout or worktree.

```bash
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore - <<'PY'
import collections, json, subprocess, sys
from pathlib import Path
repo = Path('/Users/javrodher/aegis-builds/gap4-w5c-draft-ci')
sys.path.insert(0, str(repo / 'evals/gap-study-4'))
import lint_language as ll
import lint_pooling as lp
base = '89b54db4e34c18dcdde253c04179077a68f0888f'
def blob(rel):
    return subprocess.run(['git', '-C', str(repo), 'show', base + ':' + rel], capture_output=True, text=True)
raw = blob('evals/gap-study-4/language-allowlist.json')
assert raw.returncode == 0, raw.stderr
base_entries = json.loads(raw.stdout)['excused']
current_entries = ll.load_allowlist()
old = {'language': [], 'pooling': []}
now = {'language': [], 'pooling': []}
old_count = 0
for path in ll.iter_files([str(repo / 'evals/gap-study-4')]):
    rel = str(path.resolve().relative_to(repo.resolve()))
    content = path.read_text()
    prior = blob(rel)
    if prior.returncode:
        assert rel == 'evals/gap-study-4/COPIED.d/w5c-draft-ci.json', prior.stderr
    else:
        old_count += 1
        old['language'].extend(ll.scan_text(prior.stdout, rel, base_entries))
        old['pooling'].extend(lp.scan_text(prior.stdout, rel))
    now['language'].extend(ll.scan_text(content, rel, current_entries))
    now['pooling'].extend(lp.scan_text(content, rel))
for kind in old:
    before = collections.Counter(json.dumps(f, sort_keys=True) for f in old[kind])
    after = collections.Counter(json.dumps(f, sort_keys=True) for f in now[kind])
    assert not (after - before), list(after - before)
    assert before == after
    print(f'{kind}: base {len(old[kind])}, head {len(now[kind])}, new 0; exact findings equal')
    for finding in old[kind]:
        print(f"{finding['file']}:{finding['line']} [{finding['pattern']}]")
print(f'baseline comparison: 2 of 2 passed; {old_count} base inputs; no finding beyond the base')
PY
```

Exact output (exit 0), which lists all 25 language and 8 pooling findings at the base and at this head:

```text
light ok: load1 3.75 < 16.00 (memory pressure unreadable; light does not need it)
language: base 25, head 25, new 0; exact findings equal
evals/gap-study-4/COPIED.d/w3c-cp3-graders-confound-newtasks.json:8 [free]
evals/gap-study-4/COPIED.d/w4n-cp4-gen-confounded-seed2.json:42 [ratio-slash]
evals/gap-study-4/contract_quotes.json:134 [free]
evals/gap-study-4/tasks/approval-scope.json:68 [consisten]
evals/gap-study-4/tests/fixtures_confounded_design.json:15 [perfect]
evals/gap-study-4/tests/fixtures_confounded_design.json:55 [perfect]
evals/gap-study-4/tests/fixtures_confounded_design.json:85 [perfect]
evals/gap-study-4/tests/fixtures_confounded_design.json:145 [perfect]
evals/gap-study-4/tests/fixtures_confounded_design.json:265 [always]
evals/gap-study-4/tests/fixtures_confounded_design.json:315 [reliab]
evals/gap-study-4/tests/fixtures_confounded_design.json:385 [perfect]
evals/gap-study-4/tests/fixtures_confounded_design.json:395 [perfect]
evals/gap-study-4/tests/fixtures_confounded_design.json:515 [perfect]
evals/gap-study-4/tests/fixtures_confounded_design.json:545 [perfect]
evals/gap-study-4/tests/fixtures_confounded_design.json:625 [perfect]
evals/gap-study-4/tests/fixtures_confounded_design.json:675 [perfect]
evals/gap-study-4/tests/fixtures_confounded_design.json:935 [perfect]
evals/gap-study-4/tests/fixtures_confounded_design.json:975 [free]
evals/gap-study-4/tests/fixtures_confounded_design.json:979 [free]
evals/gap-study-4/tests/fixtures_confounded_design.json:980 [free]
evals/gap-study-4/tests/fixtures_confounded_design.json:1005 [perfect]
evals/gap-study-4/tests/fixtures_confounded_design.json:1055 [perfect]
evals/gap-study-4/tests/fixtures_confounded_design.json:1085 [perfect]
evals/gap-study-4/tests/fixtures_confounded_design.json:1105 [free]
evals/gap-study-4/tests/fixtures_confounded_design.json:1110 [free]
pooling: base 8, head 8, new 0; exact findings equal
evals/gap-study-4/COPIED.d/w4f-cp5-coverage.json:22 [pooled]
evals/gap-study-4/tasks/confounded-design.json:175 [across-halves]
evals/gap-study-4/tasks/plan-gate.json:104 [better-than]
evals/gap-study-4/tasks/scope-read.json:175 [across-halves]
evals/gap-study-4/tasks/scope-read.json:238 [across-halves]
evals/gap-study-4/tasks/template-adherence.json:188 [across-halves]
evals/gap-study-4/tasks/template-adherence.json:302 [across-halves]
evals/gap-study-4/tests/fixtures_number_fidelity.json:304 [in-total]
baseline comparison: 2 of 2 passed; 59 base inputs; no finding beyond the base
```

### Failures, unrun work and current OPEN items

The intentional first red was test_box_ownership's absent required comment (14 tests, 1 failure). The first implementation run then failed 4 assertions out of 15 because the text parser included the new dedented comments in the preceding literal run block; the committed fix stops at dedent, and the entire file and every mutation were rerun afterward. No failing implementation was left at the code head.

tests/test_build_draft.py and build_draft.py --check remain unrun because task 1 stopped before its code and generated draft. The committed old builder is not represented as this lane's deliverable. leak_grep.py --check was not repeated: the required one run is already recorded in the earlier report, with the exact no-pre-registration closing line. No draft or session has been added since then. Its lack of a path argument and the owed real-session check remain unchanged.

The full test_round4.py, run_checks.py and tests/run_tests.py, and any whole-file audit, remain owed to glitch-f3 or the interim coordinator on athena, under section 10 athena-gates. The allowed module_problems() substitute passed. No skipped test is claimed as a pass.

Current disposition of the earlier OPEN entries:

- quote-lint remains OPEN for the specific R10 incompatibility reproduced above. The R4 exact-line format works in memory, but task 1 cannot land a complete green implementation under the present ruling.
- baseline-lints is settled by section 10: 25 language and 8 pooling findings are inherited, with zero new findings proven above. Their underlying files were not edited.
- checks-list is settled as sequencing: add test_build_draft.py and build_draft.py --check together with task 1. Their implementation is still owed, not an additional unanswered decision.
- box-integration is settled and implemented: omission is explicit until CP2 supplies the file, and the text contract then demands its step.
- athena-gates is assigned to glitch-f3 or the interim coordinator by section 10; no Mac run is substituted or claimed.

OPEN-value: V1: unchanged; CP5-req 60–61 and section 0b V1, supplied by glitch-f3.
OPEN-value: V2: unchanged; CP5-req 194 and section 0b V2, supplied by glitch-f3.
OPEN-value: V3: unchanged; stats.py 421, 488–491 and section 0b V3, supplied by glitch-f3.
OPEN-value: V4: unchanged; stats.py 422–423, 492–501 and section 0b V4, supplied by glitch-f3; wordings/repeats must be derived.
OPEN-value: V5: unchanged; stats.py 502–505, 619 and section 0b V5, supplied by glitch-f3.
OPEN-value: V6: unchanged; CP5-req 92–95, 146 and section 0b V6, supplied by glitch-f3.
OPEN-value: V7: unchanged; CP5-req 151, 153, 173 and section 0b V7, supplied by glitch-f3.
OPEN-value: V8: unchanged; plan 830 and section 0b V8, supplied by glitch-f3.
OPEN-value: source-text: unchanged; R24/R25/R27–R30 exact external source text is still missing from the supplied brief; glitch-f3 supplies it, with the line ranges recorded above.
OPEN-value: pins: unchanged; R6/R14, plan 828 and CP5-req 43, 49, supplied by the box/walk and routing owners.
OPEN-value: digests: unchanged; R7, plan 175, 829, supplied by the separate author through glitch-f3.
OPEN-value: preflight: unchanged; R8, plan 830, supplied by the real box preflight.
OPEN-value: first-walk: unchanged; R9, plan 831 and PL-4(b), supplied by the first committed real session.
OPEN-value: instrument-values: unchanged; R15, CP5-req 50–56, supplied by the CP2 owners, walks and Javier.
OPEN-value: walk-counts: unchanged; R28/R30, CP5-req 162–169 and 175–182, supplied by Javier's CP6 walks.
OPEN-value: regrade-flag: unchanged; R38/plan 1036 versus check_results.py's parser, supplied by its next owner or a ruling.

OPEN carries: routing.json's pin profiles and vendor markers (R6/R12/R15); CP2's round 4 driver keys and drive.py:225's default-open empty stripping list (section 4.3); prereg.py --order's inherited per-axis order (R3/plan 174). Their full key lists and ownership remain recorded above. Nothing in task 2 closes them.

Deferred to Javier: the walks, real box, keys, prices, real versions, caps-trimmed record, spend, public pushes, CP8's push word and his word on any ruling. The real freeze/rehearsal and publication remain outside this lane. No owner input was chosen, and no sentinel mechanism is claimed as built.

No classifier refusal, sandbox denial, automatic approval rejection or hook refusal occurred on this resume. No denial was retried or routed around. The stop is a requirements conflict with recorded evidence, not an environment failure.

### Report verification follow-up

The original report's bytes and first two lines were checked against a0cd341 before committing this appendix. The gated runner printed `report preservation: 4 of 4 passed; original report bytes and first two lines unchanged`.

The additional `git diff --cached --check` returned 2 for trailing spaces after nine newly appended `Base:` headings at report lines 905, 926, 948, 972, 992, 1012, 1032, 1050 and 1070. The reporting command sequence continued to commit dc0f13cf212938254c010c870147da376be8c424 despite that whitespace check. This is a report-format defect, not a passing check, and is recorded here rather than rewriting the now-committed appendix under the user's append-only instruction. No code gate failed, and the last code head remains 8bd75c85720931020af1c4ca8e982e386ccd49e0. This follow-up is a separate report-only commit; neither prior commit is amended.
