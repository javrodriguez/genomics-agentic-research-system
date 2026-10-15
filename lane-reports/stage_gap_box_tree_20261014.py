"""Dated re-export of the approved no-history tree (14 Oct 2026); supersedes nothing in place.

The 13 Oct export in the macOS temporary folder was cleaned away by the system. This script
rebuilds it with the same existing writer (walk_builders.build_run_tree -> drive.clean_run_tree)
at the same pin and exclusions, into the durable folder EXPORT_ROOT, and writes a NEW dated
manifest beside the old one. stage_gap_box_tree.py and its manifest are not touched.

It refuses unless the new export matches the old manifest row for row on every non-.git file
(path, bytes, mode, sha256), on the 156-file count and on the 1,304,859-byte total: the owner's
approval binds those exact bytes. It also keeps the old script's proposal blob/mode checks and
neutral-git guards. It runs NO scanner (the scan is ops/gap4_staging_admission.produce_scan on
the admitted copy) and transfers nothing. Run only after a fresh normal Mac light gate.
"""
import hashlib
import json
from pathlib import Path
import stat
import subprocess
import sys
import tempfile

REPO = Path(__file__).resolve().parents[1]
EVIDENCE = REPO / "lane-reports/live-box-evidence-2026-10-13"
PROPOSAL = EVIDENCE / "run-tree-source-manifest-proposal.json"
PROPOSAL_SHA = "c3ff255e0890d5f07fd8f5a866aeddf9e672abdeea2a5a329d1d353158e7e8bc"
OLD_MANIFEST = EVIDENCE / "sanitized-tree-manifest.json"
OLD_MANIFEST_SHA = "33a79a3b6d979c500d7e3a2b97e58a44d0fbbd3304509ceed6832caa911ed6ab"
NEW_MANIFEST = EVIDENCE / "sanitized-tree-manifest-20261014.json"
EXPORT_ROOT = Path("/Users/javrodher/aegis-builds/gap4-export-20261014")
APPROVED_FILES, APPROVED_BYTES = 156, 1304859


def _non_git(rows):
    return {r["path"]: r for r in rows if ".git" not in r["path"].split("/")}


def main():
    source = PROPOSAL.read_bytes()
    if hashlib.sha256(source).hexdigest() != PROPOSAL_SHA:
        raise RuntimeError("approved source proposal changed")
    old_bytes = OLD_MANIFEST.read_bytes()
    if hashlib.sha256(old_bytes).hexdigest() != OLD_MANIFEST_SHA:
        raise RuntimeError("retained 13 Oct manifest changed")
    old = _non_git(json.loads(old_bytes)["files"])
    if len(old) != APPROVED_FILES or sum(r["bytes"] for r in old.values()) != APPROVED_BYTES:
        raise RuntimeError("retained manifest is not the approved 156 files / 1,304,859 bytes")
    proposal = json.loads(source)
    EXPORT_ROOT.mkdir(mode=0o700)            # a new durable folder; refuses reuse
    tempfile.tempdir = str(EXPORT_ROOT)      # the existing writer places its checkout here
    sys.path.insert(0, str(REPO / "evals/gap-study-4"))
    import walk_builders
    import check_take
    import drive
    walk = "live-box-tree-proof-20261013"    # the same walk name, so the same neutral tree name
    tree = walk_builders.build_run_tree(walk, repo=str(REPO), commit=proposal["pin"],
                                       exclude=proposal["exclude"])
    output = {"schema": 1, "tree": str(tree), "proposal_sha256": PROPOSAL_SHA,
              "source_pin": proposal["pin"], "supersedes_manifest_sha256": OLD_MANIFEST_SHA,
              "scan": None, "files": [], "directories": []}
    try:
        if tree.parent != EXPORT_ROOT:
            raise RuntimeError("export landed outside the durable folder")
        expected = {f["path"]: f for f in proposal["files"]}
        actual = set()
        for path in sorted(tree.rglob("*")):
            st = path.lstat()
            relative = path.relative_to(tree).as_posix()
            if stat.S_ISDIR(st.st_mode):
                output["directories"].append({"path": relative, "mode": stat.S_IMODE(st.st_mode)})
                continue
            if not stat.S_ISREG(st.st_mode):
                raise RuntimeError("nonregular entry in exported tree: " + relative)
            data = path.read_bytes()
            row = {"path": relative, "bytes": len(data), "mode": stat.S_IMODE(st.st_mode),
                   "sha256": hashlib.sha256(data).hexdigest()}
            output["files"].append(row)
            if relative.startswith(".git/"):
                continue
            actual.add(relative)
            wanted = expected.get(relative)
            blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
            if wanted is None or blob != wanted["git_blob"] or len(data) != wanted["bytes"]:
                raise RuntimeError("exported file differs from approved inventory: " + relative)
            if bool(st.st_mode & 0o111) != (wanted["mode"] == "100755"):
                raise RuntimeError("exported file mode differs: " + relative)
            if old.get(relative) != row:
                raise RuntimeError("exported file differs from the 13 Oct manifest row: " + relative)
        if actual != set(expected) or actual != set(old) or len(actual) != APPROVED_FILES:
            raise RuntimeError("exported inventory differs from the approved 156 files")
        if sum(old[p]["bytes"] for p in actual) != APPROVED_BYTES:
            raise RuntimeError("exported byte total differs from 1,304,859")
        problems = drive.run_tree_problems(tree, check_take.walk_session_id(walk), proposal["exclude"])
        if problems:
            raise RuntimeError("neutral checkout guard failed: " + repr(problems))
        for args, wanted in ((["rev-list", "--all", "--count"], "1"), (["remote"], ""),
                             (["status", "--porcelain"], "")):
            got = subprocess.run(["git", "-C", str(tree), *args], check=True,
                                 capture_output=True, text=True).stdout.strip()
            if got != wanted:
                raise RuntimeError("neutral git guard failed: " + args[0])
        output["verified"] = True
    finally:
        with NEW_MANIFEST.open("x") as stream:
            json.dump(output, stream, indent=2, sort_keys=True)
            stream.write("\n")
    print(json.dumps({"tree": str(tree), "manifest": str(NEW_MANIFEST), "verified": True}))


if __name__ == "__main__":
    main()
