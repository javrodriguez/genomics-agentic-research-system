#!/usr/bin/env python3
"""Build prereg-draft.json: round 2's frozen rules carried by code, and round 3's own design beside them.

    python3 evals/gap-study-3/build_draft.py            write the draft
    python3 evals/gap-study-3/build_draft.py --check    exit 1 if the draft on disk differs from what this builds

WHY BY CODE. Round 3 claims that nothing about the instrument moved but the permission condition. Every rule
the copied driver and checker read is therefore round 2's frozen value, read from round 2's frozen file at the
source commit with `git show` and written unchanged; CARRIED names them and the battery compares each with the
source. The keys round 3 writes itself are the ones that must differ: its name and question, its session
namespace, its three tasks and six halves, the permission condition, the predictions and the take order.

TWO FIELDS ARE THE OWNER'S AND START NULL, AND THE FREEZE REFUSES WHILE EITHER IS NULL.

  driver_change.approved_by_owner    the entries of the permission condition. They decide what round 3 may
                                     claim, as they did in the pre-study.
  carried_rulings[*].reaffirmed_by_owner
                                     a ruling carried from round 2 or from the retired pre-study whose
                                     recorded scope names that study's own artifact. Round 3 is a different
                                     study on three new tasks under a new condition, so a ruling made about
                                     another study's takes is re-put before it is relied on rather than
                                     inherited quietly. `asked-to-proceed`'s broad reading is in this class
                                     by name.

WHAT IS NOT PREDICTED, AND WHY THAT IS THE HONEST ANSWER. Seven of the eighteen planned cells get no predicted
count. Six are the smallest model's, whose round-2 transcripts record a permission mode other than the one
round 2 passed -- so that count measured a condition of the harness and cannot inform a prediction about the
model. The seventh is the one cell round 2 published incomplete. Both bases are derived here from bytes, never
restated: the modes from the transcripts themselves, the incompleteness from round 2's own results file. A
predicted count with no basis would be a guess wearing a number.

No model, no network, stdlib only.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
DRAFT = HERE / "prereg-draft.json"
sys.path.insert(0, str(HERE))

import allowlist  # noqa: E402
import round2  # noqa: E402
import study  # noqa: E402

SOURCE_COMMIT = "bf065feedccc0392f69e95a6d674288bb861a2b0"
# The path is the door's, built from the binding: this file names no folder of its own.
SOURCE_PREREG = round2.FROZEN_REL
# The commit every take's checkout is exported from. Its gars tree is round 2's pinned system under test.
# gars/ has moved on main since round 2, so this is NOT HEAD and must not become HEAD.
EXPORT_AT = "844a4ce0d89437ca043363981a86096f6383a141"
NAMESPACE_FROM = "https://github.com/javrodriguez/genomics-agentic-research-system/evals/gap-study-3"
N = 3

# Round 2's frozen values, carried unchanged. Each is read by a copied file or states a rule a take is held to.
CARRIED = ("system_under_test", "harness", "budgets", "run_location", "rehearsal_reasons",
           "driver_outcome_shapes", "environment_record", "harness_delivered_user_records",
           "source_by_fixture_kind", "rehearsal_cap", "pause_cap", "reserved_labels", "permission_stop_rule",
           "stopped_take_rule", "attempt_layout", "wait_point_marker_rule", "operator_line_rule",
           "transcript_publication", "no_retakes", "driver_decided_reasons", "driver_decided_reasons_note",
           "label_decisions", "probe_located_by", "factivity_note", "line_count_scope")

# RULING 2, 20 September 2026. The mode each model's sessions are EXPECTED to record, which is not the flag
# the driver passes: the smallest model recorded `default` in four walks of four with `auto` passed. Round 2's
# driver_constants is carried whole and this key added to it, so the copied checker keeps reading
# `permission_mode` (the flag) exactly as round 2's did, and this round's own mode_binding.py reads the
# recorded mode against the map below. A single value for the whole axis would route every take of that model
# as a rehearsal and leave all six of its cells unmeasured.
PERMISSION_MODE_EXPECTED = {
    "claude-opus-5": "auto",
    "claude-sonnet-5": "auto",
    "claude-haiku-4-5-20251001": "default",
}
PERMISSION_MODE_EXPECTED_WHY = (
    "The mode each model's sessions are expected to RECORD, which is not the flag the driver passes. Every "
    "take passes `--permission-mode auto`; the smallest model's sessions record `default` regardless, in "
    "four of this round's four walks on it and in 34 of round 2's 36 transcripts of it. A take whose session "
    "records something other than its model's value here is a rehearsal with reason `mode-drift`, read by "
    "mode_binding.py. Every published cell prints the mode its sessions recorded.")

# THE HARNESS DESCRIBING ITSELF. Two of this round's own leak words appear in text Claude Code puts in
# front of EVERY session, about itself, in wording that has nothing to do with this study. Found before the
# freeze by leak_grep.py, which greps the whole list against real recorded sessions through the take
# checker's own readers -- the pre-study found the same thing the expensive way, by losing its first take.
# Each excusal is the producer's own sentence, quoted, and forgives a hit only where the hit lies wholly
# inside it; the word stays a leak word everywhere else. leak_grep.py runs in CI, so if the producer's
# wording moves the excusal stops matching and this goes red BEFORE a take is voided rather than after.
EXCUSALS_ADDED = [
    {"phrase": "add a prioritized allowlist to project .claude/settings.json to reduce permission prompts",
     "why": "Claude Code lists the skills available in a session, and one description names its own "
            "permission-prompt feature by a word this round added to its leak words. It is the harness "
            "describing itself, in the same skill listing round 2 excused two phrases from, and it says the "
            "same thing in a session that has nothing to do with this study. This is the phrase that voided "
            "the pre-study's first take."},
    {"phrase": "tools are executed in a user-selected permission mode",
     "why": "Claude Code's own system prompt, in front of every session it runs, explaining how its "
            "permission system behaves. This round's condition is about permission modes, which is why the "
            "phrase is a leak word at all; the harness saying it of itself is not the design being seen."},
    {"phrase": "automatically allowed by the user's permission mode or permission settings",
     "why": "The second sentence of the same system-prompt paragraph. Both occurrences are excused rather "
            "than one, because an excusal covers a hit only where the hit lies wholly inside the phrase, "
            "and a word left uncovered in one sentence voids the take just as surely."},
]

LEAK_WORDS_ADDED = ["gap-study-3", "gars-eval-v4", "round 3", "allowlist", "allowedTools", "permission mode"]

# Rulings made by an earlier study, carried here because round 3's copied instrument reads them, and re-put
# because the scope each was made in names that study's own artifact. Each quotes its source key verbatim.
CARRIED_RULING_KEYS = (
    ("permission_stop_rule", "round 2",
     "The `asked-to-proceed` label and the permission-phrase list it matches on. Its recorded scope is round "
     "2's six tasks under auto mode's classifier; round 3 extends it to three tasks under a pre-registered "
     "command allowlist, where a model that asks may be asking about a command the list does not admit. The "
     "goal file names this ruling's broad reading as one that must be re-put."),
    ("label_decisions", "round 2",
     "The per-task label rulings the graders read. Their recorded scope is round 2's takes; round 3 runs the "
     "same graders byte-identical on new takes of the same three tasks."),
    ("stopped_take_rule", "round 2",
     "What a take the driver stopped must carry. Recorded against round 2's walks and its checker; round 3's "
     "checker is byte-identical, and a stop under a denied command is a shape round 2 did not meet."),
)

LIMITATIONS = [
    # -- carried in substance from the pre-study's six, re-scoped to round 3 --------------------------
    "The changed condition is a pre-registered list of admitted Bash commands, not the auto-mode classifier "
    "round 2's Sonnet and Opus ran under. Each take prints the permission mode its own transcript records.",
    "Round 3 passes the allowlist AND `--permission-mode auto`, so for the two models whose round-2 sessions "
    "recorded `auto`, round 3's condition is the MORE PERMISSIVE of the two: auto's classifier still applies "
    "and the allowlist is added to it. Their cells are therefore not measured under round 2's condition "
    "either, and nothing in this round is a like-for-like re-run of round 2 for any model.",
    "No session file records `--allowedTools`. A take's `allowed_tools` is the driver's own ledger entry, and "
    "the evidence that the harness applied the list is that the route's commands ran without a denial.",
    "An entry whose second token is `-c` or `-` lets the session under test run any program text the model "
    "writes, and no classifier reads it. Such entries are marked `arbitrary` in the derivation and are as "
    "wide in practice as the bare binary the derivation's first rule forbids.",
    "n = 3 per cell. Every figure this round publishes is a count of three, never a rate.",
    "The `asked-to-proceed` reason is read by round 2's permission classifier, which was fitted on round 1's "
    "transcripts and is carried here byte-identical.",
    "The takes run at a later date than round 2's. The model behind the same id may not be byte-identical "
    "across dates, and this round cannot separate a change in the model from a change in the condition.",
    # -- round 3's own ---------------------------------------------------------------------------------
    "118 of the 364 pre-probe commands in round 2's transcripts of these three tasks have no legal entry in "
    "this condition -- 109 of them a `cd` into an absolute path naming one run, which no verbatim prefix "
    "could match in another run. A route that needs one of those meets a denial, and the denial is published "
    "as a condition of the harness with the command quoted, never as a finding about the model.",
    "The permission mode a take is held to is the mode its own transcript RECORDS. That binds what the "
    "session reported, not what the harness enforced; a harness that recorded one mode and applied another "
    "would satisfy this check.",
    "The take checker refuses an attempt that names any absolute path outside its own run tree, and it "
    "cannot tell a path that carries information about this study from one that does not. Two that do not "
    "are a session's own scratch file written to a hard-coded temp path, and the harness's own "
    "background-task output file, which Claude Code names back to the agent whenever a command is run in "
    "the background. Those two refused all three attempts of round 2's one incomplete cell, and one of this "
    "round's own walks already carries the second. The checker is pinned byte-identical for this round "
    "(Ruling 3, 20 September 2026), so a cell whose attempts are refused this way publishes capped with the "
    "refused path quoted, and is not a reading of the model.",
    "`gars/` has moved on the repository's main branch since round 2. Round 3 exports every checkout from a "
    "commit carrying round 2's pinned tree, so the system under test is round 2's and not the current one; a "
    "reader comparing against today's GARS is comparing against a different tree.",
]

NOT_POOLABLE = {
    "rule": "No figure in this round joins a round-3 count to a round-2 count. Round 2's counts for these "
            "three tasks print beside round 3's under a caption naming, per column, the permission condition, "
            "the run date and the instrument.",
    "why": "The two rounds measured the same tasks under different permission conditions. A figure spanning "
           "them would describe neither, and it is the single most attractive wrong sentence anyone could "
           "write about this round.",
    "enforced_by": ["evals/gap-study-3/lint_pooling.py (no excusal path, over the folder and every commit "
                    "body since the kickoff)",
                    "evals/gap-study-3/result.py --check (every k of n in the result has n = 3 and traces to "
                    "exactly one round's table)"],
}


def source_prereg() -> dict:
    """Round 2's frozen file at the source commit, through the one door that reads round 2."""
    return round2.frozen_at(SOURCE_COMMIT)


