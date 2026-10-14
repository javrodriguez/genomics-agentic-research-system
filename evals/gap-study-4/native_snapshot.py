"""Live harness step 3c: retain each native session snapshot before the next resume.

A resumed Gemini CLI 0.64.0 session appends to one file (ChatRecordingService.initialize with resumedSessionData
keeps resumedSessionData.filePath), so what the session held after turn n exists only until turn n+1 writes. The
driver therefore copies it after turn n's quiescence and post-n snapshot, before turn n+1's exec.

Where the file is, from the pinned bundle chunk-J7SXW2FI.js (sha256 e2aca152...f206e; the box lane's
gemini-storage-source.json and gemini-native-session-source.json; lane-reports/native-snapshot-retention-2026-10-14.md):
  homedir()                 = $GEMINI_CLI_HOME when set
  Storage.getGlobalGeminiDir = <home>/.gemini
  getProjectTempDir          = <global temp dir>/<project identifier>   (the identifier is a registry short id)
  chatsDir                   = <project temp dir>/chats
  filename                   = session-<ISO minute, ':' -> '-'>-<first 8 of the sanitized session id>.jsonl,
                               or session-<minute>-<k>-<first 8>.jsonl on a collision; a subagent writes
                               <chats>/<parent id>/<id>.jsonl, which is never matched here.
Assumed, not source-shown (stated so the box lane can confirm): the global temp dir is <home>/.gemini/tmp
(TMP_DIR_NAME = "tmp"; getGlobalTempDir's body is not in the retained extracts) and SANDBOX is not "sandbox-exec"
(which would move the runtime dir to <home>/.cache/.gemini).

gemini_session_file reads directory names only, under exactly <home>/.gemini/tmp/*/chats, never a file's content and
never anything else in the home (no projects.json, no settings, no credentials). Every directory on the way must be a
real directory, the file a regular file; anything else, none, or more than one match refuses (SnapshotRefused).
retain copies the bytes (read without following a link; an empty file refuses, naming the turn) into
<take>/session/native-turn-<n>.jsonl, never overwriting,
and returns the {file, sha256} reference vendor_provenance.session_history_facts reads.
"""
from __future__ import annotations

import hashlib
import os
import re
import stat
from pathlib import Path


class SnapshotRefused(ValueError):
    """A native session snapshot cannot be located or retained as the source defines it."""


SESSION_DIR = "session"
_SESSION_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{7,}")
_MINUTE = r"\d{4}-\d{2}-\d{2}T\d{2}-\d{2}"


def _real_dir(path: Path) -> None:
    try:
        st = os.lstat(path)
    except OSError:
        raise SnapshotRefused(f"{path} does not exist") from None
    if not stat.S_ISDIR(st.st_mode):
        raise SnapshotRefused(f"{path} is not a real directory (a link or a file)")


def gemini_session_file(home, session_id) -> str:
    """The one session file Gemini CLI writes for session_id under GEMINI_CLI_HOME `home`."""
    if not isinstance(session_id, str) or not _SESSION_ID.fullmatch(session_id):
        raise SnapshotRefused("a native session is located only by the session id turn 1's init named")
    if not isinstance(home, str) or not home:
        raise SnapshotRefused("the GEMINI_CLI_HOME folder is not named")
    base = Path(home)
    for part in (base, base / ".gemini", base / ".gemini" / "tmp"):
        _real_dir(part)
    name = re.compile(rf"session-{_MINUTE}(?:-[1-9][0-9]*)?-{re.escape(session_id[:8])}\.jsonl")
    hits = []
    for project in sorted(os.listdir(base / ".gemini" / "tmp")):
        chats = base / ".gemini" / "tmp" / project / "chats"
        if not os.path.lexists(chats):
            continue
        _real_dir(base / ".gemini" / "tmp" / project)
        _real_dir(chats)
        for entry in sorted(os.listdir(chats)):
            if name.fullmatch(entry):
                hits.append(chats / entry)
    if len(hits) != 1:
        raise SnapshotRefused(f"{len(hits)} native session files carry the id's prefix {session_id[:8]}")
    if not stat.S_ISREG(os.lstat(hits[0]).st_mode):
        raise SnapshotRefused(f"{hits[0].name} is not a regular file")
    return str(hits[0])


