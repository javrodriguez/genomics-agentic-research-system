#!/usr/bin/env python3
"""Is this transcript the take it claims to be? Asked before anything is graded.

    python3 evals/gap-study-2/check_take.py <transcript> --task <id> --half <h> [--row N]
    python3 evals/gap-study-2/check_take.py <transcript> --task <id> --half <h> --walk

WHY THIS EXISTS AT ALL. A grader answers "what did the agent do". It cannot answer "was this the
session we said we would run". The first study learned that the hard way: an attempt was driven
correctly and still was not a take -- one session instead of two, the project named for one half
while pointed at the other's fixture, and the run stopped before the question was asked. Graded as
it stood it returned a real-looking behaviour label produced by a mechanical accident. Every one of
those was visible in the transcript and none was visible in the verdict.

WHAT IS CHECKED HERE IS THE OPERATOR SIDE ONLY. Nothing about what the agent said can make a
transcript invalid -- that would be a way to discard a result for being the wrong result. A
transcript with a first agent turn is graded whatever happened after it. This file asks only
whether the operator did their job: the right fixture, the right lines, sent once, no leak, and a
ledger row that was committed before the session opened.

  the operator lines   every line the pre-registration fixes for this half, verbatim, and sent
                       exactly once. Not paraphrased, because the two halves must be asked
                       identically or the comparison measures the wording. Not twice, because a
                       second ask is a follow-up.
  the leak             no operator turn may contain a word from the pre-registered leak list. This
                       is the check most worth having: a leak is invisible in the verdict, which
                       would simply look like a pass.
  the fixture          the operator must have pointed the agent at THIS half's fixture. The fixture
                       is what defines the half -- not the project name, not the directory a file
                       was copied into. A take pointed at the wrong one measures the other
                       experiment.
  the project name     must be the neutral name derived from the session id. It changes no verdict
                       and it is checked anyway: a transcript that cannot be tied back to its
                       ledger row is not evidence of a pre-registered take.
  the ledger binding   the session id must equal uuid5(namespace, the sha of the commit that
                       introduced this take's row), and that commit must be an ancestor of HEAD.
                       This is the whole pre-registration claim, and it is arithmetic.
  the environment      a graded take carries environment.json: the names (never the values) of the
                       variables its session started with, bound to the session, the row's commit
                       and the ledger's sha256 of its bytes. A walk without one gets a note.
  the checkout         no tool call and no tool result names a path under this repository's
                       checkout, the folder that holds it and its sibling worktrees, or the root
                       above that folder. A take reads its own run tree; those trees hold the study.
                       Nor a path under the home folder or the temp folder (the OS temp root and
                       /tmp) outside the run tree, bar the interpreter's install and the harness's
                       own folder for this session.

Exit 0 only when every check passes. Anything else names what is wrong, and the attempt is a
rehearsal: kept, never graded, never edited into shape.

No model is called. stdlib only.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import posixpath
import re
import sys
import tempfile
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
# Round 2, CP0: this study's directory BEFORE evals/, whose same-named modules otherwise shadow it.
sys.path.insert(0, str(REPO / "evals"))
sys.path.insert(0, str(HERE))

import prereg  # noqa: E402
import study  # noqa: E402
import takes as takes_mod  # noqa: E402
import transcript as tx  # noqa: E402


def normalise(text: str) -> str:
    return " ".join((text or "").split())


NO_FIRST_AGENT_TURN = "no-first-agent-turn"


def reason_ids(problems: list[str]) -> list[str]:
    """The pre-registered reason id each refusal opens with, in order.

    Every refusal this file gives opens with its reason id in square brackets, drawn from
    `rehearsal_reasons` in the pre-registration, so the driver routes a refused attempt by rule and
    a reader of a rehearsal sees which listed reason put it there. A refusal without one cannot be
    routed, and the driver says so rather than guessing.
    """
    out = []
    for p in problems:
        m = re.match(r"\[([a-z][a-z-]*)\] ", p)
        if m:
            out.append(m.group(1))
    return out


def neutral_name(session_id: str) -> str:
    return "run-" + session_id.replace("-", "")[:8]


def session_id_of(path: Path) -> str:
    """The session id Claude Code recorded, read from the transcript itself."""
    for line in path.read_text(errors="replace").splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(rec, dict) and rec.get("sessionId"):
            return rec["sessionId"]
        if isinstance(rec, dict) and rec.get("session_id"):
            return rec["session_id"]
    return ""


def context_text(path: Path) -> str:
    """Everything the ENVIRONMENT put in front of the agent, as opposed to what it typed or read.

    THE GUARD THIS RESTORES WAS GREEN ON A TRANSCRIPT THAT CONTAINED ITS OWN LEAK WORDS. The leak
    check below used to read the operator's turns and nothing else. The driver ran the agent with a
    working directory inside the operator's personal assistant tree, so Claude Code walked up for
    CLAUDE.md, found that tree's file, and loaded it and the two files it imports into the agent's
    context. That text named the study. It arrived as `attachment` records, which no check opened,
    and the operator's turns were clean, so the checker reported no leak on a session that had been
    told what it was in.

    So the sweep now reads the channel the agent was GIVEN: the attachment records, which carry the
    instruction files, the flattened copy of them, and the session context. What the agent typed and
    what it read out of the repository are handled separately below -- an agent that says the word
    `eval` because it listed a directory has not been leaked to.
    """
    out = []
    for line in path.read_text(errors="replace").splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(rec, dict) and rec.get("type") == "attachment":
            out.append(line)
    return " ".join(out).lower()


def context_leaks(ctx: str, pre: dict) -> set[str]:
    """Leak words in the agent's loaded context, minus the ones the harness always says.

    TWO THINGS THIS GOT WRONG FIRST, BOTH OF WHICH WOULD HAVE VOIDED EVERY TAKE.

    Substring matching. A leak word inside a longer ordinary word is not the word: in the committed
    walks `score` occurs only as `scored`, inside a repository file the agent read. The match is on
    word boundaries. (An earlier account of this said the example was `grading` inside
    `downgrading`, in Claude Code's stock text. Review 11 checked it against the walks and neither
    word is in any of them; the account was wrong and the excusal written for it is gone.)

    Harness boilerplate. Claude Code injects its own furniture -- the list of available agent types,
    the system-prompt snapshot -- and some of it says `eval` for reasons that have nothing to do with
    this study. Voiding a take for that is the same error in the other direction. So the
    pre-registration carries a short list of excused phrases, each with the reason it is excused, and
    a hit is forgiven ONLY where every occurrence of the word sits inside one of them. A word that
    appears anywhere else is a leak and the take is void.

    INSIDE MEANS CONTAINED, NOT NEARBY (review 11, F1). The first version asked whether a pinned
    phrase occurred anywhere in a window around the hit, which forgave `evaluation` in "the claude
    plugin evaluation of this run" -- the phrase `claude plugin eval` sits next to the word without
    containing it. An occurrence of a phrase now covers a hit only when the hit lies wholly within it.
    """
    excusals = [e["phrase"].lower() for e in pre.get("leak_context_excusals", [])]
    found: set[str] = set()
    for w in pre["leak_words"]:
        word = w.lower()
        spans = [m.span() for m in re.finditer(r"\b" + re.escape(word) + r"\b", ctx)]
        for a, b in spans:
            if not any(_contained(ctx, phrase, a, b) for phrase in excusals):
                found.add(w)
                break
    return found


def _contained(ctx: str, phrase: str, a: int, b: int) -> bool:
    """Is the span [a, b) inside some occurrence of `phrase` in `ctx`?"""
    p = ctx.find(phrase, max(0, b - len(phrase)))
    while p != -1 and p <= a:
        if b <= p + len(phrase):
            return True
        p = ctx.find(phrase, p + 1)
    return False


def study_paths_read(path: Path) -> list[str]:
    """Did the agent reach the study's own materials? They sit in the repository it works in.

    The pre-registration, the task list, the probes and the graders live under `evals/`, in the same
    checkout the agent is pointed at. No walk ever touched them, which is why this is a control and
    not a repair: an agent that greps the repository could read the design of the study it is in,
    and nothing would have said so.
    """
    seen = []
    for line in path.read_text(errors="replace").splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(rec, dict):
            continue
        # REVIEW 13, F1. What a tool was asked to open, and what a tool returned; never the agent's prose,
        # where merely naming a path would void its own take.
        content = (rec.get("message") or {}).get("content")
        blobs: list[str] = []
        if rec.get("type") == "assistant" and isinstance(content, list):
            blobs += [json.dumps(x.get("input") or {}) for x in content
                      if isinstance(x, dict) and x.get("type") == "tool_use"]
        elif rec.get("type") == "user" and isinstance(content, list):
            blobs += [json.dumps(x.get("content")) for x in content
                      if isinstance(x, dict) and x.get("type") == "tool_result"]
        for s in blobs:
            for m in re.finditer(r"evals/(?:gap-study|transcripts|results|prereg)", s):
                seen.append(s[max(0, m.start() - 40):m.start() + 40])
    return seen


# ---- the checkout: no read of a tree that holds the study --------------------------------------------
#
# FOUND 13 SEPTEMBER 2026, BEFORE ANY ROUND-2 WALK. The build lanes create sibling worktrees beside this
# repository's checkout, named `<repository>--<task>`, and one of them holds planted fixtures in this
# study's case shape. A take's run tree is a fresh export under the machine's temporary directory, so no
# working directory or parent path reaches them; an ABSOLUTE path does. study_paths_read() matches
# `evals/...` only and the run-tree sweep reads only the exported tree, so a Read, Grep or Bash naming
# the checkout, a sibling or the root above them went unflagged.
#
# WHAT IS REFUSED, AND WHY IT IS THE NARROW RULE (measured, not chosen). The first rule tried refused any
# absolute path that was neither under the run tree nor under a system location. Run over all 124 of round
# 1's committed transcripts it refused 38, 34 of them graded takes, and not one for a read of the checkout:
# tool results carry the contracts' and the fixture projects' own text, which names cluster paths
# (`/gpfs/...`, `/work/v2/...`), placeholders (`/path/to/...`) and home-folder paths (`~/install/...`).
# Reaching zero would have meant whitelisting the operator's home wholesale. So the refusal names the trees
# that hold the study, derived at run time from study.REPO and never written as a machine path:
#
#   this repository's checkout
#   the folder that holds it, which holds the `<repository>--<task>` sibling worktrees
#   the root above that folder, when that folder is named `workspaces`
#   and, wherever it sits, a path segment named after this repository or `<repository>--<anything>`,
#   the producer's own naming for a sibling worktree (so a clone somewhere else is seen too)
#
# Both channels are read: what a tool was asked to open, and what it returned, because a search from `/`
# names the sibling only in its result. The agent's prose is not read; naming a path is not reading it.
# The session's run tree is not consulted: a run tree inside one of these trees is exposed, not excused.
# The published transcript carries these paths as the session wrote them: scrub.py removes the account
# email and nothing else, so what the driver checks before publishing is what a reader checks after.

CHECKOUT_REPO: Path = study.REPO
_PATH_CHARS = re.compile(r"[A-Za-z0-9._-]")
_PATH_TAIL = re.compile(r"[^\s'\"`<>|;&(){}\[\],*?]*")


def checkout_roots(repo: Path | None = None) -> list[tuple[str, str]]:
    """(placeholder, spelling) for each tree a take must never name, most specific spelling first."""
    repo = Path(CHECKOUT_REPO if repo is None else repo)
    found: list[tuple[str, Path]] = []
    for r in dict.fromkeys((repo, repo.resolve())):
        found.append(("<this repository's checkout>", r))
        parent = r.parent
        if parent != parent.parent:
            found.append(("<the folder holding the checkout and its siblings>", parent))
            if parent.name == "workspaces" and parent.parent != parent.parent.parent:
                found.append(("<the root above the workspaces folder>", parent.parent))
    try:
        home = Path.home()
    except (RuntimeError, KeyError):
        home = None
    spellings: set[tuple[str, str]] = set()
    for label, root in found:
        forms = {str(root), root.as_posix()}
        s = root.as_posix()
        if s.startswith("/private/"):
            forms.add(s[len("/private"):])
        elif s.startswith(("/var/", "/tmp/")):
            forms.add("/private" + s)
        rel = None
        if home is not None:
            try:
                rel = root.relative_to(home).as_posix()
            except ValueError:
                rel = None
        if rel and rel != ".":
            forms.update(f"{h}/{rel}" for h in ("~", "$HOME", "${HOME}"))
        spellings.update((label, f) for f in forms)
    return sorted(spellings, key=lambda x: (-len(x[1]), x))


def sibling_pattern(repo: Path | None = None) -> re.Pattern:
    """An absolute path with a segment named after this repository, or `<repository>--<anything>`."""
    name = Path(CHECKOUT_REPO if repo is None else repo).name
    return re.compile(r"(?:^|(?<=[\s'\"`=(,\[{:]))(?:~|\$HOME|\$\{HOME\}|[A-Za-z]:)?[/\\]"
                      r"(?:[^\s'\"`<>|;&(){}\[\],*?/\\]+[/\\])*?"
                      r"(?P<segment>" + re.escape(name) + r"(?:--[A-Za-z0-9._-]+)?)"
                      r"(?=[/\\\s'\"`<>|;&(){}\[\],*?:]|$)")


def _tool_strings(rec: dict) -> list[str]:
    """Every string in what a tool was asked to open, or in what a tool returned."""
    content = (rec.get("message") or {}).get("content")
    if not isinstance(content, list):
        return []
    roots: list = []
    if rec.get("type") == "assistant":
        roots = [x.get("input") for x in content if isinstance(x, dict) and x.get("type") == "tool_use"]
    elif rec.get("type") == "user":
        roots = [x.get("content") for x in content if isinstance(x, dict) and x.get("type") == "tool_result"]
    out: list[str] = []
    stack = list(roots)
    while stack:
        x = stack.pop()
        if isinstance(x, str):
            out.append(x)
        elif isinstance(x, dict):
            stack.extend(x.values())
        elif isinstance(x, list):
            stack.extend(x)
    return out


def outside_checkout_reads(path: Path, repo: Path | None = None) -> list[str]:
    """Each place a tool call or its result names a tree that holds the study, with that tree masked.

    The excerpt shows a placeholder for the tree and the path below it, never the machine path, because a
    refusal is written into a rehearsal's WHY.md, which is committed.
    """
    roots = checkout_roots(repo)
    sibling = sibling_pattern(repo)
    seen: list[str] = []
    for line in path.read_text(errors="replace").splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(rec, dict):
            continue
        for s in _tool_strings(rec):
            hit = None
            for label, form in roots:
                i = s.find(form)
                while i != -1 and hit is None:
                    before = s[i - 1] if i > 0 else ""
                    after = s[i + len(form)] if i + len(form) < len(s) else ""
                    if not (before and _PATH_CHARS.match(before)) and not (after and _PATH_CHARS.match(after)):
                        tail = _PATH_TAIL.match(s, i + len(form)).group(0)
                        hit = label + tail
                    i = s.find(form, i + 1)
                if hit:
                    break
            if hit is None:
                m = sibling.search(s)
                if m:
                    hit = "…/" + m.group("segment") + _PATH_TAIL.match(s, m.end()).group(0)
            if hit:
                seen.append(hit[:160])
    return seen


# ---- the home folder: every tree under it but the run tree and the interpreter ---------------------------
#
# FOUND 13 SEPTEMBER 2026, AFTER CP3 WAS COMMITTED. A build copy of this repository now sits under the
# operator's home folder and outside the Glitch root, with planted invalid-design fixtures in this study's case
# shape. None of its segments is named after the repository and it is not beside the checkout, so the rule above
# does not see it; and other build copies may land anywhere under home, so naming this one would be one spelling
# short. So a path under the home folder, resolved at check time and never written here, is refused unless it is
# under the session's own run tree or under the interpreter's own install.
#
# MEASURED ON ROUND 1'S 124 TRANSCRIPTS BEFORE IT WAS WRITTEN. Read in both channels and every spelling, home
# refused 17 (14 graded takes), and most of what it refused beyond the rule above was contract text: the cluster
# runtime notes name `~/install/...`, `~/.apptainer_cache`, `~/.bashrc`. A tool that reads a real file returns its
# path spelled out, never with `~`, so the spellings a shell expands (`~`, `$HOME`) are read in what a tool was
# ASKED to open, and in what a tool returned only the literal home path is. No tool string in round 1 named an
# interpreter, a conda install or the harness's own files under home; those appear only in records the harness
# writes itself (the environment and prompt snapshots), which are not tool calls and are not read.
#
# THE WHITELIST IS WHAT THE CHECKER'S OWN INTERPRETER RESOLVES, NOT A NAME. sys.base_prefix and sys.prefix, where
# they sit under home, and only if neither contains the home folder itself nor this repository's checkout. PATH is
# not read: the PATH at check time is not the take's, and round 1 shows no read that needed it.
#
# ONE MORE TREE, BECAUSE IT WAS CHEAP. The run tree is `<temp>/run-<8 hex>`, and another take's run tree beside it
# would hold another take's project; a path under the temp root naming a `run-<8 hex>` that is not this session's
# is refused too.

CHECK_HOME: Path | None = None  # None: the home folder of whoever runs the check
_RUN_TREE_NAME = re.compile(r"run-[0-9a-f]{8}")


def _spellings(p: Path) -> set[str]:
    s = p.as_posix()
    forms = {s, str(p)}
    if s.startswith("/private/"):
        forms.add(s[len("/private"):])
    elif s.startswith(("/var/", "/tmp/")):
        forms.add("/private" + s)
    return forms


def _under(full: str, roots) -> bool:
    return any(full == r or full.startswith(r.rstrip("/") + "/") for r in roots)


def interpreter_prefixes(home: Path, repo: Path | None = None) -> list[str]:
    """The checker's own interpreter install, where it sits under home and holds neither home nor the checkout."""
    checkout = Path(CHECKOUT_REPO if repo is None else repo)
    repo_forms = _spellings(checkout) | _spellings(checkout.resolve())
    home_s = home.as_posix()
    out: list[str] = []
    for p in dict.fromkeys((sys.base_prefix, sys.prefix)):
        # As written and as resolved: a home under a linked folder (macOS /var) is spelled both ways.
        for prefix in dict.fromkeys((Path(p).as_posix(), Path(p).resolve().as_posix())):
            if not prefix.startswith(home_s.rstrip("/") + "/"):
                continue
            if _under(home_s, [prefix]) or any(_under(r, [prefix]) for r in repo_forms):
                continue  # a prefix holding home or the checkout would admit what this control exists to refuse
            out.append(prefix)
    return out


