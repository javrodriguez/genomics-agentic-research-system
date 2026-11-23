#!/usr/bin/env python3
"""Lane vendor-b23 (glitch-26's rulings Q1 to Q6 and B23-2, Tue 20 Oct 2026): a Codex patch edit read and graded as a
shell edit is (arm O). Design note lane-reports/vendor-b23-DESIGN.md (sections 4 to 7 and 14).

    python3 -B -W ignore evals/gap-study-4/tests/test_codex_patch_reads.py               the tests
    python3 -B -W ignore evals/gap-study-4/tests/test_codex_patch_reads.py --witnesses   each mutant alone
    python3 -B -W ignore evals/gap-study-4/tests/test_codex_patch_reads.py --walks <records clone>
                     the committed GPT walks' streams, read by a76b4dd2's transcript_codex and by this tree's
    python3 -B -W ignore evals/gap-study-4/tests/test_codex_patch_reads.py --unchanged
                     the vendor fixtures' readings (codex and gemini) under a76b4dd2's tree and this one, compared

The pinned Codex (openai/codex 092d3acd, rust-v0.162.1) writes a patch edit as a file_change in the exec stream (paths
and kinds, started at the tool's Begin stage and completed after it) and as a FileChange item in the rollout (per path
its content, diff and rename target). Until B23 the rollout reader and the exec join refused it, and check_take's
T-8:file-change leg had no reader.

  V1-unpaired  Q1 (option C): a patch the take's cut left unfinished (an item.started file_change with no completion)
               is an edit call with no result in the view, like a killed command (on a76b4dd2 it vanished).
  V2-paired    w-o38's shape (started directly before its completion) and a completed-only stream read exactly as
               they read on a76b4dd2, event for event.
  V3-reset     one parser over two streams (bound_items and vendor_shell_commands drive one per take): each stream's
               exec ids start again at thread.started, and a second stream's item_1 is a new call.
  V4-closed    a completed file_change whose changes are not its started record's, and a second item.started with the
               same id, are refused.
  N1-project   codex_native.read_rollout projects a FileChange item on its pinned shape: one file_change output with
               its status and its changes sorted by path (on a76b4dd2: refused, "unsupported in this subset").
  N2-shape     a FileChange off its pinned shape is refused: a change kind off the tables (Q4; a delete is in them
               since lane pf1-codex-fcdelete), a delete with an extra key, an auto_approved key, a
               status of in_progress or 5, no stdout, empty changes, a change without move_path or with a move_path of
               5, an add with an extra key.
  N3-join      read_exec reads a completed file_change and join matches it to the rollout's by order: equal counts,
               paths and kinds; completed to completed, failed or declined to failed (on a76b4dd2: refused). Each
               disagreement is refused by join itself (review b0c917ff m1, mutant join-wiring-dropped).
  K1-reach     check_take's rollout records hold each FileChange as one tool record, its path keys handed over as
               values (C's string walk never reads a key), stdout and stderr as what it returned (on a76b4dd2: the
               rollout refuses).
  K2-site      the T-8:file-change site hands vendor_pending its reader, vendor_file_change_reads, and while the row is
               PENDING its refusal is byte for byte the old one (Q3); since lane vendor-settle stage V the live row is
               settled (NOT COMPARABLE), so the PENDING reading is taken on the row put back (TEST DATA), and the live
               row reads a joined patch clean and holds a rename.
  K3-reader    the reader, the row settled in a test: a joined take reads clean; a rename (move_path) is held under a
               named transcript-unreadable reason (Q2); a stream patch the rollout does not hold is transcript-unreadable.
  MUTANTS      --witnesses: one mutant per guard, each applied alone to this tree's module, each turning its own check
               red (the checks it also turns red are printed: a guard upstream of another reddens both).
  WALKS        --walks: the 76 turn streams of the 31 committed GPT walks read identically under a76b4dd2's module and
               this tree's (B22's reading, its totals and its sha256).
  UNCHANGED    --unchanged: F1 (codex) and F2 (gemini) and the codex-streams fixtures, read under a76b4dd2's tree (git
               archive into a scratch folder) and this one, print identical readings.

Every record here is synthetic (types and keys from the pinned source; paths invented). The --walks mode reads the
committed records through `git show` and prints counts only, never a record's text.
"""

from __future__ import annotations

import ast
import contextlib
import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parents[1]
REPO = HERE.parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
if str(HERE / "tests") not in sys.path:
    sys.path.insert(1, str(HERE / "tests"))

BASE = "a76b4dd2"
TID = "0199b2c4-5d6e-7f80-9a1b-2c3d4e5f6a7b"
RUN = "/tmp/run-0a1b2c3d"
PATH_A = f"{RUN}/gars/plan.md"
PATH_B = f"{RUN}/gars/notes.md"
_ABSENT = object()

