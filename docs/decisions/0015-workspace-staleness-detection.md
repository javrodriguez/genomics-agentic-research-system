---
date: 2026-08-20
status: superseded
kind: decision
symptoms:
  - "fix existed upstream, workspace could not tell"
touches:
  - gars/_system/workspace.py
  - gars/_system/upgrade.py
  - gars/00_initialize_project/CONTEXT.md
---
# A workspace can tell when it is behind its source

> **Superseded 2026-08-20 by [0016](0016-workspaces-are-checkouts.md).**
> A workspace is a git checkout; the machinery below was removed. The per-stage version
> stamping introduced here was kept — it does not depend on the rest.

**Question.** [0014](0014-workspace-upgrade-path.md) gave workspaces an upgrade path but left them
unable to know they needed one. It deferred detection on the grounds that it "earns its place only
once there is more than one workspace to track."

**That reasoning was wrong, and this supersedes it.** A single workspace telling you it is behind
is exactly what was missing when the first real user prompt was refused by the assay matcher: the
fix existed, was pushed, and the workspace had no way to say so. The number of workspaces was
never the relevant variable — the gap between "a fix exists" and "this copy has it" was.

## Where the marker lives, and why that is the whole design

A workspace is made with `cp -r`, which records no metadata. So a workspace only knows its source
once something writes one down: `upgrade.py --set-source` or `--apply`.

The marker is **`.gars-workspace` at the workspace root** — deliberately *not* in `_references/`
or `_system/`. Those are the template layer, which `upgrade.py` replaces wholesale: a marker
inside them would be destroyed by the very command that needs to write it. Only `projects/` and
root dotfiles survive an upgrade, and the marker is not project data.

## What it reports

`upgrade.py --status` never writes and never fails on absence:

| `state` | Meaning |
|---|---|
| `same` | up to date |
| `behind` | a newer template exists at the recorded source |
| `ahead` | this workspace is newer than its source — usually the wrong source, worth saying |
| `differs` | the versions are not comparable, so no ordering is claimed |
| `unknown` | no source recorded yet |
| `unreachable` | the recorded source is gone or is not a GARS checkout |

`differs` matters. `unknown` is a legitimate template version, and asserting an ordering over it
would be a guess — the same reason stage 00 records `unknown` rather than fabricating one.

## Where it is checked

Stage 00, at step 1, **before the project title is collected**. A project started on stale
contracts carries them for its whole life, so the cheapest moment to learn is the first. The agent
reports it and stops there: **it never upgrades on its own initiative**, because upgrading changes
contracts and whether to do so before or after a given project is a scientific judgment, not a
housekeeping one.

A workspace that is current says nothing at all. A staleness notice that fires every session is a
notice people learn to skip.

## Rejected

- **Checking on every stage.** Stage 00 is where it changes an outcome. Repeating it at 01 and 02
  would nag mid-analysis about something the contract tells you not to act on mid-analysis.
- **Fetching the source over the network.** `--status` compares against a local checkout. A
  workspace that cannot see its source reports `unreachable` rather than reaching out; the source
  path is the user's to keep current.