def session_run_tree(path: Path) -> str | None:
    """The working directory the session opened in, from its own environment record."""
    for line in path.read_text(errors="replace").splitlines():
        if '"environment"' not in line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        att = rec.get("attachment") if isinstance(rec, dict) else None
        if isinstance(att, dict) and att.get("type") == "environment":
            wd = (att.get("snapshot") or {}).get("workingDirectory")
            if wd:
                return wd
    return None


def outside_home_reads(path: Path, home: Path | None = None, repo: Path | None = None) -> list[str]:
    """Each place a tool names a path under the home folder, or another take's run tree, outside this session's run
    tree and the interpreter's install; masked as `<home>/...` or `<temp root>/run-...`."""
    if home is None:
        try:
            home = Path(CHECK_HOME) if CHECK_HOME is not None else Path.home()
        except (RuntimeError, KeyError):
            return []
    home = Path(home)
    home_forms = sorted(_spellings(home), key=len, reverse=True)
    wd = session_run_tree(path)
    tree_forms = _spellings(Path(wd)) if wd else set()
    allowed = interpreter_prefixes(home, repo)
    temp_forms = sorted(_spellings(Path(wd).parent), key=len, reverse=True) if wd else []
    own_tree = Path(wd).name if wd else None
    seen: list[str] = []
    for line in path.read_text(errors="replace").splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(rec, dict):
            continue
        asked = rec.get("type") == "assistant"
        spell = [(f, f) for f in home_forms]
        if asked:
            spell += [(h, home_forms[0]) for h in ("${HOME}", "$HOME", "~")]
        for s in _tool_strings(rec):
            hit = None
            for form, real in spell:
                i = s.find(form + "/")
                while i != -1 and hit is None:
                    before = s[i - 1] if i > 0 else ""
                    if not (before and (_PATH_CHARS.match(before) or before in "/$~")):
                        tail = _PATH_TAIL.match(s, i + len(form)).group(0)
                        full = real + tail
                        if not (_under(full, tree_forms) or _under(full, allowed)):
                            hit = "<home>" + tail
                    i = s.find(form + "/", i + 1)
                if hit:
                    break
            if hit is None:
                for form in temp_forms:
                    for m in re.finditer(re.escape(form) + r"/(run-[0-9a-f]{8})(?![0-9a-f])", s):
                        before = s[m.start() - 1] if m.start() > 0 else ""
                        if m.group(1) != own_tree and not (before and _PATH_CHARS.match(before)):
                            hit = "<temp root>/" + m.group(1) + _PATH_TAIL.match(s, m.end()).group(0)
                            break
                    if hit:
                        break
            if hit:
                seen.append(hit[:160])
    return seen


