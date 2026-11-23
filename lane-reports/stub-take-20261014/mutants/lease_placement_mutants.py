"""Mutants of box/run_take.py's Codex lease gate and place_lease (glitch-06, 14 Oct 2026), one per refusal branch,
against tests/test_run_take.TestLeasePlacement (in memory; nothing on disk changes). The branches for an OSError in
the middle of the copy (the source read, the write, the read-back lstat) have no mutant: no test reaches them
without a race, and each already refuses by rule."""
import io, sys, types, unittest
from pathlib import Path
T = str(Path(__file__).resolve().parents[3] / "evals/gap-study-4/tests")
sys.path.insert(0, T); sys.dont_write_bytecode = True
import test_run_take as tt
rt = tt.rt
SRC = open(rt.__file__).read()
R = "        raise LoginRefused(f\""
MUTANTS = [
 ("the gate admits", "    if CODEX_SUBSCRIPTION_READY is not True:\n        raise NotReady", "    if False:\n        raise NotReady"),
 ("a relative source admitted", "    if not isinstance(lease_src, str) or not os.path.isabs(lease_src):\n        raise", "    if not isinstance(lease_src, str):\n        raise"),
 ("a missing source crashes", "    except OSError:\n        raise LoginRefused(f\"{lease_src}: the lease file does not exist", "    except ZeroDivisionError:\n        raise LoginRefused(f\"{lease_src}: the lease file does not exist"),
 ("a linked source admitted", "    if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):\n        raise LoginRefused(f\"{lease_src}", "    if False:\n        raise LoginRefused(f\"{lease_src}"),
 ("a source with two links admitted", "    if st.st_nlink != 1:\n        raise LoginRefused(f\"{lease_src}", "    if False:\n        raise LoginRefused(f\"{lease_src}"),
 ("any source mode admitted", "    if stat.S_IMODE(st.st_mode) != 0o600:\n        raise LoginRefused(f\"{lease_src}", "    if False:\n        raise LoginRefused(f\"{lease_src}"),
 ("any source owner admitted", "    if st.st_uid != os.getuid():\n        raise LoginRefused(f\"{lease_src}", "    if False:\n        raise LoginRefused(f\"{lease_src}"),
 ("a source in a repository admitted", "    if not outside_every_repository(lease_src):", "    if False:"),
 ("an oversize source admitted", "    if len(data) > LEASE_MAX_BYTES:\n        raise LoginRefused(f\"{lease_src}", "    if False:\n        raise LoginRefused(f\"{lease_src}"),
 ("an empty source admitted", "    if not data:", "    if False:"),
 ("a relative folder admitted", "    if not isinstance(config_dir, str) or not os.path.isabs(config_dir):", "    if not isinstance(config_dir, str):"),
 ("a missing folder crashes", "    except OSError:\n        raise LoginRefused(f\"{config_dir}: the config folder does not exist", "    except ZeroDivisionError:\n        raise LoginRefused(f\"{config_dir}: the config folder does not exist"),
 ("a linked folder admitted", "    if stat.S_ISLNK(cst.st_mode) or not os.path.isdir(config_dir):", "    if False:"),
 ("any folder mode or owner admitted", "    if stat.S_IMODE(cst.st_mode) != 0o700 or cst.st_uid != os.getuid():", "    if False:"),
 ("a folder in a repository admitted", "    if not outside_every_repository(config_dir):", "    if False:"),
 ("an existing auth.json overwritten", "    if os.path.lexists(dst):", "    if False:"),
 ("a placed non-regular or linked file admitted", "    if stat.S_ISLNK(pst.st_mode) or not stat.S_ISREG(pst.st_mode) or pst.st_nlink != 1:", "    if False:"),
 ("a narrowed mode admitted", "    if stat.S_IMODE(pst.st_mode) != 0o600:", "    if False:"),
 ("a placed file of another owner admitted", "    if pst.st_uid != os.getuid():", "    if False:"),
 ("a short placement admitted", "    if pst.st_size != len(data):", "    if False:"),
]
def run(mod):
    tt.rt = mod
    try:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(tt.TestLeasePlacement)
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
