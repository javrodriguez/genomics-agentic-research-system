#!/usr/bin/env python3
"""Every registered walk held to the draft's pins: the agent version, the image ids and the system under test.

    python3 evals/gap-study-4/walk_pins.py --check      exit 1 on any walk off its pins, each named

Pre-freeze review 1, m6 (the lane orchestrator's fold plan of Sat 24 Oct 2026, lane L1). All 225 walks matched
version_pins, the image ids and the tree when the review read them, but no gate compared a walk with them, so a walk
run on another CLI, image or gars tree would still have been read as a walk of this design. This gate reads, for
every walk rehearsals/register.json lists, the walk's own committed records (the folder on disk is HEAD's:
walk_register.py --check binds the two) and compares:

  - driver-ledger.json: agent.harness is the harness the draft's rows give the walk's arm and model; agent.version and
    claude_version are that model's version_pins agent_version; model_requested is the register's model; and
    gars_tree_sha is the gars tree of variants.PINNED_TREE (git rev-parse <PINNED_TREE>:gars), the tree every take is
    archived from;
  - launch.json: exactly one take-create, proxy-create and sidecar-create step, each creating its container from the
    image id of its lock in the draft's image_locks (the harness's take image, the egress image, the sidecar image).

Every pin is read from the design files, never typed here. The gate names each walk it reads and prints the count;
a register that lists no walk is said out loud, never read as a pass about any walk.

No model, no network, no container; stdlib and git only. Read-only.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import walk_register  # noqa: E402

IMAGE_ID = re.compile(r"sha256:[0-9a-f]{64}")
# Each launch step that creates a container, and which lock's image it must create from: the walk's harness's take
# image ("take"), or the named shared image (box/image_lock.SIDECAR_IMAGE and EGRESS_IMAGE).
CREATE_STEPS = {"take-create": "take", "proxy-create": "egress", "sidecar-create": "sidecar"}


class PinsUnreadable(ValueError):
    pass


def design_pins(study_dir: Path = HERE) -> dict:
    """What a walk is held to, from the draft and the pinned commit: {"versions": {(harness, model): version},
    "harness": {(arm, model): harness}, "images": {"take": {harness: id}, "egress": id, "sidecar": id}, "gars_tree"}."""
    study_dir = Path(study_dir)
    draft = json.loads((study_dir / "prereg-draft.json").read_text())
    import variants
    from box import image_lock
    harness = {}
    for row in draft["rows"]:
        key = (row["arm"], row["model"])
        if harness.setdefault(key, row["agent"]["harness"]) != row["agent"]["harness"]:
            raise PinsUnreadable(f"arm {key[0]}, {key[1]}: the draft's rows give two harnesses")
    versions = {(h, m): pin["agent_version"] for h, per in draft["version_pins"].items() for m, pin in per.items()}
    by_image = {e["lock"]["image"]: e["lock"]["image_id"] for e in draft["image_locks"]}
    import build_draft
    take = {h: by_image[img] for h, img in zip(build_draft.HARNESSES.values(), image_lock.TAKE_IMAGES)}
    images = {"take": take, "egress": by_image[image_lock.EGRESS_IMAGE], "sidecar": by_image[image_lock.SIDECAR_IMAGE]}
    got = subprocess.run(["git", "-C", str(REPO), "rev-parse", f"{variants.PINNED_TREE}:gars"], capture_output=True,
                         text=True)
    tree = got.stdout.strip()
    if got.returncode != 0 or not re.fullmatch(r"[0-9a-f]{40}", tree):
        raise PinsUnreadable(f"the gars tree of the pinned commit {variants.PINNED_TREE[:12]} cannot be read")
    return {"versions": versions, "harness": harness, "images": images, "gars_tree": tree}


def walk_problems(entry: dict, folder: Path, pins: dict) -> list[str]:
    """Why one registered walk is off its pins ([] when it holds)."""
    out = []
    try:
        ledger = json.loads((folder / "driver-ledger.json").read_text())
        launch = json.loads((folder / "launch.json").read_text())
    except (OSError, ValueError) as e:
        return [f"its driver-ledger.json or launch.json cannot be read ({type(e).__name__})"]
    arm, model = entry["arm"], entry["model"]
    harness = pins["harness"].get((arm, model))
    if harness is None:
        return [f"arm {arm}, {model} is no row of the draft"]
    agent = ledger.get("agent") if isinstance(ledger.get("agent"), dict) else {}
    want = pins["versions"].get((harness, model))
    if agent.get("harness") != harness:
        out.append(f"its ledger's agent.harness is {agent.get('harness')!r}, the draft's is {harness!r}")
    if agent.get("version") != want or ledger.get("claude_version") != want:
        out.append(f"its ledger's agent version is {agent.get('version')!r} (claude_version "
                   f"{ledger.get('claude_version')!r}), the pinned is {want!r}")
    if ledger.get("model_requested") != model:
        out.append(f"its ledger requested {ledger.get('model_requested')!r}, the register names {model!r}")
    if ledger.get("gars_tree_sha") != pins["gars_tree"]:
        out.append(f"its gars tree is {ledger.get('gars_tree_sha')!r}, the pinned commit's is {pins['gars_tree']}")
    steps = launch.get("steps") if isinstance(launch.get("steps"), list) else []
    for step, which in CREATE_STEPS.items():
        found = [s for s in steps if isinstance(s, dict) and s.get("step") == step]
        if len(found) != 1:
            out.append(f"its launch holds {len(found)} {step} step(s), not exactly one")
            continue
        ids = [a for a in found[0].get("argv") or [] if isinstance(a, str) and IMAGE_ID.fullmatch(a)]
        lock = pins["images"]["take"].get(harness) if which == "take" else pins["images"][which]
        if ids != [lock]:
            out.append(f"its {step} creates from {ids!r}, not the {which} lock's {lock}")
    return out


def check(study_dir: Path = HERE, base: Path | None = None) -> tuple[list[str], int]:
    """(problems, walks read)."""
    base = walk_register.REHEARSALS if base is None else Path(base)
    pins = design_pins(study_dir)
    entries = walk_register.registered(base)
    out = []
    for e in entries:
        out += [f"walk {e['walk']!r}: {p}" for p in walk_problems(e, base / e["walk"], pins)]
    return out, len(entries)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0], allow_abbrev=False)
    ap.add_argument("--check", action="store_true", required=True)
    ap.add_argument("--base", help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    try:
        problems, n = check(base=a.base)
    except (PinsUnreadable, OSError, ValueError, KeyError) as e:
        print(f"walk_pins: FAIL the pins or the register cannot be read: {e}")
        return 1
    for p in problems:
        print(f"walk_pins: FAIL {p}")
    if n == 0:
        print("walk_pins: the register lists no walk; nothing here is evidence about any walk")
        return 0 if not problems else 1
    print(f"walk_pins: {n} registered walk(s) read; " + ("every one on the draft's version pins and image ids, its ledger "
          "naming the pinned gars tree (a walk records the pin, so this compares the pin with itself: pre-freeze review "
          "3, m9; the draft's limitation 'the gars tree of a walk')" if not problems else f"{len(problems)} problem(s)"))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
