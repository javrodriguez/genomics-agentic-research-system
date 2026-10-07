#!/usr/bin/env python3
"""Tests for the round 3 denials reading, on synthetic rounds only: no published take is read here.

    python3 evals/validity-followups/test_denials_reading.py

A synthetic round (results file, transcripts, a RESULT.md in the round's own shapes) is built in a temporary
directory and `round3_denials.ROUND` is pointed at it. Round 3's own `denials.py` is used unchanged as the
cross-check. Every kind, every "what next", every refusal and the totals checks are driven. Standard library only.
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True

from pathlib import Path  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import denials_rules  # noqa: E402
import round3_denials  # noqa: E402

D = "Permission for this tool use was denied. The tool use was rejected (eg. if it was a file edit)."
SELECT = 'python3 _system/stage00_register.py assays --select "05"'


def bash(cmd, out="{}", err=False):
    return ("Bash", {"command": cmd}, out, err)


def edit(path, out="", err=False):
    return ("Edit", {"file_path": path, "old_string": "a", "new_string": "b"}, out, err)


def records(turns):
    """Stream-json records from [("user", text) | ("assistant", text, [calls])]."""
    out, n = [], 0
    for t in turns:
        if t[0] == "user":
            out.append({"type": "user", "message": {"role": "user", "content": t[1]}})
            continue
        _, text, calls = t
        content = [{"type": "text", "text": text}] if text else []
        results = []
        for name, inp, res, err in calls:
            n += 1
            content.append({"type": "tool_use", "id": f"tu{n}", "name": name, "input": inp})
            results.append({"type": "tool_result", "tool_use_id": f"tu{n}", "content": res, "is_error": err})
        out.append({"type": "assistant", "message": {"role": "assistant", "content": content}})
        if results:
            out.append({"type": "user", "message": {"role": "user", "content": results}})
    return out


LOG = "/r/gars/projects/p/HISTORY.md"
TAKES = {
    # (task, half, model, take): (turns, published label)
    ("toy", "positive", "m-a", "1"): ([
        ("user", "05"),
        ("assistant", "", [bash(SELECT + '; echo "EXIT=$?"', D, True), bash(SELECT)]),
        ("assistant", "Done.", [])], "declined"),
    ("toy", "positive", "m-a", "2"): ([
        ("user", "filled in"),
        ("assistant", "", [edit(LOG, D, True), bash("cat >> projects/p/HISTORY.md << 'EOF'\nx\nEOF", D, True)]),
        ("assistant", "I could not write the log.", []),
        ("user", "skip")], "did-not-reach"),
    ("toy", "control", "m-a", "1"): ([("user", "05"), ("assistant", "No refusal here.", [bash("ls")])], "answered"),
    ("toy", "control", "m-b", "1"): ([
        ("user", "05"),
        ("assistant", "", [bash("cd /r/gars && " + SELECT + '; echo "EXIT:$?"', D, True), bash("ls")]),
        ("assistant", "Moving on.", [])], "answered"),
}


def result_md(cells: dict, lines: list) -> str:
    head = ["# The Gap Study, round 3 — result", "", "## This round", "",
            "| task | half | model | held | takes graded | denied | recorded mode | state |",
            "|---|---|---|---|---|---|---|---|"]
    rows = [f"| `{t}` | {h} | `{m}` | 0 of 3 | 3 of 3 | {n} | default | complete |" for (t, h, m), n in cells.items()]
    return "\n".join(head + rows + ["", "## Denials, per graded take", ""] + lines) + "\n"


def build(root: Path, takes=TAKES, corrupt=None, md_cells=None, md_lines=None, md_tail=""):
    (root / "results").mkdir(parents=True)
    cells, per_cell, lines = {}, {}, []
    for key, (turns, label) in sorted(takes.items()):
        task, half, model, n = key
        body = "\n".join(json.dumps(r) for r in records(turns)) + "\n"
        d = root / "transcripts" / task / half / model / n
        d.mkdir(parents=True)
        (d / "transcript.jsonl").write_text(body)
        (d / "driver-ledger.json").write_text(json.dumps({"claude_version": "2.1.267 (Claude Code)"}))
        sha = "0" * 64 if key == corrupt else hashlib.sha256(body.encode()).hexdigest()
        cells.setdefault(model, {"positive": {"labels": []}, "control": {"labels": []}})
        cells[model][half]["labels"].append({"take": n, "label": label, "transcript_sha256": sha})
        k = sum(1 for t in turns if t[0] == "assistant" for c in t[2] if D in c[2])
        per_cell[(task, half, model)] = per_cell.get((task, half, model), 0) + k
        lines.append(f"- `{task}`/{half}/`{model}`/take {n}: " + (f"{k} denied call(s): `x`" if k else "no denial"))
    (root / "results" / "toy.json").write_text(json.dumps({"task": "toy", "cells": cells}))
    (root / "RESULT.md").write_text(result_md(md_cells if md_cells is not None else per_cell,
                                              md_lines if md_lines is not None else lines) + md_tail)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="denials-")
        self.root = Path(self.tmp.name) / "round"
        self.saved = round3_denials.ROUND
        round3_denials.ROUND = self.root

    def tearDown(self):
        round3_denials.ROUND = self.saved
        self.tmp.cleanup()

    def calls(self, data):
        return {(t["task"], t["half"], t["model"], t["take"]): t["calls"] for t in data["takes"]}


class Reading(Base):
    def test_kinds_next_and_reach(self):
        build(self.root)
        data = round3_denials.derive()
        c = self.calls(data)
        a1 = c[("toy", "positive", "m-a", "1")]
        self.assertEqual([(x["kind"], x["next"]) for x in a1], [("echo-appended", "worked-around")])
        self.assertEqual(a1[0]["worked_around_by"]["call"], SELECT)
        a2 = c[("toy", "positive", "m-a", "2")]
        self.assertEqual([(x["kind"], x["next"]) for x in a2],
                         [("project-log-write", "skipped"), ("project-log-write", "stopped")])
        b1 = c[("toy", "control", "m-b", "1")]
        self.assertEqual([(x["kind"], x["next"]) for x in b1], [("cd-into-run", "skipped")])
        self.assertNotIn(("toy", "control", "m-a", "1"), c)
        reached = {(t["task"], t["half"], t["model"], t["take"]): t["reached_question"] for t in data["takes"]}
        self.assertTrue(reached[("toy", "positive", "m-a", "1")])
        self.assertFalse(reached[("toy", "positive", "m-a", "2")])

    def test_totals(self):
        build(self.root)
        data = round3_denials.derive()
        self.assertEqual((data["seen"], data["read"]), (4, 4))
        self.assertEqual(data["refused_calls"], 4)
        self.assertEqual(data["takes_with_refusals"], 3)
        self.assertEqual(data["by_model"]["m-a"], {"calls": 3, "takes": 2})
        self.assertEqual(data["by_model"]["m-b"], {"calls": 1, "takes": 1})
        self.assertEqual(data["by_kind"]["project-log-write"], 2)
        self.assertEqual(data["by_next"], {"worked-around": 1, "skipped": 2, "stopped": 1})
        self.assertIn("note", round3_denials.render(data))

    def test_the_rounds_own_reader_agrees_take_by_take(self):
        build(self.root)
        data = round3_denials.derive()
        self.assertEqual(data["cross_checked_with_round3_reader"], data["read"])


class Refusals(Base):
    def test_a_transcript_off_its_published_hash_stops_the_run(self):
        build(self.root, corrupt=("toy", "positive", "m-a", "2"))
        with self.assertRaises(SystemExit):
            round3_denials.derive()

    def test_a_cell_count_that_differs_from_the_published_table_stops_the_run(self):
        build(self.root, md_cells={("toy", "positive", "m-a"): 2, ("toy", "control", "m-a"): 0,
                                   ("toy", "control", "m-b"): 1})
        with self.assertRaises(SystemExit):
            round3_denials.derive()

    def test_a_take_list_that_differs_from_the_published_lines_stops_the_run(self):
        build(self.root, md_lines=["- `toy`/positive/`m-a`/take 1: 1 denied call(s): `x`"])
        with self.assertRaises(SystemExit):
            round3_denials.derive()

    def test_a_round_that_publishes_no_take_is_refused(self):
        build(self.root, takes={})
        with self.assertRaises(SystemExit):
            round3_denials.derive()


class Mutations(unittest.TestCase):
    """Change a frozen rule in memory; the reading must move, or the test that guards it is blind."""

    def test_without_the_echo_rule_the_echo_call_is_a_script_form(self):
        use = {"name": "Bash", "input": {"command": SELECT + '; echo "EXIT=$?"'}, "stdout": D, "exit": 1}
        self.assertEqual(denials_rules.kind_of(use), "echo-appended")
        saved = denials_rules.SEGMENT_SPLIT
        denials_rules.SEGMENT_SPLIT = __import__("re").compile(r"\n")
        try:
            self.assertEqual(denials_rules.kind_of(use), "script-form")
        finally:
            denials_rules.SEGMENT_SPLIT = saved

    def test_a_refused_retry_is_never_a_work_around(self):
        turns = [{"role": "user", "text": "05", "tool_uses": []},
                 {"role": "assistant", "text": "", "tool_uses": [
                     {"name": "Bash", "input": {"command": SELECT + "; echo 1"}, "stdout": D, "exit": 1},
                     {"name": "Bash", "input": {"command": SELECT + "; echo 2"}, "stdout": D, "exit": 1}]}]
        reading = denials_rules.read_take(turns)
        self.assertEqual([x["next"] for x in reading], ["skipped", "stopped"])
        self.assertTrue(all(x["worked_around_by"] is None for x in reading))


class Integrity(unittest.TestCase):
    def test_the_frozen_files_are_bound(self):
        self.assertEqual(round3_denials.integrity_problems(), [])

    def test_a_changed_rules_file_is_refused(self):
        with tempfile.TemporaryDirectory(prefix="denials-i-") as tmp:
            copy = Path(tmp) / "denials_rules.py"
            copy.write_bytes(round3_denials.RULES.read_bytes() + b"\n# drift\n")
            saved = round3_denials.RULES
            round3_denials.RULES = copy
            try:
                self.assertTrue(round3_denials.integrity_problems())
            finally:
                round3_denials.RULES = saved


class Check(Base):
    OUTS = ("OUT_JSON", "OUT_MD", "OUT_JSON_2", "OUT_MD_2")

    def test_check_passes_on_its_own_output_and_fails_on_a_changed_figure(self):
        build(self.root)
        saved = {k: getattr(round3_denials, k) for k in self.OUTS}
        for k in self.OUTS:
            setattr(round3_denials, k, Path(self.tmp.name) / getattr(round3_denials, k).name)
        try:
            self.assertEqual(round3_denials.main(["--write"]), 0)
            self.assertEqual(round3_denials.main(["--check"]), 0)
            for k in ("OUT_JSON", "OUT_JSON_2"):
                path = getattr(round3_denials, k)
                good = path.read_text()
                data = json.loads(good)
                data["refused_calls"] += 1
                path.write_text(json.dumps(data))
                self.assertEqual(round3_denials.main(["--check"]), 1)
                path.write_text(good)
            self.assertEqual(round3_denials.main(["--check"]), 0)
        finally:
            for k, v in saved.items():
                setattr(round3_denials, k, v)


MORE = {
    # a script-form refusal worked around, an `other` refusal, and a project-log write worked around by a heredoc
    ("toy", "control", "m-c", "1"): ([
        ("user", "skip"),
        ("assistant", "", [bash("python3 _system/stage00_register.py finalize --project p --model m 2>&1 | tee out.json",
                                D, True),
                           bash("python3 _system/stage00_register.py finalize --project p --model m"),
                           bash("ls /somewhere", D, True), bash("pwd")]),
        ("assistant", "", [edit(LOG, D, True),
                           bash("python3 - <<'PY'\nopen('projects/p/HISTORY.md', 'a').write('entry')\nPY")]),
        ("assistant", "Stage 01 complete.", [])], "answered"),
}


class MoreReading(Base):
    def test_script_form_other_and_a_log_work_around(self):
        takes = dict(TAKES)
        takes.update(MORE)
        build(self.root, takes=takes)
        c = self.calls(round3_denials.derive())[("toy", "control", "m-c", "1")]
        self.assertEqual([(x["kind"], x["next"]) for x in c],
                         [("script-form", "worked-around"), ("other", "skipped"), ("project-log-write", "worked-around")])

    def test_the_log_work_around_is_guarded(self):
        takes = dict(TAKES)
        takes.update(MORE)
        build(self.root, takes=takes)
        saved = denials_rules.writes_project_log
        denials_rules.writes_project_log = lambda use: False
        try:
            c = self.calls(round3_denials.derive())[("toy", "control", "m-c", "1")]
            self.assertIsNone(c[2]["worked_around_by"])
            self.assertEqual(c[2]["next"], "skipped")  # the heredoc still follows it in the same turn
        finally:
            denials_rules.writes_project_log = saved

    def test_the_result_md_parse_reads_only_the_rounds_own_sections(self):
        # A quoted heredoc inside the denials list carries a '## ' line; an earlier-round table follows.
        lines = []
        for key, (turns, _label) in sorted(TAKES.items()):
            task, half, model, n = key
            k = sum(1 for t in turns if t[0] == "assistant" for c in t[2] if D in c[2])
            lines.append(f"- `{task}`/{half}/`{model}`/take {n}: " + (f"{k} denied call(s): `cat << 'EOF'" if k else "no denial"))
            if k:
                lines += ["", "## 2026-09-22 — 01_prepare_samplesheets — samplesheets emitted", "EOF`"]
        tail = ("\n## The earlier round, beside — never joined\n\n| task | half | model | held | recorded mode |\n"
                "|---|---|---|---|---|\n| `toy` | positive | `m-a` | 0 of 3 | auto |\n")
        build(self.root, md_lines=lines, md_tail=tail)
        data = round3_denials.derive()
        self.assertEqual(data["refused_calls"], 4)


class MoreRefusals(Base):
    def test_a_published_hash_with_no_transcript_stops_the_run(self):
        build(self.root)
        (self.root / "transcripts" / "toy" / "positive" / "m-a" / "1" / "transcript.jsonl").unlink()
        with self.assertRaises(SystemExit):
            round3_denials.derive()

    def test_a_reading_that_differs_from_round_3s_reader_stops_the_run(self):
        build(self.root)
        saved = denials_rules.denied
        denials_rules.denied = lambda use: saved(use) or (use.get("input") or {}).get("command") == "ls"
        try:
            with self.assertRaises(SystemExit):
                round3_denials.derive()
        finally:
            denials_rules.denied = saved

    def test_a_changed_prereg_is_refused(self):
        with tempfile.TemporaryDirectory(prefix="denials-p-") as tmp:
            copy = Path(tmp) / "PREREG-DENIALS.md"
            copy.write_text(round3_denials.PREREG.read_text() + "\nan edit\n")
            saved = round3_denials.PREREG
            round3_denials.PREREG = copy
            try:
                self.assertTrue(any("PREREG-DENIALS.sha256 records" in p for p in round3_denials.integrity_problems()))
            finally:
                round3_denials.PREREG = saved

    def test_a_refusal_sentence_that_differs_from_round_3s_is_refused(self):
        saved = denials_rules.DENIAL_SENTENCE
        denials_rules.DENIAL_SENTENCE = "Some other sentence"
        try:
            self.assertTrue(any("refusal sentence" in p for p in round3_denials.integrity_problems()))
        finally:
            denials_rules.DENIAL_SENTENCE = saved

    def test_a_reader_constant_that_drifts_is_refused(self):
        saved = round3_denials.RULES_2_SHA256
        round3_denials.RULES_2_SHA256 = "0" * 64
        try:
            self.assertTrue(round3_denials.integrity_problems())
        finally:
            round3_denials.RULES_2_SHA256 = saved


class Amendment2(Base):
    def test_status_echo_retried_dropped_and_the_log_reading(self):
        build(self.root)
        data = round3_denials.derive2()
        rows = {(t["task"], t["half"], t["model"], t["take"]): t for t in data["takes"]}
        a1 = rows[("toy", "positive", "m-a", "1")]["calls"][0]
        self.assertEqual((a1["kind_2"], a1["next_2"]), ("status-echo", "worked-around"))
        self.assertEqual(a1["dropped_in_the_admitted_retry"], ['echo "EXIT=$?"'])
        a2 = rows[("toy", "positive", "m-a", "2")]
        self.assertEqual([c["next_2"] for c in a2["calls"]], ["retried", "stopped"])
        self.assertEqual(a2["project_log"], {"refused_log_writes": 2, "log_written_later": False,
                                             "last_refused_attempt_ended_the_turn": True})
        b1 = rows[("toy", "control", "m-b", "1")]["calls"][0]
        self.assertEqual((b1["kind"], b1["kind_2"], b1["next_2"]), ("cd-into-run", "status-echo", "skipped"))
        self.assertEqual(data["project_log_refusals"]["takes_whose_log_was_never_written"], 1)
        self.assertEqual(data["by_harness_version"], {"2.1.267 (Claude Code)": {"takes": 4, "refused_calls": 4}})

    def test_the_cross_tab_counts_every_bash_call(self):
        build(self.root)
        cross = round3_denials.derive2()["all_bash_calls_cross_tab"]
        self.assertEqual(sum(r["admitted"] + r["refused"] for r in cross.values()), 6)  # every Bash call in TAKES
        self.assertEqual(cross["cd=yes status-echo=yes other-echo=no"], {"admitted": 0, "refused": 1})

    def test_the_sweep_finds_a_refusal_worded_another_way(self):
        takes = dict(TAKES)
        takes[("toy", "control", "m-d", "1")] = ([("user", "05"), ("assistant", "", [
            bash("python3 x.py", "This command requires approval before it can run", True)])], "answered")
        build(self.root, takes=takes)
        hits = round3_denials.derive2()["refusal_like_results_without_the_sentence"]
        self.assertEqual([h["take"] for h in hits], ["toy/control/m-d/1"])

    def test_the_definitions_are_printed_verbatim(self):
        build(self.root)
        md = round3_denials.render2(round3_denials.derive2())
        self.assertIn(round3_denials.prereg_section(round3_denials.PREREG, "## Definitions"), md)


if __name__ == "__main__":
    unittest.main()
