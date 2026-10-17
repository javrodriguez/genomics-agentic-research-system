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
               no ruling) refuses with CheckRefused, so settling a key never silences a refusal no reader covers. A
               row's reader is a function defined in check_take itself: a class or an imported name refuses (round 8
               ruling 2).
  VP-keys      read from check_take.py's AST: every vendor_pending call names its harness and key as literals and a
               key of the map; a settled key's call site passes, as its reader, the very function its row names; the
               text "no vendor reader yet" occurs only inside vendor_pending's body. The call sites are P2's, so on this
               head the live check asserts the calls are a subset of the map's keys; P2 makes it equality. Three
               mutants on synthetic sources (a refusal written outside the helper, a key dropped from the map, a map key
               with no call site) go red here already.
  sources      tests/check_vendor_sources.py (checks.d's per-piece line, plan NIT 7) refuses a piece naming a
               READER_SOURCES or CODEX_SOURCES file, drive.py excepted for P0 alone.
  VP-fixtures  a SAME row's fixture is a file labelled RECORDED (walk and CLI version) in its folder's README, and
               VENDOR_CHECK_SHAPES_SOURCE reads "recorded" only while every row of that harness is settled.

P1, the vendor view and raw records (plan sections 4 and 9; review 36ce125 MINOR 1, folded by ruling 1), on F1 and F2
(tests/vendor_check_fixtures.py writes them; F3 variants are their parts edited and written to a scratch folder):

  P1-fixtures  the committed F1 and F2 folders are byte for byte what vendor_check_fixtures.py writes.
  P1-view      vendor_take_view reads F1 and F2 through the bound view; a stream whose bytes are not its envelope's,
               or a view holding no event, is transcript-unreadable, never clean; a claude-code take is refused.
  P1-raw       vendor_raw_records reads every tool record of every source: codex exec streams (source 1), the last
               rollout's CommandExecution items (source 2) and its READ response_items (source 3, partitioned exactly
               as codex_native.RESPONSE_ITEMS), gemini streams (source 1) and the last snapshot's toolCalls (source 2).
  P1-reach     F3 cases, each firing its reason on one source only: a codex function_call whose arguments reach
               evals/ only once decoded; an undecodable one and an image_generation_call (transcript-unreadable); a
               rollout CommandExecution naming the checkout while the exec command does not; an exec command reaching
               evals/; a study path only as an object key (MINOR 1, codex and gemini); a gemini list_directory whose
               dir_path the view's mapping drops; a snapshot toolCalls args path; a tool_result naming the checkout;
               a snapshot tool-response turn's functionResponse naming evals/ or the checkout (round 9 ruling 1);
               a refused snapshot, a snapshot the ledger's digest does not bind and an mcp_tool_call
               (transcript-unreadable).
  P1-witness   check_take.py compiled in memory with each P1 mutant (ViewError swallowed, an empty view read as clean,
               the view's args read in place of raw leaves, CommandExecution only, an unreadable tool record skipped,
               the encoded arguments read as the leaf, an undecodable leaf read as text, each source skipped, the
               snapshot's tool-response turns skipped, its ledger digest unchecked, values only, the raw readers'
               refusal swallowed) goes red on the cases above.

