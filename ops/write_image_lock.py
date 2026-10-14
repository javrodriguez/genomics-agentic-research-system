"""The one supported lock writer (glitch-06's lock-writer rulings, 14 Oct 2026).

    write_image_lock.py --repo <repo> --record <committed build-record.json> --lock <box/.../image.lock>
                        --image <take-a|take-o|take-g|sidecar|egress> [--write]

It fills one unfilled (schema-1) image lock into a schema-2 lock, only from a committed build record of an athena
build of a named commit, and refuses, writing nothing, unless:
  - the record is a file tracked in the repository whose working bytes equal HEAD's (committed, unchanged);
  - the record is schema 2 and its source_commit is a 40-hex ancestor of HEAD (git merge-base --is-ancestor);
  - the record holds exactly one row for the image, with exit 0, no label problem and valid image, platform
    manifest and config digests;
  - the lock loads through image_lock.load (closed schema, its own Dockerfile beside it), is schema 1 and is the
    named image's lock;
  - every PENDING build input of the lock is resolved by the row's lock_inputs, and every value the lock already
    holds equals the row's: nothing PENDING may remain, and no input is changed.
Without --write it prints the lock it would write. With --write the lock is replaced atomically, and only if its
bytes are still the bytes read. The record is never a credential; nothing here reads one, pushes or runs a build.
"""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

HEX40 = re.compile(r"[0-9a-f]{40}")
DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
RECORD_SCHEMA = 2
INPUT_FIELDS = ("base", "harness", "python", "users", "squid")


class Refused(ValueError):
    pass


def _need(cond, why):
    if not cond:
        raise Refused(why)


def _git(repo: Path, *args) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, timeout=60,
                          env={"PATH": "/usr/bin:/bin", "GIT_CONFIG_NOSYSTEM": "1", "HOME": str(repo)})


def committed_bytes(repo: Path, path: Path) -> bytes:
    """The file's bytes, refused unless it is tracked and identical to HEAD's blob."""
    rel = path.resolve().relative_to(repo.resolve()).as_posix()
    head = _git(repo, "show", "HEAD:" + rel)
    _need(head.returncode == 0, f"{rel} is not a file committed at HEAD")
    with open(path, "rb") as fh:
        data = fh.read()
    _need(data == head.stdout, f"{rel} differs from its committed bytes")
    return data


def is_ancestor(repo: Path, commit: str) -> bool:
    return _git(repo, "merge-base", "--is-ancestor", commit, "HEAD").returncode == 0


def plan(il, repo: Path, record_path: Path, lock_path: Path, image: str) -> tuple:
    """(the schema-2 lock to write, the lock's bytes as read). Refuses (Refused or image_lock.LockError)."""
    repo = Path(repo)
    record = json.loads(committed_bytes(repo, Path(record_path)))
    _need(isinstance(record, dict) and record.get("schema") == RECORD_SCHEMA, "the build record is not schema 2")
    commit = record.get("source_commit")
    _need(isinstance(commit, str) and HEX40.fullmatch(commit) is not None, "the record's source_commit is not 40 hex")
    _need(is_ancestor(repo, commit), f"the build commit {commit} is not an ancestor of HEAD")
    rows = [r for r in record.get("images", []) if isinstance(r, dict) and r.get("image") == image]
    _need(len(rows) == 1, f"the record holds {len(rows)} rows for {image}, not one")
    row = rows[0]
    _need(row.get("exit") == 0 and type(row.get("exit")) is int, f"{image}'s build did not exit 0")
    _need(row.get("label_problems") == [], f"{image}'s labels did not check clean")
    for k in ("image_id", "manifest_digest", "config_digest"):
        _need(isinstance(row.get(k), str) and DIGEST.fullmatch(row[k]) is not None, f"{image}'s {k} is not a digest")
    inputs = row.get("lock_inputs")
    _need(isinstance(inputs, dict), f"{image}'s row carries no lock_inputs")
    with open(lock_path, "rb") as fh:
        lock_bytes = fh.read()
    lock = il.load(str(lock_path))
    _need(lock["schema"] == il.SCHEMA, "the lock is not the unfilled schema-1 lock")
    _need(lock["image"] == image, f"the lock is {lock['image']}'s, not {image}'s")
    new = copy.deepcopy(lock)
    for field in INPUT_FIELDS:
        if field not in lock:
            _need(field not in inputs, f"{image}'s record names {field}, which its lock does not carry")
            continue
        _need(field in inputs, f"{image}'s record does not resolve {field}")
        have, want = lock[field], inputs[field]
        if field == "harness" and isinstance(have, dict) and isinstance(want, dict):
            _need(have.get("package") == want.get("package"), f"{image}'s harness package differs from the record's")
            if have.get("version") != il.PENDING:
                _need(have.get("version") == want.get("version"), f"{image}'s harness version differs from the record's")
        elif have != il.PENDING:
            _need(have == want, f"{image}'s {field} differs from the record's")
        new[field] = copy.deepcopy(want)
    new.update(schema=il.SCHEMA_2, image_id=row["image_id"], manifest_digest=row["manifest_digest"],
               config_digest=row["config_digest"], source_commit=commit, pending={})
    held = [f for f in il.PENDABLE if f in il._pending_fields(new)]
    _need(not held, f"PENDING not resolved by the evidence: {held}")
    il.validate(new)
    return new, lock_bytes


def write(lock_path: Path, new: dict, read_bytes: bytes) -> None:
    with open(lock_path, "rb") as fh:
        _need(fh.read() == read_bytes, "the lock changed since it was read")
    tmp = Path(str(lock_path) + ".writing")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(new, fh, indent=1, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, lock_path)


def load_image_lock(repo: Path):
    path = Path(repo) / "evals/gap-study-4/box/image_lock.py"
    sys.path.insert(0, str(path.parent.parent))
    spec = importlib.util.spec_from_file_location("box.image_lock", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["box.image_lock"] = mod
    spec.loader.exec_module(mod)
    return mod


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for k in ("repo", "record", "lock", "image"):
        ap.add_argument("--" + k, required=True)
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)
    il = load_image_lock(Path(a.repo))
    try:
        new, read_bytes = plan(il, Path(a.repo), Path(a.record), Path(a.lock), a.image)
    except (Refused, il.LockError, ValueError) as e:
        print(f"write_image_lock: REFUSED: {e}")
        return 1
    if a.write:
        write(Path(a.lock), new, read_bytes)
        print(f"write_image_lock: wrote {a.lock} (schema {new['schema']}, from {new['source_commit']})")
    else:
        print(json.dumps(new, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
