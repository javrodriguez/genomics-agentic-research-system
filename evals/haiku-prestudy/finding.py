#!/usr/bin/env python3
"""Re-derive the finding that started this study from round 2's committed transcripts and the probes.

    python3 evals/haiku-prestudy/finding.py           print the counts
    python3 evals/haiku-prestudy/finding.py --check   exit 1 unless they equal the counts verification/finding.md states

Two facts, each read from bytes rather than restated:
  1. the permission mode each of round 2's graded transcripts records, per model;
  2. on round 2's number-fidelity positive half, how many of each model's takes carry a harness denial.
And the probes in verification/probes/: the mode each ran under and how many denials each carries.

No model, no network, stdlib only.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
ROUND2 = REPO / "evals" / "gap-study-2" / "transcripts"
PROBES = HERE / "verification" / "probes"
DENIAL = "Permission for this tool use was denied"
MODE = re.compile(r'"permissionMode":\s*"([a-zA-Z]+)"')

# What verification/finding.md states. --check fails if the bytes say otherwise.
STATED = {
    "round2_transcripts_by_model_and_modes": {
        "claude-haiku-4-5-20251001": {"total": 36, "default": 34, "auto": 2},
        "claude-opus-5": {"total": 36, "default": 0, "auto": 36},
        "claude-sonnet-5": {"total": 34, "default": 0, "auto": 34},
    },
    "number_fidelity_positive_takes_with_a_denial": {
        "claude-haiku-4-5-20251001": 3, "claude-sonnet-5": 0, "claude-opus-5": 0,
    },
    "probes": {
        "claude-haiku-4-5-20251001.auto.jsonl": {"modes": ["default"], "denials": 3},
        "claude-sonnet-5.auto.jsonl": {"modes": ["auto"], "denials": 0},
        "claude-haiku-4-5-20251001.auto.allow.jsonl": {"modes": ["default"], "denials": 0},
        "claude-haiku-4-5-20251001.auto.allow-three-forms.jsonl": {"modes": ["default"], "denials": 0},
    },
    # verification/probes/forms/: the nine command forms round 2's Sonnet and Opus used before the probe, one
    # session per form, first under Bash(python3:*) alone and then with Bash(echo:*) added; and all nine in one
    # session under Bash(python3:*) alone, where the first denial ended the run.
    "forms_denied": {
        "Bash(python3:*)": [1],
        "Bash(python3:*) Bash(echo:*)": [],
    },
    "forms_run": 9,
    "all_nine_in_one_session_denied": True,
}


def mode_of(text: str) -> str:
    """A transcript's mode: `default` if any record says default, else `auto` if any says auto, else `none`."""
    modes = set(MODE.findall(text))
    return "default" if "default" in modes else "auto" if "auto" in modes else "none"


def derive() -> dict:
    by_model: dict[str, dict] = {}
    for t in sorted(ROUND2.glob("*/*/*/*/transcript.jsonl")):
        model = t.parts[-3]
        m = by_model.setdefault(model, {"total": 0, "default": 0, "auto": 0})
        m["total"] += 1
        mode = mode_of(t.read_text(errors="replace"))
        m[mode] = m.get(mode, 0) + 1
    denials = {}
    for d in sorted((ROUND2 / "number-fidelity" / "positive").iterdir()):
        denials[d.name] = sum(1 for t in d.glob("*/transcript.jsonl") if DENIAL in t.read_text(errors="replace"))
    probes = {}
    for p in sorted(PROBES.glob("*.jsonl")):
        text = p.read_text(errors="replace")
        probes[p.name] = {"modes": sorted(set(MODE.findall(text))), "denials": text.count(DENIAL)}
    forms = PROBES / "forms"
    tags = {"bashpython3": "Bash(python3:*)", "bashpython3-bashecho": "Bash(python3:*) Bash(echo:*)"}
    denied = {v: [] for v in tags.values()}
    seen = set()
    for p in sorted(forms.glob("form*.jsonl")):
        n, tag = p.name.split(".")[0][4:], p.name.split(".")[1]
        seen.add(int(n))
        if DENIAL in p.read_text(errors="replace"):
            denied[tags[tag]].append(int(n))
    one = forms / "all-nine-in-one-session.bashpython3.jsonl"
    return {"round2_transcripts_by_model_and_modes": by_model,
            "number_fidelity_positive_takes_with_a_denial": denials, "probes": probes,
            "forms_denied": {k: sorted(v) for k, v in denied.items()}, "forms_run": len(seen),
            "all_nine_in_one_session_denied": DENIAL in one.read_text(errors="replace")}


def main() -> int:
    got = derive()
    print(json.dumps(got, indent=2))
    if "--check" in sys.argv[1:]:
        if got != STATED:
            print("FAIL the transcripts and probes do not say what verification/finding.md states")
            return 1
        print("ok: the finding re-derives from the bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
