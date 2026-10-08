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

THE ENVIRONMENT PER HARNESS (D8 B2 item 10). Non-secret values ride as `-e NAME=VALUE`; the login variable rides as
`-e NAME` only, its value only in the client environment handed to `runtime.run`. Arm A keeps round 3's refusal of
every API-key and billing-route variable whole (drive.py's three tuples, bound by `ast` in the tests); arms O and G
each admit exactly their own vendor's one variable and refuse every other, Anthropic's included (the named departure
from the drive.py task's GOTCHA, D8 B2 item 7). A take is refused when any refused name is set in the caller's own
environment or requested for the exec.

PENDING (interface 15). A value only the real box or a walk can tell is the constant `PENDING`, listed with its
reason in `PENDING_WHY`; `pending()` names every one still pending, and a real use that needs one raises `NotReady`.
No public function takes a PENDING value as a parameter; the one documented exception is `TakeSpec`'s per-take
resources, which are refused while they hold the PENDING defaults.

No model, no network, standard library only (plus the seam's `agent_adapter` and `harness_bookkeeping`).
"""

from __future__ import annotations

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

# ------------------------------------------------------------------------------------------ per-harness tables
LOGIN_VARIABLE = {CLAUDE_CODE: "CLAUDE_CODE_OAUTH_TOKEN", CODEX: "CODEX_API_KEY", GEMINI: "GEMINI_API_KEY"}
HARNESS_ENV = {
    CLAUDE_CODE: {"DISABLE_AUTOUPDATER": "1", "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
                  "HTTPS_PROXY": PROXY_URL, **ISOLATION_ENV, "CLAUDE_CONFIG_DIR": CONFIG_MOUNT},
    CODEX: {"HTTPS_PROXY": PROXY_URL, "CODEX_HOME": CONFIG_MOUNT},
    GEMINI: {"HTTPS_PROXY": PROXY_URL, "GEMINI_CLI_HOME": CONFIG_MOUNT},
}
# Claude Code's refusal-fallback and model-fallback variables: {name: value} once confirmed at the pinned version.
FALLBACK_ENV = PENDING
# Arms O and G's own billing-route variables (a Vertex switch for Gemini CLI, for example): a tuple of names each,
# named from the harness's documentation at the pinned version. Until then the refused set is the closed list above,
# and an exec of either harness is refused (NotReady): this lane's stricter reading.
VENDOR_BILLING_ROUTE_VARIABLES = {CODEX: PENDING, GEMINI: PENDING}

# What the runtime client itself needs from the caller's environment, and nothing else.
RUNTIME_ENV_NAMES = ("PATH", "HOME", "DOCKER_HOST", "XDG_RUNTIME_DIR")

# `docker top`'s column form under rootless Docker: {"ps_options": [...], "pid_column": str, "uid_column": str}
# once measured on the box.
TOP_FORMAT = PENDING

# The Docker Engine API's spelling of each inspected fact (taken from the Engine API's ContainerInspect, never
# driven). INSPECT_STATUS stays PENDING until the stub take reads one inspect; while it is, every comparison and
# every state read refuses (NotReady).
INSPECT_PATHS = {
    "image": "Image", "user": "Config.User", "cmd": "Config.Cmd", "env": "Config.Env",
    "working_dir": "Config.WorkingDir", "network_mode": "HostConfig.NetworkMode",
    "cap_drop": "HostConfig.CapDrop", "cap_add": "HostConfig.CapAdd", "security_opt": "HostConfig.SecurityOpt",
    "privileged": "HostConfig.Privileged", "devices": "HostConfig.Devices", "pid_mode": "HostConfig.PidMode",
    "pids_limit": "HostConfig.PidsLimit", "memory": "HostConfig.Memory",
    "memory_reservation": "HostConfig.MemoryReservation", "nano_cpus": "HostConfig.NanoCpus",
    "mounts": "Mounts", "running": "State.Running", "exit_code": "State.ExitCode", "oom_killed": "State.OOMKilled",
}
INSPECT_STATUS = PENDING

PENDING_WHY = {
    "FALLBACK_ENV": "Claude Code's refusal-fallback and model-fallback variables, names and values: confirmed at "
                    "the pinned version (plan, run_take task).",
    "VENDOR_BILLING_ROUTE_VARIABLES": "arms O and G's own billing-route variables: named from each harness's "
                                      "documentation at the pinned version (D8 B2 item 7).",
    "TOP_FORMAT": "the column form `docker top` prints under rootless Docker: measured on the box.",
    "INSPECT_STATUS": "the inspect spellings, taken from the Docker Engine API: confirmed when the stub take reads "
                      "one inspect.",
    "TakeSpec.resources": "the take's memory reservation, CPU and pids values: measured at the cold-start stub take "
                          "('all recorded').",
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
        raise NotImplementedError("red: not built yet")


class TeardownError(RuntimeError):
    """A teardown step failed; every other step still ran. `record` names each step and its outcome."""

    def __init__(self, message: str, record: dict):
        raise NotImplementedError("red: not built yet")


class LeakedContainer(Refused):
    """A recorded container is still present: the restart is refused and the container named."""


def _is_pending(v) -> bool:
    raise NotImplementedError("red: not built yet")


def pending() -> dict:
    """Every value this module holds that is still PENDING, with its reason (resources: always, by design)."""
    raise NotImplementedError("red: not built yet")


# ---------------------------------------------------------------------------------------- the runtime protocol
@dataclass(frozen=True)
class Completed:
    returncode: int
    stdout: str
    stderr: str


def _check_argv(argv) -> list:
    raise NotImplementedError("red: not built yet")


class DockerRuntime:
    """The one real runtime: the box's only subprocess call (interface 10)."""

    def run(self, argv: list, *, env: dict | None = None, timeout: float | None = None) -> Completed:
        raise NotImplementedError("red: not built yet")


def runtime_env(caller_env=None) -> dict:
    """The runtime client's own needs from the caller's environment, built from nothing."""
    raise NotImplementedError("red: not built yet")


# ------------------------------------------------------------------------------------------- the take container
def _abs_path(p, what: str) -> str:
    raise NotImplementedError("red: not built yet")


def _inside(child: str, parent: str) -> bool:
    raise NotImplementedError("red: not built yet")


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
        raise NotImplementedError("red: not built yet")


def _positive_int(v) -> bool:
    raise NotImplementedError("red: not built yet")


def check_spec(spec: TakeSpec) -> None:
    """Refuse a spec create_argv must not run: a PENDING resource (NotReady), or any value off its rule."""
    raise NotImplementedError("red: not built yet")


def create_argv(spec: TakeSpec) -> list:
    """`docker create` for one take container: no environment, no alias, exactly two mounts, PID 1 the keep-alive."""
    raise NotImplementedError("red: not built yet")


# ---------------------------------------------------------------------------------- the environment per harness
def _known_harness(harness) -> str:
    raise NotImplementedError("red: not built yet")


def refused_variables(harness: str) -> frozenset:
    """The closed refused set for one take's harness: every key, token and billing-route name, less its own login."""
    raise NotImplementedError("red: not built yet")


def exec_values(harness: str, run_tree: str) -> dict:
    """The exec's non-secret values for one harness (no login). Refuses while a value it needs is PENDING."""
    raise NotImplementedError("red: not built yet")


def check_environment(harness: str, caller_env=None, requested=()) -> None:
    """Refuse the take when any refused name is set in the caller's environment or requested for the exec."""
    raise NotImplementedError("red: not built yet")


def exec_argv(container_id: str, inner, *, user: str, workdir: str, harness: str, run_tree: str, login_file: str,
              caller_env=None) -> tuple:
    """One turn's `docker exec` as the agent, and the client environment. The login rides by name only."""
    raise NotImplementedError("red: not built yet")


def agent_exec_argv(container_id: str, inner, *, workdir: str = "/") -> list:
    """A plain exec as the agent with no variable at all (preflight's reads, the kill)."""
    raise NotImplementedError("red: not built yet")


# ------------------------------------------------------------------------------------------------ the login read
def outside_every_repository(path: str) -> bool:
    """No ancestor folder of `path` (the path itself included, when a folder) holds a `.git`."""
    raise NotImplementedError("red: not built yet")


LOGIN_MAX_BYTES = 4096


def read_login(path: str, name: str) -> str:
    """The one value of a login file: exactly `name=<20+ chars, no whitespace, no double quote>\\n`, mode 600, owned by
    the reading uid, outside every repository. Every refusal names the file and the rule, never the value."""
    raise NotImplementedError("red: not built yet")


# ------------------------------------------------------------------------------------------ the config folder
def make_config_dir(parent: str) -> str:
    """A fresh per-take config folder under `parent`, outside every repository."""
    raise NotImplementedError("red: not built yet")


def remove_config_dir(launched: "Launched", *, published: bool) -> str:
    """Delete the config folder by the path launch recorded, and only once the take's records are published."""
    raise NotImplementedError("red: not built yet")


# ------------------------------------------------------------------------------------------------ launch records
def _check_id(v, what: str) -> str:
    raise NotImplementedError("red: not built yet")


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
    """Every id the moment the runtime returned it, every argv and every inspect: the launch record."""
    config_dir: str | None = None
    network_id: str | None = None
    proxy_id: str | None = None
    sidecar_id: str | None = None
    take_id: str | None = None
    steps: list = field(default_factory=list)
    ok: bool = False
    failure: str | None = None
    torn_down: list = field(default_factory=list)

    def ids(self) -> list:
        raise NotImplementedError("red: not built yet")

    def to_record(self) -> dict:
        raise NotImplementedError("red: not built yet")


LAUNCH_RECORD = "launch.json"
PROXY_LOG = "proxy.log"
STEP_TIMEOUT_S = 120


class _StepFailed(RuntimeError):
    pass


def _step(runtime, launched: Launched, name: str, argv: list, env: dict) -> Completed:
    raise NotImplementedError("red: not built yet")


def _new_id(c: Completed, what: str) -> str:
    raise NotImplementedError("red: not built yet")


def _inspect(runtime, launched: Launched, name: str, cid: str, env: dict) -> dict:
    raise NotImplementedError("red: not built yet")


def _check_proxy(proxy: ProxyLaunch) -> None:
    raise NotImplementedError("red: not built yet")


def _check_sidecar(sidecar: SidecarLaunch) -> None:
    raise NotImplementedError("red: not built yet")


def proxy_create_argv(network_id: str, proxy: ProxyLaunch) -> list:
    raise NotImplementedError("red: not built yet")


def network_name() -> str:
    """A fresh, neutral name for the take's internal network (the runtime needs one; removal is by id)."""
    raise NotImplementedError("red: not built yet")


def launch(runtime, spec: TakeSpec, *, sidecar: SidecarLaunch, proxy: ProxyLaunch, record_dir: str,
           caller_env=None) -> Launched:
    """Network, proxy, sidecar, take container, each created, inspected where interface 12 says, then started. A
    failure tears down everything made so far by its recorded id and raises LaunchError carrying the record. No agent
    turn ever runs here. The launch record is written to `record_dir` either way."""
    raise NotImplementedError("red: not built yet")


def _write_json(path: str, doc: dict) -> None:
    raise NotImplementedError("red: not built yet")


def _rm(runtime, cid: str, env: dict, sidecar: SidecarLaunch | None = None, kind: str = "") -> Completed:
    raise NotImplementedError("red: not built yet")


def _capture_proxy_log(runtime, proxy_id: str, record_dir: str, env: dict) -> Completed:
    raise NotImplementedError("red: not built yet")


def _teardown_partial(runtime, launched: Launched, sidecar: SidecarLaunch, record_dir: str, env: dict) -> None:
    """After a launch failure: remove what was made, in teardown order, each by its recorded id. No `finish`: the
    sidecar never began."""
    raise NotImplementedError("red: not built yet")


def teardown(runtime, launched: Launched, *, sidecar: SidecarLaunch, record_dir: str, caller_env=None) -> dict:
    """Interface 12's teardown order, each by its recorded id: the take container removed, then `ctl finish`, then
    the proxy's log captured into the record folder, then the sidecar, the proxy and the network removed. A step that
    fails is recorded and the rest still run; `finish` is skipped when the take's removal failed (it is called only
    after the take container is gone). Raises TeardownError when any step failed."""
    raise NotImplementedError("red: not built yet")


# ------------------------------------------------------------------------------------------- leaked containers
def leaked(runtime, recorded_ids, *, caller_env=None) -> list:
    """The recorded ids still present in the runtime's full-id listing of every container (no filter, ever)."""
    raise NotImplementedError("red: not built yet")


def refuse_restart_if_leaked(runtime, recorded_ids, *, caller_env=None) -> None:
    """A leaked container that is still present refuses the restart and names the container."""
    raise NotImplementedError("red: not built yet")


# ---------------------------------------------------------------------------------- the agent's leftover processes
def host_uid(container_uid: int, uid_map) -> int:
    """The host uid a container uid maps to, through `uid_map` lines (container start, host start, length)."""
    raise NotImplementedError("red: not built yet")


def _int_ge0(v) -> bool:
    raise NotImplementedError("red: not built yet")


def _uid_of(user: str) -> int:
    raise NotImplementedError("red: not built yet")


def agent_processes(runtime, take_id: str, *, agent_uid: int, uid_map, caller_env=None) -> list:
    """Host pids of the agent's processes in the take container, from `docker top` (host-side, mapped uids)."""
    raise NotImplementedError("red: not built yet")


def kill_agent(runtime, take_id: str, *, agent_user: str, caller_env=None) -> Completed:
    """An exec as the agent's own uid that sends KILL to all of that uid's processes (no capability needed)."""
    raise NotImplementedError("red: not built yet")


def wait_gone(runtime, take_id: str, *, agent_uid: int, uid_map, cap_s: float, interval_s: float, clock, sleep,
              caller_env=None) -> list:
    """Poll until no agent process remains or the cap passes; return the survivors (empty when gone)."""
    raise NotImplementedError("red: not built yet")


# ------------------------------------------------------------------------------------------------ the counters
# Each counter's read key is its COUNTER_FIELDS name less `_delta`; the file and line it is read from.
COUNTER_SOURCES = {"oom_kill": ("memory.events", "oom_kill"), "pids_max": ("pids.events", "max")}
_DELTA = "_delta"


def counters(cgroup_dir: str) -> dict:
    """`oom_kill` from memory.events and `max` from pids.events, read host-side. A missing file or line raises."""
    raise NotImplementedError("red: not built yet")


def counter_delta(before: dict, after: dict) -> dict:
    """The rise of each counter, keyed by agent_adapter.COUNTER_FIELDS. A counter that fell is refused."""
    raise NotImplementedError("red: not built yet")


# ----------------------------------------------------------------------------------------------- the exit record
def _path_get(doc: dict, dotted: str):
    raise NotImplementedError("red: not built yet")


def container_state(runtime, cid: str, *, caller_env=None) -> dict:
    """The runtime's exit record: Running, ExitCode and OOMKilled from the inspect's State."""
    raise NotImplementedError("red: not built yet")


# ------------------------------------------------------------------------------------------------- one turn
def run_turn(runtime, take_id: str, inner, *, harness: str, run_tree: str, login_file: str, stream_path: str,
             budget_s: float, clock, caller_env=None) -> dict:
    """One exec per turn in the kept-alive container; stdout written to the host-side stream path; times from the
    injected clock. A timeout is recorded as a timed-out exec: the caller then kills the agent's processes inside
    (killing the client alone leaves them running)."""
    raise NotImplementedError("red: not built yet")
