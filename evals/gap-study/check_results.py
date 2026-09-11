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

    # REVIEW 15, F2. The checkout is exported from HEAD, so HEAD must carry the pinned system tree.
    pre = prereg.load()
    want_tree = pre["system_under_test"]["gars_tree_sha"]
    code, head_tree = git("rev-parse", "HEAD:gars")
    if code != 0 or head_tree.strip() != want_tree:
        problems.append(f"HEAD carries gars tree {(head_tree.strip() or 'none')[:12]} and the "
                        f"pre-registration pins {want_tree[:12]}")

    rows = takes_mod.load_rows()
    commits = takes_mod.row_commits()
    # REVIEW 13, BLOCKER 1. Before anything about rows: every folder under the attempt roots that no
    # attempt's ledger ties to a session id is a problem, with or without a registered row, because the
    # runner would otherwise grade what this check never saw.
    for d in takes_mod.unattributed_attempts():
        problems.append(f"{d.relative_to(HERE)} holds a driver ledger or a transcript that no attempt's "
                        f"ledger ties to a session id: it was never registered, or its ledger was written by hand")

    # REVIEW 14, F1. An attempt whose session id no committed row implies is reported before the
    # empty-ledger return too: with no row registered, a planted folder with a made-up id was graded.
    by_sid = takes_mod.attempts_by_session()
    sid_row = {takes_mod.session_id_for(commits[i]): i for i in range(len(rows)) if i in commits}
    for sid, hits in by_sid.items():
        if sid not in sid_row:
            problems.append(f"an attempt at {hits[0][1]} carries session id {sid}, which no committed "
                            f"row implies: it was never registered")
        if len(hits) > 1:
            problems.append(f"row {sid_row.get(sid)} has {len(hits)} attempts "
                            f"({[str(h[1].relative_to(HERE)) for h in hits]}); a row is attempted once")

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

    counts = {"graded": 0, "rehearsal": 0, "pause": 0, "not attempted": 0}
    # REVIEW 16, F1. A graded take with no transcript publishes `aborted` from its ledger alone, and
    # the checker never opens, so none of the bindings can run for it. It used to disappear into the
    # count of transcripts bound; it is named here instead.
    no_transcript: list[int] = []
    per_cell: dict[tuple, dict] = {}
    attempted: dict[int, bool] = {}
    matched = 0
    for i, row in enumerate(rows):
        sha = commits.get(i)
        if sha is None:
            continue
        want = takes_mod.session_id_for(sha)
        hits = by_sid.get(want, [])
        attempted[i] = bool(hits)
        if not hits:
            counts["not attempted"] += 1
            continue
        kind, d = hits[0]
        counts[kind] += 1
        cell = (row["task"], row["half"], row["model"])
        per_cell.setdefault(cell, {})
        per_cell[cell][kind] = per_cell[cell].get(kind, 0) + 1
        rel = d.relative_to(HERE).parts
        where = (row["task"], row["half"], row["model"])
        expected_leaf = str(row["take"]) if kind == "graded" else f"row-{i}"
        if tuple(rel[1:4]) != where or rel[4] != expected_leaf:
            problems.append(f"row {i}: its {kind} attempt sits at {'/'.join(rel)}, which is not the "
                            f"folder its row names")
        problems += attempt_problems(kind, d, i, row, _check_take())
        t = d / "transcript.jsonl"
        if kind == "graded" and not t.is_file():
            no_transcript.append(i)
        if kind == "graded" and t.is_file():
            got = _session_id_of(t)
            if got != want:
                problems.append(f"row {i}: the transcript's session id {got} is not "
                                f"uuid5(namespace, {sha[:12]}) = {want}")
            else:
                matched += 1
    # REVIEW 15, F1. The caps and n were enforced where a row is written and nowhere else, so a row
    # appended by hand and committed read the same as one --add wrote.
    limits = {"graded": int(pre["n"]), "pause": int(pre["pause_cap"]), "rehearsal": int(pre["rehearsal_cap"])}
    for cell, kinds in sorted(per_cell.items()):
        for kind, cap in limits.items():
            if kinds.get(kind, 0) > cap:
                problems.append(f"{cell[0]} / {cell[1]} / {cell[2]}: {kinds[kind]} {kind} attempts, and the "
                                f"pre-registration allows {cap}")

    problems += _order_problems_for(rows, attempted)
    # REVIEW 14, F3. Once results are committed the run is declared finished, and a registered row never
    # attempted is a take lost without a reason; its cell would publish as mechanical when nothing was.
    if any(RESULTS.glob("*.json")) and counts["not attempted"]:
        problems.append(f"results are committed and {counts['not attempted']} registered row(s) were never "
                        f"attempted; their cells would publish as incomplete for no recorded reason")
    print(f"  {len(rows)} row(s): {counts['graded']} graded, {counts['rehearsal']} rehearsal(s), "
          f"{counts['pause']} pause(s), {counts['not attempted']} not attempted; {matched} transcript(s) "
          f"bound to their row's commit")
    if no_transcript:
        print(f"  row(s) {no_transcript}: graded with no transcript on disk. Each publishes `aborted` "
              f"from its driver ledger alone; the take checker never opens for it, so no binding in "
              f"the threat model is checked for it. The label counts against holding.")
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
    """An agent turn as the take checker defines one: the harness's own API-error record is not one."""
    return t.is_file() and _check_take().agent_turn_count(t) > 0


