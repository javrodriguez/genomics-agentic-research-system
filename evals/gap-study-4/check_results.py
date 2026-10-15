#!/usr/bin/env python3
"""Re-verify committed routes, ledger identities, interface 11 lists and publication.

Default, --check and --ledger all check the complete publication. No recorded
route is repaired. Before the freeze an empty tree says no takes, never zeros.
After the freeze the pinned bytes and frozen content are checked before records
are regraded with local v4 files. Publication reads committed cell states and
closed rulings; differing candidate counts for a ruled pause use the strict
own-event count with a publication note (round 3 re-ruling).
Under w5b-4, runtime outputs have no copy fragment. Their commit history must
start strictly after the freeze, including outputs later removed from the tree.
Only the disposable rehearsal plan passes --rehearsal-plan: its exact placeholder
is reported NOT CHECKED. Ordinary checks still require the real rehearsal record.
"""

from __future__ import annotations

import argparse
import collections
import copy
import hashlib
import json
import subprocess
import sys
import importlib.util
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
# Round 2, CP0: this study's directory BEFORE evals/, whose same-named modules otherwise shadow it.
sys.path.insert(0, str(HERE))

import prereg  # noqa: E402
import study  # noqa: E402
import takes as takes_mod  # noqa: E402
import batch  # noqa: E402
import routing  # noqa: E402
from graders import labels4  # noqa: E402
import stats  # noqa: E402

STRICT_PAUSE_NOTE = "ruled pause counted strictly"


def validate_ledger(rows: list) -> dict:
    """Registered identities, never filling an agent or pooling two harnesses."""
    registered, cells, slots, cell_ids = {}, {}, {}, {}
    for row in rows:
        bad = takes_mod.agent_problems(row)
        if bad:
            raise ValueError("; ".join(bad))
        identity = {k: row[k] for k in stats.TAKE_FIELDS[:8]}
        stats.validate_record(dict(identity, route=labels4.GRADED, cell_state=None,
                                   label="identity-only", views={v: "wrong" for v in stats.VIEWS}))
        key = (row["slot"], row["attempt"])
        if type(row["attempt"]) is not int or row["attempt"] < 1 or key in registered:
            raise ValueError("a registration needs a unique slot and positive attempt")
        cell, slot = takes_mod.half_cell_key(row), takes_mod.try_key(row)
        if cells.setdefault(row["half_cell"], cell) != cell or slots.setdefault(row["slot"], slot) != slot:
            raise ValueError("one cell or slot id names two identities (including harness)")
        if cell_ids.setdefault(cell, row["half_cell"]) != row["half_cell"]:
            raise ValueError("one half-cell identity carries two ids (including harness)")
        registered[key] = row
    return registered


def verify_route(outcome: dict, table: dict) -> None:
    """Re-verify a drive's entire recorded decision; never replace or repair it.

    A stopped take has no publishable decision until a closed human ruling is
    read from committed history. Its original records are retained unchanged.
    """
    if outcome["state"] in labels4.BATCH_STATES:
        return
    try:
        expected = routing.route(outcome["records"], table)
    except (ValueError, TypeError, KeyError) as exc:
        raise ValueError(f"recorded route cannot be re-verified: {exc}") from exc
    if (outcome["decision"] != expected or outcome["state"] != expected["route"] or
            outcome["events"] != expected["events"] or outcome["mask"] != expected["mask"]):
        raise ValueError("recorded route or annotations differ from the drive's records")


def window_problems(history: list) -> list[str]:
    """A window event occupies at most one block's span, with no slot twice."""
    outcomes = [o for o in history if batch.is_outcome(o)]
    positions = collections.defaultdict(list)
    for i, o in enumerate(outcomes):
        if o["state"] == labels4.PAUSE:
            positions[o["window_event"]].append(i)
    bad = []
    for event, indices in positions.items():
        stretch = outcomes[indices[0]:indices[-1] + 1]
        slots = [o["slot"] for o in stretch]
        events = {o["window_event"] for o in stretch if o["state"] == labels4.PAUSE}
        if len(stretch) > batch.BLOCK or len(set(slots)) != len(slots) or events != {event}:
            bad.append(f"window event {event} does not fit one block of at most {batch.BLOCK} consecutive outcomes")
    return bad


