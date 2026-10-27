#!/usr/bin/env python3
"""Lane pf1-codex-turnitem (Gap Study round 4; glitch-45's brief of Tue 27 Oct 2026, under Javier's standing
delegation): a Codex CommandExecution that completes after its own turn's task_complete.

Arm O walk w-o69 (gpt-6-luna) was held: "the rollout reader refuses it: line 144: an item belongs to turn '01...".
Its session/native-turn-4.jsonl ordinal 142 is turn 01a17bf1-...'s task_complete and ordinal 143 an item_completed of
that same turn, a background `while kill -0 571 ...; cat /tmp/...` wait the agent started, failed with exit -1 when
exec's shutdown terminated it. The pinned writer (openai/codex 092d3acd) does this by design: codex_native's module
docstring cites the lines. What is tested:

  R1-red        the w-o69 shape is read: the late command lands in the turn's after_complete, never in output, and
                the projection is the in-turn facts alone (red at 5f5aa9fb with the recorded reason).
  R2-reach      check_take's reach reads the late command's line like any CommandExecution line, so the take's
                event counts include it; an unread reach is never counted as zero.
  R3-join       the join pairs each late command with a command the turn's exec stream started and never completed;
                a late command with no such start refuses.
  R4-content    check_take's command comparison: in-turn commands in order as before, each late one equal (split as a
                shell line) to an unfinished start of its own turn's stream; any other is transcript-mismatch.
  W-*           every other out-of-order shape still refuses, each by name, and each guard is shown to bite: with
                `--mutants`, every mutant below is compiled into codex_native or check_take in memory and its bound
                witness must then fail.

Fixtures: the w-o69 late item line is byte for byte the recorded ordinal 143 (no model reply, prompt or tool output
is in it: its aggregated_output is empty); the task_complete is ordinal 142's structure, its ids, ordinal and
timestamps real and its last_agent_message replaced by "synthetic text 1"; the exec stream's unfinished start is
turn-4.jsonl line 9 byte for byte. The rest is test_codex_native's synthetic rollout with the walk's thread and turn
ids. Reads no committed walk; no process, network, model or credential.
"""
from __future__ import annotations

