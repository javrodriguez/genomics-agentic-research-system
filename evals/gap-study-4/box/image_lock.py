"""image_lock.py: the box images' locks, read through one closed schema, and the check of a built image's labels.

Every image of the sealed box (CP2) is a committed Dockerfile with an `image.lock` beside it:

    box/image.lock           take-a    the arm A (and C) take image
    box/codex/image.lock     take-o    the arm O take image
    box/gemini/image.lock    take-g    the arm G take image
    box/sidecar/image.lock   sidecar   the sidecar's image (ruling C1: never used for a take)
    box/egress/image.lock    egress    the egress proxy's image

A lock records what only a real build can tell: the base digest, the harness's npm version, the image's Python
version and the built image id (and, for the egress image only, the squid package version). In wave 4 nothing is
built, so each of those is the string PENDING with its reason in the lock's `pending` map (interface 15). A lock
that holds a PENDING value is never ready: `require_ready` raises NotReady naming every pending field, `build_argv`
refuses to construct a build while an input of the build is pending, and `check_labels` refuses the lock whatever a
built image's labels say, so a lock that was never filled can never pass.

The schema is closed: any other key, a missing key or a wrong shape is refused (LockError). Which fields may be null
is bound by the lock's `image`, through the closed table NULLABLE.

The Dockerfiles are read by this module's own small parser (`parse_dockerfile`: instructions, line continuations,
comments; a parser directive, a heredoc or an unknown instruction is refused) and checked against their lock by
`check_dockerfile`, which returns every way a Dockerfile departs from the image rules of CP2 (base by digest from the
lock, the harness at the lock's exact version and a check that the installed version is that version, the recorded
Python, the closed package line, the two fixed non-root users, git's ownership setting, nothing of the study copied
into a take image, and the labels from the build arguments).

This module constructs argv lists only; it never runs one, and it imports no process module.
Standard library only.
"""

from __future__ import annotations

import fnmatch
import json
import os
import re
from dataclasses import dataclass

import harness_bookkeeping
from box.egress import proxy_conf

PENDING = "PENDING"
SCHEMA = 1

BOX_DIR = os.path.dirname(os.path.abspath(__file__))

# The fixed ids (interface 11; this lane owns them). Each user's gid equals its uid.
AGENT_UID = 10001
WATCHER_UID = 10002
KEEPALIVE_UID = 10003

TAKE_IMAGES = ("take-a", "take-o", "take-g")
SIDECAR_IMAGE = "sidecar"
EGRESS_IMAGE = "egress"
IMAGES = TAKE_IMAGES + (SIDECAR_IMAGE, EGRESS_IMAGE)

# Each image's Dockerfile, relative to BOX_DIR (the lock's `dockerfile`, and the lock sits beside it).
DOCKERFILES = {
    "take-a": "Dockerfile",
    "take-o": "codex/Dockerfile",
    "take-g": "gemini/Dockerfile",
    SIDECAR_IMAGE: "sidecar/Dockerfile",
    EGRESS_IMAGE: "egress/Dockerfile",
}

# Nullability by image: "required" never null, "null" always null, "null-or-pending" null or PENDING (never a
# pinned value: the egress image records no Python, so a pending one keeps its lock unready, as the brief reads).
REQUIRED, NULL, NULL_OR_PENDING = "required", "null", "null-or-pending"
NULLABLE = {
    "take-a": {"harness": REQUIRED, "python": REQUIRED, "users": REQUIRED},
    "take-o": {"harness": REQUIRED, "python": REQUIRED, "users": REQUIRED},
    "take-g": {"harness": REQUIRED, "python": REQUIRED, "users": REQUIRED},
    SIDECAR_IMAGE: {"harness": NULL, "python": REQUIRED, "users": REQUIRED},
    EGRESS_IMAGE: {"harness": NULL, "python": NULL_OR_PENDING, "users": NULL},
}

KEYS = ("schema", "image", "dockerfile", "base", "harness", "python", "image_id", "users", "pending")
# Schema 2 (glitch-06's lock-writer rulings, 14 Oct 2026): the filled lock, written only by ops/write_image_lock.py
# from a committed build record. Schema 1 is the unfilled lock: its image_id is always PENDING. A schema-2 lock
# carries the content identity preflight checks (`manifest_digest`, the platform image manifest, which names the
# config and every layer), the config digest from BuildKit's metadata, and the commit the image was built from;
# `image_id` (the index digest, new on every build: BuildKit's provenance attestation) stays a recorded field.
SCHEMA_2 = 2
SCHEMA_2_KEYS = ("manifest_digest", "config_digest", "source_commit")
COMMIT_RE = re.compile(r"[0-9a-f]{40}")
# Keys only some images carry: the egress lock, and only it, carries `squid`.
EXTRA_KEYS = {EGRESS_IMAGE: ("squid",)}

