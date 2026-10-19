#!/usr/bin/env python3
"""box/settings_guard.py: the vendor CLIs' workspace configuration in the run tree (glitch-26's ruling B10, Sun 18 Oct
2026, from review REVIEW-vendor-r18-b9-9497bf9 MINOR 1).

With folder trust off (ruling B9, take_config.GEMINI_TRUST_SETTING) the pinned Gemini CLI 0.64.0 treats the take's
working folder, the run tree's root (run_take's `--workdir spec.run_tree`), as trusted, and every turn is a fresh
process that reads its workspace configuration from there at startup. The pinned Codex (rust-v0.162.1) reads skills
from the same root whether or not the project is trusted. The agent runs in yolo or bypass mode and can write the run
tree, so a file written in turn k would configure turn k+1. The settings guard refuses each path a pinned vendor CLI
reads there (settings_guard.WORKSPACE_PATHS, sourced in WORKSPACE_SOURCES) at build time (baseline) and on every
snapshot (snapshot_problems), the same refusal the .claude/ paths get, for every take as the .claude/ guard is.
GEMINI.md, placed by the run tree beside every CLAUDE.md under R-6, stays allowed exactly as the design places it.

Bound to real data: the pinned run tree's shipped settings file (gars/.claude/settings.json at 844a4ce0), the pinned
tree's file list (no .gemini/, .agents/ or .codex/ path), athena's stub take 5 pre-1 snapshot, and snapshots taken by
the sidecar's own snapshot_tree of a real folder between two guard calls. Each guarded path class, each folder rule and
the baseline-versus-snapshot split is also run against an in-memory mutant, printed with its red result.
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
STUDY = Path(__file__).resolve().parents[1]
REPO = STUDY.parents[1]
sys.path.insert(0, str(STUDY))
from box import settings_guard as sg  # noqa: E402
from box import sidecar  # noqa: E402
from box import take_config  # noqa: E402

PINNED = "844a4ce0d89437ca043363981a86096f6383a141"


def _show(rel: str) -> bytes:
    return subprocess.run(["git", "-C", str(REPO), "show", f"{PINNED}:{rel}"], capture_output=True,
                          check=True).stdout


SHIPPED = _show("gars/.claude/settings.json")
INSTRUCTIONS = {rel: _show(rel) for rel in ("CLAUDE.md", "gars/CLAUDE.md")}
PINNED_NAMES = subprocess.run(["git", "-C", str(REPO), "ls-tree", "-r", "--name-only", PINNED],
                              capture_output=True, check=True, text=True).stdout.splitlines()
RUN5 = REPO / "lane-reports" / "stub-take-20261014" / "stub-take-run5.derived.json"
MODEL = "gemini-3.8-flash"
SHIPPED_BASE = {"gars/.claude/settings.json": hashlib.sha256(SHIPPED).hexdigest()}

# The record of the static reads (R3's rule: file, line, and the file's sha256 or git blob), as the builder read them
# from the unpacked pinned Gemini package (cli.tgz sha256 891a794e...8365e6) and the pinned Codex source (each file
# fetched at the commit and checked against the commit's tree by its blob id).
PKG = {"package": "@google/gemini-cli", "version": "0.64.0",
       "tarball_sha256": "891a794e55c8319b6b78f6f8f13d6b8b2782a4709dfd2fcabf3a1f63ae8365e6"}
NR7 = {"file": "bundle/chunk-NR7L3FXV.js",
       "file_sha256": "d566e81b1df8d4d44a91bf7aeea96a58ec0e6c8934fa424315ef060507dcbb8c"}
FLKY = {"file": "bundle/chunk-FLKY6NH5.js",
        "file_sha256": "f6a4ddd46350dad40515218069d369aaa0025f194c552400b69925b941098bc8"}
Q2G = {"file": "bundle/gemini-Q2GRYIAK.js",
       "file_sha256": "7702da31cf099ca3e1d64fd195f15b7726b2c2829ec21e955558eb9dbfba47da"}
MA35 = {"file": "bundle/chunk-MA35JFUP.js",
        "file_sha256": "5afb745a6015fcdd0108c6fa33112e8250bb93774e73634641f458e89f990985"}
ENTRY = {"file": "bundle/gemini.js",
         "file_sha256": "ab113d84c8f1692fd6c95081366718897876d8664328c7bf0ccf9437d688145f"}
CODEX = {"package": "openai/codex", "tag": "rust-v0.162.1", "commit": "092d3acd6bec3e3a14bdc7e7a2810ab628ab759d"}
HOST_ROOTS = {"file": "codex-rs/ext/skills/src/host_roots.rs", "blob": "ac2bf3e9cdf8ccf0c396f011f3dbb8f515db39c7"}
LOADER = {"file": "codex-rs/config/src/loader/mod.rs", "blob": "e524076d7b8dd0b8bff03c0082265fd4d8ab92b7"}
STATE = {"file": "codex-rs/config/src/state.rs", "blob": "ed3d13ccce1fea4776bd7c62109e6914daabb2f7"}
MARKERS = {"file": "codex-rs/config/src/project_root_markers.rs", "blob": "3061dacc6b793cc33265a81ed704d8369240bbfc"}
EXEC_POLICY = {"file": "codex-rs/core/src/exec_policy.rs", "blob": "21e414ed01b2040830790e8b486d17edd83309dd"}
AGENTS_MD = {"file": "codex-rs/core/src/agents_md.rs", "blob": "8e0c475d90339a236f51da33f85e70b967a61f26"}
ARG0 = {"file": "codex-rs/arg0/src/lib.rs", "blob": "c3467367190389297406c1aefd40d42ca503b6b5"}
HOME_DIR = {"file": "codex-rs/utils/home-dir/src/lib.rs", "blob": "caa43569c78bae9f5cc875092f378f4d935b8063"}
MARKETPLACE = {"file": "codex-rs/core-plugins/src/marketplace.rs", "blob": "2199fe4e1e937e239304e0bf26ab56b793f8409c"}
MARKETPLACE_POLICY = {"file": "codex-rs/core-plugins/src/marketplace_policy.rs",
                      "blob": "d5907554fb0db454e81d6279927e8531fb552591"}
PLUGINS_LOCAL = {"file": "codex-rs/app-server/src/request_processors/plugins/local.rs",
                 "blob": "67cbd5c4bbde97d6dcffc11af3898b29725c46f4"}
AGENT_ROLES = {"file": "codex-rs/agent-roles/src/loader.rs", "blob": "a82649b8e10debe7a2b3c7e21e2e861d557ea3b7"}
SOURCES = {
    "gemini: the running bundle": dict(PKG, reads=[
        dict(ENTRY, lines={"main from gemini-Q2GRYIAK.js": 110}),
        dict(Q2G, lines={"from chunk-FLKY6NH5.js": 91, "from chunk-NR7L3FXV.js": 259})],
        read="the bin entry bundle/gemini.js loads main from gemini-Q2GRYIAK.js, which imports the core from "
             "chunk-NR7L3FXV.js and the CLI config from chunk-FLKY6NH5.js; gemini-6ESINPDZ.js, gemini-IPXWMEB5.js "
             "and their chunks (chunk-J7SXW2FI.js, chunk-PZ4GDG24.js among them) are imported by no file of the "
             "bundle, so every Gemini line below is cited in the files that run"),
    "gemini: the working folder": dict(PKG, reads=[
        dict(Q2G, lines={"cwd = process3.cwd()": 8275, "targetDir: cwd": 8542}),
        dict(NR7, lines={"this.storage = new Storage(this.targetDir, ...)": 380951,
                         "getGeminiDir: join(this.targetDir, GEMINI_DIR)": 253287,
                         "getAgentsDir: join(this.targetDir, AGENTS_DIR_NAME)": 253305,
                         "GEMINI_DIR = \".gemini\"": 252007, "AGENTS_DIR_NAME = \".agents\"": 253153,
                         "folder trust off: checkPathTrust returns trusted": 360569})],
        read="the workspace folders are joined to targetDir, the process's working folder (the run tree's root "
             "under run_take's --workdir), never to a parent or a sub-folder; with folder trust off every trust "
             "gate below passes"),
    "codex: the working folder": dict(CODEX, reads=[
        dict(MARKERS, lines={"DEFAULT_PROJECT_ROOT_MARKERS = [\".git\"]": 5}),
        dict(LOADER, lines={"each folder from the project root to cwd: dir.join(\".codex\")": 1682})],
        read="the run tree is a git repository (drive.clean_run_tree) and the working folder its root, so the "
             "project root is the working folder and only its own .codex/ and .agents/ are read"),
    ".gemini/settings.json": dict(PKG, reads=[
        dict(NR7, lines={"getWorkspaceSettingsPath": 253392}),
        dict(FLKY, lines={"new Storage(workspaceDir)": 16670, "workspaceSettingsPath": 16671,
                          "mergeSettings(..., workspaceSettings, isTrusted)": 16809,
                          "safeWorkspace = isTrusted ? workspace : {}": 16336}),
        dict(Q2G, lines={"projectHooks: settings.workspace.settings.hooks": 17534,
                         "mcpServers from the merged settings": 8481})],
        read="merged over the user settings, so it can set modelConfigs, mcpServers (stdio servers among them), "
             "hooks, policyPaths, context.fileName and any other setting"),
    ".gemini/agents": dict(PKG, reads=[dict(NR7, lines={"getProjectAgentsDir": 253404,
                                                         "trust gate": 342538, "loadAgentsFromDirectory": 342540})],
                           read="project subagent definitions (experimental.enableAgents defaults true)"),
    ".gemini/skills": dict(PKG, reads=[dict(NR7, lines={"getProjectSkillsDir": 253398, "trust gate": 366395,
                                                         "loadSkillsFromDir": 366399})],
                           read="project skills (skills.enabled defaults true)"),
    ".gemini/commands": dict(PKG, reads=[dict(NR7, lines={"getProjectCommandsDir": 253395}),
                                         dict(MA35, lines={"trust gate": 75002, "project commands folder": 75004})],
                             read="custom commands, loaded at startup"),
    ".agents/skills": {"gemini": dict(PKG, reads=[dict(NR7, lines={"getProjectAgentSkillsDir": 253401,
                                                                    "loadSkillsFromDir": 366401})],
                                      read="project agent skills, after .gemini/skills"),
                       "codex": dict(CODEX, reads=[dict(HOST_ROOTS, lines={"repo_agents_skill_roots": 137,
                                                                            ".agents/skills, no trust check": 154})],
                                     read="repository skills in each folder from the project root to cwd, whatever "
                                          "the project's trust")},
    ".codex/skills": dict(CODEX, reads=[
        dict(HOST_ROOTS, lines={"every layer, disabled ones included": 80, "a project layer": 86,
                                "its config folder's skills": 89}),
        dict(LOADER, lines={"a .codex folder makes a project layer, disabled when untrusted": 1682,
                            "an empty layer when it holds no config.toml": 1760})],
        read="skills from a project's .codex/skills, read from the disabled (untrusted) project layer too"),
    "not guarded: .gemini/policies": dict(PKG, reads=[dict(Q2G, lines={"disableWorkspacePolicies = true": 7881,
                                                                        "the only load, gated on it": 7906})],
                                          read="workspace policies are switched off in the pinned build"),
    "not guarded: .gemini/extensions": dict(PKG, reads=[dict(NR7, lines={"Storage.getExtensionsDir": 253479}),
                                                        dict(MA35, lines={"extensions from homedir() only": 61264})],
                                            read="extensions load from GEMINI_CLI_HOME (the per-take config "
                                                 "folder), never from the working folder"),
    "not guarded: .gemini/system.md and .gemini/sandbox*": dict(PKG, reads=[
        dict(NR7, lines={"system.md, only when GEMINI_SYSTEM_MD is set": 336179}),
        dict(Q2G, lines={"sandbox profile, only under GEMINI_SANDBOX or --sandbox": 10097})],
        read="each needs a variable or flag the box never passes (run_take refuses GEMINI_SYSTEM_MD and "
             "GEMINI_SANDBOX by name)"),
    # Review r18-b10 finding 1 (B10-F1): the .env walk reaches past the run tree, to / and HOME.
    "not guarded here: .env and .gemini/.env": {
        "gemini": dict(PKG, reads=[
            dict(FLKY, lines={"findEnvFile: from the working folder up to /": 16542,
                              "<folder>/.gemini/.env, first (trusted)": 16546, "<folder>/.env": 16551,
                              "after /: homedir()/.gemini/.env": 16560, "then homedir()/.env": 16565,
                              "loadEnvironment's call": 16610, "each key not yet set is set": 16639}),
            dict(NR7, lines={"homedir(): GEMINI_CLI_HOME, else os.homedir()": 252011})],
            read="the first of these found is loaded, a .gemini/ file without the excluded-variable filter"),
        "codex": dict(CODEX, reads=[dict(ARG0, lines={"load_dotenv, before any thread": 159,
                                                       "CODEX_HOME/.env only": 305}),
                                    dict(HOME_DIR, lines={"find_codex_home reads CODEX_HOME": 14})],
                      read="the only .env read outside test code; CODEX_ names are dropped"),
        "read": "run_take's in-container launcher (LAUNCHER_SOURCE) refuses .gemini/.env and .env, before every harness "
                "exec of every arm, in CODEX_HOME (a codex row), the container's working folder, each config home "
                "and HOME, each with every ancestor up to /, in that order; R-H5 made arms O's and G's HOME the run "
                "tree's .home while CODEX_HOME and GEMINI_CLI_HOME stay the config mount (run_take.TAKE_ENV), so the "
                "walk reads them as two folders (R-H5-1) and every file either CLI reads is among them; "
                "run_take.refuse_env_files, host-side, covers the run tree, the agent's home and the config folder "
                "only, as an early refusal"},
    "not guarded: .geminiignore": dict(PKG, reads=[dict(NR7, lines={"GEMINI_IGNORE_FILE_NAME": 313670,
                                                                     "the ignore filter": 314189})],
                                       read="it filters only what the agent's own file tools list"),
    "not guarded: Codex plugin marketplaces": dict(CODEX, reads=[
        dict(MARKETPLACE, lines={"the repository marketplace paths": 20}),
        dict(MARKETPLACE_POLICY, lines={"plugins enabled from the effective config only": 214}),
        dict(PLUGINS_LOCAL, lines={"repository scopes, on the app-server road only": 34})],
        read="a listing reads them; nothing is enabled from a disabled project layer, and codex exec builds no "
             "repository scope"),
    "not guarded: .codex/agents": dict(CODEX, reads=[dict(AGENT_ROLES, lines={"enabled layers only": 29,
                                                                               "<layer>/agents": 78})],
                                       read="agent roles come from enabled layers, never the disabled project one"),
    "not guarded: .codex/config.toml, hooks, rules and MCP": dict(CODEX, reads=[
        dict(LOADER, lines={"a layer is enabled only when trusted": 1094}),
        dict(STATE, lines={"effective_config merges enabled layers only": 532,
                           "layers_low_to_high drops disabled layers": 605}),
        dict(EXEC_POLICY, lines={"rules from enabled layers only": 669})],
        read="the take's CODEX_HOME config.toml has no [projects] table, so the project layer is disabled and its "
             "settings, hooks, MCP servers and rules never load (hooks are also off by [features] hooks = false)"),
    "not guarded: instruction files": {
        "gemini": dict(PKG, reads=[], read="GEMINI.md, placed by R-6 beside every CLAUDE.md"),
        "codex": dict(CODEX, reads=[dict(AGENTS_MD, lines={"skipped only when explicitly untrusted": 64,
                                                           "AGENTS.override.md, then AGENTS.md": 274})],
                      read="AGENTS.md, placed by R-6 beside every CLAUDE.md; AGENTS.override.md at the root is read "
                           "first"),
        "read": "instruction files are left to the agent, as CLAUDE.md is for the claude-code arm; whether an "
                "agent-written instruction file should refuse is open (B10's report)"},
}
GUARDED = {".gemini/settings.json": "file", ".gemini/agents": "folder", ".gemini/skills": "folder",
           ".gemini/commands": "folder", ".agents/skills": "folder", ".codex/skills": "folder"}
FOLDERS = (".gemini", ".agents", ".codex")

# Every path the guard refuses once the run tree gains it between turns: case -> (relative path, kind, class), kind
# "file" (bytes), "dir", or "link" (to a folder outside the tree); class is the GUARDED key or FOLDERS entry it falls
# under, for the mutants.
GAINED = {
    "workspace settings": (".gemini/settings.json", "file", ".gemini/settings.json"),
    "workspace settings as a link": (".gemini/settings.json", "link", ".gemini/settings.json"),
    "a project agent": (".gemini/agents/helper.md", "file", ".gemini/agents"),
    "a nested project agent": (".gemini/agents/deep/helper.md", "file", ".gemini/agents"),
    ".gemini/agents as a link": (".gemini/agents", "link", ".gemini/agents"),
    "a project skill": (".gemini/skills/helper/SKILL.md", "file", ".gemini/skills"),
    "a project skill as a link": (".gemini/skills/helper", "link", ".gemini/skills"),
    "a custom command": (".gemini/commands/go.toml", "file", ".gemini/commands"),
    ".gemini/commands as a file": (".gemini/commands", "file", ".gemini/commands"),
    "a repository agent skill": (".agents/skills/helper/SKILL.md", "file", ".agents/skills"),
    ".agents/skills as a file": (".agents/skills", "file", ".agents/skills"),
    "a codex project skill": (".codex/skills/helper/SKILL.md", "file", ".codex/skills"),
    ".codex/skills as a link": (".codex/skills", "link", ".codex/skills"),
    ".gemini as a link": (".gemini", "link", ".gemini"),
    ".gemini as a file": (".gemini", "file", ".gemini"),
    ".agents as a link": (".agents", "link", ".agents"),
    ".codex as a link": (".codex", "link", ".codex"),
    ".codex as a file": (".codex", "file", ".codex"),
}
# Paths no pinned vendor CLI reads from the run tree (or another check covers), which the guard leaves alone.
LEFT_ALONE = [(".gemini/policies/p.toml", "file"), (".gemini/extensions/x/gemini-extension.json", "file"),
              (".gemini/system.md", "file"), (".gemini/tmp", "dir"), ("gars/.gemini/settings.json", "file"),
              ("gars/.agents/skills/x/SKILL.md", "file"), ("gars/.codex/skills/x/SKILL.md", "file"),
              (".agents/notes.md", "file"), (".codex/config.toml", "file"), (".codex/hooks.json", "file"),
              (".codex/rules/x.rules", "file"), (".gemini/skills", "dir"), (".gemini/skills/empty", "dir"),
              (".agents/skills", "dir"), (".codex/skills", "dir"), ("notes/.gemini-settings.json", "file")]


class Tree:
    """A run tree built as walk_builders builds a gemini take's: the shipped settings file, CLAUDE.md and
    gars/CLAUDE.md, and R-6's GEMINI.md beside each (a byte-identical copy)."""

    def __init__(self):
        self.d = tempfile.mkdtemp(prefix="vwg-")
        self.root = os.path.join(self.d, "t")
        self.outside = os.path.join(self.d, "outside")
        os.makedirs(os.path.join(self.root, "gars", ".claude"))
        os.makedirs(os.path.join(self.outside, "skills", "x"))
        Path(self.outside, "settings.json").write_text("{}")
        Path(self.outside, "skills", "x", "SKILL.md").write_text("---\nname: x\n---\n")
        Path(self.root, "gars", ".claude", "settings.json").write_bytes(SHIPPED)
        for rel, data in INSTRUCTIONS.items():
            Path(self.root, rel).write_bytes(data)
            Path(self.root, os.path.dirname(rel), take_config.INSTRUCTION_FILES[take_config.GEMINI]).write_bytes(data)
        Path(self.root, "README.md").write_text("x\n")

    def put(self, rel: str, kind: str):
        p = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        if kind == "file":
            Path(p).write_text("{\"model\": {\"name\": \"other\"}}\n")
        elif kind == "dir":
            os.makedirs(p, exist_ok=True)
        else:
            os.symlink(self.outside, p)

    def snapshot(self, label: str) -> dict:
        entries, _special, _blobs = sidecar.snapshot_tree(self.root, ())
        return {"label": label, "taken_at": 0.0, "entries": entries}

    def close(self):
        shutil.rmtree(self.d)


