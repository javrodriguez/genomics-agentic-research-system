#!/usr/bin/env python3
"""Commit a finished pre-freeze review as its reviewer's session wrote it, with its blindness record beside it.

    python3 evals/gap-study-4/review_kit/commit_review.py <review folder> <N>

Asserts before anything is copied: line 1 of the report is `prereg.json sha256: <the sha256 of the kit's prereg.json, the bytes the reviewer read>`; the
report carries no absolute path and names no person; its sha256 is the one the blindness record rebuilds from the
reviewer's own session (pre-freeze review 5, M1). Copies the report to
review_kit/prefreeze-<N>.md and the blindness record beside it, lints the commit message, and commits with
`git commit -F`. The commit lands exactly the two files, which is what freeze.py's review-commit rule reads.

Never pushes: the push goes through the scanned door, on the owner's grant.

THE RULING (pre-freeze review 2, MAJOR 3; lane fold2-lb): read_ruling, imported from freeze.py, is the one reader of a
report's ruling, here and in freeze.review_file_problems (so in run_builders.py rehearse too). Exactly one line
matching RULING gives that ruling; zero or several give AMBIGUOUS, which is never DO FREEZE. A report is never refused
for its ruling: it is committed unedited and the commit records the ruling read, "ambiguous" included, because a
refused report is in practice a voided round and a second draw of the review.
"""

from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY_DIR = HERE.parent
REPO = STUDY_DIR.parent.parent
sys.path.insert(0, str(STUDY_DIR))
import study  # noqa: E402
from freeze import AMBIGUOUS, REPORT_DIGEST_GRANDFATHERED, RULING, read_ruling  # noqa: E402,F401  (MAJOR 3: the one reader)
import importlib.util  # noqa: E402
_spec = importlib.util.spec_from_file_location("review_kit_blindness_for_commit", HERE / "blindness.py")
blindness = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(blindness)

# Pre-freeze review 5, M1 (lane fold5/report-binding, glitch-45's ruling 2): a host path names a real segment after its
# root. A placeholder segment (one that starts with "<", as /home/<user or /gpfs/home/<user>) and a root alone (a bare
# search pattern such as `/Users/`) are no path of any machine, and refusing them is what made a report be masked.
ABS_PATH = re.compile(r"/(Users|private|var/folders|home)/(?![< \t\n`'\")\]]|$)")
PERSON = re.compile(r"javrodher|rodrij92|javier|@gmail", re.I)

# Lane fold9/round7-residual (glitch-45's ruling of Mon 2 Nov 2026, round 4's precedent): a report changed by its own
# reviewer's shell step has no digest to bind, and a registered review is never discarded. Round 7's reviewer ran one sed
# on the report, so it lands as these exact bytes, beside the as-written record, and can never seed
# (freeze.REPORT_DIGEST_GRANDFATHERED). An entry is for one round and one report; nothing else passes this door.
UNBOUND_REPORTS = {
    "7": {"report_sha256": "4538ce819faa156431b6d3a2d784991a880d74d7b287c264d1b606f4ed8833cf",
          "as_written": "prefreeze-7.as-written.md",
          "as_written_sha256": "56bff23fa7a445a5849e47a6a50c03b3e82400317f7bf99646163121d9f1e9c4",
          "reason": "a shell step writes the report",
          "edit": "its reviewer ran one sed on line 109, changing 'This sound apart from' to 'This is sound apart from'"},
}


