#!/usr/bin/env python3
"""What this study copied from round 3, from which commit, and what it changed -- assembled from one fragment per lane.

    python3 evals/gap-study-4/copy_manifest.py --check     assemble COPIED.d/*.json, re-derive every entry; exit 1 on any problem
    python3 evals/gap-study-4/copy_manifest.py --derive    print the assembled record (what the freeze writes as COPIED.json)
    python3 evals/gap-study-4/copy_manifest.py --later-files [REV]    after the freeze: refuse a file added under this folder
                                                                      that is no run output (later_files_problems)

ROUND 4'S SHAPE. Round 3's manifest compared one committed COPIED.json with what the files derived, so every
lane that added a file would have rewritten that same file. Here each build lane writes its own fragment,
COPIED.d/<lane id>.json:

    {"lane": "<lane id>", "files": [{"path": "<path under evals/gap-study-4/>",
                                      "status": "identical" | "edited" | "new",
                                      "source": "<repo path at the source commit, for identical and edited>",
                                      "reason": "<required for edited and new>"}]}

`--check` assembles the fragments and compares with NOTHING committed: during the build COPIED.json does not
exist, and the freeze writes it once from derive(). What --check refuses:

  - a fragment that is not that shape, or whose `lane` is not its own file name;
  - a path claimed by two fragments (or twice by one);
  - a file under this folder that no fragment claims, or a claimed file that does not exist;
  - an `identical` copy whose bytes differ from its source blob at the source commit, or that carries a reason;
  - an `edited` copy that is byte-identical to its source, or that carries no reason;
  - a `new` file that carries a source or no reason, or that is byte-identical to the round 3 file at the same
    path (that is a copy and says so);
  - an edit to any copied fixture builder (UNEDITABLE): the fixtures round 3 ran are rebuilt exactly as it ran
    them, and new fixtures are new files;
  - any change to the frozen rounds, the shared graders and fixtures, the shared transcript parser or the
    pre-study since BASE_COMMIT, in a commit or in the working tree;
  - (review W1A-1, home fold) a source outside ALLOWED_SOURCES, or any source that is one of round 3's records
    (ROUND3_RECORDS): its pre-registration, ledgers, results, transcripts, graders, battery and review records
    are round 3's, never copied;
  - (W1A-1) a `new` file whose bytes are any blob under evals/ at the source or the base commit, at any path;
  - (W1A-3) a tracked cache file (`*.pyc`, `__pycache__/`), which a fragment could never claim and a sourceless
    .pyc imports; and a symbolic link anywhere under this folder;
  - (N2) a reason that is not a non-empty string;
  - (review round 2) any file whose bytes are a round 3 record at the source or base commit, whatever its
    status; an `edited` copy whose bytes are already a file under evals/ (it is an `identical` copy of that file);
    and any copy of the first study's three named fixture builders that is not `identical`;
  - (pre-freeze review 1, m8, lane pf1-l1-freeze-gates) an `edited` copy that is a near-rewrite, more than
    NEAR_REWRITE_SHARE of its lines changed from its source (difflib's matching lines over the longer side), whose
    reason cites no commit, or any hex token that is not a commit in HEAD's history that changed the file after its
    copy commit (citation_problem; the review of 53d0e9af, finding 3, and its closure check, finding 2): a short
    reason over a rewritten file no longer passes, nor a bare date, a made-up hash or a commit that edited something
    else. What it cannot see: whether the cited commits explain every line; that stays the reviews' job.

RECORDS ARE CLAIMED BY THEIR OWN LEDGERS, NOT BY FRAGMENTS (lane w8a, ruling W8-layout-1, README Q4; this file moved
from lane w1a to lane w8a under ruling W8A-gap4-1). A file inside a walk folder, rehearsals/<walk>/**, is claimed
exactly when rehearsals/register.json lists <walk>; a file inside a take folder, takes/<slot>/<k>/**, exactly when
outcomes.json names that slot and attempt (CP7; none today). An unlisted record folder's files are unclaimed and
fail, and a fragment that claims a path inside a record folder is refused: a record is never a build file. The
folder names are mode_binding's. rehearsals/README.md and rehearsals/register.json stay fragment-claimed.

What --check cannot see (review round 2 W1A2-6): a record changed by even one byte is a new blob, so a derivative
of a record (a record plus a line, a record re-wrapped) passes these byte guards. So does an older version of a
record (review round 3 W1A3-5): the guards read the record blobs at the source and the base commit only, so a
record's exact bytes as they stood at an earlier commit pass. Keeping records out in that sense is the reviews'
job, not this check's.

What a reason says is not bound to the edit it describes (pre-freeze review 2, m14, named by lane fold2/lc): a
reason holding any citation token passes, so a reason can be stubbed, or say "No other line changed" of a file a
later lane edited (COPIED.d/w7d-rehearsals.json said so of review_kit/rounds.py until lane fold2/lc corrected it).
Every byte of every file is still pinned, by its blob and the guards above, so only the description is loose;
reading a reason against its diff stays the reviews' job.

A tree named as a source (round 3 W1A3-7, recorded, not fixed): `git show <commit>:<folder>` prints the folder's
listing, and a record folder named without its trailing slash is not matched as a record, so a listing of
record NAMES (never their content) can be copied as `identical`.

Round 3's uneditable list (check_take.py, the graders, the label reader, lint_language.py, commit_msg.py) is
NOT carried: round 4 edits its checker and writes new graders, and the copied list would refuse both.

Every source is read with `git show`, never from a working tree: round 3's files at its done commit, and the
shared files the plan names as copy sources at the base commit (lane E1's intervals landed after round 3).

No model, no network, stdlib only.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
FRAGMENTS = HERE / "COPIED.d"
sys.path.insert(0, str(HERE))

import mode_binding  # noqa: E402
import study  # noqa: E402

# Round 3's done commit: every copy is read from here.
SOURCE_COMMIT = "e2979b3143081824aadea73523ec41af30c1ddb1"
SOURCE_DIR = "evals/gap-study-3"
# The commit round 4 was cut from. Everything below is unchanged since it, so nothing here can have been edited there.
BASE_COMMIT = "68ec902f63bfbe4a18d07e0f564847531898ff95"
# Where the shared copy sources are read (review round 2 NIT): a constant of its own, so moving the pin baseline
# can never silently redefine "identical" for a shared builder. A test binds that each shared file here equals
# round 3's at SOURCE_COMMIT wherever both exist.
SHARED_COMMIT = "68ec902f63bfbe4a18d07e0f564847531898ff95"
PINNED_UNCHANGED = ("evals/gap-study", "evals/gap-study-2", "evals/gap-study-3", "evals/graders",
                    "evals/fixtures", "evals/transcript.py", "evals/haiku-prestudy", "evals/gap-study-intervals")

STATUSES = ("identical", "edited", "new")
ENTRY_KEYS = {"path", "status", "source", "reason"}
# Live harness (glitch-06's ruling, 14 Oct 2026): native-readers/ holds acceptance records and their reviews, written only
# by Javier's acceptance commit, so it is claimed once, in advance, by one pattern entry of its own status; it claims
# only <harness>-acceptance.json and <harness>-review.md for a vendor harness, and nothing else under that folder.
READER_RECORDS = "native-readers/**"
READER_RECORDS_STATUS = "acceptance-records"
READER_RECORD = re.compile(r"native-readers/(?:gemini|codex)-(?:acceptance\.json|review\.md)")

# The copied fixture builders: uneditable. Each must be claimed, as `identical`, from its round 3 path.
UNEDITABLE = ("fixtures/check_fixture.py", "fixtures/copy_project.py", "fixtures/gen_project.py",
              "fixtures/gen_source.py", "fixtures/symbol_rulings.json")

# Never part of a fragment: caches the interpreter may leave behind ON DISK. A tracked one is refused (W1A-3).
IGNORED_PARTS = ("__pycache__",)
IGNORED_SUFFIXES = (".pyc",)

# Where a copy may come from (review W1A-1): round 3's folder, and the shared files the round 4 plan names as
# copy sources (the first study's fixture builders and classifier, lane E1's interval code). Anything else is
# refused rather than allowed by default.
ALLOWED_SOURCES = ("evals/gap-study-3/", "evals/fixtures/gen_fastq.py", "evals/fixtures/neutralise.py",
                   "evals/fixtures/rank_check.py", "evals/graders/confounded_refusal.py",
                   "evals/gap-study-intervals/intervals.py")
# The first study's fixture builders the plan names (review round 2 W1A2-4): copied byte-identical, as `identical`
# only, so the copies stay exactly as the earlier rounds ran them. The rest of evals/fixtures/ (its pilot record,
# its planted answer keys) is no copy source at all.
SHARED_UNEDITABLE = ("evals/fixtures/gen_fastq.py", "evals/fixtures/neutralise.py", "evals/fixtures/rank_check.py")
# Round 3's records, never copied whatever the status (W1A-1; the lane's own exclusions, made a check).
ROUND3_RECORDS = tuple(f"{SOURCE_DIR}/{r}" for r in (
    "prereg.json", "prereg-draft.json", "takes.json", "COPIED.json", "RESULT.md", "COSTS.md", "PROGRESS.md",
    "test_round3.py", "results/", "transcripts/", "rehearsals/", "pauses/", "walks/", "verification/", "cases/",
    "graders/", "review_kit/rounds.json", "review_kit/prefreeze-"))
# Pre-freeze review 1, m8: the registered changed-line share above which an edited copy is a near-rewrite, whose reason
# must cite a commit that edited it (citation_problem).
NEAR_REWRITE_SHARE = 0.5
# The empty blob is every empty file; an empty new file copies nothing.
EMPTY_BLOB = "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True)


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def source_commit(src: str) -> str:
    """Round 3's files are read at its done commit; the shared files the plan names (some landed after it, such
    as lane E1's intervals) are read at SHARED_COMMIT, where PINNED_UNCHANGED holds them still."""
    return SOURCE_COMMIT if src.startswith(SOURCE_DIR + "/") else SHARED_COMMIT


