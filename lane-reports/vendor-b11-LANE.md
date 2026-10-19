Status: needs-review

# Lane vendor-b11

ROUND 2 SUMMARY FOR REVIEW (cloud executor, Mon 19 Oct 2026, 04:26 to 05:15 UTC; glitch-26's rulings R-H1 and R-H5 on the B11 design note). Built red first, then green, each piece its own pair: R-H1 trust table red 7f1d87ae, green d18b4ec5; R-H1 launcher red 144a13c3, green 1f3544a7; R-H5 red 133cf03f, green ade6ae01. Every red failed by assertion. Nothing was run against a vendor, container, login or walk, and no login, token, lease or account file was opened. drive.py, codex_adapter.py, check_take.py and the Codex gate and its tests are untouched.
- R-H1, the trust table (box/take_config.py). files_for, public_record and write gain run_tree. With it, a codex config.toml ends in exactly `[projects."<run tree>"]` and `trust_level = "trusted"`. The key comes from codex_project_key, which follows project_trust_key at rust-v0.162.1 (config/src/loader/mod.rs 1381-1412; dunce::canonicalize, line 61; lowercased on Windows only). So the run tree must be absolute and normalised, carry no doubled or trailing slash, have no link on the way (host realpath equals the spelling; the bind mount keeps that path in the container), and use only the characters A-Z a-z 0-9 . _ @ + - /. Anything else refuses. Codex's lookup tries the cwd, then its git root (config/src/config_toml.rs 907-921), so it finds trust_level set on turn 1 and the write at thread_processor.rs 1362-1378 never fires. write refuses a codex config with no run tree. walk_builders.vendor_config passes the walk's tree. The Gemini and Claude Code files do not depend on the run tree.
- Named for review: files_for without a run tree is still the codex template that the draft's config_templates records, so the draft did not move for R-H1. Each take's file is that template plus the one table.
- R-H1, the launcher (box/run_take.py LAUNCHER_SOURCE). For a row that carries CODEX_HOME, the launcher refuses before exec any of four paths in the working folder or any ancestor up to /, naming the first one found. Each is listed in CODEX_PROJECT_CONFIG_PATHS with its pinned-source lines:
  - .codex/config.toml: loader/mod.rs 405-411, 1663-1677, 1682, 1701
  - .codex/rules: core/src/exec_policy.rs 54, 678-679
  - .codex/skills: ext/skills/src/host_roots.rs 25, 85-91
  - .agents/skills: host_roots.rs 24-25, 154
  The pinned run tree 844a4ce0 carries none of them, so honest takes pass.
- Noted, not acted on: the repo's main carries gars/.codex/config.toml and hooks.json. A future pin that includes them would make every codex take refuse here.
- Also not refused here, because the ruling names four paths: .codex/agents/*.toml (agent roles) and .codex/hooks.json. Question for round 3.
- R-H5. The codex and gemini rows' HOME is now the marker RUN_TREE_HOME, filled per take as <run tree>/.home (RUN_TREE_HOMEDIR). That folder sits beside the run tree's .tmp and is granted with the run tree, because it is part of it. CODEX_HOME and GEMINI_CLI_HOME stay /opt/cfg. walk_builders.place_agent_home makes the folder for a codex or gemini checkout only: empty, mode 700, git-excluded (.git/info/exclude, checked with check-ignore), with run_tree_problems re-read afterwards.
- R-H5, the env checks. Before every exec the launcher checks .env and .gemini/.env in HOME, the row's config home (CLAUDE_CONFIG_DIR, CODEX_HOME or GEMINI_CLI_HOME), the cwd and every ancestor. refuse_env_files does the same host-side for <run tree>/.home on every call and for the config folder. A row's HOME may only be the config mount or RUN_TREE_HOME.
- R-H5, arm A parity. The claude-code row is byte-unchanged. E1Table.test_arm_a_row_is_byte_unchanged pins its source bytes (sha256 f28954de..., lines 155-159 at 56d7713b) and its value (sha256 97dd88fe...). A respaced row and a moved HOME each go red.
- I read the ruling's "arm C" as the Claude Code arm (arm A in the code).
- R-H5, the named difference. It is a new row "B11 R-H5" in the section 6 table of lane-reports/PLAN-codex2-signin-road-2026-10-18.md. The plan has no list of its own called limitations, so following B4's precedent the limitations entry is the draft's box_residuals entry "arm O and G HOME".
- prereg-draft.json moved, regenerated with build_draft.py. Lines 22567-22572 were added: that one box_residuals entry, nothing else. test_build_draft's box_residuals count goes from 7 to 8 (R8.residuals and R8.mode-residual), and the new name is appended to its list.
- harness_bookkeeping's two vendor candidates (inert in production) were re-grounded to the moved run_take lines (TMP 153, codex row 169-171, gemini row 172-174). They now say the session pattern is relative to the config mount, not HOME, so the home a vendor take's evidence names must be the config mount. Both name .home/ as kept in, and test_harness_bookkeeping pins those line moves.
- Mutants, each red alone:
  - take_config, TestCodexTrustTable, 4/4: table dropped, untrusted, key not canonical, write without run tree.
  - test_env_allowlist --witnesses 33/33. 16 are new: 8 for R-H1 (each path dropped, the check off, cwd only, every arm, no arm) and 8 for R-H5 (codex HOME back on the mount, the claude HOME moved, the claude row respaced, the marker unfilled, HOME or the config home unchecked in the launcher, the host's .home unchecked, the HOME rule widened).
  - test_walk_builders --witnesses: 5 new, all red (vendor-config-without-tree, agent-home-not-made, -not-excluded, -every-arm, -open), plus the three re-anchored B19 ones.
  - test_harness_bookkeeping: a ".home/ dropped" subtest.
  - Generated mutants over take_environment and refuse_env_files: 72 run, 72 killed.
- Green on ade6ae01 (clean environment, TMPDIR outside the clone, CLAUDE_CODE_MESSAGING_TOKEN unset):
  - test_take_config 11, test_run_take 68, test_env_allowlist 34, test_walk_builders 94, test_vendor_roads 13, test_live_box 38, test_build_draft 49, test_harness_bookkeeping 21.
  - 35 of the other 38 modules that name TAKE_ENV, the launcher or the draft. test_nested_agent, test_preflight and test_sidecar (and test_settings_guard) fail with exactly their baseline failures (this root sandbox).
  - test_pending_codex_walk 11, test_vendor_walk_road 6, test_codex_adapter 55, test_gemini_adapter 143, test_walk_wiring 20.
  - check_vendor_sources P2 over this round's files rc 0; lint_language clean; copy_manifest --check ok; build_draft --check ok.
  - test_vendor_workspace_guard is not present.
- Open, for review or round 3:
  - (a) run_take does not itself check that <run tree>/.home exists before a turn; the walk builder makes it.
  - (b) What the agent leaves in <run tree>/.home that Codex reads back (.agents/skills, .bashrc, .profile, the marketplace manifests) is not checked per turn. This is check_config_folder's HOME side.
  - (c) check_take's home rule and the run-tree snapshots will now see the agent's tool files under .home/. I did not read how they treat them.
  - (d) The questions above: .codex/agents and hooks.json, and the repo's gars/.codex.

RESUME HERE: review stop (round 2)

ROUND 1 SUMMARY FOR REVIEW (cloud executor, Mon 19 Oct 2026, about 03:50 UTC): lane-reports/B11-DESIGN-NOTE.md written by static reading of Codex rust-v0.162.1 (092d3acd) and Gemini CLI 0.64.0 (tarball 891a794e..., bundle hashes in the note); no code changed, nothing run. Findings that shape B11:
- H1: Codex rewrites config.toml on turn 1 of every take (trust persistence: the bypass flag plus the run tree's .git), adding [projects."<run tree>"] trust_level = "trusted" via temp file and rename. Strict byte identity would refuse every honest multi-turn Codex take. Recommended: take_config places that table up front (ruling needed).
- H2: Codex refreshes auth.json in place (access token within 5 minutes of exp, or a 401): same inode, new bytes. B11 checks it by facts only; a rotated refresh token also leaves the host lease source stale (flagged for the lease road).
- H3: a killed Codex turn leaves tmp/arg0/codex-arg0*/ with .lock and four symlinks; B11 must admit exactly those, and take_config.config_sha256 refuses links.
- Gemini never rewrites .gemini/settings.json as placed (no migration key matches).
- H5 (ruling needed): HOME is the config mount, so the agent's own tools (conda, R, Nextflow, pip caches) write under it and a closed listing refuses those honest turns; recommended a separate agent HOME.
- Refused set includes shell start files (Codex's snapshot runs a login shell and sources .bashrc), root settings.json (Gemini launcher), .gemini/GEMINI.md and tmp/<slug>/memory/** (model-writable memory), and an edited skills/.system with its marker untouched.
- B9 citation NIT: take_config cites the orphan bundle gemini-6ESINPDZ.js; the running chain's lines are gemini-Q2GRYIAK.js 11145 and 11153 (behaviour unchanged).

## Log

- Round 1 started Mon 19 Oct 2026 03:24 UTC on lane/vendor-b11 at f257a99d; design note written; status needs-review.
- Round 2 (glitch-26's rulings R-H1 and R-H5 on the design note) started Mon 19 Oct 2026 04:26 UTC on lane/vendor-b11 at 56d7713b. Baseline, clean environment, TMPDIR outside the clone: test_take_config 10, test_run_take 68, test_env_allowlist 29, test_walk_builders 93, test_vendor_roads 13, test_live_box 38, test_build_draft 49, test_harness_bookkeeping 21 all OK; of the 38 other modules naming TAKE_ENV, the launcher or the draft, 35 OK and test_nested_agent, test_preflight, test_sidecar (with test_settings_guard) red as in earlier rounds (this root sandbox). test_vendor_workspace_guard is not present.
- Round 2 done Mon 19 Oct 2026 about 05:15 UTC at ade6ae01 (code) plus this file and the plan row; status needs-review.
