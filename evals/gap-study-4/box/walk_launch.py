#!/usr/bin/env python3
"""The CP6 walk's launch road, Mac to athena and back (box lane; glitch-6b's ruling of 15 Oct 2026, item 3: a git
bundle out and back). Run on the Mac. It pushes nothing, places no login and reads no secret: the walk's login file is
the Claude1 file already on athena (run_take.WALK_LOGIN_FILES), read there by the walk itself.

    python3 evals/gap-study-4/box/walk_launch.py ship  --repo <Mac clone> --ref <branch> --suite <athena_suite.py>
                                                       --reserve <athena-reserve> --gitleaks <binary> --work <Mac folder>
        1. the Mac pre-check (machine_gate.mac_precheck): no athena suite in progress, busy runs never ran;
        2. the ref's head carries the pinned tree's history (variants.PINNED_TREE is an ancestor);
        3. `git bundle create` of the ref (the whole history), `git bundle verify`;
        4. athena_suite's own outward rule over a scratch clone of the bundle (outward_scan): no secret-shaped file,
           and gitleaks over every carried commit the public GARS remote does not serve, else refuse;
        5. a new mode-700 neutral child on athena (`mktemp -d /home/javier/w-XXXXXXXX`), the bundle and athena-reserve
           copied there, each sha256 read back on athena; athena clones the bundle and its HEAD must be the head.
        Prints one JSON line: the child, the head, the bundle's sha256.

    python3 .../walk_launch.py run --child <athena child> --head <sha> --walk <id> --task <t> --half <h>
                                   --wording <w> --arm <a> --model <m> --reason <why>
        On athena, under umask 0022 (the box lane's run 7 finding: the evidence folder must stay host-readable):
        the reservation CLAIMED with O_EXCL under this walk's hold id (one already there refuses), the athena gate
        (machine_gate athena-check; a closed gate removes the claim), then
        `nohup python3 <child>/athena-reserve hold --by <hold id> -- env GAP4_SUITE_ACCOUNT=athena-suite
        GAP4_RESERVATION=<reserved.json> GAP4_OWN_HOLD=<hold id> python3 -B <repo>/evals/gap-study-4/walk_runner.py
        ...`, so every athena suite launched during the walk is refused `reserved` and the walk's own gate admits its
        own hold only. Prints the pid.
        THE HOLD'S LIMITS (named, the review's NIT 7):
          - race: the O_EXCL claim refuses a reservation that is already there, but `athena-reserve set` and
            `hold` write unconditionally, so a second writer arriving after the claim overwrites it unseen; the
            athena gate's suite checks still read the machine at each take launch;
          - SIGHUP: the walk runs under `nohup sh -c`, so a dropped ssh session reaches neither the hold nor the walk;
          - lease lapse: `hold` writes a 29-minute lease and rewrites it every 10 minutes; if the hold process is
            killed outright (SIGKILL, an OOM), the lease is not renewed, the reservation reads free once its `until`
            passes, and the walk keeps running unreserved. athena_suite would then admit a suite beside it. The walk
            itself is stopped by hold only on a normal exit or SIGTERM/SIGHUP. No guard closes this; it is a residual.
          - a failed start: the start checks athena-reserve is in the child before the claim, and 3 s after the
            nohup that the hold still runs and the reservation is still this walk's; otherwise it removes the claim
            and exits non-zero. Recovery after any start that crashed between the claim and that check:
            `athena-reserve clear` (as javier on athena).

    python3 .../walk_launch.py status --child <athena child>
        `running` while the recorded pid lives, else the walk's exit code from its exit file.

    python3 .../walk_launch.py fetch --child <athena child> --head <sha> --ref <branch> --records <Mac clone>
                                     --gitleaks <binary> --work <Mac folder> --suite <athena_suite.py>
        On athena, a bundle of the new commits only (`<head>..<ref>`); copied to the Mac, its sha256 read back;
        fetched into a scratch shared clone of the records clone, athena_suite's scan_unpublished at the tip with
        public_shas=[head] and no allowance at all (allow comments ignored, messages and binary blobs refused); then
        fetched into the records clone as refs/heads/walk/<child name>. A walk that made no
        commit has nothing to fetch and says so.

    python3 .../walk_launch.py probe --child <athena child> --probe <id> --scenarios <A1,...|all>
                                     --image sha256:<64> --reason <why>
        Lane vendor-b27 (glitch-f1's ruling 1, 21 Oct 2026): the stub-model probe (box/stub_model_probe.py, a
        measurement, never a walk) started exactly as `run` starts a walk: the O_EXCL claim under the hold id
        gap4-probe-<id>, the athena gate, then the probe under `athena-reserve hold` with nohup, the pid and the exit
        file (the same walk.pid, walk.log and walk.exit, so `status` reads it). Its output is <child>/stub-probe-<id>.

    python3 .../walk_launch.py fetch-probe --child <athena child> --probe <id> --out <Mac folder>/stub-probe-<id>
                                           --gitleaks <binary> --work <Mac folder>
        Once the probe is not running: <child>/stub-probe-<id> tarred on athena, copied, its sha256 read on both sides,
        unpacked by this code (regular files and folders only, under that one folder), checked against the probe's
        manifest, every file scanned with no allowance (canary_scan), then moved to --out. Nothing reaches a clone.

    python3 .../walk_launch.py probe-hooks --child <athena child> --probe <id> --scenarios <HG,HO-C0,HO-C1>
                                           [--gemini-image sha256:<64>] [--codex-image sha256:<64>] --reason <why>
        Lane hook-control (glitch-f1's rulings on the D8 hook control, 21 Oct 2026): box/hook_control_probe.py, a
        measurement on the stub-model probe's road, started the same way under the same hold id gap4-probe-<id> (the
        same claim, gate, hold, nohup, pid and exit file); its output is <child>/stub-probe-<id>, fetched by
        `fetch-probe` unchanged.

Every remote and local command goes through one Runner, so tests drive the whole road on fakes.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import threading
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import machine_gate  # noqa: E402
from box import scan_record as _scan_record  # noqa: E402  (OD57's reviewed line rulings)

PINNED_TREE = "844a4ce0d89437ca043363981a86096f6383a141"      # variants.PINNED_TREE; a test binds the two
HOST = "athena"
SSH = ("ssh", "-a", "-x", "-o", "BatchMode=yes")
SCP = ("scp", "-q", "-o", "BatchMode=yes", "-o", "ForwardAgent=no", "-o", "ForwardX11=no")
CHILD_PARENT = "/home/javier"
CHILD = re.compile(r"/home/javier/w-[A-Za-z0-9]{8}")
UMASK = "0022"
SUITE_ACCOUNT = machine_gate.SUITE_ACCOUNT
RESERVATION = machine_gate.RESERVATION
# athena-reserve as the runbook pins it (FOREMAN-RUNBOOK section 13, `efeecb3a…`; aegis ops/node1/athena-reserve).
RESERVE_SHA256 = "efeecb3a606d6bb9a23c77b850b8ef1f61cb9aed0f4bcdb53c3ff3b9b039062e"
# THE WALK'S ENVIRONMENT (glitch-6b, 15 Oct 2026, after the box lane found GAP4_CONFIG_PARENT missing at 26dd61be):
# every name a study module reads at walk time is passed here or deliberately absent below, and test_walk_launch's
# L7-env binds that against every "GAP4_*" literal in the study's own modules.
#   GAP4_CONFIG_PARENT  walk_builders.config_parent_from_env: per-walk config folders and the walk's proxy
#                       configuration are made in it; an owned folder outside every repository, mode 0700 (created on
#                       athena by the box lane 15 Oct 2026, 05:23 EDT).
#   GAP4_SUITE_ACCOUNT, GAP4_RESERVATION, GAP4_OWN_HOLD, GAP4_SUITE_SLOTS  machine_gate.gate_from_env (both the
#                       pre-hold gate and the drive's own check before each take launch).
#   GIT_{AUTHOR,COMMITTER}_{NAME,EMAIL}  takes.require_commit_identity, called by WalkRepo.commit_walk: javier on athena
#                       has no global git identity and the walk's clone has no local one (read 05:23 EDT, 15 Oct 2026);
#                       the identity the box lane's commits carry (GitHub's noreply address, never the gmail one).
CONFIG_PARENT_ENV = "GAP4_CONFIG_PARENT"
CONFIG_PARENT = "/home/javier/gap4-walk-config"
COMMIT_IDENTITY = ("GIT_AUTHOR_NAME=javrodriguez GIT_AUTHOR_EMAIL=28984720+javrodriguez@users.noreply.github.com "
                   "GIT_COMMITTER_NAME=javrodriguez GIT_COMMITTER_EMAIL=28984720+javrodriguez@users.noreply.github.com")
RUN_ENV_ABSENT = {
    "DOCKER_HOST": "preflight records whether it is set and the box's runs (stub takes 1-8) ran with it unset: the "
                   "Docker client reaches javier's rootless daemon through its own context and XDG_RUNTIME_DIR",
    "CLAUDE_CONFIG_DIR": "drive.session_file (round 3's host road) reads it; a box walk reads the take's own config "
                         "folder (drive.take_session_file), so nothing on the walk path does",
    "GAP4_ATHENA_SUITE": "the first machine gate's (harness 9425bf62); no module reads it since the box lane's fa0838ec",
    "GAP4_MACHINE_BOOKING": "the first machine gate's; no module reads it since fa0838ec",
    "GAP4_ATHENA_SUITE_PY": "read only by test_walk_launch's real-scanner proof on the Mac, never at walk time",
    "GAP4_COVERAGE_STORE": "walk_counts.store_dir reads it to place the covered-set store that draft builds and "
                           "their tests read (lane gap-prebeacon-fix); nothing on the walk path reads it, and the store "
                           "keeps the walk's checkout out of it, so a walk passed it would only point at a cache",
}
HEX40 = re.compile(r"[0-9a-f]{40}")
# machine_gate's own refusal phrases, the only words of a pre-check refusal ship passes on (r7 MINOR)
PRECHECK_KINDS = {"a run in progress or unknown": "is in progress or unknown", "a list line off its form":
                  "is not that command's form", "a status that cannot be read": "its status cannot be read",
                  "a list that cannot be read": "athena_suite list", "no athena_suite.py": "athena_suite.py path"}
WALK_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
CELL = ("task", "half", "wording", "arm", "model")
# The outward bundle's scan is athena_suite's own rule (glitch-6b, 15 Oct 2026), its code reused: every carried commit the
# PUBLIC GARS remote does not already serve is scanned (scan_unpublished, after fetch_public_refs of
# PUBLIC_REFERENCE["gars"] into a plain scratch clone of the bundle, with the push door's committed rulings and the
# committed allowlist exactly as cmd_run passes them), and nothing it does serve. Shipping an already-public commit to
# athena discloses nothing new; this is not a ruling on any finding. The new-commits bundle coming back gets no
# allowance at all.
SUITE_KIND = "gars"


# The watcher's evidence blobs (glitch-6b's ruling (b), 15 Oct 2026, after w001's fetch refused on 12 of them): a binary
# blob in the walk's new commits ships only as a gzip stream under rehearsals/<walk>/evidence/blobs/<sha256>, decoded
# within these bounds and scanned decompressed with no allowance; anything else refuses.
# Lane run-launcher, decision 3 (glitch-f1, 22 Oct 2026): a counted take's watcher blobs sit at
# takes/<slot>/<attempt>/evidence/blobs/<sha256>, the slot a frozen row's s-<64 hex>, the attempt a positive whole number.
EVIDENCE_BLOB = re.compile(r"evals/gap-study-4/(?:rehearsals/[A-Za-z0-9][A-Za-z0-9._-]*|takes/s-[0-9a-f]{64}/[1-9][0-9]*)"
                           r"/evidence/blobs/[0-9a-f]{64}")
BLOB_MAX_BYTES = 16 * 1024 * 1024        # decompressed, per blob (and the stored size of one blob)
BLOB_MAX_RATIO = 256                      # decompressed : compressed, against bombs (text compresses far less)
BLOB_TOTAL_MAX = 64 * 1024 * 1024        # decompressed, all of a walk's evidence blobs together (review MAJOR 2)
BLOB_MAX_COUNT = 256                      # evidence blobs one walk may bring (review MAJOR 2)
GZ_FHCRC, GZ_FEXTRA, GZ_FNAME, GZ_FCOMMENT, GZ_RESERVED = 0x02, 0x04, 0x08, 0x10, 0xE0
CHUNK = 1 << 20
GZ_FIELD_MAX = 4096                       # each of FEXTRA, FNAME, FCOMMENT (closure review MINOR C)
# The canary proof (closure review MAJOR A and B): gitleaks `dir` silently skips a file that looks like an archive (a
# gzip, bzip2, zstd, 7z or zip signature at its start, tar's ustar at offset 257), so a clean scan proves nothing by
# itself. Every scanned file ends with its own synthetic GitHub-token-shaped canary (made at run time, never a key),
# and the scan must report exactly that one canary per file, on its own line, and nothing else.
CANARY_RULE = "github-pat"


class LaunchRefused(RuntimeError):
    """A step of the road refused; the message names the rule, never a secret."""


def clean_git_env(extra=None) -> dict:
    """git (and gitleaks) with no global or system config and no prompt: athena_suite.clean_git_env's rule, mirrored
    (closure review of a3b09f02, MINOR; test_walk_launch pins the rule): every GIT_* and GITLEAKS_* variable of the
    operator's environment is dropped, so a GIT_CONFIG_COUNT setting (fsck.zeroPaddedFilemode=ignore, say) or a
    GITLEAKS_CONFIG cannot change what a check reads."""
    env = {k: v for k, v in os.environ.items() if not k.startswith(("GIT_", "GITLEAKS_"))}
    env.update({"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0"})
    env.update(extra or {})
    return env


# The remote git calls run in javier's ssh environment on athena; they carry the same isolation as a prefix.
REMOTE_GIT = "GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 GIT_TERMINAL_PROMPT=0 git"


class Runner:
    """The one place a process starts. local(argv) and remote(cmd) return (code, stdout, stderr). A local git or
    gitleaks call runs under clean_git_env."""

    def local(self, argv, *, timeout=3600):
        argv = list(argv)
        env = clean_git_env() if argv and os.path.basename(str(argv[0])) in ("git", "gitleaks") else None
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, env=env)
        return p.returncode, p.stdout, p.stderr

    def remote(self, cmd: str, *, timeout=3600):
        return self.local(list(SSH) + [HOST, "--", cmd], timeout=timeout)

    def copy_to(self, src: str, dst: str):
        return self.local(list(SCP) + [src, f"{HOST}:{dst}"])

    def copy_from(self, src: str, dst: str):
        return self.local(list(SCP) + [f"{HOST}:{src}", dst])


def _ok(res, what):
    """The step's stdout, or a refusal naming the step and its exit code ONLY (closure review of a3b09f02, MAJOR):
    stderr and stdout are never echoed, at any site, so no athena-made byte (a bundle header, a log tail, a path) reaches
    the terminal, a transcript or a lane report unscanned."""
    code, out, err = res
    if code != 0:
        raise LaunchRefused(f"{what} failed (exit {code})")
    return out


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _child(child: str) -> str:
    if not isinstance(child, str) or not CHILD.fullmatch(child):
        # the value is never echoed: on ship it is athena's mktemp output (closure review of a3b09f02)
        raise LaunchRefused("the athena child must be a new /home/javier/w-XXXXXXXX folder")
    return child


def hold_id(walk: str) -> str:
    if not isinstance(walk, str) or not WALK_ID.fullmatch(walk):
        raise LaunchRefused(f"the walk id {walk!r} is not one path segment")
    hid = f"gap4-walk-{walk}"
    if not machine_gate.HOLD_ID.match(hid):
        raise LaunchRefused(f"the hold id {hid!r} is not one athena-reserve accepts (BY_RE, 64 characters)")
    return hid


# ------------------------------------------------------------------------------------------------ ship
def gzip_header(data: bytes) -> tuple:
    """(payload offset, [(field, bytes)]) of one RFC 1952 member header, parsed here because zlib discards FEXTRA,
    FNAME and FCOMMENT (the review of b1f5c952, MAJOR 1: a token there was fetched). Refuses: no 1f 8b magic, a method
    other than deflate, any reserved FLG bit, a header cut short, an FHCRC that does not validate."""
    import zlib
    if not isinstance(data, bytes) or len(data) < 10 or data[:2] != b"\x1f\x8b":
        raise LaunchRefused("not a gzip stream (no 1f 8b magic)")
    if data[2] != 8:
        raise LaunchRefused("the gzip method is not deflate")
    flg = data[3]
    if flg & GZ_RESERVED:
        raise LaunchRefused("the gzip header sets a reserved flag bit")
    i, fields = 10, []
    if flg & GZ_FEXTRA:
        if len(data) < i + 2:
            raise LaunchRefused("the gzip header is cut short (FEXTRA)")
        xlen = int.from_bytes(data[i:i + 2], "little")
        if len(data) < i + 2 + xlen:
            raise LaunchRefused("the gzip header is cut short (FEXTRA)")
        if xlen > GZ_FIELD_MAX:
            raise LaunchRefused(f"the gzip header's FEXTRA is longer than {GZ_FIELD_MAX} bytes")
        fields.append(("FEXTRA", data[i + 2:i + 2 + xlen]))
        i += 2 + xlen
    for bit, name in ((GZ_FNAME, "FNAME"), (GZ_FCOMMENT, "FCOMMENT")):
        if flg & bit:
            j = data.find(b"\0", i)
            if j < 0:
                raise LaunchRefused(f"the gzip header is cut short ({name})")
            if j - i > GZ_FIELD_MAX:
                raise LaunchRefused(f"the gzip header's {name} is longer than {GZ_FIELD_MAX} bytes")
            fields.append((name, data[i:j]))
            i = j + 1
    if flg & GZ_FHCRC:
        if len(data) < i + 2 or int.from_bytes(data[i:i + 2], "little") != zlib.crc32(data[:i]) & 0xFFFF:
            raise LaunchRefused("the gzip header's FHCRC does not validate")
        i += 2
    return i, fields


def gunzip_to(data: bytes, out, limit: int) -> tuple:
    """Decode one gzip member into the binary file object `out`, streamed in CHUNK pieces: (bytes written, header
    fields). Refuses past `limit` bytes, a decode error, truncation, trailing bytes, a CRC32 or ISIZE that does not
    match, and a payload that is itself binary (a NUL in its first 8000 bytes: the text scan could not read it)."""
    import zlib
    off, fields = gzip_header(data)
    d = zlib.decompressobj(-zlib.MAX_WBITS)
    buf, n, crc, first = data[off:], 0, 0, b""
    try:
        while not d.eof:
            piece = d.decompress(buf, CHUNK)
            buf = d.unconsumed_tail
            if not piece and not buf:
                break
            n += len(piece)
            if n > limit:
                raise LaunchRefused(f"the gzip stream decompresses past its bound ({limit} bytes)")
            crc = zlib.crc32(piece, crc)
            if len(first) < 8000:
                first += piece[:8000 - len(first)]
            out.write(piece)
    except zlib.error:
        raise LaunchRefused("the gzip stream does not decode") from None
    if not d.eof:
        raise LaunchRefused("the gzip stream is truncated")
    trailer = d.unused_data
    if len(trailer) != 8:
        raise LaunchRefused("the gzip stream carries trailing bytes or a cut trailer")
    if int.from_bytes(trailer[:4], "little") != crc or int.from_bytes(trailer[4:], "little") != n & 0xFFFFFFFF:
        raise LaunchRefused("the gzip trailer's CRC32 or ISIZE does not match")
    if b"\0" in first:
        raise LaunchRefused("the decompressed blob is itself binary, which the scan cannot read")
    return n, fields


def _git_out(repo: str, *args: str, binary: bool = False):
    p = subprocess.run(["git", "-C", repo, *args], capture_output=True, timeout=600, env=clean_git_env())
    if p.returncode != 0:
        raise LaunchRefused(f"git {args[0]} failed (exit {p.returncode})")
    return p.stdout if binary else p.stdout.decode("utf-8", "replace")


def evidence_candidates(repo: str, head: str, tip: str) -> dict:
    """{blob id: set of paths} for every blob in the walk's new commits (head..tip) that git would read as binary (a
    NUL in its first 8000 bytes) OR that starts with 1f 8b, text to git or not (the review's MINOR 5)."""
    paths = {}
    for commit in _git_out(repo, "rev-list", f"{head}..{tip}").split():
        for line in _git_out(repo, "ls-tree", "-r", commit).splitlines():
            meta, _, path = line.partition("\t")
            parts = meta.split()
            if len(parts) == 3 and parts[1] == "blob":
                paths.setdefault(parts[2], set()).add(path)
    new = set(_git_out(repo, "rev-list", "--objects", tip, "--not", head).split())
    out = {}
    for oid, where in paths.items():
        if oid not in new:
            continue
        if is_evidence_candidate(_git_out(repo, "cat-file", "blob", oid, binary=True)[:8000]):
            out[oid] = where
    return out


def is_evidence_candidate(head_bytes: bytes) -> bool:
    """A blob both roads decode-and-scan or refuse, by its first 8000 bytes: binary to git (a NUL there) OR gzip magic
    1f 8b, text to git or not (the fetch's MINOR 5; the outward road's since the review of 2ced80f2, MAJOR 1)."""
    if head_bytes[:2] == b"\x1f\x8b" or b"\0" in head_bytes[:8000]:
        return True
    return False


# One decode-and-stage step shared by the fetch (admitted_evidence_blobs) and the outward ship scan
# (outward_evidence_blobs), so the two roads cannot drift (the review of 2ced80f2, NIT 4, folded with its MAJOR 1):
# the stored-size cap, the sha256 of the STORED bytes as the name at every path, the per-blob bound (the absolute cap,
# the ratio and the room the caller's total leaves), gunzip_to, the binary-header check and the .header file. Each road
# keeps its own words (FETCH_SAYS is the fetch's, byte for byte as before).
FETCH_SAYS = {"stored": "blob {oid} is stored larger than {cap} bytes",
              "path": "blob {oid} sits outside rehearsals/<walk>/evidence/blobs/<sha256 of its bytes>",
              "decode": "evidence blob {oid}: {why}",
              "header": "evidence blob {oid}: a gzip header field is binary"}
OUTWARD_SAYS = {"stored": "evidence blob {oid} is stored larger than {cap} bytes; nothing ships",
                "path": "evidence blob {oid} sits off <walk or take>/evidence/blobs/<sha256 of its stored bytes>; "
                        "nothing ships",
                "decode": "evidence blob {oid}: {why}; nothing ships",
                "header": "evidence blob {oid}: a gzip header field is binary; nothing ships"}


def stage_evidence_blob(repo: str, oid: str, where, src: str, room: int, says: dict) -> int:
    """Decode blob `oid` (its paths `where`) into src/<oid> and its header into src/<oid>.header, each 0600, for the
    caller's canary scan; returns the decompressed size. `room` is what the caller's total cap leaves. Refuses in the
    words of `says` (FETCH_SAYS or OUTWARD_SAYS), naming the id and the rule, never content."""
    if int(_git_out(repo, "cat-file", "-s", oid).strip() or 0) > BLOB_MAX_BYTES:
        raise LaunchRefused(says["stored"].format(oid=oid, cap=BLOB_MAX_BYTES))
    data = _git_out(repo, "cat-file", "blob", oid, binary=True)
    name = hashlib.sha256(data).hexdigest()
    if not all(EVIDENCE_BLOB.fullmatch(p) and p.rsplit("/", 1)[1] == name for p in where):
        raise LaunchRefused(says["path"].format(oid=oid))
    limit = min(BLOB_MAX_BYTES, len(data) * BLOB_MAX_RATIO, room)
    fd = os.open(os.path.join(src, oid), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as fh:
            n, fields = gunzip_to(data, fh, limit)
    except LaunchRefused as e:
        raise LaunchRefused(says["decode"].format(oid=oid, why=e)) from None
    if any(b"\0" in v for _k, v in fields):
        raise LaunchRefused(says["header"].format(oid=oid))
    meta = (b"MTIME: " + str(int.from_bytes(data[4:8], "little")).encode() + b"\nXFL: "
            + str(data[8]).encode() + b"\nOS: " + str(data[9]).encode() + b"\n")
    _write_private(os.path.join(src, oid + ".header"),
                   meta + b"".join(k.encode() + b": " + v + b"\n" for k, v in fields))
    return n


def _tree_entries(repo: str, commit: str) -> list:
    """Every entry of the commit's whole tree, subtrees included: `<mode> <type> <id>\\t<path>` bytes, from
    `git ls-tree -r -t -z --full-tree` (NUL-framed)."""
    raw = _git_out(repo, "ls-tree", "-r", "-t", "-z", "--full-tree", commit, binary=True)
    entries = [e for e in raw.split(b"\0") if e]
    # The sibling review of athena_suite (15 Oct 2026): ls-tree prints an entry's type from its MODE, so a blob-mode
    # entry pointing at a TREE object (written with hash-object --literally) is printed as a blob and never opened.
    # Every blob or tree record's real type is read back (cat-file --batch-check); a mismatch refuses.
    declared = {}
    for e in entries:
        meta = e.split(b"\t", 1)[0].split()
        if len(meta) == 3 and meta[1] in (b"blob", b"tree"):
            declared.setdefault(meta[2].decode(), set()).add(meta[1].decode())
    if declared:
        p = subprocess.run(["git", "-C", repo, "cat-file", "--batch-check=%(objectname) %(objecttype)"],
                           input=("\n".join(declared) + "\n").encode(), capture_output=True, timeout=600,
                           env=clean_git_env())
        if p.returncode != 0:
            raise LaunchRefused(f"git cat-file --batch-check failed (exit {p.returncode})")
        real = dict(line.split()[:2] for line in p.stdout.decode().splitlines() if len(line.split()) >= 2)
        for oid, kinds in declared.items():
            if kinds != {real.get(oid)}:
                raise LaunchRefused(f"tree entry {oid} is recorded as {sorted(kinds)} but the object is "
                                    f"{real.get(oid)!r}")
    return entries


def _fsck_problems(repo: str) -> list:
    """`git fsck --strict --no-dangling` over the scratch (the sibling review's first layer, as athena_suite): every
    output line when it fails or prints anything at all (a warning too); [] when the repository is clean."""
    p = subprocess.run(["git", "-C", repo, "fsck", "--strict", "--no-dangling", "--no-progress"],
                       capture_output=True, timeout=1800, env=clean_git_env())
    lines = [x for x in (p.stdout + p.stderr).decode("utf-8", "replace").splitlines() if x.strip()]
    if p.returncode != 0 or lines:                 # a clean repository prints nothing: any line refuses
        return lines or [f"git fsck exited {p.returncode}"]
    return []


def _all_objects(repo: str) -> set:
    """Every object id the repository can read, its alternates included."""
    return set(_git_out(repo, "cat-file", "--batch-all-objects", "--batch-check=%(objectname)").split())


SCRATCH_CORE_KEYS = ("core.repositoryformatversion", "core.filemode", "core.bare", "core.logallrefupdates",
                     "core.ignorecase", "core.precomposeunicode", "core.symlinks")


def scratch_problems(repo: str) -> list:
    """athena_suite.assert_plain_scratch's rule: the clone's own config holds only what `git clone` writes (core keys,
    remote.origin.*, branch.*) and its hooks folder is empty or absent."""
    keys = [k for k in _git_out(repo, "config", "--local", "--name-only", "--null", "--list").split("\0") if k]
    odd = [k for k in keys if k.lower() not in SCRATCH_CORE_KEYS and not k.lower().startswith(("remote.origin.",
                                                                                               "branch."))]
    hooks = os.path.join(_git_out(repo, "rev-parse", "--absolute-git-dir").strip(), "hooks")
    return odd + (sorted(os.listdir(hooks)) if os.path.isdir(hooks) else [])


def _canary() -> bytes:
    import secrets
    import string
    return ("ghp_" + "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(36))).encode()


def _append_canary(path: str) -> int:
    """Append a fresh canary on its own last line; return that line's number (1-based), the line gitleaks must name."""
    lines, last = 0, b"\n"
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(CHUNK), b""):
            lines += block.count(b"\n")
            last = block[-1:]
    with open(path, "ab") as fh:
        if last != b"\n":
            fh.write(b"\n")
            lines += 1
        fh.write(_canary() + b"\n")
    return lines + 1


def _write_private(path: str, data: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as fh:
        fh.write(data)


def canary_scan(gitleaks: str, src: str, work: str) -> list:
    """gitleaks dir over src (no allowance: --ignore-gitleaks-allow, an empty ignore file, redacted), every file
    carrying its canary; returns [(file name, why)] for every file whose canary is missing or that has any other
    finding. Never content: names, rules and line numbers only."""
    expected = {name: _append_canary(os.path.join(src, name)) for name in sorted(os.listdir(src))}
    ignore = os.path.join(work, "empty.gitleaksignore")
    open(ignore, "w").close()
    report = os.path.join(work, "report.json")
    p = subprocess.run([gitleaks, "dir", "--no-banner", "--redact", "--exit-code", "0", "--ignore-gitleaks-allow",
                        "--gitleaks-ignore-path", ignore, "--report-format", "json", "--report-path", report, src],
                       capture_output=True, timeout=900, env=clean_git_env())
    try:
        with open(report, encoding="utf-8") as fh:
            found = json.load(fh)
        if not isinstance(found, list):
            raise ValueError
    except (OSError, ValueError):
        raise LaunchRefused(f"the private scan wrote no readable report (exit {p.returncode})") from None
    if p.returncode != 0:
        raise LaunchRefused(f"the private scan failed (exit {p.returncode})")
    canaries, problems = {}, []
    for f in found:
        name = os.path.basename(str(f.get("File", "")))
        if name in expected and f.get("RuleID") == CANARY_RULE and f.get("StartLine") == expected[name]:
            canaries[name] = canaries.get(name, 0) + 1
        else:
            problems.append((name, f"a finding ({f.get('RuleID')}, line {f.get('StartLine')})"))
    for name in expected:
        if canaries.get(name, 0) != 1:
            problems.append((name, "its canary was not reported exactly once (the scanner skipped or misread it)"))
    return problems


def admitted_evidence_blobs(suite_mod, repo: str, head: str, tip: str, gitleaks: str, work: str) -> tuple:
    """The walk road's own private scan, and the blob ids scan_unpublished may allow (glitch-6b's ruling (b), with
    the reviews of b1f5c952 and acbdd8e4 folded). Every candidate blob (evidence_candidates, plus athena_suite's own
    binary list) must be absent from the shipped head's history, sit at every path under
    rehearsals/<walk>/evidence/blobs/<sha256 of its stored bytes>, and decode as one gzip member within its bounds and
    the walk's totals; each payload streams into its own 0600 file, its header (MTIME, XFL, OS and any FEXTRA, FNAME,
    FCOMMENT, each at most 4 KiB) into a sibling 0600 file, and every new commit's raw object (headers and message) and
    the paths it changes into their own 0600 files (MAJOR B, E and F: the message scan's blind spot and the fields and
    paths no patch scan reads, closed on the walk road). The canary proof then scans them all.
    Refuses on anything else; reports counts and ids only, never content."""
    import shutil
    import tempfile
    fsck = _fsck_problems(repo)
    if fsck:
        raise LaunchRefused(f"git fsck --strict refuses the scratch repository ({len(fsck)} line(s)); nothing is "
                            f"scanned or fetched")
    cands = evidence_candidates(repo, head, tip)
    for _path, oid, _digest in suite_mod.binary_blobs_hashed(repo, tip, [head]):
        if oid not in cands:
            raise LaunchRefused(f"binary blob {oid} is not among the walk's new commits' blobs")
    if len(cands) > BLOB_MAX_COUNT:
        raise LaunchRefused(f"{len(cands)} evidence blobs, past the walk's cap of {BLOB_MAX_COUNT}")
    in_head = set(_git_out(repo, "rev-list", "--objects", head).split()) if cands else set()
    os.makedirs(work, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="blobs-", dir=work)            # mode 0700
    try:
        src = os.path.join(tmp, "src")
        os.mkdir(src, 0o700)
        for commit in _git_out(repo, "rev-list", f"{head}..{tip}").split():
            # The closure review of d9c14755: MAJOR F, the raw commit object (author, committer, gpgsig, mergetag,
            # encoding and the message), not only %B; MAJOR E, the paths the commit changes, which no patch scan reads.
            _write_private(os.path.join(src, f"commit-{commit}"), _git_out(repo, "cat-file", "commit", commit,
                                                                           binary=True))
            # MAJOR H (closure of 76707728; athena_suite's fix for the same hole): the commit's paths unit is every
            # tree entry (-t: empty subtrees included) the commit holds and none of its parents holds (all of them
            # for a root commit), which covers a merge (MAJOR G) and every entry a diff omits. -z only frames the
            # listing: it plays no security role (a path's bytes land whole in the scanned file either way).
            parents = _git_out(repo, "rev-list", "--parents", "-n", "1", commit).split()[1:]
            if len(parents) >= 3:
                raise LaunchRefused(f"commit {commit} has {len(parents)} parents: a walk commit has at most two "
                                    f"(an octopus is refused by construction)")
            seen = set()
            for parent in parents:
                seen |= set(_tree_entries(repo, parent))
            fresh = [e for e in _tree_entries(repo, commit) if e not in seen]
            _write_private(os.path.join(src, f"paths-{commit}"),
                           b"".join(e.split(b"\t", 1)[1] + b"\n" for e in fresh))
        total = 0
        for oid in sorted(cands):
            if oid in in_head:
                raise LaunchRefused(f"blob {oid} is in the shipped head's history, not only the walk's commits")
            total += stage_evidence_blob(repo, oid, cands[oid], src, BLOB_TOTAL_MAX - total, FETCH_SAYS)
        problems = canary_scan(gitleaks, src, tmp)
        if problems:
            names = sorted({n.split(".")[0] for n, _why in problems})
            raise LaunchRefused(f"the private scan refused {len(names)} item(s) (evidence blobs or commit messages): "
                                f"{', '.join(names)}")
        return tuple(sorted(cands))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# Lane ship-evidence-blobs (glitch-af's ruling, 23 Oct 2026, after the run launcher's rehearsal ship of the freeze line
# 1b20a10a refused on the w-g27 walk's 13 evidence blobs): the OUTWARD ship scan applies to an evidence blob the same
# decode-and-scan rule the fetch applies (admitted_evidence_blobs, unchanged), with this road's own helpers (gunzip_to,
# EVIDENCE_BLOB, the BLOB_* bounds, canary_scan); no second decoder, no --allow-blob road and no per-id list. An
# evidence blob is a binary blob (athena_suite's binary_blobs_hashed, the very list scan_unpublished refuses on) every
# one of whose paths in the shipped commits has the evidence shape; it is admitted only when it is named by the sha256
# of the bytes it stores (the fetch's binding), is stored and decodes within the per-blob bound, decodes as one gzip
# member whose payload is text, keeps the shipped evidence within BLOB_TOTAL_MAX and BLOB_MAX_COUNT, and its payload and
# header fields scan clean with no allowance. Any other binary blob is left out, so scan_unpublished refuses it as
# before; an evidence-shaped blob failing a check refuses here, naming its id and the rule, never content.
# The review of 2ced80f2 and the Lane-orchestrator's rulings on it (23 Oct 2026): the candidates are the fetch's own
# set (is_evidence_candidate: binary to git OR gzip magic, so a gzip git reads as text is decoded too, MAJOR 1), a
# gzip-magic text blob off the evidence paths refuses here, the decode step is the fetch's own (stage_evidence_blob,
# NIT 4), and the count and total caps hold per walk folder as the fetch's hold per walk (MINOR 3).
EVIDENCE_SHAPE = re.compile(r"evals/gap-study-4/(?:rehearsals|takes)/.+/evidence/blobs/[^/]+")


def _shipped_blob_paths(repo: str, head: str, present: list, wanted: set) -> dict:
    """{blob id: set of paths} at which each wanted blob sits in any shipped commit (reachable from head, from no
    public tip): every (path, blob) entry a shipped commit holds that a parent lacks, from `git log --raw` over each
    parent of a merge (--diff-merges=separate) and a root commit's whole tree (--root), NUL-framed, no rename
    folding. A wanted blob is reachable from no public commit, so any shipped commit holding it at a path either got it
    from a shipped parent or added it itself, and the commit that added it lists it here."""
    raw = _git_out(repo, "log", "--diff-merges=separate", "--root", "--raw", "-z", "--no-abbrev", "--no-renames",
                   "--format=", head, *(["--not"] + list(present) if present else []), binary=True)
    toks, found, i = raw.split(b"\0"), {}, 0
    while i < len(toks):
        tok = toks[i].lstrip(b"\n")
        if tok.startswith(b":") and i + 1 < len(toks):
            meta = tok.decode("ascii", "replace").split()
            if len(meta) >= 5 and meta[3] in wanted:
                found.setdefault(meta[3], set()).add(toks[i + 1].decode("utf-8", "surrogateescape"))
            i += 2
        else:
            i += 1
    return found


def _unpublished_candidates(repo: str, head: str, present: list) -> dict:
    """{blob id: set of the paths rev-list names it by} for every blob reachable from head and from no public tip that
    is_evidence_candidate takes (binary to git OR gzip magic, text to git or not: the review of 2ced80f2, MAJOR 1).
    Each blob's first 8000 bytes come from one `git cat-file --batch` stream; the rest is read and dropped."""
    names = {}
    for line in _git_out(repo, "rev-list", "--objects", head, *(["--not"] + list(present) if present else [])
                         ).splitlines():
        oid, _, path = line.partition(" ")
        if path:
            names.setdefault(oid, set()).add(path)
    if not names:
        return {}
    order = sorted(names)
    p = subprocess.Popen(["git", "-C", repo, "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.DEVNULL, env=clean_git_env())
    feed = threading.Thread(target=lambda: (p.stdin.write("".join(o + "\n" for o in order).encode()),
                                            p.stdin.close()), daemon=True)
    feed.start()
    out = {}
    try:
        for oid in order:
            header = p.stdout.readline().decode("ascii", "replace").split()
            if len(header) != 3 or header[0] != oid or not header[2].isdigit():
                raise LaunchRefused(f"git cat-file could not read object {oid}; nothing ships")
            size, first = int(header[2]), b""
            left = size
            while left:
                chunk = p.stdout.read(min(left, 1 << 20))
                if not chunk:
                    raise LaunchRefused(f"git cat-file ended inside object {oid}; nothing ships")
                if len(first) < 8000:
                    first += chunk[:8000 - len(first)]
                left -= len(chunk)
            if p.stdout.read(1) != b"\n":
                raise LaunchRefused(f"git cat-file framed object {oid} off its form; nothing ships")
            if header[1] == "blob" and is_evidence_candidate(first):
                out[oid] = set(names[oid])
    finally:
        feed.join(timeout=600)
        p.stdout.close()
        if p.wait(timeout=600) != 0:
            raise LaunchRefused(f"git cat-file failed (exit {p.returncode}); nothing ships")
    return out


def _evidence_walk(path: str) -> str:
    """The walk (or counted take attempt) folder an evidence path sits in: rehearsals/<walk> or takes/<slot>/<n>."""
    return path.rsplit("/evidence/blobs/", 1)[0]


def outward_evidence_blobs(suite_mod, repo: str, head: str, present: list, gitleaks: str, work: str) -> tuple:
    """The evidence blob ids the outward scan's scan_unpublished may allow (see the comment above); () when the shipped
    commits bring no candidate, in which case no file is decoded and no scanner runs.

    The candidates are the fetch's (the review of 2ced80f2, MAJOR 1): every shipped blob binary to git or starting
    with gzip magic (_unpublished_candidates), with athena_suite's own binary list on top. One every path of which in
    the shipped commits has the evidence shape is decoded and scanned by the one rule (stage_evidence_blob, then
    canary_scan); a gzip-magic blob git reads as text anywhere else refuses here; a binary one anywhere else is left to
    scan_unpublished, which refuses it unless a committed ruling names it, as before. The count and total caps hold per
    walk folder, as the fetch's hold per walk (one fetch is one walk's commits; MINOR 3); no cap value changed."""
    import shutil
    import tempfile
    binary = {}
    for path, oid, _digest in suite_mod.binary_blobs_hashed(repo, head, list(present)):
        binary.setdefault(oid, set()).add(path)
    cands = _unpublished_candidates(repo, head, present)
    for oid, where in binary.items():
        cands.setdefault(oid, set()).update(where)
    if not cands:
        return ()
    for oid, where in _shipped_blob_paths(repo, head, present, set(cands)).items():
        cands[oid] |= where
    evidence = {oid: where for oid, where in cands.items() if all(EVIDENCE_SHAPE.fullmatch(p) for p in where)}
    stray = sorted(oid for oid in cands if oid not in evidence and oid not in binary)
    if stray:
        raise LaunchRefused(f"the shipped commits bring {len(stray)} gzip blob(s) git reads as text off the evidence "
                            f"paths: {', '.join(stray)}; nothing ships")
    if not evidence:
        return ()
    walks = {}
    for oid, where in evidence.items():
        for p in where:
            walks.setdefault(_evidence_walk(p), set()).add(oid)
    for walk, oids in sorted(walks.items()):
        if len(oids) > BLOB_MAX_COUNT:
            raise LaunchRefused(f"the shipped commits bring {len(oids)} evidence blobs in one walk folder, past the cap "
                                f"of {BLOB_MAX_COUNT}; nothing ships")
    os.makedirs(work, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="blobs-", dir=work)            # mode 0700
    try:
        src = os.path.join(tmp, "src")
        os.mkdir(src, 0o700)
        decoded = {walk: 0 for walk in walks}
        for oid in sorted(evidence):
            mine = sorted({_evidence_walk(p) for p in evidence[oid]})
            room = min(BLOB_TOTAL_MAX - decoded[walk] for walk in mine)
            size = stage_evidence_blob(repo, oid, sorted(evidence[oid]), src, room, OUTWARD_SAYS)
            for walk in mine:
                decoded[walk] += size
        findings = canary_scan(gitleaks, src, tmp)
        if findings:
            ids = sorted({n.split(".")[0] for n, _why in findings})
            raise LaunchRefused(f"the private scan refused {len(ids)} evidence blob(s): {', '.join(ids)}; "
                                f"nothing ships")
        return tuple(sorted(evidence))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def load_suite(suite: str):
    """athena_suite.py from the operator's aegis checkout, loaded by path (its module level only defines names)."""
    import importlib.util
    if not isinstance(suite, str) or not os.path.isabs(suite) or not os.path.isfile(suite):
        raise LaunchRefused("the athena_suite.py path is not an existing absolute file")
    spec = importlib.util.spec_from_file_location("athena_suite_for_walk_launch", suite)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# OD57 on the walk return road (glitch-b5's ruling, 16 Oct 2026, after the walk operator found no ruling reached it):
# athena_suite.scan_unpublished admits OD57's one line (its RULED_LINES, through _ruled_bash's allow-list, aegis
# c1c4496) exactly as it does for a suite run. The return road binds the loaded suite's line rulings to the reviewed
# ones (box/scan_record.RULED_LINES: the same ruling, rule, length and sha256) and refuses a suite without them, hands
# scan_unpublished a ruled list, and records each admission under "lines_ruled"; anything else on that list refuses.
def od57_bound(suite_mod) -> None:
    """Refuses unless the suite's line rulings are exactly the reviewed OD57 ones and it carries the Bash allow-list."""
    def binding(rulings):
        return [(r.get("ruling"), r.get("rule"), r.get("bytes"), r.get("sha256")) for r in rulings
                if isinstance(r, dict)]
    got = getattr(suite_mod, "RULED_LINES", None)
    if not isinstance(got, tuple) or len(got) != len(_scan_record.RULED_LINES) \
            or binding(got) != binding(_scan_record.RULED_LINES) \
            or not callable(getattr(suite_mod, "_ruled_bash", None)):
        raise LaunchRefused("the athena_suite.py's line rulings are not the reviewed OD57 ones; nothing is fetched")


def od57_lines(ruled) -> list:
    """The OD57 admissions scan_unpublished listed; any other entry refuses (the return road allows nothing else)."""
    prefixes = tuple(r["ruling"] + ":" for r in _scan_record.RULED_LINES)
    if not all(isinstance(u, str) and u.startswith(prefixes) for u in ruled):
        raise LaunchRefused("the return scan admitted something other than an OD57 line; nothing is fetched")
    return sorted(set(ruled))


# OD57 byte twins on the OUTWARD road (the Lane-orchestrator's ruling, 23 Oct 2026, under Javier's standing delegation,
# after this lane's real-line scan of 1b20a10a refused five OD57 findings in tests/fixtures/recorded-gemini-w-g21/,
# byte copies of rehearsals/w-g21/'s walk records). No path is widened and nothing new is allowed: a finding the
# suite's own OD57 door refuses is admitted only when the flagged file's blob at the finding's commit is the very blob
# (the same id, a regular file) of a walk record the suite's door reads as agent text at that commit (its own
# _od57_file, so RULED_AGENT_TEXT and RULED_VENDOR_TEXT), and the suite's own ruled_line_findings, handed the finding
# at that record's path, admits it there: the shared rule with that record's family shapes and kind, the carried-commit
# and whole-line checks, and the probe rescan (any finding of the rule left on that line refuses). Every twin of the
# file must admit it. The road runs only when the suite's od57_rule.py and od57_shapes.py are byte for byte this
# repository's box/ copies and its RULED_LINES are the reviewed ones; otherwise the door is left as it is and such a
# finding refuses. Each admission is listed as "OD57:<commit>:<path>:<line> via <twin path>[, <twin path>...]". Any
# other rule, a byte difference, a missing twin and a twin outside the ruled set still refuse.
OD57_TWIN_MODES = ("100644", "100755")
_OD57_COPIES = {"od57_rule": HERE / "box" / "od57_rule.py", "od57_shapes": HERE / "box" / "od57_shapes.py"}


def _od57_door(suite_mod):
    """The module namespace scan_unpublished resolves its OD57 door in, when that door is the shared rule (see above);
    else None."""
    g = getattr(getattr(suite_mod, "scan_unpublished", None), "__globals__", None)
    if not isinstance(g, dict) or not callable(g.get("ruled_line_findings")) or not callable(g.get("_od57_file")):
        return None
    try:
        od57_bound(types.SimpleNamespace(RULED_LINES=g.get("RULED_LINES"), _ruled_bash=g.get("_ruled_bash")))
        for name, copy in _OD57_COPIES.items():
            if Path(getattr(g.get(name), "__file__", "") or "").read_bytes() != copy.read_bytes():
                return None
    except (LaunchRefused, OSError, ValueError):
        return None
    return g


def _tree_files(repo: str, rev: str) -> list:
    """(mode, blob id, path) of every regular file in `rev`'s whole tree, NUL-framed."""
    out = []
    for rec in _git_out(repo, "ls-tree", "-r", "-z", "--full-tree", rev, binary=True).split(b"\0"):
        meta, sep, path = rec.partition(b"\t")
        parts = meta.decode("ascii", "replace").split()
        if sep and len(parts) == 3 and parts[1] == "blob" and parts[0] in OD57_TWIN_MODES:
            out.append((parts[0], parts[2], path.decode("utf-8", "surrogateescape")))
    return out


def _od57_twin_door(door: dict, original):
    """The suite's ruled_line_findings, then the twin road (see above) over what it still refuses."""
    trees = {}

    def twins_of(repo, f):
        rev, path = f.get("Commit"), f.get("File")
        if not (isinstance(rev, str) and HEX40.fullmatch(rev) and isinstance(path, str) and door["_od57_file"](path)
                is None):
            return []
        if rev not in trees:
            try:
                trees[rev] = _tree_files(repo, rev)
            except LaunchRefused:
                trees[rev] = []
        oid = [o for _m, o, p in trees[rev] if p == path]
        if len(oid) != 1:
            return []
        return sorted(p for _m, o, p in trees[rev] if o == oid[0] and p != path and door["_od57_file"](p) is not None)

    def ruled_line_findings(repo, findings, carried, gitleaks, workdir, flags, scan_reads=None):
        still, admitted = original(repo, findings, carried, gitleaks, workdir, flags, scan_reads)
        refused, groups = [], []
        for f in still:
            twins = twins_of(repo, f)
            if twins:
                groups.append((f, [dict(f, File=t) for t in twins]))
            else:
                refused.append(f)
        if not groups:
            return still, admitted
        left, ok = original(repo, [s for _f, group in groups for s in group], carried, gitleaks, workdir, flags,
                            scan_reads)
        left_ids, ok = {id(s) for s in left}, set(ok)
        for f, group in groups:
            names = [r["ruling"] for r in door["RULED_LINES"] if r.get("rule") == f.get("RuleID")]
            if len(names) == 1 and all(id(s) not in left_ids
                                       and f"{names[0]}:{s['Commit']}:{s['File']}:{s['StartLine']}" in ok
                                       for s in group):
                admitted.append(f"{names[0]}:{f['Commit']}:{f['File']}:{f['StartLine']} via "
                                + ", ".join(s["File"] for s in group))
            else:
                refused.append(f)
        return refused, admitted

    return ruled_line_findings


@contextlib.contextmanager
def _od57_twins(suite_mod, used: list, lines_ruled):
    """scan_unpublished's OD57 door with the twin road (see above) for the duration of one outward scan, restored
    after; on a scan that returns, the OD57 admissions it listed in `used` are added to `lines_ruled`."""
    door = _od57_door(suite_mod)
    original = door["ruled_line_findings"] if door is not None else None
    if door is not None:
        door["ruled_line_findings"] = _od57_twin_door(door, original)
    try:
        yield
        if lines_ruled is not None:
            prefixes = tuple(r["ruling"] + ":" for r in _scan_record.RULED_LINES)
            lines_ruled.extend(sorted({u for u in used if isinstance(u, str) and u.startswith(prefixes)}))
    finally:
        if door is not None:
            door["ruled_line_findings"] = original


def outward_scan(suite_mod, *, repo: str, bundle: str, head: str, gitleaks: str, work: str,
                 lines_ruled: list = None) -> int:
    """athena_suite.cmd_run's checks over a scratch clone of the bundle, its own functions: the secret-shaped names
    (less the reviewed exemptions) and ignore files, then gitleaks over every commit the public GARS remote does not
    serve, its OD57 door with the twin road (_od57_twins). Returns how many commits were scanned, and adds the OD57
    admissions to `lines_ruled` when given; any refusal raises."""
    os.makedirs(work, exist_ok=True)
    check = os.path.join(work, "check-clone")
    doc, _ = suite_mod.committed_allowlist(suite_mod.ALLOWLIST)
    reviewed, ruled, ruled_msgs = suite_mod.validate_allowlist(doc, SUITE_KIND)
    suite_mod.scratch_clone(bundle, check, work)
    hits, _ = suite_mod.exempt_reviewed(check, head, suite_mod.name_hits(check, head, ()), reviewed)
    hits += suite_mod.ignore_hits(check, head, work)
    if hits:
        raise LaunchRefused(f"the bundle would carry {len(hits)} secret-shaped file(s); nothing ships")
    public = suite_mod.fetch_public_refs(check, suite_mod.PUBLIC_REFERENCE[SUITE_KIND], work)
    if not public:
        raise LaunchRefused("the public GARS remote advertised nothing; nothing ships")
    evidence = outward_evidence_blobs(suite_mod, check, head, public, gitleaks, work)     # lane ship-evidence-blobs
    used = []
    with _od57_twins(suite_mod, used, lines_ruled):                                       # the OD57 twin ruling
        return suite_mod.scan_unpublished(check, head, work, gitleaks, public, suite_mod.rulings_file(repo), evidence,
                                          ruled, used, ruled_msgs)


def ship(runner: Runner, *, repo: str, ref: str, suite: str, reserve: str, gitleaks: str, work: str,
         precheck=None, suite_module=None) -> dict:
    precheck = machine_gate.mac_precheck if precheck is None else precheck
    problems = precheck(suite)
    if problems:
        # athena-made words (a run's state, an off-form list line) are never echoed (r7 MINOR): the count, and which
        # of a fixed set of kinds were seen, only.
        kinds = sorted({k for p in problems for k, frag in PRECHECK_KINDS.items() if frag in str(p)})
        raise LaunchRefused(f"the Mac pre-check refuses: {len(problems)} problem(s)"
                            + (f" ({', '.join(kinds)})" if kinds else ""))
    if _sha256(reserve) != RESERVE_SHA256:
        raise LaunchRefused("athena-reserve is not the runbook's pinned bytes")
    # The tag case, closed by construction (closure of 78ee31e7): the ref must name a commit object itself, never an
    # annotated tag that peels to one (a tag object's own message and tagger are no commit's).
    if _ok(runner.local(["git", "-C", repo, "cat-file", "-t", ref]), "cat-file -t").strip() != "commit":
        raise LaunchRefused(f"the ref {ref!r} does not name a commit object (an annotated tag is refused)")
    head = _ok(runner.local(["git", "-C", repo, "rev-parse", "--verify", f"{ref}^{{commit}}"]), "rev-parse").strip()
    if not HEX40.fullmatch(head):
        raise LaunchRefused(f"the ref {ref!r} does not name one commit")
    if runner.local(["git", "-C", repo, "merge-base", "--is-ancestor", PINNED_TREE, head])[0] != 0:
        raise LaunchRefused(f"the head {head[:12]} does not carry the pinned tree {PINNED_TREE[:12]}'s history")
    os.makedirs(work, exist_ok=True)
    bundle = os.path.join(work, "walk-out.bundle")
    if os.path.lexists(bundle):
        raise LaunchRefused(f"{bundle} exists: a bundle is never overwritten")
    _ok(runner.local(["git", "-C", repo, "bundle", "create", bundle, ref]), "git bundle create")
    _ok(runner.local(["git", "-C", repo, "bundle", "verify", bundle]), "git bundle verify")
    heads = _ok(runner.local(["git", "bundle", "list-heads", bundle]), "git bundle list-heads").split()
    if heads != [head, f"refs/heads/{ref}"]:
        raise LaunchRefused("the bundle's heads are not exactly the ref at its head")
    lines_ruled = []        # the outward scan's OD57 admissions, each twin one naming its twin
    suite_mod = load_suite(suite) if suite_module is None else suite_module
    try:
        scanned = outward_scan(suite_mod, repo=repo, bundle=bundle, head=head, gitleaks=gitleaks,
                               work=os.path.join(work, "outward-scan"), lines_ruled=lines_ruled)
    except LaunchRefused:
        raise
    except Exception as e:  # noqa: BLE001 - athena_suite's Refused, a git failure: nothing ships unscanned
        raise LaunchRefused(f"the outward scan refused, the bundle stays on the Mac: {type(e).__name__}: "
                            f"{str(e)[:300]}") from None
    digest = _sha256(bundle)
    child = _child(_ok(runner.remote(f"umask 077; mktemp -d {CHILD_PARENT}/w-XXXXXXXX"), "the athena child").strip())
    for src, name, want in ((bundle, "walk-out.bundle", digest), (reserve, "athena-reserve", RESERVE_SHA256)):
        _ok(runner.copy_to(src, f"{child}/{name}"), f"copying {name}")
        got = _ok(runner.remote(f"sha256sum {child}/{name}"), f"reading {name}'s sha256").split()[:1]
        if got != [want]:
            raise LaunchRefused(f"{name}'s sha256 on athena is not the Mac's")
    _ok(runner.remote(f"{REMOTE_GIT} clone -q -b {shlex.quote(ref)} {child}/walk-out.bundle {child}/repo"), "the athena clone")
    if _ok(runner.remote(f"{REMOTE_GIT} -C {child}/repo rev-parse HEAD"), "the athena head").strip() != head:
        raise LaunchRefused("athena's clone is not at the head")
    return {"child": child, "head": head, "bundle_sha256": digest, "scanned_commits": scanned,
            "lines_ruled": lines_ruled}


# ------------------------------------------------------------------------------------------------ run
def run_command(*, child: str, walk: str, cell: dict, reason: str) -> str:
    """The one remote command that starts the walk under the hold (see the module's `run`)."""
    _child(child)
    hid = hold_id(walk)
    if set(cell) != set(CELL) or not all(isinstance(v, str) and v for v in cell.values()):
        raise LaunchRefused(f"the cell needs exactly {CELL}")
    if not isinstance(reason, str) or not reason.strip():
        raise LaunchRefused("a walk is run for a reason")
    repo = f"{child}/repo"
    env = _gate_env(hid)
    walk_env = f"{env} {COMMIT_IDENTITY}"
    walk_argv = ["python3", "-B", f"{repo}/evals/gap-study-4/walk_runner.py", "--walk", walk]
    for k in CELL:
        walk_argv += [f"--{k}", cell[k]]
    walk_argv += ["--reason", reason]
    return _held_command(child=child, hid=hid, env=env, held_env=walk_env, argv=walk_argv)


def _gate_env(hid: str) -> str:
    """The athena gate's variables under hold `hid` (the walk's and the probe's own hold), and the config parent."""
    return (f"env {machine_gate.ENV_ACCOUNT}={SUITE_ACCOUNT} {machine_gate.ENV_RESERVATION}={RESERVATION} "
            f"{machine_gate.ENV_HOLD}={hid} {machine_gate.ENV_SLOTS}={machine_gate.SLOTS} {CONFIG_PARENT_ENV}={CONFIG_PARENT}")


def _held_command(*, child: str, hid: str, env: str, held_env: str, argv: list) -> str:
    """The claim, the gate, then `argv` under `athena-reserve hold --by <hid>` with nohup, the pid and the exit file
    (the walk's start, shared by the stub-model probe's: lane vendor-b27). run_command's string is byte-unchanged by
    this factoring (tests/test_stub_model_probe.py pins its sha256 from the base 04c4e774)."""
    repo = f"{child}/repo"
    gate = f"{env} python3 -B {repo}/evals/gap-study-4/machine_gate.py athena-check"
    walk_env = held_env     # the name test_walk_launch's hold-dropped witness edits, kept (stage 6)
    held = (f"python3 {child}/athena-reserve hold --by {hid} -- {walk_env} "
            + " ".join(shlex.quote(a) for a in argv))
    # The exit file is written by the shell around the hold, so a walk that died still leaves its code.
    body = f"{held}; echo $? > {child}/walk.exit"
    # The claim (the review's NIT 7): the reservation is created with O_EXCL, carrying this walk's own hold id, so a
    # reservation already there refuses the start and nothing that arrives later is overwritten unseen by this
    # step; `hold` then rewrites it with the same id and removes it when the walk ends. A closed gate removes the claim.
    claim = ("import datetime as d, json, os, sys; fd = os.open(sys.argv[1], os.O_WRONLY | os.O_CREAT | os.O_EXCL, "
             "0o644); os.write(fd, json.dumps({'by': sys.argv[2], 'until': (d.datetime.now().astimezone() + "
             "d.timedelta(minutes=29)).isoformat(timespec='seconds')}).encode()); os.close(fd)")
    # After the start (closure review NIT C): the hold must still be running a moment later with the reservation
    # still this walk's; a hold that exited (athena-reserve refused, the walk ended at once) removes the claim and the
    # start exits non-zero with the log's tail, never printing a pid for a dead walk. Recovery after any failed start:
    # `athena-reserve clear` (run as javier on athena) removes a reservation a crashed start left behind.
    held_check = "import json, sys; sys.exit(json.load(open(sys.argv[1])).get('by') != sys.argv[2])"
    alive = (f"sleep 3; if ! kill -0 $(cat {child}/walk.pid) 2>/dev/null; then rm -f {RESERVATION}; "
             f"tail -5 {child}/walk.log >&2; exit 1; fi; "
             f"python3 -I -c {shlex.quote(held_check)} {RESERVATION} {hid} || "
             f"{{ echo 'the hold holds no reservation' >&2; exit 1; }}; ")
    return (f"umask {UMASK}; set -e; test -f {child}/athena-reserve || exit 1; "
            f"python3 -I -c {shlex.quote(claim)} {RESERVATION} {hid}; "
            f"{gate} > {child}/gate.out 2>&1 || {{ rm -f {RESERVATION}; exit 1; }}; "
            f"nohup sh -c {shlex.quote(body)} > {child}/walk.log 2>&1 < /dev/null & echo $! > {child}/walk.pid; "
            f"{alive}cat {child}/walk.pid")


def run(runner: Runner, *, child: str, walk: str, cell: dict, reason: str) -> int:
    out = _ok(runner.remote(run_command(child=child, walk=walk, cell=cell, reason=reason)), "starting the walk")
    pid = out.strip().splitlines()[-1] if out.strip() else ""
    if not re.fullmatch(r"[0-9]+", pid):
        raise LaunchRefused("the walk's pid was not recorded")
    return int(pid)


def status(runner: Runner, *, child: str) -> str:
    _child(child)
    code, out, _ = runner.remote(f"if kill -0 $(cat {child}/walk.pid) 2>/dev/null; then echo running; "
                                 f"elif test -f {child}/walk.exit; then echo exit=$(cat {child}/walk.exit); "
                                 f"else echo lost; fi")
    state = out.strip() if code == 0 else ""
    # athena-made bytes: only the three closed forms are ever returned or printed (closure review of a3b09f02)
    if not re.fullmatch(r"running|lost|exit=[0-9]{1,3}", state):
        raise LaunchRefused("the walk's state cannot be read (not one of its closed forms)")
    return state


# ------------------------------------------------------------------------------------------- the stub-model probe
# Lane vendor-b27 (glitch-f1's ruling 1 on the B27 design, 21 Oct 2026): box/stub_model_probe.py runs on athena through
# this road, never a walk: `probe` starts it under its own hold (the walk's claim, gate, hold, nohup, pid and exit file,
# _held_command), and `fetch-probe` copies its one output folder back. `ship` and `status` serve it unchanged. The
# probe commits nothing, so it carries no commit identity, and its output folder lives in the child, outside the clone.
PROBE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,39}")
PROBE_SCENARIOS = re.compile(r"all|[A-Z][A-Za-z0-9-]{0,15}(,[A-Z][A-Za-z0-9-]{0,15}){0,15}")
PROBE_IMAGE = re.compile(r"sha256:[0-9a-f]{64}")
PROBE_MODULE = "evals/gap-study-4/box/stub_model_probe.py"
PROBE_PREFIX = "stub-probe-"
PROBE_MAX_FILES = 20000
PROBE_MAX_BYTES = 512 * 1024 * 1024


def probe_hold_id(probe: str) -> str:
    if not isinstance(probe, str) or not PROBE_ID.fullmatch(probe):
        raise LaunchRefused(f"the probe id {probe!r} is not one short path segment")
    hid = f"gap4-probe-{probe}"
    if not machine_gate.HOLD_ID.match(hid):
        raise LaunchRefused(f"the hold id {hid!r} is not one athena-reserve accepts (BY_RE, 64 characters)")
    return hid


def probe_output(child: str, probe: str) -> str:
    probe_hold_id(probe)
    return f"{_child(child)}/{PROBE_PREFIX}{probe}"


def fresh_child_guard(child: str) -> str:
    """One probe or walk per child (glitch-f1's ruling 2, made structural by REVIEW-vendor-b27-25ffff5 MINOR 4): the
    probe's start refuses a child that already holds a walk's or a probe's process files, whose log and exit file it
    would otherwise truncate. In probe_command only; run_command's string is byte-unchanged."""
    _child(child)
    return (f"if test -e {child}/walk.pid || test -e {child}/walk.log || test -e {child}/walk.exit; then "
            f"echo 'the child already ran a walk or a probe' >&2; exit 1; fi; ")


def probe_command(*, child: str, probe: str, scenarios: str, image: str, reason: str) -> str:
    """The one remote command that starts the probe under its hold (the walk's start, _held_command), behind
    fresh_child_guard."""
    _child(child)
    hid = probe_hold_id(probe)
    if not isinstance(scenarios, str) or not PROBE_SCENARIOS.fullmatch(scenarios):
        raise LaunchRefused("the scenarios are a comma list of scenario names, or all")
    if not isinstance(image, str) or not PROBE_IMAGE.fullmatch(image):
        raise LaunchRefused("the gemini image is a full image id, sha256:<64 hex>")
    if not isinstance(reason, str) or not reason.strip():
        raise LaunchRefused("a probe is run for a reason")
    repo = f"{child}/repo"
    env = _gate_env(hid)
    argv = ["python3", "-B", f"{repo}/{PROBE_MODULE}", "--box", f"{repo}/evals/gap-study-4/box",
            "--scratch-parent", CONFIG_PARENT, "--output", probe_output(child, probe), "--gemini-image", image,
            "--scenarios", scenarios, "--reason", reason]
    return fresh_child_guard(child) + _held_command(child=child, hid=hid, env=env, held_env=env, argv=argv)


def probe(runner: Runner, *, child: str, probe_id: str, scenarios: str, image: str, reason: str) -> int:
    out = _ok(runner.remote(probe_command(child=child, probe=probe_id, scenarios=scenarios, image=image,
                                          reason=reason)), "starting the probe")
    pid = out.strip().splitlines()[-1] if out.strip() else ""
    if re.fullmatch(r"[0-9]+", pid) is None:     # spelled apart from run's check (the pid-isdigit witness's text)
        raise LaunchRefused("the probe's pid was not recorded")
    return int(pid)


# Lane hook-control (glitch-f1's rulings on lane-reports/hook-control-DESIGN.md, 21 Oct 2026): the D8 hook positive
# control, box/hook_control_probe.py, on the stub-model probe's road: the same hold id rule, child guard, held start and
# output folder; the images are named per harness (each exactly when one of its scenarios is named).
HOOK_PROBE_MODULE = "evals/gap-study-4/box/hook_control_probe.py"
HOOK_PROBE_SCENARIOS = re.compile(r"(HG|HO-C0|HO-C1)(,(HG|HO-C0|HO-C1)){0,2}")
HOOK_PROBE_HARNESS = {"HG": "gemini", "HO-C0": "codex", "HO-C1": "codex"}


def hook_probe_command(*, child: str, probe: str, scenarios: str, gemini_image, codex_image, reason: str) -> str:
    """The one remote command that starts the hook control under its hold (_held_command), behind fresh_child_guard."""
    _child(child)
    hid = probe_hold_id(probe)
    if not isinstance(scenarios, str) or not HOOK_PROBE_SCENARIOS.fullmatch(scenarios):
        raise LaunchRefused("the hook control's scenarios are a comma list of HG, HO-C0 and HO-C1")
    wanted = {HOOK_PROBE_HARNESS[s] for s in scenarios.split(",")}
    images = {"gemini": gemini_image, "codex": codex_image}
    for harness, img in images.items():
        if (harness in wanted) != (img is not None):
            raise LaunchRefused(f"the {harness} image is named exactly when one of its scenarios is")
        if img is not None and (not isinstance(img, str) or not PROBE_IMAGE.fullmatch(img)):
            raise LaunchRefused(f"the {harness} image is a full image id, sha256:<64 hex>")
    if not isinstance(reason, str) or not reason.strip():
        raise LaunchRefused("a hook control is run for a reason")
    repo = f"{child}/repo"
    env = _gate_env(hid)
    argv = ["python3", "-B", f"{repo}/{HOOK_PROBE_MODULE}", "--box", f"{repo}/evals/gap-study-4/box",
            "--scratch-parent", CONFIG_PARENT, "--output", probe_output(child, probe), "--scenarios", scenarios]
    for harness in ("gemini", "codex"):
        if images[harness] is not None:
            argv += [f"--{harness}-image", images[harness]]
    argv += ["--reason", reason]
    return fresh_child_guard(child) + _held_command(child=child, hid=hid, env=env, held_env=env, argv=argv)


def probe_hooks(runner: Runner, *, child: str, probe_id: str, scenarios: str, gemini_image, codex_image,
                reason: str) -> int:
    out = _ok(runner.remote(hook_probe_command(child=child, probe=probe_id, scenarios=scenarios,
                                               gemini_image=gemini_image, codex_image=codex_image, reason=reason)),
              "starting the hook control")
    last = out.strip().splitlines()[-1] if out.strip() else ""
    if not (last.isascii() and last.isdigit()):
        raise LaunchRefused("the hook control's pid was not recorded")
    return int(last)


def _probe_members(tar, top: str) -> list:
    """Every member of the probe's tar: a regular file or a folder under `top`/, no link, device, absolute path or
    `..`; within PROBE_MAX_FILES and PROBE_MAX_BYTES. Refuses anything else, naming the rule, never a member's bytes."""
    members, total = tar.getmembers(), 0
    if len(members) > PROBE_MAX_FILES:
        raise LaunchRefused(f"the probe's tar holds more than {PROBE_MAX_FILES} members")
    for m in members:
        name = m.name
        parts = name.split("/")
        if name.startswith("/") or ".." in parts or parts[0] != top or "\\" in name:
            raise LaunchRefused("a member of the probe's tar sits outside its one output folder")
        if not (m.isfile() or m.isdir()):
            raise LaunchRefused("a member of the probe's tar is not a regular file or a folder")
        total += m.size
        if total > PROBE_MAX_BYTES:
            raise LaunchRefused(f"the probe's tar holds more than {PROBE_MAX_BYTES} bytes")
    return members


def _extract_probe(tar_path: str, top: str, into: str) -> str:
    """The tar's files written under `into` (a new folder) by this code, never tarfile's extractall."""
    import tarfile
    os.mkdir(into, 0o700)
    with tarfile.open(tar_path, "r:") as tar:
        for m in _probe_members(tar, top):
            dst = os.path.join(into, *m.name.split("/"))
            if m.isdir():
                os.makedirs(dst, mode=0o700, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(dst), mode=0o700, exist_ok=True)
            src = tar.extractfile(m)
            fd = os.open(dst, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as fh:
                for block in iter(lambda: src.read(CHUNK), b""):
                    fh.write(block)
    return os.path.join(into, top)


def probe_manifest_problems(folder: str) -> list:
    """The probe's manifest.json against the folder: every listed file present with its sha256 and size, and every
    file listed (manifest.json aside)."""
    try:
        with open(os.path.join(folder, "manifest.json"), encoding="utf-8") as fh:
            doc = json.load(fh)
        listed = doc["files"]
        if doc.get("record_kind") != "stub-model-probe" or not isinstance(listed, dict):
            raise ValueError
    except (OSError, ValueError, KeyError, TypeError):
        return ["the probe's manifest.json is missing or off its shape"]
    out, seen = [], set()
    for b, dirs, fs in os.walk(folder):
        for f in fs:
            rel = os.path.relpath(os.path.join(b, f), folder)
            if rel != "manifest.json":
                seen.add(rel)
    for rel in sorted(seen - set(listed)):
        out.append(f"{rel}: not in the manifest")
    for rel, want in sorted(listed.items()):
        p = os.path.join(folder, rel)
        if rel not in seen:
            out.append(f"{rel}: listed, absent")
        elif _sha256(p) != want.get("sha256") or os.path.getsize(p) != want.get("bytes"):
            out.append(f"{rel}: its sha256 or size is not the manifest's")
    return out


def fetch_probe(runner: Runner, *, child: str, probe_id: str, out: str, gitleaks: str, work: str) -> dict:
    """The probe's output folder back to the Mac: tarred on athena, copied, its sha256 read on both sides, unpacked by
    this code into the work folder, checked against its manifest, scanned with no allowance (canary_scan over a flat
    copy of every file, each carrying its canary), and only then moved to `out` (a new folder)."""
    import shutil
    _child(child)
    probe_hold_id(probe_id)
    top = f"{PROBE_PREFIX}{probe_id}"
    if not isinstance(out, str) or not os.path.isabs(out) or os.path.basename(out) != top or os.path.lexists(out):
        raise LaunchRefused(f"the Mac folder is a new absolute path named {top}")
    st = status(runner, child=child)
    if st == "running":
        raise LaunchRefused("the probe is still running; nothing is fetched")
    remote_tar = f"{child}/{top}.tar"
    _ok(runner.remote(f"test -d {child}/{top} && tar -C {child} -cf {remote_tar} {top}"), "the probe's tar")
    digest = _ok(runner.remote(f"sha256sum {remote_tar}"), "the probe tar's sha256").split()[:1]
    os.makedirs(work, exist_ok=True)
    local = os.path.join(work, f"{top}.tar")
    if os.path.lexists(local):
        raise LaunchRefused(f"{local} exists: a tar is never overwritten")
    _ok(runner.copy_from(remote_tar, local), "copying the probe's tar")
    copied = _sha256(local)     # spelled apart from fetch's check, which a test_walk_launch witness edits by its text
    if [copied] != digest:
        raise LaunchRefused("the probe tar's sha256 on the Mac is not athena's")
    staged = _extract_probe(local, top, os.path.join(work, "probe-unpacked"))
    problems = probe_manifest_problems(staged)
    if problems:
        raise LaunchRefused(f"the probe's folder does not match its manifest ({len(problems)} problem(s)): "
                            f"{'; '.join(problems[:5])}")
    scan_src = os.path.join(work, "probe-scan")
    os.mkdir(scan_src, 0o700)
    n = 0
    for b, dirs, fs in os.walk(staged):
        dirs.sort()
        for f in sorted(fs):
            n += 1
            shutil.copyfile(os.path.join(b, f), os.path.join(scan_src, f"{n:05d}-{f}"))
    found = canary_scan(gitleaks, scan_src, work)
    if found:
        raise LaunchRefused(f"the probe's scan refused {len(found)} file(s): "
                            f"{', '.join(sorted({name for name, _why in found})[:10])}; nothing is moved")
    os.rename(staged, out)
    return {"state": st, "fetched": out, "files": n, "tar_sha256": digest[0]}


# ------------------------------------------------------------------------------------------------ fetch
def fetch(runner: Runner, *, child: str, head: str, ref: str, records: str, gitleaks: str, work: str,
          suite: str, suite_module=None) -> dict:
    _child(child)
    if not HEX40.fullmatch(head or ""):
        raise LaunchRefused("the head is one full commit id")
    st = status(runner, child=child)
    if st == "running":
        raise LaunchRefused("the walk is still running; nothing is fetched")
    if _ok(runner.remote(f"{REMOTE_GIT} -C {child}/repo cat-file -t {shlex.quote(ref)}"), "the athena ref's type").strip() \
            != "commit":
        raise LaunchRefused(f"athena's ref {ref!r} does not name a commit object (an annotated tag is refused)")
    tip = _ok(runner.remote(f"{REMOTE_GIT} -C {child}/repo rev-parse --verify {shlex.quote(ref)}^{{commit}}"),
              "the athena tip").strip()
    if not HEX40.fullmatch(tip):
        raise LaunchRefused("athena's tip is not one full commit id")
    if tip == head:
        return {"state": st, "fetched": None, "why": "the walk made no commit"}
    if runner.remote(f"{REMOTE_GIT} -C {child}/repo merge-base --is-ancestor {head} {tip}")[0] != 0:
        raise LaunchRefused("athena's tip does not descend from the shipped head")
    _ok(runner.remote(f"{REMOTE_GIT} -C {child}/repo bundle create {child}/walk-back.bundle {head}..{shlex.quote(ref)}"),
        "the back bundle")
    digest = _ok(runner.remote(f"sha256sum {child}/walk-back.bundle"), "the back bundle's sha256").split()[:1]
    os.makedirs(work, exist_ok=True)
    local = os.path.join(work, "walk-back.bundle")
    if os.path.lexists(local):
        raise LaunchRefused(f"{local} exists: a bundle is never overwritten")
    _ok(runner.copy_from(f"{child}/walk-back.bundle", local), "copying the back bundle")
    if [_sha256(local)] != digest:
        raise LaunchRefused("the back bundle's sha256 on the Mac is not athena's")
    scratch = os.path.join(work, "back-scan")
    # MAJOR I (closure of 76707728): the bundle names exactly one ref, the walk's tip; the scratch takes no tags; and
    # everything the scratch gains is exactly the objects reachable from the tip and not from the head (an extra
    # blob or tag riding in the pack refuses), so the scan's scope is everything that can reach the records.
    heads = _ok(runner.local(["git", "bundle", "list-heads", local]), "the back bundle's heads").split()
    if heads != [tip, f"refs/heads/{ref}"]:
        raise LaunchRefused("the back bundle's heads are not exactly the walk's tip at its ref")
    # r7 MINOR: the scratch is made from an EMPTY template (athena_suite's scratch_clone), so no template config or
    # hook (fsck.zeroPaddedFilemode=ignore, say) reaches it, and it must then be plain.
    empty = os.path.join(work, "empty-template")
    os.makedirs(empty, exist_ok=True)
    if os.listdir(empty):
        raise LaunchRefused("the scratch's empty template folder is not empty")
    _ok(runner.local(["git", "clone", "-q", "--shared", "--no-checkout", f"--template={empty}", records, scratch]),
        "the scan clone")
    if scratch_problems(scratch):
        raise LaunchRefused("the scan clone is not plain (a config key or a hook beyond what git clone writes)")
    _ok(runner.local(["git", "-C", scratch, "fetch", "-q", "--no-tags", local, f"{ref}:refs/walk/back"]),
        "the scan fetch")
    got = _ok(runner.local(["git", "-C", scratch, "rev-parse", "refs/walk/back"]), "the fetched tip").strip()
    if got != tip:
        raise LaunchRefused("the back bundle's tip is not athena's")
    expected = set(_git_out(scratch, "rev-list", "--objects", "--no-object-names", tip, "--not", head).split())
    before = _all_objects(records)
    if _all_objects(scratch) - before != expected - before:
        raise LaunchRefused("the back bundle carries objects the walk's commits do not reach; nothing is fetched")
    # The review's MAJOR 1 (15 Oct 2026): athena_suite's own scan_unpublished over the scratch clone at the tip, every
    # commit past the shipped head and NO allowance (no rulings, no ruled blobs, no ruled messages; the only allowed
    # blobs are the watcher's gzip evidence blobs, each decoded and scanned clean first: glitch-6b's ruling (b)): its
    # --ignore-gitleaks-allow, empty ignore file, remerge diffs, commit-message scan and binary-blob refusal.
    suite_mod = load_suite(suite) if suite_module is None else suite_module
    od57_bound(suite_mod)
    ruled = []          # OD57's admissions (od57_lines), recorded below as lines_ruled
    try:
        allow = admitted_evidence_blobs(suite_mod, scratch, head, tip, gitleaks, os.path.join(work, "blob-scan"))
        n = suite_mod.scan_unpublished(scratch, tip, os.path.join(work, "back-scan-work"), gitleaks, [head], None,
                                       allow, None, ruled, None)
    except Exception as e:  # noqa: BLE001 - athena_suite's Refused, a git or scanner failure: nothing is fetched
        # athena-made bytes (a path, a commit message) can sit in a foreign refusal's words: only this road's own
        # refusals, which name ids, counts and rules, are passed on; any other names its type alone.
        why = str(e) if isinstance(e, LaunchRefused) else f"{type(e).__name__} (its words are not echoed)"
        raise LaunchRefused(f"the return scan refused, nothing is fetched: {why}") from None
    if not isinstance(n, int) or n < 1:
        raise LaunchRefused("the return scan scanned no commit past the head; nothing is fetched")
    lines_ruled = od57_lines(ruled)
    name = os.path.basename(child)
    _ok(runner.local(["git", "-C", records, "fetch", "-q", "--no-tags", scratch, f"refs/walk/back:refs/heads/walk/{name}"]),
        "the records fetch")                                     # from the scanned scratch only, never the bundle
    # A defensive invariant (closure review of a3b09f02, NIT): the scratch check above already binds the scratch to
    # exactly the reachable set, and a fetch of one ref from it transfers no more, so no test can make this fire alone.
    if _all_objects(records) - before != expected - before:
        raise LaunchRefused(f"the records clone gained objects beyond the walk's commits (branch walk/{name} is "
                            f"left for a human)")
    return {"state": st, "fetched": tip, "branch": f"walk/{name}", "bundle_sha256": digest[0],
            "lines_ruled": lines_ruled}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="walk_launch.py")
    sub = ap.add_subparsers(dest="verb", required=True)
    s = sub.add_parser("ship")
    for k in ("repo", "ref", "suite", "reserve", "gitleaks", "work"):
        s.add_argument(f"--{k}", required=True)
    r = sub.add_parser("run")
    for k in ("child", "walk", "reason") + CELL:
        r.add_argument(f"--{k}", required=True)
    t = sub.add_parser("status")
    t.add_argument("--child", required=True)
    f = sub.add_parser("fetch")
    for k in ("child", "head", "ref", "records", "gitleaks", "work", "suite"):
        f.add_argument(f"--{k}", required=True)
    pr = sub.add_parser("probe")
    for k in ("child", "probe", "scenarios", "image", "reason"):
        pr.add_argument(f"--{k}", required=True)
    ph = sub.add_parser("probe-hooks")
    for k in ("child", "probe", "scenarios", "reason"):
        ph.add_argument(f"--{k}", required=True)
    ph.add_argument("--gemini-image")
    ph.add_argument("--codex-image")
    fp = sub.add_parser("fetch-probe")
    for k in ("child", "probe", "out", "gitleaks", "work"):
        fp.add_argument(f"--{k}", required=True)
    a = ap.parse_args(argv)
    runner = Runner()
    try:
        if a.verb == "ship":
            out = ship(runner, repo=a.repo, ref=a.ref, suite=a.suite, reserve=a.reserve, gitleaks=a.gitleaks,
                       work=a.work)
        elif a.verb == "run":
            out = {"pid": run(runner, child=a.child, walk=a.walk, cell={k: getattr(a, k) for k in CELL},
                              reason=a.reason)}
        elif a.verb == "status":
            out = {"state": status(runner, child=a.child)}
        elif a.verb == "probe":
            out = {"pid": probe(runner, child=a.child, probe_id=a.probe, scenarios=a.scenarios, image=a.image,
                                reason=a.reason)}
        elif a.verb == "probe-hooks":
            out = {"pid": probe_hooks(runner, child=a.child, probe_id=a.probe, scenarios=a.scenarios,
                                      gemini_image=a.gemini_image, codex_image=a.codex_image, reason=a.reason)}
        elif a.verb == "fetch-probe":
            out = fetch_probe(runner, child=a.child, probe_id=a.probe, out=a.out, gitleaks=a.gitleaks, work=a.work)
        else:
            out = fetch(runner, child=a.child, head=a.head, ref=a.ref, records=a.records, gitleaks=a.gitleaks,
                        work=a.work, suite=a.suite)
    except LaunchRefused as e:
        print(json.dumps({"refused": str(e)}))
        return 1
    print(json.dumps(out, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
