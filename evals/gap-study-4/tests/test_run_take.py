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
import dataclasses
import json
import hashlib
import os
import re
import stat
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
# Codex has no environment login (glitch-06's ruling 1, 14 Oct 2026): its LOGIN_VARIABLE is the reserved "-" (NO_LOGIN).
LOGINS = dict(zip(ARMS, ("CLAUDE_CODE_OAUTH_TOKEN", "-", "GEMINI_API_KEY")))


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


@contextlib.contextmanager
def _patches(*triples):
    with contextlib.ExitStack() as stack:
        for obj, attr, value in triples:
            stack.enter_context(mock.patch.object(obj, attr, value))
        yield


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
        if rt.LOGIN_VARIABLE != {rt.CLAUDE_CODE: "CLAUDE_CODE_OAUTH_TOKEN", rt.CODEX: "-",
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
                                 "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1", "CLAUDE_CODE_THRIFTY_SONIC": "false",
                                 "CLAUDE_CODE_SILENT_TURN_REMINDER": "0",   # glitch-b5's parity switch (16 Oct 2026)
                                 "CLAUDE_CONFIG_DIR": "/opt/cfg"},
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
    "--read-only", "--tmpfs", "/tmp:rw,exec,nosuid,nodev,mode=1777", "--tmpfs", "/var/tmp:rw,exec,nosuid,nodev,mode=1777",
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
        if "--read-only" not in argv:            # the read-only root (glitch-b5's ruling on review r15, 16 Oct 2026)
            out.append("the root filesystem is not read-only")
        tmpfs = {argv[i + 1] for i, x in enumerate(argv) if x == "--tmpfs"}
        if tmpfs != {f"{k}:{v}" for k, v in rt.TAKE_TMPFS.items()} or set(rt.TAKE_TMPFS) != {"/tmp", "/var/tmp"}:
            out.append(f"the tmpfs mounts are {sorted(tmpfs)}")
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

        def writable_root(s):                   # the read-only root (glitch-b5's ruling on review r15, 16 Oct 2026)
            return [a for a in orig(s) if a != "--read-only"]

        def extra_tmpfs(s):
            a = orig(s)
            i = a.index("--read-only") + 1
            return a[:i] + ["--tmpfs", "/run/lock:rw"] + a[i:]

        def noexec_tmp(s):
            return [("/tmp:rw,noexec" if a.startswith("/tmp:") else a) for a in orig(s)]

        self.assert_green_then_red(self.check_shape, [
            ("env-at-create", patched(rt, "create_argv", with_env)),
            ("alias-on-take", patched(rt, "create_argv", with_alias)),
            ("pull-allowed", patched(rt, "create_argv", no_pull)),
            ("third-mount", patched(rt, "create_argv", third_mount)),
            ("agent-as-pid1", patched(rt, "create_argv", agent_pid1)),
            ("writable-root", patched(rt, "create_argv", writable_root)),
            ("extra-tmpfs", patched(rt, "create_argv", extra_tmpfs)),
            ("noexec-tmp", patched(rt, "create_argv", noexec_tmp)),
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


# The documented bypass acceptance key: RULED not sent (not required in -p; glitch-06, 14 Oct 2026). Tests use it
# only to show the study refuses it.
BYPASS = "skipDangerousModePermissionPrompt"


@contextlib.contextmanager
def filled():
    """Every PENDING value exec needs, filled in memory only (interface 15). FALLBACK_ENV is FILLED (14 Oct 2026) and
    the bypass acceptance RULED not required in -p (14 Oct 2026); both are the committed values here."""
    with mock.patch.object(rt, "VENDOR_BILLING_ROUTE_VARIABLES", {rt.CODEX: (), rt.GEMINI: ()}):
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
            others = [rt.LOGIN_VARIABLE[h] for h in ARMS if h != arm and rt.LOGIN_VARIABLE[h] != rt.NO_LOGIN]
            others += ["CODEX_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY", "ANTHROPIC_API_KEY",
                       "CLAUDE_CODE_OAUTH_REFRESH_TOKEN", "CLAUDE_CODE_USE_VERTEX"]
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
                  | {"CODEX_API_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY"}
                  | set(CODEX_ROUTE_NAMED) | set(CODEX_ROUTE_DOCS_READ)    # glitch-06's rulings: every arm
                  | set(sweep_refused()) | set(_gemini_refused())
                  | set(_claude_refused()))     # glitch-6b's ruling 4(i), 15 Oct 2026: the Claude binary sweep
        for arm in ARMS:
            got = rt.refused_variables(arm)
            expected = closed - {LOGINS[arm]}
            if arm == rt.GEMINI:
                expected |= {"GEMINI_CLI_EXP_AGENT"}
            if got != expected:
                out.append(f"{arm}: refused set {sorted(got ^ expected)} off")
        if "CLAUDE_CODE_OAUTH_TOKEN" not in rt.refused_variables(rt.CODEX):
            out.append("arm O admits Anthropic's token")
        if not {"CODEX_API_KEY", "OPENAI_API_KEY"} <= rt.refused_variables(rt.CODEX):
            out.append("arm O admits an API key (subscriptions only)")
        return out

    def test_refused_sets(self):
        self.assert_green_then_red(self.check_refused_sets, [
            ("own-login-refused", patched(rt, "LOGIN_VARIABLE", dict(rt.LOGIN_VARIABLE,
                                                                     **{rt.CLAUDE_CODE: "NOT_A_VAR"}))),
            ("codex-key-admitted", patched(rt, "LOGIN_VARIABLE", dict(rt.LOGIN_VARIABLE, codex="CODEX_API_KEY"))),
            # OPENAI_API_KEY and GOOGLE_API_KEY are also in the Codex and Gemini sweep lists since 14 Oct 2026, so the
            # short vendor list is held with those two names taken out of the sweep lists too (nothing else moves)
            ("vendor-list-short", lambda: _patches(
                (rt, "VENDOR_KEY_VARIABLES", ("CODEX_API_KEY", "GEMINI_API_KEY")),
                (rt, "VENDOR_BILLING_ROUTE_VARIABLES",
                 {h: tuple(n for n in v if n not in ("OPENAI_API_KEY", "GOOGLE_API_KEY"))
                  for h, v in rt.VENDOR_BILLING_ROUTE_VARIABLES.items()}))),
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
            argv, env = rt.exec_argv(ID["take"], CLAUDE_INNER, user=rt.AGENT_USER,
                                     workdir="/srv/w/t1/tree", harness=rt.CLAUDE_CODE, run_tree="/srv/w/t1/tree",
                                     login_file=self.login, caller_env=CALLER)
        t = "/srv/w/t1/tree/.tmp"
        # Departure w12a-2 (ruling docs-1): the values ride as the launcher's NAME=VALUE pairs, the agent starting
        # from an empty environment plus its TAKE_ENV row; the login still rides as `-e NAME` only.
        want = ["docker", "exec", "--user", "10001:10001", "--workdir", "/srv/w/t1/tree",
                "-e", "CLAUDE_CODE_OAUTH_TOKEN", ID["take"], *rt.LAUNCHER, "CLAUDE_CODE_OAUTH_TOKEN", "15",
                "CLAUDE_CODE_DISABLE_AUTO_MEMORY=1", "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1",
                "CLAUDE_CODE_DISABLE_REFUSAL_FALLBACK=1", "CLAUDE_CODE_SILENT_TURN_REMINDER=0",
                "CLAUDE_CODE_THRIFTY_SONIC=false",
                "CLAUDE_CONFIG_DIR=/opt/cfg", "DISABLE_AUTOUPDATER=1", "ENABLE_CLAUDEAI_MCP_SERVERS=false",
                "HOME=/opt/cfg", "HTTPS_PROXY=http://proxy:3128", "LANG=C.UTF-8",
                f"PATH={rt.TAKE_PATH}", f"TEMP={t}", f"TMP={t}", f"TMPDIR={t}", *CLAUDE_INNER]
        if argv != want:
            out.append(f"exec argv differs: {argv}")
        if any(FAKE_VALUE in a for a in argv):
            out.append("the login value is in argv")
        if env.get("CLAUDE_CODE_OAUTH_TOKEN") != FAKE_VALUE:
            out.append("the login value is not in the client env")
        extra = set(env) - set(rt.RUNTIME_ENV_NAMES) - set(rt.HARNESS_ENV[rt.CLAUDE_CODE]) - {
            "TMPDIR", "TMP", "TEMP", "CLAUDE_CODE_DISABLE_REFUSAL_FALLBACK", "CLAUDE_CODE_OAUTH_TOKEN"}
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
            with mock.patch.object(rt, "FALLBACK_ENV", rt.PENDING):   # FILLED 14 Oct 2026; the clause stays tested
                rt.exec_argv(ID["take"], CLAUDE_INNER, user=rt.AGENT_USER, workdir="/", harness=rt.CLAUDE_CODE,
                             run_tree="/srv/w/t1/tree", login_file=self.login, caller_env=CALLER)
            out.append("an exec was built while FALLBACK_ENV is PENDING")
        except rt.NotReady:
            pass
        # glitch-06's ruling from the docs (14 Oct 2026): exactly the documented refusal-fallback switch, set to 1.
        if rt.FALLBACK_ENV != {"CLAUDE_CODE_DISABLE_REFUSAL_FALLBACK": "1"}:
            out.append(f"FALLBACK_ENV is not the ruled value: {rt.FALLBACK_ENV!r}")
        # No availability-fallback chain: --fallback-model in any spelling is refused before any login read.
        # Each is otherwise a well-formed turn (its model and the study's settings), so only the flag can refuse it.
        for inner in (CLAUDE_INNER + ["--fallback-model", "claude-sonnet-5-5"],
                      CLAUDE_INNER[:1] + ["--fallback-model=claude-sonnet-5-5"] + CLAUDE_INNER[1:]):
            try:
                with filled(), mock.patch.object(rt, "read_login", side_effect=AssertionError("login read")):
                    rt.exec_argv(ID["take"], inner, user=rt.AGENT_USER, workdir="/", harness=rt.CLAUDE_CODE,
                                 run_tree="/srv/w/t1/tree", login_file=self.login, caller_env=CALLER)
                out.append(f"an exec with a fallback model was built: {inner}")
            except rt.Refused:
                pass
            except AssertionError:
                out.append("the login was read before the fallback-model refusal")
        for h in ("codex", "gemini"):
            inner = ["gemini", "-m", "gemini-3.8-flash"] if h == rt.GEMINI else ["x"]
            lf = plant_login(self.tmp, rt.LOGIN_VARIABLE[h])
            try:
                # Gemini's list was FILLED 14 Oct 2026 (its package sweep); the PENDING clause stays red-tested with
                # the entry put back. Codex is refused by its subscription gate whatever its list holds.
                with mock.patch.dict(rt.VENDOR_BILLING_ROUTE_VARIABLES, {rt.GEMINI: rt.PENDING}), \
                        mock.patch.object(rt, "CODEX_SUBSCRIPTION_READY", False):   # Codex's gate pinned closed (B8-1)
                    rt.exec_argv(ID["take"], inner, user=rt.AGENT_USER, workdir="/", harness=h,
                                 run_tree="/srv/w/t1/tree", login_file=lf, caller_env=CALLER)
                out.append(f"a {h} exec was built while its billing-route list is PENDING")
            except rt.NotReady:
                pass
            if h == rt.CODEX:
                try:
                    with filled(), mock.patch.object(rt, "CODEX_SUBSCRIPTION_READY", False):   # pinned closed (B8-1)
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
            ("fallback-env-dropped", patched(rt, "FALLBACK_ENV", {})),
            ("fallback-env-zero", patched(rt, "FALLBACK_ENV", {"CLAUDE_CODE_DISABLE_REFUSAL_FALLBACK": "0"})),
            ("fallback-flag-admitted", patched(rt, "FALLBACK_MODEL_FLAG", "--no-such-flag")),
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


ORIG_EXEC_ARGV = rt.exec_argv


class TestWalkLoginPlace(MutantCase):
    """The walk-token road (box lane, 14 Oct 2026): the account's token file sits alone in a mode-700 folder owned by
    the reading user, never a link, with one link, outside the run tree; exec_argv checks the place before read_login,
    and read_login refuses an empty, multi-line, wrong-mode or linked file. No refusal carries the value."""

    def place(self, folder_mode=0o700, text=None):
        d = tempfile.mkdtemp(prefix="w-")
        sub = os.path.join(d, "claude1")
        os.mkdir(sub)
        os.chmod(sub, folder_mode)
        path = os.path.join(sub, "claude-walk-token")
        with open(path, "w") as fh:
            fh.write(f"CLAUDE_CODE_OAUTH_TOKEN={FAKE_VALUE}\n" if text is None else text)
        os.chmod(path, 0o600)
        return d, sub, path

    def exec_with(self, path, inner=None, run_tree="/srv/w/t1/tree"):
        return rt.exec_argv(ID["take"], inner or CLAUDE_INNER, user=rt.AGENT_USER, workdir="/",
                            harness=rt.CLAUDE_CODE, run_tree=run_tree, login_file=path, caller_env=CALLER)

    def refused(self, out, label, fn, *a, **k):
        try:
            fn(*a, **k)
            out.append(f"{label}: admitted")
        except rt.Refused as e:
            if FAKE_VALUE in str(e):
                out.append(f"{label}: the refusal carries the value")
        except AssertionError:
            out.append(f"{label}: the login was read before the refusal")

    def check(self):
        out = []
        w = rt.WALK_LOGIN_FILES
        if w != {"claude1": "/home/javier/gap4-secrets/claude1/claude-walk-token",
                 "r4-g": "/home/javier/gap4-secrets/r4-g/gemini-walk-login"}:      # the Gemini key road, 14 Oct
            out.append(f"WALK_LOGIN_FILES = {w}")
        _d, _sub, good = self.place()
        try:
            rt.check_login_place(good, "/srv/w/t1/tree")
            argv, env = self.exec_with(good)
            if env.get("CLAUDE_CODE_OAUTH_TOKEN") != FAKE_VALUE or FAKE_VALUE in " ".join(argv):
                out.append("the good place did not hand the token to the client environment alone")
        except rt.Refused as e:
            out.append(f"the good place was refused: {e}")
        # the place, refused before any read
        with mock.patch.object(rt, "read_login", side_effect=AssertionError("login read")):
            _d, sub, p = self.place(folder_mode=0o755)
            self.refused(out, "a 755 folder", self.exec_with, p)
            _d, sub, p = self.place(folder_mode=0o750)
            self.refused(out, "a 750 folder", self.exec_with, p)
            d, sub, p = self.place()
            os.link(p, os.path.join(d, "second-link"))
            self.refused(out, "a second hard link", self.exec_with, p)
            d, sub, p = self.place()
            linked = os.path.join(d, "via-link")
            os.symlink(sub, linked)
            if hasattr(os, "lchmod"):           # macOS: a 700 link, so only the link rule can refuse it
                os.lchmod(linked, 0o700)
            self.refused(out, "a folder reached through a link", self.exec_with, os.path.join(linked, "claude-walk-token"))
            d, sub, p = self.place()
            self.refused(out, "inside the run tree", self.exec_with, p, run_tree=d)
            self.refused(out, "a relative path", rt.check_login_place, "claude1/claude-walk-token", "/srv/w/t1/tree")
            self.refused(out, "--bare", self.exec_with, good, inner=CLAUDE_INNER + ["--bare"])
        # read_login's own rules, on the walk file's shape
        for label, text in (("an empty file", ""), ("two lines", f"CLAUDE_CODE_OAUTH_TOKEN={FAKE_VALUE}\nX=1\n"),
                            ("no newline", f"CLAUDE_CODE_OAUTH_TOKEN={FAKE_VALUE}"),
                            ("the bare token", f"{FAKE_VALUE}\n"), ("the prefix alone", "CLAUDE_CODE_OAUTH_TOKEN=\n")):
            _d, _sub, p = self.place(text=text)
            self.refused(out, label, rt.read_login, p, "CLAUDE_CODE_OAUTH_TOKEN")
        _d, _sub, p = self.place()
        os.chmod(p, 0o640)
        self.refused(out, "a 640 file", rt.read_login, p, "CLAUDE_CODE_OAUTH_TOKEN")
        d, _sub, p = self.place()
        link = os.path.join(_sub, "link-token")
        os.symlink(p, link)
        self.refused(out, "a linked file", rt.read_login, link, "CLAUDE_CODE_OAUTH_TOKEN")
        return out

    def test_the_walk_login_place(self):
        def no_place_check(path, run_tree):
            return None

        def exec_without_place(*a, **k):
            with mock.patch.object(rt, "check_login_place", no_place_check):
                return ORIG_EXEC_ARGV(*a, **k)
        self.assert_green_then_red(self.check, [
            ("place-unchecked", patched(rt, "exec_argv", exec_without_place)),
            ("folder-mode-unchecked", patched(rt, "check_login_place", lambda path, run_tree: None)),
            ("bare-admitted", patched(rt, "CLAUDE_BARE_FLAG", "--never-a-flag")),
            ("walk-file-moved", patched(rt, "WALK_LOGIN_FILES", {"claude1": "/tmp/claude-walk-token"})),
        ])


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
                            "MemoryReservation": s.memory_reservation, "NanoCpus": s.nano_cpus(),
                            "ReadonlyRootfs": True, "Tmpfs": {"/tmp": "rw,exec,nosuid,nodev,mode=1777", "/var/tmp": "rw,exec,nosuid,nodev,mode=1777"}},
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
            (["docker", "create", "--memory", str(rt.SIDECAR_MEMORY_BYTES), "--network", "none"], ok(ID["side"])),
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
        # INSPECT_STATUS is filled (14 Oct 2026); its clause stays red-tested with the value put back to PENDING.
        if rt._is_pending(rt.INSPECT_STATUS):
            out.append("INSPECT_STATUS is PENDING: the filled value was not committed")
        L = Launch()
        fake = FakeRuntime()
        try:
            with mock.patch.object(rt, "INSPECT_STATUS", rt.PENDING):
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
            L.launch(fake)   # the real, filled INSPECT_STATUS: only the sidecar clause can refuse
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
            ("no-sidecar-clause", patched(rt, "_check_launch_ready", _inspect_clause_only)),
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


# A claude-code turn as the adapter builds it: its model once and the study's inline settings (review finding 1).
CLAUDE_MODEL = "claude-opus-5-5"
CLAUDE_INNER = ["claude", "-p", "x", "--model", CLAUDE_MODEL, "--settings", rt.claude_study_settings(CLAUDE_MODEL),
                "--disallowedTools", "WebFetch", "WebSearch", "RemoteTrigger", "SendMessage", "ListAgents"]


ORIG_CHECK_CLAUDE_SETTINGS = rt.check_claude_settings


def _print_check_dropped(inner):
    """A mutant of check_claude_settings with its -p/--print clause removed (the rest of the gate kept)."""
    if inner and (len(inner) < 2 or inner[1] not in ("-p", "--print")):
        inner = [inner[0], "-p", "", *inner[1:]]
    ORIG_CHECK_CLAUDE_SETTINGS(inner)


def _program_check_dropped(inner):
    """A mutant of check_claude_settings with its program clause removed (the rest of the gate kept)."""
    if inner and inner[0] != "claude":
        inner = ["claude", *inner[1:]]
    ORIG_CHECK_CLAUDE_SETTINGS(inner)


class TestClaudeSettings(MutantCase):
    """glitch-06's ruling on review finding 1 (14 Oct 2026): the study's Claude settings ride inline by --settings
    (command-line level, above the agent-owned project and local files); exec_argv refuses a turn without exactly them."""

    def check(self):
        out = []
        # The bypass acceptance is RULED not required in -p (glitch-06, 14 Oct 2026): the settings build without it.
        if rt.CLAUDE_BYPASS_KEY != rt.CLAUDE_BYPASS_NOT_REQUIRED or "CLAUDE_BYPASS_KEY" in rt.pending():
            out.append(f"CLAUDE_BYPASS_KEY is not the ruled value: {rt.CLAUDE_BYPASS_KEY!r}")
        ruling = rt.CLAUDE_BYPASS_RULING
        urls = {src[0] for src in ruling["sources"]}
        if ruling["value"] != rt.CLAUDE_BYPASS_NOT_REQUIRED or ruling["ruled_by"] != "glitch-06" \
                or "https://code.claude.com/docs/en/permission-modes.md" not in urls \
                or not any(src[2] == "In non-interactive mode no dialog is shown." for src in ruling["sources"]):
            out.append(f"the bypass ruling is not recorded with its doc and quote: {ruling!r}")
        import box.take_config as tc
        if tc.CLAUDE_BYPASS_KEY != rt.CLAUDE_BYPASS_KEY:
            out.append("take_config's and run_take's bypass keys differ")
        with mock.patch.object(rt, "CLAUDE_BYPASS_KEY", rt.PENDING):
            try:
                rt.claude_study_settings(CLAUDE_MODEL)
                out.append("the study's settings were built while the bypass ruling is PENDING")
            except rt.NotReady:
                pass
        with filled():
            out += self.check_filled()
        return out

    def check_filled(self):
        out = []
        want = rt.claude_study_settings(CLAUDE_MODEL)
        doc = json.loads(want)
        if doc != {"availableModels": [CLAUDE_MODEL], "crossSessionInbound": "refuse",
                   "env": {"CLAUDE_CODE_DISABLE_REFUSAL_FALLBACK": "1", "CLAUDE_CODE_THRIFTY_SONIC": "false",
                           "CLAUDE_CODE_SILENT_TURN_REMINDER": "0"},   # + glitch-b5's parity switch (16 Oct 2026)
                   "permissions": {"deny": ["RemoteTrigger", "SendMessage", "ListAgents"]},
                   "fallbackModel": [],
                   "switchModelsOnFlag": False}:
            out.append(f"the study's settings are {doc}")
        if BYPASS in want:
            out.append("the study's settings carry the bypass acceptance key")
        for bad in (BYPASS, "switchModelsOnFlag", "env", "bad key"):
            with mock.patch.object(rt, "CLAUDE_BYPASS_KEY", bad):
                try:
                    rt.claude_study_settings(CLAUDE_MODEL)
                    out.append(f"bypass key {bad!r} accepted")
                except rt.Refused:
                    pass
        DENY = ["--disallowedTools", "WebFetch", "WebSearch", *rt.ISOLATION_DISALLOWED_TOOLS]
        good = [CLAUDE_INNER, ["claude", "-p", "--settings is just prompt text", "--model", CLAUDE_MODEL,
                               "--settings=" + want, *DENY],
                ["claude", "--print", "--bg is just prompt text", "--model", CLAUDE_MODEL, "--settings", want, *DENY],
                ["claude", "-p", "--background is just prompt text", "--model", CLAUDE_MODEL, "--settings", want, *DENY],
                ["/usr/local/bin/claude"] + CLAUDE_INNER[1:]]
        for inner in good:
            try:
                rt.check_claude_settings(inner)
            except rt.Refused as e:
                out.append(f"a well-formed turn was refused: {e}")
        other = rt.claude_study_settings("claude-sonnet-5-5")
        bad = {"no-settings": ["claude", "-p", "x", "--model", CLAUDE_MODEL, *DENY],
               "two-settings": CLAUDE_INNER + ["--settings", want],
               "another-model's": ["claude", "-p", "x", "--model", CLAUDE_MODEL, "--settings", other, *DENY],
               "switch-true": ["claude", "-p", "x", "--model", CLAUDE_MODEL, "--settings",
                               want.replace('"switchModelsOnFlag":false', '"switchModelsOnFlag":true'), *DENY],
               "no-model": ["claude", "-p", "x", "--settings", want, *DENY],
               "two-models": CLAUDE_INNER + ["--model", "claude-sonnet-5-5"],
               "settings-file": ["claude", "-p", "x", "--model", CLAUDE_MODEL, "--settings", "/opt/cfg/s.json", *DENY],
               # the bypass ruling depends on a -p run: a turn without -p/--print first, or with --bg, is refused
               "no-print": ["claude", "x", "--model", CLAUDE_MODEL, "--settings", want, *DENY],
               "print-not-first": ["claude", "--model", CLAUDE_MODEL, "-p", "x", "--settings", want, *DENY],
               "background": CLAUDE_INNER + ["--bg"],
               "background-eq": CLAUDE_INNER + ["--bg=true"],
               # review-bypass-skills B-1 and B-2: the long alias, and a program other than claude
               "background-long": CLAUDE_INNER + ["--background"],
               "background-long-eq": CLAUDE_INNER + ["--background=1"],
               "bash-program": ["bash"] + CLAUDE_INNER[1:],
               "abs-bash-program": ["/usr/bin/bash"] + CLAUDE_INNER[1:],
               "claude-lookalike": ["/opt/claude/bin/claude-wrapper"] + CLAUDE_INNER[1:],
               "empty": [],
               "with-bypass-key": ["claude", "-p", "x", "--model", CLAUDE_MODEL, "--settings",
                                   json.dumps(dict(json.loads(want), **{BYPASS: True}), sort_keys=True,
                                              separators=(",", ":")), *DENY],
               # the isolation ruling (glitch-6b, 15 Oct 2026): a turn that does not deny the three tools
               "no-deny": ["claude", "-p", "x", "--model", CLAUDE_MODEL, "--settings", want]}
        for name, inner in bad.items():
            try:
                rt.check_claude_settings(inner)
                out.append(f"{name}: admitted")
            except rt.Refused:
                pass
        login = plant_login(tempfile.mkdtemp(prefix="w-"), "CLAUDE_CODE_OAUTH_TOKEN")
        try:
            with mock.patch.object(rt, "read_login", side_effect=AssertionError("login read")):
                rt.exec_argv(ID["take"], bad["no-settings"], user=rt.AGENT_USER, workdir="/", harness=rt.CLAUDE_CODE,
                             run_tree="/srv/w/t1/tree", login_file=login, caller_env=CALLER)
            out.append("exec_argv built a claude-code turn without the study's settings")
        except rt.Refused:
            pass
        except AssertionError:
            out.append("the login was read before the settings refusal")
        # Every Claude turn reaching the box is a -p run: exec_argv refuses one without it, and builds one with it.
        with mock.patch.object(rt, "read_login", side_effect=AssertionError("login read")):
            for name in ("no-print", "print-not-first", "background", "background-long", "bash-program"):
                try:
                    rt.exec_argv(ID["take"], bad[name], user=rt.AGENT_USER, workdir="/", harness=rt.CLAUDE_CODE,
                                 run_tree="/srv/w/t1/tree", login_file=login, caller_env=CALLER)
                    out.append(f"exec_argv built a claude-code turn: {name}")
                except rt.Refused:
                    pass
                except AssertionError:
                    out.append(f"the login was read before the {name} refusal")
        argv, _env = rt.exec_argv(ID["take"], CLAUDE_INNER, user=rt.AGENT_USER, workdir="/", harness=rt.CLAUDE_CODE,
                                  run_tree="/srv/w/t1/tree", login_file=login, caller_env=CALLER)
        tail = argv[len(argv) - len(CLAUDE_INNER):]
        if tail != CLAUDE_INNER or tail[1] not in ("-p", "--print"):
            out.append("the built claude-code exec does not end in the -p turn")
        return out

    def test_the_inline_settings(self):
        self.assert_green_then_red(self.check, [
            ("check-skipped", patched(rt, "check_claude_settings", lambda inner: None)),
            ("switch-on", patched(rt, "claude_study_settings", lambda m: json.dumps(
                {"availableModels": [m], "env": dict(rt.FALLBACK_ENV), "fallbackModel": [],
                 "switchModelsOnFlag": True}, sort_keys=True, separators=(",", ":")))),
            ("no-allowlist", patched(rt, "claude_study_settings", lambda m: json.dumps(
                {"env": dict(rt.FALLBACK_ENV), "fallbackModel": [], "switchModelsOnFlag": False},
                sort_keys=True, separators=(",", ":")))),
            # the key re-added, three ways: in the built settings, as the ruled value, and the ruled check dropped
            ("bypass-key-re-added", patched(rt, "claude_study_settings", lambda m: json.dumps(
                {BYPASS: True, "availableModels": [m], "env": dict(rt.FALLBACK_ENV), "fallbackModel": [],
                 "switchModelsOnFlag": False}, sort_keys=True, separators=(",", ":")))),
            ("bypass-key-as-value", patched(rt, "CLAUDE_BYPASS_KEY", BYPASS)),
            ("bypass-still-pending", patched(rt, "CLAUDE_BYPASS_KEY", rt.PENDING)),
            # -p dropped from the gate, and --bg admitted
            ("print-check-dropped", patched(rt, "check_claude_settings", _print_check_dropped)),
            ("background-admitted", patched(rt, "CLAUDE_BACKGROUND_FLAGS", ())),
            ("background-long-admitted", patched(rt, "CLAUDE_BACKGROUND_FLAGS", ("--bg",))),
            ("bash-program-admitted", patched(rt, "check_claude_settings", _program_check_dropped)),
            ("prompt-read-as-flag", patched(rt, "_flag_values", lambda inner, flag: [
                inner[i + 1] if i + 1 < len(inner) else None for i, t in enumerate(inner) if t == flag])),
        ])


def _inspect_clause_only(sidecar):
    """A mutant of run_take._check_launch_ready with its sidecar-expectation clause removed."""
    if rt._is_pending(rt.INSPECT_STATUS):
        raise rt.NotReady("INSPECT_STATUS is PENDING")


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
# docker top's output on athena (docker 29.8.1, rootless), verbatim from the stub take (run 1's columns; its pids).
ATHENA_TOP_LIVE = ("PID                 UID                 COMMAND\n1527963             10003               sleep\n"
                   "1529070             10001               python3\n")
ATHENA_TOP_AFTER_KILL = "PID                 UID                 COMMAND\n1527963             10003               sleep\n"


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
            with mock.patch.object(rt, "TOP_FORMAT", rt.PENDING):
                rt.agent_processes(FakeRuntime(), ID["take"], agent_uid=10001, uid_map=UID_MAP)
            out.append("top read while its form is PENDING")
        except rt.NotReady:
            pass
        # The filled TOP_FORMAT (container namespace) on the tables athena printed in the stub take
        # (lane-reports/stub-take-20261014/stub-take-run2.json top_live and top_after_kill): host pids, container uids.
        for printed, want in ((ATHENA_TOP_LIVE, [1529070]), (ATHENA_TOP_AFTER_KILL, [])):
            fake = FakeRuntime([(["docker", "top", ID["take"], "-eo", "pid,uid,comm"], ok(printed))])
            got = rt.agent_processes(fake, ID["take"], agent_uid=10001, uid_map=UID_MAP, caller_env=CALLER)
            if got != want:
                out.append(f"the filled form read {got} from athena's table, not {want}")
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
        # athena's running take after the stub turns (stub-take-run2.json take_state_after_turns, its typed fields)
        athena = [{"State": {"Status": "running", "Running": True, "Paused": False, "Restarting": False,
                             "OOMKilled": False, "Dead": False, "Pid": 1527963, "ExitCode": 0, "Error": ""}}]
        fake = FakeRuntime([(["docker", "container", "inspect", ID["take"]], ok(json.dumps(athena)))])
        if rt.container_state(fake, ID["take"], caller_env=CALLER) != {"running": True, "exit_code": 0,
                                                                       "oom_killed": False}:
            out.append("the filled spellings misread athena's State")
        if not rt._is_pending(rt.INSPECT_STATUS):   # the filled spellings read a synthetic exit record too
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
            with mock.patch.object(rt, "INSPECT_STATUS", rt.PENDING):
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
            r = rt.run_turn(fake, ID["take"], CLAUDE_INNER, harness=rt.CLAUDE_CODE, run_tree="/srv/w/t1/tree",
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
            r = rt.run_turn(fake, ID["take"], CLAUDE_INNER, harness=rt.CLAUDE_CODE, run_tree="/srv/w/t1/tree",
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


# ------------------------------------------------------------------- the Codex lease's placement (glitch-06, 14 Oct)
class TestLeasePlacement(MutantCase):
    """place_lease copies the registered Codex lease file into the per-take config folder as auth.json, behind the
    CODEX_SUBSCRIPTION_READY gate (opened by B8 under ruling R5, 18 Oct 2026; closed, it refuses). It uses
    no os name beyond OS_ATTRS: an exclusive no-follow create at mode 600, then the existing lstat verifies mode and
    owner; a mode other than 600 (a umask, say) refuses, failing closed. Every refusal names the file and the rule,
    never the contents. The planted value is a fake."""

    FAKE = b'{"tokens": {"access_token": "FAKE-lease-access-0123456789-PLANTED"}}\n'

    def src(self, body=None, mode=0o600, folder_mode=0o700):
        d = tempfile.mkdtemp(prefix="lease-src-")
        os.chmod(d, folder_mode)
        p = os.path.join(d, "codex2-auth.json")
        fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.write(fd, self.FAKE if body is None else body)
        os.close(fd)
        os.chmod(p, mode)
        return p

    def cfg(self, mode=0o700):
        parent = tempfile.mkdtemp(prefix="w-")
        path = rt.make_config_dir(parent)
        os.chmod(path, mode)
        return path

    def refused(self, out, label, src, cfg, *words):
        try:
            rt.place_lease(src, cfg)
            out.append(f"{label}: placed")
            return
        except rt.LoginRefused as e:
            msg = str(e)
        except Exception as e:  # noqa: BLE001 - any other exception is a crash, not a refusal
            out.append(f"{label}: raised {type(e).__name__}, not a refusal")
            return
        if any(w not in msg for w in words):
            out.append(f"{label}: the refusal does not name {words}: {msg}")
        if "PLANTED" in msg:
            out.append(f"{label}: the refusal carries the lease's contents")

    def check_gate(self):
        # B8 (ruling R5, 18 Oct 2026): the committed gate is open. The closed gate's refusal is still checked here,
        # with the gate pinned closed: no lease is placed and nothing reaches the config folder while it is closed.
        out = []
        if rt.CODEX_SUBSCRIPTION_READY is not True:
            out.append("the Codex gate is not open in the committed module")
        src, cfg = self.src(), self.cfg()
        with mock.patch.object(rt, "CODEX_SUBSCRIPTION_READY", False):
            try:
                rt.place_lease(src, cfg)
                out.append("the closed gate placed a lease")
            except rt.NotReady as e:
                if str(e) != rt.CODEX_SUBSCRIPTION_NOT_READY:
                    out.append(f"the closed gate refused with another message: {e}")
        if os.path.lexists(os.path.join(cfg, "auth.json")):
            out.append("the closed gate left a file in the config folder")
        return out

    def test_the_gate_is_open_and_the_closed_gate_refuses(self):
        self.assertEqual(problems_of(self.check_gate), [])

    def check(self):
        out = []
        src, cfg = self.src(), self.cfg()
        placement = rt.place_lease(src, cfg)
        # round 17 B3: place_lease returns its placement record, the read-back facts the host trusts after the grant
        if not isinstance(placement, getattr(rt, "LeasePlacement", ())):
            out.append(f"place_lease returned no placement record: {type(placement).__name__}")
        dst = getattr(placement, "path", placement)
        if dst != os.path.join(cfg, "auth.json"):
            out.append(f"the lease was placed at {dst!r}, not the config folder's auth.json")
        else:
            st = os.lstat(dst)
            with open(dst, "rb") as fh:
                same = fh.read() == self.FAKE
            if not same or not stat_reg(st) or (st.st_mode & 0o7777) != 0o600 or st.st_uid != os.getuid() \
                    or st.st_nlink != 1:
                out.append("the placed lease is not the same bytes, a regular file, mode 600, ours, one link")
            cst = os.lstat(cfg)
            want = (dst, cst.st_dev, cst.st_ino, st.st_dev, st.st_ino, st.st_mode, st.st_nlink, st.st_uid, len(self.FAKE))
            got = tuple(getattr(placement, k, None) for k in ("path", "folder_dev", "folder_ino", "dev", "ino", "mode",
                                                               "nlink", "uid", "size"))
            if got != want:
                out.append(f"the placement record is not place_lease's read-back: {got} != {want}")
            if getattr(placement, "uid_map", None) != ():
                out.append("a fresh placement record is already bound to a uid map")
        # the source
        self.refused(out, "a relative source", "codex2-auth.json", self.cfg(), "absolute path")
        self.refused(out, "a missing source", os.path.join(tempfile.mkdtemp(prefix="w-"), "none.json"), self.cfg(),
                     "none.json", "does not exist")
        real = self.src()
        link = os.path.join(os.path.dirname(real), "link.json")
        os.symlink(real, link)
        self.refused(out, "a linked source", link, self.cfg(), "link.json", "regular file, never a link")
        self.refused(out, "a source at mode 644", self.src(mode=0o644), self.cfg(), "mode must be 600")
        two = self.src()
        os.link(two, two + ".2")
        self.refused(out, "a source with two links", two, self.cfg(), "exactly one link")
        self.refused(out, "an oversize source", self.src(body=b"x" * (rt.LEASE_MAX_BYTES + 1)), self.cfg(),
                     "at most")
        self.refused(out, "an empty source", self.src(body=b""), self.cfg(), "empty")
        repo = tempfile.mkdtemp(prefix="w-")
        os.makedirs(os.path.join(repo, ".git"))
        inrepo = os.path.join(repo, "auth.json")
        fd = os.open(inrepo, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.write(fd, self.FAKE)
        os.close(fd)
        self.refused(out, "a source inside a repository", inrepo, self.cfg(), "outside every repository")
        # the config folder
        self.refused(out, "a relative config folder", self.src(), "cfg-x", "absolute path")
        c = self.cfg()
        clink = c + "-link"
        os.symlink(c, clink)
        self.refused(out, "a linked config folder", self.src(), clink, "a folder, never a link")
        self.refused(out, "a config folder at mode 755", self.src(), self.cfg(mode=0o755), "mode 700")
        rcfg = os.path.join(repo, "cfg")
        os.mkdir(rcfg, 0o700)
        self.refused(out, "a config folder inside a repository", self.src(), rcfg, "outside every repository")
        c = self.cfg()
        open(os.path.join(c, "auth.json"), "w").close()
        self.refused(out, "a config folder that already holds auth.json", self.src(), c, "auth.json",
                     "already holds")
        # a umask that narrows the create: refused, never widened by a chmod
        c, narrowed_src = self.cfg(), self.src()          # made first: the umask narrows only the placement
        old = os.umask(0o277)
        try:
            self.refused(out, "a placement narrowed by the umask to 400", narrowed_src, c, "auth.json",
                         "mode must be 600")
        finally:
            os.umask(old)
        with mock.patch.object(rt.os, "getuid", lambda me=os.getuid(): me + 1):
            self.refused(out, "a source not owned by the reading user", self.src(), self.cfg(), "codex2-auth.json",
                         "lease file must be owned")
        self.refused(out, "a missing config folder", self.src(), os.path.join(tempfile.mkdtemp(prefix="w-"), "nope"),
                     "nope", "does not exist")
        # the review's NIT 5: with the lexists check blinded, the exclusive no-follow create itself refuses an existing
        # auth.json and a link planted at its path; neither is written through
        real_lexists = os.path.lexists
        for label, plant in (("an existing auth.json the lexists check missed", "file"),
                             ("a link at auth.json the lexists check missed", "link")):
            c = self.cfg()
            dst, elsewhere = os.path.join(c, "auth.json"), os.path.join(c, "elsewhere")
            with open(elsewhere, "wb") as fh:
                fh.write(b"untouched")
            if plant == "file":
                with open(dst, "wb") as fh:
                    fh.write(b"untouched")
            else:
                os.symlink(elsewhere, dst)
            with mock.patch.object(rt.os.path, "lexists",
                                   lambda p, _d=dst: False if p == _d else real_lexists(p)):
                self.refused(out, label, self.src(), c, "auth.json", "could not be written")
            for p in (dst, elsewhere):
                with open(p, "rb") as fh:
                    if fh.read() != b"untouched":
                        out.append(f"{label}: {os.path.basename(p)} was written through")
        real_lstat = os.lstat
        # the placed file read back as another user's, with a second link, or shorter or longer than the source (the
        # review of 6c21320b, MINOR 4: both directions, so a `>` in place of `!=` is caught)
        for label, field, delta, words in (
                ("a placed lease not owned by the reading user", 4, 1, ("auth.json", "owned")),
                ("a placed lease with a second link", 3, 1, ("auth.json", "exactly one link")),
                ("a placed lease shorter than the source", 6, -1, ("auth.json", "whole lease file")),
                ("a placed lease longer than the source", 6, 1, ("auth.json", "whole lease file"))):
            c = self.cfg()

            def readback(p, *a, _placed=os.path.join(c, "auth.json"), _field=field, _delta=delta, **k):
                st = real_lstat(p, *a, **k)
                if p == _placed:
                    f = list(st)
                    f[_field] = f[_field] + _delta
                    return os.stat_result(f)
                return st
            with mock.patch.object(rt.os, "lstat", readback):
                self.refused(out, label, self.src(), c, *words)
        return out

    def test_placement(self):
        with mock.patch.object(rt, "CODEX_SUBSCRIPTION_READY", True):
            self.assertEqual(problems_of(self.check), [])


# ------------------------------------------------- the registered lease source (lane vendor-admission round 17, B2)
class TestLeaseSource(MutantCase):
    """run_take.LEASE_SOURCES registers the Codex lease file by account (plan codex2-signin-road section 1): an absolute
    path whose account folder sits in the one private folder that holds every WALK_LOGIN_FILES account folder, so
    walk_builders.account_emails_path() still finds one folder; never a WALK_LOGIN_FILES entry (that map is for one-line
    NAME=value files read by read_login, and a JSON lease there would break the walk-login scripts)."""

    REGISTERED = {"codex2": "/home/javier/gap4-secrets/codex2/auth.json"}

    def check(self):
        out = []
        leases, walks = getattr(rt, "LEASE_SOURCES", None), rt.WALK_LOGIN_FILES
        if not isinstance(leases, dict) or "codex2" not in leases:
            return [f"LEASE_SOURCES records no codex2 lease: {leases!r}"]
        tops = {os.path.dirname(os.path.dirname(p)) for p in walks.values()}
        for account, path in leases.items():
            if not isinstance(path, str) or not os.path.isabs(path) or os.path.normpath(path) != path:
                out.append(f"LEASE_SOURCES[{account!r}] is not an absolute path: {path!r}")
                continue
            if os.path.basename(os.path.dirname(path)) != account:
                out.append(f"LEASE_SOURCES[{account!r}] is not in its own account folder: {path!r}")
            if tops != {os.path.dirname(os.path.dirname(path))}:
                out.append(f"LEASE_SOURCES[{account!r}] is outside the one private folder {sorted(tops)}: {path!r}")
            if account in walks or path in walks.values():
                out.append(f"LEASE_SOURCES[{account!r}] is also a WALK_LOGIN_FILES entry")
        if os.path.basename(leases["codex2"]) != "auth.json":
            out.append("the codex2 lease is not the auth.json Codex writes under CODEX_HOME")
        from walk_builders import account_emails_path
        if account_emails_path() != "/home/javier/gap4-secrets/account-emails.json":
            out.append(f"account_emails_path() moved: {account_emails_path()!r}")
        return out

    def test_the_lease_source_is_registered(self):
        self.assertEqual(getattr(rt, "LEASE_SOURCES", None), self.REGISTERED, "not the registered lease source")
        self.assertEqual(problems_of(self.check), [])

    def test_mutants(self):
        here = self.REGISTERED["codex2"]
        self.assert_green_then_red(self.check, (
            ("path relative", patched(rt, "LEASE_SOURCES", {"codex2": "gap4-secrets/codex2/auth.json"})),
            ("path outside the shared folder", patched(rt, "LEASE_SOURCES",
                                                       {"codex2": "/home/javier/other-secrets/codex2/auth.json"})),
            ("codex2 added to WALK_LOGIN_FILES", lambda: mock.patch.dict(rt.WALK_LOGIN_FILES, {"codex2": here})),
            ("another account's folder", patched(rt, "LEASE_SOURCES",
                                                 {"codex2": "/home/javier/gap4-secrets/r4-g/auth.json"})),
            ("not normalised", patched(rt, "LEASE_SOURCES",
                                       {"codex2": "/home/javier/gap4-secrets/x/../codex2/auth.json"})),
        ))


# ------------------------------------------------------------- the no-login launcher variant (glitch-06, 14 Oct)
class TestNoLoginLauncher(MutantCase):
    """glitch-06's ruling 2: LAUNCHER_SOURCE is supplied at run time (docker exec ... python3 -I -S -c SOURCE), never
    baked into the image, so a variant is built here: the reserved name NO_LOGIN copies no credential into the agent's
    environment, and launcher_argv admits it only for a Codex row behind the closed lease gate. Claude Code's road is
    unchanged. The launcher program runs in-process here with os.execvpe faked: no process starts."""

    def run_launcher(self, argv, environ):
        """The environment the launcher would exec the harness with, or the exception it raised."""
        import os as real_os
        got = {}

        def fake_exec(prog, args, env):
            got["env"] = dict(env)
            got["args"] = list(args)
            raise SystemExit(0)
        cwd = real_os.getcwd()
        home = tempfile.mkdtemp(prefix="w-")
        real_os.chdir(home)
        try:
            with mock.patch.object(real_os, "execvpe", fake_exec), mock.patch.dict(real_os.environ, environ,
                                                                                    clear=True), \
                    mock.patch.object(sys, "argv", ["-c", *argv]):
                try:
                    exec(compile(rt.LAUNCHER_SOURCE, "<launcher>", "exec"), {"__name__": "__main__"})
                except SystemExit:
                    pass
                except Exception as e:  # noqa: BLE001 - reported as the launcher's failure
                    return e
        finally:
            real_os.chdir(cwd)
        return got

    def check(self):
        out = []
        home = tempfile.mkdtemp(prefix="w-")
        # Claude Code's road: the one credential is copied from the exec's environment by its name
        got = self.run_launcher(["CLAUDE_CODE_OAUTH_TOKEN", "1", f"HOME={home}", "claude", "-p"],
                                {"CLAUDE_CODE_OAUTH_TOKEN": "FAKE-claude-0123456789-PLANTED"})
        if not isinstance(got, dict) or got["env"] != {"HOME": home,
                                                       "CLAUDE_CODE_OAUTH_TOKEN": "FAKE-claude-0123456789-PLANTED"}:
            out.append(f"the credential road changed: {got!r}"[:200])
        # the no-login road: nothing is copied, whatever the exec's environment holds
        got = self.run_launcher([rt.NO_LOGIN, "1", f"HOME={home}", "codex", "exec"],
                                {"CODEX_API_KEY": "FAKE-api-0123456789-PLANTED", "OPENAI_API_KEY": "FAKE-oa-PLANTED"})
        if not isinstance(got, dict) or got["env"] != {"HOME": home}:
            out.append(f"the no-login launcher copied something or failed: {type(got).__name__}")
        if rt.NO_LOGIN != "-" or rt._NAME.fullmatch(rt.NO_LOGIN):
            out.append("NO_LOGIN is not the reserved '-' (a name no variable can have)")
        # launcher_argv: the reserved name only for a Codex row, only behind the open gate (closed here, by B8-1)
        with mock.patch.object(rt, "CODEX_SUBSCRIPTION_READY", False):
            try:
                rt.launcher_argv(rt.NO_LOGIN, {"A": "1"}, ["codex", "exec"], harness=rt.CODEX)
                out.append("the closed gate admitted the no-login launcher")
            except rt.NotReady as e:
                if str(e) != rt.CODEX_SUBSCRIPTION_NOT_READY:
                    out.append(f"the closed gate refused with another message: {e}")
        with mock.patch.object(rt, "CODEX_SUBSCRIPTION_READY", True):
            vals = rt.exec_values(rt.CODEX, "/srv/w/t1/tree")   # the review's MINOR 2: exactly the Codex row's names
            argv = rt.launcher_argv(rt.NO_LOGIN, vals, ["codex", "exec"], harness=rt.CODEX)
            pairs = [f"{k}={vals[k]}" for k in sorted(vals)]
            if argv != [*rt.LAUNCHER, "-", str(len(pairs)), *pairs, "codex", "exec"]:
                out.append(f"the no-login launcher argv is {argv!r}"[:200])
            for harness in (rt.CLAUDE_CODE, rt.GEMINI, None):
                try:
                    rt.launcher_argv(rt.NO_LOGIN, {"A": "1"}, ["x"], harness=harness)
                    out.append(f"the no-login launcher was admitted for {harness!r}")
                except rt.NotReady:
                    out.append(f"{harness!r}: NotReady, not a refusal")
                except rt.Refused as e:
                    if "only for a Codex row" not in str(e):
                        out.append(f"{harness!r}: refused without naming the rule: {e}")
        return out

    def test_no_login_launcher(self):
        self.assertEqual(problems_of(self.check), [])


# ----------------------------------------------- the Codex row: subscriptions only, no environment login (glitch-06)
# The billing-route variables named from the pinned Codex binary's own strings (codex-auth-binary-markers.json,
# sources[0].matches[N].context; the binary's strings run together, so each boundary is the next CODEX_/OPENAI_
# prefix). The lane report cites each one and lists what the evidence cannot settle.
CODEX_ROUTE_NAMED = ("CODEX_AUTHAPI_BASE_URL", "CODEX_AGENT_IDENTITY_AUTHAPI_BASE_URL",
                     "CODEX_AGENT_IDENTITY_JWKS_BASE_URL", "CODEX_REVOKE_TOKEN_URL_OVERRIDE", "CODEX_CONNECTORS_TOKEN",
                     "OPENAI_ORGANIZATION", "OPENAI_FEDERATION_RULE_ID", "OPENAI_IDENTITY_TOKEN_FILE")
# glitch-06's ruling on the docs-read candidates (14 Oct 2026): the pinned Codex is 0.162.1 (box/codex/image.lock,
# harness.version), the version test_env_allowlist's DOCS_READ_VARIABLES was read at (rust-v0.162.1), so its Codex names
# not already above are refused if present too. Refusing more fails closed.
CODEX_ROUTE_DOCS_READ = ("OPENAI_PROJECT", "OPENAI_BASE_URL", "CODEX_ACCESS_TOKEN", "OPENAI_WORKLOAD_IDENTITY_CONTEXT",
                         "CODEX_OSS_BASE_URL", "CODEX_OSS_PORT", "AWS_BEARER_TOKEN_BEDROCK", "AWS_ACCESS_KEY_ID",
                         "AWS_SECRET_ACCESS_KEY", "AWS_REGION", "AWS_DEFAULT_REGION", "AWS_PROFILE",
                         # the review's NIT 7: matches[2]'s ambiguous end, both spellings refused (fails closed)
                         "CODEX_APP_SERVER_LOGIN_ISSUER", "CODEX_APP_SERVER_LOGIN_ISSUERA")


# The pinned Codex binary's environment-name sweep (glitch-06, 14 Oct 2026): its committed record and classification.
_CLONE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SWEEP_DIR = os.path.join(_CLONE, "lane-reports", "stub-take-20261014", "probes")


def _sweep_files():
    return (os.path.join(SWEEP_DIR, "codex-env-name-sweep-athena-20261014.json"),
            os.path.join(SWEEP_DIR, "codex-env-name-classification-20261014.json"))


CODEX_BINARY_SHA256 = "628e35487d888a28f0427fc37501da529dd3d81fcbad7a2c3421c1e8670d92e1"


def run_classifier(script: str, sweep_path: str) -> bytes:
    """The committed classifier's stdout for the committed sweep, run in this process (runpy, `-I`-equivalent: no
    process starts under this module's guard), so a classification file is bound to the program that writes it."""
    import io
    import runpy
    out = io.StringIO()
    argv = sys.argv
    sys.argv = [script, sweep_path]
    try:
        with contextlib.redirect_stdout(out):
            runpy.run_path(os.path.join(SWEEP_DIR, script), run_name="__main__")
    finally:
        sys.argv = argv
    return out.getvalue().encode()


def _lock_image(arm: str) -> str:
    with open(os.path.join(os.path.dirname(rt.__file__), arm, "image.lock"), encoding="utf-8") as fh:
        return json.load(fh)["image_id"]


def _gemini_refused() -> tuple:
    with open(os.path.join(SWEEP_DIR, "gemini-env-name-classification-20261014.json"), encoding="utf-8") as fh:
        return tuple(json.load(fh)["refuse_if_present"])


def sweep_refused() -> tuple:
    with open(_sweep_files()[1], encoding="utf-8") as fh:
        return tuple(json.load(fh)["refuse_if_present"])


class TestCodexBinarySweep(MutantCase):
    """Every billing, route, credential or ambiguous name the pinned Codex binary carries (the committed sweep and its
    deterministic classification) is refused if present for every arm; the classification is bound to the sweep by
    its sha256 and by re-deriving the split names; no take row's own name is refused."""

    def check(self):
        out = []
        sweep_path, class_path = _sweep_files()
        with open(sweep_path, "rb") as fh:
            sweep_raw = fh.read()
        sweep = json.loads(sweep_raw)
        with open(class_path, encoding="utf-8") as fh:
            cls = json.load(fh)
        if cls["sweep_sha256"] != hashlib.sha256(sweep_raw).hexdigest():
            out.append("the classification does not bind the committed sweep's bytes")
        with open(class_path, "rb") as fh:
            class_raw = fh.read()
        if run_classifier("classify_codex_env_names.py", sweep_path) != class_raw:
            out.append("the committed Codex classification is not the classifier's output for the committed sweep")
        markers = os.path.join(_CLONE, "lane-reports", "live-box-evidence-2026-10-13", "codex-auth-binary-markers.json")
        with open(markers, encoding="utf-8") as fh:
            marker_sha = json.load(fh)["sources"][0]["sha256"]
        if not (sweep["binary_sha256"] == cls["binary_sha256"] == marker_sha == CODEX_BINARY_SHA256):
            out.append("the sweep is not of the pinned binary (the full sha256, the markers file's)")
        if sweep["image"] != _lock_image("codex"):
            out.append("the Codex sweep is not of the pinned take-o image (box/codex/image.lock image_id)")
        split = re.compile(r"(?=(?:CODEX|OPENAI|AWS|AZURE|ANTHROPIC|GOOGLE)_)")
        name = re.compile(r"(CODEX|OPENAI|AWS|AZURE|ANTHROPIC|GOOGLE)_[A-Z0-9_]+")
        derived = sorted({p for r in sweep["names"] for p in split.split(r) if name.fullmatch(p)})
        if [r["match"] for r in cls["rows"]] != derived:
            out.append("the classification does not place every name the sweep found")
        refuse = set(cls["refuse_if_present"])
        want = {n for r in cls["rows"] if r["class"] in ("credential", "route", "ambiguous") for n in r["names"]}
        want |= {g["name"] for r in cls["rows"] for g in r.get("glued", ())
                 if g["class"] in ("credential", "route", "ambiguous")}
        if refuse != want:
            out.append("the refuse list is not every credential, route and ambiguous name (glued ones included)")
        for n in ("SSL_CERT_FILE", "SSL_CERT_DIR", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE", "NODE_EXTRA_CA_CERTS",
                  "GIT_SSL_CAINFO", "NODE_USE_ENV_PROXY", "ELECTRON_GET_USE_PROXY", "NODE_REPL_AUTH_TOKEN",
                  "EXEC_WRAPPER"):
            if n not in refuse:
                out.append(f"{n}, glued in the binary's strings, is not refused")
        if "HTTPS_PROXY" in refuse:
            out.append("HTTPS_PROXY, every row's egress proxy, is refused")
        if tuple(rt.CODEX_BINARY_SWEEP_REFUSED) != tuple(cls["refuse_if_present"]):
            out.append("run_take's sweep tuple drifted from the committed classification")
        for arm in (rt.CODEX, rt.CLAUDE_CODE, rt.GEMINI):
            missing = sorted(refuse - set(rt.refused_variables(arm)))
            if missing:
                out.append(f"{arm}: the sweep's names not refused: {missing[:5]}")
            in_row = sorted(set(rt.TAKE_ENV[arm]) & set(rt.refused_variables(arm)))
            if in_row:
                out.append(f"{arm}: its own row's names are refused: {in_row}")
        if "CODEX_HOME" in rt.refused_variables(rt.CODEX):
            out.append("CODEX_HOME, the Codex row's own config home, is refused")
        return out

    def test_the_binary_sweep_is_refused(self):
        self.assertEqual(problems_of(self.check), [])


class TestRefusedPrefixes(MutantCase):
    """glitch-06's ruling on the sweep's residual (14 Oct 2026): any environment name starting with
    CODEX_NETWORK_PROXY_SNAPSHOT_BROKERED_UNSET_ or CODEX_NETWORK_PROXY_SNAPSHOT_BROKERED_VALUE_ is refused for every
    arm, in this process's own environment, the caller's and an exec's request, by name only."""

    PREFIXES = ("CODEX_NETWORK_PROXY_SNAPSHOT_BROKERED_UNSET_", "CODEX_NETWORK_PROXY_SNAPSHOT_BROKERED_VALUE_")

    def check(self):
        out = []
        if tuple(rt.REFUSED_NAME_PREFIXES) != self.PREFIXES:
            out.append(f"REFUSED_NAME_PREFIXES is {rt.REFUSED_NAME_PREFIXES!r}")
        for arm in (rt.CLAUDE_CODE, rt.CODEX, rt.GEMINI):
            for prefix in self.PREFIXES:
                for name in (prefix + "HTTPS_PROXY", prefix + "X", prefix):
                    for where in ("caller", "own", "requested"):
                        try:
                            with mock.patch.dict(os.environ, {name: FAKE_VALUE} if where == "own" else {},
                                                 clear=True):
                                rt.check_environment(arm, {"PATH": "/bin", name: FAKE_VALUE} if where == "caller"
                                                     else {"PATH": "/bin"},
                                                     requested=(name,) if where == "requested" else ())
                            out.append(f"{arm}: {name} ({where}) admitted")
                        except rt.Refused as e:
                            if name not in str(e) or FAKE_VALUE in str(e):
                                out.append(f"{arm}: {name} ({where}) refused without its name, or with its value")
            bad = sorted(n for n in rt.TAKE_ENV[arm] if n.startswith(self.PREFIXES))
            if bad:
                out.append(f"{arm}: its row names a refused prefix: {bad}")
        return out

    def test_refused_prefixes(self):
        self.assertEqual(problems_of(self.check), [])


CLAUDE_SWEEP_DIR = os.path.join(_CLONE, "lane-reports", "stub-take-20261015")
CLAUDE_BINARY_SHA256 = "24972e3bc859fab2b46ed4c1e51f7d6130f06d3bd550811a114640de3370d0de"
# The ruled names, pinned as a literal (the review of ad71ca07, MINOR 4: a reclassified CLAUDE_CODE_GATEWAY_TOKEN must
# turn this red, not pass): glitch-6b's 4(i) and the review's three.
CLAUDE_RULED_REFUSED = (
    "CLAUDE_CODE_USE_ANTHROPIC_AWS", "CLAUDE_CODE_USE_ANTHROPIC_GOOGLE_CLOUD", "CLAUDE_CODE_USE_MANTLE",
    "CLAUDE_CODE_USE_GATEWAY", "CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST", "CLAUDE_CODE_HOST_CREDS_FILE",
    "ANTHROPIC_BEDROCK_BASE_URL", "ANTHROPIC_VERTEX_BASE_URL", "ANTHROPIC_FOUNDRY_BASE_URL", "ANTHROPIC_FOUNDRY_RESOURCE",
    "ANTHROPIC_AWS_BASE_URL", "ANTHROPIC_GOOGLE_CLOUD_BASE_URL", "ANTHROPIC_BEDROCK_MANTLE_BASE_URL",
    "ANTHROPIC_UNIX_SOCKET", "ANTHROPIC_FOUNDRY_AUTH_TOKEN", "ANTHROPIC_IDENTITY_TOKEN", "ANTHROPIC_IDENTITY_TOKEN_FILE",
    "ANTHROPIC_ENVIRONMENT_KEY", "ANTHROPIC_WORK_SECRET", "CLAUDE_CODE_OAUTH_TOKEN_FILE_DESCRIPTOR",
    "CLAUDE_CODE_GATEWAY_TOKEN", "CLAUDE_CODE_GATEWAY_TOKEN_FILE_DESCRIPTOR", "CLAUDE_CODE_CUSTOM_OAUTH_URL",
    "AWS_ENDPOINT_URL_BEDROCK_RUNTIME")
CLAUDE_SIX_SWITCHES = ("CLAUDE_CODE_USE_ANTHROPIC_AWS", "CLAUDE_CODE_USE_ANTHROPIC_GOOGLE_CLOUD", "CLAUDE_CODE_USE_MANTLE",
                       "CLAUDE_CODE_USE_GATEWAY", "CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST", "CLAUDE_CODE_HOST_CREDS_FILE")


def _claude_files():
    d = CLAUDE_SWEEP_DIR
    return (os.path.join(d, "claude-2.1.296-binary-sweep-20261015.json"),
            os.path.join(d, "claude-2.1.296-route-names-20261015.json"),
            os.path.join(d, "claude-2.1.296-env-refusal-20261015b.json"),
            os.path.join(d, "probes", "classify_claude_env_names_v2.py"))


def _claude_refused() -> tuple:
    with open(_claude_files()[2], encoding="utf-8") as fh:
        return tuple(json.load(fh)["refuse_if_present"])


def _exempting(loads, name):
    """json.loads that adds `name` to a classification's exempt map (the NIT B mutant: an exemption added)."""
    def wrapped(raw, *a, **k):
        doc = loads(raw, *a, **k)
        if isinstance(doc, dict) and isinstance(doc.get("exempt"), dict):
            doc["exempt"] = dict(doc["exempt"], **{name: "the operator session's own token"})
        return doc
    return wrapped


def run_claude_classifier() -> bytes:
    """classify_claude_env_names.py's stdout for the committed records, run in this process (runpy)."""
    import io
    import runpy
    sweep, route, _, script = _claude_files()
    out = io.StringIO()
    argv = sys.argv
    sys.argv = [script, sweep, route]
    try:
        with contextlib.redirect_stdout(out):
            runpy.run_path(script, run_name="__main__")
    finally:
        sys.argv = argv
    return out.getvalue().encode()


class TestClaudeBinarySweep(MutantCase):
    """glitch-6b's ruling 4(i), 15 Oct 2026: the pinned Claude Code 2.1.296 binary's provider and gateway switches and
    the inference credentials no stop list held are refused if present for every arm, from the committed sweep (box
    ba6d7f14) and its deterministic classification, re-run here byte for byte; the binary sha256 sits beside the take
    lock (run_take.CLAUDE_BINARY), bound to box/image.lock's image id, so a changed image refuses this binding."""

    def check(self):
        out = []
        sweep_path, route_path, class_path, _ = _claude_files()
        with open(class_path, "rb") as fh:
            class_raw = fh.read()
        cls = json.loads(class_raw)
        if run_claude_classifier() != class_raw:
            out.append("the committed Claude classification is not the classifier's output for the committed sweep")
        for path, key in ((sweep_path, "sweep_sha256"), (route_path, "route_names_sha256")):
            with open(path, "rb") as fh:
                if hashlib.sha256(fh.read()).hexdigest() != cls[key]:
                    out.append(f"the classification does not bind {os.path.basename(path)}'s bytes")
        binary = getattr(rt, "CLAUDE_BINARY", None)
        if not isinstance(binary, dict):
            return out + ["run_take has no CLAUDE_BINARY beside the take lock"]
        if not (cls["binary_sha256"] == binary.get("sha256") == CLAUDE_BINARY_SHA256):
            out.append("the sweep is not of the pinned binary sha256 (run_take.CLAUDE_BINARY)")
        if not (cls["image"] == binary.get("image_id") == _lock_image(".")):
            out.append("the Claude binary record is not of box/image.lock's image id")
        if binary.get("path") != cls["binary_path"]:
            out.append("CLAUDE_BINARY's path is not the swept path")
        refuse = tuple(cls["refuse_if_present"])
        if tuple(getattr(rt, "CLAUDE_BINARY_SWEEP_REFUSED", ())) != refuse:
            out.append("run_take's Claude sweep tuple drifted from the committed classification")
        for n in CLAUDE_SIX_SWITCHES:
            if n not in refuse:
                out.append(f"{n}, a billing switch outside every pattern, is not refused")
        claude_refused = rt.refused_variables(rt.CLAUDE_CODE)
        for n in CLAUDE_RULED_REFUSED:
            if n not in claude_refused:
                out.append(f"{n}, a ruled name, is not refused for a Claude take")
        # Completeness (MINOR 4): every name the sweep's patterns or the route read carried is refused, in a take
        # row, or exempt with a reason.
        with open(sweep_path, encoding="utf-8") as fh:
            swept = set(json.load(fh)["names"])
        with open(route_path, encoding="utf-8") as fh:
            swept |= set(json.load(fh)["names"])
        rows = set().union(*(set(v) for v in rt.TAKE_ENV.values()))
        exempt = {n for n, why in cls.get("exempt", {}).items() if isinstance(why, str) and why.strip()}
        if set(cls.get("exempt", {})) != {"CLAUDE_CODE_OAUTH_TOKEN"}:      # closure review NIT B: pinned exactly
            out.append(f"the exemption set is {sorted(cls.get('exempt', {}))}, not exactly the Claude login")
        loose = sorted(n for n in swept if n not in claude_refused and n not in rows and n not in exempt)
        if loose:
            out.append(f"{len(loose)} swept name(s) neither refused, in a take row nor exempt with a reason: {loose[:6]}")
        if rt.LOGIN_VARIABLE[rt.CLAUDE_CODE] in refuse:
            out.append("the Claude row's own login is refused")
        for arm in (rt.CODEX, rt.CLAUDE_CODE, rt.GEMINI):
            missing = sorted(set(refuse) - set(rt.refused_variables(arm)))
            if missing:
                out.append(f"{arm}: the Claude sweep's names not refused: {missing[:5]}")
            in_row = sorted(set(rt.TAKE_ENV[arm]) & set(rt.refused_variables(arm)))
            if in_row:
                out.append(f"{arm}: its own row's names are refused: {in_row}")
        try:
            rt.check_environment(rt.CLAUDE_CODE, {"CLAUDE_CODE_USE_MANTLE": "1"})
            out.append("a set CLAUDE_CODE_USE_MANTLE does not refuse a Claude take")
        except rt.Refused:
            pass
        return out

    def test_the_claude_binary_sweep_is_refused(self):
        self.assertEqual(problems_of(self.check), [])

    def test_mutants(self):
        refuse = tuple(json.loads(open(_claude_files()[2], encoding="utf-8").read())["refuse_if_present"])
        self.assert_green_then_red(self.check, (
            ("a switch dropped", lambda: mock.patch.object(rt, "CLAUDE_BINARY_SWEEP_REFUSED",
                                                           tuple(n for n in refuse if n != "CLAUDE_CODE_USE_MANTLE"))),
            ("the sweep not in the refused set", lambda: mock.patch.dict(
                rt.VENDOR_BILLING_ROUTE_VARIABLES, {rt.CLAUDE_CODE: ()})),
            ("another binary", lambda: mock.patch.dict(rt.CLAUDE_BINARY, {"sha256": "0" * 64})),
            ("another image", lambda: mock.patch.dict(rt.CLAUDE_BINARY, {"image_id": "sha256:" + "0" * 64})),
            ("the gateway token reclassified", lambda: _patches(
                (rt, "CLAUDE_BINARY_SWEEP_REFUSED", tuple(n for n in refuse if n != "CLAUDE_CODE_GATEWAY_TOKEN")),
                (rt, "VENDOR_BILLING_ROUTE_VARIABLES", dict(
                    rt.VENDOR_BILLING_ROUTE_VARIABLES,
                    **{rt.CLAUDE_CODE: tuple(n for n in refuse if n != "CLAUDE_CODE_GATEWAY_TOKEN")})))),
            ("the session token exempted", lambda: mock.patch.object(
                json, "loads", _exempting(json.loads, "CLAUDE_CODE_MESSAGING_TOKEN"))),
            ("a pattern-matched name dropped", lambda: _patches(
                (rt, "VENDOR_BILLING_ROUTE_VARIABLES", dict(
                    rt.VENDOR_BILLING_ROUTE_VARIABLES,
                    **{rt.CLAUDE_CODE: tuple(n for n in refuse if n != "ANTHROPIC_SMALL_FAST_MODEL")})))),
        ))


class TestGeminiPackageSweep(MutantCase):
    """glitch-06's ruling (14 Oct 2026): the pinned Gemini CLI's environment-name sweep and its deterministic
    classification (committed under probes/) fill VENDOR_BILLING_ROUTE_VARIABLES[GEMINI]: every credential, route and
    ambiguous name is refused if present for every arm; GEMINI_API_KEY stays the Gemini arm's own login; no row's own
    name is refused; take_environment no longer waits on a PENDING Gemini entry."""

    def check(self):
        out = []
        sweep_path = os.path.join(SWEEP_DIR, "gemini-env-name-sweep-athena-20261014.json")
        class_path = os.path.join(SWEEP_DIR, "gemini-env-name-classification-20261014.json")
        with open(sweep_path, "rb") as fh:
            sweep_raw = fh.read()
        sweep = json.loads(sweep_raw)
        with open(class_path, encoding="utf-8") as fh:
            cls = json.load(fh)
        with open(os.path.join(os.path.dirname(rt.__file__), "gemini", "image.lock"), encoding="utf-8") as fh:
            pinned = json.load(fh)["harness"]["version"]
        if cls["sweep_sha256"] != hashlib.sha256(sweep_raw).hexdigest():
            out.append("the classification does not bind the committed sweep's bytes")
        if sweep["package_version"] != pinned or cls["package_version"] != pinned:
            out.append(f"the sweep is not of the pinned Gemini CLI {pinned}")
        if sweep["image"] != _lock_image("gemini"):
            out.append("the Gemini sweep is not of the pinned take-g image (box/gemini/image.lock image_id)")
        with open(class_path, "rb") as fh:
            class_raw = fh.read()
        if run_classifier("classify_gemini_env_names.py", sweep_path) != class_raw:
            out.append("the committed Gemini classification is not the classifier's output for the committed sweep")
        for n in ("WEB_HOST", "EDITOR_URL"):
            if n not in cls["refuse_if_present"]:
                out.append(f"{n} is not refused")
        if sorted(r["name"] for r in cls["rows"]) != sorted(sweep["names"]):
            out.append("the classification does not place every name the sweep found")
        refuse = set(cls["refuse_if_present"])
        if refuse != {r["name"] for r in cls["rows"] if r["class"] in ("credential", "route", "ambiguous")}:
            out.append("the refuse list is not every credential, route and ambiguous name")
        if tuple(rt.GEMINI_PACKAGE_SWEEP_REFUSED) != tuple(cls["refuse_if_present"]):
            out.append("run_take's Gemini sweep tuple drifted from the committed classification")
        entry = rt.VENDOR_BILLING_ROUTE_VARIABLES[rt.GEMINI]
        if rt._is_pending(entry) or set(entry) != refuse:
            out.append("VENDOR_BILLING_ROUTE_VARIABLES[gemini] is not the sweep's refuse list")
        for arm in (rt.CODEX, rt.CLAUDE_CODE, rt.GEMINI):
            missing = sorted(refuse - set(rt.refused_variables(arm)))
            if missing:
                out.append(f"{arm}: the Gemini sweep's names not refused: {missing[:5]}")
            in_row = sorted(set(rt.TAKE_ENV[arm]) & set(rt.refused_variables(arm)))
            if in_row:
                out.append(f"{arm}: its own row's names are refused: {in_row}")
        if "GEMINI_API_KEY" in rt.refused_variables(rt.GEMINI):
            out.append("GEMINI_API_KEY, the Gemini arm's own login, is refused for it")
        if "GEMINI_API_KEY" not in rt.refused_variables(rt.CLAUDE_CODE):
            out.append("GEMINI_API_KEY is not refused for another arm")
        try:
            rt.take_environment(rt.GEMINI, "/srv/w/t1/tree")
        except rt.NotReady as e:
            out.append(f"take_environment still waits for Gemini: {e}")
        return out

    def test_the_gemini_sweep_is_refused(self):
        self.assertEqual(problems_of(self.check), [])


class TestCodexExec(MutantCase):
    """glitch-06 (14 Oct 2026): run_take's Codex exec branch, behind the closed CODEX_SUBSCRIPTION_READY gate. A turn
    is the no-login launcher over the Codex row (CODEX_HOME the config mount, where place_lease put auth.json), running
    exactly the shapes the pinned 0.162.1 help shows for `codex exec` and `codex exec resume`, with the arm's pinned
    model; anything else refuses. The lease passed is place_lease's placement record, bound to the take's uid map, its
    folder checked in place after a TEST DATA grant (round 17 B3, host_view), never read."""

    MODEL = "gpt-6.1-sol"
    BYPASS = "--dangerously-bypass-approvals-and-sandbox"

    def lease(self, mode=0o600, folder_mode=0o700, name="auth.json", parent=None):
        """A TEST DATA lease placed by place_lease and bound to UID_MAP, its folder granted to the agent in
        self.grants (host_view, at folder_mode); a mode or a name other than the placed ones is the record's (round 17
        B3: after the grant the host reads the file's own facts from the placement record only)."""
        cfg = rt.make_config_dir(parent or tempfile.mkdtemp(prefix="w-"))
        with mock.patch.object(rt, "CODEX_SUBSCRIPTION_READY", True):
            placement = rt.place_lease(lease_src(), cfg)
        self.grants[cfg] = (AGENT_HOST_UID, folder_mode)
        lease = for_take(rt)(placement, UID_MAP)
        if not isinstance(lease, getattr(rt, "LeasePlacement", ())):
            return lease                               # before B3: the bare placed path
        kw = {"path": os.path.join(cfg, name)} if name != "auth.json" else {}
        if mode != 0o600:
            kw["mode"] = stat.S_IFREG | mode
        return dataclasses.replace(lease, **kw)

    def first(self, model=None):
        return ["codex", "exec", "--json", "-m", model or self.MODEL, self.BYPASS, "fix the failing check"]

    def exec_(self, inner, lf=None, run_tree="/srv/w/t1/tree", workdir="/srv/w/t1/tree", user=None, cid=None,
              caller=None):
        return rt.exec_argv(cid or ID["take"], inner, user=user or rt.AGENT_USER, workdir=workdir, harness=rt.CODEX,
                            run_tree=run_tree, login_file=lf or self.lease(), caller_env=caller or dict(CALLER))

    def refused(self, out, label, inner=None, lf=None, word=None, **kw):
        try:
            self.exec_(inner if inner is not None else self.first(), lf=lf, **kw)
            out.append(f"{label}: admitted")
        except rt.Refused as e:
            if word and word not in str(e):
                out.append(f"{label}: refused for another reason: {e}")
        except Exception as e:  # noqa: BLE001
            out.append(f"{label}: raised {type(e).__name__}, not Refused: {str(e)[:120]}")

    def check(self):
        out = []
        self.grants = {}
        if tuple(rt.CODEX_MODELS) != ("gpt-6.1-sol", "gpt-6-luna"):
            out.append(f"CODEX_MODELS is {rt.CODEX_MODELS!r}")
        if tuple(rt.CODEX_HELP_COMMANDS) != ("resume", "fork", "review", "help"):
            out.append(f"CODEX_HELP_COMMANDS is {rt.CODEX_HELP_COMMANDS!r}")
        # the review of 1e10e320, MINOR 3 and NIT 5: the box's turn rules and the adapter's argv agree
        import codex_adapter
        if rt._CODEX_SESSION.pattern != codex_adapter._THREAD_ID.pattern:
            out.append("run_take's session-id form is not codex_adapter's thread-id form")
        if (rt.CODEX_BYPASS_FLAG,) != tuple(codex_adapter.MODE_FLAGS["bypass"]):
            out.append("run_take's bypass flag is not codex_adapter's bypass mode flags")
        with open(os.path.join(HERE, "prereg-draft.json"), encoding="utf-8") as fh:
            if tuple(json.load(fh)["models"]["O"]) != tuple(rt.CODEX_MODELS):
                out.append("CODEX_MODELS is not prereg-draft.json's arm O models")
        # the closed gate: NotReady before anything is checked or read (a bad lease, user or turn never shows first);
        # pinned closed here (B8-1), since the committed gate is open
        with mock.patch.dict(os.environ, {}, clear=True), filled(), \
                mock.patch.object(rt, "CODEX_SUBSCRIPTION_READY", False):
            for label, kw in (("a good turn", {}), ("a bad lease", {"lf": self.lease(name="lease.json")}),
                              ("another user", {"user": "0:0"}), ("a bad turn", {"inner": ["codex", "review"]})):
                try:
                    self.exec_(kw.pop("inner", self.first()), **kw)
                    out.append(f"the closed gate built a Codex exec ({label})")
                except rt.NotReady as e:
                    if str(e) != rt.CODEX_SUBSCRIPTION_NOT_READY:
                        out.append(f"the closed gate refused with another message ({label}): {e}")
                except Exception as e:  # noqa: BLE001
                    out.append(f"the closed gate let {label} through to {type(e).__name__}")
        with mock.patch.dict(os.environ, {}, clear=True), filled(), host_view(self.grants), \
                mock.patch.object(rt, "CODEX_SUBSCRIPTION_READY", True):
            for inner in (self.first(), self.first("gpt-6-luna"),
                          ["codex", "exec", "--json", "-m", self.MODEL, self.BYPASS, "resume",
                           "019a2b3c-4d5e-6f70-8192-a3b4c5d6e7f8", "next step"],
                          ["codex", "exec", self.BYPASS, "--model", self.MODEL, "--json", "go on"]):
                try:
                    argv, env = self.exec_(inner)
                except Exception as e:  # noqa: BLE001
                    out.append(f"{inner[2:6]}: not built: {type(e).__name__}: {str(e)[:120]}")
                    continue
                vals = rt.exec_values(rt.CODEX, "/srv/w/t1/tree")
                pairs = [f"{k}={vals[k]}" for k in sorted(vals)]
                want = [rt.RUNTIME_CLIENT, "exec", "--user", rt.AGENT_USER, "--workdir", "/srv/w/t1/tree",
                        ID["take"], *rt.LAUNCHER, rt.NO_LOGIN, str(len(pairs)), *pairs, *inner]
                if argv != want:
                    out.append(f"the Codex argv is off for {inner[2:6]}")
                if vals.get("CODEX_HOME") != rt.CONFIG_MOUNT:
                    out.append("CODEX_HOME is not the config mount")
                if env != rt.runtime_env(dict(CALLER)):
                    out.append("the Codex client environment is not the runtime's needs alone")
                if any(n in env for n in ("CODEX_API_KEY", "OPENAI_API_KEY", "-")):
                    out.append("a credential name rides the Codex client environment")
            # the turn shapes the pinned help does not show, or the study never uses, each refused
            B = ["codex", "exec"]
            for label, inner, word in (
                    ("a config override", B + ["-c", "model=\"o3\"", "--json", "-m", self.MODEL, self.BYPASS, "x"], None),
                    ("the open-source provider", B + ["--oss", "--json", "-m", self.MODEL, self.BYPASS, "x"], None),
                    ("a profile", B + ["-p", "p", "--json", "-m", self.MODEL, self.BYPASS, "x"], None),
                    ("a feature switch", B + ["--enable", "f", "--json", "-m", self.MODEL, self.BYPASS, "x"], None),
                    ("another writable dir", B + ["--add-dir", "/x", "--json", "-m", self.MODEL, self.BYPASS, "x"], None),
                    ("another working root", B + ["-C", "/x", "--json", "-m", self.MODEL, self.BYPASS, "x"], None),
                    ("the user config ignored", B + ["--ignore-user-config", "--json", "-m", self.MODEL, self.BYPASS,
                                                     "x"], None),
                    ("a sandbox mode", B + ["-s", "read-only", "--json", "-m", self.MODEL, self.BYPASS, "x"], None),
                    ("an output file", B + ["-o", "/x", "--json", "-m", self.MODEL, self.BYPASS, "x"], None),
                    ("an ephemeral session", B + ["--ephemeral", "--json", "-m", self.MODEL, self.BYPASS, "x"], None),
                    ("the model glued by =", B + ["--json", "--model=" + self.MODEL, self.BYPASS, "x"], None),
                    ("no --json", B + ["-m", self.MODEL, self.BYPASS, "x"], "--json"),
                    ("no model", B + ["--json", self.BYPASS, "x"], "model"),
                    ("no bypass", B + ["--json", "-m", self.MODEL, "x"], "bypass"),
                    ("the model twice", B + ["--json", "-m", self.MODEL, "-m", self.MODEL, self.BYPASS, "x"], "once"),
                    ("--json twice", B + ["--json", "--json", "-m", self.MODEL, self.BYPASS, "x"], "once"),
                    ("an unpinned model", self.first("o3"), "pinned"),
                    ("another client", ["claude", "exec", "--json", "-m", self.MODEL, self.BYPASS, "x"], "codex"),
                    ("an absolute client path", ["/usr/local/bin/codex"] + self.first()[1:], "codex"),
                    ("another subcommand", ["codex", "review", "--json", "-m", self.MODEL, self.BYPASS, "x"], "exec"),
                    ("a prompt that reads as a flag", B + ["--json", "-m", self.MODEL, self.BYPASS, "-x"], None),
                    ("the prompt from stdin", B + ["--json", "-m", self.MODEL, self.BYPASS, "-"], None),
                    ("no prompt", B + ["--json", "-m", self.MODEL, self.BYPASS], "prompt"),
                    ("two prompts", B + ["--json", "-m", self.MODEL, self.BYPASS, "x", "y"], "prompt"),
                    ("resume --last", B + ["--json", "-m", self.MODEL, self.BYPASS, "resume", "--last", "x"], None),
                    ("resume without a prompt", B + ["--json", "-m", self.MODEL, self.BYPASS, "resume", "abc-1"],
                     "prompt"),
                    ("a session id off the form", B + ["--json", "-m", self.MODEL, self.BYPASS, "resume", "a b", "x"],
                     "session"),
                    ("an option after resume", B + ["--json", "-m", self.MODEL, self.BYPASS, "resume", "-m", "o3",
                                                    "abc-1", "x"], None),
                    ("fork", B + ["--json", "-m", self.MODEL, self.BYPASS, "fork", "abc-1", "x"], None),
                    ("-m with no model", B + ["--json", self.BYPASS, "x", "-m"], None),
                    ("-m before the prompt with no model", B + ["--json", self.BYPASS, "-m"], "takes the model"),
                    # the review of 1e10e320, MAJOR: a one-word prompt that is one of the pinned help's subcommands
                    # would be run as that subcommand (`codex exec [OPTIONS] <COMMAND> [ARGS]`)
                    ("`review` as the only prompt", B + ["--json", "-m", self.MODEL, self.BYPASS, "review"],
                     "subcommand"),
                    ("`help` as the only prompt", B + ["--json", "-m", self.MODEL, self.BYPASS, "help"], "subcommand"),
                    ("`fork` as the only prompt", B + ["--json", "-m", self.MODEL, self.BYPASS, "fork"], "subcommand"),
                    ("`resume` as the only prompt", B + ["--json", "-m", self.MODEL, self.BYPASS, "resume"], None),
                    ("-m taking the next flag as its model", B + ["-m", "--json", self.BYPASS, "x"],
                     "takes the model"),
                    ("a resumed prompt that reads as a flag",
                     B + ["--json", "-m", self.MODEL, self.BYPASS, "resume", "abc-1", "-x"], "never starts with '-'"),
                    ("a resumed prompt from stdin",
                     B + ["--json", "-m", self.MODEL, self.BYPASS, "resume", "abc-1", "-"], "never starts with '-'")):
                self.refused(out, label, inner=inner, word=word)
            try:                                       # not a list of strings: refused before any shape is read
                self.exec_(B + ["--json", "-m", self.MODEL, self.BYPASS, 5])
                out.append("a non-string turn argument was admitted")
            except TypeError:
                pass
            # the exec's own frame
            for label, kw, word in (("another user", {"user": "0:0"}, "agent"),
                                    ("a container id off the form", {"cid": "not-an-id"}, None),
                                    ("a relative workdir", {"workdir": "srv/w"}, "workdir"),
                                    ("an API key in the caller's environment",
                                     {"caller": dict(CALLER, OPENAI_API_KEY=FAKE_VALUE)}, "OPENAI_API_KEY"),
                                    ("a broker-snapshot name in the caller's environment",
                                     {"caller": dict(CALLER, CODEX_NETWORK_PROXY_SNAPSHOT_BROKERED_VALUE_X="1")},
                                     "BROKERED_VALUE_X")):
                self.refused(out, label, word=word, **kw)
            # the lease: its folder checked in place after the grant, its file's facts from the placement record
            run_tree = tempfile.mkdtemp(prefix="w-")
            good = self.lease()
            rec = isinstance(good, getattr(rt, "LeasePlacement", ()))
            link = dataclasses.replace(good, mode=stat.S_IFLNK | 0o600) if rec else good
            two = dataclasses.replace(good, nlink=2) if rec else good
            for label, lf, word, kw in (
                    ("a lease file of another name", self.lease(name="lease.json"), "auth.json", {}),
                    ("a lease at mode 644", self.lease(mode=0o644), "600", {}),
                    ("a lease folder at mode 755", self.lease(folder_mode=0o755), "700", {}),
                    ("a link as the lease", link, "regular file", {}),
                    ("a lease with two links", two, "one link", {}),
                    ("a lease inside the run tree", self.lease(parent=run_tree), "run tree", {"run_tree": run_tree})):
                self.refused(out, label, lf=lf, word=word, **kw)
            other = self.lease()
            with mock.patch.object(rt.os, "getuid", lambda me=os.getuid(): me + 1):
                self.refused(out, "a lease of another owner", lf=other, word="owned")
            repo = tempfile.mkdtemp(prefix="w-")
            os.mkdir(os.path.join(repo, ".git"))
            in_repo = os.path.join(repo, "cfg")
            os.mkdir(in_repo, 0o700)
            self.grants[in_repo] = (AGENT_HOST_UID, 0o700)
            ist = os.lstat(in_repo)
            in_repo_lease = dataclasses.replace(good, path=os.path.join(in_repo, "auth.json"), folder_dev=ist.st_dev,
                                                folder_ino=ist.st_ino, dev=ist.st_dev) if rec else good
            self.refused(out, "a lease inside a repository", lf=in_repo_lease, word="repository")
            with mock.patch.object(rt, "read_login", side_effect=AssertionError("read")), \
                    mock.patch("builtins.open", side_effect=AssertionError("a file was opened")):
                try:
                    self.exec_(self.first(), lf=good)
                except AssertionError as e:
                    out.append(f"the Codex exec read a file: {e}")
        return out

    def test_codex_exec(self):
        self.assertEqual(problems_of(self.check), [])


# ------------------------------------------- the placed lease after the grant (lane vendor-admission round 17, B3)
# glitch-b5's ruling (a), Sun 18 Oct 2026: after the grant the config folder is mode 700 and owned by the agent's mapped
# host uid, so the host user cannot stat anything inside it (measured on athena: lane-reports/live-box-2026-10-13.md,
# postflight reads "unreadable: ."). The host checks only what it can read: the folder by lstat (the folder
# place_lease wrote into, by device and inode; never a link; mode 700; owned by the agent's host uid, derived from the
# take's uid map) and the path (exactly that folder's auth.json). The file's own facts are place_lease's read-back,
# carried in its placement record; a missing or mismatched record refuses.
AGENT_HOST_UID = 110000          # TEST DATA: container uid 10001 through UID_MAP, athena's measured shape


@contextlib.contextmanager
def host_view(grants: dict):
    """A TEST DATA grant as the host user sees it: for each folder in `grants` ({folder: (owner, mode)}, read live),
    its lstat shows that owner and mode, and every path beneath it raises PermissionError on lstat and open, so
    nothing inside can be stat'd or read host-side. Every other path is the real one."""
    real_lstat, real_open = os.lstat, os.open

    def under(p):
        p = os.path.normpath(os.fspath(p))
        return next((f for f in list(grants) if p.startswith(f + os.sep)), None)

    def lstat(p, *a, **k):
        if under(p):
            raise PermissionError(13, "Permission denied", os.fspath(p))
        st = real_lstat(p, *a, **k)
        got = grants.get(os.path.normpath(os.fspath(p)))
        if got is None:
            return st
        f = list(st)
        f[0], f[4] = stat.S_IFDIR | got[1], got[0]
        return os.stat_result(f)

    def open_(p, *a, **k):
        if under(p):
            raise PermissionError(13, "Permission denied", os.fspath(p))
        return real_open(p, *a, **k)
    with mock.patch.object(rt.os, "lstat", lstat), mock.patch.object(rt.os, "open", open_):
        yield


def lease_src(body=b'{"tokens": {}}\n') -> str:
    """A TEST DATA lease source, mode 600 in a mode 700 folder of its own, outside every repository."""
    d = tempfile.mkdtemp(prefix="lease-src-")
    os.chmod(d, 0o700)
    p = os.path.join(d, "auth.json")
    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.write(fd, body)
    os.close(fd)
    return p


def for_take(m):
    """m.lease_for_take, the placement record bound to the take's uid map; absent before B3, where the road handed
    _codex_exec_argv the bare placed path, today's road."""
    return getattr(m, "lease_for_take", lambda placement, uid_map: placement)


class TestPlacedLeaseAfterGrant(MutantCase):
    """Round 17 B3: _codex_exec_argv on a lease place_lease placed, after a TEST DATA grant that makes the file
    unreadable host-side, builds the turn; every way the record or the folder can be wrong refuses by name, and the
    exec reads no file."""

    MODEL = "gpt-6.1-sol"
    FIRST = ["codex", "exec", "--json", "-m", "gpt-6.1-sol", "--dangerously-bypass-approvals-and-sandbox", "go on"]

    def place(self, m, parent=None):
        """(the config folder, place_lease's placement) for a fresh TEST DATA lease, the gate open for the copy."""
        cfg = m.make_config_dir(parent or tempfile.mkdtemp(prefix="w-"))
        with mock.patch.object(m, "CODEX_SUBSCRIPTION_READY", True):
            return cfg, m.place_lease(lease_src(), cfg)

    def exec_(self, m, lease, run_tree="/srv/w/t1/tree"):
        with mock.patch.object(m, "CODEX_SUBSCRIPTION_READY", True), \
                mock.patch.object(m, "VENDOR_BILLING_ROUTE_VARIABLES", {m.CODEX: (), m.GEMINI: ()}), \
                mock.patch.dict(os.environ, {}, clear=True):
            return m.exec_argv(ID["take"], list(self.FIRST), user=m.AGENT_USER, workdir="/srv/w/t1/tree",
                               harness=m.CODEX, run_tree=run_tree, login_file=lease, caller_env=dict(CALLER))

    def refused(self, out, m, label, lease, word, grants, run_tree="/srv/w/t1/tree"):
        try:
            with host_view(grants):
                self.exec_(m, lease, run_tree=run_tree)
            out.append(f"{label}: admitted")
        except m.Refused as e:
            if word not in str(e):
                out.append(f"{label}: refused for another reason: {e}")
        except Exception as e:  # noqa: BLE001 - any other exception is a crash, not a refusal
            out.append(f"{label}: raised {type(e).__name__}, not a refusal: {str(e)[:160]}")

    def check(self, m=None):
        m = m or rt
        out = []
        cfg, placement = self.place(m)
        if not isinstance(placement, getattr(m, "LeasePlacement", ())):
            out.append(f"place_lease returned no placement record: {type(placement).__name__}")
        path = getattr(placement, "path", placement)
        if path != os.path.join(cfg, "auth.json"):
            out.append(f"the placement names {path!r}, not the config folder's auth.json")
        lease = for_take(m)(placement, UID_MAP)
        grants = {cfg: (AGENT_HOST_UID, 0o700)}
        with host_view(grants):
            try:
                os.lstat(path)
                out.append("the TEST DATA grant left the placed file readable host-side")
            except PermissionError:
                pass
            try:
                with mock.patch.object(m, "read_login", side_effect=AssertionError("read_login")), \
                        mock.patch("builtins.open", side_effect=AssertionError("a file was opened")):
                    argv, env = self.exec_(m, lease)
                vals = m.exec_values(m.CODEX, "/srv/w/t1/tree")
                pairs = [f"{k}={vals[k]}" for k in sorted(vals)]
                want = [m.RUNTIME_CLIENT, "exec", "--user", m.AGENT_USER, "--workdir", "/srv/w/t1/tree", ID["take"],
                        *m.LAUNCHER, m.NO_LOGIN, str(len(pairs)), *pairs, *self.FIRST]
                if argv != want or env != m.runtime_env(dict(CALLER)):
                    out.append("the Codex exec on the placed lease is not the no-login launcher over the row")
            except Exception as e:  # noqa: BLE001 - reported: the road refuses what it must admit
                out.append(f"a placed lease after the grant was refused: {type(e).__name__}: {str(e)[:200]}")
        if not isinstance(placement, getattr(m, "LeasePlacement", ())):
            return out
        rep = dataclasses.replace
        # the record: missing, unbound, or not place_lease's read-back of a lease it could place
        self.refused(out, m, "the bare path, no placement record", path, "placement record", grants)
        self.refused(out, m, "a record not bound to the take's uid map", placement, "uid map", grants)
        for label, kw, word in (
                ("a record of another file name", {"path": os.path.join(cfg, "lease.json")}, "auth.json"),
                ("a record of a relative path", {"path": "cfg/auth.json"}, "absolute"),
                ("a record of a path not normalised", {"path": cfg + "/./auth.json"}, "absolute"),
                ("a record of a file at mode 644", {"mode": stat.S_IFREG | 0o644}, "600"),
                ("a record of a link", {"mode": stat.S_IFLNK | 0o600}, "regular file"),
                ("a record of a file with two links", {"nlink": 2}, "one link"),
                ("a record of a file another user owned", {"uid": os.getuid() + 1}, "owned by the reading user"),
                ("a record of an empty file", {"size": 0}, "size"),
                ("a record of an oversize file", {"size": m.LEASE_MAX_BYTES + 1}, "size"),
                ("a record of another folder inode", {"folder_ino": lease.folder_ino + 1}, "wrote into"),
                ("a record of another folder device", {"folder_dev": lease.folder_dev + 1}, "wrote into"),
                ("a record of a file on another device", {"dev": lease.dev + 1}, "wrote into")):
            self.refused(out, m, label, rep(lease, **kw), word, grants)
        for label, uid_map in (("a uid map that does not map the agent", ((0, 1000, 1),)),
                               ("a uid map that maps the agent twice", UID_MAP + ((10001, 200000, 1),)),
                               ("an empty uid map", ()), ("a uid map of another shape", ((0, 1000),))):
            try:
                self.refused(out, m, f"{label} (bound)", for_take(m)(placement, uid_map), "mapped", grants)
            except m.Refused:
                pass
        # the folder, as the host reads it after the grant
        for label, grant, word in (("the folder owned by another uid", (AGENT_HOST_UID + 1, 0o700), "agent"),
                                   ("the folder still the host user's (no grant)", (os.getuid(), 0o700), "agent"),
                                   ("the folder at mode 755", (AGENT_HOST_UID, 0o755), "mode 700"),
                                   ("the folder at mode 770", (AGENT_HOST_UID, 0o770), "mode 700")):
            c, p = self.place(m)
            self.refused(out, m, label, for_take(m)(p, UID_MAP), word, {c: grant})
        c, p = self.place(m)                            # the folder replaced after placement: another inode
        os.rename(c, c + ".placed")
        os.mkdir(c, 0o700)
        self.refused(out, m, "the folder replaced after placement", for_take(m)(p, UID_MAP), "wrote into",
                     {c: (AGENT_HOST_UID, 0o700)})
        c, p = self.place(m)                            # the path reached through a linked folder
        os.symlink(c, c + "-link")
        self.refused(out, m, "the lease reached through a linked folder",
                     rep(for_take(m)(p, UID_MAP), path=os.path.join(c + "-link", "auth.json")), "never a link",
                     {c: (AGENT_HOST_UID, 0o700)})
        tree = tempfile.mkdtemp(prefix="w-")            # the lease inside the run tree
        c, p = self.place(m, parent=tree)
        self.refused(out, m, "the lease inside the run tree", for_take(m)(p, UID_MAP), "run tree",
                     {c: (AGENT_HOST_UID, 0o700)}, run_tree=tree)
        repo = tempfile.mkdtemp(prefix="w-")            # the lease's folder inside a repository
        os.mkdir(os.path.join(repo, ".git"))
        rc = os.path.join(repo, "cfg")
        os.mkdir(rc, 0o700)
        rst = os.lstat(rc)
        self.refused(out, m, "the lease inside a repository",
                     rep(lease, path=os.path.join(rc, "auth.json"), folder_dev=rst.st_dev, folder_ino=rst.st_ino,
                         dev=rst.st_dev), "repository", {rc: (AGENT_HOST_UID, 0o700)})
        with mock.patch.object(m, "CODEX_SUBSCRIPTION_READY", False):   # the closed gate still refuses first
            try:
                with host_view(grants):
                    m.exec_argv(ID["take"], list(self.FIRST), user=m.AGENT_USER, workdir="/srv/w/t1/tree",
                                harness=m.CODEX, run_tree="/srv/w/t1/tree", login_file=lease,
                                caller_env=dict(CALLER))
                out.append("the closed gate built a Codex exec on a placed lease")
            except m.NotReady:
                pass
        return out

    def test_the_placed_lease_after_the_grant(self):
        self.assertEqual(problems_of(self.check), [])

    def test_mutants(self):
        with open(rt.__file__, encoding="utf-8") as fh:
            src = fh.read()

        def variant(old, new):
            def ctx():
                if src.count(old) != 1:
                    raise AssertionError(f"the mutant's anchor is not in run_take.py exactly once: {old!r}")
                m = _run_take_variant(src.replace(old, new))
                return mock.patch.object(self, "check", lambda m=m, real=self.check: real(m))
            return ctx
        self.assert_green_then_red(lambda: self.check(), (
            ("the folder's inode unchecked",
             variant("    if (fst.st_dev, fst.st_ino) != (lease.folder_dev, lease.folder_ino):",
                     "    if False:")),
            ("the owner check accepting any uid", variant("    if fst.st_uid != agent:", "    if False:")),
            ("the owner still the host uid (the old bug)",
             variant("    if fst.st_uid != agent:", "    if fst.st_uid != os.getuid():")),
            ("the folder mode unchecked", variant("    if stat.S_IMODE(fst.st_mode) != 0o700:", "    if False:")),
            ("the placement record not required",
             variant("    if not isinstance(lease, LeasePlacement):\n        raise",
                     "    if not isinstance(lease, LeasePlacement):\n        return\n        raise")),
            ("the record's link count unchecked", variant("    if lease.nlink != 1:", "    if False:")),
        ))


class TestCodexRow(MutantCase):
    """glitch-06's ruling 1 (14 Oct 2026): no API-key route for Codex, ever. TAKE_ENV[CODEX] carries no credential;
    LOGIN_VARIABLE[CODEX] is NO_LOGIN (the lease road); every road that expects an environment login refuses a Codex
    row explicitly; CODEX_API_KEY and OPENAI_API_KEY are refused for a Codex take, by name, never by value. Ruling 3:
    VENDOR_BILLING_ROUTE_VARIABLES[CODEX] is named from the pinned version's evidence, refused if present."""

    PLANT = "FAKE-api-0123456789abcdef-PLANTED"

    def check(self):
        out = []
        row = rt.TAKE_ENV[rt.CODEX]
        if "CODEX_API_KEY" in row or rt.CREDENTIAL in row.values():
            out.append("the Codex row still carries an environment credential")
        if rt.LOGIN_VARIABLE[rt.CODEX] != rt.NO_LOGIN:
            out.append(f"LOGIN_VARIABLE[codex] is {rt.LOGIN_VARIABLE[rt.CODEX]!r}, not NO_LOGIN")
        if rt.LOGIN_VARIABLE[rt.CLAUDE_CODE] != "CLAUDE_CODE_OAUTH_TOKEN" or \
                rt.LOGIN_VARIABLE[rt.GEMINI] != "GEMINI_API_KEY":
            out.append("another arm's login variable moved")
        refused = rt.refused_variables(rt.CODEX)
        for name in ("CODEX_API_KEY", "OPENAI_API_KEY") + CODEX_ROUTE_NAMED + CODEX_ROUTE_DOCS_READ:
            if name not in refused:
                out.append(f"{name} is not refused for a Codex take")
            with mock.patch.dict(os.environ, {}, clear=True):
                try:
                    rt.check_environment(rt.CODEX, {"PATH": "/bin", name: self.PLANT})
                    out.append(f"a Codex take admitted {name} in the caller's environment")
                except rt.Refused as e:
                    if name not in str(e) or "PLANTED" in str(e):
                        out.append(f"{name}: the refusal does not name it, or carries the value: {e}")
        got_route = tuple(rt.VENDOR_BILLING_ROUTE_VARIABLES[rt.CODEX])
        if got_route[:len(CODEX_ROUTE_NAMED + CODEX_ROUTE_DOCS_READ)] != CODEX_ROUTE_NAMED + CODEX_ROUTE_DOCS_READ or \
                set(got_route) != set(CODEX_ROUTE_NAMED + CODEX_ROUTE_DOCS_READ) | set(sweep_refused()):
            out.append(f"VENDOR_BILLING_ROUTE_VARIABLES[codex] is {rt.VENDOR_BILLING_ROUTE_VARIABLES[rt.CODEX]!r}")
        for name in CODEX_ROUTE_NAMED + CODEX_ROUTE_DOCS_READ:     # refuse-if-present for every arm, like the others'
            if name not in rt.refused_variables(rt.CLAUDE_CODE):
                out.append(f"{name} is not refused for a Claude Code take")
        # a road that expects an environment login refuses a Codex row explicitly, never by KeyError
        d = tempfile.mkdtemp(prefix="w-")
        p = os.path.join(d, "login")
        fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.write(fd, b"-=" + self.PLANT.encode() + b"\n")
        os.close(fd)
        try:
            rt.read_login(p, rt.NO_LOGIN)
            out.append("read_login read a Codex environment login")
        except rt.LoginRefused as e:
            if "no environment login" not in str(e) or "PLANTED" in str(e):
                out.append(f"read_login refused a Codex row without naming the rule: {e}")
        except Exception as e:  # noqa: BLE001
            out.append(f"read_login crashed on a Codex row: {type(e).__name__}")
        try:
            with mock.patch.object(rt, "CODEX_SUBSCRIPTION_READY", False):   # the closed gate, pinned (B8-1)
                rt.exec_argv("a" * 64, ["codex", "exec"], user=rt.AGENT_USER, workdir="/", harness=rt.CODEX,
                             run_tree=d, login_file=p, caller_env={"PATH": "/bin"})
            out.append("exec_argv admitted a Codex row")
        except rt.NotReady:
            pass
        except Exception as e:  # noqa: BLE001
            out.append(f"exec_argv refused a Codex row with {type(e).__name__}, not NotReady")
        return out

    def test_codex_row(self):
        self.assertEqual(problems_of(self.check), [])


class TestReviewFolds41428177(MutantCase):
    """The review of 41428177 and 9d4bfd40 (glitch-06, 14 Oct 2026). MINOR 1: launcher_argv's harness= is required and
    the login must be LOGIN_VARIABLE[harness], so a named key for Codex refuses even with the gate open. MINOR 2: the
    no-login launcher reads the values, not only the harness= claim: exactly the Codex row's names, and no other
    harness's config home. NIT 6: the module refuses to load when the Codex row names a key, API-key or subscription
    token variable."""

    def check(self):
        out = []
        import inspect
        if inspect.signature(rt.launcher_argv).parameters["harness"].default is not inspect.Parameter.empty:
            out.append("launcher_argv's harness= has a default")
        codex_values = rt.exec_values(rt.CODEX, "/srv/w/t1/tree")
        with mock.patch.object(rt, "CODEX_SUBSCRIPTION_READY", True):
            for login in ("CODEX_API_KEY", "OPENAI_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN"):
                try:
                    rt.launcher_argv(login, codex_values, ["codex", "exec"], harness=rt.CODEX)
                    out.append(f"a Codex launcher reading {login} was built with the gate open")
                except rt.Refused as e:
                    if "not the login of" not in str(e):
                        out.append(f"{login}: refused for another reason: {e}")
            try:
                rt.launcher_argv("GEMINI_API_KEY", {"A": "1"}, ["claude"], harness=rt.CLAUDE_CODE)
                out.append("a Claude Code launcher reading Gemini's login was built")
            except rt.Refused as e:
                if "not the login of" not in str(e):
                    out.append(f"cross-arm login refused for another reason: {e}")
            got = rt.launcher_argv(rt.NO_LOGIN, codex_values, ["codex", "exec"], harness=rt.CODEX)
            if got[:len(rt.LAUNCHER) + 1] != [*rt.LAUNCHER, "-"]:
                out.append("the no-login launcher over the Codex row's values was not built")
            for label, values, word in (
                    ("Gemini's config home", dict(codex_values, GEMINI_CLI_HOME=rt.CONFIG_MOUNT), "config home"),
                    ("Claude Code's config home", dict(codex_values, CLAUDE_CONFIG_DIR=rt.CONFIG_MOUNT),
                     "config home"),
                    ("an extra name", dict(codex_values, EXTRA_NAME="1"), "exactly the Codex row's names"),
                    ("a missing name", {k: v for k, v in codex_values.items() if k != "CODEX_HOME"},
                     "exactly the Codex row's names")):
                try:
                    rt.launcher_argv(rt.NO_LOGIN, values, ["codex", "exec"], harness=rt.CODEX)
                    out.append(f"the no-login launcher was built with {label}")
                except rt.Refused as e:
                    if word not in str(e):
                        out.append(f"{label}: refused for another reason: {e}")
        # NIT 6: the module itself refuses a Codex row that names a key, API-key or subscription-token variable
        src = open(rt.__file__, encoding="utf-8").read()
        anchor = '"CODEX_HOME": CONFIG_MOUNT},'
        if src.count(anchor) != 1:
            out.append("the Codex row's anchor is not in the module once")
        for name in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN"):
            import types
            probe = types.ModuleType("rt_probe")
            probe.__file__ = rt.__file__
            try:
                with mock.patch.dict(sys.modules, {"rt_probe": probe}):   # dataclasses read the module back
                    exec(compile(src.replace(anchor, f'"CODEX_HOME": CONFIG_MOUNT, "{name}": "1"}},'), rt.__file__,
                                 "exec"), probe.__dict__)
                out.append(f"the module loaded with {name} in the Codex row")
            except RuntimeError as e:
                if name not in str(e):
                    out.append(f"{name}: the load refusal does not name it: {e}")
        return out

    def test_review_folds(self):
        self.assertEqual(problems_of(self.check), [])


def stat_reg(st) -> bool:
    import stat as _stat
    return _stat.S_ISREG(st.st_mode)


# ------------------------------------------------------------------------------- PENDING and neutral names
class TestPendingAndNames(MutantCase):
    # TOP_FORMAT and INSPECT_STATUS FILLED 14 Oct 2026 (stub-take review PASS); FALLBACK_ENV FILLED the same day from
    # the docs (glitch-06's ruling, Addendum D).
    # CLAUDE_BYPASS_KEY RULED not required in -p (glitch-06, 14 Oct 2026; CLAUDE_BYPASS_RULING).
    # VENDOR_BILLING_ROUTE_VARIABLES FILLED 14 Oct 2026: Codex from its binary's sweep, Gemini from its package's.
    EXPECT = {"TakeSpec.resources"}
    FILLED_TOP = {"ps_options": ["-eo", "pid,uid,comm"], "pid_column": "PID", "uid_column": "UID",
                  "uid_namespace": "container"}
    # "XDG_RUNTIME_DIR in the take" RETIRED 14 Oct 2026 (glitch-06): measured not needed (test_xdg_runtime_dir_*).
    CALLER_EXPECT = {"cgroup_dir", "uid_map", "tree ownership"}
    # The retirement's evidence: two stub takes on athena, by sha256 (run 1 raw, run 6 derived).
    XDG_EVIDENCE = (("stub-take-run1.json", "67a0698a2e1037fdf5a1c02caea67a1281a5f31c4bc8629adfbb476f07dd83f4"),
                    ("stub-take-run6.derived.json", "8a56240db70d38a74fbd5d50c836683134259c4617a22800dcd3e6669b63641e"))

    def check_pending(self):
        out = []
        if set(rt.pending()) != self.EXPECT:
            out.append(f"pending() = {sorted(rt.pending())}")
        if set(rt.CALLER_PENDING) != self.CALLER_EXPECT:
            out.append(f"CALLER_PENDING = {sorted(rt.CALLER_PENDING)}")
        if not all(rt.PENDING_WHY.get(k) for k in self.EXPECT):
            out.append("a pending value has no reason")
        if rt.TOP_FORMAT != self.FILLED_TOP:
            out.append(f"TOP_FORMAT is not the measured form: {rt.TOP_FORMAT!r}")
        st = rt.INSPECT_STATUS
        if not (isinstance(st, dict) and st.get("engine") == "29.8.1" and st.get("api_version") == "1.56"
                and len(st.get("evidence", ())) == 2 and not rt._is_pending(st)):
            out.append(f"INSPECT_STATUS is not the confirmed record: {st!r}")
        # CP5 review (f5c17498): each evidence file INSPECT_STATUS names hashes to the sha256 it records.
        repo = os.path.dirname(os.path.dirname(HERE))
        for rel, digest in (st.get("evidence", ()) if isinstance(st, dict) else ()):
            try:
                with open(os.path.join(repo, rel), "rb") as fh:
                    got = hashlib.sha256(fh.read()).hexdigest()
            except OSError:
                got = None
            if got != digest:
                out.append(f"INSPECT_STATUS evidence {rel} does not hash to its recorded sha256")
        if "policy" not in rt.PENDING_WHY["TakeSpec.resources"].lower():
            out.append("the resources' reason does not say they are capacity policy")
        return out

    def check_xdg_retired(self):
        """Row 4 retired on evidence: every agent exec in the two stub takes ran with no XDG_RUNTIME_DIR and returned
        0, `claude --version` included; the take's environment row sets none; and CALLER_PENDING no longer lists it."""
        out = []
        if "XDG_RUNTIME_DIR in the take" in rt.CALLER_PENDING:
            out.append("CALLER_PENDING still lists XDG_RUNTIME_DIR in the take")
        if any("XDG_RUNTIME_DIR" in row for row in rt.TAKE_ENV.values()):
            out.append("a take's environment row sets XDG_RUNTIME_DIR")
        runs = os.path.join(os.path.dirname(os.path.dirname(HERE)), "lane-reports", "stub-take-20261014")
        for name, digest in self.XDG_EVIDENCE:
            with open(os.path.join(runs, name), "rb") as fh:
                raw = fh.read()
            if hashlib.sha256(raw).hexdigest() != digest:
                out.append(f"{name} does not hash to its recorded sha256")
                continue
            execs = [c for c in json.loads(raw)["calls"] if c.get("argv", [])[:2] == ["docker", "exec"]
                     and rt.AGENT_USER in c["argv"]]
            if len(execs) < 10 or not any("claude" in c["argv"] for c in execs):
                out.append(f"{name}: too few agent execs to stand as evidence ({len(execs)})")
            if [c for c in execs if c.get("returncode") != 0 or any("XDG_RUNTIME_DIR" in a for a in c["argv"])]:
                out.append(f"{name}: an agent exec failed or carried XDG_RUNTIME_DIR")
        return out

    def test_xdg_runtime_dir_retired_on_evidence(self):
        self.assert_green_then_red(self.check_xdg_retired, [
            ("row-kept", patched(rt, "CALLER_PENDING", dict(rt.CALLER_PENDING, **{
                "XDG_RUNTIME_DIR in the take": "measured at the stub take."}))),
            ("take-env-sets-it", patched(rt, "TAKE_ENV", dict(rt.TAKE_ENV, **{rt.CLAUDE_CODE: dict(
                rt.TAKE_ENV[rt.CLAUDE_CODE], XDG_RUNTIME_DIR="/run/user/10001")}))),
            ("evidence-swapped", patched(type(self), "XDG_EVIDENCE", (
                (self.XDG_EVIDENCE[0][0], self.XDG_EVIDENCE[1][1]), self.XDG_EVIDENCE[1]))),
        ])

    def test_pending(self):
        self.assert_green_then_red(self.check_pending, [
            ("fallback-unfilled", patched(rt, "FALLBACK_ENV", rt.PENDING)),
            ("top-unfilled", patched(rt, "TOP_FORMAT", rt.PENDING)),
            ("top-host-namespace", patched(rt, "TOP_FORMAT", TOP)),
            ("inspect-unfilled", patched(rt, "INSPECT_STATUS", rt.PENDING)),
            ("inspect-evidence-swapped", patched(rt, "INSPECT_STATUS", dict(rt.INSPECT_STATUS, evidence=(
                (rt.INSPECT_STATUS["evidence"][0][0], rt.INSPECT_STATUS["evidence"][1][1]),
                rt.INSPECT_STATUS["evidence"][1])))),
            ("resources-said-measured", patched(rt, "PENDING_WHY", dict(rt.PENDING_WHY, **{
                "TakeSpec.resources": "measured at the cold-start stub take"}))),
            # FILLED 14 Oct 2026: the clause now guards the fill (a list put back to PENDING shows in pending())
            ("billing-back-to-pending", patched(rt, "VENDOR_BILLING_ROUTE_VARIABLES",
                                                {"codex": rt.PENDING, "gemini": rt.PENDING})),
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
# Box lane 14 Oct (glitch-06's ruling on the lease postflight review's NIT 5, exactly these three, nothing else):
# preflight._read_capped opens the registered auth.json and then fstats the descriptor, so the file cannot be swapped
# between the lstat check and the read:
#   O_NONBLOCK - the open never blocks on a FIFO swapped in after the check;
#   fstat      - the opened descriptor's device, inode, type, links, mode and owner are compared with the check's lstat;
#   close      - the descriptor is closed when that comparison refuses, before any byte is read.
OS_ATTRS = frozenset({"O_CREAT", "O_EXCL", "O_NOFOLLOW", "O_RDONLY", "O_WRONLY", "environ", "fdopen", "fsync",
                      "getuid", "listdir", "lstat", "makedirs", "mkdir", "open", "path", "sep", "walk",
                      "O_NONBLOCK", "fstat", "close",
                      # R-H3 (lane vendor-b11 round 3): take_config.config_sha256 reads a link's target string, by
                      # name and never followed, to hash the four arg0 links; readlink starts nothing and opens nothing
                      "readlink"})
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
    # load: box/preflight.py's session_pair (called from postflight) parses the take's own sessions/N.json, size-capped and lstat-checked first, to
    # bind it to the take's session and socket (8c95a4fb; lane fold7/battery-reds, exactly this one name).
    "json": frozenset({"dump", "dumps", "load", "loads"}),
    "preflight": frozenset({"expected_take_inspect", "inspect_mismatches"}),
    "re": frozenset({"IGNORECASE", "compile", "escape", "fullmatch", "search"}),
    # GEMINI_MODE_ROUTE_VARIABLES: preflight's image check of the Gemini mode-route names (0b6f60f9; glitch-06's
    # ruling, 14 Oct 2026: exactly this one name).
    "run_take": frozenset({"AGENT_USER", "CLAUDE_CODE", "CODEX", "CONFIG_MOUNT", "GEMINI", "GEMINI_MODE_ROUTE_VARIABLES",
                           "HARNESS_ENV",
                           "INSPECT_PATHS", "INSPECT_STATUS", "KEEPALIVE_COMMAND", "KEEPALIVE_USER", "TAKE_TMPFS", "LOGIN_VARIABLE",
                           "NotReady", "PENDING", "PENDING_WHY", "PROXY_ALIAS", "PROXY_URL", "RUNTIME_CLIENT",
                           # glitch-06 (14 Oct 2026): preflight's create-time environment check reads it, so the
                           # Codex CLI's per-variable broker-snapshot prefixes are refused at create time too
                           "REFUSED_NAME_PREFIXES",
                           "Refused", "_abs_path", "_check_id", "_is_pending", "_known_harness", "_path_get",
                           "_write_json", "agent_exec_argv", "check_spec", "config_home_names",
                           "outside_every_repository", "refused_variables", "runtime_env",
                           # R-H3 (lane vendor-b11 round 3): take_config.config_sha256 reads run_take's one arg0
                           # link rule, shared with check_config_folder (constants and a pure function)
                           "CODEX_ARG0_DIR", "CODEX_ARG0_LINKS", "CODEX_EXECUTABLE", "codex_arg0_link"}),
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

    def test_an_unlisted_run_take_name_is_still_refused(self):
        """glitch-06 ruling, 14 Oct: listing GEMINI_MODE_ROUTE_VARIABLES admits that one name only."""
        for name in ("GEMINI_MODE_ROUTE_VARIABLES", "TAKE_ENV", "kill_agent"):
            src = f"from box import run_take\nx = run_take.{name}\n"
            got = [p for p in audit_source("box/preflight.py", src) if f"run_take.{name}" in p]
            if name == "GEMINI_MODE_ROUTE_VARIABLES":
                self.assertEqual(got, [], name)
            else:
                self.assertEqual(got, [f"box/preflight.py: run_take.{name} is not in MODULE_ATTRS"], name)

    def test_an_unlisted_json_name_is_still_refused(self):
        """Lane fold7/battery-reds: listing json.load (box/preflight.py's session_pair, called from postflight, parses the
        size-capped, producer-bound sessions/N.json, 8c95a4fb) admits that one name only; the module's other readers
        stay refused. Narrower than test_allowlists, which is the guard (it refuses every name added to MODULE_ATTRS);
        kept as the red-first witness of this one admission, naming the json readers that stay out."""
        for name in ("load", "JSONDecoder", "decoder", "loads"):
            src = f"import json\nx = json.{name}\n"
            got = [p for p in audit_source("box/preflight.py", src) if f"json.{name}" in p]
            if name in ("load", "loads"):
                self.assertEqual(got, [], name)
            else:
                self.assertEqual(got, [f"box/preflight.py: json.{name} is not in MODULE_ATTRS"], name)

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


# glitch-06, 14 Oct 2026: the Codex row still names CODEX_API_KEY as its credential marker (LOGIN_VARIABLE, which
# drive.py and walk_builders.py read, is derived from it), so its unreachability is proven, not assumed. Gemini's
# GEMINI_API_KEY is D8 B2's reviewed route (an API key with a hard cap) and stays the one vendor key its row names.
# Since the Codex exec branch (glitch-06, 14 Oct 2026): exec_argv's first test hands a Codex row to _codex_exec_argv,
# whose first statement is the closed lease gate; read_login is never on that road.
_CODEX_REFUSAL = ("    if harness == CODEX:\n        return _codex_exec_argv(container_id, inner, user=user, "
                  "workdir=workdir, run_tree=run_tree,\n                                "
                  "login_file=login_file, caller_env=caller_env)\n")
_CODEX_GATE_FIRST = "    codex_lease_gate()\n    src = os.environ if caller_env is None else caller_env\n"
_CODEX_BRANCH = ("return _codex_exec_argv(container_id, inner, user=user, workdir=workdir, run_tree=run_tree, "
                 "login_file=login_file, caller_env=caller_env)")


def _run_take_variant(src: str):
    """box/run_take.py compiled in memory from `src` (never written)."""
    import types
    mod = types.ModuleType("box.run_take_variant")
    mod.__file__ = rt.__file__
    sys.modules[mod.__name__] = mod             # dataclasses read their module while the class is made
    try:
        exec(compile(src, rt.__file__ + " (variant)", "exec"), mod.__dict__)
    finally:
        sys.modules.pop(mod.__name__, None)
    return mod


def codex_key_problems(m) -> list:
    """Every way a Codex take's environment could carry a vendor API key in module `m` ([] when none can)."""
    out = []
    # 1. exec_argv refuses Codex (NotReady, the subscription message) before any environment or login is touched.
    trips = []

    def trip(name):
        def f(*a, **k):
            trips.append(name)
            raise AssertionError(f"exec_argv reached {name} for codex")
        return f
    names = ("check_environment", "check_model", "exec_values", "take_environment", "read_login", "runtime_env",
             "launcher_argv")
    with contextlib.ExitStack() as stack:
        for n in names:
            stack.enter_context(mock.patch.object(m, n, trip(n)))
        stack.enter_context(mock.patch.object(m, "CODEX_SUBSCRIPTION_READY", False))   # pinned closed (B8-1)
        try:
            m.exec_argv(ID["take"], ["codex", "exec", "x"], user=m.AGENT_USER, workdir="/", harness=m.CODEX,
                        run_tree="/srv/w0/t1/tree", login_file="/nonexistent/login", caller_env={"PATH": "/bin"})
            out.append("exec_argv built a Codex turn")
        except m.NotReady as e:
            if str(e) != m.CODEX_SUBSCRIPTION_NOT_READY:
                out.append(f"exec_argv refused Codex for another reason: {e}")
        except AssertionError as e:
            out.append(str(e))
    if trips:
        out.append(f"exec_argv touched {trips} for codex")
    # 2. By the source: read_login is called in exec_argv only, after the Codex refusal.
    src = getattr(m, "_SRC", None)
    if src is None:
        with open(m.__file__, encoding="utf-8") as fh:
            src = fh.read()
    tree = ast.parse(src)
    callers = sorted({f.name for f in ast.walk(tree) if isinstance(f, ast.FunctionDef)
                      for c in ast.walk(f) if isinstance(c, ast.Call) and getattr(c.func, "id", "") == "read_login"})
    if callers != ["exec_argv"]:
        out.append(f"read_login is called from {callers}, not exec_argv alone")
    fn = [f for f in ast.walk(tree) if isinstance(f, ast.FunctionDef) and f.name == "exec_argv"]
    body = fn[0].body if fn else []
    first_if = next((i for i, st in enumerate(body) if isinstance(st, ast.If)), None)
    login_at = next((i for i, st in enumerate(body) if any(isinstance(c, ast.Call) and getattr(c.func, "id", "")
                                                            == "read_login" for c in ast.walk(st))), None)
    # O1-1 (review-box-o1.md): the first `if` is exactly `harness == CODEX`, its body exactly the hand-over to
    # _codex_exec_argv, and no else: a refusal a switch could bypass is not this refusal. Since the Codex exec branch
    # (14 Oct 2026), _codex_exec_argv's first statement (after its docstring) is exactly `codex_lease_gate()`, whose
    # body is exactly the one test-and-raise on CODEX_SUBSCRIPTION_READY.
    want_test = ast.dump(ast.parse("harness == CODEX", mode="eval").body)
    want_body = [ast.dump(st) for st in ast.parse(_CODEX_BRANCH).body]
    refusal = first_if is not None and ast.dump(body[first_if].test) == want_test \
        and [ast.dump(st) for st in body[first_if].body] == want_body and not body[first_if].orelse
    if not refusal or login_at is None or first_if > login_at:
        out.append("exec_argv's first test is not the Codex hand-over ahead of the login read")
    fns = {f.name: f for f in ast.walk(tree) if isinstance(f, ast.FunctionDef)}

    def stmts(name):
        b = fns[name].body if name in fns else []
        return [st for st in b if not (isinstance(st, ast.Expr) and isinstance(st.value, ast.Constant))]
    if [ast.dump(st) for st in stmts("_codex_exec_argv")[:1]] != [ast.dump(st) for st in
                                                                 ast.parse("codex_lease_gate()").body]:
        out.append("_codex_exec_argv's first statement is not the closed lease gate")
    want_gate = [ast.dump(st) for st in ast.parse("if CODEX_SUBSCRIPTION_READY is not True:\n"
                                                  "    raise NotReady(CODEX_SUBSCRIPTION_NOT_READY)").body]
    if [ast.dump(st) for st in stmts("codex_lease_gate")] != want_gate:
        out.append("codex_lease_gate is not exactly the test-and-raise on CODEX_SUBSCRIPTION_READY")
    # 3. The rows: every vendor key a Codex or Gemini row names is the credential marker (never a value), the strip
    # list is unchanged, Codex names no key but its refused marker, and Gemini no key but its own reviewed one.
    if tuple(m.VENDOR_KEY_VARIABLES) != ("CODEX_API_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY"):
        out.append(f"VENDOR_KEY_VARIABLES is {m.VENDOR_KEY_VARIABLES}")
    for harness, allowed in ((m.CODEX, {"CODEX_API_KEY"}), (m.GEMINI, {"GEMINI_API_KEY"})):
        keys = {k: v for k, v in m.TAKE_ENV[harness].items() if k in m.VENDOR_KEY_VARIABLES}
        if set(keys) - allowed:
            out.append(f"{harness}'s row names vendor keys {sorted(set(keys) - allowed)}")
        if any(v != m.CREDENTIAL for v in keys.values()):
            out.append(f"{harness}'s row gives a vendor key a value")
    return out


class TestCodexKeyUnreachable(MutantCase):
    def test_no_codex_or_gemini_take_env_can_carry_a_vendor_key(self):
        src = open(rt.__file__, encoding="utf-8").read()
        self.assertEqual(src.count(_CODEX_REFUSAL), 1)
        self.assertEqual(src.count(_CODEX_GATE_FIRST), 1)
        self.assertEqual(src.count("    if CODEX_SUBSCRIPTION_READY is not True:\n"), 1)

        def variant(new_src):
            mod = _run_take_variant(new_src)
            mod._SRC = new_src
            return mod
        self.assert_green_then_red(lambda: codex_key_problems(rt), [
            ("codex-refusal-dropped", lambda: mock.patch.object(
                sys.modules[__name__], "rt", variant(src.replace(_CODEX_REFUSAL, "")))),
            ("codex-refusal-after-login", lambda: mock.patch.object(sys.modules[__name__], "rt", variant(
                src.replace(_CODEX_REFUSAL, "").replace("    value = read_login(login_file, login)\n",
                                                         "    value = read_login(login_file, login)\n" + _CODEX_REFUSAL)))),
            ("codex-row-gains-openai-key", patched(rt, "TAKE_ENV", dict(rt.TAKE_ENV, **{
                rt.CODEX: dict(rt.TAKE_ENV[rt.CODEX], OPENAI_API_KEY=rt.CREDENTIAL)}))),
            ("gemini-key-given-a-value", patched(rt, "TAKE_ENV", dict(rt.TAKE_ENV, **{
                rt.GEMINI: dict(rt.TAKE_ENV[rt.GEMINI], GEMINI_API_KEY="fake-value")}))),
            ("strip-list-shortened", patched(rt, "VENDOR_KEY_VARIABLES", rt.VENDOR_KEY_VARIABLES[1:])),
            # the reviewer's probes (review-box-o1.md, O1-1): A a second read_login caller, B a switch-gated refusal
            ("probe-A-second-read-login-caller", lambda: mock.patch.object(sys.modules[__name__], "rt", variant(
                src + "\n\ndef _peek(f):\n    return read_login(f, 'CODEX_API_KEY')\n"))),
            ("probe-B-refusal-gated-by-a-switch", lambda: mock.patch.object(sys.modules[__name__], "rt", variant(
                src.replace(_CODEX_REFUSAL, "    if harness == CODEX and not os.environ.get('GAP4_CODEX_API'):\n"
                                            "        raise NotReady(CODEX_SUBSCRIPTION_NOT_READY)\n")))),
            ("refusal-body-gains-a-statement", lambda: mock.patch.object(sys.modules[__name__], "rt", variant(
                src.replace(_CODEX_REFUSAL, "    if harness == CODEX:\n        pass\n"
                                            "        raise NotReady(CODEX_SUBSCRIPTION_NOT_READY)\n")))),
            ("gate-not-first-in-the-codex-branch", lambda: mock.patch.object(sys.modules[__name__], "rt", variant(
                src.replace(_CODEX_GATE_FIRST, "    src = os.environ if caller_env is None else caller_env\n"
                                               "    check_codex_turn(inner)\n    codex_lease_gate()\n")))),
            ("gate-gains-a-switch", lambda: mock.patch.object(sys.modules[__name__], "rt", variant(
                src.replace("    if CODEX_SUBSCRIPTION_READY is not True:\n",
                            "    if CODEX_SUBSCRIPTION_READY is not True and not os.environ.get('GAP4_CODEX'):\n")))),
        ])


# Taken last, after every import-time statement of this module: must be empty (setUpModule arms the guard).
_PATCHED_AT_IMPORT = _patched_now()



# The bash-first steer OFF (glitch-6b's study-condition ruling, 15 Oct 2026, approved by Javier's "Your call sounds
# good"): the value is bound to the pinned binary's own parser, read statically from the take image (docker create
# --network none + docker cp, never run) by the four committed probes, each record pinned by its bytes here.
STEER_EVIDENCE = (
    ("claude-2.1.296-thrifty-sonic-hxt-20261015.json", "b713239952b760e4b2fa6ba34378f2c75b2372f1990a7da42c497599cd5727de"),
    ("claude-2.1.296-thrifty-sonic-getter-20261015.json", "d1735de8f3cada3354a4c65ca527f633e1810c88fef7de0662fd99551601add4"),
    ("claude-2.1.296-tribool-20261015.json", "0dd5dd871c6c1e34590068510f4e21b273b0ba0dd776ca3a3c816a3469cb1a8f"),
    ("claude-2.1.296-tribool-helpers-20261015.json", "17b4a363720ca7a2cd4b6371c7b4e5d89fc3da043db329aa9ed071782cc74932"))
STEER_SWITCH = "CLAUDE_CODE_THRIFTY_SONIC"


def _steer_records() -> tuple:
    """The four probe records, refused unless each is the pinned bytes."""
    out = []
    for name, digest in STEER_EVIDENCE:
        with open(os.path.join(CLAUDE_SWEEP_DIR, name), "rb") as fh:
            raw = fh.read()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise AssertionError(f"{name} is not the committed probe record")
        out.append(json.loads(raw))
    return tuple(out)


def _js_list(source: str, fn: str) -> list:
    """The string list `fn`'s body tests membership in, read from its source text (exactly one such list)."""
    m = re.fullmatch(r"function " + fn + r"\(e\)\{(?:if\(e===void 0\)return!1;|if\(!e\)return!1;)if\(typeof "
                     r"e===\"boolean\"\)return(?:!| )e;let n=String\(e\)\.toLowerCase\(\)\.trim\(\);return\[((?:\"[a-z0-9]+\""
                     r",?)+)\]\.includes\(n\)\}", source)
    if not m:
        raise AssertionError(f"{fn}'s recorded source is not the tri-state helper shape")
    return json.loads("[" + m.group(1) + "]")


def _function_text(rec: dict, key: str, fn: str) -> str:
    """The recorded source of `fn` up to its closing brace (the helper bodies hold no nested braces after `{`)."""
    for site in rec["sources"].get(key, []):
        t = site["text"]
        if t.startswith(f"function {fn}(e){{"):
            depth = 0
            for i, ch in enumerate(t):
                depth += ch == "{"
                depth -= ch == "}"
                if depth == 0 and ch == "}":
                    return t[:i + 1]
    raise AssertionError(f"no recorded tri-state source for {fn}")


class TestBashFirstSteerOff(MutantCase):
    """The study condition: the auto_mode bash-first steer is OFF for every claude-code take. Claude Code 2.1.296's
    gate HXt() returns `a.CLAUDE_CODE_THRIFTY_SONIC` whenever it is not undefined (else a model cohort); the env
    module declares it `rE=H.triBool()`; triBool is `i((n)=>{if(Ne(n))return!0;if(vs(n))return!1;return})` over
    `i(n){return{parse:(e)=>n(u(e))}}`; and vs is true for exactly the lowercased, trimmed strings in its list. The
    row's value must be in vs's list and not in Ne's, and ride both the exec's pairs and the inline settings' env (the
    level above the run tree's files, and the one the per-turn launch journal records for the checker)."""

    def check(self):
        out = []
        try:
            hxt, getter, tri, helpers = _steer_records()
        except AssertionError as e:
            return [str(e)]
        for rec in (hxt, getter, tri, helpers):
            if rec.get("binary_sha256") != rt.CLAUDE_BINARY["sha256"] or rec.get("image") != rt.CLAUDE_BINARY["image_id"]:
                out.append(f"{rec.get('probe')}: not a read of the pinned binary in the pinned image")
        if rt.CLAUDE_BINARY["image_id"] != _lock_image("."):
            out.append("the pinned binary's image is not box/image.lock's")
        gate = f"function HXt(){{if(a.{STEER_SWITCH}!==void 0)return a.{STEER_SWITCH};switch(ae()){{"
        if not any(gate in h["text"] for h in hxt["HXt"]):
            out.append("HXt does not return the switch's parsed value whenever it is set")
        if getter.get("getter_target") != "rE" or not any(",rE=H.triBool()," in d["text"] for d in getter["definitions"]):
            out.append("the switch is not declared a triBool")
        tri_def = "triBool:()=>s"
        tri_body = "s=i((n)=>{if(Ne(n))return!0;if(vs(n))return!1;return})"
        if not any(tri_def in d["text"] and tri_body in d["text"] and "function i(n){return{parse:(e)=>n(u(e))}}"
                   in helpers["sources"]["ctx:700"][0]["text"] for d in tri["definition_sites"]):
            out.append("triBool is not Ne-then-vs over the raw string")
        if 'import{Ne,vs}from"' not in helpers["sources"]["ctx:700"][0]["text"]:
            out.append("the env module does not import its Ne and vs")
        try:
            false_list = _js_list(_function_text(helpers, "any:vs", "vs"), "vs")
            true_list = _js_list(_function_text(helpers, "any:Ne", "Ne"), "Ne")
        except AssertionError as e:
            return out + [str(e)]
        row = rt.TAKE_ENV[rt.CLAUDE_CODE].get(STEER_SWITCH)
        value = getattr(rt, "BASH_FIRST_STEER_ENV", {}).get(STEER_SWITCH)
        if value is None or row != value:
            out.append(f"the claude-code row does not carry {STEER_SWITCH} as BASH_FIRST_STEER_ENV gives it")
        elif value.lower().strip() not in false_list or value.lower().strip() in true_list:
            out.append(f"{STEER_SWITCH}={value!r} is not read as false by the pinned parser ({false_list})")
        for arm in (rt.CODEX, rt.GEMINI):
            if STEER_SWITCH in rt.TAKE_ENV[arm]:
                out.append(f"{arm}'s row carries a Claude Code switch")
        with filled():
            settings = json.loads(rt.claude_study_settings(CLAUDE_MODEL))
            env = rt.take_environment(rt.CLAUDE_CODE, "/srv/w/t1/tree")
        if value is not None and settings.get("env", {}).get(STEER_SWITCH) != value:
            out.append("the inline settings' env does not carry the switch off")
        if value is not None and env.get(STEER_SWITCH) != value:
            out.append("take_environment does not hand the agent the switch off")
        return out

    def test_the_steer_is_off(self):
        self.assertEqual(problems_of(self.check), [])

    def test_mutants(self):
        on = {**rt.TAKE_ENV, rt.CLAUDE_CODE: {**rt.TAKE_ENV[rt.CLAUDE_CODE], STEER_SWITCH: "1"}}
        unread = {**rt.TAKE_ENV, rt.CLAUDE_CODE: {**rt.TAKE_ENV[rt.CLAUDE_CODE], STEER_SWITCH: "disabled"}}
        gone = {**rt.TAKE_ENV, rt.CLAUDE_CODE: {k: v for k, v in rt.TAKE_ENV[rt.CLAUDE_CODE].items()
                                                  if k != STEER_SWITCH}}
        self.assert_green_then_red(self.check, (
            ("the switch on", lambda: _patches((rt, "TAKE_ENV", on),
                                               (rt, "BASH_FIRST_STEER_ENV", {STEER_SWITCH: "1"}))),
            ("a value the parser reads as unset", lambda: _patches(
                (rt, "TAKE_ENV", unread), (rt, "BASH_FIRST_STEER_ENV", {STEER_SWITCH: "disabled"}))),
            ("the switch dropped from the row", patched(rt, "TAKE_ENV", gone)),
            ("the switch dropped from the settings", patched(rt, "claude_study_settings", lambda m: json.dumps(
                {"availableModels": [m], "env": dict(rt.FALLBACK_ENV), "fallbackModel": [],
                 "switchModelsOnFlag": False}, sort_keys=True, separators=(",", ":")))),
            ("another binary", lambda: mock.patch.dict(rt.CLAUDE_BINARY, {"sha256": "0" * 64})),
            ("the evidence swapped", patched(sys.modules[__name__], "STEER_EVIDENCE",
                                             STEER_EVIDENCE[:3] + (("claude-2.1.296-tribool-helpers-20261015.json",
                                                                    "0" * 64),))),
        ))



# The isolation denials (glitch-6b's ruling, 15 Oct 2026, under the delegation): RemoteTrigger (claude.ai Routines, the
# one road a take's token has to the account outside the box), SendMessage and ListAgents (cross-session channels) are
# DISALLOWED for every claude-code take, and cross-session inbound messages are refused. The names and the setting's
# values are read from the pinned binary (claude_string_context_probe.py; docker create --network none + docker cp,
# never run), each record pinned by its bytes here.
ISOLATION_EVIDENCE = (
    ("claude-2.1.296-isolation-names-20261015.json", "ba3e3e6d54d06ab495595264521edc329b9123b57944df100acea658a303d81a"),
    ("claude-2.1.296-cross-session-values-20261015.json",
     "1ceb44b1e499e7b61365e0fafe7fbae88065899fd217644024d9deb82489dfc4"))
ISOLATION_TOOL_DECLARATIONS = {"RemoteTrigger": 'var N$="RemoteTrigger",Mcs="Manage scheduled remote Claude Code agents',
                               "SendMessage": 'var Gn="SendMessage",', "ListAgents": 'var xc="ListAgents",'}
ISOLATION_FACE = {"SendMessage": 'userFacingName(){return"SendMessage"}', "ListAgents": 'userFacingName(){return"ListAgents"}'}


def _isolation_records() -> tuple:
    out = []
    for name, digest in ISOLATION_EVIDENCE:
        with open(os.path.join(CLAUDE_SWEEP_DIR, name), "rb") as fh:
            raw = fh.read()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise AssertionError(f"{name} is not the committed probe record")
        out.append(json.loads(raw))
    return tuple(out)


def _texts(rec: dict, needle: str) -> list:
    return [s["text"] for s in rec["needles"].get(needle, {}).get("sites", [])]


class TestIsolationDenials(MutantCase):
    """The three tools are denied by the names the pinned binary declares, on the exec argv (--disallowedTools, a
    variadic comma-or-space list) AND in the inline settings' permissions.deny; crossSessionInbound is "refuse", one of
    the binary's values ["accept","hold","refuse"]. run_take refuses a claude-code turn whose argv denies fewer."""

    def check(self):
        out = []
        try:
            names, values = _isolation_records()
        except AssertionError as e:
            return [str(e)]
        for rec in (names, values):
            if rec.get("binary_sha256") != rt.CLAUDE_BINARY["sha256"] or rec.get("image") != rt.CLAUDE_BINARY["image_id"]:
                out.append(f"{rec.get('probe')}: not a read of the pinned binary in the pinned image")
        tools = tuple(getattr(rt, "ISOLATION_DISALLOWED_TOOLS", ()))
        if tools != ("RemoteTrigger", "SendMessage", "ListAgents"):
            out.append(f"ISOLATION_DISALLOWED_TOOLS is {tools}, not the ruled three")
        for tool in tools:
            decl = ISOLATION_TOOL_DECLARATIONS.get(tool)
            if decl is None or not any(decl in t for t in _texts(names, f'"{tool}"')):
                out.append(f"{tool} is not a tool name the pinned binary declares")
            if tool in ISOLATION_FACE and not any(ISOLATION_FACE[tool] in t for t in _texts(names, f'"{tool}"')):
                out.append(f"{tool} is not the name the tool answers to")
        if not any('"--disallowedTools, --disallowed-tools <tools...>",\'Comma or space-separated list of tool names to '
                   'deny' in t for t in _texts(names, '"--disallowedTools')):
            out.append("--disallowedTools is not the binary's variadic comma-or-space deny list")
        if not any('var sHt=["accept","hold","refuse"]' in t and "deny:T(" in t for t in _texts(values, "sHt=")):
            out.append('"refuse" is not a crossSessionInbound value, or permissions.deny is not in the schema')
        with filled():
            st = json.loads(rt.claude_study_settings(CLAUDE_MODEL))
            if st.get("crossSessionInbound") != "refuse":
                out.append("the inline settings do not refuse cross-session inbound messages")
            if st.get("permissions") != {"deny": list(tools)} or not tools:
                out.append(f"the inline settings' permissions are {st.get('permissions')}")
            base = ["claude", "-p", "x", "--model", CLAUDE_MODEL, "--settings", rt.claude_study_settings(CLAUDE_MODEL)]
            for name, tail, ok in (
                    ("space list", ["--disallowedTools", "WebFetch", "WebSearch", *tools], True),
                    ("comma list", ["--disallowed-tools=" + ",".join(tools)], True),
                    ("split over two flags", ["--disallowedTools", "RemoteTrigger", "--disallowed-tools",
                                              "SendMessage,ListAgents"], True),
                    ("no deny flag", [], False),
                    ("one name missing", ["--disallowedTools", "RemoteTrigger", "SendMessage"], False),
                    ("a near name", ["--disallowedTools", "RemoteTrigger", "SendMessage", "ListPeer"], False),
                    ("the names after another flag", ["--disallowedTools", "--session-id", *tools], False)):
                try:
                    rt.check_claude_settings(base + tail)
                    if not ok:
                        out.append(f"{name}: admitted")
                except rt.Refused as e:
                    if ok:
                        out.append(f"{name}: refused ({e})")
        return out

    def test_the_three_are_denied(self):
        self.assertEqual(problems_of(self.check), [])

    def test_mutants(self):
        self.assert_green_then_red(self.check, (
            ("one tool dropped", patched(rt, "ISOLATION_DISALLOWED_TOOLS", ("RemoteTrigger", "SendMessage"))),
            ("a misspelt tool", patched(rt, "ISOLATION_DISALLOWED_TOOLS", ("RemoteTriggers", "SendMessage",
                                                                           "ListAgents"))),
            ("the argv check dropped", patched(rt, "_denied_tools", lambda inner: set(rt.ISOLATION_DISALLOWED_TOOLS))),
            ("inbound accepted", patched(rt, "CROSS_SESSION_INBOUND", "accept")),
            ("another binary", lambda: mock.patch.dict(rt.CLAUDE_BINARY, {"sha256": "0" * 64})),
            ("the evidence swapped", patched(sys.modules[__name__], "ISOLATION_EVIDENCE",
                                             ISOLATION_EVIDENCE[:1] + (("claude-2.1.296-cross-session-values-"
                                                                        "20261015.json", "0" * 64),))),
        ))


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
