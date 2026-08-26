---
date: 2026-08-25
status: standing
touches:
  - gars/03_custom_analysis/CONTEXT.md
  - gars/_system/stage03_analysis.py
---
# Stage 03 runs under sbatch by default; the login node is an explicit user request

## What happened

The first live stage 03 analysis (`leukemia-tall`, `01_de-top30-heatmap`, 2026-08-25) ran on
the login node. The plan declared it, the estimate was sound (a 30×10 matrix, seconds, a few
hundred MB), the user approved it — every mechanism worked. The user still objected, and the
objection is right at the design level: "is this job small enough for the login node?" was a
**judgment call the agent made** at drafting time. This system's entire trajectory since
[0011](0011-deterministic-artifacts-in-stages-00-01.md) has been removing agent discretion
wherever a wrong call is expensive, and this call is expensive in exactly the worst way — the
login node's per-user cgroup kills whatever is running when memory runs short, not whatever is
at fault, so one under-estimate can take down another session's work
([0013](0013-integrity-verification-moves-to-stage-01.md) measured this class of failure).

## Decision

The plan's Execution section opens with a machine-checked `Runs:` line, and `approve` accepts
exactly two values:

- **`Runs: sbatch`** — the default for every analysis, whatever its size. The skeleton ships
  with this line already in place.
- **`Runs: login-node (user-requested)`** — allowed only when the user explicitly asked for
  login-node execution in this analysis's dialogue. The marker is the record of that request;
  a bare `login-node` is refused with a message saying job size is never the reason.

The agent no longer estimates its way onto the login node. The cost — Slurm queue latency on
jobs that would finish in seconds — is accepted: a uniform rule that wastes a minute beats a
judgment call that can kill a neighbour's process.

## Why a gated line, not contract prose

Prose ("run heavy work under sbatch") is what the first version had, and it delegated the
definition of *heavy* to the agent. A closed two-value vocabulary checked by `approve` follows
the same pattern as the artifact types ([0026](0026-stage-03-is-plan-gated.md)) and the config
menus ([0020](0020-config-decisions-come-from-menus.md)): the choice is visible in the plan
the human reads, the opt-out names its own justification, and the gate — not the agent's
restraint — is what makes the default stick. The venue gate is pinned by `tests/run_tests.py`:
a plan with no `Runs:` line is blocked, a bare `login-node` is blocked, the user-requested
form approves.