Fakes and synthetic sources only: no take, model, container or network.
"""

from __future__ import annotations

import ast
import contextlib
import copy
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import check_take as ct  # noqa: E402
import codex_native  # noqa: E402
import routing  # noqa: E402

sys.path.insert(0, str(HERE / "tests"))
try:
    import vendor_check_fixtures as vcf  # noqa: E402
finally:
    sys.path.remove(str(HERE / "tests"))

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


# TEST DATA: the readers settled() patches into check_take stand for functions defined there (round 8 ruling 2 admits
# only a function whose module is check_take); another_reader is never patched in and stays foreign.
synthetic_reader.__module__ = none_reader.__module__ = ct.__name__


@contextlib.contextmanager
def settled(harness: str, key: str, state: str = "SAME", *, root: Path | None = None, **fields):
    """The map with one key settled (TEST DATA, patched in), synthetic_reader and none_reader defined in check_take,
    and (unless `root` is given) a scratch fixtures folder holding vendor-check/recorded-<harness>.jsonl labelled
    RECORDED at a walk on that harness's CLI."""
    rows = copy.deepcopy(ct.VENDOR_PENDING_ROWS)
    row = {"reason": rows[harness][key]["reason"], "state": state, "reader": "synthetic_reader"}
    row.update({"SAME": {"fixture": f"vendor-check/recorded-{harness}.jsonl"}, "NOT COMPARABLE": {"ruling": "R-7"}}
               .get(state, {}))
    row.update(fields)
    rows[harness][key] = {k: v for k, v in row.items() if v is not None}
    with contextlib.ExitStack() as stack:
        if root is None:
            root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
            folder = root / "tests" / "fixtures" / "vendor-check"
            folder.mkdir(parents=True)
            for h, cli in (("codex", "codex-cli"), ("gemini", "gemini-cli")):
                (folder / f"recorded-{h}.jsonl").write_text("{}\n")
            (folder / "README.md").write_text("- `recorded-codex.jsonl`: RECORDED at walk w-0001, codex-cli 0.0.1.\n"
                                              "- `recorded-gemini.jsonl`: RECORDED at walk w-0002, gemini-cli 0.0.1.\n")
        stack.enter_context(mock.patch.object(ct, "HERE", root))
        stack.enter_context(mock.patch.object(ct, "VENDOR_PENDING_ROWS", rows))
        stack.enter_context(mock.patch.object(ct, "synthetic_reader", synthetic_reader, create=True))
        stack.enter_context(mock.patch.object(ct, "none_reader", none_reader, create=True))
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

    def test_vp_helper_a_reader_is_a_function_defined_in_check_take(self):
        # round 8 ruling 2 (review e7496cf NIT 2): a class of the module, an imported class and an imported function
        # are callable globals of check_take, never its readers
        foreign = {"a class of check_take (CheckRefused)": "CheckRefused", "an imported class (Path)": "Path",
                   "an imported function": "imported_reader", "a module": "json"}
        for name, reader in foreign.items():
            with self.subTest(case=name), settled("codex", "T-5", reader=reader), \
                    mock.patch.object(ct, "imported_reader", contextlib.contextmanager, create=True):
                row = ct.VENDOR_PENDING_ROWS["codex"]["T-5"]
                self.assertIn("no function of check_take.py", ct.vendor_row_problem("codex", "T-5", row) or "")
                self.assertTrue(any(p.startswith("T-5 ") for p in ct.vendor_rows_problems("codex")))
                with self.assertRaises(ct.CheckRefused):
                    ct.vendor_pending("codex", "T-5", getattr(ct, reader))
        with settled("codex", "T-5"):
            self.assertIsNone(ct.vendor_row_problem("codex", "T-5", ct.VENDOR_PENDING_ROWS["codex"]["T-5"]))

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


