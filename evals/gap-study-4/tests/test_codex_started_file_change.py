#!/usr/bin/env python3
"""Lane vendor-b22 (glitch-26's rulings B22-6 to B22-8, Tue 20 Oct 2026): a file_change in item.started (arm O).

    python3 -B -W ignore evals/gap-study-4/tests/test_codex_started_file_change.py               the tests
    python3 -B -W ignore evals/gap-study-4/tests/test_codex_started_file_change.py --witnesses   each mutant alone
    python3 -B -W ignore evals/gap-study-4/tests/test_codex_started_file_change.py --walks <records clone>
                     the committed GPT walks' streams, read by 19c7a88f's transcript_codex and by this tree's

GPT walk w-o38 (gpt-6-luna, plan-gate normal) was held at turn 1: "StreamError: the stream holds a record off the
pre-registered tables: item.started carrying 'file_change': only ('command_execution', 'mcp_tool_call') are
pre-registered there". The pinned Codex exec (openai/codex 092d3acd, rust-v0.162.1) prints a file_change item.started
at apply_patch's Begin stage, always with status "in_progress" (lane-reports/vendor-b22-DESIGN.md section 2c); w-o38's
stream holds two, each followed by its item.completed (types, keys and counts only, design note section 4b).

  F1-admit   a synthetic stream of w-o38's shape (item.started then item.completed file_change, one `update` change,
             between two commands) passes check_record and decode line by line, and read_stream reads it: one
             turn.completed, the file_change's id among the tool ids (on 19c7a88f: refused for the stated reason).
  F2-status  a started file_change is admitted only with the table's keys and status exactly "in_progress": a status
             of "completed", "failed" or 5, no status, an extra key, or a change kind off the tables (B22-7; a
             `delete` is in them since lane pf1-codex-fcdelete, so `rename` stands for it) is refused; the
             completed record's status stays unpinned.
  F3-view    through a COPY of PARSERS: the view holds shell 1, edit 2, shell 3, each with its one result, exactly as
             the completed-only stream reads (no phantom call). Lane vendor-b23 (glitch-26's ruling Q1, option C): the
             started record maps to the edit call itself and its completion to the result, so a cut patch stays a call.
  F4-closed  B22-8: item.started carrying agent_message, reasoning, collab_tool_call, web_search, todo_list or error,
             and an item.updated, are still refused.
  WALKS      --walks: every turn stream of the committed GPT walks reads identically under 19c7a88f's module and this
             tree's: per stream the check outcome of every line, the parser's raw-type counts and the view's call list
             (byte-equal JSON); the totals are pinned to the design note's counts (31 walks, 76 streams).
  MUTANTS    --witnesses: the type removed again, the status check removed, the started record mapped to nothing again
             (B23); each turns its own check red alone.

Every record here is synthetic (types and keys from the pinned source; paths invented); the --walks mode reads the
committed records through `git show` and prints counts only, never a record's text.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import types
import unittest
from collections import Counter
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parents[1]
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))

import codex_adapter as ca  # noqa: E402
import transcript_codex as tc  # noqa: E402
import transcript_view as tv  # noqa: E402

BASE = "19c7a88f"
TID = "0199b2c4-5d6e-7f80-9a1b-2c3d4e5f6a7b"
RUN = "/tmp/run-0a1b2c3d"


def J(rec) -> str:
    return json.dumps(rec)


def cmd(event, n, status):
    return {"type": event, "item": {"id": f"item_{n}", "type": "command_execution", "command": "/bin/bash -lc ls",
                                    "aggregated_output": "" if event == "item.started" else "a\n",
                                    "exit_code": None if event == "item.started" else 0, "status": status}}


def fc(event, n, status, kind="update", **extra):
    item = {"id": f"item_{n}", "type": "file_change", "changes": [{"path": f"{RUN}/gars/plan.md", "kind": kind}],
            "status": status}
    item.update(extra)
    return {"type": event, "item": item}


USAGE = {k: 1 for k in tc.USAGE_KEYS}
HEAD = [{"type": "thread.started", "thread_id": TID}, {"type": "turn.started"}]
TAIL = [{"type": "item.completed", "item": {"id": "item_4", "type": "agent_message", "text": "Done."}},
        {"type": "turn.completed", "usage": USAGE}]
BODY_COMPLETED = [cmd("item.started", 0, "in_progress"), cmd("item.completed", 0, "completed"),
                  fc("item.completed", 1, "completed"),
                  cmd("item.started", 2, "in_progress"), cmd("item.completed", 2, "completed")]
# w-o38's shape: the file_change's item.started directly before its item.completed, between two commands.
BODY_STARTED = BODY_COMPLETED[:2] + [fc("item.started", 1, "in_progress")] + BODY_COMPLETED[2:]
W_O38 = [J(r) for r in HEAD + BODY_STARTED + TAIL]
COMPLETED_ONLY = [J(r) for r in HEAD + BODY_COMPLETED + TAIL]


def refusal(fn, exc) -> str:
    try:
        fn()
    except exc as e:
        return ""
    except Exception as e:  # noqa: BLE001 - a refusal of the wrong type is a finding, named
        return f"raised {type(e).__name__}: {e}"
    return "was admitted"


# ------------------------------------------------------------------------------------------------------- F1
def admit_problems(mod=tc) -> list:
    out = []
    for n, line in enumerate(W_O38, 1):
        try:
            mod.check_record(json.loads(line))
            mod.decode(line)
        except mod.ShapeError as e:
            out.append(f"line {n}: refused: {e}")
    if mod is tc and not out:
        try:
            got = ca.read_stream("\n".join(W_O38) + "\n")
        except ca.StreamError as e:
            out.append(f"read_stream refused: {e}")
        else:
            if (got["completed"], got["failed"], got["tool_ids"]) != (1, 0, ["item_0", "item_1", "item_2"]):
                out.append(f"read_stream read {got['completed']} completed, {got['failed']} failed, "
                           f"tool ids {got['tool_ids']}")
    return out


# ------------------------------------------------------------------------------------------------------- F2
REFUSED_STARTED = {
    "status completed": fc("item.started", 1, "completed"),
    "status failed": fc("item.started", 1, "failed"),
    "status 5": fc("item.started", 1, 5),
    "no status": {"type": "item.started", "item": {"id": "item_1", "type": "file_change",
                                                   "changes": [{"path": f"{RUN}/a", "kind": "update"}]}},
    "an extra key": fc("item.started", 1, "in_progress", diff="+x"),
    "a change kind off the tables (B22-7; pf1-codex-fcdelete)": fc("item.started", 1, "in_progress", kind="rename"),
    "an empty change list": {"type": "item.started", "item": {"id": "item_1", "type": "file_change", "changes": [],
                                                              "status": "in_progress"}},
}


def status_problems(mod=tc) -> list:
    out = [f"a started file_change with {what} {got}" for what, rec in REFUSED_STARTED.items()
           if (got := refusal(lambda rec=rec: mod.check_record(rec), mod.ShapeError))]
    for status in ("completed", "failed"):
        try:
            mod.check_record(fc("item.completed", 1, status))
        except mod.ShapeError as e:
            out.append(f"a completed file_change with status {status} was refused: {e}")
    got = refusal(lambda: mod.check_record(fc("item.completed", 1, "completed", kind="rename")), mod.ShapeError)
    if got:
        out.append(f"a completed file_change with a change kind off the tables {got}")
    for event, status in (("item.started", "in_progress"), ("item.completed", "completed")):
        try:                     # lane pf1-codex-fcdelete (w-o76): a delete is in the tables, in both events
            mod.check_record(fc(event, 1, status, kind="delete"))
        except mod.ShapeError as e:
            out.append(f"a {event} file_change with a delete change was refused: {e}")
    return out


# ------------------------------------------------------------------------------------------------------- F3
def view(mod, lines) -> list:
    with mock.patch.dict(tv.PARSERS, {"codex": mod.CodexParser()}):
        return [(e.kind, e.tool, e.args, e.call, e.text) for e in tv.events("codex", lines)]


def calls(evs) -> list:
    return [(k, tool, n) for k, tool, _a, n, _t in evs if k in (tv.TOOL_CALL, tv.TOOL_RESULT)]


WANT_CALLS = [(tv.TOOL_CALL, tv.SHELL, 1), (tv.TOOL_RESULT, tv.SHELL, 1), (tv.TOOL_CALL, tv.EDIT, 2),
              (tv.TOOL_RESULT, tv.EDIT, 2), (tv.TOOL_CALL, tv.SHELL, 3), (tv.TOOL_RESULT, tv.SHELL, 3)]


def view_problems(mod=tc) -> list:
    try:
        started, completed = view(mod, W_O38), view(mod, COMPLETED_ONLY)
    except tv.ViewError as e:
        return [f"the view refuses: {e}"]
    out = []
    if calls(started) != WANT_CALLS:
        out.append(f"w-o38's shape reads calls {calls(started)}")
    if started != completed:
        out.append("w-o38's shape and the completed-only stream read differently")
    try:
        raw = mod.CodexParser().items(J(fc("item.started", 1, "in_progress")))
    except mod.ShapeError as e:
        return out + [f"the parser refuses the started record: {e}"]
    # B23 (glitch-26's ruling Q1, option C): the started record carries the edit call, its completion the result.
    if [(i.kind, i.tool, i.ref) for i in raw] != [(tv.TOOL_CALL, tv.EDIT, "item_1#0")]:
        out.append(f"the started record maps to {[(i.kind, i.tool, i.ref) for i in raw]}, not to its one edit call")
    return out


# ------------------------------------------------------------------------------------------------------- F4
CLOSED = {
    "item.started agent_message": {"type": "item.started", "item": {"id": "i", "type": "agent_message", "text": "x"}},
    "item.started reasoning": {"type": "item.started", "item": {"id": "i", "type": "reasoning", "text": "x"}},
    "item.started collab_tool_call": {"type": "item.started", "item": {
        "id": "i", "type": "collab_tool_call", "tool": "spawn_agent", "sender_thread_id": "t",
        "receiver_thread_ids": [], "prompt": None, "agents_states": {}, "status": "in_progress"}},
    "item.started web_search": {"type": "item.started", "item": {"id": "i", "type": "web_search", "query": "q",
                                                                 "action": {"type": "other"}}},
    "item.started todo_list": {"type": "item.started", "item": {"id": "i", "type": "todo_list", "items": []}},
    "item.started error": {"type": "item.started", "item": {"id": "i", "type": "error", "message": "m"}},
    "item.updated todo_list": {"type": "item.updated", "item": {"id": "i", "type": "todo_list", "items": []}},
    "item.completed collab_tool_call": {"type": "item.completed", "item": {
        "id": "i", "type": "collab_tool_call", "tool": "wait", "sender_thread_id": "t", "receiver_thread_ids": [],
        "prompt": None, "agents_states": {}, "status": "completed"}},
}


def closed_problems(mod=tc) -> list:
    return [f"{what} {got}" for what, rec in CLOSED.items()
            if (got := refusal(lambda rec=rec: mod.check_record(rec), mod.ShapeError))]


# ------------------------------------------------------------------------------------------------------- MUTANTS
class WitnessNotPerformed(RuntimeError):
    pass


_ABSENT = object()


def module_from(src: str, name: str) -> types.ModuleType:
    mod = types.ModuleType(name)
    mod.__file__ = str(HERE / "transcript_codex.py")
    # Lane vendor-b23 round 4 (glitch-26's ruling B23-7): put back exactly what the exec changes, the path list and
    # the prior module object under this name.
    path, prior = list(sys.path), sys.modules.get(name, _ABSENT)
    sys.modules[name] = mod
    try:
        exec(compile(src, f"transcript_codex.py ({name})", "exec"), mod.__dict__)
    finally:
        sys.path[:] = path
        if prior is _ABSENT:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = prior
    return mod


def mutant(edits) -> types.ModuleType:
    src = (HERE / "transcript_codex.py").read_text(encoding="utf-8")
    for old, new in edits:
        if src.count(old) != 1:
            raise WitnessNotPerformed(f"the anchor occurs {src.count(old)} times: {old[:60]!r}")
        src = src.replace(old, new)
    return module_from(src, "transcript_codex_b22_witness")


MUTANTS = [
    ("type-removed-again", (("STARTED_ITEM_TYPES = (COMMAND_EXECUTION, FILE_CHANGE, MCP_TOOL_CALL)",
                             "STARTED_ITEM_TYPES = (COMMAND_EXECUTION, MCP_TOOL_CALL)"),), "admit"),
    ("status-check-removed", (("    if t == ITEM_STARTED and it == FILE_CHANGE and item.get(\"status\") != "
                               "STARTED_FILE_CHANGE_STATUS:\n",
                               "    if False:\n"),), "status"),
    ("started-maps-to-nothing", (("                return self._file_change_started(item, raw)\n",
                                  "                return []\n"),), "view"),
]
CHECKS = {"admit": admit_problems, "status": status_problems, "view": view_problems, "closed": closed_problems}


def witnesses() -> list:
    """Each mutant alone, applied to this tree's module: (name, its check, red?, every check it turns red)."""
    import mutation_baseline  # lane t104-mutation-baseline: the unmutated selection runs first; a red one refuses (exit 3), nothing counted
    def unmutated():
        mod = mutant(())
        return [f"{c}: {x}" for c in CHECKS for x in CHECKS[c](mod)]
    mutation_baseline.require_clean("test_codex_started_file_change witnesses", unmutated)
    out = []
    for name, edits, check in MUTANTS:
        mod = mutant(edits)
        reds = sorted(c for c in CHECKS if CHECKS[c](mod))
        out.append((name, check, check in reds, reds))
    return out


