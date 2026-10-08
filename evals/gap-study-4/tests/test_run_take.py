#!/usr/bin/env python3
"""box/run_take.py: the runtime protocol, the take container, the environment per harness, the login read, launch
and teardown, leaked containers, the agent's leftover processes, the counters, the exit record and one turn.

Every test drives a FakeRuntime that records each (argv, env) and answers from a script; a call the script did not
expect fails the test. No test reaches a real process: the guard below patches every process start and signal for
the whole module, armed AFTER the one leak-word read (`_round3_leak_words`, interface 16). Every guard is also run
against in-memory mutants, each printed with its red result.
"""

from __future__ import annotations

import ast
import contextlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
REPO = os.path.dirname(os.path.dirname(HERE))
DRIVE = os.path.join(HERE, "drive.py")
ROUND3 = "e2979b3143081824aadea73523ec41af30c1ddb1"
LANE_LEAD_WORDS = ("gap4", "round 4", "sidecar", "watcher", "evidence", "holdout", "sealed", "probe", "trap",
                   "grader")


def _round3_leak_words() -> tuple:
    """Round 3's pre-registration key leak_words, that key alone, read once (interface 16). Never committed."""
    shown = subprocess.run(["git", "-C", REPO, "show", f"{ROUND3}:evals/gap-study-3/prereg.json"],
                           capture_output=True, check=True)
    return tuple(json.loads(shown.stdout)["leak_words"])


LEAK_WORDS = _round3_leak_words() + LANE_LEAD_WORDS


# ------------------------------------------------------------------ the process guard (interface 10), armed here
class ProcessGuardTripped(AssertionError):
    pass


def _tripwire(name):
    def trip(*a, **k):
        raise ProcessGuardTripped(f"a test reached {name}")
    return trip


GUARDED = [(subprocess, n) for n in ("run", "Popen", "call", "check_call", "check_output", "getoutput",
                                     "getstatusoutput")]
GUARDED += [(os, n) for n in ("system", "popen", "kill", "killpg", "posix_spawn", "posix_spawnp", "fork", "forkpty")
            if hasattr(os, n)]
GUARDED += [(os, n) for n in dir(os) if re.fullmatch(r"(exec|spawn)[lvpe]*", n)]
for _mod, _name in GUARDED:
    setattr(_mod, _name, _tripwire(f"{_mod.__name__}.{_name}"))

from box import run_take as rt  # noqa: E402
import harness_bookkeeping  # noqa: E402
import agent_adapter  # noqa: E402

# ------------------------------------------------------------------------------------------------- helpers
ID = {k: (c * 64) for k, c in (("net", "a"), ("proxy", "b"), ("side", "c"), ("take", "d"), ("other", "e"))}
IMAGE = "sha256:" + "f" * 64
FAKE_VALUE = "FAKEVALUE-0123456789abcdef-PLANTED"
CALLER = {"PATH": "/usr/bin:/bin", "HOME": "/home/op", "DOCKER_HOST": "unix:///run/user/1000/docker.sock",
          "XDG_RUNTIME_DIR": "/run/user/1000", "UNRELATED": "x"}
ARMS = (harness_bookkeeping.CLAUDE_CODE, "codex", "gemini")


class FakeRuntime:
    """Records every (argv, env) and answers from a script of (argv prefix, Completed | exception)."""

    def __init__(self, script=()):
        self.script = list(script)
        self.calls = []
        self.unexpected = []

    def run(self, argv, *, env=None, timeout=None):
        self.calls.append((list(argv), None if env is None else dict(env)))
        if not self.script:
            self.unexpected.append(list(argv))
            raise AssertionError(f"unexpected runtime call {argv}")
        prefix, answer = self.script.pop(0)
        if list(argv[:len(prefix)]) != list(prefix):
            self.unexpected.append(list(argv))
            raise AssertionError(f"runtime call {argv} does not start with {prefix}")
        if isinstance(answer, BaseException):
            raise answer
        return answer


def ok(stdout="", stderr=""):
    return rt.Completed(0, stdout, stderr)