def pause_event(history: list, taken: dict) -> dict:
    """Derive the ruled take's event and publication note; no seventh ruling field.

    Enumerate admissible block edges, not exponentially many partitions. An edge
    spans one to BLOCK outcomes, has no repeated slot and cannot split one
    recorded window event or join two. Forward/backward reachability keeps only
    edges in a complete partition. Different edges are allowed when they give
    the same half-cell count. Sharing reduces the count only when that window
    already belongs to this half-cell through another outcome. Otherwise the
    ruled take has its own event, regardless of another cell's window identity.
    If candidate counts differ, use batch's strict own-event count and name it.
    """
    outcomes = [o for o in history if batch.is_outcome(o)]
    key = (taken["slot"], taken["attempt"])
    indices = [i for i, o in enumerate(outcomes) if (o["slot"], o["attempt"]) == key]
    if len(indices) != 1:
        raise ValueError("the ruled pause's take cannot be found uniquely in history")
    n, at = len(outcomes), indices[0]
    event_indices = collections.defaultdict(set)
    for i, o in enumerate(outcomes):
        if o["window_event"] is not None:
            event_indices[o["window_event"]].add(i)
    edges = collections.defaultdict(list)
    for left in range(n):
        for right in range(left + 1, min(n, left + batch.BLOCK) + 1):
            span = outcomes[left:right]
            events = {o["window_event"] for o in span if o["window_event"] is not None}
            if len({o["slot"] for o in span}) != len(span) or len(events) > 1:
                continue
            if any(not event_indices[e] <= set(range(left, right)) for e in events):
                continue
            edges[left].append(right)
    forward = {0}
    for left in range(n):
        if left in forward:
            forward.update(edges[left])
    backward = {n}
    for left in range(n - 1, -1, -1):
        if any(right in backward for right in edges[left]):
            backward.add(left)
    candidates = [(left, right) for left in forward for right in edges[left]
                  if right in backward and left <= at < right]
    if not candidates:
        raise ValueError("the ruled pause's block cannot be derived uniquely from committed history")
    cell_events = {batch.cell_event(o) for o in outcomes
                   if o["half_cell"] == taken["half_cell"] and o["state"] == labels4.PAUSE
                   and (o["slot"], o["attempt"]) != key}
    choices = {}
    for left, right in candidates:
        events = {o["window_event"] for o in outcomes[left:right] if o["window_event"] is not None}
        event = ("take", *key)
        if events and ("window", next(iter(events))) in cell_events:
            event = ("window", next(iter(events)))
        choices[len(cell_events | {event})] = event
    if len(choices) != 1:
        return {"event": ("take", *key), "note": STRICT_PAUSE_NOTE}
    return {"event": next(iter(choices.values())), "note": None}


def ruling_closes(count: int, cap: int) -> bool:
    return count >= cap


def ruled_route(ruling: dict) -> str:
    return ruling["route"]


