#!/usr/bin/env python3
"""Codex slice 3: the arm O registration road, on the corrected pattern of the Gemini road (test_pending_walk.py).

A Codex walk driven by the real WalkDriver and the real CodexAdapter (built by harness_adapter_for, its rollout read
live from the take's config folder, CODEX_HOME) on a fake box, its turns run through the login-free stub exec of
glitch-06's Codex ruling (a), stopped by its pending native cross-check, committed ungraded by the real walk runner and
WalkRepo, then registered (native-readers/codex-acceptance.json) and regraded from its committed bytes.

Fakes only, in a throwaway scratch repository under test_box_integration's SCRATCH: no model, container, network,
credential or study-tree write. The fake box answers `codex --version` and `codex exec --json` with exec streams and
grows the rollout at <config>/sessions/<Y>/<MM>/<DD>/rollout-<YYYY-MM-DDTHH-MM-SS>-<thread>.jsonl (audit Addendum
B). The fixture is UNMARKED on purpose (a gate nothing can pass proves nothing) and lives only in the scratch folder.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
for p in (HERE, HERE / "tests"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import test_box_integration as tbi  # noqa: E402
import test_pending_walk as tpw  # noqa: E402
from box import run_take as rt  # noqa: E402

TID = "00000000-0000-7000-8000-0000000000c1"
MODEL = "gpt-6-luna"
CLI = "0.162.1"
UNMARKED = tpw.UNMARKED
USAGE = {"input_tokens": 3, "cached_input_tokens": 0, "output_tokens": 2, "reasoning_output_tokens": 0}


def setUpModule():
    tbi.setUpModule()


def tearDownModule():
    tbi.tearDownModule()


def jl(records) -> str:
    return "".join(json.dumps(r) + "\n" for r in records)


def rollout(turns: int, label: str = UNMARKED) -> bytes:
    """A paginated 0.162.1 rollout of `turns` turns (codex_native's subset and codex_adapter's reading)."""
    recs = []

    def add(type_, payload):
        recs.append({"timestamp": f"2026-10-14T05:00:{len(recs):02d}.000Z", "ordinal": len(recs), "type": type_,
                     "payload": payload})
    add("session_meta", {"session_id": TID, "id": TID, "timestamp": "2026-10-14T05:00:00.000Z", "cwd": "/work/tree",
                         "originator": "codex_exec", "cli_version": CLI, "source": "exec", "model_provider": "openai",
                         "base_instructions": {"text": label}, "history_mode": "paginated"})
    for k in range(1, turns + 1):
        tid = f"t{k}"
        add("event_msg", {"type": "task_started", "turn_id": tid, "model_context_window": None,
                          "collaboration_mode_kind": "default"})
        add("turn_context", {"turn_id": tid, "cwd": "/work/tree", "approval_policy": "never",
                             "sandbox_policy": {"type": "danger-full-access"}, "model": MODEL})
        for item in ({"type": "UserMessage", "id": f"u{k}", "content": [{"type": "text", "text": f"sent {k}",
                                                                          "text_elements": []}]},
                     {"type": "CommandExecution", "id": f"c{k}", "command": ["ls"], "cwd": "/work/tree",
                      "parsed_cmd": [], "source": "agent", "status": "completed", "aggregated_output": f"out {k}",
                      "exit_code": 0},
                     {"type": "AgentMessage", "id": f"m{k}", "content": [{"type": "Text", "text": "Done."}],
                      "phase": "final_answer"}):
            add("event_msg", {"type": "item_completed", "thread_id": TID, "turn_id": tid, "item": item,
                              "completed_at_ms": 0})
        add("event_msg", {"type": "task_complete", "turn_id": tid, "last_agent_message": "Done."})
    return jl(recs).encode()


def exec_stream(k: int) -> str:
    return jl([{"type": "thread.started", "thread_id": TID}, {"type": "turn.started"},
               {"type": "item.completed", "item": {"id": "item_0", "type": "command_execution", "command": "ls",
                                                   "aggregated_output": f"out {k}", "exit_code": 0,
                                                   "status": "completed"}},
               {"type": "item.completed", "item": {"id": "item_1", "type": "agent_message", "text": "Done."}},
               {"type": "turn.completed", "usage": USAGE}])


def open_rollout(turns: int) -> bytes:
    """The rollout with its last turn left open (no task_complete): a killed or cut turn."""
    lines = rollout(turns).decode().splitlines(keepends=True)
    return "".join(lines[:-1]).encode()


def open_stream(k: int) -> str:
    """The exec stream with no terminal event (an interrupted call exits 1)."""
    return "".join(exec_stream(k).splitlines(keepends=True)[:-1])


class CodexBox(tbi.FakeBox):
    """FakeBox that also answers `codex --version` and a `codex exec --json` turn, growing the rollout under the
    take's config folder (CODEX_HOME), one turn per exec."""

    def __init__(self, *a, label=UNMARKED, **kw):
        super().__init__(*a, **kw)
        self.turn_n, self.label = 0, label

    def run(self, argv, env=None, timeout=None):
        a = list(argv)
        if a[:2] == ["docker", "exec"] and "codex" in a:
            self.calls.append(a)
            if a[-1] == "--version":
                return rt.Completed(0, f"codex-cli {CLI}\n", "")
            take = [x for x in a if self.containers.get(x, {}).get("kind") == "take"][0]
            cfg = [m for m in self.specs[take] if m.startswith("type=bind,source=")
                   and m.endswith("target=" + rt.CONFIG_MOUNT)][0]
            cfg = cfg[len("type=bind,source="):-len(",target=" + rt.CONFIG_MOUNT)]
            self.turn_n += 1
            folder = Path(cfg) / "sessions" / "2026" / "10" / "14"
            folder.mkdir(parents=True, exist_ok=True)
            (folder / f"rollout-2026-10-14T05-00-00-{TID}.jsonl").write_bytes(rollout(self.turn_n, self.label))
            return rt.Completed(0, exec_stream(self.turn_n), "")
        return super().run(argv, env=env, timeout=timeout)


