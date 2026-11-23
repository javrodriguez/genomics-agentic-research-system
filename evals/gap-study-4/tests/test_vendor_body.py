#!/usr/bin/env python3
"""Lane vendor-admission T4 P2: the vendor check body (lane-reports/vendor-T4-PLAN.md v4, sections 1 and 9, ruled
READY by glitch-b5 on Sat 17 Oct 2026, on Javier's typed word "vendor-t4: yes"; round 9's rulings).

Every case is a synthetic take of test_checker_body's draft row (scope-read/trap/w3) made a codex row (arm O) or a
gemini row (arm G), its view built by the production check_take.design_view and vendor_view (P5), its folder written by
tests/vendor_check_fixtures.py from that row's own lines and replies (envelopes, ledger, turn streams, launch
journals, retained native snapshots), and read by check_take.vendor_check (plan section 1a) and
check_take.vendor_round4_problems (section 1b).

  P2-clean    a clean take of either vendor carries exactly the PENDING refusals of its harness's
              VENDOR_PENDING_ROWS keys (every key but codex T-8:file-change, which fires only on a file_change item),
              each raised through vendor_pending: no vendor take passes while a PENDING row stands. Lane vendor-settle
              stage V (S6): every row is settled, so a clean take, whose folder now carries the CLI-written context
              records the settled readers read (vendor_check_fixtures: codex_context, gemini_session_context, the
              design's pinned CLAUDE.md as the instruction file), carries none; the PENDING road is read on TEST DATA,
              the module's map with rows put back to PENDING (pending_rows; the event-id witness and each site's
              deletion). Where a settled reader also reads a case's defect, the case's want names it per harness.
              Stage W ruling 3: gemini's stop reading and marker reading read one joined view (a held marker the
              CLI streamed across two delta chunks reads held in both; witness: the stop read unjoined).
  P2-cases    one F3 case per reason, each adding exactly its reason(s) to the clean take's refusals: the CLI's own
              user record differing from the envelopes, or holding an extra turn (readers-disagree; a differing gemini
              stream reads readers-disagree, never transcript-unreadable); no agent output; no CLI session id; a
              script that is a reference; a stop with no wait point, a stop at a held marker, a line off the script,
              a reply missing its marker; the fixture hash and the source; a leak word; a launch argv the adapter never
              writes, a missing launch journal and one naming another turn's stream (inherited-context); the ledger's
              sent line differing, and a last snapshot the ledger does not bind; the email marker in a published file (one
              event for any number of hits), and a session file the ledger does not name, with the marker or without
              (transcript-unreadable by name, never a count of 0; review c-6302fd3 NIT 2), and a ledger-named snapshot
              missing (transcript-unreadable by name, never a count of 0; review d-7c774ad finding 1); a turn that did
              not end, an outcome off the driver's shapes and a ledger
              row off the script (outcome-binding); reach into evals/, the home folder and the temp folder, and a path
              under the session's own run tree admitted; the project name; the ledger row, the commit-derived and the
              walk session id; the turn budget; a turn stream line no parser read; a nested-agent switch; codex's
              session working directory and run tree (T-11, T-4) and a file_change item (T-8, PENDING); P5's
              model-binding (T-15: a rollout turn on another model and a reroute for codex, a stream's init and a
              stats.models key on another model for gemini, no requested model; review e-71a2b94 finding 3, the take
              road binding the pre-registered row's model: the row on one model and the ledger and the CLI on another,
              while a walk never reads the row) and environment record (T-17: none, and one edited after the take),
              every take carrying the drive's environment.json, and the rig's ledger row the take's own vendor row.
  P2-keys     VP-keys holds as equality on the live source (test_vendor_check), and vendor_pending is called with
              literal harness and key only.
  P2-witness  check_take.py compiled in memory with each guard dropped, each PENDING refusal deleted (one mutant per
              call site, read from the AST), a PENDING refusal moved under an event id, the envelope read twice, the
              view run before the readers, the run tree not handed to the reach, the home and temp legs dropped, the
              email counted per instance, a model mismatch admitted, the codex reroute unread, the model reading
              dropped, the ledger-only model binding restored on the take road and the environment record unread:
              each goes red on its own case.

Fakes and synthetic strings only, inside test_checker_body's process guard (only the pinned tree's read-only git
starts): no take, model, vendor, network, Docker, credential or holdout.
"""

from __future__ import annotations

import ast
import collections
import contextlib
import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TESTS = Path(__file__).resolve().parent
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))

import test_checker_body as tcb  # noqa: E402
import vendor_check_fixtures as vcf  # noqa: E402

TASK, HALF = tcb.TASK, tcb.HALF
# harness: (model, arm, the pin's permission mode: the adapter's MODE_FLAGS key) - TEST DATA, D8's arms and ids
VENDORS = {"codex": ("gpt-6.1-sol", "O", "bypass"), "gemini": ("gemini-3.8-flash", "G", "yolo")}
WALK_ID = "w-0001"
# The home folder the checker reads every case under: outside the temp roots (tcb's scratch sits under the temp folder),
# so the home and temp legs each fire alone.
HOME = "/synthetic-home"
NO_READER = "no vendor reader yet"


def setUpModule():
    tcb.setUpModule()


def tearDownModule():
    tcb.tearDownModule()


def plain_design_for(mod, harness, run_tree=tcb.RUN_TREE):
    """design_view's Design of the draft row made a `harness` row (test_vendor_script's road)."""
    model, arm, mode = VENDORS[harness]
    r = tcb.row()
    r["agent"]["harness"], r["model"], r["arm"] = harness, model, arm
    return mod.design_view(r, pin=tcb.pin(mode, harness, model), run_tree=run_tree, constants=tcb.walk_constants(mod))


def design_for(mod, harness, run_tree=tcb.RUN_TREE):
    """The production design a vendor take is read through: design_view's Design in its vendor view (T4 P5, glitch-b5
    round 13: check4_vendor reads only a vendor view; checker_view builds it in production)."""
    return mod.vendor_view(plain_design_for(mod, harness, run_tree))


# T4 P5: the version drive._environment and the ledger record for the take (TEST DATA, the fixtures' CLI versions)
VERSIONS = {"codex": vcf.CODEX_CLI, "gemini": vcf.GEMINI_CLI}


def environment_record(t, turns) -> dict:
    """environment.json as drive._environment writes it for a vendor take (drive.environment_record, round 3's schema)
    under the design's environment_record block: no name of the block's vocabulary in the vendor's child
    environment, every listed name absent, and no credential source reported on any turn; the walk road's record
    names no row."""
    spec = t.design.pre["environment_record"]
    walk = t.call["walk_id"] is not None
    return {"record": "environment", "schema": spec["schema"], "session_id": t.sid, "row": None if walk else 0,
            "row_commit": None if walk else tcb.COMMIT, "task": TASK, "half": HALF, "model_requested": t.model,
            "claude_version": VERSIONS[t.harness], "written_before_first_turn": True,
            "name_patterns": spec["name_patterns"], "names_present": [], "stripped_names": [],
            "api_key_variables": dict.fromkeys(spec["api_key_variables"], "absent"), "api_key_set": False,
            "billing_route_variables": dict.fromkeys(spec["billing_route_variables"], "absent"),
            "billing_route_set": False,
            "subscription_token_variables": dict.fromkeys(spec["subscription_token_variables"], "absent"),
            "credential_source": {"key": spec["credential_source_key"], "reported": None,
                                  "per_turn": [{"n": r["n"], "recovery": False, "exit": 0, "apiKeySource": None}
                                               for r in turns]}}


