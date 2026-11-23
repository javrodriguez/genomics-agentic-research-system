"""Data and binding mutants for the two environment-name sweeps (the review of 06775d56^..bea73659, glitch-06, 14 Oct
2026) against test_run_take.TestCodexBinarySweep and TestGeminiPackageSweep. In memory: a committed record is handed to
the tests changed through a patched open(); run_take's tuples are patched to match, so only the bindings can catch it."""
import builtins, io, json, os, sys, unittest
from pathlib import Path
from unittest import mock
T = str(Path(__file__).resolve().parents[3] / "evals/gap-study-4/tests")
sys.path.insert(0, T); sys.dont_write_bytecode = True
import test_run_take as tt
rt = tt.rt
PR = tt.SWEEP_DIR
real_open = builtins.open
def load(name):
    with real_open(os.path.join(PR, name), encoding="utf-8") as fh:
        return json.load(fh)
def dump(doc):
    return json.dumps(doc, indent=1, sort_keys=True) + "\n"
def relabel(arm, name, field):
    doc = load(f"{arm}-env-name-classification-20261014.json")
    for r in doc["rows"]:
        if r.get(field) == name:
            r["class"] = "harmless"
        for g in r.get("glued", ()):
            if g["name"] == name:
                g["class"] = "harmless"
    doc["refuse_if_present"] = [n for n in doc["refuse_if_present"] if n != name]
    return f"{arm}-env-name-classification-20261014.json", dump(doc), tuple(doc["refuse_if_present"])
def markers_sha_changed():
    p = os.path.join(tt._CLONE, "lane-reports", "live-box-evidence-2026-10-13", "codex-auth-binary-markers.json")
    with real_open(p, encoding="utf-8") as fh:
        doc = json.load(fh)
    sha = doc["sources"][0]["sha256"]
    doc["sources"][0]["sha256"] = sha[:16] + ("0" if sha[16] != "0" else "1") + sha[17:]
    return p, json.dumps(doc)
def run(files=None, patches=()):
    files = files or {}
    def opener(p, *a, **k):
        for name, text in files.items():
            if str(p).endswith(name):
                return io.BytesIO(text.encode()) if (a and "b" in a[0]) or "b" in k.get("mode", "") else io.StringIO(text)
        return real_open(p, *a, **k)
    s = unittest.TestSuite()
    for c in (tt.TestCodexBinarySweep, tt.TestGeminiPackageSweep):
        s.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(c))
    with mock.patch.object(builtins, "open", opener):
        stack = [mock.patch.object(*p) for p in patches]
        for m in stack: m.start()
        try:
            return unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(s)
        finally:
            for m in stack: m.stop()
c = run(); print("control", len(c.failures) + len(c.errors), "of", c.testsRun)
assert not (c.failures or c.errors), "the control is not clean"
alive = []
def report(name, r):
    if r is None:
        print("N/A  ", name, "(the binding it targets is absent from this test file)")
        return
    bad = len(r.failures) + len(r.errors)
    print(("RED  " if bad else "ALIVE"), f"{bad}/{r.testsRun}", name)
    if not bad: alive.append(name)
f, text, tup = relabel("gemini", "GOOGLE_CLOUD_PROJECT", "name")
entry = dict(rt.VENDOR_BILLING_ROUTE_VARIABLES, **{rt.GEMINI: tup})
report("the review's relabel: GOOGLE_CLOUD_PROJECT harmless, dropped everywhere",
       run({f: text}, [(rt, "GEMINI_PACKAGE_SWEEP_REFUSED", tup), (rt, "VENDOR_BILLING_ROUTE_VARIABLES", entry)]))
f, text, tup = relabel("codex", "SSL_CERT_FILE", "match")
report("a glued trust-store name relabelled harmless and dropped",
       run({f: text}, [(rt, "CODEX_BINARY_SWEEP_REFUSED", tup)]))
f, text, tup = relabel("codex", "CODEX_AUTHAPI_BASE_URL", "match")
report("a Codex route relabelled harmless and dropped",
       run({f: text}, [(rt, "CODEX_BINARY_SWEEP_REFUSED", tup)]))
report("the Codex sweep bound to another image", run(patches=[(tt, "_lock_image", lambda arm: "sha256:" + "0" * 64)])
       if hasattr(tt, "_lock_image") else None)
p, text = markers_sha_changed()
report("the binary sha256 differing after its first 16 characters", run({os.path.basename(p): text}))
print("ALIVE:", alive or "none")
