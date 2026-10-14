"""Mutants of the Codex row (glitch-06's rulings 1 and 3, 14 Oct 2026): box/run_take.py's row, LOGIN_VARIABLE,
read_login and billing-route names, and box/scan_record.py's read_login, against test_run_take.TestCodexRow and
test_scan_record.TestLeaseTokens.test_a_codex_row_has_no_environment_login (in memory; nothing on disk changes). A
mutant module that cannot even load counts red (the module guards itself)."""
import io, sys, types, unittest
from pathlib import Path
from unittest import mock
T = str(Path(__file__).resolve().parents[3] / "evals/gap-study-4/tests")
sys.path.insert(0, T); sys.dont_write_bytecode = True
import test_run_take as trt
import test_scan_record as tsr
RT, SR = trt.rt, tsr.sr
SRC = {"rt": open(RT.__file__).read(), "sr": open(SR.__file__).read()}
MUTANTS = [
 ("rt", "the Codex row keeps CODEX_API_KEY", '"CODEX_HOME": CONFIG_MOUNT},     # no credential', '"CODEX_HOME": CONFIG_MOUNT, "CODEX_API_KEY": CREDENTIAL},     # no credential'),
 ("rt", "LOGIN_VARIABLE[codex] not NO_LOGIN", "LOGIN_VARIABLE[CODEX] = NO_LOGIN\n", 'LOGIN_VARIABLE[CODEX] = "CODEX_API_KEY"\n'),
 ("rt", "read_login reads a Codex row", '    if name == NO_LOGIN:\n        raise LoginRefused("a Codex row', '    if False:\n        raise LoginRefused("a Codex row'),
 ("rt", "a route name dropped", '            "OPENAI_ORGANIZATION",                     # matches[40]: beside the OpenAI-Organization header\n', ''),
 ("rt", "route names never refused", "        if not _is_pending(extra):\n            names |= set(extra)", "        if not _is_pending(extra):\n            pass"),
 ("rt", "OPENAI_API_KEY admitted for codex", 'VENDOR_KEY_VARIABLES = ("CODEX_API_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY")', 'VENDOR_KEY_VARIABLES = ("CODEX_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY")'),
 ("sr", "scan_record reads a Codex row by its own rule", '    if name == "-":            # run_take.NO_LOGIN', '    if False:            # run_take.NO_LOGIN'),
]
def suite():
    s = unittest.TestSuite()
    s.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(trt.TestCodexRow))
    s.addTest(tsr.TestLeaseTokens("test_a_codex_row_has_no_environment_login"))
    return s
def run(rt=RT, sr=SR):
    with mock.patch.object(trt, "rt", rt), mock.patch.object(tsr, "sr", sr):
        return unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite())
c = run(); print("control", len(c.failures) + len(c.errors), "of", c.testsRun)
assert not (c.failures or c.errors), "the control is not clean"
alive = []
for key, name, old, new in MUTANTS:
    assert SRC[key].count(old) == 1, name
    base = RT if key == "rt" else SR
    mod = types.ModuleType(base.__name__); mod.__file__ = base.__file__
    try:
        exec(compile(SRC[key].replace(old, new), base.__file__, "exec"), mod.__dict__)
    except Exception as e:  # noqa: BLE001
        print("RED  ", "load", name, f"({type(e).__name__}: {str(e)[:60]})"); continue
    r = run(rt=mod) if key == "rt" else run(sr=mod)
    bad = len(r.failures) + len(r.errors)
    print(("RED  " if bad else "ALIVE"), f"{bad}/{r.testsRun}", name)
    if not bad: alive.append(name)
print("ALIVE:", alive or "none")
