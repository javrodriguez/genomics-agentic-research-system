"""Typed vendor evidence joins, pending reviewed native-session readers.

This is a source validator, not production admission. `actual-launch` means the
runtime's submitted exec request: its pre-call journal cannot prove a process
started or completed. Runtime exit/timeout, native terminal completeness, box
preflight, pinned config/context and independent native-session checks must all
be joined before a take can pass. No desired value is promoted to native evidence.

The production session registry intentionally has no entries. Native shapes
must be implemented from reviewed exact-version source and recorded streams.
Tests inject synthetic independent readers; adapters' cached projections are
never accepted as an alternative source of native-session bytes.
"""
from __future__ import annotations

import hashlib
import math
from copy import deepcopy
from pathlib import Path
from types import MappingProxyType

import codex_adapter
import gemini_adapter
import transcript_view as tv
from vendor_record_binding import _regular_bytes


class ProvenanceRefused(ValueError):
    """Evidence is malformed, unbound, contradictory or incomplete."""


class ProvenancePending(ProvenanceRefused):
    """A necessary reviewed reader is not available; no acceptance fallback."""


NATIVE_SESSION_READERS = MappingProxyType({})
LAUNCH_KEYS = {"schema", "harness", "container_id", "argv", "cwd", "stream", "started_at"}
WANT_KEYS = {"harness", "container_id", "model", "mode", "run_tree", "stream", "sent", "vendor_session_id", "ordinal"}
FIRST_TURN = "first-turn"     # the expectation's session on turn 1, which resumes nothing (batch-8 review finding 5)
SESSION_KEYS = {"session_id", "requested_model", "version", "cwd", "permission_mode", "sent", "output"}
OPTIONAL_NATIVE = {"requested_model", "version", "cwd", "permission_mode"}


def _fact(value, source):
    return {"value": value, "source": source}


def launch_facts(launch: dict, want: dict) -> dict:
    """Validate actual submitted argv against the registered adapter invocation."""
    if not isinstance(launch, dict) or set(launch) != LAUNCH_KEYS or type(launch.get("schema")) is not int or launch["schema"] != 1:
        raise ProvenanceRefused("actual launch has an unknown schema")
    if not isinstance(want, dict) or set(want) != WANT_KEYS:
        raise ProvenanceRefused("launch expectation has an unknown schema")
    for key in WANT_KEYS - {"ordinal"}:
        if not isinstance(want[key], str) or not want[key] or want[key] == "PENDING":
            raise ProvenanceRefused(f"launch expectation {key} is absent or PENDING")
    if type(want["ordinal"]) is not int or want["ordinal"] < 1:
        raise ProvenanceRefused("interaction ordinal must be a positive integer")
    if (want["ordinal"] == 1) != (want["vendor_session_id"] == FIRST_TURN):   # batch-8 review finding 5
        raise ProvenanceRefused(f"turn 1 resumes nothing and names {FIRST_TURN!r}; a later turn names its session")
    for actual, expected in (("harness", "harness"), ("container_id", "container_id"), ("cwd", "run_tree"), ("stream", "stream")):
        if launch[actual] != want[expected]:
            raise ProvenanceRefused(f"actual launch {actual} disagrees with bound take")
    stamp = launch["started_at"]
    if type(stamp) not in (int, float) or not math.isfinite(stamp):
        raise ProvenanceRefused("launch submission timestamp is not finite")
    argv = launch["argv"]
    if not isinstance(argv, list) or not argv or any(not isinstance(s, str) or not s for s in argv):
        raise ProvenanceRefused("actual launch argv must be a non-empty string array")
    harness = want["harness"]
    adapter = {"codex": codex_adapter, "gemini": gemini_adapter}.get(harness)
    if adapter is None:
        raise ProvenanceRefused(f"unknown vendor harness {harness!r}")
    try:
        expected_argv = adapter.argv(want["sent"], model=want["model"], mode=want["mode"],
                                     session_id=want["vendor_session_id"] if want["ordinal"] > 1 else None,
                                     first=want["ordinal"] == 1)
    except ValueError as exc:
        raise ProvenanceRefused(f"invalid registered invocation: {exc}") from None
    if argv != expected_argv:
        raise ProvenanceRefused("actual launch differs from registered model/mode/prompt/resume invocation")
    return {"requested_model": _fact(want["model"], "actual-launch"),
            "permission_mode": _fact(want["mode"], "actual-launch"),
            "cwd": _fact(launch["cwd"], "actual-launch")}


def referenced_bytes(folder: Path, ref: dict) -> bytes:
    if not isinstance(ref, dict) or set(ref) != {"file", "sha256"}:
        raise ProvenanceRefused("evidence reference has an unknown schema")
    name = ref["file"]
    if not isinstance(name, str) or not name or Path(name).name != name or name in (".", ".."):
        raise ProvenanceRefused("evidence reference is not a confined basename")
    try:
        raw = _regular_bytes(Path(folder) / name)
    except tv.ViewError as exc:
        raise ProvenanceRefused(str(exc)) from None
    if hashlib.sha256(raw).hexdigest() != ref["sha256"]:
        raise ProvenanceRefused("evidence bytes differ from their reference")
    return raw


