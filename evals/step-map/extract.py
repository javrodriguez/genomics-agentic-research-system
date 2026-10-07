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

Two layers are not plain static facts, and are kept apart so they can be checked:
- reachability rulings (RULINGS): a site a reader proved unreachable from given callers, applied
  only while every cited line still reads as cited, and listed per call site under `ruled_out`;
- template-label matching: a count's label matched to a helper key by its words, a screen that
  errs toward "unbound" (look here), never a proof.
What it does not model is listed in LIMITS and in the summary's `limits`.
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

NONZERO = -1          # "Exit non-zero": every non-zero code the call itself emits
EXIT_RE = re.compile(r"(?:\bExit|\(exit)\s+(non-zero|nonzero|\d)((?:\s*(?:,|or|and|/)\s*\d)*)")


def exit_codes(text):
    """Exit codes a piece of contract prose branches on. Capitalised `Exit N` anywhere, or a
    parenthesised `(exit N)`; a lowercase "must exit non-zero" about a script is not a branch."""
    codes = set()
    for m in EXIT_RE.finditer(text):
        if m.group(1).startswith("non"):
            codes.add(NONZERO)
        else:
            codes.add(int(m.group(1)))
            codes |= {int(d) for d in re.findall(r"\d", m.group(2))}
    return sorted(codes)


OTHER_ACTOR_RE = re.compile(r"\b(they report|the user|their own terminal)\b")


def sentence_bounds(text, pos):
    """The sentence around `pos`: a full stop ends a sentence only before a space and a capital,
    a backtick, a digit or a bold marker, so dots inside file names do not cut it."""
    ends = [m.end() for m in re.finditer(r"[.!?;](?=\s+(?:[A-Z0-9`*]|$))", text)]
    start = max([e for e in ends if e <= pos], default=0)
    end = min([e for e in ends if e > pos], default=len(text))
    return start, end


def exit_mentions(text):
    """(offset, codes, actor) for each exit-code mention. A mention in a sentence about the
    user's own command ("If they report that it refused (exit 2)") is the user's, not a branch
    on the agent's call."""
    out = []
    for m in EXIT_RE.finditer(text):
        s, _ = sentence_bounds(text, m.start())
        actor = "user" if OTHER_ACTOR_RE.search(text[s:m.start()]) else "agent"
        out.append((m.start(), exit_codes(m.group(0)), actor))
    return out


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



# --- stage-wide exit tables ------------------------------------------------------------------------
# Stages 00 and 01 carry a Definitions table, "The script's exit codes. These, and not your reading
# of its output, determine the branch", mapping each code of the stage's own script to a reply. That
# table is handling for every call of that script in the stage. A row whose meaning says the JSON's
# `template` field names the reply handles a code only at emit sites that set that field.

def parse_exit_table(doc):
    """The Definitions table headed `| Code | Meaning | Reply |`, with the script it governs (the
    first `_system/...py` named in the Purpose section). None when the contract has none."""
    sec = section(doc, "Definitions")
    if sec is None:
        return None
    rows, head = {}, None
    for i in range(sec["start"] + 1, sec["end"] + 1):
        if i in doc["fenced"]:
            continue
        cells = [c.strip() for c in doc["lines"][i - 1].strip().strip("|").split("|")]
        if head is None:
            if cells[:3] == ["Code", "Meaning", "Reply"]:
                head = i
            continue
        if not doc["lines"][i - 1].strip().startswith("|"):
            break
        if len(cells) >= 3 and re.fullmatch(r"\d", cells[0]):
            rows[cells[0]] = {"meaning": cells[1], "reply": cells[2], "line": i,
                              "needs_template_field": "template" in cells[1]}
    if head is None:
        return None
    purpose = section(doc, "Purpose")
    script = None
    if purpose:
        text = "\n".join(doc["lines"][purpose["start"]:purpose["end"]])
        m = re.search(r"`(_system/[A-Za-z0-9_./-]+\.py)`", text)
        script = m.group(1) if m else None
    return {"line": head, "script": script, "codes": rows}


def exit_rules_without_reply(doc):
    """Sentences that name the exit codes and say to branch on them, but map no reply."""
    sec = section(doc, "Definitions")
    out = []
    if sec is None:
        return out
    text, offsets = prose(doc, sec["start"] + 1, sec["end"])
    for m in re.finditer(r"Exit codes are the stage-helper standard[^.]*\.", text):
        out.append({"line": line_at(offsets, m.start()), "text": m.group(0)[:160]})
    return out


def sets_template_field(src, at):
    """Whether the statements leading to the emit site at `path:line`, in its own block, set the
    result's `template` field."""
    path, line = at.rsplit(":", 1)
    lines = src.text(path).split("\n")
    line = int(line)
    indent = len(lines[line - 1]) - len(lines[line - 1].lstrip())
    for k in range(line - 2, -1, -1):
        text = lines[k]
        if not text.strip():
            continue
        here = len(text) - len(text.lstrip())
        if here < indent:
            return False
        if here == indent and re.search(r"""\[["']template["']\]\s*=""", text):
            return True
    return False


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


RERUN_RE = re.compile(r"\bre-run `(\w+)`(?: with `(--[^`]+)`)?")
RERUN_WITHOUT_RE = re.compile(r"\bre-run without `(--[a-z][a-z0-9-]*)`")


def rerun_calls(text, offsets, calls_here, earlier_steps, registry):
    """'re-run `inspect` with `--flag ...`': a call of the latest earlier command of that
    subcommand, with the flag added."""
    out = []
    for m in RERUN_RE.finditer(text):
        sub, flag = m.group(1), m.group(2)
        previous = [c for s in earlier_steps for c in s["calls"]] + list(calls_here)
        base = [c for c in previous if c["tool"] and c["tool"].endswith("." + sub)]
        if not base:
            continue
        command = base[-1]["command"] + (" " + flag if flag else "")
        out.append(make_call(command, line_at(offsets, m.start()), "prose-rerun", registry,
                             m.start()))
    for m in RERUN_WITHOUT_RE.finditer(text):
        flag = m.group(1)
        previous = [c for s in earlier_steps for c in s["calls"]] + list(calls_here)
        base = [c for c in previous if c["tool"] and flag in c["command"].split()]
        if not base:
            continue
        command = " ".join(w for w in base[-1]["command"].split() if w != flag)
        out.append(make_call(command, line_at(offsets, m.start()), "prose-rerun", registry,
                             m.start()))
    return out


PATH_SPAN_RE = re.compile(r"/|\.(md|yaml|csv|json|tsv|py|sh|jsonl|h5ad)\b|^(STATUS|HISTORY\.md|PLAN\.md)$")


