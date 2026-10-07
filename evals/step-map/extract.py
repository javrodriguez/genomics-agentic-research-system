#!/usr/bin/env python3
"""GARS step-map extractor: the facts of every stage contract, pulled deterministically.

Reads GARS at a pinned commit through `git show <sha>:<path>` (never the working tree) and
writes one JSON per contract plus a summary. It changes nothing in GARS. Standard library only.

    python3 evals/step-map/extract.py                 # pin a626cdc2, write evals/step-map/facts/
    python3 evals/step-map/extract.py --sha <sha> --out <dir>

What it pulls, per contract (the method note's list, "What the analysis suggests doing", item 2):
- the numbered Process steps (fence-aware; lettered sub-steps such as 3a count);
- every helper call, mapped to its registry tool, and commands the contracts name that the
  registry lacks (including the implicit `date` behind "today's date");
- every exit branch each call site handles, compared with the helper's real emit sites, found by
  walking the helper's AST (calls followed into wrapperlib/executorlib; argparse's usage exit 2
  recorded as its own site); a non-zero code with no branch is a finding;
- wait points and their accept tokens (fixed answers such as `verify`, `skip`, `cancel`);
- template placeholders against the JSON keys the backing helper actually writes;
- guard coverage: `decide()` from `_system/guard_hook.py` at the pin, run in-process on synthetic
  payloads built from the contract's own commands and file actions, in synthetic workspaces
  (public, closed, fresh-from-create, fresh with a declared public source, and public beside a
  closed sibling), with no live session.

Every filter reports what it saw and what it graded; an empty result is a finding, never a pass.
Every extracted fact carries its source as `path:line` at the pin.
"""

import argparse
import ast
import contextlib
import hashlib
import io
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile

PIN = "a626cdc2"
MODEL_ID = "claude-opus-5-5"
SCHEMA = "stepmap-facts/1"

# --- reading the pinned tree -----------------------------------------------------------------


class Source:
    """A read-only view of the repository at one commit."""

    def __init__(self, repo, sha=PIN):
        self.repo = os.path.abspath(repo)
        self.sha = self.git("rev-parse", "%s^{commit}" % sha).strip()
        self._text = {}

    def git(self, *args):
        return subprocess.run(["git", "-C", self.repo] + list(args), stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, check=True,
                              universal_newlines=True).stdout

    def text(self, path):
        if path not in self._text:
            self._text[path] = self.git("show", "%s:%s" % (self.sha, path))
        return self._text[path]

    def exists(self, path):
        if not hasattr(self, "_files"):
            self._files = set(self.ls())
        return path in self._files

    def blob(self, path):
        return self.git("rev-parse", "%s:%s" % (self.sha, path)).strip()

    def ls(self, prefix=None):
        args = ["ls-tree", "-r", "--name-only", self.sha] + ([prefix] if prefix else [])
        return [p for p in self.git(*args).split("\n") if p]

    def export(self, prefixes, dest):
        """Write the pinned files under `prefixes` into `dest` (git archive; read-only on git)."""
        data = subprocess.run(["git", "-C", self.repo, "archive", "--format=tar", self.sha]
                              + list(prefixes), stdout=subprocess.PIPE, check=True).stdout
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            try:
                tar.extractall(dest, filter="data")
            except TypeError:           # Python < 3.12 has no extraction filters
                tar.extractall(dest)


def contract_paths(src):
    """The stage and sub-stage contracts: every CONTEXT.md under gars/0*_*/ (not _templates/)."""
    return sorted(p for p in src.ls("gars/")
                  if p.endswith("/CONTEXT.md") and re.match(r"gars/0\d_[^/]+/", p))


def contract_id(path):
    parts = path.split("/")[1:-1]
    if len(parts) == 1:
        return parts[0]
    return "%s__%s" % (parts[-2], parts[-1])


def contract_assay(path):
    """(assay, substage) a contract's synthetic commands are instantiated with."""
    parts = path.split("/")
    if len(parts) == 5 and parts[1] == "02_bioinformatics":
        return parts[2], parts[3]
    return "rnaseq_bulk", "01_nfcore-rnaseq-wrapper"


# --- markdown ----------------------------------------------------------------------------------

def parse_markdown(text):
    """Lines (1-based), the set of lines inside or opening/closing a fence, and `## ` sections.

    A `## ` line inside a fenced block is content, not a section (spatial-cluster-count's
    history_entry shape is one)."""
    lines = text.split("\n")
    fenced, sections, inside = set(), [], False
    for i, line in enumerate(lines, 1):
        if line.lstrip().startswith("```"):
            fenced.add(i)
            inside = not inside
            continue
        if inside:
            fenced.add(i)
            continue
        m = re.match(r"^## (.+?)\s*$", line)
        if m:
            sections.append({"name": m.group(1), "start": i})
    for k, sec in enumerate(sections):
        sec["end"] = sections[k + 1]["start"] - 1 if k + 1 < len(sections) else len(lines)
    return {"lines": lines, "fenced": fenced, "sections": sections}


def section(doc, name):
    for sec in doc["sections"]:
        if sec["name"] == name:
            return sec
    return None


def section_of(doc, line):
    for sec in doc["sections"]:
        if sec["start"] <= line <= sec["end"]:
            return sec["name"]
    return None


STEP_RE = re.compile(r"^(\d+[a-z]?)\.\s")


def parse_steps(doc):
    """Numbered items at column 0 of the Process section, outside fences. A step runs to the
    last non-blank line before the next step or the end of the section."""
    sec = section(doc, "Process")
    if sec is None:
        return []
    starts = []
    for i in range(sec["start"] + 1, sec["end"] + 1):
        if i in doc["fenced"]:
            continue
        m = STEP_RE.match(doc["lines"][i - 1])
        if m:
            starts.append((i, m.group(1)))
    steps = []
    for k, (i, n) in enumerate(starts):
        end = starts[k + 1][0] - 1 if k + 1 < len(starts) else sec["end"]
        while end > i and not doc["lines"][end - 1].strip():
            end -= 1
        steps.append({"n": n, "start": i, "end": end})
    return steps


def prose(doc, start, end):
    """The non-fenced text of lines start..end joined into one string, with a map from
    character offset back to source line."""
    parts, offsets, pos = [], [], 0
    for i in range(start, end + 1):
        if i in doc["fenced"]:
            continue
        piece = doc["lines"][i - 1].strip()
        if not piece:
            continue
        parts.append(piece)
        offsets.append((pos, i))
        pos += len(piece) + 1
    return " ".join(parts), offsets


def line_at(offsets, pos):
    line = offsets[0][1] if offsets else None
    for start, ln in offsets:
        if start <= pos:
            line = ln
    return line


def fenced_blocks(doc, start, end):
    """[(first content line, [ (line, text) ... ])] for fences opening within start..end."""
    blocks, i = [], start
    while i <= end:
        if i in doc["fenced"] and doc["lines"][i - 1].lstrip().startswith("```"):
            body, j = [], i + 1
            while j <= len(doc["lines"]) and not doc["lines"][j - 1].lstrip().startswith("```"):
                body.append((j, doc["lines"][j - 1]))
                j += 1
            blocks.append((i + 1, body))
            i = j + 1
            continue
        i += 1
    return blocks


TEMPLATE_RE = re.compile(r"^\*\*(T\d+[a-z]?)\s+[—–-]\s+(.+?)\*\*\s*$")


def parse_templates(doc):
    """{id: template} from the Response Format section: the bold `**Tn — Title**` heading and the
    first fenced block after it."""
    sec = section(doc, "Response Format")
    if sec is None:
        return {}
    heads = []
    for i in range(sec["start"] + 1, sec["end"] + 1):
        if i in doc["fenced"]:
            continue
        m = TEMPLATE_RE.match(doc["lines"][i - 1])
        if m:
            heads.append((i, m.group(1), m.group(2)))
    out = {}
    for k, (i, tid, title) in enumerate(heads):
        limit = heads[k + 1][0] - 1 if k + 1 < len(heads) else sec["end"]
        blocks = fenced_blocks(doc, i + 1, limit)
        body = blocks[0][1] if blocks else []
        out[tid] = {"id": tid, "title": title, "line": i, "body": body}
    return out


# --- what a template asks --------------------------------------------------------------------

def last_paragraph(body):
    para = []
    for _, text in reversed(body):
        if not text.strip():
            if para:
                break
            continue
        para.insert(0, text.strip())
    return " ".join(para)


def ask_kind(body):
    """question (ends with ?), gate (a sentence opening Reply/Confirm/Provide), handoff
    (Tell me / Say when / Say the word), or None: the contract standard's "a template that ends
    by asking is a wait point"."""
    para = last_paragraph(body)
    if not para:
        return None
    if para.rstrip().endswith("?"):
        return "question"
    sentences = re.split(r"(?<=[.?!;])\s+", para)
    if any(re.match(r"(Reply|Confirm|Provide)\b", s) for s in sentences):
        return "gate"
    if re.search(r"\b([Tt]ell me|Say when|Say the word)\b", para):
        return "handoff"
    return None


def accept_tokens(body):
    """Fixed answers: lowercase backticked words in the asking paragraph (`verify`, `skip`)."""
    seen = []
    for tok in re.findall(r"`([^`]+)`", last_paragraph(body)):
        if re.fullmatch(r"[a-z]+", tok) and tok not in seen:
            seen.append(tok)
    return seen


