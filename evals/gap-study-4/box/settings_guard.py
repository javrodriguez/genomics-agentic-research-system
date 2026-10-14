#!/usr/bin/env python3
"""The run tree's Claude Code settings files, guarded (glitch-06's ruling on review finding 1, 14 Oct 2026).

Every turn loads the project and local scopes (`--setting-sources project,local`), and those files sit in the run
tree, which the agent owns and can write with Bash. The study's own settings ride inline by `--settings` above them
(run_take.claude_study_settings), but a project or local file may still carry keys that change the model or its
fallbacks (an `env` block, `model`, `fallbackModel`, `switchModelsOnFlag`, `availableModels`; non-managed
`availableModels` lists merge). So:

    baseline(run_tree) -> {relative path: sha256}
        Host-side, after the run tree is built and BEFORE grant and launch (no watcher yet, so these reads are never
        logged as the agent's). Every `.claude/settings.json` and `.claude/settings.local.json` anywhere in the tree,
        links never followed; refuses (SettingsRefused) a settings file that is not a regular file, a `.claude` that
        is not a folder, JSON that is not an object, or any FORBIDDEN_KEYS key. GARS's shipped
        gars/.claude/settings.json (keys: hooks, permissions, at the pinned 844a4ce0) passes.

    snapshot_problems(snapshot, baseline) -> [problem]
        Before every turn (turn 1 included, so also at preflight's moment), on the sidecar's own pre-k snapshot read
        from the evidence folder (never by opening the run tree, which the watcher would log): the settings files must
        be exactly the baseline's, each a regular file with the baseline's sha256, and no `.claude` may be anything
        but a folder. The snapshot holds hashes, not contents, so ANY change to a settings file refuses, not only a
        forbidden key (the stricter reading; the sidecar copies contents only for the pre-registered consequential
        paths, and adding these would change the instrument).
        A non-empty list refuses the turn: before turn 1 a rehearsal, after it harness-error (routing's rows), the
        problems recorded.

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
CLAUDE_DIR = re.compile(r"(?:^|.*/)\.claude")
MAX_BYTES = 2 * 1024 * 1024


class SettingsRefused(ValueError):
    """A run tree's settings file the take may not start with. The message names the file and the rule."""


def baseline(run_tree: str) -> dict:
    """{relative path: sha256} of every Claude Code settings file in the run tree; refuses a forbidden one."""
    if not isinstance(run_tree, str) or not os.path.isabs(run_tree) or os.path.islink(run_tree) \
            or not os.path.isdir(run_tree):
        raise SettingsRefused("the run tree is an existing absolute folder, never a link")
    out = {}

    def onerror(e):
        raise SettingsRefused(f"{getattr(e, 'filename', run_tree)}: unreadable ({type(e).__name__})")
    for root, dirs, files in os.walk(run_tree, onerror=onerror, followlinks=False):
        for d in list(dirs):
            if d == ".claude" and os.path.islink(os.path.join(root, d)):
                raise SettingsRefused(f"{os.path.relpath(os.path.join(root, d), run_tree)}: .claude is a link")
        for name in files:
            rel = os.path.relpath(os.path.join(root, name), run_tree)
            if name == ".claude":
                raise SettingsRefused(f"{rel}: .claude is not a folder")
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
    """Every way a pre-turn snapshot's settings files differ from the baseline (empty: the turn may start)."""
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("entries"), dict):
        return ["the snapshot holds no entries"]
    entries = snapshot["entries"]
    out = []
    for path, e in sorted(entries.items()):
        kind = e.get("type") if isinstance(e, dict) else None
        if CLAUDE_DIR.fullmatch(path) and kind != "dir":
            out.append(f"{path}: .claude is a {kind}, not a folder")
        if SETTINGS_PATH.fullmatch(path):
            if path not in base:
                out.append(f"{path}: a settings file the run tree did not ship")
            elif kind != "file" or e.get("sha256") != base[path]:
                out.append(f"{path}: changed since the run tree was built")
    for path in sorted(base):
        if path not in entries:
            out.append(f"{path}: removed since the run tree was built")
    return out
