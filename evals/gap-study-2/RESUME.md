# RESUME — The Gap Study, round 2

**Working day 1 of 15** (cap: 30 slices or 15 working days from the kickoff commit, whichever comes first).
**Last progress-counting commit:** none yet.
**Slices spent:** 0 of 9 for this chunk (the kickoff commit will be `slice 01:`).

## Where it stands

CP0 (kickoff) is **built in the working tree, uncommitted and unpushed**.
The kickoff commit is the first commit touching `evals/gap-study-2/`, and it starts the clock.
CP0 is committed with its red suite recorded and is **not pushed**; CP1 makes the suite green and both push together.

What CP0 built:

- The copy: 41 of round 1's 505 archived files at `ac8662b`, by an explicit per-file list that stops on any unclassified file (464 left behind, 0 unclassified). `COPIED.json` records each file's round-1 blob, its sha256 as copied, and whether it has since been edited; `python3 evals/gap-study-2/copy_manifest.py --check` re-derives all of it and confirms `evals/gap-study/` is unchanged.
- `study.py` owns the study's name, paths and published-section markers; code paths, joins and markers in the copy go through it, and literal text was rewritten token-bounded. Leak and sweep patterns were left as round 1 wrote them, and `TheLeakPatternsStillSeeRoundTwo` proves they still see this study's name.
- The shadowing fix: this study's directory is ahead of `evals/` on `sys.path` in `check_results.py`, `check_take.py`, `run.py` and `test_harness.py`; `freeze.py` loads `drive.py` by path.
- The draft's identity: round 2's name, `kickoff_commit` null, drafted 13 September 2026, the round-2 session namespace, `system_under_test` at gars tree `8a54e0f8…` (not round 1's), harness `2.1.267`; the local tier removed. Every study path in the draft and in `freeze.PINNED` is round 2's, except the three listed in `round_1_data_paths`. `EveryPinnedPathIsRoundTwos` checks both, and two mutations point a draft grader path and a freeze pin back at round 1 (both red, each after a green control).
- The suite at kickoff: `verification/kickoff-suite.txt` (276 run, 12 failures, 9 errors, 26 skipped). The reds are the live-state reads CP1 replaces with owned fixtures (round 1's walks, scrub records, transcripts, `COSTS.md` and review history are not in this tree), plus the tests that read the removed local tier. Round 1's own suite is unchanged and green.

Steps 1 and 2, done alongside the build: `origin/main` was still `ac8662b` with gars tree `8a54e0f8`, and the aegis session confirmed it lands nothing on `main` until round 2's done commit. Round 1's review kit was read in full on Javier's OK and rescued byte-identical to a machine-only folder, never committed because it carries machine paths and account identifiers; `review_kit/PROVENANCE.md` records each file's sha256, and CP8 builds the committed kit from those bytes.

One absolute path remains in the copy, by design: `cases/scope-read.json:148` quotes a round-1 transcript line, and Decision 7 keeps the case suites byte-identical (the same line is in round 1's committed file).

## Next

**CP1 — the copy runs standalone, green, in CI (slice 02).** Owned fixtures for every live-state read, `EVALS_BASELINE` derived from history, pre-freeze branches in `check_results.py` / `costs.py` / `takes.py`, the contract quotes re-pinned at `ac8662b`, the allowlist re-ruled, `controls/results.json` regenerated, and the `gap-study-2` CI job.

## Open for Javier

J1–J4 in the plan (plan-gate approve regex, a scope-read `misanswered` label, what `asked-to-proceed` covers, stripping inherited session variables). The build does not wait; blind review 1 does.
