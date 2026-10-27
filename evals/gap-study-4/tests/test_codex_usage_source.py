#!/usr/bin/env python3
"""Arm O's turn.completed usage table, read from the pinned Codex CLI's own exec event struct (lane vendor-b14 round 1
B15; glitch-26's ruling, Mon 19 Oct 2026).

The second practice walk w-o3 executed turn 1 and the drive held its take: "turn.completed.usage carries key(s) with no
entry: ['cache_write_input_tokens']" (codex_adapter.read_stream against transcript_codex.USAGE_KEYS). The table was
D8 section 1's documented four keys, never read against the pinned source. B15 reads it from openai/codex at tag
rust-v0.162.1 (commit 092d3acd): codex-rs/exec/src/exec_events.rs, struct Usage, the payload of TurnCompletedEvent,
which codex exec prints with serde_json::to_string (codex-rs/exec/src/event_processor_with_jsonl_output.rs).

What the pinned struct serializes. Five i64 fields, none with skip_serializing_if (the same file uses that attribute
elsewhere, on fields meant to be left out when unset); cache_write_input_tokens carries #[serde(default)], which is
read only when deserializing (a JSON object without the key still deserializes into the struct), never when
serializing. So every turn.completed exec prints carries all five keys: the always-present set is the five, the
present-when-set set is empty, and a line without cache_write_input_tokens is refused like a line without any other.

  U1  a SYNTHETIC turn.completed line built from the pinned struct (each field a distinct count) passes check_record,
      decode and CodexParser, and codex_adapter.read_stream reads a synthetic stream that ends with it, its usage the
      five counts as written.
  U2  the table is the struct: transcript_codex.USAGE_KEYS is exactly the five fields in the struct's order, and
      codex_usage_sources records each field's file, line and text, the struct's sha256, the empty present-when-set
      set, and the serializer's lines.
  U3  still refused by read_stream: a line missing any one field (cache_write_input_tokens among them), a line with an
      invented key (named in the refusal), and a line whose value for any field is not a count (a string, a float, a
      bool, a negative number, null).
  U4  `--sources <a folder holding the pinned files at their repository paths>` (on demand, never in the battery: the
      source is not in this repository): each cited file's sha256 is the recorded one and each cited line holds its
      recorded text.

`--witnesses` builds each mutant in memory (transcript_codex, codex_adapter or codex_usage_sources compiled from its
text with one edit, never written) and runs U1 to U3 against it: each must turn at least one red.

Synthetic strings only: no recorded stream, no held take's bytes, no model, network or vendor package is read by the
battery. Standard library only.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import sys
import types
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import codex_adapter as ca  # noqa: E402
import transcript_codex as tc  # noqa: E402

try:
    import codex_usage_sources as cus  # noqa: E402
except ImportError:                      # the red state: no sources record yet; U2 says so
    cus = None

PIN = {"repo": "openai/codex", "tag": "rust-v0.162.1", "commit": "092d3acd6bec3e3a14bdc7e7a2810ab628ab759d"}
STRUCT_FILE = "codex-rs/exec/src/exec_events.rs"
EMIT_FILE = "codex-rs/exec/src/event_processor_with_jsonl_output.rs"
FILE_SHA256 = {STRUCT_FILE: "dafa872d7e86a099e56e28a329dcb9c03db90ed768c3b88cca8c91d46dc1d0e5",
               EMIT_FILE: "bc296541b385f9b4ca2c28cc638e25a8d6b1332b2cd67f5a03eaa97a3d612b19"}
# The pinned struct Usage (exec_events.rs:59-73), field by field: (name, line, text). Spelled here from the source,
# never read from the module under test.
PINNED_USAGE = (
    ("input_tokens", 63, "    pub input_tokens: i64,"),
    ("cached_input_tokens", 65, "    pub cached_input_tokens: i64,"),
    ("cache_write_input_tokens", 68, "    pub cache_write_input_tokens: i64,"),
    ("output_tokens", 70, "    pub output_tokens: i64,"),
    ("reasoning_output_tokens", 72, "    pub reasoning_output_tokens: i64,"),
)
FIELDS = tuple(f for f, _, _ in PINNED_USAGE)
NEW_FIELD = "cache_write_input_tokens"
# Every other cited line: the struct heads, the deserialize-only default, and the serializer road.
PINNED_LINES = (
    (STRUCT_FILE, 50, "pub struct TurnCompletedEvent {"),
    (STRUCT_FILE, 51, "    pub usage: Usage,"),
    (STRUCT_FILE, 60, "#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, TS, Default)]"),
    (STRUCT_FILE, 61, "pub struct Usage {"),
    (STRUCT_FILE, 67, "    #[serde(default)]"),
    (EMIT_FILE, 108, "            serde_json::to_string(&event).unwrap_or_else(|err| {"),
    (EMIT_FILE, 125, "            cache_write_input_tokens: usage.total.cache_write_input_tokens,"),
    (EMIT_FILE, 533, "                        events.push(ThreadEvent::TurnCompleted(TurnCompletedEvent {"),
    (EMIT_FILE, 534, "                            usage: self.usage_from_last_total(),"),
)
COUNTS = dict(zip(FIELDS, (1200, 800, 64, 90, 40)))
TID = "019a0000-0000-7000-8000-000000000b15"
INVENTED = "total_tokens"
NOT_COUNTS = ("64", 6.4, True, -1, None)


def done_line(usage: dict) -> str:
    return json.dumps({"type": "turn.completed", "usage": usage})


def stream(usage: dict) -> str:
    recs = [{"type": "thread.started", "thread_id": TID}, {"type": "turn.started"},
            {"type": "item.completed", "item": {"id": "item_0", "type": "agent_message", "text": "synthetic reply"}}]
    return "\n".join([json.dumps(r) for r in recs] + [done_line(usage)]) + "\n"


def _refused(fn, err) -> str | None:
    """None when fn() raises err, else what it did instead."""
    try:
        got = fn()
    except err:
        return None
    except Exception as e:  # noqa: BLE001 - any other failure is not the refusal asked for
        return f"raised {type(e).__name__}: {e}"
    return f"returned {got!r:.120}"


def u1_parses(tcm, cam) -> list:
    out = []
    line = done_line(COUNTS)
    try:
        tcm.check_record(json.loads(line))
        tcm.decode(line)
        tcm.CodexParser().items(line)
    except Exception as e:  # noqa: BLE001
        out.append(f"U1: the pinned struct's turn.completed is refused by transcript_codex: {e}")
    try:
        got = cam.read_stream(stream(COUNTS))["usage"]
        if got != COUNTS:
            out.append(f"U1: read_stream reads the pinned struct's usage as {got}, not {COUNTS}")
    except Exception as e:  # noqa: BLE001
        out.append(f"U1: read_stream refuses the pinned struct's turn.completed: {e}")
    return out


def u2_table(tcm, cusm) -> list:
    out = []
    keys = tuple(getattr(tcm, "USAGE_KEYS", ()))
    if keys != FIELDS:
        out.append(f"U2: transcript_codex.USAGE_KEYS is {keys}, not the pinned struct's {FIELDS}")
    if cusm is None:
        return out + ["U2: no codex_usage_sources module records where each usage key was read"]
    if getattr(cusm, "PIN", None) != PIN:
        out.append(f"U2: codex_usage_sources.PIN is {getattr(cusm, 'PIN', None)}, not {PIN}")
    if getattr(cusm, "FILE_SHA256", None) != FILE_SHA256:
        out.append("U2: codex_usage_sources.FILE_SHA256 is not the pinned files' sha256")
    srcs = getattr(cusm, "USAGE_SOURCES", None)
    want = {f: {"file": STRUCT_FILE, "line": n, "text": t} for f, n, t in PINNED_USAGE}
    if not isinstance(srcs, dict) or tuple(srcs) != FIELDS:
        out.append(f"U2: codex_usage_sources.USAGE_SOURCES names {tuple(srcs or ())}, not {FIELDS}")
    else:
        for f in FIELDS:
            if srcs[f] != want[f]:
                out.append(f"U2: {f}'s source is {srcs[f]}, not {want[f]}")
    if getattr(cusm, "WHEN_SET", None) != ():
        out.append(f"U2: codex_usage_sources.WHEN_SET is {getattr(cusm, 'WHEN_SET', None)!r}: the pinned struct "
                   f"has no field serialized only when set")
    lines = getattr(cusm, "LINES", None)
    if tuple(lines or ()) != PINNED_LINES:
        out.append("U2: codex_usage_sources.LINES is not the struct heads, the default and the serializer lines")
    return out


def u3_refusals(cam) -> list:
    out = []
    for f in FIELDS:
        less = {k: v for k, v in COUNTS.items() if k != f}
        got = _refused(lambda: cam.read_stream(stream(less)), cam.StreamError)
        if got:
            out.append(f"U3: a turn.completed without {f} {got}")
    try:
        cam.read_stream(stream({**COUNTS, INVENTED: 9}))
        out.append(f"U3: a turn.completed with the invented key {INVENTED} is read")
    except cam.StreamError as e:
        if INVENTED not in str(e):
            out.append(f"U3: the invented key's refusal does not name it: {e}")
    except Exception as e:  # noqa: BLE001
        out.append(f"U3: the invented key raised {type(e).__name__}: {e}")
    for f in FIELDS:
        for bad in NOT_COUNTS:
            got = _refused(lambda: cam.read_stream(stream({**COUNTS, f: bad})), cam.StreamError)
            if got:
                out.append(f"U3: {f} = {bad!r} (not a count) {got}")
    return out


def problems(tcm=tc, cam=ca, cusm=cus) -> list:
    return u1_parses(tcm, cam) + u2_table(tcm, cusm) + u3_refusals(cam)


def source_problems(root: Path) -> list:
    out = []
    files = {}
    for rel, sha in FILE_SHA256.items():
        p = root / rel
        if not p.is_file():
            out.append(f"U4: {rel} is not under {root}")
            continue
        data = p.read_bytes()
        if hashlib.sha256(data).hexdigest() != sha:
            out.append(f"U4: {rel}'s sha256 is not {sha}")
        files[rel] = data.decode("utf-8").splitlines()
    cited = [(STRUCT_FILE, n, t) for _, n, t in PINNED_USAGE] + list(PINNED_LINES)
    for rel, n, text in cited:
        if rel in files and (n > len(files[rel]) or files[rel][n - 1] != text):
            out.append(f"U4: {rel}:{n} does not hold {text!r}")
    if STRUCT_FILE in files:
        body = files[STRUCT_FILE][58:73]
        if any("skip_serializing_if" in x for x in body):
            out.append("U4: the pinned struct Usage carries a skip_serializing_if: WHEN_SET is not empty")
    return out


class TestUsageSource(unittest.TestCase):
    def test_u1_the_pinned_structs_line_parses(self):
        self.assertEqual(u1_parses(tc, ca), [])

    def test_u2_the_table_is_the_struct(self):
        self.assertEqual(u2_table(tc, cus), [])

    def test_u3_missing_invented_and_non_count_refuse(self):
        self.assertEqual(u3_refusals(ca), [])


# ---- witnesses: one edit each, compiled in memory --------------------------------------------------------------------

class WitnessNotPerformed(AssertionError):
    pass


def _compiled(target, edits: tuple) -> types.ModuleType:
    with open(target.__file__, encoding="utf-8") as fh:
        src = fh.read()
    for old, new in edits:
        if src.count(old) != 1:
            raise WitnessNotPerformed(f"the anchor occurs {src.count(old)} times in {Path(target.__file__).name}: "
                                      f"{old[:60]!r}")
        src = src.replace(old, new)
    mod = types.ModuleType(Path(target.__file__).stem + "_b15_witness")
    mod.__file__ = target.__file__
    exec(compile(src, target.__file__ + " (witness)", "exec"), mod.__dict__)
    return mod


def _modules(where: str, edits: tuple):
    """(tc, ca, cus) with one module replaced by its mutant; a mutated tc is also the ca's tc."""
    if where == "tc":
        tcm = _compiled(tc, edits)
        cam = _compiled(ca, ())
        cam.tc = tcm
        return tcm, cam, cus
    if where == "ca":
        return tc, _compiled(ca, edits), cus
    return tc, ca, _compiled(importlib.import_module("codex_usage_sources"), edits)


