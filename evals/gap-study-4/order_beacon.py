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
round is public. So the seed reads the round and its randomness only. What the freeze enforces (the review of
53d0e9af, finding 1): REGISTERED_ROUND, read by parsing each version of this file (registered_value), changed exactly
once in HEAD's history, from None to the round (history_problem); and both the commit that made that change and the
last commit that changed prereg-draft.json, whose rows the order permutes, are held by pushes GitHub itself recorded on
WITNESS_REPO (its push activity, read read-only with gh api --hostname github.com) at least WITNESS_LEAD_S before the
round is published (push_witness_problem). A local committer date is the operator's to set; GitHub's push time is not.
And every commit the mirror's records hold must be in the freezing clone, with no other registered round and no
other draft after the registration off HEAD's one line (freeze.mirror_problem; the closure check of 84ab6393), so
candidates on parallel pushed branches are refused.

WHAT THIS DOES NOT BIND, NAMED (residual(), carried into the draft beside the rule): a mirror whose history someone
rewrites, or GitHub itself (or the clock its records are stamped by); a record GitHub stops returning refuses the
freeze only when it is one of the two witnessing pushes: a dropped record of a candidate branch goes unseen, so GitHub
dropping a deleted branch's records is a remaining road (a mirror rule blocking deletion and force push would close
it; that is a repository setting, Javier's call); and the round's BLS signature is not verified here (no stdlib road):
two relays run by different operators must agree instead.

The network is read only by read_relays and push_records: at the real freeze (on the Mac), by --read, and by prereg.py
--order-from-beacon once the round is published. No take, check or test reads it; tests hand in an opener and records.

SUPERSEDED ROUNDS (pre-freeze review 2, section 1's option A+; lane fold2-lb, built before Javier's recorded answer and
merged only on it). A registered round may be replaced, and only as SUPERSEDED_ROUNDS records it: an append-only tuple
of entries, carried into the draft as take_order_beacon.superseded. history_problem accepts exactly [None, *the
superseded rounds in order, the round]. Each entry is bound by the freeze (freeze.take_order_witness) to its swap
commit, the first commit in HEAD's history in which REGISTERED_ROUND leaves that round, which must add the entry; and
it passes only one of two ways:
  before_publication: GitHub's push records hold the swap commit at least SWAP_LEAD_S before the superseded round
    publishes, so no one could know the value it replaced (no selection is possible), and no owner word is needed;
  decision + ask: the study's committed copy of its decision log (OWNER_DECISIONS, rows copied byte for byte from
    OrgOS's decision.jsonl) holds exactly one row with that id, Javier's (principal) answer to that ask, dated after
    the round published, whose reply is the round's swap phrase (swap_phrase_problem), cited by no other entry. That
    log is our own record: an outside reader takes it on the same trust as the machines and the runner.
A superseded round's order can be computed by anyone, against the draft its entry names.

