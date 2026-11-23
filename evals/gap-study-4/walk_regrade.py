#!/usr/bin/env python3
"""Live harness: regrade a pending vendor walk once its native-session reader is registered.

    python3 evals/gap-study-4/walk_regrade.py --walk <id>      write rehearsals/<id>/regrade.json (refuses if present)
    commit_regrade(<id>, secrets=..., rules_scanner=...)        scan and commit exactly that file (REGRADE_SUBJECT),
                                                                with the walk runner's own secrets and rules scanner
    python3 evals/gap-study-4/walk_regrade.py --check          every committed regrade.json re-derives to its bytes

Registration review finding 2 (glitch-06, 14 Oct 2026). A walk committed while its native cross-check was pending
(pending_walk.py) keeps its own commit and records. After a reader is registered, the cross-check and the grade are
re-derived deterministically from that walk's COMMITTED bytes (git show HEAD, never the working tree): no new take, no
container, no model. The result is a new record beside the walk's own, rehearsals/<walk>/regrade.json, which
supersedes its pending grade.json and is committed alone, under its own subject, by commit_regrade.

regrade_doc(walk) refuses (RegradeRefused) unless the walk is registered, its committed grade.json is the pending
document, its harness has a regrade road (Gemini; Codex comes with its registration slice) and a reader is
registered (production_readers, or `readers` in tests). Codex walks regrade the same way since Codex slice 3, through
drive.codex_cross_check. The document:
  {"schema": 1, "walk", "walk_commit": the commit that added its driver ledger, "supersedes": "grade.json",
   "cross_check": drive.gemini_cross_check over the committed snapshots and streams, the one shared join,
   "graded", and either "row" and "grade" (run.walk_row and run.grade_walk_folder, or `grade` in tests) when the
   cross-check agreed, or "why" when it refused}.
A grader that raises refuses the regrade: no partial record is written. Before any grader, run.vendor_admission (lane
vendor-admission T1) is handed the regrade's own cross-check and registry: anything but exactly the agreed shape, or a
registry without the walk's harness, refuses. The checker's reading and route are not
re-derived here (they need the design view and its constants); check.json keeps saying the checker never ran, and the
walk counts only once a recheck (below) reads it (lane vendor-admission T4 P5, R-9).

THE RECHECK (glitch-6b's scheduled-wakeup ruling, 15 Oct 2026; freeze-gate ruling line 51, required before that
amendment counts). A Claude Code walk whose checker DID run, checked under constants since superseded, is re-checked
from its COMMITTED records, with no live take, no container and no model. Lane vendor-admission T4 P5, R-9: so is a
codex or gemini walk, through check_take.checker_for's entry and side on its vendor view; a pending vendor walk's first
recheck runs the checker for the first time, admitted only on a verified graded-true regrade whose cross-check it
takes, and supersedes the pending check.json with `was` carrying no reasons and no digest:

    python3 evals/gap-study-4/walk_regrade.py --recheck <id> --home H --temp-root T --checkout C
                            write rehearsals/<id>/recheck-<n>.json, n one past the walk's committed rechecks
    commit_recheck(<id>, <n>, secrets=..., rules_scanner=...)   scan and commit exactly that file (RECHECK_SUBJECT)

recheck_doc(walk, n, machine=...) reads the walk folder at HEAD, refuses unless every file the walk commit added is
byte-identical at HEAD (a record edited after its walk commit is a tamper, refused) and its check.json is
walk_runner.check_record's document with the checker run (or, for a vendor walk, the pending document with a verified
graded-true regrade), then runs the same checker the driver ran (drive.take_checker, records="walks": checker_for's
entry on the committed transcript, check4_walk or the vendor entries' check4_walk_vendor, readers-disagree on a
non-empty cross-check) against the design view built now (check_take.design_view with the constants in force, the
routing pin and the walk's run tree; a vendor row's vendor view). The machine the walk ran on is named, never
guessed: `machine` is exactly {home, temp_root, checkout}, the checker's CHECK_HOME, CHECK_TEMP and CHECKOUT_REPO while
it reads, and the run tree is temp_root/neutral_name(walk_session_id(walk)), as drive.run_tree_path builds it on that
machine. The document {"schema": 1, "walk", "n", "walk_commit", "supersedes" (check.json, or recheck-<n-1>.json),
"machine", "run_tree", "checker_constants_sha256", "checker_reasons", "was" (the superseded file's digest and reasons),
"change" (digest from and to, reasons added and removed), "route": null} never edits the old check.json or an
earlier recheck: each is a new file, append-only by its ordinal. Limits, named: the route is not re-derived (the
routing records the driver folds from the live turns and the box are not committed), so `route` is null; the
checker's events are not recorded (review F: check.json's outside_reach adds the commit scan's count, and the events
depend on the machine's home and checkout, which are named, not bound to a recorded fact); the checker's interpreter prefixes and checkout_roots' `~` spellings are the RECHECKING machine's, so
a recheck run anywhere but the walk's machine is read for any reason change before it is accepted.
recheck_state(base, walk) gives the latest committed recheck only when it re-derives to its exact bytes. Coverage
(glitch-6b's recheck-coverage ruling, 15 Oct 2026): write_recheck also appends a register entry {walk, file, n,
checker_constants_sha256, sha256} (register schema 2), committed with the file by commit_recheck; and
pending_walk.checker_standing reads the walk's latest entry and its file, no git and no process (walk_plan's road),
never re-deriving it: that proof is this --check, in checks.d. --check
re-derives only each walk's LATEST recheck (review F: an earlier one was made under earlier constants and would never
re-derive again); every earlier one is checked for its shape and its place in the supersedes chain.
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

import mode_binding  # noqa: E402
import native_reader_registration as nrr  # noqa: E402
import pending_walk  # noqa: E402
import walk_register  # noqa: E402

REGRADE_FILE = walk_register.REGRADE_FILE
REGRADE_SUBJECT = walk_register.REGRADE_SUBJECT     # one spelling: walk_register's history check admits it
REGRADE_HARNESSES = ("gemini", "codex")      # Codex since Codex slice 3
RECHECK_PREFIX = "recheck-"
RECHECK_SUBJECT = walk_register.RECHECK_SUBJECT     # one spelling: walk_register's history check admits it
# Lane vendor-admission T4 P5, R-9 (a): the harnesses check_take.checker_for admits (claude-code's check4_walk, the
# vendor entries' check4_walk_vendor through their vendor view)
RECHECK_HARNESSES = ("claude-code", "codex", "gemini")
MACHINE_KEYS = ("checkout", "home", "temp_root")


class RegradeRefused(ValueError):
    """The walk cannot be regraded (or its regrade committed) from its committed bytes."""


def _walk_rel(prefix: str, walk: str) -> str:
    return nrr._rel(prefix, f"{mode_binding.WALKS_DIR}/{walk}")


def _repo(study: Path):
    root, prefix = nrr._repo(Path(study))
    if root is None:
        raise RegradeRefused("the study is not in a git repository: a regrade reads the committed tree")
    return root, prefix


def walk_commit(root: Path, walk_rel: str) -> str:
    """The commit that added the walk's driver ledger (its WalkRepo commit)."""
    got = nrr._git(root, "log", "--diff-filter=A", "--format=%H", "HEAD", "--", f"{walk_rel}/driver-ledger.json")
    commits = got.splitlines()
    if len(commits) != 1:
        raise RegradeRefused(f"{walk_rel}/driver-ledger.json was added by {len(commits)} commits, not one")
    return commits[0]


