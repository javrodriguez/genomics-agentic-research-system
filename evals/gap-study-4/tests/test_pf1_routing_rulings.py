#!/usr/bin/env python3
"""Lane pf1-l2a (Gap Study round 4): pre-freeze review 1's MAJOR 5, MAJOR 8 and m17, folded.

The Lane-orchestrator approved the fold plan (pfr-20261024/FOLD-PLAN-prefreeze-1.md) under Javier's standing
delegation on Sat 24 Oct 2026. Each guard below is written red first, and each has witnesses: a copy of the module it
guards with the guard edited out, which must turn the guard red.

  P5   MAJOR 5, the agent cannot route its own take away from grading. After the first turn a process alive at the
       quiescence cap (quiescence-cap-reached) and a non-zero exec exit with no API error and no counter rise
       (nonzero-exec-exit) route graded, never harness-error; routing.json's agent_event_rows names both, and only
       graded after-first-turn rows; run.record_for writes the winning ones into the record's agent_events, and stats
       counts each in its own column. Harness-error stays for what the agent cannot cause (an API error, a watcher
       gap), and the before-first-turn routes are unchanged.
  P8   MAJOR 8, rulings on stopped takes are bound and counted. A ruling carries why and cite; after the agent's first
       turn (or with no readable records, after a drive that started) a ruling never routes rehearsal; after the first
       turn a ruling re-runs a take only when its records meet a harness-fault row (an API error, a watcher gap, a
       counter rise), refused at the door (the Lane-orchestrator's ruling 2); a ruling that re-runs such a take, or
       one of unknown phase, stands only when the take's own grader reads its committed end state with no wrong action
       (check_results.ruled_rerun_problems, called by run.produce); every take of a ruled slot carries ruled true, and
       stats counts ruled takes per half-cell; the draft registers the rule (ruling_rule).
  P17  m17, the routing table's no-match inputs are listed and each has a pre-registered ruling default.
       routing.no_match_classes enumerates the closed input classes for every pin harness; each no-match class (its
       phase and last-turn end) has exactly one entry in routing.json's no_match_defaults, no entry is stale, a
       condition outside the closed vocabulary refuses the proof, and a ruling on a no-match take must be its
       class's default.

Synthetic records and histories only; no model, network, container or git.
"""

from __future__ import annotations

import copy
import inspect
import json
import sys
import types
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
_PATH = list(sys.path)
sys.path.insert(0, str(HERE))

import batch  # noqa: E402
import build_draft  # noqa: E402
import check_results  # noqa: E402
import routing  # noqa: E402
import run  # noqa: E402
import stats  # noqa: E402
import takes  # noqa: E402
from graders import labels4  # noqa: E402

sys.path[:] = _PATH

REAL = routing.load_table()
HARNESS = "claude-code"
MODEL = "claude-opus-5-5"
PIN = dict(REAL["pin_profiles"][HARNESS][MODEL], harness=HARNESS, model=MODEL)
INIT = {f: PIN[f] for f in ("model", "permission_mode", "version")}
EVENT_ROWS = ["nonzero-exec-exit", "quiescence-cap-reached"]
A, B = labels4.AFTER_FIRST_TURN, labels4.BEFORE_FIRST_TURN
E500 = {"status": 500, "type": "api_error", "text": None}


def records(phase=A, turns=None, end=None):
    """Clean harness-side records of one take under the real opus pin."""
    after = phase == A
    n = (2 if after else 0) if turns is None else turns
    end = (labels4.END_TURN if after else None) if end is None and n else end
    return {
        "ledger": {"first_turn_started": after, "turns": n, "end": end if n else None,
                   "turn_ends": [labels4.END_TURN] * (n - 1) + [end] if n else [],
                   "turn_outputs": [after] * n, "committed": False, "finalize_abort": False},
        "exit": {"container_started": True, "container_exited": False, "exec_codes": [0] * n},
        "cgroup": {"oom_kill_delta": 0, "pids_max_delta": 0},
        "init": [dict(INIT) for _ in range(n)],
        "pin": dict(PIN),
        "api_errors": [],
        "sidecar": {"start_record": True, "stop_record": True, "exit_code": 0, "queue_overflow": False},
        "preflight": {"ok": True},
        "operator": {"unexplained_diffs": 0},
        "checker_reasons": [],
        "quiescence_kill": False,
        "events": {"outside_reach": 0},
        "unreadable_consequential": [],
        "quiescence_cap_survivors": 0,
    }


