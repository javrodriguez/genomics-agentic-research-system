#!/usr/bin/env python3
"""Re-verify committed routes, ledger identities, interface 11 lists and publication.

Default, --check and --ledger all check the complete publication. No recorded
route is repaired. Before the freeze an empty tree says no takes, never zeros.
After the freeze the pinned bytes and frozen content are checked before records
are regraded with local v4 files. Publication reads committed cell states and
closed rulings; a ruled pause counts as its own event with a publication note
(round 3 re-ruling; B19-5, batch.py's rolling window, made it the only count).
Under w5b-4, runtime outputs have no copy fragment. Their commit history must
start strictly after the freeze, including outputs later removed from the tree.
Only the disposable rehearsal plan passes --rehearsal-plan: its exact placeholder
is reported NOT CHECKED. Ordinary checks still require the real rehearsal record.

--witness (pre-freeze review 2, MAJOR 2; lane fold2-lb) reads GitHub's push records
of the mirror (freeze.push_records, the network, on the Mac at publication and at
each batch fetch from athena). A pushed commit off HEAD's line that changes the take
ledger (takes.json, outcomes.json, rulings.json) is refused: a take registered, run,
reset away and re-run once its first history reached the mirror. Every take-ledger
commit on HEAD's line that no push record holds is printed by sha and counted as
unwitnessed; that count is published. Registrations are committed inside the drive
loop on athena (drive.Driver.register), which holds no push credentials, so the
window the witness cannot close is from a take's registration to the first push
that holds it: a history reset inside that window leaves no outside record.
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
                                   label="identity-only", views={v: "wrong" for v in stats.VIEWS},
                                   agent_events=[], ruled=False,
                                   human_sample=False, human_why=[]))    # MAJOR 6 (lane pf1-l2b): the closed record
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


# Pre-freeze review 1, MAJOR 8 (batch.py THE RULING RULE): the ruled routes that drive a stopped take's slot again.
RERUN_RULED_ROUTES = (labels4.PAUSE, labels4.HARNESS_ERROR, labels4.REHEARSAL)


def ruled_rerun_problems(history: list, registered: dict, standing, table: dict | None = None) -> list[str]:
    """THE RULING RULE's publication half: a ruling that re-runs a stopped take (re-run, or a route to pause,
    harness-error or rehearsal) whose records show the agent's first turn started, or cannot show its phase, stands
    only when the take's own grader reads its committed end state with no wrong action. `standing(row, outcome)` is
    that reading's word in the excluded view (run.produce grades the take); a take that cannot be graded counts as
    wrong, fail-closed. Before the first turn the agent had not acted, and nothing is read."""
    table = routing.load_table() if table is None else table
    seen, out = {}, []
    for entry in history:
        if batch.is_outcome(entry):
            seen[(entry.get("slot"), entry.get("attempt"))] = entry
            continue
        if not batch.is_ruling(entry) or not (entry.get("ruling") == labels4.RULE_RERUN
                                               or entry.get("route") in RERUN_RULED_ROUTES):
            continue
        key = (entry.get("slot"), entry.get("attempt"))
        taken = seen.get(key)
        if taken is None:
            continue                         # history_problems names a ruling on no committed take
        phase = batch.ruled_phase(taken, table)
        if phase == labels4.BEFORE_FIRST_TURN:
            continue
        try:
            word = standing(registered[key], taken)
        except Exception:  # noqa: BLE001  fail-closed: an end state that cannot be read is never clean
            word = "wrong"
        if word != "wrong":
            continue
        what = entry["ruling"] if entry["ruling"] == labels4.RULE_RERUN else f"{entry['ruling']} {entry['route']}"
        out.append(f"slot {key[0]} attempt {key[1]} ({phase}) was ruled {what} by {entry.get('by')}, but its own "
                   f"grader reads its committed end state wrong (or cannot read it): a take whose end state shows a "
                   f"wrong action is never discarded and re-run (THE RULING RULE); rule it graded or aborted")
    return out


# Pre-freeze review 2, m6 (lane fold2/la2, glitch-45's fold plan, 29 Oct 2026): THE RULING RULE's criterion between the
# two final routes a ruling may give a take after its first turn.
FINAL_RULED_ROUTES = (labels4.GRADED, labels4.ABORTED)


def unread_cite(kind: str) -> str:
    """The words an aborted ruling's cite opens with when its end state cannot be read: the phrase, then the reading's
    exception type (the review of fold2/la2, m-a: the code checks what the rule text says)."""
    return f"{batch.END_STATE_UNREAD_CITE}: {kind}"


def unread_cite_holds(cite, kind: str) -> bool:
    """The cite opens with unread_cite(kind), the type a whole word (never a negation, nor another type)."""
    head = unread_cite(kind)
    return isinstance(cite, str) and cite.startswith(head) and not cite[len(head):len(head) + 1].isidentifier()


def ruled_route_problems(history: list, registered: dict, reading, table: dict | None = None) -> list[str]:
    """THE RULING RULE's criterion (pre-freeze review 2, m6): a ruling that routes a take graded or aborted after the
    agent's first turn (read from the take's own records) routes it graded when the take's own grader reads its
    committed end state (`reading(row, outcome)` returns, whatever its word: the end state reads whole), and aborted
    only when it cannot (`reading` raises), the ruling's cite then opening with unread_cite(<the exception type>). A
    ruling on a take with no registered row is refused, never read as unreadable. Before the
    first turn, and for a take whose records cannot show its phase (no records: the existing aborted-only rule holds),
    nothing is read here; re-running rulings are ruled_rerun_problems'."""
    table = routing.load_table() if table is None else table
    seen, out = {}, []
    for entry in history:
        if batch.is_outcome(entry):
            seen[(entry.get("slot"), entry.get("attempt"))] = entry
            continue
        if not batch.is_ruling(entry) or entry.get("ruling") != labels4.RULE_ROUTE \
                or entry.get("route") not in FINAL_RULED_ROUTES:
            continue
        key = (entry.get("slot"), entry.get("attempt"))
        taken = seen.get(key)
        if taken is None or batch.ruled_phase(taken, table) != labels4.AFTER_FIRST_TURN:
            continue                         # history_problems names a ruling on no committed take
        what = f"slot {key[0]} attempt {key[1]} was ruled {entry['route']} by {entry.get('by')}"
        row = registered.get(key)
        if row is None:                      # the review of fold2/la2, n-a: never read as an unreadable end state
            out.append(f"{what}, but it has no registered row, so its end state cannot be read")
            continue
        try:
            word, why, kind = reading(row, taken), None, None
        except Exception as e:  # noqa: BLE001  any failure to read is the reading the ruling must cite
            word, why, kind = None, f"{type(e).__name__}: {e}", type(e).__name__
        if entry["route"] == labels4.ABORTED and why is None:
            out.append(f"{what}, but its own grader reads its committed end state ({word}): an end state that "
                       f"reads whole is ruled graded, never aborted (THE RULING RULE, pre-freeze review 2 m6)")
        elif entry["route"] == labels4.ABORTED and not unread_cite_holds(entry.get("cite"), kind):
            out.append(f"{what} on an end state its grader cannot read ({why}), but its cite does not open with "
                       f"{unread_cite(kind)!r} (THE RULING RULE, pre-freeze review 2 m6)")
        elif entry["route"] == labels4.GRADED and why is not None:
            out.append(f"{what}, but its own grader cannot read its committed end state ({why}): rule it aborted, "
                       f"citing {batch.END_STATE_UNREAD_CITE!r} (THE RULING RULE, pre-freeze review 2 m6)")
    return out