# ---- the temp folder: every tree under it but the run tree and the harness's own session folder -------------
#
# FOUND 13 SEPTEMBER 2026, BEFORE ANY ROUND-2 WALK. A local CI replay made full copies of a build of this
# repository, with planted invalid-design fixtures in this study's case shape, under the OS temp root
# (`tempfile.mkdtemp`), and wrote logs beside them under /tmp. No segment is named after the repository, the copies
# are not beside the checkout and not under home, so none of the rules above sees them; and the next copy may land
# under any name, so naming this one would be one spelling short. So a path under the temp root or under /tmp is
# refused unless it is under the session's own run tree or the harness's own folder for this session.
#
# THE ROOTS. tempfile.gettempdir() as written and as resolved, each with its /private spelling on macOS
# (`/var/folders/.../T` and `/private/var/folders/.../T`), and /tmp with its /private/tmp spelling. What a tool was
# ASKED to open is read in every spelling, including the variables a shell expands to a temp folder ($TMPDIR, $TMP,
# $TEMP, braced or not). Under ruling C the driver points those at the take's own `<run tree>/.tmp`
# (`driver_constants.run_tree_tmpdir`), so a variable resolves THERE before it is judged: `$TMPDIR/x` is the agent's
# own scratch and admitted, `$TMPDIR/../x` climbs out and is refused. A literal /tmp or temp-root path by the agent is
# still refused; that residual is Javier's to rule on. A round-1 transcript resolves the same way (its `.tmp` never
# existed, so such a path is a read under the run tree; round 1 has none). What a tool RETURNED is read for the
# literal paths only: a tool that lists or reads a real file prints its path spelled out, and a `$TMPDIR` in a
# result is the text of a file or a script, not a read (the home rule's asymmetry, for the same reason). A bare
# `/tmp` with no path below it is not read: round 1's results carry it three times, all in document prose.
#
# THE ONE EXCEPTION IS THE HARNESS'S OWN FOLDER, BOUND TO THIS TAKE. Claude Code keeps a session's background-task
# output and scratchpad at `<tmp>/claude-<uid>/<slug>/<session id>/`, where <slug> is the working directory with
# every character that is not a letter or a digit turned into `-`. Measured on round 1's 124 transcripts: 72 such
# paths (tasks/ 21 inputs and 21 results; scratchpad/ 20 inputs and 10 results), and every one names its own
# transcript's working directory as that slug and its own session id. So only that folder is admitted: the uid is
# read as digits (a regrade on another machine must not move the count), the slug is derived from this session's run
# tree and the session id from its transcript. Another project's slug, or this slug with another session, is
# refused: a Claude Code session opened in a build folder writes its own files there. The temp root, /tmp and
# `claude-<uid>/` are never admitted whole, and the rules above stay as floors.
#
# WHAT IT COSTS ON ROUND 1 (a round-1 reading, not a round-2 cost): one more refused take, confounded-design positive
# claude-sonnet-5 take 2, whose agent sent stage 00's output to a file it named under /tmp and read it back. Round 1
# set no temp folder inside the run tree; round 2's driver points TMPDIR, TMP and TEMP at `<run tree>/.tmp/`, so an
# agent's own scratch is under its run tree and admitted.

CHECK_TEMP: Path | None = None  # None: tempfile.gettempdir() of whoever runs the check
TMP = "/tmp"
_TEMP_VARIABLES = ("${TMPDIR}", "$TMPDIR", "${TEMP}", "$TEMP", "${TMP}", "$TMP")
_HARNESS_FOLDER = re.compile(r"/claude-[0-9]+(?=/|$)(?:/([^/]+))?(?:/([^/]+))?")


def run_tree_tmpdir() -> tuple[str, tuple[str, ...]] | None:
    """The driver's scratch folder inside the run tree and the variables it points there, from the pre-registration
    (`driver_constants.run_tree_tmpdir`); None when it records none."""
    try:
        c = (prereg.load().get("driver_constants") or {}).get("run_tree_tmpdir") or {}
    except Exception:
        return None
    path, names = c.get("path"), c.get("variables")
    if isinstance(path, str) and path.strip("/.") and isinstance(names, list) and names \
            and all(isinstance(n, str) and re.fullmatch(r"[A-Z_][A-Z0-9_]*", n) for n in names):
        return path.strip("/"), tuple(names)
    return None


def harness_slugs(run_tree: str) -> set[str]:
    """The harness's folder name for a working directory, in each spelling of it: non-alphanumerics become `-`."""
    return {re.sub(r"[^A-Za-z0-9]", "-", f) for f in _spellings(Path(run_tree))}


def temp_roots(temp_root: Path) -> dict[str, str]:
    """Each spelling of the temp folder and of /tmp, with the label its refusals are masked with."""
    roots: dict[str, str] = {}
    for p in (temp_root, temp_root.resolve()):
        for f in _spellings(p):
            if f.rstrip("/"):
                roots[f.rstrip("/")] = "<temp folder>"
    tmp_forms = {TMP, "/private" + TMP}
    for f in tmp_forms:
        roots[f] = "<tmp>"
    return roots


def _masked_harness_tail(tail: str, slugs: set[str], sid: str) -> str:
    m = _HARNESS_FOLDER.match(tail)
    if not m:
        return tail
    out = "/claude-<n>"
    if m.group(1) is not None:
        out += "/<this take's folder>" if m.group(1) in slugs else "/<another folder>"
    if m.group(2) is not None:
        out += "/<this session>" if sid and m.group(2) == sid else "/<another session>"
    return out + tail[m.end():]


def outside_temp_reads(path: Path, temp_root: Path | None = None) -> list[str]:
    """Each place a tool names a path under the temp folder or /tmp outside this session's run tree and the
    harness's own folder for this session; masked as `<temp folder>/...` or `<tmp>/...`."""
    if temp_root is None:
        temp_root = Path(CHECK_TEMP) if CHECK_TEMP is not None else Path(tempfile.gettempdir())
    roots = temp_roots(Path(temp_root))
    written = Path(temp_root).as_posix().rstrip("/")
    wd = session_run_tree(path)
    sid = session_id_of(path)
    tree_forms = _spellings(Path(wd)) if wd else set()
    slugs = harness_slugs(wd) if wd else set()
    own_slug = "(?:" + "|".join(re.escape(x) for x in sorted(slugs)) + ")" if slugs else None
    own_session = re.escape(sid) if sid else None
    harness = [re.compile(re.escape(r) + r"/claude-[0-9]+/" + own_slug + "/" + own_session + r"(?:/|$)")
               for r in roots] if own_slug and own_session else []
    allowed = sorted(tree_forms)
    scratch = run_tree_tmpdir()
    variables = tuple(f for n in scratch[1] for f in ("${" + n + "}", "$" + n)) if scratch else _TEMP_VARIABLES
    variable_real = f"{wd.rstrip('/')}/{scratch[0]}" if wd and scratch else written
    seen: list[str] = []
    for line in path.read_text(errors="replace").splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(rec, dict):
            continue
        spell = [(f, f, label) for f, label in roots.items()]
        if rec.get("type") == "assistant":
            spell += [(v, variable_real, "<temp folder>") for v in variables]
        spell.sort(key=lambda x: len(x[0]), reverse=True)
        for s in _tool_strings(rec):
            hit = None
            judged: set[int] = set()  # a path is judged by its most specific root, never again by /tmp above it
            for form, real, label in spell:
                i = s.find(form + "/")
                while i != -1 and hit is None:
                    before = s[i - 1] if i > 0 else ""
                    if i not in judged and not (before and (_PATH_CHARS.match(before) or before in "/$~")):
                        judged.add(i)
                        tail = _PATH_TAIL.match(s, i + len(form)).group(0)
                        # A sentence's full stop is not part of the path: the harness's own error text reads
                        # "your current working directory is <run tree>." (five round-1 results). Never after
                        # a `/` or a `.`, so `<run tree>/..` still resolves outside it.
                        full = posixpath.normpath(real + re.sub(r"(?<=[^/.])[.:,]+$", "", tail))
                        if not (_under(full, allowed) or any(h.match(full) for h in harness)):
                            hit = label + _masked_harness_tail(tail, slugs, sid)
                    i = s.find(form + "/", i + 1)
                if hit:
                    break
            if hit:
                seen.append(hit[:160])
    return seen


def inherited_context(path: Path) -> list[str]:
    """What the session was given from OUTSIDE its checkout, read from what the harness recorded.

    REVIEW 11, F3. The driver proves before a take that no CLAUDE.md sits above the checkout. That is
    a prediction about one filename on one chain of directories, and instruction text reaches a
    session by other roads -- user-scope files loaded from a fixed location, extra working directories
    granted by user settings. So this reads the session's own record after the fact:

      every instruction file it loaded lives inside the working directory it opened in
      it was granted no additional working directory
      it was offered no tool from an account connector (`mcp__...`), which would put the operator's
        own services -- mail, calendar, files -- within reach of the session under test

    Each is the operator's side of the take, so a hit makes the take invalid rather than a result.
    """
    wd = None
    files: list[str] = []
    extra: list[str] = []
    connectors: list[str] = []
    for line in path.read_text(errors="replace").splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(rec, dict) or rec.get("type") != "attachment":
            continue
        att = rec.get("attachment") or {}
        kind = att.get("type")
        if kind == "environment":
            snap = att.get("snapshot") or {}
            if wd is None:
                wd = snap.get("workingDirectory")
            for d in snap.get("additionalWorkingDirectories") or []:
                if d not in extra:
                    extra.append(d)
        elif kind == "instructions":
            files.extend(f.get("path", "") for f in att.get("files") or [])
        elif kind == "deferred_tools_delta":
            connectors.extend(n for n in att.get("addedNames") or [] if n.startswith("mcp__"))

    out = []
    if wd is None:
        out.append("the transcript records no working directory, so what it loaded cannot be placed")
    else:
        root = wd.rstrip("/\\") + os.sep
        out += [f"an instruction file from outside the checkout: {f}"
                for f in files if not f.startswith(root)]
    out += [f"an additional working directory outside the checkout: {d}" for d in extra]
    if connectors:
        out.append(f"{len(connectors)} account-connector tool(s) offered, first {connectors[0]}")
    return out


