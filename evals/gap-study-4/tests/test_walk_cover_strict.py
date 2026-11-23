#!/usr/bin/env python3
"""Lane pf1-walk-cover-strict: OD131, Javier's "walk-cover strict" (decision.jsonl, 25 Oct 2026).

OD131: a Claude walk counts as covered only if it rechecks clean under the harness as it will be frozen. Before this
lane, coverage left a graded walk out only when a checker reason was constant-bound (check_take.CONSTANT_BOUND_REASONS)
or its reading was stale, so harness-condition-violated and nested-agent still covered, and a recheck round of the
old walks under the constants in force would have read arm A complete on walks that ran a harness OD131 rejects.

The rule (the lane orchestrator's ruled design): a walk walk_plan names strict (arm A, OD131's wording; arm O, OD132's,
Javier, 26 Oct 2026: "walk-cover-o strict") is not counted
when its effective checker reading (the latest recheck, else check.json) carries any reason that the routing table as
HEAD's commit holds it routes to harness-error. The set is derived from that table by the table's own evaluator, never
typed; arm G, deferred, counts as before.

  S1.derived     pending_walk.harness_error_reasons equals an independent derivation from the table (rows whose route
                 is harness-error; their any_of and all_of conditions on checker_reasons); on the live table it holds
                 harness-condition-violated, nested-agent and transcript-mismatch; a synthetic table without the
                 generic operator-reason row, with that row routed graded, or with one added has-row (in any_of, or
                 in all_of; a none_of reason stops the route and never joins the set) moves the set to what the
                 derivation says; on HEAD's table the set holds every reason a non-graded after-first-turn row names
                 (review MINOR 4), and without the generic row it would not, so the instrument is armed
  S2.head        pending_walk.head_routing_table reads the table as HEAD's commit holds it, never the working tree:
                 an uncommitted edit moves nothing, a new commit moves the set; a table routing.check_table refuses,
                 bytes that are not JSON and a folder that is no repository raise StrictUnreadable; a GIT_DIR in the
                 environment is not read
  S3.standing    checker_standing(strict=...) : a clean reading under the constants in force counts; one carrying a
                 strict reason reads STRICT_WHY; a reason outside the set counts; without strict nothing changes; a
                 constant-bound reason still reads constant-bound; on the recheck road the latest recheck decides (a
                 stale clean check.json with a recheck carrying harness-condition-violated reads STRICT_WHY: the
                 plan's named mutant, w165's case); on the pending road the same; a set derived from a table whose
                 vocabulary lacks a reason counts that reason as a hit, a known unrouted reason still counts
                 (review MINOR 2)
  S4.uncounted   uncounted_walks(base, walks, strict_walks): only the strict walks are judged strictly; a HEAD table
                 that cannot be read leaves every strict walk uncounted, fail closed, and no other; with no strict walk
                 the table is never read; a pending walk with a graded regrade and a nested-agent recheck reads
                 STRICT_WHY through coverage_status and uncounted_walks (review MINOR 1); with operator-lines added to
                 the working tree's table and absent at HEAD, a strict walk carrying it is not counted (MINOR 2)
  S5.records     the real register at this head: walk_plan's strict arms are A and O (OD131, OD132); every arm A or O
                 walk its coverage counts has an effective reading with no reason HEAD's routing routes to
                 harness-error, and every arm G walk (deferred, as coded) reads exactly as it does without the rule.
                 The heavy reading of arm O after its regrades and rechecks is tests/test_walk_cover_o_records.py
  S6.witnesses   each anchored mutant of pending_walk.py (below) turns a case red

Red first: before the lane every clause fails by its own assertion. Fixtures: temporary folders and temporary git
repositories only; S5 reads the study's own register and walk records, read-only. No model, network or container.

    python3 -B -W ignore evals/gap-study-4/tests/test_walk_cover_strict.py
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

ct = pw = routing = wr = None
OLD = "0" * 64
HCV, NESTED, MISMATCH = "harness-condition-violated", "nested-agent", "transcript-mismatch"
GENERIC_ROW = "operator-reason-after-first-turn"


def setUpModule():
    global ct, pw, routing, wr
    import check_take as ct
    import pending_walk as pw
    import routing
    import walk_register as wr


# ---- the tests' own derivation of the set, never pending_walk's ----

def derive(table: dict) -> set:
    out = set()
    for row in table["rows"]:
        if row["route"] != "harness-error":
            continue
        for cond in list(row.get("any_of", [])) + list(row.get("all_of", [])):
            if cond.get("path") != "checker_reasons":
                continue
            if cond["op"] == "in_operator_reasons":
                out |= set(table["operator_reasons"])
            elif cond["op"] == "has":
                out.add(cond["value"])
            else:
                raise AssertionError(f"S1.derived: the derivation knows no op {cond['op']!r}")
    return out


def live_table() -> dict:
    return json.loads((HERE / "routing.json").read_text())


def without_generic(table: dict) -> dict:
    t = copy.deepcopy(table)
    t["rows"] = [r for r in t["rows"] if r["id"] != GENERIC_ROW]
    return t


def generic_graded(table: dict) -> dict:
    t = copy.deepcopy(table)
    for r in t["rows"]:
        if r["id"] == GENERIC_ROW:
            r["route"] = "graded"
    return t


def with_has_row(table: dict, reason: str, *, all_of=False, none_of=None) -> dict:
    t = without_generic(table)
    has = [{"path": "checker_reasons", "op": "has", "value": reason}]
    row = {"id": "synthetic-has-row", "when": "after-first-turn", "route": "harness-error",
           "any_of": [{"path": "api_errors", "op": "nonempty"}] if all_of else has,
           "source": "a synthetic row of test_walk_cover_strict"}
    if all_of:
        row["all_of"] = has
    if none_of is not None:                      # review NIT 1: a none_of reason stops the route, never joins the set
        row["none_of"] = [{"path": "checker_reasons", "op": "has", "value": none_of}]
    t["rows"].append(row)
    return t


def without_reason(table: dict, reason: str) -> dict:
    t = copy.deepcopy(table)
    t["operator_reasons"] = [r for r in t["operator_reasons"] if r != reason]
    return t


def before_reason(table: dict, reason: str) -> dict:
    """The table as it stood before `reason` was added to the vocabulary: without_reason, and every row condition
    that reads it through op has dropped too (a row left with no any_of is dropped). Since pre-freeze review 2 MAJOR 1
    (lane fold2/la1) the agent-reachable-reason row names operator-lines, and routing.check_table refuses a has-read of
    a reason outside the vocabulary, so a HEAD table that only drops the vocabulary entry is unreadable."""
    t = without_reason(table, reason)
    rows = []
    for row in t["rows"]:
        for key in ("any_of", "all_of", "none_of"):
            if key in row:
                row[key] = [c for c in row[key] if not (c.get("op") == "has" and c.get("value") == reason)]
                if not row[key] and key != "any_of":
                    del row[key]
        if row.get("any_of", True):
            rows.append(row)
    t["rows"] = rows
    return t


def non_graded_names(table: dict) -> set:
    """Review MINOR 4: every reason a non-graded row of the after-first-turn phase (or any phase) names through an
    any_of or all_of condition on checker_reasons; the tests' own reading."""
    out = set()
    for row in table["rows"]:
        if row["route"] == "graded" or row["when"] not in ("after-first-turn", "any"):
            continue
        for cond in list(row.get("any_of", [])) + list(row.get("all_of", [])):
            if cond.get("path") == "checker_reasons":
                out |= set(table["operator_reasons"]) if cond["op"] == "in_operator_reasons" else {cond["value"]}
    return out


