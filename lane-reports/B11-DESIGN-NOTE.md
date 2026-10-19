# B11 design note: the per-take config folder, checked before every turn

Lane vendor-b11, round 1. Written Mon 19 Oct 2026, 03:24 to 03:50 UTC, by the cloud executor, for glitch-26's review.
Scope: static reading only, no code changed. No CLI, take, walk, login, container or vendor call was run. No login,
token, lease or account file was opened.

## Sources read, and their hashes

- **Codex** is `github.com/openai/codex`, commit `092d3acd6bec3e3a14bdc7e7a2810ab628ab759d`.
  - The tag `rust-v0.162.1` is an annotated tag object `7a078f6b...`. It peels to that commit, checked with
    `ls-remote 'refs/tags/rust-v0.162.1^{}'`.
  - Paths below are relative to `codex-rs/`.
- **Gemini CLI** is `@google/gemini-cli@0.64.0`. The registry tarball's sha256 is
  `891a794e55c8319b6b78f6f8f13d6b8b2782a4709dfd2fcabf3a1f63ae8365e6`, which matches the pin.
- The Gemini bundle files cited below, with their sha256:

| tag | file | sha256 |
|---|---|---|
| [L] | bundle/gemini.js (the bin; the relaunching parent) | `ab113d84c8f1692fd6c95081366718897876d8664328c7bf0ccf9437d688145f` |
| [M] | bundle/gemini-Q2GRYIAK.js (main, imported at [L]:110) | `7702da31cf099ca3e1d64fd195f15b7726b2c2829ec21e955558eb9dbfba47da` |
| [C] | bundle/chunk-NR7L3FXV.js (core) | `d566e81b1df8d4d44a91bf7aeea96a58ec0e6c8934fa424315ef060507dcbb8c` |
| [S] | bundle/chunk-FLKY6NH5.js (settings) | `f6a4ddd46350dad40515218069d369aaa0025f194c552400b69925b941098bc8` |
| [U] | bundle/chunk-MA35JFUP.js (commands, extensions; imported by [M]) | `5afb745a6015fcdd0108c6fa33112e8250bb93774e73634641f458e89f990985` |
| [V] | bundle/chunk-VOLZQW4I.js (startup cleanup; imported by [L]) | `2aea2b74a0f598e459f1d86913f6f24f18a113caff022dc1d9354d744a3a86b6` |

How the reading was done:
- Two readers in this session read the sources in parallel, one per CLI.
- I then re-read each citation that decides a refusal, against the files above. These are the arg0 helpers, the auth
  refresh, the trust write, the skills install, the settings migration, `projects.json`, the logs folder and session
  retention.
- The remaining citations come from the first pass. The review should spot-check them.

**Finding outside B11, for B9.**
- `take_config.VALUE_SOURCES["GEMINI_TRUST_SETTING"]` cites `bundle/gemini-6ESINPDZ.js`, lines 11129 and 11137.
- That file is an orphan build: no file in the package imports it, and neither does `gemini-IPXWMEB5.js`. [L]:110
  imports only `gemini-Q2GRYIAK.js`.
- In the running chain the same check is at [M]:11145 (`if (!isFolderTrustEnabled(settings)) return null`) and
  [M]:11153 (`throw new FatalUntrustedWorkspaceError`). The `?? true` default stays at [S]:9599.
- So B9's behaviour holds, but its citation names the wrong file and lines. I changed nothing; this is for a fold.

## How the folder is used

Facts from the box code:
- `run_take.HARNESS_ENV` (`box/run_take.py` 155-165) sets **both `HOME` and the config home to `CONFIG_MOUNT`**:
  - arm O: `HOME=/opt/cfg` and `CODEX_HOME=/opt/cfg`
  - arm G: `HOME=/opt/cfg` and `GEMINI_CLI_HOME=/opt/cfg`
- So everything either CLI keys on HOME lands in the folder. So does everything the agent's own tools write or read
  under `~` (git, conda, R, Nextflow, pip, shells).
- That one fact drives most of the cases below.

How Gemini resolves its home:
- Core `homedir()` returns `GEMINI_CLI_HOME` when it is set ([C]:252010-252016).
- The global dir is `homedir()/.gemini` ([C]:253174), so settings live at `.gemini/settings.json` ([C]:253194).
- The launcher parent is the exception. It reads `$GEMINI_CLI_HOME/settings.json` with **no** `.gemini`, only for
  `advanced.autoConfigureMemory` ([L]:25-30). It then re-spawns itself ([L]:57-60).

When B11 runs:
- It runs before turn *k*, after turn *k-1*'s agent processes are gone (`kill_agent` / `wait_gone`).
- So files a CLI holds only while running are gone after a clean exit. Their leftovers appear **only after a killed
  turn** (timeout or `kill_agent`). The allow-list must admit those leftovers, or an honest timed-out turn refuses
  the take.

