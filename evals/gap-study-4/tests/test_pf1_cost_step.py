#!/usr/bin/env python3
"""Lane pf1-l4-close's cost step (review REVIEW-pf1-l4-close-291b357 M1, m4 and m5; the lane orchestrator's rulings of
Sun 25 Oct 2026: build what the approved price table's page promised, and say what the table cannot support).

    python3 -B -W ignore evals/gap-study-4/tests/test_pf1_cost_step.py

Each case is one check returning its problems (empty when it holds), run on the approved table's own rows: a call over
its model's threshold is priced at the over-threshold rows and flagged (C1, C4); cache writes are split by their
recorded duration (C2) or, unrecorded, priced at the stated bound and said so (C3); every arm A and arm O priced cost
carries its label, in the accounting and in COSTS.md (C5); the statement is generated and names what is not built, and
every follow-up's status is one of three (C6); costs.main refuses a frozen file without variants (C7); Claude Code's
recorded split reaches the call shape (C8); the freeze pins the table (C9); the variants are the table's rows (C10);
without variants the accounting is as before (C11). The expected prices are read here from the approved file's rows by
their variant names, never through build_draft's derivation. MUTANTS: each one weakens one rule in memory, and the
check it names must then report a problem. No model, no network, stdlib only.
"""
from __future__ import annotations

import contextlib
import copy
import io
import json
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import build_draft as b  # noqa: E402
import claude_code_adapter as cca  # noqa: E402
import costs  # noqa: E402
import freeze  # noqa: E402
import harness_bookkeeping  # noqa: E402
from box import run_take  # noqa: E402

TABLE = json.loads((REPO / b.PRICE_TABLE_FILE).read_bytes())
PRICES = TABLE["study_shape_candidate"]
VARIANTS = b.price_variants(TABLE)
HARNESS = {"anthropic": harness_bookkeeping.CLAUDE_CODE, "openai": run_take.CODEX, "google": run_take.GEMINI}
MTOK = Decimal(1000000)


def row(vendor, model, token_class, variant):
    """One price of the approved file, read by its row's own names."""
    (got,) = [r["price_usd"] for r in TABLE["rows"]
              if (r["vendor"], r["model"], r["token_class"], r["variant"]) == (vendor, model, token_class, variant)]
    return Decimal(got)


def call(vendor, model, usage, cid="c1", **extra):
    return dict({"vendor": vendor, "call_id": cid, "model": model,
                 "agent": {"harness": HARNESS[vendor], "version": "0.0.0-fake"}, "usage": dict(usage),
                 "total_cost_usd": None, "started_at": None, "ended_at": None}, **extra)


def priced(one, variants=None):
    return costs.price_call(one, PRICES["vendors"][one["vendor"]][one["model"]], VARIANTS if variants is None
                            else variants)


def cost_of(counts):
    return sum((Decimal(n) * price / MTOK for n, price in counts), Decimal(0))


LONG = "Standard, long context (>272K input tokens)"
SHORT = "Standard, short context (<=272K input tokens)"
OVER, UP = "prompts over 100,000 tokens", "prompts up to 100,000 tokens"


# ---- the cases -----------------------------------------------------------------------------------------------------
def c1_long_context():
    """A gpt-6.1-sol call over 272,000 prompt tokens (its three input classes together) is priced at the long-context
    rows and flagged; one at exactly 272,000 is priced at the four prices, unflagged."""
    out, m = [], "gpt-6.1-sol"
    over = call("openai", m, {"input_tokens": 200000, "cache_read_input_tokens": 72001, "output_tokens": 1000,
                              "cache_creation_input_tokens": 0})
    got = priced(over)
    want = cost_of([(200000, row("openai", m, "input_tokens", LONG)), (72001, row("openai", m, "cache_read_input_tokens",
                    LONG)), (1000, row("openai", m, "output_tokens", LONG))])
    if got["priced_cost_usd"] != want:
        out.append(f"C1: a call of 272001 prompt tokens is priced {got['priced_cost_usd']}, the long rows give {want}")
    if len(got["flags"]) != 1 or "272000" not in got["flags"][0]:
        out.append(f"C1: the long-context call's record flags {got['flags']}")
    at = priced(call("openai", m, {"input_tokens": 200000, "cache_read_input_tokens": 72000, "output_tokens": 1000}))
    want = cost_of([(200000, row("openai", m, "input_tokens", SHORT)), (72000, row("openai", m, "cache_read_input_tokens",
                    SHORT)), (1000, row("openai", m, "output_tokens", SHORT))])
    if at["priced_cost_usd"] != want or at["flags"]:
        out.append(f"C1: a call of exactly 272000 prompt tokens is priced {at['priced_cost_usd']} {at['flags']}")
    return out


