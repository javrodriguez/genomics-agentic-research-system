#!/usr/bin/env python3
"""The host side of one take's containers (CP2): the runtime protocol, the take container, the per-harness exec,
the login read, the launch and teardown orders, leaked containers, the agent's leftover processes, the cgroup
counters, the exit record and one turn's exec.

Code only, driven by fakes in wave 4: no image is built and no container is created or run by any test. Every
runtime action here is an argv list handed to a runtime object (`Completed`, `DockerRuntime`, the runtime protocol of
interface 10). `DockerRuntime.run` is the only place in the box that starts a process, with a list argv and
`shell=False`, and it passes the caller's `env` as the client's WHOLE environment.

THE TAKE CONTAINER. One fresh container per take, kept alive by `sleep infinity` as PID 1 under a third uid
(`KEEPALIVE_USER`), with a read-only root filesystem (glitch-b5, 16 Oct 2026) and exactly two bind mounts: the run tree
read-write at the same absolute path as on the host, and the per-take config folder at `CONFIG_MOUNT`; plus the
`TAKE_TMPFS` mounts (/tmp, /var/tmp) and Docker's own /dev/shm. All capabilities dropped, no new privileges, a pids limit, a memory
reservation, a ceiling of exactly three times it, a CPU limit. No environment variable at create, `--pull=never`,
the image by its id. Every agent action is a `docker exec --user AGENT_USER` into it.

THE ENVIRONMENT PER HARNESS (D8 B2 item 10; ruling docs-1, lane w12a: an ALLOWLIST). The agent starts from an empty
environment plus its arm's row of TAKE_ENV, the one table: the launcher inside the container execs the harness with
exactly the row's NAME=VALUE pairs and the credential, which rides as `-e NAME` only, its value only in the client
environment handed to `runtime.run`. A `.env` a harness would read refuses the launch and every turn (refuse_env_files),
and arm G's call names a full pinned model id, never a short alias (check_model). Arm A keeps round 3's refusal of
every API-key and billing-route variable whole (drive.py's three tuples, bound by `ast` in the tests); arms O and G
each admit exactly their own vendor's one variable and refuse every other, Anthropic's included (the named departure
from the drive.py task's GOTCHA, D8 B2 item 7). A take is refused when any refused name is set in the caller's own
environment or requested for the exec.

PENDING (interface 15). A value only the real box or a walk can tell is the constant `PENDING`, listed with its
reason in `PENDING_WHY`; `pending()` names every one still pending, and a real use that needs one raises `NotReady`.
No public function takes a PENDING value as a parameter; the one documented exception is `TakeSpec`'s per-take
resources (capacity policy, passed by the caller), which are refused while they hold the PENDING defaults.

No model, no network, standard library only (plus the seam's `agent_adapter` and `harness_bookkeeping`).
"""

from __future__ import annotations

import dataclasses
import json
import os
import re
import secrets
import shutil
import stat
import subprocess
import sys
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Callable

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import agent_adapter  # noqa: E402
import harness_bookkeeping  # noqa: E402

PENDING = "PENDING"

# ---------------------------------------------------------------------------------------------- shared values
# Merge binding 1: equal to every image.lock's users.agent / users.keepalive uid and gid (w4a).
AGENT_USER = "10001:10001"
KEEPALIVE_USER = "10003:10003"
# Merge binding 3: equal to proxy_conf.ALIAS and proxy_conf.PROXY_URL (w4a).
PROXY_ALIAS = "proxy"
PROXY_URL = "http://proxy:3128"
# The per-take config folder's mount target in the take container (this lane's, interface 11).
CONFIG_MOUNT = "/opt/cfg"
RUNTIME_CLIENT = "docker"
KEEPALIVE_COMMAND = ("sleep", "infinity")
# glitch-b5's ruling on review r15's MAJOR 2 (16 Oct 2026): the take container's root filesystem is read-only. What a
# take writes, from the image and the pinned binaries read statically (the harness lane's r15 report): its two binds
# (the run tree, where TMPDIR points, and the config mount, HOME and CLAUDE_CONFIG_DIR), /dev/shm (Docker's own tmpfs,
# which 2.1.296 opens read-write) and two tmpfs mounts for whatever falls back to /tmp or /var/tmp. A write the root
# breaks shows on the first live walks as an EROFS line, which the driver records (read-only-errors.json).
TMPFS_OPTIONS = "rw,exec,nosuid,nodev,mode=1777"
TAKE_TMPFS = {"/tmp": TMPFS_OPTIONS, "/var/tmp": TMPFS_OPTIONS}
# The runtime's default network, which the proxy alone joins for its own way out.
DEFAULT_NETWORK = "bridge"

# Harness names (interface 11): Claude Code's imported, never typed; the other two typed once each, here.
CLAUDE_CODE = harness_bookkeeping.CLAUDE_CODE
CODEX = "codex"
GEMINI = "gemini"

# The C3 routing names (interface 11, fixed by lane w4h). wait_gone returns the survivors the drive step counts
# into this box key; a non-zero count routes by the row below (after-first-turn, graded: pre-freeze review 1, MAJOR 5).
QUIESCENCE_CAP_SURVIVORS_KEY = "quiescence_cap_survivors"
QUIESCENCE_CAP_ROW = "quiescence-cap-reached"

# ------------------------------------------------------- copies of drive.py's constants (bound by ast in the tests)
ISOLATION_ENV = {"ENABLE_CLAUDEAI_MCP_SERVERS": "false", "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1"}
RUN_TREE_TMPDIR = ".tmp"
RUN_TREE_TMPDIR_VARIABLES = ("TMPDIR", "TMP", "TEMP")
API_KEY_VARIABLES = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_FOUNDRY_API_KEY",
                     "ANTHROPIC_AWS_API_KEY", "CLAUDE_CODE_API_KEY_FILE_DESCRIPTOR", "AWS_BEARER_TOKEN_BEDROCK")
BILLING_ROUTE_VARIABLES = ("CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY",
                           "ANTHROPIC_BASE_URL", "CLAUDE_CODE_API_BASE_URL")
SUBSCRIPTION_TOKEN_VARIABLES = ("CLAUDE_CODE_OAUTH_TOKEN", "CLAUDE_CODE_OAUTH_REFRESH_TOKEN",
                                "CLAUDE_CODE_SESSION_ACCESS_TOKEN")
# The other vendors' key variables (D8 B2 item 7's closed list).
VENDOR_KEY_VARIABLES = ("CODEX_API_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY")
# Installed Gemini 0.64.0 getter: this variable independently enables the ADK path.
# The current independently grounded transcript projection admits the legacy path.
GEMINI_MODE_ROUTE_VARIABLES = ("GEMINI_CLI_EXP_AGENT",)

# THE BASH-FIRST STEER OFF (glitch-6b's study-condition ruling, 15 Oct 2026, approved by Javier's "Your call sounds
# good"). Under bypassPermissions, Claude Code 2.1.296 tells the model "While bypass permissions mode is active:" plus a
# Bash-first steer (an auto_mode attachment, renderedRole system) whenever its gate HXt() holds: the env switch when it
# is set, otherwise a model-keyed cohort (CP6 walk w032, claude-opus-5-5, got it; the Haiku walks did not). The study
# condition is the steer OFF for every claude-code take, whatever the model; the product default is model-dependent
# (a named departure). Read statically from the pinned binary in the take image (docker create --network none +
# docker cp, never run; lane-reports/stub-take-20261015/claude-2.1.296-thrifty-sonic-*.json and
# claude-2.1.296-tribool*.json, bound by tests/test_run_take.py TestBashFirstSteerOff): HXt returns
# a.CLAUDE_CODE_THRIFTY_SONIC whenever it is not undefined; it is declared rE=H.triBool(); triBool is true for Ne's
# list ["1","true","yes","on"] and false for vs's ["0","false","no","off"] (lowercased, trimmed), else undefined. The
# value rides the exec's pairs (the row below) and the inline settings' env (claude_study_settings: the level above the
# run tree's files, and the argv the per-turn launch journal records for the checker's auto_mode rule).
BASH_FIRST_STEER_ENV = {"CLAUDE_CODE_THRIFTY_SONIC": "false"}
# THE SILENT-TURN REMINDER OFF (glitch-b5's parity ruling, 16 Oct 2026; CP6 walks w126, w128 and w130, claude-opus-5-5,
# held). 2.1.296 writes a silent_turn_reminder attachment on the main agent after 5 silent tool-only API turns (at most
# 3 per stretch), default-on for models carrying the opus 5.5 prompt bundle; round 3 (2.1.267 and 2.1.280, which carry
# the path) never received one. Its switch CLAUDE_CODE_SILENT_TURN_REMINDER is a triBool read before every gate (a
# read-only static read of the pinned binary, for glitch-b5): "0" turns it off. It rides the exec's pairs and the
# inline settings' env like the steer's, so every turn's launch journal records it for check_take's condition check.
SILENT_TURN_REMINDER_ENV = {"CLAUDE_CODE_SILENT_TURN_REMINDER": "0"}

# THE ISOLATION DENIALS (glitch-6b's ruling, 15 Oct 2026, under Javier's delegation). RemoteTrigger manages claude.ai
# Routines ("via the claude.ai CCR API"): the one road a take's own login has to work on the account OUTSIDE the box.
# SendMessage and ListAgents are cross-session channels. All three are DISALLOWED for every claude-code take, and
# cross-session inbound messages are refused. None of the 25 walks of 15 Oct called them. The names and values are the
# pinned binary's (lane-reports/stub-take-20261015/claude-2.1.296-isolation-names-20261015.json and
# claude-2.1.296-cross-session-values-20261015.json; docker create --network none + docker cp, never run):
# `var N$="RemoteTrigger"`, `var Gn="SendMessage"`, `var xc="ListAgents"`; `--disallowedTools, --disallowed-tools
# <tools...>` takes a comma or space-separated list; `sHt=["accept","hold","refuse"]`. Defence in depth: the exec argv
# must deny them (check_claude_settings refuses a turn that denies fewer; the adapter builds the flag) AND the inline
# settings carry permissions.deny and crossSessionInbound. Not ruled (left as they are): Cron*, ScheduleWakeup,
# Workflow, the worktree tools, the bundled skills and the two built-in plug-ins.
ISOLATION_DISALLOWED_TOOLS = ("RemoteTrigger", "SendMessage", "ListAgents")
CROSS_SESSION_INBOUND = "refuse"
CLAUDE_DENY_FLAGS = ("--disallowedTools", "--disallowed-tools")

# ------------------------------------------------------------------- THE TAKE ENVIRONMENT (ruling docs-1, w12a)
# An ALLOWLIST, never a blocklist. Every agent process starts from an EMPTY environment (the turn's launcher, below,
# execs the harness with exactly this row and nothing else: not the image's ENV, not docker exec's defaults, not the
# caller's). Each arm's row is the whole of what may reach the agent: PATH, HOME, LANG, the run tree's temporary
# folder, the proxy, the harness's own switches and config home, and the arm's ONE credential, by NAME only (its value
# is read from the login file at exec time and never rides in any argv). A name not in its row never reaches the agent.
# Arm A's HOME is the per-take config mount; arm O's and arm G's is the run tree's own RUN_TREE_HOMEDIR (R-H5, below).
# Either way a `.env` there can be read host-side before launch (refuse_env_files).
TAKE_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
TAKE_LANG = "C.UTF-8"
RUN_TREE_TMP = "<run tree>/.tmp"            # a marker: filled with f"{run_tree}/{RUN_TREE_TMPDIR}" per take
CREDENTIAL = "<credential, by name only>"   # a marker: the arm's one login variable
# R-H5 (glitch-26's ruling on the B11 design note, Mon 19 Oct 2026): arm O's and arm G's HOME is a separate folder the
# agent writes, beside the run tree's temporary folder and granted with the run tree (it is in it, git-excluded like
# .tmp: walk_builders.place_agent_home), so the agent's own tools (git, conda, R, Nextflow, pip and their caches) write
# `~` there, never into the config mount, while CODEX_HOME and GEMINI_CLI_HOME stay on the mount. Arm A's row is
# byte-unchanged (round-3 parity): its HOME stays the mount. A named difference from arm A (prereg-draft box_residuals,
# "arm O and G HOME"; the codex2 sign-in plan's section 6).
RUN_TREE_HOMEDIR = ".home"
RUN_TREE_HOME = "<run tree>/.home"          # a marker: filled with f"{run_tree}/{RUN_TREE_HOMEDIR}" per take
TAKE_ENV = {
    CLAUDE_CODE: {"PATH": TAKE_PATH, "HOME": CONFIG_MOUNT, "LANG": TAKE_LANG,
                  "TMPDIR": RUN_TREE_TMP, "TMP": RUN_TREE_TMP, "TEMP": RUN_TREE_TMP, "HTTPS_PROXY": PROXY_URL,
                  "DISABLE_AUTOUPDATER": "1", "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1", **ISOLATION_ENV,
                  **BASH_FIRST_STEER_ENV, **SILENT_TURN_REMINDER_ENV, "CLAUDE_CONFIG_DIR": CONFIG_MOUNT,
                  "CLAUDE_CODE_OAUTH_TOKEN": CREDENTIAL},
    CODEX: {"PATH": TAKE_PATH, "HOME": RUN_TREE_HOME, "LANG": TAKE_LANG,
            "TMPDIR": RUN_TREE_TMP, "TMP": RUN_TREE_TMP, "TEMP": RUN_TREE_TMP, "HTTPS_PROXY": PROXY_URL,
            "CODEX_HOME": CONFIG_MOUNT},     # no credential: subscriptions only (glitch-06, 14 Oct; the 13 Oct amendment)
    GEMINI: {"PATH": TAKE_PATH, "HOME": RUN_TREE_HOME, "LANG": TAKE_LANG,
             "TMPDIR": RUN_TREE_TMP, "TMP": RUN_TREE_TMP, "TEMP": RUN_TREE_TMP, "HTTPS_PROXY": PROXY_URL,
             "GEMINI_CLI_HOME": CONFIG_MOUNT, "GEMINI_API_KEY": CREDENTIAL},
}
# The base every row carries (bound by the tests); the views below are DERIVED from TAKE_ENV, never declared apart.
BASE_NAMES = ("PATH", "HOME", "LANG")
# Codex has no environment login (glitch-06's ruling 1, 14 Oct 2026): its login is the lease file in CODEX_HOME
# (place_lease), and LOGIN_VARIABLE[CODEX] is the launcher's reserved NO_LOGIN, set below where it is defined. Every
# road that expects an environment login refuses it explicitly (read_login; exec_argv hands Codex to
# _codex_exec_argv behind codex_lease_gate).
LOGIN_VARIABLE = {h: next(k for k, v in row.items() if v == CREDENTIAL) for h, row in TAKE_ENV.items()
                  if CREDENTIAL in row.values()}
# Owner amendment, 13 Oct 2026: Codex must use an isolated ChatGPT subscription.
# The historical API row above is not an admissible route. All execution and
# builder login entry points refuse until the reviewed subscription lease exists.
CODEX_SUBSCRIPTION_NOT_READY = "Codex subscription binding not ready; API-key login is not permitted"
# The Codex lease road's gate (glitch-06, 14 Oct 2026): OPEN since B8 (18 Oct 2026), by ruling R5 of
# lane-reports/RULINGS-codex2-signin-road-2026-10-18.md, in this order: Javier signed in to Codex2 and
# verify_codex_lease.py printed RESULT: OK; B2 to B7 were reviewed and athena's battery was green; Javier confirmed
# Codex2 holds no purchased credits and no automatic top-up; this commit opened it; the first real Codex walk is its
# first use and commits pending-native-reader. Set back to False, every lease step (place_lease, the Codex exec road)
# refuses with NotReady(CODEX_SUBSCRIPTION_NOT_READY).
CODEX_SUBSCRIPTION_READY = True
# Each harness's own non-secret values (its switches, proxy and config home): the row less the base, the run tree's
# temporary folder and the credential. config_home_names() and preflight read this view.
HARNESS_ENV = {h: {k: v for k, v in row.items()
                   if k not in BASE_NAMES and v not in (RUN_TREE_TMP, RUN_TREE_HOME, CREDENTIAL)}
               for h, row in TAKE_ENV.items()}
# The turn's launcher inside the take container: the image's own python3, isolated (-I -S), reads the credential by
# its name from the exec's environment and execs the harness with exactly the row (os.execvpe: PATH from the row).
# Before each harness exec it checks .env names in the actual container cwd, ALL its ancestors, HOME and the row's
# config home (R-H5: for arms O and G, HOME is the run tree's home and the config home the mount).
# R-H5-1 (glitch-26's ruling, Mon 19 Oct 2026): HOME and the config home are two folders, so the walk reads each as its
# own folder and refuses a .env name in or above either, in the order each pinned CLI's own lookup reads them (the
# sources as settings_guard.SOURCES records them, "not guarded here" for both files: the .env, and the .env inside
# .gemini):
#   Codex rust-v0.162.1: CODEX_HOME's .env only (codex-rs/arg0/src/lib.rs 159, load_dotenv before any thread; 305,
#     the .env in CODEX_HOME; utils/home-dir/src/lib.rs 14, find_codex_home reads CODEX_HOME), so CODEX_HOME comes
#     first.
#   Gemini CLI 0.64.0: findEnvFile from the working folder up to / (bundle/chunk-FLKY6NH5.js 16542), each folder's
#     .env inside its .gemini folder first (16546), then its own .env (16551); after /, the .env inside homedir()'s
#     .gemini folder (16560) then homedir()'s own .env (16565), where homedir() is GEMINI_CLI_HOME, else os.homedir()
#     (bundle/chunk-NR7L3FXV.js 252011).
# So the walk is: CODEX_HOME (a codex row), the working folder up to /, each config home, then HOME, each followed by
# its own ancestors (a folder no CLI reads, refused anyway), each folder once, the .env inside .gemini before the
# folder's own .env in each.
# The host-side check below is an early refusal only: a mounted run tree is not the container filesystem root.
# Its arguments: the credential's name, the count of NAME=VALUE pairs, the pairs, then the harness's argv.
# R-H1 (glitch-26's ruling on the B11 design note, Mon 19 Oct 2026): a codex take's run tree is trusted from turn 1
# (take_config places its trust table), and the pinned Codex (rust-v0.162.1) loads a trusted project's config from
# the working folder up to the project root, so for a codex row (the one that carries CODEX_HOME) the launcher also
# refuses, in the working folder and every ancestor up to /, each of CODEX_PROJECT_CONFIG_PATHS:
#   .codex/config.toml  config/src/loader/mod.rs 405-411 (load_project_layers), 1663-1677 (the cwd's ancestors to the
#                       project root), 1682 (dir.join(".codex")) and 1701 (its config.toml)
#   .codex/rules        core/src/exec_policy.rs 54 (RULES_DIR_NAME) and 678-679 (each layer's folder joined "rules")
#   .codex/skills       ext/skills/src/host_roots.rs 25 (SKILLS_DIR_NAME) and 85-91 (a Project layer's skills root)
#   .agents/skills      ext/skills/src/host_roots.rs 24-25 and 154 (each folder from the project root to the cwd)
# R-P (glitch-26's ruling on lane vendor-b11 round 2's question, round 3): two more, read from a trusted project's
# .codex folder (config/src/state.rs 219-226, a Project layer's config folder is its .codex; 239-243 its hooks folder):
#   .codex/hooks.json   hooks/src/engine/discovery.rs 146-148 (each layer's hooks folder) and 339-343 (its hooks.json)
#   .codex/agents       agent-roles/src/loader.rs 75-78 (each layer's config folder joined "agents")
CODEX_PROJECT_CONFIG_PATHS = ((".codex", "config.toml"), (".codex", "rules"), (".codex", "skills"),
                              (".agents", "skills"), (".codex", "hooks.json"), (".codex", "agents"))
# R-N1 (glitch-26, lane vendor-b11 round 3; review NIT 1 of c30234d6): arms O's and G's HOME is the run tree's .home,
# which the agent writes, so before every exec the launcher also refuses, in HOME, each path the pinned CLI of that row
# reads from HOME as configuration (the B11 design note's section 4). Everything else under HOME stays the agent's (H5).
# Codex at rust-v0.162.1 (HOME from dirs::home_dir or $HOME; CODEX_HOME is the config mount):
HOME_CONFIG_PATHS = {
    CODEX: (
        (".agents/skills", "ext/skills/src/host_roots.rs 24-25, 35-36 and 105: a User layer's ~/.agents/skills root"),
        (".agents/plugins/marketplace.json", "core-plugins/src/marketplace.rs 20-25, 307-314 and 479-480: a personal "
                                             "marketplace manifest under HOME"),
        (".agents/plugins/api_marketplace.json", "core-plugins/src/marketplace.rs 20-25, 307-314 and 479-480"),
        (".claude-plugin/marketplace.json", "core-plugins/src/marketplace.rs 20-25, 307-314 and 479-480"),
        (".cursor-plugin/marketplace.json", "core-plugins/src/marketplace.rs 20-25, 307-314 and 479-480"),
        (".cache/codex-runtimes", "core-plugins/src/marketplace_policy.rs 546-552 and 570-572: the primary-runtime "
                                  "marketplace under dirs::cache_dir, ~/.cache with no XDG_CACHE_HOME in the row"),
        (".bashrc", "shell-command/src/startup.rs 22-25 and core/src/shell_snapshot.rs 586-605: the snapshot's login "
                    "shell sources ~/.bashrc, and the snapshot is replayed into every shell command"),
        (".bash_profile", "core/src/shell_snapshot.rs 600-604: a login bash reads the first of ~/.bash_profile, "
                          "~/.bash_login, ~/.profile"),
        (".bash_login", "core/src/shell_snapshot.rs 600-604: a login bash's profile file"),
        (".profile", "core/src/shell_snapshot.rs 600-604: a login bash's profile file"),
        (".zshrc", "shell-command/src/startup.rs 11-19: the snapshot sources $ZDOTDIR or ~/.zshrc for a zsh shell"),
        (".zprofile", "core/src/shell_snapshot.rs 600-604: a login zsh's start file"),
        (".zshenv", "core/src/shell_snapshot.rs 600-604: every zsh's start file"),
        (".zlogin", "core/src/shell_snapshot.rs 600-604: a login zsh's start file"),
    ),
    # Gemini CLI 0.64.0 keys everything on GEMINI_CLI_HOME (the config mount) but this one (the B11 design note):
    GEMINI: (
        (".gemini/policies/sandbox.toml", "bundle/chunk-NR7L3FXV.js 257794: the sandbox policy, read from the OS "
                                          "home (sandbox mode only; refused anyway)"),
    ),
}
LAUNCHER_SOURCE = ("import os,sys\n"
                   "a=sys.argv[1:]\n"
                   "k,n=a[0],int(a[1])\n"
                   "e=dict(x.split('=',1) for x in a[2:2+n])\n"
                   "if k!='-':e[k]=os.environ[k]\n"
                   "def walk(d):\n"
                   " r=[]\n"
                   " while True:\n"
                   "  r.append(d)\n"
                   "  parent=os.path.dirname(d)\n"
                   "  if parent==d: break\n"
                   "  d=parent\n"
                   " return r\n"
                   "up=walk(os.getcwd())\n"
                   "homes=[e[v] for v in ('CLAUDE_CONFIG_DIR','CODEX_HOME','GEMINI_CLI_HOME') if v in e]\n"
                   "starts=([e['CODEX_HOME']] if 'CODEX_HOME' in e else [])+[os.getcwd()]+homes+[e['HOME']]\n"
                   "dirs=[]\n"
                   "for s in starts:\n"
                   " for d in walk(s):\n"
                   "  if d not in dirs: dirs.append(d)\n"
                   "for d in dirs:\n"
                   " for name in (os.path.join('.gemini','.env'),'.env'):\n"
                   "  p=os.path.join(d,name)\n"
                   "  if os.path.lexists(p): raise SystemExit('refusing .env file: '+p)\n"
                   "if 'CODEX_HOME' in e:\n"
                   " found=[p for d in up for p in (os.path.join(d,'.codex','config.toml'),"
                   "os.path.join(d,'.codex','rules'),os.path.join(d,'.codex','skills'),"
                   "os.path.join(d,'.agents','skills'),os.path.join(d,'.codex','hooks.json'),"
                   "os.path.join(d,'.codex','agents')) if os.path.lexists(p)]\n"
                   " if found: raise SystemExit('refusing codex project config: '+found[0])\n"
                   f"for v,ps in (('CODEX_HOME',{tuple(p for p, _s in HOME_CONFIG_PATHS[CODEX])!r}),"
                   f"('GEMINI_CLI_HOME',{tuple(p for p, _s in HOME_CONFIG_PATHS[GEMINI])!r})):\n"
                   " if v in e:\n"
                   "  found=[os.path.join(e['HOME'],p) for p in ps if os.path.lexists(os.path.join(e['HOME'],p))]\n"
                   "  if found: raise SystemExit('refusing harness configuration in HOME: '+found[0])\n"
                   "c=a[2+n:]\n"
                   "os.execvpe(c[0],c,e)\n")
LAUNCHER = ("/usr/bin/python3", "-I", "-S", "-c", LAUNCHER_SOURCE)
# glitch-06's ruling (14 Oct 2026), the Codex lease road: LAUNCHER_SOURCE is supplied at run time (the exec's argv),
# never baked into the image, so it carries one variant. The reserved name NO_LOGIN, which no variable NAME can be,
# copies no credential into the agent's environment; launcher_argv admits it only for a Codex row behind the closed
# lease gate (codex_lease_gate). Every other road still copies its one credential by name.
NO_LOGIN = "-"
if CREDENTIAL in TAKE_ENV[CODEX].values():
    raise RuntimeError("the Codex row carries an environment credential: subscriptions only")
# The review of 9d4bfd40, NIT 6: no Codex-row name is a key, API-key or subscription-token variable.
_CODEX_ROW_KEYS = sorted(set(TAKE_ENV[CODEX]) & (set(VENDOR_KEY_VARIABLES) | set(API_KEY_VARIABLES)
                                                 | set(SUBSCRIPTION_TOKEN_VARIABLES)))
if _CODEX_ROW_KEYS:
    raise RuntimeError(f"the Codex row names a key or token variable: {', '.join(_CODEX_ROW_KEYS)}")
LOGIN_VARIABLE[CODEX] = NO_LOGIN

