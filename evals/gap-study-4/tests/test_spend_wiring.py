#!/usr/bin/env python3
"""Lane w7c (Gap Study round 4, wave 7; ruling W7C-gap4-1): the spend-guard wiring.

Two gaps found by the spend-marker proposal (plans/gap-study-round-4/spend-markers-proposal-2026-10-11.md, sections 3
and 5; a proposal, not in force): costs.month_turn_allowed and costs.walk_gate were written and tested, yet nothing in
batch.py called them; and routing.py accepted an empty spend-cap list for any harness. This module binds the wiring:

  G1-claude   a claude-code row (arms A and C, a subscription login) never reads the ledger nor calls either check
  G2-month    a codex or gemini row (arm O or G) is refused, nothing of its block registered or launched, while
              costs.month_turn_allowed refuses; it runs once the hold is released or outside it
  G3-walk     the same, while costs.walk_gate does not say "within round caps" (or refuses its inputs)
  G4-ledger   a paid row with no ledger is refused before anything runs; an unreadable or misshapen ledger, a clock
              the hold cannot read, or a paid harness with no arm, stops the loop, never crashes it nor lets it run
  G5-order    the gate runs per block, before the block is registered: a refused block's claude-code rows wait too
              (the frozen order is kept), and each block reads the ledger afresh
  R1-nonempty routing refuses (check_table, load_table, routing.py --check) a spend-cap list that names no marker for
              any harness but those in routing.EMPTY_SPEND_LIST_HARNESSES, claude-code alone, whose list may stay
              empty; codex's empty list was admitted from round 17 B7 (ruling M) until glitch-b5's ruling B7-F4 (18
              Oct 2026) gave codex the pinned CLI's spend texts, so it is refused again with gemini's and any other
              paid harness's
  B1-names    routing's paid harnesses are the seam's names (box/run_take.py), their arms the draft's
              (build_draft.HARNESSES), their vendors costs.CAPS's; the no-money harness is the seam's claude-code
  G6-clock    the hold reads batch's OWN clock (UTC, at check time), never the ledger's `now` (glitch-1b, Q-w7c-1): a
              ledger saying "before the hold" while the clock is inside it is refused, and the converse runs
  P3-ruled    (lane w8c, ruling W8C-gap4-1; was P3-pending) spend_cap_markers_status reads RULED: since round 17 B7
              (moved by glitch-b5's ruling M, 18 Oct 2026) it is glitch-b5's RULED 18 Oct 2026 line, which quotes
              Javier's RULED 12 Oct line ("spend markers: 1A 2A 3A") word for word; since CP5 (Javier, "CP5: all as
              recommended", 14 Oct 2026) pin_profiles_status reads RULED too, and the pin-profile and spend-cap
              harnesses are exactly claude-code, codex and gemini (arm A's profiles, then R4's O and G), so
              batch.py --check is ready (exit 0) and the Batch loop starts; the spend-status gate stays armed (a
              PENDING spend status gives its one line, and the base's table, pins and statuses PENDING, still gives
              the base's three lines)

R1-nonempty also holds after the ruling (lane w8c): on routing.json as it now stands, status RULED, an OpenAI (codex)
or Google (gemini) entry with an empty spend-cap list is still refused (codex again since B7-F4), and the same entry
with one marker is sound.

Each check is a function returning problems, each line prefixed by its clause (or ERROR when the check itself raised).
Every witness (WITNESSES) edits batch.py or routing.py in memory and must be killed by its bound check's own line, the
bound check green on the tree first, with no ERROR line (rule B). Fakes only: no model, vendor, network, API, Docker,
credential or holdout; the ledger, driver, repo and window are in-memory doubles.
"""

from __future__ import annotations

import copy
import io
import json
import os
import sys
import tempfile
import types
import unittest
from datetime import datetime, timezone
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