## 1. The placed set

| harness | path | placed by | expected state before turn *k* |
|---|---|---|---|
| codex | `config.toml` | `take_config._codex` | byte-identical to take_config's record **before turn 1 only** (case H1) |
| codex | `auth.json` | `run_take.place_lease` | **never byte-identical by design** (case H2): checked by facts, never read |
| gemini | `.gemini/` (the folder) | `take_config.write` (`os.makedirs`, 0700) | a folder, never a link |
| gemini | `.gemini/settings.json` | `take_config._gemini` | byte-identical to take_config's record, before every turn |

For `settings.json`, nothing in a headless run rewrites it with the file as placed (section 3).

## 2. The allow-list: what each CLI itself writes during one headless run

Legend for the "when" column:
- **S**: startup
- **T**: during a turn
- **K**: left behind only by a killed turn
- **C**: conditional; the condition is named in the row
- **–**: deleted by the CLI

### Codex 0.162.1 (`codex exec`, run in-process through the app server; exec/src/lib.rs:716-777)

| path pattern under the folder | writer, operation | when | source |
|---|---|---|---|
| `tmp/`, `tmp/arg0/` (dirs, `tmp/arg0` chmod 0700) | arg0 helper path, mkdir | S, every process | arg0/src/lib.rs:355-365 |
| `tmp/arg0/codex-arg0??????/` (tempfile dir) | arg0, `tempfile::Builder.prefix("codex-arg0")` | S; removed at exit (guard drop); **left by K** | arg0/src/lib.rs:373-375 |
| `tmp/arg0/codex-arg0??????/.lock` | arg0, create + flock | S; K | arg0/src/lib.rs:25, 378-385 |
| `tmp/arg0/codex-arg0??????/{apply_patch,applypatch,codex-linux-sandbox,codex-execve-wrapper}` | arg0, **symlink to `current_exe()`** | S; K | arg0/src/lib.rs:21-24, 387-401; sandboxing/src/landlock.rs:7 |
| *(stale `codex-arg0*` dirs)* | arg0 janitor, `remove_dir_all` of unlocked dirs | – at S of the next turn | arg0/src/lib.rs:369, 487-512 |
| `state_5.sqlite`, `logs_2.sqlite`, `goals_1.sqlite`, `memories_1.sqlite`, `queue_1.sqlite`, each with `-wal` and `-shm` | state db, create/migrate (WAL) | S | state/src/sqlite.rs:34-39 (names), 157-192; state/src/runtime.rs:130-195 |
| `thread_history_1.sqlite`, with `-wal` and `-shm` | thread store (exec asks for paginated history) | T (lazily, first flush) | state/src/sqlite.rs:39; thread-store/src/local/mod.rs:291-301; exec/src/lib.rs:1461 |
| `db-backups/<id>/…` | state db corruption recovery, rename | C: only on a corrupt db | state/src/runtime/recovery.rs:16, 181-196 |
| `installation_id` (UUID, mode 0644) | `resolve_installation_id`, create once | S (turn 1) | core/src/installation_id.rs:17-62; app-server/src/in_process.rs:445 |
| `skills/`, `skills/.system/**`, `skills/.system/.codex-system-skills.marker` | `install_system_skills`: remove + rewrite when the marker differs | S (turn 1; again only if the marker changes) | skills/src/lib.rs:55-100; core/src/thread_manager.rs:550-554 |
| `models_cache.json` | models manager, `fs::write` (in place), TTL 300 s | S, then periodically | models-manager/src/manager.rs:34-35; models-manager/src/cache.rs:241-247 |
| `cache/codex_apps_tools/<hash>.json`, `cache/codex_apps_server_info/<hash>.json` (+ `.tmp??????` on K) | connectors, tempfile + rename | S/T, when the codex_apps MCP connects (apps on, ChatGPT auth) | connectors/src/connector_runtime/persistence.rs:30-52, 168-197 |
| `cache/codex_app_directory/<hash>.json` | connectors, `fs::write` | C: connector directory load (trigger uncertain) | connectors/src/directory_cache.rs:13, 83-99 |
| `cache/remote_plugin_catalog/*.json` (+ temp on K) | core-plugins, write_atomically | S | core-plugins/src/remote/catalog_cache.rs:17, 128-147 |
| `thread-writer-locks/.coordination.lock`, `thread-writer-locks/<thread-uuid>.lock` | rollout writer lock; the per-thread lock is deleted on drop, **left by K**, swept later | T | rollout/src/writer_lock.rs:17-18, 43-84, 108-120, 182-197 |
| `sessions/YYYY/MM/DD/rollout-YYYY-MM-DDThh-mm-ss-<thread-uuid>[_<rollout-id>].jsonl` | rollout recorder, create + append; `resume` appends to the same file | T | rollout/src/rollout_file_name.rs:62-73; rollout/src/recorder.rs:984-1000, 1740-1785, 2034-2072 |
| `shell_snapshots/<thread>.tmp-<nonce>` → `shell_snapshots/<thread>.<nonce>.sh` | shell snapshot (feature on by default), deleted on session drop; **left by K**; stale ones (no rollout, or older than 3 days) deleted | S of each session | core/src/shell_snapshot.rs:259-283, 528-536 |
| `config.toml` (rewritten), `.tmp??????` beside it on K | **trust persistence**, see H1 | T: turn 1 thread start | app-server/src/request_processors/thread_processor.rs:1352-1378; core/src/config/mod.rs:2431-2441; core/src/config/edit.rs:731-770; utils/path-utils/src/lib.rs:144-155 |
| `auth.json` (rewritten in place) | **token refresh**, see H2 | any `auth()` call | login/src/auth/manager.rs:203-204, 1600-1622, 2391-2404, 3001-3023; login/src/auth/storage.rs:214-231 |
| `cloud-config-bundle-cache.json` | cloud config, tempfile + persist | C: Business/Edu/Enterprise plans only | cloud-config/src/cache.rs:28, 160-190 |
| `plugins/cache/<marketplace>/…`, `plugins/.remote-plugin-install-staging` | remote installed-plugin sync | C: only if the account has remote-installed plugins | core-plugins/src/manager.rs:1596-1616; core-plugins/src/remote_bundle.rs:35 |

