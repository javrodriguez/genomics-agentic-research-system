#!/usr/bin/env python3
"""Unit-economics sheet for pilot 1, generated from its inputs with no hand-entered cost cell.

Row 13 step A (decision 0140, D3; R-193, R-190, R-153, §11.3, §16.4). Stdlib-only; written for
Python 3.6.8 (syntax checked, not executed on 3.6.8).

    python3 scripts/unit_economics.py --log pilot1_log.csv --baseline pilot1_baseline.csv \
        --bench backend_bench.csv --inputs owner_inputs.json --quantities bring_home.txt \
        --out <dir>

writes `<dir>/unit_economics.csv` and `<dir>/unit_economics.md` and prints the same lines.

What the sheet refuses (exit 2, `refused: <reason>` on stderr, nothing written):
- a log that is not exactly the pilot-log format (header comment with nonce, the six columns
  of docs/pilot/pilot_log_vocabulary.json -- a seventh column is a place to type a cost);
- an owner-inputs key outside the closed schema, a liability that is not `unpriced` (a typed
  number is `liability_typed`), a price that is not null;
- a bench row whose derived fields do not recompute: its cost must be `unmetered` under an
  `owned_hardware` or `institutional_allocation` basis; a number there is a hand-typed cost;
- a line starting `quantity` (any case, after leading whitespace) that is not one of the fixed
  shapes (`quantity_malformed`), and a quantity repeated with a different canonical value
  (`quantity_conflict`);
- input that crashes a parser (a NUL byte, runaway nesting): a fixed code, never a traceback;
- a number too large to print to the cent, or an exponent past the decimal context
  (`value_out_of_range`).

Refusal codes are required to be the same on every Python from 3.6 to 3.13, tested by emulating
both sides of each known split (tests/pilot_emulation.py); executed on CPython 3.8.2, 3.8.19,
3.9.6, 3.9.21, 3.10.16, 3.12.9, 3.12.14, 3.13.2 and 3.14.7, not on 3.6, 3.7 or 3.11. To that end
a NUL byte is refused before the csv module sees it (3.11 and later accept one), integers are
never converted through `int()` of their text (3.11 and later, and backports, limit its
digits), and every file is read as UTF-8 whatever the locale.

What it never does: print a free-text field (the owner's strings, a path), compute a margin
without a price, or correct the session cross-check -- a human turn outside every logged span
is printed as a DISCREPANCY and every minute stays exactly as logged. Every ratio is printed
with its numerator and denominator; a zero denominator is `uncomputable`. Identical inputs
give byte-identical outputs; the sheet's head records each input's SHA-256.
"""

import argparse
import csv
import hashlib
import io
import json
import re
import sys
from decimal import Decimal, DecimalException, ROUND_HALF_UP
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
VOCABULARY = REPO / "docs" / "pilot" / "pilot_log_vocabulary.json"

EXIT_REFUSED = 2
BACKENDS = ("local", "homelab", "slurm")
UNMETERED_BASES = ("owned_hardware", "institutional_allocation")
BENCH_COLUMNS = ("backend", "status", "samples", "cpu_s", "wall_s", "cost_usd_per_sample",
                 "cost_basis")
INPUT_KEYS = ("hourly_value_usd", "hourly_value_source", "project_definition", "liability",
              "price_usd")
NUMBER = re.compile(r"^[0-9]+(\.[0-9]+)?$")

# The three bring-home line shapes this sheet grades (docs/pilot/README.md); a line starting
# starting `quantity` in any case after leading whitespace must match one of the first two (rulings
# L4 and n2), every other line is counted and ignored.
QUANTITY_PREFIX = re.compile(r"^\s*quantity\b", re.I)
QUANTITY_SAMPLES = re.compile(r"^quantity samples_in_design ([0-9]+)$")
QUANTITY_CPU = re.compile(r"^quantity cpu_hours (local|homelab|slurm) ([0-9]+(?:\.[0-9]+)?)$")
SESSION_LINE = re.compile(
    r"^human turns: ([0-9]+); inside spans: ([0-9]+); outside spans: ([0-9]+); "
    r"outside minutes: ([0-9]+\.[0-9]{2}); session wall minutes: ([0-9]+\.[0-9]{2}); "
    r"agent active minutes: ([0-9]+\.[0-9]{2}); outside window: ([0-9]+); "
    r"graded ([0-9]+) of \8 records$")


