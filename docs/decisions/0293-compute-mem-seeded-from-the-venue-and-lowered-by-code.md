---
date: 2026-10-18
status: standing
kind: decision
touches:
  - gars/_system/venue_policy.py
  - gars/_system/configure.py
  - gars/_system/stage00_register.py
  - gars/_system/executorlib.py
  - gars/_templates/config/atacseq_bulk.yaml
  - gars/_templates/config/chipseq_bulk.yaml
  - gars/_templates/config/cutandrun.yaml
  - gars/_templates/config/methylseq.yaml
  - gars/_templates/config/rnaseq_bulk.yaml
  - gars/_templates/config/scrnaseq.yaml
  - gars/_templates/config/spatialvi.yaml
  - gars/_references/config_schema.md
  - gars/tests/test_venue_seeded_config.py
  - gars/tests/test_venue_policy.py
symptoms:
  - every assay template seeds compute.mem of 32G to 96G, the local venue refuses anything above 8 GiB, and a person must edit _config/<assay>.yaml by hand to run there
  - a stage 02 submit on local is refused with "venue local memory rule: above 8 GiB" and the refusal names neither the value the venue accepts nor how to reach it
---
# compute.mem is seeded from the venue and lowered by code

T57 (lane gars-ms21, task 4; AEGIS MS21). Design: `lanes/gars-ms21/T57-DESIGN.md` version 6, reviewed in `REVIEW-4d631ae.md` (ready to rule) and ruled by glitch-b5 in RULINGS.md rounds 9 and 10, under the owner's standing delegation.
Every ruling here is **the lane's** or glitch-b5's as named; no sentence in this record is the owner's.
This record writes no approval; the landing's approval record (0294) is glitch-b5's.

## Context