# ---- walk folders ----

AGENT = {"agent_calls": 0, "subagents": {"calls": [], "models": [], "stream_file_differences": 0},
         "nested_cli_calls": 0}


def check_doc(walk: str, reasons, digest: str) -> dict:
    return {"walk": walk, "checked": True, "checker_reasons": list(reasons), "events": {"outside_reach": 0},
            "route": "graded", "route_refused": None, "checker_constants_sha256": digest, "no_output_nudges": 0,
            **AGENT}


def recheck_bytes(walk: str, n: int, digest: str, reasons) -> bytes:
    doc = {"schema": 1, "walk": walk, "n": n, "checker_constants_sha256": digest, "checker_reasons": list(reasons),
           "supersedes": "check.json" if n == 1 else f"recheck-{n - 1}.json", "no_output_nudges": 0, **AGENT}
    return (json.dumps(doc, indent=2, sort_keys=True) + "\n").encode()


class Folder:
    """A rehearsals folder: graded walks, each with its check.json, and optionally one recheck each."""

    def __init__(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="cover-strict-"))
        self.base = self.tmp / "rehearsals"
        self.base.mkdir()
        self.rechecks: list = []

    def walk(self, walk: str, reasons, digest=None, *, recheck=None, pending=False):
        folder = self.base / walk
        folder.mkdir()
        if pending:
            (folder / "check.json").write_text(json.dumps({"walk": walk, "status": pw.PENDING, "why": "a stand-in"}))
            (folder / "grade.json").write_text(json.dumps({"graded": False, "status": pw.PENDING, "why": "a stand-in"}))
        else:
            (folder / "grade.json").write_text('{"graded": true, "row": {}, "grade": {"label": "stand-in"}}\n')
            (folder / "check.json").write_text(json.dumps(check_doc(walk, reasons, digest or ct.checker_constants_sha256())))
        if recheck is not None:
            digest_r, reasons_r = recheck
            raw = recheck_bytes(walk, 1, digest_r, reasons_r)
            (folder / "recheck-1.json").write_bytes(raw)
            self.rechecks.append({"walk": walk, "file": "recheck-1.json", "n": 1, "checker_constants_sha256": digest_r,
                                  "sha256": hashlib.sha256(raw).hexdigest()})
            (self.base / wr.REGISTER_NAME).write_text(json.dumps({"schema": 2, "walks": [], "rechecks": self.rechecks}))
        return walk

    def close(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


# ---- temporary repositories holding a routing.json ----

def git(repo: Path, *args, env=None):
    base = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    base.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull})
    got = subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                          "-c", "commit.gpgsign=false", *args], capture_output=True, text=True, env=env or base)
    if got.returncode != 0:
        raise AssertionError(f"git {args}: {got.stderr}")
    return got.stdout


