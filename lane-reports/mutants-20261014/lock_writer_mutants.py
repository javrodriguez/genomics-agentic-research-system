"""Box lane, 14 Oct 2026: source-level in-memory mutants of ops/write_image_lock.py; each must turn
tests/test_write_image_lock.py red. Run: /usr/local/bin/python3.13 -B <this file> after a light gate."""
import io, sys, types, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
T = ROOT / "evals/gap-study-4/tests"
sys.path.insert(0, str(T)); sys.dont_write_bytecode = True
import test_write_image_lock as tw
SRC = (ROOT / "ops/write_image_lock.py").read_text()
mutants = [
 ("committed check off", '_need(data == head.stdout, f"{rel} differs from its committed bytes")', 'pass'),
 ("ancestor check off", '_need(is_ancestor(repo, commit), f"the build commit {commit} is not an ancestor of HEAD")', 'pass'),
 ("exit check off", '_need(row.get("exit") == 0 and type(row.get("exit")) is int, f"{image}\'s build did not exit 0")', 'pass'),
 ("label check off", '_need(row.get("label_problems") == [], f"{image}\'s labels did not check clean")', 'pass'),
 ("digest check off", '_need(isinstance(row.get(k), str) and DIGEST.fullmatch(row[k]) is not None, f"{image}\'s {k} is not a digest")', 'pass'),
 ("one row not required", '_need(len(rows) == 1, f"the record holds {len(rows)} rows for {image}, not one")', 'pass'),
 ("unresolved input allowed", '_need(field in inputs, f"{image}\'s record does not resolve {field}")', 'if field not in inputs: continue'),
 ("changed input allowed", '_need(have == want, f"{image}\'s {field} differs from the record\'s")', 'pass'),
 ("schema-1 lock not required", '_need(lock["schema"] == il.SCHEMA, "the lock is not the unfilled schema-1 lock")', 'pass'),
 ("changed-since-read not checked", '_need(fh.read() == read_bytes, "the lock changed since it was read")', 'pass'),
 ("record schema not checked", '_need(isinstance(record, dict) and record.get("schema") == RECORD_SCHEMA, "the build record is not schema 2")', 'pass'),
]
for name, old, new in mutants:
    assert SRC.count(old) == 1, name
    mod = types.ModuleType("write_image_lock_mutant")
    exec(compile(SRC.replace(old, new), "write_image_lock.py", "exec"), mod.__dict__)
    orig = tw.w; tw.w = mod
    try:
        r = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(unittest.defaultTestLoader.loadTestsFromModule(tw))
    finally:
        tw.w = orig
    bad = len(r.failures) + len(r.errors)
    print(("RED  " if bad else "ALIVE"), f"{bad}/{r.testsRun}", name)