# ------------------------------------------------------------------------------------------------------- WALKS
# The design note's counts (section 4a): 31 committed GPT walks, 76 turn streams.
WALK_TOTALS = {"walks": 31, "streams": 76, "thread.started": 76, "turn.started": 76, "turn.completed": 76,
               "item.started:command_execution": 188, "item.completed:command_execution": 188,
               "item.completed:agent_message": 141}


def _git(*args) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True, errors="surrogateescape").stdout


def base_module() -> types.ModuleType:
    return module_from(_git("-C", str(REPO), "show", f"{BASE}:evals/gap-study-4/transcript_codex.py"),
                       "transcript_codex_b22_base")


def reading(mod, lines) -> str:
    """One stream's reading: every line's check outcome, the parser's raw-type counts, the view's events."""
    outcome = []
    for line in lines:
        try:
            outcome.append("/".join(str(x) for x in mod.check_record(json.loads(line))))
        except mod.ShapeError as e:
            outcome.append(f"refused: {e}")
    raw = Counter(it.raw_type for line in lines for it in mod.CodexParser().items(line))
    return json.dumps({"lines": outcome, "raw": sorted(raw.items()), "view": view(mod, lines)}, sort_keys=True)


def walk_streams(clone: str):
    """(walk, stream path, lines) for every turn stream of every committed GPT walk in the records clone."""
    refs = _git("-C", clone, "for-each-ref", "--format=%(refname:short)", "refs/heads/walk/w-*").split()
    for ref in refs:
        files = _git("-C", clone, "diff", "--name-only", f"walk/ship-20261019...{ref}").split()
        walks = {f.split("/")[3] for f in files if f.startswith("evals/gap-study-4/rehearsals/w-o")}
        for walk in sorted(walks):
            base = f"evals/gap-study-4/rehearsals/{walk}/"
            for f in sorted(x for x in files if x.startswith(base + "turn-") and x.endswith(".jsonl")):
                yield walk, f, tv.jsonl_lines(_git("-C", clone, "show", f"{ref}:{f}"))


