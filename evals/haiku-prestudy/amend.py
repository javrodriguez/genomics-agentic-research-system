#!/usr/bin/env python3
"""Amend the frozen pre-registration, in the open: before and after, the reason, and the regrade.

    python3 evals/haiku-prestudy/amend.py --write

WHAT AN AMENDMENT MAY BE. The frozen file's own status says a later change is published as `amended`, with before
and after, never corrected in place. Round 2's standard, carried here: an amendment may not touch a grader, a
label, a count, a criterion or the order. This file refuses one that does, by name.

WHAT IT WRITES. The change itself, then an entry in `amendments`: its number, the time, what changed with the
value before and after, why, the evidence, and the regrade -- what re-reading the attempts that already exist
gives under the amended file. The frozen file's body still re-derives from build_draft.py, so the amendment is
made in the builder and in the frozen file together, and the pinned files and the code hash are re-recorded with
their own before and after.

Each amendment is a function below, applied once, by name. Nothing here is a general editor: a change nobody
wrote into this file cannot be made by running it.

No model, no network. stdlib only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
FROZEN = HERE / "prereg.json"
sys.path.insert(0, str(HERE))

NEVER_TOUCHED = ("tasks", "n", "models", "predictions", "take_order", "outcomes", "reserved_labels",
                 "permission_stop_rule", "stopped_take_rule", "driver_change", "system_under_test", "export_at")

EXCUSAL = {
    "phrase": "add a prioritized allowlist to project .claude/settings.json",
    "why": ("Claude Code lists the skills available in a session, and one of those descriptions names its own "
            "permission-prompt feature by the word this study added to its leak words. It is the harness "
            "describing itself, in the same skill listing round 2 excused two phrases from, and it says the same "
            "thing in a session that has nothing to do with this study. The word stays a leak word everywhere "
            "else, and a hit is forgiven only where every occurrence sits inside this phrase."),
}


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def patch_builder() -> None:
    """The same change in build_draft.py, so the amended body still re-derives from the builder."""
    p = HERE / "build_draft.py"
    s = p.read_text()
    a = ('           "transcript_publication", "no_retakes", "driver_decided_reasons", '
         '"driver_decided_reasons_note")')
    b = (a + "\n\n"
         "# AMENDMENT 1: round 2 carried leak_context_excusals; this study adds one excusal to it, so the key is\n"
         "# built from round 2's value plus this list rather than carried.\n"
         "EXCUSALS_ADDED = [" + json.dumps(EXCUSAL, indent=4) + "]")
    if s.count(a) != 1:
        raise SystemExit("refusing: build_draft.py does not carry the line this amendment patches")
    s = s.replace(a, b)
    # The key leaves CARRIED, or the carried loop would write round 2's value back over the amended one.
    a1 = ('           "driver_outcome_shapes", "environment_record", "harness_delivered_user_records", '
          '"leak_context_excusals",\n')
    b1 = ('           "driver_outcome_shapes", "environment_record", "harness_delivered_user_records",\n')
    if s.count(a1) != 1:
        raise SystemExit("refusing: build_draft.py does not carry leak_context_excusals where this amendment "
                         "expects it")
    s = s.replace(a1, b1)
    a2 = '        "leak_words": list(r2["leak_words"]) + LEAK_WORDS_ADDED,'
    b2 = (a2 + "\n"
          '        "leak_context_excusals": [dict(e) for e in r2["leak_context_excusals"]]\n'
          '        + [dict(e) for e in EXCUSALS_ADDED],\n'
          '        "leak_context_excusals_note": ("Round 2\'s two excusals, carried verbatim, plus one this study "\n'
          '                                       "added by amendment 1. The key is no longer in '
          'carried_from_round_2."),')
    if s.count(a2) != 1:
        raise SystemExit("refusing: build_draft.py does not carry the leak_words line this amendment patches")
    p.write_text(s.replace(a2, b2))


def amendment_1(frozen: dict) -> dict:
    """The harness's own skill listing says `allowlist`, and it voided the first take."""
    patch_builder()
    before = [dict(e) for e in frozen["leak_context_excusals"]]
    if any(e["phrase"] == EXCUSAL["phrase"] for e in before):
        raise SystemExit("amendment 1 is already applied")
    after = before + [dict(EXCUSAL)]
    frozen["leak_context_excusals"] = after
    frozen["carried_from_round_2"] = [k for k in frozen["carried_from_round_2"] if k != "leak_context_excusals"]
    frozen["leak_context_excusals_note"] = ("Round 2's two excusals, carried verbatim, plus one this study added "
                                            "by amendment 1. The key is no longer in carried_from_round_2.")
    return {
        "n": 1,
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "what": "leak_context_excusals: one phrase added; leak_context_excusals is no longer a carried key",
        "before": before,
        "after": after,
        "why": ("Take 1 of this cell ran the whole script and reached the probe with no denial, and the take "
                "checker then refused it as a rehearsal for `leak-in-loaded-context`: the word `allowlist`, which "
                "this study added to the leak words when the allowlist became the change, occurs in the session's "
                "loaded context. It is in Claude Code's own listing of the skills available in a session, in the "
                "description of its `fewer-permission-prompts` skill, which is injected into every session on this "
                "machine. Left as it stood, every take of this cell would be refused for the harness's own "
                "furniture and the pre-study would answer nothing. The excusal is the mechanism the frozen file "
                "already carries for this class, and round 2 used it twice for the same listing."),
        "evidence": ("rehearsals/number-fidelity/positive/claude-haiku-4-5-20251001/row-0/transcript.jsonl, "
                     "attachment record 7: '... - fewer-permission-prompts: Scan your transcripts for common "
                     "read-only Bash and MCP tool calls, then add a prioritized allowlist to project "
                     ".claude/settings.json to reduce permission prompts. ...'"),
        "touches": "a leak excusal. No grader, label, count, criterion or order moves.",
        "regrade": ("Re-read under the amended file: row 0's attempt carries no other leak word, so the only "
                    "problem the checker reported is gone. It stays a rehearsal and is never graded -- an attempt "
                    "is routed once, by the checker's verdict at the time it ran -- and its slot is registered "
                    "again within the cap of three, as the pre-registration allows. The regrade is recorded in "
                    "verification/amendment-1-regrade.txt."),
    }


