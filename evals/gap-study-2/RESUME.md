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

## CP1 — the copy runs standalone, green (slice 02)

**Built and gated on 13 September 2026; committed with this file, pushed together with the kickoff.**

- The suite reads no live state: 308 tests OK, and the 9 skips are exactly the three `…Live` checks, which skip only while `results/` has no results file. `TheSuiteNeverReadsLiveState` re-runs the suite with every live record refused.
- Mutation battery: exit 0, and all 121 guards went red when broken, 114 of them after a green control. The other seven run a command that writes, or have no unmutated form. No topic modules yet.
- `check_results.py` (default, `--ledger`, `--controls`, `--regrade`), `costs.py --check`, `contracts.py --check`, `fixtures/check_fixture.py --all`, `prereg.py --status` and `copy_manifest.py --check` all exit 0 on the empty study. The language guard is clean with one excused line, a byte-exact contract quote, re-ruled from empty.
- The negative controls at gars tree `8a54e0f8` give round 1's six verdicts and exit codes (see the plan-gate note in the commit body).
- A new CI job, `gap-study-2`, runs these at every pushed commit at full depth; the two existing jobs are unchanged.

CP1 was pushed with the kickoff; CI run 34785635654 on `5d58684` succeeded in all three jobs, and its log shows 308 tests and 121 guards red.

## CP2 — round 1's process lessons as guards, and the four operator tools (slice 03)

**Built and gated on 13 September 2026.**

- Not-applicable battery entries are evaluated predicates. The draft now carries `head_readers` (every HEAD read, each production reader with `--at <sha>`), `checklist_named_tests` (with the classes later checkpoints create listed as pending), and `done_line_12_mutations` (with the CP3 and CP4 entries pending). `EveryHeadReaderIsListed`, `TheChecklistNamedTestsExist` and `EveryDoneLineMutationIsRegistered` guard them.
- Tools: `commit_msg.py`, `ci_conclusion.py`, `clean_clone_battery.sh`, `check_checklist_names.py`, with `tests_tools.py` and `mutations_tools.py`. `test_harness.py` loads every `tests_*.py`; `mutations.py` registers every `mutations_*.py`.
- Suite: 365 tests OK, and the 9 skips are the three `…Live` classes. Battery: exit 0; all 135 guards went red when broken, 128 of them after a green control. `check_checklist_names.py` on the goal file exits 0.
- The clean-clone battery's output is committed in `verification/`, and the file names the tree it tested.

## CP3 — fix 4: the environment record, the stripped child environment, and two leak channels closed (slice 04)

**Built and gated on 13 September 2026.**

- Every take and walk now writes `environment.json` beside its transcript, before the first turn. It holds variable names only, never values: the names matching the published patterns, the stripped names, the presence of each API-key, billing-route and subscription-token variable, and the harness's own credential source on every turn. The driver stops before any session if an API key or a billing route is set.
- The child environment drops the twelve inherited Claude Code session names (J4). A name a harness pattern matches, or one on the three credential and billing lists, can never be stripped. The driver and the checker share that rule, and a drift test binds them.
- `check_take.py` refuses a graded take with no valid record (a walk gets a NOTE). The ledger counts records, the runner refuses symmetrically, and `COSTS.md`'s dollar line is written by the script, evidenced take by take or naming each gap.
- A new control refuses a session that reads, by absolute path, this repository's checkout, its parent or a sibling worktree. Measured on round 1's 124 transcripts first: it refuses 19 of them and none for a system read.
- Two leak channels were found by using the instrument and closed before any walk. Round 1's precondition-refusal fixture recorded the study checkout's path in files the agent reads, so every fixture is now built inside the run tree. The run tree also carried v1.0.1 documents that name the study, so those are excluded, and a whitelist test allows sweep hits only in README.md and docs/RESULTS.md, as in round 1.
- The environment smoke (`verification/env-smoke/`) ran on haiku and sonnet, unstripped and stripped. With the twelve stripped, headless login still opens a session and the agent replies, and the pairs differ only in those names. A subscription login reports the credential source `"none"`, now pre-registered. Sonnet records effort "high" with or without the inherited effort variable.
- Round 1's committed takes regraded by this instrument: 108 of 108 refused for no environment record, and $0 evidenced by 0 of 108 (`verification/round1-regrade/environment.json`, re-derived by its script).
- `ci_conclusion.py` resolves a short sha before asking CI.
- The read control was widened twice before any walk, after other agents' build copies of this repository appeared outside the checkout. It now also refuses any path under the home folder that is not under the take's run tree, and any path under the OS temp folder or `/tmp` that is not under the run tree or the harness's own session folder for that take. Measured on round 1's 124 transcripts, it refuses 21, and each newly refused one is a real read outside the take.
- Ruling C (14 September 2026): each take's TMPDIR, TMP and TEMP point at `.tmp/` inside its run tree, so tools that honour those variables keep their scratch inside the take. A take that types a literal `/tmp` path is still refused; round 1 has one, and whether to accept that as a limitation is open for Javier before the freeze.
- A fifth environment smoke ran under that temp folder; a one-line session creates no harness temp folder, so the first walk that runs a tool shows where the harness writes.

## Next

**The five walks** (`walk:` commits, no slice): template-adherence, precondition-refusal, number-fidelity, scope-read, confounded-design, each with `claude-sonnet-5`, each checked by `check_take.py` and read by eye. Then **CP4 — `asked-to-proceed` (slice 05).**

**CP1 as planned, for the record — the copy runs standalone, green, in CI (slice 02).** Owned fixtures for every live-state read, `EVALS_BASELINE` derived from history, pre-freeze branches in `check_results.py` / `costs.py` / `takes.py`, the contract quotes re-pinned at `ac8662b`, the allowlist re-ruled, `controls/results.json` regenerated, and the `gap-study-2` CI job.

## Open for Javier

Nothing on the instrument: J1–J4 were ruled on 13 September 2026 and are recorded in the goal file's Rulings. The approve detection is fixed in round 2 (J1); a wrong scope-read control answer is `misanswered` (J2); `asked-to-proceed` takes the broad reading, report-only stops included (J3); the twelve inherited Claude Code session variables are stripped from each take's environment (J4).