def repo_with(table, tmp: Path, name="repo") -> Path:
    repo = tmp / name
    repo.mkdir()
    git(repo, "init", "-q")
    (repo / "routing.json").write_text(table if isinstance(table, str) else json.dumps(table, indent=1))
    git(repo, "add", "routing.json")
    git(repo, "commit", "-q", "-m", "routing")
    return repo


# ---- the cases (each returns its problem lines; a mutant module stands in for pending_walk) ----

def derived_cases(mod) -> list:
    out = []
    table = live_table()
    try:
        got = mod.harness_error_reasons(table)
    except Exception as exc:                     # noqa: BLE001 - a raise is a failed case, never an error
        return [f"S1.derived: harness_error_reasons raised {exc!r}"]
    if set(got) != derive(table):
        out.append(f"S1.derived: live table {sorted(got)} != the derivation {sorted(derive(table))}")
    if not {HCV, NESTED, MISMATCH} <= set(got):
        out.append(f"S1.derived: the live set lacks one of {HCV}, {NESTED}, {MISMATCH}: {sorted(got)}")
    for name, t in (("no generic row", without_generic(table)), ("generic row graded", generic_graded(table)),
                    ("one has-row", with_has_row(table, NESTED)),
                    ("one all_of has-row", with_has_row(table, HCV, all_of=True)),
                    ("one has-row with a none_of", with_has_row(table, HCV, none_of=NESTED))):
        if routing.check_table(t):
            out.append(f"S1.derived: {name}: the synthetic table is refused: {routing.check_table(t)[:2]}")
        try:
            got = set(mod.harness_error_reasons(t))
        except Exception as exc:                 # noqa: BLE001
            out.append(f"S1.derived: {name}: raised {exc!r}")
            continue
        if got != derive(t):
            out.append(f"S1.derived: {name}: {sorted(got)} != the derivation {sorted(derive(t))}")
    try:                                         # review MINOR 4: on HEAD's table no non-graded reason is left out
        head = mod.head_routing_table()
        got = set(mod.harness_error_reasons(head))
    except Exception as exc:                     # noqa: BLE001
        return out + [f"S1.derived: HEAD's table raised {exc!r}"]
    if not non_graded_names(head) <= got:
        out.append(f"S1.derived: HEAD's set leaves out the non-graded reasons "
                   f"{sorted(non_graded_names(head) - got)}")
    if non_graded_names(without_generic(head)) <= derive(without_generic(head)):
        out.append("S1.derived: the MINOR 4 instrument is not armed: without the generic row an aborted-only reason "
                   "should fall outside the set")
    return out