class Refused(Exception):
    """A named refusal; the reason is a fixed code, never input text."""


def vocabulary():
    return json.loads(VOCABULARY.read_text(encoding="utf-8"))


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def two(value):
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def ratio(numerator, denominator):
    """§11.3: numerator and denominator always printed; a zero denominator is uncomputable."""
    if denominator == 0:
        return "uncomputable (%s/%s)" % (numerator, denominator)
    return "%s/%s" % (numerator, denominator)


def read_text(path, code):
    try:
        return Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError, ValueError):
        raise Refused(code)


def csv_rows(text, code):
    """Every row of a CSV text; a parser error (a NUL byte, an oversized field) is `code`.

    The NUL byte is refused here, not left to the csv module: 3.10 and earlier raise on it, 3.11
    and later read it as data, and the refusal code must not depend on which ran."""
    if "\x00" in text:
        raise Refused(code)
    try:
        return list(csv.reader(io.StringIO(text)))
    except csv.Error:
        raise Refused(code)


def canonical_decimal(text):
    """A non-negative decimal's canonical text: no leading zeros, no trailing fractional zeros."""
    whole, _, fraction = text.partition(".")
    whole, fraction = whole.lstrip("0") or "0", fraction.rstrip("0")
    return whole + "." + fraction if fraction else whole


def whole_number(text):
    """The int of a digit string, never through int(text): 3.11 and later cap that conversion's
    digits, so a long count would refuse (or crash) on one Python and pass on another."""
    return int(Decimal(text))


# ---------------------------------------------------------------------------------------------
# The pilot log (D1). Shared with scripts/session_turns.py.

def read_log(path, vocab=None):
    """Every data row of a pilot log, validated; refuses the first malformed line."""
    vocab = vocab or vocabulary()
    lines = read_text(path, "log_unreadable").splitlines()
    if not lines or not re.match(vocab["header_comment_regex"], lines[0]):
        raise Refused("log_header_nonce")
    if len(lines) < 2:
        raise Refused("log_columns")
    header = (csv_rows(lines[1], "log_columns") or [[]])[0]
    if header != vocab["columns"]:
        raise Refused("log_columns")
    rows = []
    for number, line in enumerate(lines[2:], start=3):
        fields = (csv_rows(line, "log_malformed line %d" % number) or [[]])[0]
        if len(fields) != len(header):
            raise Refused("log_row_shape line %d" % number)
        row = dict(zip(header, fields))
        if not re.match(vocab["ts_regex"], row["ts"]):
            raise Refused("log_ts line %d" % number)
        for column in ("stage", "actor", "action", "reason_code"):
            if row[column] not in vocab[column]:
                raise Refused("log_%s line %d" % (column, number))
        if not re.match(vocab["minutes_regex"], row["minutes"]):
            raise Refused("log_minutes line %d" % number)
        row["minutes"] = Decimal(row["minutes"])
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------------------------
# The other inputs.

def read_baseline(path, vocab):
    reader = iter(csv_rows(read_text(path, "baseline_unreadable"), "baseline_malformed"))
    header = next(reader, None)
    if header != vocab["baseline_columns"]:
        raise Refused("baseline_columns")
    hours = {}
    for number, fields in enumerate(reader, start=2):
        if len(fields) != len(header):
            raise Refused("baseline_row_shape line %d" % number)
        row = dict(zip(header, fields))
        if row["stage"] not in vocab["stage"] or row["action"] not in vocab["action"]:
            raise Refused("baseline_vocabulary line %d" % number)
        if row["basis"] not in vocab["baseline_basis"]:
            raise Refused("baseline_basis line %d" % number)
        if not NUMBER.match(row["hours"]):
            raise Refused("baseline_hours line %d" % number)
        hours[row["stage"]] = hours.get(row["stage"], Decimal(0)) + Decimal(row["hours"])
    return hours


