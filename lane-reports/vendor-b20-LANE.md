Status: needs-review

## ROUND 4 SUMMARY FOR REVIEW (local executor, 2026-10-20 14:30 UTC)

glitch-26's rulings on REVIEW-vendor-b20-21fc1c7e (0 MAJOR, 1 MINOR, 2 NIT):
- **B20-6 (MINOR-1):** bind the Codex rollout CommandExecution's `cwd` to the take's own repo, exactly, and refuse any other.
  - A stream-only Codex git read has no `cwd` and is not admitted.
  - Gemini: a directory argument already refuses; a test confirms no other route reaches another repo.
- **B20-7 (NITs):** the header path is the doc's exact repo path. Only tested git forms are admitted; ranges and `git show -0` refuse. The ruled shapes are `git log -p -n 1 <commit>` and `git show <commit>`.

Red commit `82a45e51` (tests only; TestB20GitReads rewritten, 17 tests): test_scan_record ran 203 tests, FAILED (failures=32), all in TestB20GitReads.
- Among the reds is the reviewer's probe p3, rebuilt as a refusal: a rollout whose CommandExecution's cwd is another repo was admitted.

Green commit `db4ce72b`:
- **box/scan_record.py:**
  - A shape may carry an optional `git` record, checked by `_git_ok` against a closed schema. A shape without one admits no git read.
  - The `args` form: the call's arguments hold no key but the listed ones.
  - The `cwd` form: the call node's folder is exactly prefix plus the absolute path at the meta key of the file's one meta record (`_git_meta`, `_git_bound`). A third element of each call entry carries that verdict.
  - `_ruled_git` admits exactly `git log -p -n 1 <hex>` and `git show <hex>`, where `<hex>` is 7 to 40 lowercase hex digits.
  - The header must be `diff --git a/gars/_references/environment.md b/gars/_references/environment.md`.
- **The pinned Codex source:**
  - SessionMeta.cwd is a PathBuf (protocol/src/protocol.rs:3171).
  - CommandExecutionItem.cwd is a PathUri serialized as its URL (protocol/src/items.rs:265, utils/path-uri/src/lib.rs:689-695).
  - The committed w-o14 rollout matches: session_meta `/tmp/run-b6ddc761`, CommandExecution `file:///tmp/run-b6ddc761`, with one `.../gars` cwd, which now refuses.
- **gemini_adapter.py:** all three shapes carry `git` `{"args": ("command", "description")}`. dir_path, is_background or any other argument refuses.
- **codex_adapter.py:**
  - The rollout CommandExecution carries `{"cwd": "cwd", "prefix": "file://", "meta": ({"type": ("session_meta",)}, "payload.cwd")}`.
  - The stream and the exec-output copy shapes carry none. The copy admits only its CommandExecution's bound reads.
- **Re-pinned:** both adapters' READ_SHAPES pins, Gemini `d7060c34...` and Codex `68495914...`. The admission list's B20 source-list line now names both adapters and their tests.
- B17's cat and grep reads keep their road, with no cwd asked; a test pins this.

Tests, 17 in TestB20GitReads:
- Admitted: the two forms, each prefix, on Gemini (stream, session) and the Codex rollout (verbatim and literal copies).
- Refused:
  - 13 output near misses, including `evil/_references/environment.md` and the cut path `_references/environment.md`;
  - 31 commands, including the reviewer's p5 forms, `git show -0`, `git log -p`, `HEAD`, uppercase, 6 and 41 hex digits, and a trailing space;
  - Gemini: dir_path (`/elsewhere` and `.`), is_background and `cwd` arguments, on the stream, the session entry and the function-response turn; `-C`, `--git-dir`, `--work-tree`, `cd`, `GIT_DIR=` and `env GIT_DIR=`;
  - Codex: the stream; a cwd of another repo, a subfolder, the plain path, or a trailing slash; no session_meta, two session_metas, or a relative one;
  - the Claude path;
  - a cat read.
- The schema test refuses six malformed `git` records.
- An arms test pins each shape's binding.

