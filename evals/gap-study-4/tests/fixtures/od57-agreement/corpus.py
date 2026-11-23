#!/usr/bin/env python3
"""The OD57 agreement corpus (lane vendor-b24, glitch-26's rulings B24-2): one synthetic record set per read shape,
each with the verdict both scanners must give it, line by line.

The harness twin (box/scan_record.py through box/od57_rule.py) runs it in tests/test_od57_agreement.py; the aegis door
runs the same JSON (a byte copy, pinned by sha256) in its own lane. Every record is synthetic: its keys and types follow
the committed walks (lane-reports/vendor-b24-DESIGN.md section 2), every value is invented, and the ruled line is the
placeholder PLACEHOLDER, which a runner replaces by line 175 of the GARS doc it reads itself, so no copy of the line
lives in this file or in the JSON.

    python3 tests/fixtures/od57-agreement/corpus.py --write     writes cases.json beside it from build()
    python3 tests/fixtures/od57-agreement/corpus.py --check     exits 1 unless the JSON on disk is build()'s output

It lives in the fixture folder, not in tests/, because tests/ holds test modules only (test_round4.module_problems).

Each case: {"name", "family" ("c" Claude, "g" Gemini, "o" Codex), "kind" (stream | session | transcript), "records"
(one JSON value per line), "admit" (the 1-based lines admitted), "refuse" (the lines refused), "why" (one line)}. A line
is flagged by the corpus scanner when it holds the placeholder's first 40 characters (the runner's fake rules scanner),
and every flagged line is in exactly one of admit and refuse.
"""

from __future__ import annotations

import json
import os
import sys

PLACEHOLDER = "@OD57@"
# Round 3 (glitch-26's R3-4): the second key a real gitleaks 8.30 flags as generic-api-key, built by the runner at run
# time (second_key()), never written here: a record holds this placeholder in its place.
SECOND_PLACEHOLDER = "@SECOND@"
HERE = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(HERE, "cases.json")
L = PLACEHOLDER                                   # the ruled line, as it sits in a record
TS = "2026-10-21T00:00:00.000Z"
RUN = "/tmp/run-b24c0de5"                         # a run tree (the walks' form: /tmp/run-<8 hex>)
DOC_ABS = RUN + "/gars/_references/environment.md"
DOC_REL = "_references/environment.md"
GDIR = "gars/_references"                         # w-g22's dir_path form: the doc's folder, relative to the run tree


# ---------------------------------------------------------------------------------------------------- Claude Code
def c_use(uid, name, inp):
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": uid, "name": name, "input": inp}]}}