def c2_split():
    """A recorded split prices each duration at its own row; a split that does not sum is refused."""
    out, m = [], "claude-opus-5-5"
    one = call("anthropic", m, {"input_tokens": 10, "output_tokens": 20, "cache_read_input_tokens": 30,
                                "cache_creation_input_tokens": 4000}, cache_write_durations={"5m": 1000, "1h": 3000})
    got = priced(one)
    want = cost_of([(10, row("anthropic", m, "input_tokens", "standard")),
                    (20, row("anthropic", m, "output_tokens", "standard")),
                    (30, row("anthropic", m, "cache_read_input_tokens", "standard (cache hits and refreshes)")),
                    (1000, row("anthropic", m, "cache_creation_input_tokens", "5m cache write")),
                    (3000, row("anthropic", m, "cache_creation_input_tokens", "1h cache write"))])
    if got["priced_cost_usd"] != want:
        out.append(f"C2: a split of 1000 5m and 3000 1h writes is priced {got['priced_cost_usd']}, the rows give {want}")
    if not (got["cache_write"] or "").startswith("split by recorded duration"):
        out.append(f"C2: the split call's record says {got['cache_write']!r}")
    bad = dict(one, cache_write_durations={"5m": 1000, "1h": 2999})
    try:
        priced(bad)
        out.append("C2: a split summing to 3999 of 4000 cache writes was priced")
    except ValueError:
        pass
    luna = call("openai", "gpt-6-luna", {"input_tokens": 1, "output_tokens": 1, "cache_read_input_tokens": 0,
                                          "cache_creation_input_tokens": 300}, cache_write_durations={"30m": 100, "12h": 200})
    want = cost_of([(1, row("openai", "gpt-6-luna", "input_tokens", SHORT)),
                    (1, row("openai", "gpt-6-luna", "output_tokens", SHORT)),
                    (100, row("openai", "gpt-6-luna", "cache_creation_input_tokens", SHORT + " 30m write")),
                    (200, row("openai", "gpt-6-luna", "cache_creation_input_tokens", SHORT + " 12h write"))])
    if priced(luna)["priced_cost_usd"] != want:
        out.append(f"C2: a Codex split is priced {priced(luna)['priced_cost_usd']}, the rows give {want}")
    return out


def c3_bound():
    """With no split recorded, the whole is priced at the longer duration's row, and the record says so."""
    out = []
    for vendor, m, variant, bound in (("anthropic", "claude-sonnet-5-5", "1h cache write", "1h"),
                                      ("openai", "gpt-6.1-sol", SHORT + " 12h write", "12h")):
        got = priced(call(vendor, m, {"input_tokens": 0, "output_tokens": 0, "cache_read_input_tokens": 0,
                                      "cache_creation_input_tokens": 5000}))
        want = cost_of([(5000, row(vendor, m, "cache_creation_input_tokens", variant))])
        if got["priced_cost_usd"] != want:
            out.append(f"C3: {m}'s unrecorded writes are priced {got['priced_cost_usd']}, the {bound} row gives {want}")
        note = got["cache_write"] or ""
        if not (note.startswith("duration not recorded") and f"the {bound} row" in note and "conservative bound" in note):
            out.append(f"C3: {m}'s unrecorded writes' record says {note!r}")
    return out


def c4_haiku_over():
    """A claude-haiku-5-5 call over 100,000 prompt tokens is priced at the over-100,000 rows and flagged; one at
    exactly 100,000 at the up-to rows."""
    out, m = [], "claude-haiku-5-5"
    usage = {"input_tokens": 50000, "cache_read_input_tokens": 30000, "cache_creation_input_tokens": 20001,
             "output_tokens": 700}
    got = priced(call("anthropic", m, usage, cache_write_durations={"5m": 1, "1h": 20000}))
    want = cost_of([(50000, row("anthropic", m, "input_tokens", OVER)), (700, row("anthropic", m, "output_tokens", OVER)),
                    (30000, row("anthropic", m, "cache_read_input_tokens", OVER + " (cache hits and refreshes)")),
                    (1, row("anthropic", m, "cache_creation_input_tokens", OVER + " 5m cache write")),
                    (20000, row("anthropic", m, "cache_creation_input_tokens", OVER + " 1h cache write"))])
    if got["priced_cost_usd"] != want or len(got["flags"]) != 1 or "100000" not in got["flags"][0]:
        out.append(f"C4: a haiku-5-5 call of 100001 prompt tokens: {got['priced_cost_usd']} {got['flags']}, want {want}")
    at = priced(call("anthropic", m, dict(usage, cache_creation_input_tokens=20000),
                     cache_write_durations={"5m": 0, "1h": 20000}))
    want = cost_of([(50000, row("anthropic", m, "input_tokens", UP)), (700, row("anthropic", m, "output_tokens", UP)),
                    (30000, row("anthropic", m, "cache_read_input_tokens", UP + " (cache hits and refreshes)")),
                    (20000, row("anthropic", m, "cache_creation_input_tokens", UP + " 1h cache write"))])
    if at["priced_cost_usd"] != want or at["flags"]:
        out.append(f"C4: a haiku-5-5 call of exactly 100000 prompt tokens: {at['priced_cost_usd']} {at['flags']}")
    return out