No model; stdlib only.
"""
from __future__ import annotations

import argparse
import ast
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
REGISTERED_ROUND: int | None = 33536472
# The rounds registered and then replaced, oldest first (option A+, lane fold2-lb). Append-only across history; each
# entry is a dict literal with ENTRY_COMMON and either before_publication or decision and ask (superseded_problems).
# The swap commit that moves REGISTERED_ROUND off a round adds its entry in the same commit, with the draft re-derived.
# The swap commit (lane fold2/lc, Javier's OD160 on T199, option A+): round 33496978 superseded, r2 registered.
SUPERSEDED_ROUNDS: tuple = ({
        "round": 33496978, "published": "2026-10-29T17:18:18Z",
        "registering_commit": "6190a00cf322432bc4ec8b12e03adb3fbbd315b2",
        "push": "gars-cloud-mirror freeze/r4-20261021, branch_creation 2026-10-29T14:12:25Z, under OD147",
        "why": "0f634fc3 (pre-freeze review 2): DO NOT FREEZE; MAJORs 1-2 change the draft after the round's push "
               "deadline (2026-10-29T16:18:18Z)",
        "record": "6190a00c, the last commit to change the draft and the one that set the round, was pushed under "
                  "Javier's recorded word OD147 before its athena battery, which then failed one test-only check (fixed "
                  "in 1533750a and ef31e4a9, neither of which changed the draft or order_beacon.py); ef31e4a9 passed the "
                  "whole battery. The round's order can be computed by anyone with prereg.py --order <seed of round "
                  "33496978> against prereg-draft.json at 6190a00c (byte-identical at ef31e4a9); no record shows anyone "
                  "in the study computed it.",
        "decision": "OD160", "ask": "T199"},)
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
# Pre-freeze review 2, m1 (lane fold2-lb): the push rule as it is kept. 6190a00c, which registered round 33496978, was
# pushed under Javier's recorded word OD147 ("mirror-early yes") before its athena battery, which then failed one
# test-only check; "that push is the mirror of a verified wave" was untrue for it, so the rule names both roads.
PUSH_RULE = ("the push is a mirror of a wave that passed the whole athena battery, under " + STANDING_WORD + ", or a "
             "push Javier named by a recorded word (its id cited)")
# Option A+: the lead a before_publication swap commit needs before the superseded round publishes, against clock skew
# between GitHub's stamp and drand's schedule.
SWAP_LEAD_S = 60
# The committed copy of the decision rows a superseded entry cites (study-relative; rows byte-identical to OrgOS's
# decision.jsonl lines). Absent until a decision entry exists; then an entry citing an id it does not hold is refused.
OWNER_DECISIONS = "owner_decisions.jsonl"
# The swap phrase of a superseded round: `beacon-swap-<round> yes` (outcome yes), except the first, round 33496978,
# which Javier's answer to ask beacon-r4 (T199) decides; its reply is `beacon-r4 <key>` with outcome <key>, and only the
# options that drop the round count (aplus, a, b; c keeps it, so it is no word for a swap).
FIRST_SWAP = {33496978: ("beacon-r4", ("aplus", "a", "b"))}
ENTRY_COMMON = ("round", "published", "registering_commit", "push", "why", "record")
ENTRY_BEFORE = ENTRY_COMMON + ("before_publication",)
ENTRY_DECISION = ENTRY_COMMON + ("decision", "ask")
# The registering steps, in their run order (written into the draft as take_order_beacon.registration_order).
REGISTRATION_ORDER = (
    "1. Fetch every mirror ref into the freezing clone, read-only, before the freeze: freeze.mirror_problem refuses "
    "while any commit GitHub records on " + WITNESS_REPO + " is missing from it, so a force push whose old commits the "
    "mirror no longer serves blocks the freeze.",
    "2. Commit the round: set REGISTERED_ROUND in order_beacon.py to a quicknet round (order_beacon.py --round-at) and "
    "re-derive the draft, in one commit on the freeze line. Replacing a registered round, the same commit appends its "
    "entry to SUPERSEDED_ROUNDS: before_publication when the commit will be pushed at least " + str(SWAP_LEAD_S)
    + " s before that round publishes, else the decision and ask of Javier's recorded answer to the ask naming the swap.",
    "3. athena PASS: the whole gars-gap4 battery passes at that commit, unless Javier names the push by a recorded word.",
    "4. Mirror: push that wave to " + WITNESS_REPO + " with _local/bin/gars-mirror.sh, where " + PUSH_RULE
    + "; GitHub stamps the push.",
    "5. Wait: the round must publish at least an hour (" + str(WITNESS_LEAD_S) + " s) after GitHub's push stamp; the "
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
    value chosen when a draft is regenerated for its review (PENDING until then, so build_draft.pending names it); and
    (option A+) the superseded rounds' entries."""
    bad = superseded_problems(SUPERSEDED_ROUNDS)
    if bad:
        raise BeaconRefused("SUPERSEDED_ROUNDS: " + "; ".join(bad))
    if REGISTERED_ROUND is not None:
        round_time(REGISTERED_ROUND)
        if REGISTERED_ROUND in [e["round"] for e in SUPERSEDED_ROUNDS]:
            raise BeaconRefused(f"round {REGISTERED_ROUND} is superseded; a superseded round is never the registered one")
    return dict(CHAIN, relays=list(RELAYS), round="PENDING" if REGISTERED_ROUND is None else REGISTERED_ROUND,
                seed_rule=SEED_RULE, registration_order=list(REGISTRATION_ORDER), residual=residual(),
                superseded=[dict(e) for e in SUPERSEDED_ROUNDS])


