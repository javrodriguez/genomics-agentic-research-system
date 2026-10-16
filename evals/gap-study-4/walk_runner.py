#!/usr/bin/env python3
"""The CP6 walk runner: drive pre-freeze walks one at a time, check, grade and commit each.

    python3 evals/gap-study-4/walk_runner.py --walk <id> --task <t> --half <h> --wording <w> --arm <a> --model <m>
        --reason <why>      one walk end to end (walk_builders.cli); refuses (exit 2), naming each builder or
                            real-box value still missing, until every one exists

WHAT IT DOES (lane w10-walk-runner; glitch-2f's rulings D1, D2, D3 under Javier's standing delegation, Mon 12 Oct
2026, from the proposal in lane-reports/w10-walk-runner.md). run_walks(driver, repo, walks) takes a driver built by
drive.walk_driver(records="walks") and a drive.WalkRepo over the same study, and for each walk ({"row", "reason"}),
one at a time:

  1. launch through the walk arm, so the W1 pre-launch check applies (no freeze, a walk the design in force admits,
     an id not yet registered) and the D2 identity check (the walk's own session id, no ledger row); a walk row's
     slot is its walk id (the driver keys its takes by slot);
  2. drive, then remove the containers by their recorded ids;
  3. write check.json: the checker's reading (check4's round-4 walk road, D1) and the route routing gives the records;
  4. write grade.json (run.write_walk_grade: the v4 grade, or "not graded, because ..." for a walk that died before
     its first turn, D3);
  5. commit the walk folder and its register entry in one commit (WalkRepo.commit_walk);
  6. delete the per-take config folder (driver.published) only on positive proof of a clean drive (its postflight
     record present and ok, its teardown record present with no problem: clean_drive); every other state keeps it
     for a human, as the driver's own postflight stop says (S6b (e)), and fails closed (W10-R2-2).

A VENDOR WALK WHOSE NATIVE CROSS-CHECK IS PENDING (registration review finding 2, glitch-06, 14 Oct 2026). While no
native-session reader is registered, a Gemini drive stops with drive.NativeCrossCheckPending after its cleanup, ledger
and scan. That walk, and only that one (its containers removed, its ledger recording the pending cross-check), is
committed through WalkRepo with every record it made: check.json is pending_walk.check_doc (the checker never ran) and
grade.json is run.grade_walk's pending document (never graded). Its state is "pending-native-reader": never counted,
never re-run (its id is registered), and the runner moves on. After a reader is registered, walk_regrade.py re-derives
its cross-check and grade from the committed bytes into a superseding regrade.json; its own commit stays.

WHAT STOPS IT. A walk refused before launch (LaunchRefused, or a slot that is not its walk id) made nothing; it is
reported and the runner moves on (D3). A walk whose launch failed after making things, whose drive raised (a drive
scan or postflight refusal among them), whose containers could not all be removed, or whose commit was refused is
NEVER committed: its folder is left for a human, which turns walk_register --check red, and the runner stops there
(the next walk's commit would be refused by that red anyway).

A walk is graded but never counted: nothing here writes under takes/, registers a take or reads takes.json.

THE CLI refuses until the production builders exist (Q-w7b-3). Lane w12b-walk-builders (departure w12b-1, recorded in
lane w10's entry) built the half fakes can prove in walk_builders.py: the D2 identity, the login file read by name,
the counters reader, the run-tree and fixture builders and the plumbing; main hands its argv to walk_builders.cli,
which refuses by name while the DockerRuntime or any other real-box or walk-measured value is missing. walk_driver
builds each harness's production adapter (harness_adapter_for; WalkDriver admits only the exact production classes);
the CLI's builders and w7c's spend gate still decide whether a vendor walk can launch.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import mode_binding  # noqa: E402
import pending_walk  # noqa: E402
import routing  # noqa: E402
import run as run_mod  # noqa: E402
import walk_register  # noqa: E402

COMMITTED, LAUNCH_REFUSED, HELD = "committed", "launch-refused", "held"
PENDING = pending_walk.PENDING            # a vendor walk committed ungraded while its native cross-check is pending
CHECK_FILE = "check.json"                 # drive.WALK_CHECK (asserted against the driver's module at run time)
POSTFLIGHT_FILE, TEARDOWN_FILE, LEDGER_FILE = "postflight.json", "teardown.json", "driver-ledger.json"
ENTRY_FROM_ROW = ("walk", "task", "half", "wording", "arm", "model")
CLI_REFUSAL = ("the walk runner's production builders are not all there yet (Q-w7b-3: the DockerRuntime and the other "
               "real-box values come at the bring-up, the login file with the walk token, the pins and constants from "
               "the walks); each missing one is named above")


def driver_namespace(driver) -> dict:
    """The driver's own module (drive.py, or a witness compiled from it), read from its class's launch: its
    LaunchRefused and WALK_CHECK are that module's, never another import's."""
    return type(driver).launch.__globals__


def walk_entry(row: dict, reason: str) -> dict:
    return dict({k: row.get(k) for k in ENTRY_FROM_ROW}, reason=reason, counted=False)


def check_record(walk: str, records, table, route_fn, *, checked: bool, constants_sha256=None,
                 no_output_nudges=None, agent_summary=None) -> dict:
    """check.json: whether the checker ran (W10 review note: it runs only when a turn ran, and its reading is then
    the driver ledger's companion; otherwise the driver hands an empty reading, which this file must not pass off
    as a clean one), the checker's reasons and events as the drive returned them, and the route routing gives the
    records (or why it refused), and (BOOTSTRAP B5, review MINOR 3) the digest of the constants the checker read
    (constants_sha256: the driver's checker_constants_sha256(row)), null when it did not run, which
    pending_walk.coverage_status compares with the constants in force. Read, never counted. And (glitch-b5's ruling 3)
    no_output_nudges: how many no-visible-output nudges the checked transcript carries (the driver's
    no_output_nudges(row)), null when the checker did not run; analysis stratifies by it. And (glitch-b5's Agent parity
    ruling, part 6) agent_calls and subagents: the checked transcript's Agent calls and sub-agent models (the driver's
    agent_summary(row)), null when the checker did not run."""
    if not isinstance(records, dict):
        raise TypeError("the drive returned no records")
    # review r6 MINOR 2 (glitch-b5, 16 Oct 2026): when the checker ran, its count is written, never null
    if checked is True and not pending_walk.valid_nudge_count(no_output_nudges):
        raise ValueError(f"the checker ran and the nudge count is {no_output_nudges!r}, not an int >= 0")
    summary = agent_summary if isinstance(agent_summary, dict) else {}
    if checked is True and not pending_walk.valid_agent_summary(summary.get("agent_calls"), summary.get("subagents"),
                                                                summary.get("nested_cli_calls")):
        raise ValueError("the checker ran and the driver gave no valid Agent call count and sub-agent record")
    doc = {"walk": walk, "checked": checked is True, "checker_reasons": list(records.get("checker_reasons") or []),
           "events": records.get("events"), "route": None, "route_refused": None,
           "checker_constants_sha256": constants_sha256 if checked is True else None,
           "no_output_nudges": no_output_nudges if checked is True else None,
           "agent_calls": summary["agent_calls"] if checked is True else None,
           "subagents": summary["subagents"] if checked is True else None,
           "nested_cli_calls": summary["nested_cli_calls"] if checked is True else None}      # W-3b
    try:
        doc["route"] = route_fn(records, table)["route"]
    except Exception as e:  # noqa: BLE001 - routing must never sink a walk; its refusal is the walk's record
        doc["route_refused"] = f"{type(e).__name__}: {str(e)[:500]}"
    return doc


def write_check(folder: Path, doc: dict) -> Path:
    path = Path(folder) / CHECK_FILE
    path.write_text(json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def _record(path: Path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return None


def clean_drive(folder: Path) -> bool:
    """W10-R2-2 (fail closed): the drive is proven clean only by both of its records: postflight.json present,
    readable and ok, and teardown.json present, readable, recording a teardown with no problem. Any other state (a
    record missing, unreadable, not ok, or a teardown problem) is not proof."""
    post, tear = _record(Path(folder) / POSTFLIGHT_FILE), _record(Path(folder) / TEARDOWN_FILE)
    post_ok = isinstance(post, dict) and post.get("ok") is True
    tear_ok = isinstance(tear, dict) and tear.get("teardown") is not None and tear.get("problems") == []
    return post_ok and tear_ok


def _publish(driver, row: dict, folder: Path) -> str | None:
    """Delete the walk's config folder (driver.published), called only once driver.launch was reached for this row
    (W10-R1-2: never for the runner's own pre-launch refusals, whose slot may name another walk's kept take), and
    only on positive proof of a clean drive (W10-R2-2, clean_drive); every other state keeps it for a human. A row
    whose launch made no walk folder made no config folder either, and nothing is touched. Returns why the folder
    was kept or could not be deleted, or None."""
    if not Path(folder).is_dir():
        return None
    if not clean_drive(folder):
        return "the config folder is kept for a human: no clean postflight and teardown record proves the drive clean"
    try:
        driver.published(row, 0)
    except Exception as e:  # noqa: BLE001 - recorded beside the walk's state, never over it
        return f"the config folder could not be deleted: {type(e).__name__}: {e}"
    return None


def _remove(driver, cid):
    if cid is None:
        return None
    try:
        driver.remove(cid)
    except Exception as e:  # noqa: BLE001
        return e
    return None


def run_one(driver, repo, row: dict, reason: str, *, table, route_fn, grade=None) -> dict:
    walk = row.get("walk") if isinstance(row, dict) else None
    folder = Path(driver.records_root) / mode_binding.WALKS_DIR / str(walk)
    out = {"walk": walk}
    reached = []                       # W10-R1-2: set just before driver.launch is called for this row
    try:
        out.update(_run_one(driver, repo, row, reason, walk, folder, reached, table=table, route_fn=route_fn,
                            grade=grade))
    finally:
        kept = None
        if reached:
            kept = _publish(driver, row, folder)
        out["config"] = kept
    return out


def _run_one(driver, repo, row, reason, walk, folder, reached, *, table, route_fn, grade) -> dict:
    ns = driver_namespace(driver)
    if not isinstance(row, dict) or not isinstance(walk, str):
        return {"state": LAUNCH_REFUSED, "why": "the walk row names no walk id"}
    if row.get("slot") != walk:
        return {"state": LAUNCH_REFUSED, "why": f"the walk row's slot {row.get('slot')!r} is not its walk id "
                                                f"{walk!r}; a walk's slot is its walk id"}
    if not isinstance(reason, str) or not walk_register.visible(reason):
        return {"state": LAUNCH_REFUSED, "why": "the walk has no reason; every walk is committed with its reason"}
    entry = walk_entry(row, reason)
    reached.append(True)
    try:
        cid = driver.launch(row)
    except ns["LaunchRefused"] as e:
        return {"state": LAUNCH_REFUSED, "why": str(e)}
    except Exception as e:  # noqa: BLE001 - a launch that failed after making things is held for a human
        cid = getattr(e, "container_id", None)
        left = _remove(driver, cid)
        return {"state": HELD, "why": f"launch failed: {type(e).__name__}: {e}"
                                      + (f"; and its container could not be removed: {left}" if left else "")}
    drive_error = records = None
    try:
        records = driver.drive(row, cid)
    except Exception as e:  # noqa: BLE001
        drive_error = e
    removal_error = _remove(driver, cid)
    if removal_error is None and isinstance(drive_error, ns["NativeCrossCheckPending"]):
        return _commit_pending(repo, entry, folder, drive_error)
    if drive_error is not None or removal_error is not None:
        why = [f"drive raised {type(drive_error).__name__}: {drive_error}"] if drive_error is not None else []
        why += [f"container {cid} could not be removed: {removal_error}"] if removal_error is not None else []
        return {"state": HELD, "why": "; ".join(why) + "; the walk folder is left for a human, never committed"}
    if ns["WALK_CHECK"] != CHECK_FILE:
        raise RuntimeError(f"the driver's walk check file is {ns['WALK_CHECK']!r}, not {CHECK_FILE!r}")
    checked = (folder / LEDGER_FILE).is_file()     # the checker ran exactly when the driver wrote its ledger
    read = getattr(driver, "checker_constants_sha256", None)       # BOOTSTRAP: the constants the checker read
    nudges = getattr(driver, "no_output_nudges", None)              # ruling 3: the nudges the checker's transcript holds
    nudges = nudges(row) if callable(nudges) else None
    if checked and not pending_walk.valid_nudge_count(nudges):       # review r6 MINOR 2: held, never written as null
        return {"state": HELD, "why": f"the checker ran and the driver gave nudge count {nudges!r}; the walk folder is "
                                      f"left for a human, never committed"}
    agents = getattr(driver, "agent_summary", None)                 # the Agent parity ruling, part 6
    agents = agents(row) if callable(agents) else None
    if checked and not (isinstance(agents, dict) and pending_walk.valid_agent_summary(agents.get("agent_calls"),
                                                                                       agents.get("subagents"),
                                                                                       agents.get("nested_cli_calls"))):
        return {"state": HELD, "why": "the checker ran and the driver gave no valid Agent call count; the walk folder "
                                      "is left for a human, never committed"}
    write_check(folder, check_record(walk, records, table, route_fn, checked=checked,
                                     constants_sha256=read(row) if callable(read) else None,
                                     no_output_nudges=nudges, agent_summary=agents))
    try:
        run_mod.write_walk_grade(entry, folder, grade=grade)
        got = repo.commit_walk(entry)
    except Exception as e:  # noqa: BLE001 - a walk the grade or the commit refuses is held, never half-committed
        return {"state": HELD, "why": f"the walk was not committed: {type(e).__name__}: {e}"}
    doc = json.loads((folder / mode_binding.WALK_GRADE).read_text())
    check = json.loads((folder / CHECK_FILE).read_text())
    return {"state": COMMITTED, "commit": got["commit"], "graded": doc.get("graded") is True,
            "route": check["route"], "checker_reasons": check["checker_reasons"]}


def _commit_pending(repo, entry: dict, folder: Path, pending) -> dict:
    """Registration review finding 2: commit a vendor walk whose drive stopped on a pending native cross-check, with
    the pending check and grade documents, both derived from its driver ledger. A ledger that does not record the
    pending cross-check, a grade or a commit refused: held, never half-committed."""
    try:
        ledger = json.loads((folder / LEDGER_FILE).read_text(encoding="utf-8"))
        write_check(folder, pending_walk.check_doc(entry["walk"], ledger))
        run_mod.write_walk_grade(entry, folder)
        got = repo.commit_walk(entry)
    except Exception as e:  # noqa: BLE001 - a pending walk the records or the commit refuse is held
        return {"state": HELD, "why": f"drive raised {type(pending).__name__}: {pending}; the pending walk was not "
                                      f"committed: {type(e).__name__}: {e}"}
    return {"state": PENDING, "commit": got["commit"], "graded": False, "route": None, "checker_reasons": [],
            "why": str(pending)}


def run_walks(driver, repo, walks, *, table=None, route_fn=None, grade=None) -> list[dict]:
    """Each walk ({"row": the walk's row, with its `walk` id and slot equal to it; "reason": why it is run}), one at a
    time; the list of what happened to each (state committed, pending-native-reader, launch-refused or held),
    stopping after a held one."""
    if getattr(driver, "records", None) != "walks":
        raise TypeError("the walk runner drives a walk driver: drive.walk_driver(records='walks')")
    if not callable(getattr(repo, "commit_walk", None)) or Path(repo.root).resolve() != Path(driver.records_root):
        raise TypeError("the walk runner commits through a WalkRepo over the driver's own study folder")
    route_fn = routing.route if route_fn is None else route_fn    # routing.route reads routing.json when table is None
    results = []
    for item in walks:
        got = run_one(driver, repo, item.get("row"), item.get("reason"), table=table, route_fn=route_fn, grade=grade)
        results.append(got)
        if got["state"] == LAUNCH_REFUSED:
            continue                                   # D3: reported, move on
        if got["state"] == HELD:
            break                                      # D3: kept for a human, stop
    return results


def main(argv=None, *, builders=None) -> int:
    """walk_builders.cli: production_builders() unless a builder set is handed in (a test's fake box)."""
    import walk_builders
    return walk_builders.cli(argv, builders, refusal=CLI_REFUSAL)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
