"""Live harness: the Gemini native-reader registration road, built so that only real evidence is missing.

A native-session reader enters production only through a committed acceptance record, read by production_readers().
Without the record the registry stays empty, every Gemini take stays NativeCrossCheckPending (drive.py), and nothing
here changes that. The record is never written by this module or by any test.

Registration review (finding 1, MAJOR: the first road was self-certifying, since anyone able to write the working tree
could assert every field). Now:
  * every bound input (the record, the rehearsals register, the walk folder, the review, READER_SOURCES) is read from
    the committed tree (git show HEAD), and any difference between the working tree and HEAD for a bound path refuses;
  * the walk must pass drive.walk_files (on its committed bytes) and be exactly one WalkRepo commit (subject
    drive.WALK_SUBJECT) touching its folder; the native snapshot and the streams the record names must be the ones
    that walk's own driver ledger names (the last native_snapshots ref, and its streams), byte for byte;
  * the evidence label is derived from those bindings (RECORDED), never asserted: a record carrying one refuses;
  * a synthetic marker (case-insensitive "synthetic") in the native session metadata, the register entry, the review
    or the record refuses; this gate runs last, so no labelled synthetic fixture can ever register;
  * the acceptor is "javier" and the reviewer is a different principal.
These are local, unsigned git records: anyone able to commit can write them. The final guarantee is procedural (the
acceptance commit is made in Javier's own window); a hook-gated acceptance door is a named follow-up, not built here.

join_session() is the one function both the acceptance check (check_session) and the production cross-check
(drive.gemini_cross_check) call: each turn's host-captured stream joined to that interaction of a native snapshot by
gemini_stream_join.join, an extra native interaction refused, an incomplete interaction refused. Acceptance adds a
coverage floor (ACCEPTANCE_FLOOR: at least two interactions, so a resume and the snapshot-history join are exercised,
and at least one tool round trip) and re-derives the history join over every snapshot the walk's ledger names.

The acceptance record (ACCEPTANCE_FILE, beside this module; closed keys ACCEPTANCE_KEYS) binds:
  reader_sources_sha256  reader_sources_sha256() over READER_SOURCES at HEAD: any later edit of the reader, of the
                         driver's cross-check or of vendor_provenance unregisters it until a new record is committed;
  cli_version            PINNED_CLI;
  walk                   one arm-G walk of the committed rehearsals register;
  native, streams        {file, sha256}, equal to the walk's driver-ledger refs and re-hashed on the committed bytes;
  join                   {"status": "PASS", "interactions": n}, re-derived here;
  review                 {"verdict": "PASS", "file", "sha256", "reviewer"}, re-hashed on the committed bytes;
  accepted_by            "javier".
Any mismatch refuses (RegistrationRefused): a record that cannot be trusted stops the reader from loading, never
falls back to a silent empty registry.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import gemini_projection as gp  # noqa: E402
import gemini_session_replay as replay_mod  # noqa: E402
import gemini_stream_join as gsj  # noqa: E402
import mode_binding  # noqa: E402
import vendor_provenance as vp  # noqa: E402
import walk_register  # noqa: E402


class RegistrationRefused(ValueError):
    """The acceptance record cannot be trusted; the reader is not registered."""


PINNED_CLI = "0.64.0"
HARNESS = "gemini"
ARM = "G"
RECORDED = "recorded-walk"          # derived, never read from the record
ACCEPTOR = "javier"
READER_DIR = "native-readers"
ACCEPTANCE_FILE = f"{READER_DIR}/gemini-acceptance.json"
ACCEPTANCE_KEYS = ("schema", "harness", "cli_version", "reader_sources_sha256", "walk", "native", "streams", "join",
                   "review", "accepted_by")
READER_SOURCES = ("gemini_projection.py", "gemini_stream_join.py", "gemini_session_replay.py",
                  "vendor_record_binding.py", "transcript_view.py", "transcript_gemini.py",
                  "native_reader_registration.py", "drive.py", "vendor_provenance.py")
ACCEPTANCE_FLOOR = {"interactions": 2, "tool_round_trips": 1}
SHAPES = ("interactions", "tool_round_trips", "tool_error_statuses", "object_display_results",
          "multi_segment_interactions")
NEVER_COUNTED = ("parallel calls from one model message (the fact schema does not keep the issuing message)",
                 "a turn killed or timed out mid-tool (refused as incomplete, never accepted)",
                 "thoughts and thought signatures (replayed, never compared to the stream)")
SYNTHETIC = re.compile(r"synthetic", re.IGNORECASE)
_NATIVE_FILE = re.compile(r"session/native-turn-[1-9][0-9]*\.jsonl")
_STREAM_FILE = re.compile(r"turn-[1-9][0-9]*\.jsonl")
_REVIEW_FILE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\.md")
_HEX = re.compile(r"[0-9a-f]{64}")


# ---- the shared join ------------------------------------------------------------------------------------------------

def gemini_reader(raw: bytes, ordinal: int) -> dict:
    """The candidate: one interaction of a retained native snapshot, in vendor_provenance's fact schema."""
    try:
        facts = gp.project(raw)
    except gp.ProjectionRefused as e:
        raise vp.ProvenanceRefused(f"the Gemini projection refused the snapshot: {e}") from None
    if ordinal > len(facts):
        raise vp.ProvenanceRefused("snapshot lacks requested interaction")
    return facts[ordinal - 1]


