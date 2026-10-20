#!/usr/bin/env python3
"""box/take_config.py: each harness's per-take config files carry D8's values verbatim (read back with tomllib and
json), refuse while a value is PENDING, carry no key and no study word, and hash for the freeze.

No test reaches a real process: the guard below is armed after the one leak-word read (interface 16). Each guard is
also run against in-memory mutants, printed with their red results.
"""

from __future__ import annotations

import contextlib
import copy
import inspect
import json
import os
import re
import subprocess
import sys
import tempfile
import tomllib
import types
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
    # R-B9 (lane vendor-b11 round 3): the check's citation is the running chain's main bundle, gemini-Q2GRYIAK.js (the
    # bin, bundle/gemini.js line 110, imports it), never the orphan build gemini-6ESINPDZ.js.
    "GEMINI_TRUST_SETTING": dict(GEMINI_PKG, file="bundle/chunk-FLKY6NH5.js",
                                 file_sha256="f6a4ddd46350dad40515218069d369aaa0025f194c552400b69925b941098bc8",
                                 line=9599, check_file="bundle/gemini-Q2GRYIAK.js",
                                 check_file_sha256="7702da31cf099ca3e1d64fd195f15b7726b2c2829ec21e955558eb9dbfba47da",
                                 check_lines={"folder trust off: the check returns": 11145,
                                              "headless and untrusted: FatalUntrustedWorkspaceError (exit 55)": 11153},
                                 exit55_file="bundle/chunk-NR7L3FXV.js",
                                 exit55_file_sha256="d566e81b1df8d4d44a91bf7aeea96a58ec0e6c8934fa424315ef060507dcbb8c",
                                 exit55_line=252702, unreached_check_file="bundle/gemini-6ESINPDZ.js",
                                 unreached_check_file_sha256=("19950cab8f7bd8b48ea89c4ede22418b2e5d836d9c1554baed6"
                                                              "2c9019d74810b"),
                                 unreached_check_lines={
                                     "folder trust off: the check returns": 11129,
                                     "headless and untrusted: FatalUntrustedWorkspaceError (exit 55)": 11137},
                                 unreached_exit55={"file": "bundle/chunk-J7SXW2FI.js", "line": 252715, "file_sha256":
                                                   "e2aca15290b02dc9845704f3fed44c577919652508624f340974f0ff588f206e"},
                                 read="security.folderTrust.enabled defaults to true (settings.security?.folderTrust"
                                      "?.enabled ?? true), although docs/cli/trusted-folders.md calls the feature off "
                                      "by default; with it on, a headless run in an untrusted folder throws "
                                      "FatalUntrustedWorkspaceError, exit 55 (super(message, 55) at exit55_file "
                                      "exit55_line, in the running bundle: bundle/gemini.js line 110 loads "
                                      "gemini-Q2GRYIAK.js, which imports chunk-NR7L3FXV.js; unreached_check_file "
                                      "and unreached_exit55 are a second copy no bundle file imports); "
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
        # Lane vendor-b14 round 2 (R-B14-1, R-B14-2): the record gains the helper aliases' and the exclusion's reads.
        # Lane vendor-b22 (glitch-26's ruling B22-10): and the [agents] switch's read, recorded in its own test module.
        if getattr(tc, "VALUE_SOURCES", None) != dict(R3_SOURCES, **B14_SOURCES, **B18_SOURCES, **B22_SOURCES):
            out.append("take_config.VALUE_SOURCES is not the record of R3's static reads")
        if tc.pending():
            out.append(f"still pending: {sorted(tc.pending())}")
        with open(os.path.join(HERE, "prereg-draft.json"), encoding="utf-8") as fh:
            models = json.load(fh)["models"]
        if sorted(tc.CODEX_REASONING_EFFORT) != sorted(models["O"]):
            out.append("the efforts are not for exactly arm O's models")
        for m in models["O"]:
            d = tempfile.mkdtemp(prefix="w-")
            tc.write(d, tc.CODEX, model=m, run_tree=RUN_TREE)
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
            # R-B14-1 and R-B14-2 move these two: chat-base-3 beside the repointed helper aliases, invoke_agent excluded.
            if doc.get("modelConfigs") != {"customAliases": b14_aliases(m)} or \
                    doc.get("security") != {"auth": {"selectedType": "gemini-api-key"},
                                            "folderTrust": {"enabled": False}} or \
                    doc.get("tools") != {"exclude": B14_EXCLUDE} or \
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


# Lane vendor-b14 round 2 (glitch-26's rulings R-B14-1 and R-B14-2, Mon 19 Oct 2026; practice walk w-g5 held on
# result.stats.models naming helper models): every helper alias the pinned 0.64.0 reaches under arm G's settings is
# repointed at the row's model through modelConfigs.customAliases, each restating its built-in entry's other fields,
# and tools.exclude gains invoke_agent; loop detection stays on (no model.disableLoopDetection is written).
B14_ALIASES = {"gemini-3-flash-base": {"extends": "base"}, "loop-detection-double-check": {"extends": "base"},
               "chat-compression-3-flash": {}, "chat-compression-default": {}, "agent-history-provider-summarizer": {}}
B14_ROW_ALIASES = {"gemini-3.8-flash": {}, "gemini-3.5-flash-lite": {"chat-compression-3.1-flash-lite": {}}}
B14_EXCLUDE = ["google_web_search", "web_fetch", "invoke_agent"]
# Where each was read in the pinned package, as the executor read it (VALUE_SOURCES).
B14_SOURCES = {
    "GEMINI_HELPER_ALIASES": dict(GEMINI_PKG, file="bundle/chunk-NR7L3FXV.js",
                                  file_sha256="d566e81b1df8d4d44a91bf7aeea96a58ec0e6c8934fa424315ef060507dcbb8c",
                                  lines={"gemini-3-flash-base": 362386, "loop-detection-double-check": 362490,
                                         "chat-compression-3-flash": 362522, "chat-compression-3.1-flash-lite": 362527,
                                         "chat-compression-default": 362547,
                                         "agent-history-provider-summarizer": 362552},
                                  model_lines={"gemini-3-flash-base": 362389, "loop-detection-double-check": 362493,
                                               "chat-compression-3-flash": 362524,
                                               "chat-compression-3.1-flash-lite": 362529,
                                               "chat-compression-default": 362549,
                                               "agent-history-provider-summarizer": 362554},
                                  use_lines={"gemini-3-flash-base": 345269, "loop-detection extends it": 362487,
                                             "loop-detection called": 344226,
                                             "loop-detection-double-check": 343867,
                                             "compression alias by the chat's model": 337195,
                                             "chat-compression-3-flash for gemini-3.8-flash": 337044,
                                             "chat-compression-3.1-flash-lite for gemini-3.5-flash-lite": 337051,
                                             "chat-compression-default for any other model": 337060,
                                             "agent-history-provider-summarizer": 344635,
                                             "agent-history-provider-summarizer, tool output": 348760},
                                  layer_lines={"customAliases over the built-in aliases": 342156,
                                               "customAliases kept": 380852, "the alias's model wins": 342295},
                                  setting_file="bundle/chunk-FLKY6NH5.js",
                                  setting_file_sha256="f6a4ddd46350dad40515218069d369aaa0025f194c552400b69925b941098bc8",
                                  setting_line=13409, loop_detection_setting_line=13371,
                                  read="each built-in helper alias the run can reach, its model, and where it is "
                                       "used; settings.json's modelConfigs.customAliases replaces a built-in alias "
                                       "by name, so each entry restates the built-in's extends (gemini-3-flash-base "
                                       "and loop-detection-double-check extend base, the compression and summarizer "
                                       "aliases extend nothing) with the row's model; loop-detection, llm-edit-fixer "
                                       "and next-speaker-checker extend gemini-3-flash-base and follow it; "
                                       "model.disableLoopDetection (default false) is not written"),
    "GEMINI_AGENT_EXCLUSION": dict(GEMINI_PKG, file="bundle/chunk-NR7L3FXV.js",
                                   file_sha256="d566e81b1df8d4d44a91bf7aeea96a58ec0e6c8934fa424315ef060507dcbb8c",
                                   lines={'var AGENT_TOOL_NAME = "invoke_agent";': 283421,
                                          "maybeRegister(AgentTool,": 382849,
                                          "getActiveTools leaves out the excluded tools": 313466},
                                   setting_file="bundle/chunk-FLKY6NH5.js",
                                   setting_file_sha256=("f6a4ddd46350dad40515218069d369aaa0025f194c552400b69925b"
                                                        "941098bc8"),
                                   setting_line=13925, cli_file="bundle/gemini-Q2GRYIAK.js",
                                   cli_file_sha256="7702da31cf099ca3e1d64fd195f15b7726b2c2829ec21e955558eb9dbfba47da",
                                   cli_line=8674,
                                   read="tools.exclude (a list of tool names, merged into the CLI's excluded tools) "
                                        "with invoke_agent, the subagent tool's name, so the registry never offers "
                                        "it; the plan's vendor side counts zero Agent calls by construction"),
}


def b14_aliases(row) -> dict:
    """The customAliases a row's placed settings carry: R3's restated chat-base-3 and every helper alias, repointed."""
    want = copy.deepcopy(R3_VALUES["GEMINI_THINKING"]["value"])
    for alias, rest in dict(B14_ALIASES, **B14_ROW_ALIASES[row]).items():
        want[alias] = dict(rest, modelConfig={"model": row})
    return want


@contextlib.contextmanager
def in_place_aliases():
    """The writer with its one copy undone, so it adds the helper aliases into the restated chat-base-3's own mapping.
    GEMINI_THINKING is a copy for the mutant's span, so no test after it sees the change."""
    text = inspect.getsource(tc._gemini)
    copied = 'aliases = dict(configs.get("customAliases", {}))'
    if text.count(copied) != 1:
        raise AssertionError("the writer's copy of the aliases is not where this mutant reads it")
    space = dict(vars(tc))
    exec(text.replace(copied, 'aliases = configs.setdefault("customAliases", {})'), space)
    with mock.patch.object(tc, "GEMINI_THINKING", copy.deepcopy(tc.GEMINI_THINKING)), \
            mock.patch.dict(tc.WRITERS, {tc.GEMINI: lambda m: space["_gemini"](m)}):
        space["GEMINI_THINKING"] = tc.GEMINI_THINKING
        yield


def writer_mutant(*spans):
    """R-B14-7: the writer with source spans replaced, run on take_config's live globals, so a patch a check makes
    (GEMINI_THINKING, GEMINI_ROW_ALIASES) reaches the mutant as it reaches the real writer."""
    text = inspect.getsource(tc._gemini)
    for old, new in spans:
        if text.count(old) != 1:
            raise AssertionError(f"the writer's span is not where this mutant reads it: {old!r}")
        text = text.replace(old, new)
    space = {}
    exec(compile(text, "<mutant>", "exec"), dict(vars(tc)), space)
    mutated = types.FunctionType(space["_gemini"].__code__, vars(tc), "_gemini")
    return lambda: mock.patch.dict(tc.WRITERS, {tc.GEMINI: mutated})


# R-B14-7 (a): the unread-model refusal dropped, an unread model falling back to no per-row aliases.
UNREAD_MODEL_REFUSAL = (
    '    if model not in GEMINI_ROW_ALIASES:\n'
    '        raise Refused(f"no helper aliases are read for model {model!r} at the pinned Gemini CLI '
    '(GEMINI_ROW_ALIASES)")\n')
# R-B14-7 (b): the set-twice refusal dropped.
SET_TWICE_REFUSAL = ('        if alias in aliases:\n'
                     '            raise Refused(f"helper alias {alias!r} is set twice")\n')


def set_twice_refused():
    """R-B14-6: GEMINI_THINKING's value carrying a helper alias's name is refused, never overwritten by the pin."""
    out = []
    alias = next(iter(tc.GEMINI_HELPER_ALIASES))
    value = dict(tc.GEMINI_THINKING["value"], **{alias: {"extends": "base", "modelConfig": {"model": "other"}}})
    with mock.patch.object(tc, "GEMINI_THINKING", dict(tc.GEMINI_THINKING, value=value)):
        for row in tc.GEMINI_ROW_ALIASES:
            try:
                tc.files_for(tc.GEMINI, model=row)
                out.append(f"{row}: a gemini config was placed with helper alias {alias!r} set twice")
            except tc.Refused as exc:
                if "set twice" not in str(exc):
                    out.append(f"{row}: refused, but not as set twice: {exc}")
    return out


class TestB14HelperPins(MutantCase):
    """R-B14-1 and R-B14-2, per arm G row, on the settings take_config places (its real, sourced values)."""

    def check(self):
        out = []
        with open(os.path.join(HERE, "prereg-draft.json"), encoding="utf-8") as fh:
            rows = json.load(fh)["models"]["G"]
        if sorted(rows) != sorted(B14_ROW_ALIASES):
            out.append(f"arm G's rows are {rows}, not the rows these pins are read for")
        for row in rows:
            d = tempfile.mkdtemp(prefix="w-")
            try:
                tc.write(d, tc.GEMINI, model=row)
                with open(os.path.join(d, ".gemini", "settings.json")) as fh:
                    doc = json.load(fh)
            except Exception as exc:
                out.append(f"{row}: no settings placed ({type(exc).__name__}: {exc})")
                continue
            aliases = doc.get("modelConfigs", {}).get("customAliases", {})
            for alias, entry in b14_aliases(row).items():
                if aliases.get(alias) != entry:
                    out.append(f"{row}: customAliases[{alias!r}] is {aliases.get(alias)!r}, not {entry!r}")
            if set(aliases) != set(b14_aliases(row)):
                out.append(f"{row}: customAliases carries {sorted(set(aliases) - set(b14_aliases(row)))} beyond the pins")
            if doc.get("tools") != {"exclude": B14_EXCLUDE}:
                out.append(f"{row}: tools is {doc.get('tools')!r}, not tools.exclude {B14_EXCLUDE}")
            if "disableLoopDetection" in doc.get("model", {}):
                out.append(f"{row}: loop detection is configured ({doc['model']}); R-B14-1 keeps the CLI as shipped")
        if tc.GEMINI_THINKING != R3_VALUES["GEMINI_THINKING"]:
            out.append(f"placing the settings changed GEMINI_THINKING in place: {tc.GEMINI_THINKING}")
        sources = getattr(tc, "VALUE_SOURCES", {})
        for name in B14_SOURCES:
            if sources.get(name) != B14_SOURCES[name]:
                out.append(f"VALUE_SOURCES[{name!r}] is not the record of the B14 read")
        try:
            tc.files_for(tc.GEMINI, model="gemini-3-flash-preview")
            out.append("a gemini config was placed for a model whose helper aliases are not read")
        except tc.Refused:
            pass
        out += set_twice_refused()
        return out

    def test_helper_alias_set_twice_refused(self):
        self.assertEqual(set_twice_refused(), [])

    def test_b14_helper_pins(self):
        mutants = [(f"alias {alias} dropped", (lambda a: lambda: mock.patch.dict(
            tc.GEMINI_HELPER_ALIASES, {k: v for k, v in tc.GEMINI_HELPER_ALIASES.items() if k != a}, clear=True))(
            alias)) for alias in B14_ALIASES]
        mutants += [("alias chat-compression-3.1-flash-lite dropped", lambda: mock.patch.dict(
            tc.GEMINI_ROW_ALIASES, {"gemini-3.5-flash-lite": {}}))]
        mutants += [("invoke_agent not excluded", patched(tc, "GEMINI_AGENT_EXCLUSION", ()))]
        mutants += [("helper aliases written into GEMINI_THINKING's own value", in_place_aliases)]
        mutants += [("unread-model refusal dropped", writer_mutant(
            (UNREAD_MODEL_REFUSAL, ""), ("GEMINI_ROW_ALIASES[model]", "GEMINI_ROW_ALIASES.get(model, {})")))]
        mutants += [("set-twice refusal dropped", writer_mutant((SET_TWICE_REFUSAL, "")))]
        self.assert_green_then_red(self.check, mutants)


# Lane vendor-b18 (glitch-26's ruling B18-1, Mon 19 Oct 2026; the GPT practice walk w-o7's egress log): every Codex
# row's config.toml also switches off the pinned CLI's plugins (the features table's plugins key) and its metrics
# export at exit (the otel table's metrics_exporter, "none"; analytics.enabled is not used: it also turns off the
# analytics events queue and changes the analytics_enabled field of every model request's metadata). Each is cited
# from the pinned source at rust-v0.162.1, as the executor read it (VALUE_SOURCES).
CODEX_PKG = {"package": "openai/codex", "tag": "rust-v0.162.1", "commit": "092d3acd6bec3e3a14bdc7e7a2810ab628ab759d"}
B18_SOURCES = {
    "CODEX_PLUGINS": dict(CODEX_PKG, file="codex-rs/features/src/lib.rs",
                          lines={'key: "plugins"': 1560, "default_enabled: true": 1562,
                                 "plugin_recommendations_enabled needs it": 577},
                          uses={"codex-rs/app-server/src/message_processor.rs": {
                                    "the plugin startup tasks, started at process start": 558},
                                "codex-rs/core-plugins/src/manager.rs": {
                                    "the startup tasks run only with plugins on": 2820,
                                    "the curated-plugins sync, gated on plugins": 754,
                                    "the remote plugin bundle sync, gated on plugins": 1599,
                                    "plugins_for_config loads nothing with plugins off": 814,
                                    "the recommended plugins mode is Legacy with plugins off": 1908},
                                "codex-rs/core-plugins/src/startup_sync.rs": {
                                    "the curated sync's source, https://github.com/openai/plugins.git": 30},
                                "codex-rs/core-plugins/src/remote_bundle.rs": {
                                    "a bundle's download URL, from the remote listing": 192},
                                "codex-rs/core/src/session/mod.rs": {
                                    "recommended plugin candidates only if plugin_recommendations_enabled": 4248,
                                    "the recommended_plugins section pushed into the developer message": 4414},
                                "codex-rs/core/src/context/recommended_plugins_instructions.rs": {
                                    "the section's markers": 43, "the section's body, one line per plugin": 53},
                                "codex-rs/core/src/context/available_plugins_instructions.rs": {
                                    "the Plugins usage section, only when a plugin is loaded": 32},
                                "codex-rs/core/src/session/world_state.rs": {
                                    "the usage section needs a loaded plugin": 304},
                                "codex-rs/core/src/tools/spec_plan.rs": {
                                    "tool_suggest_enabled needs plugins": 712,
                                    "request_plugin_install registered only then": 1328}},
                          read="features.plugins (a Stable feature, on by default) gates the plugin startup tasks "
                               "(the curated-plugins git sync and the remote installed-plugin bundle sync), the "
                               "plugin load, and the plugin recommendations fetched from the backend, which the "
                               "developer message carries as its recommended_plugins section and the tool list as "
                               "request_plugin_install; set to false, none of them runs"),
    "CODEX_METRICS_EXPORTER": dict(CODEX_PKG, file="codex-rs/core/src/config/otel.rs",
                                   lines={"otel.metrics_exporter defaults to Statsig": 21},
                                   uses={"codex-rs/config/src/config_toml.rs": {"the otel table": 547},
                                         "codex-rs/config/src/types.rs": {
                                             "OtelExporterKind is kebab-case, so None reads none": 596,
                                             "metrics_exporter": 643},
                                         "codex-rs/otel/src/config.rs": {
                                             "Statsig's endpoint, https://ab.chatgpt.com/otlp/v1/metrics": 9,
                                             "Statsig resolved to that endpoint": 24},
                                         "codex-rs/otel/src/provider.rs": {
                                             "no metrics with the None exporter": 218,
                                             "shutdown flushes the metrics": 104, "Drop runs shutdown at exit": 359},
                                         "codex-rs/core/src/otel_init.rs": {
                                             "the metrics exporter is otel.metrics_exporter's": 74},
                                         "codex-rs/exec/src/lib.rs": {
                                             "codex exec builds the provider, analytics on by default": 668},
                                         "codex-rs/app-server/src/turn_cost_worker.rs": {
                                             "the turn cost worker reads only an explicit OTLP exporter": 106}},
                                   not_used={"analytics.enabled": {
                                       "codex-rs/core/src/otel_init.rs": 71,
                                       "codex-rs/app-server/src/analytics_utils.rs": 14,
                                       "codex-rs/analytics/src/client.rs": 321,
                                       "codex-rs/core/src/session/session.rs": 746}},
                                   read="otel.metrics_exporter defaults to Statsig, which resolves to an OTLP HTTP "
                                        "exporter at ab.chatgpt.com, flushed when the provider shuts down at exit; "
                                        "none builds no metrics exporter; the key's one other reader, the turn cost "
                                        "worker, starts only for an explicit OTLP exporter, so Statsig and none "
                                        "leave it off alike. "
                                        "analytics.enabled = false also drops the exporter, but it also turns off "
                                        "the analytics events queue and sets analytics_enabled in every model "
                                        "request's metadata, so it is not used"),
}
# Lane vendor-b22 (glitch-26's ruling B22-10): the [agents] switch's source record, kept beside its own test.
sys.path.insert(0, os.path.join(HERE, "tests"))
from test_codex_agents_off import B22_SOURCES  # noqa: E402
# A Codex row's config.toml before B18: what every other key must still read.
B18_BEFORE = {"web_search": "disabled", "check_for_update_on_startup": False, "forced_login_method": "chatgpt",
              "cli_auth_credentials_store": "file", "features": {"hooks": False}}


class TestB18CodexSwitches(MutantCase):
    """B18-1, per arm O row, on the config.toml take_config places (its real, sourced values)."""

    def check(self):
        out = []
        with open(os.path.join(HERE, "prereg-draft.json"), encoding="utf-8") as fh:
            rows = json.load(fh)["models"]["O"]
        for row in rows:
            d = tempfile.mkdtemp(prefix="w-")
            try:
                tc.write(d, tc.CODEX, model=row, run_tree=RUN_TREE)    # R-H1: a codex config names its run tree
                with open(os.path.join(d, "config.toml"), "rb") as fh:
                    doc = tomllib.load(fh)
            except Exception as exc:
                out.append(f"{row}: no config placed ({type(exc).__name__}: {exc})")
                continue
            if doc.get("features", {}).get("plugins") is not False:
                out.append(f"{row}: features.plugins is {doc.get('features', {}).get('plugins')!r}, not false")
            if doc.get("otel") != {"metrics_exporter": "none"}:
                out.append(f"{row}: otel is {doc.get('otel')!r}, not metrics_exporter none")
            rest = copy.deepcopy(doc)
            rest.get("features", {}).pop("plugins", None)
            rest.pop("otel", None)
            rest.pop("agents", None)     # B22-10's [agents] switch, bound by tests/test_codex_agents_off.py
            want = dict(B18_BEFORE, model=row, model_reasoning_effort=R3_VALUES["CODEX_REASONING_EFFORT"][row],
                        projects={RUN_TREE: {"trust_level": "trusted"}})    # R-H1's trust table, B11's own key
            if rest != want:
                out.append(f"{row}: the config's other keys read {rest}, not {want}")
        sources = getattr(tc, "VALUE_SOURCES", {})
        for name in B18_SOURCES:
            if sources.get(name) != B18_SOURCES[name]:
                out.append(f"VALUE_SOURCES[{name!r}] is not the record of the B18 read")
        return out

    def test_b18_codex_switches(self):
        self.assert_green_then_red(self.check, [
            ("plugins key dropped", patched(tc, "CODEX_FEATURES", (("hooks", False),))),
            ("plugins left on", patched(tc, "CODEX_FEATURES", (("hooks", False), ("plugins", True)))),
            ("metrics switch dropped", patched(tc, "CODEX_OTEL", ())),
            ("metrics left on Statsig", patched(tc, "CODEX_OTEL", (("metrics_exporter", "statsig"),))),
            ("another key changed", patched(tc, "CODEX_TOP", (("web_search", "live"),) + tc.CODEX_TOP[1:])),
            ("plugins source dropped", lambda: mock.patch.dict(tc.VALUE_SOURCES, {"CODEX_PLUGINS": {}})),
            ("metrics source's line moved", lambda: mock.patch.dict(tc.VALUE_SOURCES, {"CODEX_METRICS_EXPORTER": dict(
                B18_SOURCES["CODEX_METRICS_EXPORTER"], lines={"otel.metrics_exporter defaults to Statsig": 22})})),
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
                # Lane vendor-b18 (glitch-26's ruling B18-1): the CLI's plugins and its metrics export at exit off.
                "features": {"hooks": False, "plugins": False}, "otel": {"metrics_exporter": "none"},
                # Lane vendor-b22 (glitch-26's ruling B22-10): the CLI's collaboration (delegation) tools off.
                "agents": {"enabled": False},
                # R-H1: the run tree trusted up front, so Codex never rewrites the file
                "projects": {RUN_TREE: {"trust_level": "trusted"}}}
        if doc != want:
            out.append(f"codex config.toml reads {doc}")
        d, rec = written(tc.GEMINI, "gemini-3.8-flash")
        with open(os.path.join(d, ".gemini", "settings.json")) as fh:
            doc = json.load(fh)
        want = {"tools.exclude": B14_EXCLUDE,          # R-6: no context.fileName; R-B14-2: invoke_agent excluded
                "hooksConfig.enabled": False, "general.enableAutoUpdate": False,
                "general.enableAutoUpdateNotification": False, "privacy.usageStatisticsEnabled": False,
                "telemetry.enabled": False, "model.name": "gemini-3.8-flash", "model.thinkingLevel": "default",
                "security.auth.selectedType": "api-key-stand-in",
                "security.folderTrust.enabled": False,         # round 18 B9: folder trust off (glitch-26's ruling B9)
                # The frozen legacy noninteractive path (pinned 0.64.0 evidence; the renderer fold).
                "experimental.adk.agentSessionNoninteractiveEnabled": False}
        # R-B14-1: each helper alias repointed at the row's model (lane vendor-b14 round 2).
        for alias, rest in B14_ALIASES.items():
            want.update({f"modelConfigs.customAliases.{alias}.{k}": v for k, v in rest.items()})
            want[f"modelConfigs.customAliases.{alias}.modelConfig.model"] = "gemini-3.8-flash"
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
                tc.write(d, tc.CODEX, model="m", run_tree=RUN_TREE)
            repo = tempfile.mkdtemp(prefix="w-")
            os.makedirs(os.path.join(repo, ".git"))
            cfg = os.path.join(repo, "cfg")
            os.makedirs(cfg)
            with self.assertRaises(tc.Refused):
                tc.write(cfg, tc.CODEX, model="m", run_tree=RUN_TREE)


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
                    "//srv/w/run-0a1b2c3d", "/", '/srv/w/t"]\n[x', "/srv/w/t\nx", "/srv/w/r\u00e9", "", 7,
                    os.path.join(link_parent, "via", "run-0a1b2c3d")):
            try:
                with filled():
                    tc.files_for(tc.CODEX, model="gpt-6.1-sol", run_tree=bad)
                out.append(f"R-H1.key: run tree {bad!r} was admitted")
            except tc.Refused:
                pass
            except Exception as e:  # noqa: BLE001 - anything but the refusal is the guard's failure
                out.append(f"R-H1.key: run tree {bad!r} raised {type(e).__name__}, not a refusal")
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
                    tc.write(d, h, model=m, run_tree=RUN_TREE)
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
            ("digests-only", patched(tc, "config_sha256", lambda f, harness=None: __import__("hashlib").sha256("".join(sorted(
                __import__("hashlib").sha256(open(os.path.join(r, n), "rb").read()).hexdigest()
                for r, _, ns in os.walk(f) for n in ns)).encode()).hexdigest())),
            ("names-only", patched(tc, "config_sha256", lambda f, harness=None: __import__("hashlib").sha256(
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


# R-H3 (glitch-26's ruling on lane vendor-b11, round 3): a killed Codex turn leaves tmp/arg0/codex-arg0??????/ with
# .lock and four links to the image's codex executable (arg0/src/lib.rs 21-25, 358, 373-375, 395-400 at rust-v0.162.1).
# config_sha256 hashes exactly those four by name and target string, never following them, and refuses every other
# link. The executable is the pinned take-o image's, as measured (the athena name sweep's binary_path).
CODEX_EXE = ("/usr/local/lib/node_modules/@openai/codex/node_modules/@openai/codex-linux-x64/vendor/"
             "x86_64-unknown-linux-musl/bin/codex")
ARG0_NAMES = ("apply_patch", "applypatch", "codex-linux-sandbox", "codex-execve-wrapper")


def killed_codex(folder, *, names=ARG0_NAMES, sub="tmp/arg0/codex-arg0AbC123", target=CODEX_EXE):
    d = os.path.join(folder, *sub.split("/"))
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, ".lock"), "w").close()
    for n in names:
        os.symlink(target, os.path.join(d, n))
    return d


class TestArg0Links(MutantCase):
    def check_arg0_links(self):
        out = []
        if getattr(tc, "CODEX_EXECUTABLE", None) != CODEX_EXE or tuple(getattr(tc, "CODEX_ARG0_LINKS", ())) != \
                ARG0_NAMES:
            return ["R-H3: take_config does not name the image's codex executable and the four arg0 link names"]
        a, ra = written(tc.CODEX, "gpt-6.1-sol")
        killed_codex(a)
        try:
            first = tc.config_sha256(a, tc.CODEX)
        except tc.Refused as e:
            return [f"R-H3: a killed Codex turn's four arg0 links refused: {e}"]
        if first == ra["sha256"]:
            out.append("R-H3: the hash does not see the four links")
        b, _ = written(tc.CODEX, "gpt-6.1-sol")
        killed_codex(b, sub="tmp/arg0/codex-arg0ZyX987")
        if tc.config_sha256(b, tc.CODEX) == first:
            out.append("R-H3: the hash does not see the link's folder name")
        refused = {
            "a fifth name": dict(names=ARG0_NAMES + ("codex",)),
            "a link at another depth": dict(sub="tmp/arg0"),
            "a link one level deeper": dict(sub="tmp/arg0/codex-arg0AbC123/x"),
            "a folder off the tempfile shape": dict(sub="tmp/arg0/codex-arg0AbC"),
            "a folder outside tmp/arg0": dict(sub="tmp/x/codex-arg0AbC123"),
            "a target that is not the executable": dict(target="/bin/sh"),
            "a relative target": dict(target="codex"),
        }
        for why, kw in refused.items():
            c, _ = written(tc.CODEX, "gpt-6.1-sol")
            killed_codex(c, **kw)
            try:
                tc.config_sha256(c, tc.CODEX)
                out.append(f"R-H3: {why} was hashed")
            except tc.Refused:
                pass
        d, _ = written(tc.CODEX, "gpt-6.1-sol")
        os.makedirs(os.path.join(d, "tmp", "arg0"))
        os.symlink(os.path.join(d, "tmp"), os.path.join(d, "tmp", "arg0", "codex-arg0AbC123"))
        try:
            tc.config_sha256(d, tc.CODEX)
            out.append("R-H3: a folder link at the arg0 folder's place was hashed")
        except tc.Refused:
            pass
        return out

    def test_the_arg0_links(self):
        self.assert_green_then_red(self.check_arg0_links, [
            ("any-link", patched(tc, "codex_arg0_link", lambda rel, target: True)),
            ("name-only", patched(tc, "codex_arg0_link",
                                  lambda rel, target: rel.rsplit("/", 1)[-1] in ARG0_NAMES)),
            ("no-target-check", patched(tc, "codex_arg0_link", lambda rel, target: re.fullmatch(
                r"tmp/arg0/codex-arg0[A-Za-z0-9]{6}/(apply_patch|applypatch|codex-linux-sandbox|codex-execve-wrapper)",
                rel) is not None)),
            ("no-link-admitted", patched(tc, "codex_arg0_link", lambda rel, target: False)),
        ])


# R5-4 (glitch-26's ruling, round 5 of lane vendor-b11; the review of round 4, finding 4): config_sha256 admits R-H3's
# four arg0 links for the codex harness only, as run_take.check_config_folder does. A claude-code or gemini folder, or
# a folder hashed with no harness named, behaves exactly as before R-H3 (take_config.py at 936cf29f^, lines 331-332):
# any link refuses with "a link or a special file in the config folder".
PRE_R_H3_REFUSAL = "a link or a special file in the config folder"


class TestArg0LinksCodexOnly(MutantCase):
    def check_codex_only(self):
        out = []
        for h, m in ((tc.CLAUDE_CODE, None), (tc.GEMINI, "gemini-3.8-flash"), (tc.CODEX, "gpt-6.1-sol")):
            a, _ = written(h, m)
            killed_codex(a, names=ARG0_NAMES[:1])                    # one arg0 link, at its one shape and target
            calls = ((h, (a, h)), ("no harness named", (a,))) if h != tc.CODEX else (("no harness named", (a,)),)
            for who, args in calls:
                try:
                    tc.config_sha256(*args)
                    out.append(f"R5-4: {h}: a folder holding one arg0 link was hashed ({who})")
                except TypeError as e:
                    out.append(f"R5-4: config_sha256 takes no harness ({e})")
                except tc.Refused as e:
                    if str(e) != PRE_R_H3_REFUSAL:
                        out.append(f"R5-4: {h}: refused, but not as before R-H3 ({who}): {e}")
        c, _ = written(tc.CODEX, "gpt-6.1-sol")
        killed_codex(c)
        try:
            tc.config_sha256(c, tc.CODEX)
        except (TypeError, tc.Refused) as e:
            out.append(f"R5-4: codex: the four arg0 links refused with the harness named ({e})")
        return out

    def test_the_arg0_links_are_codexs_alone(self):
        original = tc.config_sha256
        self.assert_green_then_red(self.check_codex_only, [
            ("every-harness", patched(tc, "config_sha256", lambda f, harness=None: original(f, tc.CODEX))),
        ])


# Taken last, after every import-time statement of this module: must be empty (setUpModule arms the guard).
_PATCHED_AT_IMPORT = _patched_now()


if __name__ == "__main__":
    unittest.main(verbosity=2)