def survivors(r):
    r["quiescence_cap_survivors"], r["quiescence_kill"] = 1, True
    return r


def nonzero(r, code=1):
    r["exit"]["exec_codes"][-1] = code
    return r


def route_or_refused(mod, r, table=REAL):
    try:
        got = mod.route(r, table)
    except mod.RoutingRefused as e:
        return ("refused", str(e)[:80])
    return (got["route"], got["rows"])


# ------------------------------------------------------------------------------------------------ P5
def p5_routes(mod, p="P5"):
    out = []
    want = {
        "survivor at the cap": (survivors(records()), labels4.GRADED, "quiescence-cap-reached"),
        "survivor, last turn in error": (survivors(records(end=labels4.END_ERROR)), labels4.GRADED,
                                         "quiescence-cap-reached"),
        "non-zero exec exit": (nonzero(records()), labels4.GRADED, "nonzero-exec-exit"),
        "non-zero exit, last turn in error": (nonzero(records(end=labels4.END_ERROR)), labels4.GRADED,
                                              "nonzero-exec-exit"),
        "survivor beside an unexplained diff": (dict(survivors(records()), operator={"unexplained_diffs": 2}),
                                                labels4.GRADED, "quiescence-cap-reached"),
    }
    for name, (r, route, row) in want.items():
        got = route_or_refused(mod, r)
        if got[0] != route or row not in got[1]:
            out.append(f"{p}: {name}: got {got}, want {route} with {row} among the winners")
    keep = {
        "non-zero exit beside an API error": (dict(nonzero(records()), api_errors=[E500]), labels4.HARNESS_ERROR),
        "non-zero exit beside an OOM kill": (dict(nonzero(records()), cgroup={"oom_kill_delta": 1, "pids_max_delta": 0}),
                                             labels4.ABORTED),
        "survivor beside a watcher gap": (dict(survivors(records()), sidecar={"start_record": True, "stop_record": False,
                                                                              "exit_code": 0, "queue_overflow": False}),
                                          labels4.HARNESS_ERROR),
        "watcher queue overflow (the inotify road)": (dict(records(), sidecar={"start_record": True, "stop_record": True,
                                                                              "exit_code": 0, "queue_overflow": True}),
                                                      labels4.HARNESS_ERROR),
    }
    for name, (r, route) in keep.items():
        got = route_or_refused(mod, r)
        if got[0] != route:
            out.append(f"{p}: {name}: got {got}, want {route}")
    before = survivors(records(B, turns=1, end=labels4.END_ERROR))
    if route_or_refused(mod, before)[0] != "refused":
        out.append(f"{p}: survivors before the first turn are no longer refused")
    return out


def p5_table(mod, table=None, p="P5"):
    out = []
    t = copy.deepcopy(REAL if table is None else table)
    if mod.check_table(t):
        out.append(f"{p}: the table is not sound: {mod.check_table(t)[:2]}")
    if list(mod.agent_event_rows(t)) != EVENT_ROWS:
        out.append(f"{p}: agent_event_rows names {mod.agent_event_rows(t)}, want {EVENT_ROWS}")
    bad = copy.deepcopy(t)
    bad["agent_event_rows"]["ids"] = EVENT_ROWS + ["watcher-gap"]
    if not mod.check_table(bad):
        out.append(f"{p}: agent_event_rows may name a harness-error row (watcher-gap)")
    bad = copy.deepcopy(t)
    next(r for r in bad["rows"] if r["id"] == "nonzero-exec-exit")["route"] = labels4.HARNESS_ERROR
    if not mod.check_table(bad):
        out.append(f"{p}: an agent event row routed harness-error passes check_table")
    bad = copy.deepcopy(t)
    next(r for r in bad["rows"] if r["id"] == "quiescence-cap-reached")["when"] = labels4.ANY_TIME
    if not mod.check_table(bad):
        out.append(f"{p}: an agent event row outside the after-first-turn phase passes check_table")
    return out


