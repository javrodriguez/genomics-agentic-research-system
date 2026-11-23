"""Mutants of the P-2 memory caps against test_live_box.MemoryCaps (in memory; nothing on disk changes)."""
import io, sys, types, unittest
from pathlib import Path
T = str(Path(__file__).resolve().parents[3] / "evals/gap-study-4/tests")
sys.path.insert(0, T); sys.dont_write_bytecode = True
import test_live_box as tl
MUTANTS = [
 ("rt", "sidecar uncapped", 'return argv[:2] + ["--memory", str(SIDECAR_MEMORY_BYTES)] + argv[2:]', 'return argv'),
 ("rt", "sidecar cap 1 GiB", "SIDECAR_MEMORY_BYTES = 512 * 1024 * 1024", "SIDECAR_MEMORY_BYTES = 1024 * 1024 * 1024"),
 ("rt", "caller's own memory admitted", ' or any(a.startswith("--memory") or a.startswith("-m") for a in argv):', ':'),
 ("rt", "caller's -m admitted", ' or any(a.startswith("--memory") or a.startswith("-m") for a in argv):', ' or any(a.startswith("--memory") for a in argv):'),
 ("rt", "launch skips the cap", '"sidecar-create", sidecar_create_argv(sidecar), env)', '"sidecar-create", list(sidecar.create_argv), env)'),
 ("rt", "proxy uncapped", '"--security-opt", "no-new-privileges", "--memory", str(PROXY_MEMORY_BYTES),', '"--security-opt", "no-new-privileges",'),
 ("rt", "proxy cap 1 GiB", "PROXY_MEMORY_BYTES = 512 * 1024 * 1024", "PROXY_MEMORY_BYTES = 1024 * 1024 * 1024"),
]
c = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(unittest.defaultTestLoader.loadTestsFromTestCase(tl.MemoryCaps))
print("control", len(c.failures) + len(c.errors), "of", c.testsRun)
alive = []
for attr, name, old, new in MUTANTS:
    orig = getattr(tl, attr)
    src = open(orig.__file__).read()
    assert src.count(old) == 1, name
    mod = types.ModuleType(orig.__name__); mod.__file__ = orig.__file__
    exec(compile(src.replace(old, new), orig.__file__, "exec"), mod.__dict__)
    setattr(tl, attr, mod)
    try:
        r = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(unittest.defaultTestLoader.loadTestsFromTestCase(tl.MemoryCaps))
    finally:
        setattr(tl, attr, orig)
    bad = len(r.failures) + len(r.errors)
    print(("RED  " if bad else "ALIVE"), f"{bad}/{r.testsRun}", name)
    if not bad: alive.append(name)
print("ALIVE:", alive or "none")
