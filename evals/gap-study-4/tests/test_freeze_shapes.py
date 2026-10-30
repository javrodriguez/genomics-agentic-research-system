#!/usr/bin/env python3
"""Lane vendor-admission T3: the freeze refuses an arm whose adapter reads documented shapes only.

Ruling Q-3 (glitch-2f, 12 Oct 2026; codex_adapter.py:9-14, gemini_adapter.py:9-14): build arms O and G on the
documented stream shapes now, and the freeze refuses any arm whose adapter has not been re-tested on a stream recorded
at its first real walk. glitch-b5's lane vendor-admission (16 Oct 2026), task T3, builds that refusal: freeze.main
refuses while a design row's harness is codex or gemini and that adapter's SHAPES_SOURCE is not "recorded", naming the
arm; nothing is written.

  FS-draft     on the committed draft (arms O and G, both adapters "documented") the check names both arms.
  FS-main      freeze.main on a fixture draft with an O row, a G row, or both refuses at "documented" naming each arm,
               and passes once that adapter's SHAPES_SOURCE is patched to "recorded"; a claude-code-only draft passes.
  FS-docs      each adapter's SHAPES_SOURCE paragraph says freeze.py now refuses its arm, never that the refusal is
               owed to a later slice (round-2 ruling 2).
  FS-witness   freeze.py compiled in memory without the check's call, or with its comparison disabled, goes red.
  FS-check     T4 PF (lane-reports/vendor-T4-PLAN.md v4 section 7, ruled READY by glitch-b5, Sat 17 Oct 2026): the gate
               has three legs per vendor harness, (i) the adapter's SHAPES_SOURCE is "recorded", (ii) check_take's
               VENDOR_CHECK_SHAPES_SOURCE is "recorded" and every VENDOR_PENDING_ROWS row of that harness is settled,
               (iii) native_reader_registration.production_readers() holds the harness. With both adapters recorded,
               main refuses while (ii) is absent or "documented", while any row is unsettled (naming it) and while
               (iii) is empty or raises (by name, never a traceback; a missing git binary or any other OSError from
               production_readers included, round 8 ruling 1); it passes only with all three, and a claude-code-
               only draft passes unchanged. Witnesses deleting leg (ii)'s comparison, its settled condition, leg
               (iii) and leg (iii)'s OSError refusal each go red. FS-main's passing cases now settle all three legs (the PF ruling, named in the commit).

freeze.main runs against a temporary folder: git, the review, the pins, prepare and the writer are fakes (the shape of
test_holdout_digests' FreezeHarness). No take, model, container or network; no freeze output is written.
"""

from __future__ import annotations

import contextlib
import copy
import hashlib
import io
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

import check_take  # noqa: E402
import codex_adapter  # noqa: E402
import freeze  # noqa: E402
import gemini_adapter  # noqa: E402
import native_reader_registration  # noqa: E402

ADAPTERS = {"O": codex_adapter, "G": gemini_adapter}
HARNESS = {"O": "codex", "G": "gemini"}
CLI = {"codex": "codex-cli 0.0.1", "gemini": "gemini-cli 0.0.1"}


def row(arm: str) -> dict:
    harness = {"A": "claude-code", "O": "codex", "G": "gemini"}[arm]
    return {"arm": arm, "task": "synthetic-task", "half": "trap", "wording": "w1", "repeat": 1, "pressure": None,
            "model": f"synthetic-{arm}-model", "agent": {"harness": harness, "version": "0.0.1"},
            "half_cell": f"c-{arm}", "slot": f"s-{arm}"}


def draft(arms) -> dict:
    # pre-freeze review 2, m3 (lane fold2/lb's leg; this rig's draft by lane fold2/lc): a draft carries the order
    # function's hash, so freeze.main's take-order-function leg reads the draft this tree builds and the shape legs
    # stay what these tests read
    import freeze
    return {"status": "DRAFT", "tasks": [], "rows": [row(a) for a in arms],
            freeze.ORDER_FUNCTION_HASH_KEY: freeze.take_order_function_sha256()}


