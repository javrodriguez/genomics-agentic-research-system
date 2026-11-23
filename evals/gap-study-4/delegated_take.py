#!/usr/bin/env python3
"""A take that hands work to a sub-agent, presented to the unchanged graders as the agent did it.

glitch-b5's pre-freeze ruling (16 Oct 2026): a refused delegated take leaves its label missing exactly where a model
delegates, a bias in the measured run. So the grading roads present the take instead. Each Agent call is replaced,
where it stands in the main thread, by its sub-agent's own records, read as the agent's own. The graders run
unchanged; the round-3 closed graders' gates ("the grader's code is the base's") hold.

THE SOURCE. The sub-agent's records are its copied session file, subagents/agent-<id>.jsonl beside the transcript.
<id> is the agentId the call's own result names, the pair check_take binds (subagent_problems: the call, its file and
its meta one to one, the stream and the file agreeing call for call). It is the same kind of record as the main
thread's (Claude Code's session store), so the sub-agent is graded from the record the agent is graded from. The
turn stream's copy of the same records is not read here: check_take counts every difference
(check.json's subagents.stream_file_differences).

THE PRESENTATION, record by record of the sub-agent's file:
  attachment          dropped: the sub-agent's loaded context, harness furniture the checker's leak sweep reads.
  the first user line dropped: the call's own prompt, already the agent's words in its call; a string or a list of
                      text blocks (review r14 NIT 3: the static read did not settle which 2.1.296 writes, so both).
  user, tool results  presented as the agent's tool results.
  assistant           presented as the agent's: its tool calls and thinking as they are. Its text as `words` says:
                      "reasoning" (the reply-reading graders: the operator never read the sub-agent's text, only the
                      agent's reply, so it is presented as the agent's reasoning, which none of them reads) or "text"
                      (awareness: the sub-agent's words are scanned as the agent's).
The Agent call's own block and its result are not presented: the sub-agent's records stand in their place. For an
async call (run_in_background) the order is approximate (review r14 NIT 4): the sub-agent ran beside the agent's own
later records of that turn, and its records are presented as one run at the call's place, before them.

THE FALLBACK. Anything else is not presented and refuses by a named reason (NotPresented): a transcript not bound to
its folder (a probe's synthetic lines), a call whose result names no sub-agent (an errored call), a missing file, a
record of another type, a refused flag (isMeta and its kin, which the view refuses on the main thread), a later user
line, and a delegate call the presented take still holds (a nested sub-agent).
"""
from __future__ import annotations

import json
from pathlib import Path

import transcript_view as view

AGENT_TOOL = "Agent"
SUBAGENTS_DIR = "subagents"
WORDS = ("reasoning", "text")


class NotPresented(ValueError):
    """The delegated take cannot be presented as the agent's own; the message names why."""


def present(transcript, harness: str, *, words: str):
    """`transcript` itself when it holds no delegate call; else the delegated take's lines, each Agent call replaced
    by its sub-agent's records (module docstring). NotPresented when it cannot be."""
    if words not in WORDS:
        raise ValueError(f"words is one of {WORDS}")
    lines = list(transcript)
    if not view.delegated_calls(view.events(harness, lines)):
        return transcript
    bound = view.BoundTranscript.of(transcript)
    if bound is None:
        raise NotPresented("the transcript is not bound to its take folder, so its sub-agent records cannot be read")
    recs = [json.loads(x) for x in lines]
    calls = [b["id"] for r in recs if r.get("type") == "assistant" for b in _blocks(r)
             if b.get("type") == "tool_use" and b.get("name") == AGENT_TOOL]
    agent_of = {}
    for r in recs:
        for b in _blocks(r) if r.get("type") == "user" else []:
            if b.get("type") == "tool_result" and b.get("tool_use_id") in calls:
                tur = r.get("toolUseResult")
                aid = tur.get("agentId") if isinstance(tur, dict) else None
                if isinstance(aid, str) and aid:
                    agent_of[b["tool_use_id"]] = aid
    missing = [c for c in calls if c not in agent_of]
    if missing:
        raise NotPresented(f"Agent call {missing[0]} names no sub-agent in its result (an errored or unfinished call)")
    folder = bound.path.parent
    out = []
    for r in recs:
        if r.get("type") == "assistant" and any(b.get("type") == "tool_use" and b.get("name") == AGENT_TOOL
                                                for b in _blocks(r)):
            kept = []
            for b in _blocks(r):
                if b.get("type") == "tool_use" and b.get("name") == AGENT_TOOL:
                    if kept:
                        out.append(_with_content(r, kept))
                        kept = []
                    out += _sub_records(folder, agent_of[b["id"]], words)
                else:
                    kept.append(b)
            if kept:
                out.append(_with_content(r, kept))
        elif r.get("type") == "user" and any(b.get("type") == "tool_result" and b.get("tool_use_id") in calls
                                             for b in _blocks(r)):
            kept = [b for b in _blocks(r) if not (b.get("type") == "tool_result" and b.get("tool_use_id") in calls)]
            if kept:
                out.append(_with_content(r, kept))
        else:
            out.append(r)
    shown = [json.dumps(r, ensure_ascii=False) for r in out]
    if view.delegated_calls(view.events(harness, shown)):
        raise NotPresented("a sub-agent's own Agent call (a nested sub-agent) is not presented")
    return shown