class Take:
    """One synthetic vendor take of the row, before it is written: a case edits these fields, then its parts, then
    its folder. `call` holds vendor_check's keywords a case may change (row_index, walk_id, wording_script)."""

    def __init__(self, mod, harness, design, sid=None):
        self.mod, self.harness, self.design = mod, harness, design
        self.model, self.arm, self.mode = VENDORS[harness]
        self.sid = sid or tcb.sid()
        self.run_tree = design.run_tree
        self.journal_cwd = design.run_tree
        project = mod.neutral_name(self.sid)
        source = design.source(project)
        self.lines = [mod.render(s["line"], project, source) for s in design.script]
        self.replies = [f"Synthetic reply. {s.get('marker') or 'Here is what the file says.'}" for s in design.script]
        fixture = design.spec[HALF]["fixture"]
        self.ledger = {"outcome": "complete", "budget_s": 900, "permission_mode": self.mode, "finalize_wait_s": 180,
                       "poll_s": 3, "gars_tree_sha": mod.GARS_TREE_SHA, "arm": self.arm, "source": source,
                       "fixture": {"sha256": fixture["sha256"]}, "task": TASK, "half": HALF,
                       "model_requested": self.model, "session_id": self.sid}
        self.turns = None                  # None: one ledger row per line, numbered by the script's steps
        self.call = {"row_index": 0, "walk_id": None, "wording_script": design.script}
        self.parts = None
        self.row_model = self.model        # the pre-registered row's model (review e-71a2b94 finding 3)

    def build(self, parts_edit=None, folder_edit=None):
        # lane vendor-settle stage V (S6): the CLI's context records carry the design's pinned CLAUDE.md as the
        # instruction file (R-6), so the settled T-14 readers read a clean take clean
        text = self.design.instructions.get("CLAUDE.md", vcf.INSTRUCTIONS)
        if self.harness == "codex":
            self.parts = vcf.codex_parts(self.lines, self.replies, cwd=self.run_tree, model=self.model,
                                         instructions=text)
        else:
            self.parts = vcf.gemini_parts(self.lines, self.replies, model=self.model, run_tree=self.run_tree,
                                          instructions=text)
        if parts_edit:
            parts_edit(self.parts)
        turns = self.turns if self.turns is not None else [
            {"n": s["n"], "recovery": False, "exit": 0, "then": None, "sent": line}
            for s, line in zip(self.design.script, self.parts["lines"])]
        ledger = dict(self.ledger, turns=turns)
        env = environment_record(self, turns)                     # T4 P5: the drive's record, read by the checker
        raw = json.dumps(env).encode("utf-8")
        ledger.update(claude_version=VERSIONS[self.harness],
                      environment={"file": "environment.json", "sha256": hashlib.sha256(raw).hexdigest()})
        folder = Path(tempfile.mkdtemp(dir=tcb.SCRATCH))
        (folder / "environment.json").write_bytes(raw)
        path = vcf.write(folder, self.harness, self.parts, sid=self.sid, ledger=ledger, run_tree=self.journal_cwd,
                         mode=self.mode)
        if self.harness == "gemini":
            # glitch-f1's merge-5 ruling (a): mode_binding.argv_mode (lane freeze-gates-fix S10) rebuilds the registered
            # invocation from the box's launch.json take record (take_id, the take-inspect working folder), as the
            # box writes it; the synthetic take carries it, read from its own first launch journal
            first = json.loads((Path(path).parent / "turn-1.jsonl.launch.json").read_text(encoding="utf-8"))
            (Path(path).parent / "launch.json").write_text(json.dumps({"take_id": first["container_id"], "steps": [
                {"step": "take-inspect", "inspect": {"Config": {"WorkingDir": first["cwd"]}}}]}))
        if folder_edit:
            folder_edit(path)
        return path

    def vendor_row(self) -> dict:
        """The rig's ledger row 0 made this take's own vendor row (review e-71a2b94 finding 3: the rig's rows were
        Claude Code's): test_checker_body's draft row with the take's harness, arm and the row's model."""
        r = tcb.row()
        r["agent"]["harness"], r["model"], r["arm"] = self.harness, self.row_model, self.arm
        return r

    def own_rows(self):
        """takes.load_rows read as this take's ledger: its own vendor row alone, as row 0."""
        return mock.patch.object(self.mod.takes_mod, "load_rows", lambda **kw: [self.vendor_row()])

    def problems(self, path):
        with mock.patch.object(self.mod, "CHECK_HOME", Path(HOME)), self.own_rows():
            got = self.mod.vendor_check(path, TASK, HALF, self.call["row_index"],
                                        wording_script=self.call["wording_script"], design=self.design, arm=self.arm,
                                        walk_id=self.call["walk_id"])
            return got + self.mod.vendor_round4_problems(path, self.design)


def tags(problems) -> collections.Counter:
    return collections.Counter(p.split("] ")[0][1:] for p in problems)


def pending_lines(mod, harness) -> list:
    """The clean take's refusals: one per PENDING key of the harness, codex's file_change leg aside."""
    return sorted(f"[{row['reason']}] {NO_READER} ({key})" for key, row in mod.VENDOR_PENDING_ROWS[harness].items()
                  if key != "T-8:file-change" and row["state"] == mod.PENDING)


# ---- the F3 cases: (name, harnesses, edit(take) -> (parts_edit, folder_edit), the reasons it adds) -----------------
def _stream_records(parts, k):
    return parts["streams"][k]


def codex_rollout_user(parts, k, text):
    for t, pay in parts["rollout"][k]:
        if (pay.get("item") or {}).get("type") == "UserMessage":
            pay["item"]["content"][0]["text"] = text


def codex_extra_turn(parts):
    # lane vendor-settle stage V (S6): the extra turn repeats turn 1's records, never the CLI's context records
    # (written once, at the session's start) and carries the extra line in its user message too
    extra = [copy.deepcopy(x) for x in parts["rollout"][1]
             if x[0] != "world_state" and not (x[1].get("type") == "message" and x[1].get("role") in ("user", "developer")
                                               and x[1]["content"][0]["text"] != parts["lines"][0])]
    for t, pay in extra:
        for key in ("turn_id",):
            if pay.get(key) == "t1":
                pay[key] = "t9"
        if (pay.get("item") or {}).get("type") == "UserMessage":
            pay["item"]["content"][0]["text"] = "an extra line"
        if pay.get("type") == "message" and pay.get("role") == "user":
            pay["content"][0]["text"] = "an extra line"
    parts["rollout"][len(parts["rollout"])] += extra


