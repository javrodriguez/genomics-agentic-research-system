"""Mutants of box/stub_take.py against tests/test_stub_take.py (in memory; nothing on disk is changed).
Each mutant's source is exec'd into a fresh module that replaces the test module's `st`; RED means a test failed."""
import io, sys, types, unittest
from pathlib import Path
T = str(Path(__file__).resolve().parents[3] / "evals/gap-study-4/tests")
sys.path.insert(0, T); sys.dont_write_bytecode = True
import test_stub_take as tt
st = tt.st
SRC = open(st.__file__).read()
MUTANTS = [
 ("short ids admitted", 'IMAGE_ID = re.compile(r"sha256:[0-9a-f]{64}")', 'IMAGE_ID = re.compile(r"sha256:[0-9a-f]{12,64}")'),
 ("output prefix rule off", "    if not os.path.basename(folder).startswith(FOLDER_PREFIX):\n", "    if False:\n"),
 ("study record dirs rule off", "    if set(path.split(os.sep)) & set(STUDY_RECORD_DIRS):\n", "    if False:\n"),
 ("existing output overwritten", "    if os.path.lexists(path):\n        raise StubTakeRefused(\"the output already exists", "    if False:\n        raise StubTakeRefused(\"the output already exists"),
 ("lock ids not compared", '        if out[role]["image_id"] != images[role]:\n', "        if False:\n"),
 ("record may relabel itself", '    if set(doc) & {"record_kind", "not_a_study_record"}:\n', "    if False:\n"),
 ("mirror skips proxy-connect", '        run_take._step(runtime, launched, "proxy-connect",', '        (lambda *a: None)(runtime, launched, "proxy-connect",'),
 ("mirror compares inspects", '        run_take._inspect(runtime, launched, "take-inspect", launched.take_id, env)\n', '        preflight.inspect_mismatches(run_take._inspect(runtime, launched, "take-inspect", launched.take_id, env), {}, kind="take")\n'),
 ("turn runs at /", "    argv = run_take.agent_exec_argv(take_id, inner, workdir=run_tree)", "    argv = run_take.agent_exec_argv(take_id, inner, workdir=\"/\")"),
 ("cap_add from boot names", "    expect[\"cap_add\"] = list(sidecar_contract.BOOT_INSPECT_CAPABILITIES)", "    expect[\"cap_add\"] = list(sidecar_contract.BOOT_CAPABILITIES)"),
 ("launch never used", "    return not run_take._is_pending(run_take.INSPECT_STATUS)", "    return False"),
 ("main writes unlabelled", "    rec = _labelled(run_stub_take(a))", "    rec = run_stub_take(a)"),
 ("refusal after runtime", "    images = check_images({r: getattr(a, f\"{r}_image\") for r in IMAGE_ROLES})\n    output = check_output(a.output)\n    locks = load_locks(a.box, images)\n", "    Recorder()\n    images = check_images({r: getattr(a, f\"{r}_image\") for r in IMAGE_ROLES})\n    output = check_output(a.output)\n    locks = load_locks(a.box, images)\n"),
 ("main checks no ids", "    check_images({r: getattr(a, f\"{r}_image\") for r in IMAGE_ROLES})\n    output = check_output(a.output)\n    rec =", "    output = check_output(a.output)\n    Recorder()\n    rec ="),
]
def run(mod):
    tt.st = mod
    try:
        suite = unittest.defaultTestLoader.loadTestsFromModule(tt)
        return unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
    finally:
        tt.st = st
ctl = run(st); print("control", len(ctl.failures) + len(ctl.errors), "of", ctl.testsRun)
alive = []
for name, old, new in MUTANTS:
    assert SRC.count(old) == 1, name
    mod = types.ModuleType(st.__name__); mod.__file__ = st.__file__
    exec(compile(SRC.replace(old, new), st.__file__, "exec"), mod.__dict__)
    r = run(mod); bad = len(r.failures) + len(r.errors)
    print(("RED  " if bad else "ALIVE"), f"{bad}/{r.testsRun}", name)
    if not bad: alive.append(name)
print("ALIVE:", alive or "none")