# Lane vendor-b23 round 4 (glitch-26's ruling B23-7; athena battery gap4-t5-b23-a67b2b7, test_round4): check_take.py puts
# evals/ and the study folder on sys.path whenever its source runs (its first import here, and each of its mutants), and
# test_confounded_design's contract-drift test, run later in the same process, refuses evals/ on the path. setUpModule
# records sys.path and tearDownModule puts back exactly that list, in place; module_from and dump restore their own.
_STACK = contextlib.ExitStack()


def setUpModule():
    _STACK.callback(sys.path.__setitem__, slice(None), list(sys.path))


def tearDownModule():
    _STACK.close()


class WitnessNotPerformed(RuntimeError):
    pass


def J(rec) -> str:
    return json.dumps(rec)


def _mods():
    import check_take as ct
    import codex_native as cn
    import transcript_codex as tc
    import transcript_view as tv
    return ct, cn, tc, tv


# ---------------------------------------------------------------------------------------------- exec stream records
def cmd(event, n, status):
    return {"type": event, "item": {"id": f"item_{n}", "type": "command_execution", "command": "/bin/bash -lc ls",
                                    "aggregated_output": "" if event == "item.started" else "a\n",
                                    "exit_code": None if event == "item.started" else 0, "status": status}}


def fc(event, n, status, changes=None):
    changes = [{"path": PATH_A, "kind": "update"}] if changes is None else changes
    return {"type": event, "item": {"id": f"item_{n}", "type": "file_change", "changes": changes, "status": status}}


USAGE = {"input_tokens": 1, "cached_input_tokens": 1, "cache_write_input_tokens": 1, "output_tokens": 1,
         "reasoning_output_tokens": 1}
HEAD = [{"type": "thread.started", "thread_id": TID}, {"type": "turn.started"}]
TAIL = [{"type": "item.completed", "item": {"id": "item_4", "type": "agent_message", "text": "Done."}},
        {"type": "turn.completed", "usage": USAGE}]
CMD0 = [cmd("item.started", 0, "in_progress"), cmd("item.completed", 0, "completed")]
CMD2 = [cmd("item.started", 2, "in_progress"), cmd("item.completed", 2, "completed")]
W_O38 = [J(r) for r in HEAD + CMD0 + [fc("item.started", 1, "in_progress"), fc("item.completed", 1, "completed")]
         + CMD2 + TAIL]
COMPLETED_ONLY = [J(r) for r in HEAD + CMD0 + [fc("item.completed", 1, "completed")] + CMD2 + TAIL]
# A take cut by its timeout while the patch ran: exec killed, so no completion and no turn.completed.
CUT = [J(r) for r in HEAD + CMD0 + [fc("item.started", 1, "in_progress")]]


def view(tc, tv, lines) -> list:
    with mock.patch.dict(tv.PARSERS, {"codex": tc.CodexParser()}):
        return [(e.turn, e.kind, e.text, e.tool, e.args, e.call) for e in tv.events("codex", lines)]


def calls(tv, evs) -> list:
    return [(k, tool, n) for _turn, k, _x, tool, _a, n in evs if k in (tv.TOOL_CALL, tv.TOOL_RESULT)]


# --------------------------------------------------------------------------------------------------------- V1-V4
def unpaired_problems(tc=None) -> list:
    _ct, _cn, tc0, tv = _mods()
    tc = tc or tc0
    try:
        got = calls(tv, view(tc, tv, CUT))
    except tv.ViewError as e:
        return [f"the view refuses the cut stream: {e}"]
    want = [(tv.TOOL_CALL, tv.SHELL, 1), (tv.TOOL_RESULT, tv.SHELL, 1), (tv.TOOL_CALL, tv.EDIT, 2)]
    return [] if got == want else [f"the cut stream reads calls {got}, not {want} (the attempted edit vanished)"]


def base_module(rel: str, name: str) -> types.ModuleType:
    src = subprocess.run(["git", "-C", str(REPO), "show", f"{BASE}:evals/gap-study-4/{rel}"], capture_output=True,
                         text=True, check=True).stdout
    return module_from(src, name, HERE / rel)


def paired_problems(tc=None) -> list:
    _ct, _cn, tc0, tv = _mods()
    tc = tc or tc0
    old = base_module("transcript_codex.py", "transcript_codex_b23_base")
    out = []
    for name, lines in (("w-o38's shape", W_O38), ("the completed-only stream", COMPLETED_ONLY)):
        try:
            a, b = view(old, tv, lines), view(tc, tv, lines)
        except tv.ViewError as e:
            out.append(f"{name}: the view refuses: {e}")
            continue
        if json.dumps(a) != json.dumps(b):
            out.append(f"{name} reads differently on {BASE} and on this tree")
    return out