def fake_git(*args):
    return {("remote",): (0, ""), ("status", "--porcelain"): (0, ""),
            ("rev-parse", "HEAD"): (0, "b" * 40)}.get(args, (1, "no such fake git call"))


def fake_prepare(d, *, review, parent, pins, frozen_at, beacon=None):
    return dict(copy.deepcopy(d), status="FROZEN", frozen_at=frozen_at, frozen_at_commit_parent=parent,
                pre_freeze_review_commit=review, take_order_seed=review, take_order=[], pinned_files=pins)


def run_main(mod, d: dict) -> tuple[int, str, list]:
    """(exit code, stdout, frozen files written) of mod.main, previewing and then writing a rehearsal freeze."""
    written, outs, codes = [], [], []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "prereg-draft.json").write_text(json.dumps(d))
        patches = ((mod, "HERE", tmp), (mod, "REPO", tmp), (mod, "DRAFT", tmp / "prereg-draft.json"),
                   (mod, "PINNED", []), (mod, "git", fake_git), (mod, "prepare", fake_prepare),
                   (mod, "review_file_problems", lambda commit: ([], "review/prefreeze-1.md")),
                   (mod, "study_tree_sha", lambda *a, **k: "c" * 64),
                   (mod, "write_outputs", lambda frozen: written.append(frozen) or ()),
                   (mod, "owned_paths", lambda *a, **k: []),
                   # lane pf1-l1-freeze-gates (pre-freeze review 1, MAJORs 4 and 9): the coverage gate and the
                   # beacon read stood in for, as the other gates here are; tests/test_pf1_freeze_gates.py binds both
                   (mod, "coverage_problem", lambda *a, **k: None),
                   (mod, "take_order_beacon_reading", lambda *a, **k: {"synthetic": "beacon reading"}),
                   (mod.copy_manifest, "problems", lambda *a, **k: []))
        (tmp / "review").mkdir()
        (tmp / "review" / "prefreeze-1.md").write_text("synthetic review\n")
        for argv in (["--review-commit", "a" * 40, "--rehearsal"], ["--review-commit", "a" * 40, "--rehearsal",
                                                                   "--write"]):
            out = io.StringIO()
            with contextlib.ExitStack() as stack:
                for module, name, value in patches:
                    stack.enter_context(mock.patch.object(module, name, value))
                stack.enter_context(contextlib.redirect_stdout(out))
                codes.append(mod.main(argv))
            outs.append(out.getvalue())
    return max(codes), "".join(outs), written


def shapes(**recorded):
    """Patch each named arm's adapter (O, G) to SHAPES_SOURCE "recorded"."""
    stack = contextlib.ExitStack()
    for arm in recorded:
        stack.enter_context(mock.patch.object(ADAPTERS[arm], "SHAPES_SOURCE", "recorded"))
    return stack


def synthetic_reader(*args, **kwargs):
    return []


synthetic_reader.__module__ = check_take.__name__  # TEST DATA: stands for a reader defined in check_take (round 8 ruling 2)