def _no_constant(name):
    raise Refused("inputs_not_a_number")


def _no_duplicate(pairs):
    keys = [k for k, _ in pairs]
    if len(keys) != len(set(keys)):
        raise Refused("inputs_duplicate_key")
    return dict(pairs)


def read_inputs(path):
    try:
        data = json.loads(read_text(path, "inputs_unreadable"), parse_float=Decimal,
                          parse_int=Decimal, parse_constant=_no_constant,
                          object_pairs_hook=_no_duplicate)
    except (ValueError, RecursionError):
        raise Refused("inputs_not_json")
    if not isinstance(data, dict):
        raise Refused("inputs_not_object")
    unknown = sorted(set(data) - set(INPUT_KEYS))
    if unknown:
        raise Refused("inputs_unknown_key")
    if sorted(data) != sorted(INPUT_KEYS):
        raise Refused("inputs_missing_key")
    hourly = data["hourly_value_usd"]
    if isinstance(hourly, bool) or not isinstance(hourly, Decimal) or hourly < 0:
        raise Refused("inputs_hourly_value")
    for key in ("hourly_value_source", "project_definition"):
        if not isinstance(data[key], str):
            raise Refused("inputs_%s" % key)
    liability = data["liability"]
    if isinstance(liability, (Decimal, bool)):
        raise Refused("liability_typed")
    if liability != "unpriced":
        raise Refused("liability_not_unpriced")
    if data["price_usd"] is not None:
        raise Refused("price_not_null")
    return hourly


def read_bench(path):
    """Row 8B's backend_bench.csv, read by header name only (the lane's binding to 8B's plan)."""
    rows = csv_rows(read_text(path, "bench_unreadable"), "bench_malformed")
    header = rows[0] if rows else []
    if any(c not in header for c in BENCH_COLUMNS):
        raise Refused("bench_missing_column")
    backends = {}
    for number, fields in enumerate(rows[1:], start=2):
        if not fields:
            continue  # csv.DictReader's rule: a blank line is no row
        if len(fields) != len(header):
            raise Refused("bench_row_shape line %d" % number)
        row = dict(zip(header, fields))
        if row["backend"] not in BACKENDS:
            raise Refused("bench_backend line %d" % number)
        if row["status"] != "COMPLETED":
            raise Refused("bench_status line %d" % number)
        for column in ("samples", "cpu_s", "wall_s"):
            if not NUMBER.match(row[column]):
                raise Refused("bench_number line %d" % number)
        if row["cost_basis"] not in UNMETERED_BASES:
            raise Refused("bench_cost_basis line %d" % number)
        if row["cost_usd_per_sample"] != "unmetered":
            raise Refused("bench_hand_typed_cost line %d" % number)
        backends.setdefault(row["backend"], set()).add(row["cost_basis"])
    return backends


def read_quantities(path):
    """The fixed-format lines of a bring-home file; returns (quantities, graded, total).

    Values are kept as canonical decimal text, so a repeat is compared by value, not spelling,
    and the sheet's text does not depend on line order (ruling L4). Counts stay text: printing a
    Python int of more than 4300 digits fails on 3.11 and later."""
    lines = read_text(path, "quantities_unreadable").splitlines()
    found = {}
    graded = 0

    def keep(key, value):
        if key in found and found[key] != value:
            raise Refused("quantity_conflict %s" % key)
        found[key] = value

    for line in lines:
        m = QUANTITY_SAMPLES.match(line)
        if m:
            keep("samples_in_design", canonical_decimal(m.group(1)))
            graded += 1
            continue
        m = QUANTITY_CPU.match(line)
        if m:
            keep("cpu_hours " + m.group(1), canonical_decimal(m.group(2)))
            graded += 1
            continue
        if QUANTITY_PREFIX.match(line):
            raise Refused("quantity_malformed")
        m = SESSION_LINE.match(line)
        if m:
            turns, inside, outside = (canonical_decimal(m.group(i)) for i in (1, 2, 3))
            if whole_number(inside) + whole_number(outside) != whole_number(turns):
                raise Refused("quantity_session_inconsistent")
            keep("session", (turns, inside, outside, str(Decimal(m.group(4)))))
            graded += 1
    return found, graded, len(lines)


