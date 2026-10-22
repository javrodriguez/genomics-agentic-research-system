#!/usr/bin/env python3
"""F1 and F2, the synthetic vendor take folders of tests/test_vendor_check.py (lane-reports/vendor-T4-PLAN.md v4,
section 8; ruled READY by glitch-b5 on Sat 17 Oct 2026, on Javier's typed word "vendor-t4: yes").

  F1  tests/fixtures/vendor-check-codex/   a two-turn codex take: transcript.jsonl (the host's turn envelopes),
      driver-ledger.json, turn-<k>.jsonl (`codex exec --json` streams, each bound by its envelope's sha256),
      turn-<k>.jsonl.launch.json (the box's launch journal of turn k, its argv the adapter's own) and
      session/native-turn-<k>.jsonl (the rollout retained after turn k, response_item tool records included), from
      test_pending_codex_walk's generators.
  F2  tests/fixtures/vendor-check-gemini/  the same for gemini: `-o stream-json` streams and the retained native
      session snapshots, from test_pending_walk's accepted Gemini walk.

They hold the files P1's and P2's readers read (the bound view, the raw records, the launch journals P2's
inherited-context and run-tree legs read); environment.json lands with P5, whose readers read it. Every take folder a
test builds also carries P4's session-store.json (the drive's vendor store record: the store listed after every turn
and at publish, one sweep per turn, the nested CLI and unread stream line counts); F1 and F2 do not (files'
`store`): the codex store's date folders, the CLI's own <year>/<month>/<day> layout, read as lint_language's
ratio-slash shape, and an excusal of a committed line is a ruling, not this writer's (lane vendor-admission round 12). Every file is SYNTHETIC, written by this module from the documented shapes, and its
folder's README carries the label list. An F3 variant is these parts edited in a test and written by the same writer
into a scratch folder, its digests recomputed, so a variant differs from F1 or F2 only where its edit says. P2's
takes of a real draft row are the same parts built from that row's lines and replies (codex_parts and gemini_parts
take them), with the row's ledger fields merged into the ledger (files' `ledger`).

    python3 tests/vendor_check_fixtures.py --write    rewrite both folders
    python3 tests/vendor_check_fixtures.py --check    exit 1 unless both folders are what this module writes
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE.parent) not in sys.path:
    sys.path.insert(0, str(HERE.parent))
FIXTURES = HERE / "fixtures"
F1, F2 = FIXTURES / "vendor-check-codex", FIXTURES / "vendor-check-gemini"
SID = "5f0c1a2e-0000-5000-8000-0000000000f1"          # the driver's take identity (the ledger's session_id)
TURNS = 2
RUN_TREE = "/work/tree"                                # the take's run tree: the rollout's cwd and the journals'
MODES = {"codex": "bypass", "gemini": "yolo"}          # the adapters' MODE_FLAGS keys a journal's argv is built with

CODEX_TID = "00000000-0000-7000-8000-0000000000f1"    # the thread id codex mints at turn 1
CODEX_CLI = "0.162.1"
CODEX_MODEL = "gpt-6-luna"
CODEX_USAGE = {"input_tokens": 3, "cached_input_tokens": 0, "cache_write_input_tokens": 0, "output_tokens": 2,
               "reasoning_output_tokens": 0}

GEMINI_SID = "1a2b3c4d-0000-4000-8000-0000000000f2"   # the session id gemini mints
GEMINI_CLI = "0.64.0"
GEMINI_MODEL = "gemini-3.8-flash"
GEMINI_TS = "2026-10-14T00:00:00.000Z"
GEMINI_STATS = {"total_tokens": 3, "input_tokens": 2, "output_tokens": 1, "cached": 0, "input": 2, "duration_ms": 5,
                "tool_calls": 1, "models": {GEMINI_MODEL: {"total_tokens": 3, "input_tokens": 2, "output_tokens": 1,
                                                           "cached": 0, "input": 2}}}
LABEL = "SYNTHETIC, written by tests/vendor_check_fixtures.py from the documented shapes, not a recorded take."
# Lane vendor-settle stage V (S6): the CLI-written context records the settled vendor readers read, in the shapes the
# RECORDED w-o46 (codex-cli 0.162.1) and w-g21 (gemini-cli 0.64.0) takes hold, SYNTHETIC values only. The instruction
# file's text: P2's takes pass the design's pinned CLAUDE.md (R-6: AGENTS.md and GEMINI.md are its byte copies).
INSTRUCTIONS = "# Synthetic orientation\n\nA short synthetic instruction file.\n"
CODEX_COMMIT = "0" * 39 + "f"                          # session_meta.git's commit_hash (40 lower-case hex)
CODEX_PLAN = "plus"                                    # every token_count's rate_limits.plan_type (non-null)
# world_state's keys: the first of check_take.CODEX_WORLD_STATE_KEYS' two sets (the walks' set without the usage hint)
CODEX_WS_FILLER = {"collaboration_mode": {"mode": "default"}, "context_window_guidance": "", "environments_instructions":
                   False, "git_attribution": False, "host_skills": {"body": ""}, "managed_developer_instructions": {},
                   "model_catalog": "synthetic", "multi_agent_mode": {"mode": "explicitRequestOnly"},
                   "permissions": {"instructions": "synthetic"}, "persistent_mode": {}, "realtime": {"active": False},
                   "skills": {"includeInstructions": True}}
# T4 P4: where each CLI's own session sits in the take's config folder (native_snapshot's codex_rollout_rel and
# gemini_session_rel name it), the store root the drive lists (check_take.SESSION_STORE_ROOTS), and the read-write
# mounts a take container has (box/run_take.sweep_roots, which check_take.sweep_expected recomputes).
NATIVE_REL = {"codex": f"sessions/2026/10/14/rollout-2026-10-14T05-00-00-{CODEX_TID}.jsonl",
              "gemini": f".gemini/tmp/project-1/chats/session-2026-10-14T00-00-{GEMINI_SID[:8]}.jsonl"}
STORE_ROOTS = {"codex": "sessions", "gemini": ".gemini/tmp"}
CONFIG_MOUNT = "/opt/cfg"
SWEEP_FIXED = ("/tmp", "/var/tmp", "/dev/shm", "/etc/hosts", "/etc/hostname", "/etc/resolv.conf")


def sent(k: int) -> str:
    return f"sent {k}"


# ---- the parts: plain data a test edits before writing ------------------------------------------------------------
def _lines_replies(lines, replies) -> tuple:
    lines = [sent(k) for k in range(1, TURNS + 1)] if lines is None else list(lines)
    replies = ["Done."] * len(lines) if replies is None else list(replies)
    if len(replies) != len(lines) or not lines:
        raise ValueError("one reply per line, and at least one line")
    return lines, replies


def codex_context(cwd: str, model: str, instructions: str) -> list:
    """Turn 1's CLI-written context records, before its turn_context (the RECORDED w-o46 order, SYNTHETIC values):
    two developer sections of the closed six, one user message holding the AGENTS.md part and the environment-context
    part, and one full world_state (its agents_md the same file)."""
    def dev(tag):
        return ("response_item", {"type": "message", "role": "developer", "content": [
            {"type": "input_text", "text": f"<{tag}>synthetic</{tag}>"}]})
    agents = f"# AGENTS.md instructions for {cwd}\n\n<INSTRUCTIONS>\n{instructions}\n</INSTRUCTIONS>"
    env = (f"<environment_context>\n  <cwd>{cwd}</cwd>\n  <shell>bash</shell>\n  <workspace_roots><root>{cwd}</root>"
           "</workspace_roots>\n</environment_context>")
    state = dict(CODEX_WS_FILLER, agents_md={"directory": cwd, "text": instructions}, apps_instructions=False,
                 plugins_instructions=False, model=model, environments={"environments": {"local": {"cwd": cwd}}})
    return [dev("permissions instructions"), dev("collaboration_mode"),
            ("response_item", {"type": "message", "role": "user", "content": [
                {"type": "input_text", "text": agents}, {"type": "input_text", "text": env}]}),
            ("world_state", {"full": True, "state": state})]


def codex_token_count() -> tuple:
    return ("event_msg", {"type": "token_count", "info": {"total_token_usage": dict(CODEX_USAGE, total_tokens=5),
                                                          "last_token_usage": dict(CODEX_USAGE, total_tokens=5)},
                          "rate_limits": {"limit_id": "codex", "plan_type": CODEX_PLAN}})


def codex_parts(lines=None, replies=None, *, cwd: str = RUN_TREE, model: str = CODEX_MODEL,
                instructions: str = INSTRUCTIONS) -> dict:
    """{"streams": {k: [exec records]}, "meta": session_meta payload, "rollout": {k: [(line type, payload)]},
    "lines", "model", "cwd"}: one turn per line, its agent message the reply; turn 1 opens with the CLI's context
    records (codex_context) and every turn records a token_count with its plan."""
    lines, replies = _lines_replies(lines, replies)
    streams, rollout = {}, {}
    for k, (line, reply) in enumerate(zip(lines, replies), 1):
        cmd = {"id": "item_0", "type": "command_execution", "command": "ls"}
        streams[k] = [{"type": "thread.started", "thread_id": CODEX_TID}, {"type": "turn.started"},
                      {"type": "item.started", "item": dict(cmd, status="in_progress")},
                      {"type": "item.completed", "item": dict(cmd, aggregated_output=f"out {k}", exit_code=0,
                                                              status="completed")},
                      {"type": "item.completed", "item": {"id": "item_1", "type": "agent_message", "text": reply}},
                      {"type": "turn.completed", "usage": dict(CODEX_USAGE)}]
        tid = f"t{k}"

        def done(item):
            return ("event_msg", {"type": "item_completed", "thread_id": CODEX_TID, "turn_id": tid, "item": item,
                                  "completed_at_ms": 0})
        rollout[k] = [
            ("event_msg", {"type": "task_started", "turn_id": tid, "model_context_window": None,
                           "collaboration_mode_kind": "default"}),
            *(codex_context(cwd, model, instructions) if k == 1 else []),
            ("turn_context", {"turn_id": tid, "cwd": cwd, "approval_policy": "never",
                              "sandbox_policy": {"type": "danger-full-access"}, "model": model,
                              "multi_agent_version": "disabled"}),     # stage Z2: the agents-off record (T-18)
            ("response_item", {"type": "message", "role": "user", "content": [{"type": "input_text",
                                                                               "text": line}]}),
            done({"type": "UserMessage", "id": f"u{k}", "content": [{"type": "text", "text": line,
                                                                     "text_elements": []}]}),
            ("response_item", {"type": "function_call", "name": "exec_command", "call_id": f"call_{k}",
                               "arguments": json.dumps({"cmd": "ls", "workdir": cwd})}),
            done({"type": "CommandExecution", "id": f"c{k}", "command": ["ls"], "cwd": cwd, "parsed_cmd": [],
                  "source": "agent", "status": "completed", "aggregated_output": f"out {k}", "exit_code": 0}),
            ("response_item", {"type": "function_call_output", "call_id": f"call_{k}", "output": f"out {k}"}),
            codex_token_count(),
            ("response_item", {"type": "message", "role": "assistant", "content": [{"type": "output_text",
                                                                                    "text": reply}]}),
            done({"type": "AgentMessage", "id": f"m{k}", "content": [{"type": "Text", "text": reply}],
                  "phase": "final_answer"}),
            ("event_msg", {"type": "task_complete", "turn_id": tid, "last_agent_message": reply}),
        ]
    meta = {"session_id": CODEX_TID, "id": CODEX_TID, "timestamp": "2026-10-14T05:00:00.000Z", "cwd": cwd,
            "originator": "codex_exec", "cli_version": CODEX_CLI, "source": "exec", "model_provider": "openai",
            "base_instructions": {"text": "synthetic"}, "history_mode": "paginated",
            "runtime_workspace_roots": [cwd], "git": {"commit_hash": CODEX_COMMIT, "branch": "main"}}
    return {"streams": streams, "meta": meta, "rollout": rollout, "lines": lines, "model": model, "cwd": cwd}


def gemini_tool_call(k: int) -> dict:
    cid = f"call-{k}"
    return {"id": cid, "name": "read_file", "args": {"file_path": "notes.txt"}, "status": "success",
            "resultDisplay": "display text",
            "result": [{"functionResponse": {"id": cid, "name": "read_file", "response": {"output": "x"}}}]}


def gemini_session_context(run_tree: str, instructions: str) -> str:
    """The CLI's one context record's text (a user message opening <session_context>, the RECORDED w-g21 shape,
    SYNTHETIC values): the workspace directory and the listing's root the run tree, the GEMINI.md block the
    instruction file."""
    return "\n".join([
        "<session_context>", "This is the Gemini CLI. We are setting up the context for our chat.",
        "My operating system is: linux", "- **Workspace Directories:**", f"  - {run_tree}",
        "- **Directory Structure:**", "", "Showing up to 200 items (files + folders).", "", f"{run_tree}/",
        "\u251c\u2500\u2500\u2500CLAUDE.md", "\u2514\u2500\u2500\u2500GEMINI.md", "", "<loaded_context>",
        "<project_context>", f"--- Context from: {run_tree}/GEMINI.md ---", instructions.rstrip("\n"),
        f"--- End of Context from: {run_tree}/GEMINI.md ---", "</project_context>", "</loaded_context>",
        "</session_context>"])


def gemini_parts(lines=None, replies=None, *, model: str = GEMINI_MODEL, run_tree: str = RUN_TREE,
                 instructions: str = INSTRUCTIONS) -> dict:
    """{"streams": {k: [stream records]}, "meta": the snapshot's metadata record, "native": {k: [messages]}, "lines",
    "model"}: one interaction per line, its last response the reply; the first interaction opens with the CLI's
    <session_context> user record (gemini_session_context)."""
    lines, replies = _lines_replies(lines, replies)
    stats = copy.deepcopy(GEMINI_STATS)
    stats["models"] = {model: stats["models"][GEMINI_MODEL]}
    streams, native = {}, {}
    for k, (line, reply) in enumerate(zip(lines, replies), 1):
        def ev(t, **kw):
            return dict({"type": t, "timestamp": GEMINI_TS}, **kw)
        streams[k] = [ev("init", session_id=GEMINI_SID, model=model),
                      ev("message", role="user", content=line),
                      ev("message", role="assistant", content="I'll read it.", delta=True),
                      ev("tool_use", tool_name="read_file", tool_id=f"call-{k}", parameters={"file_path": "notes.txt"}),
                      ev("tool_result", tool_id=f"call-{k}", status="success", output="display text"),
                      ev("message", role="assistant", content=reply, delta=True),
                      ev("result", status="success", stats=copy.deepcopy(stats))]
        native[k] = [{"id": f"u{k}", "type": "user", "content": [{"text": line}]},
                     {"id": f"a{k}", "type": "gemini", "model": model, "content": "I'll read it.",
                      "toolCalls": [gemini_tool_call(k)]},
                     {"id": f"rt{k}", "type": "user", "content": [
                         {"functionResponse": {"id": f"call-{k}", "name": "read_file", "response": {"output": "x"}}}]},
                     {"id": f"b{k}", "type": "gemini", "model": model, "content": reply}]
    import gemini_projection                       # the context turn's pinned id (gemini_projection._session_context)
    native[1].insert(0, {"id": gemini_projection.ENV_CONTEXT_ID, "timestamp": GEMINI_TS, "type": "user",
                         "content": [{"text": gemini_session_context(run_tree, instructions)}]})
    meta = {"sessionId": GEMINI_SID, "projectHash": "project-1", "summary": "synthetic"}
    return {"streams": streams, "meta": meta, "native": native, "lines": lines, "model": model}


# ---- the writer ---------------------------------------------------------------------------------------------------
def _jl(records) -> bytes:
    return "".join(json.dumps(r) + "\n" for r in records).encode("utf-8")


def _codex_snapshot(parts: dict, upto: int) -> bytes:
    recs = []
    for t, pay in [("session_meta", parts["meta"])] + [x for k in range(1, upto + 1) for x in parts["rollout"][k]]:
        recs.append({"timestamp": f"2026-10-14T05:00:{len(recs):02d}.000Z", "ordinal": len(recs), "type": t,
                     "payload": pay})
    return _jl(recs)


def _gemini_snapshot(parts: dict, upto: int) -> bytes:
    return _jl([parts["meta"]] + [m for k in range(1, upto + 1) for m in parts["native"][k]])


def store_entries(harness: str) -> list:
    """The store listing drive.store_listing records for a take holding only its own session: every folder under the
    store root on the way to the session file, then the file, as [path, kind] pairs."""
    parts = NATIVE_REL[harness].split("/")
    depth = len(STORE_ROOTS[harness].split("/"))
    return [["/".join(parts[:i]), "dir"] for i in range(depth + 1, len(parts))] + [[NATIVE_REL[harness], "file"]]


def session_store(harness: str, turns: list, *, run_tree: str = RUN_TREE) -> dict:
    """The drive's session-store.json of a vendor take (drive.py _take_records): the store listed after every turn
    (post-<k>) and at publish, one sweep of the take container per turn finding only the take's own session, and the
    shell-command counts of a take whose commands start no nested CLI and whose stream lines were all read."""
    vendor_id = CODEX_TID if harness == "codex" else GEMINI_SID
    mounts = [run_tree, CONFIG_MOUNT, *SWEEP_FIXED]
    listings = [{"at": f"post-{k}", "entries": store_entries(harness)} for k in turns]
    sweeps = [{"at": f"post-{k}", "files": [[f"{CONFIG_MOUNT}/{NATIVE_REL[harness]}", harness, vendor_id]],
               "unreadable": [], "escapes": [], "mounts": list(mounts), "scanned": 1, "truncated": False,
               "expected": list(mounts)} for k in turns]
    return {"harness": harness, "root": STORE_ROOTS[harness],
            "listings": listings + [{"at": "publish", "entries": store_entries(harness)}], "sweeps": sweeps,
            "nested_cli_calls": 0, "unread_stream_lines": 0}


def journal(harness: str, parts: dict, k: int, *, run_tree: str = RUN_TREE, mode: str | None = None) -> dict:
    """Turn k's launch journal as box/run_take.run_turn writes it: its argv the adapter's own for the line, model and
    mode (turn 1 resumes nothing; a later turn resumes the vendor id), its cwd the run tree, its stream turn k's."""
    import codex_adapter
    import gemini_adapter
    adapter = codex_adapter if harness == "codex" else gemini_adapter
    vendor_id = CODEX_TID if harness == "codex" else GEMINI_SID
    argv = adapter.argv(parts["lines"][k - 1], model=parts["model"], mode=mode or MODES[harness],
                        session_id=None if k == 1 else vendor_id, first=k == 1)
    return {"schema": 1, "harness": harness, "container_id": "synthetic", "argv": argv, "cwd": run_tree,
            "stream": f"/synthetic/take/turn-{k}.jsonl", "started_at": 0}


