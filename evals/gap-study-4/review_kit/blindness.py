#!/usr/bin/env python3
"""The blindness of a review, read from the reviewer's own session file, written so the output can be committed.

    python3 evals/gap-study-4/review_kit/blindness.py <review folder>

Two questions, kept apart. (1) Did the operator's own material reach the reviewer's loaded context? Markers that
exist only in the operator's assistant tree are searched in the attachment records. (2) Did the reviewer read outside
its folder? Every absolute path in its tool inputs is listed unless it is inside the folder.

The markers name this round (`gap-study-4`, `round 4`, and `gap4`, the operator's shorthand for it), the rounds
before it whose names operator memory still carries (`gars-eval-v4` / `gap-study-3` / `round 3`, `gars-eval-v3` /
`gap-study-2` / `round 2`, and the pre-study `gars-haiku-prestudy` / `haiku-prestudy`), the operator's coordinating
session and its boards (`lane-orchestrator`, `Lane Board`, `OrgOS`), the operator's open-items list, the assistant's
memory and identity files, the operator's objective line, and this repository's own path, taken from this file's
location rather than typed. The account email is matched by EMAIL.

ROUND 4 (lane review-kit-port). The markers were round 3's; they now lead with round 4's names and keep every earlier
one. The coordinating session's name is also the name of a skill in the operator's own home folder, so a reviewer
that boots with that skill in its loaded context reads it as UNEXPLAINED here, which is what it is. No marker word
occurs in any CLAUDE.md this repository tracks (tests/test_review_kit.py K3), so a nested instruction file the
harness attaches as the reviewer reads `study/` cannot raise one.

LANE BLINDNESS-SIDECHAINS (the Lane-orchestrator's ruling of Sat 24 Oct 2026, under Javier's standing delegation).
Pre-freeze round 1's record read 45 UNEXPLAINED hits, every one inside a sub-agent's hand-back, and this file had
never read the sub-agents' own sessions. It now reads every sidechain session the reviewer's session spawned: the
records the client marks isSidechain, and `<session>/subagents/agent-<id>.jsonl`, matched to the Agent tool's
results (a launched agent with no session file and a session file no launch names are both stated). Each one gets
the same markers and the same absolute-path scan as the reviewer. A hand-back, whichever record carries it (a user
message, a queued command, a task notification or a synchronous tool result), is read on its own: a hit there is
explained only when the word or path it sits in occurs in a file that was in the folder at launch and that no
session wrote, and in that sub-agent's own tool traffic, so the sub-agent read it there. An operator row (OPERATOR
and the two path rows) is never explained, in a hand-back or anywhere else. Writes outside the folder are listed in
their own section and void nothing by themselves, and the last section states what the sub-agents' records show of
the reviewer's isolation.

THE REVIEW OF 5a6dc21 (CHANGES), folded on the Lane-orchestrator's rulings the same day. The folder is the folder as
it stood at launch: launch.py's per-file manifest when there is one, otherwise the files no newer than the launch
stamp that no session wrote by any tool, the shell included; the record names which rule ran. A path tail must still
hold the marker it explains. "Read it there" means a tool result the sub-agent received, never its own input, or a
report a nested agent of its own handed it and read the same way; a nested session that is missing explains
nothing. A report read through another tool (TaskOutput, or its tasks/<id>.output file) is a hand-back, read once;
an Agent result that names no agent is listed and stays UNEXPLAINED. A hit the sub-agent did not read but its brief
holds is traced via brief only when it is in the folder at launch, and section 4 prints it apart. A shell step
writes only its targets, read against the cwd it runs in: never a copy's sources or the program it runs. A record
kept twice, and a rendered form that reflows its prompt, are read once. Task notifications are listed apart from the
reports. A study word is traced by
its word alone, so a word the study's own files also hold passes even when the sub-agent met it elsewhere: the
ruling's own limit, and why the operator rows are refused outright.

stdlib only. Never prints a path or an address unmasked.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
MARKERS = [
    ("the study's folder name", "gap-study-4"),
    ("the round's name", "round 4"),
    ("the round's shorthand", "gap4"),
    ("round 3's goal id", "gars-eval-v4"),
    ("round 3's folder name", "gap-study-3"),
    ("round 3's name", "round 3"),
    ("round 2's goal id", "gars-eval-v3"),
    ("round 2's folder name", "gap-study-2"),
    ("round 2's name", "round 2"),
    ("the pre-study's goal id", "gars-haiku-prestudy"),
    ("the pre-study's folder name", "haiku-prestudy"),
    ("the operator's coordinating session", "lane-orchestrator"),
    ("the operator's lane board", "Lane Board"),
    ("the operator's list system", "OrgOS"),
    ("the operator's open-items list", "Waiting on Javier"),
    ("the assistant's memory folder", "glitch-mem"),
    ("the assistant's identity file", "SOUL.md"),
    ("the operator's objective line", "north star"),
    ("the operator's memory file", "MEMORY.md"),
]
ACCOUNT = re.compile(r"javrodher|rodrij92|javier", re.I)
PROJECTS = Path.home() / ".claude" / "projects"
# The operator's own Brain, by path, derived like REPO rather than typed in full.
BRAIN = Path.home() / "glitch"
# Ruling 2 of lane blindness-sidechains: these name the operator's side, never the study, so no folder, report or
# hand-back can explain a hit on one. The two path rows below are operator rows too.
OPERATOR = {"lane-orchestrator", "Lane Board", "OrgOS", "Waiting on Javier", "glitch-mem", "SOUL.md", "north star",
            "MEMORY.md"}
AGENT_TOOLS = ("Agent", "Task")
WRITE_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")
ABS_PATH = re.compile(r"(/(?:Users|private|var|tmp|home|etc|opt)[^\s\"'`]*)")
AGENT_MESSAGE = re.compile(r'<agent-message from="([^"]+)">')
TASK_ID = re.compile(r"<task-notification>.*?<task-id>([^<\s]+)</task-id>", re.S)
LAUNCHED_ID = re.compile(r"agentId: (\w+)")
# A sub-agent's report file, as the client names it in a task notification.
TASK_OUTPUT = re.compile(r"tasks/(\w+)\.output")
# launch.py's per-file record of the folder at launch (round 2 on): `<sha256>  <path under the folder>` per line.
MANIFEST = "folder-manifest.txt"
# The round register, whose input_sha256 a manifest must reproduce to bind anything.
REGISTER = HERE / "rounds.json"
# A shell command that writes, by its own text: a redirect (never 2>&1 or a here-document), or a verb that writes.
# The shell's own operators, read outside quotes only (shlex): the ones that write their next word, the ones that
# read it or duplicate a descriptor (that word is skipped), and the ones that end a step.
REDIRECTS = {">", ">>", "&>", "&>>", ">|"}
READS_NEXT = {"<", "<<", "<<<", "<&", ">&", "<>", "<<-"}
STEP_BREAKS = {";", "&&", "||", "|", "&", "\n", ";;", "(", ")", "|&"}
# A here-document's body, from its opening line to its terminator: data, not steps.
HEREDOC = re.compile(r"(<<-?\s*['\"]?(\w+)['\"]?[^\n]*)\n.*?\n\s*\2\s*(?=\n|$)", re.S)
# Programs whose -o is never an output path.
READERS = {"grep", "egrep", "fgrep", "rg", "ls", "find", "head", "tail", "cut", "wc", "diff", "cat", "awk", "du",
           "df", "ps", "file", "stat"}
# The characters a quoted word or path is made of, for the extent of a hit inside a hand-back.
EXTENT = re.compile(r"[a-z0-9_.\-/~']")


def rows() -> list[tuple[str, str, bool]]:
    """(label, word, operator) for every row of a marker table, the two path rows last."""
    return ([(label, w, w in OPERATOR) for label, w in MARKERS]
            + [("this repository, by path", str(REPO), True), ("the operator's Brain, by path", str(BRAIN), True)])


def mask(s: str, folder: str) -> str:
    s = s.replace(folder, "<review folder>").replace("/private" + folder, "<review folder>")
    s = s.replace(str(REPO), "<repo>").replace(str(Path.home()), "<home>")
    s = re.sub(r"/private/tmp/claude-\d+/\S*", "<harness task folder>", s)
    s = EMAIL.sub("<account email>", s)
    return ACCOUNT.sub("<account>", s)


def session_file(sid: str, projects: Path = PROJECTS) -> Path:
    hits = sorted(projects.glob(f"*/{sid}.jsonl"))
    if len(hits) != 1:
        raise SystemExit(f"session file for the reviewer: {len(hits)} found, cannot read blindness")
    return hits[0]


def classify_hits(ctx_lines: list[str], word: str, folder: Path,
                  operator: bool = False) -> tuple[int, int, int, int]:
    """Every occurrence of `word` in the loaded context, split by what put it there.

    Returns (total, in the reviewer's own report, inside the folder's own path, unexplained).

    ROUND 3, RULING 6. Round 2 counted totals, and on this round's first review every study-name marker
    read nonzero for two reasons that say nothing about blindness. The review folder is named for the
    round, and the harness echoes the working directory through its own furniture -- the environment
    record, the token reminders, the session context -- so the round's name is in the context before the
    reviewer has read anything. And the reviewer's own report is attached back into its context as it
    writes, so every study name it types returns as a hit against itself.

    Both recur in every round, so a rule read on the totals could never pass, and a round voided for it
    would void its re-run too. What the rule means is: did anything put this word there that was not the
    reviewer's own work and not the folder it was handed. That is the unexplained count.

    Lane blindness-sidechains, ruling 2: an operator row is never explained, whatever sits beside it.
    """
    own = fp = un = total = 0
    marker = word.lower()
    folder_name = folder.name.lower()
    parent_name = folder.parent.name.lower()
    for line in ctx_lines:
        try:
            kind = ((json.loads(line).get("attachment") or {}).get("type")) or ""
        except json.JSONDecodeError:
            kind = ""
        low = line.lower()
        for m in re.finditer(re.escape(marker), low):
            total += 1
            window = low[max(0, m.start() - 60):m.end() + 60]
            if operator:
                un += 1
            elif kind == "edited_text_file":
                own += 1
            elif parent_name in window or folder_name in window:
                fp += 1
            else:
                un += 1
    return total, own, fp, un


def leaves(x) -> list[str]:
    """Every string inside a JSON value."""
    if isinstance(x, str):
        return [x]
    if isinstance(x, dict):
        return [s for v in x.values() for s in leaves(v)]
    if isinstance(x, list):
        return [s for v in x for s in leaves(v)]
    return []


def squash(s: str) -> str:
    """A text with its whitespace runs made one space, so a reflowed copy reads as the same text."""
    return " ".join(s.split())


def inside(p: str, folder: Path) -> bool:
    f = str(folder)
    return any(p == base or p.startswith(base + "/") for base in (f, "/private" + f))


def handback_from(text: str) -> tuple[str, str] | None:
    """(agent, kind) when a record's text hands back from an agent: a report, or a task notification."""
    m = AGENT_MESSAGE.search(text)
    if m:
        return m.group(1), "report"
    m = TASK_ID.search(text)
    return (m.group(1), "notification") if m else None