def presented_events(harness: str, transcript, *, words: str) -> list:
    """The view's events of the presented take (present), for a grader that takes events (awareness with words
    "text", pause_adherence with "reasoning")."""
    return view.events(harness, list(present(transcript, harness, words=words)))


def _blocks(r) -> list:
    msg = r.get("message")
    c = msg.get("content") if isinstance(msg, dict) else None
    return [b for b in c if isinstance(b, dict)] if isinstance(c, list) else []


def _with_content(r: dict, content: list) -> dict:
    return dict(r, message=dict(r["message"], content=content))


def _sub_records(folder: Path, aid: str, words: str) -> list:
    path = folder / SUBAGENTS_DIR / f"agent-{aid}.jsonl"
    if not path.is_file():
        raise NotPresented(f"sub-agent {aid}'s session file {SUBAGENTS_DIR}/agent-{aid}.jsonl is not in the take folder")
    out, prompt_seen = [], False
    for n, line in enumerate(view.jsonl_lines(path.read_text(encoding="utf-8")), 1):
        if not line.strip():
            continue
        r = json.loads(line)
        t = r.get("type") if isinstance(r, dict) else None
        flagged = [f for f in view.CC_REFUSED_FLAGS if isinstance(r, dict) and f in r]
        if flagged:
            raise NotPresented(f"sub-agent {aid}'s line {n} carries {flagged[0]}, which the view refuses")
        if t == "attachment":
            continue
        if t == "user":
            c = (r.get("message") or {}).get("content") if isinstance(r.get("message"), dict) else None
            if isinstance(c, str) or (isinstance(c, list) and c and all(isinstance(b, dict) and b.get("type") == "text"
                                                                        and isinstance(b.get("text"), str) for b in c)):
                if prompt_seen or out:
                    raise NotPresented(f"sub-agent {aid}'s line {n} is a user line after its prompt, which no "
                                       f"operator sent")
                prompt_seen = True
                continue
            if not (isinstance(c, list) and c and all(isinstance(b, dict) and b.get("type") == "tool_result"
                                                       for b in c)):
                raise NotPresented(f"sub-agent {aid}'s line {n} is a user record of other than tool results")
            out.append({"type": "user", "message": {"role": "user", "content": c}})
        elif t == "assistant":
            msg = r.get("message") if isinstance(r.get("message"), dict) else {}
            c = msg.get("content")
            if not isinstance(c, list):
                raise NotPresented(f"sub-agent {aid}'s line {n} is an assistant record without a list of blocks")
            shown = [{"type": "thinking", "thinking": b["text"]}
                     if words == "reasoning" and isinstance(b, dict) and b.get("type") == "text" else b for b in c]
            m = {"role": "assistant", "content": shown}
            if "model" in msg:
                m["model"] = msg["model"]
            out.append({"type": "assistant", "message": m})
        else:
            raise NotPresented(f"sub-agent {aid}'s line {n} is a {t!r} record, which is not presented")
    return out


def nested_cli_count(transcript) -> int:
    """W-3b: how many agent-CLI mentions the take's Bash commands carry (check_take.nested_cli_mentions): over
    the take folder (main thread and sub-agents, check_take.nested_cli_calls) when the transcript is bound to it, else
    over the lines handed (a probe's synthetic take)."""
    import check_take as ct
    bound = view.BoundTranscript.of(transcript)
    if bound is not None:
        return ct.nested_cli_calls(bound.path)
    recs = []
    for line in transcript:
        try:
            r = json.loads(line)
        except (TypeError, ValueError):
            continue
        if isinstance(r, dict) and r.get("type") == "assistant":
            recs.append(r)
    return sum(len(ct.nested_cli_mentions(b["input"]["command"])) for r in recs for b in _blocks(r)
               if b.get("type") == "tool_use" and b.get("name") == "Bash" and isinstance(b.get("input"), dict)
               and isinstance(b["input"].get("command"), str))
