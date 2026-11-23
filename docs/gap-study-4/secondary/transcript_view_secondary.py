#!/usr/bin/env python3
"""OD201's secondary analysis only (branch analysis/reader-gap-secondary, never on the line): the patched claude-code
parser, installed at runtime into transcript_view.PARSERS["claude-code"]
(plans/gap-study-4-reader-gap-sensitivity-PREREG-20261108.md, item 1).

transcript_view.py itself stays byte-identical to the frozen file, so the native-reader acceptance records, which bind
the hash of the reader sources (native_reader_registration.READER_SOURCES), still hold, and vendor takes are admitted
exactly as in the primary analysis. glitch-34's ruling (13 Nov 2026, option 1) after the first attempt edited
transcript_view.py in place and 370 vendor takes were refused (VendorAdmissionRefused).

The parser admits exactly four more shapes than the frozen claude-code parser, and nothing else:
    Write.file_text      an alias of Write.content (a call carrying both is refused)
    Skill                a tool call of kind other, its keys skill and args
    skill companion      the harness's isMeta turnCompanion record whose sourceToolUseID is an earlier Skill call's id
                         (is_skill_companion: type user, isMeta and turnCompanion the boolean true, no origin, no
                         isApiErrorMessage, not a sidechain, content a non-empty list of {type: text, text: str} blocks;
                         each Skill call admits at most one), as harness; raw type `user:skill-companion`
    command_permissions  an attachment of exactly the keys type and allowedTools (a list of strings), as harness
Every other record goes to the frozen parser's own code, unchanged. Skill calls are tracked per reading pass on the
pass's own ScheduledWakeups object (transcript_view._items makes one per pass), so outside a pass no companion is
admitted. Standard library only; no model is called.

    install()      put the patched parser into transcript_view.PARSERS["claude-code"]; returns the frozen one
    installed()    a context manager: installed inside, the frozen parser restored after
"""
from __future__ import annotations

import contextlib
import json
import weakref

import transcript_view as tv

SEC_TOOLS = dict(tv.CC_TOOLS)
SEC_TOOLS["Write"] = (tv.WRITE, {"file_path": "path"}, ("file_path", "content", "file_text"))
SEC_TOOLS["Skill"] = (tv.OTHER, {}, ("skill", "args"))
WRITE_ALIAS = ("Write", ("content", "file_text"))
SKILL_TOOL = "Skill"
COMMAND_PERMISSIONS = "command_permissions"
COMMAND_PERMISSIONS_KEYS = ("type", "allowedTools")
SKILL_COMPANION = "skill-companion"


def skill_call_ids(rec) -> list:
    """The tool_use ids of the Skill calls in one genuine agent record, in order (string ids only)."""
    if not tv._genuine_agent_record(rec):
        return []
    content = rec["message"].get("content")
    return [b["id"] for b in (content if isinstance(content, list) else [])
            if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") == SKILL_TOOL
            and isinstance(b.get("id"), str)]


def _text_blocks(content) -> bool:
    return (isinstance(content, list) and bool(content)
            and all(isinstance(b, dict) and set(b) == {"type", "text"} and b["type"] == "text"
                    and isinstance(b["text"], str) for b in content))


def is_skill_companion(rec, armed) -> bool:
    """Every clause required: type user, isMeta and turnCompanion the boolean true, sourceToolUseID a string in `armed`
    (earlier Skill calls' ids no companion has consumed), no origin, no isApiErrorMessage, not a sidechain, content a
    non-empty list of text blocks of exactly {type, text}."""
    if not (isinstance(rec, dict) and rec.get("type") == "user" and rec.get("isMeta") is True
            and rec.get("turnCompanion") is True):
        return False
    if rec.get("isSidechain") is True or any(k in rec for k in ("isApiErrorMessage", "origin")):
        return False
    sid = rec.get("sourceToolUseID")
    if not isinstance(sid, str) or sid not in armed:
        return False
    msg = rec.get("message")
    return isinstance(msg, dict) and _text_blocks(msg.get("content"))


class SkillCalls:
    """One reading pass's Skill call ids: note() arms them, admit() consumes one per companion."""

    def __init__(self):
        self.armed: set = set()
        self.consumed: set = set()

    def note(self, rec) -> None:
        for ref in skill_call_ids(rec):
            if ref not in self.consumed:
                self.armed.add(ref)

    def admit(self, rec) -> bool:
        if not is_skill_companion(rec, self.armed):
            return False
        self.armed.discard(rec["sourceToolUseID"])
        self.consumed.add(rec["sourceToolUseID"])
        return True


