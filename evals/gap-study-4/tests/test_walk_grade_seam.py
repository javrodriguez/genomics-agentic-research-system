#!/usr/bin/env python3
"""The walk grading seam: the REAL production grading entry on a committed-walk-shaped folder, for every task.

glitch-6b's item E (15 Oct 2026). CP6 walk w020 (Haiku, plan-gate trap w1) ran to its end and its commit failed in
grading: "TypeError: the transcript is handed over as its lines; the grader opens no file" (graders/plan_gate.py
take_events; precondition_refusal calls the same). run.grade_walk_folder (and run.grade_committed) handed the grader
the transcript's PATH, and every battery passed because the grader tests call grade() with lines directly: no test
drove the production caller into the real grader.

  E-seam   for each of the nine tasks, run.write_walk_grade (what walk_runner calls per walk: grade_walk ->
           grade_walk_folder -> run.regrade -> the task's v4 grader) on a synthetic folder shaped as a committed walk
           (driver-ledger.json, transcript.jsonl, evidence/ in endstate's closed layout): it writes grade.json, or it
           refuses for a designed reason (the grader's, the view's or the evidence reader's own error); never a
           TypeError, AttributeError, KeyError, IndexError or NameError, which are the caller and the grader
           disagreeing about the contract.
  E-take   the take road's caller (run.grade_committed) hands the grader the same: lines, never a path.
  E-vendor (review of E, MAJOR, glitch-6b 15 Oct 2026) the same entry on a Codex and a Gemini walk for every task: the
           transcript is a bound envelope (vendor_record_binding), so the graders must be handed a value that is both
           the file's lines and bound to its path (transcript_view.BoundTranscript); each vendor cell reaches its real
           grader or refuses for a designed reason, never "vendor events require a bound transcript path".
           Lane vendor-admission T1 (glitch-b5, 16 Oct 2026): grading admits a vendor walk only through a registered
           reader and an agreed native cross-check, so each vendor walk's driver ledger carries the agreed
           cross_check_status and the seam hands write_walk_grade an injected registry holding its harness (TEST
           DATA, as the TABLE entries are).

Every fixture is synthetic: no walk's transcript is read.
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

run = variants = None
UNDESIGNED = (TypeError, AttributeError, KeyError, IndexError, NameError)
MODEL = "claude-haiku-4-5-20251001"
AGENT = {"harness": "claude-code", "version": "2.1.296"}
VENDOR = {"codex": ("synthetic-codex-model", {"harness": "codex", "version": "0.162.1"}, "O"),
          "gemini": ("synthetic-gemini-model", {"harness": "gemini", "version": "0.64.0"}, "G")}
SESSION, VENDOR_ID = "study-walk-1", "vendor-1"
AGREED = {"status": "agreed", "why": None}          # drive.gemini_cross_check's and codex_cross_check's agreed shape
PROJECT = "run-0a1b2c3d"


def setUpModule():
    global run, variants
    saved = list(sys.path)
    import run
    import variants
    sys.path[:] = saved


def tasks() -> list:
    return sorted(p.stem for p in (HERE / "tasks").glob("*.json"))


def lines_of(task: str, cell: dict) -> list:
    steps = variants.operator_steps(task, cell["half"], cell["wording"], pressure=cell["pressure"])
    out = []
    for k, step in enumerate(steps, 1):
        text = str(step.get("line", f"line {k}")).replace("{project}", PROJECT).replace("{source}", "data/src")
        out.append(json.dumps({"type": "user", "message": {"role": "user", "content": text}}))
        out.append(json.dumps({"type": "assistant", "message": {"model": MODEL, "content": [
            {"type": "text", "text": f"Synthetic reply {k}."}]}}))
    return out


def vendor_records(folder: Path, harness: str, sent: list) -> dict:
    """The smallest honest bound vendor record (as tests/test_vendor_record_binding.py builds it): one native stream
    per turn, an envelope line per turn in transcript.jsonl, bound by sha256 to its stream and to the ledger's turns."""
    envelopes, streams = [], []
    for k, line in enumerate(sent, 1):
        native = ([{"type": "thread.started", "thread_id": VENDOR_ID},
                   {"type": "item.completed", "item": {"id": f"a{k}", "type": "agent_message",
                                                       "text": f"Synthetic reply {k}."}}]
                  if harness == "codex" else
                  [{"type": "init", "session_id": VENDOR_ID, "model": VENDOR[harness][0]},
                   {"type": "message", "role": "user", "content": line},
                   {"type": "message", "role": "assistant", "content": f"Synthetic reply {k}."}])
        raw = ("\n".join(json.dumps(r) for r in native) + "\n").encode()
        name = f"turn-{k}.jsonl"
        (folder / name).write_bytes(raw)
        streams.append(name)
        envelopes.append({"type": "harness-turn", "harness": harness, "session_id": SESSION,
                          "vendor_session_id": VENDOR_ID, "n": k, "sent": line, "stream": name,
                          "sha256": hashlib.sha256(raw).hexdigest()})
    (folder / "transcript.jsonl").write_text("".join(json.dumps(e) + "\n" for e in envelopes))
    return {"session_id": SESSION, "turns": [{"n": k, "sent": line} for k, line in enumerate(sent, 1)],
            "streams": streams}


