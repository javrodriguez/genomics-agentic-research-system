#!/usr/bin/env python3
"""The take order's public randomness: one drand round, registered in the draft, read at the freeze.

    python3 evals/gap-study-4/order_beacon.py --round-at <ISO time>    the first quicknet round published at or after it
    python3 evals/gap-study-4/order_beacon.py --read <round>           read that round from both relays (network)

Pre-freeze review 1, MAJOR 9 (the lane orchestrator's fold plan of Sat 24 Oct 2026, lane L1). The take order was seeded
by the pre-freeze review commit's sha alone. An operator holding the clone could commit the review, preview the order
with prereg.py --order, reset and recommit, and choose among as many orders as it cared to commit; nothing outside the
clone saw the first commit. The order decides which half-cells go unmeasured if the money gate stops the loop.

THE ANCHOR. The draft registers one round of drand's quicknet chain (the League of Entropy's public beacon, a new
value every 3 s, CHAIN below) whose time falls after the review can be committed. Its value cannot be known before
that time by anyone, the operator included. The freeze reads the round from two independently operated relays
(RELAYS), requires them to agree byte for byte, requires the published randomness to be the sha256 of the published
signature (how drand derives it), and seeds the order with seed() over the review commit and that randomness. The
frozen file records the reading (take_order_beacon_reading). A reset and recommit before the round is published
changes nothing the operator can choose, because the value that decides the order does not exist yet.

WHAT THIS DOES NOT BIND, NAMED (residual(), carried into the draft beside the rule):
  - the round's BLS signature is not verified here (no stdlib road); two relays run by different operators must agree,
    which is a weaker guarantee than the signature check a drand client makes;
  - a review commit made AFTER the round is published could still be re-made to choose among orders. The freeze refuses
    a review whose committer time is not before the round's time, and records both, but a committer time is set by
    whoever commits, so a forged date is a lie a reader can catch only by comparing the review commit with the record
    outside the clone (the lane orchestrator's log of when the review ran).

The network is read only by read_relays: at the real freeze (on the Mac), by --read, and by prereg.py
--order-for-review once the round is published. No take, check or test reads it; tests hand in an opener.

No model; stdlib only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone

# drand quicknet, read from https://api.drand.sh/<hash>/info on Sat 24 Oct 2026 16:24 EDT (lane L1's builder):
# {"period":3,"genesis_time":1692803367,"hash":"52db9b...e971","schemeID":"bls-unchained-g1-rfc9380",
#  "metadata":{"beaconID":"quicknet"}}; round r is published at genesis_time + (r - 1) * period.
CHAIN = {
    "network": "drand",
    "beacon_id": "quicknet",
    "chain_hash": "52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971",
    "genesis_time": 1692803367,
    "period_s": 3,
    "scheme": "bls-unchained-g1-rfc9380",
}
# Two relays run by different operators (the League of Entropy's own, and Cloudflare's); both answered round 33356692
# with the same signature and randomness on Sat 24 Oct 2026 16:25 EDT (lane L1's builder, by curl).
RELAYS = ("https://api.drand.sh", "https://drand.cloudflare.com")
# The round the next draft registers: None until the draft is regenerated for its review, when the orchestrator sets the
# first round published at or after the latest time the review can be committed (--round-at <that time>), in the same
# commit as the regenerated draft. While None, the draft's round reads PENDING and the freeze is closed.
REGISTERED_ROUND: int | None = None
READING_KEYS = ("chain_hash", "round", "round_time", "randomness", "signature", "relays")
HEX = re.compile(r"[0-9a-f]+")
SEED_SHAPE = re.compile(r"[0-9a-f]{40}")
TIMEOUT_S = 20


class BeaconRefused(ValueError):
    """The beacon cannot seed this freeze; the message says why."""


def registration() -> dict:
    """What build_draft writes as the draft's take_order_beacon: the chain, the relays, the rule; the round is the one
    value chosen when a draft is regenerated for its review (PENDING until then, so build_draft.pending names it)."""
    if REGISTERED_ROUND is not None:
        round_time(REGISTERED_ROUND)
    return dict(CHAIN, relays=list(RELAYS), round="PENDING" if REGISTERED_ROUND is None else REGISTERED_ROUND,
                seed_rule=SEED_RULE, residual=residual())


SEED_RULE = ("take_order_seed is the first 40 hex characters of the sha256 of the UTF-8 text '<the pre-freeze review "
             "commit's full sha>\\n<the round>\\n<the round's randomness>', the round read from both relays, which must "
             "agree, with its randomness the sha256 of its signature (order_beacon.seed).")


def residual() -> str:
    return ("The take order is fixed once both the pre-freeze review commit and the registered drand round exist. A "
            "review committed before the round is published cannot be re-made to choose an order, because the round's "
            "value does not exist yet. The freeze refuses a review whose committer time is not before the round's time "
            "and records both, but a committer time is set by whoever commits: a review re-committed after the round "
            "under a forged earlier date would choose among orders, and only the orchestrator's record of when the "
            "review ran, kept outside the clone, can show it. The round's BLS signature is not verified; two relays run "
            "by different operators must agree instead.")


def round_time(round_no: int) -> int:
    """The unix time at which the chain publishes `round_no` (round 1 at genesis)."""
    if type(round_no) is not int or round_no < 1:
        raise BeaconRefused(f"a drand round is a positive integer, not {round_no!r}")
    return CHAIN["genesis_time"] + (round_no - 1) * CHAIN["period_s"]


def round_at(when: datetime) -> int:
    """The first round published at or after `when` (an aware datetime)."""
    t = when.timestamp()
    elapsed = t - CHAIN["genesis_time"]
    if elapsed <= 0:
        return 1
    n = int(-(-elapsed // CHAIN["period_s"]))      # ceiling
    return n + 1


def registered_round(beacon) -> int:
    """The draft's registered round, or BeaconRefused: no beacon, another chain or relays, or a round still PENDING."""
    if not isinstance(beacon, dict):
        raise BeaconRefused("the design registers no take_order_beacon: the order would rest on the review commit alone")
    for key, want in CHAIN.items():
        if beacon.get(key) != want:
            raise BeaconRefused(f"take_order_beacon.{key} is {beacon.get(key)!r}, not the registered chain's {want!r}")
    if beacon.get("relays") != list(RELAYS):
        raise BeaconRefused(f"take_order_beacon.relays is {beacon.get('relays')!r}, not {list(RELAYS)!r}")
    if beacon.get("seed_rule") != SEED_RULE:
        raise BeaconRefused("take_order_beacon.seed_rule is not order_beacon.SEED_RULE")
    r = beacon.get("round")
    if type(r) is not int:
        raise BeaconRefused(f"take_order_beacon.round is {r!r}: a round is registered when the draft is regenerated "
                            f"for its review, and no order exists without one")
    round_time(r)
    return r


