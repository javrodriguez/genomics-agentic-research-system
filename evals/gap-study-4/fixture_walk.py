#!/usr/bin/env python3
"""Does anything the agent reads name the study's checkout? Decided by code, at path boundaries.

    python3 evals/gap-study-3/fixture_walk.py --static      the static half: the fixture's own bytes and
                                                            every operator line, before any session runs
    python3 evals/gap-study-3/fixture_walk.py --replay <transcript> --task <id> --half <h>
                                                            the verdict on one recorded session
    python3 evals/gap-study-3/fixture_walk.py --check       every committed walk under walks/, re-derived

WHAT THE VERDICT IS ABOUT, AND WHAT IT IS NOT. This round's checkout holds the study: its pre-registration,
its transcripts, its graders. A session that reads a path inside that checkout has been shown the thing it
is being measured on. The verdict here is about THAT and nothing else. A session's own scratch file, written
somewhere neither the study nor the system under test owns, tells the session nothing about the study -- and
conflating the two was the failure this file was written after.

PATH BOUNDARIES, NEVER SUBSTRINGS. `/tmp/run-1/gars` is not inside `/tmp/run-11`, and a substring test says
it is. Every containment question here is answered by comparing path PARTS, on both the normalised form and
the resolved form of each path, because a symlinked temp root answers one and not the other on macOS.

WHY THIS FILE EXISTS AT ALL. Round 2's one incomplete cell -- template-adherence, control, on one model --
capped after three attempts, each refused by the take checker with `read-outside-the-checkout`. The brief
that proposed this round read that as the fixture leaking its own shape through the paths a model reads, and
the plan carried that reading forward. Reading the three refused transcripts says otherwise, and this file
re-derives that from their bytes rather than repeating it:

  * the refused path in all three is the session's own `/tmp/gars_finalize_<project>.json`, which the agent
    created by redirecting a stage-00 command's output there and then read back with `cat`;
  * template-adherence's fixture is `kind: generated` on both halves, built inside the run tree by the
    generator at take time, byte-identical across the halves, and records no path of this repository at all.

So the fixture does not name the checkout, the refusals were not about the fixture, and a re-cut of the
fixture would not have prevented any of them. `--static` proves the first of those on the bytes; `--replay`
proves the second on the three refused transcripts. What round 3 should do instead is the owner's call, and
this file takes no view on it: it reports.

No model, no network, stdlib only. Read-only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
WALKS = HERE / "walks"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "evals"))

import prereg  # noqa: E402
import round2  # noqa: E402
import study  # noqa: E402
import transcript as tx  # noqa: E402

# An absolute path as it appears in a tool call or its result. Deliberately greedy about the roots that
# matter on this machine and permissive about the tail; what makes a hit a leak is decided below, not here.
ABS_PATH = re.compile(r"(/(?:Users|home|private|var|tmp|opt|etc)/[^\s\"'`,;:)\]}>]*)")

# Roots that are the machine's, not the study's. Reading one of these tells a session nothing about the
# study, which is the only question this file answers.
SYSTEM_ROOTS = ("/usr", "/bin", "/sbin", "/opt/homebrew", "/usr/local", "/Library", "/System", "/etc",
                "/Applications")


def parts(p: str) -> tuple[str, ...]:
    """A path's parts, normalised, with no trailing empties. Comparison is by these, never by substring."""
    return tuple(x for x in PurePosixPath(os.path.normpath(p)).parts if x not in ("", "."))


def under(path: str, root: str) -> bool:
    """Is `path` at or below `root`? Answered on the normalised form AND on the resolved form.

    Both, because macOS resolves /tmp and /var to /private/tmp and /private/var: a path normalised one way
    and a root normalised the other would compare unequal while naming the same place.
    """
    for a, b in ((path, root), (os.path.realpath(path), os.path.realpath(root))):
        pa, pb = parts(a), parts(b)
        if len(pa) >= len(pb) and pa[:len(pb)] == pb:
            return True
    return False


def any_under(path: str, roots) -> bool:
    return any(under(path, r) for r in roots)


def study_roots() -> list[str]:
    """The places that hold the study. A path at or below one of these is the leak this round cares about.

    The repository's checkout, the folder holding it and its sibling worktrees, and the root above that --
    the same three round 2's checker names, taken from this file's own location rather than typed.
    """
    repo = str(REPO)
    holder = str(REPO.parent)
    above = str(REPO.parent.parent)
    return [repo, holder, above]


def paths_in(text: str) -> list[str]:
    return [m.group(1).rstrip(".,;:") for m in ABS_PATH.finditer(text or "")]


