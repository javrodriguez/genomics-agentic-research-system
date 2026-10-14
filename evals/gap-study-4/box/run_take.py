#!/usr/bin/env python3
"""The host side of one take's containers (CP2): the runtime protocol, the take container, the per-harness exec,
the login read, the launch and teardown orders, leaked containers, the agent's leftover processes, the cgroup
counters, the exit record and one turn's exec.

Code only, driven by fakes in wave 4: no image is built and no container is created or run by any test. Every
runtime action here is an argv list handed to a runtime object (`Completed`, `DockerRuntime`, the runtime protocol of
interface 10). `DockerRuntime.run` is the only place in the box that starts a process, with a list argv and
`shell=False`, and it passes the caller's `env` as the client's WHOLE environment.

THE TAKE CONTAINER. One fresh container per take, kept alive by `sleep infinity` as PID 1 under a third uid
(`KEEPALIVE_USER`), with exactly two mounts: the run tree read-write at the same absolute path as on the host, and
the per-take config folder at `CONFIG_MOUNT`. All capabilities dropped, no new privileges, a pids limit, a memory
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
# The runtime's default network, which the proxy alone joins for its own way out.
DEFAULT_NETWORK = "bridge"

# Harness names (interface 11): Claude Code's imported, never typed; the other two typed once each, here.
CLAUDE_CODE = harness_bookkeeping.CLAUDE_CODE
CODEX = "codex"
GEMINI = "gemini"

# The C3 routing names (interface 11, fixed by lane w4h). wait_gone returns the survivors the drive step counts
# into this box key; a non-zero count routes by the row below (phase after-first-turn, harness-error).
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

# ------------------------------------------------------------------- THE TAKE ENVIRONMENT (ruling docs-1, w12a)
# An ALLOWLIST, never a blocklist. Every agent process starts from an EMPTY environment (the turn's launcher, below,
# execs the harness with exactly this row and nothing else: not the image's ENV, not docker exec's defaults, not the
# caller's). Each arm's row is the whole of what may reach the agent: PATH, HOME, LANG, the run tree's temporary
# folder, the proxy, the harness's own switches and config home, and the arm's ONE credential, by NAME only (its value
# is read from the login file at exec time and never rides in any argv). A name not in its row never reaches the agent.
# HOME is the per-take config mount, so a `.env` there can be read host-side before launch (refuse_env_files).
TAKE_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
TAKE_LANG = "C.UTF-8"
RUN_TREE_TMP = "<run tree>/.tmp"            # a marker: filled with f"{run_tree}/{RUN_TREE_TMPDIR}" per take
CREDENTIAL = "<credential, by name only>"   # a marker: the arm's one login variable
TAKE_ENV = {
    CLAUDE_CODE: {"PATH": TAKE_PATH, "HOME": CONFIG_MOUNT, "LANG": TAKE_LANG,
                  "TMPDIR": RUN_TREE_TMP, "TMP": RUN_TREE_TMP, "TEMP": RUN_TREE_TMP, "HTTPS_PROXY": PROXY_URL,
                  "DISABLE_AUTOUPDATER": "1", "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1", **ISOLATION_ENV,
                  "CLAUDE_CONFIG_DIR": CONFIG_MOUNT, "CLAUDE_CODE_OAUTH_TOKEN": CREDENTIAL},
    CODEX: {"PATH": TAKE_PATH, "HOME": CONFIG_MOUNT, "LANG": TAKE_LANG,
            "TMPDIR": RUN_TREE_TMP, "TMP": RUN_TREE_TMP, "TEMP": RUN_TREE_TMP, "HTTPS_PROXY": PROXY_URL,
            "CODEX_HOME": CONFIG_MOUNT, "CODEX_API_KEY": CREDENTIAL},
    GEMINI: {"PATH": TAKE_PATH, "HOME": CONFIG_MOUNT, "LANG": TAKE_LANG,
             "TMPDIR": RUN_TREE_TMP, "TMP": RUN_TREE_TMP, "TEMP": RUN_TREE_TMP, "HTTPS_PROXY": PROXY_URL,
             "GEMINI_CLI_HOME": CONFIG_MOUNT, "GEMINI_API_KEY": CREDENTIAL},
}
# The base every row carries (bound by the tests); the views below are DERIVED from TAKE_ENV, never declared apart.
BASE_NAMES = ("PATH", "HOME", "LANG")
LOGIN_VARIABLE = {h: next(k for k, v in row.items() if v == CREDENTIAL) for h, row in TAKE_ENV.items()}
# Owner amendment, 13 Oct 2026: Codex must use an isolated ChatGPT subscription.
# The historical API row above is not an admissible route. All execution and
# builder login entry points refuse until the reviewed subscription lease exists.
CODEX_SUBSCRIPTION_NOT_READY = "Codex subscription binding not ready; API-key login is not permitted"
# Each harness's own non-secret values (its switches, proxy and config home): the row less the base, the run tree's
# temporary folder and the credential. config_home_names() and preflight read this view.
HARNESS_ENV = {h: {k: v for k, v in row.items() if k not in BASE_NAMES and v not in (RUN_TREE_TMP, CREDENTIAL)}
               for h, row in TAKE_ENV.items()}
# The turn's launcher inside the take container: the image's own python3, isolated (-I -S), reads the credential by
# its name from the exec's environment and execs the harness with exactly the row (os.execvpe: PATH from the row).
# Before each harness exec it checks .env names in the actual container cwd, ALL its ancestors and HOME.
# The host-side check below is an early refusal only: a mounted run tree is not the container filesystem root.
# Its arguments: the credential's name, the count of NAME=VALUE pairs, the pairs, then the harness's argv.
LAUNCHER_SOURCE = ("import os,sys\n"
                   "a=sys.argv[1:]\n"
                   "k,n=a[0],int(a[1])\n"
                   "e=dict(x.split('=',1) for x in a[2:2+n])\n"
                   "e[k]=os.environ[k]\n"
                   "dirs=[e['HOME']]\n"
                   "d=os.getcwd()\n"
                   "while True:\n"
                   " dirs.append(d)\n"
                   " parent=os.path.dirname(d)\n"
                   " if parent==d: break\n"
                   " d=parent\n"
                   "for d in dirs:\n"
                   " for name in ('.env',os.path.join('.gemini','.env')):\n"
                   "  p=os.path.join(d,name)\n"
                   "  if os.path.lexists(p): raise SystemExit('refusing .env file: '+p)\n"
                   "c=a[2+n:]\n"
                   "os.execvpe(c[0],c,e)\n")
LAUNCHER = ("/usr/bin/python3", "-I", "-S", "-c", LAUNCHER_SOURCE)

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
FALLBACK_ENV = PENDING
# Arms O and G's own billing-route variables (a Vertex switch for Gemini CLI, for example): a tuple of names each,
# named from the harness's documentation at the pinned version. Until then the refused set is the closed list above,
# and an exec of either harness is refused (NotReady): this lane's stricter reading.
VENDOR_BILLING_ROUTE_VARIABLES = {CODEX: PENDING, GEMINI: PENDING}

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
    "TakeSpec.resources": "the take's memory reservation, CPU and pids values: capacity POLICY, not measurements "
                          "(the caller's spec_for passes them; the stub-take derivation's rule R-RES from athena's "
                          "capacity and three concurrent takes; the stub take only showed that they apply and the "
                          "box's floor, all recorded).",
}
# Pending values this module does not hold: the caller passes them once measured.
CALLER_PENDING = {
    "cgroup_dir": "the container's cgroup folder under athena's rootless Docker: measured on the box; the caller "
                  "passes it to counters().",
    "uid_map": "the runtime's user-namespace map (javier's 100000:65536 on athena, card Part 1 step 6): the caller "
               "passes it to agent_processes().",
    "XDG_RUNTIME_DIR in the take": "whether the take's exec needs XDG_RUNTIME_DIR set inside the container (the "
                                   "guards plan's stub take, line 329): measured at the stub take.",
    "tree ownership": "the run tree's and the config folder's ownership and modes under the user-namespace map, and "
                      "the removal road for uid-mapped files the agent leaves: measured at the stub take.",
}

_HEX64 = re.compile(r"[0-9a-f]{64}")
_IMAGE_ID = re.compile(r"sha256:[0-9a-f]{64}")
_CPUS = re.compile(r"[1-9][0-9]*(\.[0-9]{1,3})?|0\.[0-9]{0,2}[1-9]")
_NAME = re.compile(r"[A-Z_][A-Z0-9_]*")


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
            "TOP_FORMAT": TOP_FORMAT, "INSPECT_STATUS": INSPECT_STATUS}


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
    """`docker create` for one take container: no environment, no alias, exactly two mounts, PID 1 the keep-alive."""
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
    out = {}
    for name, value in TAKE_ENV[harness].items():
        out[name] = f"{tree}/{RUN_TREE_TMPDIR}" if value == RUN_TREE_TMP else value
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


def launcher_argv(login: str, values: dict, inner) -> list:
    """The turn's command inside the take container: LAUNCHER, the credential's name, the count of pairs, the
    NAME=VALUE pairs in name order, then the harness's argv. The launcher execs the harness with exactly the pairs and
    the credential (read by its name from the exec's environment): the agent starts from an empty environment."""
    inner = _check_argv(inner) if inner else None
    if inner is None:
        raise Refused("the launcher needs the harness's argv")
    if not isinstance(login, str) or not _NAME.fullmatch(login):
        raise Refused("the credential is named by a variable NAME")
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
    the box root, and (given the per-take config folder, HOME's host side) in HOME. Read host-side, a link counted."""
    found = []
    for d in env_file_dirs(workdir, run_tree):
        for name in ENV_FILE_NAMES:
            if os.path.lexists(os.path.join(d, name)):
                found.append(os.path.join(d, name))
    if config_dir is not None:
        cfg = _abs_path(config_dir, "config_dir")
        for h, row in TAKE_ENV.items():
            if row.get("HOME") != CONFIG_MOUNT:
                raise Refused(f"the {h} row's HOME is not the config mount: its .env cannot be read")
        for name in ENV_FILE_NAMES:
            if os.path.lexists(os.path.join(cfg, name)):
                found.append(f"HOME ({CONFIG_MOUNT}) {os.path.join(cfg, name)}")
    if found:
        raise Refused("a .env file a harness would read is present, so the take is refused: " + "; ".join(found))


def _own_environment():
    """This process's own environment: always checked, whatever caller_env a caller passes (W4B1-9)."""
    return os.environ


def check_environment(harness: str, caller_env=None, requested=()) -> None:
    """Refuse the take when any refused name is set in this process's own environment, in the caller_env given (the
    client env's seam, never a switch for this refusal) or requested for the exec. Names only; values never read."""
    refused = refused_variables(harness)
    names = set(_own_environment()) | (set(caller_env) if caller_env is not None else set())
    in_caller = sorted(n for n in names if n in refused)
    if in_caller:
        raise Refused(f"refused variable(s) set in the caller's environment for a {harness} take: {', '.join(in_caller)}")
    asked = sorted(n for n in requested if n in refused)
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
        raise NotReady(CODEX_SUBSCRIPTION_NOT_READY)
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
    values = exec_values(harness, run_tree)
    check_environment(harness, src, set(values))
    if login in values:
        raise Refused("the login variable never rides with a value in argv")
    value = read_login(login_file, login)
    argv = [RUNTIME_CLIENT, "exec", "--user", AGENT_USER, "--workdir", workdir, "-e", login,
            container_id, *launcher_argv(login, values, inner)]
    env = runtime_env(src)
    env[login] = value
    return argv, env


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


def read_login(path: str, name: str) -> str:
    """The one value of a login file: exactly `name=<20+ chars, no whitespace, no double quote>\\n`, mode 600, owned by
    the reading uid, outside every repository. Every refusal names the file and the rule, never the value."""
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


def proxy_create_argv(network_id: str, proxy: ProxyLaunch) -> list:
    _check_proxy(proxy)
    return [RUNTIME_CLIENT, "create", "--pull=never", "--network", _check_id(network_id, "network id"),
            "--network-alias", PROXY_ALIAS, "--user", proxy.user,
            "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
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
        c = _step(runtime, launched, "sidecar-create", list(sidecar.create_argv), env)
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


# ------------------------------------------------------------------------------------------------- one turn
def run_turn(runtime, take_id: str, inner, *, harness: str, run_tree: str, login_file: str, stream_path: str,
             budget_s: float, clock, caller_env=None) -> dict:
    """One exec per turn in the kept-alive container; stdout written to the host-side stream path; times from the
    injected clock. A timeout is recorded as a timed-out exec: the caller then kills the agent's processes inside
    (killing the client alone leaves them running). The launch journal records the submitted exec request,
    not proof that Docker started it; started_at is submission time. The returned exit/timeout record and retained
    stream must be bound to it before the checker claims an executed interaction."""
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
