#!/usr/bin/env python3
"""The pilot log's only writer (row 13 step B; decisions 0140 D1, 0141).

    pilot_log.py begin  --log <path> --stage S --action A --reason R
    pilot_log.py end    --log <path> <span-id>
    pilot_log.py abort  --log <path> <span-id>
    pilot_log.py check  --log <path>
    pilot_log.py import-tool --log <path> --manifest <manifest.json>      (human only)

The log (`projects/<title>/pilot/pilot1_log.csv`) has exactly the columns
`ts,stage,actor,action,reason_code,minutes` under one header comment
`# gars-pilot-log v1 nonce=<32 hex>`, and no free-text column, so it cannot carry a sample name.
Its sidecar `<log>.open.json` carries the same nonce, the open spans and the imported
sub-stages. `ts` is a span's start and `minutes` is computed from two clock readings; neither is
ever typed.

The actor is a launch-time fact: the registry's argv for every `pilot_log.*` entry carries the
fixed token `--launched-by-dispatcher`, which no call's JSON can supply or remove. With it the
actor is `agent`; without it `human`. The guard refuses the direct spelling of this file in an
agent session, so an agent reaches it only with the token. `end` and `abort` are allowed only to
the actor that began the span; `abort` appends nothing (a forgotten span is dropped, never
back-filled). A break is `abort` of every open span, then a new `begin` after it.

Every refusal prints `refused: <code>` on stdout and exits 2; no refusal quotes an input. The
vocabulary is embedded here and bound to `docs/pilot/pilot_log_vocabulary.json` by a drift test.
Stdlib only; written for Python 3.6.8.
"""
import argparse
import csv
import datetime
import fcntl
import io
import json
import os
import re
import secrets
import sys
import time
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

TOKEN = "--launched-by-dispatcher"
FORMAT = "gars-pilot-log v1"
COLUMNS = ["ts", "stage", "actor", "action", "reason_code", "minutes"]
HEADER = re.compile(r"^# gars-pilot-log v1 nonce=([0-9a-f]{32})$")
TS = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")
MINUTES = re.compile(r"^[0-9]+\.[0-9]{2}$")
SPAN = re.compile(r"^[0-9a-f]{16}$")
VOCABULARY = {
    "stage": ["00_register", "01_samplesheets", "02_01_counts", "02_02_de", "rerun", "report",
              "other"],
    "actor": ["human", "agent", "tool"],
    "action": ["read_contract", "resolve_inputs", "check", "prepare", "submit", "poll_status",
               "collect", "summarize", "fill_config", "approve_plan", "fix_input", "rerun",
               "review_output", "verify_result", "interpret", "draft_claims", "write_report",
               "wait_queue", "compute", "setup", "break", "other"],
    "reason_code": ["approval", "fix", "rerun", "data", "interpretation", "other"],
}
# The pilot's protocol stages (0140): the DE stage and its one re-run. `check` fails while
# either has no row.
PROTOCOL_STAGES = ("02_02_de", "rerun")
# import-tool's stage, from the manifest's wrapper.
WRAPPER_STAGE = {"rnaseq-de": "02_02_de", "nfcore-rnaseq-wrapper": "02_01_counts"}
EXIT_OK, EXIT_FAILED, EXIT_REFUSED = 0, 1, 2


class Refused(Exception):
    pass


def now():
    """The clock. Tests patch this; nothing else supplies a time."""
    return time.time()


