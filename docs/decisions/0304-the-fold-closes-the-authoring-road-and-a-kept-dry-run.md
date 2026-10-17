---
date: 2026-10-17
status: standing
kind: decision
touches:
  - gars/_system/authoring/create_bioinformatics_skill.py
  - gars/_system/configure.py
  - gars/02_bioinformatics/CONTEXT.md
  - gars/tests/test_history_model.py
  - gars/tests/test_status_writer.py
  - gars/tests/test_configure_confirm.py
  - gars/tests/test_r164_writer_recovery.py
  - gars/tests/test_render_methods.py
symptoms:
  - conform fails provenance on a wrapper whose collect reads args.model
  - "changed since the dry run was shown (it was edited, or that dry run was already written)"
  - a second apply after a write is refused with no new dry run
---
# The authoring road reads the harness's model, and a dry run is tied to the file it read

The fold of the review of lane gars-t74's runs 2 to 4 (`lanes/gars-t74/REVIEW-9eb28d9.md`), under glitch-b5's rulings of Sat 17 Oct 2026 (`lanes/gars-t74/RULINGS.md`, "Fold of REVIEW-9eb28d9.md"). It completes 0303 (the model comes from the harness) and 0302 (a config write equals the dry run shown); neither record is edited. The approval record for the `_system/` change is glitch-b5's at landing.

## Context

**Finding 1.** 0303 moved every shipped writer onto `ws.history_model`, but the authoring road that builds the next wrapper did not follow: conform checked only that `--model` is declared, the scaffolded SKILL.md told the agent to pass `--model "<model id>"`, and the scaffold's failure path called `collect_failure` with no model, so it recorded `unknown` even with a session file (NIT 2). Reproduced by the reviewer: the atacseq wrapper with `model = args.model or "unknown"`, the authoring checklist's reading, conformed.

**Finding 2.** 0302's record held the sha256 of the text a dry run would write, and was kept after the write. After dry run, write, and a hand edit of the contrast, an apply of the shown settings with no new dry run produced the same text the old dry run had shown, matched the record, and wrote the shown contrast back over the edit.

## Decision

1. conform's provenance rule: `cmd_collect` must call `ws.history_model(`, and a line that names `args.model` and builds the history entry or the run record (`Model:`, `history_entry`, `complete_manifest`, `collect_failure`, a `"model"` key, `manifest`) fails it. Mutation-tested in `gars/tests/test_history_model.py::AuthoringTests`.
2. The scaffold reads the session model before its exit gate and passes it to `collect_failure`; its SKILL.md collect line passes no flag. `test_status_writer.py`'s pinned generated line changes under ruling 1, quoted: "NIT 2 folds here: the generated wrapper's failure path (collect_failure) reads the same session model, so --model none and a session file reach it too; test_status_writer.py's pinned line changes under this named ruling."
3. `apply --dry-run` records, beside the text's sha256 and the settings, `read_sha256`: the sha256 of the config file it read. `apply` refuses when the file now differs, so an edit since the dry run, or that record's own write, needs a new dry run; a record is single-use after a write, as the stage 01 check record is (0300). A record without `read_sha256` is no record.
4. Assertion change under ruling 2 (single-use after a write): the tail of `test_same_arguments_write_the_bytes_the_dry_run_showed` asserted a repeat apply after the write succeeds with no new dry run; it now asserts the repeat is refused and the bytes kept. The frozen writer-recovery row `configure_apply` (Landing C) runs the dry run before every apply rather than once, its assertions unchanged.
5. The router's step 3a says the dry run records the config it read and a write happens once onto that config.
6. NIT 3: `test_render_methods`' two fixtures record a session model different from the flag's value, so they tell the two apart; no assertion changed.

## What this does not close

- **Exit code.** configure.py refuses with its own refusal code, 1 (`EXIT_REFUSED = 1` there, as every other configure refusal); ruling 2 said exit 2, the stage 01 code. Named for glitch-b5, not changed.
- **The pinned SKILL.md files** (five wrapper usage lines, spatial-cluster-count's model sentence, the authoring skill's lines 205 and 238) still name the flag until glitch-b5 applies `lanes/gars-t74/pin-skills.patch` with their re-pin (ruling 3).
- **conform reads lines, not data flow.** A wrapper that copies `args.model` into another name and records that name is not caught; the rule catches the shapes the reviewer reproduced.

## Test

`gars/tests/test_history_model.py::AuthoringTests` (5 tests): conform on four mutants of the atacseq wrapper (the checklist's `args.model or "unknown"`; the flag on the Model line, the `complete_manifest` call and the `collect_failure` call), every shipped wrapper still conforming, the scaffold reading the session model before its failure path, and the scaffolded SKILL.md collect line without the flag. `gars/tests/test_configure_confirm.py`: the reviewer's reproduction (dry run, write, hand edit, apply with no new dry run: refused, the edit kept), the record naming the file it read, and the repeat apply after a write refused.
Red at e03bdfd3 (`FAILED (failures=6, errors=1)`, with test_status_writer) and 62a2af25 (`FAILED (failures=2, errors=1)`). Mutations: conform's flag-on-a-line rule disabled `FAILED (failures=3)`; its history_model requirement disabled `FAILED (failures=1)`; apply's read check disabled `FAILED (failures=2)`.

## Status

Standing.

## Date

2026-10-17