def gemini_extra_interaction(parts):
    last = len(parts["native"])
    parts["native"][last] += [{"id": "u9", "type": "user", "content": [{"text": "an extra line"}]},
                              {"id": "b9", "type": "gemini", "model": parts["model"], "content": "Done."}]


def no_agent_output(parts):
    for k, recs in parts["streams"].items():
        keep = ("thread.started", "turn.started", "turn.completed", "init", "result")
        parts["streams"][k] = [r for r in recs if r["type"] in keep or (r["type"] == "message" and r["role"] == "user")]


def no_session_id(parts):
    for k, recs in parts["streams"].items():
        parts["streams"][k] = [r for r in recs if r["type"] not in ("thread.started", "init")]


def turn_not_ended(parts):
    last = parts["streams"][len(parts["streams"])]
    for r in last:
        if r["type"] == "turn.completed":
            r.clear()
            r.update({"type": "turn.failed", "error": {"message": "synthetic failure"}})
        elif r["type"] == "result":
            r.update(status="error", error={"type": "synthetic", "message": "synthetic failure"})


def tool_command(command):
    """Every tool call of turn 2 becomes a shell command `command` (codex command_execution; gemini
    run_shell_command)."""
    def edit(parts):
        for r in parts["streams"][2]:
            item = r.get("item") or {}
            if item.get("type") == "command_execution":
                item["command"] = command
            if r["type"] == "tool_use":
                r.update(tool_name="run_shell_command", parameters={"command": command})
        # lane pf1-l3 (fold plan prefreeze-1, MAJOR 7, 24 Oct 2026): the rollout records the argv the stream shows, as
        # the CLI writes both, so the take's records agree (check_take.vendor_content_problems)
        for _t, pay in parts.get("rollout", {}).get(2, []):
            item = pay.get("item") if isinstance(pay, dict) else None
            if pay.get("type") == "item_completed" and isinstance(item, dict) and item.get("type") == "CommandExecution":
                item["command"] = __import__("shlex").split(command)
    return edit


def extra_journal_option(path):
    j = path.parent / "turn-1.jsonl.launch.json"
    doc = json.loads(j.read_text())
    doc["argv"] = doc["argv"][:2] + ["--add-dir", "/elsewhere"] + doc["argv"][2:]
    j.write_text(json.dumps(doc))


def marker_in(where):
    note = __import__("scrub").NOTE

    def edit(parts):
        if "stream" in where:
            for r in parts["streams"][1]:
                if (r.get("item") or {}).get("type") == "agent_message":
                    r["item"]["text"] += f" {note}"
                # lane pf1-l3 (fold plan prefreeze-1, MAJOR 7, 24 Oct 2026): gemini's marker rides an assistant delta
                # chunk, the stream's alone, so the tool result output still equals its native display
                # (check_take.vendor_content_problems); before, it rode the tool result output
                if r["type"] == "message" and r.get("role") == "assistant" and r.get("delta") is True:
                    r["content"] += f" {note}"
                    break
        if "snapshot" in where:
            key = "rollout" if "rollout" in parts else "native"
            if key == "rollout":
                for t, pay in parts["rollout"][2]:
                    if pay.get("type") == "function_call_output":
                        pay["output"] += f" {note}"
            else:
                # lane pf1-l3: the native session's own copy of the result, which no stream shows (before: its display)
                parts["native"][2][1]["toolCalls"][0]["result"][0]["functionResponse"]["response"]["output"] += f" {note}"
    return edit


def file_change(parts):
    parts["streams"][2].insert(-1, {"type": "item.completed", "item": {
        "id": "item_7", "type": "file_change", "changes": [{"path": "notes.txt", "kind": "update"}],
        "status": "completed"}})


def stopped(t):
    t.ledger["outcome"] = "stopped \u2014 wait-point marker not held"


def case_user_record_differs(t):
    if t.harness == "codex":
        return lambda p: codex_rollout_user(p, 2, "other"), None
    return lambda p: p["streams"][2][1].update(content="other"), None


def case_ledger_sent_differs(t):
    t.turns = [{"n": s["n"], "recovery": False, "exit": 0, "then": None, "sent": line if s["n"] != 2 else "other"}
               for s, line in zip(t.design.script, t.lines)]
    return None, None


def case_snapshot_unbound(t):
    def edit(path):
        led = path.parent / "driver-ledger.json"
        doc = json.loads(led.read_text())
        doc["native_snapshots"][-1]["sha256"] = "0" * 64
        led.write_text(json.dumps(doc))
    return None, edit


def case_snapshot_differs(t):
    return lambda p: p["native"][2][0]["content"][0].update(text="other"), None


def case_extra_turn(t):
    return (codex_extra_turn if t.harness == "codex" else gemini_extra_interaction), None


def case_stop_no_wait_point(t):
    stopped(t)
    return None, None


def case_stop_held_marker(t):
    stopped(t)
    t.lines.pop()
    t.replies.pop()
    return None, None


