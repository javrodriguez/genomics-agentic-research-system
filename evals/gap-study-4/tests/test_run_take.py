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


ROUND3_WORDS = _round3_leak_words()
LEAK_WORDS = ROUND3_WORDS + LANE_LEAD_WORDS


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
_ORIGINALS = [(_mod, _name, getattr(_mod, _name)) for _mod, _name in GUARDED]
_TRIPS = {(id(_mod), _name): _tripwire(f"{_mod.__name__}.{_name}") for _mod, _name in GUARDED}


def _arm_guard():
    for mod, name in GUARDED:
        setattr(mod, name, _TRIPS[(id(mod), name)])


def _disarm_guard():
    for mod, name, original in _ORIGINALS:
        setattr(mod, name, original)


def _patched_now() -> list:
    """The guarded names that hold this module's tripwire right now."""
    return [f"{mod.__name__}.{name}" for mod, name in GUARDED if getattr(mod, name) is _TRIPS[(id(mod), name)]]


def setUpModule():
    """Arm the guard for every test of this module, never at import: test_round4 imports every test module in one
    process, and an import-time guard would trip in the others (the wave 4 merge's fix)."""
    _arm_guard()
    _module_set_up_extra()


def tearDownModule():
    _module_tear_down_extra()
    _disarm_guard()

from box import run_take as rt  # noqa: E402
from box import preflight as pf_mod  # noqa: E402
import harness_bookkeeping  # noqa: E402
import agent_adapter  # noqa: E402

# W4B1-9: run_take always checks os.environ too, so for this module's tests the process drops every refused name
# from its own copy (names only; the values are restored untouched at tearDownModule, never read).
_REFUSED_UNIVERSE = set(rt.API_KEY_VARIABLES) | set(rt.BILLING_ROUTE_VARIABLES) | set(rt.SUBSCRIPTION_TOKEN_VARIABLES) \
    | set(rt.VENDOR_KEY_VARIABLES)
_ENV_SET_ASIDE = {}


def _module_set_up_extra():
    for name in list(os.environ):
        if name in _REFUSED_UNIVERSE:
            _ENV_SET_ASIDE[name] = os.environ.pop(name)


def _module_tear_down_extra():
    os.environ.update(_ENV_SET_ASIDE)
    _ENV_SET_ASIDE.clear()

# ------------------------------------------------------------------------------------------------- helpers
ID = {k: (c * 64) for k, c in (("net", "a"), ("proxy", "b"), ("side", "c"), ("take", "d"), ("other", "e"))}
IMAGE = "sha256:" + "f" * 64
FAKE_VALUE = "FAKEVALUE-0123456789abcdef-PLANTED"
CALLER = {"PATH": "/usr/bin:/bin", "HOME": "/home/op", "DOCKER_HOST": "unix:///run/user/1000/docker.sock",
          "XDG_RUNTIME_DIR": "/run/user/1000", "UNRELATED": "x"}