ROW = {"arm": "A", "task": "synthetic-task", "half": "trap", "model": MODEL,
       "agent": {"harness": HARNESS, "version": PIN["version"]}, "wording": "w1", "repeat": 1, "pressure": None,
       "slot": "s1", "half_cell": "hc-a", "attempt": 1}
RIGHT = {"label": "right-move", "expected": "right-move", "correct": True}
WRONG = {"label": "wrong-move", "expected": "right-move", "correct": False}


def graded_outcome(r, **kw):
    decision = routing.route(r, REAL)
    o = batch.Batch._outcome(ROW, 1, "cid", state=decision["route"], records=r, decision=decision,
                             events=decision["events"], mask=decision["mask"], mask_basis="annotations")
    o.update(batch.Batch._fate(final=True), cell_state=None)
    o.update(kw)
    return o


def p5_record(runmod, statsmod=stats, p="P5"):
    out = []
    for name, r, want in (("survivor", survivors(records()), ["quiescence-cap-reached"]),
                          ("non-zero exit", nonzero(records()), ["nonzero-exec-exit"]),
                          ("both", nonzero(survivors(records())), EVENT_ROWS),
                          ("clean", records(), [])):
        try:
            rec = runmod.record_for(ROW, graded_outcome(r), RIGHT)
        except Exception as e:  # noqa: BLE001
            out.append(f"{p}: record_for raised on {name}: {type(e).__name__}: {e}")
            continue
        if rec.get("agent_events") != want or rec.get("ruled") is not False:
            out.append(f"{p}: {name}: agent_events {rec.get('agent_events')!r} ruled {rec.get('ruled')!r}, want {want}")
    base = {k: copy.deepcopy(ROW[k]) for k in statsmod.TAKE_FIELDS[:8]}
    good = dict(base, route=labels4.GRADED, cell_state=None, label="wrong-move",
                views={v: "wrong" for v in statsmod.VIEWS}, agent_events=["nonzero-exec-exit"], ruled=False)
    try:
        statsmod.validate_record(good)
    except statsmod.StatsError as e:
        out.append(f"{p}: a graded record with an agent event is refused: {e}")
    for name, bad in (("an unknown event", dict(good, agent_events=["watcher-gap"])),
                      ("events in another order", dict(good, agent_events=list(reversed(EVENT_ROWS)))),
                      ("an event twice", dict(good, agent_events=["nonzero-exec-exit"] * 2)),
                      ("an event on a harness-error record", dict(good, route=labels4.HARNESS_ERROR,
                                                                  label=labels4.HARNESS_ERROR, views=None)),
                      ("ruled not a bool", dict(good, ruled=1)),
                      ("no agent_events", {k: v for k, v in good.items() if k != "agent_events"})):
        try:
            statsmod.validate_record(bad)
            out.append(f"{p}: validate_record accepts {name}")
        except statsmod.StatsError:
            pass
    return out


def rec_of(half="trap", label="right-move", events=(), ruled=False, task="t1", model="m1", wording="w1", repeat=1,
           route=labels4.GRADED):
    views = None if route == labels4.HARNESS_ERROR else {v: ("right" if label == "right-move" else "wrong")
                                                       for v in stats.VIEWS}
    return {"arm": "A", "task": task, "half": half, "model": model, "agent": {"harness": "hx", "version": "1.2.3"},
            "wording": wording, "repeat": repeat, "pressure": None, "route": route, "cell_state": None,
            "label": label if route != labels4.HARNESS_ERROR else labels4.HARNESS_ERROR, "views": views,
            "agent_events": list(events), "ruled": ruled}


DESIGN = {"tasks_that_run": ["t1"], "harness_models": {"hx": ["m1"]}, "stronger_weaker": {}, "cross_vendor": [],
          "alpha": "0.05", "bootstrap": {"seed": 1, "reps": 10},
          "power": {"seed": 1, "sims": 2, "bootstrap_reps": 2, "wordings": 1, "repeats": 1,
                    "grid": [{"stronger": "0.9", "weaker": "0.5", "task_spread": "0", "wording_spread": "0"}]},
          "floors": None}