def head_cases(mod) -> list:
    out = []
    tmp = Path(tempfile.mkdtemp(prefix="cover-strict-git-"))
    try:
        table = live_table()
        repo = repo_with(table, tmp)
        (repo / "routing.json").write_text(json.dumps(without_generic(table)))       # uncommitted: HEAD still full
        with mock.patch.object(routing, "TABLE_PATH", str(repo / "routing.json")):
            try:
                got = set(mod.harness_error_reasons(mod.head_routing_table()))
            except Exception as exc:             # noqa: BLE001
                return [f"S2.head: the HEAD read raised {exc!r}"]
            if got != derive(table):
                out.append(f"S2.head: an uncommitted edit moved the set: {sorted(got)}")
            git(repo, "commit", "-q", "-am", "the generic row dropped")
            got = set(mod.harness_error_reasons(mod.head_routing_table()))
            if got != derive(without_generic(table)):
                out.append(f"S2.head: a new commit did not move the set: {sorted(got)}")
            other = repo_with(table, tmp, "other")                                     # GIT_DIR names another repo
            with mock.patch.dict(os.environ, {"GIT_DIR": str(other / ".git")}):
                got = set(mod.harness_error_reasons(mod.head_routing_table()))
            if got != derive(without_generic(table)):
                out.append("S2.head: a GIT_DIR in the environment was read")
        bad_row = copy.deepcopy(table)
        bad_row["rows"][0]["route"] = "no-such-route"
        for name, text in (("a table check_table refuses", json.dumps(bad_row)), ("not JSON", "{not json"),
                           ("a list", "[]")):
            repo = repo_with(text, tmp, name.replace(" ", "-"))
            with mock.patch.object(routing, "TABLE_PATH", str(repo / "routing.json")):
                try:
                    mod.head_routing_table()
                    out.append(f"S2.head: {name} was read")
                except mod.StrictUnreadable:
                    pass
                except Exception as exc:         # noqa: BLE001
                    out.append(f"S2.head: {name} raised {exc!r}, not StrictUnreadable")
        plain = tmp / "plain"
        plain.mkdir()
        (plain / "routing.json").write_text(json.dumps(table))
        with mock.patch.object(routing, "TABLE_PATH", str(plain / "routing.json")):
            try:
                mod.head_routing_table()
                out.append("S2.head: a folder that is no repository was read")
            except mod.StrictUnreadable:
                pass
            except Exception as exc:             # noqa: BLE001
                out.append(f"S2.head: no repository raised {exc!r}, not StrictUnreadable")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return out


