#!/usr/bin/env python3
"""The launch journals that show the study conditions are read by position and bound to their turn and harness (the
r5 review NITs (a), (b) and (c) of ship head e471902f, queued by glitch-6b for before the freeze).

check_take.steer_condition_problems and denied_tool_problems read each turn's launch journal
(turn-N.jsonl.launch.json), box/run_take's record of the exec it submitted: {schema, harness, container_id, argv, cwd,
stream, started_at}, the argv [claude, -p, prompt, flags...] (run_take.check_claude_settings requires -p or --print at
position 1). Reproduced on 4ce3318f before the fix, each case below read clean ([] from both):

  J-print     (a) the prompt is argv[2], read by position. Before, any -p or --print anywhere skipped the token after it,
              so a stray --print before a second inline --settings hid it, and the "exactly one --settings" rule passed.
              Now that --settings is read and the take refuses; an argv whose position 1 is not -p or --print, or
              that has no prompt, cannot be read as run_take's and raises CheckRefused.
  J-bound     (b) each journal names its own turn and harness: harness "claude-code", a stream whose basename is
              turn-N.jsonl for its own N, and a claude client (claude, or an absolute path whose basename is claude).
              A journal of another harness, another turn's stream, no stream, or another client refuses.
  J-stream    (c) a turn's journal without its stream refuses: the turn's init cannot be shown (fail closed).
  J-clean     two bound turns with their streams read clean, the absolute client path included.
  J-witness   each clause dropped in memory turns a check red.

Every refusal is [harness-condition-violated] from both functions. Synthetic fixtures only.
"""

from __future__ import annotations

import contextlib
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import check_take as ct  # noqa: E402

DENY = ["RemoteTrigger", "SendMessage", "ListAgents"]
SETTINGS = json.dumps({"availableModels": ["m"], "crossSessionInbound": "refuse",
                       "env": {"CLAUDE_CODE_DISABLE_REFUSAL_FALLBACK": "1", "CLAUDE_CODE_THRIFTY_SONIC": "false",
                               "CLAUDE_CODE_SILENT_TURN_REMINDER": "0"},
                       "fallbackModel": [], "permissions": {"deny": DENY}, "switchModelsOnFlag": False},
                      sort_keys=True, separators=(",", ":"))
OTHER = json.dumps({"crossSessionInbound": "hold", "env": {"CLAUDE_CODE_THRIFTY_SONIC": "true"},
                    "permissions": {"deny": []}}, sort_keys=True, separators=(",", ":"))
INIT = {"type": "system", "subtype": "init", "session_id": "s", "tools": ["Bash", "Read"], "model": "m"}
UNSET = object()


def argv(*, client="claude", head=("-p", "x"), extra=()):
    return [client, *head, "--model", "m", "--disallowedTools", *DENY, "--settings", SETTINGS, *extra,
            "--session-id", "s"]


def journal(n, *, harness="claude-code", stream=UNSET, **kw):
    doc = {"schema": 1, "harness": harness, "container_id": "synthetic", "argv": argv(**kw), "cwd": "/synthetic/run",
           "stream": f"/synthetic/host/take/turn-{n}.jsonl" if stream is UNSET else stream, "started_at": 0.0}
    if stream is None:
        del doc["stream"]
    if harness is None:
        del doc["harness"]
    return doc


def take(tmp: Path, journals: dict, streams) -> Path:
    path = tmp / "transcript.jsonl"
    path.write_text(json.dumps({"type": "user", "message": {"content": "x"}}) + "\n")
    for n in streams:
        (tmp / f"turn-{n}.jsonl").write_text(json.dumps(INIT) + "\n")
    for n, doc in journals.items():
        (tmp / f"turn-{n}.jsonl.launch.json").write_text(json.dumps(doc))
    return path


def both(journals: dict, streams) -> dict:
    with tempfile.TemporaryDirectory() as d:
        path = take(Path(d), journals, streams)
        out = {}
        for fn in ("steer_condition_problems", "denied_tool_problems"):
            try:
                out[fn] = getattr(ct, fn)(path)
            except ct.CheckRefused as e:
                out[fn] = f"CheckRefused: {e}"
        return out


REFUSED = {
    # (a)
    "a stray --print hides a second --settings": ({1: journal(1, extra=("--print", "--settings", OTHER))}, [1]),
    "a stray -p hides a second --settings": ({1: journal(1, extra=("-p", "--settings", OTHER))}, [1]),
    # (b)
    "another harness": ({1: journal(1, harness="gemini")}, [1]),
    "no harness": ({1: journal(1, harness=None)}, [1]),
    "another turn's stream": ({1: journal(1, stream="/synthetic/host/take/turn-2.jsonl")}, [1]),
    "two turns' journals swapped": ({1: journal(2), 2: journal(1)}, [1, 2]),
    "no stream named": ({1: journal(1, stream=None)}, [1]),
    "a stream that is not a string": ({1: journal(1, stream=["turn-1.jsonl"])}, [1]),
    "a stream name with a prefix": ({1: journal(1, stream="/synthetic/host/take/native-turn-1.jsonl")}, [1]),
    "another client": ({1: journal(1, client="bash")}, [1]),
    "a relative claude path": ({1: journal(1, client="bin/claude")}, [1]),
    "an absolute path to another client": ({1: journal(1, client="/usr/local/bin/claude-x")}, [1]),
    # (c)
    "a journal with no stream": ({1: journal(1)}, []),
    "turn 2's journal with no stream": ({1: journal(1), 2: journal(2)}, [1]),
}
UNREADABLE = {
    "the prompt not at position 2": ({1: journal(1, head=())}, [1]),
    "position 1 not -p": ({1: journal(1, head=("--model", "m", "-p", "x"))}, [1]),
    "no prompt after -p": (None, [1]),
}


