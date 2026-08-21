#!/usr/bin/env python3
"""Facts about the workspace itself, shared by the stage helpers.

One home for "which template version is this?", because more than one stage needs to answer it
and the "or unknown" rule is a documented behaviour rather than a bare file read.
"""

import contextlib
import os
from pathlib import Path

VERSION_FILE = "_references/VERSION"


def workspace_root(script_file):
    """The workspace a `_system/` script belongs to."""
    return Path(script_file).resolve().parent.parent


def template_version(workspace):
    """The GARS revision this workspace is at, or 'unknown'.

    `unknown` is an honest value; a fabricated version is not. A project that cannot name the
    contract version that produced it is not reproducible, so every stage records this in
    HISTORY.md -- not only stage 00. A workspace is a git checkout, so `git pull` can move the
    contracts between stages; the per-stage stamps are the record of which version produced which
    result. `git log`, `git diff` and `git checkout <tag>` answer everything else.
    """
    p = Path(workspace) / VERSION_FILE
    if p.is_file():
        text = p.read_text(encoding="utf-8").strip()
        if text:
            return text
    return "unknown"


@contextlib.contextmanager
def atomic_open(path, newline=""):
    """Open a file for writing such that a killed process cannot leave it half-written.

    Writes to a sibling temp file, fsyncs, then renames into place. `os.replace` is atomic on
    POSIX, so a reader sees either the previous complete file or the new complete file -- never a
    prefix of one.

    This is not hypothetical. A `leukemia-test` project was found with `files.csv` accounting for
    40 of 152 linked FASTQs and `samples.csv` holding 9 of 38 samples: both machine-owned files
    ended mid-record with no trailing newline. A truncated CSV is still a *valid* CSV, so stage 01
    read it, found it internally consistent, and reported 10 samples as the truth. Nothing failed.
    """
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    fh = open(str(tmp), "w", newline=newline, encoding="utf-8")
    try:
        yield fh
        fh.flush()
        os.fsync(fh.fileno())
        fh.close()
        os.replace(str(tmp), str(path))
    except BaseException:
        try:
            fh.close()
        except OSError:
            pass
        try:
            tmp.unlink()
        except OSError:
            pass
        raise
