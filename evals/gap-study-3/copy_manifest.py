#!/usr/bin/env python3
"""What this study copied from round 2, from which commit, and what it changed.

    python3 evals/gap-study-3/copy_manifest.py --write     record COPIED.json from the files as they stand
    python3 evals/gap-study-3/copy_manifest.py --check     re-derive all of it; exit 1 on any difference

Every copied file is read from round 2's done commit with `git show`, never from a working tree. For each one
COPIED.json records its source path and blob, the sha256 of the source bytes and of the copy, and whether the
copy differs. A copy that differs must carry a reason in EDITS below; a reason for a file that does not differ,
or a difference with no reason, is refused. `--check` also confirms that round 2's folder, round 1's folder, the
pre-study's folder and the shared transcript parser are unchanged since the commits this study pins them at, so
nothing here can have been edited there.

BYTE-IDENTICAL BY THE GOAL FILE, NOT BY CHOICE. The files in UNEDITABLE are the instrument the goal file names:
check_take.py, every grader, the label reader, lint_language.py and commit_msg.py. An edit to one of them is a
FAIL here, not a manifest entry, whatever reason is offered for it -- a study that may change its grader between
rounds is not measuring the same thing twice.

No model, no network, stdlib only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
MANIFEST = HERE / "COPIED.json"
sys.path.insert(0, str(HERE))

import study  # noqa: E402

SOURCE_COMMIT = "bf065feedccc0392f69e95a6d674288bb861a2b0"
SOURCE_DIR = "evals/gap-study-2"
# The pre-study is not in the source commit -- it was built after it -- so it is pinned at its own done commit.
PRESTUDY_COMMIT = "93bcf36fd137d6af970734faf2ea028655301194"
PRESTUDY_DIR = "evals/haiku-prestudy"

FILES = (
    # the binding and the driver
    "study.py", "drive.py",
    # the take side
    "run.py", "takes.py", "prereg.py", "scrub.py", "check_take.py", "check_results.py",
    # the language and commit gates
    "lint_language.py", "commit_msg.py", "language-allowlist.json",
    # the freeze side
    "freeze.py", "freeze_rehearsal.py", "scratch_git.py", "smoke_run_tree.py",
    # the accounting and CI side
    "costs.py", "ci_conclusion.py", "check_checklist_names.py", "contracts.py", "contract_quotes.json",
    # the manifest itself
    "copy_manifest.py",
    # the graders and the label reader
    "graders/labels.py", "graders/scope_read.py", "graders/template_adherence.py",
    "graders/confounded_design.py", "graders/number_fidelity.py", "graders/plan_gate.py",
    "graders/precondition_refusal.py",
    # the lexicons
    "lexicons/permission-stop.json", "lexicons/plan-gate-approve.json", "lexicons/scope-read-answer.json",
    # the cases for the three tasks round 3 measures
    "build_cases.py", "cases/round-2/scope-read.json", "cases/round-2/template-adherence.json",
    "cases/round-2/confounded-design.json",
    # the fixture builders
    "fixtures/check_fixture.py", "fixtures/copy_project.py", "fixtures/gen_project.py",
    "fixtures/gen_source.py", "fixtures/symbol_rulings.json",
    # the review kit
    "review_kit/blindness.py", "review_kit/build_kit.py", "review_kit/launch.py",
    "review_kit/commit_review.py",
)

# What the goal file pins byte-identical. No entry in EDITS may name one of these.
UNEDITABLE = ("check_take.py", "lint_language.py", "commit_msg.py",
              "graders/labels.py", "graders/scope_read.py", "graders/template_adherence.py",
              "graders/confounded_design.py", "graders/number_fidelity.py", "graders/plan_gate.py",
              "graders/precondition_refusal.py")

PINNED_UNCHANGED = ((SOURCE_COMMIT, "evals/gap-study-2"), (SOURCE_COMMIT, "evals/gap-study"),
                    (SOURCE_COMMIT, "evals/transcript.py"), (PRESTUDY_COMMIT, "evals/haiku-prestudy"))

# Three copied files printed or wrote a path that named round 2's folder. Round 2's own design says code that
# builds a path takes it from study.py and nowhere else; these three were missed when round 2 copied round 1,
# and a literal copied from round 2 names round 2. Each now reads study.rel(). No rule and no behaviour moves.
PATH_FIX = ("A live string named the copied round's folder and now takes its path from study.py, as round 2's "
            "own design says a path must. ")

# The only copies allowed to differ from their source, and why. Anything not named here must be byte-identical.
EDITS = {
    "study.py": "The binding: this study's name, folder, title and published-section markers, and the two folders "
                "the two kinds of report live in (REVIEW_DIR, VERIFY_DIR). Round 2's harness builds every path and "
                "marker from this file, so no other copied file needs to name this study.",
    "drive.py": "Three changes, each named in the file's own docstring. (1) Every turn passes --allowedTools with "
                "the pre-registration's driver_change.allowed_tools and the ledger records them: the one permission "
                "condition across the model axis. (2) The ledger records the mode the SESSION recorded, read "
                "from the take's own published transcript, as permission_mode_recorded, beside the flag that "
                "was passed. Round 2 recorded only the flag, in the field its own constant-binding rule "
                "compared with the pre-registration's copy of the same constant -- a constant compared with "
                "itself. permission_mode keeps round 2's meaning, so the byte-identical checker keeps reading "
                "what round 2's did; the recorded mode is asserted by this round's own mode_binding.py "
                "against the per-model expectation the pre-registration pins (Ruling 2, 20 September "
                "2026). (3) One display string that spelled round 2's folder into a rehearsal's WHY.md "
                "takes its path from study.py, as round 2's own design says a path must.",
    "copy_manifest.py": "Its own constants: this study's file list, its edit reasons, the commits it pins the earlier "
                        "studies at, and the byte-identical set the goal file names.",
    "freeze.py": "Three call sites take the pre-freeze review folder from study.REVIEW_DIR instead of the literal "
                 "`verification`: the tree-binding exclusion, the review-commit rule and its latest-review scan. "
                 "Round 3 keeps pre-freeze reviews and final verifications in separate folders so a fresh run counts "
                 "each from `ls` alone. No rule changes; only where each rule looks.",
    "freeze_rehearsal.py": "The synthetic review the rehearsal commits is written to study.REVIEW_DIR, so the "
                           "rehearsal exercises the same path the real freeze reads. Same reason as freeze.py.",
    "review_kit/commit_review.py": "A committed review lands in study.REVIEW_DIR beside its blindness record. Same "
                                   "reason as freeze.py; every assertion the file makes about the report is unchanged.",
    "takes.py": PATH_FIX + "The line printing the command that reads a committed row's session id named "
                "round 2's ledger, which is a different study's rows.",
    "costs.py": PATH_FIX + "Two lines printing the command that writes the costs table named round 2's.",
    "fixtures/gen_source.py": PATH_FIX + "The `generator` field WRITTEN INTO every fixture manifest said "
                              "round 2's generator had built it. That one is data, not a display string: a "
                              "reader of the manifest would have been told the wrong study built the fixture.",
    "review_kit/launch.py": "The session id may be given as a second argument instead of drawn fresh. "
                            "Round 2 drew a uuid4 here, so a reviewer's session was tied to nothing and a "
                            "run could open several and commit the ones it liked. Round 3 passes the id its "
                            "round register derives as uuid5 of the row's commit; the uuid4 default stays, "
                            "and what makes the binding hold is rounds.py --check rather than this file.",
    "review_kit/blindness.py": "The markers name this study (`gars-eval-v4`, `gap-study-3`, `round 3`) and keep round "
                               "2's and the pre-study's, since operator memory that names either is still a leak. The record also names the "
                               "session id it read, which is what rounds.py --check holds a committed round "
                               "to; it goes here because the report is committed unedited and because naming "
                               "the session a blindness check read is what a blindness check is for.",
    "language-allowlist.json": "The excusal list is this study's own. Round 2's two verifier-report entries name "
                               "files this study did not copy and are dropped; its contract-quote entry is re-ruled "
                               "against this study's copy of contract_quotes.json, whose bytes are identical.",
}


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True)


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def derive() -> dict:
    files = []
    for f in FILES:
        src = f"{SOURCE_DIR}/{f}"
        shown = git("show", f"{SOURCE_COMMIT}:{src}")
        if shown.returncode != 0:
            raise SystemExit(f"{src} does not exist at {SOURCE_COMMIT[:12]}")
        blob = git("rev-parse", f"{SOURCE_COMMIT}:{src}").stdout.decode().strip()
        copy = (HERE / f).read_bytes()
        files.append({"path": study.rel(f), "source": src, "source_blob": blob,
                      "source_sha256": sha256(shown.stdout), "copy_sha256": sha256(copy),
                      "edited": copy != shown.stdout, "why": EDITS.get(f)})
    return {"role": "Every file this study copied from round 2, read from the source commit with git show.",
            "source_commit": SOURCE_COMMIT, "prestudy_commit": PRESTUDY_COMMIT, "files": files}


def problems(rec: dict) -> list[str]:
    out = []
    for f in rec["files"]:
        name = f["path"].split(study.STUDY_REL + "/", 1)[1]
        if f["edited"] and not f["why"]:
            out.append(f"{name} differs from {f['source']} at the source commit and no reason is recorded")
        if not f["edited"] and f["why"]:
            out.append(f"{name} carries an edit reason but is byte-identical to its source")
        if f["edited"] and name in UNEDITABLE:
            out.append(f"{name} is pinned byte-identical by the goal file and differs from {f['source']}; "
                       f"that is a FAIL, not a manifest entry")
    for bad in sorted(set(EDITS) & set(UNEDITABLE)):
        out.append(f"{bad} carries an edit reason and is pinned byte-identical by the goal file")
    for commit, p in PINNED_UNCHANGED:
        if git("diff", "--quiet", commit, "HEAD", "--", p).returncode != 0:
            out.append(f"{p} has changed since {commit[:12]}; the source this study copied is not intact")
        # ROUND 2, REVIEW 5, FOLLOW-UP 2, carried. The line above compares two commits, so an uncommitted edit to an
        # earlier study's classifier or the shared parser passed it; this one compares the working tree with the pin.
        elif git("diff", "--quiet", commit, "--", p).returncode != 0:
            out.append(f"{p} differs from {commit[:12]} in the working tree: the file this study reads by "
                       f"path is not the one it copied from")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--write", action="store_true")
    g.add_argument("--check", action="store_true")
    args = ap.parse_args()
    rec = derive()
    bad = problems(rec)
    if args.write:
        if bad:
            print("refusing to write:\n  - " + "\n  - ".join(bad))
            return 1
        MANIFEST.write_text(json.dumps(rec, indent=2) + "\n")
        print(f"wrote {MANIFEST.name}: {len(rec['files'])} files, "
              f"{sum(f['edited'] for f in rec['files'])} edited")
        return 0
    if not MANIFEST.is_file():
        print("no COPIED.json")
        return 1
    if json.loads(MANIFEST.read_text()) != rec:
        bad.append("COPIED.json does not equal what the files and the source commit derive")
    for b in bad:
        print(f"FAIL {b}")
    if not bad:
        print(f"ok: {len(rec['files'])} files trace to {SOURCE_COMMIT[:12]}, "
              f"{sum(f['edited'] for f in rec['files'])} edited with a reason, "
              f"{len(UNEDITABLE)} pinned byte-identical; round 2, round 1, the pre-study and the parser unchanged")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