def reset_problems(tc=None) -> list:
    _ct, _cn, tc0, tv = _mods()
    tc = tc or tc0
    parser = tc.CodexParser()
    # stream 1 is cut with its patch started (its item_1 never completes); stream 2 numbers its own patch item_1 too
    streams = {1: [J(r) for r in HEAD + [fc("item.started", 1, "in_progress")]],
               2: [J(r) for r in HEAD + [fc("item.started", 1, "in_progress"), fc("item.completed", 1, "completed")]]}
    items = []
    try:
        for n, stream in streams.items():
            for line in stream:
                items += [(n, it.kind, it.ref) for it in parser.items(line) if it.kind in (tv.TOOL_CALL,
                                                                                           tv.TOOL_RESULT)]
    except tc.ShapeError as e:
        return [f"the second stream is refused: {e}"]
    want = [(1, tv.TOOL_CALL, "item_1#0"), (2, tv.TOOL_CALL, "item_1#0"), (2, tv.TOOL_RESULT, "item_1#0")]
    return [] if items == want else [f"two streams read {items}, not {want}"]


def _refused(tc, lines) -> bool:
    parser = tc.CodexParser()
    try:
        for line in lines:
            parser.items(line)
    except tc.ShapeError:
        return True
    return False


def changed_changes_problems(tc=None) -> list:
    _ct, _cn, tc0, _tv = _mods()
    tc = tc or tc0
    lines = [J(r) for r in HEAD + [fc("item.started", 1, "in_progress"),
                                   fc("item.completed", 1, "completed", [{"path": PATH_B, "kind": "update"}])]]
    return [] if _refused(tc, lines) else ["a completed file_change whose changes are not its started record's was read"]


def second_start_problems(tc=None) -> list:
    _ct, _cn, tc0, _tv = _mods()
    tc = tc or tc0
    lines = [J(r) for r in HEAD + [fc("item.started", 1, "in_progress"), fc("item.started", 1, "in_progress")]]
    return [] if _refused(tc, lines) else ["a second item.started for one file_change id was read"]


# ------------------------------------------------------------------------------------------------ rollout records
def file_change_item(*, path=PATH_A, kind="update", move_path=None, status="completed", **extra):
    change = ({"type": "add", "content": "x\n"} if kind == "add" else
              {"type": "delete", "content": "x\n"} if kind == "delete" else
              {"type": "update", "unified_diff": "@@\n-a\n+b see /opt/elsewhere/secret.txt\n", "move_path": move_path})
    item = {"type": "FileChange", "id": "call_p1", "changes": {path: change}, "status": status,
            "stdout": "Success. Updated the following files:\n", "stderr": ""}
    item.update(extra)
    return item


def take_parts(item=None, *, stream_changes=None, stream_status="completed", in_stream=True, in_rollout=True):
    """vendor_check_fixtures' codex take, turn 1 holding one patch: in the stream (started and completed) and in the
    rollout (its FileChange item, before the agent message)."""
    import vendor_check_fixtures as vcf
    parts = vcf.codex_parts()
    item = file_change_item() if item is None else item
    changes = stream_changes if stream_changes is not None else sorted(
        ({"path": p, "kind": c["type"]} for p, c in item["changes"].items()), key=lambda c: c["path"])
    if in_stream:
        parts["streams"][1][4:4] = [fc("item.started", 2, "in_progress", changes),
                                    fc("item.completed", 2, stream_status, changes)]
    if in_rollout:
        at = [n for n, (t, pay) in enumerate(parts["rollout"][1])
              if t == "event_msg" and (pay.get("item") or {}).get("type") == "AgentMessage"][0]
        parts["rollout"][1].insert(at - 1, ("event_msg", {"type": "item_completed", "thread_id": vcf.CODEX_TID,
                                                          "turn_id": "t1", "item": item, "completed_at_ms": 0}))
    return parts


def snapshot(parts) -> bytes:
    import vendor_check_fixtures as vcf
    return vcf._codex_snapshot(parts, max(parts["rollout"]))


def write_take(parts, folder: Path) -> Path:
    import vendor_check_fixtures as vcf
    return vcf.write(folder, "codex", parts)


