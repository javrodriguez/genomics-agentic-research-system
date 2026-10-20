Status: needs-review

## ROUND 2 SUMMARY FOR REVIEW (local executor, Tue 20 Oct 2026, 12:31 EDT / 16:31 UTC)

glitch-26's rulings on the design note (`444a0f1c`):
- **B21-2:** option (a). Promote exactly the four measured and grounded patterns, delete VENDOR_CANDIDATES, put a dated B21 docstring paragraph in, and update the COPIED.d reason line. Option (b), the config-mount families, is refused.
- **B21-7:** `.home/**` enters TABLE on R4-4's ruling. Its grounds line says it rests on that ruling, not on measured furniture, and records the measurement.
- **F21-1** (follow-up, not this lane): the CODEX_ALLOWED sessions row's `recorder.rs 984-1000` citation is stale at pin 092d3acd (the layout is at 1739-1762), recorded for the freeze's citation pass. box/run_take.py is untouched.

### Red commit `b068c80a` (tests only)

- New `tests/test_vendor_bookkeeping.py`:
  - B21-3a: w-o45's operator step. It calls `TakeDriver._operator_step` itself (with the box road stubbed) on a codex and a gemini row, for both explain-not-act's save and confounded-design's finalize copy.
  - B21-3b: `Evidence.load` with the production table on a measured-shape folder (`run_tree ""`, `home null`, `.home` and `.tmp` empty at pre-1; turn 1 writes `__pycache__`, `.git/index`, a `gars/projects` sheet, `.home/.cache/...` and `.tmp/run_stage00.py`).
  - B21-3c: the excluded-path guard, a save aimed into `.home`.
  - B21-4: the claude-code entry's repr is pinned to sha256 `cdc7989c...`, read at `28b46165`.
  - 13 mutants, run by `--witnesses`.
- `tests/test_harness_bookkeeping.py`:
  - `VendorCandidates` becomes `VendorEntries`, reading TABLE. The grounds checks now require the walks, the pinned source lines, B21-7's wording, and the absence of the old "unmeasured until a real walk" line.
  - A new test runs check_task's check 8 over the production TABLE.
  - `HomeExclusion` reads TABLE.
  - `TheTable.test_one_real_entry_named_as_the_adapter` now expects the three harnesses. It was `[ADAPTER_NAME]`. This is the one edit to a table-level test that is not vendor-only, flagged here.
- `tests/test_walk_grade_seam.py`: new `test_e_vendor_on_the_real_table_needs_no_synthetic_entries` (B21-5). The patched test is unchanged.

The runner's own lines on `28b46165`'s module:
- test_vendor_bookkeeping: `Ran 5 tests`, `FAILED (failures=3, errors=1)`. The operator-step red is w-o45's own text: "codex save: UnknownHarness: harness 'codex' has no bookkeeping entry (known: ['claude-code'])".
- test_harness_bookkeeping: `Ran 24 tests`, `FAILED (failures=2, errors=25)`.
- The new seam test alone: `Ran 1 test`, `FAILED (failures=1)`. Every vendor cell reads "NOT REACHED (EvidenceError: take.agent.harness: harness 'codex' has no bookkeeping entry ...)".

### Green commit `a65db53d`

- harness_bookkeeping.py:
  - `TABLE["codex"]` holds home `sessions/**/rollout-*.jsonl` and run tree `.home/**`.
  - `TABLE["gemini"]` holds home `.gemini/tmp/*/chats/session-*.jsonl` and run tree `.home/**`.
  - The grounds name the walks (12 of 12 codex; 5 of 6 gemini) and the pinned source lines (codex 092d3acd: `rollout/src/lib.rs:86`, `recorder.rs:1739-1762`, `rollout_file_name.rs:62-73`; gemini 0.64.0 `chunk-NR7L3FXV.js [C] 286708-286730`).
  - The B21-7 line: "rests on that ruling, not on measured furniture ... .home exists, empty, at pre-1 in the five walks launched after R-H5 (w-o15, w-o16, w-o17, w-o45, w-g11), and nothing appears under it in any snapshot".
  - A run-tree line per harness records the measured result: no run-tree furniture of its own beyond COMMON_EXCLUSIONS.
  - `not_excluded` keeps `.tmp/`, citing w-g5's script as its witness, and the config mount's other families, left out under B21-2.
  - VENDOR_CANDIDATES is removed, and a dated B21 docstring paragraph is in its place.
  - The claude-code entry is byte-identical.
- COPIED.d/w2a-cp3-endstate.json: harness_bookkeeping.py's reason is rewritten.
- COPIED.d/vendor-admission.json: claims `tests/test_vendor_bookkeeping.py`. Without that claim, copy_manifest and freeze refused the red tree.
- drive.py: unchanged (B21-6).