def spec(**kw):
    base = dict(image=IMAGE, run_tree="/srv/w/t1/tree", config_dir="/srv/w/t1/cfg", network=ID["net"],
                memory_reservation=512 * 2 ** 20, memory=3 * 512 * 2 ** 20, cpus="2", pids_limit=256)
    base.update(kw)
    return rt.TakeSpec(**base)


def problems_of(fn) -> list:
    try:
        return list(fn())
    except Exception as exc:  # a check that crashes under a mutant reads red
        return [f"raised {type(exc).__name__}: {exc}"]


class MutantCase(unittest.TestCase):
    def assert_green_then_red(self, check, mutants):
        """`check()` returns problems; [] on the real module, non-empty under every mutant (printed)."""
        self.assertEqual(problems_of(check), [], "the guard is red on the real module")
        for name, ctx in mutants:
            with ctx():
                got = problems_of(check)
            print(f"  mutant {name}: {'red' if got else 'GREEN (survived)'}"
                  f"{' - ' + got[0][:100] if got else ''}")
            self.assertNotEqual(got, [], f"mutant {name} survived")


def patched(obj, attr, value):
    return lambda: mock.patch.object(obj, attr, value)


def drive_constant(name: str):
    """A top-level constant of drive.py, read with ast (drive.py is never imported)."""
    with open(DRIVE, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    for node in tree.body:
        targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) \
            else []
        for t in targets:
            if isinstance(t, ast.Name) and t.id == name and node.value is not None:
                return ast.literal_eval(node.value)
    raise AssertionError(f"drive.py holds no constant {name}")


# ------------------------------------------------------------------------------------------- the guard itself
class TestProcessGuard(unittest.TestCase):
    def test_guard_is_armed(self):
        with self.assertRaises(ProcessGuardTripped):
            subprocess.run(["true"])
        with self.assertRaises(ProcessGuardTripped):
            os.kill(0, 0)
        with self.assertRaises(ProcessGuardTripped):
            subprocess.Popen(["true"])
        self.assertGreater(len(GUARDED), 10)

    def test_module_is_this_rounds(self):
        self.assertTrue(os.path.abspath(rt.__file__).startswith(os.path.join(HERE, "box") + os.sep))

    def test_leak_words_read(self):
        self.assertIn("evaluation", LEAK_WORDS)
        self.assertIn("sidecar", LEAK_WORDS)


# -------------------------------------------------------------------------------------------- DockerRuntime
class TestDockerRuntime(MutantCase):
    def check(self, runtime_cls=None):
        cls = runtime_cls or rt.DockerRuntime
        seen = {}

        def fake_run(argv, **kw):
            seen["argv"], seen["kw"] = argv, kw
            return subprocess.CompletedProcess(argv, 3, "out", "err")

        problems = []
        with mock.patch.object(rt.subprocess, "run", fake_run):
            c = cls().run(["docker", "ps"], env={"PATH": "/bin"}, timeout=5)
        if not isinstance(seen.get("argv"), list) or seen["argv"] != ["docker", "ps"]:
            problems.append("argv is not passed as the list")
        if seen.get("kw", {}).get("shell") is not False:
            problems.append("shell is not explicitly False")
        if seen.get("kw", {}).get("env") != {"PATH": "/bin"}:
            problems.append("env is not the whole environment given")
        if (c.returncode, c.stdout, c.stderr) != (3, "out", "err"):
            problems.append("Completed does not carry the result")

        def timing_out(argv, **kw):
            raise subprocess.TimeoutExpired(argv, kw.get("timeout"), output=b"partial")

        with mock.patch.object(rt.subprocess, "run", timing_out):
            try:
                cls().run(["docker", "exec"], env={}, timeout=1)
                problems.append("a timeout did not raise")
            except TimeoutError as e:
                if getattr(e, "stdout", None) != "partial":
                    problems.append("the timeout lost the partial stdout")
            except Exception as e:
                problems.append(f"a timeout raised {type(e).__name__}, not TimeoutError")
        seen.clear()
        with mock.patch.object(rt.subprocess, "run", fake_run):
            cls().run(["docker", "ps"], env=None)
        if seen.get("kw", {}).get("env") != {}:
            problems.append("env None merged an environment in")
        for bad in ("docker ps", ["docker", 3], []):
            with mock.patch.object(rt.subprocess, "run", fake_run):
                try:
                    cls().run(bad)
                    problems.append(f"argv {bad!r} accepted")
                except TypeError:
                    pass
        return problems

    def test_docker_runtime(self):
        def run_shell(self, argv, *, env=None, timeout=None):
            p = rt.subprocess.run(" ".join(argv), env=env, timeout=timeout, shell=True, capture_output=True,
                                  text=True)
            return rt.Completed(p.returncode, p.stdout, p.stderr)

        def run_merged(self, argv, *, env=None, timeout=None):
            p = rt.subprocess.run(list(argv), env=dict(os.environ, **(env or {})), timeout=timeout, shell=False,
                                  capture_output=True, text=True)
            return rt.Completed(p.returncode, p.stdout, p.stderr)

        def run_no_timeout(self, argv, *, env=None, timeout=None):
            try:
                p = rt.subprocess.run(list(argv), env=env or {}, timeout=timeout, shell=False, capture_output=True,
                                      text=True)
            except subprocess.TimeoutExpired:
                return rt.Completed(124, "", "")
            return rt.Completed(p.returncode, p.stdout, p.stderr)

        self.assert_green_then_red(self.check, [
            ("shell-string", patched(rt.DockerRuntime, "run", run_shell)),
            ("merges-os-environ", patched(rt.DockerRuntime, "run", run_merged)),
            ("timeout-as-exit", patched(rt.DockerRuntime, "run", run_no_timeout)),
        ])


