#!/usr/bin/env python3
"""cost-calls.json, assembled from every committed take's own records, so costs.py accounts every arm.

Lane pf1-cost-vendors (Gap Study round 4, Mon 26 Oct 2026; the lane orchestrator glitch-f1's assignment: the gap the
L4-close lane named, "no step assembles cost-calls.json", and arm O and arm G takes that record no cost).

    python3 -B evals/gap-study-4/cost_calls.py --write     (after the freeze: cost-calls.json is run output)
    python3 -B evals/gap-study-4/cost_calls.py --check     (cost-calls.json is what this step assembles)

THE TAKES. Every committed outcome of takes.read_history(), once per (slot, attempt), in commit order; its take folder
is takes/<slot>/<attempt>/ (run.committed_evidence's road). A walk (rehearsals/) is never a take and never assembled.

THE CALLS, in costs.py's call shape {vendor, call_id, model, agent{harness, version}, usage, total_cost_usd,
started_at, ended_at, cache_write_durations}, usage in costs.CLASSES, which are disjoint (costs.prompt_tokens); an
arm A sub-agent's call also carries `subagent`, the ledger's agent_id for the file it was read from:
  claude-code  the driver ledger's cost.calls, as drive.py wrote them (claude_code_adapter.cost_record), unchanged,
               then the calls of each sub-agent file the take copied (lane gap-subagent-cost, 28 Oct 2026, the lane
               orchestrator glitch-45's ruling (b) on the D8 claude-code read's finding 1). cost_record reads the main
               session file alone, so a take whose agent called the Agent tool held only its main thread's calls (on
               walk w255, 20 of 40 calls; w260, 5 of 34). DELEGATION (glitch-45's ruling on review edb48b6, MAJOR 1,
               option (c)): a take delegated when a sub-agent file was copied (named by the ledger or present under
               subagents/) or its main session file holds an Agent tool_use; a take that did not is priced from its
               ledger's calls alone, exactly as before this lane, a cut or timed-out turn included, and nothing below
               runs. For a delegating take, subagent_calls reads every `.jsonl` entry of the ledger's `subagents`,
               at any depth below subagents/ as drive.copy_subagent_files keeps it (subagents/**/agent-<id>.jsonl),
               its bytes bound by the entry's sha256, one call per (message.id, requestId) of its assistant records
               with a usage, API-error records skipped as claude_code_adapter.session_calls skips them. Unlike the
               session file, a sub-agent file writes one call as several
               fragments whose output_tokens grow while the other classes stay put (at 2.1.296, 20 of 20 calls in
               w255's, 29 of 29 in w260's), so THE FRAGMENT RULE: across one call's fragments the model, the input,
               cache-read and cache-write counts and the 5m/1h split are equal and output never decreases, and the
               last fragment is kept; anything else refuses. The split is claude_code_adapter.cache_write_split's,
               imported, never edited (the adapter is checker code). Then RECONCILE: the four classes summed over all
               the calls, per model, must equal the last turn's modelUsage that is not None (a running total of the
               whole session, sub-agents included); a delegating take whose turns carry none, whose calls do not
               reconcile (a cut or timed-out last turn included), or whose session calls Agent with no sub-agent file
               copied, is unmeasured. The 5m/1h split is priced as recorded and is not reconciled: modelUsage prints
               no split, and its costUSD is not used as a check (the CLI's built-in prices may differ from the frozen
               table). A per-turn total_cost_usd in the ledger's cost.turns is the session's running total as the CLI
               prints it, which claude_code_adapter.py:47-48 does not say (editing it would move the checker digest):
               nothing here sums it, and no call carries a printed figure.
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
  claude-code  the ledger's cost is None (no session file, or its cost reader refused it); and for a delegating take
               (DELEGATION) only: its session file unreadable; an Agent tool_use with no sub-agent file copied; a
               sub-agent file that is missing, unnamed by the ledger, not of drive.py's admitted name, off its sha256
               or off the fragment rule; a call id in two files; a call whose usage is not four counts; calls that do
               not sum, per model and class, to the last modelUsage (a cut or timed-out last turn included); no
               modelUsage at all;
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
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import claude_code_adapter  # noqa: E402  (read only: cache_write_split, never edited here)
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


# ---- claude-code (lane gap-subagent-cost; module docstring) ---------------------------------------------------------
SUBAGENT_DIR = "subagents"
# drive.SUBAGENT_FILE, spelled here (drive.py is checker code and not imported); a test binds the two.
SUBAGENT_FILE = re.compile(r"agent-([A-Za-z0-9_-]{1,64})\.jsonl")
AGENT_TOOL = "Agent"            # check_take.AGENT_TOOL, transcript_view's one DELEGATE tool; a test binds the two
# The classes a later fragment of one sub-agent call must repeat exactly; output_tokens may only grow.
FRAGMENT_FIXED = ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
# modelUsage's names for costs.CLASSES (the CLI's result record, per model, a running total of the session).
MODEL_USAGE_KEYS = {"input_tokens": "inputTokens", "output_tokens": "outputTokens",
                    "cache_read_input_tokens": "cacheReadInputTokens",
                    "cache_creation_input_tokens": "cacheCreationInputTokens"}
CLAUDE_CLASSES = tuple(MODEL_USAGE_KEYS)


def api_error(rec: dict) -> bool:
    """The harness's API-error record, never a model call: session_calls' own skip, both halves (the camel-case flag
    the session file writes, and claude_code_adapter._is_api_error: its is_api_error_message flag or the synthetic
    model); read only, the adapter is checker code."""
    return rec.get("isApiErrorMessage") is True or claude_code_adapter._is_api_error(rec)


def fragment_holds(kept: dict, new: dict) -> bool:
    """THE FRAGMENT RULE: a later fragment of one call has the kept fragment's model, input, cache-read and cache-write
    counts and 5m/1h split, and an output count no lower than the kept one's."""
    return (new["model"] == kept["model"] and new["cache_write_durations"] == kept["cache_write_durations"]
            and all(new["usage"][k] == kept["usage"][k] for k in FRAGMENT_FIXED)
            and new["usage"]["output_tokens"] >= kept["usage"]["output_tokens"])


