"""Mutants of box/run_take.py's walk-token road (check_login_place, the --bare refusal) against
tests/test_run_take.TestWalkLoginPlace (in memory; nothing on disk changes). Each removes one clause alone."""
import io, sys, types, unittest
from pathlib import Path
T = str(Path(__file__).resolve().parents[3] / "evals/gap-study-4/tests")
sys.path.insert(0, T); sys.dont_write_bytecode = True
import test_run_take as tt
rt = tt.rt
SRC = open(rt.__file__).read()
MUTANTS = [
 ("run tree admitted", '    if _inside(os.path.normpath(path), _abs_path(run_tree, "run_tree")):\n        raise LoginRefused(f"{path}: the login file must sit outside the run tree")', '    if False:\n        raise LoginRefused(f"{path}: the login file must sit outside the run tree")'),
 ("second link admitted", '    if st.st_nlink != 1:\n        raise LoginRefused(f"{path}: the login file must have exactly one link")\n    if stat.S_ISLNK(pst', '    if False:\n        raise LoginRefused(f"{path}: the login file must have exactly one link")\n    if stat.S_ISLNK(pst'),
 ("link folder admitted", '    if stat.S_ISLNK(pst.st_mode) or not os.path.isdir(parent):', '    if not os.path.isdir(parent):'),
 ("folder mode unchecked", 'stat.S_IMODE(pst.st_mode) != 0o700 or pst.st_uid', 'pst.st_uid'),
 ("folder group bits admitted", 'stat.S_IMODE(pst.st_mode) != 0o700', 'stat.S_IMODE(pst.st_mode) & 0o007'),
 ("place not checked by exec", '    check_login_place(login_file, run_tree)\n', ''),
 ("bare admitted", '    if [a for a in _flag_tokens(inner) if a == CLAUDE_BARE_FLAG or a.startswith(CLAUDE_BARE_FLAG + "=")]:', '    if False:'),
]
def run(mod):
    tt.rt = mod
    try:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(tt.TestWalkLoginPlace)
        return unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
    finally:
        tt.rt = rt
c = run(rt); print("control", len(c.failures) + len(c.errors), "of", c.testsRun)
assert not (c.failures or c.errors), "the control is not clean"
alive = []
for name, old, new in MUTANTS:
    assert SRC.count(old) == 1, name
    mod = types.ModuleType(rt.__name__); mod.__file__ = rt.__file__
    sys.modules[mod.__name__] = mod
    try:
        exec(compile(SRC.replace(old, new), rt.__file__, "exec"), mod.__dict__)
        r = run(mod)
    finally:
        sys.modules[rt.__name__] = rt
    bad = len(r.failures) + len(r.errors)
    print(("RED  " if bad else "ALIVE"), f"{bad}/{r.testsRun}", name)
    if not bad: alive.append(name)
print("ALIVE:", alive or "none")