### Counts on the green tree

Each run used env -i with Python 3.13.2, after `mac_slot.py light-ok`; these are the runner's own lines.
- test_vendor_bookkeeping: `Ran 5 tests in 0.468s`, `OK`.
- test_vendor_bookkeeping --witnesses: `witnesses: 13/13 red`. The mutants, each red alone on its own check:
  - `.home/**` dropped (guard and load, each vendor);
  - `.home/*` narrowed (load);
  - `.tmp/**` added (load);
  - the entry removed (operator and load, each vendor);
  - the claude entry moved (claude).
- test_harness_bookkeeping: `Ran 24 tests in 1.851s`, `OK`. That includes the widened and moved home_paths mutants (12 patterns times 2, per vendor), the 8 entry mutants per vendor, the guessed `data/**` run tree caught by check 8, and check 8 on the production TABLE.
- test_walk_grade_seam (whole module): `Ran 4 tests in 1.128s`, `OK`. In the new test, the 18 vendor cells read 14 graded and 4 refused by their graders. None reads "has no bookkeeping entry".
- `harness_bookkeeping.py --check`: `harness_bookkeeping: ok: 3 harness(es): claude-code, codex, gemini`.
- `tasks/check_task.py --all` (check 8 iterates TABLE): exit 0 in 25.3 s, every task `ok (12 checks)`.
- copy_manifest --check: ok, 491 files from 60 fragments. freeze --check: `freeze: 492 owned paths checked`. build_draft --check: `ok: the committed draft is what build_draft.py builds`.
- check_vendor_sources P2 over the changed files: exit 0.
- Other modules that read TABLE: test_routing `Ran 297` OK (19 s); test_plan_gate `Ran 49` OK; test_task_scope_read `Ran 39` OK; test_task_confounded_design `Ran 84` OK; test_new_tasks `Ran 44` OK (31 s); test_vendor_admission `Ran 10` OK.

### Held for a ruling (one red)

test_endstate: `Ran 88 tests in 0.438s`, `FAILED (failures=1)`, the failure being `Seam.test_endstate_types_no_harness`: "Lists differ: ['.home'] != []".
- test_endstate is the other consumer that iterates TABLE (its `harness_strings`, test_endstate.py:527-539). It now takes each vendor's `.home` folder from `.home/**` and finds that text in graders/endstate.py. The four hits are attributes, not folders: `table).home_paths` (339), `take.home is null` (447), `self.home = run` (448), `self.home is not` (639).
- The attribute-aware form that test_harness_bookkeeping's `typed_harness` already uses for R4-4 (a lookbehind refusing an identifier, `)` or `]` before the dot) finds no hit in endstate.py. endstate types neither `codex`, `gemini`, `sessions` nor `.gemini`.
- On the base module, with these tests in place (the green change stashed), test_endstate ran `Ran 88 tests`, `OK`. So the red comes from the promotion meeting the scan, and it is a false positive.
- Not fixed: it is a Claude-arm test file (B21-4), and endstate.py is outside B21-6.
- Proposed fix, for glitch-26's call: in `harness_strings`, apply typed_harness's attribute rule to a dotted folder, and add a mutant asserting that `P = "/srv/t/.home/x"` still goes red. No product file changes.

### For athena's battery

These are longer than the Mac's 30-second bound, or were stopped by my 45-second cap; each needs its own runner line:
- test_variants (stopped by the cap);
- test_pipeline (stopped by the cap);
- test_drive_ownership, test_drive_loop, test_drive_box_seams, test_box_integration (they drive the operator step through the rig);
- the full checks.d/vendor-admission.txt and w2a-cp3-endstate.txt lines;
- the athena suite.

### Not touched

The records clone and athena's folders (read only, round 1). box/run_take.py, the scanner, drive.py, preflight, postflight, the adapters, the snapshots and the sidecar. Nothing was pushed. No regrade.json exists for any vendor walk (round 1, section 8 of the design note).

(round 2's stop, superseded by the B21-8 section's line below: review stop (round 2))

## ROUND 1 (local executor, Tue 20 Oct 2026, 12:18 EDT)

Design note lane-reports/vendor-b21-DESIGN.md, commit `444a0f1c`, design stop: 18 real walks were measured (paths and counts only); neither harness leaves run-tree furniture beyond COMMON_EXCLUSIONS; the four candidate patterns hold; the recommendation was option (a).

## B21-8 (local executor, Tue 20 Oct 2026, 12:47 EDT / 16:47 UTC)

glitch-26's ruling B21-8 on round 2's held red, and the folds from REVIEW-vendor-b21-8079cd7e.md (PASS: 0 MAJOR, 2 MINOR, 4 NIT).