@contextlib.contextmanager
def tree():
    t = Tree()
    try:
        yield t
    finally:
        t.close()


def between_turns(rel: str, kind: str) -> list:
    """Baseline a clean run tree (it must pass with exactly the shipped settings file), let the 'agent' write `rel`
    after turn 1, and return snapshot post-1's problems."""
    with tree() as t:
        base = sg.baseline(t.root, model=MODEL)
        if base != SHIPPED_BASE:
            return [f"the clean tree's baseline is {base}"]
        pre = sg.snapshot_problems(t.snapshot("pre-1"), base)
        if pre:
            return [f"the clean tree's pre-1 snapshot refuses: {pre}"]
        t.put(rel, kind)
        return sg.snapshot_problems(t.snapshot("post-1"), base)


def built_with(rel: str, kind: str):
    """The baseline's verdict on a run tree that ships `rel`: None when it passes, else the refusal text."""
    with tree() as t:
        t.put(rel, kind)
        try:
            sg.baseline(t.root, model=MODEL)
        except sg.SettingsRefused as e:
            return str(e)
        return None


def check_snapshots() -> list:
    out = []
    for case, (rel, kind, _cls) in GAINED.items():
        got = between_turns(rel, kind)
        if not got:
            out.append(f"snapshot: {case} gained between turns is not caught")
        elif not any(rel in p for p in got):
            out.append(f"snapshot: {case}'s problems do not name {rel}: {got}")
    return out