def codex_road(test, *, label=UNMARKED, reason=UNMARKED):
    import test_codex_adapter as tca
    road = tpw.Road(test, harness="codex", box=CodexBox(label=label), run_turn=tca.stub_run_turn, reason=reason,
                    row={"arm": "O", "model": MODEL, "agent": {"harness": "codex", "version": CLI}})
    got = road.walk()
    test.assertEqual(got[0]["state"], "pending-native-reader", got)
    return road


class CodexPendingWalk(unittest.TestCase):
    def test_a_pending_codex_walk_is_committed_with_its_rollouts(self):
        import pending_walk
        road = codex_road(self)
        ledger = json.loads((road.folder / "driver-ledger.json").read_text())
        self.assertEqual(ledger["agent"], {"harness": "codex", "version": CLI})
        self.assertEqual(ledger["cross_check_status"]["status"], "pending")
        self.assertEqual(ledger["native_history"]["status"], "pending")
        self.assertEqual([s["file"] for s in ledger["native_snapshots"]], ["native-turn-1.jsonl", "native-turn-2.jsonl"])
        self.assertEqual(ledger["served_model"], [{"value": None, "source": "unobserved"}] * 2)   # D-INT-2
        self.assertEqual(json.loads((road.folder / "grade.json").read_text()), pending_walk.status(ledger))
        for k in (1, 2):
            self.assertTrue((road.folder / f"turn-{k}.jsonl.launch.json").is_file())
        self.assertEqual(tpw.git(road.root, "log", "-1", "--format=%s"), road.drive.WALK_SUBJECT)