# ---------------------------------------------------------------------------------------------
# The sheet.

def sheet(log, baseline, bench, inputs, quantities):
    vocab = vocabulary()
    rows = read_log(log, vocab)
    base = read_baseline(baseline, vocab)
    hourly = read_inputs(inputs)
    backends = read_bench(bench)
    found, q_graded, q_total = read_quantities(quantities)

    lines = []

    def add(section, item, value):
        lines.append((section, item, str(value)))

    for role, path in (("log", log), ("baseline", baseline), ("bench", bench),
                       ("inputs", inputs), ("quantities", quantities)):
        add("input", role + " sha256", sha256(path))
    seen = len(read_text(log, "log_unreadable").splitlines()) - 2
    add("log", "graded", "%d of %d rows" % (len(rows), seen))
    add("quantities", "graded", "%d of %d lines" % (q_graded, q_total))

    samples = found.get("samples_in_design")
    add("quantity", "samples_in_design", "unmeasured" if samples is None else samples)
    for backend in BACKENDS:
        cpu = found.get("cpu_hours " + backend)
        add("quantity", "cpu_hours " + backend, "unmeasured" if cpu is None else cpu)

    verification = set(vocab["verification_actions"])
    human = [r for r in rows if r["actor"] == "human"]
    stages = [s for s in vocab["stage"]
              if any(r["stage"] == s for r in rows) or s in base]

    # Hours by stage exclude verification actions; verification is its own line. Each human
    # minute lands in exactly one of the two (the partition the tests hold).
    working_minutes = Decimal(0)
    for stage in stages:
        minutes = sum((r["minutes"] for r in human
                       if r["stage"] == stage and r["action"] not in verification), Decimal(0))
        working_minutes += minutes
        add("hours by stage", stage, "%s h (%s min) x hourly = $%s"
            % (two(minutes / 60), two(minutes), two(minutes * hourly / 60)))
    verify_minutes = sum((r["minutes"] for r in human if r["action"] in verification),
                         Decimal(0))
    add("verification", "hours", "%s h (%s min) x hourly = $%s"
        % (two(verify_minutes / 60), two(verify_minutes), two(verify_minutes * hourly / 60)))

    for backend in BACKENDS:
        cpu = found.get("cpu_hours " + backend)
        cpu_text = "unmeasured" if cpu is None else str(cpu)
        if backend not in backends:
            add("compute", backend, "unmeasured (no bench row); cpu_hours %s" % cpu_text)
        else:
            add("compute", backend, "unmetered (%s); cpu_hours %s"
                % ("/".join(sorted(backends[backend])), cpu_text))

    agent_minutes = sum((r["minutes"] for r in rows if r["actor"] == "agent"), Decimal(0))
    tool_minutes = sum((r["minutes"] for r in rows if r["actor"] == "tool"), Decimal(0))
    add("agent", "cost", "unmetered (subscription); quantity %s min" % two(agent_minutes))
    add("tool", "minutes", "%s min (quantity)" % two(tool_minutes))
    add("liability", "cost", "unpriced")

    human_minutes = working_minutes + verify_minutes
    dollars = two(human_minutes * hourly / 60)
    metered = [b for b in BACKENDS if b in backends]
    unmeasured = [b for b in BACKENDS if b not in backends]
    # The cost line names every part it does not price (§16.4): metered-but-unpriced compute
    # and compute with no bench row at all are different claims, so each is named by backend.
    compute = "".join(" + %s compute (%s)" % (label, ", ".join(names))
                      for label, names in (("unmetered", metered), ("unmeasured", unmeasured))
                      if names)
    add("cost", "total",
        "$%s%s + unmetered agent + unpriced liability" % (dollars, compute))
    add("cost", "unmetered share", "compute %s; agent %s min; liability unpriced"
        % (", ".join(metered) or "none measured", two(agent_minutes)))
    if samples is None:
        add("cost", "per sample", "uncomputable (samples_in_design unmeasured)")
    elif samples == "0":
        add("cost", "per sample", ratio("$%s" % dollars, 0))
    else:
        add("cost", "per sample", "$%s/%s = $%s"
            % (dollars, samples, two(dollars / Decimal(samples))))
    add("margin", "margin", "uncomputable: no price (R-193)")

    # Ruling L3: the total is like for like, over the stages that have a baseline row only; the
    # human hours of the other stages are printed on their own line and never subtracted.
    missing_base, covered_minutes, uncovered_minutes = [], Decimal(0), Decimal(0)
    for stage in stages:
        human_stage = sum((r["minutes"] for r in human if r["stage"] == stage), Decimal(0))
        if stage not in base:
            missing_base.append(stage)
            uncovered_minutes += human_stage
            add("time saved", stage, "unmeasured (no baseline row); human %s h"
                % two(human_stage / 60))
            continue
        covered_minutes += human_stage
        add("time saved", stage, "baseline %s h - human %s h = %s h"
            % (two(base[stage]), two(human_stage / 60), two(base[stage] - human_stage / 60)))
    base_total = sum(base.values(), Decimal(0))
    add("time saved", "total", "baseline %s h - human %s h = %s h"
        % (two(base_total), two(covered_minutes / 60), two(base_total - covered_minutes / 60)))
    if missing_base:
        add("human hours without a baseline", "human hours without a baseline", "%s (%s)"
            % (two(uncovered_minutes / 60), ", ".join(missing_base)))

    for stage in stages:
        add("interventions", stage, sum(1 for r in human if r["stage"] == stage))
    add("interventions", "total", len(human))
    for actor in vocab["actor"]:
        add("row coverage", actor, ratio(sum(1 for r in rows if r["actor"] == actor), len(rows)))
    add("ratio", "verification share of human minutes",
        ratio(two(verify_minutes), two(human_minutes)))

    session = found.get("session")
    if session is None:
        add("cross-check", "M4", "unmeasured")
    else:
        turns, inside, outside, outside_minutes = session
        add("cross-check", "M4", "human turns in 02_02 session: %s; inside a human span: %s; "
            "outside any span: %s (%s min)" % (turns, inside, outside, outside_minutes))
        if outside != "0":
            add("cross-check", "DISCREPANCY",
                "%s human turns outside any logged span" % outside)
    return lines


