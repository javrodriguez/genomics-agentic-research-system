"""Box lane, 14 Oct 2026: source-level in-memory mutants of the sidecar's NUL framing and new-folder rescan.
Each must turn a test red in tests/test_live_box.py. Run: /usr/local/bin/python3.13 -B <this file> after a light gate."""
import io, sys, types, unittest
from pathlib import Path
T = Path(__file__).resolve().parents[2] / "evals/gap-study-4/tests"
sys.path.insert(0, str(T)); sys.dont_write_bytecode = True
import test_live_box as tl
sc = tl.sidecar
SRC = open(sc.__file__).read()
mutants = [
 ("NUL framing replaced by a '|' split", 'if sep == b"\\0":', 'if False:'),
 ("wrong field count accepted", 'if len(rec) != len(fmt["fields"]):', 'if False:'),
 ("real parent not required", 'if not _real_dir(self.run_tree, _parent(p)):', 'if False:'),
 ("rescan on any CREATE", 'if "CREATE" in names and "ISDIR" in names and isinstance(ev.path, str):', 'if "CREATE" in names and isinstance(ev.path, str):'),
 ("every path beneath reported", "                os.lstat(os.path.join(self.run_tree, p))", "                pass"),
 ("stat follows the last link", "os.lstat(os.path.join(self.run_tree, p))", "os.stat(os.path.join(self.run_tree, p))"),
 ("found written as an access", '_append_line(self._ev(FOUND), {"at": at, "path": path, "source": FOUND_SOURCE})', '_append_line(self._ev(ACCESS), {"at": at, "path": path, "op": "modify"})'),
]
for name, old, new in mutants:
    assert SRC.count(old) == 1, name
    mod = types.ModuleType(sc.__name__); mod.__file__ = sc.__file__
    sys.modules[sc.__name__] = mod
    exec(compile(SRC.replace(old, new), sc.__file__, "exec"), mod.__dict__)
    orig = tl.sidecar; tl.sidecar = mod
    try:
        suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(c)
                                   for c in (tl.HostileNames, tl.LineFraming, tl.RescanReach, tl.NewFolderGap))
        r = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
    finally:
        tl.sidecar = orig; sys.modules[sc.__name__] = orig
    bad = len(r.failures) + len(r.errors)
    print(("RED  " if bad else "ALIVE"), f"{bad}/{r.testsRun}", name)
