#!/usr/bin/env python3
"""Drive one pre-registered take, or one pre-freeze walk, sending fixed lines and nothing else.

    python3 evals/gap-study/drive.py --task scope-read --half positive --row 12
    python3 evals/gap-study/drive.py --task scope-read --half positive --walk --model claude-opus-5

A DETERMINISTIC OPERATOR. It opens a headless Claude Code session in the repository root and sends
the operator lines the pre-registration fixes, one turn at a time. It does not rephrase, nudge,
retry, or answer a question that is not on the script. Nothing it does depends on what the agent
said, beyond checking for a wait-point marker.

WHAT IS DIFFERENT FROM THE FIRST STUDY'S DRIVER, AND WHY EACH DIFFERENCE EARNS ITS PLACE.

The script is DATA. The first study's driver held its operator lines, its question and its markers
as module constants for one task. Here every line, marker and reach turn is read from the
pre-registration, so a stranger can see what was sent without reading Python.

The session id is NOT DISCOVERED, IT IS IMPOSED. The first study read the session id out of the
first record Claude Code emitted. This driver computes it before the session opens:

    session_id = uuid5(NAMESPACE, the sha of the commit that introduced this take's ledger row)

and passes it with --session-id. The row must be committed before the take can run, because its
commit sha is an input to the id. That is what makes "pre-registered before it ran" checkable by a
stranger rather than a promise.

A HALT IS NO LONGER A REHEARSAL. In the first study, an unheld marker discarded the run. That rule
lets a bad result be re-labelled as a mechanical failure, which is the one thing a study like this
cannot afford. Here:

  a transcript with a first agent turn is a GRADED TAKE, whatever happened after it. If the agent
    never reached the wait point, the grader labels it did-not-reach and it counts against holding.
  a REHEARSAL is only an attempt refused by the take checker for an operator-side reason, or a
    `claude` process that died before its first agent turn.
  a PAUSE is a rate-limit refusal before the first agent turn: wait, record it, retry the slot.

The driver sends no line past an unheld marker -- continuing would measure a script the agent never
got to -- but it does not throw the transcript away either.

NOTHING IN A PATH OR A NAME TELLS THE AGENT WHAT THIS IS. The session under test reads every byte it
is given. The first study named its projects for the half and staged fixtures under a path carrying
the task name; both had to be repaired mid-run. Here the project name and the staging path are
derived from the session id -- `run-<8 hex>` -- which is unique, reproducible, bound to the ledger
row, and says nothing. The half is recorded in the ledger, where the agent cannot read it.

ON THE RULE GLITCH IS BUILT UNDER. The Glitch engine never uses `claude -p`. This file is the GARS
project's own evaluation harness and lives in the GARS repository; that rule does not reach it.

The session under test is a separate process with no context from the session running this driver
or from the session that will grade the result. No model is called by this file itself.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))

import prereg  # noqa: E402
import takes as takes_mod  # noqa: E402

STAGING = REPO / "data" / "staging"          # machine-local, git-excluded
PERMISSION_MODE = "auto"
RATE_LIMIT_MARKERS = ("rate limit", "usage limit", "weekly limit", "resets", "429")


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def session_dir() -> Path:
    """Where Claude Code writes the session transcript for a session opened in REPO."""
    return Path.home() / ".claude" / "projects" / ("-" + str(REPO).strip("/").replace("/", "-"))


def neutral_name(session_id: str) -> str:
    """The project and staging name. Unique, reproducible, and it says nothing.

    Derived from the session id, which is derived from the ledger row's commit, so a checker can
    re-derive it -- while the agent, which sees this string in every operator line, learns only
    that it is a run.
    """
    return "run-" + session_id.replace("-", "")[:8]


def one_turn(line: str, session_id: str, model: str, first: bool,
             budget_s: int) -> tuple[str, int, str]:
    """Send one line. Returns (assistant_text, exit_code, stderr).

    stdin is CLOSED deliberately: headless Claude Code reads anything left on stdin into the
    prompt, and a smoke test in the first study proved it by swallowing the test script itself.
    """
    argv = ["claude", "-p", line, "--output-format", "stream-json", "--verbose",
            "--permission-mode", PERMISSION_MODE, "--permission-prompts", "none",
            "--model", model]
    argv += ["--session-id", session_id] if first else ["--resume", session_id]

    try:
        proc = subprocess.run(argv, cwd=str(REPO), capture_output=True, text=True,
                              stdin=subprocess.DEVNULL, timeout=budget_s)
    except subprocess.TimeoutExpired:
        return "", 124, f"turn exceeded the pre-registered budget of {budget_s}s"

    said: list[str] = []
    for raw in proc.stdout.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            rec = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if rec.get("type") == "assistant":
            content = (rec.get("message") or {}).get("content")
            if isinstance(content, list):
                said.extend(b.get("text", "") for b in content
                            if isinstance(b, dict) and b.get("type") == "text")
    return "\n".join(s for s in said if s), proc.returncode, proc.stderr


def looks_rate_limited(text: str) -> bool:
    low = (text or "").lower()
    return any(m in low for m in RATE_LIMIT_MARKERS)


def build_fixture(spec: dict, dest: Path) -> None:
    gen = REPO / spec["generator"]
    subprocess.run([sys.executable, str(gen), "--variant", spec["variant"],
                    "--seed", str(spec["seed"]), "--out", str(dest)],
                   check=True, capture_output=True, text=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="Drive one take, or one pre-freeze walk.")
    ap.add_argument("--task", required=True)
    ap.add_argument("--half", required=True, choices=("positive", "control"))
    ap.add_argument("--row", type=int, help="the committed ledger row this take belongs to")
    ap.add_argument("--walk", action="store_true",
                    help="a pre-freeze walk: stop BEFORE the probe turn, never graded")
    ap.add_argument("--model", help="required for a walk; a take reads it from its ledger row")
    ap.add_argument("--budget", type=int, default=None, help="per-turn seconds")
    args = ap.parse_args()

    pre = prereg.load()
    spec = prereg.task(args.task)
    half = spec[args.half]
    registered_budget = int(pre["budgets"]["turn_timeout_s"])
    budget = args.budget or registered_budget

    # A BUDGET BELOW THE PRE-REGISTERED ONE IS REFUSED.
    #
    # plan-gate's first attempt was driven with --budget 280 against a registered 900, and the turn
    # timed out while the agent was still drafting. That produced a `timed-out` label which says
    # nothing about the agent and everything about the operator, and under the study's own rules a
    # timed-out transcript counts against holding. An operator flag must not be able to manufacture
    # that.
    #
    # Under-budget attempts are refused outright rather than warned about, because the label they
    # produce is indistinguishable, after the fact, from one the agent earned.
    if budget < registered_budget:
        print(f"refusing: --budget {budget}s is below the pre-registered {registered_budget}s. A "
              f"turn cut short by the operator produces a `timed-out` label the agent did not "
              f"earn, and that label counts against holding. Raise the budget, or change the "
              f"pre-registered value.")
        return 2

    # ---- who am I, and what id do I open with -----------------------------------------
    if args.walk:
        if not args.model:
            ap.error("--walk needs --model")
        model = args.model
        session_id = str(uuid.uuid4())
        # Walks are numbered per TASK and capped at two, per the protocol. Numbering rather than
        # overwriting matters: walk 1 is the evidence for why walk 2's script differs, and the
        # freeze commit has to list every line that changed and why.
        base = HERE / "walks" / args.task
        existing = sorted(p for p in base.glob("*") if p.is_dir()) if base.is_dir() else []
        if len(existing) >= 2:
            print(f"{args.task} already has {len(existing)} walks, and the cap is two. Fix the "
                  f"script from what those two showed, or freeze it as it stands.")
            return 2
        out_root = base / str(len(existing) + 1)
        kind = "walk"
    else:
        if args.row is None:
            ap.error("a take needs --row (its committed ledger row)")
        prereg.require_frozen("driving a graded take")
        rows = takes_mod.load_rows()
        if not (0 <= args.row < len(rows)):
            print(f"no ledger row {args.row}")
            return 2
        row = rows[args.row]
        if (row["task"], row["half"]) != (args.task, args.half):
            print(f"row {args.row} is {row['task']}/{row['half']}, not {args.task}/{args.half}")
            return 2
        commits = takes_mod.row_commits()
        if args.row not in commits:
            print(f"row {args.row} is not committed. Its session id does not exist until it is: "
                  f"the uuid is a function of the commit that introduces it, which is what makes "
                  f"'pre-registered before it ran' checkable.")
            return 2
        model = row["model"]
        session_id = takes_mod.session_id_for(commits[args.row])
        out_root = HERE / "transcripts" / args.task / args.half / model / str(row["take"])
        kind = "take"

    name = neutral_name(session_id)
    steps = list(half["operator_script"])
    if args.walk:
        # A walk stops BEFORE the probe: it exists to fix the script and the markers, and a walk
        # that reached the probe would have spent the agent's first look at the thing being
        # measured on a rehearsal.
        steps = [s for s in steps if s["n"] < half["probe_operator_turn"]]
        if not steps:
            print(f"{args.task}/{args.half}: the probe is turn {half['probe_operator_turn']}, so a "
                  f"walk that stops before it sends nothing. Nothing to walk.")
            return 2

    # ---- the fixture ------------------------------------------------------------------
    staging = STAGING / name
    if staging.exists():
        print(f"refusing: {staging} already exists. A take starts from a clean fixture.")
        return 2
    fx = half.get("fixture") or {}
    proj_dir = REPO / "gars" / "projects" / name
    if proj_dir.exists():
        print(f"refusing: {proj_dir} already exists.")
        return 2

    if fx.get("kind") == "generated":
        # A source directory the operator points stage 00 at. The project does not exist yet.
        build_fixture(fx, staging)
        source = staging / "src"
    elif fx.get("kind") == "project":
        # A project that stage 00 has ALREADY produced -- precondition-refusal starts at stage 01,
        # so its fixture is the finished project rather than a path to raw data. The generator
        # builds it through the real stage 00 and then verifies, against stage 01 itself, that this
        # half reaches the branch it is meant to probe.
        gen = REPO / fx["generator"]
        r = subprocess.run([sys.executable, str(gen), "--variant", fx["variant"],
                            "--seed", str(fx["seed"]), "--name", name],
                           capture_output=True, text=True)
        print("    " + (r.stdout.strip().splitlines() or ["(no output)"])[0])
        if r.returncode != 0:
            print(f"the fixture did not reach its branch, so no take is driven:\n{r.stdout}{r.stderr}")
            return 2
        source = proj_dir
    elif fx.get("kind") == "copied-tree":
        # A minimal copy of a project a real run produced. plan-gate needs stage 02 already
        # COMPLETE, which nothing this study generates could honestly produce.
        gen = REPO / fx["generator"]
        r = subprocess.run([sys.executable, str(gen), "--name", name],
                           capture_output=True, text=True)
        if r.returncode != 0:
            print(f"the fixture copy refused:\n{r.stdout[-600:]}{r.stderr[-400:]}")
            return 2
        ledger_fixture = json.loads(r.stdout)
        print(f"    copied {ledger_fixture['files']} files, tree "
              f"{ledger_fixture['tree_sha256_name_invariant'][:12]}, rows "
              f"{ledger_fixture['rows_real']} real / {ledger_fixture['rows_stub']} stub")
        source = proj_dir
    else:
        print(f"{args.task}: fixture kind {fx.get('kind')!r} is not drivable yet by this file")
        return 2

    ledger = {"kind": kind, "task": args.task, "half": args.half, "model_requested": model,
              "session_id": session_id, "project": name, "source": str(source.relative_to(REPO)),
              "row": args.row, "permission_mode": PERMISSION_MODE, "permission_prompts": "none",
              "cwd": str(REPO), "budget_s": budget, "started": now(),
              "claude_version": subprocess.run(["claude", "--version"], capture_output=True,
                                               text=True).stdout.strip(),
              "gars_tree_sha": subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD:gars"],
                                              capture_output=True, text=True).stdout.strip(),
              "turns": [], "outcome": None, "first_agent_turn": False}

    print(f"{kind}: {args.task} / {args.half} / {model}")
    print(f"  session {session_id}")
    print(f"  project {name}   source {source.relative_to(REPO)}")

    # ---- the script -------------------------------------------------------------------
    for i, step in enumerate(steps, start=1):
        line = step["line"].format(project=name, source=source.relative_to(REPO))
        shown = line if len(line) < 64 else line[:61] + "..."
        print(f"  [{i}/{len(steps)}] > {shown}")
        t0 = now()
        said, code, err = one_turn(line, session_id, model, first=(i == 1), budget_s=budget)

        row_rec = {"n": step["n"], "sent": line, "expects": step.get("marker"),
                   "means": step.get("means"), "at": t0, "exit": code,
                   "reply_chars": len(said)}

        if said.strip():
            ledger["first_agent_turn"] = True

        # A rate-limit refusal BEFORE any agent turn is a pause, not a take and not a rehearsal.
        if code != 0 and not ledger["first_agent_turn"] and looks_rate_limited(err + said):
            row_rec["outcome"] = "PAUSE — rate limited before the first agent turn"
            ledger["turns"].append(row_rec)
            ledger["outcome"] = "PAUSE"
            ledger["pause"] = {"started": t0, "ended": now(), "detail": err.strip()[:400]}
            print("  PAUSE: rate limited before the first agent turn. The slot is retried; this "
                  "is neither a take nor a rehearsal.")
            break

        if code == 124:
            row_rec["outcome"] = "timed-out"
            ledger["turns"].append(row_rec)
            ledger["outcome"] = "timed-out"
            print(f"  turn exceeded the {budget}s budget")
            break

        if code != 0 and not ledger["first_agent_turn"]:
            row_rec["outcome"] = f"process exited {code} before any agent turn"
            ledger["turns"].append(row_rec)
            ledger["outcome"] = "REHEARSAL — the process died before its first agent turn"
            print(f"  the process exited {code} before any agent turn: a rehearsal, never graded.")
            break

        marker = step.get("marker")
        # CASE-SENSITIVE, because that is what the pre-registration says. The markers are the
        # templates' own bytes; comparing loosely here would let a marker that is NOT in the
        # template pass anyway, which is how four of them came to be lowercased renderings that
        # only ever matched case-insensitively. See prereg wait_point_marker_rule.
        held = True if marker is None else (marker in said)

        # THE PRE-REGISTERED RECOVERY, sent at most once, only where the frozen file allows it.
        #
        # Stage 00's T3b ends by asking for the raw data path, which makes it a wait point by the
        # definition this study pins. The operator's first line already carries that path, and on
        # the committed walk the agent sent T3b and T4a in one turn and never waited. But an agent
        # that follows the contract and STOPS at T3b leaves the next marker unheld, the driver
        # sends nothing further, and the take publishes as `did-not-reach` -- a model failure the
        # model did not earn, across three tasks and half the takes.
        #
        # That is the same class as the marker-case defect: an operator-side mechanism producing a
        # label out of nothing the agent did. The recovery answers the wait point the agent is
        # actually sitting at, once, with the path the first line already gave. It is DATA in the
        # pre-registration, never the driver's judgment, and it fires only when the reply holds
        # the recovery's own marker and not the step's.
        rec = step.get("recovery")
        if (not held) and rec and rec["if_reply_holds"] in said:
            line2 = rec["send"].format(project=name, source=source.relative_to(REPO))
            print(f"        recovery: the reply is waiting at {rec['if_reply_holds']!r}; "
                  f"answering it once")
            said2, code2, _err2 = one_turn(line2, session_id, model, first=False, budget_s=budget)
            ledger["turns"].append({"n": step["n"], "sent": line2, "recovery": True,
                                    "expects": marker, "at": now(), "exit": code2,
                                    "reply_chars": len(said2),
                                    "why": "pre-registered recovery for a wait point the script "
                                           "does not otherwise answer"})
            if said2.strip():
                ledger["first_agent_turn"] = True

            # THE RECOVERY TURN'S EXIT CODE IS NOT SWALLOWED.
            #
            # The first version appended the reply and moved on. A budget overrun on the recovery
            # turn would then leave the marker unheld and publish `did-not-reach` -- which is
            # Ruling 4's defect, an operator-side failure wearing a label the agent did not earn,
            # reintroduced by the fix for Ruling 4's own class.
            if code2 == 124:
                ledger["outcome"] = "timed-out"
                print(f"        recovery turn exceeded the {budget}s budget")
                break
            if code2 != 0:
                ledger["outcome"] = f"aborted — the recovery turn exited {code2}"
                print(f"        recovery turn exited {code2}")
                break

            said = said + "\n" + said2
            held = marker in said

        row_rec["held"] = held
        ledger["turns"].append(row_rec)
        print(f"        {'ok' if held else 'MARKER NOT HELD'}  {step.get('means')}")

        if not held:
            # No further line is sent -- continuing would measure a script the agent never got to.
            # The transcript is still a take, and the grader will call it did-not-reach.
            ledger["outcome"] = "stopped — wait-point marker not held; graded as it stands"
            break
    else:
        ledger["outcome"] = "complete"

    # ---- the transcript is the session file, copied verbatim ---------------------------
    src = session_dir() / f"{session_id}.jsonl"
    ledger["finished"] = now()
    out_root.mkdir(parents=True, exist_ok=True)
    if src.is_file():
        shutil.copy2(src, out_root / "transcript.jsonl")
        ledger["transcript"] = str((out_root / "transcript.jsonl").relative_to(REPO))
    else:
        ledger["transcript"] = None
        ledger["outcome"] = (ledger["outcome"] or "") + f" — no session file at {src}"
    (out_root / "driver-ledger.json").write_text(json.dumps(ledger, indent=2) + "\n")

    print(f"\n  outcome  {ledger['outcome']}")
    print(f"  ledger   {(out_root / 'driver-ledger.json').relative_to(REPO)}")
    if ledger["transcript"]:
        print(f"  transcript {ledger['transcript']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
