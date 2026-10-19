#!/usr/bin/env python3
"""The per-take config folder's files, per harness (CP2), each hashed for the freeze.

The folder is mounted at `run_take.CONFIG_MOUNT` in the take container and is the harness's user-config home there
(`CLAUDE_CONFIG_DIR`, `CODEX_HOME`, `GEMINI_CLI_HOME`, set by run_take's environment per harness). Split from
run_take.py (this lane's decision) so each file stays one owner and small.

  - claude-code: an EMPTY `settings.json` (`{}`). The plan said the per-take user settings "carry only the bypass
    acceptance"; that is departed from: the acceptance is RULED not required in -p runs (glitch-06, 14 Oct 2026;
    CLAUDE_BYPASS_RULING in run_take), so the study sends no bypass key anywhere. The host's user settings never exist
    in the box, and every turn runs --setting-sources project,local, so this user scope never loads anyway.
  - codex: `config.toml` with D8's values and the owner's subscription amendment, `model` from the caller,
    `model_reasoning_effort` the harness's default for that model at the pinned version (R3, below).
  - gemini: `settings.json` with D8's values verbatim, `model.name` from the caller; the thinking level and the API-key
    auth-type setting (name and value) are the pinned version's (R3, below). The installed0.64.0 source establishes
    the file location under GEMINI_CLI_HOME and the explicitly frozen legacy noninteractive path.
  - R3 (glitch-b5's ruling, Sun 18 Oct 2026; lane vendor-admission round 17, B6): CODEX_REASONING_EFFORT,
    GEMINI_THINKING and GEMINI_AUTH_SETTING, once PENDING, are each read statically from the pinned package (no model
    call, no network), the file and line beside each value and in VALUE_SOURCES.
  - R-6 (glitch-b5's ruling of Sat 17 Oct 2026, under Javier's delegation; lane vendor-admission T4 P2): neither vendor
    file configures an instruction-file name. D8's `project_doc_fallback_filenames = ["CLAUDE.md"]` and
    `context.fileName = ["CLAUDE.md"]` are removed: each CLI reads its native file (INSTRUCTION_FILES), which
    walk_builders.build_run_tree places in the checkout beside every CLAUDE.md (round 10 ruling 3, gars/CLAUDE.md
    included) as a byte-identical copy of it.

`write()` refuses (NotReady) while any value its harness needs is PENDING. No public function takes a PENDING value
as a parameter; tests fill them only by patching this module in memory. No key ever enters a config file: no
function here takes one. Nothing in any file names the study (interface 16). Standard library only.
"""

from __future__ import annotations

import hashlib
import json
import os
import re

from box import run_take

PENDING = run_take.PENDING
NotReady = run_take.NotReady
Refused = run_take.Refused

CLAUDE_CODE, CODEX, GEMINI = run_take.CLAUDE_CODE, run_take.CODEX, run_take.GEMINI

# claude-code: the bypass acceptance, RULED not required in -p (CLAUDE_BYPASS_RULING in run_take): no key is written. This
# mirrors run_take.CLAUDE_BYPASS_KEY as its own literal (the process audit's attribute list is not widened; tests bind
# take_config.CLAUDE_BYPASS_KEY to run_take.CLAUDE_BYPASS_KEY).
CLAUDE_BYPASS_NOT_REQUIRED = "RULED: not required in -p"
CLAUDE_BYPASS_KEY = CLAUDE_BYPASS_NOT_REQUIRED
CLAUDE_SETTINGS = "settings.json"

# Codex: D8 section 3 plus owner's 13 Oct subscription-only amendment.
CODEX_CONFIG = "config.toml"
# R3: the harness's default for that model at the pinned Codex, per model: each model entry's default_reasoning_level in
# the bundled catalog codex-rs/models-manager/models.json at rust-v0.162.1 (VALUE_SOURCES).
CODEX_REASONING_EFFORT = {
    "gpt-6.1-sol": "low",       # models.json line 213
    "gpt-6-luna": "medium",     # models.json line 560
}
CODEX_TOP = (("web_search", "disabled"), ("check_for_update_on_startup", False), ("forced_login_method", "chatgpt"),
             ("cli_auth_credentials_store", "file"))
CODEX_FEATURES = (("hooks", False),)

# gemini: D8 section 3, verbatim, as dotted paths into settings.json.
GEMINI_SETTINGS = (("tools.exclude", ["google_web_search", "web_fetch"]), ("hooksConfig.enabled", False), ("general.enableAutoUpdate", False),
                   ("general.enableAutoUpdateNotification", False), ("privacy.usageStatisticsEnabled", False),
                   ("telemetry.enabled", False),
                   ("experimental.adk.agentSessionNoninteractiveEnabled", False))