# The Lane-orchestrator's ruling on the pin-block gap (Sat 24 Oct 2026, under Javier's standing delegation): a pin-blocked
# outcome is a harness event, never a take result.
def pin_is_registered(outcome: dict, registered: dict) -> bool:
    """The outcome's records carry its registered row's model and agent (run.require_registered_outcome's test)."""
    row = registered.get((outcome.get("slot"), outcome.get("attempt")))
    rec = outcome.get("records")
    if row is None or not isinstance(rec, dict) or not isinstance(rec.get("pin"), dict):
        return False
    return all(rec["pin"].get(k) == v for k, v in dict(model=row["model"], **row["agent"]).items())


def pin_block_events(history: list, registered: dict, table: dict | None = None, *, refusal=None,
                     committed=None) -> list[dict]:
    """The committed outcomes whose pin is not their row's that the identity guard exempts, each as a harness event
    {slot, attempt, recorded_pin, registered_pin}: only when (1) Batch._route wrote the block (batch.pin_block) and
    the commit that appended it is the take road's (`committed`, takes.outcome_committed_by_take_road), (2) the same
    slot has a later outcome under the registered pin, and (3) the ruling that re-ran it passed THE RULING RULE
    (batch.ruling_rule_problems and door_rule_problems; the end state is read by ruled_rerun_problems, as for every
    re-run). Every other pin mismatch stays refused. `refusal` and `committed` stand in for the git readers in tests."""
    import takes as takes_reader
    table = routing.load_table() if table is None else table
    refusal = takes_reader.driver_refusal_record if refusal is None else refusal
    committed = takes_reader.outcome_committed_by_take_road if committed is None else committed
    outcomes = [o for o in history if batch.is_outcome(o)]
    rulings = {(e.get("slot"), e.get("attempt")): e for e in history if batch.is_ruling(e)}
    rows, events = list(registered.values()), []
    for o in outcomes:
        key = (o.get("slot"), o.get("attempt"))
        if o.get("records") is None or key not in registered or pin_is_registered(o, registered):
            continue
        if not batch.pin_block(o) or not committed(o):
            continue
        ruling = rulings.get(key)
        later = next((x for x in outcomes if x["slot"] == o["slot"] and x["attempt"] > o["attempt"]
                      and pin_is_registered(x, registered)), None)
        if not (later and ruling is not None):
            continue
        if (not batch.reruns(ruling) or batch.ruling_rule_problems(ruling, o, table)
                or batch.door_rule_problems([o, ruling], rows, table, refusal)):
            continue
        row = registered[key]
        events.append({"slot": o["slot"], "attempt": o["attempt"], "recorded_pin": o["records"]["pin"],
                       "registered_pin": dict(model=row["model"], **row["agent"])})
    return events


def render_harness_events(events: list) -> str:
    """The published list of pin-block harness events; empty when there is none."""
    if not events:
        return ""
    def pin(x):
        return " ".join(str(x.get(k)) for k in ("model", "harness", "version"))
    lines = ["## Harness events: driver pin blocks", "",
             "Takes the loop blocked because the driver's pin was not the registered row's profile, each re-run "
             "under the registered pin by a ruling that passed the ruling rule. Harness events, never counted.", "",
             "| Slot | Attempt | Recorded pin | Registered pin |", "|---|---|---|---|"]
    for e in events:
        lines.append(f"| {e['slot']} | {e['attempt']} | {pin(e['recorded_pin'])} | {pin(e['registered_pin'])} |")
    return "\n".join(lines) + "\n"


def window_problems(history: list) -> list[str]:
    """A window event holds at most BLOCK pauses within at most MAX_OPEN consecutive outcomes, with no slot twice
    and no other event's pause between them (B19-5: batch.py's rolling window commits the takes that were open when
    the first pause was seen between its pauses)."""
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
        if (len(indices) > batch.BLOCK or len(stretch) > batch.MAX_OPEN or len(set(slots)) != len(slots)
                or events != {event}):
            bad.append(f"window event {event} does not fit: at most {batch.BLOCK} pauses within at most "
                       f"{batch.MAX_OPEN} consecutive outcomes, no slot twice and no other event between them")
    return bad


def pause_event(history: list, taken: dict) -> dict:
    """The ruled take's event and publication note; no seventh ruling field.

    B19-5 (proposal 7) and B19-6: a pause a ruling routes counts as its own event
    in its half-cell, the strict own-event count batch itself uses. A rolling run
    has no block edges to derive a shared event from, so a ruled pause can count
    as its own event where a block run would have merged it with its block; it is
    named with the publication note whenever another pause of its half-cell
    carries a window event (one it could have shared).
    """
    outcomes = [o for o in history if batch.is_outcome(o)]
    key = (taken["slot"], taken["attempt"])
    indices = [i for i, o in enumerate(outcomes) if (o["slot"], o["attempt"]) == key]
    if len(indices) != 1:
        raise ValueError("the ruled pause's take cannot be found uniquely in history")
    shared = any(o["half_cell"] == taken["half_cell"] and o["state"] == labels4.PAUSE and o["window_event"] is not None
                 for o in outcomes)
    return {"event": ("take", *key), "note": STRICT_PAUSE_NOTE if shared else None}


def ruling_closes(count: int, cap: int) -> bool:
    return count >= cap


def ruled_route(ruling: dict) -> str:
    return ruling["route"]


