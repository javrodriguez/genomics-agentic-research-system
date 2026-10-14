"""Mutants of box/ownership.py against tests/test_ownership.py (in memory; nothing on disk changes)."""
import io, sys, types, unittest
from pathlib import Path
T = str(Path(__file__).resolve().parents[3] / "evals/gap-study-4/tests")
sys.path.insert(0, T); sys.dont_write_bytecode = True
import test_ownership as tt
ow = tt.ow
SRC = open(ow.__file__).read()
MUTANTS = [
 ("grant to keepalive", '("run_tree", run_take._abs_path(run_tree, "run_tree"), AGENT_UID)', '("run_tree", run_take._abs_path(run_tree, "run_tree"), 10003)'),
 ("evidence to agent", '("evidence_dir", run_take._abs_path(evidence_dir, "evidence_dir"), WATCHER_UID)', '("evidence_dir", run_take._abs_path(evidence_dir, "evidence_dir"), AGENT_UID)'),
 ("grant goes on after a failure", '            raise OwnershipError(f"grant-{name} failed', '            pass\n            if False: raise OwnershipError(f"grant-{name} failed'),
 ("restore ignores present containers", "    if still:\n        raise OwnershipError(\"restore refused", "    if False:\n        raise OwnershipError(\"restore refused"),
 ("restore not verified", "        problems += owner_problems(path, os.getuid())", "        pass"),
 ("restore to the agent", "own_argv(image, path, HOST_UID)", "own_argv(image, path, AGENT_UID)"),
 ("links followed", "    os.chown(name,uid,uid,dir_fd=fd,follow_symlinks=False)", "    os.chown(name,uid,uid,dir_fd=fd,follow_symlinks=True)"),
 ("specials admitted", 'raise RuntimeError("nonregular refused")', 'pass'),
 ("link check skipped", "        if os.path.islink(p) or not os.path.isdir(p):", "        if not os.path.isdir(p):"),
 ("overlap admitted", "            if run_take._inside(p1, p2) or run_take._inside(p2, p1):", "            if False:"),
 ("cfg repo check off", "    if not run_take.outside_every_repository(out[1][1]):", "    if False:"),
 ("extra capability", 'CAPS = ("CHOWN", "DAC_OVERRIDE")', 'CAPS = ("CHOWN", "DAC_OVERRIDE", "SYS_ADMIN")'),
 ("network on", '"--network", "none", "--user", "0:0"', '"--network", "bridge", "--user", "0:0"'),
]
def run(mod):
    tt.ow = mod
    try:
        return unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(unittest.defaultTestLoader.loadTestsFromModule(tt))
    finally:
        tt.ow = ow
c = run(ow); print("control", len(c.failures) + len(c.errors), "of", c.testsRun)
alive = []
for name, old, new in MUTANTS:
    assert SRC.count(old) == 1, name
    mod = types.ModuleType(ow.__name__); mod.__file__ = ow.__file__
    exec(compile(SRC.replace(old, new), ow.__file__, "exec"), mod.__dict__)
    r = run(mod); bad = len(r.failures) + len(r.errors)
    print(("RED  " if bad else "ALIVE"), f"{bad}/{r.testsRun}", name)
    if not bad: alive.append(name)
print("ALIVE:", alive or "none")
