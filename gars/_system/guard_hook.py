#!/usr/bin/env python3
"""PreToolUse guard for a GARS workspace: the Scope Boundaries that CAN be mechanical, made so.

Wired by `.claude/settings.json`, which the agent harness loads when a session starts in the
workspace root (`gars/`). The harness sends one JSON object on stdin per tool call:

    {"tool_name": "...", "tool_input": {...}, "cwd": "..."}

Exit 0 allows the call. Exit 2 blocks it, and stderr is shown to the agent as the reason --
so every refusal names the rule and where it is written, the same way a contract template would.

Why this exists (decision 0022): prose scope boundaries were violated in real runs (0002, 0018).
The one rule that has never been violated is the one the filesystem enforces -- `files.csv` at
mode 0444. This hook generalizes that: a write the contracts forbid should fail at the moment it
is attempted, not be noticed two stages later. Prose remains for what genuinely cannot be
checked here (e.g. "do not read a colleague's directory").

Deliberately conservative: every deny below is an action NO contract ever instructs. A false
positive would block a legitimate stage step, which is worse than a miss -- misses are still
covered by prose and by 0444.

Decision 0042 adds two refusals of calls that are not a named write, because they are shapes a
bypass takes and no contract instructs either: a call the guard cannot read (not a JSON object,
or anything raising inside the hook) -- a hook that crashes must never become a hook that
allows -- and, for the SPELLINGS LISTED BELOW ONLY, a write the scanner cannot see that names a
protected path (a shell's -c string, `-c`/`-e` inline interpreter code, an unparseable
command). This is a token scan, not a sandbox: other spellings of the same writes still pass,
and 0042 lists them. The durable fix is a typed tool surface (spec R-092), not more patterns.

Runs on stock python 3.6.8, stdlib only, like every `_system/` helper.
"""

import fnmatch
import json
import os
import shlex
import sys

# Tools that write the file named in tool_input.file_path / notebook_path.
WRITE_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")

# Workspace paths no session may write: the template ships them, `git pull` updates them.
# Relative to the workspace root, fnmatch patterns.
READ_ONLY = [
    "_system/*", "_system/**/*",
    "_references/*", "_references/**/*",
    "_templates/*", "_templates/**/*",
    ".claude/*", ".claude/**/*",
    "CLAUDE.md",
    "CONTEXT.md",
    "0*/CONTEXT.md",                      # stage contracts
    "0*/**/CONTEXT.md",                   # sub-stage contracts
    # Machine-owned project files: written by _system/ scripts, regenerated, never hand-edited.
    "projects/_index.md",
    "projects/*/00_data/*/files.csv",
    "projects/*/01_samplesheets/*",
    # The stage 03 approval record: written only by `stage03_analysis.py approve` (0042).
    "projects/*/03_custom_analysis/*/PLAN.md.approved",
]

APPROVAL_RECORD = "PLAN.md.approved"

# Inline code runs a string, so the target scan never sees what it writes (decision 0042).
# A shell's -c string is scanned like any command; any other interpreter's inline code is
# refused when it names a protected path. No contract runs inline interpreter code.
SHELLS = ("bash", "sh", "zsh", "dash")
INTERPRETERS = ("python", "perl", "ruby", "node", "rscript", "r")
SEPARATORS = ("|", ";", "&&", "||", "&")

# Bash substrings that install into the locked environments. The environments are pinned by
# lockfiles (_references/*.lock.txt); an ad-hoc install silently unpins them.
INSTALL_PATTERNS = (
    "pip install", "pip3 install", "python -m pip install", "python3 -m pip install",
    "conda install", "mamba install", "conda create", "mamba create",
    "conda update", "mamba update",
)

# Directories a Bash command must not use as a write target (redirection, tee, rm, mv, cp,
# sed -i). Checked against resolved targets, not the whole command line, so reading from or
# executing scripts in these directories stays allowed.
PROTECTED_PREFIXES = ("_system/", "_references/", "_templates/", ".claude/")


def workspace_root():
    root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    return os.path.abspath(root)