def root_pattern_problems() -> list[str]:
    """REVIEW 4, NIT 5. ABS_PATH lists its roots by hand, and a checkout under a root it does not list would
    produce a verdict that classifies no path as the study and reads clean. So the verdict checks itself:
    every study root this file derives must be a path the pattern would see."""
    out = []
    for r in study_roots():
        hits = paths_in(f" {r} ")
        if not hits or not under(hits[0], r):
            out.append(f"the study root {r} is not matched by the absolute-path pattern, so a session naming it "
                       f"would not be seen; this verdict cannot grade anything from here")
    return out


# The harness's own background-task output file. Claude Code names this path back to the agent when a
# command is run with run_in_background, so merely backgrounding a command puts an absolute path outside
# the run tree into the transcript. It is the harness describing itself, exactly as the pre-study's voided
# leak word was. Matched on the path's own leading segments, never by substring.
HARNESS_TASK_OUTPUT = re.compile(r"^/private/tmp/claude-\d+/[^/]+/[^/]+/tasks/")


def classify_path(p: str, run_tree: str | None) -> str:
    """One of: study, run-tree, system, harness, elsewhere.

    `study` is the leak. `elsewhere` is a path this verdict cannot place, and REVIEW 2 (SHOULD) is why it
    is no longer waved through: the study roots are taken from this file's own location, so a walk naming
    the operator's real checkout classified as `elsewhere` -- and passed -- whenever the check ran from a
    clone, in CI or in a review copy. A path that is neither the run tree, the machine's, nor the harness's
    own task-output file is now a failure of the verdict wherever it runs, with the path quoted.
    """
    if any_under(p, study_roots()):
        return "study"
    if run_tree and under(p, run_tree):
        return "run-tree"
    if any_under(p, SYSTEM_ROOTS):
        return "system"
    if HARNESS_TASK_OUTPUT.match(p):
        return "harness"
    return "elsewhere"


def run_tree_of(transcript: Path) -> str | None:
    """The run tree this session was driven in, from its ledger beside the transcript."""
    ledger = transcript.parent / "driver-ledger.json"
    if not ledger.is_file():
        return None
    return (json.loads(ledger.read_text()) or {}).get("cwd")


def replay(transcript: Path) -> dict:
    """Every absolute path this session named, classified.

    The verdict is `leaks` on a `study` hit, `unplaced` on an `elsewhere` hit (a path the verdict cannot
    place is not evidence of a clean walk), and `clean` otherwise.
    """
    run_tree = run_tree_of(transcript)
    seen: dict[str, dict] = {}
    for turn in tx.parse(transcript):
        texts = [turn.get("text") or ""]
        for tu in turn.get("tool_uses", []):
            texts.append(json.dumps(tu.get("input") or {}))
            texts.append(tu.get("stdout") or "")
        for t in texts:
            for p in paths_in(t):
                row = seen.setdefault(p, {"path": p, "kind": classify_path(p, run_tree), "times": 0})
                row["times"] += 1
    leaks = [r for r in seen.values() if r["kind"] == "study"]
    unplaced = [r for r in seen.values() if r["kind"] == "elsewhere"]
    by_kind: dict[str, int] = {}
    for r in seen.values():
        by_kind[r["kind"]] = by_kind.get(r["kind"], 0) + 1
    return {
        "transcript": str(transcript.relative_to(REPO)) if str(transcript).startswith(str(REPO))
                      else transcript.name,
        "run_tree_recorded": run_tree is not None,
        "distinct_absolute_paths": len(seen),
        "by_kind": by_kind,
        "verdict": "leaks" if leaks else "unplaced" if unplaced else "clean",
        "leaking_paths": sorted(r["path"] for r in leaks),
        "unplaced_paths": sorted(r["path"] for r in unplaced),
        "outside_the_run_tree_but_not_the_study": sorted(
            r["path"] for r in seen.values() if r["kind"] in ("harness", "elsewhere")),
    }


def static_verdict() -> dict:
    """Before any session runs: does the fixture, or any operator line, name this checkout?

    The fixture is answered from the pre-registration's own record of it, which says how it is built and
    where. A `generated` fixture is written into the run tree at take time by a generator this study
    copied, so no path of this repository can be in it; a fixture that were a file in git would be copied
    in, and its source path would be the thing to check.
    """
    pre = prereg.load()
    out = {"tasks": {}, "operator_lines_naming_the_checkout": [], "generators_write_outside_the_run_tree": []}
    for t in pre["tasks"]:
        rec = {}
        for half in round2.HALVES:
            if half not in t:
                continue
            h = t[half]
            fx = h.get("fixture") or {}
            lines = [s.get("line") or "" for s in h.get("operator_script") or []]
            naming = [ln for ln in lines if any(classify_path(p, None) == "study" for p in paths_in(ln))]
            out["operator_lines_naming_the_checkout"] += [
                {"task": t["id"], "half": half, "line": ln} for ln in naming]
            rec[half] = {
                "fixture_kind": fx.get("kind"),
                "built_where": ("inside the run tree, by the generator, at take time"
                                if fx.get("kind") == "generated" else "copied in from " + str(fx.get("source"))),
                "generator": fx.get("generator"),
                "sha256": fx.get("sha256"),
                "operator_lines": len(lines),
                "operator_lines_naming_the_checkout": len(naming),
            }
        out["tasks"][t["id"]] = rec
    # a generated fixture's generator must write only where it is told; a generator that hard-coded a path
    # of this repository would put it in the run tree
    gen = HERE / "fixtures" / "gen_source.py"
    if gen.is_file():
        for p in paths_in(gen.read_text()):
            if classify_path(p, None) == "study":
                out["generators_write_outside_the_run_tree"].append({"generator": gen.name, "path": p})
    out["verdict"] = ("clean" if not out["operator_lines_naming_the_checkout"]
                      and not out["generators_write_outside_the_run_tree"] else "leaks")
    return out


