#!/usr/bin/env python3
"""The run tree's Claude Code settings files, guarded (glitch-06's ruling on review finding 1, 14 Oct 2026).

Every turn loads the project and local scopes (`--setting-sources project,local`), and those files sit in the run
tree, which the agent owns and can write with Bash. The study's own settings ride inline by `--settings` above them
(run_take.claude_study_settings), but a project or local file may still carry keys that change the model or its
fallbacks (an `env` block, `model`, `fallbackModel`, `switchModelsOnFlag`, `availableModels`; non-managed
`availableModels` lists merge). So:

    baseline(run_tree, *, model) -> {relative path: sha256}
        Host-side, after the run tree is built and BEFORE grant and launch (no watcher yet, so these reads are never
        logged as the agent's). Every `.claude/settings.json` and `.claude/settings.local.json` anywhere in the tree,
        links never followed; refuses (SettingsRefused) a settings file that is not a regular file, a `.claude` that
        is not a folder, JSON that is not an object, or any FORBIDDEN_KEYS key. GARS's shipped
        gars/.claude/settings.json (keys: hooks, permissions, at the pinned 844a4ce0) passes.
        Also every file under a `.claude/agents/`, `.claude/skills/` or `.claude/commands/` folder (round-2 review
        R2-6 for agents; closure-r2 note C-1 for skills and slash commands, which "accept the same frontmatter fields
        as skills", `model` among them: code.claude.com/docs/en/skills.md, read 14 Oct 2026): a file whose
        frontmatter `model:` is anything but absent, "inherit" or the take's pinned `model` refuses, and so does a
        link, a non-regular file, or a `agents`/`skills`/`commands` entry under `.claude` that is not a folder. GARS
        ships none of the three at the pinned 844a4ce0 (its only `.claude` file is gars/.claude/settings.json).
        (The Agent tool's own model parameter is outside any file: the harness's per-message served-model check backs
        it.)

    snapshot_problems(snapshot, baseline) -> [problem]
        On EVERY snapshot of the take (round-2 review R2-1): before every turn (pre-k, turn 1 included, so also at
        preflight's moment) and after every turn (post-k, the final turn and a single-turn take included), on the
        sidecar's own snapshot read
        from the evidence folder (never by opening the run tree, which the watcher would log): the settings files must
        be exactly the baseline's, each a regular file with the baseline's sha256, and no `.claude` may be anything
        but a folder. The snapshot holds hashes, not contents, so ANY change to a settings file refuses, not only a
        forbidden key (the stricter reading; the sidecar copies contents only for the pre-registered consequential
        paths, and adding these would change the instrument).
        A non-empty list refuses the turn: before turn 1 a rehearsal, after it a stop for a human ruling (drive.py's
        DriveRefused), the problems recorded. NAMED RESIDUAL (hot reload): Claude Code reloads a settings file when it changes, so a
        write takes effect inside the turn that makes it; the guard detects it at the next snapshot (that turn's
        post-k), never prevents it within the turn.

    THE VENDOR CLIs' WORKSPACE CONFIGURATION (glitch-26's ruling B10, Sun 18 Oct 2026, from review
    REVIEW-vendor-r18-b9-9497bf9 MINOR 1): with folder trust off (ruling B9) the pinned Gemini CLI 0.64.0 treats the
    take's working folder, the run tree's root (run_take's `--workdir spec.run_tree`), as trusted, and every turn is a
    fresh process that reads its workspace configuration from there; the pinned Codex reads skills from there whatever
    the project's trust. Each path WORKSPACE_PATHS names, found by a static read of the pinned packages recorded in
    WORKSPACE_SOURCES (file, line and sha256 or blob, R3's rule), refuses at the run tree's root only (neither CLI reads
    these from a parent or a sub-folder): baseline refuses a run tree that ships one (the pinned tree ships none), and
    snapshot_problems refuses one present at any snapshot, so a file the agent writes in turn k is caught at post-k,
    before turn k+1 is sent. WORKSPACE_FOLDERS must be folders where present. Applied to every take, whatever its
    harness, as the .claude/ paths are. Left alone, each with its line in WORKSPACE_SOURCES: the paths no pinned CLI
    reads there (Gemini's workspace policies, switched off in the build; its extensions, read from the config home;
    system.md and the sandbox files, behind variables the box refuses; Codex's untrusted project config.toml, hooks,
    rules and MCP servers; .geminiignore; Codex's plugin marketplaces and .codex/agents), the .env files (read from
    the working folder up to / and HOME, which run_take's in-container launcher refuses before every exec; B10-F1),
    and the instruction files (GEMINI.md and AGENTS.md, placed by R-6 beside every CLAUDE.md, as CLAUDE.md is left
    to the claude-code arm's agent).

Standard library only.
"""