# --- exit mentions ------------------------------------------------------------------------------

EXIT_RE = re.compile(r"(?:\bExit|\(exit)\s+(non-zero|nonzero|\d)((?:\s*(?:,|or|and|/)\s*\d)*)")


def exit_codes(text):
    """Exit codes a piece of contract prose branches on. Capitalised `Exit N` anywhere, or a
    parenthesised `(exit N)`; a lowercase "must exit non-zero" about a script is not a branch."""
    codes = set()
    for m in EXIT_RE.finditer(text):
        if m.group(1).startswith("non"):
            codes |= {1, 2, 3}
        else:
            codes.add(int(m.group(1)))
            codes |= {int(d) for d in re.findall(r"\d", m.group(2))}
    return sorted(codes)


def exit_mentions(text):
    return [(m.start(), exit_codes(m.group(0))) for m in EXIT_RE.finditer(text)]


# --- registry and command mapping ---------------------------------------------------------------

def load_registry(src):
    return json.loads(src.text("gars/_system/tools/registry.json"))["tools"]


EXECUTABLES = ("python3", "python", "bash", "sh", "sbatch", "squeue", "scancel", "sacct", "date",
               "git", "source", "conda", "mamba", "pip", "pip3", "nextflow", "rm", "mv", "cp",
               "ls", "cat", "head", "tail", "grep", "rg", "find", "wc", "stat", "shasum")


def normalize_script(path):
    for prefix in ("<workspace>/", "$WS/", "./"):
        if path.startswith(prefix):
            path = path[len(prefix):]
    return path


def tool_of(tokens, registry):
    """The registry tool a command names, by argv prefix; None when unregistered."""
    if not tokens:
        return None
    if tokens[0] in ("python3", "python") and len(tokens) >= 2:
        script = normalize_script(tokens[1])
        for tool in registry:
            argv = tool["argv"]
            if tool.get("filesystem") or argv[1] != script:
                continue
            if len(argv) >= 3 and not argv[2].startswith("-"):
                if len(tokens) >= 3 and tokens[2] == argv[2]:
                    return tool["name"]
                continue
            return tool["name"]
        return None
    for tool in registry:
        if tool.get("filesystem") and tokens[0] == tool["argv"][0]:
            return tool["name"]
    return None


def split_words(command):
    try:
        return shlex.split(command)
    except ValueError:
        return command.split()


def strip_comment(command):
    m = re.search(r"\s#\s.*$", command)
    return (command[:m.start()].rstrip(), command[m.start():].strip()) if m else (command, None)


# Placeholder -> synthetic value. {project} {assay} {substage} {source} {root} are filled per
# guard scenario; anything absent from this table is "uninstantiable" and reported, never guessed.
PLACEHOLDERS = {
    "title": "{project}", "project_title": "{project}", "sanitized": "{project}",
    "Assay ID": "{assay}", "assay_id": "{assay}",
    "path": "{source}",
    "class": "public", "purpose": "fixture",
    "model id": MODEL_ID, "the exact model id you are running as": MODEL_ID,
    "exactly what the user replied": "01",
    "workspace": "{root}",
    "project dir": "projects/{project}",
    "sub-stage dir": "projects/{project}/02_bioinformatics/{assay}/{substage}",
    "job_id": "4242", "n": "1", "theirs": "~ condition", "type": "counts_gene",
    "slug": "qc-look", "NN_slug": "01_qc-look",
    "script": "projects/{project}/03_custom_analysis/01_qc-look/scripts/run.sh",
    "the sub-stage the resolver named": "01_nfcore-rnaseq-wrapper",
    "the sub-stage that supplied the matrix": "01_nfcore-scrnaseq-wrapper",
    "the sub-stage that supplied the object": "01_nfcore-spatialvi-wrapper",
    "resolved path": "projects/{project}/02_bioinformatics/{assay}/01_input/run/input.h5ad",
    "their answer as a regex with named groups sample, read and optionally lane":
        "(?P<sample>[A-Za-z0-9]+)_R(?P<read>[12]).fastq.gz",
}

# Values for registry-required fields a prose call leaves implicit ("with the same paths").
REQUIRED_VALUES = {
    "project": "projects/{project}",
    "counts": "projects/{project}/02_bioinformatics/rnaseq_bulk/01_nfcore-rnaseq-wrapper/run/"
              "results/star_salmon/salmon.merged.gene_counts_length_scaled.tsv",
    "design": "projects/{project}/01_samplesheets/rnaseq_bulk_design.csv",
    "h5ad": "projects/{project}/02_bioinformatics/{assay}/01_input/run/input.h5ad",
}


def instantiate(command):
    """(minimal, maximal, missing): optional [..] groups dropped / kept (a `[<x> ...]`
    repetition is always dropped), placeholders replaced; `missing` lists unknown placeholders."""
    minimal = command
    while True:
        new = re.sub(r"\s*\[[^\[\]]*\]", "", minimal)
        if new == minimal:
            break
        minimal = new
    maximal = re.sub(r"\s*\[[^\[\]]*\.\.\.[^\[\]]*\]", "", command)
    maximal = re.sub(r"\[([^\[\]]*)\]", r"\1", maximal)
    missing = []

    def fill(text):
        def repl(m):
            key = m.group(1)
            if key in PLACEHOLDERS:
                return PLACEHOLDERS[key]
            missing.append(m.group(0))
            return m.group(0)
        return re.sub(r"<([^<>]+)>", repl, text)
    return fill(minimal), fill(maximal), sorted(set(missing))


# --- calls in a step -----------------------------------------------------------------------------

PROSE_CALL_RE = re.compile(r"\b[Rr]un (?:the wrapper's )?`(check|prepare|collect|summary)`")


def wrapper_prefix(doc):
    """The `python3 _system/wrappers/<w>/<w>.py` a sub-stage contract invokes (Definitions)."""
    for i, line in enumerate(doc["lines"], 1):
        if i in doc["fenced"]:
            m = re.match(r"\s*(python3 _system/wrappers/\S+\.py)\b", line)
            if m:
                return m.group(1), i
    return None, None


def step_calls(doc, step, registry, wrapper):
    """Every command a step tells the agent to run: fenced, inline-backticked, a prose wrapper
    subcommand, a bare executable named in backticks, and the implicit `date` behind
    "today's date". Each with its line and kind; `tool` is None when the registry lacks it.
    Returns (calls, fenced lines that are not commands)."""
    calls, other = [], []
    for _, body in fenced_blocks(doc, step["start"], step["end"]):
        joined, first = "", None
        for ln, text in body:
            stripped = text.strip()
            if not stripped:
                continue
            if first is None:
                first = ln
            if stripped.endswith("\\"):
                joined += stripped[:-1].rstrip() + " "
                continue
            joined += stripped
            words = joined.split()
            if words and words[0] in EXECUTABLES:
                calls.append(make_call(joined, first, "fenced", registry))
            else:
                other.append({"line": first, "text": joined})
            joined, first = "", None
    text, offsets = prose(doc, step["start"], step["end"])
    for m in re.finditer(r"`([^`]+)`", text):
        inner = m.group(1).strip()
        words = inner.split()
        if not words or words[0] not in EXECUTABLES:
            continue
        kind = "inline" if len(words) > 1 else "executable"
        calls.append(make_call(inner, line_at(offsets, m.start()), kind, registry, m.start()))
    if wrapper[0]:
        for m in PROSE_CALL_RE.finditer(text):
            sentence_end = text.find(". ", m.end())
            sentence = text[m.start(): sentence_end if sentence_end > 0 else len(text)]
            flags = []
            for tok in re.findall(r"`(--[^`]+)`", sentence):
                name = tok[2:]
                flags.append(tok if " " in tok else
                             "%s %s" % (tok, REQUIRED_VALUES.get(name, "<resolved path>")))
            command = " ".join([wrapper[0], m.group(1), "--project projects/<title>"] + flags)
            calls.append(make_call(command, line_at(offsets, m.start()), "prose", registry,
                                   m.start()))
    for m in re.finditer(r"today's date", text):
        calls.append(make_call("date", line_at(offsets, m.start()), "implicit", registry,
                               m.start()))
    calls.sort(key=lambda c: (c["line"], c["_pos"]))
    return calls, other


def make_call(command, line, kind, registry, pos=0):
    literal = command
    command, comment = strip_comment(command)
    words = split_words(command)
    return {"command": command, "literal": literal, "comment": comment, "line": line,
            "kind": kind, "executable": words[0] if words else None,
            "tool": tool_of(words, registry), "_pos": pos}


# --- helper exit sites (AST) ----------------------------------------------------------------------

