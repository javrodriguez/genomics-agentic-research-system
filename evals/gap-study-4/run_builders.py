#!/usr/bin/env python3
"""The counted run's builders (lane run-launcher; glitch-f1's rulings on DESIGN-run-launcher.md, Thu 22 Oct 2026, under
Javier's standing delegation). batch.py --run builds its driver, repo, usage window, spend ledger and rows here.

STAGE S1, THE PLAN, THE ORDER, THE LEDGER AND THE WINDOW (pure logic, stdlib only, no model, network or container):

  run_arms         the registered arms that have rows, less each deferred arm (the frozen `deferred_arms`) with no
                   go record. go(arm) is the go-record reader (lane gemini-defer's R5, batch.deferred_go, wired in
                   stage S3); it returns the record or None, and raises on a record it cannot trust.
  run_rows         the frozen take_order filtered to those arms, in frozen relative order and never re-sorted, less
                   every slot with a final committed outcome; `arms` only narrows the set (the rehearsal's A), `limit`
                   cuts the list. An owed re-run is not final, so it keeps its frozen place; Batch checks the rest.
  order_problems   the publication check (ruling 2): the order in which each slot is first registered in takes.json,
                   within each launch part, is a subsequence of take_order. The base part is every registered arm
                   less the deferred ones; each deferred arm is a part of its own, so a later go registers its rows
                   after A and O rows that come later in take_order and still passes. A slot's first registration is
                   attempt 1.
  SpendLedger      read() returns exactly batch.LEDGER_KEYS: `start` the round's start (ROUND_START, ruling 5),
                   `spend` every record of the committed runtime record run-ledger.json (never trimmed; Google's
                   walk-phase read is one of them), `walks` one entry per money-billing (arm, model) of the run's arms
                   (no deferred arm without a go record), `trimmed` Javier's latest "caps trimmed" record or None,
                   `now` the ledger's clock (recorded, never the hold's). It refuses while any capped vendor has no
                   read (ruling 6). run-ledger.json is written only by append_spend and append_trim, one record per
                   commit, and its history must show exactly that. A spend read is the spend since the previous read
                   (an increment), never a running total: costs.spent_since sums every record, so a billing page's
                   total recorded twice is counted twice (fail-closed: it stops a wave early, never late).
  UsageWindow      wait_reset() reads each paused take's own vendor reset signal from its committed files (Claude
                   Code's rate_limit_event resetsAt; Codex's rate_limits resets_at; Gemini has none and raises), waits
                   until the latest reset plus RESET_MARGIN_S on the injected clock, and returns at once when it has
                   passed. A pause with no signal, a reset out of bounds or an unreadable file raises, so the loop
                   stops `failed` with the reason (batch's W1B2-5). A spend cap never reaches it: routing stops it.
"""
from __future__ import annotations

import copy
import datetime
import json
import os
import re
import subprocess
import sys
import tempfile
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

# Ruling 5 (glitch-f1, 22 Oct 2026): spend counts from Javier's D8 letter ("D8: B2", Tue 6 Oct 2026 23:43:50 EDT), the
# moment arms O and G were admitted; it predates every vendor walk (the first Gemini walk ran 14 Oct).
ROUND_START = "2026-10-07T03:43:50Z"
RUN_LEDGER_NAME = "run-ledger.json"
LEDGER_DOC_KEYS = ("spend", "trimmed")
SPEND_KEYS = ("vendor", "at", "usd", "source", "by")
TRIM_KEYS = ("kind", "by", "month", "at", "figures")
# Ruling 6: with no J6 read recorded when the run launches, Google's read is the computed high figure under this source.
COMPUTED_SOURCE = "computed, not a vendor read"
_O_SOURCE = ("the Codex2 subscription: $0 of OpenAI money (accounts.json openai-api.spend_cap_usd 0, Javier, 13 Oct 2026: "
             "'existing subscriptions only'; GAP4-COSTGATE-D8-20261021.md lines 21-22)")
_G_SOURCE = ("ruling 7 (glitch-f1, 22 Oct 2026): the walk-phase extrapolation's high column per take "
             "(GAP4-COSTGATE-D8-20261021.md lines 51-52: $140.97 and $27.74 over 180 takes each); used only after a "
             "go record")
# (arm, model) -> (dollars per try as a decimal string, its source). A money-billing pair absent here refuses.
COST_PER_TRY = {
    ("O", "gpt-6.1-sol"): ("0", _O_SOURCE),
    ("O", "gpt-6-luna"): ("0", _O_SOURCE),
    ("G", "gemini-3.8-flash"): ("0.78", _G_SOURCE),
    ("G", "gemini-3.5-flash-lite"): ("0.154", _G_SOURCE),
}
RESET_MARGIN_S = 120
RESET_SLEEP_MAX_S = 300
RESET_AHEAD_MAX_S = 8 * 24 * 3600
RESET_BEHIND_MAX_S = 24 * 3600
TURN_FILE = re.compile(r"turn-([0-9]+)\.jsonl")
NATIVE_TURN_FILE = re.compile(r"native-turn-([0-9]+)\.jsonl")


# MINOR-1 (review of 122b559e, glitch-f1's ruling): the arms a ruling defers, pinned here so the launcher never trusts
# the frozen design alone to carry them (OD105 deferred arm G; its frozen `deferred_arms` entry enters at the freeze
# line's draft regeneration). build_run refuses a design that has rows for one of them, does not defer it, and has no
# committed go record for it.
RULED_DEFERRALS = {"G": "OD105"}


class RunRefused(RuntimeError):
    """The run cannot be planned or built as asked; the message names the rule."""


class LedgerRefused(RuntimeError):
    """The spend ledger cannot be read as the money gate needs it."""


class WindowRefused(RuntimeError):
    """The usage window cannot tell when the vendor's window resets."""


# ------------------------------------------------------------------------------------------------ the plan
def run_arms(pre: dict, go) -> tuple:
    """The arms this run may drive: registered arms with at least one row, in pre['arms'] order, less every deferred
    arm whose go(arm) is None."""
    if not callable(go):
        raise RunRefused("the go-record reader must be callable (arm) -> record or None")
    rows = pre["rows"]
    deferred = pre.get("deferred_arms") or {}
    if not isinstance(deferred, dict):
        raise RunRefused("the frozen deferred_arms is not an object")
    out = []
    for arm in pre["arms"]:
        if not any(r["arm"] == arm for r in rows):
            continue
        if arm in deferred and go(arm) is None:
            continue
        out.append(arm)
    return tuple(out)


def ruled_deferral_problem(pre: dict, go):
    """MINOR-1: why the design in force may not run (an arm of RULED_DEFERRALS with rows, absent from the frozen
    deferred_arms, with no committed go record), or None. A design that defers the arm is unaffected."""
    deferred = pre.get("deferred_arms") or {}
    for arm, ruling in RULED_DEFERRALS.items():
        if any(r["arm"] == arm for r in pre["rows"]) and (not isinstance(deferred, dict) or arm not in deferred) \
                and go(arm) is None:
            return f"the frozen design does not defer arm {arm} ({ruling})"
    return None


def final_slots(history: list) -> set:
    """Every slot with a committed outcome that is final for it, or that a route ruling makes final (amendment)."""
    import batch
    return {o["slot"] for o in history if batch.is_outcome(o) and o.get("final") is True} | route_ruled_final(history)


def run_rows(pre: dict, history: list, *, go, arms=None, limit=None) -> list:
    """The rows to hand Batch.run: the frozen take_order filtered to the run's arms, in frozen order, less final slots,
    narrowed by `arms` and cut at `limit`."""
    allowed = run_arms(pre, go)
    if arms is None:
        chosen = set(allowed)
    else:
        if not isinstance(arms, (list, tuple)) or not arms or not all(isinstance(a, str) for a in arms):
            raise RunRefused("--arms names one or more arms")
        outside = sorted(set(arms) - set(allowed))
        if outside:
            raise RunRefused(f"arms {outside} are not among this run's arms {list(allowed)} (a deferred arm runs only "
                             f"after its go record; an arm without rows never runs)")
        chosen = set(arms)
    order = pre.get("take_order")
    if not isinstance(order, list) or not order:
        raise RunRefused("the frozen pre-registration has no take_order")
    if limit is not None and (type(limit) is not int or limit < 1):
        raise RunRefused("--limit is a positive whole number")
    done = final_slots(history)
    rows = [copy.deepcopy(r) for r in order if r["arm"] in chosen and r["slot"] not in done]
    return rows if limit is None else rows[:limit]


# ------------------------------------------------------------------------------------------------ the order check
def order_problems(registered: list, pre: dict) -> list:
    """Ruling 2: each slot's first registration (attempt 1), within each launch part, follows take_order."""
    order = pre.get("take_order")
    if not isinstance(order, list):
        return ["the frozen pre-registration has no take_order to check the registrations against"]
    where = {r["slot"]: (i, r["arm"]) for i, r in enumerate(order)}
    deferred = set(pre.get("deferred_arms") or {})
    seen, last, problems = set(), {}, []
    for n, row in enumerate(registered):
        slot = row.get("slot")
        if slot in seen:
            continue
        seen.add(slot)
        if slot not in where:
            problems.append(f"takes.json row {n}: slot {slot!r} is not in take_order")
            continue
        index, arm = where[slot]
        if row.get("arm") != arm:
            problems.append(f"takes.json row {n}: slot {slot!r} is registered under arm {row.get('arm')!r}, take_order "
                            f"has {arm!r}")
            continue
        if row.get("attempt") != 1:
            problems.append(f"takes.json row {n}: slot {slot!r} is first registered as attempt {row.get('attempt')!r}, "
                            f"not 1")
        part = arm if arm in deferred else "base"
        if part in last and index < last[part][0]:
            problems.append(f"takes.json row {n}: slot {slot!r} (take_order {index}) is registered after slot "
                            f"{last[part][1]!r} (take_order {last[part][0]}) in launch part {part!r}: not the "
                            f"frozen order")
        else:
            last[part] = (index, slot)
    return problems


