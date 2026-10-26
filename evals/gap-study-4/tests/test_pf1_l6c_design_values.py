#!/usr/bin/env python3
"""Merge lane L6c (the lane orchestrator's assignment of Mon 26 Oct 2026, under Javier's standing delegation): the
pf1-checker-digest closure check's new MINOR (REVIEW-pf1-checker-digest-c99f114.md, "leak values come from disk").

The digest a walk is checked under binds the pre-registration's leak_words and leak_context_excusals (B7's third part,
design_values_sha256). Before this lane the WRITER (design_constants_sha256, vendor_design_constants_sha256: what a
checked walk, and walk_regrade's recheck, record) read those two values from the file on disk at the moment the digest
was asked for, while the checker had read them from the design view's own pre (prereg.load(), cached once per
process). A walk process that loaded the draft, then saw its leak values regenerated before the side digest was taken,
recorded the NEW values' digest while it was checked under the OLD ones, so it counted when it should read stale.

The rule: the writer binds the two values the view carries (design.pre, a missing key reading None as design_values
reads it); the READER (checker_constants_sha256, vendor_checker_constants_sha256, pending_walk.constants_in_force)
keeps reading disk. They agree when nothing changed, and a change between load and digest fails closed (stale).

  V1.agree      a view carrying the in-force values: each writer records exactly what the reader holds in force
                (claude-code, codex, gemini), so an unchanged walk still counts
  V2.load-gap   the pre-registration's leak_words, then its leak_context_excusals, edited on disk AFTER the view was
                built: each writer's digest is unmoved (it binds the view's values), the reader's moves, so the two
                differ and the walk reads stale; undoing the edit restores agreement
  V3.view       a view whose own leak values differ from disk's (or lack one) records a digest the reader never holds,
                and two views differing only in one leak value record different digests
  V4.witnesses  each anchored mutant of check_take.py below turns a clause red

Red first: before the lane V2 fails by its own assertion (the writer reads disk, so it moves with the edit and agrees
with the reader). Fixtures: one temporary copy of the pre-registration in force, named through DESIGN_VALUES_PATH; the
study's files are never written. No model, network, container or subprocess.

    python3 -B -W ignore evals/gap-study-4/tests/test_pf1_l6c_design_values.py
"""
from __future__ import annotations

import copy
import json
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

ct = prereg = None
VENDORS = ("codex", "gemini")
KEYS = ("leak_words", "leak_context_excusals")


def setUpModule():
    global ct, prereg
    import check_take as ct
    import prereg


class Draft:
    """A temporary copy of the pre-registration in force, named as DESIGN_VALUES_PATH while the rig is open."""

    def __init__(self, mod):
        self.tmp = Path(tempfile.mkdtemp(prefix="l6c-dv-"))
        self.path = self.tmp / "prereg-draft.json"
        shutil.copyfile(prereg.in_force(), self.path)
        self.original = self.path.read_bytes()
        self.patch = mock.patch.object(mod, "DESIGN_VALUES_PATH", self.path)

    def __enter__(self):
        self.patch.start()
        return self

    def __exit__(self, *exc):
        self.patch.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def edit(self, key: str):
        doc = json.loads(self.path.read_text(encoding="utf-8"))
        value = doc.get(key)
        if isinstance(value, list):
            doc[key] = [*value, "zz-l6c-load-gap-probe"]
        elif isinstance(value, dict):
            doc[key] = {**value, "zz-l6c-load-gap-probe": ["zz"]}
        else:
            doc[key] = ["zz-l6c-load-gap-probe"]
        self.path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def restore(self):
        self.path.write_bytes(self.original)


def on_disk(path: Path) -> dict:
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    return {k: copy.deepcopy(doc.get(k)) for k in KEYS}


def views(mod, values: dict):
    """{harness: (the view a writer reads, its writer, the reader in force)} for a view carrying `values`."""
    pre = copy.deepcopy(mod.CHECKER_CONSTANTS)
    pre["driver_constants"]["permission_mode_by_arm"] = {"A": "bypassPermissions"}
    pre.update(copy.deepcopy(values))
    claude = mod.Design(task_id="t", spec={}, pre=pre, harness="claude-code")
    out = {"claude-code": (claude, mod.design_constants_sha256, lambda: mod.checker_constants_sha256())}
    for h in VENDORS:
        out[h] = (mod.vendor_view(claude.replace(harness=h)), mod.vendor_design_constants_sha256,
                  lambda h=h: mod.vendor_checker_constants_sha256(h))
    return out


def agree_cases(mod) -> list:
    out = []
    with Draft(mod) as d:
        for h, (view, writer, reader) in views(mod, on_disk(d.path)).items():
            wrote, held = writer(view), reader()
            if wrote is None or wrote != held:
                out.append(f"V1.agree {h}: the writer records {wrote} and the reader holds {held} in force")
    return out


def load_gap_cases(mod) -> list:
    out = []
    with Draft(mod) as d:
        loaded = views(mod, on_disk(d.path))           # the views are built, then the file changes under them
        before = {h: (w(v), r()) for h, (v, w, r) in loaded.items()}
        for key in KEYS:
            d.edit(key)
            for h, (view, writer, reader) in loaded.items():
                wrote, held = writer(view), reader()
                if held == before[h][1]:
                    out.append(f"V2.load-gap {h} {key}: the reader did not move with the edit on disk")
                if wrote != before[h][0]:
                    out.append(f"V2.load-gap {h} {key}: the writer moved with the disk ({before[h][0]} -> {wrote}); "
                               f"it binds the view's loaded values")
                if wrote == held:
                    out.append(f"V2.load-gap {h} {key}: the writer and the reader agree after the edit, so a walk "
                               f"checked under the old values counts")
            d.restore()
            for h, (view, writer, reader) in loaded.items():
                if writer(view) != reader():
                    out.append(f"V2.load-gap {h} {key}: undoing the edit did not restore agreement")
    return out