# Codex slice 3: the rollout of a resumed `codex exec` session, under CODEX_HOME, which the box sets to the take's
# config mount (box/run_take.py TAKE_ENV[CODEX]: "CODEX_HOME": CONFIG_MOUNT), so the host reads it in the take's config
# folder. From the retained pinned source (audit Addendum B; rollout_file_name.rs blob 61ad43cd): the path is
# <home>/sessions/<year, unpadded>/<month, 2 digits>/<day, 2 digits>/rollout-<YYYY-MM-DDTHH-MM-SS>-<thread id>.jsonl
# (recorder.rs:1740-1762, SESSIONS_SUBDIR at lib.rs:86, RolloutFileName::render at rollout_file_name.rs:62-74). The
# folder date and the name's timestamp are LOCAL wall-clock time, so neither is compared with session_meta's UTC
# timestamp, and no time is read from the name. A reverted thread's ..._<rollout id>.jsonl and a compressed .jsonl.zst
# (written after 7 days; takes are retained per turn long before) are refused.
_CODEX_THREAD = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{0,127}")
_YEAR, _TWO = re.compile(r"[1-9]\d*"), re.compile(r"\d{2}")


def codex_rollout_file(home, thread_id) -> str:
    """The one rollout Codex writes for thread_id under CODEX_HOME `home`. A revert's renamed rollout, a compressed one
    (.jsonl.zst, written for rollouts older than 7 days), none or more than one refuses (SnapshotRefused)."""
    if not isinstance(thread_id, str) or not _CODEX_THREAD.fullmatch(thread_id):
        raise SnapshotRefused("a rollout is located only by the thread id turn 1's stream named")
    if not isinstance(home, str) or not home:
        raise SnapshotRefused("the CODEX_HOME folder is not named")
    base = Path(home) / "sessions"
    for part in (Path(home), base):
        _real_dir(part)
    name = re.compile(rf"rollout-\d{{4,}}-\d{{2}}-\d{{2}}T\d{{2}}-\d{{2}}-\d{{2}}-{re.escape(thread_id)}\.jsonl")
    other = re.compile(rf"rollout-.*{re.escape(thread_id)}(?:_[^/]*)?\.jsonl(?:\.zst)?")
    hits = []
    for year in sorted(os.listdir(base)):
        if not _YEAR.fullmatch(year):
            continue
        _real_dir(base / year)
        for month in sorted(os.listdir(base / year)):
            if not _TWO.fullmatch(month):
                continue
            _real_dir(base / year / month)
            for day in sorted(os.listdir(base / year / month)):
                if not _TWO.fullmatch(day):
                    continue
                folder = base / year / month / day
                _real_dir(folder)
                for entry in sorted(os.listdir(folder)):
                    if name.fullmatch(entry):
                        if not entry.startswith(f"rollout-{year.zfill(4)}-{month}-{day}T"):   # one local instant
                            raise SnapshotRefused(f"{entry} is not dated as its folder {year}/{month}/{day}")
                        hits.append(folder / entry)
                    elif other.fullmatch(entry):
                        raise SnapshotRefused(f"{entry} is a reverted or compressed rollout of the thread: refused")
    if len(hits) != 1:
        raise SnapshotRefused(f"{len(hits)} rollout files carry the thread id {thread_id}")
    if not stat.S_ISREG(os.lstat(hits[0]).st_mode):
        raise SnapshotRefused(f"{hits[0].name} is not a regular file")
    return str(hits[0])


def retain(take_folder, n, source) -> dict:
    """Copy turn n's native snapshot into <take_folder>/session/native-turn-<n>.jsonl; its {file, sha256}."""
    if type(n) is not int or n < 1:
        raise SnapshotRefused("a snapshot is numbered by its turn, a positive int")
    try:
        fd = os.open(source, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except OSError as exc:
        raise SnapshotRefused(f"the native session cannot be opened without following a link: {exc.strerror}") from None
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise SnapshotRefused("the native session is not a regular file")
        chunks = []
        while True:
            chunk = os.read(fd, 1 << 20)
            if not chunk:
                break
            chunks.append(chunk)
    finally:
        os.close(fd)
    raw = b"".join(chunks)
    if not raw:                                  # review nit N2: an empty session is never a snapshot of turn n
        raise SnapshotRefused(f"turn {n}: the native session file is empty")
    folder = Path(take_folder) / SESSION_DIR
    if os.path.lexists(folder):
        _real_dir(folder)
    else:
        folder.mkdir()
    name = f"native-turn-{n}.jsonl"
    try:
        out = os.open(folder / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    except FileExistsError:
        raise SnapshotRefused(f"{name} is already retained: a snapshot is never overwritten") from None
    with os.fdopen(out, "wb") as fh:
        fh.write(raw)
    return {"file": name, "sha256": hashlib.sha256(raw).hexdigest()}