1. The seven assay templates in `gars/_templates/config/` seeded `compute.mem` as constants: spatialvi 32G; atacseq_bulk, chipseq_bulk, cutandrun, rnaseq_bulk 64G; methylseq, scrnaseq 96G. `venue_policy.check()` refuses a stage 02 or stage 03 request above `8 * 1024 ** 3` bytes on venue `local`. Every seeded value was refused there, so the only way to run on `local` was to hand-edit the config.
2. The goal (glitch-b5's round 7 ruling 1): **no person has to edit `compute.mem` to run on their venue.** The ceiling stays where it is: `venue_policy.py`'s submit-time check, unchanged in value and in where it is read.
3. The threat designed against: the agent must never be able to raise its own compute limits. No new flag, environment variable or config key may name a venue, a ceiling or an override.

**Reproduction.** Lane commit 0ca5c8bc (red on this container, 18 October 2026): `gars/tests/test_venue_seeded_config.py` printed `FAILED (errors=28)`: `AttributeError: module 'venue_policy' has no attribute 'MEM_CEILING'` (the table cases, and a `local` workspace seeding 64G and 96G), and argparse's `invalid choice: 'lower'` for every `configure.py lower` case. `test_venue_policy.py` printed `FAILED (failures=2)`: `'configure.py lower --project ... --assay rnaseq_bulk' not found in 'venue_not_permitted: venue local memory rule: above 8 GiB'`, and `'this venue accepts up to 8G' not found` on the stage 03 case.

## Decision

**Part 1 (the lane's build of T57-DESIGN.md v6, as ruled R1 in round 9).**

1. **The table lives in protected code.** `venue_policy.py` holds `MEM_CEILING = {'local': 8 * 1024 ** 3}`, `ACCEPTED_MEM = {'local': '8G'}` and `SEEDED_MEM`, keyed by `(venue, assay_id)` for all seven assay ids: `local` seeds `8G` for every assay; `slurm` and `homelab` seed each template's previous value byte for byte. `homelab` and `slurm` have no `MEM_CEILING` entry, as before. `check()`'s local comparison keeps its text `mem_bytes > 8 * 1024 ** 3`, which is the anchor of the standing mutation `8.5 GiB accepted` in `gars/tests/test_venue_policy_faults.py`; a test holds that comparison and `MEM_CEILING['local']` equal (check admits exactly the table's ceiling and refuses one byte above it).
2. **Stage 00 seeds from the table.** Each template's `mem:` line is now `mem: {{mem}}`, and nothing else in any template changed. `stage00_register.py create` fills the slot from `venue_policy.seeded_mem(venue, aid)`, where `venue` is `executorlib.venue_of()` of the descriptor template it seeds (`_templates/config/executor.yaml`, parsed with `executorlib.parse_descriptor`; absent, Slurm, as `load()` treats an absent descriptor). The slot values are built per assay. The shipped descriptor names `slurm`, so a project created from it is seeded exactly as before: each seeded `_config/<assay>.yaml` is byte for byte the base file. No new file is seeded, so `guard_hook.CREATE_STAMP` is unchanged.
3. **`configure.py lower`** is a new subcommand with three flags, `--project`, `--assay` and `--dry-run`. It takes no value, no venue and no decision.
   - `--assay` must be one of the seven ids; it does not consult `ASSAY_DECISIONS`, so `spatialvi`, which `apply` refuses, is served.
   - The venue is `venue_of(load(project))`, the venue the submit compares against. A descriptor that cannot be read or decoded refuses (exit 1) with nothing written: the failure direction is "not lowered", never "raised". A descriptor that is not a file is read as absent (Slurm), as the submit reads it, so `lower` does nothing there.
   - It reads `compute.mem` with `wrapperlib.read_config`, the parser the submit uses. `venue_policy.lowered_mem` returns the venue's seed only on a venue with a `MEM_CEILING` entry and only for a request above it, or one the submit could not parse; otherwise `lower` prints `lowered: null` and exits 0. It never returns more than a parseable request.
   - **It offers nothing a venue refuses anyway** (review finding 2, folded as round 9 item 1 says): before writing, it runs `check()` on the project's dataset row at the lowered value; if any refusal remains (on `local`, any purpose but `fixture`; an unclassified dataset), it prints `lowered: null`, a `needs_venue` line naming the refusals, and exits 1, and writes nothing.
   - It refuses (exit 1, nothing written) unless the file holds exactly one `  mem:` line and that line is under `compute:`. It replaces that one line's value and keeps every other byte: line endings, a trailing comment on that line, `<REQUIRED>` markers, a custom `de.formula`, and the file's mode. It writes through `workspace.atomic_open`.
   - `--dry-run` prints `lowered: {from, to, venue, accepts_up_to}` and writes nothing; the real run prints the same plus `wrote`, `template_version` and a `history_entry` (`## <ISO-8601 date> — 02_bioinformatics — compute.mem lowered`, the template version, and one line naming the assay, the old and new value and the venue), appended to `HISTORY.md` verbatim by the agent on a public project and by the user on a non-public one (round 9 item 7, Q11).
   - Exit codes are `configure.py`'s own (1 refused, 3 usage; argparse's 2 for an unknown flag); the design's "exit 2" named the class of outcome, not the number.
4. **`apply` is unchanged.** It gains no lowering and no output key, so stage 02's T9 ("Nothing else in the file changes") stays true.
5. **The refusal names the remedy.** The local memory rule's detail is now `venue local memory rule: above 8 GiB; this venue accepts up to 8G` (today's words stay its prefix). On stage 02, on a venue with a `MEM_CEILING` entry, `executorlib._venue_refusal` appends to a memory-rule or `resource_unparseable` refusal `; configure.py lower --project <p> --assay <a> lowers compute.mem to the 8G this venue accepts`. Stage 03's refusal names the accepted value only: its memory is the script's `#SBATCH --mem`, which `lower` never touches. Slurm and homelab gain no remedy. The comparison is unchanged.
6. **`config_schema.md`** says where the value comes from, that `lower` fits it in its own step, and that the ceiling is enforced at submit.

In-spec choices (the lane's): `ACCEPTED_MEM` as the one spelling of the accepted value, so the seed, the detail and the remedy cannot disagree; keeping a trailing comment on the `mem:` line (the review's NIT; no template carries one); preserving the config's mode on rewrite.

Rejected alternatives (T57-DESIGN.md v6): keeping the template constants and lowering only; a placeholder word resolved at submit; the lowering inside `apply` (it made T9 false and re-decided science); a recorded "seeded-for" venue (it would be a new agent-writable config key).

## What this does not close

- **R1** `homelab` has no memory ceiling and seeds the Slurm values (round 9 item 3: no invented ceiling) until a measured host size.
- **R2** The venue is inferred from the descriptor's `name:` and the machine-owned homelab marker, not attested by the host (0102's residual). In a public project the agent can write `name:`; through `lower` that selects only between lowering to the accepted value and doing nothing, never a higher value. Not widened.
- **R3** The local job total is the only GARS memory bound on venue `local`; how Nextflow divides it among tasks is unbounded by GARS, as before (`lanes/gars-ms21/LOCAL-LIMITS-HARDENING.md`, a separate design item).
- **R4** `lower` reads, then replaces the file whole; an edit made between its dry run and its real run is lost, as with `apply`.
- **R5** The reproduction exemplar (`scripts/repro_exemplar_run.py`, step `02.memory`, decision 0281) still edits `  mem: 64G` to `  mem: 8G` by script after stage 00 on a Slurm-template workspace. It runs against a pinned pre-T57 GARS commit (`--expect-commit`), where `lower` does not exist, so it is left as is and stays correct there (review finding 3, recorded as round 9 item 1 allows). When the exemplar's pin moves past T57, step `02.memory` becomes `configure.py lower` with its `history_entry`.
- **R6** Until glitch-b5 applies `lanes/gars-ms21/R6-registry.patch` at landing, the agent's spelling of `configure.py lower` is refused by the tool registry (R-092); the user runs it in their own terminal.

