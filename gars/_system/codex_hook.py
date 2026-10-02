#!/usr/bin/env python3
"""The Codex envelope for the GARS guard: one decision (`guard_hook.decide`), a second harness.

Wired by `.codex/hooks.json`, whose launcher finds this file from the git root Codex itself
walks from, and runs it with one mode argument (decision 0266):

    pre-tool-use    Codex sends {session_id, turn_id, transcript_path, cwd, hook_event_name,
                    model, permission_mode, tool_name, tool_input, tool_use_id} on stdin, plus
                    agent_id/agent_type inside a sub-agent. Shell calls arrive as `Bash`
                    {command}, edits as `apply_patch` {command: <raw patch>}. Each is
                    translated into the guard's own {tool_name, tool_input, cwd} shape and
                    judged by `decide`, with the root fixed to this file's own `gars/` folder.
    session-start   runs `_system/session_state.sh`, as Claude Code's SessionStart hook does.

Codex blocks a call on exit 2 with a non-empty stderr, the convention the guard already uses.
Everything else fails OPEN under Codex (an empty stderr, a crash, any other exit), so the only
exits here are 0 and 2-with-text: anything that cannot be judged is refused (R-098; owner
ruling 3A, decision 0058). That includes a guard that fails to import. This file holds no protected-path list and no shell rule of its own: every decision
is `decide`'s, so the two harnesses cannot drift apart.

Codex runs a shell command in a `workdir` it never tells the hook, so an allowed `Bash` call is
rewritten (`updatedInput`) to start with `cd -- <the folder the guard judged it in> && `.

Runs on stock python 3.6.8, stdlib only, like every `_system/` helper.
"""

import json
import os
import re
import shlex
import subprocess
import sys
try:  # inside the fail-closed net: a guard that cannot import refuses in main() (decision 0266)
    from guard_hook import decide, deny, UNREADABLE
    IMPORT_FAILURE = None
except BaseException as exc:  # SystemExit and KeyboardInterrupt included: nothing may exit 1
    IMPORT_FAILURE = "%s: %s" % (type(exc).__name__, str(exc)[:200])

GARS_ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

# Codex 0.154 built-in tools that touch no file, allowed as they are. Verified at tag
# rust-v0.154.0 under codex-rs/core/src/tools/; the hook name is the flat tool name
# (registry.rs:129-137, 799-808; mod.rs:40-54). A sub-agent's own tool calls run PreToolUse in
# its own session, with agent_id/agent_type added (core/src/hook_runtime.rs:184-196, 1018-1035;
# hooks/src/events/pre_tool_use.rs:175-181), so spawning one hands nothing past the guard.
PASS_TOOLS = (
    "update_plan",                 # handlers/plan.rs:50: the model's own task list, held in memory
    "request_user_input",          # handlers/request_user_input_spec.rs:9: asks the human a question
    "spawn_agent",                 # hook_names.rs:46-48 (v1, aliased) and multi_agents_v2/spawn.rs:33: starts a hooked sub-agent
    "multi_agent_v1send_input",    # multi_agents/send_input.rs:10, flattened by mod.rs:40-54: text to a sub-agent
    "multi_agent_v1wait_agent",    # multi_agents/wait.rs:32, flattened: waits for a sub-agent
    "multi_agent_v1resume_agent",  # multi_agents/resume_agent.rs:13, flattened: resumes a sub-agent
    "multi_agent_v1close_agent",   # multi_agents/close_agent.rs:10, flattened: closes a sub-agent
    "send_message",                # multi_agents_v2/send_message.rs:13: text to a sub-agent
    "followup_task",               # multi_agents_v2/followup_task.rs:13: a further task for a sub-agent
    "interrupt_agent",             # multi_agents_v2/interrupt_agent.rs:11: stops a sub-agent's turn
    "list_agents",                 # multi_agents_v2/list_agents.rs:11: lists sub-agents
    "wait_agent",                  # multi_agents_v2/wait.rs:24: waits for a sub-agent
)

