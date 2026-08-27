---
date: 2026-08-20
status: standing
kind: lesson
symptoms:
  - "upgrade machinery compounding from an unexamined premise"
  - "370 lines deleted same day"
touches:
  - README.md
  - CLAUDE.md
  - gars/CLAUDE.md
  - gars/CONTEXT.md
  - gars/00_initialize_project/CONTEXT.md
  - gars/_system/workspace.py
---
# A workspace is a git checkout, not a copy

**Supersedes [0014](0014-workspace-upgrade-path.md) and [0015](0015-workspace-staleness-detection.md).**

## What was wrong

A workspace was a `cp -r` of `gars/`. Everything that followed was scaffolding for that one
choice:

> the copy goes stale → build `upgrade.py` → upgrading changes contracts under existing projects →
> stamp the version per stage → the copy cannot tell it is stale → add a marker file → the marker
> must survive an upgrade → put it outside the replaced layer

Four mechanisms, each locally justified, all compounding from a root that was never re-examined.
That is the shape of accidental complexity.

**The copy was justified by reproducibility, and was worse at it than the alternative.** The
argument was that freezing the contracts protects a running analysis. But with a detached copy you
cannot diff it, revert it, pin it, or prove what it is beyond a text file. With a checkout:

| Question | Copy | Checkout |
|---|---|---|
| What version am I on? | a `VERSION` file, unverifiable | `git describe --tags` |
| What changed? | nothing | `git diff`, `git log` |
| Pin to a release | not possible | `git checkout v0.3.0` |
| Undo an update | not possible | `git checkout -` |
| Get a pushed fix | bespoke `upgrade.py` | `git pull` |

**The objection used to reject checkouts was already false.** [0014](0014-workspace-upgrade-path.md)
rejected them because `projects/` would sit in a git tree, "one `git add -A` from a public
repository." But `.gitignore` has carried `gars/projects/*/` since long before that decision was
written. The hazard had been solved; the decision was made without checking.

## Decision

Clone the repository and work in `gars/` directly. `gars/projects/` is gitignored, so real data
never enters git. Updating is `git pull`. Pinning is `git checkout <tag>`.

Removed: `_system/upgrade.py`, the `.gars-workspace` marker, `--status` / `--set-source`, the
version-comparison helpers, and the staleness check in stage 00's Process. About 370 lines.

**Kept: every stage stamps the template version it ran under.** That was introduced alongside the
upgrade command but does not depend on it — `git pull` can still move contracts between a
project's stages, and the per-stage stamp is what makes that visible afterwards. It is the one
part of the detour worth keeping.

Also removed: `--jobs` on the integrity check. It was measured as having no effect (4 and 16
workers gave identical throughput). A knob whose settings all perform the same only invites
fiddling.

## The lesson worth more than the change

Each of 0014 and 0015 answered a question with a new mechanism instead of questioning the premise
behind it. "The user cannot update their workspace" was answered by building an updater; nobody
asked whether it should have been a copy. Both decisions were written the same day they were
superseded.

**When a fix requires a second mechanism to support it, re-examine the thing being fixed.** The
chain-of-four above was visible the whole time and read as diligence.