def standing_cases(mod) -> list:
    out = []
    strict = frozenset({HCV, NESTED})
    f = Folder()
    try:
        def want(walk, got_want, **kw):
            try:
                got = mod.checker_standing(f.base, walk, **kw)
            except Exception as exc:             # noqa: BLE001
                out.append(f"S3.standing: {walk} {kw}: raised {exc!r}")
                return
            ok = got_want(got) if callable(got_want) else got == got_want
            if not ok:
                out.append(f"S3.standing: {walk} {sorted(kw)}: {got!r}")
        strict_why = lambda r: (lambda got: isinstance(got, str) and got.startswith(mod.STRICT_WHY)  # noqa: E731
                                and got.endswith(r))
        starts = lambda p: (lambda got: isinstance(got, str) and got.startswith(p))  # noqa: E731
        f.walk("w-clean", [])
        f.walk("w-hcv", [HCV])
        f.walk("w-nested", [NESTED])
        f.walk("w-other", ["operator-lines"])
        f.walk("w-bound", ["readers-disagree", HCV])
        f.walk("w-stale-hcv", [HCV], OLD)
        want("w-clean", None, strict=strict)
        want("w-hcv", strict_why(HCV), strict=strict)
        want("w-nested", strict_why(NESTED), strict=strict)
        want("w-other", None, strict=strict)
        want("w-bound", starts("constant-bound checker reason"), strict=strict)
        want("w-stale-hcv", lambda got: got is not None, strict=strict)
        for w in ("w-clean", "w-hcv", "w-nested", "w-other"):
            want(w, None)                        # without strict, nothing changes
        # review MINOR 2: a set derived from a table whose vocabulary lacks a reason makes that reason a strict hit;
        # a reason the table knows and does not route to harness-error still counts
        try:
            narrow = mod.harness_error_reasons(without_reason(live_table(), "operator-lines"))
            unrouted = mod.harness_error_reasons(generic_graded(live_table()))
        except Exception as exc:                 # noqa: BLE001
            narrow = unrouted = None
            out.append(f"S3.standing: harness_error_reasons raised {exc!r}")
        if narrow is not None:
            want("w-other", strict_why("operator-lines"), strict=narrow)
            want("w-hcv", strict_why(HCV), strict=narrow)
            want("w-hcv", None, strict=unrouted)
            want("w-clean", None, strict=narrow)
        f.close()
        f = Folder()                             # the recheck road: the latest recheck is the reading
        f.walk("w165", [], OLD, recheck=(ct.checker_constants_sha256(), [HCV]))
        f.walk("w-rclean", [HCV], OLD, recheck=(ct.checker_constants_sha256(), []))
        f.walk("w-pend", None, pending=True, recheck=(ct.checker_constants_sha256(), [NESTED]))
        f.walk("w-pclean", None, pending=True, recheck=(ct.checker_constants_sha256(), []))
        want("w165", strict_why(HCV), strict=strict)
        want("w165", None)
        want("w-rclean", None, strict=strict)
        want("w-pend", strict_why(NESTED), pending=True, strict=strict)
        want("w-pend", None, pending=True)
        want("w-pclean", None, pending=True, strict=strict)
        try:
            got = mod.coverage_status(f.base, "w165", strict=strict)
        except Exception as exc:                 # noqa: BLE001
            got = repr(exc)
        if not strict_why(HCV)(got):
            out.append(f"S3.standing: coverage_status does not pass strict on: {got!r}")
    finally:
        f.close()
    return out