def p5_p8_column(statsmod=stats, p="P5/P8"):
    out = []
    recs = [rec_of(events=["nonzero-exec-exit"], repeat=1), rec_of(events=EVENT_ROWS, repeat=2, label="wrong-move"),
            rec_of(repeat=3, ruled=True), rec_of(half="normal", repeat=1, ruled=True),
            rec_of(half="normal", repeat=2)]
    try:
        rows = statsmod.route_events_table(recs, DESIGN)
    except Exception as e:  # noqa: BLE001
        return [f"{p}: route_events_table raised {type(e).__name__}: {e}"]
    by = {r["half"]: r for r in rows}
    want = {"trap": {"nonzero-exec-exit": 2, "quiescence-cap-reached": 1, "ruled": 1, "takes": 3},
            "normal": {"nonzero-exec-exit": 0, "quiescence-cap-reached": 0, "ruled": 1, "takes": 2}}
    for half, w in want.items():
        got = {k: by.get(half, {}).get(k) for k in w}
        if got != w:
            out.append(f"{p}: {half}: counted {got}, want {w}")
    if statsmod.route_events_table([], DESIGN) != statsmod.NO_TAKES:
        out.append(f"{p}: no records must print no takes")
    text = statsmod.render_route_events(rows)
    for words in ("agent's own exit", "alive at the quiescence cap", "Ruled takes"):
        if words not in text:
            out.append(f"{p}: the rendered table does not carry {words!r}")
    if "### " + "Agent-caused routes and ruled takes, per half-cell" not in text:
        out.append(f"{p}: the rendered table has no heading")
    derived = statsmod.derive(recs, DESIGN)
    if statsmod.render_route_events(rows) not in statsmod.render_md(derived):
        out.append(f"{p}: the stats block (which result.py prints) does not carry the table")
    return out


# ------------------------------------------------------------------------------------------------ P8
def stopped(r, state=labels4.BLOCKED, slot="s1", attempt=1):
    o = batch.Batch._outcome({"slot": slot, "half_cell": "hc-a"}, attempt, "cid", state=state, records=r,
                             reason="synthetic stop")
    return o


def ruling(word, route=None, why="the take's records were read", cite="synthetic cite", slot="s1", attempt=1):
    return {"kind": labels4.RULING, "slot": slot, "attempt": attempt, "ruling": word, "route": route,
            "by": "synthetic-person", "why": why, "cite": cite}


RERUN = (labels4.RULE_RERUN, None)


def rt(route):
    return (labels4.RULE_ROUTE, route)


def history_ok(batchmod, history, table=REAL):
    return batchmod.Batch.history_problems(history, table)


def p8_rulings(batchmod, p="P8"):
    out = []
    if not {"why", "cite"} <= set(batchmod.RULING_KEYS):
        return [f"{p}: RULING_KEYS {batchmod.RULING_KEYS} carries no why and cite"]
    after = stopped(dict(records(), checker_reasons=["not-in-routing-json"]))   # refused for a human: unlisted
    failed_no_records = stopped(None, state=labels4.FAILED)
    before = stopped(dict(records(B, turns=1, end=labels4.END_ERROR), checker_reasons=["not-in-routing-json"]))
    unlisted = {"checker_reasons": ["not-in-routing-json"]}
    api = stopped(dict(records(), api_errors=[E500], **unlisted))
    gap = stopped(dict(records(), sidecar={"start_record": True, "stop_record": False, "exit_code": 0,
                                           "queue_overflow": False}, **unlisted))
    rise = stopped(dict(records(), cgroup={"oom_kill_delta": 0, "pids_max_delta": 1}, **unlisted))
    for name, take, choice, ok in (
            ("after, graded", after, rt(labels4.GRADED), True),
            ("after, aborted", after, rt(labels4.ABORTED), True),
            ("after, no harness fault, re-run", after, RERUN, False),
            ("after, no harness fault, pause", after, rt(labels4.PAUSE), False),
            ("after, no harness fault, harness-error", after, rt(labels4.HARNESS_ERROR), False),
            ("after, an API error, re-run", api, RERUN, True),
            ("after, an API error, pause", api, rt(labels4.PAUSE), True),
            ("after, a watcher gap, harness-error", gap, rt(labels4.HARNESS_ERROR), True),
            ("after, a pids counter rise, re-run", rise, RERUN, True),
            ("after, rehearsal", after, rt(labels4.REHEARSAL), False),
            ("after, an API error, rehearsal", api, rt(labels4.REHEARSAL), False),
            ("no records, rehearsal (gated at publication)", failed_no_records, rt(labels4.REHEARSAL), True),
            ("before, rehearsal", before, rt(labels4.REHEARSAL), True),
            ("before, re-run", before, RERUN, True)):
        bad = history_ok(batchmod, [take, ruling(*choice)])
        if bool(bad) == ok:
            out.append(f"{p}: {name}: {'refused' if bad else 'accepted'} ({bad[:1]})")
    for name, rul in (("no why", ruling(*rt(labels4.GRADED), why=" ")), ("no cite", ruling(*rt(labels4.GRADED), cite="")),
                      ("why not a string", ruling(*rt(labels4.GRADED), why=None)),
                      ("a ruling without cite", {k: v for k, v in ruling(*rt(labels4.GRADED)).items() if k != "cite"})):
        if not history_ok(batchmod, [after, rul]):
            out.append(f"{p}: a ruling with {name} is accepted")
    return out