def walk_folder(root: Path, task: str, cell: dict, harness: str = "claude-code") -> tuple[dict, Path]:
    """A committed-walk-shaped folder for one cell of `task`: driver ledger, transcript and evidence."""
    model, agent, arm = (MODEL, AGENT, "A") if harness == "claude-code" else VENDOR[harness]
    folder = root / f"{task}-{harness}"
    ev = folder / "evidence"
    (ev / "snapshots").mkdir(parents=True)
    (ev / "blobs").mkdir()
    lines = lines_of(task, cell)
    n = len(lines) // 2
    extra = {}
    if harness == "claude-code":
        (folder / "transcript.jsonl").write_text("\n".join(lines) + "\n")
    else:
        extra = vendor_records(folder, harness, [json.loads(x)["message"]["content"] for x in lines[::2]])
        extra["cross_check_status"] = dict(AGREED)          # lane vendor-admission T1: graded only cross-checked
    ledger = [{"kind": "take", "model": model, "agent": agent, "run_tree": "", "home": None}]
    t = 1000.0
    health = [{"kind": "watcher-start", "at": t - 1}]        # a clean watcher: paused at each snapshot, re-armed after
    for k in range(1, n + 1):
        ledger.append({"kind": "turn", "n": k, "started_at": t + 1, "ended_at": t + 2})
        health += [{"kind": "watcher-stop", "at": t + 0.5, "exit_code": 0, "ignored_newline_paths": 0}, {"kind": "watcher-start", "at": t + 0.7},
                   {"kind": "watcher-stop", "at": t + 2.5, "exit_code": 0, "ignored_newline_paths": 0}, {"kind": "watcher-start", "at": t + 2.7}]
        for label, at in ((f"pre-{k}", t + 0.5), (f"post-{k}", t + 2.5)):
            (ev / "snapshots" / f"{label}.json").write_text(json.dumps({"label": label, "taken_at": at,
                                                                        "entries": {}}))
        t += 10
    (ev / "ledger.jsonl").write_text("".join(json.dumps(r) + "\n" for r in ledger))
    (ev / "access.jsonl").write_text("")
    health.append({"kind": "watcher-stop", "at": t, "exit_code": 0, "ignored_newline_paths": 0})        # the final stop, after post-N
    (ev / "health.jsonl").write_text("".join(json.dumps(r) + "\n" for r in health))
    (ev / "watched.json").write_text(json.dumps({"paths": ["synthetic/consequential.txt"]}))
    (folder / "driver-ledger.json").write_text(json.dumps(dict({
        "kind": "take", "task": task, "half": cell["half"], "wording": cell["wording"], "pressure": cell["pressure"],
        "repeat": cell["repeat"], "arm": arm, "model_requested": model, "agent": agent, "project": PROJECT,
        "first_agent_turn": True, "outcome": "complete"}, **extra)))
    entry = {"walk": f"w-{task}", "task": task, "half": cell["half"], "wording": cell["wording"], "arm": arm,
             "model": model}
    return entry, folder


def registered_reader(raw, ordinal):
    """TEST DATA: the injected registry's reader (lane vendor-admission T1); grading admits on its presence and never
    calls it."""
    raise AssertionError("grading never calls the native reader")


def seam(task: str, root: Path, run_mod=None, harness: str = "claude-code") -> tuple[str, str]:
    """(outcome, detail) of the production grading entry on one task's synthetic walk: "graded", "refused" (a
    designed refusal inside the grader), "UNDESIGNED", or "NOT REACHED" (refused before the task's grader was entered:
    the seam would be vacuous)."""
    run_mod = run if run_mod is None else run_mod
    cell = variants.cells(task)[0]
    entry, folder = walk_folder(root, task, cell, harness)
    reached = []
    real = run_mod.grader_for

    def grader_for(name):
        mod = real(name)
        inner = mod.grade

        def grade(*a, **kw):
            reached.append(name)
            return inner(*a, **kw)
        mod.grade = grade
        return mod
    try:
        with mock.patch.object(run_mod, "grader_for", grader_for):
            path = run_mod.write_walk_grade(entry, folder, **({} if harness == "claude-code" else
                                                                {"readers": {harness: registered_reader}}))
    except UNDESIGNED as e:
        return "UNDESIGNED", f"{type(e).__name__}: {e}"
    except Exception as e:  # noqa: BLE001 - a designed refusal of the grader, the view or the evidence reader
        return ("refused" if reached else "NOT REACHED"), f"{type(e).__name__}: {str(e)[:120]}"
    doc = json.loads(path.read_bytes())
    return ("graded" if doc.get("graded") is True else "refused"), str(doc.get("grade", doc.get("why")))[:120]


