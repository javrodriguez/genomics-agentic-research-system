#!/usr/bin/env python3
"""Facts about the workspace itself, shared by every stage helper.

One home for `which template version is this?`, because more than one stage needs to answer it and
the "or unknown" rule is a documented behaviour rather than a bare file read.
"""

import json
from pathlib import Path

VERSION_FILE = "_references/VERSION"

# Where a workspace records which checkout it came from.
#
# It lives at the workspace ROOT, deliberately -- NOT in _references/ or _system/, which
# `upgrade.py` replaces wholesale. A marker inside the replaced layer would be destroyed by the
# very command that needs to write it.
MARKER_FILE = ".gars-workspace"


def workspace_root(script_file):
    """The workspace a `_system/` script belongs to."""
    return Path(script_file).resolve().parent.parent


def template_version(workspace):
    """The GARS revision this workspace is a copy of, or 'unknown'.

    `unknown` is an honest value; a fabricated version is not. A project that cannot name the
    contract version that produced it is not reproducible, so every stage records this in
    HISTORY.md -- not only stage 00. A workspace can be upgraded between stages (see
    `_system/upgrade.py`), and when that happens the per-stage stamps are the only record that
    stage 01 ran under a different contract than stage 00.
    """
    p = Path(workspace) / VERSION_FILE
    if p.is_file():
        text = p.read_text(encoding="utf-8").strip()
        if text:
            return text
    return "unknown"


def read_marker(workspace):
    """What this workspace records about its own origin. Missing is normal, not an error.

    A workspace is made with `cp -r`, which writes no metadata, so a workspace only knows its
    source once something records one -- `upgrade.py --set-source` or `--apply`.
    """
    p = Path(workspace) / MARKER_FILE
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}


def write_marker(workspace, **fields):
    """Merge fields into the marker, preserving anything already recorded."""
    data = read_marker(workspace)
    data.update({k: v for k, v in fields.items() if v is not None})
    p = Path(workspace) / MARKER_FILE
    p.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return data


def parse_version(text):
    """`v1.2.3` -> (1, 2, 3). Returns None when it is not that shape."""
    if not text:
        return None
    core = text.strip().lstrip("vV").split("-")[0].split("+")[0]
    parts = core.split(".")
    if not (1 <= len(parts) <= 4):
        return None
    try:
        return tuple(int(p) for p in parts)
    except ValueError:
        return None


def compare_versions(here, there):
    """'behind' | 'ahead' | 'same' | 'differs'.

    `differs` is the honest answer when either side is unparseable -- `unknown` is a legitimate
    version, and claiming an ordering over it would be a guess.
    """
    if here == there:
        return "same"
    a, b = parse_version(here), parse_version(there)
    if a is None or b is None:
        return "differs"
    if a < b:
        return "behind"
    if a > b:
        return "ahead"
    return "same"