def files(harness: str, parts: dict | None = None, *, sid: str = SID, ledger: dict | None = None,
          run_tree: str = RUN_TREE, mode: str | None = None, store: bool = True) -> dict:
    """{relative path: bytes} of one take folder of `harness` built from `parts` (its default parts when None); the
    driver's take identity `sid`, and `ledger`'s fields merged over the ledger's own (a test's draft-row fields); with
    `store`, the drive's session-store.json (F1 and F2 are written without it)."""
    if harness == "codex":
        parts = codex_parts() if parts is None else parts
        vendor_id, version, snapshot = CODEX_TID, CODEX_CLI, _codex_snapshot
    else:
        parts = gemini_parts() if parts is None else parts
        vendor_id, version, snapshot = GEMINI_SID, GEMINI_CLI, _gemini_snapshot
    out, envelopes, snaps = {}, [], []
    turns = sorted(parts["streams"])
    for k in turns:
        name = f"turn-{k}.jsonl"
        out[name] = _jl(parts["streams"][k])
        envelopes.append({"type": "harness-turn", "harness": harness, "session_id": sid,
                          "vendor_session_id": vendor_id, "n": k, "sent": parts["lines"][k - 1], "stream": name,
                          "sha256": hashlib.sha256(out[name]).hexdigest()})
        out[f"{name}.launch.json"] = (json.dumps(journal(harness, parts, k, run_tree=run_tree, mode=mode),
                                                 separators=(",", ":")) + "\n").encode("utf-8")
        raw = snapshot(parts, k)
        out[f"session/native-turn-{k}.jsonl"] = raw
        snaps.append({"file": f"native-turn-{k}.jsonl", "sha256": hashlib.sha256(raw).hexdigest()})
    out["transcript.jsonl"] = _jl(envelopes)
    if store:
        out["session-store.json"] = (json.dumps(session_store(harness, turns, run_tree=run_tree), indent=2)
                                     + "\n").encode("utf-8")
    doc = {"kind": "take", "agent": {"harness": harness, "version": version}, "session_id": sid,
           "turns": [{"n": k, "sent": parts["lines"][k - 1]} for k in turns],
           "streams": [f"turn-{k}.jsonl" for k in turns], "transcript": "transcript.jsonl", "native_snapshots": snaps}
    doc.update(copy.deepcopy(ledger or {}))
    out["driver-ledger.json"] = (json.dumps(doc, indent=2) + "\n").encode("utf-8")
    title = {"codex": "F1, a synthetic codex take", "gemini": "F2, a synthetic gemini take"}[harness]
    readme = [f"# {title} (lane vendor-admission T4, plan v4 section 8)", "",
              "Written by tests/vendor_check_fixtures.py (`--write`; `--check` binds this folder to it). Labels:", ""]
    readme += [f"- `{p}`: {LABEL}" for p in sorted(out)]
    out["README.md"] = ("\n".join(readme) + "\n").encode("utf-8")
    return out


