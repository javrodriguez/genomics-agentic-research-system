#!/usr/bin/env python3
"""Turn the draft into the frozen pre-registration, once, and fill every pin as it goes.

    python3 evals/gap-study-2/freeze.py --review-commit <sha>          preview
    python3 evals/gap-study-2/freeze.py --review-commit <sha> --write  write prereg.json

THE FREEZE IS THE STUDY'S ONE IRREVERSIBLE STEP. After it, the design is read-only to the run and
every number is graded against it. So this file does three things and refuses to do them twice.

  it fills every pin      each grader, fixture generator, case suite and shared reader gets its
                          git blob sha AND its sha256 recorded, so check_results.py can prove
                          afterwards that none of them moved
  it fixes the take order one permutation per axis over every (task, half, model, take), seeded by
                          the sha of the PRE-FREEZE REVIEW COMMIT
  it refuses to re-run    if prereg.json exists, this exits rather than overwriting. A study whose
                          pre-registration can be re-frozen has none.

WHY THE SEED IS THE REVIEW COMMIT AND NOT ANYTHING ELSE. The order in which cells are driven could
matter -- a model's later takes run against a warmer cache, a rate limit lands where it lands. If
the run chose that order it could choose one that suited it. The seed is a sha that did not exist
until an independent reviewer had already read the design and committed its report, so the order
cannot have been picked to suit a result. Anyone can recompute it: `prereg.py --order <sha>`.

THE REVIEW MUST ALREADY BE COMMITTED. This file checks that the sha it is handed is a real commit
that touches the verification directory, and refuses otherwise. A seed that names nothing is a seed
the run could have invented.

No model, no network, stdlib only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))

import prereg  # noqa: E402
import study  # noqa: E402

DRAFT = HERE / "prereg-draft.json"
FROZEN = HERE / "prereg.json"

# Everything the frozen file must be able to prove did not move afterwards.
#
# Round 2, CP0 (plan amendment A4): every study path here is THIS study's, built by study.rel. This
# list, not the draft, is what builds pinned_files; left on round 1 it would pin round 1's unchanged
# graders while round 2 grades with its own. EveryPinnedPathIsRoundTwos refuses a round-1 path here.
PINNED = [
    study.rel("graders", "labels.py"),
    study.rel("graders", "template_adherence.py"),
    study.rel("graders", "precondition_refusal.py"),
    study.rel("graders", "number_fidelity.py"),
    study.rel("graders", "scope_read.py"),
    study.rel("graders", "plan_gate.py"),
    study.rel("fixtures", "gen_source.py"),
    study.rel("fixtures", "gen_project.py"),
    study.rel("fixtures", "copy_project.py"),
    study.rel("fixtures", "check_fixture.py"),
    study.rel("fixtures", "symbol_rulings.json"),
    study.rel("contract_quotes.json"),
    study.rel("controls", "results.json"),
    study.rel("run.py"),
    study.rel("analyse.py"),
    study.rel("check_take.py"),
    study.rel("drive.py"),
    study.rel("lint_language.py"),
    study.rel("graders", "confounded_design.py"),
    # the machinery a stranger runs, and the guards that decide what it may say
    study.rel("prereg.py"),
    study.rel("takes.py"),
    study.rel("contracts.py"),
    study.rel("check_results.py"),
    study.rel("costs.py"),
    study.rel("build_cases.py"),
    study.rel("test_harness.py"),
    study.rel("mutations.py"),
    study.rel("controls", "run_controls.py"),
    study.rel("smoke_run_tree.py"),
    study.rel("scrub.py"),
    # the excusals. Unpinned, anything could be excused after the freeze and the guard would still
    # report clean.
    study.rel("language-allowlist.json"),
    # what the frozen file was frozen FROM
    study.rel("prereg-draft.json"),
    # the instruction file every take loads at its checkout's root, bound by content (review 14)
    "CLAUDE.md",
    # the first study's shared readers, imported rather than copied
    "evals/transcript.py",
    "evals/stated_count.py",
    # the first study's own files the carried task rests on: its driver (the source of the carried
    # script), generator, neutraliser, rank check, classifier, case suite and take map. The first
    # study pins most of these itself; pinning them here too means THIS checker goes red if they move.
    "evals/drive.py",
    "evals/fixtures/gen_fastq.py",
    "evals/fixtures/neutralise.py",
    "evals/fixtures/rank_check.py",
    "evals/graders/confounded_refusal.py",
    "evals/fixtures/lexicon_cases_task1.json",
    "evals/take-map.json",
]

# freeze.py is deliberately NOT in that list. It runs to produce the pins, so it cannot pin the
# bytes of the run that is producing them: whatever it recorded about itself would be the state
# before it finished writing. The freeze commit's own sha is what fixes it, and check_results.py
# reads that.
NOT_PINNED_AND_WHY = {
    study.rel("freeze.py"): "it runs to produce the pins; the freeze commit's sha fixes it",
}


def git(*args: str) -> tuple[int, str]:
    out = subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True)
    return out.returncode, out.stdout.strip()


# ROUND 2, CP8. Everything the freeze WRITES, by top-level key or by the key it fills inside a task. The freeze commit's
# body carries the diff between the reviewed draft and the frozen file restricted to these keys, or the word `none`;
# a test asserts that the diff touches nothing else, so a freeze can never edit the design on the way out.
FREEZE_WRITTEN_KEYS = (
    "status", "frozen_at", "frozen_at_commit_parent", "draft_sha256_at_freeze", "pre_freeze_review_commit",
    "pre_freeze_review_file", "pre_freeze_review_sha256", "take_order_seed", "take_order", "pinned_files",
    "nulls_at_freeze",
)
FREEZE_FILLED_INSIDE = (
    "system_under_test.gars_tree_sha_at_freeze", "harness.claude_version_at_freeze",
    "tasks[].grader", "tasks[].grader_cases", "tasks[].positive.fixture", "tasks[].control.fixture",
)
REHEARSAL_GLOB = "freeze-rehearsal-*.txt"
REHEARSAL_LAST_LINE = "all green"


def changed_keys(draft: dict, frozen: dict) -> list[str]:
    """Every top-level key whose value differs between the draft and the frozen file, and every task-level key."""
    out = []
    for k in sorted(set(draft) | set(frozen)):
        if k == "tasks":
            continue
        a, b = draft.get(k), frozen.get(k)
        if a == b:
            continue
        # a dict the freeze fills one key inside (harness, system_under_test) is named by that key, not whole
        if isinstance(a, dict) and isinstance(b, dict):
            out.extend(f"{k}.{kk}" for kk in sorted(set(a) | set(b)) if a.get(kk) != b.get(kk))
        else:
            out.append(k)
    for i, (a, b) in enumerate(zip(draft.get("tasks", []), frozen.get("tasks", []))):
        for k in sorted(set(a) | set(b)):
            if a.get(k) != b.get(k):
                if k in ("positive", "control"):
                    for kk in sorted(set(a[k]) | set(b[k])):
                        if a[k].get(kk) != b[k].get(kk):
                            out.append(f"tasks[].{k}.{kk}")
                else:
                    out.append(f"tasks[].{k}")
    return sorted(set(out))


def keys_outside_the_freeze(draft: dict, frozen: dict) -> list[str]:
    """The changed keys the freeze is not allowed to write: a non-empty list means the freeze edited the design."""
    allowed = set(FREEZE_WRITTEN_KEYS) | set(FREEZE_FILLED_INSIDE)
    return [k for k in changed_keys(draft, frozen) if k not in allowed]


def commit_body_diff(draft: dict, frozen: dict) -> str:
    """What the freeze commit's body says about the bytes: the keys the freeze wrote, or `none`."""
    keys = changed_keys(draft, frozen)
    return "none" if not keys else "freeze-written keys: " + ", ".join(keys)