def check_baseline() -> list:
    out = []
    for case, (rel, kind, _cls) in GAINED.items():
        got = built_with(rel, kind)
        if got is None:
            out.append(f"baseline: a run tree shipping {case} passes")
        elif rel not in got:
            out.append(f"baseline: {case}'s refusal does not name {rel}: {got}")
    return out


def check_left_alone() -> list:
    out = []
    for rel, kind in LEFT_ALONE:
        got = between_turns(rel, kind)
        if got:
            out.append(f"left alone: {rel} ({kind}) is refused at a snapshot: {got}")
        if built_with(rel, kind) is not None:
            out.append(f"left alone: {rel} ({kind}) is refused at the baseline")
    return out


def check_athena_snapshot() -> list:
    """Athena's stub take 5 pre-1 snapshot passes, and fails once it gains each guarded file entry."""
    doc = json.loads(RUN5.read_text())
    snap = json.loads(doc["evidence"]["snapshots/pre-1.json"]["text"])
    out = [] if sg.snapshot_problems(snap, SHIPPED_BASE) == [] else ["snapshot: athena's pre-1 refuses"]
    for rel in (".gemini/settings.json", ".gemini/agents/a.md", ".gemini/skills/s/SKILL.md", ".gemini/commands/c.toml",
                ".agents/skills/s/SKILL.md", ".codex/skills/s/SKILL.md"):
        s = json.loads(json.dumps(snap))
        s["entries"][rel] = {"type": "file", "sha256": "7" * 64}
        if not sg.snapshot_problems(s, SHIPPED_BASE):
            out.append(f"snapshot: athena's pre-1 with {rel} added passes")
    for rel in FOLDERS:
        for entry in ({"type": "link", "target": "/tmp"}, {"type": "unreadable"}):
            s = json.loads(json.dumps(snap))
            s["entries"][rel] = entry
            if not sg.snapshot_problems(s, SHIPPED_BASE):
                out.append(f"snapshot: athena's pre-1 with {rel} a {entry['type']} passes")
    return out


