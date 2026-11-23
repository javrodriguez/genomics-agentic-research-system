#!/usr/bin/env python3
"""Rebuild reviews 4, 5 and 7's reports from their reviewers' real session files, on the operator's Mac.

    python3 evals/gap-study-4/review_kit/check_real_sessions.py

Lane fold5/report-binding (glitch-45's ruling of Sun 1 Nov 2026, under Javier's standing delegation): the sessions live
only under the operator's ~/.claude/projects, so this check is not a unittest (the battery bans silent skips,
test_round4.SKIP_ALLOWED). The orchestrator runs it on the Mac before each freeze step. For each round it prints the
digest review_kit/blindness.py rebuilds from the session file (its Write, then its Edits in order) beside the expected
one: review 4's as written (review_kit/prefreeze-4.as-written.md, 27f6afb8..., not the masked prefreeze-4.md) and
review 5's committed report (2a03d9dc...).

Review 7 (lane fold9/round7-residual): its reviewer ran one sed on the report, so blindness.py records no digest. Its one
Write must be the committed review_kit/prefreeze-7.as-written.md, and that text with the one edit commit_review's
UNBOUND_REPORTS names must be the report in the review folder (4538ce81...).

Exit 0 when both match, 1 on any mismatch, else 2 when a session file or review folder is absent. Read-only; stdlib only.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("review_kit_blindness_for_check", HERE / "blindness.py")
blindness = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(blindness)

# round -> (the review folder under ~/aegis-builds, the reviewer's session id, the expected digest, what it is)
ROUNDS = {
    4: ("pfr-20261031/round4", "46b6dc63-28c9-5e8c-8e06-1f5c363efa0f",
        "27f6afb8ae52e91bb5256ad508135b50d16a259322ccf902fcbce44fb47be9d8", "review_kit/prefreeze-4.as-written.md"),
    5: ("pfr-20261031b/round5", "66023ce5-1b0d-587f-a06a-f2ede76dd39f",
        "2a03d9dcca9f45cacad19b05bc26ead4ccf903fe3022889269d1188216e64892", "review_kit/prefreeze-5.md"),
}

# round -> (folder, session id, the one Write's sha256, the report's sha256, the edit's old and new bytes, the record)
EDITED_ROUNDS = {
    7: ("pfr-20261102b/round7", "8246e72f-2a60-5bb0-9854-0376a3e2e86d",
        "56bff23fa7a445a5849e47a6a50c03b3e82400317f7bf99646163121d9f1e9c4",
        "4538ce819faa156431b6d3a2d784991a880d74d7b287c264d1b606f4ed8833cf",
        b"  - This sound apart from", b"  - This is sound apart from", "prefreeze-7.as-written.md"),
}


def check(projects: Path = blindness.PROJECTS, builds: Path = Path.home() / "aegis-builds") -> int:
    mismatch = absent = False
    for n, (rel, sid, want, record) in ROUNDS.items():
        hits = sorted(projects.glob(f"*/{sid}.jsonl"))
        folder = (builds / rel).resolve()
        if len(hits) != 1 or not folder.is_dir():
            print(f"round {n}: ABSENT ({len(hits)} session file(s) for {sid}; folder present: {folder.is_dir()})")
            absent = True
            continue
        _reviewer, side = blindness.read_sessions(hits[0], folder)
        line = blindness.report_digest_line(hits[0], folder, side)
        got = line.removeprefix(blindness.REPORT_DIGEST) if line.startswith(blindness.REPORT_DIGEST) else None
        committed = hashlib.sha256((HERE / record.removeprefix("review_kit/")).read_bytes()).hexdigest()
        ok = got == want == committed
        print(f"round {n}: rebuilt {got or line} expected {want} committed {record} {committed} "
              f"{'MATCH' if ok else 'MISMATCH'}")
        mismatch |= not ok
    for n, (rel, sid, written, report, old, new, record) in EDITED_ROUNDS.items():
        hits = sorted(projects.glob(f"*/{sid}.jsonl"))
        folder = (builds / rel).resolve()
        if len(hits) != 1 or not (folder / f"prefreeze-{n}.md").is_file():
            print(f"round {n}: ABSENT ({len(hits)} session file(s) for {sid}; report present: {folder.is_dir()})")
            absent = True
            continue
        writes = [x["input"]["content"] for line in hits[0].read_text().splitlines()
                  for x in ((json.loads(line).get("message") or {}).get("content") or [])
                  if isinstance(x, dict) and x.get("type") == "tool_use" and x.get("name") == "Write"
                  and x["input"].get("file_path", "").endswith(f"prefreeze-{n}.md")]
        body = writes[0].encode() if len(writes) == 1 else b""
        ok = (len(writes) == 1 and hashlib.sha256(body).hexdigest() == written
              and hashlib.sha256((HERE / record).read_bytes()).hexdigest() == written and body.count(old) == 1
              and hashlib.sha256(body.replace(old, new)).hexdigest() == report
              == hashlib.sha256((folder / f"prefreeze-{n}.md").read_bytes()).hexdigest())
        print(f"round {n}: {len(writes)} Write(s); as written {written[:12]}; with the one edit {report[:12]}; "
              f"{'MATCH' if ok else 'MISMATCH'}")
        mismatch |= not ok
    return 1 if mismatch else 2 if absent else 0


if __name__ == "__main__":
    raise SystemExit(check())
