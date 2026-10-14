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
        A non-empty list refuses the turn: before turn 1 a rehearsal, after it harness-error (routing's rows), the
        problems recorded. NAMED RESIDUAL (hot reload): Claude Code reloads a settings file when it changes, so a
        write takes effect inside the turn that makes it; the guard detects it at the next snapshot (that turn's
        post-k), never prevents it within the turn.

Standard library only.
"""

from __future__ import annotations

import hashlib
import json
import os
import re

FORBIDDEN_KEYS = ("env", "model", "fallbackModel", "switchModelsOnFlag", "availableModels")
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
    for path in sorted(base):
        if path not in entries:
            out.append(f"{path}: removed since the run tree was built")
    return out
