"""Box lane, 14 Oct 2026: source-level in-memory mutants of the admission adapter and measure helper; each must turn a test red."""
import io, sys, types, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evals/gap-study-4/tests"))
sys.dont_write_bytecode = True
import test_staging_admission as ts
SRC = {"admission": open(ts.PATH).read(), "measure": open(ts.MEASURE_PATH).read()}
mutants = [
 ("admission", "control names emptied", 'SCANNER_CONTROL_NAMES = (".gitleaksignore", ".gitleaks.toml")', 'SCANNER_CONTROL_NAMES = ()'),
 ("admission", "only root .gitleaksignore checked", '_need(parts[-1] not in SCANNER_CONTROL_NAMES,', '_need(relative not in SCANNER_CONTROL_NAMES,'),
 ("admission", ".git admitted", '_need(GIT_COMPONENT not in parts,', '_need(True,'),
 ("admission", ".git rows kept in expected", '            excluded += 1\n            continue\n', '            excluded += 1\n'),
 ("admission", "stderr shape unchecked", '    _need(_stderr_scanned_bytes(scan.get("stderr")) == admitted_bytes,', '    _need(True,'),
 ("admission", "extra stderr lines tolerated", '_need(len(lines) == 3 and lines[2] == ""', '_need(len(lines) >= 3'),
 ("admission", "leak line loosened", 'WRN leaks found: 1")', 'WRN .*leaks found.*")'),
 ("admission", "report sha unchecked", 'scan.get("report_sha256") == _sha(report)', 'True'),
 ("admission", "finding count unchecked", 'scan["finding_count"] == len(findings)', 'True'),
 ("admission", "scan-time inventory unchecked", '_need(scan.get("tree_inventory_sha256") == expected_sha,', '_need(True,'),
 ("admission", "produce: after not compared", '_need(before == after, "tree changed during the scan")', 'pass'),
 ("admission", "produce: no pre-scan inventory", '    before = inventory(tree)   # refuses', '    before = {}   # refuses'),
 ("admission", "stage: bytes unchecked", '_need(len(data) == row["bytes"] and _sha(data) == row["sha256"],', '_need(True,'),
 ("admission", "r4: control names case-sensitive", 'parts = [part.casefold() for part in relative.split("/")]', 'parts = relative.split("/")'),
 ("admission", "r4: after-inventory unchecked", '_need(scan.get("tree_inventory_sha256_after") == scan["tree_inventory_sha256"],', '_need(True,'),
 ("admission", "r4: after-scanner sha unchecked", '_need(scan.get("scanner_sha256_after") == context["scanner_sha256"],', '_need(True,'),
 ("admission", "r4: staging follows links", 'not stat.S_ISLNK((export.joinpath(*parts[:depth])).lstat().st_mode)', 'True'),
 ("admission", "r4: inventory unsorted", 'return {"files": sorted(files, key=lambda r: r["path"]),\n            "directories": sorted(directories, key=lambda r: r["path"])}', 'return {"files": files, "directories": directories}'),
 ("measure", "r4: control names case-sensitive", 'parts = [part.casefold() for part in relative.split("/")]', 'parts = relative.split("/")'),
 ("measure", "count check off", 'type(count) is not int or count < 1 or', ''),
 ("measure", "span check off", 'or admission.get("span_sha256") != APPROVED_SPAN_SHA', ''),
 ("measure", "manifest row check off", 'row is None or row.get("sha256") != APPROVED_FILE_SHA or', ''),
 ("measure", "inventory sha check off", 'admission.get("tree_inventory_sha256") != inventory_sha256(admitted_inventory(manifest)) or', ''),
 ("measure", "control names emptied", 'SCANNER_CONTROL_NAMES = (".gitleaksignore", ".gitleaks.toml")', 'SCANNER_CONTROL_NAMES = ()'),
]
for which, name, old, new in mutants:
    src = SRC[which]
    assert src.count(old) == 1, (name, src.count(old))
    mod = types.ModuleType("mutant_" + which)
    mod.__file__ = str(ts.PATH if which == "admission" else ts.MEASURE_PATH)
    exec(compile(src.replace(old, new), mod.__file__, "exec"), mod.__dict__)
    orig = getattr(ts, which)
    setattr(ts, which, mod)
    try:
        r = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(unittest.defaultTestLoader.loadTestsFromModule(ts))
    finally:
        setattr(ts, which, orig)
    bad = len(r.failures) + len(r.errors)
    print(("RED  " if bad else "ALIVE"), f"{bad}/{r.testsRun}", which + ":", name)