def subagent_file_calls(text: str, agent: dict, agent_id, name: str) -> list:
    """One sub-agent file's calls, one per (message.id, requestId), the last fragment of each kept (THE FRAGMENT RULE),
    in costs.py's call shape plus `subagent` (the ledger's agent_id); CostUnread on any departure. The text is split on
    newline only; API-error records are skipped as claude_code_adapter.session_calls skips them."""
    by, order = {}, []
    for n, line in enumerate(text.split("\n"), 1):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except ValueError:
            raise CostUnread(f"{name} line {n} is not JSON") from None
        if not isinstance(rec, dict) or rec.get("type") != "assistant":
            continue
        if api_error(rec):
            continue
        msg = rec.get("message")
        if not isinstance(msg, dict) or not isinstance(msg.get("usage"), dict):
            continue
        key = (msg.get("id"), rec.get("requestId"))
        if not all(isinstance(k, str) and k for k in key):
            raise CostUnread(f"{name} line {n}: a usage with no (message.id, requestId) key")
        counts = {c: msg["usage"].get(c) for c in CLAUDE_CLASSES}
        if not all(_count(v) for v in counts.values()):
            raise CostUnread(f"{name} line {n}: call {key[0]}'s usage is not four counts {CLAUDE_CLASSES}")
        if not isinstance(msg.get("model"), str) or not msg["model"]:
            raise CostUnread(f"{name} line {n}: call {key[0]} names no model")
        frag = {"model": msg["model"], "usage": counts,
                "cache_write_durations": claude_code_adapter.cache_write_split(msg["usage"], counts)}
        if key in by:
            if not fragment_holds(by[key], frag):
                raise CostUnread(f"{name} line {n}: call {key[0]}'s fragments break the fragment rule (model, input, "
                                 f"cache counts or split differ, or output decreases)")
        else:
            order.append(key)
        by[key] = frag
    return [{"vendor": "anthropic", "call_id": f"{m}/{r}", "model": by[(m, r)]["model"], "agent": dict(agent),
             "usage": by[(m, r)]["usage"], "total_cost_usd": None, "started_at": None, "ended_at": None,
             "cache_write_durations": by[(m, r)]["cache_write_durations"], "subagent": agent_id}
            for m, r in order]