def source_bytes(src: str) -> bytes | None:
    shown = git("show", f"{source_commit(src)}:{src}")
    return shown.stdout if shown.returncode == 0 else None


def is_cache(rel: str) -> bool:
    return any(part in IGNORED_PARTS for part in rel.split("/")) or rel.endswith(IGNORED_SUFFIXES)


def files_here() -> set[str]:
    """Every file under this folder, on disk or in the index, as a path relative to this folder. Untracked caches
    on disk are left out; a TRACKED cache is kept, so the check refuses it (W1A-3)."""
    out = set()
    for p in HERE.rglob("*"):
        rel = p.relative_to(HERE).as_posix()
        if (p.is_file() or p.is_symlink()) and not is_cache(rel):
            out.add(rel)
    out |= tracked_here()
    return out


def files_of_the_record() -> set[str]:
    """What the copy record answers for. Lane fold11/freeze-recheck (its gate review 3, M1): under w5b-4 the run's outputs have
    no fragment, so once a frozen file is committed only the files of its introducing commit are read, as ci.yml's Copy
    record step reads them; before that commit, everything here."""
    rel = study.rel("prereg.json")
    log = git("log", "--reverse", "--format=%H", "--", rel).stdout.decode().split() if (HERE / "prereg.json").is_file() else []
    if not log:
        return files_here()
    listed = git("ls-tree", "-r", "-z", "--name-only", log[0], "--", study.STUDY_REL).stdout.decode().split("\0")
    return files_here() & {name[len(study.STUDY_REL) + 1:] for name in listed if name}