**Not written by `codex exec`.** Each of these refuses if present.
- `history.jsonl`: only the TUI uses message-history.
- `log/` and `codex-tui.log`: exec logs to stderr (exec/src/lib.rs:338-341).
- `version.json`: TUI and doctor only.
- `memories/`: the feature is off by default.
- `.tmp/plugins*`: the curated sync is skipped with remote plugins and ChatGPT auth (core-plugins/src/manager.rs:744-760).
- `.tmp/rollout-*.lock` and `.zst` rewrites: both features are off.
- `archived_sessions/` and `session_index.jsonl`: the RPCs that write them are never sent.
- `rules/default.rules` appends: exec forces `approval_policy=Never` (core/src/exec_policy.rs:464-482; exec/src/lib.rs:579).
- `proxy/` certs.
- MCP OAuth files and `secrets/`.
- Any socket or FIFO.

### Gemini CLI 0.64.0 (`gemini -p`, legacy non-interactive path; [M]:12021-12022)

`<slug>` is `basename(run_tree)` lowercased, with each non-`[a-z0-9]` character replaced by `-` and `-N` added on
collision ([C]:253035-253040). The run tree is fixed per take, so B11 can compute the slug in advance.

| path pattern under the folder | writer, operation | when | source |
|---|---|---|---|
| `.gemini/projects.json` = `{"projects": {"<run_tree>": "<slug>"}}` | ProjectRegistry, `projects.json.<uuid>.tmp` + rename | S of turn 1 (rewritten later only if the mapping fails its check) | [C]:252893-252912, 252960-252980 |
| `.gemini/projects.json.lock/` (**a folder**, proper-lockfile) and `.gemini/projects.json.<uuid>.tmp` | lock around every `getShortId`, temp on save | S, transient; **left by K** | [C]:252955-252958, 252899 |
| `.gemini/tmp/`, `.gemini/tmp/<slug>/`, `.gemini/tmp/<slug>/.project_root` (= the run tree path, `wx`) | ownership markers | S of turn 1 | [C]:253079-253112, 253351-253355 |
| `.gemini/history/`, `.gemini/history/<slug>/`, `.gemini/history/<slug>/.project_root` | the same markers; **created even with checkpointing off** | S of turn 1 | same as above; [C]:253377 |
| *(`.gemini/tmp/<slug>/checkpoints/`)* | `cleanupCheckpoints`, `rm -rf` | – at every S | [V]:126-135; [M]:17458 |
| `.gemini/tmp/<slug>/logs/` (empty dir, chmod 0700) | rag logger init | S | [C]:334255-334260, 381051 |
| `.gemini/tmp/<slug>/chats/`, `.gemini/tmp/<slug>/chats/session-YYYY-MM-DDTHH-MM-<id8>[-N].jsonl` | chat recorder, `appendFileSync` per record | T (metadata line before the first API call) | [C]:286703-286745, 286808-286822, 286895-286910 |
| the same `.jsonl` on `--resume` (append); `.tmp-<pid>` / `.unreadable-<ts>` / a legacy `.json` beside it | resume repair paths | C: resume only, repair only | [C]:286662-286700, 286832-286872 |
| `.gemini/tmp/<slug>/chats/<parentSessionId>/<agentId>.jsonl` | subagent recorder | C: a subagent runs | [C]:286709-286725 |
| *(old or unresumable `chats/session-*`, `logs/session-<id>.jsonl`, `tool-outputs/session-<id>/`, `tmp/<slug>/<id>/`, `chats/<id>/`)* | session retention, **on by default** (`enabled: true`, `maxAge: "30d"`) | – at every S, fire-and-forget | [S]:10344-10480, 12675-12697, 9958-9990 |
| `.gemini/tmp/<slug>/tool-outputs/[session-<id>/]<tool>_<id>.txt` | output truncation and masking | C: a large tool output | [C]:254186-254200, 344729-344736 |
| `.gemini/tmp/background-processes/background-<pid>.log` | shell tool, backgrounded process; files older than 7 days unlinked at S | C | [M]:17012-17040; [C]:324254-324270 |
| `.gemini/tmp/<slug>/<sessionId>/plans/` | enter-plan-mode tool | C, unlikely | [C]:355376-355381 |

