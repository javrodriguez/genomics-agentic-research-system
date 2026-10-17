#!/usr/bin/env python3
"""Lane vendor-admission T4: the vendor check readers' bindings (lane-reports/vendor-T4-PLAN.md v4, ruled READY by
glitch-b5 on Sat 17 Oct 2026, about 12:35 EDT, on Javier's typed word "vendor-t4: yes").

PF, the freeze gate's half in check_take.py (plan section 7; review 36ce125 MINOR 2, folded by ruling 2):

  VP-rows      check_take.VENDOR_PENDING_ROWS holds, per harness, exactly the PENDING keys of the comparability table
               (lane-reports/vendor-T4-TABLE.md, its key list), each with its row's reason id (a reason of routing.json's
               operator_reasons) and the state PENDING on this head; VENDOR_CHECK_SHAPES_SOURCE is "documented".
  VP-helper    vendor_pending(harness, key, reader, ...) returns the row's refusal ("[<reason id>] no vendor reader yet
               (<key>)") while the key is PENDING, raises KeyError for an unknown harness or key, and once a key is
               settled calls the reader the row names and returns its problems; a settled key with no reader, another
               reader, a reader returning no list, or a row off its shape (a SAME with no fixture, a NOT COMPARABLE with
               no ruling) refuses with CheckRefused, so settling a key never silences a refusal no reader covers.
  VP-keys      read from check_take.py's AST: every vendor_pending call names its harness and key as literals and a
               key of the map; a settled key's call site passes, as its reader, the very function its row names; the
               text "no vendor reader yet" occurs only inside vendor_pending's body. The call sites are P2's, so on this
               head the live check asserts the calls are a subset of the map's keys; P2 makes it equality. Three
               mutants on synthetic sources (a refusal written outside the helper, a key dropped from the map, a map key
               with no call site) go red here already.
  VP-fixtures  a SAME row's fixture is a file labelled RECORDED (walk and CLI version) in its folder's README, and
               VENDOR_CHECK_SHAPES_SOURCE reads "recorded" only while every row of that harness is settled.

Fakes and synthetic sources only: no take, model, container or network.
"""

from __future__ import annotations

import ast
import contextlib
import copy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import check_take as ct  # noqa: E402
import routing  # noqa: E402

# The table's key list (lane-reports/vendor-T4-TABLE.md, the header's VENDOR_PENDING_ROWS line), with each row's
# reason id as its PENDING cell names it.
TABLE_KEYS = {
    "codex": {"T-5": "unknown-harness-origin", "T-8:file-change": "transcript-unreadable",
              "T-10": "leak-in-loaded-context", "T-12:offered-context": "inherited-context",
              "T-12:instruction-files": "inherited-context", "T-12:prompt-snapshot": "inherited-context",
              "T-12:memory": "inherited-context", "T-13": "checkout-binding", "T-14": "checkout-binding",
              "T-16": "constant-binding", "T-17:billing-route": "environment-record",
              "T-18": "harness-condition-violated"},
    "gemini": {"T-4": "readers-disagree", "T-10": "leak-in-loaded-context", "T-11": "inherited-context",
               "T-12:offered-context": "inherited-context", "T-12:instruction-files": "inherited-context",
               "T-12:prompt-snapshot": "inherited-context", "T-12:memory": "inherited-context",
               "T-13": "checkout-binding", "T-14": "checkout-binding", "T-17:billing-route": "environment-record",
               "T-18": "harness-condition-violated"},
}
NO_READER = "no vendor reader yet"
SOURCE = Path(ct.__file__).read_text(encoding="utf-8")


def synthetic_reader(*args, **kwargs):
    return [f"[readers-disagree] synthetic reader read {args} {sorted(kwargs)}"]


def another_reader(*args, **kwargs):
    return ["[readers-disagree] another reader"]


def none_reader(*args, **kwargs):
    return None


