---
date: 2026-10-18
status: standing
kind: decision
touches:
  - gars/_system/stage00_register.py
  - gars/_system/venue_policy.py
  - gars/00_initialize_project/CONTEXT.md
  - gars/_system/migrate_data_class.py
  - gars/tests/test_s00_class.py
  - gars/tests/test_migrate_data_class.py
symptoms:
  - "purpose_legacy: ... is read only in a row that already carries it" from stage 00 finalize
  - "purpose_required: data_sources.tsv does not settle test or analysis" from stage 00 finalize (template T4c)
  - "purpose_disagrees: data_sources.tsv declares this data ..." from stage 00 finalize
  - "value is outside the declared vocabulary" from the guard for finalize --purpose pilot_internal (hunk R1 applied)
  - "the data_sources.tsv header is not source, data_class, declared_by" for a declaration with a use column (hunk G1 not applied)
  - "a guarded agent registers public data only" from the guard for an agent's finalize (hunk G2 applied)
  - decision pin rows test_nonpublic_read_block-535, -536, -539, -540 exit 2, expected 0 (G2 applied without its witnesses patch)
---
# Registration asks test or analysis, never internal, pilot or commercial

Item S00-class of the step map's fix list (`evals/step-map/FIXES.md`, item 1), agreed by the owner; its design is `lanes/gars-t74/S00-CLASS-DESIGN.md`, ruled by glitch-b5 under the owner's standing delegation (run 11 ruling 7: choices 1c, 2a, 3a with no agreement flag, 4 outside the lane, 5a with hunk G2). Wording is the lane's (gars-t74). The approval record for the `_system/` change is glitch-b5's at landing, and so are the frozen-file hunks the lane may not apply: `lanes/gars-t74/S00-class-R1-registry.patch` (R1) `lanes/gars-t74/S00-class-G1-guard.patch` (G1), `lanes/gars-t74/S00-class-G2-guard.patch` (G2) and its companion `lanes/gars-t74/S00-class-G2-witnesses.patch`.

## Context

Stage 00's finalize took `--purpose` from five values (`fixture`, `internal`, `pilot_internal`, `pilot_external`, `commercial`) and the contract gave the agent no way to choose among them, so a registration either asked a person a question about internal, pilot or commercial use that GARS has no capability to act on, or the agent chose. The owner asked that registration be simplified, not that enforcement be reworded.

**Reproduction.** At 5dd853ca, `gars/tests/test_s00_class.py` PurposeTests fails (`FAILED (failures=3, errors=5)`): `pilot_internal` registers as a new project (`0 != 2`), the helper and the data line do not exist. At 5f6125e8 the declaration tests fail (`FAILED (failures=20)`): finalize records nothing from a declaration and names no template, a disagreeing `--purpose` is written, the guard declares nothing from a four-column file, and the contract passes `--purpose <purpose>` with no T4c.

## Decision