class SourceLists(unittest.TestCase):
    def test_check_vendor_sources_refuses_a_listed_file_outside_p0(self):
        sys.path.insert(0, str(HERE / "tests"))
        try:
            import check_vendor_sources as cvs
        finally:
            sys.path.remove(str(HERE / "tests"))
        self.assertEqual(cvs.problems("PF", ["freeze.py", "check_take.py"]), [])
        self.assertEqual(cvs.problems("P0", ["drive.py", "check_take.py"]), [])
        for piece, files in (("PF", ["drive.py"]), ("P1", ["transcript_view.py"]), ("P2", ["codex_native.py"]),
                             ("P5", ["native_snapshot.py"]), ("PX", ["check_take.py"]), ("P1", []),
                             ("P1", ["no-such-file.py"])):
            with self.subTest(piece=piece, files=files):
                self.assertNotEqual(cvs.problems(piece, files), [])


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
                with settled("gemini", "T-4", root=Path(tmp), fixture="vendor-check/recorded.jsonl"):
                    self.assertIsNone(ct.vendor_row_problem("gemini", "T-4", ct.VENDOR_PENDING_ROWS["gemini"]["T-4"]))
                for fixture in ("vendor-check/synthetic.jsonl", "vendor-check/absent.jsonl", "elsewhere/recorded.jsonl",
                                "../vendor-check/recorded.jsonl"):
                    with self.subTest(fixture=fixture), settled("gemini", "T-4", root=Path(tmp), fixture=fixture):
                        self.assertIsNotNone(ct.vendor_row_problem("gemini", "T-4",
                                                                   ct.VENDOR_PENDING_ROWS["gemini"]["T-4"]))
                with self.subTest(case="another CLI's label"), \
                        settled("codex", "T-5", root=Path(tmp), fixture="vendor-check/recorded.jsonl"):
                    self.assertIsNotNone(ct.vendor_row_problem("codex", "T-5", ct.VENDOR_PENDING_ROWS["codex"]["T-5"]))

    def test_vp_fixtures_recorded_shapes_need_every_row_settled(self):
        self.assertEqual(ct.vendor_shapes_problems("codex"), [])          # "documented": nothing to bind yet
        with mock.patch.dict(ct.VENDOR_CHECK_SHAPES_SOURCE, {"codex": "recorded"}):
            got = ct.vendor_shapes_problems("codex")
            self.assertEqual(len(got), len(TABLE_KEYS["codex"]), got)
        with mock.patch.dict(ct.VENDOR_CHECK_SHAPES_SOURCE, {"codex": "observed"}):
            self.assertNotEqual(ct.vendor_shapes_problems("codex"), [])


# ---- P1: the vendor view and raw records ----------------------------------------------------------------------------
STUDY = "[study-materials-reached]"
OUTSIDE = "[read-outside-the-checkout]"
UNREADABLE = "[transcript-unreadable]"


def codex_done(parts, k, kind):
    """The (line type, payload) of turn k's rollout record whose item or payload type is `kind`."""
    for t, pay in parts["rollout"][k]:
        if pay.get("type") == kind or (pay.get("item") or {}).get("type") == kind:
            return pay
    raise AssertionError(f"turn {k} holds no {kind}")


def f3_codex_escaped(parts):
    # source 3 only, reachable only after decoding: `\/` for each solidus and `\u0065` for one letter (round 9
    # ruling 2, review 89ee5a8 NIT 1: the escaped letter is the plan's leg)
    codex_done(parts, 2, "function_call")["arguments"] = r'{"cmd": "cat \u0065vals\/gap-study-4\/prereg-draft.json"}'


def f3_codex_undecodable(parts):
    codex_done(parts, 2, "function_call")["arguments"] = '{"cmd": "cat'


def f3_codex_image(parts):
    parts["rollout"][2].insert(2, ("response_item", {"type": "image_generation_call", "id": "ig_1",
                                                     "status": "completed", "result": "aGk="}))


def f3_codex_rollout_argv(parts):
    codex_done(parts, 2, "CommandExecution")["item"]["command"] = ["cat", f"{ct.CHECKOUT_REPO}/README.md"]


def f3_codex_exec_command(parts):
    for rec in parts["streams"][2]:
        if (rec.get("item") or {}).get("type") == "command_execution":
            rec["item"]["command"] = "cat evals/gap-study-4/prereg-draft.json"


def f3_codex_object_key(parts):
    codex_done(parts, 2, "function_call")["arguments"] = json.dumps(
        {"cmd": "ls", "env": {"evals/gap-study-4/prereg-draft.json": "1"}})


def f3_codex_mcp(parts):
    parts["streams"][2][2:4] = [{"type": "item.started", "item": {"id": "item_0", "type": "mcp_tool_call",
                                                                  "server": "s", "tool": "t", "status": "in_progress"}},
                                {"type": "item.completed", "item": {"id": "item_0", "type": "mcp_tool_call",
                                                                    "server": "s", "tool": "t", "status": "completed",
                                                                    "result": {"content": []}}}]


def f3_gemini_list_directory(parts):
    for rec in parts["streams"][2]:
        if rec["type"] == "tool_use":
            rec.update(tool_name="list_directory", parameters={"dir_path": "evals/gap-study-4"})


def f3_gemini_snapshot_args(parts):
    parts["native"][2][1]["toolCalls"][0]["args"] = {"file_path": "evals/gap-study-4/notes.txt"}