# ----------------------------------------------------------------------------------- drive.py's constants (ast)
class TestDriveBinding(MutantCase):
    NAMES = ("ISOLATION_ENV", "RUN_TREE_TMPDIR", "RUN_TREE_TMPDIR_VARIABLES", "API_KEY_VARIABLES",
             "BILLING_ROUTE_VARIABLES", "SUBSCRIPTION_TOKEN_VARIABLES")

    def check(self):
        return [f"run_take.{n} differs from drive.{n}" for n in self.NAMES if getattr(rt, n) != drive_constant(n)]

    def test_bound_to_drive(self):
        self.assertIn("CLAUDE_CODE_OAUTH_TOKEN", drive_constant("SUBSCRIPTION_TOKEN_VARIABLES"))
        self.assert_green_then_red(self.check, [
            (f"{n}-drifts", patched(rt, n, ("X",))) for n in self.NAMES])

    def test_isolation_env_rides_in_claude_env(self):
        def check():
            env = rt.HARNESS_ENV[rt.CLAUDE_CODE]
            return [k for k, v in drive_constant("ISOLATION_ENV").items() if env.get(k) != v]
        self.assert_green_then_red(check, [
            ("isolation-dropped", patched(rt, "HARNESS_ENV", dict(rt.HARNESS_ENV, **{
                rt.CLAUDE_CODE: {k: v for k, v in rt.HARNESS_ENV[rt.CLAUDE_CODE].items()
                                 if k != "CLAUDE_CODE_DISABLE_AUTO_MEMORY"}})))])