GEMINI_MODEL_PATH = "model.name"
# R-6: the instruction file each vendor CLI reads by its own default name, configured nowhere (no fallback name is used
# or accepted): Codex's AGENTS.md, Gemini CLI's GEMINI.md. walk_builders.build_run_tree places each beside every
# CLAUDE.md of the checkout (round 10 ruling 3) as a copy of it, the file the claude-code arm reads.
INSTRUCTION_FILES = {CODEX: "AGENTS.md", GEMINI: "GEMINI.md"}
# Each {"path": "<dotted path>", "value": <JSON value>}, read statically at the pinned 0.64.0 (R3, VALUE_SOURCES).
# The thinking level: both arm G models extend the built-in alias chat-base-3 (bundle/chunk-NR7L3FXV.js lines 362349
# and 362361), whose thinkingLevel is HIGH (line 362280; ThinkingLevel.HIGH, line 258475); settings.json's
# modelConfigs.customAliases replaces an alias by name (bundle/chunk-FLKY6NH5.js line 13409; kept beside the built-in
# aliases, chunk-NR7L3FXV.js line 380852), so chat-base-3 is restated as it is: the default, pinned in the file.
GEMINI_THINKING = {"path": "modelConfigs.customAliases", "value": {"chat-base-3": {
    "extends": "chat-base", "modelConfig": {"generateContentConfig": {"thinkingConfig": {"thinkingLevel": "HIGH"}}}}}}
# The API-key auth type: security.auth.selectedType (bundle/chunk-FLKY6NH5.js line 14183) set to AuthType.USE_GEMINI,
# "gemini-api-key" (bundle/chunk-NR7L3FXV.js line 312750).
GEMINI_AUTH_SETTING = {"path": "security.auth.selectedType", "value": "gemini-api-key"}
# Folder trust off (round 18 B9, glitch-26's ruling B9): it defaults on at the pinned version (bundle/chunk-FLKY6NH5.js
# line 9599), and a headless run in a folder it does not trust stops at startup with FatalUntrustedWorkspaceError, exit
# 55 (bundle/gemini-6ESINPDZ.js line 11137), before any model call; off, that check returns first (line 11129).
# Review r18-b9 NIT 2 (B10): the bundle that runs has that check at bundle/gemini-Q2GRYIAK.js lines 11153 and 11145 and
# the class at bundle/chunk-NR7L3FXV.js line 252702; gemini-6ESINPDZ.js is a copy no bundle file imports
# (VALUE_SOURCES).
GEMINI_TRUST_SETTING = {"path": "security.folderTrust.enabled", "value": False}
# R3's record of each static read: the pinned package, the file (with its sha256 for the Gemini bundle files, equal to
# the box lane's installed-package evidence of 14 Oct), the line or lines, and what was read there.
_GEMINI_PKG = {"package": "@google/gemini-cli", "version": "0.64.0",
               "tarball_sha256": "891a794e55c8319b6b78f6f8f13d6b8b2782a4709dfd2fcabf3a1f63ae8365e6"}
