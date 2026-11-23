#!/usr/bin/env python3
"""OD57's admission: one rule set for the harness twin (box/scan_record.py) and the aegis door (a byte copy, pinned).

    ruled_text(body, ruling, data, shapes, kind, line) -> the ruled line's text, or None          (lane vendor-b24)

`body` is one record (a JSON line, no newline) of the file whose bytes are `data`, at 1-based `line`, of file kind
`kind`; `shapes` are the arm's read shapes (box/od57_shapes; () for a Claude Code file). The text is returned only when
the record carries the ruled line nowhere but as whole lines of ruled reads of the doc (or, failing that, as whole
output lines of a shell tool after a closed prefix: od57-line), each counted, and only when no write of the
doc comes first in the file. The caller keeps its own probe (the file rescanned with exactly those
occurrences removed) and its own listing of each admission.

THE RULING. OD57 (Javier's own ruling, his verified terminal reply "scan-envmd-1 safe" at 2026-10-16T12:52:33Z, outcome
"safe" on ask T83): gitleaks' generic-api-key flags line 175 of gars/_references/environment.md ("Key pinned versions:
...", a list of package versions; blob 2c0ea574, byte-identical on public GARS main a97fa9cd) when an agent reads that
doc. The ruling binds that one line's text (sha256 of its 80 bytes, no newline), decoded from the JSON record, inside a
read of that doc, in an agent-text kind. Any other rule, any other line, the same text anywhere outside a ruled read, or
a match the line alone does not explain still refuses.

WHAT IS A READ (lane vendor-b24, glitch-26's rulings B24-2, 21 Oct 2026; lane-reports/vendor-b24-DESIGN.md):
- Claude Code: a Read whose file_path names the doc (closing F-RS-4); a Grep whose path names the doc, in content mode;
  a Bash read (_ruled_shell).
- Gemini CLI 0.64.0 and Codex CLI 0.162.1: the read shapes (box/od57_shapes), now also grep_search (its `L175: ` match
  line and its display entry, and its context lines inside the window the tool itself produced).
- A shell read (every arm, _ruled_shell): `[cd <dir> (&& | ;)] grep|cat ... [| filter]...`. The output line's provenance
  is grep's own label: with the doc as the single operand the line carries none; with several operands (and no flag that
  drops or rewrites labels) the line's own label must resolve to the doc, with `:175:` under -n.
- A compound shell read (od57-gap, STOP2-OD57-GAP-20261107; every arm, _ruled_compound, tried only when _ruled_shell
  refuses): `[cd <dir> (&& | ;)]` then commands that each start with grep, rg, cat, head, tail, wc, cut, sed, awk or
  echo (or are one of _filter_ok's stdin filters), at least one of them a labelled, glob-free grep (not -r/-R) or rg
  with the doc among its typed file operands. Only a line `<label>:<80 bytes>`, or `<label>:175:<80 bytes>` where a
  labelled read of the command numbers its lines, is admitted, the label being one of a read's own typed operands and
  resolving to the doc against the cd. sed (-n, print-only scripts), awk (no system, getline, pipe or redirect) and
  echo (no `$`, no backslash) are allowed beside such a read; they never make the read. That binds the label, not the
  bytes' source: another command (echo, awk, cat of another file) or an rg directory operand (rg walks it) can print
  a line of the same shape (see RESIDUALS). A context line, a line with any other prefix, and any byte after the 80
  still refuse; a recursive grep, an rg with no file operand (outside a pipe), or a glob operand anywhere refuses the
  whole command.
  The doc's bare line (od57-gap follow-up, glitch-45's scope 1): when grep, rg, cat, head, tail, sed or awk reads the
  doc as its only file operand, and no command but a labelled read names any other file (cat, head, tail, wc, cut, sed,
  awk, an unlabelled grep or rg), a line that is exactly the 80 bytes is admitted, or `175:<80 bytes>` when a grep or
  rg in the command typed -n. So no other file operand of a command that prints file text unlabelled can supply that
  line; a command that prints text of its own can (see RESIDUALS).
- A whole output line (od57-line, SCANREFUSAL-ROAD-20261108; Javier's word pending, ask od57-line; _any_text, tried
  only when the reads above admit nothing): the 80 bytes as a whole line of a tool's output, whatever command printed
  them. The output is a Claude tool_result (and the record's toolUseResult) answering one Bash or BashOutput call, or
  a read shape's result text whose call names one of that shape's shell tools (or their output copy); Read, Grep and
  the vendors' path and grep tools keep their path-bound rules; Agent and Task results, a result with no call, and
  the agent's own text stay out. The line is the 80 bytes after exactly one of: nothing,
  `175:`, Claude Read's prefix (_READ_PREFIX), `<label>:` or `<label>:175:` with the label resolving to the doc (no
  cwd); no byte may follow. Only in an agent-text kind. T1, the digest count and the caller's probe hold unchanged.
  This widens OD57 from "inside a read of that doc" to "a whole output line of a shell tool" (STOP4,
  s-91dbb18a: the line as `175:<80 bytes>` from a command no read rule above admits).
- T1: a write of the doc (Write, Edit, MultiEdit, write_file, replace, a Codex file_change or apply_patch) at or before a
  record's line disqualifies every admission on that line and after it in the same file.

PATHS (R3-1, glitch-26's round-3 ruling on review 7fcba34 MINOR-1): every path that binds a read to the doc (Claude
Read and Grep, Gemini read_file, grep_search's File header joined to its dir_path and its display's absolutePath, a
shell operand or label) goes through _resolves_to_doc: no `..`, normalised, then the run tree's absolute doc or the doc
relative to the agent's folder. T1 alone reads a written path wider (_may_name_doc), since a write disqualifies.

RESIDUALS (named, R3-5; none admits a byte other than the ruled line, and each is held by the digest and the probe):
- the Claude path runs for every file kind, so a Claude-shaped Read record inside a Gemini session or a Codex stream
  file is read as Claude's (the vendor CLIs write those files, not the model);
- a Gemini shell read ignores the call's dir_path (the git read's argument rule, command and description only, is not
  applied to cat and grep), so `cat _references/environment.md` with dir_path elsewhere is read as the doc;
- the run tree is bound by its name only (/tmp/run-<hex>), so a model-made /tmp/run-dead/gars/... matches;
- shell writes (cp, mv, tee, sed -i, a redirect) and a Claude Bash cwd kept across calls are not seen by T1;
- grep_search's `context`, `before` or `after` present as 0 counts as an explicit window (fail-closed: it can only
  refuse a context line the tool's auto-context would have made; the bundle's own test of the value is not cited);
- od57-gap's compound read (REVIEW-OD57-GAP-20261107, MINOR-1) binds a line's shape, not its source: the same pinned
  80 bytes, with the doc's typed label or bare, can come from another command of the same line (echo or awk BEGIN
  printing literals, even split across quoted strings; awk rewriting ARGV; cat of another file holding such a line),
  from a file an rg directory operand walks, from a second file whose typed name holds a colon, or carry `175:` from
  another labelled read's -n. The 80-byte pin, the digest count and the probe hold for all of them.
- od57-line's whole output line binds the line's shape and its producer (a shell tool), not its source: any
  command (echo, printf, awk, a copy of the doc, grep -n of another file whose line 175 holds the same bytes) can print
  it. The 80-byte pin, the closed prefix, nothing after the bytes, the digest count and the probe hold for all of them.

Standard library only (hashlib, json, posixpath, re, shlex). No process, no file access: bytes in, text out.
"""

from __future__ import annotations

import hashlib
import json
import posixpath
import re
import shlex

RULED_LINES = (
    {"ruling": "OD57", "rule": "generic-api-key", "bytes": 80,
     "sha256": "0b85623f36eef7c6e7ca19c7900e865fd7ddbfe5853197b5c1d2e246d81df313",
     "source": "gars/_references/environment.md line 175, blob 2c0ea574434dbc4f1b9c454c8788fc68fcca2a13"},
)
_RULED_DOC = "_references/environment.md"
_RULED_GIT_PATH = "gars/" + _RULED_DOC
# The run tree a walk or take runs in (/tmp/run-<hex>, as every committed record names it) holds the doc at gars/.
_DOC_ABS = re.compile(r"/tmp/run-[0-9a-f]+/gars/_references/environment\.md")
_DOC_RELS = (_RULED_DOC, _RULED_GIT_PATH)
_TOOL_RESULT_KEYS = ("toolUseResult", "tool_use_result")
# Claude Code's Read: `cat -n`'s number and a tab or an arrow; the number is the doc's own, 175.
_READ_PREFIX = re.compile(r"\s*175(?:\t|→)")


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _lines(data: bytes) -> list:
    """Split on the newline only (never str.splitlines), keeping each line's own ending."""
    parts = data.split(b"\n")
    lines = [p + b"\n" for p in parts[:-1]]
    if parts[-1]:
        lines.append(parts[-1])
    return lines


def _strings(node, out):
    """Every string in a decoded JSON value, keys included."""
    if isinstance(node, str):
        out.append(node)
    elif isinstance(node, dict):
        for k, v in node.items():
            out.append(k)
            _strings(v, out)
    elif isinstance(node, list):
        for v in node:
            _strings(v, out)
    return out


