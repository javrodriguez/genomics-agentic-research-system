#!/usr/bin/env python3
"""Regrade committed takes with local v4 graders and emit interface 11 lists.

records/<task>.json is the only results destination. Routing has already happened
inside the drive: this module and check_results only re-verify its decision.
Publication reads committed cell states and closed human rulings. Rehearsals and
pauses never become take records; a final harness error has no views and leaves
the denominator. Empty input says no takes and creates no placeholder record.

CP2 supplies registered rows and batch history. A row's record_dir names its
committed take folder under this round, containing transcript.jsonl and evidence/
(endstate.Evidence's closed layout). model and agent are mandatory. The pure
produce() seam accepts a grader callback so synthetic takes need no filesystem,
model, container or network. CLI grading requires the frozen pre-registration.

THE WALK LAYOUT (lane w8a, ruling W8-layout-1, Option A; this file moved from
lane w5b to lane w8a under ruling W8A-gap4-1). A row's record_dir is bound to
the take folders (mode_binding.TAKES_DIR): a walk folder (rehearsals/<walk>/)
can never be graded into results. A walk is graded but never counted: its
grade.json is grade_walk()'s output, written beside its records before
WalkRepo commits it, and `run.py --walks --check` regrades every registered
walk and requires its grade.json byte-identical. A walk with no first agent
turn is not graded, and its grade.json says why (from its driver ledger).
"""
from __future__ import annotations

import argparse
import collections
import copy
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))
import batch
import check_results
import prereg
import routing
import stats
import takes
import transcript_view
import variants
from graders import delegation, labels4
import mode_binding
import walk_register
import pending_walk  # live harness (registration review finding 2): a pending vendor walk's grade

RECORDS = HERE / "records"

# ---- vendor admission (lane vendor-admission T1, glitch-b5, 16 Oct 2026): defence in depth at the grading callers --
# A Codex or Gemini take reaches endstate.Evidence.load only when the reader registry the caller holds includes its
# harness (native_reader_registration.production_readers(), or `readers` handed in by tests) and the native cross-check
# handed in is exactly drive's agreed shape. The take and walk roads read it from the driver ledger's
# cross_check_status; walk_regrade passes its own re-derived cross-check. claude-code is untouched.
VENDOR_HARNESSES = ("codex", "gemini")             # drive.VENDOR_HARNESSES; run.py does not import drive
AGREED_CROSS_CHECK = {"status": "agreed", "why": None}   # drive.gemini_cross_check's and codex_cross_check's


class VendorAdmissionRefused(ValueError):
    """A vendor take offered for grading without a registered reader and an agreed native cross-check."""


def vendor_admission(harness, readers, cross) -> None:
    """Refuse (VendorAdmissionRefused) a codex or gemini take unless `readers` (None: the production registry) holds a
    reader for its harness and `cross` is exactly {"status": "agreed", "why": None}; any other harness passes."""
    if harness not in VENDOR_HARNESSES:
        return
    if readers is None:
        import native_reader_registration as nrr
        try:
            readers = nrr.production_readers()
        except nrr.RegistrationRefused as e:
            raise VendorAdmissionRefused(f"harness {harness!r}: the reader registration refuses: {e}") from None
    if not isinstance(readers, dict) or readers.get(harness) is None:
        raise VendorAdmissionRefused(f"harness {harness!r}: no registered {harness} native reader in the registry "
                                     f"grading holds; a vendor take is graded only through one")
    if type(cross) is not dict or cross != AGREED_CROSS_CHECK or cross["why"] is not None:
        raise VendorAdmissionRefused(f"harness {harness!r}: the native cross-check is {cross!r}, not exactly "
                                     f"{AGREED_CROSS_CHECK!r}; a vendor take is graded only cross-checked")


