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

Javier's word: "push GARS to public main now", typed in a terminal session of his own after the coordinating session's push card named this landing, recorded at 21:38 EST on 20 November 2026.

## Context

Lane `guard-default-deny` (OrgOS T38, the matcher widening named in [0107](0107-pg-nonpublic-projects-closed-to-reads.md)'s Row 4 follow-ups) was built red first on its own branch from `c5ba8425` (record 0325, one commit after public main `dfcadadc`, not yet pushed, so it reaches public main with this landing), by Claude Code producers, and reviewed by fresh-context reviewers, each in a separate checkout, never shown a producer's transcript.
**Same-model cost.** Producers and reviewers are Claude Code sessions; a same-model reviewer shares the producer's blind spots more than a different model would (the 0009/0013/0014 precedent).
The reviews were kept independent by fresh contexts, separate checkouts and no access to the producer's transcript.

The lane's commits, red first, named by their lane ids (a landing that re-creates them names the re-created ids in its Test section):
red `d5bdc3ef` (`gars/tests/test_every_tool_name.py`, 7 of 9 tests red), fix `5205c96c` (the guard's default deny, the settings matcher and belts, the `session_state.sh` comment, and 0330), record `42b67b7c` (0330's Test section), test `98fe044f` (the refused-name grid gains four near-spellings of a pass name, the fold of review A's finding 1), wording `60b633b5` (the README's Claude Code row and the decision index, the fold of review A's finding 2), this record (`7651fbba`), and one record commit that brings 0330's Test section to the head's figures and folds the outcome review's findings 1 and 3 into it.

Reviews, kept outside the repository and cited by the sha256 of the review file:

- the plan, before the build: PASS with six MINOR and three NIT findings, from a fresh-context reviewer, review_sha256 `ae2538a7fa8ee30a58d3d99bd39227f33db4180929c8136e8a0478f8bf5f963b`; the build folded the findings on the code and its records (the refusal as a separate final test, the matcher character set as re-read on Claude Code's hooks page on the build day, 0330's scoped sentence beside residual 17, its residual R5, and its precise evidence for refusing `Agent`), and the findings on the live outcome review (its permission flags and its `claude doctor` check) are passed to that review.
- review A, the stage A code at `42b67b7c` (`c5ba8425..42b67b7c`): PASS, no misgraded input on 216 tried inputs and 41 base-and-head pairs; two MINOR findings (four mutants of the pass test survived the grid; the public wording was not yet done) and two NIT findings, review_sha256 `df43870d79f3186d50a25b37f367d08bbf28fa0a34eed3fd71f17da2a5aec582`. Both MINOR findings are folded as named above; NIT 3 (the refusal's `Next:` line omits `MultiEdit` and `NotebookEdit`) is not folded, because the message's wording is accurate for a visitor; NIT 4 is informational and is passed to the outcome review.
- review C, the live outcome at the lane head `7651fbba` (headless Claude Code sessions at the base and the head, a copy of the head without the `"mcp__*"` deny, an honest-work session, a probe of the hook and `claude doctor`): PASS, no misgraded input on the head, so the loop stopped at its first round; two MINOR and five NIT findings, review_sha256 `a18d393d34ae391346cb134c9eedc8240cea7e275999e983ab0d8c7050cc4e98`. Its finding 1 (0330's Test section gave the 18-name grid's count where the head's module prints 22) and its NIT 3 (Claude Code offers tool names 0330 does not list; the default deny refuses them) are folded into 0330's Test section; its finding 2 (the headless session offered no to-do tool, so the pass list's to-do arm is shown at the hook only) and its other NITs need no change, and the landing's smoke ceremony walks the typed-call path.

## Decision

glitch-e9, under the owner's 23 September 2026 delegation as extended on 6 October 2026, approves the following protected change as built on the lane's branch and named above:

1. **`gars/_system/guard_hook.py`** (changed): `JUDGED_TOOLS` and `PASS_TOOLS` beside `WRITE_TOOLS`; `decide()` refuses a missing, empty or non-string tool name as `UNREADABLE`, keeps its three judged arms unchanged, and refuses every other name not on `PASS_TOOLS` with the `UNJUDGED` message (0330 Decision 2).
2. **`gars/.claude/settings.json`** (changed): the PreToolUse matcher is `.*`; `"mcp__*"` joins `permissions.deny`; `"disableClaudeAiConnectors": true` (0330 Decisions 1 and 4).
3. **`gars/_system/session_state.sh`** (changed, comment only): the SessionStart comment says a pin failure is shown, not enforced, under Claude Code; the `pins.py || exit 2` line is unchanged (0330 Decision 5).

None of the three adds a typed tool the agent can call, and none adds a flag or environment variable; the one new config key is `disableClaudeAiConnectors`, which only switches a source of tools off.
Outside the protected prefixes, recorded for completeness: `gars/tests/test_every_tool_name.py`, the suite totals in README.md and DEVELOPMENT.md, the README's Claude Code "Runs on" row, 0330, this record and the index.

## Test

- The lane's own checks are in 0330's Test section.
- The landing's own checks, on 20 November 2026, recorded in the landing's evidence commit, the merge's child:

Glitch verified the landing merge `373a0cff62b452510c053106ee3d2bbc5086f58a` (first parent `c5ba8425`, record 0325, itself one commit after public main `dfcadadc`; second parent the lane head `c8ae181c`), a true merge whose tree equals its second parent's.
The lane's commits land with their lane ids, as named above; the red commit `d5bdc3ef` also carries the suite-total sentences of README.md and DEVELOPMENT.md (1606 to 1615 tests), which the commit list above does not say against it.

- The smoke delta (row 14's ceremony): one run of three `claude-opus-5-5` sessions at the merge's tree (20 November 2026, 20:54-20:56 EST), prompt and suite hashes equal to the previous record's (`prompt_sha256` `cf32c619…`, `suite_sha256` `ea2f1cde…`); run-1 3/3; `delta` `0/1`, `no change` against `evals/runs/smoke/smoke-20261018-t74-combined.json`, floor `0/1` from `evals/runs/smoke/smoke-20260926-row-14-activation.json`; the evaluator found nothing (15 outputs hashed, 15 tasks regraded).
  An earlier attempt under this run id, at 19:25 EST, ran no model turn and was not scored: the API refused all three sessions before any turn (HTTP 403: the sessions' sign-in was no longer accepted).
- The outgoing range `dfcadadc..373a0cff` (9 commits): no gitleaks finding under either ruleset (gitleaks 8.30.0, its default rules and the repository's `gars/.gitleaks.toml`; 8 commits scanned, because the merge adds no content: its tree equals the lane head's).
- A fresh-context review of the landing merge (Claude Code, Opus 5.5, its own clone, never shown the producer's transcript; it checked the merge's parents and tree, the range's commits and identities, the protected paths, the guard change by an in-process probe of `decide()`, this record's and 0330's cited hashes and figures against their evidence, the trailers and a private-name scan; it did not run the test modules or the full suite): PASS (no MAJOR or MINOR, two NIT), review_sha256 `093cf02a5736aaa9af9a4c9c66fa54b02f852a34f05c6dd71280a14bc1d2355c`.
  Its NIT 1 (the red commit also carried the suite-total sentences) is folded above; its NIT 2 (gitleaks counts 8 commits for a 9-commit range) needs no change, because the merge adds no content.
- `python3 gars/_system/hooks/audit_trailers.py`, from the landing clone's root at this records commit: `verified 373a0cff62b452510c053106ee3d2bbc5086f58a (Bench previous: evals/runs/smoke/smoke-20261018-t74-combined.json)` and `trailers audit: 19/19 _system first-parent commits since activation f3abe50 verified; graded 19 of 19 seen`, exit 0 (re-run after each amendment of this commit).
- The full suite at records commit `9ab62fe8` on the separate test machine (Linux), solo: `PASS kind=gars commit=9ab62fe8cc44 ran=1615 passed=1533 failures=0 errors=0 skipped=82` (run `gars-guard-fix-records-9ab62fe-9ab62fe-20261121T020554Z`, 552 s).
- The four record checks at `9ab62fe8`, on the Mac, after its test gate allowed them: `tests/check_counts.py` exit 0 ("clean — every current claim matches the suite"); `tests/check_contracts.py` exit 0 ("14 contracts clean: sections, wait points, vocabulary."); `tests/test_decision_links_resolve.py` exit 0 ("citations: 697/697 resolve"); `gars/tests/build_refusal_corpus.py --check` exit 0 ("decision pin: 1999 refused, 607 allowed; OK").
- The commit that adds these two lines changes only this record's text.

## Status

Standing. Approval of the guard fix's protected change; the owner's typed push word is recorded above.

## Date

2026-11-20
