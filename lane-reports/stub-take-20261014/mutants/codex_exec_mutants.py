"""Mutants of box/run_take.py's Codex exec branch (glitch-06, 14 Oct 2026), one per branch, against
test_run_take.TestCodexExec (in memory; nothing on disk changes)."""
import io, sys, types, unittest
from pathlib import Path
T = str(Path(__file__).resolve().parents[3] / "evals/gap-study-4/tests")
sys.path.insert(0, T); sys.dont_write_bytecode = True
import test_run_take as tt
rt = tt.rt
SRC = open(rt.__file__).read()
MUTANTS = [
 ("no gate", "    codex_lease_gate()\n    src = os.environ if caller_env is None else caller_env\n    if user != AGENT_USER:", "    src = os.environ if caller_env is None else caller_env\n    if user != AGENT_USER:"),
 ("any user", "    if user != AGENT_USER:\n        raise Refused(f\"every exec into the take container runs as the agent, {AGENT_USER}\")\n    _check_id(container_id, \"container id\")\n    inner = _check_argv(inner)\n    workdir = _abs_path(workdir, \"workdir\") if workdir != \"/\" else \"/\"\n    check_codex_turn(inner)", "    _check_id(container_id, \"container id\")\n    inner = _check_argv(inner)\n    workdir = _abs_path(workdir, \"workdir\") if workdir != \"/\" else \"/\"\n    check_codex_turn(inner)"),
 ("no id check", "    _check_id(container_id, \"container id\")\n    inner = _check_argv(inner)\n    workdir = _abs_path(workdir, \"workdir\") if workdir != \"/\" else \"/\"\n    check_codex_turn(inner)", "    inner = _check_argv(inner)\n    workdir = _abs_path(workdir, \"workdir\") if workdir != \"/\" else \"/\"\n    check_codex_turn(inner)"),
 ("no argv check", "    inner = _check_argv(inner)\n    workdir = _abs_path(workdir, \"workdir\") if workdir != \"/\" else \"/\"\n    check_codex_turn(inner)", "    workdir = _abs_path(workdir, \"workdir\") if workdir != \"/\" else \"/\"\n    check_codex_turn(inner)"),
 ("any workdir", "    workdir = _abs_path(workdir, \"workdir\") if workdir != \"/\" else \"/\"\n    check_codex_turn(inner)", "    check_codex_turn(inner)"),
 ("no turn check", "    check_codex_turn(inner)\n    values = exec_values(CODEX, run_tree)", "    values = exec_values(CODEX, run_tree)"),
 ("no environment check", "    values = exec_values(CODEX, run_tree)\n    check_environment(CODEX, src, set(values))\n", "    values = exec_values(CODEX, run_tree)\n"),
 ("no lease check", "    check_codex_lease_place(login_file, run_tree)\n    argv =", "    argv ="),
 ("a named login", "            *launcher_argv(NO_LOGIN, values, inner, harness=CODEX)]", "            *launcher_argv(\"CODEX_API_KEY\", values, inner, harness=rt_gemini_never)]"),
 ("another client", "    if not inner or inner[0] != CODEX_CLIENT:", "    if not inner:"),
 ("another subcommand", "    if len(inner) < 2 or inner[1] != CODEX_SUBCOMMAND:", "    if len(inner) < 2:"),
 ("any option admitted", "            raise Refused(f\"unsupported Codex turn argument {tok!r}", "            i += 1; continue\n            raise Refused(f\"unsupported Codex turn argument {tok!r}"),
 ("-m with no value", "            if value is None or value.startswith(\"-\"):\n                raise Refused(f\"{tok} takes", "            if False:\n                raise Refused(f\"{tok} takes"),
 ("--json not counted", "    if counts[\"json\"] != 1:", "    if False:"),
 ("model not counted", "    if counts[\"model\"] != 1:", "    if False:"),
 ("bypass not counted", "    if counts[\"bypass\"] != 1:", "    if False:"),
 ("any model", "    if model not in CODEX_MODELS:", "    if False:"),
 ("resume of any length", "        if len(rest) != 3:\n            raise Refused(\"`resume` takes", "        if False:\n            raise Refused(\"`resume` takes"),
 ("any session id", "        if not _CODEX_SESSION.fullmatch(rest[1]):", "        if False:"),
 ("any number of prompts", "        if len(rest) != 1:\n            raise Refused(\"a Codex turn ends", "        if False:\n            raise Refused(\"a Codex turn ends"),
 ("the session form drifts from the adapter's", '_CODEX_SESSION = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{0,127}")', '_CODEX_SESSION = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{0,63}")'),
 ("the bypass flag drifts from the adapter's", 'CODEX_BYPASS_FLAG = "--dangerously-bypass-approvals-and-sandbox"', 'CODEX_BYPASS_FLAG = "--dangerously-bypass-hook-trust"'),
 ("a subcommand name as the prompt", "        if prompt in CODEX_HELP_COMMANDS:", "        if False:"),
 ("help dropped from the commands", 'CODEX_HELP_COMMANDS = ("resume", "fork", "review", "help")', 'CODEX_HELP_COMMANDS = ("resume", "fork", "review")'),
 ("a prompt that reads as a flag", "    if not prompt or prompt.startswith(\"-\"):", "    if not prompt:"),
 ("a lease of any name", "    if os.path.basename(path) != LEASE_FILE:", "    if False:"),
 ("no place check", "    check_login_place(path, run_tree)\n    st = os.lstat(path)", "    st = os.lstat(path)"),
 ("any lease mode", "    if stat.S_IMODE(st.st_mode) != 0o600:\n        raise LoginRefused(f\"{path}: the lease's mode", "    if False:\n        raise LoginRefused(f\"{path}: the lease's mode"),
 ("a lease in a repository", "    if not outside_every_repository(path):\n        raise LoginRefused(f\"{path}: the lease must sit", "    if False:\n        raise LoginRefused(f\"{path}: the lease must sit"),
 ("another pinned model", 'CODEX_MODELS = ("gpt-6.1-sol", "gpt-6-luna")', 'CODEX_MODELS = ("gpt-6.1-sol", "o3")'),
]
EQUIVALENT = [
 ("the lease's regular-file and owner checks", "check_login_place already refuses a link (its one-link rule reads the link "
  "itself; a link is never auth.json's own file) and a folder not owned by the reader; a file inside that folder owned "
  "by another uid cannot be planted without root. Each is kept as a second line, named here, not mutated."),
]
def run(mod):
    tt.rt = mod
    try:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(tt.TestCodexExec)
        return unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
    finally:
        tt.rt = rt
c = run(rt); print("control", len(c.failures) + len(c.errors), "of", c.testsRun)
assert not (c.failures or c.errors), "the control is not clean"
alive = []
for name, old, new in MUTANTS:
    assert SRC.count(old) == 1, name
    mod = types.ModuleType(rt.__name__); mod.__file__ = rt.__file__
    try:
        exec(compile(SRC.replace(old, new), rt.__file__, "exec"), mod.__dict__)
    except Exception as e:  # noqa: BLE001
        print("RED  ", "load", name, f"({type(e).__name__})"); continue
    r = run(mod); bad = len(r.failures) + len(r.errors)
    print(("RED  " if bad else "ALIVE"), f"{bad}/{r.testsRun}", name)
    if not bad: alive.append(name)
for name, why in EQUIVALENT:
    print("EQUIVALENT (named, no mutant):", name, "-", why)
print("ALIVE:", alive or "none")