class Module:
    def __init__(self, path, text):
        self.path, self.text = path, text
        self.tree = ast.parse(text)
        self.functions = {n.name: n for n in self.tree.body if isinstance(n, ast.FunctionDef)}
        self.constants, self.aliases, self.from_imports = {}, {}, {}
        for node in self.tree.body:
            self._scan_top(node)

    def _scan_top(self, node):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and isinstance(node.value, ast.Constant) \
                        and isinstance(node.value.value, int):
                    self.constants[target.id] = node.value.value
                if isinstance(target, ast.Tuple) and isinstance(node.value, ast.Tuple):
                    for t, v in zip(target.elts, node.value.elts):
                        if isinstance(t, ast.Name) and isinstance(v, ast.Constant) \
                                and isinstance(v.value, int):
                            self.constants[t.id] = v.value
        elif isinstance(node, ast.Import):
            for a in node.names:
                self.aliases[a.asname or a.name] = a.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            for a in node.names:
                self.from_imports[a.asname or a.name] = (node.module, a.name)
        elif isinstance(node, (ast.If, ast.Try)):
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.Import, ast.ImportFrom, ast.Assign)):
                    self._scan_top(child)


class HelperIndex:
    """The `_system` modules of the pinned tree, loaded on demand by import name."""
    SEARCH = ("gars/_system/", "gars/_system/tools/")

    def __init__(self, src):
        self.src, self.modules, self.names, self.memo = src, {}, {}, {}

    def by_path(self, path):
        if path not in self.modules:
            self.modules[path] = Module(path, self.src.text(path))
        return self.modules[path]

    def by_name(self, name):
        if name not in self.names:
            rel = name.replace(".", "/") + ".py"
            found = None
            for base in self.SEARCH:
                if self.src.exists(base + rel):
                    found = self.by_path(base + rel)
                    break
            self.names[name] = found
        return self.names[name]

    def constant(self, mod, name, depth=0):
        if name in mod.constants:
            return mod.constants[name]
        if name in mod.from_imports and depth < 4:
            other = self.by_name(mod.from_imports[name][0])
            if other is not None:
                return self.constant(other, mod.from_imports[name][1], depth + 1)
        return None

    def function(self, mod, func):
        """(module, FunctionDef) a call target names, or None."""
        if isinstance(func, ast.Name):
            if func.id in mod.functions:
                return mod, mod.functions[func.id]
            if func.id in mod.from_imports:
                other = self.by_name(mod.from_imports[func.id][0])
                if other is not None and mod.from_imports[func.id][1] in other.functions:
                    return other, other.functions[mod.from_imports[func.id][1]]
            return None
        if isinstance(func, ast.Attribute):
            owner = self.module_of(mod, func.value)
            if owner is not None and func.attr in owner.functions:
                return owner, owner.functions[func.attr]
        return None

    def module_of(self, mod, node):
        if isinstance(node, ast.Name) and node.id in mod.aliases:
            return self.by_name(mod.aliases[node.id])
        if isinstance(node, ast.Attribute):
            outer = self.module_of(mod, node.value)
            if outer is not None and node.attr in outer.aliases:
                return self.by_name(outer.aliases[node.attr])
        return None

    def codes(self, mod, node, params):
        """The int codes an expression can take; ("param", name) for a parameter; None when
        unresolved."""
        if isinstance(node, ast.Constant) and isinstance(node.value, int) \
                and not isinstance(node.value, bool):
            return [node.value]
        if isinstance(node, ast.Name):
            if node.id in params:
                return ("param", node.id)
            value = self.constant(mod, node.id)
            return None if value is None else [value]
        if isinstance(node, ast.Attribute):
            owner = self.module_of(mod, node.value)
            if owner is not None:
                value = self.constant(owner, node.attr)
                return None if value is None else [value]
            return None
        if isinstance(node, ast.IfExp):
            a, b = self.codes(mod, node.body, params), self.codes(mod, node.orelse, params)
            if isinstance(a, list) and isinstance(b, list):
                return sorted(set(a + b))
        return None


def is_emit(index, mod, call):
    target = index.function(mod, call.func)
    name = target[1].name if target else (call.func.attr if isinstance(call.func, ast.Attribute)
                                          else getattr(call.func, "id", None))
    return name == "emit"


def bind_args(index, caller_mod, call, callee, caller_params, caller_bindings):
    """{param: codes | ("default", node) | None} for a callee, from the call's arguments
    (evaluated in the caller) or the callee's defaults (evaluated later, in the callee)."""
    names = [a.arg for a in callee.args.args]
    bound = {}
    defaults = callee.args.defaults
    for name, default in zip(names[len(names) - len(defaults):], defaults):
        bound[name] = ("default", default)
    pairs = list(zip(names, call.args)) + [(kw.arg, kw.value) for kw in call.keywords
                                           if kw.arg in names]
    for name, node in pairs:
        value = index.codes(caller_mod, node, caller_params)
        if isinstance(value, tuple) and value[0] == "param":
            value = caller_bindings.get(value[1])
        bound[name] = value
    return bound


UNKNOWN = object()


def binding_key(bindings):
    out = []
    for name, value in sorted(bindings.items()):
        if isinstance(value, tuple) and value[0] == "default":
            out.append((name, "default", getattr(value[1], "lineno", 0),
                        ast.dump(value[1])))
        elif isinstance(value, list):
            out.append((name, tuple(value)))
        else:
            out.append((name, repr(value)))
    return tuple(out)