@contextlib.contextmanager
def settled(*, legs=("i", "ii", "rows", "items", "iii"), registry=None, cli=None, **arms):
    """TEST DATA: each named arm (O, G) with the named legs of the freeze gate settled: "i" its adapter recorded, "ii"
    check_take's VENDOR_CHECK_SHAPES_SOURCE recorded, "rows" every VENDOR_PENDING_ROWS row of its harness SAME with a
    RECORDED fixture in a scratch fixtures folder and a reader defined in check_take, "items" every
    VENDOR_READER_ITEMS item of its harness on that fixture (round 8 ruling 3, P2), "iii" a registry holding it
    (or `registry`, a callable standing in for production_readers). `cli` ({harness: "<cli> <version>"}, default CLI)
    is what the synthetic fixtures' provenance and labels name: the version the draft under test pins."""
    harnesses = [HARNESS[a] for a in arms]
    with contextlib.ExitStack() as stack:
        tmp = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        # lane pf1-l1-freeze-gates (pre-freeze review 1, m3): leg ii holds each RECORDED fixture to the committed walk
        # record it copies (PROVENANCE.json, the source's bytes, the pinned CLI), so each harness's synthetic fixture
        # has its own folder with a provenance record and a stand-in walk record of the same bytes
        for h in harnesses:
            folder = tmp / "tests" / "fixtures" / f"synthetic-{h}"
            folder.mkdir(parents=True)
            data = b"{}\n"
            (folder / "recorded.jsonl").write_bytes(data)
            named = (cli or CLI)[h]
            (folder / "README.md").write_text(f"- `recorded.jsonl`: RECORDED at walk w-{h}, {named}.\n")
            (folder / "PROVENANCE.json").write_text(json.dumps({"walk": f"w-{h}", "harness": h, "cli": named,
                "files": {"recorded.jsonl": {"source": f"rehearsals/w-{h}/recorded.jsonl",
                                             "sha256": hashlib.sha256(data).hexdigest()}}}))
            (tmp / "rehearsals" / f"w-{h}").mkdir(parents=True)
            (tmp / "rehearsals" / f"w-{h}" / "recorded.jsonl").write_bytes(data)
        stack.enter_context(mock.patch.object(check_take, "HERE", tmp))
        stack.enter_context(mock.patch.object(check_take, "synthetic_reader", synthetic_reader, create=True))
        # the adapters' bound fixture is the synthetic one whether or not leg i is settled, so leg i's refusal at
        # "documented" stays its SHAPES_SOURCE alone (the T3 witnesses keep their meaning)
        for a in arms:
            stack.enter_context(mock.patch.object(ADAPTERS[a], "SHAPES_RECORDED_ON",
                                                  f"synthetic-{HARNESS[a]}/recorded.jsonl"))
        if "i" in legs:
            stack.enter_context(shapes(**arms))
        if "ii" in legs:
            stack.enter_context(mock.patch.dict(check_take.VENDOR_CHECK_SHAPES_SOURCE,
                                                {h: "recorded" for h in harnesses}))
        # lane vendor-settle stage V (S6): the live map is settled, so a leg left out is put in its unsettled state
        # here (rows PENDING, items unrecorded), and the map is always a patched copy: a case's edit never writes the
        # live one (the "a row unsettled" edit used to)
        rows = copy.deepcopy(check_take.VENDOR_PENDING_ROWS)
        for h in harnesses:
            if "rows" in legs:
                rows[h] = {k: {"reason": r["reason"], "state": "SAME", "fixture": f"synthetic-{h}/recorded.jsonl",
                               "reader": "synthetic_reader"} for k, r in rows[h].items()}
            else:
                rows[h] = {k: {"reason": r["reason"], "state": "PENDING"} for k, r in rows[h].items()}
        stack.enter_context(mock.patch.object(check_take, "VENDOR_PENDING_ROWS", rows))
        items = copy.deepcopy(getattr(check_take, "VENDOR_READER_ITEMS", {}))
        for h in harnesses:
            items[h] = dict.fromkeys(items.get(h, {}), f"synthetic-{h}/recorded.jsonl" if "items" in legs else None)
        stack.enter_context(mock.patch.object(check_take, "VENDOR_READER_ITEMS", items, create=True))
        if registry is not None:
            stack.enter_context(mock.patch.object(native_reader_registration, "production_readers", registry))
        elif "iii" in legs:
            held = {h: object() for h in harnesses}
            stack.enter_context(mock.patch.object(native_reader_registration, "production_readers",
                                                  lambda *a, **k: dict(held)))
        yield