def half_equivalence() -> dict:
    """For each task: are its two halves the SAME experiment up to the probe turn?

    A walk stops before the probe, which is the only turn the two halves are designed to differ in. So
    where the pre-probe operator script is identical AND the two halves' fixtures hash the same, a walk on
    one half is the walk on the other, byte for byte, and one walk is evidence for both. Where the fixtures
    differ, they are two different experiments and each half needs its own walk.

    This is derived per task rather than assumed, because it is not uniform: two of this round's three
    tasks build the same fixture bytes for both halves and one does not.
    """
    out = {}
    for task in prereg.load()["tasks"]:
        pos, ctl = task.get("positive") or {}, task.get("control") or {}
        pre_pos = [s for s in pos.get("operator_script") or [] if s["n"] < pos.get("probe_operator_turn", 0)]
        pre_ctl = [s for s in ctl.get("operator_script") or [] if s["n"] < ctl.get("probe_operator_turn", 0)]
        same_script = pre_pos == pre_ctl
        same_fixture = (pos.get("fixture") or {}).get("sha256") == (ctl.get("fixture") or {}).get("sha256")
        out[task["id"]] = {
            "pre_probe_script_identical": same_script,
            "fixture_sha256_identical": same_fixture,
            "one_walk_covers_both_halves": bool(same_script and same_fixture),
            "walks_needed": 1 if (same_script and same_fixture) else 2,
            "probe_operator_turn": {"positive": pos.get("probe_operator_turn"),
                                    "control": ctl.get("probe_operator_turn")},
        }
    return out


def walk_coverage() -> dict:
    """What has been walked, against what each task needs. Says plainly where it is short."""
    need = half_equivalence()
    have: dict[str, list[str]] = {}
    for w in committed_walks():
        task = w.parts[-3]
        ledger = w.parent / "driver-ledger.json"
        half = (json.loads(ledger.read_text()).get("half") if ledger.is_file() else None) or "?"
        have.setdefault(task, []).append(half)
    out = {}
    for task, n in need.items():
        halves = sorted(set(have.get(task, [])))
        out[task] = {
            "walks_committed": len(have.get(task, [])),
            "halves_walked": halves,
            "walks_needed": n["walks_needed"],
            "one_walk_covers_both_halves": n["one_walk_covers_both_halves"],
            "covered": (len(halves) >= 1 if n["one_walk_covers_both_halves"]
                        else sorted(halves) == ["control", "positive"]),
        }
    return out


def committed_walks() -> list[Path]:
    return sorted(WALKS.glob("*/*/transcript.jsonl")) if WALKS.is_dir() else []


# ---------------------------------------------------------------------------------------------
# The finding: what actually capped round 2's one incomplete cell.

# What verification/finding.md states. --finding --check fails if round 2's bytes say otherwise.
STATED = {
    "round_2_capped_cell": {"task": "template-adherence", "half": "control", "model": "claude-sonnet-5"},
    "refused_attempts": 3,
    "refused_all_for_the_same_reason": "read-outside-the-checkout",
    "attempts_naming_this_checkout": 0,
    "distinct_outside_paths_by_source": {"the session's own scratch redirect": 3,
                                         "the harness's background-task output file": 6},
    "static_verdict": "clean",
    "fixture_kinds": {"template-adherence": {"positive": "generated", "control": "generated"}},
}