class Flags:
    """What a concrete command line makes true of `args.<dest>`: store_true flags are True when
    present and False when absent; an option whose default is None `is None` when absent.
    Anything else is unknown, and both branches stay reachable."""

    def __init__(self, module, words):
        self.present = {w[2:].split("=")[0].replace("-", "_") for w in words if w.startswith("--")}
        self.kinds = {}
        for node in ast.walk(module.tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and \
                    node.func.attr == "add_argument" and node.args and \
                    isinstance(node.args[0], ast.Constant) and \
                    str(node.args[0].value).startswith("--"):
                dest = node.args[0].value[2:].replace("-", "_")
                kw = {k.arg: k.value for k in node.keywords}
                if isinstance(kw.get("action"), ast.Constant) and kw["action"].value == "store_true":
                    self.kinds[dest] = "bool"
                elif "default" not in kw or (isinstance(kw["default"], ast.Constant)
                                             and kw["default"].value is None):
                    self.kinds.setdefault(dest, "none_default")

    def truth(self, test):
        if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
            inner = self.truth(test.operand)
            return UNKNOWN if inner is UNKNOWN else (not inner)
        if args_attr(test) and self.kinds.get(test.attr) == "bool":
            return test.attr in self.present
        if isinstance(test, ast.Compare) and args_attr(test.left) and len(test.ops) == 1 and \
                isinstance(test.comparators[0], ast.Constant) and \
                test.comparators[0].value is None and \
                self.kinds.get(test.left.attr) == "none_default" and \
                test.left.attr not in self.present:
            if isinstance(test.ops[0], ast.Is):
                return True
            if isinstance(test.ops[0], ast.IsNot):
                return False
        return UNKNOWN


def terminates(body):
    return bool(body) and isinstance(body[-1], (ast.Return, ast.Raise))


class SiteWalker:
    """Collect exit sites reachable from one function body: `return emit(_, CODE)`,
    `raise SystemExit(emit(...))`, `raise SystemExit(CODE)`, `sys.exit(N)`, argparse's usage
    exit (2, no JSON), and `return CODE` in main; and the same inside every function it calls.
    A call whose value is returned contributes all its sites; a call whose value is dropped
    contributes only its raises. With `flags`, a branch the command line decides is followed
    one way only, and a block stops after a statement that always leaves it."""

    def __init__(self, index, flags=None):
        self.index, self.flags = index, flags

    def walk(self, mod, fn, bindings=None, returned=True, depth=0, stack=(), via=()):
        if self.flags is not None:
            return self.walk_body(mod, fn.name, fn.args, fn.body, bindings, returned, depth,
                                  stack, via)
        # Callees are walked without flags, so their sites depend only on the function, the
        # bound codes and whether the value is returned: memoize, then re-prefix `via`.
        key = (mod.path, fn.name, returned, binding_key(bindings or {}))
        if key in self.index.memo:
            cached = self.index.memo[key]
            if cached is None:          # in progress: a recursive cycle; cut it
                return []
            return [dict(s, via=list(via) + s["via"]) for s in cached]
        self.index.memo[key] = None
        sites = self.walk_body(mod, fn.name, fn.args, fn.body, bindings, returned, depth,
                               stack, ())
        self.index.memo[key] = sites
        return [dict(s, via=list(via) + s["via"]) for s in sites]

    def walk_body(self, mod, name, arguments, body, bindings=None, returned=True, depth=0,
                  stack=(), via=()):
        if depth > 12 or (mod.path, name, len(body)) in stack:
            return []
        ctx = {"mod": mod, "name": name, "params": {a.arg for a in arguments.args},
               "bindings": bindings or {}, "returned": returned, "depth": depth,
               "stack": stack + ((mod.path, name, len(body)),), "via": via,
               "parsers": set(), "sites": []}
        for stmt in body:
            for node in ast.walk(stmt):
                if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) and \
                        isinstance(node.value.func, ast.Attribute) and \
                        node.value.func.attr == "ArgumentParser":
                    ctx["parsers"] |= {t.id for t in node.targets if isinstance(t, ast.Name)}
        self._block(ctx, body, [])
        return ctx["sites"]

    def _site(self, ctx, node, codes, how, conds):
        mod = ctx["mod"]
        if isinstance(codes, tuple) and codes[0] == "param":
            bound = ctx["bindings"].get(codes[1])
            if isinstance(bound, tuple) and bound[0] == "default":
                bound = self.index.codes(mod, bound[1], set())
            codes = bound
        if not isinstance(codes, list):
            codes = [None]
        return [{"code": code, "at": "%s:%d" % (mod.path, node.lineno), "how": how,
                 "condition": " and ".join(c for c in conds[-2:] if c), "via": list(ctx["via"]),
                 "line": mod.text.split("\n")[node.lineno - 1].strip()} for code in codes]

    def _segment(self, ctx, node):
        return (ast.get_source_segment(ctx["mod"].text, node) or "").replace("\n", " ")

    def _block(self, ctx, body, conds):
        """Visit statements in order; True when the block always leaves (return/raise)."""
        for stmt in body:
            if self._stmt(ctx, stmt, conds):
                return True
        return False

    def _stmt(self, ctx, stmt, conds):
        if isinstance(stmt, (ast.FunctionDef, ast.ClassDef)):
            return False
        if isinstance(stmt, ast.If):
            self._calls(ctx, stmt.test, conds)
            truth = self.flags.truth(stmt.test) if self.flags else UNKNOWN
            seg = self._segment(ctx, stmt.test)
            if truth is True:
                return self._block(ctx, stmt.body, conds + [seg])
            if truth is False:
                return self._block(ctx, stmt.orelse, conds + ["not (%s)" % seg])
            a = self._block(ctx, stmt.body, conds + [seg])
            b = self._block(ctx, stmt.orelse, conds + ["not (%s)" % seg])
            return a and b and bool(stmt.orelse)
        if isinstance(stmt, ast.Try):
            self._block(ctx, stmt.body, conds)
            for handler in stmt.handlers:
                self._block(ctx, handler.body, conds)
            self._block(ctx, stmt.orelse, conds)
            self._block(ctx, stmt.finalbody, conds)
            return False
        if isinstance(stmt, (ast.For, ast.While)):
            self._calls(ctx, stmt.iter if isinstance(stmt, ast.For) else stmt.test, conds)
            self._block(ctx, stmt.body, conds)
            self._block(ctx, stmt.orelse, conds)
            return False
        if isinstance(stmt, ast.With):
            for item in stmt.items:
                self._calls(ctx, item.context_expr, conds)
            return self._block(ctx, stmt.body, conds)
        if isinstance(stmt, ast.Return):
            self._return(ctx, stmt, conds)
            return True
        if isinstance(stmt, ast.Raise):
            self._raise(ctx, stmt, conds)
            return True
        for child in ast.iter_child_nodes(stmt):
            if isinstance(child, ast.expr):
                self._calls(ctx, child, conds)
        return False

    def _return(self, ctx, stmt, conds):
        value, mod = stmt.value, ctx["mod"]
        if value is None:
            return
        if isinstance(value, ast.Call) and ctx["returned"]:
            if is_emit(self.index, mod, value) and len(value.args) >= 2:
                self._calls_in_args(ctx, value, conds)
                ctx["sites"] += self._site(ctx, stmt, self.index.codes(mod, value.args[1],
                                                                       ctx["params"]),
                                           "emit", conds)
                return
            target = self.index.function(mod, value.func)
            if target is not None:
                self._calls_in_args(ctx, value, conds)
                self._follow(ctx, value, target, conds, True)
                return
        if ctx["name"] == "main" and ctx["returned"]:
            codes = self.index.codes(mod, value, ctx["params"])
            if isinstance(codes, list):
                ctx["sites"] += self._site(ctx, stmt, codes, "return", conds)
                return
        self._calls(ctx, value, conds)

    def _raise(self, ctx, stmt, conds):
        exc, mod = stmt.exc, ctx["mod"]
        if isinstance(exc, ast.Call) and getattr(exc.func, "id", None) == "SystemExit" and exc.args:
            arg = exc.args[0]
            if isinstance(arg, ast.Call) and is_emit(self.index, mod, arg) and len(arg.args) >= 2:
                ctx["sites"] += self._site(ctx, stmt, self.index.codes(mod, arg.args[1],
                                                                       ctx["params"]),
                                           "raise", conds)
                return
            ctx["sites"] += self._site(ctx, stmt, self.index.codes(mod, arg, ctx["params"]),
                                       "raise", conds)
            return
        if exc is not None:
            self._calls(ctx, exc, conds)

    def _calls_in_args(self, ctx, call, conds):
        for arg in list(call.args) + [k.value for k in call.keywords]:
            self._calls(ctx, arg, conds)

    def _follow(self, ctx, call, target, conds, returned):
        mod = ctx["mod"]
        sub = bind_args(self.index, mod, call, target[1], ctx["params"], ctx["bindings"])
        for site in SiteWalker(self.index).walk(
                target[0], target[1], sub, returned, ctx["depth"] + 1, ctx["stack"],
                ctx["via"] + ("%s:%d" % (mod.path, call.lineno),)):
            if not returned and site["how"] not in ("raise", "sys.exit", "argparse"):
                continue
            site["condition"] = " and ".join(c for c in conds[-2:] + [site["condition"]] if c)
            ctx["sites"].append(site)

    def _calls(self, ctx, expr, conds):
        """Calls inside an expression whose value is dropped: sys.exit, argparse, and the raises
        of any helper function called."""
        mod = ctx["mod"]
        for node in ast.walk(expr):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) \
                    and func.value.id == "sys" and func.attr == "exit" and node.args:
                ctx["sites"] += self._site(ctx, node, self.index.codes(mod, node.args[0],
                                                                       ctx["params"]),
                                           "sys.exit", conds)
                continue
            if isinstance(func, ast.Attribute) and func.attr == "parse_args":
                ctx["sites"] += self._site(ctx, node, [2], "argparse", conds)
                continue
            if isinstance(func, ast.Attribute) and func.attr == "error" and \
                    isinstance(func.value, ast.Name) and func.value.id in ctx["parsers"]:
                ctx["sites"] += self._site(ctx, node, [2], "argparse", conds)
                continue
            target = self.index.function(mod, func)
            if target is None or target[1].name == "emit":
                continue
            self._follow(ctx, node, target, conds, False)


def dispatch_scopes(main):
    """({subcommand: [("func", name) | ("block", If)]}, common statements).

    Dict dispatch (`{"name": cmd_x}[args.cmd](...)`) and if-chains (`if args.command == "x":`)
    scope their sites to those names; `if not args.cmd:` (no subcommand) belongs to none; a
    statement after the last scoped construct is the unknown-command fall-through and is
    excluded."""
    scoped, common, last = {}, [], -1
    for k, stmt in enumerate(main.body):
        if scoped_names(stmt) or dict_dispatch(stmt) or no_command(stmt):
            last = k
    for k, stmt in enumerate(main.body):
        names, dispatch = scoped_names(stmt), dict_dispatch(stmt)
        if no_command(stmt):
            continue
        if names:
            for name in names:
                scoped.setdefault(name, []).append(("block", stmt))
            continue
        if dispatch:
            for name, func in dispatch.items():
                scoped.setdefault(name, []).append(("func", func))
            continue
        if last >= 0 and k > last:
            continue
        common.append(stmt)
    return scoped, common


def args_attr(node):
    return isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) \
        and node.value.id == "args"


def scoped_names(stmt):
    if not isinstance(stmt, ast.If):
        return None
    test = stmt.test
    if isinstance(test, ast.Compare) and args_attr(test.left) and len(test.ops) == 1:
        comp = test.comparators[0]
        if isinstance(test.ops[0], ast.Eq) and isinstance(comp, ast.Constant):
            return [comp.value]
        if isinstance(test.ops[0], ast.In) and isinstance(comp, (ast.Tuple, ast.List)):
            return [e.value for e in comp.elts if isinstance(e, ast.Constant)]
    return None


def no_command(stmt):
    return isinstance(stmt, ast.If) and isinstance(stmt.test, ast.UnaryOp) and \
        isinstance(stmt.test.op, ast.Not) and args_attr(stmt.test.operand) and \
        stmt.test.operand.attr in ("cmd", "command")


def dict_dispatch(stmt):
    for node in ast.walk(stmt):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Dict):
            keys = node.value.keys
            if keys and all(isinstance(k, ast.Constant) and isinstance(k.value, str) for k in keys):
                return {k.value: v.id for k, v in zip(keys, node.value.values)
                        if isinstance(v, ast.Name)}
    return None


def helper_exits(src, index, tool, words=None):
    """({code: [site]}, problem) for one registry tool, from its module's main().

    With `words` (a concrete command line), branches the flags decide are followed one way."""
    argv = tool["argv"]
    mod = index.by_path("gars/" + argv[1])
    sub = argv[2] if len(argv) >= 3 and not argv[2].startswith("-") else None
    main = mod.functions.get("main")
    if main is None:
        return {}, "no main()"
    flags = Flags(mod, words) if words is not None else None
    walker = SiteWalker(index, flags)
    if sub is None:
        sites = walker.walk(mod, main)
    else:
        scoped, common = dispatch_scopes(main)
        sites = walker.walk_body(mod, "main", main.args, common)
        for kind, item in scoped.get(sub, []):
            if kind == "func":
                sites += walker.walk(mod, mod.functions[item], {}, True, 1, (),
                                     ("%s:%d" % (mod.path, main.lineno),))
            else:
                sites += walker.walk_body(mod, "main", main.args, item.body)
    out, seen = {}, set()
    for site in sites:
        key = (site["code"], site["at"], site["how"])
        if key in seen:
            continue
        seen.add(key)
        out.setdefault(str(site["code"]), []).append(site)
    for code in out:
        out[code].sort(key=lambda s: (s["at"].rsplit(":", 1)[0], int(s["at"].rsplit(":", 1)[1])))
    return dict(sorted(out.items())), None