@contextlib.contextmanager
def at_documented():
    """TEST DATA: the T4 head's state for both vendor harnesses, which FS-main and FS-check start from (lane
    vendor-settle stage V flipped the live tree to "recorded"): both adapters' SHAPES_SOURCE and check_take's
    VENDOR_CHECK_SHAPES_SOURCE "documented", every VENDOR_PENDING_ROWS row PENDING, every READER item unrecorded."""
    rows = {h: {k: {"reason": r["reason"], "state": "PENDING"} for k, r in block.items()}
            for h, block in check_take.VENDOR_PENDING_ROWS.items()}
    items = {h: dict.fromkeys(block) for h, block in check_take.VENDOR_READER_ITEMS.items()}
    with contextlib.ExitStack() as stack:
        for module in ADAPTERS.values():
            stack.enter_context(mock.patch.object(module, "SHAPES_SOURCE", "documented"))
        stack.enter_context(mock.patch.dict(check_take.VENDOR_CHECK_SHAPES_SOURCE,
                                            {h: "documented" for h in HARNESS.values()}))
        stack.enter_context(mock.patch.object(check_take, "VENDOR_PENDING_ROWS", rows))
        stack.enter_context(mock.patch.object(check_take, "VENDOR_READER_ITEMS", items))
        yield


def main_problems(mod) -> list:
    with at_documented():
        return _main_problems(mod)


def _main_problems(mod) -> list:
    out = []
    for arms in (("A", "O"), ("A", "G"), ("A", "O", "G"), ("O",), ("G",)):
        vendors = [a for a in arms if a in ADAPTERS]
        code, text, written = run_main(mod, draft(arms))
        if code != 1 or written or "REFUSE" not in text:
            out.append(f"{arms} at documented: not refused (exit {code}, {len(written)} written)")
        for a in vendors:
            if f"arm {a} " not in text:
                out.append(f"{arms} at documented: the refusal does not name arm {a}: {text[:200]!r}")
        # T4 PF: leg i alone, with legs ii and iii settled, still refuses (so T3's witnesses keep their meaning)
        with settled(legs=("ii", "rows", "items", "iii"), **{a: True for a in vendors}):
            code, text, written = run_main(mod, draft(arms))
        if code != 1 or written or "REFUSE" not in text:
            out.append(f"{arms} at documented, legs ii and iii settled: not refused (exit {code})")
        for a in vendors:
            if f"arm {a} ({HARNESS[a]}): leg i: " not in text or f"arm {a} ({HARNESS[a]}): leg ii" in text:
                out.append(f"{arms} at documented, legs ii and iii settled: not leg i alone for arm {a}: "
                           f"{text[:300]!r}")
        with settled(**{a: True for a in vendors}):
            code, text, written = run_main(mod, draft(arms))
        if code != 0 or len(written) != 1:
            out.append(f"{arms} at recorded: refused (exit {code}): {text[:200]!r}")
        if len(vendors) == 2:
            with settled(O=True):
                code, text, written = run_main(mod, draft(arms))
            if code != 1 or written or "arm G " not in text or "arm O " in text:
                out.append(f"{arms} with O recorded: G not refused alone: {text[:200]!r}")
    code, text, written = run_main(mod, draft(("A",)))
    if code != 0 or len(written) != 1:
        out.append(f"a claude-code-only draft is refused: {text[:200]!r}")
    return out