# --------------------------------------------------------------------------------------------- shared values
class TestSharedValues(MutantCase):
    EXPECT = {"AGENT_USER": "10001:10001", "KEEPALIVE_USER": "10003:10003", "PROXY_ALIAS": "proxy",
              "PROXY_URL": "http://proxy:3128", "CONFIG_MOUNT": "/opt/cfg", "CODEX": "codex", "GEMINI": "gemini",
              "QUIESCENCE_CAP_SURVIVORS_KEY": "quiescence_cap_survivors", "QUIESCENCE_CAP_ROW":
              "quiescence-cap-reached"}

    def check(self):
        out = [f"{k} = {getattr(rt, k)!r}" for k, v in self.EXPECT.items() if getattr(rt, k) != v]
        if rt.CLAUDE_CODE != harness_bookkeeping.CLAUDE_CODE:
            out.append("CLAUDE_CODE is not harness_bookkeeping's")
        keys = set(rt.LOGIN_VARIABLE)
        if keys != {rt.CLAUDE_CODE, rt.CODEX, rt.GEMINI} or set(rt.HARNESS_ENV) != keys:
            out.append("the per-harness tables do not hold exactly the three harnesses")
        if rt.LOGIN_VARIABLE != {rt.CLAUDE_CODE: "CLAUDE_CODE_OAUTH_TOKEN", rt.CODEX: "CODEX_API_KEY",
                                 rt.GEMINI: "GEMINI_API_KEY"}:
            out.append("LOGIN_VARIABLE is not the card's three names")
        return out

    def test_values(self):
        muts = [(f"{k}-changed", patched(rt, k, v + "x")) for k, v in self.EXPECT.items()]
        muts.append(("claude-name-retyped", patched(rt, "CLAUDE_CODE", "claude")))
        muts.append(("extra-harness", patched(rt, "LOGIN_VARIABLE", dict(rt.LOGIN_VARIABLE, other="X_KEY"))))
        self.assert_green_then_red(self.check, muts)

    def test_claude_code_typed_nowhere_in_box(self):
        src = open(rt.__file__, encoding="utf-8").read()
        self.assertNotIn('"' + harness_bookkeeping.CLAUDE_CODE + '"', src)

    def test_harness_env_values(self):
        def check():
            e = rt.HARNESS_ENV
            want = {
                rt.CLAUDE_CODE: {"DISABLE_AUTOUPDATER": "1", "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
                                 "HTTPS_PROXY": "http://proxy:3128", "ENABLE_CLAUDEAI_MCP_SERVERS": "false",
                                 "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1", "CLAUDE_CONFIG_DIR": "/opt/cfg"},
                rt.CODEX: {"HTTPS_PROXY": "http://proxy:3128", "CODEX_HOME": "/opt/cfg"},
                rt.GEMINI: {"HTTPS_PROXY": "http://proxy:3128", "GEMINI_CLI_HOME": "/opt/cfg"},
            }
            return [h for h in want if e.get(h) != want[h]]
        muts = []
        for h, name in ((rt.CLAUDE_CODE, "DISABLE_AUTOUPDATER"), (rt.CLAUDE_CODE, "CLAUDE_CONFIG_DIR"),
                        (rt.CLAUDE_CODE, "HTTPS_PROXY"), (rt.CODEX, "CODEX_HOME"), (rt.GEMINI, "GEMINI_CLI_HOME"),
                        (rt.CODEX, "HTTPS_PROXY"), (rt.GEMINI, "HTTPS_PROXY"),
                        (rt.CLAUDE_CODE, "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC")):
            muts.append((f"{h}-drops-{name}", patched(rt, "HARNESS_ENV", dict(rt.HARNESS_ENV, **{
                h: {k: v for k, v in rt.HARNESS_ENV[h].items() if k != name}}))))
        self.assert_green_then_red(check, muts)


# ------------------------------------------------------------------------------------------------- create_argv
EXPECTED_CREATE = [
    "docker", "create", "--pull=never", "--network", ID["net"], "--user", "10003:10003", "--cap-drop", "ALL",
    "--security-opt", "no-new-privileges", "--pids-limit", "256", "--memory-reservation", str(512 * 2 ** 20),
    "--memory", str(3 * 512 * 2 ** 20), "--cpus", "2",
    "--mount", "type=bind,source=/srv/w/t1/tree,target=/srv/w/t1/tree",
    "--mount", "type=bind,source=/srv/w/t1/cfg,target=/opt/cfg",
    "--workdir", "/srv/w/t1/tree", IMAGE, "sleep", "infinity"]
FORBIDDEN_CREATE = ("-e", "--env", "--env-file", "--privileged", "--cap-add", "--device", "-p", "--publish",
                    "--pid", "--ipc", "--volumes-from", "-v", "--volume", "--network-alias", "--userns")


