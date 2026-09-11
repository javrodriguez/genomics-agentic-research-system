#!/usr/bin/env python3
"""Bind every published number to the bytes it came from.

    python3 evals/gap-study/check_results.py              every pinned file re-hashes
    python3 evals/gap-study/check_results.py --ledger     every take was pre-registered before it ran
    python3 evals/gap-study/check_results.py --controls   the two halves cannot share a correct label
    python3 evals/gap-study/check_results.py --regrade    the results re-derive byte-identically

WHAT EACH ONE ANSWERS, AND WHY IT IS A SEPARATE QUESTION.

  (default)   every file the pre-registration pinned still hashes to what it pinned. A study whose
              grader changed after the freeze is not the study that was pre-registered, and the
              only way to know is to re-take the hash.

  --ledger    for every graded transcript, its session id equals uuid5(namespace, the sha of the
              commit that introduced its row), that commit is an ancestor of HEAD, and no commit
              introduced more than one row. This is the whole "pre-registered before it ran" claim
              and it is arithmetic, not a promise.

  --controls  the correct label for the two halves DIFFERS for every task, and any model whose
              graded takes carry the same label on both halves of a task is printed as failing it.
              A degenerate agent -- one that always refuses, or always agrees -- passes one half of
              a pair by accident, and this is what catches it.

  --regrade   run.py is re-run into a temporary directory and its output compared byte for byte
              with what is committed. A results file that does not re-derive is a claim about a
              grader nobody can reproduce.

IT REFUSES IN A SHALLOW CLONE. The ledger check reads git history. CI clones at depth 1 by default,
where `git log` sees one commit and every ancestry test passes vacuously -- a green that means
nothing, and one this repository has already been bitten by. If the history is shallow this file
says so and exits non-zero rather than reporting a pass it cannot support.

No model, no network, stdlib only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "evals"))

import prereg  # noqa: E402
import takes as takes_mod  # noqa: E402
import transcript as tx  # noqa: E402

RESULTS = HERE / "results"
RAN = "RAN"


def git(*args: str) -> tuple[int, str]:
    out = subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True)
    return out.returncode, out.stdout.strip()


def is_shallow() -> bool:
    code, out = git("rev-parse", "--is-shallow-repository")
    return code == 0 and out == "true"


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ---------------------------------------------------------------- pinned files

def check_pins() -> list[str]:
    """Every file the frozen file pins by sha256 must still hash to it."""
    pre = prereg.load()
    problems: list[str] = []
    checked = 0

    def walk(node, path=""):
        nonlocal checked
        if isinstance(node, dict):
            if node.get("path") and node.get("sha256"):
                checked += 1
                f = REPO / node["path"]
                if not f.is_file():
                    problems.append(f"{path}: pinned file is missing: {node['path']}")
                elif sha256(f) != node["sha256"]:
                    problems.append(f"{path}: {node['path']} does not match its pinned sha256")
            for k, v in node.items():
                walk(v, f"{path}.{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")

    walk(pre)
    if checked == 0:
        problems.append("no file in the pre-registration carries a sha256 yet, so this check "
                        "measured nothing. That is not a pass.")
    else:
        print(f"  {checked} pinned file(s) re-hashed")
    return problems


# ---------------------------------------------------------------- the ledger

def check_ledger() -> list[str]:
    problems: list[str] = []
    if is_shallow():
        return ["this is a SHALLOW clone. The ledger check reads git history, and in a shallow "
                "clone every ancestry test passes vacuously. Clone at full depth "
                "(fetch-depth: 0 in CI) and run it again."]

    rows = takes_mod.load_rows()
    commits = takes_mod.row_commits()
    if not rows:
        print("  the ledger is empty: no take has been registered")
        return problems

    per_commit: dict[str, list[int]] = {}
    for i, row in enumerate(rows):
        sha = commits.get(i)
        if sha is None:
            problems.append(f"row {i} is not committed")
            continue
        per_commit.setdefault(sha, []).append(i)

    for sha, idxs in per_commit.items():
        if len(idxs) > 1:
            problems.append(f"commit {sha[:12]} introduced {len(idxs)} rows ({idxs}); they would "
                            f"share one session id and the binding would prove nothing")

    # EVERY ATTEMPT BELONGS TO EXACTLY ONE COMMITTED ROW, in the folder its kind puts it in
    # (prereg attempt_layout). The first version read only transcripts under the graded layout, so a
    # rehearsal or a pause could not be tied to its row and an unregistered attempt went unseen.
    by_sid = takes_mod.attempts_by_session()
    sid_row = {takes_mod.session_id_for(commits[i]): i for i in range(len(rows)) if i in commits}
    for sid, hits in by_sid.items():
        if sid not in sid_row:
            problems.append(f"an attempt at {hits[0][1]} carries session id {sid}, which no committed "
                            f"row implies: it was never registered")
        if len(hits) > 1:
            problems.append(f"row {sid_row.get(sid)} has {len(hits)} attempts "
                            f"({[str(h[1].relative_to(HERE)) for h in hits]}); a row is attempted once")

    counts = {"graded": 0, "rehearsal": 0, "pause": 0, "not attempted": 0}
    matched = 0
    for i, row in enumerate(rows):
        sha = commits.get(i)
        if sha is None:
            continue
        want = takes_mod.session_id_for(sha)
        hits = by_sid.get(want, [])
        if not hits:
            counts["not attempted"] += 1
            continue
        kind, d = hits[0]
        counts[kind] += 1
        rel = d.relative_to(HERE).parts
        where = (row["task"], row["half"], row["model"])
        expected_leaf = str(row["take"]) if kind == "graded" else f"row-{i}"
        if tuple(rel[1:4]) != where or rel[4] != expected_leaf:
            problems.append(f"row {i}: its {kind} attempt sits at {'/'.join(rel)}, which is not the "
                            f"folder its row names")
        problems += attempt_problems(kind, d, i, row, _check_take())
        t = d / "transcript.jsonl"
        if kind == "graded" and t.is_file():
            got = _session_id_of(t)
            if got != want:
                problems.append(f"row {i}: the transcript's session id {got} is not "
                                f"uuid5(namespace, {sha[:12]}) = {want}")
            else:
                matched += 1
    problems += _order_problems_for(rows)
    print(f"  {len(rows)} row(s): {counts['graded']} graded, {counts['rehearsal']} rehearsal(s), "
          f"{counts['pause']} pause(s), {counts['not attempted']} not attempted; {matched} transcript(s) "
          f"bound to their row's commit")
    return problems


_CT = None


def _check_take():
    """This study's check_take, loaded once by path: the first study has a file of the same name."""
    global _CT
    if _CT is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location("gap_check_take_for_results", HERE / "check_take.py")
        _CT = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_CT)
    return _CT


