#!/usr/bin/env python3
"""box/take_config.py: each harness's per-take config files carry D8's values verbatim (read back with tomllib and
json), refuse while a value is PENDING, carry no key and no study word, and hash for the freeze.

No test reaches a real process: the guard below is armed after the one leak-word read (interface 16). Each guard is
also run against in-memory mutants, printed with their red results.
"""

from __future__ import annotations

import contextlib
import inspect
import json
import os
import re
import subprocess
import sys
import tempfile
import tomllib
import unittest
from unittest import mock

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
REPO = os.path.dirname(os.path.dirname(HERE))
ROUND3 = "e2979b3143081824aadea73523ec41af30c1ddb1"
LANE_LEAD_WORDS = ("gap4", "round 4", "sidecar", "watcher", "evidence", "holdout", "sealed", "probe", "trap",
                   "grader")


def _round3_leak_words() -> tuple:
    """Round 3's pre-registration key leak_words, that key alone, read once (interface 16). Never committed."""
    shown = subprocess.run(["git", "-C", REPO, "show", f"{ROUND3}:evals/gap-study-3/prereg.json"],
                           capture_output=True, check=True)
    return tuple(json.loads(shown.stdout)["leak_words"])


LEAK_WORDS = _round3_leak_words() + LANE_LEAD_WORDS


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


def _module_set_up_extra():
    pass


def _module_tear_down_extra():
    pass

from box import take_config as tc  # noqa: E402
from box import run_take as rt  # noqa: E402

FAKE_VALUE = "FAKEVALUE-0123456789abcdef-PLANTED"


@contextlib.contextmanager
def filled():
    """Every PENDING value, filled in memory only (interface 15), with test-only stand-ins."""
    with mock.patch.object(tc, "CLAUDE_BYPASS_KEY", "skipDangerousModePermissionPrompt"), \
            mock.patch.object(tc, "CODEX_REASONING_EFFORT", "medium"), \
            mock.patch.object(tc, "GEMINI_THINKING", {"path": "model.thinkingLevel", "value": "default"}), \
            mock.patch.object(tc, "GEMINI_AUTH_SETTING", {"path": "security.auth.selectedType",
                                                          "value": "api-key-stand-in"}), \
            mock.patch.object(tc, "GEMINI_SETTINGS_PATH", ".gemini/settings.json"):
        yield


def problems_of(fn):
    try:
        return list(fn())
    except Exception as exc:
        return [f"raised {type(exc).__name__}: {exc}"]


class MutantCase(unittest.TestCase):
    def assert_green_then_red(self, check, mutants):
        self.assertEqual(problems_of(check), [], "the guard is red on the real module")
        for name, ctx in mutants:
            with ctx():
                got = problems_of(check)
            print(f"  mutant {name}: {'red' if got else 'GREEN (survived)'}{' - ' + got[0][:100] if got else ''}")
            self.assertNotEqual(got, [], f"mutant {name} survived")


def patched(obj, attr, value):
    return lambda: mock.patch.object(obj, attr, value)


def get(doc, dotted):
    for p in dotted.split("."):
        doc = doc[p]
    return doc


def written(harness, model):
    d = tempfile.mkdtemp(prefix="w-")
    with filled():
        rec = tc.write(d, harness, model=model)
    return d, rec


class TestGuard(unittest.TestCase):
    def test_the_guard_starts_no_patch_at_import(self):
        """Recorded at the very end of this module's import: no guarded name was patched then. Inside a test every
        guarded name holds the tripwire (setUpModule armed it), so the record can see a patch."""
        self.assertEqual(_PATCHED_AT_IMPORT, [])
        self.assertEqual(len(_patched_now()), len(GUARDED))

    def test_guard_is_armed(self):
        with self.assertRaises(ProcessGuardTripped):
            subprocess.run(["true"])

    def test_module_is_this_rounds(self):
        self.assertTrue(os.path.abspath(tc.__file__).startswith(os.path.join(HERE, "box") + os.sep))


