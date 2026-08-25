---
date: 2026-08-24
status: standing
touches:
  - gars/_references/contract_standard.md
  - gars/CLAUDE.md
  - gars/00_initialize_project/CONTEXT.md
  - gars/01_prepare_samplesheets/CONTEXT.md
  - gars/02_bioinformatics/CONTEXT.md
  - gars/02_bioinformatics/rnaseq_bulk/01_nfcore-rnaseq-wrapper/CONTEXT.md
  - gars/02_bioinformatics/rnaseq_bulk/02_rnaseq-de/CONTEXT.md
---
# The bounded voice: a compliant way to answer a question

## What happened

The contracts forbade any message outside the templates — a rule earned the hard way
([0002](0002-agent-control-negative-scope-and-templates.md)): free-form replies varied every
run and buried decisions in prose. But the rule as written had no exception, and the assessment
(2026-08-21) named the cost: the user most likely to benefit from GARS — a biologist without
pipeline expertise — is also the most likely to ask "what does strandedness mean?" mid-stage,
and the contract gave the agent no compliant way to answer. A tool that is mute toward its
intended users invites them to route around it, and an ungoverned bypass is worse than any
answer the agent could give in place.

## Decision

One standing exception, defined once in `contract_standard.md` and cited from each contract's
Response Format: when the user asks a direct question, the agent may answer it **from the
workspace's own files** — the contracts, `_references/`, the current project's directory —
**read-only**, in a short paragraph, and then **restates the pending wait point**.

The bounds are the mechanism:

- *Source-bounded*: the answer comes from files the workspace already governs, not from open
  recall or the web (`WebSearch`/`WebFetch` are denied by [0022](0022-scope-boundaries-are-enforced-by-the-harness.md)).
- *Action-bounded*: an answer never becomes an action, a recommendation to deviate, or a reason
  to skip a step.
- *State-bounded*: the stage is at the same wait point after the answer as before it. The
  restatement is what proves it — the dialogue returns to the template that was pending.

## Why an exception does not reopen 0002

0002's failure was the agent *acting and composing freely* — improvising steps, volunteering
analyses. This exception permits neither: no tool calls beyond reading workspace files, no
change to Process state, no unsolicited content — the user must have asked. The templates still
own every decision-carrying message; the voice covers only the explanatory gap between them.