from __future__ import annotations

import hashlib
import json
import os
import re

# apiKeyHelper (box lane, 14 Oct 2026, with the walk-token road): its output outranks CLAUDE_CODE_OAUTH_TOKEN in Claude
# Code's authentication precedence (code.claude.com/docs/en/authentication, items 4 and 5), so a run-tree settings file
# carrying it would replace the walk's subscription login with another credential.
FORBIDDEN_KEYS = ("env", "model", "fallbackModel", "switchModelsOnFlag", "availableModels", "apiKeyHelper")
SETTINGS_NAMES = ("settings.json", "settings.local.json")
SETTINGS_PATH = re.compile(r"(?:^|.*/)\.claude/settings(?:\.local)?\.json")
# The `.claude` folders whose files can name a model in their frontmatter: agent definitions (R2-6), skills and
# slash commands (closure-r2 note C-1). Each is guarded the same way.
MODEL_DIRS = ("agents", "skills", "commands")
AGENTS_PATH = re.compile(r"(?:^|.*/)\.claude/(?:agents|skills|commands)/.+")
CLAUDE_DIR = re.compile(r"(?:^|.*/)\.claude")
AGENTS_DIR = re.compile(r"(?:^|.*/)\.claude/(?:agents|skills|commands)")
AGENT_MODELS_ALLOWED = ("inherit",)          # plus the take's pinned model; an absent `model:` inherits too
MAX_BYTES = 2 * 1024 * 1024

# The vendor CLIs' workspace configuration at the run tree's root (ruling B10; module docstring): {relative path:
# "file" | "folder"}. A "file" refuses whenever present; a "folder" refuses unless it is a folder holding only folders.
WORKSPACE_PATHS = {".gemini/settings.json": "file", ".gemini/agents": "folder", ".gemini/skills": "folder",
                   ".gemini/commands": "folder", ".agents/skills": "folder", ".codex/skills": "folder"}
# The parents, which must be folders where present (a link would carry the paths above out of the snapshot's view).
WORKSPACE_FOLDERS = (".gemini", ".agents", ".codex")
# R3's record of each static read (B10, the builder's read of 18 Oct 2026): the unpacked pinned Gemini package
# (cli.tgz sha256 891a794e...8365e6), each file's sha256, and the pinned Codex source, each file fetched at the commit
# and checked against the commit's tree by its blob id. tests/test_vendor_workspace_guard.py mirrors it.
_W_PKG = {"package": "@google/gemini-cli", "version": "0.64.0",
          "tarball_sha256": "891a794e55c8319b6b78f6f8f13d6b8b2782a4709dfd2fcabf3a1f63ae8365e6"}
_W_NR7 = {"file": "bundle/chunk-NR7L3FXV.js",
          "file_sha256": "d566e81b1df8d4d44a91bf7aeea96a58ec0e6c8934fa424315ef060507dcbb8c"}
_W_FLKY = {"file": "bundle/chunk-FLKY6NH5.js",
           "file_sha256": "f6a4ddd46350dad40515218069d369aaa0025f194c552400b69925b941098bc8"}
_W_Q2G = {"file": "bundle/gemini-Q2GRYIAK.js",
          "file_sha256": "7702da31cf099ca3e1d64fd195f15b7726b2c2829ec21e955558eb9dbfba47da"}
_W_MA35 = {"file": "bundle/chunk-MA35JFUP.js",
           "file_sha256": "5afb745a6015fcdd0108c6fa33112e8250bb93774e73634641f458e89f990985"}
