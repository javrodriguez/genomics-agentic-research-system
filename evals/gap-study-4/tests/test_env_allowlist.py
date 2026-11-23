#!/usr/bin/env python3
"""The take environment as an ALLOWLIST (Gap Study round 4, lane w12a-env-allowlist; ruling docs-1 on the docs read of
Tue 13 Oct 2026, plans/gap-study-round-4/docs-reads-2026-10-13.md; glitch-2f's assignment under Javier's standing
delegation).

  E1  the ONE table: box/run_take.TAKE_ENV names, per arm, everything the agent may start with: PATH, HOME, LANG, the
      run tree's TMPDIR, TMP and TEMP, the proxy, the harness's own switches and config home, and exactly one
      credential, by NAME only (the CREDENTIAL marker). Arm A's HOME is the config mount; arm O's and arm G's is the
      run tree's .home (R-H5, glitch-26, 19 Oct 2026), and arm A's row is pinned by its bytes. No row names a refused
      variable.
      LOGIN_VARIABLE and HARNESS_ENV are views derived from it (by AST: comprehensions over TAKE_ENV, never literals).
  E2  nothing else reaches the agent: with every billing and route variable the docs read found (Codex's
      OPENAI_PROJECT, OPENAI_ORGANIZATION and the AWS chain; Gemini CLI's GOOGLE_GENAI_USE_VERTEXAI,
      GOOGLE_GENAI_USE_GCA, GEMINI_CLI_USE_COMPUTE_ADC, CLOUD_SHELL, GOOGLE_GEMINI_BASE_URL; and the rest of both
      lists) plus a canary set in the parent, (a) take_environment builds exactly the row; (b) exec_argv builds a
      turn whose launcher hands the harness exactly the row and the credential, and whose client environment is the
      runtime's needs and the credential alone; (c) the launcher itself, run in memory with every one of those names
      and the image's own ENV in its starting environment, execs the harness with exactly the row and the credential.
      A name the old closed refusal also names is still refused at exec (refused, never passed).
  E3  a `.env` the CLI would read refuses, by its path: the working folder, a parent between it and the box root (the
      run tree), the box root itself, HOME and the config home (the config folder; arm O's and G's HOME is the run
      tree's .home, R-H5), each alone, under both loader names (`.env`,
      `.gemini/.env`), a dangling link included; launch refuses before any runtime call; run_turn refuses before its
      exec and writes no stream; no take Dockerfile writes a `.env`.
  E4  arm G's model: a short alias (auto, pro, flash, flash-lite) is refused by its name, with what it resolves to
      (flash-lite -> gemini-2.5-flash-lite); the full pinned ids pass; another id, no model flag, or two are refused;
      exec_argv refuses a gemini call that names an alias; MODEL_PINS' arm G ids equal build_draft.MODELS["G"].
  E5  this lane's functions one at a time (the generated sweep's first-round survivors): take_environment refuses an
      unknown arm, a relative run tree and a row whose temporary-folder names are off, waits (NotReady) on each
      PENDING value, adds Claude Code's fallback values to arm A alone and never over a row's name; launcher_argv
      refuses a credential that is not a NAME and a value that is not a string; check_model refuses an empty arm G call; refuse_env_files refuses a row whose HOME is not the config mount.
  G1  the generated mutants (tests/walk_mutation.py's generator over this lane's functions in box/run_take.py):
      EQUIVALENT names only generated ids, each with a reason.

Fakes and synthetic strings only: no model, vendor, network, container runtime, credential, salt or holdout. Every
process start is a tripwire while the tests run (the witness and sweep runners start this file only, before it is
armed). Every folder a test writes or removes is its own mkdtemp. PENDING values are filled in memory for one test.

--mutant NAME compiles one altered run_take in memory before the bound test runs; --witnesses runs every registered
mutant in its own process and requires its bound test to fail by an AssertionError carrying its clause token (rule
B). --generated-mutants [--shard i/n] [--sample k] [--only id,id] [--timeout s] runs each generated mutant in its own
process over this whole module (failfast) and fails on a survivor not in EQUIVALENT, a listed one killed, or an
inconclusive run.
"""
from __future__ import annotations

