"""B-6: the inspect-Cmd equality guard removed in memory must leave the new break uncaught."""
import sys, types
from pathlib import Path
T = str(Path(__file__).resolve().parents[2] / "evals/gap-study-4/tests")
sys.path.insert(0, T); sys.dont_write_bytecode = True
import test_preflight as tp
pf = tp.pf
brk = dict(tp.BREAKS["sidecar-isolated"])["inspect-cmd-reordered"]
def caught():
    w = tp.World(tp.rt.CLAUDE_CODE); raw = w.raw(); brk(raw, w)
    with tp.filled():
        rec = w.evaluate(raw)
    return [c for c in rec["checks"] if c["id"] == "sidecar-isolated"][0]
tp.setUpModule() if hasattr(tp, "setUpModule") else None
c = caught(); print("real:", c["ok"], str(c.get("detail", c))[:160])
src = open(pf.__file__).read()
old = '_need(inspected.get("Config", {}).get("Cmd") == exp["cmd"], "the sidecar command differs in order or content")'
assert src.count(old) == 1
code = compile(src.replace(old, "pass"), pf.__file__, "exec")
saved = dict(pf.__dict__)
exec(code, pf.__dict__)
pf.CHECKS["sidecar-isolated"] = pf.__dict__[saved["CHECKS"]["sidecar-isolated"].__name__] if False else pf.CHECKS["sidecar-isolated"]
c2 = caught(); print("mutant:", "RED (uncaught)" if c2["ok"] else "still caught: " + str(c2.get("detail", c2))[:160])