def amendment_2(frozen: dict) -> dict:
    """Row 0's attempt is where the amended checker's verdict puts it: graded."""
    model, task, half = frozen["models"][0], "number-fidelity", "positive"
    src = HERE / "rehearsals" / task / half / model / "row-0"
    dest = HERE / "transcripts" / task / half / model / "1"
    if not src.is_dir():
        raise SystemExit(f"amendment 2: {src} is not there to move")
    if dest.exists():
        raise SystemExit(f"amendment 2: {dest} already holds an attempt")
    dest.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["git", "-C", str(REPO), "mv", str(src), str(dest)], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"amendment 2: git mv refused: {r.stderr.strip()}")
    led = json.loads((dest / "driver-ledger.json").read_text())
    before_attempt = dict(led.get("attempt") or {})
    led["attempt"] = {"kind": "graded", "reasons": [],
                      "amended": "amendment 2: routed as a rehearsal by the checker's verdict before amendment 1, "
                                 "graded by its verdict after it; the bytes of the transcript, the environment "
                                 "record and the scrub record are unchanged."}
    led["transcript"] = f"evals/haiku-prestudy/transcripts/{task}/{half}/{model}/1/transcript.jsonl"
    (dest / "driver-ledger.json").write_text(json.dumps(led, indent=2) + "\n")
    (dest / "WHY.md").unlink(missing_ok=True)
    return {
        "n": 2,
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "what": "row 0's attempt moved from rehearsals/ to transcripts/, and its ledger's attempt record amended",
        "before": {"path": f"rehearsals/{task}/{half}/{model}/row-0", "attempt": before_attempt,
                   "checker": "NOT VALID — [leak-in-loaded-context] the agent's loaded context contains "
                              "['allowlist']"},
        "after": {"path": f"transcripts/{task}/{half}/{model}/1", "attempt": led["attempt"],
                  "checker": "valid — every operator-side check passed"},
        "why": ("Amendment 1 excused the harness's own phrase, and the take checker then passed this attempt, so "
                "the copied ledger check refused the study: a take the checker passes cannot sit under "
                "rehearsals/. The attempt ran the whole frozen script -- both wait-point markers held, the probe "
                "was sent and answered, no denial, the environment record written before the first turn -- and "
                "the only reason it was filed as a rehearsal was a leak word this study itself added and then "
                "excused. It is graded where the amended checker's verdict puts it."),
        "ruling": ("The owner ruled it on 19 September 2026, in the window driving this goal, against the stated "
                   "alternative of discarding the take and re-driving the slot: '1'. It was put to him because "
                   "this take's outcome is the one the pre-registration predicted, so promoting it is the "
                   "flattering direction."),
        "evidence": "verification/amendment-1-regrade.txt, and the take's own transcript and driver ledger",
        "touches": ("where one attempt is filed, and its ledger's attempt record. No grader, label, count, "
                    "criterion or order moves, and no byte of the transcript, the environment record or the scrub "
                    "record is edited."),
        "regrade": ("The ledger check passes after the move (result.py --ledger), and the take reads as it did "
                    "before it: reached the probe, 0 denials, permission mode default. Recorded in "
                    "verification/amendment-2-regrade.txt."),
    }