def published_email_problems(path: Path) -> list[str]:
    """Ruling 10: a published transcript does not carry the account's email address field.

    Claude Code injects the signed-in account's email address into every session. The repository
    owner ruled that a published transcript has that one field removed, by scrub.py at copy time,
    so a transcript still carrying it is not in the published form the pre-registration fixes -- and
    the address is the operator's own.
    """
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        att = rec.get("attachment") if isinstance(rec, dict) else None
        ctx = att.get("context") if isinstance(att, dict) else None
        if (isinstance(att, dict) and att.get("type") == "session_context"
                and isinstance(ctx, dict) and "userEmail" in ctx):
            return ["[account-email] the published transcript still carries session_context.userEmail, which "
                    "Ruling 10 removes at copy time (scrub.py)"]
    return []


def expected_source_for(half: dict, project: str) -> str:
    """The source path the driver hands the agent for this half, from the fixture kind.

    Data, not a constant here: `source_by_fixture_kind` in the pre-registration. The driver builds the
    same path (`drive.py`), and a take's ledger records the one it sent, which check() compares.
    """
    kinds = prereg.load().get("source_by_fixture_kind") or {}
    tmpl = kinds.get((half.get("fixture") or {}).get("kind"))
    return tmpl.replace("{project}", project) if tmpl else ""


def render(line: str, project: str, source: str) -> str:
    """A scripted line as the driver sends it for this take."""
    return line.replace("{project}", project).replace("{source}", source)


def _ledger_beside(path: Path) -> dict | None:
    try:
        return json.loads((path.parent / "driver-ledger.json").read_text())
    except (OSError, json.JSONDecodeError):
        return None


def model_problems(path: Path, expected: str) -> list[str]:
    """REVIEW 12, BLOCKER 3. Every assistant record must carry the model the attempt is registered to.

    The counts are published per model, and the session id alone does not bind one: anyone can
    compute it from the row's commit and open a session with it under another model.
    """
    seen: dict = {}
    for line in path.read_text(errors="replace").splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(rec, dict) and rec.get("type") == "assistant":
            if rec.get("isApiErrorMessage") is True:
                continue
            m = (rec.get("message") or {}).get("model")
            seen[m] = seen.get(m, 0) + 1
    others_seen = sorted(str(m) for m in seen if m != expected)
    if others_seen:
        return [f"[model-binding] the transcript's assistant records carry {others_seen}, and this "
                f"attempt is registered to {expected!r}. The counts are published per model, so a "
                f"session on another model is not this cell's take."]
    return []


def agent_turn_count(path: Path) -> int:
    """Assistant records with text that the model wrote (review 13, F1).

    The harness writes an assistant-role record of its own when it reports an API error: model
    `<synthetic>`, `isApiErrorMessage: true` (verification/api-error-probe.txt). It is not the model
    speaking, so it neither binds a model nor counts as the agent's first turn.
    """
    n = 0
    for line in path.read_text(errors="replace").splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(rec, dict) or rec.get("type") != "assistant" or rec.get("isApiErrorMessage") is True:
            continue
        content = (rec.get("message") or {}).get("content")
        if isinstance(content, list) and any(isinstance(b, dict) and b.get("type") == "text" and (b.get("text") or "").strip()
                                             for b in content):
            n += 1
        elif isinstance(content, str) and content.strip():
            n += 1
    return n


def last_stop_reason(path: Path) -> str | None:
    """The stop reason of the last assistant record that carries one."""
    out = None
    for line in path.read_text(errors="replace").splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(rec, dict) or rec.get("type") != "assistant":
            continue
        sr = (rec.get("message") or {}).get("stop_reason")
        if sr:
            out = sr
    return out


def completion_problems(path: Path, ledger: dict | None, pre: dict | None = None) -> list[str]:
    """REVIEW 18, BLOCKER 2 and REVIEW 19, BLOCKER 1. A take the driver CUT may not publish as one
    that finished, and the reading is against the driver's own vocabulary rather than one spelling.

    `timed-out` and `aborted` are assigned from the ledger's outcome before any grader reads a turn.
    The first version of this check read that outcome only where it OPENED WITH `complete`, so the
    field could be deleted, blanked, miscased or written as any other word, and a take cut at its
    probe turn was graded from a partial reply with every committed check clean. Enumerating the
    shapes a reviewer wrote down leaves the next spelling open, so the binding reads the other way
    round: the outcome must be one the pinned driver writes (`driver_outcome_shapes`), and anything
    else is refused.

    Then both directions. A turn row carries an exit code, and a non-zero one means the driver cut
    the take: 124 is `timed-out`, anything else is `aborted`. A take not recorded as cut must end its
    last reply at the end of a turn. That reading is measured, not assumed: every one of the eleven
    committed walks ends its last assistant record at `end_turn`, and the one cut attempt on record
    (rehearsals/plan-gate/1) ends at `tool_use`.
    """
    if ledger is None:
        return []
    pre = prereg.load() if pre is None else pre
    shapes = tuple(pre.get("driver_outcome_shapes") or ())
    if not shapes:
        return []
    outcome = ledger.get("outcome")
    if not isinstance(outcome, str) or not outcome.startswith(shapes):
        return [f"[outcome-binding] the ledger records the outcome {outcome!r}, which is not one the "
                f"pinned driver writes. A take whose outcome the driver did not write is graded from a "
                f"reply nobody can say it finished."]

    out: list[str] = []
    # A pause and a death before the first agent turn ARE non-zero exits; that is what they record.
    routed = outcome.startswith(("PAUSE", "REHEARSAL"))
    if not routed:
        for row in ledger.get("turns") or []:
            code = row.get("exit")
            if not isinstance(code, int):
                out.append(f"[outcome-binding] turn {row.get('n')} records no exit code, and the driver "
                           f"writes one for every turn it sends")
                break
            if code == 0:
                continue
            want = "timed-out" if code == 124 else "aborted"
            if not outcome.startswith(want):
                out.append(f"[outcome-binding] the ledger records {outcome!r} and its own turn "
                           f"{row.get('n')} exited {code}; the driver publishes that take as {want}, and "
                           f"a take it cut is not one that finished")
            break

    if not outcome.startswith(("timed-out", "aborted", "PAUSE", "REHEARSAL")):
        sr = last_stop_reason(path)
        # REVIEW 21, F2. With no record carrying the field the reading passed having measured nothing,
        # and a harness version that stops writing it would leave every take's finish unproven. The
        # same shape as the prompt-snapshot rule: a take must carry what the check reads.
        if sr is None and agent_turn_count(path) > 0:
            out.append("[outcome-binding] no assistant record in this take carries a stop reason, so "
                       "nothing shows whether its last reply ended or was cut")
        if sr and sr != "end_turn":
            out.append(f"[outcome-binding] the ledger records {outcome!r} and the transcript's last "
                       f"reply stopped at {sr!r} rather than at the end of a turn. Every committed walk "
                       f"ends its last reply at the end of a turn; a cut one does not.")

    # REVIEW 20, BLOCKER 1. The binding read ONE WAY: a non-zero exit forced a cut outcome, and a
    # completed outcome forced a finished last reply, but a CUT outcome forced nothing. So one edit of
    # this field on a finished take published a behavioural failure -- the thing the study counts -- as
    # a failure of the harness, with every exit code still zero and every check clean. A cell reading
    # "2 of 3, one timed-out" tells a reader the model would have held but for the budget; "2 of 3, one
    # invented" tells them it did not. This is review 15's first blocker in the other reserved label.
    rows = ledger.get("turns") or []
    last = rows[-1] if rows else None
    no_session = "no session file" in outcome
    if outcome.startswith("timed-out") and not (last or {}).get("exit") == 124:
        out.append(f"[outcome-binding] the ledger publishes this take as timed-out and its own last "
                   f"turn records exit {(last or {}).get('exit')!r}; the driver writes 124 on the turn "
                   f"it cut at the budget")
    elif outcome.startswith("aborted") and not no_session:
        code = (last or {}).get("exit")
        failed_step = bool(((last or {}).get("then") or {}).get("failed"))
        if not ((isinstance(code, int) and code != 0) or failed_step):
            out.append(f"[outcome-binding] the ledger publishes this take as aborted and its own last "
                       f"turn records exit {code!r} with no failed then-step; the driver writes aborted "
                       f"only where a process died or the pre-registered then-step failed")
    if no_session and path.is_file():
        out.append(f"[outcome-binding] the ledger records that no session file was written and a "
                   f"transcript sits beside it; the driver appends that clause only when it found none")
    return out


def constant_problems(ledger: dict | None, pre: dict) -> list[str]:
    """REVIEW 12, BLOCKER 3. A take's budget and permission mode are the frozen constants."""
    if not ledger:
        return ["[constant-binding] a take with no driver ledger cannot show the turn budget and "
                "permission mode it ran under"]
    out = []
    want_budget = int(pre["budgets"]["turn_timeout_s"])
    want_mode = pre["driver_constants"]["permission_mode"]
    if ledger.get("budget_s") != want_budget:
        out.append(f"[constant-binding] the take ran with a {ledger.get('budget_s')}s turn budget and the "
                   f"pre-registered budget is {want_budget}s. Below it a turn is cut short; above it a "
                   f"slow turn the frozen file labels timed-out is graded instead.")
    if ledger.get("permission_mode") != want_mode:
        out.append(f"[constant-binding] the take ran in permission mode {ledger.get('permission_mode')!r}, "
                   f"not the pre-registered {want_mode!r}")
    # REVIEW 13, F3. The checkout is exported from HEAD; a take is bound to the gars tree the study froze.
    want_tree = pre["system_under_test"]["gars_tree_sha"]
    if ledger.get("gars_tree_sha") != want_tree:
        out.append(f"[constant-binding] the take ran against gars tree {str(ledger.get('gars_tree_sha'))[:12]}, "
                   f"and the pre-registration pins {want_tree[:12]}: a different system under test")
    return out


AUTO_MEMORY_MARK = "persistent file-based memory"


def memory_section_offered(path: Path) -> bool:
    """Whether the harness's system prompt offered the session a persistent memory folder.

    Found 11 September 2026 while review 12 ran: every headless session in both studies, the pilot
    included, carried Claude Code's auto-memory section pointing at a folder under the operator's
    home. The isolation flags do not remove it; `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` does, measured on
    a smoke with and without it. Read from the `prompt_snapshot` record, never from text the agent wrote.
    """
    for line in path.read_text(errors="replace").splitlines():
        if AUTO_MEMORY_MARK not in line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        att = rec.get("attachment") if isinstance(rec, dict) else None
        if isinstance(att, dict) and att.get("type") == "prompt_snapshot":
            return True  # the harness offered its auto-memory
    return False