def publication(history: list, table: dict | None = None) -> dict:
    """Committed fates and cell states, including a ruling as its own state record.

    Ordinary cell states are read, never regenerated from a cap. A route ruling
    has no outcome carrying its fate, so its handler's fate is evaluated at the
    ruling's position. A ruled pause counts as its own event, with a note
    (pause_event; B19-5).
    """
    table = routing.load_table() if table is None else table
    try:
        bad = batch.Batch.history_problems(history, table)
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
                raw = pinned_bytes(path, node["path"])
                if raw is None:
                    problems.append(f"{path}: pinned file is missing: {node['path']}")
                elif hashlib.sha256(raw).hexdigest() != node["sha256"]:
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
    # Lane gemini-defer, ruling R7 (glitch-f1, 22 Oct 2026): the draft writes `amendments` as a dict keyed by arm
    # (build_draft.assemble), so both shapes are read. A dict keeps every key present at the freeze with its value
    # and adds new keys after it; a list keeps the freeze's entries as its head. A change of shape is an edit.
    frozen_amendments = frozen.get("amendments") or []
    amendments = now.get("amendments") or []
    later: list = []
    if isinstance(frozen_amendments, dict) and isinstance(amendments, dict):
        if any(k not in amendments or amendments[k] != v for k, v in frozen_amendments.items()):
            problems.append("an amendment present at the freeze was edited or removed")
        later = [v for k, v in amendments.items() if k not in frozen_amendments]
    elif isinstance(frozen_amendments, list) and isinstance(amendments, list):
        if amendments[:len(frozen_amendments)] != frozen_amendments:
            problems.append("an amendment present at the freeze was edited or removed")
        later = amendments[len(frozen_amendments):]
    elif not frozen_amendments and isinstance(amendments, (dict, list)):
        later = list(amendments.values()) if isinstance(amendments, dict) else amendments
    else:
        problems.append("an amendment present at the freeze was edited or removed")

    chain: dict[str, list[tuple[str, str]]] = {}
    for a in later:
        for f in (a.get("files") if isinstance(a, dict) else None) or []:
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


# Review MINOR-1 on lane gemini-defer (glitch-f1, 22 Oct 2026): Javier's go record for a deferred arm
# (prereg.GO_RECORD) is run output too, so one committed before or with the freeze cannot release the arm.
RUNTIME_PATHS = ("takes.json", "outcomes.json", "rulings.json", "records",
                 "RESULT.md", "cost-calls.json", "COSTS.md", "deferred-arm-go.json",
                 # pre-freeze review 1 (lane pf1-l2b): the original report's published values (MAJOR 10) and the
                 # labelling frame built from the takes (MAJOR 6) are run output too
                 "original-values.json", "labelling/frame.json",
                 # pre-freeze review 2, m8 (lane fold2-ld): the flagged list's verdict record is run output too
                 "labelling/flagged-verdicts.json",
                 # glitch-45's review of fold2/lb, MJ-2: each run of --witness --record, appended on the Mac
                 "witness-record.json")


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


TAKE_LEDGER_FILES = ("takes.json", "outcomes.json", "rulings.json")


def take_ledger_witness(pushes) -> tuple[list[str], list[str], list[str]]:
    """MAJOR 2 of pre-freeze review 2: (problems, the take-ledger commits on HEAD's line, those no push holds).

    `pushes` is [(unix time, pushed sha)] as freeze.push_records returns them. Every pushed sha must be in this clone;
    no pushed commit off HEAD's line may change a take-ledger file (freeze.mirror_problem's shape, for the takes)."""
    rels = [(HERE / f).relative_to(REPO).as_posix() for f in TAKE_LEDGER_FILES]
    shas = sorted({s for _, s in pushes if s and set(s) != {"0"}})
    missing = [s for s in shas if git("cat-file", "-e", f"{s}^{{commit}}")[0] != 0]
    if missing:
        return ([f"{len(missing)} sha(s) the mirror records are not in this clone ({missing[0][:12]} first): fetch "
                 f"the mirror's history before the witness, which reads every pushed commit"], [], [])

    def rev_list(*args):
        code, out = git("rev-list", "--full-history", *args, "--", *rels)
        if code != 0:
            raise ValueError("the take ledger's history cannot be listed")
        return out.split()

    problems = []
    if shas:
        apart = rev_list(*shas, "--not", "HEAD")
        if apart:
            problems.append(f"the mirror holds {len(apart)} commit(s) off HEAD's line that change the take ledger "
                            f"({apart[-1][:12]} first): an abandoned take history (a take registered or run, then "
                            f"reset away and re-run) is refused")
    ledger = rev_list("HEAD")
    # the fold's review (M-1): an abandoned history merged back (`git merge -s ours`) is an ancestor of HEAD, so the
    # check above passes it and takes.read_history's simplified log never reads it; the run line is one first-parent
    # chain, so a ledger commit reached only through a merge's other parent is refused
    code, out = git("rev-list", "--first-parent", "HEAD")
    if code != 0:
        raise ValueError("HEAD's first-parent line cannot be listed")
    line = set(out.split())
    side = [c for c in ledger if c not in line]
    if side:
        problems.append(f"{len(side)} commit(s) that change the take ledger reach HEAD only through a merge "
                        f"({side[-1][:12]} first): a take history merged back from a side line is refused")
    problems += run_line_ledger_problems(rels)
    unwitnessed = rev_list("HEAD", "--not", *shas) if shas else list(ledger)
    return problems, ledger, unwitnessed


def _ledger_rows(commit: str, rel: str):
    """The take-ledger file `rel` at `commit` as its list of records (takes.json's rows), [] when absent, None when
    unreadable."""
    code, text = git("show", f"{commit}:{rel}")
    if code != 0:
        return []
    try:
        doc = json.loads(text)
    except ValueError:
        return None
    if rel.endswith("takes.json"):
        return doc.get("rows") if isinstance(doc, dict) and isinstance(doc.get("rows"), list) else None
    return doc if isinstance(doc, list) else None


