#!/usr/bin/env python3
"""Drive one pre-registered take, or one pre-freeze walk, sending fixed lines and nothing else.

    python3 evals/gap-study/drive.py --task scope-read --half positive --row 12
    python3 evals/gap-study/drive.py --task scope-read --half positive --walk --model claude-opus-5

A DETERMINISTIC OPERATOR. It opens a headless Claude Code session in the repository root and sends
the operator lines the pre-registration fixes, one turn at a time. It does not rephrase, nudge,
retry, or answer a question that is not on the script. Nothing it does depends on what the agent
said, beyond checking for a wait-point marker.

WHAT IS DIFFERENT FROM THE FIRST STUDY'S DRIVER, AND WHY EACH DIFFERENCE EARNS ITS PLACE.

The script is DATA. The first study's driver held its operator lines, its question and its markers
as module constants for one task. Here every line, marker and reach turn is read from the
pre-registration, so a stranger can see what was sent without reading Python.

The session id is NOT DISCOVERED, IT IS IMPOSED. The first study read the session id out of the
first record Claude Code emitted. This driver computes it before the session opens:

    session_id = uuid5(NAMESPACE, the sha of the commit that introduced this take's ledger row)

and passes it with --session-id. The row must be committed before the take can run, because its
commit sha is an input to the id. That is what makes "pre-registered before it ran" checkable by a
stranger rather than a promise.

A HALT IS NO LONGER A REHEARSAL. In the first study, an unheld marker discarded the run. That rule
lets a bad result be re-labelled as a mechanical failure, which is the one thing a study like this
cannot afford. Here:

  a transcript with a first agent turn is a GRADED TAKE, whatever happened after it. If the agent
    never reached the wait point, the grader labels it did-not-reach and it counts against holding.
  a REHEARSAL is only an attempt refused by the take checker for an operator-side reason, or a
    `claude` process that died before its first agent turn.
  a PAUSE is a rate-limit refusal before the first agent turn: wait, record it, retry the slot.

The driver sends no line past an unheld marker -- continuing would measure a script the agent never
got to -- but it does not throw the transcript away either.

ONE EXCEPTION, and it is data rather than judgment: a step may carry a pre-registered RECOVERY,
which answers a wait point the script does not otherwise answer. Sent at most once, only when the
reply holds the recovery's own marker while the step's is not held. See the frozen file's
wait_point_marker_rule.

NOTHING IN A PATH OR A NAME TELLS THE AGENT WHAT THIS IS. The session under test reads every byte it
is given. The first study named its projects for the half and staged fixtures under a path carrying
the task name; both had to be repaired mid-run. Here the project name and the staging path are
derived from the session id -- `run-<8 hex>` -- which is unique, reproducible, bound to the ledger
row, and says nothing. The half is recorded in the ledger, where the agent cannot read it.

ON THE RULE GLITCH IS BUILT UNDER. The Glitch engine never uses `claude -p`. This file is the GARS
project's own evaluation harness and lives in the GARS repository; that rule does not reach it.

The session under test is a separate process with no context from the session running this driver
or from the session that will grade the result. No model is called by this file itself.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))

import prereg  # noqa: E402
import takes as takes_mod  # noqa: E402
import scrub as scrub_mod  # noqa: E402

PERMISSION_MODE = "auto"
# The first study's constant, carried with its then-step: how long the driver waits for stage 00's
# finalize to write samples.csv before the design table is copied in. Pre-registered in
# driver_constants.finalize_wait_s; the value read at run time is the frozen file's.
FINALIZE_WAIT_S = 180
RATE_LIMIT_MARKERS = ("rate limit", "usage limit", "weekly limit", "resets", "429")

# WHAT THE SESSION UNDER TEST IS GIVEN BESIDE ITS CHECKOUT: NOTHING FROM THE OPERATOR'S OWN SETUP.
#
# The first smoke of the rebuilt checkout (verification/run-tree-smoke/1) showed a headless session
# opened in a clean temporary directory still receiving two things from the operator's user scope:
# the extra working directories their user settings grant, and the tools of the account connectors
# signed in on their Claude account -- mail, calendar and files -- offered to an agent running in auto
# permission mode. Neither is in the checkout and a stranger's clone has neither. The committed walks
# carry both. `--setting-sources project,local` reads settings from the checkout alone, and
# `--strict-mcp-config` with no `--mcp-config` admitted no MCP server in the second smoke. Whether
# that flag reaches the account connectors is not documented, so the documented switch for them,
# `ENABLE_CLAUDEAI_MCP_SERVERS=false` (code.claude.com/docs/en/mcp), is set in the session's own
# environment as well, rather than resting on a side effect. check_take.inherited_context() reads
# each transcript afterwards and refuses a take that was given either anyway, so these are controls
# whose effect is measured, not promises.
ISOLATION_FLAGS = ("--setting-sources", "project,local", "--strict-mcp-config")
# CLAUDE_CODE_DISABLE_AUTO_MEMORY: the harness otherwise offers every headless session a persistent
# memory folder under the operator's home, and the flags above do not remove it. Documented at
# code.claude.com/docs/en/memory; measured on a one-turn smoke with and without it
# (verification/auto-memory-smoke.txt). check_take refuses a take whose system prompt still offers it.
ISOLATION_ENV = {"ENABLE_CLAUDEAI_MCP_SERVERS": "false", "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1"}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def session_file(session_id: str) -> Path | None:
    """The session transcript Claude Code wrote for this id, wherever it put it.

    REVIEW 11, BLOCKER 3. The first version derived the directory from REPO. Since the session stopped
    opening in REPO it looked in the wrong place, so every take would have finished with no
    transcript. Predicting the directory means copying Claude Code's rule for naming it, which is a
    fact about one harness version. The session id is a uuid this driver imposed, so the file is
    found by that id, and more than one match refuses rather than picking one.
    """
    base = Path(os.environ.get("CLAUDE_CONFIG_DIR") or (Path.home() / ".claude")) / "projects"
    hits = sorted(base.glob(f"*/{session_id}.jsonl"))
    if len(hits) > 1:
        raise SystemExit(f"REFUSING: {len(hits)} session files carry the id {session_id}: {hits}")
    return hits[0] if hits else None


def publish_transcript(src: Path, out_root: Path) -> dict:
    """Copy the session file into the study, with the one removal the repository owner ruled.

    A transcript is the session file Claude Code wrote, with exactly one field removed:
    `session_context.userEmail`, the signed-in account's email address, which Claude Code injects
    into every session and no documented setting turns off. The repository owner ruled this on
    11 September 2026 (PROTOCOL.md, Ruling 10), for walks and graded takes alike.

    scrub.py removes the field, refuses if any record a grader reads would change, and refuses if the
    address survives anywhere in the bytes. scrub.json beside the transcript records the sha256
    before and after, so the removal is stated rather than silent. The raw session file stays where
    Claude Code wrote it and never enters this repository.
    """
    raw = src.read_bytes().decode("utf-8")
    body, removed = scrub_mod.scrub_text(raw)
    return scrub_mod.write_published(out_root / "transcript.jsonl", raw, body, removed)


def display_path(path: Path) -> str:
    """A path as a reader should see it: relative to the repository when it is inside it."""
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)


def neutral_name(session_id: str) -> str:
    """The project and staging name. Unique, reproducible, and it says nothing.

    Derived from the session id, which is derived from the ledger row's commit, so a checker can
    re-derive it -- while the agent, which sees this string in every operator line, learns only
    that it is a run.
    """
    return "run-" + session_id.replace("-", "")[:8]



# The checkout the agent runs in. It is deliberately None until a take sets it, so a turn cannot
# fall back to this repository -- which is where every leaked take was driven from.
RUN_TREE: Path | None = None

# The one commit the checkout carries, and who it says made it. Neither names anything: Claude Code
# puts the subjects of the latest commits and the git user in front of the agent on its first turn.
TREE_SUBJECT = "checkout"
TREE_IDENTITY = ("gars", "gars@localhost")


def no_inherited_instructions(tree: Path) -> list[str]:
    """Every instruction file the agent would inherit from ABOVE its working directory.

    THIS IS THE CHECK THE STUDY DID NOT HAVE, AND ITS ABSENCE COST BOTH STUDIES THEIR BLINDNESS.
    The driver ran the agent with its working directory inside the operator's personal assistant
    tree. Claude Code walks up from the working directory looking for CLAUDE.md, found that tree's
    file, and loaded it together with the two files it imports -- the operator's profile and their
    long-term memory. That text named this study. It reached the agent before the first operator
    line and no check opened it, because the leak sweep read the operator's turns only.

    A path is not the fix, because a path is a fact about one machine. The rule is the fix: the
    checkout the agent runs in must have NO instruction file above it, and the driver proves that
    on every take rather than trusting where it was pointed.
    """
    found = []
    p = tree.resolve().parent
    while True:
        if (p / "CLAUDE.md").is_file():
            found.append(str(p / "CLAUDE.md"))
        if p == p.parent:
            return found
        p = p.parent


def run_tree_path(session_id: str) -> Path:
    """Where this take's checkout lives: the machine's temporary directory, named for the session.

    REVIEW 11, BLOCKER 2. The first version hard-coded a root named after this study, and Claude Code
    hands the agent its working directory -- so the path said what the take was. The checkout now
    carries the same neutral name as the project (`run-<8 hex>`), under whatever temporary directory
    the machine has, which is a property of the machine rather than a directory this file names.
    """
    return Path(tempfile.gettempdir()).resolve() / neutral_name(session_id)


def excluded_from_run_tree(pre: dict) -> list[str]:
    """The paths the pre-registration leaves out of the checkout. Data, not a constant here."""
    return [e["path"] for e in pre["run_location"]["excluded_from_the_run_tree"]]


def clean_run_tree(commit: str, session_id: str, exclude: list[str], repo: Path = REPO) -> Path:
    """This take's own checkout of the pinned tree: no study inside it, no history, nothing above it.

    REVIEW 11, BLOCKER 1. The first version cloned this repository and deleted `evals/` from the
    working tree. A clone carries its history, so every deleted file stayed one `git show` away, and
    the deletions appeared in `git status` -- which Claude Code puts in front of the agent on its first
    turn, beside the subjects of the latest commits, which name this study. Deleting the folder did
    not hide the study; it advertised it.

    So nothing is cloned. The pinned commit is exported with `git archive`, minus the paths the
    pre-registration excludes, into a directory of its own; a new repository is initialised over it
    and committed once, under a subject and an identity that name nothing. The agent's checkout has
    one commit, a clean status, no remote (review 11, F7), and no history in which anything was
    removed.

    ONE CHECKOUT PER TAKE (review 11, F5). A reused one carried the previous take's project beside the
    next. The checkout is new, or the take refuses.

    Every property is checked on the BUILT tree before it is returned, rather than trusted from the
    steps that built it. The first version's guards were verified against constructed strings, and
    the defect sat in the part no test drove.
    """
    tree = run_tree_path(session_id)
    if tree.exists():
        raise SystemExit(f"REFUSING: {tree} already exists. Every take gets a checkout of its own; "
                         f"a reused one carries the previous take's project beside this one.")
    tree.mkdir(parents=True)

    # A CHECKOUT THAT IS REFUSED, OR FAILS TO BUILD, IS REMOVED BEFORE THE REFUSAL. The first version
    # raised and left it in the machine's temporary directory: the two run-tree mutations left 44 of
    # their synthetic repository there by 11 September 2026, and every run of the battery added
    # more. A real take refused here would have left a copy of the pinned tree behind.
    try:
        spec = [f":(exclude){p}" for p in exclude]
        archive = subprocess.run(["git", "-C", str(repo), "archive", "--format=tar", commit, "--", ".",
                                  *spec], check=True, capture_output=True)
        with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as tar:
            if hasattr(tarfile, "tar_filter"):
                tar.extractall(tree, filter="tar")
            else:
                tar.extractall(tree)

        g = ["git", "-C", str(tree)]
        subprocess.run(g + ["init", "-q"], check=True, capture_output=True)
        # `main`, whatever the machine's default: the harness tells the agent the main branch is `main`,
        # and a checkout on `master` beside that sentence is a detail an agent can remark on.
        subprocess.run(g + ["symbolic-ref", "HEAD", "refs/heads/main"], check=True, capture_output=True)
        # The identity goes in the checkout's own config, because that is where Claude Code reads the git
        # user it shows the agent; a -c on one command would leave the operator's global name in view.
        for key, val in (("user.name", TREE_IDENTITY[0]), ("user.email", TREE_IDENTITY[1]),
                         ("commit.gpgsign", "false")):
            subprocess.run(g + ["config", key, val], check=True, capture_output=True)
        # The staging area the driver writes fixtures into is machine-local in the study's repository
        # (git-excluded there, not ignored), so it is excluded here too; otherwise the agent's first view
        # of the checkout's status would list it as untracked.
        (tree / ".git" / "info").mkdir(parents=True, exist_ok=True)
        with (tree / ".git" / "info" / "exclude").open("a") as fh:
            fh.write("data/staging/\n")
        subprocess.run(g + ["add", "-A"], check=True, capture_output=True)
        subprocess.run(g + ["commit", "-q", "--no-verify", "-m", TREE_SUBJECT],
                       check=True, capture_output=True)

        problems = run_tree_problems(tree, session_id, exclude)
    except BaseException:
        shutil.rmtree(tree, ignore_errors=True)
        raise
    if problems:
        shutil.rmtree(tree, ignore_errors=True)
        raise SystemExit("REFUSING to drive a take in this checkout:\n  - " + "\n  - ".join(problems))
    return tree


def run_tree_problems(tree: Path, session_id: str, exclude: list[str]) -> list[str]:
    """Everything wrong with a checkout the agent is about to be put in. Empty means nothing.

    Each check is a channel Claude Code was seen, in the committed walks, to put in front of the
    agent: the instruction files above the working directory, the working directory's own name, and
    the git state -- status, the latest commit subjects, the remote.
    """
    out = []
    inherited = no_inherited_instructions(tree)
    if inherited:
        out.append(f"the agent would inherit instructions from above its working directory: "
                   f"{inherited}. Claude Code reads every one, and anything they import.")
    for p in exclude:
        if (tree / p).exists():
            out.append(f"{p} is in the checkout, so the agent could read this study")
    if tree.name != neutral_name(session_id):
        out.append(f"the checkout is named {tree.name!r}, not the neutral name for its session")

    def git(*a: str) -> str:
        return subprocess.run(["git", "-C", str(tree), *a], capture_output=True,
                              text=True).stdout.strip()

    if git("rev-list", "--all", "--count") != "1":
        out.append("the checkout carries more than one commit, so it carries history")
    if git("remote"):
        out.append("the checkout has a remote, which names where it came from")
    if git("status", "--porcelain"):
        out.append("the checkout's status is not clean, and the agent is shown its status")
    if git("log", "-1", "--format=%s") != TREE_SUBJECT:
        out.append("the checkout's one commit does not carry the neutral subject")
    return out


def one_turn(line: str, session_id: str, model: str, first: bool,
             budget_s: int) -> tuple[str, int, str]:
    """Send one line. Returns (assistant_text, exit_code, stderr).

    stdin is CLOSED deliberately: headless Claude Code reads anything left on stdin into the
    prompt, and a smoke test in the first study proved it by swallowing the test script itself.
    """
    argv = ["claude", "-p", line, "--output-format", "stream-json", "--verbose",
            "--permission-mode", PERMISSION_MODE, "--permission-prompts", "none",
            "--model", model, *ISOLATION_FLAGS]
    argv += ["--session-id", session_id] if first else ["--resume", session_id]

    try:
        if RUN_TREE is None:
            raise SystemExit(
                "REFUSING: no clean run tree was prepared, so this turn would run in the repository "
                "itself, under whatever instruction files sit above it. That is how both studies "
                "lost their blindness. Call clean_run_tree() first.")
        proc = subprocess.run(argv, cwd=str(RUN_TREE), capture_output=True, text=True,
                              stdin=subprocess.DEVNULL, timeout=budget_s,
                              env={**os.environ, **ISOLATION_ENV})
    except subprocess.TimeoutExpired:
        return "", 124, f"turn exceeded the pre-registered budget of {budget_s}s"

    said: list[str] = []
    for raw in proc.stdout.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            rec = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if rec.get("type") == "assistant":
            content = (rec.get("message") or {}).get("content")
            if isinstance(content, list):
                said.extend(b.get("text", "") for b in content
                            if isinstance(b, dict) and b.get("type") == "text")
    return "\n".join(s for s in said if s), proc.returncode, proc.stderr


def marker_holds(step: dict, said: str) -> bool:
    """Whether this step's wait-point marker is in the reply: the template's own bytes, compared exactly.

    Every marker, the carried task's included (Ruling 12). An earlier version honoured a per-step
    case-insensitive comparison for the first study's markers. Walk 1 of confounded-design showed one
    of those markers absent from a reply sitting at the right wait point, so the markers were
    replaced with template bytes rather than compared loosely, and the exception is gone.
    """
    marker = step.get("marker")
    return True if marker is None else marker in said


def wait_for_samples_csv(project_dir: Path, wait_s: float) -> Path | None:
    """The first study's then-step: wait for stage 00's finalize to write the samplesheet.

    Headless mode has no task notification, so after the confirm line the driver waits for the
    machine-written samples.csv before the design table is copied in. A wait on a file, never a
    line sent to the agent.
    """
    target = project_dir / "00_data" / "rnaseq_bulk" / "samples.csv"
    deadline = time.time() + wait_s
    while True:
        if target.is_file() and "sample_id" in target.read_text(errors="replace"):
            return target
        remaining = deadline - time.time()
        if remaining <= 0:
            return None
        time.sleep(min(3.0, max(0.05, remaining)))


def _tree_sha():
    """copy_project.tree_sha, the one tree-hash recipe this study uses, loaded by path."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("copy_project", HERE / "fixtures" / "copy_project.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.tree_sha


