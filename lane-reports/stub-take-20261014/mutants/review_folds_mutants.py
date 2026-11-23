"""Mutants for the folds of the review of 6c21320b, 41428177 and 9d4bfd40 (glitch-06, 14 Oct 2026), one per new
branch, against test_run_take's TestReviewFolds41428177, TestNoLoginLauncher and TestLeasePlacement (in memory;
nothing on disk changes). A test that re-reads run_take.py's source from disk is handed the mutant's source."""
import builtins, io, sys, types, unittest
from pathlib import Path
from unittest import mock
T = str(Path(__file__).resolve().parents[3] / "evals/gap-study-4/tests")
sys.path.insert(0, T); sys.dont_write_bytecode = True
import test_run_take as tt
rt = tt.rt
SRC = open(rt.__file__).read()
EQUIVALENT = ("O_NOFOLLOW dropped alone: the exclusive create (O_EXCL) already refuses a link at the path, so no test "
              "can tell it apart; dropping both is the mutant below")
MUTANTS = [
 ("harness= optional again", "def launcher_argv(login: str, values: dict, inner, *, harness) -> list:", "def launcher_argv(login: str, values: dict, inner, *, harness=None) -> list:"),
 ("any named login admitted", "        if login != LOGIN_VARIABLE[harness]:\n            raise Refused(f\"{login} is not the login", "        if False:\n            raise Refused(f\"{login} is not the login"),
 ("another config home admitted", "        if other_homes:\n            raise Refused", "        if False:\n            raise Refused"),
 ("any value names admitted", "        if names != set(TAKE_ENV[CODEX]):\n            raise Refused", "        if False:\n            raise Refused"),
 ("a key name in the Codex row loads", "if _CODEX_ROW_KEYS:\n    raise RuntimeError", "if False:\n    raise RuntimeError"),
 ("a longer placement admitted (the review's >)", "    if pst.st_size != len(data):", "    if pst.st_size > len(data):"),
 ("a shorter placement admitted", "    if pst.st_size != len(data):", "    if pst.st_size < len(data):"),
 ("the create is not exclusive", "os.open(dst, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)", "os.open(dst, os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW, 0o600)"),
 ("the create neither exclusive nor no-follow", "os.open(dst, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)", "os.open(dst, os.O_WRONLY | os.O_CREAT, 0o600)"),
 ("ISSUERA not refused", '"CODEX_APP_SERVER_LOGIN_ISSUER", "CODEX_APP_SERVER_LOGIN_ISSUERA"),', '"CODEX_APP_SERVER_LOGIN_ISSUER"),'),
]
CLASSES = (tt.TestReviewFolds41428177, tt.TestNoLoginLauncher, tt.TestLeasePlacement, tt.TestCodexRow)
real_open = builtins.open
def run(mod, src):
    def opener(p, *a, **k):
        if str(p) == rt.__file__ and src is not None:
            return io.StringIO(src)
        return real_open(p, *a, **k)
    tt.rt = mod
    try:
        s = unittest.TestSuite()
        for c in CLASSES:
            s.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(c))
        with mock.patch.object(builtins, "open", opener):
            return unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(s)
    finally:
        tt.rt = rt
c = run(rt, None); print("control", len(c.failures) + len(c.errors), "of", c.testsRun)
assert not (c.failures or c.errors), "the control is not clean"
alive = []
for name, old, new in MUTANTS:
    assert SRC.count(old) == 1, name
    msrc = SRC.replace(old, new)
    mod = types.ModuleType(rt.__name__); mod.__file__ = rt.__file__
    try:
        with mock.patch.dict(sys.modules, {rt.__name__: mod}):
            exec(compile(msrc, rt.__file__, "exec"), mod.__dict__)
    except Exception as e:  # noqa: BLE001
        print("RED  ", "load", name, f"({type(e).__name__})"); continue
    r = run(mod, msrc); bad = len(r.failures) + len(r.errors)
    print(("RED  " if bad else "ALIVE"), f"{bad}/{r.testsRun}", name)
    if not bad: alive.append(name)
print("EQUIVALENT (named, no mutant):", EQUIVALENT)
print("ALIVE:", alive or "none")