class Session:
    """One session file's records, read the same way for the reviewer and for each of its sub-agents.

    The context is its attachment records less the hand-backs, which are read on their own (section 4). What it
    received is the text of the tool results it was given, less the ones that are another agent's report: that is
    what it read. Its own tool inputs are kept apart and never count as read (review of 5a6dc21, finding 5).
    A record seen twice is read once: by its uuid, and an inline copy of a subagents/ file record without one by its
    content (read_sessions). Records without a uuid inside one file are each read: the client repeats its own.
    """

    def __init__(self, name: str, lines: list[str], folder: Path):
        self.name, self.n, self.ctx, self.inputs = name, 0, [], []
        self.launches: dict[str, str] = {}
        self.noid: list[str] = []
        self.calls: dict[str, dict] = {}
        self.pending: list[tuple[str, str]] = []
        self.results: list[str] = []
        self.handbacks: list[tuple[str, str, str]] = []
        self.written_inside: set[str] = set()
        self.writes: set[str] = set()
        self.skills: tuple[str, ...] | None = None
        self.workflow = self.mcp = self.memory_outside = 0
        self.traffic = ""
        agent_calls: set[str] = set()
        seen: set[str] = set()
        for line in lines:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            key = rec.get("uuid")
            if key and key in seen:
                continue
            if key:
                seen.add(str(key))
            self.n += 1
            kind = rec.get("type")
            if kind == "attachment":
                a = rec.get("attachment") or {}
                if a.get("type") == "queued_command":
                    # The client keeps one message up to three times on this record: the prompt, its origin and
                    # the rendered form the model was shown. The shown form is read once, the prompt only when
                    # the shown form does not hold it, whitespace aside.
                    text = "\n".join(leaves(a.get("prompt")))
                    shown = "\n".join(leaves(rec.get("rendered")))
                    if squash(text) not in squash(shown):
                        shown = (shown + "\n" + text).strip()
                    hb = handback_from(shown)
                    if hb:
                        self.handbacks.append((hb[0], shown, hb[1]))
                        continue
                self.ctx.append(line)
                if a.get("type") == "skill_listing":
                    self.skills = tuple(sorted(re.findall(r"^- ([^:\n]+):", str(a.get("content") or ""), re.M)))
                if a.get("type") == "deferred_tools_delta":
                    names = [str(n) for n in a.get("addedNames") or []]
                    self.workflow += names.count("Workflow")
                    self.mcp += sum(n.startswith("mcp__") for n in names)
                if a.get("type") in ("nested_memory", "claude_md") and a.get("path") \
                        and not inside(str(a["path"]), folder):
                    self.memory_outside += 1
            elif kind == "assistant":
                for b in (rec.get("message") or {}).get("content") or []:
                    if not (isinstance(b, dict) and b.get("type") == "tool_use"):
                        continue
                    name, inp = str(b.get("name") or ""), b.get("input") or {}
                    self.inputs.append(json.dumps(inp))
                    self.calls[str(b.get("id"))] = inp
                    self.workflow += name == "Workflow"
                    self.mcp += name.startswith("mcp__")
                    if name in AGENT_TOOLS:
                        agent_calls.add(str(b.get("id")))
                    self.note_writes(name, inp, folder, rec.get("cwd"))
            elif kind == "user":
                content = (rec.get("message") or {}).get("content")
                blocks = [{"type": "text", "text": content}] if isinstance(content, str) else content or []
                tur = rec.get("toolUseResult") if isinstance(rec.get("toolUseResult"), dict) else {}
                for b in blocks:
                    if not isinstance(b, dict):
                        continue
                    if b.get("type") == "tool_result":
                        body = "\n".join(leaves(b.get("content")))
                        tid = str(b.get("tool_use_id"))
                        if tid in agent_calls:
                            self.agent_result(tid, body, tur)
                        else:
                            self.pending.append((tid, body))
                    elif b.get("type") == "text":
                        hb = handback_from(str(b.get("text") or ""))
                        if hb:
                            self.handbacks.append((hb[0], str(b.get("text")), hb[1]))

    def agent_result(self, tid: str, body: str, tur: dict) -> None:
        """An Agent tool result: the launch of a named agent, or a foreground agent's report. One that names no
        agent is listed and read as a report from no session, so its hits stay UNEXPLAINED (finding 4)."""
        m = LAUNCHED_ID.search(body)
        aid = str(tur.get("agentId") or (m.group(1) if m else ""))
        if not aid:
            self.noid.append(tid)
            self.handbacks.append((f"(no agent id, {tid})", body, "report"))
            return
        self.launches[tid] = aid
        if tur.get("status") != "async_launched" and "Async agent launched" not in body:
            self.handbacks.append((aid, body, "report"))

    def resolve(self, ids: set[str]) -> None:
        """Once every agent id is known: a tool result whose call names an agent, or its tasks/<id>.output file
        (TaskOutput, a Read or a cat of it), is that agent's report, read once; every other result is received."""
        for tid, body in self.pending:
            strs = leaves(self.calls.get(tid, {}))
            out = [m.group(1) for x in strs for m in TASK_OUTPUT.finditer(x)]
            named = [i for i in sorted(ids) if any(re.search(rf"(?<!\w){re.escape(i)}(?!\w)", x) for x in strs)]
            aid = (out or named or [None])[0]
            if aid:
                self.handbacks.append((aid, body, "report"))
            else:
                self.results.append(body)
        self.traffic = "\n".join(self.results).lower()

    def note_writes(self, name: str, inp: dict, folder: Path, cwd: str | None = None) -> None:
        if name in WRITE_TOOLS:
            p = str(inp.get("file_path") or inp.get("notebook_path") or "")
            if p and inside(p, folder):
                self.written_inside.add(str(Path(p).resolve()))
            elif p:
                self.writes.add(p)
        elif name == "Bash":
            # The closure review of fff7e0d3, findings 1 and 2: the step's cwd starts at the record's own cwd and
            # follows every cd, and a relative target is read against it, inside the folder as well as outside.
            for words, redirected in shell_steps(str(inp.get("command") or "")):
                if words[:1] in (["cd"], ["pushd"]):
                    to = words[1] if len(words) > 1 else ""
                    cwd = (to if to.startswith("/") else os.path.normpath(os.path.join(cwd, to)) if cwd and to
                           and not to.startswith(("~", "-", "$")) else None)
                    continue
                for t, is_dir in shell_targets(words, redirected):
                    self.note_shell_write(t, is_dir, cwd, folder)

    def note_shell_write(self, t: str, is_dir: bool, cwd: str | None, folder: Path) -> None:
        """One target a shell step writes. Inside the folder it leaves the corpus (a target that is a folder, named
        so or already one, with all it holds); outside it is listed in section 6. A folder made by mkdir is listed
        but never takes a launch file with it."""
        if t.startswith("~") or not t:
            return
        if "$" in t or "*" in t:
            # A name the shell expands: where it lands is not in the text, so the folder it is written in stands for it.
            t, is_dir = (os.path.dirname(t.split("$")[0].split("*")[0]) or ".", True) if not t.startswith(("$", "*")) \
                else (".", True)
        p = t if t.startswith("/") else (os.path.normpath(os.path.join(cwd, t)) if cwd else None)
        if not p or p.startswith("/dev/"):
            return
        p = p.rstrip(").,:;\\") or p
        if inside(p, folder):
            if is_dir is not None:
                self.written_inside.add(str(Path(p).resolve()) if Path(p).exists() else os.path.normpath(p))
        else:
            self.writes.add(p)


