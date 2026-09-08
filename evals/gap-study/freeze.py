#!/usr/bin/env python3
"""Turn the draft into the frozen pre-registration, once, and fill every pin as it goes.

    python3 evals/gap-study/freeze.py --review-commit <sha>          preview
    python3 evals/gap-study/freeze.py --review-commit <sha> --write  write prereg.json

THE FREEZE IS THE STUDY'S ONE IRREVERSIBLE STEP. After it, the design is read-only to the run and
every number is graded against it. So this file does three things and refuses to do them twice.

  it fills every pin      each grader, fixture generator, case suite and shared reader gets its
                          git blob sha AND its sha256 recorded, so check_results.py can prove
                          afterwards that none of them moved
  it fixes the take order one permutation per axis over every (task, half, model, take), seeded by
                          the sha of the PRE-FREEZE REVIEW COMMIT
  it refuses to re-run    if prereg.json exists, this exits rather than overwriting. A study whose
                          pre-registration can be re-frozen has none.

WHY THE SEED IS THE REVIEW COMMIT AND NOT ANYTHING ELSE. The order in which cells are driven could
matter -- a model's later takes run against a warmer cache, a rate limit lands where it lands. If
the run chose that order it could choose one that suited it. The seed is a sha that did not exist
until an independent reviewer had already read the design and committed its report, so the order
cannot have been picked to suit a result. Anyone can recompute it: `prereg.py --order <sha>`.

THE REVIEW MUST ALREADY BE COMMITTED. This file checks that the sha it is handed is a real commit
that touches the verification directory, and refuses otherwise. A seed that names nothing is a seed
the run could have invented.

No model, no network, stdlib only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))

import prereg  # noqa: E402

DRAFT = HERE / "prereg-draft.json"
FROZEN = HERE / "prereg.json"

# Everything the frozen file must be able to prove did not move afterwards.
PINNED = [
    "evals/gap-study/graders/labels.py",
    "evals/gap-study/graders/template_adherence.py",
    "evals/gap-study/graders/precondition_refusal.py",
    "evals/gap-study/graders/number_fidelity.py",
    "evals/gap-study/graders/scope_read.py",
    "evals/gap-study/graders/plan_gate.py",
    "evals/gap-study/fixtures/gen_source.py",
    "evals/gap-study/fixtures/gen_project.py",
    "evals/gap-study/fixtures/copy_project.py",
    "evals/gap-study/fixtures/check_fixture.py",
    "evals/gap-study/fixtures/symbol_rulings.json",
    "evals/gap-study/contract_quotes.json",
    "evals/gap-study/controls/results.json",
    "evals/gap-study/run.py",
    "evals/gap-study/analyse.py",
    "evals/gap-study/check_take.py",
    "evals/gap-study/drive.py",
    "evals/gap-study/lint_language.py",
    # the first study's shared readers, imported rather than copied
    "evals/transcript.py",
    "evals/stated_count.py",
]


def git(*args: str) -> tuple[int, str]:
    out = subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True)
    return out.returncode, out.stdout.strip()


def pin(path: str) -> dict:
    f = REPO / path
    if not f.is_file():
        return {"path": path, "missing": True}
    code, blob = git("rev-parse", f"HEAD:{path}")
    return {
        "path": path,
        "git_blob_sha": blob if code == 0 else None,
        "sha256": hashlib.sha256(f.read_bytes()).hexdigest(),
        "uncommitted": code != 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Freeze the pre-registration, once.")
    ap.add_argument("--review-commit", required=True,
                    help="the sha of the committed pre-freeze review; it seeds the take order")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    if FROZEN.is_file():
        print(f"refusing: {FROZEN.name} already exists. The freeze happens once — a study whose "
              f"pre-registration can be re-frozen has none.")
        return 2

    code, _ = git("cat-file", "-e", f"{args.review_commit}^{{commit}}")
    if code != 0:
        print(f"refusing: {args.review_commit} is not a commit in this repository. The take order "
              f"is seeded by the review commit precisely so the run cannot have chosen it.")
        return 2
    code, touched = git("show", "--name-only", "--format=", args.review_commit)
    if "evals/gap-study/verification" not in touched:
        print(f"refusing: {args.review_commit[:12]} does not touch "
              f"evals/gap-study/verification/. The seed must name the commit that landed the "
              f"pre-freeze review, not some other commit.\nIt touched:\n{touched[:400]}")
        return 2

    d = json.loads(DRAFT.read_text())
    reviewed_sha256 = hashlib.sha256(DRAFT.read_bytes()).hexdigest()

    d["status"] = "FROZEN. Read-only to the run. A later change is published as `amended`, with " \
                  "before and after and both regrades side by side, never corrected in place."
    d["frozen_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    _, head = git("rev-parse", "HEAD")
    d["frozen_at_commit_parent"] = head
    d["draft_sha256_at_freeze"] = reviewed_sha256
    d["pre_freeze_review_commit"] = args.review_commit
    d["take_order_seed"] = args.review_commit

    pins = [pin(p) for p in PINNED]
    d["pinned_files"] = pins

    # THE PER-TASK PINS, filled here rather than left null beside a global list.
    #
    # Each task names its grader and its case suite by path with both shas null and a note saying
    # "pinned at the freeze". If the freeze fills only the global list, those nulls survive into the
    # frozen file and a reader cannot tell a null-to-fill from a null-by-design.
    for t in d["tasks"]:
        for key in ("grader", "grader_cases"):
            spec = t.get(key) or {}
            path = spec.get("path")
            if not path:
                continue
            got = pin(path)
            if got.get("missing"):
                spec["missing_at_freeze"] = True
                spec["note"] = (f"{path} does not exist at the freeze. Its cell publishes "
                                f"`not run — no grader module` rather than a number.")
                continue
            spec["git_blob_sha"] = got["git_blob_sha"]
            spec["sha256"] = got["sha256"]
            spec.pop("note", None)

    # THE FIXTURE PINS. A fixture is not one file in git, so it is not pinned like one.
    #
    #   generated    pinned by its GENERATOR (already in pinned_files) plus its seed and variant,
    #                and by the content hash the generator computes over the bytes it writes. That
    #                hash is filled here from `--manifest-only`, which runs the generator without
    #                writing anything.
    #   copied-tree  pinned by tree_sha256_name_invariant, computed over the copy with the take's
    #                project name substituted back to a placeholder.
    #   project      built by the real stage 00 from a pinned generator and seed, and verified on
    #                every build against the branch it must reach.
    #
    # In each case git_blob_sha stays null BY DESIGN: there is no blob. Recording that here is the
    # difference between a null a reader can account for and one they have to guess about.
    for t in d["tasks"]:
        for half in ("positive", "control"):
            fx = (t.get(half) or {}).get("fixture")
            if not isinstance(fx, dict):
                continue
            kind = fx.get("kind")
            fx["git_blob_sha_note"] = ("null by design: a fixture is not a file in git. See "
                                       "pinned_by below.")
            if kind == "generated":
                gen = REPO / fx["generator"]
                out = subprocess.run(
                    [sys.executable, str(gen), "--variant", fx["variant"],
                     "--seed", str(fx["seed"]), "--manifest-only"],
                    capture_output=True, text=True)
                try:
                    man = json.loads(out.stdout)
                    fx["sha256"] = man["fixture_sha256"]
                    fx["pinned_by"] = "the generator's blob sha in pinned_files, plus variant, "\
                                      "seed, and this content hash over the bytes it writes"
                except (json.JSONDecodeError, KeyError):
                    fx["pinned_by"] = "UNPINNED: the generator would not report a manifest"
            elif kind == "copied-tree":
                fx["pinned_by"] = ("tree_sha256_name_invariant, computed over the copy with the "
                                   "take's project name substituted back to a placeholder")
                fx.setdefault("sha256", None)
                fx["sha256_note"] = "null by design: the pin is the tree hash, not a file hash"
            elif kind == "project":
                fx["pinned_by"] = ("the generator's blob sha in pinned_files, plus seed, and the "
                                   "stage-01 exit code the generator verifies on every build")
                fx.setdefault("sha256", None)
                fx["sha256_note"] = ("null by design: the fixture is a project tree built by the "
                                     "real stage 00, not a file")

    # EVERY REMAINING NULL, CLASSIFIED. A frozen file full of nulls that nobody has accounted for
    # is a file whose reader has to guess which were intended.
    remaining = []

    def walk(node, path=""):
        if isinstance(node, dict):
            for k, v in node.items():
                if v is None:
                    remaining.append(f"{path}.{k}".lstrip("."))
                else:
                    walk(v, f"{path}.{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")

    walk(d)
    BY_DESIGN = {
        "marker": "a turn with no wait point to check; the driver checks only that the turn "
                  "produced text",
        "not_run_reason": "a model that runs has no reason not to",
        "error": "a control attempt that was not expected to error",
        "take_order_seed": "set below, from the review commit",
        "git_blob_sha": "a fixture is not a file in git; see the fixture's pinned_by",
        "sha256": "for a copied-tree or project fixture the pin is the tree hash or the verified "
                  "exit code; see the fixture's pinned_by",
    }
    d["nulls_at_freeze"] = {
        "count": len(remaining),
        "by_design": {k: v for k, v in BY_DESIGN.items()
                      if any(r.endswith("." + k) or r == k for r in remaining)},
        "unaccounted": sorted(r for r in remaining
                              if r.split(".")[-1] not in BY_DESIGN),
        "note": "Every null left in the frozen file is either listed as by-design above or named "
                "as unaccounted. A freeze with unaccounted nulls is refused.",
    }
    _, gars_tree = git("rev-parse", "HEAD:gars")
    d["system_under_test"]["gars_tree_sha_at_freeze"] = gars_tree
    ver = subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout.strip()
    d["harness"]["claude_version_at_freeze"] = ver

    order = prereg.order(args.review_commit)
    d["take_order"] = {axis: [list(c) for c in cells] for axis, cells in order.items()}

    missing = [p["path"] for p in pins if p.get("missing")]
    uncommitted = [p["path"] for p in pins if p.get("uncommitted")]

    print(f"draft sha256        {reviewed_sha256}")
    print(f"review commit       {args.review_commit[:12]}")
    print(f"gars tree at freeze {gars_tree[:12]}"
          f"  {'(unchanged since the first study)' if gars_tree == d['system_under_test']['gars_tree_sha'] else '(CHANGED — every row must say so)'}")
    print(f"harness             {ver}")
    print(f"pinned files        {len(pins)}")
    print(f"take order          {sum(len(v) for v in order.values())} cells "
          f"({', '.join(f'{k}: {len(v)}' for k, v in order.items())})")
    if missing:
        print(f"\nMISSING, so nothing can pin them: {missing}")
        return 1
    if uncommitted:
        print(f"\nNOT COMMITTED, so their blob sha is unknown: {uncommitted}")
        print("Commit them first. A pin to an uncommitted file proves nothing.")
        return 1

    nulls = d["nulls_at_freeze"]
    print(f"nulls remaining     {nulls['count']}  "
          f"({len(nulls['by_design'])} class(es) by design, "
          f"{len(nulls['unaccounted'])} unaccounted)")
    for k, why in nulls["by_design"].items():
        print(f"                    {k}: {why}")
    if nulls["unaccounted"]:
        print("\nUNACCOUNTED NULLS, so the freeze is refused:")
        for r in nulls["unaccounted"][:20]:
            print(f"  - {r}")
        print("Either fill them or record why they are null by design. A reader of the frozen "
              "file cannot tell a null-to-fill from a null-by-design, and after the freeze "
              "nobody can ask.")
        return 1

    if not args.write:
        print("\npreview only. Re-run with --write to freeze.")
        return 0

    FROZEN.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
    print(f"\nfrozen: {FROZEN.relative_to(REPO)}")
    print("The draft is kept beside it. The freeze commit body carries the diff between them, or "
          "the word `none`.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