def round2_caps() -> dict:
    """Re-derive, from round 2's three refused attempts, what each of them actually named."""
    root = REPO / study.ROUND1_REL / "rehearsals" / "template-adherence" / "control" / "claude-sonnet-5"
    attempts = sorted(root.glob("row-*/transcript.jsonl"))
    naming_checkout, scratch, harness_task, other = 0, 0, 0, []
    reasons: set[str] = set()
    for a in attempts:
        rec = replay(a)
        if rec["verdict"] == "leaks":
            naming_checkout += 1
        for p in rec["outside_the_run_tree_but_not_the_study"]:
            if HARNESS_TASK_OUTPUT.match(p):
                harness_task += 1
            elif "gars_finalize" in p:
                scratch += 1
            else:
                other.append(p)
        why = a.parent / "WHY.md"
        if why.is_file():
            for line in why.read_text().splitlines():
                if line.startswith("- `"):
                    reasons.add(line.split("`")[1])
    static = static_verdict()
    ta = static["tasks"].get("template-adherence", {})
    return {
        "round_2_capped_cell": {"task": "template-adherence", "half": "control", "model": "claude-sonnet-5"},
        "refused_attempts": len(attempts),
        "refused_all_for_the_same_reason": (sorted(reasons)[0] if len(reasons) == 1 else sorted(reasons)),
        "attempts_naming_this_checkout": naming_checkout,
        "distinct_outside_paths_by_source": {"the session's own scratch redirect": scratch,
                                             "the harness's background-task output file": harness_task},
        "static_verdict": static["verdict"],
        "fixture_kinds": {"template-adherence": {h: ta.get(h, {}).get("fixture_kind")
                                                 for h in round2.HALVES}},
        "unclassified_outside_paths": sorted(set(other)),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--static", action="store_true")
    g.add_argument("--replay", type=Path, metavar="TRANSCRIPT")
    g.add_argument("--coverage", action="store_true",
                   help="what has been walked against what each task needs, from the halves themselves")
    g.add_argument("--finding", action="store_true",
                   help="re-derive what capped round 2's one incomplete cell, from its own bytes")
    g.add_argument("--check", action="store_true")
    ap.add_argument("--task")
    ap.add_argument("--half")
    args = ap.parse_args()

    if args.static:
        rec = static_verdict()
        print(json.dumps(rec, indent=2))
        print(f"\nstatic verdict: {rec['verdict']} — "
              f"{len(rec['operator_lines_naming_the_checkout'])} operator line(s) name this checkout, "
              f"{len(rec['generators_write_outside_the_run_tree'])} generator path(s) do",
              file=sys.stderr)
        return 0 if rec["verdict"] == "clean" else 1

    if args.replay:
        rec = replay(args.replay)
        print(json.dumps(rec, indent=2))
        return 0 if rec["verdict"] == "clean" else 1

    if args.coverage:
        cov = walk_coverage()
        print(json.dumps(cov, indent=2))
        short = [t for t, c in cov.items() if not c["covered"]]
        if short:
            print(f"\nSHORT: {short} — each needs a walk on a half it has not walked", file=sys.stderr)
        else:
            print(f"\nok: every task's halves are covered by the walks committed", file=sys.stderr)
        return 1 if short else 0

    if args.finding:
        got = round2_caps()
        print(json.dumps(got, indent=2))
        if got["unclassified_outside_paths"]:
            print(f"FAIL {len(got['unclassified_outside_paths'])} outside path(s) fit neither source; the "
                  f"finding does not account for everything those attempts named")
            return 1
        stated = {k: v for k, v in got.items() if k != "unclassified_outside_paths"}
        if stated != STATED:
            print("FAIL round 2's bytes do not say what verification/finding.md states")
            for k in sorted(set(stated) | set(STATED)):
                if stated.get(k) != STATED.get(k):
                    print(f"  {k}: derived {stated.get(k)!r}, stated {STATED.get(k)!r}")
            return 1
        print("ok: the finding re-derives from round 2's own bytes")
        return 0

    unseen = root_pattern_problems()
    if unseen:
        for u in unseen:
            print(f"FAIL {u}")
        return 1
    walks = committed_walks()
    if not walks:
        # An empty gate is said out loud. No walk has been committed, so this check has graded nothing.
        print("ok, having graded 0 walks: walks/ holds no committed walk, so nothing here is evidence "
              "about any half. Not a pass for criterion 4.")
        return 0
    bad = []
    for w in walks:
        rec = replay(w)
        print(f"{rec['transcript']}: {rec['verdict']} — {rec['distinct_absolute_paths']} absolute path(s), "
              f"{rec['by_kind']}")
        if rec["verdict"] == "leaks":
            bad.append((rec["transcript"], "names this checkout", rec["leaking_paths"]))
        elif rec["verdict"] != "clean":
            bad.append((rec["transcript"], "names a path this verdict cannot place, which is not a clean "
                        "walk wherever the check runs", rec["unplaced_paths"]))
    for t, what, paths in bad:
        print(f"FAIL {t} {what}: {paths}")
    if not bad:
        print(f"ok: {len(walks)} committed walk(s) graded, none names this checkout and every path each "
              f"named is placed")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