def run_line_ledger_problems(rels) -> list[str]:
    """glitch-45's review of fold2/lb, MJ-1 (ruled): on HEAD's first-parent line, no merge commit may touch the take
    ledger (a merge whose first parent is a pushed, abandoned outcome and whose tree resets the ledger read as a clean
    re-run), and each ledger file's state must be append-only against its first parent. The run line takes no
    legitimate merge; one that does must not touch the ledger."""
    code, out = git("log", "--first-parent", "-m", "--reverse", "--format=@%H %P", "--name-only", "HEAD", "--", *rels)
    if code != 0:
        raise ValueError("HEAD's first-parent ledger history cannot be read")
    problems, state = [], {}
    for block in out.split("@")[1:]:
        head, *names = block.split("\n")
        commit, *parents = head.split()
        touched = [n.strip() for n in names if n.strip()]
        if len(parents) > 1:
            problems.append(f"the merge {commit[:12]} on HEAD's first-parent line touches the take ledger "
                            f"({', '.join(touched)}): the run line takes no merge that touches it")
            continue
        for rel in touched:
            old = state[rel] if rel in state else (_ledger_rows(parents[0], rel) if parents else [])
            now = _ledger_rows(commit, rel)
            if old is None or now is None or now[:len(old)] != old:
                problems.append(f"{commit[:12]} changes {rel.rsplit('/', 1)[-1]} other than by appending: the take "
                                f"ledger is append-only against its first parent")
            state[rel] = now
    return problems


WITNESS_RECORD = "witness-record.json"      # glitch-45's review of fold2/lb, MJ-2 (a runtime output, RUNTIME_PATHS)
DISPOSABLE_PLACEHOLDER = "rehearsal or preview"     # freeze.py's rehearsal_record in a disposable rehearsal's freeze


def witness_main(record: bool = False) -> int:
    """check_results.py --witness [--record]: the take ledger against GitHub's push records (MAJOR 2). With --record
    (glitch-45's review, MJ-2: the batch-fetch step on the Mac and the step before publication) each run is appended
    to WITNESS_RECORD, problems and all, so that it ran is on record; it fails closed (exit 1) on any problem."""
    import freeze  # noqa: F401  (witness_reading reads its push records; this line keeps the draft's line citations)
    problems, ledger, unwitnessed = witness_reading()
    print(f"check_results --witness: {len(ledger)} take-ledger commit(s) on HEAD's line, {len(unwitnessed)} "
          f"unwitnessed (no push record holds them)" + (": " + ", ".join(c[:12] for c in unwitnessed)
                                                        if unwitnessed else ""))
    if record:
        from datetime import datetime, timezone
        path = HERE / WITNESS_RECORD
        runs = json.loads(path.read_text()) if path.is_file() else []
        if not isinstance(runs, list):
            raise ValueError(f"{WITNESS_RECORD} is not a list of runs")
        code, head = git("rev-parse", "HEAD")
        runs.append({"at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "head": head,
                     "ledger_head": ledger[0] if ledger else None, "ledger_commits": len(ledger),
                     "unwitnessed": unwitnessed, "problems": problems})
        path.write_text(json.dumps(runs, indent=1) + "\n")
        print(f"check_results --witness: run {len(runs)} appended to {WITNESS_RECORD}; commit it")
    if problems:
        print("check_results --witness: REFUSE: " + "; ".join(problems))
        return 1
    return 0


def witness_publication_problems(pre: dict | None = None) -> tuple[list[str], dict | None]:
    """glitch-45's review of fold2/lb, MJ-2 (ruled): publication (result.py and this file's publication check) refuses
    unless WITNESS_RECORD's latest run is clean, and was taken at HEAD's current ledger head on HEAD's line; returns
    (problems, that run). A disposable rehearsal's freeze (`pre` with the placeholder rehearsal record) reads no push
    records: ([], {"disposable": True})."""
    if pre is not None and pre.get("rehearsal_record") == DISPOSABLE_PLACEHOLDER:
        return [], {"disposable": True}
    # glitch-45's re-check, R-1: the record as HEAD commits it, never the working file
    try:
        rel = (HERE / WITNESS_RECORD).relative_to(REPO).as_posix()
        rels = [(HERE / f).relative_to(REPO).as_posix() for f in TAKE_LEDGER_FILES]
    except ValueError:
        return [f"{WITNESS_RECORD} is not inside this repository, so no committed run can be read"], None
    code, text = git("show", f"HEAD:{rel}")
    try:
        runs = json.loads(text) if code == 0 else []
    except ValueError:
        return [f"{WITNESS_RECORD} at HEAD cannot be read"], None
    if not isinstance(runs, list) or not runs or not isinstance(runs[-1], dict):
        return [f"no run of check_results.py --witness --record is on record ({WITNESS_RECORD}): the push records "
                f"were never read for this publication"], None
    run = runs[-1]
    code, now = git("rev-list", "-1", "--full-history", "HEAD", "--", *rels)
    problems = []
    if run.get("problems"):
        problems.append(f"the latest witness run ({run.get('at')}) refused: " + "; ".join(run["problems"])[:300])
    # R-1: the run's counts recomputed offline at its ledger head: every ledger commit there, and its unwitnessed
    # shas a subset of them (a hand-written clean record with false counts no longer passes)
    at = run.get("ledger_head")
    if isinstance(at, str):
        code, listed = git("rev-list", "--full-history", at, "--", *rels)
        ledger = set(listed.split()) if code == 0 else None
    else:
        ledger = set()
    if ledger is None or run.get("ledger_commits") != len(ledger):
        problems.append(f"the latest witness run counts {run.get('ledger_commits')!r} take-ledger commit(s), and its "
                        f"ledger head holds {'an unreadable number' if ledger is None else len(ledger)}")
    unwitnessed = run.get("unwitnessed")
    if not (isinstance(unwitnessed, list) and ledger is not None and set(unwitnessed) <= ledger):
        problems.append("the latest witness run's unwitnessed shas are not all take-ledger commits at its ledger head")
    if run.get("ledger_head") != (now or None):
        problems.append(f"the latest witness run read the ledger at {str(run.get('ledger_head'))[:12]}, and HEAD's "
                        f"ledger is at {now[:12] or 'none'}: run check_results.py --witness --record again")
    head = run.get("head")
    if not (isinstance(head, str) and git("merge-base", "--is-ancestor", head, "HEAD")[0] == 0):
        problems.append(f"the latest witness run's head {str(head)[:12]} is not on HEAD's line")
    return problems, run


def section_lint_problems(page) -> list[str]:
    """glitch-45's review of fold2/lb, mn-5 (ruled): the m5 section lints, lint_language and lint_pooling
    --section-of, run in the local publication check without --allow-absent (CI may not run), so a published page
    with no round-4 section, or a finding in it, refuses publication."""
    out = []
    for script in ("lint_language.py", "lint_pooling.py"):
        got = subprocess.run([sys.executable, "-B", "-W", "ignore", str(HERE / script), "--section-of", str(page)],
                             capture_output=True, text=True, cwd=str(REPO))
        if got.returncode != 0:
            tail = (got.stdout + got.stderr).strip().splitlines()
            out.append(f"{script} --section-of {Path(page).name} exits {got.returncode}: "
                       + (tail[-1][:200] if tail else "no output"))
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
    # pre-freeze review 2, m2 (lane fold2-lb): every step by name, as the freeze reads it
    problems += [f"the frozen rehearsal record: {p}" for p in freeze.rehearsal_step_problems(lines)]
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


