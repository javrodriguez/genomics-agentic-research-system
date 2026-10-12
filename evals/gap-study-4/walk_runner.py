#!/usr/bin/env python3
"""The CP6 walk runner: drive pre-freeze walks one at a time, check, grade and commit each.

    python3 evals/gap-study-4/walk_runner.py      refuses (exit 2): no production builder of the walk driver yet

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
  6. delete the per-take config folder (driver.published), on every road but one: when the drive recorded a
     postflight that was not ok (a credential-like file left behind), the config folder is kept for a human, as the
     driver's own postflight stop says (S6b (e)).

WHAT STOPS IT. A walk refused before launch (LaunchRefused, or a slot that is not its walk id) made nothing; it is
reported and the runner moves on (D3). A walk whose launch failed after making things, whose drive raised (a drive
scan or postflight refusal among them), whose containers could not all be removed, or whose commit was refused is
NEVER committed: its folder is left for a human, which turns walk_register --check red, and the runner stops there
(the next walk's commit would be refused by that red anyway).

A walk is graded but never counted: nothing here writes under takes/, registers a take or reads takes.json.

THE CLI refuses until the production builders exist (Q-w7b-3: the DockerRuntime, the login file, the counters reader,
the identity and run-tree builders need CP2 and CP6 values). Claude walks only: walk_driver admits only the production
ClaudeCodeAdapter, so walks of arms O and G wait for their adapters and w7c's spend gate.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import mode_binding  # noqa: E402
import routing  # noqa: E402
import run as run_mod  # noqa: E402
import walk_register  # noqa: E402

COMMITTED, LAUNCH_REFUSED, HELD = "committed", "launch-refused", "held"
CHECK_FILE = "check.json"                 # drive.WALK_CHECK (asserted against the driver's module at run time)
POSTFLIGHT_FILE, TEARDOWN_FILE, LEDGER_FILE = "postflight.json", "teardown.json", "driver-ledger.json"
ENTRY_FROM_ROW = ("walk", "task", "half", "wording", "arm", "model")
CLI_REFUSAL = ("the walk runner has no production builder of walk_driver from the real box yet (Q-w7b-3: the "
               "DockerRuntime, the login file, the counters reader, the identity and run-tree builders need CP2 and "
               "CP6 values); call walk_runner.run_walks with a driver built by drive.walk_driver(records='walks')")


def driver_namespace(driver) -> dict:
    """The driver's own module (drive.py, or a witness compiled from it), read from its class's launch: its
    LaunchRefused and WALK_CHECK are that module's, never another import's."""
    return type(driver).launch.__globals__


def walk_entry(row: dict, reason: str) -> dict:
    return dict({k: row.get(k) for k in ENTRY_FROM_ROW}, reason=reason, counted=False)


def check_record(walk: str, records, table, route_fn, *, checked: bool) -> dict:
    """check.json: whether the checker ran (W10 review note: it runs only when a turn ran, and its reading is then
    the driver ledger's companion; otherwise the driver hands an empty reading, which this file must not pass off
    as a clean one), the checker's reasons and events as the drive returned them, and the route routing gives the
    records (or why it refused). Read, never counted."""
    if not isinstance(records, dict):
        raise TypeError("the drive returned no records")
    doc = {"walk": walk, "checked": checked is True, "checker_reasons": list(records.get("checker_reasons") or []),
           "events": records.get("events"), "route": None, "route_refused": None}
    try:
        doc["route"] = route_fn(records, table)["route"]
    except Exception as e:  # noqa: BLE001 - routing must never sink a walk; its refusal is the walk's record
        doc["route_refused"] = f"{type(e).__name__}: {str(e)[:500]}"
    return doc


def write_check(folder: Path, doc: dict) -> Path:
    path = Path(folder) / CHECK_FILE
    path.write_text(json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def postflight_ok(folder: Path) -> bool:
    """Whether the drive's postflight record says the config folder holds no credential file."""
    try:
        return json.loads((Path(folder) / POSTFLIGHT_FILE).read_text()).get("ok") is True
    except (OSError, ValueError, AttributeError):
        return False


def _publish(driver, row: dict, folder: Path) -> str | None:
    """Delete the walk's config folder (driver.published), called only once driver.launch was reached for this row
    (W10-R1-2: never for the runner's own pre-launch refusals, whose slot may name another walk's kept take). Kept
    for a human instead when the drive's postflight record exists and is not ok, or when the drive ran (teardown.json)
    and no postflight record was written (the driver's own stop: "the postflight check did not run"). Returns why it
    was kept or could not be deleted, or None."""
    post = Path(folder) / POSTFLIGHT_FILE
    if post.exists() and not postflight_ok(folder):
        return "the config folder is kept for a human: the postflight did not pass"
    if (Path(folder) / TEARDOWN_FILE).is_file() and not post.exists():
        return "the config folder is kept for a human: the postflight did not run"
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
    if drive_error is not None or removal_error is not None:
        why = [f"drive raised {type(drive_error).__name__}: {drive_error}"] if drive_error is not None else []
        why += [f"container {cid} could not be removed: {removal_error}"] if removal_error is not None else []
        return {"state": HELD, "why": "; ".join(why) + "; the walk folder is left for a human, never committed"}
    if ns["WALK_CHECK"] != CHECK_FILE:
        raise RuntimeError(f"the driver's walk check file is {ns['WALK_CHECK']!r}, not {CHECK_FILE!r}")
    checked = (folder / LEDGER_FILE).is_file()     # the checker ran exactly when the driver wrote its ledger
    write_check(folder, check_record(walk, records, table, route_fn, checked=checked))
    try:
        run_mod.write_walk_grade(entry, folder, grade=grade)
        got = repo.commit_walk(entry)
    except Exception as e:  # noqa: BLE001 - a walk the grade or the commit refuses is held, never half-committed
        return {"state": HELD, "why": f"the walk was not committed: {type(e).__name__}: {e}"}
    doc = json.loads((folder / mode_binding.WALK_GRADE).read_text())
    check = json.loads((folder / CHECK_FILE).read_text())
    return {"state": COMMITTED, "commit": got["commit"], "graded": doc.get("graded") is True,
            "route": check["route"], "checker_reasons": check["checker_reasons"]}


def run_walks(driver, repo, walks, *, table=None, route_fn=None, grade=None) -> list[dict]:
    """Each walk ({"row": the walk's row, with its `walk` id and slot equal to it; "reason": why it is run}), one at a
    time; the list of what happened to each (state committed, launch-refused or held), stopping after a held one."""
    if getattr(driver, "records", None) != "walks":
        raise TypeError("the walk runner drives a walk driver: drive.walk_driver(records='walks')")
    if not callable(getattr(repo, "commit_walk", None)) or Path(repo.root).resolve() != Path(driver.records_root):
        raise TypeError("the walk runner commits through a WalkRepo over the driver's own study folder")
    table = routing.load_table() if table is None else table
    route_fn = routing.route if route_fn is None else route_fn
    results = []
    for item in walks:
        got = run_one(driver, repo, item.get("row"), item.get("reason"), table=table, route_fn=route_fn, grade=grade)
        results.append(got)
        if got["state"] == LAUNCH_REFUSED:
            continue                                   # D3: reported, move on
        if got["state"] == HELD:
            break                                      # D3: kept for a human, stop
    return results


def main(argv=None) -> int:
    print(f"refused: {CLI_REFUSAL}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
