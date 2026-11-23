"""The one supported lock writer (glitch-06's lock-writer rulings, 14 Oct 2026; review LW-1 to LW-6 folded).

    write_image_lock.py --repo <repo> --record <committed build-record.json> --lock <box/.../image.lock>
                        --image <take-a|take-o|take-g|sidecar|egress> [--write]

It fills one unfilled (schema-1) image lock into a schema-2 lock, only from a committed schema-3 build record written
by lane-reports/build-20261014c/build_candidate_images.py, and refuses, writing nothing, unless:
  - the record is a file tracked in the repository whose working bytes equal HEAD's (committed, unchanged);
  - its source_commit is a 40-hex ancestor of HEAD, and the build's checkout was clean before and after it (LW-3);
  - LW-1: every input the build read is recorded (the lock's Dockerfile, each COPY source of HEAD's Dockerfile, and
    the lock-inputs file), and each recorded sha256 equals the sha256 of HEAD's blob at that path, so a build of
    source HEAD no longer holds is refused; the row's lock inputs equal that file's entry for the lock;
  - LW-2: the row's metadata file and build log sit beside the record, committed and unchanged; image_id equals the
    metadata's image index (containerimage.digest and its descriptor); manifest_digest and config_digest equal the
    build log's one `exporting manifest` and one `exporting config` line; the row's argv equals
    image_lock.build_argv(the new lock) with only --iidfile and --metadata-file added (the record's box folder mapped
    to this repository's). Departure from the ruling's wording, measured on athena 14 Oct 03:37 EDT (docker 29.8.1,
    buildx 0.37.1, containerd store): the metadata file carries no containerimage.config.digest, so the config digest
    is bound to the log's `exporting config` line and the metadata binds the index id instead;
  - LW-4: the record names its image store, and manifest_digest differs from config_digest (equal digests are
    what a classic-store inspect would give, never a platform manifest);
  - review 2: each input's git mode and blob at HEAD equal the build commit's (R2-1, and a record's own ls-tree
    entries must equal them); the log's one `exporting manifest list` line is image_id and BuildKit's provenance
    names source_commit and this box folder (R2-2); the record lists no problem (R2-3); HEAD's bytes are read with
    `git cat-file blob`, so a tree is never read as a file (R2-4);
  - the sidecar's baked program hash equals its recorded sidecar.py input;
  - the record holds exactly one row for the image, with exit 0, no label problem and valid digests;
  - the lock loads through image_lock.load (closed schema, its own Dockerfile beside it), is schema 1 and is the
    named image's lock; every PENDING build input is resolved by the row's lock_inputs, every value the lock already
    holds equals the row's, and nothing PENDING remains.
Residual (LW-2, named): a deliberately false record, committed together with a matching false metadata file and
build log, passes here; that is caught by reviewing the record commit, never by this writer.
Without --write it prints the lock it would write. With --write (LW-6) it holds an exclusive flock on the lock's
folder across the compare and the atomic replace, and replaces the lock only if its bytes are still the bytes read.
The record is never a credential; nothing here reads one, pushes or runs a build.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

HEX40 = re.compile(r"[0-9a-f]{40}")
HEX64 = re.compile(r"[0-9a-f]{64}")
DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
RECORD_SCHEMA = 3
INPUT_FIELDS = ("base", "harness", "python", "users", "squid")
LOGGED_MANIFEST = re.compile(r"^#\d+ exporting manifest (sha256:[0-9a-f]{64})(?: |$)", re.MULTILINE)
LOGGED_LIST = re.compile(r"^#\d+ exporting manifest list (sha256:[0-9a-f]{64})(?: |$)", re.MULTILINE)
LOGGED_CONFIG = re.compile(r"^#\d+ exporting config (sha256:[0-9a-f]{64})(?: |$)", re.MULTILINE)
SIDE_FILE = re.compile(r"[a-z0-9-]+\.(metadata\.json|build\.log)")
SIDECAR_PROGRAM_SRC = "sidecar.py"


class Refused(ValueError):
    pass


def _need(cond, why):
    if not cond:
        raise Refused(why)


def _git(repo: Path, *args) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, timeout=60,
                          env={"PATH": "/usr/bin:/bin", "GIT_CONFIG_NOSYSTEM": "1", "HOME": str(repo)})


def head_blob(repo: Path, rel: str) -> bytes:
    """HEAD's blob at `rel` (R2-4: `cat-file blob`, so a tree, a missing path or anything else refuses)."""
    head = _git(repo, "cat-file", "blob", "HEAD:" + rel)
    _need(head.returncode == 0, f"{rel} is not a file committed at HEAD")
    return head.stdout