def span_accounting(doc, step, text, calls):
    """Every backticked span in the step's prose, each in one class, against an independent count
    of backticks in the step's raw lines; a mismatch means a span or a line was dropped."""
    raw = sum(doc["lines"][i - 1].count("`") for i in range(step["start"], step["end"] + 1)
              if i not in doc["fenced"])
    classes = {}
    for m in re.finditer(r"`([^`]+)`", text):
        inner = m.group(1).strip()
        words = inner.split()
        before = text[max(0, m.start() - 10):m.start()]
        if words and words[0] in EXECUTABLES:
            cls = "command"
        elif inner.startswith("--"):
            cls = "flag"
        elif len(words) == 1 and re.search(r"\b(?:[Rr]un|re-run|[Rr]un the wrapper's)\s$", before):
            cls = "subcommand"
        elif PATH_SPAN_RE.search(inner):
            cls = "path"
        elif re.fullmatch(r"T\d+[a-z]?", inner):
            cls = "template"
        else:
            cls = "value"
        classes[cls] = classes.get(cls, 0) + 1
    seen = sum(classes.values())
    # An independent recount: every mention of a helper script in the step's raw lines, fenced or
    # not, against the calls found in fences and backticks. A helper named outside both is a
    # command the extractor would drop.
    raw_text = " ".join(doc["lines"][i - 1] for i in range(step["start"], step["end"] + 1))
    helper_mentions = len(re.findall(r"python3\s+\S*_system/\S+\.py\b", raw_text))
    helper_calls = sum(1 for c in calls if c["kind"] in ("fenced", "inline")
                       and re.search(r"_system/\S+\.py\b", c["command"]))
    return {"raw_backtick_pairs": raw // 2, "seen": seen, "by_class": dict(sorted(classes.items())),
            "helper_mentions": helper_mentions, "helper_calls": helper_calls,
            "consistent": raw % 2 == 0 and raw // 2 == seen and helper_mentions == helper_calls}


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
        self._skipkeys = None

    @property
    def skipkeys(self):
        """True if any file under gars/ names json's skipkeys, which would let a tuple-keyed
        dict be emitted with those keys dropped rather than refused."""
        if self._skipkeys is None:
            out = subprocess.run(["git", "-C", self.src.repo, "grep", "-l", "skipkeys",
                                  self.src.sha, "--", "gars"], stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, universal_newlines=True)
            if out.returncode not in (0, 1):
                raise RuntimeError("git grep failed: %s" % out.stderr.strip())
            self._skipkeys = bool(out.stdout.strip())
        return self._skipkeys

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
        if isinstance(test, ast.BoolOp):
            values = [self.truth(v) for v in test.values]
            if isinstance(test.op, ast.And):
                if any(v is False for v in values):
                    return False
                return True if all(v is True for v in values) else UNKNOWN
            if any(v is True for v in values):
                return True
            return False if all(v is False for v in values) else UNKNOWN
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



# --- reachability rulings ------------------------------------------------------------------------
# A static walk cannot see facts carried in data (a file written earlier, a dict's keys). A ruling
# records one such fact a reader proved from the source: the site it rules out, the tools it
# applies to, and the exact lines that prove it. Every run re-reads those lines at the pin; if any
# line has changed the ruling is void, is not applied, and is reported. Ruled-out codes stay in the
# helper's static exits and are listed per call site under `ruled_out`, never silently dropped.

NFCORE = ("atacseq", "chipseq", "cutandrun", "methylseq", "rnaseq", "scrnaseq", "spatialvi")
NFCORE_LINES = {"atacseq": (189, 206), "chipseq": (188, 205), "cutandrun": (190, 204),
                "methylseq": (118, 132), "rnaseq": (152, 169), "scrnaseq": (260, 277),
                "spatialvi": (225, 242)}
RULINGS = [{
    "id": "prepare-stage01-v1",
    "site": "gars/_system/wrapperlib.py:925",
    "tools": ["nfcore_%s_wrapper.prepare" % a for a in NFCORE],
    "why": ("write_reproducibility raises exit 2 only when key_formula is downstream-v2; an nf-core "
            "wrapper's prepare writes params.yaml first (an atomic write that renames the file into "
            "place before returning) and passes samplesheet and config, so key_formula is "
            "stage01-v1. Every cited line must read exactly as cited, indentation included"),
    "evidence": [
        ('gars/_system/wrapperlib.py', 797,
         'def write_params_yaml(substage, assay, params):'),
        ('gars/_system/wrapperlib.py', 798,
         '    with ws.atomic_open(substage / "params.yaml") as fh:'),
        ('gars/_system/wrapperlib.py', 917,
         "    manifest['key_formula'] = ('stage01-v1' if (substage / 'params.yaml').is_file()"),
        ('gars/_system/wrapperlib.py', 918,
         "                               and 'samplesheet' in inputs and 'config' in inputs else 'downstream-v2')"),
        ('gars/_system/wrapperlib.py', 919,
         "    if manifest['key_formula'] == 'downstream-v2':"),
        ('gars/_system/workspace.py', 111,
         'def atomic_open(path, newline="", mode=None):'),
        ('gars/_system/workspace.py', 123,
         '    tmp = path.with_name(path.name + ".tmp")'),
        ('gars/_system/workspace.py', 130,
         '        os.replace(str(tmp), str(path))'),
        ('gars/_system/wrappers/nfcore-atacseq-wrapper/nfcore_atacseq_wrapper.py', 189,
         '    wl.write_params_yaml(substage, ASSAY, params)'),
        ('gars/_system/wrappers/nfcore-atacseq-wrapper/nfcore_atacseq_wrapper.py', 206,
         '    wl.write_reproducibility(substage, ASSAY, paths["checkout"],'),
        ('gars/_system/wrappers/nfcore-atacseq-wrapper/nfcore_atacseq_wrapper.py', 207,
         '                             {"samplesheet": paths["samplesheet"], "config": paths["config"]},'),
        ('gars/_system/wrappers/nfcore-chipseq-wrapper/nfcore_chipseq_wrapper.py', 188,
         '    wl.write_params_yaml(substage, ASSAY, params)'),
        ('gars/_system/wrappers/nfcore-chipseq-wrapper/nfcore_chipseq_wrapper.py', 205,
         '    wl.write_reproducibility(substage, ASSAY, paths["checkout"],'),
        ('gars/_system/wrappers/nfcore-chipseq-wrapper/nfcore_chipseq_wrapper.py', 206,
         '                             {"samplesheet": paths["samplesheet"], "config": paths["config"]},'),
        ('gars/_system/wrappers/nfcore-cutandrun-wrapper/nfcore_cutandrun_wrapper.py', 190,
         '    wl.write_params_yaml(substage, ASSAY, params)'),
        ('gars/_system/wrappers/nfcore-cutandrun-wrapper/nfcore_cutandrun_wrapper.py', 204,
         '    wl.write_reproducibility(substage, ASSAY, paths["checkout"],'),
        ('gars/_system/wrappers/nfcore-cutandrun-wrapper/nfcore_cutandrun_wrapper.py', 205,
         '                             {"samplesheet": paths["samplesheet"], "config": paths["config"]},'),
        ('gars/_system/wrappers/nfcore-methylseq-wrapper/nfcore_methylseq_wrapper.py', 118,
         '    wl.write_params_yaml(substage, ASSAY, params)'),
        ('gars/_system/wrappers/nfcore-methylseq-wrapper/nfcore_methylseq_wrapper.py', 132,
         '    wl.write_reproducibility(substage, ASSAY, paths["checkout"],'),
        ('gars/_system/wrappers/nfcore-methylseq-wrapper/nfcore_methylseq_wrapper.py', 133,
         '                             {"samplesheet": paths["samplesheet"], "config": paths["config"]},'),
        ('gars/_system/wrappers/nfcore-rnaseq-wrapper/nfcore_rnaseq_wrapper.py', 152,
         '    wl.write_params_yaml(substage, ASSAY, params)'),
        ('gars/_system/wrappers/nfcore-rnaseq-wrapper/nfcore_rnaseq_wrapper.py', 169,
         '    wl.write_reproducibility(substage, ASSAY, paths["checkout"],'),
        ('gars/_system/wrappers/nfcore-rnaseq-wrapper/nfcore_rnaseq_wrapper.py', 170,
         '                             {"samplesheet": paths["samplesheet"], "config": paths["config"]},'),
        ('gars/_system/wrappers/nfcore-scrnaseq-wrapper/nfcore_scrnaseq_wrapper.py', 260,
         '    wl.write_params_yaml(substage, ASSAY, params)'),
        ('gars/_system/wrappers/nfcore-scrnaseq-wrapper/nfcore_scrnaseq_wrapper.py', 277,
         '    wl.write_reproducibility(substage, ASSAY, paths["checkout"],'),
        ('gars/_system/wrappers/nfcore-scrnaseq-wrapper/nfcore_scrnaseq_wrapper.py', 278,
         '                             {"samplesheet": paths["samplesheet"], "config": paths["config"]},'),
        ('gars/_system/wrappers/nfcore-spatialvi-wrapper/nfcore_spatialvi_wrapper.py', 225,
         '    wl.write_params_yaml(substage, ASSAY, params)'),
        ('gars/_system/wrappers/nfcore-spatialvi-wrapper/nfcore_spatialvi_wrapper.py', 242,
         '    wl.write_reproducibility(substage, ASSAY, paths["checkout"],'),
        ('gars/_system/wrappers/nfcore-spatialvi-wrapper/nfcore_spatialvi_wrapper.py', 243,
         '                             {"samplesheet": paths["samplesheet"], "config": paths["config"]},'),
    ],
}]


def check_rulings(src):
    """(rulings that hold, findings for rulings whose evidence no longer reads as cited)."""
    holding, void = [], []
    for ruling in RULINGS:
        broken = evidence_holds(src, ruling["evidence"])
        if broken:
            void.append({"kind": "ruling_void", "ruling": ruling["id"], "lines": broken})
        else:
            holding.append(ruling)
    return holding, void


def apply_rulings(exits, tool, rulings):
    """(exits without the sites a holding ruling rules out for this tool, {code: [site, ruling]})."""
    out, ruled = {}, {}
    for code, sites in exits.items():
        keep = []
        for s in sites:
            hit = [r["id"] for r in rulings if tool in r["tools"] and s["at"] == r["site"]]
            if hit:
                ruled.setdefault(code, []).append({"at": s["at"], "ruling": hit[0]})
            else:
                keep.append(s)
        if keep:
            out[code] = keep
    return out, ruled


# --- the keys that reach a subcommand's emitted result ----------------------------------------------
# Data flow, not vocabulary: start from what is passed to emit (and what a helper that emits its
# parameter is given), and follow it back through assignments, updates, loops, comprehensions,
# returned values and functions that write into it. Only keys written into that flow count.
# A key computed at run time (`d[key] = v`) is unknown to a static walk; KEY_DOMAINS records,
# with whole-line evidence re-checked on every run, where such keys come from.

KEY_DOMAINS = [{
    "id": "stage01-config-columns",
    "site": "gars/_system/stage01_samplesheet.py:779",
    "why": ("config_values[key] takes its keys from config_columns(fmt), the `config:` sources of "
            "the assay's FORMATS entry, and joins the counts at line 824"),
    "evidence": [
        ("gars/_system/stage01_samplesheet.py", 245,
         '    return [src.split(":", 1)[1] for _, src in fmt if src.startswith("config:")]'),
        ("gars/_system/stage01_samplesheet.py", 770, "    for key in config_columns(fmt):"),
        ("gars/_system/stage01_samplesheet.py", 779, "            config_values[key] = value"),
        ("gars/_system/stage01_samplesheet.py", 824, '    out["counts"].update(config_values)'),
    ],
    "keys_from": ("gars/_system/stage01_samplesheet.py", "FORMATS", "config:"),
}]


# A run-time key that names an item (an assay, a requested artifact type), never a field. Each
# entry is a reader's ruling, bound to whole lines re-checked on every run; while its evidence
# holds, the sites are explained and a missing key there stays "unbound". A broken entry leaves
# its sites unexplained (so absence reads "unknown") and is listed as void in the summary.
ITEM_KEYS = [{
    "id": "stage00-per-assay",
    "sites": ["gars/_system/stage00_register.py:705"],
    "why": ("per_assay is keyed by the assay ids finalize loops over; its keys never reach the "
            "result, only each assay's row, under the named field `assays`"),
    "evidence": [
        ("gars/_system/stage00_register.py", 654, "    per_assay = {}"),
        ("gars/_system/stage00_register.py", 656, "    for aid in assays:"),
        ("gars/_system/stage00_register.py", 705,
         '        per_assay[aid] = {"display": assay_map.get(aid, aid), "files": len(names),'),
        ("gars/_system/stage00_register.py", 708,
         '        result["assays"][aid] = {k: v for k, v in per_assay[aid].items()}'),
    ],
}, {
    "id": "resolve-requested-types",
    "sites": ["gars/_system/resolve_artifact.py:156", "gars/_system/resolve_artifact.py:158"],
    "why": ("resolved and missing are keyed by the artifact types the command asked for "
            "(--type or --consumes), emitted under the named fields `resolved` and `missing`"),
    "evidence": [
        ("gars/_system/resolve_artifact.py", 151,
         "    wanted = args.consumes if args.consumes is not None else [args.type]"),
        ("gars/_system/resolve_artifact.py", 152, "    resolved, missing = {}, {}"),
        ("gars/_system/resolve_artifact.py", 153, "    for w in wanted:"),
        ("gars/_system/resolve_artifact.py", 156, "            resolved[w] = hit"),
        ("gars/_system/resolve_artifact.py", 158, "            missing[w] = why"),
        ("gars/_system/resolve_artifact.py", 160, '    result["resolved"] = resolved'),
        ("gars/_system/resolve_artifact.py", 161, '    result["missing"] = missing'),
    ],
}]


def check_key_rulings(src):
    """Findings for key domains and item-key rulings whose evidence no longer reads as cited."""
    void = []
    for kind, entries in (("key_domain_void", KEY_DOMAINS), ("item_keys_void", ITEM_KEYS)):
        for e in entries:
            broken = evidence_holds(src, e["evidence"])
            if broken:
                void.append({"kind": kind, "ruling": e["id"], "lines": broken})
    return void


def key_domain_keys(src, domain):
    """The keys a key domain admits: every string constant inside the named module constant that
    starts with the prefix, with the prefix removed."""
    path, name, prefix = domain["keys_from"]
    tree = ast.parse(src.text(path))
    out = set()
    for top in tree.body:
        if isinstance(top, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name
                                               for t in top.targets):
            for node in ast.walk(top.value):
                if isinstance(node, ast.Constant) and isinstance(node.value, str) and \
                        node.value.startswith(prefix):
                    out.add(node.value[len(prefix):])
    return out


def evidence_holds(src, evidence):
    """The cited lines that no longer read exactly as cited (whole line, indentation included)."""
    broken = []
    for path, line, expected in evidence:
        lines = src.text(path).split("\n")
        if len(lines) < line or lines[line - 1].rstrip() != expected.rstrip():
            broken.append("%s:%d" % (path, line))
    return broken


def subscript_chain(node):
    """(base name, [constant string slices], dynamic) for x["a"]["b"][k]."""
    slices, dynamic = [], False
    while isinstance(node, ast.Subscript):
        sl = node.slice
        if isinstance(sl, ast.Constant) and isinstance(sl.value, str):
            slices.insert(0, sl.value)
        else:
            dynamic = True
        node = node.value
    return (node.id if isinstance(node, ast.Name) else None), slices, dynamic


def pruned_nodes(body, flags):
    """Every node of a body, except the branches of a top-level `if` the command's flags decide
    the other way."""
    out = []
    for stmt in body:
        if flags is not None and isinstance(stmt, ast.If):
            truth = flags.truth(stmt.test)
            out += list(ast.walk(stmt.test))
            if truth is not False:
                out += pruned_nodes(stmt.body, flags)
            if truth is not True:
                out += pruned_nodes(stmt.orelse, flags)
            continue
        out += list(ast.walk(stmt))
    return out


class Flow:
    def __init__(self, src, index, flags=None):
        self.src, self.index, self.flags = src, index, flags
        self.keys, self.dynamic, self.memo = set(), [], {}
        self.shapes = {}          # key -> set of value shapes seen where it is written
        self._nodes = []          # the current function's nodes, for one-level name lookups

    def add_key(self, key, value=None, shape=None):
        self.keys.add(key)
        s = shape if shape is not None else self.shape(value)
        self.shapes.setdefault(key, set()).add(s)

    def shape(self, node, depth=0):
        """dict, list, number, text, bool or unknown: what a written value looks like."""
        if node is None:
            return "unknown"
        if isinstance(node, (ast.Dict, ast.DictComp)):
            return "dict"
        if isinstance(node, (ast.List, ast.ListComp, ast.Tuple, ast.Set, ast.SetComp,
                             ast.GeneratorExp)):
            return "list"
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool):
                return "bool"
            if isinstance(node.value, (int, float)):
                return "number"
            if isinstance(node.value, str):
                return "text"
            return "unknown"
        if isinstance(node, ast.BinOp):
            return "number"
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) in (
                "len", "int", "float", "sum", "round", "max", "min", "abs"):
            return "number"
        if isinstance(node, (ast.BoolOp, ast.IfExp)):
            parts = node.values if isinstance(node, ast.BoolOp) else [node.body, node.orelse]
            known = {self.shape(p, depth) for p in parts} - {"unknown"}
            return known.pop() if len(known) == 1 else "unknown"
        if isinstance(node, ast.Name) and depth < 2:
            found = {self.shape(n.value, depth + 1) for n in self._nodes
                     if isinstance(n, ast.Assign) and any(isinstance(tg, ast.Name) and tg.id == node.id
                                                          for tg in n.targets)}
            found -= {"unknown"}
            return found.pop() if len(found) == 1 else "unknown"
        return "unknown"

    def resolve_dynamic(self, slice_node, lineno):
        """Keys a run-time subscript takes when its variable is bound by the innermost loop
        around the write, and that loop runs over literal strings (`for key in ("a", "b")`, or
        a name built from literals by assignment, `+=` and append; a tuple target takes its
        position in literal tuples). A variable re-bound inside the loop before the write, or
        bound by no enclosing loop, is not resolved."""
        if not isinstance(slice_node, ast.Name):
            return None
        name = slice_node.id
        loops = []
        for n in self._nodes:
            if isinstance(n, ast.For) and n.lineno <= lineno <= (n.end_lineno or n.lineno):
                if isinstance(n.target, ast.Name) and n.target.id == name:
                    loops.append((n.lineno, n, None))
                elif isinstance(n.target, ast.Tuple):
                    pos = [i for i, e in enumerate(n.target.elts)
                           if isinstance(e, ast.Name) and e.id == name]
                    if pos:
                        loops.append((n.lineno, n, pos[0]))
        if not loops:
            return None
        _, loop, pos = max(loops, key=lambda x: x[0])
        for n in self._nodes:
            if isinstance(n, (ast.Assign, ast.AugAssign, ast.AnnAssign)) and \
                    loop.lineno < n.lineno <= lineno:
                targets = n.targets if isinstance(n, ast.Assign) else [n.target]
                if any(isinstance(x, ast.Name) and x.id == name and isinstance(x.ctx, ast.Store)
                       for tg in targets for x in ast.walk(tg)):
                    return None
            elif isinstance(n, ast.For) and n is not loop and loop.lineno < n.lineno <= lineno \
                    and any(isinstance(x, ast.Name) and x.id == name for x in ast.walk(n.target)):
                return None
        return self.literal_strings(loop.iter, pos)

    def literal_strings(self, node, pos=None):
        def one(e):
            if pos is not None:
                if not isinstance(e, ast.Tuple) or len(e.elts) <= pos:
                    return None
                e = e.elts[pos]
            return e.value if isinstance(e, ast.Constant) and isinstance(e.value, str) else None
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            vals = [one(e) for e in node.elts]
            return set(vals) if vals and None not in vals else None
        if isinstance(node, ast.Name):
            base = None
            for n in self._nodes:
                if isinstance(n, ast.Assign) and any(isinstance(tg, ast.Name) and tg.id == node.id
                                                     for tg in n.targets):
                    if base is not None:
                        return None      # assigned twice: which value reaches the loop is open
                    base = self.literal_strings(n.value, pos)
                    if base is None:
                        return None
            if base is None:
                return None
            for n in self._nodes:
                if isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name) and \
                        n.target.id == node.id:
                    more = self.literal_strings(n.value, pos)
                    if more is None:
                        return None
                    base |= more
                elif isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and \
                        isinstance(n.func.value, ast.Name) and n.func.value.id == node.id and \
                        n.func.attr in ("append", "extend", "insert", "update", "add"):
                    if n.func.attr == "append" and n.args and one(n.args[0]) is not None:
                        base.add(one(n.args[0]))
                    else:
                        return None
            return base
        return None

    def module_dict(self, mod, name):
        for top in mod.tree.body:
            if isinstance(top, ast.Assign) and isinstance(top.value, ast.Dict) and \
                    any(isinstance(t, ast.Name) and t.id == name for t in top.targets):
                return top.value
        return None

    def walk(self, mod, name, args, body, tracked, returned, top=False, positions=None):
        """Follow the flow through one function body; returns the indexes of its parameters
        whose content flows (so the caller can follow its own arguments). `positions` limits a
        returned tuple to the elements the caller keeps."""
        key = (mod.path, name, len(body), frozenset(tracked), returned, top,
               None if positions is None else frozenset(positions))
        if key in self.memo:
            return self.memo[key]
        self.memo[key] = set()
        tracked = set(tracked)
        nodes = pruned_nodes(body, self.flags if top else None)
        saved_nodes, self._nodes = self._nodes, nodes
        params = [a.arg for a in args.args] if args else []
        while True:
            before = (len(tracked), len(self.keys))
            for n in nodes:
                if isinstance(n, ast.Call) and is_emit(self.index, mod, n) and n.args:
                    self.expr(mod, n.args[0], tracked)
                elif isinstance(n, ast.Return) and returned and n.value is not None:
                    if positions is not None and isinstance(n.value, ast.Tuple):
                        for i in sorted(positions):
                            if i < len(n.value.elts):
                                self.expr(mod, n.value.elts[i], tracked)
                    else:
                        self.expr(mod, n.value, tracked)
                elif isinstance(n, ast.Assign):
                    for tgt in n.targets:
                        if isinstance(tgt, (ast.Tuple, ast.List)):
                            self.tuple_assign(mod, tgt, n.value, tracked)
                        else:
                            self.assign(mod, tgt, n.value, tracked, n.lineno)
                elif isinstance(n, ast.AugAssign):
                    self.assign(mod, n.target, n.value, tracked, n.lineno)
                elif isinstance(n, ast.For):
                    names = {x.id for x in ast.walk(n.target) if isinstance(x, ast.Name)}
                    if names & tracked:
                        self.expr(mod, n.iter, tracked)
                elif isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
                    base, slices, _ = subscript_chain(n.func.value)
                    if base in tracked:
                        if n.func.attr == "update":
                            for s in slices:
                                self.add_key(s, shape="dict")
                            for a in n.args:
                                self.expr(mod, a, tracked)
                            for kw in n.keywords:
                                if kw.arg:
                                    self.add_key(kw.arg, kw.value)
                        elif n.func.attr == "setdefault" and n.args and \
                                isinstance(n.args[0], ast.Constant):
                            for s in slices:
                                self.add_key(s, shape="dict")
                            self.add_key(n.args[0].value, n.args[1] if len(n.args) > 1 else None)
                        elif n.func.attr in ("append", "extend", "insert"):
                            for s in slices:
                                self.add_key(s, shape="list")
                            for a in n.args:
                                self.expr(mod, a, tracked)
            if (len(tracked), len(self.keys)) == before:
                break
        # functions that write into a tracked name, and every helper that emits on its own
        for n in nodes:
            if not isinstance(n, ast.Call):
                continue
            target = self.index.function(mod, n.func)
            if target is None or target[1].name == "emit":
                continue
            names = [p.arg for p in target[1].args.args]
            inner = {names[i] for i, a in enumerate(n.args)
                     if i < len(names) and isinstance(a, ast.Name) and a.id in tracked}
            self.walk(target[0], target[1].name, target[1].args, target[1].body, inner, False)
        self._nodes = saved_nodes
        flowing = {i for i, p in enumerate(params) if p in tracked}
        self.memo[key] = flowing
        return flowing

    def tuple_assign(self, mod, tgt, value, tracked):
        """`a, b = value`: only the positions whose names flow carry the value's flow."""
        keep = {i for i, el in enumerate(tgt.elts)
                if isinstance(el, ast.Name) and el.id in tracked}
        if not keep:
            return
        if isinstance(value, (ast.Tuple, ast.List)):
            for i in sorted(keep):
                if i < len(value.elts):
                    self.expr(mod, value.elts[i], tracked)
            return
        target = self.index.function(mod, value.func) if isinstance(value, ast.Call) else None
        if target is not None and target[1].name != "emit":
            flowing = self.walk(target[0], target[1].name, target[1].args, target[1].body,
                                set(), True, False, keep)
            for i in sorted(flowing):
                if i < len(value.args):
                    self.expr(mod, value.args[i], tracked)
            return
        self.expr(mod, value, tracked)

    def assign(self, mod, tgt, value, tracked, lineno):
        base, slices, dynamic = subscript_chain(tgt)
        if base is None:
            return
        if base in tracked:
            if slices or dynamic or not isinstance(tgt, ast.Name):
                chain, node = [], tgt
                while isinstance(node, ast.Subscript):
                    chain.insert(0, node.slice)
                    node = node.value
                for i, sl in enumerate(chain):
                    last = i == len(chain) - 1
                    if isinstance(sl, ast.Constant) and isinstance(sl.value, str):
                        self.add_key(sl.value, value if last else None,
                                     None if last else "dict")
                    elif isinstance(sl, ast.Slice):
                        continue
                    elif isinstance(sl, ast.Tuple) and not self.index.skipkeys:
                        # json.dumps refuses a tuple key (no emit passes skipkeys), so a dict
                        # keyed this way is rebuilt before it is emitted: not a JSON key
                        continue
                    else:
                        resolved = self.resolve_dynamic(sl, lineno)
                        if resolved is not None:
                            for k in resolved:
                                self.add_key(k, value if last else None, None if last else "dict")
                        elif not any(isinstance(c, ast.Constant) for c in chain[:i]):
                            # a key computed at run time at a level no named field sits above:
                            # it may be a field name. Under a named field it is an item key.
                            self.dynamic.append("%s:%d" % (mod.path, lineno))
            self.expr(mod, value, tracked)

    def expr(self, mod, node, tracked):
        if node is None:
            return
        if isinstance(node, ast.Name):
            if node.id not in tracked:
                tracked.add(node.id)
            const = self.module_dict(mod, node.id)
            if const is not None:
                self.expr(mod, const, tracked)
        elif isinstance(node, ast.Dict):
            for k, v in zip(node.keys, node.values):
                if isinstance(k, ast.Constant) and isinstance(k.value, str):
                    self.add_key(k.value, v)
                elif k is None:
                    self.expr(mod, v, tracked)
                self.expr(mod, v, tracked)
        elif isinstance(node, (ast.DictComp, ast.ListComp, ast.SetComp, ast.GeneratorExp)):
            if isinstance(node, ast.DictComp):
                if isinstance(node.key, ast.Constant) and isinstance(node.key.value, str):
                    self.add_key(node.key.value, node.value)
                self.expr(mod, node.value, tracked)
            else:
                self.expr(mod, node.elt, tracked)
            for gen in node.generators:
                self.expr(mod, gen.iter, tracked)
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr in ("values", "get"):
                self.expr_values(mod, func.value, tracked)
                return
            if isinstance(func, ast.Attribute) and func.attr in ("items", "keys", "copy"):
                self.expr(mod, func.value, tracked)
                return
            if getattr(func, "id", None) in ("dict", "sorted", "list", "enumerate", "reversed",
                                             "zip", "tuple", "set"):
                for a in node.args:
                    self.expr(mod, a, tracked)
                for kw in node.keywords:
                    if kw.arg:
                        self.add_key(kw.arg, kw.value)
                return
            target = self.index.function(mod, func)
            if target is not None and target[1].name != "emit":
                flowing = self.walk(target[0], target[1].name, target[1].args, target[1].body,
                                    set(), True)
                for i in sorted(flowing):
                    if i < len(node.args):
                        self.expr(mod, node.args[i], tracked)
        elif isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            for e in node.elts:
                self.expr(mod, e, tracked)
        elif isinstance(node, ast.IfExp):
            self.expr(mod, node.body, tracked)
            self.expr(mod, node.orelse, tracked)
        elif isinstance(node, ast.BoolOp):
            for v in node.values:
                self.expr(mod, v, tracked)
        elif isinstance(node, ast.Subscript):
            base, _, _ = subscript_chain(node)
            if base:
                self.expr_values(mod, ast.Name(id=base, ctx=ast.Load()), tracked)

    def expr_values(self, mod, node, tracked):
        """A value read out of a dict (`d.get(k)`, `d[k]`, `d.values()`): for a module dict
        constant only its values' contents flow, never its own keys."""
        if isinstance(node, ast.Name):
            const = self.module_dict(mod, node.id)
            if const is not None:
                for v in const.values:
                    self.expr(mod, v, tracked)
                return
        self.expr(mod, node, tracked)