class TheFreezeRefusesDocumentedShapes(unittest.TestCase):
    def test_fs_the_adapters_are_recorded_on_this_head(self):
        # lane vendor-settle stage V flipped both (glitch-f1's settle rulings, Thu 22 Oct 2026)
        self.assertEqual((codex_adapter.SHAPES_SOURCE, gemini_adapter.SHAPES_SOURCE), ("recorded", "recorded"))
        self.assertEqual(check_take.VENDOR_CHECK_SHAPES_SOURCE, {"codex": "recorded", "gemini": "recorded"})

    def test_fs_draft_the_committed_draft_names_both_arms(self):
        committed = json.loads((HERE / "prereg-draft.json").read_text())
        self.assertIsNone(freeze.unrecorded_shapes_problem(committed))      # stage V: the live tree passes all legs
        with at_documented():
            got = freeze.unrecorded_shapes_problem(committed)
        self.assertIsNotNone(got)
        for words in ("arm O (codex)", "arm G (gemini)", "'documented'", "recorded"):
            self.assertIn(words, got)
        pinned = {h: freeze.pinned_cli(h, committed) for h in ("codex", "gemini")}
        with at_documented(), settled(O=True, G=True, cli=pinned):
            self.assertIsNone(freeze.unrecorded_shapes_problem(committed))
        self.assertIsNone(freeze.unrecorded_shapes_problem(draft(("A",))))
        self.assertIsNone(freeze.unrecorded_shapes_problem({"tasks": []}))

    def test_fs_main_refuses_at_documented_and_passes_at_recorded(self):
        self.assertEqual(main_problems(freeze), [])

    def test_fs_docs_the_adapters_name_the_refusal_this_lane_built(self):
        # round-2 ruling 2 (glitch-b5): the SHAPES_SOURCE paragraph of each adapter's docstring names freeze.py's
        # refusal (T3) and no longer says it is owed to a later slice
        for mod, arm in ((codex_adapter, "arm O"), (gemini_adapter, "arm G")):
            doc = " ".join(mod.__doc__.split())
            with self.subTest(adapter=mod.__name__):
                self.assertNotIn("owed to a later slice", doc)
                for words in ("freeze.py now refuses a design row of this harness", f"({arm})",
                              'while SHAPES_SOURCE is not "recorded"', "freeze.unrecorded_shapes_problem"):
                    self.assertIn(words, doc)

    def test_fs_check_mode_is_unchanged(self):
        # lane pf1-l1-freeze-gates (pre-freeze review 1, m1): freeze.py --check no longer reads the copy record and
        # the holdout fields only; it reads every leg a freeze reads (check_legs) and is red on a draft the freeze
        # refuses. What stays unchanged here: the vendor legs it reads are unrecorded_shapes_problem's, and --check is
        # green when every leg holds (tests/test_pf1_freeze_gates.py G1.check binds the legs themselves).
        out = io.StringIO()
        held = [("vendor legs i-iii", []), ("pending", [])]
        with mock.patch.object(freeze, "check_legs", lambda d: held), contextlib.redirect_stdout(out):
            self.assertEqual(freeze.main(["--check"]), 0, out.getvalue())
        self.assertIn("freeze --check: vendor legs i-iii: ok", out.getvalue())
        self.assertIn("unrecorded_shapes_problem(draft)", Path(freeze.__file__).read_text().split(
            "def check_legs(", 1)[1].split("\ndef ", 1)[0])


def refused_registry(*a, **k):
    raise native_reader_registration.RegistrationRefused("synthetic: the acceptance record is uncommitted")


def no_git_registry(*a, **k):
    # round 8 ruling 1 (review e7496cf NIT 1): production_readers runs git; a missing binary raises FileNotFoundError
    raise FileNotFoundError(2, "No such file or directory", "git")


def unreadable_registry(*a, **k):
    raise PermissionError(13, "Permission denied", "native-reader-acceptance.json")