PATCH_UNJUDGED = ("Blocked: the guard cannot judge this apply_patch call (%s), so it refuses it "
                  "(R-098; decisions 0042, 0266). Next: send one apply_patch call with "
                  "*** Begin Patch, Add/Update/Delete File entries naming workspace paths, and "
                  "*** End Patch, each line ending in a plain newline.")
APPLY_PATCH_NEXT = "Next: edit files with the apply_patch tool, not through the shell."

# ap_parser.rs:37-45 and ap_streaming.rs:19 (codex-rs/apply-patch/src/).
BEGIN_PATCH = "*** Begin Patch"
END_PATCH = "*** End Patch"
ADD_FILE = "*** Add File: "
DELETE_FILE = "*** Delete File: "
UPDATE_FILE = "*** Update File: "
MOVE_TO = "*** Move to: "
END_OF_FILE = "*** End of File"
CONTEXT = "@@ "
EMPTY_CONTEXT = "@@"
ENVIRONMENT_ID = "*** Environment ID:"
WRAPPERS = ("<<EOF", "<<'EOF'", '<<"EOF"')  # ap_parser.rs:242

# Rust's str::trim strips Unicode White_Space, which is not Python's str.strip set.
RUST_WHITESPACE = ("\t\n\x0b\x0c\r \x85\xa0        "
                   "        　")
# Line separators other than "\n" (Rust's lines() ends a line only at "\n"; Python and editors
# may end one at these): refused, so both sides always see the same lines.
OTHER_SEPARATORS = "\r\x0b\x0c\x1c\x1d\x1e\x85  "
SCHEME = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*:")
PATCH_WORD = re.compile(r"\b(?:apply_patch|applypatch)\b")


class PatchError(ValueError):
    pass


def rust_trim(text):
    return text.strip(RUST_WHITESPACE)


def rust_trim_end(text):
    return text.rstrip(RUST_WHITESPACE)


class Patch(object):
    """ap_streaming.rs's StreamingPatchParser, line for line (process_line at 175-379)."""

    def __init__(self):
        self.mode = "not_started"
        self.hunks = []  # dicts: kind, path, contents | move_path, chunks
        self.environment_id = None

    def ensure_update_not_empty(self):
        hunk = self.hunks[-1] if self.hunks else None
        if hunk is None or hunk["kind"] != "update":
            return
        if not hunk["chunks"] and self.mode == "update":
            raise PatchError("an Update File entry with no change")
        chunk = hunk["chunks"][-1] if hunk["chunks"] else None
        if chunk is not None and not chunk["old"] and not chunk["new"]:
            raise PatchError("an update chunk with no lines")

    def header(self, trimmed):
        if self.mode == "started" and trimmed.startswith(ENVIRONMENT_ID):
            if self.environment_id is not None or not rust_trim(trimmed[len(ENVIRONMENT_ID):]):
                raise PatchError("a repeated or empty Environment ID")
            self.environment_id = rust_trim(trimmed[len(ENVIRONMENT_ID):])
            return True
        if trimmed == END_PATCH:
            self.ensure_update_not_empty()
            self.mode = "ended"
            return True
        for marker, kind in ((ADD_FILE, "add"), (DELETE_FILE, "delete"), (UPDATE_FILE, "update")):
            if trimmed.startswith(marker):
                self.ensure_update_not_empty()
                self.hunks.append({"kind": kind, "path": trimmed[len(marker):], "contents": [],
                                   "move_path": None, "chunks": []})
                self.mode = kind
                return True
        return False

    def line(self, line):
        trimmed = rust_trim(line)
        if self.mode == "not_started":
            if trimmed != BEGIN_PATCH:
                raise PatchError("the first line is not *** Begin Patch")
            self.mode = "started"
        elif self.mode in ("started", "delete"):
            if not self.header(trimmed):
                raise PatchError("an unknown header line")
        elif self.mode == "add":
            if self.header(trimmed):
                return
            if not line.startswith("+"):
                raise PatchError("an Add File line that does not start with +")
            self.hunks[-1]["contents"].append(line[1:])
        elif self.mode == "update":
            self.update_line(line)
        elif trimmed:  # ended
            raise PatchError("text after *** End Patch")

    def update_line(self, line):
        update_line = rust_trim_end(line)
        if self.header(update_line):
            return
        hunk = self.hunks[-1]
        chunks = hunk["chunks"]
        last = chunks[-1] if chunks else None
        is_context = update_line == EMPTY_CONTEXT or update_line.startswith(CONTEXT)
        if last is not None and last["eof"]:
            if not update_line:
                return
            if not is_context:
                raise PatchError("a line after *** End of File that is not @@")
        if not chunks and hunk["move_path"] is None and update_line.startswith(MOVE_TO):
            hunk["move_path"] = update_line[len(MOVE_TO):]
            return
        if is_context and last is not None and not last["old"] and not last["new"]:
            raise PatchError("an @@ chunk with no lines")
        if is_context:
            chunks.append({"old": [], "new": [], "eof": False})
            return
        if update_line == END_OF_FILE:
            if last is not None and not last["old"] and not last["new"]:
                raise PatchError("*** End of File after no lines")
            if last is not None:
                last["eof"] = True
            return
        for prefix, sides in ((None, ("old", "new")), (" ", ("old", "new")),
                              ("+", ("new",)), ("-", ("old",))):
            if (line == "" if prefix is None else line.startswith(prefix)):
                if not chunks:
                    chunks.append({"old": [], "new": [], "eof": False})
                for side in sides:
                    chunks[-1][side].append(line[1:])
                return
        raise PatchError("an update line that is not context, +, - or @@")

    def finish_with(self, last_line):
        """ap_streaming.rs:154-173: the final line, which carries no newline."""
        if last_line:
            if rust_trim(last_line) == END_PATCH:
                self.ensure_update_not_empty()
                self.mode = "ended"
            else:
                self.line(last_line)
        if self.mode != "ended":
            raise PatchError("the last line is not *** End Patch")