1. **Choice 1c: `purpose` keeps today's spellings; a new registration writes only `fixture` or `internal`.** People read them as test and analysis, through one helper, `venue_policy.data_line` (`Data: public, test`), which finalize's result carries as `data`. `pilot_internal`, `pilot_external` and `commercial` are legacy: still read and enforced exactly as before in the rows that carry them (`check()`, `data_policy.tsv`, the route tokens, every run record unchanged), and finalize refuses them (`purpose_legacy`, exit 2, nothing written) unless the project's existing row already carries that purpose, so a person's re-run of a legacy row keeps it byte for byte. Hunk R1 narrows the registry's finalize `purpose` enum to `fixture` and `internal`, so an agent can register neither a legacy purpose nor re-run a legacy row; that re-run is the person's own, in their own terminal.
2. **Choice 2a: the person's own declaration settles test or analysis.** `data_sources.tsv`, which only a human writes, gains an optional fourth column `use` (`test`, `analysis` or empty; a row of three cells stays valid). With no `--purpose`, finalize records `fixture` when every linked raw entry lies inside declared sources that all say `test`, `internal` when all say `analysis`. Anything else (an empty or mixed use, three cells, an entry outside every declared source, a cell outside the two words, no file) is unsettled: exit 2, `purpose_required`, `template: T4c`, nothing written, and the contract's T4c asks once, "Reply `test` or `analysis`", re-sent on any other reply; `test` is `--purpose fixture`, `analysis` is `--purpose internal`. A `--purpose` that disagrees with a settled declaration is refused (`purpose_disagrees`). Finalize reads the file with its own reader, under the same rules as the guard's; hunk G1 makes the guard accept the fourth column (without it, a four-column file declares nothing and the agent's registration is refused, fail-closed).
3. **Choice 3a: terms of use for public data are never asked.** A public row keeps `agreement_ref` as today, and `none` means no agreement is named, never that every use is allowed (the stage 00 Definitions say so). If the person volunteers that the data comes with terms, their reference is recorded with `--agreement-ref`; no template asks. No agreement flag is added for new public projects: the cluster's agreement rule stays keyed on the legacy `pilot_internal` value (`venue_policy.check`), binding the rows that carry it and no new row; `none` still fails it.
4. **Choice 5a: restricted data stops at T5r, the existing finalize run by the person.** No new command and no new writer of `dataset.tsv`. When the person says the data is restricted, or the guard refuses `inspect` because the folder is not declared public, stage 00 replies T5r and stops: the `link` and the `finalize` (`--data-class <class> --purpose internal --agreement-ref <reference> --expiry <YYYY-MM-DD>`) to run in their own terminal, with the classes rendered from `_references/data_policy.tsv`. The agent's own finalize passes `--data-class public` only. Hunk G2 makes that a check: the guard refuses an agent's finalize whose `--data-class` is not exactly `public` (no case folding, no stripping), or that gives none, naming T5r's command, bare or through the dispatcher; `Public`, `PUBLIC` and ` public` fall to the registry's enum first, and that refusal names T5r too. Exactly `public` keeps today's decisions. T6 carries finalize's data line.
5. **What G2 changes in pinned witnesses.** Under G2 an agent's finalize with no `--data-class` on an open project, allowed before, is refused, as ruled; so is an agent's finalize with `deidentified_under_agreement` through a finalize door (`test_nonpublic_read_block` Q8Tests). Four rows of the decision pin `gars/tests/fixtures/refusal_decisions.jsonl` (`test_nonpublic_read_block-535`, `-536`, `-539`, `-540`) go from exit 0 to exit 2, and two assertions of `test_nonpublic_read_block` (EveryToolTests for finalize, Q8Tests' last call) from allowed to refused naming T5r. These land with G2 and only with it, as `lanes/gars-t74/S00-class-G2-witnesses.patch`; the pin then reads 1999 refused, 607 allowed.
6. **The migration is a dry run that reports and writes nothing.** Under 1c every existing row stays byte for byte, so `gars/_system/migrate_data_class.py` has no live mode (without `--dry-run` it refuses, exit 2): it walks `projects/*/00_data/dataset.tsv` and prints each row's class, purpose and meaning (the data line's words, plus `no route` when no route of the class serves the purpose, from `_references/data_policy.tsv`, and `cluster needs its agreement` for `pilot_internal`), and lists for a person every `pilot_external` or `commercial` row and every row it cannot read. It is not in the registry: it is the person's or glitch-b5's, not the agent's.

## What this does not close

- **The report keeps the record's word.** The design named the claims report among the helper's users; `claims/render_report.py` prints `purpose: fixture` as the manifest records it, unchanged, because its rendering is held byte for byte by `test_render_report` and the design also requires that module to pass as it is. The data line is finalize's result and the contract's.

## Test

`gars/tests/test_s00_class.py`: PurposeTests (1c), DeclarationTests and DeclarationContractTests (2a), TermsTests (3a), RestrictedContractTests and RestrictedGuardTests (5a); `gars/tests/test_migrate_data_class.py` (the migration). `test_the_agent_cannot_register_a_legacy_purpose` is green only with R1 applied, `test_the_guard_reads_a_four_column_declaration` only with G1, `test_an_agents_restricted_finalize_names_t5r` only with G2 (and with G2 the refusal corpus and `test_nonpublic_read_block` are green only with its witnesses patch).

## Status

Standing.

## Date

2026-10-18
