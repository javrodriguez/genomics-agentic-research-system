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
 ("name prefix unchecked", '''        bad["value starts with the variable name"] = value.startswith(prefix[:-1])''', '''        bad["value starts with the variable name"] = False'''),
 ("quotes unchecked", '''        bad["quote in the value"] = b'"' in value or b"'" in value''', '''        bad["quote in the value"] = False'''),
 ("stray non-ASCII unchecked", '''            if ord(ch) > 0x7e:''', '''            if False:'''),
 ("stray named by the character, not its name", '''                stray = unicodedata.name(ch, f"U+{ord(ch):04X}") if ch != "\\ufffd" else "a byte that is not UTF-8"''', '''                stray = ch'''),
 ("the Gemini account unknown", '''            "r4-g": ("gemini-walk-login", b"GEMINI_API_KEY=")}''', '''            }'''),
 ("paste checks ignored in the result", '''        ok = ok and not v''', '''        ok = ok'''),
]
def run(folder):
    tt.HERE = folder
    try:
        s = unittest.TestSuite()
        for c in (tt.WalkToken, tt.GeminiKey):
            s.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(c))
        return unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(s)
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
print("EQUIVALENT (named, no mutant): the stray non-ASCII line's own result gate, since a non-ASCII byte also fails "
      "'format ok' (bytes 0x21-0x7e only), so dropping that gate alone changes no result")
print("ALIVE:", alive or "none")