@contextlib.contextmanager
def settled(harness: str, key: str, state: str = "SAME", **fields):
    """The map with one key settled (TEST DATA, patched in), and synthetic_reader defined in check_take."""
    rows = copy.deepcopy(ct.VENDOR_PENDING_ROWS)
    row = {"reason": rows[harness][key]["reason"], "state": state, "reader": "synthetic_reader"}
    row.update({"SAME": {"fixture": "vendor-check/synthetic.jsonl"}, "NOT COMPARABLE": {"ruling": "R-7"}}
               .get(state, {}))
    row.update(fields)
    rows[harness][key] = {k: v for k, v in row.items() if v is not None}
    with mock.patch.object(ct, "VENDOR_PENDING_ROWS", rows), \
            mock.patch.object(ct, "synthetic_reader", synthetic_reader, create=True), \
            mock.patch.object(ct, "none_reader", none_reader, create=True):
        yield rows


# ---- VP-keys: the call sites read from the AST --------------------------------------------------------------------
def vendor_pending_calls(source: str) -> list:
    """[(harness, key, reader name or None, line)] of every vendor_pending call; a non-literal harness or key, or a
    reader that is neither a name nor None, raises AssertionError."""
    out = []
    for node in ast.walk(ast.parse(source)):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "vendor_pending"):
            continue
        args = node.args[:3]
        if len(args) < 3 or not all(isinstance(a, ast.Constant) and isinstance(a.value, str) for a in args[:2]):
            raise AssertionError(f"line {node.lineno}: vendor_pending is called without literal (harness, key, reader)")
        reader = args[2]
        if isinstance(reader, ast.Constant) and reader.value is None:
            name = None
        elif isinstance(reader, ast.Name):
            name = reader.id
        else:
            raise AssertionError(f"line {node.lineno}: vendor_pending's reader is neither a function name nor None")
        out.append((args[0].value, args[1].value, name, node.lineno))
    return out


def vp_keys_problems(source: str, rows: dict, *, equal: bool = True) -> list:
    """VP-keys on one source and one map: [] or each problem."""
    out = []
    try:
        calls = vendor_pending_calls(source)
    except AssertionError as e:
        return [str(e)]
    keys = {(h, k) for h, block in rows.items() for k in block}
    called = {(h, k) for h, k, _, _ in calls}
    out += [f"vendor_pending is called with {h} {k}, not a key of VENDOR_PENDING_ROWS" for h, k in sorted(called - keys)]
    if equal:
        out += [f"VENDOR_PENDING_ROWS' {h} {k} has no vendor_pending call site" for h, k in sorted(keys - called)]
    for h, k, name, line in calls:
        row = rows.get(h, {}).get(k)
        if row and row.get("state") != ct.PENDING and name != row.get("reader"):
            out.append(f"line {line}: {h} {k} is settled ({row.get('state')}) with reader {row.get('reader')!r}, but "
                       f"its call site passes {name!r}")
    tree = ast.parse(source)
    helper = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "vendor_pending"]
    if len(helper) != 1:
        return out + [f"check_take.py defines vendor_pending {len(helper)} times"]
    lines = source.split("\n")
    inside = "\n".join(lines[helper[0].lineno - 1:helper[0].end_lineno])
    if source.count(NO_READER) != inside.count(NO_READER) or inside.count(NO_READER) != 1:
        out.append(f"the text {NO_READER!r} occurs {source.count(NO_READER)} times in check_take.py, "
                   f"{inside.count(NO_READER)} of them inside vendor_pending")
    return out


class VPRows(unittest.TestCase):
    def test_vp_rows_are_the_tables_keys_with_their_reason_ids(self):
        got = {h: {k: row["reason"] for k, row in block.items()} for h, block in ct.VENDOR_PENDING_ROWS.items()}
        self.assertEqual(got, TABLE_KEYS)

    def test_vp_rows_every_reason_is_of_the_vocabulary_and_pending_here(self):
        vocabulary = routing.load_table()["operator_reasons"]
        for h, block in ct.VENDOR_PENDING_ROWS.items():
            for k, row in block.items():
                with self.subTest(harness=h, key=k):
                    self.assertIn(row["reason"], vocabulary)
                    self.assertEqual(row, {"reason": row["reason"], "state": ct.PENDING})
                    self.assertIsNone(ct.vendor_row_problem(h, k, row) if row["state"] != ct.PENDING else None)
        self.assertEqual(ct.VENDOR_CHECK_SHAPES_SOURCE, {"codex": "documented", "gemini": "documented"})

    def test_vp_rows_no_event_id_is_a_pending_reason(self):
        # plan line 15: a PENDING refusal is never written under an event id (check4 lifts those into events)
        events = {ct.EVENT_STUDY, ct.EVENT_EMAIL, ct.EVENT_OUTSIDE}
        for h, block in ct.VENDOR_PENDING_ROWS.items():
            self.assertEqual({row["reason"] for row in block.values()} & events, set(), h)

    def test_vp_rows_unsettled_names_each_pending_row(self):
        for h in TABLE_KEYS:
            got = ct.vendor_rows_problems(h)
            self.assertEqual(len(got), len(TABLE_KEYS[h]), got)
            for k, reason in TABLE_KEYS[h].items():
                self.assertIn(f"{k} {reason} is PENDING", got)
        with self.assertRaises(KeyError):
            ct.vendor_rows_problems("synthetic-harness")