# (case, the legs settled, the registry, the words the refusal must carry for each vendor arm)
CHECK_CASES = (
    ("leg ii absent", ("i", "rows", "items", "iii"), None, "absent", ("leg ii", "VENDOR_CHECK_SHAPES_SOURCE")),
    ("leg ii documented", ("i", "rows", "items", "iii"), None, None, ("leg ii", "'documented'")),
    ("a row unsettled", ("i", "ii", "items", "iii"), None, "one", ("leg ii", "is PENDING")),
    # round 8 ruling 3 (P2): a READER item on no RECORDED fixture keeps leg ii closed
    ("a reader item unrecorded", ("i", "ii", "rows", "iii"), None, None, ("leg ii", "names no RECORDED fixture")),
    ("leg iii empty", ("i", "ii", "rows", "items"), lambda *a, **k: {}, None,
     ("leg iii", "no native reader is registered")),
    ("leg iii another vendor only", ("i", "ii", "rows", "items"), lambda *a, **k: {"synthetic-harness": object()},
     None, ("leg iii", "no native reader is registered")),
    ("leg iii raises", ("i", "ii", "rows", "items"), refused_registry, None,
     ("leg iii", "the native-reader registry refuses", "synthetic: the acceptance record is uncommitted")),
    ("leg iii without git", ("i", "ii", "rows", "items"), no_git_registry, None,
     ("leg iii", "the native-reader registry could not run", "FileNotFoundError")),
    ("leg iii any OSError", ("i", "ii", "rows", "items"), unreadable_registry, None,
     ("leg iii", "the native-reader registry could not run", "PermissionError")),
)


def check_problems(mod) -> list:
    with at_documented():
        return _check_problems(mod)


def _check_problems(mod) -> list:
    out = []
    for name, legs, registry, edit, words in CHECK_CASES:
        for arms in (("A", "O"), ("A", "G"), ("A", "O", "G")):
            vendors = [a for a in arms if a in ADAPTERS]
            with settled(legs=legs, registry=registry, **{a: True for a in vendors}), contextlib.ExitStack() as s:
                if edit == "absent":
                    for a in vendors:
                        s.enter_context(mock.patch.dict(check_take.VENDOR_CHECK_SHAPES_SOURCE))
                        del check_take.VENDOR_CHECK_SHAPES_SOURCE[HARNESS[a]]
                if edit == "one":
                    for a in vendors:
                        key = sorted(check_take.VENDOR_PENDING_ROWS[HARNESS[a]])[0]
                        reason = check_take.VENDOR_PENDING_ROWS[HARNESS[a]][key]["reason"]
                        check_take.VENDOR_PENDING_ROWS[HARNESS[a]][key] = {"reason": reason, "state": "PENDING"}
                        words = ("leg ii", f"{key} {reason} is PENDING")
                try:
                    code, text, written = run_main(mod, draft(arms))
                except Exception as e:  # noqa: BLE001 - a traceback is itself the failure FS-check names
                    out.append(f"{name} {arms}: main raised {type(e).__name__}: {e}")
                    continue
            if code != 1 or written or "REFUSE" not in text:
                out.append(f"{name} {arms}: not refused (exit {code}, {len(written)} written)")
            for a in vendors:
                for w in (f"arm {a} ({HARNESS[a]}): leg",) + tuple(words):
                    if w not in text:
                        out.append(f"{name} {arms}: the refusal does not carry {w!r} for arm {a}: {text[:300]!r}")
    with settled(O=True, G=True):
        code, text, written = run_main(mod, draft(("A", "O", "G")))
    if code != 0 or len(written) != 1:
        out.append(f"all three legs settled: refused (exit {code}): {text[:300]!r}")
    code, text, written = run_main(mod, draft(("A",)))
    if code != 0 or len(written) != 1:
        out.append(f"a claude-code-only draft is refused: {text[:200]!r}")
    return out


