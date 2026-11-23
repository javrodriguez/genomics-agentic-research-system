import io, sys, types, unittest
from pathlib import Path
T = str(Path(__file__).resolve().parents[2] / "evals/gap-study-4/tests")
sys.path.insert(0, T); sys.dont_write_bytecode = True
import test_endstate as te
es = te.es
SRC = open(es.__file__).read()
mutants = [
 ("discoveries merged into accesses", "        self._found = [dict(f) for f in found]", "        self._found = [dict(f) for f in found]\n        self._access += [{'at': f['at'], 'path': f['path'], 'op': 'modify'} for f in found]"),
 ("any source admitted", 'or f["source"] not in FOUND_SOURCES', 'or False'),
 ("found.jsonl not admitted", "unknown = [n for n in names if n not in FILES + OPTIONAL_FILES + FOLDERS]", "unknown = [n for n in names if n not in FILES + FOLDERS]"),
 ("watched check off", 'if self._watched is not None and f["path"] not in {self.tree(w) for w in self._watched}:', 'if False:'),
 ("health not required", "        self._require_watched()\n        out = []", "        out = []"),
 ("late always False", "late = w[0] == IN_TURN and f[\"at\"] > self.turns[w[1] - 1].ended_at", "late = False"),
 ("path filter ignored", "if (path is None or f[\"path\"] == path) and", "if True and"),
]
for name, old, new in mutants:
    assert SRC.count(old) == 1, name
    mod = types.ModuleType(es.__name__); mod.__file__ = es.__file__
    exec(compile(SRC.replace(old, new), es.__file__, "exec"), mod.__dict__)
    orig = te.es; te.es = mod
    try:
        r = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(unittest.defaultTestLoader.loadTestsFromTestCase(te.Discoveries))
    finally:
        te.es = orig
    bad = len(r.failures) + len(r.errors)
    print(("RED  " if bad else "ALIVE"), f"{bad}/{r.testsRun}", name)