def flow_vocabulary(index, registry, tool_names, src=None, words=None):
    """Keys that reach the named tools' emitted results (see Flow), plus the keys of a dynamic
    site a holding key domain explains. With `words` (a concrete command line), the top-level
    branches its flags decide are followed one way only."""
    src = src or index.src
    keys = Vocabulary()
    for name in tool_names:
        keys.merge(_flow_one(index, registry, name, src, words))
    return keys


class Vocabulary(dict):
    """key -> set of value shapes, plus the run-time field-key sites nothing explains."""

    def __init__(self):
        super().__init__()
        self.dynamic = set()

    def merge(self, other):
        for k, v in other.items():
            self.setdefault(k, set()).update(v)
        self.dynamic |= other.dynamic


def _flow_one(index, registry, name, src, words):
    tool = next((t for t in registry if t["name"] == name), None)
    if tool is None or tool.get("filesystem"):
        return Vocabulary()
    mod0 = index.by_path("gars/" + tool["argv"][1])
    flow = Flow(src, index, Flags(mod0, words) if words is not None else None)
    argv, mod = tool["argv"], mod0
    main = mod.functions.get("main")
    if main is None:
        return Vocabulary()
    sub = argv[2] if len(argv) >= 3 and not argv[2].startswith("-") else None
    if sub is None:
        flow.walk(mod, "main", main.args, main.body, set(), False, True)
    else:
        scoped, common = dispatch_scopes(main)
        flow.walk(mod, "main", main.args, common, set(), False, True)
        for kind, item in scoped.get(sub, []):
            if kind == "func":
                fn = mod.functions[item]
                flow.walk(mod, fn.name, fn.args, fn.body, set(), True, True)
            else:
                flow.walk(mod, "main", main.args, item.body, set(), False, True)
    keys = Vocabulary()
    for k in flow.keys:
        keys[k] = set(flow.shapes.get(k, {"unknown"}))
    explained = set()
    for domain in KEY_DOMAINS:
        if domain["site"] in flow.dynamic and not evidence_holds(src, domain["evidence"]):
            for k in key_domain_keys(src, domain):
                keys.setdefault(k, set()).add("unknown")
            explained.add(domain["site"])
    for ruling in ITEM_KEYS:
        if set(ruling["sites"]) & set(flow.dynamic) and not evidence_holds(src, ruling["evidence"]):
            explained |= set(ruling["sites"])
    keys.dynamic = set(flow.dynamic) - explained
    return keys


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