def reading_problems(reading, round_no: int) -> list[str]:
    """Why a reading is not a well-formed reading of `round_no` on CHAIN (an offline check: shape, round, time, and the
    randomness as the sha256 of the signature), or []."""
    if not isinstance(reading, dict) or set(reading) != set(READING_KEYS):
        return [f"a beacon reading holds exactly {list(READING_KEYS)}"]
    out = []
    if reading["chain_hash"] != CHAIN["chain_hash"]:
        out.append(f"the reading is of chain {reading['chain_hash']!r}, not {CHAIN['chain_hash']}")
    if reading["round"] != round_no:
        out.append(f"the reading is of round {reading['round']!r}, not the registered {round_no}")
    elif reading["round_time"] != round_time(round_no):
        out.append(f"the reading's round_time {reading['round_time']!r} is not round {round_no}'s")
    sig, rnd = reading["signature"], reading["randomness"]
    if not (isinstance(sig, str) and HEX.fullmatch(sig) and len(sig) % 2 == 0):
        out.append("the reading's signature is not lowercase hex")
    elif not (isinstance(rnd, str) and rnd == hashlib.sha256(bytes.fromhex(sig)).hexdigest()):
        out.append("the reading's randomness is not the sha256 of its signature")
    if not (isinstance(reading["relays"], list) and reading["relays"] and set(reading["relays"]) <= set(RELAYS)):
        out.append(f"the reading names relays {reading['relays']!r}, not of {list(RELAYS)}")
    return out


def _open(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=TIMEOUT_S) as got:     # noqa: S310 (a fixed https relay)
        return got.read()


def read_relays(round_no: int, *, opener=None, now=None) -> dict:
    """The round as both relays publish it, or BeaconRefused: not yet due, a relay unreadable or off shape, or the two
    disagreeing. `opener(url) -> bytes` stands in for the network in tests."""
    opener = _open if opener is None else opener
    due = round_time(round_no)
    now = datetime.now(timezone.utc).timestamp() if now is None else now
    if now < due:
        raise BeaconRefused(f"drand round {round_no} is published at {iso(due)}; it is {iso(now)}, so no value exists "
                            f"yet and no order can be read")
    answers = []
    for relay in RELAYS:
        url = f"{relay}/{CHAIN['chain_hash']}/public/{round_no}"
        try:
            doc = json.loads(opener(url))
        except Exception as e:      # noqa: BLE001 (any failure to read a relay refuses, by name)
            raise BeaconRefused(f"{url} cannot be read ({type(e).__name__}: {str(e)[:120]})") from None
        if not isinstance(doc, dict) or doc.get("round") != round_no:
            raise BeaconRefused(f"{url} did not answer round {round_no}")
        answers.append((doc.get("randomness"), doc.get("signature")))
    if len(set(answers)) != 1:
        raise BeaconRefused(f"the relays disagree on round {round_no}: {answers!r}")
    randomness, signature = answers[0]
    reading = {"chain_hash": CHAIN["chain_hash"], "round": round_no, "round_time": due, "randomness": randomness,
               "signature": signature, "relays": list(RELAYS)}
    bad = reading_problems(reading, round_no)
    if bad:
        raise BeaconRefused("; ".join(bad))
    return reading


def seed(review_commit: str, reading: dict) -> str:
    """SEED_RULE: 40 lowercase hex characters, so prereg.py --order <seed> previews the frozen order."""
    if not (isinstance(review_commit, str) and SEED_SHAPE.fullmatch(review_commit)):
        raise BeaconRefused(f"the review commit is the full 40-character lowercase sha, not {review_commit!r}")
    text = f"{review_commit}\n{reading['round']}\n{reading['randomness']}"
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:40]


def iso(t: float) -> str:
    return datetime.fromtimestamp(t, timezone.utc).replace(microsecond=0).isoformat()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0], allow_abbrev=False)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--round-at", metavar="ISO")
    g.add_argument("--read", type=int, metavar="ROUND")
    a = ap.parse_args(argv)
    try:
        if a.round_at:
            when = datetime.fromisoformat(a.round_at)
            if when.tzinfo is None:
                raise BeaconRefused("give the time with its offset, e.g. 2026-10-26T09:00:00-04:00")
            r = round_at(when)
            print(f"order_beacon: quicknet round {r} is published at {iso(round_time(r))}")
            return 0
        print(json.dumps(read_relays(a.read), indent=2))
        return 0
    except (BeaconRefused, ValueError) as e:
        print(f"order_beacon: REFUSED {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