def check_all() -> list:
    return check_snapshots() + check_baseline() + check_left_alone() + check_athena_snapshot()


def uncaught() -> set:
    return {case for case, (rel, kind, _cls) in GAINED.items()
            if not between_turns(rel, kind) or built_with(rel, kind) is None}


def without(name: str, key):
    """A mutant: settings_guard's `name` (a dict or a tuple) without `key`."""
    def patch():
        cur = getattr(sg, name, None)
        new = ({k: v for k, v in cur.items() if k != key} if isinstance(cur, dict)
               else tuple(v for v in (cur or ()) if v != key))
        return mock.patch.object(sg, name, new, create=True)
    return patch


def mutants() -> list:
    out = [(f"{cls} dropped from WORKSPACE_PATHS", without("WORKSPACE_PATHS", cls), cls) for cls in GUARDED]
    out += [(f"{d} dropped from WORKSPACE_FOLDERS", without("WORKSPACE_FOLDERS", d), d) for d in FOLDERS]
    out += [("the baseline's workspace check skipped",
             lambda: mock.patch.object(sg, "workspace_tree_problems", lambda run_tree: [], create=True), "baseline"),
            ("the snapshot's workspace check skipped",
             lambda: mock.patch.object(sg, "workspace_snapshot_problems", lambda entries: [], create=True),
             "snapshot")]
    return out


