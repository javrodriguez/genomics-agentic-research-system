"""Live harness: the acceptance-walk road's records for a vendor walk whose native cross-check is pending.

Registration review finding 2 (glitch-06, 14 Oct 2026): while no native-session reader is registered, every Gemini
(and later Codex) drive stops with drive.NativeCrossCheckPending (departure D-INT-1), and the walk runner used to hold
any walk whose drive raised, so no vendor walk could ever be committed, and registration (which needs one) could never
be reached by real evidence. Now such a walk is committed through WalkRepo with every record it made, and with:

  check.json   check_doc(): {"walk", "status": "pending-native-reader", "why": the driver ledger's own pending why}
               in place of the checker's reading (the checker never ran: the driver stops before it);
  grade.json   status(): {"graded": false, "status": "pending-native-reader", "why": "not graded, because ..."}, which
               run.grade_walk returns for a ledger whose cross_check_status is pending, so run.walk_problems regrades it
               to the same bytes.

A pending walk is never graded, never counted as rehearsal coverage (walk_plan's and fixture_walk's coverage count a
walk only when it is graded true or superseded by a verified graded-true regrade: coverage_status), and never re-run (its id is registered; a retry is a new walk id). After a reader is registered,
walk_regrade.py re-derives its cross-check and grade from the committed bytes into rehearsals/<walk>/regrade.json, a
new superseding record; the walk's own commit and records are never touched.

Both documents are derived from the driver ledger alone, so the registration road re-derives them byte for byte.
"""
from __future__ import annotations

PENDING = "pending-native-reader"
PENDING_STATUS_KEYS = ("status", "why")


def _pending(ledger):
    s = ledger.get("cross_check_status") if isinstance(ledger, dict) else None
    if isinstance(s, dict) and set(s) == set(PENDING_STATUS_KEYS) and s["status"] == "pending" \
            and isinstance(s["why"], str) and s["why"]:
        return s
    return None


def status(ledger):
    """grade.json's document for a walk whose driver ledger records a pending native cross-check, else None."""
    s = _pending(ledger)
    if s is None:
        return None
    return {"graded": False, "status": PENDING, "why": f"not graded, because its native cross-check is pending: "
                                                       f"{s['why']}"}


def check_doc(walk: str, ledger) -> dict:
    """check.json's document for a pending walk; ValueError when the ledger records no pending cross-check."""
    s = _pending(ledger)
    if s is None:
        raise ValueError("the driver ledger records no pending native cross-check: not a pending walk")
    return {"walk": walk, "status": PENDING, "why": s["why"]}


def _regrade_state(base, walk: str):
    """A regrade's standing for coverage: "graded" when its bytes re-derive (walk_regrade.regrade_doc from the walk's
    committed bytes) and it grades the walk; "refused" when they re-derive and it does not (its native cross-check
    refused); None when there is none or it does not re-derive (an error included): it then supersedes nothing."""
    import walk_regrade
    from pathlib import Path
    path = Path(base) / walk / walk_regrade.REGRADE_FILE
    if not path.is_file():
        return None
    try:
        doc = walk_regrade.regrade_doc(walk, Path(base).parent)
        if walk_regrade.regrade_bytes(doc) != path.read_bytes():
            return None
    except Exception:  # noqa: BLE001 - an unverifiable regrade supersedes nothing, fail closed
        return None
    return "graded" if doc.get("graded") is True else "refused"


def coverage_status(base, walk: str):
    """Batch-8 fix ruling (glitch-06, 14 Oct 2026; CP6: "Every walk is graded but never counted"): None when the walk
    counts as coverage, else why not. A walk covers its spec only when its grade.json is graded true and its check.json
    passes checker_standing (BOOTSTRAP B5: no constant-bound checker reason, checked under the constants in force), or
    when it is a pending walk that a verified graded-true regrade supersedes (the checker never ran on it). Fail closed: a missing or unreadable grade.json, an
    ungraded walk, a pending walk, and a pending walk whose verified regrade refused are each reported, never counted."""
    import json
    from pathlib import Path
    try:
        grade = json.loads((Path(base) / walk / "grade.json").read_bytes())
    except (OSError, ValueError):
        return "grade unreadable"
    if not isinstance(grade, dict):
        return "grade unreadable"
    if grade.get("graded") is True:
        return checker_standing(base, walk)
    if grade.get("status") == PENDING:
        state = _regrade_state(base, walk)
        return None if state == "graded" else "regrade refused" if state == "refused" else "pending"
    return "not graded"


CHECK_KEYS = ("walk", "checked", "checker_reasons", "events", "route", "route_refused", "checker_constants_sha256")


