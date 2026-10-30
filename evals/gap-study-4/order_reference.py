#!/usr/bin/env python3
"""The take order recomputed from the frozen file alone, in an isolated interpreter, with its own verdict.

    python3 -I -S evals/gap-study-4/order_reference.py evals/gap-study-4/prereg.json evals/gap-study-4/prereg-draft.json
    python3 -I -S evals/gap-study-4/order_reference.py - <draft>  (the frozen file on stdin)

Lane fold2-lb, glitch-45's items after the lane review of fold2/lb (m-1) and glitch-45's own review (mn-1, mn-2).
freeze.take_order_function_sha256 cannot see a module-level patch, inside a study file, of the standard library or of
a function object, nor prepare's hand-off of the seed. So at publication this file recomputes, from the frozen file's
take_order_beacon (the registered round and chain), take_order_beacon_reading, rows, take_order_seed and take_order:

  - the frozen file's take_order_beacon is drand quicknet (CHAIN_HASH, GENESIS_TIME and PERIOD_S, pinned here) and its
    round is the committed draft's registered round (the second argument; glitch-45's re-check, R-2: a frozen file
    self-consistent on another chain, genesis or round passed);
  - the reading is of that round, on that chain, at that round's time (GENESIS_TIME + (round - 1) * PERIOD_S), and its
    randomness is the sha256 of its signature (mn-1: a reading of another round, with a matching randomness, gave
    another seed and order and passed);
  - take_order_seed is SEED_RULE over that reading (order_beacon.seed restated);
  - take_order is freeze.planned_order's permutation of the rows under that seed (restated).

WHAT IS ISOLATED (mn-2). Run as above, `-I` ignores the environment, the user site and the script's folder for
imports, `-S` skips site, and this file imports only hashlib, json and sys: no study module, and so no patch inside
one, runs in this process, and the verdict (the problems printed, the exit code) is computed here. check_results.py
runs this file the same way and reads its exit code and lines; that reading happens in check_results' own process,
which has imported study modules, so the standalone run above is the isolated form a reviewer or a gate runs. The
restated rules are bound by review with the code they restate (SEED_RULE, order_beacon.seed, freeze.planned_order).

Exit 0 and one `order_reference: ok` line when everything matches; exit 1 with one `order_reference: problem: ...`
line per problem otherwise; exit 2 when the file cannot be read.
"""

import hashlib
import json
import sys

SEED_PREFIX = "gap-study-4 take order\n"
# drand quicknet, as order_beacon.CHAIN registers it (a test binds the two)
CHAIN_HASH = "52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971"
GENESIS_TIME = 1692803367
PERIOD_S = 3


def problems(frozen, draft):
    rows, reading = frozen.get("rows"), frozen.get("take_order_beacon_reading")
    beacon, order = frozen.get("take_order_beacon"), frozen.get("take_order")
    if not (isinstance(rows, list) and rows and isinstance(reading, dict) and isinstance(beacon, dict)
            and isinstance(order, list)):
        return ["the frozen file carries no rows, take_order_beacon, beacon reading or take_order to recompute"]
    out = []
    r = beacon.get("round")
    registered = (draft.get("take_order_beacon") or {}).get("round") if isinstance(draft, dict) else None
    if type(r) is not int or r != registered:
        out.append(f"the frozen take_order_beacon's round {r!r} is not the committed draft's registered round "
                   f"{registered!r}")
    if (beacon.get("chain_hash"), beacon.get("genesis_time"), beacon.get("period_s")) != \
            (CHAIN_HASH, GENESIS_TIME, PERIOD_S):
        out.append("the frozen take_order_beacon is not drand quicknet (chain hash, genesis time or period)")
    if type(r) is not int or reading.get("round") != r:
        out.append(f"the beacon reading is of round {reading.get('round')!r}, not the registered round {r!r}")
    if reading.get("chain_hash") != CHAIN_HASH:
        out.append("the beacon reading is not of drand quicknet")
    due = GENESIS_TIME + (r - 1) * PERIOD_S if type(r) is int else None
    if due is None or reading.get("round_time") != due:
        out.append(f"the beacon reading's round_time {reading.get('round_time')!r} is not the registered round's "
                   f"{due!r}")
    sig, rnd = reading.get("signature"), reading.get("randomness")
    try:
        sig_ok = isinstance(sig, str) and rnd == hashlib.sha256(bytes.fromhex(sig)).hexdigest()
    except ValueError:
        sig_ok = False
    if not sig_ok:
        out.append("the beacon reading's randomness is not the sha256 of its signature")
    seed = hashlib.sha256(f"{SEED_PREFIX}{reading.get('round')}\n{rnd}".encode("utf-8")).hexdigest()[:40]
    if frozen.get("take_order_seed") != seed:
        out.append("take_order_seed is not SEED_RULE over the frozen beacon reading")

    def key(row):
        data = (json.dumps(row, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
        return hashlib.sha256(seed.encode() + data).hexdigest()

    if order != sorted(rows, key=key):
        out.append("take_order is not the permutation the seed gives the frozen rows: the order function that ran was "
                   "not the registered one")
    return out


def main(argv):
    if len(argv) != 3:
        print("usage: order_reference.py <prereg.json | -> <prereg-draft.json>")
        return 2
    try:
        text = sys.stdin.read() if argv[1] == "-" else open(argv[1], encoding="utf-8").read()
        frozen = json.loads(text)
        draft = json.loads(open(argv[2], encoding="utf-8").read())
    except (OSError, ValueError) as e:
        print(f"order_reference: cannot read the frozen file or the draft ({type(e).__name__})")
        return 2
    if not isinstance(frozen, dict):
        print("order_reference: the frozen file is not one object")
        return 2
    found = problems(frozen, draft)
    for p in found:
        print(f"order_reference: problem: {p}")
    if not found:
        print(f"order_reference: ok, {len(frozen['take_order'])} rows in the order the registered round's seed gives")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