def f3_gemini_object_key(parts):
    response = parts["native"][2][1]["toolCalls"][0]["result"][0]["functionResponse"]
    response["response"] = {"evals/gap-study-4/notes.txt": "x"}


def f3_gemini_tool_response(parts):
    # round 9 ruling 1 (review 89ee5a8 MINOR 1): the snapshot's tool-response user turn alone names the study; its
    # toolCalls result and every stream record stay clean
    parts["native"][2][2]["content"][0]["functionResponse"]["response"] = {
        "output": "evals/gap-study-4/prereg-draft.json says ..."}


def f3_gemini_tool_response_checkout(parts):
    parts["native"][2][2]["content"][0]["functionResponse"]["response"] = {"output": f"{ct.CHECKOUT_REPO}/README.md"}


def f3_gemini_tool_result(parts):
    for rec in parts["streams"][2]:
        if rec["type"] == "tool_result":
            rec["output"] = f"{ct.CHECKOUT_REPO}/README.md"


def f3_gemini_snapshot_refused(parts):
    parts["native"][2].pop()          # the interaction now ends on its tool calls: the projection refuses it


# (case, harness, edit, the reason the reach must carry, or None for clean)
REACH_CASES = (
    ("F1 as written", "codex", None, None),
    ("F2 as written", "gemini", None, None),
    ("codex function_call reaching evals/ only once decoded", "codex", f3_codex_escaped, STUDY),
    ("codex function_call arguments that do not decode", "codex", f3_codex_undecodable, UNREADABLE),
    ("codex image_generation_call", "codex", f3_codex_image, UNREADABLE),
    ("codex rollout argv naming the checkout, exec command not", "codex", f3_codex_rollout_argv, OUTSIDE),
    ("codex exec command reaching evals/", "codex", f3_codex_exec_command, STUDY),
    ("codex study path only as an object key", "codex", f3_codex_object_key, STUDY),
    ("codex mcp_tool_call", "codex", f3_codex_mcp, UNREADABLE),
    ("gemini list_directory dir_path the view drops", "gemini", f3_gemini_list_directory, STUDY),
    ("gemini snapshot toolCalls args", "gemini", f3_gemini_snapshot_args, STUDY),
    ("gemini study path only as an object key", "gemini", f3_gemini_object_key, STUDY),
    ("gemini tool_result naming the checkout", "gemini", f3_gemini_tool_result, OUTSIDE),
    ("gemini snapshot tool-response turn reaching evals/", "gemini", f3_gemini_tool_response, STUDY),
    ("gemini snapshot tool-response turn naming the checkout", "gemini", f3_gemini_tool_response_checkout, OUTSIDE),
    ("gemini snapshot the projection refuses", "gemini", f3_gemini_snapshot_refused, UNREADABLE),
)


@contextlib.contextmanager
def take(harness, edit=None):
    """A scratch take folder of `harness`: F1 or F2's parts, edited by `edit`; yields its transcript.jsonl."""
    parts = vcf.codex_parts() if harness == "codex" else vcf.gemini_parts()
    if edit is not None:
        edit(parts)
    with tempfile.TemporaryDirectory() as tmp:
        yield vcf.write(Path(tmp), harness, parts)