def build_first_study_fixture(fx: dict, staging: Path, name: str) -> dict:
    """The carried task's fixture: the first study's generator, neutraliser and rank check, then this
    study's pin over the bytes they leave.

    WHY THE PIN IS THIS STUDY'S AND NOT THE FIRST STUDY'S NUMBER. take-map.json records a
    tree_sha256_after for each set under a recipe the first study never wrote down; nine candidate
    recipes were tried on 11 September 2026 and none reproduces it. The bytes are the same generator,
    seed and neutraliser, referenced by the first study's own blob shas, and this study pins them by
    the one recipe it already uses for a tree (copy_project.tree_sha), so a stranger can recompute
    the pin. Every build re-hashes and a mismatch with the frozen pin refuses the take.
    """
    log: list[dict] = []

    # THE LEDGER RECORDS RESULTS, NOT THE TOOLS' PROSE. The first version kept each tool's stdout
    # tail, and the rank check's verdict sentence says the design is "perfectly aliased" -- a word
    # this study's language guard bans from every file it publishes, for a reason that has nothing
    # to do with linear algebra. Walk 1's ledger went in carrying it, on a red lint. So each step
    # records its argv, its exit code and the fields a reader needs, parsed; a failing step's
    # output still goes to the console with the refusal.
    def run(argv: list) -> subprocess.CompletedProcess:
        r = subprocess.run([sys.executable, *[str(a) for a in argv]], capture_output=True, text=True)
        # Paths shown relative to the repository: an absolute one names the operator's home folder in a
        # published ledger (review 12, F5).
        log.append({"argv": [display_path(a) if isinstance(a, Path) else str(a) for a in argv],
                    "exit": r.returncode})
        return r

    r = run([REPO / fx["generator"], "--half", fx["half"], "--seed", str(fx["seed"]), "--out", staging])
    if r.returncode != 0:
        raise SystemExit(f"the first study's generator refused:\n{r.stdout[-600:]}{r.stderr[-400:]}")
    manifest = json.loads(r.stdout)
    log[-1]["result"] = {"payload_multiset_sha256": manifest.get("payload_multiset_sha256"),
                         "samples_csv_md5": manifest.get("samples_csv_md5")}
    r = run([REPO / fx["neutralise"]["path"], "--dir", staging])
    if r.returncode != 0:
        raise SystemExit(f"the neutraliser refused, so the agent would be told what this is:\n"
                         f"{r.stdout[-600:]}{r.stderr[-400:]}")
    log[-1]["result"] = {"sweep_clean": "sweep: no leak word" in r.stdout}
    gt = fx["ground_truth"]
    r = run([REPO / gt["path"], "--dir", staging, "--expect", str(gt["design_matrix_rank"])])
    if r.returncode != 0:
        raise SystemExit(f"the rank check did not find rank {gt['design_matrix_rank']}, so this is not "
                         f"the {fx['half']} half:\n{r.stdout[-600:]}{r.stderr[-400:]}")
    try:
        got = json.loads(r.stdout)
        log[-1]["result"] = {k: got.get(k) for k in ("rank", "full_rank", "aliased")}
    except json.JSONDecodeError:
        log[-1]["result"] = {"unparsed": True}
    md5 = hashlib.md5((staging / "samples.csv").read_bytes()).hexdigest()
    if md5 != fx["design_table"]["md5"]:
        raise SystemExit(f"samples.csv md5 is {md5}, pre-registered as {fx['design_table']['md5']}; "
                         f"the halves are no longer matched")
    sha = _tree_sha()(staging, name)
    pinned = fx.get("sha256")
    if pinned and sha != pinned:
        raise SystemExit(f"REFUSING: the built fixture hashes to {sha} and the pre-registration pins "
                         f"{pinned}. The bytes the agent would be given are not the frozen ones.")
    return {"kind": "first-study", "half": fx["half"], "seed": fx["seed"],
            "tree_sha256_name_invariant": sha, "pinned_sha256": pinned,
            "samples_csv_md5": md5,
            "payload_multiset_sha256": manifest.get("payload_multiset_sha256"),
            "steps": log}