def _shapes(facts) -> dict:
    tools = [o for f in facts for o in f["output"] if o.get("kind") == "tool"]
    return {"interactions": len(facts), "tool_round_trips": len(tools),
            "tool_error_statuses": sum(t.get("emitted_status") == "error" for t in tools),
            "object_display_results": sum(not t.get("output_present") for t in tools),
            "multi_segment_interactions": sum(
                sum(o.get("kind") == "recorded-text" for o in f["output"]) > 1 for f in facts)}


def join_session(raw: bytes, streams: list, reader) -> dict:
    """THE cross-check, shared by acceptance and production: {"status": "PASS", "interactions", "shapes"} only when
    the snapshot holds exactly one interaction per stream, each joins its stream and each is complete; otherwise
    {"status": "DISAGREE", "why"}."""
    if not streams:
        return {"status": "DISAGREE", "why": "no turn streams to join"}
    facts = []
    for n, text in enumerate(streams, 1):
        try:
            fact = reader(raw, n)
            got = gsj.join(fact, text)
        except vp.ProvenanceRefused as e:
            return {"status": "DISAGREE", "why": f"interaction {n}: native: {e}"}
        except gsj.JoinRefused as e:
            return {"status": "DISAGREE", "why": f"interaction {n}: {e}"}
        if got["complete"] is not True:
            return {"status": "DISAGREE",
                    "why": f"interaction {n} is not complete (terminal status {got['terminal_status']!r})"}
        facts.append(fact)
    try:
        reader(raw, len(streams) + 1)
    except vp.ProvenanceRefused:
        pass
    else:
        return {"status": "DISAGREE", "why": f"more native interactions for {len(streams)} streams"}
    return {"status": "PASS", "interactions": len(facts), "shapes": _shapes(facts)}


def check_session(native: bytes, streams: list) -> dict:
    """The acceptance check on retained files: join_session with the candidate reader."""
    return join_session(native, streams, gemini_reader)


def coverage_line(shapes: dict) -> str:
    seen = [f"{k}={shapes[k]}" for k in SHAPES if shapes.get(k)]
    unseen = [f"{k} (0 seen)" for k in SHAPES if not shapes.get(k)] + list(NEVER_COUNTED)
    return f"exercised: {', '.join(seen) or 'none'}; unverified: {'; '.join(unseen)}"


def floor_problem(shapes: dict):
    for key, least in ACCEPTANCE_FLOOR.items():
        if shapes.get(key, 0) < least:
            return f"acceptance needs at least {least} {key.replace('_', ' ')}; the walk exercised {shapes.get(key, 0)}"
    return None


# ---- the committed tree ---------------------------------------------------------------------------------------------

def _git(root: Path, *args, binary=False):
    out = subprocess.run(["git", "-C", str(root), *args], capture_output=True)
    if out.returncode != 0:
        raise RegistrationRefused(f"git {' '.join(args[:2])} failed: {out.stderr.decode(errors='replace').strip()}")
    return out.stdout if binary else out.stdout.decode("utf-8").strip()


def _repo(study: Path):
    out = subprocess.run(["git", "-C", str(study), "rev-parse", "--show-toplevel"], capture_output=True)
    if out.returncode != 0:
        return None, None
    root = Path(out.stdout.decode().strip()).resolve()
    return root, Path(study).resolve().relative_to(root).as_posix()


def _rel(prefix: str, path: str) -> str:
    return f"{prefix}/{path}" if prefix not in ("", ".") else path