def rel_to_root(path, root, cwd):
    """A path from tool input, made relative to the workspace root; None if outside it."""
    if not os.path.isabs(path):
        path = os.path.join(cwd or root, path)
    path = os.path.normpath(path)
    root = root.rstrip(os.sep) + os.sep
    if not path.startswith(root):
        return None
    return path[len(root):].replace(os.sep, "/")


def deny(message):
    sys.stderr.write(message + "\n")
    sys.exit(2)


def check_write_tool(tool_input, root, cwd):
    path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if not path:
        return
    rel = rel_to_root(path, root, cwd)
    if rel is None:
        return  # outside the workspace; prose boundaries govern there
    for pat in READ_ONLY:
        if fnmatch.fnmatch(rel, pat):
            if rel.startswith("projects/") and rel.endswith("files.csv"):
                deny("Blocked: %s is machine-owned (mode 0444). It is regenerated by "
                     "`_system/stage00_register.py finalize`; to change the cohort, edit "
                     "samples.csv instead. See the stage 00 contract, Definitions." % rel)
            if rel.startswith("projects/") and "/01_samplesheets/" in rel:
                deny("Blocked: %s is emitted by `_system/stage01_samplesheet.py`. Edit the "
                     "design (samples.csv) and re-run the emitter; never the emitted file. "
                     "See the stage 01 contract." % rel)
            if rel == "projects/_index.md":
                deny("Blocked: projects/_index.md is generated. Rebuild it with "
                     "`bash _system/build_projects_index.sh` instead of editing it.")
            if os.path.basename(rel) == APPROVAL_RECORD:
                deny("Blocked: %s is the stage 03 approval record. It is written only by "
                     "`_system/stage03_analysis.py approve`, after the user has said yes to "
                     "the plan; never write or edit it (decision 0042)." % rel)
            deny("Blocked: %s is part of the GARS template, updated only by `git pull`. "
                 "A workspace session never edits contracts, references, templates or "
                 "_system/ code. See CLAUDE.md, Scope Boundaries." % rel)


def names_protected(text):
    """True when a string mentions a template path or an approval record anywhere in it."""
    return any(prefix in text for prefix in PROTECTED_PREFIXES) or APPROVAL_RECORD in text


def inline_code_args(tokens):
    """For each inline-code invocation in a token list: (kind, args), where kind is "shell"
    or "interpreter" and args are the tokens up to the next separator.

    `bash -c CODE`, `sh -lc CODE`; `python3 -c`, `perl -e` / `-pi -e`, `ruby -e`, `node -e`,
    `Rscript -e`, `R -e`. A versioned name (`python3.12`) or a path (`/usr/bin/perl`) counts."""
    found = []
    for i, tok in enumerate(tokens):
        name = os.path.basename(tok).lower()
        if name.startswith("python"):
            name = "python"
        kind = "shell" if name in SHELLS else "interpreter" if name in INTERPRETERS else None
        if kind is None:
            continue
        args = []
        for arg in tokens[i + 1:]:
            if arg in SEPARATORS:
                break
            args.append(arg)
        flags = [a for a in args if a.startswith("-") and not a.startswith("--")]
        if kind == "shell":
            inline = any("c" in f[1:] for f in flags)
        elif name in ("perl", "ruby"):
            inline = any(("e" in f[1:]) or ("E" in f[1:]) or ("i" in f[1:]) for f in flags)
        elif name == "python":
            inline = "-c" in flags
        else:
            inline = any(f in ("-e", "-E") for f in flags)
        if inline:
            found.append((kind, args))
    return found


