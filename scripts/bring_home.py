#!/usr/bin/env python3
"""Bring home, from the cluster, only what may leave it (row 13 step B; decision 0141, D6).

    python3 scripts/bring_home.py --out bring_home.txt [--rerun-console <f>] [--comparison <f>]
        [--rerun-diff <f>] [--manifest-check <f>] [--pilot-log <f>] [--pilot-check <f>]
        [--session-turns <f>] [--summary <f>] [--bench-evidence <f>]

For each input it writes `== <kind> sha256=<hex of the raw file> ==`, then only the lines its
keep-list allows; the raw files stay on the cluster and their hashes travel inside the paste. It
ends `bring-home: <k> sections; withheld lines: <w>`.

- rerun console and comparison.json: `reproduction: k/n`, `graded k of k outputs`, per artifact
  its path-kind (the OUTPUTS type, never the path), mode, match, metric and value, per run its job
  and match, and its reason cut to the closed prefix before the first `:` (the tail withheld);
- manifest_check: the group lines and the summary; an `ERROR` line becomes `ERROR withheld`;
- pilot log and its check: the rows, in the closed vocabulary; a value outside it is refused;
- rerun_diff, session_turns, rnaseq_de summary: their fixed-format lines only;
- bench evidence: row 8B's allowlisted fields, and the `quantity cpu_hours` line they give.

A line matching no format is withheld and counted. The keep-lists are `_system/tools/
closed_output.py`'s, the dispatcher's own, so the two cannot drift apart. A missing input exits 2
and writes nothing. Stdlib only; written for Python 3.6.8.
"""
import argparse
import hashlib
import json
import re
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "gars" / "_system"))
sys.path.insert(0, str(REPO / "scripts"))
from tools import closed_output as co  # noqa: E402
import pilot_log  # noqa: E402
from unit_economics import SESSION_LINE  # noqa: E402

KINDS = (("rerun_console", "rerun-console"), ("comparison", "comparison"),
         ("rerun_diff", "rerun-diff"), ("manifest_check", "manifest-check"),
         ("pilot_log", "pilot-log"), ("pilot_check", "pilot-check"),
         ("session_turns", "session-turns"), ("summary", "summary"),
         ("bench_evidence", "bench-evidence"))
# Row 8B's evidence allowlist (decision 0102), and the backends a quantity line may name.
BENCH_FIELDS = ("backend", "venue", "status", "workload_id", "workload_sha256", "samples",
                "wall_s", "cpu_s", "max_rss_mb", "queue_wait_s", "python_version",
                "gars_commit", "measured_at", "cost_usd_per_sample", "cost_basis")
BENCH_VALUE = re.compile(r"^[A-Za-z0-9_.:+-]{1,80}$")
BACKENDS = ("local", "homelab", "slurm")


class Refused(Exception):
    pass


def lines_of(raw):
    return raw.decode("utf-8", "replace").splitlines()


def schema_groups():
    path = REPO / "gars" / "_references" / "manifest_schema.json"
    return [g["name"] for g in json.loads(path.read_text(encoding="utf-8"))["groups"]]


def run_line(number, job, match, reason):
    prefix = co.reason_prefix(reason) if reason is not None else "none"
    return ("run %s job=%s match=%s reason=%s"
            % (number, job if job is not None else "none", "yes" if match else "no",
               prefix or "withheld"))


def rerun_console(raw):
    kept, withheld = [], 0
    for line in lines_of(raw):
        artifact = co.BRING_HOME["rerun_artifact"].match(line)
        failed = co.BRING_HOME["rerun_failed"].match(line)
        if any(p.match(line) for p in co.BRING_HOME["rerun_console"]):
            kept.append(line)
        elif artifact:
            kept.append("artifact %s %s match=%s %s=%s" % ((co.path_kind(artifact.group(1)),)
                                                           + artifact.groups()[1:]))
        elif failed:
            prefix = co.reason_prefix(failed.group(2))
            kept.append("run %s match=no reason=%s" % (failed.group(1), prefix or "withheld"))
            withheld += 1 if prefix is None or failed.group(2).strip() != prefix else 0
        else:
            withheld += 1
    return kept, withheld


def comparison(raw):
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError, RecursionError):
        return ["comparison: withheld"], 1
    if not isinstance(data, dict) or not isinstance(data.get("runs"), list):
        return ["comparison: withheld"], 1
    kept, withheld = [], 0
    for key in sorted(data):
        if key not in ("runs", "requested", "tolerances_sha256", "wrapper_sha256"):
            withheld += 1
    for key in ("tolerances_sha256", "wrapper_sha256"):
        value = data.get(key)
        if isinstance(value, str) and re.match(r"^[0-9a-f]{64}$", value):
            kept.append("%s %s" % (key, value))
    requested = data.get("requested")
    matched = 0
    for run in data["runs"]:
        number = run.get("run") if isinstance(run, dict) else None
        if type(number) is not int:
            withheld += 1
            continue
        job = run.get("job")
        job = job if isinstance(job, str) and co.JOB_ID.match(job) else (
            None if job is None else "withheld")
        reason = run.get("reason")
        kept.append(run_line(number, job, run.get("match") is True, reason))
        if isinstance(reason, str) and reason.strip() != co.reason_prefix(reason):
            withheld += 1
        withheld += len([k for k in run if k not in ("run", "job", "match", "reason",
                                                     "artifacts")])
        artifacts = run.get("artifacts") if isinstance(run.get("artifacts"), list) else []
        for artifact in artifacts:
            if not isinstance(artifact, dict):
                withheld += 1
                continue
            value = str(artifact.get("value"))
            mode, metric = artifact.get("mode"), artifact.get("metric")
            if mode not in ("byte_stable", "numeric_tolerance") \
                    or metric not in ("sha256_equal", "max_absolute_error") \
                    or not re.match("^" + co.NUMBER + "$", value):
                withheld += 1
                continue
            kept.append("run %s artifact %s %s match=%s %s=%s"
                        % (number, co.path_kind(artifact.get("path")), mode,
                           "yes" if artifact.get("match") is True else "no", metric, value))
        kept.append("run %s graded %d outputs" % (number, len(artifacts)))
        matched += int(run.get("match") is True)
    if type(requested) is int:
        kept.append("reproduction: %d/%d" % (matched, requested))
    return kept, withheld


