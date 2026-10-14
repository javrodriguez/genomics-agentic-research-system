"""Review S-1: mutants of the rules scanner's guards, each removed alone, against tests/test_scan_record.py's
TestRulesScannerFilled (in memory). The record's shape lives in box/scan_record.real_rules_scanner; the pin and factory
binding in box/rules_scanner.real_rules_scanner (moved there 14 Oct 2026, so scan_record imports nothing for it).
A rules_scanner mutant replaces only that one function, compiled in the real module's own namespace, so the module's
gitleaks_scanner keeps its identity and a red is never the trivial "another factory object"."""
import inspect, io, sys, types, unittest
from pathlib import Path
T = str(Path(__file__).resolve().parents[3] / "evals/gap-study-4/tests")
sys.path.insert(0, T); sys.dont_write_bytecode = True
import test_scan_record as tt
sr, rs = tt.sr, tt._rs
SR_SRC = open(sr.__file__).read()
RS_FN = inspect.getsource(rs.real_rules_scanner)
MUTANTS = [
 ("sr", "record key set unchecked", 'set(rec) != {"adapter", "factory", "version", "sha256", "binary"}', 'False'),
 ("sr", "unbuilt-scanner wording back", '"rules_scanner.real_rules_scanner().build(runtime, report_dir)")', '"(gitleaks on athena: PENDING)")'),
 ("rs", "factory module unchecked", 'getattr(build, "__module__", None) != __name__', 'False'),
 ("rs", "factory name unchecked", 'getattr(build, "__name__", None) != rec["factory"]', 'False'),
 ("rs", "pin drift unchecked", '    if drift:\n', '    if False:\n'),
]
def run():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(tt.TestRulesScannerFilled)
    return unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
c = run(); print("control", len(c.failures) + len(c.errors), "of", c.testsRun)
assert not (c.failures or c.errors), "the control is not clean"
alive = []
for where, name, old, new in MUTANTS:
    if where == "sr":
        assert SR_SRC.count(old) == 1, name
        mod = types.ModuleType(sr.__name__); mod.__file__ = sr.__file__
        exec(compile(SR_SRC.replace(old, new), sr.__file__, "exec"), mod.__dict__)
        tt.sr, rs.scan_record = mod, mod          # one module on both sides, so NotReady is one class
        try:
            r = run()
        finally:
            tt.sr, rs.scan_record = sr, sr
    else:
        assert RS_FN.count(old) == 1, name
        orig = rs.real_rules_scanner
        exec(compile(RS_FN.replace(old, new), rs.__file__, "exec"), rs.__dict__)
        try:
            r = run()
        finally:
            rs.real_rules_scanner = orig
    bad = len(r.failures) + len(r.errors)
    print(("RED  " if bad else "ALIVE"), f"{bad}/{r.testsRun}", name)
    if not bad: alive.append(name)
print("ALIVE:", alive or "none")
