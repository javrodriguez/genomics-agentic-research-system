Status: needs-review

## ROUND 2 SUMMARY FOR REVIEW (local executor, 2026-10-20 13:05 UTC)

The rulings are glitch-26's, made Tue 20 Oct 2026 under Javier's standing delegation, on lane-reports/B20-DESIGN.md (round 1, `c1a90b2a`):
- **B20-1:** admit exactly one regular file, `.sandbox_migration`, at the config folder root: content exactly `v1\n` (3 bytes), mode 0600, one link. Its bytes are read and checked; anything else stays refused.
- **B20-2:** red first. Tests for the admitted shape and every near miss in the note come before any code; each near miss stays refused, each has a witness that goes red on its own, and there are mutants that each fail a behaviour test.
- **B20-3:** a test drives the real pre-2 path end to end, so a multi-turn take with the file present passes pre-2.
- **B20-4:** the change touches only codex's allow-list and its reader. The Gemini and Claude admissions stay byte-identical, proved by the existing sibling tests.

Red commit `a98c722d` (tests only): test_config_folder ran 33 tests, FAILED (failures=14, errors=1).
- The 14 failures are all in the new C14SandboxMarker class. They are the honest marker, the 5 byte subtests, the 4 mode subtests, the folder and link subtests, the sibling pin, and B20-3.
- B20-3's red line is w-o17's own text: "turn 2 was refused before its exec: pre-2: the config folder: .sandbox_migration: neither placed nor on codex's allow-list".
- The error is C7Shapes.test_shape_rules, which was already failing at the base `8877ddfb` (checked with a stash). APFS refuses the test's non-UTF-8 file name `bad-\xff` with Errno 92. It is not B20's and is left for athena, where Linux accepts the name.

Green commit `2acd1582`: box/run_take.py, 12 lines added and none removed.
- CODEX_ALLOWED gains one row: `\.sandbox_migration`, a file, read by rule `sandbox_marker`, cited to execpolicy/src/sandbox_migration.rs 10, 21-27, 32-47 and core/src/session/mod.rs 649-664.
- New constants SANDBOX_MARKER = b"v1\n" and SANDBOX_MARKER_MODE = 0o600.
- config_folder_problems refuses the marker at any other mode, after the existing kind and link checks.
- _read_problem refuses any other bytes.
- Deviation, flagged: the note proposed adding a sandbox_migration.rs citation to the root `.tmp` row. It was not made, because B20-4 pins codex's allow-list to the base plus exactly one row. The `.tmp` leftover of a killed write still passes on the existing row, and that is tested.
- Also flagged: the honest marker sits in C14's own test, not in the shared `Take.codex_turn_one`. That keeps every existing witness attributed to its own test, so C2.honest stays as B11 left it.

C14SandboxMarker (tests/test_config_folder.py), 8 tests:
- B20-1 honest: the marker passes before turns 2 and 5, and its bytes are read once per check. The row cites the pinned source. A killed write's `.tmpQ7xZ2k` passes. Before turn 1 the marker refuses as "not placed".
- B20-2 near misses, 18 cases, each refused and named:
  - bytes: `v2\n`, `v1`, `v1\r\n`, `v1\n` with text after, and empty;
  - mode: 644, 400, 700 and 666;
  - shape: a folder, a symlink to auth.json, a second hard link, a fifo;
  - name: `skills/.sandbox_migration`, `tmp/.sandbox_migration`, `.Sandbox_Migration`, `.sandbox_migration.bak`;
  - harness: the marker in a gemini folder.
- B20-3 end to end: three turns through run_take.run_turn, the road CodexAdapter._turn takes with each turn's number.
  - The check is the real one: the census and read programs run in-process over the folder.
  - A fake CLI writes on its first exec what the pinned Codex writes at its first session start, the marker included.
  - Turns 2 and 3 reach their exec. There is one census per turn, and the marker is read before turns 2 and 3.
  - exec_argv is replaced by a spy, because the real one needs the lease gates. Everything before it is real.
- B20-4 siblings: GEMINI_ALLOWED, CONFIG_FOLDER_NAMED (both harnesses), CONFIG_FOLDER_PLACED and CONFIG_FOLDER_HARNESSES (which has no claude-code) are pinned by sha256 of their repr at `8877ddfb`. CODEX_ALLOWED with the one marker row taken out is pinned to the base too.

Witnesses: 17 new, 53 in the registry. `--witnesses` over the 50 that can run on the Mac: 50/50 red, each red alone, with its own clause.
- The 3 registry witnesses bound to C7Shapes (kind-unchecked, other-admitted, hard-links-admitted) cannot run on the Mac because of the APFS error above. They are athena's.
- Each near miss has its own red. Every subtest turned red under its mutant's own run:
  - marker-unread and marker-bytes-unchecked: all 5 byte cases.
  - marker-mode-unchecked: all 4 mode cases.
  - marker-kind-unchecked: the folder and the link.
  - marker-hard-links-admitted: the hard link.
  - marker-other-admitted: the fifo.
  - marker-name-nested: tmp.
  - marker-name-any-case: the case.
  - marker-name-suffix: the suffix.
  - marker-skills-unnamed: skills.
  - marker-gemini-admitted: gemini.
- Behaviour mutants:
  - marker-row-absent: the honest test.
  - marker-row-absent-e2e: B20-3.
  - marker-read-dropped: the honest test's read.
  - sibling-gemini-moved and sibling-codex-moved: B20-4.

Counts. Each run used env -i with Python 3.13.2 on /usr/local/bin and the tree at the green change. Modules ran after `mac_slot.py light-ok`; the long ones ran under `mac_slot.py run --kind heavy --owner b20`.
- test_config_folder: Ran 33, every C14 test OK, with C7Shapes' pre-existing APFS error.
- test_config_folder --witnesses: 50/50 red over the 50 Mac-runnable entries of a 53-entry registry.
- test_run_take: 68 OK.
- test_take_config: 16 OK.
- test_env_allowlist: 37 OK.
- test_drive_ownership: 48 OK.
- test_box_integration: 61 OK.
- test_pending_walk: 23 OK.
- test_scan_record: 193 OK.
- test_sidecar: 157 OK, 1 skipped.
- test_gemini_adapter: 146 OK; --witnesses 114/114 red.
- test_codex_adapter: 57 OK; --witnesses 16/16 red.
- test_scan_witness: 10 OK.
- `check_vendor_sources.py P2 box/run_take.py tests/test_config_folder.py`: exit 0 (neither file is a native-reader source).
- Every command line of checks.d/vendor-admission.txt, 66 lines in two heavy bookings: 33 + 33 ran, 0 failed.
- Every heavy run finished by 09:04 EDT, before the GPU pilot's 11:59 booking.

Left unrun (athena's): the 3 C7-bound witnesses and C7Shapes itself (Linux file names), and the full athena suite.
Not touched: athena and the w-o17 walk folder; what becomes of w-o17's held take is a human ruling.
Not pushed.

RESUME HERE: review stop (round 2)

## ROUND 1 (local executor, 2026-10-20 12:35 UTC)

Design note lane-reports/B20-DESIGN.md, commit `c1a90b2a`, design stop: Codex 0.162.1 writes `.sandbox_migration` (b"v1\n", 0600) at every first session start; every multi-turn arm O take under B11 held at pre-2; recommended ruling (a).