class TheFreezeGateHasThreeLegs(unittest.TestCase):
    def test_fs_check_each_leg_refuses_and_all_three_pass(self):
        self.assertEqual(check_problems(freeze), [])

    def test_fs_check_after_the_settlement_the_committed_draft_passes_every_leg(self):
        # glitch-f1's merge-5 ruling (b), 22 Oct 2026, keeping both lanes' intent. Since Javier's acceptance commit
        # (5457e75e) the production registry holds both vendor readers (lane freeze-gates-fix S9), and since the vendor
        # settlement (stage V) both vendors' shapes read "recorded": (1) the committed draft passes all three legs for
        # codex and gemini on the real registry; (2) with the registry empty, leg iii is named for both vendors; (3) at
        # the pre-settlement "documented" state, legs i and ii are named while leg iii holds on the real registry.
        import native_reader_registration as nrr
        committed = json.loads((HERE / "prereg-draft.json").read_text())
        self.assertEqual(nrr.production_readers(), {"codex": nrr.codex_reader, "gemini": nrr.gemini_reader})
        self.assertIsNone(freeze.unrecorded_shapes_problem(committed))                                  # (1)
        for harness in ("codex", "gemini"):
            self.assertEqual(freeze.registration_problems(harness), [], harness)
        with mock.patch.object(native_reader_registration, "production_readers", lambda *a, **k: {}):
            empty = freeze.unrecorded_shapes_problem(committed)                                       # (2)
        self.assertIsNotNone(empty)
        for arm, harness in (("O", "codex"), ("G", "gemini")):
            self.assertIn(f"arm {arm} ({harness}): leg iii:", empty)
            self.assertNotIn(f"arm {arm} ({harness}): leg i:", empty)
            self.assertNotIn(f"arm {arm} ({harness}): leg ii:", empty)
        with at_documented():
            documented = freeze.unrecorded_shapes_problem(committed)                                  # (3)
        self.assertIsNotNone(documented)
        for words in ("arm O (codex): leg i:", "arm G (gemini): leg i:", "arm O (codex): leg ii:",
                      "arm G (gemini): leg ii:", "arm G (gemini): leg ii: T-11 inherited-context is PENDING"):
            self.assertIn(words, documented)
        for arm, harness in (("O", "codex"), ("G", "gemini")):
            self.assertNotIn(f"arm {arm} ({harness}): leg iii:", documented)

def mutant(old: str, new: str):
    src = Path(freeze.__file__).read_text(encoding="utf-8")
    if src.count(old) != 1:
        raise AssertionError(f"mutation site occurs {src.count(old)} times in freeze.py: {old!r}")
    m = types.ModuleType("freeze_mutant")
    m.__file__ = freeze.__file__
    sys.modules[m.__name__] = m
    try:
        exec(compile(src.replace(old, new), freeze.__file__ + " (witness)", "exec"), m.__dict__)  # noqa: S102
    finally:
        del sys.modules[m.__name__]
    return m


WITNESSES = {
    "the check's call deleted": ("        problem = unrecorded_shapes_problem(draft)\n        if problem:\n"
                                 "            raise ValueError(problem)\n", ""),
    "the comparison disabled": ("        if source != RECORDED_SHAPES:", "        if False:"),
}
CHECK_WITNESSES = {
    "leg ii's comparison deleted": ("    out = [] if source == RECORDED_SHAPES else ", "    out = [] if True else "),
    "leg ii's settled condition deleted": ("    return out + check_take.vendor_rows_problems(harness)\n",
                                           "    return out\n"),
    "leg iii deleted": ('        legs += [f"leg iii: {p}" for p in registration_problems(harness)]\n', ""),
    "leg ii's reader items deleted": ("    out += check_take.vendor_reader_items_problems(harness)\n", ""),
    "leg iii's OSError refusal deleted": ("    except OSError as e:\n", "    except native_reader_registration."
                                                                         "RegistrationRefused as e:\n"),
}


class Witnesses(unittest.TestCase):
    def test_fs_witness_each_mutant_goes_red(self):
        for name, (old, new) in WITNESSES.items():
            with self.subTest(witness=name):
                self.assertNotEqual(main_problems(mutant(old, new)), [], f"witness {name} stayed green")

    def test_fs_check_witness_each_mutant_goes_red(self):
        for name, (old, new) in CHECK_WITNESSES.items():
            with self.subTest(witness=name):
                self.assertNotEqual(check_problems(mutant(old, new)), [], f"witness {name} stayed green")


if __name__ == "__main__":
    unittest.main()