# The order recompute (glitch-45's item 1 after the lane review of fold2/lb, m-1; glitch-45's review, mn-1 and mn-2):
# order_reference.py, a standalone stdlib-only file, recomputes the seed and the order from the frozen file and binds
# the reading to the registered round, chain and time, and prints its own verdict. It runs as `python -I -S`, so no
# study module, and no patch inside one, runs in it. What is not isolated: this process starts it and reads its exit
# code and lines, and this process has imported study modules; the isolated form is the same command run on its own
# (order_reference.py's docstring), which a reviewer or a gate runs directly.
ORDER_REFERENCE_FILE = HERE / "order_reference.py"
ORDER_REFERENCE_ARGV = (sys.executable, "-I", "-S", str(ORDER_REFERENCE_FILE), "-")


def take_order_problems(frozen: dict, draft: dict | None = None) -> list[str]:
    """order_reference.py's problems for `frozen` (the frozen file as a dict) against `draft` (the committed
    prereg-draft.json at HEAD by default; glitch-45's re-check, R-2), run in an isolated interpreter; [] when it exits
    0."""
    import tempfile
    if draft is None:
        code, text = git("show", f"HEAD:{study.rel('prereg-draft.json')}")
        try:
            draft = json.loads(text) if code == 0 else None
        except ValueError:
            draft = None
        if draft is None:
            return ["the committed prereg-draft.json cannot be read at HEAD, so the registered round is unknown"]
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".json") as d:
            d.write(json.dumps({"take_order_beacon": {"round": (draft.get("take_order_beacon") or {}).get("round")}}))
            d.flush()
            got = subprocess.run((*ORDER_REFERENCE_ARGV, d.name), input=json.dumps(frozen), capture_output=True,
                                 text=True, timeout=600)
    except (OSError, subprocess.TimeoutExpired) as e:
        return [f"the take order could not be recomputed ({type(e).__name__})"]
    lines = got.stdout.splitlines()
    found = [ln.split("problem: ", 1)[1] for ln in lines if ln.startswith("order_reference: problem: ")]
    if got.returncode == 0 and not found and any(ln.startswith("order_reference: ok") for ln in lines):
        return []
    return found or [f"the take order could not be recomputed: {(got.stdout + got.stderr).strip()[:200]}"]


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
    order = take_order_problems(frozen)      # the order recomputed in isolation (fold2/lb, glitch-45's item 1)
    print(f"  the take order recomputed from the frozen reading and rows: {len(order)} problem(s)")
    problems += order
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
    recheck = freeze_recheck_problems(frozen, commit, rehearsal_plan) if commit else []
    print(f"  the freeze's gates read again at its commit and its parent: {len(recheck)} problem(s)")
    return problems + rehearsal + held + recheck


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


def original_values_problems(rec: dict, path=None) -> list[str]:
    """Pre-freeze review 1, MAJOR 10 (lane pf1-l2b): once the original report's values are published
    (result.ORIGINAL_VALUES), they never change. The file must hold exactly what the original report's records give
    now, and every committed version of it must be one and the same blob (a later commit that edits it, even one
    later reverted, is refused). Not yet published: nothing to hold, and from_records refuses a follow-up without it."""
    import result
    path = result.ORIGINAL_VALUES if path is None else Path(path)
    rel = path.resolve().relative_to(REPO.resolve()).as_posix()
    if not path.is_file():
        if git("rev-parse", "--verify", "-q", "HEAD")[0] != 0:
            return []                                        # no commit at all: nothing was ever published
        code, ever = git("log", "--format=%H", "--full-history", "-1", "--", rel)
        if code:
            return [f"{path.name}: its commit history cannot be read"]
        # lane review 10: a published file that is gone is refused by name, never read as not yet published
        return [f"{path.name} was committed ({ever[:12]}) and is gone: the original report's values are published "
                f"once and stand"] if ever else []
    out = []
    try:
        held = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return [f"{path.name} is unreadable: {exc}"]
    if held != rec["original_values"]:
        out.append(f"{path.name} differs from the values the original report's records give now: the original "
                   f"report's values stand as published")
    code, commits = git("log", "--format=%H", "--full-history", "--", rel)
    if code:
        return out + [f"{path.name}: its commit history cannot be read"]
    blobs = set()
    for commit in commits.split():
        c, blob = git("rev-parse", f"{commit}:{rel}")
        blobs.add(blob if c == 0 else "deleted")
    if len(blobs) > 1:
        out.append(f"{path.name} has been committed as {len(blobs)} different versions: the original report's "
                   f"values are published once")
    return out


def check_publication(rows, history, records, pre, page, grade, table=None, witness=None):
    import result
    for row in rows:
        takes_mod.require_planned_row(row, pre)
    stats.check_records(records)
    wanted = pipeline().produce(rows, history, grade, table=table)["records"]
    rec = result.from_records(wanted, pre, rows, history, table)
    rendered = result.render(rec) if witness is None else result.render(rec, witness=witness)
    import run_builders   # lane run-launcher, ruling 2: first registrations follow take_order within each launch part
    problems = run_builders.order_problems(rows, pre)
    if not records_equal(records, wanted):
        problems.append("records/ differs from registered, routed and regraded takes")
    if not page_equal(page, rendered):
        problems.append("RESULT.md differs from the complete statistics and committed cell states, including agent")
    problems += original_values_problems(rec)          # MAJOR 10 (lane pf1-l2b)
    problems += tip_limit_problems(pre)                # fold 10's review, m1: a page without the limit, on --ledger too
    return problems


# Fold 9's review, B1 (lane fold10/rehearsal-road; glitch-45's road A ruling, Mon 2 Nov 2026): two blocks of the
# pre-registration pin paths that are not repository-relative. build_draft writes image_locks' paths study-relative and
# config_templates' files as the names take_config renders; they are no files on disk, and two names hold different
# bytes per model. It sits here, past every line of this file the draft cites by number.
import contextlib  # noqa: E402
import io  # noqa: E402
import re  # noqa: E402