# Every field that may hold PENDING, as the `pending` map names it.
PENDABLE = ("base", "harness.version", "python", "image_id", "squid")

# A repository name (an optional registry host with port, then path parts), never a tag, then the digest.
BASE_RE = re.compile(r"(?P<name>([a-z0-9]([a-z0-9.-]*[a-z0-9])?(:[0-9]+)?/)?[a-z0-9]+([._-][a-z0-9]+)*(/[a-z0-9]+([._-][a-z0-9]+)*)*)@(?P<digest>sha256:[0-9a-f]{64})")
VERSION_RE = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+")
# The in-container floor is Python 3.11 (interface 17).
PYTHON_RE = re.compile(r"3\.(1[1-9]|[2-9][0-9])\.[0-9]+")
IMAGE_ID_RE = re.compile(r"sha256:[0-9a-f]{64}")
SQUID_RE = re.compile(r"[0-9]+\.[0-9]+[A-Za-z0-9.+~:-]*")
PACKAGE_RE = re.compile(r"@[a-z0-9-]+/[a-z0-9-]+")
NAME_RE = re.compile(r"[a-z][a-z0-9]{1,15}")
# Names a box user may never take: root, the usual system accounts, and the users a base or package may bring.
RESERVED_NAMES = ("root", "daemon", "bin", "sys", "nobody", "node", "proxy", "squid")

# The labels a built image carries (requirement 9), a closed tuple, each from one build argument.
BASE_NAME_LABEL = "org.opencontainers.image.base.name"
BASE_DIGEST_LABEL = "org.opencontainers.image.base.digest"
CLI_LABEL = "app.cli.version"
PYTHON_LABEL = "app.python.version"
SQUID_LABEL = "app.squid.version"
LABELS = (BASE_NAME_LABEL, BASE_DIGEST_LABEL, CLI_LABEL, PYTHON_LABEL, SQUID_LABEL)
# The build argument each label reads.
LABEL_ARGS = {
    BASE_NAME_LABEL: "BASE_NAME",
    BASE_DIGEST_LABEL: "BASE_DIGEST",
    CLI_LABEL: "HARNESS_VERSION",
    PYTHON_LABEL: "PYTHON_VERSION",
    SQUID_LABEL: "SQUID_VERSION",
}
BUILD_ARGS = ("BASE", "BASE_NAME", "BASE_DIGEST", "HARNESS_VERSION", "PYTHON_VERSION", "SQUID_VERSION")

CLIENT = "docker"

# Each take image's npm package, built from the seam's harness names (imported, never typed here).
HARNESS_PACKAGES = {
    "take-a": "@anthropic-ai/" + harness_bookkeeping.CLAUDE_CODE,
    "take-o": "@openai/" + proxy_conf.CODEX,
    "take-g": "@google/" + proxy_conf.GEMINI + "-cli",
}


class LockError(ValueError):
    """A lock that is not the closed schema."""


class NotReady(RuntimeError):
    """A real use of a lock while a value it needs is PENDING."""


def _is_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _value(v, pattern, field: str, problems: list, *, pendable=True) -> None:
    if pendable and v == PENDING:
        return
    if not isinstance(v, str) or not pattern.fullmatch(v):
        problems.append(f"{field}: {v!r} is neither {PENDING} nor the pinned shape")


def _user(entry, role: str, uid: int, named: bool, problems: list) -> None:
    keys = ("name", "uid", "gid") if named else ("uid", "gid")
    if not isinstance(entry, dict) or tuple(sorted(entry)) != tuple(sorted(keys)):
        problems.append(f"users.{role}: must hold exactly {list(keys)}")
        return
    if named and (not isinstance(entry["name"], str) or not NAME_RE.fullmatch(entry["name"])
                  or entry["name"] in RESERVED_NAMES):
        problems.append(f"users.{role}.name: {entry['name']!r} is not a plain, unreserved user name")
    if not _is_int(entry["uid"]) or entry["uid"] != uid:
        problems.append(f"users.{role}.uid: must be {uid}")
    if not _is_int(entry["gid"]) or entry["gid"] != uid:
        problems.append(f"users.{role}.gid: must equal its uid {uid}")