def write(folder: Path, harness: str, parts: dict | None = None, **kw) -> Path:
    """Write one take folder (files' keywords pass through); returns its transcript.jsonl."""
    folder = Path(folder)
    for rel, data in files(harness, parts, **kw).items():
        (folder / rel).parent.mkdir(parents=True, exist_ok=True)
        (folder / rel).write_bytes(data)
    return folder / "transcript.jsonl"


def problems() -> list:
    out = []
    for folder, harness in ((F1, "codex"), (F2, "gemini")):
        want = files(harness, store=False)
        have = {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()} if folder.is_dir() else set()
        out += [f"{folder.name}/{p}: not written by this module" for p in sorted(have - set(want))]
        out += [f"{folder.name}/{p}: missing or differs" for p, data in sorted(want.items())
                if p not in have or (folder / p).read_bytes() != data]
    return out


if __name__ == "__main__":
    if sys.argv[1:] == ["--write"]:
        for folder, harness in ((F1, "codex"), (F2, "gemini")):
            write(folder, harness, store=False)
        raise SystemExit(0)
    if sys.argv[1:] == ["--check"]:
        bad = problems()
        print("\n".join(bad) or "ok: F1 and F2 are what tests/vendor_check_fixtures.py writes")
        raise SystemExit(1 if bad else 0)
    raise SystemExit("usage: vendor_check_fixtures.py --write | --check")