def unbound_report_problems(n: str, report_sha: str, record: str) -> list[str]:
    """Why round n's report, whose record states no digest, may not land under UNBOUND_REPORTS. An empty list admits it."""
    entry = UNBOUND_REPORTS.get(n)
    if entry is None:
        return ["the blindness record states no sha256 of the report as the reviewer's session wrote it"]
    out = []
    if int(n) not in REPORT_DIGEST_GRANDFATHERED:
        out.append(f"round {n} is not grandfathered (freeze.REPORT_DIGEST_GRANDFATHERED), so it could seed unbound")
    line = blindness.REPORT_UNBOUND + entry["reason"]
    if not re.search(rf"^{re.escape(line)}$", record, re.M):
        out.append(f"the blindness record states no sha256 of the report as the reviewer's session wrote it, and does "
                   f"not state the one reason this round's entry names ({entry['reason']})")
    if report_sha != entry["report_sha256"]:
        out.append(f"the report's sha256 {report_sha[:12]} is not the {entry['report_sha256'][:12]} this round's entry names")
    rel = str((STUDY_DIR / study.REVIEW_DIR / entry["as_written"]).relative_to(REPO))
    shown = subprocess.run(["git", "-C", str(REPO), "show", f"HEAD:{rel}"], capture_output=True)
    if shown.returncode != 0 or hashlib.sha256(shown.stdout).hexdigest() != entry["as_written_sha256"]:
        out.append(f"{entry['as_written']} is not committed at HEAD with sha256 {entry['as_written_sha256'][:12]}")
    return out


def report_problems(text: str, draft_sha: str) -> list[str]:
    problems = []
    first = text.splitlines()[0] if text else ""
    if first != f"prereg.json sha256: {draft_sha}":
        problems.append(f"line 1 is not the current draft's sha256 line: {first[:80]!r}")
    if ABS_PATH.search(text):
        problems.append("the report carries an absolute path")
    if PERSON.search(text):
        problems.append("the report names a person")
    return problems


