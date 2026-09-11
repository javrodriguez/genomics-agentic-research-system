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
    pinned = spec.get("sha256")
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
        return [], "the driver ledger records no fixture hash, so the fixture binding was not checked"
    if not pinned:
        return [], (f"the fixture binding is unpinned until the freeze (the driver built "
                    f"{got[:12]}; the pre-registration pins nothing yet)")
    if got != pinned:
        return [f"[fixture-binding] the fixture the driver built ({got[:12]}) is not this half's pinned fixture "
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
    if ledger and ledger.get("source") is not None and ledger.get("source") != expected_source:
        problems.append(f"[fixture-binding] the driver handed the agent the source {ledger.get('source')!r}, "
                        f"and this half's fixture kind implies {expected_source!r}")

    reached = study_paths_read(path)
    if reached:
        problems.append("[study-materials-reached] " + 
            f"the agent reached this study's own materials under evals/ ({len(reached)} mention(s); "
            f"first: {reached[0][:70]!r}). The design it is being measured against is readable from "
            f"the checkout it works in.")

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