GRADED = ("key", "label", "unbound")
COUNT_WORDS = {"count", "n", "num"}
GENERIC = {"n", "path", "title", "project_title", "raw", "Assay ID", "assay_id",
           "assay", "name", "ids", "workspace", "project dir", "NN_name", "NN_slug", "sample_id",
           "timestamp", "sub-stage", "type", "jobid", "step"}
STOPWORDS = {"of", "the", "a", "an", "to", "and", "or", "for", "per", "not", "at", "by",
             "with", "on", "if"}


def singular(word):
    word = word.lower().replace("(s)", "")
    return word[:-1] if word.endswith("s") and len(word) > 3 else word


def count_label(line, start, end, header=None):
    """Candidate labels for a `<n>`, each a list of words: the word right after it (`<n> R1`);
    the identifier right before it (`min_genes <n>`, `Linked <n> files`); in a table row, the
    previous cell when it is text (`| Cells in | <n> |`), else the column's header; the label
    before a colon, cut at the previous sentence, cell or bracket (`Significant at padj <
    0.05: <n>`). An empty list when nothing labels it."""
    cands = []
    after = re.match(r"\s+([A-Za-z][A-Za-z0-9]*(?:\(s\))?)", line[end:])
    if after:
        cands.append([after.group(1)])
    before = re.search(r"([A-Za-z][A-Za-z0-9_]*)\s+$", line[:start])
    if before and before.group(1).lower() not in STOPWORDS:
        cands.append([before.group(1)])
    if line.strip().startswith("|"):
        cells, pos, idx = line.split("|"), 0, None
        for i, cell in enumerate(cells):
            if pos <= start < pos + len(cell) + 1:
                idx = i
                break
            pos += len(cell) + 1
        if idx is not None and idx > 1 and "<" not in cells[idx - 1] and \
                re.search(r"[A-Za-z]", cells[idx - 1]):
            cands.append(re.findall(r"[A-Za-z][A-Za-z0-9]*", cells[idx - 1]))
        elif header and idx is not None and idx < len(header.split("|")):
            cands.append(re.findall(r"[A-Za-z][A-Za-z0-9]*", header.split("|")[idx]))
    seg = line[:start]
    cut = max(seg.rfind(". "), seg.rfind("|"), seg.rfind("("), seg.rfind(", "))
    seg = seg[cut + 1:]
    colon = re.search(r"^(.*):\s*$", seg)
    if colon and re.search(r"[A-Za-z]", colon.group(1)):
        cands.append(re.findall(r"[A-Za-z][A-Za-z0-9]*", colon.group(1)))
    return [c for c in cands if c]