class VPHelper(unittest.TestCase):
    def test_vp_helper_a_pending_key_refuses_under_its_reason(self):
        for h, block in TABLE_KEYS.items():
            for k, reason in block.items():
                with self.subTest(harness=h, key=k):
                    self.assertEqual(ct.vendor_pending(h, k, None), [f"[{reason}] {NO_READER} ({k})"])
                    # a reader handed in for a PENDING key is never called: the key's refusal stands
                    self.assertEqual(ct.vendor_pending(h, k, another_reader, 1, a=2), [f"[{reason}] {NO_READER} ({k})"])

    def test_vp_helper_an_unknown_key_raises(self):
        for h, k in (("codex", "T-4"), ("gemini", "T-5"), ("synthetic-harness", "T-10"), ("codex", "T-99")):
            with self.subTest(harness=h, key=k), self.assertRaises(KeyError):
                ct.vendor_pending(h, k, None)

    def test_vp_helper_a_settled_key_calls_its_reader(self):
        for state in ("SAME", "NOT COMPARABLE"):
            with self.subTest(state=state), settled("gemini", "T-4", state):
                got = ct.vendor_pending("gemini", "T-4", synthetic_reader, "folder", design="d")
                self.assertEqual(got, synthetic_reader("folder", design="d"))

    def test_vp_helper_a_settled_key_without_its_reader_refuses(self):
        cases = {"no reader": (None, {}), "another reader": (another_reader, {}),
                 "a reader returning no list": (none_reader, {"reader": "none_reader"}),
                 "the row naming no reader": (synthetic_reader, {"reader": None}),
                 "the row's reader not a function of check_take": (another_reader, {"reader": "another_reader"}),
                 "a SAME naming no fixture": (synthetic_reader, {"fixture": None}),
                 "a SAME naming an empty fixture": (synthetic_reader, {"fixture": ""}),
                 "a state off the three": (synthetic_reader, {"state": "DONE"})}
        for name, (reader, fields) in cases.items():
            state = fields.pop("state", "SAME")
            with self.subTest(case=name), settled("codex", "T-5", state, **fields), \
                    self.assertRaises(ct.CheckRefused):
                ct.vendor_pending("codex", "T-5", reader)
        with self.subTest(case="a NOT COMPARABLE naming no ruling"), \
                settled("codex", "T-5", "NOT COMPARABLE", ruling=None), self.assertRaises(ct.CheckRefused):
            ct.vendor_pending("codex", "T-5", synthetic_reader)
        with self.subTest(case="a row carrying an extra key"), \
                settled("codex", "T-5", "SAME", note="x"), self.assertRaises(ct.CheckRefused):
            ct.vendor_pending("codex", "T-5", synthetic_reader)

    def test_vp_helper_settling_a_key_closes_its_row_for_the_freeze(self):
        with settled("gemini", "T-4"):
            got = ct.vendor_rows_problems("gemini")
            self.assertNotIn("T-4 readers-disagree is PENDING", got)
            self.assertEqual(len(got), len(TABLE_KEYS["gemini"]) - 1)
        with settled("gemini", "T-4", fixture=None):
            self.assertTrue(any("T-4" in p for p in ct.vendor_rows_problems("gemini")))


