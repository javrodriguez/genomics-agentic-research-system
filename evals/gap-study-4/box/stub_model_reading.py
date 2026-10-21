#!/usr/bin/env python3
"""Lane vendor-b27 (glitch-f1's ruling 2, 21 Oct 2026): read a fetched stub-model probe folder with lane vendor-b26's
readers, unchanged, and print one line per scenario: the shape each snapshot showed, admitted or refused and why,
beside the design's prediction, and where the stub's log puts the masked, truncated and summary requests.

Mac only, light work, on a folder `walk_launch.py fetch-probe` landed. The readers come from --code, a study folder:
the design says a `git archive` of the reviewed B26 head (04c4e774 or its successor), never a fold clone; with no
--code, this file's own study folder. Nothing here changes a reader, writes a record or decides an admission: the
lines are evidence for glitch-f1's ruling and the follow-up reader lane (ruling 2).

What each scenario line reads, per scenario folder <probe>/<scenario>/:
  - every session/native-turn-<n>.jsonl through gemini_session_replay.replay: PASS with its properties, or the
    ReplayRefused reason;
  - the snapshot sequence through native_reader_registration.gemini_history (the byte-prefix invariant, then
    vendor_provenance.session_history_facts): joined, or the refusal;
  - stub/requests.jsonl: the first request carrying the masked tag, the truncation text and a state snapshot, the
    helper (generateContent) requests, any refused request, each placed in its CLI process by probe.json's process
    times;
  - scenario.json's `expect`: each snapshot's predicted verdict, compared with the observed one ("as predicted" or
    "DIFFERS").

    python3 -I -B evals/gap-study-4/box/stub_model_reading.py <probe folder> [--code <study folder>] [--json]
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent


READERS = ("gemini_session_replay", "native_reader_registration")


def _from(module, folder: Path) -> bool:
    f = getattr(module, "__file__", None)
    return bool(f) and Path(f).resolve().parent == folder


def load_readers(code: Path):
    """gemini_session_replay and native_reader_registration from the study folder `code`, leaving the process's
    sys.modules and sys.path exactly as they were (lane vendor-b27 stage 7: replacing the loaded readers in sys.modules
    split one battery process into two copies of the registry, so drive's and a later test's no longer agreed).

    When `code`'s readers are the ones already loaded, those same module objects are returned. Otherwise every module
    loaded from a study folder (this one or `code`) is set aside, the readers are imported with `code` first on
    sys.path, and sys.modules and sys.path are then restored; the returned modules keep their own copies of what they
    imported."""
    code = Path(code).resolve()
    loaded = [sys.modules.get(n) for n in READERS]
    if all(m is not None and _from(m, code) for m in loaded):
        return tuple(loaded)
    saved_modules, saved_path = dict(sys.modules), list(sys.path)
    studies = {code, HERE.resolve()}
    try:
        for name, module in list(sys.modules.items()):
            f = getattr(module, "__file__", None)
            if f and any(Path(f).resolve().is_relative_to(s) for s in studies):
                del sys.modules[name]
        sys.path.insert(0, str(code))
        replay = importlib.import_module("gemini_session_replay")
        nrr = importlib.import_module("native_reader_registration")
    finally:
        sys.modules.clear()
        sys.modules.update(saved_modules)
        sys.path[:] = saved_path
    if not _from(replay, code) or not _from(nrr, code):
        raise SystemExit(f"the readers did not load from {code}")
    return replay, nrr


def _turn(p: Path) -> int:
    return int(p.stem.rsplit("-", 1)[1])


def snapshots(folder: Path) -> list:
    return sorted((folder / "session").glob("native-turn-*.jsonl"), key=_turn)


def replay_verdicts(folder: Path, replay) -> list:
    out = []
    for p in snapshots(folder):
        try:
            got = replay.replay(p.read_bytes())
            out.append({"snapshot": _turn(p), "verdict": "PASS", "properties": got.get("properties")})
        except replay.ReplayRefused as e:
            out.append({"snapshot": _turn(p), "verdict": "refused", "reason": str(e)})
    return out


def history_verdict(folder: Path, nrr) -> dict:
    refs = [{"file": p.name, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in snapshots(folder)]
    if not refs:
        return {"verdict": "refused", "reason": "no snapshot"}
    try:
        facts = nrr.gemini_history(folder / "session", refs)
        return {"verdict": "joined", "interactions": len(facts)}
    except Exception as e:  # noqa: BLE001 - every reader refusal is evidence, named by its type and words
        return {"verdict": "refused", "reason": f"{type(e).__name__}: {e}"}


def stub_places(folder: Path) -> dict:
    """Where the stub's log puts the masked, truncated and summary requests, each placed in its CLI process."""
    log = folder / "stub" / "requests.jsonl"
    if not log.is_file():
        return {"log": "absent"}
    rows = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines() if x.strip()]
    procs = []
    probe = folder / "probe.json"
    if probe.is_file():
        procs = [(p["process"], p.get("started_at"), p.get("ended_at"))
                 for p in json.loads(probe.read_text(encoding="utf-8")).get("processes", [])]

    def where(row):
        for k, a, b in procs:
            if isinstance(a, (int, float)) and isinstance(b, (int, float)) and a <= row.get("at", -1) <= b:
                return f"request {row['n']} (process {k})"
        return f"request {row['n']}"

    def first(flag):
        hit = [r for r in rows if (r.get("flags") or {}).get(flag)]
        return where(hit[0]) if hit else None
    return {"requests": len(rows), "masked": first("masked_tag"), "truncation": first("truncation_text"),
            "state_snapshot": first("state_snapshot"),
            "helpers": [where(r) for r in rows if r.get("endpoint") == "generate"],
            "refused": [f"{where(r)}: {r.get('why')}" for r in rows if r.get("verdict") == "refused"]}


