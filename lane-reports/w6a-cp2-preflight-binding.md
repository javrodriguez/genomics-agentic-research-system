status: review passed; athena owed
RESUME HERE: hand-back at 9f176f29 (code head after the review round 1 fold; W6A-close-1: round 1 PASS, loop closed). Next: athena run_checks on the exact head; status becomes done only after it passes.

head: 27c2391a (last code/test commit; this report's own commit follows it). Base 89b54db4 (gap4/cp5-pipeline-merge), branch gap4/w6a-cp2-preflight-binding, worktree /Users/javrodher/aegis-builds/gap4-w6a.

# Lane w6a-cp2-preflight-binding: CP2 preflight lock loading and evidence identity

_Gap Study round 4, slice S1 of next-slices-2026-10-11. Written Sun 11 Oct 2026 16:42 EDT (`date`) by the slice's sole writer (Claude Opus 5.5 sub-agent), assigned by glitch-1b under Javier's standing delegation._

No image or container was built or run.
No model was run.
No network was used by any test.
No login, `.env`, sealed, holdout, brief, grader-source or saved-output path was read.
Nothing was pushed or merged.

## Scope (CP2-preflight-1 to -5, glitch-1b's rulings of 10 Oct 16:05 EDT)

The bounded seam only: the take lock reaches preflight through w4a's loader, evaluate binds the evidence folder, and one composition entry point runs the probes on `Launched.spec`.
The whole drive lifecycle (launch, cleanup on every refusal, restart, commit and re-stage) is not in this slice; it stays S5 and S6.

## Commits

| commit | what |
|---|---|
| f8802bf4 | checkpoint, red: the eight criteria, two breaks and six witnesses first; existing World calls pass the required evidence_dir |
| 27c2391a | the fix in box/preflight.py; binding 4 and 8 extensions; the copy-record reasons; the named audit-allowlist departure (OPEN w6a-1) |
| (this commit) | this report |

## What changed

`box/preflight.py`:
- `TAKE_IMAGE = {claude-code: take-a, codex: take-o, gemini: take-g}`.
- `load_take_lock(lock_path, *, harness)`: `image_lock.load`, then the lock's `image` must be the harness's take image (else `run_take.Refused`), then `image_lock.require_ready`, then exactly `LOCK_KEYS` projected with `run_take._path_get`. It takes a normalised absolute path only (`run_take._abs_path`), so a dictionary or a relative path refuses.
- `evaluate(raw, *, spec, lock, sidecar_expect, harness, hosts, evidence_dir)`: `evidence_dir` is required, with no default, and checked by the probes' own lexical rule (`run_take._abs_path`; no realpath). Every check now receives it as a seventh argument.
- `sidecar-isolated` adds `_evidence_source_problems`: the expectation's read-write `/srv/ev` mount must have `evidence_dir` as its source. The existing inspect equality then binds the actual mount to it too.
- `evidence-out-of-reach` adds: the listing probe must have tried `evidence_dir`. This binds the probes' folder to the judged one inside the pure evaluator.
- `collect_and_evaluate(runtime, *, launched, sidecar, lock_path, harness, hosts, evidence_dir, begin_reply, caller_env=None)`: lock first, then `evidence_dir`, then `_launched_parts(launched)`. That requires `ok is True`, a non-null `spec` passing `check_spec`, full 64-hex take and sidecar ids, and `spec.network == launched.network_id`. Then `probes`, `run` and `evaluate`, all with the same `evidence_dir` and `sidecar.expect`. Every lock or launch-record refusal raises before the runtime is called. It never launches, runs a turn, reads a login, writes a record or tears down.
- Unchanged: `PREFLIGHT_CHECKS` (18, same order), `LOCK_KEYS`, every PENDING constant and refusal, `run`, `probes`, `write`, `postflight`.

`tests/test_preflight.py`: World passes `evidence_dir=self.ev`, and `test_run_tree_path_neutral` passes it too. `filled()` takes an optional module. Two breaks were added (`sidecar-isolated/both-ev-source-elsewhere`, `evidence-out-of-reach/other-folder`). There are 21 new tests (below).

`tests/test_wave4_bindings.py`: binding 4 passes `evidence_dir` and adds the parsed evidence source to the judged folder. Binding 8 adds `loader()`: `pf.image_lock is il`, TAKE_IMAGE pairs every harness with its own package, every committed take lock reaches `require_ready` (NotReady), and a filled copy in a temporary box folder projects exactly the schema paths and is accepted by evaluate's lock contract. There is a new `test_binding_8_loader` with two mutants and a `TestNothingDropped`.

COPIED.d (CP2-preflight-5): the three transferred entries (`box/preflight.py` and `tests/test_preflight.py` in w4b's fragment, `tests/test_wave4_bindings.py` in wave4-merge's) stay in place, one owner each. Their reasons now name lane w6a as owner since 11 Oct and say what it added. There is no new fragment, no duplicate path and no regeneration. `copy_manifest.py --check`: ok, 218 files, 27 fragments.

## Criteria, tests and witnesses

Every witness is a whole-file mutant of box/preflight.py: one exact anchor edit, compiled in memory as its own module, never written to disk.
A kill counts only when the bound check is green on the real module first and then returns at least one line with its own prefix and no ERROR line. A raised exception, a missing anchor or a skip is never a kill. Collateral lines are listed, not credited.

| # | criterion | test (tests/test_preflight.py unless named) | witness: kill line |
|---|---|---|---|
| 1 | loader really used | TestLockSeam.test_c1_loader_really_used (spies on il.load and require_ready, all three harnesses, five values reach evaluate); test_c1_no_flattened_lock | omit-load: `red by C1-loader-spy (3 own, 3 collateral, 0 errors)` |
| 2 | closed validation survives | test_c2_closed_validation_survives (missing key, unknown key, wrong package, wrong image, duplicate key, wrong neighbouring Dockerfile, malformed JSON); test_c2_pending_refused_before_the_runtime (base, harness.version, python, image_id). Zero runtime calls and no evaluation in each | omit-readiness: `red by C2-pending (4 own, 0 collateral, 0 errors)` |
| 3 | harness/image binding | test_c3_harness_image_binding (take-o for claude-code, take-a for codex, take-o for gemini refuse; the three intended pairs pass); test_c3_no_sidecar_or_egress_lock_for_a_take; binding 8 loader | omit-harness-image-binding: `red by C3-cross (3 own, 0 collateral, 0 errors)` |
| 4 | evidence identity | test_c4_evidence_identity (A healthy; mount at B in both, expectation only, or inspect only: sidecar-isolated fails, ok false; probes at A judged as B fails evidence-out-of-reach); test_c4_evidence_dir_required (None, empty, relative, dotted, root refuse; omitted is a TypeError) | drop-mount-source-comparison: `red by C4-mount (1 own, 0 collateral, 0 errors)` |
| 5 | positive composition | test_c5_positive_composition (all three arms; spies show A reaching probes, the health read and evaluate, and evaluate gets the sidecar's own expectation object; every check green) | probes-at-another-evidence-path: `red by C5-probes-path (3 own, 6 collateral, 0 errors)` |
| 6 | Launched.spec | test_c6_launched_spec (the probed and evaluated network is the launched one, not the placeholder `e`*64; no launch, run_turn, teardown or kill_agent reached); test_c6_incomplete_launch_record (no spec, no take id, no sidecar id, not ok, spec off its network, short id, a dict: Refused, zero runtime calls, no probe built); test_the_composition_names_no_lifecycle_or_adapter (ast) | pre-launch-spec: `red by C6-launched-spec (2 own, 0 collateral, 0 errors)` |
| 7 | no old check disappears | TestNothingDropped (all 20 base test ids still load, no skip or expected-failure flag; BREAKS keeps every base break per check, 18 checks in order); test_wave4_bindings TestNothingDropped (all 10 base ids); bindings 1-7 untouched except binding 4's added argument and assertion | n/a |
| 8 | six witnesses | TestWitnesses (six methods, plus a test that names exactly six with six distinct bound checks) | all six above |

## Red, then green (Mac, `mac_slot.py light-ok &&`, `env -u CONDA_PREFIX -u CONDA_DEFAULT_ENV`, Python 3.13.2, `-B -W ignore`)

Base 89b54db4: test_preflight `Ran 20 ... OK` rc 0; test_wave4_bindings `Ran 10 ... OK` rc 0.

Seam on the unmodified candidate, demonstrated with a scratch script over the World (scratchpad `w6a/seam_demo.py`):
- `seam evidence: mounts at B, probes at A -> ok []`: the base evaluator passed.
- `evaluate() got an unexpected keyword argument 'evidence_dir'`.
- A loaded nested lock was refused by evaluate's flat-key check.
- No `load_take_lock` or `collect_and_evaluate` existed.

Red checkpoint f8802bf4 on the unmodified preflight: test_preflight `Ran 41`, `FAILED (failures=23, errors=4)`, rc 1; test_wave4_bindings `Ran 12`, `FAILED (errors=3)`, rc 1.

Green at 27c2391a, the lane sweep (checks.d w4b and wave4-merge lines, each rc 0):
- test_run_take `Ran 43 ... OK`
- test_preflight `Ran 41 ... OK`
- test_take_config `Ran 9 ... OK`
- test_run_take `--process-audit`: `30 planted positives caught, 3 modules and 3 test files read, 0 problem(s)`
- test_wave4_bindings `Ran 12 ... OK`: 12 mutants red, the three binding-8 ones included
- also: `copy_manifest.py --check` ok; test_image `Ran 41 ... OK`; test_scaffold `Ran 49 ... OK` (460 s).

Not run on the Mac: test_round4 (the battery), run_checks.py and any whole suite. Those are athena's, on the exact head.

## Departures

- RULED: w6a-1 (glitch-1b, 11 Oct: (a) ratify; the ownership sentence is in w4b's fragment entry for tests/test_run_take.py). Interface 10's default-deny audit in `tests/test_run_take.py` (w4b's file, outside this slice's list) refuses `from box import image_lock` in preflight. Its allowlists are derived from the box modules' source and bound both ways. CP2-preflight-2 requires preflight to invoke `image_lock.load` and `require_ready` itself. So 27c2391a adds exactly `("box", "image_lock")` to `IMPORT_FROM_ALLOWED` and `"image_lock": {"load", "require_ready"}` to `MODULE_ATTRS`, with a comment naming this departure. No os, subprocess, dunder, getattr or dynamic-builtin list changed. image_lock imports only fnmatch, json, os, re, dataclasses, harness_bookkeeping and box.egress.proxy_conf (os and re only), and no process module. Without the edit, the audit prints 3 problems and TestAuditAllowlists fails. The alternative is to inject the loader as a parameter, which keeps test_run_take untouched but moves "the real loader is used" to the caller, against the ruled interface. glitch-1b decides: (a) ratify the edit and record the ownership note in w4b's fragment entry for tests/test_run_take.py, or (b) refuse it, and this lane redesigns. Recommended: (a).
- Two checks are stricter, as additions, not removals: `sidecar-isolated` (the evidence source) and `evidence-out-of-reach` (the listing must have tried evidence_dir).

## Limitations (CP2-preflight-4)

- Lock and launch-record refusals raise typed exceptions (`image_lock.LockError`, `image_lock.NotReady`, `run_take.Refused`, and `ValueError` for malformed JSON) before any runtime call. The future drive step must record these as a pre-turn refusal and clean up through its own finally path. This slice does not prove full lifecycle cleanup.
- The witnesses are compiled in memory. A whole-file swap on disk, for athena, is the same anchor edit applied to a copy of box/preflight.py.
- The sidecar reply's unreadable-path validation was already present (`sidecar.parse_reply`). The caller-side integration assertion stays with S5 or S6.
- Bare adapter versions and the retry-after signal were not touched, as the readiness note says.

## Writer release

The sole writer releases the worktree at the report commit. The tree is clean and no `__pycache__` is left (`-B` throughout). Scratch outputs are in the session scratchpad under `w6a/`, outside the repository.

## Fold of review round 1 (W6A-close-1, glitch-1b, 11 Oct)

Round 1 passed; the loop is closed. Folded at 9f176f29:
- W6A-R1-1: `test_c1_relative_path_to_a_valid_lock_refused` (C1-relative) gives a relative path to a VALID, ready take lock and requires run_take.Refused with no load and no runtime call. Witness `omit-absolute-path-rule` (preflight's `_abs_path` line deleted): `red by C1-relative (1 own, 0 collateral, 0 errors)`. Seven witnesses now, each bound to its own check.
- W6A-R1-2 (ruling: the new audit entries are w6a's under w6a-1): `tests/test_run_take.py` adds `reach_audit`. It ast-parses box/image_lock.py and box/egress/proxy_conf.py, and requires imports within REACH_IMPORTS (`__future__, fnmatch, json, os, re, dataclasses, harness_bookkeeping, box.egress`), bound both ways, with no subprocess and no FORBIDDEN_OS name. It has four planted positives, and `TestReachAudit` has five mutants, all red. `--process-audit` runs it. The ownership is recorded in w4b's COPIED.d entry for that file.
- W6A-R1-3: the allowlist comment names ruling w6a-1 as ratified.

Gates at 9f176f29 (Mac, light-ok, Python 3.13), all rc 0:
- test_run_take `Ran 44 ... OK`
- test_preflight `Ran 43 ... OK`
- test_take_config `Ran 9 ... OK`
- `--process-audit`: `30 planted positives caught, 3 modules and 3 test files read, 4 reach positives caught and 2 reached modules read, 0 problem(s)`
- test_wave4_bindings `Ran 12 ... OK`
- `copy_manifest.py --check` ok

Owed: athena run_checks (and the battery) on the exact head.