def shell_steps(cmd: str) -> list[tuple[list[str], list[str]]]:
    """A shell command's steps, each (its words, the words its redirects write), split by the shell's own rules:
    quotes are honoured, so a `|` or `>` inside a quoted pattern is text, and a here-document's body is data. A
    command the shell itself could not split (an open quote) yields no steps (the closure review of fff7e0d3)."""
    lex = shlex.shlex(HEREDOC.sub(r"\1", cmd), posix=True, punctuation_chars="();<>|&\n")
    lex.whitespace = " \t\r"
    lex.whitespace_split = True
    try:
        tokens = list(lex)
    except ValueError:
        return []
    steps, words, written, i = [], [], [], 0
    while i < len(tokens):
        t = tokens[i]
        if t in STEP_BREAKS or (t and set(t) <= set("();|&\n")):
            steps.append((words, written))
            words, written = [], []
        elif t in REDIRECTS or t in READS_NEXT:
            if words and words[-1].isdigit():
                words.pop()
            if t in REDIRECTS and i + 1 < len(tokens) and tokens[i + 1] not in STEP_BREAKS:
                written.append(tokens[i + 1])
            i += 1
        else:
            words.append(t)
        i += 1
    steps.append((words, written))
    return [(w, r) for w, r in steps if w or r]


