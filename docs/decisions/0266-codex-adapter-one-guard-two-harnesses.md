---
date: 2026-10-01
status: standing
kind: decision
touches:
  - AGENTS.md
  - gars/AGENTS.md
  - gars/_system/guard_hook.py
  - gars/_system/codex_hook.py
  - gars/_system/tools/pins.py
  - gars/_references/tool_pins.json
  - gars/.codex/hooks.json
  - gars/.codex/config.toml
  - gars/.claude/settings.json
  - gars/tests/test_codex_adapter.py
  - gars/tests/test_refusal_messages.py
  - docs/architecture.md
  - DEVELOPMENT.md
symptoms:
  - a Codex session in gars/ runs with no guard and no state render
  - Codex never reads CLAUDE.md
  - a nested .codex/config.toml or AGENTS.override.md is writable
  - a Write or Read of a ~/ path is judged inside the workspace while Claude Code resolves it under the home directory
---
# One guard, two harnesses: GARS runs under Codex with the same guard decisions

## Context
GARS's stage contracts are plain files with no harness in them.
What was Claude-only is the entry file a fresh agent reads and the wiring of the PreToolUse guard (`gars/_system/guard_hook.py`) and of the SessionStart state render (`gars/_system/session_state.sh`), which only Claude Code loads, through `gars/.claude/settings.json`.
So a Codex session in `gars/` ran with no guard and no state render, and decision 0042's "Guard scope" line said so: "another harness, runs unguarded".
Spec R-161 says the three project-local mechanisms run "under one harness's hook format"; supporting a second harness changes that rule, so it needs this record.

The owner, typed in the glitch-25 window on 1 Oct 2026 (the message arrived before 19:23 EDT; that is the planning clock read, not his typing time): `1 yes · 2 codex · 3 before freeze`.
It answered these three calls, quoted unelided from the message he was replying to:

> 1. **A spec change.** R-161 says GARS runs "under one harness's hook format". Supporting several platforms changes that, so it needs a decision record and your yes. I recommend **yes**, recorded as decision `0xxx` (number assigned when written).
> 2. **Which platforms.** I recommend **Codex only for now**, since it's installed and testable. Gemini later.
> 3. **The freeze.** New features stop **Tue 6 Oct**, and portability isn't one of the three exceptions. Steps 1–2 plus the Codex proof fit by Monday if we start tomorrow. Otherwise it waits until after 16 Oct. I recommend **doing it before the freeze**. "Works with any agent, here's the test" is exactly the kind of thing a hiring scientist can check in minutes. But it's competing with Friday's HHMI and OpenRefinery applications, so those go first tomorrow morning.

## Decision
This record is written in the build lane; its in-spec calls are the lane's and the coordinator's rulings are the coordinator's, each labelled, and none of them is the owner's.

1. R-161 is read as: one decision core, `guard_hook.decide`, under each supported harness's hook format. Supported today: Claude Code, and Codex 0.144 or later.
2. The Codex envelope (`gars/_system/codex_hook.py`) translates each Codex call into the guard's own `{tool_name, tool_input, cwd}` shape and calls `decide` with the root fixed to its own `gars/` folder; it holds no protected-path list and no shell rule of its own.
3. The set of protected files grows to cover what Codex reads, and a tilde-spelled path is judged where Claude Code really resolves it.
4. The front door is `AGENTS.md`; both `CLAUDE.md` files stay byte-identical.

The envelope mapping, the protected set with the reason for each entry, R-099 per harness and the measured evidence are completed in this record before landing.

## What this does not close
The residual gaps are listed here before landing, with their measurements.

## Test
`gars/tests/test_codex_adapter.py`, red first; the figures are recorded here before landing.

## Status
Standing. Implementation in the build lane; the protected-change approval is its own addendum record.

## Date
2026-10-01