**Not written by `gemini -p` with the placed settings.** Each refuses if present.
- `installation_id`: telemetry, Clearcut and usage stats are off ([C]:275096-275147, 288935-288938).
- `google_accounts.json`, `oauth_creds.json`, `gemini-credentials.json`, `mcp-oauth-tokens.json`,
  `a2a-oauth-tokens.json`: API-key auth never reaches them ([C]:312802-312809).
- `trustedFolders.json`: folder trust is off.
- `policies/auto-saved.toml`, `policy_integrity.json`, `acknowledgments/`, `trusted_hooks.json`.
- `extensions/**`: `loadExtensions` returns early when the dir is missing ([U]:65778-65782).
- `history/<slug>/.git` and friends: checkpointing is off ([C]:381073-381075).
- `tmp/<slug>/logs.json` and `checkpoint-*.json`: only from a `/chat` slash prompt ([C]:386258-386340).
- `tmp/bin`: no download code; `getGlobalBinDir` has no callers.
- Update and telemetry files.
- Gemini creates **no symlink, hardlink, socket or FIFO** in the folder. Its only lock is the transient
  `projects.json.lock` folder.

## 3. Does either CLI rewrite a placed file during a headless run?

### H1: Codex rewrites `config.toml` on turn 1 of every take. B11 must expect it.

What happens on thread start (app-server/src/request_processors/thread_processor.rs:1350-1378):
- Codex persists the project as trusted when all of these hold:
  - the request carries a cwd (exec always sends one, exec/src/lib.rs:1452)
  - the project has no `trust_level`
  - the config is not projectless
  - the effective permissions can write the cwd
- Every arm O turn passes `--dangerously-bypass-approvals-and-sandbox` (`run_take.check_codex_turn`). That maps to
  `SandboxMode::DangerFullAccess` (exec/src/lib.rs:343-345), so the write-cwd branch is true.
- The run tree carries a `.git`: `walk_builders` builds it as a git checkout with one neutral commit, and `.git` is
  the default project-root marker (config/src/project_root_markers.rs:5). So the config is not projectless
  (config/src/loader/mod.rs:412-414).
- Result: on **turn 1**, `set_project_trust_level(codex_home, <git root of cwd = the run tree>, Trusted)` runs
  (core/src/config/mod.rs:2431-2441).

How the file changes:
- `apply_blocking` re-parses config.toml with `toml_edit` and adds a table, rendered as described at
  core/src/config/mod.rs:2360-2427:
  ```
  [projects."<run tree, normalised by project_trust_key>"]
  trust_level = "trusted"
  ```
- It writes the result with `write_atomically`: a `NamedTempFile` in the same folder, then `persist` (rename)
  (core/src/config/edit.rs:731-770; utils/path-utils/src/lib.rs:144-155).
- So config.toml gets a **new inode** and the tempfile's mode, 0600.
- The keys take_config placed are kept as they were. Exact whitespace comes from toml_edit and is not pinned by this
  reading.
- On later turns `trust_level` is already set, so nothing is written. `exec resume` has no trust write
  (`thread_resume_inner` from line 3641 carries none).
- The project key comes from `project_trust_key` (config/src/loader/mod.rs:1384-1389), which normalises and
  canonicalises the path.

Side effect:
- After the write the config is reloaded with the project trusted.
- So from turn 1 on, Codex also loads project-scope config from the run tree: `.codex/config.toml` from the cwd up to
  the root, `.codex/rules`, and `.agents/skills` (config/src/loader/mod.rs:251-414).
