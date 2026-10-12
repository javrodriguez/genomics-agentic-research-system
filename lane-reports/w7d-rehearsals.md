status: stopped

# Lane w7d-rehearsals: Gap Study round 4 wave 7 piece P3 (the rehearsal register)

Written Mon 12 Oct 2026, 00:25 EDT (`date`), by the lane's sole writer (Claude Opus 5.5), assigned by glitch-1b under Javier's standing delegation.
Branch `gap4/w7d-rehearsals`, base `82cf6ae9` (the wave 7 merge head).
Code commit `567ebfa2`.
Nothing was pushed, merged or dispatched, and no walk, model, network, Docker, credential or holdout was used.

## What closed

- `rehearsals/README.md` (plan CP6, line 870): what a walk is (874-878, 884, 1186, quoted), that a walk is never a data take (`counted: false`), the routing table's other meaning of "rehearsal" (193, 185) kept apart, where walk records live (299, 862, 708), how a walk is registered, six open questions.
- The walk register: `rehearsals/register.json` (`{"schema": 1, "walks": []}`) and `walk_register.py --check`.
  Entry fields exactly walk, task, half, wording, arm, model, reason, counted; task, wording and arm/model read against `prereg-draft.json` (arm C's optional model admitted), half against `tasks/<task>.json`; counted exactly false; reason non-empty; walk one path segment, used once.
  Binding both ways: every folder under `rehearsals/` registered, every registered walk has its folder holding a file; any other top-level file fails.
  Empty: exit 0 with `ok, having registered 0 walks: ...`; a missing register fails.
- `review_kit/rounds.py`: the five usage lines now name `evals/gap-study-4/review_kit/rounds.py`; no other line changed (its paths already come from study.py).

## Ownership (ruling W7D-gap4-1)

- New fragment `COPIED.d/w7d-rehearsals.json`: review_kit/rounds.py (edited, transferred from w1a-cp1-scaffold; the transfer named in w1a's self-entry), walk_register.py, rehearsals/README.md, rehearsals/register.json, tests/test_rehearsals.py, checks.d/w7d-rehearsals.txt, the fragment itself.
- Departure w7d-1 (for glitch-1b to ratify; recorded in w1a's tests/test_scaffold.py entry): `TheManifest.test_a_copy_that_differs_without_an_edited_entry_is_refused` named rounds.py as a w1a identical copy; `review_kit/launch.py` stands in, the shape of w6e-1 and w6h-1.
  Before the swap that single test failed by assertion (exit 1); after it, OK (exit 0).
- `checks.d/w7d-rehearsals.txt`: test_rehearsals.py, its --witnesses, walk_register.py --check, review_kit/rounds.py --check.

## Evidence (Mac, `mac_slot.py light-ok` and `timeout -s INT 120` in each command, Python 3.13.2, `env -u CONDA_PREFIX -u CONDA_DEFAULT_ENV`)

- Red first, by assertion only, against a stub walk_register.py and the unedited rounds.py: test_rehearsals 5 run, 17 failures (subtests), 0 errors, exit 1.
- Green: test_rehearsals 5 run, 0 failures, 0 errors, exit 0.
  Clauses: R1.unregistered, R2.folder, R3.malformed (twelve malformed entries plus duplicate id, schema, top-level key, non-JSON), R4.empty (also the committed register), U1.usage.
- Witnesses (rule B): 9 of 9 RED, each by its bound method's AssertionError carrying its clause, collateral none: unregistered-admitted, stray-file-admitted, missing-folder-admitted, empty-folder-admitted, fields-unchecked, counted-admitted, design-unchecked, silent-empty, round3-usage.
- `walk_register.py --check` exit 0 (0 walks line), `review_kit/rounds.py --check` exit 0 (0 rounds), `copy_manifest.py --check` exit 0 (267 files, 40 fragments, 34 identical, 19 edited, 214 new), `freeze.py --check` exit 0 (267 owned paths), `lint_language.py` on the README and register clean, exit 0; all re-run after the commit.
- Not run on the Mac: whole test_scaffold, test_pipeline, run_checks, test_round4.

## Open questions for glitch-1b

- Q-w7d-1: no road writes `rehearsals/<walk>/`. The copied round 3 walk path writes `walks/<task>/<n>/` (drive.py --walk, read by mode_binding --walks, fixture_walk, build_cases), round 3's routing section of drive.py writes take rehearsals to `rehearsals/<task>/<half>/<model>/row-<n>`, and walk_driver writes `takes/<slot>/<k>`. Any of them writing here now fails the register check as unregistered; the walk road needs a slice before the first walk.
- Q-w7d-2: what a walk folder must hold, and where its grader output lives (plan 878); the register checks only a non-empty folder.
- Q-w7d-3: coverage (every wording on Haiku, each task and half per model) is unchecked; plan 874-877's "about 170" is stale (readiness section 5 item 1).
- Q-w7d-4: copy_manifest.py refuses any unclaimed file under the study folder, so committed walk records need a claim rule (or an exemption) before the first walk.
- Q-w7d-5: neither freeze_rehearsal.py's COMMANDS nor the CP6 VALIDATE line nor the CI job runs `walk_register.py --check`; wiring belongs to those owners.
- Q-w7d-6: rounds.py's usage omits `--close-spent` (round 3's carry); left as is, path-only scope.

## Appendix: fold W7D-close-1 (review round 1: no MAJOR, 4 MINOR, 2 NIT; departure w7d-1 ratified)

Written Mon 12 Oct 2026, 00:33 EDT (`date`), by the same writer, on glitch-1b's ruling W7D-close-1 (table `plans/gap-study-round-4/w7d-review-r1-2026-10-12.md` in the Brain).
Base `4b3f9cdd`; fold code commit `8fa9f8ef`.

- R1-1: registered walks are matched against the exact names `iterdir()` lists, so a case-blind path lookup no longer passes; ids that differ only by case (`casefold`) are refused. Clause R5.case.
- R1-2: `has_a_file` counts only a regular file that is not a symlink, and a symlinked `register.json` is refused. Clause R6.symlink.
- R1-3: the register is loaded with an `object_pairs_hook` that refuses duplicate keys at any level. Clause R7.dupkey.
- R1-4: R6.symlink tests a walk folder that is a symlink. Witnesses now cover the symlink, duplicate-id and walk-id guards.
- R1-5: the README calls line 1186 "the plan's review fold-in list".
- R1-6: an unreadable register (or folder) prints a FAIL line and exits 1; `type(schema) is int`; the reason is stripped of Unicode whitespace and format characters before the non-empty check. Clause R8.nits.

Evidence (same Mac conditions):
- Reviewer's attack.py on the old code: case-dup, symlink-file-in-walk, register-symlink, dup-key-counted, schema-true and schema-1.0 passed wrongly, reason-ws-only-nbsp (U+200B) passed wrongly, and unreadable raised PermissionError.
  On 8fa9f8ef each of these FAILs (unreadable now returns a "cannot be read" problem); baseline and gitkeep-only still pass.
- Red first: test_rehearsals 9 run, 4 failures (R5-R8), 0 errors, exit 1. Green: 9 run, 0 failures, exit 0.
- Witnesses: 20 of 20 RED by their bound clauses (11 new). Collateral, listed but not counted: empty-folder-admitted, missing-folder-admitted and unregistered-admitted also fail a TheRegisterFold method.
- walk_register --check (0 walks), rounds.py --check, copy_manifest --check (267 files, 40 fragments), freeze --check and lint_language on the README all exit 0.

RESUME HERE: hand-back at 8fa9f8ef
