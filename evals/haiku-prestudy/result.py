#!/usr/bin/env python3
"""Write RESULT.md from the committed takes, by code, and check the file on disk is what the takes say.

    python3 evals/haiku-prestudy/result.py --write
    python3 evals/haiku-prestudy/result.py --check     exit 1 if RESULT.md differs from what the takes produce

Every line of RESULT.md comes from a file: the frozen pre-registration, each take's driver-ledger.json and
transcript.jsonl read by outcome.py, round 2's number-fidelity grader run on the take by path (printed for
information, never as a graded cell), and round 2's published analysis.json for the twelve Haiku cells beside it.
It prints counts of three and no rate, and it says nothing about the model beyond what each take did.

No model, no network. stdlib only.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "evals"))
sys.path.insert(0, str(HERE))

import outcome  # noqa: E402
import prereg  # noqa: E402
import transcript as tx  # noqa: E402

RESULT = HERE / "RESULT.md"
ROUND2 = REPO / "evals" / "gap-study-2"
ROUND2_GRADER = ROUND2 / "graders" / "number_fidelity.py"
ROUND2_ANALYSIS = ROUND2 / "analysis.json"
TASK, HALF = "number-fidelity", "positive"
BESIDE_HEADING = "## Round 2's twelve Haiku cells, beside it: a pre-study with a changed driver, never pooled"
INFO_HEADING = "round 2's grader label, for information only"


def round2_grader():
    spec = importlib.util.spec_from_file_location("round2_number_fidelity_for_prestudy", ROUND2_GRADER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def round2_task() -> dict:
    pre = json.loads((ROUND2 / "prereg.json").read_text())
    return next(t for t in pre["tasks"] if t["id"] == TASK)


def take_dirs(model: str) -> list[Path]:
    base = HERE / "transcripts" / TASK / HALF / model
    return sorted((p for p in base.iterdir() if p.is_dir()), key=lambda p: int(p.name)) if base.is_dir() else []


def round2_label(d: Path) -> str:
    t = d / "transcript.jsonl"
    if not t.is_file():
        return "(no transcript)"
    labels = outcome.round2_labels()
    turns = labels.mark_harness_records(tx.parse(t), labels.harness_record_flags(t))
    ledger = json.loads((d / "driver-ledger.json").read_text())
    got = round2_grader().grade(turns, ledger, HALF, round2_task())
    return str(got["label"])


def binding_problems(pre: dict, rows_ledgers: list[dict]) -> list[str]:
    """Review 1, follow-up 1: the code a result is written by must be the code the freeze pinned, and every take
    must have been driven with the allowlist the pre-registration names."""
    import hashlib
    out = []
    for f, sha in (pre.get("pinned_files") or {}).items():
        got = hashlib.sha256((HERE / f).read_bytes()).hexdigest() if (HERE / f).is_file() else None
        if got != sha:
            out.append(f"{f} is not the file the freeze pinned ({str(got)[:12]} against {sha[:12]})")
    import subprocess
    roots = [f"evals/haiku-prestudy/{d}/" for d in ("transcripts", "rehearsals", "pauses")]
    deleted = subprocess.run(["git", "-C", str(REPO), "log", "--no-renames", "--diff-filter=D", "--name-only",
                              "--format=", "--", *roots], capture_output=True, text=True).stdout.split()
    if deleted:
        out.append(f"an attempt file was deleted in this repository's history ({deleted[:3]}): a graded take may "
                   f"have been removed and its row re-driven")
    for led in rows_ledgers:
        if led.get("allowed_tools") != pre["driver_change"]["allowed_tools"]:
            out.append(f"row {led.get('row')}'s ledger records allowed_tools {led.get('allowed_tools')}, not the "
                       f"pre-registration's {pre['driver_change']['allowed_tools']}")
    return out


def ledger_problems(pre: dict) -> list[str]:
    """Review 2, follow-up 4: the copied ledger check (every attempt tied to exactly one committed row, in the folder
    its kind puts it in), read at export_at, whose gars tree is the pinned one; HEAD's moved after round 2."""
    import contextlib
    import io
    spec = importlib.util.spec_from_file_location("prestudy_check_results", HERE / "check_results.py")
    cr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cr)
    with contextlib.redirect_stdout(io.StringIO()):
        problems = cr.check_ledger(at=pre["export_at"])
        # REVIEW 4, FOLLOW-UP 1. The copied check returns before its order and skipped-row guards when no seed
        # exists, and prints that they run after the freeze, which never becomes true in a study whose order is a
        # fixed list. Both are run here against that list.
        if not pre.get("take_order_seed"):
            problems += order_and_gap_problems(cr, pre)
    return problems