def uncounted_cases(mod) -> list:
    out = []
    f = Folder()
    try:
        a, o, c = f.walk("w-a", [HCV]), f.walk("w-o", [HCV]), f.walk("w-c", [])
        calls = []

        def counted_head():
            calls.append(1)
            return live_table()
        with mock.patch.object(mod, "head_routing_table", counted_head):
            try:
                got = mod.uncounted_walks(f.base, [a, o, c], [a, c])
            except Exception as exc:             # noqa: BLE001
                return [f"S4.uncounted: raised {exc!r}"]
        if set(got) != {a} or not str(got.get(a, "")).startswith(mod.STRICT_WHY):
            out.append(f"S4.uncounted: only the strict walk carrying {HCV} is uncounted: {got!r}")
        if len(calls) != 1:
            out.append(f"S4.uncounted: the HEAD table is read once per call, read {len(calls)} times")

        def unreadable():
            raise mod.StrictUnreadable("a stand-in")
        with mock.patch.object(mod, "head_routing_table", unreadable):
            try:
                got = mod.uncounted_walks(f.base, [a, o, c], [a, c])
            except Exception as exc:             # noqa: BLE001
                return out + [f"S4.uncounted: an unreadable HEAD table raised {exc!r}"]
        if set(got) != {a, c} or not all(str(got[w]).startswith(mod.STRICT_UNREAD) for w in (a, c)):
            out.append(f"S4.uncounted: an unreadable HEAD table leaves every strict walk uncounted, no other: {got!r}")

        def never():
            raise AssertionError("read")
        with mock.patch.object(mod, "head_routing_table", never):
            try:
                got = mod.uncounted_walks(f.base, [a, o, c])
            except Exception as exc:             # noqa: BLE001
                return out + [f"S4.uncounted: with no strict walk the HEAD table was read: {exc!r}"]
        if got != {}:
            out.append(f"S4.uncounted: with no strict walk every graded clean-or-not walk counts as before: {got!r}")
        # review MINOR 1: a pending walk whose verified regrade grades it and whose recheck carries nested-agent reads
        # STRICT_WHY through coverage_status and uncounted_walks (the regrade's re-derivation is stood in: graded)
        p = f.walk("w-p", None, pending=True, recheck=(ct.checker_constants_sha256(), [NESTED]))
        with mock.patch.object(mod, "_regrade_state", lambda base, walk: "graded"), \
                mock.patch.object(mod, "head_routing_table", live_table):
            try:
                one = mod.coverage_status(f.base, p, strict=frozenset({NESTED}))
                loose = mod.coverage_status(f.base, p)
                many = mod.uncounted_walks(f.base, [p], [p])
            except Exception as exc:             # noqa: BLE001
                return out + [f"S4.uncounted: the pending road raised {exc!r}"]
        if not (str(one).startswith(mod.STRICT_WHY) and str(many.get(p)).startswith(mod.STRICT_WHY) and loose is None):
            out.append(f"S4.uncounted: the pending road: coverage_status {one!r}, without strict {loose!r}, "
                       f"uncounted_walks {many!r}")
    finally:
        f.close()
    out += dirty_vocabulary_cases(mod)
    return out


def dirty_vocabulary_cases(mod) -> list:
    """Review MINOR 2, end to end: HEAD's table lacks operator-lines, the working tree's has it (an uncommitted
    addition). The vocabulary check reads the working tree, so the walk is readable; the strict road counts the reason
    as a hit, because HEAD's table does not know it."""
    out = []
    tmp = Path(tempfile.mkdtemp(prefix="cover-strict-vocab-"))
    f = Folder()
    try:
        table = live_table()
        repo = repo_with(before_reason(table, "operator-lines"), tmp)
        (repo / "routing.json").write_text(json.dumps(table, indent=1))
        w = f.walk("w-ol", ["operator-lines"])
        with mock.patch.object(routing, "TABLE_PATH", str(repo / "routing.json")):
            try:
                got = mod.uncounted_walks(f.base, [w], [w])
                loose = mod.uncounted_walks(f.base, [w])
            except Exception as exc:             # noqa: BLE001
                return [f"S4.uncounted: the dirty vocabulary raised {exc!r}"]
        if not str(got.get(w)).startswith(mod.STRICT_WHY) or loose != {}:
            out.append(f"S4.uncounted: a reason outside HEAD's vocabulary counts on the strict road: {got!r}; "
                       f"loose {loose!r}")
    finally:
        f.close()
        shutil.rmtree(tmp, ignore_errors=True)
    return out