def render_csv(lines):
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["section", "item", "value"])
    writer.writerows(lines)
    return out.getvalue()


def render_md(lines):
    out = ["# Unit economics, pilot 1 (generated by unit_economics.py; do not edit)"]
    section = None
    for sec, item, value in lines:
        if sec != section:
            out.extend(["", "## " + sec, ""])
            section = sec
        if sec == "cross-check" and item == "DISCREPANCY":
            out.append("- DISCREPANCY: " + value)
        else:
            out.append("- %s: %s" % (item, value))
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Generate the pilot-1 unit-economics sheet.")
    for flag in ("log", "baseline", "bench", "inputs", "quantities", "out"):
        ap.add_argument("--" + flag, required=True)
    args = ap.parse_args(argv)
    try:
        lines = sheet(args.log, args.baseline, args.bench, args.inputs, args.quantities)
    except Refused as why:
        sys.stderr.write("refused: %s\n" % why)
        return EXIT_REFUSED
    except DecimalException:
        # A number past the decimal context (28 digits, or an exponent past Emax, which raises
        # Overflow rather than InvalidOperation) cannot be printed to the cent.
        sys.stderr.write("refused: value_out_of_range\n")
        return EXIT_REFUSED
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "unit_economics.csv").write_text(render_csv(lines), encoding="utf-8")
    (out / "unit_economics.md").write_text(render_md(lines), encoding="utf-8")
    for sec, item, value in lines:
        if sec == "cross-check" and item == "DISCREPANCY":
            print("DISCREPANCY: " + value)
        elif sec == item:
            print("%s: %s" % (sec, value))
        else:
            print("%s %s: %s" % (sec, item, value))
    return 0


if __name__ == "__main__":
    sys.exit(main())
