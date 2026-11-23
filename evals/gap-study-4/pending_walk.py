"""Live harness: the acceptance-walk road's records for a vendor walk whose native cross-check is pending.

Registration review finding 2 (glitch-06, 14 Oct 2026): while no native-session reader is registered, every Gemini
(and later Codex) drive stops with drive.NativeCrossCheckPending (departure D-INT-1), and the walk runner used to hold
any walk whose drive raised, so no vendor walk could ever be committed, and registration (which needs one) could never
be reached by real evidence. Now such a walk is committed through WalkRepo with every record it made, and with:

  check.json   check_doc(): {"walk", "status": "pending-native-reader", "why": the driver ledger's own pending why}
               in place of the checker's reading (the checker never ran: the driver stops before it);
  grade.json   status(): {"graded": false, "status": "pending-native-reader", "why": "not graded, because ..."}, which
               run.grade_walk returns for a ledger whose cross_check_status is pending, so run.walk_problems regrades it
               to the same bytes.

A pending walk is never graded, never counted as rehearsal coverage (walk_plan's and fixture_walk's coverage count a
walk only when it is graded true or superseded by a verified graded-true regrade and re-checked by the vendor checker
under the constants in force: coverage_status; lane vendor-admission T4 P5, R-9), and never re-run (its id is
registered; a retry is a new walk id). After a reader is registered,
walk_regrade.py re-derives its cross-check and grade from the committed bytes into rehearsals/<walk>/regrade.json, a
new superseding record; the walk's own commit and records are never touched.

Both documents are derived from the driver ledger alone, so the registration road re-derives them byte for byte.
"""
from __future__ import annotations

PENDING = "pending-native-reader"
PENDING_STATUS_KEYS = ("status", "why")


def _pending(ledger):
    s = ledger.get("cross_check_status") if isinstance(ledger, dict) else None
    if isinstance(s, dict) and set(s) == set(PENDING_STATUS_KEYS) and s["status"] == "pending" \
            and isinstance(s["why"], str) and s["why"]:
        return s
    return None


def status(ledger):
    """grade.json's document for a walk whose driver ledger records a pending native cross-check, else None."""
    s = _pending(ledger)
    if s is None:
        return None
    return {"graded": False, "status": PENDING, "why": f"not graded, because its native cross-check is pending: "
                                                       f"{s['why']}"}


def check_doc(walk: str, ledger) -> dict:
    """check.json's document for a pending walk; ValueError when the ledger records no pending cross-check."""
    s = _pending(ledger)
    if s is None:
        raise ValueError("the driver ledger records no pending native cross-check: not a pending walk")
    return {"walk": walk, "status": PENDING, "why": s["why"]}


def _regrade_state(base, walk: str):
    """A regrade's standing for coverage: "graded" when its bytes re-derive (walk_regrade.regrade_doc from the walk's
    committed bytes) and it grades the walk; "refused" when they re-derive and it does not (its native cross-check
    refused); None when there is none or it does not re-derive (an error included): it then supersedes nothing."""
    import walk_regrade
    from pathlib import Path
    path = Path(base) / walk / walk_regrade.REGRADE_FILE
    if not path.is_file():
        return None
    try:
        doc = walk_regrade.regrade_doc(walk, Path(base).parent)
        if walk_regrade.regrade_bytes(doc) != path.read_bytes():
            return None
    except Exception:  # noqa: BLE001 - an unverifiable regrade supersedes nothing, fail closed
        return None
    return "graded" if doc.get("graded") is True else "refused"