def split_reply_marker(parts):
    """gemini: the last turn's reply streamed as two delta chunks, split inside its marker (as the CLI streamed w-g14,
    w-g31 and w-g39 turn 1); the snapshot keeps the whole reply."""
    recs = parts["streams"][max(parts["streams"])]
    k = max(i for i, r in enumerate(recs) if r.get("type") == "message" and r.get("role") == "assistant")
    text = recs[k]["content"]
    marker = text[len("Synthetic reply. "):]
    cut = len("Synthetic reply. ") + max(1, len(marker) // 2)
    recs[k:k + 1] = [dict(recs[k], content=text[:cut]), dict(recs[k], content=text[cut:])]


def split_reply_across_tool(parts, k=None):
    """gemini DECOY (Gemini review 0df1437 MINOR 1): turn k's reply (the last turn by default) written as two delta
    chunks with a tool call and its result between them, split inside the marker: two messages, never one, so the
    join must not make the marker whole."""
    k = max(parts["streams"]) if k is None else k
    recs = parts["streams"][k]
    i = max(j for j, r in enumerate(recs) if r.get("type") == "message" and r.get("role") == "assistant")
    text = recs[i]["content"]
    cut = len("Synthetic reply. ") + max(1, (len(text) - len("Synthetic reply. ")) // 2)
    ts = recs[i].get("timestamp")
    tool = [{"type": "tool_use", "timestamp": ts, "tool_name": "read_file", "tool_id": f"decoy-{k}",
             "parameters": {"file_path": "notes.txt"}},
            {"type": "tool_result", "timestamp": ts, "tool_id": f"decoy-{k}", "status": "success", "output": "x"}]
    recs[i:i + 1] = [dict(recs[i], content=text[:cut]), *tool, dict(recs[i], content=text[cut:])]


def case_marker_split_across_tool(t):
    return (lambda parts: split_reply_across_tool(parts, 1)), None        # turn 1's reply, a further line after it


def case_stop_marker_split_across_tool(t):
    stopped(t)
    t.lines.pop()
    t.replies.pop()
    return split_reply_across_tool, None


def case_stop_held_marker_split(t):
    # glitch-f1's stage W ruling 3: required_steps reads gemini's joined view, as continuation_problems does; read
    # unjoined, the held marker looks absent and the stop reads proven (the passing direction)
    stopped(t)
    t.lines.pop()
    t.replies.pop()
    return split_reply_marker, None


def case_reply_marker_split(t):
    # ruling (a) on a SYNTHETIC take: a held marker split across chunks adds no continued-past-unheld-marker line
    def edit(parts):
        for k in sorted(parts["streams"])[:-1]:                 # every reply followed by a further line
            split_reply_marker({"streams": {k: parts["streams"][k]}})
    return edit, None


def case_line_off_script(t):
    t.lines[1] = "06"
    return None, None


def case_reply_without_marker(t):
    t.replies[0] = "Synthetic reply."
    return None, None


def case_fixture_hash(t):
    t.ledger["fixture"] = {"sha256": "0" * 64}
    return None, None


def case_source(t):
    t.ledger["source"] = "/elsewhere/src"
    return None, None


def case_leak(t):
    t.design = t.design.replace(pre=dict(t.design.pre, leak_words=["bulk"]))
    return None, None


def case_no_journal(t):
    return None, lambda path: (path.parent / "turn-2.jsonl.launch.json").unlink()


def case_journal_of_another_turn(t):
    def edit(path):
        j = path.parent / "turn-2.jsonl.launch.json"
        j.write_text(json.dumps(dict(json.loads(j.read_text()), stream="/synthetic/take/turn-1.jsonl")))
    return None, edit


def case_outcome_off_shapes(t):
    t.ledger["outcome"] = "invented"
    return None, None


def case_row_off_script(t):
    t.turns = [{"n": n, "recovery": False, "exit": 0, "then": None, "sent": line}
               for n, line in zip((1, 2, 9), t.lines)]
    return None, None


def case_no_project(t):
    t.lines[0] = "I'd like to begin a bulk RNA-seq project"
    return None, None


def case_no_row(t):
    t.call["row_index"] = 7
    return None, None


def case_take_without_row(t):
    t.call["row_index"] = None
    return None, None


def case_unbound(t):
    return None, None                                  # the case's own session id does the work (CASES' sid)


def case_walk_session(t):
    t.call.update(row_index=None, walk_id=WALK_ID)
    return None, None


def case_budget(t):
    t.ledger["budget_s"] = 899
    return None, None


def case_unread_stream(t):
    return None, lambda path: (path.parent / "turn-9.jsonl").write_text('{"type": "x"}\n')


def case_rollout_cwd(t):
    def edit(parts):
        for _, pay in parts["rollout"][2]:
            if "cwd" in pay and "approval_policy" in pay:
                pay["cwd"] = "/elsewhere"
    return edit, None


def case_journal_cwd(t):
    t.journal_cwd = "/elsewhere"
    return None, None


def unnamed_session_file(marker: bool):
    """A file under session/ the ledger's native_snapshots does not name (review c-6302fd3 NIT 2): with the email
    marker in it, or without."""
    body = f'{{"note": "{__import__("scrub").NOTE}"}}\n' if marker else '{"note": "synthetic"}\n'
    return lambda path: (path.parent / "session" / "native-turn-9.jsonl").write_text(body)


def named_snapshot_missing(path):
    """A retained snapshot the ledger's native_snapshots names, deleted (review d-7c774ad finding 1): its bytes cannot
    be read, so the account-email count cannot be either."""
    (path.parent / "session" / "native-turn-1.jsonl").unlink()


# ---- T4 P5: model-binding (T-15) and the environment record (T-17) ---------------------------------------------------
OTHER_MODEL = "synthetic-other-model"                     # TEST DATA


def rollout_model(parts):
    for _, pay in parts["rollout"][2]:
        if "cwd" in pay and "approval_policy" in pay:
            pay["model"] = OTHER_MODEL


def rerouted(parts):
    """Turn 2's stream gains codex's reroute item away from the requested model (codex_native.REROUTE's sentence)."""
    item = {"id": "item_9", "type": "error",
            "message": f"model rerouted: {parts['model']} -> {OTHER_MODEL} (HighRiskCyberActivity)"}
    parts["streams"][2].insert(-1, {"type": "item.completed", "item": item})


def init_model(parts):
    for r in parts["streams"][2]:
        if r["type"] == "init":
            r["model"] = OTHER_MODEL


def stats_model(parts):
    for r in parts["streams"][2]:
        if r["type"] == "result":
            r["stats"]["models"][OTHER_MODEL] = dict(next(iter(r["stats"]["models"].values())))


def case_row_on_another_model(t):
    """The pre-registered row names another model; the ledger's requested model and every CLI record are the take's
    (review e-71a2b94 finding 3): the requested model differs from the row's, and the records are not the row's."""
    t.row_model = OTHER_MODEL
    return None, None


def case_no_requested_model(t):
    t.ledger.pop("model_requested")
    return None, None


def environment_edited(path):
    f = path.parent / "environment.json"
    f.write_bytes(f.read_bytes() + b"\n")


def edits(*pair):
    return lambda t: pair


# name: (harnesses, edit(take) -> (parts edit, folder edit), the reasons it adds, the take's session id or None)
CASES = {
    # readers-disagree, operator turns (T-3); a differing gemini stream reads readers-disagree, not unreadable
    "the CLI's user record differs from the envelopes": (("codex", "gemini"), case_user_record_differs,
                                                         {"readers-disagree": 1}, None),
    "the gemini snapshot's interaction differs from the envelopes": (("gemini",), case_snapshot_differs,
                                                                     {"readers-disagree": 1}, None),
    # lane vendor-settle stage V (S6): a per-harness want where a settled reader also reads the case's defect, each
    # extra line named: codex's extra turn is also an operator part of unknown origin (T-5) and a turn_context no
    # stream ran (T-16)
    # codex constant-binding 2: freeze-gates-fix S10's turn-stream count in codex_recorded_mode (glitch-f1
    # ruling 22 Oct, merge 5)
    "the CLI's record holds an extra turn": (("codex", "gemini"), case_extra_turn,
                                             {"codex": {"readers-disagree": 1, "unknown-harness-origin": 1,
                                                        "constant-binding": 2, "transcript-mismatch": 1},
                                              "gemini": {"readers-disagree": 1}},
                                             None),
    "the ledger's sent line differs from the envelopes": (("codex", "gemini"), case_ledger_sent_differs,
                                                          {"readers-disagree": 1}, None),
    # lane pf1-l3 (fold plan prefreeze-1, MAJOR 7, 24 Oct 2026): a case whose stream and native records disagree in
    # content now also adds [transcript-mismatch] (check_take.vendor_content_problems), and an unbound snapshot one
    # more [transcript-unreadable] (that reader refuses it too); the cases are kept as they are, their reasons added
    # the last retained snapshot the ledger does not bind: no reader of it stands (codex's cwd and run tree too; since
    # stage V every settled reader of the snapshot refuses it too, each under its row's reason for codex and as
    # transcript-unreadable for gemini; none passes)
    "a codex snapshot the ledger does not bind": (("codex",), case_snapshot_unbound,
                                                  # pf2 L-A1 review (MAJOR 3): the four codex sites of
                                                  # unknown-harness-origin, leak-in-loaded-context and checkout-binding
                                                  # name a snapshot the ledger does not bind driver-record-fault
                                                  {"transcript-unreadable": 3, "inherited-context": 5,
                                                   "driver-record-fault": 4,
                                                   "environment-record": 1,
                                                   "constant-binding": 3, "harness-condition-violated": 1}, None),
    "a gemini snapshot the ledger does not bind": (("gemini",), case_snapshot_unbound, {"transcript-unreadable": 11},
                                                   None),
    # no-first-agent-turn (T-1); the replies' markers go with the output
    "no agent output": (("codex", "gemini"), edits(no_agent_output, None),
                        {"codex": {"no-first-agent-turn": 1, "continued-past-unheld-marker": 2, "transcript-mismatch": 1},
                         "gemini": {"no-first-agent-turn": 1, "continued-past-unheld-marker": 2}}, None),
    # no-session-id (T-2): bound_items refuses a stream without one, so the view refuses too
    "the CLI wrote no session id": (("codex", "gemini"), edits(no_session_id, None),
                                    {"no-session-id": 1, "transcript-unreadable": 1}, None),
    # the stop and marker family, operator-lines (T-7, T-6)
    "a stop at a line with no wait point": (("codex", "gemini"), case_stop_no_wait_point,
                                            {"stop-without-a-wait-point": 1}, None),
    "a stop at a held marker": (("codex", "gemini"), case_stop_held_marker, {"stop-at-held-marker": 1}, None),
    # stage W ruling 3 and stage V ruling (a): a marker the CLI streamed across two delta chunks reads as held
    "a stop at a held marker split across delta chunks": (("gemini",), case_stop_held_marker_split,
                                                           {"stop-at-held-marker": 1}, None),
    "a held marker split across delta chunks before the next line": (("gemini",), case_reply_marker_split, {}, None),
    # Gemini review 0df1437 MINOR 1: DECOYS, a marker split across a tool call is two messages, never joined
    "a marker split across a tool call before the next line": (("gemini",), case_marker_split_across_tool,
                                                               {"continued-past-unheld-marker": 1,
                                                                "transcript-mismatch": 1}, None),
    "a stop marker split across a tool call": (("gemini",), case_stop_marker_split_across_tool,
                                               {"transcript-mismatch": 1}, None),   # the decoy is the stream's alone
    "an operator line off the script": (("codex", "gemini"), case_line_off_script, {"operator-lines": 2}, None),
    "a reply missing its step's marker": (("codex", "gemini"), case_reply_without_marker,
                                          {"continued-past-unheld-marker": 1}, None),
    # fixture-binding (T-24)
    "another fixture hash": (("codex", "gemini"), case_fixture_hash, {"fixture-binding": 1}, None),
    "another source": (("codex", "gemini"), case_source, {"fixture-binding": 1}, None),
    # leak-in-operator-turn (T-6)
    "a leak word in an operator line": (("codex", "gemini"), case_leak, {"leak-in-operator-turn": 1}, None),
    # inherited-context, the input-side legs (T-12:offered-context)
    # stage V: gemini's T-12:prompt-snapshot partial rebuilds the launch too; its T-12:offered-context and T-13
    # partials need one launch folder over every turn
    # gemini constant-binding 2: T-24's S10 registered-invocation reading, argv_mode (glitch-f1 ruling 22 Oct, merge 5)
    "a launch argv the adapter never writes": (("codex", "gemini"), edits(None, extra_journal_option),
                                              {"codex": {"inherited-context": 1},
                                               "gemini": {"inherited-context": 2, "constant-binding": 2}},
                                              None),
    "a turn with no launch journal": (("codex", "gemini"), case_no_journal,
                                      {"codex": {"inherited-context": 1},
                                       "gemini": {"inherited-context": 3, "driver-record-fault": 1,   # pf2 L-A1 review
                                                  "constant-binding": 1}}, None),
    # gemini constant-binding 1: T-24's S10 registered-invocation reading, argv_mode (glitch-f1 ruling 22 Oct, merge 5)
    "a launch journal naming another turn's stream": (("codex", "gemini"), case_journal_of_another_turn,
                                                      {"codex": {"inherited-context": 1},
                                                       "gemini": {"inherited-context": 1, "constant-binding": 1}},
                                                      None),
    # account-email (T-9): one event per take
    "the email marker in a turn stream": (("codex", "gemini"), edits(marker_in("stream"), None),
                                          {"account-email": 1}, None),
    "the email marker in two published files": (("codex", "gemini"), edits(marker_in("stream snapshot"), None),
                                                {"account-email": 1}, None),
    # round 12, review c-6302fd3 NIT 2: only the session files the ledger names are read; any other refuses by name
    "a session file the ledger does not name, carrying the marker": (("codex", "gemini"), edits(
        None, unnamed_session_file(True)), {"transcript-unreadable": 1}, None),
    "a session file the ledger does not name": (("codex", "gemini"), edits(None, unnamed_session_file(False)),
                                                {"transcript-unreadable": 1}, None),
    # round 13, review d-7c774ad finding 1: a ledger-named session file that cannot be read refuses by name
    "a ledger-named snapshot missing": (("codex", "gemini"), edits(None, named_snapshot_missing),
                                        {"transcript-unreadable": 1}, None),
    # T4 P5 (glitch-b5 round 13): model-binding (T-15) and the environment record (T-17)
    "a rollout turn on another model": (("codex",), edits(rollout_model, None), {"model-binding": 1}, None),
    # the view and the stream parser refuse the error item as off their tables; the model reading names the reroute
    "a rerouted model": (("codex",), edits(rerouted, None), {"model-binding": 1, "transcript-unreadable": 2}, None),
    "a stream's init on another model": (("gemini",), edits(init_model, None), {"model-binding": 1}, None),
    "a stats.models key of another model": (("gemini",), edits(stats_model, None), {"model-binding": 1}, None),
    # round 14, review e-71a2b94 finding 3: the take road binds the pre-registered row's model, never the ledger's alone
    "the pre-registered row on another model": (("codex", "gemini"), case_row_on_another_model, {"model-binding": 2},
                                                None),
    # stage V: the pinned config (codex T-18, since stage X codex T-12:memory's settings leg, since stage Z2 codex T-17's
    # forced_login_method leg) and settings (gemini
    # T-12:memory, T-17, T-18) are rebuilt for the ledger's model, so no model refuses them too; T-17's partial reads environment.json's named variables
    "no requested model in the ledger": (("codex", "gemini"), case_no_requested_model,
                                         {"codex": {"model-binding": 1, "environment-record": 2,
                                                    "harness-condition-violated": 1, "inherited-context": 1},
                                          # gemini constant-binding 1: T-24's S10 registered-invocation reading,
                                          # argv_mode (glitch-f1 ruling 22 Oct, merge 5)
                                          "gemini": {"model-binding": 1, "environment-record": 2,
                                                     "inherited-context": 1, "harness-condition-violated": 1,
                                                     "constant-binding": 1}}, None),
    "no environment record": (("codex", "gemini"), edits(None, lambda path: (path.parent / "environment.json").unlink()),
                              {"environment-record": 2}, None),
    "an environment record edited after the take": (("codex", "gemini"), edits(None, environment_edited),
                                                    {"environment-record": 1}, None),
    # outcome-binding (T-24)
    "a turn that did not end": (("codex", "gemini"), edits(turn_not_ended, None), {"outcome-binding": 1}, None),
    "an outcome off the driver's shapes": (("codex", "gemini"), case_outcome_off_shapes, {"outcome-binding": 1},
                                           None),
    "a ledger row off the script": (("codex", "gemini"), case_row_off_script, {"outcome-binding": 1}, None),
    # reach (T-8): the checkout, home and temp legs
    "a command reaching evals/": (("codex", "gemini"), edits(tool_command("cat evals/gap-study-4/prereg-draft.json"),
                                                             None), {"study-materials-reached": 1}, None),
    "a command reading the home folder": (("codex", "gemini"), lambda t: (tool_command(
        f"cat {HOME}/notes.txt"), None), {"read-outside-the-checkout": 1}, None),
    "a command reading the temp folder": (("codex", "gemini"), edits(tool_command("cat /tmp/other/notes.txt"), None),
                                          {"read-outside-the-checkout": 1}, None),
    # project-name (T-6): a first line without the project is off the script too
    "no operator line names the project": (("codex", "gemini"), case_no_project,
                                           {"project-name": 1, "operator-lines": 2}, None),
    # invocation and session-binding (T-24, and T-20's ledger leg)
    "no ledger row": (("codex", "gemini"), case_no_row, {"session-binding": 1}, None),
    "a take with no row": (("codex", "gemini"), case_take_without_row, {"invocation": 1}, None),
    "a session id that is not the row commit's": (("codex", "gemini"), case_unbound, {"session-binding": 1},
                                                  "other"),
    "a walk whose session id is not its walk's": (("codex", "gemini"), case_walk_session, {"session-binding": 2},
                                                  "other"),
    # constant-binding (T-24)
    "another turn budget": (("codex", "gemini"), case_budget, {"constant-binding": 1}, None),
    # transcript-unreadable (T-23): a stream in the folder no envelope binds, its line off the tables
    # stage V ruling (c): gemini's mode is read from every turn stream's launch journal (mode_binding.argv_mode walks
    # the folder's turn-N.jsonl), and the stray stream has none
    "a turn stream line no parser read": (("codex", "gemini"), case_unread_stream,
                                          # codex constant-binding 1: freeze-gates-fix S10's turn-stream count in
                                          # codex_recorded_mode (glitch-f1 ruling 22 Oct, merge 5)
                                          {"codex": {"transcript-unreadable": 1, "constant-binding": 1},
                                           "gemini": {"transcript-unreadable": 1, "constant-binding": 1}}, None),
    # nested-agent (T-21)
    "a nested agent's session switch": (("codex",), edits(tool_command("codex exec --ephemeral hi"), None),
                                        {"nested-agent-session": 1}, None),       # pre-freeze review 2, MAJOR 1
    "a nested agent's store moved": (("codex", "gemini"), edits(tool_command("CODEX_HOME=/x codex exec hi"), None),
                                     {"store-variable-assigned": 1}, None),       # pre-freeze review 2, MAJOR 1
    # codex: the session's working directory (T-11), the run tree (T-4), and file_change (T-8, PENDING)
    "a rollout turn in another working directory": (("codex",), case_rollout_cwd,
                                                    {"inherited-context": 1, "readers-disagree": 1}, None),
    "a launch journal in another working folder": (("codex",), case_journal_cwd, {"readers-disagree": 3}, None),
    "a file_change item": (("codex",), edits(file_change, None), {"transcript-unreadable": 1}, None),
}
SID_OTHER = "00000000-0000-5000-8000-0000000000aa"


def run_case(mod, harness, name, design=None):
    """The case's problems on `mod`, and the clean take's."""
    design = design or design_for(mod, harness)
    clean = Take(mod, harness, design)
    clean_problems = clean.problems(clean.build())
    t = Take(mod, harness, design, sid=SID_OTHER if CASES[name][3] == "other" else None)
    parts_edit, folder_edit = CASES[name][1](t)
    return t.problems(t.build(parts_edit, folder_edit)), clean_problems


def case_problems(mod, names=None) -> list:
    """[] or each case that does not add exactly its reasons to the clean take's refusals, nothing removed."""
    out = []
    for name, (harnesses, _, want, _sid) in CASES.items():
        if names is not None and name not in names:
            continue
        for harness in harnesses:
            try:
                got, clean = run_case(mod, harness, name)
            except Exception as e:  # noqa: BLE001 - a traceback is itself a failure here
                out.append(f"{harness} {name}: raised {type(e).__name__}: {e}")
                continue
            added = tags(got) - tags(clean)
            removed = collections.Counter(clean) - collections.Counter(got)
            mine = want[harness] if set(want) and set(want) <= set(VENDORS) else want   # per-harness (stage V)
            if added != collections.Counter(mine) or removed:
                out.append(f"{harness} {name}: added {dict(added)}, removed {dict(removed)}, not {mine}: "
                           f"{[p[:140] for p in got if p not in clean]}")
    return out


def clean_problems(mod) -> list:
    out = []
    for harness in VENDORS:
        try:
            t = Take(mod, harness, design_for(mod, harness))
            got = sorted(t.problems(t.build()))
        except Exception as e:  # noqa: BLE001
            out.append(f"{harness} clean take: raised {type(e).__name__}: {e}")
            continue
        if got != pending_lines(mod, harness):
            out.append(f"{harness} clean take: {got}, not the PENDING refusals {pending_lines(mod, harness)}")
    return out


def walk_problems(mod) -> list:
    """A clean walk (its session id walk_session_id(WALK_ID), no row) carries the PENDING refusals only."""
    out = []
    for harness in VENDORS:
        t = Take(mod, harness, design_for(mod, harness), sid=mod.walk_session_id(WALK_ID))
        t.ledger.update(row=None, row_commit=None)
        t.call.update(row_index=None, walk_id=WALK_ID)
        got = sorted(t.problems(t.build()))
        if got != pending_lines(mod, harness):
            out.append(f"{harness} clean walk: {got}")
    return out


def walk_row_problems(mod) -> list:
    """A clean walk whose ledger row 0 names another model carries the PENDING refusals only: the walk road binds the
    ledger's requested model and never reads a row (review e-71a2b94 finding 3)."""
    out = []
    for harness in VENDORS:
        t = Take(mod, harness, design_for(mod, harness), sid=mod.walk_session_id(WALK_ID))
        t.ledger.update(row=None, row_commit=None)
        t.call.update(row_index=None, walk_id=WALK_ID)
        t.row_model = OTHER_MODEL
        got = sorted(t.problems(t.build()))
        if got != pending_lines(mod, harness):
            out.append(f"{harness} clean walk beside a row on another model: {got}")
    return out


def tree_admitted_problems(mod) -> list:
    """codex: a path under the session's own run tree, the tree under the home folder, is admitted by the home leg."""
    tree = f"{HOME}/run-tree"
    design = design_for(mod, "codex", run_tree=tree)
    t = Take(mod, "codex", design)
    got = t.problems(t.build(tool_command(f"cat {tree}/notes.txt")))
    extra = [p for p in got if p not in pending_lines(mod, "codex")]
    return [f"codex run tree under home: {extra}"] if extra else []


def script_reference_problems(mod) -> list:
    out = []
    for harness in VENDORS:
        t = Take(mod, harness, design_for(mod, harness))
        t.call["wording_script"] = "see tasks/scope-read.json"
        got = t.problems(t.build())
        if "script-not-a-list" not in tags(got):
            out.append(f"{harness}: a script that is a reference is not script-not-a-list: {got}")
    return out


class P2Clean(unittest.TestCase):
    def test_p2_clean_take_carries_exactly_its_pending_refusals(self):
        self.assertEqual(clean_problems(tcb.ct), [])

    def test_p2_clean_walk_carries_exactly_its_pending_refusals(self):
        self.assertEqual(walk_problems(tcb.ct), [])

    def test_p2_a_walk_never_reads_the_rows_model(self):
        self.assertEqual(walk_row_problems(tcb.ct), [])

    def test_p2_a_claude_code_design_is_refused(self):
        with self.assertRaises(tcb.ct.CheckRefused):
            tcb.ct.vendor_check(Path(tcb.SCRATCH) / "transcript.jsonl", TASK, HALF, 0, wording_script=[],
                                design=tcb.view(tcb.ct), arm="A")


class P2Cases(unittest.TestCase):
    def test_p2_each_case_adds_exactly_its_reasons(self):
        self.assertEqual(case_problems(tcb.ct), [])

    def test_p2_a_path_under_the_sessions_own_run_tree_is_admitted(self):
        self.assertEqual(tree_admitted_problems(tcb.ct), [])

    def test_p2_a_script_reference_is_script_not_a_list(self):
        self.assertEqual(script_reference_problems(tcb.ct), [])


class P2Keys(unittest.TestCase):
    def test_p2_every_pending_key_has_its_call_site(self):
        import test_vendor_check as tvc
        self.assertEqual(tvc.vp_keys_problems(tvc.SOURCE, tcb.ct.VENDOR_PENDING_ROWS), [])


# ---- the witnesses --------------------------------------------------------------------------------------------------
# Lane vendor-settle stage V (S6): every row is settled, so the PENDING road is exercised on TEST DATA, the map with
# rows put back to PENDING in the module under test (its vendor_pending reads that module's map).
PENDING_MAP = "the clean takes on the map with every row PENDING"


@contextlib.contextmanager
def pending_rows(mod, keys=None):
    """mod.VENDOR_PENDING_ROWS with each (harness, key) of `keys` (every key when None) put back to PENDING."""
    rows = copy.deepcopy(mod.VENDOR_PENDING_ROWS)
    for h, block in rows.items():
        for k in block:
            if keys is None or (h, k) in keys:
                block[k] = {"reason": block[k]["reason"], "state": mod.PENDING}
    with mock.patch.object(mod, "VENDOR_PENDING_ROWS", rows):
        yield rows


def pending_call_sites(source: str) -> list:
    """The source text of every vendor_pending(<harness>, <key>, None) call, with its harness: one mutant each."""
    out = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "vendor_pending":
            out.append((node.args[0].value, ast.get_source_segment(source, node)))
    return out


P2_WITNESSES = {
    "the CLI's user records not compared": (("    for name, got in readers.items():\n", "    for name, got in ():\n"),
                                           "the CLI's user record differs from the envelopes"),
    "the ledger's sent lines not compared": (("    if rows != sent:\n", "    if False:\n"),
                                            "the ledger's sent line differs from the envelopes"),
    "the snapshot's ledger digest unchecked": ((
        '    raw = _binding._regular_bytes(Path(path).parent / "session" / name)\n'
        '    if hashlib.sha256(raw).hexdigest() != snaps[-1].get("sha256"):\n'
        '        raise VendorUnreadable(f"session/{name}: its bytes are not the ones the ledger binds")\n'
        '    return raw\n',
        '    return _binding._regular_bytes(Path(path).parent / "session" / name)\n'),
        "a codex snapshot the ledger does not bind"),
    "the envelope read twice": ((
        '            readers = {"the rollout\'s UserMessage items": [t["sent"] for t in '
        '_codex_native.read_rollout(raw)["turns"]]}\n',
        '            readers = {"the rollout\'s UserMessage items": list(sent)}\n'),
        "the CLI's user record differs from the envelopes"),
    "the view run before the readers": ((
        '    view = {"events": None, "problems": []} if problems else vendor_take_view(path, harness)\n',
        '    view = vendor_take_view(path, harness)\n'), "the CLI's user record differs from the envelopes"),
    "no-first-agent-turn dropped": (('        problems += vendor_first_turn_problems(view["events"])\n', "        pass\n"),
                                    "no agent output"),
    "no-session-id dropped": (("    problems += vendor_session_id_problems(path, harness)\n", ""),
                              "the CLI wrote no session id"),
    "the stop problems dropped": (("        problems += stop_problems\n", ""), "a stop at a held marker"),
    # stage W ruling 3: the stop reading on the unjoined view misses a held marker split across chunks
    "the stop read unjoined": ((
        "        required, stop_problems = required_steps(script, path, joined, False, expected_project, "
        "expected_source, ())\n",
        "        required, stop_problems = required_steps(script, path, turns, False, expected_project, "
        "expected_source, ())\n"), "a stop at a held marker split across delta chunks"),
    "the operator lines dropped": (("        problems += line_problems\n", ""), "an operator line off the script"),
    # stage V ruling (a): the call reads gemini's joined delta chunks (vendor_continuation_turns)
    "the continuation dropped": ((
        "            problems += continuation_problems(joined, required, [], expected_project, expected_source)\n",
        "            pass\n"),
        "a reply missing its step's marker"),
    "the fixture binding dropped": (("    problems += fixture_binding_problems(path, half, False)[0]\n", ""),
                                    "another fixture hash"),
    "the leak dropped": (("        problems += vendor_leak_problems(ops, pre)\n", "        pass\n"),
                         "a leak word in an operator line"),
    "the launch argv not rebuilt": (("        if argv != want:\n", "        if False:\n"),
                                    "a launch argv the adapter never writes"),
    "a missing launch journal admitted": ((
        '        if not (doc and doc.get("harness") == harness and isinstance(doc.get("stream"), str)\n',
        '        if False and not (doc and doc.get("harness") == harness and isinstance(doc.get("stream"), str)\n'),
        "a launch journal naming another turn's stream"),
    # the anchor moved with review d-7c774ad finding 1 (the bytes read through _binding._regular_bytes, NIT 1)
    "the email marker unread": (("        if marker in raw:\n", "        if False:\n"), "the email marker in a turn stream"),
    "the email counted per instance": ((
        "    for name in names:\n",
        "    hits = [n for n in names if (path.parent / n).is_file() and marker in (path.parent / n).read_bytes()]\n"
        "    if hits:\n        return [f'[{EVENT_EMAIL}] {n}' for n in hits]\n    for name in names:\n"),
        "the email marker in two published files"),
    "an unnamed session file admitted": (("        if rel not in named:\n", "        if False:\n"),
                                         "a session file the ledger does not name, carrying the marker"),
    "a ledger-named file skipped unread": ((
        '            return [f"[{TRANSCRIPT_UNREADABLE}] {name} is a published file of this take that cannot be read "\n'
        '                    f"({e}), so its bytes cannot be counted"]\n', "            continue\n"),
        "a ledger-named snapshot missing"),
    "model mismatch admitted": (("    others = [(where, m) for where, m in seen if m != want]\n", "    others = []\n"),
                                "a rollout turn on another model"),
    "the codex reroute unread": (("                if to is not None:\n", "                if False:\n"),
                                 "a rerouted model"),
    "the model reading dropped": (("    problems += vendor_model_problems(path, harness, ledger, row_index, walk_id)\n",
                                   ""), "a stream's init on another model"),
    "the ledger-only model binding restored on the take road": ((
        "        want = _vendor_row_model(row_index)\n", "        want = requested\n"),
        "the pre-registered row on another model"),
    "the environment record unread": (("        out = environment_problems(Path(path), ledger, pre, row_commit)\n",
                                       "        out = []\n"), "no environment record"),
    "the turn end unread": (("        if not ended:\n", "        if False:\n"), "a turn that did not end"),
    "the completion legs dropped": (("    problems += completion_problems(path, ledger, pre)\n", ""),
                                    "an outcome off the driver's shapes"),
    "the ledger rows unread": (("    problems += vendor_ledger_turn_problems(ledger, script, expected_source)\n", ""),
                               "a ledger row off the script"),
    "the reach dropped": (('        problems += vendor_reach(path, harness, run_tree=vendor_session_cwd(path, harness))'
                           '["problems"]\n', ""), "a command reaching evals/"),
    "the home leg dropped": (("        outside += outside_home_reads(Path(tmp), repo=repo)\n", ""),
                             "a command reading the home folder"),
    "the temp leg dropped": (("        outside += outside_temp_reads(Path(tmp))\n", ""),
                             "a command reading the temp folder"),
    "the project name dropped": (("        problems += vendor_project_problems(ops, expected_project)\n", ""),
                                 "no operator line names the project"),
    "the take binding dropped": (("        problems += vendor_take_binding_problems(task_id, half_name, row_index, sid)\n",
                                  "        pass\n"), "no ledger row"),
    "the walk binding dropped": ((
        "        problems += vendor_walk_binding_problems(path, task_id, half_name, walk_id, sid)\n", "        pass\n"),
        "a walk whose session id is not its walk's"),
    # stage V ruling (c): the vendor road's constants read the mode from the harness's own record
    "the constants dropped": (("    problems += vendor_constant_problems(path, harness, ledger, pre)   # budget, gars "
                               "tree; mode from its record (T-24)\n", ""), "another turn budget"),
    "the session cwd unchecked": (("    if vendor_session_cwd(path, harness) is None:\n", "    if False:\n"),
                                  "a rollout turn in another working directory"),
    "the rollout cwd unchecked": (("        if cwd != design.run_tree:\n", "        if False:\n"),
                                  "a rollout turn in another working directory"),
    "the journal cwd unchecked": (('        if doc is not None and doc.get("cwd") != design.run_tree:\n',
                                   "        if False:\n"), "a launch journal in another working folder"),
    "the unread lines admitted": (("    if bad and not (isinstance(outcome, str) and outcome.startswith((\"timed-out\", "
                                   "\"aborted\"))):\n", "    if False:\n"), "a turn stream line no parser read"),
    "the nested switches unread": ((
        "    return nested_command_problems(vendor_shell_commands(Path(path).parent, harness)[0], harness)\n",
        "    return []\n"), "a nested agent's session switch"),
    "file_change read as clean": (('        return vendor_pending("codex", "T-8:file-change", '
                                   'vendor_file_change_reads, path)\n',
                                   "        return []\n"), "a file_change item"),
    "a PENDING refusal under an event id": ((
        "        return [f\"[{row['reason']}] no vendor reader yet ({key})\"]\n",
        "        return [f\"[{EVENT_STUDY}] no vendor reader yet ({key})\"]\n"), PENDING_MAP),
}


def witness_red(mod, target) -> list:
    """The witness's own failures: its target case, or the clean takes when it names none, or (PENDING_MAP) the clean
    takes read with every row put back to PENDING."""
    if target is None:
        return clean_problems(mod)
    if target == PENDING_MAP:
        with pending_rows(mod):
            return clean_problems(mod)
    if target == "the run tree not handed to the reach":
        return tree_admitted_problems(mod)
    return case_problems(mod, {target})


class P2Witnesses(unittest.TestCase):
    def test_p2_witness_each_guard_dropped_goes_red(self):
        for name, (edit, target) in P2_WITNESSES.items():
            with self.subTest(witness=name):
                self.assertEqual(witness_red(tcb.ct, target), [], f"{name}: its case is red on check_take.py")
                self.assertNotEqual(witness_red(tcb.witness_module((edit,)), target), [], f"witness {name} stayed green")

    def test_p2_witness_the_run_tree_not_handed_to_the_reach(self):
        edit = ('        problems += vendor_reach(path, harness, run_tree=vendor_session_cwd(path, harness))["problems"]\n',
                '        problems += vendor_reach(path, harness)["problems"]\n')
        self.assertEqual(tree_admitted_problems(tcb.ct), [])
        self.assertNotEqual(tree_admitted_problems(tcb.witness_module((edit,))), [])

    def test_p2_witness_each_pending_refusal_deleted_goes_red(self):
        # stage V: each site's row put back to PENDING (TEST DATA) in the module under test; the clean take (the
        # file_change case for T-8) carries the row's refusal, and the site deleted loses it
        source = Path(tcb.ct.__file__).read_text(encoding="utf-8")
        sites = pending_call_sites(source)
        self.assertEqual(len(sites), sum(len(b) for b in tcb.ct.VENDOR_PENDING_ROWS.values()))
        for harness, text in sites:
            key = ast.parse(text).body[0].value.args[1].value
            with self.subTest(site=text):
                for mod in (tcb.ct, tcb.witness_module(((text, "[]"),))):
                    with pending_rows(mod, {(harness, key)}):
                        got = (case_problems(mod, {"a file_change item"}) if key == "T-8:file-change"
                               else clean_problems(mod))
                    if mod is tcb.ct:
                        self.assertEqual(got, [], f"{text}: the PENDING row's take is red on check_take.py")
                    else:
                        self.assertNotEqual(got, [], f"deleting {text} stayed green")


if __name__ == "__main__":
    unittest.main()
