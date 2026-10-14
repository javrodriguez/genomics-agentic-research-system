"""Mutants of the P-2 memory caps against test_live_box.MemoryCaps (in memory; nothing on disk changes)."""
import io, sys, types, unittest
from pathlib import Path
T = str(Path(__file__).resolve().parents[3] / "evals/gap-study-4/tests")
sys.path.insert(0, T); sys.dont_write_bytecode = True
import test_live_box as tl
MUTANTS = [
 ("sidecar", "sidecar uncapped", '"--security-opt", "no-new-privileges", "--memory", str(MEMORY_BYTES),', '"--security-opt", "no-new-privileges",'),
 ("sidecar", "sidecar cap 1 GiB", "MEMORY_BYTES = 512 * 1024 * 1024", "MEMORY_BYTES = 1024 * 1024 * 1024"),
 ("sidecar", "flag not in the closed list", '"--security-opt": True, "--memory": True, "--mount": True}', '"--security-opt": True, "--mount": True}'),
 ("rt", "proxy uncapped", '"--security-opt", "no-new-privileges", "--memory", str(PROXY_MEMORY_BYTES),', '"--security-opt", "no-new-privileges",'),
 ("rt", "proxy cap after the image", 'proxy.image, *proxy.command]', 'proxy.image, *proxy.command][:0] or [RUNTIME_CLIENT]'),
]
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