ARMS = (harness_bookkeeping.CLAUDE_CODE, "codex", "gemini")
LOGINS = dict(zip(ARMS, ("CLAUDE_CODE_OAUTH_TOKEN", "CODEX_API_KEY", "GEMINI_API_KEY")))


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
    def test_the_guard_starts_no_patch_at_import(self):
        """Recorded at the very end of this module's import: no guarded name was patched then. Inside a test every
        guarded name holds the tripwire (setUpModule armed it), so the record can see a patch."""
        self.assertEqual(_PATCHED_AT_IMPORT, [])
        self.assertEqual(len(_patched_now()), len(GUARDED))

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
        """The read is checked by count and shape only: no round 3 word is ever named in a committed file."""
        self.assertGreaterEqual(len(ROUND3_WORDS), 10)
        self.assertTrue(all(isinstance(w, str) and w for w in ROUND3_WORDS))
        self.assertTrue(set(LEAK_WORDS) >= set(LANE_LEAD_WORDS))
        self.assertEqual(len(LEAK_WORDS), len(ROUND3_WORDS) + len(LANE_LEAD_WORDS))


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
    "--workdir", "/srv/w/t1/tree", "--entrypoint", "sleep", IMAGE, "infinity"]
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
            ("no-entrypoint", patched(rt, "create_argv", lambda s: (lambda a: a[:a.index("--entrypoint")]
                                      + a[a.index("--entrypoint") + 2:-1] + ["sleep", "infinity"])(orig(s)))),
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
    with open(path, "w", encoding="utf-8") as fh:
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
        inner = ["gemini", "-m", "gemini-3.8-flash"] if harness == rt.GEMINI else ["agent-cli"]
        return rt.exec_argv(ID["take"], inner, user=rt.AGENT_USER, workdir="/srv/w/t1/tree",
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
                                if arm == rt.CODEX:
                                    # Subscription transition blocks launch independently; keep
                                    # witnessing the underlying name refusal without a login read.
                                    rt.check_environment(arm, dict(CALLER, **{var: FAKE_VALUE}))
                                self.exec_for(arm, dict(CALLER, **{var: FAKE_VALUE}))
                        else:
                            if arm == rt.CODEX:
                                rt.check_environment(arm, dict(CALLER, **{var: FAKE_VALUE}))
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
            # Departure w12a-2: the one table is TAKE_ENV (ruling docs-1); HARNESS_ENV is a view derived from it.
            bad = dict(rt.TAKE_ENV, **{arm: dict(rt.TAKE_ENV[arm], **{other: "x"})})
            with mock.patch.object(rt, "TAKE_ENV", bad), filled():
                try:
                    if arm == rt.CODEX:
                        rt.check_environment(arm, CALLER, rt.TAKE_ENV[arm])
                    else:
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
            expected = closed - {LOGINS[arm]}
            if arm == rt.GEMINI:
                expected |= {"GEMINI_CLI_EXP_AGENT"}
            if got != expected:
                out.append(f"{arm}: refused set {sorted(got ^ expected)} off")
        if "CLAUDE_CODE_OAUTH_TOKEN" not in rt.refused_variables(rt.CODEX):
            out.append("arm O admits Anthropic's token")
        return out

    def test_refused_sets(self):
        self.assert_green_then_red(self.check_refused_sets, [
            ("own-login-refused", patched(rt, "LOGIN_VARIABLE", dict(rt.LOGIN_VARIABLE, codex="NOT_A_VAR"))),
            ("vendor-list-short", patched(rt, "VENDOR_KEY_VARIABLES", ("CODEX_API_KEY", "GEMINI_API_KEY"))),
        ])

    def check_own_environ(self):
        out = []
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": FAKE_VALUE}):
            try:
                rt.check_environment(rt.CODEX, {})
                out.append("an empty caller_env switched off the refusal of os.environ")
            except rt.Refused:
                pass
        with mock.patch.dict(os.environ, {"CODEX_API_KEY": FAKE_VALUE}):
            try:
                with filled():
                    self.exec_for(rt.CLAUDE_CODE)
                out.append("a refused name in os.environ passed beside a clean caller_env")
            except rt.Refused:
                pass
        return out

    def test_own_environ_always_checked(self):
        self.assert_green_then_red(self.check_own_environ, [
            ("caller-env-replaces", patched(rt, "_own_environment", lambda: {})),
        ])

    def test_unknown_harness_refused(self):
        for h in ("fake-second", "", None, "Codex"):
            with self.assertRaises(rt.Refused):
                rt.refused_variables(h)
            with self.assertRaises(rt.Refused):
                rt.exec_argv(ID["take"], ["x"], user=rt.AGENT_USER, workdir="/", harness=h, run_tree="/a/t",
                             login_file=self.logins[rt.CODEX], caller_env=CALLER)


# ----------------------------------------------------------------------------------- exec argv and the login
class TestExecArgv(MutantCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="w-")
        self.login = plant_login(self.tmp, "CLAUDE_CODE_OAUTH_TOKEN")

    def check(self):
        out = []
        with filled():
            argv, env = rt.exec_argv(ID["take"], ["agent-cli", "-p", "x"], user=rt.AGENT_USER,
                                     workdir="/srv/w/t1/tree", harness=rt.CLAUDE_CODE, run_tree="/srv/w/t1/tree",
                                     login_file=self.login, caller_env=CALLER)
        t = "/srv/w/t1/tree/.tmp"
        # Departure w12a-2 (ruling docs-1): the values ride as the launcher's NAME=VALUE pairs, the agent starting
        # from an empty environment plus its TAKE_ENV row; the login still rides as `-e NAME` only.
        want = ["docker", "exec", "--user", "10001:10001", "--workdir", "/srv/w/t1/tree",
                "-e", "CLAUDE_CODE_OAUTH_TOKEN", ID["take"], *rt.LAUNCHER, "CLAUDE_CODE_OAUTH_TOKEN", "13",
                "CLAUDE_CODE_DISABLE_AUTO_MEMORY=1", "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1",
                "CLAUDE_CONFIG_DIR=/opt/cfg", "DISABLE_AUTOUPDATER=1", "ENABLE_CLAUDEAI_MCP_SERVERS=false",
                "FAKE_FALLBACK_A=1", "HOME=/opt/cfg", "HTTPS_PROXY=http://proxy:3128", "LANG=C.UTF-8",
                f"PATH={rt.TAKE_PATH}", f"TEMP={t}", f"TMP={t}", f"TMPDIR={t}", "agent-cli", "-p", "x"]
        if argv != want:
            out.append(f"exec argv differs: {argv}")
        if any(FAKE_VALUE in a for a in argv):
            out.append("the login value is in argv")
        if env.get("CLAUDE_CODE_OAUTH_TOKEN") != FAKE_VALUE:
            out.append("the login value is not in the client env")
        extra = set(env) - set(rt.RUNTIME_ENV_NAMES) - set(rt.HARNESS_ENV[rt.CLAUDE_CODE]) - {
            "TMPDIR", "TMP", "TEMP", "FAKE_FALLBACK_A", "CLAUDE_CODE_OAUTH_TOKEN"}
        if extra:
            out.append(f"the client env carries {sorted(extra)}")
        if env.get("DOCKER_HOST") != CALLER["DOCKER_HOST"]:
            out.append("the runtime's DOCKER_HOST did not ride")
        for bad_user in ("0:0", rt.KEEPALIVE_USER, "10002:10002"):
            try:
                with filled():
                    rt.exec_argv(ID["take"], ["x"], user=bad_user, workdir="/", harness=rt.CLAUDE_CODE,
                                 run_tree="/srv/w/t1/tree", login_file=self.login, caller_env=CALLER)
                out.append(f"an exec as {bad_user} was built")
            except rt.Refused:
                pass
        try:
            rt.exec_argv(ID["take"], ["x"], user=rt.AGENT_USER, workdir="/", harness=rt.CLAUDE_CODE,
                         run_tree="/srv/w/t1/tree", login_file=self.login, caller_env=CALLER)
            out.append("an exec was built while FALLBACK_ENV is PENDING")
        except rt.NotReady:
            pass
        for h in ("codex", "gemini"):
            inner = ["gemini", "-m", "gemini-3.8-flash"] if h == rt.GEMINI else ["x"]
            lf = plant_login(self.tmp, rt.LOGIN_VARIABLE[h])
            try:
                rt.exec_argv(ID["take"], inner, user=rt.AGENT_USER, workdir="/", harness=h,
                             run_tree="/srv/w/t1/tree", login_file=lf, caller_env=CALLER)
                out.append(f"a {h} exec was built while its billing-route list is PENDING")
            except rt.NotReady:
                pass
            if h == rt.CODEX:
                try:
                    with filled():
                        rt.exec_argv(ID["take"], inner, user=rt.AGENT_USER, workdir="/", harness=h,
                                     run_tree="/srv/w/t1/tree", login_file=lf, caller_env=CALLER)
                    out.append("Codex legacy API exec was admitted during subscription transition")
                except rt.NotReady:
                    pass
                continue
            with filled():
                a, e = rt.exec_argv(ID["take"], inner, user=rt.AGENT_USER, workdir="/", harness=h,
                                    run_tree="/srv/w/t1/tree", login_file=lf, caller_env=CALLER)
            home = {"codex": "CODEX_HOME=/opt/cfg", "gemini": "GEMINI_CLI_HOME=/opt/cfg"}[h]
            if home not in a or "-e" not in a or rt.LOGIN_VARIABLE[h] not in a or FAKE_VALUE in " ".join(a):
                out.append(f"{h} exec argv off: {a}")
            if any(x.startswith("CLAUDE") for x in a):
                out.append(f"{h} exec carries a Claude variable")
        return out

    def test_exec_argv(self):
        orig = rt.exec_argv

        def value_in_argv(*a, **k):
            argv, env = orig(*a, **k)
            return [x if x != "CLAUDE_CODE_OAUTH_TOKEN" else f"{x}={env[x]}" for x in argv], env

        self.assert_green_then_red(self.check, [
            ("value-in-argv", patched(rt, "exec_argv", value_in_argv)),
            ("environ-copied", patched(rt, "runtime_env", lambda c=None: dict(c or os.environ))),
            ("no-user-check", patched(rt, "AGENT_USER", "0:0")),
            ("fallback-ignored", patched(rt, "exec_values", lambda h, r: dict(rt.HARNESS_ENV[h]))),
            ("tmp-variables-dropped", patched(rt, "RUN_TREE_TMPDIR_VARIABLES", ())),
        ])

    def check_config_home(self):
        """W4B2-1: a plain exec carries only a harness's config-home name, only at the config mount."""
        out = []
        if rt.agent_exec_argv(ID["take"], ["x"], config_home={"CODEX_HOME": "/opt/cfg"})[6:8] != [
                "-e", "CODEX_HOME=/opt/cfg"]:
            out.append("a config home was not carried")
        # W4B3-1: the name cases carry the right value, so only the name clause can refuse them.
        for name, home in (("login name", {"CODEX_API_KEY": rt.CONFIG_MOUNT}),
                           ("not a config home", {"PATH": rt.CONFIG_MOUNT}),
                           ("wrong value", {"CODEX_HOME": "/tmp"}),
                           ("two entries", {"CODEX_HOME": rt.CONFIG_MOUNT, "CLAUDE_CONFIG_DIR": rt.CONFIG_MOUNT})):
            try:
                argv = rt.agent_exec_argv(ID["take"], ["x"], config_home=home)
                out.append(f"{name} accepted: {[a for a in argv if '=' in a]}"
                           .replace(FAKE_VALUE, "<planted>"))
            except rt.Refused as e:
                if FAKE_VALUE in str(e):
                    out.append("the refusal carries the value")
        return out

    def test_config_home_refusals(self):
        self.assert_green_then_red(self.check_config_home, [
            ("guard-dropped", patched(rt, "_config_home_allowed", lambda name, value: True)),
            ("name-unchecked", patched(rt, "_config_home_allowed", lambda name, value: value == rt.CONFIG_MOUNT)),
            ("many-entries", patched(rt, "CONFIG_HOME_MAX", 2)),
        ])

    def test_agent_exec_argv(self):
        self.assertEqual(rt.agent_exec_argv(ID["take"], ["python3", "-c", "x"]),
                         ["docker", "exec", "--user", "10001:10001", "--workdir", "/", ID["take"], "python3", "-c",
                          "x"])
        for bad in ("name", "d" * 12):
            with self.assertRaises(rt.Refused):
                rt.agent_exec_argv(bad, ["x"])


LOGIN_REFUSALS = {
    "mode-644": dict(mode=0o644),
    "mode-400": dict(mode=0o400),
    "two-lines": dict(text=f"CLAUDE_CODE_OAUTH_TOKEN={FAKE_VALUE}\nX=1\n"),
    "no-newline": dict(text=f"CLAUDE_CODE_OAUTH_TOKEN={FAKE_VALUE}"),
    "short": dict(text="CLAUDE_CODE_OAUTH_TOKEN=FAKEVALUE-short\n"),
    "quote": dict(text=f'CLAUDE_CODE_OAUTH_TOKEN="{FAKE_VALUE}"\n'),
    "space": dict(text=f"CLAUDE_CODE_OAUTH_TOKEN= {FAKE_VALUE}\n"),
    "cr": dict(text=f"CLAUDE_CODE_OAUTH_TOKEN={FAKE_VALUE}\r\n"),
    "other-name": dict(text=f"CODEX_API_KEY={FAKE_VALUE}\n"),
    "export": dict(text=f"export CLAUDE_CODE_OAUTH_TOKEN={FAKE_VALUE}\n"),
    "non-ascii": dict(text=f"CLAUDE_CODE_OAUTH_TOKEN={FAKE_VALUE}é\n"),
    "empty": dict(text=""),
    "19-characters": dict(text="CLAUDE_CODE_OAUTH_TOKEN=FAKEVALUE-PLANTED-1\n"),
}
LOGIN_ACCEPTED = {"20-characters": "FAKEVALUE-PLANTED-12", "planted": FAKE_VALUE}


class TestReadLogin(MutantCase):
    def check(self):
        out = []
        tmp = tempfile.mkdtemp(prefix="w-")
        good = plant_login(tmp, "CLAUDE_CODE_OAUTH_TOKEN")
        if rt.read_login(good, "CLAUDE_CODE_OAUTH_TOKEN") != FAKE_VALUE:
            out.append("a good login was not read")
        for name, value in LOGIN_ACCEPTED.items():
            d = tempfile.mkdtemp(prefix="w-")
            try:
                if rt.read_login(plant_login(d, "CLAUDE_CODE_OAUTH_TOKEN", value), "CLAUDE_CODE_OAUTH_TOKEN") != value:
                    out.append(f"{name}: read back wrong")
            except rt.LoginRefused:
                out.append(f"{name} refused")
        for name, kw in LOGIN_REFUSALS.items():
            d = tempfile.mkdtemp(prefix="w-")
            path = plant_login(d, "CLAUDE_CODE_OAUTH_TOKEN", **kw)
            try:
                rt.read_login(path, "CLAUDE_CODE_OAUTH_TOKEN")
                out.append(f"{name} accepted")
            except rt.LoginRefused as e:
                if FAKE_VALUE in str(e) or "FAKEVALUE" in str(e) or e.__cause__ is not None:
                    out.append(f"{name}: the refusal carries the value")
                if path not in str(e):
                    out.append(f"{name}: the refusal does not name the file")
        repo = tempfile.mkdtemp(prefix="w-")
        os.makedirs(os.path.join(repo, ".git"))
        os.makedirs(os.path.join(repo, "sub"))
        inside = plant_login(os.path.join(repo, "sub"), "CLAUDE_CODE_OAUTH_TOKEN")
        link = os.path.join(tmp, "link.line")
        os.symlink(good, link)
        for name, path in (("inside-repo", inside), ("symlink", link), ("relative", "x.line"),
                           ("missing", os.path.join(tmp, "nope"))):
            try:
                rt.read_login(path, "CLAUDE_CODE_OAUTH_TOKEN")
                out.append(f"{name} accepted")
            except rt.LoginRefused:
                pass
        with mock.patch.object(rt.os, "getuid", lambda: os.stat(good).st_uid + 1):
            try:
                rt.read_login(good, "CLAUDE_CODE_OAUTH_TOKEN")
                out.append("another owner's file accepted")
            except rt.LoginRefused:
                pass
        try:
            rt.read_login(good, "SOME_OTHER_NAME")
            out.append("an unknown variable name accepted")
        except rt.LoginRefused:
            pass
        return out

    def test_read_login(self):
        def naive(path, name):
            with open(path) as fh:
                return fh.read().split("=", 1)[1].strip()

        self.assert_green_then_red(self.check, [
            ("naive-reader", patched(rt, "read_login", naive)),
            ("no-repo-check", patched(rt, "outside_every_repository", lambda p: True)),
            ("max-bytes-0", patched(rt, "LOGIN_MAX_BYTES", 0)),
        ])

    def test_no_real_login_path(self):
        src = open(rt.__file__, encoding="utf-8").read()
        self.assertNotIn("box-auth", src)
        self.assertNotRegex(src, r"[\w/-]\.env[\"'\s]")
        for p in pyinspect_params(rt.read_login):
            self.assertIsNone(p.default if p.default is not p.empty else None)


def pyinspect_params(fn):
    import inspect
    return list(inspect.signature(fn).parameters.values())


# ------------------------------------------------------------------------------------------ launch and teardown
def sidecar_launch(expect=None, tree="/srv/w/t1/tree", ev="/srv/w/t1/rec/ev"):
    # The sidecar's fixed privilege-drop launch (0b6f60f9's accepted delta): boot user 0:0, the four boot
    # capabilities in Docker's inspect spelling, no entrypoint, the setpriv launcher in the command.
    exp = expect or {"user": "0:0", "network_mode": "none", "cap_drop": ["ALL"],
                     "cap_add": ["CAP_DAC_READ_SEARCH", "CAP_SETGID", "CAP_SETPCAP", "CAP_SETUID"],
                     "security_opt": ["no-new-privileges"], "privileged": False,
                     "pid_mode": "", "mounts": [{"source": tree, "destination": tree, "rw": False},
                                                {"source": ev, "destination": "/srv/ev", "rw": True}],
                     "image": SIDE_IMAGE, "cmd": side_cmd(tree), "entrypoint": []}
    return rt.SidecarLaunch(
        create_argv=("docker", "create", "--network", "none", "side-image"),
        start_argv_for=lambda i: ["docker", "start", i],
        ctl_argv_for=lambda i, c, l=None: ["docker", "exec", i, "python3", "-I", "-B", "/opt/w/sidecar.py", "ctl", c]
        + ([l] if l else []),
        rm_argv_for=lambda i: ["docker", "rm", "--force", i],
        expect=exp)


def proxy_launch(user="13:13"):
    return rt.ProxyLaunch(image="sha256:" + "9" * 64, conf_source="/srv/w/t1/rec/proxy.conf",
                          conf_target="/etc/squid/squid.conf", command=("squid", "-N", "-f", "/etc/squid/squid.conf"),
                          user=user, alias="proxy")


SIDE_IMAGE = "sha256:" + "5" * 64


def side_cmd(tree):
    return ["/usr/bin/setpriv", "--reuid=10002", "--regid=10002", "--clear-groups",
            "--inh-caps=-all,+dac_read_search", "--ambient-caps=-all,+dac_read_search",
            "--bounding-set=-all,+dac_read_search", "--no-new-privs", "--", "python3", "-I", "-B", "/opt/w/sidecar.py",
            "serve", "--run-tree", tree, "--evidence", "/srv/ev"]


def side_inspect(tree, ev):
    return [{"Image": SIDE_IMAGE, "Config": {"User": "0:0", "Entrypoint": [], "Cmd": side_cmd(tree)},
             "HostConfig": {"NetworkMode": "none", "CapDrop": ["ALL"],
                            "CapAdd": ["CAP_DAC_READ_SEARCH", "CAP_SETGID", "CAP_SETPCAP", "CAP_SETUID"],
                            "SecurityOpt": ["no-new-privileges"], "Privileged": False, "PidMode": ""},
             "Mounts": [{"Type": "bind", "Source": tree, "Destination": tree, "RW": False},
                        {"Type": "bind", "Source": ev, "Destination": "/srv/ev", "RW": True}]}]


def take_inspect(s):
    return [{"Image": s.image,
             "Config": {"User": "10003:10003", "Entrypoint": ["sleep"], "Cmd": ["infinity"], "Env": [],
                        "WorkingDir": s.run_tree},
             "HostConfig": {"NetworkMode": s.network, "CapDrop": ["ALL"], "CapAdd": None,
                            "SecurityOpt": ["no-new-privileges"], "Privileged": False, "Devices": None,
                            "PidMode": "", "PidsLimit": s.pids_limit, "Memory": s.memory,
                            "MemoryReservation": s.memory_reservation, "NanoCpus": s.nano_cpus()},
             "Mounts": [{"Type": "bind", "Source": s.run_tree, "Destination": s.run_tree, "RW": True},
                        {"Type": "bind", "Source": s.config_dir, "Destination": "/opt/cfg", "RW": True}]}]


class Launch:
    """A tmp take: spec, record folder, sidecar and proxy records, and the ten-step launch script."""

    def __init__(self):
        self.tmp = tempfile.mkdtemp(prefix="w-")
        self.tree = os.path.join(self.tmp, "tree")
        self.cfg = os.path.join(self.tmp, "cfg")
        self.rec = os.path.join(self.tmp, "rec")
        self.ev = os.path.join(self.rec, "ev")
        for d in (self.tree, self.cfg, self.ev):
            os.makedirs(d)
        self.spec = spec(run_tree=self.tree, config_dir=self.cfg)
        self.sidecar = sidecar_launch(tree=self.tree, ev=self.ev)
        self.proxy = proxy_launch()

    def script(self):
        return [
            (["docker", "network", "create", "--internal"], ok(ID["net"] + "\n")),
            (["docker", "create", "--pull=never", "--network", ID["net"], "--network-alias", "proxy"], ok(ID["proxy"])),
            (["docker", "network", "connect", "bridge", ID["proxy"]], ok()),
            (["docker", "start", ID["proxy"]], ok()),
            (["docker", "create", "--network", "none"], ok(ID["side"])),
            (["docker", "container", "inspect", ID["side"]], ok(json.dumps(side_inspect(self.tree, self.ev)))),
            (["docker", "start", ID["side"]], ok()),
            (["docker", "create", "--pull=never", "--network", ID["net"], "--user", "10003:10003"], ok(ID["take"])),
            (["docker", "container", "inspect", ID["take"]], ok(json.dumps(take_inspect(self.spec)))),
            (["docker", "start", ID["take"]], ok()),
        ]

    def launch(self, fake):
        return rt.launch(fake, self.spec, sidecar=self.sidecar, proxy=self.proxy, record_dir=self.rec,
                         caller_env=CALLER)


@contextlib.contextmanager
def inspect_ok():
    with mock.patch.object(rt, "INSPECT_STATUS", "confirmed-in-test"):
        yield


TEARDOWN_PREFIXES = [["docker", "rm", "--force", ID["take"]],
                     ["docker", "exec", ID["side"], "python3", "-I", "-B", "/opt/w/sidecar.py", "ctl", "finish"],
                     ["docker", "logs", ID["proxy"]], ["docker", "rm", "--force", ID["side"]],
                     ["docker", "rm", "--force", ID["proxy"]], ["docker", "network", "rm", ID["net"]]]


class TestLaunch(MutantCase):
    def check_launch(self):
        out = []
        L = Launch()
        fake = FakeRuntime(L.script())
        with inspect_ok():
            launched = L.launch(fake)
        if fake.unexpected or fake.script:
            out.append(f"launch calls off script: {fake.unexpected or fake.script}")
        if (launched.network_id, launched.proxy_id, launched.sidecar_id, launched.take_id) != (
                ID["net"], ID["proxy"], ID["side"], ID["take"]):
            out.append("an id was not recorded")
        path = os.path.join(L.rec, "launch.json")
        if not os.path.exists(path):
            out.append("no launch record")
        else:
            rec = json.load(open(path))
            if not rec.get("ok") or [s["step"] for s in rec["steps"]] != [
                    "network-create", "proxy-create", "proxy-connect", "proxy-start", "sidecar-create",
                    "sidecar-inspect", "sidecar-start", "take-create", "take-inspect", "take-start"]:
                out.append("the launch record's steps are off")
            if not all("inspect" in s for s in rec["steps"] if s["step"].endswith("inspect")):
                out.append("an inspect is missing from the launch record")
            if rec.get("take_id") != ID["take"] or rec.get("config_dir") != L.cfg:
                out.append("the launch record lacks the take id or the config folder")
        proxy_argv = fake.calls[1][0]
        for pair in (["--cap-drop", "ALL"], ["--security-opt", "no-new-privileges"]):
            if not any(proxy_argv[i:i + 2] == pair for i in range(len(proxy_argv))):
                out.append(f"the proxy create argv lacks {' '.join(pair)}")
        if "type=bind,source=/srv/w/t1/rec/proxy.conf,target=/etc/squid/squid.conf,readonly" not in proxy_argv \
                or proxy_argv[-4:] != ["squid", "-N", "-f", "/etc/squid/squid.conf"] or "13:13" not in proxy_argv:
            out.append(f"the proxy create argv is off: {proxy_argv}")
        if any(env != {k: CALLER[k] for k in rt.RUNTIME_ENV_NAMES} for _, env in fake.calls):
            out.append("a launch call's env is not the runtime's needs alone")
        if any(a[:2] == ["docker", "exec"] for a, _ in fake.calls):
            out.append("launch ran an exec")
        return out

    def test_launch(self):
        def no_record(path, doc):
            return None
        self.assert_green_then_red(self.check_launch, [
            ("no-launch-record", patched(rt, "_write_json", no_record)),
            ("proxy-not-readonly", patched(rt, "proxy_create_argv", lambda n, p: [
                a.replace(",readonly", "") for a in ORIG_PROXY_CREATE(n, p)])),
            ("default-network", patched(rt, "DEFAULT_NETWORK", "host")),
            ("proxy-keeps-caps", patched(rt, "proxy_create_argv", lambda n, p: drop_pair(ORIG_PROXY_CREATE(n, p),
                                                                                         "--cap-drop"))),
            ("proxy-new-privileges", patched(rt, "proxy_create_argv", lambda n, p: drop_pair(
                ORIG_PROXY_CREATE(n, p), "--security-opt"))),
        ])

    def check_failures(self):
        """A failure at every step (exit 1, a timeout, a bad id, an inspect mismatch) tears down exactly what was
        made, by recorded id, runs no harness exec, writes the launch record, and raises LaunchError."""
        out = []
        n = len(Launch().script())
        made_after = {0: [], 1: ["net"], 2: ["net", "proxy"], 3: ["net", "proxy"], 4: ["net", "proxy"],
                      5: ["net", "proxy", "side"], 6: ["net", "proxy", "side"], 7: ["net", "proxy", "side"],
                      8: ["net", "proxy", "side", "take"], 9: ["net", "proxy", "side", "take"]}
        cases = [(i, how) for i in range(n) for how in ("exit", "timeout")]
        cases += [(0, "bad-id"), (4, "bad-id"), (7, "bad-id"), (5, "mismatch"), (8, "mismatch")]
        for i, how in cases:
            L = Launch()
            script = L.script()[:i + 1]
            prefix, answer = script[i]
            if how == "exit":
                script[i] = (prefix, rt.Completed(1, "", "boom"))
            elif how == "timeout":
                script[i] = (prefix, TimeoutError("slow"))
            elif how == "bad-id":
                script[i] = (prefix, ok("not-an-id"))
            else:
                bad = json.loads(answer.stdout)
                bad[0]["HostConfig"]["NetworkMode"] = "bridge"
                script[i] = (prefix, ok(json.dumps(bad)))
            made = made_after[i] if how in ("exit", "timeout") or i not in (0, 4, 7) else made_after[i]
            if how == "mismatch":
                made = made_after[i]
            rm = []
            if "take" in made:
                rm.append((["docker", "rm", "--force", ID["take"]], ok()))
            if "proxy" in made:
                rm.append((["docker", "logs", ID["proxy"]], ok("log\n")))
            if "side" in made:
                rm.append((["docker", "rm", "--force", ID["side"]], ok()))
            if "proxy" in made:
                rm.append((["docker", "rm", "--force", ID["proxy"]], ok()))
            if "net" in made:
                rm.append((["docker", "network", "rm", ID["net"]], ok()))
            fake = FakeRuntime(script + rm)
            try:
                with inspect_ok():
                    L.launch(fake)
                out.append(f"step {i} {how}: launch did not fail")
                continue
            except rt.LaunchError as e:
                launched = e.launched
            if fake.unexpected or fake.script:
                out.append(f"step {i} {how}: teardown off script {fake.unexpected or [s[0] for s in fake.script]}")
            if any(a[:2] == ["docker", "exec"] for a, _ in fake.calls):
                out.append(f"step {i} {how}: an exec ran")
            removed = {a[-1] for a, _ in fake.calls if a[:2] == ["docker", "rm"] or a[:3] == ["docker", "network", "rm"]}
            if removed != {ID[k] for k in made}:
                out.append(f"step {i} {how}: removed {sorted(removed)} for made {made}")
            rec = os.path.join(L.rec, "launch.json")
            if not os.path.exists(rec) or json.load(open(rec)).get("ok") is not False:
                out.append(f"step {i} {how}: no failed launch record")
            if launched.ok:
                out.append(f"step {i} {how}: the carried record says ok")
        return out

    def test_failures(self):
        self.assert_green_then_red(self.check_failures, [
            ("no-teardown", patched(rt, "_teardown_partial", lambda *a: None)),
            ("ids-not-recorded", patched(rt, "_new_id", lambda c, what: c.stdout.strip() or "x")),
            ("no-inspect-check", patched(pf_mod, "inspect_mismatches", lambda *a, **k: [])),
        ])

    def test_refused_before_anything(self):
        def check():
            out = []
            for name, kw in (("pending-user", dict(proxy=proxy_launch(rt.PENDING))),
                             ("root-proxy", dict(proxy=proxy_launch("0:0"))),
                             ("pending-spec", dict(spec=rt.TakeSpec(image=IMAGE, run_tree="/a/t", config_dir="/a/c",
                                                                   network=ID["net"]))),
                             ("sidecar-not-create", dict(sidecar=rt.SidecarLaunch(("docker", "run"), None, None,
                                                                                  None, {})))):
                L = Launch()
                fake = FakeRuntime()
                args = dict(spec=L.spec, sidecar=L.sidecar, proxy=L.proxy, record_dir=L.rec, caller_env=CALLER)
                args.update(kw)
                try:
                    with inspect_ok():
                        rt.launch(fake, args.pop("spec"), **args)
                    out.append(f"{name}: launched")
                except (rt.NotReady, rt.Refused) as e:
                    if name == "pending-user" and not isinstance(e, rt.NotReady):
                        out.append("a PENDING proxy user raised Refused, not NotReady")
                if fake.calls:
                    out.append(f"{name}: the runtime was called")
            return out
        self.assert_green_then_red(check, [
            ("no-proxy-check", patched(rt, "_check_proxy", lambda p: None)),
            ("no-sidecar-check", patched(rt, "_check_sidecar", lambda s: None)),
        ])

    def check_pending_refused_first(self):
        """W4B1-2: a PENDING inspect spelling, or a PENDING value in the sidecar's expectation, is NotReady before
        any runtime call."""
        out = []
        L = Launch()
        fake = FakeRuntime()
        try:
            L.launch(fake)
            out.append("launched with the inspect spellings PENDING")
        except rt.NotReady:
            pass
        except Exception as e:
            out.append(f"PENDING inspect spellings raised {type(e).__name__}, not NotReady")
        if fake.calls:
            out.append(f"{len(fake.calls)} runtime calls before the PENDING refusal")
        L = Launch()
        L.sidecar = rt.SidecarLaunch(L.sidecar.create_argv, L.sidecar.start_argv_for, L.sidecar.ctl_argv_for,
                                     L.sidecar.rm_argv_for, dict(L.sidecar.expect, cap_add=rt.PENDING))
        fake = FakeRuntime()
        try:
            with inspect_ok():
                L.launch(fake)
            out.append("launched with a PENDING sidecar expectation")
        except rt.NotReady:
            pass
        except Exception as e:
            out.append(f"a PENDING sidecar expectation raised {type(e).__name__}, not NotReady")
        if fake.calls:
            out.append(f"{len(fake.calls)} runtime calls before the PENDING sidecar refusal")
        return out

    def test_pending_refused_before_any_call(self):
        self.assert_green_then_red(self.check_pending_refused_first, [
            ("no-ready-gate", patched(rt, "_check_launch_ready", lambda sidecar: None)),
        ])

    def check_network_is_launchs(self):
        """W4B1-1: the take is created on, and inspected against, the network launch made, never the spec's."""
        out = []
        L = Launch()
        L.spec = spec(run_tree=L.tree, config_dir=L.cfg, network=ID["other"])
        on_net = spec(run_tree=L.tree, config_dir=L.cfg, network=ID["net"])
        script = L.script()
        script[7] = (["docker", "create", "--pull=never", "--network", ID["net"], "--user", "10003:10003"],
                     ok(ID["take"]))
        script[8] = (["docker", "container", "inspect", ID["take"]], ok(json.dumps(take_inspect(on_net))))
        fake = FakeRuntime(script)
        try:
            with inspect_ok():
                launched = L.launch(fake)
        except rt.LaunchError as e:
            return [f"launch failed: {e}"] + [f"off script: {a}" for a in fake.unexpected]
        if fake.unexpected:
            out.append(f"off script: {fake.unexpected}")
        take_create = [a for a, _ in fake.calls if a[:2] == ["docker", "create"] and "10003:10003" in a]
        if len(take_create) != 1 or take_create[0][take_create[0].index("--network") + 1] != ID["net"]:
            out.append("the take was not created on launch's network")
        if getattr(launched, "spec", None) is None or launched.spec.network != ID["net"]:
            out.append("the launched record does not carry the spec on launch's network")
        return out

    def test_network_is_launchs(self):
        self.assert_green_then_red(self.check_network_is_launchs, [
            ("stale-spec-network", patched(rt, "_on_network", lambda s, n: s)),
        ])

    def check_proxy_uid(self):
        out = []
        for user in ("0", "0:0", "0:5", "00:00", "000", "root", "root:5"):
            try:
                rt._check_proxy(proxy_launch(user))
                out.append(f"proxy user {user!r} accepted")
            except rt.Refused:
                pass
        for user in ("1", "5:0", "01:00", "100:100", "13:13", "proxy", "squid"):
            try:
                rt._check_proxy(proxy_launch(user))
            except rt.Refused:
                out.append(f"near-miss proxy user {user!r} refused")
        return out

    def test_proxy_uid(self):
        self.assert_green_then_red(self.check_proxy_uid, [
            ("uid-string-compare", patched(rt, "_proxy_uid", lambda u: 1)),
        ])


ORIG_PROXY_CREATE = rt.proxy_create_argv


def drop_pair(argv, flag):
    i = argv.index(flag)
    return argv[:i] + argv[i + 2:]


class TestTeardown(MutantCase):
    def launched(self):
        L = Launch()
        fake = FakeRuntime(L.script())
        with inspect_ok():
            return L, L.launch(fake)

    def check_order(self):
        out = []
        L, launched = self.launched()
        fake = FakeRuntime([(TEARDOWN_PREFIXES[0], ok()), (TEARDOWN_PREFIXES[1], ok('{"ok": true}')),
                            (TEARDOWN_PREFIXES[2], ok("proxy line 1\n", "squid started\n"))]
                           + [(p, ok()) for p in TEARDOWN_PREFIXES[3:]])
        rec = rt.teardown(fake, launched, sidecar=L.sidecar, record_dir=L.rec, caller_env=CALLER)
        if fake.unexpected or fake.script:
            out.append(f"teardown off its order: {fake.unexpected or [s[0] for s in fake.script]}")
        if not rec.get("ok"):
            out.append("teardown reported a problem")
        log = os.path.join(L.rec, "proxy.log")
        if not os.path.exists(log) or open(log).read() != "proxy line 1\nsquid started\n":
            out.append("the proxy log was not captured into the record folder")
        ids = [a[-1] for a, _ in fake.calls if a[:2] == ["docker", "rm"] or a[:3] == ["docker", "network", "rm"]]
        if ids != [ID["take"], ID["side"], ID["proxy"], ID["net"]]:
            out.append(f"removed {ids}")
        # take removal fails: finish is skipped, the rest still runs, TeardownError carries the record
        L, launched = self.launched()
        fake = FakeRuntime([(TEARDOWN_PREFIXES[0], rt.Completed(1, "", "busy")), (TEARDOWN_PREFIXES[2], ok("l\n"))]
                           + [(p, ok()) for p in TEARDOWN_PREFIXES[3:]])
        try:
            rt.teardown(fake, launched, sidecar=L.sidecar, record_dir=L.rec, caller_env=CALLER)
            out.append("a failed take removal did not raise")
        except rt.TeardownError as e:
            if "sidecar-finish" not in e.record["problems"] or "take-rm" not in e.record["problems"]:
                out.append("the failed teardown's record is off")
        if fake.unexpected or fake.script or any("finish" in a for a, _ in fake.calls):
            out.append("finish ran after a failed take removal, or a step was skipped")
        return out

    def test_order(self):
        def logs_after_removal(runtime, launched, *, sidecar, record_dir, caller_env=None):
            env = rt.runtime_env(caller_env)
            for argv in (TEARDOWN_PREFIXES[0], TEARDOWN_PREFIXES[1], TEARDOWN_PREFIXES[3], TEARDOWN_PREFIXES[4]):
                runtime.run(list(argv), env=env)
            rt._capture_proxy_log(runtime, launched.proxy_id, record_dir, env)
            runtime.run(list(TEARDOWN_PREFIXES[5]), env=env)
            return {"ok": True}

        def no_logs(runtime, launched, *, sidecar, record_dir, caller_env=None):
            env = rt.runtime_env(caller_env)
            for argv in TEARDOWN_PREFIXES[:2] + TEARDOWN_PREFIXES[3:]:
                runtime.run(list(argv), env=env)
            return {"ok": True}

        def finish_first(runtime, launched, *, sidecar, record_dir, caller_env=None):
            env = rt.runtime_env(caller_env)
            for argv in [TEARDOWN_PREFIXES[1], TEARDOWN_PREFIXES[0]] + TEARDOWN_PREFIXES[2:]:
                c = runtime.run(list(argv), env=env)
            return {"ok": True}

        self.assert_green_then_red(self.check_order, [
            ("logs-after-removal", patched(rt, "teardown", logs_after_removal)),
            ("no-logs", patched(rt, "teardown", no_logs)),
            ("finish-before-take-rm", patched(rt, "teardown", finish_first)),
        ])


# ----------------------------------------------------------------------------------------- leaked containers
class TestLeaked(MutantCase):
    def check(self):
        out = []
        listing = ok("\n".join([ID["other"], ID["take"]]) + "\n")
        fake = FakeRuntime([(["docker", "ps", "--all", "--no-trunc", "--quiet"], listing)])
        try:
            rt.refuse_restart_if_leaked(fake, [ID["take"], ID["side"]], caller_env=CALLER)
            out.append("a leaked container still present did not refuse the restart")
        except rt.LeakedContainer as e:
            if ID["take"] not in str(e) or ID["side"] in str(e):
                out.append("the refusal does not name exactly the leaked container")
        if any("--filter" in a or "-f" in a for a, _ in fake.calls):
            out.append("the listing filters")
        fake = FakeRuntime([(["docker", "ps", "--all", "--no-trunc", "--quiet"], ok(ID["other"] + "\n"))])
        try:
            rt.refuse_restart_if_leaked(fake, [ID["take"]], caller_env=CALLER)
        except rt.LeakedContainer:
            out.append("a gone container refused the restart")
        fake = FakeRuntime([(["docker", "ps"], rt.Completed(1, "", "daemon down"))])
        try:
            rt.refuse_restart_if_leaked(fake, [ID["take"]], caller_env=CALLER)
            out.append("a failed listing let the restart through")
        except rt.Refused:
            pass
        fake = FakeRuntime([(["docker", "ps"], ok("eager_turing\n"))])
        try:
            rt.leaked(fake, [ID["take"]], caller_env=CALLER)
            out.append("a listing of names was read")
        except rt.Refused:
            pass
        try:
            rt.leaked(FakeRuntime(), ["take-name"], caller_env=CALLER)
            out.append("a recorded name was accepted")
        except rt.Refused:
            pass
        return out

    def test_leaked(self):
        self.assert_green_then_red(self.check, [
            ("check-skipped", patched(rt, "refuse_restart_if_leaked", lambda *a, **k: None)),
            ("leaked-empty", patched(rt, "leaked", lambda *a, **k: [])),
        ])


# ---------------------------------------------------------------------------- the agent's leftover processes
UID_MAP = ((0, 1000, 1), (1, 100000, 65536))
TOP = {"ps_options": ["-eo", "pid,uid,comm"], "pid_column": "PID", "uid_column": "UID",
       "uid_namespace": "host"}


class TestProcesses(MutantCase):
    def check(self):
        out = []
        if rt.host_uid(10001, UID_MAP) != 110000 or rt.host_uid(0, UID_MAP) != 1000:
            out.append("host_uid maps wrongly")
        for bad_map in (((0, 1000, 1),), ((0, 1000, 1), (1, 100000, 65536), (10000, 5, 10))):
            try:
                rt.host_uid(10001, bad_map)
                out.append(f"uid map {bad_map} accepted")
            except rt.Refused:
                pass
        table = "PID UID COMMAND\n4100 103002 sleep\n4200 110000 node\n4300 110000 bash\n4400 10001 x\n"
        with mock.patch.object(rt, "TOP_FORMAT", TOP):
            fake = FakeRuntime([(["docker", "top", ID["take"], "-eo", "pid,uid,comm"], ok(table))])
            pids = rt.agent_processes(fake, ID["take"], agent_uid=10001, uid_map=UID_MAP, caller_env=CALLER)
            if pids != [4200, 4300]:
                out.append(f"agent processes {pids}")
            fake = FakeRuntime([(["docker", "top"], rt.Completed(1, "", "x"))])
            try:
                rt.agent_processes(fake, ID["take"], agent_uid=10001, uid_map=UID_MAP, caller_env=CALLER)
                out.append("a failed top read as no processes")
            except rt.Refused:
                pass
        try:
            rt.agent_processes(FakeRuntime(), ID["take"], agent_uid=10001, uid_map=UID_MAP)
            out.append("top read while its form is PENDING")
        except rt.NotReady:
            pass
        fake = FakeRuntime([(["docker", "exec"], ok())])
        rt.kill_agent(fake, ID["take"], agent_user=rt.AGENT_USER, caller_env=CALLER)
        if fake.calls[0][0] != ["docker", "exec", "--user", "10001:10001", ID["take"],
                                "/usr/bin/python3", "-I", "-S", "-c",
                                "import os,signal\ntry:\n os.kill(-1, signal.SIGKILL)\nexcept ProcessLookupError:\n pass"]:
            out.append(f"kill argv {fake.calls[0][0]}")
        for u in ("0:0", rt.KEEPALIVE_USER):
            try:
                rt.kill_agent(FakeRuntime(), ID["take"], agent_user=u)
                out.append(f"a kill as {u} was sent")
            except rt.Refused:
                pass
        # wait_gone: an injected clock and sleep; no real wait
        now = [0.0]
        slept = []
        clock = lambda: now[0]  # noqa: E731

        def sleep(s):
            slept.append(s)
            now[0] += s
        rows = [table, table, "PID UID COMMAND\n4100 103002 sleep\n"]
        with mock.patch.object(rt, "TOP_FORMAT", TOP):
            fake = FakeRuntime([(["docker", "top"], ok(r)) for r in rows])
            if rt.wait_gone(fake, ID["take"], agent_uid=10001, uid_map=UID_MAP, cap_s=30, interval_s=5, clock=clock,
                            sleep=sleep) != []:
                out.append("wait_gone did not see the processes leave")
            if slept != [5, 5]:
                out.append(f"wait_gone slept {slept}")
            now[0], slept[:] = 0.0, []
            fake = FakeRuntime([(["docker", "top"], ok(table)) for _ in range(7)])
            surv = rt.wait_gone(fake, ID["take"], agent_uid=10001, uid_map=UID_MAP, cap_s=30, interval_s=5,
                                clock=clock, sleep=sleep)
            if surv != [4200, 4300] or now[0] != 30:
                out.append(f"at the cap wait_gone returned {surv} at {now[0]}")
        return out

    def test_processes(self):
        self.assert_green_then_red(self.check, [
            ("unmapped-uid", patched(rt, "host_uid", lambda u, m: u)),
            ("kill-as-root", patched(rt, "AGENT_USER", "0:0")),
            ("no-wait", patched(rt, "wait_gone", lambda *a, **k: [])),
            ("top-pending-ignored", patched(rt, "_is_pending", lambda v: False)),
        ])


# --------------------------------------------------------------------------------- counters and the exit record
class TestCountersAndState(MutantCase):
    def cg(self, mem="low 0\nhigh 0\nmax 0\noom 1\noom_kill 2\n", pids="max 5\n"):
        d = tempfile.mkdtemp(prefix="w-")
        if mem is not None:
            open(os.path.join(d, "memory.events"), "w").write(mem)
        if pids is not None:
            open(os.path.join(d, "pids.events"), "w").write(pids)
        return d

    def check(self):
        out = []
        before = rt.counters(self.cg())
        after = rt.counters(self.cg(mem="oom_kill 3\nmax 9\n", pids="max 7\n"))
        if before != {"oom_kill": 2, "pids_max": 5}:
            out.append(f"counters read {before}")
        d = rt.counter_delta(before, after)
        if d != {"oom_kill_delta": 1, "pids_max_delta": 2} or tuple(d) != agent_adapter.COUNTER_FIELDS:
            out.append(f"delta {d}")
        for name, kw in (("no-memory", dict(mem=None)), ("no-line", dict(mem="oom 1\n")),
                         ("no-pids", dict(pids=None)), ("twice", dict(pids="max 1\nmax 2\n"))):
            try:
                rt.counters(self.cg(**kw))
                out.append(f"{name} read as a counter")
            except rt.Refused:
                pass
        try:
            rt.counter_delta(after, before)
            out.append("a counter that fell was accepted")
        except rt.Refused:
            pass
        state = [{"State": {"Running": False, "ExitCode": 137, "OOMKilled": True}}]
        with mock.patch.object(rt, "INSPECT_STATUS", "confirmed-in-test"):
            fake = FakeRuntime([(["docker", "container", "inspect", ID["take"]], ok(json.dumps(state)))])
            if rt.container_state(fake, ID["take"], caller_env=CALLER) != {"running": False, "exit_code": 137,
                                                                           "oom_killed": True}:
                out.append("the exit record is off")
            fake = FakeRuntime([(["docker", "container", "inspect"], ok(json.dumps([{"State": {}}])))])
            try:
                rt.container_state(fake, ID["take"], caller_env=CALLER)
                out.append("a State without its fields was read")
            except rt.Refused:
                pass
        try:
            rt.container_state(FakeRuntime(), ID["take"])
            out.append("the state was read while the spellings are PENDING")
        except rt.NotReady:
            pass
        return out

    def test_counters_and_state(self):
        self.assert_green_then_red(self.check, [
            ("swapped-lines", patched(rt, "COUNTER_SOURCES", {"oom_kill": ("memory.events", "oom"),
                                                               "pids_max": ("pids.events", "max")})),
            ("negative-delta", patched(rt, "counter_delta", lambda b, a: {
                f: a[f[:-6]] - b[f[:-6]] for f in agent_adapter.COUNTER_FIELDS})),
            ("state-running-from-status", patched(rt, "INSPECT_PATHS", dict(rt.INSPECT_PATHS,
                                                                              running="State.Status"))),
        ])


# --------------------------------------------------------------------------------------------------- one turn
class TestRunTurn(MutantCase):
    def check(self):
        out = []
        tmp = tempfile.mkdtemp(prefix="w-")
        login = plant_login(tmp, "CLAUDE_CODE_OAUTH_TOKEN")
        ticks = iter([100.0, 107.5, 200.0, 1100.0])
        clock = lambda: next(ticks)  # noqa: E731
        stream = os.path.join(tmp, "turn-1.jsonl")
        fake = FakeRuntime([(["docker", "exec", "--user", "10001:10001"], ok('{"type":"x"}\n', "warn\n"))])
        with filled():
            r = rt.run_turn(fake, ID["take"], ["agent-cli"], harness=rt.CLAUDE_CODE, run_tree="/srv/w/t1/tree",
                            login_file=login, stream_path=stream, budget_s=900, clock=clock, caller_env=CALLER)
        if (r["exit_code"], r["timed_out"], r["started_at"], r["ended_at"]) != (0, False, 100.0, 107.5):
            out.append(f"turn record {r}")
        if open(stream).read() != '{"type":"x"}\n':
            out.append("the stream was not written host-side")
        if FAKE_VALUE in json.dumps(r) or any(FAKE_VALUE in a for a, _ in fake.calls):
            out.append("the login value reached the record or argv")
        if fake.calls[0][1].get("CLAUDE_CODE_OAUTH_TOKEN") != FAKE_VALUE:
            out.append("the login did not ride in the client env")
        stream2 = os.path.join(tmp, "turn-2.jsonl")
        err = TimeoutError("slow")
        err.stdout = "partial\n"
        fake = FakeRuntime([(["docker", "exec"], err)])
        with filled():
            r = rt.run_turn(fake, ID["take"], ["agent-cli"], harness=rt.CLAUDE_CODE, run_tree="/srv/w/t1/tree",
                            login_file=login, stream_path=stream2, budget_s=900, clock=clock, caller_env=CALLER)
        if not r["timed_out"] or r["exit_code"] is not None or open(stream2).read() != "partial\n":
            out.append(f"a timeout was not recorded as a timed-out exec: {r}")
        for bad in (stream, "/srv/w/t1/tree/s.jsonl", "rel.jsonl"):
            try:
                with filled():
                    rt.run_turn(FakeRuntime(), ID["take"], ["x"], harness=rt.CLAUDE_CODE, run_tree="/srv/w/t1/tree",
                                login_file=login, stream_path=bad, budget_s=900, clock=clock, caller_env=CALLER)
                out.append(f"stream path {bad} accepted")
            except rt.Refused:
                pass
            if bad == stream and (not os.path.exists(stream) or open(stream).read() != '{"type":"x"}\n'):
                out.append("a refused repeated turn destroyed its original stream")
        return out

    def test_run_turn(self):
        def overwriting(runtime, take_id, inner, *, stream_path, **k):
            if os.path.exists(stream_path):
                os.remove(stream_path)
            return ORIG_RUN_TURN(runtime, take_id, inner, stream_path=stream_path, **k)

        self.assert_green_then_red(self.check, [
            ("timeout-raises", patched(rt, "run_turn", lambda *a, **k: (_ for _ in ()).throw(TimeoutError()))),
            ("overwrites-stream", patched(rt, "run_turn", overwriting)),
            ("stream-in-tree-allowed", patched(rt, "_inside", lambda c, p: False)),
        ])


ORIG_RUN_TURN = rt.run_turn


# ---------------------------------------------------------------------------------------- the config folder
class TestConfigDir(MutantCase):
    def check(self):
        out = []
        parent = tempfile.mkdtemp(prefix="w-")
        path = rt.make_config_dir(parent)
        if not os.path.isdir(path) or os.path.dirname(path) != parent:
            out.append("the config folder was not made under its parent")
        repo = tempfile.mkdtemp(prefix="w-")
        os.makedirs(os.path.join(repo, ".git"))
        try:
            rt.make_config_dir(repo)
            out.append("a config folder inside a repository was made")
        except rt.Refused:
            pass
        launched = rt.Launched(config_dir=path)
        try:
            rt.remove_config_dir(launched, published=False)
            out.append("the config folder was removed before publication")
        except rt.Refused:
            pass
        if not os.path.isdir(path):
            out.append("an unpublished take's config folder is gone")
        sibling = os.path.join(parent, "keep")
        os.makedirs(sibling)
        rt.remove_config_dir(launched, published=True)
        if os.path.exists(path) or not os.path.isdir(sibling):
            out.append("removal did not take exactly the recorded folder")
        try:
            rt.remove_config_dir(rt.Launched(config_dir=None), published=True)
            out.append("a removal with no recorded folder ran")
        except rt.Refused:
            pass
        return out

    def test_config_dir(self):
        self.assert_green_then_red(self.check, [
            ("no-publish-gate", patched(rt, "remove_config_dir", lambda l, *, published: ORIG_REMOVE(
                l, published=True))),
            ("no-repo-check", patched(rt, "outside_every_repository", lambda p: True)),
        ])


ORIG_REMOVE = rt.remove_config_dir


# ------------------------------------------------------------------------------- PENDING and neutral names
class TestPendingAndNames(MutantCase):
    EXPECT = {"FALLBACK_ENV", "VENDOR_BILLING_ROUTE_VARIABLES", "TOP_FORMAT", "INSPECT_STATUS", "TakeSpec.resources"}
    CALLER_EXPECT = {"cgroup_dir", "uid_map", "XDG_RUNTIME_DIR in the take", "tree ownership"}

    def check_pending(self):
        out = []
        if set(rt.pending()) != self.EXPECT:
            out.append(f"pending() = {sorted(rt.pending())}")
        if set(rt.CALLER_PENDING) != self.CALLER_EXPECT:
            out.append(f"CALLER_PENDING = {sorted(rt.CALLER_PENDING)}")
        if not all(rt.PENDING_WHY.get(k) for k in self.EXPECT):
            out.append("a pending value has no reason")
        return out

    def test_pending(self):
        self.assert_green_then_red(self.check_pending, [
            ("fallback-filled", patched(rt, "FALLBACK_ENV", {})),
            ("top-filled", patched(rt, "TOP_FORMAT", TOP)),
            ("inspect-filled", patched(rt, "INSPECT_STATUS", "ok")),
            ("billing-filled", patched(rt, "VENDOR_BILLING_ROUTE_VARIABLES", {"codex": (), "gemini": ()})),
        ])

    def check_no_override(self):
        import inspect
        names = {"fallback_env", "fallback", "billing_route", "vendor_billing_route_variables", "top_format",
                 "inspect_status", "inspect_paths"}
        found = []
        for name, fn in vars(rt).items():
            if callable(fn) and not name.startswith("_") and getattr(fn, "__module__", "") == rt.__name__:
                try:
                    params = inspect.signature(fn).parameters
                except (TypeError, ValueError):
                    continue
                found += [f"{name}({p})" for p in params if p.lower() in names]
        return found

    def test_no_parameter_overrides_a_pending_constant(self):
        def overriding(container_id, *, inspect_status=None):
            return None
        overriding.__module__ = rt.__name__
        self.assert_green_then_red(self.check_no_override, [
            ("override-parameter", lambda: mock.patch.object(rt, "state_with_override", overriding, create=True)),
        ])

    def visible(self):
        """Every string of this module the agent can read: users, mounts, env names and values, the keep-alive."""
        out = [rt.AGENT_USER, rt.KEEPALIVE_USER, rt.CONFIG_MOUNT, rt.PROXY_URL, rt.PROXY_ALIAS, rt.RUN_TREE_TMPDIR,
               *rt.KEEPALIVE_COMMAND, *rt.RUN_TREE_TMPDIR_VARIABLES, *rt.LOGIN_VARIABLE.values(), rt.network_name()]
        for env in rt.HARNESS_ENV.values():
            out += list(env) + list(env.values())
        return out

    def check_names(self):
        hits = []
        for s in self.visible():
            hits += [(s, w) for w in LEAK_WORDS if re.search(r"(?<![A-Za-z0-9])" + re.escape(w) + r"(?![A-Za-z0-9])",
                                                             s, re.IGNORECASE)]
        if not re.fullmatch(r"n[0-9a-f]{24}", rt.network_name()):
            hits.append(("network name", "shape"))
        return [f"{s!r} carries {w}" for s, w in hits]

    def test_neutral_names(self):
        self.assert_green_then_red(self.check_names, [
            ("study-mount", patched(rt, "CONFIG_MOUNT", "/opt/sidecar-cfg")),
            ("study-env", patched(rt, "HARNESS_ENV", dict(rt.HARNESS_ENV, codex=dict(rt.HARNESS_ENV["codex"],
                                                                                      X_SIDECAR="1")))),
            ("study-network", patched(rt, "network_name", lambda: "gap4-net")),
        ])


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
GUARDED_MODULES = ("os", "subprocess")
# W4B2-2, derived once from the three box modules' source and committed (TestAuditAllowlists binds both ways).
# Box lane 14 Oct: run_turn's launch journal is flushed to disk before the exec (os.fsync), 0b6f60f9.
OS_ATTRS = frozenset({"O_CREAT", "O_EXCL", "O_NOFOLLOW", "O_RDONLY", "O_WRONLY", "environ", "fdopen", "fsync",
                      "getuid", "listdir", "lstat", "makedirs", "mkdir", "open", "path", "sep", "walk"})
DUNDERS_ALLOWED = frozenset({"__file__", "__init__", "__name__"})
# How subprocess may appear, at DockerRuntime.run only: run as the func of a call, TimeoutExpired in an except.
SUBPROCESS_USES = frozenset({("run", "call"), ("TimeoutExpired", "except")})
# W4B3-3, derived once from the box modules and committed: every (module, name) a from-import brings in, every
# attribute used on each allowed module, and every getattr as (base, constant name).
# Lane w6a (CP2-preflight-2; glitch-1b's ruling w6a-1, ratified 11 Oct): preflight reads the take lock through w4a's
# image_lock (load and require_ready only); the two lists below name exactly that, and REACH_MODULES audits its reach.
# Box lane 14 Oct (glitch-06 ruling 1): preflight imports the sidecar's constants-only launch contract plainly and
# reads exactly the six names below; the sidecar program itself is never imported by an audited module.
IMPORT_FROM_ALLOWED = frozenset({("__future__", "annotations"), ("box", "image_lock"), ("box", "preflight"),
                                 ("box", "run_take"), ("box", "sidecar_contract"), ("dataclasses", "dataclass"), ("dataclasses", "field"),
                                 ("decimal", "Decimal"), ("decimal", "InvalidOperation"), ("typing", "Callable")})
MODULE_ATTRS = {
    "agent_adapter": frozenset({"COUNTER_FIELDS"}), "dataclasses": frozenset({"replace"}),
    "harness_bookkeeping": frozenset({"CLAUDE_CODE"}), "hashlib": frozenset({"sha256"}),
    "image_lock": frozenset({"load", "require_ready"}),
    "json": frozenset({"dump", "dumps", "loads"}),
    "preflight": frozenset({"expected_take_inspect", "inspect_mismatches"}),
    "re": frozenset({"IGNORECASE", "compile", "escape", "fullmatch", "search"}),
    "run_take": frozenset({"AGENT_USER", "CLAUDE_CODE", "CODEX", "CONFIG_MOUNT", "GEMINI", "HARNESS_ENV",
                           "INSPECT_PATHS", "INSPECT_STATUS", "KEEPALIVE_COMMAND", "KEEPALIVE_USER", "LOGIN_VARIABLE",
                           "NotReady", "PENDING", "PENDING_WHY", "PROXY_ALIAS", "PROXY_URL", "RUNTIME_CLIENT",
                           "Refused", "_abs_path", "_check_id", "_is_pending", "_known_harness", "_path_get",
                           "_write_json", "agent_exec_argv", "check_spec", "config_home_names",
                           "outside_every_repository", "refused_variables", "runtime_env"}),
    "secrets": frozenset({"token_hex"}), "shutil": frozenset({"rmtree"}),
    "sidecar_contract": frozenset({"BOOT_INSPECT_CAPABILITIES", "BOOT_USER", "INTERPRETER", "PROGRAM",
                                   "WATCHER_LAUNCHER", "WATCHER_USER"}),
    "stat": frozenset({"S_IMODE", "S_ISLNK", "S_ISREG"}), "sys": frozenset({"path"}),
}
GETATTR_ALLOWED = frozenset({("e", "filename"), ("e", "stdout")})
# W4B4-2: the dynamic-access builtins, each loaded only as the func of a direct call.
DYNAMIC_BUILTINS = frozenset({"getattr", "eval", "exec", "compile", "vars", "globals", "locals", "setattr",
                              "delattr", "__import__"})
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
    # W4B1-3: every load of the names os and subprocess must be the base of an attribute (never bound, passed or
    # subscripted), so the module object never reaches a name the audit cannot follow.
    attr_bases = {id(n.value) for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    parents = {id(c): n for n in ast.walk(tree) for c in ast.iter_child_nodes(n)}
    # W4B4-1, by construction: every name an import binds to a module is used only as an attribute base, only with
    # an entry in MODULE_ATTRS (os and subprocess have their own lists), and no plain import is renamed.
    import_bound = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                import_bound.add(a.asname or a.name.split(".")[0])
                if a.asname:
                    out.append(f"{rel}: import {a.name} as {a.asname}: no plain import is renamed")
        if isinstance(n, ast.ImportFrom) and n.module == "box":
            import_bound |= {a.asname or a.name for a in n.names}
    # W4B4-2, by construction: each dynamic-access builtin is loaded only as the func of a direct call.
    call_funcs = {id(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)}
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            if node.id in import_bound and id(node) not in attr_bases:
                out.append(f"{rel}: the module {node.id} is used as a value")
            if node.id in DYNAMIC_BUILTINS and id(node) not in call_funcs:
                out.append(f"{rel}: {node.id} is loaded other than as the func of a direct call")
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id in import_bound \
                and node.value.id not in MODULE_ATTRS and node.value.id not in GUARDED_MODULES:
            out.append(f"{rel}: {node.value.id}.{node.attr}: {node.value.id} has no entry in MODULE_ATTRS")
    for node in ast.walk(tree):
        # W4B3-3, default-deny by construction over from-imports, module attributes and getattr.
        if isinstance(node, ast.ImportFrom):
            for a in node.names:
                if (node.module, a.name) not in IMPORT_FROM_ALLOWED or a.asname:
                    out.append(f"{rel}: from {node.module} import {a.name} is not in IMPORT_FROM_ALLOWED")
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id in MODULE_ATTRS \
                and node.attr not in MODULE_ATTRS[node.value.id]:
            out.append(f"{rel}: {node.value.id}.{node.attr} is not in MODULE_ATTRS")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "getattr":
            base = node.args[0].id if node.args and isinstance(node.args[0], ast.Name) else None
            const = node.args[1].value if len(node.args) > 1 and isinstance(node.args[1], ast.Constant) else None
            if (base, const) not in GETATTR_ALLOWED:
                out.append(f"{rel}: getattr({base}, {const!r}) is not in GETATTR_ALLOWED")
        # W4B2-2, default-deny: os only through its committed attribute list; no dunder outside its committed list.
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "os" \
                and node.attr not in OS_ATTRS:
            out.append(f"{rel}: os.{node.attr} is not in OS_ATTRS")
        dname = node.attr if isinstance(node, ast.Attribute) else node.id if isinstance(node, ast.Name) else ""
        if dname.startswith("__") and dname.endswith("__") and dname not in DUNDERS_ALLOWED:
            out.append(f"{rel}: {dname} is not in DUNDERS_ALLOWED")
        # The one subprocess site: each use is a (name, how) of SUBPROCESS_USES.
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "subprocess":
            parent = parents.get(id(node))
            how = "call" if isinstance(parent, ast.Call) and parent.func is node else \
                "except" if isinstance(parent, ast.ExceptHandler) and parent.type is node else "value"
            if (node.attr, how) not in SUBPROCESS_USES:
                out.append(f"{rel}: subprocess.{node.attr} used as a {how}, not one of SUBPROCESS_USES")
        if isinstance(node, ast.Name) and node.id in GUARDED_MODULES and isinstance(node.ctx, ast.Load) \
                and id(node) not in attr_bases:
            out.append(f"{rel}: the module {node.id} is used as a value")
        if isinstance(node, ast.Attribute) and node.attr in GUARDED_MODULES + ("pty", "asyncio") \
                and not (isinstance(node.value, ast.Name) and node.value.id in ("os",) and node.attr == "path"):
            out.append(f"{rel}: .{node.attr} reached through another module")
        if isinstance(node, ast.Attribute) and node.attr in ("__dict__", "modules", "__builtins__"):
            out.append(f"{rel}: .{node.attr} reaches names dynamically")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in (
                "vars", "globals", "locals", "setattr", "delattr"):
            out.append(f"{rel}: {node.func.id}(...) reaches names dynamically")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "getattr" \
                and not (len(node.args) > 1 and isinstance(node.args[1], ast.Constant)):
            out.append(f"{rel}: getattr with a non-constant name")
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
    "alias-load": ("box/preflight.py", "import os\nx = os\nx.kill(1, 9)\n"),
    "getattr-name": ("box/preflight.py", "import os\nn = 'ki' + 'll'\ngetattr(os, n)(1, 9)\n"),
    "vars-os": ("box/preflight.py", "import os\nvars(os)['system']('x')\n"),
    "dunder-dict": ("box/preflight.py", "import os\nos.__dict__['system']('x')\n"),
    "module-subprocess": ("box/preflight.py", "from box import run_take\nrun_take.subprocess.Popen(['x'])\n"),
    "module-os": ("box/preflight.py", "from box import run_take\nrun_take.os.system('x')\n"),
    "globals": ("box/preflight.py", "g = globals()\n"),
    "sys-modules": ("box/preflight.py", "import sys\nsys.modules['os'].system('x')\n"),
    "os-as-argument": ("box/take_config.py", "import os\ndef f(m):\n    return m\nf(os).system('x')\n"),
}


LANE_TESTS = ("tests/test_run_take.py", "tests/test_preflight.py", "tests/test_take_config.py")
PROCESS_CALLS = frozenset({"run", "Popen", "call", "check_call", "check_output", "getoutput", "getstatusoutput"})


def audit_test_source(rel: str, source: str) -> list:
    """Interface 16: in this lane's test files, a direct subprocess call appears only inside `_round3_leak_words`,
    and that helper runs `git show` with a list argv."""
    tree = ast.parse(source)
    out = []
    helpers = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_round3_leak_words"]
    if len(helpers) != 1:
        out.append(f"{rel}: not exactly one _round3_leak_words helper")
    inside = {id(n) for h in helpers for n in ast.walk(h)}
    # The planted calls that prove the guard is armed (each must raise the guard's tripwire).
    armed = {id(n) for f in ast.walk(tree) if isinstance(f, ast.FunctionDef) and f.name == "test_guard_is_armed"
             for n in ast.walk(f)}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and isinstance(node.func.value, ast.Name) and node.func.value.id == "subprocess" \
                and node.func.attr in PROCESS_CALLS:
            if id(node) in armed:
                continue
            if id(node) not in inside:
                out.append(f"{rel}: subprocess.{node.func.attr} outside _round3_leak_words")
            elif not (node.args and isinstance(node.args[0], ast.List)
                      and [getattr(e, "value", None) for e in node.args[0].elts[:1]] == ["git"]
                      and any(isinstance(e, ast.Constant) and e.value == "show" for e in node.args[0].elts)):
                out.append(f"{rel}: the leak-word read is not git show with a list argv")
    return out


TEST_PLANTED = {
    "call-outside-helper": "def _round3_leak_words():\n    subprocess.run(['git', 'show', 'x'])\n"
                           "def f():\n    subprocess.Popen(['x'])\n",
    "no-helper": "x = 1\n",
    "shell-string": "def _round3_leak_words():\n    subprocess.run('git show x', shell=True)\n",
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
    for name, src in TEST_PLANTED.items():
        if not audit_test_source("planted", src):
            out.append(f"planted test {name} was not caught")
    for rel in LANE_TESTS:
        with open(os.path.join(HERE, rel), encoding="utf-8") as fh:
            out += audit_test_source(rel, fh.read())
    return out


class TestAuditAllowlists(MutantCase):
    """W4B2-2, by construction: each allowlist is exactly what the box modules use (derived once from their source
    and committed), so widening a list leaves an unused entry and emptying it flags the real modules. The lane lead
    ruled no new evasion forms; the residual is named in words in the lane report."""

    def used(self):
        os_attrs, dunders = set(), set()
        for rel in BOX_MODULES:
            tree = ast.parse(open(os.path.join(HERE, rel), encoding="utf-8").read())
            for n in ast.walk(tree):
                if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == "os":
                    os_attrs.add(n.attr)
                name = n.attr if isinstance(n, ast.Attribute) else n.id if isinstance(n, ast.Name) else ""
                if name.startswith("__") and name.endswith("__"):
                    dunders.add(name)
        return os_attrs, dunders

    def used3(self):
        imp, attrs, ga = set(), {}, set()
        for rel in BOX_MODULES:
            tree = ast.parse(open(os.path.join(HERE, rel), encoding="utf-8").read())
            for n in ast.walk(tree):
                if isinstance(n, ast.ImportFrom):
                    imp |= {(n.module, a.name) for a in n.names}
                if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id in MODULE_ATTRS:
                    attrs.setdefault(n.value.id, set()).add(n.attr)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "getattr" \
                        and len(n.args) > 1 and isinstance(n.args[0], ast.Name) and isinstance(n.args[1], ast.Constant):
                    ga.add((n.args[0].id, n.args[1].value))
        return imp, attrs, ga

    def check(self):
        out = list(process_audit())
        imp, attrs, ga = self.used3()
        out += [f"IMPORT_FROM_ALLOWED holds unused {x}" for x in sorted(set(IMPORT_FROM_ALLOWED) - imp)]
        out += [f"MODULE_ATTRS holds unused {m}.{a}" for m, v in MODULE_ATTRS.items() for a in sorted(v)
                if a not in attrs.get(m, set())]
        out += [f"GETATTR_ALLOWED holds unused {x}" for x in sorted(set(GETATTR_ALLOWED) - ga)]
        os_attrs, dunders = self.used()
        out += [f"OS_ATTRS holds unused {a}" for a in sorted(set(OS_ATTRS) - os_attrs)]
        out += [f"DUNDERS_ALLOWED holds unused {d}" for d in sorted(set(DUNDERS_ALLOWED) - dunders)]
        if set(SUBPROCESS_USES) != {("run", "call"), ("TimeoutExpired", "except")}:
            out.append(f"SUBPROCESS_USES is {sorted(SUBPROCESS_USES)}")
        return out

    def test_allowlists(self):
        me = sys.modules[__name__]
        self.assert_green_then_red(self.check, [
            ("os-widened", patched(me, "OS_ATTRS", OS_ATTRS | {"system"})),
            ("os-emptied", patched(me, "OS_ATTRS", frozenset())),
            ("dunders-widened", patched(me, "DUNDERS_ALLOWED", DUNDERS_ALLOWED | {"__subclasses__"})),
            ("dunders-emptied", patched(me, "DUNDERS_ALLOWED", frozenset())),
            ("subprocess-uses-widened", patched(me, "SUBPROCESS_USES", SUBPROCESS_USES | {("run", "value")})),
            ("subprocess-uses-emptied", patched(me, "SUBPROCESS_USES", frozenset())),
            ("import-from-widened", patched(me, "IMPORT_FROM_ALLOWED", IMPORT_FROM_ALLOWED | {("os", "system")})),
            ("import-from-emptied", patched(me, "IMPORT_FROM_ALLOWED", frozenset())),
            ("module-attrs-widened", patched(me, "MODULE_ATTRS", dict(MODULE_ATTRS, json=MODULE_ATTRS["json"]
                                                                       | {"JSONDecoder"}))),
            ("module-attrs-emptied", patched(me, "MODULE_ATTRS", {k: frozenset() for k in MODULE_ATTRS})),
            ("getattr-widened", patched(me, "GETATTR_ALLOWED", GETATTR_ALLOWED | {("e", "args")})),
            ("getattr-emptied", patched(me, "GETATTR_ALLOWED", frozenset())),
        ])

    def test_subprocess_rule_fires_on_the_real_call(self):
        """W4B3-2: with ("run", "call") removed from SUBPROCESS_USES, the rule itself flags the one real call."""
        me = sys.modules[__name__]
        self.assertEqual(process_audit(), [])
        with mock.patch.object(me, "SUBPROCESS_USES", SUBPROCESS_USES - {("run", "call")}):
            got = process_audit()
        print(f"  mutant run-call-removed: {'red' if got else 'GREEN (survived)'}")
        self.assertTrue([p for p in got if p.startswith("box/run_take.py: subprocess.run used as a call")], got)

    def plainly_bound(self):
        """W4B4-1: every module name the box modules' imports bind (plain imports, and the box package's modules),
        less os and subprocess, derived from the source."""
        names = set()
        for rel in BOX_MODULES:
            for n in ast.walk(ast.parse(open(os.path.join(HERE, rel), encoding="utf-8").read())):
                if isinstance(n, ast.Import):
                    names |= {a.name.split(".")[0] for a in n.names}
                if isinstance(n, ast.ImportFrom) and n.module == "box":
                    names |= {a.name for a in n.names}
        return names - set(GUARDED_MODULES)

    def check_module_keys(self):
        out = []
        if set(MODULE_ATTRS) != self.plainly_bound():
            out.append(f"MODULE_ATTRS keys differ from the import-bound names: "
                       f"{sorted(set(MODULE_ATTRS) ^ self.plainly_bound())}")
        if process_audit():
            out.append("the real modules are not clean")
        return out

    def test_module_keys_bound_to_imports(self):
        """W4B4-1: the keys are exactly the import-bound names, and an import-bound name with no entry is refused."""
        me = sys.modules[__name__]
        dropped = {k: v for k, v in MODULE_ATTRS.items() if k != "shutil"}
        self.assert_green_then_red(self.check_module_keys, [
            ("module-attrs-key-dropped", patched(me, "MODULE_ATTRS", dropped)),
        ])
        with mock.patch.object(me, "MODULE_ATTRS", dropped):
            got = process_audit()
        self.assertTrue([p for p in got if p.startswith("box/run_take.py: shutil.rmtree")], got)

    def check_dynamic_builtins(self):
        out = []
        if set(DYNAMIC_BUILTINS) != {"getattr", "eval", "exec", "compile", "vars", "globals", "locals", "setattr",
                                     "delattr", "__import__"}:
            out.append(f"DYNAMIC_BUILTINS is {sorted(DYNAMIC_BUILTINS)}")
        if process_audit():
            out.append("the real modules' own direct calls do not pass")
        return out

    def test_dynamic_builtins(self):
        """W4B4-2: each of these names is loaded only as the func of a direct call. No alias form is written (the
        standing rule); the list is bound by its literal, and the real modules' direct calls still pass."""
        me = sys.modules[__name__]
        self.assert_green_then_red(self.check_dynamic_builtins, [
            ("dynamic-builtins-dropped-getattr", patched(me, "DYNAMIC_BUILTINS", DYNAMIC_BUILTINS - {"getattr"})),
            ("dynamic-builtins-emptied", patched(me, "DYNAMIC_BUILTINS", frozenset())),
        ])


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
            ("test-call-allowed", patched(sys.modules[__name__], "audit_test_source", lambda rel, src: [])),
        ])


