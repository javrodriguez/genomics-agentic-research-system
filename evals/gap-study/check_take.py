#!/usr/bin/env python3
"""Is this transcript the take it claims to be? Asked before anything is graded.

    python3 evals/gap-study/check_take.py <transcript> --task <id> --half <h> [--row N]
    python3 evals/gap-study/check_take.py <transcript> --task <id> --half <h> --walk

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

Exit 0 only when every check passes. Anything else names what is wrong, and the attempt is a
rehearsal: kept, never graded, never edited into shape.

No model is called. stdlib only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "evals"))

import prereg  # noqa: E402
import takes as takes_mod  # noqa: E402
import transcript as tx  # noqa: E402


def normalise(text: str) -> str:
    return " ".join((text or "").split())


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
        if not isinstance(rec, dict) or rec.get("type") not in ("user", "assistant"):
            continue
        for m in re.finditer(r"evals/(?:gap-study|transcripts|results|prereg)", line):
            seen.append(line[max(0, m.start() - 40):m.start() + 40])
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
            return ["the published transcript still carries session_context.userEmail, which "
                    "Ruling 10 removes at copy time (scrub.py)"]
    return []


def _line_head(line: str, expected_project: str) -> str:
    """The fixed head of a scripted line, rendered for this take; a line carrying a path is matched on
    the part before the path, since the path is per-take."""
    line = line.replace("{project}", expected_project).replace("{source}", "").strip()
    needle = normalise(line).lower()
    return needle.split(" in ")[0] if " in " in needle else needle


def _is_recovery_send(op: str, rec: dict, expected_project: str) -> bool:
    """Is this operator turn the step's pre-registered recovery line, rendered for this take?"""
    got = normalise(op).strip()
    send = rec["send"].strip()
    if send == "{source}":
        # the source path is per-take: it carries the project's neutral name and has no spaces
        return bool(expected_project) and expected_project in got and " " not in got
    want = normalise(send.replace("{project}", expected_project)).strip()
    return got.lower() == want.lower()


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
                   expected_project: str) -> tuple[list[dict], list[str]]:
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
        if marker:
            head = _line_head(step["line"], expected_project)
            idx = max((i for i, t in enumerate(turns)
                       if t["role"] == "user" and head and head in normalise(t["text"]).lower()),
                      default=None)
            after = ("\n".join(t["text"] for t in turns[idx + 1:] if t["role"] == "assistant")
                     if idx is not None else "")
            if marker in after:
                problems.append(
                    f"the driver stopped at operator turn {last} because its marker was not held, and "
                    f"the marker {marker!r} is in the agent's reply after that line. A stop at a held "
                    f"wait point manufactures `did-not-reach`.")
    return required, problems


def operator_line_problems(ops: list[str], steps: list[dict], expected_project: str) -> list[str]:
    """The operator's turns against the script: each step's line, in order, once; then at most
    `at_most` sends of THAT step's pre-registered recovery; and nothing else.

    FOUND 11 SEPTEMBER 2026, BEFORE ANY TAKE. The previous check counted: every line present once,
    and `len(ops) > len(steps)` was improvisation. A recovery is a real operator turn, sent by the
    driver from the frozen file, so on the take it rescued the count came out one high and the
    checker refused the take as the operator improvising. Every recovery would have voided the take
    it existed to save, and a reader of the rehearsal folder would have seen "improvising" beside a
    line the pre-registration itself named.

    A recovery is admitted only where the frozen file attaches one, only immediately after the step
    it answers, only as many times as `at_most` allows, and only as the rendered `send`. Anything
    else the operator sent is still improvisation and still refused.
    """
    problems: list[str] = []
    norm = [normalise(o).lower() for o in ops]
    heads = [_line_head(s["line"], expected_project) for s in steps]
    unexplained: list[int] = []
    i = 0
    for idx, step in enumerate(steps):
        head = heads[idx]
        nxt = heads[idx + 1] if idx + 1 < len(heads) else None

        def is_next(k: int) -> bool:
            return bool(nxt) and nxt in norm[k]

        if not head:
            problems.append(f"operator turn {step['n']} renders to nothing; the script is broken")
            continue
        pos = next((k for k in range(i, len(ops)) if head in norm[k]), None)
        if pos is None:
            problems.append(f"operator turn {step['n']} was never sent: {head[:70]!r}")
            continue
        unexplained.extend(range(i, pos))
        i = pos + 1
        while i < len(ops) and head in norm[i] and not is_next(i):
            problems.append(f"operator turn {step['n']} was sent twice; it is sent once")
            i += 1
        rec = step.get("recovery")
        if rec:
            at_most = int(rec.get("at_most", 1))
            used = 0
            while i < len(ops) and _is_recovery_send(ops[i], rec, expected_project) and not is_next(i):
                used += 1
                if used > at_most:
                    problems.append(f"the recovery for operator turn {step['n']} was sent {used} "
                                    f"times and the frozen file allows {at_most}; a recovery that "
                                    f"repeats is the operator improvising")
                i += 1
    unexplained.extend(range(i, len(ops)))
    for k in unexplained:
        problems.append(f"operator turn {k + 1} is not on the script: {ops[k][:70]!r}. A line that "
                        f"is not on the script is the operator improvising.")
    return problems