def project_problems(cn=None) -> list:
    _ct, cn0, _tc, _tv = _mods()
    cn = cn or cn0
    try:
        turns = cn.read_rollout(snapshot(take_parts()))["turns"]
    except cn.ReaderRefused as e:
        return [f"the rollout reader refuses a FileChange: {e}"]
    got = [o for o in turns[0]["output"] if o["kind"] == "file_change"]
    want = [{"kind": "file_change", "status": "completed",
             "changes": [{"path": PATH_A, "kind": "update", "move_path": None}]}]
    out = [] if got == want else [f"turn 1 projects {got}, not {want}"]
    two = file_change_item()
    two["changes"] = {PATH_B: {"type": "add", "content": "y\n"}, PATH_A: two["changes"][PATH_A]}
    try:
        got = [o for o in cn.read_rollout(snapshot(take_parts(two)))["turns"][0]["output"] if o["kind"] == "file_change"]
    except cn.ReaderRefused as e:
        return out + [f"a two-file FileChange is refused: {e}"]
    if [c["path"] for c in got[0]["changes"]] != sorted([PATH_A, PATH_B]):
        out.append(f"a two-file FileChange's changes are not sorted by path: {got[0]['changes']}")
    return out


SHAPE_REFUSALS = {
    "a change kind off the tables (Q4; pf1-codex-fcdelete)": dict(file_change_item(), changes={
        PATH_A: {"type": "rename", "content": "x\n"}}),
    "a delete with an extra key": dict(file_change_item(), changes={
        PATH_A: {"type": "delete", "content": "x\n", "move_path": None}}),
    "an auto_approved key": file_change_item(auto_approved=True),
    "status in_progress": file_change_item(status="in_progress"),
    "status 5": file_change_item(status=5),
    "no stdout": {k: v for k, v in file_change_item().items() if k != "stdout"},
    "empty changes": dict(file_change_item(), changes={}),
    "a change without move_path": dict(file_change_item(), changes={PATH_A: {"type": "update", "unified_diff": "@@\n"}}),
    "a move_path of 5": file_change_item(move_path=5),
    "an add with an extra key": dict(file_change_item(), changes={PATH_A: {"type": "add", "content": "x", "diff": ""}}),
}


def shape_problems(cn=None) -> list:
    _ct, cn0, _tc, _tv = _mods()
    cn = cn or cn0
    out = []
    for what, item in SHAPE_REFUSALS.items():
        try:
            cn.read_rollout(snapshot(take_parts(item)))
        except cn.ReaderRefused:
            continue
        out.append(f"a FileChange with {what} was read")
    try:
        cn.read_rollout(snapshot(take_parts(file_change_item(move_path=PATH_B))))
    except cn.ReaderRefused as e:
        out.append(f"a FileChange with a move_path is refused by the reader (the T-8 reader holds it, Q2): {e}")
    return out


def _join(cn, parts, *, count=True):
    """join's own result, and (with `count`) how many file changes join_file_changes matched in the same turn. The
    refusal cases pass count=False, so a refusal they see is join's own (review b0c917ff m1: join's call of
    join_file_changes is the drive's cross-check road)."""
    import vendor_check_fixtures as vcf
    turn = cn.read_rollout(snapshot(parts))["turns"][0]
    text = "".join(json.dumps(r) + "\n" for r in parts["streams"][1])
    got = cn.join(turn, text, exit_code=0, session_id=vcf.CODEX_TID)
    if not count:
        return got
    return dict(got, file_changes=cn.join_file_changes(turn, cn.read_exec(text, model=turn["requested_model"])))


def join_problems(cn=None) -> list:
    _ct, cn0, _tc, _tv = _mods()
    cn = cn or cn0
    out = []
    for what, parts in (("a completed patch", take_parts()),
                        ("a declined patch (exec prints failed)", take_parts(file_change_item(status="declined"),
                                                                             stream_status="failed")),
                        ("a failed patch", take_parts(file_change_item(status="failed"), stream_status="failed"))):
        try:
            got = _join(cn, parts)
        except (cn.JoinRefused, cn.ReaderRefused) as e:
            out.append(f"{what}: refused: {e}")
            continue
        if got.get("file_changes") != 1:
            out.append(f"{what}: join reads file_changes {got.get('file_changes')!r}, not 1")
    return out


JOIN_REFUSALS = {
    "the stream's patch missing from the rollout": dict(in_rollout=False),
    "the rollout's patch missing from the stream": dict(in_stream=False),
    "another path in the stream": dict(stream_changes=[{"path": PATH_B, "kind": "update"}]),
    "another kind in the stream": dict(stream_changes=[{"path": PATH_A, "kind": "add"}]),
    "a completed rollout patch the stream prints failed": dict(stream_status="failed"),
}