Mutants: 22 B20 mutants, each red alone; 137 in the file.
- The forms: log, show, the commit, the show length, the log length.
- The argument allow-list.
- The bound folder; the stream binds no folder.
- One session_meta; an absolute run tree; the file:// form.
- A shell read only; only a git read.
- One prefix; a hunk body; a diff header; the doc's diff; the doc's own path; one path both sides.
- The wrapped script; the copy reads a git source as a diff; the git schema.

The reviewer's probe on `db4ce72b`, run unchanged:
- p3 (Codex cwd elsewhere), p2 (evil path) and p5's five forms now fail their "admitted" assertions, which means they are refused as ruled.
- p1, p4 (23 commands) and p6 stay refused.
- p0's second control (`git log -p HEAD`) is now refused, by B20-7.

Counts, each run after light-ok with env -i and Python 3.13.2:
- test_scan_record: 203 OK.
- test_sidecar: 157 OK, 1 skipped; --process-check ok.
- test_scan_witness: 10 OK.
- test_gemini_adapter: 146 OK; --witnesses 114/114.
- test_codex_adapter: 57 OK; --witnesses 16/16.
- check_vendor_sources: B17 and the B20 line exit 0.
- copy_manifest, build_draft and freeze --check: ok.
- The three B20 admission lines: 3 of 3.

Waiting (heavy; the Mac is booked from 11:59, so these go to the evening or athena): the full 69-line admission list, test_walk_launch and the drive suites, both adapters' generated mutation sweeps, and the athena suite.
Also open, for athena: a w-g11 rescan, to confirm its real run_shell_command arguments are only command and description.

RESUME HERE: review stop (round 4)

## ROUND 3 SUMMARY FOR REVIEW (local executor, 2026-10-20 14:20 UTC)

glitch-26's ruling **B20-5**, made Tue 20 Oct 2026, is glitch-26's own: Javier ruled the line safe in OD57, and which commands may carry it is the implementation's scope.
Gemini practice walk w-g11 was held at the drive scan: generic-api-key three times on one string, OD57's line, which the agent printed with `git log -p -n 1 7bd5b8b` so it carried a `+` diff prefix.
The ruling: admit OD57's exact line, matched by its content sha256, in git diff output with exactly one leading `+`, `-` or space. The read must be a `git log -p` or `git show` inside the take's own repo, in Gemini and Codex read output alike, through the one shared admission path. Nothing else widens.

Red commit `43f304b4` (tests only): test_scan_record ran 199 tests, FAILED (failures=5, errors=14), every failure and error in the new TestB20GitReads.

Green commit `460bf624`, box/scan_record.py:
- `_ruled_git`:
  - the command is `git log` with `-p` or `--patch`, or `git show`;
  - words are split on single spaces;
  - each option is `-p`, `--patch`, `-N`, `--max-count=N`, `-n N` or `--no-color`;
  - each other word is a revision (no shell syntax, quotes, colon path form or redirection).
  - So there is no `-C`, `--git-dir`, `--output`, `--ext-diff` or `--`, and no cd, pipe or environment prefix.
- `_reads_git`: only shell tools (script, wrapped and argv kinds) count. A call whose arguments name a directory (`dir_path`, `workdir`, `cwd`, `directory`) refuses; that is "the take's own repo".
- `_ruled_diff_line`: exactly one prefix and then the 80 ruled bytes.
  - Only diff body lines may sit between the line and its `@@ ` hunk header.
  - The nearest `diff --git a/P b/P` above it must name the doc, with the same P on both sides.
- Wiring:
  - `_shape_read` marks a git read;
  - `_ruled_text` reads its lines as diff lines;
  - the Codex copy rule reads a git source's lines the same way;
  - `_ruled_wrapped` takes the script check as a parameter.
- The Claude path (`_ruled_tool`, `_ruled_bash`) is unchanged.
- Every B17 mutant anchor still matches once.
- Fold found by the run: the sidecar's process check refused `re.fullmatch` in scan_record.py (`uses re.fullmatch, outside its allowlist`). The fix is a compiled `_GIT_COUNT`, with the one witness edit re-anchored to it.