## Test

`gars/tests/test_venue_seeded_config.py`:
- `SeedTests.test_every_local_seed_is_within_the_ceiling`: the table names all seven assays on every venue, every local seed is at most `MEM_CEILING['local']`, Slurm and homelab seeds equal the base values, and `check()` refuses exactly above `MEM_CEILING['local']`.
- `SeedTests.test_a_local_workspace_seeds_memory_within_the_local_ceiling`: a workspace whose descriptor template names `local` seeds every assay within the ceiling, `check()` refuses none of them on a public/fixture row, and the created tree is the guard's `CREATE_STAMP`.
- `SeedTests.test_a_slurm_workspace_seeds_todays_bytes`: each template with its slot filled by the base value hashes to the base template's SHA-256, and a Slurm workspace seeds each file byte for byte.
- `LowerTests`: `test_lower_serves_every_assay_and_never_raises` (one subtest per assay, `spatialvi` included: dry run, real run, every other byte kept, a second run a no-op), `test_lower_leaves_other_venues_and_small_requests` (local at 4G, Slurm at 128G, homelab), `test_lower_refuses_without_writing` (two `mem:` lines, a second one outside `compute:`, an undecodable descriptor, an absent config, an unknown assay; a descriptor that is a directory and a `mem:` line that is not `compute.mem` are no-ops), `test_lower_takes_no_decision_argument`, `test_lower_offers_nothing_a_venue_refuses_anyway` (finding 2), `test_lower_keeps_line_endings_comment_and_mode`, `test_a_refused_replace_leaves_the_config` (a refused `os.replace` leaves the file and no temp file), `test_apply_is_unchanged_by_t57`.

`gars/tests/test_venue_policy.py`: `VenuePolicyTests.test_raising_seeded_memory_is_refused_naming_the_accepted_value` (9G and an unparseable value on a local stage 02 name the remedy; Slurm names none), and `SubmissionOrderingTests.test_analysis_memory_declarations` now also requires the accepted value and no `configure.py` on stage 03.

They must fail when the local seed is the Slurm value or `9G`, when `lowered_mem` ignores the request, when `lower` acts on a venue with no ceiling, when one template loses its slot, when `lower` is gated on `ASSAY_DECISIONS` (the spatialvi subtest), when `lower` resets `de.formula` or drops the line's comment, when the futile-lowering check is removed, when `create` shares one slot dict across assays, when the remedy moves into `check()`'s detail (the stage 03 case), when the remedy is dropped from `resource_unparseable`, and when the remedy is given on Slurm; the lane's mutation runs turned each red. `gars/tests/test_venue_policy_faults.py` stays green: its anchors `mem_bytes > 8 * 1024 ** 3` and `policy.check(row, venue_of(executed),` are unchanged.

## Status

Standing. Part 1 is implemented; its contract step and registry entry follow in this record as they land.

## Date

2026-10-18