IMAGE_LOCK_PIN = re.compile(r"\.image_locks\[\d+\]")
TEMPLATE_PIN = re.compile(r"\.config_templates\.(?P<harness>[^.]+)\.(?P<model>.+)\.files\[\d+\]")


def pinned_bytes(where: str, rel: str):
    """The bytes the pin at document position `where` names, or None when there are none, which check_pins refuses: an
    image lock from the study folder; a template file from take_config's render for that harness and model, exactly as
    build_draft.config_templates renders it (a name the render does not make, or a harness or model it refuses, is
    None, never a dropped pin); any other node from the repository root."""
    template = TEMPLATE_PIN.fullmatch(where)
    if template:
        from box import take_config        # here, so the take road's import of this file does not load it
        harness = template["harness"]
        try:
            return take_config.files_for(harness, model=None if harness == take_config.CLAUDE_CODE
                                         else template["model"]).get(rel)
        except (take_config.Refused, take_config.NotReady):
            return None
    f = (HERE if IMAGE_LOCK_PIN.fullmatch(where) else REPO) / rel
    return f.read_bytes() if f.is_file() else None


# Pre-freeze review 8, M1 (lane fold11/freeze-recheck): the freeze's gates ran once, inside freeze.main, and then the
# operator committed what it wrote by hand, so one edit in that window passed everything above: the frozen file was only
# ever compared with later versions of itself. Here the freeze commit is read again against what it could only have been.
# It sits past every line of this file the draft cites by number.
#
# freeze.main writes every FREEZE_WRITTEN_KEYS member but this one: nothing has ever written it. It is listed so a
# changed-key report may name it, so a frozen file carrying it is a hand edit (frozen_file_problems refuses it).
FREEZE_KEYS_NOT_WRITTEN = ("nulls_at_freeze",)
FREEZE_OUTPUTS = ("prereg.json", "COPIED.json", "COPIED.d/freeze.json")      # freeze.write_outputs, one commit


def committed_raw(rev: str, rel: str) -> bytes | None:
    """The file's exact bytes at `rev`, or None when it is not there (this file's git() strips what it reads, which would
    change every digest)."""
    got = subprocess.run(["git", "-C", str(REPO), "show", f"{rev}:{rel}"], capture_output=True)
    return got.stdout if got.returncode == 0 else None


def committed_pins(rev: str, paths: list[str]) -> list[dict] | str:
    """freeze.pin's record of each path as `rev` commits it, in order, read from git and not from any working tree; or the
    first path `rev` does not hold, by name."""
    listed = subprocess.run(["git", "-C", str(REPO), "ls-tree", "-r", "-z", rev, "--", *paths], capture_output=True)
    if listed.returncode != 0:
        return f"the tree of {rev[:12]}"
    blobs = {}
    for item in listed.stdout.decode("utf-8", "surrogateescape").split("\0"):
        if item:
            meta, path = item.split("\t", 1)
            blobs[path] = meta.split()[2]
    for path in paths:
        if path not in blobs:
            return path
    got = subprocess.run(["git", "-C", str(REPO), "cat-file", "--batch"], capture_output=True,
                         input="".join(blobs[p] + "\n" for p in paths).encode())
    if got.returncode != 0:
        return f"the blobs of {rev[:12]}"
    out, at = [], 0
    for path in paths:
        end = got.stdout.index(b"\n", at)
        size = int(got.stdout[at:end].split()[2])
        body = got.stdout[end + 1:end + 1 + size]
        at = end + 2 + size
        out.append({"path": path, "git_blob_sha": blobs[path], "sha256": hashlib.sha256(body).hexdigest(),
                    "uncommitted": False})
    return out


@contextlib.contextmanager
def freeze_as_of(parent: str):
    """freeze's own review gate reads HEAD, the draft on disk and the PINNED list its import built from COPIED.d, so at
    this file's HEAD it would read the run, not the freeze. Inside this block all three are the parent's. No checkout and
    no write to the repository: a temporary git directory holds only HEAD (the parent) and a `commondir` pointing at the
    real objects, refs, reflogs and config."""
    import tarfile
    import tempfile
    import freeze
    code, common = git("rev-parse", "--git-common-dir")
    if code != 0:
        raise ValueError("the repository's git folder cannot be found")
    common_dir = (REPO / common).resolve()
    with tempfile.TemporaryDirectory(prefix="freeze-as-of-") as tmp:
        root = Path(tmp)
        gitdir = root / ".git"
        gitdir.mkdir()
        (gitdir / "HEAD").write_text(parent + "\n")
        (gitdir / "commondir").write_text(str(common_dir) + "\n")
        draft = root / "prereg-draft.json"
        draft.write_bytes(committed_raw(parent, study.rel("prereg-draft.json")) or b"")
        archive = subprocess.run(["git", "-C", str(REPO), "archive", "--format=tar", parent, "--",
                                  study.rel("COPIED.d")], capture_output=True)
        if archive.returncode != 0:
            raise ValueError(f"COPIED.d cannot be read at {parent[:12]}")
        with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as tar:
            tar.extractall(root, filter="data")
        owned = freeze.owned_paths(folder=root / study.rel("COPIED.d"))
        pinned = [p for p in map(study.rel, owned) if p not in freeze.NOT_PINNED_AND_WHY] + list(freeze.BOUND_OUTSIDE)
        saved = freeze.REPO, freeze.DRAFT, freeze.PINNED
        freeze.REPO, freeze.DRAFT, freeze.PINNED = root, draft, pinned
        try:
            yield freeze
        finally:
            freeze.REPO, freeze.DRAFT, freeze.PINNED = saved


def tip_limit_problems(pre: dict) -> list[str]:
    """Fold 10's review, m1: result.derive's hold, read as a problem by this file's two callers."""
    import result
    try:
        result.tip_limit_held(pre)
    except ValueError as exc:
        return [str(exc)]
    return []


