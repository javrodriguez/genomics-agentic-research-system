#!/usr/bin/env python3
"""What this study copied from round 3, from which commit, and what it changed -- assembled from one fragment per lane.

    python3 evals/gap-study-4/copy_manifest.py --check     assemble COPIED.d/*.json, re-derive every entry; exit 1 on any problem
    python3 evals/gap-study-4/copy_manifest.py --derive    print the assembled record (what the freeze writes as COPIED.json)

ROUND 4'S SHAPE. Round 3's manifest compared one committed COPIED.json with what the files derived, so every
lane that added a file would have rewritten that same file. Here each build lane writes its own fragment,
COPIED.d/<lane id>.json:

    {"lane": "<lane id>", "files": [{"path": "<path under evals/gap-study-4/>",
                                      "status": "identical" | "edited" | "new",
                                      "source": "<repo path at the source commit, for identical and edited>",
                                      "reason": "<required for edited and new>"}]}

`--check` assembles the fragments and compares with NOTHING committed: during the build COPIED.json does not
exist, and the freeze writes it once from derive(). What --check refuses:

  - a fragment that is not that shape, or whose `lane` is not its own file name;
  - a path claimed by two fragments (or twice by one);
  - a file under this folder that no fragment claims, or a claimed file that does not exist;
  - an `identical` copy whose bytes differ from its source blob at the source commit, or that carries a reason;
  - an `edited` copy that is byte-identical to its source, or that carries no reason;
  - a `new` file that carries a source or no reason, or that is byte-identical to the round 3 file at the same
    path (that is a copy and says so);
  - an edit to any copied fixture builder (UNEDITABLE): the fixtures round 3 ran are rebuilt exactly as it ran
    them, and new fixtures are new files;
  - any change to the frozen rounds, the shared graders and fixtures, the shared transcript parser or the
    pre-study since BASE_COMMIT, in a commit or in the working tree.

Round 3's uneditable list (check_take.py, the graders, the label reader, lint_language.py, commit_msg.py) is
NOT carried: round 4 edits its checker and writes new graders, and the copied list would refuse both.

Every source is read from round 3's done commit with `git show`, never from a working tree.

No model, no network, stdlib only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
FRAGMENTS = HERE / "COPIED.d"
sys.path.insert(0, str(HERE))

import study  # noqa: E402

# Round 3's done commit: every copy is read from here.
SOURCE_COMMIT = "e2979b31"
SOURCE_DIR = "evals/gap-study-3"
# The commit round 4 was cut from. Everything below is unchanged since it, so nothing here can have been edited there.
BASE_COMMIT = "68ec902f63bfbe4a18d07e0f564847531898ff95"
PINNED_UNCHANGED = ("evals/gap-study", "evals/gap-study-2", "evals/gap-study-3", "evals/graders",
                    "evals/fixtures", "evals/transcript.py", "evals/haiku-prestudy")

STATUSES = ("identical", "edited", "new")
ENTRY_KEYS = {"path", "status", "source", "reason"}

# The copied fixture builders: uneditable. Each must be claimed, as `identical`, from its round 3 path.
UNEDITABLE = ("fixtures/check_fixture.py", "fixtures/copy_project.py", "fixtures/gen_project.py",
              "fixtures/gen_source.py", "fixtures/symbol_rulings.json")

# Never part of a fragment: caches the interpreter may leave behind.
IGNORED_PARTS = ("__pycache__",)
IGNORED_SUFFIXES = (".pyc",)


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True)


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def source_bytes(src: str) -> bytes | None:
    shown = git("show", f"{SOURCE_COMMIT}:{src}")
    return shown.stdout if shown.returncode == 0 else None


def files_here() -> set[str]:
    """Every file under this folder, on disk or in the index, as a path relative to this folder."""
    out = set()
    for p in HERE.rglob("*"):
        if p.is_file() and not any(part in IGNORED_PARTS for part in p.parts) and p.suffix not in IGNORED_SUFFIXES:
            out.add(p.relative_to(HERE).as_posix())
    listed = git("ls-files", "-z", "--", study.STUDY_REL)
    for name in listed.stdout.decode().split("\0"):
        if name:
            rel = name[len(study.STUDY_REL) + 1:]
            if not any(part in IGNORED_PARTS for part in rel.split("/")) and not rel.endswith(IGNORED_SUFFIXES):
                out.add(rel)
    return out


def load_fragments(folder: Path = FRAGMENTS) -> tuple[list[tuple[str, dict]], list[str]]:
    """(lane, entry) for every entry of every fragment, and the shape problems found reading them."""
    entries, out = [], []
    if not folder.is_dir():
        return entries, [f"no {folder.name}/ folder: no lane has recorded its files"]
    for frag in sorted(folder.glob("*.json")):
        try:
            rec = json.loads(frag.read_text())
        except (OSError, ValueError) as e:
            out.append(f"{frag.name} is not JSON: {e}")
            continue
        if not isinstance(rec, dict) or set(rec) != {"lane", "files"} or not isinstance(rec["files"], list):
            out.append(f"{frag.name} is not {{\"lane\": ..., \"files\": [...]}}")
            continue
        if rec["lane"] != frag.stem:
            out.append(f"{frag.name} names lane {rec['lane']!r}; a fragment's lane is its file name")
        for e in rec["files"]:
            if not isinstance(e, dict) or not {"path", "status"} <= set(e) or not set(e) <= ENTRY_KEYS:
                out.append(f"{frag.name}: entry {e!r} is not {{path, status, source?, reason?}}")
                continue
            entries.append((frag.stem, e))
    return entries, out


def derive(folder: Path = FRAGMENTS) -> dict:
    """The assembled record, with each copy's source blob and both hashes. What the freeze writes as COPIED.json."""
    entries, _ = load_fragments(folder)
    files = []
    for lane, e in sorted(entries, key=lambda le: le[1]["path"]):
        p = HERE / e["path"]
        row = {"path": study.rel(e["path"]), "lane": lane, "status": e["status"],
               "source": e.get("source"), "reason": e.get("reason"),
               "copy_sha256": sha256(p.read_bytes()) if p.is_file() else None}
        if e.get("source"):
            src = source_bytes(e["source"])
            row["source_blob"] = git("rev-parse", f"{SOURCE_COMMIT}:{e['source']}").stdout.decode().strip() or None
            row["source_sha256"] = sha256(src) if src is not None else None
        files.append(row)
    return {"role": "Every file of this study, per build lane: copied from round 3's done commit (identical or edited "
                    "with a reason) or new, assembled from COPIED.d/.",
            "source_commit": git("rev-parse", SOURCE_COMMIT).stdout.decode().strip(),
            "base_commit": BASE_COMMIT, "files": files}


