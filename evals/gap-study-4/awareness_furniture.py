#!/usr/bin/env python3
"""The awareness furniture check: which pre-registered phrases match the harness's own records.

    python3 evals/gap-study-4/awareness_furniture.py                            round 3's committed transcripts
    python3 evals/gap-study-4/awareness_furniture.py FILE ...                   the named transcript.jsonl files
    python3 evals/gap-study-4/awareness_furniture.py --harness codex [FILE ...]   every rehearsals/w-o* walk, or FILEs
    python3 evals/gap-study-4/awareness_furniture.py --harness gemini [FILE ...]  every rehearsals/w-g* walk, or FILEs

The plan's gotcha for `graders/awareness.py`: "Grep the phrase list against a real transcript's
attachment records before freezing. Round 3 nearly voided takes on its own harness furniture." The
grader excludes `harness` events by kind; this check shows what that exclusion keeps out. It runs
`awareness.PHRASES` against the `harness` events of every transcript, read through the view's parser
for the take's harness (`--harness`; without it `transcript_view.ROUND3_HARNESS`, round 3's takes carrying none).

It reads each transcript twice through the view, both times whole: once for its events (so a transcript the view
refuses fails the check), then for its raw items (`transcript_view.raw_items`), so each match has its one raw record
type. Only `harness` items are scanned. Item G (glitch-6b, 15 Oct 2026): it used to read the second pass one line at a
time, and a scheduled-wakeup line read alone has no earlier ScheduleWakeup call, so the check refused a w006-shaped
take the view reads.

THE NATIVE SESSION (lane d8-furniture, 21 Oct 2026; D8 lines 352 and 494). A codex or gemini transcript is the host's
turn envelopes; the view reads the per-turn streams, which hold neither the CLI's instructions (Codex's system prompt,
developer and AGENTS.md messages; Gemini's session context and GEMINI.md) nor, for Gemini, what a read returned (every
successful read_file result is "" in the stream). So for those two harnesses the check also reads the walk's native
session (session/native-turn-N.jsonl, the last one; each snapshot must be a byte prefix of the next) and scans two more
families of text, each row's raw type naming its family:
  furniture:<record kind>      the string leaves at the harness's FURNITURE positions (box/scan_record.py), the
                               account positions excluded (they are never scanned or printed)
  native-result:<tool>         what each tool call returned to the model, once per call (Gemini's resume re-records,
                               ids ending "_response", are skipped; Codex's output after the CLI's banner)
Native-result rows are not furniture: they are the agent-visible environment the stream withholds, scanned so a zero is
a reading. Every record kind of the native session must be a FURNITURE kind (record_kind's rule), or the check refuses
the walk, naming the kind: the pre-registered list is complete on every walk it reads, by check.

It prints only, per match row: the phrase, the raw record type, the file and a count, tab-separated;
then one closing line. It NEVER prints a matched line or any text around a match. It exits 0 when
every transcript was read (whatever it found), 1 when the view refused one, a native session was refused, or none was
found.

Round 3's transcripts are opened in the working tree, read-only (the brief's named exception to
`git show`; `copy_manifest.py --check` pins `evals/gap-study-3` unchanged).

No model is called anywhere in this module. Standard library only.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import mode_binding  # noqa: E402  (WALKS_DIR: the walks' one record-root name, test_walk_layout L1)
import transcript_view as view  # noqa: E402
from box import scan_record  # noqa: E402
from graders import awareness  # noqa: E402

REPO = HERE.parent.parent
ROUND3_TRANSCRIPTS = REPO / "evals" / "gap-study-3" / "transcripts"
REHEARSALS = HERE / mode_binding.WALKS_DIR
WALK_PREFIX = {"codex": "w-o", "gemini": "w-g"}
NATIVE = re.compile(r"native-turn-([1-9][0-9]*)\.jsonl")
# Codex's CLI-injected user message (D8-READ-w-o46 section 3 item 5): every content item of one of these kinds, and no
# metadata.retained_source, which every operator and assistant message carries.
CODEX_INJECTED_KINDS = ("agents_md.instructions", "environments.environment_context")
GEMINI_CONTEXT_OPEN = "<session_context>"


class NativeRefused(ValueError):
    """A native session this check cannot read as pre-registered. Its message names a kind or a file, never text."""


def round3_files() -> list[Path]:
    return sorted(ROUND3_TRANSCRIPTS.glob("*/*/*/*/transcript.jsonl"))


def walk_files(harness: str) -> list[Path]:
    return sorted(p / "transcript.jsonl" for p in REHEARSALS.glob(WALK_PREFIX[harness] + "*")
                  if (p / "transcript.jsonl").is_file())


# ---- the record-kind rule (box/scan_record.FURNITURE's `record`) ---------------------------------------------------

def record_kind(harness: str, file: str, rec) -> str:
    """The FURNITURE record kind of one record of `harness`'s `file` ("session" or "stream")."""
    if not isinstance(rec, dict):
        return "<not an object>"
    if harness == "codex" and file == "session":
        p = rec.get("payload") if isinstance(rec.get("payload"), dict) else {}
        if rec.get("type") == "response_item" and p.get("type") == "message":
            role = p.get("role")
            kinds = (p.get("internal_chat_message_metadata_passthrough") or {}).get("content_item_kinds") or []
            meta = rec.get("metadata") if isinstance(rec.get("metadata"), dict) else {}
            if role == "user" and kinds and all(k in CODEX_INJECTED_KINDS for k in kinds) \
                    and "retained_source" not in meta:
                return "response_item/message/user:injected"
            return f"response_item/message/{role}"
        return "/".join(str(x) for x in (rec.get("type"), p.get("type")) if x)
    if harness == "codex":
        item = rec.get("item") if isinstance(rec.get("item"), dict) else {}
        return "/".join(str(x) for x in (rec.get("type"), item.get("type")) if x)
    if harness == "gemini" and file == "session":
        if "type" in rec:
            content = rec.get("content")
            if rec["type"] == "user" and isinstance(content, list) and content and isinstance(content[0], dict) \
                    and str(content[0].get("text", "")).startswith(GEMINI_CONTEXT_OPEN):
                return "user:session_context"
            return str(rec["type"])
        if set(rec) == {"$set"} and isinstance(rec["$set"], dict):
            return "$set:" + ",".join(sorted(rec["$set"]))
        if set(rec) == {"$patch"}:
            return "$patch"
        if "sessionId" in rec and "projectHash" in rec:
            return "<header>"
        return "<unknown: " + ",".join(sorted(map(str, rec))) + ">"
    if harness == "gemini":
        return str(rec.get("type"))
    if rec.get("type") == "attachment" and isinstance(rec.get("attachment"), dict):
        return f"attachment:{rec['attachment'].get('type')}"
    if file == "session" and rec.get("type") == "user" and rec.get("isMeta") is True:
        # the two isMeta records transcript_view admits as harness (its own predicates decide admission)
        if rec.get("turnCompanion") is True:
            return f"user:{view.CC_NO_OUTPUT_NUDGE}"
        if rec.get("turnOrigin") == view.CC_WAKEUP_TURN_ORIGIN:
            return f"user:{view.CC_SCHEDULED_WAKEUP}"
    return "/".join(str(x) for x in (rec.get("type"), rec.get("subtype")) if x)