def join_refusal_problems(cn=None) -> list:
    _ct, cn0, _tc, _tv = _mods()
    cn = cn or cn0
    out = []
    for what, kw in JOIN_REFUSALS.items():
        try:
            _join(cn, take_parts(**kw), count=False)
        except cn.JoinRefused:
            continue
        except cn.ReaderRefused as e:
            out.append(f"{what}: the rollout reader refused it ({e}), not the join")
            continue
        out.append(f"{what}: joined")
    return out


# ------------------------------------------------------------------------------------------------------ check_take
def reach_problems(ct=None) -> list:
    ct0, _cn, _tc, _tv = _mods()
    ct = ct or ct0
    item = file_change_item(path=f"{RUN}/elsewhere/a.md", move_path=None)
    try:
        recs = ct._codex_rollout_records(snapshot(take_parts(item)), "session/native-turn-2.jsonl")
    except ct.VendorUnreadable as e:
        return [f"the rollout records refuse a FileChange: {e}"]
    fcs = [r for r in recs if r[1].get("type") == "FileChange" or r[2].get("type") == "FileChange"]
    if len(fcs) != 1:
        return [f"{len(fcs)} FileChange tool records, not 1"]
    _where, asked, returned = fcs[0]
    out = []
    if set(returned) != {"stdout", "stderr"}:
        out.append(f"the FileChange record returned {sorted(returned)}, not stdout and stderr")
    strings = [s for line in ct.vendor_reach_lines([fcs[0]]) for s in ct._tool_strings(json.loads(line))]
    for want in (f"{RUN}/elsewhere/a.md", "@@\n-a\n+b see /opt/elsewhere/secret.txt\n"):
        if want not in strings:
            out.append(f"reach's string walk does not read {want[:40]!r} from the FileChange record")
    return out


def _site_call(src: str):
    tree = ast.parse(src)
    fn = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "vendor_file_change_problems"]
    if len(fn) != 1:
        return None
    got = [n for n in ast.walk(fn[0]) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
           and n.func.id == "vendor_pending"]
    return got[0] if len(got) == 1 else None


PENDING_TEXT = ["[transcript-unreadable] no vendor reader yet (T-8:file-change)"]


def site_problems(ct=None) -> list:
    ct0, _cn, _tc, _tv = _mods()
    ct = ct or ct0
    call = _site_call(Path(ct.__file__).read_text(encoding="utf-8") if ct is ct0 else ct.__source__)
    out = []
    if call is None:
        return ["vendor_file_change_problems holds no single vendor_pending call"]
    reader = call.args[2] if len(call.args) > 2 else None
    if not (isinstance(reader, ast.Name) and reader.id == "vendor_file_change_reads"):
        out.append(f"the T-8:file-change site hands in {ast.dump(reader) if reader else None}, not "
                   "vendor_file_change_reads")
    if [ast.dump(a) for a in call.args[3:]] != [ast.dump(ast.Name("path", ast.Load()))]:
        out.append("the T-8:file-change site does not hand the reader the take's path")
    # lane vendor-settle stage V (S6): the live row is settled (NOT COMPARABLE, glitch-f1's adopted T-8 ruling), so
    # the PENDING reading is taken with the row put back to PENDING (TEST DATA), and the live row runs the reader
    pending = copy.deepcopy(ct.VENDOR_PENDING_ROWS)
    pending["codex"]["T-8:file-change"] = {"reason": ct.TRANSCRIPT_UNREADABLE, "state": ct.PENDING}
    with tempfile.TemporaryDirectory() as tmp:
        path = write_take(take_parts(), Path(tmp))
        with mock.patch.object(ct, "VENDOR_PENDING_ROWS", pending):
            got = ct.vendor_file_change_problems(path, "codex")
        live = ct.vendor_file_change_problems(path, "codex")
        renamed = write_take(take_parts(file_change_item(move_path=PATH_B)), Path(tmp) / "renamed")
        live_rename = ct.vendor_file_change_problems(renamed, "codex")
    if got != PENDING_TEXT:
        out.append(f"the PENDING row reads {got}, not {PENDING_TEXT}")
    if live != []:
        out.append(f"the settled row reads a joined patch as {live}, not clean")
    if not any(p.startswith(f"[{ct.TRANSCRIPT_UNREADABLE}] ") and "rename" in p for p in live_rename):
        out.append(f"the settled row does not hold a rename through the patch tool: {live_rename}")
    return out


def _settled(ct):
    row = {"reason": ct.TRANSCRIPT_UNREADABLE, "state": "SAME", "fixture": "vendor-check-codex/turn-1.jsonl",
           "reader": "vendor_file_change_reads"}
    rows = copy.deepcopy(ct.VENDOR_PENDING_ROWS)
    rows["codex"]["T-8:file-change"] = row
    return mock.patch.multiple(ct, VENDOR_PENDING_ROWS=rows, _vendor_recorded_fixture_problem=lambda h, f: None)