def subagent_calls(folder: Path, ledger: dict) -> tuple:
    """(the calls of every sub-agent file the ledger names, the files read). Each `.jsonl` entry of the ledger's
    `subagents` is read from the take folder and its bytes must hash to the entry's sha256; the `.jsonl` files under
    subagents/ must be exactly the ones named. CostUnread otherwise."""
    entries = ledger.get("subagents") or []
    if not isinstance(entries, list):
        raise CostUnread("the ledger's subagents is not a list")
    calls, named = [], []
    for e in entries:
        if not isinstance(e, dict) or not isinstance(e.get("file"), str):
            raise CostUnread("a ledger subagents entry names no file")
        if not e["file"].endswith(".jsonl"):
            continue
        if not admitted_path(e["file"]):
            raise CostUnread(f"sub-agent file {e['file']!r} is not a {SUBAGENT_DIR}/**/agent-<id>.jsonl path")
        try:
            raw = (folder / e["file"]).read_bytes()
        except OSError as err:
            raise CostUnread(f"sub-agent file {e['file']}: {err}") from None
        if not bytes_bound(raw, e):
            raise CostUnread(f"sub-agent file {e['file']}'s bytes are not the ledger's sha256")
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            raise CostUnread(f"sub-agent file {e['file']} is not UTF-8") from None
        calls += subagent_file_calls(text, ledger["agent"], e.get("agent_id"), e["file"])
        named.append(e["file"])
    if not files_match(folder, named):
        raise CostUnread(f"the sub-agent files under {SUBAGENT_DIR}/ {subagent_files(folder)} are not the ledger's "
                         f"{sorted(named)}")
    return calls, named


def bytes_bound(raw: bytes, entry: dict) -> bool:
    """A sub-agent file's bytes hash to its ledger entry's sha256."""
    return hashlib.sha256(raw).hexdigest() == entry.get("sha256")


def admitted_path(rel: str) -> bool:
    """A ledger path drive.copy_subagent_files can write: subagents/, then any depth of plain folder names, then
    agent-<id>.jsonl (SUBAGENT_FILE); never `.`, `..` or an empty part."""
    parts = rel.split("/")
    return (len(parts) >= 2 and parts[0] == SUBAGENT_DIR and all(x not in ("", ".", "..") for x in parts)
            and SUBAGENT_FILE.fullmatch(parts[-1]) is not None)


def files_match(folder: Path, named: list) -> bool:
    """The `.jsonl` files under subagents/ are exactly the ledger's (none unnamed, none named twice)."""
    return subagent_files(folder) == sorted(named)


def subagent_files(folder: Path) -> list:
    """The `.jsonl` files at any depth under the take folder's subagents/, as ledger paths, sorted; a symlink there
    refuses (drive.py copies none)."""
    sub = folder / SUBAGENT_DIR
    if not sub.is_dir():
        return []
    out = []
    for p in sorted(sub.rglob("*")):
        if p.is_symlink():
            raise CostUnread(f"{SUBAGENT_DIR}/{p.relative_to(sub).as_posix()} is a symlink")
        if p.is_file() and p.name.endswith(".jsonl"):
            out.append(f"{SUBAGENT_DIR}/{p.relative_to(sub).as_posix()}")
    return sorted(out)


def model_key(model):
    """The key RECONCILE sums under: the model id itself, so the calls of one model are checked against that model's
    modelUsage, never pooled with another's."""
    return model


def reconcile(calls: list, turns: list, *, has_sub: bool) -> None:
    """RECONCILE: the calls' four classes, summed per model, equal the last turn's modelUsage that is not None (the
    session's running total). With no modelUsage at all, a take with a sub-agent file is CostUnread (claude_calls
    passes has_sub True for every delegating take; a take that did not delegate never reaches here). CostUnread on any
    departure: a take is never priced from a partial sum."""
    usages = [t.get("model_usage") for t in turns if isinstance(t, dict) and t.get("model_usage") is not None]
    if not usages:
        if has_sub:
            raise CostUnread("a take with a sub-agent file whose turns print no modelUsage: its calls cannot be "
                             "checked complete")
        return
    theirs = {}
    if not isinstance(usages[-1], dict) or not usages[-1]:
        raise CostUnread("the last modelUsage is not a non-empty object")
    for model, entry in usages[-1].items():
        if not isinstance(entry, dict) or not all(_count(entry.get(v)) for v in MODEL_USAGE_KEYS.values()):
            raise CostUnread(f"the last modelUsage of {model!r} does not hold four counts")
        s = theirs.setdefault(model_key(model), dict.fromkeys(CLAUDE_CLASSES, 0))
        for k, v in MODEL_USAGE_KEYS.items():
            s[k] += entry[v]
    mine = {}
    for c in calls:
        u = c.get("usage")
        if not isinstance(u, dict) or not all(_count(u.get(k)) for k in CLAUDE_CLASSES):
            raise CostUnread(f"call {c.get('call_id')!r}'s usage is not four counts: the calls cannot be reconciled")
        s = mine.setdefault(model_key(c.get("model")), dict.fromkeys(CLAUDE_CLASSES, 0))
        for k in CLAUDE_CLASSES:
            s[k] += u[k]
    if mine != theirs:
        raise CostUnread(f"the calls' sums per model {mine} are not the last modelUsage's {theirs}")