def _calls():
    return [call("anthropic", "claude-opus-5-5", {"input_tokens": 5, "output_tokens": 5}, "a1"),
            call("openai", "gpt-6-luna", {"input_tokens": 5, "output_tokens": 5}, "o1"),
            call("google", "gemini-3.8-flash", {"input_tokens": 5, "output_tokens": 5}, "g1")]


def c5_labels():
    """Every arm A and arm O priced cost carries the table's label, in the accounting and on the page; google's none."""
    out = []
    acct = costs.account(_calls(), PRICES, VARIANTS)
    labels = {"anthropic": TABLE["arm_a_label"], "openai": TABLE["arm_o_label"]}
    for vendor, label in labels.items():
        if acct["vendors"][vendor].get("label") != label:
            out.append(f"C5: the {vendor} subtotal is labelled {acct['vendors'][vendor].get('label')!r}")
    for one in acct["calls_priced"]:
        want = labels.get(one["vendor"])
        if one.get("label") != want:
            out.append(f"C5: call {one['call_id']} is labelled {one.get('label')!r}, want {want!r}")
    if "label" in acct["vendors"]["google"]:
        out.append("C5: the google subtotal carries a label")
    page = costs.render(acct, costs.cost_statement(VARIANTS))
    for label in labels.values():
        if page.count(label) < 3:                    # the statement's line, the subtotal and the call
            out.append(f"C5: COSTS.md carries {label!r} {page.count(label)} time(s)")
    if not all(label.startswith(costs.LABEL_PREFIX) for label in labels.values()):
        out.append("C5: a table label does not open with \"API-equivalent, not billed\"")
    return out


def c6_statement():
    """The statement is generated from the variants, names every NOT_BUILT item, and the draft carries it; each
    follow-up's and lead ruling's status is built, partly built or not built, and only those not built say so."""
    out = []
    lines = costs.cost_statement(VARIANTS)
    for item in costs.NOT_BUILT_ITEMS:
        if f"not built in round 4: {item}" not in lines:
            out.append(f"C6: the statement lacks {item[:50]!r}")
    if len([ln for ln in lines if ln.startswith("not built in round 4: ")]) != len(costs.NOT_BUILT_ITEMS):
        out.append("C6: the statement's not-built lines are not the NOT_BUILT items")
    for needle in ("over 272000 tokens", "over 100000 tokens", "K as 1000"):
        if not any(needle in ln for ln in lines):
            out.append(f"C6: no built line says {needle!r}")
    d = json.loads((HERE / "prereg-draft.json").read_text())
    if d.get("cost_statement") != costs.cost_statement(d.get("price_variants")):
        out.append("C6: the draft's cost_statement is not costs.cost_statement of its price_variants")
    src = d["price_table_source"]
    for key in ("follow_ups", "lead_rulings"):
        for e in src[key]:
            s = e["status"]
            if not s.startswith(("built: ", "partly built: ", costs.NOT_BUILT + ": ")):
                out.append(f"C6: a {key} status opens {s[:20]!r}")
            if s.startswith("built: ") and costs.NOT_BUILT in s:
                out.append(f"C6: a built {key} status says not built: {s[:60]!r}")
            if not s.startswith("built: ") and costs.NOT_BUILT not in s:
                out.append(f"C6: an unbuilt {key} status does not say so: {s[:60]!r}")
    unbuilt = [e["text"][:40] for k in ("follow_ups", "lead_rulings") for e in src[k] if costs.NOT_BUILT in e["status"]]
    if len(unbuilt) != 4:                          # follow-ups 3, 4 and 6, and lead ruling 5
        out.append(f"C6: {len(unbuilt)} unbuilt follow-ups or rulings: {unbuilt}")
    return out