def coverage_status(base, walk: str, *, strict=None):
    """Batch-8 fix ruling (glitch-06, 14 Oct 2026; CP6: "Every walk is graded but never counted"): None when the walk
    counts as coverage, else why not. A walk covers its spec only when its grade.json is graded true and its check.json
    passes checker_standing (BOOTSTRAP B5: no constant-bound checker reason, checked under the constants in force), or
    when it is a pending walk that a verified graded-true regrade supersedes and whose latest recheck passes
    checker_standing's pending road (T4 P5, R-9: the checker never ran on it, so the regrade alone never counts it).
    Fail closed: a missing or unreadable grade.json, an ungraded walk, a pending walk, a pending walk whose verified
    regrade refused and one regraded with no checker reading under the constants in force are each reported, never
    counted. `strict` (OD131) is handed to checker_standing on both roads."""
    import json
    from pathlib import Path
    try:
        grade = json.loads((Path(base) / walk / "grade.json").read_bytes())
    except (OSError, ValueError):
        return "grade unreadable"
    if not isinstance(grade, dict):
        return "grade unreadable"
    if grade.get("graded") is True:
        return checker_standing(base, walk, strict=strict)
    if grade.get("status") == PENDING:
        state = _regrade_state(base, walk)
        # lane vendor-admission T4 P5, R-9 (c): a verified graded-true regrade counts the walk only through a checker
        # reading under the constants in force (checker_standing's pending road), never on the regrade alone
        return checker_standing(base, walk, pending=True, strict=strict) if state == "graded" else "regrade refused" \
            if state == "refused" else "pending"
    return "not graded"


CHECK_KEYS = ("walk", "checked", "checker_reasons", "events", "route", "route_refused", "checker_constants_sha256")
# glitch-b5's ruling 3 (16 Oct 2026): walk_runner.check_record also writes the walk's no-visible-output nudge count; a
# check.json written before the ruling lacks it. Either shape is walk_runner's; the count is an int >= 0 or null.
CHECK_NUDGE_KEY = "no_output_nudges"


# glitch-b5's Agent parity ruling, part 6 (16 Oct 2026): check.json also carries agent_calls (an int) and subagents
# ({calls, models}); a check.json written before it lacks both. Under the constants in force a checked walk's
# effective reading carries a valid pair.
CHECK_AGENT_KEYS = ("agent_calls", "subagents", "nested_cli_calls")   # + W-3b: the agent-CLI calls Bash ran
AGENT_CALL_KEYS = ("tool_use_id", "agent_id", "is_async", "status", "resolved_model", "completion")   # + r10 R-B


def valid_agent_summary(count, subagents, nested) -> bool:
    """nested_cli_calls (W-3b) an int >= 0; agent_calls an int >= 0; subagents exactly {calls, models, stream_file_differences (an int >= 0)}: calls a list
    of that many {tool_use_id: str,
    agent_id, status, resolved_model, completion: str or None, is_async: bool or None}, models a sorted list of
    distinct str."""
    if type(nested) is not int or nested < 0:
        return False
    if type(count) is not int or count < 0 or not isinstance(subagents, dict) or \
            set(subagents) != {"calls", "models", "stream_file_differences"}:
        return False
    d = subagents["stream_file_differences"]               # review r11, R11-1: how many stream records differ
    if type(d) is not int or d < 0:
        return False
    calls, models = subagents["calls"], subagents["models"]
    if not isinstance(calls, list) or len(calls) != count or not isinstance(models, list) \
            or not all(type(m) is str for m in models) or models != sorted(set(models)):
        return False
    return all(isinstance(c, dict) and set(c) == set(AGENT_CALL_KEYS) and type(c["tool_use_id"]) is str
               and all(c[k] is None or type(c[k]) is str for k in ("agent_id", "status", "resolved_model", "completion"))
               and (c["is_async"] is None or type(c["is_async"]) is bool) for c in calls)


def valid_nudge_count(n) -> bool:
    """A no-visible-output nudge count: an int >= 0 (never a bool, a float or null)."""
    return type(n) is int and n >= 0


def check_keys_ok(check) -> bool:
    """check.json carries exactly walk_runner's keys, with or without the nudge count, and that count is a count or
    null. Whether null may stand is checker_standing's (review r6 MINOR 2): only under older constants."""
    if not isinstance(check, dict):
        return False
    if set(check) == set(CHECK_KEYS):
        return True
    n = check.get(CHECK_NUDGE_KEY)
    if set(check) == set(CHECK_KEYS) | {CHECK_NUDGE_KEY}:
        return n is None or valid_nudge_count(n)
    a, s, c = check.get("agent_calls"), check.get("subagents"), check.get("nested_cli_calls")    # + W-3b
    if set(check) == set(CHECK_KEYS) | {CHECK_NUDGE_KEY} | set(CHECK_AGENT_KEYS[:2]):    # written before W-3b
        return (n is None or valid_nudge_count(n)) and ((a is None and s is None) or valid_agent_summary(a, s, 0))
    return (set(check) == set(CHECK_KEYS) | {CHECK_NUDGE_KEY} | set(CHECK_AGENT_KEYS)
            and (n is None or valid_nudge_count(n))
            and ((a is None and s is None and c is None) or valid_agent_summary(a, s, c)))


