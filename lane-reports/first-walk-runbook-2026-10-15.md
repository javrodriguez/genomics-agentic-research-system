# First walk runbook: claude-haiku-4-5, approval-scope trap w1, arm A (box lane, 15 Oct 2026)

Written 05:31 EDT, clock read first, for glitch-6b.
The walk starts after Claude1 resets at 09:00 EDT, and only on glitch-6b's word.
Nothing in this runbook has been shipped or run.
Every fact is marked as read (with its source) or as **OPEN**.

## 0. What must be true before anything starts

- **The head.** The final pre-walk merge must carry box `fb0c5d98`: the walk's GAP4_CONFIG_PARENT and commit identity.
  Without it, the walk refuses (see section 2).
  **The ship head is `ce818d85f4bd988deb87ff7dfa7abd32a46a9f40`** (glitch-6b, 06:20): box `fb0c5d98` + harness `664a24e7` + bootstrap `253fb094`, on the integration clone's `gap4/live-merge-20261014`.
  - It carries `fb0c5d98` (`merge-base --is-ancestor`).
  - Its `walk_launch.py` and `machine_gate.py` are byte-equal to `fb0c5d98`'s.
  - Its three image locks equal `1cde8066`'s, the stub takes' (`git diff --quiet`, read 06:20).
- **The battery.** The integration lane's solo battery on that exact head, `gap4-merge-prewalk-ce818d8`, PASSED 274/274 (log sha256 `9626ac17…3e24`, as glitch-6b relayed).

## 1. The walk spec

**Read from `walk_plan.py --list`** on the merged tree `26dd61be` (Mac, 05:22). There are 198 required walks. The arm A Haiku model is `claude-haiku-4-5-20251001` (the full id; "every wording of each task and half", 90 walks). Its first line is:

```
walk  A claude-haiku-4-5-20251001 claude-code approval-scope trap w1
```

**The arguments `walk_runner.py` takes** (`walk_builders.parse`): `--walk <id> --task <t> --half <h> --wording <w> --arm <a> --model <m> --reason <why>`. For this walk:

```
--walk w001 --task approval-scope --half trap --wording w1 --arm A --model claude-haiku-4-5-20251001
--reason "CP6 walk (plan 874-876, ruling Q-2): every wording of every task and half on this model; graded, never counted"
```

- **The reason** is walk_plan's `REASON_EVERY`, verbatim. The runner may keep or replace it.
- **The walk id** follows `walk_register.WALK_ID`, `[A-Za-z0-9][A-Za-z0-9._-]*`, one path segment.
  - The id is the runner's to choose; no ruling names a rule for it (walk_plan's docstring).
  - The proposed `w001` is neutral: it names no task, study or arm.
  - The hold id becomes `gap4-walk-w001`, which athena-reserve's BY_RE admits.
  - A retry is a new id (`w002`, …), never the same one (ruling W8-layout-1).
- **The register entry is written by the runner, never by hand.** `walk_runner.run_walks` commits the walk folder `evals/gap-study-4/rehearsals/w001/` and its `rehearsals/register.json` entry in one commit (`WalkRepo.commit_walk`), with `counted: false`.
  The register at `26dd61be` is `{"schema": 1, "walks": []}`.

## 2. The environment on athena

All of it is set by `walk_launch.run_command` (box `fb0c5d98`); nothing is exported by hand. The walk starts under `nohup` over ssh, so only the command's own `env` reaches it.

