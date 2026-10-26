#!/usr/bin/env python3
"""cost-calls.json, assembled from every committed take's own records, so costs.py accounts every arm.

Lane pf1-cost-vendors (Gap Study round 4, Mon 26 Oct 2026; the lane orchestrator glitch-f1's assignment: the gap the
L4-close lane named, "no step assembles cost-calls.json", and arm O and arm G takes that record no cost).

    python3 -B evals/gap-study-4/cost_calls.py --write     (after the freeze: cost-calls.json is run output)
    python3 -B evals/gap-study-4/cost_calls.py --check     (cost-calls.json is what this step assembles)

THE TAKES. Every committed outcome of takes.read_history(), once per (slot, attempt), in commit order; its take folder
is takes/<slot>/<attempt>/ (run.committed_evidence's road). A walk (rehearsals/) is never a take and never assembled.

THE CALLS, in costs.py's call shape {vendor, call_id, model, agent{harness, version}, usage, total_cost_usd,
started_at, ended_at, cache_write_durations}, usage in costs.CLASSES, which are disjoint (costs.prompt_tokens):
  claude-code  the driver ledger's cost.calls, as drive.py wrote them (claude_code_adapter.cost_record), unchanged.
  codex        one per token_usage_record of the take's last retained rollout (session/<native snapshot>, bound by the
               ledger's sha256): at the pinned CLI (openai/codex 092d3acd, protocol/src/protocol.rs:2291-2302) it is
               "Best-effort Responses API usage observed for one completed response", one per response_id. Its usage
               is the Responses API's, and input_tokens is the whole prompt: every recorded call's total_tokens is its
               input_tokens plus its output_tokens while most record cached tokens, so cached_input_tokens and
               reasoning_output_tokens are parts of input and output (checked on every call). That
               cache_write_input_tokens is a part of input too is read from the pinned source alone, since no recorded
               call writes to the cache: codex-api/src/sse/responses.rs:128-143 reads both cached and written tokens
               from input_tokens_details, and its test at :846-870 gives an input that is exactly its cached plus its
               written tokens, 40 and 60 (a blob-verified copy of the file at the pin, with its provenance, is kept at
               /Users/javrodher/aegis-builds/codex-responses-pin-20261026/).
               So: input_tokens = input - cached - written,
               cache_read_input_tokens = cached, cache_creation_input_tokens = written, output_tokens = output. The
               model is the call's turn's turn_context model (the rollout's requested model): exec records no served
               model per call, so a take whose stream recorded a reroute (the ledger's served_model) is not assembled
               call by call. cache_write_durations is None: Codex records no write duration, so costs.py prices every
               write at the 12h row, the stated bound (the price table's lead ruling 2), and says so.
  gemini       one per replayed gemini message with tokens (gemini_session_replay.replay of the last retained
               snapshot): the CLI writes the API response's usageMetadata there (@google/gemini-cli 0.64.0,
               bundle/chunk-NR7L3FXV.js:286950-286973). input is promptTokenCount, which holds the cached tokens
               (the CLI's own input = prompt - cached, :287474); thoughts are priced at the output row (Google's page:
               "Output price (including thinking tokens)"). So: input_tokens = input - cached,
               cache_read_input_tokens = cached, output_tokens = output + thoughts; Gemini records no cache write, so
               that class is absent. A call with tool-use prompt tokens (tool > 0) has no row the approved table
               names for them, so it is never priced on a guess: its take is assembled as one unmeasured call.
  Each vendor call also carries `recorded`, the counts as the vendor wrote them, and `unrecorded`, the fields of the
  call shape the vendor does not record (UNRECORDED), which stay None, never 0.

COMPLETE OR UNMEASURED. A take's calls are summed by costs.account only when every call was read: otherwise the take
carries one call, of its requested model, with usage None (an UNMEASURED call), so its vendor's priced total, and the
round-wide usage and priced total costs.account reads, are unmeasured, never a partial sum (costs.py: "Missing
measurements remain unmeasured, never zero"). That happens when
  claude-code  the ledger's cost is None (no session file, or its cost reader refused it);
  codex        a record off its shape, a running total (thread_token_usage, turn_token_usage) that is not the sum of
               the records before it, a turn whose exec stream printed no turn.completed, or one whose total (the
               thread's running total at that turn, as exec prints it) is not the records' sum to the end of that
               turn; the rollout or a stream that the readers refuse; a recorded reroute;
  gemini       a turn whose stream holds no result stats, per-model sums of input, output, cached and total that are
               not the stats' (stats.models: the CLI's telemetry counts every response, the session file only those
               it recorded on a message; the stats carry no thoughts or tool count, but their total_tokens sums the
               messages' totals, chunk-NR7L3FXV.js:287470 and :383045, so thoughts and tool-use tokens are checked
               together through the total, never apart), a tokens record with no model or with tool-use prompt
               tokens, or a snapshot the replay refuses;
  any harness  a take folder with turn streams and no driver ledger; and, when the outcome does not say its drive
               never started (drive_started not False), a take with no folder, or no ledger and no turn streams.
Standard library only. No model, vendor, network or credential is touched.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import codex_adapter  # noqa: E402
import codex_native  # noqa: E402
import gemini_adapter  # noqa: E402
import gemini_session_replay  # noqa: E402
import mode_binding  # noqa: E402
import native_snapshot  # noqa: E402
import vendor_provenance  # noqa: E402

CALLS = HERE / "cost-calls.json"
LEDGER = "driver-ledger.json"
VENDOR = {"claude-code": "anthropic", "codex": "openai", "gemini": "google"}
CALL_KEYS = ("vendor", "call_id", "model", "agent", "usage", "total_cost_usd", "started_at", "ended_at",
             "cache_write_durations")
# The fields of the call shape each vendor's per-call record does not hold: None, never 0.
UNRECORDED = {
    "openai": ("total_cost_usd", "started_at", "ended_at", "cache_write_durations"),
    "google": ("total_cost_usd", "started_at", "ended_at", "cache_write_durations", "cache_creation_input_tokens"),
}
CODEX_USAGE = ("input_tokens", "cached_input_tokens", "cache_write_input_tokens", "output_tokens",
               "reasoning_output_tokens", "total_tokens")
CODEX_RECORD_KEYS = ("thread_id", "turn_id", "session_id", "root_turn_id", "response_id", "usage", "turn_token_usage",
                     "thread_token_usage")
GEMINI_TOKENS = ("input", "output", "cached", "thoughts", "tool", "total")
GEMINI_CHECKED = (("input", "input_tokens"), ("output", "output_tokens"), ("cached", "cached"),
                  ("total", "total_tokens"))
UNMEASURED = "unmeasured"


class CostUnread(ValueError):
    """A take's calls cannot all be read or checked complete: the take is assembled as UNMEASURED calls."""