def regrade_doc(walk: str, study: Path = HERE, *, readers=None, grade=None) -> dict:
    import drive
    import run as run_mod
    study = Path(study)
    if not (isinstance(walk, str) and walk_register.WALK_ID.fullmatch(walk)):
        raise RegradeRefused(f"{walk!r} is not a walk id")
    root, prefix = _repo(study)
    walk_rel = _walk_rel(prefix, walk)
    register_rel = nrr._rel(prefix, f"{mode_binding.WALKS_DIR}/{walk_register.REGISTER_NAME}")
    try:
        register = json.loads(nrr._show(root, register_rel), object_pairs_hook=walk_register.no_duplicate_keys)
        entries = [e for e in register["walks"] if isinstance(e, dict) and e.get("walk") == walk]
    except (ValueError, KeyError, TypeError, walk_register.DuplicateKey, nrr.RegistrationRefused) as e:
        raise RegradeRefused(f"the committed rehearsals register cannot be read: {e}") from None
    if len(entries) != 1:
        raise RegradeRefused(f"walk {walk!r} is not registered once in the committed register")
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp) / walk
        materialize_walk(root, walk_rel, base)
        try:
            ledger = json.loads((base / drive.LEDGER_FILE).read_bytes())
            stored = json.loads((base / drive.WALK_GRADE).read_bytes())
        except (OSError, ValueError) as e:
            raise RegradeRefused(f"the committed walk's ledger or grade cannot be read: {e}") from None
        if stored != pending_walk.status(ledger):
            raise RegradeRefused("the committed walk is not a pending walk: its grade.json is not the pending document")
        harness = (ledger.get("agent") or {}).get("harness")
        if harness not in REGRADE_HARNESSES:
            raise RegradeRefused(f"no regrade road for harness {harness!r} yet")
        try:
            readers = nrr.production_readers(study) if readers is None else readers
        except nrr.RegistrationRefused as e:
            raise RegradeRefused(f"the reader registration refuses: {e}") from None
        refs = list(ledger.get("native_snapshots") or [])
        cross = (drive.gemini_cross_check(base, refs, len(ledger.get("streams") or []), readers=readers)
                 if harness == "gemini" else
                 drive.codex_cross_check(base, refs, [t.get("exit") for t in ledger.get("turns") or []],
                                         sent=[t.get("sent") for t in ledger.get("turns") or []],
                                         model=ledger.get("model_requested"), readers=readers))
        if cross["status"] == "pending":
            raise RegradeRefused(f"no registered reader: {cross['why']}")
        doc = {"schema": 1, "walk": walk, "walk_commit": walk_commit(root, walk_rel), "supersedes": drive.WALK_GRADE,
               "cross_check": cross}
        if cross["status"] != "agreed":
            return dict(doc, graded=False, why=f"not graded, because the native cross-check refused: {cross['why']}")
        admitted(harness, readers, cross)
        row = run_mod.walk_row(entries[0], ledger)
        try:
            got = (run_mod.grade_walk_folder if grade is None else grade)(row, base)
        except Exception as e:  # noqa: BLE001 - a grader that cannot grade the walk refuses the whole regrade
            raise RegradeRefused(f"the grader refused the walk: {type(e).__name__}: {e}") from None
        return dict(doc, graded=True, row=row, grade=got)


def admitted(harness, readers, cross) -> None:
    """Lane vendor-admission T1: run.vendor_admission on the regrade's OWN cross-check and the registry it holds (the
    pending walk's ledger still says pending); RegradeRefused naming why, before any grader."""
    import run as run_mod
    try:
        run_mod.vendor_admission(harness, readers, cross)
    except run_mod.VendorAdmissionRefused as e:
        raise RegradeRefused(f"vendor admission refuses the regrade: {e}") from None