# ------------------------------------------------------------------------------------------------ the spend ledger
def _git(repo, *args) -> str:
    got = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if got.returncode != 0:
        raise LedgerRefused(f"git {args[0]} failed (exit {got.returncode})")
    return got.stdout


def _aware(value, what: str) -> datetime.datetime:
    import costs
    try:
        return costs.utc(value)
    except (ValueError, TypeError, AttributeError) as e:
        raise LedgerRefused(f"{what} {value!r} is not an aware time: {e}") from None


def spend_record_problems(rec, *, now) -> list:
    """Why a stored spend record is refused: exactly SPEND_KEYS; a capped vendor; usd a non-negative decimal string;
    `at` aware, not before ROUND_START and not after `now`; source and by non-empty text."""
    import costs
    if type(rec) is not dict or set(rec) != set(SPEND_KEYS):
        return [f"a spend record is not exactly {list(SPEND_KEYS)}: {sorted(rec) if isinstance(rec, dict) else rec!r}"]
    p = []
    if rec["vendor"] not in costs.CAPS:
        p.append(f"spend vendor {rec['vendor']!r} is not a capped vendor {sorted(costs.CAPS)}")
    if type(rec["usd"]) is not str:
        p.append(f"spend usd {rec['usd']!r} is not a decimal string")
    else:
        try:
            costs.amount(rec["usd"])
        except ValueError as e:
            p.append(f"spend usd {rec['usd']!r}: {e}")
    for k in ("source", "by"):
        if not isinstance(rec[k], str) or not rec[k].strip():
            p.append(f"spend {k} is empty")
    try:
        at = _aware(rec["at"], "spend at")
        if at < _aware(ROUND_START, "the round's start"):
            p.append(f"spend at {rec['at']!r} is before the round's start {ROUND_START}")
        if at > _aware(now, "the ledger's clock"):
            p.append(f"spend at {rec['at']!r} is after the ledger's clock")
    except LedgerRefused as e:
        p.append(str(e))
    return p


def trim_record_problems(rec) -> list:
    """Why a stored "caps trimmed" record is refused: exactly costs' keys, kind "caps trimmed", by "Javier", a YYYY-MM
    month, an aware `at`, figures for every capped vendor. Whether it releases a month is costs.month_turn_allowed's."""
    import costs
    if type(rec) is not dict or set(rec) != set(TRIM_KEYS):
        return [f"a trim record is not exactly {list(TRIM_KEYS)}"]
    p = []
    if rec["kind"] != "caps trimmed" or rec["by"] != "Javier":
        p.append("a trim record is kind 'caps trimmed' by 'Javier'")
    if not isinstance(rec["month"], str) or not re.fullmatch(r"[0-9]{4}-(0[1-9]|1[0-2])", rec["month"]):
        p.append(f"trim month {rec['month']!r} is not YYYY-MM")
    try:
        _aware(rec["at"], "trim at")
    except LedgerRefused as e:
        p.append(str(e))
    if not isinstance(rec["figures"], dict) or set(rec["figures"]) != set(costs.CAPS):
        p.append(f"trim figures name exactly {sorted(costs.CAPS)}")
    return p


def ledger_doc_problems(doc) -> list:
    """The stored document: exactly {spend: [...], trimmed: [...]}, both lists."""
    if type(doc) is not dict or set(doc) != set(LEDGER_DOC_KEYS):
        return [f"{RUN_LEDGER_NAME} is not exactly {list(LEDGER_DOC_KEYS)}"]
    return [f"{RUN_LEDGER_NAME}'s {k} is not a list" for k in LEDGER_DOC_KEYS if type(doc[k]) is not list]


def ledger_history_problems(versions: list) -> list:
    """The committed versions of run-ledger.json, oldest first: each a valid document extending the previous one by
    exactly one record (spend or trimmed), every earlier record unchanged."""
    p, previous = [], {"spend": [], "trimmed": []}
    for n, doc in enumerate(versions):
        bad = ledger_doc_problems(doc)
        if bad:
            return [f"version {n}: {b}" for b in bad]
        grew = 0
        for k in LEDGER_DOC_KEYS:
            if doc[k][:len(previous[k])] != previous[k]:
                p.append(f"version {n}: an earlier {k} record changed or went (append-only)")
            grew += len(doc[k]) - len(previous[k])
        if grew != 1:
            p.append(f"version {n}: adds {grew} records, not exactly one")
        previous = doc
    return p


def ledger_path(root) -> Path:
    return Path(root) / RUN_LEDGER_NAME


def read_ledger_doc(root, repo) -> dict:
    """run-ledger.json as committed at HEAD, its whole history checked; {spend: [], trimmed: []} when never committed."""
    root, repo = Path(root).resolve(), Path(repo).resolve()
    rel = ledger_path(root).relative_to(repo).as_posix()
    if _git(repo, "status", "--porcelain", "--", rel).strip():
        raise LedgerRefused(f"{rel} has uncommitted changes")
    versions = []
    for sha in _git(repo, "log", "--reverse", "--format=%H", "--", rel).split():
        try:
            versions.append(json.loads(_git(repo, "show", f"{sha}:{rel}")))
        except ValueError:
            raise LedgerRefused(f"{rel} at {sha[:12]} is not JSON") from None
    bad = ledger_history_problems(versions)
    if bad:
        raise LedgerRefused("; ".join(bad))
    return versions[-1] if versions else {"spend": [], "trimmed": []}


def ledger_walks(pre: dict, history: list, arms) -> list:
    """One walk_gate entry per money-billing (arm, model) of `arms`: tries_left the pair's planned rows whose slot is
    not final, cost_per_try from COST_PER_TRY (a pair absent there refuses)."""
    import routing
    done = final_slots(history)
    out, seen = [], set()
    for r in pre["rows"]:
        harness = r["agent"]["harness"]
        key = (r["arm"], r["model"])
        if r["arm"] not in arms or harness in routing.NO_MONEY_HARNESSES or key in seen:
            continue
        seen.add(key)
        if harness not in routing.PAID_HARNESSES:
            raise LedgerRefused(f"harness {harness!r} bills money and has no vendor in routing.PAID_HARNESSES")
        if key not in COST_PER_TRY:
            raise LedgerRefused(f"arm {key[0]} model {key[1]!r} bills money and has no registered cost per try")
        left = sum(1 for x in pre["rows"] if (x["arm"], x["model"]) == key and x["slot"] not in done)
        out.append({"vendor": routing.PAID_HARNESSES[harness]["vendor"], "model": r["model"],
                    "agent": {"harness": harness, "version": r["agent"]["version"]},
                    "tries_left": left, "cost_per_try": COST_PER_TRY[key][0]})
    return out


def ledger_snapshot(doc: dict, *, pre: dict, history: list, arms, now) -> dict:
    """One reading for batch's money gate, exactly batch.LEDGER_KEYS, or LedgerRefused."""
    import costs
    bad = ledger_doc_problems(doc)
    for rec in (doc.get("spend") or []) if not bad else []:
        bad += spend_record_problems(rec, now=now)
    for rec in (doc.get("trimmed") or []) if not bad else []:
        bad += trim_record_problems(rec)
    if bad:
        raise LedgerRefused("; ".join(bad))
    unread = sorted(set(costs.CAPS) - {r["vendor"] for r in doc["spend"]})
    if unread:
        raise LedgerRefused(f"no spend read is recorded for {unread}: every capped vendor's spend since the round "
                            f"began is read first (Google's walk-phase spend included; ruling 6)")
    return {"now": _aware(now, "the ledger's clock").isoformat(),
            "walks": ledger_walks(pre, history, arms),
            "spend": [{"vendor": r["vendor"], "at": r["at"], "usd": r["usd"]} for r in doc["spend"]],
            "start": ROUND_START,
            "trimmed": doc["trimmed"][-1] if doc["trimmed"] else None}


def computed_reads(doc: dict) -> list:
    """Ruling 6: the vendors whose recorded reads include the computed fallback, for the run's report."""
    return sorted({r["vendor"] for r in doc.get("spend", []) if r.get("source") == COMPUTED_SOURCE})


def utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


class SpendLedger:
    """batch's spend ledger: read() is one checked reading of the committed run-ledger.json (ledger_snapshot)."""

    def __init__(self, *, root, repo, pre, history, arms, clock=utc_now):
        if not callable(history) or not callable(clock):
            raise TypeError("history and clock must be callable")
        self.root, self.repo, self.pre, self.history, self.arms, self.clock = root, repo, pre, history, tuple(arms), clock

    def read(self) -> dict:
        return ledger_snapshot(read_ledger_doc(self.root, self.repo), pre=self.pre, history=self.history(),
                               arms=self.arms, now=self.clock())


def _append(root, repo, key: str, rec: dict, subject: str) -> str:
    import takes
    root, repo = Path(root).resolve(), Path(repo).resolve()
    if _git(repo, "status", "--porcelain", "--untracked-files=all").strip():
        raise LedgerRefused(f"{RUN_LEDGER_NAME} is written only in a clean repository (no loop running)")
    takes.require_commit_identity(repo)
    doc = read_ledger_doc(root, repo)
    new = {k: list(doc[k]) for k in LEDGER_DOC_KEYS}
    new[key].append(rec)
    path = ledger_path(root)
    path.write_text(json.dumps(new, indent=2) + "\n", encoding="utf-8")
    rel = path.relative_to(repo).as_posix()
    try:
        _git(repo, "add", "--", rel)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt") as message:
            message.write(subject + "\n")
            message.flush()
            _git(repo, "commit", "-q", "-F", message.name)
    except LedgerRefused:
        _git(repo, "reset", "-q", "--", rel)
        tracked = _git(repo, "ls-tree", "--name-only", "HEAD", "--", rel).strip()
        if tracked:
            _git(repo, "checkout", "-q", "HEAD", "--", rel)
        else:
            path.unlink()
        raise
    return _git(repo, "rev-parse", "HEAD").strip()