def rehearsal_problems(draft_sha256: str, verification: Path) -> list[str]:
    """Why the freeze may not be written yet: no rehearsal record for THESE draft bytes that ended all green.

    A rehearsal file is `verification/freeze-rehearsal-<n>.txt`, written by freeze_rehearsal.py; its first line is
    the sha256 of the draft it rehearsed, and its last line reads `all green` only when every step of the gate
    passed on the frozen state in the throwaway clone. A draft edited after its rehearsal has a new sha256 and needs
    a new rehearsal, so the freeze cannot run on a state that was never exercised.
    """
    files = sorted(verification.glob(REHEARSAL_GLOB))
    if not files:
        return [f"no {REHEARSAL_GLOB} under {verification.name}/: the freeze has not been rehearsed. Run "
                f"freeze_rehearsal.py first."]
    matching = [f for f in files if f.read_text().splitlines()[:1] == [draft_sha256]]
    if not matching:
        return [f"no rehearsal record names these draft bytes ({draft_sha256[:12]}): the draft changed since the last "
                f"rehearsal. Run freeze_rehearsal.py again."]
    green = [f for f in matching if f.read_text().rstrip().splitlines()[-1].strip() == REHEARSAL_LAST_LINE]
    if not green:
        return [f"the rehearsal of these draft bytes did not end `{REHEARSAL_LAST_LINE}` ({matching[-1].name}); "
                f"fix what it found and rehearse again."]
    return []