def fixed_lines(raw, patterns):
    kept, withheld = [], 0
    for line in lines_of(raw):
        if any(p.match(line) for p in patterns):
            kept.append(line)
        else:
            withheld += 1
    return kept, withheld


def manifest_check(raw):
    groups = schema_groups()
    kept, withheld = [], 0
    for line in lines_of(raw):
        group = co.BRING_HOME["manifest_group"].match(line)
        if line.startswith("ERROR"):
            kept.append("ERROR withheld")
            withheld += 1
        elif group and group.group(2) in groups:
            kept.append(line)
        elif any(p.match(line) for p in co.BRING_HOME["manifest_check"]):
            kept.append(line)
        else:
            withheld += 1
    return kept, withheld


def pilot_log_rows(path):
    try:
        pilot_log.read_log(path)
    except pilot_log.Refused:
        raise Refused("pilot_log_value")
    return lines_of(path.read_bytes()), 0


def pilot_check(raw):
    kept, withheld = co.pilot_lines(raw.decode("utf-8", "replace"))
    if withheld or not kept or not all(line.startswith(("rows: ", "check failed: "))
                                       for line in kept):
        raise Refused("pilot_check_value")
    return kept, 0


def session_turns(raw):
    return fixed_lines(raw, [SESSION_LINE])


def summary(raw):
    stdout, _ = co.filter_output("rnaseq_de.summary", raw.decode("utf-8", "replace"), "", 0,
                                 keep=co.SUMMARY_KEYS)
    data = json.loads(stdout)
    if data.get("withheld") is True:
        return ["summary: withheld"], 1
    withheld = len([v for v in data.values() if v == co.WITHHELD])
    kept = []
    for key in ("status", "genes_tested", "padj_lt_0.1", "na_padj"):
        if data.get(key, co.WITHHELD) != co.WITHHELD:
            kept.append("summary %s %s" % (key, data[key]))
    split = data.get("padj_lt_0.05")
    if isinstance(split, dict) and co.WITHHELD not in split.values():
        kept.append("summary padj_lt_0.05 up %s down %s" % (split["up"], split["down"]))
    gate = data.get("gate")
    if isinstance(gate, list) and co.WITHHELD not in gate:
        kept.append("summary gate %s" % (",".join(gate) or "none"))
    samples = data.get("samples_in_design")
    if type(samples) is int:
        kept.append("quantity samples_in_design %d" % samples)
    return kept, withheld


def bench_evidence(raw):
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError, RecursionError):
        return ["bench: withheld"], 1
    if not isinstance(data, dict):
        return ["bench: withheld"], 1
    kept, withheld = [], len([k for k in data if k not in BENCH_FIELDS])
    for key in BENCH_FIELDS:
        value = data.get(key)
        if value is None or isinstance(value, bool):
            text = "null" if value is None else None
        elif isinstance(value, (int, float)):
            text = repr(value)
        elif isinstance(value, str) and BENCH_VALUE.match(value):
            text = value
        else:
            text = None
        if text is None:
            withheld += 1
        else:
            kept.append("bench %s %s" % (key, text))
    cpu = data.get("cpu_s")
    if data.get("status") == "COMPLETED" and data.get("backend") in BACKENDS \
            and type(cpu) in (int, float) and cpu >= 0:
        hours = (Decimal(repr(cpu)) / Decimal(3600)).quantize(Decimal("0.01"),
                                                             rounding=ROUND_HALF_UP)
        kept.append("quantity cpu_hours %s %s" % (data["backend"], hours))
    return kept, withheld


READERS = {"rerun_console": rerun_console, "comparison": comparison,
           "rerun_diff": lambda raw: fixed_lines(raw, co.BRING_HOME["rerun_diff"]),
           "manifest_check": manifest_check, "pilot_check": pilot_check,
           "session_turns": session_turns, "summary": summary,
           "bench_evidence": bench_evidence}


def build(inputs):
    out, sections, withheld = [], 0, 0
    for key, kind in KINDS:
        path = inputs.get(key)
        if path is None:
            continue
        path = Path(path)
        if not path.is_file():
            raise Refused("input_missing " + kind)
        raw = path.read_bytes()
        out.append("== %s sha256=%s ==" % (kind, hashlib.sha256(raw).hexdigest()))
        kept, count = pilot_log_rows(path) if key == "pilot_log" else READERS[key](raw)
        out.extend(kept)
        sections += 1
        withheld += count
    out.append("bring-home: %d sections; withheld lines: %d" % (sections, withheld))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Bring home only what may leave the cluster.")
    ap.add_argument("--out", required=True)
    for key, kind in KINDS:
        ap.add_argument("--" + kind, dest=key)
    args = ap.parse_args(argv)
    try:
        lines = build(vars(args))
    except Refused as why:
        sys.stderr.write("refused: %s\n" % why)
        return 2
    Path(args.out).write_text("".join(line + "\n" for line in lines), encoding="utf-8")
    print(lines[-1])
    return 0


if __name__ == "__main__":
    sys.exit(main())