def view_cases(mod) -> list:
    out = []
    with Draft(mod) as d:
        disk = on_disk(d.path)
        for key in KEYS:
            changed = copy.deepcopy(disk)
            changed[key] = (changed[key] or []) + ["zz-l6c-view-only"] if isinstance(changed[key], list) \
                else {**(changed[key] or {}), "zz-l6c-view-only": ["zz"]}
            dropped = {k: v for k, v in disk.items() if k != key}
            same, other, gone = views(mod, disk), views(mod, changed), views(mod, dropped)
            for h in same:
                a = same[h][1](same[h][0])
                b = other[h][1](other[h][0])
                c = gone[h][1](gone[h][0])
                held = same[h][2]()
                if b is None or b == a or b == held:
                    out.append(f"V3.view {h} {key}: a view carrying another value records {b} (same view {a}, in "
                               f"force {held})")
                if disk.get(key) is not None and (c is None or c == held):
                    out.append(f"V3.view {h} {key}: a view lacking the key records {c}, the digest in force")
    return out


CASES = (("V1.agree", agree_cases), ("V2.load-gap", load_gap_cases), ("V3.view", view_cases))

# Each witness: an anchored edit of check_take.py (its anchor occurs exactly once) and the clauses it must turn red.
WITNESSES = (
    ("the writer reads disk", "    values = design_values_digest(view_design_values(design))\n",
     "    values = design_values_sha256()\n", ("V2.load-gap", "V3.view")),
    ("the writer binds no design values", "    values = design_values_digest(view_design_values(design))\n",
     "    values = ''\n", ("V1.agree",)),
    ("the view's values read from CHECKER_CONSTANTS keys only",
     "    return {k: copy.deepcopy(design.pre.get(k)) for k in DESIGN_VALUE_KEYS}\n",
     "    return {k: copy.deepcopy(design.pre.get(k)) for k in DESIGN_VALUE_KEYS if k in CHECKER_CONSTANTS}\n",
     ("V1.agree",)),
    ("the claude-code writer back on the reader",
     "        return view_checker_constants_sha256(got, design)\n    except (KeyError, TypeError, AttributeError, "
     "CheckRefused):\n        return None\n\n\n# ---- B7",
     "        return checker_constants_sha256(got)\n    except (KeyError, TypeError, AttributeError, "
     "CheckRefused):\n        return None\n\n\n# ---- B7", ("V2.load-gap",)),
    ("the vendor writer back on the reader",
     "        return view_checker_constants_sha256(got, design)\n    except (KeyError, TypeError, AttributeError, "
     "CheckRefused):\n        return None\n\n\ndef checker_view(",
     "        return checker_constants_sha256(got)\n    except (KeyError, TypeError, AttributeError, "
     "CheckRefused):\n        return None\n\n\ndef checker_view(", ("V2.load-gap",)),
)


def mutant(mod, old: str, new: str):
    src = Path(mod.__file__).read_text(encoding="utf-8")
    if src.count(old) != 1:
        raise AssertionError(f"V4.witnesses: the mutation site occurs {src.count(old)} times: {old!r}")
    m = types.ModuleType(mod.__name__)
    m.__file__ = mod.__file__
    with mock.patch.dict(sys.modules, {mod.__name__: m}):
        exec(compile(src.replace(old, new), mod.__file__, "exec"), m.__dict__)
    return m


class Base(unittest.TestCase):
    def clean(self, clause: str, cases, *args):
        """cases(*args) returns no problem line; any exception fails the clause by an assertion, never an error."""
        try:
            got = cases(*args)
        except Exception as exc:                 # noqa: BLE001
            self.fail(f"{clause}: raised {exc!r}")
        self.assertEqual(got, [], clause)


class V1Agree(Base):
    def test_an_unchanged_view_agrees_with_the_reader(self):
        self.clean("V1.agree", agree_cases, ct)


class V2LoadGap(Base):
    def test_a_change_between_load_and_digest_reads_stale(self):
        self.clean("V2.load-gap", load_gap_cases, ct)


class V3View(Base):
    def test_the_writer_binds_the_views_own_values(self):
        self.clean("V3.view", view_cases, ct)


class V4Witnesses(unittest.TestCase):
    def test_each_witness_turns_its_clause_red(self):
        clauses = dict(CASES)
        for name, old, new, want in WITNESSES:
            with self.subTest(witness=name):
                m = mutant(ct, old, new)
                for clause in want:
                    try:
                        red = clauses[clause](m)
                    except Exception as exc:     # noqa: BLE001 - a clause the mutant makes raise is red, by name
                        red = [f"{clause}: raised {exc!r}"]
                    self.assertTrue(red, f"V4.witnesses: {name} survives {clause}")
                    self.assertTrue(all(line.startswith(clause) for line in red),
                                    f"V4.witnesses: {name} is red outside {clause}: {red[:2]}")


if __name__ == "__main__":
    unittest.main()