def claude_version() -> str:
    """The harness version, from `claude --version`, or a refusal: a frozen file with a blank harness version would
    print an empty range in the published section."""
    try:
        out = subprocess.run(["claude", "--version"], capture_output=True, text=True)
    except FileNotFoundError:
        raise SystemExit("REFUSING to freeze: `claude` is not on PATH, so the harness version cannot be recorded. "
                         "Nothing was written.")
    ver = out.stdout.strip()
    if out.returncode != 0 or not ver:
        raise SystemExit(f"REFUSING to freeze: `claude --version` exited {out.returncode} with no version. Nothing "
                         f"was written.")
    return ver


def pin(path: str) -> dict:
    f = REPO / path
    if not f.is_file():
        return {"path": path, "missing": True}
    code, blob = git("rev-parse", f"HEAD:{path}")
    return {
        "path": path,
        "git_blob_sha": blob if code == 0 else None,
        "sha256": hashlib.sha256(f.read_bytes()).hexdigest(),
        "uncommitted": code != 0,
    }


def review_file_problems(review_commit: str) -> tuple[list[str], str | None]:
    """The seed commit must land exactly one review report, committed exactly once (review 14, F5).

    The take order is seeded by the review commit's sha. A report re-committed under another message or
    time yields another sha and another order, so the operator could choose among as many orders as it
    cared to commit. One report, one commit, recorded in the frozen file, lets a reader see it was not.
    """
    code, touched = git("show", "--name-only", "--format=", review_commit)
    if code != 0:
        return [f"{review_commit[:12]} cannot be read"], None
    reports = [ln for ln in touched.splitlines()
               if re.search(rf"^{re.escape(study.rel('verification'))}/prefreeze-\d+\.md$", ln)]
    if len(reports) != 1:
        return [f"{review_commit[:12]} lands {len(reports)} pre-freeze review reports; the seed must land exactly one"], None
    code, hist = git("log", "--format=%H", "--", reports[0])
    if len(hist.split()) != 1:
        return [f"{reports[0]} was committed {len(hist.split())} times; the seed would be one of several candidates"], None
    return [], reports[0]