class TheGuard(unittest.TestCase):
    def test_the_pinned_tree_ships_no_vendor_workspace_path(self):
        """Turn 1 is clean by construction: no .gemini/, .agents/ or .codex/ path anywhere in the pinned tree, and
        no GEMINI.md or AGENTS.md either (R-6 places them)."""
        self.assertGreater(len(PINNED_NAMES), 100)
        self.assertEqual([n for n in PINNED_NAMES if any(f"/{d}/" in "/" + n for d in FOLDERS)
                          or n.split("/")[-1] in ("GEMINI.md", "AGENTS.md", "AGENTS.override.md")], [])
        # the run tree drops evals/ (check_take's exclusions), which holds gap-study-2's fixture checkout
        self.assertEqual(sorted(n for n in PINNED_NAMES if n.split("/")[-1] == "CLAUDE.md"
                                and not n.startswith("evals/")), sorted(INSTRUCTIONS))

    def test_a_placed_gemini_md_is_not_caught(self):
        with tree() as t:
            self.assertTrue(os.path.isfile(os.path.join(t.root, "GEMINI.md")))
            self.assertTrue(os.path.isfile(os.path.join(t.root, "gars", "GEMINI.md")))
            base = sg.baseline(t.root, model=MODEL)
            self.assertEqual(base, SHIPPED_BASE)
            self.assertEqual(sg.snapshot_problems(t.snapshot("pre-1"), base), [])
            self.assertEqual(sg.snapshot_problems(t.snapshot("post-1"), base), [])

    def test_each_guarded_path_gained_between_turns_is_caught(self):
        self.assertEqual(check_snapshots(), [])

    def test_each_guarded_path_refuses_at_build_time(self):
        self.assertEqual(check_baseline(), [])

    def test_paths_no_pinned_cli_reads_are_left_alone(self):
        self.assertEqual(check_left_alone(), [])

    def test_athena_pre1_snapshot(self):
        self.assertEqual(check_athena_snapshot(), [])

    def test_the_guarded_set_and_its_record(self):
        self.assertEqual(getattr(sg, "WORKSPACE_PATHS", None), GUARDED)
        self.assertEqual(getattr(sg, "WORKSPACE_FOLDERS", None), FOLDERS)
        self.assertEqual(getattr(sg, "WORKSPACE_SOURCES", None), SOURCES)
        self.assertEqual(sorted(k for k in SOURCES if not k.startswith(("not guarded", "gemini:", "codex:"))),
                         sorted(GUARDED))
        self.assertEqual({cls for _rel, _kind, cls in GAINED.values()}, set(GUARDED) | set(FOLDERS))

    def test_mutants_each_red_alone(self):
        self.assertEqual(check_all(), [], "the guard is not green, so no mutant can be judged")
        for name, patch, cls in mutants():
            with self.subTest(mutant=name):
                with patch():
                    got = check_all()
                    lost = uncaught()
                print(f"mutant {name}: {'red' if got else 'GREEN (survived)'} ({len(got)} failures; first: "
                      f"{got[0] if got else '-'})")
                self.assertTrue(got, f"mutant {name} survived")
                if cls in ("baseline", "snapshot"):
                    self.assertTrue(all(g.startswith(cls) for g in got), f"mutant {name} reddened another check: {got}")
                    continue
                own = {case for case, (_rel, _kind, c) in GAINED.items() if c == cls}
                self.assertTrue(lost & own, f"mutant {name} leaves none of its own cases uncaught: {got}")
                self.assertLessEqual(lost, own, f"mutant {name} leaves cases outside its class uncaught: {lost - own}")


