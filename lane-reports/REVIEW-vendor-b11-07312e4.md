VERDICT: CHANGES

# Review of lane vendor-b11, range 52619ab1..07312e4f (rounds 3 and 4)

Fresh cloud reviewer, Mon 19 Oct 2026. I did not write this change. I read the B11 design note (sections 2 to 7), the
round 4 and round 3 summaries in lane-reports/vendor-b11-LANE.md, and the section 6 table of
lane-reports/PLAN-codex2-signin-road-2026-10-18.md. Then I read the whole diff of the range. No code was changed. I
ran no walk, take, container or vendor call, and I opened no login, token, lease or account file. The two skill digests
held under R4-3 are held on purpose and are not counted as a finding.

There are no MAJOR findings. Arm A's road is unchanged in behaviour. No fail-open path was found in the census check.
Edit D's record is complete. The version probe's throwaway home is correct. The verdict is CHANGES because of the two
MINOR findings below.

## Findings

1. MINOR. A new guard has no test that fails without it (threat 5). This is evals/gap-study-4/box/run_take.py.
   - Line 2519 is the device check: every census entry must be on the root folder's device. Replace it with
     `if False:` and no test in the ruled list goes red.
   - Lines 2610-2615 are the codex lease-record binding: `folder.lease` is a LeasePlacement at
     `<config_dir>/auth.json`, bound to the record's uid map. Replace it with `if False and (...)` and no test goes
     red either.
   - I ran each mutant on its own scratch worktree outside the clone, under env -i (see Checks). All of these stayed
     OK: test_config_folder (19), test_run_take (68), test_take_config (12), test_env_allowlist (37),
     test_drive_ownership (48), test_box_integration (61), test_pending_walk (23), test_codex_adapter (56) and
     test_gemini_adapter (144).
   - test_config_folder's own `--witnesses` registry (27 of 27 red) has no entry for either guard.
   - Missing check: tests/test_config_folder.py needs a case and a registered witness for each guard:
     - a census entry whose `dev` differs from the root's, which must refuse;
     - a codex ConfigFolder whose lease path is not `<config_dir>/auth.json`, or whose lease uid_map differs from
       the record's, which must refuse.
   - From reading only, not mutated, these may also lack a test of their own:
     - `folder.harness`/`run_tree` mismatch (line 2608);
     - the placed-kind and placed-nlink problems (lines 2529, 2532);
     - "absent at its read" (line 2579).