def _is_ruled(text, ruling) -> bool:
    """Whether `text` is exactly the ruled line's bytes."""
    b = text.encode("utf-8", "surrogateescape") if isinstance(text, str) else b""
    return len(b) == ruling["bytes"] and _sha(b) == ruling["sha256"]


def _resolves_to_doc(path, cwd=None) -> bool:
    """A path (and the folder a command set) that resolves to the doc inside the run tree: no `..` anywhere, then
    either the run tree's absolute doc or the doc relative to the agent's own folder (the run tree or its gars/)."""
    if not isinstance(path, str) or not path or any(c in path for c in "\0\n\r"):
        return False
    if cwd is not None and not isinstance(cwd, str):
        return False
    p = path if path.startswith("/") or not cwd else cwd.rstrip("/") + "/" + path
    if ".." in p.split("/"):
        return False
    n = posixpath.normpath(p)
    if n.startswith("/"):
        return _DOC_ABS.fullmatch(n) is not None
    return n in _DOC_RELS


# ------------------------------------------------------------------------------------------------- Claude Code
# B17-11 (glitch-26, lane vendor-b17 round 3): a tool_use or tool_result block is read only at a message record's own
# positions (message.content[*]), never one nested deeper, so nothing inside a tool's input is ever a call or a result.
_CLAUDE_AT = (("message", "content", "*"),)


def _path_values(node, path, out):
    """The values at the end of a path from `node` (a tuple of keys, "*" for each list element)."""
    if not path:
        out.append(node)
    elif path[0] == "*":
        if isinstance(node, list):
            for v in node:
                _path_values(v, path[1:], out)
    elif isinstance(node, dict) and path[0] in node:
        _path_values(node[path[0]], path[1:], out)
    return out


def _top_blocks(rec, kind) -> list:
    """The `kind` blocks at a record's own positions (_CLAUDE_AT)."""
    return [b for at in _CLAUDE_AT for b in _path_values(rec, at, []) if isinstance(b, dict) and b.get("type") == kind]


def _records(data: bytes) -> list:
    out = []
    for n, line in enumerate(_lines(data), 1):
        try:
            out.append((n, json.loads(line)))
        except ValueError:
            continue
    return out


def _tool_uses(data: bytes) -> dict:
    """{tool_use id: [(tool name, its input)]} over every JSON record of a file (main thread or a sub-agent's), each
    block at its record's own position (B17-11)."""
    uses = {}
    for _, rec in _records(data):
        for b in _top_blocks(rec, "tool_use"):
            if isinstance(b.get("id"), str):
                uses.setdefault(b["id"], []).append((b.get("name"), b.get("input")))
    return uses


def _claude_tool(uses, tool_use_id):
    """The ruled read a tool_result answers, as a tool entry for the line rule, else None: one tool_use with that id; a
    Read of the doc (B24-2 item 3, closing F-RS-4), a Grep of the doc in content mode, or a Bash shell read."""
    got = uses.get(tool_use_id) if isinstance(tool_use_id, str) else None
    if not got or len(got) != 1:
        return None
    name, inp = got[0]
    if not isinstance(inp, dict):
        return None
    if name == "Read":
        return "read" if _resolves_to_doc(inp.get("file_path")) else None
    if name == "Grep":
        if inp.get("output_mode") != "content":
            return None
        return "grep" if _resolves_to_doc(inp.get("path")) else None
    if name == "Bash":
        spec = _ruled_shell(inp.get("command"))
        return spec if spec is not None else _ruled_compound(inp.get("command"))
    return None


def _tool_result_strings(node, uses, out):
    """(string, line rule) for a ruled tool's result: a tool_result block's content (a string, or its text items), and
    every string under a record's own tool-result key (toolUseResult; tool_use_result in a stream) when every
    tool_result block of that record answers one and the same ruled read. Blocks only at the record's own positions."""
    blocks = _top_blocks(node, "tool_result")
    rules = []
    for b in blocks:
        rule = _claude_tool(uses, b.get("tool_use_id"))
        rules.append(rule)
        if rule is None:
            continue
        c = b.get("content")
        if isinstance(c, str):
            out.append((c, _claude_rule(rule)))
        elif isinstance(c, list):
            out += [(i["text"], _claude_rule(rule)) for i in c if isinstance(i, dict) and i.get("type") == "text"
                    and isinstance(i.get("text"), str)]
    if isinstance(node, dict) and blocks and all(r is not None for r in rules) \
            and all(r == rules[0] for r in rules):
        for k, v in node.items():
            if k in _TOOL_RESULT_KEYS:
                out += [(s, _claude_rule(rules[0])) for s in _strings(v, [])]
    return out


def _claude_rule(rule) -> dict:
    if rule == "read":
        return {"kind": "read"}
    if rule == "grep":
        return {"kind": "claude-grep"}
    return {"kind": "shell", "spec": rule}


# ------------------------------------------------------------------------------------------------- the shell read
# The shell form OD57 admits (glitch-b5's allow-list of 16 Oct 2026, after walk w167 and the cloud review of aegis
# 41de680; narrowed by B24-2 item 5 as revised: provenance from grep's own labels). The command holds no newline or
# carriage return, no $(...), backtick or process substitution, no `#`, no backslash outside quotes and no shell
# operator but && || ; | and the output redirects > >> >& (an input redirect < refuses); it shell-tokenises; no token is
# a shell or eval. It is [cd <dir> (&& or ;)] then one read, grep or cat, then commands (head, tail, sort, uniq, wc,
# grep, cat) that name no file: a pipe's filters, or after && || ; a command that reads nothing. Anything else
# refuses. Admitting less is fine.
_RULED_SEPARATORS = ("&&", "||", ";", "|")
_RULED_REDIRECTS = (">", ">>", ">&")
_RULED_SHELLS = ("sh", "bash", "zsh", "dash", "ksh", "eval")
# grep's flags without a value (GNU grep 3): none rewrites or drops a label but -h, which _grep_spec reads; -Z, -T,
# -b, -u, --label and every long option refuse. -e takes the pattern; -A -B -C -m take a number.
_GREP_FLAGS = frozenset("nirRHhEFGwxvsaIclLqo")
_GREP_NUMBER = frozenset("ABCm")
_CAT_FLAGS = frozenset("nu")
_NUMBER = re.compile(r"[0-9]+")


def _ruled_unquoted_backslash(cmd):
    """A backslash outside quotes (a first word is compared on its exact token: no \\grep, no /bin/grep)."""
    quote, skip = None, False
    for ch in cmd:
        if skip:
            skip = False
        elif quote == "'":
            if ch == "'":
                quote = None
        elif quote == '"':
            if ch == "\\":
                skip = True
            elif ch == '"':
                quote = None
        elif ch in "'\"":
            quote = ch
        elif ch == "\\":
            return True
    return False


