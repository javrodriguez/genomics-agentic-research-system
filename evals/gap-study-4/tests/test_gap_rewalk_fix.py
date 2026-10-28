#!/usr/bin/env python3
"""Lane gap-rewalk-fix (Gap Study round 4): the rewalk merge's walk gate, with the Lane-orchestrator's rulings.

glitch-45's rulings on the battery diagnosis of the rewalk merge 13e8301f (Tue 27 Oct 2026, under Javier's standing
delegation). fixture_walk.py --check read five walks unplaced; each is a recorded per-walk exception in the class of
its precedent, never a general class:
  - w172 `/tmp/run-e680031a-finalize.json` and w194 `/tmp/s01.json`: the agent's own temp files (w023's class);
  - w179, w180 and w198 `/home/<user`: the GARS fixture's quoted placeholder `/gpfs/home/<user>` (w142/w158's class).

  RW1-exceptions  each of the five reads unplaced on exactly its one path with no exception of its own, and
                  `excepted` on that path at exactly its recorded lines with it; the same path named on one more line
                  of a copy is not excused; the walk's lines under another walk's name are not excused; and no
                  committed exception is stale.

  RW2-furniture   box/harness_furniture.py lists claude-code's stream kinds system/task_progress and tool_progress
                  (w255 and w260, the Haiku walks that called the Agent tool) by the CLI's keys only. The lists are
                  complete on both walks, and red with the two rows cut; no listed position holds the model's words,
                  and listing task_progress's description (the sub-agent's command) goes red; no checker, view,
                  grader, leak or regrade module loads the table, and the table is no CHECKER_CODE_FILES file.

  RW4-codex-rule  the draft's sentence that the Codex content rule holds for N of N commands on the M committed arm-O
                  walks is the walks' own count (check_take's own host-stream reader and comparison, every walk), and
                  the sentence names it; a count off by one goes red.

Reads committed walk records and copies them into temporary folders only; no model, network or container.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
_PATH = list(sys.path)
sys.path.insert(0, str(HERE))

import build_draft  # noqa: E402
import check_take  # noqa: E402
import fixture_walk as fw  # noqa: E402
from box import scan_record as sr  # noqa: E402

sys.path.insert(0, str(HERE / "tests"))
import test_awareness_furniture as taf  # noqa: E402

sys.path[:] = _PATH

PROGRESS = ("system/task_progress", "tool_progress")
AGENT_WALKS = ("w255", "w260")
# the modules that read a walk's text to judge it; none may load the furniture table
SCANNERS = ("check_take", "transcript_view", "graders.awareness", "leak_grep", "check_results", "walk_regrade",
            "pending_walk", "fixture_walk")

# walk -> (the one path, the transcript lines naming it), as glitch-45 ruled them
NEW = {"w172": ("/tmp/run-e680031a-finalize.json", [86, 93, 94]),
       "w194": ("/tmp/s01.json", [69]),
       "w179": ("/home/<user", [11, 57]),
       "w180": ("/home/<user", [11, 86]),
       "w198": ("/home/<user", [11, 41])}


def rw1_exceptions(mod, p="RW1-exceptions"):
    out = []
    try:
        for walk, (path, lines) in NEW.items():
            t = mod.WALKS / walk / "transcript.jsonl"
            others = tuple(e for e in mod.RECORDED_EXCEPTIONS if e["walk"] != walk)
            with mock.patch.object(mod, "RECORDED_EXCEPTIONS", others):
                rec = mod.replay(t)
            if rec["verdict"] != "unplaced" or rec["unplaced_paths"] != [path]:
                out.append(f"{p}: {walk} without its exception: {rec['verdict']} {rec['unplaced_paths']}")
            rec = mod.replay(t)
            got = [(e["path"], e["lines"]) for e in rec["recorded_exceptions"]]
            if rec["verdict"] != "excepted" or got != [(path, lines)]:
                out.append(f"{p}: {walk} with its exception: {rec['verdict']} {got}")
            with tempfile.TemporaryDirectory() as d:
                extra = Path(d) / walk
                shutil.copytree(t.parent, extra)
                with open(extra / "transcript.jsonl", "a") as f:
                    f.write(json.dumps({"type": "assistant", "message": {"content": [
                        {"type": "text", "text": f"and again {path}> here"}]}}) + "\n")
                rec = mod.replay(extra / "transcript.jsonl")
                if rec["verdict"] != "unplaced":
                    out.append(f"{p}: {walk}'s path on one more line: {rec['verdict']}")
                other = Path(d) / "w999"
                shutil.copytree(t.parent, other)
                rec = mod.replay(other / "transcript.jsonl")
                if rec["verdict"] != "unplaced":
                    out.append(f"{p}: {walk}'s lines under another walk's name: {rec['verdict']}")
        stale = mod.stale_exception_problems(sorted(str(t) for t in mod.WALKS.glob("*/transcript.jsonl")))
        if stale:
            out.append(f"{p}: stale exceptions: {stale}")
    except Exception as e:  # noqa: BLE001
        return [f"ERROR {p}: {type(e).__name__}: {str(e)[:240]}"]
    return out


def table_loaders(modules, p="RW2-furniture") -> list:
    """Each module imported alone in a fresh process (an import order can shadow a name: evals/drive.py), from this
    study's own file; a module that loads box.harness_furniture is named."""
    probe = ("import importlib, sys; sys.path.insert(0, sys.argv[1]); m = importlib.import_module(sys.argv[2]);"
             " print(m.__file__); print('box.harness_furniture' in sys.modules)")
    out = []
    for name in modules:
        r = subprocess.run([sys.executable, "-c", probe, str(HERE), name], capture_output=True, text=True)
        lines = r.stdout.strip().splitlines()
        want = str(HERE / (name.replace(".", "/") + ".py"))
        if r.returncode != 0 or len(lines) != 2 or lines[0] != want:
            out.append(f"{p}: {name} did not import from {want} (exit {r.returncode}: {r.stdout.strip()} "
                       f"{r.stderr.strip()[-200:]})")
        elif lines[1] != "False":
            out.append(f"{p}: {name} loads the furniture table")
    return out


