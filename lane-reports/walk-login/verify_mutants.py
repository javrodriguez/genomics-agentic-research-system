"""Mutants of verify_walk_login.py's paste checks (review-walk-token W-2), each removed alone, against
test_walk_login_scripts.py. The script runs as a subprocess, so each mutant is a temporary copy beside it."""
import io, os, shutil, sys, tempfile, unittest
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.dont_write_bytecode = True
import test_walk_login_scripts as tt
SRC = (HERE / "verify_walk_login.py").read_text()
MUTANTS = [
 ("'=' unchecked", '''        bad["value contains '='"] = b"=" in value''', '''        bad["value contains '='"] = False'''),
 ("double paste unchecked", '''        bad["value pasted twice"] = n > 0 and n % 2 == 0 and value[:n // 2] == value[n // 2:]''', '''        bad["value pasted twice"] = False'''),
 ("name prefix unchecked", '''        bad["value starts with the variable name"] = value.startswith(b"CLAUDE_CODE_OAUTH_TOKEN")''', '''        bad["value starts with the variable name"] = False'''),
 ("paste checks ignored in the result", '''        ok = ok and not v''', '''        ok = ok'''),
]
def run(folder):
    tt.HERE = folder
    try:
        return unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(tt.WalkToken))
    finally:
        tt.HERE = HERE
c = run(HERE); print("control", len(c.failures) + len(c.errors), "of", c.testsRun)
assert not (c.failures or c.errors)
alive = []
for name, old, new in MUTANTS:
    assert SRC.count(old) == 1, name
    d = Path(tempfile.mkdtemp(prefix="vm-"))
    shutil.copy(HERE / "prepare_walk_login.py", d)
    (d / "verify_walk_login.py").write_text(SRC.replace(old, new))
    r = run(d); bad = len(r.failures) + len(r.errors)
    shutil.rmtree(d)
    print(("RED  " if bad else "ALIVE"), f"{bad}/{r.testsRun}", name)
    if not bad: alive.append(name)
print("ALIVE:", alive or "none")