- That is outside the config folder (B10's ground), but B11 should not be read as covering it.

### H2: Codex rewrites `auth.json` in place on token refresh. B11 must never compare its bytes.

When it refreshes:
- `AuthManager::auth()` refreshes ahead of time when the access token's JWT `exp` is within 5 minutes
  (login/src/auth/manager.rs:204, 3010-3017).
- Only when `exp` cannot be parsed does it fall back to `last_refresh` older than 8 days (manager.rs:203, 3018-3023).
- A 401 also triggers a refresh (the `UnauthorizedRecovery` state machine, manager.rs:1828-1993).
- `auth()` runs at startup, in plugin and connector tasks, and before model requests (manager.rs:2391-2404).

What changes:
- `persist_tokens` updates `tokens.id_token`, `tokens.access_token` and `tokens.refresh_token` (each only if the
  server returned it) and sets `last_refresh = now` (manager.rs:1600-1622).
- `FileAuthStorage::save` does `truncate + write` **in place**: the same inode, no temp file and no lock, with mode
  0600 applied only on create (login/src/auth/storage.rs:214-231).
- So the device, inode, one link, mode 600 and owner all stay. Size and bytes change.

Consequence beyond B11, flagged for glitch-26:
- A refresh can rotate the refresh token.
- If it does, the host's registered lease source (`run_take.LEASE_SOURCES`) holds a stale refresh token after the
  take.
- `preflight.postflight`'s compare-only lease check would then see the placed copy differ from its source.

Deletion risk:
- If `CODEX_API_KEY` reached the process, `enforce_login_restrictions` would see API-key auth against
  `forced_login_method = "chatgpt"`, **delete auth.json** and exit (exec/src/lib.rs:656-661;
  manager.rs:1316-1383, 1443-1460, 1500-1506).
- The box's row carries no such variable, and `.env` cannot set `CODEX_*` keys (arg0/src/lib.rs:297-327).
- So this is a refusal B11 should keep, not an honest case.

### Gemini: `.gemini/settings.json` is not rewritten with the file as placed

The migration does not touch it:
- `migrateDeprecatedSettings` runs on every load ([S]:16859-16862). It acts only on:
  - `general.disableAutoUpdate` and `general.disableUpdateNag`
  - `ui.accessibility.*` loading phrases
  - `context.fileFiltering.disableFuzzySearch`
  - `tools.approvalMode`
  - `experimental.{codebaseInvestigatorSettings, cliHelpAgentSettings, plan}`

  ([S]:16862-17020, 17057-17140)
- None of take_config's keys is among them: `experimental.adk.*`, `hooksConfig`, `modelConfigs`, `tools.exclude`,
  `security.*`, `privacy`, `telemetry` and `general.enableAutoUpdate*` are all absent from that list.
- This build has no separate V1→V2 migrator.

How a rewrite would happen, and why none does here:
- Every write goes through `setValue` → `saveSettings` → `updateSettingsFilePreservingFormat`, as a temp file plus
  rename ([S]:16461-16477, 17024-17043).
- The headless callers do not fire:
  - The auth type is persisted only when it is unset **and** `CLOUD_SHELL` or `GEMINI_CLI_USE_COMPUTE_ADC` is set
    ([M]:17519-17531).
  - `model.name` is persisted only by a `-p "/model set … --persist"` slash prompt ([U]:99198-99216).
- So `settings.json` stays byte-identical for an honest take whose prompts are not slash commands.

What is out of B11's scope:
- A deprecated key in the *workspace* file `<run tree>/.gemini/settings.json` would rewrite that file. That is B10's.
- `tools.exclude` only produces a deprecation warning on stderr ([M]:17485-17490).

## 4. The refused set: configuration-shaped files either CLI reads from the folder that take_config does not place

Each of these changes what the next turn does, and nothing honest writes them. Any one present before a turn refuses
that turn.

### Codex (CODEX_HOME and HOME are the same folder)

- `.env`: dotenv, loaded before threads start; `CODEX_*` keys are filtered out (arg0/src/lib.rs:159, 299-327).
- `AGENTS.override.md` and `AGENTS.md`: global instructions (codex-home/src/instructions/mod.rs:12-13, 43-57).
- `rules/**`, chiefly `rules/*.rules`: exec policy (core/src/exec_policy.rs:54-56, 679).
- `agents/*.toml`: agent roles from each layer's config folder (agent-roles/src/loader.rs:75-80).
- `skills/**` **other than** `skills/.system/**`, plus `.agents/skills/**`: user skill roots. `$HOME/.agents/skills`
  is the same folder here (ext/skills/src/host_roots.rs:94-118).
- `skills/.system/**` **whose contents differ from the embedded set**.
  - Codex rewrites `.system` only when the marker differs from the embedded fingerprint (skills/src/lib.rs:84-89).
  - An edited skill with an untouched marker therefore persists, and is loaded.
  - At the pin the embedded set (`skills/src/assets/samples`) holds 48 files in 21 folders (`find -type d` lists 22,
    counting the root), with no links, across `imagegen`, `openai-docs`, `review-agent`, `skill-creator` and
    `skill-installer`. `sha256sum` over the sorted file list hashes to
    `f5702460ae03a0bd98d89a01224afb315f70313a06db41284cab367ac468d55d`.
  - The marker is a Rust `DefaultHasher` value (skills/src/lib.rs:111-123), so it is not computable outside the
    binary. It is best recorded from the take image once.
- `hooks.json`: not read while `[features] hooks = false` (hooks/src/engine/mod.rs:241), but refused anyway, since
  it is hook config.
- `environments.toml` (exec-server/src/environment_toml.rs:26, 237).
- `*.config.toml`: profile layers (with `--profile`, which the turn shape refuses; refused anyway).
- `requirements.toml` and `managed_config.toml`: these are read from `/etc/codex`, not the folder. Refuse them here
  too, so a mis-set path cannot use them.
- `.agents/plugins/marketplace.json`, `.agents/plugins/api_marketplace.json`, `.claude-plugin/marketplace.json`,
  `.cursor-plugin/marketplace.json`: personal marketplaces under HOME (core-plugins/src/marketplace.rs:20-25,
  307-314).
- `.cache/codex-runtimes/**`: the primary-runtime marketplace under `$HOME/.cache`
  (core-plugins/src/marketplace_policy.rs:546-567).
- `plugins/**`: plugin manifests `.mcp.json`, `.app.json`, `hooks/hooks.json` (core-plugins/src/loader.rs:70-72).
  These are config, so they are refused even though Codex itself writes `plugins/cache` for an account with
  remote-installed plugins. See case R4.
- `cloud-config-bundle-cache.json`: a managed-config bundle, read back. See case R5.
- **Shell start files.**
  - The shell snapshot runs a *login* shell and then sources `$HOME/.bashrc` (or `$ZDOTDIR`/`$HOME/.zshrc`)
    (core/src/shell_snapshot.rs:586-605; shell-command/src/startup.rs:9-27).
  - A login bash also reads the first of `~/.bash_profile`, `~/.bash_login`, `~/.profile`.
  - So **`.bashrc`, `.bash_profile`, `.bash_login`, `.profile`, `.zshrc`, `.zprofile`, `.zshenv`, `.zlogin`** in the
    folder are read by Codex, and the snapshot is replayed into every shell command.
- Agent-writable files that are read back but cannot be refused by a listing: `sessions/**` (read on `resume`),
  the sqlite files, `models_cache.json`, `installation_id`. They are allowed by name. Their content is a named
  residual: the session sweep and the native reader already judge `sessions/**`.

### Gemini CLI (GEMINI_CLI_HOME and HOME are the same folder)

- `settings.json` **at the folder root**: the launcher reads it for `advanced.autoConfigureMemory` ([L]:25-30).
- `.gemini/.env` and `.env`.
  - The env search goes from the cwd up to `/`, checking `<dir>/.gemini/.env` and then `<dir>/.env`.
  - Only after reaching the root does it fall back to `~/.gemini/.env` and then `~/.env`.
  - Existing variables are never overridden ([S]:16542-16572, 16602-16650).
- `.gemini/GEMINI.md`: global memory ([C]:363483-363497).
  - The model can write it with `write_file` or `replace`. `isPathAllowed` whitelists that exact file
    ([C]:382330-382356, 253540).
  - So an agent writing it is the very case B11 exists for. Refuse it.
- `.gemini/tmp/<slug>/memory/**` (`MEMORY.md`, `GEMINI.md`): project-private memory, read into context
  ([C]:363498-363520). It is model-writable for the same reason as `GEMINI.md`. Refuse it.
- `.gemini/extensions/**` ([U]:65778-65790, 61263).
- `.gemini/agents/**`: agents are on by default ([C]:342579, 380820).
- `.gemini/skills/**` and `.agents/skills/**`: skills default on ([C]:253238-253255, 366391-366393, 380828).
- `.gemini/policies/**` ([C]:367775, 367862-367889).
- `.gemini/commands/**`: slash prompts only ([U]:74994-75001).
- `.gemini/trustedFolders.json`: read every run ([M]:17474; [C]:360716-360750).
- `.gemini/mcp-server-enablement.json`, `.gemini/keybindings.json`, `.gemini/trusted_hooks.json`,
  `.gemini/policy_integrity.json`, `.gemini/acknowledgments/**`.
- `.gemini/projects.json` **with any content but the one expected mapping**.
  - It is read every run, and it decides the temp dir.
  - A changed mapping redirects the session and memory paths.
- Credential-shaped names: `oauth_creds.json`, `google_accounts.json`, `gemini-credentials.json`,
  `mcp-oauth-tokens.json`, `a2a-oauth-tokens.json`, `installation_id`. These are also caught by
  `preflight.CREDENTIAL_LIKE` where the name matches.
- The Gemini shell tool runs `bash -c`, so it reads no shell start files. They are refused anyway under the general
  rule below.

### Both, by the general rule

The general rule: anything not on the allow-list and not placed refuses. With HOME in the folder, the files the
agent's **own tools** read from `~` fall under it. They are not the CLIs' reads, but each is a cross-turn
configuration channel, so refusing them is correct:
- `.gitconfig`
- `.condarc` and `.conda/`
- `.Rprofile` and `.Renviron`
- `.nextflow/` (it holds `config`)
- `.npmrc`
- `.config/**`
- `.netrc`, `.curlrc`, `.wgetrc`
- `.ssh/`
- `.inputrc`

## 5. Every case that would refuse an honest take

| id | case | what an honest take leaves | what B11 must do |
|---|---|---|---|
| **H1** | Codex trust write, turn 1 | `config.toml` = placed keys + `[projects."<run tree>"] trust_level = "trusted"`, new inode, mode 0600 | Not byte-identity after turn 1. Either (a) **recommended**: take_config places that table up front, so nothing is written and byte-identity holds every turn (needs `files_for` to take the run tree and a ruling); or (b) parse with `tomllib` and require exactly the placed document plus that one table, with the run tree as key. |
| **H2** | Codex token refresh | `auth.json` bytes changed in place | Check by facts only: regular, one link, mode 600, the agent's mapped owner, the same dev and inode as `place_lease`'s record, size 1 to `LEASE_MAX_BYTES`. `operator_read` refuses the name anyway (`ownership.credential_name`). Its content stays postflight's job. |
| **H3** | a killed Codex turn (timeout, `kill_agent`) | `tmp/arg0/codex-arg0??????/` with `.lock` and **four symlinks**; `thread-writer-locks/<uuid>.lock`; a `shell_snapshots/*.tmp-*` or `*.sh`; possibly `cache/**/.tmp??????` or a `config.toml` sibling `.tmp??????` | Admit exactly these shapes. A link is admitted **only** at those four names in that one folder shape (readlink checked against the image's codex executable). `operator_list` reports it as `"link"`, and the caller must not refuse it there. Note `take_config.config_sha256` refuses any link: a postflight hash after a killed Codex turn would refuse too. |
| **H4** | a killed Gemini turn | the `.gemini/projects.json.lock/` folder, `projects.json.<uuid>.tmp`, a partial session `.jsonl` | Admit them. proper-lockfile's stale lock (10 s) is recovered by the next start. |
| **H5** | the agent's tools write under `~` (= the folder) | `.cache/**` (pip, matplotlib, fontconfig), `.nextflow/**` (history, plugins), `.conda/environments.txt`, `.npm/**`, `.local/**`, `.Rhistory`, `.bash_history` (possible from Codex's snapshot shell; not settled statically), `.lesshst`, `.wget-hsts` | Under the ruled closed listing **these refuse the next turn**, though the agent did nothing wrong. GARS takes run conda, R and Nextflow, so this is the likeliest honest refusal. **Ruling needed, not blocking this note.** Recommended: give the agent a separate writable HOME outside the config mount and keep `CODEX_HOME` and `GEMINI_CLI_HOME` on the mount. Gemini keys everything but `~/.gemini/policies/sandbox.toml` (sandbox only, [C]:257794) on `GEMINI_CLI_HOME`. Codex's HOME reads (`.agents/**`, the marketplace manifests, `.cache/codex-runtimes/**`, the shell start files) would move to that HOME, and B11 would then check those paths there as a refuse-if-present set while tool caches stay free. The alternative is to keep HOME on the mount and accept H5 refusals as harness-error rows. |
| **H6** | Gemini session retention deletes at startup | an unresumable or subagent `chats/session-*` from an earlier turn is **unlinked** by the next turn's start ([S]:9970-9985) | Nothing for B11, since a closed listing does not refuse absence. Noted because it deletes native evidence: the native reader should take each turn's session before the next turn starts. |
| **R4** | Codex remote-installed plugins | `plugins/cache/**` with `.mcp.json` and hooks | Refuse. Codex2's account is expected to have none. If it has some, the take is not the study's configuration anyway. |
| **R5** | Codex cloud config on Business/Edu/Enterprise plans | `cloud-config-bundle-cache.json` | Refuse unless glitch-26 rules the codex2 plan eligible. This reading cannot tell the plan without reading the lease. |
| **R6** | Codex DB corruption recovery | `db-backups/**` | Refuse and record. It is rare, and its cause is not the agent's to show. |

## 6. Recommended check shape

`run_take.check_config_folder(runtime, *, image, harness, run_tree, config_dir, placed, lease, turn) -> None`

Where it runs:
- Call it in `run_take.run_turn` beside the per-turn lease check, before `exec_argv` builds the turn.
- A Codex turn already reaches `check_codex_lease_place` through `_codex_exec_argv`. Put the new call immediately
  before `exec_argv`, so every harness's turn gets it.

What it does:
1. **List, level by level, through `ownership.operator_list`** (root kind `"config"`) from `"."`.
   - Descend only into folders whose path matches an allow-list folder pattern.
   - Any entry that matches neither a placed path nor an allow-list pattern refuses, with every such path named.
   - `"other"` refuses, except the credential name the lease is placed under (`auth.json` for Codex), which
     `operator_list` reports as `"other"` by design (O-2).
   - `"link"` refuses, except H3's four names.
   - Reading the readlink target needs a small extension of the listing program. Otherwise H3 can be ruled
     admit-by-name-and-shape only.
2. **Read through `ownership.operator_read`** (root kind `"config"`) only:
   - `config.toml` and `.gemini/settings.json`: byte-identical to `take_config.files_for(...)`, or for config.toml
     per H1(b);
   - `.gemini/projects.json`: parsed, exactly `{"projects": {run_tree: slug}}`;
   - the two `.project_root` markers: exactly the run tree path;
   - `installation_id` for Codex: a UUID shape;
   - every `skills/.system/**` file: against the embedded manifest.
   - Never read: the sqlite files, `sessions/**`, `models_cache.json`, `cache/**`. They are admitted by name and
     shape only; their content is the residual named in section 4.
3. **`auth.json`**: facts only, per H2.
   - This needs one compare-only lstat of that one file: dev, ino, mode, nlink, uid, size, with no bytes.
   - That is not `operator_read`, which refuses the name.
   - The options are a facts-only mode added to the listing program, or reuse of the program that
     `check_codex_lease_place` would need anyway to re-stat.
4. **Before turn 1** the folder must hold exactly the placed set and nothing else:
   - codex: `config.toml`, `auth.json`
   - gemini: `.gemini/`, `.gemini/settings.json`
5. On refusal, raise `Refused`, with the problems recorded, routed like `settings_guard.snapshot_problems`: before
   turn 1 a rehearsal, after it harness-error. Run nothing.

Cost: one operator container per listed folder.
- Codex's `sessions/YYYY/MM/DD` adds three or four levels, and `skills/.system/**` about 22 folders.
- If that is too slow, one census program (a sibling of `LIST_PROGRAM`) returning the whole tree's lstat facts in one
  reply is the cheaper shape. It needs the same O_NOFOLLOW and credential-name rules. Ruling needed; this note does
  not pick.

## 7. Tests it needs (all with a fake runtime, as in the existing box tests)

1. **Clean folders before turn 1:**
   - a fresh folder from `take_config.write` with the lease placed passes for codex;
   - the same for gemini;
   - one extra empty file or folder anywhere refuses, named.
2. **The honest Codex sequence passes.** After turn 1 the folder holds every honest turn-1 row of section 2's Codex
   table, and passes. Case: config.toml carries H1's table per the chosen option, and auth.json has new bytes on the
   same dev and ino.
3. **The honest Gemini sequence passes.** After turn 1 the folder holds `projects.json` with the expected mapping,
   the two `.project_root` markers, the empty `logs/` folder, and `chats/session-…jsonl`. It passes.
4. **Killed-turn leftovers pass:**
   - H3: the arg0 folder with `.lock` and four links, a writer lock, a `.tmp-` snapshot;
   - H4: the lock folder and a `.tmp`.
   - A fifth link name, a link at a different depth, or a link whose target is not the codex executable refuses.
5. **Placed files are enforced:**
   - one byte changed in `.gemini/settings.json` refuses;
   - for `config.toml`, refusal under H1(a) follows any change, and under H1(b) follows any change except that one
     table;
   - `auth.json` with a different ino, mode, link count or owner, or missing, refuses.
6. **Each refused-set path refuses.** One parametrised case per section 4 entry, including:
   - `.bashrc` and `.profile`;
   - root `settings.json` for gemini;
   - `.gemini/GEMINI.md`;
   - `tmp/<slug>/memory/MEMORY.md`;
   - a `skills/.system` file edited with the marker untouched;
   - `projects.json` mapping a second path.
7. **Shape rules:**
   - a non-UTF-8 name (`"other"`) refuses;
   - a credential-shaped name other than the placed lease refuses;
   - more than `LIST_MAX_ENTRIES` refuses loudly.
8. **Wiring:**
   - `run_turn` calls the check before `exec_argv` for every harness (a spy runtime);
   - a refusal leaves no launch journal and no stream file.
9. **Pins:**
   - a test binds the allow-list's source citations (the Codex commit, the Gemini bundle sha256s) to the values here;
   - a version bump of either CLI then breaks it on purpose.