import ast
import builtins
import contextlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent.parent
for p in (HERE, HERE / "tests"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from box import run_take as REAL_RT  # noqa: E402
import claude_code_adapter as CCA  # noqa: E402  (the box's real Claude Code turn builder, C15)

SELECTED = None          # --mutant NAME
GENERATED = None         # --gen-mutant ID
MODS: dict = {}
SOURCE = HERE / "box" / "run_take.py"
MODULE = "run_take"
# This lane's functions in box/run_take.py: the generated sweep's road.
ROAD_FUNCTIONS = ("take_environment", "exec_values", "launcher_argv", "check_model", "env_file_dirs",
                  "refuse_env_files")

ID = "d" * 64
CLAUDE_MODEL = "claude-opus-5-5"
CLAUDE_SID = "00000000-0000-4000-8000-000000000001"
FAKE_VALUE = "FAKEVALUE-w12a-0123456789abcdef-PLANTED"
CANARY = "W12A_CANARY_PARENT_ONLY"
CANARY_VALUE = "canary-value-w12a"
CALLER = {"PATH": "/usr/bin:/bin", "HOME": "/home/op", "DOCKER_HOST": "unix:///run/user/1000/docker.sock",
          "XDG_RUNTIME_DIR": "/run/user/1000"}
ARMS = ("claude-code", "codex", "gemini")
# Codex has no environment login (glitch-06's ruling 1, 14 Oct 2026: subscriptions only, the lease road): its row has
# no credential and its LOGIN_VARIABLE is the launcher's reserved "-" (run_take.NO_LOGIN).
LOGINS = {"claude-code": "CLAUDE_CODE_OAUTH_TOKEN", "codex": "-", "gemini": "GEMINI_API_KEY"}
ENV_CREDENTIAL = {"claude-code": ["CLAUDE_CODE_OAUTH_TOKEN"], "codex": [], "gemini": ["GEMINI_API_KEY"]}
# The docs read of 13 Oct (section d): every billing and route variable both lists name, docs and source.
DOCS_READ_VARIABLES = (
    # Codex, read by the source at rust-v0.162.1 beyond its docs
    "OPENAI_PROJECT", "OPENAI_ORGANIZATION", "AWS_BEARER_TOKEN_BEDROCK", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY",
    "AWS_REGION", "AWS_DEFAULT_REGION", "AWS_PROFILE", "CODEX_OSS_BASE_URL", "CODEX_OSS_PORT",
    # Codex, documented
    "CODEX_ACCESS_TOKEN", "OPENAI_FEDERATION_RULE_ID", "OPENAI_IDENTITY_TOKEN_FILE", "OPENAI_WORKLOAD_IDENTITY_CONTEXT",
    "OPENAI_BASE_URL",
    # Gemini CLI, read by the source at v0.63.0 beyond its docs
    "GOOGLE_GENAI_USE_VERTEXAI", "GOOGLE_GENAI_USE_GCA", "GEMINI_CLI_USE_COMPUTE_ADC", "CLOUD_SHELL",
    "GEMINI_API_KEY_AUTH_MECHANISM", "GEMINI_CLI_CUSTOM_HEADERS",
    # Gemini CLI, documented
    "GOOGLE_GEMINI_BASE_URL", "GOOGLE_VERTEX_BASE_URL", "GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_PROJECT_ID",
    "GOOGLE_CLOUD_LOCATION", "GOOGLE_APPLICATION_CREDENTIALS",
)
# The Gemini CLI v0.63.0 alias table (docs/cli/cli-reference.md, read 13 Oct 2026), copied by hand from the read.
GEMINI_ALIASES = {"auto": "gemini-2.5-pro or gemini-3-pro-preview", "pro": "gemini-2.5-pro or gemini-3-pro-preview",
                  "flash": "gemini-2.5-flash", "flash-lite": "gemini-2.5-flash-lite"}
# A stand-in for the image's own ENV and docker exec's defaults, in the launcher's starting environment.
IMAGE_ENV = {"PYTHONDONTWRITEBYTECODE": "1", "HOSTNAME": "take", "HOME": "/home/dana",
             "PATH": "/usr/local/bin:/usr/bin:/bin"}


# ---------------------------------------------------------------------------------- the process guard
GUARDED = [(subprocess, n) for n in ("run", "Popen", "call", "check_call", "check_output")]
GUARDED += [(os, n) for n in ("system", "popen", "kill", "killpg", "fork", "posix_spawn", "posix_spawnp")
            if hasattr(os, n)]
GUARDED += [(os, n) for n in dir(os) if re.fullmatch(r"(exec|spawn)[lvpe]*", n)]
_ORIGINALS = [(m, n, getattr(m, n)) for m, n in GUARDED]
_ENV_SET_ASIDE: dict = {}


def _trip(name):
    def trip(*a, **k):
        raise AssertionError(f"process guard: a test reached {name}")
    return trip


def compile_module(source: str) -> types.ModuleType:
    mod = types.ModuleType("run_take_w12a_under_test")
    mod.__file__ = str(SOURCE)
    sys.modules[mod.__name__] = mod          # dataclasses read the defining module from sys.modules
    exec(compile(source, str(SOURCE) + " (witness)", "exec"), mod.__dict__)
    return mod


def setUpModule():
    text = SOURCE.read_text()
    if SELECTED is not None:
        _, old, new = mutants()[SELECTED]
        assert text.count(old) == 1, f"witness {SELECTED}: its anchor occurs {text.count(old)} times"
        MODS["rt"] = compile_module(text.replace(old, new))
    elif GENERATED is not None:
        m = by_id()[GENERATED]
        MODS["rt"] = compile_module(m.source(text))
    else:
        MODS["rt"] = compile_module(text)
    MODS["text"] = text if SELECTED is None else text.replace(*mutants()[SELECTED][1:])
    rt = MODS["rt"]
    # run_take always refuses a closed-list name in this process's own environment: set those aside for the module
    # (names only; restored untouched at tearDownModule, never read or printed).
    closed = set(rt.API_KEY_VARIABLES) | set(rt.BILLING_ROUTE_VARIABLES) | set(rt.SUBSCRIPTION_TOKEN_VARIABLES) \
        | set(rt.VENDOR_KEY_VARIABLES) | set(DOCS_READ_VARIABLES) | {CANARY}
    for name in list(os.environ):
        if name in closed:
            _ENV_SET_ASIDE[name] = os.environ.pop(name)
    for m, n in GUARDED:
        setattr(m, n, _trip(f"{m.__name__}.{n}"))


def tearDownModule():
    for m, n, orig in _ORIGINALS:
        setattr(m, n, orig)
    os.environ.update(_ENV_SET_ASIDE)
    _ENV_SET_ASIDE.clear()


def rt():
    return MODS["rt"]


@contextlib.contextmanager
def filled():
    """The PENDING values an exec needs, filled in memory for one test (interface 15)."""
    m = rt()
    with mock.patch.object(m, "FALLBACK_ENV", {}), \
            mock.patch.object(m, "VENDOR_BILLING_ROUTE_VARIABLES", {m.CODEX: (), m.GEMINI: ()}):
        yield


class FakeRuntime:
    def __init__(self):
        self.calls = []

    def run(self, argv, *, env=None, timeout=None):
        self.calls.append(list(argv))
        raise AssertionError(f"unexpected runtime call {argv}")


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="w12a-")).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        # While the slice is absent (the red run on the base): a failure by assertion, never an error.
        self.assertTrue(hasattr(rt(), "TAKE_ENV"), "w12a: box/run_take.TAKE_ENV, the module under test, is absent")

    def must(self, clause, fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except AssertionError:
            raise
        except Exception as e:  # noqa: BLE001
            self.fail(f"{clause}: {type(e).__name__}: {str(e)[:400]}")

    def refuses(self, clause, words, fn, *args, **kwargs):
        try:
            fn(*args, **kwargs)
        except rt().Refused as e:
            for w in ([words] if isinstance(words, str) else words):
                self.assertIn(w, str(e), f"{clause}: refused for another reason: {e}")
            self.assertNotIn(FAKE_VALUE, str(e), f"{clause}: the refusal carries the value")
            return str(e)
        except Exception as e:  # noqa: BLE001
            self.fail(f"{clause}: raised {type(e).__name__}, not Refused: {str(e)[:300]}")
        self.fail(f"{clause}: not refused ({words!r})")

    def not_ready(self, clause, words, fn, *args, **kwargs):
        try:
            fn(*args, **kwargs)
        except rt().NotReady as e:
            self.assertIn(words, str(e), f"{clause}: pending for another reason: {e}")
            return
        except Exception as e:  # noqa: BLE001
            self.fail(f"{clause}: raised {type(e).__name__}, not NotReady: {str(e)[:300]}")
        self.fail(f"{clause}: did not wait on {words}")

    def login(self, harness):
        path = self.tmp / f"{harness}.line"
        path.write_text(f"{LOGINS[harness]}={FAKE_VALUE}\n")
        os.chmod(path, 0o600)
        return str(path)


def expected_row(harness, run_tree):
    """The arm's row as the ruling words it, written here by hand (never read from the module under test). R-H5
    (glitch-26's ruling on the B11 design note, Mon 19 Oct 2026): arm O's and arm G's HOME is the run tree's own
    .home, outside the config mount, while CODEX_HOME and GEMINI_CLI_HOME stay on it; arm A's HOME is the mount."""
    t = f"{run_tree}/.tmp"
    home = "/opt/cfg" if harness == "claude-code" else f"{run_tree}/.home"
    base = {"PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin", "HOME": home,
            "LANG": "C.UTF-8", "TMPDIR": t, "TMP": t, "TEMP": t, "HTTPS_PROXY": "http://proxy:3128"}
    own = {"claude-code": {"DISABLE_AUTOUPDATER": "1", "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
                           "ENABLE_CLAUDEAI_MCP_SERVERS": "false", "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1",
                           "CLAUDE_CODE_THRIFTY_SONIC": "false",   # the bash-first steer OFF (glitch-6b, 15 Oct)
                           "CLAUDE_CODE_SILENT_TURN_REMINDER": "0",   # the silent-turn reminder OFF (glitch-b5, 16 Oct)
                           "CLAUDE_CONFIG_DIR": "/opt/cfg"},
           "codex": {"CODEX_HOME": "/opt/cfg"},
           "gemini": {"GEMINI_CLI_HOME": "/opt/cfg"}}[harness]
    return {**base, **own}


def split_turn(argv):
    """(the docker part, the launcher argv, the credential name, the pairs as a dict, the harness argv)."""
    i = argv.index(ID)
    launcher = argv[i + 1:i + 1 + len(REAL_RT_LAUNCHER_LEN())]
    rest = argv[i + 1 + len(launcher):]
    name, n = rest[0], int(rest[1])
    pairs = dict(x.split("=", 1) for x in rest[2:2 + n])
    return argv[:i + 1], launcher, name, pairs, rest[2 + n:]


def REAL_RT_LAUNCHER_LEN():
    return getattr(rt(), "LAUNCHER", ())


def run_launcher(launcher_and_args, start_env, present=(), cwd="/srv/w/t1/tree", recorded=None):
    """The launcher's source run in memory: `import os,sys` answers fakes; os.execvpe is captured, never called."""
    src = launcher_and_args[4]
    got = {} if recorded is None else recorded
    path = types.SimpleNamespace(join=os.path.join, dirname=os.path.dirname, lexists=lambda p: p in present)
    fake_os = types.SimpleNamespace(environ=dict(start_env), path=path, getcwd=lambda: cwd,
                                    execvpe=lambda f, a, e: got.update(file=f, argv=list(a), env=dict(e)))
    fake_sys = types.SimpleNamespace(argv=["-c", *launcher_and_args[5:]])
    real_import = builtins.__import__

    def imp(name, *a, **k):
        return {"os": fake_os, "sys": fake_sys}.get(name) or real_import(name, *a, **k)
    exec(compile(src, "<launcher>", "exec"), {"__builtins__": dict(vars(builtins), __import__=imp)})
    return got


# ------------------------------------------------------------------------------------------------- E1
class E1Table(Case):
    def test_each_row_is_the_ruling_s_set(self):
        m = rt()
        table = getattr(m, "TAKE_ENV", None)
        self.assertIsInstance(table, dict, "E1.table: run_take has no TAKE_ENV table")
        self.assertEqual(sorted(table), sorted(ARMS), "E1.table: the arms are off")
        for h in ARMS:
            row = table[h]
            creds = [k for k, v in row.items() if v == m.CREDENTIAL]
            self.assertEqual(creds, ENV_CREDENTIAL[h], f"E1.table: {h}'s credential is not its one login, by name")
            markers = {m.RUN_TREE_TMP: "/r/t/.tmp", getattr(m, "RUN_TREE_HOME", m.RUN_TREE_TMP): "/r/t/.home"}
            filled = {k: markers.get(v, v) for k, v in row.items() if v != m.CREDENTIAL}
            self.assertEqual(filled, expected_row(h, "/r/t"), f"E1.table: {h}'s row is off the ruling's set")
            bad = sorted(set(row) & set(m.refused_variables(h)))
            self.assertEqual(bad, [], f"E1.table: {h}'s row names a refused variable")
            for k, v in row.items():
                self.assertRegex(k, r"^[A-Z_][A-Z0-9_]*$", "E1.table: a name off the variable-name form")
                self.assertNotIn("\0", v, "E1.table: a value carries a NUL")

    # R-H5: arm A's row stays byte-unchanged (round-3 parity), pinned by its source bytes at 56d7713b (box/run_take.py
    # lines 155-159 there) and by its value.
    CLAUDE_ROW_SOURCE = (
        '    CLAUDE_CODE: {"PATH": TAKE_PATH, "HOME": CONFIG_MOUNT, "LANG": TAKE_LANG,\n'
        '                  "TMPDIR": RUN_TREE_TMP, "TMP": RUN_TREE_TMP, "TEMP": RUN_TREE_TMP, "HTTPS_PROXY": PROXY_URL,\n'
        '                  "DISABLE_AUTOUPDATER": "1", "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1", **ISOLATION_ENV,\n'
        '                  **BASH_FIRST_STEER_ENV, **SILENT_TURN_REMINDER_ENV, "CLAUDE_CONFIG_DIR": CONFIG_MOUNT,\n'
        '                  "CLAUDE_CODE_OAUTH_TOKEN": CREDENTIAL},\n')
    CLAUDE_ROW_SOURCE_SHA256 = "f28954dea54db364f5ecd3db83d06ab69939651fdb504a6c0cd6b94020d051a7"
    CLAUDE_ROW_VALUE_SHA256 = "97dd88fe3065413904ab9643767a0b1771d3db7ec0e2741b6ba730b3059c7800"

    def test_arm_a_row_is_byte_unchanged(self):
        import hashlib
        m = rt()
        self.assertEqual(hashlib.sha256(self.CLAUDE_ROW_SOURCE.encode()).hexdigest(), self.CLAUDE_ROW_SOURCE_SHA256,
                         "R-H5.parity: the pinned bytes themselves moved")
        self.assertEqual(MODS["text"].count(self.CLAUDE_ROW_SOURCE), 1,
                         "R-H5.parity: arm A's TAKE_ENV row is not its round-3-parity bytes")
        value = json.dumps(m.TAKE_ENV[m.CLAUDE_CODE], sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(value).hexdigest(), self.CLAUDE_ROW_VALUE_SHA256,
                         "R-H5.parity: arm A's TAKE_ENV row has another value")
        self.assertEqual(m.TAKE_ENV[m.CLAUDE_CODE]["HOME"], m.CONFIG_MOUNT, "R-H5.parity: arm A's HOME moved")

    def test_the_views_are_derived(self):
        m = rt()
        self.assertEqual(m.LOGIN_VARIABLE, LOGINS, "E1.derived: LOGIN_VARIABLE off")
        for h in ARMS:
            want = {k: v for k, v in expected_row(h, "/r/t").items()
                    if k not in ("PATH", "HOME", "LANG", "TMPDIR", "TMP", "TEMP")}
            self.assertEqual(m.HARNESS_ENV[h], want, f"E1.derived: HARNESS_ENV[{h}] off")
        tree = ast.parse(SOURCE.read_text())
        assigned = {}
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        assigned.setdefault(t.id, []).append(node.value)
        self.assertEqual(len(assigned.get("TAKE_ENV", [])), 1, "E1.derived: TAKE_ENV is not assigned exactly once")
        for name in ("LOGIN_VARIABLE", "HARNESS_ENV"):
            vals = assigned.get(name, [])
            self.assertEqual(len(vals), 1, f"E1.derived: {name} assigned {len(vals)} times")
            self.assertIsInstance(vals[0], ast.DictComp, f"E1.derived: {name} is declared, not derived")
            self.assertIn("TAKE_ENV", ast.unparse(vals[0]), f"E1.derived: {name} is not read from TAKE_ENV")


# ------------------------------------------------------------------------------------------------- E2
PARENT = {**{n: FAKE_VALUE for n in DOCS_READ_VARIABLES}, CANARY: CANARY_VALUE}


class E2Allowlist(Case):
    def test_take_environment_is_the_row_alone(self):
        m = rt()
        with filled(), mock.patch.dict(os.environ, PARENT):
            for h in ARMS:
                got = self.must("E2.built", m.take_environment, h, "/srv/w/t1/tree")
                want = dict(expected_row(h, "/srv/w/t1/tree"), **{n: m.CREDENTIAL for n in ENV_CREDENTIAL[h]})
                self.assertEqual(got, want, f"E2.built: {h}'s environment is not exactly its row")
                leaked = sorted(set(got) & set(PARENT))
                self.assertEqual(leaked, [], f"E2.built: {h}: parent variables reached the child: {leaked}")
                self.assertNotIn(FAKE_VALUE, json.dumps(got), "E2.built: a parent value reached the child")
                self.assertNotIn(CANARY_VALUE, json.dumps(got), "E2.built: the canary reached the child")
                vals = self.must("E2.built", m.exec_values, h, "/srv/w/t1/tree")
                self.assertEqual(vals, expected_row(h, "/srv/w/t1/tree"),
                                 f"E2.built: exec_values({h}) is not the row less its credential")

    def inner_for(self, h):
        """Each arm's harness argv. Claude Code's is the box's real launch form (box lane, 14 Oct 2026: since d3fd5305
        exec_argv refuses a Claude turn without its --model and the study's inline --settings), built by the real
        builder, claude_code_adapter.argv, over the module under test (so a witness's run_take builds it too)."""
        if h == "claude-code":
            with filled(), mock.patch.object(CCA, "rt", rt()):
                return CCA.argv("x", model=CLAUDE_MODEL, permission_mode="bypassPermissions", session_id=CLAUDE_SID,
                                first=True)
        return {"codex": ["codex", "exec", "--json", "x"],
                "gemini": ["gemini", "-p", "x", "-m", "gemini-3.5-flash-lite"]}[h]

    def turn(self, h, inner=None, caller=None, environ=None):
        m = rt()
        inner = inner or self.inner_for(h)
        with filled(), mock.patch.dict(os.environ, environ or {}):
            return m.exec_argv(ID, inner, user=m.AGENT_USER, workdir="/srv/w/t1/tree", harness=h,
                               run_tree="/srv/w/t1/tree", login_file=self.login(h),
                               caller_env=dict(CALLER, **(caller or {})))

    def launch_for(self, h):
        """The launcher argv a turn runs in the container (everything after the container id). Codex's exec is
        refused until its subscription binding is built (run_take.CODEX_SUBSCRIPTION_NOT_READY, test_codex_turn_*), so
        its launcher is built by the same launcher_argv over the same exec_values that exec_argv would use."""
        m = rt()
        if h == m.CODEX:          # the no-login launcher (glitch-06, 14 Oct 2026), behind the lease gate held open
            with filled(), mock.patch.object(m, "CODEX_SUBSCRIPTION_READY", True):
                return m.launcher_argv(m.NO_LOGIN, m.exec_values(h, "/srv/w/t1/tree"), self.inner_for(h),
                                       harness=m.CODEX)
        argv, _ = self.turn(h)
        return argv[argv.index(ID) + 1:]

    def test_codex_turn_is_refused_until_its_subscription_binding(self):
        m = rt()
        with mock.patch.object(m, "read_login", side_effect=AssertionError("E2.codex: the login was read")), \
                mock.patch.object(m, "CODEX_SUBSCRIPTION_READY", False):   # the closed gate, pinned (B8-1)
            with self.assertRaises(m.NotReady, msg="E2.codex: a Codex turn was built") as cm:
                self.turn(m.CODEX)
        self.assertIn("subscription", str(cm.exception), "E2.codex: refused for another reason")

    def test_the_turn_hands_the_harness_the_row_alone(self):
        m = rt()
        on_old_list = set(m.API_KEY_VARIABLES) | set(m.BILLING_ROUTE_VARIABLES) | set(m.VENDOR_KEY_VARIABLES) \
            | set(m.SUBSCRIPTION_TOKEN_VARIABLES)
        passable = {k: v for k, v in PARENT.items() if k not in on_old_list}
        self.assertIn("OPENAI_PROJECT", passable, "E2.turn: the test's own parent set is off")
        for h in ARMS:
            if h == m.CODEX:
                # No Codex turn exists until its subscription binding (test_codex_turn_*); its launcher, built from
                # the same exec_values, is held to (c) below exactly as the other arms' are.
                launch = self.must("E2.launcher", self.launch_for, h)
                # no environment login: an API key in the exec's environment is never copied (subscriptions only)
                start = dict(IMAGE_ENV, **PARENT, CODEX_API_KEY=FAKE_VALUE, OPENAI_API_KEY=FAKE_VALUE)
                got = self.must("E2.launcher", run_launcher, launch, start)
                self.assertEqual(got.get("argv"), self.inner_for(h), f"E2.launcher: {h}: the harness argv is off")
                self.assertEqual(got.get("env"), expected_row(h, "/srv/w/t1/tree"),
                                 f"E2.launcher: {h}: the harness does not start with exactly its row, no credential")
                continue
            argv, env = self.must("E2.turn", self.turn, h, caller=passable, environ=passable)
            at = argv.index(ID) + 1
            self.assertEqual(tuple(argv[at:at + len(m.LAUNCHER)]), tuple(m.LAUNCHER),
                             f"E2.turn: {h}'s turn is not run by the launcher")
            head, launcher, name, pairs, inner = self.must("E2.turn", split_turn, argv)
            self.assertEqual(tuple(launcher), tuple(m.LAUNCHER), f"E2.turn: {h}'s turn is not run by the launcher")
            self.assertEqual(head, ["docker", "exec", "--user", m.AGENT_USER, "--workdir", "/srv/w/t1/tree",
                                    "-e", LOGINS[h], ID], f"E2.turn: {h}'s docker part is off")
            self.assertEqual(name, LOGINS[h], f"E2.turn: {h}'s launcher reads another credential")
            self.assertEqual(pairs, expected_row(h, "/srv/w/t1/tree"), f"E2.turn: {h}'s pairs are not the row")
            self.assertEqual(inner[0], {"claude-code": "claude", "codex": "codex", "gemini": "gemini"}[h],
                             "E2.turn: the harness argv is off")
            self.assertNotIn(FAKE_VALUE, " ".join(argv), f"E2.turn: {h}: a value rides in argv")
            self.assertNotIn(CANARY_VALUE, " ".join(argv), f"E2.turn: {h}: the canary rides in argv")
            self.assertEqual(env, dict(CALLER, **{LOGINS[h]: FAKE_VALUE}),
                             f"E2.turn: {h}'s client environment is not the runtime's needs and the credential")
            # (c) the launcher, run in memory from a dirty start: the image's ENV, docker's defaults, every parent name.
            start = dict(IMAGE_ENV, **PARENT, **{LOGINS[h]: FAKE_VALUE})
            got = self.must("E2.launcher", run_launcher, argv[argv.index(ID) + 1:], start)
            self.assertEqual(got.get("argv"), inner, f"E2.launcher: {h}: the harness argv is off")
            self.assertEqual(got.get("env"), dict(expected_row(h, "/srv/w/t1/tree"), **{LOGINS[h]: FAKE_VALUE}),
                             f"E2.launcher: {h}: the harness does not start with exactly the row and its credential")

    def test_an_old_list_name_is_still_refused(self):
        m = rt()
        for h in ARMS:
            for name in ("AWS_BEARER_TOKEN_BEDROCK", "OPENAI_API_KEY", "ANTHROPIC_BASE_URL"):
                if h == m.CODEX:
                    # exec_argv's first environment step for every arm, the refused-name table alone; Codex's exec
                    # stops earlier, at its subscription refusal (test_codex_turn_*).
                    self.refuses("E2.refused", name, m.check_environment, h, dict(CALLER, **{name: FAKE_VALUE}),
                                 set(m.TAKE_ENV[h]))
                else:
                    self.refuses("E2.refused", name, self.turn, h, caller={name: FAKE_VALUE})

    def test_launcher_refuses_container_ancestors_and_current_home(self):
        # These are virtual names only: no protected path is created or inspected.
        for h in ARMS:
            launch = self.launch_for(h)
            home = rt().CONFIG_MOUNT
            for folder in ("/srv/w/t1/tree", "/srv/w/t1", "/srv/w", "/srv", "/", home):
                for name in (".env", ".gemini/.env"):
                    path = os.path.join(folder, name)
                    recorded = {}
                    with self.assertRaisesRegex(SystemExit, re.escape(path), msg="E3.container: env file accepted"):
                        run_launcher(launch, {LOGINS[h]: FAKE_VALUE}, present=(path,), recorded=recorded)
                    self.assertEqual(recorded, {}, "E3.container: harness dispatched before refusal")

    def test_launcher_refuses_env_in_the_agent_home_and_the_config_home(self):
        # R-H5: arm O's and arm G's HOME (the run tree's .home) and their config home (the mount) are each read for a
        # .env before every exec, under both loader names
        m = rt()
        for h in (m.CODEX, m.GEMINI):
            launch = self.launch_for(h)
            for folder, what in (("/srv/w/t1/tree/.home", "HOME"), (m.CONFIG_MOUNT, "the config home")):
                for name in (".env", ".gemini/.env"):
                    path = os.path.join(folder, name)
                    recorded = {}
                    try:
                        run_launcher(launch, {LOGINS[h]: FAKE_VALUE}, present=(path,), recorded=recorded)
                    except SystemExit as e:
                        self.assertIn(path, str(e), f"R-H5.launcher: {h}: refused without naming {path}")
                    else:
                        self.fail(f"R-H5.launcher: {h}: a .env in {what} ({path}) was accepted")
                    self.assertEqual(recorded, {}, "R-H5.launcher: harness dispatched before refusal")

    # R-H1 (glitch-26's ruling on the B11 design note, Mon 19 Oct 2026): with the run tree trusted from turn 1, a
    # codex take's launcher also refuses Codex's project-config paths in the working folder and every ancestor up to /,
    # written here by hand from the pinned source (rust-v0.162.1): .codex/config.toml (config/src/loader/mod.rs 1663-1701,
    # reached from 405-411), .codex/rules (core/src/exec_policy.rs 54 and 678-679), .codex/skills
    # (ext/skills/src/host_roots.rs 25 and 85-91) and .agents/skills (host_roots.rs 24-25 and 154). R-P (glitch-26,
    # lane vendor-b11 round 3) adds .codex/hooks.json (hooks/src/engine/discovery.rs 146-148 and 339-343, through
    # config/src/state.rs 219-243) and .codex/agents (agent-roles/src/loader.rs 75-78).
    CODEX_PROJECT_PATHS = (".codex/config.toml", ".codex/rules", ".codex/skills", ".agents/skills",
                           ".codex/hooks.json", ".codex/agents")
    R_P_PATHS = (".codex/hooks.json", ".codex/agents")
    # R-N1 (glitch-26, lane vendor-b11 round 3, review NIT 1): what each pinned CLI reads from HOME as configuration,
    # written here by hand from the B11 design note's section 4 and the pinned source. Codex (rust-v0.162.1): the user
    # skill root ~/.agents/skills (ext/skills/src/host_roots.rs 24-25, 35-36, 105), the personal marketplace manifests
    # (core-plugins/src/marketplace.rs 20-25, 307-314, 479-480), the primary-runtime marketplace under ~/.cache
    # (core-plugins/src/marketplace_policy.rs 546-572, dirs::cache_dir), and the shell start files its login-shell
    # snapshot reads (core/src/shell_snapshot.rs 586-605; shell-command/src/startup.rs 9-27; a login bash's profile
    # files; zsh's). Gemini CLI (0.64.0): only ~/.gemini/policies/sandbox.toml (chunk-NR7L3FXV.js 257794, sandbox only);
    # it keys everything else on GEMINI_CLI_HOME.
    HOME_CONFIG = {"codex": (".agents/skills", ".agents/plugins/marketplace.json",
                             ".agents/plugins/api_marketplace.json", ".claude-plugin/marketplace.json",
                             ".cursor-plugin/marketplace.json", ".cache/codex-runtimes", ".bashrc", ".bash_profile",
                             ".bash_login", ".profile", ".zshrc", ".zprofile", ".zshenv", ".zlogin"),
                   "gemini": (".gemini/policies/sandbox.toml",)}
    # H5: the agent's own tools' files under HOME stay the agent's
    AGENT_HOME_FILES = (".cache/pip/http/x", ".nextflow/history", ".conda/environments.txt", ".Rhistory",
                        ".bash_history", ".local/bin/tool", ".npm/_cacache/index", ".config/matplotlib/rc")

    def test_codex_launcher_refuses_hooks_and_agents(self):
        m = rt()
        named = tuple("/".join(p) for p in getattr(m, "CODEX_PROJECT_CONFIG_PATHS", ()))
        self.assertEqual([p for p in self.R_P_PATHS if p not in named], [],
                         "R-P.launcher: run_take's codex project-config paths miss .codex/hooks.json or .codex/agents")
        launch = self.launch_for(m.CODEX)
        for cwd in ("/srv/w/t1/tree", "/srv/w/t1/tree/a/b"):
            folders = [cwd]
            while folders[-1] != "/":
                folders.append(os.path.dirname(folders[-1]))
            for folder in folders:
                for name in self.R_P_PATHS:
                    path = os.path.join(folder, name)
                    recorded = {}
                    try:
                        run_launcher(launch, {}, present=(path,), cwd=cwd, recorded=recorded)
                    except SystemExit as e:
                        self.assertIn(path, str(e), f"R-P.launcher: refused without naming {path}")
                    else:
                        self.fail(f"R-P.launcher: a codex turn ran with {path} present (cwd {cwd})")
                    self.assertEqual(recorded, {}, "R-P.launcher: harness dispatched before refusal")

    def test_launcher_refuses_harness_config_in_home(self):
        m = rt()
        table = getattr(m, "HOME_CONFIG_PATHS", None)
        self.assertIsInstance(table, dict, "R-N1.launcher: run_take has no HOME_CONFIG_PATHS")
        self.assertEqual({h: tuple(p for p, _src in table.get(h, ())) for h in (m.CODEX, m.GEMINI)}, self.HOME_CONFIG,
                         "R-N1.launcher: run_take's HOME configuration paths are off the ruled set")
        self.assertEqual(sorted(table), sorted((m.CODEX, m.GEMINI)), "R-N1.launcher: a row other than O and G")
        self.assertEqual([p for h in table for p, src in table[h] if not (isinstance(src, str) and src.strip())], [],
                         "R-N1.launcher: a HOME configuration path without its pinned-source line")
        home = "/srv/w/t1/tree/.home"
        for h in (m.CODEX, m.GEMINI):
            launch = self.launch_for(h)
            start = {LOGINS[h]: FAKE_VALUE} if h != m.CODEX else {}
            for name in self.HOME_CONFIG[h]:
                path = os.path.join(home, name)
                recorded = {}
                try:
                    run_launcher(launch, start, present=(path,), recorded=recorded)
                except SystemExit as e:
                    self.assertIn(path, str(e), f"R-N1.launcher: {h}: refused without naming {path}")
                else:
                    self.fail(f"R-N1.launcher: {h}: a turn ran with {path} in HOME")
                self.assertEqual(recorded, {}, "R-N1.launcher: harness dispatched before refusal")
            # H5: everything else under HOME stays the agent's, and the other CLI's HOME reads are not this row's
            other = self.HOME_CONFIG[m.GEMINI if h == m.CODEX else m.CODEX]
            present = tuple(os.path.join(home, n) for n in self.AGENT_HOME_FILES + other)
            try:
                got = run_launcher(launch, start, present=present)
            except SystemExit as e:
                self.fail(f"R-N1.launcher: {h}: the agent's own HOME files refused the turn: {e}")
            self.assertIn("env", got, f"R-N1.launcher: {h}: a clean turn did not run")
        # arm A: the same names under its HOME (the config mount) leave its launcher as it was
        present = tuple(os.path.join(m.CONFIG_MOUNT, n) for n in self.HOME_CONFIG[m.CODEX] + self.HOME_CONFIG[m.GEMINI])
        try:
            got = run_launcher(self.launch_for(m.CLAUDE_CODE), {LOGINS[m.CLAUDE_CODE]: FAKE_VALUE}, present=present)
        except SystemExit as e:
            self.fail(f"R-N1.launcher: arm A's turn was refused for a vendor HOME path: {e}")
        self.assertIn("env", got, "R-N1.launcher: arm A's turn did not run")

    def test_codex_launcher_refuses_project_config(self):
        m = rt()
        self.assertEqual(tuple("/".join(p) for p in getattr(m, "CODEX_PROJECT_CONFIG_PATHS", ())),
                         self.CODEX_PROJECT_PATHS, "R-H1.launcher: run_take names other codex project-config paths")
        launch = self.launch_for(m.CODEX)
        for cwd in ("/srv/w/t1/tree", "/srv/w/t1/tree/a/b"):
            folders = [cwd]
            while folders[-1] != "/":
                folders.append(os.path.dirname(folders[-1]))
            for folder in folders:
                for name in self.CODEX_PROJECT_PATHS:
                    path = os.path.join(folder, name)
                    recorded = {}
                    try:
                        run_launcher(launch, {}, present=(path,), cwd=cwd, recorded=recorded)
                    except SystemExit as e:
                        self.assertIn(path, str(e), f"R-H1.launcher: refused without naming {path}")
                    else:
                        self.fail(f"R-H1.launcher: a codex turn ran with {path} present (cwd {cwd})")
                    self.assertEqual(recorded, {}, "R-H1.launcher: harness dispatched before refusal")
        got = run_launcher(launch, {}, present=())
        self.assertEqual(got.get("file"), "codex", "R-H1.launcher: a clean codex turn did not run")
        # only for a codex take: the other arms' launchers run with the same paths present
        for h in (m.CLAUDE_CODE, m.GEMINI):
            present = tuple(os.path.join(f, n) for f in ("/srv/w/t1/tree", "/") for n in self.CODEX_PROJECT_PATHS)
            try:
                got = run_launcher(self.launch_for(h), {LOGINS[h]: FAKE_VALUE}, present=present)
            except SystemExit as e:
                self.fail(f"R-H1.launcher: a {h} turn was refused for a codex path: {e}")
            self.assertIn("env", got, f"R-H1.launcher: a {h} turn did not run")

    def test_the_launcher_needs_the_credential(self):
        m = rt()
        for h in ARMS:
            if h == m.CODEX:      # the no-login launcher needs none, and copies none
                got = run_launcher(self.launch_for(h), dict(IMAGE_ENV))
                self.assertEqual(got.get("env"), expected_row(h, "/srv/w/t1/tree"), "E2.launcher: codex: no-login off")
                continue
            with self.assertRaises(KeyError, msg=f"E2.launcher: {h}: a launcher without its credential ran"):
                run_launcher(self.launch_for(h), dict(IMAGE_ENV))
        # harness= is required and the login must be that arm's own (the review of 41428177, MINOR 1); Codex has no
        # named login, so the pairs are held to the rule on Gemini's
        g = {"harness": m.GEMINI}
        self.refuses("E2.pairs", "NAME", m.launcher_argv, "GEMINI_API_KEY", {"bad name": "x"}, ["gemini"], **g)
        self.refuses("E2.pairs", "credential", m.launcher_argv, "GEMINI_API_KEY", {"GEMINI_API_KEY": "x"}, ["gemini"],
                     **g)
        self.refuses("E2.pairs", "NUL", m.launcher_argv, "GEMINI_API_KEY", {"A": "x\0y"}, ["gemini"], **g)
        self.refuses("E2.pairs", "harness", m.launcher_argv, "GEMINI_API_KEY", {"A": "x"}, [], **g)
        self.refuses("E2.pairs", "not the login of", m.launcher_argv, "CODEX_API_KEY", {"A": "x"}, ["codex"],
                     harness=m.CODEX)
        got = self.must("E2.pairs", m.launcher_argv, "GEMINI_API_KEY", {"B": "2", "A": "1=1"}, ["gemini", "x"], **g)
        self.assertEqual(got, [*m.LAUNCHER, "GEMINI_API_KEY", "2", "A=1=1", "B=2", "gemini", "x"],
                         "E2.pairs: the launcher's argv is off")


# ------------------------------------------------------------------------------------------------- E3
class E3EnvFiles(Case):
    def layout(self):
        tree = self.tmp / "tree"
        work = tree / "a" / "b"
        cfg = self.tmp / "cfg"
        for d in (work, cfg):
            d.mkdir(parents=True)
        return tree, work, cfg

    def check(self, where_dir, name, *, tree, work, cfg, clause):
        path = where_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("GOOGLE_GEMINI_BASE_URL=http://synthetic.invalid\n")
        msg = self.refuses(clause, [str(path), ".env"], rt().refuse_env_files, workdir=str(work),
                           run_tree=str(tree), config_dir=str(cfg))
        path.unlink()
        self.must(clause, rt().refuse_env_files, workdir=str(work), run_tree=str(tree), config_dir=str(cfg))
        return msg

    def test_the_working_folder(self):
        tree, work, cfg = self.layout()
        for name in (".env", ".gemini/.env"):
            self.check(work, name, tree=tree, work=work, cfg=cfg, clause="E3.workdir")

    def test_a_parent_below_the_box_root(self):
        tree, work, cfg = self.layout()
        for name in (".env", ".gemini/.env"):
            self.check(work.parent, name, tree=tree, work=work, cfg=cfg, clause="E3.parent")

    def test_the_box_root(self):
        tree, work, cfg = self.layout()
        for name in (".env", ".gemini/.env"):
            self.check(tree, name, tree=tree, work=work, cfg=cfg, clause="E3.root")

    def test_home(self):
        tree, work, cfg = self.layout()
        for name in (".env", ".gemini/.env"):
            msg = self.check(cfg, name, tree=tree, work=work, cfg=cfg, clause="E3.home")
            self.assertIn("HOME", msg, "E3.home: the refusal does not say it is HOME")

    def test_the_agent_home(self):
        # R-H5: arm O's and arm G's HOME is the run tree's .home, read host-side too, whatever the working folder
        tree, work, cfg = self.layout()
        for name in (".env", ".gemini/.env"):
            msg = self.check(tree / ".home", name, tree=tree, work=work, cfg=cfg, clause="R-H5.home")
            self.assertIn("HOME", msg, "R-H5.home: the refusal does not say it is HOME")
            path = tree / ".home" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("X=1\n")
            self.refuses("R-H5.home", str(path), rt().refuse_env_files, workdir=str(work), run_tree=str(tree))
            path.unlink()

    def test_an_arm_a_tree_with_no_home_passes_unchanged(self):
        # R-N2 (glitch-26, lane vendor-b11 round 3; review NIT 2): the stricter host check of <run tree>/.home runs for
        # every harness, and an arm-A run tree (a claude-code checkout, which holds no .home) passes it as before
        tree, work, cfg = self.layout()
        self.assertFalse(os.path.lexists(tree / ".home"), "R-N2.parity: the layout already holds a .home")
        self.must("R-N2.parity", rt().refuse_env_files, workdir=str(work), run_tree=str(tree), config_dir=str(cfg))
        self.must("R-N2.parity", rt().refuse_env_files, workdir=str(tree), run_tree=str(tree))
        self.assertFalse(os.path.lexists(tree / ".home"), "R-N2.parity: the host check made a .home")
        for where in (work, cfg):           # its refusals are the ones it had: a .env in the tree or arm A's HOME
            (where / ".env").write_text("X=1\n")
            self.refuses("R-N2.parity", str(where / ".env"), rt().refuse_env_files, workdir=str(work),
                         run_tree=str(tree), config_dir=str(cfg))
            (where / ".env").unlink()

    def test_a_dangling_link_and_the_shape(self):
        tree, work, cfg = self.layout()
        (work / ".env").symlink_to(self.tmp / "nowhere")
        self.refuses("E3.link", str(work / ".env"), rt().refuse_env_files, workdir=str(work), run_tree=str(tree),
                     config_dir=str(cfg))
        (work / ".env").unlink()
        self.refuses("E3.shape", "inside the run tree", rt().refuse_env_files, workdir=str(self.tmp),
                     run_tree=str(tree), config_dir=str(cfg))
        dirs = self.must("E3.shape", rt().env_file_dirs, str(work), str(tree))
        self.assertEqual(dirs, [str(work), str(work.parent), str(tree)], "E3.shape: the folders read are off")
        (self.tmp / ".env").write_text("X=1\n")        # above the box root: not in the box
        self.must("E3.shape", rt().refuse_env_files, workdir=str(work), run_tree=str(tree), config_dir=str(cfg))

    def test_launch_refuses_before_any_runtime_call(self):
        m = rt()
        tree, work, cfg = self.layout()
        rec = self.tmp / "rec"
        rec.mkdir()
        spec = m.TakeSpec(image="sha256:" + "f" * 64, run_tree=str(tree), config_dir=str(cfg), network="a" * 64,
                          memory_reservation=512, memory=1536, cpus="2", pids_limit=256)
        for where in (tree / ".env", cfg / ".env", cfg / ".gemini" / ".env"):
            where.parent.mkdir(parents=True, exist_ok=True)
            where.write_text("X=1\n")
            fake = FakeRuntime()
            self.refuses("E3.launch", str(where), m.launch, fake, spec, sidecar=None, proxy=None,
                         record_dir=str(rec), caller_env=CALLER)
            self.assertEqual(fake.calls, [], "E3.launch: a runtime call ran before the refusal")
            where.unlink()
        fake = FakeRuntime()
        msg = self.refuses("E3.launch", "proxy", m.launch, fake, spec, sidecar=None, proxy=None,
                           record_dir=str(rec), caller_env=CALLER)
        self.assertNotIn(".env", msg, "E3.launch: a clean take was refused for a .env")

    def test_run_turn_refuses_before_its_exec(self):
        m = rt()
        tree, work, cfg = self.layout()
        (tree / ".env").write_text("X=1\n")
        stream = self.tmp / "stream.jsonl"
        fake = FakeRuntime()
        with filled():
            self.refuses("E3.turn", str(tree / ".env"), m.run_turn, fake, ID, ["claude", "-p", "x"],
                         harness="claude-code", run_tree=str(tree), login_file=self.login("claude-code"),
                         stream_path=str(stream), budget_s=10, clock=lambda: 0.0, caller_env=CALLER)
        self.assertEqual(fake.calls, [], "E3.turn: the exec ran")
        self.assertFalse(stream.exists(), "E3.turn: a stream was written")

    def test_no_take_image_writes_an_env_file(self):
        found = []
        for df in sorted((HERE / "box").rglob("Dockerfile")):
            for i, line in enumerate(df.read_text().splitlines(), 1):
                if re.search(r"(^|[\s/'\"])\.env\b", line):
                    found.append(f"{df.relative_to(HERE)}:{i}")
        self.assertEqual(found, [], "E3.image: a take Dockerfile names a .env file")
        self.assertGreaterEqual(len(list((HERE / "box").rglob("Dockerfile"))), 3, "E3.image: Dockerfiles missing")


# ------------------------------------------------------------------------------------------------- E4
class E4Model(Case):
    def test_a_short_alias_is_refused_by_name(self):
        m = rt()
        for alias, to in GEMINI_ALIASES.items():
            for inner in (["gemini", "-p", "x", "-m", alias], ["gemini", "-p", "x", f"--model={alias}"],
                          ["gemini", "--model", alias, "-p", "x"]):
                msg = self.refuses("E4.alias", [repr(alias), to, "gemini-3.5-flash-lite"], m.check_model, "gemini",
                                   inner)
                self.assertIn("alias", msg, "E4.alias: the refusal does not say it is an alias")

    def test_the_full_ids_pass_and_others_refuse(self):
        m = rt()
        for model in ("gemini-3.5-flash-lite", "gemini-3.8-flash"):
            got = self.must("E4.pinned", m.check_model, "gemini", ["gemini", "-p", "x", "-m", model])
            self.assertEqual(got, model, "E4.pinned: the full id was not returned")
        self.refuses("E4.pinned", "gemini-2.5-flash-lite", m.check_model, "gemini",
                     ["gemini", "-p", "x", "-m", "gemini-2.5-flash-lite"])
        self.refuses("E4.once", "exactly once", m.check_model, "gemini", ["gemini", "-p", "x"])
        self.refuses("E4.once", "exactly once", m.check_model, "gemini",
                     ["gemini", "-m", "gemini-3.8-flash", "-m", "gemini-3.8-flash"])
        self.refuses("E4.once", "exactly once", m.check_model, "gemini", ["gemini", "-p", "x", "-m"])
        for h, inner in (("claude-code", ["claude", "--model", "sonnet"]), ("codex", ["codex", "-m", "flash"])):
            self.assertIsNone(self.must("E4.scope", m.check_model, h, inner), "E4.scope: another call was checked")

    def test_all_gemini_exec_spellings_are_checked(self):
        m = rt()
        with filled(), mock.patch.object(m, "read_login", return_value=FAKE_VALUE):
            for client in ("gemini", "/usr/local/bin/gemini", "/opt/bin/gemini"):
                for args in (["-m", "flash-lite"], ["--model=flash-lite"], ["-m=flash-lite"]):
                    with mock.patch.object(m, "launcher_argv", side_effect=AssertionError("launcher reached")):
                        self.refuses("E4.boundary", "flash-lite", m.exec_argv, ID, [client, *args],
                                     user=m.AGENT_USER, workdir="/virtual/tree", harness="gemini",
                                     run_tree="/virtual/tree", login_file="/virtual/never-read", caller_env=CALLER)
                for args in (["-m", "gemini-3.8-flash"], ["--model=gemini-3.8-flash"], ["-m=gemini-3.8-flash"]):
                    self.assertEqual(m.check_model("gemini", [client, *args]), "gemini-3.8-flash", "E4.boundary")
            for client in ("agent-cli", "./gemini", "bin/gemini", "/usr/bin/env", "sh", "/opt/gemini-wrapper"):
                self.refuses("E4.boundary", "executable", m.check_model, "gemini",
                             [client, "-m", "gemini-3.8-flash"])
            for args in (["-m", "gemini-3.8-flash", "-mflash-lite"],
                         ["-m", "gemini-3.8-flash", "--", "--model", "flash-lite"],
                         ["-m", "gemini-3.8-flash", "-xm", "flash-lite"]):
                self.refuses("E4.boundary", "unsupported", m.check_model, "gemini", ["gemini", *args])

    def test_non_model_options_need_non_flag_values(self):
        m = rt()
        for flag in ("-p", "--prompt", "-o", "--output-format", "--approval-mode", "--resume", "-r"):
            for tail in ([flag], [flag, "-unexpected"], [flag + "=-unexpected"]):
                with self.subTest(flag=flag, tail=tail):
                    self.refuses("E4.values", f"value for {flag!r}", m.check_model, "gemini",
                                 ["gemini", "-m", "gemini-3.8-flash", *tail])

    def test_exec_refuses_an_alias(self):
        m = rt()
        with filled():
            self.refuses("E4.exec", "'flash-lite'", m.exec_argv, ID, ["gemini", "-p", "x", "-m", "flash-lite"],
                         user=m.AGENT_USER, workdir="/srv/w/t1/tree", harness="gemini", run_tree="/srv/w/t1/tree",
                         login_file=self.login("gemini"), caller_env=CALLER)

    def test_the_table_is_the_pre_registered_one(self):
        import build_draft
        m = rt()
        pin = m.MODEL_PINS["gemini"]
        self.assertEqual(tuple(pin["models"]), tuple(build_draft.MODELS["G"]), "E4.table: arm G's ids are off")
        self.assertEqual(pin["short_aliases"], GEMINI_ALIASES, "E4.table: the alias table is off the docs read")
        self.assertEqual((pin["client"], tuple(pin["flags"])), ("gemini", ("-m", "--model")), "E4.table: client")
        self.assertEqual(sorted(m.MODEL_PINS), ["gemini"], "E4.table: another arm pinned without a docs read")


# ------------------------------------------------------------------------------------------------- E5
class E5Units(Case):
    """This lane's functions one at a time: the refusals the end-to-end tests above do not reach."""

    def test_take_environment_refusals(self):
        m = rt()
        with filled():
            for bad in ("fake-second", "", None, "Codex"):
                self.refuses("E5.harness", "unknown harness", m.take_environment, bad, "/r/t")
            self.refuses("E5.tree", "run_tree", m.take_environment, "codex", "r/t")
            with mock.patch.object(m, "RUN_TREE_TMPDIR_VARIABLES", ("TMPDIR", "TMP")):
                self.refuses("E5.tmp", "temporary-folder names", m.take_environment, "codex", "/r/t")
        with mock.patch.object(m, "VENDOR_BILLING_ROUTE_VARIABLES", {m.CODEX: (), m.GEMINI: ()}):
            with mock.patch.object(m, "FALLBACK_ENV", m.PENDING):   # FILLED 14 Oct 2026; the clause stays red-tested
                self.not_ready("E5.pending", "FALLBACK_ENV is PENDING", m.take_environment, "claude-code", "/r/t")
        with mock.patch.object(m, "FALLBACK_ENV", {"FAKE_FALLBACK_A": "1"}):
            # both FILLED 14 Oct 2026 (Codex's binary and Gemini's package sweeps); the clause stays red-tested
            with mock.patch.dict(m.VENDOR_BILLING_ROUTE_VARIABLES, {m.GEMINI: m.PENDING}):
                self.not_ready("E5.pending", "VENDOR_BILLING_ROUTE_VARIABLES['gemini'] is PENDING",
                               m.take_environment, "gemini", "/r/t")

    def test_the_fallback_values_are_arm_a_s_alone(self):
        m = rt()
        with mock.patch.object(m, "FALLBACK_ENV", {"FAKE_FALLBACK_A": "1"}), \
                mock.patch.object(m, "VENDOR_BILLING_ROUTE_VARIABLES", {m.CODEX: (), m.GEMINI: ()}):
            got = self.must("E5.fallback", m.take_environment, "claude-code", "/r/t")
            self.assertEqual(got.get("FAKE_FALLBACK_A"), "1", "E5.fallback: arm A lacks its fallback value")
            self.assertEqual(set(got) - set(expected_row("claude-code", "/r/t")),
                             {"FAKE_FALLBACK_A", "CLAUDE_CODE_OAUTH_TOKEN"}, "E5.fallback: arm A's names are off")
            for h in ("codex", "gemini"):
                self.assertNotIn("FAKE_FALLBACK_A", self.must("E5.fallback", m.take_environment, h, "/r/t"),
                                 f"E5.fallback: {h} carries arm A's fallback value")
        for name in ("PATH", "HOME", "CLAUDE_CODE_OAUTH_TOKEN"):
            with mock.patch.object(m, "FALLBACK_ENV", {name: "x"}):
                self.refuses("E5.fallback", f"may not override {name}", m.take_environment, "claude-code", "/r/t")

    def test_launcher_argv_refusals(self):
        m = rt()
        for login in (None, 5, "bad name", "lower"):
            self.refuses("E5.login", "credential is named", m.launcher_argv, login, {"A": "1"}, ["gemini"],
                         harness=m.GEMINI)
        for value in (5, None, b"x"):
            self.refuses("E5.value", "NUL", m.launcher_argv, "GEMINI_API_KEY", {"A": value}, ["gemini"],
                         harness=m.GEMINI)

    def test_the_no_login_launcher_reads_its_values(self):
        """The merged battery's generated sweep (gap4-merge-66bacad): the no-login launcher's own branches, bound here
        (glitch-06, 14 Oct 2026). The lease gate refuses first; then only a Codex row; then no other harness's config
        home, by name; then exactly the Codex row's names; and a named login's harness must be a known one."""
        m = rt()
        vals = m.exec_values(m.CODEX, "/srv/w/t1/tree")
        inner = ["codex", "exec"]
        with mock.patch.object(m, "CODEX_SUBSCRIPTION_READY", False):   # the closed gate refuses first (B8-1)
            self.not_ready("E5.nologin", "Codex subscription binding not ready", m.launcher_argv, m.NO_LOGIN, vals,
                           inner, harness=m.CODEX)
        with mock.patch.object(m, "CODEX_SUBSCRIPTION_READY", True):
            got = self.must("E5.nologin", m.launcher_argv, m.NO_LOGIN, vals, inner, harness=m.CODEX)
            self.assertEqual(got[:len(m.LAUNCHER) + 1], [*m.LAUNCHER, "-"], "E5.nologin: the launcher is off")
            for h in (m.CLAUDE_CODE, m.GEMINI, "bogus"):
                self.refuses("E5.nologin", "only for a Codex row", m.launcher_argv, m.NO_LOGIN, vals, inner, harness=h)
            for home in ("GEMINI_CLI_HOME", "CLAUDE_CONFIG_DIR"):
                self.refuses("E5.nologin", ["config home", home], m.launcher_argv, m.NO_LOGIN,
                             dict(vals, **{home: m.CONFIG_MOUNT}), inner, harness=m.CODEX)
            self.refuses("E5.nologin", "exactly the Codex row's names", m.launcher_argv, m.NO_LOGIN,
                         dict(vals, EXTRA_NAME="1"), inner, harness=m.CODEX)
            self.refuses("E5.nologin", "exactly the Codex row's names", m.launcher_argv, m.NO_LOGIN,
                         {k: v for k, v in vals.items() if k != "CODEX_HOME"}, inner, harness=m.CODEX)
        self.refuses("E5.harness", "unknown harness", m.launcher_argv, "GEMINI_API_KEY", {"A": "1"}, ["gemini"],
                     harness="bogus")

    def test_check_model_edges(self):
        m = rt()
        for inner in ([], ()):
            self.refuses("E5.model", "executable", m.check_model, "gemini", inner)

    def test_home_must_be_the_config_mount(self):
        m = rt()
        tree = self.tmp / "tree"
        tree.mkdir()
        cfg = self.tmp / "cfg"
        cfg.mkdir()
        for h in ARMS:
            bad = dict(m.TAKE_ENV, **{h: dict(m.TAKE_ENV[h], HOME="/home/dana")})
            with mock.patch.object(m, "TAKE_ENV", bad):
                self.refuses("E5.home", "HOME is neither the config mount nor the run tree's home",
                             m.refuse_env_files, workdir=str(tree), run_tree=str(tree), config_dir=str(cfg))
                self.must("E5.home", m.refuse_env_files, workdir=str(tree), run_tree=str(tree))


class AgentHomeResidual(Case):
    def test_r_h5_is_in_the_drafts_box_residuals(self):
        """R-H5's named difference from arm A is pre-registered with the study's box limitations."""
        draft = json.loads((HERE / "prereg-draft.json").read_text(encoding="utf-8"))
        rows = [r for r in draft["box_residuals"] if r.get("name") == "arm O and G HOME"]
        self.assertEqual(len(rows), 1, "R-H5.residual: the draft holds no one 'arm O and G HOME' entry")
        for words in ("<run tree>/.home", "CODEX_HOME", "GEMINI_CLI_HOME", "config mount", "arm A",
                      "byte-unchanged", "git-excluded", ".agents/skills", ".bashrc"):
            self.assertIn(words, rows[0]["text"], f"R-H5.residual: the entry does not say {words!r}")
        self.assertIn("R-H5", rows[0]["ruling"], "R-H5.residual")
        self.assertIn("tests/test_env_allowlist.py", rows[0]["closed_check"], "R-H5.residual")


# ------------------------------------------------------------------------------------------------- witnesses
def mutants() -> dict:
    """name -> (clause, old text in box/run_take.py, new text). Each weakens one guard; old occurs exactly once."""
    return {
        "env-from-caller": ("E2.built", "    out = {}\n    for name, value in TAKE_ENV[harness].items():",
                            "    out = {k: v for k, v in os.environ.items() if k.startswith('OPENAI_')}\n"
                            "    for name, value in TAKE_ENV[harness].items():"),
        "row-base-dropped": ("E1.table", '    CODEX: {"PATH": TAKE_PATH, "HOME": RUN_TREE_HOME, "LANG": TAKE_LANG,\n',
                             '    CODEX: {"PATH": TAKE_PATH, "HOME": RUN_TREE_HOME,\n'),
        "home-elsewhere": ("E1.table", '    GEMINI: {"PATH": TAKE_PATH, "HOME": RUN_TREE_HOME,',
                           '    GEMINI: {"PATH": TAKE_PATH, "HOME": "/home/dana",'),
        # R-H5 (lane vendor-b11 round 2): the agent's own HOME for arms O and G, arm A's row by its bytes
        "agent-home-on-mount": ("E1.table", '    CODEX: {"PATH": TAKE_PATH, "HOME": RUN_TREE_HOME,',
                                '    CODEX: {"PATH": TAKE_PATH, "HOME": CONFIG_MOUNT,'),
        "claude-home-moved": ("R-H5.parity", '    CLAUDE_CODE: {"PATH": TAKE_PATH, "HOME": CONFIG_MOUNT,',
                              '    CLAUDE_CODE: {"PATH": TAKE_PATH, "HOME": RUN_TREE_HOME,'),
        "claude-row-respaced": ("R-H5.parity", '"CLAUDE_CODE_OAUTH_TOKEN": CREDENTIAL},',
                                '"CLAUDE_CODE_OAUTH_TOKEN":  CREDENTIAL},'),
        "home-marker-unfilled": ("E2.built", ', RUN_TREE_HOME: f"{tree}/{RUN_TREE_HOMEDIR}"}', "}"),
        # re-anchored, R-H5-1 (the walk reads HOME and the config home as two folders, each with its ancestors)
        "env-agent-home-unchecked": ("R-H5.launcher", "+homes+[e['HOME']]", "+homes"),
        "env-config-home-unchecked": ("R-H5.launcher",
                                      "starts=([e['CODEX_HOME']] if 'CODEX_HOME' in e else [])+[os.getcwd()]+homes+",
                                      "starts=[os.getcwd()]+"),
        "host-agent-home-unchecked": ("R-H5.home", "        if os.path.lexists(os.path.join(home, name)):",
                                      "        if False:"),
        "home-check-widened": ("E5.home", "            if row.get(\"HOME\") not in (CONFIG_MOUNT, RUN_TREE_HOME):",
                               "            if row.get(\"HOME\") not in (CONFIG_MOUNT, RUN_TREE_HOME, \"/home/dana\"):"),
        "values-in-client-env": ("E2.turn", "    env[login] = value\n", "    env[login] = value\n"
                                 "    env.update(values)\n"),
        "no-launcher": ("E2.turn", "            container_id, *launcher_argv(login, values, inner, harness=harness)]",
                        "            container_id, *inner]"),
        "launcher-keeps-env": ("E2.launcher", "                   \"e=dict(x.split('=',1) for x in a[2:2+n])\\n\"",
                               "                   \"e=dict(os.environ,**dict(x.split('=',1) for x in a[2:2+n]))\\n\""),
        # R-H1 (lane vendor-b11 round 2): the codex launcher's project-config refusal, one guard at a time
        "codex-project-unchecked": ("R-H1.launcher", " if found: raise SystemExit('refusing codex project",
                                    " if False: raise SystemExit('refusing codex project"),  # re-anchored, R-N1
        "codex-project-cwd-only": ("R-H1.launcher", "for d in up for p in", "for d in up[:1] for p in"),
        "codex-project-config-dropped": ("R-H1.launcher", "(os.path.join(d,'.codex','config.toml'),", "("),
        "codex-project-rules-dropped": ("R-H1.launcher", "os.path.join(d,'.codex','rules'),", ""),
        "codex-project-skills-dropped": ("R-H1.launcher", "os.path.join(d,'.codex','skills'),", ""),
        "codex-project-agents-dropped": ("R-H1.launcher", "os.path.join(d,'.agents','skills'),", ""),  # re-anchored, R-P
        "codex-project-every-arm": ("R-H1.launcher", "if 'CODEX_HOME' in e:", "if True:"),
        "codex-project-no-arm": ("R-H1.launcher", "if 'CODEX_HOME' in e:", "if 'CODEX_HOME' in os.environ:"),
        # R-P and R-N1 (lane vendor-b11 round 3): the codex project's hooks and agents, each CLI's HOME configuration
        "codex-project-hooks-dropped": ("R-P.launcher", "os.path.join(d,'.codex','hooks.json'),", ""),
        "codex-project-agents-folder-dropped": ("R-P.launcher", "\"os.path.join(d,'.codex','agents')) if",
                                                "\") if"),
        "home-config-unchecked": ("R-N1.launcher", "  if found: raise SystemExit('refusing harness configuration",
                                  "  if False: raise SystemExit('refusing harness configuration"),
        "home-config-first-only": ("R-N1.launcher", "for p in ps if", "for p in ps[:1] if"),
        "home-config-gemini-dropped": ("R-N1.launcher",
                                       "f\"('GEMINI_CLI_HOME',{tuple(p for p, _s in HOME_CONFIG_PATHS[GEMINI])!r})):\\n\"",
                                       "\"('GEMINI_CLI_HOME',())):\\n\""),
        "home-config-every-arm": ("R-N1.launcher", "                   \" if v in e:\\n\"",
                                  "                   \" if True:\\n\""),
        "home-config-bashrc-dropped": ("R-N1.launcher", "        (\".bashrc\", \"shell-command", "        (\".bashrcX\", \"shell-command"),
        "host-agent-home-required": ("R-N2.parity",
                                     "    home = os.path.join(_abs_path(run_tree, \"run_tree\"), RUN_TREE_HOMEDIR)\n",
                                     "    home = os.path.join(_abs_path(run_tree, \"run_tree\"), RUN_TREE_HOMEDIR)\n"
                                     "    if not os.path.isdir(home):\n        found.append('no HOME at ' + home)\n"),
        "container-env-unchecked": ("E3.container", "  if os.path.lexists(p): raise SystemExit", "  if False: raise SystemExit"),
        "pairs-unchecked": ("E2.pairs", "        if not _NAME.fullmatch(k):", "        if False:"),
        "launch-no-env-check": ("E3.launch", "    refuse_env_files(workdir=spec.run_tree, run_tree=spec.run_tree, "
                                "config_dir=spec.config_dir)\n", ""),
        "turn-no-env-check": ("E3.turn", "    refuse_env_files(workdir=run_tree, run_tree=run_tree)\n", ""),
        "home-unchecked": ("E3.home", "    if config_dir is not None:", "    if False:"),
        "gemini-name-dropped": ("E3.workdir", 'ENV_FILE_NAMES = (".env", os.path.join(".gemini", ".env"))',
                                'ENV_FILE_NAMES = (".env",)'),
        "root-not-read": ("E3.root", "for i in range(len(parts), -1, -1)]", "for i in range(len(parts), 0, -1)]"),
        "alias-unchecked": ("E4.alias", "    if model in pin[\"short_aliases\"]:", "    if False:"),
        "any-id": ("E4.pinned", "    if model not in pin[\"models\"]:", "    if False:"),
        "gemini-executable-unbound": ("E4.boundary", "    if not inner or not (inner[0] == pin[\"client\"] or", "    if False and not (inner[0] == pin[\"client\"] or"),
        "exec-no-model-check": ("E4.exec", "    check_model(harness, inner)\n", ""),
    }


METHOD = {
    "env-from-caller": "E2Allowlist.test_take_environment_is_the_row_alone",
    "row-base-dropped": "E1Table.test_each_row_is_the_ruling_s_set",
    "home-elsewhere": "E1Table.test_each_row_is_the_ruling_s_set",
    "values-in-client-env": "E2Allowlist.test_the_turn_hands_the_harness_the_row_alone",
    "no-launcher": "E2Allowlist.test_the_turn_hands_the_harness_the_row_alone",
    "launcher-keeps-env": "E2Allowlist.test_the_turn_hands_the_harness_the_row_alone",
    "container-env-unchecked": "E2Allowlist.test_launcher_refuses_container_ancestors_and_current_home",
    "agent-home-on-mount": "E1Table.test_each_row_is_the_ruling_s_set",
    "claude-home-moved": "E1Table.test_arm_a_row_is_byte_unchanged",
    "claude-row-respaced": "E1Table.test_arm_a_row_is_byte_unchanged",
    "home-marker-unfilled": "E2Allowlist.test_take_environment_is_the_row_alone",
    "env-agent-home-unchecked": "E2Allowlist.test_launcher_refuses_env_in_the_agent_home_and_the_config_home",
    "env-config-home-unchecked": "E2Allowlist.test_launcher_refuses_env_in_the_agent_home_and_the_config_home",
    "host-agent-home-unchecked": "E3EnvFiles.test_the_agent_home",
    "home-check-widened": "E5Units.test_home_must_be_the_config_mount",
    **{name: "E2Allowlist.test_codex_launcher_refuses_project_config" for name in (
        "codex-project-unchecked", "codex-project-cwd-only", "codex-project-config-dropped",
        "codex-project-rules-dropped", "codex-project-skills-dropped", "codex-project-agents-dropped",
        "codex-project-every-arm", "codex-project-no-arm")},
    **{name: "E2Allowlist.test_codex_launcher_refuses_hooks_and_agents" for name in (
        "codex-project-hooks-dropped", "codex-project-agents-folder-dropped")},
    **{name: "E2Allowlist.test_launcher_refuses_harness_config_in_home" for name in (
        "home-config-unchecked", "home-config-first-only", "home-config-gemini-dropped", "home-config-every-arm",
        "home-config-bashrc-dropped")},
    "host-agent-home-required": "E3EnvFiles.test_an_arm_a_tree_with_no_home_passes_unchanged",
    "pairs-unchecked": "E2Allowlist.test_the_launcher_needs_the_credential",
    "launch-no-env-check": "E3EnvFiles.test_launch_refuses_before_any_runtime_call",
    "turn-no-env-check": "E3EnvFiles.test_run_turn_refuses_before_its_exec",
    "home-unchecked": "E3EnvFiles.test_home",
    "gemini-name-dropped": "E3EnvFiles.test_the_working_folder",
    "root-not-read": "E3EnvFiles.test_the_box_root",
    "alias-unchecked": "E4Model.test_a_short_alias_is_refused_by_name",
    "any-id": "E4Model.test_the_full_ids_pass_and_others_refuse",
    "gemini-executable-unbound": "E4Model.test_all_gemini_exec_spellings_are_checked",
    "exec-no-model-check": "E4Model.test_exec_refuses_an_alias",
}
WITNESSES = {name: (METHOD[name], m[0]) for name, m in mutants().items()}

# Generated mutants this module does not kill that are equivalent, each with a reason a reviewer can check.
EQUIVALENT: dict = {}


def generate():
    import walk_mutation
    with mock.patch.dict(walk_mutation.ROAD, {MODULE: ROAD_FUNCTIONS}, clear=True):
        return walk_mutation.generate_module(MODULE, SOURCE.read_text())


def by_id() -> dict:
    return {m.id: m for m in generate()[0]}


class G1Generated(Case):
    def test_the_equivalent_list_matches_the_generated_mutants(self):
        ids = set(self.must("G1.generated", by_id))
        self.assertGreater(len(ids), 0, "G1.generated: the generator produced nothing")
        self.assertEqual(sorted(set(EQUIVALENT) - ids), [], "G1.generated: EQUIVALENT entries that name no mutant")
        bare = sorted(k for k, why in EQUIVALENT.items() if not isinstance(why, str) or len(why.strip()) < 12)
        self.assertEqual(bare, [], "G1.generated: EQUIVALENT entries without a reason")
        fns = {i.split(":")[0].split(".", 1)[1] for i in ids}
        self.assertEqual(fns, set(ROAD_FUNCTIONS), "G1.generated: a road function made no mutant")


GENERATED_ORDER = ("E1Table", "E5Units", "E4Model", "E2Allowlist", "E3EnvFiles", "G1Generated")


def _outcome(stdout):
    record = re.findall(r"^test_env_allowlist outcomes: (\{.*\})$", stdout, re.M)
    return json.loads(record[-1]) if record else None


def run_witnesses(names) -> int:
    chosen = names or sorted(WITNESSES)
    import mutation_baseline  # lane t104-mutation-baseline: the unmutated selection runs first; a red one refuses (exit 3), nothing counted
    mutation_baseline.require_green("test_env_allowlist witnesses", [sys.executable, "-B", "-W", "ignore", str(Path(__file__).resolve()),
                                    *sorted({WITNESSES[x][0] for x in chosen})], timeout=1800, tag="test_env_allowlist")
    red = 0
    for name in chosen:
        method, clause = WITNESSES[name]
        got = subprocess.run([sys.executable, "-B", "-W", "ignore", str(Path(__file__).resolve()), "--mutant", name,
                              method], capture_output=True, text=True, timeout=110)
        outcome = _outcome(got.stdout)
        blocks = re.findall(r"^FAIL: (\w+) \(__main__\.(\w+)\.\w+\)[^\n]*\n(.*?)(?=^=|^Ran |\Z)", got.stderr,
                            re.M | re.S)
        attributed = any(f"{cls}.{test}" == method and "AssertionError" in body and
                         re.search(r"(?<![\w:.-])" + re.escape(clause) + r"(?![\w.-])", body)
                         for test, cls, body in blocks)
        clean = bool(outcome) and set(outcome["failures"]) == {method} and outcome["errors"] == [] \
            and outcome["skipped"] == []
        passed = attributed and clean and got.returncode != 0
        print(f"witness {name} -> {method} {clause}: {'RED' if passed else 'FAIL'}", flush=True)
        if not passed:
            print(got.stdout[-3000:] + got.stderr[-3000:], flush=True)
            return 1
        red += 1
    print(f"test_env_allowlist witnesses: {red}/{len(chosen)} red; registry {len(WITNESSES)}", flush=True)
    return 0


def run_generated(shard=None, sample=None, timeout=600, only=None) -> int:
    mutants_all, dropped = generate()
    chosen = list(enumerate(mutants_all))
    if shard:
        i, n = shard
        chosen = [(k, m) for k, m in chosen if k % n == i - 1]
    if sample:
        chosen = chosen[::sample]
    if only is not None:
        chosen = [(k, m) for k, m in chosen if m.id in only]
    import mutation_baseline  # lane t104-mutation-baseline: the unmutated selection runs first; a red one refuses (exit 3), nothing counted
    mutation_baseline.require_green("test_env_allowlist generated mutants", [sys.executable, "-B", "-W", "ignore", str(Path(__file__).resolve()), *GENERATED_ORDER],
                                    timeout=timeout, tag="test_env_allowlist")
    killed, survived, equivalent, listed_killed, inconclusive = [], [], [], [], []

    def one(mid, fast):
        argv = [sys.executable, "-B", "-W", "ignore", str(Path(__file__).resolve()), "--gen-mutant", mid]
        got = subprocess.run(argv + (["--failfast"] if fast else []), capture_output=True, text=True,
                             timeout=timeout)
        return got, _outcome(got.stdout)

    for _, m in chosen:
        try:
            got, outcome = one(m.id, True)
            if outcome is not None and not outcome["failures"] and outcome["errors"]:
                got, outcome = one(m.id, False)
        except subprocess.TimeoutExpired:
            inconclusive.append(m.id)
            print(f"generated {m.id}: TIMEOUT (inconclusive)", flush=True)
            continue
        if outcome is None:
            inconclusive.append(m.id)
            print(f"generated {m.id}: NO OUTCOME (rc {got.returncode})\n{got.stderr[-1500:]}", flush=True)
            continue
        if outcome["failures"]:
            killed.append(m.id)
            state = "KILLED"
            if m.id in EQUIVALENT:
                listed_killed.append(m.id)
        elif m.id in EQUIVALENT:
            equivalent.append(m.id)
            state = "EQUIVALENT"
        else:
            survived.append(m.id)
            state = "SURVIVED"
        print(f"generated {m.id}: {state} by {outcome['failures'][:1]} (errors {len(outcome['errors'])}) "
              f"[{m.kind} at line {m.line}: {m.original[:60]!r} -> {m.replacement[:40]!r}]", flush=True)
    print(f"test_env_allowlist generated mutants: {len(mutants_all)} generated ({dropped} dropped, not compiling), "
          f"{len(chosen)} run, {len(killed)} killed, {len(equivalent)} equivalent (listed), {len(survived)} "
          f"survived unlisted, {len(listed_killed)} listed but killed, {len(inconclusive)} inconclusive", flush=True)
    for name, ids in (("SURVIVED (unlisted)", survived), ("LISTED BUT KILLED", listed_killed),
                      ("INCONCLUSIVE", inconclusive)):
        for x in ids:
            print(f"  {name}: {x}", flush=True)
    return 0 if not survived and not listed_killed and not inconclusive else 1


if __name__ == "__main__":
    if "--generated-mutants" in sys.argv:
        shard = sample = None
        if "--shard" in sys.argv:
            a, b = sys.argv[sys.argv.index("--shard") + 1].split("/")
            shard = (int(a), int(b))
            if not 1 <= shard[0] <= shard[1]:
                raise SystemExit("--shard i/n with 1 <= i <= n")
        if "--sample" in sys.argv:
            sample = int(sys.argv[sys.argv.index("--sample") + 1])
        per = int(sys.argv[sys.argv.index("--timeout") + 1]) if "--timeout" in sys.argv else 600
        only = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None
        raise SystemExit(run_generated(shard, sample, per, only))
    failfast = "--failfast" in sys.argv
    if failfast:
        sys.argv.remove("--failfast")
    if "--gen-mutant" in sys.argv:
        index = sys.argv.index("--gen-mutant")
        GENERATED = sys.argv[index + 1]
        del sys.argv[index:index + 2]
        if len(sys.argv) == 1:
            sys.argv += list(GENERATED_ORDER)
    if "--witnesses" in sys.argv:
        raise SystemExit(run_witnesses(sys.argv[sys.argv.index("--witnesses") + 1:]))
    if "--mutant" in sys.argv:
        index = sys.argv.index("--mutant")
        SELECTED = sys.argv[index + 1]
        if SELECTED not in WITNESSES:
            raise SystemExit(f"unknown mutant {SELECTED!r}")
        del sys.argv[index:index + 2]
    result = unittest.main(verbosity=2, exit=False, failfast=failfast).result
    ids = lambda pairs: [t.id().removeprefix("__main__.").split(" ")[0] for t, _ in pairs]  # noqa: E731
    print(f"test_env_allowlist: {result.testsRun} run, {len(result.failures)} failures, "
          f"{len(result.errors)} errors, {len(result.skipped)} skipped")
    print("test_env_allowlist outcomes: " + json.dumps({"failures": ids(result.failures),
                                                       "errors": ids(result.errors),
                                                       "skipped": ids(result.skipped)}))
    raise SystemExit(0 if result.wasSuccessful() else 1)