# B10-F1 (review r18-b10 finding 1): an env file planted outside the run tree, where the take container's writable /tmp
# sits above it, is refused before the next exec by run_take's in-container launcher (LAUNCHER_SOURCE). The launcher
# runs in-process with os.execvpe faked, from a working folder laid out as the box lays it out (<tmp>/run-x); no
# process starts. R-H5-1 (glitch-26's ruling, Mon 19 Oct 2026): HOME is the run tree's .home and the config home a
# separate folder (<d>/opt/cfg, as the mount /opt/cfg), each walked as its own folder with its ancestors, for the
# Gemini row and the Codex row alike.
from box import run_take as rt  # noqa: E402

ENV_NAMES = (".env", ".gemini/.env")
ENV_ROWS = {rt.GEMINI: ("GEMINI_API_KEY", "GEMINI_CLI_HOME", ["gemini", "-p", "x"]),
            rt.CODEX: (rt.NO_LOGIN, "CODEX_HOME", ["codex", "exec", "x"])}


def launch(cwd: str, home: str, cfg: str, harness: str = rt.GEMINI):
    """'exec' when the launcher would exec the harness, else the launcher's refusal text."""
    got = {}
    login, home_var, argv = ENV_ROWS[harness]

    def fake_exec(prog, args, env):
        got["env"] = dict(env)
        raise SystemExit(0)
    here = os.getcwd()
    os.chdir(cwd)
    try:
        with mock.patch.object(os, "execvpe", fake_exec), mock.patch.dict(os.environ, {"GEMINI_API_KEY": "x"},
                                                                          clear=True), \
                mock.patch.object(sys, "argv", ["-c", login, "2", f"HOME={home}", f"{home_var}={cfg}", *argv]):
            try:
                exec(compile(rt.LAUNCHER_SOURCE, "<launcher>", "exec"), {"__name__": "__main__"})
            except SystemExit as e:
                return "exec" if "env" in got else str(e.code)
    finally:
        os.chdir(here)
    return "neither"