def bash_write_targets(command):
    """Targets a shell command writes to: redirections, tee/rm/mv/cp/sed -i arguments,
    dd of=, ln/install destinations, touch/truncate/chmod/chown operands.

    Best-effort token scan -- shlex, no shell emulation. Returns None when the command cannot
    be parsed, so the caller decides: refused if it names a protected path (decision 0042),
    allowed otherwise, as before."""
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        return None
    targets = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok in (">", ">>", "1>", "2>", "&>") and i + 1 < len(tokens):
            targets.append(tokens[i + 1]); i += 2; continue
        if tok.startswith((">", ">>")) and len(tok) > 1 and not tok.startswith(">&"):
            targets.append(tok.lstrip(">")); i += 1; continue
        if tok == "tee":
            # Skip flags rather than stop at them: `tee -a FILE` writes FILE (decision 0042).
            j = i + 1
            while j < len(tokens) and tokens[j] not in SEPARATORS:
                if not tokens[j].startswith("-"):
                    targets.append(tokens[j])
                j += 1
            i = j; continue
        if tok == "rm":
            for arg in tokens[i + 1:]:
                if arg in ("|", ";", "&&", "||"):
                    break
                if not arg.startswith("-"):
                    targets.append(arg)
            i += 1; continue
        if tok in ("mv", "cp"):
            args = operands(tokens, i)
            if len(args) >= 2:
                targets.extend(destinations(args, sources_too=(tok == "mv")))
            i += 1; continue
        if tok == "sed":
            rest = tokens[i + 1:]
            if any(a == "-i" or a.startswith("-i") for a in rest if a.startswith("-")):
                for arg in reversed(rest):
                    if arg in ("|", ";", "&&", "||"):
                        break
                    if not arg.startswith("-"):
                        targets.append(arg)
                        break
            i += 1; continue
        # The verbs added by decision 0042 count only in command position, so a read that
        # merely mentions one (`grep chmod _system/x`) is not taken for a write.
        at_command = i == 0 or tokens[i - 1] in SEPARATORS
        if tok == "dd" and at_command:
            for arg in tokens[i + 1:]:
                if arg in SEPARATORS:
                    break
                if arg.startswith("of="):
                    targets.append(arg[3:])
            i += 1; continue
        if tok in ("ln", "install") and at_command:
            args = operands(tokens, i)
            if len(args) >= 2:
                targets.extend(destinations(args))
            i += 1; continue
        if tok in ("touch", "truncate", "chmod", "chown") and at_command:
            # chmod/chown take a mode or owner first and truncate -s a size: those operands
            # are listed too, and are harmless -- they never resolve to a protected path.
            targets.extend(operands(tokens, i))
            i += 1; continue
        i += 1
    return targets


def operands(tokens, i):
    """The non-flag arguments of the command at tokens[i], up to the next separator."""
    found = []
    for arg in tokens[i + 1:]:
        if arg in SEPARATORS:
            break
        if not arg.startswith("-"):
            found.append(arg)
    return found


def destinations(args, sources_too=False):
    """Where cp/mv/ln/install write: the last operand and, in case it is a directory, each
    source's basename inside it -- so `cp PLAN.md.approved <dir>/` is seen (decision 0042).
    `mv` also removes its sources, so they are writes too."""
    dest = args[-1]
    found = [dest]
    for src in args[:-1]:
        found.append(dest.rstrip("/") + "/" + os.path.basename(src.rstrip("/")))
        if sources_too:
            found.append(src)
    return found


UNREADABLE = ("Blocked: the guard could not read this tool call, so it cannot tell whether the "
              "call is safe. A call it cannot judge is refused, never waved through (decision "
              "0042). Retry the call; if this keeps happening, stop and report it.")