def shell_targets(words: list[str], redirected: list[str]) -> list[tuple[str, bool | None]]:
    """What one shell step writes, by its own text: (target, is it a folder; None for a folder mkdir makes).

    Redirects (`>`, `>>`, `&>`, `2>`) write their target; a cp or mv writes its destination (into a folder, each
    source's name there), rsync, tar -x and unzip their destination folder (-C, -d, or the cwd), tee and touch their
    files, sed -i its file, ln and install their last argument, git clone, worktree and init theirs, and any program
    that is not a reader its --out, --output or -o argument. Never a copy's sources, never the program a step runs.
    """
    out: list[tuple[str, bool | None]] = [(t, False) for t in redirected]
    while words and (words[0] in ("sudo", "env", "nohup", "time", "command")
                     or ("=" in words[0] and not words[0].startswith("-"))):
        words = words[1:]
    if words[:1] == ["timeout"]:
        words = words[2:]
    if not words:
        return out
    verb, args = os.path.basename(words[0]), words[1:]
    plain = [a for a in args if not a.startswith("-")]
    if verb in ("cp", "mv") and len(plain) >= 2:
        dest = plain[-1]
        if len(plain) > 2 or dest.endswith("/") or dest in (".", ".."):
            out += [(dest.rstrip("/") + "/" + os.path.basename(src.rstrip("/")), True) for src in plain[:-1]]
        else:
            out.append((dest, False))
    elif verb == "rsync" and len(plain) >= 2:
        out.append((plain[-1], True))
    elif verb in ("ln", "install") and plain:
        out.append((plain[-1], False))
    elif verb in ("tee", "touch"):
        out += [(a, False) for a in plain]
    elif verb == "mkdir":
        out += [(a, None) for a in plain]
    elif verb == "sed" and any(a.startswith("-i") for a in args) and plain:
        out.append((plain[-1], False))
    elif verb == "tar" and ("--extract" in args or any(a.startswith("-") and not a.startswith("--") and "x" in a
                                                       for a in args) or (args and "x" in args[0])):
        out.append((args[args.index("-C") + 1] if "-C" in args[:-1] else ".", True))
    elif verb == "unzip":
        out.append((args[args.index("-d") + 1] if "-d" in args[:-1] else ".", True))
    elif verb == "git" and args[:1] and args[0] in ("clone", "worktree", "init") and plain:
        out.append((plain[-1], True))
    if verb not in READERS:
        for i, a in enumerate(args):
            if a in ("-o", "--out", "--output") and i + 1 < len(args):
                out.append((args[i + 1], False))
            elif a.startswith(("--out=", "--output=")):
                out.append((a.split("=", 1)[1], False))
    return out


def outside_paths(s: Session, folder: Path) -> set[str]:
    """The absolute paths in a session's tool inputs that are not inside its folder (round 3's scan, unchanged)."""
    outside = set()
    for t in s.inputs:
        for m in ABS_PATH.finditer(t):
            p = m.group(1)
            if str(folder) in p or ("/private" + str(folder)) in p:
                continue
            if "\\" in p or "|" in p:
                outside.add("(a search pattern the reviewer used on its own report, not a path it read)")
                continue
            outside.add(mask(p, str(folder))[:120])
    return outside


def read_sessions(main: Path, folder: Path) -> tuple[Session, dict[str, Session]]:
    """The reviewer's session and every sidechain session it spawned, as the client writes them: records marked
    isSidechain inside the session file, and `<session>/subagents/agent-<id>.jsonl` beside it."""
    own, inline = [], {}
    for line in main.read_text(errors="replace").splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            own.append(line)
            continue
        if rec.get("isSidechain") and rec.get("agentId"):
            inline.setdefault(str(rec["agentId"]), []).append(line)
        else:
            own.append(line)
    files = {}
    for f in sorted((main.parent / main.stem / "subagents").glob("agent-*.jsonl")):
        files[f.stem[len("agent-"):]] = f.read_text(errors="replace").splitlines()
    def bare(line: str) -> str:
        """A record's content less the two keys an inline copy adds."""
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            return line
        return json.dumps({k: v for k, v in rec.items() if k not in ("isSidechain", "agentId")}, sort_keys=True)

    for aid, lines in inline.items():
        in_file = {bare(x) for x in files.get(aid, [])}
        inline[aid] = [x for x in lines if bare(x) not in in_file]
    side = {aid: Session(aid, files.get(aid, []) + inline.get(aid, []), folder)
            for aid in sorted(set(files) | set(inline))}
    reviewer = Session("the reviewer", own, folder)
    ids = set(side) | {aid for s in (reviewer, *side.values()) for aid in s.launches.values()}
    for s in (reviewer, *side.values()):
        s.resolve(ids)
    return reviewer, side