def prompt_snapshot_present(path: Path) -> bool:
    """Whether the session recorded its system prompt at all (review 13, F5).

    memory_section_offered() reads one phrase in one record type, read at harness 2.1.267. If the
    harness stopped writing that record, the check would pass having read nothing, so a take must
    carry one.
    """
    snapshot_found = False
    for line in path.read_text(errors="replace").splitlines():
        if '"prompt_snapshot"' not in line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        att = rec.get("attachment") if isinstance(rec, dict) else None
        if isinstance(att, dict) and att.get("type") == "prompt_snapshot":
            snapshot_found = True
            break
    return snapshot_found


def user_text_records(path: Path, pre: dict) -> tuple[list[str], list[str], list[str]]:
    """(operator lines, harness-delivered texts, unknown-origin texts), in transcript order.

    FOUND ON WALK 1 OF confounded-design, 11 SEPTEMBER 2026. At harness 2.1.267 a background task's
    completion is reported to the agent inside the same headless turn, as a user-role record carrying
    `origin.kind: task-notification`. The shared transcript reader cannot tell it from a line the
    operator typed, so the checker counted it as a sixth operator line and refused the walk as the
    operator improvising. Every take whose agent started a background task would have gone the same way.

    So the operator's lines are read off the RECORDS: a user record with text and no origin is the
    operator's; one whose origin kind the pre-registration names (harness_delivered_user_records) is
    the harness's; any other origin refuses, because who sent it cannot be established.
    """
    kinds = set((pre.get("harness_delivered_user_records") or {}).get("origin_kinds") or [])
    ops: list[str] = []
    harness: list[str] = []
    unknown: list[str] = []
    for line in path.read_text(errors="replace").splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(rec, dict) or rec.get("type") != "user":
            continue
        msg = rec.get("message") if isinstance(rec.get("message"), dict) else rec
        content = msg.get("content")
        if tx._tool_results_from_content(content):
            continue
        text = tx._text_from_content(content)
        if not text.strip():
            continue
        origin = rec.get("origin")
        kind = origin.get("kind") if isinstance(origin, dict) else None
        if kind is None:
            ops.append(text)
        elif kind in kinds:
            harness.append(text)
        else:
            unknown.append(f"{kind}: {text[:60]}")
    return ops, harness, unknown


def required_steps(steps: list[dict], path: Path, turns: list[dict], is_walk: bool,
                   expected_project: str, expected_source: str,
                   harness: list[str] | tuple = ()) -> tuple[list[dict], list[str]]:
    """The scripted lines this transcript must carry, and any problem with where the driver stopped.

    A walk carries each pre-probe line. A take carries each line up to the last one the driver sent
    and none after it: the driver sends nothing past an unheld marker, a timeout or an abort, and the
    take is still graded (requirement 4). The first version required every line whatever happened,
    so a take that stopped correctly failed as `never sent`, and `did-not-reach` had no valid
    transcript to be published from.

    The stop is read from the driver ledger, which is the operator's own record, so it is not taken
    on trust: for an unheld marker the transcript must show the marker absent from the agent's text
    after that line. A driver that stopped at a held wait point would manufacture `did-not-reach`.
    """
    if is_walk:
        return steps, []
    ledger_path = path.parent / "driver-ledger.json"
    if not ledger_path.is_file():
        return steps, []
    try:
        ledger = json.loads(ledger_path.read_text())
    except (OSError, json.JSONDecodeError):
        return steps, []
    outcome = ledger.get("outcome") or ""
    if outcome.startswith("complete"):
        return steps, []
    sent = [r.get("n") for r in ledger.get("turns") or [] if not r.get("recovery")]
    sent = [n for n in sent if isinstance(n, int)]
    if not sent:
        return steps, []
    last = max(sent)
    required = [s for s in steps if s["n"] <= last]
    problems: list[str] = []
    if outcome.startswith("stopped"):
        step = next((s for s in steps if s["n"] == last), None)
        marker = (step or {}).get("marker")
        rec = (step or {}).get("recovery")
        if not marker:
            # REVIEW 15, BLOCKER 1. Every task's probe turn carries no marker, so a `stopped` outcome
            # whose last line is the probe was proven by nothing and published `did-not-reach` from the
            # ledger alone. The driver cannot stop there: a step with no marker always holds.
            problems.append(f"[stop-without-a-wait-point] the ledger records a stop at operator turn "
                            f"{last}, which carries no wait point to hold; the driver stops only where a "
                            f"marker was not held, so this is a state it cannot produce")
        else:
            want = normalise(render(step["line"], expected_project, expected_source))
            idx = max((i for i, x in enumerate(turns)
                       if x["role"] == "user" and want and normalise(x["text"]) == want),
                      default=None)
            after = ("\n".join(x["text"] for x in turns[idx + 1:] if x["role"] == "assistant")
                     if idx is not None else "")
            send = normalise(render(rec["send"], expected_project, expected_source)) if rec else None
            if marker in after:
                problems.append(f"[stop-at-held-marker] the driver stopped at operator turn {last} "
                                f"because its marker was not held, and the marker {marker!r} is in the "
                                f"agent's reply after that line. A stop at a held wait point "
                                f"manufactures `did-not-reach`.")
            if rec and idx is not None:
                sent_recovery = any(x["role"] == "user" and normalise(x["text"]) == send
                                    for x in turns[idx + 1:])
                if not sent_recovery and rec["if_reply_holds"] in after:
                    problems.append(f"[stop-at-held-marker] the driver stopped at operator turn {last} with no "
                                    f"recovery sent, and the reply holds the recovery's own marker "
                                    f"{rec['if_reply_holds']!r}; withholding a pre-registered recovery "
                                    f"manufactures `did-not-reach`.")
            if idx is not None:
                # The driver sends nothing past an unheld marker, so a further line means the ledger's
                # `stopped` is not what happened (review 15, blocker 1).
                extra = [x for x in turns[idx + 1:]
                         if x["role"] == "user" and x["text"].strip() and x["text"] not in harness
                         and (send is None or normalise(x["text"]) != send)]
                if extra:
                    problems.append(f"[stop-without-a-wait-point] the ledger records a stop at operator "
                                    f"turn {last} and {len(extra)} further operator line(s) were sent; the "
                                    f"driver sends nothing past an unheld marker")
    return required, problems


def operator_line_problems(ops: list[str], steps: list[dict], expected_project: str,
                           expected_source: str) -> list[str]:
    """The operator's turns against the script: each step's line, in order, once; then at most
    `at_most` sends of THAT step's pre-registered recovery; and nothing else.

    WHOLE LINES, RENDERED AS THE DRIVER RENDERS THEM (review 12, blocker 1). The first version matched
    a line's head with the per-take path blanked out and tested containment. scope-read's probe puts
    text after its path, so its head was in no line the driver sends and that whole row could never
    pass; and the head of the `05` turn is two characters, which a source path carrying the neutral name
    contains about one take in forty, so a fired recovery read as the line sent twice. Each turn is now
    compared for equality, after whitespace normalisation, with the line rendered from this take's
    project and the source its fixture kind implies.

    FOUND 11 SEPTEMBER 2026, BEFORE ANY TAKE. A recovery is a real operator turn, sent by the driver
    from the frozen file; it is admitted only where the file attaches one, immediately after its step,
    at most `at_most` times, and only as its rendered `send`.
    """
    problems: list[str] = []
    norm = [normalise(o) for o in ops]
    lines = [normalise(render(s["line"], expected_project, expected_source)) for s in steps]
    unexplained: list[int] = []
    i = 0
    for idx, step in enumerate(steps):
        want = lines[idx]
        nxt = lines[idx + 1] if idx + 1 < len(lines) else None

        def is_next(k: int) -> bool:
            return nxt is not None and norm[k] == nxt

        if not want:
            problems.append("[operator-lines] " + f"operator turn {step['n']} renders to nothing; the script is broken")
            continue
        pos = next((k for k in range(i, len(ops)) if norm[k] == want), None)
        if pos is None:
            problems.append("[operator-lines] " + f"operator turn {step['n']} was never sent: {want[:70]!r}")
            continue
        unexplained.extend(range(i, pos))
        i = pos + 1
        while i < len(ops) and norm[i] == want and not is_next(i):
            problems.append("[operator-lines] " + f"operator turn {step['n']} was sent twice; it is sent once")
            i += 1
        rec = step.get("recovery")
        if rec:
            at_most = int(rec.get("at_most", 1))
            send = normalise(render(rec["send"], expected_project, expected_source))
            used = 0
            while i < len(ops) and norm[i] == send and not is_next(i):
                used += 1
                if used > at_most:
                    problems.append("[operator-lines] " + f"the recovery for operator turn {step['n']} was sent {used} "
                                    f"times and the frozen file allows {at_most}; a recovery that "
                                    f"repeats is the operator improvising")
                i += 1
    unexplained.extend(range(i, len(ops)))
    for k in unexplained:
        problems.append("[operator-lines] " + f"operator turn {k + 1} is not on the script: {ops[k][:70]!r}. A line that "
                        f"is not on the script is the operator improvising.")
    return problems


def checkout_problems(path: Path, pre: dict) -> list[str]:
    """The checkout the session opened in, from the session's own record of its git status (review 14, blocker 3).

    The session id is computable by anyone from a row's commit, so a session could be opened by hand in a
    doctored checkout. The session records the git status it was shown, and the driver's checkout has a
    fixed shape: its own identity, a clean status and one commit with a neutral subject.
    """
    rl = pre["run_location"]
    gs = ""
    for line in path.read_text(errors="replace").splitlines():
        if '"session_context"' not in line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        att = rec.get("attachment") if isinstance(rec, dict) else None
        if isinstance(att, dict) and att.get("type") == "session_context":
            gs = (att.get("context") or {}).get("gitStatus") or ""
            break
    if not gs:
        return ["[checkout-binding] the session recorded no git status, so the checkout it opened in cannot be shown"]
    user = re.search(r"^Git user: (.*)$", gs, re.M)
    status = gs.split("Status:", 1)[1].split("Recent commits:", 1)[0].strip() if "Status:" in gs and "Recent commits:" in gs else None
    commits = gs.split("Recent commits:", 1)[1].strip().splitlines() if "Recent commits:" in gs else []
    checkout_ok = (user is not None and user.group(1).strip() == rl["checkout_identity"] and status == "(clean)"
                   and len(commits) == 1 and commits[0].strip().endswith(" " + rl["checkout_subject"]))
    if not checkout_ok:
        return [f"[checkout-binding] the session's git status is not the driver's checkout (git user "
                f"{rl['checkout_identity']}, a clean status, one commit named {rl['checkout_subject']!r})"]
    return []


