#!/usr/bin/env python3
"""A record carrying a line separator other than newline fails closed at both ends (glitch-b5's ruling on review r8's
finding 1, 16 Oct 2026).

Claude Code's writer (JSON.stringify) leaves exactly U+2028, U+2029 and U+0085 raw inside strings. str.splitlines() also
splits on them (and on \\r, \\x0b, \\x0c and \\x1c-\\x1e), so an assistant record carrying one was dropped by round 3's transcript reader
(evals/transcript.py, kept as it is: round 3 reproduces from it) and by the driver's stream readers: a wait point the
agent reached read did-not-reach, and readers-disagree compares user text only. So:

  L-driver    the driver's stream reader (claude_code_adapter.read_stream, the turn's stdout) refuses a stream carrying
              any of those separators (StreamError; after the exec it is an executed turn's refusal, so the take or
              walk stops for a ruling); the stream file is opened with newline="", which keeps a \\r the file holds,
              though box/run_take's capture has already translated a \\r from the harness (review r9), so on the real
              road \\r is the checker's to refuse; the
              cross-check names a session file carrying one (a problem, never a crash). A plain stream still reads.
  L-split     the driver's other readers split on "\\n" alone: drive.stream_split, drive.stream_init_source,
              drive.modes_recorded and mode_binding.modes_recorded read a record carrying U+2028 whole.
  L-checker   check_take.transcript_line_problems refuses a transcript in which a line carries one of the separators,
              or a non-blank line is not JSON: [transcript-unreadable], routed by the generic operator-reason rows
              like harness-condition-violated; check4 and check4_walk both add it. The reviewer's u2028.py case and a
              joined "A<LS>B" line refuse; its control (a space) and blank lines do not.
  L-witness   each clause dropped in memory turns a check red.

SUPERSEDED IN PART (lane pf1-l3, the lane orchestrator's ruling on the closure check of 8cf492b2, 24 Oct 2026):
U+2028, U+2029 and U+0085 are legal inside a JSON string and every reader splits on "\n" alone, so a record carrying
one is READ whole by both ends, never refused (the refusal let an agent void and re-run its own take by printing one
character); the C0 separators (never legal raw in a JSON string) are still refused, and a line two records are
joined into is still not JSON, so the checker still refuses it.

Synthetic fixtures only.
"""

from __future__ import annotations

import ast
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(Path(__file__).resolve().parent))

ct = cca = drive = mode_binding = None


def setUpModule():
    global ct, cca, drive, mode_binding
    saved = list(sys.path)
    import check_take as ct
    import claude_code_adapter as cca
    import drive
    import mode_binding
    sys.path[:] = saved


LS = "\u2028"
SEPARATORS = ("\r", "\x0b", "\x0c", "\x1c", "\x1d", "\x1e")             # refused (C0, never legal raw in JSON)
JSON_LEGAL = ("\x85", "\u2028", "\u2029")                                 # read whole (pf1-l3)
USER = {"type": "user", "message": {"role": "user", "content": "please start"}, "permissionMode": "bypassPermissions"}
INIT = {"type": "system", "subtype": "init", "session_id": "s", "model": "m", "permissionMode": "bypassPermissions",
        "claude_code_version": "2.1.296", "apiKeySource": "none", "tools": ["Bash"]}


def said(text):
    return {"type": "assistant", "session_id": "s",
            "message": {"id": "msg_1", "model": "m", "role": "assistant", "content": [{"type": "text", "text": text}]}}


def jsonl(*recs) -> str:
    return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in recs)


