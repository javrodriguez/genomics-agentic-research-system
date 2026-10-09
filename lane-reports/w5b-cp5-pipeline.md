status: done
RESUME HERE: glitch-f3 should run full test_round4.py and run_checks.py on athena at the new hand-back head as the closing gate; no further review round.

head: 97f2005629ee04200f60fa2957d0127ec7a7b2a6 (last code/test commit; the final report commit follows it).

The earlier checkpoints below are retained as history. The final review-round-3 fold, mutant proofs, and closing-gate hand-back are appended at the end.

Original checkpoint header (retained):
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


---

status: done
RESUME HERE: glitch-f3 should run the full test_round4.py and run_checks.py on athena at this hand-back head, then send it for review; carry w5b-4's copy-gate timing to the ci.yml lane.

head: 3595662603fc0d65ca5fe45bb9aecd968f82fe5f (last code/test commit; this append-only report's own commit follows it).

Date read before this append: Fri Oct 9 14:24:19 EDT 2026.

This continuation supersedes the historical blocked statuses above. Those entries and their original first two lines remain unchanged, as sections 10 and 11 explicitly require. The supplied w5b-3 and w5b-4 rulings close both earlier questions. No active decision remains pending. The status here covers the lane's implementation and Mac gates; the remote battery and review remain the lead's next steps, not a claim of having run them here.

### Ruling applied and completed behavior

- w5b-4: runtime outputs have no fragment. check_results.runtime_timing_problems inspects reachable commit history for takes.json, outcomes.json, rulings.json, records/, RESULT.md, cost-calls.json and COSTS.md, including files later deleted. They must first occur strictly after the introducing freeze commit. The checker refuses before reading or grading publication when that history is early. Tests use scratch repositories, and the runtime-timing mutant fails by assertion.
- The build and frozen state retain the unchanged copy_manifest.py gate. No runtime fragment was added, and no ownership exception was extended. The w5b-3 scratch tests still prove the build gate, frozen gate, snapshot before the freeze fragment, missing-claim refusal and second-freeze refusal.
- Registration now consumes committed route-ruling fates, including closed cells. Every attempted outcome, including a nonfinal attempt, is bound to its registration and model/agent pin. Regrading also binds evidence.model, evidence.harness and evidence.version to the registered row. The nonempty cost CLI now supplies require_frozen's required purpose argument.
- Rehearsal uses full round 4 rows, the existing committed pre-freeze review, and the required frozen-state command list. Runtime commands run only after that gate, without another copy check. No synthetic review changes the build tree. The clone, row input and report stay under a system temporary directory. The real freeze accepts the report through --rehearsal-record, verifies its draft hash, tree hash and green ending, and retains its text and hash in prereg.json without importing an output file into the build tree. The program itself was not run on the Mac.
- A scratch artifact test reads real closed Evidence files, invokes the local v4 number_fidelity module, writes records, writes RESULT.md and checks the full publication. Synthetic variants data, rows/history and the frozen-design accessor are injected; it does not claim to exercise CP2's future real repo/driver or a real take.

### Lane decisions and downstream contracts

The choices below are this lane's implementation decisions, not new rulings attributed to glitch-f3 or Javier.

- R33: CP2 calls takes.guard_registration(row, attempt, rows, history, live=...) or keeps one process-local takes.RegistrationGuard. Its live set belongs only to the current block. Restart never restores it. takes.commit_registration commits the full planned identity as one append to takes.json's closed rows container; failed commits remain for human reconciliation.
- R24: the human door is takes.py --ruling (takes.commit_ruling). It appends one closed batch.RULING_KEYS record to evals/gap-study-4/rulings.json, one commit per ruling, taking by only from its caller. outcomes.json and rulings.json are lists. takes.read_history merges their one-record appends in commit order; this is the CP2-facing history contract. The door writes no seventh block field.
- R26 / PL-3: publication derives a ruled pause's block from the stopped (slot, attempt) and committed outcome order/window events. It refuses absent or ambiguous membership and reuses an existing block event. This meets W1B4-3's count-once purpose by derivation, under the supplied ruling, rather than a recorded block field.
- PL-2 fixes the destination at evals/gap-study-4/records/. run.py writes interface 11 lists only there. stats.RESULTS_DIR changes in exactly one line; its old-default test changes in exactly one line. stats' authoritative interface uses views=None for final harness errors; the inline graded-record example does not spell that case out. The producer follows stats.py and never publishes a rehearsal or pause as a record.
- A full row includes the eight interface identity fields plus slot and half_cell, and binds any additional planned driver metadata. For actual artifact grading, record_dir is round-relative and holds transcript.jsonl and evidence/; project and any mapped grader_half come from the planned row/task. No earlier round's grader or table is read.
- Rehearsal selects the latest valid committed review (or the explicit --review-commit), so its clone freezes the same owned build bytes. External rehearsal evidence is an explicit --rehearsal-record input; the frozen record retains its content, name and hash, without retaining an absolute host path. This keeps the copy gate at the two states w5b-4 names and avoids changing the rehearsed build merely to store its report.
- Cost calls are cost-calls.json; the rendered page is COSTS.md. Per-vendor call IDs deduplicate identical fragments and refuse conflicts. Missing cost, token or timing measurements remain unmeasured. Prices are passed as a dated table, and all numeric prices in these tests are explicitly fake. The monthly release record has kind, by, month, at and both vendor figures; the predicate requires the current month's release, or the coming month's once the last-day 23:30 UTC hold begins. Elapsed time never supplies a missing release.
- The runtime timing check also rejects outputs in the freeze commit itself and on merged history that lacks the freeze as ancestor. This is the fail-closed reading of outputs being written after the freeze.

### Requirement accounting

Every test below is in tests/test_pipeline.py unless a final gate is named. The red-proven column gives the primary named mutant's exact whole-file closing line; the complete mutant table gives every additional mutant and its own closing line. No R1-R33 implementation item is deferred to CP8. Code-free delivery instructions in R10/R19 are evidenced by commits and gates as well as their ownership/import regressions.

| Requirement | Test name / evidence | Mutant(s) | Red proven (primary runner closing line) | Out-of-scope portion |
|---|---|---|---|---|
| R1 | PipelineOwnership.test_eight_edited_sources_and_local_module_files | `claims-eight` | `test_pipeline: 52 run, 1 failures, 0 errors, 0 skipped` | Implemented in this lane. |
| R2 | InterfaceRecords.test_keys_include_arm_half_wording_level_and_harness; FreezeDesign.test_freeze_preserves_design_and_orders_full_identity_without_vendor_cli | `key-harness`, `freeze-identity` | `test_pipeline: 52 run, 1 failures, 0 errors, 0 skipped` | Implemented in this lane. |
| R3 | PublicationHistory.test_every_route_is_reverified_without_replacement; InterfaceRecords.test_runner_reverifies_in_addition_to_publication_checker | `recorded-route`, `runner-route`, `stop-view` | `test_pipeline: 52 run, 6 failures, 0 errors, 0 skipped` | Implemented in this lane. |
| R4 | InterfaceRecords.test_regrade_uses_v4_file_even_with_same_named_module_cached | `bare-grader` | `test_pipeline: 52 run, 1 failures, 1 errors, 0 skipped` | Implemented in this lane. |
| R5 | Registration.test_live_block_three_restart_requires_reconciliation; test_four_open_mutant; test_routes_free_slots_only_with_committed_rerun | `four-open`, `stale-row`, `final-slot` | `test_pipeline: 52 run, 2 failures, 0 errors, 0 skipped` | Implemented in this lane. |
| R6 | CostAccounting.test_per_call_usage_printed_cost_and_wall_time; test_each_vendor_prices_its_calls_from_the_supplied_fake_table | `per-call`, `token-sums` | `test_pipeline: 52 run, 3 failures, 0 errors, 0 skipped` | Implemented in this lane. |
| R7 | FreezeCoverage.test_every_owned_path_is_pinned_including_fragments_and_prose; FreezeDesign.test_generated_outputs_are_pinned_in_the_frozen_file | `pin-all`, `output-pins` | `test_pipeline: 52 run, 1 failures, 0 errors, 0 skipped` | Implemented in this lane. |
| R8 | Reporting.test_every_table_comes_from_stats_and_no_prior_round | `result-tables` | `test_pipeline: 52 run, 6 failures, 0 errors, 0 skipped` | Implemented in this lane. |
| R9 | PublishedArtifacts.test_produce_drives_fake_takes_through_all_routes; Reporting.test_empty_records_print_no_takes_never_zeros | `records-shape`, `empty-result` | `test_pipeline: 52 run, 1 failures, 1 errors, 0 skipped` | Implemented in this lane. |
| R10 | PipelineOwnership.test_eight_edited_sources_and_local_module_files; all final gates below; CP8 changes no code | `claims-eight` | `test_pipeline: 52 run, 1 failures, 0 errors, 0 skipped` | Implemented in this lane. |
| R11 | CostAccounting.test_per_call_usage_printed_cost_and_wall_time; test_nonempty_cost_cli_writes_then_checks_the_frozen_prices | `printed-cost`, `token-sums`, `wall-time`, `per-call` | `test_pipeline: 52 run, 1 failures, 0 errors, 0 skipped` | Implemented in this lane. |
| R12 | InterfaceRecords.test_every_stop_has_three_views_and_aborted_counts_against_holding; Reporting.test_excluded_dict_no_takes_and_only_stops_all_render | `stop-view`, `result-tables` | `test_pipeline: 52 run, 1 failures, 3 errors, 0 skipped` | Implemented in this lane. |
| R13 | Registration.test_routes_free_slots_only_with_committed_rerun; PublishedArtifacts.test_produce_drives_fake_takes_through_all_routes; PublicationHistory.test_ruled_half_cell_closes_from_the_ruling | `final-slot`, `ruled-state` | `test_pipeline: 52 run, 5 failures, 0 errors, 0 skipped` | Implemented in this lane. |
| R14 | PublicationHistory.test_every_route_is_reverified_without_replacement; InterfaceRecords.test_runner_reverifies_in_addition_to_publication_checker | `recorded-route`, `runner-route` | `test_pipeline: 52 run, 6 failures, 0 errors, 0 skipped` | Implemented in this lane. |
| R15 | Reporting.test_every_table_comes_from_stats_and_no_prior_round | `prior-round` | `test_pipeline: 52 run, 1 failures, 0 errors, 0 skipped` | Implemented in this lane. |
| R16 | Reporting.test_empty_records_print_no_takes_never_zeros; StatsDestination.test_no_argument_cli_reads_records_and_legacy_shape_is_refused | `empty-result`, `stats-default` | `test_pipeline: 52 run, 1 failures, 0 errors, 0 skipped` | Implemented in this lane. |
| R17 | InterfaceRecords.test_regrade_uses_v4_file_even_with_same_named_module_cached; PublishedArtifacts.test_committed_artifacts_regrade_and_publish_through_cli | `bare-grader`, `evidence-identity` | `test_pipeline: 52 run, 1 failures, 1 errors, 0 skipped` | Implemented in this lane. |
| R18 | FreezeOutputs.test_build_and_frozen_manifest_and_snapshot; test_missing_claim_mutant_is_refused; test_second_freeze_refused_before_any_write | `freeze-claims`, `freeze-snapshot`, `freeze-once` | `test_pipeline: 52 run, 1 failures, 0 errors, 0 skipped` | Implemented in this lane. |
| R19 | PipelineOwnership.test_eight_edited_sources_and_local_module_files; FreezeCoverage.test_rehearsal_keeps_every_required_command_even_when_missing; explicit path staging before record gates | `foreign-module` | `test_pipeline: 52 run, 1 failures, 0 errors, 0 skipped` | Implemented in this lane. |
| R20 | FreezeCoverage.test_rehearsal_keeps_every_required_command_even_when_missing; test_rehearsal_uses_full_rows_and_copy_gate_only_on_frozen_state; test_external_rehearsal_record_binds_draft_tree_and_green_result | `rehearsal-commands`, `rehearsal-runtime`, `rehearsal-evidence` | `test_pipeline: 52 run, 2 failures, 0 errors, 0 skipped` | Actual rehearsal run is CP6, plan 880-895. |
| R21 | Registration.test_live_block_three_restart_requires_reconciliation; test_four_open_mutant | `stale-row`, `four-open` | `test_pipeline: 52 run, 3 failures, 0 errors, 0 skipped` | Implemented in this lane. |
| R22 | Registration.test_routes_free_slots_only_with_committed_rerun; test_route_rulings_release_or_close_registration | `final-slot`, `registration-ruling` | `test_pipeline: 52 run, 5 failures, 0 errors, 0 skipped` | Implemented in this lane. |
| R23 | Reporting.test_mechanical_state_read_even_without_a_graded_record; Registration.test_committed_cell_state_refuses_new_slot | `committed-state`, `closed-cell` | `test_pipeline: 52 run, 1 failures, 0 errors, 0 skipped` | Implemented in this lane. |
| R24 | RulingDoor.test_door_commits_one_closed_record_with_callers_by; test_door_refuses_unknown_word_and_empty_by_with_mutants; PublicationHistory.test_ruled_half_cell_closes_from_the_ruling; test_ruled_take_publishes_under_the_ruled_route; Registration.test_route_rulings_release_or_close_registration | `ruling-word`, `ruling-by`, `ruled-state`, `ruled-route`, `registration-ruling` | `test_pipeline: 52 run, 1 failures, 0 errors, 0 skipped` | Implemented in this lane. |
| R25 | Registration.test_lost_drive_and_lost_pause_never_launch_on_restart | `stale-row` | `test_pipeline: 52 run, 3 failures, 0 errors, 0 skipped` | Implemented in this lane. |
| R26 | PublicationHistory.test_ruled_pause_counts_its_existing_block_once; test_ruled_pause_requires_unique_block_and_existing_take | `pause-block` | `test_pipeline: 52 run, 2 failures, 0 errors, 0 skipped` | Implemented in this lane. |
| R27 | PublicationHistory.test_window_event_must_fit_one_block | `window-span` | `test_pipeline: 52 run, 1 failures, 0 errors, 0 skipped` | Implemented in this lane. |
| R28 | InterfaceRecords.test_agent_missing_refused_by_ledger_and_records; Registration.test_row_agent_required_never_defaulted; LedgerDoor.test_registration_commits_the_full_planned_identity_and_audits_it; PublishedArtifacts.test_checker_binds_complete_identity_to_the_frozen_plan; test_every_attempt_binds_its_registration_model_and_agent; test_checker_binds_records_page_agent_and_final_route | `row-agent`, `design-row`, `attempt-identity`, `evidence-identity`, `published-page` | `test_pipeline: 52 run, 1 failures, 1 errors, 0 skipped` | Pre-registration writer: section 7, CP5-req 42. |
| R29 | CostAccounting.test_each_vendor_prices_its_calls_from_the_supplied_fake_table; test_pricing_requires_dated_table_and_agent; test_round_caps_use_all_months_and_all_models; test_month_turn_refuses_until_both_figures_recorded | `vendor-prices`, `price-date`, `vendor-caps`, `total-cap`, `round-spend`, `walk-cap`, `month-hold` | `test_pipeline: 52 run, 2 failures, 0 errors, 0 skipped` | Driver invokes the predicates: section 7, CP5-req 57; no driver edited. |
| R30 | Reporting.test_pair_count_comes_from_nine_task_design | `task-count` | `test_pipeline: 52 run, 1 failures, 0 errors, 0 skipped` | Implemented in this lane. |
| R31 | StatsDestination.test_no_argument_cli_reads_records_and_legacy_shape_is_refused; InterfaceRecords.test_record_lists_written_only_in_records_and_legacy_shape_refused; PublishedArtifacts.test_checker_binds_records_page_agent_and_final_route; RuntimeTiming.test_pre_freeze_outputs_refused_even_when_removed_before_freeze | `stats-default`, `records-shape`, `stored-records`, `runtime-timing` | `test_pipeline: 52 run, 1 failures, 0 errors, 0 skipped` | Implemented in this lane. |
| R32 | Reporting.test_excluded_dict_no_takes_and_only_stops_all_render | `result-tables` | `test_pipeline: 52 run, 6 failures, 0 errors, 0 skipped` | Implemented in this lane. |
| R33 | Registration.test_live_block_three_restart_requires_reconciliation; test_lost_drive_and_lost_pause_never_launch_on_restart; LedgerDoor.test_registration_commits_the_full_planned_identity_and_audits_it | `stale-row`, `registration-ruling` | `test_pipeline: 52 run, 3 failures, 0 errors, 0 skipped` | Implemented in this lane. |

### Whole-file mutant proof

All 52 mutants were armed only in setUpModule, undone in tearDownModule, and run against the whole 52-test module. Each exited 1 with at least one assertion failure. Additional downstream errors for some missing guards are shown honestly in the closing lines; an error alone was never accepted as proof. No mutant survived and no mutant run was skipped.

Each row used this exact command prefix followed by the row's mutant name:

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/tests/test_pipeline.py --mutant <name>
```

| Clause | Mutant name | Whole-file result and exact closing line | Binding test(s) |
|---|---|---|---|
| R1, R10 | claims-eight | RED (exit 1): `test_pipeline: 52 run, 1 failures, 0 errors, 0 skipped` | PipelineOwnership.test_eight_edited_sources_and_local_module_files; PipelineOwnership.test_eight_edited_sources_and_local_module_files; all final gates below; CP8 changes no code |
| R19 | foreign-module | RED (exit 1): `test_pipeline: 52 run, 1 failures, 0 errors, 0 skipped` | PipelineOwnership.test_eight_edited_sources_and_local_module_files; FreezeCoverage.test_rehearsal_keeps_every_required_command_even_when_missing; explicit path staging before record gates |
| R11 | printed-cost | RED (exit 1): `test_pipeline: 52 run, 1 failures, 0 errors, 0 skipped` | CostAccounting.test_per_call_usage_printed_cost_and_wall_time; test_nonempty_cost_cli_writes_then_checks_the_frozen_prices |
| R6, R11 | token-sums | RED (exit 1): `test_pipeline: 52 run, 1 failures, 0 errors, 0 skipped` | CostAccounting.test_per_call_usage_printed_cost_and_wall_time; test_each_vendor_prices_its_calls_from_the_supplied_fake_table; CostAccounting.test_per_call_usage_printed_cost_and_wall_time; test_nonempty_cost_cli_writes_then_checks_the_frozen_prices |
| R11 | wall-time | RED (exit 1): `test_pipeline: 52 run, 1 failures, 0 errors, 0 skipped` | CostAccounting.test_per_call_usage_printed_cost_and_wall_time; test_nonempty_cost_cli_writes_then_checks_the_frozen_prices |
| R29 | vendor-prices | RED (exit 1): `test_pipeline: 52 run, 2 failures, 0 errors, 0 skipped` | CostAccounting.test_each_vendor_prices_its_calls_from_the_supplied_fake_table; test_pricing_requires_dated_table_and_agent; test_round_caps_use_all_months_and_all_models; test_month_turn_refuses_until_both_figures_recorded |
| R29 | vendor-caps | RED (exit 1): `test_pipeline: 52 run, 1 failures, 0 errors, 0 skipped` | CostAccounting.test_each_vendor_prices_its_calls_from_the_supplied_fake_table; test_pricing_requires_dated_table_and_agent; test_round_caps_use_all_months_and_all_models; test_month_turn_refuses_until_both_figures_recorded |
| R29 | total-cap | RED (exit 1): `test_pipeline: 52 run, 1 failures, 0 errors, 0 skipped` | CostAccounting.test_each_vendor_prices_its_calls_from_the_supplied_fake_table; test_pricing_requires_dated_table_and_agent; test_round_caps_use_all_months_and_all_models; test_month_turn_refuses_until_both_figures_recorded |
| R31; section 11 | runtime-timing | RED (exit 1): `test_pipeline: 52 run, 7 failures, 0 errors, 0 skipped` | StatsDestination.test_no_argument_cli_reads_records_and_legacy_shape_is_refused; InterfaceRecords.test_record_lists_written_only_in_records_and_legacy_shape_refused; PublishedArtifacts.test_checker_binds_records_page_agent_and_final_route; RuntimeTiming.test_pre_freeze_outputs_refused_even_when_removed_before_freeze |
| R28 | attempt-identity | RED (exit 1): `test_pipeline: 52 run, 3 failures, 2 errors, 0 skipped` | InterfaceRecords.test_agent_missing_refused_by_ledger_and_records; Registration.test_row_agent_required_never_defaulted; LedgerDoor.test_registration_commits_the_full_planned_identity_and_audits_it; PublishedArtifacts.test_checker_binds_complete_identity_to_the_frozen_plan; test_every_attempt_binds_its_registration_model_and_agent; test_checker_binds_records_page_agent_and_final_route |
| R17, R28 | evidence-identity | RED (exit 1): `test_pipeline: 52 run, 1 failures, 0 errors, 0 skipped` | InterfaceRecords.test_regrade_uses_v4_file_even_with_same_named_module_cached; PublishedArtifacts.test_committed_artifacts_regrade_and_publish_through_cli; InterfaceRecords.test_agent_missing_refused_by_ledger_and_records; Registration.test_row_agent_required_never_defaulted; LedgerDoor.test_registration_commits_the_full_planned_identity_and_audits_it; PublishedArtifacts.test_checker_binds_complete_identity_to_the_frozen_plan; test_every_attempt_binds_its_registration_model_and_agent; test_checker_binds_records_page_agent_and_final_route |
| R20 | rehearsal-evidence | RED (exit 1): `test_pipeline: 52 run, 1 failures, 0 errors, 0 skipped` | FreezeCoverage.test_rehearsal_keeps_every_required_command_even_when_missing; test_rehearsal_uses_full_rows_and_copy_gate_only_on_frozen_state; test_external_rehearsal_record_binds_draft_tree_and_green_result |
| R22, R24, R33 | registration-ruling | RED (exit 1): `test_pipeline: 52 run, 6 failures, 0 errors, 0 skipped` | Registration.test_routes_free_slots_only_with_committed_rerun; test_route_rulings_release_or_close_registration; RulingDoor.test_door_commits_one_closed_record_with_callers_by; test_door_refuses_unknown_word_and_empty_by_with_mutants; PublicationHistory.test_ruled_half_cell_closes_from_the_ruling; test_ruled_take_publishes_under_the_ruled_route; Registration.test_route_rulings_release_or_close_registration; Registration.test_live_block_three_restart_requires_reconciliation; test_lost_drive_and_lost_pause_never_launch_on_restart; LedgerDoor.test_registration_commits_the_full_planned_identity_and_audits_it |
| R2 | freeze-identity | RED (exit 1): `test_pipeline: 52 run, 1 failures, 0 errors, 0 skipped` | InterfaceRecords.test_keys_include_arm_half_wording_level_and_harness; FreezeDesign.test_freeze_preserves_design_and_orders_full_identity_without_vendor_cli |
| R7 | output-pins | RED (exit 1): `test_pipeline: 52 run, 1 failures, 0 errors, 0 skipped` | FreezeCoverage.test_every_owned_path_is_pinned_including_fragments_and_prose; FreezeDesign.test_generated_outputs_are_pinned_in_the_frozen_file |
| R7 | pin-all | RED (exit 1): `test_pipeline: 52 run, 1 failures, 0 errors, 0 skipped` | FreezeCoverage.test_every_owned_path_is_pinned_including_fragments_and_prose; FreezeDesign.test_generated_outputs_are_pinned_in_the_frozen_file |
| R20 | rehearsal-commands | RED (exit 1): `test_pipeline: 52 run, 2 failures, 0 errors, 0 skipped` | FreezeCoverage.test_rehearsal_keeps_every_required_command_even_when_missing; test_rehearsal_uses_full_rows_and_copy_gate_only_on_frozen_state; test_external_rehearsal_record_binds_draft_tree_and_green_result |
| R20 | rehearsal-runtime | RED (exit 1): `test_pipeline: 52 run, 1 failures, 0 errors, 0 skipped` | FreezeCoverage.test_rehearsal_keeps_every_required_command_even_when_missing; test_rehearsal_uses_full_rows_and_copy_gate_only_on_frozen_state; test_external_rehearsal_record_binds_draft_tree_and_green_result |
| R18 | freeze-claims | RED (exit 1): `test_pipeline: 52 run, 1 failures, 0 errors, 0 skipped` | FreezeOutputs.test_build_and_frozen_manifest_and_snapshot; test_missing_claim_mutant_is_refused; test_second_freeze_refused_before_any_write |
| R18 | freeze-once | RED (exit 1): `test_pipeline: 52 run, 1 failures, 0 errors, 0 skipped` | FreezeOutputs.test_build_and_frozen_manifest_and_snapshot; test_missing_claim_mutant_is_refused; test_second_freeze_refused_before_any_write |
| R18 | freeze-snapshot | RED (exit 1): `test_pipeline: 52 run, 1 failures, 0 errors, 0 skipped` | FreezeOutputs.test_build_and_frozen_manifest_and_snapshot; test_missing_claim_mutant_is_refused; test_second_freeze_refused_before_any_write |
| R31 | stored-records | RED (exit 1): `test_pipeline: 52 run, 1 failures, 0 errors, 0 skipped` | StatsDestination.test_no_argument_cli_reads_records_and_legacy_shape_is_refused; InterfaceRecords.test_record_lists_written_only_in_records_and_legacy_shape_refused; PublishedArtifacts.test_checker_binds_records_page_agent_and_final_route; RuntimeTiming.test_pre_freeze_outputs_refused_even_when_removed_before_freeze |
| R28 | published-page | RED (exit 1): `test_pipeline: 52 run, 1 failures, 0 errors, 0 skipped` | InterfaceRecords.test_agent_missing_refused_by_ledger_and_records; Registration.test_row_agent_required_never_defaulted; LedgerDoor.test_registration_commits_the_full_planned_identity_and_audits_it; PublishedArtifacts.test_checker_binds_complete_identity_to_the_frozen_plan; test_every_attempt_binds_its_registration_model_and_agent; test_checker_binds_records_page_agent_and_final_route |
| R28 | design-row | RED (exit 1): `test_pipeline: 52 run, 2 failures, 0 errors, 0 skipped` | InterfaceRecords.test_agent_missing_refused_by_ledger_and_records; Registration.test_row_agent_required_never_defaulted; LedgerDoor.test_registration_commits_the_full_planned_identity_and_audits_it; PublishedArtifacts.test_checker_binds_complete_identity_to_the_frozen_plan; test_every_attempt_binds_its_registration_model_and_agent; test_checker_binds_records_page_agent_and_final_route |
| R5, R21, R25, R33 | stale-row | RED (exit 1): `test_pipeline: 52 run, 3 failures, 0 errors, 0 skipped` | Registration.test_live_block_three_restart_requires_reconciliation; test_four_open_mutant; test_routes_free_slots_only_with_committed_rerun; Registration.test_live_block_three_restart_requires_reconciliation; test_four_open_mutant; Registration.test_lost_drive_and_lost_pause_never_launch_on_restart; Registration.test_live_block_three_restart_requires_reconciliation; test_lost_drive_and_lost_pause_never_launch_on_restart; LedgerDoor.test_registration_commits_the_full_planned_identity_and_audits_it |
| R5, R21 | four-open | RED (exit 1): `test_pipeline: 52 run, 2 failures, 0 errors, 0 skipped` | Registration.test_live_block_three_restart_requires_reconciliation; test_four_open_mutant; test_routes_free_slots_only_with_committed_rerun; Registration.test_live_block_three_restart_requires_reconciliation; test_four_open_mutant |
| R28 | row-agent | RED (exit 1): `test_pipeline: 52 run, 1 failures, 1 errors, 0 skipped` | InterfaceRecords.test_agent_missing_refused_by_ledger_and_records; Registration.test_row_agent_required_never_defaulted; LedgerDoor.test_registration_commits_the_full_planned_identity_and_audits_it; PublishedArtifacts.test_checker_binds_complete_identity_to_the_frozen_plan; test_every_attempt_binds_its_registration_model_and_agent; test_checker_binds_records_page_agent_and_final_route |
| R5, R13, R22 | final-slot | RED (exit 1): `test_pipeline: 52 run, 5 failures, 0 errors, 0 skipped` | Registration.test_live_block_three_restart_requires_reconciliation; test_four_open_mutant; test_routes_free_slots_only_with_committed_rerun; Registration.test_routes_free_slots_only_with_committed_rerun; PublishedArtifacts.test_produce_drives_fake_takes_through_all_routes; PublicationHistory.test_ruled_half_cell_closes_from_the_ruling; Registration.test_routes_free_slots_only_with_committed_rerun; test_route_rulings_release_or_close_registration |
| R23 | closed-cell | RED (exit 1): `test_pipeline: 52 run, 2 failures, 0 errors, 0 skipped` | Reporting.test_mechanical_state_read_even_without_a_graded_record; Registration.test_committed_cell_state_refuses_new_slot |
| R3, R14 | recorded-route | RED (exit 1): `test_pipeline: 52 run, 6 failures, 0 errors, 0 skipped` | PublicationHistory.test_every_route_is_reverified_without_replacement; InterfaceRecords.test_runner_reverifies_in_addition_to_publication_checker |
| R26 | pause-block | RED (exit 1): `test_pipeline: 52 run, 2 failures, 0 errors, 0 skipped` | PublicationHistory.test_ruled_pause_counts_its_existing_block_once; test_ruled_pause_requires_unique_block_and_existing_take |
| R27 | window-span | RED (exit 1): `test_pipeline: 52 run, 1 failures, 0 errors, 0 skipped` | PublicationHistory.test_window_event_must_fit_one_block |
| R13, R24 | ruled-state | RED (exit 1): `test_pipeline: 52 run, 1 failures, 1 errors, 0 skipped` | Registration.test_routes_free_slots_only_with_committed_rerun; PublishedArtifacts.test_produce_drives_fake_takes_through_all_routes; PublicationHistory.test_ruled_half_cell_closes_from_the_ruling; RulingDoor.test_door_commits_one_closed_record_with_callers_by; test_door_refuses_unknown_word_and_empty_by_with_mutants; PublicationHistory.test_ruled_half_cell_closes_from_the_ruling; test_ruled_take_publishes_under_the_ruled_route; Registration.test_route_rulings_release_or_close_registration |
| R24 | ruled-route | RED (exit 1): `test_pipeline: 52 run, 7 failures, 1 errors, 0 skipped` | RulingDoor.test_door_commits_one_closed_record_with_callers_by; test_door_refuses_unknown_word_and_empty_by_with_mutants; PublicationHistory.test_ruled_half_cell_closes_from_the_ruling; test_ruled_take_publishes_under_the_ruled_route; Registration.test_route_rulings_release_or_close_registration |
| R24 | ruling-word | RED (exit 1): `test_pipeline: 52 run, 1 failures, 0 errors, 0 skipped` | RulingDoor.test_door_commits_one_closed_record_with_callers_by; test_door_refuses_unknown_word_and_empty_by_with_mutants; PublicationHistory.test_ruled_half_cell_closes_from_the_ruling; test_ruled_take_publishes_under_the_ruled_route; Registration.test_route_rulings_release_or_close_registration |
| R24 | ruling-by | RED (exit 1): `test_pipeline: 52 run, 1 failures, 0 errors, 0 skipped` | RulingDoor.test_door_commits_one_closed_record_with_callers_by; test_door_refuses_unknown_word_and_empty_by_with_mutants; PublicationHistory.test_ruled_half_cell_closes_from_the_ruling; test_ruled_take_publishes_under_the_ruled_route; Registration.test_route_rulings_release_or_close_registration |
| R4, R17 | bare-grader | RED (exit 1): `test_pipeline: 52 run, 1 failures, 1 errors, 0 skipped` | InterfaceRecords.test_regrade_uses_v4_file_even_with_same_named_module_cached; InterfaceRecords.test_regrade_uses_v4_file_even_with_same_named_module_cached; PublishedArtifacts.test_committed_artifacts_regrade_and_publish_through_cli |
| R3, R12 | stop-view | RED (exit 1): `test_pipeline: 52 run, 1 failures, 3 errors, 0 skipped` | PublicationHistory.test_every_route_is_reverified_without_replacement; InterfaceRecords.test_runner_reverifies_in_addition_to_publication_checker; InterfaceRecords.test_every_stop_has_three_views_and_aborted_counts_against_holding; Reporting.test_excluded_dict_no_takes_and_only_stops_all_render |
| R3, R14 | runner-route | RED (exit 1): `test_pipeline: 52 run, 1 failures, 0 errors, 0 skipped` | PublicationHistory.test_every_route_is_reverified_without_replacement; InterfaceRecords.test_runner_reverifies_in_addition_to_publication_checker |
| R9, R31 | records-shape | RED (exit 1): `test_pipeline: 52 run, 1 failures, 1 errors, 0 skipped` | PublishedArtifacts.test_produce_drives_fake_takes_through_all_routes; Reporting.test_empty_records_print_no_takes_never_zeros; StatsDestination.test_no_argument_cli_reads_records_and_legacy_shape_is_refused; InterfaceRecords.test_record_lists_written_only_in_records_and_legacy_shape_refused; PublishedArtifacts.test_checker_binds_records_page_agent_and_final_route; RuntimeTiming.test_pre_freeze_outputs_refused_even_when_removed_before_freeze |
| R2 | key-harness | RED (exit 1): `test_pipeline: 52 run, 1 failures, 0 errors, 0 skipped` | InterfaceRecords.test_keys_include_arm_half_wording_level_and_harness; FreezeDesign.test_freeze_preserves_design_and_orders_full_identity_without_vendor_cli |
| R16, R31 | stats-default | RED (exit 1): `test_pipeline: 52 run, 1 failures, 0 errors, 0 skipped` | Reporting.test_empty_records_print_no_takes_never_zeros; StatsDestination.test_no_argument_cli_reads_records_and_legacy_shape_is_refused; StatsDestination.test_no_argument_cli_reads_records_and_legacy_shape_is_refused; InterfaceRecords.test_record_lists_written_only_in_records_and_legacy_shape_refused; PublishedArtifacts.test_checker_binds_records_page_agent_and_final_route; RuntimeTiming.test_pre_freeze_outputs_refused_even_when_removed_before_freeze |
| R30 | task-count | RED (exit 1): `test_pipeline: 52 run, 1 failures, 0 errors, 0 skipped` | Reporting.test_pair_count_comes_from_nine_task_design |
| R23 | committed-state | RED (exit 1): `test_pipeline: 52 run, 1 failures, 0 errors, 0 skipped` | Reporting.test_mechanical_state_read_even_without_a_graded_record; Registration.test_committed_cell_state_refuses_new_slot |
| R8, R12, R32 | result-tables | RED (exit 1): `test_pipeline: 52 run, 6 failures, 0 errors, 0 skipped` | Reporting.test_every_table_comes_from_stats_and_no_prior_round; InterfaceRecords.test_every_stop_has_three_views_and_aborted_counts_against_holding; Reporting.test_excluded_dict_no_takes_and_only_stops_all_render; Reporting.test_excluded_dict_no_takes_and_only_stops_all_render |
| R9, R16 | empty-result | RED (exit 1): `test_pipeline: 52 run, 1 failures, 0 errors, 0 skipped` | PublishedArtifacts.test_produce_drives_fake_takes_through_all_routes; Reporting.test_empty_records_print_no_takes_never_zeros; Reporting.test_empty_records_print_no_takes_never_zeros; StatsDestination.test_no_argument_cli_reads_records_and_legacy_shape_is_refused |
| R6, R11 | per-call | RED (exit 1): `test_pipeline: 52 run, 3 failures, 0 errors, 0 skipped` | CostAccounting.test_per_call_usage_printed_cost_and_wall_time; test_each_vendor_prices_its_calls_from_the_supplied_fake_table; CostAccounting.test_per_call_usage_printed_cost_and_wall_time; test_nonempty_cost_cli_writes_then_checks_the_frozen_prices |
| R29 | price-date | RED (exit 1): `test_pipeline: 52 run, 1 failures, 0 errors, 0 skipped` | CostAccounting.test_each_vendor_prices_its_calls_from_the_supplied_fake_table; test_pricing_requires_dated_table_and_agent; test_round_caps_use_all_months_and_all_models; test_month_turn_refuses_until_both_figures_recorded |
| R29 | round-spend | RED (exit 1): `test_pipeline: 52 run, 1 failures, 0 errors, 0 skipped` | CostAccounting.test_each_vendor_prices_its_calls_from_the_supplied_fake_table; test_pricing_requires_dated_table_and_agent; test_round_caps_use_all_months_and_all_models; test_month_turn_refuses_until_both_figures_recorded |
| R29 | walk-cap | RED (exit 1): `test_pipeline: 52 run, 1 failures, 0 errors, 0 skipped` | CostAccounting.test_each_vendor_prices_its_calls_from_the_supplied_fake_table; test_pricing_requires_dated_table_and_agent; test_round_caps_use_all_months_and_all_models; test_month_turn_refuses_until_both_figures_recorded |
| R29 | month-hold | RED (exit 1): `test_pipeline: 52 run, 1 failures, 0 errors, 0 skipped` | CostAccounting.test_each_vendor_prices_its_calls_from_the_supplied_fake_table; test_pricing_requires_dated_table_and_agent; test_round_caps_use_all_months_and_all_models; test_month_turn_refuses_until_both_figures_recorded |
| R15 | prior-round | RED (exit 1): `test_pipeline: 52 run, 1 failures, 0 errors, 0 skipped` | Reporting.test_every_table_comes_from_stats_and_no_prior_round |

### Red-first continuation commits

The preceding continuation's red/green commits remain in the earlier report. This resume added these logical pairs; neither commits nor report history were amended or rewritten.

| Red test commit | Green code commit | Contract | Red runner closing line |
|---|---|---|---|
| 7e103866 | b9eb1436 | Runtime output timing under w5b-4 | test_pipeline: 43 run, 2 failures, 0 errors, 0 skipped |
| fae8419a | 4147173b | Registration after route rulings | test_pipeline: 44 run, 1 failures, 0 errors, 0 skipped |
| 1679a023 | 9a2e2def | Nonempty cost CLI | test_pipeline: 45 run, 1 failures, 0 errors, 0 skipped |
| 2064d8c1 | ffb34bb4 | Full-row rehearsal runtime commands | test_pipeline: 46 run, 1 failures, 0 errors, 0 skipped |
| 2a56a245 | 072e901d | Every attempt's identity and the planned publication | test_pipeline: 48 run, 2 failures, 0 errors, 0 skipped |
| 52b94bed | 6db3c31b | Committed artifact grading and evidence identity | test_pipeline: 49 run, 1 failures, 0 errors, 0 skipped |
| a090ddce | e7b63534 | External rehearsal evidence without a build-tree write | test_pipeline: 50 run, 1 failures, 0 errors, 0 skipped |

Green coverage commits aa9599f4 and 35956626 added ownership and cost-clause mutants, an explicit record-list assertion, and the mutant that supplies a default agent. They changed tests only. The final ordinary run is `test_pipeline: 52 run, 0 failures, 0 errors, 0 skipped`. Each pre-freeze continuation commit passed the copy gate after explicit-path staging; red test commits intentionally retain their specified failing tests until the immediately following implementation.

### Final gates on the code head

Each command ran after explicit-path git add, alone in the foreground, with the Mac load gate in the same command, Python 3.13.2, bytecode disabled, and single-threaded BLAS variables. All 15 commands exited 0. No final gate overlapped another. The stats CLI check is additional direct empty-default evidence; an empty-study exit 0 is not a measurement on takes.

`tests/test_pipeline.py`

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/tests/test_pipeline.py
```

Runner closing output:

```text
Ran 52 tests in 12.649s

OK
test_pipeline: 52 run, 0 failures, 0 errors, 0 skipped
```

`copy_manifest.py --check`

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/copy_manifest.py --check
```

Runner closing output:

```text
ok: 218 files from 27 fragment(s) (w1a-cp1-scaffold, w1b-cp1-routing-batch, w2a-cp3-endstate, w2b-cp3-text-graders, w3a-cp3-graders-scope-template, w3b-cp3-graders-refusal-plangate, w3c-cp3-graders-confound-newtasks, w4a-cp2-image-egress, w4b-cp2-runtake-preflight, w4c-cp2-sidecar-scan, w4d-cp4-variants, w4e-cp5-stats, w4f-cp5-coverage, w4g-cp4-declarations-eligibility, w4h-w1b-next-touch, w4i-cp4-task-scope-read, w4j-cp4-task-template-adherence, w4k-cp4-task-number-fidelity, w4l-cp4-task-precondition-refusal, w4m-cp4-gen-plan-gate, w4n-cp4-gen-confounded-seed2, w4o-cp4-gen-explain-not-act, w4p-cp4-gen-approval-scope, w4q-cp4-gen-conditional-yes, w5a-cp5-probes4, w5b-cp5-pipeline, wave4-merge): 40 identical and 13 edited (round 3 at e2979b31, shared files at 68ec902f), 165 new; 5 fixture builders byte-identical; 8 frozen paths unchanged since 68ec902f63bf
```

`tests/test_scaffold.py`

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/tests/test_scaffold.py
```

Runner closing output:

```text
Ran 49 tests in 299.242s

OK
```

`tests/test_batch.py`

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/tests/test_batch.py
```

Runner closing output:

```text
Ran 118 tests in 4.451s

OK
```

`tests/test_stats.py`

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/tests/test_stats.py
```

Runner closing output:

```text
Ran 98 tests in 9.860s

OK
```

`tests/test_pause_adherence.py`

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/tests/test_pause_adherence.py
```

Runner closing output:

```text
Ran 30 tests in 3.883s

OK
```

`takes.py --check`

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/takes.py --check
```

Runner closing output:

```text
takes: no takes; no registration or outcome measured
```

`run.py --check`

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/run.py --check
```

Runner closing output:

```text
run: no takes; nothing was graded or written
```

`result.py --check`

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/result.py --check
```

Runner closing output:

```text
result: no takes; no table measured or written
```

`completeness.py --check`

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/completeness.py --check
```

Runner closing output:

```text
completeness: no takes; no cells measured
```

`check_results.py --check`

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/check_results.py --check
```

Runner closing output:

```text
check_results: no takes; no frozen pins or publication measured
```

`costs.py --check`

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/costs.py --check
```

Runner closing output:

```text
costs: no takes; no cost measured or written
```

`freeze.py --check`

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/freeze.py --check
```

Runner closing output:

```text
freeze: 218 owned paths checked; no takes or freeze performed
```

`stats.py --check`

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/stats.py --check
```

Runner closing output:

```text
stats --check: no takes (0 results files); nothing was compared
```

`test_round4.module_problems()`

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore -c 'import sys; sys.path.insert(0, "/Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4"); import test_round4; problems = test_round4.module_problems(); print("test_round4.module_problems:", len(problems), "problems; 0 tests run"); print("\n".join(problems)) if problems else None; sys.exit(bool(problems))'
```

Runner closing output:

```text
test_round4.module_problems: 0 problems; 0 tests run
```

### Changed files and named exceptions

At code head 3595662603fc0d65ca5fe45bb9aecd968f82fe5f, `git -C /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline diff --stat be1286f7..HEAD` printed:

```text
evals/gap-study-4/COPIED.d/w1a-cp1-scaffold.json |   40 -
 evals/gap-study-4/COPIED.d/w5b-cp5-pipeline.json |   68 ++
 evals/gap-study-4/check_results.py               | 1088 +++++--------------
 evals/gap-study-4/checks.d/w5b-cp5-pipeline.txt  |   16 +
 evals/gap-study-4/completeness.py                |  143 ++-
 evals/gap-study-4/costs.py                       |  643 ++++--------
 evals/gap-study-4/freeze.py                      |  593 ++++-------
 evals/gap-study-4/freeze_rehearsal.py            |  324 +++---
 evals/gap-study-4/result.py                      |  399 +------
 evals/gap-study-4/run.py                         |  527 ++++------
 evals/gap-study-4/stats.py                       |    2 +-
 evals/gap-study-4/takes.py                       |  674 ++++++------
 evals/gap-study-4/tests/test_pipeline.py         | 1206 ++++++++++++++++++++++
 evals/gap-study-4/tests/test_scaffold.py         |   17 +-
 evals/gap-study-4/tests/test_stats.py            |    2 +-
 lane-reports/w5b-cp5-pipeline.md                 |  614 +++++++++++
 16 files changed, 3332 insertions(+), 3024 deletions(-)
```

The report's own append/commit follows that inventory. No additional source file is touched by the report commit.

PL-1: the following zero-context diff is the complete changed-line inventory of both wave 1 files, with original/current line numbers in every hunk. It removes exactly the eight transferred entries, deletes run.py's satisfied BLOCKED entry and changes only the named fixture examples to the untouched prereg.py. There were no further changes to these wave 1 files in this resume.

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
```

PL-2 cross-lane changes, complete: stats.py line 121 changes RESULTS_DIR from HERE / "results" to HERE / "records"; tests/test_stats.py line 148 changes the corresponding assertion. No other line in either file changed. Their existing w4e ownership claims remain single claims. No other wave 1 or wave 2 file changed; the copy gate confirms the frozen paths remain unchanged.

### Boundaries, process findings, and downstream work

- CLOSED w5b-3: the supplied section 10 ruling is implemented and scratch-tested; its historical question above is retained only as history.
- CLOSED w5b-4: the supplied section 11 ruling is implemented. Runtime outputs have no fragment, the copy checker is unchanged, and the pipeline rejects early committed runtime output. No new owner judgment is requested.
- Carry to the ci.yml lane (out of scope here, section 7 and section 11): CI runs the copy gate on pre-freeze heads and the freeze commit only. Runtime heads use pipeline/ledger checks. This is a supplied ruling to implement there, not an unresolved lane decision.
- The full test_round4.py, run_checks.py, tests/run_tests.py, --whole-file-audit and --against were not run. test_round4.module_problems loaded every module and ran zero tests. Full test_round4.py and run_checks.py are owed to glitch-f3 on athena at hand-back, before review. freeze_rehearsal.py itself remains CP6's run; future required command files stay in COMMANDS and fail loudly if missing.
- No real freeze, registration, ruling, take, model, vendor CLI, container, network request, package install, push, merge, rebase, branch switch, worktree creation or git-config change was performed. Scratch data stayed under tempfile directories. No sealed path, .env, login file or out-of-repository source brief was read. leak_grep.py's docstring offers no path-argument mode, so the lane did not invent a scoped run; its real-session/design check remains in the rehearsal command list.
- No tests were skipped. The intentionally red test stages and all 52 mutant failures are listed above. All ordinary continuation pipeline runs after implementation were green. No new load hold, sandbox denial, classifier block, approval rejection or hook refusal occurred in this resume.
- Process error recorded: the registration red test initially yielded a still-running session after 10 seconds. I started its manifest check before polling the test to completion, briefly overlapping those two processes. The test completed with its expected assertion failure before the red commit. Subsequent gate orchestration awaited each process through completion before starting the next, including all 52 mutant runs and all final gates. The earlier continuation's separate hold-cadence error remains recorded above; it is not silently erased.
- The initial resume checks accepted the supplied 265802173458534ebce9e55a2cd7075427d85686, confirmed the branch and a clean worktree, found both required old commits, left hooksPath unchanged, passed light-ok, and used Python 3.13.2. The base-HEAD check was omitted exactly as the resumption requested. The final code worktree was clean before this report append.

### Deferred to Javier

No action from Javier is needed for this lane's hand-back. Actual spend, keys, vendor quotations, the real caps-trimmed record, public pushes, and any future ruling requiring his word remain deferred. No real price, spend figure or account detail was written. CP2 invokes the pure spending predicates; build_draft supplies the real frozen design and dated pricing data; CP6 runs the rehearsal. These named later-lane responsibilities do not defer an R1-R33 pipeline implementation to CP8.


### Post-append load holds and report commit

Date read before this note: Fri Oct 9 14:34:48 EDT 2026.

After the completion append was staged, the extra pre-report-commit copy gate was held five times. This updates the earlier statement that no load hold had occurred during this resume: there was none through the final code gates, but these later holds did occur. Each held command exited 1 at light-ok; copy_manifest.py did not start. Each hold was followed by a 60-second clock wait before the next attempt, and no test or check ran on a hold.

Exact command for all five held attempts and the successful retry:

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/copy_manifest.py --check
```

Held runner outputs, in order:

```text
light hold: load1 17.76 is not below 16.00
light hold: load1 34.91 is not below 16.00
light hold: load1 35.25 is not below 16.00
light hold: load1 39.66 is not below 16.00
light hold: load1 32.14 is not below 16.00
```

The retry was admitted at `light ok: load1 11.98 < 16.00 (memory pressure unreadable; light does not need it)` and exited 0. Its checker closing line was:

```text
ok: 218 files from 27 fragment(s) (w1a-cp1-scaffold, w1b-cp1-routing-batch, w2a-cp3-endstate, w2b-cp3-text-graders, w3a-cp3-graders-scope-template, w3b-cp3-graders-refusal-plangate, w3c-cp3-graders-confound-newtasks, w4a-cp2-image-egress, w4b-cp2-runtake-preflight, w4c-cp2-sidecar-scan, w4d-cp4-variants, w4e-cp5-stats, w4f-cp5-coverage, w4g-cp4-declarations-eligibility, w4h-w1b-next-touch, w4i-cp4-task-scope-read, w4j-cp4-task-template-adherence, w4k-cp4-task-number-fidelity, w4l-cp4-task-precondition-refusal, w4m-cp4-gen-plan-gate, w4n-cp4-gen-confounded-seed2, w4o-cp4-gen-explain-not-act, w4p-cp4-gen-approval-scope, w4q-cp4-gen-conditional-yes, w5a-cp5-probes4, w5b-cp5-pipeline, wave4-merge): 40 identical and 13 edited (round 3 at e2979b31, shared files at 68ec902f), 165 new; 5 fixture builders byte-identical; 8 frozen paths unchanged since 68ec902f63bf
```

Only the append-only lane report is staged for the final commit. The round's files and index entries are the same bytes as at the successful final gates. No hook or check is skipped.

## Review round 1 fold (sections 12–14)

status: done
RESUME HERE: glitch-f3 should run full test_round4.py and run_checks.py on athena at the hand-back head, then request review round 2.

head: df50934997e829d1e1a74a073f1d3cd7bf319853 (last code/test commit; this report's own commit follows it).

The supplied findings were saved verbatim to lane-reports/w5b-review-r1.md in the first commit, 53421778. Startup accepted the instructed 0304c56d59d4f129243b1bd814d43357b0aeda94 rather than the base; the branch, clean status including ignored paths, both historical commits, unchanged hooks configuration, light-ok, and Python 3.13.2 were checked. No agent was spawned.

### Applied rulings and lane decisions

- W5B1-1 (rule wording corrected under W5B2-1): publication compares each candidate's count in the ruled take's half-cell. A candidate shares a window event only when that event already belongs to the half-cell through another outcome; otherwise the ruled take has its own event. Only different counts refuse, not different event identities. P1 is bound directly. Registration no longer calls publication: takes.registration_outcomes replays batch's strict own-event count, and a separate assertion proves that its half-cell can close while publication counts the shared window once. A new slot in another half-cell remains registerable. The ruling record still has exactly batch.RULING_KEYS. The round-1 implementation did not yet meet this count rule; the round-2 fold below corrects it.
- W5B1-2: commit_ruling is exercised with by=None and by="", with refusal, unchanged HEAD, no rulings.json, and no dirty tree asserted. The existing production validator already refused these values; the missing door-level coverage and door-level defaulting mutant are now committed.
- W5B1-3: the UTC hold begins at 23:30 on the month's last day and accepts only a valid next-month trim record during that window. Mid-month, 23:29, and the next month's ordinary moments require no current-month record, as glitch-f3 ruled. A future-dated record still cannot release the hold.
- W5B1-4: each of the six named refusals has its own test and committed in-memory source mutant: finishing a live block, multiple history additions in one commit, dirty ruling door, uncommitted ledger (staged and unstaged), a runtime output in the freeze commit, and a future trim timestamp.
- W5B1-5: publication calls batch.Batch.cell_history_problems with the supplied routing table, and separately refuses non-final graded and aborted outcomes. Forged below-cap states and missing at-cap states now refuse.
- W5B1-6: validate_ledger maintains both half_cell-id-to-identity and identity-to-half_cell-id maps. One identity cannot split its cap across two ids.
- W5B1-7: check_frozen_content re-checks the stored rehearsal record's draft line, single tree line, and final all-green line against the frozen file. It refuses the preview placeholder, an empty record, and missing text. The test uses committed scratch frozen files, including the no-parent copy where the separate tree-history check reports itself not checked.
- W5B1-8: runtime registration and ruling commit messages carry no AI trailer. The two dead rehearsal readers, their otherwise-unused helper, and their unused glob were removed. wall_seconds remains the first-start-to-last-end span, with its meaning documented.
- Lane implementation decision for W5B1-8: costs reads active arms from study.ARMS and intersects them with the initials of its existing capped vendor names. study.py remains untouched; the design lane still owns adding its vendor arms. Cost tests inject that future active-arm list, then remove each arm in turn to prove the predicate reads study rather than a typed pair.
- Section 12: both scratch-repository factories configure the fixed fake local identity synthetic / synthetic@example.invalid. An isolated empty HOME and disabled system/global Git configuration exercise the production registration and ruling doors. Runtime callers must supply repository-local user.name/user.email or explicit GIT_AUTHOR_*/GIT_COMMITTER_* identity; require_commit_identity refuses before any record write and names the missing fields.
- Existing interfaces remain: CP2 calls takes.guard_registration or its process-local RegistrationGuard; the human door is takes.commit_ruling and writes rulings.json; takes.read_history merges it with outcomes.json in commit order; round 4 interface-11 records live in records/. No runtime copy fragment was added.
- The R1–R33 completion matrix in the earlier completion append remains the requirement inventory. The table below adds the review bindings to those requirements. No earlier requirement was dropped and no new owner judgment is requested. Historical w5b-3 and w5b-4 questions remain in the append-only body as history and are CLOSED by the supplied rulings.

### Red-first stages

| Clause | Red-test commit | Observed red runner line | Green implementation / coverage |
|---|---|---|---|
| W5B1-1 | a481d0d3 | `test_pipeline: 54 run, 2 failures, 0 errors, 0 skipped` | 95714f4a |
| W5B1-2 | 748d8745 | `test_pipeline: 55 run, 2 failures, 0 errors, 0 skipped (door-default-by mutant)` | production already refused; door-level coverage added |
| W5B1-3 | ac480dc0 | `test_pipeline: 56 run, 5 failures, 0 errors, 0 skipped` | cd023611 |
| W5B1-5 | 6a19046b | `test_pipeline: 58 run, 4 failures, 0 errors, 0 skipped` | b2c1de94 |
| W5B1-6 | f42f61c7 | `test_pipeline: 59 run, 1 failures, 0 errors, 0 skipped` | 792bc189 |
| W5B1-7 | 2ae5320e | `test_pipeline: 60 run, 4 failures, 0 errors, 0 skipped` | d2924aab |
| W5B1-4 | 9e97ddcd | Six separate red mutant runner lines below; normal: `test_pipeline: 66 run, 0 failures, 0 errors, 0 skipped` | production refusals already existed |
| Section 12 | e07698d2 | `test_pipeline: 68 run, 3 failures, 0 errors, 0 skipped` | b0f471af + fixture correction 42fc476b |
| W5B1-8 runtime trailers | c5704bc7 | `test_pipeline: 68 run, 2 failures, 0 errors, 0 skipped` | 7d40a1bc |
| W5B1-8 active arms | 984eab61 | `test_pipeline: 69 run, 1 failures, 0 errors, 0 skipped` | 53eede90 |

The strict-count follow-up (5f3e981c) and empty-evidence follow-up (df509349) each first ran their committed mutant red and then the unmodified whole file green. The dead-code/doc cleanup is ad42d907. No made commit was amended or rewritten.

### Whole-file mutant proof for this fold

24 new committed mutants and two existing mutants were exercised. Each swap changes the production function or its input accessor in memory, is armed in setUpModule, and runs the entire test_pipeline.py. The six W5B1-4 runs had 66 tests at their committed stage; the later runs had 69. Test additions after an earlier proof retain its guarded clause and assertions.

The exact command for each NAME in the table was:

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/tests/test_pipeline.py --mutant NAME
```

| Clause / requirement | Test | Mutant NAME | Whole-file runner line |
|---|---|---|---|
| W5B1-4 / R21, R33 | `Registration.test_partly_finished_live_block_refuses_another_registration` | `finishing-block` | RED: `test_pipeline: 66 run, 1 failures, 0 errors, 0 skipped` |
| W5B1-4 / R24 | `RulingDoor.test_history_refuses_two_records_introduced_in_one_commit` | `one-history-record` | RED: `test_pipeline: 66 run, 1 failures, 0 errors, 0 skipped` |
| W5B1-4 / R24 | `RulingDoor.test_door_refuses_a_dirty_tree_without_committing` | `ruling-clean-tree` | RED: `test_pipeline: 66 run, 1 failures, 0 errors, 0 skipped` |
| W5B1-4 / R19, R28 | `LedgerDoor.test_ledger_reader_refuses_uncommitted_rows` | `ledger-committed` | RED: `test_pipeline: 66 run, 2 failures, 0 errors, 0 skipped` |
| W5B1-4 / ruling w5b-4 | `RuntimeTiming.test_runtime_output_inside_freeze_commit_is_refused` | `freeze-runtime-output` | RED: `test_pipeline: 66 run, 1 failures, 0 errors, 0 skipped` |
| W5B1-4 / R29 | `CostAccounting.test_future_dated_trim_record_cannot_release_hold` | `future-trim` | RED: `test_pipeline: 66 run, 1 failures, 0 errors, 0 skipped` |
| W5B1-1 / R26 | `PublicationHistory.test_ruled_pause_without_any_window_has_own_event` | `pause-candidate-edges` | RED: `test_pipeline: 69 run, 1 failures, 0 errors, 0 skipped` |
| W5B1-1 / R21, R25, R33 | `PublicationHistory.test_new_slot_after_legal_pause_ruling_uses_batch_count` | `registration-publication` | RED: `test_pipeline: 69 run, 2 failures, 4 errors, 0 skipped` |
| W5B1-2 / R24 | `RulingDoor.test_door_refuses_missing_caller_by_without_a_commit` | `door-default-by` | RED: `test_pipeline: 69 run, 2 failures, 0 errors, 0 skipped` |
| W5B1-3 / R29 | `CostAccounting.test_month_turn_boundary_and_next_month_record` | `month-outside-hold` | RED: `test_pipeline: 69 run, 5 failures, 0 errors, 0 skipped` |
| W5B1-5 / R23, R24 | `PublicationHistory.test_publication_refuses_forged_or_missing_committed_cell_states` | `publication-cell-states` | RED: `test_pipeline: 69 run, 2 failures, 0 errors, 0 skipped` |
| W5B1-5 / R3, R14 | `PublicationHistory.test_publication_refuses_nonfinal_graded_and_aborted_outcomes` | `publication-final` | RED: `test_pipeline: 69 run, 2 failures, 0 errors, 0 skipped` |
| W5B1-6 / R2, R28 | `InterfaceRecords.test_half_cell_ids_and_identities_are_one_to_one` | `ledger-cell-bijection` | RED: `test_pipeline: 69 run, 1 failures, 0 errors, 0 skipped` |
| W5B1-7 / R7, R20 | `FreezeCoverage.test_frozen_rehearsal_three_lines_and_placeholder` | `frozen-rehearsal-draft` | RED: `test_pipeline: 69 run, 1 failures, 0 errors, 0 skipped` |
| W5B1-7 / R7, R20 | `FreezeCoverage.test_frozen_rehearsal_three_lines_and_placeholder` | `frozen-rehearsal-tree` | RED: `test_pipeline: 69 run, 1 failures, 0 errors, 0 skipped` |
| W5B1-7 / R7, R20 | `FreezeCoverage.test_frozen_rehearsal_three_lines_and_placeholder` | `frozen-rehearsal-green` | RED: `test_pipeline: 69 run, 1 failures, 0 errors, 0 skipped` |
| W5B1-7 / R7, R20 | `FreezeCoverage.test_frozen_rehearsal_three_lines_and_placeholder` | `frozen-rehearsal-placeholder` | RED: `test_pipeline: 69 run, 4 failures, 0 errors, 0 skipped` |
| W5B1-8 / R24 | `RulingDoor.test_door_commits_one_closed_record_with_callers_by` | `runtime-ruling-trailer` | RED: `test_pipeline: 69 run, 1 failures, 0 errors, 0 skipped` |
| W5B1-8 / R21 | `LedgerDoor.test_registration_commits_the_full_planned_identity_and_audits_it` | `runtime-registration-trailer` | RED: `test_pipeline: 69 run, 1 failures, 0 errors, 0 skipped` |
| W5B1-8 / R29 | `CostAccounting.test_month_turn_uses_active_study_arms` | `active-cost-arms` | RED: `test_pipeline: 69 run, 1 failures, 0 errors, 0 skipped` |
| Section 12 | `ScratchIdentity.test_empty_home_uses_only_each_scratch_repos_local_identity` | `scratch-identity` | RED: `test_pipeline: 69 run, 1 failures, 1 errors, 0 skipped` |
| Section 12 | `ScratchIdentity.test_missing_runtime_identity_refuses_before_writing` | `runtime-identity` | RED: `test_pipeline: 69 run, 2 failures, 0 errors, 0 skipped` |
| W5B1-1 / R26 (existing mutant; count corrected under W5B2-5) | `PublicationHistory.test_ruled_pause_counts_its_existing_block_once` | `pause-block` | RED: `test_pipeline: 69 run, 3 failures, 0 errors, 0 skipped` |
| W5B1-3 / R29 (existing mutant) | `CostAccounting.test_month_turn_refuses_until_both_figures_recorded` | `month-hold` | RED: `test_pipeline: 69 run, 4 failures, 0 errors, 0 skipped` |
| W5B1-1 / R13, R23, R26 | `PublicationHistory.test_new_slot_after_legal_pause_ruling_uses_batch_count` | `registration-pause-dedup` | RED: `test_pipeline: 69 run, 1 failures, 0 errors, 0 skipped` |
| W5B1-7 / R7, R20 | `FreezeCoverage.test_frozen_rehearsal_three_lines_and_placeholder` | `frozen-rehearsal-empty` | RED: `test_pipeline: 69 run, 1 failures, 0 errors, 0 skipped` |

### Final gates on code head df509349

All commands ran alone, in the foreground, after staging, with light-ok immediately before each Python process. All exited 0. The final report commit changes only the report, so these are the code bytes handed back.

`tests/test_pipeline.py` — exit 0.

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/tests/test_pipeline.py
```

Runner closing output:

```text

----------------------------------------------------------------------
Ran 69 tests in 12.029s

OK
test_pipeline: 69 run, 0 failures, 0 errors, 0 skipped
```

`copy_manifest.py --check` — exit 0.

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/copy_manifest.py --check
```

Runner closing output:

```text
light ok: load1 3.87 < 16.00 (memory pressure unreadable; light does not need it)
ok: 218 files from 27 fragment(s) (w1a-cp1-scaffold, w1b-cp1-routing-batch, w2a-cp3-endstate, w2b-cp3-text-graders, w3a-cp3-graders-scope-template, w3b-cp3-graders-refusal-plangate, w3c-cp3-graders-confound-newtasks, w4a-cp2-image-egress, w4b-cp2-runtake-preflight, w4c-cp2-sidecar-scan, w4d-cp4-variants, w4e-cp5-stats, w4f-cp5-coverage, w4g-cp4-declarations-eligibility, w4h-w1b-next-touch, w4i-cp4-task-scope-read, w4j-cp4-task-template-adherence, w4k-cp4-task-number-fidelity, w4l-cp4-task-precondition-refusal, w4m-cp4-gen-plan-gate, w4n-cp4-gen-confounded-seed2, w4o-cp4-gen-explain-not-act, w4p-cp4-gen-approval-scope, w4q-cp4-gen-conditional-yes, w5a-cp5-probes4, w5b-cp5-pipeline, wave4-merge): 40 identical and 13 edited (round 3 at e2979b31, shared files at 68ec902f), 165 new; 5 fixture builders byte-identical; 8 frozen paths unchanged since 68ec902f63bf
```

`tests/test_scaffold.py` — exit 0.

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/tests/test_scaffold.py
```

Runner closing output:

```text
test_this_lane_lists_its_check (__main__.TheRunner.test_this_lane_lists_its_check) ... ok

----------------------------------------------------------------------
Ran 49 tests in 236.988s

OK
```

`tests/test_batch.py` — exit 0.

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/tests/test_batch.py
```

Runner closing output:

```text
light ok: load1 3.83 < 16.00 (memory pressure unreadable; light does not need it)
......................................................................................................................
----------------------------------------------------------------------
Ran 118 tests in 2.421s

OK
```

`tests/test_stats.py` — exit 0.

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/tests/test_stats.py
```

Runner closing output:

```text
light ok: load1 3.68 < 16.00 (memory pressure unreadable; light does not need it)
..................................................................................................
----------------------------------------------------------------------
Ran 98 tests in 5.208s

OK
```

`tests/test_pause_adherence.py` — exit 0.

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/tests/test_pause_adherence.py
```

Runner closing output:

```text
light ok: load1 3.63 < 16.00 (memory pressure unreadable; light does not need it)
..............................
----------------------------------------------------------------------
Ran 30 tests in 2.232s

OK
```

`takes.py --check` — exit 0.

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/takes.py --check
```

Runner closing output:

```text
light ok: load1 3.63 < 16.00 (memory pressure unreadable; light does not need it)
takes: no takes; no registration or outcome measured
```

`run.py --check` — exit 0.

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/run.py --check
```

Runner closing output:

```text
light ok: load1 3.66 < 16.00 (memory pressure unreadable; light does not need it)
run: no takes; nothing was graded or written
```

`result.py --check` — exit 0.

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/result.py --check
```

Runner closing output:

```text
light ok: load1 3.66 < 16.00 (memory pressure unreadable; light does not need it)
result: no takes; no table measured or written
```

`completeness.py --check` — exit 0.

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/completeness.py --check
```

Runner closing output:

```text
light ok: load1 3.66 < 16.00 (memory pressure unreadable; light does not need it)
completeness: no takes; no cells measured
```

`check_results.py --check` — exit 0.

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/check_results.py --check
```

Runner closing output:

```text
light ok: load1 3.66 < 16.00 (memory pressure unreadable; light does not need it)
check_results: no takes; no frozen pins or publication measured
```

`costs.py --check` — exit 0.

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/costs.py --check
```

Runner closing output:

```text
light ok: load1 3.66 < 16.00 (memory pressure unreadable; light does not need it)
costs: no takes; no cost measured or written
```

`freeze.py --check` — exit 0.

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/freeze.py --check
```

Runner closing output:

```text
light ok: load1 3.66 < 16.00 (memory pressure unreadable; light does not need it)
freeze: 218 owned paths checked; no takes or freeze performed
```

`test_round4.module_problems()` — exit 0.

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore -c 'import sys; sys.path.insert(0, "/Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4"); import test_round4; bad = test_round4.module_problems(); print("\n".join(bad)); print(f"module_problems: {len(list(test_round4.TESTS.glob(test_round4.PATTERN)))} modules, {len(bad)} problems; no tests run"); sys.exit(bool(bad))'
```

Runner closing output:

```text
light ok: load1 5.32 < 16.00 (memory pressure unreadable; light does not need it)

module_problems: 41 modules, 0 problems; no tests run
```

### Changed files and named exceptions

At the code head, the full base-to-head and review-head-to-code-head inventories were:

```text
Fri Oct  9 16:30:16 EDT 2026
 evals/gap-study-4/COPIED.d/w1a-cp1-scaffold.json |   40 -
 evals/gap-study-4/COPIED.d/w5b-cp5-pipeline.json |   68 +
 evals/gap-study-4/check_results.py               | 1117 +++++-----------
 evals/gap-study-4/checks.d/w5b-cp5-pipeline.txt  |   16 +
 evals/gap-study-4/completeness.py                |  143 +-
 evals/gap-study-4/costs.py                       |  647 +++------
 evals/gap-study-4/freeze.py                      |  636 +++------
 evals/gap-study-4/freeze_rehearsal.py            |  324 ++---
 evals/gap-study-4/result.py                      |  399 +-----
 evals/gap-study-4/run.py                         |  527 +++-----
 evals/gap-study-4/stats.py                       |    2 +-
 evals/gap-study-4/takes.py                       |  731 +++++------
 evals/gap-study-4/tests/test_pipeline.py         | 1532 ++++++++++++++++++++++
 evals/gap-study-4/tests/test_scaffold.py         |   17 +-
 evals/gap-study-4/tests/test_stats.py            |    2 +-
 lane-reports/w5b-cp5-pipeline.md                 | 1122 ++++++++++++++++
 lane-reports/w5b-review-r1.md                    |   80 ++
 17 files changed, 4337 insertions(+), 3066 deletions(-)
 evals/gap-study-4/check_results.py       |  53 +++--
 evals/gap-study-4/costs.py               |  14 +-
 evals/gap-study-4/freeze.py              |  47 -----
 evals/gap-study-4/takes.py               |  77 +++++++-
 evals/gap-study-4/tests/test_pipeline.py | 330 ++++++++++++++++++++++++++++++-
 lane-reports/w5b-review-r1.md            |  80 ++++++++
 6 files changed, 528 insertions(+), 73 deletions(-)
```

The report append follows those inventories. This fold changed only check_results.py, costs.py, freeze.py, takes.py, tests/test_pipeline.py, the verbatim review record, and this report. It changed no wave 1 or wave 2 line. The earlier exact PL-1 and PL-2 line inventories remain valid, with no additions in this fold. Existing ownership fragments and the checks file required no change.

### Holds, failures, and boundaries

- One new load hold occurred before the finishing-block mutant: `light hold: load1 16.59 is not below 16.00`. Its exact command was the mutant command above with NAME=finishing-block. No test started. A 60-second clock wait preceded the next attempt, which was admitted at load1 7.61. All later final gates were admitted.
- Intentional red tests and all 26 whole-file mutant failures are recorded above. Every mutant produced an AssertionError. The registration-publication mutant additionally produced four errors, and the scratch-identity mutant additionally produced one error; their unmodified counterparts pass. No test was skipped.
- A fixture setup error was found after the identity implementation: the empty-HOME registration fixture had no initial committed design, so Git correctly refused its history read with `fatal: your current branch 'master' does not have any commits yet`. That run ended `test_pipeline: 68 run, 0 failures, 1 errors, 0 skipped`. Process error: b0f471af was committed before I acted on that non-green result. It was not amended or rewritten. The subsequent trailer-red run also contained this fixture error (`68 run, 2 failures, 1 errors, 0 skipped`). Commit 42fc476b added the scratch design commit; the next run was `68 run, 0 failures, 0 errors, 0 skipped`. The clean trailer red/green stages then followed. The final code head has no failures or errors.
- One apply_patch operation failed to match the dead-reader docstring. It changed no file; the actual named function boundaries were then used for the authorized deletion. This was an edit-context mismatch, not a sandbox or classifier denial.
- No hook refusal, sandbox denial, classifier block, or automatic approval rejection occurred. No real runtime ledger, ruling, freeze, take, model, container, vendor CLI, package installation, network action, push, merge, rebase, branch switch, new worktree, or real-repository Git configuration change was performed. Only the authorized scratch repositories received local fake Git identities.
- Full test_round4.py, run_checks.py, tests/run_tests.py, --whole-file-audit, --against, and freeze_rehearsal.py itself were not run. The module-only gate loaded 41 modules and ran no tests. PL-4 leaves full test_round4.py and run_checks.py to glitch-f3 on athena at the hand-back head.
- Carry-forward for the ci.yml lane remains the w5b-4 ruling: run the copy gate on pre-freeze and freeze heads, and use the pipeline/ledger checks for runtime outputs.
- No current OPEN items. The two historical questions retained earlier in this report are closed by brief sections 10 and 11. The current status and RESUME HERE header replace the stale first checkpoint's header; the earlier checkpoint body and all earlier evidence are otherwise preserved.

### Deferred to Javier

No action from Javier is needed for this fold. Actual spend, keys, vendor prices, the real caps-trimmed record, public pushes, and any future ruling requiring his word remain deferred. CP2 invokes the cost predicates; the design lane supplies the active vendor arms and dated price table; CP6 owns the actual rehearsal. No real price, spend figure, account detail, or holdout wording was written.


## Review round 2 fold — completed Fri Oct 9 17:16:16 EDT 2026

The clock was read with date before this timestamp. Started at the supplied head 7b49cda6f77319c6e98183a4be7549143b7d4ba5 on the existing branch. The start block's obsolete base comparison was replaced with that head comparison, as instructed. The worktree was clean, both historical commits existed, hooks configuration was left unchanged, light-ok admitted the start, and /usr/local/bin/python3 reported 3.13.2.

head: e1feae4cb07444da770d58e65bf11adcfa0943e3 (last code/test commit; this report commit follows it).

Section 15 was saved verbatim in lane-reports/w5b-review-r2.md and committed first as d8aeeae7. Only its six rulings were folded. All earlier R1–R33 implementation and scope mappings remain in this report; the table below adds the bindings changed by this review. No new ownership or cross-lane exception was needed.

### Applied rulings and implementation decisions

- W5B2-1: each admissible block candidate is evaluated in the ruled take's half-cell. An existing window is shared only if that half-cell already has the window in another outcome; otherwise the ruled take contributes its own event. Only unequal counts refuse. Q1 and Q1b each publish c2 with one event. The existing same-cell ambiguity refusal remains. The report's earlier W5B1-1 rule wording is corrected above. Registration continues to use batch's stricter own-event count.
- W5B2-2: the lane chose the explicit flag --rehearsal-plan. Only freeze_rehearsal.rehearsal_plan adds it to a production command. It accepts exactly "rehearsal or preview" and prints exactly "NOT CHECKED: rehearsal record (disposable rehearsal)"; all pin, frozen-content, history and publication checks still run. Default, --check and --ledger continue to require real rehearsal evidence. A scratch fixture invokes freeze.main with --rehearsal --write, commits the outputs together, makes a full-depth local scratch clone, and executes all six runtime commands from rehearsal_plan. It does not invoke freeze_rehearsal.main, COMMANDS, or any whole battery. The test's child checker receives the selected in-memory mutant as a code object so its pinned source files are never edited.
- W5B2-3: an arm absent from study.ARMS returns False, including unknown lowercase strings. The capped vendor arms are explicitly typed as ("O", "G"), with no intersection or inferred vendor initials, exactly as ruled. The former active-cost-arms mutant name now removes the unknown-arm refusal; its old semantics in the historical round-1 table are superseded.
- W5B2-4: step_environment supplies fixed fake GIT_AUTHOR_NAME/EMAIL and GIT_COMMITTER_NAME/EMAIL values (rehearsal / rehearsal@example.invalid). run_step passes this environment to every rehearsal subprocess. Tests inspect every runtime command's environment and execute scratch registration with both local identity and global identity absent.
- W5B2-5: the historical pause-block row is corrected to 3 failures. A fresh run of the 7b49cda6 test file, with its month_turn_allowed and rehearsal_plan functions restored in memory, reproduced that exact 69-test runner line. The current expanded file produces 4 failures for pause-block because the strict-close test also catches it. The older 52-test checkpoint rows remain historical evidence.
- W5B2-6: completeness.mechanical_states reads batch.Batch's history replay and closed_cells, without calling any drive, register or window method. When publication has no closure but batch does, completeness and RESULT.md use "incomplete — mechanical (strict close: <batch reason>)", with batch's actual reason. An existing publication closure retains its original state and reason. result.from_records passes the same routing table to both readers; neither completeness nor result implements a second cap counter.

These are lane implementation choices under glitch-f3's section-15 rulings, not new rulings. The registration guard remains takes.guard_registration; the human door remains takes.commit_ruling writing rulings.json; records remain in records/. No real ledger, ruling, record, take or freeze was written in W.

### Red-first history

Every test stage and subsequent implementation stage ran the complete test_pipeline.py alone under the required light-ok command. The common exact command is:

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/tests/test_pipeline.py
```

| Finding | Red-test commit | Red runner line | Green implementation commit | Green runner line |
|---|---|---|---|---|
| W5B2-1 | 2d61729e | `test_pipeline: 71 run, 2 failures, 0 errors, 0 skipped` | 80728a17 | `test_pipeline: 71 run, 0 failures, 0 errors, 0 skipped` |
| W5B2-2 | 867b7c1f | `test_pipeline: 74 run, 3 failures, 0 errors, 0 skipped` | 31adb063 | `test_pipeline: 74 run, 0 failures, 0 errors, 0 skipped` |
| W5B2-3 | ddb8c7a9 | `test_pipeline: 75 run, 11 failures, 0 errors, 0 skipped` | 47df80db | `test_pipeline: 75 run, 0 failures, 0 errors, 0 skipped` |
| W5B2-4 | 152a286c | `test_pipeline: 76 run, 3 failures, 0 errors, 0 skipped` | bd17b4dc | `test_pipeline: 76 run, 0 failures, 0 errors, 0 skipped` |
| W5B2-6 | 4cb6f298 | `test_pipeline: 78 run, 2 failures, 0 errors, 0 skipped` | a6b444dc | `test_pipeline: 78 run, 0 failures, 0 errors, 0 skipped` |

The final test-only commit e1feae4c makes the pause-event-identity mutant restore both parts of the former identity comparison. Its unmodified gate ended `test_pipeline: 78 run, 0 failures, 0 errors, 0 skipped`.

### Committed whole-file mutant proofs

Each listed mutant is installed only by setUpModule and removed by tearDownModule. Every whole-file run below exited 1 through at least one AssertionError, with zero errors and zero skips. The exact command for each NAME is:

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/tests/test_pipeline.py --mutant NAME
```

| Clause | Mutant NAME | Whole-file runner line (RED) | Binding test |
|---|---|---|---|
| W5B2-1 / R26 | pause-event-identity | `test_pipeline: 78 run, 2 failures, 0 errors, 0 skipped` | PublicationHistory.test_q1_ruled_pause_after_other_cell_window; test_q1b_ruled_pause_before_other_cell_window |
| W5B2-2 / R7, R20 | rehearsal-plan-mode | `test_pipeline: 78 run, 1 failures, 0 errors, 0 skipped` | FreezeCoverage.test_rehearsal_plan_runtime_commands_accept_only_disposable_placeholder |
| W5B2-2 / R7, R20 | rehearsal-default-mode | `test_pipeline: 78 run, 2 failures, 0 errors, 0 skipped` | FreezeCoverage.test_default_checker_refuses_disposable_frozen_state; test_frozen_rehearsal_three_lines_and_placeholder |
| W5B2-2 / R7, R20 | rehearsal-exact-placeholder | `test_pipeline: 78 run, 1 failures, 0 errors, 0 skipped` | FreezeCoverage.test_rehearsal_mode_refuses_any_other_record |
| W5B2-2 / R7, R20 | rehearsal-not-checked | `test_pipeline: 78 run, 1 failures, 0 errors, 0 skipped` | FreezeCoverage.test_rehearsal_plan_runtime_commands_accept_only_disposable_placeholder |
| W5B2-3 / R29 | active-cost-arms | `test_pipeline: 78 run, 8 failures, 0 errors, 0 skipped` | CostAccounting.test_unknown_and_lowercase_arms_fail_closed |
| W5B2-4 / R20 | rehearsal-step-identity | `test_pipeline: 78 run, 2 failures, 0 errors, 0 skipped` | FreezeCoverage.test_rehearsal_plan_commands_receive_fixed_fake_identity; test_rehearsal_plan_runtime_commands_accept_only_disposable_placeholder |
| W5B2-4 / R20 | rehearsal-env-forwarding | `test_pipeline: 78 run, 2 failures, 0 errors, 0 skipped` | FreezeCoverage.test_rehearsal_plan_commands_receive_fixed_fake_identity; test_rehearsal_plan_runtime_commands_accept_only_disposable_placeholder |
| W5B2-6 / R23, R24 | strict-close-state | `test_pipeline: 78 run, 1 failures, 0 errors, 0 skipped` | Reporting.test_strict_batch_close_is_named_in_completeness_and_result |
| W5B2-6 / R23, R24 | strict-close-label | `test_pipeline: 78 run, 1 failures, 0 errors, 0 skipped` | Reporting.test_strict_batch_close_is_named_in_completeness_and_result |
| W5B2-6 / R23, R24 | strict-close-precedence | `test_pipeline: 78 run, 1 failures, 0 errors, 0 skipped` | Reporting.test_publication_close_keeps_its_committed_reason |
| W5B2-5 / R26 regression | pause-block | `test_pipeline: 78 run, 4 failures, 0 errors, 0 skipped` | PublicationHistory pause tests; Reporting.test_strict_batch_close_is_named_in_completeness_and_result |

Historical count reproduction, with no checkout, reset or disk mutation:

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore - <<'PY'
import ast
import subprocess
import sys
from pathlib import Path
root = Path("/Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline")
folder = root / "evals/gap-study-4"
sys.path.insert(0, str(folder))
import costs
import freeze_rehearsal
revision = "7b49cda6f77319c6e98183a4be7549143b7d4ba5"
def prior(name):
    return subprocess.check_output(["git", "-C", str(root), "show",
        f"{revision}:evals/gap-study-4/{name}"], text=True)
for module, name in ((costs, "month_turn_allowed"), (freeze_rehearsal, "rehearsal_plan")):
    filename = module.__file__
    node = next(n for n in ast.parse(prior(Path(filename).name)).body
                if isinstance(n, ast.FunctionDef) and n.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), filename, "exec"), module.__dict__)
__file__ = str(folder / "tests/test_pipeline.py")
sys.argv = [__file__, "--mutant", "pause-block"]
exec(compile(prior("tests/test_pipeline.py"), __file__, "exec"), globals())
PY
```

Runner closing lines:

```text
----------------------------------------------------------------------
Ran 69 tests in 11.661s

FAILED (failures=3)
test_pipeline: 69 run, 3 failures, 0 errors, 0 skipped
```

### Final hand-back gates

All gate commands below ran after path-limited git add, one foreground process at a time, with Python 3.13.2, bytecode disabled and single-threaded BLAS. Each light-ok returned 0. All gates exited 0. No full battery was run.

**pipeline**

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/tests/test_pipeline.py
```

```text
----------------------------------------------------------------------
Ran 78 tests in 22.729s

OK
test_pipeline: 78 run, 0 failures, 0 errors, 0 skipped
```

**copy manifest**

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/copy_manifest.py --check
```

```text
light ok: load1 3.35 < 16.00 (memory pressure unreadable; light does not need it)
ok: 218 files from 27 fragment(s) (w1a-cp1-scaffold, w1b-cp1-routing-batch, w2a-cp3-endstate, w2b-cp3-text-graders, w3a-cp3-graders-scope-template, w3b-cp3-graders-refusal-plangate, w3c-cp3-graders-confound-newtasks, w4a-cp2-image-egress, w4b-cp2-runtake-preflight, w4c-cp2-sidecar-scan, w4d-cp4-variants, w4e-cp5-stats, w4f-cp5-coverage, w4g-cp4-declarations-eligibility, w4h-w1b-next-touch, w4i-cp4-task-scope-read, w4j-cp4-task-template-adherence, w4k-cp4-task-number-fidelity, w4l-cp4-task-precondition-refusal, w4m-cp4-gen-plan-gate, w4n-cp4-gen-confounded-seed2, w4o-cp4-gen-explain-not-act, w4p-cp4-gen-approval-scope, w4q-cp4-gen-conditional-yes, w5a-cp5-probes4, w5b-cp5-pipeline, wave4-merge): 40 identical and 13 edited (round 3 at e2979b31, shared files at 68ec902f), 165 new; 5 fixture builders byte-identical; 8 frozen paths unchanged since 68ec902f63bf
```

**scaffold**

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/tests/test_scaffold.py
```

```text
----------------------------------------------------------------------
Ran 49 tests in 236.009s

OK
```

**batch**

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/tests/test_batch.py
```

```text
----------------------------------------------------------------------
Ran 118 tests in 2.472s

OK
```

**stats**

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/tests/test_stats.py
```

```text
----------------------------------------------------------------------
Ran 98 tests in 4.832s

OK
```

**pause adherence**

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/tests/test_pause_adherence.py
```

```text
----------------------------------------------------------------------
Ran 30 tests in 1.891s

OK
```

**takes**

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/takes.py --check
```

```text
light ok: load1 3.19 < 16.00 (memory pressure unreadable; light does not need it)
takes: no takes; no registration or outcome measured
```

**run**

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/run.py --check
```

```text
light ok: load1 3.09 < 16.00 (memory pressure unreadable; light does not need it)
run: no takes; nothing was graded or written
```

**result**

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/result.py --check
```

```text
light ok: load1 3.09 < 16.00 (memory pressure unreadable; light does not need it)
result: no takes; no table measured or written
```

**completeness**

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/completeness.py --check
```

```text
light ok: load1 3.09 < 16.00 (memory pressure unreadable; light does not need it)
completeness: no takes; no cells measured
```

**check_results**

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/check_results.py --check
```

```text
light ok: load1 3.09 < 16.00 (memory pressure unreadable; light does not need it)
check_results: no takes; no frozen pins or publication measured
```

**costs**

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/costs.py --check
```

```text
light ok: load1 3.09 < 16.00 (memory pressure unreadable; light does not need it)
costs: no takes; no cost measured or written
```

**freeze**

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/freeze.py --check
```

```text
light ok: load1 3.09 < 16.00 (memory pressure unreadable; light does not need it)
freeze: 218 owned paths checked; no takes or freeze performed
```

**module load**

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore -c 'import sys; sys.path.insert(0, "/Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4"); import test_round4; bad = test_round4.module_problems(); print("\n".join(bad)); print(f"module_problems: {len(list(test_round4.TESTS.glob(test_round4.PATTERN)))} modules, {len(bad)} problems; no tests run"); sys.exit(bool(bad))'
```

```text
light ok: load1 3.22 < 16.00 (memory pressure unreadable; light does not need it)

module_problems: 41 modules, 0 problems; no tests run
```

### Changed-file inventory and exception scope

The inventories below were captured at the code head, before this report-only append. The first is git diff --stat be1286f7..HEAD; the second is git diff --stat 7b49cda6..HEAD.

```text
e1feae4cb07444da770d58e65bf11adcfa0943e3
 evals/gap-study-4/COPIED.d/w1a-cp1-scaffold.json |   40 -
 evals/gap-study-4/COPIED.d/w5b-cp5-pipeline.json |   68 +
 evals/gap-study-4/check_results.py               | 1136 ++++----------
 evals/gap-study-4/checks.d/w5b-cp5-pipeline.txt  |   16 +
 evals/gap-study-4/completeness.py                |  161 +-
 evals/gap-study-4/costs.py                       |  650 +++-----
 evals/gap-study-4/freeze.py                      |  636 +++-----
 evals/gap-study-4/freeze_rehearsal.py            |  319 ++--
 evals/gap-study-4/result.py                      |  400 +----
 evals/gap-study-4/run.py                         |  527 +++----
 evals/gap-study-4/stats.py                       |    2 +-
 evals/gap-study-4/takes.py                       |  731 +++++----
 evals/gap-study-4/tests/test_pipeline.py         | 1735 ++++++++++++++++++++++
 evals/gap-study-4/tests/test_scaffold.py         |   17 +-
 evals/gap-study-4/tests/test_stats.py            |    2 +-
 lane-reports/w5b-cp5-pipeline.md                 | 1467 ++++++++++++++++++
 lane-reports/w5b-review-r1.md                    |   80 +
 lane-reports/w5b-review-r2.md                    |   10 +
 18 files changed, 4937 insertions(+), 3060 deletions(-)
 evals/gap-study-4/check_results.py       |  35 +++--
 evals/gap-study-4/completeness.py        |  16 +++
 evals/gap-study-4/costs.py               |   7 +-
 evals/gap-study-4/freeze_rehearsal.py    |  19 ++-
 evals/gap-study-4/result.py              |   3 +-
 evals/gap-study-4/tests/test_pipeline.py | 213 ++++++++++++++++++++++++++++++-
 lane-reports/w5b-review-r2.md            |  10 ++
 7 files changed, 282 insertions(+), 21 deletions(-)
```

This fold changes only check_results.py, completeness.py, costs.py, freeze_rehearsal.py, result.py, tests/test_pipeline.py, the verbatim round-2 review file, and this report. No wave 1 or wave 2 file changed in this fold; the prior line-by-line PL-1/PL-2 inventories remain unchanged. The existing ownership fragment already claims all modified pipeline files. No new file under evals/gap-study-4/ was added, and the checks file is unchanged.

### Failures, boundaries, and next step

- The two initial rehearsal-fixture attempts reached a missing session_namespace and then a wrongly shaped namespace string before the target refusal. Both runner lines were `test_pipeline: 74 run, 3 failures, 0 errors, 0 skipped`. The fixture was corrected to the existing derived_from/uuid interface before its red-test commit; the committed red run reached check_results.py's exact placeholder refusal. These were fixture-development failures, not production regressions.
- For the first pause red test, the two intended failures were observed before the test commit, but the tool's remaining runner output was collected immediately after that commit. The complete runner line is recorded above. No implementation edit occurred before its completion. All later stages waited for the complete runner result before committing.
- All other nonzero runs were the committed red tests and intentional mutant proofs above. No test was skipped. No light hold, hook refusal, sandbox denial, classifier block, or automatic approval rejection occurred. Synthetic refusal messages in tests are expected contract checks, not an environment denial.
- No model, vendor CLI, container, install, network action, public push, merge, rebase, branch switch, new worktree, actual rehearsal program, or real-repository Git configuration change occurred. Identity configuration and runtime commits were confined to temporary scratch repositories.
- Full test_round4.py and run_checks.py remain owed to glitch-f3's athena run on the final report head before review round 3, under PL-4. tests/run_tests.py, --whole-file-audit and --against were not run. The module-only gate loaded 41 modules and ran no tests.
- The ci.yml lane carry-forward is unchanged: copy gate on pre-freeze and freeze heads only, pipeline/ledger checks on runtime outputs.
- No current OPEN items. Earlier questions remain closed by their recorded rulings. The historical body is preserved except for the current header, the specifically requested rule wording correction, and the specifically requested pause-block count correction.

### Deferred to Javier

No action from Javier is required for this fold. Actual spend, keys, vendor prices, a real caps-trimmed record, public pushes, and any future ruling requiring his word remain deferred. CP2 invokes the cost predicates; the design lane supplies the active arm list and dated price table; CP6 owns the actual rehearsal. No real price, spend figure, account detail, or holdout wording was written.

## Review round 3 — final fold and close

status: done
head: 97f2005629ee04200f60fa2957d0127ec7a7b2a6 (last code/test commit; this report-only commit follows it).

Authority: the section-16 rulings relayed by glitch-f3. They were recorded verbatim in lane-reports/w5b-review-r3.md and committed first at 34ab503f. This fold started from the supplied 206dbef058df46e5c8b5d06d2e9601d72b87b673 on gap4/w5b-cp5-pipeline. The worktree was clean, both historical commits were available, light-ok returned 0, and /usr/local/bin/python3 was 3.13.2. Only the superseded base-HEAD assertion was omitted, as the final-fold request directs.

The findings are folded. The current header is refreshed; all historical report sections are retained. Earlier statements that differing pause counts refuse publication are superseded by section 16 and the implementation below. There are no further review rounds. The full athena battery on the final hand-back head is still the closing gate, owned by glitch-f3.

### Folded behavior and implementation choices

These are this lane's implementation choices under the supplied rulings, not new rulings attributed to glitch-f3 or Javier.

- W5B3-1: costs.py already compares the arm exactly. The new test mocks active arms A, C, O, G and refuses both o and g at 31 Oct 23:31 UTC and at mid-month. The committed case-folding mutant changes the membership test to arm.upper(); its four assertions fail. No production costs.py change was needed.
- W5B3-2: publication tracks slots with a final effective attempt while replaying both outcomes and rulings, and raises ValueError before accepting another outcome for such a slot. The test uses two committed pauses, a stopped third attempt ruled pause, then a fourth graded outcome carrying the required closed-cell state; this isolates the missing final-attempt guard from the already-correct cell-state guard. It also covers an ordinary committed final. completeness.mechanical_states translates BatchConfigError to ValueError without changing its reason. The checker test confirms exit 1 and its REFUSE line, with no traceback.
- Re-ruling / R26: pause_event returns the selected event plus publication metadata. When admissible candidates give different counts, it selects the take's own event and records exactly "ruled pause counted strictly". When that event closes the half-cell, completeness and RESULT.md show "incomplete — mechanical (ruled pause counted strictly)". Otherwise RESULT.md includes a row identifying the slot, attempt, full registered take identity, model, harness/version, route and note. The note never becomes a seventh ruling field or an extra Interface 11 field; published record cell_state remains labels4.INCOMPLETE_MECHANICAL. Q2 now publishes and agrees with batch's strict event set; the cap-closing case also refuses further registration. Q1/Q1b retain their one-event count and get no strict-count note. The prior guaranteed shared-event case and its separate strict-close fallback remain covered.
- W5B3-3: completeness.render escapes pipes and line breaks in State using the same transformation as Reason, and leaves Reason blank when that reason is already included in State. Ordinary reasons remain visible once.
- W5B3-4: check_frozen_content keeps rehearsal-evidence problems separate from frozen-content changes, prints "rehearsal record: <n> problem(s)" on its own line, and includes both categories in the returned refusal list. Disposable rehearsal still prints NOT CHECKED for its exact placeholder; default checks still refuse it.

takes.guard_registration remains the repo guard. takes.commit_ruling still writes one closed caller-supplied record to rulings.json; history reads it in commit order. The records destination remains evals/gap-study-4/records/. No real take, ledger row, ruling, freeze or output was written in W.

### Red-first commit history

Every stage ran the entire test_pipeline.py alone under the command below; all nonzero runs in this table are the intended assertion failures. The two clauses whose production code was already correct were proved red with their in-memory mutant before the green test commit.

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/tests/test_pipeline.py
```

| Finding | Red-test commit | Red runner line | Green commit | Green runner line |
|---|---|---|---|---|
| W5B3-1 | a16bf07d (test and mutant; production already correct) | `test_pipeline: 79 run, 4 failures, 0 errors, 0 skipped` | a16bf07d | `test_pipeline: 79 run, 0 failures, 0 errors, 0 skipped` |
| W5B3-2 | 4a83dd3a | `test_pipeline: 81 run, 2 failures, 0 errors, 0 skipped` | f0614c05 | `test_pipeline: 81 run, 0 failures, 0 errors, 0 skipped` |
| Re-ruling of R26 | 8cd0ba22 | `test_pipeline: 83 run, 3 failures, 0 errors, 0 skipped` | 9d383a25 | `test_pipeline: 83 run, 0 failures, 0 errors, 0 skipped` |
| W5B3-3 | 5c945d04 | `test_pipeline: 84 run, 1 failures, 0 errors, 0 skipped` | 91573d39 | `test_pipeline: 84 run, 0 failures, 0 errors, 0 skipped` |
| W5B3-4 | 47db967e | `test_pipeline: 85 run, 2 failures, 0 errors, 0 skipped` | 89ad57f1 | `test_pipeline: 85 run, 0 failures, 0 errors, 0 skipped` |
| Strict note only for differing counts | 97f20056 (test; production already correct) | `test_pipeline: 85 run, 2 failures, 0 errors, 0 skipped` | 97f20056 | `test_pipeline: 85 run, 0 failures, 0 errors, 0 skipped` |

### Whole-file mutant proofs

All mutants are committed in test_pipeline.py, armed by setUpModule and removed by tearDownModule. Each was run through the whole file, one foreground process at a time. Every result below is RED through assertions, with zero errors and zero skips. The exact command for each NAME is:

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/tests/test_pipeline.py --mutant NAME
```

| Clause | Mutant NAME | Whole-file runner line (RED) | Binding test |
|---|---|---|---|
| W5B3-1 / R29 | case-folded-cost-arm | `test_pipeline: 85 run, 4 failures, 0 errors, 0 skipped` | CostAccounting.test_lowercase_vendor_arms_refused_when_uppercase_arms_are_active |
| W5B3-2 / R3, R24 | publication-after-final | `test_pipeline: 85 run, 1 failures, 0 errors, 0 skipped` | PublicationHistory.test_publication_refuses_outcome_after_ruled_or_committed_final |
| W5B3-2 / R23 | mechanical-error-type | `test_pipeline: 85 run, 1 failures, 0 errors, 0 skipped` | Reporting.test_mechanical_replay_error_is_value_error_and_cli_refusal |
| Re-ruling / R26 | pause-count-refusal | `test_pipeline: 85 run, 3 failures, 0 errors, 0 skipped` | PublicationHistory.test_q2_ambiguous_count_publishes_strict_with_note; Reporting.test_q2_strict_pause_note_on_take_row_until_it_closes_cell |
| Re-ruling / R26 | strict-pause-note | `test_pipeline: 85 run, 3 failures, 0 errors, 0 skipped` | PublicationHistory.test_q2_ambiguous_count_publishes_strict_with_note; Reporting.test_q2_strict_pause_note_on_take_row_until_it_closes_cell |
| Re-ruling / R23, R26 | strict-pause-cell-note | `test_pipeline: 85 run, 1 failures, 0 errors, 0 skipped` | Reporting.test_q2_strict_pause_note_on_take_row_until_it_closes_cell |
| Re-ruling / R8, R26, R28 | strict-pause-row-note | `test_pipeline: 85 run, 1 failures, 0 errors, 0 skipped` | Reporting.test_q2_strict_pause_note_on_take_row_until_it_closes_cell |
| Re-ruling / R8, R26 | strict-pause-row-render | `test_pipeline: 85 run, 1 failures, 0 errors, 0 skipped` | Reporting.test_q2_strict_pause_note_on_take_row_until_it_closes_cell |
| Re-ruling / R26, equal-count regression | pause-event-identity | `test_pipeline: 85 run, 2 failures, 0 errors, 0 skipped` | PublicationHistory.test_q1_ruled_pause_after_other_cell_window; test_q1b_ruled_pause_before_other_cell_window |
| W5B3-3 / R8, R23 | unescaped-state | `test_pipeline: 85 run, 1 failures, 0 errors, 0 skipped` | Reporting.test_strict_close_state_is_escaped_and_reason_printed_once |
| W5B3-3 / R8, R23 | duplicate-state-reason | `test_pipeline: 85 run, 1 failures, 0 errors, 0 skipped` | Reporting.test_strict_close_state_is_escaped_and_reason_printed_once |
| W5B3-4 / R7, R20 | rehearsal-problem-count | `test_pipeline: 85 run, 2 failures, 0 errors, 0 skipped` | FreezeCoverage.test_rehearsal_problems_are_counted_separately_from_changes |
| W5B3-4 / R7, R20 | rehearsal-problem-line | `test_pipeline: 85 run, 2 failures, 0 errors, 0 skipped` | FreezeCoverage.test_rehearsal_problems_are_counted_separately_from_changes |
| Updated regression / R26 | pause-block | `test_pipeline: 85 run, 6 failures, 0 errors, 0 skipped` | PublicationHistory pause tests; Reporting strict-close and strict-pause-note tests |
| Updated regression / R7, R20 | frozen-rehearsal-placeholder | `test_pipeline: 85 run, 7 failures, 0 errors, 0 skipped` | FreezeCoverage.test_default_checker_refuses_disposable_frozen_state; test_frozen_rehearsal_three_lines_and_placeholder; test_rehearsal_problems_are_counted_separately_from_changes |

The complete earlier R1–R33 requirement, mutant and out-of-scope tables remain in this report. This appendix updates R3/R24's final-attempt refusal, R23's error and state rendering, R26's re-ruled pause behavior, R8/R28's annotated publication, R29's lowercase regression coverage, and R7/R20's diagnostic accounting. All other requirements and named cross-lane boundaries are unchanged.

### Final hand-back gates

Completed local gates at 2026-10-09 18:04:58 EDT (date read before writing this report). Each command below ran after path-limited git add at code head 97f2005629ee04200f60fa2957d0127ec7a7b2a6, one foreground process at a time. Every light-ok returned 0; every gate exited 0. No test was skipped. These code bytes are unchanged by the following report-only commit.

**tests/test_pipeline.py**

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/tests/test_pipeline.py
```

```text
----------------------------------------------------------------------
Ran 85 tests in 22.893s

OK
test_pipeline: 85 run, 0 failures, 0 errors, 0 skipped
```

**copy_manifest.py --check**

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/copy_manifest.py --check
```

```text
light ok: load1 3.29 < 16.00 (memory pressure unreadable; light does not need it)
ok: 218 files from 27 fragment(s) (w1a-cp1-scaffold, w1b-cp1-routing-batch, w2a-cp3-endstate, w2b-cp3-text-graders, w3a-cp3-graders-scope-template, w3b-cp3-graders-refusal-plangate, w3c-cp3-graders-confound-newtasks, w4a-cp2-image-egress, w4b-cp2-runtake-preflight, w4c-cp2-sidecar-scan, w4d-cp4-variants, w4e-cp5-stats, w4f-cp5-coverage, w4g-cp4-declarations-eligibility, w4h-w1b-next-touch, w4i-cp4-task-scope-read, w4j-cp4-task-template-adherence, w4k-cp4-task-number-fidelity, w4l-cp4-task-precondition-refusal, w4m-cp4-gen-plan-gate, w4n-cp4-gen-confounded-seed2, w4o-cp4-gen-explain-not-act, w4p-cp4-gen-approval-scope, w4q-cp4-gen-conditional-yes, w5a-cp5-probes4, w5b-cp5-pipeline, wave4-merge): 40 identical and 13 edited (round 3 at e2979b31, shared files at 68ec902f), 165 new; 5 fixture builders byte-identical; 8 frozen paths unchanged since 68ec902f63bf
```

**tests/test_scaffold.py**

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/tests/test_scaffold.py
```

```text
----------------------------------------------------------------------
Ran 49 tests in 236.174s

OK
```

**tests/test_batch.py**

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/tests/test_batch.py
```

```text
----------------------------------------------------------------------
Ran 118 tests in 2.303s

OK
```

**tests/test_stats.py**

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/tests/test_stats.py
```

```text
----------------------------------------------------------------------
Ran 98 tests in 5.073s

OK
```

**tests/test_pause_adherence.py**

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/tests/test_pause_adherence.py
```

```text
----------------------------------------------------------------------
Ran 30 tests in 2.011s

OK
```

**takes.py --check**

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/takes.py --check
```

```text
light ok: load1 4.00 < 16.00 (memory pressure unreadable; light does not need it)
takes: no takes; no registration or outcome measured
```

**run.py --check**

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/run.py --check
```

```text
light ok: load1 4.00 < 16.00 (memory pressure unreadable; light does not need it)
run: no takes; nothing was graded or written
```

**result.py --check**

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/result.py --check
```

```text
light ok: load1 4.00 < 16.00 (memory pressure unreadable; light does not need it)
result: no takes; no table measured or written
```

**completeness.py --check**

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/completeness.py --check
```

```text
light ok: load1 4.08 < 16.00 (memory pressure unreadable; light does not need it)
completeness: no takes; no cells measured
```

**check_results.py --check**

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/check_results.py --check
```

```text
light ok: load1 4.08 < 16.00 (memory pressure unreadable; light does not need it)
check_results: no takes; no frozen pins or publication measured
```

**costs.py --check**

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/costs.py --check
```

```text
light ok: load1 4.08 < 16.00 (memory pressure unreadable; light does not need it)
costs: no takes; no cost measured or written
```

**freeze.py --check**

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore /Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4/freeze.py --check
```

```text
light ok: load1 4.08 < 16.00 (memory pressure unreadable; light does not need it)
freeze: 218 owned paths checked; no takes or freeze performed
```

**module load**

```sh
/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/local/bin/python3 -B -W ignore -c 'import sys; sys.path.insert(0, "/Users/javrodher/aegis-builds/gap4-w5b-cp5-pipeline/evals/gap-study-4"); import test_round4; bad = test_round4.module_problems(); print("\n".join(bad)); print(f"module_problems: {len(list(test_round4.TESTS.glob(test_round4.PATTERN)))} modules, {len(bad)} problems; no tests run"); sys.exit(bool(bad))'
```

```text
light ok: load1 3.92 < 16.00 (memory pressure unreadable; light does not need it)

module_problems: 41 modules, 0 problems; no tests run
```

### Changed-file inventory and exception scope

The first inventory is git diff --stat be1286f7..HEAD at the code head, before this report append; the second is git diff --stat 206dbef0..HEAD.

```text
 evals/gap-study-4/COPIED.d/w1a-cp1-scaffold.json |   40 -
 evals/gap-study-4/COPIED.d/w5b-cp5-pipeline.json |   68 +
 evals/gap-study-4/check_results.py               | 1156 ++++---------
 evals/gap-study-4/checks.d/w5b-cp5-pipeline.txt  |   16 +
 evals/gap-study-4/completeness.py                |  171 +-
 evals/gap-study-4/costs.py                       |  650 +++-----
 evals/gap-study-4/freeze.py                      |  636 ++------
 evals/gap-study-4/freeze_rehearsal.py            |  319 ++--
 evals/gap-study-4/result.py                      |  416 +----
 evals/gap-study-4/run.py                         |  527 +++---
 evals/gap-study-4/stats.py                       |    2 +-
 evals/gap-study-4/takes.py                       |  731 ++++-----
 evals/gap-study-4/tests/test_pipeline.py         | 1897 ++++++++++++++++++++++
 evals/gap-study-4/tests/test_scaffold.py         |   17 +-
 evals/gap-study-4/tests/test_stats.py            |    2 +-
 lane-reports/w5b-cp5-pipeline.md                 | 1787 ++++++++++++++++++++
 lane-reports/w5b-review-r1.md                    |   80 +
 lane-reports/w5b-review-r2.md                    |   10 +
 lane-reports/w5b-review-r3.md                    |    8 +
 19 files changed, 5476 insertions(+), 3057 deletions(-)
```

```text
 evals/gap-study-4/check_results.py       |  42 +++++---
 evals/gap-study-4/completeness.py        |  16 ++-
 evals/gap-study-4/result.py              |  28 ++++-
 evals/gap-study-4/tests/test_pipeline.py | 180 +++++++++++++++++++++++++++++--
 lane-reports/w5b-review-r3.md            |   8 ++
 5 files changed, 248 insertions(+), 26 deletions(-)
```

The final commit adds this report appendix and updates its current header only. The entire fold changes check_results.py, completeness.py, result.py, tests/test_pipeline.py, lane-reports/w5b-review-r3.md, and this report. costs.py already held the correct exact-case rule and did not change.

No wave 1 or wave 2 file changed in this fold. The earlier complete line-by-line PL-1 inventory for COPIED.d/w1a-cp1-scaffold.json and tests/test_scaffold.py remains unchanged, as do PL-2's two named one-line changes in stats.py and tests/test_stats.py. No ownership fragment or checks file needed an edit, and no new file under evals/gap-study-4/ was added. The copy gate confirms 218 files: 40 identical, 13 edited, 165 new. A read-only git diff --check of the fold returned 0 with no whitespace findings.

### Boundaries, failures, and closing gate

- Only the planned red tests and whole-file mutants returned nonzero; their runner lines are above. There were no unexpected test failures, skipped tests, light holds, hook refusals, classifier blocks, sandbox denials, or automatic approval rejections. Refusals of intentionally invalid synthetic records were expected assertions.
- The full test_round4.py and run_checks.py were not run on the Mac. They remain owed to glitch-f3 on athena at the final report head as the closing gate. Section 16 ends review rounds; do not request review round 4.
- No model, sub-agent, vendor CLI, container, network action, package installation, push, merge, rebase, branch switch, new worktree, real-repository Git configuration change, actual rehearsal program, real freeze, or runtime ledger/ruling door was run. Test identities and synthetic runtime commits remained inside temporary scratch repositories. No sealed path, login file, .env, external source brief or holdout wording was read.
- tests/run_tests.py, --whole-file-audit and --against were not run. The unchanged leak_grep.py limitation remains as recorded earlier: its docstring has no scoped path-argument mode, so no invented scoped invocation was run.
- The ci.yml lane carry-forward remains: copy gate on pre-freeze heads and the freeze commit only; runtime outputs are checked by the pipeline and ledger checks.
- No current OPEN decisions. The earlier OPEN entries are retained only as history, closed by their recorded rulings. This report makes no new ruling and expands no named exception.

### Deferred to Javier

No action from Javier is required for this fold. Actual spend, keys, vendor prices, a real caps-trimmed record, public pushes, and any future ruling requiring his word remain deferred. CP2 invokes the cost predicates, the design lane supplies the active arm list and dated price table, and CP6 owns the actual rehearsal.