def _count(v) -> bool:
    return type(v) is int and v >= 0


def _call(vendor, call_id, model, agent, usage, recorded):
    return {"vendor": vendor, "call_id": call_id, "model": model, "agent": dict(agent), "usage": usage,
            "total_cost_usd": None, "started_at": None, "ended_at": None, "cache_write_durations": None,
            "recorded": recorded, "unrecorded": list(UNRECORDED[vendor])}


def unmeasured(vendor, take_key, model, agent, why) -> dict:
    """The one call that stands for a take's unread calls: usage None, so costs.account reads the
    vendor's priced total as unmeasured; `why` says what could not be read."""
    return {"vendor": vendor, "call_id": f"{take_key}/{UNMEASURED}/{model}", "model": model, "agent": dict(agent),
            "usage": None, "total_cost_usd": None, "started_at": None, "ended_at": None,
            "cache_write_durations": None, "recorded": None, "unrecorded": list(UNMEASURED_FIELDS), UNMEASURED: why}


UNMEASURED_FIELDS = ("usage", "total_cost_usd", "started_at", "ended_at", "cache_write_durations")


def _snapshot(folder: Path, ledger: dict) -> bytes:
    refs = ledger.get("native_snapshots")
    if not isinstance(refs, list) or not refs:
        raise CostUnread("the take retained no native snapshot")
    try:
        return vendor_provenance.referenced_bytes(folder / native_snapshot.SESSION_DIR, refs[-1])
    except vendor_provenance.ProvenanceRefused as e:
        raise CostUnread(f"the last native snapshot: {e}") from None


def _streams(folder: Path, ledger: dict) -> list:
    names = ledger.get("streams")
    if not isinstance(names, list) or not names:
        raise CostUnread("the ledger names no turn streams")
    out = []
    for n, name in enumerate(names, 1):
        if name != f"turn-{n}.jsonl":
            raise CostUnread(f"stream {n} is {name!r}, not turn-{n}.jsonl")
        try:
            out.append((folder / name).read_text(encoding="utf-8", errors="surrogateescape"))
        except OSError as e:
            raise CostUnread(f"{name}: {e}") from None
    return out