SEED_PREFIX = "gap-study-4 take order\n"
SEED_RULE = ("take_order_seed is the first 40 hex characters of the sha256 of the UTF-8 text 'gap-study-4 take "
             "order\\n<the round>\\n<the round's randomness>': nothing the operator commits enters it. The round is the "
             "one registered here, read from both relays, which must agree, with its randomness the sha256 of its "
             "signature (order_beacon.seed); the freeze refuses unless the commit that registered the round was pushed "
             "to " + WITNESS_REPO + " at least " + str(WITNESS_LEAD_S) + " s before the round is published, by GitHub's "
             "own push record, and so must the last commit that changed the draft (order_beacon.push_witness_problem); "
             + PUSH_RULE + ". A registered round is replaced only as take_order_beacon.superseded records it: by a "
             "swap commit GitHub's records hold at least " + str(SWAP_LEAD_S) + " s before that round publishes, or "
             "under Javier's recorded answer to the ask naming that swap (order_beacon.SUPERSEDED_ROUNDS).")


def residual() -> str:
    return ("The take order is seeded by the registered drand round and its randomness alone. The freeze enforces that "
            "REGISTERED_ROUND, read by parsing order_beacon.py at every commit, changed in the history it freezes only "
            "from None to the round, through each superseded round take_order_beacon.superseded records, in that order "
            "(history_problem: [None, *superseded, round]), and that GitHub's own records hold a push of the commit "
            "that set the round and a push of the last commit that changed the draft, each at least an hour before the round is "
            "published, and that no commit the mirror's records hold registers another round, or changes the draft "
            "after the registration, off that one line. The remaining road is only a mirror whose history someone "
            "rewrites, or GitHub itself (or the clock its records are stamped by), and among GitHub's own roads its "
            "dropping a deleted branch's records: a record GitHub stops returning refuses the freeze only when it is "
            "one of the two witnessing pushes, and a dropped record of a candidate branch goes unseen (a mirror rule "
            "blocking deletion and force push would close it, a repository setting and Javier's call). The round's "
            "BLS signature is not verified (two relays run by different operators must agree instead). For the "
            "witnessing pushes, " + PUSH_RULE + "; " + RETENTION_NOTE + ", so a push record GitHub no longer "
            "returns for a witnessing push refuses the freeze, never passes it. A registered round may be "
            "superseded, and each such round is listed in take_order_beacon.superseded with why: the freeze passes "
            "a superseded round only when GitHub's records hold the commit that replaced it at least "
            + str(SWAP_LEAD_S) + " s before it published, so its value was unknown, or under Javier's recorded "
            "answer to the ask naming that swap, a row the freeze reads from the study's committed copy of its "
            "decision log (" + OWNER_DECISIONS + "), which an outside reader takes on the same trust as the "
            "machines and the runner. A superseded round's order can be computed by anyone, against the draft its "
            "entry names; it is a published deviation, never a silent one.")