def p1_problems(mod) -> list:
    """P1's cases on one check_take module (the real one or a mutant): [] or each failure."""
    out = []
    for name, harness, edit, reason in REACH_CASES:
        with take(harness, edit) as path:
            try:
                got = mod.vendor_reach(path, harness)
            except Exception as e:  # noqa: BLE001 - a traceback is itself a failure here
                out.append(f"{name}: vendor_reach raised {type(e).__name__}: {e}")
                continue
            tags = {p.split("] ")[0] + "]" for p in got["problems"]}
            if tags != ({reason} if reason else set()):
                out.append(f"{name}: reach problems {sorted(tags)}, not {[reason] if reason else []}: "
                           f"{got['problems']}")
            view = mod.vendor_take_view(path, harness)
            if view["problems"] or not view["events"]:
                out.append(f"{name}: the view refuses a bound take: {view['problems']}")
    for harness in ("codex", "gemini"):
        with take(harness) as path:
            records = mod.vendor_raw_records(path, harness)
            rollout = codex_native._json_lines((path.parent / "session" / "native-turn-2.jsonl").read_bytes(),
                                               ValueError) if harness == "codex" else []
            want = {"codex": 4 + 2 + sum(r["type"] == "response_item" and r["payload"]["type"] in
                                         mod.CODEX_RESPONSE_READ for r in rollout),
                    "gemini": 4 + 2 + 2}[harness]       # + each tool-response turn's part (round 9 ruling 1)
            if len(records) != want:
                out.append(f"{harness}: {len(records)} raw tool records read, not {want}")
            # a stream whose bytes are not its envelope's: refused on both roads, never clean
            (path.parent / "turn-2.jsonl").write_bytes((path.parent / "turn-2.jsonl").read_bytes() + b"\n")
            view, reach = mod.vendor_take_view(path, harness), mod.vendor_reach(path, harness)
            for road, got in (("view", view), ("reach", reach)):
                if [p.split("] ")[0] + "]" for p in got["problems"]] != [UNREADABLE]:
                    out.append(f"{harness} digest broken: the {road} is not transcript-unreadable: {got['problems']}")
        # the last snapshot's bytes are not the ones the ledger binds (round 9 ruling 2, review 89ee5a8 NIT 2)
        with take(harness) as path:
            ledger = json.loads((path.parent / "driver-ledger.json").read_text(encoding="utf-8"))
            ledger["native_snapshots"][-1]["sha256"] = "0" * 64
            (path.parent / "driver-ledger.json").write_text(json.dumps(ledger), encoding="utf-8")
            got = mod.vendor_reach(path, harness)
            if [p.split("] ")[0] + "]" for p in got["problems"]] != [UNREADABLE]:
                out.append(f"{harness} snapshot digest broken: the reach is not transcript-unreadable: "
                           f"{got['problems']}")
        with take(harness) as path, mock.patch.object(mod.transcript_view, "events", lambda *a, **k: []):
            if [p.split("] ")[0] + "]" for p in mod.vendor_take_view(path, harness)["problems"]] != [UNREADABLE]:
                out.append(f"{harness}: an empty view is read as clean")
    return out


class P1Fixtures(unittest.TestCase):
    def test_p1_fixtures_are_what_the_builder_writes(self):
        self.assertEqual(vcf.problems(), [])
        for folder in (vcf.F1, vcf.F2):
            readme = (folder / "README.md").read_text(encoding="utf-8")
            for p in sorted(x.relative_to(folder).as_posix() for x in folder.rglob("*")
                            if x.is_file() and x.name != "README.md"):
                with self.subTest(file=f"{folder.name}/{p}"):
                    self.assertIn(f"- `{p}`: SYNTHETIC, ", readme)


class P1Readers(unittest.TestCase):
    def test_p1_view_and_reach_on_every_case(self):
        self.assertEqual(p1_problems(ct), [])

    def test_p1_raw_the_partition_is_response_items_exactly(self):
        parts = (ct.CODEX_RESPONSE_READ, ct.CODEX_RESPONSE_NOT_TOOL, ct.CODEX_RESPONSE_REFUSED)
        self.assertEqual(sorted(x for part in parts for x in part), sorted(codex_native.RESPONSE_ITEMS))
        self.assertTrue(set(ct.CODEX_RESPONSE_RETURNED) <= set(ct.CODEX_RESPONSE_READ))
        self.assertEqual(ct.VENDOR_JSON_DOCUMENTS, {"codex": {"function_call": ("arguments",)}, "gemini": {}})

    def test_p1_raw_reads_cli_bytes_not_the_view(self):
        with take("gemini", f3_gemini_list_directory) as path:
            view = ct.vendor_take_view(path, "gemini")["events"]
            self.assertIn({}, [e.args for e in view if e.kind == "tool-call"])     # the mapping drops dir_path
            asked = [a for _, a, _ in ct.vendor_raw_records(path, "gemini") if a.get("tool_name") == "list_directory"]
            self.assertEqual([a["parameters"] for a in asked], [{"dir_path": "evals/gap-study-4"}])
        with take("codex", f3_codex_escaped) as path:
            got = [a for w, a, _ in ct.vendor_raw_records(path, "codex") if a.get("type") == "function_call"]
            self.assertEqual(got[-1]["arguments"], {"cmd": "cat evals/gap-study-4/prereg-draft.json"})

    def test_p1_a_claude_code_take_is_refused(self):
        with take("codex") as path:
            for fn in (ct.vendor_take_view, ct.vendor_raw_records, ct.vendor_reach):
                with self.subTest(reader=fn.__name__), self.assertRaises(ct.CheckRefused):
                    fn(path, "claude-code")