def _shell_tokens(cmd):
    """(segments, separators) of a command the allow-list may admit, else None."""
    # "#" refuses anywhere, quoted or not: shlex starts a comment at a mid-word "#" where bash does not (cloud review
    # of aegis b2738e2), and admitting less is fine
    if not isinstance(cmd, str) or any(x in cmd for x in ("\n", "\r", "#", "$(", "`", "<(", ">(")):
        return None
    if _ruled_unquoted_backslash(cmd):
        return None
    try:
        lex = shlex.shlex(cmd, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        lex.commenters = ""         # defence in depth: no comment ever hides a token from these checks
        tokens = list(lex)
    except ValueError:
        return None
    if any(t in _RULED_SHELLS for t in tokens):
        return None
    segments, seps, cur, skip = [], [], [], False
    for t in tokens:
        if skip:
            skip = False
            if t in _RULED_SEPARATORS or (t and set(t) <= set("();<>|&")):
                return None
            continue
        if t in _RULED_SEPARATORS:
            segments.append(cur)
            seps.append(t)
            cur = []
        elif t in _RULED_REDIRECTS:
            if cur and cur[-1] in ("1", "2"):
                cur.pop()                     # an fd number before the redirect (2>/dev/null)
            skip = True                       # its target is no operand
        elif t and set(t) <= set("();<>|&"):
            return None                       # < and every other operator refuse
        else:
            cur.append(t)
    if skip:
        return None
    segments.append(cur)
    return segments, seps


def _grep_parse(args):
    """grep's arguments as {"flags", "ops", "context"}, or None for any form this rule does not read."""
    flags, patterns, ops, context, i = set(), 0, [], False, 0
    while i < len(args):
        t = args[i]
        if t.startswith("--"):
            return None
        if t == "-":
            return None
        if t.startswith("-") and len(t) > 1:
            j = 1
            while j < len(t):
                ch = t[j]
                if ch == "e" or ch in _GREP_NUMBER:
                    rest = t[j + 1:]
                    if not rest:
                        if i + 1 >= len(args):
                            return None
                        i += 1
                        rest = args[i]
                    if ch == "e":
                        patterns += 1
                    elif not _NUMBER.fullmatch(rest):
                        return None
                    elif ch != "m":
                        context = True
                    break
                if ch not in _GREP_FLAGS:
                    return None
                flags.add(ch)
                j += 1
            i += 1
            continue
        ops.append(t)
        i += 1
    if patterns == 0:
        if not ops:
            return None
        ops = ops[1:]
    return {"flags": flags, "ops": ops, "context": context}


def _grep_spec(args, cwd):
    """The read spec of a grep segment: unlabelled (the doc its single operand) or labelled (each line's own label must
    resolve to the doc), else None."""
    g = _grep_parse(args)
    if g is None:
        return None
    flags, ops = g["flags"], g["ops"]
    numbered = "n" in flags
    recursive = bool(flags & {"r", "R"})
    if "h" in flags and "H" in flags:
        return None
    single_doc = len(ops) == 1 and _resolves_to_doc(ops[0], cwd)
    labelled = "H" in flags or ("h" not in flags and (len(ops) > 1 or (recursive and not single_doc)))
    # R3-2 (review of 7fcba34, MINOR-2): a label must be a name typed in the command, never one a filename on disk
    # supplies (a recursive folder walk, or a glob the shell expands; a filename may hold a newline)
    if labelled and recursive:
        return None
    if labelled and any(c in op for op in ops for c in "*?["):
        return None
    if not labelled:
        if len(ops) != 1:                      # several files and -h: no label to bind them
            return None
        if not _resolves_to_doc(ops[0], cwd):
            return None
    return {"read": "grep", "labelled": labelled, "n": numbered, "context": g["context"], "cwd": cwd}


def _cat_spec(args, cwd):
    flags, ops = set(), []
    for t in args:
        if t.startswith("-") and len(t) > 1:
            if t.startswith("--") or not set(t[1:]) <= _CAT_FLAGS:
                return None
            flags |= set(t[1:])
        else:
            ops.append(t)
    if len(ops) != 1 or not _resolves_to_doc(ops[0], cwd):
        return None
    return {"read": "cat", "labelled": False, "n": "n" in flags, "context": False, "cwd": cwd}


_FILTER_FORMS = {
    "head": re.compile(r"-(?:[nc]?[0-9]+|[qv])"),
    "tail": re.compile(r"-(?:[nc]?[+-]?[0-9]+|[qv])"),
    "sort": re.compile(r"-(?:[bdfginrRuMhVs]+|k[0-9.,a-zA-Z]+)"),
    "uniq": re.compile(r"-[cdiu]+"),
    "wc": re.compile(r"-[lwcm]+"),
    "cat": re.compile(r"-[nu]+"),
}


def _filter_ok(seg) -> bool:
    """A `|` filter that reads its standard input only: no file operand."""
    word, rest = seg[0], seg[1:]
    if word == "grep":
        g = _grep_parse(rest)
        return g is not None and not g["ops"]
    form = _FILTER_FORMS.get(word)
    if form is None:
        return False
    i, kept = 0, []
    while i < len(rest):
        t = rest[i]
        if word in ("head", "tail") and t in ("-n", "-c") and i + 1 < len(rest) \
                and re.fullmatch(r"[+-]?[0-9]+", rest[i + 1]):
            i += 2
            continue
        if word == "sort" and t == "-k" and i + 1 < len(rest) and re.fullmatch(r"[0-9.,a-zA-Z]+", rest[i + 1]):
            i += 2
            continue
        if not form.fullmatch(t):
            kept.append(t)
        i += 1
    rest = kept
    return not rest


def _ruled_shell(cmd):
    """The read spec of a shell command OD57 admits (the allow-list above), else None."""
    got = _shell_tokens(cmd)
    if got is None:
        return None
    segments, seps = got
    if any(not seg for seg in segments):
        return None
    cwd, i = None, 0
    if segments[0][0] == "cd":
        if len(segments[0]) != 2 or len(segments) < 2 or seps[0] not in ("&&", ";"):
            return None
        cwd, i = segments[0][1], 1
        if ".." in cwd.split("/"):
            return None
    read = segments[i]
    if read[0] == "grep":
        spec = _grep_spec(read[1:], cwd)
    elif read[0] == "cat":
        spec = _cat_spec(read[1:], cwd)
    else:
        return None
    if spec is None:
        return None
    # every later command reads its standard input only (a pipe from the read, or nothing): it names no file
    for seg in segments[i + 1:]:
        if not _filter_ok(seg):
            return None
    return spec


def _ruled_bash(cmd) -> bool:
    """A shell command OD57 admits (kept by name: the twin's tests and the git rule read it)."""
    return _ruled_shell(cmd) is not None


# od57-gap (STOP2-OD57-GAP-20261107): the counted run's takes s-3c4f8d and s-0e780d carried line 175 as a labelled grep
# line (`<doc>:` or `<doc>:175:`) of a Bash command with a second command after `;` that names a file, which
# _ruled_shell refuses as a whole. A compound read admits ONLY a labelled line of one of its labelled reads (grep, or rg
# with typed file operands): the label is the read's own provenance, one of its typed operands (no recursion, no glob,
# R3-2), so the other commands need not be silent. Every other command is read-only text (no shell, no substitution, no
# `<`: _shell_tokens; no cd after the first; sed prints only, awk runs no command and reads no other input).
_GLOB = frozenset("*?[")
_PLAIN_READS = ("cat", "head", "tail", "wc", "cut")   # each token an option or a file operand: no glob in any
# rg's forms read here (ripgrep 14): flags without a value, the value flags, and a closed set of long options. Anything
# else refuses (among them -r replace, -g/-t filters, -u, -L, -z, -f, --pre, --heading, --column, --vimgrep, -c, -l).
_RG_FLAGS = frozenset("niSswxFHIvoN")
_RG_NUMBER = frozenset("ABCm")
_RG_LONG = {"--line-number": "n", "--no-line-number": "N", "--with-filename": "H", "--no-filename": "I",
            "--ignore-case": "i", "--smart-case": "S", "--case-sensitive": "s", "--fixed-strings": "F",
            "--word-regexp": "w", "--line-regexp": "x", "--no-heading": "", "--color=never": ""}
_SED_ADDR = r"(?:[0-9]+|\$|/[^/\\$]*/)"
_SED_PRINT = re.compile(rf"{_SED_ADDR}(?:,{_SED_ADDR})?p(?:;{_SED_ADDR}(?:,{_SED_ADDR})?p)*;?")
_AWK_REFUSED = ("system", "getline", "close", "fflush", "ENVIRON", "PROCINFO", "|", "@")


def _rg_parse(args):
    """rg's arguments as {"flags", "ops", "context"}, or None for any form this rule does not read."""
    flags, patterns, ops, context, i = set(), 0, [], False, 0
    while i < len(args):
        t = args[i]
        if t.startswith("--"):
            if t not in _RG_LONG:
                return None
            flags |= set(_RG_LONG[t])
            i += 1
            continue
        if t == "-":
            return None
        if t.startswith("-") and len(t) > 1:
            j = 1
            while j < len(t):
                ch = t[j]
                if ch == "e" or ch in _RG_NUMBER:
                    rest = t[j + 1:]
                    if not rest:
                        if i + 1 >= len(args):
                            return None
                        i += 1
                        rest = args[i]
                    if ch == "e":
                        patterns += 1
                    elif not _NUMBER.fullmatch(rest):
                        return None
                    elif ch != "m":
                        context = True
                    break
                if ch not in _RG_FLAGS:
                    return None
                flags.add(ch)
                j += 1
            i += 1
            continue
        ops.append(t)
        i += 1
    if patterns == 0:
        if not ops:
            return None
        ops = ops[1:]
    return {"flags": flags, "ops": ops, "context": context}


def _typed_doc(ops, cwd) -> tuple:
    """The typed operands that resolve to the doc."""
    return tuple(op for op in ops if _resolves_to_doc(op, cwd))


def _sed_ops(args):
    """sed -n with print-only scripts (addresses, then p): its file operands (no glob), else None."""
    quiet, scripts, ops, i = False, [], [], 0
    while i < len(args):
        t = args[i]
        if t.startswith("-") and len(t) > 1:
            if t.startswith("--"):
                return None
            for j, ch in enumerate(t[1:], 1):
                if ch == "n":
                    quiet = True
                elif ch in "Er":
                    continue
                elif ch == "e" and j == len(t) - 1 and i + 1 < len(args):
                    i += 1
                    scripts.append(args[i])
                else:
                    return None
        elif not scripts:
            scripts.append(t)                # the first word that is no option is the script (no -e given)
        else:
            ops.append(t)
        i += 1
    ok = (quiet and bool(scripts) and all(_SED_PRINT.fullmatch(s) for s in scripts)
          and not any(c in op for op in ops for c in _GLOB))
    return ops if ok else None


_AWK_ASSIGN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=.*", re.S)


def _awk_ops(args):
    """awk with one program text: -F and -v only; no command, no other input, no redirect (in an action), no glob. Its
    file operands (a `name=value` operand is an assignment, no file), else None."""
    i = 0
    while i < len(args):
        t = args[i]
        if t in ("-F", "-v"):
            if i + 1 >= len(args):
                return None
            i += 2
            continue
        if t.startswith(("-F", "-v")) and len(t) > 2:
            i += 1
            continue
        if t.startswith("-"):
            return None
        prog, ops = t, args[i + 1:]
        action = prog.split("{", 1)[1] if "{" in prog else ""
        ok = (not any(x in prog for x in _AWK_REFUSED) and ">" not in action
              and not any(c in op for op in ops for c in _GLOB))
        return [op for op in ops if not _AWK_ASSIGN.fullmatch(op)] if ok else None
    return None


_VALUED = {"head": ("-n", "-c"), "tail": ("-n", "-c"), "cut": ("-d", "-f", "-c", "-b"), "cat": (), "wc": ()}


def _plain_ops(word, rest):
    """cat, head, tail, wc or cut: the file operands (no glob; `--` and `-` refuse, so an operand never hides as an
    option or as standard input), else None."""
    ops, i = [], 0
    while i < len(rest):
        t = rest[i]
        if t in ("--", "-") or any(c in t for c in _GLOB):
            return None
        if t in _VALUED[word]:
            i += 2
            continue
        if not t.startswith("-"):
            ops.append(t)
        i += 1
    return ops


def _echo_ok(args) -> bool:
    """echo of literal words: no expansion, no escape."""
    return not any("$" in t or "\\" in t for t in args)


def _ruled_compound(cmd):
    """The read spec of a compound shell read (see the module docstring), else None."""
    got = _shell_tokens(cmd)
    if got is None:
        return None
    segments, seps = got
    if any(not seg for seg in segments):
        return None
    cwd, i = None, 0
    if segments[0][0] == "cd":
        if len(segments[0]) != 2 or len(segments) < 2 or seps[0] not in ("&&", ";"):
            return None
        cwd, i = segments[0][1], 1
        if ".." in cwd.split("/"):
            return None
    specs, other, bare, numbered = [], False, False, False
    for k in range(i, len(segments)):
        word, rest = segments[k][0], segments[k][1:]
        labelled, ops = False, None
        if word == "grep":
            g = _grep_parse(rest)
            if g is None or g["flags"] & {"r", "R"} or any(c in op for op in g["ops"] for c in _GLOB):
                return None
            spec = _grep_spec(rest, cwd)
            typed = _typed_doc(g["ops"], cwd)
            ops, numbered = g["ops"], numbered or "n" in g["flags"]
            labelled = "H" in g["flags"] or ("h" not in g["flags"] and len(ops) > 1)
            if spec is not None and spec["labelled"] and typed:
                specs.append({"typed": typed, "numbers": (spec["n"],)})
        elif word == "rg":
            g = _rg_parse(rest)
            if g is None or any(c in op for op in g["ops"] for c in _GLOB):
                return None
            if not g["ops"]:
                if k == 0 or seps[k - 1] != "|":
                    return None              # no file operand outside a pipe: rg walks the folder (R3-2)
                continue
            flags, typed, ops = g["flags"], _typed_doc(g["ops"], cwd), g["ops"]
            if "H" in flags and "I" in flags:
                return None
            numbered = numbered or ("n" in flags and "N" not in flags)
            labelled = "H" in flags or ("I" not in flags and len(ops) > 1)
            if labelled and typed:
                # off a terminal rg numbers no line unless -n; on one it may (its heading then holds the label alone)
                numbers = (True,) if "n" in flags and "N" not in flags else (False,) if "N" in flags else (False, True)
                specs.append({"typed": typed, "numbers": numbers})
        elif word in _PLAIN_READS:
            ops = _plain_ops(word, rest)
            if ops is None:
                return None
        elif word == "sed":
            ops = _sed_ops(rest)
            if ops is None:
                return None
        elif word == "awk":
            ops = _awk_ops(rest)
            if ops is None:
                return None
        elif word == "echo":
            if not _echo_ok(rest):
                return None
        elif not _filter_ok(segments[k]):
            return None
        # od57-gap follow-up (glitch-45, scope 1): an unlabelled line is admitted only when every file operand of every
        # command but a labelled read (whose lines all carry a label) is the doc, so a bare line can come from the doc
        # alone; wc and cut of another file refuse too (stricter than needed).
        if ops and not labelled:
            docs = [op for op in ops if _resolves_to_doc(op, cwd)]
            if len(docs) != len(ops):
                other = True
            elif word in ("grep", "rg", "cat", "head", "tail", "sed", "awk"):
                bare = True
    bare = bare and not other
    if not specs and not bare:
        return None
    return {"read": "compound", "specs": tuple(specs), "bare": bare, "numbered": bare and numbered}


def _compound_line(prefix, spec) -> bool:
    """A compound read's admitted prefix: <label>: or <label>:175: (as that read numbers), the label exactly one of its
    typed operands, each of which resolves to the doc against the folder the command set (_typed_doc). No context
    line."""
    for numbered in spec["numbers"]:
        tail = ":175:" if numbered else ":"
        if prefix.endswith(tail) and prefix[:-len(tail)] in spec["typed"]:
            return True
    return False


def _labelled_line(prefix, spec) -> bool:
    """A labelled grep line's prefix: <label><sep>[175<sep>], sep `:` (or `-` for a context line), the label resolving
    to the doc against the folder the command set."""
    number = "175"
    seps = ":-" if spec["context"] else ":"
    for sep in seps:
        tail = sep + (number + sep if spec["n"] else "")
        if prefix.endswith(tail) and len(prefix) > len(tail):
            label = prefix[:-len(tail)]
            if not _resolves_to_doc(label, spec["cwd"]):
                continue
            return True
    return False


def _shell_prefix_ok(prefix, spec) -> bool:
    """The prefix a shell read's output line may carry before the ruled bytes."""
    if spec["read"] == "compound":                       # od57-gap: a labelled line of one of its labelled reads, or
        if spec["bare"] and (prefix == "" or (spec["numbered"] and prefix == "175:")):   # the doc's bare line
            return True
        return any(_compound_line(prefix, s) for s in spec["specs"])
    if spec["read"] == "cat":
        return re.fullmatch(r" *175\t", prefix) is not None if spec["n"] else prefix == ""
    if spec["labelled"]:
        return _labelled_line(prefix, spec)
    if spec["n"]:
        return prefix == "175:" or (spec["context"] and prefix == "175-")
    return prefix == ""


# ------------------------------------------------------------------------------------------------- the git read
# B20-5 (glitch-26's ruling, lane vendor-b20, 20 Oct 2026; Gemini practice walk w-g11): OD57's line, by its content
# sha256, is also admitted where a git diff carries it: exactly one leading "+", "-" or " " before its 80 bytes, inside a
# hunk of the ruled doc's own diff (`diff --git a/<doc> b/<doc>`, then a `@@ ` hunk header, then diff body lines only),
# in the output of a git read of the take's own repo. Only through the read shapes (the Gemini and Codex arms' one shared
# path); the Claude path is unchanged. B20-7: the read is exactly `git log -p -n 1 <commit>` or `git show <commit>`,
# <commit> 7 to 40 lowercase hex digits, words split on single spaces; the diff header names the doc's own repo path,
# gars/_references/environment.md, exactly, on both sides. B20-6: the read's folder is bound by its shape's `git` record
# (an optional shape key; a shape without it admits no git read): {"args": (key, ...)}, the call's arguments hold no
# key but those, or {"cwd": node key, "prefix": str, "meta": (RECORD, dotted key)}, the call node's folder is exactly
# prefix + the value at the dotted key of the file's one RECORD record.
_GIT_COMMIT = re.compile(r"[0-9a-f]{7,40}")
_DIFF_PREFIXES = ("+", "-", " ")
_GIT_HEADER = re.compile(r"diff --git a/(\S+) b/(\S+)")
GIT_KEYS = (("args",), ("cwd", "prefix", "meta"))


def _ruled_git(cmd) -> bool:
    """A git read B20-5 and B20-7 admit: exactly `git log -p -n 1 <commit>` or `git show <commit>`."""
    if not isinstance(cmd, str):
        return False
    t = cmd.split(" ")
    if len(t) == 6 and t[:5] == ["git", "log", "-p", "-n", "1"]:
        c = t[5]
    elif len(t) == 3 and t[:2] == ["git", "show"]:
        c = t[2]
    else:
        return False
    return _GIT_COMMIT.fullmatch(c) is not None


def _git_ok(shape) -> bool:
    """A shape's optional `git` record on its closed schema (B20-6)."""
    if "git" not in shape:
        return True
    git = shape["git"]
    if not (isinstance(git, dict) and tuple(sorted(git)) in tuple(tuple(sorted(k)) for k in GIT_KEYS)):
        return False
    if "args" in git:
        return _strs_ok(git["args"])
    meta = git["meta"]
    return (isinstance(git["cwd"], str) and git["cwd"] != "" and isinstance(git["prefix"], str)
            and isinstance(meta, tuple) and len(meta) == 2 and isinstance(meta[0], dict) and meta[0] != {}
            and all(isinstance(k, str) and k and _strs_ok(v) for k, v in meta[0].items())
            and isinstance(meta[1], str) and meta[1] != "")


def _git_meta(records, shape):
    """B20-6: the run tree a shape's `git` cwd binding names: the absolute path at its meta key in the file's one record
    of its meta type, else None."""
    git = shape.get("git") or {}
    if "meta" not in git:
        return None
    record, key = git["meta"]
    metas = [_record_value(rec, key) for _, rec in records
             if isinstance(rec, dict) and all(_record_value(rec, k) in v for k, v in record.items())]
    return metas[0] if len(metas) == 1 and isinstance(metas[0], str) and metas[0].startswith("/") else None


def _git_bound(shape, node, meta):
    """B20-6: True when a call node's folder is exactly the shape's prefix + the file's run tree; None when the shape
    binds no folder or the file names no run tree."""
    git = shape.get("git") or {}
    if "cwd" not in git or meta is None:
        return None
    return node.get(git["cwd"]) == git["prefix"] + meta


def _git_doc_header(line) -> bool:
    """A `diff --git` header of the ruled doc's own repo path, the same on both sides (B20-5, B20-7)."""
    m = _GIT_HEADER.fullmatch(line)
    return m is not None and m[1] == m[2] and m[2] == _RULED_GIT_PATH


def _ruled_diff_line(lines, i, ruling):
    """B20-5: the ruled text when line i of a git read's output is exactly one diff prefix and the ruled text, inside a
    hunk of the ruled doc's own diff, else None."""
    ln = lines[i]
    if ln[:1] not in _DIFF_PREFIXES:
        return None
    rest = ln[1:].encode("utf-8", "surrogateescape")
    if len(rest) != ruling["bytes"] or _sha(rest) != ruling["sha256"]:
        return None
    j = i - 1
    while j >= 0 and not lines[j].startswith("@@ "):
        if lines[j][:1] not in _DIFF_PREFIXES + ("\\",):
            return None
        j -= 1
    k = j - 1
    while k >= 0 and not lines[k].startswith("diff --git "):
        k -= 1
    if k < 0:
        return None
    return rest.decode() if _git_doc_header(lines[k]) else None


# ------------------------------------------------------------------------------------------------- Gemini grep_search
# B24-2 item 2 as revised (glitch-26, 21 Oct 2026). Gemini CLI 0.64.0's grep_search, read from the pinned bundle
# (bundle/chunk-NR7L3FXV.js, sha256 d566e81b..., the take-g image; lane-reports/vendor-b24-LANE.md round 2 stage 0):
# - its model-facing output (321667-321690): `Found N match(es) for pattern "<p>" <where>...:`, then per file `---`,
#   `File: <path>` and one `L<n><sep> <line.trimEnd()>` per line, sep `:` for a match and `-` for a context line
#   (321678, 321684), the whole trimmed;
# - its display (321691-321698): {summary, matches: the match lines only, never a context line, each {filePath,
#   absolutePath, lineNumber, line}};
# - auto-context (321596-321635): with 1 to 3 matches and none of names_only, context, before, after set, the tool reads
#   each matched file and adds 50 lines (one match) or 15 lines around each match as context lines.
# A line is admitted only as `L175: ` or `L175- ` and the 80 bytes, inside a block whose File: header joined to the
# call's dir_path names the doc; a match line only when the call's own display holds the doc's match 175 with exactly
# those bytes; a context line only when that display holds a match on the doc and 175 lies in the window the call made
# (its explicit context, before and after; else the auto window). Line 0 (it carries the model's pattern) never is.
_GREP_ARGS = ("pattern", "dir_path", "include_pattern", "context", "before", "after")
_GREP_ROW = re.compile(r"L([0-9]+)([:-]) (.*)", re.S)


def _grep_ruled_number() -> int:
    return 175


def _count(v) -> bool:
    return type(v) is int and v >= 0


def _grep_args_ok(args) -> bool:
    """grep_search's arguments this rule reads: a pattern, and only the keys it names (numbers for the context ones)."""
    return (isinstance(args, dict) and set(args) <= set(_GREP_ARGS) and isinstance(args.get("pattern"), str)
            and args["pattern"] != "" and all(isinstance(args[k], str) for k in ("dir_path", "include_pattern")
                                              if k in args)
            and all(_count(args[k]) for k in ("context", "before", "after") if k in args))


def _abs_doc(p) -> bool:
    """A display entry's absolutePath that is the run tree's doc."""
    return isinstance(p, str) and p.startswith("/") and _resolves_to_doc(p)


def _attests(m, text) -> bool:
    """A display entry for the doc's match 175 whose line is exactly `text`."""
    return isinstance(m, dict) and m.get("lineNumber") == _grep_ruled_number() and type(m.get("lineNumber")) is int \
        and m.get("line") == text


def _grep_names_doc(dir_path, header) -> bool:
    """A File: header, joined to the call's dir_path, that names the doc (no `..` anywhere)."""
    if not isinstance(header, str) or not header or (dir_path is not None and not isinstance(dir_path, str)):
        return False
    return _resolves_to_doc(header, dir_path or None)          # R3-1: the one run-tree check


def _grep_window(args, matches, docs) -> bool:
    """Whether 175 lies in a context window the call produced around one of the doc's matches."""
    target = _grep_ruled_number()
    numbers = [m["lineNumber"] for m in docs if type(m.get("lineNumber")) is int]
    if any(k in args for k in ("context", "before", "after")):
        ctx = args.get("context", 0)
        before = args.get("before", ctx)
        after = args.get("after", ctx)
        return any(n - before <= target <= n + after for n in numbers)
    if not 1 <= len(matches) <= 3:
        return False                         # auto-context fires for 1 to 3 matches only (321598)
    cl = 50 if len(matches) == 1 else 15     # 321599
    return any(abs(target - n) <= cl for n in numbers)


def _grep_line(lines, i, tool, ruling):
    """The ruled text when output line i of a ruled grep_search is admitted (the rule above), else None."""
    m = _GREP_ROW.fullmatch(lines[i])
    if m is None or int(m[1]) != _grep_ruled_number() or str(int(m[1])) != m[1] or not _is_ruled(m[3], ruling):
        return None
    text = m[3]
    j = i - 1
    while j >= 1 and _GREP_ROW.fullmatch(lines[j]) is not None and not lines[j].startswith("File: "):
        j -= 1
    if j < 1 or not lines[j].startswith("File: ") or lines[j - 1] != "---":
        return None
    args, matches = tool["grep"]
    if not _grep_names_doc(args.get("dir_path"), lines[j][len("File: "):]):
        return None
    docs = [x for x in matches if isinstance(x, dict) and _abs_doc(x.get("absolutePath"))]
    if m[2] == ":":
        if not any(_attests(m, text) for m in docs):
            return None
        return text
    if not docs or not _grep_window(args, matches, docs):
        return None
    return text


def _grep_display(node, ruling):
    """The ruled text of each display entry that attests the doc's match 175."""
    return [m["line"] for m in node if isinstance(m, dict) and _abs_doc(m.get("absolutePath"))
            and _attests(m, m.get("line")) and _is_ruled(m.get("line"), ruling)]


# ------------------------------------------------------------------------------------------------- read shapes (B17)
# glitch-26's rulings B17-5 to B17-7 (lane vendor-b17 round 2, 19 Oct 2026; lane-reports/B17-DESIGN-NOTE.md): OD57
# admits its line in another agent's read of the same doc through READ SHAPES (box/od57_shapes; the drive passes them
# per row). A shape says, as data only, how a read's call and its result are found in a record file; this module checks
# every shape against the closed schema below and keeps each OD57 constraint in its own code.
#
#   shape   {"shape": label, "call": CALL, "result": RESULT or None, "copies": "one" | "same", "tools": TOOLS,
#            "copy_of": index or None, "kinds": (file kind, ...), ["git": GIT]}
#   CALL    {"match": {key: value}, "at": ((path, RECORD, anchor), ...), "id": key, "name": {"key": key} or
#            {"value": name}, "args": key, "args_json": bool, "text": (path, ...)}   (text only when result is None)
#   RESULT  {"match": {key: value}, "at": ((path, RECORD, anchor), ...), "id": key, "name": key or None,
#            "text": (path, ...)}
#   RECORD  {(dotted) top-level key: (allowed value, ...)}
#   TOOLS   {tool name: TOOL}
#   TOOL    {"kind": "path" | "script" | "wrapped" | "argv" | "copy" | "grep" | "grep-display", "arg": key or None,
#            "prefix": str or None, "opener": str or None, "shells": (absolute path, ...) or None,
#            "flags": (flag, ...) or None}
# A node is the JSON object at the end of one of its spec's `at` paths, in a record whose keys hold one of the RECORD's
# values each, holding every `match` value and a string id, at a fixed position (B17-10), its id equal to its anchor
# object's when the position has one (B17-17). A wrapped tool's argv is exactly [one of its `shells`, one of its
# `flags`, a script _ruled_shell admits] (B17-12, B17-14, B17-16a); kind "argv" takes the list form only. A COPY shape
# (B17-16b to B17-22) admits the ruled line in its result only inside a verbatim copy, or one exact JSON string literal,
# of a read its `copy_of` joined shape admits between its own call's line and its own line. B24: kind "grep" is
# grep_search's output (arg dir_path), kind "grep-display" its display's match entries (the call's text path ends at
# each entry); both read the call's own display.
SHAPE_KEYS = ("shape", "call", "result", "copies", "tools", "copy_of", "kinds")
CALL_KEYS = ("match", "at", "id", "name", "args", "args_json", "text")
RESULT_KEYS = ("match", "at", "id", "name", "text")
TOOL_KEYS = ("kind", "arg", "prefix", "opener", "shells", "flags")
COPIES = ("one", "same")
TOOL_KINDS = ("path", "script", "wrapped", "argv", "copy", "grep", "grep-display")
AGENT_TEXT_KINDS = ("transcript", "stream", "session")


def _opt_str(v) -> bool:
    return v is None or (isinstance(v, str) and v != "")


def _path_ok(p, empty) -> bool:
    return isinstance(p, tuple) and (empty or p != ()) and all(isinstance(k, str) and k for k in p)


def _paths_ok(paths) -> bool:
    return isinstance(paths, tuple) and all(_path_ok(p, False) for p in paths)


def _strs_ok(v) -> bool:
    return isinstance(v, tuple) and v != () and all(isinstance(s, str) and s for s in v)


def _at_ok(at) -> bool:
    return (isinstance(at, tuple) and len(at) == 3 and _path_ok(at[0], True) and isinstance(at[1], dict)
            and all(isinstance(k, str) and k and _strs_ok(v) for k, v in at[1].items())
            and (at[2] is None or (type(at[2]) is int and 0 < at[2] < len(at[0]))))


def _node_ok(spec, keys) -> bool:
    return (isinstance(spec, dict) and set(spec) == set(keys) and isinstance(spec["match"], dict)
            and all(isinstance(k, str) and isinstance(v, str) for k, v in spec["match"].items())
            and isinstance(spec["at"], tuple) and spec["at"] != () and all(_at_ok(a) for a in spec["at"])
            and isinstance(spec["id"], str) and spec["id"] != "" and _paths_ok(spec["text"]))


def _tool_ok(tool) -> bool:
    wrapped = isinstance(tool, dict) and tool.get("kind") in ("wrapped", "argv")
    return (isinstance(tool, dict) and set(tool) == set(TOOL_KEYS) and tool["kind"] in TOOL_KINDS
            and _opt_str(tool["arg"]) and (tool["arg"] is not None or tool["kind"] in ("wrapped", "argv", "copy"))
            and _opt_str(tool["prefix"]) and _opt_str(tool["opener"])
            and (tool["opener"] is None or tool["prefix"] is not None)
            and (tool["kind"] not in ("grep", "grep-display") or tool["prefix"] is None)
            and (_strs_ok(tool["shells"]) and all(s.startswith("/") for s in tool["shells"]) and _strs_ok(tool["flags"])
                 if wrapped else tool["shells"] is None and tool["flags"] is None))


def _shape_ok(shape) -> bool:
    if not (isinstance(shape, dict) and set(shape) - {"git"} == set(SHAPE_KEYS) and _git_ok(shape)
            and isinstance(shape["shape"], str)
            and shape["copies"] in COPIES and isinstance(shape["tools"], dict) and shape["tools"]
            and all(isinstance(k, str) and _tool_ok(t) for k, t in shape["tools"].items())
            and _strs_ok(shape["kinds"]) and all(k in AGENT_TEXT_KINDS for k in shape["kinds"])):
        return False
    call, result = shape["call"], shape["result"]
    if not (_node_ok(call, CALL_KEYS) and isinstance(call["name"], dict) and len(call["name"]) == 1
            and set(call["name"]) <= {"key", "value"} and all(isinstance(v, str) and v for v in call["name"].values())
            and isinstance(call["args"], str) and call["args"] != "" and type(call["args_json"]) is bool):
        return False
    if result is None:
        return call["text"] != ()
    return call["text"] == () and _node_ok(result, RESULT_KEYS) and result["text"] != () and _opt_str(result["name"])


def _copy_ok(shapes, i) -> bool:
    """A shape's copy_of: None with no copy tool, or the index of another, joined, non-copy shape with copy tools only."""
    shape, kinds = shapes[i], [t["kind"] for t in shapes[i]["tools"].values()]
    k = shape["copy_of"]
    if k is None:
        return "copy" not in kinds
    return (type(k) is int and 0 <= k < len(shapes) and k != i and shapes[k]["result"] is None
            and shapes[k]["copy_of"] is None and shape["result"] is not None and all(x == "copy" for x in kinds))


def check_shapes(read_shapes) -> tuple:
    """The caller's read shapes, each checked against the closed schema; ValueError on any other."""
    if not isinstance(read_shapes, tuple) or not all(_shape_ok(s) for s in read_shapes) \
            or not all(_copy_ok(read_shapes, i) for i, _ in enumerate(read_shapes)):
        raise ValueError("read shapes are a tuple of shape records on the closed schema (SHAPE_KEYS, CALL_KEYS, "
                         "RESULT_KEYS, TOOL_KEYS)")
    return read_shapes


def _record_value(rec, key):
    """The one value at a record's (dotted) key, else None."""
    got = _path_values(rec, tuple(key.split(".")), [])
    return got[0] if len(got) == 1 else None


def _anchored(rec, path, anchor) -> list:
    """(node, its anchor object or None) at a position's path."""
    if anchor is None:
        return [(n, None) for n in _path_values(rec, path, [])]
    return [(n, a) for a in _path_values(rec, path[:anchor], []) for n in _path_values(a, path[anchor:], [])]


def _shape_nodes(rec, spec) -> list:
    """The objects a node spec finds in a decoded record: only at its fixed positions (B17-10), in a record of the
    position's type, answering their anchor object's id when the position has one."""
    return [n for path, record, anchor in spec["at"]
            if isinstance(rec, dict) and all(_record_value(rec, k) in v for k, v in record.items())
            for n, a in _anchored(rec, path, anchor)
            if isinstance(n, dict) and isinstance(n.get(spec["id"]), str)
            and all(n.get(k) == v for k, v in spec["match"].items())
            and (a is None or (isinstance(a, dict) and a.get(spec["id"]) == n.get(spec["id"])))]


def _shape_call(node, spec):
    """(tool name, arguments) of a call node, or None when it names no tool."""
    name = spec["name"]["value"] if "value" in spec["name"] else node.get(spec["name"]["key"])
    if not isinstance(name, str):
        return None
    args = node.get(spec["args"])
    if spec["args_json"]:
        try:
            args = json.loads(args) if isinstance(args, str) else None
        except (ValueError, RuntimeError):
            args = None
    return name, args


def _shape_calls(records, shapes, kind=None) -> list:
    """Per shape, ({call id: [(tool name, arguments, folder bound: B20-6)]}: every copy of each call; for a copy shape
    the (line, text, tool entry) of each read its copy_of shape admits in this file, else (); {call id: [its lines]};
    {call id: [its output lines]}; {call id: [its call node's display]}). A shape whose kinds do not hold the file's kind
    finds nothing."""
    calls_of, lines_of, displays_of = [], [], []
    for shape in shapes:
        calls, lines, displays = {}, {}, {}
        if kind in shape["kinds"]:
            meta = _git_meta(records, shape)                    # B20-6: the run tree, for a cwd-bound shape
            for n, rec in records:
                for node in _shape_nodes(rec, shape["call"]):
                    got = _shape_call(node, shape["call"])
                    if got is not None:
                        cid = node[shape["call"]["id"]]
                        calls.setdefault(cid, []).append(got + (_git_bound(shape, node, meta),))
                        lines.setdefault(cid, []).append(n)
                        displays.setdefault(cid, []).append(node.get("resultDisplay"))
        calls_of.append(calls)
        lines_of.append(lines)
        displays_of.append(displays)
    out = []
    for shape, calls, lines, displays in zip(shapes, calls_of, lines_of, displays_of):
        sources, out_lines = [], {}
        if shape["copy_of"] is not None and kind in shape["kinds"]:
            for n, rec in records:
                for node in _shape_nodes(rec, shape["result"]):
                    out_lines.setdefault(node[shape["result"]["id"]], []).append(n)
            # B17-21: an exec window is one call line and its one output line; a read counts only inside exactly one
            windows = [(lines[c][0], out_lines[c][0]) for c in out_lines
                       if len(lines.get(c) or ()) == 1 and len(out_lines[c]) == 1]
            k = shape["copy_of"]
            for n, rec in records:
                if sum(1 for c, o in windows if c < n < o) == 1:
                    sources += [(n, s, t) for s, t in _shape_strings(
                        rec, (shapes[k],), ((calls_of[k], (), lines_of[k], {}, displays_of[k]),))]
        out.append((calls, tuple(x for x in sources if x[1]), lines, out_lines, displays))
    return out


def _ruled_wrapped(argv, shells, flags, lists_only=False, script=None):
    """The script of a shell wrapper OD57 admits: exactly [<one of `shells`>, <one of `flags`>, <script>], as an
    argument list or (unless lists_only) as its shell-quoted string, else None. `script` checks the script (the shell
    read's spec when None)."""
    if isinstance(argv, str) and not lists_only:
        try:
            lex = shlex.shlex(argv, posix=True)
            lex.whitespace_split = True
            lex.commenters = ""
            argv = list(lex)
        except ValueError:
            return None
    if not (isinstance(argv, list) and len(argv) == 3 and all(isinstance(a, str) for a in argv)):
        return None
    if argv[0] not in shells or argv[1] not in flags:
        return None
    if script is not None:
        return argv[2] if script(argv[2]) else None
    return _ruled_shell(argv[2])


def _tool_arg(tool, args):
    if tool["arg"] is None:
        return args
    return args.get(tool["arg"]) if isinstance(args, dict) else None


def _reads_doc(tool, args, display=None):
    """The tool entry a call's arguments make a read of the ruled doc, else None (a copy tool's own read is the copy
    rule's, in _shape_strings)."""
    if tool["kind"] == "copy":
        return dict(tool)
    arg = _tool_arg(tool, args)
    if tool["kind"] == "path":
        return dict(tool) if _resolves_to_doc(arg) else None
    if tool["kind"] in ("grep", "grep-display"):
        if not _grep_args_ok(args):
            return None
        matches = display.get("matches") if isinstance(display, dict) else None
        if not isinstance(matches, list):
            return None
        return dict(tool, grep=(args, matches))
    if tool["kind"] == "script":
        spec = _ruled_shell(arg)
        if spec is None:                                  # od57-gap: the compound read, every arm
            spec = _ruled_compound(arg)
    else:
        spec = _ruled_wrapped(arg, tool["shells"], tool["flags"], tool["kind"] == "argv")
        if spec is None:                                  # od57-gap: the compound read inside the same wrapper
            inner = _ruled_wrapped(arg, tool["shells"], tool["flags"], tool["kind"] == "argv",
                                   lambda s: _ruled_compound(s) is not None)
            spec = _ruled_compound(inner) if inner is not None else None
    return dict(tool, spec=spec) if spec is not None else None


def _reads_git(shape, tool, call) -> bool:
    """B20-5, B20-6: whether a call makes its shell tool a git read _ruled_git admits, its folder bound by the shape."""
    _, args, bound = call
    git = shape.get("git") or {}
    if "args" in git:
        if not (isinstance(args, dict) and set(args) <= set(git["args"])):
            return False
    elif bound is not True:
        return False
    arg = _tool_arg(tool, args)
    if tool["kind"] in ("wrapped", "argv"):
        return _ruled_wrapped(arg, tool["shells"], tool["flags"], tool["kind"] == "argv", _ruled_git) is not None
    return tool["kind"] == "script" and _ruled_git(arg)


def _shape_read(shape, calls, cid, name, displays=None):
    """The tool entry of the one read of the ruled doc that call id `cid` finds, or None: the id's copies (exactly one
    for copies "one"; every copy the same name and arguments: B17-6), the result's own name when it carries one, a
    tool the shape names, and arguments that read the doc (a grep's display: exactly one distinct one)."""
    got = calls.get(cid)
    if not got or (shape["copies"] == "one" and len(got) != 1):
        return None
    if any(g != got[0] for g in got):
        return None
    tool = shape["tools"].get(got[0][0])
    if tool is None or (name is not None and name != got[0][0]):
        return None
    display = None
    if tool["kind"] in ("grep", "grep-display"):
        shown = {json.dumps(d, sort_keys=True) for d in (displays or {}).get(cid, [])}
        if len(shown) != 1:
            return None
        display = json.loads(shown.pop())
    read = _reads_doc(tool, got[0][1], display)
    if read is not None:
        return read
    if _reads_git(shape, tool, got[0]):
        return dict(tool, git=True)                                  # B20-5: its output read as a diff
    return None


def _json_value_at(s, p) -> bool:
    """Whether a JSON string literal starting at s[p] sits at a JSON value position: the first non-whitespace
    character before it is `:`, `[` or `,` (B17-22)."""
    j = p - 1
    while j >= 0 and s[j] in " \t\r\n":
        j -= 1
    return j >= 0 and s[j] in ":[,"


def _copy_hits(s, srcs, ruling) -> list:
    """The ruled text once per distinct position of it in `s` that lies inside a verbatim copy of a source, or inside
    the one JSON string literal of a source that `s` holds (json.dumps with non-ASCII raw, as JSON.stringify writes it;
    exactly one such literal, at a JSON value position), the position being an admitted line of that source (B17-17a,
    B17-18, B17-20, B17-22). srcs: [(text, tool entry)]."""
    hits, seen = [], set()
    for a, tool in srcs:
        found, at, lines_a = [], 0, a.split("\n")
        for i, ln in enumerate(lines_a):
            f = _line_text(lines_a, i, tool, ruling, None)
            if f is not None:
                found.append((at + len(ln) - len(f), f))
            at += len(ln) + 1
        e = json.dumps(a, ensure_ascii=False)
        one = s.count(e) == 1
        for k, f in found:
            spans = [(k, None), (len(json.dumps(a[:k], ensure_ascii=False)) - 1, e)]
            q = s.find(f)
            while q != -1:
                for kk, lit in spans:
                    p = q - kk
                    if p < 0:
                        continue
                    if lit is None:
                        ok = s[p:p + len(a)] == a
                    else:
                        ok = one and s[p:p + len(e)] == e and _json_value_at(s, p) and json.loads(e) == a
                    if ok:
                        if q not in seen:
                            seen.add(q)
                            hits.append(f)
                q = s.find(f, q + 1)
    return hits


def _shape_strings(rec, shapes, indexes, ruling=None, line=None) -> list:
    """(text, tool entry) for every string a ruled read's result carries in this record, by the read shapes; a copy
    result's text is its admitted positions (_copy_hits) among the reads of its own exec pair (B17-19); a grep display's
    is each entry that attests the doc's match 175."""
    out = []
    for shape, (calls, sources, call_lines, out_lines, displays) in zip(shapes, indexes):
        joined = shape["result"] is None
        spec = shape["call"] if joined else shape["result"]
        for node in _shape_nodes(rec, spec):
            if joined and _shape_call(node, spec) is None:
                continue                      # a joined result is itself a copy of its call
            name = None
            if not joined and spec["name"] is not None:
                name = node.get(spec["name"])
                if not isinstance(name, str):
                    continue
            tool = _shape_read(shape, calls, node[spec["id"]], name, displays)
            if tool is None:
                continue
            for path in spec["text"]:
                for s in _path_values(node, path, []):
                    if tool["kind"] == "grep-display":
                        if isinstance(s, list) and ruling is not None:
                            out += [(f, dict(tool, kind="exact")) for f in _grep_display(s, ruling)]
                        continue
                    if not isinstance(s, str):
                        continue
                    if tool["kind"] != "copy":
                        out.append((s, tool))
                        continue
                    cl = call_lines.get(node[spec["id"]])
                    if ruling is None or line is None or not cl:
                        continue
                    if len(out_lines.get(node[spec["id"]]) or ()) != 1:
                        continue              # B17-21: one output per exec call
                    if len(cl) != 1:
                        continue
                    srcs = [(t, tl) for ln, t, tl in sources if cl[0] < ln < line]
                    out += [(f, dict(tool, kind="exact")) for f in _copy_hits(s, srcs, ruling)]
    return out


# ------------------------------------------------------------------------------------------------- one line's rule
def _line_prefix(tool, lines, i):
    """The tool's own prefix when line i is its result's first line (after its opener line), else None."""
    if tool is None or tool.get("prefix") is None:
        return None
    first = 1 if tool.get("opener") is not None and lines[0] == tool["opener"] else 0
    return tool["prefix"] if i == first else None


def _claude_grep_prefix(prefix) -> bool:
    """A Claude Code Grep content line's prefix (the path is the doc): none, rg's number, or its label and number."""
    if prefix in ("", "175:", "175-"):
        return True
    for sep in ":-":
        for tail in (sep + "175" + sep, sep):
            if prefix.endswith(tail) and len(prefix) > len(tail) and _resolves_to_doc(prefix[:-len(tail)]):
                return True
    return False


def _line_text(lines, i, tool, ruling, extra):
    """The ruled text when line i of a ruled read's result is admitted by that read's own line rule, else None."""
    ln = lines[i]
    kind = tool["kind"]
    if tool.get("git"):
        return _ruled_diff_line(lines, i, ruling)
    if kind == "grep":
        return _grep_line(lines, i, tool, ruling)
    if kind == "exact":
        return ln if _is_ruled(ln, ruling) else None
    forms = [ln] + ([ln[len(extra):]] if extra is not None and ln.startswith(extra) else [])
    for form in forms:
        b = form.encode("utf-8", "surrogateescape")
        if len(b) < ruling["bytes"]:
            continue
        rest, prefix = b[-ruling["bytes"]:], b[:-ruling["bytes"]].decode("utf-8", "surrogateescape")
        if _sha(rest) != ruling["sha256"]:
            continue
        if kind == "path":
            ok = prefix == ""
        elif kind == "read":
            ok = prefix == "" or _READ_PREFIX.fullmatch(prefix) is not None
        elif kind == "claude-grep":
            ok = _claude_grep_prefix(prefix)
        elif kind in ("script", "wrapped", "argv", "shell"):
            ok = _shell_prefix_ok(prefix, tool["spec"])
        elif kind == "any":
            ok = _any_prefix_ok(prefix)
        else:
            ok = False
        if ok:
            return rest.decode()
    return None


# ------------------------------------------------------------------------------------------------- od57-line
# A whole output line of a shell tool (SCANREFUSAL-ROAD-20261108, candidate 3 narrowed), the fallback after the reads
# above: the producer is whitelisted (Claude's Bash and BashOutput; for a vendor, a shell tool its read shape names, or
# that tool's output copy), the prefix is closed and the 80 bytes end the line. Read, Grep and the vendors' path and
# grep tools keep their own path-bound rules: a read of another path is no read of the doc.
_ANY_CLAUDE_TOOLS = ("Bash", "BashOutput")
_ANY_SHAPE_KINDS = ("script", "wrapped", "argv", "copy")    # a vendor shape's shell tools and their output copy
_ANY = {"kind": "any"}


def _any_prefix_ok(prefix) -> bool:
    """A whole output line's prefix: none, `175:`, Claude Read's, or a label naming the doc with or without `175:`."""
    if prefix in ("", "175:") or _READ_PREFIX.fullmatch(prefix) is not None:
        return True
    for tail in (":175:", ":"):
        if prefix.endswith(tail) and len(prefix) > len(tail) and _resolves_to_doc(prefix[:-len(tail)]):
            return True
    return False


def _any_claude_strings(rec, uses) -> list:
    """(string, _ANY) for each tool_result block answering exactly one whitelisted call, and every string under the
    record's own tool-result keys when every tool_result block of the record does. Blocks only at the record's own
    positions (B17-11)."""
    blocks, out, named = _top_blocks(rec, "tool_result"), [], []
    for b in blocks:
        tid = b.get("tool_use_id")
        got = uses.get(tid) if isinstance(tid, str) else None
        ok = bool(got) and len(got) == 1 and got[0][0] in _ANY_CLAUDE_TOOLS
        named.append(ok)
        if not ok:
            continue
        c = b.get("content")
        if isinstance(c, str):
            out.append((c, _ANY))
        elif isinstance(c, list):
            out += [(i["text"], _ANY) for i in c if isinstance(i, dict) and i.get("type") == "text"
                    and isinstance(i.get("text"), str)]
    if isinstance(rec, dict) and blocks and all(named):
        for k, v in rec.items():
            if k in _TOOL_RESULT_KEYS:
                out += [(s, _ANY) for s in _strings(v, [])]
    return out


def _any_shape_strings(rec, shapes, indexes) -> list:
    """(string, _ANY) for each string a read shape's result (or joined call) carries in this record, its call found as
    _shape_read finds it (the id's copies, the same each, the result's own name) and naming one of the shape's shell
    tools (or their output copy), whatever its arguments; a path or grep tool stays with its own read rule."""
    out = []
    for shape, (calls, _, _, _, _) in zip(shapes, indexes):
        joined = shape["result"] is None
        spec = shape["call"] if joined else shape["result"]
        for node in _shape_nodes(rec, spec):
            if joined and _shape_call(node, spec) is None:
                continue
            name = None
            if not joined and spec["name"] is not None:
                name = node.get(spec["name"])
                if not isinstance(name, str):
                    continue
            got = calls.get(node[spec["id"]])
            if not got or (shape["copies"] == "one" and len(got) != 1) or any(g != got[0] for g in got):
                continue
            tool = shape["tools"].get(got[0][0])
            if tool is None or tool["kind"] not in _ANY_SHAPE_KINDS or (name is not None and name != got[0][0]):
                continue
            for path in spec["text"]:
                out += [(s, _ANY) for s in _path_values(node, path, []) if isinstance(s, str)]
    return out


def _any_text(rec, body, uses, shapes, indexes, kind, ruling):
    """od57-line: the ruled text when this record carries it only as whole output lines of whitelisted tools, each
    counted the way ruled_text counts; else None. T1 is ruled_text's, checked before this is reached."""
    if kind not in AGENT_TEXT_KINDS or not isinstance(rec, dict):
        return None
    found, hits = None, 0
    for s, tool in _any_claude_strings(rec, uses) + _any_shape_strings(rec, shapes, indexes):
        lines = s.split("\n")
        for i in range(len(lines)):
            text = _line_text(lines, i, tool, ruling, None)
            if text is not None:
                found, hits = text, hits + 1
    if found is None:
        return None
    if json.dumps(found)[1:-1] != found or sum(x.count(found) for x in _strings(rec, [])) != hits \
            or body.count(found.encode()) != hits:
        return None
    return found


# ------------------------------------------------------------------------------------------------- T1: writes first
# B24-2 item 4: a write of the doc earlier in the same file disqualifies every later admission there (at or after the
# write's own record line). Writes: Claude Code's Write, Edit, MultiEdit and NotebookEdit; Gemini's write_file and
# replace (session toolCalls and functionCall parts; stream tool_use); Codex's file_change (stream item, started or
# completed) and a rollout FileChange item; a rollout custom_tool_call whose script calls apply_patch on the doc.
_WRITE_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit", "write_file", "replace")


def _may_name_doc(p) -> bool:
    """R3-3: a written path that may be the doc: normalised first (`./`, `//`, `..` resolved lexically), then the
    doc's suffix. Wider than _resolves_to_doc on purpose (no run-tree binding, `..` allowed): a write disqualifies, so
    a wider match fails closed."""
    if not isinstance(p, str) or not p:
        return False
    n = posixpath.normpath(p)
    return n == _RULED_DOC or n.endswith("/" + _RULED_DOC)


_PATCH_FILE = re.compile(r"\*\*\* (?:Add|Update|Delete) File: (.+)|\*\*\* Move to: (.+)")


def _writes_doc(name, args) -> bool:
    if name not in _WRITE_TOOLS or not isinstance(args, dict):
        return False
    return any(_may_name_doc(args.get(k)) for k in ("file_path", "notebook_path"))


def _change_paths(changes) -> list:
    if isinstance(changes, dict):
        return list(changes)
    if isinstance(changes, list):
        return [c.get("path") for c in changes if isinstance(c, dict)]
    return []


def _record_writes_doc(rec) -> bool:
    if not isinstance(rec, dict):
        return False
    for b in _top_blocks(rec, "tool_use"):
        if _writes_doc(b.get("name"), b.get("input")):
            return True
    if rec.get("type") == "gemini":
        for c in rec.get("toolCalls") or [] if isinstance(rec.get("toolCalls"), list) else []:
            if isinstance(c, dict) and _writes_doc(c.get("name"), c.get("args")):
                return True
        for p in rec.get("content") or [] if isinstance(rec.get("content"), list) else []:
            fc = p.get("functionCall") if isinstance(p, dict) else None
            if isinstance(fc, dict) and _writes_doc(fc.get("name"), fc.get("args")):
                return True
    if rec.get("type") == "tool_use" and _writes_doc(rec.get("tool_name"), rec.get("parameters")):
        return True
    item = rec.get("item")
    if isinstance(item, dict) and item.get("type") == "file_change" \
            and any(_may_name_doc(p) for p in _change_paths(item.get("changes"))):
        return True
    payload = rec.get("payload")
    if isinstance(payload, dict):
        pitem = payload.get("item")
        if isinstance(pitem, dict) and pitem.get("type") == "FileChange" \
                and any(_may_name_doc(p) for p in _change_paths(pitem.get("changes"))):
            return True
        inp = payload.get("input")
        if payload.get("type") == "custom_tool_call" and isinstance(inp, str) and "apply_patch" in inp \
                and (_RULED_DOC in inp or any(_may_name_doc((m[1] or m[2]).strip().strip("\\\"'"))
                                              for m in _PATCH_FILE.finditer(inp))):
            return True
    return False


def _first_write(records):
    """The line of the file's first write of the doc, else None."""
    return next((n for n, rec in records if _record_writes_doc(rec)), None)


# ------------------------------------------------------------------------------------------------- the entry point
def ruled_text(body, ruling, data, shapes=(), kind=None, line=None):
    """The ruled line's text when this JSON record carries it only as whole admitted lines of ruled reads of the doc
    (Claude Code's, or the read shapes'), each counted, and no write of the doc comes at or before `line` in the file
    whose bytes are `data`; else None."""
    try:
        rec = json.loads(body)
    except ValueError:
        return None
    records = _records(data)
    writes = _first_write(records)
    if writes is not None and writes <= line:
        return None
    uses = _tool_uses(data)
    indexes = _shape_calls(records, shapes, kind) if shapes else ()
    found, hits = None, 0
    for s, tool in _tool_result_strings(rec, uses, []) + _shape_strings(rec, shapes, indexes, ruling, line):
        lines = s.split("\n")
        for i in range(len(lines)):
            text = _line_text(lines, i, tool, ruling, _line_prefix(tool, lines, i))
            if text is not None:
                found, hits = text, hits + 1
    if found is None:
        return _any_text(rec, body, uses, shapes, indexes, kind, ruling)       # od57-line
    # the text must sit in the record only where it was counted, and appear raw exactly as often (it needs no JSON
    # escape), so the probe removes those occurrences and nothing else
    if json.dumps(found)[1:-1] != found or sum(x.count(found) for x in _strings(rec, [])) != hits \
            or body.count(found.encode()) != hits:
        return None
    return found