def tree_entry(repo: Path, rev: str, rel: str) -> list:
    """[mode, blob id] of the one blob at `rel` in `rev`'s tree (R2-1: Docker COPY keeps the mode)."""
    got = _git(repo, "ls-tree", "--full-tree", rev, "--", rel)
    lines = got.stdout.decode("utf-8", "replace").splitlines() if got.returncode == 0 else []
    _need(len(lines) == 1, f"{rel} is not one entry in {rev}'s tree")
    meta, _, path = lines[0].partition("\t")
    mode, kind, oid = (meta.split(" ") + ["", "", ""])[:3]
    _need(kind == "blob" and path == rel, f"{rel} is not a blob in {rev}'s tree")
    return [mode, oid]


def committed_bytes(repo: Path, path: Path) -> bytes:
    """The file's bytes, refused unless it is tracked and identical to HEAD's blob."""
    rel = path.resolve().relative_to(repo.resolve()).as_posix()
    blob = head_blob(repo, rel)
    with open(path, "rb") as fh:
        data = fh.read()
    _need(data == blob, f"{rel} differs from its committed bytes")
    return data


def is_ancestor(repo: Path, commit: str) -> bool:
    return _git(repo, "merge-base", "--is-ancestor", commit, "HEAD").returncode == 0


def canonical(doc) -> bytes:
    return json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()


def copy_sources(il, text: str) -> list:
    """Every COPY source of a Dockerfile, relative to the build context; anything else that reads the context refuses."""
    out = []
    for ins in il.parse_dockerfile(text):
        if ins.keyword in ("COPY", "ADD"):
            words = shlex.split(ins.args)
            _need(ins.keyword == "COPY" and len(words) >= 2 and not any(w.startswith("-") for w in words)
                  and not any(set(w) & set("*?[") or ".." in w.split("/") or w.startswith("/") for w in words[:-1]),
                  f"line {ins.line}: a context read this writer does not bind: {ins.args!r}")
            out += words[:-1]
    return out


def required_inputs(il, repo: Path, lock: dict) -> tuple:
    """(the repo-relative build inputs HEAD's source says this image reads, the sidecar program's path or None)."""
    box = Path(il.BOX_DIR).resolve().relative_to(Path(repo).resolve()).as_posix()
    dockerfile = f"{box}/{lock['dockerfile']}"
    want = [dockerfile] + [f"{box}/{src}" for src in copy_sources(il, head_blob(repo, dockerfile).decode("utf-8"))]
    program = f"{box}/{SIDECAR_PROGRAM_SRC}" if lock["image"] == il.SIDECAR_IMAGE else None
    return want, program


def check_inputs(il, repo: Path, record: dict, row: dict, lock: dict, lock_path: Path, commit: str) -> None:
    """LW-1: every input the build read equals HEAD's blob, and the lock inputs are the committed file's."""
    inputs = row.get("inputs")
    _need(isinstance(inputs, dict) and inputs, f"{lock['image']}'s row records no build inputs")
    want, program = required_inputs(il, repo, lock)
    _need(sorted(inputs) == sorted(want), f"{lock['image']}'s recorded inputs {sorted(inputs)} are not the inputs "
                                          f"HEAD's Dockerfile reads {sorted(want)}")
    if program is not None:
        _need(program in want, f"the sidecar's Dockerfile does not copy {program}")
    for rel, sha in sorted(inputs.items()):
        _need(isinstance(sha, str) and HEX64.fullmatch(sha) is not None, f"{rel}'s recorded sha256 is not 64 hex")
        _need(hashlib.sha256(head_blob(repo, rel)).hexdigest() == sha,
              f"{rel} at HEAD is not the {rel} the image was built from")
    # R2-1: each input's git mode and blob at HEAD are the build commit's (the build ran in a clean checkout of it);
    # a record that carries its own ls-tree entries (script c from review 2 on) must name exactly those.
    built = {rel: tree_entry(repo, commit, rel) for rel in sorted(inputs)}
    for rel in sorted(inputs):
        _need(tree_entry(repo, "HEAD", rel) == built[rel], f"{rel}'s mode or blob at HEAD is not the build commit's")
    if "tree_entries" in row:
        _need(row["tree_entries"] == built, f"{lock['image']}'s recorded tree entries are not the build commit's")
    src = record.get("lock_inputs_source")
    _need(isinstance(src, dict) and set(src) == {"path", "sha256"} and isinstance(src["path"], str),
          "the record names no lock-inputs file")
    blob = head_blob(repo, src["path"])
    _need(hashlib.sha256(blob).hexdigest() == src["sha256"],
          f"{src['path']} at HEAD is not the lock-inputs file the build read")
    box_parent = Path(il.BOX_DIR).resolve().parent
    lock_rel = Path(lock_path).resolve().relative_to(box_parent).as_posix()
    _need(row.get("lock") == lock_rel, f"the row is the build of {row.get('lock')!r}, not of {lock_rel}")
    entry = json.loads(blob).get("locks", {}).get(lock_rel, {}).get("content")
    _need(isinstance(entry, dict), f"{src['path']} holds no entry for {lock_rel}")
    _need(row.get("lock_inputs") == {k: entry[k] for k in INPUT_FIELDS if k in entry},
          f"{lock['image']}'s lock_inputs are not {src['path']}'s")
    _need(row.get("lock_inputs_sha256") == hashlib.sha256(canonical(row["lock_inputs"])).hexdigest(),
          f"{lock['image']}'s lock_inputs_sha256 is not its lock_inputs'")
    if program is not None:
        _need(row.get("baked_sidecar_sha256") == inputs[program],
              "the sidecar image's baked program is not its recorded sidecar.py")


