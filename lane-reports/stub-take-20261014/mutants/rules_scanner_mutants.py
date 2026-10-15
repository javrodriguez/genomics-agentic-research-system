"""Mutants of box/rules_scanner.py against tests/test_rules_scanner.py (in memory)."""
import io, sys, types, unittest
from pathlib import Path
T = str(Path(__file__).resolve().parents[3] / "evals/gap-study-4/tests")
sys.path.insert(0, T); sys.dont_write_bytecode = True
import test_rules_scanner as tt
rs = tt.rs
SRC = open(rs.__file__).read()
MUTANTS = [
 ("sha unchecked", "    if _sha256_file(binary) != GITLEAKS_SHA256:\n", "    if False:\n"),
 ("version unchecked", "    if v.returncode != 0 or v.stdout.strip() != GITLEAKS_VERSION:\n", "    if v.returncode != 0:\n"),
 ("version prefix", "v.stdout.strip() != GITLEAKS_VERSION", "not v.stdout.strip().endswith(GITLEAKS_VERSION)"),
 ("exit ignored", "            if c.returncode != 0:\n                raise ScannerRefused(f\"gitleaks exited", "            if False:\n                raise ScannerRefused(f\"gitleaks exited"),
 ("missing report is clean", "                raise ScannerRefused(f\"gitleaks wrote no readable report for {p}\") from None", "                findings = []"),
 ("unredacted", '"--redact", ', ""),
 ("finding shape unchecked", "                if not (isinstance(line, int)", "                if False and not (isinstance(line, int)"),
 ("pin version drift", 'GITLEAKS_VERSION = "8.30.1"', 'GITLEAKS_VERSION = "8.30.0"'),
 ("used report folder", " or os.listdir(report_dir):", ":"),
]
def run(mod):
    tt.rs = mod
    try:
        return unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(unittest.defaultTestLoader.loadTestsFromModule(tt))
    finally:
        tt.rs = rs
c = run(rs); print("control", len(c.failures) + len(c.errors), "of", c.testsRun)
alive = []
for name, old, new in MUTANTS:
    assert SRC.count(old) == 1, name
    mod = types.ModuleType(rs.__name__); mod.__file__ = rs.__file__
    exec(compile(SRC.replace(old, new), rs.__file__, "exec"), mod.__dict__)
    r = run(mod); bad = len(r.failures) + len(r.errors)
    print(("RED  " if bad else "ALIVE"), f"{bad}/{r.testsRun}", name)
    if not bad: alive.append(name)
print("ALIVE:", alive or "none")
