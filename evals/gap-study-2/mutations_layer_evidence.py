"""Mutations for CP8's layer-evidence binding (review 1, blocker 1), registered by mutations.register_topic_modules."""

from __future__ import annotations

import json

from mutations import Sandbox, _edit, _prereg

CLS = "TheLayerEvidenceIsTheControlsRecord"


def _guard(s: Sandbox) -> list[str]:
    return [str(s.study / "test_harness.py"), CLS]


def m_attempt_id_in_the_draft_edited(s: Sandbox) -> tuple[int, str]:
    """A control attempt in the draft edited by hand: the draft says one command ran, the record another."""
    s.control(_guard(s))
    path = _prereg(s)
    doc = json.loads(path.read_text())
    task = next(t for t in doc["tasks"] if t["id"] == "plan-gate")
    task["layer"]["evidence"]["per_behaviour"][0]["attempts"][-1]["exit"] = 1
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    code, out = s.run_out(_guard(s))
    return Sandbox.expect(code, out, "not derived from the controls record"), f"test_harness.py {CLS} (an attempt edited)"


def m_record_from_another_tree(s: Sandbox) -> tuple[int, str]:
    """The controls record re-stamped with another gars tree: a demonstration of some other system."""
    s.control(_guard(s))
    p = s.study / "controls" / "results.json"
    rec = json.loads(p.read_text())
    rec["gars_tree_sha"] = "1" * 40
    p.write_text(json.dumps(rec, indent=2) + "\n")
    code, out = s.run_out(_guard(s))
    return Sandbox.expect(code, out, "gars_tree_sha"), f"test_harness.py {CLS} (another tree)"


def m_binding_stops_comparing_blocks(s: Sandbox) -> tuple[int, str]:
    """bind_evidence.problems no longer compares the blocks, so any typed evidence passes."""
    s.control(_guard(s))
    _edit(s.study / "controls" / "bind_evidence.py",
          '        if t.get("layer", {}).get("evidence") != w.get("layer", {}).get("evidence"):\n', "        if False:\n")
    code, out = s.run_out(_guard(s))
    return Sandbox.expect(code, out, "not what the controls record gives"), f"test_harness.py {CLS} (blocks not compared)"


MUTATIONS = [
    ("a control attempt edited in the draft", m_attempt_id_in_the_draft_edited, False),
    ("a controls record from another tree", m_record_from_another_tree, False),
    ("the evidence binding no longer comparing the blocks", m_binding_stops_comparing_blocks, False),
]
