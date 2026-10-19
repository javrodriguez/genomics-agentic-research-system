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
        if getattr(tc, "VALUE_SOURCES", None) != dict(R3_SOURCES, **B14_SOURCES):
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
                "features": {"hooks": False}}
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
