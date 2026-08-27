---
date: 2026-08-27
status: standing
kind: decision
touches:
  - gars/_system/project_state.py
  - gars/_system/session_state.sh
  - gars/.claude/settings.json
  - gars/CLAUDE.md
  - docs/decisions/build_index.sh
symptoms:
  - "new session re-reads HISTORY.md to find its place"
  - "projects/_index.md stale (Last built days old)"
  - "decision exists but only findable by path"
---
# A session boots knowing the state, and the decision log answers symptoms

## What happened

An external pattern review (2026-08-26, after "GARS Under Review") found that GARS had nine
recording mechanisms and zero recall: a session booted on 100% static template content, with
nothing instructing it to read any project's HISTORY.md; `projects/_index.md` was rebuilt only
by hand, so its `Last built` stamp drifted; and the decision log was queryable by path alone —
"why does the login node keep killing my job?" found nothing, because the symptom lived in
0005's prose.

## Decision

Three mechanisms, all derived-not-recorded:

1. **`_system/project_state.py`** — a read-only render of every project: per-assay design and
   samplesheet state, unmade config decisions (the `<REQUIRED` markers), each sub-stage's
   STATUS (still the only authority), registered artifact types, and the last HISTORY.md
   entries. The per-project sibling of `build_projects_index.sh`, honoring the same law: a
   derived view cannot drift, so nothing new is ever recorded.
2. **A SessionStart hook** (`_system/session_state.sh`) rebuilds `projects/_index.md` — ending
   index staleness mechanically — and prints the catch-up into boot context. A session starts
   knowing where every project stands, at the cost of one directory walk.
3. **`kind:` and `symptoms:` frontmatter** on every decision, rendered by `build_index.sh`
   into the index, so the log answers symptom-shaped questions ("login-node SIGKILL" → 0027)
   and not only path-shaped ones. Backfilled across 0001–0031 the same day.

## Why a render, not a memory

The system's most repeated rule is that memory is not evidence: pipeline and data facts are
re-read from source, every time. These mechanisms recall only *events and decisions*, each
line citable to the file it was derived from (STATUS, HISTORY.md, a decision's own
frontmatter). The rejected alternatives are recorded in the same review: no embeddings or
database (wrong scale, breaks the stdlib-3.6.8 floor), no second event log (HISTORY.md and
git already are one; a restatement is dual-maintenance rot), no agent-writable memory file
(a memory the agent can write is a memory it can poison).