# ---- codex ----------------------------------------------------------------------------------------------------------
def codex_usage(u: dict) -> dict:
    """costs.CLASSES from one Responses API usage (module docstring); CostUnread when the parts exceed the whole or
    total_tokens is not input + output."""
    if not isinstance(u, dict) or set(u) != set(CODEX_USAGE) or not all(_count(u[k]) for k in CODEX_USAGE):
        raise CostUnread(f"a usage is not exactly the counts {CODEX_USAGE}")
    fresh = u["input_tokens"] - u["cached_input_tokens"] - u["cache_write_input_tokens"]
    if fresh < 0 or u["reasoning_output_tokens"] > u["output_tokens"]:
        raise CostUnread("a usage's parts exceed its whole (cached and written input, or reasoning output)")
    if u["total_tokens"] != u["input_tokens"] + u["output_tokens"]:
        raise CostUnread("a usage's total_tokens is not input_tokens + output_tokens")
    return {"input_tokens": fresh, "output_tokens": u["output_tokens"],
            "cache_read_input_tokens": u["cached_input_tokens"],
            "cache_creation_input_tokens": u["cache_write_input_tokens"]}


def _add(total: dict, u: dict) -> dict:
    return {k: total.get(k, 0) + u[k] for k in CODEX_USAGE}


def running_totals_hold(pay: dict, thread: dict, turn: dict) -> bool:
    """A record's thread_token_usage and turn_token_usage are the sums of the records up to and including it."""
    return pay["thread_token_usage"] == thread and pay["turn_token_usage"] == turn


def turn_total_holds(printed: dict, running: dict) -> bool:
    """The exec's turn.completed usage (the thread's running total) is the records' sum to the end of that turn."""
    return {k: running.get(k, 0) for k in printed} == printed


def reroute_problem(ledger: dict):
    """Why a Codex take's calls have no recorded model each (a reroute on its stream), or None."""
    for k, s in enumerate(ledger.get("served_model") or [], 1):
        if isinstance(s, dict) and s.get("value") is not None:
            return f"turn {k}'s stream recorded a reroute to {s['value']!r}: which calls it served is not recorded"
    return None


def codex_calls(folder: Path, ledger: dict) -> list:
    """The take's Codex calls (module docstring), or CostUnread."""
    agent, model = ledger["agent"], ledger.get("model_requested")
    why = reroute_problem(ledger)
    if why is not None:
        raise CostUnread(why)
    raw = _snapshot(folder, ledger)
    try:
        rollout = codex_native.read_rollout(raw)
    except codex_native.ReaderRefused as e:
        raise CostUnread(f"the rollout reader refused the snapshot: {e}") from None
    turns = rollout["turns"]
    order = {t["turn_id"]: k for k, t in enumerate(turns)}
    for t in turns:
        if t["requested_model"] != model:
            raise CostUnread(f"turn {t['turn_id']} requested {t['requested_model']!r}, not the take's {model!r}")
    calls, seen, thread, per_turn, at_end = [], set(), {}, {}, {}
    for line in raw.decode("utf-8").split("\n"):
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("type") != "token_usage_record":
            continue
        pay = rec.get("payload")
        if not isinstance(pay, dict) or set(pay) != set(CODEX_RECORD_KEYS):
            raise CostUnread(f"a token_usage_record is not exactly {CODEX_RECORD_KEYS}")
        rid, tid = pay["response_id"], pay["turn_id"]
        if pay["thread_id"] != rollout["session_id"] or tid not in order:
            raise CostUnread(f"token_usage_record {rid!r} names another thread or no turn of the rollout")
        if not isinstance(rid, str) or not rid or rid in seen:
            raise CostUnread(f"token_usage_record response_id {rid!r} is empty or repeated")
        seen.add(rid)
        usage = codex_usage(pay["usage"])
        thread = _add(thread, pay["usage"])
        per_turn[tid] = _add(per_turn.get(tid, {}), pay["usage"])
        if not running_totals_hold(pay, thread, per_turn[tid]):
            raise CostUnread(f"token_usage_record {rid!r}: the running totals are not the sum of the records "
                             f"before it (a call's record is missing)")
        at_end[tid] = dict(thread)
        calls.append(_call("openai", rid, turns[order[tid]]["requested_model"], agent, usage, dict(pay["usage"])))
    streams = _streams(folder, ledger)
    if len(streams) != len(turns):
        raise CostUnread(f"{len(streams)} exec streams and {len(turns)} rollout turns")
    running = {}
    for n, (text, t) in enumerate(zip(streams, turns), 1):
        try:
            got = codex_adapter.read_stream(text, model=model)
        except codex_adapter.StreamError as e:
            raise CostUnread(f"turn {n}'s stream: {e}") from None
        running = at_end.get(t["turn_id"], running)
        if got["usage"] is None:
            raise CostUnread(f"turn {n}'s exec printed no turn.completed: its calls cannot be checked complete")
        if not turn_total_holds(got["usage"], running):
            raise CostUnread(f"turn {n}'s exec total is not the records' sum to the end of that turn")
    return calls