class TestCreateArgv(MutantCase):
    def check_shape(self):
        argv = rt.create_argv(spec())
        out = [] if argv == EXPECTED_CREATE else [f"create argv differs: {argv}"]
        flags = [a.split("=")[0] for a in argv]
        out += [f"forbidden flag {f}" for f in FORBIDDEN_CREATE if f in flags]
        if argv.count("--mount") != 2:
            out.append("not exactly two mounts")
        return out

    def test_shape(self):
        orig = rt.create_argv

        def with_env(s):
            return orig(s)[:2] + ["-e", "X=1"] + orig(s)[2:]

        def with_alias(s):
            return orig(s)[:5] + ["--network-alias", "proxy"] + orig(s)[5:]

        def no_pull(s):
            return [a for a in orig(s) if a != "--pull=never"]

        def third_mount(s):
            a = orig(s)
            return a[:-4] + ["--mount", "type=bind,source=/x,target=/x"] + a[-4:]

        def agent_pid1(s):
            return [("10001:10001" if a == "10003:10003" else a) for a in orig(s)]

        self.assert_green_then_red(self.check_shape, [
            ("env-at-create", patched(rt, "create_argv", with_env)),
            ("alias-on-take", patched(rt, "create_argv", with_alias)),
            ("pull-allowed", patched(rt, "create_argv", no_pull)),
            ("third-mount", patched(rt, "create_argv", third_mount)),
            ("agent-as-pid1", patched(rt, "create_argv", agent_pid1)),
            ("keepalive-user", patched(rt, "KEEPALIVE_USER", "10001:10001")),
            ("config-mount", patched(rt, "CONFIG_MOUNT", "/root/cfg")),
            ("keepalive-command", patched(rt, "KEEPALIVE_COMMAND", ("sh",))),
        ])

    REFUSED = {
        "pending-reservation": dict(memory_reservation=rt.PENDING),
        "pending-memory": dict(memory=rt.PENDING),
        "pending-cpus": dict(cpus=rt.PENDING),
        "pending-pids": dict(pids_limit=rt.PENDING),
        "memory-not-3x": dict(memory=2 * 512 * 2 ** 20),
        "bool-pids": dict(pids_limit=True),
        "zero-pids": dict(pids_limit=0),
        "cpus-not-decimal": dict(cpus="two"),
        "cpus-zero": dict(cpus="0"),
        "keepalive-other": dict(keepalive_user="0:0"),
        "agent-other": dict(agent_user="0:0"),
        "cap-drop-partial": dict(cap_drop=("NET_RAW",)),
        "security-opt-other": dict(security_opt=()),
        "image-tag": dict(image="busybox:latest"),
        "network-name": dict(network="bridge"),
        "relative-tree": dict(run_tree="srv/tree"),
        "comma-in-tree": dict(run_tree="/srv/a,b"),
        "tree-in-cfg": dict(run_tree="/srv/w/t1/cfg/tree"),
        "tree-over-mount": dict(run_tree="/opt/cfg/x"),
        "root-tree": dict(run_tree="/"),
    }

    def check_refusals(self):
        out = []
        for name, kw in self.REFUSED.items():
            try:
                rt.create_argv(spec(**kw))
                out.append(f"{name} accepted")
            except rt.NotReady:
                if not name.startswith("pending"):
                    out.append(f"{name} raised NotReady, not Refused")
            except rt.Refused:
                if name.startswith("pending"):
                    out.append(f"{name} raised Refused, not NotReady")
        return out

    def test_refusals(self):
        self.assert_green_then_red(self.check_refusals, [
            ("no-spec-check", patched(rt, "check_spec", lambda s: None))])

    def test_defaults_are_pending(self):
        s = rt.TakeSpec(image=IMAGE, run_tree="/a/t", config_dir="/a/c", network=ID["net"])
        with self.assertRaises(rt.NotReady):
            rt.create_argv(s)


# --------------------------------------------------------------------------------- the environment per harness
def plant_login(folder, name, value=FAKE_VALUE, mode=0o600, text=None):
    path = os.path.join(folder, f"{name.lower()}.line")
    with open(path, "w", encoding="ascii") as fh:
        fh.write(text if text is not None else f"{name}={value}\n")
    os.chmod(path, mode)
    return path


@contextlib.contextmanager
def filled():
    """Every PENDING value exec needs, filled in memory only (interface 15)."""
    with mock.patch.object(rt, "FALLBACK_ENV", {"FAKE_FALLBACK_A": "1"}), \
            mock.patch.object(rt, "VENDOR_BILLING_ROUTE_VARIABLES", {rt.CODEX: (), rt.GEMINI: ()}):
        yield