# The model each arm's call names, where the harness has short aliases that resolve elsewhere (docs read 13 Oct 2026:
# Gemini CLI v0.63.0 docs/cli/cli-reference.md, its alias table; `flash-lite` resolves to gemini-2.5-flash-lite).
# Arm G passes a full pinned id on every call, never a short alias; an alias is refused by its name.
MODEL_PINS = {
    GEMINI: {"client": "gemini", "flags": ("-m", "--model"),
             "models": ("gemini-3.8-flash", "gemini-3.5-flash-lite"),
             "short_aliases": {"auto": "gemini-2.5-pro or gemini-3-pro-preview",
                               "pro": "gemini-2.5-pro or gemini-3-pro-preview",
                               "flash": "gemini-2.5-flash", "flash-lite": "gemini-2.5-flash-lite"}},
}
# The files a harness would load variables from, read in every folder from the working folder up to the box root (the
# run tree) and in HOME (Gemini CLI v0.63.0 docs/reference/configuration.md: the working folder, its parents up to
# the project root or home, then ~/.env; `.gemini/.env` is that loader's other name). Refused for every arm.
ENV_FILE_NAMES = (".env", os.path.join(".gemini", ".env"))
# Claude Code's refusal-fallback and model-fallback variables: {name: value} once confirmed at the pinned version.
# FILLED 14 Oct 2026 (glitch-06's ruling from the official docs, codex-0.162.1-rollout-audit.md Addendum D):
# code.claude.com/docs/en/env-vars.md (sha256 a439ceb1...): "Set to `1` to turn off the automatic model switch when a
# safety classifier flags a request"; the name is in the pinned 2.1.296 binary (stub-take-20261014/
# claude-fallback-probe-20261014.json, claude-settings-names-probe-20261014.json). Only the documented, relevant one:
# NO_MODEL_FALLBACK, REFUSAL_FALLBACK_CATCH_ALL and DISABLE_REFUSAL_RETRY are undocumented; LEGACY_MODEL_REMAP (Opus 4
# and 4.1 pins), MODEL_ACCESS_FALLBACK (Bedrock and Agent Platform) and NONSTREAMING (transport) do not apply. The
# study's settings ride inline by --settings (CLAUDE_SETTINGS_FLAG, below), and exec_argv refuses --fallback-model.
# Named residual: the docs do not say whether the variable covers a subagent re-running a flagged request; routing
# compares each turn's init model with the pin, and the served-model check over every message is the harness lane's.
FALLBACK_ENV = {"CLAUDE_CODE_DISABLE_REFUSAL_FALLBACK": "1"}
# Claude Code's availability-fallback flag (on only if configured: model-config.md, "Fallback model chains").
FALLBACK_MODEL_FLAG = "--fallback-model"
# The study's Claude Code settings, one take (glitch-06's ruling on review finding 1, 14 Oct 2026). Every turn runs
# --setting-sources project,local, so the user scope (the config folder) never loads, and the project and local files
# sit in the agent-owned run tree. The settings therefore ride INLINE in the exec argv, `--settings <json>`
# (claude 2.1.296 --help: "--settings <file-or-json>  Path to a settings JSON file or a JSON string"), which is the
# command-line level, above local and project and below managed (docs settings.md, "Settings precedence", sha256
# a8cc395a..., read 14 Oct 2026). Inline, not a file on a third mount: the take keeps exactly its two mounts.
#   switchModelsOnFlag false   a safety-flagged request in a -p run ends as an error instead of switching
#   fallbackModel []           the chain is taken whole from the highest file that defines it: here, none
#   availableModels [model]    the take's pinned model only (non-managed lists merge, so box/settings_guard.py also
#                              refuses a run tree whose settings files carry the key)
#   env                        FALLBACK_ENV and BASH_FIRST_STEER_ENV again, at a level above the run tree's files
CLAUDE_SETTINGS_FLAG = "--settings"
# The walk tokens' files on athena (box lane, 14 Oct 2026; the CP2 hands card's "separately prepared protected Athena
# file for that account"). One file per account, in a folder of its own: /home/javier/gap4-secrets/<account>/, mode 700,
# the file mode 600, owned by javier (the user that runs the driver and so reads it, read_login's owner rule), outside
# every repository, every run tree and every per-take config folder (those sit under the walk's own folders;
# exec_argv's check_login_place refuses a login file inside the run tree, with another link, or in a folder that is not
# the reading user's own mode-700 folder). Its one line is `CLAUDE_CODE_OAUTH_TOKEN=<the token from claude
# setup-token>`, the variable Claude Code reads in a -p run (code.claude.com/docs/en/authentication, "Generate a
# long-lived token" and "Authentication precedence" item 5; env-vars.md). Prepared and verified by
# lane-reports/walk-login/prepare_walk_login.py and verify_walk_login.py; the value is never read by any session.
# The Gemini key road (glitch-06, 14 Oct 2026), the same road: account alias r4-g (Javier's Google project label from the
# plan), one line `GEMINI_API_KEY=<the study key>`, the variable the Gemini arm's row names; prepared and verified by
# the same two scripts.
WALK_LOGIN_FILES = {"claude1": "/home/javier/gap4-secrets/claude1/claude-walk-token",
                    "r4-g": "/home/javier/gap4-secrets/r4-g/gemini-walk-login"}
# The Codex lease source (lane vendor-admission round 17 B2; plan codex2-signin-road section 1): account alias codex2,
# Javier's Codex2 ChatGPT login, the auth.json Codex writes under CODEX_HOME when cli_auth_credentials_store is "file",
# in its own mode-700 account folder beside WALK_LOGIN_FILES' (so walk_builders.account_emails_path still finds one
# private folder). Never a WALK_LOGIN_FILES entry: that map holds one-line NAME=value files read by read_login. Read only
# by place_lease, behind codex_lease_gate; the value is never read by any session.
LEASE_SOURCES = {"codex2": "/home/javier/gap4-secrets/codex2/auth.json"}

# The bypass acceptance: RULED not required in -p (glitch-06, 14 Oct 2026, on the docs read in Addendum E of
# gap4-codex-rollout-audit-20261014/codex-0.162.1-rollout-audit.md). The study sends NO bypass acceptance key.
#   https://code.claude.com/docs/en/permission-modes.md (sha256 1930f91d012559bd045f5b63b9fdd9881e382043efc7012bfc0e1c9213f9a2d5,
#   line 603): "In non-interactive mode no dialog is shown." The dialog is shown "the first time you start an
#   interactive session with this mode enabled" (line 598); the recorded acceptance is required only for --bg sessions.
#   https://code.claude.com/docs/en/settings-reference.md (sha256 2db996847f31ad322a4eff57aa8a1e5ca4618701fd1caf2191327a3922be095c,
#   lines 1733-1748): the key is `skipDangerousModePermissionPrompt`, valid only in "User, local, or managed" settings.
# The ruling depends on every Claude Code turn being a -p (--print) run and never --bg: check_claude_settings refuses
# a turn that is not `claude` with -p or --print first, and a turn carrying --bg or --background. Unverified until the first walk: that
# the pinned 2.1.296 binary behaves as the live docs say (the lane report's first-walk acceptance checks).
# take_config.CLAUDE_BYPASS_KEY is the same value (a test binds them).
CLAUDE_BYPASS_NOT_REQUIRED = "RULED: not required in -p"
CLAUDE_BYPASS_KEY = CLAUDE_BYPASS_NOT_REQUIRED
CLAUDE_BYPASS_RULING = {
    "value": CLAUDE_BYPASS_NOT_REQUIRED, "ruled_by": "glitch-06", "ruled_on": "2026-10-14",
    "sources": (("https://code.claude.com/docs/en/permission-modes.md",
                 "1930f91d012559bd045f5b63b9fdd9881e382043efc7012bfc0e1c9213f9a2d5",
                 "In non-interactive mode no dialog is shown."),
                ("https://code.claude.com/docs/en/settings-reference.md",
                 "2db996847f31ad322a4eff57aa8a1e5ca4618701fd1caf2191327a3922be095c",
                 "skipDangerousModePermissionPrompt: User, local, or managed")),
    "depends_on": "every Claude Code turn is a -p (--print) run, never --bg",
}
# The documented key the study must never send (a test and check_claude_settings refuse it in the inline settings).
CLAUDE_BYPASS_DOC_KEY = "skipDangerousModePermissionPrompt"
CLAUDE_PRINT_FLAGS = ("-p", "--print")
# --bg and its long alias --background (review-bypass-skills B-1), each refused bare or as `flag=value`.
CLAUDE_BACKGROUND_FLAGS = ("--bg", "--background")
# The program a claude-code turn runs (review-bypass-skills B-2): `claude`, or an absolute path whose basename is
# `claude`, as Gemini's client check does; so the -p rule binds the program as well as the position.
CLAUDE_CLIENT = "claude"
# --bare skips the OAuth token the walk logs in with ("Bare mode does not read CLAUDE_CODE_OAUTH_TOKEN"): refused.
CLAUDE_BARE_FLAG = "--bare"
# Arms O and G's own billing-route variables (a Vertex switch for Gemini CLI, for example): a tuple of names each,
# named from the harness's documentation at the pinned version. Until then the refused set is the closed list above,
# and an exec of either harness is refused (NotReady): this lane's stricter reading.
# CODEX FILLED 14 Oct 2026 (glitch-06's ruling 3), from the pinned Codex binary's own strings only
# (lane-reports/live-box-evidence-2026-10-13/codex-auth-binary-markers.json, committed in 72239cd4, sha256
# f7cfa2621e22c1a6f2b150ac00f14bef3e227fcc46d62e8e1fd2958f8cea3323; sources[0].matches[N].context; the strings
# run together, so each name ends at the next CODEX_/OPENAI_ prefix or a lower-case byte). Refused if present, like
# every other vendor's names. What the evidence cannot settle is listed in the lane report, never guessed.
# The pinned Codex binary's environment-name sweep (glitch-06, 14 Oct 2026): every credential, route (billing, endpoint,
# proxy, trust-store or sandbox switch) and ambiguous name its strings carry, the non-prefixed names glued to them
# included (the review of 06775d56, MINOR 3), refused if present for every arm.
# Source: lane-reports/stub-take-20261014/probes/codex-env-name-classification-20261014.json (sha256 c0cbb46d...), the
# deterministic classification of codex-env-name-sweep-athena-20261014.json (sha256 ddb31eec...), the sweep of the
# binary sha256 628e35487d888a28... copied out of the pinned take-o image; test_run_take binds this tuple to that file.
CODEX_BINARY_SWEEP_REFUSED = (
    "AWS_ACCESS_KEY_ID", "AWS_ACCOUNT_ID", "AWS_ACCOUNT_IDE", "AWS_ACCOUNT_ID_ENDPOINT_MODE",
    "AWS_AUTH_SCHEME_PREFERENCE", "AWS_BEARER_TOKEN_BEDROCK", "AWS_CONFIG_FILE", "AWS_CONTAINER_AUTHORIZATION_TOKEN",
    "AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE", "AWS_CONTAINER_CREDENTIALS_FULL_URI",
    "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI", "AWS_DEFAULT_REGION", "AWS_DEFAULT_REGIONA", "AWS_DEFAULT_REGIONU",
    "AWS_EC2_METADATA_DISABLED", "AWS_EC2_METADATA_SERVICE_ENDPOINT", "AWS_EC2_METADATA_SERVICE_ENDPOINT_MODE",
    "AWS_ENDPOINT_URL", "AWS_IGNORE_CONFIGURED_ENDPOINT_URLS", "AWS_LOGIN_CACHE_DIRECTORY", "AWS_PROFILE",
    "AWS_REGION", "AWS_REGIONG", "AWS_ROLE_ARN", "AWS_ROLE_SESSION_NAME", "AWS_SECRET_ACCESS_KEY",
    "AWS_SECRET_ACCESS_KEYN", "AWS_SERVICE", "AWS_SESSION_TOKEN", "AWS_SHARED_CREDENTIALS_FILE", "AWS_SIGV4",
    "AWS_SIGV4S", "AWS_USE_DUALSTACK_ENDPOINT", "AWS_USE_FIPS_ENDPOINT", "AWS_WEB_IDENTITY_TOKEN_FILE",
    "AZURE_CLIENT_SECRET", "AZURE_FEDERATED_TOKEN_FILE", "BUNDLE_SSL_CA_CERT", "CARGO_HTTP_CAINFO",
    "CODEX_ACCESS_TOKEN", "CODEX_AGENT_IDENTITY_AUTHAPI_BASE_URL", "CODEX_AGENT_IDENTITY_JWKS_BASE_URL",
    "CODEX_API_KEY", "CODEX_APP_SERVER_CHATGPT_BASE_URL", "CODEX_APP_SERVER_LOGIN_CLIENT_ID",
    "CODEX_APP_SERVER_LOGIN_ISSUER", "CODEX_APP_SERVER_LOGIN_ISSUERA", "CODEX_AUTH", "CODEX_AUTHAPI_BASE_URL",
    "CODEX_CA_CERTIFICATE", "CODEX_CLOUD_TASKS_BASE_URL", "CODEX_CLOUD_TASKS_FORCE_INTERNAL",
    "CODEX_CONNECTORS_TOKEN", "CODEX_DAEMON_TELEMETRY_HANDOFF", "CODEX_ESCALATE_SOCKET",
    "CODEX_EXEC_SERVER_NOISE_AUTH_TOKEN", "CODEX_EXEC_SERVER_NOISE_CHATGPT_ACCOUNT_ID",
    "CODEX_EXEC_SERVER_NOISE_CHATGPT_ACCOUNT_IDN", "CODEX_EXEC_SERVER_NOISE_ENVIRONMENT_ID",
    "CODEX_EXEC_SERVER_NOISE_REGISTRY_URL", "CODEX_EXEC_SERVER_PROXY_PRIVATE_IPS_VIA_UPSTREAM",
    "CODEX_EXEC_SERVER_URL", "CODEX_GITHUB_PERSONAL_ACCESS_TOKEN", "CODEX_GUARDIAN_DECISIONS_API_KEY",
    "CODEX_INTERNAL_APP_SERVER_REMOTE_CONTROL_DISABLED", "CODEX_INTERNAL_ORIGINATOR_OVERRIDE",
    "CODEX_NETWORK_ALLOW_LOCAL_BINDING", "CODEX_NETWORK_POLICY_VIOLATION", "CODEX_NETWORK_PROXY_ACTIVE",
    "CODEX_NETWORK_PROXY_ATTRIBUTION", "CODEX_NETWORK_PROXY_BROKERED_CREDENTIALS",
    "CODEX_NETWORK_PROXY_CREDENTIAL_BROKER_ACTIVE", "CODEX_NETWORK_PROXY_SNAPSHOT_BROKERED_UNSET_",
    "CODEX_NETWORK_PROXY_SNAPSHOT_BROKERED_VALUE_", "CODEX_NETWORK_PROXY_SNAPSHOT_ORIGINAL_BASH_ENV",
    "CODEX_NETWORK_PROXY_SNAPSHOT_ORIGINAL_POSIX_ENV", "CODEX_NETWORK_PROXY_SNAPSHOT_ORIGINAL_ZDOTDIR__",
    "CODEX_OSS_BASE_URL", "CODEX_OSS_PORT", "CODEX_PERMISSION", "CODEX_PERMISSION_PROFILE",
    "CODEX_REFRESH_TOKEN_URL_OVERRIDE", "CODEX_REVOKE_TOKEN_URL_OVERRIDE", "CODEX_SANDBOX",
    "CODEX_SANDBOX_NETWORK_DISABLED", "CODEX_SNAPSHOT_BROKER_XTRACE", "CODEX_SNAPSHOT_OVERRIDE",
    "CODEX_SNAPSHOT_PROXY_ENV_SET", "CODEX_SNAPSHOT_PROXY_OVERRIDE", "CURL_CA_BUNDLE", "ELECTRON_GET_USE_PROXY",
    "EXEC_WRAPPER", "GIT_SSL_CAINFO", "GOOGLE_APPLICATION_CREDENTIALS", "HTTP_PROXY", "NODE_EXTRA_CA_CERTS",
    "NODE_REPL_AUTH_TOKEN", "NODE_USE_ENV_PROXY", "OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_CLUSTER",
    "OPENAI_FEDERATION_RULE_ID", "OPENAI_IDENTITY_TOKEN_FILE", "OPENAI_ORGANIZATION",
    "OPENAI_WORKLOAD_IDENTITY_CONTEXT", "REQUESTS_CA_BUNDLE", "REQUEST_DISPATCH_MODE", "SSL_CERT_DIR",
    "SSL_CERT_FILE",)
# The pinned Gemini CLI's environment-name sweep (glitch-06, 14 Oct 2026): every credential, route (billing, endpoint,
# proxy, trust-store, sandbox, model, settings or telemetry-egress switch) and ambiguous name the package (0.64.0, its
# dependencies included) reads or names, refused if present for every arm; GEMINI_API_KEY stays the Gemini arm's own
# login and every row's own names stay out. Source: lane-reports/stub-take-20261014/probes/
# gemini-env-name-classification-20261014.json (sha256 0a364720...), the deterministic classification of
# gemini-env-name-sweep-athena-20261014.json (sha256 fc80791d...); test_run_take binds this tuple to that file.
GEMINI_PACKAGE_SWEEP_REFUSED = (
    "ANTIGRAVITY_CLI_ALIAS", "AWS_ACCESS_KEY_ID", "AWS_ACCOUNT", "AWS_DEFAULT_REGION",
    "AWS_EC2_METADATA_IPV4_ADDRESS", "AWS_EC2_METADATA_IPV6_ADDRESS", "AWS_REGION", "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN", "AZURE_CLIENT_ID", "AZURE_TENANT_ID", "BUILD_SANDBOX", "CLOUDSDK_CONFIG",
    "CLOUDSDK_CONFIG_DIRECTORY", "CLOUD_RUN_JOB", "CLOUD_SHELL", "CLOUD_SHELL_VERSION", "CODE_ASSIST_API_VERSION",
    "CODE_ASSIST_ENDPOINT", "CRUX_API_KEY", "DEBUG_AUTH", "DETECT_GCP_RETRIES", "DOTENV_KEY",
    "EDITOR_IN_CLOUD_SHELL", "EDITOR_URL", "FUNCTION_NAME", "FUNCTION_REGION", "FUNCTION_TARGET", "GAE_MODULE_NAME",
    "GAE_MODULE_VERSION", "GAE_SERVICE", "GAE_VERSION", "GCE_METADATA_HOST", "GCE_METADATA_IP", "GCLOUD_PROJECT",
    "GCLOUD_SANDBOX_ENV", "GCP_VERTEX_AI", "GEMINI_API_KEY_AUTH_MECHANISM", "GEMINI_CLI_ACTIVITY_LOG_TARGET",
    "GEMINI_CLI_API_ERROR_MODEL", "GEMINI_CLI_API_REQUEST_MODEL", "GEMINI_CLI_API_RESPONSE_CACHED_TOKEN_COUNT",
    "GEMINI_CLI_API_RESPONSE_INPUT_TOKEN_COUNT", "GEMINI_CLI_API_RESPONSE_MODEL",
    "GEMINI_CLI_API_RESPONSE_OUTPUT_TOKEN_COUNT", "GEMINI_CLI_API_RESPONSE_THINKING_TOKEN_COUNT",
    "GEMINI_CLI_API_RESPONSE_TOOL_TOKEN_COUNT", "GEMINI_CLI_AUTH_OVERRIDE", "GEMINI_CLI_AUTH_TYPE",
    "GEMINI_CLI_BILLING_CREDITS_CONSUMED", "GEMINI_CLI_BILLING_CREDITS_REMAINING",
    "GEMINI_CLI_BILLING_CREDIT_BALANCE", "GEMINI_CLI_BILLING_MODEL", "GEMINI_CLI_BILLING_PURCHASE_SOURCE",
    "GEMINI_CLI_BILLING_SELECTED_OPTION", "GEMINI_CLI_COMPRESSION_TOKENS_AFTER",
    "GEMINI_CLI_COMPRESSION_TOKENS_BEFORE", "GEMINI_CLI_CUSTOM_HEADERS", "GEMINI_CLI_EXPERIMENT_IDS",
    "GEMINI_CLI_EXP_AGENT", "GEMINI_CLI_EXTENSION_DISABLE_SETTING_SCOPE",
    "GEMINI_CLI_EXTENSION_ENABLE_SETTING_SCOPE", "GEMINI_CLI_EXTENSION_REGISTRY_URI",
    "GEMINI_CLI_FILE_OPERATION_EXTENSION", "GEMINI_CLI_FILE_OPERATION_LINES", "GEMINI_CLI_FILE_OPERATION_MIMETYPE",
    "GEMINI_CLI_FILE_OPERATION_TYPE", "GEMINI_CLI_GOOGLE_ACCOUNTS_COUNT", "GEMINI_CLI_IDE_AUTH_TOKEN",
    "GEMINI_CLI_IDE_PID", "GEMINI_CLI_IDE_SERVER_PORT", "GEMINI_CLI_IDE_SERVER_STDIO_ARGS",
    "GEMINI_CLI_IDE_SERVER_STDIO_COMMAND", "GEMINI_CLI_IDE_WORKSPACE_PATH", "GEMINI_CLI_INTEGRATION_TEST",
    "GEMINI_CLI_KEYCHAIN_AVAILABLE", "GEMINI_CLI_KEY_UNKNOWN", "GEMINI_CLI_LLM_LOOP_CHECK_MAIN_MODEL",
    "GEMINI_CLI_LLM_LOOP_CHECK_MAIN_MODEL_CONFIDENCE", "GEMINI_CLI_LOOP_DETECTED_CONFIRMED_BY_MODEL",
    "GEMINI_CLI_MALFORMED_JSON_RESPONSE_MODEL", "GEMINI_CLI_MODEL_SLASH_COMMAND",
    "GEMINI_CLI_RESEARCH_CONTACT_EMAIL", "GEMINI_CLI_ROUTING_CLASSIFIER_THRESHOLD", "GEMINI_CLI_ROUTING_DECISION",
    "GEMINI_CLI_ROUTING_DECISION_SOURCE", "GEMINI_CLI_ROUTING_FAILURE", "GEMINI_CLI_ROUTING_FAILURE_REASON",
    "GEMINI_CLI_ROUTING_LATENCY_MS", "GEMINI_CLI_ROUTING_NUMERICAL_ENABLED", "GEMINI_CLI_ROUTING_REASONING",
    "GEMINI_CLI_START_SESSION_API_KEY_ENABLED", "GEMINI_CLI_START_SESSION_EMBEDDING_MODEL",
    "GEMINI_CLI_START_SESSION_MODEL", "GEMINI_CLI_START_SESSION_SANDBOX",
    "GEMINI_CLI_START_SESSION_TELEMETRY_ENABLED", "GEMINI_CLI_START_SESSION_TELEMETRY_LOG_USER_PROMPTS_ENABLED",
    "GEMINI_CLI_START_SESSION_VERTEX_API_ENABLED", "GEMINI_CLI_SURFACE", "GEMINI_CLI_SYSTEM_DEFAULTS_PATH",
    "GEMINI_CLI_SYSTEM_SETTINGS_PATH", "GEMINI_CLI_TEST_VAR", "GEMINI_CLI_TOKEN_STORAGE_FORCED",
    "GEMINI_CLI_TOKEN_STORAGE_TYPE", "GEMINI_CLI_TOOL_OUTPUT_MASKING_TOKENS_AFTER",
    "GEMINI_CLI_TOOL_OUTPUT_MASKING_TOKENS_BEFORE", "GEMINI_CLI_TOOL_OUTPUT_MASKING_TOTAL_PRUNABLE_TOKENS",
    "GEMINI_CLI_TRUSTED_FOLDERS_PATH", "GEMINI_CLI_TRUST_WORKSPACE", "GEMINI_CLI_USER_SETTINGS",
    "GEMINI_CLI_USE_COMPUTE_ADC", "GEMINI_CONTEXT_TRACE_DIR", "GEMINI_DEBUG_LOG_FILE", "GEMINI_DEFAULT_AUTH_TYPE",
    "GEMINI_DIR", "GEMINI_EXP", "GEMINI_FORCE_ENCRYPTED_FILE_STORAGE", "GEMINI_FORCE_FILE_STORAGE",
    "GEMINI_IGNORE_FILE_NAME", "GEMINI_MODEL", "GEMINI_MODEL_ALIAS_AUTO", "GEMINI_MODEL_ALIAS_FLASH",
    "GEMINI_MODEL_ALIAS_FLASH_LITE", "GEMINI_MODEL_ALIAS_PRO", "GEMINI_PLANS_DIR", "GEMINI_PROJECT_DIR",
    "GEMINI_RESTRICTED_MODE", "GEMINI_SANDBOX", "GEMINI_SANDBOX_IMAGE", "GEMINI_SANDBOX_PROXY_COMMAND",
    "GEMINI_SYSTEM_MD", "GEMINI_TELEMETRY_ENABLED", "GEMINI_TELEMETRY_LOG_PROMPTS", "GEMINI_TELEMETRY_OTLP_ENDPOINT",
    "GEMINI_TELEMETRY_OTLP_PROTOCOL", "GEMINI_TELEMETRY_OUTFILE", "GEMINI_TELEMETRY_TARGET",
    "GEMINI_TELEMETRY_TRACES_ENABLED", "GEMINI_TELEMETRY_USE_CLI_AUTH", "GEMINI_TELEMETRY_USE_COLLECTOR",
    "GEMINI_WRITE_SYSTEM_MD", "GITHUB_TOKEN", "GOOGLE_ACCOUNTS_FILENAME", "GOOGLE_AI_API_DEFAULT_VERSION",
    "GOOGLE_API_CERTIFICATE_CONFIG", "GOOGLE_API_CLIENT_HEADER", "GOOGLE_API_KEY", "GOOGLE_API_KEY_HEADER",
    "GOOGLE_API_USE_CLIENT_CERTIFICATE", "GOOGLE_API_USE_MTLS_ENDPOINT", "GOOGLE_APPLICATION_CREDENTIALS",
    "GOOGLE_CLOUD_ACCESS_TOKEN", "GOOGLE_CLOUD_ACCOUNT", "GOOGLE_CLOUD_LOCATION", "GOOGLE_CLOUD_PROJECT",
    "GOOGLE_CLOUD_PROJECT_ID", "GOOGLE_CLOUD_QUOTA_PROJECT", "GOOGLE_CLOUD_REGION", "GOOGLE_CLOUD_UNIVERSE_DOMAIN",
    "GOOGLE_CLOUD_WORKSTATIONS", "GOOGLE_CREDENTIALS", "GOOGLE_EXTERNAL_ACCOUNT_ALLOW_EXECUTABLES",
    "GOOGLE_EXTERNAL_ACCOUNT_AUDIENCE", "GOOGLE_EXTERNAL_ACCOUNT_IMPERSONATED_EMAIL",
    "GOOGLE_EXTERNAL_ACCOUNT_INTERACTIVE", "GOOGLE_EXTERNAL_ACCOUNT_OUTPUT_FILE",
    "GOOGLE_EXTERNAL_ACCOUNT_TOKEN_TYPE", "GOOGLE_GEMINI_BASE_URL", "GOOGLE_GENAI_API_VERSION",
    "GOOGLE_GENAI_USE_GCA", "GOOGLE_GENAI_USE_VERTEXAI", "GOOGLE_GRANT_TYPE", "GOOGLE_REVOKE_TOKEN_URL",
    "GOOGLE_SERVICE_ACCOUNT_AUTH", "GOOGLE_TOKEN_INFO_URL", "GOOGLE_TOKEN_URL", "GOOGLE_VERTEX_BASE_URL",
    "GRPC_DEFAULT_SSL_ROOTS_FILE_PATH", "GRPC_NODE_USE_ALTERNATIVE_RESOLVER", "GRPC_SSL_CIPHER_SUITES", "HTTP_PROXY",
    "K_CONFIGURATION", "K_REVISION", "K_SERVICE", "LOG_TOKENS", "METADATA_SERVER_DETECTION", "NODE_OPTIONS",
    "NO_PROXY", "OAUTH_CALLBACK_HOST", "OAUTH_CALLBACK_PORT", "OTEL_EXPORTER_OTLP_HEADERS",
    "OTEL_EXPORTER_PROMETHEUS_HOST", "OTEL_EXPORTER_PROMETHEUS_PORT", "OTLP_GOOGLE_CLOUD_PROJECT",
    "RATE_LIMIT_ERROR_MESSAGE_VERTEX", "REQUIRED_VERTEX_AI_SCOPE", "SANDBOX", "SANDBOX_ENV", "SANDBOX_FLAGS",
    "SANDBOX_MOUNTS", "SANDBOX_PORTS", "SANDBOX_SET_UID_GID", "SEATBELT_PROFILE", "SURFACE", "USE_VERTEX_AI",
    "VERTEX_AI_API_DEFAULT_VERSION", "VERTEX_AI_EU_REP_ENDPOINT", "VERTEX_AI_REQUEST_TYPE_HEADER",
    "VERTEX_AI_SHARED_REQUEST_TYPE_HEADER", "VERTEX_AI_US_REP_ENDPOINT", "WEB_HOST", "gcloud_project",
    "google_application_credentials", "google_cloud_project", "grpc_proxy", "http_proxy", "https_proxy",
    "no_grpc_proxy", "no_proxy",)
