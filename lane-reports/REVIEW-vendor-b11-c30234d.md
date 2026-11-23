VERDICT: PASS

# Review of lane vendor-b11, round 2 (range 56d7713b..c30234d6)

Fresh cloud reviewer for glitch-26, Mon 19 Oct 2026. Measured against rulings R-H1 and R-H5 and the five-point threat
model. I changed no code. No walk, take, container or vendor call was run. No login, token, lease or account file was
opened. No safety check refused a tool call.

To check the Codex claims I read the public source of openai/codex at 092d3acd (the rust-v0.162.1 pin). I fetched only
these paths, into a scratch folder outside the clone: config/src, core/src/exec_policy.rs, ext/skills/src and
app-server/src/request_processors/thread_processor.rs.

## What I checked, by threat

1. **A config.toml that Codex would still rewrite.** None found.
   - thread_processor.rs 1363-1366 persists trust only when `config.active_project.trust_level.is_none()`.
   - get_active_project (config/src/config_toml.rs 907-921) tries the cwd, then the git root. Each lookup
     (config/src/project_trust.rs 28-39 and 76-96) tries the canonical spelling first, then the original one, by
     exact key on POSIX.
   - The take's cwd is the run tree (run_take.py 889 `--workdir`). The tree is bind-mounted at the same path (887).
     It is a fresh one-commit `git init` (drive.clean_run_tree), so its git root is itself.
   - codex_project_key (take_config.py 237-246) admits only a path whose realpath is its own spelling, with no `.`,
     `..`, doubled or trailing slash, and a TOML-safe character set. Anything else refuses, so it fails closed.
   - An honest take's file is the template plus exactly one table: test_take_config TestContents and
     TestCodexTrustTable (`data == plain + TABLE`), and test_walk_builders B19 on the real walk road. The Gemini and
     Claude Code files do not depend on the run tree (checked in TestCodexTrustTable).
2. **Project-config paths.** None missed.
   - discover_project_layers (loader/mod.rs 1653-1701) walks the cwd's ancestors up to the project root and reads
     `<dir>/.codex/config.toml`.
   - exec_policy.rs 54 and 678-679 cover `.codex/rules`.
   - host_roots.rs 24-25 and 85-91 cover `.codex/skills`. Its repo_agents_skill_roots covers `.agents/skills`, from
     the project root to the cwd.
   - The launcher (run_take.py 234-238) refuses all four, in the cwd and every ancestor up to /. That is a superset of
     what Codex reads, as the ruling asks, and the pinned run tree carries none of them (the honest tests stay green).
   - `.codex/hooks.json` and `.codex/agents/` were already ruled to round 3, so they are not findings.
3. **The claude-code row.** Unchanged.
   - Its TAKE_ENV row is byte-identical: E1Table.test_arm_a_row_is_byte_unchanged pins both the source bytes and the
     value.
   - Its launcher checks the same set of folders as before. For that row, `dirs` is HOME plus CLAUDE_CONFIG_DIR (both
     /opt/cfg) plus the ancestors. The codex block is skipped because the row carries no CODEX_HOME.
   - test_preflight and test_sidecar fail identically at 56d7713b and at c30234d6 (see Checks), so their meaning did
     not move. One host-side tightening is noted as NIT 2.
4. **The agent HOME.**
   - `<run tree>/.home` is made inside the run tree, mode 700 and git-excluded (walk_builders.place_agent_home).
     ownership.grant chowns the whole run tree to the agent's uid, so the agent alone can read or write it after the
     grant.
   - Its `.env` and `.gemini/.env` are checked in the container (run_take.py 229, together with every row's config
     home). They are also checked host-side on every call (run_take.py 1142-1145), and the config folder still is too
     (1146-1154).
   - The grader's take.home must be disjoint from the run tree (graders/endstate.py 446-447). harness_bookkeeping now
     says the evidence's home is the config mount, which is consistent with that rule.