def c_result(uid, content, tur=None):
    rec = {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": uid, "content": content}]}}
    if tur is not None:
        rec["toolUseResult"] = tur
    return rec


def c_bash(cmd, out):
    return [c_use("toolu_B", "Bash", {"command": cmd}),
            c_result("toolu_B", out, {"stdout": out, "stderr": "", "interrupted": False})]


def c_read(path, content=None):
    content = content if content is not None else f"   174→line 174\n   175→{L}\n   176→line 176\n"
    return [c_use("toolu_R", "Read", {"file_path": path}),
            c_result("toolu_R", content, {"type": "text", "file": {"filePath": path,
                                                                    "content": f"line 174\n{L}\nline 176"}})]


def c_grep(inp, out):
    return [c_use("toolu_G", "Grep", inp),
            c_result("toolu_G", out, {"mode": "content", "numFiles": 1, "filenames": [], "content": out,
                                      "numLines": out.count("\n") + 1})]


# ---------------------------------------------------------------------------------------------------- Gemini CLI
G_HEAD = {"sessionId": "session-1", "projectHash": "hash-1", "startTime": TS, "lastUpdated": TS,
          "kind": "main"}
G_USER = {"id": "msg-u1", "timestamp": TS, "type": "user", "content": [{"text": "read the pinned versions"}]}


def g_resp(cid, name, output):
    return {"functionResponse": {"id": cid, "name": name, "response": {"output": output}}}


def g_call(cid, name, args, output, display=""):
    return {"id": cid, "name": name, "args": args, "result": [g_resp(cid, name, output)], "status": "success",
            "timestamp": TS, "resultDisplay": display, "displayName": name, "description": "",
            "renderOutputAsMarkdown": True}


def g_msg(mid, calls):
    return {"id": mid, "timestamp": TS, "type": "gemini", "content": "", "toolCalls": calls, "thoughts": [],
            "model": "model-under-test", "tokens": {"input": 10, "output": 2, "total": 12}}


def g_user_resp(mid, *parts):
    return {"id": mid, "timestamp": TS, "type": "user", "content": list(parts)}


def g_patch(cid, *responses):
    return {"$patch": {"removeIds": [], "updates": [{"id": "msg-g1", "toolCalls": [{"id": cid,
                                                                                    "result": list(responses)}]}]}}


def g_shell_out(stdout):
    return f"<untrusted_context>\nOutput: {stdout}\nProcess Group PGID: 4242\n</untrusted_context>"


def grep_out(pattern, where, blocks):
    """Gemini 0.64.0's grep_search llmContent (bundle/chunk-NR7L3FXV.js:321667-321690): a header, then per file
    `---`/`File: <path>` and `L<n><sep> <line>` lines, trimmed. blocks: [(header path, [(n, sep, text)])]."""
    count = sum(1 for _, rows in blocks for _, sep, _ in rows if sep == ":")
    out = f'Found {count} {"match" if count == 1 else "matches"} for pattern "{pattern}" {where}:\n---\n'
    for header, rows in blocks:
        out += f"File: {header}\n"
        out += "".join(f"L{n}{sep} {text}\n" for n, sep, text in rows)
        out += "---\n"
    return out.strip()


def g_match(n, text, absolute=DOC_ABS, rel="environment.md"):
    return {"filePath": rel, "absolutePath": absolute, "lineNumber": n, "line": text}


def g_display(matches):
    return {"summary": f"Found {len(matches)} matches", "matches": matches}


def g_grep_records(args, blocks, matches, replays=True, name="grep_search"):
    """A grep_search call as w-g22 committed it: the gemini record (output + display), its user response, and (with
    replays) a replayed two-part user response and a $patch holding two copies."""
    out = grep_out(args.get("pattern", "p"), f'in path "{args.get("dir_path", ".")}"', blocks)
    recs = [G_HEAD, G_USER, g_msg("msg-g1", [g_call("call-g1", name, args, out, g_display(matches))]),
            g_user_resp("msg-u2", g_resp("call-g1", name, out))]
    if replays:
        recs += [g_user_resp("msg-u3", g_resp("call-g1", name, out), g_resp("call-g1", name, out)),
                 g_patch("call-g1", g_resp("call-g1", name, out), g_resp("call-g1", name, out))]
    return recs


FOUR = [g_match(84, "line 84"), g_match(101, "line 101"), g_match(125, "line 125"), g_match(175, L)]
DOC_BLOCK = ("environment.md", [(84, ":", "line 84"), (101, ":", "line 101"), (125, ":", "line 125"),
                                (175, ":", L)])
GARGS = {"pattern": "pinned|deseq", "dir_path": GDIR}


def ctx_block(match_lines, extra=((174, "-", "line 174"), (175, "-", L), (176, "-", "line 176"))):
    rows = sorted([(n, ":", f"line {n}") for n in match_lines] + list(extra))
    return ("environment.md", rows)


def g_stream(cid, name, params, output):
    return [{"type": "init", "timestamp": TS, "session_id": "session-1", "model": "model-under-test"},
            {"type": "tool_use", "timestamp": TS, "tool_name": name, "tool_id": cid, "parameters": params},
            {"type": "tool_result", "timestamp": TS, "tool_id": cid, "status": "success", "output": output}]


# ---------------------------------------------------------------------------------------------------- Codex CLI
def o_item(event, iid, command, output, status="completed", typ="command_execution"):
    return {"type": event, "item": {"id": iid, "type": typ, "command": command, "aggregated_output": output,
                                    "exit_code": 0, "status": status}}


def o_stream(script, out, shell="/bin/bash", flag="-lc"):
    cmd = f"{shell} {flag} '{script}'"
    return [{"type": "thread.started", "thread_id": "thread-1"}, {"type": "turn.started"},
            o_item("item.started", "item_1", cmd, "", "in_progress"), o_item("item.completed", "item_1", cmd, out)]


def o_line(n, kind, payload):
    return {"timestamp": TS, "ordinal": n, "type": kind, "payload": payload}


def o_rollout(script, out, copy=None):
    exec_in = 'const r = await tools.exec_command({cmd: "x"});\ntext(r.output);'
    return [o_line(0, "session_meta", {"id": "thread-1", "cli_version": "0.162.1", "cwd": RUN}),
            o_line(1, "response_item", {"type": "custom_tool_call", "name": "exec", "call_id": "call-o1",
                                        "id": "ctc_1", "input": exec_in, "status": "completed"}),
            o_line(2, "event_msg", {"type": "item_completed", "thread_id": "thread-1", "turn_id": "turn-1",
                                    "item": {"type": "CommandExecution", "id": "exec-1",
                                             "command": ["/bin/bash", "-lc", script], "cwd": "file://" + RUN,
                                             "parsed_cmd": [], "process_id": "1001",
                                             "source": "unified_exec_startup", "status": "completed",
                                             "aggregated_output": out, "exit_code": 0, "duration": 1}}),
            o_line(3, "response_item", {"type": "custom_tool_call_output", "call_id": "call-o1", "id": "ctco_3",
                                        "output": [{"type": "input_text",
                                                    "text": out if copy is None else copy}]})]


# ---------------------------------------------------------------------------------------------------- the cases
def case(name, family, kind, records, admit, refuse, why):
    return {"name": name, "family": family, "kind": kind, "records": records, "admit": admit, "refuse": refuse,
            "why": why}


def build() -> list:
    cases = []
    add = cases.append
    lines3 = f"line 174\n{L}\nline 176\n"

    # ---------------------------------------------------------------- Gemini grep_search (B24-2 item 2, as revised)
    add(case("g-grep-match", "g", "session", g_grep_records(GARGS, [DOC_BLOCK], FOUR), [3, 4, 5, 6], [],
             "w-g22's shape: `L175: ` in its File: environment.md block (dir_path gars/_references), attested by "
             "the display's match 175 on the doc, in the gemini, user, replayed and $patch records"))
    add(case("g-grep-match-no-replay-abs-dir", "g", "session",
             g_grep_records({"pattern": "pinned", "dir_path": RUN + "/gars/_references"}, [DOC_BLOCK], FOUR,
                            replays=False), [3, 4], [], "an absolute dir_path inside the run tree"))
    add(case("g-grep-auto-one", "g", "session",
             g_grep_records(GARGS, [ctx_block([140])], [g_match(140, "line 140")], replays=False), [3, 4], [],
             "auto-context, one match at 140: 50 lines each side (321598-321599), 175 inside"))
    add(case("g-grep-auto-three", "g", "session",
             g_grep_records(GARGS, [ctx_block([101, 160, 300])],
                            [g_match(101, "line 101"), g_match(160, "line 160"), g_match(300, "line 300")],
                            replays=False), [3, 4], [], "auto-context, three matches: 15 lines each side, 175-160=15"))
    add(case("g-grep-explicit-context", "g", "session",
             g_grep_records(dict(GARGS, context=20), [ctx_block([160])], [g_match(160, "line 160")],
                            replays=False), [3, 4], [], "explicit context 20 around 160"))
    add(case("g-grep-explicit-after", "g", "session",
             g_grep_records(dict(GARGS, before=2, after=15), [ctx_block([160])], [g_match(160, "line 160")],
                            replays=False), [3, 4], [], "explicit after 15 from 160"))
    # witnesses that stay refused (each red alone, test_od57_agreement.RED_ALONE)
    add(case("g-grep-auto-one-outside", "g", "session",
             g_grep_records(GARGS, [ctx_block([124])], [g_match(124, "line 124")], replays=False), [], [3, 4],
             "175 is 51 lines after the one match: outside the 50-line auto window"))
    add(case("g-grep-auto-three-outside", "g", "session",
             g_grep_records(GARGS, [ctx_block([101, 159, 300])],
                            [g_match(101, "line 101"), g_match(159, "line 159"), g_match(300, "line 300")],
                            replays=False), [], [3, 4], "175 is 16 after the nearest of three matches"))
    add(case("g-grep-explicit-outside", "g", "session",
             g_grep_records(dict(GARGS, context=14), [ctx_block([160])], [g_match(160, "line 160")],
                            replays=False), [], [3, 4], "explicit context 14 around 160 ends at 174"))
    add(case("g-grep-explicit-after-outside", "g", "session",
             g_grep_records(dict(GARGS, context=30, after=14), [ctx_block([160])], [g_match(160, "line 160")],
                            replays=False), [], [3, 4], "after 14 overrides context 30 on that side"))
    add(case("g-grep-four-matches-no-auto", "g", "session",
             g_grep_records(GARGS, [ctx_block([101, 120, 160, 300])],
                            [g_match(n, f"line {n}") for n in (101, 120, 160, 300)], replays=False), [], [3, 4],
             "four matches: auto-context does not fire, so a context line has no window"))
    add(case("g-grep-names-only", "g", "session",
             g_grep_records(dict(GARGS, names_only=True), [ctx_block([160])], [g_match(160, "line 160")],
                            replays=False), [], [3, 4], "names_only set: no auto-context, and not an admitted key"))
    add(case("g-grep-other-header", "g", "session",
             g_grep_records(GARGS, [("other.md", [(175, ":", L)])], [g_match(175, L)], replays=False), [], [3, 4],
             "the right line under another file's header (the display attests the doc)"))
    add(case("g-grep-other-header-context", "g", "session",
             g_grep_records(GARGS, [("other.md", [(160, ":", "line 160"), (175, "-", L)])],
                            [g_match(160, "line 160")], replays=False), [], [3, 4],
             "a context line under another file's header, the window and attestation met"))
    add(case("g-grep-forged-block", "g", "session",
             g_grep_records(GARGS, [("environment.md", [(175, ":", L)])],
                            [g_match(175, "line 175 of another file", "/tmp/run-b24c0de5/gars/notes.md", "notes.md")],
                            replays=False), [], [3, 4], "a block naming the doc with no display entry for it"))
    add(case("g-grep-wrong-number", "g", "session",
             g_grep_records(GARGS, [("environment.md", [(176, ":", L)])], [g_match(176, L)], replays=False), [],
             [3, 4], "`L176: ` and a display lineNumber 176"))
    add(case("g-grep-display-other-path", "g", "session",
             g_grep_records(GARGS, [DOC_BLOCK],
                            FOUR[:3] + [g_match(175, L, "/tmp/run-b24c0de5/gars/notes/environment.md")],
                            replays=False), [], [3, 4], "the display entry's absolutePath is another environment.md"))
    add(case("g-grep-dotdot-header", "g", "session",
             g_grep_records({"pattern": "p", "dir_path": "gars/x"},
                            [("../_references/environment.md", [(175, ":", L)])],
                            [g_match(175, L)], replays=False), [], [3, 4], "a header that climbs out with .."))
    add(case("g-grep-path-key", "g", "session",
             g_grep_records({"pattern": "p", "dir_path": GDIR, "path": GDIR}, [DOC_BLOCK], FOUR, replays=False),
             [], [3, 4],
             "an argument key the rule does not admit (path)"))
    add(case("g-grep-alias", "g", "session",
             g_grep_records(GARGS, [DOC_BLOCK], FOUR, replays=False, name="search_file_content"), [], [3, 4],
             "the legacy alias search_file_content"))
    add(case("g-grep-patch-orphan", "g", "session",
             [G_HEAD, G_USER, g_patch("call-g9", g_resp("call-g9", "grep_search",
                                                         grep_out("p", "in path", [DOC_BLOCK])))], [], [3],
             "a $patch response whose id names no gemini call"))
    add(case("g-grep-second-key", "g", "session",
             g_grep_records(GARGS, [("environment.md", [(175, ":", L), (176, ":", SECOND_PLACEHOLDER)])],
                            [g_match(175, L), g_match(176, SECOND_PLACEHOLDER)], replays=False), [],
             [3, 4], "a second key on the record (the probe refuses)"))
    add(case("g-grep-pattern-line", "g", "session",
             g_grep_records({"pattern": L, "dir_path": GDIR}, [DOC_BLOCK], FOUR, replays=False), [], [3, 4],
             "the model's pattern is the line, so line 0 (the tool's header) carries it too: never admitted text"))
    add(case("g-display-in-glob", "g", "session",
             [G_HEAD, G_USER, g_msg("msg-g1", [g_call("call-g1", "glob", {"pattern": "*.md"}, "found 1 file",
                                                      g_display([g_match(175, L)]))])], [], [3],
             "the line in another tool's display"))

    # ---------------------------------------------------------------- Gemini read_file, shell, stream (existing shapes)
    add(case("g-read-file", "g", "session",
             [G_HEAD, G_USER, g_msg("msg-g1", [g_call("call-g1", "read_file", {"file_path": DOC_ABS}, lines3)]),
              g_user_resp("msg-u2", g_resp("call-g1", "read_file", lines3)),
              g_patch("call-g1", g_resp("call-g1", "read_file", lines3))], [3, 4, 5], [], "read_file of the doc"))
    add(case("g-shell-cat", "g", "session",
             [G_HEAD, G_USER, g_msg("msg-g1", [g_call("call-g1", "run_shell_command",
                                                      {"command": "cat " + DOC_REL, "description": "read"},
                                                      g_shell_out(lines3.rstrip("\n")), lines3.rstrip("\n"))]),
              g_user_resp("msg-u2", g_resp("call-g1", "run_shell_command", g_shell_out(lines3.rstrip("\n"))))],
             [3, 4], [], "a cat of the doc: output (wrapped) and resultDisplay"))
    add(case("g-shell-grep-output-prefix", "g", "session",
             [G_HEAD, G_USER, g_msg("msg-g1", [g_call("call-g1", "run_shell_command",
                                                      {"command": "grep -n pinned " + DOC_REL, "description": "r"},
                                                      g_shell_out(f"175:{L}"), f"175:{L}")])], [3], [],
             "the line right behind `Output: `, with grep -n's 175:"))
    add(case("g-stream-shell", "g", "stream",
             g_stream("call-g1", "run_shell_command", {"command": "cat " + DOC_REL, "description": "r"},
                      lines3.rstrip("\n")), [3], [], "the stream's tool_result of a cat"))
    add(case("g-model-text", "g", "session",
             [G_HEAD, G_USER, dict(g_msg("msg-g1", []), content=f"the doc says:\n{L}")], [], [3],
             "model text"))
    add(case("g-thoughts", "g", "session",
             [G_HEAD, G_USER, dict(g_msg("msg-g1", []), thoughts=[{"subject": "s", "description": L}])], [], [3],
             "a thought"))

    # ---------------------------------------------------------------- T1: a write of the doc first
    add(case("t1-gemini-write-then-read", "g", "session",
             [G_HEAD, G_USER, g_msg("msg-g0", [g_call("call-g0", "write_file",
                                                      {"file_path": DOC_ABS, "content": "x"}, "ok")]),
              g_msg("msg-g1", [g_call("call-g1", "read_file", {"file_path": DOC_ABS}, lines3)])], [], [4],
             "write_file of the doc, then read_file"))
    add(case("t1-gemini-replace-then-grep", "g", "session",
             [G_HEAD, G_USER, g_msg("msg-g0", [g_call("call-g0", "replace",
                                                      {"file_path": DOC_ABS, "old_string": "a", "new_string": "b"},
                                                      "ok")])] + g_grep_records(GARGS, [DOC_BLOCK], FOUR,
                                                                                replays=False)[2:], [], [4, 5],
             "replace of the doc, then grep_search"))
    add(case("t1-gemini-read-then-write", "g", "session",
             [G_HEAD, G_USER, g_msg("msg-g1", [g_call("call-g1", "read_file", {"file_path": DOC_ABS}, lines3)]),
              g_msg("msg-g2", [g_call("call-g2", "write_file", {"file_path": DOC_ABS, "content": "x"}, "ok")])],
             [3], [], "the read comes first: admitted"))
    add(case("t1-claude-edit-then-read", "c", "transcript",
             [c_use("toolu_E", "Edit", {"file_path": DOC_ABS, "old_string": "a", "new_string": "b"}),
              c_result("toolu_E", "ok")] + c_read(DOC_ABS), [], [4], "Edit of the doc, then Read"))
    add(case("t1-codex-file-change-then-cat", "o", "stream",
             [{"type": "thread.started", "thread_id": "thread-1"},
              {"type": "item.started", "item": {"id": "item_0", "type": "file_change",
                                                "changes": [{"path": DOC_ABS, "kind": "update"}],
                                                "status": "in_progress"}}] + o_stream("cat " + DOC_REL, lines3)[1:],
             [], [5], "a Codex file_change of the doc, then a cat"))

    # ---------------------------------------------------------------- T2 as revised: grep's own labels
    w167 = (f"cd {RUN}/gars && grep -n -i \"deseq\\|sklearn\" _references/environment.md "
            "_references/gars-bio.conda.txt 2>/dev/null | head -30")
    add(case("t2-w167-labelled", "c", "transcript", c_bash(w167, f"_references/environment.md:175:{L}\n"), [2], [],
             "W167's shape: several operands, the line labelled with the doc and :175:"))
    add(case("t2-single-operand", "c", "transcript", c_bash("grep -n pinned " + DOC_REL, f"175:{L}\n"), [2], [],
             "the doc as the single operand: no label"))
    add(case("t2-cat-n", "c", "transcript", c_bash("cat -n " + DOC_REL, f"   174\tline 174\n   175\t{L}\n"), [2],
             [], "cat -n of the doc"))
    add(case("t2-gemini-several", "g", "session",
             [G_HEAD, G_USER, g_msg("msg-g1", [g_call("call-g1", "run_shell_command",
                                                      {"command": f"grep pinned {DOC_REL} gars-bio.lock.txt"},
                                                      g_shell_out(f"{DOC_REL}:{L}"), f"{DOC_REL}:{L}")])], [3], [],
             "Gemini: two operands, labelled"))
    add(case("t2-codex-single", "o", "stream", o_stream("cat " + DOC_REL, lines3), [4], [], "Codex: a cat"))
    add(case("t2-codex-rollout", "o", "session", o_rollout("grep -n pinned " + DOC_REL, f"175:{L}\n"), [3, 4], [],
             "Codex rollout: the CommandExecution and the exec output's verbatim copy"))
    # od57-line (SCANREFUSAL-ROAD-20261108; Javier's word pending, ask od57-line): ten T2 refusals of this corpus print
    # the pinned bytes as a whole Bash or shell output line after a closed prefix, so they are admitted whatever the
    # command. Each was its read rule's refusal (still witnessed with the fallback off: RED_ALONE_READS in the runner),
    # and each has a refusal twin one residual edge away: a trailing byte, a changed byte, or another rule on the line.
    add(case("t2-h-several", "c", "transcript",
             c_bash(f"grep -h pinned {DOC_REL} /tmp/notes.md", f"{L}\n"), [2], [],
             "od57-line: a whole bare output line (was: grep -h with several operands, no label to bind)"))
    add(case("t2-h-several-trailing", "c", "transcript",
             c_bash(f"grep -h pinned {DOC_REL} /tmp/notes.md", f"{L}~\n"), [], [2],
             "od57-line twin: one byte after the pinned bytes"))
    add(case("t2-other-label", "c", "transcript",
             c_bash(f"grep pinned {DOC_REL} /tmp/notes.md", f"/tmp/notes.md:{L}\n"), [], [2],
             "the line labelled with another file"))
    add(case("t2-label-wrong-number", "c", "transcript",
             c_bash(f"grep -n pinned {DOC_REL} /tmp/notes.md", f"{DOC_REL}:176:{L}\n"), [], [2],
             "the doc's label with :176: under -n"))
    add(case("t2-label-outside-run-tree", "c", "transcript",
             c_bash("grep pinned /home/someone/gars/_references/environment.md /tmp/notes.md",
                    f"/home/someone/gars/_references/environment.md:{L}\n"), [], [2],
             "a label naming an environment.md outside the run tree"))
    add(case("t2-label-flag", "c", "transcript",
             c_bash(f"grep --label={DOC_REL} -H pinned {DOC_REL} /tmp/notes.md", f"{DOC_REL}:{L}\n"), [2], [],
             "od57-line: the doc's label, a whole output line (was: --label rewrites the label)"))
    add(case("t2-label-flag-changed", "c", "transcript",
             c_bash(f"grep --label={DOC_REL} -H pinned {DOC_REL} /tmp/notes.md", f"{DOC_REL}:176:{L}\n"), [], [2],
             "od57-line twin: one changed byte in the prefix (:176:)"))
    add(case("t2-unlabelled-other-only", "c", "transcript",
             c_bash("grep pinned /tmp/notes.md", f"{L}\n"), [2], [],
             "od57-line: a whole bare output line (was: a single operand that is not the doc)"))
    add(case("t2-unlabelled-other-only-trailing", "c", "transcript",
             c_bash("grep pinned /tmp/notes.md", f"{L} \n"), [], [2],
             "od57-line twin: one byte (a space) after the pinned bytes"))
    add(case("t2-cat-two", "c", "transcript", c_bash(f"cat {DOC_REL} /tmp/notes.md", f"{L}\n"), [2], [],
             "od57-line: a whole bare output line (was: cat of two files, cat labels nothing)"))
    add(case("t2-cat-two-trailing", "c", "transcript", c_bash(f"cat {DOC_REL} /tmp/notes.md", f"{L}.\n"), [], [2],
             "od57-line twin: one byte after the pinned bytes"))
    add(case("t2-then-cat-other", "c", "transcript",
             c_bash(f"grep pinned {DOC_REL} && cat /tmp/notes.md", f"{L}\n"), [2], [],
             "od57-line: a whole bare output line (was: a second command after the read reads another file)"))
    add(case("t2-then-cat-other-trailing", "c", "transcript",
             c_bash(f"grep pinned {DOC_REL} && cat /tmp/notes.md", f"{L}x\n"), [], [2],
             "od57-line twin: one byte after the pinned bytes"))
    add(case("t2-filter-with-file", "c", "transcript",
             c_bash(f"cat {DOC_REL} | head /tmp/notes.md", f"{L}\n"), [2], [],
             "od57-line: a whole bare output line (was: a filter that names a file)"))
    add(case("t2-filter-with-file-trailing", "c", "transcript",
             c_bash(f"cat {DOC_REL} | head /tmp/notes.md", f"{L}\t\n"), [], [2],
             "od57-line twin: one byte (a tab) after the pinned bytes"))
    add(case("t2-codex-c-flag", "o", "stream", o_stream("cat " + DOC_REL, lines3, flag="-c"), [4], [],
             "od57-line: a whole bare line of a shell tool's output (was: bash -c, which no committed record uses, "
             "F-RS-6)"))
    add(case("t2-codex-c-flag-trailing", "o", "stream",
             o_stream("cat " + DOC_REL, f"line 174\n{L}~\nline 176\n", flag="-c"), [], [4],
             "od57-line twin: one byte after the pinned bytes"))

    # ---------------------------------------------------------------- Claude Read and Grep (item 3)
    add(case("c-read-doc", "c", "transcript", c_read(DOC_ABS), [2], [], "Read of the doc"))
    add(case("c-read-other", "c", "transcript", c_read(RUN + "/notes.md"), [], [2],
             "Read of another path (F-RS-4)"))
    add(case("c-grep-doc", "c", "transcript",
             c_grep({"pattern": "pinned", "path": DOC_ABS, "output_mode": "content", "-n": True}, f"175:{L}"), [2],
             [], "Grep of the doc, content mode"))
    add(case("c-grep-doc-context", "c", "transcript",
             c_grep({"pattern": "line 174", "path": DOC_ABS, "output_mode": "content", "-n": True, "-A": 1},
                    f"174:line 174\n175-{L}"), [2], [], "Grep of the doc, a context line"))
    add(case("c-grep-dir", "c", "transcript",
             c_grep({"pattern": "pinned", "path": RUN + "/gars/_references", "output_mode": "content"},
                    f"{DOC_ABS}:{L}"), [], [2], "Grep of a folder"))
    add(case("c-grep-other-file", "c", "transcript",
             c_grep({"pattern": "pinned", "path": RUN + "/notes.md", "output_mode": "content"}, L), [], [2],
             "Grep of another file"))
    # ---------------------------------------------------------------- round 3 (glitch-26's R3-1 to R3-3)
    # R3-1: every path binding is the one run-tree check (_resolves_to_doc)
    add(case("c-read-dotdot", "c", "transcript", c_read(RUN + "/gars/../../evil/_references/environment.md"), [],
             [2], "Read of a path with .. (it names the doc's suffix only)"))
    add(case("c-read-lookalike-tmp", "c", "transcript", c_read("/tmp/evil/_references/environment.md"), [], [2],
             "Read of an environment.md outside the run tree"))
    add(case("c-read-relative-lookalike", "c", "transcript", c_read("x/_references/environment.md"), [], [2],
             "Read of a relative look-alike"))
    add(case("c-grep-dotdot", "c", "transcript",
             c_grep({"pattern": "pinned", "path": RUN + "/gars/../gars/_references/environment.md",
                     "output_mode": "content", "-n": True}, f"175:{L}"), [], [2], "Grep of a path with .."))
    add(case("g-read-file-dotdot", "g", "session",
             [G_HEAD, G_USER, g_msg("msg-g1", [g_call("call-g1", "read_file",
                                                      {"file_path": RUN + "/gars/../gars/_references/environment.md"},
                                                      lines3)])], [], [3], "read_file of a path with .."))
    add(case("g-grep-lookalike-tree", "g", "session",
             g_grep_records({"pattern": "pinned", "dir_path": "/tmp/evil/gars/_references"}, [DOC_BLOCK],
                            FOUR[:3] + [g_match(175, L, "/tmp/evil/gars/_references/environment.md")],
                            replays=False), [], [3, 4],
             "grep_search over a look-alike tree outside the run tree, its display naming the same"))
    # R3-2: in labelled mode no label may come from a filename on disk
    # od57-line: a forged label is admitted only in front of the sha-pinned public bytes with nothing after them, and
    # the probe still rescans the whole record, so a forgery can reproduce the public line and nothing more
    add(case("t2-rgrep-newline-filename", "c", "transcript",
             c_bash("grep -rn Key gars", f"gars/x\ngars/_references/environment.md:175:{L}\n"), [2], [],
             "od57-line: the doc's label and :175:, a whole output line (was: grep -r over a folder, a filename "
             "holding a newline forges the doc's label)"))
    add(case("t2-rgrep-newline-filename-changed", "c", "transcript",
             c_bash("grep -rn Key gars", f"gars/x\ngars/_references/environment.md:176:{L}\n"), [], [2],
             "od57-line twin: one changed byte in the prefix (:176:)"))
    add(case("t2-rgrep-newline-filename-gemini", "g", "session",
             [G_HEAD, G_USER, g_msg("msg-g1", [g_call("call-g1", "run_shell_command",
                                                      {"command": "grep -rn Key gars", "description": "r"},
                                                      g_shell_out(f"gars/x\ngars/_references/environment.md:175:{L}"),
                                                      f"gars/x\ngars/_references/environment.md:175:{L}")])],
             [3], [], "od57-line: the same through Gemini's shell"))
    add(case("t2-rgrep-newline-filename-gemini-changed", "g", "session",
             [G_HEAD, G_USER, g_msg("msg-g1", [g_call("call-g1", "run_shell_command",
                                                      {"command": "grep -rn Key gars", "description": "r"},
                                                      g_shell_out(f"gars/x\ngars/_references/environment.md:176:{L}"),
                                                      f"gars/x\ngars/_references/environment.md:176:{L}")])],
             [], [3], "od57-line twin: the same through Gemini's shell, :176:"))
    add(case("t2-glob-operand", "c", "transcript",
             c_bash("grep -n Key gars/_references/* /dev/null", f"gars/_references/environment.md:175:{L}\n"),
             [2], [], "od57-line: the doc's label and :175:, a whole output line (was: a glob operand, the shell, "
                      "not the command, names the files)"))
    add(case("t2-glob-operand-second-key", "c", "transcript",
             c_bash("grep -n Key gars/_references/* /dev/null",
                    f"gars/_references/environment.md:175:{L}\ngars/_references/notes.md:3:{SECOND_PLACEHOLDER}\n"),
             [], [2], "od57-line twin: another rule on the line (a second key on the record: the probe refuses)"))
    # R3-3: T1 normalises the written path
    add(case("t1-write-dot-segment", "g", "session",
             [G_HEAD, G_USER, g_msg("msg-g0", [g_call("call-g0", "write_file",
                                                      {"file_path": RUN + "/gars/_references/./environment.md",
                                                       "content": "x"}, "ok")]),
              g_msg("msg-g1", [g_call("call-g1", "read_file", {"file_path": DOC_ABS}, lines3)])], [], [4],
             "write_file to _references/./environment.md, then read_file of the doc"))
    add(case("t1-claude-write-doubleslash", "c", "transcript",
             [c_use("toolu_W", "Write", {"file_path": RUN + "/gars/_references//environment.md", "content": "x"}),
              c_result("toolu_W", "ok")] + c_read(DOC_ABS), [], [4],
             "Write to _references//environment.md, then Read of the doc"))
    add(case("c-model-text", "c", "transcript",
             [{"type": "assistant", "message": {"content": [{"type": "text", "text": L}]}}], [], [1], "model text"))
    return cases


def dump(cases) -> bytes:
    return (json.dumps({"schema": 1, "placeholder": PLACEHOLDER, "cases": cases}, indent=1, ensure_ascii=False,
                       sort_keys=True) + "\n").encode()


def main(argv) -> int:
    data = dump(build())
    if argv == ["--write"]:
        os.makedirs(os.path.dirname(JSON_PATH), exist_ok=True)
        with open(JSON_PATH, "wb") as fh:
            fh.write(data)
        return 0
    if argv == ["--check"]:
        with open(JSON_PATH, "rb") as fh:
            return 0 if fh.read() == data else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