def append_spend(rec: dict, *, root=HERE, repo=None, clock=utc_now) -> str:
    """One vendor spend read appended to run-ledger.json, one commit."""
    bad = spend_record_problems(rec, now=clock())
    if bad:
        raise LedgerRefused("; ".join(bad))
    return _append(root, repo if repo is not None else _repo_of(root), "spend", rec, "Record one vendor spend read")


def append_trim(rec: dict, *, root=HERE, repo=None) -> str:
    """Javier's "caps trimmed" record appended to run-ledger.json, one commit."""
    bad = trim_record_problems(rec)
    if bad:
        raise LedgerRefused("; ".join(bad))
    return _append(root, repo if repo is not None else _repo_of(root), "trimmed", rec, "Record Javier's caps trimmed")


def _repo_of(root) -> Path:
    return Path(_git(root, "rev-parse", "--show-toplevel").strip()).resolve()


# ------------------------------------------------------------------------------------------------ the usage window
def _jsonl(data: bytes) -> list:
    out = []
    for line in data.decode("utf-8", "replace").splitlines():
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        if isinstance(obj, dict):
            out.append(obj)
    return out


def _epoch(value, what: str) -> float:
    if type(value) not in (int, float) or value <= 0:
        raise WindowRefused(f"{what} {value!r} is not an epoch time")
    return float(value)


def claude_reset(files: dict) -> float:
    """Claude Code: the last rate_limit_event whose status is not 'allowed' gives its resetsAt; with none, the latest
    resetsAt of a window at full utilisation, else the last event's resetsAt. Files: {name: bytes}, turn order."""
    events = []
    for name in sorted((n for n in files if TURN_FILE.fullmatch(os.path.basename(n))),
                       key=lambda n: int(TURN_FILE.fullmatch(os.path.basename(n)).group(1))):
        events += [o["rate_limit_info"] for o in _jsonl(files[name])
                   if o.get("type") == "rate_limit_event" and isinstance(o.get("rate_limit_info"), dict)]
    if not events:
        raise WindowRefused("the paused Claude Code take records no rate_limit_event (no reset signal)")
    refused = [e for e in events if e.get("status") != "allowed"]
    if refused:
        return _epoch(refused[-1].get("resetsAt"), "the refused rate_limit_event's resetsAt")
    last = events[-1]
    full = [w.get("resetsAt") for w in (last.get("unifiedWindows") or {}).values()
            if isinstance(w, dict) and type(w.get("utilization")) in (int, float) and w["utilization"] >= 1]
    if full:
        return max(_epoch(x, "a full window's resetsAt") for x in full)
    return _epoch(last.get("resetsAt"), "the last rate_limit_event's resetsAt")


def codex_reset(files: dict) -> float:
    """Codex: the last rate_limits reading gives the latest resets_at among windows at 100 percent used, else the
    latest of all its windows."""
    readings = []
    for name in sorted((n for n in files if NATIVE_TURN_FILE.fullmatch(os.path.basename(n))),
                       key=lambda n: int(NATIVE_TURN_FILE.fullmatch(os.path.basename(n)).group(1))):
        for o in _jsonl(files[name]):
            payload = o.get("payload")
            if isinstance(payload, dict) and isinstance(payload.get("rate_limits"), dict):
                readings.append(payload["rate_limits"])
    if not readings:
        raise WindowRefused("the paused Codex take records no rate_limits reading (no reset signal)")
    windows = [w for k in ("primary", "secondary") for w in [readings[-1].get(k)] if isinstance(w, dict)]
    if not windows:
        raise WindowRefused("the Codex take's last rate_limits reading holds no window")
    full = [w for w in windows if type(w.get("used_percent")) in (int, float) and w["used_percent"] >= 100]
    return max(_epoch(w.get("resets_at"), "a Codex window's resets_at") for w in (full or windows))


RESET_READERS = {"claude-code": claude_reset, "codex": codex_reset}


def reset_for(harness: str, files: dict) -> float:
    """The vendor's own reset time for a paused take of `harness`. Gemini records none (routing's named residual: the
    operator treats a Gemini pause past its window as a stop), so it raises, as does any harness without a reader."""
    reader = RESET_READERS.get(harness)
    if reader is None:
        raise WindowRefused(f"harness {harness!r} records no reset signal the window can read: a pause of it stops for "
                            f"the operator (routing's named residual)")
    return reader(files)


def paused_takes(history: list) -> list:
    """(slot, attempt) of every pause in the tail batch.restart_waits reads: a committed pause, or the ruled take of a
    ruling that routes pause."""
    import batch
    from graders import labels4
    at = [i for i, e in enumerate(history) if batch.is_outcome(e)][-batch.MAX_OPEN:]
    tail = history[at[0]:] if at else history
    return [(e["slot"], e["attempt"]) for e in tail if batch.effective_route(e) == labels4.PAUSE]


def wait_target(history: list, harness_of, files_of, now: float) -> float:
    """The time to wait until: the latest vendor reset of the paused takes plus RESET_MARGIN_S, each within bounds."""
    takes = paused_takes(history)
    if not takes:
        raise WindowRefused("the loop waits for the usage window, and the committed history holds no pause")
    resets = []
    for slot, attempt in takes:
        reset = reset_for(harness_of(slot, attempt), files_of(slot, attempt))
        if reset > now + RESET_AHEAD_MAX_S:
            raise WindowRefused(f"slot {slot} attempt {attempt}: the vendor's reset is {reset - now:.0f} s ahead, "
                                f"past the {RESET_AHEAD_MAX_S} s bound")
        if reset < now - RESET_BEHIND_MAX_S:
            raise WindowRefused(f"slot {slot} attempt {attempt}: the vendor's reset is {now - reset:.0f} s behind, "
                                f"past the {RESET_BEHIND_MAX_S} s bound (a stale signal)")
        resets.append(reset)
    return max(resets) + RESET_MARGIN_S


def wait_until(target: float, clock, sleep) -> None:
    """Return at once when the clock has reached target; else sleep in chunks of at most RESET_SLEEP_MAX_S."""
    while True:
        now = clock()
        if now >= target:
            return
        sleep(min(RESET_SLEEP_MAX_S, target - now))


def committed_take_files(root, repo, slot, attempt) -> dict:
    """{path: bytes} of every file committed at HEAD under takes/<slot>/<attempt>/."""
    import mode_binding
    root, repo = Path(root).resolve(), Path(repo).resolve()
    rel = (root / mode_binding.TAKES_DIR / str(slot) / str(attempt)).relative_to(repo).as_posix()
    names = _git(repo, "ls-tree", "-r", "--name-only", "HEAD", "--", rel + "/").split("\n")
    out = {}
    for name in (n for n in names if n):
        got = subprocess.run(["git", "-C", str(repo), "show", f"HEAD:{name}"], capture_output=True)
        if got.returncode != 0:
            raise WindowRefused(f"{name} cannot be read at HEAD")
        out[name] = got.stdout
    return out


def registered_harness(rows: list, slot, attempt) -> str:
    found = [r for r in rows if r.get("slot") == slot and r.get("attempt") == attempt]
    if len(found) != 1:
        raise WindowRefused(f"slot {slot} attempt {attempt} has {len(found)} registrations in takes.json")
    return found[0]["agent"]["harness"]


class UsageWindow:
    """batch's usage window: wait_reset() waits for the paused takes' vendor resets (wait_target, wait_until)."""

    def __init__(self, *, root, repo, history, rows, clock, sleep):
        for name, fn in (("history", history), ("rows", rows), ("clock", clock), ("sleep", sleep)):
            if not callable(fn):
                raise TypeError(f"{name} must be callable")
        self.root, self.repo, self.history, self.rows, self.clock, self.sleep = root, repo, history, rows, clock, sleep

    def wait_reset(self) -> None:
        rows = self.rows()
        target = wait_target(self.history(), lambda s, a: registered_harness(rows, s, a),
                             lambda s, a: committed_take_files(self.root, self.repo, s, a), self.clock())
        wait_until(target, self.clock, self.sleep)


# =====================================================================================================================
# STAGE S2, THE TAKE ROAD (glitch-f1's rulings 4 and 8 on DESIGN-run-launcher.md, 22 Oct 2026). The counted run's
# production builders for takes, mirroring walk_builders' (walk_driver_for, production_builders) and reusing every
# value that is not walk-specific. drive.py is in both hashed reader-source lists, so nothing here edits it.
#   run_login_path  ruling 4: the counted run's Claude Code login is RUN_LOGIN_FILES["claude-run"], one line
#                   CLAUDE_CODE_OAUTH_TOKEN=<token> that Javier fills by the one key road; ruling 8: the rehearsal take
#                   runs on the walk login (walk_builders.walk_login_path("claude1")) while it is live. A path only:
#                   walk_builders.login_file_by_name checks the file by NAME, run_take reads the value at exec time.
#   take_identity   the take's identity from its one open registration in the committed takes.json: the row's index,
#                   its registration commit (takes.row_commits) and session_id = takes.session_id_for(that commit).
#   build_take_run_tree  walk_builders.build_run_tree for a take: drive.clean_run_tree at the take's own session, then
#                   R-6's native instruction file and R-H5's agent home for a codex or gemini row.
#   prepare_take    the run tree, then the half's fixture (walk_builders.build_walk_fixture, unchanged) and the
#                   identity, exactly drive.IDENTITY_KEYS; a refused fixture removes the tree.
#   TakeRoad        the per-take state, keyed by slot: prepared before the sub-driver's launch, read by its hooks
#                   (sidecar_for, spec_for, project_for, identity_for), discarded (its run tree removed) once the
#                   take's commit lands, or kept for a human when the take needs a ruling.
#   LeasePool       the Codex lease road for many concurrent takes: one walk_builders.CodexLeaseRoad per take, placed
#                   by spec_for into that take's config folder after its freshness check against that take's budget;
#                   login_file_for(take) is that take's placement; secrets() the union of every placed lease's.
#   RunDriver       batch's driver over one drive.walk_driver(records="takes") per harness: launch routes by the row's
#                   harness and records container id -> sub-driver, so drive, remove, record_files and published reach
#                   the take's own. drive.launch_problems runs before anything is built.
#   build_run       the driver, one TakeRepo (secrets the union of every run harness's), the usage window, the spend
#                   ledger (None when no run harness bills money) and the rows; refuses by name before anything is built.
# =====================================================================================================================
import threading  # noqa: E402