# ---- positions ---------------------------------------------------------------------------------------------------

def _leaves(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from _leaves(v, f"{path}.{k}" if path else str(k))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from _leaves(v, f"{path}[{i}]")
    elif isinstance(o, str):
        yield path, o


def _field_re(field: str):
    """A FURNITURE field as a pattern over leaf paths: "[]" any index, "[n]" that one; the field or anything below."""
    if field == "*":
        return re.compile(r".*", re.S)
    return re.compile(re.escape(field).replace(r"\[\]", r"\[[0-9]+\]") + r"(?:$|[.\[].*)", re.S)


def _account_paths(harness: str, file: str, kind: str) -> tuple:
    return tuple(_field_re(f) for e in scan_record.account_positions(harness)
                 if e["file"] == file and e["record"] == kind for f in e["fields"])


def furniture_strings(harness: str, file: str, rec) -> list[str]:
    """The string leaves of `rec` at its kind's FURNITURE positions, less every account position. Raises NativeRefused
    for a kind FURNITURE does not list."""
    kind = record_kind(harness, file, rec)
    entries = [e for e in scan_record.furniture_positions(harness)
               if e["file"] == file and e["record"] == kind and not e["account"]]
    known = any(e["file"] == file and e["record"] == kind for e in scan_record.furniture_positions(harness))
    if not known:
        raise NativeRefused(f"a {harness} {file} record kind outside its furniture list: {kind}")
    want = [_field_re(f) for e in entries for f in e["fields"]]
    skip = _account_paths(harness, file, kind)
    return [s for path, s in _leaves(rec)
            if any(p.fullmatch(path) for p in want) and not any(p.fullmatch(path) for p in skip)]


def native_results(harness: str, rec, names: dict) -> list[tuple[str, str]]:
    """(tool, text) for what one record returned to the model; `names` maps a Codex call id to its tool name."""
    out = []
    if harness == "codex":
        p = rec.get("payload") if isinstance(rec.get("payload"), dict) else {}
        if rec.get("type") == "response_item" and p.get("type") == "custom_tool_call":
            names[p.get("call_id")] = str(p.get("name"))
        if rec.get("type") == "response_item" and p.get("type") == "custom_tool_call_output":
            tool = names.get(p.get("call_id"), "custom_tool_call_output")
            for part in (p.get("output") or [])[1:]:          # [0] is the CLI's banner, a FURNITURE position
                if isinstance(part, dict) and isinstance(part.get("text"), str):
                    out.append((tool, part["text"]))
        return out
    if rec.get("type") == "user" and isinstance(rec.get("content"), list):
        for c in rec["content"]:
            fr = c.get("functionResponse") if isinstance(c, dict) else None
            if isinstance(fr, dict) and isinstance(fr.get("response"), dict):
                for k in ("output", "error"):
                    if isinstance(fr["response"].get(k), str):
                        out.append((str(fr.get("name")), fr["response"][k]))
    return out


def native_session(walk: Path) -> Path:
    """The walk's last native snapshot; refused unless each snapshot is a byte prefix of the next."""
    snaps = sorted(((int(m.group(1)), p) for p in (walk / "session").glob("native-turn-*.jsonl")
                    if (m := NATIVE.fullmatch(p.name))), key=lambda t: t[0])
    if not snaps:
        raise NativeRefused(f"no native session under {walk.name}/session")
    if [n for n, _ in snaps] != list(range(1, len(snaps) + 1)):
        raise NativeRefused(f"{walk.name}: native snapshots are not numbered 1..{len(snaps)}")
    for (_, a), (_, b) in zip(snaps, snaps[1:]):
        if not b.read_bytes().startswith(a.read_bytes()):
            raise NativeRefused(f"{walk.name}: {a.name} is not a prefix of {b.name}")
    return snaps[-1][1]


def native_counts(harness: str, walk: Path) -> dict[tuple[str, str], int]:
    """{(phrase, raw type): count} over one walk's native session: its furniture positions and its tool results."""
    counts: dict[tuple[str, str], int] = {}

    def add(text, raw_type):
        for phrase in awareness.scan(text):
            counts[(phrase, raw_type)] = counts.get((phrase, raw_type), 0) + 1

    names: dict = {}
    for i, ln in enumerate(view.jsonl_lines(native_session(walk).read_text(encoding="utf-8")), 1):
        try:
            rec = json.loads(ln)
        except ValueError:
            raise NativeRefused(f"{walk.name}: native line {i} is not JSON") from None
        kind = record_kind(harness, "session", rec)
        for s in furniture_strings(harness, "session", rec):
            add(s, f"furniture:{kind}")
        if harness == "gemini" and rec.get("id", "").endswith("_response"):
            continue
        for tool, text in native_results(harness, rec, names):
            add(text, f"native-result:{tool}")
    return counts


def furniture(harness: str, path: Path) -> dict[tuple[str, str], int]:
    """{(phrase, raw record type): count} over the harness events of one transcript, and for codex and gemini over its
    walk's native session (native_counts)."""
    view.events(harness, path)  # the whole file first: a refusal fails the check
    counts: dict[tuple[str, str], int] = {}
    for it in view.raw_items(harness, path):
        if it.kind != view.HARNESS:
            continue
        for phrase in awareness.scan(it.text):
            counts[(phrase, it.raw_type)] = counts.get((phrase, it.raw_type), 0) + 1
    if harness in WALK_PREFIX:
        for k, n in native_counts(harness, Path(path).parent).items():
            counts[k] = counts.get(k, 0) + n
    return counts


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    harness = view.ROUND3_HARNESS
    if args[:1] == ["--harness"]:
        if len(args) < 2 or args[1] not in view.PARSERS:
            print(f"awareness_furniture: --harness takes one of {sorted(view.PARSERS)}")
            return 1
        harness, args = args[1], args[2:]
    if args:
        files = [Path(a) for a in args]
    else:
        files = walk_files(harness) if harness in WALK_PREFIX else round3_files()
    if not files:
        print("awareness_furniture: no transcript found")
        return 1
    rows = 0
    families: dict[str, int] = {}
    for f in files:
        try:
            counts = furniture(harness, f)
        except (view.ViewError, NativeRefused, OSError) as e:
            print(f"awareness_furniture: {f}: refused: {type(e).__name__}" +
                  (f": {e}" if isinstance(e, NativeRefused) else ""))
            return 1
        try:
            name = f.resolve().relative_to(REPO)
        except ValueError:
            name = f
        for (phrase, raw_type), n in sorted(counts.items()):
            print(f"{phrase}\t{raw_type}\t{name}\t{n}")
            rows += 1
            fam = raw_type.split(":", 1)[0] if raw_type.startswith(("furniture:", "native-result:")) else "harness"
            families[fam] = families.get(fam, 0) + n
    print(f"awareness_furniture: {rows} match row(s) over {len(files)} transcript(s); "
          f"{len(awareness.PHRASES)} phrases; harness {harness}; harness events only"
          + ("" if harness not in WALK_PREFIX else
             f", plus the native session's furniture and tool results; matches by family "
             f"{dict(sorted(families.items()))}"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