5. **A guard without a test.** None found. My four mutants (below) were each caught. The lane's 16 new witnesses, plus
   the 5 in test_walk_builders, cover the rest.

## Findings

1. NIT. `box/run_take.py` line 234 (the codex block of LAUNCHER_SOURCE), and the round-3 HOME side of B11.
   - The pinned Codex also reads `$HOME/.agents/skills` as a user skill root: ext/skills/src/host_roots.rs line 105,
     with HOME taken from `dirs::home_dir()` at line 36.
   - Since R-H5, HOME is `<run tree>/.home`, which the agent writes. A skill the agent leaves there in turn k is loaded
     as a user skill in turn k+1, and nothing in this range refuses it.
   - Before this range the same path sat in the config folder, but no per-turn check of that folder exists yet either,
     so this is no regression. The lane names it as open item (b), and the plan's section 6 row names it too.
   - The missing check: the codex block should also test `os.path.join(e['HOME'],'.agents','skills')`, or B11 round 3's
     HOME-side listing should close it. This belongs in round 3 together with `.bashrc` and `.profile`.
2. NIT. `box/run_take.py` lines 1142-1145.
   - The host-side check of `<run tree>/.home/.env` now runs for every harness, including claude-code, whose HOME is
     not there.
   - It is a stricter early refusal on arm A's host road. It does not touch the row or the launcher. A claude-code
     checkout holds no `.home`, so honest arm-A takes do not change.
   - I name it only because threat 3 asks for every change on arm A's path. No test pins that arm A skips it. None is
     needed unless glitch-26 wants arm A's host road byte-identical too.
3. NIT. `tests/test_run_take.py` lines 765 and 918 (TestExecArgv, TestWalkLoginPlace).
   - These go red when the caller's environment carries this sandbox's proxy and token variables. They refuse
     correctly, by design, and pass under `env -i`.
   - The lane's "clean environment" means exactly that, so this is not the change's fault. The CHECKS line in future
     review prompts could say `env -i` explicitly.

## Checks run

All from evals/gap-study-4 in the foreground, under `env -i PATH=... HOME=/root LANG=C.UTF-8 TMPDIR=<scratch outside
the clone>`. CLAUDE_CODE_MESSAGING_TOKEN was unset.

| module | result |
|---|---|
| tests/test_take_config.py | 11 run, OK |
| tests/test_run_take.py | 68 run, OK (with the sandbox's own environment instead of env -i: 2 failures, NIT 3) |
| tests/test_env_allowlist.py | 34 run, OK |
| tests/test_walk_builders.py | 94 run, OK |
| tests/test_vendor_roads.py | 13 run, OK |
| tests/test_live_box.py | 38 run, OK |
| tests/test_build_draft.py | 49 run, OK |
| tests/test_harness_bookkeeping.py | 21 run, OK |

Extra checks, each run at both 56d7713b and c30234d6:
- test_preflight: 59 run. The same single failure at both commits (TestLeasePostflight lease-credential test).
- test_sidecar: 157 run. The same single failure at both commits (TestRoundTrip.test_round_trip_loads_clean).
- test_box_integration: 61 run, OK at both commits.

My own mutants, made on a scratch clone at c30234d6 outside this clone. Each was applied alone and then reverted.

| mutant | what it changes | result |
|---|---|---|
| M1 | take_config.codex_project_key loses its `realpath` check (a linked run tree is admitted) | killed: TestCodexTrustTable.test_the_trust_table |
| M2 | the launcher's `.agents/skills` is misspelled `.agents/skillz` (the CODEX_PROJECT_CONFIG_PATHS tuple is left alone) | killed: E2Allowlist.test_codex_launcher_refuses_project_config. test_run_take stays green, as expected. |
| M3 | refuse_env_files' check of `<run tree>/.home` covers `.env` only, dropping `.gemini/.env` | killed: E3EnvFiles.test_the_agent_home |
| M4 | the trust table key gets a trailing slash (Codex's lookup would miss it) | killed: TestCodexTrustTable and TestContents |
