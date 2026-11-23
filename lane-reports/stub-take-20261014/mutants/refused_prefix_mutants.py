"""Mutants of box/run_take.py's prefix refusal (glitch-06, 14 Oct 2026) against test_run_take.TestRefusedPrefixes (in
memory; nothing on disk changes)."""
import io, sys, types, unittest
from pathlib import Path
T = str(Path(__file__).resolve().parents[3] / "evals/gap-study-4/tests")
sys.path.insert(0, T); sys.dont_write_bytecode = True
import test_run_take as tt
rt = tt.rt
SRC = open(rt.__file__).read()
MUTANTS = [
 ("no prefix check", "    return name in refused or (isinstance(name, str) and name.startswith(REFUSED_NAME_PREFIXES))", "    return name in refused"),
 ("the caller's names by membership only", "    in_caller = sorted(n for n in names if _refused_name(n, refused))", "    in_caller = sorted(n for n in names if n in refused)"),
 ("the requested names by membership only", "    asked = sorted(n for n in requested if _refused_name(n, refused))", "    asked = sorted(n for n in requested if n in refused)"),
 ("the VALUE_ prefix dropped", 'REFUSED_NAME_PREFIXES = ("CODEX_NETWORK_PROXY_SNAPSHOT_BROKERED_UNSET_", "CODEX_NETWORK_PROXY_SNAPSHOT_BROKERED_VALUE_")', 'REFUSED_NAME_PREFIXES = ("CODEX_NETWORK_PROXY_SNAPSHOT_BROKERED_UNSET_",)'),
]
def run(mod):
    tt.rt = mod
    try:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(tt.TestRefusedPrefixes)
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