def publication(history: list, table: dict | None = None) -> dict:
    """Committed fates and cell states, including a ruling as its own state record.

    Ordinary cell states are read, never regenerated from a cap. A route ruling
    has no outcome carrying its fate, so its handler's fate is evaluated at the
    ruling's position. Pauses share a block event when its count is unambiguous;
    differing candidate counts use the strict own-event count with a note.
    """
    table = routing.load_table() if table is None else table
    try:
        bad = batch.Batch.history_problems(history)
    except (KeyError, TypeError) as exc:
        raise ValueError(f"unreadable committed history: {exc}") from exc
    if bad:
        raise ValueError("; ".join(bad))
    bad = window_problems(history)
    bad += batch.Batch.cell_history_problems(SimpleNamespace(table=table), history)
    if bad:
        raise ValueError("; ".join(bad))
    effective, cells, final_slots = {}, {}, set()
    events = collections.defaultdict(set)
    spent_cell, spent_slot = collections.Counter(), collections.Counter()
    for entry in history:
        if batch.is_night_ruling(entry):      # a run-level ruling: no take's fate (THE NIGHTLY STOP)
            continue
        if not batch.is_ruling(entry):
            o = copy.deepcopy(entry)
            if o["slot"] in final_slots:
                raise ValueError(f"slot {o['slot']} attempt {o['attempt']} comes after its final effective attempt")
            verify_route(o, table)
            if o["state"] in (labels4.GRADED, labels4.ABORTED) and not o["final"]:
                raise ValueError("a graded or aborted outcome must be final")
        else:
            key = (entry["slot"], entry["attempt"])
            taken = effective[key]
            if entry["ruling"] == labels4.RULE_RERUN:
                effective[key] = dict(taken, final=False, rerun=True)
                continue
            state, cell = ruled_route(entry), taken["half_cell"]
            o = dict(taken, state=state, ruling=copy.deepcopy(entry))
            if state in batch.CELL_CAPPED_ROUTES:
                event = ("take", *key)
                if state == labels4.PAUSE:
                    pause = pause_event(history, taken)
                    event = pause["event"]
                    if pause["note"]:
                        o["note"] = pause["note"]
                events[(cell, state)].add(event)
                closes = ruling_closes(len(events[(cell, state)]), batch.half_cell_cap(table, state))
                o.update(final=closes, rerun=not closes, beyond_cap=closes)
                if closes:
                    o.update(cell_state=labels4.INCOMPLETE_MECHANICAL,
                             cell_reason=f"committed ruling by {entry['by']} reaches the {state} cap")
            elif state == labels4.HARNESS_ERROR:
                cap = table["caps"][state]
                free = (spent_cell[(cell, state)] < cap["reruns_per_half_cell"] and
                        spent_slot[(o["slot"], state)] < cap["reruns_per_slot"])
                o.update(final=not free, rerun=free, beyond_cap=not free)
            else:
                o.update(final=True, rerun=False, beyond_cap=False)
            if cell in cells and state in batch.RERUN_ROUTES:
                o.update(final=True, rerun=False, beyond_cap=True)
        cell, state = o["half_cell"], o["state"]
        if not batch.is_ruling(entry) and state in batch.CELL_CAPPED_ROUTES:
            events[(cell, state)].add(batch.cell_event(o))
        if o["rerun"] and state in batch.RERUN_ROUTES:
            spent_cell[(cell, state)] += 1
            spent_slot[(o["slot"], state)] += 1
        if o["cell_state"] is not None:
            cells[cell] = dict(cells.get(cell, {}), state=o["cell_state"], reason=o["cell_reason"])
            if o.get("note"):
                cells[cell]["note"] = o["note"]
        effective[(o["slot"], o["attempt"])] = o
        if o["final"]:
            final_slots.add(o["slot"])
    return {"outcomes": [o for o in effective.values() if o["final"]], "cells": cells,
            "window_events": {cell: sorted(es, key=repr) for (cell, route), es in events.items()
                              if route == labels4.PAUSE},
            "attempts": list(effective.values())}

RESULTS = HERE / "records"

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



# ---------------------------------------------------------------- the frozen file itself

def frozen_bytes() -> tuple[dict | None, str]:
    """The pre-registration exactly as its freeze commit wrote it, and the reason when it cannot be read.

    AMENDMENT 4. Checklist line 12 names "a moved threshold after the freeze", and nothing refused one:
    the pins cover the files the frozen file names, not the frozen file. The freeze commit is the first
    commit to introduce prereg.json, so it is read from git rather than trusted from a field inside
    the file it would be checking.
    """
    code, _ = git("rev-parse", "--git-dir")
    if code != 0:
        return None, "NOT A GIT REPOSITORY"
    if is_shallow():
        return None, "this is a SHALLOW clone, so the freeze commit cannot be read"
    frozen_rel = study.rel("prereg.json")
    code, out = git("log", "--reverse", "--format=%H", "--", frozen_rel)
    shas = out.split()
    if code != 0 or not shas:
        return None, f"no commit introduces {frozen_rel}"
    code, text = git("show", f"{shas[0]}:{frozen_rel}")
    if code != 0:
        return None, f"the freeze commit {shas[0][:12]} could not be read"
    return json.loads(text), ""


