## mission
Run genomics analyses through explicit human decisions. Then read `CLAUDE.md` (the workspace orientation),
`CONTEXT.md` and the stage contract the request maps to; execute it literally: Scope Boundaries bind, Response Format only, stop and ask before any deviation.
## architecture
Build specification: `../docs/specs/GARS_Unified_Master_Guideline_v1.0.1_FINAL.md`.
Workspace stage map: `CONTEXT.md`; helpers compute, contracts orchestrate.
## coding standards
`../CLAUDE.md`: preserve correct behavior; stdlib Python core; tests accompany changes.
## security policy
Specification §9 in `../docs/specs/GARS_Unified_Master_Guideline_v1.0.1_FINAL.md`;
current enforcement: `.claude/settings.json` (Claude Code), `.codex/hooks.json` (Codex) and `_system/guard_hook.py`; per-agent support: README "Runs on".
No "# Project state" render at session start means the guard is not loaded, and a render alone does not prove it is: approve both hooks, or stop and ask the human.
## testing policy
From the repository root: `python3 tests/run_tests.py` and
`python3 tests/check_contracts.py`. From `gars/`, first `cd ..`.
Row 1 alone: `python3 tests/test_stage01_design.py`; sealed inputs absent means skipped.
## memory policy
Specification §12 in `../docs/specs/GARS_Unified_Master_Guideline_v1.0.1_FINAL.md`.
Current records: project `HISTORY.md`; derived state: `_system/project_state.py`.
## Git policy
`../CLAUDE.md`: stage named paths only; no real data or patient-derived IDs in Git.
Do not push, approve, or merge your own work without owner authorization.
## change-control policy
Before editing, search `../docs/decisions/CONTEXT.md` for affected paths and read matches.
Unspecified material choices require a decision record, not an inferred scientific default.
## prohibited operations
`CONTEXT.md` and each stage's Scope Boundaries govern analyses. Specification R-074/R-094
in `../docs/specs/GARS_Unified_Master_Guideline_v1.0.1_FINAL.md` defines approval restrictions.
Do not claim these future controls are implemented; existing guards are listed above.
## definition of done
Specification §17 in `../docs/specs/GARS_Unified_Master_Guideline_v1.0.1_FINAL.md`.
Named exit tests must pass; missing sealed evidence remains unmeasured, never PASS.