def strict_boundaries(lines):
    """ap_parser.rs:215-274."""
    if not lines or rust_trim(lines[0]) != BEGIN_PATCH or rust_trim(lines[-1]) != END_PATCH:
        raise PatchError("missing *** Begin Patch or *** End Patch")
    return lines


def parse_patch(text):
    """ap_parser.rs parse_patch_text in lenient mode (193-254), then the streaming parser.
    Returns (hunks, environment_id); raises PatchError where Codex would, and also where
    Codex would read lines differently than this does (any separator other than "\\n")."""
    if any(ch in text for ch in OTHER_SEPARATORS):
        raise PatchError("a line separator other than a plain newline")
    trimmed = rust_trim(text)
    lines = trimmed.split("\n") if trimmed else []
    try:
        lines = strict_boundaries(lines)
    except PatchError:
        if not (len(lines) >= 4 and lines[0] in WRAPPERS and lines[-1].endswith("EOF")):
            raise
        lines = strict_boundaries(lines[1:-1])
    patch = Patch()
    for line in lines[:-1]:
        patch.line(line)
    patch.finish_with(lines[-1])
    return patch.hunks, patch.environment_id


def check_path(path):
    if not path:
        raise PatchError("an empty path")
    if any(ord(ch) < 0x20 or 0x7f <= ord(ch) <= 0x9f for ch in path):
        raise PatchError("a control character in a path")
    if SCHEME.match(path):
        raise PatchError("a scheme-prefixed path")
    return path