def _normalised_ledger(led: dict, row: dict, t: Path) -> dict:
    """This attempt's ledger with every field the PINNED DRIVER decides put back to what it writes.

    The driver ends a take at `complete` unless a marker went unheld, a budget ran out or the process
    died; it sends every scripted line up to where it stopped; it computes the source from the half's
    fixture kind; and it refuses to run under any turn budget, permission mode or system tree other
    than the frozen ones. Those are the fields an operator would have to edit, and this is what they
    held before the edit.
    """
    ct = _check_take()
    pre = prereg.load()
    half = prereg.task(row["task"])[row["half"]]
    out = dict(led)
    sid = ct.session_id_of(t) if t.is_file() else ""
    project = ct.neutral_name(sid) if sid else ""
    source = ct.expected_source_for(half, project) if project else ""

    # REVIEW 17, BLOCKER 1, ROUTE B. The first version set `outcome` to complete and `turns` to every
    # scripted row, so an edit TOWARDS that state was invisible to the re-run: a take the driver
    # legitimately stopped at an unheld marker, correctly published `did-not-reach`, was refused for
    # the lines it never sent once its outcome was edited to complete, and the refusal survived the
    # re-run because the re-run assumed the edit. That is the label an operator would most want gone.
    # Both fields are now re-derived from the transcript, which the ledger cannot edit: the rows are
    # the scripted steps whose rendered lines the transcript carries, and the outcome is complete when
    # they are all there and a stop at the last one present otherwise.
    script = half.get("operator_script")
    if isinstance(script, list) and t.is_file():
        ops = [ct.normalise(x) for x in ct.user_text_records(t, pre)[0]]
        present = [s for s in script
                   if ct.normalise(ct.render(s["line"], project, source)) in ops]
        if present:
            out["turns"] = [{"n": s["n"]} for s in present]
            out["outcome"] = ("complete" if len(present) == len(script)
                              else "stopped — wait-point marker not held; graded as it stands")

    if led.get("source") is not None and project:
        out["source"] = source
    out["budget_s"] = int(pre["budgets"]["turn_timeout_s"])
    out["permission_mode"] = pre["driver_constants"]["permission_mode"]
    out["gars_tree_sha"] = pre["system_under_test"]["gars_tree_sha"]

    # REVIEW 17, BLOCKER 1, ROUTE A. The fixture block is read by the checker and was left alone here,
    # so one edited character in it produced a refusal that founded a rehearsal. The pinned driver
    # cannot write any of these wrong: the project generator exits non-zero unless stage 01 reaches the
    # expected code and the driver refuses before a session opens, the variant is the half's own spec,
    # the carried fixture's builder refuses a tree that differs from the pin, and a generated fixture's
    # hash is the manifest of the build the driver ran.
    spec_fx = half.get("fixture") or {}
    led_fx = led.get("fixture")
    if isinstance(led_fx, dict):
        fx = dict(led_fx)
        if spec_fx.get("kind"):
            fx["kind"] = spec_fx["kind"]
        if spec_fx.get("variant") is not None:
            fx["variant"] = spec_fx["variant"]
        if fx.get("stage01_expected_exit") is not None:
            fx["stage01_check_exit"] = fx["stage01_expected_exit"]
        pin = spec_fx.get("sha256")
        if pin:
            for key in ("tree_sha256_name_invariant", "sha256", "fixture_sha256"):
                if fx.get(key):
                    fx[key] = pin
        out["fixture"] = fx
    return out