_W_ENTRY = {"file": "bundle/gemini.js",
            "file_sha256": "ab113d84c8f1692fd6c95081366718897876d8664328c7bf0ccf9437d688145f"}
_W_CODEX = {"package": "openai/codex", "tag": "rust-v0.162.1", "commit": "092d3acd6bec3e3a14bdc7e7a2810ab628ab759d"}
_W_HOST_ROOTS = {"file": "codex-rs/ext/skills/src/host_roots.rs", "blob": "ac2bf3e9cdf8ccf0c396f011f3dbb8f515db39c7"}
_W_LOADER = {"file": "codex-rs/config/src/loader/mod.rs", "blob": "e524076d7b8dd0b8bff03c0082265fd4d8ab92b7"}
_W_STATE = {"file": "codex-rs/config/src/state.rs", "blob": "ed3d13ccce1fea4776bd7c62109e6914daabb2f7"}
_W_MARKERS = {"file": "codex-rs/config/src/project_root_markers.rs", "blob": "3061dacc6b793cc33265a81ed704d8369240bbfc"}
_W_EXEC_POLICY = {"file": "codex-rs/core/src/exec_policy.rs", "blob": "21e414ed01b2040830790e8b486d17edd83309dd"}
_W_AGENTS_MD = {"file": "codex-rs/core/src/agents_md.rs", "blob": "8e0c475d90339a236f51da33f85e70b967a61f26"}
_W_ARG0 = {"file": "codex-rs/arg0/src/lib.rs", "blob": "c3467367190389297406c1aefd40d42ca503b6b5"}
_W_HOME_DIR = {"file": "codex-rs/utils/home-dir/src/lib.rs", "blob": "caa43569c78bae9f5cc875092f378f4d935b8063"}
_W_MARKETPLACE = {"file": "codex-rs/core-plugins/src/marketplace.rs",
                  "blob": "2199fe4e1e937e239304e0bf26ab56b793f8409c"}
_W_MARKETPLACE_POLICY = {"file": "codex-rs/core-plugins/src/marketplace_policy.rs",
                         "blob": "d5907554fb0db454e81d6279927e8531fb552591"}
_W_PLUGINS_LOCAL = {"file": "codex-rs/app-server/src/request_processors/plugins/local.rs",
                    "blob": "67cbd5c4bbde97d6dcffc11af3898b29725c46f4"}