def check_build(il, repo: Path, record_path: Path, record: dict, row: dict, new: dict) -> None:
    """LW-2: the digests bound to the build's own metadata file and log; the argv is build_argv's plus two files."""
    image = new["image"]
    side = {}
    for key in ("metadata_file", "build_log"):
        name = row.get(key)
        _need(isinstance(name, str) and SIDE_FILE.fullmatch(name) is not None and name.startswith(image + "."),
              f"{image}'s {key} is not a file named for it beside the record")
        side[key] = committed_bytes(repo, Path(record_path).parent / name)
    meta = json.loads(side["metadata_file"])
    desc = meta.get("containerimage.descriptor") if isinstance(meta, dict) else None
    _need(isinstance(meta, dict) and meta.get("containerimage.digest") == row["image_id"]
          and isinstance(desc, dict) and desc.get("digest") == row["image_id"],
          f"{image}'s image_id is not its metadata file's image index")
    log = side["build_log"].decode("utf-8", "replace")
    logged = sorted(set(LOGGED_MANIFEST.findall(log)))
    _need(logged == [row["manifest_digest"]], f"{image}'s build log exported manifest {logged}, not "
                                              f"{row['manifest_digest']}")
    configs = sorted(set(LOGGED_CONFIG.findall(log)))
    _need(configs == [row["config_digest"]], f"{image}'s config_digest is not its build log's one exported config "
                                             f"{configs}")
    lists = sorted(set(LOGGED_LIST.findall(log)))
    _need(lists == [row["image_id"]], f"{image}'s build log exported manifest list {lists}, not its image_id")
    _need(row["manifest_digest"] != row["config_digest"],
          f"{image}'s manifest digest equals its config digest: a classic-store reading, not a platform manifest")
    rbox, checkout = record.get("box_dir"), record.get("checkout")
    rel_box = Path(il.BOX_DIR).resolve().relative_to(Path(repo).resolve()).as_posix()
    # R2-2: BuildKit's own provenance names the revision and the context folder it built.
    try:
        args = meta["buildx.build.provenance"]["invocation"]["parameters"]["root"]["request"]["args"]
    except (KeyError, TypeError):
        args = None
    _need(isinstance(args, dict) and args.get("vcs:revision") == record["source_commit"]
          and args.get("vcs:localdir:context") == rel_box,
          f"{image}'s provenance is not the build of {record['source_commit']} from {rel_box}")
    _need(isinstance(rbox, str) and isinstance(checkout, str) and os.path.isabs(checkout)
          and rbox == checkout.rstrip("/") + "/" + rel_box, "the record's box folder is not its checkout's box folder")
    argv = row.get("argv")
    _need(isinstance(argv, list) and all(isinstance(a, str) for a in argv), f"{image}'s row records no argv")
    mapped = [il.BOX_DIR + a[len(rbox):] if a == rbox or a.startswith(rbox + "/") else a for a in argv]
    want = il.build_argv(new, context=il.BOX_DIR)
    _need(len(mapped) == len(want) + 4 and mapped[-1] == want[-1] and mapped[:len(want) - 1] == want[:-1]
          and mapped[len(want) - 1] == "--iidfile" and mapped[len(want) + 1] == "--metadata-file",
          f"{image}'s argv is not image_lock.build_argv of the new lock plus --iidfile and --metadata-file")
    iid, md = mapped[len(want)], mapped[len(want) + 2]
    _need(os.path.isabs(iid) and os.path.isabs(md) and os.path.basename(md) == row["metadata_file"],
          f"{image}'s --metadata-file is not the committed {row['metadata_file']}")


