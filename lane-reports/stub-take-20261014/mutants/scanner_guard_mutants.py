"""Review S-1: mutants of box/scan_record.real_rules_scanner's three structural guards, each removed alone, against
tests/test_scan_record.py (in memory). Each must leave the suite red."""
import io, sys, types, unittest
from pathlib import Path
T = str(Path(__file__).resolve().parents[3] / "evals/gap-study-4/tests")
sys.path.insert(0, T); sys.dont_write_bytecode = True
import test_scan_record as tt
sr = tt.sr
SRC = open(sr.__file__).read()
MUTANTS = [
 ("record key set unchecked", 'set(rec) != {"adapter", "factory", "version", "sha256", "binary"}', 'False'),
 ("factory module unchecked", 'getattr(build, "__module__", None) != rec["adapter"]', 'False'),
 ("factory name unchecked", 'getattr(build, "__name__", None) != rec["factory"]', 'False'),
 ("unbuilt-scanner wording back", '"real_rules_scanner().build(runtime, report_dir)")', '"(gitleaks on athena: PENDING)")'),
]
def run(mod):
    tt.sr = mod
    try:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(tt.TestRulesScannerFilled)
        return unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
    finally:
        tt.sr = sr
c = run(sr); print("control", len(c.failures) + len(c.errors), "of", c.testsRun)
assert not (c.failures or c.errors), "the control is not clean"
alive = []
for name, old, new in MUTANTS:
    assert SRC.count(old) == 1, name
    mod = types.ModuleType(sr.__name__); mod.__file__ = sr.__file__
    exec(compile(SRC.replace(old, new), sr.__file__, "exec"), mod.__dict__)
    r = run(mod); bad = len(r.failures) + len(r.errors)
    print(("RED  " if bad else "ALIVE"), f"{bad}/{r.testsRun}", name)
    if not bad: alive.append(name)
print("ALIVE:", alive or "none")