def amendment_3(frozen: dict) -> dict:
    """The deleted-attempt guard learns what a recorded amendment moved, and refuses everything else."""
    helper = '''

def amended_attempt_paths(pre: dict) -> list[str]:
    """Attempt paths a recorded amendment moved, as repository-relative prefixes (amendment 3).

    The deleted-attempt guard reads history with --no-renames, so a move an amendment records reads there as a
    deletion. An amendment names where the attempt sat; only those paths are forgiven, and each is in the frozen
    file for a reader to check. Any other deletion under the attempt roots still refuses.
    """
    out = []
    for a in pre.get("amendments") or []:
        before = a.get("before")
        if isinstance(before, dict) and before.get("path"):
            out.append("evals/haiku-prestudy/" + before["path"].strip("/"))
    return out
'''
    p = HERE / "take.py"
    s = p.read_text()
    a = ('    deleted = git("log", "--no-renames", "--diff-filter=D", "--name-only", "--format=", "--", '
         '*ATTEMPT_DIRS).split()')
    b = (a + "\n"
         '    amended = amended_attempt_paths(pre)\n'
         '    deleted = [d for d in deleted if not any(d == m or d.startswith(m + "/") for m in amended)]')
    if s.count(a) != 1:
        raise SystemExit("refusing: take.py does not carry the deleted-attempt line this amendment patches")
    s = s.replace(a, b)
    anchor = "def git(*args: str, check: bool = False) -> str:"
    if s.count(anchor) != 1:
        raise SystemExit("refusing: take.py has no place for the helper")
    s = s.replace(anchor, helper.strip("\n") + "\n\n\n" + anchor)
    p.write_text(s)

    p = HERE / "result.py"
    s = p.read_text()
    a = ('''    if deleted:
        out.append(f"an attempt file was deleted in this repository's history ({deleted[:3]}): a graded take may "
                   f"have been removed and its row re-driven")''')
    b = ('''    import take as take_mod
    deleted = [d for d in deleted if not any(d == m or d.startswith(m + "/")
                                             for m in take_mod.amended_attempt_paths(pre))]
''' + a)
    if s.count(a) != 1:
        raise SystemExit("refusing: result.py does not carry the deleted-attempt lines this amendment patches")
    p.write_text(s.replace(a, b))
    return {
        "n": 3,
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "what": "the deleted-attempt guard in take.py and result.py forgives exactly the paths an amendment records",
        "before": "every path ever deleted under transcripts/, rehearsals/ or pauses/ refused the take and the result",
        "after": ("a path a recorded amendment names as where an attempt sat is not read as a deletion; every other "
                  "deletion under those roots still refuses"),
        "why": ("Amendment 2 moved row 0's attempt with git mv, and the guard reads history with --no-renames, so "
                "the move reads there as three deletions under rehearsals/. The guard then refused to start take 2. "
                "It is the guard working on the study's own recorded move: what it lacked is the amendment record. "
                "The forgiven paths come from the frozen file's amendments, so a reader can see each one."),
        "evidence": "take.py refused take 2 on 19 September 2026 with the three deleted paths of amendment 2's move",
        "touches": ("two guards' reading of history. No grader, label, count, criterion or order moves, and no "
                    "attempt is filed differently."),
        "regrade": ("take.py's preflight passes for take 2 and result.py --ledger still passes; a deletion under "
                    "the attempt roots that no amendment records still refuses, which "
                    "TheDeletedAttemptGuardForgivesOnlyAmendments drives."),
    }


