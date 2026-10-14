"""Live harness: the Gemini native-reader registration road, built so that only real evidence is missing.

A native-session reader enters production only through a committed acceptance record, read by production_readers().
Without the record the registry stays empty, every Gemini take stays NativeCrossCheckPending (drive.py), and nothing
here changes that. The record is never written by this module or by any test; a human commits it after the first
Gemini walk, the acceptance check and an independent review.

The reader candidate (gemini_reader) is gemini_projection.project, ordinal by ordinal, in vendor_provenance's fact
schema. check_session() is the acceptance check the first Gemini walk runs on its retained files: the projection of
the walk's last retained native snapshot, joined interaction by interaction to the walk's host-captured streams by
gemini_stream_join.join; PASS needs one interaction per stream, every join clean and every interaction complete.

The acceptance record (ACCEPTANCE_FILE, beside this module; closed keys ACCEPTANCE_KEYS) binds:
  reader_sources_sha256  reader_sources_sha256() over READER_SOURCES, as they stand: any later edit of the reader
                         or the code it relies on unregisters it until a new record is committed;
  cli_version            the pinned Gemini CLI version the evidence was recorded at (PINNED_CLI);
  walk, evidence_label   a walk the committed rehearsals register lists under arm G, labelled "recorded-walk";
                         a record labelled anything else (a synthetic fixture) refuses;
  native, streams        {file, sha256} of the walk's retained snapshot and its turn streams, confined to the walk's
                         folder, re-hashed here;
  join                   {"status": "PASS", "interactions": n}, re-derived here by check_session on those bytes;
  review                 {"verdict": "PASS", "file", "sha256", "reviewer"}: the independent review's report beside the
                         record, re-hashed here;
  accepted_by            who committed it (never inferred).
Any mismatch refuses (RegistrationRefused): a record that cannot be trusted stops the reader from loading, never
falls back to a silent empty registry.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import gemini_projection as gp  # noqa: E402
import gemini_stream_join as gsj  # noqa: E402
import mode_binding  # noqa: E402
import vendor_provenance as vp  # noqa: E402
import walk_register  # noqa: E402


class RegistrationRefused(ValueError):
    """The acceptance record cannot be trusted; the reader is not registered."""


PINNED_CLI = "0.64.0"
HARNESS = "gemini"
ARM = "G"
RECORDED = "recorded-walk"
READER_DIR = "native-readers"
ACCEPTANCE_FILE = f"{READER_DIR}/gemini-acceptance.json"
ACCEPTANCE_KEYS = ("schema", "harness", "cli_version", "reader_sources_sha256", "walk", "evidence_label", "native",
                   "streams", "join", "review", "accepted_by")
READER_SOURCES = ("gemini_projection.py", "gemini_stream_join.py", "gemini_session_replay.py",
                  "vendor_record_binding.py", "transcript_view.py", "transcript_gemini.py",
                  "native_reader_registration.py")
_NATIVE_FILE = re.compile(r"session/native-turn-[1-9][0-9]*\.jsonl")
_STREAM_FILE = re.compile(r"turn-[1-9][0-9]*\.jsonl")
_REVIEW_FILE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\.md")
_HEX = re.compile(r"[0-9a-f]{64}")


def reader_sources_sha256(study: Path = HERE) -> str:
    """One hash over the reader's sources, each named and hashed, in a fixed order."""
    lines = []
    for name in READER_SOURCES:
        lines.append(f"{name}\0{hashlib.sha256((Path(study) / name).read_bytes()).hexdigest()}\n")
    return hashlib.sha256("".join(lines).encode()).hexdigest()


def gemini_reader(raw: bytes, ordinal: int) -> dict:
    """The candidate: one interaction of a retained native snapshot, in vendor_provenance's fact schema."""
    try:
        facts = gp.project(raw)
    except gp.ProjectionRefused as e:
        raise vp.ProvenanceRefused(f"the Gemini projection refused the snapshot: {e}") from None
    if ordinal > len(facts):
        raise vp.ProvenanceRefused("snapshot lacks requested interaction")
    return facts[ordinal - 1]


def check_session(native: bytes, streams: list) -> dict:
    """The acceptance check: {"status": "PASS", "interactions", "complete"} or {"status": "DISAGREE", "why"}."""
    try:
        facts = gp.project(native)
    except gp.ProjectionRefused as e:
        return {"status": "DISAGREE", "why": f"projection refused the native snapshot: {e}"}
    if len(facts) != len(streams):
        return {"status": "DISAGREE", "why": f"{len(facts)} native interactions for {len(streams)} streams"}
    complete = []
    for n, (fact, text) in enumerate(zip(facts, streams), 1):
        try:
            got = gsj.join(fact, text)
        except gsj.JoinRefused as e:
            return {"status": "DISAGREE", "why": f"interaction {n}: {e}"}
        complete.append(got["complete"])
    if not all(complete):
        return {"status": "DISAGREE", "why": f"interactions not complete: {[n for n, c in enumerate(complete, 1) if not c]}"}
    return {"status": "PASS", "interactions": len(facts), "complete": complete}