def c7_main():
    """costs.main refuses a frozen file without variants, and with them writes the statement and the labels."""
    out = []
    with tempfile.TemporaryDirectory() as tmp:
        calls, page = Path(tmp) / "cost-calls.json", Path(tmp) / "COSTS.md"
        calls.write_text(json.dumps(_calls()))
        for pre, want in (({"price_table": PRICES}, 1), ({"price_table": PRICES, "price_variants": VARIANTS}, 0)):
            with mock.patch.object(costs, "CALLS", calls), mock.patch.object(costs, "PAGE", page), \
                    mock.patch.object(costs.prereg, "require_frozen", return_value=pre), \
                    contextlib.redirect_stdout(io.StringIO()):
                got = costs.main(["--write"])
            if got != want:
                out.append(f"C7: main with {sorted(pre)} exits {got}, want {want}")
        text = page.read_text() if page.exists() else ""
        if not text.startswith("# Costs\n\n- built: ") or TABLE["arm_a_label"] not in text:
            out.append("C7: the written page does not open with the statement or lacks arm A's label")
    return out


def c8_adapter_split():
    """Claude Code's recorded 5m and 1h split reaches the call shape; a split that does not sum, or none, reads None."""
    out = []
    usage = {"input_tokens": 1, "output_tokens": 2, "cache_read_input_tokens": 3, "cache_creation_input_tokens": 70,
             "cache_creation": {"ephemeral_5m_input_tokens": 20, "ephemeral_1h_input_tokens": 50}}
    def session(u):
        return json.dumps({"type": "assistant", "sessionId": "s", "requestId": "r1",
                           "message": {"id": "m1", "model": "claude-opus-5-5", "role": "assistant",
                                       "content": [{"type": "text", "text": "x"}], "usage": u}}) + "\n"
    got = cca.cost_record([], session(usage), model="claude-opus-5-5", version="2.1.296")["calls"]
    if [c["cache_write_durations"] for c in got] != [{"5m": 20, "1h": 50}]:
        out.append(f"C8: a recorded split reads {[c['cache_write_durations'] for c in got]}")
    for u in (dict(usage, cache_creation={"ephemeral_5m_input_tokens": 20, "ephemeral_1h_input_tokens": 49}),
              {k: v for k, v in usage.items() if k != "cache_creation"}):
        if cca.session_calls(session(u))[0]["cache_write_durations"] is not None:
            out.append("C8: a split that does not sum, or no split, does not read None")
    walk = (HERE / "rehearsals/w125/transcript.jsonl").read_text()
    calls = cca.session_calls(walk)
    if not calls or not all(c["cache_write_durations"] is not None for c in calls):
        out.append("C8: a committed Claude walk's calls do not all carry their recorded split")
    return out


def c9_freeze_pin():
    out = []
    if b.PRICE_TABLE_FILE not in freeze.PINNED:
        out.append("C9: the freeze does not pin the approved price table")
    if b.PRICE_TABLE_FILE not in freeze.BOUND_OUTSIDE:
        out.append("C9: the study tree hash does not bind the approved price table")
    if b.PRICE_TABLE_FILE not in freeze.pinned_paths(freeze.PINNED):
        out.append("C9: the expanded pins lack the approved price table")
    return out


def c10_variants_are_the_rows():
    """Each variant price is the approved file's row of that name, and a variant set whose bound is not the four
    prices' cache-write price is refused."""
    out = []
    for m in ("claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-4-5-20251001"):
        for d in ("5m", "1h"):
            if Decimal(VARIANTS["cache_write"]["anthropic"][m][d]) != row("anthropic", m, costs.WRITE, f"{d} cache write"):
                out.append(f"C10: {m} {d}")
    for m in ("gpt-6.1-sol", "gpt-6-luna"):
        over = VARIANTS["over"]["openai"][m]
        for c in ("input_tokens", "output_tokens", "cache_read_input_tokens"):
            if Decimal(over["prices"][c]) != row("openai", m, c, LONG):
                out.append(f"C10: {m} long {c}")
        for d in ("30m", "12h"):
            if Decimal(over["cache_write"][d]) != row("openai", m, costs.WRITE, f"{LONG} {d} write"):
                out.append(f"C10: {m} long {d}")
            if Decimal(VARIANTS["cache_write"]["openai"][m][d]) != row("openai", m, costs.WRITE, f"{SHORT} {d} write"):
                out.append(f"C10: {m} short {d}")
    if set(VARIANTS["over"]) != {"anthropic", "openai"} or set(VARIANTS["over"]["anthropic"]) != {"claude-haiku-5-5"}:
        out.append(f"C10: over-threshold models {VARIANTS['over']}")
    bad = copy.deepcopy(VARIANTS)
    bad["cache_write"]["anthropic"]["claude-opus-5-5"]["1h"] = bad["cache_write"]["anthropic"]["claude-opus-5-5"]["5m"]
    try:
        costs.validate_variants(bad, PRICES)
        out.append("C10: a bound that is not the four prices' cache-write price was admitted")
    except ValueError:
        pass
    if json.loads((HERE / "prereg-draft.json").read_text()).get("price_variants") != VARIANTS:
        out.append("C10: the draft's price_variants are not price_variants of the approved table")
    return out