def registered_value(source: str):
    """REGISTERED_ROUND as one version of this file assigns it, read by parsing the module (the review of 53d0e9af,
    finding 1a: a line of text in a docstring is no registration). The one module-level assignment's value must be the
    literal None or an int; anything else, or no or several assignments, is BeaconRefused."""
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        raise BeaconRefused(f"this version of order_beacon.py does not parse ({e.msg})") from None
    found = []
    for node in tree.body:
        targets = [node.target] if isinstance(node, ast.AnnAssign) else node.targets if isinstance(node, ast.Assign) \
            else []
        if any(isinstance(t, ast.Name) and t.id == "REGISTERED_ROUND" for t in targets):
            found.append(node.value)
    if len(found) != 1:
        raise BeaconRefused(f"this version of order_beacon.py assigns REGISTERED_ROUND {len(found)} times, not once")
    value = found[0]
    if isinstance(value, ast.Constant) and (value.value is None or type(value.value) is int):
        return value.value
    raise BeaconRefused("REGISTERED_ROUND is not assigned the literal None or an integer")


def history_problem(values: list, round_no: int, superseded=()):
    """Why a file's REGISTERED_ROUND values, commit by commit in history order, are not exactly [None, *the superseded
    rounds in order, `round_no`] (finding 1b: a round set twice, or set back, could be chosen after its value is
    public; option A+: a round is replaced only as an entry of `superseded` records it), or None."""
    rounds = [e["round"] for e in superseded]
    if round_no in rounds:
        return f"round {round_no} is superseded; a superseded round is never the registered one"
    changes = [v for i, v in enumerate(values) if i == 0 or v != values[i - 1]]
    if changes != [None, *rounds, round_no]:
        return (f"REGISTERED_ROUND's history is {changes}, not None, then the superseded rounds {rounds}, then "
                f"{round_no}: a round set more than once, set back, never None first, or replaced with no entry is "
                f"refused")
    return None


def superseded_value(source: str) -> tuple:
    """SUPERSEDED_ROUNDS as one version of this file assigns it, read by parsing (a version before option A+ assigns
    none: ()). One module-level assignment of a literal tuple of dicts, else BeaconRefused."""
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        raise BeaconRefused(f"this version of order_beacon.py does not parse ({e.msg})") from None
    bound = []
    for node in tree.body:
        targets = [node.target] if isinstance(node, ast.AnnAssign) else node.targets if isinstance(node, ast.Assign) \
            else []
        if any(isinstance(t, ast.Name) and t.id == "SUPERSEDED_ROUNDS" for t in targets):
            bound.append(node.value)
    # the fold's review (NIT): a second binding anywhere (inside an if, a def, a loop) could hide an entry at run time
    stores = sum(1 for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id == "SUPERSEDED_ROUNDS"
                 and isinstance(n.ctx, (ast.Store, ast.Del)))
    if stores != len(bound):
        raise BeaconRefused("SUPERSEDED_ROUNDS is bound somewhere other than one module-level assignment")
    if not bound:
        return ()
    if len(bound) != 1:
        raise BeaconRefused(f"this version of order_beacon.py assigns SUPERSEDED_ROUNDS {len(bound)} times, not once")
    try:
        value = ast.literal_eval(bound[0])
    except ValueError:
        raise BeaconRefused("SUPERSEDED_ROUNDS is not a literal") from None
    if not (isinstance(value, tuple) and all(isinstance(e, dict) for e in value)):
        raise BeaconRefused("SUPERSEDED_ROUNDS is not a literal tuple of dicts")
    return value