def fixture_binding_problems(path: Path, half: dict) -> tuple[list[str], str | None]:
    """The fixture the driver built, from its ledger beside the transcript, against this half's pin.

    The fixture is what defines the half. For the five tasks whose halves share one fixture the
    check is vacuous; for confounded-design the halves differ before the probe, and a take pointed
    at the other half's fixture measures the other experiment. Returns (problems, note): a note
    where the comparison could not be made, so a silent pass is never printed for it.
    """
    ledger_path = path.parent / "driver-ledger.json"
    pinned = (half.get("fixture") or {}).get("sha256")
    if not ledger_path.is_file():
        return [], "no driver ledger beside the transcript, so the fixture binding was not checked"
    try:
        ledger = json.loads(ledger_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return [f"the driver ledger beside the transcript is unreadable ({exc!r})"], None
    fx = ledger.get("fixture") or {}
    got = fx.get("tree_sha256_name_invariant") or fx.get("sha256")
    if not got:
        return [], "the driver ledger records no fixture hash, so the fixture binding was not checked"
    if not pinned:
        return [], (f"the fixture binding is unpinned until the freeze (the driver built "
                    f"{got[:12]}; the pre-registration pins nothing yet)")
    if got != pinned:
        return [f"the fixture the driver built ({got[:12]}) is not this half's pinned fixture "
                f"({pinned[:12]}). The take measures the other experiment."], None
    return [], None


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
        problems.append(
            f"the transcript reader counts {n_user} user turn(s) with text and the record reader "
            f"counts {len(ops) + len(harness) + len(unknown)}. The two disagree, so which turns the "
            f"operator sent cannot be established.")
    if unknown:
        problems.append(
            f"{len(unknown)} user record(s) carry a harness origin the pre-registration does not "
            f"name -- first: {unknown[0]!r}. Whether the operator sent it cannot be established.")
    if harness:
        print(f"  NOTE     {len(harness)} user record(s) delivered by the harness, not the operator; "
              f"not counted as operator lines")

    if not any(t["role"] == "assistant" and t["text"].strip() for t in turns):
        problems.append(
            "no agent turn produced text. Without a first agent turn this is a rehearsal by "
            "definition, not a take that happened to go badly.")

    # ---- the session id, and what the project name must be ----------------------------
    sid = session_id_of(path)
    if not sid:
        problems.append("the transcript records no session id, so it cannot be tied to a ledger row")
    expected_project = neutral_name(sid) if sid else ""

    # ---- the operator lines: verbatim, in order, once, and nothing else -----------------
    script = half["operator_script"]
    if isinstance(script, str):
        problems.append(f"this task's operator script is a reference ({script}), not a list of "
                        f"turns; the frozen file must hold the lines it sends")
        return problems

    steps = script if not is_walk else [s for s in script if s["n"] < half["probe_operator_turn"]]
    required, stop_problems = required_steps(steps, path, turns, is_walk, expected_project)
    problems += stop_problems
    problems += operator_line_problems(ops, required, expected_project)

    # ---- the fixture ---------------------------------------------------------------------
    fx_problems, fx_note = fixture_binding_problems(path, half)
    problems += fx_problems
    if fx_note:
        print(f"  NOTE     {fx_note}")

    # ---- the leak ----------------------------------------------------------------------
    leaked = sorted({w for w in pre["leak_words"] if w.lower() in joined})
    if leaked:
        problems.append(
            f"an operator turn contains {leaked}, which tells the agent what this is. The take is "
            f"void: a leak does not show in the verdict, it simply looks like a pass.")

    ctx = context_text(path)
    ctx_leaked = sorted(context_leaks(ctx, pre))
    if ctx_leaked:
        problems.append(
            f"the agent's loaded context contains {ctx_leaked}. Nothing the operator typed says it, "
            f"so this came in with the session -- an instruction file above the working directory, "
            f"or the session context. The agent was told what it was in before the first line was "
            f"sent, and the verdict would look exactly like a pass.")

    outside = inherited_context(path)
    if outside:
        problems.append(
            f"the session was given {len(outside)} thing(s) from outside its checkout -- first: "
            f"{outside[0][:140]}. The agent's world is meant to be the checkout and nothing else.")

    problems += published_email_problems(path)

    reached = study_paths_read(path)
    if reached:
        problems.append(
            f"the agent reached this study's own materials under evals/ ({len(reached)} mention(s); "
            f"first: {reached[0][:70]!r}). The design it is being measured against is readable from "
            f"the checkout it works in.")

    # ---- the project name --------------------------------------------------------------
    if expected_project and expected_project.lower() not in joined:
        problems.append(
            f"no operator turn names the project {expected_project!r}, which is the name derived "
            f"from this session's id. The transcript cannot be tied back to its ledger row.")

    # ---- the ledger binding -------------------------------------------------------------
    if is_walk:
        if row_index is not None:
            problems.append("a walk has no ledger row; --row and --walk are mutually exclusive")

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
        return problems

    if row_index is None:
        problems.append("a graded take needs its ledger row (--row N) to check the binding")
        return problems

    rows = takes_mod.load_rows()
    if not (0 <= row_index < len(rows)):
        problems.append(f"no ledger row {row_index}")
        return problems
    row = rows[row_index]
    if (row["task"], row["half"]) != (task_id, half_name):
        problems.append(f"row {row_index} is {row['task']}/{row['half']}, not {task_id}/{half_name}")

    commits = takes_mod.row_commits()
    if row_index not in commits:
        problems.append(f"row {row_index} is not committed, so the session id it implies does not "
                        f"exist and nothing binds this transcript to a pre-registration")
    else:
        want = takes_mod.session_id_for(commits[row_index])
        if sid != want:
            problems.append(
                f"the session id does not match its row's commit. The transcript says {sid}, and "
                f"uuid5(namespace, {commits[row_index][:12]}) is {want}. Either this is not the "
                f"session that row registered, or the row was committed after the fact.")

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
