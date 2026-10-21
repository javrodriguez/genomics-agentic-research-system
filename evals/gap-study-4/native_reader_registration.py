"""Live harness: the Gemini native-reader registration road, built so that only real evidence is missing.

A native-session reader enters production only through a committed acceptance record, read by production_readers().
Without the record the registry stays empty, every Gemini take stays NativeCrossCheckPending (drive.py), and nothing
here changes that. The record is never written by this module or by any test.

Registration review (finding 1, MAJOR: the first road was self-certifying, since anyone able to write the working tree
could assert every field). Now:
  * every bound input (the record, the rehearsals register, the walk folder, the review, READER_SOURCES) is read from
    the committed tree (git show HEAD), and any difference between the working tree and HEAD for a bound path refuses;
  * the walk must pass drive.walk_files (on its committed bytes) and its folder's first commit must carry
    drive.WALK_SUBJECT (a subject anyone can write) and change exactly the folder and its register entry; the native snapshot and the streams the record names must be the ones
    that walk's own driver ledger names (the last native_snapshots ref, and its streams), byte for byte;
  * the evidence label is derived from those bindings (RECORDED), never asserted: a record carrying one refuses;
  * a synthetic marker (case-insensitive "synthetic") in the native session metadata, the register entry, the review
    or the record refuses; this gate runs last, so no labelled synthetic fixture can ever register;
  * the acceptor is "javier" and the reviewer is a different principal.
These are local, unsigned git records: anyone able to commit can write them. The final guarantee is procedural (the
acceptance commit is made in Javier's own window); a hook-gated acceptance door is a named follow-up, not built here.

What the gates are, stated plainly (batch-8 review finding 3): every gate below, the walk-commit, ledger, record and
journal checks included, is a CONSISTENCY check over bytes the producer writes or can derive. It refuses an
inconsistent walk, a placeholder record, or a walk committed by hand under another subject; it cannot tell a
consistent fabrication (the road's bytes copied, or rewritten coherently, and committed by hand under WALK_SUBJECT)
from a real walk. The guarantee against fabrication is procedural: the acceptance commit, made in Javier's window after
the independent review of the real walk. Binding the walk to a record outside the producer's write reach (for example
the box's per-take witness hashes recorded by another principal) is a named follow-up, not built.

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
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import codex_native as cn  # noqa: E402
import gemini_projection as gp  # noqa: E402
import gemini_session_replay as replay_mod  # noqa: E402
import gemini_stream_join as gsj  # noqa: E402
import mode_binding  # noqa: E402
import pending_walk  # noqa: E402
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
_REVIEW_FILE = re.compile(re.escape(HARNESS) + r"-review\.md")   # the one review name copy_manifest claims
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
    return {"status": "PASS", "interactions": len(facts), "shapes": _shapes(facts), "properties": take_properties(raw)}


def take_properties(raw: bytes):
    """Lane vendor-b26 (glitch-26's rulings 1 and 2): the take's named properties, never facts: history_rewrites and
    tool_outputs_masked (the CLI's tool-output masking re-recorded the history, chunk-NR7L3FXV.js:348251), the
    ignored-prompt resumes (:286096-286110) and loop_feedback_injected (:348601-348609), counted on the snapshot the
    join read. None when the Gemini projection does not read the snapshot (a reader other than gemini_reader)."""
    try:
        return gp.project_with_properties(raw)[1]
    except gp.ProjectionRefused:
        return None


def gemini_snapshot_prefixes(folder: Path, refs: list) -> None:
    """Lane vendor-b26 (glitch-26's ruling 6): inside the Gemini history join, each retained snapshot is a byte prefix
    of the next one. The recorder only appends (appendRecord), so a re-record's retired originals stay in every later
    snapshot's bytes; a later snapshot that is not an extension of the earlier one refuses (vp.ProvenanceRefused).
    vendor_provenance's contract is unchanged: this runs beside session_history_facts, never inside it."""
    previous = None
    for ref in refs:
        raw = vp.referenced_bytes(Path(folder), ref)
        if previous is not None and not raw.startswith(previous):
            raise vp.ProvenanceRefused("a later Gemini native snapshot is not a byte extension of the one before it")
        previous = raw


def gemini_history(folder: Path, refs: list, *, reader=None) -> list:
    """The Gemini history join: the byte-prefix invariant, then vendor_provenance.session_history_facts."""
    gemini_snapshot_prefixes(folder, refs)
    return vp.session_history_facts(HARNESS, Path(folder), [dict(r) for r in refs],
                                    readers={HARNESS: reader or gemini_reader})


def check_session(native: bytes, streams: list) -> dict:
    """The acceptance check on retained files: join_session with the candidate reader."""
    return join_session(native, streams, gemini_reader)


# ---- Codex slice 3: the Codex reader and its one shared join -----------------------------------------------------

CODEX_PINNED_CLI = cn.PINNED_CLI
CODEX_ACCEPTANCE_FILE = f"{READER_DIR}/codex-acceptance.json"
CODEX_SOURCES = ("codex_native.py", "native_reader_registration.py", "drive.py", "vendor_provenance.py",
                 "native_snapshot.py")
CODEX_FLOOR = {"interactions": 2, "command_round_trips": 1}
CODEX_SHAPES = ("interactions", "command_round_trips", "reroutes", "marker_texts")


def codex_reader(raw: bytes, ordinal: int) -> dict:
    """The Codex candidate: one turn of a retained rollout, in vendor_provenance's fact schema (codex_native.project;
    requested_model is the turn_context's REQUESTED model, never the served one)."""
    try:
        facts = cn.project(raw)
    except cn.ReaderRefused as e:
        raise vp.ProvenanceRefused(f"the Codex rollout reader refused the snapshot: {e}") from None
    if ordinal > len(facts):
        raise vp.ProvenanceRefused("snapshot lacks requested interaction")
    return facts[ordinal - 1]


def codex_join_session(raw: bytes, streams: list, exit_codes: list, *, sent: list, model: str) -> dict:
    """THE Codex cross-check, shared by acceptance and production (drive.codex_cross_check): PASS only when the rollout
    holds exactly one turn per exec stream, each turn's recorded prompt (its UserMessage) is the line the driver sent
    that turn (`sent`, one per stream) and its requested model (turn_context.model) is the take's requested `model`
    (lane vendor-b25, Codex review M1: the exec stream carries neither, so the launch side is the only witness), each
    turn joins its stream (codex_native.join) and each is complete; otherwise DISAGREE with the reason. cwd is read but
    not compared: vendor_provenance.cross_check, the contract, binds session_id, sent, output and requested_model only."""
    if not streams or len(streams) != len(exit_codes) or len(sent) != len(streams):
        return {"status": "DISAGREE", "why": "no exec streams, or not one exit code and one sent line per stream"}
    if not (isinstance(model, str) and model):
        return {"status": "DISAGREE", "why": "no requested model to compare the rollout's against"}
    try:
        got = cn.read_rollout(raw)
    except cn.ReaderRefused as e:
        return {"status": "DISAGREE", "why": f"native: {e}"}
    turns = got["turns"]
    if len(turns) != len(streams):
        return {"status": "DISAGREE", "why": f"{len(turns)} native turns for {len(streams)} streams"}
    joined = []
    for n, (turn, text, code) in enumerate(zip(turns, streams, exit_codes), 1):
        if turn["sent"] != sent[n - 1]:
            return {"status": "DISAGREE", "why": f"interaction {n}: the rollout's sent prompt is not the line sent"}
        if turn["requested_model"] != model:
            return {"status": "DISAGREE", "why": f"interaction {n}: the rollout's requested model is not the take's"}
        try:
            j = cn.join(turn, text, exit_code=code, session_id=got["session_id"])
        except cn.JoinRefused as e:
            return {"status": "DISAGREE", "why": f"interaction {n}: {e}"}
        if j["complete"] is not True:
            return {"status": "DISAGREE", "why": f"interaction {n} is not complete (terminal {j['terminal']!r})"}
        joined.append(j)
    shapes = {"interactions": len(joined), "command_round_trips": sum(j["commands"] for j in joined),
              "reroutes": sum(j["served_model"] is not None for j in joined),
              "marker_texts": sum(bool(j["marker_text"]) for j in joined)}
    return {"status": "PASS", "interactions": len(joined), "shapes": shapes,
            "served_models": [j["served_model"] for j in joined]}


def codex_check(native: bytes, streams: list, ledger: dict) -> dict:
    """The Codex acceptance check: the shared join, and (Codex road review F3) the driver ledger's served_model bound to
    each turn's own stream: unobserved with no value when it holds no reroute, stream-reroute with its `to` model when
    it does. A served model claimed in the ledger and not observed in its stream refuses."""
    got = codex_join_session(native, streams, [t.get("exit") for t in ledger["turns"]],
                             sent=[t.get("sent") for t in ledger["turns"]], model=ledger.get("model_requested"))
    if got["status"] != "PASS":
        return got
    want = [{"value": None, "source": "unobserved"} if s is None else {"value": s, "source": "stream-reroute"}
            for s in got["served_models"]]
    if ledger.get("served_model") != want:
        return {"status": "DISAGREE", "why": f"the ledger's served_model is not each turn's own stream evidence: {want}"}
    return got


def coverage_line(shapes: dict) -> str:
    seen = [f"{k}={shapes[k]}" for k in SHAPES if shapes.get(k)]
    unseen = [f"{k} (0 seen)" for k in SHAPES if not shapes.get(k)] + list(NEVER_COUNTED)
    return f"exercised: {', '.join(seen) or 'none'}; unverified: {'; '.join(unseen)}"


def floor_problem(shapes: dict, floor=None):
    for key, least in (ACCEPTANCE_FLOOR if floor is None else floor).items():
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


def reader_sources_sha256(study: Path = HERE, *, committed=None, sources=None) -> str:
    """One hash over the reader's sources, each named and hashed, in a fixed order. `committed(name)` gives HEAD's
    bytes (the registration road); without it, the files as they stand (the check tool's report)."""
    lines = []
    for name in (READER_SOURCES if sources is None else sources):
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


# ---- finding 1: the walk's records are consistent with a runner-made walk (consistency, not provenance) -------------------------------------------------------------------------

LEDGER_KEYS = ("kind", "task", "half", "wording", "pressure", "repeat", "arm", "model_requested", "agent", "session_id",
               "project", "source", "row", "row_commit", "permission_mode", "permission_mode_passed",
               "permission_mode_recorded", "budget_s", "finalize_wait_s", "poll_s", "gars_tree_sha", "fixture", "claude_version", "turns",
               "outcome", "first_agent_turn", "environment", "transcript", "published", "cross_check", "cost",
               "streams", "native_snapshots", "native_snapshot_refusal", "native_history", "cross_check_status",
               "operator_steps")   # the ownership road's grant and restore (drive.OWNERSHIP_STEPS), 14 Oct 2026
ENVIRONMENT_FILE = "environment.json"
LAUNCH_FILE = "launch.json"


def _walk_commit(root: Path, walk_rel: str, register_rel: str, entry: dict) -> str:
    """The walk's WalkRepo commit: the oldest commit touching its folder, whose subject is drive.WALK_SUBJECT, which
    adds exactly the folder's files plus that walk's register entry (the committed register is its parent's with
    exactly this entry appended). Any later commit touching the folder is a regrade commit (walk_regrade's subject)
    changing only its regrade.json."""
    import drive
    import walk_regrade
    log = [ln.split("\0") for ln in _git(root, "log", "--format=%H%x00%s", "HEAD", "--", walk_rel + "/").splitlines()]
    if not log or log[-1][1] != drive.WALK_SUBJECT:
        raise RegistrationRefused(f"the walk folder's first commit is not a WalkRepo commit ({drive.WALK_SUBJECT!r})")
    commit = log[-1][0]
    for later, subject in log[:-1]:
        changed = _git(root, "diff-tree", "-r", "--no-commit-id", "--name-only", "--no-renames", later).splitlines()
        if subject != walk_regrade.REGRADE_SUBJECT or changed != [f"{walk_rel}/{walk_regrade.REGRADE_FILE}"]:
            raise RegistrationRefused(f"commit {later} touches the walk folder and is not a regrade commit of its "
                                      f"{walk_regrade.REGRADE_FILE} alone")
    status = _git(root, "diff-tree", "-r", "--no-commit-id", "--name-status", "--no-renames", "--root",
                  commit).splitlines()
    walk_files = sorted(p for st, p in (ln.split("\t", 1) for ln in status) if p.startswith(walk_rel + "/"))
    others = sorted(p for st, p in (ln.split("\t", 1) for ln in status) if not p.startswith(walk_rel + "/"))
    added = all(st == "A" for st, p in (ln.split("\t", 1) for ln in status) if p.startswith(walk_rel + "/"))
    at_commit = sorted(_git(root, "ls-tree", "-r", "--name-only", commit, "--", walk_rel + "/").splitlines())
    if others != [register_rel] or not added or walk_files != at_commit or not walk_files:
        raise RegistrationRefused(f"the walk commit {commit} does not add exactly {walk_rel}/** and its register "
                                  f"entry: others {others}")
    if walk_regrade.REGRADE_FILE in {p.rsplit("/", 1)[-1] for p in walk_files}:
        raise RegistrationRefused("the walk commit already holds a regrade record")

    def walks_at(rev):
        try:
            return json.loads(_git(root, "show", f"{rev}:{register_rel}", binary=True))["walks"]
        except (ValueError, KeyError, TypeError) as e:
            raise RegistrationRefused(f"the register at {rev} cannot be read: {e}") from None
    if walks_at(commit) != walks_at(f"{commit}^") + [entry]:
        raise RegistrationRefused("the walk commit's register is not its parent's with exactly this entry appended")
    return commit


def _ledger_problems(ledger, entry: dict, base: Path, harness: str = HARNESS) -> None:
    """The driver ledger's full take schema (drive's _take_records), for a Gemini walk whose cross-check is pending,
    with environment.json re-hashed."""
    keys = set(PROFILES[harness]["ledger_keys"])
    if not isinstance(ledger, dict) or set(ledger) != keys:
        raise RegistrationRefused(f"the driver ledger is not the take schema of a native-session vendor walk: "
                                  f"{sorted(set(ledger) ^ keys) if isinstance(ledger, dict) else ledger}")
    for key, want in (("kind", "take"), ("task", entry["task"]), ("half", entry["half"]),
                      ("wording", entry["wording"]), ("arm", entry["arm"]), ("model_requested", entry["model"]),
                      ("agent", {"harness": harness, "version": PROFILES[harness]["cli"]}), ("row", None),
                      ("row_commit", None),
                      ("first_agent_turn", True), ("transcript", None), ("published", None), ("cross_check", None),
                      ("cost", None), ("native_snapshot_refusal", None)):
        if ledger[key] != want:
            raise RegistrationRefused(f"the driver ledger's {key} is {ledger[key]!r}, not {want!r}")
    n = len(ledger["streams"]) if isinstance(ledger["streams"], list) else 0
    if ledger["streams"] != [f"turn-{k}.jsonl" for k in range(1, n + 1)] or not n:
        raise RegistrationRefused("the driver ledger's streams are not turns 1..n")
    turns = ledger["turns"]
    if not isinstance(turns, list) or len(turns) != n or not all(
            isinstance(t, dict) and isinstance(t.get("sent"), str) and t["sent"] for t in turns):
        raise RegistrationRefused("the driver ledger's turns are not one row with its sent line per stream")
    if not isinstance(ledger["session_id"], str) or not isinstance(ledger["permission_mode_passed"], str):
        raise RegistrationRefused("the driver ledger names no session id or passed permission mode")
    env = base / ENVIRONMENT_FILE
    if ledger["environment"] != {"file": ENVIRONMENT_FILE, "sha256": hashlib.sha256(
            env.read_bytes() if env.is_file() else b"").hexdigest()} or not env.is_file():
        raise RegistrationRefused("environment.json does not re-hash to the driver ledger's record of it")
    if pending_walk.status(ledger) is None:
        raise RegistrationRefused("the driver ledger records no pending native cross-check: not an acceptance walk")


def _records_problems(base: Path, entry: dict, ledger: dict) -> None:
    """check.json and grade.json are exactly their writers' bytes for a pending walk."""
    import run as run_mod
    import walk_runner
    try:
        doc = pending_walk.check_doc(entry["walk"], ledger)
    except ValueError as e:
        raise RegistrationRefused(str(e)) from None
    want_check = (json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    if (base / walk_runner.CHECK_FILE).read_bytes() != want_check:
        raise RegistrationRefused("check.json is not the walk runner's pending check record")
    if (base / mode_binding.WALK_GRADE).read_bytes() != run_mod.walk_grade_bytes(run_mod.grade_walk(entry, base)):
        raise RegistrationRefused("grade.json is not run.grade_walk's pending document")


def _journal_problems(base: Path, entry: dict, ledger: dict, harness: str = HARNESS) -> None:
    """Each turn's launch journal, validated by vendor_provenance.launch_facts against the registered invocation:
    the take container from launch.json, model, mode and sent line from the ledger, the resumed session from turn 1's
    init. The working folder and the stream's host folder are the journals' own (one value across every turn); the
    stream's name must be its turn's."""
    try:
        take_id = json.loads((base / LAUNCH_FILE).read_bytes())["take_id"]
        first = json.loads((base / "turn-1.jsonl").read_text(encoding="utf-8").splitlines()[0])
        session = PROFILES[harness]["session_of"](first)
    except (OSError, ValueError, KeyError, TypeError, IndexError) as e:
        raise RegistrationRefused(f"launch.json or turn 1's init cannot be read: {e}") from None
    cwds, dirs = set(), set()
    for k in range(1, len(ledger["streams"]) + 1):
        path = base / f"turn-{k}.jsonl.launch.json"
        try:
            journal = json.loads(path.read_bytes())
            stream = journal["stream"]
        except (OSError, ValueError, KeyError, TypeError) as e:
            raise RegistrationRefused(f"turn {k}'s launch journal cannot be read: {e}") from None
        if not isinstance(stream, str) or os.path.basename(stream) != f"turn-{k}.jsonl":
            raise RegistrationRefused(f"turn {k}'s launch journal names another stream")
        cwds.add(journal.get("cwd"))
        dirs.add(os.path.dirname(stream))
        want = {"harness": harness, "container_id": take_id, "model": entry["model"],
                "mode": ledger["permission_mode_passed"], "run_tree": journal.get("cwd"), "stream": stream,
                "sent": ledger["turns"][k - 1]["sent"],
                "vendor_session_id": "first-turn" if k == 1 else session, "ordinal": k}
        try:
            vp.launch_facts(journal, want)
        except vp.ProvenanceRefused as e:
            raise RegistrationRefused(f"turn {k}'s launch journal fails launch_facts: {e}") from None
    if len(cwds) != 1 or len(dirs) != 1:
        raise RegistrationRefused("the launch journals do not share one working folder and one stream folder")


def _regrade_problems(base: Path, walk: str, study: Path, harness: str = HARNESS) -> None:
    """Batch-8 review finding 4: a regrade.json the walk carries must re-derive (walk_regrade.regrade_doc from the
    committed bytes, through the candidate reader) to its exact bytes; anything else refuses."""
    import walk_regrade
    path = base / walk_regrade.REGRADE_FILE
    if not path.is_file():
        return
    try:
        again = walk_regrade.regrade_bytes(walk_regrade.regrade_doc(walk, study,
                                                                    readers={harness: PROFILES[harness]["reader"]}))
    except walk_regrade.RegradeRefused as e:
        raise RegistrationRefused(f"the walk's regrade.json cannot be re-derived: {e}") from None
    if again != path.read_bytes():
        raise RegistrationRefused("the walk's regrade.json does not re-derive to its bytes")


def acceptance_problems(record, study: Path = HERE, harness: str = HARNESS) -> None:
    """Raise RegistrationRefused unless `record` (read from HEAD) binds a committed recorded walk, as above, for the
    harness's profile (PROFILES: Gemini, and Codex since Codex slice 3)."""
    prof = PROFILES[harness]
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
    if record["harness"] != harness or record["cli_version"] != prof["cli"]:
        raise RegistrationRefused(f"the record is for {harness} {prof['cli']} only")
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
    review_ref = _ref({"file": review["file"], "sha256": review["sha256"]}, prof["review"], "review")
    review_rel = _rel(prefix, f"{READER_DIR}/{review_ref['file']}")
    _clean(root, [register_rel, walk_rel, review_rel] + [_rel(prefix, n) for n in prof["sources"]])
    if record["reader_sources_sha256"] != reader_sources_sha256(committed=lambda n: _show(root, _rel(prefix, n)),
                                                                sources=prof["sources"]):
        raise RegistrationRefused("the reader's sources changed since the record: a new acceptance is needed")
    try:
        register = json.loads(_show(root, register_rel), object_pairs_hook=walk_register.no_duplicate_keys)
        entries = [e for e in register["walks"] if isinstance(e, dict) and e.get("walk") == walk]
    except (ValueError, KeyError, TypeError, walk_register.DuplicateKey) as e:
        raise RegistrationRefused(f"the committed rehearsals register cannot be read: {e}") from None
    if len(entries) != 1 or entries[0].get("arm") != prof["arm"]:
        raise RegistrationRefused(f"walk {walk!r} is not one committed arm-{prof['arm']} walk of the rehearsals "
                                  f"register")
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp) / walk
        _materialize(root, walk_rel, base)
        try:
            drive.walk_files(base)
        except drive.DriveRefused as e:
            raise RegistrationRefused(f"the committed walk fails drive.walk_files: {e}") from None
        walk_commit = _walk_commit(root, walk_rel, register_rel, entries[0])
        try:
            ledger = json.loads((base / drive.LEDGER_FILE).read_bytes())
        except (OSError, ValueError) as e:
            raise RegistrationRefused(f"the walk's driver ledger cannot be read: {e}") from None
        _ledger_problems(ledger, entries[0], base, harness)
        _records_problems(base, entries[0], ledger)
        _journal_problems(base, entries[0], ledger, harness)
        _regrade_problems(base, walk, study, harness)
        snaps, ledger_streams = list(ledger["native_snapshots"]), list(ledger["streams"])
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
        got = prof["check"](native, streams, ledger)
        join = record["join"]
        if got["status"] != "PASS" or join != {"status": "PASS", "interactions": got["interactions"]}:
            raise RegistrationRefused(f"the join does not re-derive as recorded: {got.get('why') or got['interactions']}")
        floor = floor_problem(got["shapes"], prof["floor"])
        if floor:
            raise RegistrationRefused(floor)
        try:
            if harness == HARNESS:
                gemini_snapshot_prefixes(base / "session", [dict(s) for s in snaps])
            vp.session_history_facts(harness, base / "session", [dict(s) for s in snaps],
                                     readers={harness: prof["reader"]})
        except (vp.ProvenanceRefused, vp.ProvenancePending) as e:
            raise RegistrationRefused(f"the snapshot-history join over the ledger's snapshots refuses: {e}") from None
        if len(snaps) < 2:
            raise RegistrationRefused("the snapshot-history join needs a resume: at least 2 retained snapshots")
        metadata = prof["metadata"](native)
    review_text = _hashed(_show(root, review_rel), review_ref, "review")
    for what, text in (("the native session metadata", json.dumps(metadata, sort_keys=True)),
                       ("the register entry", json.dumps(entries[0], sort_keys=True)),
                       ("the review", review_text.decode("utf-8", errors="replace")),
                       ("the acceptance record", json.dumps(record, sort_keys=True))):
        if SYNTHETIC.search(text):
            raise RegistrationRefused(f"{what} carries a synthetic marker: never acceptance evidence")


def _gemini_metadata(native: bytes):
    try:
        return replay_mod.replay(native)["metadata"]
    except replay_mod.ReplayRefused as e:
        raise RegistrationRefused(f"the native session metadata cannot be read: {e}") from None


def _codex_metadata(native: bytes):
    """The rollout's session_meta payload (its first line), scanned for a synthetic marker."""
    try:
        return json.loads(native.decode("utf-8").split("\n", 1)[0])["payload"]
    except (ValueError, KeyError, TypeError, UnicodeError) as e:
        raise RegistrationRefused(f"the rollout's session_meta cannot be read: {e}") from None


def _codex_thread(first: dict):
    return first.get("thread_id") if first.get("type") == "thread.started" else None


PROFILES = {
    "gemini": {"cli": PINNED_CLI, "arm": ARM, "acceptance": ACCEPTANCE_FILE, "review": _REVIEW_FILE,
               "reader": gemini_reader, "sources": READER_SOURCES, "floor": ACCEPTANCE_FLOOR,
               "check": lambda native, streams, ledger: check_session(native, streams),
               "session_of": lambda first: first.get("session_id") if first.get("type") == "init" else None,
               "ledger_keys": LEDGER_KEYS, "metadata": _gemini_metadata},
    # Codex slice 3 (arm O, glitch-06's ruling): the rollout reader and its shared join; a Codex ledger also records
    # each turn's served-model evidence (served_model, D-INT-2).
    "codex": {"cli": CODEX_PINNED_CLI, "arm": "O", "acceptance": CODEX_ACCEPTANCE_FILE,
              "review": re.compile(r"codex-review\.md"), "reader": codex_reader, "sources": CODEX_SOURCES,
              "floor": CODEX_FLOOR,
              "check": codex_check,
              "session_of": _codex_thread, "ledger_keys": LEDGER_KEYS + ("served_model",),
              "metadata": _codex_metadata},
}


def production_readers(study: Path = HERE) -> dict:
    """The production native-reader registry, per harness profile: {} without any acceptance record in the working
    tree (no git is run, so a take's driver pays nothing; a committed record deleted from disk also reads absent, which
    keeps that harness's takes pending, the fail-closed side); each harness whose committed, clean record holds maps to
    its reader; any record that exists and does not hold raises RegistrationRefused."""
    study = Path(study)
    out = {}
    for harness, prof in PROFILES.items():
        path = study / prof["acceptance"]
        if not (path.exists() or path.is_symlink()):
            continue
        root, prefix = _repo(study)
        if root is None:
            raise RegistrationRefused("an acceptance record outside a git repository is never read")
        rel = _rel(prefix, prof["acceptance"])
        if not _in_head(root, rel):
            raise RegistrationRefused("the acceptance record is uncommitted: only a committed record is read")
        _clean(root, [rel])
        try:
            record = json.loads(_show(root, rel))
        except (ValueError, UnicodeError) as e:
            raise RegistrationRefused(f"the acceptance record is not JSON: {e}") from None
        acceptance_problems(record, study, harness)
        out[harness] = prof["reader"]
    return out


def acceptance_provenance(study: Path = HERE, harness: str = HARNESS) -> dict:
    """Who committed the record and the review, and when HEAD stands: printed by `verify`, never a trust input."""
    study = Path(study)
    root, prefix = _repo(study)
    if root is None:
        raise RegistrationRefused("the study is not in a git repository")

    def last(rel):
        line = _git(root, "log", "-1", "--format=%H%x00%an", "HEAD", "--", rel)
        return line.split("\0") if line else [None, None]

    acceptance = PROFILES[harness]["acceptance"]
    commit, author = last(_rel(prefix, acceptance))
    reviews = _git(root, "log", "--format=%H", "HEAD", "--",
                   _rel(prefix, f"{READER_DIR}/{harness}-review.md")).splitlines()
    walk = walk_author = walk_committer = None
    try:
        walk = json.loads(_show(root, _rel(prefix, acceptance))).get("walk")
    except (RegistrationRefused, ValueError, AttributeError):
        walk = None
    if isinstance(walk, str) and walk_register.WALK_ID.fullmatch(walk):
        log = _git(root, "log", "--format=%H%x00%an <%ae>%x00%cn <%ce>", "HEAD", "--",
                   _rel(prefix, f"{mode_binding.WALKS_DIR}/{walk}/driver-ledger.json")).splitlines()
        if log:
            walk, walk_author, walk_committer = log[-1].split("\0")
    return {"acceptance_commit": commit, "acceptance_author": author,
            "review_commit": reviews[0] if reviews else None, "walk_commit": walk if walk_author else None,
            "walk_author": walk_author, "walk_committer": walk_committer, "head": _git(root, "rev-parse", "HEAD")}


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
              f"{prov['acceptance_author']}; review commit {prov['review_commit']}; walk commit {prov['walk_commit']} "
              f"authored by {prov['walk_author']}, committed by {prov['walk_committer']}; HEAD {prov['head']}. The "
              f"gates are consistency checks over producer-written bytes and cannot tell a consistent fabrication "
              f"from a real walk; the guarantee against fabrication is procedural: the acceptance commit, made in "
              f"Javier's own window after the independent review of the real walk")
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