def version_fact(harness: str, folder: Path, ref: dict, *, expected: str) -> dict:
    """A retained bare CLI --version stdout; invocation/preflight binding is separate."""
    adapter = {"codex": codex_adapter, "gemini": gemini_adapter}.get(harness)
    if adapter is None or not isinstance(expected, str) or not expected or expected == "PENDING":
        raise ProvenanceRefused("observed version requires a known harness and measured pin")
    try:
        text = referenced_bytes(folder, ref).decode("utf-8").strip()
    except UnicodeError:
        raise ProvenanceRefused("version stdout is not UTF-8") from None
    found = adapter.VERSION_FORM.fullmatch(text)
    if found is None or found.group(1) != expected:
        raise ProvenanceRefused("observed CLI version differs from the image/version pin")
    return _fact(found.group(1), "observed-version")


def pinned_files(folder: Path, refs: dict, expected: dict, *, source: str) -> dict:
    """Retained config/instruction/source bytes against frozen hashes.

    This proves byte correspondence, not that a CLI actually loaded these files.
    Launch/config-directory/preflight binding must establish that separately.
    """
    if source not in ("per-take-config", "pinned-instructions", "pinned-vendor-source"):
        raise ProvenanceRefused("unknown pinned-file source kind")
    if not isinstance(refs, dict) or not isinstance(expected, dict) or not expected or set(refs) != set(expected):
        raise ProvenanceRefused("retained file set differs from frozen source set")
    out = {}
    for name, digest in expected.items():
        if not isinstance(name, str) or not name or not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ProvenanceRefused("pinned source name or hash is absent, PENDING or malformed")
        raw = referenced_bytes(folder, refs[name])
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ProvenanceRefused(f"retained source {name!r} differs from its frozen bytes")
        out[name] = _fact(digest, source)
    return out


def session_facts(harness: str, folder: Path, ref: dict, *, ordinal: int, readers=None) -> dict:
    """Native bytes are decoded by a separate registered session reader.

    A generic reader may retain optional None values. Later per-harness admission
    must still require Codex requested model from each rollout turn_context, and
    Gemini requested model from init plus every stats.models key. These are not
    interchangeable sources. Gemini native-session model absence is permitted;
    absence of native prompt/output/session identity is never permitted.
    """
    readers = NATIVE_SESSION_READERS if readers is None else readers
    if harness not in ("codex", "gemini"):
        raise ProvenanceRefused("unknown native-session harness")
    if type(ordinal) is not int or ordinal < 1:
        raise ProvenanceRefused("native session ordinal must be a positive integer")
    reader = readers.get(harness)
    if not callable(reader):
        raise ProvenancePending(f"no reviewed native-session reader for {harness}")
    facts = reader(referenced_bytes(folder, ref), ordinal)
    if not isinstance(facts, dict) or set(facts) != SESSION_KEYS:
        raise ProvenanceRefused("native-session reader returned an unknown fact schema")
    for key, value in facts.items():
        if key == "output":
            if not isinstance(value, list):
                raise ProvenanceRefused("native output projection must be a list")
        elif value is None and key in OPTIONAL_NATIVE:
            continue
        elif not isinstance(value, str) or not value or value == "PENDING":
            raise ProvenanceRefused(f"native-session {key} is absent or invalid")
    return {key: None if value is None else _fact(value, "native-session") for key, value in facts.items()}


def cross_check(stream: dict, session: dict) -> list[str]:
    """Names of missing/disagreeing native sources; never substitutes a desired value."""
    problems = []
    for key in ("session_id", "sent", "output", "requested_model"):
        got = session.get(key)
        if key == "requested_model" and got is None:
            continue
        if (not isinstance(got, dict) or set(got) != {"value", "source"} or
                got["source"] != "native-session" or key not in stream or got["value"] != stream[key]):
            problems.append(key)
    return problems


def session_history_facts(harness: str, folder: Path, refs: list, *, readers=None) -> list:
    """Bind each retained snapshot to every previously checked interaction.

    A later snapshot must reproduce the complete original facts, including None
    values, and preserve native session identity. This is not proof that there
    are no extra interactions: the eventual semantic reader/aggregate admission
    must independently reject extra or unassigned native interactions. Missing
    ordinal errors propagate; none is read as an empty or successful turn.
    """
    if not isinstance(refs, list) or not refs:
        raise ProvenanceRefused("native session history requires retained snapshots")
    known, names = [], set()
    for ordinal, ref in enumerate(refs, 1):
        # Validate the reference before using its name; no registry fallback.
        current = deepcopy(session_facts(harness, folder, ref, ordinal=ordinal, readers=readers))
        if ref["file"] in names:
            raise ProvenanceRefused("native session snapshots must use unique retained filenames")
        names.add(ref["file"])
        if known and current["session_id"] != known[0]["session_id"]:
            raise ProvenanceRefused("native session identity changed across snapshots")
        for previous_ordinal, previous in enumerate(known, 1):
            repeated = session_facts(harness, folder, ref, ordinal=previous_ordinal, readers=readers)
            if repeated != previous:
                raise ProvenanceRefused("later native snapshot rewrites a previously checked interaction")
        known.append(current)
    return known