def effective_reasons(base: Path, walk: str):
    """The tests' own reading: the walk's latest register recheck's reasons, else check.json's (None if neither)."""
    reg = json.loads((base / "register.json").read_text())
    entries = [e for e in reg.get("rechecks", []) if e.get("walk") == walk]
    path = base / walk / (entries[-1]["file"] if entries else "check.json")
    try:
        return json.loads(path.read_text()).get("checker_reasons")
    except (OSError, ValueError):
        return None


def records_cases() -> list:
    import walk_plan
    out = []
    base = wr.REHEARSALS
    rep = walk_plan.coverage_report()
    entries = {e["walk"]: e for e in rep["entries"]}
    strict = set(pw.harness_error_reasons(pw.head_routing_table()))
    if walk_plan.WALK_COVER_STRICT.get("arms") != STRICT_ARMS:
        out.append(f"S5.records: the strict arms are {walk_plan.WALK_COVER_STRICT.get('arms')!r}, not OD131's and "
                   f"OD132's {STRICT_ARMS!r}")
    covering = {w for walks in rep["got"]["covered"].values() for w in walks}
    for w in sorted(covering):
        if entries[w]["arm"] in STRICT_ARMS:
            reasons = effective_reasons(base, w)
            if not isinstance(reasons, list) or set(reasons) & strict:
                out.append(f"S5.records: arm {entries[w]['arm']} walk {w} is counted on the reading {reasons!r}")
    loose = pw.uncounted_walks(base, list(entries))
    held = dict(rep["got"]["uncounted"])
    for w, e in entries.items():
        if e["arm"] not in STRICT_ARMS and held.get(w) != loose.get(w):
            out.append(f"S5.records: walk {w} of arm {e['arm']} reads {held.get(w)!r}, not {loose.get(w)!r} as before")
    if not any(e["arm"] == "G" for e in entries.values()):
        out.append("S5.records: the register holds no arm G walk, so arm G's standing is not exercised")
    return out


# OD131 (Javier, 25 Oct 2026, "walk-cover strict": a Claude walk) and OD132 (26 Oct 2026, "walk-cover-o strict": a Codex
# walk); arm G is deferred and stays as coded. The tests' own reading of the two rulings.
STRICT_ARMS = ("A", "O")


# ---- the witnesses: each one anchored edit of pending_walk.py, and the cases it must turn red ----

WITNESSES = {
    "strict check dropped": ("    if strict is not None:\n        hit = strict_hits(check[\"checker_reasons\"], strict)\n",
                             "    if False:\n        hit = strict_hits(check[\"checker_reasons\"], strict)\n"),
    "pending road strict check dropped": ("    if strict is not None:\n        hit = strict_hits(reasons, strict)\n",
                                          "    if False:\n        hit = strict_hits(reasons, strict)\n"),
    # the review of ff58e02f: MINOR 1 (the pending road through coverage_status), MINOR 2 (HEAD's vocabulary), NIT 1
    "coverage_status drops strict on the pending road": (
        "        return checker_standing(base, walk, pending=True, strict=strict) if state",
        "        return checker_standing(base, walk, pending=True) if state"),
    "a reason outside HEAD's vocabulary counts": (
        "    return [r for r in reasons if r in strict or (vocabulary is not None and r not in vocabulary)]\n",
        "    return [r for r in reasons if r in strict]\n"),
    "the set carries no vocabulary": ("    return StrictReasons(out, table[\"operator_reasons\"])\n",
                                      "    return StrictReasons(out)\n"),
    "none_of conditions read too": (
        "    conds = [c for r in rows for c in (*r.get(\"any_of\", []), *r.get(\"all_of\", []))\n",
        "    conds = [c for r in rows for c in (*r.get(\"any_of\", []), *r.get(\"all_of\", []), *r.get(\"none_of\", []))\n"),
    "coverage_status drops strict on the graded road": ("        return checker_standing(base, walk, strict=strict)\n",
                                                        "        return checker_standing(base, walk)\n"),
    "every row read, not only harness-error rows": (
        "    rows = [r for r in table[\"rows\"] if r.get(\"route\") == routing.labels4.HARNESS_ERROR]\n",
        "    rows = list(table[\"rows\"])\n"),
    "any_of only": ("    conds = [c for r in rows for c in (*r.get(\"any_of\", []), *r.get(\"all_of\", []))\n",
                    "    conds = [c for r in rows for c in (*r.get(\"any_of\", []),)\n"),
    "a constant list": ("    return StrictReasons(out, table[\"operator_reasons\"])\n",
                        "    return frozenset({\"harness-condition-violated\", \"nested-agent\", \"transcript-mismatch\"})\n"),
    "the working tree read, not HEAD": ("    raw = _git_show_head(routing.TABLE_PATH)\n",
                                        "    raw = open(routing.TABLE_PATH, \"rb\").read()\n"),
    "HEAD's table unchecked": ("    problems = _table_problems(table)\n", "    problems = []\n"),
    "the environment's GIT_ variables kept": (
        "    env = {k: v for k, v in os.environ.items() if not k.startswith(\"GIT_\")}\n",
        "    env = dict(os.environ)\n"),
    "every walk strict": ("        strict = reasons if w in strict_ids else None\n", "        strict = reasons\n"),
    "an unreadable HEAD counts": ("            out[w] = unread\n            continue\n", "            pass\n"),
    "the HEAD table read per walk": ("            reasons = strict_reasons()\n",
                                     "            reasons = strict_reasons()\n            strict_reasons()\n"),
}