VALUE_SOURCES = {
    "CODEX_REASONING_EFFORT": {
        "package": "openai/codex", "tag": "rust-v0.162.1", "commit": "092d3acd6bec3e3a14bdc7e7a2810ab628ab759d",
        "file": "codex-rs/models-manager/models.json", "lines": {"gpt-6.1-sol": 213, "gpt-6-luna": 560},
        "read": "each model entry's default_reasoning_level; the file is the bundled catalog "
                "(include_str!, codex-rs/models-manager/src/lib.rs line 15)"},
    "GEMINI_THINKING": dict(_GEMINI_PKG, file="bundle/chunk-NR7L3FXV.js",
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
    "GEMINI_AUTH_SETTING": dict(_GEMINI_PKG, file="bundle/chunk-FLKY6NH5.js",
                                file_sha256="f6a4ddd46350dad40515218069d369aaa0025f194c552400b69925b941098bc8",
                                line=14183, value_file="bundle/chunk-NR7L3FXV.js", value_line=312750,
                                read="security.auth.selectedType (packages/cli/src/config/settingsSchema.ts), set to "
                                     "AuthType.USE_GEMINI, the API-key auth type"),
    "GEMINI_TRUST_SETTING": dict(_GEMINI_PKG, file="bundle/chunk-FLKY6NH5.js",
                                 file_sha256="f6a4ddd46350dad40515218069d369aaa0025f194c552400b69925b941098bc8",
                                 line=9599, check_file="bundle/gemini-6ESINPDZ.js",
                                 check_file_sha256="19950cab8f7bd8b48ea89c4ede22418b2e5d836d9c1554baed62c9019d74810b",
                                 check_lines={"folder trust off: the check returns": 11129,
                                              "headless and untrusted: FatalUntrustedWorkspaceError (exit 55)": 11137},
                                 exit55_file="bundle/chunk-NR7L3FXV.js",
                                 exit55_file_sha256="d566e81b1df8d4d44a91bf7aeea96a58ec0e6c8934fa424315ef060507dcbb8c",
                                 exit55_line=252702, running_check_file="bundle/gemini-Q2GRYIAK.js",
                                 running_check_file_sha256=("7702da31cf099ca3e1d64fd195f15b7726b2c2829ec21e9"
                                                            "55558eb9dbfba47da"),
                                 running_check_lines={"folder trust off: the check returns": 11145,
                                                      "headless and untrusted: FatalUntrustedWorkspaceError (exit 55)":
                                                          11153},
                                 unreached_exit55={"file": "bundle/chunk-J7SXW2FI.js", "line": 252715, "file_sha256":
                                                   "e2aca15290b02dc9845704f3fed44c577919652508624f340974f0ff588f206e"},
                                 read="security.folderTrust.enabled defaults to true (settings.security?.folderTrust"
                                      "?.enabled ?? true), although docs/cli/trusted-folders.md calls the feature off "
                                      "by default; with it on, a headless run in an untrusted folder throws "
                                      "FatalUntrustedWorkspaceError, exit 55 (super(message, 55) at exit55_file "
                                      "exit55_line, in the running bundle: bundle/gemini.js line 110 loads "
                                      "gemini-Q2GRYIAK.js, which imports chunk-NR7L3FXV.js; check_file and "
                                      "unreached_exit55 are a second copy no bundle file imports); "
                                      "set to false, the startup check returns before any trust lookup"),
}
# The settings file's path relative to GEMINI_CLI_HOME (for example ".gemini/settings.json"), once measured.
# Installed0.64.0 Storage.getGlobalSettingsPath: GEMINI_CLI_HOME/.gemini/settings.json.
# Exact installed path/hash/offset retained in gemini-storage-source.json.
GEMINI_SETTINGS_PATH = ".gemini/settings.json"

PENDING_WHY = {
    "CLAUDE_BYPASS_KEY": "the bypass acceptance: RULED not required in -p runs (CLAUDE_BYPASS_RULING in run_take); "
                         "listed here only if it is ever set back to PENDING.",
    "CODEX_REASONING_EFFORT": "Codex's model_reasoning_effort: the harness's default for that model at the pinned "
                              "version.",
    "GEMINI_THINKING": "Gemini CLI's thinking level (setting path and value) at the pinned version.",
    "GEMINI_AUTH_SETTING": "Gemini CLI's API-key auth-type setting, name and value, at the pinned version.",
    "GEMINI_SETTINGS_PATH": "where Gemini CLI reads settings.json under GEMINI_CLI_HOME at the pinned version.",
}
NEEDS = {CLAUDE_CODE: ("CLAUDE_BYPASS_KEY",), CODEX: ("CODEX_REASONING_EFFORT",),
         GEMINI: ("GEMINI_THINKING", "GEMINI_AUTH_SETTING", "GEMINI_SETTINGS_PATH")}

_MODEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}")
_KEY = re.compile(r"[A-Za-z][A-Za-z0-9_]*")


def _pending_values() -> dict:
    return {"CLAUDE_BYPASS_KEY": CLAUDE_BYPASS_KEY, "CODEX_REASONING_EFFORT": CODEX_REASONING_EFFORT,
            "GEMINI_THINKING": GEMINI_THINKING, "GEMINI_AUTH_SETTING": GEMINI_AUTH_SETTING,
            "GEMINI_SETTINGS_PATH": GEMINI_SETTINGS_PATH}


def pending() -> dict:
    values = _pending_values()
    return {k: why for k, why in PENDING_WHY.items() if run_take._is_pending(values[k])}


def _ready(harness: str) -> None:
    values = _pending_values()
    still = [k for k in NEEDS[harness] if run_take._is_pending(values[k])]
    if still:
        raise NotReady(f"{harness} config needs {', '.join(still)}: " + " ".join(PENDING_WHY[k] for k in still))


