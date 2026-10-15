"""Mutants of box/preflight.py's create-time prefix refusal (glitch-06, 14 Oct 2026) against
tests/test_preflight.TestCreatePrefixRefusal (in memory; nothing on disk changes)."""
import io, sys, types, unittest
from pathlib import Path
T = str(Path(__file__).resolve().parents[3] / "evals/gap-study-4/tests")
sys.path.insert(0, T); sys.dont_write_bytecode = True
import test_preflight as tt
pf = tt.pf
SRC = open(pf.__file__).read()
MUTANTS = [
 ("no prefix at create", "    leaked = sorted(n for n in names if n in refused or n.startswith(run_take.REFUSED_NAME_PREFIXES))",
  "    leaked = sorted(n for n in names if n in refused)"),
 ("prefix matched anywhere but the start", "    leaked = sorted(n for n in names if n in refused or n.startswith(run_take.REFUSED_NAME_PREFIXES))",
  "    leaked = sorted(n for n in names if n in refused or n.endswith(run_take.REFUSED_NAME_PREFIXES))"),
]
def run(mod):
    tt.pf = mod
    try:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(tt.TestCreatePrefixRefusal)
        return unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
    finally:
        tt.pf = pf
c = run(pf); print("control", len(c.failures) + len(c.errors), "of", c.testsRun)
assert not (c.failures or c.errors), "the control is not clean"
alive = []
for name, old, new in MUTANTS:
    assert SRC.count(old) == 1, name
    mod = types.ModuleType(pf.__name__); mod.__file__ = pf.__file__
    exec(compile(SRC.replace(old, new), pf.__file__, "exec"), mod.__dict__)
    r = run(mod); bad = len(r.failures) + len(r.errors)
    print(("RED  " if bad else "ALIVE"), f"{bad}/{r.testsRun}", name)
    if not bad: alive.append(name)
print("ALIVE:", alive or "none")
