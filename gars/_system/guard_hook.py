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
    "data_sources.tsv",
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

# Non-public projects are closed (decision 0107): only data_class `public` may enter a
# hosted-model prompt (spec §6.1, §21 Q4; R-061/R-074). A project is open only when its
# machine-owned dataset row reads exactly `public`; what the guard cannot judge stays closed.
DATASET_ROW = "00_data/dataset.tsv"
# Written only by a human: absolute folders whose data is public, which a guarded agent may
# then register through stage 00 (decision 0107). Machine-local; never committed.
DECLARATIONS = "data_sources.tsv"
DECLARATIONS_HEADER = ["source", "data_class", "declared_by"]
OPEN_IN_CLOSED_EXACT = (DATASET_ROW,)
OPEN_IN_CLOSED_BASENAME = ("STATUS",)
CLOSED_PROJECT_DOORS = ()                   # empty in this lane (0107)
# What `stage00_register.py create` leaves in a project, project-relative; `{assay}` stands for
# each assay directory under 00_data/. Bound to the real `create` by a drift test (0107).
CREATE_STAMP = (
    "00_data", "00_data/.gitkeep", "00_data/{assay}", "00_data/{assay}/raw",
    "CONTEXT.md", "HISTORY.md",
    "_config", "_config/.gitkeep", "_config/executor.yaml", "_config/nextflow.slurm.config",
    "_config/{assay}.yaml",
)
RECURSIVE_FS = ("fs.search", "fs.inspect", "fs.find")
SHELL_GLOB = set("*?[]{}()")
KNOWN_CLASSES = ("public", "deidentified_under_agreement", "identifiable")
INSPECT, LINK, FINALIZE = ("stage00_register.inspect", "stage00_register.link",
                           "stage00_register.finalize")
CLOSED_WHY = ("Only public data may enter a hosted-model prompt (spec §6.1, §21 Q4; "
              "R-061/R-074; decision 0107).")


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
            if rel.casefold() == DECLARATIONS.casefold():
                deny("Blocked: data_sources.tsv declares which data folders are public; only a "
                     "human writes it (decision 0107).")
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


# --- non-public projects are closed (decision 0107) ----------------------------------------

def _inside(child, parent):
    """True when child is parent or lies below it: casefolded, at path boundaries, so
    `projects/pilot-2` is not inside `projects/pilot`."""
    c, p = child.casefold(), parent.casefold()
    if p != os.sep:
        p = p.rstrip(os.sep)
    return c == p or c.startswith(p if p.endswith(os.sep) else p + os.sep)


def _bases(cwd, root):
    """Every path is judged from the session cwd (where the guard resolves it) and from the
    workspace root (where the dispatcher runs it)."""
    return (cwd or root, root)


def _forms(token, bases):
    """Each base x each form (normalized, resolved) of a path token."""
    found = []
    for base in bases:
        path = token if os.path.isabs(token) else os.path.join(base, token)
        for form in (os.path.normpath(path), os.path.realpath(path)):
            if form not in found:
                found.append(form)
    return found


def static_prefix(token):
    """The folder no shell expansion of `token` can leave: the path before its first
    SHELL_GLOB character, cut back to a whole folder; '.' when that is empty."""
    cut = [i for i, c in enumerate(token) if c in SHELL_GLOB]
    if not cut:
        return token
    head = token[:cut[0]]
    slash = head.rfind("/")
    if slash < 0:
        return "."
    return head[:slash] or "/"


def _regular_text(path):
    """The UTF-8 text of a regular file, opened without following a final symlink and without
    blocking on a FIFO; anything else raises OSError."""
    import stat
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    with os.fdopen(os.open(path, flags), "rb") as fh:
        if not stat.S_ISREG(os.fstat(fh.fileno()).st_mode):
            raise OSError("not a regular file")
        return fh.read().decode("utf-8")