def reader_problems(ct=None) -> list:
    ct0, _cn, _tc, _tv = _mods()
    ct = ct or ct0
    if not callable(getattr(ct, "vendor_file_change_reads", None)):
        return ["check_take.py defines no vendor_file_change_reads"]
    out = []
    cases = (("a joined patch", take_parts(), None),
             ("a rename", take_parts(file_change_item(move_path=PATH_B)), "a rename through the patch tool"),
             ("a stream patch the rollout does not hold", take_parts(in_rollout=False), "do not join"))
    for what, parts, want in cases:
        with tempfile.TemporaryDirectory() as tmp, _settled(ct):
            path = write_take(parts, Path(tmp))
            try:
                got = ct.vendor_file_change_problems(path, "codex")
            except Exception as e:  # noqa: BLE001 - a traceback is itself a finding
                out.append(f"{what}: raised {type(e).__name__}: {e}")
                continue
        if want is None and got != []:
            out.append(f"{what}: read {got}, not clean")
        if want is not None and not (len(got) == 1 and got[0].startswith("[transcript-unreadable] ")
                                     and want in got[0]):
            out.append(f"{what}: read {got}, not one transcript-unreadable naming {want!r}")
    return out


# ------------------------------------------------------------------------------------------------------- MUTANTS
def module_from(src: str, name: str, file: Path) -> types.ModuleType:
    mod = types.ModuleType(name)
    mod.__file__ = str(file)
    mod.__source__ = src
    path, prior = list(sys.path), sys.modules.get(name, _ABSENT)      # B23-7: put back exactly what the exec changes
    sys.modules[name] = mod
    try:
        exec(compile(src, f"{file.name} ({name})", "exec"), mod.__dict__)
    finally:
        sys.path[:] = path
        if prior is _ABSENT:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = prior
    return mod


def mutant(rel: str, edits) -> types.ModuleType:
    src = (HERE / rel).read_text(encoding="utf-8")
    for old, new in edits:
        if src.count(old) != 1:
            raise WitnessNotPerformed(f"{rel}: the anchor occurs {src.count(old)} times: {old[:70]!r}")
        src = src.replace(old, new)
    return module_from(src, f"{Path(rel).stem}_b23_witness", HERE / rel)


TC, CN, CT = "transcript_codex.py", "codex_native.py", "check_take.py"
MUTANTS = [
    ("started-maps-to-nothing-again", TC, (("                return self._file_change_started(item, raw)\n",
                                            "                return []\n"),), "unpaired"),
    ("no-reset-at-thread-started", TC, (("            self._started = {}\n", "            pass\n"),), "reset"),
    ("changed-changes-admitted", TC, (("            if started != changes:\n", "            if False:\n"),),
     "changed"),
    ("second-start-admitted", TC, (("        if item[\"id\"] in self._started:\n", "        if False:\n"),),
     "second-start"),
    ("filechange-not-projected", CN, (('PROJECTED_ITEMS = ("UserMessage", "AgentMessage", "Reasoning", '
                                       '"CommandExecution", "FileChange")',
                                       'PROJECTED_ITEMS = ("UserMessage", "AgentMessage", "Reasoning", '
                                       '"CommandExecution")'),), "project"),
    ("status-pin-widened", CN, (("    if item[\"status\"] not in FILE_CHANGE_STATUSES:\n",
                                 "    if not isinstance(item[\"status\"], str):\n"),), "shape"),
    ("auto-approved-admitted", CN, (('FILE_CHANGE_KEYS = ("type", "id", "changes", "status", "stdout", "stderr")',
                                     'FILE_CHANGE_KEYS = ("type", "id", "changes", "status", "stdout", "stderr", '
                                     '"auto_approved")'),
                                    ("    if set(item) != set(FILE_CHANGE_KEYS):\n",
                                     "    if not set(FILE_CHANGE_KEYS) - {\"auto_approved\"} <= set(item) "
                                     "<= set(FILE_CHANGE_KEYS):\n")), "shape"),
    ("unknown-kind-admitted", CN, (('        if kind not in FILE_CHANGE_KINDS or set(change) != '
                                    'set(FILE_CHANGE_KINDS[kind]):\n',
                                    '        if kind in FILE_CHANGE_KINDS and set(change) != '
                                    'set(FILE_CHANGE_KINDS[kind]):\n'),), "shape"),
    ("join-paths-unread", CN, (("        if [(c.get(\"path\"), c.get(\"kind\")) for c in got] != "
                                "[(c[\"path\"], c[\"kind\"]) for c in nat[\"changes\"]]:\n",
                                "        if [c.get(\"kind\") for c in got] != [c[\"kind\"] for c in nat[\"changes\"]]:\n"),),
     "join-refusal"),
    ("join-wiring-dropped", CN, (("    join_file_changes(turn, call)\n", ""),), "join-refusal"),
    ("declined-not-failed", CN, (('EXEC_FILE_CHANGE_STATUS = {"completed": "completed", "failed": "failed", '
                                  '"declined": "failed"}',
                                  'EXEC_FILE_CHANGE_STATUS = {"completed": "completed", "failed": "failed", '
                                  '"declined": "declined"}'),), "join"),
    ("path-keys-kept-as-keys", CT, (('            fc = dict(item, changes=[{"path": p, **c} for p, c in '
                                     'item["changes"].items()])\n',
                                     "            fc = dict(item)\n"),), "reach"),
    ("filechange-not-in-reach", CT, (('        if isinstance(item, dict) and item.get("type") == "FileChange":\n',
                                      "        if False:\n"),), "reach"),
    ("reader-not-handed-in", CT, (('        return vendor_pending("codex", "T-8:file-change", '
                                   'vendor_file_change_reads, path)\n',
                                   '        return vendor_pending("codex", "T-8:file-change", None)\n'),),
     "site"),
    ("rename-hold-dropped", CT, (("                    if c[\"move_path\"] is not None:\n",
                                  "                    if False:\n"),), "reader"),
]
CHECKS = {"unpaired": (TC, unpaired_problems), "paired": (TC, paired_problems), "reset": (TC, reset_problems),
          "changed": (TC, changed_changes_problems), "second-start": (TC, second_start_problems),
          "project": (CN, project_problems), "shape": (CN, shape_problems), "join": (CN, join_problems),
          "join-refusal": (CN, join_refusal_problems), "reach": (CT, reach_problems), "site": (CT, site_problems),
          "reader": (CT, reader_problems)}