def _in_head(root: Path, rel: str) -> bool:
    return subprocess.run(["git", "-C", str(root), "cat-file", "-e", f"HEAD:{rel}"], capture_output=True).returncode == 0


def _clean(root: Path, rels: list) -> None:
    dirty = _git(root, "status", "--porcelain", "--untracked-files=all", "--", *rels)
    if dirty:
        raise RegistrationRefused(f"a bound path differs from the committed tree: {dirty.splitlines()[0]}")


def _show(root: Path, rel: str) -> bytes:
    if not _in_head(root, rel):
        raise RegistrationRefused(f"{rel} is not in the committed tree")
    return _git(root, "show", f"HEAD:{rel}", binary=True)


def reader_sources_sha256(study: Path = HERE, *, committed=None) -> str:
    """One hash over the reader's sources, each named and hashed, in a fixed order. `committed(name)` gives HEAD's
    bytes (the registration road); without it, the files as they stand (the check tool's report)."""
    lines = []
    for name in READER_SOURCES:
        raw = committed(name) if committed else (Path(study) / name).read_bytes()
        lines.append(f"{name}\0{hashlib.sha256(raw).hexdigest()}\n")
    return hashlib.sha256("".join(lines).encode()).hexdigest()


def _ref(ref, pattern, what):
    if (not isinstance(ref, dict) or set(ref) != {"file", "sha256"} or not isinstance(ref["file"], str)
            or not pattern.fullmatch(ref["file"]) or not isinstance(ref["sha256"], str) or not _HEX.fullmatch(ref["sha256"])):
        raise RegistrationRefused(f"{what} must be {{file, sha256}} with a confined file name and a sha256")
    return ref


def _hashed(raw: bytes, ref: dict, what: str) -> bytes:
    if hashlib.sha256(raw).hexdigest() != ref["sha256"]:
        raise RegistrationRefused(f"the {what} hash in the record does not match the committed bytes of {ref['file']}")
    return raw


def _materialize(root: Path, rel: str, into: Path) -> None:
    """The walk folder's committed blobs, written under `into`; a link or a submodule refuses."""
    listing = _git(root, "ls-tree", "-r", "-z", "HEAD", "--", rel + "/", binary=True)
    entries = [e for e in listing.split(b"\0") if e]
    if not entries:
        raise RegistrationRefused(f"walk folder {rel} is not in the committed tree")
    for entry in entries:
        meta, path = entry.split(b"\t", 1)
        mode, kind, sha = meta.decode().split()
        if kind != "blob" or mode not in ("100644", "100755"):
            raise RegistrationRefused(f"{path.decode()} in the committed walk is not a regular file")
        local = into / Path(path.decode()).relative_to(rel)
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_bytes(_git(root, "cat-file", "blob", sha, binary=True))


