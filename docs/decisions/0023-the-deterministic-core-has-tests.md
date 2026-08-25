---
date: 2026-08-24
status: standing
touches:
  - gars/_system/
  - tests/
---
# The deterministic core has tests; the contracts have a lint

## What happened

Decision [0011](0011-deterministic-artifacts-in-stages-00-01.md) moved artifact generation into
`_system/` scripts precisely because they are conventional, testable software — and then nobody
tested them. ~1,700 lines of load-bearing stdlib Python, whose outputs are byte-reproducible by
design, had no test suite; every regression so far was caught by a live run on real data, which
is the most expensive possible test harness. The same assessment (2026-08-21) named the twin
gap: validation rules are stated twice — as script code and as contract Definitions prose
([0011](0011-deterministic-artifacts-in-stages-00-01.md) accepts this) — and nothing detected
drift between them.

## Decision

Two runners at the repository level, both stdlib-only on stock python 3.6.8 — the same
interpreter contract as the helpers, so they run anywhere the helpers run:

**`tests/run_tests.py`** builds a throwaway workspace per run (copying `_system/`,
`_references/`, `_templates/`), generates a 4-sample paired-end cohort of real gzipped FASTQs,
and drives every helper through its actual CLI the way the contracts drive it: assay menu →
create → inspect → link → finalize → design fill → check → emit → configure menus → resolver →
adapter. The properties pinned are the ones decisions were fought over:

- byte-identical re-emission on an unchanged design (0011);
- `files.csv` at `0444`, and a hand-edit caught by the `registry` check (0017/0018);
- a filled `samples.csv` never overwritten by `finalize` (0017);
- samplesheet paths inside the project, symlinks not dereferenced (the 08-19 defect);
- the adapter's identifier column named `gene` (0010/0021);
- the resolver refusing incomplete sub-stages and preferring `native` (0007);
- `quick` integrity not catching truncation and `full` catching it (0013);
- the guard hook's whole allow/deny matrix (0022);
- `--model` landing in the history entry (0024).

**`tests/check_contracts.py`** is the static half of contract compliance: every contract has
the eight sections in order; every failure code a script can emit appears in the contract that
handles it (the drift check); no two templates in a contract end with the identical question
(the stage-00 `T2` bug class); and the token load of each contract is printed as a number, so
growth is tracked rather than felt.

## What this is not

It is not the live compliance harness the assessment asked for — that replays scripted
scenarios against the agent itself and needs billed runs per release. This is the half that is
free and runs anywhere; the scenario replay remains open in DEVELOPMENT.md. Run the suite
before every commit that touches `gars/_system/` or a contract; a release is not taggable with
it red.
