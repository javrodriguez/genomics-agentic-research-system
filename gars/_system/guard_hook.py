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

The owner ruled 3A: when the guard cannot judge a call it refuses. Every refusal names
its rule, where it is written, and the typed call to use instead (R-098; decision 0058).
The Bash transport accepts only registered typed calls or read-only filesystem commands;
it is not a general shell. Non-agent builders require Row 15's git-level hooks.

Runs on stock python 3.6.8, stdlib only, like every `_system/` helper.
"""

import fnmatch
import json
import os
import shlex
import sys
from tools.policy import Refusal, simple_tokens, parse_argv, authorize

# Tools that write the file named in tool_input.file_path / notebook_path.
WRITE_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")

# Workspace paths no session may write: the template ships them, `git pull` updates them.
# Relative to the workspace root, fnmatch patterns.
READ_ONLY = [
    "_system/*", "_system/**/*",
    "_references/*", "_references/**/*",
    "_templates/*", "_templates/**/*",
    ".claude/*", ".claude/**/*",
    "AGENTS.md",
    "CLAUDE.md",
    "CONTEXT.md",
    "0*/CONTEXT.md",                      # stage contracts
    "0*/**/CONTEXT.md",                   # sub-stage contracts
    # Machine-owned project files: written by _system/ scripts, regenerated, never hand-edited.
    "repo:.gars-approvals/*",
    "repo:.githooks/*",
    "repo:.github/*",
    "repo:.gitlab-ci.yml",
    "repo:docs/decisions/*",  # includes every accepted/standing record
    "repo:tests/fixtures/*",
    "repo:evals/*/fixtures/*",
    "repo:evals/*/test-fixtures/*",
    "repo:benchmarks/holdout/*",
    "tests/fixtures/*",
    "projects/_index.md",
    "projects/*/.gars_submissions",
    "projects/*/.gars_submissions/*",
    "projects/*/.gars_local_jobs",
    "projects/*/.gars_local_jobs/*",
    "projects/*/02_bioinformatics/*/run/.gars_run_complete",
    "projects/*/02_bioinformatics/*/run/*",
    "projects/*/02_bioinformatics/*/run/**/*",
    "projects/*/03_custom_analysis/*/run/*",
    "projects/*/03_custom_analysis/*/run/**/*",
    "projects/*/03_custom_analysis/*/.gars_submissions.jsonl",
    "projects/*/02_bioinformatics/*/submit.sh.local.exit",
    "projects/*/02_bioinformatics/*/reproducibility/manifest.json",
    "projects/*/02_bioinformatics/*/submit.sh",
    "projects/*/02_bioinformatics/*/params.yaml",
    "projects/*/.STATUS.lock",
    "projects/*/STATUS",  # R-151: only code writes lifecycle state (the owner, 13A).
    "projects/*/00_data/*/files.csv",
    "projects/*/00_data/dataset.tsv",
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
    return os.path.realpath(root)


def rel_to_root(path, root, cwd):
    """A path from tool input, made relative to the workspace root; None if outside it."""
    if not os.path.isabs(path):
        path = os.path.join(cwd or root, path)
    path = os.path.realpath(path)
    root = root.rstrip(os.sep) + os.sep
    if not path.startswith(root):
        return None
    return path[len(root):].replace(os.sep, "/")


def deny(message):
    sys.stderr.write(message + " Rule R-092/R-094/R-098, spec §9.1/§9.3/§9.6; "
                     "decision 0058. Use typed call: python3 _system/tool_call.py fs.read "
                     "\'{\"paths\":[\"CONTEXT.md\"]}\'.\n")
    sys.exit(2)


def check_write_tool(tool_input, root, cwd):
    path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if not isinstance(path, str) or not path:
        deny("Blocked: could not read write target")
    rel = rel_to_root(path, root, cwd)
    if rel is None:
        deny("Blocked: resolved write target is outside the workspace root (R-094). "
             "Row 15 git-level hooks cover non-agent builders.")
    for pat in READ_ONLY:
        if fnmatch.fnmatch(rel.casefold(), pat.casefold()) or (pat.startswith("repo:") and
                fnmatch.fnmatch(("gars/" + rel).casefold(), pat[5:].casefold())):
            if rel.startswith("projects/") and rel.casefold().endswith("/status"):
                deny("Blocked: R-151, spec §15; decision 0063 (the owner's ruling 13A): "
                     "STATUS is code-owned. Use typed call: python3 _system/executorlib.py "
                     "status --workspace <project> <job_id>.")
            if rel.startswith("projects/") and rel.casefold().endswith("files.csv"):
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
            if os.path.basename(rel).casefold() == APPROVAL_RECORD.casefold():
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
    command = tool_input.get("command")
    if isinstance(command, str):
        # Explicit R-096 reasons precede the generic no-git refusal, including = spelling.
        if "--no-verify" in command:
            deny("Blocked: R-096 forbids --no-verify, including --no-verify=VALUE (spec §9.4).")
        if "hooks.gitleaks" in command and "false" in command:
            deny("Blocked: R-096 forbids git config hooks.gitleaks false (spec §9.4).")
    try:
        tokens = simple_tokens(command)
        tool, args = parse_argv(tokens, root, cwd or root)
        authorize(tool, args, 'producer', root, cwd or root)
    except Refusal as exc:
        deny("Blocked: " + json.dumps(exc.record(), sort_keys=True))


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
        if tool in ('Read', 'Glob', 'Grep'):
            target = tool_input.get('file_path') or tool_input.get('path') or cwd or root
            read_path = os.path.realpath(os.path.join(cwd or root, target))
            if read_path != os.path.realpath(root) and rel_to_root(target, root, cwd) is None:
                deny('Blocked: R-073 human approval store is outside workspace read access.')
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