def checker_standing(base, walk: str, *, pending: bool = False, strict=None):
    """BOOTSTRAP B5 (glitch-6b's first-walk bootstrap ruling, 15 Oct 2026; required, or the falsifier argument fails):
    None when a graded walk's check.json lets it count, else why not. A walk is graded whenever its first agent turn
    ran, whatever its checker reasons; a walk whose checker named a reason a CHECKER_CONSTANTS value decides
    (check_take.CONSTANT_BOUND_REASONS) is never counted, and neither is one checked under constants other than those
    in force (its check.json's checker_constants_sha256): it reads stale until it is regraded. Fail closed: a missing
    or unreadable check.json, one not exactly walk_runner.check_record's keys, one the checker did not run on, one whose
    routing refused, and one with a reason that is not a string of routing.json's operator_reasons (the pre-registered
    rehearsal_reasons) are "check unreadable"; constants still PENDING are reported too. OD131 (walk-cover strict):
    given `strict`, a set of reasons (strict_reasons), a walk whose effective reading carries one is never counted
    either (STRICT_WHY); without it, nothing here changes."""
    import json
    from pathlib import Path
    import check_take
    try:
        check = json.loads((Path(base) / walk / "check.json").read_bytes())
    except (OSError, ValueError):
        return "check unreadable"
    if pending:
        return pending_standing(base, walk, check, strict)
    if not check_keys_ok(check) or check.get("checked") is not True \
            or check.get("route_refused") is not None or not isinstance(check.get("route"), str) \
            or not isinstance(check.get("checker_reasons"), list):
        return "check unreadable"
    events = check["events"]              # review NIT B: exactly what agent_adapter.harness_records writes
    if not (isinstance(events, dict) and set(events) == {"outside_reach"} and type(events["outside_reach"]) is int
            and events["outside_reach"] >= 0):
        return "check unreadable"
    nudges = check.get(CHECK_NUDGE_KEY)                       # check.json's own count
    latest = latest_recheck(base, walk)      # the recheck-coverage ruling (glitch-6b, 15 Oct 2026)
    if isinstance(latest, str):
        return latest
    eff_nudges = nudges
    eff_agent = (check.get("agent_calls"), check.get("subagents"), check.get("nested_cli_calls"))
    if latest is not None:
        check = dict(check, checker_reasons=latest["checker_reasons"],
                     checker_constants_sha256=latest["checker_constants_sha256"])
        eff_nudges = latest.get(CHECK_NUDGE_KEY)
        eff_agent = (latest.get("agent_calls"), latest.get("subagents"), latest.get("nested_cli_calls"))

    import routing                        # review MINOR 2: every reason a str of the pre-registered vocabulary
    vocabulary = routing.load_table()["operator_reasons"]
    if not isinstance(check["checker_reasons"], list) or \
            not all(isinstance(r, str) and r in vocabulary for r in check["checker_reasons"]):
        return "check unreadable"
    bound = [r for r in check["checker_reasons"] if r in check_take.CONSTANT_BOUND_REASONS]
    if bound:
        return f"constant-bound checker reason: {', '.join(bound)}"
    if strict is not None:
        hit = strict_hits(check["checker_reasons"], strict)
        if hit:
            return f"{STRICT_WHY}: {', '.join(hit)}"
    try:
        now = constants_in_force(base, walk)
    except check_take.CheckRefused:
        return "the checker constants in force are PENDING"
    # review r6 MINOR 2 (glitch-b5, 16 Oct 2026): a walk checked under the constants in force carries its nudge count;
    # null (or no key) stands only for a reading under older constants. Review r7 MINOR 2: the reading that counts is
    # the EFFECTIVE one, the latest recheck's when there is one (its count, which walk_regrade recomputes), else
    # check.json's own
    if check.get("checker_constants_sha256") == now and not valid_nudge_count(eff_nudges):
        return "check unreadable: no no-visible-output nudge count under the checker constants in force"
    if check.get("checker_constants_sha256") == now and not valid_agent_summary(*eff_agent):    # Agent parity, part 6
        return "check unreadable: no Agent call count under the checker constants in force"
    if check.get("checker_constants_sha256") != now:
        return "stale: checked under other checker constants or code; regrade it"
    return None


