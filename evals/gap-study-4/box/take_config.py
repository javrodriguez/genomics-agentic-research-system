#!/usr/bin/env python3
"""The per-take config folder's files, per harness (CP2), each hashed for the freeze.

The folder is mounted at `run_take.CONFIG_MOUNT` in the take container and is the harness's user-config home there
(`CLAUDE_CONFIG_DIR`, `CODEX_HOME`, `GEMINI_CLI_HOME`, set by run_take's environment per harness). Split from
run_take.py (this lane's decision) so each file stays one owner and small.

  - claude-code: an EMPTY `settings.json` (`{}`). The plan said the per-take user settings "carry only the bypass
    acceptance"; that is departed from: the acceptance is RULED not required in -p runs (glitch-06, 14 Oct 2026;
    CLAUDE_BYPASS_RULING in run_take), so the study sends no bypass key anywhere. The host's user settings never exist
    in the box, and every turn runs --setting-sources project,local, so this user scope never loads anyway.
  - codex: `config.toml` with D8's values and the owner's subscription amendment, `model` from the caller, `model_reasoning_effort` PENDING (the
    harness's default for that model at the pinned version).
  - gemini: `settings.json` with D8's values verbatim, `model.name` from the caller; the thinking level, the API-key
    auth-type setting (name and value) are PENDING. The installed0.64.0 source establishes the file location
    under GEMINI_CLI_HOME and the explicitly frozen legacy noninteractive path.
  - R-6 (glitch-b5's ruling of Sat 17 Oct 2026, under Javier's delegation; lane vendor-admission T4 P2): neither vendor
    file configures an instruction-file name. D8's `project_doc_fallback_filenames = ["CLAUDE.md"]` and
    `context.fileName = ["CLAUDE.md"]` are removed: each CLI reads its native file (INSTRUCTION_FILES), which
    walk_builders.build_run_tree places in the checkout as a byte-identical copy of the pinned tree's CLAUDE.md.

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
CODEX_REASONING_EFFORT = PENDING
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
# or accepted): Codex's AGENTS.md, Gemini CLI's GEMINI.md. walk_builders.build_run_tree places each as a copy of the
# pinned tree's CLAUDE.md, the file the claude-code arm reads.
INSTRUCTION_FILES = {CODEX: "AGENTS.md", GEMINI: "GEMINI.md"}
# Each, once measured: {"path": "<dotted path>", "value": <JSON value>}.
GEMINI_THINKING = PENDING
GEMINI_AUTH_SETTING = PENDING
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
    lines = [f"model = {_toml_value(_model(model))}",
             f"model_reasoning_effort = {_toml_value(CODEX_REASONING_EFFORT)}"]
    lines += [f"{k} = {_toml_value(v)}" for k, v in CODEX_TOP]
    lines += ["", "[features]"] + [f"{k} = {_toml_value(v)}" for k, v in CODEX_FEATURES]
    return {CODEX_CONFIG: ("\n".join(lines) + "\n").encode("ascii")}


def _gemini(model) -> dict:
    doc = {}
    for path, value in GEMINI_SETTINGS:
        _set(doc, path, value)
    _set(doc, GEMINI_MODEL_PATH, _model(model))
    for measured in (GEMINI_THINKING, GEMINI_AUTH_SETTING):
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