# PRE-FREEZE REVIEW 5, M1 (lane fold5/report-binding; glitch-45's ruling 1, Sat 31 Oct 2026, under Javier's standing
# delegation): the report is bound to the bytes the reviewer's own session wrote. The record states the sha256 of the
# report rebuilt from the session file alone: its Write of the report, then its Edits and MultiEdits in order, each one
# the session's result names a success. Nothing is recorded, and the record says why, when the rebuild is not exact: a
# write the session file does not show whole (a content or edit text that is not a string, a NotebookEdit, a result it
# does not hold, an Edit whose old text is not in the report exactly once), any shell step that names the report and is
# not a recognised pure read (PURE_READS, sed -n, awk with no > or -i inplace), a shell write the text cannot place in its folder, or a sub-agent that
# writes it. commit_review.py re-runs the record from the session itself and freeze.registered_review_problem reads the
# line by REPORT_DIGEST; the record also states the session file's sha256, so a later audit can re-read the same bytes.
REPORT_DIGEST = "report sha256, as the reviewer's session wrote it: "
REPORT_UNBOUND = "report sha256, as the reviewer's session wrote it: NOT RECORDED, "
REPORT_NAME = re.compile(r"prefreeze-(\d+)\.md")


def recorded_report_digest(text: str) -> str | None:
    """The 64-hex digest a blindness record states for its report, or None (none, several, or NOT RECORDED)."""
    got = re.findall(rf"^{re.escape(REPORT_DIGEST)}([0-9a-f]{{64}})$", text, re.M)
    return got[0] if len(got) == 1 else None


def _names_report(p: str, cwd: str | None, report: Path) -> bool:
    if not p:
        return False
    if not p.startswith("/"):
        if not cwd:
            return False
        p = os.path.join(cwd, p)
    p = os.path.normpath(p)
    r = os.path.normpath(str(report))
    return p in (r, "/private" + r) or os.path.realpath(p) == os.path.realpath(r)


# The shell steps that only read a file they name (the review of f3ae7772, m1: fail closed). Any other step that names the
# report's file name, and any step whose writes the text cannot place (a glob, a variable, no known cwd) into the
# report's folder, leaves the report NOT RECORDED: python3 -c open(...,'a'), perl -pi, dd of=, truncate, git checkout,
# bash -c '... >>' and an mv of a glob into the folder all write it in ways the text alone does not show.
PURE_READS = {"cat", "head", "tail", "grep", "egrep", "fgrep", "rg", "wc", "shasum", "sha256sum", "ls", "diff", "sort", "less",
              "more", "uniq", "cut", "nl", "stat", "file"}   # and awk, when its command holds no > and no -i inplace


def shell_touches_report(cmd: str, cwd: str | None, report: Path) -> str | None:
    """Why one Bash command may write the report (fail closed), or None when every step that names it only reads."""
    name, folder = report.name, os.path.normpath(str(report.parent))
    steps = shell_steps(cmd)
    if not steps:
        return "a shell command the shell's own rules cannot split names the report" if name in cmd else None
    for words, redirected in steps:
        if words[:1] in (["cd"], ["pushd"]):
            to = words[1] if len(words) > 1 else ""
            cwd = (to if to.startswith("/") else os.path.normpath(os.path.join(cwd, to)) if cwd and to
                   and not to.startswith(("~", "-", "$")) else None)
            continue
        for t, _is_dir in shell_targets(list(words), list(redirected)):
            if _names_report(t, cwd, report):
                return "a shell step writes the report"
            if any(c in t for c in "*?$[") or (not t.startswith("/") and cwd is None):
                where = os.path.dirname(t) or "."
                where = where if where.startswith("/") else (os.path.normpath(os.path.join(cwd, where)) if cwd else None)
                if where is None or os.path.normpath(where) == folder or name.split(".")[0] in t:
                    return "a shell step writes a name the text does not place, in the report's folder"
        if any(name in w for w in words) or any(name in w for w in redirected):
            verb = os.path.basename(words[0]) if words else ""
            pure = (verb in PURE_READS or (verb == "sed" and "-n" in words and not any(w.startswith("-i") for w in words))
                    or (verb in ("awk", "gawk") and ">" not in cmd and "inplace" not in cmd))
            if not pure:
                return f"a shell step that is not a recognised read ({verb or 'a redirect'}) names the report"
    return None


def written_report(lines: list[str], report: Path, side_writes: set[str] | None = None) -> tuple[str | None, str]:
    """(the report's text as the session wrote it, "") or (None, why it cannot be rebuilt exactly). `lines` is the
    reviewer's own session file; `side_writes` the paths its sub-agents' sessions wrote (Session.written_inside)."""
    real = os.path.realpath(str(report))
    if side_writes and any(os.path.realpath(w) == real for w in side_writes):
        return None, "a sub-agent's session writes the report"
    ops, results, seen = [], {}, set()
    for line in lines:
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(rec, dict):
            continue
        key = rec.get("uuid")
        if key and key in seen:
            continue
        if key:
            seen.add(str(key))
        content = (rec.get("message") or {}).get("content") if isinstance(rec.get("message"), dict) else None
        if rec.get("type") == "user" and isinstance(content, list):
            for b in content:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    results[str(b.get("tool_use_id"))] = bool(b.get("is_error"))
        if rec.get("type") != "assistant" or not isinstance(content, list):
            continue
        for b in content:
            if not (isinstance(b, dict) and b.get("type") == "tool_use"):
                continue
            name, inp, tid = str(b.get("name") or ""), b.get("input") or {}, str(b.get("id"))
            if not isinstance(inp, dict):
                continue
            if name in WRITE_TOOLS and _names_report(str(inp.get("file_path") or inp.get("notebook_path") or ""),
                                                     rec.get("cwd"), report):
                if rec.get("isSidechain"):
                    return None, "a sub-agent's record writes the report"
                ops.append((name, inp, tid))
            elif name == "Bash":
                why = shell_touches_report(str(inp.get("command") or ""), rec.get("cwd"), report)
                if why:
                    return None, why
    text = None
    for name, inp, tid in ops:
        if tid not in results:
            return None, f"the session file holds no result for its {name} of the report"
        if results[tid]:
            continue                                         # a failed write changed nothing
        if name == "Write":
            if not isinstance(inp.get("content"), str):
                return None, "a Write of the report the session file does not show whole"
            text = inp["content"]
            continue
        if name not in ("Edit", "MultiEdit") or text is None:
            return None, f"a {name} of the report the session file does not rebuild exactly"
        edits = [inp] if name == "Edit" else inp.get("edits")
        if not isinstance(edits, list):
            return None, "a MultiEdit of the report the session file does not show whole"
        for e in edits:
            old, new = (e.get("old_string"), e.get("new_string")) if isinstance(e, dict) else (None, None)
            if not (isinstance(old, str) and isinstance(new, str)) or not old:
                return None, f"an {name} of the report the session file does not show whole"
            count = text.count(old)
            if count == 0 or (count > 1 and e.get("replace_all") is not True):
                return None, f"an {name} of the report whose old text is not in it exactly once"
            text = text.replace(old, new) if e.get("replace_all") is True else text.replace(old, new, 1)
    if text is None:
        return None, "the session file holds no Write of the report"
    return text, ""