def patch_calls(command):
    """The guard calls one apply_patch stands for: Add -> Write, Update -> Edit,
    Delete -> Write of empty content, Move -> Edit of the source and Write of the destination."""
    hunks, environment_id = parse_patch(command)
    if environment_id is not None:
        raise PatchError("an Environment ID line names a filesystem the guard cannot see")
    if not hunks:
        raise PatchError("no file entries")
    calls = []
    for hunk in hunks:
        path = check_path(hunk["path"])
        if hunk["kind"] == "add":
            calls.append(("Write", {"file_path": path,
                                    "content": "".join(l + "\n" for l in hunk["contents"])}))
        elif hunk["kind"] == "delete":
            calls.append(("Unlink", path))
            calls.append(("Write", {"file_path": path, "content": ""}))
        else:
            old = "\n".join(l for c in hunk["chunks"] for l in c["old"])
            new = "\n".join(l for c in hunk["chunks"] for l in c["new"])
            if hunk["move_path"] is not None:
                calls.append(("Unlink", path))
            calls.append(("Edit", {"file_path": path, "old_string": old, "new_string": new}))
            if hunk["move_path"] is not None:
                calls.append(("Write", {"file_path": check_path(hunk["move_path"]),
                                        "content": new}))
    return calls


def refuse_link(path, cwd):
    """Delete File and a Move's source remove the path itself, while the guard judges the file a
    symlink points to (it resolves every path), so a link there is refused: judged by its
    target, a link at a machine-owned place would pass (review r1, R1-4; decision 0266)."""
    if os.path.islink(os.path.join(cwd, os.path.expanduser(path) if path.startswith("~/") else path)):
        deny("Blocked: %s is a symbolic link; the guard judges the file it points to, but deleting or moving it acts on the link itself, so it cannot judge this entry (R-098; decision 0266). Next: leave the link in place and ask the human if it must be removed." % path)


def guard_text(payload, root):
    """decide()'s verdict with its refusal text kept: None when allowed, else the text."""
    saved, sys.stderr = sys.stderr, _Capture()
    try:
        decide(payload, root)
        return None
    except SystemExit as exc:
        if exc.code != 2:
            raise
        return sys.stderr.text
    finally:
        sys.stderr = saved


class _Capture(object):
    def __init__(self):
        self.text = ""

    def write(self, text):
        self.text += text

    def flush(self):
        pass


def without_next(text):
    """The guard's refusal with its one `Next:` sentence removed (decision 0175: one per
    refusal); None when the text does not carry exactly one."""
    text = text.rstrip("\n")
    if text.count("Next: ") != 1:
        return None
    if text.startswith("Blocked: {"):
        try:
            record, end = json.JSONDecoder().raw_decode(text[len("Blocked: "):])
        except ValueError:
            return None
        if not isinstance(record, dict) or text[len("Blocked: ") + end:].strip():
            return None
        for key, value in record.items():
            if isinstance(value, str) and "Next: " in value:
                record[key] = value.split("Next: ", 1)[0].rstrip()
        return "Blocked: " + json.dumps(record, sort_keys=True)
    return text.split("Next: ", 1)[0].rstrip()


def run_bash(tool_input, cwd, root):
    command = tool_input.get("command")
    prefix = "cd -- " + shlex.quote(cwd) + " && "
    if isinstance(command, str) and command.startswith(prefix):
        command = command[len(prefix):]  # our own rewrite, coming back
    call = {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": cwd}
    if isinstance(command, str) and PATCH_WORD.search(command):
        text = guard_text(call, root)
        if text is not None:
            body = without_next(text)
            if body is None:
                deny("Blocked: a shell command that runs apply_patch is not a registered call (R-092; decision 0266). " + APPLY_PATCH_NEXT)
            deny(body + " " + APPLY_PATCH_NEXT)
    else:
        decide(call, root)
    if not isinstance(command, str):
        deny(UNREADABLE)
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                   "permissionDecision": "allow",
                                   "updatedInput": {"command": prefix + command}}}