def witnesses() -> list:
    """Each mutant applied alone: (name, its check, red?, every check of its module it turns red)."""
    import mutation_baseline  # lane t104-mutation-baseline: the unmutated selection runs first; a red one refuses (exit 3), nothing counted
    def unmutated():
        mods = {rel: mutant(rel, ()) for rel in sorted({crel for crel, _ in CHECKS.values()})}
        return [f"{c}: {x}" for c, (crel, fn) in CHECKS.items() for x in fn(mods[crel])]
    mutation_baseline.require_clean("test_codex_patch_reads witnesses", unmutated)
    out = []
    for name, rel, edits, check in MUTANTS:
        mod = mutant(rel, edits)
        reds = []
        for c, (crel, fn) in CHECKS.items():
            if crel == rel:
                try:
                    bad = fn(mod)
                except Exception as e:  # noqa: BLE001 - a traceback on a mutant is a red check
                    bad = [f"raised {type(e).__name__}: {e}"]
                if bad:
                    reds.append(c)
        out.append((name, check, check in reds, reds))
    return out


# ---------------------------------------------------------------------------------------------------------- WALKS
def walk_problems(clone: str) -> tuple:
    import test_codex_started_file_change as b22
    b22.BASE = BASE                      # B22's reading, now against B22's own head
    return b22.walk_problems(clone)


# ------------------------------------------------------------------------------------------------------ UNCHANGED
def dump(study: str) -> str:
    """The readings of the committed vendor fixtures, read by the modules of `study` (a gap-study-4 folder); the
    fixtures are this tree's. Printed as one JSON document."""
    path, modules = list(sys.path), dict(sys.modules)                  # B23-7: restored exactly, in place
    try:
        return _dump(study)
    finally:
        sys.path[:] = path
        for name in [m for m in sys.modules if m not in modules]:
            del sys.modules[name]
        sys.modules.update(modules)