def published_text(round_no: int) -> str:
    """The round's publication time as an entry's `published` field writes it: UTC, seconds, a trailing Z."""
    return datetime.fromtimestamp(round_time(round_no), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def superseded_problems(entries) -> list[str]:
    """Why `entries` are not well-formed SUPERSEDED_ROUNDS entries (an offline shape check), or []."""
    if not isinstance(entries, (tuple, list)):
        return ["SUPERSEDED_ROUNDS is not a tuple"]
    out, rounds, ids = [], [], []
    for i, e in enumerate(entries):
        if not isinstance(e, dict) or set(e) not in (set(ENTRY_BEFORE), set(ENTRY_DECISION)):
            out.append(f"entry {i} holds neither exactly {list(ENTRY_BEFORE)} nor exactly {list(ENTRY_DECISION)}")
            continue
        r = e["round"]
        try:
            want = published_text(r)
        except BeaconRefused as err:
            out.append(f"entry {i}: {err}")
            continue
        rounds.append(r)
        if e["published"] != want:
            out.append(f"entry {i}: published is {e['published']!r}, not round {r}'s time {want}")
        if not (isinstance(e["registering_commit"], str) and SEED_SHAPE.fullmatch(e["registering_commit"])):
            out.append(f"entry {i}: registering_commit is not a full 40-hex commit")
        for key in ("push", "why", "record"):
            if not (isinstance(e[key], str) and e[key].strip()):
                out.append(f"entry {i}: {key} is not a non-empty sentence")
        if "before_publication" in e and e["before_publication"] is not True:
            out.append(f"entry {i}: before_publication is not true")
        if "decision" in e:
            for key in ("decision", "ask"):
                if not (isinstance(e[key], str) and e[key].strip()):
                    out.append(f"entry {i}: {key} is not a non-empty id")
            ids.append(e["decision"])
    if len(set(rounds)) != len(rounds):
        out.append("a round is superseded twice")
    if len(set(ids)) != len(ids):
        out.append("one decision id is cited by two entries")
    return out


def swap_phrase_problem(round_no: int, row: dict):
    """Why a decision row's reply is not the swap phrase of `round_no`, or None (FIRST_SWAP for round 33496978;
    `beacon-swap-<round> yes` with outcome yes for every other round)."""
    match, outcome = row.get("principal_match"), row.get("outcome")
    if round_no in FIRST_SWAP:
        code, keys = FIRST_SWAP[round_no]
        if outcome in keys and match == f"{code} {outcome}":
            return None
        return (f"its reply is {match!r} with outcome {outcome!r}, not one of "
                f"{[f'{code} {k}' for k in keys]} with that key as its outcome")
    if match == f"beacon-swap-{round_no} yes" and outcome == "yes":
        return None
    return f"its reply is {match!r} with outcome {outcome!r}, not 'beacon-swap-{round_no} yes' with outcome 'yes'"


def _utc(text) -> float | None:
    try:
        return datetime.fromisoformat(str(text).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def decision_problem(entry: dict, rows: list, entries, now: float | None = None) -> str | None:
    """Option A+, step 3b: why `entry`'s decision does not bind its swap, or None. The decision list `rows` must hold
    exactly one row with the entry's id, an `ask.answer` by the principal with its turn's sha256, answering the entry's
    ask with the round's swap phrase, created after the round published; no other entry of `entries` cites the id.
    glitch-45's review of fold2/lb, mn-3 (ruled): no row of the list supersedes it (`supersedes_id`), no later row
    answers or withdraws the same ask, and its `expires_at`, when set, is still ahead of `now` (the check's own clock
    by default). The list is the study's committed copy; a later row OrgOS holds and the copy lacks is not seen (the
    copy's trust limit, named in residual())."""
    did, r = entry["decision"], entry["round"]
    if sum(1 for e in entries if isinstance(e, dict) and e.get("decision") == did) != 1:
        return f"decision {did} is cited by more than one superseded entry"
    match = [row for row in rows if isinstance(row, dict) and row.get("id") == did]
    if len(match) != 1:
        return f"the committed decision list ({OWNER_DECISIONS}) holds {len(match)} row(s) with id {did}, not one"
    row = match[0]
    if row.get("action") != "ask.answer" or row.get("actor_role") != "principal":
        return f"{did} is a {row.get('action')!r} by {row.get('actor_role')!r}, not the principal's answer to an ask"
    if not (isinstance(row.get("principal_turn_sha256"), str) and re.fullmatch(r"[0-9a-f]{64}",
                                                                                 row["principal_turn_sha256"])):
        return f"{did} carries no principal_turn_sha256: it binds no turn of his"
    phrase = swap_phrase_problem(r, row)
    if phrase:
        return f"{did}: {phrase}"
    if row.get("target_id") != entry["ask"]:
        return f"{did} answers {row.get('target_id')!r}, not the ask {entry['ask']!r} the entry names"
    made = _utc(row.get("created_at"))
    if made is None or made <= round_time(r):
        return (f"{did} is dated {row.get('created_at')!r}, not after round {r} published ({published_text(r)}): "
                f"no word on a swap before the value it replaces was out")
    later = [x.get("id") for x in rows if isinstance(x, dict) and x is not row and
             (x.get("supersedes_id") == did or
              (x.get("target_id") == entry["ask"] and
               # glitch-45's re-check, R-4: a same-ask row with no readable time refuses, never reads as earlier
               (_utc(x.get("created_at")) is None or _utc(x.get("created_at")) > made)))]
    if later:
        return (f"{did} is superseded, or its ask {entry['ask']} answered or withdrawn again, by {later[0]}: a word "
                f"taken back binds no swap")
    if row.get("expires_at") is not None:
        ends = _utc(row["expires_at"])
        clock = datetime.now(timezone.utc).timestamp() if now is None else now
        if ends is None or ends <= clock:
            return f"{did} expired at {row['expires_at']!r}: an expired word binds no swap"
    return None


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
    if beacon.get("superseded") != [dict(e) for e in SUPERSEDED_ROUNDS]:
        raise BeaconRefused("take_order_beacon.superseded is not order_beacon.SUPERSEDED_ROUNDS (option A+)")
    r = beacon.get("round")
    if type(r) is not int:
        raise BeaconRefused(f"take_order_beacon.round is {r!r}: a round is registered when the draft is regenerated "
                            f"for its review, and no order exists without one")
    round_time(r)
    if r in [e["round"] for e in SUPERSEDED_ROUNDS]:
        raise BeaconRefused(f"take_order_beacon.round {r} is superseded; a superseded round is never the registered one")
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
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "gap-study-4-order-beacon"}), timeout=TIMEOUT_S) as got:  # noqa: S310 (a fixed https relay; drand.cloudflare.com answers 403 to the default agent)
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


