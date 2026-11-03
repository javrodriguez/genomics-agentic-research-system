#!/usr/bin/env python3
"""Lane fold10/rehearsal-road (Gap Study round 4; glitch-45's road A ruling of Mon 2 Nov 2026, under Javier's standing
delegation; fold 9's review, B1 and m1).

  PINS       check_results.check_pins, unmocked, on the real draft's shape: every pin re-read where the code that wrote
             it can read it, the image locks from the study folder and each template file from take_config's render.
             Every pin is still counted and still compared: another hash, a lost file or a harness or model the
             renderer refuses each refuse, and a node anywhere else still resolves against the repository root.
  LIMIT      (review m1) result.derive refuses a frozen file whose published_tip_residual is not
             freeze.PUBLISHED_TIP_LIMIT.

The real draft and the study's real files are read; nothing is written outside temporary directories. No model, network
or container.
"""

from __future__ import annotations

import contextlib
import copy
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import check_results as cr  # noqa: E402
import freeze  # noqa: E402
import result  # noqa: E402
from box import take_config  # noqa: E402

DRAFT = json.loads((HERE / "prereg-draft.json").read_text(encoding="utf-8"))
OFF_ROOT = 12        # the five image locks and seven template files whose paths are not repository-relative


def pins(pre):
    """check_pins on `pre`, unmocked but for the document it reads: (problems, the printed count line)."""
    out = io.StringIO()
    with mock.patch.object(cr.prereg, "load", return_value=pre), contextlib.redirect_stdout(out):
        problems = cr.check_pins()
    return problems, out.getvalue()


def counted(pre) -> int:
    n = 0

    def walk(node):
        nonlocal n
        if isinstance(node, dict):
            n += bool(node.get("path") and node.get("sha256"))
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    walk(pre)
    return n


def templates(pre):
    for harness, models in pre["config_templates"].items():
        for model, entry in models.items():
            yield harness, model, entry


