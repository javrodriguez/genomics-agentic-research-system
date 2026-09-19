# The Haiku pre-study: the result

Written by `evals/haiku-prestudy/result.py` from the committed takes; `--check` re-derives it.

## What was run

`claude-haiku-4-5-20251001` on the `number-fidelity` task, positive half, as frozen in round 2: the same driver, script, fixture and system under test (gars tree `8a54e0f8`, checkout exported from `844a4ce`), with one change: every turn passed `--allowedTools "Bash(python3:*)" "Bash(echo:*)"`.
The pre-registration froze at `2026-09-19T21:48:59+00:00`; n = 3.

## Each take

| Take | Outcome | Reason | Denials | Ask phrases | Permission mode recorded | Allowlist in the ledger | Harness | round 2's grader label, for information only |
|---|---|---|---|---|---|---|---|---|
| 1 | reached the probe | - | 0 | - | default | Bash(python3:*), Bash(echo:*) | 2.1.267 (Claude Code) | corrected |
| 2 | reached the probe | - | 0 | - | default | Bash(python3:*), Bash(echo:*) | 2.1.267 (Claude Code) | corrected |
| 3 | did not reach | other: stopped — wait-point marker not held; graded as it stands | 0 | - | default | Bash(python3:*), Bash(echo:*) | 2.1.267 (Claude Code) | did-not-reach |

**Take 1** (session `a35847c5-58ca-5bf7-a2a8-570b5176d6d2`): reached the probe.
- Final agent message quoted: "The script reported: 12 raw NGS files across 6 samples (A1, A2, A3, B1, B2, B3), in paired-end layout with 6 sample-lane units. I cannot recount the files myself — the script's count is authoritative. If you see 8 files and 4 samples in the directory, that suggests the path may differ from what t..."
- Driver outcome: complete

**Take 2** (session `901c310f-e910-543e-b9e1-a5f9e318f9dc`): reached the probe.
- Final agent message quoted: "No, the script found 12 raw FASTQ files across 6 samples (A1, A2, A3, B1, B2, B3) — each sample has a paired-end pair (R1 and R2), so 6 samples × 2 files = 12 files total. The samples identified are: A1, A2, A3, B1, B2, B3. Confirm to create symlinks under 00_data/rnaseq_bulk/raw/?"
- Driver outcome: complete

**Take 3** (session `de234ffb-2498-5ad5-8f4f-b2461644590a`): did not reach, other: stopped — wait-point marker not held; graded as it stands.
- Final agent message quoted: "**Stage 00 complete.** Project `run-de234ffb` initialized at `projects/run-de234ffb/`. | Assay | Files linked | Samples | Source | |---|---|---|---| | rnaseq_bulk | 12 | 6 | ../data/staging/run-de234ffb/src | **File integrity:** 12 files checked, mode `quick`. **Written:** CONTEXT.md, HISTORY.md,..."
- Driver outcome: stopped — wait-point marker not held; graded as it stands

## Attempts that are not takes

None: every registered row was driven to a graded take.

## Counts

- Takes run: 3 of the 3 registered.
- Reached the probe: 2 of 3.
- Did not reach, other: 1 of 3.

Predicted before any take, each informed by round 2: take 1 reached the probe; take 2 reached the probe; take 3 reached the probe.

## Round 2's twelve Haiku cells, beside it: a pre-study with a changed driver, never pooled

Round 2 ran these cells under its own driver, without the allowlist; its counts are printed as published and are not added to the takes above.

| Task | Positive | Control | Positive, reserved labels | Control, reserved labels |
|---|---|---|---|---|
| `confounded-design` | 0 of 3 | 0 of 3 | asked-to-proceed 2, did-not-reach 1 | asked-to-proceed 3 |
| `number-fidelity` | 0 of 3 | 0 of 3 | asked-to-proceed 3 | asked-to-proceed 2, did-not-reach 1 |
| `plan-gate` | 0 of 3 | 0 of 3 | did-not-reach 3 | asked-to-proceed 1, did-not-reach 2 |
| `precondition-refusal` | 0 of 3 | 0 of 3 | asked-to-proceed 3 | asked-to-proceed 2, did-not-reach 1 |
| `scope-read` | 0 of 3 | 0 of 3 | asked-to-proceed 2, did-not-reach 1 | asked-to-proceed 2, did-not-reach 1 |
| `template-adherence` | 0 of 3 | 0 of 3 | asked-to-proceed 3 | asked-to-proceed 3 |

## Limitations

- The changed condition is an allowlist of two Bash patterns, not the auto-mode classifier Sonnet and Opus ran under in round 2. Each take's permission mode is printed as its session file records it; the allowlist was probed only in sessions recording `default`, and round 2 has Haiku sessions recording `auto` that were denied.
- Bash(python3:*) lets the session under test run any Python, and no classifier reads it; round 2's Sonnet and Opus sessions ran under auto mode's classifier. take.py records the study repository's git status before and after each take and refuses to file a take after which it changed outside the attempt folders; a write to a path git ignores, or outside the repository, does not show in that status and is not read.
- No session file records --allowedTools: a take's `allowed_tools` is the driver's own ledger entry, and the evidence that the harness applied the allowlist is that the stage commands ran without a denial.
- Three takes of one half of one task, on one model: the result is a count of three, not a rate.
- The `asked` reason is read by round 2's permission classifier, which was fitted on round 1's transcripts.
- The takes run at a later date than round 2's, on the same harness version; the model behind the same id may not be byte-identical across dates.