def _pending_fields(lock: dict) -> list:
    out = []
    for field in PENDABLE:
        head, _, tail = field.partition(".")
        v = lock.get(head)
        if tail:
            v = v.get(tail) if isinstance(v, dict) else None
        if v == PENDING:
            out.append(field)
    return out


def problems(lock) -> list:
    """Every way `lock` is not the closed schema ([] when it is)."""
    if not isinstance(lock, dict):
        return ["the lock is not an object"]
    image = lock.get("image")
    if image not in IMAGES:
        return [f"image: {image!r} is not one of {list(IMAGES)}"]
    out = []
    want = set(KEYS) | set(EXTRA_KEYS.get(image, ())) | (set(SCHEMA_2_KEYS) if lock.get("schema") == SCHEMA_2 else set())
    for k in sorted(want - set(lock)):
        out.append(f"missing key {k!r}")
    for k in sorted(set(lock) - want):
        out.append(f"unknown key {k!r}")
    if out:
        return out
    if not _is_int(lock["schema"]) or lock["schema"] not in (SCHEMA, SCHEMA_2):
        out.append(f"schema: must be {SCHEMA} (unfilled) or {SCHEMA_2} (filled by the lock writer)")
    elif lock["schema"] == SCHEMA and lock["image_id"] != PENDING:
        out.append(f"schema {SCHEMA} is the unfilled lock: an image id is pinned only in a schema-{SCHEMA_2} lock, "
                   f"written by the lock writer from a committed build record")
    elif lock["schema"] == SCHEMA_2:
        for k in ("manifest_digest", "config_digest"):
            _value(lock[k], IMAGE_ID_RE, k, out, pendable=False)
        if not isinstance(lock["source_commit"], str) or not COMMIT_RE.fullmatch(lock["source_commit"]):
            out.append("source_commit: a 40-hex commit id")
        if _pending_fields(lock) or lock["pending"] != {}:
            out.append(f"schema {SCHEMA_2} holds no {PENDING} value and no pending reason")
    if lock["dockerfile"] != DOCKERFILES[image]:
        out.append(f"dockerfile: must be {DOCKERFILES[image]!r} for {image}")
    _value(lock["base"], BASE_RE, "base", out)
    _value(lock["image_id"], IMAGE_ID_RE, "image_id", out)
    rules = NULLABLE[image]
    for field in ("harness", "python", "users"):
        v, rule = lock[field], rules[field]
        if rule == NULL and v is not None:
            out.append(f"{field}: must be null for {image}")
            continue
        if rule == REQUIRED and v is None:
            out.append(f"{field}: may not be null for {image}")
            continue
        if rule == NULL_OR_PENDING and v not in (None, PENDING):
            out.append(f"{field}: must be null or {PENDING} for {image}")
            continue
        if v is None:
            continue
        if field == "harness":
            if not isinstance(v, dict) or sorted(v) != ["package", "version"]:
                out.append("harness: must hold exactly package and version")
            else:
                _value(v["package"], PACKAGE_RE, "harness.package", out, pendable=False)
                if v["package"] != HARNESS_PACKAGES.get(image):
                    out.append(f"harness.package: {v['package']!r} is not {image}'s harness")
                _value(v["version"], VERSION_RE, "harness.version", out)
        elif field == "python":
            _value(v, PYTHON_RE, "python", out)
        else:
            if not isinstance(v, dict) or sorted(v) != ["agent", "keepalive", "watcher"]:
                out.append("users: must hold exactly agent, watcher and keepalive")
            else:
                _user(v["agent"], "agent", AGENT_UID, True, out)
                _user(v["watcher"], "watcher", WATCHER_UID, True, out)
                _user(v["keepalive"], "keepalive", KEEPALIVE_UID, False, out)
                names = [v[r].get("name") for r in ("agent", "watcher") if isinstance(v[r], dict)]
                if len(names) == 2 and names[0] == names[1]:
                    out.append("users: the agent and the watcher must have different names")
    if "squid" in lock:
        _value(lock["squid"], SQUID_RE, "squid", out)
    pend = lock["pending"]
    if not isinstance(pend, dict):
        out.append("pending: must be an object")
        return out
    held = _pending_fields(lock)
    for f in held:
        if f not in pend:
            out.append(f"{f} is {PENDING} but `pending` does not explain it")
    for f, why in pend.items():
        if f not in held:
            out.append(f"pending names {f!r}, which holds no {PENDING} value")
        if not isinstance(why, str) or not why.strip():
            out.append(f"pending[{f!r}]: the reason must be a non-empty string")
    return out