| Variable | Value | Read by | Checked on athena (as javier, ssh, 05:23-05:30 EDT) |
|---|---|---|---|
| `GAP4_CONFIG_PARENT` | `/home/javier/gap4-walk-config` | `walk_builders.config_parent_from_env` | **Created by this lane, 05:23** (the one write): `javier:javier 700`, in no repository (`git rev-parse` fails). |
| `GAP4_SUITE_ACCOUNT` | `athena-suite` | `machine_gate.gate_from_env` | `getent`: `athena-suite:1106`. |
| `GAP4_RESERVATION` | `/srv/aegis-handoff/machine/reserved.json` | machine_gate, and walk_launch's O_EXCL claim | Folder `javier:javier 755`; the file was absent at 05:23. |
| `GAP4_OWN_HOLD` | `gap4-walk-w001` | machine_gate (own hold, exact id) | Derived from the walk id. |
| `GAP4_SUITE_SLOTS` | `/home/javier/athena-suites/.slots` | machine_gate (flock probe) | `javier 775`, holding `1.lock` to `4.lock`. |
| `GIT_AUTHOR_NAME`, `GIT_COMMITTER_NAME` | `javrodriguez` | `takes.require_commit_identity` (WalkRepo) | javier has **no** global git identity (`git config --global user.name/email` unset, 05:23). |
| `GIT_AUTHOR_EMAIL`, `GIT_COMMITTER_EMAIL` | `28984720+javrodriguez@users.noreply.github.com` | the same | As above. This is the noreply identity, never the gmail one. |

**Read from the ssh environment, never set:**
- `PATH`, `HOME`, and `XDG_RUNTIME_DIR=/run/user/1000` (`run_take.RUNTIME_ENV_NAMES`).
- `umask` is 0002 over ssh, and the run sets 0022 first.

**Deliberately absent** (`walk_launch.RUN_ENV_ABSENT`, each with its reason):
- `DOCKER_HOST`: unset; Docker 29.8.1 is reached through javier's context.
- `CLAUDE_CONFIG_DIR`.
- `GAP4_ATHENA_SUITE` and `GAP4_MACHINE_BOOKING`: no module reads them since fa0838ec.
- `GAP4_ATHENA_SUITE_PY`.
- Every name `run_take` refuses must be absent too: 680 names across the three arms, including `CLAUDE_CODE_MESSAGING_TOKEN`. athena's ssh environment held none of them (02:10).

**Other athena facts read:**
- `id`: javier, groups including `aegis-procview` (984).
- `stat -c %U /proc/1` gives root, so the gate's visibility proof holds.
- python3 3.13.5; Docker server 29.8.1.

## 3. The command sequence, from the Mac

Use plain Terminal or this session, with full paths throughout. `PY=/usr/local/bin/python3.13`. `WL` is the walk_launch.py of the records clone.

**Prepare the records clone at `ce818d85`, once, before the ship.** It is a shared clone of the integration clone, on its own branch at the ship head. The walk's commits come back onto this branch, and the clone is also fetch's records target. It must not exist beforehand: a new folder, never reused.

```
test ! -e /Users/javrodher/aegis-builds/gap4-walk-records-20261015
git clone -q --shared /Users/javrodher/aegis-builds/gap4-live-merge-20261014 /Users/javrodher/aegis-builds/gap4-walk-records-20261015
git -C /Users/javrodher/aegis-builds/gap4-walk-records-20261015 config maintenance.auto false
git -C /Users/javrodher/aegis-builds/gap4-walk-records-20261015 checkout -q -b walk/first-20261015 ce818d85f4bd988deb87ff7dfa7abd32a46a9f40
git -C /Users/javrodher/aegis-builds/gap4-walk-records-20261015 rev-parse HEAD     # must print ce818d85f4bd988deb87ff7dfa7abd32a46a9f40
git -C /Users/javrodher/aegis-builds/gap4-walk-records-20261015 status --short       # must print nothing
WL=/Users/javrodher/aegis-builds/gap4-walk-records-20261015/evals/gap-study-4/box/walk_launch.py
PY=/usr/local/bin/python3.13
```

1. **Ship** (Mac pre-check, outward scan, child, sha256 read-back, athena clone). This prints `{"child": "/home/javier/w-XXXXXXXX", "head": ..., "bundle_sha256": ..., "scanned_commits": ...}`.
   ```
   $PY -B $WL ship --repo /Users/javrodher/aegis-builds/gap4-walk-records-20261015 --ref walk/first-20261015 \
     --suite /Users/javrodher/glitch/workspaces/aegis/ops/athena_suite.py \
     --reserve /Users/javrodher/glitch/workspaces/aegis/ops/node1/athena-reserve \
     --gitleaks /Users/javrodher/.local/bin/gitleaks --work /Users/javrodher/aegis-builds/gap4-walk-work-20261015
   ```