def main() -> int:
    ap = argparse.ArgumentParser(description="Freeze the pre-registration, once.")
    ap.add_argument("--review-commit", required=True,
                    help="the sha of the committed pre-freeze review; it seeds the take order")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--rehearsal", action="store_true",
                    help="run by freeze_rehearsal.py inside a throwaway clone with no remote; skips the rehearsal "
                         "record the real freeze requires, and is refused in a repository that has a remote")
    args = ap.parse_args()

    if args.rehearsal:
        code, remotes = git("remote")
        if code != 0 or remotes.strip():
            print("refusing: --rehearsal is for a throwaway clone with no remote, and this repository has one. The "
                  "real freeze needs a rehearsal record, not this flag.")
            return 2

    if FROZEN.is_file():
        print(f"refusing: {FROZEN.name} already exists. The freeze happens once — a study whose "
              f"pre-registration can be re-frozen has none.")
        return 2

    code, _ = git("cat-file", "-e", f"{args.review_commit}^{{commit}}")
    if code != 0:
        print(f"refusing: {args.review_commit} is not a commit in this repository. The take order "
              f"is seeded by the review commit precisely so the run cannot have chosen it.")
        return 2
    code, touched = git("show", "--name-only", "--format=", args.review_commit)
    if study.rel("verification") not in touched:
        print(f"refusing: {args.review_commit[:12]} does not touch "
              f"{study.rel('verification')}/. The seed must name the commit that landed the "
              f"pre-freeze review, not some other commit.\nIt touched:\n{touched[:400]}")
        return 2

    problems, review_file = review_file_problems(args.review_commit)
    if problems:
        print("refusing: " + " ".join(problems))
        return 2

    d = json.loads(DRAFT.read_text())
    reviewed_sha256 = hashlib.sha256(DRAFT.read_bytes()).hexdigest()
    # ROUND 2, CP8. The irreversible step runs only on a state a rehearsal exercised: checked here, before any pin is
    # computed, so the refusal names the rehearsal and nothing else.
    if args.write and not args.rehearsal:
        problems = rehearsal_problems(reviewed_sha256, HERE / "verification")
        if problems:
            print("REFUSING to freeze: " + " ".join(problems))
            return 1
    d["pre_freeze_review_file"] = review_file
    d["pre_freeze_review_sha256"] = hashlib.sha256((REPO / review_file).read_bytes()).hexdigest()

    d["status"] = "FROZEN. Read-only to the run. A later change is published as `amended`, with " \
                  "before and after and both regrades side by side, never corrected in place."
    d["frozen_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    _, head = git("rev-parse", "HEAD")
    d["frozen_at_commit_parent"] = head
    d["draft_sha256_at_freeze"] = reviewed_sha256
    d["pre_freeze_review_commit"] = args.review_commit
    d["take_order_seed"] = args.review_commit

    pins = [pin(p) for p in PINNED]
    d["pinned_files"] = pins

    # THE PER-TASK PINS, filled here rather than left null beside a global list.
    #
    # Each task names its grader and its case suite by path with both shas null and a note saying
    # "pinned at the freeze". If the freeze fills only the global list, those nulls survive into the
    # frozen file and a reader cannot tell a null-to-fill from a null-by-design.
    for t in d["tasks"]:
        for key in ("grader", "grader_cases"):
            spec = t.get(key) or {}
            path = spec.get("path")
            if not path:
                continue
            got = pin(path)
            if got.get("missing"):
                spec["missing_at_freeze"] = True
                spec["note"] = (f"{path} does not exist at the freeze. Its cell publishes "
                                f"`not run — no grader module` rather than a number.")
                continue
            spec["git_blob_sha"] = got["git_blob_sha"]
            spec["sha256"] = got["sha256"]
            spec.pop("note", None)

    # THE FIXTURE PINS. A fixture is not one file in git, so it is not pinned like one.
    #
    #   generated    pinned by its GENERATOR (already in pinned_files) plus its seed and variant,
    #                and by the content hash the generator computes over the bytes it writes. That
    #                hash is filled here from `--manifest-only`, which runs the generator without
    #                writing anything.
    #   copied-tree  pinned by tree_sha256_name_invariant, computed over the copy with the take's
    #                project name substituted back to a placeholder.
    #   project      built by the real stage 00 from a pinned generator and seed, and verified on
    #                every build against the branch it must reach.
    #
    # In each case git_blob_sha stays null BY DESIGN: there is no blob. Recording that here is the
    # difference between a null a reader can account for and one they have to guess about.
    for t in d["tasks"]:
        for half in ("positive", "control"):
            fx = (t.get(half) or {}).get("fixture")
            if not isinstance(fx, dict):
                continue
            kind = fx.get("kind")
            fx["git_blob_sha_note"] = ("null by design: a fixture is not a file in git. See "
                                       "pinned_by below.")
            if kind == "generated":
                gen = REPO / fx["generator"]
                out = subprocess.run(
                    [sys.executable, str(gen), "--variant", fx["variant"],
                     "--seed", str(fx["seed"]), "--manifest-only"],
                    capture_output=True, text=True)
                try:
                    man = json.loads(out.stdout)
                    fx["sha256"] = man["fixture_sha256"]
                    fx["pinned_by"] = "the generator's blob sha in pinned_files, plus variant, "\
                                      "seed, and this content hash over the bytes it writes"
                except (json.JSONDecodeError, KeyError) as exc:
                    # REVIEW 20, F5. It wrote a frozen file with an unpinned fixture and let every take
                    # on that task be refused afterwards, which is an amendment where a refusal here is
                    # a retry. The freeze is irreversible; this is the last place to stop.
                    raise SystemExit(f"REFUSING to freeze: the generator for {t['id']}/{half} would not "
                                     f"report a manifest ({exc!r}), so its fixture would be pinned by "
                                     f"nothing and every take on it refused. Nothing was written.")
            elif kind == "copied-tree":
                fx["pinned_by"] = ("tree_sha256_name_invariant, computed over the copy with the "
                                   "take's project name substituted back to a placeholder")
                fx.setdefault("sha256", None)
                fx["sha256_note"] = "null by design: the pin is the tree hash, not a file hash"
            elif kind == "project":
                fx["pinned_by"] = ("the generator's blob sha in pinned_files, plus seed, and the "
                                   "stage-01 exit code the generator verifies on every build")
                fx.setdefault("sha256", None)
                fx["sha256_note"] = ("null by design: the fixture is a project tree built by the "
                                     "real stage 00, not a file")
            elif kind == "first-study":
                # The carried task's fixture, built fresh in a temporary directory by the first
                # study's pinned generator and neutraliser and hashed by this study's one tree
                # recipe. The driver rebuilds and re-hashes on every take and refuses a mismatch.
                # loaded here so a draft-only freeze never imports it; loaded BY PATH (round 2, CP0)
                # because the first study has a drive.py of its own on the same import path
                import importlib.util  # noqa: PLC0415
                spec = importlib.util.spec_from_file_location("gap_study_drive", HERE / "drive.py")
                drive = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(drive)
                with tempfile.TemporaryDirectory() as tmp:
                    staging = Path(tmp) / "data" / "staging" / "<project>"
                    rec = drive.build_first_study_fixture({**fx, "sha256": None}, staging, "<project>")
                fx["sha256"] = rec["tree_sha256_name_invariant"]
                fx["pinned_by"] = ("the first study's generator, seed and neutraliser (their blob shas "
                                   "in pinned_files and first_study_pins), the rank check's expected "
                                   "rank, the design table's md5, and this tree_sha256_name_invariant "
                                   "over the neutralised staging directory, which the driver "
                                   "recomputes on every build")

    # EVERY REMAINING NULL, CLASSIFIED. A frozen file full of nulls that nobody has accounted for
    # is a file whose reader has to guess which were intended.
    remaining = []

    def walk(node, path=""):
        if isinstance(node, dict):
            for k, v in node.items():
                if v is None:
                    remaining.append(f"{path}.{k}".lstrip("."))
                else:
                    walk(v, f"{path}.{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")

    walk(d)
    BY_DESIGN = {
        "marker": "a turn with no wait point to check; the driver checks only that the turn "
                  "produced text",
        "not_run_reason": "a model that runs has no reason not to",
        "error": "a control attempt that was not expected to error",
        "take_order_seed": "set below, from the review commit",
        "git_blob_sha": "a fixture is not a file in git; see the fixture's pinned_by",
        "sha256": "for a copied-tree or project fixture the pin is the tree hash or the verified "
                  "exit code; see the fixture's pinned_by",
    }
    # CONDITIONAL, NOT BLANKET. The freeze refused on 11 September 2026 because
    # `first_study_marker` was null on the carried task's probe turn in both halves. It is null there
    # for the reason `marker` is: that turn has no wait point, in this study and in the first, and the
    # field records the marker as the first study wrote it. Excusing the field by name would also
    # excuse a first-study marker missing from a turn that DOES have a wait point, which would be a
    # real gap, so this is accounted only where that step's own marker is null and anything else stays
    # unaccounted.
    CONDITIONAL = {
        "first_study_marker": "the carried task's turn has no wait point, so the first study recorded "
                              "no marker there either; accounted only where that step's own marker is "
                              "null, and unaccounted anywhere else",
    }

    def _at(path: str):
        node = d
        for part in path.split("."):
            name = re.match(r"[^\[]*", part).group(0)
            if name:
                node = node[name]
            for i in re.findall(r"\[(\d+)\]", part):
                node = node[int(i)]
        return node

    def accounted(path: str) -> bool:
        leaf = path.split(".")[-1]
        if leaf in BY_DESIGN:
            return True
        if leaf in CONDITIONAL and "." in path:
            parent = _at(path.rsplit(".", 1)[0])
            return isinstance(parent, dict) and parent.get("marker") is None
        return False

    d["nulls_at_freeze"] = {
        "count": len(remaining),
        "by_design": {**{k: v for k, v in BY_DESIGN.items()
                         if any(r.endswith("." + k) or r == k for r in remaining)},
                      **{k: v for k, v in CONDITIONAL.items()
                         if any(r.split(".")[-1] == k and accounted(r) for r in remaining)}},
        "unaccounted": sorted(r for r in remaining if not accounted(r)),
        "note": "Every null left in the frozen file is either listed as by-design above or named "
                "as unaccounted. A freeze with unaccounted nulls is refused.",
    }
    _, gars_tree = git("rev-parse", "HEAD:gars")
    d["system_under_test"]["gars_tree_sha_at_freeze"] = gars_tree
    ver = claude_version()
    d["harness"]["claude_version_at_freeze"] = ver

    order = prereg.order(args.review_commit)
    d["take_order"] = {axis: [list(c) for c in cells] for axis, cells in order.items()}

    missing = [p["path"] for p in pins if p.get("missing")]
    uncommitted = [p["path"] for p in pins if p.get("uncommitted")]

    print(f"draft sha256        {reviewed_sha256}")
    print(f"review commit       {args.review_commit[:12]}")
    print(f"review report       {review_file}  sha256 {d['pre_freeze_review_sha256']}  (committed once)")
    print(f"gars tree at freeze {gars_tree[:12]}"
          f"  {'(equals the pre-registered pin)' if gars_tree == d['system_under_test']['gars_tree_sha'] else '(NOT the pre-registered pin: every take would be refused)'}")
    print(f"harness             {ver}")
    print(f"pinned files        {len(pins)}")
    print(f"take order          {sum(len(v) for v in order.values())} cells "
          f"({', '.join(f'{k}: {len(v)}' for k, v in order.items())})")
    if missing:
        print(f"\nMISSING, so nothing can pin them: {missing}")
        return 1
    if uncommitted:
        print(f"\nNOT COMMITTED, so their blob sha is unknown: {uncommitted}")
        print("Commit them first. A pin to an uncommitted file proves nothing.")
        return 1

    nulls = d["nulls_at_freeze"]
    print(f"nulls remaining     {nulls['count']}  "
          f"({len(nulls['by_design'])} class(es) by design, "
          f"{len(nulls['unaccounted'])} unaccounted)")
    for k, why in nulls["by_design"].items():
        print(f"                    {k}: {why}")
    if nulls["unaccounted"]:
        print("\nUNACCOUNTED NULLS, so the freeze is refused:")
        for r in nulls["unaccounted"][:20]:
            print(f"  - {r}")
        print("Either fill them or record why they are null by design. A reader of the frozen "
              "file cannot tell a null-to-fill from a null-by-design, and after the freeze "
              "nobody can ask.")
        return 1

    outside = keys_outside_the_freeze(json.loads(DRAFT.read_text()), d)
    if outside:
        print(f"\nREFUSING: the freeze would change keys it may not write: {outside}. Nothing was written.")
        return 1
    print(f"commit body       {commit_body_diff(json.loads(DRAFT.read_text()), d)}")

    if not args.write:
        print("\npreview only. Re-run with --write to freeze.")
        return 0

    FROZEN.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
    print(f"\nfrozen: {FROZEN.relative_to(REPO)}")
    print("The draft is kept beside it. The freeze commit body carries the line printed above as `commit body`.")
    print("Before committing, run verification/round1-regrade/regrade_environment.py --write: that record names the "
          "pre-registration in force by sha, and the freeze commit carries it rewritten beside the frozen file.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