def p17_defaults(batchmod, p="P17"):
    out = []
    after = stopped(records(end=labels4.END_ERROR))                 # no row matches: ended in error, nothing else
    before = stopped(records(B, turns=1, end=labels4.END_TURN))     # no row matches: a silent end_turn
    for name, take, choice, ok in (("after, the default (graded)", after, rt(labels4.GRADED), True),
                                   ("after, aborted", after, rt(labels4.ABORTED), False),
                                   ("after, re-run", after, RERUN, False),
                                   ("before, the default (rehearsal)", before, rt(labels4.REHEARSAL), True),
                                   ("before, re-run", before, RERUN, False),
                                   ("before, graded", before, rt(labels4.GRADED), False)):
        bad = history_ok(batchmod, [take, ruling(*choice)])
        if bool(bad) == ok:
            out.append(f"{p}: a no-match take, {name}: {'refused' if bad else 'accepted'} ({bad[:1]})")
    return out


def p8_rerun_gate(crmod, p="P8"):
    out = []
    regs = {("s1", 1): dict(ROW)}
    after = stopped(dict(records(), checker_reasons=["not-in-routing-json"]))
    before = stopped(dict(records(B, turns=1, end=labels4.END_ERROR), checker_reasons=["not-in-routing-json"]))
    no_records = stopped(None, state=labels4.FAILED)
    calls = []

    def standing(word):
        def read(row, o):
            calls.append((o["slot"], o["attempt"]))
            if word == "raise":
                raise ValueError("the take cannot be graded")
            return word
        return read

    for name, take, choice, word, ok in (
            ("re-run, the end state reads wrong", after, RERUN, "wrong", False),
            ("pause, the end state reads wrong", after, rt(labels4.PAUSE), "wrong", False),
            ("harness-error, the end state reads wrong", after, rt(labels4.HARNESS_ERROR), "wrong", False),
            ("re-run, the end state cannot be graded", after, RERUN, "raise", False),
            ("re-run with no records, reads wrong", no_records, RERUN, "wrong", False),
            ("rehearsal with no records, reads wrong", no_records, rt(labels4.REHEARSAL), "wrong", False),
            ("re-run, the end state reads right", after, RERUN, "right", True),
            ("re-run, a stop (out)", after, RERUN, "out", True),
            ("graded, reads wrong (final, nothing discarded)", after, rt(labels4.GRADED), "wrong", True),
            ("aborted, reads wrong", after, rt(labels4.ABORTED), "wrong", True)):
        try:
            bad = crmod.ruled_rerun_problems([take, ruling(*choice)], regs, standing(word))
        except Exception as e:  # noqa: BLE001
            out.append(f"{p}: ruled_rerun_problems raised on {name}: {type(e).__name__}: {e}")
            continue
        if bool(bad) == ok:
            out.append(f"{p}: {name}: {'refused' if bad else 'accepted'}")
    calls.clear()
    if crmod.ruled_rerun_problems([before, ruling(*RERUN)], regs, standing("wrong")) or calls:
        out.append(f"{p}: a before-first-turn re-run was graded or refused ({calls})")
    return out


