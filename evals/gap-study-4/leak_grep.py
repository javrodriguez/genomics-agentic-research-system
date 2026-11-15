#!/usr/bin/env python3
"""Every leak word, grepped against real sessions' loaded context, BEFORE the freeze.

    python3 evals/gap-study-3/leak_grep.py            every word, and what it hits
    python3 evals/gap-study-3/leak_grep.py --check    exit 1 if this list would void a real session

WHY THIS RUNS BEFORE THE FREEZE AND NOT AFTER. A leak word is a word that, if the agent was shown it, means
the session was told what it was in -- and the take is void. The list is frozen with the design, so a word
that the HARNESS says of its own accord voids every take that ever runs, and nothing catches it until the
first take is thrown away. The pre-study learned this the expensive way: it added `allowlist` to its list,
Claude Code's own skill listing carries that word while describing its permission feature, and its first
take was voided by the harness describing itself. Round 3's list carries `allowlist` too.

So the list is driven against real sessions before it is frozen, through the take checker's OWN readers --
`context_text` and `context_leaks`, loaded from the copied checker by path. A check that re-implemented
them would be testing a different rule from the one that will judge the takes.

WHAT COUNTS AS A HIT. The same thing the checker counts: a word-boundary match inside the `attachment`
records, which are the channel the environment put in front of the agent, as opposed to what the agent
typed or read out of the repository. An agent that says `eval` because it listed a directory has not been
leaked to, and this file does not say it has.

WHAT A HIT MEANS, AND WHAT IT DOES NOT. A hit here is not proof the word is harness furniture: it may be a
real leak this round has to fix. The two are told apart by reading the record the word appears in, which is
printed with every hit. A word that hits and is furniture needs an excusal pinned to the phrase it appears
in, and that excusal is the owner's to rule rather than this file's to write.

WHERE THE SESSIONS ARE (lane w8a, ruling W8-layout-1; this file moved from lane w1a to lane w8a under ruling
W8A-gap4-1). Round 4's sessions are its records: the walks (rehearsals/<walk>/transcript.jsonl) and the takes
(takes/<slot>/<k>/transcript.jsonl), the roots named once in mode_binding.RECORD_ROOTS and read at their records' top
level (mode_binding.record_transcripts). Round 3's roots (walks/, transcripts/, pauses/) are never written in round 4.

No model, no network, stdlib only. Read-only.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))

import mode_binding  # noqa: E402
import prereg  # noqa: E402
import study  # noqa: E402

ROOTS = mode_binding.RECORD_ROOTS        # W8A: the record roots, named once in mode_binding


def checker():
    """The copied take checker, loaded by path: its readers are the ones that will judge the takes."""
    spec = importlib.util.spec_from_file_location("round3_check_take_for_leak_grep", HERE / "check_take.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sessions(base: Path | None = None) -> list[Path]:
    out: list[Path] = []
    for root in ROOTS:
        out += mode_binding.record_transcripts(HERE if base is None else Path(base), root)
    return out


def snippet(ctx: str, word: str, width: int = 90) -> str:
    """The text around the first hit, so a reader can tell furniture from a leak without guessing."""
    m = re.search(rf"\b{re.escape(word.lower())}\b", ctx)
    if not m:
        return ""
    lo = max(0, m.start() - width // 2)
    return "…" + ctx[lo:m.end() + width // 2].replace("\n", " ") + "…"


VENDOR_HARNESSES = ("codex", "gemini")
# Review 0df1437 MINOR 3 (glitch-f1's ruling): the recorded sessions the take checker's reader refuses, each named with
# why; checked_against refuses when the unread set is any other (build_draft.checked_sessions, unread_problem).
KNOWN_UNREADABLE = {"rehearsals/w-g24": "a turn that timed out: the Gemini native session reader refuses the "
                                        "incomplete interaction (lane vendor-b27/b28's road; w-g24 is graded false)"}


def session_context(ct, s) -> dict:
    """One session's loaded context, as the take checker will read it (glitch-f1's stage W ruling 2, lane
    vendor-settle, Thu 22 Oct 2026): a codex or gemini session (its driver ledger's agent.harness) through
    check_take.vendor_loaded_context_text, the text that harness's settled T-10 reader sweeps; any other session
    through context_text, Claude Code's attachment sweep. {harness, reader, ctx, unreadable}: an unreadable vendor
    session reads "" and names why, never a clean 0."""
    try:
        ledger = json.loads((Path(s).parent / "driver-ledger.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:              # review 0df1437 MINOR 3: never a fall back to context_text
        raise ValueError(f"{Path(s).parent.name}/driver-ledger.json cannot be read ({type(e).__name__}), so the "
                         "session's harness, and so its reader, is unknown") from None
    if not isinstance(ledger, dict):
        raise ValueError(f"{Path(s).parent.name}/driver-ledger.json is not one JSON object")
    harness = (ledger.get("agent") or {}).get("harness")
    if harness not in VENDOR_HARNESSES:
        return {"harness": harness, "reader": "context_text", "ctx": ct.context_text(s), "unreadable": None}
    reader = f"vendor_loaded_context_text ({harness})"
    try:
        return {"harness": harness, "reader": reader, "ctx": ct.vendor_loaded_context_text(s, harness),
                "unreadable": None}
    except Exception as e:  # noqa: BLE001 - a session the reader refuses is named, never read as clean
        return {"harness": harness, "reader": reader, "ctx": "", "unreadable": f"{type(e).__name__}: {str(e)[:200]}"}


# aborted-leak (ask T242, Javier's word pending; glitch-45's road a-prime): a take whose latest committed take ruling
# routes it aborted is read and listed, but left out of the void check, marked NOT_CHECKED. Its end state is already
# not graded, so a leak word in its loaded context changes nothing measured; checking it would only let one aborted
# take refuse the whole draft (the od57-line ship, gate of 9544fbd3: s-0e780d's command_permissions attachment). The
# route is read only through the history loader (takes.read_history: outcomes.json and rulings.json in commit order),
# from the latest take ruling per (slot, attempt); a take with no ruling, or whose latest ruling routes it anywhere
# else, is checked as before.
NOT_CHECKED = "not checked: ruled aborted"
# v3-routed-leak (V3 gate, 14 Nov 2026; Javier's word on the ask): a take whose latest committed history entry
# is its own outcome with state aborted -- routed aborted by the frozen routing table, as agent-reachable-reason
# routes leak-in-loaded-context after the first turn -- is not graded either, so it is read and listed the same
# way, under its own mark. A take with a later ruling is the ruling's (ruled_aborted above), never this one's.
NOT_CHECKED_ROUTED = "not checked: routed aborted"
TAKE_SESSION = re.compile(r"takes/(s-[0-9a-f]{64})/([1-9][0-9]*)")


def take_key(session: str):
    """(slot, attempt) of a take session named takes/<slot>/<k>, else None (a walk)."""
    m = TAKE_SESSION.fullmatch(session) if isinstance(session, str) else None
    return (m.group(1), int(m.group(2))) if m else None


_RULED_ABORTED: dict = {}         # {(the loader, the last history commit): the takes ruled aborted}


def ruled_aborted() -> set:
    """{(slot, attempt)} whose latest committed take ruling routes the take aborted (THE RULINGS, read through
    takes.read_history only)."""
    import batch
    import takes
    from graders import labels4
    paths = [(takes.HERE / p).relative_to(takes.REPO).as_posix() for p in takes.HISTORY_FILES]
    key = (takes.read_history, takes._git_at(takes.REPO, "log", "-1", "--format=%H", "--", *paths).strip())
    if key in _RULED_ABORTED:                      # the history is the commits; the last one touching it names them all
        return set(_RULED_ABORTED[key])
    latest = {}
    for e in takes.read_history():
        if batch.is_ruling(e):
            latest[(e.get("slot"), e.get("attempt"))] = e
    out = {k for k, e in latest.items() if e.get("ruling") == labels4.RULE_ROUTE and e.get("route") == labels4.ABORTED}
    _RULED_ABORTED[key] = frozenset(out)
    return out


_ROUTED_ABORTED: dict = {}        # {(the loader, the last history commit): the takes routed aborted}


def routed_aborted() -> set:
    """{(slot, attempt)} whose latest committed history entry is its outcome, with state aborted (read through
    takes.read_history only; a ruling, of either word, after the outcome takes the take out of this set)."""
    import batch
    import takes
    from graders import labels4
    paths = [(takes.HERE / p).relative_to(takes.REPO).as_posix() for p in takes.HISTORY_FILES]
    key = (takes.read_history, takes._git_at(takes.REPO, "log", "-1", "--format=%H", "--", *paths).strip())
    if key in _ROUTED_ABORTED:
        return set(_ROUTED_ABORTED[key])
    latest = {}
    for e in takes.read_history():
        if batch.is_ruling(e) or batch.is_outcome(e):
            latest[(e.get("slot"), e.get("attempt"))] = e
    out = {k for k, e in latest.items() if batch.is_outcome(e) and e.get("state") == labels4.ABORTED}
    _ROUTED_ABORTED[key] = frozenset(out)
    return out


def unread_problem(rec: dict) -> str | None:
    """None when the unread sessions are exactly KNOWN_UNREADABLE; else why the measurement does not stand."""
    got = sorted(u["session"] for u in rec["sessions_unread"])
    if got != sorted(KNOWN_UNREADABLE):
        return (f"{len(got)} session(s) cannot be read by the take checker's reader ({got[:5]}), not exactly the known "
                f"{sorted(KNOWN_UNREADABLE)}: the leak list was not grepped against them")
    return None


def derive() -> dict:
    ct = checker()
    pre = prereg.load()
    words = list(pre["leak_words"])
    found = sessions()
    per_word: dict[str, dict] = {w: {"word": w, "sessions_hit": 0, "still_flagged_in": 0, "first": ""}
                                 for w in words}
    per_session, unread = [], []
    aborted = ruled_aborted() if found else set()
    routed = routed_aborted() if found else set()        # v3-routed-leak
    for s in found:
        read = session_context(ct, s)
        ctx = read["ctx"]
        flagged = {w.lower() for w in ct.context_leaks(ctx, pre)}
        session = str(s.parent.relative_to(HERE))
        skipped = take_key(session) in aborted           # aborted-leak: read and listed, never counted as voided
        routed_skip = not skipped and take_key(session) in routed     # v3-routed-leak: the same, its own mark
        hits = []
        for w in words:
            if not re.search(rf"\b{re.escape(w.lower())}\b", ctx):
                continue
            rec = per_word[w]
            rec["sessions_hit"] += 1
            if not rec["first"]:
                rec["first"] = snippet(ctx, w)
            if w.lower() in flagged and not skipped and not routed_skip:
                rec["still_flagged_in"] += 1
            hits.append(w)
        entry = {"session": session,
                 "context_records_bytes": len(ctx),
                 "words_present": sorted(hits),
                 "words_the_checker_would_void_on": sorted(flagged)}
        if skipped:
            entry["leak_check"] = NOT_CHECKED
        elif routed_skip:
            entry["leak_check"] = NOT_CHECKED_ROUTED
        if read["harness"] in VENDOR_HARNESSES:                    # stage W: which reader read it, and any refusal
            entry.update(harness=read["harness"], reader=read["reader"], context_unreadable=read["unreadable"])
        if not ctx:                                                 # review 0df1437 MINOR 3: 0 characters is unread
            unread.append({"session": entry["session"], "why": read["unreadable"] or "0 characters read"})
        per_session.append(entry)
    return {
        "role": "Every pre-registered leak word, grepped against the loaded context of every real session "
                "this study has recorded, through the take checker's own readers.",
        "leak_words": len(words),
        "sessions_found": len(found),
        "sessions_read": len(found) - len(unread),
        "sessions_unread": unread,
        "words_present_in_some_session": sorted(w for w, r in per_word.items() if r["sessions_hit"]),
        "words_that_would_void_a_session": sorted(w for w, r in per_word.items()
                                                  if r["still_flagged_in"]),
        "per_word": [per_word[w] for w in words if per_word[w]["sessions_hit"]],
        "per_session": per_session,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    rec = derive()
    if args.json:
        print(json.dumps(rec, indent=2))
    else:
        print(f"{rec['leak_words']} leak word(s), read against {rec['sessions_read']} recorded session(s) "
              f"({len(rec['sessions_unread'])} unread: {[u['session'] for u in rec['sessions_unread']]}) "
              f"through the take checker's own readers.")
        # pre-freeze review 1, NIT (lane pf1-l4a, 25 Oct 2026): each session the list was not grepped against is named
        # with its reason, so the gap is printed, not silent.
        for u in rec["sessions_unread"]:
            print(f"  not grepped: {u['session']} ({KNOWN_UNREADABLE.get(u['session'], 'not a known unreadable')}; "
                  f"the reader: {u['why']})")
        print()
        for s in rec["per_session"]:
            print(f"  {s['session']:42} context {s['context_records_bytes']:>8} bytes  "
                  f"present {s['words_present']}  WOULD VOID {s['words_the_checker_would_void_on']}"
                  + (f"  ({s['leak_check']})" if "leak_check" in s else ""))
        if rec["per_word"]:
            print("\nwords present in some session's loaded context:")
            for w in rec["per_word"]:
                print(f"  {w['word']:22} in {w['sessions_hit']} session(s), "
                      f"{w['still_flagged_in']} of them would be voided")
                if w["first"]:
                    print(f"      {w['first'][:170]}")
    if rec["sessions_read"] == 0:
        # An empty gate is said out loud: with no session recorded, this has grepped nothing.
        print("\nok, having read 0 sessions: none is recorded yet, so this list has been grepped against "
              "nothing and its green says nothing. Not a pass for the freeze.")
        return 1 if args.check else 0
    problem = unread_problem(rec)
    if problem:
        print(f"\nFAIL {problem}")
        return 1
    bad = rec["words_that_would_void_a_session"]
    if bad:
        print(f"\nFAIL {bad} would void a real session. Either the word is this study's own name reaching "
              f"the agent -- a leak to fix -- or it is the harness describing itself, which needs an "
              f"excusal pinned to the phrase it appears in, and that is the owner's ruling to make.")
        return 1
    unread = len(rec["sessions_unread"])
    print(f"\nok: {rec['leak_words']} leak word(s) grepped against {rec['sessions_read']} real session(s); "
          f"none would void one" + (f"; {unread} session(s) not grepped (unreadable, named above)" if unread else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