RUN_ACCOUNT = "claude-run"
# Ruling 4 (glitch-f1, 22 Oct 2026): the fresh run token the freeze gate issues, beside the walk tokens' folders, in its
# own mode-700 folder; on Javier's freeze-gate card. Never opened by any session.
# Part T contract line 1 (its review MAJOR-1): a plain literal, keys included, that ops/gap4_run_launcher.py reads with
# ast.literal_eval and stat-checks on athena by path.
RUN_LOGIN_FILES = {"claude-run": "/home/javier/gap4-secrets/claude-run/claude-run-token"}
# Ruling 8: the rehearsal take runs before the freeze gate, on the walk login, never the run token.
REHEARSAL_ACCOUNT = "claude1"


def run_login_path(account: str = RUN_ACCOUNT):
    """The Claude Code login file's path for `account`: RUN_LOGIN_FILES' for the counted run, the box's walk record for
    the rehearsal's walk account (a Missing while this tree records none). A path only, never opened here."""
    import walk_builders as wb
    if account == REHEARSAL_ACCOUNT:
        return wb.walk_login_path(account)
    if account not in RUN_LOGIN_FILES:
        raise RunRefused(f"no run login is recorded for account {account!r} (RUN_LOGIN_FILES: "
                         f"{sorted(RUN_LOGIN_FILES)}; the rehearsal's walk account: {REHEARSAL_ACCOUNT!r})")
    path = RUN_LOGIN_FILES[account]
    if not isinstance(path, str) or not os.path.isabs(path) or os.path.normpath(path) != path:
        raise RunRefused(f"RUN_LOGIN_FILES[{account!r}] is not an absolute, normalised path: {path!r}")
    return path


def take_identity(root, repo, slot) -> dict:
    """{index, attempt, row_commit, session_id} of the slot's one open registration in the committed takes.json."""
    import drive
    import takes
    root, repo = Path(root).resolve(), Path(repo).resolve()
    reg = drive.open_registration(root, repo, slot)
    rows = takes.load_rows(root=root, repo=repo)
    where = [i for i, r in enumerate(rows) if r == reg]
    if len(where) != 1:
        raise RunRefused(f"slot {slot!r}'s open registration is not one row of takes.json ({len(where)} found)")
    commits = takes.row_commits(root=root, repo=repo)
    if where[0] not in commits:
        raise RunRefused(f"takes.json row {where[0]} has no registration commit")
    commit = commits[where[0]]
    return {"index": where[0], "attempt": reg["attempt"], "row_commit": commit,
            "session_id": takes.session_id_for(commit)}


def build_take_run_tree(session_id: str, *, repo, commit: str, exclude, harness=None) -> Path:
    """The take's own checkout of `commit` at its session's neutral name, with R-6's native instruction file and
    R-H5's agent home for a codex or gemini harness; any refusal is walk_builders.BuilderRefused, nothing left."""
    import shutil
    import drive
    import walk_builders as wb
    if not isinstance(session_id, str) or not session_id:
        raise wb.BuilderRefused("the take's run tree needs its session id")
    if not isinstance(commit, str) or not wb.HEX40.fullmatch(commit):
        raise wb.BuilderRefused(f"the run tree's commit {commit!r} is not a 40-hex commit id")
    if not isinstance(exclude, (list, tuple)) or not all(isinstance(p, str) and p and not os.path.isabs(p)
                                                         for p in exclude):
        raise wb.BuilderRefused("the run tree's exclusions are a list of relative paths")
    try:
        tree = drive.clean_run_tree(commit, session_id, list(exclude), Path(repo))
    except (SystemExit, Exception) as e:  # noqa: BLE001 - clean_run_tree refuses by SystemExit
        raise wb.BuilderRefused(f"the run tree was not built: {type(e).__name__}: {e}") from None
    try:
        wb.place_instruction_file(tree, harness, repo=repo, commit=commit, session_id=session_id, exclude=list(exclude))
        wb.place_agent_home(tree, harness, session_id=session_id, exclude=list(exclude))
    except BaseException:
        shutil.rmtree(tree, ignore_errors=True)
        raise
    return tree


def exported_gars_tree(repo, commit: str) -> str:
    """Pre-freeze review 2, m13 (lane fold2-ld, 29 Oct 2026): the gars tree of the commit a take's run tree is exported
    from, read at export (`git rev-parse <commit>:gars`), never the checker's constant handed back to it; refused
    (walk_builders.BuilderRefused) unless `commit` is a 40-hex commit id whose gars tree reads as a 40-hex tree id."""
    import walk_builders as wb
    if not isinstance(commit, str) or not wb.HEX40.fullmatch(commit):
        raise wb.BuilderRefused(f"the run tree's commit {commit!r} is not a 40-hex commit id")
    got = subprocess.run(["git", "-C", str(repo), "rev-parse", "--verify", "--quiet", f"{commit}:gars"],
                         capture_output=True, text=True)
    tree = got.stdout.strip()
    kind = subprocess.run(["git", "-C", str(repo), "cat-file", "-t", tree], capture_output=True, text=True) if (
        got.returncode == 0 and wb.HEX40.fullmatch(tree)) else None
    if kind is None or kind.returncode != 0 or kind.stdout.strip() != "tree":
        raise wb.BuilderRefused(f"the gars tree of {commit[:12]} cannot be read in {repo}: a take records the tree "
                                f"it was exported from")
    return tree


def prepare_take(row: dict, *, root, repo, origin, exclude, tree_reader=None, tree_builder=None,
                 fixture_builder=None) -> dict:
    """The take's state: its identity (exactly drive.IDENTITY_KEYS), run tree and project. A fixture refused removes
    the tree it was built in. The identity's gars_tree_sha is the gars tree of the commit the run tree is exported
    from, read by `tree_reader(origin repo, commit)` (exported_gars_tree) before the tree is built (m13)."""
    import drive
    import walk_builders as wb
    tree_reader = exported_gars_tree if tree_reader is None else tree_reader
    tree_builder = build_take_run_tree if tree_builder is None else tree_builder
    fixture_builder = wb.build_walk_fixture if fixture_builder is None else fixture_builder
    ident = take_identity(root, repo, row["slot"])
    sid = ident["session_id"]
    project = drive.neutral_name(sid)
    origin_repo, commit = origin
    gars_tree_sha = tree_reader(origin_repo, commit)
    tree = tree_builder(sid, repo=origin_repo, commit=commit, exclude=exclude, harness=row["agent"]["harness"])
    try:
        record, source = fixture_builder(row, tree, project)
    except BaseException:
        wb.remove_run_tree(tree)
        raise
    identity = {"session_id": sid, "row": ident["index"], "row_commit": ident["row_commit"], "source": source,
                "fixture": record, "gars_tree_sha": gars_tree_sha}
    return {"slot": row["slot"], "attempt": ident["attempt"], "tree": Path(tree), "project": project,
            "identity": identity}


class TakeRoad:
    """The per-take state by slot (prepare_take's), for the sub-drivers' hooks; thread-safe."""

    def __init__(self, *, prepare, remove):
        if not callable(prepare) or not callable(remove):
            raise TypeError("prepare and remove must be callable")
        self._prepare, self._remove = prepare, remove
        self._lock = threading.Lock()
        self._by_slot: dict = {}
        self.kept: list = []          # (slot, run tree) held for a human
        self.problems: list = []      # a run tree that could not be removed, and why

    def prepare(self, row) -> dict:
        return road_prepare(self, row)

    def state(self, row) -> dict:
        with self._lock:
            got = self._by_slot.get(row["slot"])
        if got is None:
            raise RunRefused(f"slot {row['slot']!r} has no prepared take")
        return got

    def discard(self, slot) -> None:
        road_release(self, slot, keep=False)

    def keep(self, slot) -> None:
        road_release(self, slot, keep=True)


def road_prepare(road: TakeRoad, row) -> dict:
    """One prepared take per slot at a time: a second prepare of a live slot refuses before anything is built."""
    slot = row["slot"]
    with road._lock:
        if slot in road._by_slot:
            raise RunRefused(f"slot {slot!r} already has a prepared take ({road._by_slot[slot]['tree']})")
    state = road._prepare(row)
    with road._lock:
        road._by_slot[slot] = state
    return state


def road_release(road: TakeRoad, slot, *, keep: bool) -> None:
    """The slot's take leaves the road: its run tree kept for a human (named in road.kept) or removed (a removal that
    fails is named in road.problems)."""
    with road._lock:
        state = road._by_slot.pop(slot, None)
    if state is None:
        return
    if keep:
        road.kept.append((slot, str(state["tree"])))
        return
    why = road._remove(state["tree"])
    if why:
        road.problems.append(f"slot {slot!r}: {why}")