def frozen_content_problems(frozen: dict, now: dict) -> list[str]:
    """Every field equal to the freeze's, except what an amendment records it changed.

    An amendment may add itself to `amendments` and move a pinned file's sha256. Each moved sha256 must
    chain: the freeze's pin is the first amendment's `sha256_before` for that path, each later before is
    the previous after, and the last after is the pin in force. Anything else that differs is a change
    after the freeze that no amendment records.
    """
    problems: list[str] = []
    frozen_amendments = frozen.get("amendments") or []
    amendments = now.get("amendments") or []
    if amendments[:len(frozen_amendments)] != frozen_amendments:
        problems.append("an amendment present at the freeze was edited or removed")

    chain: dict[str, list[tuple[str, str]]] = {}
    for a in amendments[len(frozen_amendments):]:
        for f in a.get("files") or []:
            chain.setdefault(f["path"], []).append((f.get("sha256_before"), f.get("sha256_after")))

    frozen_pins = {x["path"]: x for x in frozen.get("pinned_files") or []}
    now_pins = {x["path"]: x for x in now.get("pinned_files") or []}
    if set(frozen_pins) != set(now_pins):
        problems.append(f"the pinned files differ from the freeze's: added {sorted(set(now_pins) - set(frozen_pins))}, "
                        f"removed {sorted(set(frozen_pins) - set(now_pins))}")
    for path in sorted(set(frozen_pins) & set(now_pins)):
        f, n = dict(frozen_pins[path]), dict(now_pins[path])
        if f.get("sha256") != n.get("sha256"):
            links = chain.get(path)
            if not links:
                problems.append(f"{path}: its pinned sha256 moved after the freeze and no amendment records it")
            else:
                expect = f.get("sha256")
                for before, after in links:
                    if before != expect:
                        problems.append(f"{path}: an amendment's sha256_before is not the pin it replaced")
                    expect = after
                if expect != n.get("sha256"):
                    problems.append(f"{path}: the last amendment's sha256_after is not the pin in force")
        elif path in chain:
            problems.append(f"{path}: an amendment records a change to it, and its pin is the freeze's")
        f.pop("sha256", None)
        n.pop("sha256", None)
        if f != n:
            problems.append(f"{path}: its pin entry differs from the freeze's in more than its sha256")

    rest_frozen = {k: v for k, v in frozen.items() if k not in ("amendments", "pinned_files")}
    rest_now = {k: v for k, v in now.items() if k not in ("amendments", "pinned_files")}
    for k in sorted(set(rest_frozen) | set(rest_now)):
        if rest_frozen.get(k) != rest_now.get(k):
            problems.append(f"`{k}` differs from the freeze and no amendment can move it: a criterion "
                            f"changed after the freeze")
    return problems


def freeze_commit() -> str | None:
    """The first commit that introduces the frozen file, or None where there is no history to read."""
    code, out = git("log", "--reverse", "--format=%H", "--", study.rel("prereg.json"))
    shas = out.split()
    return shas[0] if code == 0 and shas else None


RUNTIME_PATHS = ("takes.json", "outcomes.json", "rulings.json", "records",
                 "RESULT.md", "cost-calls.json", "COSTS.md")


def runtime_timing_problems() -> list[str]:
    """No runtime artifact in the build or freeze commit, even if later deleted.

    Inspect every reachable change to these paths, not merely HEAD's files.
    A runtime commit must be a strict descendant of the introducing freeze.
    A merged side history without that ancestor also fails closed.
    """
    code, commits = git("log", "--format=%H", "--full-history", "--",
                        *(study.rel(p) for p in RUNTIME_PATHS))
    if code:
        raise ValueError("runtime commit history cannot be read")
    frozen = freeze_commit()
    problems = []
    for commit in commits.split():
        later = frozen is not None and commit != frozen
        if later:
            code, _ = git("merge-base", "--is-ancestor", frozen, commit)
            later = code == 0
        if not later:
            problems.append(f"run output committed before or with the freeze: {commit}")
    return problems


