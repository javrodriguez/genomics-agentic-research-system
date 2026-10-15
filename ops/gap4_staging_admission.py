"""One owner-approved directory finding, bound to managed byte-ruling metadata.

The scanner still runs without suppressions and returns1. This adapter neither
edits source nor writes rulings. It is not a general scanner allowlist, and it
never presents an approved finding as a clean scan. Managed metadata is read by
athena_suite.read_byte_rulings; no commit is invented for a directory finding.

Scope (r3 fold, 14 Oct 2026). The admitted and transferred tree is the pinned
export WITHOUT any `.git` path: gitleaks' default configuration never scans a
`.git` directory, so nothing under one can be admitted as scanned. The export
keeps its `.git/`; stage_admitted_tree copies only the manifest's non-`.git`
rows, byte-verified, into a new directory, which is what is scanned, admitted
and transferred. A tree holding any path named `.gitleaksignore` or
`.gitleaks.toml` is refused before scanning and at admission: gitleaks v8.30.0
always loads `<source>/.gitleaksignore`, whatever `--gitleaks-ignore-path` says.

Limitation, stated plainly: every record here is local and unsigned. Admission
binds consistency between the scan record, the report bytes, the tree now, the
scanner binary now and the managed rulings; it cannot prove the recorded run
happened, and a deliberate forger with write access to the evidence folder can
still write a consistent scan record.
"""
from __future__ import annotations

import hashlib
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess

SOURCE_PIN = "844a4ce0d89437ca043363981a86096f6383a141"
APPROVED_PATH = "gars/_references/environment.md"
APPROVED_RULE = "generic-api-key"
APPROVED_FILE_SHA = "574bed96b184c4e9ca50acd11fc48a892f6f1748d70ca9c2d603cbe5ba89d079"
APPROVED_FILE_BYTES = 10731
APPROVED_SPAN_SHA = "0b85623f36eef7c6e7ca19c7900e865fd7ddbfe5853197b5c1d2e246d81df313"
APPROVED_LINE = 175
SCANNER = "/Users/javrodher/.local/bin/gitleaks"
SCANNER_VERSION = "8.30.0"
DEFAULT_CONFIG = b"[extend]\nuseDefault = true\n"
GIT_COMPONENT = ".git"
SCANNER_CONTROL_NAMES = (".gitleaksignore", ".gitleaks.toml")
SCOPE = ("admitted tree = pinned export manifest rows without any .git path component; .git is never scanned by "
         "the default configuration and is neither admitted nor transferred")
LIMITATION = ("local unsigned records: admission binds consistency of scan record, report bytes, tree, scanner "
              "binary and managed rulings; it cannot prove the recorded run happened")

# The exact success shape of a full v8.30.0 run with one finding (cmd/root.go findingSummaryAndExit, err == nil),
# after ANSI colour codes are removed. Anything else (a partial scan, a skipped file, any other WRN/ERR) refuses.
_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_SCANNED = re.compile(r"\d{1,2}:\d{2}(?:AM|PM) INF scanned ~(\d+) bytes \([^()\n]+\) in [^\n]+")
_LEAKS = re.compile(r"\d{1,2}:\d{2}(?:AM|PM) WRN leaks found: 1")


class Refused(ValueError):
    pass


def _need(condition, message):
    if not condition:
        raise Refused(message)