# The pinned Claude Code binary (glitch-6b's ruling 4(i), 15 Oct 2026). Its sha256 sits here, beside the take lock: the
# image it was swept in is box/image.lock's image_id, so a changed binary is a changed image, which preflight's
# image-matches-lock refuses, and test_run_take refuses this record for any image but the lock's.
CLAUDE_BINARY = {"image_id": "sha256:336aa8cd024f0781c3ae3223e70bb0df15d9ad052fb1ec935deb2294b17c8b49",
                 "path": "/usr/local/lib/node_modules/@anthropic-ai/claude-code/bin/claude.exe",
                 "sha256": "24972e3bc859fab2b46ed4c1e51f7d6130f06d3bd550811a114640de3370d0de"}
# Every name the binary's sweep records carry, refused if present for every arm (refusing more fails closed): the review
# of ad71ca07 (MINOR 4) made the list complete over the sweep, so it cannot shrink and stay green. That covers
# glitch-6b's ruled names (4(i): the provider and gateway switches outside every drive.py pattern, the provider
# endpoints and socket, the inference credentials no list held), the review's three (CLAUDE_CODE_GATEWAY_TOKEN_FILE_
# DESCRIPTOR, CLAUDE_CODE_CUSTOM_OAUTH_URL, AWS_ENDPOINT_URL_BEDROCK_RUNTIME), every other pattern-matched or route-read
# name, and two env names seen only in the records' contexts; exempt with its reason only CLAUDE_CODE_OAUTH_TOKEN, the
# Claude row's own login. Source: lane-reports/stub-take-20261015/claude-2.1.296-env-refusal-20261015b.json
# (classify_claude_env_names_v2.py over the committed records of box ba6d7f14: the binary sweep sha256 ea41aeb1..., the
# route names f7b7c024...); test_run_take re-runs the classifier and binds this tuple to its output byte for byte. It
# supersedes 116d83e8's 21-name list (claude-2.1.296-env-refusal-20261015.json, v1, kept as that commit's record).
CLAUDE_BINARY_SWEEP_REFUSED = (
    "ACCESS_TOKEN", "ACCESS_TOKEN_WITH_AUTH_SCHEME", "ACTIONS_ID_TOKEN_REQUEST_TOKEN", "ACTIONS_RUNTIME_TOKEN",
    "AGENT_PROXY_AUTH_TOKEN", "AMPERSAND_TOKEN", "ANACONDA_API_TOKEN", "ANSIBLE_VAULT_PASSWORD_FILE",
    "ANTHROPIC_API_HOST", "ANTHROPIC_API_KEY", "ANTHROPIC_ASSETS_HOST", "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_AWS_API_KEY", "ANTHROPIC_AWS_BASE_URL", "ANTHROPIC_AWS_WORKSPACE_ID", "ANTHROPIC_BASE_URL",
    "ANTHROPIC_BEDROCK_BASE_URL", "ANTHROPIC_BEDROCK_MANTLE_BASE_URL", "ANTHROPIC_BEDROCK_REGION_PREFIX",
    "ANTHROPIC_BEDROCK_SERVICE_TIER", "ANTHROPIC_BETAS", "ANTHROPIC_CONFIG_DIR", "ANTHROPIC_CUSTOM_HEADERS",
    "ANTHROPIC_CUSTOM_MODEL_OPTION", "ANTHROPIC_CUSTOM_MODEL_OPTION_DESCRIPTION",
    "ANTHROPIC_CUSTOM_MODEL_OPTION_NAME", "ANTHROPIC_CUSTOM_MODEL_OPTION_SUPPORTED_CAPABILITIES",
    "ANTHROPIC_DEFAULT_FABLE_MODEL", "ANTHROPIC_DEFAULT_FABLE_MODEL_DESCRIPTION",
    "ANTHROPIC_DEFAULT_FABLE_MODEL_NAME", "ANTHROPIC_DEFAULT_FABLE_MODEL_SUPPORTED_CAPABILITIES",
    "ANTHROPIC_DEFAULT_FABLE_MODEL_SUPPORTED_CAPABILITIES3", "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL_DESCRIPTION", "ANTHROPIC_DEFAULT_HAIKU_MODEL_NAME",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL_SUPPORTED_CAPABILITIES", "ANTHROPIC_DEFAULT_HAIKU_MODEL_SUPPORTED_CAPABILITIES4",
    "ANTHROPIC_DEFAULT_MODEL", "ANTHROPIC_DEFAULT_OPUS_MODEL", "ANTHROPIC_DEFAULT_OPUS_MODEL_DESCRIPTION",
    "ANTHROPIC_DEFAULT_OPUS_MODEL_NAME", "ANTHROPIC_DEFAULT_OPUS_MODEL_SUPPORTED_CAPABILITIES",
    "ANTHROPIC_DEFAULT_SONNET_MODEL", "ANTHROPIC_DEFAULT_SONNET_MODEL_DESCRIPTION",
    "ANTHROPIC_DEFAULT_SONNET_MODEL_NAME", "ANTHROPIC_DEFAULT_SONNET_MODEL_SUPPORTED_CAPABILITIES",
    "ANTHROPIC_ENVIRONMENT_ID", "ANTHROPIC_ENVIRONMENT_KEY", "ANTHROPIC_FEDERATION_RULE_ID",
    "ANTHROPIC_FOUNDRY_API_KEY", "ANTHROPIC_FOUNDRY_AUTH_TOKEN", "ANTHROPIC_FOUNDRY_BASE_URL",
    "ANTHROPIC_FOUNDRY_RESOURCE", "ANTHROPIC_GOOGLE_CLOUD_BASE_URL", "ANTHROPIC_GOOGLE_CLOUD_LOCATION",
    "ANTHROPIC_GOOGLE_CLOUD_PROJECT", "ANTHROPIC_GOOGLE_CLOUD_WORKSPACE_ID", "ANTHROPIC_IDENTITY_TOKEN",
    "ANTHROPIC_IDENTITY_TOKEN_FILE", "ANTHROPIC_LOG", "ANTHROPIC_MODEL", "ANTHROPIC_ORGANIZATION_ID",
    "ANTHROPIC_PROFILE", "ANTHROPIC_SCOPE", "ANTHROPIC_SERVICE_ACCOUNT_ID", "ANTHROPIC_SESSION_ID",
    "ANTHROPIC_SMALL_FAST_MODEL", "ANTHROPIC_SMALL_FAST_MODEL_AWS_REGION", "ANTHROPIC_TELEMETRY_GROUP",
    "ANTHROPIC_TIER_NAMES", "ANTHROPIC_UNIX_SOCKET", "ANTHROPIC_VERTEX_BASE_URL", "ANTHROPIC_VERTEX_PROJECT_ID",
    "ANTHROPIC_WEBHOOK_SIGNING_KEY", "ANTHROPIC_WORKSPACE_ID", "ANTHROPIC_WORK_ID", "ANTHROPIC_WORK_SECRET",
    "API_KEY", "API_KEY_URL", "API_KEY_WITH_CREDENTIALS", "APP_SERVICE_SECRET_HEADER_NAME",
    "ARTIFACTS_CREDENTIALPROVIDER_ACCESSTOKEN", "ARTIFACTS_CREDENTIALPROVIDER_EXTERNAL_FEED_ENDPOINTS",
    "ATTR_CLOUD_PROVIDER", "AUTO_REPLIES_ARMED_TOKEN", "AWS_ACCESS_KEY_ID", "AWS_ACCOUNT_ID",
    "AWS_AUTH_SCHEME_PREFERENCE", "AWS_BEARER_TOKEN_BEDROCK", "AWS_CA_BUNDLE",
    "AWS_CHAIN_RESOLVE_REQUEST_TIMEOUT_MS", "AWS_CONFIG_FILE", "AWS_CONTAINER_AUTHORIZATION_TOKEN",
    "AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE", "AWS_CONTAINER_CREDENTIALS_FULL_URI",
    "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI", "AWS_CREDENTIAL_EXPIRATION", "AWS_CREDENTIAL_SCOPE",
    "AWS_DEFAULTS_MODE", "AWS_DEFAULT_REGION", "AWS_EC2_METADATA_DISABLED", "AWS_EC2_METADATA_IPV4_ADDRESS",
    "AWS_EC2_METADATA_IPV6_ADDRESS", "AWS_EC2_METADATA_SERVICE_ENDPOINT", "AWS_EC2_METADATA_SERVICE_ENDPOINT_MODE",
    "AWS_EC2_METADATA_V1_DISABLED", "AWS_ECS_EC2", "AWS_ECS_FARGATE", "AWS_ENDPOINT_URL", "AWS_ENDPOINT_URL_BEDROCK",
    "AWS_ENDPOINT_URL_BEDROCK_RUNTIME", "AWS_ENDPOINT_URL_SSO", "AWS_ENDPOINT_URL_SSO_OIDC", "AWS_ENDPOINT_URL_STS",
    "AWS_EXECUTION_ENV", "AWS_IAM_ROLE_ARN_RE", "AWS_LAMBDA_BENCHMARK_MODE", "AWS_LAMBDA_FUNCTION_NAME",
    "AWS_LAMBDA_MAX_CONCURRENCY", "AWS_LAMBDA_NODEJS_NO_GLOBAL_AWSLAMBDA", "AWS_LOGIN_CACHE_DIRECTORY",
    "AWS_MAX_ATTEMPTS", "AWS_PAGER", "AWS_PROFILE", "AWS_REGION", "AWS_REGION_RE", "AWS_RETRY_MODE", "AWS_ROLE_ARN",
    "AWS_ROLE_SESSION_NAME", "AWS_SDK_UA_APP_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN",
    "AWS_SHARED_CREDENTIALS_FILE", "AWS_SIGV4A_SIGNING_REGION_SET", "AWS_USE_DUALSTACK_ENDPOINT",
    "AWS_USE_FIPS_ENDPOINT", "AWS_WEB_IDENTITY_TOKEN_FILE", "AZURE_ADDITIONALLY_ALLOWED_TENANTS", "AZURE_ARC",
    "AZURE_AUTHORITY_HOST", "AZURE_AUTH_LOCATION", "AZURE_CLIENT_CERTIFICATE_PASSWORD",
    "AZURE_CLIENT_CERTIFICATE_PATH", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET", "AZURE_CLIENT_SEND_CERTIFICATE_CHAIN",
    "AZURE_CLOUDS", "AZURE_CLOUD_HOSTS", "AZURE_CONFIG_DIR", "AZURE_FEDERATED_TOKEN_FILE",
    "AZURE_FUNCTIONS_ENVIRONMENT", "AZURE_IDENTITY_DISABLE_MULTITENANTAUTH", "AZURE_LOG_LEVEL", "AZURE_PASSWORD",
    "AZURE_POD_IDENTITY_AUTHORITY_HOST", "AZURE_REGIONAL_AUTHORITY_NAME", "AZURE_REGION_AUTO_DISCOVER_FLAG",
    "AZURE_TENANT_ID", "AZURE_TOKEN_CREDENTIALS", "AZURE_USERNAME", "BAD_PASSWORD_READ", "BINSTAR_API_TOKEN",
    "CACHED_ACCESS_TOKEN_EXPIRED", "CARGO_REGISTRY_TOKEN", "CCR_OAUTH_TOKEN_FILE", "CHOICE_TOKEN", "CLAUDE_API_KEY",
    "CLAUDE_BRIDGE_BASE_URL", "CLAUDE_BRIDGE_OAUTH_TOKEN", "CLAUDE_CODE_API_BASE_URL",
    "CLAUDE_CODE_API_KEY_FILE_DESCRIPTOR", "CLAUDE_CODE_API_KEY_HELPER_TTL_MS", "CLAUDE_CODE_ARTIFACTS_API_BASE_URL",
    "CLAUDE_CODE_ARTIFACTS_API_TOKEN", "CLAUDE_CODE_ARTIFACT_ASSET_BASE_URL", "CLAUDE_CODE_ARTIFACT_LIVE_BASE_URL",
    "CLAUDE_CODE_ARTIFACT_SYNC_BASE_URL", "CLAUDE_CODE_ARTIFACT_VIEWER_BASE_URL", "CLAUDE_CODE_CUSTOM_OAUTH_URL",
    "CLAUDE_CODE_GATEWAY_TOKEN", "CLAUDE_CODE_GATEWAY_TOKEN_FILE_DESCRIPTOR", "CLAUDE_CODE_GB_BASE_URL",
    "CLAUDE_CODE_HFI_BEARER_TOKEN", "CLAUDE_CODE_HOST_CREDS_FILE", "CLAUDE_CODE_MCP_SERVE_AUTH_TOKEN",
    "CLAUDE_CODE_MEMORY_API_BASE_URL", "CLAUDE_CODE_MEMORY_API_TOKEN", "CLAUDE_CODE_MESSAGING_TOKEN",
    "CLAUDE_CODE_OAUTH_REFRESH_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN_FILE_DESCRIPTOR",
    "CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST", "CLAUDE_CODE_SESSION_ACCESS_TOKEN",
    "CLAUDE_CODE_SKIP_ANTHROPIC_AWS_AUTH", "CLAUDE_CODE_SKIP_ANTHROPIC_GOOGLE_CLOUD_AUTH",
    "CLAUDE_CODE_SKIP_AWS_CRED_CACHE", "CLAUDE_CODE_SKIP_BEDROCK_AUTH", "CLAUDE_CODE_SKIP_FAST_MODE_NETWORK_ERRORS",
    "CLAUDE_CODE_SKIP_FAST_MODE_ORG_CHECK", "CLAUDE_CODE_SKIP_FOUNDRY_AUTH", "CLAUDE_CODE_SKIP_HFI_VERSION_CHECK",
    "CLAUDE_CODE_SKIP_MANTLE_AUTH", "CLAUDE_CODE_SKIP_MODEL_ACCESS_MEMORY", "CLAUDE_CODE_SKIP_PLUGIN_MCP_SERVERS",
    "CLAUDE_CODE_SKIP_PLUGIN_MCP_SERVERS_EXCEPT", "CLAUDE_CODE_SKIP_PROJECT_BACKFILL",
    "CLAUDE_CODE_SKIP_PROMPT_HISTORY", "CLAUDE_CODE_SKIP_REPO_UPLOAD", "CLAUDE_CODE_SKIP_VERTEX_AUTH",
    "CLAUDE_CODE_SLACK_TAG_TOKEN", "CLAUDE_CODE_USE_ANTHROPIC_AWS", "CLAUDE_CODE_USE_ANTHROPIC_GOOGLE_CLOUD",
    "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_CCR_V2", "CLAUDE_CODE_USE_COWORK_PLUGINS", "CLAUDE_CODE_USE_FOUNDRY",
    "CLAUDE_CODE_USE_GATEWAY", "CLAUDE_CODE_USE_MANTLE", "CLAUDE_CODE_USE_NATIVE_FILE_SEARCH",
    "CLAUDE_CODE_USE_POWERSHELL_TOOL", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_WEBSOCKET_AUTH_FILE_DESCRIPTOR",
    "CLAUDE_LOCAL_OAUTH_API_BASE", "CLAUDE_RUNNER_API_BASE_URL", "CLAUDE_TRUSTED_DEVICE_TOKEN",
    "CLIENT_CREDENTIALS_GRANT", "CLIENT_EARLY_TRAFFIC_SECRET", "CLIENT_HANDSHAKE_TRAFFIC_SECRET",
    "CLIENT_TRAFFIC_SECRET_0", "CLOUDPROVIDERVALUES_ALIBABA_CLOUD", "CLOUDPROVIDERVALUES_AWS",
    "CLOUDPROVIDERVALUES_AZURE", "CLOUDPROVIDERVALUES_GCP", "CLOUDSDK_AUTH_ACCESS_TOKEN",
    "CLOUDSDK_AUTH_ACCESS_TOKEN_FILE", "CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE", "CLOUDSDK_PROXY_PASSWORD",
    "CODEARTIFACT_AUTH_TOKEN", "CONAN_PASSWORD", "CONSUL_HTTP_TOKEN", "COURSIER_CREDENTIALS",
    "CREDENTIALED_URL_MESSAGE", "CREDENTIALS_CODE", "CREDENTIALS_DIRECTORY", "CREDENTIALS_ENV_VARS",
    "CREDENTIALS_ENV_VARS0", "CREDENTIALS_ENV_VARS_STS_WEB_ID_TOKEN", "CREDENTIALS_HTTP", "CREDENTIALS_LOGIN",
    "CREDENTIALS_PROCESS", "CREDENTIALS_PROFILE", "CREDENTIALS_PROFILE_LOGIN", "CREDENTIALS_PROFILE_NAMED_PROVIDER",
    "CREDENTIALS_PROFILE_PROCESS", "CREDENTIALS_PROFILE_SOURCE_PROFILE", "CREDENTIALS_PROFILE_SSO",
    "CREDENTIALS_PROFILE_SSO_LEGACY", "CREDENTIALS_PROFILE_STS_WEB_ID_TOKEN", "CREDENTIALS_SSO",
    "CREDENTIALS_SSO_LEGACY", "CREDENTIALS_STS_ASSUME_ROLE", "CREDENTIALS_STS_ASSUME_ROLE_WEB_ID",
    "CREDENTIAL_HELPER_SETTINGS_KEYS", "CREDENTIAL_KINDS_FOR_PROVIDER", "CREDENTIAL_QUERY_PARAM", "CREDENTIAL_SPEC",
    "DATADOG_API_KEY", "DATADOG_CLIENT_TOKEN", "DEFAULT_INFERENCE_PROVIDER", "DEFAULT_WORKFLOW_TOKEN",
    "DOLLAR_TOKEN", "ENVIRONMENT_SECRET", "ENV_SECRET", "ERR_INVALID_HTTP_TOKEN",
    "ERR_MYSQL_FAILED_TO_ENCRYPT_PASSWORD", "ERR_MYSQL_PASSWORD_REQUIRED", "ERR_REDIS_INVALID_PASSWORD",
    "ERR_S3_INVALID_SESSION_TOKEN", "ERR_S3_MISSING_CREDENTIALS", "ERR_SECRETS_ACCESS_DENIED",
    "ERR_SECRETS_AUTH_FAILED", "ERR_SECRETS_INTERACTION_NOT_ALLOWED", "ERR_SECRETS_INTERACTION_REQUIRED",
    "ERR_SECRETS_INTERACTION_REQUIREDBUG", "ERR_SECRETS_NOT_FOUND", "ERR_SECRETS_PLATFORM_ERROR",
    "ERR_SECRETS_USER_CANCELED", "ERR_UNKNOWN_CREDENTIAL", "EXPORTER_SECRET",
    "FAASINVOKEDPROVIDERVALUES_ALIBABA_CLOUD", "FAASINVOKEDPROVIDERVALUES_AWS", "FAASINVOKEDPROVIDERVALUES_AZURE",
    "FAASINVOKEDPROVIDERVALUES_GCP", "FLIT_PASSWORD", "FOO_API_KEY", "GEM_HOST_API_KEY", "GH_ENTERPRISE_TOKEN",
    "GH_TOKEN", "GITHUB_ACCESS_TOKEN", "GITHUB_ENTERPRISE_TOKEN", "GITHUB_TOKEN", "GITLAB_ACCESS_TOKEN",
    "GITLAB_TOKEN", "GOOGLE_APPLICATION_CREDENTIALS", "GOOGLE_OAUTH_ACCESS_TOKEN", "HF_TOKEN",
    "HPE_INVALID_HEADER_TOKEN", "HTTP2_HEADER_ACCESS_CONTROL_ALLOW_CREDENTIALS",
    "HTTP_PARSER_ERROR_INVALID_HEADER_TOKEN", "HUGGINGFACEHUB_API_TOKEN", "HUGGING_FACE_HUB_TOKEN",
    "HYBRID_SERVABLE_CREDENTIAL_KINDS", "HYBRID_SERVABLE_PROVIDERS", "IDTOKEN_TOKEN", "ID_TOKEN",
    "INCORRECT_PASSWORD", "INFERENCE_CREDENTIAL_KINDS", "INVALID_DELEGATED_CREDENTIAL", "INVALID_PASSWORD",
    "INVALID_SECRET_LENGTH", "INVALID_TOKEN", "LISTENER_NEW_TOKEN", "LONG_LIVED_OAUTH_TOKEN_TTL_SECONDS",
    "LSQUIC_LOG_SECRETS", "MARIADB_PASSWORD", "MARKETPLACE_CREDENTIAL_KINDS", "MATURIN_PASSWORD",
    "MATURIN_PYPI_TOKEN", "MCP_CLIENT_SECRET", "MCP_XAA_IDP_CLIENT_SECRET", "MISSING_CREDENTIALS",
    "ML_AND_SF_SECRET_HEADER_NAME", "MSI_SECRET", "MYSQL_PASSWORD", "MY_API_KEY", "NEW_TOKEN", "NODE_AUTH_TOKEN",
    "NOMAD_TOKEN", "NOOP_METER_PROVIDER", "NO_CACHED_ACCESS_TOKEN", "NO_CREDENTIALS_FOUND", "NPM_CONFIG_TOKEN",
    "NPM_TOKEN", "NUGET_AUTH_TOKEN", "OAUTH_TOKEN", "OAUTH_TOKEN_SAVE_FAILED_WARNING", "OVERRIDE_GITHUB_TOKEN",
    "PG_PASSWORD", "PLACEHOLDER_CREDENTIAL_KEYS", "PROVIDER_ARMS", "PROVIDER_CLI_FLAG", "PROVIDER_DETECTED",
    "PROVIDER_DISPLAY", "PROVIDER_SELECTOR_ENV_FLAGS", "PYPI_API_TOKEN", "PYPI_TOKEN", "QUIC_FRAME_NEW_TOKEN",
    "REFRESH_TOKEN", "RESOURCE_OWNER_PASSWORD_GRANT", "RUNNER_ENVIRONMENT_SECRET", "RUNNER_POOL_SECRET",
    "SBT_CREDENTIALS", "SECRET_ACCESS_KEY", "SELF_HOSTED_RUNNER_ENVIRONMENT_SECRET",
    "SELF_HOSTED_RUNNER_POOL_SECRET", "SEMATTRS_FAAS_INVOKED_PROVIDER", "SEMRESATTRS_CLOUD_PROVIDER",
    "SERVER_HANDSHAKE_TRAFFIC_SECRET", "SERVER_TRAFFIC_SECRET_0", "SESSION_TOKEN", "SHR_GIT_PROXY_TOKEN",
    "SIGN_IN_CREDENTIAL_KINDS", "SONAR_TOKEN", "THIRD_PARTY_PROVIDER_ENV_VARS", "THIRD_PARTY_PROVIDER_LABELS",
    "TRUST_TOKEN", "TWINE_PASSWORD", "UNSUPPORTED_CREDENTIAL_LIST", "USER_CREDENTIALS_CHANGED",
    "UV_PUBLISH_PASSWORD", "UV_PUBLISH_TOKEN", "U_UNEXPECTED_TOKEN", "VAULT_AUTH_TOKEN", "VAULT_SECRET_ID",
    "VAULT_TOKEN", "VERTEX_OAUTH_CREDENTIAL_KIND", "VOICE_STREAM_BASE_URL", "VSS_NUGET_ACCESSTOKEN",
    "WEB_SEARCH_PROVIDERS", "WEB_SEARCH_PROVIDER_HOSTS",)
