---
date: 2026-11-20
status: standing
kind: decision
touches:
  - gars/_system/guard_hook.py
  - gars/_system/session_state.sh
  - gars/.claude/settings.json
symptoms:
  - The guard fix (0330) changes files under the protected prefixes gars/_system/ and gars/.claude/ with no owner-approval record
---
# The guard fix, 0330: approval of its protected change

Addendum to [0330](0330-the-guard-judges-every-tool-name-under-claude-code.md), which stays as the lane wrote it.
Two files this record approves are under the protected prefix `gars/_system/` and one under `gars/.claude/` (§9.3, R-094: `guard_hook.PROTECTED_PREFIXES`), so the change needs an owner-approval record.
Its shape follows [0296](0296-ms21-landing-c-0295-approval-of-protected-change.md) and [0324](0324-ms21b-t44b-approval.md).

Two things approve it, and they are kept apart here:

- **The coordinating session, on the code as reviewed.** The owner delegated approval of protected changes on 23 September 2026, and since 6 October 2026 every non-money build decision is the lane coordinator's, reported to him after; the lane was built and reviewed under that delegation, and its rulings are glitch-e9's, the lane's coordinating session: **approved by glitch-e9 under Javier's standing delegation; to land only on Javier's typed word.**
  No sentence in this record is the owner's.
- **The owner's own word, on the push.** Landing on public main waits for the owner's own typed push word; it is recorded on the line below when he gives it, and nothing else here records it.

Javier's word: PENDING.

## Context

Lane `guard-default-deny` (OrgOS T38, the matcher widening named in [0107](0107-pg-nonpublic-projects-closed-to-reads.md)'s Row 4 follow-ups) was built red first on its own branch from public main `c5ba8425`, by Claude Code producers, and reviewed by fresh-context reviewers, each in a separate checkout, never shown a producer's transcript.
**Same-model cost.** Producers and reviewers are Claude Code sessions; a same-model reviewer shares the producer's blind spots more than a different model would (the 0009/0013/0014 precedent).
The reviews were kept independent by fresh contexts, separate checkouts and no access to the producer's transcript.

The lane's commits, red first, named by their lane ids (a landing that re-creates them names the re-created ids in its Test section):
red `d5bdc3ef` (`gars/tests/test_every_tool_name.py`, 7 of 9 tests red), fix `5205c96c` (the guard's default deny, the settings matcher and belts, the `session_state.sh` comment, and 0330), record `42b67b7c` (0330's Test section), test `98fe044f` (the refused-name grid gains four near-spellings of a pass name, the fold of review A's finding 1), wording `60b633b5` (the README's Claude Code row and the decision index, the fold of review A's finding 2), and this record.

Reviews, kept outside the repository and cited by the sha256 of the review file:

- the plan, before the build: PASS with six MINOR and three NIT findings, from a fresh-context reviewer, review_sha256 `ae2538a7fa8ee30a58d3d99bd39227f33db4180929c8136e8a0478f8bf5f963b`; the build folded the findings on the code and its records (the refusal as a separate final test, the matcher character set as re-read on Claude Code's hooks page on the build day, 0330's scoped sentence beside residual 17, its residual R5, and its precise evidence for refusing `Agent`), and the findings on the live outcome review (its permission flags and its `claude doctor` check) are passed to that review.
- review A, the stage A code at `42b67b7c` (`c5ba8425..42b67b7c`): PASS, no misgraded input on 216 tried inputs and 41 base-and-head pairs; two MINOR findings (four mutants of the pass test survived the grid; the public wording was not yet done) and two NIT findings, review_sha256 `df43870d79f3186d50a25b37f367d08bbf28fa0a34eed3fd71f17da2a5aec582`. Both MINOR findings are folded as named above; NIT 3 (the refusal's `Next:` line omits `MultiEdit` and `NotebookEdit`) is not folded, because the message's wording is accurate for a visitor; NIT 4 is informational and is passed to the outcome review.

## Decision

glitch-e9, under the owner's 23 September 2026 delegation as extended on 6 October 2026, approves the following protected change as built on the lane's branch and named above:

1. **`gars/_system/guard_hook.py`** (changed): `JUDGED_TOOLS` and `PASS_TOOLS` beside `WRITE_TOOLS`; `decide()` refuses a missing, empty or non-string tool name as `UNREADABLE`, keeps its three judged arms unchanged, and refuses every other name not on `PASS_TOOLS` with the `UNJUDGED` message (0330 Decision 2).
2. **`gars/.claude/settings.json`** (changed): the PreToolUse matcher is `.*`; `"mcp__*"` joins `permissions.deny`; `"disableClaudeAiConnectors": true` (0330 Decisions 1 and 4).
3. **`gars/_system/session_state.sh`** (changed, comment only): the SessionStart comment says a pin failure is shown, not enforced, under Claude Code; the `pins.py || exit 2` line is unchanged (0330 Decision 5).

None of the three adds a typed tool the agent can call, and none adds a flag or environment variable; the one new config key is `disableClaudeAiConnectors`, which only switches a source of tools off.
Outside the protected prefixes, recorded for completeness: `gars/tests/test_every_tool_name.py`, the suite totals in README.md and DEVELOPMENT.md, the README's Claude Code "Runs on" row, 0330, this record and the index.

## Test

- The lane's own checks are in 0330's Test section.
- The landing's checks (the merge, the smoke ceremony and its delta, the trailer audit, the full suite at the merge, the outgoing range's scans and the landing review) are recorded here at landing, in the landing's evidence commit.

## Status

Standing. Approval of the guard fix's protected change; the owner's typed push word is recorded above when he gives it.

## Date

2026-11-20
