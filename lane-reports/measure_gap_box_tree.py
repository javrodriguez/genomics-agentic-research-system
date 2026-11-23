"""Read-only full-tree watch measurement on the already scanned, admitted sanitized tree.

Run on Athena only. No fixture or production constant is written. The source tree
is mounted read-only into the pinned watcher image; no credentials are mounted.

The source is the admitted tree: the pinned export's manifest rows without any
.git path (the default scanner configuration never scans .git, so it is neither
admitted nor transferred). The admission record is re-checked field by field
against the approved constants and this exact manifest; a record carrying only
the status fields does not unlock the measurement. The scan exit reported is the
fresh admitted scan's, never the superseded manifest scan's. Records are local
and unsigned (named limitation of the admission).
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

SOURCE_PIN = "844a4ce0d89437ca043363981a86096f6383a141"
APPROVED_PATH = "gars/_references/environment.md"
APPROVED_RULE = "generic-api-key"
APPROVED_FILE_SHA = "574bed96b184c4e9ca50acd11fc48a892f6f1748d70ca9c2d603cbe5ba89d079"
APPROVED_SPAN_SHA = "0b85623f36eef7c6e7ca19c7900e865fd7ddbfe5853197b5c1d2e246d81df313"
GIT_COMPONENT = ".git"
SCANNER_CONTROL_NAMES = (".gitleaksignore", ".gitleaks.toml")


def _refuse_control_or_git(relative):
    parts = [part.casefold() for part in relative.split("/")]   # case-insensitive volumes (review r4 finding 1)
    if parts[-1] in SCANNER_CONTROL_NAMES or GIT_COMPONENT in parts:
        raise RuntimeError("a scanner control file or .git path is never admitted")


def admitted_inventory(manifest):
    """The manifest's non-.git rows, in the admission adapter's canonical inventory form."""
    files = [dict(r) for r in manifest["files"] if GIT_COMPONENT not in r["path"].split("/")]
    dirs = [dict(d) for d in manifest["directories"] if GIT_COMPONENT not in d["path"].split("/")]
    for r in files + dirs:
        _refuse_control_or_git(r["path"])
    return {"files": sorted(files, key=lambda r: r["path"]), "directories": sorted(dirs, key=lambda r: r["path"])}


def inventory_sha256(inv):
    return hashlib.sha256(json.dumps(inv, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def check_admission(admission, manifest, manifest_bytes):
    """Every field the measurement relies on, re-checked; any difference refuses."""
    count = admission.get("matching_managed_ruling_count")
    row = next((r for r in manifest.get("files", []) if r.get("path") == APPROVED_PATH), None)
    if (admission.get("status") != "owner-approved-byte-bound-finding" or
            admission.get("raw_scan_exit") != 1 or admission.get("approved_findings") != 1 or
            admission.get("unresolved_findings") != 0 or
            admission.get("source_pin") != manifest.get("source_pin") or
            admission.get("path") != APPROVED_PATH or admission.get("rule") != APPROVED_RULE or
            admission.get("file_sha256") != APPROVED_FILE_SHA or admission.get("span_sha256") != APPROVED_SPAN_SHA or
            type(count) is not int or count < 1 or
            row is None or row.get("sha256") != APPROVED_FILE_SHA or
            admission.get("tree_inventory_sha256") != inventory_sha256(admitted_inventory(manifest)) or
            admission.get("inputs", {}).get("manifest") != hashlib.sha256(manifest_bytes).hexdigest()):
        raise RuntimeError("byte-bound admission does not cover this exact manifest")
    return admission["raw_scan_exit"]


def superseded_scan_exit(manifest):
    """The export manifest's own scan exit, or None: the 14 Oct re-export manifest records no scan."""
    scan = manifest.get("scan")
    return scan.get("exit") if isinstance(scan, dict) else None


def source_inventory(tree):
    files, directories = [], []
    for path in sorted(tree.rglob("*")):
        st = path.lstat()
        relative = path.relative_to(tree).as_posix()
        _refuse_control_or_git(relative)
        if stat.S_ISDIR(st.st_mode):
            directories.append({"path": relative, "mode": stat.S_IMODE(st.st_mode)})
            continue
        if not stat.S_ISREG(st.st_mode):
            raise RuntimeError("nonregular source entry refused")
        data = path.read_bytes()
        files.append({"path": relative, "bytes": len(data), "mode": stat.S_IMODE(st.st_mode),
                      "sha256": hashlib.sha256(data).hexdigest()})
    return {"files": sorted(files, key=lambda r: r["path"]),
            "directories": sorted(directories, key=lambda r: r["path"])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--admission", required=True, help="reviewed byte-bound admission of the fresh scan")
    parser.add_argument("--box-source", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if sys.platform != "linux":
        raise RuntimeError("Athena Linux measurement only")
    tree = Path(args.source)
    if not tree.is_absolute() or tree.is_symlink() or tree.stat().st_uid != os.getuid():
        raise RuntimeError("owned absolute sanitized tree required")
    manifest_bytes = Path(args.manifest).read_bytes()
    manifest = json.loads(manifest_bytes)
    if manifest.get("source_pin") != SOURCE_PIN:
        raise RuntimeError("pinned export manifest required")
    path = Path(args.admission)
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("regular byte-bound admission record required")
    data = path.read_bytes()
    admitted_scan_exit = check_admission(json.loads(data), manifest, manifest_bytes)
    admission_hash = hashlib.sha256(data).hexdigest()
    expected = admitted_inventory(manifest)
    actual = source_inventory(tree)
    if actual["files"] != expected["files"]:
        raise RuntimeError("transported source inventory/hash mismatch")
    if actual["directories"] != expected["directories"]:
        raise RuntimeError("transported directory inventory mismatch")
    directories = 1 + len(actual["directories"])
    sys.path.insert(0, args.box_source)
    from box.measure_live import MEASURE, Proof
    proof = Proof()
    output = {"scope": "sanitized admitted-tree (no .git) watch measurement; no fixture or production admission",
              "source_pin": manifest["source_pin"], "source_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
              "admitted_scan_exit": admitted_scan_exit,
              "superseded_manifest_scan_exit": superseded_scan_exit(manifest),
              "byte_bound_admission_sha256": admission_hash, "tree_inventory_sha256": inventory_sha256(actual),
              "files_verified": len(actual["files"]), "directory_count": directories, "calls": proof.calls}
    try:
        output["measurement"] = json.loads(proof.watcher(
            ["/usr/bin/python3", "-I", "-S", "-c", MEASURE], ((tree, "/tree", True),)))
        if output["measurement"]["watch_count"] != directories:
            raise RuntimeError("watch count does not cover all transported directories")
        output["verified"] = True
    finally:
        with open(args.output, "x", encoding="utf-8") as stream:
            json.dump(output, stream, indent=2, sort_keys=True)
            stream.write("\n")


if __name__ == "__main__":
    main()