VENDOR_BILLING_ROUTE_VARIABLES = {
    CODEX: ("CODEX_AUTHAPI_BASE_URL",                  # matches[46], [50]: before https://auth.openai.com/api/accounts
            "CODEX_AGENT_IDENTITY_AUTHAPI_BASE_URL",   # matches[68]
            "CODEX_AGENT_IDENTITY_JWKS_BASE_URL",      # matches[46], [68]
            "CODEX_REVOKE_TOKEN_URL_OVERRIDE",         # matches[65]: before https://auth.openai.com/oauth/revoke
            "CODEX_CONNECTORS_TOKEN",                  # matches[33]
            "OPENAI_ORGANIZATION",                     # matches[40]: beside the OpenAI-Organization header
            "OPENAI_FEDERATION_RULE_ID",               # matches[31]
            "OPENAI_IDENTITY_TOKEN_FILE",              # matches[31]
            # glitch-06's ruling on the docs-read candidates (14 Oct 2026): the pinned Codex is 0.162.1
            # (box/codex/image.lock line 7, harness.version), the version tests/test_env_allowlist.py's
            # DOCS_READ_VARIABLES was read at ("Codex, read by the source at rust-v0.162.1" and "Codex, documented");
            # its Codex names not named above, refused if present (refusing more fails closed).
            "OPENAI_PROJECT", "OPENAI_BASE_URL", "CODEX_ACCESS_TOKEN", "OPENAI_WORKLOAD_IDENTITY_CONTEXT",
            "CODEX_OSS_BASE_URL", "CODEX_OSS_PORT", "AWS_BEARER_TOKEN_BEDROCK", "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY", "AWS_REGION", "AWS_DEFAULT_REGION", "AWS_PROFILE",
            # the review's NIT 7: matches[2] reads CODEX_APP_SERVER_LOGIN_ISSUERAmazon Bed..., an ambiguous end; both
            # spellings are refused (refusing more fails closed)
            "CODEX_APP_SERVER_LOGIN_ISSUER", "CODEX_APP_SERVER_LOGIN_ISSUERA"),
    GEMINI: GEMINI_PACKAGE_SWEEP_REFUSED,    # FILLED 14 Oct 2026 (glitch-06): the Gemini package sweep
    CLAUDE_CODE: CLAUDE_BINARY_SWEEP_REFUSED}    # FILLED 15 Oct 2026 (glitch-6b's ruling 4(i)): the Claude binary sweep
# The sweep's names not named above join the Codex entry, in the sweep's order (glitch-06, 14 Oct 2026).
VENDOR_BILLING_ROUTE_VARIABLES[CODEX] = VENDOR_BILLING_ROUTE_VARIABLES[CODEX] + tuple(
    n for n in CODEX_BINARY_SWEEP_REFUSED if n not in VENDOR_BILLING_ROUTE_VARIABLES[CODEX])

# What the runtime client itself needs from the caller's environment, and nothing else.
RUNTIME_ENV_NAMES = ("PATH", "HOME", "DOCKER_HOST", "XDG_RUNTIME_DIR")

# `docker top`'s column form under rootless Docker: {"ps_options": [...], "pid_column": str, "uid_column": str,
# "uid_namespace": "host" | "container"}. Docker 29.8.1 on Athena reports container UIDs even though its PIDs
# are host PIDs (live probe 13 Oct 2026). The namespace must be measured, never inferred from rootless mode.
# once measured on the box.
# FILLED 14 Oct 2026 (box lane; stub-take review PASS, glitch-06): measured on athena, docker 29.8.1, rootless, by
# lane-reports/stub-take-20261014/stub-take-run1.json and -run2.json (derivation rule R-TOP): `docker top -eo
# pid,uid,comm` prints host pids beside the rootless daemon's (here the container's) uids, e.g. 10001 for host 110000.
# Re-measure if the box ever adds a per-container user-namespace remap.
TOP_FORMAT = {"ps_options": ["-eo", "pid,uid,comm"], "pid_column": "PID", "uid_column": "UID",
              "uid_namespace": "container"}

# The Docker Engine API's spelling of each inspected fact (taken from the Engine API's ContainerInspect, never
# driven). INSPECT_STATUS stays PENDING until the stub take reads one inspect; while it is, every comparison and
# every state read refuses (NotReady).
INSPECT_PATHS = {
    "image": "Image", "user": "Config.User", "cmd": "Config.Cmd", "env": "Config.Env",
    "working_dir": "Config.WorkingDir", "entrypoint": "Config.Entrypoint", "network_mode": "HostConfig.NetworkMode",
    "cap_drop": "HostConfig.CapDrop", "cap_add": "HostConfig.CapAdd", "security_opt": "HostConfig.SecurityOpt",
    "privileged": "HostConfig.Privileged", "devices": "HostConfig.Devices", "pid_mode": "HostConfig.PidMode",
    "pids_limit": "HostConfig.PidsLimit", "memory": "HostConfig.Memory",
    "memory_reservation": "HostConfig.MemoryReservation", "nano_cpus": "HostConfig.NanoCpus",
    "mounts": "Mounts", "running": "State.Running", "exit_code": "State.ExitCode", "oom_killed": "State.OOMKilled",
    # the read-only root (glitch-b5, 16 Oct 2026): the Engine API's spellings, confirmed by the first live walk
    "readonly_rootfs": "HostConfig.ReadonlyRootfs", "tmpfs": "HostConfig.Tmpfs",
}
# FILLED 14 Oct 2026 (box lane; stub-take review PASS): every INSPECT_PATHS spelling resolved in the take's, the
# sidecar's and the proxy's inspects of both stub takes (rule R-INSPECT).
INSPECT_STATUS = {"confirmed_on": "2026-10-14", "engine": "29.8.1", "api_version": "1.56",
                  "evidence": (("lane-reports/stub-take-20261014/stub-take-run1.json",
                                "67a0698a2e1037fdf5a1c02caea67a1281a5f31c4bc8629adfbb476f07dd83f4"),
                               ("lane-reports/stub-take-20261014/stub-take-run2.json",
                                "8a72763f4d172ce22ecdd5779d1ffd89e60ff07abba2cf22b43a829bd6fd08bb"))}

PENDING_WHY = {
    "FALLBACK_ENV": "Claude Code's refusal-fallback and model-fallback variables, names and values: confirmed at "
                    "the pinned version (plan, run_take task).",
    "VENDOR_BILLING_ROUTE_VARIABLES": "arms O and G's own billing-route variables: named from each harness's "
                                      "documentation at the pinned version (D8 B2 item 7).",
    "TOP_FORMAT": "the column form `docker top` prints under rootless Docker: measured on the box.",
    "INSPECT_STATUS": "the inspect spellings, taken from the Docker Engine API: confirmed when the stub take reads "
                      "one inspect.",
    "CLAUDE_BYPASS_KEY": "the bypass acceptance: RULED not required in -p runs (glitch-06, 14 Oct 2026; "
                         "CLAUDE_BYPASS_RULING); listed here only if it is ever set back to PENDING.",
    "TakeSpec.resources": "the take's memory reservation, CPU and pids values: capacity POLICY, not measurements "
                          "(the caller's spec_for passes them; the stub-take derivation's rule R-RES from athena's "
                          "capacity and three concurrent takes; the stub take only showed that they apply and the "
                          "box's floor, all recorded).",
}
# Pending values this module does not hold: the caller passes them once measured.
# RETIRED 14 Oct 2026 (glitch-06, row 4 of the box lane's open table): "XDG_RUNTIME_DIR in the take" (the guards
# plan's stub take, line 329), measured NOT needed. In stub takes 1-4 and 6 on athena (lane-reports/stub-take-20261014,
# stub-take-run1..4.json and stub-take-run6.derived.json), every one of 18 execs per take into the take container as
# AGENT_USER, `claude --version` at the pinned 2.1.296 among them, returned 0 with no XDG_RUNTIME_DIR in its argv,
# and TAKE_ENV sets none. test_run_take re-derives this from run 1 and run 6 by their sha256.
CALLER_PENDING = {
    "cgroup_dir": "the container's cgroup folder under athena's rootless Docker: measured on the box; the caller "
                  "passes it to counters().",
    "uid_map": "the runtime's user-namespace map (javier's 100000:65536 on athena, card Part 1 step 6): the caller "
               "passes it to agent_processes().",
    "tree ownership": "the run tree's and the config folder's ownership and modes under the user-namespace map, and "
                      "the removal road for uid-mapped files the agent leaves: measured at the stub take.",
}

_HEX64 = re.compile(r"[0-9a-f]{64}")
_IMAGE_ID = re.compile(r"sha256:[0-9a-f]{64}")
_CPUS = re.compile(r"[1-9][0-9]*(\.[0-9]{1,3})?|0\.[0-9]{0,2}[1-9]")
_NAME = re.compile(r"[A-Z_][A-Z0-9_]*")
_NAME_KEY = re.compile(r"[A-Za-z][A-Za-z0-9_]*")


class NotReady(RuntimeError):
    """A real use needs a value that is still PENDING."""


class Refused(ValueError):
    """The take, the exec or the input is refused by a rule. The message names the rule, never a secret."""


class LoginRefused(Refused):
    """A login file breaks the format or the placement rule. The message names the file and the rule only."""


class LaunchError(RuntimeError):
    """A launch step failed; everything made so far was torn down by its recorded id. `launched` carries the ids."""

    def __init__(self, message: str, launched: "Launched"):
        super().__init__(message)
        self.launched = launched


class TeardownError(RuntimeError):
    """A teardown step failed; every other step still ran. `record` names each step and its outcome."""

    def __init__(self, message: str, record: dict):
        super().__init__(message)
        self.record = record


class LeakedContainer(Refused):
    """A recorded container is still present: the restart is refused and the container named."""


def _is_pending(v) -> bool:
    if isinstance(v, str):
        return v == PENDING
    if isinstance(v, dict):
        return any(_is_pending(x) for x in v.values())
    if isinstance(v, (list, tuple)):
        return any(_is_pending(x) for x in v)
    return False


def _pending_values() -> dict:
    return {"FALLBACK_ENV": FALLBACK_ENV, "VENDOR_BILLING_ROUTE_VARIABLES": VENDOR_BILLING_ROUTE_VARIABLES,
            "TOP_FORMAT": TOP_FORMAT, "INSPECT_STATUS": INSPECT_STATUS, "CLAUDE_BYPASS_KEY": CLAUDE_BYPASS_KEY}


def pending() -> dict:
    """Every value this module holds that is still PENDING, with its reason (resources: always, by design)."""
    out = {k: PENDING_WHY[k] for k, v in _pending_values().items() if _is_pending(v)}
    out["TakeSpec.resources"] = PENDING_WHY["TakeSpec.resources"]
    return out


# ---------------------------------------------------------------------------------------- the runtime protocol
@dataclass(frozen=True)
class Completed:
    returncode: int
    stdout: str
    stderr: str


def _check_argv(argv) -> list:
    if isinstance(argv, (str, bytes)) or not isinstance(argv, (list, tuple)) or not argv:
        raise TypeError("argv is a non-empty list of strings, never a shell string")
    if not all(isinstance(a, str) for a in argv):
        raise TypeError("argv is a non-empty list of strings")
    return list(argv)


class DockerRuntime:
    """The one real runtime: the box's only subprocess call (interface 10)."""

    def run(self, argv: list, *, env: dict | None = None, timeout: float | None = None) -> Completed:
        argv = _check_argv(argv)
        whole = {} if env is None else {str(k): str(v) for k, v in env.items()}
        try:
            p = subprocess.run(argv, env=whole, timeout=timeout, shell=False, capture_output=True, text=True,
                               encoding="utf-8", errors="surrogateescape", check=False)
        except subprocess.TimeoutExpired as e:
            err = TimeoutError(f"{argv[0]} {argv[1] if len(argv) > 1 else ''} timed out after {timeout} s")
            out = e.stdout
            err.stdout = out.decode("utf-8", "surrogateescape") if isinstance(out, bytes) else (out or "")
            raise err from None
        return Completed(p.returncode, p.stdout, p.stderr)


def runtime_env(caller_env=None) -> dict:
    """The runtime client's own needs from the caller's environment, built from nothing."""
    src = os.environ if caller_env is None else caller_env
    return {k: src[k] for k in RUNTIME_ENV_NAMES if k in src}


# ------------------------------------------------------------------------------------------- the take container
def _abs_path(p, what: str) -> str:
    if not isinstance(p, str) or not p.startswith("/") or os.path.normpath(p) != p or p == "/":
        raise Refused(f"{what} must be a normalised absolute path other than /")
    if any(c in p for c in ",=\n\r\t\0") or p != p.strip():
        raise Refused(f"{what} must not carry a comma, an equals sign, a control character or edge whitespace")
    return p


def _inside(child: str, parent: str) -> bool:
    return child == parent or child.startswith(parent.rstrip("/") + "/")


@dataclass(frozen=True)
class TakeSpec:
    """Every value `create_argv` passes to `docker create` (interface 13)."""
    image: str
    run_tree: str
    config_dir: str
    network: str
    memory_reservation: int | str = PENDING
    memory: int | str = PENDING
    cpus: str = PENDING
    pids_limit: int | str = PENDING
    keepalive_user: str = KEEPALIVE_USER
    agent_user: str = AGENT_USER
    cap_drop: tuple = ("ALL",)
    security_opt: tuple = ("no-new-privileges",)

    def nano_cpus(self) -> int:
        return int(Decimal(self.cpus) * 1_000_000_000)


def _positive_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool) and v > 0


def check_spec(spec: TakeSpec) -> None:
    """Refuse a spec create_argv must not run: a PENDING resource (NotReady), or any value off its rule.

    W4B2-3: the network must be a full 64-hex id here. Before launch the drive step cannot know the internal network's
    id, so it passes a placeholder 64-hex id, which launch replaces with the network it creates (`_on_network`)."""
    if not isinstance(spec, TakeSpec):
        raise Refused("spec must be a TakeSpec")
    resources = {"memory_reservation": spec.memory_reservation, "memory": spec.memory, "cpus": spec.cpus,
                 "pids_limit": spec.pids_limit}
    still = sorted(k for k, v in resources.items() if _is_pending(v))
    if still:
        raise NotReady(f"the take's resources are PENDING: {', '.join(still)} ({PENDING_WHY['TakeSpec.resources']})")
    for k in ("memory_reservation", "memory", "pids_limit"):
        if not _positive_int(resources[k]):
            raise Refused(f"{k} must be a positive int")
    if spec.memory != 3 * spec.memory_reservation:
        raise Refused("memory must be exactly three times memory_reservation")
    if not isinstance(spec.cpus, str) or not _CPUS.fullmatch(spec.cpus):
        raise Refused("cpus must be a positive decimal string with at most three places")
    try:
        Decimal(spec.cpus)
    except InvalidOperation:
        raise Refused("cpus must be a decimal") from None
    if spec.keepalive_user != KEEPALIVE_USER:
        raise Refused(f"the keep-alive user is {KEEPALIVE_USER}, never another")
    if spec.agent_user != AGENT_USER:
        raise Refused(f"the agent user is {AGENT_USER}, never another")
    if tuple(spec.cap_drop) != ("ALL",):
        raise Refused("cap_drop is exactly ('ALL',)")
    if tuple(spec.security_opt) != ("no-new-privileges",):
        raise Refused("security_opt is exactly ('no-new-privileges',)")
    if not isinstance(spec.image, str) or not _IMAGE_ID.fullmatch(spec.image):
        raise Refused("image must be the lock's image id, sha256:<64 hex>, never a tag")
    if not isinstance(spec.network, str) or not _HEX64.fullmatch(spec.network):
        raise Refused("network must be the internal network's full id")
    rt = _abs_path(spec.run_tree, "run_tree")
    cfg = _abs_path(spec.config_dir, "config_dir")
    if _inside(rt, cfg) or _inside(cfg, rt):
        raise Refused("the run tree and the config folder must not contain each other")
    if _inside(rt, CONFIG_MOUNT) or _inside(CONFIG_MOUNT, rt):
        raise Refused(f"the run tree must not overlap the config mount {CONFIG_MOUNT}")


def create_argv(spec: TakeSpec) -> list:
    """`docker create` for one take container: no environment, no alias, a read-only root with exactly two bind mounts
    and the TAKE_TMPFS mounts, PID 1 the keep-alive."""
    check_spec(spec)
    return [RUNTIME_CLIENT, "create", "--pull=never",
            "--network", spec.network,
            "--user", KEEPALIVE_USER,
            "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges",
            "--pids-limit", str(spec.pids_limit),
            "--memory-reservation", str(spec.memory_reservation),
            "--memory", str(spec.memory),
            "--cpus", spec.cpus,
            "--read-only",
            *[a for path, opts in TAKE_TMPFS.items() for a in ("--tmpfs", f"{path}:{opts}")],
            "--mount", f"type=bind,source={spec.run_tree},target={spec.run_tree}",
            "--mount", f"type=bind,source={spec.config_dir},target={CONFIG_MOUNT}",
            "--workdir", spec.run_tree,
            "--entrypoint", KEEPALIVE_COMMAND[0],
            spec.image, *KEEPALIVE_COMMAND[1:]]


# ---------------------------------------------------------------------------------- the environment per harness
def _known_harness(harness) -> str:
    if not isinstance(harness, str) or harness not in TAKE_ENV or harness not in LOGIN_VARIABLE:
        raise Refused(f"unknown harness {harness!r}: one of {sorted(LOGIN_VARIABLE)}, never a default")
    return harness


def refused_variables(harness: str) -> frozenset:
    """The closed refused set for one take's harness: every key, token and billing-route name, less its own login."""
    harness = _known_harness(harness)
    names = set(API_KEY_VARIABLES) | set(BILLING_ROUTE_VARIABLES) | set(SUBSCRIPTION_TOKEN_VARIABLES)
    names |= set(VENDOR_KEY_VARIABLES)
    if harness == GEMINI:
        names |= set(GEMINI_MODE_ROUTE_VARIABLES)
    for h, extra in VENDOR_BILLING_ROUTE_VARIABLES.items():
        if not _is_pending(extra):
            names |= set(extra)
    return frozenset(names - {LOGIN_VARIABLE[harness]})


def take_environment(harness: str, run_tree: str) -> dict:
    """The agent's WHOLE starting environment for one take (ruling docs-1), built from nothing: TAKE_ENV's row for the
    arm, the run tree's temporary folder filled in, and (arm A) Claude Code's fallback values once confirmed. The
    credential stays the CREDENTIAL marker; its value is read at exec time and rides by name only. No caller's
    environment is read. Refuses while a value it needs is PENDING."""
    harness = _known_harness(harness)
    tree = _abs_path(run_tree, "run_tree")
    if sorted(k for k, v in TAKE_ENV[harness].items() if v == RUN_TREE_TMP) != sorted(RUN_TREE_TMPDIR_VARIABLES):
        raise Refused(f"the {harness} row's temporary-folder names are not {list(RUN_TREE_TMPDIR_VARIABLES)}")
    markers = {RUN_TREE_TMP: f"{tree}/{RUN_TREE_TMPDIR}", RUN_TREE_HOME: f"{tree}/{RUN_TREE_HOMEDIR}"}
    out = {}
    for name, value in TAKE_ENV[harness].items():
        out[name] = markers.get(value, value)
    if harness == CLAUDE_CODE:
        if _is_pending(FALLBACK_ENV):
            raise NotReady(f"FALLBACK_ENV is PENDING: {PENDING_WHY['FALLBACK_ENV']}")
        for k, v in FALLBACK_ENV.items():
            if k in out:
                raise Refused(f"a fallback variable may not override {k}")
            out[k] = v
    elif _is_pending(VENDOR_BILLING_ROUTE_VARIABLES.get(harness, PENDING)):
        raise NotReady(f"VENDOR_BILLING_ROUTE_VARIABLES[{harness!r}] is PENDING: "
                       f"{PENDING_WHY['VENDOR_BILLING_ROUTE_VARIABLES']}")
    return out


def exec_values(harness: str, run_tree: str) -> dict:
    """The exec's non-secret values for one harness: take_environment less the credential (no login)."""
    return {k: v for k, v in take_environment(harness, run_tree).items() if v != CREDENTIAL}


def launcher_argv(login: str, values: dict, inner, *, harness) -> list:
    """The turn's command inside the take container: LAUNCHER, the credential's name, the count of pairs, the
    NAME=VALUE pairs in name order, then the harness's argv. The launcher execs the harness with exactly the pairs and
    the credential (read by its name from the exec's environment): the agent starts from an empty environment.
    `harness` is required (the review of 41428177, MINOR 1): the login must be LOGIN_VARIABLE[harness], so a named key
    for a Codex row refuses whatever the gate. The reserved NO_LOGIN copies no credential: admitted only for a Codex
    row behind the closed lease gate, and only over exactly the Codex row's names with no other harness's config home
    (MINOR 2: the values are read, not only the harness= claim)."""
    inner = _check_argv(inner) if inner else None
    if inner is None:
        raise Refused("the launcher needs the harness's argv")
    if login == NO_LOGIN:
        codex_lease_gate()
        if harness != CODEX:
            raise Refused("the no-login launcher name is admitted only for a Codex row")
        names = set(values) if isinstance(values, dict) else set()
        other_homes = sorted(names & (config_home_names() - set(HARNESS_ENV[CODEX])))
        if other_homes:
            raise Refused(f"the no-login launcher carries another harness's config home: {', '.join(other_homes)}")
        if names != set(TAKE_ENV[CODEX]):
            raise Refused("the no-login launcher's values must be exactly the Codex row's names")
    elif not isinstance(login, str) or not _NAME.fullmatch(login):
        raise Refused("the credential is named by a variable NAME")
    else:
        harness = _known_harness(harness)
        if login != LOGIN_VARIABLE[harness]:
            raise Refused(f"{login} is not the login of a {harness} row")
    pairs = []
    for k in sorted(values):
        v = values[k]
        if not _NAME.fullmatch(k):
            raise Refused(f"{k!r} is not a variable NAME")
        if k == login:
            raise Refused("the credential never rides as a pair: by name only")
        if not isinstance(v, str) or "\0" in v:
            raise Refused(f"the value of {k} is not a string free of NUL")
        pairs.append(f"{k}={v}")
    return [*LAUNCHER, login, str(len(pairs)), *pairs, *inner]


def claude_study_settings(model: str) -> str:
    """The inline --settings JSON for one Claude Code take (canonical: sorted keys, no spaces). NotReady while
    FALLBACK_ENV or CLAUDE_BYPASS_KEY is PENDING. It carries no bypass acceptance key: RULED not required in -p
    (CLAUDE_BYPASS_RULING); any other value of CLAUDE_BYPASS_KEY is refused."""
    if not isinstance(model, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}", model):
        raise Refused("the take's model is a plain model id")
    if _is_pending(FALLBACK_ENV):
        raise NotReady(f"FALLBACK_ENV is PENDING: {PENDING_WHY['FALLBACK_ENV']}")
    if _is_pending(CLAUDE_BYPASS_KEY):
        raise NotReady(f"CLAUDE_BYPASS_KEY is PENDING: {PENDING_WHY['CLAUDE_BYPASS_KEY']}")
    if CLAUDE_BYPASS_KEY != CLAUDE_BYPASS_NOT_REQUIRED:
        raise Refused("the study sends no bypass acceptance key: RULED not required in -p runs (CLAUDE_BYPASS_RULING)")
    return json.dumps({"availableModels": [model], "crossSessionInbound": CROSS_SESSION_INBOUND,
                       "env": {**FALLBACK_ENV, **BASH_FIRST_STEER_ENV, **SILENT_TURN_REMINDER_ENV},
                       "permissions": {"deny": list(ISOLATION_DISALLOWED_TOOLS)},
                       "fallbackModel": [], "switchModelsOnFlag": False}, sort_keys=True, separators=(",", ":"))


def _flag_values(inner, flag: str) -> list:
    """Every value of `flag` in a Claude Code argv (`flag v` or `flag=v`), never reading the prompt after -p or
    --print."""
    out, i = [], 1
    while i < len(inner):
        tok = inner[i]
        if tok in CLAUDE_PRINT_FLAGS:
            i += 2
            continue
        if tok == flag:
            out.append(inner[i + 1] if i + 1 < len(inner) else None)
            i += 2
            continue
        if tok.startswith(flag + "="):
            out.append(tok[len(flag) + 1:])
        i += 1
    return out


def _denied_tools(inner) -> set:
    """Every tool name a Claude Code argv denies by --disallowedTools / --disallowed-tools: the binary's variadic
    `<tools...>`, so each flag takes the following tokens up to the next one that starts with "-", or its `=` value;
    each value a comma or space-separated list. The prompt after -p or --print is never read."""
    out, toks, i = set(), _flag_tokens(inner), 0
    while i < len(toks):
        flag, sep, value = toks[i].partition("=")
        if flag in CLAUDE_DENY_FLAGS:
            vals = [value] if sep else []
            i += 1
            while not sep and i < len(toks) and not toks[i].startswith("-"):
                vals.append(toks[i])
                i += 1
            out |= {n for v in vals for n in v.replace(",", " ").split()}
            continue
        i += 1
    return out


def _flag_tokens(inner) -> list:
    """Every token of a Claude Code argv except the prompt that follows -p or --print."""
    out, i = [], 1
    while i < len(inner):
        if inner[i] in CLAUDE_PRINT_FLAGS:
            i += 2
            continue
        out.append(inner[i])
        i += 1
    return out


def check_claude_settings(inner) -> None:
    """A Claude Code turn is a -p (--print) run, never --bg, names its model once and carries exactly the study's
    inline settings for that model. The bypass ruling (CLAUDE_BYPASS_RULING) depends on the -p and the no --bg."""
    if not isinstance(inner, (list, tuple)) or not inner or not isinstance(inner[0], str) or not (
            inner[0] == CLAUDE_CLIENT or (os.path.isabs(inner[0]) and os.path.basename(inner[0]) == CLAUDE_CLIENT)):
        raise Refused(f"a claude-code turn runs {CLAUDE_CLIENT} (or its absolute path), nothing else")
    if len(inner) < 2 or inner[1] not in CLAUDE_PRINT_FLAGS:
        raise Refused("a claude-code turn is a non-interactive run: -p or --print comes first (the bypass ruling "
                      "depends on it)")
    if [a for a in _flag_tokens(inner) if a == CLAUDE_BARE_FLAG or a.startswith(CLAUDE_BARE_FLAG + "=")]:
        raise Refused(f"a claude-code turn never runs {CLAUDE_BARE_FLAG}: bare mode does not read the walk token's "
                      f"CLAUDE_CODE_OAUTH_TOKEN (code.claude.com/docs/en/authentication)")
    if [a for a in _flag_tokens(inner) for f in CLAUDE_BACKGROUND_FLAGS if a == f or a.startswith(f + "=")]:
        raise Refused(f"a claude-code turn never runs {' or '.join(CLAUDE_BACKGROUND_FLAGS)}: a background session "
                      f"needs the bypass acceptance the study does not send")
    models = _flag_values(inner, "--model")
    if len(models) != 1 or not models[0]:
        raise Refused("a claude-code turn names its model exactly once by --model")
    missing = [t for t in ISOLATION_DISALLOWED_TOOLS if t not in _denied_tools(inner)]
    if missing:
        raise Refused(f"a claude-code turn denies {list(ISOLATION_DISALLOWED_TOOLS)} by "
                      f"{CLAUDE_DENY_FLAGS[0]} (the isolation ruling); it does not deny {missing}")
    given = _flag_values(inner, CLAUDE_SETTINGS_FLAG)
    if given != [claude_study_settings(models[0])]:
        raise Refused(f"a claude-code turn carries exactly one {CLAUDE_SETTINGS_FLAG}: the study's settings for its "
                      f"model (switchModelsOnFlag false, no fallback chain, availableModels [model])")