def acceptance_problems(record, study: Path = HERE) -> None:
    """Raise RegistrationRefused unless `record` (read from HEAD) binds a committed recorded walk, as above."""
    import drive                                    # lazily: drive imports this module
    study = Path(study)
    root, prefix = _repo(study)
    if root is None:
        raise RegistrationRefused("the study is not in a git repository: the record is read from a committed tree")
    if not isinstance(record, dict):
        raise RegistrationRefused("an acceptance record is a JSON object")
    if "evidence_label" in record:
        raise RegistrationRefused("evidence_label is derived from the walk's bindings, never asserted by the record")
    if set(record) != set(ACCEPTANCE_KEYS) or record.get("schema") != 1:
        raise RegistrationRefused(f"an acceptance record holds exactly {list(ACCEPTANCE_KEYS)}, schema 1")
    if record["harness"] != HARNESS or record["cli_version"] != PINNED_CLI:
        raise RegistrationRefused(f"the record is for {HARNESS} {PINNED_CLI} only")
    review = record["review"]
    if (not isinstance(review, dict) or set(review) != {"verdict", "file", "sha256", "reviewer"}
            or review["verdict"] != "PASS" or not (isinstance(review["reviewer"], str) and review["reviewer"].strip())):
        raise RegistrationRefused("the record carries an independent review's PASS, its report and reviewer")
    if record["accepted_by"] != ACCEPTOR:
        raise RegistrationRefused(f"the acceptor must be {ACCEPTOR!r}, in his own window; not {record['accepted_by']!r}")
    if review["reviewer"].strip().lower() == ACCEPTOR:
        raise RegistrationRefused("the reviewer and the acceptor must be different principals")
    walk = record["walk"]
    if not (isinstance(walk, str) and walk_register.WALK_ID.fullmatch(walk)):
        raise RegistrationRefused(f"walk {walk!r} is not a walk id")
    walks = _rel(prefix, mode_binding.WALKS_DIR)
    register_rel, walk_rel = f"{walks}/{walk_register.REGISTER_NAME}", f"{walks}/{walk}"
    review_ref = _ref({"file": review["file"], "sha256": review["sha256"]}, _REVIEW_FILE, "review")
    review_rel = _rel(prefix, f"{READER_DIR}/{review_ref['file']}")
    _clean(root, [register_rel, walk_rel, review_rel] + [_rel(prefix, n) for n in READER_SOURCES])
    if record["reader_sources_sha256"] != reader_sources_sha256(committed=lambda n: _show(root, _rel(prefix, n))):
        raise RegistrationRefused("the reader's sources changed since the record: a new acceptance is needed")
    try:
        register = json.loads(_show(root, register_rel), object_pairs_hook=walk_register.no_duplicate_keys)
        entries = [e for e in register["walks"] if isinstance(e, dict) and e.get("walk") == walk]
    except (ValueError, KeyError, TypeError, walk_register.DuplicateKey) as e:
        raise RegistrationRefused(f"the committed rehearsals register cannot be read: {e}") from None
    if len(entries) != 1 or entries[0].get("arm") != ARM:
        raise RegistrationRefused(f"walk {walk!r} is not one committed arm-{ARM} walk of the rehearsals register")
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp) / walk
        _materialize(root, walk_rel, base)
        try:
            drive.walk_files(base)
        except drive.DriveRefused as e:
            raise RegistrationRefused(f"the committed walk fails drive.walk_files: {e}") from None
        subjects = _git(root, "log", "--format=%s", "HEAD", "--", walk_rel + "/").splitlines()
        if subjects != [drive.WALK_SUBJECT]:
            raise RegistrationRefused(f"the walk folder is not exactly one WalkRepo commit ({drive.WALK_SUBJECT!r}): "
                                      f"{subjects}")
        try:
            ledger = json.loads((base / drive.LEDGER_FILE).read_bytes())
            snaps, ledger_streams = list(ledger["native_snapshots"]), list(ledger["streams"])
        except (OSError, ValueError, KeyError, TypeError) as e:
            raise RegistrationRefused(f"the walk's driver ledger names no native snapshots and streams: {e}") from None
        if not isinstance(ledger.get("native_history"), dict):
            raise RegistrationRefused("the walk's driver ledger holds no native_history record")
        native_ref = _ref(record["native"], _NATIVE_FILE, "native")
        native = _hashed((base / native_ref["file"]).read_bytes() if (base / native_ref["file"]).is_file() else b"",
                         native_ref, "native")
        if not snaps or {"file": "session/" + str(snaps[-1].get("file")), "sha256": snaps[-1].get("sha256")} \
                != native_ref:
            raise RegistrationRefused("the native snapshot is not the last one the walk's driver ledger names")
        if not isinstance(record["streams"], list) or not record["streams"]:
            raise RegistrationRefused("the record names the walk's turn streams")
        refs = [_ref(s, _STREAM_FILE, "stream") for s in record["streams"]]
        if [r["file"] for r in refs] != ledger_streams or ledger_streams != [
                f"turn-{n}.jsonl" for n in range(1, len(refs) + 1)]:
            raise RegistrationRefused("the record's streams are not the streams the driver ledger names, turns 1..n")
        streams = []
        for r in refs:
            path = base / r["file"]
            streams.append(_hashed(path.read_bytes() if path.is_file() else b"", r, "stream").decode("utf-8"))
        got = check_session(native, streams)
        join = record["join"]
        if got["status"] != "PASS" or join != {"status": "PASS", "interactions": got["interactions"]}:
            raise RegistrationRefused(f"the join does not re-derive as recorded: {got.get('why') or got['interactions']}")
        floor = floor_problem(got["shapes"])
        if floor:
            raise RegistrationRefused(floor)
        try:
            vp.session_history_facts(HARNESS, base / "session", [dict(s) for s in snaps],
                                     readers={HARNESS: gemini_reader})
        except (vp.ProvenanceRefused, vp.ProvenancePending) as e:
            raise RegistrationRefused(f"the snapshot-history join over the ledger's snapshots refuses: {e}") from None
        if len(snaps) < 2:
            raise RegistrationRefused("the snapshot-history join needs a resume: at least 2 retained snapshots")
        try:
            metadata = replay_mod.replay(native)["metadata"]
        except replay_mod.ReplayRefused as e:
            raise RegistrationRefused(f"the native session metadata cannot be read: {e}") from None
    review_text = _hashed(_show(root, review_rel), review_ref, "review")
    for what, text in (("the native session metadata", json.dumps(metadata, sort_keys=True)),
                       ("the register entry", json.dumps(entries[0], sort_keys=True)),
                       ("the review", review_text.decode("utf-8", errors="replace")),
                       ("the acceptance record", json.dumps(record, sort_keys=True))):
        if SYNTHETIC.search(text):
            raise RegistrationRefused(f"{what} carries a synthetic marker: never acceptance evidence")


