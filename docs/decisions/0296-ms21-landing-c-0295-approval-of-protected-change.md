---
date: 2026-10-17
status: standing
kind: decision
touches:
  - gars/_system/executorlib.py
  - gars/_system/project_state.py
  - gars/_system/stage00_register.py
  - gars/_system/stage03_analysis.py
symptoms:
  - Landing C of lane gars-ms21 (0295) changes four files under the protected prefix gars/_system/ with no owner-approval record
---
# Lane gars-ms21 Landing C, 0295: approval of its protected change

Addendum to [0295](0295-project-and-analysis-creation-published-by-rename.md), which stays as the lane wrote it.
The four files this record approves are under a protected prefix (§9.3, R-094: `gars/_system/` in `guard_hook.PROTECTED_PREFIXES`), so the change needs an owner-approval record.
Its shape follows [0282](0282-reproduction-package-0281-delegated-approval-of-protected-additions.md) and [0277](0277-methods-journal-paragraph-0276-approval-of-protected-change.md).

Two things approve it, and they are kept apart here:

- **The coordinating session, on the code as reviewed.** The owner delegated approval of protected changes on 23 September 2026, and since 6 October 2026 every non-money build decision is the lane coordinator's, reported to him after; the lane was built and reviewed under that delegation, and its rulings (rounds 3, 3b and 4) are glitch-b5's, the lane's coordinating session: **approved by glitch-b5 under Javier's standing delegation; to land only on Javier's typed word.**
  No sentence in this record is the owner's.
- **The owner's own word, on the push.** Landing on public main waits for the owner's own typed push word; it is recorded on the line below when he gives it, and nothing else here records it.

Javier's word: "push GARS to public main now", typed in the coordinating session's window after its push card named this landing, recorded at 21:34 EDT on 17 October 2026.

## Context

Lane `gars-ms21` task G5 T34 (the three writers 0200's R2 left open) was built red first on its own branch from public main `a97fa9cd`, by Claude Code producers, and reviewed by fresh-context reviewers, each in a separate checkout, never shown a producer's transcript.
**Same-model cost.** Producers and reviewers are Claude Code sessions; a same-model reviewer shares the producer's blind spots more than a different model would (the 0009/0013/0014 precedent).
The reviews were kept independent by fresh contexts, separate checkouts and no access to the producer's transcript.

The landed commits, red first, re-created after Landing A from the lane's commits, each with its tree change, message, author, committer and dates kept, and named here by its re-created id (the lane's own working files under `lanes/`, among them the T57 design note, do not land):
red `d12d7332` (three writer-recovery rows and a creation-sibling test), fix `92136bb7` (stage 00 and stage 03 create build in a dot sibling and publish by rename; `project_state` skips a dot name), record `39843c30`, fix `3b7dfd10` (the stage 03 submissions history rewritten through `atomic_open`, and the standing mutation re-pointed by round 3b ruling 1), record `6fa9f717`, red `33b01937`, fix `ef2f89d7` (`project_state` skips a dot sibling under `03_custom_analysis/`), tests `2bd0d1a7` and `ffd15cad`, record `c45febcf`.

Reviews, of commit ranges on the lane's own branch, kept outside the repository and cited by the sha256 of the owner's held review file:

- round 3, `c9f9d603..746fd691`: CHANGES (no MAJOR on Landing C; three MINOR: a stage 03 creation sibling was listed as an analysis, the stage 03 sibling cleanup was bound by no test, and the history's kept mode was bound by no test), review_sha256 `91f5a751be7670f43befec4be612a7a117fe3ebcb9a19eca677dd56e4a3548b7`; each folded in round 4 as glitch-b5 ruled: the first red first (`33b01937`, then `ef2f89d7`), the second and third bound by new assertions (`2bd0d1a7`, `ffd15cad`) that the round 4 review showed red under a mutant.
- round 4, `45f60028..0ac4587a`, with Landing C read as a whole (`c9f9d603..0ac4587a`): PASS (no finding against Landing C, NITs only), review_sha256 `ba8bf68cb1c1c53694f952496f52a5343f168a66a06663b4d2bb2b5a5d4daade`, so the loop ended at round 4. It ran the named modules and the four gates, parsed the four files as Python 3.6, and ran six mutants of the three writers' fixes and the re-pointed standing mutation, each red in the module the rulings bind it to.

## Decision

glitch-b5, under the owner's 23 September 2026 delegation as extended on 6 October 2026, approves the following protected change as re-created at the build-branch commits named above:

1. **`gars/_system/stage00_register.py`** (changed): `create` builds the project in `projects/.<title>-XXXX` and renames it into place; any failure removes the sibling.
2. **`gars/_system/stage03_analysis.py`** (changed): `create` builds the analysis folders in a dot sibling, renames them into place, and removes the folder if `PLAN.md` cannot be published.
3. **`gars/_system/project_state.py`** (changed): skips a dot-named entry under `projects/` and under `03_custom_analysis/`.
4. **`gars/_system/executorlib.py`** (changed): the stage 03 submissions history is rewritten whole through `workspace.atomic_open`, keeping the file's mode.

On success the bytes, names and modes written are those of the old writers (0295 item 6). None of the four is a new typed tool the agent can call, and none adds a flag, environment variable or config key.
Outside the protected prefix, recorded for completeness: the suite totals in README.md and DEVELOPMENT.md, `gars/tests/test_r164_writer_recovery.py`, `gars/tests/test_lifecycle_faults.py` (the re-pointed anchor only; name, witness and expected error unchanged), `gars/tests/test_stage03_execution.py`, 0295, this record and the index.

## Test

- Full suite at the lane head `2d819179` (whose tree equals the landing's outside `lanes/` and the landing's records) on a separate test machine (Linux): run `gars-ms21-land-ac-2d819179-2d81917-20261017T041958Z`, `PASS kind=gars commit=2d819179add8 state=done rc=0 ran=1415 passed=1333 failures=0 errors=0 skipped=82`.
- The landing's own checks (the merge, the outgoing range's scans, the smoke delta, the landing reviews and the trailer audit), for Landings A and C together, are recorded in [0292](0292-ms21-landing-a-approval.md)'s Test section, in the landing's evidence commit.

## Status

Standing. Approval of Landing C's protected change; the owner's typed push word is recorded above.

## Date

2026-10-17