def _ref(ref, pattern, what):
    if (not isinstance(ref, dict) or set(ref) != {"file", "sha256"} or not isinstance(ref["file"], str)
            or not pattern.fullmatch(ref["file"]) or not isinstance(ref["sha256"], str) or not _HEX.fullmatch(ref["sha256"])):
        raise RegistrationRefused(f"{what} must be {{file, sha256}} with a confined file name and a sha256")
    return ref


def _bytes(base: Path, ref: dict, what: str) -> bytes:
    path = base / ref["file"]
    if path.is_symlink() or not path.is_file():
        raise RegistrationRefused(f"{what} {ref['file']} is not a regular file")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != ref["sha256"]:
        raise RegistrationRefused(f"{what} {ref['file']} does not match its recorded sha256")
    return raw


def acceptance_problems(record, study: Path = HERE) -> None:
    """Raise RegistrationRefused unless `record` binds everything ACCEPTANCE_KEYS names, re-derived here."""
    study = Path(study)
    if not isinstance(record, dict) or set(record) != set(ACCEPTANCE_KEYS) or record.get("schema") != 1:
        raise RegistrationRefused(f"an acceptance record holds exactly {list(ACCEPTANCE_KEYS)}, schema 1")
    if record["harness"] != HARNESS or record["cli_version"] != PINNED_CLI:
        raise RegistrationRefused(f"the record is for {HARNESS} {PINNED_CLI} only")
    if record["evidence_label"] != RECORDED:
        raise RegistrationRefused(f"evidence labelled {record['evidence_label']!r} is never acceptance evidence")
    if record["reader_sources_sha256"] != reader_sources_sha256(study):
        raise RegistrationRefused("the reader's sources changed since the record: a new acceptance is needed")
    if not (isinstance(record["accepted_by"], str) and record["accepted_by"].strip()):
        raise RegistrationRefused("the record names who accepted it")
    walk = record["walk"]
    rehearsals = study / mode_binding.WALKS_DIR
    entries = [e for e in walk_register.registered(rehearsals) if e.get("walk") == walk]
    if not (isinstance(walk, str) and walk_register.WALK_ID.fullmatch(walk)) or len(entries) != 1 \
            or entries[0].get("arm") != ARM:
        raise RegistrationRefused(f"walk {walk!r} is not one committed arm-{ARM} walk of the rehearsals register")
    base = rehearsals / walk
    native = _bytes(base, _ref(record["native"], _NATIVE_FILE, "native"), "native")
    if not isinstance(record["streams"], list) or not record["streams"]:
        raise RegistrationRefused("the record names the walk's turn streams")
    names = [_ref(s, _STREAM_FILE, "stream")["file"] for s in record["streams"]]
    if names != [f"turn-{n}.jsonl" for n in range(1, len(names) + 1)]:
        raise RegistrationRefused("the streams are the walk's turns 1..n, in order")
    streams = [_bytes(base, s, "stream").decode("utf-8") for s in record["streams"]]
    got = check_session(native, streams)
    join = record["join"]
    if (got["status"] != "PASS" or not isinstance(join, dict) or join != {"status": "PASS",
                                                                          "interactions": got["interactions"]}):
        raise RegistrationRefused(f"the join does not re-derive as recorded: {got}")
    review = record["review"]
    if (not isinstance(review, dict) or set(review) != {"verdict", "file", "sha256", "reviewer"}
            or review["verdict"] != "PASS" or not (isinstance(review["reviewer"], str) and review["reviewer"].strip())):
        raise RegistrationRefused("the record carries an independent review's PASS, its report and reviewer")
    _bytes(study / READER_DIR, _ref({"file": review["file"], "sha256": review["sha256"]}, _REVIEW_FILE, "review"),
           "review")


def production_readers(study: Path = HERE) -> dict:
    """The production native-reader registry: {} without an acceptance record; {"gemini": gemini_reader} with one
    that holds; RegistrationRefused when one exists and does not."""
    path = Path(study) / ACCEPTANCE_FILE
    if not path.exists() and not path.is_symlink():
        return {}
    if path.is_symlink() or not path.is_file():
        raise RegistrationRefused("the acceptance record is not a regular file")
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as e:
        raise RegistrationRefused(f"the acceptance record is not JSON: {e}") from None
    acceptance_problems(record, study)
    return {HARNESS: gemini_reader}


def main(argv=None) -> int:
    """`check --native <snapshot> --stream <turn-1> [--stream <turn-2> …]`: the first Gemini walk's acceptance check on
    its retained files. Prints PASS with the interaction count, or DISAGREE with the exact disagreement."""
    import argparse
    ap = argparse.ArgumentParser(prog="native_reader_registration.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("--native", required=True)
    c.add_argument("--stream", action="append", required=True)
    a = ap.parse_args(argv)
    got = check_session(Path(a.native).read_bytes(), [Path(s).read_text(encoding="utf-8") for s in a.stream])
    if got["status"] == "PASS":
        print(f"PASS: {got['interactions']} interaction(s) joined, every one complete; reader sources sha256 "
              f"{reader_sources_sha256()}")
        return 0
    print(f"DISAGREE: {got['why']}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
