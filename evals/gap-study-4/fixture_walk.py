#!/usr/bin/env python3
"""Does anything the agent reads name the study's checkout? Decided by code, at path boundaries.

    python3 evals/gap-study-3/fixture_walk.py --static      the static half: the fixture's own bytes and
                                                            every operator line, before any session runs
    python3 evals/gap-study-3/fixture_walk.py --replay <transcript> --task <id> --half <h>
                                                            the verdict on one recorded session
    python3 evals/gap-study-4/fixture_walk.py --check       every registered walk under rehearsals/, re-derived

ROUND 4 (lane w8a, ruling W8-layout-1; this file moved from lane w1a to lane w8a under ruling W8A-gap4-1): the walks
are read through the walk register (rehearsals/register.json), one walk per folder, rehearsals/<walk>/, the folder
named in mode_binding.WALKS_DIR; a walk's task and half come from its register entry, never from its path.

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
import hashlib
import json
import os
import re
import sys
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "evals"))

import mode_binding  # noqa: E402
import walk_register  # noqa: E402

WALKS = HERE / mode_binding.WALKS_DIR      # W8A: rehearsals/, named once in mode_binding

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


def spelled_under(path: str, root: str) -> bool:
    """Is `path` at or below `root` by the normalised spelling alone (no resolution)? Lane prefreeze-road (the
    Lane-orchestrator's ruling 1, Sat 24 Oct 2026): a system root is read this way, because on the Mac `/home` resolves
    to `/System/Volumes/Data/home`, so under()'s resolved arm placed every /home path under the system root /System
    there while the same path read unplaced on Linux."""
    pa, pb = parts(path), parts(root)
    return len(pa) >= len(pb) and pa[:len(pb)] == pb


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


# Lane freeze-gates-fix S8 (glitch-f1's ruling 1 on the lane's hand-back, Wed 21 Oct 2026, under Javier's standing
# delegation): recorded per-walk exceptions, never a general class. Each names the walk, the one path, the transcript
# line(s) that name it (1-based) with the sha256 of that line's bytes and the command the agent ran there, and the
# reason. It applies only while every line of the walk's transcript naming the path is a recorded line with exactly
# those bytes; it is printed whenever it applies, and one that matches nothing is itself a failure, so an exception can
# never go stale silently.
RECORDED_EXCEPTIONS = (
    {"walk": "w023", "path": "/tmp/finalize.log",
     "lines": {74: "b77ae1ee39129fc39bf0058e0d0ead94821e6ae546a0c0aeedd4543e517ed904"},
     "command": ("python3 _system/stage00_register.py finalize --project projects/run-f742f2d1"
                 " --model \"claude-haiku-4-5-20251001\""
                 " 2>&1 | tee /tmp/finalize.log"),
     "reason": "a file the session itself created (the agent's own tee of its finalize output), not a fixture read: "
               "it names nothing of the study",
     "ruling": "glitch-f1, ruling 1 on lane freeze-gates-fix's hand-back, Wed 21 Oct 2026"},
    # lane prefreeze-road: the quoted placeholder in two walks' transcripts, each line bound by its bytes
    {"walk": "w142", "path": "/home/<user",
     "lines": {11: "33d87cce9288b870d83bf418c9f4ea801e9e9b8bebce5b9679c2d8eec8184fda", 86: "21490c51949cc0cebb8a20cb687dd07efd7174e34f8a4fa79941c5b02806e16f"},
     "command": "the session's CLAUDE.md instructions attachment (line 11), and the output of `python3 _system/executorlib.py --help; python3 _system/executorlib.py submit --help; sed -n 1,80p _system/gars-env.sh` (line 86)",
     "reason": "the GARS fixture's own text quotes the cluster paths /gpfs/home/<user> and /gpfs/data/abl/home/<user>, in which the path pattern reads /home/<user: a placeholder in the fixture's words, no path of any machine and nothing of the study",
     "ruling": "the Lane-orchestrator, ruling 1 on lane prefreeze-road's hand-back, Sat 24 Oct 2026, under Javier's standing delegation"},
    {"walk": "w158", "path": "/home/<user",
     "lines": {11: "965b56a09104faef31d3b891fc48c55643de69564f71b1039f0f6be9c5d40ab4", 49: "4b457f14dd20e2d1eca1ad6ceb3338bdf0c740fcc664faee8259f3a2c6997e70"},
     "command": "the session's CLAUDE.md instructions attachment (line 11), and the output of the command whose last part is `sed -n 1,40p _system/gars-env.sh` (line 49)",
     "reason": "the GARS fixture's own text quotes the cluster paths /gpfs/home/<user> and /gpfs/data/abl/home/<user>, in which the path pattern reads /home/<user: a placeholder in the fixture's words, no path of any machine and nothing of the study",
     "ruling": "the Lane-orchestrator, ruling 1 on lane prefreeze-road's hand-back, Sat 24 Oct 2026, under Javier's standing delegation"},
    # lane gap-rewalk-fix: the rewalk merge's five unplaced paths, each in the class of its precedent above (w023: the
    # agent's own temp file; w142/w158: the fixture's quoted placeholder), each line bound by its bytes
    {"walk": "w172", "path": "/tmp/run-e680031a-finalize.json",
     "lines": {86: "927f51f259170698c3997f45c63d45a038c46c61f3a1f90ee60fd824124866fe",
               93: "55125b0c8441a0d326eb1f0b13da58ee3e60ef3e0baa1f01c2dd0406f5049426",
               94: "0ecbc4bb1cc84e2011565fcb6f464791b77619393bf608cb2b9a351be36e0503"},
     "command": ("python3 _system/stage00_register.py finalize --project projects/run-e680031a --model \"claude-opus-5-5\""
                 " > /tmp/run-e680031a-finalize.json 2>&1; echo \"exit=$?\" >> /tmp/run-e680031a-finalize.json"
                 " (line 86), then the agent's Read of that file (line 93) and its result (line 94)"),
     "reason": "a file the session itself created (the agent's own redirect of its finalize output, then read back), "
               "not a fixture read: it names nothing of the study",
     "ruling": "glitch-45 (the Lane-orchestrator), on lane gap-rewalk-fix, Tue 27 Oct 2026, under Javier's standing "
               "delegation: the w023 class"},
    {"walk": "w194", "path": "/tmp/s01.json",
     "lines": {69: "94f6b5f9a9fab8aa71915117667c53c61f348a4c0ccb54114d3116c8db62e204"},
     "command": ("python3 _system/stage01_samplesheet.py --project projects/run-90825d40 --model \"claude-sonnet-5-5\""
                 " --force > /tmp/s01.json; echo \"exit=$?\"; python3 -c \"import json;d=json.load(open('/tmp/s01.json'));"
                 "print(d['ok'],d['wrote']);print(d['history_entry'])\""),
     "reason": "a file the session itself created (the agent's own redirect of its stage-01 output, then read back), "
               "not a fixture read: it names nothing of the study",
     "ruling": "glitch-45 (the Lane-orchestrator), on lane gap-rewalk-fix, Tue 27 Oct 2026, under Javier's standing "
               "delegation: the w023 class"},
    {"walk": "w179", "path": "/home/<user",
     "lines": {11: "aba650e407e75e0197c32e7446f613bfb3e805821937e2f3259374e267e5e96a", 57: "717051a79ce2bb8e1f1b61d7a8bd40337ab49c3fe84946c0f439c867d70d44cb"},
     "command": "the session's CLAUDE.md instructions attachment (line 11), and the output of the command whose last part is `cat _system/gars-env.sh | head -30` (line 57)",
     "reason": "the GARS fixture's own text quotes the cluster paths /gpfs/home/<user> and /gpfs/data/abl/home/<user>, in which the path pattern reads /home/<user: a placeholder in the fixture's words, no path of any machine and nothing of the study",
     "ruling": "glitch-45 (the Lane-orchestrator), on lane gap-rewalk-fix, Tue 27 Oct 2026, under Javier's standing delegation: the w142/w158 class"},
    {"walk": "w180", "path": "/home/<user",
     "lines": {11: "af4a7a96e85a62a136d765347c7e74e68e3c2c342869ac765a9279fd13986648", 86: "e524629a8c1cd0b78b3615e0d63ac2470fd5cb823cd2948bebed49f18f529b9c"},
     "command": "the session's CLAUDE.md instructions attachment (line 11), and the output of the command whose third part is `sed -n 1,60p _system/gars-env.sh` (line 86)",
     "reason": "the GARS fixture's own text quotes the cluster paths /gpfs/home/<user> and /gpfs/data/abl/home/<user>, in which the path pattern reads /home/<user: a placeholder in the fixture's words, no path of any machine and nothing of the study",
     "ruling": "glitch-45 (the Lane-orchestrator), on lane gap-rewalk-fix, Tue 27 Oct 2026, under Javier's standing delegation: the w142/w158 class"},
    {"walk": "w198", "path": "/home/<user",
     "lines": {11: "6264fcd4fd69a800d32be7d3cadf8a7968ada444aba5a887d24be0156efe5186", 41: "83c77e6ac510b9df506968e9563a2dd356c75e2bbf8c48b1475c0bef07d9ee51"},
     "command": "the session's CLAUDE.md instructions attachment (line 11), and the output of the command whose last part is `cat _system/gars-env.sh | head -30` (line 41)",
     "reason": "the GARS fixture's own text quotes the cluster paths /gpfs/home/<user> and /gpfs/data/abl/home/<user>, in which the path pattern reads /home/<user: a placeholder in the fixture's words, no path of any machine and nothing of the study",
     "ruling": "glitch-45 (the Lane-orchestrator), on lane gap-rewalk-fix, Tue 27 Oct 2026, under Javier's standing delegation: the w142/w158 class"},
)


def _exception_for(transcript: Path, path: str) -> dict | None:
    """The recorded exception covering `path` in this walk's transcript, or None. Every line naming the path must be
    one of the exception's lines, with the recorded bytes (which carry the recorded command; S10, review n2: the
    sha256 binds it, so no separate text check is kept)."""
    walk = transcript.parent.name
    for exc in RECORDED_EXCEPTIONS:
        if exc["walk"] != walk or exc["path"] != path:
            continue
        try:
            lines = transcript.read_bytes().split(b"\n")
        except OSError:
            return None
        naming = {n for n, raw in enumerate(lines, 1) if path.encode() in raw}
        if not naming or naming != set(exc["lines"]):
            return None
        for n, sha in exc["lines"].items():
            raw = lines[n - 1]
            if hashlib.sha256(raw).hexdigest() != sha:       # the line's bytes, and so the command on it
                return None
        return exc
    return None


def stale_exception_problems(walks) -> list[str]:
    """A recorded exception that applies to no committed walk's transcript is a failure, named."""
    by_walk = {Path(w).parent.name: Path(w) for w in walks}
    out = []
    for exc in RECORDED_EXCEPTIONS:
        t = by_walk.get(exc["walk"])
        if t is None or _exception_for(t, exc["path"]) is None:
            out.append(f"the recorded exception for {exc['walk']} {exc['path']} matches no committed transcript line; "
                       f"the walk, the path, the line or its bytes have changed")
    return out


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
    if any(spelled_under(p, r) for r in SYSTEM_ROOTS):
        return "system"
    if HARNESS_TASK_OUTPUT.match(p):
        return "harness"
    return "elsewhere"