def instruction_content_problems(path: Path) -> list[str]:
    """The instruction files the session loaded, bound to this repository's bytes (review 14, blocker 3).

    The path alone was checked, so a session opened in a checkout whose root CLAUDE.md said something
    the study did not pin passed. The harness records each file's content; it equals the file in the
    pinned tree with its trailing newline dropped (measured on both built-checkout walks), so the bytes
    are compared with trailing whitespace ignored. The freeze pins the root CLAUDE.md and the gars tree.
    """
    wd = None
    files: list[dict] = []
    for line in path.read_text(errors="replace").splitlines():
        if '"attachment"' not in line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        att = rec.get("attachment") if isinstance(rec, dict) else None
        if not isinstance(att, dict):
            continue
        if att.get("type") == "environment" and wd is None:
            wd = (att.get("snapshot") or {}).get("workingDirectory")
        elif att.get("type") == "instructions":
            files.extend(att.get("files") or [])
    if not files:
        return ["[checkout-binding] the session recorded no instruction file, so what it was told cannot be shown"]
    if wd is None:
        return ["[checkout-binding] the session recorded no working directory, so its instruction files cannot be placed"]
    out: list[str] = []
    for f in files:
        try:
            rel = Path(f.get("path") or "").relative_to(Path(wd))
        except ValueError:
            continue  # outside the checkout: inherited_context reports it
        repo_file = REPO / rel
        if not repo_file.is_file():
            out.append(f"[checkout-binding] the session loaded {rel}, which the pinned tree does not carry")
            continue
        file_text = repo_file.read_text(errors="replace")
        if file_text.rstrip() != (f.get("content") or "").rstrip():
            out.append(f"[checkout-binding] the session loaded {rel} with content other than the pinned tree's; "
                       f"the agent was told something the study did not pin")
    return out


def continuation_problems(turns: list[dict], steps: list[dict], harness: list[str], project: str,
                          source: str) -> list[str]:
    """Every line the operator sent after a wait point, proven against the reply before it (review 13, blocker 2).

    Ruling 12 proved a stop: a take the driver stopped at an unheld marker must show the marker absent.
    Nothing proved a continuation, so a take driven past an unheld marker -- which the frozen file labels
    `did-not-reach` -- passed as complete with its probe answer graded, on the driver's word that each
    marker held. Now, for each step with a marker that is followed by a further line, the marker must be in
    the agent's text between that step's line and the next; where a recovery was sent, the recovery's own
    marker must be in the reply before it, the step's marker absent there, and the step's marker in the
    reply after it. These are what `stopped_take_rule` and the recovery rule say happened.
    """
    ops = [(i, normalise(x["text"])) for i, x in enumerate(turns)
           if x["role"] == "user" and x["text"].strip() and x["text"] not in harness]

    def text_between(a: int, b: int) -> str:
        return "\n".join(x["text"] for x in turns[a + 1:b] if x["role"] == "assistant" and x["text"])

    positions = []
    k = 0
    for s in steps:
        want = normalise(render(s["line"], project, source))
        while k < len(ops) and ops[k][1] != want:
            k += 1
        if k >= len(ops):
            break
        line_pos = ops[k][0]
        k += 1
        rec_pos = None
        rec = s.get("recovery")
        if rec and k < len(ops) and ops[k][1] == normalise(render(rec["send"], project, source)):
            rec_pos = ops[k][0]
            k += 1
        positions.append((s, line_pos, rec_pos))

    out: list[str] = []
    for idx, (s, line_pos, rec_pos) in enumerate(positions[:-1]):
        marker = s.get("marker")
        nxt = positions[idx + 1][1]
        if rec_pos is not None:
            before, after = text_between(line_pos, rec_pos), text_between(rec_pos, nxt)
            if s["recovery"]["if_reply_holds"] not in before:
                out.append(f"[continued-past-unheld-marker] operator turn {s['n']}'s recovery was sent, and the "
                           f"reply before it does not hold {s['recovery']['if_reply_holds']!r}")
            if marker and marker in before:
                out.append(f"[continued-past-unheld-marker] operator turn {s['n']}'s recovery was sent after a "
                           f"reply that already held the step's marker")
            if marker and marker not in after:
                out.append(f"[continued-past-unheld-marker] operator turn {positions[idx + 1][0]['n']} was sent, "
                           f"and no reply to turn {s['n']} holds its marker {marker!r}")
        elif marker and marker not in text_between(line_pos, nxt):
            out.append(f"[continued-past-unheld-marker] operator turn {positions[idx + 1][0]['n']} was sent, and "
                       f"the reply to turn {s['n']} does not hold its marker {marker!r}; the frozen file labels "
                       f"that take did-not-reach")
    return out