# ---- gemini ---------------------------------------------------------------------------------------------------------
def gemini_usage(tokens: dict):
    """costs.CLASSES from one gemini message's tokens (module docstring), or None when it holds tool-use prompt
    tokens (no row names them); CostUnread when the record is off its shape."""
    if not isinstance(tokens, dict) or set(tokens) != set(GEMINI_TOKENS) or not all(
            _count(tokens[k]) for k in GEMINI_TOKENS):
        raise CostUnread(f"a tokens record is not exactly the counts {GEMINI_TOKENS}")
    if tokens["cached"] > tokens["input"]:
        raise CostUnread("a tokens record's cached exceeds its input")
    if tokens["tool"]:
        return None
    return {"input_tokens": tokens["input"] - tokens["cached"], "output_tokens": tokens["output"] + tokens["thoughts"],
            "cache_read_input_tokens": tokens["cached"]}


def gemini_calls(folder: Path, ledger: dict) -> list:
    """The take's Gemini calls (module docstring), or CostUnread."""
    agent, model = ledger["agent"], ledger.get("model_requested")
    raw = _snapshot(folder, ledger)
    try:
        messages = gemini_session_replay.replay(raw)["messages"]
    except gemini_session_replay.ReplayRefused as e:
        raise CostUnread(f"the session replay refused the snapshot: {e}") from None
    calls, sums = [], {}
    for m in messages:
        if m.get("type") != "gemini" or m.get("tokens") is None:
            continue
        if not isinstance(m.get("model"), str) or not m["model"]:
            raise CostUnread(f"gemini message {m.get('id')!r} records tokens and no model")
        usage = gemini_usage(m["tokens"])
        s = sums.setdefault(m["model"], dict.fromkeys(GEMINI_TOKENS, 0))
        for k in GEMINI_TOKENS:
            s[k] += m["tokens"][k]
        calls.append(_call("google", m["id"], m["model"], agent, usage, dict(m["tokens"])))
    stats_sums = {}
    for n, text in enumerate(_streams(folder, ledger), 1):
        try:
            got = gemini_adapter.read_stream(text, model=model)
        except gemini_adapter.StreamError as e:
            raise CostUnread(f"turn {n}'s stream: {e}") from None
        if got["stats"] is None:
            raise CostUnread(f"turn {n}'s stream holds no result stats: its calls cannot be checked complete")
        for name, entry in got["stats"]["models"].items():
            s = stats_sums.setdefault(name, {})
            for _, key in GEMINI_CHECKED:
                s[key] = s.get(key, 0) + entry[key]
    for name in sorted(set(stats_sums) | set(sums)):
        if not stats_agree(sums.get(name, {}), stats_sums.get(name, {})):
            raise CostUnread(f"{name}: the session file's input, output, cached and total sums are not the result "
                             f"stats' (the session file records {len([c for c in calls if c['model'] == name])} "
                             f"calls)")
    why = unpriced_problem(calls)
    if why is not None:
        raise CostUnread(why)
    return calls


def stats_agree(mine: dict, theirs: dict) -> bool:
    """One model's session-file sums of input, output, cached and total equal its result stats' sums over the turns
    (the total holds the thoughts and tool-use tokens, which the stats do not count apart)."""
    return all(mine.get(a, 0) == theirs.get(b, 0) for a, b in GEMINI_CHECKED)


def unpriced_problem(calls: list):
    """Why a take holds a call no approved row prices (usage None: tool-use prompt tokens), or None. Such a take is one
    unmeasured call, never a take of measured calls beside an unpriced one (review aa4394c NIT-1)."""
    bad = [c["call_id"] for c in calls if c["usage"] is None]
    if bad:
        return f"{len(bad)} call(s) record tool-use prompt tokens, which no approved row prices (first {bad[0]!r})"
    return None