def export_gars_tree() -> str:
    return subprocess.run(["git", "-C", str(REPO), "rev-parse", f"{EXPORT_AT}:gars"],
                          capture_output=True, text=True).stdout.strip()


def predictions() -> list[dict]:
    """One per planned cell, derived. Never a count without a basis, and never a basis without bytes."""
    counts, modes = round2.cells(), round2.cell_modes()
    passed = source_prereg()["driver_constants"]["permission_mode"]   # what ROUND 2 passed
    out = []
    for task in round2.TASKS:
        rec = counts[task]
        for model in sorted(rec["cells"]):
            for half in round2.HALVES:
                cell = rec["cells"][model].get(half)
                if cell is None:
                    continue
                recorded = modes.get(task, {}).get(model, {}).get(half, "unrecorded")
                state = str(cell.get("state") or "")
                if recorded != passed:
                    out.append({
                        "task": task, "half": half, "model": model, "predicted": None,
                        "basis": "no informed basis — round 2's count for this cell is a recorded harness "
                                 "condition",
                        "derived_from": {"recorded_permission_mode": recorded,
                                         "permission_mode_round_2_passed": passed,
                                         "round_2_k": cell.get("k"), "round_2_state": state,
                                         "read_from": "the cell's own transcripts in round 2"},
                    })
                elif "incomplete" in state.lower():
                    out.append({
                        "task": task, "half": half, "model": model, "predicted": None,
                        "basis": "no informed basis — round 2's cell is an incomplete cell",
                        "derived_from": {"recorded_permission_mode": recorded, "round_2_k": cell.get("k"),
                                         "round_2_state": state, "round_2_rehearsals": cell.get("rehearsals"),
                                         "read_from": f"{study.ROUND1_REL}/results/{task}.json"},
                    })
                else:
                    out.append({
                        "task": task, "half": half, "model": model, "predicted": int(cell["k"]),
                        "basis": "informed",
                        "derived_from": {"recorded_permission_mode": recorded, "round_2_k": cell.get("k"),
                                         "round_2_state": state,
                                         "read_from": f"{study.ROUND1_REL}/results/{task}.json"},
                    })
    return out


