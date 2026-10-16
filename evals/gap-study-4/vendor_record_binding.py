"""Host turn envelopes bound to retained native bytes, never vendor-observed claims.

Schema 1 has one harness-turn per interaction, including recovery interactions.
`n` is its contiguous position, independent of the script step's ledger n. Only
the operator prompt is supplied by the envelope. Model, mode, version, cwd and
instruction provenance must be checked separately; this module grants no take
admission and is not evidence that documented native shapes were live-verified.
"""
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import stat

import transcript_view as tv

HARNESSES = ("codex", "gemini")
KEYS = {"type", "harness", "session_id", "vendor_session_id", "n", "sent", "stream", "sha256"}


def _regular_bytes(path):
    """No links, devices or blocking opens; validate the descriptor actually read."""
    try:
        if not stat.S_ISREG(path.lstat().st_mode):
            raise tv.ViewError("bound evidence must be a regular file")
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as fh:
            if not stat.S_ISREG(os.fstat(fh.fileno()).st_mode):
                raise tv.ViewError("bound evidence descriptor is not a regular file")
            return fh.read()
    except OSError as exc:
        raise tv.ViewError(f"unreadable bound evidence: {exc}") from None


def _json(text):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise tv.ViewError("duplicate JSON key in bound record")
            out[key] = value
        return out
    try:
        return json.loads(text, object_pairs_hook=pairs)
    except (ValueError, TypeError) as exc:
        raise tv.ViewError(f"invalid bound record: {exc}") from None


def _jsonl_lines(text):
    """JSONL is framed by LF, never Unicode separators within JSON strings."""
    lines = text.split("\n")
    if lines[-1] == "":
        lines.pop()
    return lines


def bound_items(harness, path):
    """Read only an on-disk envelope alongside its ledger and native streams. `path` is the transcript's path, or a
    transcript_view.BoundTranscript, bound by its .path, whose carried lines must be the file's lines now (item E's
    review: one value never carries two transcripts)."""
    bound = tv.BoundTranscript.of(path)            # the transcript itself, or a grader's whole, ordered copy of it
    carried = bound.lines if bound is not None else None
    if bound is not None:
        path = bound.path
    if harness not in HARNESSES or not isinstance(path, (str, Path)):
        raise tv.ViewError("vendor events require a bound transcript path")
    path = Path(path)
    if carried is not None:
        try:
            now = tuple(tv.jsonl_lines(_regular_bytes(path).decode("utf-8")))   # review r7: newline only
        except (OSError, UnicodeError) as exc:
            raise tv.ViewError(f"missing bound record: {exc}") from None
        if now != carried:
            raise tv.ViewError("the bound transcript's lines are not its file's lines")
    ledger_path = path.parent / "driver-ledger.json"
    try:
        ledger = _json(_regular_bytes(ledger_path).decode("utf-8"))
        envelopes = [_json(line) for line in _jsonl_lines(_regular_bytes(path).decode("utf-8"))]
    except (OSError, UnicodeError) as exc:
        raise tv.ViewError(f"missing bound record: {exc}") from None
    if not isinstance(ledger, dict) or not isinstance(ledger.get("agent"), dict):
        raise tv.ViewError("bound transcript needs a driver ledger")
    turns = ledger.get("turns")
    if ledger["agent"].get("harness") != harness or not isinstance(turns, list) or len(turns) != len(envelopes):
        raise tv.ViewError("harness or interaction count differs from ledger")
    if not envelopes:
        raise tv.ViewError("no bound interactions")
    out, names, vendor_id = [], [], None
    if harness == "codex":
        from transcript_codex import CodexParser
        parser = CodexParser()
    else:
        from transcript_gemini import GeminiParser
        parser = GeminiParser()
    for ordinal, (env, turn) in enumerate(zip(envelopes, turns), 1):
        if not isinstance(env, dict) or set(env) != KEYS or not isinstance(turn, dict):
            raise tv.ViewError("wrong turn envelope shape")
        if (env["type"] != "harness-turn" or env["harness"] != harness or
                type(env["n"]) is not int or env["n"] != ordinal or
                not isinstance(env["session_id"], str) or not env["session_id"] or
                env["session_id"] != ledger.get("session_id") or
                not isinstance(env["sent"], str) or env["sent"] != turn.get("sent")):
            raise tv.ViewError("turn envelope differs from ledger")
        sid = env["vendor_session_id"]
        if not isinstance(sid, str) or not sid or (vendor_id is not None and sid != vendor_id):
            raise tv.ViewError("vendor identity changes between turns")
        vendor_id = sid
        name = env["stream"]
        if (not isinstance(name, str) or not name or Path(name).name != name or
                name in (".", "..", "transcript.jsonl", "driver-ledger.json") or name in names):
            raise tv.ViewError("stream is not a unique confined basename")
        native_path = path.parent / name
        try:
            raw = _regular_bytes(native_path)
            text = raw.decode("utf-8")
        except (OSError, UnicodeError) as exc:
            raise tv.ViewError(f"unreadable native stream: {exc}") from None
        if hashlib.sha256(raw).hexdigest() != env["sha256"]:
            raise tv.ViewError("native stream digest differs")
        names.append(name)
        out.append(tv.RawItem("harness-turn", tv.OPERATOR, text=env["sent"]))
        native_ids, operators = [], []
        for line in _jsonl_lines(text):
            record = _json(line)
            if isinstance(record, dict):
                if harness == "codex" and record.get("type") == "thread.started":
                    native_ids.append(record.get("thread_id"))
                if harness == "gemini" and record.get("type") == "init":
                    native_ids.append(record.get("session_id"))
            for item in parser.items(line):
                if item.kind == tv.OPERATOR:
                    operators.append(item.text)
                else:
                    out.append(replace(item, ref=f"{ordinal}:{item.ref}") if item.ref is not None else item)
        if native_ids != [sid]:
            raise tv.ViewError("native stream must bind exactly one matching vendor identity")
        if (harness == "gemini" and operators != [env["sent"]]) or (harness == "codex" and operators):
            raise tv.ViewError("native operator record differs from sent prompt")
    if ledger.get("streams") != names:
        raise tv.ViewError("bound streams differ from ledger stream inventory")
    return out