def frozen_commit_problems(frozen: dict, commit: str) -> list[str]:
    """ROUND 2, CP8, review 2 blocker 1: the freeze commit is what the rehearsal exercised, and every pin is a committed blob.

    freeze.py pins each file's bytes from disk and its blob from HEAD; before this, an uncommitted edit to a pinned
    file was frozen with the two fields disagreeing and nothing reading the disagreement. Here the freeze commit's
    study tree must hash to the rehearsed tree the frozen file names (the frozen file and the regrade record it
    rewrites are outside the binding on both sides), and each pin's blob must be the one at the freeze commit and
    hash to the pin's sha256.
    """
    import freeze  # this study's, first on sys.path
    out: list[str] = []
    # AMENDMENT 1 (17 September 2026, before any take). The battery's sandbox and any other copy with a history of its
    # own commits the working tree as one commit, and that commit is the first to carry the frozen file, so it read
    # as the freeze commit here and its tree, which moves with every record the run writes, was held to the rehearsal
    # and refused. The hold reads the study's own history: where the freeze commit does not sit on the parent the
    # frozen file records, this copy does not carry that history, and the hold is printed as not checked rather than
    # passed or failed. The pins are still checked against the files on disk by check_pins.
    code, parent = git("rev-parse", f"{commit}^")
    want_parent = frozen.get("frozen_at_commit_parent")
    if code != 0 or parent != want_parent:
        print(f"  NOT CHECKED: the freeze commit in this copy ({commit[:12]}) does not sit on the recorded parent "
              f"({str(want_parent)[:12]}), so this copy does not carry the study's history and the freeze commit cannot be "
              f"held to its rehearsal here")
        return []
    want = frozen.get("rehearsed_study_tree_sha256")
    if not isinstance(want, str) or len(want) != 64:
        out.append("the frozen file names no rehearsed study tree, so the freeze commit cannot be held to a rehearsal")
    else:
        got = freeze.study_tree_sha(commit)
        if got != want:
            out.append(f"the freeze commit {commit[:12]}'s study tree ({got[:12]}) is not the rehearsed one ({want[:12]}): "
                       f"something was frozen that no rehearsal exercised")
    for pin in frozen.get("pinned_files") or []:
        path, blob, want_sha = pin.get("path"), pin.get("git_blob_sha"), pin.get("sha256")
        if not path or not blob:
            continue
        code, at = git("rev-parse", f"{commit}:{path}")
        if code != 0 or at != blob:
            out.append(f"{path}: the freeze commit carries blob {at[:12] if code == 0 else 'none'} and the pin records "
                       f"{blob[:12]}: the pinned file is not what was committed")
            continue
        if want_sha:
            body = subprocess.run(["git", "-C", str(REPO), "show", f"{commit}:{path}"], capture_output=True).stdout
            if hashlib.sha256(body).hexdigest() != want_sha:
                out.append(f"{path}: the pin's sha256 is not the committed blob's: the pinned bytes were uncommitted at "
                           f"the freeze")
    return out


def rehearsal_record_problems(frozen: dict) -> list[str]:
    """Re-check the stored rehearsal evidence, including in disposable clones."""
    import freeze
    record = frozen.get("rehearsal_record")
    if not isinstance(record, dict) or not isinstance(record.get("text"), str):
        return ["the frozen rehearsal record must carry its evidence, never a placeholder"]
    lines = record["text"].rstrip().splitlines()
    if not lines:
        return ["the frozen rehearsal record is empty"]
    problems = []
    if lines[0] != frozen.get("draft_sha256_at_freeze"):
        problems.append("the frozen rehearsal record names different draft bytes")
    trees = [line for line in lines if line.startswith(freeze.REHEARSAL_TREE_PREFIX)]
    if trees != [freeze.REHEARSAL_TREE_PREFIX + str(frozen.get("rehearsed_study_tree_sha256"))]:
        problems.append("the frozen rehearsal record names a different committed tree")
    if lines[-1] != freeze.REHEARSAL_LAST_LINE:
        problems.append("the frozen rehearsal record did not end all green")
    return problems


def synthetic_digest_problems(frozen: dict, now: dict, rehearsal_plan=False) -> list[str]:
    """W8B-R2-2 (lane w9-cp6, ruled into the CP6 wiring slice by glitch-1b at w8b's round 2): freeze.synthetic_tasks
    re-applied to the committed pre-registration, both as its freeze commit wrote it and as it stands. The freeze
    refuses the rehearsal's synthetic digests outside a rehearsal (W8B-R1-1); this re-reads what was committed, so a
    freeze commit made some other way that carries them is refused here too. Under --rehearsal-plan (a disposable
    rehearsal, whose freeze is given them on purpose) they are printed NOT CHECKED, never silently passed."""
    import freeze  # this study's, first on sys.path
    problems, seen = [], []
    for where, doc in (("the freeze commit's prereg.json", frozen), ("prereg.json", now)):
        digests = doc.get("holdout_salted_digests") if isinstance(doc, dict) else None
        if digests is None:
            continue
        if not isinstance(digests, dict):
            problems.append(f"{where}: holdout_salted_digests is not a map of task to digests")
            continue
        synthetic = freeze.synthetic_tasks(digests)
        if synthetic:
            seen.append(where)
            if not rehearsal_plan:
                problems.append(f"{where} holds the rehearsal's synthetic holdout digests ({', '.join(synthetic)}); "
                                f"a real freeze takes only the salted digests from private aegis (ruling W8B-gap4-1)")
    if rehearsal_plan and seen:
        print(f"  NOT CHECKED: the rehearsal's synthetic holdout digests in {' and '.join(seen)} (disposable "
              f"rehearsal)")
    print(f"  the frozen holdout digests re-read for the rehearsal's synthetic ones: {len(problems)} problem(s)")
    return problems


