VERDICT: PASS

# Review of lane vendor-b11, range c581ccdf..2b609ff9 (round 5: rulings R5-1 to R5-4)

Fresh cloud reviewer, Mon 19 Oct 2026. I did not write this change. I read the review of rounds 3 and 4
(lane-reports/REVIEW-vendor-b11-07312e4.md), the round 5 Progress lines of lane-reports/vendor-b11-LANE.md, and the
whole diff of the range (7 files: box/run_take.py, box/take_config.py, tests/test_config_folder.py,
tests/test_take_config.py, COPIED.d/vendor-admission.json, the plan's section 6 table, the lane file). No code or test
was changed by this review. I ran no walk, take, login, container or vendor call, ran no Gemini CLI, Codex or Claude
Code, and opened no login, token, lease or account file. R4-3's two held skill digests are held on purpose and are not
a finding. R5-5 (the integration merge) is not in this range; the lane file's blocked status for it is not a finding.

There are no MAJOR and no MINOR findings. All four findings of the first review are closed with the check each named.

## Findings

1. NIT. evals/gap-study-4/tests/test_config_folder.py line 855 (C13Guards.test_an_entry_on_another_device_refuses)
   varies `dev` only on file entries (config.toml, .gemini/settings.json, installation_id, .gemini/projects.json).
   - My mutant 2 narrowed the device check at box/run_take.py line 2521 to skip directories
     (`if e["dev"] != root["dev"] and e["kind"] != "dir":`). It survived every module of the ruled list (see Checks).
   - The guard itself is witnessed (device-unchecked is red), so R5-1 holds as ruled. But a mount point inside the
     config folder is a directory, and no test pins that a directory entry on another device refuses.
   - Missing check: one more case in that test with a directory entry (for example `.gemini` before turn 1, or
     `tmp` after a codex turn 1) on another device, which must refuse naming "another device".

2. NIT. Commit 676b10e5 (the round's first commit, status running) carries a session link in its message, against
   the lane's commit-message rule. The executor named it at lane-reports/vendor-b11-LANE.md line 128 and did not amend
   it (append-only, which is right). No other commit message in the range carries a link, a home path or a backtick.
   Nothing in the tree is affected; this is recorded so the count is complete.

## Threat model

### (1) The first review's four findings

- Finding 1 (MINOR, untested guards): closed.
  - Nine witnesses are registered in tests/test_config_folder.py `mutants()`/`METHOD`: device-unchecked,
    lease-record-unbound, lease-path-unbound, lease-uid-map-unbound, record-harness-unbound, record-tree-unbound,
    placed-kind-unchecked, placed-links-unchecked, absent-unnamed. Each old text occurs once in box/run_take.py
    (lines 2521, 2530, 2533, 2580, 2610, 2612-2614).
  - Each is bound to a C13Guards test (lines 845-943) and is red alone (run individually by me, below).
  - Red first is real: at 319dac37 (registry only) each of the nine mutants leaves the then 19 tests OK, so no older
    test killed any of them; the witness run there fails because C13Guards does not yet exist.
  - Note, not a finding: placed-kind-unchecked, placed-links-unchecked and absent-unnamed are red by the refusal's
    wording. With each guard off, the check still refuses (a read refusal, or "not byte-identical"), so the check
    stays closed and the test pins that the named rule is the one that fires. That is the right binding.
- Finding 2 (MINOR, R4-2 unnamed in section 6): closed. Row "B11 R4-2" at
  lane-reports/PLAN-codex2-signin-road-2026-10-18.md line 271. See (4).
- Finding 3 (NIT, stale routing prose): closed. box/run_take.py lines 2200-2201 and 2434-2435 now name R4-1's
  routing (before turn 1 a rehearsal; after it DriveRefused, recorded failed with drive_started true). Those are
  comment-only hunks; no code line of run_take.py moved.
- Finding 4 (NIT, config_sha256 admits arg0 links for every harness): closed. See (3).

### (2) Does any new test or witness pass without its guard

- `--witnesses`: 36 of 36 red, registry 36.
- I ran each of the nine new mutants alone with `--mutant NAME`. Each fails exactly its bound C13Guards test by an
  AssertionError carrying its clause, and the other 24 tests stay OK.
- TestArg0LinksCodexOnly (tests/test_take_config.py lines 672-700) is red first at 5fb85434 (that commit adds only the
  test). Its own mutant every-harness is red at the head.
- My mutant 1 (take_config.config_sha256's non-codex branch reduced to `if not os.path.isfile(path):`, so a link to
  a file is followed and hashed) is killed by TestHashAndNames.test_hash.
- My mutant 2 (the device check skips directories) survived; that is finding 1.

### (3) R5-4

- box/take_config.py lines 341-367: with harness other than codex, or no harness named, the function is the
  pre-R-H3 body (take_config.py at 936cf29f^, lines 322-338) statement for statement. Directory links refuse with
  "a link in the config folder"; any file link or special file refuses with "a link or a special file in the config
  folder". The hash input for plain files is unchanged.
- Only `harness == CODEX` reaches the arg0 branch, and that branch still admits only `codex_arg0_link(rel, target)`,
  run_take's one rule, so only R-H3's four names at their one shape and target.
- The only caller is `take_config.write` (line 319), now passing its own harness on a fresh folder with no links. So
  no recorded hash can move. `build_draft.py --check` reports the committed draft is what it builds.
- Edits to older tests in test_take_config are mechanical: two mutant lambdas take the new optional parameter, and
  TestArg0Links names `tc.CODEX` where it hashes a codex folder. No assertion was dropped or loosened.

### (4) The R4-2 row

- It is true to box/preflight.py:
  - lines 379-431 hold `VERSION_PROBE_ROOT`, `VERSION_PROBE_HOMES`, `VERSION_PROBE_PROGRAM` and `_version_argv`;
  - line 431 is the claude-code branch, with its config home from `_config_home_values`.
- Its test citations match the head:
  - test_config_folder: `version_probe_problems` starts at line 776, and C12VersionProbe runs from line 819 to 841
    with four mutants on both arms.
  - test_preflight: `World()` defaults to claude-code (line 182), and the loop over `w = World()` (line 1136) pins
    `CLAUDE_CONFIG_DIR=/opt/cfg` alone at lines 1152-1155. The O and G pin is at lines 1166-1175, and the three named
    mutants are at lines 1182-1184.
- The arg0 source lines it cites agree with lane-reports/B11-DESIGN-NOTE.md's table (arg0/src/lib.rs 355-401).
- B11's differences between the arms are named by rows R-H5, R-CF, R4-4 and now R4-2. Round 5 adds none:
  - R5-4 only narrows a hash rule that has no effect on a fresh folder.
  - R5-1 and R5-3 are tests and comments.
  - I found no unnamed difference.

### (5) Scope

- No file beyond the four rulings moved, apart from the lane file and COPIED.d/vendor-admission.json. The latter
  changes only the reason text of tests/test_config_folder.py's entry, to name C13.
- box/settings_guard.py, box/sidecar.py, box/preflight.py, drive.py, check_take.py and prereg-draft.json are
  untouched.
- `check_vendor_sources.py EB drive.py` exits 0.
- No earlier test, witness or guard was removed or weakened: the registry grew from 27 to 36, test_config_folder from
  19 to 25 tests, and test_take_config from 12 to 13.

## Checks run

- Head 2b609ff9.
- Every check ran in the foreground under `env -i` with only PATH, HOME, LANG and TMPDIR set. HOME and TMPDIR were in
  the session scratch directory, outside the clone.

| check | result |
|---|---|
| test_config_folder | 25 OK |
| test_config_folder --witnesses | 36 of 36 red |
| test_config_folder --mutant, each of the nine new names | each FAILED (1, its bound C13Guards test) |
| test_take_config | 13 OK |
| test_run_take | 68 OK |
| test_env_allowlist | 37 OK |
| test_drive_ownership | 48 OK |
| test_box_integration | 61 OK |
| test_pending_walk | 23 OK |
| test_walk_builders | 94 OK |
| test_harness_bookkeeping | 23 OK |
| test_preflight | 59 run, 1 failure: TestLeasePostflight.test_the_lease_admits_exactly_its_one_credential, the known red also present at 52619ab1, not this range's |
| test_codex_adapter | 56 OK |
| test_gemini_adapter | 144 OK |
| test_vendor_pins | 5 OK |
| build_draft.py --check | rc 0, "the committed draft is what build_draft.py builds" |
| check_vendor_sources.py EB drive.py (edit D) | rc 0 |
| red-first, 5fb85434: test_take_config | 13 run, FAILED (1: TestArg0LinksCodexOnly) |
| red-first, 319dac37: the nine mutants against the 19 older tests | all OK (survive), as the commit says |

Two mutants of my own were each run on a fresh local clone in a mktemp directory outside this clone, left in place:

- Mutant 1, box/take_config.py line 360: `if os.path.islink(path) or not os.path.isfile(path):` became
  `if not os.path.isfile(path):`. Killed: test_take_config FAILED (TestHashAndNames.test_hash). test_run_take (68)
  and test_config_folder (25) stayed OK.
- Mutant 2, box/run_take.py line 2521: `if e["dev"] != root["dev"]:` became
  `if e["dev"] != root["dev"] and e["kind"] != "dir":`. Survived: test_config_folder 25, test_run_take 68,
  test_take_config 13, test_env_allowlist 37, test_drive_ownership 48, test_box_integration 61, test_pending_walk 23,
  test_codex_adapter 56 and test_gemini_adapter 144 were all OK. This is finding 1.

`gitleaks git --staged` was run before this commit.