class LeasePool:
    """The Codex lease road for concurrent takes: one CodexLeaseRoad per take, by slot (lease_place, lease_login,
    lease_secrets_union)."""

    def __init__(self, lease_src, *, uid_map, clock, walk_s_for, road_class=None):
        import walk_builders as wb
        if not callable(walk_s_for):
            raise TypeError("walk_s_for must be callable (row) -> the take's budget in seconds")
        self.road_class = wb.CodexLeaseRoad if road_class is None else road_class
        self.lease_src, self.uid_map, self.clock, self.walk_s_for = lease_src, uid_map, clock, walk_s_for
        self._lock = threading.Lock()
        self._by_slot: dict = {}

    def place(self, row, config_dir) -> str:
        return lease_place(self, row, config_dir)

    def login_file_for(self, take):
        return lease_login(self, take)

    def secrets(self) -> list:
        return lease_secrets_union(self)


def lease_place(pool: LeasePool, row, config_dir) -> str:
    """A new CodexLeaseRoad for the take, its budget the take's own, placed into its config folder (its freshness
    check and the gate are CodexLeaseRoad.place's)."""
    road = pool.road_class(pool.lease_src, uid_map=pool.uid_map, clock=pool.clock)
    road.walk_s = pool.walk_s_for(row)
    path = road.place(config_dir)
    with pool._lock:
        pool._by_slot[row["slot"]] = road
    return path


def lease_login(pool: LeasePool, take):
    """The take's own placement, by its row's slot; a take with none placed refuses."""
    with pool._lock:
        road = pool._by_slot.get(take.row["slot"])
    if road is None:
        raise RunRefused(f"no lease is placed for slot {take.row['slot']!r}")
    return road.login_file_for(take)


def lease_secrets_union(pool: LeasePool) -> list:
    """Every placed lease's secrets, each pair once, read now."""
    with pool._lock:
        roads = list(pool._by_slot.values())
    out = []
    for road in roads:
        for pair in road.secrets():
            if pair not in out:
                out.append(pair)
    return out


class RunDriver:
    """batch's driver over one sub-driver per harness (THE DRIVER contract: launch, drive, remove), plus the repo's
    record_files and on_published hooks (run_launch, run_published, run_sub)."""

    def __init__(self, *, drivers: dict, road: TakeRoad, precheck, history=None):
        if not isinstance(drivers, dict) or not drivers:
            raise TypeError("drivers is a non-empty {harness: driver} map")
        if not callable(precheck):
            raise TypeError("precheck must be callable (driver, row)")
        self.drivers, self.road, self.precheck, self.history = drivers, road, precheck, history
        self._lock = threading.Lock()
        self._by_cid: dict = {}

    def launch(self, row) -> str:
        return run_launch(self, row)

    def drive(self, row, container_id) -> dict:
        return run_of(self, container_id).drive(row, container_id)

    def remove(self, container_id) -> None:
        run_of(self, container_id).remove(container_id)

    def record_files(self, row, attempt) -> list:
        return run_sub(self, row).record_files(row, attempt)

    def published(self, row, attempt) -> None:
        run_published(self, row, attempt)


def run_sub(rd: RunDriver, row):
    """The row's harness's sub-driver; a harness this run has none for refuses."""
    harness = (row.get("agent") or {}).get("harness")
    if harness not in rd.drivers:
        raise RunRefused(f"slot {row.get('slot')!r}: harness {harness!r} has no driver in this run ({sorted(rd.drivers)})")
    return rd.drivers[harness]


def run_of(rd: RunDriver, container_id):
    """The sub-driver that launched the container."""
    with rd._lock:
        sub = rd._by_cid.get(container_id)
    if sub is None:
        raise RunRefused(f"container {container_id!r} was not launched by this run")
    return sub


def run_launch(rd: RunDriver, row) -> str:
    """The records check first (nothing built for a take that does not match its records), then the take prepared,
    then the sub-driver's launch. A launch that leaves no container removes the take's run tree; one that leaves a
    container records it (batch removes it, and the take's commit decides the tree)."""
    sub = run_sub(rd, row)
    rd.precheck(sub, row)
    rd.road.prepare(row)
    try:
        cid = sub.launch(row)
    except BaseException as e:
        left = getattr(e, "container_id", None)
        if left:
            with rd._lock:
                rd._by_cid[left] = sub
        else:
            rd.road.discard(row["slot"])
        raise
    with rd._lock:
        rd._by_cid[cid] = sub
    return cid


def run_published(rd: RunDriver, row, attempt) -> None:
    """The sub-driver's own publish step, then the take's run tree: kept for a human when its committed outcome needs
    a ruling (batch.needs_ruling), else removed."""
    import batch
    try:
        run_sub(rd, row).published(row, attempt)
    finally:
        mine = [o for o in (rd.history() if callable(rd.history) else [])
                if batch.is_outcome(o) and (o.get("slot"), o.get("attempt")) == (row["slot"], attempt)]
        if mine and batch.needs_ruling(mine[-1]):
            rd.road.keep(row["slot"])
        else:
            rd.road.discard(row["slot"])


def union_secrets(*sources):
    """One secrets() over several: every pair of each, once, in order, read at call time."""
    def secrets():
        out = []
        for source in sources:
            for pair in source():
                if pair not in out:
                    out.append(pair)
        return out
    return secrets


def harness_driver(builders: dict, harness: str, road: TakeRoad, rules, root):
    """(drive.walk_driver(records="takes") for one harness, that harness's secrets()) from the builder set, every
    per-take value read from the road."""
    import drive
    import walk_builders as wb
    from box import run_take as rt
    lock_path = wb.for_row(builders["lock_path"], harness)
    proxy = wb.for_row(builders["proxy"], harness)

    def tree(r):
        return str(road.state(r)["tree"])
    if harness == rt.CODEX:
        gate = wb.codex_gate_problem()
        if gate:
            raise RunRefused(f"harness {harness!r}: {gate}")
        lease = builders.get("lease_path")
        if not isinstance(lease, str) or not os.path.isabs(lease):
            why = lease.why if isinstance(lease, wb.Missing) else f"not an absolute path: {lease!r}"
            raise RunRefused(f"harness {harness!r}: the Codex lease source is missing: {why}")
        pool = LeasePool(lease, uid_map=builders["uid_map"], clock=builders["clock"],
                         walk_s_for=lambda r: wb.walk_budget_s(builders["design_for"](r, None).script,
                                                               builders["budgets"]))
        login, secrets = pool.login_file_for, pool.secrets

        def spec_for(r, cfg):
            wb.vendor_config(r, cfg, tree(r))
            pool.place(r, cfg)
            return builders["take_spec"](r, cfg, tree(r))
    elif harness in (rt.GEMINI, rt.CLAUDE_CODE):
        path = builders.get("gemini_login_path" if harness == rt.GEMINI else "login_path")
        if isinstance(path, wb.Missing):
            raise RunRefused(f"harness {harness!r}: its login file is missing: {path.why}")
        login = wb.login_file_by_name(path, harness)
        secrets = wb.login_secrets(login, harness)

        def spec_for(r, cfg):
            wb.vendor_config(r, cfg, tree(r))
            return builders["take_spec"](r, cfg, tree(r))
    else:
        raise RunRefused(f"harness {harness!r}: the run admits Claude Code, Codex and Gemini")
    budget_s, finalize_wait_s, poll_s = builders["budgets"]
    driver = drive.walk_driver(
        runtime=builders["runtime"], root=str(root), config_parent=builders["config_parent"], spec_for=spec_for,
        sidecar_for=lambda r, ev: builders["sidecar_for"](r, ev, tree(r), road.state(r)["project"]), proxy=proxy,
        lock_path=lock_path, hosts=builders["hosts"], login_file=login,
        counters_for=wb.counters_reader(builders["cgroup_dir_for"]), pin_for=builders["pin_for"],
        design_for=builders["design_for"], project_for=lambda r: road.state(r)["project"],
        identity_for=lambda r: dict(road.state(r)["identity"]), secrets=secrets, rules_scanner=rules,
        uid_map=builders["uid_map"], budget_s=budget_s, finalize_wait_s=finalize_wait_s, poll_s=poll_s,
        clock=builders["clock"], sleep=builders["sleep"], records="takes", ownership=builders["ownership"],
        settings_guard=builders["settings_guard"], machine_gate=builders["machine_gate"])
    return driver, secrets


def build_run(*, pre, go, arms=None, limit=None, account=RUN_ACCOUNT, builders=None, root=None, repo=None,
              real=None) -> dict:
    """{driver, repo, window, ledger, rows, arms, harnesses, road, table} for batch.Batch, or RunRefused naming every
    value that is missing before anything is built. `account` is the Claude Code login's (ruling 4; the rehearsal's
    walk account under ruling 8)."""
    import drive
    import routing
    import takes
    import time
    import walk_builders as wb
    root = Path(root if root is not None else HERE).resolve()
    repo = Path(repo if repo is not None else drive.REPO).resolve()
    real = builders is None if real is None else real
    builders = wb.production_builders() if builders is None else dict(builders)
    deferral = ruled_deferral_problem(pre, go)
    if deferral:
        raise RunRefused(deferral)
    builders["login_path"] = run_login_path(account)
    gaps = wb.missing(builders)
    if gaps:
        raise RunRefused("; ".join(f"missing {n}: {why}" for n, why in gaps))
    history = takes.read_history(root=root, repo=repo)
    rows = run_rows(pre, history, go=go, arms=arms, limit=limit)
    chosen = tuple(a for a in run_arms(pre, go) if arms is None or a in arms)
    harnesses = sorted({r["agent"]["harness"] for r in pre["rows"] if r["arm"] in chosen})
    rules = wb.walk_rules_scanner(builders["rules_scanner"], builders["runtime"], builders["config_parent"], real=real)
    origin, exclude = builders["run_tree_origin"], builders["run_tree_exclude"]
    road = TakeRoad(prepare=lambda r: prepare_take(r, root=root, repo=repo, origin=origin, exclude=exclude),
                    remove=wb.remove_run_tree)            # m13: the tree exported is read per take, never the constant
    subs, sources = {}, []
    for harness in harnesses:
        subs[harness], secrets = harness_driver(builders, harness, road, rules, root)
        sources.append(secrets)
    driver = RunDriver(drivers=subs, road=road, precheck=drive.launch_problems)
    take_repo = drive.TakeRepo(runtime=builders["runtime"], record_files=driver.record_files,
                               secrets=union_secrets(*sources), rules_scanner=rules, root=root, repo=repo,
                               on_published=driver.published)
    driver.history = take_repo.history
    window = UsageWindow(root=root, repo=repo, history=take_repo.history,
                         rows=lambda: takes.load_rows(root=root, repo=repo), clock=time.time, sleep=time.sleep)
    money = any(h not in routing.NO_MONEY_HARNESSES for h in harnesses)
    ledger = SpendLedger(root=root, repo=repo, pre=pre, history=take_repo.history, arms=chosen) if money else None
    return {"driver": driver, "repo": take_repo, "window": window, "ledger": ledger, "rows": rows, "arms": chosen,
            "harnesses": harnesses, "road": road, "table": builders["table"]}