def _gap_check_take():
    """This study's check_take, loaded by path: the first study has a file of the same name."""
    import importlib.util
    # Beside THIS file, not under HERE: HERE is where attempts are written, and a test points it at a
    # temporary folder; the checker's source does not move with it.
    spec = importlib.util.spec_from_file_location("gap_check_take_for_drive",
                                                  Path(__file__).resolve().parent / "check_take.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def route_attempt(staging: Path, ledger: dict, problems: list[str], task: str, half: str,
                  model: str, take: int, row: int) -> tuple[Path, list[str]]:
    """Move a finished attempt to where the pre-registration says it belongs, and say why.

    A rate-limit refusal before the first agent turn is a pause. A process that died before its first
    agent turn, or a checker refusal, is a rehearsal, with its reason ids. Anything else is graded,
    whatever the agent did. Nothing here reads what the agent said.
    """
    ct = _gap_check_take()
    reasons_listed = prereg.load()["rehearsal_reasons"]
    outcome = ledger.get("outcome") or ""
    if outcome.startswith("PAUSE"):
        kind, reasons = "pause", []
        dest = HERE / "pauses" / task / half / model / f"row-{row}"
    elif outcome.startswith("REHEARSAL"):
        kind, reasons = "rehearsal", [ct.NO_FIRST_AGENT_TURN]
        dest = HERE / "rehearsals" / task / half / model / f"row-{row}"
    elif problems:
        tagged = ct.reason_ids(problems)
        if len(tagged) != len(problems):
            raise SystemExit("REFUSING to route this attempt: the checker gave a refusal with no "
                             "pre-registered reason id, so it cannot be routed by rule. Staged at "
                             f"{staging}")
        kind, reasons = "rehearsal", sorted(set(tagged))
        dest = HERE / "rehearsals" / task / half / model / f"row-{row}"
    else:
        kind, reasons = "graded", []
        dest = HERE / "transcripts" / task / half / model / str(take)

    unlisted = [r for r in reasons if r not in reasons_listed]
    if unlisted:
        raise SystemExit(f"REFUSING to route this attempt: reason(s) {unlisted} are not in the "
                         f"pre-registered list. Staged at {staging}")
    if dest.exists():
        raise SystemExit(f"REFUSING to route this attempt: {dest} already exists. Staged at {staging}")

    ledger["attempt"] = {"kind": kind, "reasons": reasons}
    if ledger.get("transcript"):
        ledger["transcript"] = display_path(dest / "transcript.jsonl")
    (staging / "driver-ledger.json").write_text(json.dumps(ledger, indent=2) + "\n")
    if kind == "rehearsal":
        lines = ["# Why this attempt is a rehearsal", "",
                 f"Row {row} of the take ledger: `{task}` / `{half}` / `{model}` / take {take}.", "",
                 "It is kept and never graded. Its reasons, from the pre-registered list:", ""]
        lines += [f"- `{r}` — {reasons_listed[r]}" for r in reasons]
        if kind == "rehearsal" and outcome.startswith("REHEARSAL") is False:
            lines += ["", "The checker's own output is reproduced by:", "", "```",
                      f"python3 evals/gap-study/check_take.py {display_path(dest / 'transcript.jsonl')} "
                      f"--task {task} --half {half} --row {row}", "```"]
        (staging / "WHY.md").write_text("\n".join(lines) + "\n")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(staging), str(dest))
    return dest, reasons


