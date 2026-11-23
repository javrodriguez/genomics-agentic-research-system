# Plan: the Codex2 sign-in road, and readiness of the first Codex and first Gemini walks

Writer: read-only planner for glitch-b5, Sun 18 Oct 2026, about 05:20-06:00 EDT, on the Mac.
Read at the vendor lane head `7f0ae4614b3b70f5d6939721598d975a93963bf4` (refs/remotes/mirror/lane/vendor-admission of /Users/javrodher/aegis-builds/gap4-live-harness-20261013), with `git show`; nothing was checked out, fetched or run.
D/ below means evals/gap-study-4/ at that head.
athena was read with read-only ssh only (id, ls -la, stat, sha256sum of tool scripts, command -v, docker image ls and image inspect); no file under /home/javier/gap4-secrets/ was opened, and no login, CLI or container was run.
Official sources were read with WebFetch, cited where used.

## 0. What changes the picture (read first)

1. **The Gemini key is very probably already in.**
   The night log says "21:46 glitch-5a: Javier placed the r4-g Gemini key; I confirmed verify reads RESULT: OK" (/Users/javrodher/glitch/plans/gap-study-round-4/orchestrator-night-2026-10-13-claude.md:554).
   athena agrees by metadata: `/home/javier/gap4-secrets/r4-g/gemini-walk-login` is mode 600, javier, 69 bytes, modified 14 Oct 21:44; the prepared, empty file was 15 bytes (lane-reports/live-box-2026-10-13.md:3361).
   So the brief's "a protected file on athena waits for his paste" looks stale; Javier owes no Gemini paste unless he has since deleted that key in AI Studio.
2. **A Codex take on a ChatGPT login talks to chatgpt.com, and the box only lets it reach api.openai.com.**
   D/box/egress/proxy_conf.py:32-36 gives `CODEX: "api.openai.com"`, and the take's one route out is that proxy (proxy.conf: `http_access allow tunnel api_host`, `deny all`).
   Codex at the pinned tag picks its base URL by auth mode: `to_api_provider` sends `AuthMode::Chatgpt` to `CHATGPT_CODEX_BASE_URL = "https://chatgpt.com/backend-api/codex"` and only API-key auth to `https://api.openai.com/v1` (raw.githubusercontent.com/openai/codex/rust-v0.162.1/codex-rs/model-provider-info/src/lib.rs, read 18 Oct).
   The pinned binary carries both strings side by side (lane-reports/live-box-evidence-2026-10-13/codex-auth-binary-markers.json:238).
   As built, the first real Codex turn would be refused at the proxy.