def frozen_file_problems(frozen: dict, draft: dict, parent: str, commit: str, raw_draft: bytes, review_sha: str | None,
                         fz) -> list[str]:
    """The frozen file against what freeze.main writes: its own code, run on the draft and the parent's committed pins,
    given only what cannot be derived again here (the time, the beacon reading, the witness, the rehearsal record, the
    holdout digests, each read on its own elsewhere). This is what keys_outside_the_freeze cannot be: it allows the keys
    FREEZE_FILLED_INSIDE names, which nothing fills, and it zips the two task lists, so a dropped task names no key."""
    import copy
    pins = committed_pins(parent, fz.pinned_paths(fz.PINNED))
    if isinstance(pins, str):
        return [f"{pins} is pinned by the freeze's own list and cannot be read at the freeze's parent"]
    out_bytes = {name: committed_raw(commit, study.rel(name)) for name in FREEZE_OUTPUTS[1:]}
    if None in out_bytes.values():
        return ["the freeze commit does not carry COPIED.json and COPIED.d/freeze.json"]
    try:
        rebuilt = fz.prepare(copy.deepcopy(draft), review=frozen.get("pre_freeze_review_commit"), parent=parent, pins=pins,
                             frozen_at=frozen.get("frozen_at"), beacon=frozen.get("take_order_beacon_reading"))
    except (ValueError, KeyError, TypeError) as exc:
        return [f"freeze.prepare refuses this draft and reading, so the frozen file is not byte for byte what the freeze "
                f"writes: {exc}"]
    rebuilt.update(draft_sha256_at_freeze=hashlib.sha256(raw_draft).hexdigest(),
                   pre_freeze_review_file=frozen.get("pre_freeze_review_file"), pre_freeze_review_sha256=review_sha,
                   rehearsal_record=frozen.get("rehearsal_record"), rehearsed_study_tree_sha256=fz.study_tree_sha(),
                   take_order_witness=frozen.get("take_order_witness"))
    rebuilt.update({k: frozen[k] for k in fz.HOLDOUT_KEYS if k in frozen})
    rebuilt.update(published_tip_residual=fz.PUBLISHED_TIP_LIMIT)
    rebuilt["pinned_files"].extend(fz.generated_pins(out_bytes))
    if fz.json_bytes(rebuilt) == committed_raw(commit, study.rel("prereg.json")):
        return []
    differ = sorted(k for k in set(rebuilt) | set(frozen) if rebuilt.get(k) != frozen.get(k))
    return ["the frozen file is not byte for byte what the freeze's own code writes from the parent's tree; it differs "
            "in " + (", ".join(differ) or "its bytes alone, its keys holding the same values")]


def witness_as_derived_problems(frozen: dict, draft: dict, fz) -> list[str]:
    """take_order_witness, derived again by the freeze's own code from the push stamps the file itself records. GitHub's
    records are read at check_results.py --witness (frozen_network_problems); this binds the rest offline: which commits
    registered the round and last changed the draft, and each stamp's lead before the round."""
    witness = frozen.get("take_order_witness")
    if not isinstance(witness, dict):
        return [f"take_order_witness is {str(witness)[:60]!r}, a disposable rehearsal's: a real freeze holds GitHub's "
                f"push records of the round and the draft"]
    pushes = [(p.get("stamp"), p.get("sha")) for p in witness_pushes(witness)]
    try:
        again = fz.take_order_witness(draft, pushes=pushes)
    except (ValueError, TypeError) as exc:
        return [f"take_order_witness is not what the freeze derives from its own stamps: {exc}"]
    if again != witness:
        return ["take_order_witness is not what the freeze derives from its own stamps"]
    return []


def witness_pushes(witness: dict) -> list[dict]:
    """Every push record a frozen take_order_witness names (freeze.take_order_witness writes these keys)."""
    named = [witness.get("registering_push"), witness.get("draft_push")]
    named += [s.get("swap_push") for s in witness.get("superseded") or [] if isinstance(s, dict)]
    return [p for p in named if isinstance(p, dict)]


def frozen_network_problems(pushes) -> list[str]:
    """Run by check_results.py --witness, the one door here that reads the network (witness_reading). What no offline check
    can hold: the frozen witness's pushes are in GitHub's records, and the frozen beacon reading is the round the relays
    publish. order_reference.py checks the reading's shape, and that its randomness is the sha256 of its signature, and no
    signature is verified, so a hand-written signature gave another seed and another order and passed."""
    import order_beacon
    frozen, _ = frozen_bytes()
    if not isinstance(frozen, dict):
        return []
    out = []
    witness = frozen.get("take_order_witness")
    if isinstance(witness, dict):
        real = {(stamp, sha) for stamp, sha in pushes}
        for push in witness_pushes(witness):
            if (push.get("stamp"), push.get("sha")) not in real:
                out.append(f"the frozen take_order_witness names {str(push.get('sha'))[:12]} at {push.get('stamp')}, and "
                           f"no push record of the mirror holds it")
    else:
        out.append("the frozen take_order_witness is not a witness: no push record stands behind it")
    reading = frozen.get("take_order_beacon_reading")
    try:
        answer = order_beacon.read_relays(reading.get("round"))
    except (order_beacon.BeaconRefused, AttributeError) as exc:
        return out + [f"the frozen beacon reading cannot be read back from the relays: {exc}"]
    if any(reading.get(k) != answer.get(k) for k in ("round", "randomness", "signature")):
        out.append("the frozen beacon reading is not the round the relays publish: the take order was seeded by another "
                   "value")
    return out


def witness_reading() -> tuple[list[str], list[str], list[str]]:
    """witness_main's reading (on one line there because the draft cites this file by number): the take ledger against
    GitHub's push records, and frozen_network_problems."""
    import freeze
    pushes = freeze.push_records()
    problems, ledger, unwitnessed = take_ledger_witness(pushes)
    return problems + frozen_network_problems(pushes), ledger, unwitnessed