def check_model(harness: str, inner):
    """Arm G's call names its model exactly once, by a full pinned id; a short alias is refused by its name (it
    resolves to another model). Returns the model, or None for an arm MODEL_PINS does not cover."""
    pin = MODEL_PINS.get(harness)
    if pin is None:
        return None
    if not inner or not (inner[0] == pin["client"] or
                         (os.path.isabs(inner[0]) and os.path.basename(inner[0]) == pin["client"])):
        raise Refused(f"unsupported {harness} executable: {inner[0] if inner else None!r}; "
                      f"use {pin['client']} or its absolute path; probes use agent_exec_argv")
    # Admit only the value-taking flags used by the adapter and their long aliases. Consume their values,
    # so prompt text is not parsed as flags. Compact/clustered flags, positional tails and -- refuse rather
    # than letting the CLI parse a second model choice differently from this boundary.
    value_flags = ("-p", "--prompt", "-o", "--output-format", "--approval-mode", "--resume", "-r")
    given = []
    i = 1
    while i < len(inner):
        tok = inner[i]
        flag, sep, value = tok.partition("=")
        if flag not in pin["flags"] and flag not in value_flags:
            raise Refused(f"unsupported {harness} turn argument {tok!r}")
        if not sep:
            i += 1
            value = inner[i] if i < len(inner) else None
        if flag in pin["flags"]:
            given.append(value)
        elif value is None or value.startswith("-"):
            raise Refused(f"unsupported {harness} value for {flag!r}")
        i += 1
    if len(given) != 1 or given[0] is None:
        raise Refused(f"a {harness} call names its model exactly once by {pin['flags'][0]}, never the default")
    model = given[0]
    if model in pin["short_aliases"]:
        raise Refused(f"{model!r} is a short alias (it resolves to {pin['short_aliases'][model]}): the call passes "
                      f"a full model id, one of {', '.join(pin['models'])}")
    if model not in pin["models"]:
        raise Refused(f"model {model!r} is not one of the arm's pinned ids: {', '.join(pin['models'])}")
    return model


def env_file_dirs(workdir: str, run_tree: str) -> list:
    """The folders a harness reads a `.env` from inside the run tree: the working folder and every parent up to and
    including the box root (the run tree, mounted at the same path)."""
    cur = _abs_path(workdir, "workdir")
    root = _abs_path(run_tree, "run_tree")
    if not _inside(cur, root):
        raise Refused("the working folder must sit inside the run tree (the box root)")
    rel = os.path.relpath(cur, root)
    parts = [] if rel == "." else rel.split(os.sep)
    return [os.path.join(root, *parts[:i]) for i in range(len(parts), -1, -1)]


def refuse_env_files(*, workdir: str, run_tree: str, config_dir: str | None = None) -> None:
    """Refuse, naming each file, when a `.env` a harness would read exists: in the working folder, any parent up to
    the box root, arms O's and G's HOME (the run tree's home, R-H5), and (given the per-take config folder, arm A's
    HOME and every arm's config home, host side) in the config folder. Read host-side, a link counted."""
    found = []
    for d in env_file_dirs(workdir, run_tree):
        for name in ENV_FILE_NAMES:
            if os.path.lexists(os.path.join(d, name)):
                found.append(os.path.join(d, name))
    home = os.path.join(_abs_path(run_tree, "run_tree"), RUN_TREE_HOMEDIR)
    for name in ENV_FILE_NAMES:
        if os.path.lexists(os.path.join(home, name)):
            found.append(f"HOME ({RUN_TREE_HOME}) {os.path.join(home, name)}")
    if config_dir is not None:
        cfg = _abs_path(config_dir, "config_dir")
        for h, row in TAKE_ENV.items():
            if row.get("HOME") not in (CONFIG_MOUNT, RUN_TREE_HOME):
                raise Refused(f"the {h} row's HOME is neither the config mount nor the run tree's home: its .env "
                              f"cannot be read")
        for name in ENV_FILE_NAMES:
            if os.path.lexists(os.path.join(cfg, name)):
                found.append(f"HOME or config home ({CONFIG_MOUNT}) {os.path.join(cfg, name)}")
    if found:
        raise Refused("a .env file a harness would read is present, so the take is refused: " + "; ".join(found))


def _own_environment():
    """This process's own environment: always checked, whatever caller_env a caller passes (W4B1-9)."""
    return os.environ


# glitch-06's ruling on the Codex sweep's residual (14 Oct 2026): two of the binary's names are prefixes the CLI extends
# per variable, so every name starting with either is refused for every arm (refusing more fails closed).
REFUSED_NAME_PREFIXES = ("CODEX_NETWORK_PROXY_SNAPSHOT_BROKERED_UNSET_", "CODEX_NETWORK_PROXY_SNAPSHOT_BROKERED_VALUE_")


def _refused_name(name, refused) -> bool:
    return name in refused or (isinstance(name, str) and name.startswith(REFUSED_NAME_PREFIXES))


def check_environment(harness: str, caller_env=None, requested=()) -> None:
    """Refuse the take when any refused name, or a name with a REFUSED_NAME_PREFIXES prefix, is set in this process's
    own environment, in the caller_env given (the client env's seam, never a switch for this refusal) or requested for
    the exec. Names only; values never read."""
    refused = refused_variables(harness)
    names = set(_own_environment()) | (set(caller_env) if caller_env is not None else set())
    in_caller = sorted(n for n in names if _refused_name(n, refused))
    if in_caller:
        raise Refused(f"refused variable(s) set in the caller's environment for a {harness} take: {', '.join(in_caller)}")
    asked = sorted(n for n in requested if _refused_name(n, refused))
    if asked:
        raise Refused(f"refused variable(s) requested for a {harness} exec: {', '.join(asked)}")


def exec_argv(container_id: str, inner, *, user: str, workdir: str, harness: str, run_tree: str, login_file: str,
              caller_env=None) -> tuple:
    """One turn's `docker exec` as the agent, and the client environment. The login rides by name only.

    Interface (glitch-f3's ratification, Thu 8 Oct): the required `login_file` is part of exec_argv's signature; the
    login is read from it at exec time by `read_login`, and its value reaches only the client environment.

    Ruling docs-1 (w12a): the turn runs under the launcher, so the agent starts from an empty environment plus its
    TAKE_ENV row and the credential; the client environment is the runtime's needs and the credential alone."""
    harness = _known_harness(harness)
    if harness == CODEX:
        return _codex_exec_argv(container_id, inner, user=user, workdir=workdir, run_tree=run_tree,
                                login_file=login_file, caller_env=caller_env)
    src = os.environ if caller_env is None else caller_env
    login = LOGIN_VARIABLE[harness]
    # Refused names first, from the table alone (so a cross-arm refusal never waits on a PENDING value).
    check_environment(harness, src, set(TAKE_ENV[harness]))
    if user != AGENT_USER:
        raise Refused(f"every exec into the take container runs as the agent, {AGENT_USER}")
    _check_id(container_id, "container id")
    inner = _check_argv(inner)
    workdir = _abs_path(workdir, "workdir") if workdir != "/" else "/"
    check_model(harness, inner)
    if harness == CLAUDE_CODE and [a for a in inner if a == FALLBACK_MODEL_FLAG or a.startswith(FALLBACK_MODEL_FLAG + "=")]:
        raise Refused(f"{FALLBACK_MODEL_FLAG} would configure a model fallback chain: a take runs its pinned model only")
    if harness == CLAUDE_CODE:
        check_claude_settings(inner)
    values = exec_values(harness, run_tree)
    check_environment(harness, src, set(values))
    if login in values:
        raise Refused("the login variable never rides with a value in argv")
    check_login_place(login_file, run_tree)
    value = read_login(login_file, login)
    argv = [RUNTIME_CLIENT, "exec", "--user", AGENT_USER, "--workdir", workdir, "-e", login,
            container_id, *launcher_argv(login, values, inner, harness=harness)]
    env = runtime_env(src)
    env[login] = value
    return argv, env


# ------------------------------------------------------------------------------- the Codex turn (glitch-06, 14 Oct 2026)
# Behind the closed lease gate. The arm's pinned models: prereg-draft.json "models"["O"] (test_run_take binds them).
CODEX_MODELS = ("gpt-6.1-sol", "gpt-6-luna")
# The turn shapes are only what the pinned 0.162.1 help shows and the study uses
# (lane-reports/live-box-evidence-2026-10-13/codex-exec-help.json, sha256 a90c28e8..., and codex-resume-help.json,
# sha256 f145e5b7..., both `docker run ... <the take-o image> codex exec [resume] --help`):
#   `codex exec [OPTIONS] [PROMPT]` and `codex exec [OPTIONS] <COMMAND> [ARGS]` with COMMAND `resume`, whose own usage
#   is `codex exec resume [OPTIONS] [SESSION_ID] [PROMPT]`; the options are exec's, given before `resume`.
#   --json                                      "Print events to stdout as JSONL"
#   -m, --model <MODEL>                         "Model the agent should use"
#   --dangerously-bypass-approvals-and-sandbox  "Skip all confirmation prompts and execute commands without sandboxing.
#                                               ... Intended solely for running in environments that are externally
#                                               sandboxed" (the box is that sandbox; codex_adapter.MODE_FLAGS["bypass"])
#   [PROMPT]  "If not provided as an argument (or if `-` is used), instructions are read from stdin": refused, so a
#             prompt never starts with "-". [SESSION_ID] "Conversation/session id (UUID) or thread name".
# Every other option the help lists (-c, --enable, --disable, --strict-config, -i, --oss, --local-provider, -p, -s,
# --approve-for-me, --dangerously-bypass-hook-trust, -C, --worktree, --add-dir, --thread-source,
# --cyber-access-program, --skip-git-repo-check, --ephemeral, --ignore-user-config, --ignore-rules, --output-schema,
# --color, -o, --last, --all) and every other subcommand (fork, review, help) is refused.
CODEX_CLIENT = "codex"
CODEX_SUBCOMMAND = "exec"
# The pinned help's "Commands:" list for `codex exec` (codex-exec-help.json): a one-word prompt equal to one of them
# would be run as that subcommand (`codex exec [OPTIONS] <COMMAND> [ARGS]`), so it is refused as a prompt (the review
# of 1e10e320, MAJOR). Hidden aliases and subcommands the help does not list are a named residual.
CODEX_HELP_COMMANDS = ("resume", "fork", "review", "help")
CODEX_RESUME = "resume"
CODEX_JSON_FLAG = "--json"
CODEX_MODEL_FLAGS = ("-m", "--model")
CODEX_BYPASS_FLAG = "--dangerously-bypass-approvals-and-sandbox"
_CODEX_SESSION = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{0,127}")


def check_codex_turn(inner) -> str:
    """The Codex turn's argv held to the shapes above; its model, or Refused naming the rule."""
    inner = list(inner)
    if not inner or inner[0] != CODEX_CLIENT:
        raise Refused(f"a Codex turn runs `{CODEX_CLIENT}`, the pinned image's client, by name")
    if len(inner) < 2 or inner[1] != CODEX_SUBCOMMAND:
        raise Refused(f"a Codex turn is `{CODEX_CLIENT} {CODEX_SUBCOMMAND}`")
    counts, model, i = {"json": 0, "model": 0, "bypass": 0}, None, 2
    while i < len(inner) and inner[i].startswith("-"):
        tok = inner[i]
        if tok == CODEX_JSON_FLAG:
            counts["json"] += 1
            i += 1
        elif tok == CODEX_BYPASS_FLAG:
            counts["bypass"] += 1
            i += 1
        elif tok in CODEX_MODEL_FLAGS:
            value = inner[i + 1] if i + 1 < len(inner) else None
            if value is None or value.startswith("-"):
                raise Refused(f"{tok} takes the model as its next argument")
            counts["model"] += 1
            model = value
            i += 2
        else:
            raise Refused(f"unsupported Codex turn argument {tok!r}: a turn uses --json, -m/--model and "
                          f"{CODEX_BYPASS_FLAG}, nothing else")
    if counts["json"] != 1:
        raise Refused(f"a Codex turn passes {CODEX_JSON_FLAG} exactly once")
    if counts["model"] != 1:
        raise Refused("a Codex turn names its model exactly once by -m, never the default")
    if counts["bypass"] != 1:
        raise Refused(f"a Codex turn passes {CODEX_BYPASS_FLAG} exactly once (the box is the sandbox)")
    if model not in CODEX_MODELS:
        raise Refused(f"model {model!r} is not one of the arm's pinned ids: {', '.join(CODEX_MODELS)}")
    rest = inner[i:]
    if rest[:1] == [CODEX_RESUME]:
        if len(rest) != 3:
            raise Refused("`resume` takes exactly a session id and a prompt")
        if not _CODEX_SESSION.fullmatch(rest[1]):
            raise Refused("the resumed session id is not a session id's form")
        prompt = rest[2]
    else:
        if len(rest) != 1:
            raise Refused("a Codex turn ends with exactly one prompt (or `resume <session id> <prompt>`)")
        prompt = rest[0]
        if prompt in CODEX_HELP_COMMANDS:
            raise Refused(f"a one-word prompt {prompt!r} is a `codex exec` subcommand name: it would run as that "
                          f"subcommand, not as the prompt")
    if not prompt or prompt.startswith("-"):
        raise Refused("a Codex turn's prompt never starts with '-' (it would read as a flag, or `-` as stdin)")
    return model


def check_codex_lease_place(lease, run_tree: str) -> None:
    """A Codex turn's login is the lease place_lease put in the per-take config folder, checked after the grant (lane
    vendor-admission round 17, B3; glitch-b5's ruling (a)). The grant makes the folder the agent's (mode 700, its
    mapped host uid), so the host can no longer stat the file inside it: the host checks only what it can read. The
    path: exactly the placed folder's LEASE_FILE, outside the run tree. The folder, by lstat: the folder place_lease
    wrote into (its device and inode), never a link, mode 700, owned by the agent's host uid (derived from the take's
    uid map, which lease_for_take bound; never typed in), outside every repository. The file's own facts (a regular
    file, one link, mode 600, the reading user's, 1 to LEASE_MAX_BYTES bytes) are place_lease's read-back before the
    grant, carried in the placement record; a missing or mismatched record refuses. Named residual: once granted, the
    file is the agent's to change, and the host trusts its placement-time facts until the ownership restore, after
    which postflight admits exactly LEASE_FILE and read_lease_tokens' rules read it again. Nothing is read here."""
    if not isinstance(lease, LeasePlacement):
        raise LoginRefused("no placement record: a Codex turn's login is the record place_lease returned, bound to the "
                           "take's uid map (lease_for_take)")
    path = lease.path
    if not isinstance(path, str) or not os.path.isabs(path) or os.path.normpath(path) != path:
        raise LoginRefused("the lease file is named by a normalised absolute path")
    if os.path.basename(path) != LEASE_FILE:
        raise LoginRefused(f"{path}: a Codex turn's login is the placed lease, {LEASE_FILE}")
    # the file's own facts, as place_lease read them back before the grant
    if stat.S_ISLNK(lease.mode) or not stat.S_ISREG(lease.mode):
        raise LoginRefused(f"{path}: the placed lease must be a regular file, never a link")
    if lease.nlink != 1:
        raise LoginRefused(f"{path}: the placed lease must have exactly one link")
    if stat.S_IMODE(lease.mode) != 0o600:
        raise LoginRefused(f"{path}: the placed lease's mode must be 600")
    if lease.uid != os.getuid():
        raise LoginRefused(f"{path}: the placed lease must have been owned by the reading user when placed")
    if not (isinstance(lease.size, int) and 0 < lease.size <= LEASE_MAX_BYTES):
        raise LoginRefused(f"{path}: the placed lease's size must be 1 to {LEASE_MAX_BYTES} bytes")
    if not lease.uid_map:
        raise LoginRefused(f"{path}: the placement record is not bound to the take's uid map (lease_for_take)")
    agent = host_uid(_uid_of(AGENT_USER), lease.uid_map)
    if _inside(path, _abs_path(run_tree, "run_tree")):
        raise LoginRefused(f"{path}: the lease must sit outside the run tree")
    # the folder, as the host reads it after the grant
    folder = os.path.dirname(path)
    try:
        fst = os.lstat(folder)
    except OSError:
        raise LoginRefused(f"{folder}: the lease's folder does not exist or cannot be read") from None
    if stat.S_ISLNK(fst.st_mode) or not os.path.isdir(folder):
        raise LoginRefused(f"{folder}: the lease's folder must be a folder, never a link")
    if (fst.st_dev, fst.st_ino) != (lease.folder_dev, lease.folder_ino):
        raise LoginRefused(f"{folder}: the lease's folder is not the folder place_lease wrote into")
    if lease.dev != lease.folder_dev:
        raise LoginRefused(f"{path}: the placed lease is not on the device of the folder place_lease wrote into")
    if stat.S_IMODE(fst.st_mode) != 0o700:
        raise LoginRefused(f"{folder}: the lease's folder must be mode 700")
    if fst.st_uid != agent:
        raise LoginRefused(f"{folder}: the lease's folder must be owned by the agent's mapped host uid {agent}")
    if not outside_every_repository(folder):
        raise LoginRefused(f"{path}: the lease must sit outside every repository")


def _codex_exec_argv(container_id: str, inner, *, user: str, workdir: str, run_tree: str, login_file: str,
                     caller_env=None) -> tuple:
    """exec_argv for a Codex row (glitch-06, 14 Oct 2026). The closed lease gate first (NotReady before anything is
    checked or read); then the user, the ids, the turn's shape and model, the refused names over the row's values and
    this process's and the caller's environments, and the placed lease (its placement record, round 17 B3). The turn
    runs under the no-login launcher over exactly the Codex row (CODEX_HOME the config mount, which holds the placed
    auth.json); no credential rides in argv or in the client environment."""
    codex_lease_gate()
    src = os.environ if caller_env is None else caller_env
    if user != AGENT_USER:
        raise Refused(f"every exec into the take container runs as the agent, {AGENT_USER}")
    _check_id(container_id, "container id")
    inner = _check_argv(inner)
    workdir = _abs_path(workdir, "workdir") if workdir != "/" else "/"
    check_codex_turn(inner)
    values = exec_values(CODEX, run_tree)
    check_environment(CODEX, src, set(values))
    check_codex_lease_place(login_file, run_tree)
    argv = [RUNTIME_CLIENT, "exec", "--user", AGENT_USER, "--workdir", workdir, container_id,
            *launcher_argv(NO_LOGIN, values, inner, harness=CODEX)]
    return argv, runtime_env(src)


def config_home_names() -> frozenset:
    """Each harness's config-home variable: the HARNESS_ENV names whose value is the config mount."""
    return frozenset(k for env in HARNESS_ENV.values() for k, v in env.items() if v == CONFIG_MOUNT)


# W4B3-4: a plain exec carries at most one harness's config home.
CONFIG_HOME_MAX = 1


def _config_home_allowed(name, value) -> bool:
    """W4B2-1: only a harness's config-home name, and only at the config mount (never a login, never anything else)."""
    return name in config_home_names() and value == CONFIG_MOUNT


def agent_exec_argv(container_id: str, inner, *, workdir: str = "/", config_home=None) -> list:
    """A plain exec as the agent (preflight's reads): no variable but, when given, one harness's config home."""
    _check_id(container_id, "container id")
    inner = _check_argv(inner)
    workdir = _abs_path(workdir, "workdir") if workdir != "/" else "/"
    extra = []
    if len(config_home or {}) > CONFIG_HOME_MAX:
        raise Refused("a plain exec carries one harness's config home at most")
    for name, value in sorted((config_home or {}).items()):
        if not _config_home_allowed(name, value):
            raise Refused("a plain exec carries only a harness's config home, at the config mount")
        extra += ["-e", f"{name}={value}"]
    return [RUNTIME_CLIENT, "exec", "--user", AGENT_USER, "--workdir", workdir, *extra, container_id, *inner]


# ------------------------------------------------------------------------------------------------ the login read
def outside_every_repository(path: str) -> bool:
    """No ancestor folder of `path` (the path itself included, when a folder) holds a `.git`."""
    p = os.path.realpath(path)
    cur = p if os.path.isdir(p) else os.path.dirname(p)
    while True:
        if os.path.lexists(os.path.join(cur, ".git")):
            return False
        parent = os.path.dirname(cur)
        if parent == cur:
            return True
        cur = parent


LOGIN_MAX_BYTES = 4096


def check_login_place(path: str, run_tree: str) -> None:
    """The walk-token road (box lane, 14 Oct 2026), checked by exec_argv before read_login: the login file has exactly
    one link and sits outside the run tree, in a folder of its own that is never a link, mode 700 and owned by the
    reading user, so no other account can list, replace or hard-link it. read_login's own rules (and its agreement with
    scan_record.read_login, binding 5) are unchanged. Every refusal names the file and the rule, never the value."""
    if not isinstance(path, str) or not os.path.isabs(path):
        raise LoginRefused("the login file is named by an absolute path")
    if _inside(os.path.normpath(path), _abs_path(run_tree, "run_tree")):
        raise LoginRefused(f"{path}: the login file must sit outside the run tree")
    parent = os.path.dirname(os.path.normpath(path))
    try:
        st, pst = os.lstat(path), os.lstat(parent)
    except OSError:
        raise LoginRefused(f"{path}: the login file or its folder does not exist or cannot be read") from None
    if st.st_nlink != 1:
        raise LoginRefused(f"{path}: the login file must have exactly one link")
    if stat.S_ISLNK(pst.st_mode) or not os.path.isdir(parent):
        raise LoginRefused(f"{path}: the login file's folder must be a folder, never a link")
    if stat.S_IMODE(pst.st_mode) != 0o700 or pst.st_uid != os.getuid():
        raise LoginRefused(f"{path}: the login file's folder must be mode 700 and owned by the reading user")


def read_login(path: str, name: str) -> str:
    """The one value of a login file: exactly `name=<20+ chars, no whitespace, no double quote>\\n`, mode 600, owned by
    the reading uid, outside every repository. Every refusal names the file and the rule, never the value."""
    if name == NO_LOGIN:
        raise LoginRefused("a Codex row has no environment login: its login is the lease (place_lease)")
    if not isinstance(name, str) or name not in LOGIN_VARIABLE.values():
        raise LoginRefused(f"the login variable must be one of {sorted(LOGIN_VARIABLE.values())}")
    if not isinstance(path, str) or not os.path.isabs(path):
        raise LoginRefused("the login file is named by an absolute path")
    try:
        st = os.lstat(path)
    except OSError:
        raise LoginRefused(f"{path}: the login file does not exist or cannot be read") from None
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
        raise LoginRefused(f"{path}: the login file must be a regular file, never a link")
    if stat.S_IMODE(st.st_mode) != 0o600:
        raise LoginRefused(f"{path}: the login file's mode must be 600")
    if st.st_uid != os.getuid():
        raise LoginRefused(f"{path}: the login file must be owned by the reading user")

    if not outside_every_repository(path):
        raise LoginRefused(f"{path}: the login file must sit outside every repository")
    if st.st_size > LOGIN_MAX_BYTES:
        raise LoginRefused(f"{path}: the login file holds more than one short line")
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as fh:
            raw = fh.read(LOGIN_MAX_BYTES + 1)
    except OSError:
        raise LoginRefused(f"{path}: the login file cannot be read") from None
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError:
        raise LoginRefused(f"{path}: the login file must be ASCII") from None
    if text.count("\n") != 1 or not text.endswith("\n"):
        raise LoginRefused(f"{path}: the login file must be exactly one newline-terminated line")
    if not text.startswith(name + "="):
        raise LoginRefused(f"{path}: the line must start with {name}=")
    value = text[len(name) + 1:-1]
    if len(value) < 20 or re.search(r'[\s"]', value):
        raise LoginRefused(f"{path}: the value must be at least 20 characters with no whitespace and no double quote")
    return value


# ------------------------------------------------------------------------------------------ the config folder
def make_config_dir(parent: str) -> str:
    """A fresh per-take config folder under `parent`, outside every repository."""
    parent = _abs_path(parent, "config parent")
    if not os.path.isdir(parent):
        raise Refused("the config folder's parent must exist")
    if not outside_every_repository(parent):
        raise Refused("the per-take config folder must sit outside every repository")
    path = os.path.join(parent, "cfg-" + secrets.token_hex(8))
    os.mkdir(path, 0o700)
    return path


# The Codex lease (glitch-06, 14 Oct 2026): the subscription login lives at CODEX_HOME/auth.json, and CODEX_HOME is the
# per-take config folder (the owner's 13 Oct amendment); postflight admits exactly that one file after the take.
LEASE_FILE = "auth.json"
LEASE_MAX_BYTES = 1024 * 1024


@dataclass(frozen=True)
class LeasePlacement:
    """place_lease's placement record (lane vendor-admission round 17, B3): the placed path, the device and inode of
    the folder it was written into, and the file's own lstat facts as place_lease read them back before the grant
    (device, inode, st_mode, links, owner, size). uid_map is empty until lease_for_take binds the take's runtime uid map
    (read at run time from the take container's /proc entry by walk_builders.uid_map_of_pid). After the grant
    check_codex_lease_place reads the file's facts from here; the host can no longer stat the file itself."""
    path: str
    folder_dev: int
    folder_ino: int
    dev: int
    ino: int
    mode: int
    nlink: int
    uid: int
    size: int
    uid_map: tuple = ()


def lease_for_take(placement, uid_map) -> LeasePlacement:
    """The placement record bound to the take's uid map, the lines (container start, host start, length) of the take
    container's /proc uid_map (walk_builders.uid_map_of_pid, never typed in), in which the agent maps exactly once."""
    if not isinstance(placement, LeasePlacement):
        raise LoginRefused("no placement record: a Codex take's lease is the record place_lease returned")
    if not isinstance(uid_map, (list, tuple)) or not uid_map:
        raise LoginRefused("the take's uid map is empty or not a list of (start, host start, length) lines")
    host_uid(_uid_of(AGENT_USER), uid_map)          # each line's shape, and the agent mapped exactly once
    return dataclasses.replace(placement, uid_map=tuple(tuple(row) for row in uid_map))


