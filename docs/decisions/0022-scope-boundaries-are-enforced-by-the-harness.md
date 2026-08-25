---
date: 2026-08-24
status: standing
touches:
  - gars/.claude/settings.json
  - gars/_system/guard_hook.py
---
# Scope boundaries the harness can enforce, the harness enforces

## What happened

An external assessment (2026-08-21) put it plainly: of every scope rule in the system, exactly
one had never been violated — `files.csv` at mode `0444` — and it was the only rule the
filesystem enforces rather than prose advises. The record backs this up: two layers of prose
instruction were ignored in the first live test ([0002](0002-agent-control-negative-scope-and-templates.md)),
and a user's perfectly reasonable hand-edit of a machine-owned file got through a `# do not
edit` comment without friction ([0018](0018-machine-ownership-is-enforced-not-advised.md)).
Meanwhile the agent harness itself supports deny-rules and pre-tool hooks, and GARS used
neither. The architecture argued for enforcement and then under-used the enforcement available.

## Decision

The workspace ships its own harness configuration. `gars/.claude/settings.json` arms a
PreToolUse hook, `_system/guard_hook.py`, on every session started in the workspace root. The
hook refuses, at the moment of the tool call and with a message naming the rule:

- **writes to the template**: `_system/`, `_references/`, `_templates/`, `.claude/`, the
  workspace `CLAUDE.md`/`CONTEXT.md`, and every stage contract — these are updated by
  `git pull`, never by a session;
- **writes to machine-owned project files**: `files.csv`, everything under `01_samplesheets/`,
  and `projects/_index.md` — these are produced by `_system/` scripts, and the fix for a wrong
  one is to re-run the script;
- **`chmod`/`rm`/`mv` aimed at `files.csv`** — the obvious ways around `0444`;
- **ad-hoc `pip`/`conda`/`mamba` installs** — the environments are pinned by lockfiles, and an
  install silently unpins them;
- **shell write-targets** (`>`, `tee`, `sed -i`, `cp`/`mv` destinations) resolving into any of
  the protected directories.

A `permissions.deny` list in the same file covers the template directories a second time, and
denies `WebSearch`/`WebFetch` — no contract calls for the web.

## The line that keeps this safe

Every deny is an action **no contract ever instructs**. That is the review criterion for adding
a rule: a false positive here blocks a legitimate stage step mid-run, which is strictly worse
than a miss — misses are still covered by prose, by `0444`, and by stage 01's registry check
([0017](0017-machine-owned-files-are-verified-not-trusted.md)). This is why the hook does not
try to restrict *reads*: "do not read a colleague's directory" cannot be distinguished
mechanically from "read the source directory the user just gave", so it stays prose.

The hook's allow/deny matrix is pinned by `tests/run_tests.py` (GuardHookTests): each deny is a
forbidden action, each allow is a step a contract does instruct. Change the hook and the tests
say what you changed.

## Scope

The guard arms when a session starts in `gars/` — the documented workspace posture. A session
started elsewhere (including development sessions at the repository root, which must edit
contracts) is not covered, deliberately. Prose boundaries remain in force everywhere; the hook
is a floor, not the ceiling.
