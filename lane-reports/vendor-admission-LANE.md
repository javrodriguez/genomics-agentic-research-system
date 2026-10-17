Status: planning

# Lane vendor-admission: groundwork for arms O (Codex) and G (Gemini)

Directed by glitch-b5, the Lane-orchestrator, under Javier's standing delegation. Opened Fri 16 Oct 2026, 21:01 EDT, on harness head a2ec7232 (athena battery PASS: gap4-ship-a2ec7232).
This file is the lane's contract: line 1 is the status (planning, running, needs-review, blocked, done or failed); keep Goal, Plan, Progress (dated, newest last) and RESUME HERE current.
Scope: tasks T0 to T3 of the brief below. T4 (vendor check readers) is NOT in this lane.

## glitch-b5 rulings
- T0: option (a). design_view admits codex and gemini rows; check4 and check4_walk keep harness_guard. The R4-guard test moves from 'design_view refuses' to 'check4 refuses', named in the commit. First prove the blocker exists, through the real walk_builders design_for wiring on fakes.
- Touch no READER_SOURCES or CODEX_SOURCES file (see the brief's sequencing hazard). If a task seems to need one, set Status: blocked and name it.
- Coverage from a regrade with no checker reading (pending_walk.py:86-88) is flagged for the T4 ruling, not changed here.
- The cloud's whole suite is red for environment reasons: run named modules only (the brief lists them). glitch-b5 runs the athena battery on your head.

## The brief (from a read-only planner, static read of 9d80c543; a2ec7232 adds only the OD57 scanner changes)

LANE BRIEF: vendor admission prep, arms O (Codex) and G (Gemini). Fixtures only, for a cloud executor.
Repo: /Users/javrodher/aegis-builds/gap4-live-harness-20261013, branch codex/gap4-live-harness-20261013, head 9d80c543. Code is under evals/gap-study-4/ (cited below as `D/`). Lane notes are under lane-reports/. Everything here comes from reading the code statically. I ran nothing.

## Goal
Build every fail-closed piece that arms O and G need after native-reader registration. That way, once Javier commits his acceptance records, the only work left is what real walk bytes alone can supply. Nothing this lane builds may open a production road for a vendor take that has no registered reader and no agreed cross-check.

## The gates a vendor take meets today, in road order
1. **Script, before turn 1.**
   - `walk_driver`'s `script_for` calls `design_for(row, None)` (D/drive.py:3788-3789).
   - The production `design_for` is `check_take.design_view` (D/walk_builders.py:942-946).
   - `design_view` calls `harness_guard` with no condition (D/check_take.py:2156-2157), and `HARNESSES_WITH_READERS = ("claude-code",)` (D/check_take.py:2014, 2111-2115).
   - So a production Codex or Gemini walk refuses before its first turn. This is by design: tests/test_checker_body.py:38 says "a codex or gemini row is refused by design_view and by check4".
   - The vendor pending-walk tests get round this by building `WalkDriver` directly with a synthetic `script_for` (D/tests/test_pending_walk.py:180-194). No test drives `walk_driver` plus the real `design_for` on a vendor row.
   - **This may block Javier's acceptance walks themselves.** I did not run it. Confirm it before any vendor walk is scheduled.
2. **Native cross-check.**
   - With no committed acceptance record, `production_readers()` returns `{}` (D/native_reader_registration.py:595-619).
   - `gemini_cross_check` and `codex_cross_check` then return "pending" (D/drive.py:3093-3134), and the drive raises `NativeCrossCheckPending` before the checker runs (D/drive.py:2869-2872).
   - The walk is committed as "pending-native-reader" (D/pending_walk.py:23-49; D/run.py:301-303).
3. **Checker, after registration.**
   - `take_checker` calls `design_for` and then `check4` or `check4_walk` (D/drive.py:3593-3614). Both call `harness_guard` (D/check_take.py:1933, 2385).
   - The round-3 `check()` body is a Claude Code session reader: session id, prompt snapshot, memory folder, model problems (D/check_take.py:1566-1780). The Claude-only round-4 checks are gated at D/check_take.py:1957-1963 and 2408-2414.
   - So even after registration, every production vendor take fails here with `CheckRefused`. The tests that "register a reader" use fake checkers (D/tests/test_vendor_checker_road.py:133; lane-reports/codex-registration-road-2026-10-14.md:49).
4. **End state.**
   - `_operator_check` (D/drive.py:2876-2878) and the graders (`run.grade_committed` and `grade_walk_folder`, D/run.py:238 and 282) call `Evidence.load`.
   - That reaches `agent_of` → `hb.entry` (D/graders/endstate.py:321-334, 383-438), which raises `UnknownHarness` for codex and gemini (D/harness_bookkeeping.py:78-113).
   - The vendor entries in D/tests/test_walk_grade_seam.py:186-193 are TEST DATA patched in with `mock.patch.dict`.
5. **Regrade of pending walks.**
   - `walk_regrade.regrade_doc` goes through `run.grade_walk_folder`, so it also needs gate 4 (D/walk_regrade.py:155-160).
   - It never runs the checker (D/walk_regrade.py:22-23).
   - Yet `pending_walk.coverage_status` counts a pending walk that a verified graded-true regrade supersedes as coverage (D/pending_walk.py:73-74, 86-88).
6. **Freeze.**
   - Both adapters say SHAPES_SOURCE = "documented", and the freeze is owed a refusal of any arm not re-tested on a recorded stream (D/codex_adapter.py:9-14, 90; D/gemini_adapter.py:9-14, 57-60, 93).
   - D/freeze.py has no reference to SHAPES_SOURCE: not built.

## Sequencing hazard (read first)
- The acceptance record binds `reader_sources_sha256` over READER_SOURCES and CODEX_SOURCES. Those lists include **drive.py, transcript_view.py, vendor_provenance.py, native_snapshot.py and native_reader_registration.py** (D/native_reader_registration.py:85-87, 160-161, 491-493).
- Any edit to those files after Javier's acceptance commit makes `production_readers` raise `RegistrationRefused` (fail-closed), and he would have to accept again.
- **This lane touches none of those files.** If a task seems to need one, stop and ask glitch-b5.
- The one known open item in them, `splitlines()` at D/native_reader_registration.py:414 (lane note harness-window2-resume:362-366), fails closed. Leave it alone unless glitch-b5 rules it in before acceptance.

## Tasks

### T0. A vendor walk can get its script (RULING FIRST: glitch-b5)
- **Files:** D/check_take.py (`design_view`) and tests/test_checker_body.py. Option (b) would also touch D/drive.py, which is forbidden after acceptance, so prefer (a).
- **Options for the ruling:**
  - (a) `design_view` admits codex and gemini rows, while `check4` and `check4_walk` keep `harness_guard` (D/check_take.py:1933, 2385). This keeps L-S6-1, "one design view feeds the lines sent and the checker" (D/drive.py:3629).
  - (b) A separate script view.
- **Red-first test:** build `walk_driver` with walk_builders' real `design_for` (constants from `CHECKER_CONSTANTS`) on a gemini row and on a codex row. `script_for(row)` must return the wording's steps. Today it raises `CheckRefused`.
  - Witness: `check4` and `check4_walk` on a vendor design still raise `CheckRefused`.
  - The R4-guard test changes from "design_view refuses" to "check4 refuses" only by ruling, and must be named in the commit.
- **Done:** a vendor row reaches turn 1 through the production wiring on fakes, and every checker entry still refuses vendors.

### T1. Vendor admission guard at the grading callers (defence in depth)
- **Files:** D/run.py (`grade_committed`, `grade_walk`, `grade_walk_folder`'s callers), D/walk_regrade.py:155-157, and a new test module. Not graders/, not endstate.
- **Behaviour:** for harness in {codex, gemini}, grading refuses unless both hold:
  - the registry the caller holds includes that harness (`production_readers()`, or `readers` passed in);
  - the cross-check record handed in is exactly `{"status": "agreed", "why": None}` (the shape at D/drive.py:3111-3112, 3132-3133).
- **Who supplies the cross-check:**
  - the take road and the walk road read it from the driver ledger's `cross_check_status`;
  - the regrade passes its own `cross` (D/walk_regrade.py:145-153), because the pending walk's ledger still says pending.
- claude-code is untouched.
- **Red-first tests:** with fake vendor TABLE entries in place, each of these must refuse, naming the reason:
  - an unregistered reader with an agreed cross-check;
  - a registered reader with a pending, refused or missing cross-check;
  - a cross-check dict with extra keys.
- Each test needs a mutant witness (the guard removed goes red).
- Extend tests/test_walk_grade_seam.py E-vendor so its fixture carries an agreed cross-check and injected readers. It must still reach every grader. Do not loosen its asserts.
- test_pending_walk `Regrade` and test_pending_codex_walk `CodexRegrade` must stay green, and they inject readers.
- **Done:** no road reaches `Evidence.load` for a vendor take without a registered reader and an agreed cross-check, even with vendor TABLE entries present.

### T2. Vendor bookkeeping candidates, not promoted
- **Files:** D/harness_bookkeeping.py (a new `VENDOR_CANDIDATES` dict beside TABLE, not in it) and tests/test_harness_bookkeeping.py (new tests only).
- **Codex candidate:**
  - home_paths `("sessions/**/rollout-*.jsonl",)`, grounded on CODEX_HOME = /opt/cfg (D/box/run_take.py:68, 162) and the rollout path (D/codex_adapter.py:41);
  - run_tree_paths `()`, with grounds saying "unmeasured until a real walk";
  - not_excluded should name `.tmp/` (TMPDIR in the run tree, D/box/run_take.py:93-94, 152-165).
- **Gemini candidate:**
  - home_paths `(".gemini/tmp/*/chats/session-*.jsonl",)`, grounded on GEMINI_CLI_HOME (D/box/run_take.py:165) and D/native_snapshot.py:7-18, including its stated assumption about the global temp dir;
  - run_tree_paths `()`, unmeasured.
- Note: production evidence records `"home": None` (D/drive.py:2762), and the sidecar snapshots only the run tree (D/box/sidecar.py:58). So home_paths are inert there, and only run_tree_paths will matter.
- **Red-first tests:**
  - each candidate passes `check_table`;
  - each grounds line re-derives from the cited source lines, the way `derived_session_pattern` does (D/tests/test_harness_bookkeeping.py:50-59);
  - mutants that widen a pattern go red;
  - `endstate.exclusion_conflicts` holds for every task under each candidate (D/tasks/check_task.py:944-946);
  - the `typed_harness` grader scan stays clean with the candidates added to its table (D/tests/test_harness_bookkeeping.py:257-275). Check that "sessions" and ".gemini" do not hit grader source. Fix the candidates, never the scan.
- Keep `sorted(hb.TABLE) == ["claude-code"]` (D/tests/test_harness_bookkeeping.py:124) asserted and unchanged.
- **Done:** candidates exist, grounded and tested. TABLE is unchanged, and production `Evidence.load` still refuses vendor takes.

### T3. The freeze refuses a documented-shapes arm
- **Files:** D/freeze.py and a new test module.
- **Behaviour:** freeze refuses while a design row's harness is codex or gemini and that adapter's SHAPES_SOURCE is not "recorded", naming the arm.
- **Red-first tests:** on fixtures, a draft with an O or G row refuses at "documented" and passes with a patched "recorded". A mutant with the check deleted goes red. claude-code rows are unaffected.
- **Done:** the freeze cannot pass an arm whose adapter was never re-tested on a recorded stream.

### T4. Vendor check readers (RULING FIRST: scope, from glitch-b5; probably its own lane)
- **Files:** D/check_take.py, as a new appended ruled span (precedent: lane note harness-window2-resume:219), and checks.d pins.
- **Behaviour:** `HARNESSES_WITH_READERS` gains codex and gemini only when a vendor `check()` exists. It reads the bound envelope (transcript_view.VendorBoundParser, D/transcript_view.py:619-630; `vendor_shell_commands`, D/check_take.py:3486), and a ruling must say which round-3 and round-4 reasons apply:
  - session binding (vendors mint their own ids: D/codex_adapter.py:22-24, D/gemini_adapter.py:23-25);
  - leaks, reach, operator lines, model, and inherited context.
- Build on documented shapes only, with fixtures labelled as such (ruling Q-3 precedent).
- **Done:** to be defined by the ruling. Until then it is not built.

## Must NOT be built until a real walk exists
- **Acceptance records and reviews** (native-readers/*-acceptance.json, *-review.md). Javier's step only. Pre-declared at D/copy_manifest.py:99-104. The SYNTHETIC gate refuses fixtures anyway (D/native_reader_registration.py:94, 551-556).
- **Vendor `run_tree_paths`, and promoting the candidates into TABLE.** What Codex and Gemini leave in the run tree (.tmp, cwd) is only visible in a walk's snapshots. A guessed `()` would let harness furniture read as agent changes, and a guessed pattern could hide them.
  - Promotion also changes regrade bytes, so promote **before** any regrade.json is committed. Otherwise `walk_regrade --check` stops re-deriving (D/walk_regrade.py:276-283).
- **SHAPES_SOURCE = "recorded" and RECORDED fixtures.** This needs recorded streams with provenance (D/tests/test_codex_adapter.py:708-711).
- **Regrades of pending walks** (walk_regrade `--walk` and commit). They need registration and final TABLE entries.
- **Re-testing T4 readers, vendor_store_violations and the native_snapshot assumptions against real bytes.** The open items are:
  - Codex exec options before `resume` (D/codex_adapter.py:29);
  - Gemini `-r` (D/gemini_adapter.py:23-25);
  - the Gemini temp dir (D/native_snapshot.py:16-18);
  - other Gemini tmp entries (lane note harness-window2-resume:528).

## Hard constraints
- No logins, no walks, no takes, no Docker, no network calls to any vendor. Fixtures and synthetic strings only.
- Never write native-readers/**, rehearsals/register.json, or any walk folder.
- Do not edit graders/** or D/graders/endstate.py.
- Do not touch READER_SOURCES or CODEX_SOURCES files (see the sequencing hazard).
- Never weaken a test or a witness:
  - an assertion changes only by a named ruling;
  - every new check has a mutant that goes red;
  - patch TABLE only in tests, and only via `mock.patch.dict`.
- Every new or edited owned file is claimed per copy_manifest. The gates the lane notes use must be clean: lint_language, copy_manifest, build_draft `--check`, the w6e and w6j byte checks, walk_regrade `--check`, and the gitleaks staged gate (harness-window2-resume:377, 401). I did not verify the exact command lines.
- The cloud whole suite is red for environment reasons, so run named modules only, under python3.12 with `env -u CLAUDE_CODE_MESSAGING_TOKEN`: test_harness_bookkeeping, test_endstate, test_walk_grade_seam, test_checker_body, test_walk_builders, test_native_reader_registration, test_pending_walk (about 170 s), test_pending_codex_walk, test_vendor_checker_road, test_vendor_take_records, test_codex_adapter, test_gemini_adapter, test_walk_wiring, plus the new modules. Do not start test_walk_runner whole, test_round4 or the generated shards.
- Commit red-first; never push to the real remote.

## Review threat model
- **Fail-open reader.** Any path where a missing record, an empty registry, or a reader exception reads as "agreed" or as an empty diff. Probe: `production_readers` returning `{}`, a `cross` of None, `UnknownHarness` swallowed, `try/except Exception` near the guards.
- **A reader that counts a take it cannot read.**
  - vendor rows admitted to `check4` with Claude readers;
  - a vendor `check()` that returns no problems on an unparsed envelope;
  - coverage counted from a regrade with no checker reading (D/pending_walk.py:86-88; flag it, and change it only by ruling).
- **Graders edited.** `git diff -- D/graders` must be empty, and test_no_grader_types_a_harness must stay green.
- **Bookkeeping that admits an unregistered reader.**
  - vendor names in TABLE before promotion is ruled;
  - T1's guard bypassable (a reader injected in production, the ledger's cross-check trusted on the regrade road);
  - `entry()` defaulting.
- **Gate drift.**
  - any edit to a READER_SOURCES file;
  - a weakened assert (`sorted(TABLE)`, R4-guard) not named in the commit;
  - the SYNTHETIC gate or the acceptance ordering touched.

## Size, honestly (agent-hours)
| Task | Build | Review folds |
|---|---|---|
| T0 | 2-4, after the ruling | |
| T1 | 4-6 | 1-2 |
| T2 | 3-5 | 1-2 |
| T3 | 3-5 | 1 |
| T4 | 16-30, scope-dependent | |

- T0 to T3 together: about 14-24.
- T4 is better as its own lane after the ruling.
- After the walks (not cloud): measure run_tree_paths, promote, add recorded fixtures and flip SHAPES_SOURCE, re-test T4, regrade. About 6-12 more.

## What I could not determine
- Whether the production walk runner really refuses a vendor row at `script_for`, and how walk_runner records a `CheckRefused` there. This is a static read only.
- Where Codex and Gemini write inside the run tree.
- Whether counting regraded vendor walks as coverage without a checker is intended.
- The Codex pinned CLI value (I did not read D/codex_native.py).
- The full set of round-3 `check()` reasons that would apply to vendors. I only listed its sub-checks.

### Critical Files for Implementation
- /Users/javrodher/aegis-builds/gap4-live-harness-20261013/evals/gap-study-4/check_take.py
- /Users/javrodher/aegis-builds/gap4-live-harness-20261013/evals/gap-study-4/run.py
- /Users/javrodher/aegis-builds/gap4-live-harness-20261013/evals/gap-study-4/harness_bookkeeping.py
- /Users/javrodher/aegis-builds/gap4-live-harness-20261013/evals/gap-study-4/freeze.py
- /Users/javrodher/aegis-builds/gap4-live-harness-20261013/evals/gap-study-4/native_reader_registration.py (read-only for this lane: it is a sequencing hazard)


## Progress
- 2026-10-16 21:01 EDT: lane opened by glitch-b5.

RESUME HERE: read this file, then start T0 (prove the blocker, then the fix).