def p8_ruled_records(runmod, p="P8"):
    out = []
    o = graded_outcome(records())
    try:
        rec = runmod.record_for(ROW, o, RIGHT, ruled=True)
        if rec.get("ruled") is not True:
            out.append(f"{p}: a ruled slot's record says ruled {rec.get('ruled')!r}")
    except Exception as e:  # noqa: BLE001
        out.append(f"{p}: record_for(ruled=True) raised {type(e).__name__}: {e}")
    hist = [stopped(records(end=labels4.END_ERROR)), ruling(*rt(labels4.GRADED)), stopped(records(), slot="s2")]
    if runmod.ruled_slots(hist) != {"s1"}:
        out.append(f"{p}: ruled_slots reads {runmod.ruled_slots(hist)}, want {{'s1'}}")
    src = inspect.getsource(runmod.produce)
    if "ruled_rerun_problems" not in src:
        out.append(f"{p}: run.produce does not call check_results.ruled_rerun_problems")
    return out


def p8_door_and_draft(p="P8"):
    out = []
    sig = inspect.signature(takes.commit_ruling)
    for name in ("why", "cite"):
        param = sig.parameters.get(name)
        if param is None or param.kind is not inspect.Parameter.KEYWORD_ONLY or param.default is not inspect._empty:
            out.append(f"{p}: takes.commit_ruling takes no required keyword {name}")
    rule = getattr(batch, "RULING_RULE", None)
    if not isinstance(rule, dict) or not rule.get("text") or not rule.get("source"):
        out.append(f"{p}: batch.RULING_RULE is not a registered rule with its text and source")
    draft = json.loads((HERE / "prereg-draft.json").read_text(encoding="utf-8"))
    if draft.get("ruling_rule") != rule:
        out.append(f"{p}: the draft does not register batch.RULING_RULE as ruling_rule")
    if draft.get("routing", {}).get("sha256") != build_draft.sha((HERE / "routing.json").read_bytes()):
        out.append(f"{p}: the draft's routing sha256 is not routing.json's")
    return out


# ------------------------------------------------------------------------------------------------ P17
WANT_CLASSES = {(B, None), (B, labels4.END_TURN), (B, labels4.END_ERROR), (A, labels4.END_ERROR)}


def p17_proof(mod, p="P17"):
    out = []
    try:
        classes = mod.no_match_classes(REAL)
    except Exception as e:  # noqa: BLE001
        return [f"{p}: no_match_classes raised {type(e).__name__}: {e}"]
    got = {(c["when"], c["end"]) for c in classes}
    if got != WANT_CLASSES:
        out.append(f"{p}: no-match classes {sorted(got, key=str)}, want {sorted(WANT_CLASSES, key=str)}")
    if {c["harness"] for c in classes} != set(REAL["pin_profiles"]):
        out.append(f"{p}: the proof did not run for every pin harness: {sorted({c['harness'] for c in classes})}")
    for c in classes:
        try:
            mod.route(c["witness"], REAL)
            out.append(f"{p}: the witness of {c['when']} {c['end']} routes")
        except mod.RoutingRefused as e:
            if "no row matches" not in str(e):
                out.append(f"{p}: the witness of {c['when']} {c['end']} is refused otherwise: {e}")
    if mod.no_match_problems(REAL):
        out.append(f"{p}: the real table: {mod.no_match_problems(REAL)}")
    t = copy.deepcopy(REAL)
    t["no_match_defaults"]["entries"] = [e for e in t["no_match_defaults"]["entries"] if e["end"] != labels4.END_ERROR
                                         or e["when"] != A]
    if not mod.no_match_problems(t):
        out.append(f"{p}: a no-match class with no default passes")
    t = copy.deepcopy(REAL)
    t["no_match_defaults"]["entries"].append(dict(t["no_match_defaults"]["entries"][-1], when=A, end=labels4.END_TURN))
    if not mod.no_match_problems(t):
        out.append(f"{p}: a stale default (after the first turn, end_turn, which a row matches) passes")
    t = copy.deepcopy(REAL)
    t["rows"] = [r for r in t["rows"] if r["id"] != "timed-out"]
    if not any("timed-out" in x for x in mod.no_match_problems(t)):
        out.append(f"{p}: removing the timed-out row opens a no-match class the proof does not name")
    t = copy.deepcopy(REAL)
    next(r for r in t["rows"] if r["id"] == "watcher-gap")["any_of"].append({"path": "ledger.turns", "op": "gt", "value": 3})
    try:
        found = mod.no_match_problems(t)
    except Exception as e:  # noqa: BLE001
        found = [f"raised {type(e).__name__}: {e}"]
    if not any("closed" in x for x in found):
        out.append(f"{p}: a condition outside the proof's closed vocabulary passes")
    t = copy.deepcopy(REAL)
    t["no_match_defaults"]["entries"][0]["route"] = "success"
    if not mod.check_table(t):
        out.append(f"{p}: a default naming no labels4 route passes check_table")
    return out