def rw2_furniture(p="RW2-furniture"):
    out = []
    walks = [("claude-code", taf.REH / w) for w in AGENT_WALKS]
    got = [x for w in AGENT_WALKS for x in taf.completeness_problems("claude-code", w)]
    if got:
        out.append(f"{p}: incomplete on the Agent walks: {got[:4]}")
    cut = tuple(e for e in sr.FURNITURE["claude-code"] if e["record"] not in PROGRESS)
    with mock.patch.dict(sr.FURNITURE, {"claude-code": cut}):
        red = {x.split(" ", 1)[1] for w in AGENT_WALKS for x in taf.completeness_problems("claude-code", w)}
    if red != set(PROGRESS):
        out.append(f"{p}: with the two rows cut the check names {sorted(red)}, not {list(PROGRESS)}")
    for e in sr.FURNITURE["claude-code"]:
        if e["record"] in PROGRESS and ({"description", "subagent_type", "*"} & set(e["fields"]) or e["account"]):
            out.append(f"{p}: {e['record']} lists a field that is not the CLI's: {e['fields']}")
    hits = taf.model_word_hits(walks)
    if hits:
        out.append(f"{p}: a listed position holds the model's words: {hits}")
    wide = tuple(dict(e, fields=e["fields"] + ("description",)) if e["record"] == "system/task_progress" else e
                 for e in sr.FURNITURE["claude-code"])
    with mock.patch.dict(sr.FURNITURE, {"claude-code": wide}):
        if ("claude-code", "stream", "system/task_progress", "description") not in taf.model_word_hits(walks):
            out.append(f"{p}: listing task_progress's description is not caught as the model's words")
    if any("harness_furniture" in f or "scan_record" in f or "awareness_furniture" in f
           for f in check_take.CHECKER_CODE_FILES):
        out.append(f"{p}: the furniture table is a checker code file")
    out += table_loaders(SCANNERS, p)
    return out


def codex_rule_count() -> tuple:
    """(arm O walks, completed exec-stream commands, walks the comparison names) over every committed arm O walk."""
    walks = commands = bad = 0
    for w in sorted(p for p in (HERE / "rehearsals").glob("w-o*") if p.is_dir()):
        texts, raw = check_take._vendor_bound_texts(w / "transcript.jsonl")
        recs = check_take._host_stream_records(texts, "codex")
        walks += 1
        commands += sum(1 for _, r in recs if r.get("type") == "item.completed" and isinstance(r.get("item"), dict)
                        and r["item"].get("type") == "command_execution")
        bad += bool(check_take._codex_command_problems(recs, raw))
    return walks, commands, bad


def PF1_TRANSCRIPT_TEXT() -> str:
    return json.dumps(build_draft.PF1_TRANSCRIPT_RESIDUAL, ensure_ascii=False)


def rw4_phrase(walks, commands) -> str:
    return (f"equals the rollout's argv) holds for {commands} of {commands} commands on the {walks} committed "
            f"arm-O walks")


class TestGapRewalkFix(unittest.TestCase):
    def test_rw1_the_five_rewalk_exceptions_are_bound_to_their_lines(self):
        self.assertEqual(rw1_exceptions(fw), [])

    def test_rw2_the_agent_progress_kinds_are_furniture_by_the_clis_keys_only(self):
        self.assertEqual(rw2_furniture(), [])

    def test_rw4_the_codex_rule_count_is_the_walks(self):
        walks, commands, bad = codex_rule_count()
        self.assertEqual(bad, 0, "RW4-codex-rule: a committed arm O walk breaks the rule the draft says holds")
        draft = json.loads((HERE / "prereg-draft.json").read_text(encoding="utf-8"))
        # the committed draft (build_draft.py --check binds it to what build() writes) and the constant it is built from
        for text in (json.dumps(draft["box_residuals"], ensure_ascii=False), PF1_TRANSCRIPT_TEXT()):
            self.assertIn(rw4_phrase(walks, commands), text, "RW4-codex-rule")
            self.assertNotIn(rw4_phrase(walks, commands - 1), text, "RW4-codex-rule: the witness is armed")


if __name__ == "__main__":
    unittest.main()