def walk_problems(clone: str) -> tuple:
    old, new = base_module(), tc
    totals, out, digest = Counter(), [], hashlib.sha256()
    walks = set()
    for walk, f, lines in walk_streams(clone):
        walks.add(walk)
        totals["streams"] += 1
        a, b = reading(old, lines), reading(new, lines)
        digest.update(b.encode())
        if a != b:
            out.append(f"{walk} {Path(f).name}: reads differently before and after")
        for line in lines:
            rec = json.loads(line)
            it = rec.get("item", {}).get("type") if isinstance(rec.get("item"), dict) else None
            totals[f"{rec.get('type')}:{it}" if it else rec.get("type")] += 1
    totals["walks"] = len(walks)
    if dict(totals) != WALK_TOTALS:
        out.append(f"the totals are {dict(sorted(totals.items()))}, not the design note's {WALK_TOTALS}")
    return out, dict(totals), digest.hexdigest()


# ------------------------------------------------------------------------------------------------------- tests
class F1Admit(unittest.TestCase):
    def test_w_o38_shape_reads(self):
        self.assertEqual(admit_problems(), [])


class F2Status(unittest.TestCase):
    def test_a_started_file_change_only_in_progress_and_the_tables_keys(self):
        self.assertEqual(status_problems(), [])


