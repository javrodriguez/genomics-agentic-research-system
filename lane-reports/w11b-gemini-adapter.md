# Lane w11b-gemini-adapter: arm G's adapter, on documented shapes

Gap Study round 4; glitch-2f (Lane-orchestrator) under Javier's standing delegation.
Brief: plans/gap-study-round-4/next-slices-plan-2026-10-12.md section 2, "w11b-gemini-adapter", with ruling Q-3 (build on the documented Gemini CLI shapes now).
Branch gap4/w11b-gemini-adapter from f14ab57b; worktree /Users/javrodher/aegis-builds/gap4-w11b.
This report is appended to, never rewritten.

## Stage 1: the tests first (Mon 12 Oct 2026 15:49 EDT, `date`)

Committed: tests/test_gemini_adapter.py, 15 SYNTHETIC fixtures under tests/fixtures/gemini-streams/ with their README labels, COPIED.d/w11b-gemini-adapter.json and checks.d/w11b-gemini-adapter.txt.
Red on the base (gemini_adapter.py and transcript_gemini.py absent), /usr/local/bin/python3.13, behind mac_slot light-ok and `timeout -s INT 120`:

- `test_gemini_adapter.py`: Ran 116 tests, FAILED (failures=116), 0 errors; every failure an AssertionError (114 "Lists differ" naming the module's missing names, 1 the adapter's name, 1 the witness registry's missing file).
- `test_gemini_adapter.py --witnesses`: FAILED (failures=99), "0/98 red; registry 98".

Gates on this tree: copy_manifest, build_draft, freeze and walk_register `--check` exit 0; lint_language and lint_pooling clean.