def _dataset_class(project_dir):
    """(public, label): public only for exactly the row finalize writes, read by header name.
    The label is a known class or `unclassified`; a cell's text is never echoed."""
    path = os.path.join(project_dir, DATASET_ROW)
    try:
        # The project's own row: not a symlink, not reached through a linked 00_data/.
        if os.path.realpath(path) != os.path.join(os.path.realpath(project_dir),
                                                  *DATASET_ROW.split("/")):
            return False, "unclassified"
        text = _regular_text(path)
    except (OSError, UnicodeError):
        return False, "unclassified"
    if "\r" in text:
        return False, "unclassified"
    lines = text.split("\n")
    if lines[-1] == "":
        lines.pop()
    if len(lines) < 2:
        return False, "unclassified"
    header = lines[0].split("\t")
    if header.count("data_class") != 1:
        return False, "unclassified"
    column = header.index("data_class")
    values = []
    for line in lines[1:]:
        cells = line.split("\t")
        if len(cells) != len(header):
            return False, "unclassified"
        values.append(cells[column])
    if all(value == "public" for value in values):
        return True, "public"
    if len(set(values)) == 1 and values[0] in KNOWN_CLASSES:
        return False, values[0]
    return False, "unclassified"


def project_is_public(project_dir):
    """True only when 00_data/dataset.tsv is a regular file whose every data row reads exactly
    `public` in its data_class column (decision 0107)."""
    return _dataset_class(project_dir)[0]


def _projects(root):
    """(name, path, forms, public, label) for every entry of projects/ that is not a regular
    file. A symlinked entry is resolved and kept on both spellings. projects/ absent: none;
    projects/ unreadable raises, and main() refuses the call."""
    base = os.path.join(root, "projects")
    if not os.path.lexists(base):
        return []
    found = []
    for name in sorted(os.listdir(base)):
        path = os.path.join(base, name)
        if os.path.isfile(path) and not os.path.islink(path):
            continue
        public, label = _dataset_class(path)
        forms = [os.path.normpath(path)]
        if os.path.realpath(path) not in forms:
            forms.append(os.path.realpath(path))
        found.append((name, path, forms, public, label))
    return found


def closed_projects(root):
    """The closed projects, computed once per call: (name, label, forms)."""
    return [(name, label, forms) for name, _, forms, public, label in _projects(root)
            if not public]


def _open_in_closed(form, project_form):
    """Read and the fs.* reads may read a closed project's dataset row and its STATUS files."""
    prefix = project_form.rstrip(os.sep) + os.sep
    if not form.startswith(prefix) or os.path.isdir(form):
        return False
    rel = form[len(prefix):].replace(os.sep, "/")
    return rel in OPEN_IN_CLOSED_EXACT or rel.rsplit("/", 1)[-1] in OPEN_IN_CLOSED_BASENAME


def _hit(token, bases, recursive, closed, readable):
    for form in _forms(token, bases):
        for name, label, project_forms in closed:
            for project_form in project_forms:
                if _inside(form, project_form):
                    if readable and _open_in_closed(form, project_form):
                        continue
                    return ("inside", name, label)
                if recursive and _inside(project_form, form):
                    return ("ancestor", name, label)
    return None


def closed_hit(token, root, bases, recursive, closed, readable=False):
    """How a path token reaches a closed project, or None: ("inside" | "ancestor" | "tilde",
    name, label). `readable` marks Read and the fs.* reads, the only callers that may read a
    closed project's dataset row and STATUS files. A SHELL_GLOB token is also judged by its
    static prefix, recursively, from the session cwd, where the shell expands it."""
    if token.startswith("~"):
        return ("tilde", None, "unclassified")
    if SHELL_GLOB & set(token):
        hit = _hit(static_prefix(token), bases[:1], True, closed, False)
        if hit:
            return hit
    return _hit(token, bases, recursive, closed, readable)


def closed_refusal(token, hit):
    kind, name, label = hit
    if kind == "tilde":
        return ("Blocked: %s starts with ~, which the shell expands to a folder the guard cannot "
                "judge; spell the path out. %s" % (token, CLOSED_WHY))
    if kind == "ancestor":
        return ("Blocked: %s is an ancestor of project %s, whose data_class is %s, and this call "
                "searches below it. %s Search from a folder that is not an ancestor of a closed "
                "project: _system/, _references/, or a public project."
                % (token, name, label, CLOSED_WHY))
    return ("Blocked: %s is in project %s, whose data_class is %s. %s Readable here: "
            "00_data/dataset.tsv and the STATUS files. Ask the human to run the step, declare a "
            "public source in data_sources.tsv, or read a public project."
            % (token, name, label, CLOSED_WHY))


