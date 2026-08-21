#!/usr/bin/env python3
"""Facts about the workspace itself, shared by every stage helper.

One home for `which template version is this?`, because more than one stage needs to answer it and
the "or unknown" rule is a documented behaviour rather than a bare file read.
"""

from pathlib import Path

VERSION_FILE = "_references/VERSION"


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