_PASSES: "weakref.WeakKeyDictionary" = weakref.WeakKeyDictionary()   # a pass's ScheduledWakeups -> its SkillCalls


def _pass_skills():
    wakeups = tv._PASS_WAKEUPS.get()
    if wakeups is None:
        return None
    if wakeups not in _PASSES:
        _PASSES[wakeups] = SkillCalls()
    return _PASSES[wakeups]


def _command_permissions_item(a) -> list:
    if set(a) != set(COMMAND_PERMISSIONS_KEYS):
        raise tv.ViewError(f"a command_permissions attachment whose keys are not exactly "
                           f"{sorted(COMMAND_PERMISSIONS_KEYS)}")
    tools = a["allowedTools"]
    if not (isinstance(tools, list) and all(type(x) is str for x in tools)):
        raise tv.ViewError("a command_permissions attachment whose allowedTools is not a list of strings")
    return [tv.RawItem("attachment:" + COMMAND_PERMISSIONS, tv.HARNESS, text="\n".join(tools) if tools else None)]


class SecondaryClaudeCodeParser(tv.ClaudeCodeSessionParser):
    """The frozen claude-code parser plus exactly the four shapes above."""

    tools = SEC_TOOLS
    attachment_types = tv.CC_ATTACHMENT_TYPES + (COMMAND_PERMISSIONS,)
    secondary = True

    def items(self, line: str) -> list:
        skills = _pass_skills()
        try:
            r = json.loads(line)
        except ValueError:
            r = None
        if skills is not None and isinstance(r, dict) and any(f in r for f in tv.CC_REFUSED_FLAGS) \
                and r.get("type") in tv.CC_RECORD_TYPES and skills.admit(r):
            return [tv.RawItem("user:" + SKILL_COMPANION, tv.HARNESS,
                               text="\n".join(b["text"] for b in r["message"]["content"]))]
        got = super().items(line)
        if skills is not None and isinstance(r, dict) and r.get("type") == "assistant":
            skills.note(r)
        return got

    def _assistant(self, r) -> list:
        msg = r.get("message")
        if isinstance(msg, dict) and msg.get("model") == tv.CC_SYNTHETIC_MODEL:
            raise tv.ViewError("an assistant record whose model is <synthetic>: the harness wrote it itself, refused")
        content = msg.get("content") if isinstance(msg, dict) else None
        if not isinstance(content, list):
            raise tv.ViewError("an assistant record whose content is not a list of blocks")
        out = []
        for b in content:
            bt = b.get("type") if isinstance(b, dict) else None
            if bt not in tv.CC_ASSISTANT_BLOCKS:
                raise tv.ViewError(f"unknown block type in an assistant record: {bt!r}")
            if bt == "text":
                if not isinstance(b.get("text"), str):
                    raise tv.ViewError("a text block without its string")
                out.append(tv.RawItem("assistant", tv.AGENT_TEXT, text=b["text"]))
            elif bt == "thinking":
                if not isinstance(b.get("thinking"), str):
                    raise tv.ViewError("a thinking block without its string")
                out.append(tv.RawItem("assistant", tv.AGENT_REASONING, text=b["thinking"]))
            else:
                if not isinstance(b.get("id"), str):
                    raise tv.ViewError("a tool call without an id")
                name, keys = WRITE_ALIAS
                if b.get("name") == name and isinstance(b.get("input"), dict) and set(keys) <= set(b["input"]):
                    raise tv.ViewError(f"tool {name!r}: both {list(keys)}; file_text is an alias, not a second key")
                kind, args = tv.map_tool(SEC_TOOLS, b.get("name"), b.get("input"))
                out.append(tv.RawItem("assistant", tv.TOOL_CALL, tool=kind, args=args, ref=b["id"]))
        return out

    def _attachment(self, r) -> list:
        a = r.get("attachment")
        if isinstance(a, dict) and a.get("type") == COMMAND_PERMISSIONS:
            return _command_permissions_item(a)
        return super()._attachment(r)


FROZEN_PARSER = tv.PARSERS["claude-code"]


def install():
    """Install the patched claude-code parser; returns the parser it replaced."""
    old = tv.PARSERS["claude-code"]
    if not getattr(old, "secondary", False):
        tv.PARSERS["claude-code"] = SecondaryClaudeCodeParser()
    return old


@contextlib.contextmanager
def installed():
    old = install()
    try:
        yield tv.PARSERS["claude-code"]
    finally:
        tv.PARSERS["claude-code"] = old