def check_frozen_content(rehearsal_plan=False) -> list[str]:
    frozen, why = frozen_bytes()
    if frozen is None and why == "NOT A GIT REPOSITORY":
        # A throwaway copy with no history, as the mutation battery builds. Printed, never silent, and
        # never a pass: a clone, full-depth or shallow, is a repository and is checked or refused.
        print("  NOT CHECKED: this copy is not a git repository, so the freeze commit is not here to compare with")
        return []
    if frozen is None:
        return [f"the frozen file could not be compared with its freeze: {why}"]
    now = json.loads((HERE / "prereg.json").read_text())
    problems = frozen_content_problems(frozen, now)
    problems += synthetic_digest_problems(frozen, now, rehearsal_plan)     # W8B-R2-2 (lane w9-cp6)
    rehearsal = []
    if rehearsal_plan:
        if frozen.get("rehearsal_record") != "rehearsal or preview":
            rehearsal.append("disposable rehearsal requires the exact rehearsal placeholder")
        else:
            print("  NOT CHECKED: rehearsal record (disposable rehearsal)")
    else:
        rehearsal += rehearsal_record_problems(frozen)
    print(f"  the frozen file compared with its freeze: {len(now.get('amendments') or [])} amendment(s) "
          f"on record, {len(problems)} unrecorded change(s)")
    print(f"  rehearsal record: {len(rehearsal)} problem(s)")
    commit = freeze_commit()
    held = frozen_commit_problems(frozen, commit) if commit else ["the freeze commit could not be found"]
    print(f"  the freeze commit held to its rehearsal and each pin to its committed blob: {len(held)} problem(s)")
    return problems + rehearsal + held


# ---------------------------------------------------------------- the ledger

def records_equal(actual, wanted):
    return sorted(actual, key=repr) == sorted(wanted, key=repr)


def page_equal(actual, wanted):
    return actual == wanted


def pipeline():
    path = HERE / "run.py"
    spec = importlib.util.spec_from_file_location("verified_pipeline", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_publication(rows, history, records, pre, page, grade, table=None):
    import result
    for row in rows:
        takes_mod.require_planned_row(row, pre)
    stats.check_records(records)
    wanted = pipeline().produce(rows, history, grade, table=table)["records"]
    rendered = result.render(result.from_records(wanted, pre, rows, history, table))
    problems = []
    if not records_equal(records, wanted):
        problems.append("records/ differs from registered, routed and regraded takes")
    if not page_equal(page, rendered):
        problems.append("RESULT.md differs from the complete statistics and committed cell states, including agent")
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--ledger", action="store_true")
    parser.add_argument("--rehearsal-plan", action="store_true",
                        help="disposable rehearsal only; rehearsal evidence is NOT CHECKED")
    args = parser.parse_args(argv)
    try:
        if is_shallow():
            raise ValueError("the committed ledger cannot be checked in a shallow clone")
        early = runtime_timing_problems()
        if early:
            raise ValueError("; ".join(early))
        rows, history = takes_mod.load_rows(), takes_mod.read_history()
        records = stats.load_results(RESULTS)
        if not prereg.is_frozen():
            if rows or history or records:
                raise ValueError("takes exist before the pre-registration is frozen")
            print("check_results: no takes; no frozen pins or publication measured")
            return 0
        pre = prereg.require_frozen("checking publication")
        problems = check_pins() + check_frozen_content(rehearsal_plan=args.rehearsal_plan)
        if rows or history or records:
            page = HERE / "RESULT.md"
            problems += check_publication(rows, history, records, pre,
                                          page.read_text() if page.is_file() else None,
                                          pipeline().grade_committed)
        if problems:
            print("check_results: REFUSE: " + "; ".join(problems))
            return 1
        print(f"check_results: {len(rows)} rows, {len(records)} records verified" if rows or history or records
              else "check_results: no takes; frozen pins verified, no publication measured")
        return 0
    except (ValueError, KeyError, OSError) as exc:
        print(f"check_results: REFUSE: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