def regrade_bytes(doc: dict) -> bytes:
    return (json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def write_regrade(walk: str, study: Path = HERE, **kw) -> Path:
    path = Path(study) / mode_binding.WALKS_DIR / walk / REGRADE_FILE
    if os.path.lexists(path):
        raise RegradeRefused(f"{path} exists: a regrade is written once; a later one needs its own ruling")
    data = regrade_bytes(regrade_doc(walk, study, **kw))
    path.write_bytes(data)
    return path


def commit_regrade(walk: str, study: Path = HERE, *, secrets, rules_scanner, holdout_matcher=None) -> str:
    """Scan the walk's regrade.json (box/scan_record, kind ledger, as WalkRepo scans a walk's ledgers) and commit it
    alone under REGRADE_SUBJECT. Refuses when anything else is staged, the scan refuses, or the staged blob is not the
    scanned bytes."""
    return _commit_one(walk, REGRADE_FILE, REGRADE_SUBJECT, study, secrets=secrets, rules_scanner=rules_scanner,
                       holdout_matcher=holdout_matcher)


def _commit_one(walk: str, name: str, subject: str, study: Path, *, secrets, rules_scanner, holdout_matcher,
                with_register: bool = False) -> str:
    """Scan and commit exactly the walk's new `name` (and, for a recheck, the register beside it), under `subject`."""
    import takes as takes_mod
    from box import scan_record
    study = Path(study)
    root, prefix = _repo(study)
    rel = f"{_walk_rel(prefix, walk)}/{name}"
    path = root / rel
    if path.is_symlink() or not path.is_file():
        raise RegradeRefused(f"{rel} is not a regular file")
    if nrr._in_head(root, rel):
        raise RegradeRefused(f"{rel} is already committed")
    if nrr._git(root, "diff", "--cached", "--name-only"):
        raise RegradeRefused("the index already holds staged changes; a regrade is committed alone")
    takes_mod.require_commit_identity(root)
    rels = [rel] + ([nrr._rel(prefix, f"{mode_binding.WALKS_DIR}/{walk_register.REGISTER_NAME}")]
                    if with_register else [])
    scan = scan_record.scan([(str(root / r), "ledger") for r in rels], list(secrets()), rules_scanner=rules_scanner,
                            holdout_matcher=holdout_matcher)
    if not scan_record.passed(scan):
        raise RegradeRefused("the commit scan refused the regrade: " + "; ".join(r["why"] for r in scan["refused"]))
    nrr._git(root, "add", "--", *rels)
    staged = nrr._git(root, "diff", "--cached", "--name-only").splitlines()
    after = {r["path"]: r["sha256_after"] for r in scan["files"]}
    if sorted(staged) != sorted(rels) or any(
            after.get(str(root / r)) != hashlib.sha256(nrr._git(root, "show", f":{r}", binary=True)).hexdigest()
            for r in rels):
        nrr._git(root, "reset", "-q", "--", *rels)
        raise RegradeRefused(f"the staged files are not exactly the scanned {rels}: {staged}")
    with tempfile.NamedTemporaryFile("w", suffix=".msg", delete=False) as fh:
        fh.write(subject + "\n")
        msg = fh.name
    try:
        nrr._git(root, "commit", "-q", "-F", msg)
    finally:
        os.unlink(msg)
    return nrr._git(root, "rev-parse", "HEAD")


def _vendor(harness) -> bool:
    """Lane vendor-admission T4 P5: a harness whose walks the vendor side reads (check_take.checker_for's vendor
    entries); every other harness, None included, is read by Claude Code's readers, as before."""
    import check_take as ct
    return harness in ct.VENDOR_CHECKER_CONSTANTS and harness in ct.CHECKER_ENTRIES


def nudge_count_problems(check: dict, transcript: Path, harness=None) -> list:
    """Review r6 MINOR 2 (glitch-b5, 16 Oct 2026): check.json's no_output_nudges, where it is a count, is check_take's
    count of the committed transcript; a mismatch is named. A null (an older check.json) is not re-derived. A vendor
    walk's count (`harness`, its ledger's agent.harness; T4 P5) is the vendor side's reading of its folder."""
    import check_take as ct
    want = check.get("no_output_nudges") if isinstance(check, dict) else None
    if not pending_walk.valid_nudge_count(want):          # null (or a shape check_keys_ok refuses) is not re-derived
        return []
    got = ct.vendor_side_readings(Path(transcript), harness)[0] if _vendor(harness) else \
        ct.no_output_nudges(Path(transcript))
    if got != want:
        return [f"check.json's no_output_nudges is {want} and the committed transcript carries {got}"]
    return []


def agent_summary_problems(check: dict, transcript: Path, harness=None) -> list:
    """The Agent parity ruling, part 6: check.json's agent_calls and subagents, where present, are check_take's reading
    of the committed transcript and the turn streams beside it; a mismatch is named. A check.json without them (written
    before the ruling) is not re-derived. A vendor walk's (`harness`; T4 P5) is the vendor side's reading."""
    import check_take as ct
    if not isinstance(check, dict) or check.get("agent_calls") is None:
        return []
    derived = ct.vendor_side_readings(Path(transcript), harness)[1] if _vendor(harness) else \
        ct.agent_summary(Path(transcript))
    # Lane freeze-gates-fix (glitch-f1's ruling (2), Wed 21 Oct 2026, under Javier's standing delegation): compare only
    # the fields the walk's checker version wrote. nested_cli_calls came with W-3b (9e57ce79); a check.json written
    # before it has no such KEY (20261016c's 28 walks, w137-w164). Its absence passes only when the derived count is
    # 0, else it is named; a key present with null still compares, and is red.
    out = []
    if "nested_cli_calls" not in check:
        derived = dict(derived)
        nested = derived.pop("nested_cli_calls", None)
        if nested != 0:
            out.append(f"check.json was written before nested_cli_calls was recorded and the committed walk folder "
                       f"carries {nested!r} nested agent-CLI call(s); only 0 passes unrecorded")
    recorded = {"agent_calls": check.get("agent_calls"), "subagents": check.get("subagents")}
    if "nested_cli_calls" in check:
        recorded["nested_cli_calls"] = check.get("nested_cli_calls")
    if derived != recorded:
        rec_sub = recorded["subagents"] if isinstance(recorded["subagents"], dict) else {}
        fields = [k for k in ("agent_calls", "nested_cli_calls") if k in recorded and recorded[k] != derived.get(k)] + \
            ([f"subagents.{k}" for k in sorted(set(rec_sub) | set(derived["subagents"]))
              if rec_sub.get(k) != derived["subagents"].get(k)] if isinstance(recorded["subagents"], dict)
             else ["subagents"])                  # review r13 NIT 1: every mismatched field named
        named = ", ".join(f"{f} (recorded {_field(recorded, f)!r}, derived {_field(derived, f)!r})" for f in fields)
        return out + [f"check.json's agent_calls and subagents are not the committed walk folder's reading: "
                      f"{named}"[:600]]
    return out


def _field(doc: dict, dotted: str):
    for k in dotted.split("."):
        doc = doc.get(k) if isinstance(doc, dict) else None
    return doc


NOT_A_REPOSITORY = ("{study} is not inside a git repository: a regrade, a recheck and a count are re-derived from "
                    "committed bytes, so nothing here can be checked, and that is not a pass")


def new_counts() -> dict:
    return {"walks": 0, "regrades": 0, "recheck_walks": 0, "counts": 0, "pending": 0, "pending_unregraded": [], "unnudged": 0}


def regrade_report(study: Path = HERE, *, readers=None, grade=None) -> tuple[list, dict]:
    """(problems, counts): regrade_problems' reading and how much of it was re-derived (pre-freeze review 1, m7: the
    gate printed a bare ok having re-derived nothing, and returned [] outside a git repository). counts is
    {"walks": walks listed at HEAD, "regrades": regrade.json files re-derived, "recheck_walks": walks whose recheck
    chain was read, "counts": check.json counts re-derived from their transcripts, "pending": walks whose committed
    grade.json is the pending document or does not read as one object, "pending_unregraded": the pending walks with no regrade.json}."""
    counts = new_counts()
    return regrade_problems(study, readers=readers, grade=grade, counts=counts), counts


def regrade_problems(study: Path = HERE, *, readers=None, grade=None, counts=None) -> list:
    """Every committed regrade.json must re-derive to its exact bytes; `counts` (new_counts()), when given, is filled
    with how much was re-derived (regrade_report)."""
    study = Path(study)
    counts = new_counts() if counts is None else counts
    root, prefix = nrr._repo(study)
    if root is None:
        return [NOT_A_REPOSITORY.format(study=study)]
    walks = nrr._rel(prefix, mode_binding.WALKS_DIR)
    listed = nrr._git(root, "ls-tree", "-r", "--name-only", "HEAD", "--", walks + "/").splitlines()
    out = []
    names = {tuple(rel[len(walks) + 1:].split("/")) for rel in listed}
    counts["walks"] = len({n[0] for n in names if len(n) == 2})
    for walk, name in sorted(n for n in names if len(n) == 2 and n[1] == "grade.json"):
        try:
            doc = json.loads(nrr._show(root, f"{walks}/{walk}/grade.json"))
        except (ValueError, nrr.RegistrationRefused):
            doc = None          # the review of 53d0e9af, NIT 7: an unreadable grade counts as pending, never skipped
        if not isinstance(doc, dict) or doc.get("status") == pending_walk.PENDING:
            counts["pending"] += 1
            if (walk, REGRADE_FILE) not in names:
                counts["pending_unregraded"].append(walk)
    for rel in listed:
        parts = rel[len(walks) + 1:].split("/")
        if len(parts) != 2 or parts[1] != REGRADE_FILE:
            continue
        counts["regrades"] += 1
        try:
            again = regrade_bytes(regrade_doc(parts[0], study, readers=readers, grade=grade))
        except RegradeRefused as e:
            out.append(f"walk {parts[0]!r}: its regrade cannot be re-derived: {e}")
            continue
        if again != nrr._show(root, rel):
            out.append(f"walk {parts[0]!r}: {REGRADE_FILE} differs from re-deriving it")
    by_walk: dict = {}
    for rel in listed:
        parts = rel[len(walks) + 1:].split("/")
        if len(parts) == 2 and parts[1].startswith(RECHECK_PREFIX):
            by_walk.setdefault(parts[0], []).append(parts[1])
    for walk, chain in sorted(by_walk.items()):
        counts["recheck_walks"] += 1
        out += recheck_chain_problems(root, prefix, walk, chain, study, readers=readers, grade=grade)
    out += register_recheck_problems(root, prefix, by_walk)
    for rel in listed:                    # review r6 MINOR 2: every committed count re-derived from its transcript
        parts = rel[len(walks) + 1:].split("/")
        if len(parts) != 2 or parts[1] != "check.json":
            continue
        try:
            check = json.loads(nrr._show(root, rel))
        except (ValueError, nrr.RegistrationRefused):
            continue                      # check.json's own shape is pending_walk's and the register's to judge
        if not isinstance(check, dict) or not isinstance(check.get("no_output_nudges"), int):
            counts["unnudged"] += 1; continue     # pre-freeze review 3, m9 (lane fold3/m1): counted and printed
        with tempfile.TemporaryDirectory() as tmp:  # review r12 R12-1: the whole walk folder, as recheck_doc reads it
            base = Path(tmp) / parts[0]
            try:
                materialize_walk(root, f"{walks}/{parts[0]}", base)
            except RegradeRefused as e:
                out.append(f"walk {parts[0]!r}: its nudge count cannot be re-derived: {e}")
                continue
            path = base / "transcript.jsonl"
            if not path.is_file():
                out.append(f"walk {parts[0]!r}: its nudge count cannot be re-derived: the committed walk has no "
                           f"transcript.jsonl")
                continue
            harness = pending_walk.walk_harness(Path(tmp), parts[0])      # T4 P5: the vendor side's reading
            counts["counts"] += 1
            out += [f"walk {parts[0]!r}: {p}" for p in nudge_count_problems(check, path, harness)]
            out += [f"walk {parts[0]!r}: {p}" for p in agent_summary_problems(check, path, harness)]
    return out


def gate_problems(problems: list, counts: dict) -> list:
    """What --check refuses beyond regrade_problems (m7): a register of walks of which nothing was re-derived (the gate
    would be vacuous), and, once any regrade exists, a pending walk with none (the regrade is all or nothing, so a
    partial one never reads green)."""
    out = list(problems)
    derived = counts["regrades"] + counts["recheck_walks"] + counts["counts"]
    if counts["walks"] and not derived:
        out.append(f"{counts['walks']} walk(s) are committed and nothing was re-derived: not a pass")
    if counts["regrades"]:
        out += [f"walk {w!r}: its committed grade.json is pending and it has no {REGRADE_FILE}, though the regrade "
                f"has begun" for w in counts["pending_unregraded"]]
    return out


def counts_line(counts: dict) -> str:
    return (f"re-derived {counts['regrades']} {REGRADE_FILE} file(s), {counts['recheck_walks']} walk(s)' recheck "
            f"chains and {counts['counts']} check.json count(s), over {counts['walks']} committed walk(s); "
            f"{counts['pending']} walk(s) graded pending, {len(counts['pending_unregraded'])} of them with no "
            f"{REGRADE_FILE}; {counts.get('unnudged', 0)} check.json file(s) carry no integer count to re-derive (not read)")


def materialize_walk(root, walk_rel: str, into: Path) -> None:
    """The committed walk folder at HEAD (every blob: the transcript, the turn streams, subagents/ and its metas),
    written under `into`: the one road regrade_doc, recheck_doc and regrade_problems read a walk by (review r12
    R12-1), so no reader re-derives from a partial folder."""
    try:
        nrr._materialize(root, walk_rel, into)
    except nrr.RegistrationRefused as e:
        raise RegradeRefused(str(e)) from None


def register_recheck_problems(root, prefix, by_walk: dict) -> list:
    """The register at HEAD names every committed recheck, each with its file's sha256 at HEAD, and nothing else."""
    reg_rel = nrr._rel(prefix, f"{mode_binding.WALKS_DIR}/{walk_register.REGISTER_NAME}")
    try:
        reg = json.loads(nrr._show(root, reg_rel), object_pairs_hook=walk_register.no_duplicate_keys)
    except (ValueError, nrr.RegistrationRefused, walk_register.DuplicateKey) as e:
        return [f"the register cannot be read at HEAD: {e}"] if by_walk else []
    named = {(e.get("walk"), e.get("file")): e for e in walk_register.rechecks_of(reg) if isinstance(e, dict)}
    out = []
    for walk, names in sorted(by_walk.items()):
        for name in names:
            e = named.pop((walk, name), None)
            if e is None:
                out.append(f"walk {walk!r}: {name} has no recheck entry in the register")
                continue
            got = hashlib.sha256(nrr._show(root, f"{_walk_rel(prefix, walk)}/{name}")).hexdigest()
            if e.get("sha256") != got:
                out.append(f"walk {walk!r}: {name} is not the bytes its register entry names")
    out += [f"walk {w!r}: the register names {f}, which HEAD does not hold" for (w, f) in sorted(named)]
    return out


def recheck_chain_problems(root, prefix, walk: str, names, study, *, readers=None, grade=None) -> list:
    """One walk's rechecks: named 1..k; each earlier one's shape and supersedes link (its walk, its ordinal, the file
    before it); the latest re-derived to its exact bytes under the constants in force."""
    try:
        have = _committed_rechecks(names)
    except RegradeRefused as e:
        return [f"walk {walk!r}: {e}"]
    out = []
    for n in have:
        rel = f"{_walk_rel(prefix, walk)}/{recheck_name(n)}"
        try:
            raw = nrr._show(root, rel)
            doc = json.loads(raw)
            want = "check.json" if n == 1 else recheck_name(n - 1)
            if not isinstance(doc, dict) or set(doc) - {RECHECK_NUDGE_KEY, *RECHECK_AGENT_KEYS} != set(RECHECK_KEYS) or (doc["walk"], doc["n"], doc["supersedes"],
                                                                              doc["was"].get("file")) != (walk, n, want, want):
                out.append(f"walk {walk!r}: {recheck_name(n)} is not a recheck of ordinal {n} superseding {want}")
                continue
            if n == have[-1]:
                again = regrade_bytes(recheck_doc(walk, n, study, machine=doc["machine"], readers=readers,
                                                  grade=grade))
                if again != raw:
                    out.append(f"walk {walk!r}: {recheck_name(n)} differs from re-deriving it")
        except (RegradeRefused, ValueError, KeyError, TypeError, AttributeError, nrr.RegistrationRefused) as e:
            out.append(f"walk {walk!r}: {recheck_name(n)} cannot be read or re-derived: {e}")
    return out


RECHECK_KEYS = ("schema", "walk", "n", "walk_commit", "supersedes", "machine", "run_tree", "checker_constants_sha256",
                "checker_reasons", "route", "was", "change")
# review r7 MINOR 2 (glitch-b5, 16 Oct 2026): a recheck also carries check_take's count of the committed transcript; a
# recheck written before the fold lacks it, and either shape is a recheck's (re-deriving the latest one writes the key)
RECHECK_NUDGE_KEY = "no_output_nudges"
# glitch-b5's Agent parity ruling, part 6 (16 Oct 2026): a recheck also carries the Agent calls and sub-agent models,
# re-derived from the committed transcript and streams; a recheck written before it lacks them.
RECHECK_AGENT_KEYS = ("agent_calls", "subagents", "nested_cli_calls")    # + W-3b (glitch-b5, 16 Oct 2026)


# ---- the recheck (glitch-6b's scheduled-wakeup ruling, 15 Oct 2026) -------------------------------------------------

def recheck_name(n: int) -> str:
    if type(n) is not int or n < 1:
        raise RegradeRefused(f"a recheck's ordinal is a positive integer, not {n!r}")
    return f"{RECHECK_PREFIX}{n}.json"


def _committed_rechecks(names) -> list:
    """The ordinals of the recheck files among `names`; every recheck-* name is recheck-<n>.json and they run 1..k."""
    import re
    shape = re.compile(re.escape(RECHECK_PREFIX) + r"([1-9][0-9]*)\.json")
    odd = [x for x in names if x.startswith(RECHECK_PREFIX) and not shape.fullmatch(x)]
    if odd:
        raise RegradeRefused(f"recheck files not named recheck-<n>.json: {odd}")
    got = sorted(int(shape.fullmatch(x).group(1)) for x in names if shape.fullmatch(x))
    if got != list(range(1, len(got) + 1)):
        raise RegradeRefused(f"the walk's rechecks are {got}, not 1..{len(got)}")
    return got


def _machine(machine) -> dict:
    if not isinstance(machine, dict) or sorted(machine) != sorted(MACHINE_KEYS) or not all(
            isinstance(v, str) and v.startswith("/") and "\n" not in v for v in machine.values()):
        raise RegradeRefused(f"the walk's machine is named exactly as {list(MACHINE_KEYS)}, absolute paths; "
                             f"never guessed")
    return dict(machine)


def _untampered(root: Path, walk_rel: str, commit: str, names) -> None:
    """Every file the walk commit added is byte-identical at HEAD, and nothing but rechecks and regrade.json was added
    after it."""
    then = nrr._git(root, "ls-tree", "-r", commit, "--", walk_rel + "/").splitlines()
    now = nrr._git(root, "ls-tree", "-r", "HEAD", "--", walk_rel + "/").splitlines()
    then = {ln.split("\t", 1)[1]: ln.split("\t", 1)[0] for ln in then}
    now = {ln.split("\t", 1)[1]: ln.split("\t", 1)[0] for ln in now}
    changed = sorted(p for p in then if now.get(p) != then[p])
    if changed:
        raise RegradeRefused(f"the walk's records changed after its walk commit {commit[:12]}: {changed}; a committed "
                             f"record is never edited, so this walk is refused")
    later = sorted(p.rsplit("/", 1)[1] for p in now if p not in then)
    stray = [x for x in later if x != REGRADE_FILE and not x.startswith(RECHECK_PREFIX)]
    if stray:
        raise RegradeRefused(f"the walk folder gained {stray} after its walk commit; only rechecks and a regrade may")


def _check_fields(doc, name) -> dict:
    """The superseded file's digest and reasons. check.json must be walk_runner's document with the checker run."""
    import pending_walk
    if name == "check.json" and (not pending_walk.check_keys_ok(doc)
                                 or doc.get("checked") is not True):
        raise RegradeRefused("the walk's check.json is not walk_runner's document with the checker run; a recheck "
                             "re-runs a checker that ran, never runs it first")
    if not isinstance(doc, dict) or not isinstance(doc.get("checker_reasons"), list):
        raise RegradeRefused(f"{name} carries no checker reasons")
    return {"file": name, "checker_constants_sha256": doc.get("checker_constants_sha256"),
            "checker_reasons": list(doc["checker_reasons"])}


def production_design(row, run_tree):
    """The design view a walk is re-checked against: check_take.design_view with the constants in force, routing's pin
    for the row and the walk's run tree; a vendor row's in its vendor view (check_take.checker_view, T4 P5), which
    the vendor entries read."""
    import batch
    import check_take as ct
    import routing
    return ct.checker_view(ct.design_view(row, pin=batch.expected_pin(row, routing.load_table()), run_tree=run_tree))


def production_checker(row, design, base: Path, ledger: dict) -> dict:
    """The driver's own checker (drive.take_checker, records="walks") on the committed folder."""
    import types
    import drive
    take = types.SimpleNamespace(folder=str(base), cross_check=ledger.get("cross_check"))
    return drive.take_checker(design_for=lambda r, t: design, records="walks")(row, take, [])


def _verified_regrade_cross(walk: str, study: Path, root, walk_rel: str, harness, *, readers, grade) -> list:
    """Lane vendor-admission T4 P5, R-9 (b): a pending vendor walk is re-checked only when its committed regrade.json
    re-derives to its exact bytes (regrade_doc from the committed walk) and grades it true; the cross-check the
    checker is handed is that regrade's, as drive.TakeDriver maps an agreed status ([]), never the ledger's pending
    one, after run.vendor_admission admits it (as regrade_doc does)."""
    rel = f"{walk_rel}/{REGRADE_FILE}"
    if not nrr._in_head(root, rel):
        raise RegradeRefused("the pending walk has no committed regrade.json: its checker never ran on a registered "
                             "reader's cross-check")
    doc = regrade_doc(walk, study, readers=readers, grade=grade)
    if regrade_bytes(doc) != nrr._show(root, rel):
        raise RegradeRefused("the pending walk's committed regrade.json does not re-derive to its bytes")
    if doc.get("graded") is not True or (doc.get("cross_check") or {}).get("status") != "agreed":
        raise RegradeRefused("the pending walk's verified regrade does not grade it: its native cross-check refused")
    try:
        readers = nrr.production_readers(study) if readers is None else readers
    except nrr.RegistrationRefused as e:
        raise RegradeRefused(f"the reader registration refuses: {e}") from None
    admitted(harness, readers, doc["cross_check"])
    return []


def recheck_doc(walk: str, n: int, study: Path = HERE, *, machine, design_for=None, checker=None, readers=None,
                grade=None) -> dict:
    """The recheck document of ordinal `n` for `walk` (module docstring). `design_for(row, run_tree)` defaults to
    check_take.design_view with routing's pin (a vendor row's vendor view); `checker(row, design, folder, ledger)` to
    production_checker. Lane vendor-admission T4 P5, R-9: a codex or gemini walk is re-checked through checker_for's
    entry and side; a pending vendor walk's first recheck admits its pending check.json only on a verified graded-true
    regrade, whose cross-check it takes (`readers` and `grade` are regrade_doc's), and supersedes check.json with
    `was` carrying no reasons and no digest."""
    import check_take as ct
    import drive
    import run as run_mod
    machine = _machine(machine)
    if not (isinstance(walk, str) and walk_register.WALK_ID.fullmatch(walk)):
        raise RegradeRefused(f"{walk!r} is not a walk id")
    name = recheck_name(n)
    root, prefix = _repo(Path(study))
    walk_rel = _walk_rel(prefix, walk)
    register_rel = nrr._rel(prefix, f"{mode_binding.WALKS_DIR}/{walk_register.REGISTER_NAME}")
    try:
        register = json.loads(nrr._show(root, register_rel), object_pairs_hook=walk_register.no_duplicate_keys)
        entries = [e for e in register["walks"] if isinstance(e, dict) and e.get("walk") == walk]
    except (ValueError, KeyError, TypeError, walk_register.DuplicateKey, nrr.RegistrationRefused) as e:
        raise RegradeRefused(f"the committed rehearsals register cannot be read: {e}") from None
    if len(entries) != 1:
        raise RegradeRefused(f"walk {walk!r} is not registered once in the committed register")
    commit = walk_commit(root, walk_rel)
    names = [p.rsplit("/", 1)[1] for p in nrr._git(root, "ls-tree", "-r", "--name-only", "HEAD", "--",
                                                    walk_rel + "/").splitlines()]
    _untampered(root, walk_rel, commit, names)
    have = _committed_rechecks(names)
    if n > len(have) + 1:
        raise RegradeRefused(f"recheck {n} would skip ordinal {len(have) + 1}")
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp) / walk
        materialize_walk(root, walk_rel, base)
        for later in range(n, len(have) + 1):             # the doc of ordinal n sees only what came before it
            (base / recheck_name(later)).unlink()
        try:
            ledger = json.loads((base / drive.LEDGER_FILE).read_bytes())
            old = json.loads((base / "check.json").read_bytes())
        except (OSError, ValueError) as e:
            raise RegradeRefused(f"the committed walk's ledger or check.json cannot be read: {e}") from None
        harness = (ledger.get("agent") or {}).get("harness") if isinstance(ledger, dict) else None
        vendor = harness != "claude-code" and _vendor(harness)
        try:
            pending = vendor and old == pending_walk.check_doc(walk, ledger)
        except ValueError:
            pending = False
        check_ledger = ledger
        if pending:                                   # R-9 (b): the regrade's cross-check, never the ledger's
            check_ledger = dict(ledger, cross_check=_verified_regrade_cross(walk, Path(study), root, walk_rel, harness,
                                                                            readers=readers, grade=grade))
        else:
            _check_fields(old, "check.json")
        prev_name = "check.json" if n == 1 else recheck_name(n - 1)
        if pending and n == 1:                        # the checker never ran: no reasons, no digest
            prev = {"file": "check.json", "checker_constants_sha256": None, "checker_reasons": []}
        else:
            try:
                prev = _check_fields(json.loads((base / prev_name).read_bytes()), prev_name)
            except (OSError, ValueError) as e:
                raise RegradeRefused(f"{prev_name} cannot be read: {e}") from None
        if harness not in RECHECK_HARNESSES:
            raise RegradeRefused(f"no recheck road for harness {harness!r}: only the harnesses check_take.checker_for "
                                 f"admits have record readers in check_take.py")
        if not (base / "transcript.jsonl").is_file():
            raise RegradeRefused("the committed walk has no transcript.jsonl")
        side = harness if vendor else None            # R-9 (b): a vendor walk's counts are the vendor side's
        forged = nudge_count_problems(old, base / "transcript.jsonl", side)      # review r6 MINOR 2
        if forged:
            raise RegradeRefused(forged[0])
        nudges = (ct.vendor_side_readings(base / "transcript.jsonl", harness)[0] if vendor
                  else ct.no_output_nudges(base / "transcript.jsonl"))  # review r7 MINOR 2: the recheck's own count
        forged = agent_summary_problems(old, base / "transcript.jsonl", side)    # the Agent parity ruling, part 6
        if forged:
            raise RegradeRefused(forged[0])
        agents = (ct.vendor_side_readings(base / "transcript.jsonl", harness)[1] if vendor
                  else ct.agent_summary(base / "transcript.jsonl"))
        try:
            row = dict(run_mod.walk_row(entries[0], ledger), walk=walk, slot=walk)
        except ValueError as e:
            raise RegradeRefused(f"the walk's row cannot be rebuilt: {e}") from None
        run_tree = machine["temp_root"].rstrip("/") + "/" + drive.neutral_name(ct.walk_session_id(walk))
        design_for = production_design if design_for is None else design_for
        saved = (ct.CHECK_HOME, ct.CHECK_TEMP, ct.CHECKOUT_REPO)
        ct.CHECK_HOME, ct.CHECK_TEMP, ct.CHECKOUT_REPO = (Path(machine["home"]), Path(machine["temp_root"]),
                                                          Path(machine["checkout"]))
        try:
            design = design_for(row, run_tree)
            digest = ct.vendor_design_constants_sha256(design) if vendor else ct.design_constants_sha256(design)
            if digest is None:
                raise RegradeRefused("the design view's constants or code have no digest (PENDING, incomplete, or a "
                                     "checker code file missing)")
            got = (production_checker if checker is None else checker)(row, design, base, check_ledger)
        except (ct.CheckRefused, KeyError) as e:
            raise RegradeRefused(f"the checker refused the walk: {type(e).__name__}: {e}") from None
        finally:
            ct.CHECK_HOME, ct.CHECK_TEMP, ct.CHECKOUT_REPO = saved
    reasons = list(got["checker_reasons"])
    return {"schema": 1, "walk": walk, "n": n, "walk_commit": commit, "supersedes": prev_name, "machine": machine,
            "run_tree": design.run_tree, "checker_constants_sha256": digest, "checker_reasons": reasons,
            "route": None, "no_output_nudges": nudges, "agent_calls": agents["agent_calls"],
            "subagents": agents["subagents"], "nested_cli_calls": agents["nested_cli_calls"],
            "was": prev,
            "change": {"checker_constants_sha256": [prev["checker_constants_sha256"], digest],
                       "reasons_added": sorted(set(reasons) - set(prev["checker_reasons"])),
                       "reasons_removed": sorted(set(prev["checker_reasons"]) - set(reasons))}}