def refused_problems() -> list:
    out = []
    for name, (journals, streams) in REFUSED.items():
        for fn, got in both(journals, streams).items():
            if isinstance(got, str) or ct.reason_ids(got)[:1] != ["harness-condition-violated"]:
                out.append(f"J {name} ({fn}): {got}")
    return out


def unreadable_problems() -> list:
    out = []
    for name, (journals, streams) in UNREADABLE.items():
        if journals is None:
            j = journal(1)
            j["argv"] = ["claude", "-p"]
            journals = {1: j}
        for fn, got in both(journals, streams).items():
            if not (isinstance(got, str) and got.startswith("CheckRefused")):
                out.append(f"J-print {name} ({fn}): read as {got}")
    return out


def clean_problems() -> list:
    out = []
    for name, journals, streams in (("one turn", {1: journal(1)}, [1]),
                                    ("two turns", {1: journal(1), 2: journal(2)}, [1, 2]),
                                    ("--print and an absolute client", {1: journal(1, client="/usr/local/bin/claude",
                                                                               head=("--print", "x"))}, [1])):
        for fn, got in both(journals, streams).items():
            if got != []:
                out.append(f"J-clean {name} ({fn}): {got}")
    return out


@contextlib.contextmanager
def source_mutant(old: str, new: str):
    """check_take's two condition functions taken from a copy of its source with one anchored edit, patched in."""
    src = Path(ct.__file__).read_text()
    assert src.count(old) == 1, f"anchor occurs {src.count(old)} times: {old!r}"
    m = types.ModuleType("check_take_witness")
    m.__file__ = ct.__file__
    sys.modules[m.__name__] = m
    try:
        exec(compile(src.replace(old, new), ct.__file__, "exec"), m.__dict__)
    finally:
        del sys.modules[m.__name__]
    m.CheckRefused = ct.CheckRefused        # the mutant raises the class the cases catch, so a refusal is not a crash
    with mock.patch.object(ct, "steer_condition_problems", m.steer_condition_problems), \
            mock.patch.object(ct, "denied_tool_problems", m.denied_tool_problems):
        yield


MUTANTS = (
    ("the prompt skipped anywhere", (
        "    tokens = argv[3:]\n",
        "    tokens, i = [], 1\n    while i < len(argv):\n        if argv[i] in _JOURNAL_PRINT_FLAGS:\n"
        "            i += 2\n            continue\n        tokens.append(argv[i])\n        i += 1\n")),
    ("position 1 not required", ("len(argv) < 3 or argv[1] not in _JOURNAL_PRINT_FLAGS", "len(argv) < 3")),
    ("harness not bound", ('doc.get("harness") == CLAUDE_CODE and ', "")),
    ("turn not bound", ('os.path.basename(stream) == f"turn-{n}.jsonl"', "os.path.basename(stream).startswith(\"turn-\")")),
    ("stream not required", ('isinstance(stream, str) and os.path.basename(stream) == f"turn-{n}.jsonl"',
                             '(stream is None or isinstance(stream, str) and os.path.basename(stream) == f"turn-{n}.jsonl")')),
    ("client not bound", ("and _journal_client(argv[0] if isinstance(argv, list) and argv else None)", "")),
    ("journals without streams read", ("    streamless = sorted(set(journals) - streams)\n",
                                       "    streamless = []\n")),
)


class TheJournalBinding(unittest.TestCase):
    def test_refused(self):
        self.assertEqual(refused_problems(), [])

    def test_unreadable(self):
        self.assertEqual(unreadable_problems(), [])

    def test_clean(self):
        self.assertEqual(clean_problems(), [])

    def test_witnesses(self):
        for name, (old, new) in MUTANTS:
            with self.subTest(clause=name):
                with source_mutant(old, new):
                    try:
                        got = refused_problems() + unreadable_problems() + clean_problems()
                    except Exception as e:  # noqa: BLE001 - a mutant that crashes a check is red too
                        got = [f"raised {type(e).__name__}"]
                print(f"\nWITNESS {name}: {'red' if got else 'NOT KILLED'} ({got[:1]})", end=" ", file=sys.stderr)
                self.assertTrue(got, name)


if __name__ == "__main__":
    unittest.main()