def driver_problems(mod=None) -> list:
    mod = mod or cca
    out = []
    try:
        mod.read_stream(jsonl(INIT, said("ok READY-MARK")))
    except mod.StreamError as e:
        out.append(f"L-driver: a plain stream is refused: {e}")
    for sep in SEPARATORS:
        raw = json.dumps(said("ok_READY-MARK")).replace("ok_", "ok" + sep)     # written raw, as a writer would leave it
        for name, text in (("inside a record", jsonl(INIT) + raw + "\n"),
                           ("joining two records", json.dumps(INIT) + sep + json.dumps(said("READY-MARK")) + "\n")):
            try:
                mod.read_stream(text)
                out.append(f"L-driver: a stream with {sep!r} {name} was read")
            except mod.StreamError:
                pass
    for sep in JSON_LEGAL:
        raw = json.dumps(said("ok_READY-MARK"), ensure_ascii=False).replace("ok_", "ok" + sep)
        try:
            got = mod.read_stream(jsonl(INIT) + raw + "\n")
            if "READY-MARK" not in got["agent_text"] or sep not in got["agent_text"]:
                out.append(f"L-driver: a record carrying {sep!r} lost its text: {got['agent_text']!r}")
        except mod.StreamError as e:
            out.append(f"L-driver: a record carrying {sep!r} inside a string was refused: {e}")
    got = mod.cross_check([], jsonl(said("a" + LS + "b")), session_id="s")
    if any("separator" in g for g in got):
        out.append(f"L-driver: the cross-check refuses a session file carrying U+2028 inside a string: {got}")
    # the second closure check of f0c0eb1d: a session file the driver cannot split is named, never crashed on
    got = mod.cross_check([], jsonl(said("a")) .replace('"a"', '"a\x0bb"'), session_id="s")
    if not any("separator" in g for g in got):
        out.append(f"L-driver: the cross-check does not name a session file carrying \\x0b: {got}")
    src = Path(mod.__file__).read_text()
    if 'with open(got["stream_path"], encoding="utf-8", errors="surrogateescape", newline="") as fh:' not in src:
        out.append("L-driver: the stream file is not opened with newline=\"\"")
    return out


def split_problems(drv=None, mb=None) -> list:
    drv, mb = drv or drive, mb or mode_binding
    out = []
    stdout = jsonl(INIT, said("ok" + LS + "READY-MARK"))
    if "READY-MARK" not in drv.stream_split(stdout)[0]:
        out.append("L-split: drive.stream_split drops a record carrying U+2028")
    init = dict(INIT, note="a" + LS + "b")
    if drv.stream_init_source(jsonl(init)) != "none":
        out.append("L-split: drive.stream_init_source drops an init carrying U+2028")
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "transcript.jsonl"
        p.write_text(jsonl(dict(USER, message={"role": "user", "content": "a" + LS + "b"})), encoding="utf-8")
        for name, fn in (("drive", drv.modes_recorded), ("mode_binding", mb.modes_recorded)):
            if fn(p) != {"bypassPermissions"}:
                out.append(f"L-split: {name}.modes_recorded drops a record carrying U+2028")
    return out


def transcript(text: str) -> Path:
    d = Path(tempfile.mkdtemp())
    p = d / "transcript.jsonl"
    p.write_bytes(text.encode("utf-8"))
    return p


def checker_problems(mod=None) -> list:
    mod = mod or ct
    out = []
    refused = {
        'a joined "A<LS>B" line': json.dumps(USER) + LS + json.dumps(said("READY-MARK")) + "\n",
        "a non-blank line that is not JSON": jsonl(USER) + "not json\n" + jsonl(said("x")),
        "half a record": jsonl(USER) + json.dumps(said("x"))[:20] + "\n",
        "a carriage return line end": json.dumps(USER) + "\r\n",
    }
    # written raw into the line (json.dumps escapes the C0 ones, so a writer that left one raw is what this models)
    refused.update({f"the separator {s!r}": jsonl(USER) + json.dumps(said("a_b")).replace("a_b", "a" + s + "b") + "\n"
                    for s in SEPARATORS})
    for name, text in refused.items():
        got = mod.transcript_line_problems(transcript(text))
        if mod.reason_ids(got) != ["transcript-unreadable"]:
            out.append(f"L-checker {name}: {got}")
    for name, text in (("the control (a space)", jsonl(USER, said("ok READY-MARK"))),
                       ("the reviewer's u2028.py case, read whole (pf1-l3)", jsonl(USER, said("ok" + LS + "READY-MARK"))),
                       ("U+2029 inside a string (pf1-l3)", jsonl(USER, said("ok\u2029READY-MARK"))),
                       ("U+0085 inside a string (pf1-l3)", jsonl(USER, said("ok\x85READY-MARK"))),
                       ("blank lines", jsonl(USER) + "\n   \n" + jsonl(said("x"))), ("empty", "")):
        got = mod.transcript_line_problems(transcript(text))
        if got:
            out.append(f"L-checker {name}: refused {got}")
    tree = ast.parse(Path(mod.__file__).read_text())
    for fn in ("check4", "check4_walk"):
        body = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == fn)
        if "transcript_line_problems" not in {c.func.id for c in ast.walk(body)
                                               if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}:
            out.append(f"L-checker: {fn} does not add transcript_line_problems")
    return out