ENV_WHERE = ("run tree", "parent", "grandparent", "HOME", "config home", "above the config home")


def env_cases(wheres=ENV_WHERE):
    """(harness, where, name) -> launcher result after planting <where>/<name>: where is the run tree, its parent (the
    container's /tmp), its grandparent, HOME (the run tree's .home), the config home, or the config home's parent."""
    out = {}
    for harness in ENV_ROWS:
        for where in wheres:
            for name in ENV_NAMES:
                d = tempfile.mkdtemp(prefix="vwe-")
                try:
                    tmp = os.path.join(d, "tmp")
                    run = os.path.join(tmp, "run-x")
                    home = os.path.join(run, rt.RUN_TREE_HOMEDIR)
                    cfg = os.path.join(d, "opt", "cfg")
                    os.makedirs(home, mode=0o700)
                    os.makedirs(cfg)
                    base = {"run tree": run, "parent": tmp, "grandparent": d, "HOME": home, "config home": cfg,
                            "above the config home": os.path.dirname(cfg)}[where]
                    clean = launch(run, home, cfg, harness)
                    p = os.path.join(base, *name.split("/"))
                    os.makedirs(os.path.dirname(p), exist_ok=True)
                    Path(p).write_text("GEMINI_SYSTEM_MD=/tmp/x\n")
                    out[(harness, where, name)] = (clean, launch(run, home, cfg, harness))
                finally:
                    shutil.rmtree(d)
    return out