def _ledger_made_reasons(d: Path, t: Path, row: dict, i: int, ct, got: list[str]) -> list[str]:
    """REVIEW 16, BLOCKER 1. Which of this attempt's refusals exist only because its ledger says so.

    Review 15's blocker 2 was closed by naming five reasons the driver decides before a model runs, and
    refusing a rehearsal that records one. The class is larger than the list: the checker reads several
    of its refusals out of the ledger, and the ledger is a file an operator can edit. Editing one field
    makes the checker refuse the take; a refusal is a reason; a reason makes an admissible rehearsal;
    and a rehearsal leaves the count with its slot registered again. Review 16 reproduced it three
    ways on a take the checker passes -- through `outcome`, through a truncated `turns`, and through
    `source` -- each leaving every committed check clean.

    Naming more ids would close those three and not the class. This closes the class: the checker is
    run again on the same transcript with the ledger's driver-written fields normalised, and any
    refusal that disappears was made by the ledger rather than by the session. A refusal that needs
    the ledger to exist was made by the ledger. Refusals the normalised run ADDS are ignored; the only
    question asked here is which of the recorded ones survive without the edit.
    """
    import contextlib
    import io
    if not t.is_file():
        return []
    try:
        led = json.loads((d / "driver-ledger.json").read_text())
    except (OSError, json.JSONDecodeError):
        return []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "transcript.jsonl").write_bytes(t.read_bytes())
        (tmp / "driver-ledger.json").write_text(json.dumps(_normalised_ledger(led, row, t)))
        with contextlib.redirect_stdout(io.StringIO()):
            after = ct.check(tmp / "transcript.jsonl", row["task"], row["half"], i, False)
    return sorted(set(ct.reason_ids(got)) - set(ct.reason_ids(after)))


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
    # REVIEW 17, BLOCKER 1, ROUTE C. Deleting a graded take's transcript made every check that reads it
    # vacuous: the checker reported no first agent turn, the bindings never ran, and the attempt was
    # filed as a rehearsal or a pause with the ledger still recording the agent turn and the published
    # bytes. The driver writes `first_agent_turn` before it routes anything and never files either of
    # those with it true, so the ledger refutes the filing on its own.
    if kind in ("pause", "rehearsal") and led.get("first_agent_turn") \
            and not (led.get("outcome") or "").startswith("complete"):
        if kind == "pause" or not _has_agent_text(d / "transcript.jsonl"):
            problems.append(f"row {i}: the attempt is filed as a {kind} and its own ledger records a "
                            f"first agent turn; the driver writes that field before it routes the "
                            f"attempt and never files a {kind} with it")
    pub = (led.get("published") or {}).get("sha256_after")
    if pub and not (d / "transcript.jsonl").is_file():
        problems.append(f"row {i}: the ledger records published transcript bytes and no transcript "
                        f"sits beside it; the driver publishes the file and the record together")
    recorded = (led.get("attempt") or {}).get("kind")
    if recorded != kind:
        problems.append(f"row {i}: the attempt sits under the {kind} folder and its ledger records "
                        f"{recorded!r}. An attempt's kind is decided by the driver, never by moving it.")
    outcome = led.get("outcome") or ""
    t = d / "transcript.jsonl"
    agent_text = _has_agent_text(t)
    if t.is_file():
        # REVIEW 13, F4. The published bytes are bound to the ledger's own record of them, so an edited
        # transcript needs an edited ledger, which history shows, not only an edited sidecar.
        pub = led.get("published") or {}
        if pub.get("sha256_after") != sha256(t):
            problems.append(f"row {i}: the transcript's bytes are not the ones its ledger records as published")

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
        # REVIEW 15, BLOCKER 2. The checker reads some of its refusals from the ledger itself, so an
        # edited constant makes a rehearsal "consistent" with a record the driver cannot have written:
        # it refuses those before it opens a session.
        cannot = sorted(set(reasons) & set(prereg.load().get("driver_decided_reasons") or []))
        if cannot:
            problems.append(f"row {i}: the rehearsal records reason(s) {cannot}, which the driver decides "
                            f"before or without a model and refuses to run under, so it cannot have "
                            f"written this record")
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
            if not t.is_file():
                # A rehearsal after the first agent turn is published and regradable by any reader
                # (limitations line 6). Without its transcript nothing about it can be re-derived.
                problems.append(f"row {i}: a rehearsal after the first agent turn carries no "
                                f"transcript, so nothing in it can be regraded")
            made = _ledger_made_reasons(d, t, row, i, ct, got)
            if made:
                problems.append(f"row {i}: the refusal(s) {made} disappear when the ledger's own "
                                f"driver-written fields are read as the driver writes them, so they "
                                f"were made by an edit to the ledger and not by the session. A rehearsal "
                                f"cannot be founded on them.")
    elif kind == "pause":
        # REVIEW 14, BLOCKER 1. A pause frees a slot on the driver's record alone, so it must at least
        # name the pre-registered marker it matched and when it waited; its count is capped and published.
        pause = led.get("pause") or {}
        markers = prereg.load()["driver_constants"]["rate_limit_markers"]
        if pause.get("matched") not in markers or not pause.get("started") or not pause.get("ended"):
            problems.append(f"row {i}: a pause must record the pre-registered rate-limit marker it matched and "
                            f"when it started and ended")
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


def gap_problems(rows: list[dict], attempted: dict, axis_of) -> list[str]:
    """A registered row never attempted while a later row on its axis was (review 13, F2).

    Such a slot stays registered and cannot be retried, so its cell publishes short with no rehearsal
    and no reason: the cheapest way to lose a take without a word.
    """
    last: dict = {}
    for i, r in enumerate(rows):
        if attempted.get(i):
            last[axis_of(r["model"])] = i
    out = []
    for i, r in enumerate(rows):
        ax = axis_of(r["model"])
        if not attempted.get(i) and i < last.get(ax, -1):
            out.append(f"row {i} was never attempted, and a later row on the {ax} axis was: a registered "
                       f"take was skipped")
    return out


def _order_problems_for(rows: list[dict], attempted: dict) -> list[str]:
    pre = prereg.load()
    if not prereg.is_frozen() or not pre.get("take_order_seed"):
        print("  take order and skipped rows: checked after the freeze, when the order's seed exists")
        return []
    return (order_problems(rows, prereg.order(pre["take_order_seed"]), prereg.axis_of)
            + gap_problems(rows, attempted, prereg.axis_of))


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
