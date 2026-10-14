#!/usr/bin/env python3
"""Live harness: regrade a pending vendor walk once its native-session reader is registered.

    python3 evals/gap-study-4/walk_regrade.py --walk <id>      write rehearsals/<id>/regrade.json (refuses if present)
    commit_regrade(<id>, secrets=..., rules_scanner=...)        scan and commit exactly that file (REGRADE_SUBJECT),
                                                                with the walk runner's own secrets and rules scanner
    python3 evals/gap-study-4/walk_regrade.py --check          every committed regrade.json re-derives to its bytes

Registration review finding 2 (glitch-06, 14 Oct 2026). A walk committed while its native cross-check was pending
(pending_walk.py) keeps its own commit and records. After a reader is registered, the cross-check and the grade are
re-derived deterministically from that walk's COMMITTED bytes (git show HEAD, never the working tree): no new take, no
container, no model. The result is a new record beside the walk's own, rehearsals/<walk>/regrade.json, which
supersedes its pending grade.json and is committed alone, under its own subject, by commit_regrade.

regrade_doc(walk) refuses (RegradeRefused) unless the walk is registered, its committed grade.json is the pending
document, its harness has a regrade road (Gemini; Codex comes with its registration slice) and a reader is
registered (production_readers, or `readers` in tests). The document:
  {"schema": 1, "walk", "walk_commit": the commit that added its driver ledger, "supersedes": "grade.json",
   "cross_check": drive.gemini_cross_check over the committed snapshots and streams, the one shared join,
   "graded", and either "row" and "grade" (run.walk_row and run.grade_walk_folder, or `grade` in tests) when the
   cross-check agreed, or "why" when it refused}.
A grader that raises refuses the regrade: no partial record is written. The checker's reading and route are not
re-derived here (they need the design view and its constants); check.json keeps saying the checker never ran.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import mode_binding  # noqa: E402
import native_reader_registration as nrr  # noqa: E402
import pending_walk  # noqa: E402
import walk_register  # noqa: E402

REGRADE_FILE = "regrade.json"
REGRADE_SUBJECT = "Regrade one pending walk; never counted"
REGRADE_HARNESSES = ("gemini",)


class RegradeRefused(ValueError):
    """The walk cannot be regraded (or its regrade committed) from its committed bytes."""


def _walk_rel(prefix: str, walk: str) -> str:
    return nrr._rel(prefix, f"{mode_binding.WALKS_DIR}/{walk}")


def _repo(study: Path):
    root, prefix = nrr._repo(Path(study))
    if root is None:
        raise RegradeRefused("the study is not in a git repository: a regrade reads the committed tree")
    return root, prefix


def walk_commit(root: Path, walk_rel: str) -> str:
    """The commit that added the walk's driver ledger (its WalkRepo commit)."""
    got = nrr._git(root, "log", "--diff-filter=A", "--format=%H", "HEAD", "--", f"{walk_rel}/driver-ledger.json")
    commits = got.splitlines()
    if len(commits) != 1:
        raise RegradeRefused(f"{walk_rel}/driver-ledger.json was added by {len(commits)} commits, not one")
    return commits[0]


def regrade_doc(walk: str, study: Path = HERE, *, readers=None, grade=None) -> dict:
    import drive
    import run as run_mod
    study = Path(study)
    if not (isinstance(walk, str) and walk_register.WALK_ID.fullmatch(walk)):
        raise RegradeRefused(f"{walk!r} is not a walk id")
    root, prefix = _repo(study)
    walk_rel = _walk_rel(prefix, walk)
    register_rel = nrr._rel(prefix, f"{mode_binding.WALKS_DIR}/{walk_register.REGISTER_NAME}")
    try:
        register = json.loads(nrr._show(root, register_rel), object_pairs_hook=walk_register.no_duplicate_keys)
        entries = [e for e in register["walks"] if isinstance(e, dict) and e.get("walk") == walk]
    except (ValueError, KeyError, TypeError, walk_register.DuplicateKey, nrr.RegistrationRefused) as e:
        raise RegradeRefused(f"the committed rehearsals register cannot be read: {e}") from None
    if len(entries) != 1:
        raise RegradeRefused(f"walk {walk!r} is not registered once in the committed register")
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp) / walk
        try:
            nrr._materialize(root, walk_rel, base)
        except nrr.RegistrationRefused as e:
            raise RegradeRefused(str(e)) from None
        try:
            ledger = json.loads((base / drive.LEDGER_FILE).read_bytes())
            stored = json.loads((base / drive.WALK_GRADE).read_bytes())
        except (OSError, ValueError) as e:
            raise RegradeRefused(f"the committed walk's ledger or grade cannot be read: {e}") from None
        if stored != pending_walk.status(ledger):
            raise RegradeRefused("the committed walk is not a pending walk: its grade.json is not the pending document")
        harness = (ledger.get("agent") or {}).get("harness")
        if harness not in REGRADE_HARNESSES:
            raise RegradeRefused(f"no regrade road for harness {harness!r} yet")
        readers = nrr.production_readers(study) if readers is None else readers
        cross = drive.gemini_cross_check(base, list(ledger.get("native_snapshots") or []),
                                         len(ledger.get("streams") or []), readers=readers)
        if cross["status"] == "pending":
            raise RegradeRefused(f"no registered reader: {cross['why']}")
        doc = {"schema": 1, "walk": walk, "walk_commit": walk_commit(root, walk_rel), "supersedes": drive.WALK_GRADE,
               "cross_check": cross}
        if cross["status"] != "agreed":
            return dict(doc, graded=False, why=f"not graded, because the native cross-check refused: {cross['why']}")
        row = run_mod.walk_row(entries[0], ledger)
        try:
            got = (run_mod.grade_walk_folder if grade is None else grade)(row, base)
        except Exception as e:  # noqa: BLE001 - a grader that cannot grade the walk refuses the whole regrade
            raise RegradeRefused(f"the grader refused the walk: {type(e).__name__}: {e}") from None
        return dict(doc, graded=True, row=row, grade=got)


