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
    """Every once-PENDING value, replaced in memory only (interface 15) by test-only stand-ins, so the renderer is read
    on values no source gives (round 17 B6: the real ones, sourced by R3, are bound by TestR3Values). The effort is
    per model; "m" is the stand-in model of the refusal tests, so their refusal is the folder's, never the model's."""
    with mock.patch.object(tc, "CODEX_REASONING_EFFORT", {"gpt-6.1-sol": "medium", "gpt-6-luna": "medium",
                                                          "m": "medium"}), \
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


# R-H1 (glitch-26's ruling on the B11 design note, Mon 19 Oct 2026): a codex take's config.toml names its run tree.
RUN_TREE = "/srv/w/run-0a1b2c3d"


def written(harness, model, run_tree=RUN_TREE):
    d = tempfile.mkdtemp(prefix="w-")
    with filled():
        rec = tc.write(d, harness, model=model, run_tree=run_tree)
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


# Round 17 B6 (glitch-b5's ruling R3, Sun 18 Oct 2026): the three once-PENDING values, each the harness's default for
# that model at the pinned version, read statically from the pinned package (no model call, no network); the record
# take_config keeps beside them (VALUE_SOURCES), as the executor read it.
GEMINI_PKG = {"package": "@google/gemini-cli", "version": "0.64.0",
              "tarball_sha256": "891a794e55c8319b6b78f6f8f13d6b8b2782a4709dfd2fcabf3a1f63ae8365e6"}
R3_SOURCES = {
    "CODEX_REASONING_EFFORT": {
        "package": "openai/codex", "tag": "rust-v0.162.1", "commit": "092d3acd6bec3e3a14bdc7e7a2810ab628ab759d",
        "file": "codex-rs/models-manager/models.json", "lines": {"gpt-6.1-sol": 213, "gpt-6-luna": 560},
        "read": "each model entry's default_reasoning_level; the file is the bundled catalog "
                "(include_str!, codex-rs/models-manager/src/lib.rs line 15)"},
    "GEMINI_THINKING": dict(GEMINI_PKG, file="bundle/chunk-NR7L3FXV.js",
                            file_sha256="d566e81b1df8d4d44a91bf7aeea96a58ec0e6c8934fa424315ef060507dcbb8c",
                            lines={"chat-base-3": 362280, "gemini-3.5-flash-lite": 362349, "gemini-3.8-flash": 362361,
                                   "ThinkingLevel.HIGH": 258475, "customAliases kept": 380852},
                            setting_file="bundle/chunk-FLKY6NH5.js",
                            setting_file_sha256="f6a4ddd46350dad40515218069d369aaa0025f194c552400b69925b941098bc8",
                            setting_line=13409,
                            read="both arm G models extend the built-in alias chat-base-3, whose thinkingLevel is "
                                 "HIGH (packages/core/src/config/defaultModelConfigs.ts); settings.json's "
                                 "modelConfigs.customAliases replaces an alias by name, so the built-in chat-base-3 is "
                                 "restated as it is"),
    "GEMINI_AUTH_SETTING": dict(GEMINI_PKG, file="bundle/chunk-FLKY6NH5.js",
                                file_sha256="f6a4ddd46350dad40515218069d369aaa0025f194c552400b69925b941098bc8",
                                line=14183, value_file="bundle/chunk-NR7L3FXV.js", value_line=312750,
                                read="security.auth.selectedType (packages/cli/src/config/settingsSchema.ts), set to "
                                     "AuthType.USE_GEMINI, the API-key auth type"),
    # Round 18 B9 (glitch-26's ruling B9, Sun 18 Oct 2026, from the held walk w-g1's exit 55): folder trust defaults on
    # at the pinned version, so a headless take in a folder Gemini CLI does not trust stops before any model call.
    "GEMINI_TRUST_SETTING": dict(GEMINI_PKG, file="bundle/chunk-FLKY6NH5.js",
                                 file_sha256="f6a4ddd46350dad40515218069d369aaa0025f194c552400b69925b941098bc8",
                                 line=9599, check_file="bundle/gemini-6ESINPDZ.js",
                                 check_file_sha256="19950cab8f7bd8b48ea89c4ede22418b2e5d836d9c1554baed62c9019d74810b",
                                 check_lines={"folder trust off: the check returns": 11129,
                                              "headless and untrusted: FatalUntrustedWorkspaceError (exit 55)": 11137},
                                 read="security.folderTrust.enabled defaults to true (settings.security?.folderTrust"
                                      "?.enabled ?? true), although docs/cli/trusted-folders.md calls the feature off "
                                      "by default; with it on, a headless run in an untrusted folder throws "
                                      "FatalUntrustedWorkspaceError, exit 55 "
                                      "(gemini-cli-core dist/src/utils/errors.js); "
                                      "set to false, the startup check returns before any trust lookup"),
}
R3_VALUES = {
    "CODEX_REASONING_EFFORT": {"gpt-6.1-sol": "low", "gpt-6-luna": "medium"},
    "GEMINI_THINKING": {"path": "modelConfigs.customAliases", "value": {"chat-base-3": {
        "extends": "chat-base", "modelConfig": {"generateContentConfig": {"thinkingConfig": {"thinkingLevel": "HIGH"}}}}}},
    "GEMINI_AUTH_SETTING": {"path": "security.auth.selectedType", "value": "gemini-api-key"},
    "GEMINI_TRUST_SETTING": {"path": "security.folderTrust.enabled", "value": False},
}


