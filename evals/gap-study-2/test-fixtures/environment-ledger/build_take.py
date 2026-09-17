"""Graded takes WITH their environment records, built from the templates beside this file (CP3, fix 4).

A graded take cannot be a static file. Its session id is uuid5(namespace, the commit that introduced its row), so
it exists only once that commit does, and the project name, the source path and every record's `sessionId`
follow from it. So the three files here are templates (a number-fidelity control take on claude-opus-5 that
completes all three scripted lines, its driver ledger and its environment.json, schema 1, in the driver's shape)
and this module renders them for a row whose commit the caller has made:

    build_study(root, study_dir, pre, commit, takes=(1, 2, 3), lacking=(2,))

writes the rows one per commit through `commit(message) -> sha` and leaves each take in the folder its row names,
the take numbers in `lacking` without an environment record (and without the ledger's `environment` entry). The
instruction file the transcript records is the one in `root/gars/CLAUDE.md`, so the checker's content binding
reads the tree it is run in.

The record names no variable (names_present is empty) and every listed variable absent. Its credential source is
the draft's `environment_record.subscription_source`, or `fixture-source` while the draft pins none: a stand-in
that no harness reports, never a guess at the real value. Loaded by path by tests_environment_ledger.py and by
mutations.py; stdlib only, and it imports nothing of the study's, so it renders the same in any copy.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path

FIXTURE = Path(__file__).resolve().parent
ROW = {"task": "number-fidelity", "half": "control", "model": "claude-opus-5"}
STAND_IN_SOURCE = "fixture-source"


def load_pre(study_dir: Path) -> dict:
    frozen = study_dir / "prereg.json"
    return json.loads((frozen if frozen.is_file() else study_dir / "prereg-draft.json").read_text())


def session_id_for(pre: dict, row_commit: str) -> str:
    ns = uuid.uuid5(uuid.NAMESPACE_URL, pre["session_namespace"]["derived_from"])
    return str(uuid.uuid5(ns, row_commit))


def take_folder(study_dir: Path, take: int) -> Path:
    return study_dir / "transcripts" / ROW["task"] / ROW["half"] / ROW["model"] / str(take)


def existing_rows(study_dir: Path) -> list[dict]:
    """The rows the copied ledger already holds. After the first real row was committed (17 September 2026), a
    battery sandbox carried it in its base commit, and a test row written at index 0 was then 'introduced' by
    that base commit rather than by the row commit this builder makes; the take's records disagreed and the
    checker refused the unedited fixture. The test rows go after whatever is there."""
    p = study_dir / "takes.json"
    if not p.is_file():
        return []
    try:
        rows = json.loads(p.read_text()).get("rows") or []
    except (OSError, json.JSONDecodeError):
        return []
    return [r for r in rows if r.get("_test_row") is not True]


def write_rows(study_dir: Path, base: list[dict], takes) -> None:
    rows = base + [{**ROW, "take": k, "order_index": k, "fixture_sha": "x",
                    "environment_class": "claude-subscription-headless", "_test_row": True} for k in takes]
    (study_dir / "takes.json").write_text(json.dumps({"role": "test", "rows": rows}, indent=2) + "\n")


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def build_take(study_dir: Path, root: Path, pre: dict, *, row: int, take: int, row_commit: str,
               record: bool = True, api_key_source: str | None = None) -> Path:
    """One graded take for `row`, whose commit is `row_commit`, in the folder its row names."""
    block = pre["environment_record"]
    sid = session_id_for(pre, row_commit)
    project = "run-" + sid.replace("-", "")[:8]
    source = pre["source_by_fixture_kind"]["generated"].replace("{project}", project)
    source_value = api_key_source or block.get("subscription_source") or STAND_IN_SOURCE

    def render(name: str) -> str:
        return ((FIXTURE / name).read_text().replace("@@SESSION_ID@@", sid)
                .replace("@@SOURCE@@", source).replace("@@PROJECT@@", project))

    d = take_folder(study_dir, take)
    d.mkdir(parents=True, exist_ok=True)

    gars_claude = (root / "gars" / "CLAUDE.md").read_text()
    lines = []
    for raw in render("transcript.jsonl").splitlines():
        rec = json.loads(raw)
        att = rec.get("attachment") or {}
        if att.get("type") == "instructions":
            for f in att["files"]:
                f["content"] = gars_claude.rstrip("\n")
        lines.append(json.dumps(rec))
    t = d / "transcript.jsonl"
    t.write_text("\n".join(lines) + "\n")

    led = json.loads(render("driver-ledger.json"))
    led["row"] = row
    led["gars_tree_sha"] = pre["system_under_test"]["gars_tree_sha"]
    # ROUND 2, CP8 (rehearsal 4). Once the half's fixture is pinned, a take whose ledger records no fixture hash is
    # refused, so this take records the pin the pre-registration in force carries, in the driver's shape for a
    # generated fixture; unpinned (the draft), it records none and the checker notes that, as before.
    half = next(t for t in pre["tasks"] if t["id"] == ROW["task"])[ROW["half"]]
    fx = half.get("fixture") or {}
    if fx.get("sha256"):
        led["fixture"] = {"kind": fx.get("kind"), "variant": fx.get("variant"), "seed": fx.get("seed"),
                          "fixture_sha256": fx["sha256"]}
    led["published"]["sha256_after"] = _sha256(t)

    env = d / "environment.json"
    if record:
        rec = json.loads(render("environment.json"))
        rec["row"] = row
        rec["row_commit"] = row_commit
        rec["name_patterns"] = block["name_patterns"]
        for key in ("api_key_variables", "billing_route_variables", "subscription_token_variables"):
            rec[key] = {name: "absent" for name in block[key]}
        rec["credential_source"]["per_turn"] = [
            {"n": r["n"], "recovery": bool(r.get("recovery")), "exit": r.get("exit"), "apiKeySource": source_value}
            for r in led["turns"]]
        rec["credential_source"]["reported"] = source_value
        env.write_text(json.dumps(rec, indent=2) + "\n")
        led["environment"]["sha256"] = _sha256(env)
    else:
        env.unlink(missing_ok=True)
        del led["environment"]
    (d / "driver-ledger.json").write_text(json.dumps(led, indent=2) + "\n")
    return d


def build_study(root: Path, study_dir: Path, pre: dict, commit, *, takes=(1,), lacking=(),
                api_key_source: str | None = None) -> dict[int, Path]:
    """take number -> its folder: each row committed on its own, then its take left beside it."""
    out: dict[int, Path] = {}
    base = existing_rows(study_dir)
    for i, k in enumerate(takes):
        write_rows(study_dir, base, takes[:i + 1])
        row = len(base) + i
        sha = commit(f"take: row {row}")
        out[k] = build_take(study_dir, root, pre, row=row, take=k, row_commit=sha,
                            record=k not in lacking, api_key_source=api_key_source)
    return out