def regrade_bytes(doc: dict) -> bytes:
    return (json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def write_regrade(walk: str, study: Path = HERE, **kw) -> Path:
    path = Path(study) / mode_binding.WALKS_DIR / walk / REGRADE_FILE
    if os.path.lexists(path):
        raise RegradeRefused(f"{path} exists: a regrade is written once; a later one needs its own ruling")
    data = regrade_bytes(regrade_doc(walk, study, **kw))
    path.write_bytes(data)
    return path


def commit_regrade(walk: str, study: Path = HERE, *, secrets, rules_scanner, holdout_matcher=None) -> str:
    """Scan the walk's regrade.json (box/scan_record, kind ledger, as WalkRepo scans a walk's ledgers) and commit it
    alone under REGRADE_SUBJECT. Refuses when anything else is staged, the scan refuses, or the staged blob is not the
    scanned bytes."""
    import takes as takes_mod
    from box import scan_record
    study = Path(study)
    root, prefix = _repo(study)
    rel = f"{_walk_rel(prefix, walk)}/{REGRADE_FILE}"
    path = root / rel
    if path.is_symlink() or not path.is_file():
        raise RegradeRefused(f"{rel} is not a regular file")
    if nrr._in_head(root, rel):
        raise RegradeRefused(f"{rel} is already committed")
    if nrr._git(root, "diff", "--cached", "--name-only"):
        raise RegradeRefused("the index already holds staged changes; a regrade is committed alone")
    takes_mod.require_commit_identity(root)
    scan = scan_record.scan([(str(path), "ledger")], list(secrets()), rules_scanner=rules_scanner,
                            holdout_matcher=holdout_matcher)
    if not scan_record.passed(scan):
        raise RegradeRefused("the commit scan refused the regrade: " + "; ".join(r["why"] for r in scan["refused"]))
    nrr._git(root, "add", "--", rel)
    staged = nrr._git(root, "diff", "--cached", "--name-only").splitlines()
    blob = nrr._git(root, "show", f":{rel}", binary=True)
    after = {r["path"]: r["sha256_after"] for r in scan["files"]}
    if staged != [rel] or after.get(str(path)) != hashlib.sha256(blob).hexdigest():
        nrr._git(root, "reset", "-q", "--", rel)
        raise RegradeRefused(f"the staged regrade is not exactly the scanned {rel}: {staged}")
    with tempfile.NamedTemporaryFile("w", suffix=".msg", delete=False) as fh:
        fh.write(REGRADE_SUBJECT + "\n")
        msg = fh.name
    try:
        nrr._git(root, "commit", "-q", "-F", msg)
    finally:
        os.unlink(msg)
    return nrr._git(root, "rev-parse", "HEAD")


def regrade_problems(study: Path = HERE, *, readers=None, grade=None) -> list:
    """Every committed regrade.json must re-derive to its exact bytes."""
    study = Path(study)
    root, prefix = nrr._repo(study)
    if root is None:
        return []
    walks = nrr._rel(prefix, mode_binding.WALKS_DIR)
    listed = nrr._git(root, "ls-tree", "-r", "--name-only", "HEAD", "--", walks + "/").splitlines()
    out = []
    for rel in listed:
        parts = rel[len(walks) + 1:].split("/")
        if len(parts) != 2 or parts[1] != REGRADE_FILE:
            continue
        try:
            again = regrade_bytes(regrade_doc(parts[0], study, readers=readers, grade=grade))
        except RegradeRefused as e:
            out.append(f"walk {parts[0]!r}: its regrade cannot be re-derived: {e}")
            continue
        if again != nrr._show(root, rel):
            out.append(f"walk {parts[0]!r}: {REGRADE_FILE} differs from re-deriving it")
    return out


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="walk_regrade.py")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--walk")
    g.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    try:
        if a.check:
            bad = regrade_problems()
            for b in bad:
                print(f"walk_regrade: FAIL {b}")
            print("walk_regrade: ok" if not bad else f"walk_regrade: {len(bad)} problem(s)")
            return 1 if bad else 0
        print(f"walk_regrade: wrote {write_regrade(a.walk)}; commit it with commit_regrade (scanned, alone)")
        return 0
    except (RegradeRefused, nrr.RegistrationRefused) as e:
        print(f"walk_regrade: REFUSED {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