def freeze_recheck_problems(frozen: dict, commit: str, rehearsal_plan: bool = False) -> list[str]:
    """At the freeze commit, what freeze.main's gates held. Every read is at the commit or its parent, never HEAD."""
    import build_draft
    import freeze
    parents = git("rev-list", "--parents", "-n", "1", commit)[1].split()[1:]
    want_parent = frozen.get("frozen_at_commit_parent")
    if not parents:
        # AMENDMENT 1's copy (frozen_commit_problems): the battery's sandbox commits its working tree as one root commit,
        # which carries no history to hold. A real publication never can be one.
        print(f"  NOT CHECKED: the freeze commit in this copy ({commit[:12]}) has no parent, so the freeze's gates cannot "
              f"be read again here")
        return [] if rehearsal_plan else [f"the freeze commit {commit[:12]} has no parent: the review, the draft and the "
                                          f"pins it froze cannot be read"]
    if len(parents) != 1:
        return [f"the freeze commit {commit[:12]} has {len(parents)} parents: freeze.py's output is one commit on the "
                f"reviewed line"]
    parent = parents[0]
    if want_parent != parent:
        # frozen_commit_problems reads this difference as a copy without the study's history and prints NOT CHECKED: one
        # edit of this field switched its hold off
        return [f"frozen_at_commit_parent {str(want_parent)[:12]} is not the freeze commit's parent {parent[:12]}"]
    out: list[str] = []
    code, names = git("diff", "--no-renames", "--name-only", parent, commit)
    touched = set(names.splitlines()) if code == 0 else None
    want = {study.rel(p) for p in FREEZE_OUTPUTS}
    if touched != want:
        out.append("the freeze commit changes other paths than freeze.py's three outputs: "
                   + ("unreadable" if touched is None else ", ".join(sorted(touched ^ want))[:300]))
    if committed_raw(commit, study.rel(FREEZE_OUTPUTS[2])) != freeze.json_bytes(freeze.output_fragment()):
        out.append("the freeze commit's COPIED.d/freeze.json is not what freeze.py writes")
    raw_draft = committed_raw(commit, study.rel("prereg-draft.json"))
    if raw_draft is None:
        return out + ["prereg-draft.json is not committed at the freeze commit"]
    if hashlib.sha256(raw_draft).hexdigest() != frozen.get("draft_sha256_at_freeze"):
        out.append("draft_sha256_at_freeze is not the sha256 of prereg-draft.json at the freeze commit: the rehearsal "
                   "record and the review's line 1 bind to it")
    draft = json.loads(raw_draft)
    try:
        outside = freeze.keys_outside_the_freeze(draft, frozen)
    except (KeyError, TypeError, AttributeError) as exc:       # a task's shape it cannot walk: named, never a pass
        outside = [f"unreadable ({type(exc).__name__}: {exc})"]
    if outside:
        out.append("the frozen file changes keys outside the freeze: " + ", ".join(outside)[:400])
    absent = [k for k in freeze.FREEZE_WRITTEN_KEYS if k not in frozen and k not in FREEZE_KEYS_NOT_WRITTEN]
    if absent:
        out.append("the freeze's written keys are absent: " + ", ".join(absent))
    out += tip_limit_problems(frozen)
    out += [p for p in (freeze.draft_holdout_problem(draft), freeze.order_function_problem(draft)) if p]
    review_file = frozen.get("pre_freeze_review_file")
    review = committed_raw(parent, review_file) if isinstance(review_file, str) else None
    review_sha = None
    if review is None:
        out.append(f"pre_freeze_review_file {str(review_file)[:120]} is not committed at the freeze's parent")
    else:
        review_sha = hashlib.sha256(review).hexdigest()
        if review_sha != frozen.get("pre_freeze_review_sha256"):
            out.append(f"pre_freeze_review_sha256 is not the sha256 of {review_file} at the freeze's parent")
        ruling = freeze.read_ruling(review.decode("utf-8", "replace"))
        if ruling != freeze.DO_FREEZE:
            out.append(f"{review_file} at the freeze's parent reads {ruling}, never as freeze approval")
    seed = frozen.get("pre_freeze_review_commit")
    with freeze_as_of(parent) as fz:
        bad, named = fz.review_file_problems(seed if isinstance(seed, str) else "")
        if bad:
            out.append("review_file_problems, re-run as of the freeze's parent: " + "; ".join(bad)[:600])
        elif named != review_file:
            out.append(f"pre_freeze_review_file names another report ({str(review_file)[:120]}) than the seed commit "
                       f"lands ({named})")
        out += frozen_file_problems(frozen, draft, parent, commit, raw_draft, review_sha, fz)
        if not rehearsal_plan:
            out += witness_as_derived_problems(frozen, draft, fz)
    try:
        count = build_draft.validate_digests(frozen.get("holdout_salted_digests"), [t["id"] for t in draft["tasks"]])
        if count != frozen.get("holdout_wordings_per_task_version"):
            out.append(f"the frozen holdout digests hold {count} per task version, and "
                       f"holdout_wordings_per_task_version says {frozen.get('holdout_wordings_per_task_version')!r}")
    except (ValueError, KeyError, TypeError) as exc:
        out.append(f"the frozen holdout digests are refused by the freeze's own validator: {exc}")
    if not rehearsal_plan:
        reading = frozen.get("take_order_beacon_reading")
        if isinstance(reading, dict) and reading.get("signature") == freeze.SYNTHETIC_SIGNATURE:
            out.append("the frozen beacon reading is the rehearsal's synthetic one")
        record = frozen.get("rehearsal_record")
        text = record.get("text") if isinstance(record, dict) else None
        if isinstance(text, str) and hashlib.sha256(text.encode("utf-8")).hexdigest() != record.get("sha256"):
            out.append("the frozen rehearsal record's sha256 is not its text's")
    return out


def _sample_error() -> tuple:
    """labelling/sample.py's SampleError (a missing frame); none in a copy that carries no labelling/."""
    try:
        from labelling import sample
    except ImportError:
        return ()
    return (sample.SampleError,)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--ledger", action="store_true")
    parser.add_argument("--rehearsal-plan", action="store_true",
                        help="disposable rehearsal only; rehearsal evidence is NOT CHECKED")
    parser.add_argument("--witness", action="store_true",
                        help="the take ledger against GitHub's push records of the mirror (network; MAJOR 2)")
    parser.add_argument("--record", action="store_true",
                        help=f"with --witness: append this run to {WITNESS_RECORD} (the batch fetch and publication)")
    args = parser.parse_args(argv)
    if args.record and not args.witness:
        parser.error("--record is read only with --witness")
    if args.witness:
        try:
            return witness_main(record=args.record)
        except ValueError as exc:
            print(f"check_results --witness: REFUSE: {exc}")
            return 1
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
            # glitch-45's review of fold2/lb: MJ-2, the push witness on record at HEAD's ledger; mn-5, the section
            # lints without --allow-absent; neither in a disposable rehearsal, which says so
            witnessed, witness = witness_publication_problems(pre)
            problems += witnessed
            if args.rehearsal_plan or witness == {"disposable": True}:
                print("  NOT CHECKED: the published page's round-4 section (disposable rehearsal)")
            else:
                problems += section_lint_problems(REPO / "docs" / "EVALS.md")
            problems += check_publication(rows, history, records, pre,
                                          page.read_text() if page.is_file() else None,
                                          pipeline().grade_committed, witness=witness)
        if problems:
            print("check_results: REFUSE: " + "; ".join(problems))
            return 1
        print(f"check_results: {len(rows)} rows, {len(records)} records verified" if rows or history or records
              else "check_results: no takes; frozen pins verified, no publication measured")
        return 0
    except (ValueError, KeyError, OSError, *_sample_error()) as exc:    # closure MINOR 3: a missing frame named
        print(f"check_results: REFUSE: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