def routing_problems() -> list:
    import routing
    t = routing.load_table()
    out = []
    if "transcript-unreadable" not in t["operator_reasons"] or \
            "transcript-unreadable" not in t["operator_reasons_round4"]["ids"]:
        out.append("L-routing: transcript-unreadable is not a round-4 operator reason")
    if routing.check_table(t):
        out.append(f"L-routing: {routing.check_table(t)}")
    return out


def mutant(mod, old: str, new: str):
    src = Path(mod.__file__).read_text(encoding="utf-8")
    if src.count(old) != 1:
        raise AssertionError(f"mutation site occurs {src.count(old)} times in {mod.__file__}: {old!r}")
    m = types.ModuleType(mod.__name__ + "_mutant")
    m.__file__ = mod.__file__
    sys.modules[m.__name__] = m
    try:
        exec(compile(src.replace(old, new), mod.__file__, "exec"), m.__dict__)
    finally:
        del sys.modules[m.__name__]
    return m


class TheLineSeparators(unittest.TestCase):
    def test_l_driver(self):
        self.assertEqual(driver_problems(), [])

    def test_l_split(self):
        self.assertEqual(split_problems(), [])

    def test_l_checker(self):
        self.assertEqual(checker_problems(), [])

    def test_l_routing(self):
        self.assertEqual(routing_problems(), [])

    def test_l_witnesses(self):
        cases = (
            ("the stream's separators unread", lambda: driver_problems(mutant(
                cca, "    if any(s in (text or \"\") for s in LINE_SEPARATORS):", "    if False:"))),
            ("the cross-check crashes", lambda: driver_problems(mutant(
                cca, "    except StreamError as e:\n        return [str(e)]\n", "    except KeyError as e:\n        return [str(e)]\n"))),
            ("the JSON-legal separators refused again", lambda: driver_problems(mutant(
                cca, 'LINE_SEPARATORS = ("\\r", "\\x0b", "\\x0c", "\\x1c", "\\x1d", "\\x1e")',
                'LINE_SEPARATORS = ("\\r", "\\x0b", "\\x0c", "\\x1c", "\\x1d", "\\x1e", "\\u2028")'))),
            ("the checker's separators unread", lambda: checker_problems(mutant(
                ct, '    seps = sorted({f"U+{ord(s):04X}" for s in TRANSCRIPT_LINE_SEPARATORS if s in text})',
                "    seps = []"))),
            ("the checker's JSON unread", lambda: checker_problems(mutant(
                ct, "            bad.append(i)\n", "            pass\n"))),
            ("drive.stream_split on splitlines", lambda: split_problems(drv=mutant(
                drive, '    for raw in stdout.split("\\n"):', "    for raw in stdout.splitlines():"))),
        )
        for name, run in cases:
            with self.subTest(witness=name):
                try:
                    got = run()
                except Exception as e:  # noqa: BLE001 - a mutant that crashes a reader is red too
                    got = [f"raised {type(e).__name__}"]
                print(f"\nWITNESS {name}: {'red' if got else 'NOT KILLED'} ({got[:1]})", end=" ", file=sys.stderr)
                self.assertTrue(got, name)


if __name__ == "__main__":
    unittest.main()