PENDING_UNCHECKED = "pending: regraded, no checker reading under the constants in force"


def pending_standing(base, walk: str, check, strict=None):
    """Lane vendor-admission T4 P5, R-9 (c) (plan v4 section 6): the standing of a pending walk whose verified regrade
    grades it true. Its check.json is the pending document (the checker never ran); the effective reading is its
    latest recheck (latest_recheck), judged by the rules a checked walk's is: every reason a string of routing.json's
    operator_reasons, none in CONSTANT_BOUND_REASONS, checked under the constants in force for its harness, with a
    nudge count and an Agent summary. No recheck reads PENDING_UNCHECKED; anything else not exactly so is named."""
    import check_take
    import routing
    if not (isinstance(check, dict) and check.get("walk") == walk and set(check) == {"walk", *PENDING_STATUS_KEYS}
            and check["status"] == PENDING):
        return "check unreadable"
    latest = latest_recheck(base, walk)
    if latest is None:
        return PENDING_UNCHECKED
    if isinstance(latest, str):
        return latest
    reasons = latest.get("checker_reasons")
    vocabulary = routing.load_table()["operator_reasons"]
    if not isinstance(reasons, list) or not all(isinstance(r, str) and r in vocabulary for r in reasons):
        return "check unreadable"
    bound = [r for r in reasons if r in check_take.CONSTANT_BOUND_REASONS]
    if bound:
        return f"constant-bound checker reason: {', '.join(bound)}"
    if strict is not None:
        hit = strict_hits(reasons, strict)
        if hit:
            return f"{STRICT_WHY}: {', '.join(hit)}"
    try:
        now = constants_in_force(base, walk)
    except check_take.CheckRefused:
        return "the checker constants in force are PENDING"
    if latest.get("checker_constants_sha256") != now:
        return "stale: checked under other checker constants or code; regrade it"
    if not valid_nudge_count(latest.get(CHECK_NUDGE_KEY)):
        return "check unreadable: no no-visible-output nudge count under the checker constants in force"
    if not valid_agent_summary(latest.get("agent_calls"), latest.get("subagents"), latest.get("nested_cli_calls")):
        return "check unreadable: no Agent call count under the checker constants in force"
    return None


def walk_harness(base, walk: str):
    """The walk's harness as its driver ledger records it (agent.harness, as walk_regrade reads it); None when the
    ledger is missing or unreadable (check.json carries no harness), or its harness is not a string (review
    e-71a2b94 NIT 1: a malformed ledger reads as no harness, never a TypeError)."""
    import json
    from pathlib import Path
    try:
        ledger = json.loads((Path(base) / walk / "driver-ledger.json").read_bytes())
    except (OSError, ValueError):
        return None
    agent = ledger.get("agent") if isinstance(ledger, dict) else None
    harness = agent.get("harness") if isinstance(agent, dict) else None
    return harness if isinstance(harness, str) else None


def constants_in_force(base, walk: str) -> str:
    """Lane vendor-admission T4 P5 (plan v4 section 6, NIT 4): the digest a walk must have been checked under. A walk
    whose readable driver ledger names a vendor harness of check_take.checker_for is checked under CHECKER_CONSTANTS
    merged with that harness's block (vendor_checker_constants_sha256); every other walk (no ledger, an unreadable
    one, claude-code or any other harness, the bare check.json folders included) under checker_constants_sha256(), as
    before. A vendor walk misread on that fallback reads stale, never current: its digest is the merged one."""
    import check_take
    harness = walk_harness(base, walk)
    if harness in check_take.VENDOR_CHECKER_CONSTANTS and harness in check_take.CHECKER_ENTRIES:
        return check_take.vendor_checker_constants_sha256(harness)
    return check_take.checker_constants_sha256()