def order_and_gap_problems(cr, pre: dict) -> list[str]:
    """The copied skipped-row guard, and the registration order held to the pre-registration's own list."""
    import takes as takes_mod
    rows = takes_mod.load_rows()
    commits = takes_mod.row_commits()
    by_sid = takes_mod.attempts_by_session()
    attempted = {i: bool(takes_mod.attempt_kind(i, commits, by_sid)) for i in range(len(rows))}
    out = list(cr.gap_problems(rows, attempted, lambda model: "claude"))
    want = [list(x) for x in pre["take_order"]]
    seen: list[list] = []
    for r in rows:
        slot = [r["task"], r["half"], r["model"], r["take"]]
        if slot not in seen:
            seen.append(slot)
    if seen != want[:len(seen)]:
        out.append(f"the slots were registered in the order {seen}, and the pre-registration fixes {want}")
    return out


def other_attempts(model: str) -> list[dict]:
    """Review 1, follow-up 2: every rehearsal and pause, with its row and reason ids, so no attempt goes unpublished."""
    out = []
    for kind in ("rehearsals", "pauses"):
        base = HERE / kind / TASK / HALF / model
        for d in sorted(base.glob("row-*")) if base.is_dir() else []:
            led = json.loads((d / "driver-ledger.json").read_text())
            out.append({"kind": kind[:-1], "row": led.get("row"), "reasons": (led.get("attempt") or {}).get("reasons") or [],
                        "outcome": led.get("outcome")})
    return out


def quote(text: str, limit: int = 300) -> str:
    one = " ".join((text or "").split())
    return one if len(one) <= limit else one[: limit - 3] + "..."


def without_run_tree(text: str, cwd: str | None) -> str:
    """REVIEW 5, FOLLOW-UP 3. A command the model wrote may name the run tree by absolute path, which is a folder
    under this machine's temporary directory. The ledger records that path as `cwd`; it is replaced by a marker."""
    return text.replace(cwd, "<the take's checkout>") if cwd and text else text


def denial_lines(den: dict, cwd: str | None = None) -> list[str]:
    """What a denial publishes: the command, what the harness said needed approval, and its own words.

    REVIEW 4, BLOCKER 1. The quote limits are here, with the lines they cut, so a test drives the published form
    rather than rebuilding it: at 2.1.267 the harness names the command about 570 characters into its refusal.
    """
    cmd = without_run_tree(den.get("command") or "", cwd)
    out = [f"- Denied command: `{cmd}`" if cmd else "- Denied command: (not a command)"]
    if den.get("required_approval"):
        out.append("- The harness said it required approval for: "
                   + quote(without_run_tree(den["required_approval"], cwd), 400))
    out.append(f"- Denial quoted: \"{quote(without_run_tree(den['text'], cwd), 800)}\"")
    return out


