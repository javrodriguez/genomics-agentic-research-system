"""Mutants of box/preflight.py's Codex lease postflight (glitch-06, 14 Oct 2026), one per refusal branch, against
tests/test_preflight.TestLeasePostflight (in memory; nothing on disk changes)."""
import io, sys, types, unittest
from pathlib import Path
T = str(Path(__file__).resolve().parents[3] / "evals/gap-study-4/tests")
sys.path.insert(0, T); sys.dont_write_bytecode = True
import test_preflight as tt
pf = tt.pf
SRC = open(pf.__file__).read()
MUTANTS = [
 ("registered path may be a link", '        if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):\n            problems.append(f"{reg}: the registered', '        if False:\n            problems.append(f"{reg}: the registered'),
 ("second hard link admitted", '        elif st.st_nlink != 1:', '        elif False:'),
 ("any mode admitted", '        elif stat.S_IMODE(st.st_mode) != 0o600:', '        elif False:'),
 ("any owner admitted", '        elif st.st_uid != os.getuid():', '        elif False:'),
 ("links to it admitted", '            if os.path.realpath(path) == reg_real or name in _credential_names() or CREDENTIAL_LIKE.search(name):', '            if False:'),
 ("second credential-shaped file admitted", '        if name in _credential_names() or CREDENTIAL_LIKE.search(name):\n            problems.append(f"{rel}: a credential-shaped', '        if False:\n            problems.append(f"{rel}: a credential-shaped'),
 ("renamed copy admitted", '                and _read_capped(path, LEASE_CREDENTIAL_MAX_BYTES) == reg_bytes:', '                and False:'),
 ("registered file not exempted by path", '        if rel == reg:\n            continue', '        if False:\n            continue'),
]
def run(mod):
    tt.pf = mod
    try:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(tt.TestLeasePostflight)
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