class TestR3Values(MutantCase):
    """R3: each once-PENDING value is the statically sourced one, recorded with its package, file and line, and the
    configs written with them carry it (and D8's other values, tools.exclude among them)."""

    def check(self):
        out = []
        for name, want in R3_VALUES.items():
            if getattr(tc, name, None) != want:
                out.append(f"{name} is {getattr(tc, name, None)!r}, not the sourced {want!r}")
        if getattr(tc, "VALUE_SOURCES", None) != R3_SOURCES:
            out.append("take_config.VALUE_SOURCES is not the record of R3's static reads")
        if tc.pending():
            out.append(f"still pending: {sorted(tc.pending())}")
        with open(os.path.join(HERE, "prereg-draft.json"), encoding="utf-8") as fh:
            models = json.load(fh)["models"]
        if sorted(tc.CODEX_REASONING_EFFORT) != sorted(models["O"]):
            out.append("the efforts are not for exactly arm O's models")
        for m in models["O"]:
            d = tempfile.mkdtemp(prefix="w-")
            tc.write(d, tc.CODEX, model=m)
            with open(os.path.join(d, "config.toml"), "rb") as fh:
                doc = tomllib.load(fh)
            if doc.get("model_reasoning_effort") != R3_VALUES["CODEX_REASONING_EFFORT"][m] or doc.get("model") != m:
                out.append(f"{m}'s config.toml reads effort {doc.get('model_reasoning_effort')!r}")
        try:
            tc.files_for(tc.CODEX, model="gpt-5.4")
            out.append("a codex config was written for a model with no sourced effort")
        except tc.Refused:
            pass
        for m in models["G"]:
            d = tempfile.mkdtemp(prefix="w-")
            tc.write(d, tc.GEMINI, model=m)
            with open(os.path.join(d, ".gemini", "settings.json")) as fh:
                doc = json.load(fh)
            if doc.get("modelConfigs") != {"customAliases": R3_VALUES["GEMINI_THINKING"]["value"]} or \
                    doc.get("security") != {"auth": {"selectedType": "gemini-api-key"},
                                            "folderTrust": {"enabled": False}} or \
                    doc.get("tools") != {"exclude": ["google_web_search", "web_fetch"]} or \
                    doc.get("model") != {"name": m}:
                out.append(f"{m}'s settings.json reads {doc}")
        return out

    def test_r3_values(self):
        self.assert_green_then_red(self.check, [
            ("efforts swapped", patched(tc, "CODEX_REASONING_EFFORT", {"gpt-6.1-sol": "medium", "gpt-6-luna": "low"})),
            ("one model's effort dropped", patched(tc, "CODEX_REASONING_EFFORT", {"gpt-6.1-sol": "low"})),
            ("thinking LOW", patched(tc, "GEMINI_THINKING", {"path": "modelConfigs.customAliases", "value": {
                "chat-base-3": {"extends": "chat-base", "modelConfig": {"generateContentConfig": {
                    "thinkingConfig": {"thinkingLevel": "LOW"}}}}}})),
            ("thinking at another path", patched(tc, "GEMINI_THINKING", {"path": "model.thinkingLevel",
                                                                         "value": "HIGH"})),
            ("auth by OAuth", patched(tc, "GEMINI_AUTH_SETTING", {"path": "security.auth.selectedType",
                                                                  "value": "oauth-personal"})),
            ("folder trust left on", lambda: mock.patch.object(tc, "GEMINI_TRUST_SETTING", {
                "path": "security.folderTrust.enabled", "value": True}, create=True)),
            ("sources dropped", patched(tc, "VALUE_SOURCES", {})),
            ("a source's line moved", lambda: mock.patch.dict(tc.VALUE_SOURCES, {"GEMINI_AUTH_SETTING": dict(
                R3_SOURCES["GEMINI_AUTH_SETTING"], line=14184)})),
            ("tools.exclude dropped", patched(tc, "GEMINI_SETTINGS", tc.GEMINI_SETTINGS[1:])),
        ])