- **B21-8** (`8079cd7e`): test_endstate's `harness_strings` applies typed_harness's attribute rule to a dotted folder, and the new witness `AgentHomeWitness` keeps a typed `"/srv/t/.home/x"` red.
  - This is not a Claude-arm behaviour change. The scan widened by itself when TABLE gained `.home/**`, and its hits were attribute names (`.home_paths`, `take.home`, `self.home`). No grader, no Claude path and no other assertion moved.
  - Runner lines: before, `Ran 88 tests`, `FAILED (failures=1)`; after, `Ran 89 tests`, `OK`.
  - Witnesses: endstate.py with the path literal appended gives `Seam.test_endstate_types_no_harness` `FAILED (failures=1)` (['.home'] != []). A rule that hides every dotted folder gives `AgentHomeWitness` `FAILED (failures=1)` ([] != ['.home']).
- **MINOR-1** (fold): this file is append-only again. Line 63's heading is back to its `e0b88590` text, the B21-8 bullet is out of "Not touched", and only the RESUME HERE line moved, to the end.
- **MINOR-2** (fold): COPIED.d/w2a-cp3-endstate.json's reason for tests/test_endstate.py gains one B21-8 sentence.
- **NIT-3** (fold): each harness's grounds cite only its own walks. Codex's measured `.home` line names w-o15, w-o16, w-o17 and w-o45; gemini's names w-g11. candidate_problems' required strings now follow suit, per harness.
- Runner lines on the folded tree, after light-ok (CPU speed limit 68):
  - test_harness_bookkeeping: `Ran 24 tests in 1.701s`, `OK`.
  - test_vendor_bookkeeping: `Ran 5 tests in 0.464s`, `OK`; `--witnesses`: `witnesses: 13/13 red`.
  - test_endstate: `Ran 89 tests in 0.570s`, `OK`.
  - harness_bookkeeping.py --check: `harness_bookkeeping: ok: 3 harness(es): claude-code, codex, gemini`.
  - copy_manifest.py --check: `ok: 491 files from 60 fragment(s) ...` (14.6 s).
  - freeze.py --check: `freeze: 492 owned paths checked; no takes or freeze performed` (15.3 s).
- Follow-ups, recorded only:
  - F21-1: CODEX_ALLOWED's sessions row cites `recorder.rs 984-1000`; at 092d3acd the layout is at 1739-1762. For the freeze's citation pass.
  - F21-2: the red commit `b068c80a` missed its COPIED.d claim, which landed in the green commit `a65db53d`; next time the claim rides with the red.
  - F21-3: rename `test_one_real_entry_named_as_the_adapter`, which now asserts three entries.
  - F21-4: the w-o45 reproduction drives `TakeDriver._operator_step` on a stand-in self; the real TakeDriver path is covered by test_drive_ownership, test_drive_loop and test_drive_box_seams in athena's battery.
  - F21-5: an ungraded, reported count of excluded `.home` changes per take, so writes through the agent HOME stay visible (the reviewer's O1). After round 4.
- Not touched: box/, drive.py, graders/, the adapters, the sidecar, .git/hooks, the records clone and athena. Nothing pushed.

(B21-8's stop, superseded by the B21-9 line below: review stop (B21-8 folded))

## B21-9 (local executor, Tue 20 Oct 2026, 14:13 EDT / 18:13 UTC)

- **B21-9** (glitch-26, after athena's battery passed `45239b01`: run `gap4-t5-b21-45239b0-45239b0-20261020T165144Z`, ran 1303, battery 363/363): `checks.d/vendor-admission.txt` gains the two lines `python3 -B -W ignore evals/gap-study-4/tests/test_vendor_bookkeeping.py` and the same with `--witnesses`, under a lane comment. Every other line is unchanged, and nothing pins the list's length (copy_manifest and freeze hash no checks.d line count). On the Mac, run from the repository root under `bash -o pipefail` after light-ok (CPU speed limit 100): the module gave `Ran 5 tests in 0.423s`, `OK` (0.6 s); `--witnesses` gave `witnesses: 13/13 red` (0.6 s); copy_manifest --check gave `ok: 491 files from 60 fragment(s) ...` (12.6 s); freeze --check gave `freeze: 492 owned paths checked; no takes or freeze performed` (12.4 s). Note for glitch-26: test_round4.py discovers every tests/test_*.py, and a discovery of this file alone loads 5 tests, so the module's tests should already sit inside the battery's 1303; what no battery ran was the --witnesses line. Why the total equals B20's was not checked here.

RESUME HERE: B21-9 committed; athena runs the two new lines in a walk pause.
