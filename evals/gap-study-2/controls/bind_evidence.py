#!/usr/bin/env python3
"""The draft's layer.evidence blocks, derived from the committed controls record rather than typed.

    python3 evals/gap-study-2/controls/bind_evidence.py --check
    python3 evals/gap-study-2/controls/bind_evidence.py --write

WHY (round 2, CP8, review 1 blocker 1). The draft carried the attempts of round 1's controls run, on round 1's tree,
under a source line naming round 2's record; nothing bound the two. Now `run_controls.py --write` names the tree,
the commit and the day, this file derives each task's `per_behaviour` from that record and copies its provenance
into the block, and TheLayerEvidenceIsTheControlsRecord refuses a draft whose blocks are not what this derives or
whose record ran on a tree other than the pinned system under test. Tasks whose evidence is a reviewer's ruling
rather than a controls run (confounded-design) are left as they are.

stdlib only, no model.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
REPO = STUDY.parent.parent
sys.path.insert(0, str(STUDY))
import study  # noqa: E402

RECORD = HERE / "results.json"
DRAFT = STUDY / "prereg-draft.json"
SOURCE_PREFIX = study.rel("controls", "results.json")


def derived_blocks(record: dict) -> dict[str, list[dict]]:
    """task id -> per_behaviour list, in the record's order, attempts as the command line and its exit."""
    out: dict[str, list[dict]] = {}
    for c in record["controls"]:
        out.setdefault(c["task"], []).append({
            "behaviour": c["behaviour"], "verdict": c["verdict"], "why": c["why"],
            "attempts": [{"argv": " ".join(a["argv"]), "exit": a["exit"]} for a in c["attempts"]]})
    return out


def provenance(record: dict) -> dict:
    return {k: record[k] for k in ("gars_tree_sha", "commit", "run_at")}


def bound_tasks(draft: dict) -> list[dict]:
    return [t for t in draft["tasks"]
            if str(((t.get("layer") or {}).get("evidence") or {}).get("source", "")).startswith(SOURCE_PREFIX)]


def apply(draft: dict, record: dict) -> dict:
    """The draft with every controls-sourced evidence block rewritten from the record; the rest untouched."""
    out = copy.deepcopy(draft)
    blocks = derived_blocks(record)
    for t in bound_tasks(out):
        ev = t["layer"]["evidence"]
        new = {"source": ev["source"], "per_behaviour": blocks.get(t["id"], []), "record": provenance(record)}
        for k, v in ev.items():
            if k not in new:
                new[k] = v
        t["layer"]["evidence"] = new
    return out


def problems(draft: dict, record: dict) -> list[str]:
    out = []
    pinned = (draft.get("system_under_test") or {}).get("gars_tree_sha")
    if record.get("gars_tree_sha") != pinned:
        out.append(f"the controls record ran on gars tree {str(record.get('gars_tree_sha'))[:12]}, not the pinned tree "
                   f"{str(pinned)[:12]}: the demonstration is of another system")
    want = apply(draft, record)
    for t, w in zip(draft["tasks"], want["tasks"]):
        if t.get("layer", {}).get("evidence") != w.get("layer", {}).get("evidence"):
            out.append(f"{t['id']}: the draft's layer.evidence is not what the controls record gives; run "
                       f"bind_evidence.py --write")
    if not bound_tasks(draft):
        out.append("no task's evidence names the controls record, so nothing here is bound")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Derive the draft's layer evidence from the controls record.")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--draft", type=Path, default=DRAFT)
    ap.add_argument("--record", type=Path, default=RECORD)
    args = ap.parse_args()
    draft = json.loads(args.draft.read_text())
    record = json.loads(args.record.read_text())
    if args.write:
        args.draft.write_text(json.dumps(apply(draft, record), indent=2, ensure_ascii=False) + "\n")
        print(f"wrote {len(bound_tasks(draft))} evidence block(s) from {args.record.name} "
              f"(gars tree {record['gars_tree_sha'][:12]}, commit {record['commit'][:12]}, {record['run_at']})")
        return 0
    got = problems(draft, record)
    for p in got:
        print(f"  - {p}")
    print("the draft's evidence blocks are what the controls record gives" if not got else
          f"{len(got)} problem(s): the draft's evidence is not bound to the record")
    return 1 if got else 0


if __name__ == "__main__":
    raise SystemExit(main())