# =====================================================================================================================
# STAGE S3, THE WIRING (glitch-f1's rulings 1A and 2 on S3, 22 Oct 2026; Part T's contract lines 3, 4 and 6).
#   go_reader   ruling 1A: lane gemini-defer's R5 reader under its real name, one reader for Batch and the launcher:
#               go(arm) is True when prereg.deferred_arm_go(arm, prereg.committed_go_records(root)), else None.
#   run_main    batch.py --run's body (batch.main keeps the nohup rule before it): the frozen pre-registration, build_run,
#               batch.Batch(..., ledger=...).run(rows), never history=; one JSON summary line on stdout. Exit 0 when the
#               queue drained, 1 when the loop stopped or refused its rows, 2 when refused before anything was built.
#   run_summary the summary's closed fields: the state counts, the stop (a spend-cap stop reads "spend event", never a
#               window; CP2-requirements' spend-cap section), the arms, the rows handed, the run tree kept for a human,
#               and ruling 6's computed spend reads.
#   main        `run_builders.py spend-read`, `trimmed` (Part T line 4) and `night-ruling` (line 3): one commit each.
# =====================================================================================================================
SPEND_CAP_ROW = "spend-cap-reached"     # routing.json's spend_cap_refusal id
STUDY_ROOT = [HERE]                     # the study folder main() writes in (one element, read at call time)


def go_reader(root=None):
    """Ruling 1A: the go-record reader run_arms takes, over R5's prereg functions (read at call time, at HEAD)."""
    def go(arm):
        import prereg
        return True if prereg.deferred_arm_go(arm, prereg.committed_go_records(root)) else None
    return go


def run_summary(outcomes: list, stopped, built: dict, computed=()) -> dict:
    """The run's closed summary (no take's words beyond the loop's own stop reason)."""
    counts: dict = {}
    for o in outcomes:
        counts[o["state"]] = counts.get(o["state"], 0) + 1
    stop = None
    if stopped is not None:
        reason = str(stopped.get("reason"))
        stop = dict(stopped, kind="spend event" if SPEND_CAP_ROW in reason else "stop")
    return {"counts": counts, "stopped": stop, "arms": list(built["arms"]), "rows": len(built["rows"]),
            "kept_run_trees": list(built["road"].kept), "run_tree_problems": list(built["road"].problems),
            "computed_spend_reads": list(computed)}


