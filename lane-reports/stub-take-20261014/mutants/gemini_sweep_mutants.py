"""Mutants of box/run_take.py's Gemini package-sweep refusals (glitch-06, 14 Oct 2026) against
test_run_take.TestGeminiPackageSweep and TestCodexBinarySweep (in memory; nothing on disk changes)."""
import io, sys, types, unittest
from pathlib import Path
T = str(Path(__file__).resolve().parents[3] / "evals/gap-study-4/tests")
sys.path.insert(0, T); sys.dont_write_bytecode = True
import test_run_take as tt
rt = tt.rt
SRC = open(rt.__file__).read()
MUTANTS = [
 ("the Gemini entry back to PENDING", "    GEMINI: GEMINI_PACKAGE_SWEEP_REFUSED}", "    GEMINI: PENDING}"),
 ("a Gemini sweep name dropped", '"GEMINI_MODEL", ', ''),
 ("GEMINI_API_KEY refused for the Gemini arm", "GEMINI_PACKAGE_SWEEP_REFUSED = (\n", 'GEMINI_PACKAGE_SWEEP_REFUSED = ("GEMINI_API_KEY",\n'),
 ("a row name refused (GEMINI_CLI_HOME)", "GEMINI_PACKAGE_SWEEP_REFUSED = (\n", 'GEMINI_PACKAGE_SWEEP_REFUSED = ("GEMINI_CLI_HOME",\n'),
 ("a row name refused (HTTPS_PROXY)", "GEMINI_PACKAGE_SWEEP_REFUSED = (\n", 'GEMINI_PACKAGE_SWEEP_REFUSED = ("HTTPS_PROXY",\n'),
]
def run(mod):
    tt.rt = mod
    try:
        s = unittest.TestSuite()
        for c in (tt.TestGeminiPackageSweep, tt.TestCodexBinarySweep):
            s.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(c))
        return unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(s)
    finally:
        tt.rt = rt
c = run(rt); print("control", len(c.failures) + len(c.errors), "of", c.testsRun)
assert not (c.failures or c.errors), "the control is not clean"
alive = []
for name, old, new in MUTANTS:
    assert SRC.count(old) == 1, name
    mod = types.ModuleType(rt.__name__); mod.__file__ = rt.__file__
    try:
        exec(compile(SRC.replace(old, new), rt.__file__, "exec"), mod.__dict__)
    except Exception as e:  # noqa: BLE001
        print("RED  ", "load", name, f"({type(e).__name__})"); continue
    r = run(mod); bad = len(r.failures) + len(r.errors)
    print(("RED  " if bad else "ALIVE"), f"{bad}/{r.testsRun}", name)
    if not bad: alive.append(name)
print("ALIVE:", alive or "none")