def next_recheck(walk: str, study: Path = HERE) -> int:
    root, prefix = _repo(Path(study))
    walk_rel = _walk_rel(prefix, walk)
    names = [p.rsplit("/", 1)[1] for p in nrr._git(root, "ls-tree", "-r", "--name-only", "HEAD", "--",
                                                    walk_rel + "/").splitlines()]
    return len(_committed_rechecks(names)) + 1


def write_recheck(walk: str, study: Path = HERE, **kw) -> Path:
    """Write the next recheck (one past the committed ones); refuses when that file, or any uncommitted recheck,
    already exists in the folder: append-only, one at a time."""
    n = next_recheck(walk, study)
    folder = Path(study) / mode_binding.WALKS_DIR / walk
    loose = sorted(p.name for p in folder.glob(RECHECK_PREFIX + "*"))
    root, prefix = _repo(Path(study))
    loose = [x for x in loose if not nrr._in_head(root, f"{_walk_rel(prefix, walk)}/{x}")]
    if loose:
        raise RegradeRefused(f"uncommitted recheck(s) {loose} in the walk folder; commit or remove them first")
    doc = recheck_doc(walk, n, study, **kw)
    data = regrade_bytes(doc)
    path = folder / recheck_name(n)
    register = Path(study) / mode_binding.WALKS_DIR / walk_register.REGISTER_NAME
    reg_rel = nrr._rel(prefix, f"{mode_binding.WALKS_DIR}/{walk_register.REGISTER_NAME}")
    head_bytes = nrr._show(root, reg_rel)
    if register.read_bytes() != head_bytes:
        raise RegradeRefused(f"{walk_register.REGISTER_NAME} on disk is not HEAD's; a recheck appends to HEAD's")
    reg = json.loads(head_bytes, object_pairs_hook=walk_register.no_duplicate_keys)
    if set(reg) != set(walk_register.top_keys(reg.get("schema"))):
        raise RegradeRefused(f"{walk_register.REGISTER_NAME} at HEAD is not a register of schema 1 or 2")
    entry = {"walk": walk, "file": recheck_name(n), "n": n, "checker_constants_sha256": doc["checker_constants_sha256"],
             "sha256": hashlib.sha256(data).hexdigest()}
    # The recheck-coverage ruling: the first recheck bumps the register to schema 2, which adds `rechecks`.
    reg = {"schema": walk_register.SCHEMA_RECHECKS, "walks": reg["walks"],
           "rechecks": walk_register.rechecks_of(reg) + [entry]}
    with open(path, "xb") as fh:
        fh.write(data)
    register.write_text(json.dumps(reg, indent=2) + "\n", encoding="utf-8")
    return path