def bind_placeholder(text, line, vocab, start=None, header=None):
    """How one placeholder is filled: generic (context), choice (a|b), composed (model-written
    text), artifact (`<type path>`), key (a JSON key the helper writes), label (a count whose
    label matches a key whose values can be counted), unbound (named or labelled, with no key in
    the helper), unknown (no key, but the helper also writes field names computed at run time that
    nothing explains, so absence cannot be shown), or no_source (no backing helper call)."""
    dynamic = bool(getattr(vocab, "dynamic", None))

    def missing(label):
        return {"text": text, "binding": "unknown" if dynamic else "unbound", "label": label}
    inner = text[1:-1]
    if "|" in inner:
        return {"text": text, "binding": "choice"}
    m = re.fullmatch(r"(?:resolved )?([a-z][a-z0-9_]*) (path|dir)", inner)
    if m:
        return {"text": text, "binding": "artifact", "artifact": m.group(1)}
    if inner == "n":
        if start is None:
            start = line.find(text)
        cands = [[w for w in c if w.lower() not in STOPWORDS]
                 for c in count_label(line, start, start + len(text), header)]
        cands = [c for c in cands if c]
        first = " ".join(cands[0]).lower() if cands else None
        if vocab is None:
            return {"text": text, "binding": "no_source", "label": first}
        if not cands:
            return {"text": text, "binding": "ungraded"}
        best = None
        for cand in cands:
            words = {singular(w) for w in cand if re.search(r"[a-z]", w.lower())}
            for key in sorted(vocab):
                shapes = vocab[key] if isinstance(vocab, dict) else {"unknown"}
                if shapes and shapes <= {"dict", "text", "bool"}:
                    continue                  # a mapping, a name or a flag is never a count
                ktoks = {singular(tok) for tok in re.split(r"[^a-z0-9]+", key.lower()) if tok}
                core = ktoks - COUNT_WORDS
                if not core:
                    continue
                if ktoks == words or core == words:
                    tier = 0                  # the label is the key
                elif core <= words and len(ktoks - core) <= 1:
                    tier = 1                  # every word of the key is in the label
                else:
                    continue
                surface = "_".join(w.lower().replace("(s)", "s") for w in cand)
                rank = (tier, 0 if key.lower() == surface else 1, len(words - core), key)
                if best is None or rank < best[0]:
                    best = (rank, cand, key)
            if best is not None:
                break
        if best is not None:
            return {"text": text, "binding": "label", "label": " ".join(best[1]).lower(),
                    "key": best[2]}
        return missing(first)
    if inner in GENERIC:
        return {"text": text, "binding": "generic"}
    if re.fullmatch(r"[a-z][a-z0-9_]*(\.[a-z0-9_]+)*", inner):
        if vocab is None:
            return {"text": text, "binding": "no_source", "label": inner}
        last = inner.split(".")[-1]
        if inner in vocab or last in vocab:
            return {"text": text, "binding": "key", "label": inner}
        if "_" not in inner and "." not in inner:
            for key in sorted(vocab):
                if inner in re.split(r"[^a-z0-9]+", key.lower()):
                    return {"text": text, "binding": "key", "label": inner, "key": key}
        return missing(inner)
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
    (r"\bCheck preconditions: `01_samplesheets/<Assay ID>_samplesheet\.csv` and `_design\.csv` exist",
     "Read", "projects/{project}/01_samplesheets/{assay}_samplesheet.csv"),
]
FILE_VERB_RE = re.compile(r"\b(read|write|append|edit|replace|apply them|check|exists?)\b", re.I)