class F3View(unittest.TestCase):
    def test_the_started_record_adds_no_call(self):
        self.assertEqual(view_problems(), [])


class F4Closed(unittest.TestCase):
    def test_every_other_type_stays_refused(self):
        self.assertEqual(closed_problems(), [])


class Mutants(unittest.TestCase):
    def test_every_mutant_is_red_alone(self):
        got = witnesses()
        self.assertEqual(len(got), 3)
        self.assertEqual([(n, c) for n, c, red, _reds in got if not red], [])


if __name__ == "__main__":
    if sys.argv[1:] == ["--witnesses"]:
        got = witnesses()
        for n, c, red, reds in got:
            print(f"{'red  ' if red else 'GREEN'} {n} ({c}); red checks: {', '.join(reds) or 'none'}")
        print(f"witnesses: {sum(r for _, _, r, _x in got)}/{len(got)} red")
        raise SystemExit(0 if all(r for _, _, r, _x in got) else 1)
    if len(sys.argv) == 3 and sys.argv[1] == "--walks":
        problems, totals, digest = walk_problems(sys.argv[2])
        print("walks totals: " + ", ".join(f"{k} {v}" for k, v in sorted(totals.items())))
        print(f"walks readings sha256 (this tree): {digest}")
        for p in problems:
            print(f"PROBLEM {p}")
        print(f"walks: {totals.get('streams', 0)} streams of {totals.get('walks', 0)} walks, "
              f"{'identical before and after' if not problems else f'{len(problems)} problem(s)'}")
        raise SystemExit(1 if problems else 0)
    unittest.main(verbosity=2)
