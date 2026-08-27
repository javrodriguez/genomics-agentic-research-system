---
date: 2026-08-24
status: standing
kind: decision
touches:
  - gars/03_custom_analysis/CONTEXT.md
  - gars/_system/stage03_analysis.py
  - gars/_references/artifact_types.md
---
# Stage 03 runs an approved plan, never an improvised one

## What happened

Stage 03 spent five template versions as a stub whose only job was to refuse — a correct
defense (an empty directory is an invitation to improvise, [0002](0002-agent-control-negative-scope-and-templates.md))
that also left the system's premise untested. The assessment (2026-08-21) put it sharply:
custom analysis is the one stage where agentic judgment would actually differentiate GARS —
every other stage's rigor comes from nf-core or from `_system/` code — and it is also where
ungoverned agents are most dangerous. The unexploited opportunity and the unmanaged risk were
the same stage.

## Decision

Stage 03 is **plan-gated**. The agent's judgment goes into drafting `PLAN.md` — goal, inputs,
method, outputs, execution — as a reviewable file; a person approves it; only the approved plan
executes. Intent gets a human gate exactly where the design table got one in stage 01: at the
moment a decision becomes expensive to reverse.

The rails are code, `_system/stage03_analysis.py` ([0011](0011-deterministic-artifacts-in-stages-00-01.md)):

- **`create`** allocates `03_custom_analysis/<NN_slug>/` and stamps a skeleton whose
  `<FILL: ...>` markers state what a plan must contain.
- **`approve`** is the gate made durable and machine-checked: it refuses while skeleton
  markers survive, while the Outputs table is empty, while any output type falls outside the
  closed vocabulary, or while any output path escapes the analysis directory — then stamps
  `Status: APPROVED <date>` into the file. The approval lives in the plan, not in the
  conversation; the contract forbids running `approve` before the user has said yes.
- **`verify`** is the exit gate: refuses an unapproved plan, checks every declared output
  exists non-empty, writes `OUTPUTS.tsv` and `STATUS`, and returns the history entry (template
  version + model, [0024](0024-the-model-is-part-of-provenance.md)).

After approval the plan is frozen: a change of mind is a new analysis with a new number, and
the superseded one keeps its record. A failed execution is reported, not patched around — a
revised method is a new plan for review.

## Vocabulary

The closed artifact vocabulary ([0007](0007-artifact-registry-outputs-tsv.md)) gains three
deliberately generic types — `table`, `figure`, `report` — because custom outputs cannot be
enumerated in advance. Genericity is contained by adjacency: an analysis's semantics live in
its `PLAN.md`, which sits beside its `OUTPUTS.tsv`, and a specific type is preferred over a
generic one wherever it fits.

## Why a plan file, not a dialogue confirmation

A dialogue approval scrolls away; a plan file is versionable, greppable, and sits beside the
results it produced, so "what did we intend?" has an answer months later. It is also the
correct place for a reviewer's edits — the user changes the file, not the agent's memory. And
it makes the gate testable: `tests/run_tests.py` drives skeleton-refusal, vocabulary-refusal,
unapproved-verify-refusal, and the complete path without any agent in the loop.

This also finally closes the registry's original gap: stage 03 is the consumer that resolves
inputs by artifact type at run time because it cannot know its producers in advance.