import copy
import json
import sys
import types
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
for p in (HERE, HERE / "tests"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import test_codex_native as tcn  # noqa: E402

THREAD = "01a17bf0-0ad4-7f71-b79b-9307923fe25f"
TURN = "01a17bf1-1bcf-7373-80c3-4de4933d01ce"
LATE_LINE = ('{"timestamp":"2026-10-27T06:00:07.282Z","ordinal":143,"type":"event_msg","payload":{"type":'
             '"item_completed","thread_id":"01a17bf0-0ad4-7f71-b79b-9307923fe25f","turn_id":'
             '"01a17bf1-1bcf-7373-80c3-4de4933d01ce","item":{"type":"CommandExecution","id":'
             '"exec-1800f9a7-0811-45f7-98b9-4367e4e6bd00","process_id":"76075","command":["/bin/bash","-lc",'
             '"while kill -0 571 2>/dev/null; do sleep 2; done; cat /tmp/run-e3f03fe0-stage00-finalize.json"],'
             '"cwd":"file:///tmp/run-e3f03fe0/gars","parsed_cmd":[{"type":"unknown","cmd":"while kill -0 571 '
             '2>/dev/null; do sleep 2; done; cat /tmp/run-e3f03fe0-stage00-finalize.json"}],"source":'
             '"unified_exec_startup","status":"failed","aggregated_output":"","exit_code":-1,"duration":{"secs":39,'
             '"nanos":636639440}},"started_at_ms":1793080767645,"completed_at_ms":1793080807282}}')
TASK_COMPLETE = {"timestamp": "2026-10-27T06:00:07.277Z", "ordinal": 142, "type": "event_msg",
                 "payload": {"type": "task_complete", "root_turn_id": TURN, "turn_id": TURN,
                             "last_agent_message": "synthetic text 1", "started_at": 1793080761,
                             "completed_at": 1793080807, "duration_ms": 45978, "time_to_first_token_ms": 1644}}
STREAM_UNFINISHED = ('{"type":"item.started","item":{"id":"item_4","type":"command_execution","command":"/bin/bash '
                     '-lc \'while kill -0 571 2>/dev/null; do sleep 2; done; cat /tmp/run-e3f03fe0-stage00-finalize.json'
                     '\'","aggregated_output":"","exit_code":null,"status":"in_progress"}}')
REFUSED_AT_HEAD = f"an item belongs to turn '{TURN}', not the open turn"

MODS: dict = {}


def cn():
    return MODS.get("cn") or tcn.cn()


def ct():
    if "ct" not in MODS:
        import check_take
        MODS["ct"] = check_take
    return MODS["ct"]


def records() -> list:
    """test_codex_native's one-turn rollout on w-o69's thread and turn ids, its task_complete w-o69's ordinal 142 and
    the recorded late line after it, ordinals 136 to 143 (the late line keeps its own)."""
    recs = tcn.rollout(turns=1)
    for rec in recs:
        pay = rec["payload"]
        for key, old, new in (("id", tcn.TID, THREAD), ("session_id", tcn.TID, THREAD),
                              ("thread_id", tcn.TID, THREAD), ("turn_id", "t1", TURN)):
            if pay.get(key) == old:
                pay[key] = new
    recs[-1] = copy.deepcopy(TASK_COMPLETE)
    recs.append(json.loads(LATE_LINE))
    for n, rec in enumerate(recs):
        rec["ordinal"] = 136 + n
    return recs


def raw(recs) -> bytes:
    """Every line as test_codex_native writes it, except a record equal to the recorded late line, kept verbatim."""
    late = json.loads(LATE_LINE)
    return "".join((LATE_LINE if r == late else json.dumps(r)) + "\n" for r in recs).encode()


def late(recs) -> dict:
    return recs[-1]["payload"]


def stream(*, unfinished=True) -> str:
    """test_codex_native's exec stream on w-o69's thread, with w-o69's unfinished start before the agent message."""
    lines = tcn.exec_stream().replace(tcn.TID, THREAD).splitlines()
    if unfinished:
        lines.insert(3, STREAM_UNFINISHED)
    return "".join(x + "\n" for x in lines)


class R1Red(unittest.TestCase):
    def test_r1_the_w_o69_shape_is_read(self):
        m = cn()
        recs = records()
        self.assertIn(LATE_LINE.encode(), raw(recs), "the recorded line is in the fixture byte for byte")
        got = m.read_rollout(raw(recs))
        turn = got["turns"][0]
        self.assertEqual(turn["terminal"], "complete")
        self.assertEqual(turn["after_complete"], [{"kind": "command", "status": "failed", "exit_code": -1,
                                                   "output": "", "marker_text": False}])
        plain = records()[:-1]
        self.assertEqual(m.project(raw(recs)), m.project(raw(plain)), "the late command adds no in-turn fact")
        self.assertEqual(m.read_rollout(raw(plain))["turns"][0]["after_complete"], [])

    def test_r1_two_late_commands_are_both_read(self):
        m = cn()
        recs = records()
        second = copy.deepcopy(recs[-1])
        second["ordinal"] += 1
        second["payload"]["item"]["id"] = "exec-second"
        recs.append(second)
        self.assertEqual(len(m.read_rollout(raw(recs))["turns"][0]["after_complete"]), 2)


class R2Reach(unittest.TestCase):
    def test_r2_the_reach_reads_the_late_command(self):
        got = ct()._codex_rollout_records(raw(records()), "session/native-turn-1.jsonl")
        late_at = "session/native-turn-1.jsonl line 8"
        self.assertIn(late_at, [where for where, _a, _r in got], "the late CommandExecution line is read")
        asked = next(a for where, a, _r in got if where == late_at)
        self.assertIn("cat /tmp/run-e3f03fe0-stage00-finalize.json", json.dumps(asked))

    def test_r2_a_refused_late_shape_leaves_the_reach_unread(self):
        recs = records()
        late(recs)["item"]["source"] = "agent"
        with self.assertRaises(ct().VendorUnreadable) as cm:
            ct()._codex_rollout_records(raw(recs), "session/native-turn-1.jsonl")
        self.assertIn("the rollout reader refuses it", str(cm.exception))


class R3Join(unittest.TestCase):
    def test_r3_the_late_command_joins_an_unfinished_start(self):
        m = cn()
        turn = m.read_rollout(raw(records()))["turns"][0]
        got = m.join(turn, stream(), exit_code=0, session_id=THREAD)
        self.assertEqual((got["complete"], got["commands"]), (True, 1))
        self.assertEqual(m.read_exec(stream())["unfinished_commands"], 1)
        self.assertEqual(m.read_exec(stream(unfinished=False))["unfinished_commands"], 0)

    def test_r3_w_no_unfinished_start_refuses(self):
        m = cn()
        turn = m.read_rollout(raw(records()))["turns"][0]
        with self.assertRaises(m.JoinRefused) as cm:
            m.join(turn, stream(unfinished=False), exit_code=0, session_id=THREAD)
        self.assertIn("after the turn's task_complete", str(cm.exception))

    def test_r3_w_a_repeated_start_id_credits_none(self):
        m = cn()
        doubled = stream().replace(STREAM_UNFINISHED + "\n", STREAM_UNFINISHED + "\n" + STREAM_UNFINISHED + "\n")
        self.assertEqual(m.read_exec(doubled)["unfinished_commands"], 0)


class R4Content(unittest.TestCase):
    def problems(self, recs, text):
        c = ct()
        return c._codex_command_problems(c._host_stream_records([text], "codex"), raw(recs))

    def test_r4_the_late_command_equals_its_unfinished_start(self):
        self.assertEqual(self.problems(records(), stream()), [])

    def test_r4_w_no_unfinished_start_is_a_mismatch(self):
        got = self.problems(records(), stream(unfinished=False))
        self.assertEqual(len(got), 1)
        self.assertIn("[transcript-mismatch] turn 1: a command the rollout records completing after", got[0])

    def test_r4_w_another_argv_is_a_mismatch(self):
        recs = records()
        late(recs)["item"]["command"] = ["/bin/bash", "-lc", "cat /tmp/other"]
        self.assertIn("completing after the turn's task_complete", self.problems(recs, stream())[0])

    def test_r4_w_an_unfinished_start_of_another_turn_is_a_mismatch(self):
        c = ct()
        other = "".join(x + "\n" for x in (json.dumps({"type": "thread.started", "thread_id": THREAD}),
                                             json.dumps({"type": "turn.started"}), STREAM_UNFINISHED))
        recs = c._host_stream_records([stream(unfinished=False), other], "codex")
        self.assertIn("turn 1:", c._codex_command_problems(recs, raw(records()))[0])

    def test_r4_in_turn_commands_compare_as_before(self):
        recs = records()
        recs[4]["payload"]["item"]["command"] = ["ls", "-l"]
        self.assertIn("the argv the rollout records for it", self.problems(recs, stream())[0])


def refusal(edit) -> str:
    m = cn()
    recs = records()
    edit(recs)
    for n, rec in enumerate(recs):
        rec["ordinal"] = 136 + n
    try:
        m.read_rollout(raw(recs))
    except m.ReaderRefused as e:
        return str(e)
    return "ACCEPTED"


def _aborted(recs):
    recs[-2]["payload"] = {"type": "turn_aborted", "turn_id": TURN, "reason": "interrupted",
                           "started_at": 1793080761, "completed_at": 1793080807}


def _separated(recs):
    recs.insert(-1, tcn.line(0, "event_msg", {"type": "token_count", "info": None, "rate_limits": None}))


def _next_turn(recs):
    recs.insert(-1, tcn.line(0, "event_msg", {"type": "task_started", "turn_id": "t2",
                                              "model_context_window": None, "collaboration_mode_kind": "default"}))


def _before_any_turn(recs):
    recs.insert(1, recs.pop())


def _set(path, value):
    def edit(recs):
        target = late(recs)
        for key in path[:-1]:
            target = target[key]
        if value is _DROP:
            target.pop(path[-1])
        else:
            target[path[-1]] = value
    return edit


_DROP = object()

# name -> (the edit, a fragment of its refusal)
WITNESSES = {
    "after-turn-aborted": (_aborted, "does not directly follow its turn's task_complete"),
    "separated-by-a-line": (_separated, "does not directly follow its turn's task_complete"),
    "inside-the-next-turn": (_next_turn, "not the open turn"),
    "before-any-turn": (_before_any_turn, "does not directly follow its turn's task_complete"),
    "another-turn": (_set(["turn_id"], "01a17bf1-0000-7000-8000-000000000000"), "only that turn's own command"),
    "another-thread": (_set(["thread_id"], "other-thread"), "an item names another thread"),
    "agent-message": (_set(["item"], {"type": "AgentMessage", "id": "m9",
                                      "content": [{"type": "Text", "text": "late"}], "phase": "final_answer"}),
                      "only a CommandExecution"),
    "file-change": (_set(["item", "type"], "FileChange"), "only a CommandExecution"),
    "source-agent": (_set(["item", "source"], "agent"), "exit watcher"),
    "no-process-id": (_set(["item", "process_id"], _DROP), "exit watcher"),
    "empty-process-id": (_set(["item", "process_id"], ""), "exit watcher"),
    "id-already-completed": (_set(["item", "id"], "c1"), "an id the turn has not already completed"),
    "started-before-the-turn": (_set(["started_at_ms"], 1793080760999), "started inside its turn"),
    "started-after-the-turn": (_set(["started_at_ms"], 1793080808000), "started inside its turn"),
    "no-started-at": (_set(["started_at_ms"], _DROP), "started inside its turn"),
    "completed-before-started": (_set(["completed_at_ms"], 1793080767644), "started inside its turn"),
    "off-shape-command": (_set(["item", "status"], None), "off its pinned shape"),
}


class Witnesses(unittest.TestCase):
    def test_every_other_out_of_order_shape_refuses_by_name(self):
        for name, (edit, why) in WITNESSES.items():
            with self.subTest(witness=name):
                self.assertIn(why, refusal(edit))

    def test_the_task_complete_without_its_times_refuses_a_late_command(self):
        def edit(recs):
            recs[-2]["payload"].pop("started_at")
        self.assertIn("started inside its turn", refusal(edit))


# ---- mutants: each guard taken out in memory; its bound witness must then fail -------------------------------------
CN_MUTANTS = {
    "m-window": ("            closed = None                       # the late window", "            pass  #",
                 "W.separated-by-a-line"),
    "m-aborted": ("            current = None\n        elif kind == \"item_completed\":",
                  "            closed = (current, pay)\n            current = None\n        elif kind == \"item_completed\":",
                  "W.after-turn-aborted"),
    "m-turn": ('    if tid != turn["turn_id"]:', "    if False:", "W.another-turn"),
    "m-thread": ('    if pay.get("thread_id") != session_id:\n        raise',
                 "    if False:\n        raise", "W.another-thread"),
    "m-kind": ('    if kind != "CommandExecution":', "    if False:", "W.file-change"),
    "m-source": ('    if item.get("source") != "unified_exec_startup" or not (',
                 "    if False or not (", "W.source-agent"),
    "m-process": ('    if item.get("source") != "unified_exec_startup" or not (',
                  '    if item.get("source") != "unified_exec_startup" or False and not (', "W.no-process-id"),
    "m-seen": (' or item["id"] in seen:', ":", "W.id-already-completed"),
    "m-window-times": ("t0 * 1000 <= begun < (t1 + 1) * 1000", "True", "W.started-before-the-turn"),
    "m-ended": ("            and ended >= begun):", "            ):", "W.completed-before-started"),
    "m-join": ('    if len(turn["after_complete"]) > call["unfinished_commands"]:', "    if False:",
               "R3Join.test_r3_w_no_unfinished_start_refuses"),
    "m-repeat": ("    if len(set(begun)) == len(begun):", "    if True:",
                 "R3Join.test_r3_w_a_repeated_start_id_credits_none"),
    "m-output": ('    turn["after_complete"].append(turn["output"].pop())',
                 '    turn["after_complete"].append(dict(turn["output"][-1]))', "R1Red.test_r1_the_w_o69_shape_is_read"),
}
CT_MUTANTS = {
    "m-ct-argv": ("            if split == argv:", "            if True:", "R4Content.test_r4_w_another_argv_is_a_mismatch"),
    "m-ct-turn": ('            if turn != f"turn-{turn_no}.jsonl":', "            if False:",
                  "R4Content.test_r4_w_an_unfinished_start_of_another_turn_is_a_mismatch"),
    "m-ct-late": ("        else:\n            return [f\"[{TRANSCRIPT_MISMATCH}] turn {turn_no}:",
                  "        else:\n            continue\n            return [f\"[{TRANSCRIPT_MISMATCH}] turn {turn_no}:",
                  "R4Content.test_r4_w_no_unfinished_start_is_a_mismatch"),
}


def _compile(name: str, path: Path, old: str, new: str) -> types.ModuleType:
    text = path.read_text()
    assert text.count(old) == 1, f"mutant {name}: its anchor occurs {text.count(old)} times"
    mod = types.ModuleType(f"{path.stem}_{name.replace('-', '_')}")
    mod.__file__ = str(path)
    sys.modules[mod.__name__] = mod          # dataclasses read the defining module from sys.modules
    exec(compile(text.replace(old, new), f"{path} ({name})", "exec"), mod.__dict__)
    return mod


def _bound_fails(target: str) -> bool:
    if target.startswith("W."):
        edit, why = WITNESSES[target[2:]]
        return why not in refusal(edit)
    case, method = target.split(".")
    result = unittest.TestResult()
    globals()[case](method).run(result)
    return not result.wasSuccessful()


def run_mutants() -> int:
    bad = []
    for name, (old, new, target) in {**CN_MUTANTS, **CT_MUTANTS}.items():
        MODS.clear()
        if name in CN_MUTANTS:
            MODS["cn"] = _compile(name, HERE / "codex_native.py", old, new)
        else:
            MODS["ct"] = _compile(name, HERE / "check_take.py", old, new)
        failed = _bound_fails(target)
        print(f"{name}: {'bites' if failed else 'SURVIVES'} ({target})")
        if not failed:
            bad.append(name)
    MODS.clear()
    print("every mutant bites" if not bad else f"SURVIVING: {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    if sys.argv[1:] == ["--mutants"]:
        sys.exit(run_mutants())
    unittest.main()