def stamp(epoch):
    return datetime.datetime.fromtimestamp(epoch, datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


def minutes(start, end):
    if end < start:
        raise Refused("clock_backwards")
    value = (Decimal(repr(end)) - Decimal(repr(start))) / Decimal(60)
    return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def sidecar_path(log):
    return Path(str(log) + ".open.json")


def lock_path(log):
    return Path(str(log) + ".lock")


def read_log(log):
    """(nonce, rows) of an existing log; every row is validated against the vocabulary."""
    try:
        data = log.read_bytes()
        text = data.decode("utf-8")
    except (OSError, UnicodeError):
        raise Refused("log_unreadable")
    if "\x00" in text or "\r" in text:
        raise Refused("log_malformed")
    lines = text.split("\n")
    if lines[-1] != "":
        raise Refused("log_malformed")
    lines.pop()
    if not lines:
        raise Refused("nonce_missing")
    match = HEADER.match(lines[0])
    if not match:
        raise Refused("nonce_missing")
    if len(lines) < 2 or lines[1] != ",".join(COLUMNS):
        raise Refused("log_malformed line 2")
    rows = []
    for number, line in enumerate(lines[2:], 3):
        try:
            cells = next(csv.reader([line]))
        except (csv.Error, StopIteration):
            raise Refused("log_malformed line %d" % number)
        if len(cells) != len(COLUMNS):
            raise Refused("log_malformed line %d" % number)
        row = dict(zip(COLUMNS, cells))
        if not TS.match(row["ts"]) or not MINUTES.match(row["minutes"]) \
                or any(row[key] not in VOCABULARY[key]
                       for key in ("stage", "actor", "action", "reason_code")):
            raise Refused("log_malformed line %d" % number)
        rows.append(row)
    return match.group(1), rows


def read_sidecar(log):
    try:
        data = json.loads(sidecar_path(log).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, RecursionError):
        raise Refused("sidecar_unreadable")
    if not isinstance(data, dict) or set(data) != {"format", "nonce", "spans", "imported"} \
            or data["format"] != FORMAT or not isinstance(data["spans"], dict) \
            or not isinstance(data["imported"], list):
        raise Refused("sidecar_malformed")
    if not isinstance(data["nonce"], str) or not re.match(r"^[0-9a-f]{32}$", data["nonce"]):
        raise Refused("nonce_missing")
    return data


def load(log, create=False):
    """(sidecar, rows). A log and its sidecar exist together or not at all; their nonces are
    equal. Only `begin` creates them, and only when both are absent."""
    have_log, have_side = os.path.lexists(str(log)), os.path.lexists(str(sidecar_path(log)))
    if not have_log and not have_side:
        if not create:
            raise Refused("log_missing")
        nonce = secrets.token_hex(16)
        log.parent.mkdir(parents=True, exist_ok=True)
        write_new(log, "# %s nonce=%s\n%s\n" % (FORMAT, nonce, ",".join(COLUMNS)))
        side = {"format": FORMAT, "nonce": nonce, "spans": {}, "imported": []}
        save(log, side, new=True)
        return side, []
    if not have_side:
        raise Refused("sidecar_missing")
    if not have_log:
        raise Refused("log_missing")
    for path in (log, sidecar_path(log)):
        if os.path.islink(str(path)) or not path.is_file():
            raise Refused("log_not_regular")
    nonce, rows = read_log(log)
    side = read_sidecar(log)
    if side["nonce"] != nonce:
        raise Refused("nonce_mismatch")
    return side, rows


def write_new(path, text):
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with io.open(fd, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def save(log, side, new=False):
    text = json.dumps(side, indent=2, sort_keys=True) + "\n"
    if new:
        write_new(sidecar_path(log), text)
        return
    tmp = Path(str(sidecar_path(log)) + ".tmp")
    with io.open(str(tmp), "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    os.replace(str(tmp), str(sidecar_path(log)))


def append(log, row):
    buffer = io.StringIO()
    csv.writer(buffer, lineterminator="\n").writerow([row[key] for key in COLUMNS])
    with io.open(str(log), "a", encoding="utf-8", newline="") as fh:
        fh.write(buffer.getvalue())


def begin(log, stage, action, reason, actor):
    for key, value in (("stage", stage), ("action", action), ("reason_code", reason)):
        if value not in VOCABULARY[key]:
            raise Refused("vocabulary_" + key)
    side, _ = load(log, create=True)
    span = secrets.token_hex(8)
    while span in side["spans"]:
        span = secrets.token_hex(8)
    side["spans"][span] = {"actor": actor, "stage": stage, "action": action, "reason": reason,
                           "start": now(), "status": "open"}
    save(log, side)
    return "begin: span %s; actor %s" % (span, actor)


def owned_open_span(side, span, actor):
    if not SPAN.match(span or ""):
        raise Refused("span_malformed")
    entry = side["spans"].get(span)
    if entry is None:
        raise Refused("span_unknown")
    if entry["status"] != "open":
        raise Refused("span_" + entry["status"])
    if entry["actor"] != actor:
        raise Refused("actor_mismatch")
    return entry


def end(log, span, actor):
    side, _ = load(log)
    entry = owned_open_span(side, span, actor)
    value = minutes(entry["start"], now())
    append(log, {"ts": stamp(entry["start"]), "stage": entry["stage"], "actor": entry["actor"],
                 "action": entry["action"], "reason_code": entry["reason"], "minutes": value})
    entry["status"] = "closed"
    save(log, side)
    return "end: span %s; minutes %s" % (span, value)


def abort(log, span, actor):
    side, _ = load(log)
    entry = owned_open_span(side, span, actor)
    entry["status"] = "aborted"
    save(log, side)
    return "abort: span %s" % span


def check(log):
    side, rows = load(log)
    count = dict((actor, sum(1 for r in rows if r["actor"] == actor))
                 for actor in VOCABULARY["actor"])
    open_spans = sum(1 for s in side["spans"].values() if s.get("status") == "open")
    line = ("rows: %d; human: %d; agent: %d; tool: %d; open spans: %d; nonce: ok"
            % (len(rows), count["human"], count["agent"], count["tool"], open_spans))
    missing = [s for s in PROTOCOL_STAGES if not any(r["stage"] == s for r in rows)]
    problems = (["open spans"] if open_spans else []) + ["no rows: " + s for s in missing]
    return line, problems


def elapsed_minutes(text):
    """sacct Elapsed, `[D-]HH:MM:SS`, as exact minutes."""
    match = re.match(r"^(?:([0-9]+)-)?([0-9]{1,2}):([0-9]{2}):([0-9]{2})$", text or "")
    if not match:
        raise Refused("elapsed_malformed")
    days, hours, mins, secs = (int(g or 0) for g in match.groups())
    seconds = ((days * 24 + hours) * 60 + mins) * 60 + secs
    return str((Decimal(seconds) / Decimal(60)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def import_tool(log, manifest_path):
    """`tool` rows from the executor's record: wait_queue (Start - Submit) and compute
    (sacct Elapsed). A sub-stage's submission is imported once."""
    try:
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, RecursionError):
        raise Refused("manifest_unreadable")
    if not isinstance(manifest, dict):
        raise Refused("manifest_unreadable")
    stage_name = WRAPPER_STAGE.get(manifest.get("wrapper"))
    key = manifest.get("idempotency_key")
    if stage_name is None:
        raise Refused("stage_unknown")
    if not isinstance(key, str) or not re.match(r"^[0-9a-f]{16,128}$", key):
        raise Refused("idempotency_key_missing")
    substage = Path(manifest_path).resolve().parent.parent
    root = substage
    for candidate in [substage] + list(substage.parents):
        if (candidate / "_config").is_dir():
            root = candidate
            break
    try:
        record = json.loads((root / ".gars_submissions" / (key + ".json")).read_text(
            encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, RecursionError):
        raise Refused("no_sacct_record")
    if not isinstance(record, dict) or record.get("executor") != "slurm":
        raise Refused("no_sacct_record")
    submitted, started = record.get("submitted_at"), record.get("started_at")
    if type(submitted) not in (int, float) or type(started) not in (int, float):
        raise Refused("no_sacct_record")
    resources = manifest.get("resources")
    compute = elapsed_minutes(resources.get("Elapsed") if isinstance(resources, dict) else None)
    side, _ = load(log)
    if key in side["imported"]:
        raise Refused("already_imported")
    wait = minutes(submitted, started)
    for ts, action, value in ((submitted, "wait_queue", wait), (started, "compute", compute)):
        append(log, {"ts": stamp(ts), "stage": stage_name, "actor": "tool", "action": action,
                     "reason_code": "other", "minutes": value})
    side["imported"].append(key)
    save(log, side)
    return "import-tool: rows 2; wait_queue %s; compute %s" % (wait, compute)


def parser():
    ap = argparse.ArgumentParser(description="The pilot log's writer (decision 0141).")
    sub = ap.add_subparsers(dest="verb")
    for name in ("begin", "end", "abort", "check", "import-tool"):
        p = sub.add_parser(name)
        p.add_argument("--log", required=True)
        p.add_argument(TOKEN, dest="dispatcher", action="store_true")
        if name == "begin":
            p.add_argument("--stage", required=True)
            p.add_argument("--action", required=True)
            p.add_argument("--reason", required=True)
        if name in ("end", "abort"):
            p.add_argument("span")
        if name == "import-tool":
            p.add_argument("--manifest", required=True)
    return ap


def main(argv=None):
    try:
        args = parser().parse_args(argv)
    except SystemExit:
        print("refused: usage")
        return EXIT_REFUSED
    if not args.verb:
        print("refused: usage")
        return EXIT_REFUSED
    actor = "agent" if args.dispatcher else "human"
    log = Path(args.log)
    try:
        with lock(log, create=args.verb == "begin"):
            if args.verb == "begin":
                print(begin(log, args.stage, args.action, args.reason, actor))
            elif args.verb == "end":
                print(end(log, args.span, actor))
            elif args.verb == "abort":
                print(abort(log, args.span, actor))
            elif args.verb == "check":
                line, problems = check(log)
                print(line)
                if problems:
                    print("check failed: " + "; ".join(problems))
                    return EXIT_FAILED
            else:
                if actor != "human":
                    raise Refused("human_only")
                print(import_tool(log, args.manifest))
    except Refused as why:
        print("refused: %s" % why)
        return EXIT_REFUSED
    return EXIT_OK


class lock(object):
    """An exclusive lock beside the log, so two writers never interleave."""

    def __init__(self, log, create=False):
        self.path = lock_path(log)
        self.create = create
        self.handle = None

    def __enter__(self):
        if not self.path.parent.is_dir():
            if not self.create:
                raise Refused("log_missing")
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
            except OSError:
                raise Refused("log_unwritable")
        try:
            self.handle = open(str(self.path), "a")
        except OSError:
            raise Refused("log_unwritable")
        fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX)
        return self

    def __exit__(self, *exc):
        fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        self.handle.close()
        return False


if __name__ == "__main__":
    sys.exit(main())