class TestContents(MutantCase):
    def check(self):
        out = []
        d, rec = written(tc.CODEX, "gpt-6.1-sol")
        with open(os.path.join(d, "config.toml"), "rb") as fh:
            doc = tomllib.load(fh)
        # R-6 (glitch-b5's ruling of 17 Oct 2026; lane vendor-admission T4 P2): no instruction-file name is configured
        want = {"model": "gpt-6.1-sol", "model_reasoning_effort": "medium", "web_search": "disabled",
                "check_for_update_on_startup": False,
                # The renderer fold (owner amendment, 13 Oct): Codex reads a ChatGPT subscription login from a
                # file store; no API-key route.
                "forced_login_method": "chatgpt", "cli_auth_credentials_store": "file",
                "features": {"hooks": False},
                # R-H1: the run tree trusted up front, so Codex never rewrites the file
                "projects": {RUN_TREE: {"trust_level": "trusted"}}}
        if doc != want:
            out.append(f"codex config.toml reads {doc}")
        d, rec = written(tc.GEMINI, "gemini-3.8-flash")
        with open(os.path.join(d, ".gemini", "settings.json")) as fh:
            doc = json.load(fh)
        want = {"tools.exclude": ["google_web_search", "web_fetch"],          # R-6: no context.fileName
                "hooksConfig.enabled": False, "general.enableAutoUpdate": False,
                "general.enableAutoUpdateNotification": False, "privacy.usageStatisticsEnabled": False,
                "telemetry.enabled": False, "model.name": "gemini-3.8-flash", "model.thinkingLevel": "default",
                "security.auth.selectedType": "api-key-stand-in",
                "security.folderTrust.enabled": False,         # round 18 B9: folder trust off (glitch-26's ruling B9)
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
        if doc != {}:   # the bypass acceptance RULED not required in -p (glitch-06, 14 Oct 2026): nothing to carry
            out.append(f"claude settings hold {doc}, not nothing")
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


class TestCodexTrustTable(MutantCase):
    """R-H1 (glitch-26's ruling on the B11 design note, Mon 19 Oct 2026). At the pinned Codex 0.162.1 a thread start
    whose project has no trust_level, in a git checkout, with the bypass flag's full access, writes
    [projects."<run tree>"] trust_level = "trusted" into config.toml (app-server/src/request_processors/
    thread_processor.rs 1362-1378; core/src/config/mod.rs 2359-2441). take_config places that table up front, keyed by
    the run tree as project_trust_key spells it (config/src/loader/mod.rs 1381-1412: dunce::canonicalize, imported as
    normalize_path at line 61; lowercased on Windows only), so Codex finds trust_level set on turn 1, never rewrites
    the file, and its bytes stay take_config's on every turn."""

    TABLE = f'\n[projects."{RUN_TREE}"]\ntrust_level = "trusted"\n'

    def check(self):
        out = []
        with filled():
            plain = tc.files_for(tc.CODEX, model="gpt-6.1-sol")[tc.CODEX_CONFIG]
            files = tc.files_for(tc.CODEX, model="gpt-6.1-sol", run_tree=RUN_TREE)
        if sorted(files) != [tc.CODEX_CONFIG]:
            out.append(f"R-H1.table: a codex take writes {sorted(files)}")
            return out
        data = files[tc.CODEX_CONFIG]
        if data != plain + self.TABLE.encode("ascii"):
            out.append(f"R-H1.table: config.toml does not end in the one trust table: {data[-120:]!r}")
        doc = tomllib.loads(data.decode("ascii"))
        if doc.get("projects") != {RUN_TREE: {"trust_level": "trusted"}}:
            out.append(f"R-H1.table: the projects table reads {doc.get('projects')!r}")
        d, rec = written(tc.CODEX, "gpt-6.1-sol")
        with open(os.path.join(d, tc.CODEX_CONFIG), "rb") as fh:
            if fh.read() != data:
                out.append("R-H1.write: write placed other bytes than files_for with the run tree")
        if rec["files"] != [tc.CODEX_CONFIG]:
            out.append(f"R-H1.write: the record lists {rec['files']}")
        # the other harnesses' files do not depend on the run tree
        for h, m in ((tc.GEMINI, "gemini-3.8-flash"), (tc.CLAUDE_CODE, None)):
            with filled():
                if tc.files_for(h, model=m, run_tree=RUN_TREE) != tc.files_for(h, model=m):
                    out.append(f"R-H1.table: {h}'s files changed with the run tree")
        # a codex write without its run tree would leave Codex to rewrite config.toml on turn 1: refused
        try:
            with filled():
                tc.write(tempfile.mkdtemp(prefix="w-"), tc.CODEX, model="gpt-6.1-sol")
            out.append("R-H1.write: a codex config was written without its run tree")
        except tc.Refused as e:
            if "run tree" not in str(e):
                out.append(f"R-H1.write: refused without naming the run tree: {e}")
        # the key is the canonical spelling, or Codex's lookup misses it and writes its own table
        link_parent = tempfile.mkdtemp(prefix="w-")
        os.makedirs(os.path.join(link_parent, "real", "run-0a1b2c3d"))
        os.symlink(os.path.join(link_parent, "real"), os.path.join(link_parent, "via"))
        for bad in ("srv/w/run-0a1b2c3d", "/srv/w/run-0a1b2c3d/", "/srv/w/../w/run-0a1b2c3d", "/srv//w/run-0a",
                    "//srv/w/run-0a1b2c3d", "/", '/srv/w/t"]\n[x', "/srv/w/t\nx", "/srv/w/r\u00e9", None, 7,
                    os.path.join(link_parent, "via", "run-0a1b2c3d")):
            try:
                with filled():
                    tc.files_for(tc.CODEX, model="gpt-6.1-sol", run_tree=bad)
                out.append(f"R-H1.key: run tree {bad!r} was admitted")
            except tc.Refused:
                pass
        with filled():
            real = os.path.join(link_parent, "real", "run-0a1b2c3d")
            if os.path.realpath(real) == real:
                got = tomllib.loads(tc.files_for(tc.CODEX, model="gpt-6.1-sol", run_tree=real)[tc.CODEX_CONFIG]
                                    .decode("ascii"))
                if got.get("projects") != {real: {"trust_level": "trusted"}}:
                    out.append("R-H1.key: a canonical run tree was keyed otherwise")
        return out

    def test_the_trust_table(self):
        self.assert_green_then_red(self.check, [
            ("table-dropped", patched(tc, "_codex_trust_table", lambda run_tree: b"")),
            ("untrusted", patched(tc, "CODEX_TRUST_LEVEL", "untrusted")),
            ("key-not-canonical", patched(tc, "codex_project_key", lambda run_tree: run_tree)),
            ("write-without-run-tree", patched(tc, "CODEX_NEEDS_RUN_TREE", False)),
        ])


class TestPending(MutantCase):
    # GEMINI_SETTINGS_PATH is measured at the pinned 0.64.0 (Storage.getGlobalSettingsPath; the renderer fold).
    # CLAUDE_BYPASS_KEY RULED not required in -p (glitch-06, 14 Oct 2026): Claude Code's config is ready.
    # Round 17 B6 (glitch-b5's ruling R3, Sun 18 Oct 2026): CODEX_REASONING_EFFORT, GEMINI_THINKING and
    # GEMINI_AUTH_SETTING are sourced statically from the pinned packages, so nothing is pending; this assertion moves
    # by that ruling (it read the three as pending), and the refusal while any is PENDING is read by putting each back.
    EXPECT = set()
    ONCE_PENDING = ("CODEX_REASONING_EFFORT", "GEMINI_THINKING", "GEMINI_AUTH_SETTING")

    def check(self):
        out = []
        if set(tc.pending()) != self.EXPECT:
            out.append(f"pending() = {sorted(tc.pending())}")
        if tc.CLAUDE_BYPASS_KEY != rt.CLAUDE_BYPASS_KEY or tc.CLAUDE_BYPASS_NOT_REQUIRED != rt.CLAUDE_BYPASS_NOT_REQUIRED:
            out.append(f"take_config's bypass value is not run_take's ruled one: {tc.CLAUDE_BYPASS_KEY!r}")
        d = tempfile.mkdtemp(prefix="w-")
        rec = tc.write(d, tc.CLAUDE_CODE, model=None)
        with open(os.path.join(d, "settings.json"), "rb") as fh:
            if fh.read() != b"{}\n" or rec["files"] != ["settings.json"]:
                out.append("claude-code's per-take settings are not the empty document")
        for bad in ("skipDangerousModePermissionPrompt", "k"):
            with mock.patch.object(tc, "CLAUDE_BYPASS_KEY", bad):
                try:
                    tc.files_for(tc.CLAUDE_CODE, model=None)
                    out.append(f"claude-code config written with bypass value {bad!r}")
                except tc.Refused:
                    pass
        with mock.patch.object(tc, "CLAUDE_BYPASS_KEY", tc.PENDING):
            try:
                tc.files_for(tc.CLAUDE_CODE, model=None)
                out.append("claude-code config written while the bypass ruling is PENDING")
            except tc.NotReady:
                pass
        for name in self.ONCE_PENDING:
            h, m = (tc.CODEX, "gpt-6-luna") if name.startswith("CODEX") else (tc.GEMINI, "gemini-3.5-flash-lite")
            d = tempfile.mkdtemp(prefix="w-")
            with mock.patch.object(tc, name, tc.PENDING):
                if name not in tc.pending():
                    out.append(f"{name} put back to PENDING is not pending")
                try:
                    tc.write(d, h, model=m)
                    out.append(f"{h} config written while {name} is PENDING")
                except tc.NotReady:
                    pass
            if os.listdir(d):
                out.append(f"{h}: a refused write left a file")
        return out

    def test_pending(self):
        self.assert_green_then_red(self.check, [
            ("no-ready-gate", patched(tc, "_ready", lambda h: None)),
            ("needs-dropped", patched(tc, "NEEDS", {tc.CLAUDE_CODE: (), tc.CODEX: (), tc.GEMINI: ()})),
            ("bypass-key-re-added", patched(tc, "CLAUDE_BYPASS_KEY", "skipDangerousModePermissionPrompt")),
            ("bypass-key-written", lambda: mock.patch.dict(tc.WRITERS, {tc.CLAUDE_CODE: lambda m: {
                "settings.json": b'{"skipDangerousModePermissionPrompt": true}\n'}})),
            ("bypass-unmirrored", patched(tc, "CLAUDE_BYPASS_KEY", "RULED: something else")),
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