_W_AGENT_ROLES = {"file": "codex-rs/agent-roles/src/loader.rs", "blob": "a82649b8e10debe7a2b3c7e21e2e861d557ea3b7"}
WORKSPACE_SOURCES = {
    "gemini: the running bundle": dict(_W_PKG, reads=[
        dict(_W_ENTRY, lines={"main from gemini-Q2GRYIAK.js": 110}),
        dict(_W_Q2G, lines={"from chunk-FLKY6NH5.js": 91, "from chunk-NR7L3FXV.js": 259})],
        read="the bin entry bundle/gemini.js loads main from gemini-Q2GRYIAK.js, which imports the core from "
             "chunk-NR7L3FXV.js and the CLI config from chunk-FLKY6NH5.js; gemini-6ESINPDZ.js, gemini-IPXWMEB5.js "
             "and their chunks (chunk-J7SXW2FI.js, chunk-PZ4GDG24.js among them) are imported by no file of the "
             "bundle, so every Gemini line below is cited in the files that run"),
    "gemini: the working folder": dict(_W_PKG, reads=[
        dict(_W_Q2G, lines={"cwd = process3.cwd()": 8275, "targetDir: cwd": 8542}),
        dict(_W_NR7, lines={"this.storage = new Storage(this.targetDir, ...)": 380951,
                         "getGeminiDir: join(this.targetDir, GEMINI_DIR)": 253287,
                         "getAgentsDir: join(this.targetDir, AGENTS_DIR_NAME)": 253305,
                         "GEMINI_DIR = \".gemini\"": 252007, "AGENTS_DIR_NAME = \".agents\"": 253153,
                         "folder trust off: checkPathTrust returns trusted": 360569})],
        read="the workspace folders are joined to targetDir, the process's working folder (the run tree's root "
             "under run_take's --workdir), never to a parent or a sub-folder; with folder trust off every trust "
             "gate below passes"),
    "codex: the working folder": dict(_W_CODEX, reads=[
        dict(_W_MARKERS, lines={"DEFAULT_PROJECT_ROOT_MARKERS = [\".git\"]": 5}),
        dict(_W_LOADER, lines={"each folder from the project root to cwd: dir.join(\".codex\")": 1682})],
        read="the run tree is a git repository (drive.clean_run_tree) and the working folder its root, so the "
             "project root is the working folder and only its own .codex/ and .agents/ are read"),
    ".gemini/settings.json": dict(_W_PKG, reads=[
        dict(_W_NR7, lines={"getWorkspaceSettingsPath": 253392}),
        dict(_W_FLKY, lines={"new Storage(workspaceDir)": 16670, "workspaceSettingsPath": 16671,
                          "mergeSettings(..., workspaceSettings, isTrusted)": 16809,
                          "safeWorkspace = isTrusted ? workspace : {}": 16336}),
        dict(_W_Q2G, lines={"projectHooks: settings.workspace.settings.hooks": 17534,
                         "mcpServers from the merged settings": 8481})],
        read="merged over the user settings, so it can set modelConfigs, mcpServers (stdio servers among them), "
             "hooks, policyPaths, context.fileName and any other setting"),
    ".gemini/agents": dict(_W_PKG, reads=[dict(_W_NR7, lines={"getProjectAgentsDir": 253404,
                                                         "trust gate": 342538, "loadAgentsFromDirectory": 342540})],
                           read="project subagent definitions (experimental.enableAgents defaults true)"),
    ".gemini/skills": dict(_W_PKG, reads=[dict(_W_NR7, lines={"getProjectSkillsDir": 253398, "trust gate": 366395,
                                                         "loadSkillsFromDir": 366399})],
                           read="project skills (skills.enabled defaults true)"),
    ".gemini/commands": dict(_W_PKG, reads=[dict(_W_NR7, lines={"getProjectCommandsDir": 253395}),
                                         dict(_W_MA35, lines={"trust gate": 75002, "project commands folder": 75004})],
                             read="custom commands, loaded at startup"),
    ".agents/skills": {"gemini": dict(_W_PKG, reads=[dict(_W_NR7, lines={"getProjectAgentSkillsDir": 253401,
                                                                    "loadSkillsFromDir": 366401})],
                                      read="project agent skills, after .gemini/skills"),
                       "codex": dict(_W_CODEX, reads=[dict(_W_HOST_ROOTS, lines={"repo_agents_skill_roots": 137,
                                                                            ".agents/skills, no trust check": 154})],
                                     read="repository skills in each folder from the project root to cwd, whatever "
                                          "the project's trust")},
    ".codex/skills": dict(_W_CODEX, reads=[
        dict(_W_HOST_ROOTS, lines={"every layer, disabled ones included": 80, "a project layer": 86,
                                "its config folder's skills": 89}),
        dict(_W_LOADER, lines={"a .codex folder makes a project layer, disabled when untrusted": 1682,
                            "an empty layer when it holds no config.toml": 1760})],
        read="skills from a project's .codex/skills, read from the disabled (untrusted) project layer too"),
    "not guarded: .gemini/policies": dict(_W_PKG, reads=[dict(_W_Q2G, lines={"disableWorkspacePolicies = true": 7881,
                                                                        "the only load, gated on it": 7906})],
                                          read="workspace policies are switched off in the pinned build"),
    "not guarded: .gemini/extensions": dict(_W_PKG, reads=[dict(_W_NR7, lines={"Storage.getExtensionsDir": 253479}),
                                                        dict(_W_MA35, lines={"extensions from homedir() only": 61264})],
                                            read="extensions load from GEMINI_CLI_HOME (the per-take config "
                                                 "folder), never from the working folder"),
    "not guarded: .gemini/system.md and .gemini/sandbox*": dict(_W_PKG, reads=[
        dict(_W_NR7, lines={"system.md, only when GEMINI_SYSTEM_MD is set": 336179}),
        dict(_W_Q2G, lines={"sandbox profile, only under GEMINI_SANDBOX or --sandbox": 10097})],
        read="each needs a variable or flag the box never passes (run_take refuses GEMINI_SYSTEM_MD and "
             "GEMINI_SANDBOX by name)"),
    # Review r18-b10 finding 1 (B10-F1): the .env walk reaches past the run tree, to / and HOME.
    "not guarded here: .env and .gemini/.env": {
        "gemini": dict(_W_PKG, reads=[
            dict(_W_FLKY, lines={"findEnvFile: from the working folder up to /": 16542,
                              "<folder>/.gemini/.env, first (trusted)": 16546, "<folder>/.env": 16551,
                              "after /: homedir()/.gemini/.env": 16560, "then homedir()/.env": 16565,
                              "loadEnvironment's call": 16610, "each key not yet set is set": 16639}),
            dict(_W_NR7, lines={"homedir(): GEMINI_CLI_HOME, else os.homedir()": 252011})],
            read="the first of these found is loaded, a .gemini/ file without the excluded-variable filter"),
        "codex": dict(_W_CODEX, reads=[dict(_W_ARG0, lines={"load_dotenv, before any thread": 159,
                                                       "CODEX_HOME/.env only": 305}),
                                    dict(_W_HOME_DIR, lines={"find_codex_home reads CODEX_HOME": 14})],
                      read="the only .env read outside test code; CODEX_ names are dropped"),
        "read": "run_take's in-container launcher (LAUNCHER_SOURCE) refuses .gemini/.env and .env, before every harness "
                "exec of every arm, in CODEX_HOME (a codex row), the container's working folder, each config home "
                "and HOME, each with every ancestor up to /, in that order; R-H5 made arms O's and G's HOME the run "
                "tree's .home while CODEX_HOME and GEMINI_CLI_HOME stay the config mount (run_take.TAKE_ENV), so the "
                "walk reads them as two folders (R-H5-1) and every file either CLI reads is among them; "
                "run_take.refuse_env_files, host-side, covers the run tree, the agent's home and the config folder "
                "only, as an early refusal"},
    "not guarded: .geminiignore": dict(_W_PKG, reads=[dict(_W_NR7, lines={"GEMINI_IGNORE_FILE_NAME": 313670,
                                                                     "the ignore filter": 314189})],
                                       read="it filters only what the agent's own file tools list"),
    "not guarded: Codex plugin marketplaces": dict(_W_CODEX, reads=[
        dict(_W_MARKETPLACE, lines={"the repository marketplace paths": 20}),
        dict(_W_MARKETPLACE_POLICY, lines={"plugins enabled from the effective config only": 214}),
        dict(_W_PLUGINS_LOCAL, lines={"repository scopes, on the app-server road only": 34})],
        read="a listing reads them; nothing is enabled from a disabled project layer, and codex exec builds no "
             "repository scope"),
    "not guarded: .codex/agents": dict(_W_CODEX, reads=[dict(_W_AGENT_ROLES, lines={"enabled layers only": 29,
                                                                               "<layer>/agents": 78})],
                                       read="agent roles come from enabled layers, never the disabled project one"),
    "not guarded: .codex/config.toml, hooks, rules and MCP": dict(_W_CODEX, reads=[
        dict(_W_LOADER, lines={"a layer is enabled only when trusted": 1094}),
        dict(_W_STATE, lines={"effective_config merges enabled layers only": 532,
                           "layers_low_to_high drops disabled layers": 605}),
        dict(_W_EXEC_POLICY, lines={"rules from enabled layers only": 669})],
        read="the take's CODEX_HOME config.toml has no [projects] table, so the project layer is disabled and its "
             "settings, hooks, MCP servers and rules never load (hooks are also off by [features] hooks = false)"),
    "not guarded: instruction files": {
        "gemini": dict(_W_PKG, reads=[], read="GEMINI.md, placed by R-6 beside every CLAUDE.md"),
        "codex": dict(_W_CODEX, reads=[dict(_W_AGENTS_MD, lines={"skipped only when explicitly untrusted": 64,
                                                           "AGENTS.override.md, then AGENTS.md": 274})],
                      read="AGENTS.md, placed by R-6 beside every CLAUDE.md; AGENTS.override.md at the root is read "
                           "first"),
        "read": "instruction files are left to the agent, as CLAUDE.md is for the claude-code arm; whether an "
                "agent-written instruction file should refuse is open (B10's report)"},
}