sys.dont_write_bytecode = True
_PATH_BEFORE = list(sys.path)
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TESTS = os.path.dirname(os.path.abspath(__file__))
for _p in (_ROOT, _TESTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import batch  # noqa: E402
import build_draft  # noqa: E402  (the draft's arm -> harness table, read only)
import costs  # noqa: E402
import harness_bookkeeping as hb  # noqa: E402
import routing  # noqa: E402
import test_batch as tb  # noqa: E402  (its World, FakeRepo, FakeWindow and test table)
from box import run_take as rt  # noqa: E402  (the seam's harness names, never typed here)
from graders import labels4  # noqa: E402

CODEX, GEMINI, CLAUDE = rt.CODEX, rt.GEMINI, hb.CLAUDE_CODE
ARM_OF = {h: a for a, h in build_draft.HARNESSES.items()}          # the draft's arm of each harness
PAID = (CODEX, GEMINI)
MODEL = {CLAUDE: tb.PIN["model"], CODEX: "test-gpt", GEMINI: "test-gemini", "fake-paid": "test-fake-paid"}

# The month turn and the round's start, as costs reads them (aware UTC strings).
START = "2026-10-01T00:00:00Z"
IN_HOLD = "2026-10-31T23:45:00Z"          # after 23:30 UTC on October's last day
OUT_OF_HOLD = "2026-10-15T12:00:00Z"
TRIMMED = {"kind": "caps trimmed", "by": "Javier", "month": "2026-11", "at": "2026-10-31T23:40:00Z",
           "figures": {"openai": "150", "google": "100"}}     # each at or under its cap (OpenAI 180 since OD107)

# The three lines batch.py --check printed at 82cf6ae9 (lane w7c's base), in order: what the spend-status gate still
# gives on routing.json with its spend status set back to the base's PENDING wording (P3-ruled).
BASE_START_PROBLEMS = [
    "pin_profiles is empty in routing.json (CP5 pre-registers them)",
    "pin_profiles_status is not ruled in routing.json (RULED or FILLED, with no PENDING)",
    "spend_cap_markers_status is not ruled in routing.json (RULED or FILLED, with no PENDING): a spend cap stops for "
    "a human ruling",
]
# Lane w8c: after Javier's "spend markers: 1A 2A 3A", the two pin-profile lines were left; CP5 (Javier, 14 Oct 2026)
# cleared them, so a PENDING spend status alone gives the last line.
SPEND_ONLY_PROBLEMS = BASE_START_PROBLEMS[2:]
CP5_STATUS = ("RULED 14 Oct by Javier (\"CP5: all as recommended\"): arm A profiles registered; O and G follow when "
              "their rate-limit and spend-cap rules are set")
BASE_SPEND_STATUS = ("PENDING (glitch-f3): claude-code's spend-cap types. Its list is empty (see "
                     "spend_cap_markers.claude-code.source) until glitch-f3 rules it.")
# Round 17 B7 (glitch-b5's ruling M, 18 Oct 2026): the spend status is glitch-b5's RULED 18 Oct line, which must quote
# Javier's RULED 12 Oct line, typed here once as it stood at 6d1b69db, word for word.
B7_SPEND_PREFIX = "RULED 18 Oct 2026 by glitch-b5 under the owner's delegation"
OWNER_SPEND_STATUS = (
    "RULED 2026-10-12 by Javier (\"spend markers: 1A 2A 3A\", typed Mon 12 Oct 2026 08:52 EDT in glitch-1b's window, "
    "on plans/gap-study-round-4/spend-markers-proposal-2026-10-11.md): claude-code's spend-cap list is empty on "
    "purpose; arm A runs on his subscription login (D4 A), which bills no money per call, and a usage or weekly limit "
    "pauses under rate_limit_markers. The OpenAI and Google entries are added with their adapters, each with a "
    "non-empty list (OpenAI: project_spend_limit_exceeded, organization_spend_limit_exceeded, "
    "credit_balance_exhausted, insufficient_quota; Google: status 402 and its spend-cap error read at a walk), and "
    "this status is ruled again then.")


def walk(harness, tries=10, cost="1.34"):
    vendor = {CODEX: "openai", GEMINI: "google"}[harness]
    return {"vendor": vendor, "model": MODEL[harness], "agent": {"harness": harness, "version": "0.0.1-test"},
            "tries_left": tries, "cost_per_try": cost}


def snapshot(now=OUT_OF_HOLD, trimmed=None, spend=None, walks=None):
    """One reading of the spend ledger, within the caps unless told otherwise."""
    return {"now": now, "trimmed": trimmed, "start": START,
            "spend": spend if spend is not None else [{"vendor": "openai", "at": "2026-10-05T00:00:00Z", "usd": "20"},
                                                      {"vendor": "google", "at": "2026-10-05T00:00:00Z", "usd": "5"}],
            "walks": walks if walks is not None else [walk(CODEX), walk(GEMINI)]}


class ShiftingDict(dict):
    """W7C-R2-1: a hostile dict subclass whose spend reads as a list at the shape check and as "" afterwards."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.reads = 0

    def __getitem__(self, key):
        if key == "spend":
            self.reads += 1
            return dict.__getitem__(self, key) if self.reads == 1 else ""
        return dict.__getitem__(self, key)


class KeyLike(str):
    """W7C-R2-1 (the reviewer's probe2): a key equal to every key, hashing as "walks"."""

    def __eq__(self, other):
        return True

    def __hash__(self):
        return hash("walks")


class LyingFloat(float):
    """W7C-R2-2: a float subclass whose str() says nothing was spent."""

    def __str__(self):
        return "0"

    __repr__ = __str__


OVER_SPENT = [{"vendor": "openai", "at": "2026-10-05T00:00:00Z", "usd": "261"}]


class Ledger:
    """The spend ledger's double: read() returns one snapshot (a deep copy, its own type kept), or raises."""

    def __init__(self, snap=None, raises=None, world=None):
        self.snap, self.raises, self.world, self.reads = snap, raises, world, 0

    def read(self):
        self.reads += 1
        if self.world is not None:
            self.world.log("ledger-read")
        if self.raises is not None:
            raise self.raises
        if isinstance(self.snap, ShiftingDict):
            return ShiftingDict(copy.deepcopy(dict(self.snap)))
        return copy.deepcopy(self.snap)


def paid_table() -> dict:
    """test_batch's test table, plus test-only markers, spend-cap lists and one profile for each paid harness (and for
    a made-up paid harness with no arm, `fake-paid`)."""
    t = tb.test_table()
    for h, typ, status in ((CODEX, "test_codex_spend_limit", []), (GEMINI, "test_gemini_spend_cap", [402]),
                           ("fake-paid", "test_fake_spend", [])):
        t["rate_limit_markers"][h] = {"status": [429], "type": [f"{typ}_slow"], "text": [f"{h} throttled"],
                                      "reset_wait": None, "source": "test-only"}
        t["spend_cap_markers"][h] = {"status": list(status), "type": [typ], "text": [], "source": "test-only"}
        t["pin_profiles"][h] = {MODEL[h]: {"permission_mode": "test-mode", "version": "0.0.1-test"}}
    return t


def row(slot, harness):
    profile = paid_table()["pin_profiles"][harness][MODEL[harness]]
    return {"slot": slot, "half_cell": f"hc-{harness}-{slot}", "row_id": slot, "model": MODEL[harness],
            "agent": {"harness": harness, "version": profile["version"]}}


class Driver:
    """launch / drive / remove: drive returns the registered row's own pin, so every take routes (by the stub route)."""

    def __init__(self, world, mod, table):
        self.world, self.mod, self.table = world, mod, table

    def launch(self, r):
        cid = f"ctr-{r['slot']}"
        self.world.log("launch", r["slot"], cid)
        return cid

    def drive(self, r, cid):
        return {"pin": self.mod.expected_pin(r, self.table)}

    def remove(self, cid):
        self.world.log("remove", cid)


def at(text):
    """An aware UTC clock reading, from the same strings the ledger carries."""
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc)


def run(mod, rows, ledger, serial=False, table=None, clock=None):
    """One loop of `mod` (batch.py, or a witness of it) on in-memory doubles; the route and annotations are stubs.
    `clock` is batch's own clock; when none is given it reads the same moment as the ledger's `now` (G6-clock is the
    check that sets the two apart)."""
    w = tb.World()
    if clock is None:
        snap = getattr(ledger, "snap", None)
        moment = at(snap["now"]) if isinstance(snap, dict) and isinstance(snap.get("now"), str) \
            and snap["now"].endswith("Z") else at(OUT_OF_HOLD)
        clock = lambda: moment  # noqa: E731
    if isinstance(ledger, Ledger):
        ledger.world = w
    t = table or paid_table()
    b = mod.Batch(Driver(w, mod, t), tb.FakeRepo(w), tb.FakeWindow(w), table=t, serial=serial,
                  route_fn=lambda records, table: {"route": labels4.GRADED},
                  annotate_fn=lambda records, table: {"events": [], "mask": False}, ledger=ledger,
                  clock=clock)
    b.run(rows)
    return b, w


def kinds(w, kind):
    return [e for e in w.events if e[1] == kind]


def guarded(clause, fn):
    """A check that raised has found nothing it can vouch for: an ERROR line, never a pass."""
    def check(*a):
        try:
            return fn(*a)
        except Exception as e:  # noqa: BLE001
            return [f"ERROR: {clause}: {type(e).__name__}: {e}"]
    return check


# ------------------------------------------------------------------------------------------------ the checks
def _g1(mod) -> list[str]:
    p = []
    claude = [row(i, CLAUDE) for i in (1, 2, 3)]
    calls = {"month": 0, "walk": 0}

    def count(name, real):
        def spy(*a, **k):
            calls[name] += 1
            return real(*a, **k)
        return spy
    with mock.patch.object(costs, "month_turn_allowed", count("month", costs.month_turn_allowed)), \
            mock.patch.object(costs, "walk_gate", count("walk", costs.walk_gate)):
        try:
            b, w = run(mod, copy.deepcopy(claude), None)
        except mod.BatchConfigError as e:
            p.append(f"G1-claude: claude-code rows with no ledger are refused: {e}")
        else:
            if len(kinds(w, "launch")) != 3 or b.stopped is not None:
                p.append(f"G1-claude: claude-code rows with no ledger did not all run: {len(kinds(w, 'launch'))} "
                         f"launched, stopped {b.stopped}")
        for name, ledger in (("an unreadable ledger", Ledger(raises=RuntimeError("no ledger here"))),
                             ("the hold and a spent cap", Ledger(snapshot(now=IN_HOLD, spend=OVER_SPENT)))):
            b, w = run(mod, copy.deepcopy(claude), ledger)
            if ledger.reads:
                p.append(f"G1-claude: claude-code rows read the ledger ({name}): {ledger.reads} reads")
            if len(kinds(w, "launch")) != 3 or b.stopped is not None:
                p.append(f"G1-claude: claude-code rows under {name} did not all run: stopped {b.stopped}")
    if calls["month"] or calls["walk"]:
        p.append(f"G1-claude: claude-code rows called the money checks: {calls}")
    return p


def _refused(clause, b, w, why, words) -> list[str]:
    p = []
    if kinds(w, "register") or kinds(w, "launch"):
        p.append(f"{clause}: {why}: the block was registered or launched: {w.events}")
    if not isinstance(b.stopped, dict) or b.stopped.get("state") != labels4.BLOCKED:
        p.append(f"{clause}: {why}: the loop did not stop blocked: {b.stopped}")
    else:
        for word in words:
            if word not in str(b.stopped.get("reason")):
                p.append(f"{clause}: {why}: the stop does not name {word!r}: {b.stopped['reason']}")
    return p


def _ran(clause, b, w, why, n=1) -> list[str]:
    if len(kinds(w, "launch")) != n or b.stopped is not None:
        return [f"{clause}: {why}: want {n} launched and no stop, got {len(kinds(w, 'launch'))}, {b.stopped}"]
    return []


def _g2(mod) -> list[str]:
    p = []
    for h in PAID:
        arm = ARM_OF[h]
        b, w = run(mod, [row(1, h)], Ledger(snapshot(now=IN_HOLD)))
        p += _refused("G2-month", b, w, f"{h} in the month-turn hold", ("month-turn", f"arm {arm}"))
        b, w = run(mod, [row(1, h)], Ledger(snapshot(now=IN_HOLD, trimmed=copy.deepcopy(TRIMMED))))
        p += _ran("G2-month", b, w, f"{h} in the hold with Javier's trim recorded")
        seen = []
        real = costs.month_turn_allowed

        def spy(a, now, trimmed):
            seen.append((a, now, trimmed))
            return real(a, now, trimmed)
        with mock.patch.object(costs, "month_turn_allowed", spy):
            b, w = run(mod, [row(1, h)], Ledger(snapshot(now=OUT_OF_HOLD)))
        p += _ran("G2-month", b, w, f"{h} outside the hold")
        if seen != [(arm, at(OUT_OF_HOLD), None)] * 2:   # at the block's gate, and again just before the launch (R1-3)
            p.append(f"G2-month: {h}: costs.month_turn_allowed was called {seen}, want twice (gate, launch) with "
                     f"({arm!r}, batch's clock, the ledger's trim)")
        with mock.patch.object(costs, "month_turn_allowed", lambda a, now, trimmed: False):
            b, w = run(mod, [row(1, h)], Ledger(snapshot(now=OUT_OF_HOLD)))
        p += _refused("G2-month", b, w, f"{h} when costs' own hold refuses", ("month-turn",))
    return p


def _g3(mod) -> list[str]:
    p = []
    for h in PAID:
        b, w = run(mod, [row(1, h)], Ledger(snapshot(spend=OVER_SPENT)))
        p += _refused("G3-walk", b, w, f"{h} after OpenAI's cap was spent", ("walk gate", costs.STOP_FOR_WORD))
        b, w = run(mod, [row(1, h)], Ledger(snapshot(walks=[walk(CODEX, tries=1000)])))
        p += _refused("G3-walk", b, w, f"{h} when the remaining tries project past a cap", ("walk gate",))
        # W7C-R1-2: a start after the loop's clock would exclude every dollar spent ($300 OpenAI here)
        b, w = run(mod, [row(1, h)], Ledger(snapshot(spend=[{"vendor": "openai", "at": "2026-10-10T00:00:00Z",
                                                               "usd": "300"}]) | {"start": "2027-01-01T00:00:00Z"}),
                   clock=lambda: at(OUT_OF_HOLD))
        p += _refused("G3-walk", b, w, f"{h} when the ledger's start is after the loop's clock", ("start",))
        b, w = run(mod, [row(1, h)], Ledger(snapshot(walks=[dict(walk(CODEX), vendor="anthropic")])))
        p += _refused("G3-walk", b, w, f"{h} when the walk gate refuses its inputs", ("walk gate",))
        for decision, refused in ((costs.STOP_FOR_WORD, True), ("anything else", True), (costs.PROCEED, False)):
            with mock.patch.object(costs, "walk_gate", lambda walks, spend, start, d=decision: {"decision": d}):
                b, w = run(mod, [row(1, h)], Ledger(snapshot()))
            p += (_refused("G3-walk", b, w, f"{h} when costs' own gate says {decision!r}", ("walk gate",)) if refused
                  else _ran("G3-walk", b, w, f"{h} when costs' own gate says {decision!r}"))
    return p


def _g4(mod) -> list[str]:
    p = []
    for h in PAID:
        try:
            run(mod, [row(1, CLAUDE), row(2, h)], None)
        except mod.BatchConfigError as e:
            if h not in str(e) or "ledger" not in str(e):
                p.append(f"G4-ledger: {h} with no ledger: the refusal names neither the harness nor the ledger: {e}")
        else:
            p.append(f"G4-ledger: a {h} row ran with no ledger")
        for why, ledger in (("an unreadable ledger", Ledger(raises=OSError("ledger file gone"))),
                            ("a ledger that is no dict", Ledger(["not", "a", "snapshot"])),
                            ("a ledger missing its trim", Ledger({k: v for k, v in snapshot().items() if k != "trimmed"})),
                            ("a ledger with an extra key", Ledger(dict(snapshot(), note="x"))),
                            # W7C-R1-1 (MAJOR, money fail-open): an empty string or dict iterates as nothing spent
                            ("walks as an empty string", Ledger(snapshot(walks=""))),
                            ("walks as an empty dict", Ledger(snapshot(walks={}))),
                            ("spend as an empty string", Ledger(snapshot(spend=""))),
                            ("spend as an empty dict", Ledger(snapshot(spend={}))),
                            ("spend as a tuple", Ledger(snapshot(spend=tuple(snapshot()["spend"])))),
                            ("a spend element that is no dict", Ledger(snapshot(spend=["openai 300"]))),
                            ("a walk that is no dict", Ledger(snapshot(walks=[1]))),
                            ("start as an int", Ledger(snapshot() | {"start": 0})),
                            ("start as a naive datetime", Ledger(snapshot() | {"start": datetime(2026, 10, 1)})),
                            ("start as None", Ledger(snapshot() | {"start": None})),
                            # W7C-R2-1: the reading itself must be exactly a dict
                            ("a dict subclass reading", Ledger(ShiftingDict(snapshot(spend=OVER_SPENT)))),
                            # W7C-R2-2: usd must be exactly str, int or float ($300 whose str() says 0)
                            ("a usd whose type lies", Ledger(snapshot(spend=[{"vendor": "openai",
                                                                             "at": "2026-10-05T00:00:00Z",
                                                                             "usd": LyingFloat(300)}]))),
                            ("a key that is a str subclass", Ledger({KeyLike("zzz"): [], **{k: v for k, v in
                                                                              snapshot().items() if k != "walks"}})),
                            ("a usd that is a bool", Ledger(snapshot(spend=[{"vendor": "openai",
                                                                            "at": "2026-10-05T00:00:00Z",
                                                                            "usd": True}])))):
            b, w = run(mod, [row(1, h)], ledger)
            p += _refused("G4-ledger", b, w, f"{h}, {why}", ("ledger",))
        b, w = run(mod, [row(1, h)], Ledger(snapshot()), clock=lambda: datetime(2026, 10, 15, 12))   # no zone
        p += _refused("G4-ledger", b, w, f"{h}, a clock the hold cannot read", ("month-turn",))
    b, w = run(mod, [row(1, "fake-paid")], Ledger(snapshot()))
    p += _refused("G4-ledger", b, w, "a paid harness with no arm", ("fake-paid", "no arm"))
    return p


def _g5(mod) -> list[str]:
    p = []
    b, w = run(mod, [row(1, CLAUDE), row(2, CODEX), row(3, CLAUDE)], Ledger(snapshot(now=IN_HOLD)))
    p += _refused("G5-order", b, w, "a block holding one held codex row", ("month-turn",))
    if isinstance(b.stopped, dict) and b.stopped.get("slot") != 2:
        p.append(f"G5-order: the stop names slot {b.stopped.get('slot')}, not the refused row's slot 2")
    b, w = run(mod, [row(1, CLAUDE), row(2, GEMINI)], Ledger(snapshot(now=IN_HOLD)), serial=True)
    if [e[2] for e in kinds(w, "register")] != [1] or [e[2] for e in kinds(w, "launch")] != [1]:
        p.append(f"G5-order: serial, the claude-code block before the held gemini block: want slot 1 alone "
                 f"registered and launched, got {w.events}")
    ledger = Ledger(snapshot())
    b, w = run(mod, [row(1, CODEX), row(2, GEMINI)], ledger, serial=True)
    p += _ran("G5-order", b, w, "two paid blocks within the caps", n=2)
    if ledger.reads != 2:
        p.append(f"G5-order: two paid blocks read the ledger {ledger.reads} times, want once per block")
    order = [e[1] for e in w.events if e[1] in ("ledger-read", "register")]
    if order != ["ledger-read", "register", "ledger-read", "register"]:
        p.append(f"G5-order: the ledger is not read before each block's registration: {order}")
    return p


def _g6(mod) -> list[str]:
    p = []
    for h in PAID:
        b, w = run(mod, [row(1, h)], Ledger(snapshot(now=OUT_OF_HOLD)), clock=lambda: at(IN_HOLD))
        p += _refused("G6-clock", b, w, f"{h}: the ledger says 15 Oct, batch's clock is inside the hold",
                      ("month-turn",))
        b, w = run(mod, [row(1, h)], Ledger(snapshot(now=IN_HOLD)), clock=lambda: at(OUT_OF_HOLD))
        p += _ran("G6-clock", b, w, f"{h}: the ledger says inside the hold, batch's clock says 15 Oct")
    # W7C-R1-3: the clock passes 23:30 UTC Sat 31 Oct between the block's gate and a paid launch
    for rows_, paid_slot in (([row(1, CODEX)], 1), ([row(1, CLAUDE), row(2, GEMINI), row(3, CLAUDE)], 2)):
        ticks = [at("2026-10-31T23:29:59Z")]

        def ticking():
            reading = ticks[0]
            ticks[0] = at("2026-10-31T23:30:30Z")   # every later reading is past 23:30
            return reading
        b, w = run(mod, copy.deepcopy(rows_), Ledger(snapshot()), clock=ticking)
        launched = [e[2] for e in kinds(w, "launch")]
        mine = [o for o in b.outcomes if o["slot"] == paid_slot]
        if paid_slot in launched:
            p.append(f"G6-clock: slot {paid_slot} launched after 23:30 UTC 31 Oct (gated at 23:29:59): {w.events}")
        if [(o["state"], o["drive_started"]) for o in mine] != [(labels4.FAILED, False)]:
            p.append(f"G6-clock: the held launch is not committed failed with drive_started false: {mine}")
        if not isinstance(b.stopped, dict) or b.stopped.get("state") != labels4.BLOCKED \
                or "month-turn" not in str(b.stopped.get("reason")) or b.stopped.get("slot") != paid_slot:
            p.append(f"G6-clock: the loop did not stop blocked on slot {paid_slot}'s month-turn hold: {b.stopped}")
        if [o["slot"] for o in b.outcomes] != [r["slot"] for r in rows_]:
            p.append(f"G6-clock: not every registered take of the block was committed: {b.outcomes}")
        if any(s > paid_slot for s in launched):
            p.append(f"G6-clock: a take after the held one was launched: {launched}")
    calls = []
    b, w = run(mod, [row(1, CODEX)], Ledger(snapshot()), clock=lambda: calls.append(1) or at(OUT_OF_HOLD))
    if not calls:
        p.append("G6-clock: batch's clock was never read for a paid block")
    return p


def _r1(mod) -> list[str]:
    p = []
    real = mod.load_table()
    if mod.check_table(real) != []:
        p.append(f"R1-nonempty: routing.json itself is refused: {mod.check_table(real)}")
    elif any(real["spend_cap_markers"][CLAUDE][k] for k in ("status", "type", "text")):
        p.append("R1-nonempty: claude-code's spend-cap list is not the empty one this check holds sound")
    t = paid_table()
    if mod.check_table(t) != []:
        p.append(f"R1-nonempty: the test table with non-empty paid lists is refused: {mod.check_table(t)}")
    for h in PAID + ("fake-paid",):   # B7-F4: codex's empty list is refused again, with gemini's
        t = paid_table()
        t["spend_cap_markers"][h].update(status=[], type=[], text=[])
        found = mod.check_table(t)
        if not any(h in x and "spend" in x for x in found):
            p.append(f"R1-nonempty: an empty spend-cap list for {h} is admitted by check_table: {found}")
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "routing.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(t, fh)
            try:
                mod.load_table(path)
            except mod.TableError as e:
                if h not in str(e):
                    p.append(f"R1-nonempty: load_table refuses the empty {h} list without naming it: {e}")
            else:
                p.append(f"R1-nonempty: load_table admits an empty spend-cap list for {h}")
            with mock.patch.object(mod, "TABLE_PATH", path), redirect_stdout(io.StringIO()), \
                    redirect_stderr(io.StringIO()):
                try:
                    rc = mod.main(["--check"])
                except mod.TableError:
                    rc = "refused"
            if rc == 0:
                p.append(f"R1-nonempty: routing.py --check passes an empty spend-cap list for {h}")
    # Lane w8c: the refusal outlives the ruling. On routing.json as it stands (status RULED), a codex or gemini entry
    # with an empty list is refused; with one marker it is sound (the control). B7-F4 restored codex's refusal.
    if batch.is_pending(real.get("spend_cap_markers_status", batch.PENDING)):
        p.append("R1-nonempty: spend_cap_markers_status is not ruled, so the after-the-ruling refusal is unproven")
    for h in PAID:
        for markers, want_refused in (([], True), ([f"test_{h}_spend_cap"], False)):
            t = copy.deepcopy(real)
            t["rate_limit_markers"][h] = {"status": [429], "type": [f"test_{h}_slow"], "text": [f"{h} throttled"],
                                          "reset_wait": None, "source": "test-only"}
            t["spend_cap_markers"][h] = {"status": [], "type": list(markers), "text": [], "source": "test-only"}
            found = mod.check_table(t)
            refused = any(h in x and "names no spend-cap marker" in x for x in found)
            if want_refused and not refused:
                p.append(f"R1-nonempty: after the ruling, an empty spend-cap list for {h} is admitted: {found}")
            if not want_refused and found:
                p.append(f"R1-nonempty: after the ruling, a {h} list with one marker is refused: {found}")
    t = paid_table()
    t["spend_cap_markers"][GEMINI].update(status=[402], type=[], text=[])   # one documented status is enough
    if mod.check_table(t) != []:
        p.append(f"R1-nonempty: a gemini list holding only status 402 is refused: {mod.check_table(t)}")
    return p


def _b1(mod) -> list[str]:
    p = []
    want = {h: {"arm": ARM_OF[h], "vendor": build_draft.VENDORS[h]} for h in PAID}
    if getattr(mod, "PAID_HARNESSES", None) != want:
        p.append(f"B1-names: routing.PAID_HARNESSES is {getattr(mod, 'PAID_HARNESSES', None)!r}, want {want!r}")
    if {v["vendor"] for v in want.values()} != set(costs.CAPS):
        p.append(f"B1-names: the paid vendors are not costs.CAPS's {sorted(costs.CAPS)}")
    if tuple(getattr(mod, "NO_MONEY_HARNESSES", ())) != (CLAUDE,):
        p.append(f"B1-names: routing.NO_MONEY_HARNESSES is {getattr(mod, 'NO_MONEY_HARNESSES', None)!r}, want "
                 f"({CLAUDE!r},)")
    return p


def _refusal(mod, table) -> str | None:
    """The loop's refusal on `table` (None when it would start)."""
    w = tb.World()
    try:
        mod.Batch(Driver(w, mod, table), tb.FakeRepo(w), tb.FakeWindow(w), table=table, ledger=Ledger(snapshot()))
    except mod.BatchConfigError as e:
        return str(e)
    return None


def _p3(mod) -> list[str]:
    p = []
    table = routing.load_table()
    spend = table["spend_cap_markers_status"]
    # Round 17 B7 (glitch-b5's ruling M): glitch-b5's RULED 18 Oct line, quoting Javier's RULED 12 Oct line word for word
    if not (spend.startswith(B7_SPEND_PREFIX) and f'This supersedes, word for word: "{OWNER_SPEND_STATUS}"' in spend
            and '"spend markers: 1A 2A 3A"' in spend and not batch.is_pending(spend)):
        p.append(f"P3-ruled: spend_cap_markers_status is not the RULED 18 Oct line quoting Javier's: {spend[:80]!r}")
    if table["pin_profiles_status"] != CP5_STATUS or batch.is_pending(table["pin_profiles_status"]):
        p.append(f"P3-ruled: pin_profiles_status is not the CP5 ruling: {table['pin_profiles_status'][:80]!r}")
    if set(table["pin_profiles"]) != {CLAUDE, CODEX, GEMINI} or set(table["spend_cap_markers"]) != {CLAUDE, CODEX, GEMINI}:
        p.append("P3-ruled: routing.json's pin-profile or spend-cap harnesses are not exactly claude-code, codex and gemini")
    if mod.start_problems(table) != []:
        p.append(f"P3-ruled: start_problems is not empty: {mod.start_problems(table)}")
    out = io.StringIO()
    with redirect_stdout(out):
        rc = mod.main(["--check"])
    if rc != 0 or out.getvalue().splitlines() != ["batch: routing.json ready"]:
        p.append(f"P3-ruled: batch.py --check is not exit 0 and ready: {rc}, {out.getvalue()!r}")
    why = _refusal(mod, table)
    if why is not None:
        p.append(f"P3-ruled: the loop refuses the ruled routing.json: {why}")
    # the spend-status gate stays armed: a PENDING spend status alone refuses with its own line
    spend_pending = copy.deepcopy(table)
    spend_pending["spend_cap_markers_status"] = BASE_SPEND_STATUS
    if mod.start_problems(spend_pending) != SPEND_ONLY_PROBLEMS:
        p.append(f"P3-ruled: a PENDING spend status does not give its one line: {mod.start_problems(spend_pending)}")
    if _refusal(mod, spend_pending) != "routing.json is not ready: " + "; ".join(SPEND_ONLY_PROBLEMS):
        p.append(f"P3-ruled: the loop does not refuse a PENDING spend status with its line: "
                 f"{_refusal(mod, spend_pending)}")
    # the spend-status gate stays armed: the same table with the base's PENDING status refuses as the base did
    pending = copy.deepcopy(table)   # the base's table: pins empty and both statuses PENDING
    pending.update(pin_profiles={}, pin_profiles_status="PENDING (CP5)", spend_cap_markers_status=BASE_SPEND_STATUS)
    if mod.start_problems(pending) != BASE_START_PROBLEMS:
        p.append(f"P3-ruled: a PENDING spend status no longer gives the base's three lines: {mod.start_problems(pending)}")
    if _refusal(mod, pending) != "routing.json is not ready: " + "; ".join(BASE_START_PROBLEMS):
        p.append(f"P3-ruled: the loop does not refuse a PENDING spend status with the base's words: "
                 f"{_refusal(mod, pending)}")
    return p


CHECKS = {"G1-claude": _g1, "G2-month": _g2, "G3-walk": _g3, "G4-ledger": _g4, "G5-order": _g5, "G6-clock": _g6,
          "R1-nonempty": _r1, "B1-names": _b1, "P3-ruled": _p3}
CHECKS = {k: guarded(k, f) for k, f in CHECKS.items()}


class TestTheMoneyGate(unittest.TestCase):
    def test_g1_claude_rows_never_touch_the_money_checks(self):
        self.assertEqual(CHECKS["G1-claude"](batch), [])

    def test_g2_the_month_turn_hold_refuses_arms_o_and_g(self):
        self.assertEqual(CHECKS["G2-month"](batch), [])

    def test_g3_the_walk_gate_refuses_arms_o_and_g(self):
        self.assertEqual(CHECKS["G3-walk"](batch), [])

    def test_g4_the_ledger_is_required_and_read_fail_closed(self):
        self.assertEqual(CHECKS["G4-ledger"](batch), [])

    def test_g5_the_gate_holds_the_whole_block_before_registration(self):
        self.assertEqual(CHECKS["G5-order"](batch), [])

    def test_g6_the_hold_reads_batchs_own_clock(self):
        self.assertEqual(CHECKS["G6-clock"](batch), [])


class TestTheSpendLists(unittest.TestCase):
    def test_the_test_table_is_sound(self):
        self.assertEqual(routing.check_table(paid_table()), [])

    def test_r1_a_paid_harness_never_has_an_empty_spend_list(self):
        self.assertEqual(CHECKS["R1-nonempty"](routing), [])

    def test_b1_the_paid_harnesses_are_the_seams_and_the_drafts(self):
        self.assertEqual(CHECKS["B1-names"](routing), [])


class TestSpendStatusRuled(unittest.TestCase):
    def test_p3_the_spend_and_pin_statuses_are_ruled_and_the_spend_gate_stays_armed(self):
        self.assertEqual(CHECKS["P3-ruled"](batch), [])


# name: (edits, the module the edits apply to, the bound check)
WITNESSES = {
    # re-anchored to batch.py's rolling window (B19-8): the same mutations, on the wave the gate now reads
    "gate-never-called": ((("        if self._money_gate(wave):                         # W7C: before the wave is "
                            "registered\n            return\n", ""),), "batch", "G2-month"),
    "month-check-dropped": ((("            allowed = costs.month_turn_allowed(arm, now, snap[\"trimmed\"])",
                              "            allowed = True"),), "batch", "G2-month"),
    "walk-check-dropped": ((("    if gate.get(\"decision\") != costs.PROCEED:",
                             "    if gate.get(\"decision\") == \"never\":"),), "batch", "G3-walk"),
    "claude-gated": ((("    return row[\"agent\"][\"harness\"] not in routing.NO_MONEY_HARNESSES",
                       "    return True"),), "batch", "G1-claude"),
    "no-ledger-passes": ((("        return [f\"the loop was given no spend ledger",
                           "        return []\n        return [f\"the loop was given no spend ledger"),
                          ("            elif bills_money(r) and self.ledger is None:",
                           "            elif False:"),), "batch", "G4-ledger"),
    "gate-after-register": ((("        if self._money_gate(wave):                         # W7C: before the wave is "
                              "registered\n            return\n"
                              "        if not self._register(wave):                        # serial: one commit each\n"
                              "            return\n",
                              "        if not self._register(wave):                        # serial: one commit each\n"
                              "            return\n"
                              "        if self._money_gate(wave):                         # W7C: before the wave is "
                              "registered\n            return\n"),), "batch", "G5-order"),
    # re-anchored to round 17 B7's check line (ruling M): the same mutation, the empty-list refusal switched off
    "empty-paid-list-admitted": ((("        if key == \"spend_cap_markers\" and harness not in EMPTY_SPEND_LIST_HARNESSES",
                                   "        if False"),), "routing", "R1-nonempty"),
    "spend-status-ungated": ((("    if is_pending(table.get(\"spend_cap_markers_status\", PENDING)):",
                               "    if False:"),), "batch", "P3-ruled"),
    "ledger-clock": ((("            allowed = costs.month_turn_allowed(arm, now, snap[\"trimmed\"])",
                       "            allowed = costs.month_turn_allowed(arm, snap[\"now\"], snap[\"trimmed\"])"),),
                     "batch", "G6-clock"),
    "shape-unchecked": ((("    p = ledger_shape_problems(snap)\n", "    p = []\n"),), "batch", "G4-ledger"),
    "start-after-clock-admitted": ((("        if costs.utc(snap[\"start\"]) > costs.utc(now):",
                                     "        if False:"),), "batch", "G3-walk"),
    "launch-recheck-dropped": ((("        if bills_money(row):\n            why = hold_problem(",
                                 "        if False:\n            why = hold_problem("),), "batch", "G6-clock"),
    "stopped-guard-dropped": ((("        if self.stopped is not None:\n            return None, MoneyGateRefused(",
                                "        if False:\n            return None, MoneyGateRefused("),), "batch", "G6-clock"),
    "paid-arm-renamed": ((("    \"codex\": {\"arm\": \"O\", \"vendor\": \"openai\"},",
                           "    \"codex\": {\"arm\": \"C\", \"vendor\": \"openai\"},"),), "routing", "B1-names"),
}


def compiled(name: str, edits: tuple) -> types.ModuleType:
    """`name`.py with `edits`, compiled in memory as its own module (the real one stays in sys.modules)."""
    real = sys.modules[name]
    with open(real.__file__, encoding="utf-8") as fh:
        src = fh.read()
    for old, new in edits:
        if src.count(old) != 1:
            raise AssertionError(f"witness not performed: the anchor occurs {src.count(old)} times: {old[:70]!r}")
        src = src.replace(old, new)
    mod = types.ModuleType(name)
    mod.__file__ = real.__file__
    exec(compile(src, real.__file__ + " (witness)", "exec"), mod.__dict__)
    return mod


WITNESS_LOG: list = []


class TestWitnesses(unittest.TestCase):
    """Rule B: each witness is killed only by its bound check's own line, the bound check green on the tree first; an
    ERROR line or an unperformed edit is never a kill. Collateral (other clauses' lines) is listed, not credited."""

    def kill(self, name):
        edits, target, clause = WITNESSES[name]
        real = sys.modules[target]
        self.assertEqual(CHECKS[clause](real), [], f"{name}: the bound check {clause} is not green on the tree")
        got = CHECKS[clause](compiled(target, edits))
        errors = [x for x in got if x.startswith("ERROR")]
        own = [x for x in got if x.startswith(clause + ":")]
        collateral = [x for x in got if x not in own and x not in errors]
        line = (f"WITNESS {name}: {'red' if own and not errors else 'NOT KILLED'} by {clause} ({len(own)} own, "
                f"{len(collateral)} collateral, {len(errors)} errors)")
        print(f"\n{line}", end=" ", file=sys.stderr, flush=True)
        WITNESS_LOG.append(line)
        self.assertEqual(errors, [], f"{name}: the bound check errored under the witness: {errors}")
        self.assertTrue(own, f"{name}: survived (no {clause} line): {got}")

    def test_witness_gate_never_called(self):
        self.kill("gate-never-called")

    def test_witness_month_check_dropped(self):
        self.kill("month-check-dropped")

    def test_witness_walk_check_dropped(self):
        self.kill("walk-check-dropped")

    def test_witness_claude_gated(self):
        self.kill("claude-gated")

    def test_witness_no_ledger_passes(self):
        self.kill("no-ledger-passes")

    def test_witness_gate_after_register(self):
        self.kill("gate-after-register")

    def test_witness_empty_paid_list_admitted(self):
        self.kill("empty-paid-list-admitted")

    def test_witness_spend_status_ungated(self):
        self.kill("spend-status-ungated")

    def test_witness_ledger_clock(self):
        self.kill("ledger-clock")

    def test_witness_shape_unchecked(self):
        self.kill("shape-unchecked")

    def test_witness_start_after_clock_admitted(self):
        self.kill("start-after-clock-admitted")

    def test_witness_launch_recheck_dropped(self):
        self.kill("launch-recheck-dropped")

    def test_witness_stopped_guard_dropped(self):
        self.kill("stopped-guard-dropped")

    def test_witness_paid_arm_renamed(self):
        self.kill("paid-arm-renamed")

    def test_the_witnesses_are_named_and_bound(self):
        self.assertEqual(sorted(WITNESSES), sorted([
            "gate-never-called", "month-check-dropped", "walk-check-dropped", "claude-gated", "no-ledger-passes",
            "gate-after-register", "empty-paid-list-admitted", "paid-arm-renamed", "spend-status-ungated", "ledger-clock",
            "shape-unchecked", "start-after-clock-admitted", "launch-recheck-dropped",
            "stopped-guard-dropped"]))
        self.assertTrue(all(w[2] in CHECKS for w in WITNESSES.values()))


def tearDownModule():
    sys.path[:] = [p for p in sys.path if p in _PATH_BEFORE or p in (_ROOT, _TESTS)]


if __name__ == "__main__":
    unittest.main(verbosity=2)