def ledger_cross_check(folder):
    """The driver ledger's cross_check_status in `folder`; None when it is absent or unreadable (never agreement)."""
    try:
        ledger = json.loads((Path(folder) / "driver-ledger.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return ledger.get("cross_check_status") if isinstance(ledger, dict) else None


def grader_for(name: str):
    """Load the v4 file itself, regardless of a cached module of the same name."""
    if name not in variants.GRADERS:
        raise ValueError(f"unknown grader {name!r}")
    path = HERE / "graders" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"pipeline_grader_{name}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if Path(mod.__file__).resolve() != path.resolve():
        raise ValueError("the grader did not load from its v4 file")
    return mod


def stop_views() -> dict:
    return dict(stats.STOP_VIEWS)


def grade_views(grade: dict, grader=None) -> dict:
    """Map the grader's own standing; no text is re-read or re-graded here."""
    if grade["label"] in labels4.RESERVED:
        return stop_views()
    if grader is not None and callable(getattr(grader, "correct_in_view", None)):
        native = {v: grader.correct_in_view(grade["label"], grade["expected"], v) for v in stats.VIEWS}
    elif grader is not None and callable(getattr(grader, "stop_views", None)):
        native = grader.stop_views(grade)
    elif "views" in grade:
        native = grade["views"]
    else:
        if type(grade.get("correct")) is not bool:
            raise ValueError("the grader supplied no standing")
        native = {v: grade["correct"] for v in stats.VIEWS}
    out = {}
    for view in stats.VIEWS:
        value = native[view]
        if type(value) is bool:
            value = "right" if value else "wrong"
        if value not in ("right", "wrong"):
            raise ValueError("a non-stop grader standing must be right or wrong")
        out[view] = value
    return out


def regrade(name: str, row: dict, spec: dict, transcript, evidence) -> tuple[dict, str]:
    mod = grader_for(name)
    original = transcript                 # W-3b: the nested agent-CLI count reads the take as it was handed
    transcript, refused = delegation.seam(name, evidence, transcript)   # a delegated take, presented (16 Oct)
    if refused:
        raise mod.GradeError(refused)
    if name in ("scope_read", "template_adherence"):
        got = mod.grade(spec, evidence, transcript)
    elif name == "number_fidelity":     # review r13 NIT 4: the harness the seam and every grader read, the evidence's
        got = mod.grade(transcript_view.events(evidence.harness, transcript), spec)
    elif name == "precondition_refusal":
        got = mod.grade(transcript, evidence, spec, variants.row_fields({k: row[k] for k in
                                                                     ("half", "wording", "repeat", "pressure")}))
    elif name == "plan_gate":
        got = mod.grade(transcript, evidence, spec)
    elif name == "confounded_design":
        got = mod.grade(transcript, evidence, spec, half=row["grader_half"])
    elif name == "new_tasks":
        got = mod.grade(row["task"], transcript, evidence, spec, half=row["grader_half"])
    else:
        raise ValueError(f"no invocation for grader {name!r}")
    got = delegation.sampled(got, original)                      # W-3b: a nested agent CLI, to the human sample
    return dict(got, views=grade_views(got, mod)), str(Path(mod.__file__).resolve())


def verify_route(outcome: dict, table: dict) -> None:
    check_results.verify_route(outcome, table)


def agent_events(outcome: dict, table: dict | None = None) -> list:
    """Pre-freeze review 1, MAJOR 5: the agent event rows (routing.json agent_event_rows, in its order) among a graded
    take's winning rows; [] for any other route or a take whose fate a ruling gave (no routing decision of its own)."""
    if outcome["state"] != labels4.GRADED or not isinstance(outcome.get("decision"), dict):
        return []
    won = outcome["decision"].get("rows") or []
    return [rid for rid in routing.agent_event_rows(routing.load_table() if table is None else table) if rid in won]


def ruled_slots(history: list) -> set:
    """Pre-freeze review 1, MAJOR 8: the slots a committed ruling touched (every published take of one is ruled)."""
    return {entry["slot"] for entry in history if batch.is_ruling(entry)}


def record_for(row: dict, outcome: dict, grade: dict, *, ruled: bool = False, table: dict | None = None) -> dict | None:
    route = outcome["state"]
    if not outcome["final"] or route in stats.NEVER_IN_RESULTS:
        return None
    bad = takes.agent_problems(row)
    if bad:
        raise ValueError("; ".join(bad))
    record = {k: copy.deepcopy(row[k]) for k in stats.TAKE_FIELDS[:8]}
    if route == labels4.HARNESS_ERROR:
        if not outcome["beyond_cap"]:
            raise ValueError("a harness error is published only beyond its cap")
        label, views = labels4.HARNESS_ERROR, None
    elif route == labels4.ABORTED:
        label, views = labels4.ABORTED, stop_views()
    elif route == labels4.GRADED:
        label, views = grade["label"], grade_views(grade)
    else:
        raise ValueError("an unresolved stopped take is never a take record")
    record.update(route=route, cell_state=outcome["cell_state"], label=label, views=views,
                  agent_events=agent_events(outcome, table), ruled=ruled)
    return stats.validate_record(record)


def require_registered_outcome(outcome: dict, registered: dict) -> None:
    key = (outcome["slot"], outcome["attempt"])
    if key not in registered:
        raise ValueError("an outcome has no registered row")
    row = registered[key]
    if row["half_cell"] != outcome["half_cell"]:
        raise ValueError("the outcome differs from its registered half-cell")
    records = outcome["records"]
    if records is not None:
        pin = records["pin"]
        if any(pin.get(k) != v for k, v in dict(model=row["model"], **row["agent"]).items()):
            if batch.pin_block(outcome):
                raise ValueError("the outcome differs from its registered model or agent: a pin-blocked take that "
                                 "was not re-run under the registered pin by a ruling that passed the ruling rule "
                                 "(or whose block the take road did not commit) is a stop that needs an owner")
            raise ValueError("the outcome differs from its registered model or agent")


def produce(rows: list, history: list, grade, *, table=None, refusal=None, committed=None) -> dict:
    """Re-verify every attempt, then grade final eligible takes; no routing repair."""
    table = routing.load_table() if table is None else table
    registered = check_results.validate_ledger(rows)
    refusal = takes.driver_refusal_record if refusal is None else refusal
    # The orchestrator's pin-block ruling: a pin block re-run under the registered pin is a harness event, never counted
    events = check_results.pin_block_events(history, registered, table, refusal=refusal, committed=committed)
    exempt = {(e["slot"], e["attempt"]) for e in events}
    for o in history:
        if batch.is_outcome(o):
            if (o["slot"], o["attempt"]) not in exempt:
                require_registered_outcome(o, registered)
            verify_route(o, table)
    published = check_results.publication(history, table)
    # Pre-freeze review 1, MAJOR 8: a ruling that re-ran a take after its first turn stands only on a clean end state.
    bad = check_results.ruled_rerun_problems(history, registered,
                                             lambda r, o: grade_views(grade(r, o))["excluded"], table)
    # The closure review of 898e598c: the door's two git-bound conditions, again (`refusal` stands in for tests).
    bad += batch.door_rule_problems(history, list(registered.values()), table, refusal)
    if bad:
        raise ValueError("; ".join(bad))
    ruled = ruled_slots(history)
    records, audit = [], []
    for o in published["outcomes"]:
        key = (o["slot"], o["attempt"])
        row = registered[key]
        result = grade(row, o) if o["state"] == labels4.GRADED else {}
        cell = published["cells"].get(o["half_cell"])
        rec = record_for(row, dict(o, cell_state=cell["state"] if cell else o["cell_state"]), result,
                         ruled=o["slot"] in ruled, table=table)
        if rec is not None:
            records.append(rec)
            audit.append({"slot": o["slot"], "attempt": o["attempt"], "grade": result})
    stats.check_records(records)
    return dict(published, records=records, audit=audit, harness_events=events)


def record_document(records: list) -> list:
    return records


def write_records(records: list, *, root=HERE) -> list[Path]:
    stats.check_records(records)
    grouped = collections.defaultdict(list)
    for record in records:
        grouped[record["task"]].append(record)
    paths = []
    for task, rows in sorted(grouped.items()):
        path = Path(root) / "records" / f"{task}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        ordered = sorted(rows, key=lambda r: repr(stats.try_key(r)))
        path.write_text(json.dumps(record_document(ordered), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        paths.append(path)
    return paths


def require_evidence_identity(row: dict, evidence) -> None:
    if (evidence.model != row["model"] or evidence.harness != row["agent"]["harness"] or
            evidence.version != row["agent"]["version"]):
        raise ValueError("the evidence names another model or agent")


def transcript_lines(path) -> "transcript_view.BoundTranscript":
    """The transcript as the graders' contract takes it: its lines, read here (item E, glitch-6b 15 Oct 2026: CP6 walk
    w020's commit failed because a path reached plan_gate.take_events, whose guard refuses one; a grader opens no
    file), bound to its path (the review of E: the vendor binding reads the envelope's streams beside it), as one
    transcript_view.BoundTranscript, never a bare path."""
    return transcript_view.BoundTranscript(path)


def grade_committed(row: dict, outcome: dict, *, readers=None) -> dict:
    """The real callback: bound take artifacts and specs, with the same pure grader path. A vendor take is admitted
    first (vendor_admission: `readers`, None for the production registry, and its driver ledger's cross-check)."""
    from graders import endstate
    path = (HERE / row["record_dir"]).resolve()
    takes_root = (HERE / mode_binding.TAKES_DIR).resolve()
    if path == takes_root or not path.is_relative_to(takes_root):          # W8A (L5): takes/ only, never a walk
        raise ValueError(f"record_dir {row['record_dir']!r} is not a take folder under {mode_binding.TAKES_DIR}/; "
                         f"a walk folder or any other folder is never graded into results")
    inside = path.relative_to(takes_root).parts                           # W8A-R1-3: takes/<slot>/<k>, this row's
    if len(inside) != mode_binding.RECORD_DEPTH[mode_binding.TAKES_DIR] or \
            inside != (str(row["slot"]), str(row["attempt"])):              # W8A-R2-3: a missing key raises
        raise ValueError(f"record_dir {row['record_dir']!r} is not this row's take folder "
                         f"{mode_binding.TAKES_DIR}/{row['slot']}/{row['attempt']}")
    rel = path.relative_to(REPO.resolve()).as_posix()
    if takes._git_at(REPO, "status", "--porcelain", "--", rel):
        raise ValueError("take artifacts have uncommitted changes")
    if not takes._git_at(REPO, "ls-files", "--", rel):
        raise ValueError("take artifacts are not committed")
    task = variants.load_task(row["task"])
    spec = variants.grader_spec(row["task"], row["half"], row["wording"], pressure=row["pressure"],
                                project=row["project"])
    vendor_admission((row.get("agent") or {}).get("harness"), readers, ledger_cross_check(path))
    evidence = endstate.Evidence.load(path / "evidence")
    require_evidence_identity(row, evidence)
    named = dict(row, grader_half=(task["grader_halves"] or {}).get(row["half"]))
    got, module = regrade(variants.grader_name(task), named, spec, transcript_lines(path / "transcript.jsonl"),
                          evidence)
    return dict(got, graded_by=module)


# ---- the walks (W8A, L6): graded, never counted --------------------------------------------------------------------
WALK_ROW_FROM_GRADE = ("pressure", "repeat")      # the cell fields a register entry does not carry (driver ledger)


def walk_row(entry: dict, ledger: dict, cell: dict | None = None) -> dict:
    """The row a walk is graded as: task, half, wording, arm and model from its register entry, the agent, project,
    pressure and repeat from its driver ledger (which must agree with the entry). W8A-R1-2: the cell is the driver
    ledger's own record of the row's pressure and repeat; a `cell` handed in must equal it, so grade.json can never
    supply one the walk did not run under."""
    for key, led in (("task", "task"), ("half", "half"), ("wording", "wording"), ("arm", "arm"),
                     ("model", "model_requested")):
        if ledger.get(led) != entry[key]:
            raise ValueError(f"the walk's driver ledger records {led} {ledger.get(led)!r}; its register entry "
                             f"says {entry[key]!r}")
    missing = [k for k in WALK_ROW_FROM_GRADE if k not in ledger]
    if missing:
        raise ValueError(f"the walk's driver ledger records no {', '.join(missing)}; a walk is graded under the cell "
                         f"its driver recorded")
    recorded = {k: ledger[k] for k in WALK_ROW_FROM_GRADE}
    if (recorded["repeat"] is None) == (recorded["pressure"] is None):         # W8A-R2-4: stats._one_level's rule
        raise ValueError(f"the walk's driver ledger records pressure {recorded['pressure']!r} and repeat "
                         f"{recorded['repeat']!r}; exactly one of them is None (variants.cells)")
    if cell is not None and cell != recorded:
        raise ValueError(f"the cell {cell!r} is not the one the walk's driver ledger records ({recorded!r})")
    cell = recorded
    return {"task": entry["task"], "half": entry["half"], "wording": entry["wording"], "arm": entry["arm"],
            "model": entry["model"], "agent": dict(ledger["agent"]), "project": ledger["project"], **cell}


def grade_walk_folder(row: dict, folder: Path) -> dict:
    """The real grading of a walk folder: the same v4 grader road as grade_committed, past its take-folder binding.
    graded_by is study-relative, so the bytes are the same on every machine. It admits nothing itself: its callers do
    (grade_walk on the driver ledger's cross-check, walk_regrade on its own re-derived one)."""
    from graders import endstate
    task = variants.load_task(row["task"])
    spec = variants.grader_spec(row["task"], row["half"], row["wording"], pressure=row["pressure"],
                                project=row["project"])
    evidence = endstate.Evidence.load(folder / "evidence")
    require_evidence_identity(row, evidence)
    named = dict(row, grader_half=(task["grader_halves"] or {}).get(row["half"]))
    got, module = regrade(variants.grader_name(task), named, spec, transcript_lines(folder / "transcript.jsonl"),
                          evidence)
    return dict(got, graded_by=Path(module).resolve().relative_to(HERE.resolve()).as_posix())


def grade_walk(entry: dict, folder, cell: dict | None = None, grade=None, *, readers=None) -> dict:
    """grade.json's document for one walk: {"graded": true, "row", "grade"} when its driver ledger records a first
    agent turn, else {"graded": false, "why"} with the ledger's own outcome. `grade` stands in for
    grade_walk_folder (tests); `cell` ({pressure, repeat}) is optional and must equal the driver ledger's. A vendor
    walk is admitted first (vendor_admission: `readers`, None for the production registry, and the driver ledger's
    cross-check), whichever grade stands in."""
    folder = Path(folder)
    if not (folder / "driver-ledger.json").is_file():         # D3
        return {"graded": False, "why": "not graded, because " + died_before_turn_one(folder)}
    ledger = json.loads((folder / "driver-ledger.json").read_text())
    if ledger.get("first_agent_turn") is not True:
        return {"graded": False, "why": f"no first agent turn, so a rehearsal before the agent's first turn "
                                        f"(the routing table's first row): {ledger.get('outcome')}"}
    pending = pending_walk.status(ledger)          # a vendor walk whose native cross-check is pending: never graded
    if pending is not None:
        return pending
    row = walk_row(entry, ledger, cell)
    vendor_admission(row["agent"].get("harness"), readers, ledger.get("cross_check_status"))
    return {"graded": True, "row": row, "grade": (grade_walk_folder if grade is None else grade)(row, folder)}


def died_before_turn_one(folder: Path) -> str:
    """W10 (ruling D3; this file edited by lane w10, departure w10-1): why a walk with no driver ledger was not
    graded, read from its own records: the pre-turn refusal (refusal.json), else the preflight checks that failed
    (preflight.json). A folder with neither, or one holding a transcript or a turn record (W10-R2-3: a turn ran),
    raises: it is not a walk WalkRepo commits (drive.walk_files)."""
    ran = sorted(p.name for p in folder.iterdir() if p.name == "transcript.jsonl"
                 or (p.name.startswith("turn-") and p.name.endswith(".jsonl")))
    if ran:                                              # W10-R2-3: a turn ran; its ledger is missing, not unwritten
        raise ValueError(f"{folder} holds {', '.join(ran)} and no driver-ledger.json: a walk whose turn ran is never "
                         f"read as one that died before turn 1")
    refusal, pre = folder / "refusal.json", folder / "preflight.json"
    if refusal.is_file():
        doc = json.loads(refusal.read_text())
        return f"the walk was refused before its first turn ({doc.get('refused')}: {doc.get('why')})"
    if pre.is_file():
        doc = json.loads(pre.read_text())
        failed = [f"{c.get('id')}: {c.get('detail')}" for c in doc.get("checks") or [] if c.get("ok") is not True]
        if doc.get("ok") is not True:
            return f"its preflight failed before the first turn ({'; '.join(failed) or 'no check named'})"
        return "its preflight passed and no turn ran, so the driver wrote no ledger"
    raise ValueError(f"{folder} holds no driver-ledger.json, refusal.json or preflight.json; nothing says why the "
                     f"walk was not graded")


def walk_grade_bytes(doc: dict) -> bytes:
    return (json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def write_walk_grade(entry: dict, folder, cell: dict | None = None, grade=None, *, readers=None) -> Path:
    """Write a walk's grade.json (before WalkRepo commits the walk)."""
    path = Path(folder) / mode_binding.WALK_GRADE
    path.write_bytes(walk_grade_bytes(grade_walk(entry, folder, cell, grade, readers=readers)))
    return path


def walk_problems(base=None, grade=None) -> tuple[list[str], int]:
    """L6: every registered walk regraded; its grade.json must be the regrade's bytes exactly. (problems, walks)."""
    walks_root = Path(HERE if base is None else base) / mode_binding.WALKS_DIR
    entries = walk_register.registered(walks_root)
    out = []
    for entry in entries:
        folder = walks_root / entry["walk"]
        stored_path = folder / mode_binding.WALK_GRADE
        try:
            stored = stored_path.read_bytes()
            doc = json.loads(stored)
            cell = ({k: doc["row"][k] for k in WALK_ROW_FROM_GRADE} if isinstance(doc, dict) and doc.get("graded")
                    is True and isinstance(doc.get("row"), dict) else None)
            again = walk_grade_bytes(grade_walk(entry, folder, cell, grade))
        except (OSError, ValueError, KeyError, TypeError) as e:
            out.append(f"walk {entry['walk']!r}: cannot be regraded: {type(e).__name__}: {e}")
            continue
        if again != stored:
            out.append(f"walk {entry['walk']!r}: {mode_binding.WALKS_DIR}/{entry['walk']}/{mode_binding.WALK_GRADE} "
                       f"differs from regrading it")
    return out, len(entries)


def walks_main() -> int:
    bad, n = walk_problems()
    for b in bad:
        print(f"run: FAIL {b}")
    if bad:
        return 1
    if n == 0:
        print("run: ok, having regraded 0 walks: none is registered, so nothing here is evidence about any walk")
    else:
        print(f"run: {n} walk(s) regraded, every grade.json the regrade's bytes; never counted")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true")
    group.add_argument("--task")
    group.add_argument("--check", action="store_true")
    ap.add_argument("--walks", action="store_true", help="with --check: regrade every registered walk")
    args = ap.parse_args(argv)
    if args.walks:
        if not args.check:
            ap.error("--walks goes with --check only: a walk is regraded and compared, never written into results")
        return walks_main()
    rows, history = takes.load_rows(), takes.read_history()
    if not rows and not history and not stats.results_files(RECORDS):
        print("run: no takes; nothing was graded or written")
        return 0
    prereg.require_frozen("grading takes")
    got = produce(rows, history, grade_committed)
    records = got["records"]
    if args.task:
        records = [r for r in records if r["task"] == args.task]
    if args.check:
        have = stats.load_results(RECORDS)
        if sorted(have, key=repr) != sorted(records, key=repr):
            print("run: FAIL stored records differ from regrading")
            return 1
        print(f"run: {len(records)} records regraded and compared")
    else:
        paths = write_records(records)
        print(f"run: {len(records)} records in {len(paths)} files" if records else "run: no takes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
