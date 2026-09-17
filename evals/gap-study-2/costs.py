#!/usr/bin/env python3
"""What each take cost, read from the raw transcript rather than from anybody's memory.

    python3 evals/gap-study-2/costs.py                 every committed take and walk, and the bill
    python3 evals/gap-study-2/costs.py --write         rewrite the tables and the dollar line in COSTS.md
    python3 evals/gap-study-2/costs.py --check         exit 1 if COSTS.md is not what --write writes

THE FLAG USED TO DO NOTHING. `--write` was accepted and ignored until 11 September 2026, while
COSTS.md said every number in it came from this file; its walk table had been typed. The tables are
now rendered here and written in place, and `--check` is what the test harness runs.

WHY THIS IS ITS OWN READER. The shared transcript parser keeps what the agent said and what it ran,
and DISCARDS usage and timestamps -- deliberately, because a grader must never be able to see how
expensive a take was. So the only place tokens and wall clock survive is the raw JSONL, and this is
the only thing that opens it that way.

WHAT IT REPORTS, AND WHAT IT REFUSES TO. Tokens by class and wall clock from the first to the last
timestamp. It does not convert either into money, it never reads the cost figure the harness prints
in its result record, and it never reads the take ledger's environment class, which is a label the
operator chose rather than a record of the environment.

THE DOLLAR LINE (ROUND 2, CP3). Round 1's dollar line was typed into COSTS.md and this file printed a
sentence of its own; neither was bound to anything (Ruling 34). Here the line is rendered by the script
under its own heading, `--check` refuses it when it differs, and it takes exactly one of two forms:

    $0, evidenced by N of M environment records (no API-key variable set; the harness reported
    credential source <value> on every turn)

only when every graded take has an environment record that check_take.environment_problems finds valid,
that records no API-key variable and no billing-route variable set, and whose every turn reported the
pre-registered subscription source; otherwise

    $0 as the operator states it; evidenced by N of M; not evidenced: <slot>: <reason>; ...

naming every gap take by take. While the pre-registration names no subscription source, no take can be
evidence, and each take says so. A study with no graded take on disk evidences nothing either: zero
records is not zero dollars evidenced.

BEFORE THE FIRST TAKE. `--check` with no COSTS.md prints `no takes yet` while nothing exists that the
file would record, and so does `--write`, which writes nothing then: the file is created with the first
take, from the template below, so that `--check` keeps its `no takes yet` on the empty study.

A take with no usage records is reported as unmeasured rather than as zero. Zero is a measurement.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
# The code this file loads beside it (check_take, takes, prereg). HERE is the study the data is read from,
# which a test points at a fixture; CODE is never repointed.
CODE = Path(__file__).resolve().parent
CLASSES = ("input_tokens", "output_tokens", "cache_read_input_tokens",
           "cache_creation_input_tokens")
BILL = "Dollars billed beyond the standing subscription"
NAME = re.compile(r"^[A-Z_][A-Z0-9_]*$")


def read_one(path: Path) -> dict:
    acc = {c: 0 for c in CLASSES}
    stamps: list[str] = []
    model = None
    records = 0
    with_usage = 0
    for line in path.read_text(errors="replace").splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        records += 1
        msg = rec.get("message") if isinstance(rec.get("message"), dict) else {}
        model = model or msg.get("model")
        usage = msg.get("usage") or {}
        if usage:
            with_usage += 1
            for c in CLASSES:
                acc[c] += usage.get(c, 0) or 0
        if rec.get("timestamp"):
            stamps.append(rec["timestamp"])

    wall = None
    if len(stamps) >= 2:
        try:
            a = datetime.fromisoformat(stamps[0].replace("Z", "+00:00"))
            b = datetime.fromisoformat(stamps[-1].replace("Z", "+00:00"))
            wall = round((b - a).total_seconds() / 60.0, 1)
        except ValueError:
            wall = None

    try:
        shown = str(path.relative_to(REPO))
    except ValueError:
        shown = str(path)
    return {"path": shown, "model": model, "records": records,
            "usage_records": with_usage, "wall_minutes": wall,
            "measured": with_usage > 0, **acc}


# --------------------------------------------------------------------------- the environment records

def _load(name: str):
    """A module of this study by path, never by a sys.path lookup a first-study file of that name could win."""
    if str(CODE) not in sys.path:
        sys.path.insert(0, str(CODE))
    spec = importlib.util.spec_from_file_location(f"gap_study_2_costs_{name}", CODE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def pre_registration() -> dict:
    if str(CODE) not in sys.path:
        sys.path.insert(0, str(CODE))
    import prereg
    return prereg.load()


def environment_checker():
    """check_take.environment_problems(path, ledger, pre, row_commit), or None while the checker has none."""
    return getattr(_load("check_take"), "environment_problems", None)


def row_commits() -> dict[int, str]:
    """row index -> the commit that introduced it; empty when the history cannot be read, which no record
    survives, because the checker is then handed no row commit to bind."""
    try:
        return _load("takes").row_commits()
    except SystemExit:
        return {}


def _plain(text: str, limit: int = 200) -> str:
    """Text from a record or the checker, made safe for one line whose gaps are separated by semicolons."""
    one = " ".join(str(text).split()).replace(";", ",")
    return one if len(one) <= limit else one[:limit - 3] + "..."


def _names(variables, state: str) -> list[str]:
    """The names a record marks with `state`. Only a variable name is ever printed; a key that is not one is
    counted, never shown, because it may be a value written where a name belongs."""
    if not isinstance(variables, dict):
        return []
    hits = [k for k, v in variables.items() if v == state]
    shown = sorted(k for k in hits if isinstance(k, str) and NAME.match(k))
    if len(shown) < len(hits):
        shown.append(f"{len(hits) - len(shown)} key(s) that are not variable names")
    return shown


def _turn(t: dict) -> str:
    return f"turn {t.get('n')}" + (" (recovery)" if t.get("recovery") else "")


def environment_gaps(folder: Path, pre: dict, sub, checker, commits: dict) -> list[str]:
    """Why this take's environment record does not evidence the bill; [] when it does."""
    path = folder / "environment.json"
    if not path.is_file():
        return ["no environment record"]
    try:
        rec = json.loads(path.read_text())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return ["its environment record cannot be read as JSON"]
    if not isinstance(rec, dict):
        return ["its environment record is not a JSON object"]
    try:
        ledger = json.loads((folder / "driver-ledger.json").read_text())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        ledger = None

    gaps: list[str] = []
    if checker is None:
        gaps.append("no record checker exists (check_take.environment_problems), so no record is judged valid")
    else:
        row = ledger.get("row") if isinstance(ledger, dict) else None
        commit = commits.get(row) if isinstance(row, int) and not isinstance(row, bool) else None
        try:
            problems = checker(folder / "transcript.jsonl", ledger, pre, commit)
        except Exception as exc:  # named in the bill, never read as a valid record
            problems = [f"the checker raised {type(exc).__name__}"]
        if problems:
            more = f", and {len(problems) - 1} more" if len(problems) > 1 else ""
            gaps.append(f"the checker refuses its record ({_plain(problems[0])}{more})")

    for kind, variables, flag in (("an API-key variable", "api_key_variables", "api_key_set"),
                                  ("a billing-route variable", "billing_route_variables", "billing_route_set")):
        named = _names(rec.get(variables), "set")
        if named or rec.get(flag) is True:
            gaps.append(f"{kind} is set ({', '.join(named) if named else flag + ' is true'})")
        elif rec.get(flag) is not False:
            gaps.append(f"its record does not say {flag} false")

    source = rec.get("credential_source") if isinstance(rec.get("credential_source"), dict) else {}
    per_turn = source.get("per_turn")
    if not isinstance(per_turn, list) or not per_turn:
        gaps.append("no turn's credential source is recorded")
        return gaps
    turn_gaps = 0
    for t in per_turn:
        t = t if isinstance(t, dict) else {}
        label = _turn(t)
        src = t.get("apiKeySource")
        if src is None:
            gaps.append(f"{label} reported no credential source")
            turn_gaps += 1
            continue
        if sub is not None and src != sub:
            gaps.append(f"{label} reported credential source {_plain(src, 60)}, not {sub}")
            turn_gaps += 1
    if sub is not None and not turn_gaps and source.get("reported") != sub:
        gaps.append(f"its record reports credential source {_plain(source.get('reported'), 60)}, not {sub}")
    return gaps