def render() -> str:
    pre = prereg.require_frozen("writing the result")
    model = pre["models"][0]
    half = prereg.task(TASK)[HALF]
    dirs = take_dirs(model)
    ledgers = [json.loads((d / "driver-ledger.json").read_text()) for d in dirs]
    others = other_attempts(model)
    bad = binding_problems(pre, ledgers + [json.loads((HERE / (a["kind"] + "s") / TASK / HALF / model / f"row-{a['row']}"
                                                       / "driver-ledger.json").read_text()) for a in others])
    spec = importlib.util.spec_from_file_location("prestudy_copy_manifest_for_result", HERE / "copy_manifest.py")
    cm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cm)
    bad += cm.problems(cm.derive())
    bad += ledger_problems(pre)
    if bad:
        raise SystemExit("REFUSING to write the result:\n  - " + "\n  - ".join(bad))
    rows = [outcome.read(d, half) | {"round2_label": round2_label(d), "claude_version": led.get("claude_version")}
            for d, led in zip(dirs, ledgers)]
    reached = sum(1 for r in rows if r["outcome"] == outcome.REACHED)
    by_reason: dict[str, int] = {}
    for r in rows:
        if r["outcome"] != outcome.REACHED:
            key = r["reason"].split(":")[0]
            by_reason[key] = by_reason.get(key, 0) + 1
    L = ["# The Haiku pre-study: the result", "",
         "Written by `evals/haiku-prestudy/result.py` from the committed takes; `--check` re-derives it.", "",
         "## What was run", "",
         f"`{model}` on the `{TASK}` task, {HALF} half, as frozen in round 2: the same driver, script, fixture and "
         f"system under test (gars tree `{pre['system_under_test']['gars_tree_sha'][:8]}`, checkout exported from "
         f"`{pre['export_at'][:7]}`), with one change: every turn passed `--allowedTools "
         + " ".join(f"\"{a}\"" for a in pre["driver_change"]["allowed_tools"]) + "`.",
         f"The pre-registration froze at `{pre['frozen_at']}`; n = {pre['n']}.", "",
         "## Each take", "",
         f"| Take | Outcome | Reason | Denials | Ask phrases | Permission mode recorded | Allowlist in the ledger | Harness | {INFO_HEADING} |",
         "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['take']} | {r['outcome']} | {r['reason'] or '-'} | {max(len(r['denials']), r['tagged_denials'])} | "
                 f"{', '.join(r['ask_phrases']) or '-'} | {', '.join(r['permission_modes']) or '-'} | "
                 f"{', '.join(r['allowed_tools'] or []) or '-'} | {r['claude_version'] or '-'} | {r['round2_label']} |")
    L.append("")
    for r in rows:
        L.append(f"**Take {r['take']}** (session `{r['session_id']}`): {r['outcome']}"
                 + (f", {r['reason']}." if r["reason"] else "."))
        for den in r["denials"]:
            L += denial_lines(den, r.get("cwd"))
        L.append(f"- Final agent message quoted: \"{quote(r['final_agent_message'])}\"")
        L.append(f"- Driver outcome: {r['driver_outcome']}")
        L.append("")
    L += ["## Attempts that are not takes", ""]
    if others:
        for a in others:
            L.append(f"- Row {a['row']}: a {a['kind']}, reason ids {', '.join(a['reasons']) or '-'}; driver outcome: {a['outcome']}.")
        for kind, cap in (("rehearsal", int(pre["rehearsal_cap"])), ("pause", int(pre["pause_cap"]))):
            if sum(1 for a in others if a["kind"] == kind) >= cap and len(rows) < pre["n"]:
                L.append(f"- The half reached the {kind} cap of {cap}: it publishes `incomplete — mechanical`, "
                         f"{len(rows)} of {pre['n']}.")
    else:
        L.append("None: every registered row was driven to a graded take.")
    L.append("")
    # REVIEW 5, FOLLOW-UP 1. takes.py caps rehearsals and pauses apart, so the completeness rule counts them apart.
    capped = any(sum(1 for a in others if a["kind"] == kind) >= int(pre[f"{kind}_cap"])
                 for kind in ("rehearsal", "pause"))
    if len(rows) < pre["n"] and not capped:
        raise SystemExit(f"REFUSING to write the result: {len(rows)} of {pre['n']} takes are graded and no cap is "
                         f"reached, so the cell is neither complete nor mechanically incomplete "
                         f"({sum(1 for a in others if a['kind'] == 'rehearsal')} rehearsal(s), "
                         f"{sum(1 for a in others if a['kind'] == 'pause')} pause(s)).")
    L += ["## Counts", "",
          f"- Takes run: {len(rows)} of the {pre['n']} registered.",
          f"- Reached the probe: {reached} of {len(rows)}."]
    for k in outcome.REASON_ORDER:
        if by_reason.get(k):
            L.append(f"- Did not reach, {k}: {by_reason[k]} of {len(rows)}.")
    L += ["", "Predicted before any take, each informed by round 2: "
          + "; ".join(f"take {p['take']} {p['prediction']}" for p in pre["predictions"]) + ".", ""]
    a = json.loads(ROUND2_ANALYSIS.read_text())
    L += [BESIDE_HEADING, "",
          "Round 2 ran these cells under its own driver, without the allowlist; its counts are printed as published "
          "and are not added to the takes above.", "",
          "| Task | Positive | Control | Positive, reserved labels | Control, reserved labels |", "|---|---|---|---|---|"]
    for tid in sorted(a["tasks"]):
        m = a["tasks"][tid]["models"][model]
        fmt = lambda h: ", ".join(f"{k} {v}" for k, v in sorted(m["reserved_counts"][h].items()) if v) or "-"
        L.append(f"| `{tid}` | {m['positive']} | {m['control']} | {fmt('positive')} | {fmt('control')} |")
    L += ["", "## Limitations", ""] + [f"- {x}" for x in pre["limitations_lines"]] + [""]
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--write", action="store_true")
    g.add_argument("--check", action="store_true")
    g.add_argument("--ledger", action="store_true", help="only the ledger check, at export_at")
    args = ap.parse_args()
    if args.ledger:
        bad = ledger_problems(prereg.load())
        for b in bad:
            print(f"FAIL {b}")
        print("ok: every attempt is tied to one committed row" if not bad else f"{len(bad)} ledger problem(s)")
        return 1 if bad else 0
    text = render()
    if args.write:
        RESULT.write_text(text)
        print(f"wrote {RESULT.name}")
        return 0
    same = RESULT.is_file() and RESULT.read_text() == text
    print("ok: RESULT.md is what the takes produce" if same else "FAIL RESULT.md differs from what the takes produce")
    return 0 if same else 1


if __name__ == "__main__":
    raise SystemExit(main())