def _has_agent_text(t: Path) -> bool:
    if not t.is_file():
        return False
    import transcript as tx
    return any(x["role"] == "assistant" and x["text"].strip() for x in tx.load(t)["turns"])


def attempt_problems(kind: str, d: Path, i: int, row: dict, ct) -> list[str]:
    """An attempt re-derived from its own bytes, against the folder it sits in (review 12, blocker 2).

    The folder was the only thing that decided an attempt's kind, so one `git mv` turned a graded take
    into a rehearsal, freed its slot, and left every check clean. Now the ledger's own record of the
    attempt must agree with its folder, a graded take must pass the take checker with its row, a
    rehearsal must carry its WHY.md and either the driver's death-before-first-turn or exactly the
    checker's reasons, and a pause must record a pause and no agent text.
    """
    import contextlib
    import io
    try:
        led = json.loads((d / "driver-ledger.json").read_text())
    except (OSError, json.JSONDecodeError):
        return [f"row {i}: the {kind} attempt has no readable driver ledger"]
    problems: list[str] = []
    recorded = (led.get("attempt") or {}).get("kind")
    if recorded != kind:
        problems.append(f"row {i}: the attempt sits under the {kind} folder and its ledger records "
                        f"{recorded!r}. An attempt's kind is decided by the driver, never by moving it.")
    outcome = led.get("outcome") or ""
    t = d / "transcript.jsonl"
    agent_text = _has_agent_text(t)

    def checked() -> list[str]:
        if not t.is_file():
            return [f"[{ct.NO_FIRST_AGENT_TURN}] no transcript"]
        with contextlib.redirect_stdout(io.StringIO()):
            return ct.check(t, row["task"], row["half"], i, False)

    if kind == "graded":
        if outcome.startswith(("PAUSE", "REHEARSAL")):
            problems.append(f"row {i}: a graded take records the outcome {outcome.split(' ')[0]!r}")
        if t.is_file():
            graded_problems = checked()
            if graded_problems:
                problems.append(f"row {i}: the graded take does not pass the take checker "
                                f"({sorted(set(ct.reason_ids(graded_problems)))})")
        elif not (led.get("first_agent_turn") and "no session file" in outcome):
            problems.append(f"row {i}: a graded take with no transcript must record a first agent turn "
                            f"and a missing session file")
    elif kind == "rehearsal":
        if not (d / "WHY.md").is_file():
            problems.append(f"row {i}: a rehearsal carries no WHY.md naming its reasons")
        reasons = sorted((led.get("attempt") or {}).get("reasons") or [])
        if outcome.startswith("REHEARSAL"):
            if agent_text:
                problems.append(f"row {i}: recorded as a death before the first agent turn, and its "
                                f"transcript holds agent text")
            if reasons != [ct.NO_FIRST_AGENT_TURN]:
                problems.append(f"row {i}: a death before the first agent turn records reasons {reasons}")
        else:
            got = checked()
            ids = sorted(set(ct.reason_ids(got)))
            if not got:
                problems.append(f"row {i}: the take checker passes this attempt, so it is a graded take "
                                f"filed as a rehearsal")
            elif ids != reasons:
                problems.append(f"row {i}: the checker's reasons {ids} are not the recorded {reasons}")
    elif kind == "pause":
        if not outcome.startswith("PAUSE"):
            problems.append(f"row {i}: a pause records the outcome {outcome.split(' ')[0]!r}")
        if agent_text:
            problems.append(f"row {i}: a pause is a refusal before the first agent turn, and its "
                            f"transcript holds agent text")
    return problems