def slot_name(r: dict) -> str:
    """task half model take N: never with a solidus, which the language guard reads as a rate."""
    task, half, model, take = r["slot"]
    return f"{task} {half} {model} take {take}"


def bill_line(takes: list[dict], sub) -> str:
    """The dollar line, in exactly one of its two forms."""
    m = len(takes)
    evidenced = [r for r in takes if not r["environment"]]
    if m and len(evidenced) == m and sub is not None:
        return (f"$0, evidenced by {len(evidenced)} of {m} environment records (no API-key variable set; the "
                f"harness reported credential source {sub} on every turn)")
    if not m:
        gaps = ["no graded take is on disk, so no environment record exists to evidence it"]
    else:
        gaps = [f"{slot_name(r)}: {', '.join(r['environment'])}" for r in takes if r["environment"]]
    return f"$0 as the operator states it; evidenced by {len(evidenced)} of {m}; not evidenced: " + "; ".join(gaps)


def read_environments(takes: list[dict]):
    """Each graded take's gaps, into r["environment"], and the pre-registered subscription source returned."""
    pre = pre_registration()
    spec = pre.get("environment_record") if isinstance(pre.get("environment_record"), dict) else {}
    sub = spec.get("subscription_source")
    checker = environment_checker()
    commits = row_commits()
    for r in takes:
        gaps = environment_gaps(r["dir"], pre, sub, checker, commits)
        if sub is None:
            gaps.append("no subscription source is pre-registered to match its turns against")
        r["environment"] = gaps
    return sub