class VPKeys(unittest.TestCase):
    def test_vp_keys_the_live_source(self):
        # P2 writes the call sites; until then the calls are a subset of the map's keys (P2 makes this equality)
        self.assertEqual(vp_keys_problems(SOURCE, ct.VENDOR_PENDING_ROWS, equal=False), [])

    def test_vp_keys_each_mutant_goes_red(self):
        rows = {"codex": {"T-5": {"reason": "unknown-harness-origin", "state": ct.PENDING},
                          "T-13": {"reason": "checkout-binding", "state": ct.PENDING}}}
        helper = ('def vendor_pending(harness, key, reader, *args, **kwargs):\n'
                  '    return [f"[x] no vendor reader yet ({key})"]\n')
        good = helper + ('\ndef f():\n    return vendor_pending("codex", "T-5", None) + '
                         'vendor_pending("codex", "T-13", None)\n')
        self.assertEqual(vp_keys_problems(good, rows), [])
        mutants = {
            "a PENDING refusal raised outside the helper":
                good + '\ndef g():\n    return ["[checkout-binding] no vendor reader yet (T-13)"]\n',
            "a key dropped from the map": good,
            "a map key with no call site": good.replace(' + vendor_pending("codex", "T-13", None)', ""),
            "a non-literal key": good.replace('"T-13", None)', 'KEY, None)'),
            "a settled key passing another reader": good,
        }
        for name, source in mutants.items():
            probe = copy.deepcopy(rows)
            if name == "a key dropped from the map":
                del probe["codex"]["T-13"]
            if name == "a settled key passing another reader":
                probe["codex"]["T-5"] = {"reason": "unknown-harness-origin", "state": "SAME", "fixture": "f",
                                         "reader": "synthetic_reader"}
            with self.subTest(mutant=name):
                self.assertNotEqual(vp_keys_problems(source, probe), [], f"mutant {name} stayed green")


class VPFixtures(unittest.TestCase):
    def test_vp_fixtures_a_same_row_needs_a_recorded_fixture(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "tests" / "fixtures" / "vendor-check"
            folder.mkdir(parents=True)
            (folder / "synthetic.jsonl").write_text("{}\n")
            (folder / "recorded.jsonl").write_text("{}\n")
            (folder / "README.md").write_text(
                "- `synthetic.jsonl`: SYNTHETIC, from the documented shape.\n"
                "- `recorded.jsonl`: RECORDED at walk w-0042, gemini-cli 0.64.0.\n")
            with mock.patch.object(ct, "HERE", Path(tmp)):
                with settled("gemini", "T-4", fixture="vendor-check/recorded.jsonl"):
                    self.assertIsNone(ct.vendor_row_problem("gemini", "T-4", ct.VENDOR_PENDING_ROWS["gemini"]["T-4"]))
                for fixture in ("vendor-check/synthetic.jsonl", "vendor-check/absent.jsonl", "elsewhere/recorded.jsonl",
                                "../vendor-check/recorded.jsonl"):
                    with self.subTest(fixture=fixture), settled("gemini", "T-4", fixture=fixture):
                        self.assertIsNotNone(ct.vendor_row_problem("gemini", "T-4",
                                                                   ct.VENDOR_PENDING_ROWS["gemini"]["T-4"]))
                with self.subTest(case="another CLI's label"), \
                        settled("codex", "T-5", fixture="vendor-check/recorded.jsonl"):
                    self.assertIsNotNone(ct.vendor_row_problem("codex", "T-5", ct.VENDOR_PENDING_ROWS["codex"]["T-5"]))

    def test_vp_fixtures_recorded_shapes_need_every_row_settled(self):
        self.assertEqual(ct.vendor_shapes_problems("codex"), [])          # "documented": nothing to bind yet
        with mock.patch.dict(ct.VENDOR_CHECK_SHAPES_SOURCE, {"codex": "recorded"}):
            got = ct.vendor_shapes_problems("codex")
            self.assertEqual(len(got), len(TABLE_KEYS["codex"]), got)
        with mock.patch.dict(ct.VENDOR_CHECK_SHAPES_SOURCE, {"codex": "observed"}):
            self.assertNotEqual(ct.vendor_shapes_problems("codex"), [])


if __name__ == "__main__":
    unittest.main()