class SettingsRefused(ValueError):
    """A run tree's settings file the take may not start with. The message names the file and the rule."""


def agent_model(text: str):
    """The `model:` value of an agent definition's frontmatter (None when absent or no frontmatter)."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for ln in lines[1:]:
        if ln.strip() == "---":
            return None
        key, sep, value = ln.partition(":")
        if sep and key.strip() == "model":
            return value.strip().strip("'\"")
    return None


def baseline(run_tree: str, *, model: str) -> dict:
    """{relative path: sha256} of every Claude Code settings file and every agent, skill and command file in the run
    tree; refuses a forbidden one."""
    if not isinstance(model, str) or not model:
        raise SettingsRefused("the take's pinned model is named")
    if not isinstance(run_tree, str) or not os.path.isabs(run_tree) or os.path.islink(run_tree) \
            or not os.path.isdir(run_tree):
        raise SettingsRefused("the run tree is an existing absolute folder, never a link")
    out = {}

    def onerror(e):
        raise SettingsRefused(f"{getattr(e, 'filename', run_tree)}: unreadable ({type(e).__name__})")
    for root, dirs, files in os.walk(run_tree, onerror=onerror, followlinks=False):
        rel_root = os.path.relpath(root, run_tree)
        parts = [] if rel_root == "." else rel_root.split(os.sep)
        in_agents = any(parts[i] == ".claude" and parts[i + 1] in MODEL_DIRS for i in range(len(parts) - 1))
        for d in list(dirs):
            if (d == ".claude" or (d in MODEL_DIRS and os.path.basename(root) == ".claude")) \
                    and os.path.islink(os.path.join(root, d)):
                raise SettingsRefused(f"{os.path.relpath(os.path.join(root, d), run_tree)}: a link")
            if in_agents and os.path.islink(os.path.join(root, d)):
                raise SettingsRefused(f"{os.path.relpath(os.path.join(root, d), run_tree)}: a link under "
                                      f".claude/{{{','.join(MODEL_DIRS)}}}")
        for name in files:
            rel = os.path.relpath(os.path.join(root, name), run_tree)
            if name == ".claude":
                raise SettingsRefused(f"{rel}: .claude is not a folder")
            if in_agents:
                path = os.path.join(root, name)
                if os.path.islink(path) or not os.path.isfile(path) or os.lstat(path).st_size > MAX_BYTES:
                    raise SettingsRefused(f"{rel}: an agent, skill or command file must be a regular file of at "
                                          f"most 2 MiB")
                with open(path, "rb") as fh:
                    data = fh.read()
                got = agent_model(data.decode("utf-8", "replace"))
                if got is not None and got not in AGENT_MODELS_ALLOWED + (model,):
                    raise SettingsRefused(f"{rel}: an agent, skill or command names model {got!r}, not the take's "
                                          f"{model!r}")
                out[rel] = hashlib.sha256(data).hexdigest()
                continue
            if name in MODEL_DIRS and os.path.basename(root) == ".claude":
                raise SettingsRefused(f"{rel}: .claude/{name} is not a folder")
            if os.path.basename(root) != ".claude" or name not in SETTINGS_NAMES:
                continue
            path = os.path.join(root, name)
            st = os.lstat(path)
            if not os.path.isfile(path) or os.path.islink(path) or st.st_size > MAX_BYTES:
                raise SettingsRefused(f"{rel}: a settings file must be a regular file of at most 2 MiB")
            with open(path, "rb") as fh:
                data = fh.read()
            try:
                doc = json.loads(data)
            except ValueError:
                raise SettingsRefused(f"{rel}: not JSON") from None
            if not isinstance(doc, dict):
                raise SettingsRefused(f"{rel}: not a JSON object")
            bad = sorted(k for k in doc if k in FORBIDDEN_KEYS)
            if bad:
                raise SettingsRefused(f"{rel}: carries {bad}, which only the study's --settings may set")
            out[rel] = hashlib.sha256(data).hexdigest()
    problems = workspace_tree_problems(run_tree)   # ruling B10: the vendor CLIs' workspace configuration
    if problems:
        raise SettingsRefused("; ".join(problems))
    return out


def workspace_tree_problems(run_tree: str) -> list:
    """Every WORKSPACE_PATHS entry and every non-folder WORKSPACE_FOLDERS entry at the run tree's root, host-side
    (empty: none). Links are never followed below a guarded folder."""
    out = []
    for name in WORKSPACE_FOLDERS:
        path = os.path.join(run_tree, name)
        if os.path.lexists(path) and (os.path.islink(path) or not os.path.isdir(path)):
            out.append(f"{name}: not a folder")
    for rel, kind in WORKSPACE_PATHS.items():
        path = os.path.join(run_tree, *rel.split("/"))
        if not os.path.lexists(path):
            continue
        if kind == "file":
            out.append(f"{rel}: a vendor CLI's workspace configuration file, which no run tree ships")
            continue
        if os.path.islink(path) or not os.path.isdir(path):
            out.append(f"{rel}: not a folder")
            continue

        def onerror(e, rel=rel):
            out.append(f"{rel}: unreadable ({type(e).__name__})")
        for root, dirs, files in os.walk(path, onerror=onerror, followlinks=False):
            for name in sorted(dirs + files):
                full = os.path.join(root, name)
                if os.path.islink(full) or not os.path.isdir(full):
                    out.append(f"{os.path.relpath(full, run_tree)}: vendor CLI workspace configuration, which no "
                               f"run tree ships")
    return out


def workspace_snapshot_problems(entries: dict) -> list:
    """Every snapshot entry at a WORKSPACE_PATHS path or beneath a guarded folder that is not a folder, and every
    WORKSPACE_FOLDERS or guarded folder entry that is not a folder (empty: none)."""
    out = []
    for path, e in sorted(entries.items()):
        kind = e.get("type") if isinstance(e, dict) else None
        if path in WORKSPACE_FOLDERS and kind != "dir":
            out.append(f"{path}: a {kind}, not a folder")
            continue
        for rel, want in WORKSPACE_PATHS.items():
            if path == rel and (want == "file" or kind != "dir"):
                out.append(f"{path}: a vendor CLI's workspace configuration ({kind}) the run tree did not ship")
            elif want == "folder" and path.startswith(rel + "/") and kind != "dir":
                out.append(f"{path}: a vendor CLI's workspace configuration ({kind}) the run tree did not ship")
    return out


def snapshot_problems(snapshot, base: dict) -> list:
    """Every way a snapshot's settings files and agent, skill and command files differ from the baseline (empty:
    none). Called on every pre-k and every post-k snapshot."""
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("entries"), dict):
        return ["the snapshot holds no entries"]
    entries = snapshot["entries"]
    out = []
    for path, e in sorted(entries.items()):
        kind = e.get("type") if isinstance(e, dict) else None
        if (CLAUDE_DIR.fullmatch(path) or AGENTS_DIR.fullmatch(path)) and kind != "dir":
            out.append(f"{path}: a {kind}, not a folder")
        if AGENTS_PATH.fullmatch(path) and kind == "dir":
            continue
        if SETTINGS_PATH.fullmatch(path) or AGENTS_PATH.fullmatch(path):
            if path not in base:
                out.append(f"{path}: a settings, agent, skill or command file the run tree did not ship")
            elif kind != "file" or e.get("sha256") != base[path]:
                out.append(f"{path}: changed since the run tree was built")
    out += workspace_snapshot_problems(entries)       # ruling B10: on every snapshot, every take
    for path in sorted(base):
        if path not in entries:
            out.append(f"{path}: removed since the run tree was built")
    return out