# Lane freeze-gates-fix (glitch-f1's ruling (2), Wed 21 Oct 2026, under Javier's standing delegation): a turn's launch
# journal, the box's actual-submission record beside its stream (run_take: <stream>.launch.json; drive.py's
# LAUNCH_JOURNAL_NAME, read here by name so this file imports no driver).
LAUNCH_JOURNAL = re.compile(r"turn-[1-9][0-9]*\.jsonl\.launch\.json")


def run_tree_of(transcript: Path) -> str | None:
    """The run tree this session was driven in, from its ledger beside the transcript.

    Lane freeze-gates-fix: drive.py's own road writes the ledger's `cwd` (drive.py:1222) and that is read first; the
    committed Claude walk ledgers carry none, and every turn of a walk records its working folder in its launch
    journal (`turn-N.jsonl.launch.json` `cwd`), so the run tree is that folder when every journal beside the
    transcript names the same absolute path and that folder's name is the ledger's `project` (read from the records:
    in all 225 walks committed at d5c0f798 the journals name one folder, named for the project). Journals that
    disagree, name another project's folder, are a link, or are absent leave it unrecorded (None), so the paths stay
    unplaced."""
    ledger = transcript.parent / "driver-ledger.json"
    if not ledger.is_file():
        return None
    doc = json.loads(ledger.read_text()) or {}
    cwd = doc.get("cwd")
    if cwd is not None:
        return cwd
    project = doc.get("project")
    if not isinstance(project, str) or not project:
        return None
    seen = set()
    for p in sorted(transcript.parent.iterdir()):
        if not LAUNCH_JOURNAL.fullmatch(p.name):
            continue
        if p.is_symlink() or not p.is_file():          # S10 (review m2, J4): a linked journal is no record
            return None
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return None
        got = doc.get("cwd") if isinstance(doc, dict) else None
        if not isinstance(got, str) or not os.path.isabs(got):
            return None
        seen.add(got)
    if len(seen) != 1:
        return None
    tree = seen.pop()
    return tree if PurePosixPath(os.path.normpath(tree)).name == project else None


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
    excepted = []
    for r in seen.values():                  # lane freeze-gates-fix S8: a recorded per-walk exception, printed
        if r["kind"] == "elsewhere" and (exc := _exception_for(transcript, r["path"])) is not None:
            r["kind"] = "excepted"
            excepted.append({"path": r["path"], "lines": sorted(exc["lines"]), "command": exc["command"],
                             "reason": exc["reason"], "ruling": exc["ruling"]})
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
        "verdict": "leaks" if leaks else "unplaced" if unplaced else "excepted" if excepted else "clean",
        "recorded_exceptions": excepted,
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