_TC_KEYS = ('USAGE_KEYS = ("input_tokens", "cached_input_tokens", "cache_write_input_tokens", "output_tokens",\n'
            '              "reasoning_output_tokens")')
WITNESSES = {
    "new-key-dropped": ("tc", ((_TC_KEYS, 'USAGE_KEYS = ("input_tokens", "cached_input_tokens", "output_tokens",\n'
                                          '              "reasoning_output_tokens")'),)),
    "invented-key-tabled": ("tc", ((_TC_KEYS, _TC_KEYS[:-1] + ', "total_tokens")'),)),
    "missing-key-skipped": ("ca", (("vals = {k: rec[\"usage\"].get(k) for k in tc.USAGE_KEYS}",
                                 "vals = {k: rec[\"usage\"][k] for k in tc.USAGE_KEYS if k in rec[\"usage\"]}"),)),
    "missing-key-zero": ("ca", (("vals = {k: rec[\"usage\"].get(k) for k in tc.USAGE_KEYS}",
                             "vals = {k: rec[\"usage\"].get(k, 0) for k in tc.USAGE_KEYS}"),)),
    "new-key-any-value": ("ca", (("            if not all(_count(v) for v in vals.values()):",
                                  "            if not all(_count(v) for k, v in vals.items() if k != "
                                  "\"cache_write_input_tokens\"):"),)),
    "invented-key-admitted": ("ca", (("            extra = sorted(set(rec[\"usage\"]) - set(tc.USAGE_KEYS))",
                                      "            extra = []"),)),
    "source-line-moved": ("cus", (('"cache_write_input_tokens": {"file": STRUCT_FILE, "line": 68,',
                                   '"cache_write_input_tokens": {"file": STRUCT_FILE, "line": 67,'),)),
    "when-set-claimed": ("cus", (("WHEN_SET = ()", "WHEN_SET = (\"cache_write_input_tokens\",)"),)),
    "serializer-uncited": ("cus", (("    (EMIT_FILE, 108, ", "    (EMIT_FILE, 106, "),)),
}