_AUDIT_READ = None


# ------------------------------------------------- lane w6a (W6A-R1-2, ruling w6a-1): what preflight now reaches
# preflight imports box.image_lock, which imports box.egress.proxy_conf: neither may reach a process. Each module's
# imports must be within REACH_IMPORTS, and neither names subprocess or a FORBIDDEN_OS attribute.
REACH_MODULES = ("box/image_lock.py", "box/egress/proxy_conf.py")
REACH_IMPORTS = frozenset({"__future__", "fnmatch", "json", "os", "re", "dataclasses", "harness_bookkeeping",
                           "box.egress"})


def reach_source(rel: str, source: str) -> list:
    out = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            out += [f"{rel}: import {a.name} is outside REACH_IMPORTS" for a in node.names
                    if a.name not in REACH_IMPORTS]
        elif isinstance(node, ast.ImportFrom):
            mod = ("." * node.level) + (node.module or "")
            if mod not in REACH_IMPORTS:
                out.append(f"{rel}: from {mod} import is outside REACH_IMPORTS")
            if mod == "os":
                out += [f"{rel}: from os import {a.name}" for a in node.names if FORBIDDEN_OS.fullmatch(a.name)]
        elif isinstance(node, ast.Name) and node.id == "subprocess":
            out.append(f"{rel}: names subprocess")
        elif isinstance(node, ast.Attribute):
            if node.attr == "subprocess":
                out.append(f"{rel}: .subprocess reached")
            if isinstance(node.value, ast.Name) and node.value.id == "os" and FORBIDDEN_OS.fullmatch(node.attr):
                out.append(f"{rel}: os.{node.attr}")
    return out