2. **Run.** It claims the reservation, runs the gate, starts the hold and the walk, and checks after 3 s. It prints `{"pid": N}`, or refuses.
   ```
   $PY -B $WL run --child <child> --walk w001 --task approval-scope --half trap --wording w1 --arm A \
     --model claude-haiku-4-5-20251001 \
     --reason "CP6 walk (plan 874-876, ruling Q-2): every wording of every task and half on this model; graded, never counted"
   ```
3. **Status,** every 2 to 5 minutes: `$PY -B $WL status --child <child>`. It prints `running`, then `exit=<code>`, or `lost`.
   walk_runner's codes are: 0 committed; 1 refused at launch or held; 2 refused before anything was built.
4. **Fetch,** only after `exit=`. It takes the new commits only, scanned by athena_suite's `scan_unpublished` with no allowance, then lands them as branch `walk/<child name>` in the records clone.
   ```
   $PY -B $WL fetch --child <child> --head ce818d85f4bd988deb87ff7dfa7abd32a46a9f40 --ref walk/first-20261015 \
     --records /Users/javrodher/aegis-builds/gap4-walk-records-20261015 \
     --gitleaks /Users/javrodher/.local/bin/gitleaks --work /Users/javrodher/aegis-builds/gap4-walk-work-20261015 \
     --suite /Users/javrodher/glitch/workspaces/aegis/ops/athena_suite.py
   ```
5. **Where the records land:** branch `walk/<child name>` of the records clone, folder `evals/gap-study-4/rehearsals/w001/`, plus the register entry. Read them in this order:
   1. `check.json`: the checker's reading (check4's round-4 walk road) and the route routing gives;
   2. `grade.json`: the v4 grade, or "not graded, because …";
   3. `driver-ledger.json`;
   4. `transcript.jsonl`;
   5. `environment.json`: the money line;
   6. the watcher's record. **There is no `watched.json` on `26dd61be`.** The watch is `evidence-ledger-copy.json` (the host copy of the sidecar's `evidence-ledger.jsonl`), beside `settings-guard.json`;
   7. `preflight.json`, `postflight.json`, `teardown.json`, `ownership-grant.json` and `ownership-restore.json`, and `refusal.json` if present.
   - These names are drive.py's record constants (`PREFLIGHT_RECORD` …, `EVIDENCE_LEDGER_COPY`). Which of them a successful walk commits under `rehearsals/w001/` is **OPEN** until the first walk shows it.

## 4. Pre-walk checklist (in order, at the time of the walk)

1. **athena idle.**
   - `$PY -B /Users/javrodher/aegis-builds/gap4-walk-records-20261015/evals/gap-study-4/machine_gate.py mac-precheck /Users/javrodher/glitch/workspaces/aegis/ops/athena_suite.py` prints `gate: OPEN`.
   - Then: `ssh -a -x -o BatchMode=yes athena -- 'echo suite=$(ps -u athena-suite -o pid= | wc -l) runners=$(ps -eo args | grep -c "[a]thena_suite_remote.py work") reserved=$(test -e /srv/aegis-handoff/machine/reserved.json && echo yes || echo no) containers=$(docker ps -aq | wc -l)'`. It must print `suite=0 runners=0 reserved=no containers=0`.
2. **The Claude1 sign-in file.** `ssh -a -x -o BatchMode=yes athena -- python3 -I /home/javier/gap4-tools/walk-login/verify_walk_login.py claude1 | grep '^RESULT'` must print `RESULT: OK`. Read only that line, never the token.
   - **Read at 05:30: `RESULT: OK`.** The script's sha256 on athena is `2e0e624c…`, equal to the committed file. The token file is javier 600, 133 bytes, in a 700 folder (stat only).