def validate(lock) -> dict:
    """Return `lock` when it is the closed schema; raise LockError naming every problem otherwise."""
    found = problems(lock)
    if found:
        raise LockError("; ".join(found))
    return lock


def _no_duplicates(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise LockError(f"duplicate key {k!r}")
        out[k] = v
    return out


def load(path: str) -> dict:
    """Read one lock file, refuse anything but the closed schema, and bind it to the Dockerfile beside it."""
    with open(path, encoding="utf-8") as fh:
        lock = json.load(fh, object_pairs_hook=_no_duplicates)
    validate(lock)
    beside = os.path.join(os.path.dirname(os.path.abspath(path)), "Dockerfile")
    if os.path.abspath(os.path.join(BOX_DIR, lock["dockerfile"])) != beside:
        raise LockError(f"dockerfile: {lock['dockerfile']!r} is not the Dockerfile beside {path}")
    return lock


def pending(lock) -> tuple:
    """The fields of `lock` that hold PENDING, in PENDABLE order."""
    return tuple(_pending_fields(validate(lock)))


def ready(lock) -> bool:
    return not pending(lock)


def require_ready(lock) -> dict:
    held = pending(lock)
    if held:
        raise NotReady("the lock is not ready; pending: " + ", ".join(held))
    return lock


def _base_parts(lock) -> tuple:
    m = BASE_RE.fullmatch(lock["base"])
    return m.group("name"), m.group("digest")


def build_args(lock) -> dict:
    """The build arguments of `lock`'s image, from its values; refuses while any of them is PENDING."""
    validate(lock)
    held = [f for f in _pending_fields(lock) if f != "image_id"]
    if held:
        raise NotReady("a build input is pending: " + ", ".join(held))
    name, digest = _base_parts(lock)
    args = {"BASE": lock["base"], "BASE_NAME": name, "BASE_DIGEST": digest}
    if lock["harness"] is not None:
        args["HARNESS_VERSION"] = lock["harness"]["version"]
    if lock["python"] is not None:
        args["PYTHON_VERSION"] = lock["python"]
    if "squid" in lock:
        args["SQUID_VERSION"] = lock["squid"]
    return {k: args[k] for k in BUILD_ARGS if k in args}


def expected_labels(lock) -> dict:
    """The labels a build of `lock` carries: each label key with the value of its build argument."""
    args = build_args(lock)
    return {k: args[LABEL_ARGS[k]] for k in LABELS if LABEL_ARGS[k] in args}


def check_labels(lock, inspect) -> list:
    """Problems with one `docker image inspect` object against `lock` ([] when they agree).

    A lock holding any PENDING value is refused whatever the labels say."""
    try:
        validate(lock)
    except LockError as e:
        return [f"lock refused: {e}"]
    held = _pending_fields(lock)
    if held:
        return [f"lock refused: {f} is {PENDING}" for f in held]
    if not isinstance(inspect, dict):
        return ["inspect: not an object"]
    out = []
    if inspect.get("Id") != lock["image_id"]:
        out.append(f"Id: {inspect.get('Id')!r} is not the lock's image_id")
    config = inspect.get("Config")
    labels = config.get("Labels") if isinstance(config, dict) else None
    if labels is None:
        labels = {}
    if not isinstance(labels, dict):
        return out + ["Config.Labels: not an object"]
    want = expected_labels(lock)
    for k in want:
        if k not in labels:
            out.append(f"label {k!r} missing")
        elif labels[k] != want[k]:
            out.append(f"label {k!r} is {labels[k]!r}, the lock says {want[k]!r}")
    for k in sorted(set(labels) - set(want)):
        out.append(f"label {k!r} is not one the lock names")
    return out


def build_argv(lock, *, context: str) -> list:
    """The `docker build` argv for `lock`'s image (constructed, never run); refuses while a build input is PENDING.

    It builds from any `lock` that validates, a hand-filled dict included: no committed lock file need stand behind
    it. The drive step passes only `load()` output, so the argv is always the committed lock's (fold 3, W4A1-8)."""
    args = build_args(lock)
    if not isinstance(context, str) or not os.path.isabs(context):
        raise ValueError("context must be an absolute path")
    if lock["image"] == SIDECAR_IMAGE and os.path.abspath(context) != BOX_DIR:
        raise ValueError(f"the sidecar image's build context is {BOX_DIR}")
    argv = [CLIENT, "build", "--pull=false", "--file", os.path.join(BOX_DIR, lock["dockerfile"])]
    for k, v in args.items():
        argv += ["--build-arg", f"{k}={v}"]
    for k, v in expected_labels(lock).items():
        argv += ["--label", f"{k}={v}"]
    argv.append(context)
    return argv


# ---------------------------------------------------------------------------------------------------------------
# The Dockerfiles.

class DockerfileError(ValueError):
    """A Dockerfile this parser does not read (it never guesses)."""


# The instructions a box Dockerfile may use at all (a closed set; anything else is refused by the check).
ALLOWED_INSTRUCTIONS = ("ARG", "FROM", "RUN", "ENV", "LABEL", "COPY", "ENTRYPOINT", "USER")
KNOWN_INSTRUCTIONS = ALLOWED_INSTRUCTIONS + ("ADD", "CMD", "EXPOSE", "HEALTHCHECK", "MAINTAINER", "ONBUILD", "SHELL",
                                             "STOPSIGNAL", "VOLUME", "WORKDIR")


@dataclass(frozen=True)
class Instruction:
    line: int        # the line the instruction starts on (1-based)
    keyword: str     # upper case
    args: str        # the arguments, continuation lines joined by one space


# BuildKit's continuation (moby/buildkit frontend/dockerfile/parser/parser.go, its master branch as lane review
# round 1 read it on 8 Oct 2026; no commit was recorded, so this is a citation, not a pin): a line ending in the escape character, optionally
# followed by spaces or tabs, continues; the escape and that whitespace are dropped, the character before it kept.
_CONTINUATION_RE = re.compile(r"([^\\])\\[ \t]*$")
# What a Dockerfile line may hold: printable ASCII, space and tab (no carriage return, no other control or
# non-ASCII character), so this parser and BuildKit read the same bytes.
_DOCKERFILE_CHAR_RE = re.compile(r"[\x20-\x7e\t]*")


def normalized(args: str) -> str:
    """An instruction's arguments with every run of whitespace made one space (what the closed RUN lines compare)."""
    return " ".join(args.split())


def parse_dockerfile(text: str) -> list:
    """The instructions of `text`, joined the way BuildKit joins them.

    The first line of an instruction loses its leading whitespace; each continuation line is appended with no
    separator and its leading whitespace kept; a comment line or an empty line inside a continuation is skipped.
    So `"$(..)"\\` / `=\\` / `"${V}"` reads as `"$(..)"="${V}"`, exactly the word Docker runs."""
    lines = text.split("\n")
    for n, line in enumerate(lines, 1):
        if not _DOCKERFILE_CHAR_RE.fullmatch(line):
            raise DockerfileError(f"line {n}: a character outside printable ASCII, space and tab")
    out, i = [], 0
    while i < len(lines):
        stripped = lines[i].strip(" \t")
        if not stripped or stripped.startswith("#"):
            if re.fullmatch(r"#\s*(syntax|escape|check)\s*=.*", stripped, re.IGNORECASE) and not out:
                raise DockerfileError(f"line {i + 1}: a parser directive is not read here")
            i += 1
            continue
        start = i + 1
        joined, done = _continued(stripped)
        i += 1
        while not done:
            if i >= len(lines):
                raise DockerfileError(f"line {start}: a continuation runs off the end of the file")
            raw = lines[i]
            i += 1
            if raw.strip(" \t").startswith("#") or not raw.strip(" \t"):
                continue
            part, done = _continued(raw)
            joined += part
        keyword, _, args = joined.lstrip(" \t").partition(" ")
        keyword = keyword.upper()
        if keyword not in KNOWN_INSTRUCTIONS:
            raise DockerfileError(f"line {start}: unknown instruction {keyword!r}")
        if "<<" in args:
            raise DockerfileError(f"line {start}: a heredoc is not read here")
        out.append(Instruction(start, keyword, args.strip(" \t")))
    return out


def _continued(line: str) -> tuple:
    """(the line with its continuation escape dropped, whether the instruction ends here)."""
    m = _CONTINUATION_RE.search(line)
    if not m:
        return line, True
    return line[:m.start()] + m.group(1), False


COMMON_BEGIN = "# common:begin"
COMMON_END = "# common:end"


def common_block(text: str) -> str:
    """The lines from `# common:begin` to `# common:end`, both included, exactly as written."""
    lines = text.split("\n")
    if lines.count(COMMON_BEGIN) != 1 or lines.count(COMMON_END) != 1:
        raise DockerfileError("the common block's markers must each appear exactly once")
    a, b = lines.index(COMMON_BEGIN), lines.index(COMMON_END)
    if b < a:
        raise DockerfileError("the common block ends before it begins")
    return "\n".join(lines[a:b + 1])


# The closed package list of the take and sidecar images (one apt-get line, identical in all four).
PACKAGES = ("python3", "git", "inotify-tools", "procps", "ca-certificates")
# Packages no box image may install: container clients and runtimes, and network tools (fnmatch patterns).
FORBIDDEN_PACKAGES = ("docker*", "podman", "containerd", "runc", "buildah", "curl", "wget", "netcat*", "ncat", "nmap",
                      "socat", "openssh-client", "telnet", "dnsutils", "bind9-dnsutils", "iputils-ping", "net-tools",
                      "ftp", "lynx", "aria2")
# Words no RUN may hold, whatever it installs: privilege helpers and fetchers.

PYTHON_CHECK = ("test \"$(python3 -c 'import platform; print(platform.python_version())')\" = \"${PYTHON_VERSION}\"")
GIT_SAFE = "git config --system --add safe.directory '*'"
NPM_INSTALL = 'npm install -g "{package}@${{HARNESS_VERSION}}"'
VERSION_CHECK = ('test "$(node -p \'require(process.argv[1]).version\' "$(npm root -g)/{package}/package.json")"'
                 ' = "${{HARNESS_VERSION}}"')
APT_LINE = ("apt-get update && apt-get install -y --no-install-recommends " + " ".join(PACKAGES)
            + " && rm -rf /var/lib/apt/lists/*")
EGRESS_APT_LINE = ('apt-get update && apt-get install -y --no-install-recommends "squid=${SQUID_VERSION}"'
                   " && rm -rf /var/lib/apt/lists/*")
USERS_LINE = ("groupadd --gid {a[gid]} {a[name]}"
              " && useradd --uid {a[uid]} --gid {a[gid]} --create-home --home-dir /home/{a[name]} --shell /bin/bash"
              " {a[name]}"
              " && groupadd --gid {w[gid]} {w[name]}"
              " && useradd --uid {w[uid]} --gid {w[gid]} --no-create-home --home-dir /nonexistent"
              " --shell /usr/sbin/nologin {w[name]}")
# The sidecar program's path inside the sidecar image (interface 11; merge binding 6 reads it).
SIDECAR_PROGRAM = "/opt/w/sidecar.py"
SIDECAR_COPY = "sidecar.py " + SIDECAR_PROGRAM
SQUID_PACKAGE = "squid=${SQUID_VERSION}"
# The ENV lines each image carries, exactly.
ENVS = {
    "take-a": {"PYTHONDONTWRITEBYTECODE": "1", "DISABLE_AUTOUPDATER": "1"},
    "take-o": {"PYTHONDONTWRITEBYTECODE": "1"},
    "take-g": {"PYTHONDONTWRITEBYTECODE": "1"},
    SIDECAR_IMAGE: {"PYTHONDONTWRITEBYTECODE": "1"},
    EGRESS_IMAGE: {},
}
# The last USER of each image that has one: the agent in a take image, the watcher in the sidecar.
LAST_USER = {
    "take-a": f"{AGENT_UID}:{AGENT_UID}",
    "take-o": f"{AGENT_UID}:{AGENT_UID}",
    "take-g": f"{AGENT_UID}:{AGENT_UID}",
    SIDECAR_IMAGE: f"{WATCHER_UID}:{WATCHER_UID}",
}


def expected_runs(lock) -> list:
    """The RUN lines of `lock`'s image, exactly and in order: a closed vocabulary, so nothing else can run at build."""
    validate(lock)
    image = lock["image"]
    if image == EGRESS_IMAGE:
        return [EGRESS_APT_LINE]
    users = USERS_LINE.format(a=lock["users"]["agent"], w=lock["users"]["watcher"])
    runs = [APT_LINE, PYTHON_CHECK, users, GIT_SAFE]
    if image in TAKE_IMAGES:
        package = lock["harness"]["package"]
        runs += [NPM_INSTALL.format(package=package), VERSION_CHECK.format(package=package)]
    return runs


def arg_names(lock) -> tuple:
    """The build argument names `lock`'s image takes, by the lock's shape (never its values)."""
    validate(lock)
    names = ["BASE", "BASE_NAME", "BASE_DIGEST"]
    if lock["harness"] is not None:
        names.append("HARNESS_VERSION")
    if lock["python"] is not None:
        names.append("PYTHON_VERSION")
    if "squid" in lock:
        names.append("SQUID_VERSION")
    return tuple(n for n in BUILD_ARGS if n in names)


def label_keys(lock) -> tuple:
    """The label keys `lock`'s image carries, by the lock's shape."""
    names = arg_names(lock)
    return tuple(k for k in LABELS if LABEL_ARGS[k] in names)


def _apt_packages(args: str) -> list:
    m = re.search(r"apt-get install((?:\s+\S+)*?)\s*(&&|$)", args)
    if not m:
        return []
    return [t.strip('"') for t in m.group(1).split() if not t.startswith("-")]


def forbidden(packages) -> list:
    """The packages of `packages` on the forbidden list."""
    return [p for p in packages if any(fnmatch.fnmatchcase(p, pat) for pat in FORBIDDEN_PACKAGES)]


_VALUE_OPTS = ("--uid", "--gid", "--home-dir", "--shell")
# The useradd options a box user may be made with (no --non-unique, no --groups, no --system).
_USERADD_OPTS = _VALUE_OPTS + ("--create-home", "--no-create-home")


def _users(runs) -> tuple:
    """(useradd entries as (name, uid, gid, home), groupadd entries as (name, gid)) across every RUN."""
    users, groups = [], []
    for args in runs:
        for cmd in re.split(r"\s*&&\s*", args):
            toks = cmd.split()
            if not toks:
                continue
            if toks[0] in ("useradd", "groupadd"):
                opts, j = {}, 1
                while j < len(toks) - 1:
                    if toks[j] in _VALUE_OPTS:
                        opts[toks[j]] = toks[j + 1] if j + 1 < len(toks) - 1 else None
                        j += 2
                    else:
                        opts[toks[j]] = True
                        j += 1
                if toks[0] == "useradd":
                    users.append((toks[-1], opts.get("--uid"), opts.get("--gid"), opts.get("--home-dir"),
                                  tuple(sorted(o for o in opts if o not in _USERADD_OPTS))))
                else:
                    groups.append((toks[-1], opts.get("--gid")))
    return users, groups


def check_dockerfile(text: str, lock) -> list:
    """Every way `text` departs from the rules for `lock`'s image ([] when it keeps all of them)."""
    validate(lock)
    image = lock["image"]
    try:
        ins = parse_dockerfile(text)
    except DockerfileError as e:
        return [str(e)]
    out = []
    kw = [i.keyword for i in ins]
    for i in ins:
        if i.keyword not in ALLOWED_INSTRUCTIONS:
            out.append(f"line {i.line}: {i.keyword} is not allowed in a box image")
    # 1. The base, by digest, from the lock's build argument only.
    if len(ins) < 2 or (ins[0].keyword, ins[0].args) != ("ARG", "BASE") or (ins[1].keyword, ins[1].args) != (
            "FROM", "${BASE}"):
        out.append("the file must open with ARG BASE then FROM ${BASE}")
    if kw.count("FROM") != 1:
        out.append("exactly one FROM")
    args = [i.args for i in ins if i.keyword == "ARG"]
    if sorted(args) != sorted(arg_names(lock)) or len(set(args)) != len(args):
        out.append(f"ARG names {args} are not exactly the lock's build arguments {list(arg_names(lock))}")
    # Labels: one key per LABEL, each the value of its own build argument.
    labels = {}
    for i in ins:
        if i.keyword == "LABEL":
            m = re.fullmatch(r'([a-z0-9.]+)="\$\{([A-Z_]+)\}"', i.args)
            if not m or m.group(1) in labels:
                out.append(f"line {i.line}: LABEL must be one key=\"${{ARG}}\", each key once")
                continue
            labels[m.group(1)] = m.group(2)
    if labels != {k: LABEL_ARGS[k] for k in label_keys(lock)}:
        out.append(f"labels {labels} are not exactly {list(label_keys(lock))} from their build arguments")
    # ENV: exactly the image's own lines.
    envs = {}
    for i in ins:
        if i.keyword == "ENV":
            m = re.fullmatch(r"([A-Z_][A-Z0-9_]*)=(\S+)", i.args)
            if not m or m.group(1) in envs:
                out.append(f"line {i.line}: ENV must be one NAME=value, each name once")
                continue
            envs[m.group(1)] = m.group(2)
    if envs != ENVS[image]:
        out.append(f"ENV {envs} is not exactly {ENVS[image]}")
    # The entrypoint is reset; nothing is added from outside, and nothing of the study is copied into a take image.
    entry = [i.args for i in ins if i.keyword == "ENTRYPOINT"]
    if entry != ["[]"]:
        out.append("exactly one ENTRYPOINT [] (the base's entrypoint reset)")
    copies = [i.args for i in ins if i.keyword == "COPY"]
    if image == SIDECAR_IMAGE:
        if copies != [SIDECAR_COPY]:
            out.append(f"the sidecar image copies exactly {SIDECAR_COPY!r}")
    elif copies:
        out.append("no COPY in this image")
    # The RUN lines are a closed sequence (expected_runs): nothing else can run at build, so no deny list of words,
    # setuid modes or install spellings is kept beside it (fold 3, W4A1-7: each was dead under the sequence).
    runs = [normalized(i.args) for i in ins if i.keyword == "RUN"]
    if runs != expected_runs(lock):
        out.append("the RUN lines are not exactly the closed sequence for this image (image_lock.expected_runs)")
    installs = [r for r in runs if "apt-get install" in r]
    if len(installs) != 1:
        out.append("exactly one apt-get install line")
    else:
        if "--no-install-recommends" not in installs[0].split():
            out.append("apt-get install without --no-install-recommends")
        pkgs = _apt_packages(installs[0])
        for p in forbidden(pkgs):
            out.append(f"forbidden package {p!r}")
        want = [SQUID_PACKAGE] if image == EGRESS_IMAGE else list(PACKAGES)
        if pkgs != want:
            out.append(f"packages {pkgs} are not exactly {want}")
    npm = [r for r in runs if re.search(r"\bnpm\b", r) and "install" in r.split()]
    if image in TAKE_IMAGES:
        package = lock["harness"]["package"]
        want_install = NPM_INSTALL.format(package=package)
        want_check = VERSION_CHECK.format(package=package)
        if npm != [want_install]:
            out.append(f"the harness install must be exactly one RUN {want_install}")
        at = runs.index(want_install) if want_install in runs else None
        if at is None or want_check not in runs[at + 1:]:
            out.append("a RUN after the install must check the installed version equals HARNESS_VERSION")
    elif npm:
        out.append("no harness is installed in this image")
    if image in TAKE_IMAGES or image == SIDECAR_IMAGE:
        try:
            common_block(text)
        except DockerfileError as e:
            out.append(str(e))
        if PYTHON_CHECK not in runs:
            out.append("a RUN must check python3 reports exactly PYTHON_VERSION")
        if GIT_SAFE not in runs:
            out.append("git must accept the run tree's ownership (safe.directory '*')")
        users, groups = _users(runs)
        want_users = [(lock["users"][r]["name"], str(lock["users"][r]["uid"]), str(lock["users"][r]["gid"]))
                      for r in ("agent", "watcher")]
        if [u[:3] for u in users] != want_users:
            out.append(f"useradd entries {[u[:3] for u in users]} are not exactly the lock's {want_users}")
        if [g for g in groups] != [(n, gid) for n, _, gid in want_users]:
            out.append(f"groupadd entries {groups} are not exactly the lock's users' groups")
        if users and users[0][3] != f"/home/{lock['users']['agent']['name']}":
            out.append("the agent's home must be /home/<its name>")
        for u in users:
            if u[4]:
                out.append(f"useradd {u[0]} uses options outside the closed set: {list(u[4])}")
        users_at = [i for i in ins if i.keyword == "USER"]
        if not users_at or ins[-1].keyword != "USER" or ins[-1].args != LAST_USER[image] or len(users_at) != 1:
            out.append(f"exactly one USER, last, and it is {LAST_USER[image]}")
    else:
        if lock["python"] is None and any("PYTHON_VERSION" in r for r in runs):
            out.append("a Python check in an image whose lock has no python")
        if [i for i in ins if i.keyword == "USER"]:
            out.append("the egress image sets no USER (run_take names squid's user)")
    return out


def shared_base_problems(locks) -> list:
    """The take locks and the sidecar lock must name one shared base (PENDING alike, or one digest)."""
    bases = {lock["image"]: lock["base"] for lock in locks
             if lock["image"] in TAKE_IMAGES + (SIDECAR_IMAGE,)}
    if set(bases) != set(TAKE_IMAGES + (SIDECAR_IMAGE,)):
        return [f"the shared-base check needs every take lock and the sidecar lock, got {sorted(bases)}"]
    if len(set(bases.values())) != 1:
        return [f"the take and sidecar images do not share one base: {bases}"]
    return []
