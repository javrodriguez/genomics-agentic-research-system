# Gap Study round 4: the D8 hook positive control (design, not run)

_Written Wed 21 Oct 2026, 22:33 EDT (clock read with `date`), by a read-only design sub-agent for glitch-f1._
_Study tree read: `evals/gap-study-4` at `d5c0f7989083990f0eb76308b8eb79f86e41d7e4` in `/Users/javrodher/aegis-builds/freeze-dry-20261021`, through `git show` only._
_B27 road read: head `49c350a9` in `/Users/javrodher/aegis-builds/vendor-b27-20261021`, through `git show` only (d5c0f798 is not in that clone: B27 is not yet on the study line)._
_Gemini CLI 0.64.0: the pinned tarball (sha256 `891a794e…6e` read back equal) extracted with `tar -x` into the new empty folder `/private/tmp/claude-501/-Users-javrodher-glitch/de671dc9-9274-4a09-b079-1f80eb793658/scratchpad/hookctl/pkg/`, never executed; the three bundle files read below hash to the sha256 values take_config.py records (`gemini-Q2GRYIAK.js` 7702da31…, `chunk-NR7L3FXV.js` d566e81b…, `chunk-FLKY6NH5.js` f6a4ddd4…)._
_Codex 0.162.1: no source of the hook engine is on this Mac (the local subset `/Users/javrodher/aegis-builds/gap4-codex-rollout-audit-20261014/src/codex-rs` has no `hooks/` folder); Codex facts below are the study's own citations or its committed help capture, labelled so._
_Nothing was run, built or written anywhere but this file and that scratch folder; no credential, lease, token, key or .env file was opened; scripts ran behind `mac_slot.py light-ok --work gap-study-r4` (one hold waited out)._

## Findings first

