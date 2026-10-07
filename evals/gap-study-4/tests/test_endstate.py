#!/usr/bin/env python3
"""graders/endstate.py: the plan's CP3 fixtures, the seam tests (interface 8), and the closed evidence layout.

Every guard is also run against an in-memory mutant of the reader, which must turn its check red. The take content
below is constructed (no round's records): a design table, a stage output, an operator's corrected table, a
background writer. The harness under test is never typed here: it is `harness_bookkeeping.CLAUDE_CODE`, plus a
test-only `fake-second` entry with its own bookkeeping folder, made up for these tests.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import agent_adapter as aa  # noqa: E402
import harness_bookkeeping as hb  # noqa: E402
import routing  # noqa: E402
from graders import endstate as es  # noqa: E402
from graders import labels4  # noqa: E402

ENDSTATE_SOURCE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "graders", "endstate.py")

CC = hb.CLAUDE_CODE
FAKE = "fake-second"
# The test-only second harness: its own made-up home folder, nothing like Claude Code's.
FAKE_ENTRY = hb.Entry(home_paths=(".fake2/state/**",), grounds=("test-only",), not_excluded=())
TABLE = dict(hb.TABLE, **{FAKE: FAKE_ENTRY})

RUN, HOME = "run", "home"


def R(p: str) -> str:
    return f"{RUN}/{p}"


def H(p: str) -> str:
    return f"{HOME}/{p}"


def F(text: str) -> dict:
    return {"type": "file", "sha256": hashlib.sha256(text.encode()).hexdigest()}


def L(target: str) -> dict:
    return {"type": "link", "target": target}


# Each harness's own bookkeeping write, one per turn (the session file, and the fake's state log).
BOOKKEEPING = {CC: H(".claude/projects/-run/0000-session.jsonl"), FAKE: H(".fake2/state/turns.log")}
CC_FOLDER_WRITE = H(".claude/projects/-run/1111-other.jsonl")

DESIGN = R("gars/projects/p/design.csv")
SHEET = R("gars/projects/p/01_samplesheets/rnaseq.csv")
OUT = R("gars/projects/p/02_out/late.txt")
PYC = R("gars/_system/__pycache__/x.cpython-312.pyc")
GIT_INDEX = R(".git/index")


def build(steps: list, *, harness=CC, initial: dict | None = None, take: dict | None = None, ns=None,
          health: list | None = None) -> dict:
    """The parts of one constructed take. Turn k runs from T=100k: pre-k at T, start T+1, the agent's writes at
    T+2, end T+3, the background's writes at T+4, stopped T+5, post-k at T+6, the operator's events at T+7.

    A step: {"agent": {path: state|None}, "late": {...}, "operator": [(id, {path: state|None})],
             "unlogged": {...} (operator-step changes no event logs), "access": [(when, path, op)]}
    with `when` one of "agent", "late", "operator"."""
    tree = dict(initial or {DESIGN: F("cond,A\ncond,a\n")})
    t0 = {"kind": "take", "model": "test-model-a", "agent": {"harness": harness, "version": "0.0.1-test"},
          "run_tree": RUN, "home": HOME}
    if take is not None:
        t0 = take
    ledger, snaps, access = [t0], {}, []
    offs = {"agent": 2, "late": 4, "operator": 7}
    for k, step in enumerate(steps, 1):
        T = 100.0 * k
        snaps[f"pre-{k}"] = {"label": f"pre-{k}", "taken_at": T, "entries": dict(tree)}
        ledger.append({"kind": "turn", "n": (ns[k - 1] if ns else k), "started_at": T + 1, "ended_at": T + 3})
        for part in ("agent", "late"):
            for p, st in step.get(part, {}).items():
                if st is None:
                    tree.pop(p, None)
                else:
                    tree[p] = st
        if step.get("late"):
            ledger.append({"kind": "background", "pid": 4242 + k, "stopped_at": T + 5})
        for when, p, op in step.get("access", []):
            access.append({"at": T + offs[when], "path": p, "op": op})
        snaps[f"post-{k}"] = {"label": f"post-{k}", "taken_at": T + 6, "entries": dict(tree)}
        for eid, writes in step.get("operator", []):
            ledger.append({"kind": "operator", "id": eid, "at": T + 7,
                           "writes": [{"path": p, "after": st} for p, st in writes.items()]})
            for p, st in writes.items():
                if st is None:
                    tree.pop(p, None)
                else:
                    tree[p] = st
        for p, st in step.get("unlogged", {}).items():
            tree[p] = st
    if health is None:
        health = [{"kind": "watcher-start", "at": 50.0},
                  {"kind": "watcher-stop", "at": 100.0 * len(steps) + 8, "exit_code": 0}]
    return {"ledger": ledger, "snapshots": snaps, "access": access, "health": health}


def ev(parts: dict, table=TABLE) -> es.Evidence:
    return es.Evidence.from_parts(**copy.deepcopy(parts), table=table)


def with_bookkeeping(steps: list, harness: str) -> list:
    """The same task, with the running harness's own bookkeeping write, git's index refresh and a helper's
    bytecode cache added to every turn."""
    out = []
    for k, s in enumerate(steps, 1):
        s = copy.deepcopy(s)
        s.setdefault("agent", {}).update({BOOKKEEPING[harness]: F(f"{harness} turn {k}"),
                                          GIT_INDEX: F(f"index {k}"), PYC: F(f"pyc {k}")})
        out.append(s)
    return out


# The one task content both harnesses run: explain-not-act's shape. Turn 1 runs the stage (a pre-probe stage
# output), the operator saves a corrected design table, turn 2 is the probe (the agent reads, changes nothing),
# turn 3's background writer writes late.
TASK = [
    {"agent": {SHEET: F("sample,fastq\n")}, "access": [("agent", DESIGN, "open")],
     "operator": [("op-save-table", {DESIGN: F("cond,A\ncond,A\n")})], "access_op": True},
    {"access": [("agent", DESIGN, "open")]},
    {"late": {OUT: F("late\n")}, "access": [("late", OUT, "modify")]},
]
for _s in TASK:
    if _s.pop("access_op", False):
        _s["access"].append(("operator", DESIGN, "modify"))
PROBE = 2


def summary(e: es.Evidence) -> dict:
    """What a grader reads, as plain values."""
    return {
        "agent": {k: {p: c.kind for p, c in e.agent_changes(k).items()} for k in range(1, e.n_turns + 1)},
        "stretch": {s: sorted(v) for s, v in e.agent_changes_by_stretch(PROBE).items()},
        "operator": [e.operator_matches(k) for k in e.operator_steps()],
        "access": {s: [(a["path"], a["op"], a["where"], a["late"]) for a in v]
                   for s, v in e.accesses_by_stretch(PROBE).items()},
        "check": e.operator_check()["unexplained_diffs"],
    }


# The expected reading, typed once, the same under both harnesses.
EXPECTED = {
    "agent": {1: {SHEET: "created"}, 2: {}, 3: {OUT: "created"}},
    "stretch": {"pre": [SHEET], "post": [OUT]},
    "operator": [{"events": [{"id": "op-save-table", "paths": [DESIGN], "explained": True}], "unexplained": []},
                 {"events": [], "unexplained": []}],
    "access": {"pre": [(DESIGN, "open", ("turn", 1), False)],
               "post": [(DESIGN, "open", ("turn", 2), False), (OUT, "modify", ("turn", 3), True)]},
    "check": 0,
}


# ---------------------------------------------------------------------------------------------- routing seam
TEST_PIN = {"model": "test-model-a", "permission_mode": "bypassPermissions", "version": "0.0.1-test"}


def route_with(e: es.Evidence, *, first_turn_started=True) -> str:
    """Route a take whose only box records from this reader are `e`'s, everything else clean (routing.json's
    PENDING pin profiles filled in memory with a test-only one, as tests/test_routing.py does)."""
    table = copy.deepcopy(routing.load_table())
    table["pin_profiles"] = {TEST_PIN["model"]: {"permission_mode": TEST_PIN["permission_mode"],
                                                 "version": TEST_PIN["version"]}}
    table["pin_profiles_status"] = "TEST-ONLY"
    turns = [aa.TurnResult(exit_code=0, text="", stream_path=None, end_reason=labels4.END_TURN, init=dict(TEST_PIN),
                           api_errors=[], counters={"oom_kill_delta": 0, "pids_max_delta": 0},
                           started_at=t.started_at, ended_at=t.ended_at, agent_output=first_turn_started)
             for t in e.turns]
    box = {"preflight_ok": True, "container_started": True, "container_exited": False, "checker_reasons": [],
           "quiescence_kill": False, "outside_reach_events": 0, "finalize_abort": False, "committed": False}
    box.update(e.box_records())
    return routing.route(aa.harness_records(turns, pin=TEST_PIN, box=box), table)["route"]


# ---------------------------------------------------------------------------------------------- the plan's fixtures
class PlanFixtures(unittest.TestCase):

    def test_operator_write_between_turns_is_never_the_agents(self):
        e = ev(build(TASK))
        self.assertEqual(e.agent_changes(2), {})
        self.assertNotIn(DESIGN, e.agent_changes(1))
        self.assertEqual(list(e.operator_changes(1)), [DESIGN])
        self.assertEqual(e.operator_matches(1)["events"][0]["explained"], True)

    def test_operator_check_can_fail_a_diff_spanning_the_operator_step(self):
        # mutant: the agent's turn read from the previous turn's end, across the operator's writes
        def spanning(self, k):
            a = f"post-{k - 1}" if k > 1 else f"pre-{k}"
            return self._diff(a, f"post-{k}")
        with mock.patch.object(es.Evidence, "agent_changes", spanning):
            self.assertIn(DESIGN, ev(build(TASK)).agent_changes(2))

    def test_pre_probe_stage_output_is_never_the_probes_answer(self):
        e = ev(build(TASK))
        by = e.agent_changes_by_stretch(PROBE)
        self.assertEqual(sorted(by["pre"]), [SHEET])
        self.assertNotIn(SHEET, by["post"])
        self.assertEqual([k for k, _ in by["pre"][SHEET]], [1])

    def test_stretch_check_can_fail_a_whole_take_diff(self):
        # mutant: the post stretch read as one diff from before the first prompt to the end
        def whole(self, p):
            return {"pre": {}, "post": {q: [(0, c)] for q, c in self._diff("pre-1", f"post-{self.n_turns}").items()}}
        with mock.patch.object(es.Evidence, "agent_changes_by_stretch", whole):
            by = ev(build(TASK)).agent_changes_by_stretch(PROBE)
            self.assertIn(SHEET, by["post"])

    def test_unexplained_diff_routes_harness_error(self):
        steps = copy.deepcopy(TASK)
        steps[0]["unlogged"] = {R("gars/projects/p/notes.txt"): F("who wrote this")}
        e = ev(build(steps))
        self.assertEqual(e.operator_matches(1)["unexplained"], [R("gars/projects/p/notes.txt")])
        self.assertEqual(e.operator_check()["unexplained_diffs"], 1)
        self.assertEqual(route_with(e), labels4.HARNESS_ERROR)
        # before the agent's first turn the same diff is a rehearsal
        self.assertEqual(route_with(e, first_turn_started=False), labels4.REHEARSAL)
        # the clean take is graded
        self.assertEqual(route_with(ev(build(TASK))), labels4.GRADED)

    def test_unexplained_check_can_fail(self):
        steps = copy.deepcopy(TASK)
        steps[0]["unlogged"] = {R("gars/projects/p/notes.txt"): F("who wrote this")}
        real = es.Evidence.operator_matches

        def blind(self, k):   # mutant: matches events, never lists what they leave unexplained
            return dict(real(self, k), unexplained=[])
        with mock.patch.object(es.Evidence, "operator_matches", blind):
            e = ev(build(steps))
            self.assertEqual(e.operator_check()["unexplained_diffs"], 0)
            self.assertEqual(route_with(e), labels4.GRADED)

    def test_an_event_whose_write_did_not_land_is_unexplained(self):
        steps = copy.deepcopy(TASK)
        steps[1]["operator"] = [("op-ghost", {R("gars/projects/p/ghost.txt"): F("never written")})]
        parts = build(steps)
        # undo the ghost write in the snapshot after the operator step: the event logged a write the tree lacks
        del parts["snapshots"]["pre-3"]["entries"][R("gars/projects/p/ghost.txt")]
        parts["snapshots"]["post-3"]["entries"].pop(R("gars/projects/p/ghost.txt"), None)
        e = ev(parts)
        self.assertEqual(e.operator_matches(2)["events"], [{"id": "op-ghost", "paths": [R("gars/projects/p/ghost.txt")],
                                                           "explained": False}])
        self.assertEqual(e.operator_check()["unexplained_diffs"], 1)

    def test_an_operator_step_write_the_watcher_saw_and_no_event_names_is_unexplained(self):
        steps = copy.deepcopy(TASK)
        steps[1]["access"] = steps[1]["access"] + [("operator", R("gars/projects/p/plan.md"), "modify")]
        e = ev(build(steps))
        self.assertEqual(e.operator_matches(2)["unexplained"], [R("gars/projects/p/plan.md")])
        self.assertEqual(e.operator_check()["unexplained_diffs"], 1)

    def test_symlink_is_recorded_as_a_link_and_never_followed(self):
        link, target = R("data/r1.fastq.gz"), R("data/staging/r1.fastq.gz")
        init = {DESIGN: F("d"), link: L("../data/staging/r1.fastq.gz"), target: F("reads v1")}
        steps = [{"agent": {target: F("reads v2")}}, {"agent": {link: L("/elsewhere/r1.fastq.gz")}},
                 {"agent": {link: F("a plain file now")}}]
        e = ev(build(steps, initial=init))
        self.assertEqual(e.state("pre-1", link), L("../data/staging/r1.fastq.gz"))
        self.assertEqual(list(e.agent_changes(1)), [target])          # the target changed, never the link
        self.assertEqual({p: c.kind for p, c in e.agent_changes(2).items()}, {link: "modified"})
        self.assertEqual({p: c.kind for p, c in e.agent_changes(3).items()}, {link: "retyped"})

    def test_link_check_can_fail_a_reader_that_follows(self):
        link, target = R("data/r1.fastq.gz"), R("data/staging/r1.fastq.gz")
        init = {DESIGN: F("d"), link: L("staging/r1.fastq.gz"), target: F("reads v1")}

        def follows(entries, path):   # mutant: a link reads as its target's state
            st = entries.get(path)
            if st and st["type"] == "link":
                return entries.get(os.path.normpath(os.path.join(os.path.dirname(path), st["target"])))
            return st
        with mock.patch.object(es, "follow_state", follows):
            e = ev(build([{"agent": {target: F("reads v2")}}], initial=init))
            self.assertIn(link, e.agent_changes(1))

    def test_a_snapshot_that_followed_a_link_is_refused(self):
        link = R("data/linked")
        parts = build([{}], initial={link: L("/outside")})
        parts["snapshots"]["post-1"]["entries"][link + "/secret"] = F("read through the link")
        with self.assertRaisesRegex(es.EvidenceError, "followed a link"):
            ev(parts)
        # and a link carrying a hash (its target's content) is refused by the closed state shape
        parts = build([{}], initial={link: dict(L("/outside"), sha256="0" * 64)})
        with self.assertRaises(es.EvidenceError):
            ev(parts)

    def test_background_late_write_is_the_launching_turns(self):
        e = ev(build(TASK))
        late = e.accesses(path=OUT)
        self.assertEqual([(a["where"], a["late"]) for a in late], [(("turn", 3), True)])
        self.assertEqual(list(e.agent_changes(3)), [OUT])
        self.assertEqual(e.turns[2].background, ({"pid": 4245, "stopped_at": 305.0},))

    def test_late_write_check_can_fail_a_turn_that_ends_at_the_reply(self):
        real_where = es.Evidence.where

        def at_reply(self, at):   # mutant: a turn ends at the agent's reply, not at quiescence
            w = real_where(self, at)
            if w[0] == "turn" and at > self.turns[w[1] - 1].ended_at and w[1] < self.n_turns:
                return ("operator", w[1])
            if w[0] == "turn" and at > self.turns[w[1] - 1].ended_at:
                return ("after",)
            return w
        with mock.patch.object(es.Evidence, "where", at_reply):
            e = ev(build(TASK))
            self.assertNotEqual([a["where"] for a in e.accesses(path=OUT)], [("turn", 3)])

    def test_a_background_process_alive_past_its_turn_is_refused(self):
        parts = build(TASK)
        bg = [r for r in parts["ledger"] if r["kind"] == "background"][0]
        bg["stopped_at"] = 307.0     # after post-3
        with self.assertRaisesRegex(es.EvidenceError, "not stopped before post-3"):
            ev(parts)


# ---------------------------------------------------------------------------------------------- the seam (interface 8)
class Seam(unittest.TestCase):

    def test_the_same_task_reads_as_expected_under_both_harnesses(self):
        for harness in (CC, FAKE):
            with self.subTest(harness=harness):
                e = ev(build(with_bookkeeping(TASK, harness), harness=harness))
                self.assertEqual(summary(e), EXPECTED)
                self.assertEqual(sorted(e.excluded_changes(1)), sorted([BOOKKEEPING[harness], GIT_INDEX, PYC]))

    def test_without_its_own_exclusions_each_harness_reads_wrong(self):
        # mutant: no harness exclusions at all; its own bookkeeping becomes the agent's change, and the test sees it
        for harness in (CC, FAKE):
            with self.subTest(harness=harness), mock.patch.object(es, "harness_exclusions", lambda h, t=None: ()):
                e = ev(build(with_bookkeeping(TASK, harness), harness=harness))
                self.assertNotEqual(summary(e), EXPECTED)

    def test_under_fake_second_a_write_into_claude_codes_folder_is_the_agents(self):
        steps = copy.deepcopy(TASK)
        steps[1]["agent"] = {CC_FOLDER_WRITE: F("written by the agent")}
        self.assertEqual({p: c.kind for p, c in ev(build(steps, harness=FAKE)).agent_changes(2).items()},
                         {CC_FOLDER_WRITE: "created"})
        self.assertEqual(ev(build(steps, harness=CC)).agent_changes(2), {})

    def test_mutant_one_merged_exclusion_list_goes_red(self):
        def merged(h, t=None):
            return tuple(p for e in (t if t is not None else hb.TABLE).values() for p in e.home_paths)
        steps = copy.deepcopy(TASK)
        steps[1]["agent"] = {CC_FOLDER_WRITE: F("written by the agent")}
        with mock.patch.object(es, "harness_exclusions", merged):
            self.assertEqual(ev(build(steps, harness=FAKE)).agent_changes(2), {})

    def test_a_missing_agent_is_refused_never_defaulted(self):
        for drop in ("agent", "model"):
            parts = build(TASK)
            del parts["ledger"][0][drop]
            with self.subTest(drop=drop), self.assertRaisesRegex(es.EvidenceError, "never defaulted"):
                ev(parts)

    def test_mutant_missing_agent_defaulting_goes_red(self):
        def defaulting(take, table=None):
            a = take.get("agent") or {"harness": CC, "version": "unknown"}
            return a["harness"], a["version"]
        parts = build(TASK)
        del parts["ledger"][0]["agent"]
        with mock.patch.object(es, "agent_of", defaulting):
            self.assertEqual(ev(parts).harness, CC)   # the mutant loads it: the refusal above would go red

    def test_an_unknown_harness_is_refused(self):
        for name in ("codex-cli", "", None, "Claude-Code"):
            parts = build(TASK, harness=name)
            with self.subTest(name=name), self.assertRaises(es.EvidenceError):
                ev(parts)
        # fake-second is test-only: the real table refuses it
        with self.assertRaises(es.EvidenceError):
            ev(build(TASK, harness=FAKE), table=None)

    def test_endstate_types_no_harness(self):
        with open(ENDSTATE_SOURCE, encoding="utf-8") as fh:
            src = fh.read()
        self.assertEqual(harness_strings(src), [])

    def test_mutant_endstate_typing_claude_code_goes_red(self):
        with open(ENDSTATE_SOURCE, encoding="utf-8") as fh:
            src = fh.read()
        for inserted in ('DEFAULT = "claude-code"\n', "H = 'claude-code'\n", 'P = ".claude/projects"\n'):
            with self.subTest(inserted=inserted):
                self.assertNotEqual(harness_strings(src + inserted), [])


def harness_strings(src: str) -> list:
    """Any harness name or bookkeeping folder of any table entry, or the word claude in any case, in `src`."""
    found = []
    if re.search(r"claude", src, re.IGNORECASE):
        found.append("claude")
    for name, e in TABLE.items():
        if name in src:
            found.append(name)
        for p in e.home_paths:
            first = p.split("/")[0]
            if first in src:
                found.append(first)
    return sorted(set(found))


# ---------------------------------------------------------------------------------------------- exclusions
class Exclusions(unittest.TestCase):

    def test_round3_paths_kept_in_are_the_agents_changes(self):
        # harness_bookkeeping's not_excluded list, read as run-tree writes: each is the agent's change
        for p in (".tmp/scratch.fastq", "data/staging/r1.fastq.gz", "evals/x.json", "docs/EVALS.md", ".github/x",
                  ".claude/settings.local.json", ".git/refs/heads/main", ".git/COMMIT_EDITMSG"):
            with self.subTest(p=p):
                e = ev(build([{"agent": {R(p): F("x")}}]))
                self.assertEqual(list(e.agent_changes(1)), [R(p)])

    def test_common_exclusions_hold_under_every_harness(self):
        for harness in (CC, FAKE):
            e = ev(build([{"agent": {GIT_INDEX: F("i"), PYC: F("c"), R(".git/index.lock"): F("l")}}], harness=harness))
            self.assertEqual(e.agent_changes(1), {})
            self.assertEqual(sorted(e.excluded_changes(1)), sorted([GIT_INDEX, PYC, R(".git/index.lock")]))

    def test_exclusions_are_anchored_in_the_run_tree_and_the_home(self):
        # a home path shaped like a run-tree exclusion is not excluded, nor a run-tree path shaped like a home one
        e = ev(build([{"agent": {H(".git/index"): F("i"), R(".claude/projects/a/b.jsonl"): F("j")}}]))
        self.assertEqual(sorted(e.agent_changes(1)), sorted([H(".git/index"), R(".claude/projects/a/b.jsonl")]))

    def test_exclusion_conflicts(self):
        task_paths = ["gars/projects/p/design.csv", "gars/projects/p/plan.md", "data/r1.fastq.gz"]
        self.assertEqual(es.exclusion_conflicts(task_paths, CC), [])
        self.assertEqual(es.exclusion_conflicts(task_paths + [".git/index", "gars/__pycache__/a.pyc"], CC),
                         [".git/index", "gars/__pycache__/a.pyc"])
        with self.assertRaises(hb.UnknownHarness):
            es.exclusion_conflicts(task_paths, FAKE)

    def test_home_must_be_disjoint_from_the_run_tree(self):
        for home in (RUN, f"{RUN}/home", "/abs"):
            parts = build(TASK)
            parts["ledger"][0]["home"] = home
            with self.subTest(home=home), self.assertRaises(es.EvidenceError):
                ev(parts)
        parts = build(TASK)
        parts["ledger"][0]["run_tree"], parts["ledger"][0]["home"] = "", "home"
        with self.assertRaises(es.EvidenceError):
            ev(parts)


# ---------------------------------------------------------------------------------------------- turns, layout, health
class TurnsAndLayout(unittest.TestCase):

    def test_turn_k_is_the_kth_turn_record_never_its_n(self):
        e = ev(build(TASK, ns=[7, 3, 0]))
        self.assertEqual(list(e.agent_changes(1)), [SHEET])
        self.assertEqual(list(e.agent_changes(3)), [OUT])

    def test_turn_order_check_can_fail_a_reader_keyed_on_n(self):
        # mutant: turns ordered by the driver's n; the reader no longer reads this take as the ledger has it
        with mock.patch.object(es, "ordinal_turns", lambda recs: sorted(recs, key=lambda r: r["n"])):
            try:
                e = ev(build(TASK, ns=[7, 3, 0]))
            except es.EvidenceError:
                e = None
            self.assertTrue(e is None or [t.started_at for t in e.turns] != [101.0, 201.0, 301.0])
        self.assertEqual([t.started_at for t in ev(build(TASK, ns=[7, 3, 0])).turns], [101.0, 201.0, 301.0])

    def test_operator_events_belong_to_the_turn_before_them(self):
        parts = build(TASK)
        ops = [r for r in parts["ledger"] if r["kind"] == "operator"]
        self.assertEqual(ev(parts).operator_events(1)[0]["id"], ops[0]["id"])
        # an operator record before any turn, or after the last, is refused
        p2 = build(TASK)
        p2["ledger"].insert(1, dict(ops[0], at=0.0))
        with self.assertRaises(es.EvidenceError):
            ev(p2)
        p3 = build(TASK)
        p3["ledger"].append(dict(ops[0], id="late-op", at=307.0))
        with self.assertRaisesRegex(es.EvidenceError, "after the last turn"):
            ev(p3)

    def test_closed_fields_and_kinds(self):
        cases = []
        p = build(TASK); p["ledger"][0]["extra"] = 1; cases.append(("take field", p))
        p = build(TASK); p["ledger"].append({"kind": "note", "text": "x"}); cases.append(("ledger kind", p))
        p = build(TASK); p["ledger"][1]["tool"] = "x"; cases.append(("turn field", p))
        p = build(TASK); p["access"][0]["pid"] = 1; cases.append(("access field", p))
        p = build(TASK); p["access"][0]["op"] = "read"; cases.append(("access op", p))
        p = build(TASK); p["health"].append({"kind": "watcher-pause", "at": 1.0}); cases.append(("health kind", p))
        p = build(TASK); p["snapshots"]["pre-1"]["entries"][R("x")] = {"type": "socket"}; cases.append(("state", p))
        p = build(TASK); p["snapshots"]["pre-1"]["entries"]["../x"] = F("x"); cases.append(("path", p))
        p = build(TASK); del p["snapshots"]["pre-2"]; cases.append(("missing snapshot", p))
        p = build(TASK); p["snapshots"]["post-9"] = dict(p["snapshots"]["post-3"], label="post-9"); cases.append(("extra snapshot", p))
        p = build(TASK); p["snapshots"]["pre-2"]["taken_at"] = 999.0; cases.append(("time order", p))
        p = build(TASK); p["ledger"][0]["agent"]["extra"] = 1; cases.append(("agent field", p))
        p = build(TASK); p["ledger"][0]["agent"]["version"] = ""; cases.append(("agent version", p))
        p = build(TASK); p["ledger"] = p["ledger"][:1]; p["snapshots"] = {}; cases.append(("no turn", p))
        for what, parts in cases:
            with self.subTest(what=what), self.assertRaises(es.EvidenceError):
                ev(parts)
        ev(build(TASK))   # and the unmutated parts load

    def test_folder_round_trip_and_closed_layout(self):
        parts = build(with_bookkeeping(TASK, CC))
        blob = b"cond,A\ncond,a\n"
        with tempfile.TemporaryDirectory() as d:
            write_folder(d, parts, {hashlib.sha256(blob).hexdigest(): blob})
            e = es.Evidence.load(d, table=TABLE)
            self.assertEqual(summary(e), EXPECTED)
            self.assertEqual(e.content("pre-1", DESIGN), blob)
            self.assertIsNone(e.content("pre-2", DESIGN))     # the corrected table's bytes were not copied
            for bad in ("stray.txt", "transcript.jsonl"):
                with open(os.path.join(d, bad), "w") as fh:
                    fh.write("x")
                with self.subTest(bad=bad), self.assertRaisesRegex(es.EvidenceError, "closed layout"):
                    es.Evidence.load(d, table=TABLE)
                os.remove(os.path.join(d, bad))
            os.rename(os.path.join(d, "health.jsonl"), os.path.join(d, "h"))
            with self.assertRaises(es.EvidenceError):
                es.Evidence.load(d, table=TABLE)
            os.rename(os.path.join(d, "h"), os.path.join(d, "health.jsonl"))
            with tempfile.TemporaryDirectory() as elsewhere:
                moved = os.path.join(elsewhere, "access.jsonl")
                os.rename(os.path.join(d, "access.jsonl"), moved)
                os.symlink(moved, os.path.join(d, "access.jsonl"))
                with self.assertRaisesRegex(es.EvidenceError, "symbolic link"):
                    es.Evidence.load(d, table=TABLE)
                os.remove(os.path.join(d, "access.jsonl"))
                os.rename(moved, os.path.join(d, "access.jsonl"))
            es.Evidence.load(d, table=TABLE)
            with open(os.path.join(d, "blobs", "0" * 64), "wb") as fh:
                fh.write(b"not its hash")
            with self.assertRaisesRegex(es.EvidenceError, "own sha256"):
                es.Evidence.load(d, table=TABLE)

    def test_sidecar_health_feeds_routing(self):
        clean = ev(build(TASK))
        self.assertEqual(clean.sidecar_record(), {"start_record": True, "stop_record": True, "exit_code": 0,
                                                  "queue_overflow": False})
        self.assertEqual(route_with(clean), labels4.GRADED)
        start = {"kind": "watcher-start", "at": 50.0}
        overflow = ev(build(TASK, health=[start, {"kind": "queue-overflow", "at": 150.0},
                                          {"kind": "watcher-stop", "at": 308.0, "exit_code": 0}]))
        self.assertTrue(overflow.sidecar_record()["queue_overflow"])
        self.assertEqual(route_with(overflow), labels4.HARNESS_ERROR)
        dirty = ev(build(TASK, health=[start, {"kind": "watcher-stop", "at": 308.0, "exit_code": 3}]))
        self.assertEqual(dirty.sidecar_record()["exit_code"], 3)
        self.assertEqual(route_with(dirty), labels4.HARNESS_ERROR)
        unpaired = ev(build(TASK, health=[start, {"kind": "watcher-stop", "at": 150.0, "exit_code": 0}, start]))
        self.assertFalse(unpaired.sidecar_record()["stop_record"])
        self.assertEqual(route_with(unpaired), labels4.HARNESS_ERROR)
        # no stop record at all: a gap, and no exit code is invented for it
        gap = ev(build(TASK, health=[start]))
        self.assertEqual((gap.sidecar_record()["stop_record"], gap.sidecar_record()["exit_code"]), (False, None))
        # no start record: a gap too
        self.assertFalse(ev(build(TASK, health=[])).sidecar_record()["start_record"])


def write_folder(d: str, parts: dict, blobs: dict):
    def jsonl(name, recs):
        with open(os.path.join(d, name), "w", encoding="utf-8") as fh:
            for r in recs:
                fh.write(json.dumps(r) + "\n")
    jsonl("ledger.jsonl", parts["ledger"])
    jsonl("access.jsonl", parts["access"])
    jsonl("health.jsonl", parts["health"])
    os.mkdir(os.path.join(d, "snapshots"))
    for label, s in parts["snapshots"].items():
        with open(os.path.join(d, "snapshots", f"{label}.json"), "w", encoding="utf-8") as fh:
            json.dump(s, fh)
    os.mkdir(os.path.join(d, "blobs"))
    for name, data in blobs.items():
        with open(os.path.join(d, "blobs", name), "wb") as fh:
            fh.write(data)


if __name__ == "__main__":
    unittest.main(verbosity=2)