3. **Javier's Claude1 usage reading BEFORE the walk (his step).** Signed in as Claude1 at claude.ai, he opens Settings → Usage and reads the session and weekly "% used" and the reset time. He types in his own window one line of exactly this form:
   ```
   Claude1 before w001: session <N>% used, weekly <N>% used, resets <day HH:MM>
   ```
   An after-reading follows the walk in the same form (`Claude1 after w001: …`). The walk waits for the before-line.
4. **The image locks.** The take, sidecar and egress images are present on athena by their lock ids:
   - `sha256:336aa8cd…` (box/image.lock, the Claude take image; the binary sha256 `24972e3b…` is bound in run_take.CLAUDE_BINARY);
   - `sha256:13d0597e…` (sidecar);
   - `sha256:5055a840…` (egress).

   All three were read at 05:23 with `docker image inspect`. The take's own preflight (`image-matches-lock`) re-checks at launch. Also check `git -C /Users/javrodher/aegis-builds/gap4-walk-records-20261015 diff --quiet 1cde8066 ce818d85 -- evals/gap-study-4/box/image.lock evals/gap-study-4/box/sidecar/image.lock evals/gap-study-4/box/egress/image.lock` (the locks the stub takes ran).
5. **The ship's own checks** (done by `ship`): the outward scan is clean, the bundle and athena-reserve sha256 read back (athena-reserve `efeecb3a…`), and athena's clone is at the head.

## 5. Stop rules: stop and ask glitch-6b

- **Any refusal from walk_launch** (`{"refused": …}`), from `ship`, `run` or `fetch`.
- **Status `lost`.**
- **Any walk exit other than 0.**
- **A record that says stop:**
  - `refusal.json` present;
  - `preflight.json` not ok;
  - `postflight.json` failing;
  - `teardown.json` with a problem;
  - an ownership restore not ok;
  - the money line in `environment.json` showing an API-key or billing-route variable set;
  - `check.json`'s route anything but the clean route;
  - `grade.json` "not graded";
  - a per-take config folder left under `/home/javier/gap4-walk-config` (walk_runner keeps it for a human on any unclean drive).
- **Athena left in a bad state:**
  - a reservation left on athena after `exit=` (`reserved.json` present);
  - any container left (`docker ps -aq` not 0).
- **The account:** a Claude1 usage reading near its limit before the walk.
- **No retry without glitch-6b's word.** A failed or refused walk is never retried without it. A retry is always a new walk id, and the failed walk's records stay as they are (never edited).
- **Recovery** after a start that crashed between the claim and the hold: `athena-reserve clear`, as javier on athena, on glitch-6b's word.

## 6. What could not be settled here

1. **Settled 06:20:** the ship head is `ce818d85`, battery PASS 274/274.
2. **The record set** a committed walk carries. `watched.json` does not exist on `26dd61be`; the watch is `evidence-ledger-copy.json`. Confirm on the first walk's commit.
3. **`run`, `status` and `fetch` against the real athena** have run only on fakes and the dry ship. The first walk is their first real use.
4. **The athena child folders:** the walk's child holds the athena repository and its log. It is kept until glitch-6b rules after reading the records.

## 7. Usage readings (recorded here and in the lane report's w001 section)

- **Before w001**, typed by Javier in glitch-6b's window, relayed verbatim at 09:36 EDT on 15 Oct 2026:
  > Claude1 before w001: session 0% used, weekly 0% used, resets Thurs 9 am
- **After w001:** pending. glitch-6b asks Javier for it once the walk ends.
- **After w001**, typed by Javier in glitch-6b's window and relayed verbatim (received between 10:22 and 10:29 EDT):
  > Claude1 after w001: session 0% used, weekly 0% used, resets Thu 9am
  - With 0% before and after, the readings are inconclusive. The records summary will add account evidence and token sums from the committed records.