# ---- the take and the assembly --------------------------------------------------------------------------------------
READERS = {"codex": codex_calls, "gemini": gemini_calls}


def drive_may_have_started(outcome) -> bool:
    """Review aa4394c MINOR-2: only an outcome that says its drive never started (drive_started False, batch.py:103)
    can stand for a take that made no call; a missing outcome or any other value may have made calls."""
    return outcome is None or outcome.get("drive_started") is not False


def take_calls(folder, row: dict, outcome=None) -> list:
    """One take's calls (module docstring): its readable calls, or UNMEASURED calls naming why. `outcome` is the take's
    committed outcome (None: not known, read as a drive that may have started)."""
    folder = Path(folder)
    key = f"{mode_binding.TAKES_DIR}/{row['slot']}/{row['attempt']}"
    path = folder / LEDGER
    if not path.is_file():
        ran = sorted(p.name for p in folder.glob("turn-*.jsonl")) if folder.is_dir() else []
        harness = row["agent"]["harness"]
        if not ran:
            if not drive_may_have_started(outcome):
                return []                                  # the drive never started: the take made no call
            where = f"holds no {LEDGER} and no turn streams" if folder.is_dir() else "is missing"
            return [unmeasured(VENDOR[harness], key, row["model"], row["agent"],
                               f"the outcome's drive_started is {(outcome or {}).get('drive_started')!r} and the take "
                               f"folder {where}")]
        return [unmeasured(VENDOR[harness], key, row["model"], row["agent"],
                           f"turn streams {ran} and no {LEDGER}")]
    ledger = json.loads(path.read_text(encoding="utf-8"))
    harness = ledger["agent"]["harness"]
    vendor = VENDOR[harness]
    if harness == "claude-code":
        cost = ledger.get("cost")
        if cost is None:
            return [unmeasured(vendor, key, ledger["model_requested"], ledger["agent"],
                               "the driver ledger's cost is None (no session file, or its cost reader refused it)")]
        return [dict(c) for c in cost["calls"]]
    try:
        return READERS[harness](folder, ledger)
    except CostUnread as e:
        return [unmeasured(vendor, key, ledger["model_requested"], ledger["agent"], str(e))]
    except (ValueError, OSError) as e:                     # any other failure to read is unmeasured, never a pass
        return [unmeasured(vendor, key, ledger["model_requested"], ledger["agent"], f"{type(e).__name__}: {e}")]


def outcome_keys(history: list) -> list:
    """(slot, attempt) of every committed outcome, once each, in commit order (rulings are not outcomes)."""
    import batch
    out = []
    for o in history:
        if batch.is_outcome(o) and (o["slot"], o["attempt"]) not in out:
            out.append((o["slot"], o["attempt"]))
    return out


def assemble(rows: list, history: list, *, root=HERE) -> list:
    """Every committed outcome's take, once, in commit order, its calls concatenated."""
    registered = {(r["slot"], r["attempt"]): r for r in rows}
    import batch
    first = {}
    for o in history:
        if batch.is_outcome(o):
            first.setdefault((o["slot"], o["attempt"]), o)
    out = []
    for slot, attempt in outcome_keys(history):
        out += take_calls(Path(root) / mode_binding.TAKES_DIR / str(slot) / str(attempt), registered[(slot, attempt)],
                          first.get((slot, attempt)))
    return out


def render(calls: list) -> str:
    return json.dumps(calls, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    import takes
    try:
        rows, history = takes.load_rows(), takes.read_history()
        if not history:
            print("cost_calls: no takes; nothing assembled or written")
            return 0
        rel = (HERE / mode_binding.TAKES_DIR).relative_to(REPO).as_posix()
        if takes._git_at(REPO, "status", "--porcelain", "--", rel):
            raise ValueError("take folders have uncommitted changes")
        value = render(assemble(rows, history))
        if args.write:
            CALLS.write_text(value, encoding="utf-8")
        elif not CALLS.is_file() or CALLS.read_text(encoding="utf-8") != value:
            raise ValueError("cost-calls.json is not what this step assembles from the committed takes")
        print(f"cost_calls: {len(json.loads(value))} calls from {len(outcome_keys(history))} takes")
        return 0
    except (ValueError, KeyError, OSError) as e:
        print(f"cost_calls: REFUSE: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