def _dump(study: str) -> str:
    sys.path.insert(0, study)
    for m in ("check_take", "codex_native", "transcript_codex", "transcript_view", "vendor_record_binding"):
        sys.modules.pop(m, None)
    import check_take as ct
    import transcript_codex as tc
    import transcript_view as tv
    assert Path(ct.__file__).resolve().parent == Path(study).resolve(), ct.__file__
    out = {}
    fixtures = HERE / "tests" / "fixtures"
    for harness, folder in (("codex", "vendor-check-codex"), ("gemini", "vendor-check-gemini")):
        path = fixtures / folder / "transcript.jsonl"
        view = ct.vendor_take_view(path, harness)
        out[harness] = {
            "view": [list(map(repr, (e.turn, e.kind, e.text, e.tool, e.args, e.call))) for e in view["events"] or []],
            "view_problems": view["problems"],
            "raw": repr(ct.vendor_raw_records(path, harness)),
            "reach": repr({k: v for k, v in ct.vendor_reach(path, harness).items()}),
            "file_change": ct.vendor_file_change_problems(path, harness)}
    for f in sorted((fixtures / "codex-streams").glob("*.jsonl")):
        lines = tv.jsonl_lines(f.read_text(encoding="utf-8"))
        try:
            parser = tc.CodexParser()
            got = [repr(it) for line in lines for it in parser.items(line)]
            with mock.patch.dict(tv.PARSERS, {"codex": tc.CodexParser()}):
                evs = [repr((e.turn, e.kind, e.text, e.tool, e.args, e.call)) for e in tv.events("codex", lines)]
            out[f"codex-streams/{f.name}"] = {"items": got, "view": evs}
        except Exception as e:  # noqa: BLE001 - a refusal is a reading too
            out[f"codex-streams/{f.name}"] = f"refused: {type(e).__name__}: {e}"
    return json.dumps(out, sort_keys=True)


def unchanged_problems() -> tuple:
    with tempfile.TemporaryDirectory() as tmp:
        # the study folder and what check_take imports from evals/ (its REPO / "evals" path entry)
        archive = subprocess.run(["git", "-C", str(REPO), "archive", BASE, "evals/gap-study-4", ":(glob)evals/*.py",
                                  "evals/graders"], capture_output=True, check=True).stdout
        subprocess.run(["tar", "-x", "-C", tmp], input=archive, check=True)
        readings = []
        for study in (str(Path(tmp) / "evals" / "gap-study-4"), str(HERE)):
            got = subprocess.run([sys.executable, "-B", "-W", "ignore", __file__, "--dump", study],
                                 capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
            if got.returncode != 0:
                return [f"--dump {study} failed: {got.stderr.strip()[-300:]}"], None
            readings.append(got.stdout)
    digest = hashlib.sha256(readings[1].encode()).hexdigest()
    return ([] if readings[0] == readings[1] else [f"the fixtures read differently on {BASE} and on this tree"]), digest


# ---------------------------------------------------------------------------------------------------------- tests
class V1Unpaired(unittest.TestCase):
    def test_a_cut_patch_is_an_unanswered_edit_call(self):
        self.assertEqual(unpaired_problems(), [])


class V2Paired(unittest.TestCase):
    def test_w_o38_and_completed_only_read_as_on_a76b4dd2(self):
        self.assertEqual(paired_problems(), [])


class V3Reset(unittest.TestCase):
    def test_each_stream_starts_its_ids_again(self):
        self.assertEqual(reset_problems(), [])


class V4Closed(unittest.TestCase):
    def test_changed_changes_refused(self):
        self.assertEqual(changed_changes_problems(), [])

    def test_a_second_start_refused(self):
        self.assertEqual(second_start_problems(), [])


class N1Project(unittest.TestCase):
    def test_a_file_change_is_projected(self):
        self.assertEqual(project_problems(), [])


class N2Shape(unittest.TestCase):
    def test_off_shape_file_changes_refused(self):
        self.assertEqual(shape_problems(), [])


class N3Join(unittest.TestCase):
    def test_a_patch_joins(self):
        self.assertEqual(join_problems(), [])

    def test_a_disagreeing_patch_refuses(self):
        self.assertEqual(join_refusal_problems(), [])


class K1Reach(unittest.TestCase):
    def test_the_file_change_is_read_by_reach(self):
        self.assertEqual(reach_problems(), [])


class K2Site(unittest.TestCase):
    def test_the_site_hands_in_the_reader_and_pending_reads_as_before(self):
        self.assertEqual(site_problems(), [])


class K3Reader(unittest.TestCase):
    def test_the_reader_once_settled(self):
        self.assertEqual(reader_problems(), [])


class Mutants(unittest.TestCase):
    def test_every_mutant_is_red_alone(self):
        got = witnesses()
        self.assertEqual(len(got), len(MUTANTS))
        self.assertEqual([(n, c, reds) for n, c, red, reds in got if not red], [])


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--dump":
        print(dump(sys.argv[2]))
        raise SystemExit(0)
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
    if sys.argv[1:] == ["--unchanged"]:
        problems, digest = unchanged_problems()
        for p in problems:
            print(f"PROBLEM {p}")
        print(f"unchanged: fixtures readings sha256 (this tree) {digest}; "
              f"{'identical on ' + BASE + ' and this tree' if not problems else 'DIFFER'}")
        raise SystemExit(1 if problems else 0)
    unittest.main(verbosity=2)