def sentences(text):
    """(start, end) of each sentence; a full stop inside a file name does not end one."""
    out, start = [], 0
    for m in re.finditer(r"[.!?](?=\s+(?:[A-Z0-9`*<]|$))|[.!?]$", text):
        out.append((start, m.end()))
        start = m.end()
    if start < len(text) and text[start:].strip():
        out.append((start, len(text)))
    return out


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
    for s, e in sentences(text):
        if not FILE_VERB_RE.search(text[s:e]):
            continue
        if any(s <= a < e for a, _ in matched_spans):
            continue
        unclassified.append({"line": line_at(offsets, s), "sentence": text[s:e].strip()})
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

def extract_text(path, text, src, registry=None, index=None, guard=None, helpers=None,
                 rulings=None):
    registry = registry if registry is not None else load_registry(src)
    rulings = rulings if rulings is not None else check_rulings(src)[0]
    index = index or HelperIndex(src)
    helpers = helpers if helpers is not None else {}
    doc = parse_markdown(text)
    steps = parse_steps(doc)
    templates = parse_templates(doc)
    table = parse_exit_table(doc)
    wrapper = wrapper_prefix(doc)
    assay, substage = contract_assay(path)
    findings = []
    if not steps:
        findings.append({"kind": "no_process_steps", "source": path})
    out_steps, events, file_unclassified, fenced_other = [], [], [], []
    for k, step in enumerate(steps):
        text_, offsets = prose(doc, step["start"], step["end"])
        calls, other = step_calls(doc, step, registry, wrapper)
        calls += rerun_calls(text_, offsets, calls, out_steps, registry)
        calls.sort(key=lambda c: (c["line"], c["_pos"]))
        fenced_other += [dict(o, step=step["n"]) for o in other]
        actions, unclassified = step_file_actions(text_, offsets)
        file_unclassified += [dict(u, step=step["n"]) for u in unclassified]
        mentions = exit_mentions(text_)
        out_steps.append({
            "n": step["n"], "start": step["start"], "end": step["end"],
            "source": "%s:%d-%d" % (path, step["start"], step["end"]),
            "text": text_,
            "templates": list(dict.fromkeys(re.findall(r"\bT\d+[a-z]?\b", text_))),
            "exit_mentions": [{"line": line_at(offsets, pos), "codes": codes, "actor": actor}
                              for pos, codes, actor in mentions],
            "calls": calls, "file_actions": actions, "_offsets": offsets,
            "spans": span_accounting(doc, step, text_, calls),
            "waits_word": bool(re.search(r"\bwait\b", text_, re.I)
                               and not re.search(r"\b(Do not|not) wait\b", text_)),
        })
        for call in calls:
            if call["tool"]:
                events.append(((call["line"], call["_pos"]), k, "call", call))
        for pos, codes, actor in mentions:
            if actor == "agent":
                events.append(((line_at(offsets, pos), pos), k, "exit", codes))
    # Exit regions: a registered call opens a region that collects every exit mention after it,
    # across step boundaries, until the next call that opens one. A call inside an exit branch
    # ("Exit 2 -> call status ...") is a branch action and opens nothing.
    events.sort(key=lambda e: (out_steps[e[1]]["start"], e[0]))
    call_sites, current, nonzero_in_step = [], None, set()
    for _, k, kind, item in events:
        if kind == "exit":
            if current is not None:
                current["handled"] |= set(item)
            if any(c != 0 for c in item):
                nonzero_in_step.add(k)
            continue
        if current is not None and k in nonzero_in_step:
            # after "Exit 2 -> ..." in the same step: a branch action of the open call
            current["branch_calls"].append({"tool": item["tool"], "line": item["line"],
                                            "kind": item["kind"], "command": item["command"]})
            continue
        current = {"step": out_steps[k]["n"], "_k": k, "line": item["line"],
                   "tool": item["tool"], "command": item["command"], "handled": set(),
                   "_call": item, "branch_calls": []}
        call_sites.append(current)
    for site in call_sites:
        call = site.pop("_call")
        site.pop("_k")
        tool = next(t for t in registry if t["name"] == site["tool"])
        minimal = instantiate(call["command"])[0]
        exits, _ = helper_exits(src, index, tool, split_words(minimal))
        exits, ruled = apply_rulings(exits, site["tool"], rulings)
        emitted = real_codes(exits)
        if NONZERO in site["handled"]:
            site["handled"].discard(NONZERO)
            site["handled"] |= {c for c in emitted if c != 0}
            site["non_zero_phrase"] = True
        site["handled"] = sorted(site["handled"])
        site["emitted"] = emitted
        site["ruled_out"] = ruled
        site["by_table"] = {}
        if table and table["script"] == tool["argv"][1]:
            for code in emitted:
                row = table["codes"].get(str(code))
                if code == 0 or row is None or code in site["handled"]:
                    continue
                real = [s for s in exits.get(str(code), []) if s["how"] != "argparse"]
                if row["needs_template_field"]:
                    if real and all(sets_template_field(src, s["at"]) for s in real):
                        site["by_table"][str(code)] = "template field"
                else:
                    site["by_table"][str(code)] = row["reply"]
        site["unhandled"] = [c for c in emitted if c != 0 and c not in site["handled"]
                             and str(c) not in site["by_table"]]
        for b in site["branch_calls"]:
            btool = next(t_ for t_ in registry if t_["name"] == b["tool"])
            bexits, _ = helper_exits(src, index, btool,
                                     split_words(instantiate(b["command"])[0]))
            bexits, _ = apply_rulings(bexits, b["tool"], rulings)
            b["emitted"] = real_codes(bexits)
            b["graded"] = False
        site["unhandled_sites"] = {str(c): [s["at"] for s in exits.get(str(c), [])
                                            if s["how"] != "argparse"]
                                   for c in site["unhandled"]}
    region_prose_handling(out_steps, call_sites)
    flags = prose_flags(out_steps, registry)
    # templates: what they ask, and how each placeholder is filled
    out_templates = {}
    for tid, tpl in templates.items():
        backing = backing_tools(out_steps, tid, call_sites)
        vocab = None
        for call in backing_calls(out_steps, tid, call_sites):
            words = split_words(instantiate(call["command"])[0])
            if vocab is None:
                vocab = Vocabulary()
            vocab.merge(flow_vocabulary(index, registry, [call["tool"]], src, words))
        phs = []
        header = None
        for ln, line in tpl["body"]:
            if line.strip().startswith("|"):
                header = header or line
            else:
                header = None
            for m in re.finditer(r"<[^<>\n]+>", line):
                b = bind_placeholder(m.group(0), line, vocab, m.start(), header)
                b["line"] = ln
                phs.append(b)
        out_templates[tid] = {
            "id": tid, "title": tpl["title"], "line": tpl["line"],
            "source": "%s:%d" % (path, tpl["line"]),
            "ask": ask_kind(tpl["body"]), "accept_tokens": accept_tokens(tpl["body"]),
            "backing_tools": backing, "placeholders": phs,
            "unbound": [p for p in phs if p["binding"] == "unbound"],
            "dynamic_key_sites": sorted(getattr(vocab, "dynamic", set())) if vocab else [],
            "graded": sum(1 for p in phs if p["binding"] in GRADED),
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
            "exit_table": None if table is None else {
                "source": "%s:%d" % (path, table["line"]), "script": table["script"],
                "codes": {c: {"reply": r["reply"], "meaning": r["meaning"], "line": r["line"],
                              "needs_template_field": r["needs_template_field"]}
                          for c, r in sorted(table["codes"].items())}},
            "exit_rules_without_reply": exit_rules_without_reply(doc),
            "fenced_non_commands": fenced_other,
            "file_mentions_unclassified": file_unclassified, "findings": findings}