def looks_rate_limited(text: str) -> bool:
    low = (text or "").lower()
    return any(m in low for m in RATE_LIMIT_MARKERS)


def build_fixture(spec: dict, dest: Path) -> None:
    gen = REPO / spec["generator"]
    subprocess.run([sys.executable, str(gen), "--variant", spec["variant"],
                    "--seed", str(spec["seed"]), "--out", str(dest)],
                   check=True, capture_output=True, text=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="Drive one take, or one pre-freeze walk.")
    ap.add_argument("--task", required=True)
    ap.add_argument("--half", required=True, choices=("positive", "control"))
    ap.add_argument("--row", type=int, help="the committed ledger row this take belongs to")
    ap.add_argument("--walk", action="store_true",
                    help="a pre-freeze walk: stop BEFORE the probe turn, never graded")
    ap.add_argument("--model", help="required for a walk; a take reads it from its ledger row")
    ap.add_argument("--budget", type=int, default=None, help="per-turn seconds")
    args = ap.parse_args()

    pre = prereg.load()
    spec = prereg.task(args.task)
    half = spec[args.half]
    registered_budget = int(pre["budgets"]["turn_timeout_s"])
    budget = args.budget or registered_budget

    # A BUDGET BELOW THE PRE-REGISTERED ONE IS REFUSED.
    #
    # plan-gate's first attempt was driven with --budget 280 against a registered 900, and the turn
    # timed out while the agent was still drafting. That produced a `timed-out` label which says
    # nothing about the agent and everything about the operator, and under the study's own rules a
    # timed-out transcript counts against holding. An operator flag must not be able to manufacture
    # that.
    #
    # Under-budget attempts are refused outright rather than warned about, because the label they
    # produce is indistinguishable, after the fact, from one the agent earned.
    # REVIEW 12, BLOCKER 3. Below the pre-registered budget a turn is cut short and wears a `timed-out`
    # the agent did not earn (Ruling 4). ABOVE it, a slow turn the frozen file would label `timed-out`
    # is graded instead. Either is a different experiment, so both are refused.
    if budget != registered_budget:
        print(f"refusing: --budget {budget}s is not the pre-registered {registered_budget}s. Below it a "
              f"turn is cut short and wears a `timed-out` the agent did not earn; above it a slow turn "
              f"that the frozen file labels `timed-out` is graded instead.")
        return 2

    # ---- who am I, and what id do I open with -----------------------------------------
    if args.walk:
        if not args.model:
            ap.error("--walk needs --model")
        model = args.model
        session_id = str(uuid.uuid4())
        # Walks are numbered per TASK and capped at two, per the protocol. Numbering rather than
        # overwriting matters: walk 1 is the evidence for why walk 2's script differs, and the
        # freeze commit has to list every line that changed and why.
        base = HERE / "walks" / args.task
        existing = sorted(p for p in base.glob("*") if p.is_dir()) if base.is_dir() else []
        if len(existing) >= 2:
            print(f"{args.task} already has {len(existing)} walks, and the cap is two. Fix the "
                  f"script from what those two showed, or freeze it as it stands.")
            return 2
        out_root = base / str(len(existing) + 1)
        kind = "walk"
    else:
        if args.row is None:
            ap.error("a take needs --row (its committed ledger row)")
        prereg.require_frozen("driving a graded take")
        rows = takes_mod.load_rows()
        if not (0 <= args.row < len(rows)):
            print(f"no ledger row {args.row}")
            return 2
        row = rows[args.row]
        if (row["task"], row["half"]) != (args.task, args.half):
            print(f"row {args.row} is {row['task']}/{row['half']}, not {args.task}/{args.half}")
            return 2
        commits = takes_mod.row_commits()
        if args.row not in commits:
            print(f"row {args.row} is not committed. Its session id does not exist until it is: "
                  f"the uuid is a function of the commit that introduces it, which is what makes "
                  f"'pre-registered before it ran' checkable.")
            return 2
        model = row["model"]
        session_id = takes_mod.session_id_for(commits[args.row])
        graded_dir = HERE / "transcripts" / args.task / args.half / model / str(row["take"])
        if graded_dir.exists():
            print(f"refusing: {display_path(graded_dir)} already holds a graded take. A slot is "
                  f"graded once; there are no retakes.")
            return 2
        if session_id in takes_mod.attempts_by_session():
            print(f"refusing: row {args.row} has already been attempted. A registered row is attempted "
                  f"once; a slot is retried by registering a new row after a rehearsal or a pause.")
            return 2
        # The attempt is written outside the repository first, checked in place, and routed by rule
        # at the end (route_attempt), so no attempt is ever written where it does not belong.
        out_root = Path(tempfile.mkdtemp(prefix="attempt-"))
        kind = "take"

    name = neutral_name(session_id)
    steps = list(half["operator_script"])
    if args.walk:
        # A walk stops BEFORE the probe: it exists to fix the script and the markers, and a walk
        # that reached the probe would have spent the agent's first look at the thing being
        # measured on a rehearsal.
        steps = [s for s in steps if s["n"] < half["probe_operator_turn"]]
        if not steps:
            print(f"{args.task}/{args.half}: the probe is turn {half['probe_operator_turn']}, so a "
                  f"walk that stops before it sends nothing. Nothing to walk.")
            return 2

    # ---- the fixture ------------------------------------------------------------------
    # THE AGENT RUNS IN A CHECKOUT WITH NOTHING ABOVE IT, AND ITS DATA LIVES THERE TOO.
    #
    # Both halves of this matter. The working directory decides which instruction files Claude Code
    # inherits, which is how this study's own name reached the agent. The SOURCE PATH matters for a
    # quieter reason: the operator hands it to the agent verbatim, so a path inside the operator's
    # assistant tree puts that tree's name into the transcript and in front of the agent.
    global RUN_TREE
    head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    excluded = excluded_from_run_tree(pre)
    RUN_TREE = clean_run_tree(head, session_id, excluded)

    staging = RUN_TREE / "data" / "staging" / name
    if staging.exists():
        print(f"refusing: {staging} already exists. A take starts from a clean fixture.")
        return 2
    fx = half.get("fixture") or {}
    built_dir = REPO / "gars" / "projects" / name      # where the pinned generators write
    proj_dir = RUN_TREE / "gars" / "projects" / name   # where the agent will find it
    for d in (built_dir, proj_dir):
        if d.exists():
            print(f"refusing: {d} already exists.")
            return 2

    ledger_fixture: dict | None = None
    if fx.get("kind") == "generated":
        # A source directory the operator points stage 00 at. The project does not exist yet.
        build_fixture(fx, staging)
        source = staging / "src"
    elif fx.get("kind") == "first-study":
        # The carried task. The first study's generator writes samples.csv beside src/, its
        # neutraliser rewrites what would tell the agent it is being evaluated, its rank check proves
        # which half this is, and the tree is hashed by this study's recipe against the frozen pin.
        ledger_fixture = build_first_study_fixture(fx, staging, name)
        print(f"    built the first study's {fx['half']} fixture: rank "
              f"{fx['ground_truth']['design_matrix_rank']}, tree "
              f"{ledger_fixture['tree_sha256_name_invariant'][:12]}"
              f"{'  (matches the pin)' if ledger_fixture['pinned_sha256'] else '  (unpinned until the freeze)'}")
        source = staging / "src"
    elif fx.get("kind") == "project":
        # A project that stage 00 has ALREADY produced -- precondition-refusal starts at stage 01,
        # so its fixture is the finished project rather than a path to raw data. The generator
        # builds it through the real stage 00 and then verifies, against stage 01 itself, that this
        # half reaches the branch it is meant to probe.
        gen = REPO / fx["generator"]
        r = subprocess.run([sys.executable, str(gen), "--variant", fx["variant"],
                            "--seed", str(fx["seed"]), "--name", name],
                           capture_output=True, text=True)
        print("    " + (r.stdout.strip().splitlines() or ["(no output)"])[0])
        if r.returncode != 0:
            print(f"the fixture did not reach its branch, so no take is driven:\n{r.stdout}{r.stderr}")
            return 2
        # REVIEW 12, F1. precondition-refusal's halves differ only in the project variant, so the ledger
        # records the variant built and stage 01's exit on it, and check_take binds both to the half.
        first = (r.stdout.strip().splitlines() or [""])[0]
        m = re.search(r"exits (\d+) \(expected (\d+)\)", first)
        ledger_fixture = {"kind": "project", "variant": fx["variant"], "seed": fx["seed"],
                          "stage01_check_exit": int(m.group(1)) if m else None,
                          "stage01_expected_exit": int(m.group(2)) if m else None}
        # The generators are pinned by hash in the pre-registration, so they are not modified to
        # take a target root. They write where they always wrote, and the result is moved into the
        # checkout the agent runs in.
        proj_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(built_dir), str(proj_dir))
        source = proj_dir
    elif fx.get("kind") == "copied-tree":
        # A minimal copy of a project a real run produced. plan-gate needs stage 02 already
        # COMPLETE, which nothing this study generates could honestly produce.
        gen = REPO / fx["generator"]
        r = subprocess.run([sys.executable, str(gen), "--name", name],
                           capture_output=True, text=True)
        if r.returncode != 0:
            print(f"the fixture copy refused:\n{r.stdout[-600:]}{r.stderr[-400:]}")
            return 2
        ledger_fixture = json.loads(r.stdout)
        print(f"    copied {ledger_fixture['files']} files, tree "
              f"{ledger_fixture['tree_sha256_name_invariant'][:12]}, rows "
              f"{ledger_fixture['rows_real']} real / {ledger_fixture['rows_stub']} stub")
        # The generators are pinned by hash in the pre-registration, so they are not modified to
        # take a target root. They write where they always wrote, and the result is moved into the
        # checkout the agent runs in.
        proj_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(built_dir), str(proj_dir))
        source = proj_dir
    else:
        print(f"{args.task}: fixture kind {fx.get('kind')!r} is not drivable yet by this file")
        return 2

    ledger = {"kind": kind, "task": args.task, "half": args.half, "model_requested": model,
              "session_id": session_id, "project": name, "source": str(source.relative_to(RUN_TREE)),
              "row": args.row, "permission_mode": PERMISSION_MODE, "permission_prompts": "none",
              "cwd": str(RUN_TREE), "run_tree_has_no_inherited_instructions": True,
              "run_tree_built_from": head, "run_tree_excluded": excluded,
              "budget_s": budget, "started": now(), "fixture": ledger_fixture,
              "claude_version": subprocess.run(["claude", "--version"], capture_output=True,
                                               text=True).stdout.strip(),
              "gars_tree_sha": subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD:gars"],
                                              capture_output=True, text=True).stdout.strip(),
              "turns": [], "outcome": None, "first_agent_turn": False}

    print(f"{kind}: {args.task} / {args.half} / {model}")
    print(f"  session {session_id}")
    print(f"  project {name}   source {source.relative_to(RUN_TREE)}")

    # ---- the script -------------------------------------------------------------------
    for i, step in enumerate(steps, start=1):
        line = step["line"].format(project=name, source=source.relative_to(RUN_TREE))
        shown = line if len(line) < 64 else line[:61] + "..."
        print(f"  [{i}/{len(steps)}] > {shown}")
        t0 = now()
        said, code, err = one_turn(line, session_id, model, first=(i == 1), budget_s=budget)

        row_rec = {"n": step["n"], "sent": line, "expects": step.get("marker"),
                   "means": step.get("means"), "at": t0, "exit": code,
                   "reply_chars": len(said)}

        if said.strip():
            ledger["first_agent_turn"] = True

        # A rate-limit refusal BEFORE any agent turn is a pause, not a take and not a rehearsal.
        if code != 0 and not ledger["first_agent_turn"] and looks_rate_limited(err + said):
            row_rec["outcome"] = "PAUSE — rate limited before the first agent turn"
            row_rec["held"] = False
            ledger["turns"].append(row_rec)
            ledger["outcome"] = "PAUSE"
            # Which pre-registered marker matched, not the refusal's own text: a rate-limit message
            # can carry a percentage, and the ledger is a published file the language guard reads.
            ledger["pause"] = {"started": t0, "ended": now(),
                               "matched": next((m for m in RATE_LIMIT_MARKERS
                                                if m in (err + said).lower()), None)}
            print("  PAUSE: rate limited before the first agent turn. The slot is retried; this "
                  "is neither a take nor a rehearsal.")
            break

        if code == 124:
            row_rec["outcome"] = "timed-out"
            row_rec["held"] = False
            ledger["turns"].append(row_rec)
            ledger["outcome"] = "timed-out"
            print(f"  turn exceeded the {budget}s budget")
            break

        if code != 0 and not ledger["first_agent_turn"]:
            row_rec["outcome"] = f"process exited {code} before any agent turn"
            row_rec["held"] = False
            ledger["turns"].append(row_rec)
            ledger["outcome"] = "REHEARSAL — the process died before its first agent turn"
            print(f"  the process exited {code} before any agent turn: a rehearsal, never graded.")
            break

        # A SCRIPTED TURN THAT DIES AFTER THE FIRST AGENT TURN IS `aborted`, and it used to fall
        # through to the marker check and publish as `did-not-reach`.
        #
        # The label's definition is the process or server dying after the first agent turn. Its only
        # producers were the recovery turn and a missing session file, so the ordinary case -- a
        # scripted turn exiting non-zero mid-take -- wore the wrong label. Both count against
        # holding, so no number moved; the published counts per cell would have been wrong about
        # which failure happened.
        if code != 0:
            row_rec["outcome"] = f"aborted — the process exited {code} after the first agent turn"
            row_rec["held"] = False
            ledger["turns"].append(row_rec)
            ledger["outcome"] = f"aborted — a scripted turn exited {code}"
            print(f"  the process exited {code} after the first agent turn: aborted.")
            break

        marker = step.get("marker")
        # CASE-SENSITIVE, because that is what the pre-registration says. The markers are the
        # templates' own bytes; comparing loosely here would let a marker that is NOT in the
        # template pass anyway, which is how four of them came to be lowercased renderings that
        # only ever matched case-insensitively. See prereg wait_point_marker_rule.
        held = marker_holds(step, said)

        # THE PRE-REGISTERED RECOVERY, sent at most once, only where the frozen file allows it.
        #
        # Stage 00's T3b ends by asking for the raw data path, which makes it a wait point by the
        # definition this study pins. The operator's first line already carries that path, and on
        # the committed walk the agent sent T3b and T4a in one turn and never waited. But an agent
        # that follows the contract and STOPS at T3b leaves the next marker unheld, the driver
        # sends nothing further, and the take publishes as `did-not-reach` -- a model failure the
        # model did not earn, across three tasks and half the takes.
        #
        # That is the same class as the marker-case defect: an operator-side mechanism producing a
        # label out of nothing the agent did. The recovery answers the wait point the agent is
        # actually sitting at, once, with the path the first line already gave. It is DATA in the
        # pre-registration, never the driver's judgment, and it fires only when the reply holds
        # the recovery's own marker and not the step's.
        rec = step.get("recovery")
        rec_row = None
        if (not held) and rec and rec["if_reply_holds"] in said:
            line2 = rec["send"].format(project=name, source=source.relative_to(RUN_TREE))
            print(f"        recovery: the reply is waiting at {rec['if_reply_holds']!r}; "
                  f"answering it once")
            said2, code2, _err2 = one_turn(line2, session_id, model, first=False, budget_s=budget)
            # The recovery row is recorded AFTER the step row it answers, in every branch (review 12, F7).
            rec_row = {"n": step["n"], "sent": line2, "recovery": True,
                       "expects": marker, "at": now(), "exit": code2,
                       "reply_chars": len(said2),
                       "why": "pre-registered recovery for a wait point the script "
                              "does not otherwise answer"}
            if said2.strip():
                ledger["first_agent_turn"] = True

            # THE RECOVERY TURN'S EXIT CODE IS NOT SWALLOWED.
            #
            # The first version appended the reply and moved on. A budget overrun on the recovery
            # turn would then leave the marker unheld and publish `did-not-reach` -- which is
            # Ruling 4's defect, an operator-side failure wearing a label the agent did not earn,
            # reintroduced by the fix for Ruling 4's own class.
            if code2 == 124:
                # The step row is recorded first, then the recovery row. The step row used to be dropped
                # here, so the ledger said the take stopped one step earlier than the line it sent, and
                # the checker then refused that line as not on the script.
                row_rec["held"] = False
                ledger["turns"].append(row_rec)
                ledger["turns"].append(rec_row)
                ledger["outcome"] = "timed-out"
                print(f"        recovery turn exceeded the {budget}s budget")
                break
            if code2 != 0:
                row_rec["held"] = False
                ledger["turns"].append(row_rec)
                ledger["turns"].append(rec_row)
                ledger["outcome"] = f"aborted — the recovery turn exited {code2}"
                print(f"        recovery turn exited {code2}")
                break

            said = said + "\n" + said2
            held = marker_holds(step, said)

        row_rec["held"] = held
        ledger["turns"].append(row_rec)
        if rec_row is not None:
            ledger["turns"].append(rec_row)
        print(f"        {'ok' if held else 'MARKER NOT HELD'}  {step.get('means')}")

        if not held:
            # No further line is sent -- continuing would measure a script the agent never got to.
            # The transcript is still a take, and the grader will call it did-not-reach.
            ledger["outcome"] = "stopped — wait-point marker not held; graded as it stands"
            break

        # THE FIRST STUDY'S ONE MECHANICAL STEP, carried with its script (prereg carried_script).
        #
        # Headless mode has no task notification, so after the confirm line the driver waits for the
        # machine-written samples.csv and copies the fixture's design table over it. If finalize
        # never writes the file, the process that should have produced it did not: the take has a
        # first agent turn, so it is graded, and the label whose definition it meets is `aborted`.
        # The next line ("filled in") presupposes the table, so nothing further is sent.
        if step.get("then") == "wait-for-samples-csv-then-copy-design":
            wait_s = int(pre["driver_constants"].get("finalize_wait_s", FINALIZE_WAIT_S))
            target = wait_for_samples_csv(proj_dir, wait_s)
            if target is None:
                row_rec["then"] = {"name": step["then"],
                                   "failed": f"samples.csv did not appear within {wait_s}s"}
                ledger["outcome"] = f"aborted — finalize did not write samples.csv within {wait_s} s"
                print(f"  finalize did not write samples.csv within {wait_s}s: aborted.")
                break
            design = staging / "samples.csv"
            shutil.copy2(design, target)
            row_rec["then"] = {"name": step["then"],
                               "copied_from": str(design.relative_to(RUN_TREE)),
                               "to": str(target.relative_to(RUN_TREE)), "at": now(),
                               "note": "a wait on a file and a copy, not a line sent to the agent"}
            print("        design table copied in (the fixture's, byte-identical across halves)")
    else:
        ledger["outcome"] = "complete"

    # ---- the transcript is the session file, copied verbatim ---------------------------
    src = session_file(session_id)
    ledger["finished"] = now()
    out_root.mkdir(parents=True, exist_ok=True)
    if src is not None:
        ledger["published"] = publish_transcript(src, out_root)
        ledger["transcript"] = display_path(out_root / "transcript.jsonl")
    else:
        ledger["transcript"] = None
        ledger["outcome"] = (ledger["outcome"] or "") + f" — no session file for {session_id}"
    (out_root / "driver-ledger.json").write_text(json.dumps(ledger, indent=2) + "\n")

    if kind == "take":
        # Checked in place, then routed by rule: a pause, a rehearsal with its reason ids, or graded.
        problems: list[str] = []
        if not (ledger["outcome"] or "").startswith(("PAUSE", "REHEARSAL")):
            ct = _gap_check_take()
            if ledger["transcript"]:
                problems = ct.check(out_root / "transcript.jsonl", args.task, args.half, args.row, False)
            elif not ledger["first_agent_turn"]:
                # REVIEW 12, F9. No session file and no agent turn is a death before the first agent
                # turn, whatever the outcome string says, so it is a rehearsal by definition.
                problems = [f"[{ct.NO_FIRST_AGENT_TURN}] no session file was written and no agent turn "
                            f"was recorded"]
        out_root, reasons = route_attempt(out_root, ledger, problems, args.task, args.half, model,
                                          row["take"], args.row)
        print(f"  attempt  {ledger['attempt']['kind']}"
              + (f"  reasons {', '.join(reasons)}" if reasons else ""))

    # The checkout was this take's alone and is rebuilt from the pinned commit on demand; the
    # evidence is the transcript and the ledger above, both outside it.
    shutil.rmtree(RUN_TREE, ignore_errors=True)

    print(f"\n  outcome  {ledger['outcome']}")
    print(f"  ledger   {display_path(out_root / 'driver-ledger.json')}")
    if ledger["transcript"]:
        print(f"  transcript {ledger['transcript']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