def report_digest_line(main: Path, folder: Path, side: dict) -> str:
    """The record's report line: the folder's one prefreeze-N.md rebuilt from the session, or why not."""
    reports = sorted(p for p in folder.iterdir() if REPORT_NAME.fullmatch(p.name)) if folder.is_dir() else []
    if len(reports) != 1:
        return REPORT_UNBOUND + f"the folder holds {len(reports)} pre-freeze reports, not exactly one"
    lines = main.read_text(errors="replace").splitlines()
    text, why = written_report(lines, reports[0], set().union(*(s.written_inside for s in side.values())))
    if text is None:
        return REPORT_UNBOUND + why
    return REPORT_DIGEST + hashlib.sha256(text.encode("utf-8")).hexdigest()


SESSION_DIGEST = "the reviewer's session file sha256: "


def regular_files(top: Path) -> list[Path]:
    """Every regular file under `top`, never inside a .git folder and never through a link."""
    if top.is_symlink() or not top.exists():
        return []
    if top.is_file():
        return [top]
    out = []
    for d, dirs, names in os.walk(top):
        dirs[:] = sorted(x for x in dirs if x != ".git" and not (Path(d) / x).is_symlink())
        out += [Path(d) / x for x in sorted(names) if not (Path(d) / x).is_symlink() and (Path(d) / x).is_file()]
    return out


def written_over(p: Path, written: set[str]) -> bool:
    """A session wrote this file, or a folder that holds it."""
    r = p.resolve()
    return str(r) in written or any(str(q) in written for q in r.parents)


def manifest_digest(text: str) -> str:
    """rounds.py's input_sha256, computed from the manifest's own lines: path, a NUL, then the file's sha256."""
    h = hashlib.sha256()
    for line in text.splitlines():
        sha, rel = line.split("  ", 1)
        h.update(rel.encode())
        h.update(b"\0")
        h.update(bytes.fromhex(sha))
    return h.hexdigest()


def register_rows() -> list[dict]:
    try:
        return json.loads(REGISTER.read_text())["rows"]
    except (OSError, ValueError, KeyError):
        return []


def corpus(folder: Path, written: set[str]) -> tuple[list[Path], str]:
    """The files the reviewer was given, as the folder stood at launch, and the rule that chose them.

    With the per-file manifest rounds.py --add writes before it hashes the row (round 2 on), exactly the files it
    lists whose bytes still hash as they did; the record says which row's input_sha256 the manifest reproduces.
    Without one (round 1), every file under the folder's entries at launch that is no newer than the launch stamp
    (folder-at-launch.txt) and that no session wrote by any tool, the shell included, a folder target with all it
    holds (reviews of 5a6dc21 and fff7e0d3). Never a .git folder or a link.
    """
    side = folder.parent / (folder.name + "-launch")
    manifest = side / MANIFEST
    if manifest.is_file():
        listed = [ln.split("  ", 1) for ln in manifest.read_text().splitlines() if "  " in ln]
        out = []
        for sha, rel in listed:
            p = folder / rel
            if p.is_symlink() or not p.is_file() or not inside(str(p.resolve()), folder.resolve()):
                continue
            if hashlib.sha256(p.read_bytes()).hexdigest() == sha:
                out.append(p)
        digest = manifest_digest(manifest.read_text())
        rows = [r["n"] for r in register_rows() if r.get("input_sha256") == digest]
        bound = (f"its digest {digest[:12]} is the input_sha256 of round row {rows[0]}" if rows else
                 f"its digest {digest[:12]} is the input_sha256 of NO round row, so it binds nothing")
        return out, (f"the per-file manifest written before the round row was hashed: {len(out)} of its "
                     f"{len(listed)} files, those whose bytes are unchanged since; {bound}")
    listing = side / "folder-at-launch.txt"
    tops = ([folder / n for n in listing.read_text().split("\n") if n.strip()] if listing.is_file()
            else sorted(folder.iterdir()))
    files = [p for top in tops for p in regular_files(top)]
    stamp = listing.stat().st_mtime_ns if listing.is_file() else None
    newer = [p for p in files if stamp is not None and p.stat().st_mtime_ns > stamp]
    newer_set = set(newer)
    by_write = [p for p in files if p not in newer_set and written_over(p, written)]
    gone = newer_set | set(by_write)
    out = [p for p in files if p not in gone]
    when = (time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(stamp / 1e9)) if stamp is not None
            else "none recorded")
    return out, (f"no per-file manifest at launch, so the launch stamp (folder-at-launch.txt, {when}): {len(out)} "
                 f"files, less {len(newer)} newer than the stamp and {len(by_write)} a session wrote")


def candidates(ext: str, marker: str, folder: Path) -> list[str]:
    """What must be found for a hit whose extent is `ext`: the extent itself, and for a path each tail of it that
    still holds a `/` and still holds the marker (so `ROOT/study/evals/x` may be found as `evals/x`, never as a bare
    word, and never by a tail that has dropped the word it explains). An absolute path outside the folder has none:
    it is a read outside, not a file in the folder."""
    if ext.startswith(("/", "~")):
        for base in (str(folder).lower(), "/private" + str(folder).lower()):
            if ext == base or ext.startswith(base + "/"):
                ext = ext[len(base):].lstrip("/")
                break
        else:
            return []
    if not ext:
        return []
    parts = ext.split("/")
    tails = ["/".join(parts[i:]) for i in range(1, len(parts) - 1)]
    return [c for c in [ext] + tails if marker in c]


