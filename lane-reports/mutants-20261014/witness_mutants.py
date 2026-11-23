import os, sys, unittest, io
from unittest import mock
from pathlib import Path
T = str(Path(__file__).resolve().parents[2] / "evals/gap-study-4/tests")
sys.path.insert(0, T); sys.path.insert(0, os.path.dirname(T))
sys.dont_write_bytecode = True
import test_scan_witness as tw
from box import scan_record as sr
real_w, real_rep = sr._witness, sr._replacements
def nocheck(path, before, after, reps):
    return {"schema": 1, "original_sha256": sr._sha(before), "published_sha256": sr._sha(after),
            "original_bytes": len(before), "published_bytes": len(after), "replacements": reps}
mutants = {
 "no spans recorded (+ rebuild check off)": [("_replacements", lambda b, m, n: []), ("_witness", nocheck)],
 "line offsets off by one (+ rebuild check off)": [("_line_offsets", lambda d: [0 for _ in sr._lines(d)]), ("_witness", nocheck)],
 "replacement ids swapped": [("REPLACEMENT_IDS", {"token": "mask-key-v1", "key": "mask-token-v1", "email": "mask-email-v1"})],
 "published sha = original sha": [("_witness", lambda p, b, a, r: dict(real_w(p, b, a, r), published_sha256=sr._sha(b)))],
 "arbitrary replacement id accepted": [("replacement_marker", lambda rid: sr.MARKERS.get(rid.split("-")[1], rid).encode())],
 "spans recorded for refused JSON line": [("_replacements", lambda b, m, n: real_rep(b, m, n) or ([{"start":1,"end":2,"kind":"token","replacement_id":"mask-token-v1"}] if b.startswith(b'"') else []))],
 "witness dropped for unchanged files": [("_witness", lambda p, b, a, r: real_w(p, b, a, r) if r else None)],
}
for name, patches in mutants.items():
    ps = [mock.patch.object(sr, a, v) for a, v in patches]
    for p in ps: p.start()
    try:
        r = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(unittest.defaultTestLoader.loadTestsFromModule(tw))
    finally:
        for p in ps: p.stop()
    bad = len(r.failures) + len(r.errors)
    print(("RED  " if bad else "ALIVE"), f"{bad}/{r.testsRun}", name)
