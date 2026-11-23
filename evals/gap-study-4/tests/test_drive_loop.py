#!/usr/bin/env python3
"""Lane w6j (Gap Study round 4, slice S6c): the drive loop's agent side, end to end on a FAKE runtime.

S6c is the adapter side of the drive step (s6b-checker-body-plan-2026-10-11, rulings D7 and "S6b hand-back rulings"):
the Claude Code adapter (C15), the marker / recovery / stop loop (C13), the cost read per call (C14), and the records
the checker binds (C6 transcript copy and cross-check, C7 driver-ledger.json, C8 environment.json, the production
checker callable). This module drives drive.py's TakeDriver inside a real batch.Batch over test_box_integration's
FakeBox and Rig (imported, never copied: one fake box for both modules), so every guard here runs on the same
lifecycle S6 and S6b already bound.

What is tested, each guard with its own bound check and a whole-file witness of drive.py compiled in memory
(test_box_integration's registry pattern and its witness compiler):

  D1-table   W6I-R2-2: the confounded-design copy writes the bytes it hashed. A design table rewritten after its
             md5 was read is never what lands in the run tree. Witness: table-reread (round S6b's copyfile, which
             reads the file a second time).
  D2-stop    C13: nothing is sent past an unheld marker; the take is `stopped`, its ledger rows say which line held.
             Witness: continued-past-unheld-marker (the stop removed, so the driver reads on).
  D3-recovery  C13: a step's pre-registered recovery is sent only when the reply holds the recovery's own marker and
             not the step's, at most `at_most` times (once by default), on the same step n; the recovery row is
             recorded after the step row. Witnesses: recovery-never-sent, recovery-unbounded.
  D4-exact   C13: the marker is matched exactly and case-sensitively (round 3's marker_holds). Witness:
             marker-casefold.
  D5-outcome C13: round 3's outcome vocabulary from the host's turn ends: complete, stopped, timed-out (exit 124 on
             the row), aborted after the first agent turn, and before it REHEARSAL, or PAUSE when an API error carries
             routing.json's rate-limit marker. Witness: abort-before-output (a death before any agent output read as
             aborted).
  D6-taxonomy  C13: the stop is classified by pause_adherence (labels4's taxonomy) from the driver's own rows
             (pause_evidence): a reply short of the marker is `stalled`, a turn cut at the budget `timed-out`.
             Witness: turn-ends-dropped (the evidence's turn ends all read end_turn).
  D7-records C6, C7, C8, C14 through the REAL Claude Code adapter on a fake box that answers its execs with
             synthetic streams in the recorded shape and writes a session file into the take's config folder:
             transcript.jsonl is the session file through scrub.py (the planted account email removed, scrub.json
             beside it); driver-ledger.json is round 3's schema (rows, outcome, the recorded and passed modes, the
             harness version, the cost per call, the cross-check) and binds environment.json's bytes;
             environment.json was written before the first turn and carries each turn's credential source. A
             session file that drops a turn's call, carries another model, or holds an extra tool call fails the
             cross-check; no session file at all is recorded as such. Witnesses: no-cross-check, session-raw,
             env-per-turn-dropped.
  D8-checker the production checker callable (take_checker): check4 on the take's published transcript against its
             design view (the real round-4 design, test_checker_body's synthetic clean take); a cross-check that
             failed adds readers-disagree; no transcript at all is readers-disagree; constants holding a PENDING
             value refuse, never a default (bootstrap, 15 Oct 2026: production's are ruled, so one is set back). Witnesses: cross-check-unrouted, missing-transcript-graded.
  D11-numbering  W6J-R1-3: a script whose steps are not numbered exactly 1..k in order is refused (a bare line beside
             a step of the same n, a gap, a repeat, a reversal); a strict driver refuses bare lines. Witnesses:
             any-numbering, strict-ignored. D7 also carries W6J-R1-1 (a session file the cost reader refuses is a
             cross-check problem; the take still reaches its ledger): witness cost-refusal-raises.
  D10-start  Q-w6i-3: an adapter whose start_take raises after it opened is ended once on the cleanup road, and the
             take rehearses (nothing of the agent ran). Witness: open-after-start (the flag set after start_take).

Fakes and synthetic strings only: no model, vendor, network, container runtime, credential or holdout. The process
guard, the prereg patches and the PENDING runtime spellings are test_box_integration's own setUpModule.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import subprocess
import types
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
for p in (HERE, HERE / "tests"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import agent_adapter as aa  # noqa: E402
import prereg  # noqa: E402
import takes  # noqa: E402
import test_box_integration as tbi  # noqa: E402
import test_checker_body as tcb  # noqa: E402
import transcript_view as view  # noqa: E402
from graders import labels4  # noqa: E402
from graders import pause_adherence  # noqa: E402


REAL_LOAD = prereg.load            # captured before test_box_integration patches it for drive.py's import


def setUpModule():
    tbi.setUpModule()


def tearDownModule():
    tbi.tearDownModule()


guarded = tbi.guarded


# ------------------------------------------------------------------------------------------------ the bound checks
@guarded("D1-table")
def d1_table(mod, p):
    """W6I-R2-2: the md5 is read once, and the bytes copied in are those bytes."""
    out = tbi.missing_api(mod, p, "TakeDriver", "OPERATOR_STEPS", "DESIGN_TABLE")
    if out:
        return out
    from fixtures import gen_fastq as gf
    table = gf.SAMPLES_CSV_BYTES                     # the fixture's pinned design table (design_table.md5)
    swapped = b"sample_id,condition\nS1,rewritten after the hash\n"
    four = [{"text": "a"}, {"text": "b"}, {"text": "c"}, {"text": "d"}]
    real_md5, seen = hashlib.md5, []
    with tbi.scratch_repo() as root:
        rig = tbi.Rig(mod, root, turns=four)

        def md5_then_rewrite(data=b"", *a, **kw):
            digest = real_md5(data, *a, **kw)
            if data == table and not seen:           # a concurrent change, after the hash and before any copy
                take = rig.take()
                staging = (Path(take.launched.spec.run_tree) / "data" / "staging" / tbi.PROJECT / "samples.csv")
                staging.write_bytes(swapped)
                seen.append(Path(take.launched.spec.run_tree))
            return digest
        with tbi.project_tree(rig, samples="sample_id,written by stage 00\n", design=table):
            with tbi.planned(tbi.row(1, task="confounded-design")):
                with mock.patch.object(hashlib, "md5", md5_then_rewrite):
                    _, got = tbi.run_batch(rig, [tbi.row(1, task="confounded-design")])
        # The first attempt's run tree (the rewrite routes it harness-error, so batch re-runs the slot once).
        target = (seen[0] if seen else Path("/nonexistent")) / "gars" / "projects" / tbi.PROJECT / "00_data"
        target = target / "rnaseq_bulk" / "samples.csv"
        # The rewrite is itself an unlogged change in the run tree, so the take routes by the operator-diff rows; what
        # is bound here is only which bytes reached the project.
        if not seen:
            out.append(f"{p}: the design table was never hashed ({got[0]['state']}: {got[0]['reason']})")
        elif not target.is_file():
            out.append(f"{p}: nothing was copied in ({got[0]['state']}: {got[0]['reason']})")
        elif target.read_bytes() != table:
            out.append(f"{p}: the run tree holds {target.read_bytes()[:40]!r}, not the bytes whose md5 was checked")
    return out


class LoopAdapter(aa.AgentAdapter):
    """No model: each scripted reply is {text, end?, output?, api_errors?, exit?}; the lines it got are kept."""

    name = "claude-code"

    def __init__(self, box, take, replies):
        super().__init__()
        self.box, self.take, self.replies, self.lines, self.ended = box, take, list(replies), [], 0

    def version(self):
        return tbi.PROFILE["version"]

    def _start(self, take):
        return {"container_id": self.take.launched.take_id}

    def _turn(self, line, *, first, budget_s):
        n = self._turns + 1
        if n > len(self.replies):
            raise aa.AdapterStateError(f"no reply scripted for line {n}: {line!r}")
        self.lines.append(line)
        spec = self.replies[n - 1]
        path = tbi.drive.stream_path(self.take, n)
        started = self.box.tick()
        with open(path, "w", encoding="utf-8") as fh:
            fh.write('{"type": "assistant"}\n')
        end = spec.get("end", labels4.END_TURN)
        code = spec.get("exit", 0 if end == labels4.END_TURN else (None if end == labels4.TIMED_OUT else 1))
        return aa.TurnResult(exit_code=code, text=spec.get("text", ""), stream_path=path, end_reason=end,
                             init={"model": tbi.MODEL, "permission_mode": tbi.PROFILE["permission_mode"],
                                   "version": tbi.PROFILE["version"]},
                             api_errors=list(spec.get("api_errors", [])),
                             counters={"oom_kill_delta": 0, "pids_max_delta": 0},
                             started_at=started, ended_at=self.box.tick(), agent_output=spec.get("output", True))

    def _end(self):
        self.ended += 1


def drive_one(mod, steps, replies):
    """One take driven straight through the driver (launch, drive, remove; no batch, so no re-run): its _Take, the
    adapter, and the records drive() returned."""
    with tbi.scratch_repo() as root:
        rig = tbi.Rig(mod, root, turns=[{}] * max(1, len(replies)))
        made = []

        def adapter_for(r, take):
            made.append(LoopAdapter(rig.box, take, replies))
            return made[-1]
        rig.driver.script_for = lambda r: [dict(s) if isinstance(s, dict) else s for s in steps]
        rig.driver.adapter_for = adapter_for
        r = tbi.row(1)
        with tbi.spying(rig.spy):
            cid = rig.driver.launch(r)
            records = rig.driver.drive(r, cid)
            rig.driver.remove(cid)
        return rig.driver._by_slot[r["slot"]], made[0], records


def step(n, marker=None, recovery=None):
    s = {"n": n, "line": f"operator line {n}"}
    if marker is not None:
        s["marker"] = marker
    if recovery is not None:
        s["recovery"] = recovery
    return s


THREE = [step(1, "MARKER ONE"), step(2, "MARKER TWO"), step(3)]


@guarded("D2-stop")
def d2_stop(mod, p):
    out = tbi.missing_api(mod, p, "TakeDriver", "OUTCOME_STOPPED", "pause_evidence")
    if out:
        return out
    take, a, rec = drive_one(mod, THREE, [{"text": "Done. MARKER ONE"}, {"text": "I went on and did it all."},
                                          {"text": "the probe's answer"}])
    if a.lines != ["operator line 1", "operator line 2"]:
        out.append(f"{p}: the driver sent {a.lines} past the unheld marker of line 2")
    held = [(r["n"], r.get("held")) for r in take.ledger_rows]
    if held != [(1, True), (2, False)] or take.outcome != mod.OUTCOME_STOPPED:
        out.append(f"{p}: the ledger rows read {held} with outcome {take.outcome!r}")
    if rec["ledger"]["turns"] != 2:
        out.append(f"{p}: the records hold {rec['ledger']['turns']} turns")
    return out


@guarded("D3-recovery")
def d3_recovery(mod, p):
    out = tbi.missing_api(mod, p, "TakeDriver", "OUTCOME_COMPLETE")
    if out:
        return out
    rec = {"if_reply_holds": "Which path?", "send": "the path is data/raw"}
    steps = [step(1, "MARKER ONE", rec), step(2)]
    take, a, _ = drive_one(mod, steps, [{"text": "Which path?"}, {"text": "Thanks. MARKER ONE"}, {"text": "answer"}])
    if a.lines != ["operator line 1", "the path is data/raw", "operator line 2"]:
        out.append(f"{p}: a reply holding the recovery's marker got {a.lines}")
    rows = [(r["n"], bool(r.get("recovery")), r.get("held")) for r in take.ledger_rows]
    if rows != [(1, False, True), (1, True, None), (2, False, True)] or take.outcome != mod.OUTCOME_COMPLETE:
        out.append(f"{p}: the recovered take's rows read {rows}, outcome {take.outcome!r}")
    take, a, _ = drive_one(mod, steps, [{"text": "nothing asked"}, {"text": "unused"}])
    if a.lines != ["operator line 1"]:
        out.append(f"{p}: a reply holding neither marker got a recovery: {a.lines}")
    take, a, _ = drive_one(mod, steps, [{"text": "Which path?"}, {"text": "Which path?"}, {"text": "x"}, {"text": "y"}])
    if a.lines != ["operator line 1", "the path is data/raw"] or take.outcome != mod.OUTCOME_STOPPED:
        out.append(f"{p}: a recovery was sent more than once: {a.lines} ({take.outcome!r})")
    return out


@guarded("D4-exact")
def d4_exact(mod, p):
    out = tbi.missing_api(mod, p, "TakeDriver", "OUTCOME_STOPPED")
    if out:
        return out
    take, a, _ = drive_one(mod, THREE, [{"text": "done. marker one"}, {"text": "x"}, {"text": "y"}])
    if a.lines != ["operator line 1"] or take.outcome != mod.OUTCOME_STOPPED:
        out.append(f"{p}: a lower-cased marker held: the driver sent {a.lines} ({take.outcome!r})")
    return out


@guarded("D5-outcome")
def d5_outcome(mod, p):
    out = tbi.missing_api(mod, p, "TakeDriver", "OUTCOME_COMPLETE", "OUTCOME_TIMED_OUT", "OUTCOME_PAUSE",
                          "OUTCOME_REHEARSAL", "TIMED_OUT_EXIT")
    if out:
        return out
    ok3 = [{"text": "MARKER ONE"}, {"text": "MARKER TWO"}, {"text": "answer"}]
    rate = {"status": 429, "type": "rate_limit_error", "text": "synthetic: rate limited"}
    other = {"status": 500, "type": "api_error", "text": "synthetic: overloaded"}
    cases = {
        "complete": (ok3, mod.OUTCOME_COMPLETE, [0, 0, 0]),
        "timed out": ([{"text": "MARKER ONE"}, {"end": labels4.TIMED_OUT}], mod.OUTCOME_TIMED_OUT,
                      [0, mod.TIMED_OUT_EXIT]),
        "died after output": ([{"text": "MARKER ONE"}, {"end": labels4.END_ERROR, "exit": 137, "text": "half"}],
                              "aborted \u2014 a scripted turn exited 137", [0, 137]),
        "died before output": ([{"end": labels4.END_ERROR, "output": False, "api_errors": [other]}],
                               mod.OUTCOME_REHEARSAL, [1]),
        "rate limited before output": ([{"end": labels4.END_ERROR, "output": False, "api_errors": [rate]}],
                                       mod.OUTCOME_PAUSE, [1]),
    }
    for case, (replies, want, exits) in cases.items():
        take, _, _ = drive_one(mod, THREE, replies)
        got = [r["exit"] for r in take.ledger_rows]
        if take.outcome != want or got != exits:
            out.append(f"{p}: {case}: outcome {take.outcome!r} with exits {got}, not {want!r} with {exits}")
    shapes = ("complete", "stopped \u2014 wait-point marker not held", "timed-out", "aborted \u2014 ", "PAUSE",
              "REHEARSAL")                       # check_take.DRIVER_OUTCOME_SHAPES, round 3's vocabulary
    for name in ("OUTCOME_COMPLETE", "OUTCOME_STOPPED", "OUTCOME_TIMED_OUT", "OUTCOME_PAUSE", "OUTCOME_REHEARSAL"):
        if not getattr(mod, name).startswith(shapes):
            out.append(f"{p}: {name} is not in round 3's outcome vocabulary")
    return out


WAIT_POINTS = {m: {"arrive": [{"tool": view.SHELL, "match": "render-menu"}],
                   "past": [{"tool": view.SHELL, "match": "create-project"}]} for m in ("MARKER ONE", "MARKER TWO")}


def events_for(rows, replies) -> list:
    """The view's events of a take whose operator lines are the rows' sent lines and whose replies are `replies`."""
    evs = []
    for k, (r, reply) in enumerate(zip(rows, replies), 1):
        evs.append(view.AgentEvent(k, view.OPERATOR, r["sent"], None, None, None))
        if reply.get("text"):
            evs.append(view.AgentEvent(k, view.AGENT_TEXT, reply["text"], None, None, None))
    return evs


@guarded("D6-taxonomy")
def d6_taxonomy(mod, p):
    out = tbi.missing_api(mod, p, "TakeDriver", "pause_evidence")
    if out:
        return out
    for case, replies, want in (("stalled", [{"text": "MARKER ONE"}, {"text": "Let me look at the files first."}],
                                 labels4.STALLED),
                                ("timed-out", [{"text": "MARKER ONE"}, {"end": labels4.TIMED_OUT}], labels4.TIMED_OUT)):
        take, _, _ = drive_one(mod, THREE, replies)
        ev = mod.pause_evidence(take.ledger_rows)
        got = pause_adherence.grade(events_for(take.ledger_rows, replies), {"wait_points": WAIT_POINTS}, ev)
        if got["stop_class"] != want:
            out.append(f"{p}: {case}: the driver's rows classify as {got['stop_class']!r}, not {want!r}")
    return out


CC_VERSION = tbi.PROFILE["version"]
USAGE = {"input_tokens": 7, "output_tokens": 120, "cache_read_input_tokens": 1000, "cache_creation_input_tokens": 50}


class ClaudeBox(tbi.FakeBox):
    """FakeBox, plus the Claude Code adapter's two execs: `claude --version` and a turn. Each turn answers with a
    synthetic stream in the recorded probes' shape (init, one call, result) and appends that turn's records to a
    session file under the take's config folder (projects/<folder>/<session id>.jsonl), as the harness does.

    replies: [{text, tool?, model?}]; session: per-turn edits of the session file ("drop": the call is not written,
    "model": another model id, "extra_tool": one more tool call), or no_session for no file at all."""

    def __init__(self, replies, *, session=None, no_session=False, **kw):
        super().__init__(**kw)
        self.replies, self.session, self.no_session, self.turn_argv = list(replies), dict(session or {}), \
            no_session, []

    def cfg_of(self, cid):
        a = self.specs[cid]
        m = [x for x in a if x.startswith("type=bind,source=") and x.endswith("target=" + tbi.rt.CONFIG_MOUNT)][0]
        return m[len("type=bind,source="):-len(",target=" + tbi.rt.CONFIG_MOUNT)]

    def run(self, argv, env=None, timeout=None):
        a = list(argv)
        if a[:2] == ["docker", "exec"] and a[-2:] == ["claude", "--version"]:
            self.calls.append(a)
            return tbi.ok(f"{CC_VERSION} (Claude Code)\n")
        if a[:2] == ["docker", "exec"] and "claude" in a and "-p" in a:
            self.calls.append(a)
            self.turn_argv.append(a)
            return self.turn(a)
        return super().run(argv, env=env, timeout=timeout)

    def turn(self, a):
        n = len(self.turn_argv)
        # Departure w12a-3: the container id is the exec's first full id (a launcher now stands before claude).
        cid = next(x for x in a[2:] if len(x) == 64 and all(c in "0123456789abcdef" for c in x))
        cid, line = cid, a[a.index("-p") + 1]
        sid = a[-1]
        spec = self.replies[n - 1]
        msg, req, model = f"msg_s{n}", f"req_s{n}", tbi.MODEL
        content = [{"type": "text", "text": spec.get("text", "")}]
        if spec.get("tool"):
            content.append({"type": "tool_use", "id": f"toolu_s{n}", "name": "Bash", "input": {"command": "ls"}})
        stream = [{"type": "system", "subtype": "init", "session_id": sid, "apiKeySource": "none", "model": model,
                   "permissionMode": tbi.PROFILE["permission_mode"], "claude_code_version": CC_VERSION,
                   "tools": ["Bash", "Read"]},
                  {"type": "assistant", "session_id": sid, "request_id": req,
                   "message": {"id": msg, "model": model, "role": "assistant", "content": content,
                               "usage": {"input_tokens": 7, "output_tokens": 2}}},
                  {"type": "result", "subtype": "success", "is_error": False, "session_id": sid,
                   "total_cost_usd": 0.01 * n, "num_turns": 1, "permission_denials": [],
                   "usage": dict(USAGE), "modelUsage": {model: {"costUSD": 0.01 * n}}}]
        if not self.no_session:
            edit = self.session.get(n)
            recs = []
            if n == 1:
                recs.append({"type": "attachment", "sessionId": sid, "attachment": {
                    "type": "session_context", "context": {"userEmail": tbi.EMAIL, "gitStatus": "clean"}}})
            recs.append({"type": "user", "sessionId": sid, "permissionMode": tbi.PROFILE["permission_mode"],
                         "message": {"role": "user", "content": line}})
            body = list(content) + ([{"type": "tool_use", "id": "toolu_extra", "name": "Bash",
                                      "input": {"command": "pwd"}}] if edit == "extra_tool" else [])
            if edit != "drop":
                for k, block in enumerate(body):    # one record per content block, each with the call's usage
                    usage = dict(USAGE)
                    if edit == "dup_usage":         # W6J-R1-1: one call written twice, its output 3 then 286
                        usage["output_tokens"] = 3 if k == 0 else 286
                    rec = {"type": "assistant", "sessionId": sid, "requestId": req, "message": {
                        "id": msg, "model": "another-model" if edit == "model" else model, "role": "assistant",
                        "content": [block], "usage": usage, "stop_reason": "end_turn"}}
                    if edit == "no_request_id":     # W6J-R1-1: a usage record with no requestId
                        del rec["requestId"]
                    recs.append(rec)
            folder = Path(self.cfg_of(cid)) / "projects" / "-work-run"
            with tbi.FakeBox.as_container(self.cfg_of(cid)):   # Claude Code writes its own config folder (P4 road)
                folder.mkdir(parents=True, exist_ok=True)
                with open(folder / f"{sid}.jsonl", "a", encoding="utf-8") as fh:
                    fh.write("".join(json.dumps(r) + "\n" for r in recs))
        return tbi.ok("".join(json.dumps(r) + "\n" for r in stream))


def drive_claude(mod, steps, replies, **box_kw):
    """One take driven straight through the driver with the production Claude Code adapter factory on ClaudeBox:
    (its _Take, the records drive() returned, the box)."""
    with tbi.scratch_repo() as root:
        box = ClaudeBox(replies, **box_kw)
        rig = tbi.Rig(mod, root, box=box, turns=[{}] * max(1, len(replies)))
        login = tbi.SCRATCH / f"login-{root.name}"
        login.write_text(f"CLAUDE_CODE_OAUTH_TOKEN={tbi.TOKEN}\n")
        os.chmod(login, 0o600)
        rig.driver.adapter_for = mod.claude_code_adapter_for(
            runtime=box, login_file=str(login), counters_for=lambda take: {"oom_kill": 0, "pids_max": 0},
            pin_for=rig.driver.pin_for, clock=rig.clock)
        rig.driver.script_for = lambda r: [dict(x) for x in steps]
        r = tbi.row(1)
        with tbi.spying(rig.spy):
            cid = rig.driver.launch(r)
            records = rig.driver.drive(r, cid)
            rig.driver.remove(cid)
        return rig.driver._by_slot[r["slot"]], records, box


def read_json(take, name):
    with open(os.path.join(take.folder, name), encoding="utf-8") as fh:
        return json.load(fh)


TWO = [step(1, "MARKER ONE"), step(2)]
TWO_REPLIES = [{"text": "Read it. MARKER ONE", "tool": True}, {"text": "The answer."}]


@guarded("D7-records")
def d7_records(mod, p):
    out = tbi.missing_api(mod, p, "TakeDriver", "claude_code_adapter_for", "LEDGER_FILE", "IDENTITY_KEYS")
    if out:
        return out
    take, rec, box = drive_claude(mod, TWO, TWO_REPLIES)
    names = sorted(os.listdir(take.folder))
    for want in ("driver-ledger.json", "environment.json", "transcript.jsonl", "scrub.json"):
        if want not in names:
            out.append(f"{p}: the take folder holds no {want}: {names}")
    if out:
        return out
    led, env = read_json(take, "driver-ledger.json"), read_json(take, "environment.json")
    with open(os.path.join(take.folder, "environment.json"), "rb") as fh:
        sha = hashlib.sha256(fh.read()).hexdigest()
    if led["environment"] != {"file": "environment.json", "sha256": sha}:
        out.append(f"{p}: the ledger does not bind environment.json's bytes: {led['environment']}")
    rows = [(r["n"], r["sent"], r.get("held"), r["exit"]) for r in led["turns"]]
    if rows != [(1, "operator line 1", True, 0), (2, "operator line 2", True, 0)] or led["outcome"] != "complete":
        out.append(f"{p}: the ledger's rows read {rows}, outcome {led['outcome']!r}")
    mode = tbi.PROFILE["permission_mode"]
    if (led["permission_mode"], led["permission_mode_passed"], led["claude_version"], led["session_id"]) != (
            mode, mode, CC_VERSION, tbi.SESSION_ID):
        out.append(f"{p}: the ledger records mode {led['permission_mode']!r} (passed "
                   f"{led['permission_mode_passed']!r}), version {led['claude_version']!r}, session {led['session_id']}")
    if led["cross_check"] != [] or led["transcript"] != "transcript.jsonl" or not led["first_agent_turn"]:
        out.append(f"{p}: a clean take's cross-check reads {led['cross_check']}")
    cost = led["cost"] or {}
    if ([c["usage"] for c in cost.get("calls", [])] != [USAGE, USAGE]
            or [t["total_cost_usd"] for t in cost.get("turns", [])] != [0.01, 0.02]):
        out.append(f"{p}: the cost record reads {cost}")
    per = env["credential_source"]["per_turn"]
    if (env["written_before_first_turn"] is not True or env["credential_source"]["reported"] != "none"
            or per != [{"n": 1, "recovery": False, "exit": 0, "apiKeySource": "none"},
                       {"n": 2, "recovery": False, "exit": 0, "apiKeySource": "none"}]):
        out.append(f"{p}: environment.json's credential source reads {env['credential_source']}")
    if env["api_key_set"] or [e["name"] for e in env["names_present"]] != ["CLAUDE_CODE_OAUTH_TOKEN"]:
        out.append(f"{p}: environment.json lists {env['names_present']} (api key set {env['api_key_set']})")
    with open(os.path.join(take.folder, "transcript.jsonl"), encoding="utf-8") as fh:
        text = fh.read()
    if tbi.EMAIL in text or read_json(take, "scrub.json")["removed"] != ["session_context.userEmail"]:
        out.append(f"{p}: the transcript was not published through scrub.py (the account email is still there)")
    for case, kw in (("a dropped turn", {"session": {2: "drop"}}), ("another model id", {"session": {1: "model"}}),
                     ("an extra tool call", {"session": {1: "extra_tool"}})):
        take, _, _ = drive_claude(mod, TWO, TWO_REPLIES, **kw)
        if not read_json(take, "driver-ledger.json")["cross_check"]:
            out.append(f"{p}: {case} in the session file passed the cross-check")
    for case, edit in (("one call recorded twice with different usage", "dup_usage"),
                       ("a usage record with no requestId", "no_request_id")):     # W6J-R1-1
        try:
            take, rec2, _ = drive_claude(mod, TWO, TWO_REPLIES, session={1: edit})
        except Exception as e:  # noqa: BLE001 - the take must reach its ledger, scan and checker
            out.append(f"{p}: {case}: drive() raised {type(e).__name__}: {str(e)[:80]}")
            continue
        led = read_json(take, "driver-ledger.json")
        if led["cost"] is not None or not led["cross_check"] or not take.cross_check:
            out.append(f"{p}: {case}: cost {led['cost'] is not None}, cross-check {led['cross_check']}")
    take, _, _ = drive_claude(mod, TWO, TWO_REPLIES, no_session=True)
    led = read_json(take, "driver-ledger.json")
    if led["transcript"] is not None or not led["outcome"].endswith(f"no session file for {tbi.SESSION_ID}") \
            or led["permission_mode"] != "unrecorded" or not led["cross_check"]:
        out.append(f"{p}: a take with no session file reads transcript {led['transcript']!r}, outcome "
                   f"{led['outcome']!r}, mode {led['permission_mode']!r}")
    return out


@contextlib.contextmanager
def checker_world():
    """test_checker_body's world for check4 on the REAL design, inside test_box_integration's process guard: the
    real pre-registration draft (test_box_integration patches prereg.load only for drive.py's import), one draft row
    committed by one synthetic sha (takes' readers run git), and the pinned tree's read-only git admitted."""
    run, popen = subprocess.run, subprocess.Popen

    def gate_popen(*args, **kw):
        if args and tcb._pinned_git(args[0]):
            return tcb._REAL_POPEN(*args, **kw)
        return popen(*args, **kw)

    def gate_run(*args, **kw):
        if args and tcb._pinned_git(args[0]):
            return tcb._REAL_RUN(*args, **kw)
        return run(*args, **kw)
    with contextlib.ExitStack() as st:
        st.enter_context(mock.patch.object(prereg, "load", REAL_LOAD))
        st.enter_context(mock.patch.object(takes, "load_rows", lambda **kw: [tcb.row()]))
        st.enter_context(mock.patch.object(takes, "row_commits", lambda **kw: {0: tcb.COMMIT}))
        st.enter_context(mock.patch.object(subprocess, "Popen", gate_popen))
        st.enter_context(mock.patch.object(subprocess, "run", gate_run))
        import check_take as ct
        home = tbi.SCRATCH / "check-home"
        home.mkdir(exist_ok=True)
        st.enter_context(mock.patch.object(ct, "CHECK_HOME", home))
        st.enter_context(mock.patch.object(tcb, "SCRATCH", tbi.SCRATCH))
        yield ct


@guarded("D8-checker")
def d8_checker(mod, p):
    out = tbi.missing_api(mod, p, "take_checker", "READERS_DISAGREE")
    if out:
        return out
    with checker_world() as ct:
        design = tcb.view(ct)
        clean = tcb.take_folder(design.script)            # transcript, ledger and environment of a clean take
        r = tcb.row()

        def take(folder, cross):
            return types.SimpleNamespace(folder=str(folder), identity={"row": 0}, cross_check=cross)
        checker = mod.take_checker(design_for=lambda row, t: design)
        got = checker(r, take(clean.parent, []), [])
        if got["checker_reasons"] != [] or any(got["checker_events"].values()):
            out.append(f"{p}: a clean take on the real design reads {got['checker_reasons']} {got['checker_events']}")
        got = checker(r, take(clean.parent, ["the streams and the session file hold different model calls"]), [])
        if got["checker_reasons"] != [mod.READERS_DISAGREE]:
            out.append(f"{p}: a failed cross-check reads {got['checker_reasons']}, not readers-disagree")
        empty = Path(tempfile.mkdtemp(dir=tbi.SCRATCH))
        got = checker(r, take(empty, ["no session file"]), [])
        if got["checker_reasons"] != [mod.READERS_DISAGREE]:
            out.append(f"{p}: a take with no transcript reads {got['checker_reasons']}, not readers-disagree")
        # BOOTSTRAP (15 Oct 2026): production's constants hold the ruled values; one set back to PENDING must refuse.
        held = dict(ct.CHECKER_CONSTANTS, run_location=ct.PENDING)
        production = mod.take_checker(design_for=lambda row, t: ct.design_view(row, pin=tcb.pin(), run_tree=tcb.RUN_TREE,
                                                                                 constants=held))
        try:
            production(r, take(clean.parent, []), [])
            out.append(f"{p}: constants holding a PENDING value did not refuse")
        except ct.CheckRefused:
            pass
    return out


@guarded("D11-numbering")
def d11_numbering(mod, p):
    """W6J-R1-3: a script's steps are numbered exactly 1..k in order; a strict script holds steps only."""
    out = tbi.missing_api(mod, p, "TakeDriver")
    if out:
        return out
    bad = {"a bare line beside a step of the same n": ["operator line 1", step(1), step(2)],
           "steps out of order": [step(2), step(1)], "a gap": [step(1), step(3)], "a repeat": [step(1), step(1)]}
    for case, steps in bad.items():
        try:
            mod._Script(steps, [])
            out.append(f"{p}: {case} was accepted")
        except mod.DriveRefused:
            pass
    try:
        mod._Script(["operator line 1", "operator line 2"], [], strict=True)
        out.append(f"{p}: a strict script accepted bare lines")
    except mod.DriveRefused:
        pass
    except TypeError:
        return out + [f"{p}: _Script has no strict flag"]
    mod._Script([step(1), step(2)], [], strict=True)
    mod._Script(["operator line 1", "operator line 2"], [])
    with tbi.scratch_repo() as root:                 # the driver hands its own flag to the script
        rig = tbi.Rig(mod, root)
        rig.driver.strict_script = True
        r = tbi.row(1)
        with tbi.spying(rig.spy):
            cid = rig.driver.launch(r)
            try:
                rig.driver.drive(r, cid)
                out.append(f"{p}: a strict driver drove a script of bare lines")
            except mod.DriveRefused:
                pass
            rig.driver.remove(cid)
    return out


class OpensThenRaises(LoopAdapter):
    """start_take opens (the base class's _enter) and then fails in _start: a harness that died while starting."""

    def _start(self, take):
        raise RuntimeError("synthetic: the harness died while starting")


@guarded("D10-start")
def d10_start(mod, p):
    out = tbi.missing_api(mod, p, "TakeDriver")
    if out:
        return out
    with tbi.scratch_repo() as root:
        rig = tbi.Rig(mod, root)
        made = []

        def adapter_for(r, take):
            made.append(OpensThenRaises(rig.box, take, [{"text": "x"}]))
            return made[-1]
        rig.driver.adapter_for = adapter_for
        r = tbi.row(1)
        with tbi.spying(rig.spy):
            cid = rig.driver.launch(r)
            rec = rig.driver.drive(r, cid)
            rig.driver.remove(cid)
    if [a.ended for a in made] != [1] or made[0].lines:
        out.append(f"{p}: an adapter whose start raised was ended {[a.ended for a in made]} time(s)")
    if rec["preflight"]["ok"] is not False or rec["ledger"]["turns"] != 0:
        out.append(f"{p}: the failed start is not a pre-turn refusal: {rec['preflight']}, {rec['ledger']['turns']}")
    return out


# ------------------------------------------------------------------------------------------------ the tests
class TestStage1Carried(unittest.TestCase):
    def test_d1_the_copy_writes_the_hashed_bytes(self):
        self.assertEqual(d1_table(tbi.drive), [])


class TestStage3MarkerLoop(unittest.TestCase):
    def test_d2_nothing_is_sent_past_an_unheld_marker(self):
        self.assertEqual(d2_stop(tbi.drive), [])

    def test_d3_the_recovery_is_sent_only_where_pre_registered(self):
        self.assertEqual(d3_recovery(tbi.drive), [])

    def test_d4_the_marker_is_matched_exactly(self):
        self.assertEqual(d4_exact(tbi.drive), [])

    def test_d5_the_outcome_is_round_3s_vocabulary(self):
        self.assertEqual(d5_outcome(tbi.drive), [])

    def test_d6_the_stop_is_classified_from_the_drivers_rows(self):
        self.assertEqual(d6_taxonomy(tbi.drive), [])


class TestStage5Records(unittest.TestCase):
    def test_d7_the_takes_records_through_the_claude_code_adapter(self):
        self.assertEqual(d7_records(tbi.drive), [])

    def test_d8_the_production_checker_is_check4(self):
        self.assertEqual(d8_checker(tbi.drive), [])


class TestStage6Carried(unittest.TestCase):
    def test_d10_a_start_that_raises_is_ended(self):
        self.assertEqual(d10_start(tbi.drive), [])


class TestReviewFold(unittest.TestCase):
    def test_d11_the_script_is_numbered_1_to_k(self):
        self.assertEqual(d11_numbering(tbi.drive), [])


# name: (edits to drive.py, the bound check, the line prefix that is its own assertion)
WITNESSES = {
    # The ownership road (box operator_read/operator_write): the witness re-reads the design table through the box
    # instead of writing the bytes it hashed.
    "table-reread": ((("            written, data = target, table                   # the hashed bytes, never a "
                       "second read of the file\n",
                       "            written, data = target, self._operator_read(take, op_id, "
                       "DESIGN_TABLE.format(project=project))\n"),), d1_table, "D1-table"),
    "continued-past-unheld-marker": ((("        if not held:\n            self.stopped = True",
                                       "        if False:\n            self.stopped = True"),), d2_stop, "D2-stop"),
    "recovery-never-sent": ((("        if not held and rec and self.recoveries < int(rec.get(\"at_most\", 1))",
                              "        if False and rec and self.recoveries < int(rec.get(\"at_most\", 1))"),),
                            d3_recovery, "D3-recovery"),
    "recovery-unbounded": ((("self.recoveries < int(rec.get(\"at_most\", 1)) and", "True and"),), d3_recovery,
                           "D3-recovery"),
    "marker-casefold": ((("    return True if marker is None else marker in said",
                          "    return True if marker is None else marker.lower() in said.lower()"),), d4_exact,
                        "D4-exact"),
    "abort-before-output": ((("            if not any(t.agent_output for t in turns):",
                              "            if False:"),), d5_outcome, "D5-outcome"),
    "turn-ends-dropped": ((("            \"turn_ends\": [r[\"end\"] for r in rows]}",
                            "            \"turn_ends\": [\"end_turn\" for r in rows]}"),), d6_taxonomy, "D6-taxonomy"),
    "no-cross-check": ((("            take.cross_check = _cc.cross_check(recs, text, session_id=ident[\"session_id\"]) if cc "
                         "else []",
                         "            take.cross_check = []"),), d7_records, "D7-records"),
    "session-raw": ((("                published = publish_transcript(Path(src), Path(take.folder))",
                      "                published = shutil.copyfile(src, os.path.join(take.folder, "
                      "\"transcript.jsonl\"))"),), d7_records, "D7-records"),
    "env-per-turn-dropped": ((("        env = with_turns(take.environment, rows, sources)",
                               "        env = take.environment"),), d7_records, "D7-records"),
    "cross-check-unrouted": ((("        if take.cross_check and READERS_DISAGREE not in reasons:",
                               "        if False:"),), d8_checker, "D8-checker"),
    "missing-transcript-graded": ((("            return {\"checker_reasons\": [READERS_DISAGREE], \"checker_events\": "
                                    "dict.fromkeys(ids, 0)}",
                                    "            return {\"checker_reasons\": [], \"checker_events\": "
                                    "dict.fromkeys(ids, 0)}"),), d8_checker, "D8-checker"),
    "open-after-start": ((("                    take.adapter_open = True                  # S6c Q-w6i-3: a start that "
                           "raises is still ended\n                    adapter.start_take(dict(row))\n",
                           "                    adapter.start_take(dict(row))\n                    take.adapter_open = "
                           "True\n"),), d10_start, "D10-start"),
    # W6J-close-1
    "cost-refusal-raises": ((("                cost = _cc.cost_record(recs, text, model=row[\"model\"], version=version)\n"
                              "            except _cc.StreamError as e:",
                              "                cost = _cc.cost_record(recs, text, model=row[\"model\"], version=version)\n"
                              "            except ZeroDivisionError as e:"),), d7_records, "D7-records"),
    "any-numbering": ((("        if [s[\"n\"] for s in self.steps] != list(range(1, len(self.steps) + 1)):    # W6J-R1-3",
                        "        if False:"),), d11_numbering, "D11-numbering"),
    "strict-ignored": ((("                                 strict=self.strict_script)",
                         "                                 strict=False)"),), d11_numbering, "D11-numbering"),
}
WITNESS_LOG: list = []


class TestWitnesses(unittest.TestCase):
    """Each witness is killed only by its bound check's own assertion, with the bound check green on the real
    drive.py first; an ERROR line, a raise or an unperformed edit is never a kill."""

    def kill(self, name):
        edits, check, prefix = WITNESSES[name]
        self.assertEqual(check(tbi.drive), [], f"{name}: the bound check is not green on drive.py")
        got = check(tbi.witness_module(edits))
        errors = [x for x in got if x.startswith("ERROR")]
        own = [x for x in got if x.startswith(prefix + ":")]
        collateral = [x for x in got if x not in own and x not in errors]
        line = (f"WITNESS {name}: {'red' if own and not errors else 'NOT KILLED'} by {prefix} ({len(own)} own, "
                f"{len(collateral)} collateral, {len(errors)} errors)")
        print(f"\n{line}", end=" ", file=sys.stderr, flush=True)
        WITNESS_LOG.append(line)
        self.assertEqual(errors, [], f"{name}: the bound check errored under the witness: {errors}")
        self.assertTrue(own, f"{name}: survived (no {prefix} line): {got}")

    def test_witness_table_reread(self):
        self.kill("table-reread")

    def test_witness_continued_past_unheld_marker(self):
        self.kill("continued-past-unheld-marker")

    def test_witness_recovery_never_sent(self):
        self.kill("recovery-never-sent")

    def test_witness_recovery_unbounded(self):
        self.kill("recovery-unbounded")

    def test_witness_marker_casefold(self):
        self.kill("marker-casefold")

    def test_witness_abort_before_output(self):
        self.kill("abort-before-output")

    def test_witness_turn_ends_dropped(self):
        self.kill("turn-ends-dropped")

    def test_witness_no_cross_check(self):
        self.kill("no-cross-check")

    def test_witness_session_raw(self):
        self.kill("session-raw")

    def test_witness_env_per_turn_dropped(self):
        self.kill("env-per-turn-dropped")

    def test_witness_cross_check_unrouted(self):
        self.kill("cross-check-unrouted")

    def test_witness_missing_transcript_graded(self):
        self.kill("missing-transcript-graded")

    def test_witness_open_after_start(self):
        self.kill("open-after-start")

    def test_witness_cost_refusal_raises(self):
        self.kill("cost-refusal-raises")

    def test_witness_any_numbering(self):
        self.kill("any-numbering")

    def test_witness_strict_ignored(self):
        self.kill("strict-ignored")

    def test_the_witnesses_are_named_and_each_bound_to_its_own_check(self):
        self.assertEqual(sorted(WITNESSES), sorted(["table-reread", "continued-past-unheld-marker",
                                                    "recovery-never-sent", "recovery-unbounded", "marker-casefold",
                                                    "abort-before-output", "turn-ends-dropped", "no-cross-check",
                                                    "session-raw", "env-per-turn-dropped", "cross-check-unrouted",
                                                    "missing-transcript-graded", "open-after-start",
                                                    "cost-refusal-raises", "any-numbering", "strict-ignored"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