def production_readers(study: Path = HERE) -> dict:
    """The production native-reader registry: {} without an acceptance record in the working tree (no git is run, so
    a take's driver pays nothing; a committed record deleted from disk also reads {}, which keeps every Gemini take
    pending, the fail-closed side); {"gemini": gemini_reader} with a committed, clean one that holds;
    RegistrationRefused otherwise."""
    study = Path(study)
    path = study / ACCEPTANCE_FILE
    if not (path.exists() or path.is_symlink()):
        return {}
    root, prefix = _repo(study)
    if root is None:
        raise RegistrationRefused("an acceptance record outside a git repository is never read")
    rel = _rel(prefix, ACCEPTANCE_FILE)
    if not _in_head(root, rel):
        raise RegistrationRefused("the acceptance record is uncommitted: only a committed record is read")
    _clean(root, [rel])
    try:
        record = json.loads(_show(root, rel))
    except (ValueError, UnicodeError) as e:
        raise RegistrationRefused(f"the acceptance record is not JSON: {e}") from None
    acceptance_problems(record, study)
    return {HARNESS: gemini_reader}


def acceptance_provenance(study: Path = HERE) -> dict:
    """Who committed the record and the review, and when HEAD stands: printed by `verify`, never a trust input."""
    study = Path(study)
    root, prefix = _repo(study)
    if root is None:
        raise RegistrationRefused("the study is not in a git repository")

    def last(rel):
        line = _git(root, "log", "-1", "--format=%H%x00%an", "HEAD", "--", rel)
        return line.split("\0") if line else [None, None]

    commit, author = last(_rel(prefix, ACCEPTANCE_FILE))
    reviews = _git(root, "log", "--format=%H", "HEAD", "--", _rel(prefix, READER_DIR + "/*.md")).splitlines()
    return {"acceptance_commit": commit, "acceptance_author": author,
            "review_commit": reviews[0] if reviews else None, "head": _git(root, "rev-parse", "HEAD")}


def _head() -> str:
    out = subprocess.run(["git", "-C", str(HERE), "rev-parse", "HEAD"], capture_output=True)
    return out.stdout.decode().strip() if out.returncode == 0 else "unknown (not a git checkout)"


def main(argv=None) -> int:
    """`check --native <snapshot> --stream <turn-1> [--stream <turn-2> …]`: the acceptance check on retained files.
    `verify`: production_readers on the committed tree, with the record's and the review's commits."""
    import argparse
    ap = argparse.ArgumentParser(prog="native_reader_registration.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("--native", required=True)
    c.add_argument("--stream", action="append", required=True)
    sub.add_parser("verify")
    a = ap.parse_args(argv)
    if a.cmd == "verify":
        try:
            readers = production_readers()
        except RegistrationRefused as e:
            print(f"REFUSED: {e}")
            return 1
        prov = acceptance_provenance()
        print(f"registered: {sorted(readers) or 'none'}; acceptance commit {prov['acceptance_commit']} by "
              f"{prov['acceptance_author']}; review commit {prov['review_commit']}; HEAD {prov['head']}; local "
              f"unsigned records: the guarantee is that the acceptance commit was made in Javier's own window")
        return 0
    got = check_session(Path(a.native).read_bytes(), [Path(s).read_text(encoding="utf-8") for s in a.stream])
    if got["status"] == "PASS":
        floor = floor_problem(got["shapes"])
        print(f"PASS: {got['interactions']} interaction(s) joined, every one complete; {coverage_line(got['shapes'])}; "
              f"acceptance floor {'met' if floor is None else 'NOT met: ' + floor}; reader sources sha256 "
              f"{reader_sources_sha256()} at HEAD {_head()}")
        return 0
    print(f"DISAGREE: {got['why']}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