class Pins(unittest.TestCase):
    def test_the_real_draft_holds_every_pin(self):
        problems, printed = pins(DRAFT)
        self.assertEqual(problems, [])
        self.assertIn(f"{counted(DRAFT)} pinned file(s) re-hashed", printed)

    def test_the_real_draft_has_the_off_root_shape_this_guards(self):
        locks = [e["path"] for e in DRAFT["image_locks"]]
        files = [f["path"] for _, _, e in templates(DRAFT) for f in e["files"]]
        self.assertEqual(len(locks) + len(files), OFF_ROOT)
        for rel in locks + files:
            self.assertFalse((cr.REPO / rel).exists(), rel)
        for rel in locks:
            self.assertTrue((HERE / rel).is_file(), rel)

    def test_every_lock_is_compared(self):
        for i in range(len(DRAFT["image_locks"])):
            pre = copy.deepcopy(DRAFT)
            pre["image_locks"][i]["sha256"] = "0" * 64
            problems, _ = pins(pre)
            self.assertEqual(len(problems), 1, i)
            self.assertIn(f".image_locks[{i}]", problems[0])
            self.assertIn("does not match", problems[0])

    def test_every_template_file_is_compared(self):
        for harness, model, _ in templates(DRAFT):
            pre = copy.deepcopy(DRAFT)
            pre["config_templates"][harness][model]["files"][0]["sha256"] = "0" * 64
            problems, _ = pins(pre)
            self.assertEqual(len(problems), 1, (harness, model))
            self.assertIn(f".config_templates.{harness}.{model}.files[0]", problems[0])
            self.assertIn("does not match", problems[0])

    def test_a_lock_edited_on_disk_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            for e in DRAFT["image_locks"]:
                (Path(tmp) / e["path"]).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(HERE / e["path"], Path(tmp) / e["path"])
            pre = {"image_locks": DRAFT["image_locks"]}
            with mock.patch.object(cr, "HERE", Path(tmp)):
                self.assertEqual(pins(pre)[0], [])
                Path(tmp, DRAFT["image_locks"][3]["path"]).write_text("edited\n")
                problems, _ = pins(pre)
                self.assertEqual(len(problems), 1)
                self.assertIn("does not match", problems[0])
                Path(tmp, DRAFT["image_locks"][3]["path"]).unlink()
                problems, _ = pins(pre)
                self.assertEqual(len(problems), 1)
                self.assertIn("is missing", problems[0])

    def test_a_render_that_moved_is_refused(self):
        pre = {"config_templates": DRAFT["config_templates"]}
        real = take_config.files_for

        def moved(harness, *, model, run_tree=None):
            return {p: d + b"\n" for p, d in real(harness, model=model, run_tree=run_tree).items()}
        with mock.patch.object(take_config, "files_for", moved):
            problems, _ = pins(pre)
        self.assertEqual(len(problems), sum(1 for _ in templates(DRAFT)))
        self.assertTrue(all("does not match" in p for p in problems), problems)

    def test_a_name_the_render_does_not_make_is_refused_never_dropped(self):
        pre = {"config_templates": {"codex": {"gpt-6-luna": {"files": [{"path": "other.toml", "sha256": "0" * 64}]}}}}
        problems, printed = pins(pre)
        self.assertEqual(len(problems), 1)
        self.assertIn("other.toml", problems[0])
        self.assertIn("1 pinned file(s)", printed)

    def test_a_harness_the_render_refuses_is_refused_never_dropped(self):
        pre = {"config_templates": {"no-such": {"m": {"files": [{"path": "settings.json", "sha256": "0" * 64}]}}}}
        problems, _ = pins(pre)
        self.assertEqual(len(problems), 1)
        self.assertIn("no-such", problems[0])

    def test_each_template_is_rendered_for_its_own_model(self):
        """The two codex models' config.toml share a name and differ in hash: swapping them must refuse."""
        pre = copy.deepcopy(DRAFT)
        codex = pre["config_templates"]["codex"]
        a, b = codex["gpt-6.1-sol"]["files"][0], codex["gpt-6-luna"]["files"][0]
        self.assertEqual(a["path"], b["path"])
        self.assertNotEqual(a["sha256"], b["sha256"])
        a["sha256"], b["sha256"] = b["sha256"], a["sha256"]
        self.assertEqual(len(pins(pre)[0]), 2)

    def test_any_other_node_still_resolves_against_the_repository_root(self):
        lock = DRAFT["image_locks"][0]
        for pre in ({"elsewhere": {"path": lock["path"], "sha256": lock["sha256"]}},
                    {"image_locks": {"x": {"path": lock["path"], "sha256": lock["sha256"]}}},
                    {"config_templates": {"codex": {"gpt-6-luna": {"path": "config.toml", "sha256": "0" * 64}}}}):
            problems, _ = pins(pre)
            self.assertEqual(len(problems), 1, pre)
            self.assertIn("pinned file is missing", problems[0])
        rel = "evals/gap-study-4/check_results.py"
        self.assertEqual(pins({"elsewhere": {"path": rel, "sha256": cr.sha256(cr.REPO / rel)}})[0], [])

    def test_a_lock_node_cannot_read_outside_the_study_by_a_template_name(self):
        """A template's name is never a file: the render is the only source, whatever sits at that name on disk."""
        pre = {"config_templates": {"codex": {"gpt-6-luna": {"files": [
            {"path": "check_results.py", "sha256": cr.sha256(HERE / "check_results.py")}]}}}}
        self.assertEqual(len(pins(pre)[0]), 1)


class Limit(unittest.TestCase):
    def derive_on(self, pre):
        row = {"slot": 1}
        with mock.patch.object(result.stats, "load_results", return_value=[]), \
                mock.patch.object(result.takes, "load_rows", return_value=[row]), \
                mock.patch.object(result.takes, "read_history", return_value=[]), \
                mock.patch.object(result.prereg, "require_frozen", return_value=pre), \
                mock.patch.object(result, "from_records", return_value="derived") as made:
            return result.derive(), made

    def test_the_constant_passes(self):
        got, made = self.derive_on({"published_tip_residual": freeze.PUBLISHED_TIP_LIMIT})
        self.assertEqual(got, "derived")
        made.assert_called_once()

    def test_stripped_or_softened_is_refused(self):
        for pre in ({}, {"published_tip_residual": None}, {"published_tip_residual": ""},
                    {"published_tip_residual": "Nothing to report."},
                    {"published_tip_residual": freeze.PUBLISHED_TIP_LIMIT + " "}):
            with self.assertRaises(ValueError) as caught:
                self.derive_on(pre)
            self.assertIn("published_tip_residual", str(caught.exception))

    def test_main_reports_it_as_a_failure_not_a_traceback(self):
        out = io.StringIO()
        with mock.patch.object(result.stats, "load_results", return_value=[]), \
                mock.patch.object(result.takes, "load_rows", return_value=[{"slot": 1}]), \
                mock.patch.object(result.takes, "read_history", return_value=[]), \
                mock.patch.object(result.prereg, "require_frozen", return_value={}), \
                contextlib.redirect_stdout(out):
            self.assertEqual(result.main(["--check"]), 1)
        self.assertIn("result: FAIL", out.getvalue())


if __name__ == "__main__":
    unittest.main()