def latest_recheck(base, walk: str):
    """The recheck-coverage ruling (glitch-6b, 15 Oct 2026): the walk's LATEST recheck entry in the register, read with
    no git and no process (walk_plan's register-only road, P7), only the register and the recheck file opened. None
    when the register names none; the recheck file's {checker_reasons, checker_constants_sha256} when the file is
    there, is the bytes the entry names (sha256) and carries the entry's digest; else why the walk counts nothing
    (a str). Whether the recheck matches a fresh checker run on committed bytes is walk_regrade.py --check's, in
    checks.d, never run here."""
    import hashlib
    import json
    from pathlib import Path
    import walk_register
    try:
        reg = json.loads((Path(base) / walk_register.REGISTER_NAME).read_bytes(),
                         object_pairs_hook=walk_register.no_duplicate_keys)
    except FileNotFoundError:
        return None                       # no register here (a bare folder of walk records): nothing supersedes
    except (OSError, ValueError, walk_register.DuplicateKey):
        return "register unreadable"
    entries = [e for e in walk_register.rechecks_of(reg) if isinstance(e, dict) and e.get("walk") == walk]
    if not entries:
        return None
    e = entries[-1]
    if not isinstance(e.get("file"), str) or walk_register.RECHECK_FILE.fullmatch(e["file"]) is None:
        return "recheck entry unreadable"
    try:
        raw = (Path(base) / walk / e["file"]).read_bytes()
    except OSError:
        return f"recheck file missing: {e['file']}"
    if hashlib.sha256(raw).hexdigest() != e.get("sha256"):
        return f"recheck file differs from its register entry: {e['file']}"
    try:
        doc = json.loads(raw, object_pairs_hook=walk_register.no_duplicate_keys)
    except (ValueError, walk_register.DuplicateKey):
        return "recheck unreadable"
    if not isinstance(doc, dict) or doc.get("checker_constants_sha256") != e.get("checker_constants_sha256") \
            or doc.get("walk") != walk \
            or type(doc.get("n")) is not int or type(e.get("n")) is not int or doc["n"] != e["n"]:
        return f"recheck file does not carry its register entry's walk, ordinal and digest: {e['file']}"
    return {"checker_reasons": doc.get("checker_reasons"), "checker_constants_sha256": doc["checker_constants_sha256"],
            CHECK_NUDGE_KEY: doc.get(CHECK_NUDGE_KEY),           # review r7: null in a recheck written before it
            "agent_calls": doc.get("agent_calls"), "subagents": doc.get("subagents"),      # Agent parity, part 6
            "nested_cli_calls": doc.get("nested_cli_calls")}                                # W-3b


# OD131 (Javier, 25 Oct 2026, decision.jsonl: "walk-cover strict"; lane pf1-walk-cover-strict, the lane orchestrator's
# ruled design under Javier's standing delegation): a Claude walk counts as covered only if it rechecks clean under the
# harness as it will be frozen; OD132 (Javier, 26 Oct 2026: "walk-cover-o strict") a Codex walk too. A walk walk_plan
# names strict (strict_walks: arm A by OD131's wording, arm O by OD132's; arm G as coded) is not counted
# when its effective checker reading carries any reason the routing table, as HEAD's commit holds it, routes to
# harness-error: the set is derived from that table by its own evaluator (harness_error_reasons), never typed here.
# The constant-bound and stale rules above are unchanged, and a walk named nowhere strict counts as before.
STRICT_WHY = "harness-error checker reason under OD131 and OD132 (walk-cover strict)"
STRICT_UNREAD = "OD131 (walk-cover strict): the routing table at HEAD cannot be read"


class StrictUnreadable(ValueError):
    pass


class StrictReasons(frozenset):
    """harness_error_reasons' set, carrying the operator_reasons of the table it was derived from (`vocabulary`;
    None when a plain set is handed in)."""

    def __new__(cls, reasons=(), vocabulary=None):
        self = super().__new__(cls, reasons)
        self.vocabulary = None if vocabulary is None else frozenset(vocabulary)
        return self


def strict_hits(reasons, strict) -> list:
    """The reasons of `reasons` that are strict hits: in `strict`, or outside the vocabulary of the table `strict` was
    derived from, when it carries one (the review of ff58e02f, MINOR 2: the vocabulary check reads the working tree's
    table and the strict set HEAD's, so a reason HEAD's table does not know is never counted)."""
    vocabulary = getattr(strict, "vocabulary", None)
    return [r for r in reasons if r in strict or (vocabulary is not None and r not in vocabulary)]