def real_codes(exits):
    """Codes with at least one site that is not argparse's usage exit."""
    return sorted(int(c) for c, sites in exits.items()
                  if c != "None" and any(s["how"] != "argparse" for s in sites))


# --- JSON key vocabulary ---------------------------------------------------------------------

def key_vocabulary(src, module_paths):
    """String keys a module can write into its JSON: dict-literal keys, `x["k"] = ...` targets,
    `setdefault("k", ...)`, and keyword names of dict(...)/update(...). Paths are relative to
    gars/ (as the registry spells them) or to the repository."""
    vocab = set()
    for path in module_paths:
        full = path if path.startswith("gars/") else "gars/" + path
        tree = ast.parse(src.text(full))
        for node in ast.walk(tree):
            if isinstance(node, ast.Dict):
                vocab |= {k.value for k in node.keys
                          if isinstance(k, ast.Constant) and isinstance(k.value, str)}
            elif isinstance(node, (ast.Assign, ast.AugAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for t in targets:
                    if isinstance(t, ast.Subscript):
                        sl = t.slice
                        if isinstance(sl, ast.Constant) and isinstance(sl.value, str):
                            vocab.add(sl.value)
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "setdefault" and node.args and \
                        isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                    vocab.add(node.args[0].value)
                if node.func.attr in ("update",):
                    vocab |= {kw.arg for kw in node.keywords if kw.arg}
            if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "dict":
                vocab |= {kw.arg for kw in node.keywords if kw.arg}
    return vocab


def key_tokens(vocab):
    tokens = set()
    for key in vocab:
        for tok in re.split(r"[^a-z0-9]+", key.lower()):
            if tok:
                tokens.add(tok)
    return tokens


GENERIC = {"n", "path", "title", "project_title", "sanitized", "raw", "Assay ID", "assay_id",
           "assay", "name", "ids", "workspace", "project dir", "NN_name", "NN_slug", "sample_id",
           "timestamp", "sub-stage", "type", "jobid", "step"}
STOPWORDS = {"of", "the", "a", "an", "in", "to", "and", "or", "for", "per", "not"}


def singular(word):
    word = word.lower().replace("(s)", "")
    return word[:-1] if word.endswith("s") and len(word) > 3 else word


def count_label(line, start, end):
    """The words labelling a `<n>`: the word right after it, else the label before a colon."""
    after = re.match(r"\s+([A-Za-z][A-Za-z0-9]*(?:\(s\))?)", line[end:])
    if after:
        return [after.group(1)]
    before = re.search(r"([A-Za-z][A-Za-z ()]*?):\s*$", line[:start])
    if before:
        return [w for w in re.findall(r"[A-Za-z0-9]+", before.group(1))]
    return []


def bind_placeholder(text, line, vocab, start=None):
    """How one placeholder is filled: generic (context), choice (a|b), composed (model-written
    text), artifact (`<type path>`), key (a JSON key the helper writes), label (a count whose
    label matches a key), unbound (named or labelled, with no key in the helper), or no_source
    (the template has no backing helper call at all)."""
    inner = text[1:-1]
    if "|" in inner:
        return {"text": text, "binding": "choice"}
    m = re.fullmatch(r"(?:resolved )?([a-z][a-z0-9_]*) (path|dir)", inner)
    if m:
        return {"text": text, "binding": "artifact", "artifact": m.group(1)}
    if inner == "n":
        if start is None:
            start = line.find(text)
        labels = [w for w in count_label(line, start, start + len(text)) if w.lower() not in STOPWORDS]
        if not labels:
            return {"text": text, "binding": "generic"}
        if vocab is None:
            return {"text": text, "binding": "no_source", "label": singular(labels[0])}
        tokens = {singular(t) for t in key_tokens(vocab)}
        if any(singular(w) in tokens for w in labels):
            return {"text": text, "binding": "label", "label": " ".join(labels).lower()}
        return {"text": text, "binding": "unbound", "label": singular(labels[-1])}
    if inner in GENERIC:
        return {"text": text, "binding": "generic"}
    if re.fullmatch(r"[a-z][a-z0-9_]*(\.[a-z0-9_]+)*", inner):
        if vocab is None:
            return {"text": text, "binding": "no_source", "label": inner}
        last = inner.split(".")[-1]
        if inner in vocab or last in vocab:
            return {"text": text, "binding": "key", "label": inner}
        return {"text": text, "binding": "unbound", "label": inner}
    return {"text": text, "binding": "composed"}


# --- file actions ----------------------------------------------------------------------------------

FILE_RULES = [
    (r"\bRead (?:the|each sub-stage's) STATUS file", "Read", "{substage_dir}/STATUS"),
    (r"\bRead each assay config\b", "Read", "projects/{project}/_config/{assay}.yaml"),
    (r"\b[Ww]rite exactly their supplied values into the existing `_config/<Assay ID>\.yaml`",
     "Edit", "projects/{project}/_config/{assay}.yaml"),
    (r"\b[Aa]ppend (?:a |the script's |its |the returned )?`?(?:history_entry`? (?:to )?)?"
     r"(?:the project's )?`?HISTORY\.md`?", "Edit", "projects/{project}/HISTORY.md"),
    (r"\b[Aa]ppend (?:its|the returned|the script's) `history_entry`", "Edit",
     "projects/{project}/HISTORY.md"),
    (r"\bfrom `_references/assay_stage_skill_map\.md`", "Read",
     "_references/assay_stage_skill_map.md"),
    (r"\bread its `Consumes` column from the assay map", "Read",
     "_references/assay_stage_skill_map.md"),
    (r"\bRead `02_bioinformatics/<Assay ID>/<NN_name>/CONTEXT\.md`", "Read",
     "02_bioinformatics/{assay}/{substage}/CONTEXT.md"),
    (r"\breplace every `<FILL: \.\.\.>` marker in the created `PLAN\.md`", "Edit",
     "projects/{project}/03_custom_analysis/01_qc-look/PLAN.md"),
    (r"\bapply them to `PLAN\.md`", "Edit",
     "projects/{project}/03_custom_analysis/01_qc-look/PLAN.md"),
    (r"\bwrite its scripts under `scripts/`", "Write",
     "projects/{project}/03_custom_analysis/01_qc-look/scripts/run.sh"),
    (r"\bthe analysis log says\b", "Read", "{substage_dir}/logs/analysis.log"),
]
FILE_VERB_RE = re.compile(r"\b(read|write|append|edit|replace|apply them)\b", re.I)


def step_file_actions(text, offsets):
    """File reads and writes a step tells the agent to make, by the explicit rules above; every
    sentence with a file verb that no rule matches is returned as unclassified."""
    actions, matched_spans = [], []
    for pattern, tool, path in FILE_RULES:
        for m in re.finditer(pattern, text):
            if any(a <= m.start() < b for a, b in matched_spans):
                continue
            matched_spans.append((m.start(), m.end()))
            actions.append({"tool": tool, "path": path, "line": line_at(offsets, m.start()),
                            "phrase": m.group(0)})
    unclassified = []
    for sentence in re.finditer(r"[^.]+(?:\.|$)", text):
        s, e = sentence.start(), sentence.end()
        if not FILE_VERB_RE.search(sentence.group(0)):
            continue
        if any(s <= a < e for a, _ in matched_spans):
            continue
        unclassified.append({"line": line_at(offsets, s), "sentence": sentence.group(0).strip()})
    actions.sort(key=lambda a: a["line"])
    return actions, unclassified


# --- guard coverage ------------------------------------------------------------------------------

SCENARIOS = ("public", "closed", "fresh", "fresh_declared", "mixed")
PROJECT = "demo"
ASSAYS = ("rnaseq_bulk", "atacseq_bulk", "chipseq_bulk", "cutandrun", "methylseq", "scrnaseq",
          "spatialvi")


class GuardHarness:
    """Synthetic workspaces at the pin, and `decide()` run in-process on synthetic payloads.

    public          projects/demo, dataset row `public`, a full stamp, every assay's config and a
                    sub-stage manifest whose config hash holds (so collect is judged on the rules,
                    not on a broken fixture)
    closed          the same project with data_class `deidentified_under_agreement`
    fresh           projects/demo exactly as `create` leaves it: no dataset row, empty raw/
    fresh_declared  fresh, raw/ linked into a source folder a human declared public in
                    data_sources.tsv (the one opening decision 0107 gives an agent)
    mixed           the public project beside a closed sibling project `other`
    """

    def __init__(self, src, tmp):
        self.tmp = os.path.realpath(tmp)
        pristine = os.path.join(self.tmp, "pristine")
        src.export(["gars/_system", "gars/_references", "gars/_templates"], pristine)
        self.roots = {}
        for name in SCENARIOS:
            root = os.path.join(self.tmp, name, "gars")
            shutil.copytree(os.path.join(pristine, "gars"), root, symlinks=True)
            os.makedirs(os.path.join(root, "projects"))
            self.roots[name] = root
            self._build(name, root)
        self.system = os.path.join(pristine, "gars", "_system")
        self.guard = load_guard(self.system)

    def close(self):
        if self.system in sys.path:
            sys.path.remove(self.system)

    def source(self, scenario):
        return os.path.join(self.tmp, scenario, "source")

    def _build(self, name, root):
        source = self.source(name)
        os.makedirs(source)
        with open(os.path.join(source, "S1_S1_L001_R1_001.fastq.gz"), "wb") as fh:
            fh.write(b"\x1f\x8b\x08\x00")
        project = os.path.join(root, "projects", PROJECT)
        if name in ("fresh", "fresh_declared"):
            self._fresh(root, project)
            if name == "fresh_declared":
                raw = os.path.join(project, "00_data", "rnaseq_bulk", "raw")
                os.symlink(os.path.join(source, "S1_S1_L001_R1_001.fastq.gz"),
                           os.path.join(raw, "S1_S1_L001_R1_001.fastq.gz"))
                with open(os.path.join(root, "data_sources.tsv"), "w") as fh:
                    fh.write("source\tdata_class\tdeclared_by\n%s\tpublic\tstepmap\n" % source)
            return
        self._full(root, project, "deidentified_under_agreement" if name == "closed" else "public")
        if name == "mixed":
            self._full(root, os.path.join(root, "projects", "other"),
                       "deidentified_under_agreement")

    def _fresh(self, root, project):
        for d in ("00_data/rnaseq_bulk/raw", "_config"):
            os.makedirs(os.path.join(project, d))
        for f in ("00_data/.gitkeep", "_config/.gitkeep"):
            open(os.path.join(project, f), "w").close()
        for f in ("CONTEXT.md", "HISTORY.md"):
            shutil.copy(os.path.join(root, "_templates", "project", f), os.path.join(project, f))
        for f in ("executor.yaml", "nextflow.slurm.config", "rnaseq_bulk.yaml"):
            shutil.copy(os.path.join(root, "_templates", "config", f),
                        os.path.join(project, "_config", f))

    def _full(self, root, project, data_class):
        os.makedirs(os.path.join(project, "_config"))
        for f in ("CONTEXT.md", "HISTORY.md"):
            shutil.copy(os.path.join(root, "_templates", "project", f), os.path.join(project, f))
        shutil.copy(os.path.join(root, "_templates", "config", "executor.yaml"),
                    os.path.join(project, "_config", "executor.yaml"))
        os.makedirs(os.path.join(project, "01_samplesheets"))
        os.makedirs(os.path.join(project, "00_data"))
        with open(os.path.join(project, "00_data", "dataset.tsv"), "w") as fh:
            fh.write("data_class\tpurpose\tagreement_ref\tinput_data_location\tpermitted_backends\t"
                     "provider_exposure\tretention\texpiry\n%s\tfixture\tnone\t[]\tslurm\tnone\t"
                     "none\tnone\n" % data_class)
        for assay in ASSAYS:
            os.makedirs(os.path.join(project, "00_data", assay, "raw"))
            cfg = os.path.join(project, "_config", assay + ".yaml")
            shutil.copy(os.path.join(root, "_templates", "config", assay + ".yaml"), cfg)
            digest = hashlib.sha256(open(cfg, "rb").read()).hexdigest()
            for substage in self._substages(root, assay):
                stage = os.path.join(project, "02_bioinformatics", assay, substage)
                os.makedirs(os.path.join(stage, "reproducibility"))
                os.makedirs(os.path.join(stage, "logs"))
                with open(os.path.join(stage, "reproducibility", "manifest.json"), "w") as fh:
                    json.dump({"config_sha256": digest}, fh)
                with open(os.path.join(stage, "STATUS"), "w") as fh:
                    fh.write("SUBMITTED 4242 2026-10-07T00:00:00\n")
        analysis = os.path.join(project, "03_custom_analysis", "01_qc-look", "scripts")
        os.makedirs(analysis)
        with open(os.path.join(project, "03_custom_analysis", "01_qc-look", "PLAN.md"), "w") as fh:
            fh.write("# Plan\n")

    @staticmethod
    def _substages(root, assay):
        out = []
        with open(os.path.join(root, "_references", "assay_stage_skill_map.md")) as fh:
            for line in fh:
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if len(cells) >= 4 and cells[1] == assay:
                    out.append(cells[3])
        return out

    def fill(self, scenario, text, assay="rnaseq_bulk", substage="01_nfcore-rnaseq-wrapper"):
        root = self.roots[scenario]
        for key, value in (("{project}", PROJECT), ("{assay}", assay), ("{substage}", substage),
                           ("{source}", self.source(scenario)), ("{root}", root),
                           ("{substage_dir}", "projects/%s/02_bioinformatics/%s/%s"
                            % (PROJECT, assay, substage))):
            text = text.replace(key, value)
        return text

    def _decide(self, scenario, payload):
        err = io.StringIO()
        try:
            with contextlib.redirect_stderr(err):
                self.guard.decide(payload, self.roots[scenario])
        except SystemExit as exc:
            return {"allow": exc.code == 0 or exc.code is None,
                    "reason": self.scrub(err.getvalue().strip())}
        return {"allow": True, "reason": ""}

    def scrub(self, text):
        return text.replace(self.tmp, "<scenario-root>")

    def bash(self, scenario, command, assay="rnaseq_bulk", substage="01_nfcore-rnaseq-wrapper"):
        root = self.roots[scenario]
        return self._decide(scenario, {"tool_name": "Bash", "cwd": root, "tool_input": {
            "command": self.fill(scenario, command, assay, substage)}})

    def file(self, scenario, tool, relpath, assay="rnaseq_bulk",
             substage="01_nfcore-rnaseq-wrapper"):
        root = self.roots[scenario]
        path = os.path.join(root, self.fill(scenario, relpath, assay, substage))
        tool_input = {"file_path": path}
        if tool == "Edit":
            tool_input.update({"old_string": "a", "new_string": "b"})
        if tool == "Write":
            tool_input.update({"content": "x"})
        return self._decide(scenario, {"tool_name": tool, "cwd": root, "tool_input": tool_input})

    def edit(self, scenario, relpath):
        return self.file(scenario, "Edit", relpath)

    def dispatcher_form(self, scenario, command, assay, substage):
        """The same call through `python3 _system/tool_call.py <tool> '<json>'`, built with the
        pinned policy's own parser; None when the direct form does not parse."""
        policy = sys.modules.get("tools.policy")
        root = self.roots[scenario]
        try:
            tokens = shlex.split(self.fill(scenario, command, assay, substage))
            tool, args = policy.parse_argv(tokens, root, root)
        except Exception:  # noqa: BLE001 -- any parse refusal means no dispatcher form exists
            return None
        if tool.get("filesystem"):
            return None
        return "python3 _system/tool_call.py %s '%s'" % (tool["name"], json.dumps(args,
                                                                                 sort_keys=True))


GUARD_MODULES = ("guard_hook", "tools", "workspace", "executorlib", "venue_policy",
                 "integrity", "wrapperlib")


def load_guard(system):
    """Import the pinned `guard_hook` from an exported `_system/`, fresh: modules cached from an
    earlier export are dropped first, and the export stays on sys.path because the guard imports
    some of its modules lazily, at decision time."""
    for name in list(sys.modules):
        if name.split(".")[0] in GUARD_MODULES:
            del sys.modules[name]
    sys.path[:] = [p for p in sys.path if not p.endswith(os.path.join("gars", "_system"))]
    sys.path.insert(0, system)
    import importlib
    return importlib.import_module("guard_hook")


def intended_scenario(contract_path, tool):
    if contract_path.startswith("gars/00_") and tool and tool.startswith("stage00_register."):
        return "fresh_declared"
    return "public"


# --- one contract ---------------------------------------------------------------------------

def extract_text(path, text, src, registry=None, index=None, guard=None, helpers=None):
    registry = registry if registry is not None else load_registry(src)
    index = index or HelperIndex(src)
    helpers = helpers if helpers is not None else {}
    doc = parse_markdown(text)
    steps = parse_steps(doc)
    templates = parse_templates(doc)
    wrapper = wrapper_prefix(doc)
    assay, substage = contract_assay(path)
    findings = []
    if not steps:
        findings.append({"kind": "no_process_steps", "source": path})
    out_steps, events, file_unclassified, fenced_other = [], [], [], []
    for k, step in enumerate(steps):
        text_, offsets = prose(doc, step["start"], step["end"])
        calls, other = step_calls(doc, step, registry, wrapper)
        fenced_other += [dict(o, step=step["n"]) for o in other]
        actions, unclassified = step_file_actions(text_, offsets)
        file_unclassified += [dict(u, step=step["n"]) for u in unclassified]
        mentions = exit_mentions(text_)
        out_steps.append({
            "n": step["n"], "start": step["start"], "end": step["end"],
            "source": "%s:%d-%d" % (path, step["start"], step["end"]),
            "text": text_,
            "templates": list(dict.fromkeys(re.findall(r"\bT\d+[a-z]?\b", text_))),
            "exit_mentions": [{"line": line_at(offsets, pos), "codes": codes}
                              for pos, codes in mentions],
            "calls": calls, "file_actions": actions, "_offsets": offsets,
            "waits_word": bool(re.search(r"\bwait\b", text_, re.I)
                               and not re.search(r"\b(Do not|not) wait\b", text_)),
        })
        for call in calls:
            if call["tool"]:
                events.append(((call["line"], call["_pos"]), k, "call", call))
        for pos, codes in mentions:
            events.append(((line_at(offsets, pos), pos), k, "exit", codes))
    # Exit regions: a registered call opens a region that collects every exit mention after it,
    # across step boundaries, until the next call that opens one. A call inside an exit branch
    # ("Exit 2 -> call status ...") is a branch action and opens nothing.
    events.sort(key=lambda e: (out_steps[e[1]]["start"], e[0]))
    call_sites, current, exit_since_open, opened_in_step = [], None, False, set()
    for _, k, kind, item in events:
        if kind == "exit":
            if current is not None:
                current["handled"] |= set(item)
                exit_since_open = True
            continue
        first_in_step = k not in opened_in_step
        if first_in_step or not exit_since_open or current is None or current["_k"] != k:
            current = {"step": out_steps[k]["n"], "_k": k, "line": item["line"],
                       "tool": item["tool"], "command": item["command"], "handled": set(),
                       "_call": item, "branch_calls": []}
            call_sites.append(current)
            opened_in_step.add(k)
            exit_since_open = False
        else:
            current["branch_calls"].append({"tool": item["tool"], "line": item["line"]})
    for site in call_sites:
        call = site.pop("_call")
        site.pop("_k")
        tool = next(t for t in registry if t["name"] == site["tool"])
        minimal = instantiate(call["command"])[0]
        exits, _ = helper_exits(src, index, tool, split_words(minimal))
        emitted = real_codes(exits)
        site["handled"] = sorted(site["handled"])
        site["emitted"] = emitted
        site["unhandled"] = [c for c in emitted if c != 0 and c not in site["handled"]]
        site["unhandled_sites"] = {str(c): [s["at"] for s in exits.get(str(c), [])
                                            if s["how"] != "argparse"]
                                   for c in site["unhandled"]}
    region_prose_handling(out_steps, call_sites)
    flags = prose_flags(out_steps, registry)
    # templates: what they ask, and how each placeholder is filled
    out_templates = {}
    for tid, tpl in templates.items():
        backing = backing_tools(out_steps, tid, call_sites)
        modules = sorted({module_for(t, registry) for t in backing if module_for(t, registry)})
        extra = set()
        for m in modules:
            if "/wrappers/" in m:
                extra.add("_system/wrapperlib.py")
        vocab = key_vocabulary(src, sorted(set(modules) | extra)) if modules else None
        phs = []
        for ln, line in tpl["body"]:
            for m in re.finditer(r"<[^<>\n]+>", line):
                b = bind_placeholder(m.group(0), line, vocab, m.start())
                b["line"] = ln
                phs.append(b)
        out_templates[tid] = {
            "id": tid, "title": tpl["title"], "line": tpl["line"],
            "source": "%s:%d" % (path, tpl["line"]),
            "ask": ask_kind(tpl["body"]), "accept_tokens": accept_tokens(tpl["body"]),
            "backing_tools": backing, "placeholders": phs,
            "unbound": [p for p in phs if p["binding"] == "unbound"],
            "commands_for_user": [
                {"line": ln, "command": re.sub(r"^\s*(Check progress: )?", "", line).strip()}
                for ln, line in tpl["body"]
                if re.match(r"\s*(Check progress: )?(python3|squeue|sbatch)\b", line)],
        }
    for step in out_steps:
        asking = [t for t in step["templates"] if t in out_templates and out_templates[t]["ask"]]
        step["wait"] = {"kind": out_templates[asking[0]]["ask"] if asking
                        else ("word" if step["waits_word"] else None),
                        "templates": asking,
                        "accept_tokens": sorted({tok for t in asking
                                                 for tok in out_templates[t]["accept_tokens"]})}
        step.pop("waits_word")
    if guard is not None:
        for step in out_steps:
            for call in step["calls"]:
                call["guard"] = guard_row(guard, path, call, assay, substage)
            for action in step["file_actions"]:
                action["guard"] = {s: guard.file(s, action["tool"], action["path"], assay,
                                                 substage) for s in SCENARIOS}
        for entry in flags:
            if entry["variant"]:
                fake = {"command": entry["variant"], "literal": entry["variant"], "comment": None,
                        "kind": "variant", "tool": entry["target_tool"]}
                entry["guard"] = guard_row(guard, path, fake, assay, substage)
    for step in out_steps:
        step.pop("_offsets", None)
        for call in step["calls"]:
            call.pop("_pos", None)
    sections = [{"name": s["name"], "start": s["start"], "end": s["end"]} for s in doc["sections"]]
    return {"path": path, "id": contract_id(path), "assay": assay, "substage": substage,
            "sections": sections, "steps": out_steps, "templates": out_templates,
            "call_sites": call_sites, "prose_flags": flags, "wrapper_invocation": wrapper[0],
            "fenced_non_commands": fenced_other,
            "file_mentions_unclassified": file_unclassified, "findings": findings}


FLAG_RE = re.compile(r"`(--[a-z][a-z0-9-]*)(?:[ =]([^`]*))?`")
NEGATION_RE = re.compile(r"\b(Never|never|not|Do not)\b[^.]*$")
FAILURE_RE = re.compile(r"(?:^|(?<=\. ))If [^.]*\b(fail\w*|refus\w*|absent|missing|error|not met|"
                        r"nothing is resolvable)\b[^.]*\.")


def command_flags(command):
    return {w.strip("[]").split("=")[0] for w in command.split() if w.strip("[]").startswith("--")}


def flag_value_default(tool_name, flag, registry):
    """None for a boolean flag, else a synthetic value for a string flag named bare in prose."""
    tool = next((t for t in registry if t["name"] == tool_name), None)
    if tool is None:
        return "x"
    for key, spec in tool["cli"].items():
        if spec["flag"] == flag:
            if tool["input_schema"]["properties"][key]["type"] == "boolean":
                return None
            if key == "sample-id-pattern":
                return "'<their answer as a regex with named groups sample, read and optionally lane>'"
            return "x"
    return "x"


def prose_flags(out_steps, registry):
    """Backticked `--flag` mentions in step prose, each tied to the call it modifies: the last
    registered call in the step, or for "re-run `sub`" the latest earlier call of that
    subcommand, or else the latest earlier call. A flag a step requires but its literal command
    lacks is `in_command: false`; "Never add `--force`" is `prohibited`; "re-run without
    `--dry-run`" is a removal. Each yields a command variant for the guard."""
    out = []
    for k, step in enumerate(out_steps):
        text = step["text"]
        for m in FLAG_RE.finditer(text):
            flag, value = m.group(1), (m.group(2) or "").strip() or None
            sentence_start = max(text.rfind(". ", 0, m.start()), 0)
            prohibited = bool(NEGATION_RE.search(text[sentence_start:m.start()]))
            removal = text[max(0, m.start() - 8):m.start()].endswith("without ")
            fpos = (line_at(step["_offsets"], m.start()), m.start())
            here = [c for c in step["calls"] if c["tool"]]
            key = lambda c: (c["line"], -1 if c["kind"] == "fenced" else c["_pos"])  # noqa: E731
            before = [c for c in here if key(c) < fpos]
            after = [c for c in here if key(c) >= fpos]
            target = before[-1] if before else (after[0] if after else None)
            target_step = step["n"] if target else None
            if target is None:
                rerun = re.search(r"re-run `(\w+)`", text)
                for prev in reversed(out_steps[:k]):
                    cands = [c for c in prev["calls"] if c["tool"] and
                             (not rerun or c["tool"].endswith("." + rerun.group(1)))]
                    if cands:
                        target, target_step = cands[-1], prev["n"]
                        break
            if target is None:
                continue
            in_command = flag in command_flags(target["command"])
            entry = {"step": step["n"], "line": line_at(step["_offsets"], m.start()),
                     "flag": flag, "value": value, "target_tool": target["tool"],
                     "target_step": target_step, "in_command": in_command,
                     "prohibited": prohibited, "removal": removal, "variant": None}
            if removal and in_command:
                words = target["command"].split()
                entry["variant"] = " ".join(w for w in words if w.strip("[]") != flag)
            elif not in_command and not removal:
                if value is None:
                    value = flag_value_default(target["tool"], flag, registry)
                entry["variant"] = target["command"] + " " + flag + (" " + value if value else "")
            out.append(entry)
    return out


def region_prose_handling(out_steps, call_sites):
    """Sentences after each call, up to the next call site's step, that handle a failure in
    words rather than by exit code ("If approval is absent ... reply T3")."""
    index = {s["n"]: i for i, s in enumerate(out_steps)}
    for j, site in enumerate(call_sites):
        k = index[site["step"]]
        nxt = index[call_sites[j + 1]["step"]] if j + 1 < len(call_sites) else len(out_steps)
        texts = [out_steps[k]["text"]] + [out_steps[i]["text"] for i in range(k + 1, max(nxt, k + 1))]
        found = []
        for t in texts:
            for m in FAILURE_RE.finditer(t):
                sentence = m.group(0).strip()
                if "Exit" not in sentence and "(exit" not in sentence and sentence not in found:
                    found.append(sentence)
        site["prose_handling"] = found[:4]


def module_for(tool_name, registry):
    for tool in registry:
        if tool["name"] == tool_name and not tool.get("filesystem"):
            return tool["argv"][1]
    return None


def backing_tools(steps, tid, call_sites=None):
    """Where template `tid`'s values can come from. Walking back from each step that sends it,
    the nearest step with a data source decides: its call sites (their JSON; in the template's
    own step, every call there), or, if that step has only Reads the agent makes itself, files
    (then nothing binds the placeholders: [])."""
    openers = {(cs["step"], cs["line"]) for cs in (call_sites or [])}
    out = []
    for k, step in enumerate(steps):
        if tid not in step["templates"]:
            continue
        for prev in reversed(steps[:k + 1]):
            calls = [c["tool"] for c in prev["calls"]
                     if c["tool"] and (call_sites is None or (prev["n"], c["line"]) in openers)]
            reads = [a for a in prev["file_actions"] if a["tool"] == "Read"]
            if calls:
                out += calls if prev is step else calls[-1:]
                break
            if reads:
                break
    return list(dict.fromkeys(out))


def guard_row(guard, path, call, assay, substage):
    """The guard's decision on a call: literal and instantiated (minimal/maximal) forms in every
    scenario, the dispatcher spelling, and the scenario the contract is meant to work in."""
    minimal, maximal, missing = instantiate(call["command"])
    row = {"intended": intended_scenario(path, call["tool"]), "missing_placeholders": missing}
    if missing:
        row["status"] = "uninstantiable"
        return row
    forms = {"minimal": minimal}
    if maximal != minimal:
        forms["maximal"] = maximal
    if call["comment"]:
        forms["literal_with_comment"] = instantiate(call["literal"])[0]
    if call["kind"] == "prose":
        forms = {k: add_required(v, call["tool"], guard) for k, v in forms.items()}
    row["forms"] = {}
    for name, command in forms.items():
        row["forms"][name] = {"command": guard.scrub(guard.fill("public", command, assay,
                                                                 substage)).replace(
                                  guard.roots["public"], "<root>"),
                              "decisions": {s: guard.bash(s, command, assay, substage)
                                            for s in SCENARIOS}}
    disp = guard.dispatcher_form("public", minimal if call["kind"] != "prose"
                                 else forms["minimal"], assay, substage)
    if disp:
        row["dispatcher"] = {"decisions": {s: guard.bash(s, dispatcher_for(guard, s, call,
                                                                           forms["minimal"],
                                                                           assay, substage),
                                                         assay, substage)
                                           for s in SCENARIOS}}
    intended = row["intended"]
    row["allowed_where_intended"] = row["forms"]["minimal"]["decisions"][intended]["allow"]
    row["status"] = "checked"
    return row


def dispatcher_for(guard, scenario, call, command, assay, substage):
    form = guard.dispatcher_form(scenario, command, assay, substage)
    return form or command


def add_required(command, tool_name, guard):
    """A prose call names only some flags; add the registry's required ones it leaves implicit."""
    policy = sys.modules.get("tools.policy")
    tool = policy.named(tool_name)
    for key in tool["input_schema"].get("required", []):
        flag = tool["cli"][key]["flag"]
        if flag and flag not in command.split():
            command += " %s %s" % (flag, REQUIRED_VALUES.get(key, "x"))
    return command


# --- everything ------------------------------------------------------------------------------

def extract(src, with_guard=True):
    registry = load_registry(src)
    index = HelperIndex(src)
    helpers = {}
    for tool in registry:
        if tool.get("filesystem"):
            continue
        exits, problem = helper_exits(src, index, tool)
        helpers[tool["name"]] = {"module": "gars/" + tool["argv"][1],
                                 "subcommand": tool["argv"][2] if len(tool["argv"]) >= 3
                                 and not tool["argv"][2].startswith("-") else None,
                                 "exits": exits, "problem": problem}
    tmp = tempfile.mkdtemp(prefix="stepmap-")
    guard = None
    try:
        guard = GuardHarness(src, tmp) if with_guard else None
        contracts = [dict(extract_text(p, src.text(p), src, registry, index, guard, helpers),
                          blob=src.blob(p)) for p in contract_paths(src)]
    finally:
        if guard is not None:
            guard.close()
        shutil.rmtree(tmp, ignore_errors=True)
    return {"schema": SCHEMA, "sha": src.sha, "contracts": contracts, "helpers": helpers,
            "summary": summarize(contracts, helpers, registry)}


def summarize(contracts, helpers, registry):
    steps = sum(len(c["steps"]) for c in contracts)
    calls = [(c, s, call) for c in contracts for s in c["steps"] for call in s["calls"]]
    uninst = [x for x in calls if x[2]["tool"] and x[2].get("guard", {}).get("status")
              == "uninstantiable"]
    acc = {"seen": len(calls), "mapped": sum(1 for x in calls if x[2]["tool"]) - len(uninst),
           "unregistered": sum(1 for x in calls if not x[2]["tool"]), "uninstantiable": len(uninst)}
    unreg_process = sorted({x[2]["executable"] for x in calls if not x[2]["tool"]})
    phs = [p for c in contracts for t in c["templates"].values() for p in t["placeholders"]]
    by_binding = {}
    for p in phs:
        by_binding[p["binding"]] = by_binding.get(p["binding"], 0) + 1
    sites = [cs for c in contracts for cs in c["call_sites"]]
    guard_refused = []
    for c, s, call in calls:
        g = call.get("guard")
        if g and g.get("status") == "checked" and not g["allowed_where_intended"]:
            guard_refused.append({"contract": c["id"], "step": s["n"], "tool": call["tool"],
                                  "command": call["command"],
                                  "scenario": g["intended"],
                                  "reason": g["forms"]["minimal"]["decisions"][g["intended"]]["reason"][:300]})
    file_seen = sum(len(s["file_actions"]) for c in contracts for s in c["steps"])
    return {
        "contracts": len(contracts),
        "steps": steps,
        "steps_by_contract": {c["id"]: len(c["steps"]) for c in contracts},
        "templates": sum(len(c["templates"]) for c in contracts),
        "command_accounting": acc,
        "unregistered_in_process": unreg_process,
        "unregistered_calls": [{"contract": c["id"], "step": s["n"], "line": call["line"],
                                "executable": call["executable"], "kind": call["kind"]}
                               for c, s, call in calls if not call["tool"]],
        "placeholder_accounting": {"seen": len(phs), "by_binding": dict(sorted(by_binding.items()))},
        "accept_tokens": sorted({tok for c in contracts for t in c["templates"].values()
                                 for tok in t["accept_tokens"]}),
        "exits": {"call_sites": len(sites),
                  "emitted": sum(len(cs["emitted"]) for cs in sites),
                  "handled": sum(len(cs["handled"]) for cs in sites),
                  "unhandled": sum(len(cs["unhandled"]) for cs in sites),
                  "unhandled_list": [{"contract": c["id"], "step": cs["step"], "tool": cs["tool"],
                                      "codes": cs["unhandled"]}
                                     for c in contracts for cs in c["call_sites"] if cs["unhandled"]]},
        "guard": {"calls_checked": sum(1 for x in calls if x[2].get("guard", {}).get("status")
                                       == "checked"),
                  "refused_where_intended": guard_refused,
                  "file_actions_checked": file_seen},
        "file_mentions_unclassified": sum(len(c["file_mentions_unclassified"]) for c in contracts),
        "empty_findings": [f for c in contracts for f in c["findings"]],
        "helpers": len(helpers),
    }


def write(result, out):
    os.makedirs(out, exist_ok=True)
    for c in result["contracts"]:
        with open(os.path.join(out, c["id"] + ".json"), "w") as fh:
            json.dump(dict(c, sha=result["sha"], schema=result["schema"]), fh, indent=1,
                      sort_keys=True, ensure_ascii=False)
            fh.write("\n")
    with open(os.path.join(out, "_helpers.json"), "w") as fh:
        json.dump({"sha": result["sha"], "helpers": result["helpers"]}, fh, indent=1,
                  sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    with open(os.path.join(out, "_summary.json"), "w") as fh:
        json.dump(dict(result["summary"], sha=result["sha"], schema=result["schema"]), fh,
                  indent=1, sort_keys=True, ensure_ascii=False)
        fh.write("\n")


def main(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo", default=os.path.dirname(os.path.dirname(here)))
    ap.add_argument("--sha", default=PIN)
    ap.add_argument("--out", default=os.path.join(here, "facts"))
    ap.add_argument("--no-guard", action="store_true")
    args = ap.parse_args(argv)
    src = Source(args.repo, args.sha)
    result = extract(src, with_guard=not args.no_guard)
    write(result, args.out)
    s = result["summary"]
    print(json.dumps({k: s[k] for k in ("contracts", "steps", "templates", "command_accounting",
                                        "unregistered_in_process", "exits")}
                     | {"guard_refused_where_intended": len(s["guard"]["refused_where_intended"])},
                     indent=1, default=str)[:4000])
    if s["empty_findings"]:
        print("FINDING: contracts with no Process steps: %s" % s["empty_findings"], file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