def order_problems(rows: list[dict], order_by_axis: dict, axis_of) -> list[str]:
    """Each slot's FIRST registration falls where the pre-registered order puts it (review 12, F2).

    A retry after a rehearsal or a pause registers its slot again later, and is skipped.
    """
    seen: set = set()
    k: dict = {}
    out: list[str] = []
    for i, r in enumerate(rows):
        slot = (r["task"], r["half"], r["model"], r["take"])
        if slot in seen:
            continue
        seen.add(slot)
        axis = axis_of(r["model"])
        j = k.get(axis, 0)
        k[axis] = j + 1
        order = order_by_axis.get(axis) or []
        if j >= len(order) or tuple(order[j]) != slot:
            there = tuple(order[j]) if j < len(order) else "nothing"
            out.append(f"row {i}: {slot} is registration {j + 1} on the {axis} axis, and the "
                       f"pre-registered order puts {there} there")
    return out


def _order_problems_for(rows: list[dict]) -> list[str]:
    pre = prereg.load()
    if not prereg.is_frozen() or not pre.get("take_order_seed"):
        print("  take order: checked after the freeze, when its seed exists")
        return []
    return order_problems(rows, prereg.order(pre["take_order_seed"]), prereg.axis_of)


def _session_id_of(path: Path) -> str:
    for line in path.read_text(errors="replace").splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(rec, dict):
            sid = rec.get("sessionId") or rec.get("session_id")
            if sid:
                return sid
    return ""


# ---------------------------------------------------------------- the controls

def check_controls() -> list[str]:
    problems: list[str] = []
    pre = prereg.load()
    seen = 0

    for t in pre["tasks"]:
        pos = t["positive"]["correct_behaviour_label"]
        ctl = t["control"]["correct_behaviour_label"]
        if pos == ctl:
            problems.append(f"{t['id']}: both halves have the same correct label ({pos!r}). A "
                            f"degenerate agent would pass both, and the pair measures nothing.")

    for t in pre["tasks"]:
        p = RESULTS / f"{t['id']}.json"
        if not p.is_file():
            continue
        res = json.loads(p.read_text())
        for model, cells in res["cells"].items():
            pl = {x["label"] for x in cells.get("positive", {}).get("labels", [])}
            cl = {x["label"] for x in cells.get("control", {}).get("labels", [])}
            if not pl or not cl:
                continue
            seen += 1
            if pl == cl and len(pl) == 1:
                problems.append(
                    f"{t['id']} / {model}: every take carries the SAME label {pl.pop()!r} on both "
                    f"halves. That is what a degenerate agent looks like, and it fails this task.")

    print(f"  {len(pre['tasks'])} task label-pair(s) checked, {seen} model cell-pair(s) with takes")
    if seen == 0:
        print("  no cell has takes on both halves yet, so the degenerate-agent check has nothing "
              "to read. Recorded, not counted as a pass.")
    return problems


# ---------------------------------------------------------------- the regrade

def check_regrade() -> list[str]:
    problems: list[str] = []
    committed = sorted(RESULTS.glob("*.json"))
    if not committed:
        print("  no results file on disk: nothing to re-derive")
        return problems

    before = {p.name: sha256(p) for p in committed}
    with tempfile.TemporaryDirectory() as td:
        for p in committed:
            (Path(td) / p.name).write_bytes(p.read_bytes())
        code = subprocess.run([sys.executable, str(HERE / "run.py"), "--all"],
                              capture_output=True, text=True).returncode
        if code != 0:
            problems.append(f"run.py --all exited {code}; the results cannot be re-derived")
            return problems
        after = {p.name: sha256(p) for p in sorted(RESULTS.glob("*.json"))}
        for name, digest in before.items():
            if after.get(name) != digest:
                problems.append(f"{name} did not re-derive byte-identically")
    print(f"  {len(before)} results file(s) re-derived")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description="Bind the published numbers to the bytes.")
    ap.add_argument("--ledger", action="store_true")
    ap.add_argument("--controls", action="store_true")
    ap.add_argument("--regrade", action="store_true")
    args = ap.parse_args()

    ran_any = False
    problems: list[str] = []

    if not (args.ledger or args.controls or args.regrade):
        print("pinned files:")
        problems += check_pins()
        ran_any = True
    if args.ledger:
        print("the ledger:")
        problems += check_ledger()
        ran_any = True
    if args.controls:
        print("the controls:")
        problems += check_controls()
        ran_any = True
    if args.regrade:
        print("the regrade:")
        problems += check_regrade()
        ran_any = True

    if not ran_any:
        print("nothing was checked. That is not a pass.")
        return 2

    if problems:
        print(f"\n{len(problems)} problem(s):")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("\nclean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