def c11_unchanged_without_variants():
    """Without variants the accounting is as before; a call under every threshold with no cache writes prices the same
    with them."""
    out = []
    old = costs.account(_calls(), PRICES)
    if "calls_priced" in old or any("label" in v for v in old["vendors"].values()):
        out.append("C11: an accounting without variants carries the variants' fields")
    new = costs.account(_calls(), PRICES, VARIANTS)
    if new["priced_cost_usd"] != old["priced_cost_usd"]:
        out.append(f"C11: plain calls price {new['priced_cost_usd']} with variants and {old['priced_cost_usd']} without")
    return out


CASES = {"C1": c1_long_context, "C2": c2_split, "C3": c3_bound, "C4": c4_haiku_over, "C5": c5_labels,
         "C6": c6_statement, "C7": c7_main, "C8": c8_adapter_split, "C9": c9_freeze_pin,
         "C10": c10_variants_are_the_rows, "C11": c11_unchanged_without_variants}


def _standard_tier(vendor, model, usage, prices, variants):
    return prices, variants["cache_write"].get(vendor, {}).get(model), None


def _no_flag(original):
    def tier(*a):
        p, w, _ = original(*a)
        return p, w, None
    return tier


def _ignore_split(original):
    def cost(vendor, one, count, prices, writes):
        return original(vendor, {k: v for k, v in one.items() if k != "cache_write_durations"}, count, prices, writes)
    return cost


# name -> (the case it must turn red, the patch)
MUTANTS = {
    "no-over-threshold": ("C1", lambda: mock.patch.object(costs, "tier_for", _standard_tier)),
    "no-flag": ("C1", lambda: mock.patch.object(costs, "tier_for", _no_flag(costs.tier_for))),
    "prompt-is-input-only": ("C1", lambda: mock.patch.object(costs, "prompt_tokens",
                                                              lambda u: u.get("input_tokens", 0))),
    "split-ignored": ("C2", lambda: mock.patch.object(costs, "cache_write_cost", _ignore_split(costs.cache_write_cost))),
    "bound-is-the-shorter": ("C3", lambda: mock.patch.object(costs, "BOUND_DURATION",
                                                              {"anthropic": "5m", "openai": "30m"})),
    "haiku-over-dropped": ("C4", lambda: mock.patch.dict(VARIANTS["over"], {"anthropic": {}})),
    "no-label": ("C5", lambda: mock.patch.object(costs, "label_for", lambda vendor, variants: None)),
    "statement-silent": ("C6", lambda: mock.patch.object(costs, "NOT_BUILT_ITEMS", ())),
    "main-unvalidated": ("C7", lambda: mock.patch.object(costs, "frozen_inputs", lambda pre: (
        pre["price_table"], pre.get("price_variants") or VARIANTS))),
    "adapter-drops-split": ("C8", lambda: mock.patch.object(cca, "cache_write_split", lambda usage, counts: None)),
    "freeze-unpinned": ("C9", lambda: mock.patch.object(freeze, "PINNED", [p for p in freeze.PINNED
                                                                           if p != b.PRICE_TABLE_FILE])),
}


def run_case(name):
    try:
        return CASES[name]()
    except Exception as e:                       # a case that raises is a problem, never a pass
        return [f"{name}: raised {type(e).__name__}: {e}"]


class TheCases(unittest.TestCase):
    def test_every_case_holds(self):
        for name in CASES:
            with self.subTest(case=name):
                self.assertEqual(run_case(name), [], name)


class TheMutants(unittest.TestCase):
    def test_every_mutant_turns_its_case_red(self):
        self.assertEqual({case for case, _ in MUTANTS.values()} - set(CASES), set())
        for name, (case, patch) in MUTANTS.items():
            with self.subTest(mutant=name):
                with patch():
                    self.assertTrue(run_case(case), f"mutant {name} left {case} green")

    def test_no_mutant_leaks(self):
        for name in CASES:
            self.assertEqual(run_case(name), [], f"{name} after the mutants")


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=2).result
    n = result.testsRun
    print(f"test_pf1_cost_step: {n} run, {len(result.failures)} failures, {len(result.errors)} errors")
    sys.exit(0 if result.wasSuccessful() else 1)