def checker_standing(base, walk: str):
    """BOOTSTRAP B5 (glitch-6b's first-walk bootstrap ruling, 15 Oct 2026; required, or the falsifier argument fails):
    None when a graded walk's check.json lets it count, else why not. A walk is graded whenever its first agent turn
    ran, whatever its checker reasons; a walk whose checker named a reason a CHECKER_CONSTANTS value decides
    (check_take.CONSTANT_BOUND_REASONS) is never counted, and neither is one checked under constants other than those
    in force (its check.json's checker_constants_sha256): it reads stale until it is regraded. Fail closed: a missing
    or unreadable check.json, one not exactly walk_runner.check_record's keys, one the checker did not run on, one whose
    routing refused, and one with a reason that is not a string of routing.json's operator_reasons (the pre-registered
    rehearsal_reasons) are "check unreadable"; constants still PENDING are reported too."""
    import json
    from pathlib import Path
    import check_take
    try:
        check = json.loads((Path(base) / walk / "check.json").read_bytes())
    except (OSError, ValueError):
        return "check unreadable"
    if not isinstance(check, dict) or set(check) != set(CHECK_KEYS) or check.get("checked") is not True \
            or check.get("route_refused") is not None or not isinstance(check.get("route"), str) \
            or not isinstance(check.get("checker_reasons"), list):
        return "check unreadable"
    events = check["events"]              # review NIT B: exactly what agent_adapter.harness_records writes
    if not (isinstance(events, dict) and set(events) == {"outside_reach"} and type(events["outside_reach"]) is int
            and events["outside_reach"] >= 0):
        return "check unreadable"
    latest = latest_recheck(base, walk)      # the recheck-coverage ruling (glitch-6b, 15 Oct 2026)
    if isinstance(latest, str):
        return latest
    if latest is not None:
        check = dict(check, checker_reasons=latest["checker_reasons"],
                     checker_constants_sha256=latest["checker_constants_sha256"])
    import routing                        # review MINOR 2: every reason a str of the pre-registered vocabulary
    vocabulary = routing.load_table()["operator_reasons"]
    if not isinstance(check["checker_reasons"], list) or \
            not all(isinstance(r, str) and r in vocabulary for r in check["checker_reasons"]):
        return "check unreadable"
    bound = [r for r in check["checker_reasons"] if r in check_take.CONSTANT_BOUND_REASONS]
    if bound:
        return f"constant-bound checker reason: {', '.join(bound)}"
    try:
        now = check_take.checker_constants_sha256()
    except check_take.CheckRefused:
        return "the checker constants in force are PENDING"
    if check.get("checker_constants_sha256") != now:
        return "stale: checked under other checker constants; regrade it"
    return None


def latest_recheck(base, walk: str):
    """The recheck-coverage ruling (glitch-6b, 15 Oct 2026): the walk's LATEST recheck entry in the register, read with
    no git and no process (walk_plan's register-only road, P7), only the register and the recheck file opened. None
    when the register names none; the recheck file's {checker_reasons, checker_constants_sha256} when the file is
    there, is the bytes the entry names (sha256) and carries the entry's digest; else why the walk counts nothing
    (a str). Whether the recheck matches a fresh checker run on committed bytes is walk_regrade.py --check's, in
    checks.d, never run here."""
    import hashlib
    import json
    from pathlib import Path
    import walk_register
    try:
        reg = json.loads((Path(base) / walk_register.REGISTER_NAME).read_bytes(),
                         object_pairs_hook=walk_register.no_duplicate_keys)
    except FileNotFoundError:
        return None                       # no register here (a bare folder of walk records): nothing supersedes
    except (OSError, ValueError, walk_register.DuplicateKey):
        return "register unreadable"
    entries = [e for e in walk_register.rechecks_of(reg) if isinstance(e, dict) and e.get("walk") == walk]
    if not entries:
        return None
    e = entries[-1]
    if not isinstance(e.get("file"), str) or walk_register.RECHECK_FILE.fullmatch(e["file"]) is None:
        return "recheck entry unreadable"
    try:
        raw = (Path(base) / walk / e["file"]).read_bytes()
    except OSError:
        return f"recheck file missing: {e['file']}"
    if hashlib.sha256(raw).hexdigest() != e.get("sha256"):
        return f"recheck file differs from its register entry: {e['file']}"
    try:
        doc = json.loads(raw, object_pairs_hook=walk_register.no_duplicate_keys)
    except (ValueError, walk_register.DuplicateKey):
        return "recheck unreadable"
    if not isinstance(doc, dict) or doc.get("checker_constants_sha256") != e.get("checker_constants_sha256") \
            or doc.get("walk") != walk \
            or type(doc.get("n")) is not int or type(e.get("n")) is not int or doc["n"] != e["n"]:
        return f"recheck file does not carry its register entry's walk, ordinal and digest: {e['file']}"
    return {"checker_reasons": doc.get("checker_reasons"), "checker_constants_sha256": doc["checker_constants_sha256"]}


def uncounted_walks(base, walks) -> dict:
    """{walk id: why it is not counted} for the walk ids of `walks` under the rehearsals folder `base`; walk_plan's and
    fixture_walk's coverage never count them."""
    return {w: why for w in walks if isinstance(w, str) for why in (coverage_status(base, w),) if why is not None}