1. **D8's control is not done, and the study has no road for it yet.** The switches are values only: `box/take_config.py:69` (`CODEX_FEATURES = (("hooks", False), CODEX_PLUGINS)`) and `:94` (`("hooksConfig.enabled", False)`), asserted in `tests/test_take_config.py:632` and `tests/test_live_box.py:163`.
2. **Gemini: the switch is the single gate, verified in the pinned bundle.** `hooksConfig.enabled` becomes `enableHooks` (`gemini-Q2GRYIAK.js:8656`), default true (`chunk-NR7L3FXV.js:380944`); with it false the `HookSystem` is never built (`chunk-NR7L3FXV.js:381113-381116`), so the headless road's `SessionStart` firing finds no hook system (`gemini-Q2GRYIAK.js:17752-17755`) and no hook of any source (user, workspace, extension) can be registered (`chunk-NR7L3FXV.js:364897-364917`). With folder trust off (`take_config.py:119`), `checkPathTrust` returns trusted (`chunk-NR7L3FXV.js:360568-360569`), so a user-settings hook in the take's own `settings.json` would run when the switch is on (`chunk-NR7L3FXV.js:364901-364904`, `:365029`). The B27 stub road fits this control almost unchanged.
3. **Codex: a second gate sits beside the switch, so a naive control would pass for the wrong reason.** The pinned 0.162.1 help lists `--dangerously-bypass-hook-trust`, "Run enabled hooks without requiring persisted hook trust for this invocation" (`lane-reports/live-box-evidence-2026-10-13/codex-exec-help.json`, captured from a take-o image reporting `codex-cli 0.162.1`, `lane-reports/live-box-2026-10-13.md:101`; that image id `sha256:ac201dbe…` is older than today's lock `sha256:21b21415…`, same version). A planted hook with no persisted trust may stay silent even with hooks on. The design therefore runs the trust-bypassed pair (where only the switch differs) beside the study's exact argv.
4. **Codex has no stub or fake model road in the study.** `box/stub_agents/` is in-memory with no container (`box/stub_agents/agents.py:1-13`), and B27's probe is Gemini-only (`stub_model_probe.py:81`, `HARNESS = run_take.GEMINI`). The cheapest honest road is no model at all: `SessionStart` is a session-start event, so the marker can be written before any model request. Whether `codex exec` reaches session start with no login is not verifiable here, so the hooks-on twin is the arbiter, with two fallbacks named in section 2.
5. **Cost: about $0, no Codex2 allowance, no Google spend; about 30-45 minutes of an operator on athena, solo, plus one builder lane of about 3-5 hours and one review.**
6. **Doc drift seen in passing (NIT for glitch-f1):** `box/settings_guard.py:221` still says "the take's CODEX_HOME config.toml has no [projects] table, so the project layer is disabled", but R-H1 places that table (`take_config.py:79-90`, `:429-430`, `:475-476`); the project layer is now trusted, and its `.codex/hooks.json` is kept out by the launcher (`run_take.py:290-295`) and the switch, not by a disabled layer.

## 1. The control, per harness

### Shared shape (both harnesses)

- **Road:** B27's stub-model probe, `box/stub_model_probe.py` on `49c350a9`, started only through `walk_launch.py probe` (B27 `walk_launch.py:754-780`: the O_EXCL claim under the hold id, the athena gate, `athena-reserve hold`, nohup, `walk.pid`/`walk.log`/`walk.exit`) and fetched with `walk_launch.py fetch-probe` (`:848`, manifest check and canary scan, nothing reaches a clone).
- **What runs unmodified, as in B27 (`stub_model_probe.py:15-22`):** `run_take.create_argv` on the locked image by id with `--pull=never`, read-only root, the run tree and config folder as the two bind mounts; `make_config_dir`; `launcher_argv` (the agent starts from an empty environment plus the row); `ownership.grant`/`operator_list`/`operator_read`/`restore`; `_teardown_partial`, `leaked`, the network listing; `walk_builders.TAKE_RESOURCES`.
- **Images:** the committed locks only. Gemini `sha256:d10aa00b5958b00d1c719be1f0572967c04f30bfe381a427107c9e9a3f16b013` (`box/gemini/image.lock:10`, checked by `check_image`, `stub_model_probe.py:134-141`); Codex `sha256:21b214159e4eb02d5e73f78ccdf5ee047da2fc6944808f9a454a6b0f427dd381` (`box/codex/image.lock:10`), checked by the same rule against that lock (new).
- **Network:** a fresh `docker network create --internal` (`stub_model_probe.py:275-276`), no proxy, no sidecar: no route out, so no spend is possible.
- **The planted marker hook:** one command hook that appends its event name to `<run tree>/.hookctl/fired.log`.
  - Command (no `$`, no quoting traps, the image's own python3; Gemini runs it with `bash -c`, `chunk-NR7L3FXV.js:254665`, `:365194-365212`): `/usr/bin/python3 -I -S -c "import os,sys;fd=os.open(sys.argv[1],os.O_WRONLY|os.O_CREAT|os.O_APPEND,0o644);os.write(fd,(sys.argv[2]+chr(10)).encode());os.close(fd)" <run tree>/.hookctl/fired.log <EventName>`.
  - It prints nothing, so it adds no hook context to the prompt (`gemini-Q2GRYIAK.js:17756-17765`).
  - `.hookctl/` is created by the probe in the run tree (granted to the agent with the run tree) and read back after each process with `ownership.operator_list`/`operator_read` (root_kind `run_tree`), as B27 reads the stub's `state.json` (`stub_model_probe.py:487-489`).
- **Self-test (so an absent marker can never mean a broken command):** before the CLI processes, the probe runs the exact marker command once as the agent through `run_take.agent_exec_argv` with event name `selftest`; `fired.log` must then read exactly `selftest`.
- **The diff rule (so "off" differs from "on" by the switch alone):** a pure function builds both twins from `take_config.files_for(...)` bytes and refuses unless (a) the off twin's config equals the study's bytes plus only the planted hook, and (b) the on twin differs from the off twin in exactly one value, the switch. Each config's sha256 and the study config's `config_sha256` are recorded side by side.
- **Two processes per run where the road allows:** process 1 fresh, process 2 a resume (`-r <session id>` for Gemini, `codex exec resume <thread id>` for Codex), because every walk turn after the first is a resume and `SessionStart` has a resume source (`gemini-Q2GRYIAK.js:17752`).
- **Labels:** every record carries `record_kind` `stub-model-probe` and the not-a-study-record text (`stub_model_probe.py:76-78`, `:113-117`); the output is one new `stub-probe-<id>` folder outside the study's record folders (`:121-131`).

### Gemini (arm G)

- **Where the hook goes:** a top-level `hooks` key added to the take's own `GEMINI_CLI_HOME/.gemini/settings.json` (`take_config.py:320`), the user scope, read through `settings.hooks` (`gemini-Q2GRYIAK.js:8658`).
  - Shape, as the registry validates it (`chunk-NR7L3FXV.js:364941-364986`): `{"<Event>": [{"matcher": ".*", "hooks": [{"type": "command", "command": "<marker command> <Event>"}]}]}`.
  - Events planted: all eleven of `HookEventName` (`chunk-NR7L3FXV.js:336623-336636`), each with its own name in the marker, so the off twin is tested against every event, not one.
- **Twins:**
  - **G-on:** the study's settings, plus `hooks`, with `hooksConfig.enabled` true. **The marker must read `SessionStart` in process 1** (pass condition); the other events seen are recorded, with the prediction written before the run (expected at least `BeforeAgent`, `BeforeModel`, `AfterModel`, `BeforeTool`, `AfterTool`, `AfterAgent`, `SessionEnd`; not a pass condition).
  - **G-off:** the study's settings byte for byte plus `hooks` (`hooksConfig.enabled` false as the study writes it). **`fired.log` must hold only `selftest`** after both processes.
- **Model:** the B27 stub (`box/stub_model_server.py`, stdlib, on 127.0.0.1 inside the container, HTTP 400 and held on anything unscripted, `stub_model_server.py:10-17`), with B27's exactly-three environment changes (`stub_model_probe.py:24-28`, `:219-244`): `GOOGLE_GEMINI_BASE_URL` the stub, `GEMINI_API_KEY` the fixed dummy string, `HTTPS_PROXY` absent.
- **Scenario file:** one new `box/stub_model_scenarios/HG.json`, two processes; process 1's prompt gets one `read_file` call then text (so the tool events can fire in G-on), process 2's prompt gets text only. B27's own scenarios show both shapes work (A1 request 0 a call, request 9 text only).
- **argv:** `gemini_adapter.argv` (`-p <line> -o stream-json -m <model> --approval-mode yolo`, `-r <session id>` after process 1), checked by `run_take.check_model` (`stub_model_probe.py:259-265`). Unchanged.
- **Prediction to watch:** with only user-scope hooks, `getProjectHooks()` is empty (`gemini-Q2GRYIAK.js:17534`), so no `trusted_hooks.json` is written (`chunk-NR7L3FXV.js:364874-364891`); the config folder listing after each run is recorded to check it.

### Codex (arm O)

- **Where the hook goes:** `CODEX_HOME/hooks.json` (the config mount, `run_take.py:171`), the user layer's hooks file per the study's citation (`run_take.py:230-231`: `hooks/src/engine/discovery.rs 146-148` each layer's hooks folder, `339-343` its `hooks.json`). The launcher's project refusal reads only the working folder's ancestors (`run_take.py:290-295`), so `/opt/cfg/hooks.json` is not refused there; the walk road's per-turn config-folder audit would refuse it (`run_take.py:2420`), and the probe deliberately does not run that audit (a named departure: the control isolates the switch).
  - Shape: GARS's own Codex hooks file, the only shape seen working (`workspaces/genomics-agentic-research-system/gars/.codex/hooks.json:1-28`): `{"hooks": {"SessionStart": [{"matcher": ".*", "hooks": [{"type": "command", "command": "<marker command> SessionStart"}]}], "PreToolUse": [...same, PreToolUse...]}}`.
  - Events planted: `SessionStart` and `PreToolUse` only. Other names appear only as schema file names in the pinned tree listing (`gap4-codex-rollout-audit-20261014/src/git-tree-recursive.json`, `codex-rs/hooks/schema/generated/*`); an unrecognised name could make Codex reject the whole file and silence the on twin for the wrong reason.
- **Config:** `take_config.files_for(CODEX, model=..., run_tree=...)` bytes (the study's `config.toml` with its trust table, `take_config.py:465-477`); the on twin changes the one line `hooks = false` to `hooks = true` under `[features]` (`take_config.py:409`).
- **argv:** `codex_adapter.argv` (`codex exec --json -m <model> --dangerously-bypass-approvals-and-sandbox <line>`, `resume <thread id>` on process 2; `codex_adapter.py:279-296`, `:76-89`), checked by `run_take.check_codex_turn` before anything is appended (B27's order for `--fake-responses`, `stub_model_probe.py:259-265`).
- **Environment:** the Codex row (`run_take.py:169-171`) less `HTTPS_PROXY`, no login: `launcher_argv(NO_LOGIN, ...)` (`run_take.py:308`, `:316`); no lease is ever placed (`place_lease`, `read_login` and `exec_argv` never called, bound by ast as B27 binds its own, `stub_model_probe.py:11-13`).
- **Run tree:** `git init` plus one empty commit, so the trust table's key and the git-root lookup match a walk's (`take_config.py:79-88`); B27's run tree is not a checkout (`stub_model_probe.py:552-555`), and Codex's exec road cares more.
- **Runs (four per road):**

| Run | config | argv | Must | Why |
|---|---|---|---|---|
| O-on-bypass | hooks = true | study argv + `--dangerously-bypass-hook-trust` | marker `SessionStart` | proves this CLI build loads and runs a hook from that file when hooks are on |
| O-off-bypass | study bytes | study argv + `--dangerously-bypass-hook-trust` | only `selftest` | the switch alone keeps it off, trust bypassed; differs from O-on-bypass by the switch only |
| O-off-study | study bytes | study argv exactly | only `selftest` | the walk's exact posture |
| O-on-study | hooks = true | study argv exactly | recorded, no pass rule | shows whether missing trust alone also blocks (expected silent): a second, independent barrier |

- **Model road, in order (glitch-f1's call, section 3):**
  - **C0 (recommended first, zero new machinery):** no model and no login at all; the internal network has nothing listening. `SessionStart` fires at session start, before the first request; the request then fails and the process exits non-zero or times out. A per-process cap of 120 s (a probe value, recorded as a departure from B27's `PROCESS_TIMEOUT_S = 600`, `stub_model_probe.py:102`). Non-zero exit is expected and not a problem for this road; the pass rule reads only the markers.
  - **C1 (same run, if glitch-f1 wants one athena trip):** as C0, plus a provider table in `config.toml` (`model_provider` and `[model_providers.<neutral name>]` with a dead `http://127.0.0.1:<closed port>` base URL and `requires_openai_auth = false`), in all four runs alike, so on and off still differ by the switch only. The key names are Codex's documented provider settings as of earlier versions, **not verified at 0.162.1** (inference); it is only worth running if C0's on twin is silent because of login.
  - **C2 (only if both on twins stay silent):** a scripted Responses-API stub (new, stdlib, one SSE reply), so turn 1 completes with exit 0 and process 2 can resume. New machinery; built only on that result.
  - **Not proposed:** a real Codex2 turn. It is $0 of money and a sliver of the weekly allowance, but it uses the lease and a real model, which the brief rules out; glitch-f1 can still name it.
- **Resume leg:** process 2 runs only when process 1's stream names a thread id (C2 always; C0 and C1 only if Codex emits `thread.started` before the failed request).

### The verdict (one pure function, tested on fakes)

- **PASS** only if, for each harness: every self-test reads `selftest`; the on twin (G-on; O-on-bypass on at least one road) logged `SessionStart` in process 1; and every off twin (G-off; O-off-bypass and O-off-study on every road run) logged nothing but `selftest` after every process.
- **INCONCLUSIVE** if a self-test failed or an on twin stayed silent (the control could not have failed); next road, or a ruling.
- **FAIL** if any off twin logged an event: the switch does not keep that hook off, and arm O's or arm G's counted runs wait for glitch-f1 (stop condition, section 3).
- The probe exits 0 only on PASS (B27's exit rule, `stub_model_probe.py:647-657`), so `walk.exit` carries it.

## 2. What it proves, what it does not, cost, record, people, code

### Proves

- At the locked images, with the study's own config bytes and argv, in headless `-p`/`exec` mode, fresh and (where reached) resumed: a hook planted in the harness's user configuration runs when the switch is on, and the same hook does not run when only the switch is off.
- For Codex, that the switch holds even with persisted hook trust bypassed, so the walk does not rest on trust alone; and that `hooks = false` is a key 0.162.1 honours (without `--strict-config`, which the help lists, an unknown feature key may be ignored silently; that is inference, and exactly what O-off-bypass would expose).

### Does not prove

- Anything about the Claude Code arm (its per-take settings are `{}`, `take_config.py:8-11`; its project hooks are a separate question, section 3 item 12).
- Hooks from places other switches or guards cover: Gemini workspace `.gemini/settings.json` (refused at the run tree root, `settings_guard.py:141-149`; though `enableHooks` gates every source, `chunk-NR7L3FXV.js:381113`), extensions (`skipExtensions: true`, `gemini-Q2GRYIAK.js:17536`), Codex project `.codex/hooks.json` (launcher, `run_take.py:290-295`), Codex plugin hooks (plugins off, `take_config.py:68`).
- Codex events other than `SessionStart` and `PreToolUse`, and Gemini events the stub script does not reach (`PreCompress`, `Notification`, `BeforeToolSelection` maybe).
- Behaviour behind the real proxy, sidecar or a real model; the walk road's config-folder audit (deliberately bypassed); any CLI version other than the pins.
- That no hook ran in the 74 committed practice walks: that is a records claim (a cheap supplementary scan, section 3 item 8).

### Cost

- **athena:** B27's whole eight-scenario run took about 2 minutes of probe time (`/Users/javrodher/aegis-builds/b27-smoke-20261021/RUNLOG.md`: full run started 21:03:05, first exit=0 reading 21:05:17). This control is 2 Gemini runs (4 processes, seconds each) and 4-8 Codex runs at up to 120 s per process: at most about 16-20 minutes of probe time on the worst case, about 30-45 minutes of operator time with ship, gates, status and fetch. Solo on athena under the hold.
- **Spend:** $0. Gemini uses the dummy key against the in-container stub (`stub_model_probe.py:96`); Codex uses no login on an internal network. No Codex2 allowance, no r4-g spend.
- **Mac:** light only (the dry run, the tests, the fetch and reading).

### Record

- On athena: `<child>/stub-probe-hookctl<N>` (B27 `walk_launch.py:740-742`), with `summary.json`, `calls.json`, `manifest.json`, each run's `probe.json`, both twins' config files, `fired.log` per process, streams and stderr.
- On the Mac: fetched by `fetch-probe` to `/Users/javrodher/aegis-builds/hookctl-<date>/stub-probe-hookctl<N>`, with a `RUNLOG.md` beside it in B27's form.
- In the study: a short labelled note `lane-reports/hook-control-<date>.md` (verdict, sha256 of the manifest, the twins' config hashes) so the freeze and the D8 duty row can cite it (glitch-f1's call, section 3 item 6).

### Who runs it

- An operator lane on the Mac drives `walk_launch.py ship`, `probe`, `status`, `fetch-probe` (B27's RUNLOG steps), with the athena gate before and after; never by hand on athena.
- A builder lane builds the code; a fresh reviewer (opus-medium) reviews it; athena's battery (`test_round4`) runs on the head before the probe; glitch-f1 reads the verdict.

### The code it needs (smallest change on B27's road)

- `box/stub_model_probe.py`:
  - harness per scenario (today fixed to Gemini, `:81`); Codex image check against `box/codex/image.lock`; the Codex env (row less `HTTPS_PROXY`, `NO_LOGIN`) with its own exact-difference check, as `environment_changes` does for Gemini (`:229-244`);
  - `hook_twins(study_files, harness)` → `{on, off}` bytes plus the diff-rule refusal; the probe writes the twin's files with O_EXCL instead of calling `take_config.write` (recorded as a departure, the study bytes' hash beside);
  - `.hookctl/` creation, the self-test exec, the marker read after each process;
  - Codex process argv from `codex_adapter.argv`, `check_codex_turn` first, then the bypass flag on the two bypass runs only; `git init` of the Codex run tree; no stub start for C0/C1;
  - `hook_verdict(records)`; `scenario_problems` reads it; exit 0 only on PASS.
- `box/stub_model_scenarios/HG.json` (Gemini script); Codex scenarios declared as data (`HO-C0`, `HO-C1`) with no stub script.
- `box/walk_launch.py`: `probe_command` gains an optional `--codex-image` (same `PROBE_IMAGE` rule, `:724`, `:761-762`), passed through; scenario names already fit `PROBE_SCENARIOS` (`:723`).
- `checks.d` lines for the new tests; `COPIED.d` claims for the new files (B27's pattern, lane log stage 6).

### Tests on fakes (red first)

- Diff rule: off equals study bytes plus `hooks` only; on differs by exactly the switch; a mutant that flips another key, or flips the switch in the off twin, or drops the hook from the off twin, goes red.
- Marker command: its exact text per event; no `$`; it never names a study word (the eval-awareness rule, D8:347-350).
- Codex argv: the study argv passes `check_codex_turn` before the flag; the flag appears in exactly the two bypass runs; never in O-off-study.
- Environment: Gemini exactly B27's three changes; Codex exactly the row less `HTTPS_PROXY`; no key, no lease (ast: `place_lease`, `read_login`, `exec_argv`, `run_turn` never called).
- Verdict truth table: on silent → INCONCLUSIVE; self-test missing → INCONCLUSIVE; any off event → FAIL; all good → PASS; mutants that ignore the off twin, or accept the self-test line as an event, go red.
- Dry run prints every argv (ownership, network, take, self-test, each process) and runs nothing, on the Mac.
- The single-process hazard check with the stub-agent modules (B27's stage-7 lesson).

### Review

- One fresh opus-medium reviewer, adversarial first lens: can this control pass when hooks would in fact run, or fail to fail? Scope: the diff rule, the verdict, the Codex trust layer, the departures list, the dry run's argv against a walk's.
- Stop rule: the review loop's usual one (stop at nits).

## 3. Open calls for glitch-f1

1. **Base:** build the hook lane on B27's head `49c350a9` now, or wait until B27 folds onto the study line (d5c0f798 does not contain it). Recommend: on B27's head, rebased at fold.
2. **Codex road order:** C0 alone first, or C0 and C1 in one athena trip (recommend both in one trip: minutes, $0), C2 only if both on twins stay silent; a real Codex2 turn only on your word.
3. **The trust layer:** accept O-off-bypass (study config, trust bypassed, only the switch differing from O-on-bypass) as the D8 proof for Codex, with O-off-study as the walk's exact posture beside it. Recommend yes; the alternative, planting persisted trust, needs the trust store's format, which is not readable here.
4. **Event sets:** Gemini all eleven events; Codex `SessionStart` and `PreToolUse` only (GARS's proven shape). Recommend yes.
5. **Pass rule and stop:** PASS as section 1 states; INCONCLUSIVE goes to the next road; FAIL holds that arm's counted runs until a fix and a rerun (yours; Javier only if a fix touches spend or the cut order).
6. **Record home:** fetched folder under `/Users/javrodher/aegis-builds/`, plus a labelled lane note in the study so the freeze manifest can cite it; whether the prereg's `box_residuals` or CP6 block names it.
7. **Second guard, descriptive:** also run `run_take.check_config_folder` host-side over each Codex twin's folder (`run_take.py:2632`) to record that the walk road refuses the planted `hooks.json` by name (`:2420`). Recommend yes (no runtime cost).
8. **Records scan:** a Mac-light scan of the 38 Codex and 36 Gemini committed walks for any hook event in streams and native sessions, as a supplement. Recommend yes; it can ride the end-to-end transcript read.
9. **Resume leg:** Gemini always two processes; Codex only when a thread id exists. Recommend yes.
10. **Codex run tree:** `git init` plus one empty commit (recommend), or B27's plain folder.
11. **walk_launch widening:** an optional `--codex-image` on `probe` (recommend), or a separate subcommand.
12. **Arm A wording:** D8 says "No hook of any kind runs in any arm" (D8-non-claude-arms.md, "Hooks inactive, with a positive control"), while arm A loads GARS's shipped `gars/.claude/settings.json` hooks under `--setting-sources project,local` (`settings_guard.py:4-5`, `:15`). Confirm the D8 line means arms O and G's harness hooks only, or name what arm A needs.
13. **The stale `settings_guard.py:221` text** (Finding 6): fold a one-line correction into the hook lane, or leave it to the review-kit-port scope.

## Verified, inferred, not checked

- **Verified this session:** every study-code and B27 line cited (read at d5c0f798 and 49c350a9 through `git show`); the Gemini bundle lines (tarball hash and the three file hashes equal take_config's records); the Codex help text for `--dangerously-bypass-hook-trust`, `--enable/--disable` and `--strict-config`; GARS's Codex hooks shape; B27's athena timings from its RUNLOG; both image ids from the locks.
- **Inferred:** that Codex's `SessionStart` fires before the first model request and before any login check; that the user layer reads `CODEX_HOME/hooks.json` (the study's citation, not re-read); that an unknown feature key is ignored without `--strict-config`; that Codex runs command hooks through a shell; the C1 provider key names at 0.162.1; the probe-time estimates.
- **Not checked:** Codex's hook engine source at 0.162.1 (not on this Mac; the study cites `hooks/src/engine/mod.rs:241` for the switch, `lane-reports/B11-DESIGN-NOTE.md:277`); the persisted-trust store's format; whether the take images' `bash` is on the agent's PATH for Gemini's hook spawn (the images create the agent with `/bin/bash`, `box/gemini/Dockerfile:18`, `box/codex/Dockerfile:18`).
