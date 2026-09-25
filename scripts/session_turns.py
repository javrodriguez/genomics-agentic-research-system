#!/usr/bin/env python3
"""Session cross-check (M4): human turns in an agent session against the logged human spans.

Row 13 step A (decision 0140, D4b and ruling L1). Stdlib only; runs on Python 3.6.8.

    python3 scripts/session_turns.py --transcript <session.jsonl> --log <pilot1_log.csv> \
        --stage 02_02_de

Every line of the transcript is one record and must classify:
- `type == "user"` with `isMeta` true: a meta record (non-human);
- `type == "user"` whose content is all `tool_result` blocks: a tool result (non-human);
- any other `type == "user"` record (string content, or blocks none of which is a
  `tool_result`): a human turn;
- `type == "assistant"`: an agent record.
Each record needs an ISO-8601 `timestamp` with `Z` or a numeric offset. Anything else -- another
record type, a missing or unparseable timestamp, content mixing `tool_result` with other blocks,
a blank line -- is unclassifiable and exits 2; no record is skipped.

A human turn is inside when its timestamp falls within a `human` span (`ts` to `ts + minutes`)
of the stage. `outside minutes` (ruling L1) is a LOWER BOUND on unlogged human attention: each
outside turn's interval runs from the latest record strictly earlier in time to the turn, is
clipped to the part outside every human span of the stage, and the union of those intervals is
measured once, rounded half-up to two decimals. It is never added to or subtracted from any
logged minute.

Prints one line of numbers only; never message content, a path or an identifier:
`human turns: <t>; inside spans: <i>; outside spans: <o>; outside minutes: <m>; session wall
minutes: <w>; agent active minutes: <a>; graded <n> of <n> records`.
"""

import argparse
import calendar
import json
import re
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import unit_economics as ue  # noqa: E402 -- the one pilot-log reader

EXIT_REFUSED = 2
MICROS_PER_MINUTE = 60 * 1000000
TIMESTAMP = re.compile(r"^([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})"
                       r"(\.[0-9]+)?(Z|[+-][0-9]{2}:?[0-9]{2})$")


def micros(text):
    """Epoch microseconds of an ISO-8601 timestamp, or None; no datetime.fromisoformat."""
    if not isinstance(text, str):
        return None
    m = TIMESTAMP.match(text)
    if not m:
        return None
    year, month, day, hour, minute, second = (int(m.group(i)) for i in range(1, 7))
    if not (1 <= month <= 12 and 1 <= day <= calendar.monthrange(year, month)[1]
            and hour < 24 and minute < 60 and second < 60):
        return None
    fraction = m.group(7) or ".0"
    sub = int((fraction[1:] + "000000")[:6])
    zone = m.group(8)
    offset = 0
    if zone != "Z":
        digits = zone[1:].replace(":", "")
        oh, om = int(digits[:2]), int(digits[2:])
        if oh > 23 or om > 59:
            return None
        offset = (oh * 60 + om) * (1 if zone[0] == "+" else -1)
    seconds = calendar.timegm((year, month, day, hour, minute, second)) - offset * 60
    return seconds * 1000000 + sub


def classify(record):
    """'human', 'tool_result', 'meta' or 'assistant'; None when unclassifiable."""
    if not isinstance(record, dict) or micros(record.get("timestamp")) is None:
        return None
    kind = record.get("type")
    if kind == "assistant":
        return "assistant"
    if kind != "user":
        return None
    meta = record.get("isMeta", False)
    if not isinstance(meta, bool):
        return None
    if meta:
        return "meta"
    message = record.get("message")
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    if isinstance(content, str):
        return "human"
    if not isinstance(content, list) or not content:
        return None
    if not all(isinstance(b, dict) and isinstance(b.get("type"), str) for b in content):
        return None
    results = [b["type"] == "tool_result" for b in content]
    if all(results):
        return "tool_result"
    if any(results):
        return None
    return "human"


def subtract(interval, spans):
    """The parts of [start, end] lying outside every span."""
    pieces = [interval]
    for s, e in spans:
        cut = []
        for a, b in pieces:
            if e <= a or s >= b:
                cut.append((a, b))
                continue
            if a < s:
                cut.append((a, s))
            if e < b:
                cut.append((e, b))
        pieces = cut
    return [(a, b) for a, b in pieces if b > a]


def union_length(intervals):
    total, current = 0, None
    for a, b in sorted(intervals):
        if current is None or a > current[1]:
            if current is not None:
                total += current[1] - current[0]
            current = [a, b]
        else:
            current[1] = max(current[1], b)
    if current is not None:
        total += current[1] - current[0]
    return total


def minutes(micro):
    return (Decimal(micro) / MICROS_PER_MINUTE).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def count(transcript, log, stage):
    vocab = ue.vocabulary()
    if stage not in vocab["stage"]:
        raise ue.Refused("stage")
    spans = []
    for row in ue.read_log(log, vocab):
        if row["actor"] == "human" and row["stage"] == stage:
            start = micros(row["ts"])
            spans.append((start, start + int(row["minutes"] * MICROS_PER_MINUTE)))
    try:
        lines = Path(transcript).read_text().splitlines()
    except (OSError, UnicodeDecodeError):
        raise ue.Refused("transcript_unreadable")
    if not lines:
        raise ue.Refused("transcript_empty")
    records = []
    for number, line in enumerate(lines, start=1):
        try:
            record = json.loads(line)
        except ValueError:
            record = None
        kind = classify(record)
        if kind is None:
            raise ue.Refused("unclassifiable record line %d" % number)
        records.append((kind, micros(record["timestamp"])))

    times = [t for _, t in records]
    agent = [t for kind, t in records if kind == "assistant"]
    human = [t for kind, t in records if kind == "human"]
    inside = [t for t in human if any(s <= t <= e for s, e in spans)]
    outside = [t for t in human if not any(s <= t <= e for s, e in spans)]
    attention = []
    for t in outside:
        earlier = [x for x in times if x < t]
        if earlier:
            attention.extend(subtract((max(earlier), t), spans))
    return ("human turns: %d; inside spans: %d; outside spans: %d; outside minutes: %s; "
            "session wall minutes: %s; agent active minutes: %s; graded %d of %d records"
            % (len(human), len(inside), len(outside), minutes(union_length(attention)),
               minutes(max(times) - min(times)),
               minutes(max(agent) - min(agent) if agent else 0),
               len(records), len(lines)))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Count human turns against logged human spans.")
    ap.add_argument("--transcript", required=True)
    ap.add_argument("--log", required=True)
    ap.add_argument("--stage", required=True)
    args = ap.parse_args(argv)
    try:
        line = count(args.transcript, args.log, args.stage)
    except ue.Refused as why:
        sys.stderr.write("refused: %s\n" % why)
        return EXIT_REFUSED
    print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
