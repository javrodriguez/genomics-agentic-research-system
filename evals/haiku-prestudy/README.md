# The Haiku pre-study

Round 2 of the Gap Study published `claude-haiku-4-5-20251001` as `0 of 3` in all twelve of its cells, and it never reached a graded wrong answer.
Round 2's driver passed `--permission-mode auto` to Haiku, Sonnet and Opus alike.
Its committed transcripts show that 34 of Haiku's 36 sessions ran in `default` mode instead, while all 70 Sonnet and Opus sessions ran in `auto`.
On the number-fidelity positive half, each of Haiku's three takes had its first stage-00 command denied by the harness, and the take stopped there.
The record of that finding, with the probes that reproduced it, is `verification/finding.md`.

This pre-study asks one question.
With everything else as round 2 froze it, and one pre-registered Bash allowlist added to every turn, does each of three Haiku takes of that half reach the probe turn?

## What is copied and what changed

- Round 2's driver, loader, ledger, scrubber, take checker and review kit are byte copies from round 2's done commit `bf065fe`, read with `git show`.
  `COPIED.json` names each file, its source blob and whether it was edited; `python3 evals/haiku-prestudy/copy_manifest.py --check` re-derives all of it.
- Four copies differ, each with its reason in `COPIED.json`:
  - `drive.py`: the one change. Every turn passes `--allowedTools` with the entries in `driver_change.allowed_tools`, and the ledger records them. `--permission-mode auto` is still passed.
  - `study.py`: this study's name and folder.
  - `prereg.py`: the planned-take count covers only the halves a task lists.
  - `review_kit/blindness.py`: this study's goal id is a marker beside round 2's.
- The copies' usage lines still name round 2's folder; they are left as copied rather than edited.
- The copied loader prints `take order: not yet — seeded at the freeze` even when frozen: this study has one cell, draws no seed, and its order is `take_order` in the pre-registration.
- The copied checker's study-path pattern names round 1's and round 2's folders, not this one; every take's checkout excludes `evals/`, so no path of this study can reach a session.
- The review kit's `BRIEF.md` and `why.md` are written for this study, not copied.
- `freeze.py` writes `pinned_files` as a name-to-sha256 map, which the copied `check_results.py` frozen-content check does not read; this study binds its pins through `freeze.py`, `take.py` and `result.py`, and uses the copied checker only for the ledger (`result.py --ledger`).
- `prereg-draft.json` is built by `build_draft.py`, which carries round 2's frozen rules unchanged by code and writes this study's own design beside them.
- Takes run against a checkout exported from `844a4ce`, whose content is the checkout round 2's three Haiku takes of this half ran in, with round 2's system under test (gars tree `8a54e0f8`).

## What a take can read as

- `reached the probe`: the probe line was sent and answered.
- `did not reach`, with the first reason that applies: `harness denial`, `asked`, or `other`.

`outcome.py` reads it from the take's own files.
Round 2's grader label is printed beside each take for information and is not a graded cell.

**Status: pre-freeze. Nothing here has been run or graded.**