ALL_CASES = (("S1.derived", derived_cases), ("S2.head", head_cases), ("S3.standing", standing_cases),
             ("S4.uncounted", uncounted_cases))


def mutant(old: str, new: str):
    src = Path(pw.__file__).read_text(encoding="utf-8")
    if src.count(old) != 1:
        raise AssertionError(f"S6.witnesses: the mutation site occurs {src.count(old)} times: {old!r}")
    m = types.ModuleType("pending_walk_mutant")
    m.__file__ = pw.__file__
    sys.modules[m.__name__] = m
    try:
        exec(compile(src.replace(old, new), pw.__file__, "exec"), m.__dict__)
    finally:
        del sys.modules[m.__name__]
    return m


class Base(unittest.TestCase):
    def clean(self, clause: str, cases, *args):
        """cases(*args) returns no problem line; any exception fails the clause by an assertion, never an error."""
        try:
            got = cases(*args)
        except Exception as exc:                 # noqa: BLE001
            self.fail(f"{clause}: raised {exc!r}")
        self.assertEqual(got, [], clause)


class S1Derived(Base):
    def test_the_set_is_derived_from_the_table(self):
        self.clean("S1.derived", derived_cases, pw)


class S2Head(Base):
    def test_the_table_is_heads(self):
        self.clean("S2.head", head_cases, pw)


class S3Standing(Base):
    def test_a_strict_walk_counts_only_clean(self):
        self.clean("S3.standing", standing_cases, pw)


class S4Uncounted(Base):
    def test_only_the_strict_walks_are_judged_strictly(self):
        self.clean("S4.uncounted", uncounted_cases, pw)


class S5Records(Base):
    def test_the_real_register(self):
        self.clean("S5.records", records_cases)


class S6Witnesses(unittest.TestCase):
    def test_each_witness_turns_a_case_red(self):
        for name, (old, new) in WITNESSES.items():
            with self.subTest(witness=name):
                if not hasattr(pw, "STRICT_WHY"):
                    self.fail("S6.witnesses: pending_walk has no strict rule yet")
                m = mutant(old, new)
                red = []
                for clause, cases in ALL_CASES:
                    try:
                        red += cases(m)
                    except Exception as exc:     # noqa: BLE001 - a case the mutant makes raise is red, by name
                        red.append(f"{clause}: raised {exc!r}")
                self.assertTrue(red, f"S6.witnesses: {name} survives every case")


if __name__ == "__main__":
    unittest.main()
