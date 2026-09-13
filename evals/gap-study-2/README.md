# The Gap Study, round 2

Round 2 asks round 1's question again: where the deterministic layer does not cover a failure mode, which model catches it, and in how many of n takes.
It runs against the system under test as it stands at `ac8662b` (gars tree `8a54e0f8`), which is not the tree round 1 measured.
Its harness began as a byte copy of round 1's (`COPIED.json` names every file, its round-1 blob and whether it has since been edited, and `copy_manifest.py --check` re-derives all of it), bound to its own name and paths through `study.py`.
Round 1 in `evals/gap-study/` is never edited, and round 1's transcripts are read here only as data.
Before any take, the copy fixes four instrument defects that reading round 1's transcripts exposed (the scope-read control answer, the plan-gate operator line, permission stops, and an unrecorded environment); each fix is shown on round 1's committed transcripts, and the design is pre-registered before any result exists.
**Status: pre-freeze, kickoff checkpoint. Nothing here has been graded.** Where the work stands is in `RESUME.md`.
