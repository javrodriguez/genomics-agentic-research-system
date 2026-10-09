status: blocked
RESUME HERE: glitch-f3 must rule on OPEN w5b-3, the copy-manifest policy for freeze-generated records, before this lane resumes implementation.

head: be1286f76e7d09a9222ec78a58460c67fccbdffb (unchanged base; no code commit was made; this report's own commit follows it).

## Blocking finding

The start block passed. Implementation stopped during interface inspection, before any code or manifest edit, under brief section 9's requirement to report a scope/owner question and stop.

R18 requires `freeze.py` to write `COPIED.json` once at the freeze (plan 395-398). The freeze also writes `prereg.json`. R20 requires `copy_manifest.py --check` against that frozen state (plan 1021-1031). The existing wave 1 checker has no generated-record exception:

- `copy_manifest.py:141-152` enumerates every file under the round, except untracked interpreter caches.
- `copy_manifest.py:302-304` refuses a claimed file that does not exist. Claiming the future outputs now therefore makes the build gate red.
- `copy_manifest.py:354-355` refuses every present, unclaimed file. Neither freeze output is currently claimed. Creating them with the current fragments therefore makes the frozen gate red.
- `copy_manifest.py:252-270` derives the assembled record from every fragment entry, including each entry's current file hash at line 260. Treating `COPIED.json` as an ordinary claimed input also raises the self-hash question: before its one write its hash is absent; afterwards it contains the snapshot rather than a hash of its own final bytes.

The bounded in-memory check below reproduced both unclaimed-file refusals without creating either artifact or running the freeze. The unchanged base's normal copy-manifest check passed first.

This is this lane's finding and request for a ruling, not a ruling attributed to glitch-f3 or Javier. PL-1 permits only eight ownership transfers and specific scaffold-test edits; it does not permit changing `copy_manifest.py`. PL-2 permits the separate stats default edit and does not address generated records. I did not silently add a runtime fragment rewrite, exclude the outputs through monkeypatching, weaken the checker, or leave a known frozen-state failure for CP6.

OPEN: w5b-3: What is the authorized policy for `COPIED.json` and `prereg.json` at freeze: a named exception allowing the wave 1 checker to recognize generated outputs, or an explicitly ruled generation/claim protocol with a non-circular assembled record? R18 (plan 395-398) and R20 (plan 1021-1031) require the outputs and the frozen-state check; `copy_manifest.py:302-304,354-355` refuses absent claims/present unclaimed outputs, and `:252-270` hashes every claimed input. Brief sections 3.1 and 5 keep that checker outside this lane's edits; PL-1 does not extend to it.

## Files and decisions

Only `lane-reports/w5b-cp5-pipeline.md` is added. At the recorded code head, `git -C /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline diff --stat be1286f7..HEAD` has no changes; the report commit follows that head. No pipeline, stats, test, checks, or copy-fragment file was edited. No round 4 records folder or placeholder was created.

PL-1 wave 1 changed-line inventory: none in `COPIED.d/w1a-cp1-scaffold.json`; none in `tests/test_scaffold.py`; no other wave 1 or wave 2 edits.

Lane decisions:

- Stop at the generated-record policy question rather than invent authority for a change to the frozen scaffold.
- Keep all implementation unstarted once this question is established. No red test commit or green implementation commit exists.
- R33 guard function: not implemented or named yet.
- R24 ruling door file/record path: not implemented or chosen yet; no ruling was written.
- Records destination: `evals/gap-study-4/records/`, as PL-2 already rules; not created. This is not this lane's naming decision.
- PL-3's closed ruling record and block derivation remain binding and unimplemented.

## Requirement and mutant accounting

“Not started” below means blocked at interface inspection; it is not an out-of-scope claim, a test pass, or proof of a red mutant. No requirement is reported complete.

| Requirement | Test name / evidence | Mutant | Red proven (runner closing line) / disposition |
|---|---|---|---|
| R1 | Not started | None | Eight edits and fragment transfer not made |
| R2 | Not started | None | Cell/harness keys not implemented |
| R3 | Not started | None | Route re-verification and views not implemented |
| R4 | Not started | None | Grader-path regression not implemented |
| R5 | Not started | None | Open-row guard not implemented |
| R6 | Not started | None | Per-call costs not implemented |
| R7 | Not started | None | Freeze pin coverage not changed |
| R8 | Not started | None | Stats-backed result renderer not implemented |
| R9 | Not started | None | `test_pipeline.py` not created |
| R10 | Not completed | None | Base manifest gate passes; CP8 finality and pipeline validation not established |
| R11 | Not started | None | Tokens, total cost, wall time and docstring not changed |
| R12 | Not started | None | Three stop views and strict holds not implemented here |
| R13 | Not started | None | Publication/registration cap integration not implemented |
| R14 | Not started | None | Recorded-route re-verification not implemented |
| R15 | Not started | None | Prior-round result comparison not removed |
| R16 | Not started | None | Empty-records renderer regression not implemented |
| R17 | Not started | None | v4 regrading regression not implemented |
| R18 | In-memory freeze artifact check, below | None; diagnostic only | `freeze artifact check: 2 of 2 required artifacts refused; 0 files written`; OPEN w5b-3 |
| R19 | Not started | None | No import edits or code staging performed |
| R20 | In-memory freeze artifact check, below | None; diagnostic only | `freeze artifact check: 2 of 2 required artifacts refused; 0 files written`; OPEN w5b-3; rehearsal command constant not implemented |
| R21 | Not started | None | Scratch-repo restart regressions not implemented |
| R22 | Not started | None | Slot freeing not implemented |
| R23 | Not started | None | Committed cell-state readers not implemented |
| R24 | Not started | None | Human door and ruled publication not implemented |
| R25 | Not started | None | Lost-outcome restart regressions not implemented |
| R26 | Not started | None | PL-3 block derivation not implemented |
| R27 | Not started | None | Window-event block validation not implemented |
| R28 | Not started | None | Ledger/results/table agent checks not implemented; preregistration writer remains section 7's next lane (CP5-req 42) |
| R29 | Not started | None | Pure pricing/cap/walk/month-turn functions not implemented; driver's call remains CP2's responsibility (CP5-req 57, section 7) |
| R30 | Not started | None | Design-derived task count not implemented |
| R31 | Not started | None | PL-2 destination/default edit and regressions not implemented |
| R32 | Not started | None | Excluded-view reader regressions not implemented |
| R33 | Not started | None | Repo-callable guard and fake-repo tests not implemented |

There is no completed-clause mutant table: no new production clause, test, or constant was written, and no whole-file mutant run was performed. The diagnostic is not counted as a committed mutant or as a completed requirement.

## Start checks

The brief's start block was run in its order, one shell call per command. The `W` assignment was repeated in calls that needed it because shell calls have separate environments.

1. `W=/Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline`; `test "$(git -C $W rev-parse HEAD)" = be1286f76e7d09a9222ec78a58460c67fccbdffb || { echo "STOP: HEAD is not the base be1286f76e7d09a9222ec78a58460c67fccbdffb"; exit 1; }` — exit 0, no output.
2. `test "$(git -C $W rev-parse --abbrev-ref HEAD)" = gap4/w5b-cp5-pipeline || { echo "STOP: not on gap4/w5b-cp5-pipeline"; exit 1; }` — exit 0, no output.
3. `git -C $W status --porcelain --ignored` — exit 0, no output. Repeated before the report write: still empty.
4. `git -C $W cat-file -t e2979b31 && git -C $W cat-file -t 68ec902f || { echo "STOP: an old commit is missing"; exit 1; }` — exit 0, two lines: `commit`, `commit`.
5. `git -C $W config --get-all core.hooksPath; echo "hooksPath read"` — output only `hooksPath read`. No configuration was changed and no hook was skipped.
6. `/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok; echo "light-ok exit $?"` — `light ok: load1 10.89 < 16.00 (memory pressure unreadable; light does not need it)`; closing line `light-ok exit 0`.
7. `/usr/local/bin/python3 --version` — `Python 3.13.2`.

All four pre-launch ruling slots were filled. No start STOP occurred.

## Checks actually run

Each check ran in the foreground, one process at a time, with `light-ok` immediately before it in the same command. No load hold occurred.

Exact baseline manifest command:

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/copy_manifest.py --check
```

Exit 0. Closing line, copied from the runner:

```text
ok: 215 files from 26 fragment(s) (w1a-cp1-scaffold, w1b-cp1-routing-batch, w2a-cp3-endstate, w2b-cp3-text-graders, w3a-cp3-graders-scope-template, w3b-cp3-graders-refusal-plangate, w3c-cp3-graders-confound-newtasks, w4a-cp2-image-egress, w4b-cp2-runtake-preflight, w4c-cp2-sidecar-scan, w4d-cp4-variants, w4e-cp5-stats, w4f-cp5-coverage, w4g-cp4-declarations-eligibility, w4h-w1b-next-touch, w4i-cp4-task-scope-read, w4j-cp4-task-template-adherence, w4k-cp4-task-number-fidelity, w4l-cp4-task-precondition-refusal, w4m-cp4-gen-plan-gate, w4n-cp4-gen-confounded-seed2, w4o-cp4-gen-explain-not-act, w4p-cp4-gen-approval-scope, w4q-cp4-gen-conditional-yes, w5a-cp5-probes4, wave4-merge): 48 identical and 5 edited (round 3 at e2979b31, shared files at 68ec902f), 162 new; 5 fixture builders byte-identical; 8 frozen paths unchanged since 68ec902f63bf
```

Exact bounded diagnostic command (the accessor's `present` argument changes only the in-memory inventory):

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore - <<'PY'
import sys
from pathlib import Path
root = Path('/Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4')
sys.path.insert(0, str(root))
import copy_manifest as cm
present = cm.files_here()
artifacts = {'COPIED.json', 'prereg.json'}
entries, shape = cm.load_fragments()
assert shape == [], shape
assert not artifacts & {entry['path'] for _, entry in entries}
base = cm.problems(present=present, pinned=False)
after = cm.problems(present=present | artifacts, pinned=False)
assert base == [], base
expected = [f'{name} is under {cm.study.STUDY_REL}/ and no fragment in COPIED.d/ claims it' for name in sorted(artifacts)]
assert after == expected, after
for problem in after:
    print(problem)
print('freeze artifact check: 2 of 2 required artifacts refused; 0 files written')
PY
```

Exit 0, confirming the diagnostic assertions, not a green frozen-state gate. Full diagnostic output after the load line:

```text
COPIED.json is under evals/gap-study-4/ and no fragment in COPIED.d/ claims it
prereg.json is under evals/gap-study-4/ and no fragment in COPIED.d/ claims it
freeze artifact check: 2 of 2 required artifacts refused; 0 files written
```

The normal manifest check ran before staging because this is a base-state investigation, not a completed-lane hand-back gate. No after-staging code gate is claimed.

## Work not run and boundaries

The pipeline, scaffold, batch, stats, pause-adherence, and module-load hand-back gates were not run: implementation stopped at OPEN w5b-3 before a code change or a hand-back candidate existed. No test was skipped by a test runner. The full battery and `run_checks.py` remain owed to glitch-f3 on athena after implementation; neither ran here. No whole-file audit, freeze, rehearsal, driver, model, container, real ledger registration, ruling door, or network command ran.

The leak-grep docstring was read. It documents only the default and `--check`, not a path argument, so no scoped leak-grep was run. No task wording, fake take wording, or holdout wording was written. No sealed path, login file, or `.env` file was read. No external source document was read. No subagent was spawned.

Refusals/denials: no tool, classifier, sandbox, or commit-hook denial was encountered before this report. The two manifest refusals above are the expected in-memory diagnostic result; their command and exact messages are recorded above. They were not bypassed.

## Deferred to Javier

Spend, keys, real prices, the caps-trimmed record and both figures, public pushes, and any ruling requiring Javier's own word remain deferred. None was requested or supplied, and no real vendor/account data was written. OPEN w5b-3 is addressed to glitch-f3 under the lane's existing delegation, not attributed to Javier.


---

## Append-only continuation after ruling w5b-3

status: blocked
RESUME HERE: glitch-f3 must rule on OPEN w5b-4, ownership of non-freeze runtime outputs, before implementation resumes.

This continuation supersedes the historical RESUME HERE and requirement accounting above. The original report at ed8d2d58 is preserved byte for byte as instructed. Its w5b-3 question is CLOSED by glitch-f3's supplied ruling of 9 October, 12:41 EDT; that old OPEN line is historical, not an active question.

Recorded after reading `date`: `Fri Oct  9 13:41:35 EDT 2026`.

head: 590f4cfcd512c4ccfa11bd8c4bf4e78441073a5c (last code/test/checks commit; this append-only report's own commit follows it). Branch remains gap4/w5b-cp5-pipeline. Every diff uses be1286f7; startup accepted ed8d2d58 under the resume instruction.

### New blocking finding: non-freeze outputs have the same ownership boundary

The resumed implementation meets w5b-3's three-output protocol in scratch repositories. Build-time and post-freeze `copy_manifest.problems()` both return no problems; COPIED.json equals derive() over the build fragments without freeze.json; all three outputs land in one scratch commit; a second write is refused. The committed test also removes the claims in memory and observes the unclaimed-file refusals. No real freeze ran.

While connecting the rehearsal to these outputs, the next boundary became concrete. `freeze_rehearsal.py` writes a synthetic pre-freeze report before calling freeze.py (current lines 145-153). The report is not claimed. The copy checker therefore refuses before the freeze. It also refuses the later rehearsal record, ledger, outcomes, rulings, records and publication files. w5b-3 authorizes a fragment claiming exactly COPIED.json, prereg.json and itself; it does not name a protocol for any of these other outputs. PL-1 does not allow rewriting frozen build fragments or the wave 1 checker. CP2 also owns writing outcomes, so the runtime protocol must be shared with that lane.

`UnclaimedOutputs.test_nonfreeze_outputs_need_an_authorized_claim_protocol` reproduces the boundary without executing the rehearsal, driver or any real ledger door: after a green synthetic freeze in a scratch git repository, it creates nine synthetic output files. The checker returns exactly nine unclaimed-file findings, one for each of:

- review_kit/prefreeze-1.md
- verification/freeze-rehearsal-1.txt
- takes.json
- outcomes.json
- rulings.json
- records/synthetic-task.json
- RESULT.md
- cost-calls.json (this lane's proposed normalized per-call input)
- COSTS.md

The test asserts each finding starts with the specific path and contains `no fragment`. These are synthetic marker bodies, not actual takes or a proposed output schema. The diagnostic is not a mutant proof or a proposed policy. No runtime fragment was added and no wave 1 checker was edited. An exploratory, uncommitted test requiring a rehearsal claim helper failed; after recognizing the scope boundary it was replaced with this passing diagnostic, without adding the unauthorized helper.

OPEN: w5b-4: What claim protocol is authorized for non-freeze runtime outputs (rehearsal/review reports, takes.json, outcomes.json, rulings.json, records/*.json, RESULT.md and cost records), including fragment ownership, append/update behavior and their relationship to freeze pins? R1/R18 (plan 809 and 395-398), R20 (plan 1021-1031), R24 (CP5-req 25-30), R28 (CP5-req 42) and R31 (CP5-req 193) require these producers/readers and the copy gate; copy_manifest.py:141-152,302-304,354-355 refuses absent claims or present unclaimed outputs. Sections 3.1 and 5 prohibit editing the wave 1 checker, and the w5b-3 ruling names only the three freeze outputs. This lane requests a named protocol, including the CP2 outcome producer, rather than extending w5b-3 itself.

This is a blocked implementation checkpoint, not a CP5/CP8-ready hand-back. No requirement below is certified complete until its remaining integration and whole-file mutant proof are done.

### Files changed

The following is `git -C W diff --stat be1286f7..HEAD` at the code head. The report's 155-line count is the original report; this continuation is added in the following report commit.

```text
 evals/gap-study-4/COPIED.d/w1a-cp1-scaffold.json |   40 -
 evals/gap-study-4/COPIED.d/w5b-cp5-pipeline.json |   68 ++
 evals/gap-study-4/check_results.py               | 1052 +++++-----------------
 evals/gap-study-4/checks.d/w5b-cp5-pipeline.txt  |   16 +
 evals/gap-study-4/completeness.py                |  143 +--
 evals/gap-study-4/costs.py                       |  643 ++++---------
 evals/gap-study-4/freeze.py                      |  578 ++++--------
 evals/gap-study-4/freeze_rehearsal.py            |   53 +-
 evals/gap-study-4/result.py                      |  399 ++------
 evals/gap-study-4/run.py                         |  511 +++++------
 evals/gap-study-4/stats.py                       |    2 +-
 evals/gap-study-4/takes.py                       |  666 ++++++--------
 evals/gap-study-4/tests/test_pipeline.py         |  963 ++++++++++++++++++++
 evals/gap-study-4/tests/test_scaffold.py         |   17 +-
 evals/gap-study-4/tests/test_stats.py            |    2 +-
 lane-reports/w5b-cp5-pipeline.md                 |  155 ++++
 16 files changed, 2443 insertions(+), 2865 deletions(-)
```

The eight pipeline files are all transferred from w1a's fragment into this lane's fragment as edited copies with round 3 source paths and requirement reasons. The three new round files (test, fragment, checks) are claimed. No placeholder or real record was added. stats.py remains claimed by its original lane; only PL-2's default line changes.

### Exact PL-1 and PL-2 changed-line inventory

This zero-context diff lists every changed line in both wave 1 files, followed by PL-2's two one-line cross-lane changes. No other line of either wave 1 file changes. In w1a's fragment the removed base ranges are 34-38, 59-63, 80-84, 125-134, 182-186, 227-231 and 258-262: exactly the eight transferred entries. The unchanged `sys.path.insert(0, str(HERE))` remains in takes.py, and freeze_rehearsal.py retains its freeze, scratch_git and study imports.

```diff
diff --git a/evals/gap-study-4/COPIED.d/w1a-cp1-scaffold.json b/evals/gap-study-4/COPIED.d/w1a-cp1-scaffold.json
index 657c60af..b5a05752 100644
--- a/evals/gap-study-4/COPIED.d/w1a-cp1-scaffold.json
+++ b/evals/gap-study-4/COPIED.d/w1a-cp1-scaffold.json
@@ -34,5 +33,0 @@
-    {
-      "path": "check_results.py",
-      "status": "identical",
-      "source": "evals/gap-study-3/check_results.py"
-    },
@@ -59,5 +53,0 @@
-    {
-      "path": "completeness.py",
-      "status": "identical",
-      "source": "evals/gap-study-3/completeness.py"
-    },
@@ -80,5 +69,0 @@
-    {
-      "path": "costs.py",
-      "status": "identical",
-      "source": "evals/gap-study-3/costs.py"
-    },
@@ -125,10 +109,0 @@
-    {
-      "path": "freeze.py",
-      "status": "identical",
-      "source": "evals/gap-study-3/freeze.py"
-    },
-    {
-      "path": "freeze_rehearsal.py",
-      "status": "identical",
-      "source": "evals/gap-study-3/freeze_rehearsal.py"
-    },
@@ -182,5 +156,0 @@
-    {
-      "path": "result.py",
-      "status": "identical",
-      "source": "evals/gap-study-3/result.py"
-    },
@@ -227,5 +196,0 @@
-    {
-      "path": "run.py",
-      "status": "identical",
-      "source": "evals/gap-study-3/run.py"
-    },
@@ -258,5 +222,0 @@
-    {
-      "path": "takes.py",
-      "status": "identical",
-      "source": "evals/gap-study-3/takes.py"
-    },
diff --git a/evals/gap-study-4/stats.py b/evals/gap-study-4/stats.py
index abec8e22..8ef33c8f 100644
--- a/evals/gap-study-4/stats.py
+++ b/evals/gap-study-4/stats.py
@@ -121 +121 @@ labels4 = _load("gap4_labels4", HERE / "graders" / "labels4.py")
-RESULTS_DIR = HERE / "results"
+RESULTS_DIR = HERE / "records"
diff --git a/evals/gap-study-4/tests/test_scaffold.py b/evals/gap-study-4/tests/test_scaffold.py
index 36ad751e..11aa5bf4 100644
--- a/evals/gap-study-4/tests/test_scaffold.py
+++ b/evals/gap-study-4/tests/test_scaffold.py
@@ -41 +40,0 @@ BLOCKED = {
-    "run.py": "ModuleNotFoundError: No module named 'labels'",
@@ -150,2 +149,2 @@ class TheManifest(unittest.TestCase):
-        bad = cm.problems(pinned=False, present=present - {"takes.py"})
-        self.assertTrue(any("takes.py" in b and "does not exist" in b for b in bad), bad)
+        bad = cm.problems(pinned=False, present=present - {"prereg.py"})
+        self.assertTrue(any("prereg.py" in b and "does not exist" in b for b in bad), bad)
@@ -158 +157 @@ class TheManifest(unittest.TestCase):
-                if e["path"] == "takes.py":
+                if e["path"] == "prereg.py":
@@ -163 +162 @@ class TheManifest(unittest.TestCase):
-            self.assertTrue(any("takes.py" in b and "it is a copy and must say so" in b for b in bad), bad)
+            self.assertTrue(any("prereg.py" in b and "it is a copy and must say so" in b for b in bad), bad)
@@ -373 +372 @@ class TheManifest(unittest.TestCase):
-        takes = cm.source_bytes("evals/gap-study-3/takes.py")
+        takes = cm.source_bytes("evals/gap-study-3/prereg.py")
@@ -375 +374 @@ class TheManifest(unittest.TestCase):
-            ({"path": "takes.py", "status": "identical", "source": "evals/gap-study-3/takes.py", "reason": "x"},
+            ({"path": "prereg.py", "status": "identical", "source": "evals/gap-study-3/prereg.py", "reason": "x"},
@@ -377 +376 @@ class TheManifest(unittest.TestCase):
-            ({"path": "takes.py", "status": "identical"}, "names no source"),
+            ({"path": "prereg.py", "status": "identical"}, "names no source"),
@@ -383 +382 @@ class TheManifest(unittest.TestCase):
-            ({"path": "takes.py", "status": "identical", "source": "evals/gap-study-3/no-such-file.py"},
+            ({"path": "prereg.py", "status": "identical", "source": "evals/gap-study-3/no-such-file.py"},
diff --git a/evals/gap-study-4/tests/test_stats.py b/evals/gap-study-4/tests/test_stats.py
index b9d3f924..4573f6b9 100644
--- a/evals/gap-study-4/tests/test_stats.py
+++ b/evals/gap-study-4/tests/test_stats.py
@@ -148 +148 @@ class TheModuleIsRound4s(unittest.TestCase):
-        self.assertEqual(stats.RESULTS_DIR, HERE / "results")
+        self.assertEqual(stats.RESULTS_DIR, HERE / "records")
```

### Lane decisions and implemented interfaces

These are this lane's implementation decisions, not new rulings by glitch-f3 or Javier:

- R33: `takes.guard_registration(row, attempt, rows, history, live=...)` is the repo-callable guard. `RegistrationGuard` retains only this process's live block; `registered` is called after its commit succeeds. Restarts have an empty live set. A registered row without a committed outcome refuses registration until reconciled.
- `takes.commit_registration` commits one full planned identity to takes.json's closed `{"rows": [...]}` document. `row_commits` checks one appended row per commit and refuses rewritten history. The frozen design's `rows` supplies the planned identities and metadata; it is not synthesized from model names.
- R24: `takes.commit_ruling` is the human door in takes.py. It appends one record with exactly batch.RULING_KEYS to `evals/gap-study-4/rulings.json` and commits it. The caller's `by` is mandatory, never defaulted from git or an environment variable. `takes.read_history` reads outcomes.json and rulings.json in commit order, requiring one appended outcome/ruling per commit. This is the interface for CP2's history(), whose real repo object remains outside this lane.
- R2: half-cell keys delegate to stats and include arm/task/half/model/agent.harness; try keys add wording and the repeat-or-pressure level. Opaque batch half_cell/slot IDs are checked against these identities.
- PL-3: publication derives the ruled pause's block from committed outcomes, refusing absent or ambiguous membership. It counts a block's existing window event once, with no seventh ruling key. This implements W1B4-3's purpose by derivation under the supplied ruling.
- PL-2: records/ is the ruled destination, not this lane's naming decision. run.py writes lists there; result.py and check_results.py read it explicitly. stats.RESULTS_DIR is records, and its no-argument CLI test sees one synthetic take. The legacy dictionary-with-cells shape is refused.
- Regrading loads local v4 files with spec_from_file_location and returns the module path in its grade audit. Stop standings use the closed labels and three views. result.py delegates every statistics table to stats; completeness uses the design task list and committed mechanical states.
- Cost input is a normalized list keyed by (vendor, call_id). Exact duplicate fragments count once; conflicting duplicates refuse. The supplied dated table prices tokens per million; printed total_cost_usd is summed once per call, separately from that calculated price. Missing measurements stay unmeasured. Tests use invented prices only.
- Round cap arithmetic totals all vendor-read spend since the injected round start, across months. The month predicate requires a dated Javier caps-trimmed record with both figures for the current month (or next month once the last-day 23:30 hold begins); it never releases a hold merely because time passed. The driver's invocation is CP2's.
- Freeze pins all claimed build paths, including prose, checks, this builder and COPIED.d. Generated COPIED.json and freeze.json have byte pins in prereg.json. prereg.json binds itself through its introducing commit. The snapshot remains exactly the pre-output derive(), as w5b-3 requires.
- Freeze's proposed round 4 take_order is a deterministic permutation of complete design rows, seeded by the review commit; agent identities are preserved and no vendor CLI is invoked. This still needs the integration work below before it is usable at CP8.

### Requirement accounting

`NR` means the whole-file mutant swap has NOT been run, so there is no red closing line to claim. Named mutants are defined for future `test_pipeline.py --mutant NAME` runs; many tests already assert local in-memory guard removal, but that is not the required whole-file proof. All named tests below are in test_pipeline.py unless qualified. No item is silently declared out of scope.

| Requirement | Named test(s) / current evidence | Mutant(s) | Red proven / remaining disposition |
|---|---|---|---|
| R1 | TheManifest.test_check_passes_on_the_folder; FreezeCoverage.test_every_owned_path_is_pinned_including_fragments_and_prose | pin-all | NR; eight ownership transfers pass the build copy gate |
| R2 | InterfaceRecords.test_keys_include_arm_half_wording_level_and_harness | key-harness | NR |
| R3 | PublicationHistory.test_every_route_is_reverified_without_replacement; InterfaceRecords.test_every_stop_has_three_views_and_aborted_counts_against_holding | recorded-route, stop-view | NR |
| R4 | InterfaceRecords.test_regrade_uses_v4_file_even_with_same_named_module_cached | bare-grader | NR |
| R5 | Registration.test_live_block_three_restart_requires_reconciliation; test_four_open_mutant; test_routes_free_slots_only_with_committed_rerun | stale-row, four-open, final-slot | NR; ruled rerun integration remains |
| R6 | CostAccounting.test_per_call_usage_printed_cost_and_wall_time | per-call | NR |
| R7 | FreezeCoverage.test_every_owned_path_is_pinned_including_fragments_and_prose; FreezeDesign.test_generated_outputs_are_pinned_in_the_frozen_file | pin-all, output-pins | NR; runtime fragment policy blocked |
| R8 | Reporting.test_every_table_comes_from_stats_and_no_prior_round | result-tables | NR |
| R9 | PublishedArtifacts.test_produce_drives_fake_takes_through_all_routes; Reporting.test_empty_records_print_no_takes_never_zeros | empty-result, records-shape | NR |
| R10 | 42-test green and copy-manifest green | not yet complete | Blocked: CP8 finality is not established |
| R11 | CostAccounting.test_per_call_usage_printed_cost_and_wall_time; test_pricing_requires_dated_table_and_agent | per-call, price-date | NR; nonempty cost CLI remains |
| R12 | InterfaceRecords.test_every_stop_has_three_views_and_aborted_counts_against_holding; unchanged stats strict-view tests | stop-view | NR |
| R13 | Registration.test_routes_free_slots_only_with_committed_rerun; PublishedArtifacts.test_produce_drives_fake_takes_through_all_routes | final-slot, ruled-state | NR; complete cap/ruled-registration integration remains |
| R14 | InterfaceRecords.test_runner_reverifies_in_addition_to_publication_checker | runner-route, recorded-route | NR |
| R15 | Reporting.test_every_table_comes_from_stats_and_no_prior_round | prior-round | NR |
| R16 | Reporting.test_empty_records_print_no_takes_never_zeros; StatsDestination.test_no_argument_cli_reads_records_and_legacy_shape_is_refused | empty-result, stats-default | NR |
| R17 | InterfaceRecords.test_regrade_uses_v4_file_even_with_same_named_module_cached | bare-grader | NR |
| R18 | FreezeOutputs.test_build_and_frozen_manifest_and_snapshot; test_missing_claim_mutant_is_refused; test_second_freeze_refused_before_any_write | freeze-snapshot, freeze-claims, freeze-once | NR; w5b-3 protocol implemented, w5b-4 blocks other output claims |
| R19 | FreezeCoverage.test_rehearsal_keeps_every_required_command_even_when_missing; TheImports.test_the_named_imports_resolve_here | existing scaffold import mutant; rehearsal-commands | NR; index checks were staged first |
| R20 | FreezeCoverage.test_rehearsal_keeps_every_required_command_even_when_missing | rehearsal-commands | NR; constant includes all nine commands, rehearsal runtime incomplete |
| R21 | Registration.test_live_block_three_restart_requires_reconciliation; test_four_open_mutant | stale-row, four-open | NR |
| R22 | Registration.test_routes_free_slots_only_with_committed_rerun | final-slot | NR |
| R23 | Reporting.test_mechanical_state_read_even_without_a_graded_record; Registration.test_committed_cell_state_refuses_new_slot | committed-state, closed-cell | NR |
| R24 | RulingDoor.test_door_commits_one_closed_record_with_callers_by; test_door_refuses_unknown_word_and_empty_by_with_mutants; PublicationHistory.test_ruled_half_cell_closes_from_the_ruling; test_ruled_take_publishes_under_the_ruled_route | ruling-word, ruling-by, ruled-state, ruled-route | NR; door output ownership blocked |
| R25 | Registration.test_lost_drive_and_lost_pause_never_launch_on_restart | stale-row | NR |
| R26 | PublicationHistory.test_ruled_pause_counts_its_existing_block_once; test_ruled_pause_requires_unique_block_and_existing_take | pause-block | NR |
| R27 | PublicationHistory.test_window_event_must_fit_one_block | window-span | NR |
| R28 | InterfaceRecords.test_agent_missing_refused_by_ledger_and_records; LedgerDoor.test_registration_commits_the_full_planned_identity_and_audits_it; PublishedArtifacts.test_checker_binds_records_page_agent_and_final_route | row-agent, design-row, published-page | NR; preregistration writer outside lane (CP5-req 42; section 7) |
| R29 | CostAccounting.test_round_caps_use_all_months_and_all_models; test_month_turn_refuses_until_both_figures_recorded; test_pricing_requires_dated_table_and_agent | round-spend, walk-cap, month-hold, price-date | NR; driver invocation outside lane (CP5-req 57; section 7) |
| R30 | Reporting.test_pair_count_comes_from_nine_task_design | task-count | NR |
| R31 | StatsDestination.test_no_argument_cli_reads_records_and_legacy_shape_is_refused; InterfaceRecords.test_record_lists_written_only_in_records_and_legacy_shape_refused | stats-default, records-shape | NR; stats.py:121 and tests/test_stats.py:148 are the exact PL-2 touches |
| R32 | Reporting.test_excluded_dict_no_takes_and_only_stops_all_render | result-tables (shared; shape-specific proof still needed) | NR |
| R33 | Registration.test_lost_drive_and_lost_pause_never_launch_on_restart; test_live_block_three_restart_requires_reconciliation | stale-row | NR; CP2 real repo object outside lane (CP2-req 41; section 7) |

### Mutant inventory at this blocked checkpoint

No whole-file mutant audit was completed. Early attempted mutant commands encountered light holds and launched no test process; they are not evidence of red or green. The blocked boundary was found before the final audit stage. Each row below remains NR; the local 42-test green does not satisfy that separate requirement.

| Clause | Mutant | Whole test_pipeline run red or green | Test name |
|---|---|---|---|
| R1, R7 | pin-all | NR — not run | TheManifest.test_check_passes_on_the_folder; FreezeCoverage.test_every_owned_path_is_pinned_including_fragments_and_prose |
| R2 | key-harness | NR — not run | InterfaceRecords.test_keys_include_arm_half_wording_level_and_harness |
| R3, R14 | recorded-route | NR — not run | PublicationHistory.test_every_route_is_reverified_without_replacement; InterfaceRecords.test_every_stop_has_three_views_and_aborted_counts_against_holding |
| R3, R12 | stop-view | NR — not run | PublicationHistory.test_every_route_is_reverified_without_replacement; InterfaceRecords.test_every_stop_has_three_views_and_aborted_counts_against_holding |
| R4, R17 | bare-grader | NR — not run | InterfaceRecords.test_regrade_uses_v4_file_even_with_same_named_module_cached |
| R5, R21, R25, R33 | stale-row | NR — not run | Registration.test_live_block_three_restart_requires_reconciliation; test_four_open_mutant; test_routes_free_slots_only_with_committed_rerun |
| R5, R21 | four-open | NR — not run | Registration.test_live_block_three_restart_requires_reconciliation; test_four_open_mutant; test_routes_free_slots_only_with_committed_rerun |
| R5, R13, R22 | final-slot | NR — not run | Registration.test_live_block_three_restart_requires_reconciliation; test_four_open_mutant; test_routes_free_slots_only_with_committed_rerun |
| R6, R11 | per-call | NR — not run | CostAccounting.test_per_call_usage_printed_cost_and_wall_time |
| R7 | output-pins | NR — not run | FreezeCoverage.test_every_owned_path_is_pinned_including_fragments_and_prose; FreezeDesign.test_generated_outputs_are_pinned_in_the_frozen_file |
| R8, R32 | result-tables | NR — not run | Reporting.test_every_table_comes_from_stats_and_no_prior_round |
| R9, R16 | empty-result | NR — not run | PublishedArtifacts.test_produce_drives_fake_takes_through_all_routes; Reporting.test_empty_records_print_no_takes_never_zeros |
| R9, R31 | records-shape | NR — not run | PublishedArtifacts.test_produce_drives_fake_takes_through_all_routes; Reporting.test_empty_records_print_no_takes_never_zeros |
| R11, R29 | price-date | NR — not run | CostAccounting.test_per_call_usage_printed_cost_and_wall_time; test_pricing_requires_dated_table_and_agent |
| R13, R24 | ruled-state | NR — not run | Registration.test_routes_free_slots_only_with_committed_rerun; PublishedArtifacts.test_produce_drives_fake_takes_through_all_routes |
| R14 | runner-route | NR — not run | InterfaceRecords.test_runner_reverifies_in_addition_to_publication_checker |
| R15 | prior-round | NR — not run | Reporting.test_every_table_comes_from_stats_and_no_prior_round |
| R16, R31 | stats-default | NR — not run | Reporting.test_empty_records_print_no_takes_never_zeros; StatsDestination.test_no_argument_cli_reads_records_and_legacy_shape_is_refused |
| R18 | freeze-snapshot | NR — not run | FreezeOutputs.test_build_and_frozen_manifest_and_snapshot; test_missing_claim_mutant_is_refused; test_second_freeze_refused_before_any_write |
| R18 | freeze-claims | NR — not run | FreezeOutputs.test_build_and_frozen_manifest_and_snapshot; test_missing_claim_mutant_is_refused; test_second_freeze_refused_before_any_write |
| R18 | freeze-once | NR — not run | FreezeOutputs.test_build_and_frozen_manifest_and_snapshot; test_missing_claim_mutant_is_refused; test_second_freeze_refused_before_any_write |
| R20 | rehearsal-commands | NR — not run | FreezeCoverage.test_rehearsal_keeps_every_required_command_even_when_missing |
| R23 | committed-state | NR — not run | Reporting.test_mechanical_state_read_even_without_a_graded_record; Registration.test_committed_cell_state_refuses_new_slot |
| R23 | closed-cell | NR — not run | Reporting.test_mechanical_state_read_even_without_a_graded_record; Registration.test_committed_cell_state_refuses_new_slot |
| R24 | ruling-word | NR — not run | RulingDoor.test_door_commits_one_closed_record_with_callers_by; test_door_refuses_unknown_word_and_empty_by_with_mutants; PublicationHistory.test_ruled_half_cell_closes_from_the_ruling; test_ruled_take_publishes_under_the_ruled_route |
| R24 | ruling-by | NR — not run | RulingDoor.test_door_commits_one_closed_record_with_callers_by; test_door_refuses_unknown_word_and_empty_by_with_mutants; PublicationHistory.test_ruled_half_cell_closes_from_the_ruling; test_ruled_take_publishes_under_the_ruled_route |
| R24 | ruled-route | NR — not run | RulingDoor.test_door_commits_one_closed_record_with_callers_by; test_door_refuses_unknown_word_and_empty_by_with_mutants; PublicationHistory.test_ruled_half_cell_closes_from_the_ruling; test_ruled_take_publishes_under_the_ruled_route |
| R26 | pause-block | NR — not run | PublicationHistory.test_ruled_pause_counts_its_existing_block_once; test_ruled_pause_requires_unique_block_and_existing_take |
| R27 | window-span | NR — not run | PublicationHistory.test_window_event_must_fit_one_block |
| R28 | row-agent | NR — not run | InterfaceRecords.test_agent_missing_refused_by_ledger_and_records; LedgerDoor.test_registration_commits_the_full_planned_identity_and_audits_it; PublishedArtifacts.test_checker_binds_records_page_agent_and_final_route |
| R28 | design-row | NR — not run | InterfaceRecords.test_agent_missing_refused_by_ledger_and_records; LedgerDoor.test_registration_commits_the_full_planned_identity_and_audits_it; PublishedArtifacts.test_checker_binds_records_page_agent_and_final_route |
| R28 | published-page | NR — not run | InterfaceRecords.test_agent_missing_refused_by_ledger_and_records; LedgerDoor.test_registration_commits_the_full_planned_identity_and_audits_it; PublishedArtifacts.test_checker_binds_records_page_agent_and_final_route |
| R29 | round-spend | NR — not run | CostAccounting.test_round_caps_use_all_months_and_all_models; test_month_turn_refuses_until_both_figures_recorded; test_pricing_requires_dated_table_and_agent |
| R29 | walk-cap | NR — not run | CostAccounting.test_round_caps_use_all_months_and_all_models; test_month_turn_refuses_until_both_figures_recorded; test_pricing_requires_dated_table_and_agent |
| R29 | month-hold | NR — not run | CostAccounting.test_round_caps_use_all_months_and_all_models; test_month_turn_refuses_until_both_figures_recorded; test_pricing_requires_dated_table_and_agent |
| R30 | task-count | NR — not run | Reporting.test_pair_count_comes_from_nine_task_design |
| R2, R7 | freeze-identity | NR — not run | FreezeDesign.test_freeze_preserves_design_and_orders_full_identity_without_vendor_cli |
| R3, R28, R31 | stored-records | NR — not run | PublishedArtifacts.test_checker_binds_records_page_agent_and_final_route |

### Logical commits and red-first evidence

The red tests precede their implementation commits; commits were not amended or rewritten. Every actual commit uses a temporary message file and the exact Codex trailer. Earlier successful green stages remain in history.

| Red test commit | Green code commit | New contract | Observed red closing line |
|---|---|---|---|
| 8a6dce1e | 8990f2fd | w5b-3 freeze outputs | test_pipeline: 3 run, 3 failures, 0 errors, 0 skipped |
| 5cf0af3b | 3835f332 | registration/restart guard | test_pipeline: 9 run, 6 failures, 0 errors, 0 skipped |
| fc635ff5 | b7bee260 | routes/rulings publication | test_pipeline: 15 run, 6 failures, 0 errors, 0 skipped |
| 50f8c4e3 | 70f22b62 | explicit human ruling door | test_pipeline: 17 run, 2 failures, 0 errors, 0 skipped |
| 323d23cd | 9dbb8c1a | interface records and grader provenance | test_pipeline: 24 run, 7 failures, 0 errors, 0 skipped |
| 5eb07a20 | 718c7ad7 | stats-backed publication and PL-2 | test_pipeline: 30 run, 6 failures, 0 errors, 0 skipped |
| 29581288 | 04af06f5 | costs and spending predicates | test_pipeline: 34 run, 4 failures, 0 errors, 0 skipped |
| 29e21996 | 934df2b9 | owned pins and rehearsal command constant | test_pipeline: 36 run, 2 failures, 0 errors, 0 skipped |
| 5ca905e7 | b6c2a2f9 | full committed registration door | test_pipeline: 37 run, 1 failures, 0 errors, 0 skipped |
| 1fcdb042 | 8c5c5b52 | records/page verification | test_pipeline: 39 run, 1 failures, 0 errors, 0 skipped |
| 13d5ca49 | 2b9c7136 | frozen rows and generated-output pins | test_pipeline: 41 run, 2 failures, 0 errors, 0 skipped |
| diagnostic only | 590f4cfc | nine unclaimed non-freeze outputs; empty-tree checks | test_pipeline: 42 run, 0 failures, 0 errors, 0 skipped |

Successful pipeline stage closings were respectively 3, 9, 15, 17, 24, 30, 34, 36, 37, 39, 41 and 42 run, each with `0 failures, 0 errors, 0 skipped`. These are ordinary suite runs, not mutant audit results. Additional intermediate failures in this continuation: `test_pipeline: 36 run, 1 failures, 0 errors, 0 skipped` (repository-relative versus round-relative path expectation, corrected); `test_pipeline: 37 run, 0 failures, 1 errors, 0 skipped` (scratch repository had no initial commit, corrected by committing its synthetic design); `test_pipeline: 42 run, 1 failures, 0 errors, 0 skipped` (the uncommitted rehearsal-claim-helper test, replaced by the blocker diagnostic). The green 42-test run was repeated after staging the diagnostic and checks file and before committing them.

### Final checkpoint gates (all exit 0)

Every command below ran alone in the foreground, after the last code/test/checks changes were staged. The code commit contains those exact staged bytes. No second test process overlapped another. Commands are written in full so they can be replayed; no gate used a bare interpreter on this Mac.

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/tests/test_pipeline.py
```

Runner closing output:

```text
Ran 42 tests in 6.315s
OK
test_pipeline: 42 run, 0 failures, 0 errors, 0 skipped
```

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/copy_manifest.py --check
```

Runner closing output:

```text
ok: 218 files from 27 fragment(s) (w1a-cp1-scaffold, w1b-cp1-routing-batch, w2a-cp3-endstate, w2b-cp3-text-graders, w3a-cp3-graders-scope-template, w3b-cp3-graders-refusal-plangate, w3c-cp3-graders-confound-newtasks, w4a-cp2-image-egress, w4b-cp2-runtake-preflight, w4c-cp2-sidecar-scan, w4d-cp4-variants, w4e-cp5-stats, w4f-cp5-coverage, w4g-cp4-declarations-eligibility, w4h-w1b-next-touch, w4i-cp4-task-scope-read, w4j-cp4-task-template-adherence, w4k-cp4-task-number-fidelity, w4l-cp4-task-precondition-refusal, w4m-cp4-gen-plan-gate, w4n-cp4-gen-confounded-seed2, w4o-cp4-gen-explain-not-act, w4p-cp4-gen-approval-scope, w4q-cp4-gen-conditional-yes, w5a-cp5-probes4, w5b-cp5-pipeline, wave4-merge): 40 identical and 13 edited (round 3 at e2979b31, shared files at 68ec902f), 165 new; 5 fixture builders byte-identical; 8 frozen paths unchanged since 68ec902f63bf
```

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/tests/test_scaffold.py
```

Runner closing output:

```text
Ran 49 tests in 291.606s
OK
```

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/tests/test_batch.py
```

Runner closing output:

```text
Ran 118 tests in 2.544s
OK
```

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/tests/test_stats.py
```

Runner closing output:

```text
Ran 98 tests in 5.973s
OK
```

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/tests/test_pause_adherence.py
```

Runner closing output:

```text
Ran 30 tests in 2.760s
OK
```

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/takes.py --check
```

Runner closing output:

```text
takes: no takes; no registration or outcome measured
```

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/run.py --check
```

Runner closing output:

```text
run: no takes; nothing was graded or written
```

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/result.py --check
```

Runner closing output:

```text
result: no takes; no table measured or written
```

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/completeness.py --check
```

Runner closing output:

```text
completeness: no takes; no cells measured
```

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/check_results.py --check
```

Runner closing output:

```text
check_results: no takes; no frozen pins or publication measured
```

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/costs.py --check
```

Runner closing output:

```text
costs: no takes; no cost measured or written
```

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/freeze.py --check
```

Runner closing output:

```text
freeze: 218 owned paths checked; no takes or freeze performed
```

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore -c 'import sys; sys.path.insert(0, "/Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4"); import test_round4; problems = test_round4.module_problems(); print("test_round4.module_problems:", len(problems), "problems; 0 tests run"); print("\n".join(problems)) if problems else None; sys.exit(bool(problems))'
```

Runner closing output: `test_round4.module_problems: 0 problems; 0 tests run`.


The full test_round4.py, run_checks.py, tests/run_tests.py and any whole-file-audit were NOT run on the Mac. test_round4.module_problems loaded modules only and ran zero tests. The full battery and run_checks remain owed to glitch-f3 on athena after this lane is finished, before review. freeze_rehearsal.py itself, a real freeze --write, real ledger/ruling doors, walks, models and containers were not run. The leak_grep.py docstring has no path-argument mode; its described operation reads real sessions and the design, so no invented scoped invocation was run.

### Remaining implementation after a ruling

- Implement only the authorized non-freeze claim protocol, including its CP2-facing path/commit contract and treatment in freeze pins/tree binding. Re-test the copy checker before and after those writes.
- Finish freeze_rehearsal's runtime migration: its command constant and three-file freeze staging are updated, but lines 177-185 still assume the old dictionary take_order and old takes --add flags, and its synthetic report is currently unclaimed. Its existing scratch commit messages/runtime setup also still need the lane's final migration. It must not be treated as runnable CP6 code yet.
- Complete nonempty CLI integration. In particular costs.py:204 still calls require_frozen without the required `what` argument; the pure accounting functions and empty check pass, but that nonempty path needs a red test and correction.
- Complete registration-after-route-ruling integration: publication understands ruled routes, but guard_registration currently admits an explicit re-run ruling only. Exercise the ruled rerun routes and ruled cell closure through the real registration seam.
- Extend real artifact binding and full producer/checker integration tests, including every committed outcome's registration and model/agent identity, cap handling, and table/version coverage. The synthetic tests are not a claim that CP2's as-yet-unbuilt repo object or nonempty production workflow was exercised.
- Run each named whole-file mutant, repair any surviving mutant or non-assertion-only failure, and fill in a genuine closing-line proof for every clause. Add missing clause-level mutants where the current table only gives shared coverage. Then repeat the final gates on the completed head and hand that head to glitch-f3 for the athena battery/review.

These are unfinished implementation tasks, not requests to edit another lane or changes silently deferred to CP8. R10 remains incomplete.

### Holds, failures and boundaries

The resume start checks accepted ed8d2d58 rather than the base, found the correct branch and a clean worktree, found both required old commits, left the empty hooksPath setting unchanged, and used Python 3.13.2. No model, sub-agent, vendor CLI, network, installation, push, merge, rebase, branch switch, new worktree, git config change or real runtime record write was performed.

mac_slot returned ordinary load holds during startup, early mutant attempts and the freeze-design stage. No test ran on a hold. The two observed later holds were `light hold: load1 21.56 is not below 16.00` and `light hold: load1 18.29 is not below 16.00`; each was followed by a 60-second wait before the next test-gate retry. Early in the resumed session, a loop issued repeated light-ok checks on holds without the required 60-second wait; no test launched, but that retry cadence was a process error and was corrected. No blocking wait longer than 60 seconds was used.

No sandbox denial, classifier block, automatic approval rejection or hook refusal occurred. A malformed apply_patch request was rejected as patch syntax during implementation and was corrected; it was not a safety denial. Expected production/checker refusals were exercised only in synthetic tests. The non-freeze unclaimed-output refusal is the blocking finding above, not something bypassed.

### Deferred to Javier

No action is requested from Javier by this lane. Actual spend, keys, vendor price quotations, the real caps-trimmed record, public pushes and any ruling requiring his word remain deferred. No real price, spend figure or account detail was written. The pending technical ownership ruling goes to glitch-f3 under the supplied delegation.