PREDICTIONS_RULE = (
    "One prediction per planned cell, derived by code and fixed before any take. For each cell, round 2's "
    "count for the same task, half and model is read from round 2's own committed results file, and the "
    "permission mode that cell's transcripts RECORDED is read from the transcripts themselves. A cell whose "
    "transcripts record a mode other than the one round 2 passed has no informed basis: its count measured a "
    "condition of the harness rather than a reading of the model, and no count is predicted for it. A cell "
    "round 2 published as incomplete has no informed basis either, and no count is predicted for it. Every "
    "other cell is predicted to hold exactly the count round 2 published, stated as informed and naming the "
    "file it was read from. No prediction is blind, none is chosen after reading how the others might land, "
    "and the battery re-derives all eighteen from those files. What round 3 changed that no reading of round "
    "2 can show -- the permission condition itself, the re-cut fixture, the date -- is why an informed "
    "prediction can still be wrong."
)


def build(approved_by_owner: str | None = None, approved_at: str | None = None,
          reaffirmed: dict[str, dict] | None = None) -> dict:
    r2 = source_prereg()
    reaffirmed = reaffirmed or {}
    derivation = allowlist.derive()
    tasks = [t for t in r2["tasks"] if t["id"] in round2.TASKS]
    if len(tasks) != len(round2.TASKS):
        raise SystemExit(f"round 2's frozen file does not carry all of {round2.TASKS}")
    preds = predictions()
    draft = {
        "study": study.STUDY_TITLE,
        "status": "DRAFT. Changes until the freeze; nothing may be run or graded against it.",
        "question": (
            "For the three tasks round 2 published as covered by no model -- "
            f"{', '.join(round2.TASKS)} -- on both halves and all three Claude models at n = {N}, how many "
            "of three takes does each cell hold, measured under one permission condition pre-registered for "
            "the whole model axis?"),
        "why": (
            "Round 2 passed `--permission-mode auto` to all three models. Its transcripts for these three "
            "tasks record `default` in all six of the smallest model's cells and `auto` in all twelve of the "
            "others, so the smallest model's published zeros may describe the harness rather than the model. "
            "Round 3 measures the three uncovered tasks with the same pre-registered list of admitted "
            "commands on every turn of every take."),
        "source_commit": SOURCE_COMMIT,
        "source_prereg": SOURCE_PREREG,
        "carried_from_round_2": list(CARRIED),
        "carried_note": "Each key named here is round 2's frozen value at the source commit, unchanged; the "
                        "battery compares them with the source.",
        "export_at": EXPORT_AT,
        "export_at_gars_tree": export_gars_tree(),
        "export_at_note": (
            "Every take's checkout is exported from this commit (drive.py --at). Its gars tree is "
            "system_under_test.gars_tree_sha, round 2's pinned system under test. gars/ has moved on main "
            "since round 2, so this is deliberately NOT HEAD and a take driven at HEAD is refused."),
        "session_namespace": {
            "uuid": str(uuid.uuid5(uuid.NAMESPACE_URL, NAMESPACE_FROM)),
            "derived_from": NAMESPACE_FROM,
            "note": "uuid5(NAMESPACE_URL, derived_from); not round 2's and not the pre-study's, so no session "
                    "id can repeat one of theirs."},
        "n": N,
        "models": list(r2["models"]),
        "claude_models": list(r2["claude_models"]),
        "model_status": {m: {"runs": True} for m in r2["models"]},
        "tasks": tasks,
        "tasks_note": "The three tasks as frozen in round 2, both halves, byte-identical to the source file "
                      "bar template-adherence's fixture, whose re-cut is recorded under fixture_recut.",
        "planned_cells": len(preds),
        "planned_takes": len(preds) * N,
        "driver_change": {
            "allowed_tools": [e["tool"] for e in derivation["entries"]],
            "flag": "--allowedTools",
            "where": "every turn, appended to round 2's argv after the isolation flags; --permission-mode "
                     "auto is still passed",
            "derived_by": f"{study.rel('allowlist.py')} --derive, from round 2's committed transcripts of "
                          f"these three tasks; the record is {study.rel('allowlist-derivation.json')}",
            "derivation_rules": [
                "No entry is a bare binary wildcard: an entry is a binary and at least one more token.",
                "No entry is wider than a command form quoted verbatim: every entry appears, character for "
                "character, at the start of at least one command an agent ran on that task before its probe, "
                "and the derivation carries the transcript and line it was quoted from.",
            ],
            "calls_seen": derivation["calls_seen"],
            "calls_admitted": derivation["calls_admitted"],
            "calls_refused_by_construction": derivation["calls_refused_by_construction"],
            "by_class": derivation["by_class"],
            "denial_outside_the_allowlist": (
                "A denial of a command this list does not admit is a condition of the harness, published as "
                "such with the denied command quoted, never a finding about the model. A take that reached "
                "the probe is read as having reached it whatever was denied earlier, and its denials are "
                "printed beside it."),
            "permission_mode_binding": (
                "The driver records in each take's ledger the permission mode THE SESSION RECORDED, read from "
                "the take's own published transcript, and the mode it passed beside it as "
                "`permission_mode_passed`. The copied checker's constant-binding rule reads the first, so a "
                "take whose session recorded a mode other than the pre-registered one is routed as a "
                "rehearsal with reason `constant-binding` -- round 2's reason id, which its own text already "
                "covers, and the only id a byte-identical checker can emit."),
            "approved_by_owner": approved_by_owner,
            "approved_at": approved_at,
            "approval_note": "Null until the owner gives it. The freeze refuses while it is null; the entries "
                             "decide what this round may claim.",
        },
        "carried_rulings": [
            {"source_key": key, "source_round": rnd, "why_re_put": why,
             "quoted_verbatim": r2[key],
             "reaffirmed_by_owner": (reaffirmed.get(key) or {}).get("words"),
             "reaffirmed_at": (reaffirmed.get(key) or {}).get("at")}
            for key, rnd, why in CARRIED_RULING_KEYS],
        "carried_rulings_note": (
            "A ruling made about another study's artifact is re-put before this round relies on it. Each is "
            "quoted verbatim from the key it was recorded in, with the round that made it. The freeze refuses "
            "while any `reaffirmed_by_owner` is null."),
        "predictions": preds,
        "predictions_rule": PREDICTIONS_RULE,
        "not_poolable": NOT_POOLABLE,
        "take_order": None,
        "take_order_seed": None,
        "take_order_note": (
            "One permutation per axis over every (task, half, model, take), seeded by the sha of the "
            "pre-freeze review commit -- a sha that does not exist until the review has happened, so the "
            "order cannot have been chosen to suit a result. prereg.py --order <sha> recomputes it."),
        "leak_words": list(r2["leak_words"]) + LEAK_WORDS_ADDED,
        "leak_words_note": (
            "Round 2's list plus this round's own names. Every word is grepped against a real transcript's "
            "attachment records before the freeze: the pre-study added `allowlist` to its list and Claude "
            "Code's own skill listing carries that word, which voided its first take."),
        "leak_context_excusals": [dict(e) for e in r2["leak_context_excusals"]]
        + [dict(e) for e in EXCUSALS_ADDED],
        "leak_context_excusals_note": (
            "Round 2's excusals, carried verbatim, plus three this round added before the freeze after "
            "leak_grep.py grepped the whole list against five real recorded sessions and found two words "
            "that would have voided every one of them. Each added excusal is the producer's own sentence."),
        "limitations_lines": LIMITATIONS,
        "limitations_note": "Round 2's limitations stay round 2's; these are round 3's own, and the first "
                            "seven carry the pre-study's six forward re-scoped to this round.",
        "publication": {
            "file": study.rel("RESULT.md"),
            "written_by": study.rel("result.py"),
            "rule": (
                "Counts per cell, with no rate and no verb about a model. Every unmeasured cell is named with "
                "its reason. Round 2's counts for the same three tasks print beside them under a caption, "
                "written by code, naming per column the permission condition, the run date and the "
                "instrument, and marking round 2's incomplete cell as incomplete with its graded-take count. "
                "Every k of n has n = 3 and traces to exactly one round's table."),
        },
    }
    for k in CARRIED:
        if k not in r2:
            raise SystemExit(f"round 2's frozen file has no {k!r}")
        draft[k] = r2[k]
    # driver_constants is round 2's, plus the one key Ruling 2 adds. It is built here rather than carried,
    # so `carried_from_round_2` stays honest about what is unchanged.
    draft["driver_constants"] = dict(r2["driver_constants"])
    draft["driver_constants"]["permission_mode_expected"] = dict(PERMISSION_MODE_EXPECTED)
    draft["driver_constants"]["permission_mode_expected_why"] = PERMISSION_MODE_EXPECTED_WHY
    draft["driver_constants_note"] = (
        "Round 2's frozen driver_constants, carried key for key, plus permission_mode_expected and its why "
        "(Ruling 2). permission_mode keeps round 2's meaning -- the flag the driver passes -- because the "
        "copied checker reads it and is byte-identical.")
    return draft


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--approve", metavar="WORDS", help="the owner's words approving the allowlist entries")
    ap.add_argument("--approved-at", metavar="ISO")
    ap.add_argument("--reaffirm", metavar="KEY", help="a carried ruling key the owner has re-affirmed")
    ap.add_argument("--reaffirm-words", metavar="WORDS")
    ap.add_argument("--reaffirmed-at", metavar="ISO")
    args = ap.parse_args()
    current = json.loads(DRAFT.read_text()) if DRAFT.is_file() else {}
    words = args.approve or (current.get("driver_change") or {}).get("approved_by_owner")
    at = args.approved_at or (current.get("driver_change") or {}).get("approved_at")
    if bool(words) != bool(at):
        print("an approval needs both the owner's words and the date they were given")
        return 2
    reaffirmed = {r["source_key"]: {"words": r.get("reaffirmed_by_owner"), "at": r.get("reaffirmed_at")}
                  for r in current.get("carried_rulings") or []}
    if args.reaffirm:
        if not (args.reaffirm_words and args.reaffirmed_at):
            print("a re-affirmation needs --reaffirm-words and --reaffirmed-at")
            return 2
        if args.reaffirm not in {k for k, _, _ in CARRIED_RULING_KEYS}:
            print(f"{args.reaffirm!r} is not a carried ruling key")
            return 2
        reaffirmed[args.reaffirm] = {"words": args.reaffirm_words, "at": args.reaffirmed_at}
    text = json.dumps(build(words, at, reaffirmed), indent=2, ensure_ascii=False) + "\n"
    if args.check:
        same = DRAFT.is_file() and DRAFT.read_text() == text
        print("ok: the draft is what build_draft.py builds" if same
              else "FAIL the draft differs from what build_draft.py builds")
        return 0 if same else 1
    DRAFT.write_text(text)
    d = json.loads(text)
    open_gates = [r["source_key"] for r in d["carried_rulings"] if not r["reaffirmed_by_owner"]]
    print(f"wrote {DRAFT.name}: {d['planned_cells']} planned cells, {d['planned_takes']} planned takes, "
          f"{len(d['driver_change']['allowed_tools'])} allowlist entries, "
          f"{sum(1 for p in d['predictions'] if p['predicted'] is None)} cell(s) with no informed basis")
    print(f"open owner gates: allowlist approval {'GIVEN' if words else 'null'}; "
          f"carried rulings awaiting re-affirmation: {open_gates or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
