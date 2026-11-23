"""Mutants of box/preflight.py's Codex lease postflight (glitch-06, 14 Oct 2026), one per refusal branch, against
tests/test_preflight.TestLeasePostflight (in memory; nothing on disk changes)."""
import io, signal, sys, types, unittest
from pathlib import Path
T = str(Path(__file__).resolve().parents[3] / "evals/gap-study-4/tests")
sys.path.insert(0, T); sys.dont_write_bytecode = True
import test_preflight as tt
pf = tt.pf
SRC = open(pf.__file__).read()
MUTANTS = [
 ("registered path may be a link", '        if stat.S_ISLNK(st.st_mode):\n            problems.append(f"{reg}: the registered', '        if False:\n            problems.append(f"{reg}: the registered'),
 ("registered path may be non-regular", '        elif not stat.S_ISREG(st.st_mode):', '        elif False:'),
 ("oversize admitted", '            if reg_bytes is None:', '            if False:'),
 ("links to it or to a folder above it admitted", '            if os.path.commonpath([real, reg_real]) == real \\\n                    or name', '            if name'),
 ("credential-named links admitted", '                    or name in _credential_names() or CREDENTIAL_LIKE.search(name):', '                    :'),
 ("unreadable candidate raises", '            except OSError:\n                problems.append(f"{rel}: unreadable', '            except ZeroDivisionError:\n                problems.append(f"{rel}: unreadable'),
 ("second hard link admitted", '        elif st.st_nlink != 1:', '        elif False:'),
 ("any mode admitted", '        elif stat.S_IMODE(st.st_mode) != 0o600:', '        elif False:'),
 ("any owner admitted", '        elif st.st_uid != os.getuid():', '        elif False:'),
 ("second credential-shaped file admitted", '        if name in _credential_names() or CREDENTIAL_LIKE.search(name):\n            problems.append(f"{rel}: a credential-shaped', '        if False:\n            problems.append(f"{rel}: a credential-shaped'),
 ("renamed copy admitted", '            if same:', '            if False:'),
 ("registered file not exempted by path", '        if rel == reg:\n            continue', '        if False:\n            continue'),
 ("the read not bound to the check", '    if (opened.st_dev, opened.st_ino, opened.st_nlink, opened.st_mode, opened.st_uid) != \\\n            (checked.st_dev, checked.st_ino, checked.st_nlink, checked.st_mode, checked.st_uid):', '    if False:'),
 ("device and inode not compared", '    if (opened.st_dev, opened.st_ino, opened.st_nlink, opened.st_mode, opened.st_uid) != \\\n            (checked.st_dev, checked.st_ino, checked.st_nlink, checked.st_mode, checked.st_uid):', '    if (opened.st_nlink, opened.st_mode, opened.st_uid) != \\\n            (checked.st_nlink, checked.st_mode, checked.st_uid):'),
 ("registered unreadable raises", '            except OSError:\n                problems.append(f"{reg}: the registered credential is unreadable', '            except ZeroDivisionError:\n                problems.append(f"{reg}: the registered credential is unreadable'),
 ("absent credential admitted", '        problems.append(f"{reg}: absent; the lease home must hold exactly one registered credential file")', '        pass'),
]
HUNG = []


def run(mod):
    tt.pf = mod
    # a mutant that hangs (a FIFO opened blocking once the non-regular refusal is gone) is red, not a stalled run
    def hung(*_):
        HUNG.append(True)
        raise TimeoutError("the mutant hung")
    old = signal.signal(signal.SIGALRM, hung)
    signal.alarm(60)
    try:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(tt.TestLeasePostflight)
        return unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)
        tt.pf = pf
c = run(pf); print("control", len(c.failures) + len(c.errors), "of", c.testsRun)
assert not (c.failures or c.errors), "the control is not clean"
alive = []
for name, old, new in MUTANTS:
    assert SRC.count(old) == 1, name
    mod = types.ModuleType(pf.__name__); mod.__file__ = pf.__file__
    exec(compile(SRC.replace(old, new), pf.__file__, "exec"), mod.__dict__)
    r = run(mod); bad = len(r.failures) + len(r.errors)
    hang = bool(HUNG); HUNG.clear()
    print(("RED  " if bad else "ALIVE"), f"{bad}/{r.testsRun}", name, "(hung, stopped at 60 s)" if hang else "")
    if not bad: alive.append(name)
print("ALIVE:", alive or "none")
