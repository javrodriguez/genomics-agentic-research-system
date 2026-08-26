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


# One pinned upstream pipeline per assay. Single source of truth: configure.py keys the
# derived-reference cache with these, and each wrapper asserts its checkout matches. An index
# cache is version-keyed because an aligner refuses an index built by an incompatible version
# (decision 0009); the checkout lives at $GARS_PIPELINES/<value without the nf-core- prefix>.
PIPELINES = {
    "rnaseq_bulk": "nf-core-rnaseq-3.26.0",
    "atacseq_bulk": "nf-core-atacseq-2.1.2",
}

# The design table's columns, per assay (decision 0030). Every assay carries the base four;
# ChIP-family assays add columns their pipelines require: `control` points at the sample_id of
# the input-chromatin (chipseq) or IgG (cutandrun) sample -- same column shape, different
# biological referent, which is why VALIDATION stays per-assay while the shape is shared.
# Stage 00 writes the header, stage 01 validates and consumes it; both read it from here so
# the two can never disagree.
BASE_DESIGN_COLUMNS = ["sample_id", "condition", "group", "replicate"]
EXTRA_DESIGN_COLUMNS = {
    "chipseq_bulk": ["antibody", "control"],
    "cutandrun": ["control"],
}


def design_columns(assay):
    return BASE_DESIGN_COLUMNS + EXTRA_DESIGN_COLUMNS.get(assay, [])


MACHINE_OWNED_MODE = 0o444


@contextlib.contextmanager
def atomic_open(path, newline="", mode=None):
    """Open a file for writing such that a killed process cannot leave it half-written.

    Writes to a sibling temp file, fsyncs, then renames into place. `os.replace` is atomic on
    POSIX, so a reader sees either the previous complete file or the new complete file -- never a
    prefix of one.

    `mode` is applied after the rename. Pass `MACHINE_OWNED_MODE` for a file a stage owns and a
    user must not edit: a comment line saying "do not edit" is advisory and editors ignore it,
    whereas 0444 makes the mistake fail at the moment it is made rather than two stages later.
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
        if mode is not None:
            # `rename` needs write permission on the DIRECTORY, not on the target, so a
            # machine-owned file can still be replaced by the stage that owns it.
            os.chmod(str(path), mode)
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
