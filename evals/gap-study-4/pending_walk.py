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

A pending walk is never graded, never counted as rehearsal coverage (nothing reads a walk's grade as coverage unless it
is graded), and never re-run (its id is registered; a retry is a new walk id). After a reader is registered,
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