def tracked_here() -> set[str]:
    listed = git("ls-files", "-z", "--", study.STUDY_REL)
    return {name[len(study.STUDY_REL) + 1:] for name in listed.stdout.decode().split("\0") if name}


def blob_id(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


_PRIOR_BLOBS: set[str] | None = None


class ManifestError(Exception):
    """The check could not read what it needs; it fails, never passes on an empty read (review round 3 W1A3-6)."""


def listed_blobs(commit: str, prefix: str) -> list[tuple[str, str]]:
    """(blob id, path) for every blob under `prefix` at `commit`; raises when git cannot list it."""
    listed = git("ls-tree", "-r", "-z", commit, "--", prefix)
    if listed.returncode != 0:
        raise ManifestError(f"cannot list {prefix} at {commit[:12]}: git ls-tree exited {listed.returncode}")
    out = []
    for entry in listed.stdout.decode().split("\0"):
        if entry:
            meta, path = entry.split("\t", 1)
            out.append((meta.split()[2], path))
    return out


def prior_blobs() -> set[str]:
    """Every blob under evals/ (round 4's own folder left out) at the source commit and the base commit."""
    global _PRIOR_BLOBS
    if _PRIOR_BLOBS is None:
        blobs = set()
        for commit in (SOURCE_COMMIT, BASE_COMMIT):
            blobs |= {b for b, path in listed_blobs(commit, "evals/") if not path.startswith(study.STUDY_REL + "/")}
        if not blobs - {EMPTY_BLOB}:
            raise ManifestError("cannot list evals/: git listed no file at the source or the base commit")
        _PRIOR_BLOBS = blobs - {EMPTY_BLOB}
    return _PRIOR_BLOBS


_RECORD_BLOBS: set[str] | None = None


def record_blobs() -> set[str]:
    """Every blob at a ROUND3_RECORDS path, at the source and the base commit (review round 2 W1A2-1)."""
    global _RECORD_BLOBS
    if _RECORD_BLOBS is None:
        blobs = set()
        for commit in (SOURCE_COMMIT, BASE_COMMIT):
            found = {b for b, path in listed_blobs(commit, SOURCE_DIR + "/") if is_record(path)}
            if not found:
                raise ManifestError(f"cannot list round 3's records: none found at {commit[:12]}")
            blobs |= found
        _RECORD_BLOBS = blobs - {EMPTY_BLOB}
    return _RECORD_BLOBS


def changed_share(orig: bytes, copy: bytes) -> float:
    """The share of lines an edit changed: 1 less difflib's matching lines over the longer side's line count."""
    import difflib
    a = orig.decode("utf-8", errors="replace").splitlines()
    b = copy.decode("utf-8", errors="replace").splitlines()
    kept = sum(m.size for m in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks())
    return 1 - kept / max(len(a), len(b), 1)


COMMIT_TOKEN = re.compile(r"(?<![0-9a-f])[0-9a-f]{8,40}(?![0-9a-f])")


# The citation sentence lane pf1-l1-freeze-gates appends to each near-rewrite's reason (m8): the strict rule reads
# the tokens inside it; every other hex token in a reason is its owner's prose (the second closure check of 2971d1d7,
# minor 2) and needs only to be a commit in HEAD's history.
CITATION_MARK = " Pre-freeze review 1, m8 (lane pf1-l1-freeze-gates"


def citation_problem(path: str, why: str) -> str | None:
    """Why a near-rewrite's reason does not cite the commits that edited it, or None (the review of 53d0e9af, finding
    3, its closure check, finding 2, and the second closure check, minor 2). The reason must carry this lane's
    citation sentence (CITATION_MARK), and every 8-to-40 hex token inside it must be a commit in HEAD's history that
    changed this file after its copy commit (the first commit in its history): a bare date, a hash that names nothing,
    a commit on another branch, the copy commit or a commit that never touched the file each refuse, and one good
    citation never covers a bad one. Every hex token elsewhere in the reason must be a commit in HEAD's history."""
    why = why or ""
    head, mark, sentence = why.partition(CITATION_MARK)
    strict = COMMIT_TOKEN.findall(sentence) if mark else []
    if not strict:
        return "its reason carries no citation sentence naming a commit that edited it"
    listed = git("log", "--full-history", "--format=%H", "--", study.rel(path))
    history = listed.stdout.decode().split() if listed.returncode == 0 else []
    edits = set(history[:-1])            # newest first; the last is the copy commit
    for t, must_edit in [(t, False) for t in COMMIT_TOKEN.findall(head)] + [(t, True) for t in strict]:
        got = git("rev-parse", "--verify", "--quiet", f"{t}^{{commit}}")
        if got.returncode != 0:
            return f"its reason cites {t}, which resolves to no commit"
        full = got.stdout.decode().strip()
        if git("merge-base", "--is-ancestor", full, "HEAD").returncode != 0:
            return f"its reason cites {t}, a commit outside HEAD's history"
        if must_edit and full not in edits:
            return f"its reason cites {t}, which did not change it after its copy commit"
    return None


def is_record(src: str) -> bool:
    return any(src == r or (r.endswith(("/", "-")) and src.startswith(r)) for r in ROUND3_RECORDS)


def is_link(name: str) -> bool:
    return (HERE / name).is_symlink()


def source_problem(src: str) -> str | None:
    if not any(src == a or (a.endswith("/") and src.startswith(a)) for a in ALLOWED_SOURCES):
        return f"its source {src} is not an allowed copy source ({', '.join(ALLOWED_SOURCES)})"
    if is_record(src):
        return f"its source {src} is one of round 3's records, which are never copied"
    return None


def load_fragments(folder: Path = FRAGMENTS) -> tuple[list[tuple[str, dict]], list[str]]:
    """(lane, entry) for every entry of every fragment, and the shape problems found reading them."""
    entries, out = [], []
    if not folder.is_dir():
        return entries, [f"no {folder.name}/ folder: no lane has recorded its files"]
    for frag in sorted(folder.glob("*.json")):
        try:
            rec = json.loads(frag.read_text())
        except (OSError, ValueError) as e:
            out.append(f"{frag.name} is not JSON: {e}")
            continue
        if not isinstance(rec, dict) or set(rec) != {"lane", "files"} or not isinstance(rec["files"], list):
            out.append(f"{frag.name} is not {{\"lane\": ..., \"files\": [...]}}")
            continue
        if rec["lane"] != frag.stem:
            out.append(f"{frag.name} names lane {rec['lane']!r}; a fragment's lane is its file name")
        for e in rec["files"]:
            if not isinstance(e, dict) or not {"path", "status"} <= set(e) or not set(e) <= ENTRY_KEYS:
                out.append(f"{frag.name}: entry {e!r} is not {{path, status, source?, reason?}}")
                continue
            entries.append((frag.stem, e))
    return entries, out


def derive(folder: Path = FRAGMENTS) -> dict:
    """The assembled record, with each copy's source blob and both hashes. What the freeze writes as COPIED.json."""
    entries, _ = load_fragments(folder)
    files = []
    for lane, e in sorted(entries, key=lambda le: le[1]["path"]):
        p = HERE / e["path"]
        row = {"path": study.rel(e["path"]), "lane": lane, "status": e["status"],
               "source": e.get("source"), "reason": e.get("reason"),
               "copy_sha256": sha256(p.read_bytes()) if p.is_file() else None}
        if e.get("source"):
            src = source_bytes(e["source"])
            row["source_commit"] = source_commit(e["source"])
            row["source_blob"] = git("rev-parse", f"{row['source_commit']}:{e['source']}").stdout.decode().strip() or None
            row["source_sha256"] = sha256(src) if src is not None else None
        files.append(row)
    return {"role": "Every file of this study, per build lane: copied from round 3's done commit (identical or edited "
                    "with a reason) or new, assembled from COPIED.d/.",
            "source_commit": git("rev-parse", SOURCE_COMMIT).stdout.decode().strip(),
            "base_commit": BASE_COMMIT, "files": files}


def read_copy(path: str) -> bytes:
    return (HERE / path).read_bytes()


def committed_records(base: Path = HERE) -> dict:
    """W8A: what the records' own ledgers claim: {"walks": the walk ids rehearsals/register.json lists, "takes": the
    (slot, attempt) pairs outcomes.json names, the attempt as its folder's name}. An unreadable ledger claims nothing,
    so its records fail as unclaimed (walk_register --check names the register's own problem)."""
    import walk_register
    walks = {e["walk"] for e in walk_register.registered(Path(base) / mode_binding.WALKS_DIR)}
    takes = set()
    try:
        history = json.loads((Path(base) / "outcomes.json").read_text())
    except (OSError, ValueError):
        history = []
    for o in history if isinstance(history, list) else []:
        if isinstance(o, dict) and isinstance(o.get("slot"), str) and type(o.get("attempt")) is int:
            takes.add((o["slot"], str(o["attempt"])))
    return {"walks": walks, "takes": takes}


def record_root_of(path: str) -> str | None:
    """The record root when `path` (relative to this folder) is a file inside a record folder, else None."""
    got = mode_binding.record_parts(path.split("/"))
    return got[0] if got is not None and got[1] == 0 else None


def record_claims(present: set[str], records: dict) -> set[str]:
    """W8A: the present files a record ledger claims: rehearsals/<walk>/** when the register lists <walk>,
    takes/<slot>/<k>/** when the outcomes name (slot, k)."""
    out = set()
    for name in present:
        root = record_root_of(name)
        parts = name.split("/")
        if root == mode_binding.WALKS_DIR and parts[1] in records["walks"]:
            out.add(name)
        elif root == mode_binding.TAKES_DIR and (parts[1], parts[2]) in records["takes"]:
            out.add(name)
    return out


def problems(folder: Path = FRAGMENTS, present: set[str] | None = None, read=read_copy,
             pinned: bool = True, records: dict | None = None) -> list[str]:
    """Every problem with the assembled fragments. `present` and `read` stand in for the folder (tests mutate them);
    `records` for committed_records() (W8A)."""
    entries, out = load_fragments(folder)
    try:
        record_blobs()
        prior_blobs()
    except ManifestError as e:   # the byte guards cannot read: the check fails, it never runs them empty
        return out + [str(e)]
    present = files_of_the_record() if present is None else present
    claimed: dict[str, str] = {}
    for lane, e in entries:
        path, status, src, why = e["path"], e["status"], e.get("source"), e.get("reason")
        if status == READER_RECORDS_STATUS or path.startswith("native-readers/"):     # live harness, 14 Oct 2026
            if path != READER_RECORDS or status != READER_RECORDS_STATUS or src is not None or not (
                    isinstance(why, str) and why.strip()):
                out.append(f"{path} ({lane}): native-readers/ is claimed only by one {READER_RECORDS!r} entry of "
                           f"status {READER_RECORDS_STATUS!r} with a reason")
            elif READER_RECORDS in claimed:
                out.append(f"{READER_RECORDS} is claimed by {claimed[READER_RECORDS]} and again by {lane}")
            else:
                claimed[READER_RECORDS] = lane
            continue
        if record_root_of(path) is not None:            # W8A: a record is claimed by its ledger, never a fragment
            out.append(f"{path} ({lane}) is inside a record folder; a record is claimed by its register or outcomes "
                       f"ledger, never by a fragment")
            continue
        if path in claimed:
            out.append(f"{path} is claimed by {claimed[path]} and again by {lane}; a file has one owner")
            continue
        claimed[path] = lane
        if why is not None and (not isinstance(why, str) or not why.strip()):
            out.append(f"{path} ({lane}): its reason is not a non-empty string")
            why = None
        if is_cache(path):
            out.append(f"{path} ({lane}) is an interpreter cache; caches are never part of the study")
        if status not in STATUSES:
            out.append(f"{path} ({lane}): status {status!r} is not one of {', '.join(STATUSES)}")
            continue
        if path not in present:
            out.append(f"{path} ({lane}) is claimed but does not exist")
            continue
        copy = read(path)
        if blob_id(copy) in record_blobs():
            out.append(f"{path} ({lane}): its bytes are one of round 3's records, which are never copied")
            continue
        if status == "new":
            if src:
                out.append(f"{path} ({lane}) is new and names a source; a copy is identical or edited")
            if not why:
                out.append(f"{path} ({lane}) is new and carries no reason")
            same = source_bytes(f"{SOURCE_DIR}/{path}")
            if same is not None and same == copy:
                out.append(f"{path} ({lane}) is recorded as new but is byte-identical to {SOURCE_DIR}/{path} at "
                           f"{SOURCE_COMMIT}; it is a copy and must say so")
            elif blob_id(copy) in prior_blobs():
                out.append(f"{path} ({lane}) is recorded as new but its bytes are a file under evals/ at "
                           f"{SOURCE_COMMIT} or {BASE_COMMIT[:12]}; it is a copy and must say so")
            if path in UNEDITABLE:
                out.append(f"{path} ({lane}) is a copied fixture builder recorded as new")
            continue
        if not src:
            out.append(f"{path} ({lane}) is {status} and names no source")
            continue
        bad_source = source_problem(src)
        if bad_source:
            out.append(f"{path} ({lane}): {bad_source}")
            continue
        orig = source_bytes(src)
        if orig is None:
            out.append(f"{path} ({lane}): its source {src} does not exist at {source_commit(src)}")
            continue
        differs = orig != copy
        if status == "identical" and differs:
            out.append(f"{path} ({lane}) differs from {src} at {source_commit(src)} and has no `edited` entry")
        if status == "identical" and why:
            out.append(f"{path} ({lane}) is identical and carries a reason; a reason is for an edit or a new file")
        if status == "edited" and not differs:
            out.append(f"{path} ({lane}) carries an edit reason but is byte-identical to {src}")
        if status == "edited" and blob_id(copy) in prior_blobs():
            out.append(f"{path} ({lane}) is recorded as edited but its bytes are a file under evals/; record it "
                       f"identical from that file")
        if src in SHARED_UNEDITABLE and (differs or status != "identical"):
            out.append(f"{path} ({lane}) copies the shared builder {src}, which is uneditable: identical only")
        if status == "edited" and not why:
            out.append(f"{path} ({lane}) differs from {src} and no reason is recorded")
        elif status == "edited" and differs:
            share = changed_share(orig, copy)
            if share > NEAR_REWRITE_SHARE:
                problem = citation_problem(path, why)
                if problem:
                    out.append(f"{path} ({lane}) is a near-rewrite of {src} ({share:.0%} of its lines changed, above "
                               f"{NEAR_REWRITE_SHARE:.0%}) and {problem}")
        if path in UNEDITABLE and (differs or status != "identical"):
            out.append(f"{path} ({lane}) is a copied fixture builder and differs from {src}, or is recorded as "
                       f"edited; that is a FAIL, not a manifest entry")
        if path in UNEDITABLE and src != f"{SOURCE_DIR}/{path}":
            out.append(f"{path} ({lane}) is a copied fixture builder whose source is {src}, not {SOURCE_DIR}/{path}")
    by_record = record_claims(present, committed_records() if records is None else records)
    by_reader = {n for n in present if READER_RECORD.fullmatch(n)} if READER_RECORDS in claimed else set()
    for name in sorted(present - set(claimed) - by_record - by_reader):
        out.append(f"{name} is under {study.STUDY_REL}/ and no fragment in {folder.name}/ claims it")
    for name in sorted(n for n in present if is_cache(n)):
        if name not in claimed:
            out.append(f"{name} is a tracked interpreter cache under {study.STUDY_REL}/; caches are never tracked")
    for name in sorted(present):
        if is_link(name):
            out.append(f"{name} is a symbolic link; every file of the study is a regular file")
    for name in UNEDITABLE:
        if name not in claimed:
            out.append(f"{name}, a copied fixture builder, is not claimed by any fragment")
    for p in (PINNED_UNCHANGED if pinned else ()):
        if git("diff", "--quiet", BASE_COMMIT, "HEAD", "--", p).returncode != 0:
            out.append(f"{p} has changed since {BASE_COMMIT[:12]}; a frozen round or shared file was edited")
        elif git("diff", "--quiet", BASE_COMMIT, "--", p).returncode != 0:
            out.append(f"{p} differs from {BASE_COMMIT[:12]} in the working tree")
    return out


# Fold 13, A3 (the post-run triage's probe: a fractions.py committed in this folder after the freeze ran inside
# check_results.py --ledger and passed every check). check_pins reads pinned paths and files_of_the_record the freeze commit's,
# so nothing read a file ADDED later, and this folder is first on sys.path. The paths a real run writes that
# check_results.RUNTIME_PATHS does not name (they may exist with the freeze, so its timing rule cannot hold them):
# run_builders' spend and trim ledger (its RUN_LEDGER_NAME; arms O and G's money gate reads it, so the counted run commits it),
# Javier's labelling inputs, the drawn samples and the agreement page; a take's own folder is read by record_root_of below.
LATER_RUN_FILES = ("run-ledger.json", "labelling/definitions.json", "labelling/labels.json", "labelling/AGREEMENT.md", "labelling/sample.json",
                   "labelling/sample-followup.json")


def runtime_paths() -> tuple:
    """check_results.RUNTIME_PATHS read from its source, never imported: importing it runs stats' `from fractions import`
    from this folder, so the very file the probe committed would have run inside its own refusal."""
    for node in ast.parse((HERE / "check_results.py").read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and [getattr(t, "id", None) for t in node.targets] == ["RUNTIME_PATHS"]:
            return ast.literal_eval(node.value)
    raise ManifestError("check_results.py names no RUNTIME_PATHS, so what a run writes cannot be read")


def is_run_output(name: str) -> bool:
    """A path a real run or a verifier writes: check_results' runtime paths, verification/, a take's record folder."""
    written = (*runtime_paths(), *LATER_RUN_FILES, study.VERIFY_DIR)
    return record_root_of(name) == mode_binding.TAKES_DIR or any(name == p or name.startswith(p + "/") for p in written)


def later_files_problems(rev: str | None = None) -> list[str] | None:
    """Every path under this folder that the freeze commit does not hold and no run writes, or None before the freeze: at
    `rev`, in any commit between the freeze and `rev` (a file added, used and deleted was still there), and, with no `rev`,
    on disk. CI gives `rev` and runs the freeze commit's copy of this file, so a file added later cannot shadow what reads it."""
    log = git("log", "--reverse", "--format=%H", "--", study.rel("prereg.json")).stdout.decode().split()
    if not log or not (HERE / "prereg.json").is_file():
        return None
    frozen, tip = log[0], rev or "HEAD"
    if git("merge-base", "--is-ancestor", frozen, tip).returncode != 0:
        raise ManifestError(f"{tip} does not descend from the freeze commit {frozen[:12]}, so what it added cannot be read")

    def names(*args: str) -> set[str]:
        got = git(*args, "--", study.STUDY_REL)
        if got.returncode != 0:
            raise ManifestError(f"cannot read git {args[0]} at {tip}: git exited {got.returncode}")
        listed = got.stdout.decode("utf-8", "surrogateescape").split("\0")
        return {name.strip("\n")[len(study.STUDY_REL) + 1:] for name in listed if name.strip("\n")}

    at_freeze = names("ls-tree", "-r", "-z", "--name-only", frozen)
    later = names("ls-tree", "-r", "-z", "--name-only", tip) | names(
        "log", "--full-history", "-m", "--no-renames", "--diff-filter=A", "--format=", "--name-only", "-z", f"{frozen}..{tip}")
    if rev is None:
        later |= files_here()
    return [f"{name} is under {study.STUDY_REL}/, the freeze commit {frozen[:12]} does not hold it and no run writes it"
            for name in sorted(later - at_freeze) if not is_run_output(name)]


def later_files_main(rev: str | None) -> int:
    try:
        bad = later_files_problems(rev)
    except ManifestError as e:
        print(f"FAIL {e}")
        return 1
    if bad is None:
        print("later files: not applicable, not frozen")
        return 0
    for b in bad:
        print(f"FAIL {b}")
    if not bad:
        print(f"later files: ok, every file added since the freeze commit is a run output ({rev or 'HEAD and this disk'})")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--derive", action="store_true")
    g.add_argument("--later-files", nargs="?", const="", metavar="REV")
    args = ap.parse_args()
    if args.later_files is not None:
        return later_files_main(args.later_files or None)
    for commit in (SOURCE_COMMIT, BASE_COMMIT, SHARED_COMMIT):
        if git("cat-file", "-e", f"{commit}^{{commit}}").returncode != 0:
            print(f"FAIL commit {commit} is not in this clone (git fetch --unshallow)")
            return 1
    bad = problems()
    if args.derive:
        # the record the freeze writes is derived only from a manifest that checks clean (review N9)
        if bad:
            for b in bad:
                print(f"FAIL {b}")
            return 1
        print(json.dumps(derive(), indent=2))
        return 0
    for b in bad:
        print(f"FAIL {b}")
    if not bad:
        entries, _ = load_fragments()
        count = {s: sum(e["status"] == s for _, e in entries) for s in STATUSES}
        lanes = sorted({lane for lane, _ in entries})
        files = sum(e["status"] in STATUSES for _, e in entries)
        readers = sorted(n for n in files_here() if READER_RECORD.fullmatch(n))
        print(f"ok: {files} files from {len(lanes)} fragment(s) ({', '.join(lanes)}) and the {READER_RECORDS} "
              f"pattern claiming {len(readers)} acceptance record(s) or review(s): "
              f"{count['identical']} identical and {count['edited']} edited (round 3 at {SOURCE_COMMIT[:8]}, "
              f"shared files at {SHARED_COMMIT[:8]}), "
              f"{count['new']} new; {len(UNEDITABLE)} fixture builders byte-identical; "
              f"{len(PINNED_UNCHANGED)} frozen paths unchanged since {BASE_COMMIT[:12]}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