Fixture: w-g11's shape is rebuilt from the investigator's notes (scratchpad wg11-findings.md); no walk record was read.
- Gemini stream `tool_use` and `tool_result.output`.
- The session toolCalls entry's `resultDisplay`, holding the line once under the doc's diff header, with the functionResponse output truncated short of it.
- The line is the doc's own (`_env_line`, hash-matched), never a copied value.

TestB20GitReads, 13 tests:
- Admitted:
  - Gemini stream and session, each prefix (`+`, `-`, space), for `git log -p -n 1 7bd5b8b`, `git show 7bd5b8b`, `git log --patch -3 --no-color`, `git show --max-count=1 HEAD` and plain `git log -p`;
  - Codex stream, and the rollout's CommandExecution with its exec output (verbatim and gpt-6.1-sol's literal).
- Refused:
  - 11 output near misses: another line, `++`, `+ `, no prefix, a tab, trailing text, a cut line, another file's hunk, a renamed side, no diff header, outside a hunk body;
  - 16 commands: `git diff`, `blame`, `log` without `-p`, `-C`, `--output`, `--ext-diff`, a pipe, `cd &&`, a `GIT_DIR=` prefix, `show HEAD:path`, a double space, `-n x`, `cat-file`, `grep`, `/usr/bin/git`, a newline;
  - a `dir_path` argument;
  - Codex `++` and `git diff`;
  - the Claude Bash git read;
  - a cat read with a diff-shaped output.
- 16 B20-5 mutants, each red alone:
  - the subcommand;
  - log needs a patch;
  - the option list;
  - a revision word;
  - `-n` takes a number;
  - git is the first word;
  - the take's own folder;
  - a shell read only;
  - one prefix;
  - a hunk body;
  - a diff header;
  - the doc's diff;
  - one path both sides;
  - only a git read;
  - the wrapped script (Codex);
  - the copy reads a git source as a diff (a behaviour test: the mutant loses the Codex exec output's admission).

Counts. Each run used env -i with Python 3.13.2 and was preceded by light-ok, with heavy bookings for the long ones.
- At `460bf624`'s tree:
  - test_scan_record: Ran 199 OK, 131 mutants red, 16 of them B20-5's.
  - test_sidecar: 157 OK, 1 skipped; --process-check ok.
  - test_scan_witness: 10 OK.
  - check_vendor_sources: the B17 line and the new P2 line exit 0.
  - copy_manifest --check, build_draft --check and freeze --check: ok.
  - The three new admission-list lines: 3 of 3 exit 0.
- Before the compiled-pattern fold:
  - test_gemini_adapter: 146 OK; --witnesses 114/114 red.
  - test_codex_adapter: 57 OK; --witnesses 16/16 red.
  - test_drive_commit 31, test_walk_runner 89, test_wave4_bindings 13, test_walk_layout 14, test_rules_scanner 9, test_drive_box_seams 6, test_native_reader_registration 7, test_drive_loop 27, test_walk_launch 49 and test_config_folder C14 8: each OK.
  - The 66 earlier admission-list lines: 65 exit 0. The 66th is test_sidecar, the fold above, green after it.
  - The fold changed one regex call form, so these were not re-run.
- test_walk_launch ran 2,099 s inside a 20-minute heavy booking, so that booking overran.
- All runs finished by 10:10 EDT, before 11:59.

Flagged, not fixed:
- test_scan_record's module-level loop variable `_cls_from` is a TestCase class, so the loader runs that class twice. At the base that was TestB17Round5 (12 duplicates in "Ran 193"); now it is TestB17Round6 (5 duplicates in "Ran 199"). It is pre-existing, and the counts above include it.
- Codex's CommandExecution `cwd` is not checked: the shapes hand `_reads_git` the argv only. The take's own repo is bound for Codex by the command alone (no `-C` or cd) and by the doc's diff header.

(round 3's stop, superseded by round 4's line above: review stop (round 3))

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

(round 2's stop, superseded by round 3's line above: review stop (round 2))

## ROUND 1 (local executor, 2026-10-20 12:35 UTC)

Design note lane-reports/B20-DESIGN.md, commit `c1a90b2a`, design stop: Codex 0.162.1 writes `.sandbox_migration` (b"v1\n", 0600) at every first session start; every multi-turn arm O take under B11 held at pre-2; recommended ruling (a).