def seam_problems(run_mod=None, harnesses=("claude-code",)) -> tuple[list, dict]:
    out, seen = [], {}
    with tempfile.TemporaryDirectory() as tmp:
        for harness in harnesses:
            for task in tasks():
                got = seam(task, Path(tmp), run_mod, harness)
                seen[(harness, task)] = got
                if got[0] in ("UNDESIGNED", "NOT REACHED") or "require a bound transcript path" in got[1]:
                    out.append(f"E-seam {harness} {task}: {got[0]}: {got[1]}")
    return out, seen


class TheGradingSeam(unittest.TestCase):
    def test_e_seam_every_task_grades_or_refuses_by_design(self):
        self.assertEqual(len(tasks()), 9, f"E-seam: the tasks are {tasks()}")
        problems, seen = seam_problems()
        for (_, task), (outcome, detail) in seen.items():
            print(f"\nSEAM {task}: {outcome} ({detail})", end=" ", file=sys.stderr, flush=True)
        self.assertEqual(problems, [])

    def test_e_vendor_every_task_reaches_its_grader_on_a_bound_transcript(self):
        # TEST DATA: harness_bookkeeping.TABLE holds claude-code only on this tree, so production Evidence.load refuses
        # every vendor take before any grader ("has no bookkeeping entry"; named in the item-E fold's report). These
        # synthetic entries let the seam reach the graders; they are not the vendors' bookkeeping.
        import harness_bookkeeping as hb
        fake = {h: hb.Entry(home_paths=(f"synthetic-{h}-home/*",), run_tree_paths=(), grounds=("TEST DATA",),
                            not_excluded=()) for h in VENDOR}
        with mock.patch.dict(hb.TABLE, fake):
            problems, seen = seam_problems(harnesses=("codex", "gemini"))
        for (harness, task), (outcome, detail) in seen.items():
            print(f"\nSEAM {harness} {task}: {outcome} ({detail})", end=" ", file=sys.stderr, flush=True)
        self.assertEqual(problems, [])

    def test_e_vendor_on_the_real_table_needs_no_synthetic_entries(self):
        # B21-5 (glitch-26, lane vendor-b21, Tue 20 Oct 2026): codex and gemini are in harness_bookkeeping.TABLE, so
        # the same seam reaches every vendor cell's grader with no patch; the patched test above stays as it is.
        problems, seen = seam_problems(harnesses=("codex", "gemini"))
        for (harness, task), (outcome, detail) in seen.items():
            print(f"\nSEAM-REAL {harness} {task}: {outcome} ({detail})", end=" ", file=sys.stderr, flush=True)
        self.assertEqual(problems, [])
        self.assertEqual([k for k, (_, detail) in seen.items() if "has no bookkeeping entry" in detail], [])
        self.assertEqual(len(seen), 18)

    def test_e_take_the_take_road_hands_lines(self):
        handed = []

        def spy(name, row, spec, transcript, evidence):
            handed.append(transcript)
            return {"label": "synthetic"}, str(HERE / "graders" / "plan_gate.py")
        with tempfile.TemporaryDirectory() as tmp:
            entry, folder = walk_folder(Path(tmp), "plan-gate", variants.cells("plan-gate")[0])
            takes_root = (HERE / "takes").resolve()
            row = dict(run.walk_row(entry, json.loads((folder / "driver-ledger.json").read_text())),
                       record_dir="takes/s1/1", slot="s1", attempt=1)
            committed = lambda repo, *args: "" if args[0] == "status" else "takes/s1/1/transcript.jsonl"  # noqa
            with mock.patch.object(run, "regrade", spy), \
                    mock.patch.object(run, "HERE", Path(tmp)), mock.patch.object(run, "REPO", Path(tmp)), \
                    mock.patch.object(run.takes, "_git_at", committed), \
                    mock.patch.object(run.mode_binding, "TAKES_DIR", "takes"):
                dest = Path(tmp) / "takes" / "s1" / "1"
                dest.parent.mkdir(parents=True)
                folder.rename(dest)
                try:
                    run.grade_committed(row, {})
                except Exception:  # noqa: BLE001 - only what reached the grader matters here
                    pass
        del takes_root
        self.assertTrue(handed, "E-take: grade_committed never reached the grader")
        import transcript_view as tv
        self.assertTrue(all(isinstance(t, tv.BoundTranscript) and all(isinstance(x, str) for x in t) for t in handed),
                        f"E-take: the take road handed {[type(t).__name__ for t in handed]}")


if __name__ == "__main__":
    unittest.main()
