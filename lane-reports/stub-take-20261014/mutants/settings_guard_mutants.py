"""Mutants of box/settings_guard.py against tests/test_settings_guard.py (in memory)."""
import io, sys, types, unittest
from pathlib import Path
T = str(Path(__file__).resolve().parents[3] / "evals/gap-study-4/tests")
sys.path.insert(0, T); sys.dont_write_bytecode = True
import test_settings_guard as tt
sg = tt.sg
SRC = open(sg.__file__).read()
MUTANTS = [
 ("env allowed", 'FORBIDDEN_KEYS = ("env", "model",', 'FORBIDDEN_KEYS = ("model",'),
 ("local file ignored", 'SETTINGS_NAMES = ("settings.json", "settings.local.json")', 'SETTINGS_NAMES = ("settings.json",)'),
 ("forbidden keys not checked", "            if bad:\n", "            if False:\n"),
 ("link file followed", "            if not os.path.isfile(path) or os.path.islink(path) or st.st_size > MAX_BYTES:", "            if not os.path.isfile(path) or st.st_size > MAX_BYTES:"),
 ("claude link admitted", '            if d == ".claude" and os.path.islink(os.path.join(root, d)):', '            if False:'),
 ("new file admitted", '            if path not in base:\n                out.append(f"{path}: a settings file the run tree did not ship")', '            if path not in base:\n                pass'),
 ("hash not compared", '            elif kind != "file" or e.get("sha256") != base[path]:', '            elif kind != "file":'),
 ("removal admitted", '        if path not in entries:\n', '        if False:\n'),
 ("dir type unchecked", '        if CLAUDE_DIR.fullmatch(path) and kind != "dir":', '        if False:'),
 ("pattern too loose", 'SETTINGS_PATH = re.compile(r"(?:^|.*/)\\.claude/settings(?:\\.local)?\\.json")', 'SETTINGS_PATH = re.compile(r".*settings.*\\.json")'),
]
def run(mod):
    tt.sg = mod
    try:
        return unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(unittest.defaultTestLoader.loadTestsFromModule(tt))
    finally:
        tt.sg = sg
c = run(sg); print("control", len(c.failures) + len(c.errors), "of", c.testsRun)
alive = []
for name, old, new in MUTANTS:
    assert SRC.count(old) == 1, name
    mod = types.ModuleType(sg.__name__); mod.__file__ = sg.__file__
    exec(compile(SRC.replace(old, new), sg.__file__, "exec"), mod.__dict__)
    r = run(mod); bad = len(r.failures) + len(r.errors)
    print(("RED  " if bad else "ALIVE"), f"{bad}/{r.testsRun}", name)
    if not bad: alive.append(name)
print("ALIVE:", alive or "none")