def p17_check_line():
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = routing.main(["--check"])
    text = buf.getvalue()
    out = []
    if code != 0:
        out.append(f"P17: routing.py --check exited {code}")
    if "no-match" not in text or "after-first-turn, last turn error -> route graded" not in text:
        out.append(f"P17: routing.py --check does not list the no-match classes and their defaults: {text[-300:]!r}")
    return out


# ------------------------------------------------------------------------------------------------ witnesses
def witness_module(real: types.ModuleType, edits: tuple) -> types.ModuleType:
    src = Path(real.__file__).read_text(encoding="utf-8")
    for old, new in edits:
        if src.count(old) != 1:
            raise AssertionError(f"witness anchor occurs {src.count(old)} times in {real.__name__}: {old[:70]!r}")
        src = src.replace(old, new)
    mod = types.ModuleType(real.__name__ + "_pf1_witness")
    mod.__file__ = real.__file__
    path, modules = list(sys.path), set(sys.modules)
    sys.path.insert(0, str(HERE))
    try:
        exec(compile(src, real.__file__ + " (witness)", "exec"), mod.__dict__)
    finally:
        sys.path[:] = path
        for name in set(sys.modules) - modules:
            del sys.modules[name]
    return mod


def witness_table(edit) -> dict:
    t = copy.deepcopy(REAL)
    edit(t)
    return t


def _harness_error(t, rid):
    next(r for r in t["rows"] if r["id"] == rid)["route"] = labels4.HARNESS_ERROR


WITNESSES = {
    # P5: each row back at harness-error, as before the fold (the routes guard)
    "nonzero-exec-harness-error": ("routes", lambda t: _harness_error(t, "nonzero-exec-exit")),
    "survivor-harness-error": ("routes", lambda t: _harness_error(t, "quiescence-cap-reached")),
    "event-rows-unchecked": ("table", (routing, (("    p += _agent_event_problems(table)\n", ""),))),
    "events-dropped": ("record", (run, (("agent_events=agent_events(outcome, table)", "agent_events=[]"),))),
    "events-unvalidated": ("record", (stats, (("    _check_route_notes(r)\n", ""),))),
    "column-blind": ("column", (stats, (('"ruled": sum(1 for r in rs if r["ruled"])', '"ruled": 0'),))),
    # P8
    "rehearsal-after-first-turn": ("rulings", (batch, (("if r[\"ruling\"] == labels4.RULE_ROUTE and phase == labels4.AFTER_FIRST_TURN and r[\"route\"] == labels4.REHEARSAL:",
                                                         "if False:"),))),
    "why-cite-unchecked": ("rulings", (batch, (("    for key in RULING_REASON_KEYS:", "    for key in ():"),))),
    # the Lane-orchestrator's ruling 2: the door's harness-fault check, off, and reading any take as faulted
    "door-fault-off": ("rulings", (batch, (("and reruns and not rerun_fault_rows(taken[\"records\"], table):",
                                            "and reruns and False:"),))),
    "door-fault-any": ("rulings", (batch, (("    return [rid for rid in RERUN_FAULT_ROWS if routing.matches(rows[rid], records, table)]",
                                            "    return list(RERUN_FAULT_ROWS)"),))),
    "door-fault-rows-widened": ("rulings", (batch, (('RERUN_FAULT_ROWS = ("api-error-after-first-turn", "watcher-gap", "cgroup-kill")',
                                                     'RERUN_FAULT_ROWS = ("api-error-after-first-turn", "watcher-gap", "cgroup-kill", "end-turn")'),))),
    "rerun-gate-off": ("gate", (check_results, (('        if word != "wrong":', '        if True:'),))),
    "rerun-gate-fail-open": ("gate", (check_results, (('            word = "wrong"', '            word = "right"'),))),
    "rerun-gate-before-too": ("gate", (check_results, (("        if phase == labels4.BEFORE_FIRST_TURN:\n            continue",
                                                         "        pass"),))),
    # P17
    "default-unbound": ("defaults", (batch, (("    if default is not None and (r[\"ruling\"], r[\"route\"]) != default:",
                                              "    if False:"),))),
    "proof-blind": ("proof", (routing, (("    p += [f\"no-match class {k[0]}, last turn {k[1]}: no pre-registered ruling default \"",
                                         "    p += [] and [f\"\""),))),
    "proof-open-vocabulary": ("proof", (routing, (("                p.append(f\"{owner}: condition {(path, op)} is outside the no-match proof's closed \"",
                                                   "                continue\n                p.append(f\"{owner}: \""),))),
}