def fixture_binding_problems(path: Path, half: dict, is_walk: bool = True) -> tuple[list[str], str | None]:
    """The fixture the driver built, from its ledger beside the transcript, against this half's spec.

    The fixture is what defines the half. For three tasks the halves share one fixture and the check is
    vacuous; for confounded-design the halves differ in their generated tree, and for
    precondition-refusal in the project variant (review 12, F1), so a take pointed at the other half's
    fixture measures the other experiment. Returns (problems, note): a note where the comparison could
    not be made, so a silent pass is never printed for it.
    """
    ledger_path = path.parent / "driver-ledger.json"
    spec = half.get("fixture") or {}
    # REVIEW 19, BLOCKER 3. The copied-tree fixture carries its pin as the tree hash and the freeze
    # leaves `sha256` null for that kind by design, so this read nothing for plan-gate: after the
    # freeze all eighteen of its takes would have printed "unpinned until the freeze" and been bound
    # to no fixture at all, under a spec that says it is pinned there.
    pinned = spec.get("sha256") or spec.get("tree_sha256_name_invariant")
    if not ledger_path.is_file():
        return [], "no driver ledger beside the transcript, so the fixture binding was not checked"
    try:
        ledger = json.loads(ledger_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return [f"[fixture-binding] the driver ledger beside the transcript is unreadable ({exc!r})"], None
    fx = ledger.get("fixture") or {}
    if spec.get("kind") == "project":
        if not fx:
            if is_walk:
                return [], "this walk predates the project fixture record, so its variant was not checked"
            return [f"[fixture-binding] a take on a project fixture must record the variant it built and "
                    f"stage 01's exit on it"], None
        out = []
        if fx.get("variant") != spec.get("variant"):
            out.append(f"[fixture-binding] the driver built the {fx.get('variant')!r} project and this "
                       f"half's fixture is {spec.get('variant')!r}. The take measures the other half.")
        if fx.get("stage01_check_exit") is None or fx.get("stage01_check_exit") != fx.get("stage01_expected_exit"):
            out.append(f"[fixture-binding] stage 01 --check exited {fx.get('stage01_check_exit')} on the "
                       f"built project, not the {fx.get('stage01_expected_exit')} its variant is built to reach")
        return out, None
    # REVIEW 16, F7: `fixture_sha256` is what a generated fixture's builder records, from the manifest
    # the generator wrote for the bytes of that build.
    got = fx.get("tree_sha256_name_invariant") or fx.get("sha256") or fx.get("fixture_sha256")
    if not got:
        # REVIEW 17, F2. A missing hash was a note on every kind but `project`, before and after the
        # freeze, so deleting the fixture block from a take's ledger removed the binding with every
        # check clean. Once the half's fixture is pinned, its absence is a refusal.
        if pinned and not is_walk:
            return [f"[fixture-binding] this take's ledger records no fixture hash, and the half's "
                    f"fixture is pinned at {pinned[:12]}. A take that cannot be bound to the fixture "
                    f"it ran against is not graded."], None
        return [], "the driver ledger records no fixture hash, so the fixture binding was not checked"
    if not pinned:
        if prereg.is_frozen() and not is_walk:
            return [f"[fixture-binding] the frozen file pins no fixture for this half, so this take "
                    f"(built {got[:12]}) is bound to nothing. A binding the freeze was meant to fill "
                    f"and did not is a check that passes having measured nothing."], None
        return [], (f"the fixture binding is unpinned until the freeze (the driver built "
                    f"{got[:12]}; the pre-registration pins nothing yet)")
    if got != pinned:
        return [f"[fixture-binding] the fixture the driver built ({got[:12]}) is not this half's pinned fixture "
                f"({pinned[:12]}). The take measures the other experiment."], None
    return [], None


# ---- the environment record ---------------------------------------------------------------------------
#
# DECISION 4. The bill was a statement in round 1 (Ruling 34): nothing a take left behind showed it ran on
# the subscription rather than a per-token key. The driver now writes environment.json beside each
# transcript, before the first turn: the NAMES of the variables its session started with that match the
# published vocabulary, the presence of each fixed billing name, and the credential source the harness
# reported on each turn. This reads that record against the pre-registration's `environment_record` block.
#
# NEVER ON THE SOURCE'S VALUE. A refusal files the attempt as a rehearsal and frees its slot, so a check that
# refused a take for the credential source it reported would be a retake route for a take someone wanted
# gone. The driver stops a non-subscription run under the money line; this checks the record is whole and is
# this take's, and nothing about what it says.
#
# NEVER A VALUE IN A REFUSAL. A string that is not a variable name may be a value written where a name
# belongs, so the refusal gives its position and length and not the string.

ENVIRONMENT_RECORD_KEYS = ("record", "schema", "session_id", "row", "row_commit", "task", "half",
                           "model_requested", "claude_version", "written_before_first_turn", "name_patterns",
                           "names_present", "stripped_names", "api_key_variables", "api_key_set",
                           "billing_route_variables", "billing_route_set", "subscription_token_variables",
                           "credential_source")
VARIABLE_NAME = re.compile(r"^[A-Z_][A-Z0-9_]*$")
PRESENCE_STATES = ("absent", "empty", "set")
FIXED_NAME_LISTS = (("api_key_variables", "api_key_set"), ("billing_route_variables", "billing_route_set"),
                    ("subscription_token_variables", None))
SHA1_HEX = re.compile(r"^[0-9a-f]{40}$")


def matched_by(name: str, patterns: dict) -> str | None:
    """The published group a variable name matches: re.search, case-sensitive, the harness group first."""
    for group in ("harness", "generic"):
        if any(re.search(p, name) for p in patterns.get(group) or []):
            return group
    return None


def never_stripped(name: str, patterns: dict, fixed: set) -> bool:
    """A name the driver may never strip: one a HARNESS pattern matches, or one on the three fixed lists.

    The generic shape is not in this rule, as in drive.never_stripped_problems: it is a recording catch-all, and
    one of J4's twelve inherited session names (CLAUDE_CODE_MESSAGING_TOKEN) has its shape. Found in integration,
    13 September 2026: the first version refused a name any group matched, so every record written under J4 was
    refused.
    """
    return matched_by(name, patterns) == "harness" or name in fixed


def environment_problems(path: Path, ledger: dict | None, pre: dict, row_commit: str | None) -> list[str]:
    """The environment record beside a transcript, against the pre-registration. `path` is the transcript or
    its folder; `row_commit` is the sha of the commit that introduced the take's row, or None for a walk."""
    out: list[str] = []

    def refuse(sentence: str) -> None:
        out.append("[environment-record] " + sentence)

    spec = pre.get("environment_record")
    if not isinstance(spec, dict):
        refuse("the pre-registration carries no environment_record block, so no record can be checked against it")
        return out
    folder = path if path.is_dir() else path.parent
    transcript = folder / "transcript.jsonl" if path.is_dir() else path
    name = spec.get("file") or "environment.json"
    rec_path = folder / name
    if not rec_path.is_file():
        refuse(f"no {name} beside the transcript. A take that does not carry the record of the environment its "
               f"session started in cannot show which credentials it ran with, so the bill is a statement again.")
        return out
    try:
        raw = rec_path.read_bytes()
        rec = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        refuse(f"{name} is unreadable ({type(exc).__name__}), so the environment it records cannot be read")
        return out
    if not isinstance(rec, dict):
        refuse(f"{name} holds a {type(rec).__name__}, not the object the driver writes")
        return out

    missing = [k for k in ENVIRONMENT_RECORD_KEYS if k not in rec]
    extra = [k for k in rec if k not in ENVIRONMENT_RECORD_KEYS]
    if missing or extra:
        shown = [k for k in extra if re.fullmatch(r"[a-z_][a-z0-9_]*", k)]
        refuse(f"{name} does not carry exactly the schema-{spec.get('schema')} keys: missing {missing}, "
               f"{len(extra)} not in the schema {shown}. The record is replaced whole, never merged.")
        return out
    if rec["schema"] != spec.get("schema"):
        refuse(f"{name} is schema {rec['schema']!r} and the pre-registration fixes schema {spec.get('schema')!r}")
    if rec["written_before_first_turn"] is not True:
        refuse(f"{name} does not record that it was written before the first turn")

    patterns = spec.get("name_patterns") or {}
    if rec["name_patterns"] != patterns:
        refuse(f"{name} records name patterns other than the pre-registration's; the names it lists were "
               f"matched against a vocabulary nobody published")

    if transcript.is_file():
        sid, whose = session_id_of(transcript), "this transcript's"
    else:
        # NO TRANSCRIPT. run.py and check_results.py --ledger grade such a take from its ledger alone, so the
        # record is bound to the session id the driver wrote there. A transcript that exists and records no
        # session id is still refused above, by the transcript branch.
        sid, whose = str((ledger or {}).get("session_id") or ""), "the ledger's (no transcript sits beside it)"
    if rec["session_id"] != sid:
        refuse(f"{name} records a session id that is not {whose} ({sid or 'none recorded'}); it is "
               f"another session's record")
    if not (rec["row_commit"] is None or (isinstance(rec["row_commit"], str) and SHA1_HEX.match(rec["row_commit"]))):
        refuse(f"{name} records a row commit that is neither null nor a 40-hex sha")
    elif row_commit is not None and rec["row_commit"] != row_commit:
        refuse(f"{name} records the row commit {str(rec['row_commit'])[:12]} and this take's row was introduced by "
               f"{row_commit[:12]}; the record belongs to another row")
    if not (rec["row"] is None or (isinstance(rec["row"], int) and not isinstance(rec["row"], bool))):
        refuse(f"{name} records a row that is neither null nor an integer")

    if not isinstance(ledger, dict):
        refuse(f"no driver ledger beside the transcript binds {name}'s bytes")
    else:
        want = {"file": name, "sha256": hashlib.sha256(raw).hexdigest()}
        if ledger.get("environment") != want:
            refuse(f"the driver ledger does not record {name} with the sha256 of its bytes "
                   f"({want['sha256'][:12]}); a record edited after the take, or another take's, is not bound")
        if rec["claude_version"] != ledger.get("claude_version"):
            refuse(f"{name} records harness {rec['claude_version']!r} and the ledger records "
                   f"{ledger.get('claude_version')!r}")
        for key in ("task", "half", "model_requested"):
            if rec[key] != ledger.get(key):
                refuse(f"{name} records {key} {rec[key]!r} and the ledger records {ledger.get(key)!r}")

    listed: list[str] = []
    entries = rec["names_present"]
    if not isinstance(entries, list):
        refuse(f"{name}'s names_present is not a list")
        entries = []
    for i, e in enumerate(entries):
        if not (isinstance(e, dict) and set(e) == {"name", "matched_by"} and isinstance(e.get("name"), str)):
            refuse(f"entry {i} of names_present is not a {{name, matched_by}} pair")
            continue
        n = e["name"]
        if not VARIABLE_NAME.match(n):
            refuse(f"entry {i} of names_present is not a variable name ({len(n)} characters, not shown). The "
                   f"record carries names only, and a value written where a name belongs is refused unprinted.")
            continue
        group = matched_by(n, patterns)
        if group is None:
            refuse(f"entry {i} of names_present matches no published pattern ({len(n)} characters, not shown); "
                   f"the record lists only names the vocabulary matches")
            continue
        if e["matched_by"] != group:
            refuse(f"names_present records {n} as matched by {e['matched_by']!r}; the published patterns, "
                   f"harness first, match it as {group!r}")
        listed.append(n)
    if listed != sorted(set(listed)):
        refuse(f"{name}'s names_present is not sorted by name with each name once")

    stripped = rec["stripped_names"]
    allowed = (pre.get("driver_constants") or {}).get("stripped_env")
    fixed = {n for key, _ in FIXED_NAME_LISTS for n in (spec.get(key) or [])}
    if not (isinstance(stripped, list) and all(isinstance(n, str) for n in stripped)):
        refuse(f"{name}'s stripped_names is not a list of names")
    else:
        if stripped != sorted(set(stripped)):
            refuse(f"{name}'s stripped_names is not sorted with each name once")
        for i, n in enumerate(stripped):
            if not VARIABLE_NAME.match(n):
                refuse(f"entry {i} of stripped_names is not a variable name ({len(n)} characters, not shown)")
            elif never_stripped(n, patterns, fixed):
                refuse(f"stripped_names holds {n}, which the published vocabulary names; a login or billing "
                       f"variable is never stripped")
            elif not isinstance(allowed, list) or n not in allowed:
                refuse(f"stripped_names holds {n}, which driver_constants.stripped_env does not list")

    for list_key, set_key in FIXED_NAME_LISTS:
        want_names = spec.get(list_key)
        got = rec[list_key]
        if not isinstance(want_names, list):
            refuse(f"the pre-registration's environment_record carries no {list_key} list")
            continue
        if not isinstance(got, dict):
            refuse(f"{name}'s {list_key} is not a name-to-state object")
            continue
        absent_names = [n for n in want_names if n not in got]
        extra_n = sum(1 for n in got if n not in want_names)
        if absent_names or extra_n:
            refuse(f"{name}'s {list_key} is not exactly the pre-registered list: missing {absent_names}, "
                   f"{extra_n} name(s) not on it")
        bad = [n for n in want_names if n in got and got[n] not in PRESENCE_STATES]
        if bad:
            refuse(f"{name}'s {list_key} records {bad} in a state other than absent, empty or set (not shown)")
        if set_key is not None:
            truth = any(got.get(n) == "set" for n in want_names)
            if rec[set_key] is not truth:
                refuse(f"{name} records {set_key} {rec[set_key]!r} and its own {list_key} "
                       f"{'has' if truth else 'has no'} name set; the flag is what the list shows")
        for n in want_names:
            state = got.get(n)
            if state in ("empty", "set") and n not in listed and matched_by(n, patterns):
                refuse(f"{name}'s {list_key} records {n} as {state} and names_present does not list it")
            elif state == "absent" and n in listed:
                refuse(f"names_present lists {n} and {name}'s {list_key} records it absent")

    cs = rec["credential_source"]
    if not (isinstance(cs, dict) and set(cs) == {"key", "per_turn", "reported"}):
        refuse(f"{name}'s credential_source is not {{key, per_turn, reported}}")
        return out
    if cs["key"] != spec.get("credential_source_key"):
        refuse(f"{name}'s credential_source reads {cs['key']!r}; the pre-registration reads "
               f"{spec.get('credential_source_key')!r}")
    if not (cs["reported"] is None or isinstance(cs["reported"], str)):
        refuse(f"{name}'s credential_source.reported is neither null nor a string")
    per_turn = cs["per_turn"]
    if not isinstance(per_turn, list) or not all(
            isinstance(t, dict) and set(t) == {"n", "recovery", "exit", "apiKeySource"}
            and (t["apiKeySource"] is None or isinstance(t["apiKeySource"], str)) for t in per_turn):
        refuse(f"{name}'s credential_source.per_turn is not a list of {{n, recovery, exit, apiKeySource}} "
               f"entries with a string or null source")
    elif isinstance(ledger, dict):
        ours = collections.Counter((t["n"], bool(t["recovery"])) for t in per_turn)
        theirs = collections.Counter((r.get("n"), bool(r.get("recovery")))
                                     for r in ledger.get("turns") or [] if isinstance(r, dict))
        if ours != theirs:
            refuse(f"{name}'s credential_source.per_turn records {len(per_turn)} turn(s) and the ledger "
                   f"{sum(theirs.values())}; they are not one to one by (n, recovery), so a turn's source is "
                   f"missing or invented")
    return out


def check(path: Path, task_id: str, half_name: str, row_index: int | None,
          is_walk: bool) -> list[str]:
    problems: list[str] = []
    spec = prereg.task(task_id)
    half = spec[half_name]
    pre = prereg.load()

    data = tx.load(path)
    turns = data["turns"]
    ops, harness, unknown = user_text_records(path, pre)
    joined = normalise(" ".join(ops)).lower()

    n_user = sum(1 for t in turns if t["role"] == "user" and t["text"].strip())
    if n_user != len(ops) + len(harness) + len(unknown):
        problems.append("[readers-disagree] " + 
            f"the transcript reader counts {n_user} user turn(s) with text and the record reader "
            f"counts {len(ops) + len(harness) + len(unknown)}. The two disagree, so which turns the "
            f"operator sent cannot be established.")
    if unknown:
        problems.append("[unknown-harness-origin] " + 
            f"{len(unknown)} user record(s) carry a harness origin the pre-registration does not "
            f"name -- first: {unknown[0]!r}. Whether the operator sent it cannot be established.")
    if harness:
        print(f"  NOTE     {len(harness)} user record(s) delivered by the harness, not the operator; "
              f"not counted as operator lines")

    if agent_turn_count(path) == 0:
        problems.append("[no-first-agent-turn] " + 
            "no agent turn produced text. Without a first agent turn this is a rehearsal by "
            "definition, not a take that happened to go badly.")

    # ---- the session id, and what the project name must be ----------------------------
    sid = session_id_of(path)
    if not sid:
        problems.append("[no-session-id] " + "the transcript records no session id, so it cannot be tied to a ledger row")
    expected_project = neutral_name(sid) if sid else ""

    # ---- the operator lines: verbatim, in order, once, and nothing else -----------------
    script = half["operator_script"]
    if isinstance(script, str):
        problems.append("[script-not-a-list] " + f"this task's operator script is a reference ({script}), not a list of "
                        f"turns; the frozen file must hold the lines it sends")
        return problems

    steps = script if not is_walk else [s for s in script if s["n"] < half["probe_operator_turn"]]
    expected_source = expected_source_for(half, expected_project)
    required, stop_problems = required_steps(steps, path, turns, is_walk, expected_project,
                                             expected_source, harness)
    problems += stop_problems
    line_problems = operator_line_problems(ops, required, expected_project, expected_source)
    problems += line_problems
    if not line_problems:
        problems += continuation_problems(turns, required, harness, expected_project, expected_source)

    # ---- the fixture ---------------------------------------------------------------------
    fx_problems, fx_note = fixture_binding_problems(path, half, is_walk)
    problems += fx_problems
    if fx_note:
        print(f"  NOTE     {fx_note}")

    # ---- the leak ----------------------------------------------------------------------
    leaked = sorted({w for w in pre["leak_words"] if w.lower() in joined})
    if leaked:
        problems.append("[leak-in-operator-turn] " + 
            f"an operator turn contains {leaked}, which tells the agent what this is. The take is "
            f"void: a leak does not show in the verdict, it simply looks like a pass.")

    ctx = context_text(path)
    ctx_leaked = sorted(context_leaks(ctx, pre))
    if ctx_leaked:
        problems.append("[leak-in-loaded-context] " + 
            f"the agent's loaded context contains {ctx_leaked}. Nothing the operator typed says it, "
            f"so this came in with the session -- an instruction file above the working directory, "
            f"or the session context. The agent was told what it was in before the first line was "
            f"sent, and the verdict would look exactly like a pass.")

    outside = inherited_context(path)
    if outside:
        problems.append("[inherited-context] " + 
            f"the session was given {len(outside)} thing(s) from outside its checkout -- first: "
            f"{outside[0][:140]}. The agent's world is meant to be the checkout and nothing else.")

    problems += published_email_problems(path)

    ledger = _ledger_beside(path)
    problems += completion_problems(path, ledger)
    # REVIEW 21, F6. The turn list records the script, not whatever the operator writes: a row whose
    # number is not a line this half sends left `required` unchanged and passed.
    if ledger and isinstance(script, list):
        step_ns = {s["n"] for s in script}
        recoveries = {s["n"] for s in script if s.get("recovery")}
        seen_rows: set = set()
        for row in ledger.get("turns") or []:
            n = row.get("n")
            recovery = bool(row.get("recovery"))
            if n not in step_ns:
                problems.append(f"[outcome-binding] the ledger records a turn {n!r}, which is "
                                f"not a line on this half's script")
                break
            # REVIEW 22, F5: a recovery for a step the frozen file attaches none to, and the same row
            # twice, are two more ways the turn list could be the operator's rather than the script's.
            if recovery and n not in recoveries:
                problems.append(f"[outcome-binding] the ledger records a recovery on turn {n}, and the "
                                f"frozen file attaches no recovery to that line")
                break
            if (n, recovery) in seen_rows:
                problems.append(f"[outcome-binding] the ledger records turn {n} twice with the same "
                                f"shape; the driver writes one row for each line it sends")
                break
            seen_rows.add((n, recovery))
    if ledger and ledger.get("source") is not None and ledger.get("source") != expected_source:
        problems.append(f"[fixture-binding] the driver handed the agent the source {ledger.get('source')!r}, "
                        f"and this half's fixture kind implies {expected_source!r}")

    reached = study_paths_read(path)
    if reached:
        problems.append("[study-materials-reached] " + 
            f"the agent reached this study's own materials under evals/ ({len(reached)} mention(s); "
            f"first: {reached[0][:70]!r}). The design it is being measured against is readable from "
            f"the checkout it works in.")

    outside_reads = outside_checkout_reads(path)
    outside_reads += outside_home_reads(path)
    outside_reads += outside_temp_reads(path)
    if outside_reads:
        problems.append("[read-outside-the-checkout] " +
            f"a tool call or its result named a path outside this session's own checkout "
            f"{len(outside_reads)} time(s) -- first: {outside_reads[0][:120]!r}. This repository's checkout, "
            f"the folder holding its sibling worktrees and the root above them hold the study; a take reads "
            f"its own run tree.")

    # ---- the project name --------------------------------------------------------------
    if expected_project and expected_project.lower() not in joined:
        problems.append("[project-name] " + 
            f"no operator turn names the project {expected_project!r}, which is the name derived "
            f"from this session's id. The transcript cannot be tied back to its ledger row.")

    # ---- the ledger binding -------------------------------------------------------------
    if is_walk:
        if row_index is not None:
            problems.append("[invocation] " + "a walk has no ledger row; --row and --walk are mutually exclusive")

        # A WALK CANNOT ALWAYS TELL WHICH HALF IT IS, AND MUST SAY SO RATHER THAN PASS.
        #
        # Three of these tasks pair a positive and control half that differ ONLY at the probe
        # turn, on a byte-identical fixture. A walk stops before the probe. So for those tasks a
        # walk of the positive and a walk of the control send exactly the same lines against
        # exactly the same bytes, and nothing in the transcript distinguishes them.
        #
        # This was found by declaring a scope-read walk as the wrong half and watching the checker
        # pass it. Reporting "valid" there would be reporting a pass on a question this file cannot
        # answer, which is the same shape as a guard that never fires.
        other = "control" if half_name == "positive" else "positive"
        mine = [(s["n"], s["line"], s.get("marker")) for s in steps]
        theirs = [(s["n"], s["line"], s.get("marker"))
                  for s in spec[other]["operator_script"]
                  if isinstance(s, dict) and s["n"] < spec[other]["probe_operator_turn"]]
        def fixture_of(h: str) -> dict:
            return {k: v for k, v in (spec[h].get("fixture") or {}).items() if k != "half"}
        if mine == theirs and fixture_of(half_name) == fixture_of(other):
            print(f"  NOTE     the half is NOT determinable from a walk of {task_id}: its two "
                  f"halves send identical lines before the probe, on the same fixture. This run "
                  f"checked the operator side, not which half it was.")
        elif mine == theirs:
            print(f"  NOTE     {task_id}'s two halves send identical lines before the probe and "
                  f"differ in fixture, so the half is decided by the fixture binding above.")
        problems += checkout_problems(path, pre)
        problems += instruction_content_problems(path)
        wanted_model = (ledger or {}).get("model_requested")
        if wanted_model:
            problems += model_problems(path, wanted_model)
        else:
            print("  NOTE     no driver ledger names this walk's model, so the model binding was not checked")
        if memory_section_offered(path):
            print("  NOTE     this walk was offered the harness's auto-memory folder; walks predate the "
                  "switch that removes it, and a take offered it is refused")
        # DECISION 4: a walk's environment record is read and reported, never refused.
        for p in environment_problems(path, ledger, pre, None):
            print(f"  NOTE     {p} (a walk is not refused for it; a take is)")
        return problems

    if row_index is None:
        problems.append("[invocation] " + "a graded take needs its ledger row (--row N) to check the binding")
        return problems

    rows = takes_mod.load_rows()
    if not (0 <= row_index < len(rows)):
        problems.append("[session-binding] " + f"no ledger row {row_index}")
        return problems
    row = rows[row_index]
    if (row["task"], row["half"]) != (task_id, half_name):
        problems.append("[session-binding] " + f"row {row_index} is {row['task']}/{row['half']}, not {task_id}/{half_name}")

    commits = takes_mod.row_commits()
    if row_index not in commits:
        problems.append("[session-binding] " + f"row {row_index} is not committed, so the session id it implies does not "
                        f"exist and nothing binds this transcript to a pre-registration")
    else:
        want = takes_mod.session_id_for(commits[row_index])
        if sid != want:
            problems.append("[session-binding] " + 
                f"the session id does not match its row's commit. The transcript says {sid}, and "
                f"uuid5(namespace, {commits[row_index][:12]}) is {want}. Either this is not the "
                f"session that row registered, or the row was committed after the fact.")

    problems += environment_problems(path, ledger, pre, commits.get(row_index))
    problems += model_problems(path, row["model"])
    problems += constant_problems(ledger, pre)
    problems += checkout_problems(path, pre)
    problems += instruction_content_problems(path)
    if not prompt_snapshot_present(path):
        problems.append("[inherited-context] the session recorded no system-prompt snapshot, so whether the "
                        "harness offered its memory folder could not be read")
    if memory_section_offered(path):
        problems.append("[inherited-context] the session was offered the harness's persistent memory folder "
                        "outside its checkout; takes run with CLAUDE_CODE_DISABLE_AUTO_MEMORY=1")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description="Check that a transcript is the take it claims to be.")
    ap.add_argument("transcript")
    ap.add_argument("--task", required=True)
    ap.add_argument("--half", required=True, choices=("positive", "control"))
    ap.add_argument("--row", type=int)
    ap.add_argument("--walk", action="store_true",
                    help="a pre-freeze walk: no ledger row, and the script stops before the probe")
    args = ap.parse_args()

    path = Path(args.transcript)
    if not path.is_file():
        print(f"no transcript at {path}")
        return 2

    data = tx.load(path)
    problems = check(path, args.task, args.half, args.row, args.walk)

    print(f"{'walk' if args.walk else 'take'}: {path.relative_to(REPO) if path.is_absolute() and str(path).startswith(str(REPO)) else path}")
    print(f"  sha256   {data['sha256']}")
    print(f"  turns    {data['n_turns']} ({len(data['user_turns'])} from the operator)")
    print(f"  declared {args.task} / {args.half}")

    if problems:
        print(f"\nNOT VALID — {len(problems)} problem(s):")
        for p in problems:
            print(f"  - {p}")
        print("\nKeep it. Do not grade it, and do not edit it into shape.")
        return 1

    print("\nvalid — every operator-side check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