def ct_mutant(*edits):
    """check_take.py compiled in memory with each (old, new) replaced; each old must occur exactly once."""
    src = SOURCE
    for old, new in edits:
        if src.count(old) != 1:
            raise AssertionError(f"mutation site occurs {src.count(old)} times in check_take.py: {old!r}")
        src = src.replace(old, new)
    name = "check_take_p1_mutant"
    m = types.ModuleType(name)
    m.__file__ = ct.__file__
    sys.modules[name] = m
    try:
        exec(compile(src, ct.__file__ + " (witness)", "exec"), m.__dict__)  # noqa: S102
    finally:
        sys.modules.pop(name, None)
    return m


P1_WITNESSES = {
    "ViewError swallowed": ((
        '        return {"events": None, "problems": [f"[{TRANSCRIPT_UNREADABLE}] the {harness} view refuses the '
        'take: {e}"]}\n', '        return {"events": [], "problems": []}\n'),),
    "an empty view read as clean": (("    if not evs:\n", "    if False:\n"),),
    "the view's args read in place of raw leaves": ((
        '            out.append((f"{where} line {n}", rec, {}))\n',
        '            out.append((f"{where} line {n}", {"args": _tx_gemini.tool_kind(rec)[1]}, {}))\n'),),
    "CommandExecution only": (('        if rec["type"] != "response_item":\n            continue\n',
                               '        if True:\n            continue\n'),),
    "an unreadable tool record skipped": ((
        '            raise VendorUnreadable(f"{at}: a response_item {kind}, which the vendor readers refuse")\n',
        '            continue\n'),),
    "the encoded arguments read as the leaf": (("    for field in documents:\n", "    for field in ():\n"),),
    "an undecodable leaf read as text": ((
        '        raise VendorUnreadable(f"{where}: {field} does not decode as the JSON document its record type '
        'defines") from None\n', '        return value\n'),),
    "the exec streams skipped": (('            out += read(raw.decode("utf-8"), env["stream"])\n',
                                  '            pass\n'),),
    "the rollout's CommandExecution items skipped": ((
        '            out.append(_vendor_split(item, "CommandExecution", at))\n', '            pass\n'),),
    "the native snapshot skipped": (('        out += read(raw, f"session/{name}")\n', '        pass\n'),),
    "values only (MINOR 1)": (('"input": asked}', '"input": transcript_view._strings(asked)}'),
                              ('"content": returned}', '"content": transcript_view._strings(returned)}')),
    "the snapshot's tool-response turns skipped (round 9 ruling 1)": ((
        '                out.append((f"{where} message {message.get(\'id\')!r} response {i + 1}", {}, part))\n',
        '                pass\n'),),
    "the snapshot's ledger digest unchecked (round 9 ruling 2)": ((
        '        if hashlib.sha256(raw).hexdigest() != snaps[-1].get("sha256"):\n', '        if False:\n'),),
    "the raw readers' refusal swallowed": ((
        '        return {"problems": [f"[{TRANSCRIPT_UNREADABLE}] the {harness} raw records refuse the take: {e}"],\n',
        '        return {"problems": [],\n'),),
}


class P1Witnesses(unittest.TestCase):
    def test_p1_witness_each_mutant_goes_red(self):
        for name, edits in P1_WITNESSES.items():
            with self.subTest(witness=name):
                self.assertNotEqual(p1_problems(ct_mutant(*edits)), [], f"witness {name} stayed green")


if __name__ == "__main__":
    unittest.main()