def check_bash(tool_input, root, cwd, depth=0):
    command = tool_input.get("command") or ""
    if not isinstance(command, str):
        deny(UNREADABLE)
    lowered = " ".join(command.lower().split())

    for pat in INSTALL_PATTERNS:
        if pat in lowered:
            deny("Blocked: `%s` -- the gars-bio/gars-nxf environments are pinned by lockfiles "
                 "(_references/*.lock.txt). Installing ad hoc silently unpins them. If a tool "
                 "is missing, stop and report it; do not install. See _references/environment.md."
                 % pat)

    if "files.csv" in lowered:
        try:
            tokens = shlex.split(command, posix=True)
        except ValueError:
            tokens = command.split()
        verbs = {"chmod", "rm", "mv", "truncate", "shred"}
        if any(os.path.basename(t) in verbs or t in verbs for t in tokens[:1]) \
                or any(t in verbs for t in tokens):
            if any("files.csv" in t for t in tokens):
                deny("Blocked: files.csv is machine-owned (mode 0444) and regenerated by "
                     "`_system/stage00_register.py finalize`. Do not chmod, remove or move it; "
                     "to change the cohort, edit samples.csv. See decision 0018.")

    targets = bash_write_targets(command)
    if targets is None:
        if names_protected(command):
            deny("Blocked: the command could not be parsed (unbalanced quotes?) and it names a "
                 "protected path. A write the guard cannot see is refused when it touches "
                 "_system/, _references/, _templates/, .claude/ or an approval record "
                 "(decision 0042). Fix the quoting, or run the _system/ script directly.")
        targets = []
    else:
        for kind, args in inline_code_args(shlex.split(command, posix=True)):
            if kind == "shell" and depth < 3:
                # A shell's -c string is a command: scan it exactly like one.
                for code in args:
                    if not code.startswith("-"):
                        check_bash({"command": code}, root, cwd, depth + 1)
            elif names_protected(" ".join(args)):
                deny("Blocked: inline code (%s) that names a protected path. The target "
                     "scan cannot see what inline code writes, so it is refused when it "
                     "touches _system/, _references/, _templates/, .claude/ or an approval "
                     "record; no contract runs inline code there (decision 0042). Run the "
                     "_system/ script as a file instead." % " ".join(args[:1] or ["-c"]))

    for target in targets:
        rel = rel_to_root(target, root, cwd)
        if rel is None:
            continue
        if rel == "projects/_index.md":
            continue  # build_projects_index.sh legitimately redirects into it
        for prefix in PROTECTED_PREFIXES:
            # `rel + "/" == prefix` catches the directory itself (`chmod -R a+w _system`,
            # `cp x _system/`): normpath has already dropped any trailing slash.
            if rel.startswith(prefix) or rel + "/" == prefix:
                deny("Blocked: the command writes to %s, which is part of the GARS template "
                     "(updated only by `git pull`). A workspace session never modifies "
                     "_system/, _references/, _templates/ or .claude/. See CLAUDE.md." % rel)
        if os.path.basename(rel) == APPROVAL_RECORD:
            deny("Blocked: the command writes to %s, the stage 03 approval record. It is "
                 "written only by `_system/stage03_analysis.py approve`, after the user has "
                 "said yes to the plan (decision 0042)." % rel)
        if rel.startswith("projects/") and (rel.endswith("files.csv")
                                            or "/01_samplesheets/" in rel):
            deny("Blocked: the command writes to %s, which is machine-owned. It is produced "
                 "by a _system/ script; run the script instead of writing the file. See the "
                 "stage contract." % rel)


def main():
    # Everything that can raise sits inside the try -- reading stdin, a payload nested deep
    # enough to exhaust the JSON parser, a working directory that no longer exists -- because
    # the harness treats any exit other than 2 as "allow" (decision 0042).
    try:
        try:
            payload = json.loads(sys.stdin.read())
        except ValueError:
            payload = None
        if not isinstance(payload, dict) \
                or not isinstance(payload.get("tool_input") or {}, dict):
            deny(UNREADABLE)
        tool = payload.get("tool_name") or ""
        tool_input = payload.get("tool_input") or {}
        cwd = payload.get("cwd") or ""
        root = workspace_root()
        if tool in WRITE_TOOLS:
            check_write_tool(tool_input, root, cwd)
        elif tool == "Bash":
            check_bash(tool_input, root, cwd)
    except Exception as exc:  # deny() raises SystemExit, which is not an Exception
        deny("Blocked: the guard failed while checking this call (%s: %s), so it cannot tell "
             "whether the call is safe. A call it cannot judge is refused (decision 0042). "
             "Report it: this is a defect in _system/guard_hook.py."
             % (type(exc).__name__, str(exc)[:200]))
    sys.exit(0)


if __name__ == "__main__":
    main()