def run(payload, root):
    """Deny (exit 2), or return None (allow) or a dict (allow + the rewrite JSON to print)."""
    if not isinstance(payload, dict):
        deny(UNREADABLE)
    name = payload.get("tool_name")
    tool_input = payload.get("tool_input")
    cwd = payload.get("cwd")
    if not isinstance(name, str) or not name or not isinstance(tool_input, dict) \
            or not isinstance(cwd, str) or not os.path.isabs(cwd):
        deny(UNREADABLE)
    workdir = tool_input.get("workdir")  # not forwarded by Codex 0.154; joined if it ever is
    if workdir is not None:
        if not isinstance(workdir, str):
            deny(UNREADABLE)
        cwd = os.path.join(cwd, workdir) if workdir else cwd
    if name == "Bash":
        return run_bash(tool_input, cwd, root)
    if name == "apply_patch":
        command = tool_input.get("command")
        if not isinstance(command, str):
            deny(UNREADABLE)
        try:
            calls = patch_calls(command)
        except PatchError as exc:
            deny(PATCH_UNJUDGED % exc)
        for tool, guard_input in calls:
            if tool == "Unlink":
                refuse_link(guard_input, cwd)
                continue
            decide({"tool_name": tool, "tool_input": guard_input, "cwd": cwd}, root)
        return None
    if name == "view_image":
        path = tool_input.get("path")
        if not isinstance(path, str) or not path:
            deny(UNREADABLE)
        if tool_input.get("environment_id"):  # view_image.rs:58-63: another executor's files
            deny("Blocked: this view_image names another environment's filesystem, which the guard cannot see (R-098; decision 0266). Next: view the image from this session's own workspace, without environment_id.")
        decide({"tool_name": "Read", "tool_input": {"file_path": path}, "cwd": cwd}, root)
        return None
    if name in PASS_TOOLS:
        return None
    deny("The guard cannot judge Codex tool %s (R-098, decision 0266). Next: use a read-only shell command or the typed call the stage contract names." % re.sub(r"[^A-Za-z0-9_.:-]", "?", name)[:120])


def session_start():
    """Claude Code's SessionStart hook, in Codex's shape: the state render passes through as
    context; a pin failure (session_state.sh exits 2) stops the first turn with its reason."""
    try:
        proc = subprocess.Popen(["bash", os.path.join(GARS_ROOT, "_system", "session_state.sh")],
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, cwd=GARS_ROOT)
        out, err = proc.communicate()
        if proc.returncode == 2:
            print(json.dumps({"continue": False,
                              "stopReason": err.decode("utf-8", "replace").strip()}))
        else:
            sys.stdout.buffer.write(out)
            sys.stdout.flush()
    except SystemExit:
        raise
    except BaseException as exc:
        print(json.dumps({"continue": False, "stopReason": "GARS state (Codex) failed to render (%s: %s), so the guard's state is unknown (R-098; decision 0266). Next: stop and ask the human to run bash _system/session_state.sh in their own terminal." % (type(exc).__name__, str(exc)[:200])}))
    sys.exit(0)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if IMPORT_FAILURE is not None:
        text = ("Blocked: the GARS guard could not be loaded (%s), so it cannot tell whether the "
                "call is safe (R-098; decision 0266). Next: stop and ask the human to restore "
                "_system/guard_hook.py from the repository." % IMPORT_FAILURE)
        if mode == "session-start":
            print(json.dumps({"continue": False, "stopReason": text}))
            sys.exit(0)
        sys.stderr.write(text + "\n")
        sys.exit(2)
    if mode == "session-start":
        session_start()
    try:
        if mode != "pre-tool-use":
            deny("Blocked: the Codex hook was started without a known mode, so it cannot judge this call (R-098; decision 0266). Next: restore gars/.codex/hooks.json from the repository and retry.")
        try:
            payload = json.loads(sys.stdin.buffer.read().decode("utf-8"))
        except ValueError:  # includes UnicodeDecodeError
            deny(UNREADABLE)
        out = run(payload, GARS_ROOT)
        if out is not None:
            print(json.dumps(out))
            sys.stdout.flush()
        sys.exit(0)
    except SystemExit:
        raise
    except BaseException as exc:
        deny("Blocked: GARS guard (Codex) failed while checking this call (%s: %s), so it cannot tell whether the call is safe (R-098; decision 0042). Next: retry the call; if this keeps happening, stop and report the defect in _system/codex_hook.py." % (type(exc).__name__, str(exc)[:200]))


if __name__ == "__main__":
    main()