def handback_hits(handbacks: list[tuple[str, str, str]]) -> list[dict]:
    """Every marker occurrence in every hand-back, with its extent."""
    hits = []
    for aid, text, kind in handbacks:
        low = text.lower()
        for label, w, op in rows():
            for m in re.finditer(re.escape(w.lower()), low):
                s, e = m.start(), m.end()
                while s > 0 and EXTENT.match(low[s - 1]):
                    s -= 1
                while e < len(low) and EXTENT.match(low[e]):
                    e += 1
                hits.append({"aid": aid, "label": label, "op": op, "word": w.lower(), "kind": kind,
                             "ext": low[s:e].rstrip(".'-/").lstrip(".'-"),
                             "quote": " ".join(text[max(0, m.start() - 40):m.start() + 160].split())})
    return hits


def found_in(files: list[Path], folder: Path, wanted: set[str]) -> set[str]:
    """The wanted strings that occur (lower-cased) in one of the files or in the files' own relative paths."""
    paths = "\n".join(str(p.relative_to(folder)).lower() for p in files)
    found = {w for w in wanted if w in paths}
    pending = wanted - found
    for p in files:
        if not pending:
            break
        try:
            body = p.read_bytes().decode("utf-8", errors="replace").lower()
        except OSError:
            continue
        hit = {w for w in pending if w in body}
        found |= hit
        pending -= hit
    return found


def read_there(aid: str, c: str, side: dict[str, Session], seen: frozenset = frozenset()) -> bool:
    """Did agent `aid` read `c`: in a tool result it received, or in a report a nested agent of its own handed it,
    where that nested agent read it in turn by this same rule (finding 6). No session, no read."""
    if aid in seen or aid not in side:
        return False
    s = side[aid]
    if c in s.traffic:
        return True
    return any(c in text.lower() and read_there(child, c, side, seen | {aid}) for child, text, _ in s.handbacks)


def table_of(ctx: list[str], folder: Path) -> list[dict]:
    out = []
    for label, w, op in rows():
        t, own, fp, un = classify_hits(ctx, w, folder, operator=op)
        out.append({"label": label, "total": t, "own": own, "fp": fp, "un": un})
    return out


def analyse(folder: Path, sid: str, projects: Path = PROJECTS) -> dict:
    """Everything the record states, as data. render() writes it; the tests read it."""
    main = session_file(sid, projects)
    reviewer, side = read_sessions(main, folder)
    sessions = [reviewer, *side.values()]
    launched = {aid for s in sessions for aid in s.launches.values()}
    all_hb = [h for s in sessions for h in s.handbacks]
    handbacks: dict[str, list[str]] = {}
    for aid, text, _ in all_hb:
        handbacks.setdefault(aid, []).append(text)
    written = set().union(*(s.written_inside for s in sessions))
    files, rule = corpus(folder, written)
    hits = handback_hits(all_hb)
    # Operator hits are searched too, so the one rule that refuses them is the line below, and it alone.
    wanted = {c for h in hits for c in candidates(h["ext"], h["word"], folder)}
    in_folder = found_in(files, folder, wanted)
    # The brief each agent was launched with, and the session that wrote it (the lead's ruling, 24 Oct 2026,
    # tightened after the closure review of fff7e0d3): a hit that traces only through the brief is explained only
    # when its extent is in the launch corpus. What the author read outside the folder lends no sub-agent cover; it
    # stays in sections 1 and 5.
    briefs: dict[str, tuple[Session, str]] = {}
    for s in sessions:
        for tid, aid in s.launches.items():
            briefs[aid] = (s, "\n".join(leaves((s.calls.get(tid) or {}).get("prompt"))).lower())
    for h in hits:
        cs = candidates(h["ext"], h["word"], folder)
        if h["op"]:
            h["via"] = None
        elif any(c in in_folder and read_there(h["aid"], c, side) for c in cs):
            h["via"] = "direct"
        elif h["aid"] in briefs and any(c in briefs[h["aid"]][1] and c in in_folder for c in cs):
            h["via"] = "brief"
        else:
            h["via"] = None
        h["traced"] = h["via"] is not None
    hb_table = []
    for label, _, _ in rows():
        mine = [h for h in hits if h["label"] == label]
        traced = sum(h["traced"] for h in mine)
        brief = sum(h["via"] == "brief" for h in mine)
        hb_table.append({"label": label, "total": len(mine), "traced": traced, "brief": brief,
                         "un": len(mine) - traced})
    side_ctx = [line for s in side.values() for line in s.ctx]
    per_agent = {aid: [r for r in table_of(s.ctx, folder) if r["un"]] for aid, s in side.items()}
    skills = set(reviewer.skills or ())
    return {
        "sid": sid, "n": reviewer.n, "ctx": reviewer.ctx, "inputs": reviewer.inputs, "sidechains": side,
        "missing": sorted(launched - set(side)), "unlaunched": sorted(set(side) - launched),
        "noid": [t for s in sessions for t in s.noid],
        "table": table_of(reviewer.ctx, folder), "side_table": table_of(side_ctx, folder),
        "per_agent": {aid: r for aid, r in per_agent.items() if r},
        "handbacks": handbacks, "handback_table": hb_table, "corpus_files": [str(p) for p in files],
        "corpus_rule": rule,
        "reports": [(aid, text) for aid, text, kind in all_hb if kind == "report"],
        "notifications": [(aid, text) for aid, text, kind in all_hb if kind == "notification"],
        "handback_quotes": [(f"agent {h['aid']}, {h['label']}", mask(h["quote"], str(folder))[:120])
                            for h in hits if not h["traced"]],
        "outside": outside_paths(reviewer, folder),
        "side_outside": {aid: outside_paths(s, folder) for aid, s in side.items()},
        "writes": {s.name: sorted(s.writes) for s in sessions if s.writes},
        "isolation": {aid: {"skills_as_reviewer": None if s.skills is None else set(s.skills) == skills,
                            "workflow": s.workflow, "mcp": s.mcp, "memory_outside": s.memory_outside}
                      for aid, s in side.items()},
        "email": len(EMAIL.findall("\n".join(reviewer.ctx + side_ctx))),
        "report_line": report_digest_line(main, folder, side),
        "session_sha": hashlib.sha256(main.read_bytes()).hexdigest(),
    }