def compare(observed: list, expect: dict) -> list:
    out = []
    for o in observed:
        want = (expect or {}).get(str(o["snapshot"]))
        if want is None:
            out.append("unpredicted")
        elif want["verdict"] == "PASS":
            out.append("as predicted" if o["verdict"] == "PASS" else "DIFFERS")
        elif not want.get("reason_contains"):        # "" is in every reason (REVIEW-vendor-b27-25ffff5 NIT 8)
            out.append("DIFFERS (the prediction names no reason)")
        else:
            ok = o["verdict"] == "refused" and want["reason_contains"] in o.get("reason", "")
            out.append("as predicted" if ok else "DIFFERS")
    return out


# glitch-f1's ruling 3 and REVIEW-vendor-b27-25ffff5 MINOR 6: every reading names the probe workspace's differences
# from a walk's (box/stub_model_probe.py DEPARTURES says the same)
WORKSPACE_DIFFERENCES = ("content only: the probe's run tree holds .stub-probe/ (the stub's copy, its script, its log) "
                         "and the scenario's synthetic files; it is not a git checkout (a walk's is the pinned "
                         "checkout); and it has no GEMINI.md (a walk places the instruction file)")


def read_scenario(folder: Path, replay, nrr) -> dict:
    scenario = json.loads((folder / "scenario.json").read_text(encoding="utf-8")) \
        if (folder / "scenario.json").is_file() else {}
    observed = replay_verdicts(folder, replay)
    history = history_verdict(folder, nrr)
    expect = (scenario.get("expect") or {}).get("snapshots") or {}
    marks = compare(observed, expect)
    last = observed[-1] if observed else {"verdict": "refused", "reason": "no snapshot"}
    if last["verdict"] == "PASS" and history["verdict"] == "joined":
        outcome = "admitted"
    else:
        outcome = "refused: " + (last.get("reason") if last["verdict"] != "PASS" else history.get("reason", ""))
    return {"scenario": folder.name, "observed": observed, "history": history, "predicted": expect, "marks": marks,
            "outcome": outcome, "stub": stub_places(folder), "workspace_differences": WORKSPACE_DIFFERENCES,
            "processes_expected": len(scenario.get("processes") or []), "snapshots_seen": len(observed)}


def line(r: dict) -> str:
    snaps = "; ".join(f"{o['snapshot']} " + ("PASS" + (f" {o['properties']}" if o.get("properties") else "")
                                             if o["verdict"] == "PASS" else f"refused: {o['reason']}") + f" [{m}]"
                      for o, m in zip(r["observed"], r["marks"]))
    stub = r["stub"]
    places = ", ".join(f"{k} {v}" for k, v in (("masked", stub.get("masked")), ("truncation", stub.get("truncation")),
                                               ("snapshot", stub.get("state_snapshot"))) if v)
    extra = f"; helpers {len(stub.get('helpers') or [])}" if stub.get("helpers") else ""
    held = f"; stub refused {stub['refused']}" if stub.get("refused") else ""
    short = "" if r["snapshots_seen"] == r["processes_expected"] else \
        f"; only {r['snapshots_seen']} of {r['processes_expected']} snapshots"
    return (f"{r['scenario']}: {r['outcome']} | snapshots: {snaps or 'none'} | history: {r['history']['verdict']}"
            f" | stub: {places or 'no flagged request'}{extra}{held}{short}")


def read_probe(probe: Path, code: Path) -> list:
    replay, nrr = load_readers(code)
    return [read_scenario(d, replay, nrr) for d in sorted(Path(probe).iterdir())
            if d.is_dir() and ((d / "session").is_dir() or (d / "scenario.json").is_file())]


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="read a stub-model probe folder with lane vendor-b26's readers")
    p.add_argument("probe")
    p.add_argument("--code", default=str(HERE))
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    results = read_probe(Path(a.probe), Path(a.code))
    if not a.json:
        print(f"workspace differences from a walk: {WORKSPACE_DIFFERENCES}")
    for r in results:
        print(json.dumps(r, sort_keys=True, default=str) if a.json else line(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