def _git_show_head(path: str) -> bytes:
    """The bytes HEAD's commit holds at `path` (git show HEAD:./<name>, run beside the file, with no GIT_ variable of
    the environment, so another repository's GIT_DIR is never read); StrictUnreadable when git cannot say."""
    import os
    import subprocess
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    try:
        got = subprocess.run(["git", "-C", os.path.dirname(path), "show", "HEAD:./" + os.path.basename(path)],
                             capture_output=True, env=env, timeout=60)
    except (OSError, subprocess.SubprocessError) as exc:
        raise StrictUnreadable(f"git could not run: {exc}") from exc
    if got.returncode != 0:
        raise StrictUnreadable(f"git show exited {got.returncode}: "
                               f"{got.stderr.decode('utf-8', 'replace').strip()[:200]}")
    return got.stdout


def _table_problems(table) -> list:
    import routing
    if not isinstance(table, dict):
        return ["the table is not an object"]
    try:
        return routing.check_table(table)
    except Exception as exc:  # noqa: BLE001 - a table check_table cannot read is refused, fail closed
        return [f"routing.check_table raised {exc!r}"]


def head_routing_table() -> dict:
    """routing.json as the repository's HEAD commit holds it (beside routing.TABLE_PATH, read at call time), accepted
    only when routing.check_table accepts it; StrictUnreadable otherwise. HEAD's, never the working tree's: an
    uncommitted edit of the table moves no walk's standing."""
    import json
    import routing
    raw = _git_show_head(routing.TABLE_PATH)
    try:
        table = json.loads(raw)
    except ValueError as exc:
        raise StrictUnreadable(f"HEAD's routing.json is not JSON: {exc}") from exc
    problems = _table_problems(table)
    if problems:
        raise StrictUnreadable("HEAD's routing.json is refused by routing.check_table: " + "; ".join(problems[:3]))
    return table


def harness_error_reasons(table: dict) -> frozenset:
    """The checker reasons `table` routes to harness-error: each of its operator_reasons for which a condition on
    checker_reasons of a row whose route is harness-error (any phase; the row's any_of and all_of) holds when the
    take's checker_reasons is that reason alone, by routing.holds, the table's own evaluator. A row's other conditions
    are not read, so a reason any harness-error row can route there is enough: fail closed, such a walk is not
    counted; a none_of condition stops a route and never adds a reason. The set is a StrictReasons carrying the
    table's operator_reasons, so strict_hits also counts a reason the table does not know as a hit. StrictUnreadable
    when a condition cannot be evaluated."""
    import routing
    rows = [r for r in table["rows"] if r.get("route") == routing.labels4.HARNESS_ERROR]
    conds = [c for r in rows for c in (*r.get("any_of", []), *r.get("all_of", []))
             if isinstance(c, dict) and c.get("path") == routing.HAS_PATH]
    out = set()
    for reason in table["operator_reasons"]:
        try:
            if any(routing.holds(c, {routing.HAS_PATH: [reason]}, table) for c in conds):
                out.add(reason)
        except Exception as exc:  # noqa: BLE001 - an unreadable condition reads nothing, fail closed
            raise StrictUnreadable(f"a harness-error condition cannot be read for {reason!r}: {exc!r}") from exc
    return StrictReasons(out, table["operator_reasons"])


def strict_reasons() -> frozenset:
    """OD131's set: the reasons the routing table at HEAD routes to harness-error."""
    return harness_error_reasons(head_routing_table())


def uncounted_walks(base, walks, strict_walks=()) -> dict:
    """{walk id: why it is not counted} for the walk ids of `walks` under the rehearsals folder `base`; walk_plan's and
    fixture_walk's coverage never count them. The walks `strict_walks` names are judged by OD131's strict rule too
    (strict_reasons, read once per call, and only when one is named); when the table at HEAD cannot be read, each of
    them is reported (STRICT_UNREAD), never counted, and every other walk is judged as before."""
    strict_ids = {w for w in strict_walks if isinstance(w, str)}
    reasons, unread = None, None
    if strict_ids:
        try:
            reasons = strict_reasons()
        except StrictUnreadable as exc:
            unread = f"{STRICT_UNREAD}: {exc}"
    out = {}
    for w in walks:
        if not isinstance(w, str):
            continue
        if w in strict_ids and unread is not None:
            out[w] = unread
            continue
        strict = reasons if w in strict_ids else None
        why = coverage_status(base, w, strict=strict)
        if why is not None:
            out[w] = why
    return out