def render(a: dict, folder: Path) -> str:
    F = str(folder)
    side = a["sidechains"]
    out = [f"blindness check, read from the reviewer's own session file ({a['n']} records, {len(a['ctx'])} attachment "
           f"records, {len(a['inputs'])} tool calls) and its {len(side)} sub-agent session files",
           f"session id: {a['sid']}", "",
           "1. Operator material in the loaded context (attachment records).",
           "   Every hit is classified. Two causes carry nothing about the study and recur in EVERY round:",
           "   the review folder's own path, which the harness echoes through its own furniture, and the",
           "   reviewer's own report, which it wrote and the harness attached back into its context. The",
           "   count that binds is UNEXPLAINED, and it must be 0 (Ruling 6, 20 September 2026). A rule read",
           "   on the totals could never pass, because both causes are present before the reviewer starts.",
           "   A sub-agent's hand-back is not counted here: section 4 reads it. An operator row is never",
           "   explained (lane blindness-sidechains, 24 October 2026).",
           "",
           f"   {'marker':34} {'total':>6} {'own report':>11} {'folder path':>12} {'UNEXPLAINED':>12}"]
    out += [f"   {r['label']:34} {r['total']:>6} {r['own']:>11} {r['fp']:>12} {r['un']:>12}" for r in a["table"]]
    out.append(f"   {'the account email':34} {a['email']:>6} {'':>11} {'':>12} {'tolerated':>12}")
    out += ["", f"2. The reviewer's sub-agents: {len(side)} sidechain session files read",
            f"   launched agents with no session file: {len(a['missing'])}"
            + (f" ({', '.join(a['missing'])})" if a["missing"] else ""),
            f"   session files no launch names: {len(a['unlaunched'])}"
            + (f" ({', '.join(a['unlaunched'])})" if a["unlaunched"] else ""),
            f"   Agent results that name no agent: {len(a['noid'])}"
            + (f" (tool uses {', '.join(a['noid'])}; read as reports from no session)" if a["noid"] else "")]
    out += [f"   - agent {aid}: {s.n} records, {len(s.ctx)} attachment records, {len(s.inputs)} tool calls"
            for aid, s in side.items()]
    out += ["", "3. Operator material in the sub-agents' own loaded context, all sessions together, by the rules of 1.",
            "", f"   {'marker':34} {'total':>6} {'own report':>11} {'folder path':>12} {'UNEXPLAINED':>12}"]
    out += [f"   {r['label']:34} {r['total']:>6} {r['own']:>11} {r['fp']:>12} {r['un']:>12}"
            for r in a["side_table"]]
    for aid, rs in a["per_agent"].items():
        out += [f"   - agent {aid}: {r['label']} UNEXPLAINED {r['un']}" for r in rs]
    rep_from = sorted({aid for aid, _ in a["reports"]})
    note_from = sorted({aid for aid, _ in a["notifications"]})
    out += ["", f"4. Sub-agent hand-backs carrying a report: {len(a['reports'])}, from {len(rep_from)} agents.",
            f"   Task notifications, listed apart: {len(a['notifications'])}, from {len(note_from)} agents; their",
            "   text is read by the same rule, so any hit in one is in the table below.",
            "   A hit is explained only when its text (the word or path it sits in) is in a file of the folder as",
            "   it stood at launch, and in a tool result that sub-agent received (or a report a nested agent of",
            "   its own handed it and read the same way): it read it there. Any other hit is UNEXPLAINED, and an",
            "   operator row is never explained. A study word is traced by its word alone, so a word the study's",
            "   own files also hold passes even when the sub-agent met it elsewhere; that is why the operator",
            "   rows are refused outright. The count that binds is UNEXPLAINED, and it must be 0.",
            "   A hit is traced via brief when the sub-agent did not read it but its brief holds it and it is in",
            "   the folder at launch. What the brief's author read outside the folder lends no cover.",
            f"   The folder as it stood at launch: {a['corpus_rule']}.", "",
            f"   {'marker':34} {'total':>6} {'traced, direct':>15} {'traced via brief':>17} {'UNEXPLAINED':>12}"]
    out += [f"   {r['label']:34} {r['total']:>6} {r['traced'] - r['brief']:>15} {r['brief']:>17} {r['un']:>12}"
            for r in a["handback_table"]]
    if a["handback_quotes"]:
        out.append("   UNEXPLAINED hits, each quoted to its first 120 characters:")
        out += [f"   - {who}: {q}" for who, q in a["handback_quotes"]]
    out += ["", f"5. Absolute paths in the reviewer's tool inputs that are not inside its folder: {len(a['outside'])}"]
    out += ["   - " + p for p in sorted(a["outside"])[:20]]
    for aid, ps in a["side_outside"].items():
        out.append(f"   agent {aid}, in its tool inputs: {len(ps)}")
        out += ["   - " + p for p in sorted(ps)[:20]]
    n_w = sum(len(v) for v in a["writes"].values())
    out += ["", f"6. Writes outside the folder: {n_w} paths, by the Write and Edit tools' own paths and by the paths",
            "   a shell command that writes names. Listed, not ruled: a write outside does not void a round by itself."]
    for who, ps in a["writes"].items():
        out.append(f"   {who if who == 'the reviewer' else 'agent ' + who}: {len(ps)}")
        out += ["   - " + mask(p, F)[:120] for p in ps[:20]]
    out += ["", "7. The reviewer's isolation, as the sub-agents' own records show it. The launch flags are process",
            "   flags and no sidechain record carries them, nor the environment it ran with."]
    for aid, iso in a["isolation"].items():
        sk = {True: "the reviewer's", False: "NOT the reviewer's", None: "none recorded"}[iso["skills_as_reviewer"]]
        out.append(f"   - agent {aid}: skills offered {sk}; Workflow tool named {iso['workflow']}; MCP tools named "
                   f"{iso['mcp']}; instruction files from outside the folder {iso['memory_outside']}")
    out += ["", "8. The report as the reviewer's session wrote it, rebuilt from the session file alone (its Write, then its",
            "   Edits in order); commit_review.py and the freeze refuse a committed report with other bytes.",
            a["report_line"], SESSION_DIGEST + a["session_sha"]]
    return "\n".join(out) + "\n"


def report(folder: Path, sid: str, projects: Path = PROJECTS) -> str:
    return render(analyse(folder, sid, projects), folder)


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__.split("\n")[2].strip())
        return 2
    folder = Path(sys.argv[1]).resolve()
    side = folder.parent / (folder.name + "-launch")
    sid = (side / "SESSION").read_text().strip()
    text = report(folder, sid)
    (side / "blindness.txt").write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