def run_main(*, arms=None, limit=None, serial=False, account=RUN_ACCOUNT, root=None, repo=None, builders=None) -> int:
    """batch.py --run (see the S3 header)."""
    import batch
    import drive
    import prereg
    root = Path(root if root is not None else HERE).resolve()
    repo = Path(repo if repo is not None else drive.REPO).resolve()
    try:
        pre = prereg.require_frozen("running the counted takes")
    except SystemExit as e:
        print(f"batch: refused: {e}", file=sys.stderr)
        return 2
    narrowed = None if arms is None else [a.strip() for a in str(arms).split(",")]
    try:
        built = build_run(pre=pre, go=go_reader(root), arms=narrowed, limit=limit, account=account,
                          builders=builders, root=root, repo=repo)
        computed = computed_reads(read_ledger_doc(root, repo)) if built["ledger"] is not None else []
    except Exception as e:  # noqa: BLE001 - every refusal before the loop is named, nothing is built past it
        print(f"batch: refused: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    try:
        loop = batch.Batch(built["driver"], built["repo"], built["window"], table=built["table"], serial=serial,
                           ledger=built["ledger"])
        got = loop.run(built["rows"])
    except batch.BatchConfigError as e:
        print(f"batch: refused: {e}", file=sys.stderr)
        print(json.dumps(run_summary([], {"reason": str(e)}, built, computed), sort_keys=True, default=str))
        return 1
    print(json.dumps(run_summary(got, loop.stopped, built, computed), sort_keys=True, default=str))
    return 0 if loop.stopped is None else 1


def parse_figures(pairs) -> dict:
    """--figure vendor=amount, once per capped vendor."""
    out = {}
    for pair in pairs or []:
        vendor, sep, value = str(pair).partition("=")
        if not sep or not vendor or vendor in out:
            raise LedgerRefused(f"--figure {pair!r} is not one vendor=amount (each vendor once)")
        out[vendor] = value
    return out


def main(argv=None) -> int:
    import argparse
    import takes
    ap = argparse.ArgumentParser(prog="run_builders.py", description="The counted run's record writers.")
    sub = ap.add_subparsers(dest="verb", required=True)
    s = sub.add_parser("spend-read", help="record one vendor spend read (one commit): the spend since the previous "
                                          "read (an increment), never a running total; reads are summed")
    for k in ("vendor", "usd", "at", "source", "by"):
        s.add_argument(f"--{k}", required=True)
    t = sub.add_parser("trimmed", help="record Javier's caps trimmed (one commit)")
    for k in ("month", "at", "by"):
        t.add_argument(f"--{k}", required=True)
    t.add_argument("--figure", action="append", required=True, help="vendor=amount, once per capped vendor")
    n = sub.add_parser("night-ruling", help="commit the night ruling that resolves a nightly stop (one commit)")
    n.add_argument("--slot", required=True)
    n.add_argument("--attempt", type=int, required=True)
    n.add_argument("--by", required=True)
    for verb, why in (("rehearse", "the rehearsal take (B19-16): a throwaway frozen clone under --out, two takes"),
                      ("rehearse-takes", "the rehearsal's takes, run inside its frozen clone by `rehearse`")):
        sub.add_parser(verb, help=why).add_argument("--out", required=True)
    args = ap.parse_args(argv)
    if args.verb in ("rehearse", "rehearse-takes"):
        try:
            return rehearse(Path(args.out)) if args.verb == "rehearse" else rehearse_takes(Path(args.out))
        except RunRefused as e:
            print(f"run_builders: refused: {e}", file=sys.stderr)
            return 1
        except Exception as e:  # noqa: BLE001 - closure MINOR-1: summary.json always exists for the take step
            print(f"run_builders: refused: {type(e).__name__}", file=sys.stderr)
            if args.verb == "rehearse-takes" and Path(args.out).is_dir():
                write_summary(Path(args.out), rehearsal_summary([], {}, {}, refused="batch-config"))
            elif args.verb == "rehearse" and rehearse_out_writable(Path(args.out)):
                write_summary(Path(args.out), rehearsal_summary([], {}, {}, refused="freeze-failed"))
            return 1
    root = Path(STUDY_ROOT[0]).resolve()      # read at call time (a test points it at a scratch repository)
    try:
        repo = _repo_of(root)
        if args.verb == "spend-read":
            got = append_spend({k: getattr(args, k) for k in SPEND_KEYS}, root=root, repo=repo)
        elif args.verb == "trimmed":
            got = append_trim({"kind": "caps trimmed", "by": args.by, "month": args.month, "at": args.at,
                               "figures": parse_figures(args.figure)}, root=root, repo=repo)
        else:
            takes.commit_night_ruling(slot=args.slot, attempt=args.attempt, by=args.by, root=root, repo=repo)
            got = _git(repo, "rev-parse", "HEAD").strip()
    except (LedgerRefused, RunRefused, ValueError, KeyError, OSError) as e:
        print(f"run_builders: refused: {e}", file=sys.stderr)
        return 1
    print(json.dumps({"verb": args.verb, "commit": got}))
    return 0


# =====================================================================================================================
# STAGE S4, THE REHEARSAL TAKE (B19-16; glitch-f1's ruling 8 as amended on S3, 22 Oct 2026; Part T contract line 2).
#   rehearse        `run_builders.py rehearse --out <dir>`, on athena in a Part T child, solo, after Part S's battery and
#                   before prefreeze-precheck. Everything stays under <dir>: the throwaway clone (<dir>/clone, git clone
#                   --no-local of HEAD, its remote removed), the synthetic holdout digests freeze_rehearsal makes, and
#                   summary.json. It never writes the shipped repository: <dir> must lie outside it, and the source must
#                   be committed and clean. The clone is frozen with freeze_rehearsal's own command (freeze.py --rehearsal
#                   --write, imported, never edited) and committed; then the clone's own writer records two zero spend
#                   reads (google and openai, --usd 0, source REHEARSAL_SPEND_SOURCE, by "rehearsal"; one commit each,
#                   in the clone only, so the money gate can read a ledger; MAJOR-1 of the review of 122b559e; a
#                   failed read is freeze-failed like every other clone step); then the clone's own run_builders.py
#                   rehearse-takes runs the takes there, so every module read is the clone's. The take step has no
#                   freeze_rehearsal one-hour timeout: it is bounded by the two rehearsal rows' walk budgets plus the
#                   quiescence cap once (takes_budget_s), and on expiry the summary is refused:takes-timeout (MINOR-4).
#   rehearse_takes  the first arm A row and the first arm O row of the clone's frozen take_order (both bill no money: A on
#                   the claude1 walk login, never the run token; O on the Codex subscription with one lease from
#                   LeasePool), in their frozen relative order, through build_run's road and batch.Batch's rolling
#                   window, timed by TimedDriver. A Codex lease that is not live never fails as a take (Part T's
#                   closure): the arm A take runs alone, and the arm O take is written refused with the one reason
#                   "codex lease not live" (exit 3 once the A take is committed under a route; a blocked or failed A
#                   take exits 1): Javier's fresh Codex login. A loop
#                   that stops with no take is one closed refusal: refused:money-gate when batch's money gate stopped
#                   it, else refused:loop-stopped; an error from the loop itself (a BatchConfigError at construction,
#                   or any error from its run) is refused:batch-config, so summary.json always exists (an unexpected
#                   error inside `rehearse` is refused:freeze-failed, written by main into an absolute, existing --out
#                   outside the source repository). Every run tree
#                   the road kept for a human is removed at the end (the rehearsal's records are discarded): counts
#                   carries kept_removed, a closed integer, and a tree that cannot be removed makes the summary
#                   refused:run-tree-left (MINOR-3).
#   summary.json    exactly the contract's keys: takes (each exactly {arm, state, route, commit, launched_at,
#                   drive_started_at, drive_ended_at}, plus `reason` only on the lease refusal, only "codex lease not
#                   live"), overlap (two takes' drive intervals intersect), pass (two takes, A and O, both committed under
#                   a route, never blocked or failed, and overlap), counts (takes by route; a refusal is its one closed
#                   entry "refused:<reason>"). No other reason, transcript or wording text.
# =====================================================================================================================
REHEARSAL_REFUSALS = ("out-not-empty", "out-inside-source", "source-not-clean", "no-pre-freeze-review",
                      "freeze-failed", "builders-missing", "rows-missing", "codex-lease-not-live", "money-gate",
                      "loop-stopped", "run-tree-left", "takes-timeout", "batch-config")
REHEARSAL_SPEND_VENDORS = ("google", "openai")
REHEARSAL_SPEND_SOURCE = "rehearsal clone, not a vendor read"
REHEARSAL_SPEND_BY = "rehearsal"
MONEY_GATE_STOP = "the money gate refuses the block"     # batch.Batch._money_gate's stop reason opens with it
REHEARSAL_TAKE_KEYS = ("arm", "state", "route", "commit", "launched_at", "drive_started_at", "drive_ended_at")
LEASE_REASON = "codex lease not live"      # Part T's contract: the one reason a take entry may carry
SUMMARY_KEYS = ("takes", "overlap", "pass", "counts")
LEASE_REFUSED_EXIT = 3


class RehearsalRefused(RuntimeError):
    """The rehearsal does not run; `reason` is one of REHEARSAL_REFUSALS."""

    def __init__(self, reason: str, detail: str = ""):
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason


def rehearsal_rows(rows: list) -> list:
    """The first arm A row and the first arm O row, in their frozen relative order (ruling 8 as amended)."""
    first = {}
    for r in rows:
        if r["arm"] in ("A", "O") and r["arm"] not in first:
            first[r["arm"]] = r
    if set(first) != {"A", "O"}:
        raise RehearsalRefused("rows-missing", f"the frozen order holds arms {sorted(first)} of A and O")
    return [r for r in rows if r is first["A"] or r is first["O"]]


def overlap_of(times: dict) -> bool:
    """True when two takes' drives ran at once: their drive intervals (drive_started_at to drive_ended_at) intersect
    (glitch-f1's ruling 2 on the fold of the review of 122b559e: never launch-during-drive, since batch.Batch launches
    a whole wave before its drives start). Intervals that only touch, and an undriven take, never overlap."""
    spans = [(t["drive_started_at"], t["drive_ended_at"]) for t in times.values()
             if t.get("drive_started_at") is not None and t.get("drive_ended_at") is not None]
    return any(a0 < b1 and b0 < a1 for i, (a0, a1) in enumerate(spans) for b0, b1 in spans[i + 1:])


class TimedDriver:
    """The run driver with each take's launch and drive times recorded (the injected clock), by slot."""

    def __init__(self, inner, clock):
        self.inner, self.clock, self.times = inner, clock, {}
        self._lock = threading.Lock()

    def launch(self, row):
        return timed_launch(self, row)

    def drive(self, row, container_id):
        return timed_drive(self, row, container_id)

    def remove(self, container_id):
        return self.inner.remove(container_id)


def timed_launch(td: TimedDriver, row):
    with td._lock:
        td.times[row["slot"]] = {"launched_at": td.clock(), "drive_started_at": None, "drive_ended_at": None}
    return td.inner.launch(row)


def timed_drive(td: TimedDriver, row, container_id):
    with td._lock:
        td.times[row["slot"]]["drive_started_at"] = td.clock()
    try:
        return td.inner.drive(row, container_id)
    finally:
        with td._lock:
            td.times[row["slot"]]["drive_ended_at"] = td.clock()


def outcome_commits(root, repo) -> dict:
    """{(slot, attempt): the commit that appended its outcome to outcomes.json}."""
    import takes
    root, repo = Path(root).resolve(), Path(repo).resolve()
    rel = (root / takes.HISTORY_FILES[0]).relative_to(repo).as_posix()
    out, seen = {}, 0
    for sha in _git(repo, "log", "--reverse", "--format=%H", "--", rel).split():
        doc = json.loads(_git(repo, "show", f"{sha}:{rel}"))
        for o in doc[seen:]:
            out[(o["slot"], o["attempt"])] = sha
        seen = len(doc)
    return out


def _iso(t):
    return None if t is None else datetime.datetime.fromtimestamp(t, datetime.timezone.utc).isoformat()


def rehearsal_summary(outcomes: list, times: dict, commits: dict, refused=None, arms=None, lease_refused=False) -> dict:
    """summary.json: exactly SUMMARY_KEYS, each take exactly REHEARSAL_TAKE_KEYS (plus `reason` on the lease refusal
    alone), closed values only. arms: {slot: arm}. lease_refused: the arm O take was not run, its lease not live."""
    from graders import labels4
    if refused is not None:
        if refused not in REHEARSAL_REFUSALS:
            raise RunRefused(f"{refused!r} is not a closed rehearsal refusal")
        return {"takes": [], "overlap": False, "pass": False, "counts": {f"refused:{refused}": 1}}
    arms = arms or {}
    takes_, counts = [], {}
    for o in outcomes:
        t = times.get(o["slot"], {})
        commit = commits.get((o["slot"], o["attempt"]))
        if arms.get(o["slot"]) not in ("A", "O"):
            raise RunRefused(f"slot {o['slot']!r} has no rehearsal arm (A or O)")
        takes_.append({"arm": arms[o["slot"]], "state": "committed" if commit else "not committed",
                       "route": o["state"], "commit": commit,
                       "launched_at": _iso(t.get("launched_at")), "drive_started_at": _iso(t.get("drive_started_at")),
                       "drive_ended_at": _iso(t.get("drive_ended_at"))})
        counts[o["state"]] = counts.get(o["state"], 0) + 1
    if lease_refused:
        takes_.append({"arm": "O", "state": "refused", "reason": LEASE_REASON, "route": None, "commit": None,
                       "launched_at": None, "drive_started_at": None, "drive_ended_at": None})
        counts["refused:codex-lease-not-live"] = 1
    overlap = overlap_of(times)
    good = [t for t in takes_ if t["state"] == "committed" and t["route"] in labels4.ROUTES]
    return {"takes": takes_, "overlap": overlap, "pass": len(takes_) == 2 and len(good) == 2 and overlap,
            "counts": counts}


def write_summary(out, summary: dict) -> Path:
    path = Path(out) / "summary.json"
    path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def lease_problem(builders: dict, rows: list):
    """None when the Codex lease is live for the rehearsal's O row (the box's gate open, its freshness against that
    take's budget), else the closed reason codex-lease-not-live."""
    import walk_builders as wb
    for r in rows:
        if r["agent"]["harness"] != "codex":
            continue
        try:
            gate = wb.codex_gate_problem()
            lease = builders.get("lease_path")
            if gate or not isinstance(lease, str):
                return "codex-lease-not-live"
            walk_s = wb.walk_budget_s(builders["design_for"](r, None).script, builders["budgets"])
            if wb.lease_freshness_problem(lease, now=builders["clock"](), walk_s=walk_s):
                return "codex-lease-not-live"
        except Exception:  # noqa: BLE001 - a lease that cannot be read is not live
            return "codex-lease-not-live"
    return None


def rehearse_takes(out, *, builders=None, root=None, repo=None, clock=None, batch_class=None) -> int:
    """The two rehearsal takes in the frozen clone this module was imported from (see the S4 header)."""
    import batch
    import drive
    import prereg
    import time
    import walk_builders as wb
    root = Path(root if root is not None else HERE).resolve()
    repo = Path(repo if repo is not None else drive.REPO).resolve()
    clock = time.time if clock is None else clock
    batch_class = batch.Batch if batch_class is None else batch_class
    real = builders is None
    builders = wb.production_builders() if builders is None else builders
    try:
        pre = prereg.require_frozen("rehearsing the counted take road")
        built = build_run(pre=pre, go=go_reader(root), arms=["A", "O"], account=REHEARSAL_ACCOUNT, builders=builders,
                          root=root, repo=repo, real=real)
        rows = rehearsal_rows(built["rows"])
    except RehearsalRefused as e:
        write_summary(out, rehearsal_summary([], {}, {}, refused=e.reason))
        return 1
    except (SystemExit, Exception):  # noqa: BLE001 - its words are not written: a closed reason only
        write_summary(out, rehearsal_summary([], {}, {}, refused="builders-missing"))
        return 1
    lease_dead = lease_problem(builders, rows) is not None
    if lease_dead:                                  # the A take alone; the O take is written refused, never run
        rows = [r for r in rows if r["arm"] == "A"]
    timed = TimedDriver(built["driver"], clock)
    try:
        loop = batch_class(timed, built["repo"], built["window"], table=built["table"], ledger=built["ledger"])
        got = loop.run(rows)
    except Exception:  # noqa: BLE001 - closure MINOR-1: a BatchConfigError or any loop error is one closed reason
        remove_kept(built["road"])
        write_summary(out, rehearsal_summary([], {}, {}, refused="batch-config"))
        return 1
    removed, left = remove_kept(built["road"])
    if left:
        write_summary(out, rehearsal_summary([], {}, {}, refused="run-tree-left"))
        return 1
    stopped = getattr(loop, "stopped", None)
    if not got and stopped is not None:
        why = "money-gate" if str(stopped.get("reason", "")).startswith(MONEY_GATE_STOP) else "loop-stopped"
        write_summary(out, rehearsal_summary([], {}, {}, refused=why))
        return 1
    summary = rehearsal_summary(got, timed.times, outcome_commits(root, repo), arms={r["slot"]: r["arm"] for r in rows},
                                lease_refused=lease_dead)
    summary["counts"]["kept_removed"] = removed
    write_summary(out, summary)
    if lease_dead:
        from graders import labels4
        a_done = any(t["arm"] == "A" and t["state"] == "committed" and t["route"] in labels4.ROUTES
                     for t in summary["takes"])        # closure NIT-1: a blocked or failed A take is not done
        return LEASE_REFUSED_EXIT if a_done else 1
    return 0 if summary["pass"] else 1


def remove_kept(road: TakeRoad) -> tuple:
    """MINOR-3: every run tree the road kept for a human, removed with the road's own remover (the rehearsal's records
    are discarded, so nothing is left outside <dir>). (how many were removed, [why a tree is left]): a tree whose
    removal failed during the run (road.problems) is left too."""
    with road._lock:
        kept, road.kept = list(road.kept), []
    removed, left = 0, list(road.problems)
    for slot, tree in kept:
        why = road._remove(tree)
        if why:
            left.append(f"slot {slot!r}: {why}")
        else:
            removed += 1
    return removed, left


def takes_budget_s(rows: list, budgets, script_for) -> int:
    """MINOR-4: the rehearsal take step's bound: each row's walk budget (walk_builders.walk_budget_s over its script)
    plus the quiescence cap once for the last finalize."""
    import walk_builders as wb
    return sum(wb.walk_budget_s(script_for(r), budgets) for r in rows) + int(budgets[1])


def rehearsal_budget_s(clone: Path) -> int:
    """takes_budget_s for the frozen clone's two rehearsal rows: its prereg.json's take_order, its own task scripts, and
    the checker's budgets. A budget that cannot be read is RehearsalRefused builders-missing."""
    import study
    import variants
    import walk_builders as wb
    folder = Path(clone) / study.STUDY_REL
    pre = json.loads((folder / "prereg.json").read_text(encoding="utf-8"))
    rows = rehearsal_rows(pre["take_order"])
    budgets = wb.checker_budgets()
    if isinstance(budgets, wb.Missing):
        raise RehearsalRefused("builders-missing", budgets.why)
    return takes_budget_s(rows, budgets, lambda r: variants.operator_steps(
        r["task"], r["half"], r["wording"], pressure=r.get("pressure"), root=folder))


def run_takes_step(argv, cwd, timeout):
    """The take step, under freeze_rehearsal's step environment, with `timeout` seconds (subprocess.TimeoutExpired
    propagates; subprocess.run has killed the child by then). (returncode, output)."""
    import freeze_rehearsal as fr
    try:
        got = subprocess.run(argv, cwd=str(cwd), capture_output=True, text=True, env=fr.step_environment(),
                             timeout=timeout)
    except OSError as e:
        return 1, str(e)
    return got.returncode, got.stdout + got.stderr


def rehearsal_source_problem(out: Path, source: Path):
    """The closed reason the rehearsal may not start from `source` into `out`, or None."""
    if os.path.lexists(out) and (not out.is_dir() or any(out.iterdir())):
        return "out-not-empty"
    if out.resolve() == source.resolve() or source.resolve() in out.resolve().parents:
        return "out-inside-source"
    if _git(source, "status", "--porcelain", "--untracked-files=all").strip():
        return "source-not-clean"
    return None


def latest_review(source: Path):
    """The latest committed pre-freeze review freeze.py admits (freeze_rehearsal's rule), or None."""
    import freeze
    import study
    got = subprocess.run(["git", "-C", str(source), "log", "-1", "--format=%H", "--",
                          study.rel(study.REVIEW_DIR, "prefreeze-*.md")], capture_output=True, text=True)
    review = got.stdout.strip()
    if got.returncode != 0 or not review:
        return None
    problems, _ = freeze.review_file_problems(review)
    return None if problems else review


def rehearse_out_writable(out: Path) -> bool:
    """Closure 2 NIT-1: main may write rehearse's closed summary into `out` only when it is an absolute, existing folder
    outside the source repository (drive.REPO)."""
    import drive
    try:
        source = Path(drive.REPO).resolve()
        where = out.resolve()
        return out.is_absolute() and out.is_dir() and where != source and source not in where.parents
    except OSError:
        return False


def rehearse(out, *, source=None, review=None, runner=None, takes_runner=None, budget_for=None, clock=None) -> int:
    """`run_builders.py rehearse --out <dir>` (see the S4 header). runner(argv, cwd) -> (returncode, output) for the
    clone's steps; takes_runner(argv, cwd, timeout) -> (returncode, output), raising subprocess.TimeoutExpired, for the
    take step; budget_for(clone) -> seconds; clock() -> the spend reads' aware time."""
    import drive
    import freeze_rehearsal as fr
    import study
    out = Path(out)
    source = Path(source if source is not None else drive.REPO).resolve()
    runner = runner if runner is not None else (lambda argv, cwd: fr.sh(argv, cwd, env=fr.step_environment()))
    takes_runner = takes_runner if takes_runner is not None else run_takes_step
    budget_for = budget_for if budget_for is not None else rehearsal_budget_s
    clock = clock if clock is not None else utc_now
    if not out.is_absolute():
        raise RunRefused("--out is an absolute path")
    why = rehearsal_source_problem(out, source)
    if why is None:
        review = review if review is not None else latest_review(source)
        why = None if review else "no-pre-freeze-review"
    if why == "out-inside-source":
        print(f"run_builders: refused: rehearsal {why}", file=sys.stderr)     # nothing is written into the source
        return 1
    out.mkdir(parents=True, exist_ok=True)
    if why is not None:
        write_summary(out, rehearsal_summary([], {}, {}, refused=why))
        return 1
    clone = out / "clone"
    steps = [["git", "clone", "-q", "--no-local", str(source), str(clone)],
             ["git", "-C", str(clone), "remote", "remove", "origin"]]
    for argv in steps:
        code, _ = runner(argv, str(out))
        if code:
            write_summary(out, rehearsal_summary([], {}, {}, refused="freeze-failed"))
            return 1
    holdout = out / fr.HOLDOUT_FILE
    fr.synthetic_holdout_source(clone / study.rel("prereg-draft.json"), holdout)
    rel = study.STUDY_REL
    freeze_argv = [sys.executable, "-B", "-W", "ignore", str(clone / rel / "freeze.py"),
                   *fr.freeze_command(review, holdout)[1:]]
    staged = [study.rel(p) for p in ("prereg.json", "COPIED.json", "COPIED.d/freeze.json")]
    for argv in (freeze_argv, ["git", "-C", str(clone), "add", "--", *staged],
                 ["git", "-C", str(clone), "-c", "user.name=rehearsal", "-c", "user.email=rehearsal@example.invalid",
                  "commit", "-q", "-m", "Rehearse the frozen state for the rehearsal take"]):
        code, _ = runner(argv, str(clone))
        if code:
            write_summary(out, rehearsal_summary([], {}, {}, refused="freeze-failed"))
            return 1
    at = _aware(clock(), "the rehearsal's clock").strftime("%Y-%m-%dT%H:%M:%SZ")
    for vendor in REHEARSAL_SPEND_VENDORS:          # MAJOR-1: the clone's own writer, one commit each, clone only
        code, _ = runner([sys.executable, "-B", "-W", "ignore", str(clone / rel / "run_builders.py"), "spend-read",
                          "--vendor", vendor, "--usd", "0", "--at", at, "--source", REHEARSAL_SPEND_SOURCE,
                          "--by", REHEARSAL_SPEND_BY], str(clone))
        if code:
            write_summary(out, rehearsal_summary([], {}, {}, refused="freeze-failed"))
            return 1
    try:
        timeout = budget_for(clone)
    except RehearsalRefused as e:
        write_summary(out, rehearsal_summary([], {}, {}, refused=e.reason))
        return 1
    except Exception:  # noqa: BLE001 - its words are not written: a closed reason only
        write_summary(out, rehearsal_summary([], {}, {}, refused="builders-missing"))
        return 1
    try:
        code, _ = takes_runner([sys.executable, "-B", "-W", "ignore", str(clone / rel / "run_builders.py"),
                                "rehearse-takes", "--out", str(out)], str(clone), timeout)
    except subprocess.TimeoutExpired:
        write_summary(out, rehearsal_summary([], {}, {}, refused="takes-timeout"))
        return 1
    return code


# ---- amendment run-amend-20261105 (OD195), placed here by its revision so no line a frozen text cites moves
def route_ruled_final(history: list) -> set:
    """The slots a route ruling makes final (Batch closes such a slot and refuses its row: amendment
    run-amend-20261105), read by final_slots. A history with no route ruling adds none, so it reads as before."""
    from graders import labels4
    if any(e.get("ruling") == labels4.RULE_ROUTE for e in history):     # only a ruling holds the key
        import takes
        return {o["slot"] for o in takes.registration_outcomes(history) if o["final"]}
    return set()


if __name__ == "__main__":
    raise SystemExit(main())