def collect() -> dict:
    """Every graded take and walk, read from its raw JSONL, every recorded pause from its ledger, and the bill."""
    out: dict = {"takes": [], "walks": [], "pauses": []}
    for p in sorted((HERE / "transcripts").glob("*/*/*/*/transcript.jsonl")):
        r = read_one(p)
        r["slot"] = p.parent.relative_to(HERE / "transcripts").parts
        r["dir"] = p.parent
        out["takes"].append(r)
    for p in sorted((HERE / "walks").glob("*/*/transcript.jsonl")):
        r = read_one(p)
        r["walk"] = (p.parent.parent.name, p.parent.name)
        out["walks"].append(r)
    for led in sorted((HERE / "pauses").glob("*/*/*/*/driver-ledger.json")):
        try:
            d = json.loads(led.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        pause = d.get("pause") or {}
        out["pauses"].append({"started": pause.get("started"), "ended": pause.get("ended"),
                              "model": d.get("model_requested"),
                              "slot": "/".join(led.parent.relative_to(HERE / "pauses").parts)})
    sub = read_environments(out["takes"]) if out["takes"] else None
    out["bill"] = bill_line(out["takes"], sub)
    return out


def costs_md() -> Path:
    return HERE / "COSTS.md"


def registered_rows() -> int:
    """How many rows the take ledger holds; an unreadable ledger counts as not empty."""
    ledger = HERE / "takes.json"
    if not ledger.is_file():
        return 0
    try:
        return len(json.loads(ledger.read_text())["rows"])
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        return 1


def _n(x: int) -> str:
    return f"{x:,}"


def _cells(r: dict) -> str:
    if not r["measured"]:
        return "unmeasured | unmeasured | unmeasured | unmeasured"
    return (f"{_n(r['input_tokens'])} | {_n(r['cache_read_input_tokens'])} | "
            f"{_n(r['cache_creation_input_tokens'])} | {_n(r['output_tokens'])}")


def _wall(r: dict) -> str:
    return f"{_minutes(r['wall_minutes'])} min" if r["wall_minutes"] is not None else "unmeasured"


def _minutes(wall) -> str:
    """One decimal, and a whole number of minutes printed whole. AMENDMENT 3 (17 September 2026): a take that ran one
    minute rendered as `1.0 min`, which the language guard reads as a proportion of one, and the loop stopped on the
    costs table; the number is the same, only its spelling changes."""
    s = f"{round(wall, 1)}"
    return s[:-2] if s.endswith(".0") else s


def _environment(r: dict) -> str:
    return "not evidenced" if r["environment"] else "evidenced"


def tables(got: dict) -> dict[str, list[str]]:
    """The four tables COSTS.md carries, keyed by the heading each sits under."""
    out: dict[str, list[str]] = {}
    rows = [f"| `{r['slot'][0]}` | {r['slot'][1]} | `{r['slot'][2]}` | {r['slot'][3]} | {_cells(r)} | "
            f"{_wall(r)} | {_environment(r)} |" for r in got["takes"]]
    out["Per take"] = (["| task | half | model | take | input | cache read | cache write | output | wall clock "
                        "| environment |",
                        "|---|---|---|---|---|---|---|---|---|---|"]
                       + (rows or ["| _(no take has run)_ | | | | | | | | | |"]))
    rows = [f"| `{r['walk'][0]}` {r['walk'][1]} | `{r['model'] or 'unrecorded'}` | {_cells(r)} | {_wall(r)} |"
            for r in got["walks"]]
    out["Pre-freeze walks"] = (["| walk | model | input | cache read | cache write | output | wall clock |",
                                "|---|---|---|---|---|---|---|"]
                               + (rows or ["| _(no walk on disk)_ | | | | | | |"]))
    per: dict[str, dict] = {}
    for r in got["takes"]:
        m = per.setdefault(r["slot"][2], {"k": 0, "ctx": 0, "out": 0, "wall": 0.0})
        m["k"] += 1
        m["ctx"] += r["input_tokens"] + r["cache_read_input_tokens"] + r["cache_creation_input_tokens"]
        m["out"] += r["output_tokens"]
        m["wall"] += r["wall_minutes"] or 0.0
    rows = [f"| `{m}` | {v['k']} | {_n(v['ctx'])} | {_n(v['out'])} | {_minutes(v['wall'])} min |"
            for m, v in sorted(per.items())]
    out["Per model"] = (["| model | graded takes | context tokens | output tokens | wall clock |",
                         "|---|---|---|---|---|"]
                        + (rows or ["| _(no take has run)_ | | | | |"]))
    rows = [f"| {p['started']} | {p['ended']} | `{p['model']}` | {p['slot']} |" for p in got["pauses"]]
    out["Recorded pauses"] = (["| started | ended | model | slot |", "|---|---|---|---|"]
                              + (rows or ["| _(none)_ | | | |"]))
    return out


def _section(lines: list[str], heading: str, block: list[str]) -> list[str]:
    """Everything under `## heading`, up to the next heading, replaced by `block`: the section is the script's."""
    try:
        h = lines.index(f"## {heading}")
    except ValueError:
        raise SystemExit(f"COSTS.md has no '## {heading}' section to write under")
    j = next((k for k in range(h + 1, len(lines)) if lines[k].startswith("## ")), len(lines))
    return lines[:h + 1] + block + lines[j:]


def render(text: str, got: dict) -> str:
    """COSTS.md with each table and the dollar line replaced by what the reader writes; everything else untouched."""
    lines = text.split("\n")
    for heading, block in tables(got).items():
        try:
            h = lines.index(f"## {heading}")
        except ValueError:
            raise SystemExit(f"COSTS.md has no '## {heading}' section to write its table under")
        i = h + 1
        while i < len(lines) and not lines[i].startswith("|"):
            if lines[i].startswith("## "):
                raise SystemExit(f"COSTS.md has no table under '## {heading}'")
            i += 1
        j = i
        while j < len(lines) and lines[j].startswith("|"):
            j += 1
        lines[i:j] = block
    lines = _section(lines, BILL, ["", got["bill"], ""])
    return "\n".join(lines)


TEMPLATE = f"""# The bill and the machine

Every table below, and the line under the first heading, is written by `costs.py --write` from the raw transcripts, the driver ledgers and each take's environment record.
`costs.py --check` fails when this file differs from what it writes.
Everything under `## {BILL}` is the script's; a note goes under a heading of its own.

## {BILL}

## Per take

| _(written by costs.py)_ |

## Pre-freeze walks

| _(written by costs.py)_ |

## Per model

| _(written by costs.py)_ |

## Recorded pauses

| _(written by costs.py)_ |
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="Read what each take and walk cost.")
    ap.add_argument("--write", action="store_true", help="rewrite the tables and the dollar line in COSTS.md")
    ap.add_argument("--check", action="store_true", help="exit 1 if COSTS.md is not what --write writes")
    args = ap.parse_args()

    got = collect()
    path = costs_md()
    if (args.write or args.check) and not path.is_file():
        # Round 2, CP1: COSTS.md is written with the first take. Before it, --check has nothing to
        # compare, which is a pass only while nothing exists that it would have to record; --write then
        # writes nothing, so --check keeps saying so. CP3: once something exists, --write creates the file
        # from TEMPLATE rather than failing to read one.
        registered = registered_rows()
        on_disk = len(got["takes"]) + len(got["walks"]) + len(got["pauses"])
        if registered == 0 and on_disk == 0:
            print("no takes yet" + (f": nothing for {path.name} to record, so it was not written" if args.write else ""))
            return 0
        if args.check:
            print(f"{path.name} does not exist, and {registered} registered row(s) and {on_disk} take, walk "
                  f"or pause record(s) on disk would be in it. Run: python3 evals/gap-study-2/costs.py --write")
            return 1
    if args.write or args.check:
        current = path.read_text() if path.is_file() else TEMPLATE
        wanted = render(current, got)
        if args.write:
            path.write_text(wanted)
            print(f"wrote the tables and the dollar line in {path.name}: {len(got['takes'])} take(s), "
                  f"{len(got['walks'])} walk(s), {len(got['pauses'])} pause(s)")
            return 0
        if wanted != current:
            print(f"{path.name} is NOT what the reader writes. Run: python3 evals/gap-study-2/costs.py --write")
            return 1
        print(f"{path.name} is what the reader writes")
        return 0

    total = len(got["takes"]) + len(got["walks"])
    if total == 0:
        print("no transcript on disk. Nothing was measured, and that is not a cost of zero.")
        return 2

    for kind in ("takes", "walks"):
        rows = got[kind]
        if not rows:
            print(f"{kind}: none on disk")
            continue
        print(f"\n{kind} ({len(rows)}):")
        for r in rows:
            if not r["measured"]:
                print(f"  {r['path'][-58:]}  UNMEASURED — no usage records")
                continue
            print(f"  {r['path'][-58:]}")
            print(f"     model {r['model']}  wall {r['wall_minutes']} min")
            print(f"     input {r['input_tokens']:>7}  output {r['output_tokens']:>7}  "
                  f"cache read {r['cache_read_input_tokens']:>9}  "
                  f"cache write {r['cache_creation_input_tokens']:>8}")

    unmeasured = [r for kind in ("takes", "walks") for r in got[kind] if not r["measured"]]
    if unmeasured:
        print(f"\n{len(unmeasured)} transcript(s) carry no usage records and are reported "
              f"unmeasured, never as zero.")
    print(f"\n{BILL.lower()}: {got['bill']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