def walk_problems(cases) -> list:
    out = []
    for (harness, where, name), (clean, planted) in cases.items():
        if clean != "exec":
            out.append(f"env walk: the clean tree does not launch ({harness}: {clean})")
        if not planted.startswith("refusing .env file: "):
            out.append(f"env walk: {name} planted in the {where} is not refused ({harness}: {planted})")
    return out


def check_env_walk() -> list:
    out = walk_problems(env_cases())
    # R-H5-1: the rows are the two folders the walk above models: HOME the run tree's .home, the config home the mount
    for h in ENV_ROWS:
        row = rt.TAKE_ENV[h]
        home_var = ENV_ROWS[h][1]
        if row.get("HOME") != rt.RUN_TREE_HOME or row.get(home_var) != rt.CONFIG_MOUNT:
            out.append(f"env walk: {h}'s HOME and config home are not the run tree's home and the mount: "
                       f"{row.get('HOME')!r}, {row.get(home_var)!r}")
    return out


def check_config_home_env() -> list:
    """R-H5-1: a .env name planted in the config home, or above it, is refused for each row."""
    return walk_problems(env_cases(("config home", "above the config home")))


class TheEnvWalk(unittest.TestCase):
    def test_a_planted_env_file_above_the_run_tree_is_refused(self):
        """A /tmp/.gemini/.env (or .env) planted between turns, above the run tree, in HOME or in the tree itself,
        refuses the next exec; the harness never starts."""
        self.assertEqual(check_env_walk(), [])

    def test_mutants_each_red(self):
        self.assertEqual(check_env_walk(), [], "the launcher is not green, so no mutant can be judged")
        src = rt.LAUNCHER_SOURCE
        cases = {
            "the ancestor walk stops at the working folder": src.replace(" d=parent\n", " break\n"),
            "only .env is checked": src.replace("(os.path.join('.gemini','.env'),'.env')", "('.env',)"),
            "only .gemini/.env is checked": src.replace("(os.path.join('.gemini','.env'),'.env')",
                                                        "(os.path.join('.gemini','.env'),)"),
            "HOME is not checked": src.replace("+homes+[e['HOME']]", "+homes"),
        }
        for name, mutant in cases.items():
            with self.subTest(mutant=name):
                self.assertNotEqual(mutant, src, f"mutant {name} did not apply")
                with mock.patch.object(rt, "LAUNCHER_SOURCE", mutant):
                    got = check_env_walk()
                print(f"mutant {name}: {'red' if got else 'GREEN (survived)'} ({len(got)}; first: "
                      f"{got[0] if got else '-'})")
                self.assertTrue(got, f"mutant {name} survived")
                self.assertFalse([g for g in got if "clean tree" in g], f"mutant {name} broke the launcher: {got}")
        with mock.patch.dict(rt.TAKE_ENV[rt.GEMINI], {"GEMINI_CLI_HOME": "/opt/elsewhere"}):
            got = check_env_walk()
        print(f"mutant GEMINI_CLI_HOME off the mount: {'red' if got else 'GREEN (survived)'}")
        self.assertTrue(got, "mutant GEMINI_CLI_HOME off the mount survived")

    def test_a_planted_env_file_in_the_config_home_is_refused(self):
        """R-H5-1: a .env or .gemini/.env planted in the config home (or above it) refuses the next exec, for the
        Gemini row and the Codex row; its witness, the config homes dropped from the walk, goes red alone."""
        self.assertEqual(check_config_home_env(), [])
        src = rt.LAUNCHER_SOURCE
        mutant = src.replace("[e['CODEX_HOME']] if 'CODEX_HOME' in e else []", "[]").replace("+homes+", "+")
        self.assertNotEqual(mutant, src, "the witness did not apply")
        self.assertEqual(mutant.count("homes"), src.count("homes") - 1, "the witness touched more than the walk")
        with mock.patch.object(rt, "LAUNCHER_SOURCE", mutant):
            got = check_config_home_env()
        print(f"witness the config homes dropped from the walk: {'red' if got else 'GREEN (survived)'} ({len(got)}; "
              f"first: {got[0] if got else '-'})")
        self.assertTrue(got, "witness the config homes dropped from the walk survived")
        self.assertFalse([g for g in got if "clean tree" in g], f"the witness broke the launcher: {got}")
        self.assertTrue([g for g in got if "(codex:" in g] and [g for g in got if "(gemini:" in g],
                        f"the witness is not red for both rows: {got}")


if __name__ == "__main__":
    unittest.main()
