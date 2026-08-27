---
date: 2026-08-27
status: standing
kind: lesson
touches:
  - CLAUDE.md
  - DEVELOPMENT.md
  - gars/_templates/config/rnaseq_bulk.yaml
symptoms:
  - "10/10 samples failed strandedness check"
  - "sense ~= antisense 0.33-0.40 in infer_experiment"
  - "lesson parked in status prose and forgotten"
---
# A lesson lands in the artifact it constrains — first case: the unstranded library

## What happened

The 2026-08-24 `leukemia-tall` run established a durable fact about this lab's libraries:
RSeQC `infer_experiment` returned sense ≈ antisense (0.33–0.40 each) on all ten samples — the
library prep is **unstranded** — corroborated independently by the lab's earlier sns analysis
(`EXP-STRAND|unstr`). nf-core's "10/10 samples failed strandedness check" warning is the
expected face of that fact, not a failure.

The conclusion — "set `strandedness: unstranded` explicitly in future configs" — was recorded
in DEVELOPMENT.md's volatile Data quality note. Nothing a future project touches knew it: not
the config template, not the menus. The next project would have re-derived it from the same
alarming-looking warning, or worse, mistrusted a healthy run.

## Decision

Two things, the specific and the general:

**The specific:** the site measurement now lives in `_templates/config/rnaseq_bulk.yaml`'s
`strandedness` comment — the exact place a person deciding that key is looking — with this
decision as its provenance. The template default stays `auto`, because the template ships to
any site; the comment is what carries the lab's measured answer.

**The general rule, added to the maintenance discipline:** a lesson that constrains future
runs lands in the artifact it constrains — a template default or comment, a menu entry, a
preflight check, or a decision file with accurate `touches` — never parked in status prose.
DEVELOPMENT.md may point at where a lesson landed; it must not be a lesson's home.

## Why an artifact, not a lessons file

A pile of advisory prose is what this system's whole trajectory eliminates (0011, 0018, 0021:
each converted a prescription that stayed prose into a mechanism that fires). A lessons file
would be a new pile with dual-maintenance rot on top. The decision log already is the durable
store — what it needed was the symptom index (added the same day) and the discipline of
landing conclusions where they execute.