class TestContents(MutantCase):
    def check(self):
        out = []
        d, rec = written(tc.CODEX, "gpt-6.1-sol")
        with open(os.path.join(d, "config.toml"), "rb") as fh:
            doc = tomllib.load(fh)
        want = {"model": "gpt-6.1-sol", "model_reasoning_effort": "medium", "web_search": "disabled",
                "project_doc_fallback_filenames": ["CLAUDE.md"], "check_for_update_on_startup": False,
                # The renderer fold (owner amendment, 13 Oct): Codex reads a ChatGPT subscription login from a
                # file store; no API-key route.
                "forced_login_method": "chatgpt", "cli_auth_credentials_store": "file",
                "features": {"hooks": False}}
        if doc != want:
            out.append(f"codex config.toml reads {doc}")
        d, rec = written(tc.GEMINI, "gemini-3.8-flash")
        with open(os.path.join(d, ".gemini", "settings.json")) as fh:
            doc = json.load(fh)
        want = {"tools.exclude": ["google_web_search", "web_fetch"], "context.fileName": ["CLAUDE.md"],
                "hooksConfig.enabled": False, "general.enableAutoUpdate": False,
                "general.enableAutoUpdateNotification": False, "privacy.usageStatisticsEnabled": False,
                "telemetry.enabled": False, "model.name": "gemini-3.8-flash", "model.thinkingLevel": "default",
                "security.auth.selectedType": "api-key-stand-in",
                # The frozen legacy noninteractive path (pinned 0.64.0 evidence; the renderer fold).
                "experimental.adk.agentSessionNoninteractiveEnabled": False}
        for k, v in want.items():
            try:
                if get(doc, k) != v:
                    out.append(f"gemini {k} = {get(doc, k)!r}")
            except (KeyError, TypeError):
                out.append(f"gemini {k} missing")
        n = sum(1 for _ in _leaves(doc))
        if n != len(want):
            out.append(f"gemini settings hold {n} values, not {len(want)}")
        d, rec = written(tc.CLAUDE_CODE, None)
        with open(os.path.join(d, "settings.json")) as fh:
            doc = json.load(fh)
        # The bypass acceptance and, since glitch-06's ruling of 14 Oct 2026, switchModelsOnFlag false; no fallbackModel.
        if doc != {"skipDangerousModePermissionPrompt": True, "switchModelsOnFlag": False}:
            out.append(f"claude settings hold {doc}, not the bypass acceptance and switchModelsOnFlag false")
        if "fallbackModel" in doc:
            out.append("claude settings configure a fallback model")
        for fixed in ((("switchModelsOnFlag", True),), (("switchModelsOnFlag", False), ("fallbackModel", "x"))):
            with filled(), mock.patch.object(tc, "CLAUDE_FIXED_SETTINGS", fixed):
                try:
                    tc.files_for(tc.CLAUDE_CODE, model=None)
                    out.append(f"claude settings {fixed} were rendered")
                except tc.Refused:
                    pass
        if rec["files"] != ["settings.json"] or len(rec["sha256"]) != 64:
            out.append("the write record is off")
        return out

    def test_contents(self):
        self.assert_green_then_red(self.check, [
            ("web-search-on", patched(tc, "CODEX_TOP", (("web_search", "live"),) + tc.CODEX_TOP[1:])),
            ("hooks-on", patched(tc, "CODEX_FEATURES", (("hooks", True),))),
            ("codex-login-store", patched(tc, "CODEX_TOP", tc.CODEX_TOP[:-1] + (("cli_auth_credentials_store",
                                                                                  "ephemeral"),))),
            ("codex-login-method", patched(tc, "CODEX_TOP", tc.CODEX_TOP[:-2] + (("forced_login_method", "api"),)
                                           + tc.CODEX_TOP[-1:])),
            ("gemini-web-fetch", patched(tc, "GEMINI_SETTINGS", (("tools.exclude", ["google_web_search"]),)
                                         + tc.GEMINI_SETTINGS[1:])),
            ("gemini-telemetry", patched(tc, "GEMINI_SETTINGS", tc.GEMINI_SETTINGS[:-1])),
            ("gemini-extra", patched(tc, "GEMINI_SETTINGS", tc.GEMINI_SETTINGS + (("general.vimMode", True),))),
            ("claude-extra", lambda: mock.patch.dict(tc.WRITERS, {tc.CLAUDE_CODE: lambda m: {
                "settings.json": b'{"a": 1, "skipDangerousModePermissionPrompt": true}\n'}})),
            ("model-dropped", patched(tc, "GEMINI_MODEL_PATH", "model.alias")),
            ("switch-models-on-flag-true", patched(tc, "CLAUDE_FIXED_SETTINGS", (("switchModelsOnFlag", True),))),
            ("switch-guard-dropped", patched(tc, "CLAUDE_FIXED_SETTINGS", ())),
            ("fallback-model-present", lambda: mock.patch.dict(tc.WRITERS, {tc.CLAUDE_CODE: lambda m: {
                "settings.json": b'{"fallbackModel": "x", "skipDangerousModePermissionPrompt": true, '
                                 b'"switchModelsOnFlag": false}\n'}})),
        ])

    def test_refusals(self):
        with filled():
            for h, m in ((tc.CODEX, None), (tc.CODEX, 'x" = 1\n[y]'), (tc.GEMINI, ""), (tc.CLAUDE_CODE, "m")):
                with self.assertRaises(tc.Refused):
                    tc.files_for(h, model=m)
            for h in ("fake-second", None):
                with self.assertRaises(tc.Refused):
                    tc.files_for(h, model="m")
            d = tempfile.mkdtemp(prefix="w-")
            open(os.path.join(d, "stale"), "w").close()
            with self.assertRaises(tc.Refused):
                tc.write(d, tc.CODEX, model="m")
            repo = tempfile.mkdtemp(prefix="w-")
            os.makedirs(os.path.join(repo, ".git"))
            cfg = os.path.join(repo, "cfg")
            os.makedirs(cfg)
            with self.assertRaises(tc.Refused):
                tc.write(cfg, tc.CODEX, model="m")