def _regular_bytes(path: Path) -> bytes:
    """No link or special-file read, including a swapped final path."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        _need(stat.S_ISREG(os.fstat(fd).st_mode), "nonregular input refused")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            return stream.read()
    finally:
        os.close(fd)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _refuse_control_or_git(relative: str):
    """Case-folded: this Mac's APFS volume is case-insensitive, so gitleaks' stat of <tree>/.gitleaksignore finds
    .GITLEAKSIGNORE too (r4 finding 1); .git is folded the same way."""
    parts = [part.casefold() for part in relative.split("/")]
    _need(parts[-1] not in SCANNER_CONTROL_NAMES, "a scanner control file (.gitleaksignore/.gitleaks.toml) refused")
    _need(GIT_COMPONENT not in parts, "a .git path is never scanned, so it is never admitted")


def inventory(tree: Path) -> dict:
    """The tree's exact file and directory inventory, refusing links, special files, scanner control files and
    any .git path."""
    _need(tree.is_absolute() and not tree.is_symlink() and tree.is_dir(), "absolute real tree required")
    files, directories = [], []
    for path in sorted(tree.rglob("*")):
        st = path.lstat()
        relative = path.relative_to(tree).as_posix()
        _refuse_control_or_git(relative)
        if stat.S_ISDIR(st.st_mode):
            directories.append({"path": relative, "mode": stat.S_IMODE(st.st_mode)})
            continue
        _need(stat.S_ISREG(st.st_mode), "nonregular exported entry refused")
        data = _regular_bytes(path)
        files.append({"path": relative, "bytes": len(data), "mode": stat.S_IMODE(st.st_mode), "sha256": _sha(data)})
    # One order for every inventory: the path string (r4 finding 4), as admitted_inventory sorts.
    return {"files": sorted(files, key=lambda r: r["path"]),
            "directories": sorted(directories, key=lambda r: r["path"])}


def inventory_sha256(inv: dict) -> str:
    return _sha(json.dumps(inv, sort_keys=True, separators=(",", ":")).encode())


def admitted_inventory(manifest: dict) -> tuple:
    """(the manifest's non-.git inventory in inventory()'s form, the count of excluded .git rows)."""
    _need(isinstance(manifest, dict) and manifest.get("source_pin") == SOURCE_PIN, "wrong pinned export")
    rows, dirs = manifest.get("files"), manifest.get("directories")
    _need(isinstance(rows, list) and all(isinstance(row, dict) for row in rows) and
          isinstance(dirs, list) and all(isinstance(d, dict) for d in dirs), "bad export file manifest")
    files, seen, excluded = [], set(), 0
    for row in rows:
        name = row.get("path")
        _need(isinstance(name, str) and name and not name.startswith("/") and
              all(part not in ("", ".", "..") for part in name.split("/")) and name not in seen,
              "bad or duplicate export path")
        seen.add(name)
        _need(set(row) == {"path", "bytes", "mode", "sha256"}, "bad export file row")
        if GIT_COMPONENT in name.split("/"):
            excluded += 1
            continue
        _refuse_control_or_git(name)
        files.append(dict(row))
    directories = []
    for d in dirs:
        name = d.get("path")
        _need(isinstance(name, str) and set(d) == {"path", "mode"}, "bad export directory row")
        if GIT_COMPONENT in name.split("/"):
            continue
        _refuse_control_or_git(name)
        directories.append(dict(d))
    return ({"files": sorted(files, key=lambda r: r["path"]),
             "directories": sorted(directories, key=lambda r: r["path"])}, excluded)


def stage_admitted_tree(export: Path, manifest: dict, dest: Path) -> dict:
    """Copy the manifest's non-.git rows, byte-verified, from the retained export into a new directory.
    The export is only read. Returns {inventory_sha256, files, directories, excluded_git_rows}."""
    _need(export.is_absolute() and not export.is_symlink() and export.is_dir(), "absolute real export required")
    _need(manifest.get("tree") == str(export), "export manifest names another tree")
    expected, excluded = admitted_inventory(manifest)
    _need(dest.is_absolute(), "absolute staging directory required")
    dest.mkdir(mode=0o700)   # refuses reuse, including a symlink
    for d in expected["directories"]:
        (dest / d["path"]).mkdir(mode=0o700)
    for row in expected["files"]:
        parts = row["path"].split("/")
        for depth in range(1, len(parts) + 1):   # no link in any component (r4 finding 3)
            _need(not stat.S_ISLNK((export.joinpath(*parts[:depth])).lstat().st_mode),
                  "a link inside the export refused")
        data = _regular_bytes(export / row["path"])
        _need(len(data) == row["bytes"] and _sha(data) == row["sha256"], "export bytes differ from manifest")
        _need(stat.S_IMODE((export / row["path"]).lstat().st_mode) == row["mode"], "export mode differs")
        fd = os.open(dest / row["path"], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
        os.chmod(dest / row["path"], row["mode"])
    for d in reversed(expected["directories"]):
        os.chmod(dest / d["path"], d["mode"])
    actual = inventory(dest)
    _need(actual == expected, "staged tree differs from the manifest's admitted rows")
    return {"inventory_sha256": inventory_sha256(actual), "files": len(actual["files"]),
            "directories": len(actual["directories"]), "excluded_git_rows": excluded}


def _stderr_scanned_bytes(stderr) -> int:
    """The scanned byte count of an exact full-run, one-finding stderr; anything else refuses."""
    _need(isinstance(stderr, str), "scanner stderr absent")
    lines = _ANSI.sub("", stderr).split("\n")
    _need(len(lines) == 3 and lines[2] == "", "scanner stderr is not the full-scan success shape")
    scanned = _SCANNED.fullmatch(lines[0])
    _need(scanned is not None and _LEAKS.fullmatch(lines[1]) is not None,
          "scanner stderr is not the full-scan success shape (partial, skipped, warned or errored scans refuse)")
    return int(scanned.group(1))


def admit_directory_finding(tree: Path, manifest: dict, scan: dict, report: bytes,
                            *, managed_rulings: list) -> dict:
    """Validate one raw scan, its report bytes and every admitted byte against the retained manifest.

    managed_rulings must come from the existing managed reader at the CLI boundary.
    This boundary accepts parsed inputs for refusal tests; it has no write path.
    """
    _need(tree.is_absolute() and not tree.is_symlink() and tree.is_dir(), "absolute real tree required")
    expected, excluded = admitted_inventory(manifest)
    _need(isinstance(scan, dict) and type(scan.get("exit")) is int and scan["exit"] == 1,
          "raw scan must retain its finding exit1")
    context = scan.get("context")
    _need(isinstance(context, dict), "controlled scanner context absent")
    cwd = Path(context.get("cwd", ""))
    _need(cwd.is_absolute() and cwd.is_dir() and not cwd.is_symlink() and
          stat.S_IMODE(cwd.stat().st_mode) == 0o700, "scanner cwd is not controlled")
    config = cwd / "defaults.toml"
    _need(sorted(p.name for p in cwd.iterdir()) == ["defaults.toml"] and
          _regular_bytes(config) == DEFAULT_CONFIG, "scanner configuration differs")
    _need(context == {"cwd": str(cwd), "env": {"PATH": "/usr/bin:/bin", "HOME": str(cwd)},
                      "config_path": str(config), "config_sha256": _sha(DEFAULT_CONFIG),
                      "scanner_sha256": _sha(_regular_bytes(Path(SCANNER))),
                      "scanner_version": SCANNER_VERSION}, "scanner identity or environment differs")
    expected_argv = [SCANNER, "dir", "--no-banner", "--redact", "--config", str(config),
                     "--exit-code", "1", "--ignore-gitleaks-allow", "--gitleaks-ignore-path", "/dev/null", str(tree),
                     "--report-format", "json"]
    argv = scan.get("argv")
    _need(isinstance(argv, list) and argv[:len(expected_argv)] == expected_argv and
          len(argv) == len(expected_argv) + 2 and argv[-2] == "--report-path" and
          isinstance(argv[-1], str) and os.path.isabs(argv[-1]), "scan command is not the unsuppressed road")
    # The report bytes are the ones the scan recorded, and the stderr is a full run of exactly the admitted bytes.
    _need(isinstance(report, bytes) and scan.get("report_sha256") == _sha(report), "report not bound to scan")
    try:
        findings = json.loads(report)
    except ValueError:
        raise Refused("report is not JSON") from None
    _need(isinstance(findings, list) and len(findings) == 1 and isinstance(findings[0], dict),
          "one finding required; new or malformed findings refuse")
    _need(type(scan.get("finding_count")) is int and scan["finding_count"] == len(findings),
          "recorded finding count differs from report")
    admitted_bytes = sum(row["bytes"] for row in expected["files"])
    _need(_stderr_scanned_bytes(scan.get("stderr")) == admitted_bytes,
          "scanner did not scan exactly the admitted bytes")
    finding = findings[0]
    expected_file = str(tree / APPROVED_PATH)
    _need(finding.get("File") == expected_file and finding.get("RuleID") == APPROVED_RULE,
          "finding path or rule differs")
    for field, value in (("StartLine", 175), ("EndLine", 175), ("StartColumn", 2), ("EndColumn", 38)):
        _need(type(finding.get(field)) is int and finding[field] == value, "finding span differs")
    _need(finding.get("Commit", "") == "", "directory finding must not claim a commit")
    _need(finding.get("Fingerprint") == expected_file + ":generic-api-key:175", "finding fingerprint differs")
    _need(finding.get("Secret") == "REDACTED", "raw report must be redacted")
    expected_ruling = (APPROVED_PATH, APPROVED_RULE, 1, APPROVED_SPAN_SHA)
    _need(isinstance(managed_rulings, list) and managed_rulings.count(expected_ruling) >= 1,
          "exact managed byte ruling is absent")

    expected_sha = inventory_sha256(expected)
    _need(scan.get("tree_inventory_sha256") == expected_sha, "tree at scan time differs from the admitted rows")
    # Every refusal produce_scan makes after writing its record is visible here too (r4 finding 2).
    _need(scan.get("tree_inventory_sha256_after") == scan["tree_inventory_sha256"], "tree changed during the scan")
    _need(scan.get("scanner_sha256_after") == context["scanner_sha256"], "scanner changed during run")
    actual = inventory(tree)
    _need(actual == expected, "export changed since raw scan")
    row = next((r for r in actual["files"] if r["path"] == APPROVED_PATH), None)
    _need(row == {"path": APPROVED_PATH, "bytes": APPROVED_FILE_BYTES, "mode": 0o644,
                  "sha256": APPROVED_FILE_SHA}, "approved full-file bytes differ")
    data = _regular_bytes(tree / APPROVED_PATH)
    lines = data.split(b"\n")
    _need(len(lines) >= APPROVED_LINE, "approved line absent")
    held = lines[APPROVED_LINE - 1].replace(b"\r", b"")
    _need(len(held) == 80 and _sha(held) == APPROVED_SPAN_SHA, "approved span bytes differ")
    return {"schema": 2, "status": "owner-approved-byte-bound-finding", "raw_scan_exit": 1,
            "approved_findings": 1, "unresolved_findings": 0, "source_pin": SOURCE_PIN,
            "path": APPROVED_PATH, "rule": APPROVED_RULE, "file_sha256": APPROVED_FILE_SHA,
            "span_sha256": APPROVED_SPAN_SHA, "managed_ruling_count": len(managed_rulings),
            "matching_managed_ruling_count": managed_rulings.count(expected_ruling),
            "scope": SCOPE, "excluded_git_rows": excluded, "admitted_tree": str(tree),
            "manifest_tree": manifest.get("tree"), "tree_inventory_sha256": expected_sha,
            "scanned_bytes": admitted_bytes, "report_sha256": scan["report_sha256"],
            "limitation": LIMITATION}


def produce_scan(tree: Path, output: Path) -> dict:
    """Fresh raw evidence only; call after the external normal-resource gate.

    v8.30.0's official configuration contract supports an explicit extension of
    the embedded defaults; an explicit --config wins over the environment and a
    target .gitleaks.toml, and --gitleaks-ignore-path /dev/null names no ignore
    file. It does NOT stop gitleaks loading <tree>/.gitleaksignore, so a tree
    holding any .gitleaksignore or .gitleaks.toml (or any .git path) is refused
    before the scan. The tree inventory is taken before and after the run and
    must not differ. All newly created objects and failed evidence remain
    available for review; a refusal after the run still leaves raw-scan.json.
    """
    _need(tree.is_absolute() and tree.is_dir() and not tree.is_symlink(), "real scan tree required")
    _need(output.is_absolute(), "absolute evidence directory required")
    before = inventory(tree)   # refuses control files and .git before anything runs
    output.mkdir(mode=0o700)  # Refuse reuse, including a symlink.
    cwd = output / "scanner-cwd"
    cwd.mkdir(mode=0o700)
    config = cwd / "defaults.toml"
    config.write_bytes(DEFAULT_CONFIG)
    config.chmod(0o600)
    env = {"PATH": "/usr/bin:/bin", "HOME": str(cwd)}
    scanner_hash = _sha(_regular_bytes(Path(SCANNER)))
    version = subprocess.run([SCANNER, "version"], cwd=cwd, env=env,
                             capture_output=True, text=True, timeout=10)
    _need(version.returncode == 0 and version.stdout.strip() == SCANNER_VERSION,
          "scanner version differs from scanner of record")
    report = output / "raw-report.json"
    argv = [SCANNER, "dir", "--no-banner", "--redact", "--config", str(config),
            "--exit-code", "1", "--ignore-gitleaks-allow", "--gitleaks-ignore-path", "/dev/null", str(tree),
            "--report-format", "json", "--report-path", str(report)]
    run = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True, timeout=120)
    after = inventory(tree)
    scanner_hash_after = _sha(_regular_bytes(Path(SCANNER)))
    context = {"cwd": str(cwd), "env": env, "config_path": str(config),
               "config_sha256": _sha(DEFAULT_CONFIG),
               "scanner_sha256": scanner_hash, "scanner_version": version.stdout.strip()}
    report_sha, finding_count = None, None
    try:
        report_bytes = _regular_bytes(report)
        report_sha = _sha(report_bytes)
        parsed = json.loads(report_bytes)
        finding_count = len(parsed) if isinstance(parsed, list) else None
    except (OSError, ValueError, Refused):
        pass
    result = {"argv": argv, "exit": run.returncode, "stdout": run.stdout, "stderr": run.stderr,
              "context": context, "report_sha256": report_sha, "finding_count": finding_count,
              "tree_inventory_sha256": inventory_sha256(before),
              "tree_inventory_sha256_after": inventory_sha256(after), "scanner_sha256_after": scanner_hash_after}
    with (output / "raw-scan.json").open("x") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    _need(scanner_hash_after == scanner_hash, "scanner changed during run")
    _need(before == after, "tree changed during the scan")
    _need(report_sha is not None and finding_count is not None, "scanner report absent or malformed")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("tree", "manifest", "scan", "report", "output"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    inputs = {name: _regular_bytes(Path(getattr(args, name))) for name in ("manifest", "scan", "report")}
    parsed = {name: json.loads(inputs[name]) for name in ("manifest", "scan")}
    _need(parsed["scan"].get("argv", [])[-1:] == [str(Path(args.report))], "raw report path not bound to scan")
    reader = Path("/Users/javrodher/glitch/workspaces/aegis/ops/athena_suite.py")
    rulings = Path("/Users/javrodher/glitch/workspaces/genomics-agentic-research-system/.git/hooks/glitch-gitleaksignore")
    spec = importlib.util.spec_from_file_location("gap_managed_athena_suite", reader)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    ruling_bytes = _regular_bytes(rulings)
    rules = module.read_byte_rulings(str(rulings))
    _need(_regular_bytes(rulings) == ruling_bytes, "managed rulings changed during read")
    result = admit_directory_finding(Path(args.tree), parsed["manifest"], parsed["scan"], inputs["report"],
                                     managed_rulings=rules)
    result["inputs"] = {name: _sha(data) for name, data in inputs.items()}
    result["managed_reader_sha256"] = _sha(_regular_bytes(reader))
    result["managed_rulings_sha256"] = _sha(ruling_bytes)
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"status": result["status"], "approved_findings": 1, "unresolved_findings": 0}))


if __name__ == "__main__":
    main()