def amendment_4(frozen: dict) -> dict:
    """A test's own synthetic input, and one language excusal for a path that reads as a ratio."""
    p = HERE / "test_prestudy.py"
    s = p.read_text()
    a = '        pre = {"pinned_files": real, "driver_change": {"allowed_tools": ["Bash(python3:*)", "Bash(echo:*)"]}}'
    b = ('        # The amendments come from the file in force: binding_problems forgives exactly the attempt paths\n'
         '        # they record (amendment 3), and a synthetic input without them reads the real move as a deletion.\n'
         '        pre = {"pinned_files": real, "driver_change": {"allowed_tools": ["Bash(python3:*)", "Bash(echo:*)"]},\n'
         '               "amendments": in_force().get("amendments") or []}')
    if s.count(a) != 1:
        raise SystemExit("refusing: test_prestudy.py does not carry the synthetic input this amendment patches")
    p.write_text(s.replace(a, b))

    allow = HERE / "language-allowlist.json"
    rec = json.loads(allow.read_text())
    line = '      "path": "transcripts/number-fidelity/positive/claude-haiku-4-5-20251001/1",'
    rec["excused"].append({
        "file": "evals/haiku-prestudy/prereg.json",
        "pattern": "ratio-slash",
        "line_text": line,
        "ruled": "2026-09-19",
        "why": ("Amendment 2 records where the attempt was filed, and the take's folder is named for its take "
                "number, so the path ends `.../claude-haiku-4-5-20251001/1`. The guard reads the model id's date "
                "and the take number across the separator as a `k / n` shape. It is a path this study's own layout "
                "fixes (attempt_layout), not a rate, and the line is pinned exactly, so editing it brings the "
                "finding back."),
    })
    allow.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n")
    return {
        "n": 4,
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "what": "TheResultIsBoundToTheFreeze's synthetic input carries the amendments in force; one language line excused",
        "before": "the test built a pre with no amendments, and the language guard read a take's path as a ratio",
        "after": "the test reads the amendments from the file in force; the path line is excused with its reason",
        "why": ("Amendment 3 made the deleted-attempt guard read the amendments, and the test's synthetic input has "
                "none, so it read amendment 2's recorded move as a deletion and went red: the test's input was "
                "wrong, not the guard. The language guard's ratio rule fired on the path amendment 2 records, "
                "which is a folder named for its take number."),
        "evidence": "the suite's failure on TheResultIsBoundToTheFreeze, and lint_language.py on prereg.json line 770",
        "touches": ("one test's synthetic input and one excused line. No guard is weakened: the guard's own reading "
                    "is unchanged, and the excusal is pinned to the exact line text."),
        "regrade": "the suite passes and the language guard is clean, both recorded in the commit that carries this.",
    }


AMENDMENTS = {1: amendment_1, 2: amendment_2, 3: amendment_3, 4: amendment_4}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--n", type=int, default=1)
    ap.add_argument("--write", action="store_true", required=True)
    args = ap.parse_args()
    if not FROZEN.is_file():
        print("refusing: there is no frozen file to amend")
        return 2
    if subprocess.run(["git", "-C", str(REPO), "status", "--porcelain", "--", "evals/haiku-prestudy"],
                      capture_output=True, text=True).stdout.strip():
        print("refusing: the study has uncommitted changes; an amendment is made on committed bytes")
        return 2
    before_file = sha256_file(FROZEN)
    frozen = json.loads(FROZEN.read_text())
    before_keys = {k: json.dumps(frozen.get(k), sort_keys=True) for k in NEVER_TOUCHED}

    entry = AMENDMENTS[args.n](frozen)

    for k, v in before_keys.items():
        if json.dumps(frozen.get(k), sort_keys=True) != v:
            print(f"refusing: the amendment changes {k}, which an amendment may never touch")
            return 2

    # The builder must still build this body, so the change lives in both, and the pins are re-recorded.
    import importlib

    import build_draft
    importlib.reload(build_draft)
    dc = frozen["driver_change"]
    rebuilt = build_draft.build(dc["approved_by_owner"], dc["approved_at"])
    added = ("status", "frozen_at", "pre_freeze_review_commit", "rehearsal_record", "draft_sha256_at_freeze",
             "code_sha256_at_freeze", "harness_at_freeze", "pinned_files", "amendments")
    body = {k: v for k, v in frozen.items() if k not in added}
    if body != {k: v for k, v in rebuilt.items() if k not in added}:
        print("refusing: build_draft.py does not build this amended body. Amend the builder in the same change, "
              "so the frozen file still re-derives.")
        return 2

    import freeze as fz
    pins_before = dict(frozen["pinned_files"])
    code_before = frozen["code_sha256_at_freeze"]
    frozen["pinned_files"] = {f: sha256_file(HERE / f) for f in fz.PINNED if (HERE / f).is_file()}
    frozen["code_sha256_at_freeze"] = fz.code_sha256()
    entry["pinned_files_changed"] = {f: {"before": pins_before.get(f), "after": frozen["pinned_files"][f]}
                                     for f in frozen["pinned_files"] if pins_before.get(f) != frozen["pinned_files"][f]}
    entry["code_sha256"] = {"before": code_before, "after": frozen["code_sha256_at_freeze"]}
    entry["draft_sha256"] = {"before": frozen["draft_sha256_at_freeze"],
                             "after": hashlib.sha256((json.dumps(rebuilt, indent=2, ensure_ascii=False) + "\n")
                                                     .encode()).hexdigest()}
    frozen["draft_sha256_at_freeze"] = entry["draft_sha256"]["after"]
    frozen.setdefault("amendments", []).append(entry)
    FROZEN.write_text(json.dumps(frozen, indent=2, ensure_ascii=False) + "\n")
    entry["frozen_file_sha256"] = {"before": before_file, "after": sha256_file(FROZEN)}
    print(json.dumps({k: entry[k] for k in ("n", "what", "touches", "code_sha256", "draft_sha256",
                                            "frozen_file_sha256")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