def declared_sources(root):
    """(validated realpaths, None) from a valid data_sources.tsv, else ((), the failed rule).
    A missing or invalid file declares nothing; the rule named never quotes the file."""
    path = os.path.join(root, DECLARATIONS)
    if not os.path.lexists(path):
        return (), "no data_sources.tsv"
    try:
        text = _regular_text(path)
    except (OSError, UnicodeError):
        return (), "data_sources.tsv is not a readable regular file"
    if "\r" in text:
        return (), "data_sources.tsv has CR line endings"
    lines = text.split("\n")
    if lines[-1] == "":
        lines.pop()
    if not lines or lines[0].split("\t") != DECLARATIONS_HEADER:
        return (), "the data_sources.tsv header is not source, data_class, declared_by"
    store = os.path.join(os.path.dirname(os.path.realpath(root)), ".gars-approvals")
    places = [os.path.join(root, d) for d in
              ("projects", "_system", "_references", "_templates", ".claude")] + [store]
    guarded = []
    for place in places:
        guarded += [os.path.normpath(place), os.path.realpath(place)]
    for _, _, forms, _, _ in _projects(root):
        guarded += forms
    roots = [os.path.normpath(root), os.path.realpath(root)]
    seen, found = [], []
    for line in lines[1:]:
        cells = line.split("\t")
        if len(cells) != 3:
            return (), "a data_sources.tsv row does not have three cells"
        source, data_class, declared_by = cells
        if source.startswith("~") or SHELL_GLOB & set(source):
            return (), "a source holds ~ or a shell-glob character"
        if not os.path.isabs(source):
            return (), "a source is not an absolute path"
        if not os.path.isdir(source):
            return (), "a source is not an existing directory"
        if data_class != "public":
            return (), "a declared data_class is not exactly public"
        if not declared_by.strip():
            return (), "a declared_by label is empty"
        forms = [os.path.normpath(source), os.path.realpath(source)]
        for form in forms:
            if any(_inside(r, form) for r in roots):
                return (), "a source equals or contains the workspace root"
            if any(_inside(form, g) or _inside(g, form) for g in guarded):
                return (), ("a source equals, contains or lies inside projects/, a project, "
                            "_system/, _references/, _templates/, .claude/ or .gars-approvals/")
            for other in seen:
                if form.casefold() == other.casefold():
                    return (), "a source is declared twice"
                if form.casefold() != other.casefold() and (_inside(form, other)
                                                            or _inside(other, form)):
                    return (), "two declared sources are nested"
        seen += forms
        found.append(os.path.realpath(source))
    if not found:
        return (), "data_sources.tsv declares no source"
    return tuple(found), None


def inside_declared(path, sources):
    """True when a resolved path lies in (or is) a declared-public source."""
    return any(_inside(path, source) for source in sources)


def registrable(project_dir):
    """True when a project has no dataset row and holds nothing beyond create's stamp plus
    entries directly under 00_data/<assay>/raw/ (decision 0107)."""
    if os.path.lexists(os.path.join(project_dir, DATASET_ROW)):
        return False
    data = os.path.join(project_dir, "00_data")
    try:
        if os.path.islink(project_dir) or os.path.islink(data):
            return False
        assays = [n for n in os.listdir(data) if os.path.isdir(os.path.join(data, n))]
    except OSError:
        return False
    allowed = set()
    for entry in CREATE_STAMP:
        allowed.update([entry.replace("{assay}", a) for a in assays] if "{assay}" in entry
                       else [entry])
    raw_dirs = set("00_data/%s/raw" % a for a in assays)

    def fail(exc):
        raise exc
    try:
        for top, dirs, files in os.walk(project_dir, onerror=fail):
            rel_top = os.path.relpath(top, project_dir).replace(os.sep, "/")
            rel_top = "" if rel_top == "." else rel_top
            if rel_top in raw_dirs:
                dirs[:] = []
                continue
            for name in dirs + files:
                rel = rel_top + "/" + name if rel_top else name
                if rel == DATASET_ROW:
                    continue        # judged by the precondition above, on lexists
                if rel not in allowed or os.path.islink(os.path.join(top, name)):
                    return False
    except OSError:
        return False
    return True


def _raw_entries(project_dir):
    data = os.path.join(project_dir, "00_data")
    found = []
    for assay in sorted(os.listdir(data)):
        raw = os.path.join(data, assay, "raw")
        if os.path.isdir(raw) and not os.path.islink(raw):
            found += [os.path.join(raw, n) for n in sorted(os.listdir(raw))]
    return found