2. MINOR. The arms are treated unequally in a way the section 6 table does not name (threat 1). This is R4-2,
   evals/gap-study-4/box/preflight.py lines 379-431 (`VERSION_PROBE_*`, `_version_argv`).
   - Arms O and G now run their `--version` probe on a throwaway HOME and config home under the take's /tmp, which
     is then discarded. So their config folder holds exactly the placed set at turn 1.
   - Arm A's probe still runs with CLAUDE_CONFIG_DIR on the config mount (comment at line 385). Whatever
     `claude --version` writes stays in arm A's config folder for the agent's turn 1.
   - This preflight difference between the arms is deliberate and ruled. But the section 6 table of
     lane-reports/PLAN-codex2-signin-road-2026-10-18.md has no row for it. Its B11 rows are R-H5, R-CF (line 269) and
     R4-4 (line 270), and none of them mentions the version probe.
   - Missing: a "B11 R4-2" row in that table naming the difference and what bounds it (test_config_folder
     C12VersionProbe; test_preflight TestPrograms' arm A pin).

3. NIT. Stale routing prose: evals/gap-study-4/box/run_take.py line 2200 (the R-CF block comment) and line 2433
   (ConfigFolderRefused's docstring).
   - Both still say a refusal after turn 1 is routed as "harness-error".
   - Under R4-1, a refusal after turn 1 is a stop for a ruling: drive.py raises DriveRefused, and its message says
     "no registered harness-error row reads it". batch records that as failed with drive_started True, the same as
     the settings guard.
   - The code is right; the two comments describe the old routing.

4. NIT. evals/gap-study-4/box/take_config.py lines 341-358: `config_sha256` now admits R-H3's four arg0 links for
   every harness, arm A's config folder included. Today this has no effect: the only caller is `take_config.write`
   (line 319), which runs on a fresh folder with no links. If a later caller hashes a folder after a turn, the link
   rule should be limited to the codex harness, as `check_config_folder` already is.

## What was checked and held

- Arm A's road (threat 1):
  - No diff in the range touches box/settings_guard.py, box/sidecar.py, box/sidecar/, claude_code_adapter.py,
    check_take.py, box/Dockerfile or prereg-draft.json.
  - The claude-code TAKE_ENV row is untouched.
  - `run_turn` calls `check_config_folder` only for CONFIG_FOLDER_HARNESSES (run_take.py line 2659). C8 pins this with
    a spy, and the witnesses arm-a-checked and check-skipped are red.
  - The shared LAUNCHER_SOURCE gained a HOME loop guarded by `if v in e` for CODEX_HOME and GEMINI_CLI_HOME. So arm
    A's exec argv bytes change, but its behaviour does not. This is the same pattern round 2 already used for R-H1.
  - Arm A's version probe argv is unchanged (`_version_argv`'s claude-code branch).
  - harness_bookkeeping TABLE is untouched. Only VENDOR_CANDIDATES gains `.home/**`, and it is inert in production.
- Fail-open (threat 2):
  - I read config_folder_problems, _allowed, _lease_problems and _read_problem against the note's sections 1, 2, 4
    and 5. Before turn 1, every entry other than the placed set refuses.
  - After turn 1, the order is: "other" refuses first, then the named refusals, then the allow-list with kind,
    link-target and nlink checks.
  - Reads run only when the census is clean. They go through operator_read, and only to the section 6 point 2 list.
  - auth.json is checked by facts only and is never read.
  - I checked every honest allow-listed name and every embedded skill path component against
    `ownership.credential_name`. Only `auth.json` matches, so no honest entry is turned into "other".
  - A folder the agent makes unreadable makes the census fail. That is a refusal, so the check fails closed.
  - I found no honest section-5 case (H1 to H4) that the check refuses, given R-H1's placed trust table.
- Edit D (threat 3):
  - Mechanically verified: drive.py at the head hashes to POST_EDIT_D_DRIVE_SHA256.
  - `without_edit_d(drive.py at the head)` equals drive.py at 52619ab1 byte for byte.
  - `edit_b_problems` and `edit_d_problems` return nothing, and `check_vendor_sources.py EB drive.py` exits 0.
  - The 7 EDIT_D hunks are exactly the 7 hunks of the drive.py diff.
  - Routing:
    - Before turn 1, a refusal goes through `_refused` with `ok = False`. turns is empty, so the outcome is None
      and no records are taken: a rehearsal, as the settings guard's pre-1 refusal is.
    - After turn 1, `take.config_stop` is set and DriveRefused is raised after cleanup, postflight and the scan.
      batch records it as failed with drive_started True.
    - No road passes silently.
  - The codex lease handed in is walk_builders' `lease_for_take` record, a LeasePlacement.
- The version probe (threat 4):
  - `tempfile.mkdtemp` runs under /tmp, the take's tmpfs (mode 1777): neither the config folder nor the run tree.
  - `shutil.rmtree` runs in `finally`, and a failed discard fails the probe.
  - stdout, stderr and the exit code pass through, so the parsed version is the harness's own output, unchanged.
  - The adapters' own `version()` execs carry no config home, so they do not write into the config folder.

## Checks run

All runs were in the foreground under `env -i` with only PATH, HOME, LANG and TMPDIR set. TMPDIR and HOME were in the
session scratch directory, outside the clone, and CLAUDE_CODE_MESSAGING_TOKEN was unset. The head was 07312e4f.

| module | result |
|---|---|
| test_config_folder | 19 OK |
| test_drive_ownership | 48 OK |
| test_box_integration | 61 OK |
| test_pending_walk | 23 OK |
| test_vendor_envelopes | 7 OK |
| test_vendor_check | 26 OK |
| test_run_take | 68 OK |
| test_take_config | 12 OK |
| test_env_allowlist | 37 OK |
| test_walk_builders | 94 OK |
| test_harness_bookkeeping | 23 OK |
| test_preflight | 59 run, 1 failure |
| test_codex_adapter | 56 OK |
| test_gemini_adapter | 144 OK |

- The test_preflight failure is TestLeasePostflight.test_the_lease_admits_exactly_its_one_credential. The same test
  fails at 52619ab1 (scratch worktree, 59 run, 1 failure), so it is present at both and is not this range's.
- Extra checks:
  - `test_config_folder.py --witnesses`: 27 of 27 red.
  - `check_vendor_sources.py EB drive.py`: rc 0.
  - The edit D script check is described under "What was checked and held".
- Mutant 1 (run_take.py line 2519, the device check off): every module listed in finding 1 stayed OK. It survived.
- Mutant 2 (run_take.py line 2610, the codex lease-record binding off): every module listed in finding 1 stayed OK.
  It survived.
- In the first archive copies, test_run_take and test_take_config could not start because they need the repository's
  git history. That was only my setup, and the git worktree runs in the table above replace them.
- `gitleaks git --staged` was run before this commit.