def registered_session_id(n: str) -> str | None:
    """takes.session_id_for(the commit that introduced round n's prefreeze row), read from REPO, or None."""
    import json
    import takes
    reg = str((STUDY_DIR / study.REVIEW_DIR / "rounds.json").relative_to(REPO))
    log = subprocess.run(["git", "-C", str(REPO), "log", "--reverse", "--format=%H", "--", reg], capture_output=True,
                         text=True)
    head = subprocess.run(["git", "-C", str(REPO), "show", f"HEAD:{reg}"], capture_output=True, text=True)
    try:
        rows = json.loads(head.stdout)["rows"] if head.returncode == 0 else []
    except (ValueError, KeyError, TypeError):
        return None
    idx = [i for i, r in enumerate(rows) if isinstance(r, dict) and r.get("kind") == "prefreeze" and str(r.get("n")) == str(n)]
    if len(idx) != 1:
        return None
    for sha in log.stdout.split() if log.returncode == 0 else []:
        blob = subprocess.run(["git", "-C", str(REPO), "show", f"{sha}:{reg}"], capture_output=True, text=True)
        try:
            if blob.returncode == 0 and len(json.loads(blob.stdout)["rows"]) > idx[0]:
                return takes.session_id_for(sha)
        except (ValueError, KeyError, TypeError):
            continue
    return None


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__.split("\n")[2].strip())
        return 2
    folder, n = Path(sys.argv[1]).resolve(), sys.argv[2]
    report = folder / f"prefreeze-{n}.md"
    side = folder.parent / (folder.name + "-launch")
    blind = side / "blindness.txt"
    for f in (report, blind):
        if not f.is_file():
            print(f"missing: {f.name}")
            return 2
    # ROUND 2, CP8: the report is bound to the bytes the reviewer was handed, the kit's prereg.json, not to the
    # draft in force at commit time. Review 1's fix moved the draft before its report was committed, and this refused
    # the report for it; whether the seed review read the CURRENT bytes is freeze.py's rule, which also requires the
    # seed to be the latest review committed.
    read_sha = hashlib.sha256((folder / "prereg.json").read_bytes()).hexdigest()
    draft_sha = hashlib.sha256((STUDY_DIR / "prereg-draft.json").read_bytes()).hexdigest()
    text = report.read_text()
    problems = report_problems(text, read_sha)
    # Pre-freeze review 5, M1 (lane fold5/report-binding, glitch-45's ruling 1): the report is committed only as the
    # reviewer's own session wrote it, the bytes whose sha256 its blindness record rebuilds from the session file.
    report_sha = hashlib.sha256(report.read_bytes()).hexdigest()
    # The review of f3ae7772, MAJOR: the record is re-derived here, never trusted. The record committed is the one
    # blindness.report writes now from the reviewer's own session file, byte for byte, so a forged digest line (or any
    # other edit of the record) is refused, and the digest it states is the session's own.
    sid_file = side / "SESSION"
    sid = sid_file.read_text().strip() if sid_file.is_file() else ""
    # The re-check of 0beda082, MINOR 1: the session read is the one the registered round derives, never any session
    # the side folder names (rounds.json's row N, its introducing commit, takes.session_id_for).
    want_sid = registered_session_id(n)
    if want_sid is None:
        problems.append(f"round {n} has no registered prefreeze row committed in review_kit/rounds.json")
    elif sid and sid != want_sid:
        problems.append(f"{sid_file.name} names session {sid}, not the {want_sid} round {n}'s registered row derives")
    try:
        rebuilt = blindness.report(folder, sid, blindness.PROJECTS) if sid else None
    except SystemExit as e:                       # blindness.session_file refuses a missing or ambiguous session file
        rebuilt, problems = None, problems + [f"the reviewer's session cannot be read again: {e}"]
    if rebuilt is None and not sid:
        problems.append(f"no session id in {sid_file.name}, so the blindness record cannot be re-derived")
    elif rebuilt is not None and rebuilt != blind.read_text():
        problems.append("the blindness record is not the one blindness.py writes from the reviewer's session now")
    session_sha = blindness.recorded_report_digest(blind.read_text())
    if session_sha is None:
        problems += unbound_report_problems(n, report_sha, blind.read_text())
    elif session_sha != report_sha:
        problems.append(f"the report's sha256 {report_sha[:12]} is not the {session_sha[:12]} the reviewer's session "
                        "wrote: the report was changed after the reviewer wrote it")
    if problems:
        print("refusing to commit the report: " + "; ".join(problems))
        return 1
    dest = STUDY_DIR / study.REVIEW_DIR / f"prefreeze-{n}.md"
    dest_blind = STUDY_DIR / study.REVIEW_DIR / f"prefreeze-{n}-blindness.txt"
    if dest.exists():
        print(f"refusing: {dest.relative_to(REPO)} already exists; a review is committed once")
        return 1
    shutil.copy2(report, dest)
    shutil.copy2(blind, dest_blind)
    ruling = read_ruling(text)
    msg = folder.parent / f"prefreeze-{n}-commit-message.txt"
    msg.write_text(f"review: pre-freeze review {n}, committed as it stands\n\nOne fresh reviewer, launched headless "
                   f"outside the Brain with only the kit, read the draft at sha256 {read_sha[:12]} and ruled: {ruling}"
                   + (" (zero or several ruling lines; the freeze reads it as no DO FREEZE)" if ruling == AMBIGUOUS
                      else "") + ". "
                   + ("" if read_sha == draft_sha else f"The draft in force at this commit is {draft_sha[:12]}: it moved after the review, so this review cannot seed a freeze. ")
                   + (f"The report's sha256 is {report_sha}, the bytes its blindness record rebuilds from the "
                      "reviewer's own session; the report and the record are committed as they are.\n\n"
                      if session_sha is not None else
                      f"The report's sha256 is {report_sha}; its record states no digest: "
                      f"{UNBOUND_REPORTS[n]['edit']}. The session's bytes are "
                      f"{study.REVIEW_DIR}/{UNBOUND_REPORTS[n]['as_written']}, and this round never seeds a freeze. The "
                      "report and the record are committed as they are.\n\n")
                   + "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n")
    lint = subprocess.run([sys.executable, str(STUDY_DIR / "commit_msg.py"), str(msg)], capture_output=True, text=True)
    if lint.returncode != 0:
        print(lint.stdout)
        return 1
    rel = [str(dest.relative_to(REPO)), str(dest_blind.relative_to(REPO))]
    subprocess.run(["git", "-C", str(REPO), "add", "--", *rel], check=True)
    staged = subprocess.run(["git", "-C", str(REPO), "diff", "--cached", "--name-only"], capture_output=True,
                            text=True).stdout.split()
    if sorted(staged) != sorted(rel):
        print(f"refusing: the commit would land {staged}, not exactly the review and its blindness record")
        subprocess.run(["git", "-C", str(REPO), "reset", "-q"])
        return 1
    subprocess.run(["git", "-C", str(REPO), "commit", "-q", "-F", str(msg)], check=True)
    sha = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    print(f"committed {sha[:12]}: {ruling}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