def _declared_entry(path, sources):
    """A raw or source entry counts only when it resolves to something that exists inside a
    declared-public source; a dangling entry is undeclared."""
    return os.path.exists(path) and inside_declared(os.path.realpath(path), sources)


def _named_project(token, root, bases):
    """(name, path) of the one project a --project token names on every base x form."""
    if not isinstance(token, str) or not token:
        return None
    projects = _projects(root)
    names = set()
    for form in _forms(token, bases):
        match = [p for p in projects if any(form.casefold() == f.casefold() for f in p[2])]
        if len(match) != 1:
            return None
        names.add(match[0][0])
    if len(names) != 1:
        return None
    name = names.pop()
    return [(p[0], p[1]) for p in projects if p[0] == name][0]


def _reaches_project(forms, root):
    """True when any form equals, contains or lies inside projects/ or a project."""
    places = [os.path.normpath(os.path.join(root, "projects")),
              os.path.realpath(os.path.join(root, "projects"))]
    for _, _, project_forms, _, _ in _projects(root):
        places += project_forms
    return any(_inside(f, p) or _inside(p, f) for f in forms for p in places)


def declared_registration(tool, args, root, bases, closed, sources):
    """The one opening (decision 0107): stage 00 on data a human declared public. Returns the
    names of the projects whose own hits the call may carry (() for inspect), or None when the
    call is not a declared registration."""
    name = tool.get("name")
    if name not in (INSPECT, LINK, FINALIZE) or not sources or args.get("force"):
        return None
    for key in ("project", "source", "data-class"):
        value = args.get(key)
        if isinstance(value, str) and (value.startswith("~") or SHELL_GLOB & set(value)):
            return None
    if name == FINALIZE and args.get("data-class") != "public":
        return None
    if name in (INSPECT, LINK):
        source = args.get("source")
        if not isinstance(source, str) or not source:
            return None
        forms = _forms(source, bases)
        if name == INSPECT:
            declared = all(inside_declared(os.path.realpath(f), sources) for f in forms)
        else:
            declared = all(inside_declared(f, sources) for f in forms)
        if not declared or _reaches_project(forms, root):
            return None
        if name == INSPECT:
            return ()
    project = _named_project(args.get("project"), root, bases)
    if project is None or not registrable(project[1]):
        return None
    try:
        raw = _raw_entries(project[1])
        if not all(_declared_entry(entry, sources) for entry in raw):
            return None
        if name == LINK:
            for form in set(os.path.realpath(f) for f in _forms(args["source"], bases)):
                entries = [os.path.join(form, n) for n in os.listdir(form)]
                if not all(_declared_entry(entry, sources) for entry in entries):
                    return None
        elif not raw:
            return None
    except OSError:
        return None
    return (project[0],)


def first_public_classification(tool, args, root, bases, closed, sources):
    """Q8 (decision 0107): only a human, or a protected declaration, supplies class public.
    The refusal for an agent's finalize that would supply it, or None."""
    if tool.get("name") != FINALIZE:
        return None
    value = args.get("data-class")
    if not isinstance(value, str) or value.strip().casefold() != "public":
        return None
    if declared_registration(tool, args, root, bases, closed, sources) is not None:
        return None
    project = _named_project(args.get("project"), root, bases)
    if value == "public" and project is not None \
            and not any(project[0] == c[0] for c in closed):
        return None                 # a same-value re-run on a project already public
    return ("Blocked: classifying data is the owner's (spec §21 Q4): a guarded agent never "
            "supplies data_class public (decision 0107). The human runs `python3 "
            "_system/stage00_register.py finalize --project <project> --data-class public ...` "
            "in their own terminal, or declares the source folder in gars/data_sources.tsv.")


def _strings(value, key=None):
    """(top-level key, string) for every string in a dispatcher call's JSON, recursively."""
    if isinstance(value, str):
        return [(key, value)]
    if isinstance(value, dict):
        return [s for k, v in value.items() for s in _strings(v, k if key is None else key)]
    if isinstance(value, list):
        return [s for item in value for s in _strings(item, key)]
    return []


