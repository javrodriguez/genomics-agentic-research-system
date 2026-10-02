---
date: 2026-10-01
status: standing
kind: decision
touches:
  - gars/_system/guard_hook.py
  - gars/_system/codex_hook.py
  - gars/_system/tools/pins.py
  - gars/_references/tool_pins.json
  - gars/.claude/settings.json
  - gars/.codex/hooks.json
  - gars/.codex/config.toml
  - gars/AGENTS.md
symptoms:
  - decision 0266 changes gars/_system/, gars/_references/, gars/.claude/ and gars/AGENTS.md and adds gars/.codex/ with no owner approval record
---
# Codex adapter 0266: approval of its protected change, under the owner's delegation

Addendum to [0266](0266-codex-adapter-one-guard-two-harnesses.md), which stays byte-identical.
The files this record approves are protected (`gars/_system/`, `gars/_references/`, `gars/.claude/` and `gars/AGENTS.md`; §9.3, R-094), and `gars/.codex/` is protected by 0266 itself, so the change needs an owner-approval record.
Under the owner's 23 September 2026 delegation this record is written by the build lane and labelled as such; no sentence in it is the owner's.
Its shape follows [0252](0252-awsbatch-template-0251-delegated-approval-of-protected-change.md).

## The owner's yes (EMPTY until he types it)

> OWNER'S WORDS: NOT YET GIVEN. This slot is filled only with the owner's own typed words, quoted verbatim, never paraphrased and never written by the lane.
>
> - Words (verbatim):
> - Typed at (from `date`, with timezone), and the window:
> - Candidate sha he approved:

Until the slot is filled, nothing in this record is the owner's approval, and the candidate is not pushed; the public push waits for the owner's own words, typed in the Row-orchestrator's window.

## Context
Decision 0266 makes GARS run under Codex with the same guard decisions: one decision core, `guard_hook.decide`, behind two hook envelopes.
It was built on branch `gars-codex-port` from public main `c9fe683` in a `--no-local` lane clone with no remote, red first, by the lane executor under the Row-orchestrator glitch-4a's coordination.
The test file was committed red (`3229246`), then the guard (`c3e40f4`), the adapter and its wiring (`ac972c6`), the pins (`3fa7e39`) and the static-scan coverage (`31d95d0`); the pilot fixture follows the pinned `.codex` folder (`a4b3efc`).
Review: a fresh-context reviewer grades the branch; its verdict and the review file's sha256 are recorded at the landing, and the review itself stays outside the repository.

## Decision
The following protected changes are approved under the owner's 23 September 2026 delegation, as they stand at the branch head, subject to the owner's yes in the slot above.

1. **`gars/_system/guard_hook.py`**: `decide()` extracted with every check, its order and every message as at `c9fe683`, and `main()` reading stdin and calling it; the one guard-failed message held in `guard_failed()`; READ_ONLY gains `.codex/*`, `.codex/**/*`, `*/.codex/*`, `AGENTS.override.md`, `*/AGENTS.override.md`, `.git`, `.git/*`, `*/.git`, `*/.git/*`, `.agents/*`, `.agents/**/*`, `*/.agents/*`, `repo:.codex/*`, `repo:AGENTS.override.md` and `repo:.agents/*`; PROTECTED_PREFIXES gains `.codex/`; `expand_tilde()`, applied to write targets and to the Read, Glob and Grep target before the existing inside-the-root checks (0266, item 5: a pre-existing hole on public main, closed here); one docstring sentence. Every other line is as at `c9fe683`.
2. **`gars/_system/codex_hook.py`** (new): the Codex envelope 0266 items 2 and 3 describe, including its guard import inside the fail-closed net, the guard's own `UNREADABLE` text, and the refusal of a symbolic link at a Delete or a Move's source; it defines no protected path and no shell rule, and every refusal carries one `Next:`.
3. **`gars/_system/tools/pins.py`**: `inventory()` adds every regular file under any `.codex` folder. Every other line is as at `c9fe683`.
4. **`gars/_references/tool_pins.json`**: two entries of kind `harness_config`, `.codex/config.toml` sha256 `0b03c7a230c4746378fb8ec636e0567de9546b181e599d02e795fb98e8d43a2d` and `.codex/hooks.json` sha256 `1496ac91345f50c1b91dd58683a029090be47de0bee34c5e39b266877dfbd3f1`, both `reviewed`.
5. **`gars/.claude/settings.json`**: the deny list mirrors each new READ_ONLY entry in its `Edit(...)` form (`repo:` as `../`).
6. **`gars/.codex/hooks.json`** (new) and **`gars/.codex/config.toml`** (new): 0266 item 3.
7. **`gars/AGENTS.md`**: the mission line names the binding rule and points to `CLAUDE.md`; the security policy names both harnesses' wiring and the render signal, including that a render alone does not prove the guard is loaded; ten headings, 32 lines.

Outside the protected prefixes, recorded for completeness: the root `AGENTS.md`, `gars/tests/test_codex_adapter.py`, `gars/tests/test_refusal_messages.py`, `gars/tests/pilot_fixture.py`, 0266, this record, the index, `docs/architecture.md`, and the README and DEVELOPMENT texts and counts.

## What this does not close
- 0266's "What this does not close", items 1 to 14.
- The live Codex session: pending: Javier's CP3 run.
- The smoke ceremony (row 14) for this `_system/` landing is not yet run; it runs at the final merge.

## Test
- Claude Code's decisions, before and after: `build_refusal_corpus.py --check` prints `decision pin: 1995 refused, 611 allowed; OK` at `c9fe683` and at the branch head.
- `test_guard_hook.py` `Ran 7`, `test_protected_paths.py` `Ran 6`, `test_refusal_messages.py` `Ran 15`, each `OK`, inside the whole suite at `a4b3efc` (`ran 1282, passed 1200, failures 0, errors 0, skipped 82`).
- 0266's Test section holds the red-first counts, the parity line and the mutation proof.

## Status
Standing as the lane's record of the protected change. It is not the owner's approval until the slot above holds his words.

## Date
2026-10-01