def commit_recheck(walk: str, n: int, study: Path = HERE, *, secrets, rules_scanner, holdout_matcher=None) -> str:
    """Scan and commit the walk's recheck-<n>.json and the register's new entry, together, under RECHECK_SUBJECT."""
    return _commit_one(walk, recheck_name(n), RECHECK_SUBJECT, study, secrets=secrets, rules_scanner=rules_scanner,
                       holdout_matcher=holdout_matcher, with_register=True)


def committed_rechecks(walk: str, study: Path) -> int:
    """How many rechecks of `walk` the study's HEAD holds: 0 outside a repository, before a first commit, or when none
    is committed (nothing to verify, so nothing supersedes check.json); RegradeRefused on a misnamed recheck."""
    root, prefix = nrr._repo(Path(study))
    if root is None or subprocess.run(["git", "-C", str(root), "rev-parse", "--verify", "-q", "HEAD"],
                                      capture_output=True).returncode != 0:
        return 0
    listed = nrr._git(root, "ls-tree", "-r", "--name-only", "HEAD", "--", _walk_rel(prefix, walk) + "/").splitlines()
    return len(_committed_rechecks([p.rsplit("/", 1)[1] for p in listed]))


def recheck_state(base, walk: str, **kw):
    """The latest committed recheck of a walk under the rehearsals folder `base`, when it re-derives to its exact
    bytes (recheck_doc with its own recorded machine): its document; None when the walk has none committed (outside a
    repository or before a first commit included); RegradeRefused when one does not re-derive (fail closed)."""
    study = Path(base).parent
    n = committed_rechecks(walk, study)
    if n == 0:
        return None
    root, prefix = _repo(study)
    raw = nrr._show(root, f"{_walk_rel(prefix, walk)}/{recheck_name(n)}")
    try:
        doc = json.loads(raw)
        machine = doc["machine"]
    except (ValueError, KeyError, TypeError) as e:
        raise RegradeRefused(f"{recheck_name(n)} cannot be read: {e}") from None
    if regrade_bytes(recheck_doc(walk, n, study, machine=machine, **kw)) != raw:
        raise RegradeRefused(f"{recheck_name(n)} differs from re-deriving it")
    return doc


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="walk_regrade.py")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--walk")
    g.add_argument("--check", action="store_true")
    g.add_argument("--recheck", metavar="WALK")
    for key in MACHINE_KEYS:
        ap.add_argument("--" + key.replace("_", "-"), help="the walk machine's own (a recheck needs all three)")
    a = ap.parse_args(argv)
    try:
        if a.recheck:
            machine = {k: getattr(a, k) for k in MACHINE_KEYS}
            path = write_recheck(a.recheck, machine=machine)
            doc = json.loads(path.read_bytes())
            ch = doc["change"]
            print(f"walk_regrade: wrote {path} (supersedes {doc['supersedes']}); digest "
                  f"{ch['checker_constants_sha256'][0]} -> {ch['checker_constants_sha256'][1]}; reasons added "
                  f"{ch['reasons_added']}, removed {ch['reasons_removed']}; commit it with commit_recheck")
            return 0
        if a.check:
            problems, counts = regrade_report()
            bad = gate_problems(problems, counts)
            for b in bad:
                print(f"walk_regrade: FAIL {b}")
            print("walk_regrade: " + counts_line(counts))
            print("walk_regrade: ok" if not bad else f"walk_regrade: {len(bad)} problem(s)")
            return 1 if bad else 0
        print(f"walk_regrade: wrote {write_regrade(a.walk)}; commit it with commit_regrade (scanned, alone)")
        return 0
    except (RegradeRefused, nrr.RegistrationRefused, FileExistsError) as e:
        print(f"walk_regrade: REFUSED {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
