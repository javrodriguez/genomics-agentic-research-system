#!/usr/bin/env python3
"""The take order's public randomness: one drand round, registered in the draft, read at the freeze.

    python3 evals/gap-study-4/order_beacon.py --round-at <ISO time>    the first quicknet round published at or after it
    python3 evals/gap-study-4/order_beacon.py --read <round>           read that round from both relays (network)

Pre-freeze review 1, MAJOR 9 (the lane orchestrator's fold plan of Sat 24 Oct 2026, lane L1). The take order was seeded
by the pre-freeze review commit's sha alone. An operator holding the clone could commit the review, preview the order
with prereg.py --order, reset and recommit, and choose among as many orders as it cared to commit; nothing outside the
clone saw the first commit. The order decides which half-cells go unmeasured if the money gate stops the loop.

THE ANCHOR. The draft registers one round of drand's quicknet chain (the League of Entropy's public beacon, a new
value every 3 s, CHAIN below), set once in REGISTERED_ROUND. Its value cannot be known before that round's time by
anyone, the operator included. The freeze reads the round from two independently operated relays (RELAYS), requires
them to agree byte for byte, requires the published randomness to be the sha256 of the published signature (how drand
derives it), and seeds the order with seed() over that round and its randomness alone (SEED_RULE). The frozen file
records the reading (take_order_beacon_reading).

NOTHING THE OPERATOR COMMITS IS IN THE SEED (the lane orchestrator's ruling 1 on lane L1's hand-back, Sat 24 Oct 2026).
A review commit or the draft's bytes in the seed could be ground: re-made many times under a forged date once the
round is public. So the seed reads the round and its randomness only, and the one thing left to choose, which round,
is fixed before its value exists by an outside witness: the freeze refuses unless the commit that set REGISTERED_ROUND
to the round is contained in a push GitHub itself recorded on WITNESS_REPO (its push activity, read read-only with
gh api) at least WITNESS_LEAD_S before the round is published (push_witness_problem). A local committer date is the
operator's to set; GitHub's push time is not.

WHAT THIS DOES NOT BIND, NAMED (residual(), carried into the draft beside the rule): whoever controls GitHub, or the
clock its push records are stamped by, could register a round after its value is public; and the round's BLS signature
is not verified here (no stdlib road): two relays run by different operators must agree instead.

The network is read only by read_relays and push_records: at the real freeze (on the Mac), by --read, and by prereg.py
--order-from-beacon once the round is published. No take, check or test reads it; tests hand in an opener and records.

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
# The outside witness of when the round was registered (ruling 1, and its second hand-back of 24 Oct 2026): GitHub's
# push activity on the private GARS mirror, which holds the study's own history (the aegis remote is another
# repository and can never hold a study commit). Pushes there run under Javier's standing word "mirror every verified
# gap study wave" (typed 12 Oct 2026 in glitch-2f's window, plans/gap-study-round-4/next-slices-2026-10-11.md), with
# _local/bin/gars-mirror.sh once athena passes the wave. WITNESS_LEAD_S is how long before the round's publication the
# registering commit must have been pushed there.
WITNESS_REPO = "javrodriguez/gars-cloud-mirror"
WITNESS_LEAD_S = 3600
STANDING_WORD = ("Javier's standing word \"mirror every verified gap study wave\" (12 Oct 2026, "
                 "plans/gap-study-round-4/next-slices-2026-10-11.md)")
# The registering steps, in their run order (written into the draft as take_order_beacon.registration_order).
REGISTRATION_ORDER = (
    "1. Commit the round: set REGISTERED_ROUND in order_beacon.py to a quicknet round (order_beacon.py --round-at) and "
    "re-derive the draft, in one commit on the freeze line.",
    "2. athena PASS: the whole gars-gap4 battery passes at that commit.",
    "3. Mirror: push that verified wave to " + WITNESS_REPO + " with _local/bin/gars-mirror.sh, under " + STANDING_WORD
    + "; GitHub stamps the push.",
    "4. Wait: the round must publish at least an hour (" + str(WITNESS_LEAD_S) + " s) after GitHub's push stamp; the "
    "freeze refuses otherwise, and reads the round only once it is published.",
)
# Retention (checked Sat 24 Oct 2026 by lane L1's builder): GitHub's REST docs for GET /repos/{owner}/{repo}/activity
# (https://docs.github.com/en/rest/repos/repos#list-repository-activities) and for the activity view
# (https://docs.github.com/en/repositories/viewing-activity-and-data-for-your-repository/using-the-activity-view-to-see-changes-to-a-repository)
# state no retention period. Read live the same day, both repositories returned every push back to their creation
# (gars-cloud-mirror: 536 records from 2026-09-30, created 2026-09-30; aegis: from 2026-09-12, its creation day), but an
# undocumented limit is no guarantee, so a record GitHub no longer returns refuses by name (push_witness_problem).
RETENTION_NOTE = ("GitHub's activity API documents no retention period "
                  "(docs.github.com/en/rest/repos/repos#list-repository-activities)")
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
                seed_rule=SEED_RULE, registration_order=list(REGISTRATION_ORDER), residual=residual())


SEED_PREFIX = "gap-study-4 take order\n"
SEED_RULE = ("take_order_seed is the first 40 hex characters of the sha256 of the UTF-8 text 'gap-study-4 take "
             "order\\n<the round>\\n<the round's randomness>': nothing the operator commits enters it. The round is the "
             "one registered here, read from both relays, which must agree, with its randomness the sha256 of its "
             "signature (order_beacon.seed); the freeze refuses unless the commit that registered the round was pushed "
             "to " + WITNESS_REPO + " at least " + str(WITNESS_LEAD_S) + " s before the round is published, by GitHub's "
             "own push record (order_beacon.push_witness_problem); that push is the mirror of a verified wave, under "
             + STANDING_WORD + ".")


def residual() -> str:
    return ("The take order is fixed by the registered drand round alone, and the round is fixed before its value "
            "exists by GitHub's own record of the push that registered it, at least an hour before the round is "
            "published. Whoever controls GitHub, or the clock its push records are stamped by, could register a round "
            "after its value is public and so choose the order. The round's BLS signature is not verified; two relays "
            "run by different operators must agree instead. The witnessing push is the mirror of a verified wave, made "
            "under " + STANDING_WORD + "; " + RETENTION_NOTE + ", so a push record GitHub no longer returns refuses "
            "the freeze, never passes it.")


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


def seed(reading: dict) -> str:
    """SEED_RULE: 40 lowercase hex characters over the round and its randomness alone, so prereg.py --order <seed>
    previews the frozen order."""
    text = f"{SEED_PREFIX}{reading['round']}\n{reading['randomness']}"
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:40]


def push_witness_problem(commit, round_no: int, pushes, contains) -> str | None:
    """Why GitHub's push records do not witness the round's registration in time (ruling 1), or None.

    `commit` is the commit that set REGISTERED_ROUND to `round_no` (None when no commit did); `pushes` is
    [(unix time, pushed sha)] as GitHub recorded them on WITNESS_REPO; `contains(commit, sha)` says whether `sha`'s
    history holds `commit`. A push counts only if it holds the commit and GitHub stamped it at least WITNESS_LEAD_S
    before the round's publication time."""
    if not (isinstance(commit, str) and SEED_SHAPE.fullmatch(commit)):
        return (f"no commit in this history sets REGISTERED_ROUND to {round_no}: the round's registration has no "
                f"commit to witness")
    deadline = round_time(round_no) - WITNESS_LEAD_S
    held = sorted(t for t, sha in pushes if contains(commit, sha))
    if not held:
        return (f"GitHub returns no push to {WITNESS_REPO} holding {commit[:12]}, the commit that registered round "
                f"{round_no}: either it was never mirrored or GitHub no longer returns the record ({RETENTION_NOTE}); "
                f"a missing record never passes")
    if held[0] > deadline:
        return (f"GitHub's first push to {WITNESS_REPO} holding {commit[:12]} is stamped {iso(held[0])}, later than "
                f"{iso(deadline)} ({WITNESS_LEAD_S} s before round {round_no} is published): the round could have been "
                f"registered with its value in sight")
    return None


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
