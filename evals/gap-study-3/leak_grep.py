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

import prereg  # noqa: E402
import study  # noqa: E402

ROOTS = ("walks", "transcripts", "rehearsals", "pauses")


def checker():
    """The copied take checker, loaded by path: its readers are the ones that will judge the takes."""
    spec = importlib.util.spec_from_file_location("round3_check_take_for_leak_grep", HERE / "check_take.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sessions() -> list[Path]:
    out: list[Path] = []
    for root in ROOTS:
        base = HERE / root
        if base.is_dir():
            out += sorted(base.rglob("transcript.jsonl"))
    return out


def snippet(ctx: str, word: str, width: int = 90) -> str:
    """The text around the first hit, so a reader can tell furniture from a leak without guessing."""
    m = re.search(rf"\b{re.escape(word.lower())}\b", ctx)
    if not m:
        return ""
    lo = max(0, m.start() - width // 2)
    return "…" + ctx[lo:m.end() + width // 2].replace("\n", " ") + "…"


def derive() -> dict:
    ct = checker()
    pre = prereg.load()
    words = list(pre["leak_words"])
    found = sessions()
    per_word: dict[str, dict] = {w: {"word": w, "sessions_hit": 0, "still_flagged_in": 0, "first": ""}
                                 for w in words}
    per_session = []
    for s in found:
        ctx = ct.context_text(s)
        flagged = {w.lower() for w in ct.context_leaks(ctx, pre)}
        hits = []
        for w in words:
            if not re.search(rf"\b{re.escape(w.lower())}\b", ctx):
                continue
            rec = per_word[w]
            rec["sessions_hit"] += 1
            if not rec["first"]:
                rec["first"] = snippet(ctx, w)
            if w.lower() in flagged:
                rec["still_flagged_in"] += 1
            hits.append(w)
        per_session.append({"session": str(s.parent.relative_to(HERE)),
                            "context_records_bytes": len(ctx),
                            "words_present": sorted(hits),
                            "words_the_checker_would_void_on": sorted(flagged)})
    return {
        "role": "Every pre-registered leak word, grepped against the loaded context of every real session "
                "this study has recorded, through the take checker's own readers.",
        "leak_words": len(words),
        "sessions_read": len(found),
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
              f"through the take checker's own readers.\n")
        for s in rec["per_session"]:
            print(f"  {s['session']:42} context {s['context_records_bytes']:>8} bytes  "
                  f"present {s['words_present']}  WOULD VOID {s['words_the_checker_would_void_on']}")
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
    bad = rec["words_that_would_void_a_session"]
    if bad:
        print(f"\nFAIL {bad} would void a real session. Either the word is this study's own name reaching "
              f"the agent -- a leak to fix -- or it is the harness describing itself, which needs an "
              f"excusal pinned to the phrase it appears in, and that is the owner's ruling to make.")
        return 1
    print(f"\nok: {rec['leak_words']} leak word(s) grepped against {rec['sessions_read']} real session(s); "
          f"none would void one")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