def _spellings(word):
    """The candidates a word may name: itself, its option-stripped form, its value after the
    first `=`, and for a single-dash cluster every suffix after each letter (`-rfFILE`)."""
    found = [word, word.lstrip("-")]
    if "=" in word:
        found.append(word.split("=", 1)[1])
    if word.startswith("-") and not word.startswith("--"):
        found += [word[i:] for i in range(2, len(word))]
    return [w for w in found if w]


def _recursive(name, words):
    if name in RECURSIVE_FS:
        return True
    if name == "fs.list":
        return any(w == "--recursive" or (w.startswith("-") and not w.startswith("--")
                                          and "R" in w) for w in words)
    return False


def closed_read_refusal(tool, tool_input, root, cwd):
    """Read, Glob and Grep on a closed project (decision 0107)."""
    closed = closed_projects(root)
    if not closed:
        return
    bases = _bases(cwd, root)
    here = tool_input.get("path") or cwd or root
    if tool == "Read":
        checks = [(tool_input.get("file_path") or here, False, True)]
    else:
        checks = [(here, True, False)]
        pattern = tool_input.get("pattern")
        if tool == "Glob" and isinstance(pattern, str) and pattern and isinstance(here, str):
            checks.append((pattern if pattern.startswith("~")
                           else os.path.join(here, static_prefix(pattern)), True, False))
    for token, recursive, readable in checks:
        if not isinstance(token, str):
            deny(UNREADABLE)
        hit = closed_hit(token, root, bases, recursive, closed, readable)
        if hit:
            deny(closed_refusal(token, hit))


def closed_bash_refusal(tool, args, tokens, root, cwd):
    """A registered Bash call, bare or through the dispatcher, once `authorize` passed (0107):
    the rg --pre refusal, Q8, the stage 00 opening, then the closed-project rule."""
    name = tool.get("name")
    dispatcher = (len(tokens) == 4 and tokens[0] == "python3" and os.path.realpath(
        os.path.join(cwd, tokens[1])) == os.path.realpath(os.path.join(root, "_system",
                                                                        "tool_call.py")))
    if dispatcher:
        words = [(None, t) for t in tokens[1:3]] + _strings(args)
    else:
        words, key = [], None
        for token in tokens[1:]:
            words.append(("project" if token.startswith("--project=") else key, token))
            key = "project" if token == "--project" else None
    for _, word in [(None, t) for t in tokens] + words:
        if word in ("--pre", "--pre-glob") or word.startswith(("--pre=", "--pre-glob=")):
            deny("Blocked: rg --pre and --pre-glob run a program on every file searched, and "
                 "the typed surface runs no program it does not name (R-092; decision 0107).")
    bases = _bases(cwd, root)
    closed = closed_projects(root)
    sources, failed = declared_sources(root)
    message = first_public_classification(tool, args, root, bases, closed, sources)
    if message:
        deny(message)
    declared = declared_registration(tool, args, root, bases, closed, sources)
    if declared is None and name in (INSPECT, LINK):
        deny("Blocked: stage 00 %s prints file and sample names into the prompt, so a guarded "
             "agent runs it only on a project fresh from create and a --source inside a folder "
             "a human declared public in data_sources.tsv (%s). %s Ask the human to run it in "
             "their own terminal, or to declare the source."
             % (name.split(".")[1], failed or "this call is not a declared registration",
                CLOSED_WHY))
    if name in CLOSED_PROJECT_DOORS or not closed:
        return
    exempt = declared or ()
    for form in _forms(cwd, (root,)):
        for project, label, project_forms in closed:
            if project not in exempt and any(_inside(form, f) for f in project_forms):
                deny("Blocked: the session's working directory is in project %s, whose "
                     "data_class is %s. %s Readable here: 00_data/dataset.tsv and the STATUS "
                     "files, from outside the project. Ask the human to run the step, declare a "
                     "public source in data_sources.tsv, or work in a public project."
                     % (project, label, CLOSED_WHY))
    recursive = _recursive(name, [w for _, w in words])
    readable = bool(tool.get("filesystem"))
    for key, word in words:
        for token in _spellings(word):
            hit = closed_hit(token, root, bases, recursive, closed, readable)
            if hit and not (key == "project" and hit[0] == "inside" and hit[1] in exempt):
                deny(closed_refusal(token, hit))


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
        closed_bash_refusal(tool, args, tokens, root, cwd or root)
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
            closed_read_refusal(tool, tool_input, root, cwd)
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