class TestArmVariables(MutantCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.logins = {h: plant_login(self.tmp, rt.LOGIN_VARIABLE[h]) for h in ARMS}

    def exec_for(self, harness, caller=None):
        return rt.exec_argv(ID["take"], ["agent-cli"], user=rt.AGENT_USER, workdir="/srv/w/t1/tree",
                            harness=harness, run_tree="/srv/w/t1/tree", login_file=self.logins[harness],
                            caller_env=CALLER if caller is None else caller)

    def check_cross_arm(self):
        """A take in each arm carrying each other arm's variable (or any refused name) is refused."""
        out = []
        for arm in ARMS:
            others = [rt.LOGIN_VARIABLE[h] for h in ARMS if h != arm]
            others += ["OPENAI_API_KEY", "GOOGLE_API_KEY", "ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_REFRESH_TOKEN",
                       "CLAUDE_CODE_USE_VERTEX"]
            for var in others:
                for where in ("caller", "pending"):
                    try:
                        if where == "caller":
                            with filled():
                                self.exec_for(arm, dict(CALLER, **{var: FAKE_VALUE}))
                        else:
                            self.exec_for(arm, dict(CALLER, **{var: FAKE_VALUE}))
                        out.append(f"{arm} take carrying {var} ({where}) accepted")
                    except rt.Refused as e:
                        if FAKE_VALUE in str(e):
                            out.append("a refusal printed the value")
                    except rt.NotReady:
                        out.append(f"{arm} take carrying {var} ({where}) waited on PENDING instead of refusing")
        # Its own login set in the caller's own environment is not a refusal (it rides from its file).
        return out

    def test_cross_arm_refused(self):
        self.assert_green_then_red(self.check_cross_arm, [
            ("no-env-check", patched(rt, "check_environment", lambda *a, **k: None)),
            ("vendor-keys-dropped", patched(rt, "VENDOR_KEY_VARIABLES", ())),
            ("api-keys-dropped", patched(rt, "API_KEY_VARIABLES", ())),
            ("billing-dropped", patched(rt, "BILLING_ROUTE_VARIABLES", ())),
            ("subscription-dropped", patched(rt, "SUBSCRIPTION_TOKEN_VARIABLES", ())),
        ])

    def check_requested(self):
        out = []
        for arm in ARMS:
            other = next(rt.LOGIN_VARIABLE[h] for h in ARMS if h != arm)
            bad = dict(rt.HARNESS_ENV, **{arm: dict(rt.HARNESS_ENV[arm], **{other: "x"})})
            with mock.patch.object(rt, "HARNESS_ENV", bad), filled():
                try:
                    self.exec_for(arm)
                    out.append(f"{arm} exec requesting {other} accepted")
                except rt.Refused:
                    pass
        return out

    def test_requested_refused(self):
        self.assert_green_then_red(self.check_requested, [
            ("no-env-check", patched(rt, "check_environment", lambda *a, **k: None))])

    def check_refused_sets(self):
        out = []
        closed = (set(rt.API_KEY_VARIABLES) | set(rt.BILLING_ROUTE_VARIABLES) | set(rt.SUBSCRIPTION_TOKEN_VARIABLES)
                  | {"CODEX_API_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY"})
        for arm in ARMS:
            got = rt.refused_variables(arm)
            if got != closed - {rt.LOGIN_VARIABLE[arm]}:
                out.append(f"{arm}: refused set {sorted(got ^ (closed - {rt.LOGIN_VARIABLE[arm]}))} off")
        if "CLAUDE_CODE_OAUTH_TOKEN" not in rt.refused_variables(rt.CODEX):
            out.append("arm O admits Anthropic's token")
        return out

    def test_refused_sets(self):
        self.assert_green_then_red(self.check_refused_sets, [
            ("own-login-refused", patched(rt, "LOGIN_VARIABLE", dict(rt.LOGIN_VARIABLE, codex="NOT_A_VAR"))),
            ("vendor-list-short", patched(rt, "VENDOR_KEY_VARIABLES", ("CODEX_API_KEY", "GEMINI_API_KEY"))),
        ])

    def test_unknown_harness_refused(self):
        for h in ("fake-second", "", None, "Codex"):
            with self.assertRaises(rt.Refused):
                rt.refused_variables(h)
            with self.assertRaises(rt.Refused):
                rt.exec_argv(ID["take"], ["x"], user=rt.AGENT_USER, workdir="/", harness=h, run_tree="/a/t",
                             login_file=self.logins[rt.CODEX], caller_env=CALLER)


# ------------------------------------------------------------- interface 10's default-deny audit (ast, not grep)
BOX_MODULES = ("box/run_take.py", "box/take_config.py", "box/preflight.py")
# The closed standard-library allowlist this lane names, plus the seam modules and its own box modules.
ALLOWED_IMPORTS = frozenset({"__future__", "dataclasses", "decimal", "hashlib", "json", "os", "re", "secrets",
                             "shutil", "stat", "subprocess", "sys", "typing"})
LOCAL_IMPORTS = frozenset({"agent_adapter", "harness_bookkeeping", "box", "box.run_take", "box.preflight",
                           "box.take_config"})
SUBPROCESS_MODULE = "box/run_take.py"
SUBPROCESS_SITE = ("DockerRuntime", "run")
SUBPROCESS_NAMES = frozenset({"run", "TimeoutExpired"})
FORBIDDEN_OS = re.compile(r"(kill|killpg|system|popen|fork|forkpty|posix_spawnp?|exec[lvpe]*|spawn[lvpe]*)")


def audit_source(rel: str, source: str) -> list:
    """Problems with one non-test box module: imports off the allowlist, subprocess outside its one site, a process
    start or signal name, shell=True."""
    tree = ast.parse(source)
    out = []
    scopes = {}

    def walk(node, stack):
        for child in ast.iter_child_nodes(node):
            scopes[child] = stack
            walk(child, stack + ((child.name,) if isinstance(child, (ast.ClassDef, ast.FunctionDef,
                                                                     ast.AsyncFunctionDef)) else ()))
    walk(tree, ())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                top = a.name
                if top not in ALLOWED_IMPORTS and top not in LOCAL_IMPORTS:
                    out.append(f"{rel}: import {a.name} is off the allowlist")
                if top == "subprocess" and rel != SUBPROCESS_MODULE:
                    out.append(f"{rel}: imports subprocess")
                if a.asname and top in ("os", "subprocess"):
                    out.append(f"{rel}: {top} imported under another name")
        elif isinstance(node, ast.ImportFrom):
            mod = ("." * node.level) + (node.module or "")
            if mod not in ALLOWED_IMPORTS and mod not in LOCAL_IMPORTS:
                out.append(f"{rel}: from {mod} import is off the allowlist")
            if mod in ("os", "subprocess", "pty", "asyncio"):
                out.append(f"{rel}: from {mod} import names a process function directly")
        elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            base, attr = node.value.id, node.attr
            if base == "subprocess":
                if rel != SUBPROCESS_MODULE or scopes.get(node, ())[-2:] != SUBPROCESS_SITE \
                        or attr not in SUBPROCESS_NAMES:
                    out.append(f"{rel}: subprocess.{attr} outside DockerRuntime.run")
            if base == "os" and FORBIDDEN_OS.fullmatch(attr):
                out.append(f"{rel}: os.{attr}")
            if base == "pty" or (base == "asyncio" and attr.startswith("create_subprocess")):
                out.append(f"{rel}: {base}.{attr}")
        elif isinstance(node, ast.keyword) and node.arg == "shell":
            if not (isinstance(node.value, ast.Constant) and node.value.value is False):
                out.append(f"{rel}: shell= is not the constant False")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in (
                "getattr", "__import__", "eval", "exec", "compile"):
            if node.func.id != "getattr" or (len(node.args) > 1 and isinstance(node.args[1], ast.Constant)
                                             and isinstance(node.args[1].value, str)
                                             and FORBIDDEN_OS.fullmatch(node.args[1].value)):
                out.append(f"{rel}: {node.func.id}(...) reaches a name dynamically")
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)
             and n.value.id == "subprocess" and n.attr == "run"]
    if rel == SUBPROCESS_MODULE and len(calls) != 1:
        out.append(f"{rel}: {len(calls)} subprocess.run sites, never exactly one")
    return out