class CodexRegistration(unittest.TestCase):
    def test_it_registers_and_each_single_mutation_unregisters(self):
        road = codex_road(self)
        road.accept()
        nrr = road.nrr
        self.assertEqual(nrr.production_readers(road.study), {"codex": nrr.codex_reader})
        prov = nrr.acceptance_provenance(road.study, "codex")
        self.assertEqual(prov["acceptance_commit"], tpw.git(road.root, "rev-parse", "HEAD"))
        for why, mutate in (
                ("acceptor", lambda r: r.accept(accepted_by="glitch-06")),
                ("reviewer and the acceptor", lambda r: r.accept(reviewer="javier")),
                ("synthetic marker", lambda r: r.accept(review="a synthetic review")),
                ("driver ledger names", lambda r: r.accept(edit=lambda rec: rec.__setitem__("native", {
                    "file": "session/native-turn-1.jsonl", "sha256": json.loads(
                        (r.folder / "driver-ledger.json").read_text())["native_snapshots"][0]["sha256"]}))),
                ("join does not re-derive", lambda r: r.accept(edit=lambda rec: rec["join"].__setitem__(
                    "interactions", 3))),
                ("the record is for codex", lambda r: r.accept(edit=lambda rec: rec.__setitem__("cli_version",
                                                                                                "0.64.0"))),
                ("arm-O walk", lambda r: r.accept(edit=lambda rec: rec.__setitem__("walk", "another-walk")))):
            with self.subTest(why=why):
                other = codex_road(self)
                mutate(other)
                self.assertIn(why, other.refused())

    def test_a_marked_rollout_refuses_last(self):
        road = codex_road(self, label="a synthetic session")
        road.accept()
        self.assertIn("synthetic marker", road.refused())

    def test_the_coverage_floor_and_the_shared_join(self):
        import drive
        nrr = __import__("native_reader_registration")
        good = nrr.codex_join_session(rollout(2), [exec_stream(1), exec_stream(2)], [0, 0])
        self.assertEqual((good["status"], good["shapes"]["interactions"], good["shapes"]["command_round_trips"]),
                         ("PASS", 2, 2))
        for why, args in (("2 native turns for 1 streams", (rollout(2), [exec_stream(1)], [0])),
                          ("interaction 2", (rollout(2), [exec_stream(1), exec_stream(1)], [0, 0])),
                          ("not one exit code per stream", (rollout(2), [exec_stream(1), exec_stream(2)], [0])),
                          ("interaction 2 is not complete", (open_rollout(2), [exec_stream(1), open_stream(2)], [0, 1]))):
            with self.subTest(why=why):
                got = nrr.codex_join_session(*args)
                self.assertEqual(got["status"], "DISAGREE")
                self.assertIn(why, got["why"])
        self.assertEqual(nrr.floor_problem({"interactions": 1, "command_round_trips": 1}, nrr.CODEX_FLOOR),
                         "acceptance needs at least 2 interactions; the walk exercised 1")
        self.assertEqual(drive.codex_cross_check("/nonexistent", [], [0], readers={})["status"], "pending")


class CodexCrossCheckInTheDriver(unittest.TestCase):
    """With a Codex reader registered, the driver joins each turn's exec stream to the retained rollout through the
    one shared join: the history joins and the cross-check agrees, so the checker reads the take (never pending)."""

    def test_a_registered_reader_agrees_in_the_driver(self):
        import native_reader_registration as nrr
        import test_codex_adapter as tca
        road = tpw.Road(self, harness="codex", box=CodexBox(), run_turn=tca.stub_run_turn,
                        row={"arm": "O", "model": MODEL, "agent": {"harness": "codex", "version": CLI}})
        checked = []
        road.driver.checker = lambda row, take, turns: checked.append(len(turns)) or tbi.checker_record()
        row = dict(road.row)
        with mock.patch.object(nrr, "production_readers", lambda study=None: {"codex": nrr.codex_reader}), \
                tbi.spying(road.rig.spy):
            cid = road.driver.launch(row)
            try:
                road.driver.drive(row, cid)
            finally:
                road.driver.remove(cid)
        ledger = json.loads((road.folder / "driver-ledger.json").read_text())
        self.assertEqual(ledger["native_history"]["status"], "joined")
        self.assertEqual(ledger["cross_check_status"], {"status": "agreed", "why": None})
        self.assertEqual(ledger["cross_check"], [])
        self.assertEqual(checked, [2], "the checker read the take")


class CodexRegrade(unittest.TestCase):
    def test_a_registered_codex_reader_regrades_the_committed_walk(self):
        import run
        import walk_regrade
        road = codex_road(self)
        road.accept()
        with mock.patch.object(run, "grade_walk_folder", tpw.stand_in_grade):
            doc = walk_regrade.regrade_doc(tpw.WALK, road.study)
        self.assertEqual(doc["cross_check"], {"status": "agreed", "why": None})
        self.assertTrue(doc["graded"])


if __name__ == "__main__":
    unittest.main()
