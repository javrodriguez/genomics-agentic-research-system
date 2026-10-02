# GARS — repository orientation

This repository holds GARS (the Genomics Agentic Research System). Two ways in:

- **Developing GARS:** read `CLAUDE.md`, the developer orientation. It is named for Claude Code but written for whichever agent you use, and it is kept byte-stable because the Gap Study pre-registrations pin it.
- **Using GARS:** start your agent inside `gars/`, whose `AGENTS.md` is the entry.

The guard and the session-start render load only when the agent starts in `gars/` (Claude Code via `gars/.claude/`, Codex via `gars/.codex/`).
A session at the repository root is unguarded (decision 0042).