PLANTED = {
    "posix-spawn-import": ("box/preflight.py", "from os import posix_spawn\n"),
    "posix-spawn-call": ("box/take_config.py", "import os\nos.posix_spawn('x', ['x'], {})\n"),
    "kill": ("box/run_take.py", "import os\nos.kill(1, 9)\n"),
    "killpg": ("box/run_take.py", "import os\ndef f():\n    os.killpg(1, 9)\n"),
    "system": ("box/preflight.py", "import os\nos.system('x')\n"),
    "execv": ("box/preflight.py", "import os\nos.execv('x', ['x'])\n"),
    "fork": ("box/preflight.py", "import os\nos.fork()\n"),
    "subprocess-elsewhere": ("box/preflight.py", "import subprocess\n"),
    "popen-in-run-take": ("box/run_take.py", "import subprocess\nclass DockerRuntime:\n    def run(self):\n"
                                             "        subprocess.run([])\ndef g():\n    subprocess.Popen([])\n"),
    "run-outside-site": ("box/run_take.py", "import subprocess\ndef g():\n    subprocess.run([])\n"),
    "shell-true": ("box/run_take.py", "import subprocess\nclass DockerRuntime:\n    def run(self):\n"
                                      "        subprocess.run('x', shell=True)\n"),
    "socket-import": ("box/run_take.py", "import socket\n"),
    "importlib": ("box/preflight.py", "import importlib\n"),
    "pty": ("box/preflight.py", "import pty\npty.spawn('x')\n"),
    "asyncio": ("box/preflight.py", "import asyncio\n"),
    "getattr-kill": ("box/preflight.py", "import os\ngetattr(os, 'kill')(1, 9)\n"),
    "dunder-import": ("box/preflight.py", "__import__('subprocess')\n"),
    "aliased-os": ("box/preflight.py", "import os as o\n"),
}