def _leaves(doc):
    if isinstance(doc, dict):
        for v in doc.values():
            yield from _leaves(v)
    else:
        yield doc


class TestPending(MutantCase):
    # GEMINI_SETTINGS_PATH is measured at the pinned 0.64.0 (Storage.getGlobalSettingsPath; the renderer fold).
    EXPECT = {"CLAUDE_BYPASS_KEY", "CODEX_REASONING_EFFORT", "GEMINI_THINKING", "GEMINI_AUTH_SETTING"}

    def check(self):
        out = []
        if set(tc.pending()) != self.EXPECT:
            out.append(f"pending() = {sorted(tc.pending())}")
        for h, m in ((tc.CLAUDE_CODE, None), (tc.CODEX, "gpt-6-luna"), (tc.GEMINI, "gemini-3.5-flash-lite")):
            d = tempfile.mkdtemp(prefix="w-")
            try:
                tc.write(d, h, model=m)
                out.append(f"{h} config written while PENDING")
            except tc.NotReady:
                pass
            if os.listdir(d):
                out.append(f"{h}: a refused write left a file")
        return out

    def test_pending(self):
        self.assert_green_then_red(self.check, [
            ("no-ready-gate", patched(tc, "_ready", lambda h: None)),
            ("needs-dropped", patched(tc, "NEEDS", {tc.CLAUDE_CODE: (), tc.CODEX: (), tc.GEMINI: ()})),
            ("bypass-filled", patched(tc, "CLAUDE_BYPASS_KEY", "k")),
        ])

    def test_no_parameter_overrides_a_pending_constant(self):
        def overriding(config_dir, *, bypass_key=None):
            return None
        overriding.__module__ = tc.__name__
        self.assert_green_then_red(self.check_no_override, [
            ("override-parameter", lambda: mock.patch.object(tc, "write_with", overriding, create=True)),
        ])

    def check_no_override(self):
        names = {k.lower() for k in self.EXPECT} | {"bypass_key", "reasoning_effort", "effort", "thinking", "auth",
                                                    "auth_type", "settings_path", "key", "api_key", "token", "login"}
        found = []
        for name, fn in vars(tc).items():
            if callable(fn) and not name.startswith("_") and getattr(fn, "__module__", "") == tc.__name__:
                try:
                    found += [f"{name}({p})" for p in inspect.signature(fn).parameters if p.lower() in names]
                except (TypeError, ValueError):
                    pass
        return found