def ids_once(calls: list) -> bool:
    """No call id is recorded twice across the session file and the sub-agent files."""
    ids = [c.get("call_id") for c in calls]
    return len(set(ids)) == len(ids)


def agent_called(folder: Path, ledger: dict) -> bool:
    """The take's main session file (the ledger's `transcript`) holds an assistant tool_use of the Agent tool. A line
    that does not name Agent cannot hold one and is not parsed; one that does and is not a JSON object refuses
    (CostUnread), as does an unreadable file: delegation is never assumed away."""
    name = ledger.get("transcript")
    if not isinstance(name, str) or not name or "/" in name:
        raise CostUnread(f"the ledger names no session file ({name!r}), so delegation cannot be read")
    try:
        text = (folder / name).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise CostUnread(f"the session file {name}: {e}") from None
    for n, line in enumerate(text.split("\n"), 1):
        if AGENT_TOOL not in line:
            continue
        try:
            rec = json.loads(line)
        except ValueError:
            raise CostUnread(f"{name} line {n} names {AGENT_TOOL} and is not JSON") from None
        if not isinstance(rec, dict):
            raise CostUnread(f"{name} line {n} names {AGENT_TOOL} and is not a JSON object")
        if rec.get("type") == "assistant" and any(b.get("type") == "tool_use" and b.get("name") == AGENT_TOOL
                                                  for b in claude_code_adapter._blocks(rec)):
            return True
    return False


def ledger_named(ledger: dict) -> list:
    """The `.jsonl` paths the ledger's `subagents` names."""
    entries = ledger.get("subagents") or []
    if not isinstance(entries, list):
        raise CostUnread("the ledger's subagents is not a list")
    return [e.get("file") for e in entries if isinstance(e, dict) and str(e.get("file", "")).endswith(".jsonl")]


def delegates(named: list, on_disk: list, tool: bool) -> bool:
    """DELEGATION: a sub-agent file named or present, or an Agent tool_use in the session."""
    return bool(named or on_disk or tool)


def file_missing(tool: bool, files: list) -> bool:
    """An Agent tool_use whose sub-agent left no copied file: its calls cannot be read."""
    return tool and not files


def claude_calls(folder: Path, ledger: dict) -> list:
    """The take's Claude calls (module docstring): the ledger's cost calls unchanged; for a delegating take, then its
    sub-agent files' calls, reconciled; or CostUnread."""
    cost = ledger["cost"]
    if not isinstance(cost, dict) or not isinstance(cost.get("calls"), list) or not isinstance(cost.get("turns"), list):
        raise CostUnread("the driver ledger's cost holds no calls and turns lists")
    tool = agent_called(folder, ledger)
    if not delegates(ledger_named(ledger), subagent_files(folder), tool):
        return [dict(c) for c in cost["calls"]]                # as before this lane, a cut turn included
    sub, files = subagent_calls(folder, ledger)
    if file_missing(tool, files):
        raise CostUnread(f"the session calls {AGENT_TOOL} and no sub-agent file was copied: its calls cannot be read")
    calls = [dict(c) for c in cost["calls"]] + sub
    if not ids_once(calls):
        raise CostUnread("a call id is recorded twice (the session file and a sub-agent file, or two sub-agent files)")
    reconcile(calls, cost["turns"], has_sub=True)
    return calls


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
READERS = {"claude-code": claude_calls, "codex": codex_calls, "gemini": gemini_calls}


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
    if harness == "claude-code" and ledger.get("cost") is None:
        return [unmeasured(vendor, key, ledger["model_requested"], ledger["agent"],
                           "the driver ledger's cost is None (no session file, or its cost reader refused it)")]
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