def witnesses() -> int:
    red = 0
    import mutation_baseline  # lane t104-mutation-baseline: the unmutated selection runs first; a red one refuses (exit 3), nothing counted
    mutation_baseline.require_clean("test_codex_usage_source witnesses", lambda: [
        f"{where}: {x}" for where in sorted({w for w, _ in WITNESSES.values()}) for x in problems(*_modules(where, ()))])
    for name, (where, edits) in WITNESSES.items():
        try:
            found = problems(*_modules(where, edits))
        except WitnessNotPerformed as e:
            print(f"NOT PERFORMED {name}: {e}")
            continue
        if found:
            red += 1
            print(f"red   {name}: {len(found)} problem(s), first: {found[0]}")
        else:
            print(f"GREEN {name}: the mutant passes U1 to U3")
    print(f"test_codex_usage_source witnesses: {red}/{len(WITNESSES)} red")
    return 0 if red == len(WITNESSES) else 1


if __name__ == "__main__":
    if "--witnesses" in sys.argv:
        raise SystemExit(witnesses())
    if "--sources" in sys.argv:
        found = source_problems(Path(sys.argv[sys.argv.index("--sources") + 1]))
        for p in found:
            print(p)
        n = len(PINNED_USAGE) + len(PINNED_LINES)
        print(f"test_codex_usage_source sources: {len(found)} problems over {n} cited lines")
        raise SystemExit(1 if found else 0)
    unittest.main()