def plan(il, repo: Path, record_path: Path, lock_path: Path, image: str, *, unfilled: dict | None = None) -> tuple:
    """(the schema-2 lock to write, the lock's bytes as read). Refuses (Refused or image_lock.LockError).

    `unfilled` is only for rederive(): the committed lock re-made unfilled in memory, planned at its own path; its
    bytes-as-read are then None and nothing may be written from it."""
    repo = Path(repo)
    record = json.loads(committed_bytes(repo, Path(record_path)))
    _need(isinstance(record, dict) and record.get("schema") == RECORD_SCHEMA,
          f"the build record is not schema {RECORD_SCHEMA}")
    commit = record.get("source_commit")
    _need(isinstance(commit, str) and HEX40.fullmatch(commit) is not None, "the record's source_commit is not 40 hex")
    _need(is_ancestor(repo, commit), f"the build commit {commit} is not an ancestor of HEAD")
    _need(record.get("clean_after") is True, "the record does not show its checkout clean after the builds")
    _need(record.get("problems") == [], "the record lists problems, or names none")   # R2-3
    store = record.get("store")
    _need(isinstance(store, dict) and isinstance(store.get("driver"), str) and store["driver"]
          and isinstance(store.get("driver_status"), list), "the record does not name its image store")
    rows = [r for r in record.get("images", []) if isinstance(r, dict) and r.get("image") == image]
    _need(len(rows) == 1, f"the record holds {len(rows)} rows for {image}, not one")
    row = rows[0]
    _need(row.get("exit") == 0 and type(row.get("exit")) is int, f"{image}'s build did not exit 0")
    _need(row.get("label_problems") == [], f"{image}'s labels did not check clean")
    for k in ("image_id", "manifest_digest", "config_digest"):
        _need(isinstance(row.get(k), str) and DIGEST.fullmatch(row[k]) is not None, f"{image}'s {k} is not a digest")
    inputs = row.get("lock_inputs")
    _need(isinstance(inputs, dict), f"{image}'s row carries no lock_inputs")
    if unfilled is None:
        with open(lock_path, "rb") as fh:
            lock_bytes = fh.read()
        lock = il.load(str(lock_path))
    else:
        lock_bytes, lock = None, il.validate(copy.deepcopy(unfilled))
    _need(lock["schema"] == il.SCHEMA, "the lock is not the unfilled schema-1 lock")
    _need(lock["image"] == image, f"the lock is {lock['image']}'s, not {image}'s")
    check_inputs(il, repo, record, row, lock, Path(lock_path), commit)
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
    check_build(il, repo, Path(record_path), record, row, new)
    return new, lock_bytes


def lock_text(new: dict) -> str:
    """A written lock's exact text (write() and the dry run print the same bytes)."""
    return json.dumps(new, indent=1, sort_keys=True) + "\n"


def rederive(il, repo: Path, record_path: Path, lock_path: Path, image: str) -> bytes:
    """The bytes a committed lock must hold (glitch-06's ruling on the post-write guard, 14 Oct 2026): the committed
    lock must be the named image's schema-2 lock; its schema-2 fields are removed and image_id is PENDING again, and
    plan() over the committed build record re-derives it. A hand-edited pin, a pin from another record or row, or a
    stale pin (an input changed at HEAD) differs from these bytes or refuses."""
    lock = il.load(str(lock_path))
    _need(lock["schema"] == il.SCHEMA_2 and lock["image"] == image,
          f"{lock_path} is not {image}'s filled schema-{il.SCHEMA_2} lock")
    unfilled = {k: v for k, v in lock.items() if k not in il.SCHEMA_2_KEYS}
    unfilled.update(schema=il.SCHEMA, image_id=il.PENDING, pending={"image_id": "re-derived by rederive()"})
    new, _ = plan(il, repo, record_path, lock_path, image, unfilled=unfilled)
    return lock_text(new).encode()


def write(lock_path: Path, new: dict, read_bytes: bytes) -> None:
    """Compare and replace under an exclusive flock on the lock's folder (LW-6); refuses if another writer holds it."""
    try:
        import fcntl
    except ImportError:
        raise Refused("no flock on this system: the writer runs on the Mac or athena only") from None
    dfd = os.open(os.path.dirname(os.path.abspath(lock_path)), os.O_RDONLY)
    try:
        try:
            fcntl.flock(dfd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Refused("another writer holds the lock's folder") from None
        _need(read_bytes is not None, "a re-derived plan is never written")
        with open(lock_path, "rb") as fh:
            _need(fh.read() == read_bytes, "the lock changed since it was read")
        tmp = Path(str(lock_path) + ".writing")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(lock_text(new))
        os.replace(tmp, lock_path)
    finally:
        os.close(dfd)   # closing the descriptor releases the flock


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
        try:
            write(Path(a.lock), new, read_bytes)
        except Refused as e:
            print(f"write_image_lock: REFUSED: {e}")
            return 1
        print(f"write_image_lock: wrote {a.lock} (schema {new['schema']}, from {new['source_commit']})")
    else:
        print(lock_text(new), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