def codex_lease_gate() -> None:
    """Refuses (NotReady, CODEX_SUBSCRIPTION_NOT_READY) while the Codex lease road's gate is closed."""
    if CODEX_SUBSCRIPTION_READY is not True:
        raise NotReady(CODEX_SUBSCRIPTION_NOT_READY)


def place_lease(lease_src: str, config_dir: str) -> LeasePlacement:
    """Copy the registered Codex lease file into the per-take config folder as LEASE_FILE; its placement record
    (LeasePlacement: the placed path, the folder's device and inode, the read-back facts below). Behind the
    closed gate (codex_lease_gate). The source: an absolute regular file (never a link), one link, mode 600, owned by
    the reading user, outside every repository, 1 to LEASE_MAX_BYTES bytes. The folder: an absolute folder (never a
    link), mode 700, owned by the reading user, outside every repository, not already holding LEASE_FILE. The copy is
    an exclusive no-follow create at mode 600, then lstat checks it: a regular file, one link, mode 600 (a umask that
    narrows it refuses: no chmod, it fails closed), owned by the reading user, the source's size. Every refusal
    (LoginRefused) names the file and the rule, never the contents; a refused copy stays in the folder, which is
    removed with the take's other config files and never launched."""
    codex_lease_gate()
    if not isinstance(lease_src, str) or not os.path.isabs(lease_src):
        raise LoginRefused("the lease file is named by an absolute path")
    try:
        st = os.lstat(lease_src)
    except OSError:
        raise LoginRefused(f"{lease_src}: the lease file does not exist or cannot be read") from None
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
        raise LoginRefused(f"{lease_src}: the lease file must be a regular file, never a link")
    if st.st_nlink != 1:
        raise LoginRefused(f"{lease_src}: the lease file must have exactly one link")
    if stat.S_IMODE(st.st_mode) != 0o600:
        raise LoginRefused(f"{lease_src}: the lease file's mode must be 600")
    if st.st_uid != os.getuid():
        raise LoginRefused(f"{lease_src}: the lease file must be owned by the reading user")
    if not outside_every_repository(lease_src):
        raise LoginRefused(f"{lease_src}: the lease file must sit outside every repository")
    try:
        fd = os.open(lease_src, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as fh:
            data = fh.read(LEASE_MAX_BYTES + 1)
    except OSError:
        raise LoginRefused(f"{lease_src}: the lease file cannot be read") from None
    if len(data) > LEASE_MAX_BYTES:
        raise LoginRefused(f"{lease_src}: the lease file must be at most {LEASE_MAX_BYTES} bytes")
    if not data:
        raise LoginRefused(f"{lease_src}: the lease file is empty")
    if not isinstance(config_dir, str) or not os.path.isabs(config_dir):
        raise LoginRefused("the config folder is named by an absolute path")
    try:
        cst = os.lstat(config_dir)
    except OSError:
        raise LoginRefused(f"{config_dir}: the config folder does not exist or cannot be read") from None
    if stat.S_ISLNK(cst.st_mode) or not os.path.isdir(config_dir):
        raise LoginRefused(f"{config_dir}: the config folder must be a folder, never a link")
    if stat.S_IMODE(cst.st_mode) != 0o700 or cst.st_uid != os.getuid():
        raise LoginRefused(f"{config_dir}: the config folder must be mode 700 and owned by the reading user")
    if not outside_every_repository(config_dir):
        raise LoginRefused(f"{config_dir}: the config folder must sit outside every repository")
    dst = os.path.join(config_dir, LEASE_FILE)
    if os.path.lexists(dst):
        raise LoginRefused(f"{dst}: the config folder already holds {LEASE_FILE}")
    try:
        fd = os.open(dst, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
    except OSError:
        raise LoginRefused(f"{dst}: the lease could not be written") from None
    try:
        pst = os.lstat(dst)
    except OSError:
        raise LoginRefused(f"{dst}: the placed lease cannot be read back") from None
    if stat.S_ISLNK(pst.st_mode) or not stat.S_ISREG(pst.st_mode) or pst.st_nlink != 1:
        raise LoginRefused(f"{dst}: the placed lease must be a regular file with exactly one link")
    if stat.S_IMODE(pst.st_mode) != 0o600:
        raise LoginRefused(f"{dst}: the placed lease's mode must be 600 (a umask narrowed it; nothing widens it)")
    if pst.st_uid != os.getuid():
        raise LoginRefused(f"{dst}: the placed lease must be owned by the reading user")
    if pst.st_size != len(data):
        raise LoginRefused(f"{dst}: the placed lease is not the whole lease file")
    return LeasePlacement(path=dst, folder_dev=cst.st_dev, folder_ino=cst.st_ino, dev=pst.st_dev, ino=pst.st_ino,
                          mode=pst.st_mode, nlink=pst.st_nlink, uid=pst.st_uid, size=pst.st_size)


def remove_config_dir(launched: "Launched", *, published: bool) -> str:
    """Delete the config folder by the path launch recorded, and only once the take's records are published."""
    if published is not True:
        raise Refused("the config folder is deleted only once the take's records are published")
    path = launched.config_dir
    if not path or not os.path.isabs(path):
        raise Refused("no config folder was recorded at launch")
    if not outside_every_repository(path):
        raise Refused("the recorded config folder is inside a repository; nothing is deleted")
    if os.path.islink(path) or not os.path.isdir(path):
        raise Refused("the recorded config folder is not a folder")
    shutil.rmtree(path)
    return path


# ------------------------------------------------------------------------------------------------ launch records
def _check_id(v, what: str) -> str:
    if not isinstance(v, str) or not _HEX64.fullmatch(v):
        raise Refused(f"{what} must be a full 64-hex id")
    return v


@dataclass(frozen=True)
class SidecarLaunch:
    create_argv: tuple
    start_argv_for: Callable
    ctl_argv_for: Callable
    rm_argv_for: Callable
    expect: dict


@dataclass(frozen=True)
class ProxyLaunch:
    image: str
    conf_source: str
    conf_target: str
    command: tuple
    user: str
    alias: str


@dataclass
class Launched:
    """Every id the moment the runtime returned it, every argv and every inspect: the launch record. `spec` is the
    take's spec on the network launch made (W4B1-1): the drive step hands that one to preflight."""
    config_dir: str | None = None
    spec: TakeSpec | None = None
    network_id: str | None = None
    proxy_id: str | None = None
    sidecar_id: str | None = None
    take_id: str | None = None
    steps: list = field(default_factory=list)
    ok: bool = False
    failure: str | None = None
    torn_down: list = field(default_factory=list)

    def ids(self) -> list:
        return [i for i in (self.take_id, self.sidecar_id, self.proxy_id) if i]

    def to_record(self) -> dict:
        return {"ok": self.ok, "failure": self.failure, "config_dir": self.config_dir,
                "network_id": self.network_id, "proxy_id": self.proxy_id, "sidecar_id": self.sidecar_id,
                "take_id": self.take_id, "steps": list(self.steps), "torn_down": list(self.torn_down)}


LAUNCH_RECORD = "launch.json"
PROXY_LOG = "proxy.log"
STEP_TIMEOUT_S = 120


class _StepFailed(RuntimeError):
    pass


def _step(runtime, launched: Launched, name: str, argv: list, env: dict) -> Completed:
    try:
        c = runtime.run(list(argv), env=env, timeout=STEP_TIMEOUT_S)
    except TimeoutError:
        launched.steps.append({"step": name, "argv": list(argv), "returncode": None, "timed_out": True})
        raise _StepFailed(f"{name}: timed out") from None
    entry = {"step": name, "argv": list(argv), "returncode": c.returncode}
    launched.steps.append(entry)
    if c.returncode != 0:
        raise _StepFailed(f"{name}: exit {c.returncode}")
    return c


def _new_id(c: Completed, what: str) -> str:
    out = c.stdout.strip()
    if not _HEX64.fullmatch(out):
        raise _StepFailed(f"{what}: the runtime returned no full id")
    return out


def _inspect(runtime, launched: Launched, name: str, cid: str, env: dict) -> dict:
    c = _step(runtime, launched, name, [RUNTIME_CLIENT, "container", "inspect", cid], env)
    try:
        doc = json.loads(c.stdout)
    except ValueError:
        raise _StepFailed(f"{name}: the inspect is not JSON") from None
    if not (isinstance(doc, list) and len(doc) == 1 and isinstance(doc[0], dict)):
        raise _StepFailed(f"{name}: the inspect is not exactly one object")
    launched.steps[-1]["inspect"] = doc[0]
    return doc[0]


def _proxy_uid(user: str):
    """The uid of a `uid[:gid]` or `name[:gid]` spelling, numerically (None for a name); refuses any other form."""
    m = re.fullmatch(r"([0-9]+|[a-z_][a-z0-9_-]*)(:[0-9]+)?", user) if isinstance(user, str) else None
    if m is None:
        raise Refused("the proxy user is uid[:gid] or name[:gid]")
    head = m.group(1)
    if head.isdigit():
        return int(head)
    return 0 if head == "root" else None


def _check_proxy(proxy: ProxyLaunch) -> None:
    if not isinstance(proxy, ProxyLaunch):
        raise Refused("proxy must be a ProxyLaunch")
    if _is_pending(proxy.user) or _is_pending(proxy.command) or _is_pending(proxy.image):
        raise NotReady("the proxy's user (squid's package user) is PENDING until a built image tells it")
    if _proxy_uid(proxy.user) == 0:
        raise Refused("the proxy runs as squid's own non-root user, never uid 0 in any spelling")
    if proxy.alias != PROXY_ALIAS:
        raise Refused(f"the proxy's alias is {PROXY_ALIAS}")
    if not isinstance(proxy.image, str) or not _IMAGE_ID.fullmatch(proxy.image):
        raise Refused("the proxy image is pinned by its id")
    _abs_path(proxy.conf_source, "proxy conf_source")
    _abs_path(proxy.conf_target, "proxy conf_target")
    _check_argv(proxy.command)


def _check_sidecar(sidecar: SidecarLaunch) -> None:
    if not isinstance(sidecar, SidecarLaunch):
        raise Refused("sidecar must be a SidecarLaunch")
    argv = _check_argv(sidecar.create_argv)
    if argv[:2] != [RUNTIME_CLIENT, "create"]:
        raise Refused("the sidecar's create argv starts with docker create")
    if not isinstance(sidecar.expect, dict):
        raise Refused("the sidecar's expectation is a dict")


# glitch-06's ruling on P-2 (14 Oct 2026): the egress proxy's and the sidecar's memory caps. The sidecar's is applied
# here, by launch, to the caller's sidecar create argv (sidecar_create_argv), so box/sidecar.py stays byte-identical
# to the program baked into the locked sidecar image (the lock's re-derivation guard, tests/test_image.py).
# Policy beside it (P-1 and P-2, the same ruling): a take's cgroup counters are read every turn and an oom_kill rise is
# routed by routing.json (row cgroup-kill); the first walk records each turn's memory.peak and pids.peak, and a cap is
# re-ruled before measured takes if a rehearsal OOMs, never mid-run; no athena_suite or other heavy job runs while any
# take runs.
PROXY_MEMORY_BYTES = 512 * 1024 * 1024
SIDECAR_MEMORY_BYTES = 512 * 1024 * 1024


def sidecar_create_argv(sidecar: SidecarLaunch) -> list:
    """The sidecar's `docker create` as launch runs it: the caller's argv with the memory cap after `create`."""
    argv = _check_argv(sidecar.create_argv)
    if argv[:2] != [RUNTIME_CLIENT, "create"] or any(a.startswith("--memory") or a.startswith("-m") for a in argv):
        raise Refused("the sidecar's create argv starts with docker create and sets no memory value of its own "
                      "(--memory or -m, in any spelling)")
    return argv[:2] + ["--memory", str(SIDECAR_MEMORY_BYTES)] + argv[2:]


def proxy_create_argv(network_id: str, proxy: ProxyLaunch) -> list:
    _check_proxy(proxy)
    return [RUNTIME_CLIENT, "create", "--pull=never", "--network", _check_id(network_id, "network id"),
            "--network-alias", PROXY_ALIAS, "--user", proxy.user,
            "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--memory", str(PROXY_MEMORY_BYTES),
            "--mount", f"type=bind,source={proxy.conf_source},target={proxy.conf_target},readonly",
            proxy.image, *proxy.command]


def network_name() -> str:
    """A fresh, neutral name for the take's internal network (the runtime needs one; removal is by id)."""
    return "n" + secrets.token_hex(12)


def _check_launch_ready(sidecar: SidecarLaunch) -> None:
    """W4B1-2: NotReady before any runtime call while an inspect spelling or the sidecar's expectation is PENDING."""
    if _is_pending(INSPECT_STATUS):
        raise NotReady(f"INSPECT_STATUS is PENDING: {PENDING_WHY['INSPECT_STATUS']}")
    if isinstance(sidecar, SidecarLaunch) and _is_pending(sidecar.expect):
        raise NotReady("the sidecar's expectation holds a PENDING value (its added capability's spelling)")


def _on_network(spec: TakeSpec, network_id: str) -> TakeSpec:
    """W4B1-1: the take's spec on the network launch just made, never the caller's."""
    return dataclasses.replace(spec, network=network_id)


def launch(runtime, spec: TakeSpec, *, sidecar: SidecarLaunch, proxy: ProxyLaunch, record_dir: str,
           caller_env=None) -> Launched:
    """Network, proxy, sidecar, take container, each created, inspected where interface 12 says, then started. A
    failure tears down everything made so far by its recorded id and raises LaunchError carrying the record. No agent
    turn ever runs here. The launch record is written to `record_dir` either way.

    Interface (glitch-f3's ratification, Thu 8 Oct): the required `record_dir` is part of launch's signature; the launch
    record and, at teardown, the proxy log are written there, beside the evidence folder.

    W4B2-3: `spec.network` is a placeholder 64-hex id the drive step passes (it cannot know the id yet); launch
    replaces it with the network it creates, and `Launched.spec` carries the spec preflight must use."""
    from box import preflight  # the take's expected inspect (interface 13); imported here, preflight imports us

    check_spec(spec)
    refuse_env_files(workdir=spec.run_tree, run_tree=spec.run_tree, config_dir=spec.config_dir)
    _check_proxy(proxy)
    _check_sidecar(sidecar)
    _check_launch_ready(sidecar)
    record_dir = _abs_path(record_dir, "record_dir")
    if not os.path.isdir(record_dir) or os.path.lexists(os.path.join(record_dir, LAUNCH_RECORD)):
        raise Refused("the record folder must exist and hold no launch record yet")
    if not os.path.isdir(spec.config_dir) or not outside_every_repository(spec.config_dir):
        raise Refused("the per-take config folder must exist outside every repository")
    env = runtime_env(caller_env)
    launched = Launched(config_dir=spec.config_dir)
    try:
        c = _step(runtime, launched, "network-create",
                  [RUNTIME_CLIENT, "network", "create", "--internal", network_name()], env)
        launched.network_id = _new_id(c, "network-create")
        c = _step(runtime, launched, "proxy-create", proxy_create_argv(launched.network_id, proxy), env)
        launched.proxy_id = _new_id(c, "proxy-create")
        _step(runtime, launched, "proxy-connect",
              [RUNTIME_CLIENT, "network", "connect", DEFAULT_NETWORK, launched.proxy_id], env)
        _step(runtime, launched, "proxy-start", [RUNTIME_CLIENT, "start", launched.proxy_id], env)
        c = _step(runtime, launched, "sidecar-create", sidecar_create_argv(sidecar), env)
        launched.sidecar_id = _new_id(c, "sidecar-create")
        got = _inspect(runtime, launched, "sidecar-inspect", launched.sidecar_id, env)
        bad = preflight.inspect_mismatches(got, sidecar.expect, kind="sidecar")
        if bad:
            raise _StepFailed("sidecar-inspect: " + "; ".join(bad))
        _step(runtime, launched, "sidecar-start", list(sidecar.start_argv_for(launched.sidecar_id)), env)
        launched.spec = spec = _on_network(spec, launched.network_id)
        take_expect = preflight.expected_take_inspect(spec)
        c = _step(runtime, launched, "take-create", create_argv(spec), env)
        launched.take_id = _new_id(c, "take-create")
        got = _inspect(runtime, launched, "take-inspect", launched.take_id, env)
        bad = preflight.inspect_mismatches(got, take_expect, kind="take")
        if bad:
            raise _StepFailed("take-inspect: " + "; ".join(bad))
        _step(runtime, launched, "take-start", [RUNTIME_CLIENT, "start", launched.take_id], env)
    except Exception as exc:  # every failure: tear down by recorded id, record, carry the record out
        launched.failure = str(exc) if isinstance(exc, (_StepFailed, Refused, NotReady)) else type(exc).__name__
        _teardown_partial(runtime, launched, sidecar, record_dir, env)
        _write_json(os.path.join(record_dir, LAUNCH_RECORD), launched.to_record())
        raise LaunchError(f"launch failed: {launched.failure}", launched) from exc
    launched.ok = True
    _write_json(os.path.join(record_dir, LAUNCH_RECORD), launched.to_record())
    return launched


def _write_json(path: str, doc: dict) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True)
        fh.write("\n")


def _rm(runtime, cid: str, env: dict, sidecar: SidecarLaunch | None = None, kind: str = "") -> Completed:
    argv = list(sidecar.rm_argv_for(cid)) if (sidecar is not None and kind == "sidecar") \
        else [RUNTIME_CLIENT, "rm", "--force", cid]
    return runtime.run(argv, env=env, timeout=STEP_TIMEOUT_S)


def _capture_proxy_log(runtime, proxy_id: str, record_dir: str, env: dict) -> Completed:
    c = runtime.run([RUNTIME_CLIENT, "logs", proxy_id], env=env, timeout=STEP_TIMEOUT_S)
    path = os.path.join(record_dir, PROXY_LOG)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(fd, "w", encoding="utf-8", errors="surrogateescape") as fh:
        fh.write(c.stdout)
        fh.write(c.stderr)
    return c


def _teardown_partial(runtime, launched: Launched, sidecar: SidecarLaunch, record_dir: str, env: dict) -> None:
    """After a launch failure: remove what was made, in teardown order, each by its recorded id. No `finish`: the
    sidecar never began."""
    plan = []
    if launched.take_id:
        plan.append(("take-rm", lambda: _rm(runtime, launched.take_id, env)))
    if launched.proxy_id:
        plan.append(("proxy-logs", lambda: _capture_proxy_log(runtime, launched.proxy_id, record_dir, env)))
    if launched.sidecar_id:
        plan.append(("sidecar-rm", lambda: _rm(runtime, launched.sidecar_id, env, sidecar, "sidecar")))
    if launched.proxy_id:
        plan.append(("proxy-rm", lambda: _rm(runtime, launched.proxy_id, env)))
    if launched.network_id:
        plan.append(("network-rm", lambda: runtime.run([RUNTIME_CLIENT, "network", "rm", launched.network_id],
                                                       env=env, timeout=STEP_TIMEOUT_S)))
    for name, fn in plan:
        try:
            c = fn()
            launched.torn_down.append({"step": name, "returncode": c.returncode})
        except Exception as exc:  # recorded, never stops the rest
            launched.torn_down.append({"step": name, "returncode": None, "error": type(exc).__name__})


def teardown(runtime, launched: Launched, *, sidecar: SidecarLaunch, record_dir: str, caller_env=None) -> dict:
    """Interface 12's teardown order, each by its recorded id: the take container removed, then `ctl finish`, then
    the proxy's log captured into the record folder, then the sidecar, the proxy and the network removed. A step that
    fails is recorded and the rest still run; `finish` is skipped when the take's removal failed (it is called only
    after the take container is gone). Raises TeardownError when any step failed."""
    if not isinstance(launched, Launched) or not launched.ok:
        raise Refused("teardown takes the record of a completed launch")
    record_dir = _abs_path(record_dir, "record_dir")
    env = runtime_env(caller_env)
    steps, problems = [], []

    def do(name, fn):
        try:
            c = fn()
        except Exception as exc:
            steps.append({"step": name, "returncode": None, "error": type(exc).__name__})
            problems.append(name)
            return None
        steps.append({"step": name, "argv_ok": True, "returncode": c.returncode, "stdout": c.stdout
                      if name == "sidecar-finish" else None})
        if c.returncode != 0:
            problems.append(name)
        return c

    take = do("take-rm", lambda: _rm(runtime, launched.take_id, env))
    if take is not None and take.returncode == 0:
        do("sidecar-finish", lambda: runtime.run(list(sidecar.ctl_argv_for(launched.sidecar_id, "finish", None)),
                                                 env=env, timeout=STEP_TIMEOUT_S))
    else:
        steps.append({"step": "sidecar-finish", "skipped": "the take container was not removed"})
        problems.append("sidecar-finish")
    do("proxy-logs", lambda: _capture_proxy_log(runtime, launched.proxy_id, record_dir, env))
    do("sidecar-rm", lambda: _rm(runtime, launched.sidecar_id, env, sidecar, "sidecar"))
    do("proxy-rm", lambda: _rm(runtime, launched.proxy_id, env))
    do("network-rm", lambda: runtime.run([RUNTIME_CLIENT, "network", "rm", launched.network_id], env=env,
                                         timeout=STEP_TIMEOUT_S))
    record = {"ok": not problems, "steps": steps, "problems": problems}
    if problems:
        raise TeardownError(f"teardown: {', '.join(problems)} failed", record)
    return record


# ------------------------------------------------------------------------------------------- leaked containers
def leaked(runtime, recorded_ids, *, caller_env=None) -> list:
    """The recorded ids still present in the runtime's full-id listing of every container (no filter, ever)."""
    ids = [_check_id(i, "recorded id") for i in recorded_ids]
    c = runtime.run([RUNTIME_CLIENT, "ps", "--all", "--no-trunc", "--quiet"], env=runtime_env(caller_env),
                    timeout=STEP_TIMEOUT_S)
    if c.returncode != 0:
        raise Refused(f"the container listing failed (exit {c.returncode}): a restart is refused unread")
    listed = set(line.strip() for line in c.stdout.splitlines() if line.strip())
    bad = [line for line in listed if not _HEX64.fullmatch(line)]
    if bad:
        raise Refused("the container listing holds a line that is not a full id")
    return [i for i in ids if i in listed]


def refuse_restart_if_leaked(runtime, recorded_ids, *, caller_env=None) -> None:
    """A leaked container that is still present refuses the restart and names the container."""
    still = leaked(runtime, recorded_ids, caller_env=caller_env)
    if still:
        raise LeakedContainer(f"restart refused: leaked container(s) still present: {', '.join(still)}")


# ---------------------------------------------------------------------------------- the agent's leftover processes
def host_uid(container_uid: int, uid_map) -> int:
    """The host uid a container uid maps to, through `uid_map` lines (container start, host start, length)."""
    if not _int_ge0(container_uid):
        raise Refused("a container uid is a non-negative int")
    hits = []
    for row in uid_map:
        if not (isinstance(row, (list, tuple)) and len(row) == 3 and all(_int_ge0(x) for x in row)) or row[2] == 0:
            raise Refused("a uid map line is (container start, host start, length > 0)")
        start, host, length = row
        if start <= container_uid < start + length:
            hits.append(host + container_uid - start)
    if len(hits) != 1:
        raise Refused(f"container uid {container_uid} is mapped {len(hits)} times, never exactly once")
    return hits[0]


def _int_ge0(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool) and v >= 0


def _uid_of(user: str) -> int:
    return int(user.split(":")[0])


def agent_processes(runtime, take_id: str, *, agent_uid: int, uid_map, caller_env=None) -> list:
    """Host pids of the agent's processes, comparing UIDs in docker top's measured namespace."""
    if _is_pending(TOP_FORMAT):
        raise NotReady(f"TOP_FORMAT is PENDING: {PENDING_WHY['TOP_FORMAT']}")
    mapped = host_uid(agent_uid, uid_map)  # validate the real mapping even when top reports container UIDs
    namespace = TOP_FORMAT.get("uid_namespace")
    if namespace not in ("host", "container"):
        raise Refused("docker top's UID namespace must be measured as host or container")
    want = mapped if namespace == "host" else agent_uid
    argv = [RUNTIME_CLIENT, "top", _check_id(take_id, "take id"), *TOP_FORMAT["ps_options"]]
    c = runtime.run(argv, env=runtime_env(caller_env), timeout=STEP_TIMEOUT_S)
    if c.returncode != 0:
        raise Refused(f"docker top failed (exit {c.returncode}): the processes are unknown, never none")
    lines = [ln for ln in c.stdout.splitlines() if ln.strip()]
    if not lines:
        raise Refused("docker top printed no header")
    head = lines[0].split()
    try:
        pi, ui = head.index(TOP_FORMAT["pid_column"]), head.index(TOP_FORMAT["uid_column"])
    except ValueError:
        raise Refused("docker top's header lacks the measured pid or uid column") from None
    pids = []
    for ln in lines[1:]:
        cols = ln.split()
        if len(cols) <= max(pi, ui) or not cols[pi].isdigit() or not cols[ui].isdigit():
            raise Refused("docker top printed a row off its measured form")
        if int(cols[ui]) == want:
            pids.append(int(cols[pi]))
    return pids


def kill_agent(runtime, take_id: str, *, agent_user: str, caller_env=None) -> Completed:
    """An exec as the agent's own uid that sends KILL to all of that uid's processes (no capability needed)."""
    if agent_user != AGENT_USER:
        raise Refused(f"the kill runs as the agent's own uid, {AGENT_USER}, never root or the keep-alive")
    # The pinned procps kill rejects the old `kill -s KILL -- -1` form. The image's isolated Python invokes
    # the same-user kernel primitive directly; the distinct keepalive uid survives (live probe 13 Oct 2026).
    argv = [RUNTIME_CLIENT, "exec", "--user", AGENT_USER, _check_id(take_id, "take id"),
            "/usr/bin/python3", "-I", "-S", "-c", "import os,signal\ntry:\n os.kill(-1, signal.SIGKILL)\nexcept ProcessLookupError:\n pass"]
    return runtime.run(argv, env=runtime_env(caller_env), timeout=STEP_TIMEOUT_S)


def wait_gone(runtime, take_id: str, *, agent_uid: int, uid_map, cap_s: float, interval_s: float, clock, sleep,
              caller_env=None) -> list:
    """Poll until no agent process remains or the cap passes; return the survivors (empty when gone)."""
    if not (isinstance(cap_s, (int, float)) and cap_s >= 0 and isinstance(interval_s, (int, float))
            and interval_s > 0):
        raise Refused("cap_s >= 0 and interval_s > 0")
    start = clock()
    while True:
        procs = agent_processes(runtime, take_id, agent_uid=agent_uid, uid_map=uid_map, caller_env=caller_env)
        if not procs:
            return []
        if clock() - start >= cap_s:
            return procs
        sleep(interval_s)


# ------------------------------------------------------------------------------------------------ the counters
# Each counter's read key is its COUNTER_FIELDS name less `_delta`; the file and line it is read from.
COUNTER_SOURCES = {"oom_kill": ("memory.events", "oom_kill"), "pids_max": ("pids.events", "max")}
_DELTA = "_delta"


def counters(cgroup_dir: str) -> dict:
    """`oom_kill` from memory.events and `max` from pids.events, read host-side. A missing file or line raises."""
    out = {}
    for key, (fname, line_key) in COUNTER_SOURCES.items():
        path = os.path.join(cgroup_dir, fname)
        try:
            with open(path, encoding="ascii") as fh:
                text = fh.read()
        except OSError:
            raise Refused(f"{fname} cannot be read: the counter is unknown, never zero") from None
        vals = [ln.split() for ln in text.splitlines() if ln.split()[:1] == [line_key]]
        if len(vals) != 1 or len(vals[0]) != 2 or not vals[0][1].isdigit():
            raise Refused(f"{fname} holds no single '{line_key} <n>' line")
        out[key] = int(vals[0][1])
    return out


def counter_delta(before: dict, after: dict) -> dict:
    """The rise of each counter, keyed by agent_adapter.COUNTER_FIELDS. A counter that fell is refused."""
    delta = {}
    for f in agent_adapter.COUNTER_FIELDS:
        key = f[:-len(_DELTA)] if f.endswith(_DELTA) else None
        if key not in COUNTER_SOURCES:
            raise Refused(f"no source for counter field {f}")
        if not (_int_ge0(before.get(key)) and _int_ge0(after.get(key))):
            raise Refused(f"counter {key} missing from a reading")
        d = after[key] - before[key]
        if d < 0:
            raise Refused(f"counter {key} fell: not the same cgroup")
        delta[f] = d
    return delta


# ----------------------------------------------------------------------------------------------- the exit record
def _path_get(doc: dict, dotted: str):
    cur = doc
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            raise KeyError(dotted)
        cur = cur[part]
    return cur


def container_state(runtime, cid: str, *, caller_env=None) -> dict:
    """The runtime's exit record: Running, ExitCode and OOMKilled from the inspect's State."""
    if _is_pending(INSPECT_STATUS):
        raise NotReady(f"INSPECT_STATUS is PENDING: {PENDING_WHY['INSPECT_STATUS']}")
    c = runtime.run([RUNTIME_CLIENT, "container", "inspect", _check_id(cid, "container id")],
                    env=runtime_env(caller_env), timeout=STEP_TIMEOUT_S)
    if c.returncode != 0:
        raise Refused(f"inspect failed (exit {c.returncode}): the state is unknown")
    try:
        doc = json.loads(c.stdout)
        obj = doc[0] if isinstance(doc, list) and len(doc) == 1 else None
        running = _path_get(obj, INSPECT_PATHS["running"])
        code = _path_get(obj, INSPECT_PATHS["exit_code"])
        oom = _path_get(obj, INSPECT_PATHS["oom_killed"])
    except (ValueError, KeyError, TypeError):
        raise Refused("the inspect holds no State record") from None
    if not isinstance(running, bool) or not isinstance(oom, bool) or not (isinstance(code, int)
                                                                          and not isinstance(code, bool)):
        raise Refused("the inspect's State fields are off their types")
    return {"running": running, "exit_code": code, "oom_killed": oom}


# ----------------------------------------------------------------------------- B11: the per-take config folder, per turn
# glitch-26's rulings on lane vendor-b11, round 3 (Mon 19 Oct 2026), on the B11 design note (lane-reports/
# B11-DESIGN-NOTE.md, sections 2 to 7). Arms O and G only: before every codex or gemini turn, immediately before
# exec_argv, run_turn checks the take's config folder (CODEX_HOME / GEMINI_CLI_HOME, the agent's to write since the
# grant) and the agent's HOME (<run tree>/.home). Arm A keeps its own guard, settings_guard over the sidecar's
# snapshots, and its road is unchanged: run_turn never calls this for claude-code (the named difference is a row of the
# codex2 sign-in plan's section 6 table).
#   R-C   the folder is read by ONE census (ownership.operator_census: every entry's lstat facts, never a byte), plus
#         operator_read of exactly what the note's section 6 point 2 lists, nothing else.
#   R-CF  before turn 1 the folder holds exactly the placed set; after it, the placed set (config.toml and
#         .gemini/settings.json byte-identical to take_config.files_for, every turn) plus the note's section 2
#         allow-list, nothing else. A refusal is ConfigFolderRefused, routed as settings_guard.snapshot_problems is
#         (R4-1, drive.py's edit D: before turn 1 a rehearsal; after it a stop for a ruling, DriveRefused, recorded
#         failed with drive_started true); the turn's exec never runs.
#   R-H2  auth.json by its facts only, from the census: a regular file, one link, mode 600, the agent's owner, the
#         device and inode place_lease recorded, 1 to LEASE_MAX_BYTES bytes. Never its bytes.
#   R-H3  a killed Codex turn's leftovers (section 5 H3), the four arg0 links at their one folder shape with the
#         image's codex executable as target; any other link refuses.
#   R-H4  a killed Gemini turn's leftovers (section 5 H4).
#   R4-6  plugins/** (R4: remote-installed plugins), cloud-config-bundle-cache.json (R5: the codex2 plan is not ruled
#         eligible) and db-backups/** (R6) refuse, each named.
#   R-OA  <run tree>/.home: a folder (never a link) of mode 700, owned by the agent's mapped host uid.
CONFIG_FOLDER_HARNESSES = (CODEX, GEMINI)
# The pinned sources the allow-list below was read from (the B11 design note's "Sources read"); tests bind them, and a
# version bump of either CLI's image lock breaks that binding on purpose.
CONFIG_FOLDER_SOURCES = {
    CODEX: {"package": "openai/codex", "tag": "rust-v0.162.1", "version": "0.162.1",
            "commit": "092d3acd6bec3e3a14bdc7e7a2810ab628ab759d"},
    GEMINI: {"package": "@google/gemini-cli", "version": "0.64.0",
             "tarball_sha256": "891a794e55c8319b6b78f6f8f13d6b8b2782a4709dfd2fcabf3a1f63ae8365e6",
             "bundle_sha256": {
                 "bundle/gemini.js": "ab113d84c8f1692fd6c95081366718897876d8664328c7bf0ccf9437d688145f",
                 "bundle/gemini-Q2GRYIAK.js": "7702da31cf099ca3e1d64fd195f15b7726b2c2829ec21e955558eb9dbfba47da",
                 "bundle/chunk-NR7L3FXV.js": "d566e81b1df8d4d44a91bf7aeea96a58ec0e6c8934fa424315ef060507dcbb8c",
                 "bundle/chunk-FLKY6NH5.js": "f6a4ddd46350dad40515218069d369aaa0025f194c552400b69925b941098bc8",
                 "bundle/chunk-MA35JFUP.js": "5afb745a6015fcdd0108c6fa33112e8250bb93774e73634641f458e89f990985",
                 "bundle/chunk-VOLZQW4I.js": "2aea2b74a0f598e459f1d86913f6f24f18a113caff022dc1d9354d744a3a86b6"}},
}
# R-H3: a Codex process that is killed, or that exits without unwinding (clap's own exit after --version), leaves its
# arg0 helper folder: CODEX_HOME/tmp/arg0/codex-arg0<6 tempfile characters>/ with .lock and four links, each to
# std::env::current_exe() (codex-rs/arg0/src/lib.rs at rust-v0.162.1: names 21-24 and sandboxing/src/landlock.rs 7,
# .lock 25, the folder 358 and 373-375, the links 387-401). The executable is the pinned take-o image's, as measured
# (lane-reports/stub-take-20261014/probes/codex-env-name-sweep-athena-20261014.json, sha256 ddb31eec..., binary_path;
# its image is box/codex/image.lock's image_id, sha256:21b21415...). take_config.config_sha256 reads the same rule.
CODEX_ARG0_LINKS = ("apply_patch", "applypatch", "codex-linux-sandbox", "codex-execve-wrapper")
CODEX_ARG0_DIR = re.compile(r"tmp/arg0/codex-arg0[A-Za-z0-9]{6}")
CODEX_EXECUTABLE = ("/usr/local/lib/node_modules/@openai/codex/node_modules/@openai/codex-linux-x64/vendor/"
                    "x86_64-unknown-linux-musl/bin/codex")


def codex_arg0_link(rel: str, target) -> bool:
    """Is `rel` (relative to CODEX_HOME, `/`-separated) one of a killed Codex process's four arg0 links, at its one
    folder shape, with the image's codex executable as its target (compared as a string, never followed)?"""
    folder, _, name = rel.rpartition("/")
    return CODEX_ARG0_DIR.fullmatch(folder) is not None and name in CODEX_ARG0_LINKS and target == CODEX_EXECUTABLE


# Codex's embedded system skills at the pin (codex-rs/skills/src/assets/samples, include_dir!, skills/src/lib.rs 55),
# installed into CODEX_HOME/skills/.system on a start whose marker differs (skills/src/lib.rs 77-100). Each file's
# sha256: 48 files in 21 folders, no links; `find . -type f | sort | xargs sha256sum | sha256sum` over them is the
# note's f5702460... (CODEX_SYSTEM_SKILLS_SHA256, bound by the tests). An edited file with its marker untouched is
# loaded as a skill (the note's section 4), so each one present is read and compared. The marker itself is a Rust
# DefaultHasher value, admitted by name (a named residual: its content is not checked).
CODEX_SYSTEM_SKILLS_SHA256 = "f5702460ae03a0bd98d89a01224afb315f70313a06db41284cab367ac468d55d"
# HELD (lane vendor-b11 round 3): the pre-push secret scan (gitleaks generic-api-key) flagged two files' sha256 digests
# in this table, for their names (an "api" and a "key"), and they stayed out, failing closed. ADMITTED on Javier's word
# skill-digests (Mon 19 Oct 2026, typed in glitch-26's window): both are sha256 digests of public files, read from
# openai/codex at 092d3acd (rust-v0.162.1), and with them the 48 files' aggregate is CODEX_SYSTEM_SKILLS_SHA256. Each of
# the two lines carries the scanner's own inline allow. A digest held again goes back in this tuple, its value to None.
CODEX_SYSTEM_SKILLS_HELD = ()
CODEX_SYSTEM_SKILLS_MARKER = ".codex-system-skills.marker"
CODEX_SYSTEM_SKILLS = {
    "imagegen/LICENSE.txt": "4dd13869245e356246a5b770723247bbb80a8f07a181d1d3d873a1734297cdb9",
    "imagegen/SKILL.md": "681ddb4ad6d06a2acc78a3535b583f8d0c1ea800ecda3d56370d3310fd2cd4ba",
    "imagegen/agents/openai.yaml": "9ca574af14580dc7a2a3dc37a1796d17f93cb8850be66501f0799ef8603e9dc0",
    "imagegen/assets/imagegen-small.svg": "cff5f34f57ff60b3ee92eaedd17b15e96dd4b9e776df3e78936c9e00d42be294",
    "imagegen/assets/imagegen.png": "95952f644064eb9e890f98d8db07216347186526e4c41ad66d3420629eb86e20",
    "imagegen/references/cli.md": "ecfc2e09261a0feb3482517a5fa0ff410cb7d1958e3cbd2ac6b61586f5b81405",
    "imagegen/references/codex-network.md": "c88298ca4481f6116a16fa7987434fc977f8b311c1bbc0c3d862ffd0c5981148",
    "imagegen/references/image-api.md": "dc975d7af8a4888967251a0276014b4a71ea30455294944b762256373ce3e569",  # gitleaks:allow
    "imagegen/references/prompting.md": "b210b051c775860267080941eba968212bf0ac7fce581d75c5dcc217d8293f8b",
    "imagegen/references/sample-prompts.md": "70474177d151855b175c6133de2aae1d90b7f146b0dab50ec830972c47d72183",
    "imagegen/scripts/image_gen.py": "b4345cf835e5b593b97df6bb2b70bda493b8a97eee4cabbc99b2fa57dba9b448",
    "imagegen/scripts/remove_chroma_key.py": "a5893c4bd04b21abced33731ea89d2ac428e81d92a0368eb18ffbe4fda5253e2",  # gitleaks:allow
    "openai-docs/LICENSE.txt": "4dd13869245e356246a5b770723247bbb80a8f07a181d1d3d873a1734297cdb9",
    "openai-docs/SKILL.md": "aa6829e21df2223167c85d2e49b6337a7345c84c1033f1ec10182c7882b36d45",
    "openai-docs/agents/openai.yaml": "44b9efac6be1bae32d869aa2942fecbe4dcae82682ee03e4120f2f9b7d4658ec",
    "openai-docs/assets/openai-small.svg": "45be1f0757eb18889eefb1e7db79668ef46a275dc4e0e78e8df5ebd7f6cdeadc",
    "openai-docs/assets/openai.png": "156cc84d7332bfe95b310350bd470b690d22aa33d65340cc6c2e06022946194c",
    "openai-docs/references/codex-self-knowledge.md": "8c8fb00e6e5cb1977924f5164684a6095427fa828bbc765225f17d9aeb79a912",
    "openai-docs/references/latest-model.md": "bdf241d505eb071b1c7b0b732f842b701348cf6eab95d1c36fd97edac64dd158",
    "openai-docs/references/mcp-diagnostics.md": "49bbd2f73df7bbd7f86c80425dea4da2d301c22046080399a36bfc0ca49509e9",
    "openai-docs/references/model-migration.md": "bef46671036c8e483b7f65df931171217d55a8d26098851c2f89784db8edca2f",
    "openai-docs/references/model-selection.md": "ba2d164abbca30435a460a0bc3a7d82398dce2bdf092705c98ba55b3f3af38a8",
    "openai-docs/references/official-docs.md": "7962f2dce55089b93bde4115bb89fd42f20993c1597a2b13edd4956f463875b9",
    "openai-docs/references/prompting-guide.md": "548d4ca73a34cd4b0041ef05a899592e8c50772b8f3a76c579ec941e403e19f6",
    "openai-docs/references/upgrade-guide.md": "ecac89155f910f064fd306e89c74585cabdb2142aba4f2acc0cead092ae1d1a5",
    "openai-docs/references/upgrading-to-gpt-6-astra.md": "62ef6d22684662a019d203834fe1205a07e4ca4c65dddcbabe1bb51efe1aa840",
    "openai-docs/scripts/fetch-codex-manual.mjs": "f53eb6d2f286e9efcc397e8bee93a938e37296c90953e4e06e94899ef1b6c363",
    "openai-docs/scripts/resolve-latest-model-info": "7354dbb030ca0736dd633a7ca1b930cf640abd40370725dea3a458cb51d49523",
    "openai-docs/scripts/resolve-latest-model-info.cjs": "eeb1bb486018e16b37edfc06b1a37179dbc672982d501040d4f7142f29dd2e64",
    "review-agent/SKILL.md": "07079efd0dc76f05fade424e5dfb048dce1de2df7626e1a4f56292a4f3f92228",
    "review-agent/agents/openai.yaml": "4d867a46d15e36ac880176484aae160f59855340c6059b2ea6ab9fbc9af084de",
    "skill-creator/SKILL.md": "6656e54755638e8efcf275a472b9672eaa8a9a1b9e59dc210e275b03b59e1e66",
    "skill-creator/agents/openai.yaml": "d07d21b93fcf3d4dc8d9a3399c05fc226a49a333a96d3e1c68b451b8dd9eade6",
    "skill-creator/assets/skill-creator-small.svg": "6591bf8ea9bb9435890dbdea299e0d2bd05f3aa893a335d26e4c535e93c8e7fb",
    "skill-creator/assets/skill-creator.png": "a4024b0306ddb05847e1012879d37aaf1e658205199da596f5145ed7a88d9162",
    "skill-creator/license.txt": "cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30",
    "skill-creator/references/openai_yaml.md": "ffac39318e408108141d40f820968e59f70434a891694f9bf1d25be8237b150c",
    "skill-creator/scripts/generate_openai_yaml.py": "816df12072d74faf924d802a6599a139997e1441e90bfe4869ec304f2e5e2851",
    "skill-creator/scripts/init_skill.py": "bf0656a5f9d8d8cdecf0245eaf27e1df8e0e9b6d40ccdda814eb8e3d5f6992c8",
    "skill-creator/scripts/quick_validate.py": "ee6dba90f44d37171c5a6edb8095979c54919ff6822c1a907afca2e78c48738c",
    "skill-installer/LICENSE.txt": "cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30",
    "skill-installer/SKILL.md": "d68b77e5bbb34dedab89d134da52855f140fc4b4299b80104f534e3b9e98f8ee",
    "skill-installer/agents/openai.yaml": "5ce223d8b1070b82c42298538f1b8d376f788eb9e7a42a987e8c094070d73f0e",
    "skill-installer/assets/skill-installer-small.svg": "3928703ff00dc1a681e7a22401843b7edcbd4b2051651ce4c43b75f7e140504e",
    "skill-installer/assets/skill-installer.png": "d0a230b1a79b71b858b7c215a0fbb0768d6459c14ea4ef80c61592629bf0e605",
    "skill-installer/scripts/github_utils.py": "61c1bbe2ae217433b4b6f9f09f21aca4df52c12598068343ade719f706e4859b",
    "skill-installer/scripts/install-skill-from-github.py": "38f311b75664bb063808f982c600271ebc4b560830f491705190f88a94e3e781",
    "skill-installer/scripts/list-skills.py": "9d6dfb2abf3afeee7f027a89fb1626b918a973da18f4eb6c25681286301beb41",
}
_UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
_TEMP6 = r"[A-Za-z0-9]{6}"
_SESSION_DAY = r"sessions/[0-9]{4}/[0-9]{2}/[0-9]{2}"
# The placed set (the note's section 1): what take_config.write and place_lease put in the folder before the grant.
# "lease" is R-H2's facts-only rule.
CONFIG_FOLDER_PLACED = {CODEX: (("config.toml", "file"), ("auth.json", "lease")),
                        GEMINI: ((".gemini", "dir"), (".gemini/settings.json", "file"))}
# Section 2's allow-list: (pattern, kind, what is read and checked or None, source), after turn 1 only. Every pattern
# is a full match over the path relative to the folder. Codex 0.162.1 (paths relative to codex-rs/):
CODEX_ALLOWED = (
    (r"tmp|tmp/arg0", "dir", None, "arg0/src/lib.rs 355-365"),
    (r"tmp/arg0/codex-arg0" + _TEMP6, "dir", None, "arg0/src/lib.rs 373-375 (H3: left by a killed process)"),
    (r"tmp/arg0/codex-arg0" + _TEMP6 + r"/\.lock", "file", None, "arg0/src/lib.rs 25, 378-385 (H3)"),
    (r"tmp/arg0/codex-arg0" + _TEMP6 + r"/(?:apply_patch|applypatch|codex-linux-sandbox|codex-execve-wrapper)",
     "link", "arg0", "arg0/src/lib.rs 21-24, 387-401 (H3: the target is the image's codex executable)"),
    (r"(?:state_5|logs_2|goals_1|memories_1|queue_1|thread_history_1)\.sqlite(?:-wal|-shm)?", "file", None,
     "state/src/sqlite.rs 34-39; state/src/runtime.rs 130-195; thread-store/src/local/mod.rs 291-301"),
    (r"\.sqlite-maintenance\.lock", "file", None, "state/src/runtime/reclamation.rs 17, 28-30, 37-67, 115-129; "
     "state/src/runtime.rs 258 (pf1-codex-lock: the reclamation worker's lock, opened create, never written)"),
    (r"installation_id", "file", "uuid", "core/src/installation_id.rs 17-62 (Uuid::new_v4, written once)"),
    (r"skills|skills/\.system", "dir", None, "skills/src/lib.rs 55-100"),
    (r"skills/\.system/" + re.escape(CODEX_SYSTEM_SKILLS_MARKER), "file", None, "skills/src/lib.rs 58, 97-98"),
    (r"models_cache\.json", "file", None, "models-manager/src/manager.rs 34-35; models-manager/src/cache.rs 241-247"),
    (r"cache|cache/(?:codex_apps_tools|codex_apps_server_info|codex_app_directory|remote_plugin_catalog)", "dir",
     None, "connectors/src/connector_runtime/persistence.rs 30-52; connectors/src/directory_cache.rs 13; "
           "core-plugins/src/remote/catalog_cache.rs 17"),
    (r"cache/(?:codex_apps_tools|codex_apps_server_info)/(?:[0-9a-f]{40}\.json|\.tmp" + _TEMP6 + ")", "file", None,
     "connectors/src/connector_runtime/persistence.rs 46-52, 168-197 (sha1 name; tempfile and rename)"),
    (r"cache/codex_app_directory/[0-9a-f]+\.json", "file", None, "connectors/src/directory_cache.rs 34-35, 83-99"),
    (r"cache/remote_plugin_catalog/(?:[0-9a-f]{16}\.json|\.tmp" + _TEMP6 + ")", "file", None,
     "core-plugins/src/remote/catalog_cache.rs 128-147, 181-182"),
    (r"thread-writer-locks", "dir", None, "rollout/src/writer_lock.rs 17"),
    (r"thread-writer-locks/(?:\.coordination|" + _UUID + r")\.lock", "file", None,
     "rollout/src/writer_lock.rs 18, 51, 96 (a thread's lock is left by a killed turn, H3)"),
    (r"sessions|sessions/[0-9]{4}|sessions/[0-9]{4}/[0-9]{2}|" + _SESSION_DAY, "dir", None,
     "rollout/src/recorder.rs 984-1000"),
    (_SESSION_DAY + r"/rollout-[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}-[0-9]{2}-[0-9]{2}-" + _UUID + r"(?:_" + _UUID
     + r")?\.jsonl", "file", None, "rollout/src/rollout_file_name.rs 62-73"),
    (r"shell_snapshots", "dir", None, "core/src/shell_snapshot.rs 259-283"),
    (r"shell_snapshots/" + _UUID + r"\.(?:tmp-[0-9]+|[0-9]+\.sh)", "file", None,
     "core/src/shell_snapshot.rs 263-272 (the .tmp- form is left by a killed turn, H3)"),
    (r"\.tmp" + _TEMP6, "file", None, "core/src/config/edit.rs 731-770 (config.toml's sibling, left by a killed "
                                      "write, H3)"),
    (r"\.sandbox_migration", "file", "sandbox_marker",
     "execpolicy/src/sandbox_migration.rs 10, 21-27, 32-47; core/src/session/mod.rs 649-664 (B20: the one-shot "
     "marker, written once at the first session start: b'v1\\n', mode 0600, tempfile 3.27.0's persist_noclobber)"),
)
# B20 (glitch-26's B20-1, lane vendor-b20, on lane-reports/B20-DESIGN.md): the marker's exact bytes and mode.
SANDBOX_MARKER = b"v1\n"
SANDBOX_MARKER_MODE = 0o600
# Gemini CLI 0.64.0 (bundle files as in CONFIG_FOLDER_SOURCES; [C] chunk-NR7L3FXV.js, [M] gemini-Q2GRYIAK.js).
# {slug} is the run tree's basename lowercased, every other character than [a-z0-9] as "-" ([C] 253035-253040; a fresh
# folder has no collision, so no "-N").
GEMINI_ALLOWED = (
    (r"\.gemini/projects\.json", "file", "projects", "[C] 252893-252912, 252960-252980"),
    (r"\.gemini/projects\.json\.lock", "dir", None, "[C] 252955-252958 (proper-lockfile's folder; H4: left by a kill)"),
    (r"\.gemini/projects\.json\." + _UUID + r"\.tmp", "file", None, "[C] 252899 (H4: left by a killed save)"),
    (r"\.gemini/(?:tmp|history)|\.gemini/(?:tmp|history)/{slug}", "dir", None, "[C] 253079-253112, 253351-253377"),
    (r"\.gemini/(?:tmp|history)/{slug}/\.project_root", "file", "project_root", "[C] 253079-253112, 253351-253355"),
    (r"\.gemini/tmp/{slug}/logs", "dir", None, "[C] 334255-334260, 381051 (empty)"),
    (r"\.gemini/tmp/{slug}/chats", "dir", None, "[C] 286703-286745"),
    (r"\.gemini/tmp/{slug}/chats/session-[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}-[0-9]{2}-[0-9a-f]{8}(?:-[0-9]+)?"
     r"(?:\.jsonl|\.jsonl\.tmp-[0-9]+|\.jsonl\.unreadable-[0-9]+|\.json)", "file", None,
     "[C] 286662-286745, 286808-286872, 286895-286910 (a partial .jsonl is H4's)"),
    (r"\.gemini/tmp/{slug}/chats/" + _UUID, "dir", None, "[C] 286709-286725 (a subagent's folder)"),
    (r"\.gemini/tmp/{slug}/chats/" + _UUID + r"/[A-Za-z0-9_-]+\.jsonl", "file", None, "[C] 286709-286725"),
    (r"\.gemini/tmp/{slug}/tool-outputs|\.gemini/tmp/{slug}/tool-outputs/session-" + _UUID, "dir", None,
     "[C] 254186-254200, 344729-344736"),
    (r"\.gemini/tmp/{slug}/tool-outputs/(?:session-" + _UUID + r"/)?[A-Za-z0-9_-]+_[A-Za-z0-9_-]+\.txt", "file", None,
     "[C] 254186-254200, 344729-344736"),
    (r"\.gemini/tmp/background-processes", "dir", None, "[M] 17012-17040"),
    (r"\.gemini/tmp/background-processes/background-[0-9]+\.log", "file", None, "[M] 17012-17040; [C] 324254-324270"),
    (r"\.gemini/tmp/{slug}/" + _UUID + r"|\.gemini/tmp/{slug}/" + _UUID + r"/plans", "dir", None,
     "[C] 355376-355381"),
)
# Paths refused by name, each with its reason, before the allow-list is read (the note's section 4 and R4 to R6).
# Anything else neither placed nor allow-listed refuses too, as "not on the allow-list".
CONFIG_FOLDER_NAMED = {
    CODEX: (
        (r"plugins(?:/.*)?", "R4: plugins/** (remote-installed plugins carry MCP and hook config; "
                             "core-plugins/src/manager.rs 1596-1616, loader.rs 70-72)"),
        (r"cloud-config-bundle-cache\.json", "R5: a managed-config bundle Codex reads back (cloud-config/src/cache.rs "
                                             "28, 160-190); the codex2 plan is not ruled eligible"),
        (r"db-backups(?:/.*)?", "R6: the state database's corruption recovery (state/src/runtime/recovery.rs 16, "
                                "181-196): recorded for a human"),
        (r"\.env", "the dotenv Codex loads before threads start (arg0/src/lib.rs 299-327)"),
        (r"AGENTS(?:\.override)?\.md", "global instructions (codex-home/src/instructions/mod.rs 12-13, 43-57)"),
        (r"rules(?:/.*)?", "exec policy (core/src/exec_policy.rs 54-56, 679)"),
        (r"agents(?:/.*)?", "agent roles (agent-roles/src/loader.rs 75-80)"),
        (r"skills/(?!\.system(?:/|$)).*", "a user skill root (ext/skills/src/host_roots.rs 94-118)"),
        (r"\.agents(?:/.*)?", "a user skill root or a personal marketplace (host_roots.rs 105; "
                              "core-plugins/src/marketplace.rs 20-25)"),
        (r"hooks\.json", "hook config (hooks/src/engine/discovery.rs 339-343)"),
        (r"environments\.toml", "exec-server/src/environment_toml.rs 26, 237"),
        (r"[^/]*\.config\.toml|requirements\.toml|managed_config\.toml", "a profile or managed config layer"),
        (r"\.(?:bashrc|bash_profile|bash_login|profile|zshrc|zprofile|zshenv|zlogin)",
         "a shell start file (core/src/shell_snapshot.rs 586-605)"),
    ),
    GEMINI: (
        (r"settings\.json", "the launcher reads the root settings.json ([L] 25-30)"),
        (r"\.env|\.gemini/\.env", "the dotenv fallback ([S] 16542-16572, 16602-16650)"),
        (r"\.gemini/GEMINI\.md", "global memory, model-writable ([C] 363483-363497, 382330-382356)"),
        (r"\.gemini/tmp/[^/]+/memory(?:/.*)?", "project memory, model-writable ([C] 363498-363520)"),
        (r"\.gemini/(?:extensions|agents|skills|policies|commands|acknowledgments)(?:/.*)?",
         "extensions, agents, skills, policies or commands Gemini CLI loads ([U] 65778-65790; [C] 342579, 253238, "
         "367775; [U] 74994)"),
        (r"\.agents(?:/.*)?", "a user skill root ([C] 253238-253255)"),
        (r"\.gemini/(?:trustedFolders|mcp-server-enablement|keybindings|trusted_hooks|policy_integrity)\.json",
         "configuration Gemini CLI reads every run ([M] 17474; [C] 360716-360750)"),
    ),
}
CONFIG_FOLDER_ALLOWED = {CODEX: CODEX_ALLOWED, GEMINI: GEMINI_ALLOWED}


@dataclass(frozen=True, eq=False)
class ConfigFolder:
    """One take's B11 record, built once per take by ownership.config_folder (drive: TakeDriver.config_folder) and
    handed to every arm O and G turn. `placed` is take_config.files_for's {relative path: bytes}; `lease` is
    lease_for_take's record (codex) or None (gemini); `uid_map` the take's runtime uid map; `census()` is one
    ownership.operator_census of the folder, `read(rel)` and `read_sha256(rel)` one ownership.operator_read each (the
    bytes, or their sha256; None when absent)."""
    harness: str
    run_tree: str
    config_dir: str
    placed: dict
    lease: object
    uid_map: tuple
    census: Callable
    read: Callable
    read_sha256: Callable


class ConfigFolderRefused(Refused):
    """B11: the config folder or the agent's HOME is not what turn `turn` may start with. `problems` names each path
    and the rule; routed like settings_guard.snapshot_problems (R4-1: before turn 1 a rehearsal; after it a stop for a
    ruling, DriveRefused, recorded failed with drive_started true)."""

    def __init__(self, problems, turn):
        super().__init__(f"the config folder before turn {turn}: " + "; ".join(problems))
        self.problems, self.turn = list(problems), turn


_SLUG_OTHER = re.compile(r"[^a-z0-9]")


def gemini_slug(run_tree: str) -> str:
    """Gemini CLI's project short id for a fresh folder: the basename lowercased, each non-[a-z0-9] character "-"."""
    return _SLUG_OTHER.sub("-", os.path.basename(run_tree).lower())


def agent_home_problems(run_tree: str, uid_map) -> list:
    """R-OA: <run tree>/.home is a folder (never a link) of mode 700, owned by the agent's mapped host uid. Host lstat
    only: the folder itself, never what is in it."""
    tree = _abs_path(run_tree, "run_tree")
    home = os.path.join(tree, RUN_TREE_HOMEDIR)
    try:
        st = os.lstat(home)
    except OSError:
        return [f"{home}: the agent's HOME is missing"]
    if stat.S_ISLNK(st.st_mode) or not os.path.isdir(home):
        return [f"{home}: the agent's HOME is not a folder (a link or a file)"]
    out = []
    if stat.S_IMODE(st.st_mode) != 0o700:
        out.append(f"{home}: the agent's HOME is mode {stat.S_IMODE(st.st_mode):o}, not 700")
    try:
        agent = host_uid(_uid_of(AGENT_USER), uid_map)
    except Refused as e:
        return out + [f"{home}: the take's uid map does not map the agent ({e})"]
    if st.st_uid != agent:
        out.append(f"{home}: the agent's HOME is not owned by the agent's mapped host uid {agent}")
    return out


def _lease_problems(e: dict, lease) -> list:
    """R-H2: auth.json by its census facts only, never its bytes."""
    out, rel = [], e["path"]
    if not isinstance(lease, LeasePlacement):
        return [f"{rel}: no placement record to compare the lease with"]
    if not stat.S_ISREG(e["mode"]):
        out.append(f"{rel}: the lease is not a regular file")
    if e["nlink"] != 1:
        out.append(f"{rel}: the lease has {e['nlink']} links, not one")
    if stat.S_IMODE(e["mode"]) != 0o600:
        out.append(f"{rel}: the lease's mode is {stat.S_IMODE(e['mode']):o}, not 600")
    if e["uid"] != _uid_of(AGENT_USER):
        out.append(f"{rel}: the lease is not owned by the agent")
    if (e["dev"], e["ino"]) != (lease.dev, lease.ino):
        out.append(f"{rel}: the lease is not the file place_lease placed (another device or inode)")
    if not 0 < e["size"] <= LEASE_MAX_BYTES:
        out.append(f"{rel}: the lease's size is not 1 to {LEASE_MAX_BYTES} bytes")
    return out


def _allowed(harness: str, rel: str, run_tree: str):
    """(kind, read rule, source) of the allow-list pattern `rel` matches, or None."""
    if harness == CODEX and rel.startswith("skills/.system/"):
        key = rel[len("skills/.system/"):]
        if key == CODEX_SYSTEM_SKILLS_MARKER:
            return "file", None, "skills/src/lib.rs 58, 97-98"
        if key in CODEX_SYSTEM_SKILLS:
            return "file", "skill", "skills/src/lib.rs 55, 146-173 (the embedded set)"
        if any(f.startswith(key + "/") for f in CODEX_SYSTEM_SKILLS):
            return "dir", None, "skills/src/lib.rs 146-173 (the embedded set)"
        return None
    slug = re.escape(gemini_slug(run_tree))
    for pattern, kind, rule, source in CONFIG_FOLDER_ALLOWED[harness]:
        if re.fullmatch(pattern.replace("{slug}", slug), rel):
            return kind, rule, source
    return None


def config_folder_problems(folder, entries, *, turn: int) -> tuple:
    """(problems, reads) of a census against the placed set and, after turn 1, the allow-list; reads are the
    (path, rule) pairs check_config_folder then reads. A pure function of the census."""
    h = folder.harness
    by = {e["path"]: e for e in entries}
    root = by.get(".")
    if root is None or root["kind"] != "dir":
        return ["the census holds no folder at its root"], []
    problems, reads = [], []
    for e in entries:
        if e["dev"] != root["dev"]:
            problems.append(f"{e['path']}: on another device than the folder")
    placed = dict(CONFIG_FOLDER_PLACED[h])
    for rel, kind in placed.items():
        e = by.get(rel)
        if e is None:
            problems.append(f"{rel}: placed, and missing")
        elif kind == "lease":
            problems += _lease_problems(e, folder.lease)
        elif e["kind"] != kind:
            problems.append(f"{rel}: placed as a {kind}, now a {e['kind']}")
        elif kind == "file":
            if e["nlink"] != 1:
                problems.append(f"{rel}: placed with one link, now {e['nlink']}")
            reads.append((rel, "placed"))
    for e in entries:
        rel, kind = e["path"], e["kind"]
        if rel == "." or rel in placed:
            continue
        if turn == 1:
            problems.append(f"{rel}: not placed (before turn 1 the folder holds exactly the placed set)")
            continue
        if kind == "other":
            problems.append(f"{rel}: a special file, a name that is not UTF-8, or a credential-shaped name other "
                            f"than the placed lease")
            continue
        named = [why for pattern, why in CONFIG_FOLDER_NAMED[h] if re.fullmatch(pattern, rel)]
        if named:
            problems.append(f"{rel}: refused, {named[0]}")
            continue
        got = _allowed(h, rel, folder.run_tree)
        if got is None:
            problems.append(f"{rel}: neither placed nor on {h}'s allow-list")
            continue
        want, rule, _source = got
        if kind != want:
            problems.append(f"{rel}: a {kind} where the allow-list admits only a {want}")
            continue
        if kind == "link":
            if not codex_arg0_link(rel, e["target"]):
                problems.append(f"{rel}: a link whose target is not the image's codex executable")
            continue
        if kind == "file" and e["nlink"] != 1:
            problems.append(f"{rel}: a file with {e['nlink']} links")
            continue
        if rule == "sandbox_marker" and stat.S_IMODE(e["mode"]) != SANDBOX_MARKER_MODE:
            problems.append(f"{rel}: Codex's sandbox-migration marker at mode {stat.S_IMODE(e['mode']):o}, not "
                            f"{SANDBOX_MARKER_MODE:o}")
            continue
        if rule is not None:
            reads.append((rel, rule))
    return problems, reads


def _read_problem(folder, rel: str, rule: str):
    """The one problem a section-6-point-2 read finds, or None."""
    if rule == "skill":
        want = CODEX_SYSTEM_SKILLS[rel[len("skills/.system/"):]]
        if want is None:
            return f"{rel}: its pinned digest is held (CODEX_SYSTEM_SKILLS_HELD), so it is never admitted unread"
        got = folder.read_sha256(rel)
        return None if got == want else f"{rel}: not the pinned embedded skill (an edited system skill)"
    data = folder.read(rel)
    if data is None:
        return f"{rel}: listed by the census, absent at its read"
    if rule == "placed":
        return None if data == folder.placed[rel] else f"{rel}: not byte-identical to take_config.files_for"
    if rule == "sandbox_marker":
        return None if data == SANDBOX_MARKER else f"{rel}: not Codex's sandbox-migration marker (exactly b'v1\\n')"
    if rule == "uuid":
        return None if re.fullmatch(_UUID, data.decode("ascii", "replace")) else f"{rel}: not one UUID"
    if rule == "project_root":
        return None if data == folder.run_tree.encode("utf-8") else f"{rel}: does not name the run tree alone"
    if rule == "projects":
        try:
            doc = json.loads(data)
        except ValueError:
            doc = None
        want = {"projects": {folder.run_tree: gemini_slug(folder.run_tree)}}
        return None if doc == want else f"{rel}: not exactly the run tree's one mapping"
    return f"{rel}: no read rule {rule!r}"


def check_config_folder(folder, *, harness: str, run_tree: str, turn: int) -> None:
    """B11 before every arm O and G turn (run_turn, immediately before exec_argv): R-OA's HOME, then one census of the
    config folder against the placed set and (after turn 1) the allow-list, then the reads section 6 point 2 lists.
    Any problem raises ConfigFolderRefused, naming each; nothing of the turn runs."""
    if harness not in CONFIG_FOLDER_HARNESSES:
        raise Refused(f"the config folder check is arm O's and arm G's; {harness!r} keeps its own guard")
    if not (isinstance(turn, int) and not isinstance(turn, bool) and turn >= 1):
        raise Refused("a turn is numbered from 1")
    if not isinstance(folder, ConfigFolder):
        raise ConfigFolderRefused([f"a {harness} turn carries no config folder record (ownership.config_folder)"],
                                  turn)
    tree = _abs_path(run_tree, "run_tree")
    if folder.harness != harness or folder.run_tree != tree:
        raise ConfigFolderRefused(["the config folder record is another harness's or another run tree's"], turn)
    if harness == CODEX and (not isinstance(folder.lease, LeasePlacement)
                             or folder.lease.path != os.path.join(folder.config_dir, LEASE_FILE)
                             or tuple(folder.lease.uid_map) != tuple(folder.uid_map)):
        raise ConfigFolderRefused(["the lease record is not this config folder's, bound to the record's uid map"],
                                  turn)
    problems = agent_home_problems(tree, folder.uid_map)
    if problems:
        raise ConfigFolderRefused(problems, turn)
    try:
        entries = folder.census()
    except Exception as e:  # noqa: BLE001 - OwnershipError (a cap, a refusal, a reply off its shape) or any other
        raise ConfigFolderRefused([f"the census refused: {type(e).__name__}: {str(e)[:300]}"], turn) from None
    problems, reads = config_folder_problems(folder, entries, turn=turn)
    if not problems:
        for rel, rule in reads:
            try:
                why = _read_problem(folder, rel, rule)
            except Exception as e:  # noqa: BLE001 - a read that fails is a problem, never a pass
                why = f"{rel}: the read refused ({type(e).__name__}: {str(e)[:200]})"
            if why is not None:
                problems.append(why)
    if problems:
        raise ConfigFolderRefused(problems, turn)


# ------------------------------------------------------------------------------------------------- one turn
def run_turn(runtime, take_id: str, inner, *, harness: str, run_tree: str, login_file: str, stream_path: str,
             budget_s: float, clock, caller_env=None, config_folder=None, turn=None) -> dict:
    """One exec per turn in the kept-alive container; stdout written to the host-side stream path; times from the
    injected clock. A timeout is recorded as a timed-out exec: the caller then kills the agent's processes inside
    (killing the client alone leaves them running). The launch journal records the submitted exec request,
    not proof that Docker started it; started_at is submission time. The returned exit/timeout record and retained
    stream must be bound to it before the checker claims an executed interaction.

    B11 (lane vendor-b11 round 3, R-CF): an arm O or G turn carries its take's ConfigFolder record and its number
    (`config_folder`, `turn`), and check_config_folder runs immediately before exec_argv; a refusal runs nothing and
    writes no journal or stream. Arm A's turn never calls it (settings_guard is its guard)."""
    stream_path = _abs_path(stream_path, "stream_path")
    if _inside(stream_path, _abs_path(run_tree, "run_tree")):
        raise Refused("the host-side stream never sits inside the run tree")
    if os.path.lexists(stream_path):
        raise Refused("the stream path already exists: a stream is never overwritten")
    launch_path = stream_path + ".launch.json"
    if os.path.lexists(launch_path):
        raise Refused("the launch journal already exists: an attempted turn is never overwritten")
    if not (isinstance(budget_s, (int, float)) and budget_s > 0):
        raise Refused("budget_s > 0")
    refuse_env_files(workdir=run_tree, run_tree=run_tree)
    inner = _check_argv(inner)
    if harness in CONFIG_FOLDER_HARNESSES:
        check_config_folder(config_folder, harness=harness, run_tree=run_tree, turn=turn)
    argv, env = exec_argv(take_id, inner, user=AGENT_USER, workdir=run_tree, harness=harness, run_tree=run_tree,
                          login_file=login_file, caller_env=caller_env)
    started = clock()
    launch = {"schema": 1, "harness": harness, "container_id": take_id, "argv": inner,
              "cwd": run_tree, "stream": stream_path, "started_at": started}
    fd = os.open(launch_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(launch, fh, separators=(",", ":"))
        fh.write("\n")
        fh.flush()
        os.fsync(fh.fileno())
    timed_out, code, out, err = False, None, "", ""
    try:
        c = runtime.run(argv, env=env, timeout=budget_s)
        code, out, err = c.returncode, c.stdout, c.stderr
    except TimeoutError as e:
        timed_out, out = True, getattr(e, "stdout", "") or ""
    ended = clock()
    del env
    fd = os.open(stream_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8", errors="surrogateescape") as fh:
        fh.write(out)
    return {"exit_code": code, "timed_out": timed_out, "started_at": started, "ended_at": ended,
            "stream_path": stream_path, "stderr": err, "launch_path": launch_path}


# ------------------------------------------------------------------------------------------------ the session sweep
# W-3b (glitch-b5's rulings on reviews r14 and r15, 16 Oct 2026): after every turn, inside the take container (its
# agent's processes gone, before the teardown), the swept locations are read for files of an agent session's shape:
# a Codex rollout's session_meta, a record with a sessionId string and a type string (Claude Code's; any type), a
# Gemini chat's sessionId and projectHash, on ANY line of a file up to SWEEP_FILE_CAP (a larger file that opens with
# "{" is reported, fail closed). It runs as the agent's own uid through the image's isolated Python (/usr/bin/python3
# -I -S, root-owned, as kill_agent does). A link is never followed: an agent-owned link whose target leaves the swept
# roots is reported. /proc and /sys are never roots and never entered. A file that does not open with "{" is read no
# further than its first block. An agent-owned entry the sweep cannot read, and an entry that cannot be lstat'ed
# under an agent-owned folder, are reported. The checker admits only the take's own session and its sub-agent pairs.
# Its roots are the read-write mounts of the container's own mount table (review r15's MAJOR 2: a nested session
# in /run/lock, mode 1777, was outside every listed root); with the root filesystem read-only, those are every location
# a take can write, and the checker refuses a read-write mount outside sweep_roots().
AGENT_PASSWD_HOME = "/home/dana"          # the image's agent user (box/Dockerfile useradd --home-dir): read-only now
# glitch-b5's ruling on review r15's MAJOR 2 (16 Oct 2026): the take container's root filesystem is read-only, and the
# sweep's roots are every read-write mount of the container's own mount table at sweep time (/proc, /sys and /dev never,
# /dev/shm kept). The listed set below is only what those mounts are compared against: a read-write mount outside it
# refuses [nested-agent].
SWEEP_FIXED_ROOTS = ("/tmp", "/var/tmp", "/dev/shm")
SWEEP_NEVER_ROOTS = ("/proc", "/sys", "/dev")  # never a root, never entered ...
SWEEP_KEPT_ROOTS = ("/dev/shm",)               # ... but for these
SWEEP_MOUNTINFO = "/proc/self/mountinfo"
# Docker bind-mounts these three runtime files into every container; under ReadonlyRootfs it mounts them read-only
# (moby, review r16), so they are not among the read-write mounts. They stay in the expected set so a runtime that mounts
# them read-write (root-owned files the agent cannot write) still compares clean; the sweep reads them either way.
DOCKER_RUNTIME_FILES = ("/etc/hosts", "/etc/hostname", "/etc/resolv.conf")
SWEEP_MAX_FILES = 200000
SWEEP_FILE_CAP = 64 * 1024 * 1024           # review r15: every line of a file up to 64 MB; a larger "{" file fails closed
SWEEP_PROGRAM = r'''
import json, os, stat, sys
mountinfo, uid, cap, fcap = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
never, kept = json.loads(sys.argv[5]), json.loads(sys.argv[6])
out = {"files": [], "unreadable": [], "escapes": [], "mounts": [], "scanned": 0, "truncated": False}
def inside(p, tops):
    return any(p == t or p.startswith(t.rstrip("/") + "/") for t in tops)
def barred(p):
    return inside(p, never) and not inside(p, kept)
def unescape(field):
    return field.encode("latin-1").decode("unicode_escape") if "\\" in field else field
with open(mountinfo, encoding="utf-8", errors="surrogateescape") as fh:
    for line in fh:
        f = line.split(" ")
        if len(f) > 5 and "rw" in f[5].split(","):
            point = unescape(f[4])
            if not barred(point):
                out["mounts"].append(point)
out["mounts"] = sorted(set(out["mounts"]))
roots = out["mounts"]
real_roots = [os.path.realpath(r) for r in roots]     # a link's target compared by realpath too
real_never, real_kept = [os.path.realpath(n) for n in never], [os.path.realpath(k) for k in kept]
walk = []                          # review r16 NIT: each tree walked once (a root inside another, by realpath, is not)
given = sorted({os.path.realpath(r) if os.path.islink(r) else r for r in roots},   # review r17 NIT 2: a root that is
               key=lambda q: len(os.path.realpath(q)))                              # a link is walked at its realpath
for r in given:
    if not inside(os.path.realpath(r), [os.path.realpath(w) for w in walk]):
        walk.append(r)
def classify(line):
    try:
        r = json.loads(line)
    except ValueError:
        return None
    if not isinstance(r, dict):
        return None
    if r.get("type") == "session_meta":
        q = r.get("payload") if isinstance(r.get("payload"), dict) else {}
        return ["codex", q.get("id") if isinstance(q.get("id"), str) else None]
    if isinstance(r.get("sessionId"), str) and isinstance(r.get("type"), str):
        return ["claude", r["sessionId"]]
    if isinstance(r.get("sessionId"), str) and isinstance(r.get("projectHash"), str):
        return ["gemini", r["sessionId"]]
    return None
def shape(path, fd):
    first = os.read(fd, 4096)
    if first.lstrip()[:1] != b"{":
        return None
    chunks, size = [first], len(first)
    while size <= fcap:
        b = os.read(fd, 1048576)
        if not b:
            break
        chunks.append(b)
        size += len(b)
    if size > fcap:
        return "over-cap"
    for line in b"".join(chunks).split(b"\n"):
        if line.strip():
            got = classify(line)
            if got:
                return got
    return None
def visit(path, parent_uid):
    if barred(path):
        return
    try:
        st = os.lstat(path)
    except OSError:
        if parent_uid == uid:
            out["unreadable"].append([path, "lstat"])
        return
    if stat.S_ISLNK(st.st_mode):
        # reviews r16 and r17: with the root read-only, a link to a read-only location hides nothing (a venv's links into
        # /usr, a genomics link to /mnt/refs/hg38.fa); an agent-owned link is reported only into a barred tree (/proc,
        # /sys, /dev but /dev/shm), caught by realpath even when its target is missing. Every writable location is a
        # read-write mount, so a swept root or a barred one.
        if st.st_uid == uid:
            target = os.path.realpath(path)
            if barred(target) or (inside(target, real_never) and not inside(target, real_kept)):
                out["escapes"].append([path, target])
        return
    if stat.S_ISDIR(st.st_mode):
        try:
            names = sorted(os.listdir(path))
        except OSError:
            if st.st_uid == uid:
                out["unreadable"].append([path, "dir"])
            return
        for n in names:
            if out["truncated"]:
                return
            visit(os.path.join(path, n), st.st_uid)
        return
    if not stat.S_ISREG(st.st_mode):
        return
    out["scanned"] += 1
    if out["scanned"] > cap:
        out["truncated"] = True
        return
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError:
        if st.st_uid == uid:
            out["unreadable"].append([path, "file"])
        return
    try:
        got = shape(path, fd)
    except OSError:
        got = None
        if st.st_uid == uid:
            out["unreadable"].append([path, "file"])
    finally:
        os.close(fd)
    if got == "over-cap":
        out["unreadable"].append([path, "over-cap"])
    elif got:
        out["files"].append([path] + got)
for root in walk:
    visit(root, None)
print(json.dumps(out, sort_keys=True))
'''


def sweep_roots(run_tree: str) -> list:
    """The read-write mounts the take container is expected to have (its two binds, its tmpfs mounts, /dev/shm and
    Docker's runtime files): what the sweep's mount table is compared against, never what it reads."""
    return [run_tree, CONFIG_MOUNT, *SWEEP_FIXED_ROOTS, *DOCKER_RUNTIME_FILES]


def sweep_argv(take_id: str) -> list:
    return [RUNTIME_CLIENT, "exec", "--user", AGENT_USER, _check_id(take_id, "take id"), "/usr/bin/python3", "-I",
            "-S", "-c", SWEEP_PROGRAM, SWEEP_MOUNTINFO, AGENT_USER.split(":", 1)[0], str(SWEEP_MAX_FILES),
            str(SWEEP_FILE_CAP), json.dumps(list(SWEEP_NEVER_ROOTS)), json.dumps(list(SWEEP_KEPT_ROOTS))]


def sweep_sessions(runtime, take_id: str, *, caller_env=None) -> dict:
    """One sweep of the take container (above): {files: [[path, shape, session id]], unreadable: [[path, kind]],
    escapes: [[link, target]], mounts: [the read-write mount points it read], scanned, truncated}. A failed exec or a
    reply off that shape raises Refused."""
    got = runtime.run(sweep_argv(take_id), env=runtime_env(caller_env), timeout=STEP_TIMEOUT_S)
    if got.returncode != 0:
        raise Refused(f"the session sweep exited {got.returncode}: {str(got.stderr)[:200]}")
    try:
        doc = json.loads(got.stdout)
    except (TypeError, ValueError):
        raise Refused("the session sweep's reply is not JSON") from None
    if not (isinstance(doc, dict) and set(doc) == {"files", "unreadable", "escapes", "mounts", "scanned", "truncated"}
            and isinstance(doc["mounts"], list) and all(isinstance(m, str) for m in doc["mounts"])
            and isinstance(doc["files"], list) and isinstance(doc["unreadable"], list)
            and isinstance(doc["escapes"], list)
            and all(isinstance(u, list) and len(u) == 2 and all(isinstance(x, str) for x in u) for u in doc["escapes"])
            and type(doc["scanned"]) is int and type(doc["truncated"]) is bool
            and all(isinstance(f, list) and len(f) == 3 and isinstance(f[0], str) and isinstance(f[1], str)
                    for f in doc["files"])
            and all(isinstance(u, list) and len(u) == 2 and all(isinstance(x, str) for x in u)
                    for u in doc["unreadable"])):
        raise Refused("the session sweep's reply is off its shape")
    return doc
