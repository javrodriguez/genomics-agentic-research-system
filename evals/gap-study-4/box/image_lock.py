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

This module constructs argv lists only; it never runs one, and it imports no process module.
Standard library only.
"""

from __future__ import annotations

import json
import os
import re

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

# Nullability by image: "required" never null, "null" always null, "optional" null or a value.
REQUIRED, NULL, OPTIONAL = "required", "null", "optional"
NULLABLE = {
    "take-a": {"harness": REQUIRED, "python": REQUIRED, "users": REQUIRED},
    "take-o": {"harness": REQUIRED, "python": REQUIRED, "users": REQUIRED},
    "take-g": {"harness": REQUIRED, "python": REQUIRED, "users": REQUIRED},
    SIDECAR_IMAGE: {"harness": NULL, "python": REQUIRED, "users": REQUIRED},
    EGRESS_IMAGE: {"harness": NULL, "python": OPTIONAL, "users": NULL},
}

KEYS = ("schema", "image", "dockerfile", "base", "harness", "python", "image_id", "users", "pending")
# Keys only some images carry: the egress lock, and only it, carries `squid`.
EXTRA_KEYS = {EGRESS_IMAGE: ("squid",)}

# Every field that may hold PENDING, as the `pending` map names it.
PENDABLE = ("base", "harness.version", "python", "image_id", "squid")

BASE_RE = re.compile(r"(?P<name>[a-z0-9][a-z0-9._/:-]*)@(?P<digest>sha256:[0-9a-f]{64})")
VERSION_RE = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+")
# The in-container floor is Python 3.11 (interface 17).
PYTHON_RE = re.compile(r"3\.(1[1-9]|[2-9][0-9])\.[0-9]+")
IMAGE_ID_RE = re.compile(r"sha256:[0-9a-f]{64}")
SQUID_RE = re.compile(r"[0-9][A-Za-z0-9.+~:-]*")
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
    want = set(KEYS) | set(EXTRA_KEYS.get(image, ()))
    for k in sorted(want - set(lock)):
        out.append(f"missing key {k!r}")
    for k in sorted(set(lock) - want):
        out.append(f"unknown key {k!r}")
    if out:
        return out
    if not _is_int(lock["schema"]) or lock["schema"] != SCHEMA:
        out.append(f"schema: must be {SCHEMA}")
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
        if v is None:
            continue
        if field == "harness":
            if not isinstance(v, dict) or sorted(v) != ["package", "version"]:
                out.append("harness: must hold exactly package and version")
            else:
                _value(v["package"], PACKAGE_RE, "harness.package", out, pendable=False)
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
    """The `docker build` argv for `lock`'s image (constructed, never run); refuses while a build input is PENDING."""
    args = build_args(lock)
    if not isinstance(context, str) or not os.path.isabs(context):
        raise ValueError("context must be an absolute path")
    argv = [CLIENT, "build", "--pull=false", "--file", os.path.join(BOX_DIR, lock["dockerfile"])]
    for k, v in args.items():
        argv += ["--build-arg", f"{k}={v}"]
    for k, v in expected_labels(lock).items():
        argv += ["--label", f"{k}={v}"]
    argv.append(context)
    return argv