class TestHashAndNames(MutantCase):
    def check_hash(self):
        out = []
        a, ra = written(tc.CODEX, "gpt-6.1-sol")
        b, rb = written(tc.CODEX, "gpt-6.1-sol")
        if ra["sha256"] != rb["sha256"] or tc.config_sha256(a) != ra["sha256"]:
            out.append("the hash is not deterministic")
        c, rc = written(tc.CODEX, "gpt-6-luna")
        if rc["sha256"] == ra["sha256"]:
            out.append("the hash does not see the model")
        with open(os.path.join(a, "sessions.log"), "w") as fh:
            fh.write("x")
        if tc.config_sha256(a) == ra["sha256"]:
            out.append("the hash does not see an added file")
        renamed, _ = written(tc.CODEX, "gpt-6.1-sol")
        os.rename(os.path.join(renamed, "config.toml"), os.path.join(renamed, "config2.toml"))
        if tc.config_sha256(renamed) == ra["sha256"]:
            out.append("the hash does not see a renamed file")
        os.symlink("/etc/hosts", os.path.join(b, "link"))
        try:
            tc.config_sha256(b)
            out.append("a link was hashed")
        except tc.Refused:
            pass
        return out

    def test_hash(self):
        self.assert_green_then_red(self.check_hash, [
            ("digests-only", patched(tc, "config_sha256", lambda f: __import__("hashlib").sha256("".join(sorted(
                __import__("hashlib").sha256(open(os.path.join(r, n), "rb").read()).hexdigest()
                for r, _, ns in os.walk(f) for n in ns)).encode()).hexdigest())),
            ("names-only", patched(tc, "config_sha256", lambda f: __import__("hashlib").sha256(
                "\n".join(sorted(os.listdir(f))).encode()).hexdigest())),
        ])

    def check_names(self):
        out = []
        for h, m in ((tc.CLAUDE_CODE, None), (tc.CODEX, "gpt-6.1-sol"), (tc.GEMINI, "gemini-3.8-flash")):
            with filled():
                files = tc.files_for(h, model=m)
            for rel, data in files.items():
                text = rel + "\n" + data.decode("ascii")
                hits = [w for w in LEAK_WORDS if re.search(r"(?<![A-Za-z0-9])" + re.escape(w) + r"(?![A-Za-z0-9])",
                                                           text, re.IGNORECASE)]
                if hits:
                    out.append(f"{h} {rel} carries {hits}")
                if FAKE_VALUE in text:
                    out.append(f"{h} {rel} carries a key")
        if set(tc.WRITERS) != set(rt.LOGIN_VARIABLE):
            out.append("WRITERS does not hold exactly the harnesses of run_take")
        return out

    def test_names(self):
        self.assert_green_then_red(self.check_names, [
            ("study-word", patched(tc, "CODEX_FEATURES", (("hooks", False), ("sidecar", False)))),
            ("key-in-file", patched(tc, "CODEX_TOP", tc.CODEX_TOP + (("api_key", FAKE_VALUE),))),
            ("writer-missing", patched(tc, "WRITERS", {tc.CODEX: tc._codex, tc.GEMINI: tc._gemini})),
        ])


# Taken last, after every import-time statement of this module: must be empty (setUpModule arms the guard).
_PATCHED_AT_IMPORT = _patched_now()


if __name__ == "__main__":
    unittest.main(verbosity=2)