def push_witness_problem(commit, round_no: int, pushes, contains, lead: int = WITNESS_LEAD_S) -> str | None:
    """Why GitHub's push records do not witness the round's registration in time (ruling 1), or None.

    `commit` is the commit that set REGISTERED_ROUND to `round_no` (None when no commit did); `pushes` is
    [(unix time, pushed sha)] as GitHub recorded them on WITNESS_REPO; `contains(commit, sha)` says whether `sha`'s
    history holds `commit`. A push counts only if it holds the commit and GitHub stamped it at least `lead` seconds
    (WITNESS_LEAD_S; SWAP_LEAD_S for a before_publication swap) before the round's publication time."""
    if not (isinstance(commit, str) and SEED_SHAPE.fullmatch(commit)):
        return (f"no commit in this history sets REGISTERED_ROUND to {round_no}: the round's registration has no "
                f"commit to witness")
    deadline = round_time(round_no) - lead
    held = sorted(t for t, sha in pushes if contains(commit, sha))
    if not held:
        return (f"GitHub returns no push to {WITNESS_REPO} holding {commit[:12]}, the commit that registered round "
                f"{round_no}: either it was never mirrored or GitHub no longer returns the record ({RETENTION_NOTE}); "
                f"a missing record never passes")
    if held[0] > deadline:
        return (f"GitHub's first push to {WITNESS_REPO} holding {commit[:12]} is stamped {iso(held[0])}, later than "
                f"{iso(deadline)} ({lead} s before round {round_no} is published): the round could have been "
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