def process_audit(read=None) -> list:
    """Planted positives first (each must be caught), then the three real modules (each must be clean)."""
    out = []
    for name, (rel, src) in PLANTED.items():
        if not audit_source(rel, src):
            out.append(f"planted {name} was not caught")
    for rel in BOX_MODULES:
        path = os.path.join(HERE, rel)
        src = read(rel) if read else open(path, encoding="utf-8").read()
        out += audit_source(rel, src)
    return out


class TestProcessAudit(MutantCase):
    def test_audit(self):
        real = {rel: open(os.path.join(HERE, rel), encoding="utf-8").read() for rel in BOX_MODULES}

        def with_added(rel, extra):
            return lambda: mock.patch.dict(globals(), {"_AUDIT_READ": lambda r: real[r] + (extra if r == rel else "")})
        global _AUDIT_READ
        _AUDIT_READ = lambda r: real[r]  # noqa: E731
        check = lambda: process_audit(lambda r: _AUDIT_READ(r))  # noqa: E731
        self.assert_green_then_red(check, [
            ("run-take-imports-socket", with_added("box/run_take.py", "\nimport socket\n")),
            ("preflight-imports-subprocess", with_added("box/preflight.py", "\nimport subprocess\n")),
            ("take-config-kills", with_added("box/take_config.py", "\nos.kill(1, 9)\n")),
            ("second-run-site", with_added("box/run_take.py", "\ndef g():\n    subprocess.run([])\n")),
            ("planted-dropped", lambda: mock.patch.dict(PLANTED, {"posix-spawn-import": ("box/x.py", "x = 1\n")})),
        ])


_AUDIT_READ = None


if __name__ == "__main__":
    if sys.argv[1:] == ["--process-audit"]:
        problems = process_audit()
        for p in problems:
            print(f"process audit: {p}")
        print(f"process audit: {len(PLANTED)} planted positives caught, {len(BOX_MODULES)} modules read, "
              f"{len(problems)} problem(s)")
        sys.exit(1 if problems else 0)
    unittest.main(verbosity=2)
