"""Mutants for the bypass ruling (not required in -p; glitch-06, 14 Oct 2026), in memory, against the adapter's and
run_take's tests. Each mutant must turn a suite red: the key re-added, and -p dropped (at the adapter, and at the
adapter and the box gate together, so the adapter's own -p assertion is shown to bind). The box gate's own mutants
(-p dropped, --bg admitted, the key re-added three ways) are in-suite: test_run_take.TestClaudeSettings. Run alone:
test_claude_code_adapter's module fixtures do not share a process with another test module."""
import contextlib, io, json, sys, unittest
from pathlib import Path
from unittest import mock
T = str(Path(__file__).resolve().parents[3] / "evals/gap-study-4/tests")
sys.path.insert(0, T); sys.dont_write_bytecode = True
import test_claude_code_adapter as tca
cca, rt = tca.cca, tca.rt
ORIG_ARGV, ORIG_GATE, ORIG_SETTINGS = cca.argv, rt.check_claude_settings, rt.claude_study_settings
KEY = "skipDangerousModePermissionPrompt"


def argv_without_p(line, **kw):
    out = ORIG_ARGV(line, **kw)
    i = out.index("-p")
    return out[:i] + out[i + 1:]


def argv_print_moved(line, **kw):
    out = ORIG_ARGV(line, **kw)
    i = out.index("-p")
    rest = out[:i] + out[i + 2:]
    return rest + ["-p", line]


def gate_without_print(inner):
    if len(inner) < 2 or inner[1] not in ("-p", "--print"):
        inner = [inner[0], "-p", "", *inner[1:]]
    ORIG_GATE(inner)


def settings_with_key(m):
    return json.dumps(dict(json.loads(ORIG_SETTINGS(m)), **{KEY: True}), sort_keys=True, separators=(",", ":"))


MUTANTS = {
    "adapter drops -p": [(cca, "argv", argv_without_p)],
    "adapter and gate drop -p": [(cca, "argv", argv_without_p), (rt, "check_claude_settings", gate_without_print)],
    "adapter moves -p last, gate check dropped": [(cca, "argv", argv_print_moved),
                                                  (rt, "check_claude_settings", gate_without_print)],
    "key re-added to the settings": [(rt, "claude_study_settings", settings_with_key)],
    "key re-added as the value": [(rt, "CLAUDE_BYPASS_KEY", KEY)],
}


def run(mod):
    r = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(
        unittest.defaultTestLoader.loadTestsFromModule(mod))
    return len(r.failures) + len(r.errors), r.testsRun


bad, n = run(tca)
print(f"control test_claude_code_adapter: {bad} of {n}")
assert bad == 0, "the control is not clean: every mutant result would be vacuous"
alive = []
for name, patches in MUTANTS.items():
    with contextlib.ExitStack() as stack:
        for o, a, v in patches:
            stack.enter_context(mock.patch.object(o, a, v))
        got = run(tca)[0]
    print(("RED  " if got else "ALIVE"), f"{got} failing in test_claude_code_adapter:", name)
    if not got:
        alive.append(name)
print("ALIVE:", alive or "none")