def _json_bytes(doc) -> bytes:
    return (json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode("ascii")


def _toml_value(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, str):
        if not re.fullmatch(r"[A-Za-z0-9._ -]*", v):
            raise Refused("a config string holds only letters, digits, dot, dash, underscore and space")
        return f'"{v}"'
    if isinstance(v, list):
        return "[" + ", ".join(_toml_value(x) for x in v) + "]"
    raise Refused(f"no TOML form for {type(v).__name__}")


def _set(doc: dict, dotted: str, value) -> None:
    parts = dotted.split(".")
    if not all(_KEY.fullmatch(p) for p in parts):
        raise Refused(f"setting path {dotted!r} is off its shape")
    cur = doc
    for p in parts[:-1]:
        cur = cur.setdefault(p, {})
        if not isinstance(cur, dict):
            raise Refused(f"setting path {dotted!r} crosses a value")
    if parts[-1] in cur:
        raise Refused(f"setting {dotted!r} is set twice")
    cur[parts[-1]] = value


def _model(model) -> str:
    if not isinstance(model, str) or not _MODEL.fullmatch(model):
        raise Refused("the model is a plain model id")
    return model


def _claude(model) -> dict:
    if model is not None:
        raise Refused("Claude Code's per-take settings are empty; the model rides as a flag")
    if CLAUDE_BYPASS_KEY != CLAUDE_BYPASS_NOT_REQUIRED:
        raise Refused("the study writes no bypass acceptance key: RULED not required in -p runs")
    return {CLAUDE_SETTINGS: _json_bytes({})}


def _codex(model) -> dict:
    model = _model(model)
    effort = CODEX_REASONING_EFFORT.get(model) if isinstance(CODEX_REASONING_EFFORT, dict) else None
    if not isinstance(effort, str):
        raise Refused(f"no reasoning effort is sourced for model {model!r} at the pinned Codex "
                      f"(CODEX_REASONING_EFFORT)")
    lines = [f"model = {_toml_value(model)}",
             f"model_reasoning_effort = {_toml_value(effort)}"]
    lines += [f"{k} = {_toml_value(v)}" for k, v in CODEX_TOP]
    lines += ["", "[features]"] + [f"{k} = {_toml_value(v)}" for k, v in CODEX_FEATURES]
    return {CODEX_CONFIG: ("\n".join(lines) + "\n").encode("ascii")}


def _gemini(model) -> dict:
    doc = {}
    for path, value in GEMINI_SETTINGS:
        _set(doc, path, value)
    _set(doc, GEMINI_MODEL_PATH, _model(model))
    for measured in (GEMINI_THINKING, GEMINI_AUTH_SETTING, GEMINI_TRUST_SETTING):
        if not (isinstance(measured, dict) and set(measured) == {"path", "value"}):
            raise Refused("a measured setting is {'path', 'value'}")
        _set(doc, measured["path"], measured["value"])
    rel = GEMINI_SETTINGS_PATH
    if not isinstance(rel, str) or rel.startswith("/") or ".." in rel.split("/") or not rel.endswith(".json"):
        raise Refused("the settings path is a relative .json path under GEMINI_CLI_HOME")
    return {rel: _json_bytes(doc)}


WRITERS = {CLAUDE_CODE: _claude, CODEX: _codex, GEMINI: _gemini}


def files_for(harness: str, *, model) -> dict:
    """{relative path: bytes} for one harness's per-take config. Refuses while a value it needs is PENDING."""
    run_take._known_harness(harness)
    if harness not in WRITERS:
        raise Refused(f"no config writer for {harness!r}")
    _ready(harness)
    return WRITERS[harness](model)


def public_record(harness: str, *, model) -> dict:
    """Submitted public settings only, rendered through every existing readiness check.

    No config-home file or credential is read. This is not proof of loaded settings;
    actual launch/preflight/native-session evidence must bind these generated bytes.
    Codex's subscription execution remains independently refused by run_take.
    """
    files = files_for(harness, model=model)
    return {"schema": 1, "harness": harness,
            "files": [{"path": path, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                       "text": data.decode("ascii")} for path, data in sorted(files.items())]}


def write(config_dir: str, harness: str, *, model) -> dict:
    """Write the files into a fresh, empty per-take config folder outside every repository; return their hash."""
    config_dir = run_take._abs_path(config_dir, "config_dir")
    files = files_for(harness, model=model)
    if os.path.islink(config_dir) or not os.path.isdir(config_dir) or os.listdir(config_dir):
        raise Refused("the per-take config folder must exist and be empty")
    if not run_take.outside_every_repository(config_dir):
        raise Refused("the per-take config folder must sit outside every repository")
    for rel, data in sorted(files.items()):
        path = os.path.join(config_dir, rel)
        os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
    return {"harness": harness, "files": sorted(files), "sha256": config_sha256(config_dir)}


def config_sha256(folder: str) -> str:
    """One sha256 over every file of the folder: sorted relative paths and their bytes' sha256. Links refused."""
    entries = []
    for root, dirs, names in os.walk(folder, followlinks=False):
        for d in dirs:
            if os.path.islink(os.path.join(root, d)):
                raise Refused("a link in the config folder")
        for n in names:
            path = os.path.join(root, n)
            if os.path.islink(path) or not os.path.isfile(path):
                raise Refused("a link or a special file in the config folder")
            with open(path, "rb") as fh:
                entries.append((os.path.relpath(path, folder), hashlib.sha256(fh.read()).hexdigest()))
    h = hashlib.sha256()
    for rel, digest in sorted(entries):
        h.update(f"{rel}\0{digest}\n".encode("utf-8"))
    return h.hexdigest()