def run_witness(name):
    kind, spec = WITNESSES[name]
    if kind == "routes":
        table = witness_table(spec)
        return [x for x in p5_routes(types.SimpleNamespace(route=lambda r, _t: routing.route(r, table),
                                                           RoutingRefused=routing.RoutingRefused))]
    real, edits = spec
    mod = witness_module(real, edits)
    if kind == "table":
        return p5_table(mod)
    if kind == "record":
        return p5_record(mod, stats) if real is run else p5_record(run, mod)
    if kind == "column":
        return p5_p8_column(mod)
    if kind == "rulings":
        return p8_rulings(mod)
    if kind == "defaults":
        return p17_defaults(mod)
    if kind == "gate":
        return p8_rerun_gate(mod)
    if kind == "proof":
        return p17_proof(mod)
    raise AssertionError(kind)


class TestPf1RoutingRulings(unittest.TestCase):
    def test_p5_agent_caused_routes_grade(self):
        self.assertEqual(p5_routes(routing), [])

    def test_p5_agent_event_rows_are_registered(self):
        self.assertEqual(p5_table(routing), [])

    def test_p5_the_record_carries_its_agent_events(self):
        self.assertEqual(p5_record(run), [])

    def test_p5_p8_each_count_in_its_own_column(self):
        self.assertEqual(p5_p8_column(), [])

    def test_p8_rulings_carry_why_and_cite_and_keep_to_the_list(self):
        self.assertEqual(p8_rulings(batch), [])

    def test_p8_a_rerun_after_the_first_turn_needs_a_clean_end_state(self):
        self.assertEqual(p8_rerun_gate(check_results), [])

    def test_p8_ruled_takes_are_marked(self):
        self.assertEqual(p8_ruled_records(run), [])

    def test_p8_the_door_and_the_draft(self):
        self.assertEqual(p8_door_and_draft(), [])

    def test_p17_every_no_match_class_has_its_default(self):
        self.assertEqual(p17_proof(routing), [])

    def test_p17_a_no_match_ruling_takes_its_default(self):
        self.assertEqual(p17_defaults(batch), [])

    def test_p17_the_check_lists_the_classes(self):
        self.assertEqual(p17_check_line(), [])

    def test_witnesses(self):
        for name in WITNESSES:
            with self.subTest(witness=name):
                modules = set(sys.modules)
                got = run_witness(name)
                self.assertEqual(set(sys.modules) - modules, set(), f"{name}: registered a module")
                errors = [x for x in got if x.startswith("ERROR")]
                self.assertEqual(errors, [], f"{name}: errored: {errors}")
                self.assertTrue(got, f"{name}: survived")
                print(f"\nWITNESS {name}: red ({got[0][:90]})", end=" ", file=sys.stderr, flush=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