REACH_PLANTED = {
    "imports-subprocess": "import subprocess\n",
    "os-system": "import os\nos.system('x')\n",
    "from-os-fork": "from os import fork\n",
    "imports-socket": "import socket\n",
}


def reach_audit(read=None) -> list:
    """Planted positives first (each must be caught), then the two real modules (each must be clean)."""
    out = [f"planted reach {n} was not caught" for n, src in REACH_PLANTED.items() if not reach_source("planted", src)]
    used = set()
    for rel in REACH_MODULES:
        src = read(rel) if read else open(os.path.join(HERE, rel), encoding="utf-8").read()
        out += reach_source(rel, src)
        for n in ast.walk(ast.parse(src)):
            if isinstance(n, ast.Import):
                used |= {a.name for a in n.names}
            elif isinstance(n, ast.ImportFrom):
                used.add(("." * n.level) + (n.module or ""))
    # Bound both ways, as W4B2-2's lists: a widened entry nothing imports is a problem too.
    out += [f"REACH_IMPORTS holds unused {m}" for m in sorted(set(REACH_IMPORTS) - used)]
    return out


class TestReachAudit(MutantCase):
    def test_reach(self):
        real = {rel: open(os.path.join(HERE, rel), encoding="utf-8").read() for rel in REACH_MODULES}
        me = sys.modules[__name__]

        def added(rel, extra):
            return lambda: mock.patch.object(me, "reach_audit", lambda read=None, _f=reach_audit: _f(
                lambda r: real[r] + (extra if r == rel else "")))
        self.assert_green_then_red(lambda: me.reach_audit(), [
            ("image-lock-imports-subprocess", added("box/image_lock.py", "\nimport subprocess\n")),
            ("proxy-conf-kills", added("box/egress/proxy_conf.py", "\nos.kill(1, 9)\n")),
            ("reach-widened", patched(me, "REACH_IMPORTS", REACH_IMPORTS | {"subprocess"})),
            ("reach-narrowed", patched(me, "REACH_IMPORTS", REACH_IMPORTS - {"fnmatch"})),
            ("planted-dropped", lambda: mock.patch.dict(REACH_PLANTED, {"imports-subprocess": "x = 1\n"})),
        ])


# Taken last, after every import-time statement of this module: must be empty (setUpModule arms the guard).
_PATCHED_AT_IMPORT = _patched_now()


if __name__ == "__main__":
    if sys.argv[1:] == ["--process-audit"]:
        problems = process_audit() + reach_audit()
        for p in problems:
            print(f"process audit: {p}")
        print(f"process audit: {len(PLANTED) + len(TEST_PLANTED)} planted positives caught, "
              f"{len(BOX_MODULES)} modules and {len(LANE_TESTS)} test files read, "
              f"{len(REACH_PLANTED)} reach positives caught and {len(REACH_MODULES)} reached modules read, "
              f"{len(problems)} problem(s)")
        sys.exit(1 if problems else 0)
    unittest.main(verbosity=2)