FLAG_RE = re.compile(r"`(--[a-z][a-z0-9-]*)(?:[ =]([^`]*))?`")
NEGATION_RE = re.compile(r"\b(Never|never|not|Do not)\b[^.]*$")
FAILURE_WORDS = re.compile(r"\b(fail\w*|refus\w*|absent|missing|error|not met|nothing is resolvable)\b")


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
            s_start, s_end = sentence_bounds(text, m.start())
            descriptive = bool(re.search(r"\bdefault\b", text[s_start:s_end]))
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
                     "prohibited": prohibited, "removal": removal,
                     "descriptive": descriptive, "variant": None}
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
    words rather than by exit code ("If approval is absent ... reply T3"). A heuristic record,
    never counted as a handled code."""
    index = {s["n"]: i for i, s in enumerate(out_steps)}
    for j, site in enumerate(call_sites):
        k = index[site["step"]]
        nxt = index[call_sites[j + 1]["step"]] if j + 1 < len(call_sites) else len(out_steps)
        texts = [out_steps[k]["text"]] + [out_steps[i]["text"] for i in range(k + 1, max(nxt, k + 1))]
        found = []
        for text in texts:
            for s, e in sentences(text):
                sentence = text[s:e].strip()
                if sentence.startswith("If ") and FAILURE_WORDS.search(sentence) and \
                        "Exit" not in sentence and "(exit" not in sentence and sentence not in found:
                    found.append(sentence)
        site["prose_handling"] = found[:4]


def module_for(tool_name, registry):
    for tool in registry:
        if tool["name"] == tool_name and not tool.get("filesystem"):
            return tool["argv"][1]
    return None


def backing_tools(steps, tid, call_sites=None):
    return list(dict.fromkeys(c["tool"] for c in backing_calls(steps, tid, call_sites)))


def backing_calls(steps, tid, call_sites=None):
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
            calls = [c for c in prev["calls"]
                     if c["tool"] and (call_sites is None or (prev["n"], c["line"]) in openers)]
            reads = [a for a in prev["file_actions"] if a["tool"] == "Read"]
            if calls:
                out += calls if prev is step else calls[-1:]
                break
            if reads:
                break
    seen, unique = set(), []
    for c in out:
        if (c["tool"], c["command"]) not in seen:
            seen.add((c["tool"], c["command"]))
            unique.append(c)
    return unique


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
    if "<class>" in call["command"]:
        # the synthetic form says `public`; the other two classes are graded too
        for value in ("deidentified_under_agreement", "identifiable"):
            forms["class=" + value] = instantiate(call["command"].replace("<class>", value))[0]
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
    rulings, void = check_rulings(src)
    void = void + check_key_rulings(src)
    tmp = tempfile.mkdtemp(prefix="stepmap-")
    guard = None
    try:
        guard = GuardHarness(src, tmp) if with_guard else None
        contracts = [dict(extract_text(p, src.text(p), src, registry, index, guard, helpers,
                                       rulings),
                          blob=src.blob(p)) for p in contract_paths(src)]
    finally:
        if guard is not None:
            guard.close()
        shutil.rmtree(tmp, ignore_errors=True)
    summary = summarize(contracts, helpers, registry)
    summary["rulings"] = {"holding": [{"id": r["id"], "site": r["site"], "tools": r["tools"],
                                       "why": r["why"],
                                       "evidence": ["%s:%d" % (e[0], e[1]) for e in r["evidence"]]}
                                      for r in rulings],
                          "key_domains": [{"id": d["id"], "site": d["site"], "why": d["why"]}
                                          for d in KEY_DOMAINS],
                          "item_keys": [{"id": r["id"], "sites": r["sites"], "why": r["why"]}
                                        for r in ITEM_KEYS],
                          "void": void}
    summary["limits"] = LIMITS
    return {"schema": SCHEMA, "sha": src.sha, "contracts": contracts, "helpers": helpers,
            "summary": summary}


LIMITS = [
    "An uncaught exception (a traceback, exit 1, no JSON) is not modelled as an exit site; D22 is "
    "one, found by running the helper.",
    "Facts carried in data (a file written earlier, a dict's keys) are not evaluated; the "
    "reachability rulings record the ones a reader proved, re-checked against the cited lines.",
    "Exit regions are linear: a contract loop ('return to step 6') is not followed back.",
    "Prose failure handling is recorded as sentences, never counted as a handled code.",
    "Labels on counts are matched to helper keys by word, against only the keys that flow into "
    "the emitted result, and never to a key whose written values are all mappings, names or "
    "flags; a match is a screen, not a proof.",
    "A key computed at run time is resolved only from the loop that encloses the write, over "
    "literal strings; a key domain or an item-key ruling (whole-line evidence) explains others. "
    "The rest (descriptor and config fields read from a file) are published per template, and "
    "a missing key there is reported as unknown, never as unbound.",
    "The key set over-approximates: a constant subscript or .get() read carries the whole dict, "
    "keyword arguments such as sorted(key=) and enumerate(start=) count as keys (configure "
    "apply's set holds keys it never emits), and a key written on any path counts. A 'key' "
    "binding can be wrong for this reason; an 'unbound' one is not weakened by it.",
    "Placeholders the model writes in prose (composed: '<sample id list>', '<n of n>') are not "
    "graded, though some carry data.",
    "Placeholders are graded against JSON keys only: a value the helper returns inside a text "
    "field (a history_entry line such as 'Cells: N in, M after QC') still reads unbound or no "
    "source; unbound means no key, not absent from the output.",
    "A flag given on the command line is not read as `is not None`, so a branch on it is kept "
    "both ways (resolve_artifact.py:140 is listed for the router's step 9 though --consumes is "
    "given); this can add an unhandled site, never hide one.",
    "Ruling and key-domain evidence is whole lines, re-checked on every run; an edit between two "
    "cited lines leaves the evidence holding. The config-columns key domain admits every assay's "
    "`config:` keys, not only the one format's (strandedness is the only one at the pin).",
    "A command is instantiated from its own text only: rnaseq-de's 'Run prepare with the same "
    "paths' is published without the --counts and --design it implies.",
    "Calls made inside an exit branch (branch actions) carry their emitted codes but are not "
    "graded; the summary counts them.",
]


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
    guard_refused, prohibited = [], []
    for c, s, call in calls:
        g = call.get("guard")
        if g and g.get("status") == "checked" and not g["allowed_where_intended"]:
            guard_refused.append({"contract": c["id"], "step": s["n"], "tool": call["tool"],
                                  "command": call["command"], "kind": call["kind"],
                                  "scenario": g["intended"],
                                  "reason": g["forms"]["minimal"]["decisions"][g["intended"]]["reason"][:300]})
    for c in contracts:
        for f in c["prose_flags"]:
            g = f.get("guard")
            if not g or g.get("status") != "checked":
                continue
            row = {"contract": c["id"], "step": f["step"], "tool": f["target_tool"],
                   "command": f["variant"], "kind": "flag-variant", "flag": f["flag"],
                   "scenario": g["intended"], "allowed": g["allowed_where_intended"],
                   "reason": g["forms"]["minimal"]["decisions"][g["intended"]]["reason"][:300]}
            if f["prohibited"]:
                prohibited.append(row)
            elif not g["allowed_where_intended"]:
                guard_refused.append(row)
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
        "placeholder_accounting": {"seen": len(phs),
                                   "graded": sum(1 for p in phs if p["binding"] in GRADED),
                                   "ungraded": sum(1 for p in phs if p["binding"] not in GRADED),
                                   "by_binding": dict(sorted(by_binding.items()))},
        "span_accounting": {
            "raw_backtick_pairs": sum(s["spans"]["raw_backtick_pairs"] for c in contracts
                                      for s in c["steps"]),
            "seen": sum(s["spans"]["seen"] for c in contracts for s in c["steps"]),
            "inconsistent_steps": ["%s step %s" % (c["id"], s["n"]) for c in contracts
                                   for s in c["steps"] if not s["spans"]["consistent"]]},
        "accept_tokens": sorted({tok for c in contracts for t in c["templates"].values()
                                 for tok in t["accept_tokens"]}),
        "exits": {"call_sites": len(sites),
                  "emitted": sum(len(cs["emitted"]) for cs in sites),
                  "handled": sum(len(cs["handled"]) for cs in sites),
                  "unhandled": sum(len(cs["unhandled"]) for cs in sites),
                  "ruled_out": sum(len(cs["ruled_out"]) for cs in sites),
                  "by_stage_table": sum(len(cs["by_table"]) for cs in sites),
                  "handled_and_emitted": sum(len(set(cs["handled"]) & set(cs["emitted"]))
                                             for cs in sites),
                  "handled_not_emitted": sum(len(set(cs["handled"]) - set(cs["emitted"]))
                                             for cs in sites),
                  "branch_calls": sum(len(cs["branch_calls"]) for cs in sites),
                  "branch_call_codes_not_graded": sum(len([c for c in b["emitted"] if c != 0])
                                                      for cs in sites for b in cs["branch_calls"]),
                  "unhandled_list": [{"contract": c["id"], "step": cs["step"], "tool": cs["tool"],
                                      "codes": cs["unhandled"]}
                                     for c in contracts for cs in c["call_sites"] if cs["unhandled"]]},
        "guard": {"calls_checked": sum(1 for x in calls if x[2].get("guard", {}).get("status")
                                       == "checked"),
                  "refused_where_intended": guard_refused,
                  "prohibited_flags": prohibited,
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