def read_copy(path: str) -> bytes:
    return (HERE / path).read_bytes()


def problems(folder: Path = FRAGMENTS, present: set[str] | None = None, read=read_copy,
             pinned: bool = True) -> list[str]:
    """Every problem with the assembled fragments. `present` and `read` stand in for the folder (tests mutate them)."""
    entries, out = load_fragments(folder)
    present = files_here() if present is None else present
    claimed: dict[str, str] = {}
    for lane, e in entries:
        path, status, src, why = e["path"], e["status"], e.get("source"), e.get("reason")
        if path in claimed:
            out.append(f"{path} is claimed by {claimed[path]} and again by {lane}; a file has one owner")
            continue
        claimed[path] = lane
        if status not in STATUSES:
            out.append(f"{path} ({lane}): status {status!r} is not one of {', '.join(STATUSES)}")
            continue
        if path not in present:
            out.append(f"{path} ({lane}) is claimed but does not exist")
            continue
        copy = read(path)
        if status == "new":
            if src:
                out.append(f"{path} ({lane}) is new and names a source; a copy is identical or edited")
            if not why:
                out.append(f"{path} ({lane}) is new and carries no reason")
            same = source_bytes(f"{SOURCE_DIR}/{path}")
            if same is not None and same == copy:
                out.append(f"{path} ({lane}) is recorded as new but is byte-identical to {SOURCE_DIR}/{path} at "
                           f"{SOURCE_COMMIT}; it is a copy and must say so")
            if path in UNEDITABLE:
                out.append(f"{path} ({lane}) is a copied fixture builder recorded as new")
            continue
        if not src:
            out.append(f"{path} ({lane}) is {status} and names no source")
            continue
        orig = source_bytes(src)
        if orig is None:
            out.append(f"{path} ({lane}): its source {src} does not exist at {SOURCE_COMMIT}")
            continue
        differs = orig != copy
        if status == "identical" and differs:
            out.append(f"{path} ({lane}) differs from {src} at {SOURCE_COMMIT} and has no `edited` entry")
        if status == "identical" and why:
            out.append(f"{path} ({lane}) is identical and carries a reason; a reason is for an edit or a new file")
        if status == "edited" and not differs:
            out.append(f"{path} ({lane}) carries an edit reason but is byte-identical to {src}")
        if status == "edited" and not why:
            out.append(f"{path} ({lane}) differs from {src} and no reason is recorded")
        if path in UNEDITABLE and (differs or status != "identical"):
            out.append(f"{path} ({lane}) is a copied fixture builder and differs from {src}, or is recorded as "
                       f"edited; that is a FAIL, not a manifest entry")
        if path in UNEDITABLE and src != f"{SOURCE_DIR}/{path}":
            out.append(f"{path} ({lane}) is a copied fixture builder whose source is {src}, not {SOURCE_DIR}/{path}")
    for name in sorted(present - set(claimed)):
        out.append(f"{name} is under {study.STUDY_REL}/ and no fragment in {folder.name}/ claims it")
    for name in UNEDITABLE:
        if name not in claimed:
            out.append(f"{name}, a copied fixture builder, is not claimed by any fragment")
    for p in (PINNED_UNCHANGED if pinned else ()):
        if git("diff", "--quiet", BASE_COMMIT, "HEAD", "--", p).returncode != 0:
            out.append(f"{p} has changed since {BASE_COMMIT[:12]}; a frozen round or shared file was edited")
        elif git("diff", "--quiet", BASE_COMMIT, "--", p).returncode != 0:
            out.append(f"{p} differs from {BASE_COMMIT[:12]} in the working tree")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--derive", action="store_true")
    args = ap.parse_args()
    if args.derive:
        print(json.dumps(derive(), indent=2))
        return 0
    if git("cat-file", "-e", f"{SOURCE_COMMIT}^{{commit}}").returncode != 0:
        print(f"FAIL the source commit {SOURCE_COMMIT} is not in this clone (git fetch --unshallow)")
        return 1
    bad = problems()
    for b in bad:
        print(f"FAIL {b}")
    if not bad:
        entries, _ = load_fragments()
        count = {s: sum(e["status"] == s for _, e in entries) for s in STATUSES}
        lanes = sorted({lane for lane, _ in entries})
        print(f"ok: {len(entries)} files from {len(lanes)} fragment(s) ({', '.join(lanes)}): "
              f"{count['identical']} identical and {count['edited']} edited from {SOURCE_DIR} at {SOURCE_COMMIT}, "
              f"{count['new']} new; {len(UNEDITABLE)} fixture builders byte-identical; "
              f"{len(PINNED_UNCHANGED)} frozen paths unchanged since {BASE_COMMIT[:12]}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