3. **Every Codex turn would refuse its own placed lease, by owner.**
   drive.launch calls `spec_for` (which places the lease, host-owned) and then `_grant_ownership`, which chowns the whole config folder to the agent (D/drive.py:2143, 2152, 2154; D/box/ownership.py:90-93, 171-185, OWN_PROGRAM's recursive fchown).
   Each turn then runs `run_turn → exec_argv → _codex_exec_argv → check_codex_lease_place` (D/codex_adapter.py:367; D/box/run_take.py:1152-1153, 1293, 1303), which requires the file owned by the reading host user (run_take.py:1281-1282) in a mode-700 folder owned by that user (check_login_place, run_take.py:1374).
   After the grant both belong to the agent's mapped uid, so turn 1 raises LoginRefused.
   This is an inference from reading; no test drives `_codex_exec_argv` after a real grant (the tests use fake ownership), so it must be proved red first (piece B3).
4. **Neither vendor walk can be built yet, whatever the logins.**
   `routing.json` `pin_profiles` holds only `claude-code` (D/routing.json:63), and `prereg-draft.json` `version_pins` holds codex and gemini with `"version": "PENDING"`, `"permission_mode": "PENDING"` (D/prereg-draft.json:20390 onward).
   `walk_builders.agent_versions` then gives Missing for both harnesses (D/walk_builders.py:990-1020), so `walk_row` refuses, and `batch.expected_pin` refuses by name ("CP5 registers it", D/batch.py:422-430).
5. **The account record is missing on athena.**
   `stat /home/javier/gap4-secrets/account-emails.json`: No such file or directory (read 05:21 EDT).
   Round 10 ruling 2 makes every codex and gemini walk refuse before launch without it (D/walk_builders.py:268-326; lane file line 172).
6. **No walk writes the per-take vendor config, and three of its values are still PENDING.**
   Only build_draft calls `take_config.files_for`; nothing on the walk road calls `take_config.write` (grep of D/ outside tests).
   `CODEX_REASONING_EFFORT`, `GEMINI_THINKING` and `GEMINI_AUTH_SETTING` are PENDING (D/box/take_config.py:52, 68-69, 84-85).
   So a walk today would run each vendor CLI with its own defaults: Codex without `web_search = "disabled"`, `forced_login_method = "chatgpt"`, `check_for_update_on_startup = false`; Gemini without `tools.exclude = ["google_web_search", "web_fetch"]` and telemetry off.
   Both web tools are server-side and would pass the one allowed host, which D8 forbids (D8-non-claude-arms.md:286, 312).

## 1. Before Javier can run the Codex2 sign-in safely

**Where the lease lives (new, registered):** `/home/javier/gap4-secrets/codex2/auth.json`.
- The folder: mode 700, owner javier (uid 1000), beside `claude1/` and `r4-g/`, so `walk_builders.account_emails_path()` still finds one private folder (D/walk_builders.py:244-257 requires every registered account folder under one parent).
- Register it in a new constant `run_take.LEASE_SOURCES = {"codex2": "/home/javier/gap4-secrets/codex2/auth.json"}`, not in `WALK_LOGIN_FILES`: that map is for one-line `NAME=value` files read by `read_login` (run_take.py:275-276, 1377-1420), and a JSON lease there would break `prepare_walk_login.py`, `verify_walk_login.py` and `login_file_by_name`.
- `account_emails_path()` must keep working: it reads only `WALK_LOGIN_FILES`, which is unchanged.
- `production_builders()["lease_path"]` reads `LEASE_SOURCES["codex2"]` instead of the hard-coded Missing (D/walk_builders.py:1116-1117).
- The file name is `auth.json` because Codex writes `CODEX_HOME/auth.json` when `cli_auth_credentials_store` is `file` (learn.chatgpt.com/docs/auth: "`file` stores credentials in `auth.json` under `CODEX_HOME`"), and `place_lease` copies it to `cfg/auth.json` (run_take.py:1436, 1494).
  postflight already names that file the one registered credential (D/box/preflight.py:1031); ownership.credential_name hides it from operator reads (ownership.py:327-344).

**How the pinned CLI runs the login: a one-shot container from the pinned take-o image, never a host binary.**
- athena has no codex, node or npm on the host (`command -v codex node npm` printed nothing; `/home/javier/.codex` does not exist), and the pinned image is there: `docker image inspect sha256:21b214159e4eb02d5e73f78ccdf5ee047da2fc6944808f9a454a6b0f427dd381` reads label `app.cli.version` 0.162.1, created 2026-10-13T21:16 (equal to D/box/codex/image.lock `image_id`).
- Why the container is safer: the same pinned bytes the takes run (by image id, `--pull=never`); nothing installed on the host; no everyday `~/.codex` touched; CODEX_HOME set explicitly; it can write only into the one mounted folder.
- The run, by a wrapper `codex_login.py` (below), as javier on athena, in the rootless daemon:
  `docker run --rm -it --pull=never --user 0:0 --cap-drop ALL --security-opt no-new-privileges --read-only --tmpfs /tmp --network <login network> -e CODEX_HOME=/lease -e HOME=/lease --mount type=bind,source=/home/javier/gap4-secrets/codex2,target=/lease <image id> codex -c cli_auth_credentials_store="file" -c forced_login_method="chatgpt" login --device-auth`,
  then the same container shape with `codex -c cli_auth_credentials_store="file" login status`.
- `--user 0:0` is deliberate: under rootless Docker container root is host javier (ownership.py:37 `HOST_UID = 0`), so the file lands owned by uid 1000, which `place_lease` requires (run_take.py:1468-1469).
  Running as the agent (10001) would leave it owned by the mapped uid and refused.
- `-c` reaches both subcommands: `run_login_with_device_code(cli_config_overrides, ...)` and `run_login_status(cli_config_overrides)` both start with `load_config_or_exit(cli_config_overrides)`, and device login refuses with "ChatGPT login is disabled" if ChatGPT is not allowed (raw.githubusercontent.com/openai/codex/rust-v0.162.1/codex-rs/cli/src/login.rs, read 18 Oct).
  The `file` store is explicit because the docs do not say which store is the default ("The page doesn't state which value is the default").
- What the login needs on the network: the device flow calls `<issuer>/api/accounts/deviceauth/usercode`, polls `<issuer>/api/accounts/deviceauth/token`, and exchanges the code (device_code_auth.rs at rust-v0.162.1); the issuer is `https://auth.openai.com` (run_take.py:564-567 notes, manager.rs:212).
  It times out after 15 minutes ("device auth timed out after 15 minutes").
- **Recommended egress for the login: one host, `auth.openai.com`, through a squid container from the locked egress image (`5055a840...`, present on athena) on its own internal network,** rendered by a new `proxy_conf.render_host("auth.openai.com")` that reuses the template's one slot.
  The cheaper alternative is the default bridge network for this one container: it runs only OpenAI's own pinned login code, no model and no agent, for at most 15 minutes.
  That is glitch-b5's call; the plan sizes the proxied road.
- Javier opens the verification page in the Codex2 browser profile on the Mac; the container never needs a browser (device flow: "Open the link in your browser, sign in, then enter the one-time code", learn.chatgpt.com/docs/auth).
  Device code login must be enabled in his ChatGPT security settings; the night log says it is ("Codex2: device login on", orchestrator-night...:486).

**The prepare script (`prepare_codex_lease.py codex2`, deployed to `/home/javier/gap4-tools/codex-login/`):** the walk-login pattern (lane-reports/walk-login/prepare_walk_login.py).
- Never as root; home outside every git repository; umask 077; creates `gap4-secrets/codex2` mode 700 if absent; refuses if the folder holds anything (a lease is never overwritten: a re-login is a deliberate `--replace` that moves the old file aside to a timestamped name first, never deletes it).
- Prints only paths, modes, owner and sizes as JSON.

**The verify script (`verify_codex_lease.py codex2`): yes/no lines only, never a value, part of a value, or a hash of one.**
- `present (regular file, one link): yes`
- `mode 600: yes`, `owner you: yes`, `folder 700, yours, not a link: yes`, `outside every repository: yes`
- `folder holds only auth.json: yes` (any other entry named; Codex may leave a `log/` folder, which would be named here and ruled, not silently admitted)
- `size between 1 byte and 1 MiB: yes` (place_lease's LEASE_MAX_BYTES, run_take.py:1437)
- `one JSON object: yes`
- `auth mode is ChatGPT (tokens present, no API key): yes`: the object holds a `tokens` object and no non-null `OPENAI_API_KEY` member (the shape `persist_tokens_async` writes with `None` for the API key).
- `no OPENAI_API_KEY or CODEX_API_KEY value anywhere in the file: yes`: a key-name walk over every JSON key plus a byte search for the two names, reporting only yes/no.
- `access_token present (string, 20+ chars, one line): yes` and `refresh_token present (...): yes`: the same rule as `scan_record.read_lease_tokens` with `LEASE_TOKEN_KEYS = ("access_token", "refresh_token")` (D/box/scan_record.py:264, 279-330); the script imports nothing from the repo, so a test binds its rule to read_lease_tokens' on TEST DATA.
- `access token hours left: N` (whole hours from the JWT `exp` claim, which is a time, not a secret) and `last refresh days ago: N`; these settle section 2's refresh question at once.
- `RESULT: OK` only when every line passes; exit 0 or 1.
- What it must never do: print or hash a token, the id_token, the account id or the email claim.

**Javier's own check line:** the wrapper's last step runs `codex login status` in the same container shape; OK reads `Logged in using ChatGPT` (login.rs at the tag).
`Logged in using an API key - ...` would print a masked key: the card says stop, do not copy that line anywhere.

## 2. Before the FIRST real Codex walk can run

**The gate's wording, resolved into an order.**
The comment says the gate "opens only after Javier's Codex2 login and the first real walk" (run_take.py:179-181); the first real walk cannot run while it is closed (place_lease and `_codex_exec_argv` both call `codex_lease_gate()` first, run_take.py:1293, 1455; walk_builders.prepare refuses a codex row, D/walk_builders.py:1186-1189).
Read it as: the gate opens after the login, and the first real walk is its first use.
1. Javier signs in; verify prints `RESULT: OK` (glitch-b5 runs it again).
2. Pieces B2 to B7 below are on the walk branch, reviewed, and the athena battery is green.
3. One commit flips `CODEX_SUBSCRIPTION_READY = True` and rewrites the comment to that order (B8); its review checks nothing else moved.
4. The first real Codex walk runs on the walk road (walk_launch.py `ship`/`run`), commits `pending-native-reader`, and becomes the acceptance candidate.
The gate opening admits nothing into grading: a Codex take's cross-check stays `pending` until Javier's codex acceptance record exists (D/drive.py:3176-3183; D/native_reader_registration.py:159-161), and the drive raises NativeCrossCheckPending before any checker (lane file "gates" item 2).

**Host-side token refresh: not built, probably not needed for practice walks, and its supported form is not what the code comment assumes.**
- Not built: the only refresh code is `CodexLeaseRoad.refreshed()`, which just re-reads (D/walk_builders.py:435-438); nothing refreshes.
- When Codex refreshes by itself: `should_refresh_proactively` refreshes when the access token's JWT `exp` is within 5 minutes, or, if `exp` cannot be read, when `last_refresh` is older than 8 days (gap4-codex-rollout-audit-20261014/src/codex-rs/login/src/auth/manager.rs:203-204, 3001-3023); also on a 401 (learn.chatgpt.com/docs/auth/ci-cd-auth: "if a request gets a `401`, Codex also has a built-in refresh-and-retry path").
  Inside a take the refresh endpoint `https://auth.openai.com/oauth/token` (manager.rs:212) is not in egress, so such a refresh fails and the turn fails closed; the source lease is untouched.
- Whether it is needed: only if the access token lives shorter than a walk plus margin; the docs state no lifetime ("The page does not state an access token lifetime"), so verify's `access token hours left` line measures it on his first sign-in.
- **Build now instead (B5): a walk-start check, not a refresh.** `CodexLeaseRoad.place` refuses by name when the lease's access token has less than the walk budget plus 15 minutes left, or its `last_refresh` is past 7 days; a refused walk asks for a fresh `codex login --device-auth` (two minutes of Javier's), never a hand refresh.
- **If the measured lifetime is shorter than a walk,** the supported refresh is a normal Codex run on the host side ("Any normal Codex run can refresh the session"; "without calling the OAuth token endpoint yourself", ci-cd-auth), so the design would be: between takes (never mid-take), the same login container shape with CODEX_HOME on the source folder and egress to `auth.openai.com` plus `chatgpt.com`, a one-line `codex exec` that spends a sliver of allowance, then verify; one actor holds the source file at a time (ci-cd-auth: "Do not share the same file across concurrent jobs").
  Mid-take refresh is not designed: replacing `cfg/auth.json` mid-take needs a write into the agent-owned config folder, which no road allows today.
  Defer this until the number is read.
- **The refresh-token rotation hazard for the measured run:** up to three concurrent Codex takes share one source lease (machine-order memory note); concurrent use of the access token is fine, but any refresh rotates the refresh token, so refreshes stay serialized on the host and never inside a take.

**Is `lease_secrets` passed end to end for a codex row?** Yes, by reading.
`walk_driver_for` makes one `CodexLeaseRoad`, places it in `spec_for`, and passes `lease.secrets` as `secrets=` to `drive.walk_driver` and to `drive.WalkRepo` (D/walk_builders.py:1225-1232, 1245, 1255-1256); the commit scan runs after the ownership restore (D/drive.py:2860-2882), so `read_lease_tokens`' owner rule (scan_record.py:205-206) sees the host user again.
The take-start read happens in `place`, before the grant (walk_builders.py:418-419), so it also sees the host owner.

**Everything else that would stop the first Codex walk, in road order:**
1. No account record on athena (section 0 item 5): `CodexLeaseRoad.__init__` refuses (walk_builders.py:403).
2. No codex pin profile or version (section 0 item 4): `walk_row` and `pin_for` refuse.
3. Gate closed (run_take.py:181): `prepare` refuses.
4. `lease_path` hard-coded Missing (walk_builders.py:1116-1117): `prepare` refuses.
5. Turn 1 refused by owner after the grant (section 0 item 3).
6. Egress to the wrong host (section 0 item 2): the turn fails at the proxy.
7. No `config.toml` (section 0 item 6): runs, but outside D8 (web search not disabled).
8. Not a blocker, named: `forced_chatgpt_workspace_id` is not set, so the audit's wrong-workspace negative test (codex-0.162.1-rollout-audit.md section 3 verdict) is not needed for these walks.

## 3. Before the FIRST real Gemini walk can run

1. **The key:** in since 14 Oct (section 0 item 1); glitch-b5 confirms with `ssh athena python3 -I /home/javier/gap4-tools/walk-login/verify_walk_login.py r4-g` (the deployed script's sha256 is `2e0e624c2c8a96c56a6b9af32dc487849d939b6cd9a5de8b900e39c2d6ae7215`, equal to the committed one, read today).
   I did not run it (it opens the key file, which this planner may not).
   Only Javier knows whether the key still exists in AI Studio; the first walk's first turn would show a dead key as an auth error.
2. **The account record** (section 0 item 5): `login_secrets` refuses a gemini take without it (walk_builders.py:341-342).
3. **The gemini pin profile and version** (section 0 item 4): same refusal as Codex.
4. **The per-take settings** (section 0 item 6): without `.gemini/settings.json` under GEMINI_CLI_HOME, `tools.exclude` is off and `google_web_search` works through generativelanguage.googleapis.com.
   Whether Gemini CLI 0.64.0 headless picks the API key from `GEMINI_API_KEY` with no auth setting is not established here (`GEMINI_AUTH_SETTING` is PENDING for exactly that reason, take_config.py:69, 82); a static read of the pinned package's non-interactive auth validation settles it, and the first walk's turn 1 would show it.
5. **Already in place, by reading:** the r4-g key is masked in every scan (`login_secrets` with `WALK_LOGIN_FILES["r4-g"]`, walk_builders.py:335-350, run_take.py:275-276); the egress host is right (proxy_conf.py:35); the gemini take lock is ready (D/box/gemini/image.lock `pending: {}`, image `sha256:d10aa00b...`, present on athena); `script_for` works for vendor rows since T0 (lane file, test_vendor_script 8 OK).
6. **What the walk commits:** with no committed `native-readers/gemini-acceptance.json`, `production_readers()` gives no gemini reader, `gemini_cross_check` returns `pending` (D/drive.py:3154-3163), the drive stops with NativeCrossCheckPending, and walk_runner commits it with check.json and grade.json status `pending-native-reader` (D/pending_walk.py:8-10, 25; D/walk_runner.py:29, 247).
   That is the intended state until his reader acceptance.
   The lane rules R-9's recheck onto a second walk, walk-g2, driven by the same road (lane file line 118), so plan two Gemini walks.

## 4. Javier's card (draft, plain words; it goes to him only after the build and its review pass)

# Codex2 sign-in for the GPT arm: your handoff card

_It mirrors the Gemini key card. About five minutes._

## What this is

The GPT arm runs Codex signed in to your **Codex2** ChatGPT account.
You sign in once, on athena, with a one-time code; Codex saves the sign-in in one protected file there.
You never copy or paste the sign-in itself.

## Before you start

1. Use the **plain Terminal app**, in a **new window**: not a Claude Code or Glitch session, not VS Code (whatever prints there is captured into a transcript).
2. Type `cd ~` first.
3. **No screen sharing or recording.**
4. Open the browser profile signed in to **Codex2**, and nothing else of OpenAI's.

## Step 1: start the sign-in

```
ssh -t athena python3 -I /home/javier/gap4-tools/codex-login/codex_login.py codex2
```

It prints a web address and a short one-time code, then waits (up to 15 minutes).

## Step 2: approve it in the browser

1. In the **Codex2** browser profile, open the address it printed.
2. Sign in if asked, then type the one-time code yourself.
3. Approve.

The Terminal then prints `Logged in using ChatGPT` and returns.
If it prints anything with "API key", stop and tell me which line, without copying the line.

## Step 3: check it

```
ssh athena python3 -I /home/javier/gap4-tools/codex-login/verify_codex_lease.py codex2
```

It prints only yes/no lines and two numbers; you want the last line `RESULT: OK`.
If it isn't OK, don't touch the file; tell me which line failed.

## Step 4: clean up

1. Close the browser tab.
2. Clear the Terminal window (Cmd-K) and close it.

Never paste the code, the address or anything from that file into the chat, a command or a note.

## Step 5: tell me

Reply: **codex2 in**, and, if you haven't yet, the two sign-in addresses the study must mask: the email of the Codex2 ChatGPT account and the email of the Google account that owns r4-g (addresses are not secrets; Glitch writes them into the box's private record).

## What protects this sign-in, and what doesn't

- The file sits in a folder only you can open (mode 700), the file mode 600, outside every repository.
- Each walk gets its own copy; the walk's Codex can technically read that copy inside the box, which is why the box lets a walk reach only `chatgpt.com`, and every record is scanned for both tokens before anything is committed.
- A walk never renews the sign-in; if it ages out, the walk refuses at start and I ask you to repeat steps 1 to 4.

_(Gemini: nothing to do if the r4-g study key you placed on 14 Oct is still in AI Studio. If you deleted it, the Gemini card's steps apply again.)_

## 5. The build, in order (each red first; mutants that must go red)

No piece touches a READER_SOURCES or CODEX_SOURCES file (D/native_reader_registration.py:85-87, 160-161: drive.py, native_reader_registration.py, vendor_provenance.py, native_snapshot.py, codex_native.py, transcript_view.py, and the gemini reader files).
Every piece edits run_take.py, proxy_conf.py, walk_builders.py, routing.json, prereg-draft.json or new scripts.
Touching them is allowed now (no acceptance yet), but keeping drive.py out matters: vendor-admission edits B and C are the last planned drive.py change before acceptance (lane file, round 16).

- **B1 (box lane): the login wrapper and the lease scripts.**
  Files: lane-reports/codex-login/{codex_login.py, prepare_codex_lease.py, verify_codex_lease.py, test_codex_lease_scripts.py, verify_mutants.py}, deployed to /home/javier/gap4-tools/codex-login/ with sha256 read back.
  Red: tests that the wrapper's argv is exactly the pinned image id, `--pull=never`, `--user 0:0`, `--cap-drop ALL`, read-only, one bind mount of the lease folder, CODEX_HOME, the two `-c` values and `login --device-auth`; that prepare refuses root, a link, a repo, a non-empty folder; and that verify passes a TEST DATA ChatGPT-shaped auth.json and fails each wrong one.
  Mutants: mode 640 admitted; owner unchecked; second link admitted; extra file admitted; API-key member admitted; `CODEX_API_KEY` string admitted; one token missing admitted; a token printed (output contains a TEST DATA token: red); the hours line computed from a value other than `exp`; `--pull=never` dropped; `--user 0:0` dropped; a second mount added; `-c cli_auth_credentials_store="file"` dropped.
  Plus `proxy_conf.render_host` for the login's one host, with its own check that the rendered text allows exactly `auth.openai.com` (mutant: a second allow line).
  About 2.5 h.
- **B2 (box lane): register the lease source.**
  Files: D/box/run_take.py (`LEASE_SOURCES`), D/walk_builders.py (`lease_path` from it), tests in test_run_take and test_walk_builders.
  Red: `production_builders()["lease_path"]` is the registered absolute path, under the same private folder as WALK_LOGIN_FILES (`account_emails_path()` unchanged).
  Mutants: path relative; path outside the shared folder; codex2 added to WALK_LOGIN_FILES.
  About 0.5 h.
- **B3 (box lane): the placed lease is checked as the agent's after the grant.**
  Files: D/box/run_take.py (`check_codex_lease_place`), its tests; test_run_take's process audit must stay green (OS_ATTRS not widened).
  Red first: drive `_codex_exec_argv` on a placed lease after a grant that changes the file's and folder's owner (a TEST DATA uid map), which raises LoginRefused today.
  Fix: `place_lease` records (st_dev, st_ino, size) of what it wrote; `check_codex_lease_place` takes that record and the take's uid map and requires the same inode, one link, mode 600, owner equal to the agent's mapped host uid (`walk_builders.uid_map_of_pid`, never typed in), folder mode 700 owned by that uid, outside the run tree and every repository.
  Mutants: inode unchecked; owner check accepts any uid; owner check still the host uid (the bug); folder mode unchecked; link count unchecked.
  The `CodexLeaseRoad.login_file_for` call gains the placement record (walk_builders.py:423-428).
  About 1 h.
- **B4 (box lane, needs glitch-b5's ruling on D8 B2 item 8): arm O's egress host becomes `chatgpt.com`.**
  Files: D/box/egress/proxy_conf.py:32-36 and its docstring, tests/test_egress.py (its mutant "codex render carrying the Anthropic host" keeps its meaning), preflight's egress probe evidence for codex re-measured on athena when the battery frees it (a stub take, no login).
  Red: a test that the codex host equals the host of `CHATGPT_CODEX_BASE_URL` as recorded from the pinned source (a sourced constant with its URL and tag).
  Mutants: `api.openai.com` restored; `chatgpt.com` with a leading dot (subdomains admitted); `auth.openai.com` added to a take.
  About 1 h plus the athena re-measure.
- **B5 (harness lane): the walk-start token check.**
  Files: D/walk_builders.py (`CodexLeaseRoad.place`), D/box/scan_record.py only if the `exp` read lives beside `read_lease_tokens` (scan_record is not a reader source).
  Red: a TEST DATA lease whose access token's `exp` is 10 minutes away refuses by name, never printing the token.
  Mutants: margin zero; `exp` ignored; `last_refresh` ignored; the refusal text carries a token.
  About 1 h.
- **B6 (harness lane, with three values ruled by glitch-b5): the vendor config is written on the walk road.**
  Files: D/walk_builders.py (`spec_for` calls `take_config.write(cfg, harness, model=row["model"])` for codex and gemini, before the grant), D/box/take_config.py (the three PENDING values, each with its source).
  Red: a codex walk's config folder holds `config.toml` with `web_search = "disabled"` and `forced_login_method = "chatgpt"`, and a gemini walk's holds `.gemini/settings.json` with `tools.exclude`, through the real `walk_driver_for` on fakes.
  Mutants: the write skipped for gemini; skipped for codex; written after the grant; `tools.exclude` dropped.
  The three values: effort and thinking are "the harness's default for that model at the pinned version" (D8-non-claude-arms.md:167), sourced by a static read of the pinned packages (no model call); the Gemini auth setting likewise.
  If glitch-b5 rules the practice walks may run before those three are sourced, take_config needs a named practice mode, which I do not recommend: D8 line 312 expects no web_search item even in a single walk.
  About 1.5 h.
- **B7 (CP5): the O and G pin profiles.**
  Files: D/routing.json `pin_profiles` (codex: each model `{"permission_mode": "bypass", "version": "0.162.1"}`; gemini: `{"permission_mode": "yolo", "version": "0.64.0"}`, matching codex_adapter.MODE_FLAGS and gemini_adapter.MODE_FLAGS, codex_adapter.py:89, gemini_adapter.py:89), then build_draft regenerates prereg-draft.json's version_pins, and the freeze and walk_regrade checks rerun.
  Red: `agent_versions()` gives a version for codex and gemini; `expected_pin` on the first codex and gemini draft rows returns the profile (test_pin_for_vendor today asserts the named refusal, so that assertion moves by ruling).
  Mutants: version 0.162.0; permission mode "yolo" for codex; one model missing.
  The rate-limit and spend-cap markers CP5 attaches to these profiles (T4 plan R-4) are glitch-b5's to rule; practice walks do not need them if the routing table admits a pin without them, which I could not confirm.
  About 1 to 1.5 h.
- **B8: open the gate.**
  Files: D/box/run_take.py:179-181 only.
  Red: test_run_take's "the gate is closed in the committed module" moves to "open", named as this ruling in the commit; TestCodexKeyUnreachable's structure checks stay as they are (live-box-2026-10-13.md, the rebinding of that test).
  About 0.25 h.
- **Operator steps, not code:** write `/home/javier/gap4-secrets/account-emails.json` (mode 600) from the addresses Javier gives, by a small script that validates with `walk_builders.account_emails` on athena; redeploy no other script.

**Builder estimate:** about 8.5 to 9.5 agent-hours of build, about 11 to 12 with review folds (this lane's measured fold rate, about 30 percent); B1 and B2 alone (what his sign-in needs) are about 3 hours, so the Codex2 sign-in is realistic this afternoon, not this morning.
B3, B4, B6 and B7 are on both arms' first-walk path (B6 and B7 for Gemini too), so the first Gemini walk waits on B6, B7 and the account record, not on any step of his.

## 6. Codex2's allowance (estimate only)

The reading is from **14 Oct 14:20**, not 13 Oct: "Codex2: ... Pro100, 24% left (down from 55% on 13 Oct; resets Tue 20 Oct 20:00)" (orchestrator-night-2026-10-13-claude.md:484-486), plus three reset credits, used only when measured numbers show the runs cannot fit (line 490).
Whether Codex2 was used since (for example by a Codex builder) is not recorded there; the current percentage is unknown.
Practice walks are few: two Codex walks (an acceptance candidate and a recheck walk, by analogy with walk-g1 and walk-g2), each a handful of turns, at least 2 interactions and 1 command round trip (CODEX_FLOOR, native_reader_registration.py:162).
That plausibly fits in what is left before Tuesday's reset; the measured run's arm O takes do not belong in this estimate and are measured at the first walk, as the night log already says.

### Named residuals of the first-walk road (vendor-admission round 17, under glitch-b5's rulings)

| Piece | Residual | Why it stays | What bounds it |
|---|---|---|---|
| B3 (ruling (a)) | Once the grant makes the config folder the agent's, `auth.json` inside it is the agent's to change, and the host trusts the file's placement-time facts (regular, one link, mode 600, host-owned, its size, carried in place_lease's placement record) until the ownership restore. | The host cannot stat inside the agent's mode-700 folder; option (b), a stat-only container per turn, would widen box/ownership.py's operator roads for no gain in what a take can reach. | Before every turn the host checks the folder by lstat (the folder place_lease wrote into, by device and inode; never a link; mode 700; owned by the agent's host uid from the take's uid map) and the path (exactly that folder's `auth.json`); after the restore, postflight admits exactly `auth.json` and read_lease_tokens' rules read it again. |
| B4 (ruling R1) | Arm O's one egress host is `chatgpt.com`, which is also where the Codex2 account's own ChatGPT data lives, and a take holds a copy of the lease; the proxy sees hosts, not paths, and the study does not intercept TLS. | At the pinned Codex 0.162.1 a ChatGPT login sends its model requests to `CHATGPT_CODEX_BASE_URL` (`https://chatgpt.com/backend-api/codex`, rust-v0.162.1, codex-rs/model-provider-info/src/lib.rs line 80), so `api.openai.com` would refuse every turn. | Exactly `chatgpt.com`, no subdomain, never the sign-in host (tests/test_egress.py CodexHostTest); pre-registered in prereg-draft's box_residuals ("arm O egress host"); Javier's card asks him to confirm Codex2 holds nothing he would mind a test agent reaching. The home-server re-measure of the egress probe is glitch-b5's. |
| B11 R-H5 (glitch-26, 19 Oct 2026; a named difference from arm C, the Claude Code arm) | Arm O's and arm G's `HOME` is `<run tree>/.home`, a folder of the run tree the agent writes, while `CODEX_HOME` and `GEMINI_CLI_HOME` stay on the config mount; the Claude Code arm's `HOME` stays the config mount, its `TAKE_ENV` row byte-unchanged (round-3 parity). So a Codex or Gemini take's own tools (git, conda, R, Nextflow, pip and their caches) and Codex's own `HOME` reads (`~/.agents/skills`, the personal plugin marketplaces, the shell start files its shell snapshot sources) live in the run tree, outside the config folder; a Claude Code take's live in its config folder. | With `HOME` on the mount, those honest tool writes would land in the config folder the per-turn config check (B11) reads, and a closed listing would refuse the next turn though the agent did nothing wrong (design note case H5). | `box/run_take.py` `RUN_TREE_HOME` in the codex and gemini rows; `walk_builders.place_agent_home` makes the folder empty, mode 700, git-excluded like `.tmp`, granted with the run tree; the launcher refuses a `.env` (or `.gemini/.env`) in `HOME`, the config home, the working folder and every ancestor before every exec, and the host does the same for both homes (tests/test_env_allowlist.py; tests/test_walk_builders.py B21AgentHome); arm A's row pinned by its bytes (E1Table.test_arm_a_row_is_byte_unchanged). Pre-registered in prereg-draft's box_residuals ("arm O and G HOME"), the study's limitations. Still open for B11 round 3: what the agent leaves in `<run tree>/.home` that Codex reads back (`.agents/skills`, `.bashrc`, `.profile`) is not yet checked per turn. |
| B11 R-CF (glitch-26, 19 Oct 2026; a named difference in mechanism from arm A, the Claude Code arm) | What guards the configuration a turn starts from differs by arm. Arm A keeps its own guard, `box/settings_guard.py`: the run tree's Claude settings, agent, skill and command files are baselined before the grant and compared on the sidecar's snapshot before and after every turn; its config folder is not listed per turn, and its road is unchanged. Arms O and G get the closed census: before every turn, immediately before `exec_argv`, `run_take.check_config_folder` reads the whole config folder's lstat facts in one operator container (`ownership.operator_census`, never a byte), requires exactly the placed set before turn 1 and the placed set plus the design note's section 2 allow-list after it, reads back only what section 6 point 2 lists, checks `auth.json` by its facts alone, and checks `<run tree>/.home` (mode 700, the agent's owner); the launcher also refuses each CLI's `HOME` configuration paths and Codex's project `.codex/hooks.json` and `.codex/agents`. | The two CLIs keep their configuration in different places: Claude Code's study settings ride inline (`--settings`) and its project and local settings sit in the run tree the sidecar already snapshots, while Codex and Gemini CLI read `CODEX_HOME` and `GEMINI_CLI_HOME`, the agent-writable config mount, which no snapshot covers. A census of arm A's folder would change arm A's road, which round-3 parity forbids. | `tests/test_config_folder.py` (C8: a spy pins that a claude-code turn never calls the check, and that an O or G turn calls it before `exec_argv`); `tests/test_settings_guard.py` and `tests/test_drive_ownership.py` S1 to S4 for arm A; routed alike (before turn 1 a rehearsal, after it a stop for a ruling) by the drive-side wiring, landed under ruling R4-1 as check_vendor_sources' edit D (`tests/test_drive_ownership.py` C1 and C2; lane-reports/vendor-b11-LANE.md, round 4). |
| B11 R4-4 (glitch-26, 19 Oct 2026; a named difference in what the end-state grader reads, from arm A, the Claude Code arm) | Arms O and G: the agent `HOME` (`<run tree>/.home`) is inside the run tree, so the sidecar's run-tree snapshots walk and hash it, but the end-state grader does not grade it: the codex and gemini entries of `harness_bookkeeping.VENDOR_CANDIDATES` exclude `.home/**` in `run_tree_paths`. Arm A: its `HOME` is the config mount, outside the run tree, so neither its snapshots nor its grading see it; its `TABLE` entry is untouched. | What the agent's own tools leave in its `HOME` (conda environments, pip, R and Nextflow caches, shell start files) is not the task's work, and grading it would read tool furniture as the agent's changes. Leaving `.home` out of the snapshots instead would change `box/sidecar.py`, which the shared sidecar image bakes in for every arm, a change on arm A's road; so `box/sidecar.py` and the sidecar image stay byte-unchanged. The snapshot cost of a large `.home` (conda environments) is to be measured on the next practice walks. | `tests/test_harness_bookkeeping.py` HomeExclusion (the grader's own `Evidence.is_excluded` each way: excluded under arms O and G, not under arm A) and VendorCandidates (`run_tree_paths` exactly `.home/**`; dropped, widened, narrowed and still-kept-in mutants red). |
| B11 R4-2 (glitch-26, 19 Oct 2026; a named difference in preflight from arm A, the Claude Code arm; row added under ruling R5-2) | Arms O and G run preflight's `--version` probe on a throwaway `HOME` and config home: one fresh folder under the take's `/tmp` tmpfs, neither the config folder nor the run tree, discarded after the probe, so their config folder holds exactly the placed set at turn 1. Arm A's probe runs with `CLAUDE_CONFIG_DIR` on its config mount, and whatever `claude --version` writes there stays in arm A's config folder for turn 1, as in every recorded Claude walk. Arm A's code and bytes do not move. | Before turn 1 the O and G config folder must hold exactly the placed set (`run_take.check_config_folder`), and Codex's arg0 dispatch leaves `tmp/arg0` and a `codex-arg0` folder under `CODEX_HOME` before its `--version` exits (rust-v0.162.1 arg0/src/lib.rs 158-162, 355-401). Arm A has no per-turn census of its config folder (row B11 R-CF), and moving its probe would change arm A's road. | `box/preflight.py` lines 379-431 (`VERSION_PROBE_ROOT`, `VERSION_PROBE_HOMES`, `VERSION_PROBE_PROGRAM`, `_version_argv`: the claude-code branch, line 431, is unchanged). `tests/test_config_folder.py` C12VersionProbe (lines 819-841, with `version_probe_problems` lines 776-816): for codex and gemini the probe, run through `preflight.run` on a fake exec, leaves the config folder holding exactly the placed set; four mutants red on both arms. `tests/test_preflight.py` TestPrograms: arm A's pin at lines 1152-1155 (`World()` is the claude-code arm, line 182: its version probe carries exactly `CLAUDE_CONFIG_DIR=/opt/cfg`, its config home on the config mount, and nothing else); the O and G pin at lines 1166-1175; the mutants version-without-config-home, version-probe-on-the-config-mount and version-probe-root-moved at lines 1182-1184. |
| vendor-b14 round 2 (ruling R-B14-2) | Arm G cannot delegate: its settings exclude `invoke_agent` (box/take_config.py GEMINI_AGENT_EXCLUSION, read at the pinned Gemini CLI 0.64.0: the tool's name at bundle/chunk-NR7L3FXV.js line 283421, its registration at line 382849, the registry leaving excluded tools out at line 313466). Arm A can: Claude Code's argv denies only WebFetch, WebSearch and the isolation tools (claude_code_adapter.DISALLOWED_TOOLS), so the Agent tool is offered and its sub-agents are admitted under the Agent parity ruling and ruling R-C. | The plan's vendor side counts zero Agent calls by construction and refuses any delegation, so an offered `invoke_agent` could only stop a take; excluded, its subagents' helper models (the codebase investigator on gemini-3-flash-preview) never run. | A named difference from arm A on delegation, not a restriction arm A shares: arm G's tools.exclude is bound by tests/test_take_config.py TestB14HelperPins (the exclusion dropped: red), and a stream's `invoke_agent` call still reads as a delegation (transcript_gemini.GEMINI_TOOLS) and refuses the take (transcript_view.DELEGATED_REFUSAL). |
| vendor-b14 round 2 (ruling R-B14-1) | Arm G's helper calls run on, and are billed to, the row's model, where the shipped CLI used other models: each helper alias the run reaches is pinned to the row's model in `modelConfigs.customAliases` (box/take_config.py lines 99-102, GEMINI_HELPER_ALIASES and GEMINI_ROW_ALIASES; written by _gemini at lines 316-320). At the verified 0.64.0 (tarball sha256 891a794e..., bundle/chunk-NR7L3FXV.js sha256 d566e81b...) the CLI ships them on: gemini-3-flash-base on gemini-3-flash-preview (line 362389; loop detection's first check `loop-detection` extends it, line 362486), loop-detection-double-check on gemini-3-pro-preview (line 362493), chat-compression-3-flash on gemini-3-flash-preview (line 362524), chat-compression-3.1-flash-lite on gemini-3.1-flash-lite (line 362529, the gemini-3.5-flash-lite row only), chat-compression-default on gemini-3-pro-preview (line 362549) and agent-history-provider-summarizer on gemini-3-flash-preview (line 362554). So loop detection and its double check, chat compression and the agent-history summarizer now run on the row's model. Arm A's side calls stay on Claude Code's shipped small model: a modelUsage key beside the pin's is admitted only for a model on the closed list SIDE_MODELS = ("claude-haiku-4-5-20251001",) (evals/gap-study-4/claude_code_adapter.py lines 314-317; read at lines 381 and 399, a key off it a mismatch that stops the take). | Left as shipped, arm G's stats would name helper models beside the row's (practice walk w-g5) and the strict identity check (ruling R-B14-3) would refuse the take; pinning them keeps every model call on the measured row. Arm A's code and bytes do not move. | A named difference from arm A on helper models, and a change to arm G's road from its shipped defaults: the row's model serves, and is billed for, helper work the vendor gave other models. Bound by tests/test_take_config.py TestB14HelperPins (each alias entry dropped, an unread model admitted and a helper alias set twice: each red alone); arm A's admission by SIDE_MODELS is unchanged. |

## 7. Open questions

**For Javier:**
1. Is the r4-g study key he placed on 14 Oct still live in AI Studio (not deleted)?
2. The two addresses for the account record: the Codex2 ChatGPT login email, and the email of the Google account that owns r4-g (plus confirmation the operator address is his usual one).
3. The Codex2 sign-in itself (the card above), once B1 and B2 pass review.

**For glitch-b5 (rulings):**
1. D8 B2 item 8's arm O host: `chatgpt.com` for a subscription take (B4).
2. The login's egress: a one-host `auth.openai.com` proxy (recommended) or the default bridge for that one container.
3. The three PENDING config values and whether any walk may run before the vendor config is written (B6).
4. The O and G pin profiles and their marker rules (B7).
5. The gate's order (section 2) and the test assertion it moves (B8).

**Checks this planner could not run (each with the command that settles it, for when athena is free):**
1. The r4-g Gemini key file's state: `ssh athena python3 -I /home/javier/gap4-tools/walk-login/verify_walk_login.py r4-g` (prints yes/no only).
2. The pinned login help and the `-c` acceptance: `docker run --rm --pull=never --network none <take-o image id> codex login --help` (no network, no login).
3. Whether Codex 0.162.1 leaves anything besides `auth.json` in CODEX_HOME after a login: read by verify's `folder holds only auth.json` line on his first sign-in.
4. The access token's lifetime: verify's `access token hours left` line right after his sign-in.
5. Whether Codex in exec mode contacts any host besides `chatgpt.com` (telemetry, update check): the first walk's `proxy.log`, where denials are recorded and fail closed.