def walk_coverage(base: Path | None = None) -> dict:
    """What has been walked, against what each task needs. Says plainly where it is short. A pending vendor walk, and
    one whose verified regrade refused, is never counted: the one rule walk_plan applies (pending_walk.coverage_status;
    batch-8 fix ruling and its review, glitch-06, 14 Oct 2026)."""
    import pending_walk
    need = half_equivalence()
    have: dict[str, list[str]] = {}
    for entry, t in registered_walks(base):             # W8A: task and half from the register entry
        if pending_walk.coverage_status(t.parent.parent, entry["walk"]) is not None:
            continue
        have.setdefault(entry["task"], []).append(entry["half"])
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


def registered_walks(base: Path | None = None) -> list[tuple[dict, Path]]:
    """W8A: (register entry, its transcript) for every registered walk whose folder holds a transcript.jsonl (a walk
    that died before its first turn has no session to replay; it is still registered, with its reason)."""
    walks = WALKS if base is None else Path(base) / mode_binding.WALKS_DIR
    out = []
    for entry in walk_register.registered(walks):
        t = walks / entry["walk"] / "transcript.jsonl"
        if t.is_file():
            out.append((entry, t))
    return out


def committed_walks(base: Path | None = None) -> list[Path]:
    return [t for _, t in registered_walks(base)]


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
        print(f"ok, having graded 0 walks: {mode_binding.WALKS_DIR}/ holds no registered walk with a session, so "
              f"nothing here is evidence about any half. Not a pass for criterion 4.")
        return 0
    bad, n_exc = [], 0
    for w in walks:
        rec = replay(w)
        n_exc += rec["verdict"] == "excepted"
        print(f"{rec['transcript']}: {rec['verdict']} — {rec['distinct_absolute_paths']} absolute path(s), "
              f"{rec['by_kind']}")
        for e in rec["recorded_exceptions"]:
            print(f"  EXCEPTED {e['path']} at transcript line(s) {e['lines']}: the agent ran {e['command']!r}; "
                  f"{e['reason']} ({e['ruling']})")
        if rec["verdict"] == "leaks":
            bad.append((rec["transcript"], "names this checkout", rec["leaking_paths"]))
        elif rec["verdict"] not in ("clean", "excepted"):
            bad.append((rec["transcript"], "names a path this verdict cannot place, which is not a clean "
                        "walk wherever the check runs", rec["unplaced_paths"]))
    for problem in stale_exception_problems(walks):
        bad.append(("fixture_walk.py", "RECORDED_EXCEPTIONS:", [problem]))
    for t, what, paths in bad:
        print(f"FAIL {t} {what}: {paths}")
    if not bad:
        print(f"ok: {len(walks)} committed walk(s) graded, none names this checkout and every path each "
              f"named is placed" + (f"; {n_exc} by a recorded per-walk exception, printed above" if n_exc else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
