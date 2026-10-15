"""Mutants of box/run_take.py's no-login launcher variant (glitch-06, 14 Oct 2026), one per branch, against
tests/test_run_take.TestNoLoginLauncher (in memory; nothing on disk changes, no process starts)."""
import io, sys, types, unittest
from pathlib import Path
T = str(Path(__file__).resolve().parents[3] / "evals/gap-study-4/tests")
sys.path.insert(0, T); sys.dont_write_bytecode = True
import test_run_take as tt
rt = tt.rt
SRC = open(rt.__file__).read()
MUTANTS = [
 ("the launcher copies the reserved name", '"if k!=\'-\':e[k]=os.environ[k]\\n"', '"e[k]=os.environ.get(k,\'\')\\n"'),
 ("the launcher skips every credential", '"if k!=\'-\':e[k]=os.environ[k]\\n"', '"pass\\n"'),
 ("no gate on the reserved name", "    if login == NO_LOGIN:\n        codex_lease_gate()\n", "    if login == NO_LOGIN:\n"),
 ("the reserved name for any harness", '        if harness != CODEX:\n            raise Refused("the no-login', '        if False:\n            raise Refused("the no-login'),
 ("the reserved name not reserved", 'NO_LOGIN = "-"', 'NO_LOGIN = "NO_LOGIN"'),
]
def run(mod):
    tt.rt = mod
    try:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(tt.TestNoLoginLauncher)
        return unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
    finally:
        tt.rt = rt
c = run(rt); print("control", len(c.failures) + len(c.errors), "of", c.testsRun)
assert not (c.failures or c.errors), "the control is not clean"
alive = []
for name, old, new in MUTANTS:
    assert SRC.count(old) == 1, name
    mod = types.ModuleType(rt.__name__); mod.__file__ = rt.__file__
    exec(compile(SRC.replace(old, new), rt.__file__, "exec"), mod.__dict__)
    r = run(mod); bad = len(r.failures) + len(r.errors)
    print(("RED  " if bad else "ALIVE"), f"{bad}/{r.testsRun}", name)
    if not bad: alive.append(name)
print("ALIVE:", alive or "none")
