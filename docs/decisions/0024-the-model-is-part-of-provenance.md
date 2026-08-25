---
date: 2026-08-24
status: standing
touches:
  - gars/_system/stage00_register.py
  - gars/_system/stage01_samplesheet.py
  - gars/_templates/project/HISTORY.md
  - gars/_references/contract_standard.md
---
# The model that executed a stage is part of its provenance

## What happened

GARS's own standard says a project that cannot name the contract version that produced it is
not reproducible — every stage stamps `_references/VERSION` into `HISTORY.md` for exactly that
reason. But the contracts are executed by a language model, and nothing recorded *which* one. A
stage run under one model and re-run under another is a different run — same contract, different
interpreter — and the system's behavior can drift with a vendor's model update, silently. The
assessment (2026-08-21) called this out: the model is part of the toolchain, and a project that
cannot name it is not fully reproducible by GARS's own standard.

## Decision

Every `HISTORY.md` entry carries a `Model: <id>` line beside the template version.

- **Stage 00**: `finalize --model <id>`; the value fills the `{{model}}` placeholder in the
  project stamp's creation entry.
- **Stage 01**: `--model <id>`; the value lands in the script-built `history_entry` the agent
  appends verbatim.
- **02.01 / 02.02** (entries the agent writes itself): the contracts require the line
  explicitly.
- **The standard** (`contract_standard.md`) makes it a rule for every future contract, so a new
  stage cannot ship without it.

The value flows through code where code writes the entry, exactly like the template version —
the agent passes a flag, it does not compose provenance prose. And as with the version stamp:
**`unknown` is an honest value; a guessed id is not.** The flag defaults to `unknown`, so a
harness that cannot name its model degrades to honesty rather than to fabrication.

## What this does not solve

It records the interpreter; it does not test it. A model id in `HISTORY.md` makes drift
*attributable* after the fact — which run was under which model — not *detectable* in advance.
Detection is the live compliance harness, still open in DEVELOPMENT.md.
