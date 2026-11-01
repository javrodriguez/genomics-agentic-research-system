#!/usr/bin/env python3
"""Drive one pre-registered take, or one pre-freeze walk, sending fixed lines and nothing else.

    python3 evals/gap-study-2/drive.py --task scope-read --half positive --row 12
    python3 evals/gap-study-2/drive.py --task scope-read --half positive --walk --model claude-opus-5

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

THE CHANGES FROM ROUND 2'S DRIVER. This file is a byte copy of evals/gap-study-2/drive.py at bf065fe
with five changes, and nothing else moves:

  1. Every turn also passes `--allowedTools` with the entries the pre-registration pins in
     `driver_change.allowed_tools`, and the ledger records them. Round 2 passed
     `--permission-mode auto` to every model and Haiku's sessions ran in `default` instead, where
     its stage-00 commands were denied by the harness. The allowlist gives every model the same
     working permission condition.

  2. Every turn passes `--permission-mode default` instead of round 2's `auto`: PERMISSION_MODE is
     `"default"` (RULING 7, 20 September 2026). Under `default` no classifier admits a command the
     list does not, so the allowlist of change 1 is the ENTIRE permission surface, identically for
     all three models. This is the one executable constant the round changes, and it is named here
     so the diff against round 2's file is exactly what this list says.

  3. The ledger's `permission_mode` is the mode THE SESSION RECORDED, read from the take's own
     published transcript, with the flag that was passed kept beside it as `permission_mode_passed`
     and the same reading repeated as `permission_mode_recorded` for this round's own checker.

     Round 2 wrote the flag into that field, and its own constant-binding rule compared it with the
     pre-registration's copy of the same constant -- a constant compared with itself, which could
     not fail and did not see the mismatch the pre-study found. Writing the RECORDED mode there
     makes check_take.py's byte-identical rule a real assertion: a take whose session recorded
     anything other than the pre-registered mode is routed as a rehearsal with reason
     `constant-binding`, by the copied checker, with no help from this round.

     RULING 2 (superseded) made that expectation per model, because the axis then carried two modes
     and a single value would have routed every take of the smallest model as a rehearsal. RULING 7
     removes the reason: `default` is passed to every model and every model is expected to record
     it, so one value covers the axis and the copied checker can carry the rule itself. The rehearsal
     that rule founds is admissible: `constant-binding` is not among this round's
     driver_decided_reasons, and check_results.py re-derives the field from the transcript when it
     re-runs the checker (review 2, blocker 1).

  4. One display string that spelled `evals/gap-study-2/check_take.py` into a rehearsal's WHY.md
     now takes the path from study.py, as round 2's own design says a path must.

  5. The per-task walk cap is four rather than two (RULING 8, 20 September 2026). Round 2's cap counts
     OPERATOR-SCRIPT REVISIONS -- its own comment says walk 1 is the evidence for why walk 2's script
     differs -- and this round revises no script: its three tasks are carried verbatim from round 2's
     frozen file and a test compares them byte for byte. Ruling 7 then required a walk on each of the
     two larger models under the new permission condition, with five of round 2's six slots already
     spent. The cap stays a cap; nothing about walk numbering, routing or recording moves.

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
import study  # noqa: E402
import takes as takes_mod  # noqa: E402
import scrub as scrub_mod  # noqa: E402

# ROUND 2, CP2 (structural lesson 7): the commit the checkout is exported from, whose gars tree a take is
# bound to. HEAD unless `--at <sha>` names another. Round 1 read HEAD in three places and each went red the
# day gars/ moved (Ruling 38); the draft's `head_readers` lists this line.
DEFAULT_AT = "HEAD"

# RULING 7, 20 September 2026. `default` on every turn of every take, for every model. Round 2 passed
# `auto` and the smallest model's sessions recorded `default` anyway, so the axis carried two conditions
# and a difference between that model's counts and the others' could still be auto's classifier. Under
# `default` the pre-registered allowlist is the ENTIRE permission surface, identically for all three, which
# is what makes this round's question true rather than merely softened. Review 1, blocker 4.
PERMISSION_MODE = "default"
# RULING 8: walks per task. Round 2's two counted operator-script revisions; this round revises no script.
WALK_CAP = 4
# The first study's constant, carried with its then-step: how long the driver waits for stage 00's
# finalize to write samples.csv before the design table is copied in. Pre-registered in
# driver_constants.finalize_wait_s; the value read at run time is the frozen file's.
FINALIZE_WAIT_S = 180
# Word-bounded, and without `resets` (review 13, F6): a pause is uncapped where a rehearsal is capped,
# so a death before the first turn whose message merely says "resets" must not be read as a pause.
RATE_LIMIT_MARKERS = ("rate limit", "usage limit", "weekly limit", "429")  # = driver_constants.rate_limit_markers

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

# ROUND 2, CP3 (Javier's ruling C, 14 Sep 2026): EACH TAKE'S SCRATCH LANDS INSIDE ITS OWN RUN TREE.
#
# Round 1's takes wrote scratch files into the machine's temporary folder: one agent redirected stage 00's output
# there and read its own file back. That folder is also where other copies of this project can sit, so the take
# checker is to refuse reads of the temp root outside the run tree. It could not do that without refusing a take
# for its own scratch. So every turn is given a temp folder inside its run tree, named by the variables tools read
# for one (TMPDIR, and TMP and TEMP for the tools that read those). The folder is git-excluded in the checkout, so
# the status the agent is shown stays clean. None of the three is on any recorded list or matches a published
# pattern, so the environment record is unchanged by them; driver_constants.run_tree_tmpdir carries both constants.
RUN_TREE_TMPDIR = ".tmp"
RUN_TREE_TMPDIR_VARIABLES = ("TMPDIR", "TMP", "TEMP")

# ROUND 2, CP3 (fix 4, structural lesson 14): THE ENVIRONMENT WAS A STATEMENT, AND IS NOW A RECORD.
#
# Round 1 said its takes ran on the subscription and nothing beside a transcript showed it (Ruling 34). And
# its driver passed os.environ wholesale, so a take driven from a Claude Code pane inherited that pane's
# session variables, its effort level among them. Two things change here, both data in the draft:
#
#   the child environment drops an explicit list of inherited session names (driver_constants.stripped_env,
#     J4 ruled yes: the twelve names, never a pattern), and the same environment is passed to every turn
#     and read by the record, so what is recorded is what was given;
#   environment.json, written beside the transcript before the first turn, names every variable in that
#     environment matching the published vocabulary (names, never values), says of each listed key,
#     billing route and subscription token whether it is absent, empty or set, and carries the credential
#     source the harness reported on every turn.
#
# A set API key or a set billing route stops the driver before any session opens: the money line.
# The vocabulary is read from the 2.1.267 binary; environment_record in the draft carries the same lists,
# and a test binds the two.
ENVIRONMENT_RECORD_FILE = "environment.json"
ENVIRONMENT_SCHEMA = 1
ENVIRONMENT_RECORD_SENTENCE = ("The names of the variables in the environment the session under test was given, "
                               "and whether each listed one was absent, empty or set; never a value.")
HARNESS_NAME_PATTERNS = (
    "^ANTHROPIC_", "^CLAUDE_CODE_USE_(BEDROCK|VERTEX|FOUNDRY)$", "^CLAUDE_CODE_SKIP_.*_AUTH$",
    "^CLAUDE_CODE_OAUTH_TOKEN$", "^CLAUDE_CODE_OAUTH_REFRESH_TOKEN$", "^CLAUDE_CODE_API_KEY_FILE_DESCRIPTOR$",
    "^CLAUDE_CODE_GATEWAY_TOKEN_FILE_DESCRIPTOR$", "^CLAUDE_CODE_SESSION_ACCESS_TOKEN$",
    "^CLAUDE_CODE_API_BASE_URL$", "^CLAUDE_CODE_CUSTOM_OAUTH_URL$", "^AWS_", "^GOOGLE_APPLICATION_CREDENTIALS$",
    "^AZURE_",
)
GENERIC_NAME_PATTERNS = ("(API_?KEY|AUTH_?TOKEN|ACCESS_?TOKEN|_TOKEN$|SECRET|CREDENTIAL|PASSWORD)",)
# A set one bills per token.
API_KEY_VARIABLES = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_FOUNDRY_API_KEY",
                     "ANTHROPIC_AWS_API_KEY", "CLAUDE_CODE_API_KEY_FILE_DESCRIPTOR", "AWS_BEARER_TOKEN_BEDROCK")
# A set one moves the session off the subscription.
BILLING_ROUTE_VARIABLES = ("CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY",
                           "ANTHROPIC_BASE_URL", "CLAUDE_CODE_API_BASE_URL")
# Recorded, never counted as an API key, never a stop.
SUBSCRIPTION_TOKEN_VARIABLES = ("CLAUDE_CODE_OAUTH_TOKEN", "CLAUDE_CODE_OAUTH_REFRESH_TOKEN",
                                "CLAUDE_CODE_SESSION_ACCESS_TOKEN")
CREDENTIAL_SOURCE_KEY = "system/init.apiKeySource"
# The draft's explicit list, read where every other pre-registered constant is read. Empty when the draft
# carries none, which is the unstripped condition.
STRIPPED_ENV: tuple[str, ...] = tuple((prereg.load().get("driver_constants") or {}).get("stripped_env") or ())


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
        # of the checkout's status would list it as untracked. The take's own temp folder (ruling C) is
        # excluded beside it, for the same reason: whatever a tool writes there must not reach that status.
        (tree / ".git" / "info").mkdir(parents=True, exist_ok=True)
        with (tree / ".git" / "info" / "exclude").open("a") as fh:
            fh.write("data/staging/\n")
            fh.write(f"{RUN_TREE_TMPDIR}/\n")
        subprocess.run(g + ["add", "-A"], check=True, capture_output=True)
        subprocess.run(g + ["commit", "-q", "--no-verify", "-m", TREE_SUBJECT],
                       check=True, capture_output=True)
        # Made after the one commit and before any turn, here rather than in main(), so every caller of this
        # function (the driver and the run-tree smoke) gets the folder child_env() points the take at.
        (tree / RUN_TREE_TMPDIR).mkdir()

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
    # The take's temp folder, read on the built tree: present, and excluded, so a file written there later
    # cannot reach the status (an empty folder never shows in status, so presence alone would prove nothing).
    if not (tree / RUN_TREE_TMPDIR).is_dir():
        out.append(f"the take's temp folder {RUN_TREE_TMPDIR}/ is missing from the checkout")
    elif subprocess.run(["git", "-C", str(tree), "check-ignore", "-q", f"{RUN_TREE_TMPDIR}/probe"],
                        capture_output=True).returncode != 0:
        out.append(f"the take's temp folder {RUN_TREE_TMPDIR}/ is not git-excluded, so a file a tool writes there "
                   f"would show in the git status the agent is shown")
    if git("log", "-1", "--format=%s") != TREE_SUBJECT:
        out.append("the checkout's one commit does not carry the neutral subject")
    return out


def stream_split(stdout: str) -> tuple[str, str]:
    """A turn's stream read for two different things: what the AGENT said, and what the HARNESS reported.

    REVIEW 15, BLOCKER 3. When the API refuses a request the harness writes an assistant record of its
    own and the process exits 1. The checker already excludes it from the agent-turn count; the driver
    did not, so `first_agent_turn` went true on it and the pause branch, which fires only before the
    first agent turn, was skipped: a rate limit would have been filed as a death before the first turn
    and counted against the rehearsal cap. Measured in the stream the driver reads
    (verification/api-error-stream-probe.txt): model `<synthetic>`, `is_api_error_message` true; the
    session file spells the same flag `isApiErrorMessage`, and both are kept out of the agent's text here.

    REVIEW 16, BLOCKER 2. Skipping that record also dropped its words from the only place any probe has
    shown a rate-limit message, and the pause branch was left deciding on stderr, which no probe records
    on a refused turn. A rate limit before the first agent turn would then have been filed as a death
    before the first turn: the same false record review 15 described, reintroduced by the fix for it.
    The harness's own words are kept here, apart from the agent's, and the branch that decides a pause
    reads both. The closing `result` record reports the same failure in a field the driver never read,
    so it is collected too.
    """
    said: list[str] = []
    harness: list[str] = []
    for raw in stdout.split("\n"):
        raw = raw.strip()
        if not raw:
            continue
        try:
            rec = json.loads(raw)
        except json.JSONDecodeError:
            continue
        kind = rec.get("type")
        if kind == "result":
            if (rec.get("is_error") or rec.get("isError")
                    or str(rec.get("subtype") or "").startswith("error")):
                harness.extend(str(rec.get(k)) for k in ("result", "error") if rec.get(k))
            continue
        if kind != "assistant":
            continue
        content = (rec.get("message") or {}).get("content")
        texts = ([b.get("text", "") for b in content
                  if isinstance(b, dict) and b.get("type") == "text"]
                 if isinstance(content, list) else [])
        if rec.get("is_api_error_message") or rec.get("isApiErrorMessage"):
            harness.extend(texts)
            continue
        said.extend(texts)
    return "\n".join(s for s in said if s), "\n".join(s for s in harness if s)


def stream_text(stdout: str) -> str:
    """What the agent itself said in this turn: the reply a wait-point marker is read against."""
    return stream_split(stdout)[0]


def stream_error_text(stdout: str) -> str:
    """What the harness itself reported in this turn, which is where a rate limit arrives."""
    return stream_split(stdout)[1]


def stream_init_source(stdout: str) -> str | None:
    """The credential source the harness reported for this turn: the top-level `apiKeySource` of the stream's
    `type=system, subtype=init` record.

    None when no init record carries a string there. Never the word "none": a source the harness did not
    report is recorded as unreported, and a spelling of our own would read as a value it gave.
    """
    for raw in (stdout or "").split("\n"):
        raw = raw.strip()
        if not raw:
            continue
        try:
            rec = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(rec, dict) and rec.get("type") == "system" and rec.get("subtype") == "init":
            src = rec.get("apiKeySource")
            return src if isinstance(src, str) else None
    return None


def modes_recorded(transcript: Path) -> set[str]:
    """Every value of the record-level `permissionMode` field, one JSON record at a time.

    REVIEW 2, NIT. This was a pattern over the file's text, which would also have read the same JSON
    echoed inside a tool result. The field sits at the top of the harness's own user-type records, so
    it is read from there and nowhere else.
    """
    out: set[str] = set()
    try:
        lines = transcript.read_text(errors="replace").split("\n")
    except OSError:
        return out
    for line in lines:
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(rec, dict) and isinstance(rec.get("permissionMode"), str):
            out.add(rec["permissionMode"])
    return out


def mode_recorded(transcript: Path) -> str:
    """The permission mode THIS session recorded, read from its own published transcript.

    `default` when every record that carries the field says default; any other recorded value wins
    over it (mode_precedence, review 3 NIT 6); `unrecorded` when no record carries the field.

    ROUND 3. Round 2's ledger recorded the flag the driver passed, and check_take.py's
    constant-binding rule compared it with the pre-registration's copy of the same constant, so the
    rule could not fail. The pre-study then read 34 of the smallest model's 36 transcripts as
    `default` where `auto` was passed. Reading the transcript here is what gives that rule something
    to measure; the checker is byte-identical to round 2's.
    """
    modes = modes_recorded(transcript)
    return mode_precedence(modes)


def mode_precedence(modes: set[str]) -> str:
    """One reading from the set of values a session recorded.

    REVIEW 3, NIT 6. The pre-study's precedence let `default` win whatever other records said, because
    under round 2's `auto` a `default` record was the anomaly. Under this round `default` is the
    expectation, so the anomaly is any OTHER value: a session that recorded `default` in one record and
    something else in another ran, for some of its turns, under a condition this round did not
    pre-register, and is read as that other value so the copied checker's constant rule sees it. No
    transcript on record carries two values; this is the reading if one ever does.
    """
    others = sorted(m for m in modes if m != "default")
    if others:
        return "auto" if "auto" in others else others[0]
    return "default" if "default" in modes else "unrecorded"


def run_tree_temp_env(tree: Path | None) -> dict:
    """TMPDIR, TMP and TEMP, each set to the run tree's own temp folder; nothing before a run tree exists.

    Before clean_run_tree there is no folder to point at, and no turn can be sent (one_turn refuses), so the only
    reader then is the money line, which reads names these three are not.
    """
    if tree is None:
        return {}
    folder = str(tree / RUN_TREE_TMPDIR)
    return {name: folder for name in RUN_TREE_TMPDIR_VARIABLES}


def child_env() -> dict:
    """The environment every turn's session is given: this process's, minus the stripped names, plus isolation,
    plus the run tree's temp folder.

    One function, used by one_turn and by the environment record, so the record describes the environment
    that was passed and not one rebuilt beside it. The temp variables are applied last, so no stripped list can
    take them out of a take's environment.
    """
    return {k: v for k, v in os.environ.items() if k not in STRIPPED_ENV} | ISOLATION_ENV | run_tree_temp_env(RUN_TREE)


def matched_by(name: str) -> str | None:
    """"harness" when a harness pattern matches the name, else "generic" when the generic shape does, else None.

    re.search on the name, case-sensitive, harness patterns tried first.
    """
    if any(re.search(p, name) for p in HARNESS_NAME_PATTERNS):
        return "harness"
    if any(re.search(p, name) for p in GENERIC_NAME_PATTERNS):
        return "generic"
    return None


def never_stripped_problems(stripped) -> list[str]:
    """Every stripped name that may never be stripped: one a harness pattern matches, or on any of the three lists.

    Stripping such a name would hide a key, a billing route or a login from the record and from the money
    line. The generic shape is not in this rule: it is a recording catch-all, and one of the twelve inherited
    session names (CLAUDE_CODE_MESSAGING_TOKEN) has its shape.
    """
    listed = set(API_KEY_VARIABLES) | set(BILLING_ROUTE_VARIABLES) | set(SUBSCRIPTION_TOKEN_VARIABLES)
    return [f"{n} is in driver_constants.stripped_env and "
            + ("is on a listed credential or billing list" if n in listed else "matches a harness name pattern")
            for n in stripped if n in listed or matched_by(n) == "harness"]


def _presence(env, names) -> dict:
    # Presence and emptiness only: a value is compared with the empty string and never kept.
    return {n: ("absent" if n not in env else "empty" if env[n] == "" else "set") for n in names}


def environment_record(child, parent, *, session_id: str, row: int | None, row_commit: str | None, task: str,
                       half: str, model: str, claude_version: str) -> dict:
    """environment.json, schema 1, before its first turn: per_turn empty and nothing reported yet."""
    api = _presence(child, API_KEY_VARIABLES)
    route = _presence(child, BILLING_ROUTE_VARIABLES)
    return {
        "record": ENVIRONMENT_RECORD_SENTENCE,
        "schema": ENVIRONMENT_SCHEMA,
        "session_id": session_id,
        "row": row,
        "row_commit": row_commit,
        "task": task,
        "half": half,
        "model_requested": model,
        "claude_version": claude_version,
        "written_before_first_turn": True,
        "name_patterns": {"harness": list(HARNESS_NAME_PATTERNS), "generic": list(GENERIC_NAME_PATTERNS)},
        "names_present": [{"name": n, "matched_by": matched_by(n)} for n in sorted(child) if matched_by(n)],
        "stripped_names": sorted(n for n in parent if n in STRIPPED_ENV and n not in child),
        "api_key_variables": api,
        "api_key_set": any(v == "set" for v in api.values()),
        "billing_route_variables": route,
        "billing_route_set": any(v == "set" for v in route.values()),
        "subscription_token_variables": _presence(child, SUBSCRIPTION_TOKEN_VARIABLES),
        "credential_source": {"key": CREDENTIAL_SOURCE_KEY, "per_turn": [], "reported": None},
    }


def money_line_names(rec: dict) -> list[str]:
    """The API-key and billing-route variable names a record shows set. Any one stops the driver."""
    return [n for block in ("api_key_variables", "billing_route_variables")
            for n, state in rec[block].items() if state == "set"]


def with_turns(rec: dict, turns: list[dict], sources: dict) -> dict:
    """The record with one per_turn entry per ledger turn row, recovery rows included, in the ledger's order.

    `n` and `recovery` are copied from the row itself (a step row carries no `recovery` field, so it reads
    false); `apiKeySource` is what that row's turn reported, or None. `reported` is the one value every turn
    gave, and None when any turn gave none or two turns differ.
    """
    per_turn = [{"n": r["n"], "recovery": bool(r.get("recovery")), "exit": r.get("exit"),
                 "apiKeySource": sources.get(id(r))} for r in turns]
    seen = {t["apiKeySource"] for t in per_turn}
    reported = next(iter(seen)) if len(seen) == 1 and None not in seen else None
    return {**rec, "credential_source": {**rec["credential_source"], "per_turn": per_turn, "reported": reported}}


def write_record_atomically(path: Path, rec: dict) -> None:
    """Written beside itself and moved into place, so a reader never meets half a record."""
    tmp = path.with_name(f".{path.name}.partial")
    tmp.write_text(json.dumps(rec, indent=2) + "\n")
    os.replace(tmp, path)


class TurnRows(list):
    """ledger["turns"], which rewrites the environment record each time a row is added.

    The loop appends rows in a separate place for each way a turn can end, and a record synced by hand in
    each would be one place short the day another is written. Appending is the one thing they share.
    """

    def __init__(self, on_append):
        super().__init__()
        self._on_append = on_append

    def append(self, row) -> None:
        super().append(row)
        self._on_append()


def one_turn(line: str, session_id: str, model: str, first: bool,
             budget_s: int) -> tuple[str, int, str, str, str | None]:
    """Send one line. Returns (assistant_text, exit_code, stderr, the harness's own error text,
    the credential source the harness reported, or None).

    stdin is CLOSED deliberately: headless Claude Code reads anything left on stdin into the
    prompt, and a smoke test in the first study proved it by swallowing the test script itself.
    """
    argv = ["claude", "-p", line, "--output-format", "stream-json", "--verbose",
            "--permission-mode", PERMISSION_MODE, "--permission-prompts", "none",
            "--model", model, *ISOLATION_FLAGS]
    argv += ["--allowedTools", *prereg.load()["driver_change"]["allowed_tools"]]
    argv += ["--session-id", session_id] if first else ["--resume", session_id]

    try:
        if RUN_TREE is None:
            raise SystemExit(
                "REFUSING: no clean run tree was prepared, so this turn would run in the repository "
                "itself, under whatever instruction files sit above it. That is how both studies "
                "lost their blindness. Call clean_run_tree() first.")
        proc = subprocess.run(argv, cwd=str(RUN_TREE), capture_output=True, text=True,
                              stdin=subprocess.DEVNULL, timeout=budget_s,
                              env=child_env())
    except subprocess.TimeoutExpired as exc:
        # A cut turn's stream up to the cut still carries its init record; the bytes may arrive undecoded.
        partial = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        return "", 124, f"turn exceeded the pre-registered budget of {budget_s}s", "", stream_init_source(partial)

    said, harness = stream_split(proc.stdout)
    return said, proc.returncode, proc.stderr, harness, stream_init_source(proc.stdout)


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
                      f"python3 {study.rel('check_take.py')} {display_path(dest / 'transcript.jsonl')} "
                      f"--task {task} --half {half} --row {row}", "```"]
        (staging / "WHY.md").write_text("\n".join(lines) + "\n")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(staging), str(dest))
    return dest, reasons


def matched_marker(text: str) -> str | None:
    """The pre-registered rate-limit marker this text carries, by the same bounded search that decides
    a pause (review 15, F6): the marker recorded and the marker that admitted the pause are one."""
    low = (text or "").lower()
    for m in RATE_LIMIT_MARKERS:
        if re.search(r"(?<![\w])" + re.escape(m) + r"(?![\w])", low):
            return m
    return None


def looks_rate_limited(text: str) -> bool:
    return matched_marker(text) is not None


def build_fixture(spec: dict, dest: Path) -> dict | None:
    """Build a generated fixture and return the generator's own manifest for the bytes it wrote.

    REVIEW 16, F7. The freeze pins `sha256` for these three tasks from the generator's `--manifest-only`
    run, and nothing on the take side ever recorded a hash to compare it with: the checker printed a
    note and passed. The generator has always been able to write its manifest beside the fixture rather
    than inside it, and its own docstring says the driver records it; it was never wired up.

    The manifest is taken from the SAME invocation that writes the fixture, never from a second
    `--manifest-only` run: a hash recomputed from the frozen variant and seed would match the pin
    whatever was actually built, which is a green that means nothing. What this binds is the recipe the
    driver ran -- a take built from the other half's variant or another seed records a hash that is not
    the pinned one. It does not bind the bytes on disk after the build; that is a published limitation.
    """
    gen = REPO / spec["generator"]
    with tempfile.TemporaryDirectory() as tmp:
        man_path = Path(tmp) / "manifest.json"
        subprocess.run([sys.executable, str(gen), "--variant", spec["variant"],
                        "--seed", str(spec["seed"]), "--out", str(dest),
                        "--manifest-out", str(man_path)],
                       check=True, capture_output=True, text=True)
        try:
            man = json.loads(man_path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            # REVIEW 17, F2. It used to return None, and the driver then filed the take with no
            # fixture record at all, which the checker passes with a note. A take nobody can bind to
            # its fixture is not a take this study grades.
            raise SystemExit(f"REFUSING: the generator wrote no readable manifest for this fixture "
                             f"({exc!r}), so the take could not be bound to the fixture it ran "
                             f"against. Nothing was sent to a model.")
    # REVIEW 20, F1. The carried and copied builders refuse a tree that differs from their pin before a
    # session opens; this one recorded the hash and left the mismatch to the checker, where it becomes a
    # refusal no record can clear. Symmetry costs three lines and gives the state a name.
    got = man.get("fixture_sha256")
    pin = spec.get("sha256")
    if pin and got != pin:
        raise SystemExit(f"REFUSING: the generated fixture hashes to {str(got)[:12]} and this half pins "
                         f"{str(pin)[:12]}. Nothing was sent to a model.")
    return {"kind": "generated", "variant": spec["variant"], "seed": spec["seed"],
            "fixture_sha256": got}


def build_take_fixture(fx: dict, run_tree: Path, name: str) -> tuple[dict | None, Path | None]:
    """Build this half's fixture INSIDE the run tree and return (ledger record, source), or (None, None)
    after saying why nothing can be driven.

    ROUND 2, CP3: EVERY KIND IS BUILT WHERE THE AGENT WILL FIND IT. Round 1 built the precondition-refusal
    project under this repository's checkout and moved it into the run tree afterwards. Stage 00 records the
    source path it linked, absolutely, in CONTEXT.md, HISTORY.md and every raw/ link, so the agent read a path
    inside the checkout; the read-outside-the-checkout control refuses exactly that. The project generator now
    takes the run tree's workspace and staging folder, and the copied tree the run tree's projects folder, so
    nothing is written into the checkout and nothing moves. TheFixtureNamesNoPathOutsideTheRunTree builds every
    kind this way and reads every byte and link target for the checkout.
    """
    staging = run_tree / "data" / "staging" / name
    proj_dir = run_tree / "gars" / "projects" / name   # where the agent will find it
    kind = fx.get("kind")
    if kind == "generated":
        # A source directory the operator points stage 00 at. The project does not exist yet.
        return build_fixture(fx, staging), staging / "src"
    if kind == "first-study":
        # The carried task. The first study's generator writes samples.csv beside src/, its
        # neutraliser rewrites what would tell the agent it is being evaluated, its rank check proves
        # which half this is, and the tree is hashed by this study's recipe against the frozen pin.
        ledger_fixture = build_first_study_fixture(fx, staging, name)
        print(f"    built the first study's {fx['half']} fixture: rank "
              f"{fx['ground_truth']['design_matrix_rank']}, tree "
              f"{ledger_fixture['tree_sha256_name_invariant'][:12]}"
              f"{'  (matches the pin)' if ledger_fixture['pinned_sha256'] else '  (unpinned until the freeze)'}")
        return ledger_fixture, staging / "src"
    if kind == "project":
        # A project that stage 00 has ALREADY produced -- precondition-refusal starts at stage 01,
        # so its fixture is the finished project rather than a path to raw data. The generator
        # builds it through the real stage 00 and then verifies, against stage 01 itself, that this
        # half reaches the branch it is meant to probe.
        gen = REPO / fx["generator"]
        r = subprocess.run([sys.executable, str(gen), "--variant", fx["variant"],
                            "--seed", str(fx["seed"]), "--name", name,
                            "--workspace", str(run_tree / "gars"), "--staging", str(run_tree / "data" / "staging")],
                           capture_output=True, text=True)
        print("    " + (r.stdout.strip().splitlines() or ["(no output)"])[0])
        if r.returncode != 0:
            print(f"the fixture did not reach its branch, so no take is driven:\n{r.stdout}{r.stderr}")
            return None, None
        if not proj_dir.is_dir():
            print(f"the project fixture was not built in the run tree ({proj_dir.relative_to(run_tree)} is "
                  f"missing), so no take is driven")
            return None, None
        # REVIEW 12, F1. precondition-refusal's halves differ only in the project variant, so the ledger
        # records the variant built and stage 01's exit on it, and check_take binds both to the half.
        first = (r.stdout.strip().splitlines() or [""])[0]
        m = re.search(r"exits (\d+) \(expected (\d+)\)", first)
        return ({"kind": "project", "variant": fx["variant"], "seed": fx["seed"],
                 "stage01_check_exit": int(m.group(1)) if m else None,
                 "stage01_expected_exit": int(m.group(2)) if m else None}, proj_dir)
    if kind == "copied-tree":
        # A minimal copy of a project a real run produced. plan-gate needs stage 02 already
        # COMPLETE, which nothing this study generates could honestly produce.
        gen = REPO / fx["generator"]
        r = subprocess.run([sys.executable, str(gen), "--name", name,
                            "--projects", str(run_tree / "gars" / "projects")],
                           capture_output=True, text=True)
        if r.returncode != 0:
            print(f"the fixture copy refused:\n{r.stdout[-600:]}{r.stderr[-400:]}")
            return None, None
        ledger_fixture = json.loads(r.stdout)
        # REVIEW 19, BLOCKER 3. The carried builder refuses a tree that differs from its pin before a
        # session opens; this one printed the hash and compared it with nothing, so a take could be
        # driven from an altered origin project and honestly recorded.
        pin = fx.get("sha256") or fx.get("tree_sha256_name_invariant")
        built = ledger_fixture.get("tree_sha256_name_invariant")
        if pin and built != pin:
            print(f"REFUSING: the copied fixture hashes to {str(built)[:12]} and this half pins "
                  f"{str(pin)[:12]}. Nothing was sent to a model.")
            return None, None
        print(f"    copied {ledger_fixture['files']} files, tree "
              f"{ledger_fixture['tree_sha256_name_invariant'][:12]}, rows "
              f"{ledger_fixture['rows_real']} real / {ledger_fixture['rows_stub']} stub")
        return ledger_fixture, proj_dir
    print(f"fixture kind {kind!r} is not drivable yet by this file")
    return None, None


def main() -> int:
    ap = argparse.ArgumentParser(description="Drive one take, or one pre-freeze walk.")
    ap.add_argument("--task", required=True)
    ap.add_argument("--half", required=True, choices=("positive", "control"))
    ap.add_argument("--row", type=int, help="the committed ledger row this take belongs to")
    ap.add_argument("--walk", action="store_true",
                    help="a pre-freeze walk: stop BEFORE the probe turn, never graded")
    ap.add_argument("--model", help="required for a walk; a take reads it from its ledger row")
    ap.add_argument("--budget", type=int, default=None, help="per-turn seconds")
    ap.add_argument("--at", default=DEFAULT_AT, metavar="<sha>",
                    help="the commit the checkout is exported from and whose gars tree is checked (default: HEAD)")
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

    # ---- the environment the session is given: the money line, before anything is built -----
    # ROUND 2, CP3. A stripped name that hides a key, a route or a login is refused, and so is a set API key
    # or billing route in the environment every turn would be passed. Only names are printed.
    bad_strip = never_stripped_problems(STRIPPED_ENV)
    if bad_strip:
        print("refusing: " + "; ".join(bad_strip) + ". Stripping it would hide it from the environment record "
              "and from the money line. Nothing was sent.")
        return 2
    money = money_line_names(environment_record(child_env(), os.environ, session_id="", row=None,
                                                row_commit=None, task=args.task, half=args.half, model="",
                                                claude_version=""))
    if money:
        print(f"refusing: {', '.join(money)} set in the environment the session would be given. A set API-key "
              f"variable bills per token and a set billing-route variable moves the session off the "
              f"subscription, so no session is opened. Nothing was sent.")
        return 2

    # ---- who am I, and what id do I open with -----------------------------------------
    if args.walk:
        if not args.model:
            ap.error("--walk needs --model")
        model = args.model
        session_id = str(uuid.uuid4())
        row_commit = None
        # Walks are numbered per TASK and capped, per the protocol. Numbering rather than overwriting
        # matters: walk 1 is the evidence for why walk 2's script differs, and the freeze commit has to
        # list every line that changed and why. ROUND 3, RULING 8: the cap is four rather than two,
        # because that reason counts SCRIPT REVISIONS and this round revises no script -- its tasks are
        # carried verbatim -- while ruling 7 needed a walk per model under a condition adopted after
        # five of the six original slots were already spent.
        base = HERE / "walks" / args.task
        existing = sorted(p for p in base.glob("*") if p.is_dir()) if base.is_dir() else []
        if len(existing) >= WALK_CAP:
            print(f"{args.task} already has {len(existing)} walks, and the cap is {WALK_CAP}. Fix the "
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
        row_commit = commits[args.row]
        session_id = takes_mod.session_id_for(row_commit)
        # REVIEW 13, F3. The checkout is exported from HEAD, so HEAD must carry the system under test the
        # study froze; the take checker binds the tree the ledger records as well.
        pinned_gars = pre["system_under_test"]["gars_tree_sha"]
        head_gars = subprocess.run(["git", "-C", str(REPO), "rev-parse", f"{args.at}:gars"],
                                   capture_output=True, text=True).stdout.strip()
        if head_gars != pinned_gars:
            print(f"refusing: {args.at} carries gars tree {head_gars[:12]} and the pre-registration pins "
                  f"{pinned_gars[:12]}. A take is driven only against the system under test the study froze.")
            return 2
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
    head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--verify", "--quiet", f"{args.at}^{{commit}}"],
                          capture_output=True, text=True).stdout.strip()
    if not head:
        print(f"refusing: --at {args.at} names no commit in this repository, so there is no checkout to export.")
        return 2
    excluded = excluded_from_run_tree(pre)
    RUN_TREE = clean_run_tree(head, session_id, excluded)

    staging = RUN_TREE / "data" / "staging" / name
    if staging.exists():
        print(f"refusing: {staging} already exists. A take starts from a clean fixture.")
        return 2
    fx = half.get("fixture") or {}
    proj_dir = RUN_TREE / "gars" / "projects" / name   # where the agent will find it
    if proj_dir.exists():
        print(f"refusing: {proj_dir} already exists.")
        return 2

    # Built inside the run tree, every kind (round 2, CP3): nothing is built in this repository's checkout
    # and moved, so no path the agent reads names the checkout.
    ledger_fixture, source = build_take_fixture(fx, RUN_TREE, name)
    if source is None:
        print(f"{args.task}: no take is driven")
        return 2

    ledger = {"kind": kind, "task": args.task, "half": args.half, "model_requested": model,
              "session_id": session_id, "project": name, "source": str(source.relative_to(RUN_TREE)),
              "row": args.row, "permission_mode": PERMISSION_MODE, "permission_prompts": "none",
              "permission_mode_passed": PERMISSION_MODE,
              "permission_mode_expected": (pre["driver_constants"].get("permission_mode_expected") or {})
                                          .get(model),
              "permission_mode_recorded": None,
              "allowed_tools": list(pre["driver_change"]["allowed_tools"]),
              "cwd": str(RUN_TREE), "run_tree_has_no_inherited_instructions": True,
              "run_tree_built_from": head, "run_tree_excluded": excluded,
              "budget_s": budget, "started": now(), "fixture": ledger_fixture,
              "claude_version": subprocess.run(["claude", "--version"], capture_output=True,
                                               text=True).stdout.strip(),
              "gars_tree_sha": subprocess.run(["git", "-C", str(REPO), "rev-parse", f"{head}:gars"],
                                              capture_output=True, text=True).stdout.strip(),
              "turns": [], "outcome": None, "first_agent_turn": False}

    # ---- the environment record, before the first turn ------------------------------------
    # Built from the same child_env() every turn is passed. Unwritable, nothing is sent: a take with no
    # record is one the checker refuses, and a session opened for it would be spent on a rehearsal.
    env_path = out_root / ENVIRONMENT_RECORD_FILE
    env_rec = environment_record(child_env(), os.environ, session_id=session_id,
                                 row=None if args.walk else args.row, row_commit=row_commit, task=args.task,
                                 half=args.half, model=model, claude_version=ledger["claude_version"])
    turn_sources: dict[int, str | None] = {}

    def sync_environment() -> None:
        write_record_atomically(env_path, with_turns(env_rec, ledger["turns"], turn_sources))

    try:
        out_root.mkdir(parents=True, exist_ok=True)
        sync_environment()
    except OSError as exc:
        shutil.rmtree(RUN_TREE, ignore_errors=True)
        print(f"refusing: the environment record could not be written ({type(exc).__name__}), so no line is "
              f"sent. Nothing was sent.")
        return 2
    ledger["turns"] = TurnRows(sync_environment)

    print(f"{kind}: {args.task} / {args.half} / {model}")
    print(f"  session {session_id}")
    print(f"  project {name}   source {source.relative_to(RUN_TREE)}")

    # ---- the script -------------------------------------------------------------------
    for i, step in enumerate(steps, start=1):
        line = step["line"].format(project=name, source=source.relative_to(RUN_TREE))
        shown = line if len(line) < 64 else line[:61] + "..."
        print(f"  [{i}/{len(steps)}] > {shown}")
        t0 = now()
        # `key_source`, not `source`: that name is the fixture path every line is rendered with.
        said, code, err, harness_said, key_source = one_turn(line, session_id, model, first=(i == 1),
                                                             budget_s=budget)

        row_rec = {"n": step["n"], "sent": line, "expects": step.get("marker"),
                   "means": step.get("means"), "at": t0, "exit": code,
                   "reply_chars": len(said)}
        turn_sources[id(row_rec)] = key_source

        if said.strip():
            ledger["first_agent_turn"] = True

        # A rate-limit refusal BEFORE any agent turn is a pause, not a take and not a rehearsal.
        # The harness's own report of the refusal is read here too (review 16, blocker 2): stderr is
        # not where any probe has seen it.
        # REVIEW 17, F3. Joined with no separator, a marker sitting at the join lost its word
        # boundary and the bounded search missed it: 'Error' + '429 ...' reads as 'Error429'.
        refusal = "\n".join(x for x in (err, harness_said, said) if x)
        if code != 0 and not ledger["first_agent_turn"] and looks_rate_limited(refusal):
            row_rec["outcome"] = "PAUSE — rate limited before the first agent turn"
            row_rec["held"] = False
            ledger["turns"].append(row_rec)
            ledger["outcome"] = "PAUSE"
            # Which pre-registered marker matched, not the refusal's own text: a rate-limit message
            # can carry a percentage, and the ledger is a published file the language guard reads.
            ledger["pause"] = {"started": t0, "ended": now(),
                               "matched": matched_marker(refusal)}
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
            said2, code2, _err2, _harness2, key_source2 = one_turn(line2, session_id, model, first=False,
                                                                   budget_s=budget)
            # The recovery row is recorded AFTER the step row it answers, in every branch (review 12, F7).
            rec_row = {"n": step["n"], "sent": line2, "recovery": True,
                       "expects": marker, "at": now(), "exit": code2,
                       "reply_chars": len(said2),
                       "why": "pre-registered recovery for a wait point the script "
                              "does not otherwise answer"}
            turn_sources[id(rec_row)] = key_source2
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
        # ROUND 3, change 3 (Rulings 2 and 7). What the session RECORDED, over what was passed. The
        # copied checker reads `permission_mode`, so from here its constant-binding rule is an
        # assertion about the session rather than about a flag.
        recorded = mode_recorded(out_root / "transcript.jsonl")
        ledger["permission_mode"] = recorded
        ledger["permission_mode_recorded"] = recorded
    else:
        ledger["permission_mode"] = "unrecorded"
        ledger["permission_mode_recorded"] = "unrecorded"
        ledger["transcript"] = None
        ledger["outcome"] = (ledger["outcome"] or "") + f" — no session file for {session_id}"
    # The record carries every turn row by now (TurnRows); it is written once more so its bytes are the final
    # ones, and the ledger binds exactly those bytes. It sits in out_root, so route_attempt moves it with the
    # folder and the in-place check below reads it where the ledger says.
    sync_environment()
    ledger["environment"] = {"file": ENVIRONMENT_RECORD_FILE,
                             "sha256": hashlib.sha256(env_path.read_bytes()).hexdigest()}
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


# =====================================================================================================================
# ROUND 4, CP2: THE DRIVE LIFECYCLE, PART 1 -- THE COMMIT STEP (lane w6e, slice S5 of next-slices-2026-10-11;
# ownership moved here from lane w1a's copy record under glitch-1b's ruling S5-gap4-1).
#
# THE CHANGES FROM ROUND 3'S DRIVER, ROUND 4 (the plan's named-changes PATTERN). They are written here, beside the
# code, and not in the docstring's block at the top, so that every line other files cite by number (drive.py:149,
# 158-186, 170, 241-242, 741, 750, 1346, 1348, and the constants test_run_take reads by ast) stays where it is.
# Everything above this banner is round 3's driver, byte for byte.
#
#   R4-1. TakeRepo: the repo object batch.Batch is handed, with its three doors, register, commit_records and
#         history. It holds no state a restart could inherit except the committed record (its RegistrationGuard is
#         process-local, as takes.py requires).
#   R4-2. THE COMMIT STEP RE-STAGES AND RE-HASHES AFTER MASKING (lane w4c's call Q3; CP2-requirements, "Re-stage and
#         re-hash after masking"). The take's files and the outcome ledger are staged, and the scan list is built
#         from the staged index (record checks read the index). box/scan_record.py then masks agent-text hits ON
#         DISK. So every scanned file is staged AGAIN, and every staged blob's sha256 must equal the scan's
#         `sha256_after` before anything is committed. A commit of the first staging would carry the unmasked value;
#         a file that moved after the scan would carry bytes nobody scanned. Either refuses, and nothing is committed.
#   R4-3. Every staged name must be one of the take's declared files or the ledger, and every one of those must be
#         staged: a stray staged file refuses the commit rather than riding it unscanned.
#   R4-4. history() IS CHRONOLOGICAL: takes.read_history, the committed outcomes and rulings in commit order
#         (CP2-requirements, w1b fold 4 open question 10), never the two files concatenated, so a ruling committed
#         after its outcome comes back after it.
#   R4-5. A RESTART IS REFUSED WHILE A LEAKED CONTAINER REMAINS (open question 11). register() first lists every
#         container (box/run_take.py's refuse_restart_if_leaked, a full-id listing with no filter) and refuses,
#         naming it, while any id the committed history records as `leaked_container` is still present. batch.py
#         registers before it launches, so a refused register launches nothing.
#   R4-6. preflight_take is the driver's one road to preflight: S1's composition entry point, every argument passed
#         through. The driver never reads or projects a take lock itself (CP2-preflight-2).
#
# Part 2 (lane w6h, S6; ownership of this file moved to w6h under glitch-1b's ruling S6-gap4-1) adds R4-7 to R4-12
# in its own banner below: launch, preflight, the turns, quiescence, the drive step's scan, teardown, the
# finally-path cleanup on every refusal, and a refused commit restoring the ledger (ruling S6-Q2).
# =====================================================================================================================

from box import preflight as _preflight  # noqa: E402
from box import run_take as _run_take  # noqa: E402
from box import scan_record as _scan_record  # noqa: E402
import importlib.util as _importlib_util  # noqa: E402
# The box lane's ownership road (box/ownership.py, 81ede46d): imported like the box modules above wherever the file is
# (the merged head); absent from this tree, it stays None and TakeDriver.launch refuses (ownership_problems). A module
# that is present but fails to import raises here, never read as absent.
_ownership = None
if _importlib_util.find_spec("box.ownership") is not None:
    from box import ownership as _ownership  # noqa: E402
# The box lane's run-tree settings guard (box/settings_guard.py, d3fd5305; ownership review finding 1), the same way.
_settings_guard = None
if _importlib_util.find_spec("box.settings_guard") is not None:
    from box import settings_guard as _settings_guard  # noqa: E402

OUTCOMES_FILE = takes_mod.HISTORY_FILES[0]
OUTCOME_KIND = "ledger"
COMMIT_SUBJECT = "Record one take's outcome and its records"


class CommitRefused(RuntimeError):
    """The commit step committed nothing. Its message names paths, lines and kinds, never a secret's value."""


def _git_bytes(repo: Path, *args: str) -> bytes:
    got = subprocess.run(["git", "-C", str(repo), *args], capture_output=True)
    if got.returncode:
        raise CommitRefused(f"git {args[0]} failed (exit {got.returncode})")
    return got.stdout


def _staged_names(repo: Path) -> list[str]:
    raw = _git_bytes(repo, "diff", "--cached", "--name-only", "--no-renames", "-z")
    return [n.decode("utf-8") for n in raw.split(b"\0") if n]


def preflight_take(runtime, *, launched, sidecar, lock_path: str, harness: str, hosts: dict, evidence_dir: str,
                   begin_reply, caller_env=None) -> dict:
    """R4-6: S1's entry point, unchanged arguments, its record returned as it is. Its typed refusals (a lock or launch
    record it cannot use) propagate to the drive step, which records a pre-turn refusal and cleans up (S6)."""
    return _preflight.collect_and_evaluate(
        runtime, launched=launched, sidecar=sidecar, lock_path=lock_path, harness=harness, hosts=hosts,
        evidence_dir=evidence_dir, begin_reply=begin_reply, caller_env=caller_env)


class TakeRepo:
    """batch.Batch's repo (R4-1): register(row, attempt), commit_records(row, attempt, outcome), history().

    runtime          the container runtime protocol box/run_take.py uses (run(argv, env=, timeout=))
    record_files     (row, attempt) -> [(absolute path, scan_record kind)]: the take's record files, from the drive
                     step; every one inside the repository, a regular file, listed once
    secrets          () -> [(kind, value)], read at commit time and never held by this object
    rules_scanner    scan_record's rules scanner (required; the real one refuses while it is PENDING)
    holdout_matcher  scan_record's holdout matcher, injected on the Mac (None records "not-checked")
    on_published     (row, attempt) -> None, run once the take's commit has landed (R4-7, R4-11: TakeDriver.published
                     deletes the per-take config folder then and only then); None runs nothing
    """

    def __init__(self, *, runtime, record_files, secrets, rules_scanner, holdout_matcher=None, root=HERE,
                 repo=REPO, caller_env=None, on_published=None):
        if not callable(getattr(runtime, "run", None)):
            raise TypeError("runtime must offer run(argv, env=, timeout=)")
        for name, fn in (("record_files", record_files), ("secrets", secrets), ("rules_scanner", rules_scanner)):
            if not callable(fn):
                raise TypeError(f"{name} must be callable")
        self.runtime, self.record_files, self.secrets = runtime, record_files, secrets
        self.rules_scanner, self.holdout_matcher, self.caller_env = rules_scanner, holdout_matcher, caller_env
        self.root, self.repo = Path(root).resolve(), Path(repo).resolve()
        self.guard = takes_mod.RegistrationGuard()
        if on_published is not None and not callable(on_published):
            raise TypeError("on_published must be callable")
        self.on_published, self.publish_problems, self._touched = on_published, [], []

    # ------------------------------------------------------------------------------------------- history (R4-4)
    def history(self) -> list:
        return takes_mod.read_history(root=self.root, repo=self.repo)

    # ------------------------------------------------------------------------------------------- restart (R4-5)
    def leaked_ids(self) -> list:
        """Every container id the committed outcomes record as leaked, once each, in commit order: leaked_container
        and every id of leaked_containers (ruling S6-gap4-2: a take's surviving sidecar or proxy too)."""
        ids = []
        for entry in self.history():
            if not takes_mod.batch.is_outcome(entry):     # a take's or a night ruling
                continue
            missing = [k for k in ("leaked_container", "leaked_containers") if k not in entry]
            if missing:          # W6H-R2-1 (S6b): a typed refusal, never a bare KeyError
                raise HistoryRefused(f"the committed outcome of slot {entry.get('slot')!r} attempt "
                                     f"{entry.get('attempt')!r} carries no {', '.join(missing)}; a restart cannot "
                                     f"read what it leaked")
            for cid in [entry["leaked_container"], *(entry["leaked_containers"] or [])]:
                if cid is not None and cid not in ids:
                    ids.append(cid)
        return ids

    def refuse_restart(self) -> None:
        ids = self.leaked_ids()
        _run_take.refuse_restart_if_leaked(self.runtime, [i for i in ids if not i.startswith(NETWORK_PREFIX)],
                                           caller_env=self.caller_env)
        nets = leaked_networks(self.runtime, ids, caller_env=self.caller_env)      # R-S6-net (S6b)
        if nets:
            raise _run_take.LeakedContainer(f"restart refused: leaked network(s) still present: {', '.join(nets)}")

    def register(self, row: dict, attempt: int) -> str:
        self.refuse_restart()
        return takes_mod.commit_registration(row, attempt, guard=self.guard, root=self.root, repo=self.repo)

    # ------------------------------------------------------------------------------------------- commit (R4-2, R4-3)
    def _reserved(self) -> set:
        """W6E-R1-2: the study's own ledgers (outcomes.json, rulings.json, takes.json), never a take's record."""
        return {(self.root / f).relative_to(self.repo).as_posix()
                for f in (*takes_mod.HISTORY_FILES, takes_mod.LEDGER.name)}

    def _take_files(self, row: dict, attempt: int, reserved: set) -> dict:
        """{repo-relative name: (absolute path, kind)} for the take's record files, or CommitRefused. A record file
        is a new file: never one of the ledgers, never a path already tracked at HEAD (W6E-R1-2)."""
        files = {}
        for item in self.record_files(row, attempt):
            if not (isinstance(item, (tuple, list)) and len(item) == 2):
                raise CommitRefused("a record file is not (absolute path, kind)")
            path, kind = item
            if not isinstance(path, str) or not os.path.isabs(path) or os.path.normpath(path) != path:
                raise CommitRefused(f"a record file is not a normalised absolute path: {path!r}")
            if kind not in _scan_record.KINDS:
                raise CommitRefused(f"{path}: kind {kind!r} is not one of the scan's kinds")
            try:
                name = Path(path).relative_to(self.repo).as_posix()
            except ValueError:
                raise CommitRefused(f"{path} is outside the repository") from None
            if name in reserved:
                raise CommitRefused(f"{name} is one of the study's ledgers, which a take's records never are")
            if os.path.islink(path) or not os.path.isfile(path):
                raise CommitRefused(f"{name} is not a regular file")
            if name in files:
                raise CommitRefused(f"{name} is listed twice")
            if _git_bytes(self.repo, "ls-tree", "--name-only", "HEAD", "--", name).strip():
                raise CommitRefused(f"{name} is already tracked at HEAD; a take's records are new files")
            files[name] = (path, kind)
        return files

    def _staged_exactly(self, declared: dict) -> list:
        """R4-3: the staged names, which must be exactly the declared ones."""
        staged = _staged_names(self.repo)
        extra = sorted(n for n in staged if n not in declared)
        missing = sorted(n for n in declared if n not in staged)
        if extra:
            raise CommitRefused(f"staged outside the take's records: {', '.join(extra)}")
        if missing:
            raise CommitRefused(f"declared but not staged: {', '.join(missing)}")
        return [n for n in staged if n in declared]

    def _commit_step(self, row: dict, attempt: int, outcome: dict) -> dict:
        """One commit: the take's record files and its outcome, appended to the ledger. Returns the commit and the
        scan's masked count. Raises CommitRefused, takes.py's identity refusal (ValueError) or the scan's own
        scan_record.ScanError / NotReady (W6E-R1-4), each fail-closed: no commit lands, and HEAD moves only by the
        pinned update-ref below. Called only by commit_records (R4-7), which restores the ledger on any refusal."""
        if not isinstance(outcome, dict) or set(outcome) != set(takes_mod.batch.OUTCOME_KEYS):
            raise CommitRefused("the outcome does not hold exactly batch.OUTCOME_KEYS")
        if (outcome["slot"], outcome["attempt"]) != (row["slot"], attempt):
            raise CommitRefused("the outcome is not this row's slot and attempt")
        # W6E-R1-1: the outcome must be one batch can trust after the committed history, or nothing is written.
        bad = takes_mod.batch.Batch.history_problems(self.history() + [outcome])
        if bad:
            raise CommitRefused("the outcome cannot follow the committed history: " + "; ".join(bad))
        ledger = self.root / OUTCOMES_FILE
        ledger_rel = ledger.relative_to(self.repo).as_posix()
        files = self._take_files(row, attempt, self._reserved())
        takes_mod.require_commit_identity(self.repo)
        tracked = _git_bytes(self.repo, "ls-tree", "--name-only", "HEAD", "--", ledger_rel).strip()
        committed = json.loads(_git_bytes(self.repo, "show", f"HEAD:{ledger_rel}")) if tracked else []
        if not isinstance(committed, list):
            raise CommitRefused(f"{ledger_rel} at HEAD is not a list")
        ledger.write_text(json.dumps(committed + [outcome], indent=2) + "\n", encoding="utf-8")
        declared = {name: kind for name, (_, kind) in files.items()}
        declared[ledger_rel] = OUTCOME_KIND
        paths = {name: path for name, (path, _) in files.items()}
        paths[ledger_rel] = str(ledger)
        self._touched = sorted(declared)            # R4-7: what a refusal unstages
        _git_bytes(self.repo, "add", "--", *sorted(declared))
        staged = self._staged_exactly(declared)
        scan = _scan_record.scan([(paths[n], declared[n]) for n in staged], list(self.secrets()),
                                 read_shapes=scan_read_shapes(row),
                                 rules_scanner=self.rules_scanner, holdout_matcher=self.holdout_matcher)
        if not _scan_record.passed(scan):
            why = "; ".join(f"{r['path']}:{r['line']} ({r['kind']}): {r['why']}" for r in scan["refused"])
            raise CommitRefused(f"the commit scan refused the take: {why}")
        # THE INDEX (R4-2): the scan masked on disk, so stage again, then bind every staged blob to its scanned bytes.
        _git_bytes(self.repo, "add", "--", *staged)
        staged = self._staged_exactly(declared)
        # W6E-R1-3: the commit is bound to the checked tree. The index is written once as a tree; that tree's change
        # set and blobs are checked; the commit is made from that tree and HEAD moves only from the head it was
        # checked against. A file staged after write-tree never reaches the commit; a moved HEAD refuses.
        head = _git_bytes(self.repo, "rev-parse", "--verify", "HEAD").decode().strip()
        tree = _git_bytes(self.repo, "write-tree").decode().strip()
        changed = sorted(n.decode("utf-8") for n in _git_bytes(
            self.repo, "diff-tree", "-r", "--name-only", "--no-renames", "-z", head, tree).split(b"\0") if n)
        if changed != sorted(declared):
            raise CommitRefused(f"the written tree changes {changed}, not the take's declared files")
        after = {rec["path"]: rec["sha256_after"] for rec in scan["files"]}
        for name in staged:
            blob = _git_bytes(self.repo, "cat-file", "blob", f"{tree}:{name}")
            if hashlib.sha256(blob).hexdigest() != after.get(paths[name]):
                raise CommitRefused(f"the staged blob of {name} is not the bytes the scan left (sha256_after)")
        self._before_commit()
        commit = self._bind(head, tree)
        return {"commit": commit, "masked": scan["masked"], "events": scan["events"], "holdout": scan["holdout"]}

    def _before_commit(self) -> None:
        """Between the checked tree and the commit. Does nothing; the tests stage an interloper here (W6E-R1-3)."""

    def _bind(self, head: str, tree: str) -> str:
        """The commit of exactly `tree` on `head`; HEAD moves only if it still is `head` (update-ref's old value)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt") as message:
            message.write(COMMIT_SUBJECT + "\n")
            message.flush()
            new = _git_bytes(self.repo, "commit-tree", tree, "-p", head, "-F", message.name).decode().strip()
        _git_bytes(self.repo, "update-ref", "-m", COMMIT_SUBJECT, "HEAD", new, head)
        return new

    # ------------------------------------------------------------------------------- the refused commit (R4-7)
    def commit_records(self, row: dict, attempt: int, outcome: dict) -> dict:
        """batch.Batch's commit door (R4-7, ruling S6-Q2: a refused commit leaves no half state). _commit_step does
        the work. If it refuses, for any reason, the outcome ledger is put back to HEAD's bytes (removed when HEAD has
        none) and every name this call staged is unstaged; then the refusal is raised as it was. The masks the scan
        wrote on the take's own files stay (masking never deletes, and a masked file is never re-exposed). Once the
        commit has landed, on_published(row, attempt) runs; a failure there is recorded in publish_problems, never
        raised, because the commit stands and the loop must not read it as refused."""
        self._touched = []
        try:
            got = self._commit_step(row, attempt, outcome)
        except BaseException as refused:
            try:
                self._restore()
            except Exception as e:  # noqa: BLE001 - the restore's own failure is named beside the refusal
                raise CommitRefused(f"the commit was refused ({type(refused).__name__}: {refused}), and the ledger "
                                    f"could not be restored to HEAD: {type(e).__name__}: {e}") from refused
            raise
        if self.on_published is not None:
            try:
                self.on_published(row, attempt)
            except Exception as e:  # noqa: BLE001 - recorded: the commit landed and stands
                self.publish_problems.append(f"slot {row.get('slot')!r} attempt {attempt}: {type(e).__name__}: {e}")
        return got

    def _restore(self) -> None:
        """R4-7: the ledger file back to HEAD's bytes (or gone, when HEAD tracks none), and this call's staged names
        back to HEAD's index entries."""
        ledger = self.root / OUTCOMES_FILE
        rel = ledger.relative_to(self.repo).as_posix()
        if _git_bytes(self.repo, "ls-tree", "--name-only", "HEAD", "--", rel).strip():
            ledger.write_bytes(_git_bytes(self.repo, "show", f"HEAD:{rel}"))
        elif os.path.lexists(ledger):
            ledger.unlink()
        staged = set(_staged_names(self.repo))
        names = [n for n in self._touched if n in staged]
        if names:
            _git_bytes(self.repo, "reset", "-q", "--", *names)


# =====================================================================================================================
# ROUND 4, CP2: THE DRIVE LIFECYCLE, PART 2 -- LAUNCH, PREFLIGHT, THE DRIVE STEP AND ITS CLEANUP (lane w6h, slice S6
# of next-slices-2026-10-11; this file's ownership moved from lane w6e to lane w6h under glitch-1b's ruling
# S6-gap4-1). Appended after part 1, above `if __name__`, so no line other files cite by number moves.
#
#   R4-7.  A REFUSED COMMIT LEAVES NO HALF STATE (ruling S6-Q2). TakeRepo.commit_records (in part 1's class) wraps the
#          commit step: on any refusal the outcome ledger goes back to HEAD's bytes and every name the call staged is
#          unstaged, then the refusal is raised as it was. The take's own masked files stay masked.
#   R4-8.  TakeDriver IS batch.Batch's DRIVER: launch(row) -> the take container's recorded id, drive(row, id) -> the
#          take's harness-side records (agent_adapter.harness_records' shape), remove(id).
#   R4-9.  PREFLIGHT THROUGH S1. drive() begins the sidecar (its one-line reply read by sidecar.parse_completed), then
#          calls preflight_take (R4-6) with the Launched record launch returned (so Launched.spec), the sidecar's own
#          launch record and the take's evidence folder, and writes the record beside the evidence (preflight.write).
#          A failed check, a refused begin, or a typed refusal (pre_turn_refusal: a ValueError such as a lock or
#          launch record preflight cannot use or a malformed reply, a box module's NotReady, or a TimeoutError of the
#          begin exec; W6H-R1-1, R1-8b) is a PRE-TURN REFUSAL (CP2-preflight-4): it is written to refusal.json, no
#          turn runs, and preflight_ok is False (a rehearsal, by the table's first row). So is any failure of the
#          adapter's making or start before turn 1 (W6H-R1-7: the plan's row 1, a container start failure before the
#          first turn), and then the checker is not run (W6H-R1-4).
#   R4-10. SCAN -> MASK -> ROUTE -> COMMIT (ruling S6-Q3). Before drive() returns, every record file of the take is
#          scanned by box/scan_record.py, which masks agent-text hits on disk; the masked hits plus the checker's
#          per-id events, less account-email, become events.outside_reach (W6H-R1-2: the email is the scan's to count;
#          a checker email count above the scan's email masks refuses). batch.py routes those records (routing.py) and annotates them before
#          the commit, and the commit (R4-2) scans again and binds the committed bytes. A scan refusal raises: the
#          take is `failed` and the loop stops for a ruling.
#   R4-11. CLEANUP ON EVERY ROAD (the run_take task's GOTCHAs). After every turn the driver polls the agent's
#          processes (host-side) until none remain or the quiescence cap passes; at the cap (and at once after a
#          timed-out turn) it kills them by an exec as the agent's own uid and polls again until none remain, and
#          only then signals the snapshot. In drive()'s finally, on every road, the adapter is ended, the agent's
#          leftover processes are killed the same way and polled to none, and every container is removed by its
#          recorded id (run_take.teardown); what failed is written to teardown.json, with the survivors of each
#          quiescence cap by turn (W6H-R1-6). remove(id) checks every container the take recorded (take, sidecar,
#          proxy), removes again by its id each one the full listing still holds, and raises (A LEAK) naming any
#          still listed after, or a network whose removal the teardown recorded as failed (W6H-R1-3). The leak
#          carries those ids (`leaked_ids`); batch commits them as leaked_containers, and leaked_ids() reads them
#          beside leaked_container, so a restart refuses while a leaked sidecar or proxy is listed (S6-gap4-2). A launch failure carries the take container's id when the partial teardown failed to remove
#          it. The per-take config folder is deleted only once the take's records are committed (TakeRepo's
#          on_published = TakeDriver.published), never after a refused commit.
#   R4-12. The restart listing stays per register (ruling S6-Q4: correctness first; hoisted only if measured slow).
# =====================================================================================================================

import threading  # noqa: E402
import types  # noqa: E402  (live harness 3a: the executed-refused turn's end for _quiesce)
import native_snapshot as _native_snapshot  # noqa: E402  (live harness 3c)
import vendor_provenance as _vendor_provenance  # noqa: E402  (live harness integration: the native history record)
import native_reader_registration as _registration  # noqa: E402  (the production native-reader registry)

import agent_adapter as _adapter  # noqa: E402
import harness_bookkeeping as _hb  # noqa: E402
import routing as _routing  # noqa: E402
import variants as _variants  # noqa: E402
from graders import endstate as _endstate  # noqa: E402
from box import sidecar as _sidecar  # noqa: E402

# The take folder's files, each with its scan kind (box/scan_record.KINDS). A file outside this closed map refuses
# the take: nothing rides a commit unscanned under a guessed kind.
TAKE_FILE_KINDS = {"launch.json": "launch", "teardown.json": "launch", "proxy.log": "proxy-log",
                   "preflight.json": "preflight", "refusal.json": "preflight", "transcript.jsonl": "transcript",
                   "postflight.json": "preflight",    # S6b (e)
                   "operator-check.json": "launch",   # S6b C11
                   "driver-ledger.json": "ledger", "environment.json": "launch", "scrub.json": "launch",   # S6c C6-C8
                   "public-config.json": "launch",   # live harness 13 Oct: box take_config.public_record's bytes
                   "ownership-grant.json": "launch", "ownership-restore.json": "launch",   # the ownership road
                   "settings-guard.json": "launch",   # the run tree's Claude settings: baseline and per-turn checks
                   "evidence-ledger.jsonl": "evidence", "evidence-ledger-copy.json": "launch",   # review MAJOR 1
                   "session-store.json": "ledger",    # W-3b (glitch-b5, 16 Oct 2026): the session store's listings
                   "read-only-errors.json": "ledger"}    # R15-2: what the read-only root broke, by turn
STREAM_NAME = re.compile(r"turn-[1-9][0-9]*\.jsonl")
# Live harness 13 Oct: the box's per-turn actual-submission journal (run_take: stream path + ".launch.json"), an exact
# top-level sibling of a turn stream, scanned as an unmaskable launch record. Nearby or nested spellings still refuse.
LAUNCH_JOURNAL_NAME = re.compile(r"turn-[1-9][0-9]*\.jsonl\.launch\.json")
EVIDENCE_DIR, SESSION_DIR = "evidence", "session"
EVIDENCE_KINDS = {_sidecar.SNAPSHOTS: "snapshot", _sidecar.BLOBS: "blob"}
PREFLIGHT_RECORD, REFUSAL_RECORD, TEARDOWN_RECORD = "preflight.json", "refusal.json", "teardown.json"
POSTFLIGHT_RECORD, OPERATOR_CHECK_RECORD = "postflight.json", "operator-check.json"
# THE OWNERSHIP ROAD (stub-take review finding 9; the box lane's call contract, live-box-2026-10-13.md at 81ede46d,
# routed by glitch-06 on 14 Oct 2026). Under rootless Docker the run tree and config folder are granted to the agent,
# and the evidence folder to the watcher, before run_take.launch; all three are restored to the host user after
# teardown, before postflight, the scan and the config folder's removal. The road is box/ownership.py (`_ownership`
# above) unless a TakeDriver is handed another that has this exact interface (a fake, in the tests on a branch that
# lacks the box module):
#   grant(runtime, *, image, run_tree, config_dir, evidence_dir, caller_env)  -> record; raises OwnershipError
#   restore(runtime, *, image, run_tree, config_dir, evidence_dir, ids, caller_env) -> record; raises OwnershipError
#   OwnershipError   an exception class whose instances carry `record`
#   operator_write(runtime, *, image, run_tree, rel_path, data, caller_env) -> {ok, path, sha256, bytes}
#   operator_read(runtime, *, image, root_kind, run_tree, config_dir, rel_path, caller_env) -> bytes | None
#   operator_list(runtime, *, image, root_kind, run_tree, config_dir, rel_dir, caller_env) -> [(name, kind)], kind in
#                    file, dir, link,
#                    other (root_kind "run_tree" or "config"; drive-wiring review MAJOR 1: the vendor arms' native
#                    sessions are read in the agent-owned config folder through these, never host-side)
#                    (ownership review MAJOR 2, the box contract at 4c3d8e53: a mid-take operator step reads and writes
#                    the agent-owned run tree inside the box, never host-side; required at launch for a task with one)
OWNERSHIP_GRANT_PARAMS = ("runtime", "image", "run_tree", "config_dir", "evidence_dir", "caller_env")
OWNERSHIP_RESTORE_PARAMS = ("runtime", "image", "run_tree", "config_dir", "evidence_dir", "ids", "caller_env")
OWNERSHIP_OPERATOR_WRITE_PARAMS = ("runtime", "image", "run_tree", "rel_path", "data", "caller_env")
OWNERSHIP_OPERATOR_READ_PARAMS = ("runtime", "image", "root_kind", "run_tree", "config_dir", "rel_path", "caller_env")
OWNERSHIP_OPERATOR_LIST_PARAMS = ("runtime", "image", "root_kind", "run_tree", "config_dir", "rel_dir", "caller_env")
OPERATOR_ROOTS = ("run_tree", "config")      # the box's operator_read and operator_list roots (box d73c43ed)
OWNERSHIP_GRANT_RECORD, OWNERSHIP_RESTORE_RECORD = "ownership-grant.json", "ownership-restore.json"
OWNERSHIP_STEPS = ("ownership-grant", "ownership-restore")      # the driver ledger's operator steps, in order
_IMAGE_ID = re.compile(r"sha256:[0-9a-f]{64}")                    # the lock's image id; a tag never runs a step


# THE SETTINGS GUARD (ownership review finding 1; the box contract at d3fd5305): the run tree's Claude settings files are
# baselined host-side before the grant, and every turn k is sent only when the sidecar's own pre-k snapshot shows them
# unchanged, and every turn's post-k snapshot (the last turn's too) must show them unchanged as well (box 22b15f56,
# review round 2: Claude Code reloads a changed settings file, so a change is caught at that turn's post-k). The guard
# is box/settings_guard.py (`_settings_guard`) unless a TakeDriver is handed another with this interface:
# baseline(run_tree, *, model) -> {path: sha256}, raising SettingsRefused; snapshot_problems(snapshot, base) -> [problem].
SETTINGS_RECORD = "settings-guard.json"
# Drive-wiring review MAJOR 1: the driver's evidence-ledger lines during the take, and the record of their copy.
EVIDENCE_LEDGER_HOST, EVIDENCE_LEDGER_COPY = "evidence-ledger.jsonl", "evidence-ledger-copy.json"
SETTINGS_GUARD_PARAMS = {"baseline": ("run_tree", "model"), "snapshot_problems": ("snapshot", "base")}


def settings_guard_problems(guard) -> list:
    """Why `guard` is not a settings guard this driver can call (empty when it is); None is a problem, never a skip."""
    import inspect
    if guard is None:
        return ["no settings guard: box/settings_guard.py is not on this tree (the box lane's d3fd5305), so no take "
                "launches"]
    p = []
    err = getattr(guard, "SettingsRefused", None)
    if not (isinstance(err, type) and issubclass(err, Exception)):
        p.append("the settings guard's SettingsRefused is not an exception class")
    for name, params in SETTINGS_GUARD_PARAMS.items():
        fn = getattr(guard, name, None)
        if not callable(fn) or [q.name for q in inspect.signature(fn).parameters.values()] != list(params):
            p.append(f"the settings guard has no {name}({', '.join(params)})")
    return p


def ownership_problems(road, *, operator_write: bool = False, native: bool = False) -> list:
    """Why `road` is not an ownership road this driver can call (empty when it is): the interface above, by name,
    kind and order of each parameter. None (box/ownership.py absent from this tree) is a problem, never a skip.
    operator_write: the take has a mid-take operator step, so the road must also offer operator_write and
    operator_read. native: a vendor take, whose native session is read through operator_list and operator_read."""
    import inspect
    if road is None:
        return ["no ownership road: box/ownership.py is not on this tree (the box lane's 81ede46d), so no take "
                "launches"]
    p = []
    err = getattr(road, "OwnershipError", None)
    if not (isinstance(err, type) and issubclass(err, Exception)):
        p.append("the ownership road's OwnershipError is not an exception class")
    steps = [("grant", OWNERSHIP_GRANT_PARAMS), ("restore", OWNERSHIP_RESTORE_PARAMS)]
    if operator_write:
        steps += [("operator_write", OWNERSHIP_OPERATOR_WRITE_PARAMS)]
    if operator_write or native:
        steps += [("operator_read", OWNERSHIP_OPERATOR_READ_PARAMS)]
    if native:
        steps += [("operator_list", OWNERSHIP_OPERATOR_LIST_PARAMS)]
    for name, params in steps:
        fn = getattr(road, name, None)
        if not callable(fn):
            p.append(f"the ownership road has no callable {name}")
            continue
        got = list(inspect.signature(fn).parameters.values())
        kinds = [inspect.Parameter.POSITIONAL_OR_KEYWORD] + [inspect.Parameter.KEYWORD_ONLY] * (len(params) - 1)
        if [q.name for q in got] != list(params) or [q.kind for q in got] != kinds:
            p.append(f"the ownership road's {name} is not {name}({params[0]}, *, {', '.join(params[1:])})")
    return p
# What the checker callable returns: a closed record (the drive step's operator-side reading of the take).
# S6b (C11, C12): the operator-diff count and the finalize abort are the driver's own readings now, so the checker
# hands only its reasons and its per-id events.
CHECKER_KEYS = ("checker_reasons", "checker_events")
# The checker event the scan counts itself (W6H-R1-2): the account email is a secret the scan masks, so the checker's
# count of it is only cross-checked, never added (one email is one event, not two).
ACCOUNT_EMAIL_EVENT, EMAIL_SECRET = "account-email", "email"


def pre_turn_refusal(e: BaseException) -> bool:
    """R4-9 (W6H-R1-1, R1-8b): a typed refusal before the agent's first turn. A ValueError (the lock's LockError, the
    launch record's Refused, the sidecar's ReplyError, malformed JSON), a NotReady of a box module (run_take's,
    sidecar's, the lock reader's: each box module defines its own NotReady(RuntimeError); drive.py never names the lock
    module, so the class is told by its name and its box module), or a TimeoutError of the begin exec. Anything else
    (a TypeError, a NotImplementedError, a RecursionError) is a defect and is raised, never routed as a rehearsal.
    Live harness 3a: an executed turn's refusal (agent_adapter.ExecutedTurnRefused, even one that is also a ValueError)
    is never a pre-turn refusal: the turn ran."""
    if isinstance(e, _adapter.ExecutedTurnRefused):
        return False
    if isinstance(e, (ValueError, TimeoutError)):
        return True
    return (isinstance(e, RuntimeError) and type(e).__name__ == "NotReady"
            and type(e).__module__.startswith("box."))


class DriveRefused(RuntimeError):
    """The drive step cannot hand the take to routing: the loop records it `failed` and stops for a human."""


class LaunchNeedsRuling(DriveRefused):
    """Review NOTE 6 (glitch-06's ruling, 14 Oct 2026): a refusal before launch that a restart would only meet again
    (a refused settings baseline, a failed grant): nothing launched, and batch records it BLOCKED for a ruling, never
    re-driven on its own. Departure, named: the box contract said "a rehearsal" for both."""
    needs_ruling = True


class OperatorStepRefused(DriveRefused):
    """A mid-take operator step's read or write through the ownership road failed (ownership review MAJOR 2): the
    take stopped after its drive started, for a human ruling, never a re-run."""


class NativeCrossCheckPending(DriveRefused):
    """Live harness integration: a vendor take whose native cross-check cannot run yet (no reviewed native reader).
    D8 grades a vendor's host-captured stream "cross-checked with" its native record, so the take is not gradable:
    stopped after cleanup, ledger and scan for a human ruling, never graded, never readers-disagree, never a re-run."""


def stream_path(take, n: int) -> str:
    """Where turn n's host-captured stream is written: in the take folder, outside the run tree."""
    return os.path.join(take.folder, f"turn-{n}.jsonl")


def sidecar_health(evidence_dir: str) -> dict:
    """routing.py's `sidecar` record from the sidecar's own health.jsonl, read after its finish: a watcher-start was
    written; the last record is a watcher-stop; the exit code is the first non-zero stop's (a mid-take death), else
    the last stop's; any queue-overflow. A missing or unreadable file reads as no start and no stop, never as
    healthy."""
    path = os.path.join(evidence_dir, _sidecar.HEALTH)
    try:
        with open(path, encoding="utf-8") as fh:
            recs = [json.loads(line) for line in fh if line.strip()]
    except (OSError, ValueError):
        return {"start_record": False, "stop_record": False, "exit_code": -1, "queue_overflow": False}
    kinds = [r.get("kind") if isinstance(r, dict) else None for r in recs]
    stops = [r.get("exit_code") for r in recs if isinstance(r, dict) and r.get("kind") == _sidecar.WATCHER_STOP]
    codes = [c if isinstance(c, int) and not isinstance(c, bool) else -1 for c in stops]
    bad = [c for c in codes if c != 0]
    return {"start_record": _sidecar.WATCHER_START in kinds,
            "stop_record": bool(kinds) and kinds[-1] == _sidecar.WATCHER_STOP,
            "exit_code": bad[0] if bad else (codes[-1] if codes else -1),
            "queue_overflow": _sidecar.QUEUE_OVERFLOW in kinds}


class _Take:
    """One launched (or attempted) take: what the driver recorded about it, keyed by the take container's id."""

    def __init__(self, row: dict, folder: str, config_dir: str):
        self.row, self.folder, self.config_dir = row, folder, config_dir
        self.evidence_dir = os.path.join(folder, EVIDENCE_DIR)
        self.launched = None
        self.sidecar = None
        self.cleanup: list = []        # what the finally path could not do, by step
        self.survivors: list = []      # W6H-R1-6: {turn, pids} for each quiescence cap that found agent processes
        self.teardown = None           # run_take.teardown's record (W6H-R1-3: remove() reads its network step)
        self.driven = False
        self.adapter_open = False      # S6b (d): set when start_take returned, cleared when end_take was called
        self.ledger_rows: list = []    # S6c C13: one row per line sent (round 3's ledger turns[]), recovery rows too
        self.outcome = None            # S6c C13: round 3's ledger outcome (check_take's driver_outcome_shapes)
        self.identity = None           # S6c C7: identity_for(row), checked closed
        self.environment = None        # S6c C8: environment.json as written before the first turn
        self.cross_check = None        # S6c C6: the streams against the session file (problems; [] when they agree)
        self.executed_refusal = None   # live harness 3a: the executed turn whose own record the harness refused
        self.adapter_ref = None        # live harness 3c: the adapter the executed-refusal road retains through
        self.cross_check_status = None  # live harness integration: a vendor take's native cross-check status
        self.native_hook = False       # live harness 3c: the adapter names a native session to retain per turn
        self.native_snapshots: list = []        # 3c: {file, sha256} per retained turn, under session/
        self.native_snapshot_refusal = None     # 3c: why a turn's snapshot was not retained (the take stops)
        self.session_store: list = []  # W-3b: the config folder's session store, listed after every turn and at publish
        self.session_sweeps: list = []  # W-3b (review r14): the take container swept for session files after every turn
        self.read_only_errors: list = []  # R15-2: EROFS lines of the turns' streams and stderr (read-only-errors.json)
        self.native_rel = None         # W-3b: the vendor take's own native session, relative to the config folder
        self.store_refusal = None      # W-3b: a vendor take whose session store holds more than its own session
        self.spec = None               # the ownership road: the TakeSpec the grant and the restore name
        self.grant = None              # {ok, why, record}: the grant's record (ownership-grant.json)
        self.restore = None            # {ok, why, ids, record}: the restore's record (ownership-restore.json)
        self.ownership_hold = None     # why the take's folders are kept for a human: no postflight, scan or commit
        self.settings = None           # {baseline, refused, checks}: the settings guard's record (settings-guard.json)
        self.settings_stop = None      # the problems that stopped the take before turn k > 1 (a ruling)
        self.config_stop = None        # B11: the config folder's problems that stopped an O or G take before turn k > 1


class TakeDriver:
    """batch.Batch's driver (R4-8): launch, drive, remove, plus the repo's record_files and on_published hooks.

    Every collaborator is injected and none is defaulted (a value only the box or a walk can tell stays the caller's):

    runtime          run_take's runtime protocol (run(argv, env=, timeout=)); a fake in tests, DockerRuntime on the box
    take_folder      (row) -> a new absolute folder inside the repository, the take's records' home (it must not exist)
    config_parent    the folder per-take config folders are made in (outside every repository)
    spec_for         (row, config_dir) -> run_take.TakeSpec (its network a placeholder: launch replaces it)
    sidecar_for      (row, evidence_dir) -> run_take.SidecarLaunch
    proxy            run_take.ProxyLaunch
    lock_path        the take lock's absolute path (S1's load_take_lock reads it inside preflight)
    hosts            preflight's hosts mapping
    adapter_for      (row, take) -> agent_adapter.AgentAdapter for the take; it writes turn n's stream at
                     stream_path(take, n)
    script_for       (row) -> the operator lines of the take's own wording, in order
    pin_for          (row) -> the routing pin: the registered row's pre-registered profile (batch.expected_pin)
    checker          (row, take, turns) -> {CHECKER_KEYS}: the operator-side reading (check_take.check4's reasons and
                     its per-id events dict as checker_events); not called when preflight failed or no turn ran
                     (W6H-R1-4). The operator-diff count and the finalize abort are the driver's own (S6b C11, C12)
    project_for      (row) -> the take's project name (the neutral name of its session), for the operator steps
    identity_for     (row) -> the take's identity as the row's registration and the run-tree builder know it, exactly
                     IDENTITY_KEYS: session_id (takes.session_id_for of the row's commit), row, row_commit, source
                     (the absolute source handed in), fixture (the fixture builder's record), gars_tree_sha (S6c C7)
    strict_script    W6J-R1-3: True refuses a script_for entry that is a bare line (the production wiring,
                     script_from_design, hands steps with their markers); False keeps S6's synthetic line scripts
    secrets          () -> [(kind, value)] for the scan, read at scan time and never held
    rules_scanner, holdout_matcher   box/scan_record.py's
    uid_map          the runtime's uid map lines (container start, host start, length), or (take) -> those lines,
                     read at run time from the take container (walk_builders.run_time_readers)
    budget_s, finalize_wait_s, poll_s   the turn budget, the quiescence cap and the poll interval (pre-registered)
    clock, sleep     the injected host clock and sleep (no real wait in a test)
    ownership        the ownership road (OWNERSHIP_GRANT_PARAMS, OWNERSHIP_RESTORE_PARAMS): box/ownership.py when
                     None; launch refuses while ownership_problems names anything
    settings_guard   the run tree's settings guard (SETTINGS_GUARD_PARAMS): box/settings_guard.py when None; launch
                     refuses while settings_guard_problems names anything
    machine_gate     P-2 (glitch-06, 14 Oct 2026): () -> [problem], machine_gate.gate's check (an athena suite in
                     progress, a booked machine); launch refuses while it names anything, and when it is None
    """

    def __init__(self, *, runtime, take_folder, config_parent, spec_for, sidecar_for, proxy, lock_path, hosts,
                 adapter_for, script_for, pin_for, checker, secrets, rules_scanner, uid_map, budget_s,
                 finalize_wait_s, poll_s, clock, sleep, project_for, identity_for, holdout_matcher=None,
                 caller_env=None, strict_script=False, ownership=None, settings_guard=None, machine_gate=None):
        if not callable(getattr(runtime, "run", None)):
            raise TypeError("runtime must offer run(argv, env=, timeout=)")
        for name, fn in (("take_folder", take_folder), ("spec_for", spec_for), ("sidecar_for", sidecar_for),
                         ("adapter_for", adapter_for), ("script_for", script_for), ("pin_for", pin_for),
                         ("checker", checker), ("secrets", secrets), ("rules_scanner", rules_scanner),
                         ("clock", clock), ("sleep", sleep), ("project_for", project_for),
                         ("identity_for", identity_for)):
            if not callable(fn):
                raise TypeError(f"{name} must be callable")
        self.runtime, self.take_folder, self.config_parent = runtime, take_folder, config_parent
        self.spec_for, self.sidecar_for, self.proxy = spec_for, sidecar_for, proxy
        self.lock_path, self.hosts = lock_path, hosts
        self.adapter_for, self.script_for, self.pin_for, self.checker = adapter_for, script_for, pin_for, checker
        self.secrets, self.rules_scanner, self.holdout_matcher = secrets, rules_scanner, holdout_matcher
        self.uid_map, self.budget_s, self.finalize_wait_s, self.poll_s = uid_map, budget_s, finalize_wait_s, poll_s
        self.clock, self.sleep, self.caller_env = clock, sleep, caller_env
        self.project_for = project_for
        self.identity_for = identity_for                  # S6c C7
        self.strict_script = strict_script is True        # W6J-R1-3: True in the CP6 production wiring
        self.ownership = _ownership if ownership is None else ownership   # the box module unless one is handed in
        self.settings_guard = _settings_guard if settings_guard is None else settings_guard   # the same
        self.machine_gate = machine_gate                  # P-2: () -> [problem]; None refuses every launch
        self._lock = threading.Lock()
        self._by_id: dict = {}        # take container id -> _Take
        self._by_slot: dict = {}      # slot -> the slot's latest _Take not yet published
        self.published_takes: list = []
        self.publish_problems: list = []   # S6b Q6: a published take whose config folder could not be deleted

    # ------------------------------------------------------------------------------------------- launch (R4-8)
    def launch(self, row: dict, *, _folder=None) -> str:
        """The take's config folder, record folder and containers (run_take.launch); returns the take container's id.
        _folder (W9, ruling w9-Q1) is the record folder WalkDriver.launch has already checked; None reads take_folder.
        A launch failure re-raises run_take's LaunchError with `container_id` set to the take container's id when its
        partial teardown did not remove it (batch records it and removes it again), else None."""
        if self.publish_problems:                             # S6b Q6 (D5): a config folder never reused silently
            raise DriveRefused(f"a published take's cleanup failed: {self.publish_problems[0]}")
        road = ownership_problems(self.ownership,               # before any folder or container
                                  operator_write=any(task == row.get("task") for task, _ in OPERATOR_STEPS),
                                  native=(row.get("agent") or {}).get("harness") in VENDOR_HARNESSES)
        road += settings_guard_problems(self.settings_guard)
        if road:
            raise DriveRefused("; ".join(road))
        busy = (["no machine gate (P-2): a take never starts unchecked"] if not callable(self.machine_gate)
                else list(self.machine_gate()))
        if busy:                                              # P-2: before any folder or container
            raise DriveRefused("P-2, the take does not start: " + "; ".join(busy))
        folder = self.take_folder(row) if _folder is None else _folder
        if not isinstance(folder, str) or not os.path.isabs(folder) or os.path.normpath(folder) != folder:
            raise DriveRefused(f"the take folder is not a normalised absolute path: {folder!r}")
        os.makedirs(folder)                                     # a new folder: an existing one raises
        cfg = _run_take.make_config_dir(self.config_parent)
        take = _Take(row, folder, cfg)
        with self._lock:
            self._by_slot[row["slot"]] = take
        os.mkdir(take.evidence_dir)
        os.chmod(take.evidence_dir, 0o755)   # never the umask's (box lane, 15 Oct 2026: umask 077 hid it from the host)
        # A named property of the launch road (review of 89525f03..3943d61c): on athena this 0755 folder sits inside
        # the launch road's 0700 per-walk child, so no other account can reach it.
        take.sidecar = self.sidecar_for(row, take.evidence_dir)
        spec = self.spec_for(row, cfg)       # every host-side write into the run tree and config folder is done here
        take.spec = spec
        self._settings_baseline(take)        # the settings guard: host-side, before the grant (no watcher yet)
        self._grant_ownership(take)          # the ownership road: after them and the evidence folder, pre-launch
        try:
            take.launched = _run_take.launch(self.runtime, spec, sidecar=take.sidecar, proxy=self.proxy,
                                             record_dir=folder, caller_env=self.caller_env)
        except _run_take.LaunchError as e:
            take.launched = e.launched
            removed = any(s.get("step") == "take-rm" and s.get("returncode") == 0 for s in e.launched.torn_down)
            e.container_id = e.launched.take_id if e.launched.take_id and not removed else None
            if e.container_id:
                with self._lock:
                    self._by_id[e.container_id] = take
            self._restore_ownership(take)    # after the launch's partial teardown; a failure holds the take
            raise
        except Exception:                    # review MINOR 4: refused before any container, after the grant
            if take.launched is None:
                self._restore_ownership(take, ids=[])
            raise
        with self._lock:
            self._by_id[take.launched.take_id] = take
        return take.launched.take_id

    # ------------------------------------------------------------------------------------------- the settings guard
    def _settings_baseline(self, take) -> None:
        """The run tree's Claude settings files, baselined before the grant. A refusal (a forbidden key, an odd
        shape) means no launch: recorded in settings-guard.json and raised as DriveRefused (nothing ran)."""
        try:
            base = self.settings_guard.baseline(take.spec.run_tree, model=take.row["model"])   # the pinned model
        except Exception as e:  # noqa: BLE001 - SettingsRefused or any other failure: no launch
            take.settings = {"baseline": None, "refused": f"{type(e).__name__}: {str(e)[:500]}", "checks": []}
            self._write(take, SETTINGS_RECORD, take.settings)
            raise LaunchNeedsRuling(f"the run tree's Claude settings refused before launch: {e}") from e
        take.settings = {"baseline": base, "refused": None, "checks": []}   # written once, by the cleanup

    def _settings_problems(self, take, label: str) -> list:
        """The guard over the sidecar's own snapshot `label` (pre-n before turn n, post-n after it), read from the
        evidence folder, never the run tree. A snapshot that is missing or does not read is a problem, never a pass.
        Recorded either way."""
        path = os.path.join(take.evidence_dir, _sidecar.SNAPSHOTS, f"{label}.json")
        try:
            with open(path, encoding="utf-8") as fh:
                doc = json.load(fh)
            problems = list(self.settings_guard.snapshot_problems(doc, take.settings["baseline"]))
        except Exception as e:  # noqa: BLE001 - an unreadable snapshot or a failing guard is a problem
            problems = [f"{label}: the settings check could not run ({type(e).__name__}: {str(e)[:200]})"]
        take.settings["checks"].append({"snapshot": label, "problems": problems})
        return problems

    # ------------------------------------------------------------------------------------------- the ownership road
    def _grant_ownership(self, take) -> None:
        """Grant the run tree and config folder to the agent and the evidence folder to the watcher, by the take
        image's id. On OwnershipError the take never launches: a restore with no ids undoes any partial grant, the
        grant record is written, and DriveRefused is raised (nothing ran)."""
        spec, road = take.spec, self.ownership
        image = getattr(spec, "image", None)
        if not isinstance(image, str) or not _IMAGE_ID.fullmatch(image):
            raise DriveRefused(f"the ownership road runs the take image by its lock's id, never {image!r}")
        try:
            record = road.grant(self.runtime, image=spec.image, run_tree=spec.run_tree, config_dir=take.config_dir,
                                evidence_dir=take.evidence_dir, caller_env=self.caller_env)
        except Exception as e:  # noqa: BLE001 - OwnershipError, or a refusal before any step: undone and refused
            take.grant = {"ok": False, "why": f"{type(e).__name__}: {str(e)[:500]}",
                          "record": getattr(e, "record", None)}
            self._restore_ownership(take, ids=[])
            self._write(take, OWNERSHIP_GRANT_RECORD, take.grant)
            raise LaunchNeedsRuling(f"ownership grant failed, the take is not launched: {e}") from e
        take.grant = {"ok": True, "why": None, "record": record}
        self._write(take, OWNERSHIP_GRANT_RECORD, take.grant)

    def _restore_ownership(self, take, ids=None) -> None:
        """Restore the three folders to the host user (ids: every container the take recorded). Never raises: any
        failure sets take.ownership_hold, so no postflight, scan, commit or removal follows, and the take's folders
        are kept for a human ruling. The restore record is written either way."""
        spec, road = take.spec, self.ownership
        try:
            ids = list(take.launched.ids()) if ids is None else list(ids)
            record = road.restore(self.runtime, image=spec.image, run_tree=spec.run_tree, config_dir=take.config_dir,
                                  evidence_dir=take.evidence_dir, ids=ids, caller_env=self.caller_env)
            take.restore = {"ok": True, "why": None, "ids": ids, "record": record}
        except Exception as e:  # noqa: BLE001 - OwnershipError or anything else: the folders are held, fail closed
            take.restore = {"ok": False, "why": f"{type(e).__name__}: {str(e)[:500]}",
                            "ids": ids if isinstance(ids, list) else None, "record": getattr(e, "record", None)}
            take.ownership_hold = f"ownership restore failed ({type(e).__name__}: {str(e)[:300]})"
        try:
            self._write(take, OWNERSHIP_RESTORE_RECORD, take.restore)
        except Exception as e:  # noqa: BLE001
            take.ownership_hold = take.ownership_hold or f"the restore record could not be written ({e})"

    @staticmethod
    def _unrestored(take) -> str | None:
        """Why the take's records must not be read, scanned or committed: a held restore, or a grant never
        restored."""
        if take.ownership_hold:
            return take.ownership_hold
        if take.grant is not None and take.restore is None:
            return "the take's folders were granted and never restored"
        return None

    # ------------------------------------------------------------------------------------------- drive (R4-9..11)
    def _env(self) -> dict:
        return _run_take.runtime_env(self.caller_env)

    def _ctl(self, take, command: str, label=None) -> dict:
        argv = list(take.sidecar.ctl_argv_for(take.launched.sidecar_id, command, label))
        return _sidecar.parse_completed(self.runtime.run(argv, env=self._env(), timeout=_run_take.STEP_TIMEOUT_S))

    def _gone(self, take) -> list:
        uid_map = self.uid_map(take) if callable(self.uid_map) else self.uid_map   # read at run time, or given
        return _run_take.wait_gone(self.runtime, take.launched.take_id, agent_uid=_run_take._uid_of(
            _run_take.AGENT_USER), uid_map=uid_map, cap_s=self.finalize_wait_s, interval_s=self.poll_s,
            clock=self.clock, sleep=self.sleep, caller_env=self.caller_env)

    def _kill(self, take) -> int:
        """KILL to every process of the agent's uid, by an exec as that uid. Its exit status is returned, never
        trusted: `kill -1` with nothing left to signal exits non-zero, so the poll that follows is the proof."""
        return _run_take.kill_agent(self.runtime, take.launched.take_id, agent_user=_run_take.AGENT_USER,
                                    caller_env=self.caller_env).returncode

    def _quiesce(self, take, turn) -> tuple:
        """After a turn: (survivors at the cap, killed). A timed-out turn's processes are killed at once; otherwise
        the driver waits up to the cap and kills what is left. Either way it polls again until none remain."""
        survivors, killed = [], False
        if turn.end_reason == _adapter.END_TIMED_OUT:
            self._kill(take)
            killed = True
        else:
            survivors = self._gone(take)
            if survivors:
                self._kill(take)
                killed = True
        if killed and self._gone(take):
            raise DriveRefused("the agent's processes outlived the kill as its own uid")
        return survivors, killed

    def _write(self, take, name: str, doc: dict) -> None:
        _run_take._write_json(os.path.join(take.folder, name), doc)

    def _preflight(self, take, harness: str) -> bool:
        """R4-9: True when every preflight check passed; a refusal is recorded and read as False."""
        try:
            begin = self._ctl(take, "begin")
            record = preflight_take(self.runtime, launched=take.launched, sidecar=take.sidecar,
                                    lock_path=self.lock_path, harness=harness, hosts=self.hosts,
                                    evidence_dir=take.evidence_dir, begin_reply=begin, caller_env=self.caller_env)
            _preflight.write(record, os.path.join(take.folder, PREFLIGHT_RECORD))
        except Exception as e:  # noqa: BLE001 - only the typed refusals are routed; the rest is raised
            if not pre_turn_refusal(e):
                raise
            self._refused(take, e)
            return False
        return record["ok"] is True

    # ------------------------------------------------------------------------------------------- S6b C9-C11
    def _evidence_line(self, take, rec: dict) -> None:
        """C10: one record of the driver's evidence ledger (endstate's ledger.jsonl), appended in order. Drive-wiring
        review MAJOR 1 (glitch-06's ruling, 14 Oct 2026): during the take the evidence folder is the watcher's, so the
        lines go to a host-owned file in the take folder (outside every granted folder, never mounted into a
        container), copied byte-exact into the evidence folder after the restore (_copy_evidence_ledger)."""
        with open(os.path.join(take.folder, EVIDENCE_LEDGER_HOST), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, sort_keys=True) + "\n")

    def _copy_evidence_ledger(self, take) -> None:
        """After a restore that succeeded: the host ledger copied byte-exact into <evidence>/ledger.jsonl (a new file,
        links never followed), both sha256 recorded in evidence-ledger-copy.json, then the host copy removed. Any
        failure holds the take (no postflight, scan or commit) and keeps the host copy with the folders."""
        host = os.path.join(take.folder, EVIDENCE_LEDGER_HOST)
        if not os.path.lexists(host):
            return                                            # nothing of the drive was logged (a launch road)
        try:
            with open(host, "rb") as fh:
                data = fh.read()
            fd = os.open(os.path.join(take.evidence_dir, _endstate.LEDGER),
                         os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
            with os.fdopen(fd, "wb") as fh:
                fh.write(data)
            with open(os.path.join(take.evidence_dir, _endstate.LEDGER), "rb") as fh:
                back = fh.read()
            record = {"host_sha256": hashlib.sha256(data).hexdigest(),
                      "evidence_sha256": hashlib.sha256(back).hexdigest(), "bytes": len(data)}
            self._write(take, EVIDENCE_LEDGER_COPY, record)
            if record["host_sha256"] != record["evidence_sha256"]:
                raise OSError("the evidence copy's bytes are not the host ledger's")
            os.remove(host)
        except Exception as e:  # noqa: BLE001 - the take is held, its host ledger kept with the folders
            why = f"the evidence ledger could not be copied ({type(e).__name__}: {e})"
            take.ownership_hold = take.ownership_hold or why

    def _operator_step(self, take, row, step) -> bool:
        """C9 (ruling D8): the closed table's operator step after turn n, logged as one operator event (its writes
        with the state each leaves). Ownership review MAJOR 2 (the box contract's operator addition): the run tree is
        the agent's after the grant, so every read and write of it here is the box's (operator_read, operator_write,
        inside the box, links never followed), never a host-side open; the event's sha256 is the write's reply.
        False when the step's wait ran out (C12: round 3's finalize abort); the event is then not logged, because
        nothing was written. A failed read or write stops the take (OperatorStepRefused)."""
        op_id, action = step
        tree = take.launched.spec.run_tree
        project = self.project_for(row)
        proj = os.path.join(tree, "gars", "projects", project)
        target = os.path.join(proj, "00_data", "rnaseq_bulk", "samples.csv")
        if action == OPERATOR_SAVE:
            from fixtures import gen_explain_not_act as _gen          # the generator's own save (SAVE_PATH)
            written, data = str(_gen.samples_csv(Path(proj))), _gen.CORRECTED.encode()   # operator_save's bytes
        elif action == OPERATOR_FINALIZE:
            deadline = self.clock() + self.finalize_wait_s
            while True:                                     # each poll is one box read; the injected poll_s paces it
                got = self._operator_read(take, op_id, self._rel(target, tree))
                if got is not None and b"sample_id" in got:
                    break
                if self.clock() >= deadline:
                    return False
                self.sleep(self.poll_s)
            table = self._operator_read(take, op_id, DESIGN_TABLE.format(project=project))
            if table is None:                               # W6I-R1-4: a stop, never a bare FileNotFoundError
                raise DriveRefused(f"operator step {op_id!r}: the fixture's design table {DESIGN_TABLE} is missing")
            want = (((_variants.load_task(row["task"])["halves"][row["half"]].get("fixture") or {})
                     .get("design_table") or {}).get("md5"))
            got = hashlib.md5(table).hexdigest()            # S6c (W6I-R2-2): read once; these bytes are written
            if not want or got != want:                     # the table copied in is the fixture's pinned one
                raise DriveRefused(f"operator step {op_id!r}: the design table's md5 {got} is not the fixture's "
                                   f"pinned {want!r}")
            written, data = target, table                   # the hashed bytes, never a second read of the file
        else:
            raise DriveRefused(f"operator step {op_id!r} has no action this driver knows ({action!r})")
        rel = self._rel(written, tree)
        if self._excluded(rel, row["agent"]["harness"]):          # CP2-requirements open question 4
            raise DriveRefused(f"operator step {op_id!r} writes {rel}, an excluded path; it is never logged")
        try:
            reply = self.ownership.operator_write(self.runtime, image=take.spec.image, run_tree=tree, rel_path=rel,
                                                  data=data, caller_env=self.caller_env)
        except Exception as e:  # noqa: BLE001 - OwnershipError, Refused or anything else: the take's stop
            raise OperatorStepRefused(f"operator step {op_id!r}: the box's write of {rel} failed "
                                      f"({type(e).__name__}: {str(e)[:300]}); the take is kept for a human ruling, "
                                      f"never a re-run") from e
        ok = isinstance(reply, dict) and reply.get("ok") is True
        sha = reply.get("sha256") if isinstance(reply, dict) else None
        if not ok or sha != hashlib.sha256(data).hexdigest():
            raise OperatorStepRefused(f"operator step {op_id!r}: the box's write of {rel} replied {reply!r}, not ok "
                                      f"with the data's sha256; the take is kept for a human ruling")
        self._evidence_line(take, {"kind": "operator", "id": op_id, "at": self.clock(),
                                   "writes": [{"path": rel, "after": {"type": "file", "sha256": sha}}]})
        return True

    @staticmethod
    def _rel(path: str, tree: str) -> str:
        return os.path.relpath(path, tree).replace(os.sep, "/")

    def _operator_read(self, take, op_id, rel: str):
        """The box's read of one run-tree file (bytes, or None when it does not exist); any failure stops the take."""
        try:
            got = self.ownership.operator_read(self.runtime, image=take.spec.image, root_kind="run_tree",
                                               run_tree=take.launched.spec.run_tree, config_dir=take.config_dir,
                                               rel_path=rel,
                                               caller_env=self.caller_env)
        except Exception as e:  # noqa: BLE001 - OwnershipError, Refused or anything else: the take's stop
            raise OperatorStepRefused(f"operator step {op_id!r}: the box's read of {rel} failed "
                                      f"({type(e).__name__}: {str(e)[:300]}); the take is kept for a human ruling, "
                                      f"never a re-run") from e
        if got is not None and not isinstance(got, bytes):
            raise OperatorStepRefused(f"operator step {op_id!r}: the box's read of {rel} gave {type(got).__name__}")
        return got

    @staticmethod
    def _excluded(rel: str, harness: str) -> bool:
        """A run-tree path endstate never diffs (git's and helpers' bookkeeping, the harness's own)."""
        return any(_hb.matches(p, rel) for p in _endstate.COMMON_EXCLUSIONS
                   + _endstate.harness_run_tree_exclusions(harness))

    def _operator_check(self, take, row) -> int:
        """C11: endstate's operator_check over the take's evidence, after the sidecar's finish (in the teardown),
        written as operator-check.json. An evidence folder that does not load is never read as no diff: it counts
        one, so the take routes by the operator-diff rows (never graded), and the reason is in that record."""
        try:
            got = _endstate.Evidence.load(take.evidence_dir).operator_check()
        except _endstate.EvidenceError as e:
            got = {"unexplained_diffs": 1, "problems": [f"the evidence does not load: {e}"]}
        self._write(take, OPERATOR_CHECK_RECORD, got)
        return got["unexplained_diffs"]

    def _postflight(self, take, row) -> dict | None:
        """S6b (e): preflight.postflight on the per-take config folder (still there: it goes only after the commit),
        written as postflight.json; a failure to run it is recorded in take.cleanup and returns None (a stop)."""
        try:
            post = _preflight.postflight(take.config_dir, row["agent"]["harness"], session_id=(take.identity or {}).get("session_id"), run_tree=take.spec.run_tree if take.spec else None)  # noqa: E501  lane fold6/kill-leftovers
            self._write(take, POSTFLIGHT_RECORD, post)
            return post
        except Exception as e:  # noqa: BLE001 - never replaces the drive's own exception; read as a stop after
            take.cleanup.append(f"postflight: {type(e).__name__}: {e}")
            return None

    def _identity(self, row) -> dict:
        """S6c C7: identity_for(row), exactly IDENTITY_KEYS, its session id a string; anything else refuses."""
        ident = self.identity_for(row)
        if not isinstance(ident, dict) or set(ident) != set(IDENTITY_KEYS):
            raise DriveRefused(f"identity_for must give exactly {list(IDENTITY_KEYS)}")
        if not isinstance(ident["session_id"], str) or not ident["session_id"]:
            raise DriveRefused("the take's identity names no session id")
        return dict(ident)

    def _environment(self, take, row, adapter) -> list:
        """S6c C8 (ruling D4): environment.json in round 3's schema, before the first turn: the names the take's exec
        gives the agent (run_take.exec_values and the harness's login variable, never a value; the image's own
        environment is preflight's record), the stripped names against this process's environment, and an empty
        per-turn credential source. Written again with every turn's source once the take is done."""
        harness = row["agent"]["harness"]
        child = dict(_run_take.exec_values(harness, take.launched.spec.run_tree))
        if harness == _run_take.CODEX:
            # The Codex lease road (glitch-06, 14 Oct 2026): a Codex row has no environment login (run_take.NO_LOGIN);
            # its login is the lease file run_take.place_lease put in the config folder, never a child variable.
            pass
        else:
            child[_run_take.LOGIN_VARIABLE[harness]] = "set"      # read and checked by run_take at exec time
        ident = take.identity
        take.environment = environment_record(child, os.environ, session_id=ident["session_id"], row=ident["row"],
                                              row_commit=ident["row_commit"], task=row["task"], half=row["half"],
                                              model=row["model"], claude_version=adapter.version())
        write_record_atomically(Path(take.folder) / ENVIRONMENT_RECORD_FILE, take.environment)   # rewritten at the end
        return money_line_names(take.environment)   # round 3's money line: the caller stops the take on any

    def _executed_refused(self, take, n: int, line: str, e) -> list:
        """Live harness 3a: turn n's exec ran and the adapter then refused its own record of it. The turn is accounted
        for as launched: its evidence line from the kept times, quiescence (killed at once when it timed out), its
        post-n snapshot and its ledger row (end unknown: None; the refusal named). Nothing further is sent. Returns
        the snapshot's unreadable-consequential list. The drive then cleans up, writes its ledger, scans, and refuses
        the take for a human (DriveRefused after the scan): never a pre-turn refusal, a rehearsal or a re-run."""
        x = e.executed
        stream = os.path.basename(x["stream_path"]) if isinstance(x.get("stream_path"), str) else None
        take.executed_refusal = {"n": n, "exit_code": x["exit_code"], "timed_out": x["timed_out"],
                                 "started_at": x["started_at"], "ended_at": x["ended_at"], "stream": stream,
                                 "refused": str(x["refused"] or e)}
        take.ledger_rows.append({"n": n, "sent": line, "expects": None,
                                 "exit": TIMED_OUT_EXIT if x["timed_out"] else x["exit_code"], "end": None,
                                 "then": None, "refused": take.executed_refusal["refused"]})
        self._evidence_line(take, {"kind": "turn", "n": n, "started_at": x["started_at"], "ended_at": x["ended_at"]})
        ended = types.SimpleNamespace(end_reason=_adapter.END_TIMED_OUT if x["timed_out"] else _adapter.END_ERROR)
        left, killed = self._quiesce(take, ended)
        take.executed_refusal["quiescence_kill"] = bool(killed)     # review r2 nit 4: carried, never dropped
        if left:
            take.survivors.append({"turn": n, "pids": list(left)})
            stopped = self.clock()
            for pid in left:
                self._evidence_line(take, {"kind": "background", "pid": pid, "stopped_at": stopped})
        unreadable = self._ctl(take, "snapshot", f"post-{n}")["unreadable_consequential"]
        self._retain_native(take, take.adapter_ref, n)    # 3c: kept as evidence when the source allows; never raised
        return unreadable

    def _retain_native(self, take, adapter, n: int) -> bool:
        """Live harness 3c: for an adapter that names a native session (native_session_path(home), home the take's
        config folder), copy it into session/native-turn-<n>.jsonl after turn n's post-n snapshot and before any next
        resume (native_snapshot.retain). False, with the reason kept, when it cannot be located or retained: nothing
        further is sent and the take stops for a human after cleanup and scan. An adapter without one: True."""
        locate = getattr(adapter, "native_session_rel", None)
        if not callable(locate):
            if callable(getattr(adapter, "native_session_path", None)):   # a host path only: never opened mid-take
                take.native_hook = True
                take.native_snapshot_refusal = (f"turn {n}: the adapter names no box road to its native session "
                                                f"(native_session_rel)")
                return False
            return True
        take.native_hook = True
        try:
            lister, reader = self.config_view(take)
            rel = locate(lister)
            take.native_rel = rel                                         # W-3b: the store's one admitted session
            take.native_snapshots.append(_native_snapshot.retain_bytes(take.folder, n, reader(rel)))
            return True
        except (_native_snapshot.SnapshotRefused, OSError) as e:
            if take.native_snapshot_refusal is None:
                take.native_snapshot_refusal = f"turn {n}: native session snapshot not retained: {e}"
            return False

    def _list_session_store(self, take, row, at: str, lister=None) -> None:
        """W-3b (glitch-b5's pre-freeze ruling, 16 Oct 2026): every entry of the take's session store (check_take
        SESSION_STORE_ROOTS, by harness) listed through `lister` (the box's, config_view, during the take; the host's
        after the restore), appended to take.session_store as {at, entries} or, when the listing fails, {at, refused}.
        Never raised: a refused listing is the checker's to refuse."""
        import check_take as _ct
        root = _ct.SESSION_STORE_ROOTS.get(row["agent"]["harness"])
        try:
            lister = lister or self.config_view(take)[0]
            take.session_store.append({"at": at, "entries": store_listing(lister, root)})
        except Exception as e:  # noqa: BLE001 - a listing that fails is recorded, never a pass
            take.session_store.append({"at": at, "refused": f"{type(e).__name__}: {str(e)[:200]}"})

    def _note_read_only_errors(self, take, adapter, n: int, turn) -> None:
        """glitch-b5's ruling on R15-2 (16 Oct 2026): every line of turn n's stream and of the harness's stderr that
        names EROFS or "Read-only file system" (READ_ONLY_ERROR), kept in take.read_only_errors as {turn, where,
        line} (capped), so the first live walks name each path the read-only root broke. Never raised."""
        try:
            sources = []
            if getattr(turn, "stream_path", None) and os.path.isfile(turn.stream_path):
                with open(turn.stream_path, encoding="utf-8", errors="replace") as fh:
                    sources.append(("stream", fh.read()))
            seen = getattr(adapter, "stderr_seen", None) or []
            if seen:
                sources.append(("stderr", seen[-1]))
            for where, text in sources:
                for line in text.split("\n"):
                    if READ_ONLY_ERROR.search(line) and len(take.read_only_errors) < READ_ONLY_ERRORS_MAX:
                        take.read_only_errors.append({"turn": n, "where": where, "line": line[:500]})
        except Exception as e:  # noqa: BLE001 - the record is evidence; its failure is named in it
            take.read_only_errors.append({"turn": n, "where": "reader", "line": f"{type(e).__name__}: {e}"[:500]})

    def _sweep_sessions(self, take, at: str) -> None:
        """W-3b (glitch-b5's ruling on review r14, 16 Oct 2026): box/run_take.sweep_sessions over the take container's
        writable locations, after the turn's processes are gone and before the teardown, appended to
        take.session_sweeps as {at, files, unreadable, escapes, mounts, scanned, truncated, expected} (expected: the
        read-write mounts the container should have, run_take.sweep_roots) or {at, refused}. Never raised."""
        try:
            doc = _run_take.sweep_sessions(self.runtime, take.launched.take_id, caller_env=self.caller_env)
            take.session_sweeps.append({"at": at, **doc, "expected": _run_take.sweep_roots(take.spec.run_tree)})
        except Exception as e:  # noqa: BLE001 - a sweep that fails is recorded, never a pass
            take.session_sweeps.append({"at": at, "refused": f"{type(e).__name__}: {str(e)[:200]}"})

    def config_folder(self, take, lease=None):
        """B11 (lane vendor-b11 round 3): the take's run_take.ConfigFolder for its O or G turns, through the box's
        census and reads of the config folder (ownership.config_folder): the take image, run tree, config folder and
        model, the codex lease's placement record (`lease`, the adapter's login: bound to the take's uid map; None
        for gemini), and the take's uid map."""
        harness = (take.row.get("agent") or {}).get("harness")
        uid_map = self.uid_map
        if callable(uid_map):                       # read at run time (the take container's own map), or given
            uid_map = uid_map(take)
        return self.ownership.config_folder(self.runtime, image=take.spec.image, harness=harness,
                                            run_tree=take.spec.run_tree, config_dir=take.config_dir,
                                            model=take.row["model"], lease=lease, uid_map=uid_map,
                                            caller_env=self.caller_env)

    def config_view(self, take) -> tuple:
        """(lister(rel_dir), reader(rel_path)) over the take's config folder through the box's operator_list and
        operator_read (drive-wiring review MAJOR 1: the folder is the agent's during the take). A failure of either is
        a SnapshotRefused naming the box step: an operator step's failure, never an agent event. A reader's None (the
        file is absent) is passed on."""
        road = self.ownership

        def call(what, **kw):
            try:
                return getattr(road, what)(self.runtime, image=take.spec.image, root_kind="config",
                                           run_tree=take.spec.run_tree, config_dir=take.config_dir,
                                           caller_env=self.caller_env, **kw)
            except Exception as e:  # noqa: BLE001 - OwnershipError, Refused or anything else
                raise _native_snapshot.SnapshotRefused(f"the box's {what} of the config folder failed "
                                                       f"({type(e).__name__}: {str(e)[:200]})") from None
        return (lambda rel_dir: call("operator_list", rel_dir=rel_dir),
                lambda rel_path: call("operator_read", rel_path=rel_path))

    def _take_records(self, take, row, adapter, turns) -> None:
        """S6c C6, C7, C8, C14, once the agent's processes are gone and before the scan: the session file copied out
        of the config folder through scrub.py as transcript.jsonl (round 3's publish_transcript, Ruling 10) and
        cross-checked against the streams; environment.json with every turn's credential source; the cost record;
        and driver-ledger.json in round 3's schema, binding environment.json's bytes."""
        ident, rows = take.identity, take.ledger_rows
        cc = isinstance(adapter, _cc.ClaudeCodeAdapter)
        recs = list(adapter.turn_records) if cc else []
        harness = row["agent"]["harness"]
        vendor = harness in VENDOR_HARNESSES          # live harness integration: its own native evidence, never Claude's
        src = None if vendor else take_session_file(take.config_dir, ident["session_id"])
        published, text, recorded, subagents = None, None, "unrecorded", None
        history = (native_history_record(harness, Path(take.folder) / _native_snapshot.SESSION_DIR,
                                         take.native_snapshots) if take.native_hook else None)
        joined = history is not None and history["status"] == "joined"
        cross = (gemini_cross_check(take.folder, take.native_snapshots, len(turns)) if harness == "gemini" and joined
                 else codex_cross_check(take.folder, take.native_snapshots, [t.exit_code for t in turns],
                                        sent=[r.get("sent") for r in rows], model=row.get("model"))
                 if harness == "codex" and joined else None)
        status = vendor_cross_check_status(harness, history, cross) if vendor else None
        if vendor:
            take.cross_check = ([status["why"]] if status["status"] == "refused"
                                else [] if status["status"] == "agreed" else None)
            # T4 edit B (glitch-b5 rounds 14 and 15, review e-71a2b94 finding 1): the host turn envelopes
            # vendor_record_binding reads, schema 1: one harness-turn per ledger turn row, recovery rows included, its
            # sent the row's, its stream that turn's by basename and sha256, and the CLI's own session id read from
            # that stream (codex thread.started, gemini init). src stays None, so the ledger's transcript stays None
            # for a vendor take (round 15 ruling 1): C3 reads the file, bound_items the envelopes; edit C rebinds
            # each sha256 to the masked bytes after the drive's scan
            envelopes = []
            for k, r in enumerate(rows, 1):
                stream = getattr(turns[k - 1], "stream_path", None) if k <= len(turns) else None
                raw = b""
                if stream and os.path.isfile(stream):
                    with open(stream, "rb") as fh:
                        raw = fh.read()
                first, key = ("thread.started", "thread_id") if harness == "codex" else ("init", "session_id")
                vid = None
                for line in raw.decode("utf-8", errors="replace").split("\n"):
                    try:
                        rec = json.loads(line)
                    except ValueError:
                        continue
                    if isinstance(rec, dict) and rec.get("type") == first:
                        vid = rec.get(key)
                        break
                envelopes.append({"type": "harness-turn", "harness": harness, "session_id": ident["session_id"],
                                  "vendor_session_id": vid, "n": k, "sent": r.get("sent"),
                                  "stream": os.path.basename(stream) if stream else None,
                                  "sha256": hashlib.sha256(raw).hexdigest() if stream else None})
            (Path(take.folder) / "transcript.jsonl").write_text("".join(json.dumps(e) + "\n" for e in envelopes),
                                                                encoding="utf-8")
        elif src is not None:
            try:
                published = publish_transcript(Path(src), Path(take.folder))
            except SystemExit as e:              # scrub.py refuses by SystemExit: a stop here, never an exit
                raise DriveRefused(f"the session file could not be published: {e}") from None
            subagents = copy_subagent_files(Path(src), ident["session_id"], Path(take.folder))   # Agent parity, R-A
            path = Path(take.folder) / "transcript.jsonl"
            text = path.read_text(encoding="utf-8", errors="replace")
            recorded = mode_recorded(path)
            take.cross_check = _cc.cross_check(recs, text, session_id=ident["session_id"]) if cc else []
        else:
            take.cross_check = [f"no session file for {ident['session_id']} in the take's config folder"]
        self._list_session_store(take, row, "publish", host_lister(take.config_dir))   # W-3b: at publish, host-side
        import check_take as _ct
        store_doc = {"harness": harness, "root": _ct.SESSION_STORE_ROOTS.get(harness),
                     "listings": [dict(x) for x in take.session_store], "sweeps": [dict(x) for x in take.session_sweeps]}
        if vendor:                                # review r15 MINOR 5: the vendor road's shell commands read too
            cmds, unread = _ct.vendor_shell_commands(take.folder, harness)
            store_doc["nested_cli_calls"] = sum(len(_ct.nested_cli_mentions(c)) for c in cmds)
            store_doc["unread_stream_lines"] = len(unread)        # the adapter judged the stream; counted here
        self._write(take, SESSION_STORE_RECORD, store_doc)
        self._write(take, READ_ONLY_ERRORS_RECORD, {"read_only_root": True, "errors": list(take.read_only_errors)})
        if vendor:                                # W-3b: no checker reads a vendor take yet, so the driver judges it
            bad = vendor_nested_problems(take.session_store, take.session_sweeps, harness, take.native_rel, cmds,
                                         [], take.spec.run_tree)
            if bad:
                take.store_refusal = f"[{_ct.NESTED_AGENT}] a nested agent may have run: {'; '.join(bad[:3])}"
        sources = {id(r): (recs[k]["api_key_source"] if k < len(recs) else None) for k, r in enumerate(rows)}
        env = with_turns(take.environment, rows, sources)
        write_record_atomically(Path(take.folder) / ENVIRONMENT_RECORD_FILE, env)    # replaced whole, never merged
        with open(os.path.join(take.folder, ENVIRONMENT_RECORD_FILE), "rb") as fh:
            env_sha = hashlib.sha256(fh.read()).hexdigest()
        version = adapter.version()
        cost = None
        if cc and text is not None:
            try:                       # W6J-R1-1: a session file the cost reader refuses is a disagreement, never a crash
                cost = _cc.cost_record(recs, text, model=row["model"], version=version)
            except _cc.StreamError as e:
                take.cross_check = list(take.cross_check) + [f"the cost reader refused the session file: {e}"]
        outcome = take.outcome if (src is not None or vendor) else (
            f"{take.outcome} \u2014 no session file for {ident['session_id']}")
        pin = self.pin_for(row)
        ledger = {"kind": "take", "task": row["task"], "half": row["half"], "wording": row.get("wording"),
                  "pressure": row.get("pressure"), "repeat": row.get("repeat"),     # W8A-R1-2: the row's cell
                  "arm": row["arm"], "model_requested": row["model"],
                  "agent": {"harness": row["agent"]["harness"], "version": version},
                  "session_id": ident["session_id"], "project": self.project_for(row), "source": ident["source"],
                  "row": ident["row"], "row_commit": ident["row_commit"],
                  "permission_mode": recorded, "permission_mode_passed": pin.get("permission_mode"),
                  "permission_mode_recorded": recorded, "budget_s": self.budget_s,
                  "finalize_wait_s": self.finalize_wait_s, "poll_s": self.poll_s,     # BOOTSTRAP B4: the cap, the poll
                  "gars_tree_sha": ident["gars_tree_sha"], "fixture": ident["fixture"], "claude_version": version,
                  "turns": [dict(r) for r in rows], "outcome": outcome,
                  # live harness 3a: an executed turn whose record was refused leaves agent output unknown
                  "first_agent_turn": (None if take.executed_refusal is not None
                                       else any(t.agent_output for t in turns)),
                  "environment": {"file": ENVIRONMENT_RECORD_FILE, "sha256": env_sha},
                  "transcript": "transcript.jsonl" if src is not None else None, "published": published,
                  "cross_check": None if take.cross_check is None else list(take.cross_check),
                  "cost": cost,
                  "streams": [os.path.basename(t.stream_path) for t in turns if t.stream_path]}
        if not vendor:          # glitch-b5's Agent parity ruling (16 Oct 2026): the sub-agent files copied, named, bound
            ledger["subagents"] = subagents
        ledger["operator_steps"] = [            # the ownership road: operator steps, never agent events
            {"step": OWNERSHIP_STEPS[0], "ok": (take.grant or {}).get("ok"), "record": OWNERSHIP_GRANT_RECORD},
            {"step": OWNERSHIP_STEPS[1], "ok": (take.restore or {}).get("ok"), "record": OWNERSHIP_RESTORE_RECORD}]
        if take.native_hook:                      # live harness 3c: only for an adapter that names a native session
            ledger["native_snapshots"] = [dict(r) for r in take.native_snapshots]
            ledger["native_snapshot_refusal"] = take.native_snapshot_refusal
            ledger["native_history"] = history
        if harness == "codex":                    # D-INT-2: each turn's served-model evidence, recorded per take
            ledger["served_model"] = [None if t.identity is None else dict(t.identity["model"]) for t in turns]
        if vendor:                                # live harness integration: pending is recorded as pending
            ledger["cross_check_status"] = status
            take.cross_check_status = dict(status)
        if take.executed_refusal is not None:     # live harness 3a: only when a turn's record was refused
            ledger["executed_refusal"] = dict(take.executed_refusal)
            if take.executed_refusal["stream"] is not None:
                ledger["streams"].append(take.executed_refusal["stream"])
        self._write(take, LEDGER_FILE, ledger)

    @staticmethod
    def _rate_limited(row, turns) -> bool:
        """S6c C13: whether an API-error record of the take carries one of routing.json's rate-limit markers for the
        take's harness (status or type by exact membership, or a text marker by routing's own bounded search): the
        ledger's PAUSE outcome before the first agent turn. The route itself stays routing.py's."""
        marks = _routing.load_table()["rate_limit_markers"].get(row["agent"]["harness"]) or {}
        for t in turns:
            for e in t.api_errors:
                if (e.get("status") in (marks.get("status") or ()) or e.get("type") in (marks.get("type") or ())
                        or (isinstance(e.get("text"), str)
                            and _routing.rate_limit_text_marker(e["text"], marks.get("text") or ()) is not None)):
                    return True
        return False

    def _refused(self, take, e: BaseException) -> None:
        """R4-9: the pre-turn refusal record (its type and message; never a secret: lock, launch and reply texts)."""
        self._write(take, REFUSAL_RECORD, {"refused": type(e).__name__, "why": str(e)[:500]})

    def _cleanup(self, take, adapter) -> None:
        """R4-11, on every road: end the adapter, kill and poll the agent's leftover processes, remove every container
        by its recorded id. Each failure is recorded in take.cleanup and written to teardown.json; none stops the
        rest."""
        if adapter is not None and take.adapter_open:          # S6b (d): the driver's own flag, never the adapter's
            take.adapter_open = False
            try:
                adapter.end_take()
            except Exception as e:  # noqa: BLE001
                take.cleanup.append(f"end_take: {type(e).__name__}: {e}")
        try:
            self._kill(take)
            if self._gone(take):
                take.cleanup.append("leftover agent processes survived the kill")
        except Exception as e:  # noqa: BLE001
            take.cleanup.append(f"leftover processes: {type(e).__name__}: {e}")
        record = None
        try:
            record = _run_take.teardown(self.runtime, take.launched, sidecar=take.sidecar, record_dir=take.folder,
                                        caller_env=self.caller_env)
        except _run_take.TeardownError as e:
            record = e.record
            take.cleanup.append(f"teardown: {e}")
        except Exception as e:  # noqa: BLE001
            take.cleanup.append(f"teardown: {type(e).__name__}: {e}")
        take.teardown = record
        try:                     # W6H-R1-8c: a failed write is recorded, never raised over the drive's own exception
            self._write(take, TEARDOWN_RECORD, {"teardown": record, "problems": list(take.cleanup),
                                                "quiescence_survivors": list(take.survivors)})
        except Exception as e:  # noqa: BLE001
            take.cleanup.append(f"{TEARDOWN_RECORD}: {type(e).__name__}: {e}")
        if take.settings is not None:     # the settings guard's record: its baseline and every per-turn check
            try:
                self._write(take, SETTINGS_RECORD, take.settings)
            except Exception as e:  # noqa: BLE001
                take.cleanup.append(f"{SETTINGS_RECORD}: {type(e).__name__}: {e}")
        self._restore_ownership(take)    # the ownership road: after teardown (returned or raised), pre-postflight
        if not take.ownership_hold:      # review MAJOR 1: the driver's ledger joins the evidence once it is the host's
            self._copy_evidence_ledger(take)

    def drive(self, row: dict, container_id: str) -> dict:
        """One take, from preflight to its routable records (R4-9, R4-10), cleaning up on every road (R4-11)."""
        with self._lock:
            take = self._by_id.get(container_id)
        if take is None or take.launched is None or not take.launched.ok or take.row["slot"] != row["slot"]:
            raise DriveRefused(f"no completed launch of slot {row.get('slot')!r} is recorded under {container_id}")
        if take.driven:
            raise DriveRefused(f"take {container_id} was already driven")
        take.driven = True
        turns, unreadable, survivors, killed, adapter, state, post = [], [], 0, False, None, None, None
        finalize_abort, money = False, []
        take.identity = self._identity(row)                   # S6c C7: refused before anything starts
        try:
            self._evidence_line(take, {"kind": "take", "model": row["model"],     # S6b C10: before begin
                                       "agent": {"harness": row["agent"]["harness"],
                                                 "version": self.pin_for(row)["version"]},
                                       "run_tree": "", "home": None})
            ok = self._preflight(take, row["agent"]["harness"])      # W6H-R1-8a: read inside the try
            if ok:                # the settings guard at turn 1, at preflight's moment: a problem is a pre-turn refusal
                first = self._settings_problems(take, "pre-1")
                if first:
                    self._refused(take, DriveRefused(f"pre-1: the run tree's Claude settings: {'; '.join(first)}"))
                    ok = False
            if ok:
                try:              # W6H-R1-7: the adapter's making or start before turn 1 is a pre-turn refusal
                    adapter = self.adapter_for(row, take)
                    adapter_identity_problems(adapter, row)   # W7B (W6B-R1-3): the row's harness is the adapter's
                    take.adapter_open = True                  # S6c Q-w6i-3: a start that raises is still ended
                    adapter.start_take(dict(row))
                    money = self._environment(take, row, adapter)   # S6c C8: written before the first turn
                except AdapterIdentityRefused:                # W7B (W6B-R1-3): a mis-wired driver stops, never rehearses
                    raise
                except Exception as e:  # noqa: BLE001 - nothing of the agent ran: harness-side (plan, row 1)
                    self._refused(take, e)
                    ok = False
            if ok and money:                                  # S6c C8: round 3's money line stops the driver
                raise DriveRefused(f"the exec would give the agent {money}: an API key or a billing route")
            if ok:
                script = _Script(self.script_for(row), take.ledger_rows,        # S6c C13: markers, recovery, stop
                                 strict=self.strict_script)
                for n, line in enumerate(script, 1):
                    if n > 1:
                        unreadable += self._ctl(take, "snapshot", f"pre-{n}")["unreadable_consequential"]
                        later = self._settings_problems(take, f"pre-{n}")   # the settings guard: turn n not sent
                        if later:
                            take.settings_stop = f"pre-{n}: the run tree's Claude settings: {'; '.join(later)}"
                            break
                    take.adapter_ref = adapter
                    try:
                        turn = adapter.turn(line, first=(n == 1), budget_s=self.budget_s)
                    except _run_take.ConfigFolderRefused as e:    # B11 (vendor-b11 R-CF): refused before its exec,
                        if n == 1:                                # routed as the settings guard is: a rehearsal
                            self._refused(take, e)
                            ok = False
                        else:                                     # after turn 1, a stop for a ruling
                            take.config_stop = f"pre-{n}: the config folder: {'; '.join(e.problems)}"
                        break
                    except _adapter.ExecutedTurnRefused as e:     # live harness 3a: the turn ran; account for it
                        unreadable += self._executed_refused(take, n, line, e)
                        after = self._settings_problems(take, f"post-{n}")   # review MINOR 2: this road too
                        if after:
                            take.settings_stop = f"post-{n}: the run tree's Claude settings: {'; '.join(after)}"
                        break
                    turns.append(turn)
                    self._evidence_line(take, {"kind": "turn", "n": n, "started_at": turn.started_at,
                                               "ended_at": turn.ended_at})              # S6b C10
                    left, k = self._quiesce(take, turn)
                    survivors += len(left)
                    if left:
                        take.survivors.append({"turn": n, "pids": list(left)})
                        stopped = self.clock()
                        for pid in left:                   # S6b C10: stopped at the cap, before post-n
                            self._evidence_line(take, {"kind": "background", "pid": pid, "stopped_at": stopped})
                    killed = killed or (k and bool(left))
                    unreadable += self._ctl(take, "snapshot", f"post-{n}")["unreadable_consequential"]
                    retained = self._retain_native(take, adapter, n)  # live harness 3c: before any next resume
                    self._list_session_store(take, row, f"post-{n}")      # W-3b: after every turn, through the box
                    self._sweep_sessions(take, f"post-{n}")                # W-3b (r14): the container, before teardown
                    self._note_read_only_errors(take, adapter, n, turn)      # R15-2: what the read-only root broke
                    after = self._settings_problems(take, f"post-{n}")   # the settings guard, the last turn's too
                    if after:
                        take.settings_stop = f"post-{n}: the run tree's Claude settings: {'; '.join(after)}"
                        break
                    if not script.read(turn) or not retained:         # S6c C13: an unheld marker, or a cut turn
                        break
                    step = OPERATOR_STEPS.get((row["task"], script.done)) if script.done is not None else None
                    if step is not None and script.pending is not None:   # S6b C9: between post-n and pre-(n+1)
                        if not self._operator_step(take, row, step):
                            finalize_abort = True                     # C12: nothing further is sent
                            script.then(step[0], failed=True)
                            break
                        script.then(step[0], failed=False)
                take.outcome = script.outcome(turns, finalize_abort=finalize_abort, wait_s=self.finalize_wait_s,
                                              rate_limited=self._rate_limited(row, turns))
                if take.executed_refusal is not None:
                    r = take.executed_refusal
                    take.outcome = (f"incomplete \u2014 turn {r['n']} executed and its record was refused: "
                                    f"{r['refused']}")
            state = _run_take.container_state(self.runtime, take.launched.take_id, caller_env=self.caller_env)
        finally:
            # _cleanup ends with the ownership restore; a held restore runs no postflight (nor scan, nor commit)
            self._cleanup(take, adapter)
            post = self._postflight(take, row) if not take.ownership_hold else None   # S6b (e): pre-scan
        if take.ownership_hold:                               # the ownership road: no postflight, scan or commit
            raise DriveRefused(f"{take.ownership_hold}: the take's folders are kept for a human ruling, never a "
                               f"re-run")
        if post is None or post.get("ok") is not True:        # a credential file left behind is a stop for a human
            why = "the postflight check did not run" if post is None else post["checks"][0]["detail"]
            raise DriveRefused(f"postflight: {why}; the config folder is kept for a human")
        if ok and (turns or take.executed_refusal is not None):   # S6c C6-C8, C14; 3a: a launched turn needs it
            self._take_records(take, row, adapter, turns)
        # R4-10: scan -> mask, then the checker; routing and the commit follow in batch.py.
        scan = _scan_record.scan(self.take_files(take), list(self.secrets()), rules_scanner=self.rules_scanner,
                                 read_shapes=scan_read_shapes(row),
                                 holdout_matcher=self.holdout_matcher)
        if not _scan_record.passed(scan):
            why = "; ".join(f"{r['path']}:{r['line']} ({r['kind']}): {r['why']}" for r in scan["refused"])
            raise DriveRefused(f"the drive scan refused the take: {why}")
        if row["agent"]["harness"] in VENDOR_HARNESSES and Path(take.folder, "transcript.jsonl").is_file():
            # T4 edit C (glitch-b5 round 15 ruling 2; review e-71a2b94 finding 2, option (a)): the scan masks turn
            # streams and session/ snapshots in place, so each sha256 edit B's envelopes and the ledger's
            # native_snapshots bind is moved along the scan's own record, from its sha256_before to its sha256_after,
            # the bytes the checker reads; a binding the scan's before does not match is left, and refuses. The record
            # is the driver ledger's own native_snapshots sha256, where _vendor_last_snapshot, vendor_raw_records, the
            # registration and the regrade read it (its closed keys and each entry's file and sha256 stay;
            # native_history keeps its pre-scan basis); with nothing masked no byte changes
            moved = {os.path.relpath(f["path"], take.folder): (f["sha256_before"], f["sha256_after"])
                     for f in scan["files"]}
            path = os.path.join(take.folder, "transcript.jsonl")
            with open(path, encoding="utf-8") as fh:
                envs = [json.loads(x) for x in fh.read().splitlines() if x]
            rebound = False
            for env in envs:
                was, now = moved.get(env.get("stream"), (None, None))
                if was is not None and env.get("sha256") == was and now != was:
                    env["sha256"], rebound = now, True
            if rebound:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write("".join(json.dumps(env) + "\n" for env in envs))
            path = os.path.join(take.folder, LEDGER_FILE)
            with open(path, encoding="utf-8") as fh:
                led = json.load(fh)
            rebound = False
            for snap in led.get("native_snapshots") or []:
                was, now = moved.get(f"session/{snap.get('file')}", (None, None))
                if was is not None and snap.get("sha256") == was and now != was:
                    snap["sha256"], rebound = now, True
            if rebound:                       # replaced whole, in the ledger writer's own form
                _run_take._write_json(path + ".partial", led)
                os.replace(path + ".partial", path)
        if take.config_stop is not None:          # B11 after turn 1, as the settings guard: cleaned and scanned
            raise DriveRefused(f"{take.config_stop}: no further turn is sent; the take is kept for a human ruling "
                               f"(no registered harness-error row reads it), never a re-run")
        if take.settings_stop is not None:        # the settings guard after turn 1: cleaned, recorded and scanned
            raise DriveRefused(f"{take.settings_stop}: no further turn is sent; the take is kept for a human ruling "
                               f"(no registered harness-error row reads it), never a re-run")
        if take.executed_refusal is not None:     # live harness 3a: cleaned, recorded and scanned; a human rules
            r = take.executed_refusal
            raise DriveRefused(f"turn {r['n']} executed and its record was refused ({r['refused']}): the take is "
                               f"kept for a human ruling, never a rehearsal or a re-run")
        if take.native_snapshot_refusal is not None:     # live harness 3c: cleaned, recorded and scanned
            raise DriveRefused(f"{take.native_snapshot_refusal}: the take is kept for a human ruling, never a "
                               f"rehearsal or a re-run")
        if take.store_refusal is not None:               # W-3b: a vendor take's nested agent, cleaned and scanned
            raise DriveRefused(f"{take.store_refusal}: the take is kept for a human ruling, never a rehearsal or a "
                               f"re-run")
        pending = take.cross_check_status
        if ok and turns and pending is not None and pending["status"] == "pending":   # D8: graded only cross-checked
            raise NativeCrossCheckPending(f"native cross-check pending ({pending['why']}): the take is kept for a "
                                          f"human ruling, never graded, never readers-disagree, never a re-run")
        ids = tuple(_routing.load_table()["checker_reasons_become_events"]["ids"])
        if ok and turns:
            checked = self.checker(row, take, list(turns))
            diffs = self._operator_check(take, row)          # S6b C11: endstate's re-verification, the driver's own
        else:                     # W6H-R1-4: nothing of the agent ran, so there is nothing to check
            checked = {"checker_reasons": [], "checker_events": dict.fromkeys(ids, 0)}
            diffs = 0
        if not isinstance(checked, dict) or set(checked) != set(CHECKER_KEYS):
            raise DriveRefused(f"the checker's record is not exactly {CHECKER_KEYS}")
        events = checked["checker_events"]
        if (ACCOUNT_EMAIL_EVENT not in ids or not isinstance(events, dict) or set(events) != set(ids)
                or not all(isinstance(v, int) and not isinstance(v, bool) and v >= 0 for v in events.values())):
            raise DriveRefused(f"the checker's events are not one count per event id {sorted(ids)}")
        # W6H-R1-2: the account email is counted by the scan's masked hits alone; a checker count above them means
        # an email instance the scan did not mask, which is refused, never added.
        emails = sum(1 for m in scan["masked"] if m["kind"] == EMAIL_SECRET)
        if events[ACCOUNT_EMAIL_EVENT] > emails:
            raise DriveRefused(f"the checker counts {events[ACCOUNT_EMAIL_EVENT]} account-email event(s) and the "
                               f"scan masked {emails}")
        reach = scan["events"] + sum(v for k, v in events.items() if k != ACCOUNT_EMAIL_EVENT)
        box = {"preflight_ok": ok, "container_started": True, "container_exited": not state["running"],
               "sidecar": sidecar_health(take.evidence_dir),
               "unexplained_operator_diffs": diffs,
               "checker_reasons": checked["checker_reasons"], "quiescence_kill": killed,
               "outside_reach_events": reach,
               "finalize_abort": finalize_abort, "committed": False,
               "unreadable_consequential": list(dict.fromkeys(unreadable)),
               "quiescence_cap_survivors": survivors}
        return _adapter.harness_records(turns, pin=self.pin_for(row), box=box)

    # ------------------------------------------------------------------------------------------- remove (R4-11)
    def remove(self, container_id: str) -> None:
        """Every container the take recorded (W6H-R1-3: the take, its sidecar and its proxy, by their recorded ids;
        the given id alone when the driver recorded no launch for it): each one the full listing still holds is
        removed again by its id; any still listed after raises LeakedContainer naming them, and so does a network
        whose removal the teardown recorded as failed. batch then records A LEAK: the take keeps its route, the loop
        stops."""
        with self._lock:
            take = self._by_id.get(container_id)
        launched = take.launched if take is not None and take.launched is not None else None
        ids = launched.ids() if launched is not None else [container_id]
        if container_id not in ids:
            ids = [container_id, *ids]
        for cid in _run_take.leaked(self.runtime, ids, caller_env=self.caller_env):
            argv = (list(take.sidecar.rm_argv_for(cid)) if launched is not None and cid == launched.sidecar_id
                    else [_run_take.RUNTIME_CLIENT, "rm", "--force", cid])
            self.runtime.run(argv, env=self._env(), timeout=_run_take.STEP_TIMEOUT_S)
        still = _run_take.leaked(self.runtime, ids, caller_env=self.caller_env)
        if still:
            leak = _run_take.LeakedContainer(f"still listed after their removal: {', '.join(still)}")
            leak.leaked_ids = list(still)          # S6-gap4-2: batch commits them as leaked_containers
            raise leak
        if take is not None and take.grant is not None and take.grant["ok"] and take.restore is None:
            self._restore_ownership(take)   # the ownership road: a drive refused before its cleanup; containers gone
        steps = (take.teardown or {}).get("steps", []) if take is not None else []
        bad = [s for s in steps if s.get("step") == "network-rm" and s.get("returncode") != 0]
        if bad and launched is not None and launched.network_id:
            leak = _run_take.LeakedContainer(f"the take's network {launched.network_id} was not removed "
                                             f"(teardown recorded network-rm {bad[0].get('returncode')!r})")
            leak.leaked_ids = [NETWORK_PREFIX + launched.network_id]   # R-S6-net: the restart lists networks too
            raise leak

    # ------------------------------------------------------------------------------------------- the repo's hooks
    def take_files(self, take) -> list:
        """Every file in the take folder, (absolute path, scan kind), by the closed map; an unknown file refuses."""
        out = []
        for base, dirs, files in os.walk(take.folder, followlinks=False):
            dirs.sort()
            for name in sorted(files):
                path = os.path.join(base, name)
                rel = os.path.relpath(path, take.folder).split(os.sep)
                out.append((path, record_kind(rel)))      # W8A: the closed map, shared with walk_files
        return out

    def record_files(self, row: dict, attempt: int) -> list:
        """TakeRepo's record_files: the slot's latest unpublished take's files ([] when none was launched)."""
        with self._lock:
            take = self._by_slot.get(row["slot"])
        if take is not None and self._unrestored(take):     # the ownership road: never read, scanned or committed
            raise DriveRefused(f"{self._unrestored(take)}: the take's folders are kept for a human ruling")
        return [] if take is None else self.take_files(take)

    def checker_constants_sha256(self, row: dict):
        """BOOTSTRAP (review MINOR 3): the digest of the constants the checker read for the slot's take (take_checker
        records it from the design view), or None when no checker read it; read by walk_runner before published()."""
        with self._lock:
            take = self._by_slot.get(row.get("slot")) if isinstance(row, dict) else None
        return getattr(take, "checker_constants_sha256", None)

    def agent_summary(self, row: dict):
        """glitch-b5's Agent parity ruling, part 6: the checked transcript's Agent calls and sub-agent models
        (take_checker records them), or None when no checker read one; read by walk_runner into check.json."""
        with self._lock:
            take = self._by_slot.get(row.get("slot")) if isinstance(row, dict) else None
        return getattr(take, "agent_summary", None)

    def no_output_nudges(self, row: dict):
        """glitch-b5's ruling 3 (i): how many no-visible-output nudges the transcript the checker read carries
        (take_checker records it), or None when no checker read one; read by walk_runner into check.json."""
        with self._lock:
            take = self._by_slot.get(row.get("slot")) if isinstance(row, dict) else None
        return getattr(take, "no_output_nudges", None)

    def published(self, row: dict, attempt: int) -> None:
        """TakeRepo's on_published (R4-11): the take's records are committed, so its config folder is deleted (by
        the path launch recorded), and the slot's next take starts clean."""
        with self._lock:
            take = self._by_slot.pop(row["slot"], None)
        if take is None:
            return
        if self._unrestored(take):                          # the ownership road: the folders are never removed
            self.publish_problems.append(f"slot {row.get('slot')!r} attempt {attempt}: {self._unrestored(take)}")
            raise DriveRefused(f"{self._unrestored(take)}: the config folder is kept for a human")
        self.published_takes.append(take)
        launched = take.launched if take.launched is not None else _run_take.Launched(config_dir=take.config_dir)
        try:
            _run_take.remove_config_dir(launched, published=True)
        except Exception as e:  # noqa: BLE001 - recorded here (Q6) and raised for TakeRepo's publish_problems
            self.publish_problems.append(f"slot {row.get('slot')!r} attempt {attempt}: {type(e).__name__}: {e}")
            raise


# =====================================================================================================================
# ROUND 4, SLICE S6b (lane w6i; this file moved from lane w6h to lane w6i under glitch-1b's ruling S6b-gap4-1): the
# carried items, edited in place in parts 1 and 2 above (round 3's bytes stay untouched):
#   (d)       TakeDriver ends the adapter by its own flag (_Take.adapter_open, set when start_take returned), never by
#             reading the adapter's private state (ruling D6).
#   (e)       preflight.postflight runs in drive()'s finally, after the cleanup and before the scan, on every road; it
#             is written as postflight.json (scan kind preflight). A record that is not ok (a credential-like file
#             left in the config folder), or a postflight that could not run, raises DriveRefused: a stop for a
#             human, and the config folder is kept (it goes only after a commit).
#   Q6 (D5)   TakeDriver.published records a failed config-folder deletion in its own publish_problems and raises it
#             on for TakeRepo's; launch() refuses while any is recorded, so a config folder is never reused silently.
#   W6H-R2-1  leaked_ids() refuses an outcome without leaked_container or leaked_containers with HistoryRefused, never
#             a bare KeyError.
#   R-S6-net  a network the teardown failed to remove is carried as "network:<id>" in the leak's leaked_ids (batch
#             commits it in leaked_containers), and the restart refusal lists the networks for those ids.
#   C10       the driver's evidence ledger (endstate's ledger.jsonl): the take record before the sidecar's begin, a
#             turn record per line sent, a background record per cap survivor (stopped before post-n), an operator
#             record per operator event.
#   C9/D8     the closed OPERATOR_STEPS table: between post-n and pre-(n+1) the driver does the step host-side in
#             the run tree and logs it; a write on an excluded path is refused, never logged.
#   C12       confounded-design's finalize wait (finalize_wait_s, the injected clock): a samples.csv that never
#             comes is round 3's finalize abort (ledger.finalize_abort, nothing further sent).
#   C11       the operator-diff count is endstate's operator_check over the evidence after finish, written as
#             operator-check.json; the checker hands only its reasons and events (CHECKER_KEYS).
# =====================================================================================================================

NETWORK_PREFIX = "network:"

# C9 / ruling D8: the closed operator-step table, (task, the operator line it follows) -> (event id, action); frozen
# into the pre-registration at CP6. Its sources: explain-not-act's save is fixtures/gen_explain_not_act.py's
# SAVE_AFTER_STEP (2) and operator_save (SAVE_PATH), the task's decision `operator-save`; confounded-design's is round
# 3's step-3 then-step, dropped from tasks/confounded-design.json's script (its decision `script-from-round-3`, line
# 190) and named for CP2's driver: wait up to finalize_wait_s for stage 00's samples.csv, then copy the fixture's
# design table over it (round 3's drive.py 1405-1425); if it never appears, round 3's finalize abort (C12).
OPERATOR_SAVE, OPERATOR_FINALIZE = "save", "finalize-copy"
# W6I-R1-4: where confounded-design's generator puts the design table: its <out> is the source template's folder
# above `src` (gen_confounded_seed2 writes <out>/src/... and <out>/samples.csv); a test binds the two.
DESIGN_TABLE = "data/staging/{project}/samples.csv"
OPERATOR_STEPS = {
    ("explain-not-act", 2): ("operator-save", OPERATOR_SAVE),
    ("confounded-design", 3): ("wait-for-samples-csv-then-copy-design", OPERATOR_FINALIZE),
}
_FULL_ID = re.compile(r"[0-9a-f]{64}")


class HistoryRefused(RuntimeError):
    """W6H-R2-1: a committed outcome the restart cannot read (a leak key missing)."""


def leaked_networks(runtime, recorded_ids, *, caller_env=None) -> list:
    """R-S6-net: the "network:<id>" entries of recorded_ids still in the runtime's full network listing (no listing
    when none is recorded)."""
    nets = [i[len(NETWORK_PREFIX):] for i in recorded_ids if isinstance(i, str) and i.startswith(NETWORK_PREFIX)]
    if not nets:
        return []
    bad = [n for n in nets if not _FULL_ID.fullmatch(n)]
    if bad:
        raise _run_take.Refused("a recorded network id is not a full 64-hex id")
    c = runtime.run([_run_take.RUNTIME_CLIENT, "network", "ls", "--no-trunc", "--quiet"],
                    env=_run_take.runtime_env(caller_env), timeout=_run_take.STEP_TIMEOUT_S)
    if c.returncode != 0:
        raise _run_take.Refused(f"the network listing failed (exit {c.returncode}): a restart is refused unread")
    listed = {line.strip() for line in c.stdout.splitlines() if line.strip()}
    if any(not _FULL_ID.fullmatch(x) for x in listed):
        raise _run_take.Refused("the network listing holds a line that is not a full id")
    return [n for n in nets if n in listed]


# =====================================================================================================================
# ROUND 4, SLICE S6c (lane w6j; drive.py moved from lane w6i to lane w6j under glitch-1b's ruling S6c-gap4-1): the
# drive loop's agent side. In-place edits in part 2 above are marked "S6c"; round 3's bytes stay untouched.
#   W6I-R2-2  confounded-design's finalize copy writes the bytes whose md5 it checked, never a second read.
#   Q-w6i-3   the driver's adapter-open flag is set before start_take, so an adapter whose start raised after it
#             opened is still ended on the cleanup road (an end_take that finds nothing open is a cleanup record).
#   C13       the marker / recovery / stop loop (round 3's drive.py:1347-1402, the same file's main()): TakeDriver
#             sends each step's line, reads the reply against the step's marker (exact and case-sensitive: round 3's
#             marker_holds), sends the step's pre-registered recovery (at most `at_most` times, once by default)
#             only when the reply holds the recovery's own marker and not the step's, and sends nothing past an
#             unheld marker: the take is `stopped` and graded as it stands. A turn the host saw end other than
#             end_turn is cut there. The operator step after step n (ruling D8) is keyed by the step's own n, so a
#             recovery turn never shifts it. Each line sent is one ledger row (n, sent, expects, exit, end, held,
#             recovery, then: round 3's turns[] fields, plus the host's turn end), and the outcome is round 3's
#             vocabulary (check_take's driver_outcome_shapes). The stop itself is classified by pause_adherence
#             (labels4's taxonomy: ran-ahead, reworded-marker, stalled, asked-to-proceed, refused, timed-out, other)
#             from pause_evidence(rows), never by the driver: the driver reads only whether the marker is there.
# =====================================================================================================================

import claude_code_adapter as _cc  # noqa: E402

TIMED_OUT_EXIT = 124      # round 3's exit for a turn cut at the budget (check_take.completion_problems reads it)
LEDGER_FILE = "driver-ledger.json"
IDENTITY_KEYS = ("session_id", "row", "row_commit", "source", "fixture", "gars_tree_sha")


VENDOR_HARNESSES = ("codex", "gemini")
NATIVE_HISTORY_BASIS = "unmasked retained originals, before the drive scan"   # batch-5 review nit 4


def gemini_cross_check(take_folder, refs, n_turns: int, *, readers=None) -> dict:
    """The Gemini cross-check D8 names, through the ONE join the acceptance check also runs
    (native_reader_registration.join_session; registration review finding 2): each turn's host-captured stream joined
    to that interaction of the take's last retained native snapshot, read by the registered reader. `pending` without a
    registered reader (production_readers: no committed acceptance record); `refused` on any disagreement, an extra or
    a missing interaction, or an incomplete interaction; `agreed` only when every turn joins complete."""
    readers = _registration.production_readers() if readers is None else readers
    reader = readers.get("gemini")
    if reader is None:
        return {"status": "pending", "why": "no registered Gemini native reader (no committed acceptance record)"}
    folder = Path(take_folder)
    try:
        raw = _vendor_provenance.referenced_bytes(folder / _native_snapshot.SESSION_DIR, refs[-1])
        streams = [(folder / f"turn-{n}.jsonl").read_text(encoding="utf-8") for n in range(1, n_turns + 1)]
    except (IndexError, OSError, UnicodeError, _vendor_provenance.ProvenanceRefused) as e:
        return {"status": "refused", "why": f"{type(e).__name__}: {e}"}
    got = _registration.join_session(raw, streams, reader)
    if got["status"] != "PASS":
        return {"status": "refused", "why": got["why"]}
    return {"status": "agreed", "why": None}


def codex_cross_check(take_folder, refs, exit_codes, *, sent, model, readers=None) -> dict:
    """Codex slice 3: D8's cross-check for a Codex take, through the ONE join the acceptance check also runs
    (native_reader_registration.codex_join_session): each turn's exec stream joined to that turn of the take's last
    retained rollout, its recorded prompt to the line sent (`sent`, the ledger rows') and its requested model to the
    take's (`model`; lane vendor-b25, Codex review M1). `pending` without a registered Codex reader; `refused` on any
    disagreement, an extra or missing turn, or an incomplete turn; `agreed` only when every turn joins complete."""
    readers = _registration.production_readers() if readers is None else readers
    if readers.get("codex") is None:
        return {"status": "pending", "why": "no registered Codex native reader (no committed acceptance record)"}
    folder = Path(take_folder)
    try:
        raw = _vendor_provenance.referenced_bytes(folder / _native_snapshot.SESSION_DIR, refs[-1])
        streams = [(folder / f"turn-{n}.jsonl").read_text(encoding="utf-8") for n in range(1, len(exit_codes) + 1)]
    except (IndexError, OSError, UnicodeError, _vendor_provenance.ProvenanceRefused) as e:
        return {"status": "refused", "why": f"{type(e).__name__}: {e}"}
    got = _registration.codex_join_session(raw, streams, list(exit_codes), sent=list(sent), model=model)
    if got["status"] != "PASS":
        return {"status": "refused", "why": got["why"]}
    return {"status": "agreed", "why": None}


def vendor_cross_check_status(harness: str, history, cross=None) -> dict:
    """Live harness integration: a non-Claude take's cross-check, from its own native evidence only. Gemini: its
    retained snapshots' history record (pending while no reviewed reader is registered; refused when the snapshots are
    missing, unreadable or inconsistent; a joined history still leaves the stream join pending, since the projection
    and the stream join are unregistered). Codex the same way, from its retained rollouts (Codex slice 3). Never a pass."""
    if harness in ("gemini", "codex"):        # Codex slice 3: Codex reads its own retained rollouts the same way
        if history is None:
            return {"status": "refused", "why": f"the {harness} adapter retained no native snapshot record"}
        if history["status"] == "refused":
            return {"status": "refused", "why": f"native snapshots: {history['why']}"}
        if history["status"] == "pending":
            return {"status": "pending", "why": history["why"]}
        if cross is None:
            return {"status": "pending", "why": "native snapshots join; the stream join to them is not registered yet"}
        return dict(cross)
    raise DriveRefused(f"no vendor cross-check road for harness {harness!r}")


def native_history_record(harness: str, session_dir, refs, *, readers=None) -> dict:
    """Live harness integration: what the take's retained native snapshots prove, for the driver ledger. Step 1's
    vendor_provenance.session_history_facts over them, through the PRODUCTION reader registry unless `readers` is
    given (tests): `pending` while no reviewed reader is registered (its reason kept), `refused` when the snapshots
    cannot be read or a later one rewrites an earlier interaction, `joined` (with the interaction count) when every
    later snapshot reproduces every earlier interaction. `joined` is a stability join, never admission of the take.
    Each record names its basis: it is computed on the unmasked retained originals, before the drive scan, which may
    mask session/ bytes afterwards (the open masking-provenance design; a re-join over published bytes refuses)."""
    readers = _registration.production_readers() if readers is None else readers
    try:
        facts = _vendor_provenance.session_history_facts(harness, Path(session_dir), list(refs), readers=readers)
        if harness == "gemini":
            _registration.gemini_snapshot_prefixes(Path(session_dir), list(refs))
    except _vendor_provenance.ProvenancePending as e:
        return {"status": "pending", "why": str(e), "interactions": None, "basis": NATIVE_HISTORY_BASIS}
    except _vendor_provenance.ProvenanceRefused as e:
        return {"status": "refused", "why": str(e), "interactions": None, "basis": NATIVE_HISTORY_BASIS}
    return {"status": "joined", "why": None, "interactions": len(facts), "basis": NATIVE_HISTORY_BASIS}


# ---- THE SUB-AGENT FILES (glitch-b5's Agent parity ruling, 16 Oct 2026, part 2 and R-A; review r10's F2) -----------
#   2.1.296 writes a sub-agent's own transcript to <projects>/<project>/<session id>/subagents/[<subdir>/]agent-<id>.jsonl
#   (a static read of the pinned binary), beside the session file, with agent-<id>.meta.json beside it (review r10's
#   survey of 20 real 2.1.267 and 2.1.280 sdk-cli files: 20 pairs). _take_records copies each pair before published()
#   deletes the config folder: the meta byte for byte, the jsonl byte for byte and then scrubbed as the transcript is
#   (scrub.scrub_text: session_context.userEmail removed, refused if anything else would change); the driver ledger
#   names each (file, agent id, sha256 of what was written, and for the jsonl its raw sha256 and what was removed);
#   record_kind scans both as transcripts. 2.1.296's own files are unseen, so the reader stays CLOSED, from the binary
#   and the survey:
#     agent-<id>.meta.json   exactly {agentType: str, description: str, requestNonInteractive: bool, requestShape:
#                            "foreground" or "background", spawnDepth: 1, toolUseId: str} (a nested sub-agent, depth 2,
#                            or any other key, such as model, holds)
#     agent-<id>.jsonl       every non-blank line one JSON object of type user, assistant or attachment, isSidechain
#                            true, agentId the file's id, sessionId the session's; an attachment admitted only under the
#                            main transcript view's own allow-list and closed shapes (transcript_view's reader); a raw
#                            U+2028, U+2029 or U+0085 is admitted (it can only sit inside a JSON string, and every
#                            reader here splits on newline alone), any other line separator is not
#   A file of any other shape, an unpaired file, any other file under subagents/, a symlink or a duplicate id HOLDS the
#   take or walk for a ruling (DriveRefused), so the first live Agent walk shows 2.1.296's shape.
SUBAGENTS_DIR = "subagents"
SUBAGENT_FILE = re.compile(r"agent-([A-Za-z0-9_-]{1,64})\.jsonl")
SUBAGENT_META = re.compile(r"agent-([A-Za-z0-9_-]{1,64})\.meta\.json")
SUBAGENT_RECORD_TYPES = ("user", "assistant", "attachment")
SUBAGENT_META_KEYS = ("agentType", "description", "requestNonInteractive", "requestShape", "spawnDepth", "toolUseId")
SUBAGENT_REQUEST_SHAPES = ("foreground", "background")
# review r11, R11-4: 2.1.296's meta writer spreads model, effort and name from the Agent call's input when it passes
# them; the checker binds each to the call. model is the input's alias (the schema's enum), effort one of the schema's
# effort values (Ia and bXo, read statically), name a string.
# review r12 NIT: the writer stores no effort for an input of lower or higher, so the meta admits only the levels it stores
SUBAGENT_META_OPTIONAL = {"model": ("sonnet", "opus", "haiku", "fable"),
                          "effort": ("low", "medium", "high", "xhigh", "max"), "name": None}
_REFUSED_SEPARATORS = ("\r", "\x0b", "\x0c", "\x1c", "\x1d", "\x1e")


def subagent_meta_problems(raw: bytes) -> list:
    """Why a sub-agent meta file is not of the closed shape (an empty list when it is)."""
    try:
        meta = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return ["it is not UTF-8 JSON"]
    if not isinstance(meta, dict) or not set(SUBAGENT_META_KEYS) <= set(meta) \
            or not set(meta) <= set(SUBAGENT_META_KEYS) | set(SUBAGENT_META_OPTIONAL):
        return [f"its keys are not {list(SUBAGENT_META_KEYS)} plus any of {list(SUBAGENT_META_OPTIONAL)}"]
    for k, allowed in SUBAGENT_META_OPTIONAL.items():
        if k in meta and not (type(meta[k]) is str and (allowed is None or meta[k] in allowed)):
            return [f"its {k} is not one the 2.1.296 Agent schema admits"]
    if not (type(meta["agentType"]) is str and type(meta["description"]) is str and type(meta["toolUseId"]) is str
            and type(meta["requestNonInteractive"]) is bool and meta["requestShape"] in SUBAGENT_REQUEST_SHAPES
            and type(meta["spawnDepth"]) is int and meta["spawnDepth"] == 1):
        return ["a value is not of its closed type (spawnDepth 1 only: a nested sub-agent is not read)"]
    return []


def subagent_shape_problems(text: str, agent_id: str, session_id: str) -> list:
    """Why a sub-agent jsonl is not of the shape this lane admits (an empty list when it is)."""
    import transcript_view as _tv
    out = []
    seps = sorted({f"U+{ord(s):04X}" for s in _REFUSED_SEPARATORS if s in text})
    if seps:
        out.append(f"line separator(s) {', '.join(seps)} other than newline")
    parser = _tv.ClaudeCodeSessionParser()
    for i, line in enumerate(text.split("\n"), 1):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            out.append(f"line {i} is not JSON")
            continue
        if not isinstance(rec, dict):
            out.append(f"line {i} is not an object")
        elif rec.get("type") not in SUBAGENT_RECORD_TYPES:
            out.append(f"line {i} is of type {str(rec.get('type'))[:40]!r}, not one of {list(SUBAGENT_RECORD_TYPES)}")
        elif rec.get("isSidechain") is not True or rec.get("agentId") != agent_id or rec.get("sessionId") != session_id:
            out.append(f"line {i} does not carry isSidechain true, the file's agentId and the session's id")
        elif rec["type"] == "attachment":
            try:
                parser._attachment(rec)
            except _tv.ViewError as e:
                out.append(f"line {i}: an attachment the transcript view does not admit ({str(e)[:80]})")
    return out


def copy_subagent_files(session_file: Path, session_id: str, folder: Path) -> list:
    """Copy each <session dir>/subagents/**/agent-<id>.jsonl and its agent-<id>.meta.json into folder/subagents/,
    keeping its path below subagents/: [{file, agent_id, sha256[, raw_sha256, removed]}] in path order. Anything else
    there, an unpaired or duplicate id, a symlink, or a file not of the admitted shape refuses (DriveRefused): the take
    or walk is held for a ruling, never graded."""
    base = Path(session_file).parent / session_id / SUBAGENTS_DIR
    if not base.exists():
        return []
    if base.is_symlink() or not base.is_dir():
        raise DriveRefused(f"{SUBAGENTS_DIR}/ beside the session file is not a folder")
    jsonl, meta = {}, {}
    for p in sorted(base.rglob("*")):
        rel = p.relative_to(base)
        if p.is_symlink():
            raise DriveRefused(f"{SUBAGENTS_DIR}/{rel.as_posix()} is a symlink: held for a ruling")
        if p.is_dir():
            continue
        m, mm = SUBAGENT_FILE.fullmatch(p.name), SUBAGENT_META.fullmatch(p.name)
        if not p.is_file() or (m is None and mm is None):
            raise DriveRefused(f"{SUBAGENTS_DIR}/{rel.as_posix()} is not a sub-agent file of the admitted shape "
                               f"(agent-<id>.jsonl, agent-<id>.meta.json): held for a ruling")
        table, agent = (jsonl, m.group(1)) if m else (meta, mm.group(1))
        if agent in table:
            raise DriveRefused(f"two sub-agent files carry agent id {agent}: held for a ruling")
        table[agent] = (p, rel)
    if set(jsonl) != set(meta):
        raise DriveRefused(f"sub-agent ids {sorted(set(jsonl) ^ set(meta))} have a jsonl or a meta file without the "
                           f"other: held for a ruling")
    out = []
    for agent in sorted(jsonl):
        mp, mrel = meta[agent]
        mraw = mp.read_bytes()
        bad = subagent_meta_problems(mraw)
        if bad:
            raise DriveRefused(f"{SUBAGENTS_DIR}/{mrel.as_posix()} is not of the admitted shape ({bad[0]}): held for a "
                               f"ruling (glitch-b5, 16 Oct 2026)")
        p, rel = jsonl[agent]
        raw = p.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            raise DriveRefused(f"{SUBAGENTS_DIR}/{rel.as_posix()} is not UTF-8: held for a ruling") from None
        bad = subagent_shape_problems(text, agent, session_id)
        if bad:
            raise DriveRefused(f"{SUBAGENTS_DIR}/{rel.as_posix()} is not of the admitted shape ({bad[0]}; {len(bad)} "
                               f"problem(s)): held for a ruling (glitch-b5, 16 Oct 2026)")
        try:
            body, removed = scrub_mod.scrub_text(text)      # scrubbed as the transcript is (Ruling 10)
        except SystemExit as e:
            raise DriveRefused(f"{SUBAGENTS_DIR}/{rel.as_posix()} could not be scrubbed ({e}): held for a ruling") from None
        written = body.encode("utf-8")
        for dest_rel, data in ((mrel, mraw), (rel, written)):
            dest = Path(folder) / SUBAGENTS_DIR / dest_rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(dest, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
            with os.fdopen(fd, "wb") as fh:
                fh.write(data)
        out.append({"file": f"{SUBAGENTS_DIR}/{mrel.as_posix()}", "agent_id": agent,
                    "sha256": hashlib.sha256(mraw).hexdigest()})
        out.append({"file": f"{SUBAGENTS_DIR}/{rel.as_posix()}", "agent_id": agent,
                    "sha256": hashlib.sha256(written).hexdigest(), "raw_sha256": hashlib.sha256(raw).hexdigest(),
                    "removed": list(removed)})
    return out


SESSION_STORE_RECORD = "session-store.json"
SESSION_STORE_LIST_MAX = 5000
READ_ONLY_ERRORS_RECORD = "read-only-errors.json"   # R15-2 (glitch-b5, 16 Oct 2026)
READ_ONLY_ERROR = re.compile(r"EROFS|Read-only file system")
READ_ONLY_ERRORS_MAX = 200


def vendor_nested_problems(listings, sweeps, harness: str, native_rel, commands, unread, run_tree=None) -> list:
    """W-3b on the vendor road (no checker reads a vendor take yet, so the driver judges it): every store listing
    holds only the take's own native session (check_take.vendor_store_violations), every sweep finds no session but
    it, and the turn streams' shell commands carry no session-off switch and move no store (check_take.
    command_problems). `unread` is kept for a caller's own refusals; the drive passes none (vendor_shell_commands)."""
    import check_take as _ct
    bad = [f"at {x['at']}: {v}" for x in listings
           for v in (["listing refused"] if "refused" in x else
                     _ct.vendor_store_violations(x["entries"], harness, native_rel))]
    own = {f"{_run_take.CONFIG_MOUNT}/{native_rel}"} if native_rel else set()
    bad += [f"the sweep at {x['at']}: {v}" for x in sweeps
            for v in (["sweep refused"] if "refused" in x else
                      _ct.sweep_violations(dict(x, files=[f for f in x["files"] if f[0] not in own]), set(), None,
                                           run_tree))]
    return bad + list(unread) + _ct.command_problems(commands, harness)


def store_listing(lister, root: str) -> list:
    """W-3b: [[path, kind], ...] for every entry under `root` (paths relative to the config folder), depth first in
    name order, through lister(rel_dir) -> [(name, kind)] or None (absent: []). A link is listed and never entered;
    more than SESSION_STORE_LIST_MAX entries refuses (ValueError)."""
    out = []

    def walk(rel):
        got = lister(rel)
        for item in sorted(got or []):
            if not (isinstance(item, (list, tuple)) and len(item) == 2 and all(isinstance(x, str) for x in item)):
                raise ValueError(f"the listing of {rel} is not (name, kind) pairs")
            name, kind = item
            path = f"{rel}/{name}"
            out.append([path, kind])
            if len(out) > SESSION_STORE_LIST_MAX:
                raise ValueError(f"the session store holds more than {SESSION_STORE_LIST_MAX} entries")
            if kind == "dir":
                walk(path)
    if not isinstance(root, str) or not root:
        raise ValueError("no session store is named for the harness")
    walk(root)
    return out


def host_lister(config_dir: str):
    """W-3b: the host's lister over the take's config folder after the restore: lister(rel_dir) -> [(name, kind)]
    (file, dir, link or other, by lstat; never followed) or None when rel_dir is absent or not a real folder."""
    import stat                               # inside: drive.py's round-3 prefix stays byte-identical (w6e)
    base = Path(config_dir)

    def lister(rel):
        p = base / rel
        if p.is_symlink() or not p.is_dir():
            return None
        out = []
        for q in sorted(p.iterdir()):
            st = os.lstat(q)
            kind = ("link" if stat.S_ISLNK(st.st_mode) else "dir" if stat.S_ISDIR(st.st_mode)
                    else "file" if stat.S_ISREG(st.st_mode) else "other")
            out.append((q.name, kind))
        return out
    return lister


def take_session_file(config_dir: str, session_id: str) -> str | None:
    """S6c C6: the session file Claude Code wrote for this id under the take's config folder (the container's
    CLAUDE_CONFIG_DIR): <config>/projects/*/<id>.jsonl, round 3's session_file rule (review 11, blocker 3: found by
    the imposed id, never by predicting the folder's name). More than one refuses; none is None."""
    base = Path(config_dir) / "projects"
    hits = sorted(base.glob(f"*/{session_id}.jsonl")) if base.is_dir() else []
    if len(hits) > 1:
        raise DriveRefused(f"{len(hits)} session files carry the id {session_id}")
    return str(hits[0]) if hits else None
OUTCOME_COMPLETE = "complete"
OUTCOME_STOPPED = "stopped \u2014 wait-point marker not held; graded as it stands"
OUTCOME_TIMED_OUT = "timed-out"
OUTCOME_PAUSE = "PAUSE \u2014 rate limited before the first agent turn"
OUTCOME_REHEARSAL = "REHEARSAL \u2014 no completed agent output before the turn ended"


class _Script:
    """C13: the take's operator script as the driver sends it, one line at a time, deciding the next line from the
    last reply's marker alone. Iterating yields the next line to send; read(turn) records the line's ledger row and
    decides what comes next (False: send nothing further). `done` is the step number completed by the last read
    (None while a recovery is pending), `pending` the next line (None when nothing more is sent)."""

    def __init__(self, steps, rows: list, *, strict: bool = False):
        self.steps = []
        for i, s in enumerate(list(steps), 1):
            if isinstance(s, str) and strict:         # W6J-R1-3: the production wiring hands steps, never bare lines
                raise DriveRefused(f"operator script entry {i} is a bare line; a strict script holds steps only")
            if isinstance(s, str):                    # a line with no wait point (S6's and S6b's synthetic scripts)
                s = {"n": i, "line": s}
            if not (isinstance(s, dict) and isinstance(s.get("n"), int) and isinstance(s.get("line"), str)
                    and (s.get("marker") is None or isinstance(s["marker"], str))
                    and (s.get("recovery") is None or (isinstance(s["recovery"], dict)
                                                      and isinstance(s["recovery"].get("if_reply_holds"), str)
                                                      and isinstance(s["recovery"].get("send"), str)))):
                raise DriveRefused(f"operator script entry {i} is not a step (n, line, marker?, recovery?)")
            self.steps.append(s)
        if [s["n"] for s in self.steps] != list(range(1, len(self.steps) + 1)):    # W6J-R1-3
            raise DriveRefused(f"the operator script's steps are numbered {[s['n'] for s in self.steps]}, not 1..k "
                               f"in order: an operator step could fire twice")
        self.rows, self.i, self.recoveries, self.said = rows, 0, 0, ""
        self.pending = self.steps[0]["line"] if self.steps else None
        self.sent, self.done, self.stopped, self.step_row = None, None, False, None

    def __iter__(self):
        return self

    def __next__(self) -> str:
        if self.pending is None:
            raise StopIteration
        self.sent, self.pending = self.pending, None
        return self.sent

    def read(self, turn) -> bool:
        step = self.steps[self.i]
        code = TIMED_OUT_EXIT if turn.end_reason == _adapter.END_TIMED_OUT else turn.exit_code
        row = {"n": step["n"], "sent": self.sent, "expects": step.get("marker"), "exit": code,
               "end": turn.end_reason, "then": None}
        if self.recoveries:
            row["recovery"] = True
        else:
            self.step_row, self.said = row, ""
        self.rows.append(row)
        self.done = None
        if turn.end_reason != _adapter.END_TURN:
            self.step_row["held"] = False
            return False
        self.said = turn.text if not self.recoveries else self.said + "\n" + turn.text
        held = marker_holds(step, self.said)
        rec = step.get("recovery")
        if not held and rec and self.recoveries < int(rec.get("at_most", 1)) and rec["if_reply_holds"] in turn.text:
            self.recoveries += 1
            self.pending = rec["send"]
            return True
        self.step_row["held"] = held
        if not held:
            self.stopped = True                       # no line past an unheld marker: graded as it stands
            return False
        self.done, self.i, self.recoveries = step["n"], self.i + 1, 0
        self.pending = self.steps[self.i]["line"] if self.i < len(self.steps) else None
        return True

    def then(self, op_id: str, *, failed: bool) -> None:
        """The operator step after the completed step, on that step's row (round 3's `then`)."""
        self.step_row["then"] = {"name": op_id, "failed": failed}

    def outcome(self, turns, *, finalize_abort: bool, wait_s, rate_limited: bool):
        """Round 3's ledger outcome (drive.py main(), check_take's driver_outcome_shapes)."""
        if not turns:
            return None
        last = turns[-1]
        if finalize_abort:
            return f"aborted \u2014 finalize did not write samples.csv within {wait_s} s"
        if last.end_reason == _adapter.END_TIMED_OUT:
            return OUTCOME_TIMED_OUT
        if last.end_reason != _adapter.END_TURN:
            if not any(t.agent_output for t in turns):
                return OUTCOME_PAUSE if rate_limited else OUTCOME_REHEARSAL
            which = "the recovery turn" if self.rows and self.rows[-1].get("recovery") else "a scripted turn"
            return f"aborted \u2014 {which} exited {last.exit_code}"
        if self.stopped:
            return OUTCOME_STOPPED
        return OUTCOME_COMPLETE if self.pending is None and self.i >= len(self.steps) else OUTCOME_STOPPED


def pause_evidence(rows: list) -> dict:
    """pause_adherence's evidence from the driver's ledger rows: each line sent with the marker it expected, and the
    host's end of its turn (graders/pause_adherence.py INPUTS: turns[].sent, turns[].expects, turn_ends)."""
    return {"turns": [{"sent": r["sent"], "expects": r["expects"]} for r in rows],
            "turn_ends": [r["end"] for r in rows]}


# ---- S6c: the production wiring (the Claude Code adapter, the take's own script, check4 as the checker) ---------
def script_from_design(design, project: str, source: str) -> list:
    """TakeDriver's script_for in production: the take's own wording's steps (check_take.design_view's script, from
    variants.operator_steps) with {project} and {source} rendered as check_take renders them, markers and
    recoveries kept, so the driver's lines are the ones check4 binds."""
    def render(line: str) -> str:
        return line.replace("{project}", project).replace("{source}", source)
    out = []
    for s in design.script:
        step = {"n": s["n"], "line": render(s["line"])}
        if s.get("marker") is not None:
            step["marker"] = s["marker"]
        if s.get("recovery"):
            step["recovery"] = dict(s["recovery"], send=render(s["recovery"]["send"]))
        out.append(step)
    return out


def login_file_of(login_file, take) -> str:
    """The take's login file: login_file(take) when it is per take (the Codex lease road: the take's placed
    cfg/auth.json, review MINOR 1 of 1f032586..27ade10a), else the one path given."""
    return login_file(take) if callable(login_file) else login_file


def claude_code_adapter_for(*, runtime, login_file: str, counters_for, pin_for, clock, caller_env=None):
    """TakeDriver's adapter_for in production: (row, take) -> claude_code_adapter.ClaudeCodeAdapter on the take's
    container and run tree, with the take's imposed session id, the row's model, its routing pin, the driver's stream
    path and counters_for(take) (run_take.counters of the take container's cgroup folder: CALLER_PENDING until the box
    measures it)."""
    def make(row, take):
        return _cc.ClaudeCodeAdapter(runtime=runtime, take_id=take.launched.take_id,
                                     run_tree=take.launched.spec.run_tree, login_file=login_file_of(login_file, take),
                                     session_id=take.identity["session_id"], model=row["model"], pin=pin_for(row),
                                     stream_path_for=lambda n, take=take: stream_path(take, n),
                                     counters_for=lambda take=take: counters_for(take), clock=clock,
                                     caller_env=caller_env)
    return make


def harness_adapter_for(*, runtime, login_file: str, counters_for, pin_for, clock,
                        rollout_for=None, caller_env=None, config_view=None, config_folder=None):
    """The three production adapters, with no default harness or invented evidence.

    Codex rollout_for(take, interaction_n) must retain and return the native
    rollout bytes through the box's measured retrieval road. Its absence refuses
    before a turn. This factory alone grants neither checker nor walk admission.
    """
    claude = claude_code_adapter_for(runtime=runtime, login_file=login_file,
                                     counters_for=counters_for, pin_for=pin_for,
                                     clock=clock, caller_env=caller_env)

    def make(row, take):
        harness = (row.get("agent") or {}).get("harness")
        if harness == "claude-code":
            return claude(row, take)
        if harness not in ("codex", "gemini"):
            raise AdapterIdentityRefused(f"no production adapter for harness {harness!r}")
        common = dict(runtime=runtime, take_id=take.launched.take_id,
                      run_tree=take.launched.spec.run_tree, login_file=login_file_of(login_file, take),
                      model=row["model"], pin=pin_for(row),
                      stream_path_for=lambda n: stream_path(take, n),
                      counters_for=lambda: counters_for(take), clock=clock, caller_env=caller_env,
                      # B11 (vendor-b11 R-CF): the take's config folder record (walk_driver binds the driver's)
                      config_folder=None)
        if callable(config_folder):
            common["config_folder"] = config_folder(take, common["login_file"] if harness == "codex" else None)
        if harness == "codex":
            if callable(rollout_for):
                return _codex.CodexAdapter(**common, rollout_for=lambda n: rollout_for(take, n))
            # Codex slice 3: by default the rollout is read where Codex writes it, in the take's config folder
            # (CODEX_HOME, box run_take TAKE_ENV[CODEX]), located by the adapter's own thread id; a read that cannot
            # locate exactly one rollout refuses the turn (an executed refusal), never a guess.
            made = {}

            def live_rollout(n):
                # Drive-wiring review MAJOR 1: read through the box (operator_list, operator_read) over the config
                # folder, never host-side; config_view is the driver's (walk_driver binds it).
                if not callable(config_view):
                    raise _native_snapshot.SnapshotRefused("no box road to read the rollout (config_view)")
                lister, reader = config_view(take)
                raw = reader(made["adapter"].native_session_rel(lister))
                if raw is None:
                    raise _native_snapshot.SnapshotRefused("the located rollout is absent")
                return raw.decode("utf-8")
            made["adapter"] = _codex.CodexAdapter(**common, rollout_for=live_rollout)
            return made["adapter"]
        return _gemini.GeminiAdapter(**common)
    return make


READERS_DISAGREE = "readers-disagree"


def take_checker(*, design_for, records="takes"):
    """TakeDriver's checker in production (S6c): check4 on the take's published transcript against its design view
    (design_for(row, take): check_take.design_view with the routing pin and the take's run tree; a constant still
    PENDING refuses: check_take.CHECKER_CONSTANTS carries ruled, sourced values since 15 Oct 2026, never a walk's). The streams and the session file disagreeing (C6), or no session
    file at all, adds round 3's readers-disagree: the two readers of one take do not agree, a rehearsal before the
    first agent turn and harness-error after it."""
    def checker(row, take, turns):
        import check_take as _ct
        if take.cross_check is None:              # review nit: None is a pending native cross-check, never agreement
            raise NativeCrossCheckPending("the checker was handed a take whose native cross-check is pending")
        ids = tuple(_routing.load_table()["checker_reasons_become_events"]["ids"])
        path = Path(take.folder) / "transcript.jsonl"
        if not path.is_file():
            return {"checker_reasons": [READERS_DISAGREE], "checker_events": dict.fromkeys(ids, 0)}
        design = design_for(row, take)
        entry, side = _ct.checker_for(design)     # T4 edit A: the harness's entry, refused before the take is read
        # BOOTSTRAP: the constants it read; glitch-b5's ruling 3: the nudges it carries; the Agent parity ruling,
        # part 6: its Agent calls (claude-code's side is exactly those three readers, as before edit A)
        take.checker_constants_sha256, take.no_output_nudges, take.agent_summary = side(path, design)
        got = entry(path, row, design, take=take, records=records)     # D1: records "walks" is the walk road
        reasons = list(got["reasons"])
        if take.cross_check and READERS_DISAGREE not in reasons:
            reasons.append(READERS_DISAGREE)
        return {"checker_reasons": reasons, "checker_events": dict(got["events"])}
    return checker


# =====================================================================================================================
# ROUND 4, WAVE 7 PIECE P2 (lane w7b; this file moved from lane w6j to lane w7b under glitch-1b's ruling W7B-gap4-1):
# the CP6 walk wiring, appended here, and one line edited in place in TakeDriver.drive (the adapter identity):
#   C6-strict  walk_driver() is the one road a walk or a take builds its driver by: WalkDriver, whose script is strict
#              (a bare operator line refuses) and whose strictness cannot be set False, neither by an argument (the
#              factory takes none) nor afterwards (the attribute refuses any value but True).
#   Q-w6i-1    the take folder is fixed: <root>/<mode_binding.TAKES_DIR>/<slot>/<k>, k the next unused attempt
#              number; mode_binding.py reads its takes from the same TAKES_DIR (one name, both readers).
#   W6B-R1-3   a take's records name the harness its row names, and the driver refuses (AdapterIdentityRefused, a
#              stop, never a rehearsal) an adapter whose own name is not that harness: a stub's persisted take carries
#              the stub's identity, never probes4's or claude-code's.
#   L-S6-1     one design view per take feeds both the lines sent (script_from_design) and the checker (take_checker),
#              each read with the take's own run tree.
# =====================================================================================================================

import mode_binding as _mode_binding  # noqa: E402

TAKES_DIR = _mode_binding.TAKES_DIR           # Q-w6i-1: named once, in mode_binding.py, and read by both
_SLOT = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


class AdapterIdentityRefused(DriveRefused):
    """W6B-R1-3: the adapter the driver was handed is not the harness the take's row names."""


def adapter_identity_problems(adapter, row: dict) -> None:
    """W6B-R1-3: the adapter's own `name` (agent_adapter's class attribute) must be the row's harness, so every record
    the take persists (the evidence ledger's take record, driver-ledger.json, the routing pin) names the identity that
    actually ran. An adapter without a name refuses as well."""
    want = (row.get("agent") or {}).get("harness")
    got = getattr(adapter, "name", None)
    if not isinstance(got, str) or got != want:
        raise AdapterIdentityRefused(f"the take's row names harness {want!r} and its adapter is {got!r}; a take's "
                                     f"records carry the identity that ran, never another's")


def take_folder_in(root):
    """Q-w6i-1: TakeDriver's take_folder in production: (row) -> <root>/takes/<slot>/<k>, k = 1 + the attempts the
    slot already holds (a new folder each launch; launch() refuses one that exists). The slot is one path segment."""
    base = Path(root).resolve() / TAKES_DIR

    def take_folder(row: dict) -> str:
        slot = row.get("slot")
        if not isinstance(slot, str) or not _SLOT.fullmatch(slot):
            raise DriveRefused(f"the row's slot {slot!r} is not one path segment")
        folder = base / slot
        used = [int(p.name) for p in folder.iterdir() if p.name.isdigit()] if folder.is_dir() else []
        return str(folder / str(max(used, default=0) + 1))
    return take_folder


# W8D-R1-3 (fold W8D-close-1): the production class, captured when this module is imported, so a later patch of
# claude_code_adapter.ClaudeCodeAdapter admits nothing; its module is checked too (a class captured under a patch is
# another module's). Not seen here (walk_register's limits, W8D-R1-4, W8D-R2-2): an object whose __class__ is
# reassigned to this class, or a fake whose __module__ is "claude_code_adapter" captured because drive.py was imported
# or reloaded while ClaudeCodeAdapter was patched.
PRODUCTION_ADAPTER = _cc.ClaudeCodeAdapter
PRODUCTION_ADAPTER_MODULE = "claude_code_adapter"
import codex_adapter as _codex  # noqa: E402
import gemini_adapter as _gemini  # noqa: E402

PRODUCTION_ADAPTERS = {
    "claude-code": (PRODUCTION_ADAPTER, PRODUCTION_ADAPTER_MODULE),
    "codex": (_codex.CodexAdapter, "codex_adapter"),
    "gemini": (_gemini.GeminiAdapter, "gemini_adapter"),
}


def scan_read_shapes(row) -> tuple:
    """Piece B17 (glitch-26's ruling B17-5, 19 Oct 2026): the read shapes OD57's admission uses in this row's scan,
    its arm's (routing.PAID_HARNESSES binds the arm to its harness, whose adapter holds them); () for any other arm,
    a row without one, or a row whose declared harness is not its arm's, so the scan admits what it did before B17."""
    arm = row.get("arm") if isinstance(row, dict) else None
    agent = row.get("agent") if isinstance(row, dict) else None
    for harness, module in (("codex", _codex), ("gemini", _gemini)):
        if _routing.PAID_HARNESSES[harness]["arm"] == arm:
            declared = agent.get("harness") if isinstance(agent, dict) else harness
            return module.READ_SHAPES if declared == harness else ()
    return ()


def adapter_class_problems(adapter) -> None:
    """The adapter is its harness's captured production class, never a stub or subclass."""
    expected = PRODUCTION_ADAPTERS.get(getattr(adapter, "name", None))
    if expected is None or type(adapter) is not expected[0] or type(adapter).__module__ != expected[1]:
        raise AdapterIdentityRefused(f"the walk driver built an adapter of class {type(adapter).__module__}."
                                     f"{type(adapter).__qualname__}; the declared harness requires its exact "
                                     f"production adapter class, whatever name an object declares")


def take_k_problems(records_root, row: dict, attempt, take) -> None:
    """W7B-R1-5 (lane w8d, ruling W8D-gap4-1): the take folder's k is Batch's attempt. TakeRepo.commit_records(row,
    attempt) receives the attempt Batch registered; the folder take_folder_in made counts the folders on disk, which
    drift from it when a launch is refused before its folder exists. So the records are handed over only from
    <records_root>/takes/<slot>/<attempt>, exactly; any other folder refuses (DriveRefused), never a commit under the
    wrong attempt."""
    want = Path(records_root) / TAKES_DIR / str(row.get("slot")) / str(attempt)
    if Path(take.folder) != want:
        raise DriveRefused(f"the take's records are in {take.folder}, and Batch commits them as attempt {attempt} of "
                           f"slot {row.get('slot')!r}, whose folder is {want}; a take folder's k is its attempt")


class WalkDriver(TakeDriver):
    """C6-strict (W6J-close-1's CP6 checklist item): the production driver. Its script is strict by construction: the
    production script (script_from_design) hands steps with their markers, and a bare line is refused, never sent.

    W8D (lane w8d, ruling W8D-gap4-1): records_root (required) is the study folder walk_driver was given; a take's
    records are handed to TakeRepo only from <records_root>/takes/<slot>/<attempt> (W7B-R1-5), and every adapter it
    makes is checked to be exactly the production class (W7B-R1-4), however adapter_for is set."""

    def __init__(self, *, records_root=None, records=None, **kw):
        if "strict_script" in kw:
            raise TypeError("the walk driver's script is strict by construction; it takes no strict_script")
        if records_root is None:
            raise TypeError("the walk driver takes records_root, the study folder its take folders sit under")
        if records not in RECORD_FOLDERS:        # W9 K1-launch: the records its launch is checked against
            raise TypeError("the walk driver takes records, 'takes' or 'walks' (what its launch is checked against)")
        self.records_root = Path(records_root).resolve()
        self.records = records
        super().__init__(strict_script=True, **kw)

    def launch(self, row: dict) -> str:
        folder = launch_problems(self, row)          # W9 K1-launch (Q-w8d-1): before any folder, container or spend
        return super().launch(row, _folder=folder)   # ruling w9-Q1: a take's folder is its registered attempt

    @property
    def adapter_for(self):
        made = self._adapter_for

        def checked(row, take):
            adapter = made(row, take)
            adapter_class_problems(adapter)          # W7B-R1-4
            return adapter
        return checked

    @adapter_for.setter
    def adapter_for(self, fn) -> None:
        self._adapter_for = fn

    def record_files(self, row: dict, attempt: int) -> list:
        with self._lock:
            take = self._by_slot.get(row["slot"])
        if take is not None:
            take_k_problems(self.records_root, row, attempt, take)    # W7B-R1-5
        return super().record_files(row, attempt)

    @property
    def strict_script(self) -> bool:
        return True

    @strict_script.setter
    def strict_script(self, value) -> None:
        if value is not True:
            raise DriveRefused("the walk driver's script is strict; it is never relaxed")


def walk_driver(*, runtime, root, config_parent, spec_for, sidecar_for, proxy, lock_path, hosts, login_file,
                counters_for, pin_for, design_for, project_for, identity_for, secrets, rules_scanner, uid_map,
                budget_s, finalize_wait_s, poll_s, clock, sleep, holdout_matcher=None, caller_env=None,
                records="takes", rollout_for=None, ownership=None, settings_guard=None,
                machine_gate=None) -> WalkDriver:
    """The CP6 production wiring (cp6-readiness row 3): batch's driver for a walk or a take of any of the three
    harnesses (registration review finding 2, glitch-06, 14 Oct 2026: harness_adapter_for, so a Gemini walk, and a
    Codex walk once its rollout_for road exists, runs on the same road; WalkDriver still admits only each harness's
    exact production class).

    design_for  (row, run_tree) -> check_take.design_view(row, pin=pin_for(row), run_tree=run_tree, constants=...):
                the script is read with run_tree None (its lines carry {project} and {source}, rendered here from the
                take's identity), the checker with the take's own run tree (TakeSpec.run_tree)
    root        the study folder the take records are committed under (take_folder_in)
    records     W8A: "takes" (the default: takes/<slot>/<k>, take_folder_in) or "walks" (rehearsals/<walk>/,
                walk_folder_in, the row's `walk` id); any other value refuses (record_folder_in)
    rollout_for Codex's native rollout retrieval (harness_adapter_for): None refuses a Codex walk before a turn
    Everything else is TakeDriver's (its docstring) or harness_adapter_for's. The checker constants stay the
    caller's: design_for hands them to design_view (check_take.CHECKER_CONSTANTS, ruled from their sources on 15 Oct
    2026, not measured by a walk), and check4 refuses while any is PENDING."""
    if not callable(design_for):
        raise TypeError("design_for must be callable")
    if Path(root).resolve() != Path(_mode_binding.HERE).resolve():    # W7B-R1-2: the root the gate reads
        raise DriveRefused(f"the take records' root {str(root)!r} is not the study folder mode_binding reads "
                           f"({_mode_binding.HERE}); takes written anywhere else leave its --check grading nothing")

    def script_for(row):
        ident = identity_for(row)
        return script_from_design(design_for(row, None), project_for(row), ident["source"])

    bound: dict = {}                    # review MAJOR 1: the Codex rollout is read through the driver's config view
    driver = WalkDriver(
        records_root=root, records=records, runtime=runtime, take_folder=record_folder_in(root, records), config_parent=config_parent, spec_for=spec_for,
        sidecar_for=sidecar_for, proxy=proxy, lock_path=lock_path, hosts=hosts,
        adapter_for=harness_adapter_for(runtime=runtime, login_file=login_file, counters_for=counters_for,
                                        pin_for=pin_for, clock=clock, rollout_for=rollout_for, caller_env=caller_env,
                                        config_view=lambda take: bound["driver"].config_view(take),
                                        config_folder=lambda take, lease: bound["driver"].config_folder(take, lease)),
        script_for=script_for, pin_for=pin_for,
        checker=take_checker(design_for=lambda row, take: design_for(row, take.launched.spec.run_tree),
                             records=records),
        secrets=secrets, rules_scanner=rules_scanner, holdout_matcher=holdout_matcher, uid_map=uid_map,
        budget_s=budget_s, finalize_wait_s=finalize_wait_s, poll_s=poll_s, clock=clock, sleep=sleep,
        project_for=project_for, identity_for=identity_for, caller_env=caller_env, ownership=ownership,
        settings_guard=settings_guard, machine_gate=machine_gate)
    bound["driver"] = driver
    return driver


# =====================================================================================================================
# ROUND 4, THE WALK LAYOUT (lane w8a; this file moved from lane w7b to lane w8a under glitch-1b's ruling W8A-gap4-1,
# from ruling W8-layout-1: Option A of walk-layout-options-2026-10-12). Appended here, above `if __name__`, with two
# small edits in place: take_files reads its kinds through record_kind, and walk_driver takes `records`.
#   L2  one walk is one folder, rehearsals/<walk>/ (mode_binding.WALKS_DIR): walk_driver(records="walks") launches
#       into it (walk_folder_in; the row's `walk` id, one path segment, a folder that exists refused);
#       records="takes" keeps takes/<slot>/<k>; any other value refuses.
#   L4  WalkRepo commits ONE walk: its folder's records (walk_files: a take folder's closed map plus grade.json,
#       driver-ledger.json and grade.json required) and its new rehearsals/register.json entry, in one commit,
#       through the same scan (box/scan_record), re-stage, tree binding and blob check as TakeRepo's commit step.
#   L3  WalkRepo refuses once prereg.json exists: walks are pre-freeze, takes post-freeze (TakeRepo.register refuses
#       before the freeze through takes.commit_registration), so the two never overlap in time.
#   L1  round 3's host road (main --walk and route_attempt, which wrote walks/, transcripts/, pauses/ and
#       rehearsals/<task>/<half>/<model>/row-<n>) is shadowed below by refusals naming the walk runner; its bytes stay
#       above, untouched and unreachable (ROUND3_ONLY holds the originals so a test can name them).
# =====================================================================================================================

WALKS_DIR = _mode_binding.WALKS_DIR           # W8A: named once, in mode_binding.py
WALK_GRADE = _mode_binding.WALK_GRADE
# grade.json's scan kind: a machine record the driver side writes, scanned as the ledgers are (w4c's KINDS; whether
# it deserves a kind of its own is w4c's call, named in lane-reports/w8a-walk-layout.md).
WALK_CHECK = "check.json"     # W10 (D1): the walk's checker reading and its route, beside grade.json
WALK_REGRADE = "regrade.json"  # live harness (finding 2): a pending walk's superseding regrade, a later commit's only file
WALK_FILE_KINDS = {WALK_GRADE: "ledger", WALK_CHECK: "ledger", WALK_REGRADE: "ledger"}
# The scheduled-wakeup ruling (glitch-6b, 15 Oct 2026): a walk's rechecks, recheck-<n>.json (walk_regrade.py), each a
# later commit's only file, scanned as the ledgers are.
WALK_RECHECK = re.compile(r"recheck-[1-9][0-9]*\.json")
WALK_REQUIRED = (WALK_GRADE, WALK_CHECK)
WALK_PRE_TURN = (PREFLIGHT_RECORD, REFUSAL_RECORD)
WALK_TRANSCRIPT = "transcript.jsonl"          # W10-R2-3: with a turn record, the sign that a turn ran    # W10 (D3): what says why a walk died before its driver ledger
WALK_SUBJECT = "Commit one walk; never counted"
WALK_REGISTER_KIND = "ledger"
FROZEN_NAME = prereg.FROZEN.name               # prereg.json: once it exists, no walk is committed


def record_kind(rel: list, extra: dict | None = None) -> str:
    """The scan kind of a record file at `rel` (its path parts inside the record folder), by the closed map: a take
    folder's files (TAKE_FILE_KINDS, turn-N.jsonl, turn-N.jsonl.launch.json), evidence/** and session/**, plus `extra` top-level names (a walk
    folder's grade.json). Anything else refuses: nothing rides a commit unscanned under a guessed kind."""
    name = rel[-1]
    if len(rel) == 1 and extra and name in extra:
        return extra[name]
    if len(rel) == 1 and (name in TAKE_FILE_KINDS or STREAM_NAME.fullmatch(name)):
        return TAKE_FILE_KINDS.get(name, "stream")
    if len(rel) == 1 and LAUNCH_JOURNAL_NAME.fullmatch(name):
        return "launch"
    if rel[0] == EVIDENCE_DIR and len(rel) >= 2:
        return EVIDENCE_KINDS.get(rel[1], "evidence") if len(rel) > 2 else "evidence"
    if rel[0] == SESSION_DIR and len(rel) >= 2:
        return "session"
    if rel[0] == SUBAGENTS_DIR and len(rel) >= 2 and (SUBAGENT_FILE.fullmatch(name) or SUBAGENT_META.fullmatch(name)):
        return "transcript"                       # Agent parity: a sub-agent's records and its meta, scanned as text
    raise DriveRefused(f"{'/'.join(rel)} in the take folder has no scan kind")


def walk_files(folder) -> list:
    """W8A: every file of a walk folder, (absolute path, scan kind): a take folder's closed map plus grade.json. A file
    outside the map, a symlink, or a folder without driver-ledger.json and grade.json refuses (DriveRefused)."""
    folder = os.path.abspath(os.fspath(folder))
    if os.path.islink(folder) or not os.path.isdir(folder):
        raise DriveRefused(f"{folder} is not a walk folder")
    out = []
    for base, dirs, files in os.walk(folder, followlinks=False):
        dirs.sort()
        for name in sorted(files) + sorted(d for d in dirs if os.path.islink(os.path.join(base, d))):
            path = os.path.join(base, name)
            rel = os.path.relpath(path, folder).split(os.sep)
            if os.path.islink(path) or not os.path.isfile(path):
                raise DriveRefused(f"{'/'.join(rel)} in the walk folder is not a regular file")
            out.append((path, "ledger" if len(rel) == 1 and WALK_RECHECK.fullmatch(name)
                        else record_kind(rel, WALK_FILE_KINDS)))
    tops = {os.path.relpath(p, folder) for p, _ in out}
    missing = [n for n in WALK_REQUIRED if n not in tops]
    if LEDGER_FILE not in tops and not (tops & set(WALK_PRE_TURN)):
        missing.insert(0, f"{LEDGER_FILE} (nor, for a walk that died before turn 1, {' or '.join(WALK_PRE_TURN)})")
    ran = sorted(n for n in tops if n == WALK_TRANSCRIPT or STREAM_NAME.fullmatch(n)
                 or LAUNCH_JOURNAL_NAME.fullmatch(n))     # live harness 3a (glitch-06): a launch journal is a turn launched
    if LEDGER_FILE not in tops and ran:                  # W10-R2-3: a turn ran, so the driver wrote its ledger
        raise DriveRefused(f"the walk folder holds {', '.join(ran)} and no {LEDGER_FILE}: a walk whose agent turn ran "
                           f"is committed with its driver ledger; only a walk with no transcript and no turn record "
                           f"died before turn 1")
    if missing:
        raise DriveRefused(f"the walk folder holds no {', '.join(missing)}; a walk is committed with its driver ledger "
                           f"(or the record of why it died before turn 1), its checker reading and its grade (or why "
                           f"it was not graded)")
    return out


def walk_folder_in(root):
    """L2: the walk's record folder, (row) -> <root>/rehearsals/<row's walk id>, one walk per folder. The walk id is
    one path segment (walk_register's shape); a folder that already exists is refused (a retry is a new walk id)."""
    import walk_register as _walk_register
    base = Path(root).resolve() / WALKS_DIR

    def walk_folder(row: dict) -> str:
        walk = row.get("walk")
        if not isinstance(walk, str) or not _walk_register.WALK_ID.fullmatch(walk):
            raise DriveRefused(f"the row's walk id {walk!r} is not one path segment")
        folder = base / walk
        if os.path.lexists(folder):
            raise DriveRefused(f"{WALKS_DIR}/{walk}/ already exists; a walk is never driven twice into one folder")
        return str(folder)
    return walk_folder


RECORD_FOLDERS = {"takes": take_folder_in, "walks": walk_folder_in}


def record_folder_in(root, records):
    """L2: the driver's record folder by kind of record: "takes" (takes/<slot>/<k>) or "walks" (rehearsals/<walk>/)."""
    if records not in RECORD_FOLDERS:
        raise DriveRefused(f"records {records!r} is neither 'takes' nor 'walks'")
    return RECORD_FOLDERS[records](root)


class WalkRepo(TakeRepo):
    """L3, L4: the walk's repo. commit_walk(entry) makes ONE commit holding rehearsals/<walk>/** and the walk's new
    register.json entry, refused once prereg.json exists. A walk is never registered or committed as a take:
    register() and commit_records() refuse here.

    runtime, secrets, rules_scanner, holdout_matcher, root, repo, caller_env   as TakeRepo's
    design   walk_register.design_in_force()'s shape (None reads root's prereg-draft.json and tasks/)
    """

    def __init__(self, *, runtime, secrets, rules_scanner, holdout_matcher=None, root=HERE, repo=REPO,
                 caller_env=None, design=None):
        super().__init__(runtime=runtime, record_files=self._walk_record_files, secrets=secrets,
                         rules_scanner=rules_scanner, holdout_matcher=holdout_matcher, root=root, repo=repo,
                         caller_env=caller_env)
        self.design, self._walk_folder = design, None

    def register(self, row: dict, attempt: int) -> str:
        raise CommitRefused("a walk is never registered as a take; WalkRepo commits walks only (commit_walk)")

    def commit_records(self, row: dict, attempt: int, outcome: dict) -> dict:
        raise CommitRefused("a walk is never committed as a take; WalkRepo commits walks only (commit_walk)")

    def _walk_record_files(self, row, attempt) -> list:
        return walk_files(self._walk_folder)

    def refuse_after_freeze(self) -> None:
        """L3: walks are pre-freeze (plan CP6); once prereg.json exists only TakeRepo commits records. Read on disk
        here, and again in the commit at HEAD and in the tree being written (W8A-R1-1: a committed freeze deleted on
        disk is still a freeze)."""
        if os.path.lexists(self.root / FROZEN_NAME):
            raise CommitRefused(f"{FROZEN_NAME} exists: the design is frozen, and walks run before the freeze (plan "
                                f"CP6); after it only the graded takes are committed")

    def _holds_freeze(self, rev: str) -> bool:
        """W8A-R1-1: whether commit or tree `rev` holds this study's prereg.json (git cat-file -e, exit 0)."""
        rel = (self.root / FROZEN_NAME).relative_to(self.repo).as_posix()
        got = subprocess.run(["git", "-C", str(self.repo), "cat-file", "-e", f"{rev}:{rel}"], capture_output=True)
        return got.returncode == 0

    def _refuse_ever_frozen(self, head: str) -> None:
        """W8A-R2-1: un-freezing is never legitimate (prereg.py's docstring), so a walk is refused when any commit in
        HEAD's history ever held this study's prereg.json, even one removed since. A history git cannot read refuses."""
        rel = (self.root / FROZEN_NAME).relative_to(self.repo).as_posix()
        got = subprocess.run(["git", "-C", str(self.repo), "log", "-1", "--format=%H", head, "--", rel],
                             capture_output=True, text=True)
        if got.returncode != 0 or got.stdout.strip():
            raise CommitRefused(f"{FROZEN_NAME} is in this branch's history: the design was frozen, and walks run "
                                f"before the freeze (plan CP6); a freeze removed later is still a freeze")

    def _refuse_frozen_at(self, rev: str, where: str) -> None:
        if self._holds_freeze(rev):
            raise CommitRefused(f"{FROZEN_NAME} is in {where}: the design is frozen, and walks run before the freeze "
                                f"(plan CP6); a freeze deleted on disk is still committed")

    def _register_path(self) -> Path:
        import walk_register as _walk_register
        return self.root / WALKS_DIR / _walk_register.REGISTER_NAME

    def commit_walk(self, entry: dict) -> dict:
        """One walk's commit. On any refusal the register goes back to HEAD's bytes and every name this call staged is
        unstaged (TakeRepo's R4-7 rule); the walk's own files stay, masked where the scan masked them."""
        self._touched = []
        try:
            return self._commit_walk(entry)
        except BaseException as refused:
            try:
                self._restore_register()
            except Exception as e:  # noqa: BLE001 - the restore's own failure is named beside the refusal
                raise CommitRefused(f"the walk's commit was refused ({type(refused).__name__}: {refused}), and the "
                                    f"register could not be restored to HEAD: {type(e).__name__}: {e}") from refused
            raise

    def _commit_walk(self, entry: dict) -> dict:
        import walk_register as _walk_register
        self.refuse_after_freeze()
        design = _walk_register.design_in_force(self.root) if self.design is None else self.design
        bad = _walk_register.entry_problems(0, entry, design)
        if bad:
            raise CommitRefused("the walk's register entry is refused: " + "; ".join(bad))
        register = self._register_path()
        reg_rel = register.relative_to(self.repo).as_posix()
        if not _git_bytes(self.repo, "ls-tree", "--name-only", "HEAD", "--", reg_rel).strip():
            raise CommitRefused(f"{reg_rel} is not tracked at HEAD; the register is committed before any walk")
        try:
            doc = json.loads(_git_bytes(self.repo, "show", f"HEAD:{reg_rel}"),
                             object_pairs_hook=_walk_register.no_duplicate_keys)
        except ValueError as e:
            raise CommitRefused(f"{reg_rel} at HEAD is not a register: {e}") from None
        if not isinstance(doc, dict) or set(doc) != set(_walk_register.top_keys(doc.get("schema"))) \
                or not isinstance(doc["walks"], list):      # schema 2 (the recheck-coverage ruling) adds rechecks
            raise CommitRefused(f"{reg_rel} at HEAD is not {{schema, walks: [...]}} (and rechecks, at schema 2)")
        if any(isinstance(e, dict) and isinstance(e.get("walk"), str)
               and e["walk"].casefold() == entry["walk"].casefold() for e in doc["walks"]):
            raise CommitRefused(f"walk {entry['walk']!r} is already registered; a retry is a new walk id")
        self._walk_folder = self.root / WALKS_DIR / entry["walk"]
        try:
            files = self._take_files(entry, 0, self._reserved() | {reg_rel})
        except DriveRefused as e:
            raise CommitRefused(f"the walk folder is refused: {e}") from None
        takes_mod.require_commit_identity(self.repo)
        register.write_text(json.dumps(dict(doc, walks=doc["walks"] + [entry]), indent=2) + "\n",
                            encoding="utf-8")                # every other key (schema, rechecks) as HEAD has it
        # The register and the folder, as they will be committed, must pass the register's own check, content rule
        # included: a commit the gate would refuse is never made.
        problems, _ = _walk_register.check(register.parent, design)
        problems += _walk_register.content_problems(register.parent, [entry["walk"]])
        if problems:
            raise CommitRefused("walk_register --check would refuse this walk: " + "; ".join(problems))
        declared = {name: kind for name, (_, kind) in files.items()}
        declared[reg_rel] = WALK_REGISTER_KIND
        paths = {name: path for name, (path, _) in files.items()}
        paths[reg_rel] = str(register)
        self._touched = sorted(declared)
        _git_bytes(self.repo, "add", "--", *sorted(declared))
        staged = self._staged_exactly(declared)
        scan = _scan_record.scan([(paths[n], declared[n]) for n in staged], list(self.secrets()),
                                 read_shapes=scan_read_shapes(entry),
                                 rules_scanner=self.rules_scanner, holdout_matcher=self.holdout_matcher)
        if not _scan_record.passed(scan):
            why = "; ".join(f"{r['path']}:{r['line']} ({r['kind']}): {r['why']}" for r in scan["refused"])
            raise CommitRefused(f"the commit scan refused the walk: {why}")
        _git_bytes(self.repo, "add", "--", *staged)          # the scan masked on disk: stage the masked bytes
        staged = self._staged_exactly(declared)
        head = _git_bytes(self.repo, "rev-parse", "--verify", "HEAD").decode().strip()
        self._refuse_frozen_at(head, "the commit the walk would follow")          # W8A-R1-1: HEAD
        self._refuse_ever_frozen(head)                                            # W8A-R2-1: any ancestor
        tree = _git_bytes(self.repo, "write-tree").decode().strip()
        self._refuse_frozen_at(tree, "the tree the walk's commit would hold")     # W8A-R1-1: the written tree
        changed = sorted(n.decode("utf-8") for n in _git_bytes(
            self.repo, "diff-tree", "-r", "--name-only", "--no-renames", "-z", head, tree).split(b"\0") if n)
        if sorted(declared) != changed:
            raise CommitRefused(f"the written tree changes {changed}, not the walk's declared files")
        after = {rec["path"]: rec["sha256_after"] for rec in scan["files"]}
        for name in staged:
            blob = _git_bytes(self.repo, "cat-file", "blob", f"{tree}:{name}")
            if after.get(paths[name]) != hashlib.sha256(blob).hexdigest():
                raise CommitRefused(f"the staged blob of {name} is not the bytes the scan left (sha256_after)")
        self._before_commit()
        walk_commit = self._bind(head, tree)
        return {"commit": walk_commit, "masked": scan["masked"], "events": scan["events"], "holdout": scan["holdout"]}

    def _bind(self, head: str, tree: str) -> str:
        """The commit of exactly `tree` on `head`, under the walk's own subject; HEAD moves only if it still is `head`."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt") as message:
            message.write(WALK_SUBJECT + "\n")
            message.flush()
            new = _git_bytes(self.repo, "commit-tree", tree, "-p", head, "-F", message.name).decode().strip()
        _git_bytes(self.repo, "update-ref", "-m", WALK_SUBJECT, "HEAD", new, head)
        return new

    def _restore_register(self) -> None:
        register = self._register_path()
        rel = register.relative_to(self.repo).as_posix()
        if _git_bytes(self.repo, "ls-tree", "--name-only", "HEAD", "--", rel).strip():
            register.write_bytes(_git_bytes(self.repo, "show", f"HEAD:{rel}"))
        staged = set(_staged_names(self.repo))
        names = [n for n in self._touched if n in staged]
        if names:
            _git_bytes(self.repo, "reset", "-q", "--", *names)


# L1: round 3's host road, kept byte for byte above and shadowed here. Nothing in round 4 calls it: the CLI and every
# caller of these names reach the refusals below; the originals stay reachable only through ROUND3_ONLY, by name.
ROUND3_ONLY = {"main": main, "route_attempt": route_attempt}
ROUND3_RETIRED = ("round 3's host road (drive.py --walk, --row) is retired in round 4: a walk runs through "
                  "walk_driver(records='walks') into rehearsals/<walk>/ and is committed by WalkRepo; a take runs "
                  "through batch.Batch with walk_driver and TakeRepo")


def route_attempt(*args, **kwargs):  # noqa: F811 - L1: round 3's router, retired
    raise DriveRefused(ROUND3_RETIRED)


def main() -> int:  # noqa: F811 - L1: round 3's CLI, retired
    print(f"refused: {ROUND3_RETIRED}", file=sys.stderr)
    return 2


# =====================================================================================================================
# ROUND 4, CP6 WIRING (lane w9-cp6; this file moved from lane w8d-cp8-prep to lane w9-cp6 under glitch-2f's wave 9
# ruling, the Lane-orchestrator under Javier's standing delegation, Mon 12 Oct 2026). Appended above `if __name__`;
# the in-place edits are WalkDriver's records argument and launch override, and walk_driver passing records.
#   K1-launch  Q-w8d-1: K1 (take_k_problems) refuses a drifted k at the commit, which comes after the take ran and
#              was paid for. So WalkDriver.launch first calls launch_problems, and a refusal (LaunchRefused, a
#              DriveRefused) comes before any take folder, config folder or container exists: nothing is spent.
#              What the launch is checked against is what the records bind, field by named field:
#                takes  the slot's ONE open registration in the committed takes.json (a registered row with no
#                       committed outcome, read with takes.load_rows and takes.read_history): every field of
#                       LAUNCH_FIELDS (the allow-list) present in both and equal; the row the frozen
#                       pre-registration's planned row (takes.require_planned_row, every key of it bound); and the
#                       take folder <root>/takes/<slot>/<that registration's attempt> not yet existing (ruling w9-Q1:
#                       launch makes exactly that folder).
#                walks  no freeze (prereg.json absent: walks are pre-freeze, as WalkRepo refuses at the commit);
#                       WALK_LAUNCH_FIELDS read as a register entry the design in force accepts
#                       (walk_register.entry_problems on prereg-draft.json and tasks/); its id not in register.json.
#   w9-Q1      ruling w9-Q1 (glitch-2f, Mon 12 Oct 2026; reverses Q-w6i-1 because the facts changed): a take's folder
#              is <root>/takes/<slot>/<the open registration's attempt>, refused by name when it already exists; it is
#              never a count of the folders on disk. A launch is now refused before its folder exists, so a count would
#              give attempt - 1 for ever after and strand the slot. take_folder_in (the count) still names a WalkDriver's
#              take_folder for other readers, but WalkDriver.launch never reads it for a take; K1 at the commit
#              (take_k_problems) stays as the second guard.
# =====================================================================================================================

import stats as _stats  # noqa: E402

LAUNCH_FIELDS = tuple(_stats.TAKE_FIELDS[:8]) + ("slot", "half_cell")
WALK_LAUNCH_FIELDS = ("walk", "task", "half", "wording", "arm", "model")
WALK_LAUNCH_REASON = "pre-launch check"     # a stand-in reason: the entry's reason is written at the commit


class LaunchRefused(DriveRefused):
    """K1-launch (Q-w8d-1): the take does not match its records, refused before launch (nothing created or spent)."""


def records_repo(root: Path) -> Path:
    """The git repository the study folder sits in (REPO in production), read from git itself."""
    got = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if got.returncode != 0 or not got.stdout.strip():
        raise LaunchRefused(f"the take records' root {root} is in no git repository, so its committed registrations "
                            f"cannot be read; nothing was launched")
    return Path(got.stdout.strip()).resolve()


def open_registration(root: Path, repo: Path, slot) -> dict:
    """The slot's one registration in the committed takes.json that has no committed outcome yet."""
    try:
        rows = takes_mod.load_rows(root=root, repo=repo)
        history = takes_mod.read_history(root=root, repo=repo)
    except (ValueError, KeyError, OSError) as e:
        raise LaunchRefused(f"the committed registrations cannot be read ({type(e).__name__}: {e}); nothing was "
                            f"launched") from None
    done = {(o.get("slot"), o.get("attempt")) for o in history if takes_mod.batch.is_outcome(o)}
    mine = [r for r in rows if r.get("slot") == slot]
    open_ = [r for r in mine if (slot, r.get("attempt")) not in done]
    if len(open_) != 1:
        raise LaunchRefused(f"slot {slot!r} has {len(open_)} open registrations in takes.json (registered, no "
                            f"committed outcome); a take launches only under its slot's one open registration")
    reg = open_[0]
    if reg.get("attempt") != max(r.get("attempt") for r in mine):
        raise LaunchRefused(f"slot {slot!r}'s open registration is attempt {reg.get('attempt')!r}, not its latest; "
                            f"a take launches only under the attempt Batch registered last")
    return reg


def take_launch_problems(driver, row: dict) -> str:
    root = driver.records_root
    slot = row.get("slot")
    reg = open_registration(root, records_repo(root), slot)
    attempt = reg["attempt"]
    wrong = [k for k in LAUNCH_FIELDS if k not in row or k not in reg or row[k] != reg[k]]
    if wrong:
        raise LaunchRefused(f"the take differs from its registration (slot {slot!r}, attempt {attempt}) in "
                            f"{', '.join(wrong)}; a take launches exactly as it was registered")
    try:
        pre = prereg.require_frozen("launching a take")
        takes_mod.require_planned_row(row, pre)
    except (SystemExit, ValueError, KeyError, TypeError) as e:
        raise LaunchRefused(f"the take (slot {slot!r}, attempt {attempt}) is not the frozen pre-registration's "
                            f"planned row: {e}") from None
    folder = root / TAKES_DIR / str(slot) / str(attempt)        # ruling w9-Q1: the registered attempt, never a count
    if os.path.lexists(folder):
        raise LaunchRefused(f"{folder} already exists: slot {slot!r}'s open registration is attempt {attempt}, and a "
                            f"take folder is made once, by its own launch (ruling w9-Q1)")
    return str(folder)


def walk_launch_problems(driver, row: dict) -> None:
    """The walk arm; the walk's folder stays walk_folder_in's (rehearsals/<walk>/, an existing one refused)."""
    import walk_register as _walk_register
    root = driver.records_root
    if os.path.lexists(root / FROZEN_NAME):
        raise LaunchRefused(f"{FROZEN_NAME} exists: the design is frozen, and walks run before the freeze (plan CP6)")
    entry = {k: row.get(k) for k in WALK_LAUNCH_FIELDS}
    entry.update(reason=WALK_LAUNCH_REASON, counted=False)
    try:
        design = _walk_register.design_in_force(root)
    except (ValueError, KeyError, OSError) as e:
        raise LaunchRefused(f"the design in force cannot be read ({type(e).__name__}: {e})") from None
    bad = _walk_register.entry_problems(0, entry, design)
    if bad:
        raise LaunchRefused("the walk is not one the design in force admits: " + "; ".join(bad))
    register = root / WALKS_DIR / _walk_register.REGISTER_NAME
    try:
        doc = json.loads(register.read_text(encoding="utf-8"), object_pairs_hook=_walk_register.no_duplicate_keys)
        walks = doc["walks"]
        ids = {e["walk"].casefold() for e in walks if isinstance(e, dict) and isinstance(e.get("walk"), str)}
    except (ValueError, KeyError, TypeError, OSError) as e:
        raise LaunchRefused(f"{WALKS_DIR}/{_walk_register.REGISTER_NAME} cannot be read ({type(e).__name__}); "
                            f"nothing was launched") from None
    if row["walk"].casefold() in ids:
        raise LaunchRefused(f"walk {row['walk']!r} is already registered; a retry is a new walk id")
    walk_identity_problems(driver, row)           # D2, before anything is made


def launch_problems(driver, row: dict):
    """K1-launch (Q-w8d-1): refuse (LaunchRefused) a take or walk that does not match its records, before launch.
    Returns the take's record folder (ruling w9-Q1), or None for a walk (its folder is take_folder's)."""
    if not isinstance(row, dict):
        raise LaunchRefused("the row is not an object")
    if driver.records == "takes":
        return take_launch_problems(driver, row)
    elif driver.records == "walks":
        walk_launch_problems(driver, row)
        return None
    else:
        raise LaunchRefused(f"records {driver.records!r} is neither 'takes' nor 'walks'")


# =====================================================================================================================
# ROUND 4, THE WALK RUNNER'S DRIVER SIDE (lane w10-walk-runner; this file moved from lane w9-cp6 to lane w10 under
# glitch-2f's rulings D1, D2 and D3, the Lane-orchestrator under Javier's standing delegation, Mon 12 Oct 2026).
# Appended above `if __name__`; the in-place edits are take_checker's records argument (walk_driver passes its own),
# the walk folder's closed map (WALK_CHECK, WALK_REQUIRED, WALK_PRE_TURN in walk_files) and one line in
# walk_launch_problems.
#   D1  take_checker reads a walk by check_take.check4_walk (no takes.json row, the full script, the walk's own
#       session), never as a take; the runner (walk_runner.py) writes its reading as check.json, which a walk folder
#       must hold.
#   D2  a walk launches only under its own identity: identity_for(row) gives session id
#       check_take.walk_session_id(<walk id>) and row and row_commit None, else LaunchRefused before anything is made.
#   D3  a walk that died before its driver ledger is committed with preflight.json or refusal.json in its place (and
#       grade.json saying why it was not graded); a folder with neither still refuses.
# =====================================================================================================================

def walk_identity_problems(driver, row: dict) -> None:
    """D2: the walk's identity, as the driver will stamp it on every record, is the walk's own."""
    import check_take as _ct
    try:
        ident = driver.identity_for(row)
        want = _ct.walk_session_id(row["walk"])
    except Exception as e:  # noqa: BLE001 - an identity that cannot be built is refused, never guessed
        raise LaunchRefused(f"the walk's identity cannot be read ({type(e).__name__}: {e}); nothing was launched") \
            from None
    if not isinstance(ident, dict) or ident.get("session_id") != want or ident.get("row") is not None \
            or ident.get("row_commit") is not None:
        got = ident if not isinstance(ident, dict) else {k: ident.get(k) for k in ("session_id", "row", "row_commit")}
        raise LaunchRefused(f"the walk's identity is not its own (ruling D2): {got!r}; a walk has no ledger row or row "
                            f"commit, and its session id is {want} (uuid5 of 'walk/{row['walk']}')")


# ROUND 4, BOOTSTRAP LANE: THE ENVIRONMENT RECORD'S VOCABULARY. Appended here, never above, so no line round 4's
# tests and notes cite by number moves; matched_by, never_stripped_problems and environment_record read these names.
# (glitch-6b's checker-constants ruling of 15 Oct 2026 and its addition of the same morning).
# NAMED DEPARTURE from round 3: the vocabulary above is round 3's, read from the 2.1.267 binary, and the record is
# EXTENDED WITH THE 2.1.296 NAMES FROM THE PINNED BINARY'S STATIC READ (box lane ba6d7f14, lane-reports/stub-take-
# 20261015/claude-2.1.296-env-classification-20261015.json, sha256 4e4c81bf...0fcbd; binary sha256 24972e3b...). All
# fourteen of round 3's listed names are still in 2.1.296; the read found six billing switches outside every pattern
# (HARNESS_NAME_PATTERNS, about line 205) and inference credentials on no list. The four flag lists of that file are added here exactly, and nothing
# else: billing_route_outside_every_pattern and billing_route_in_patterns_not_listed to the billing routes,
# credential_in_patterns_not_listed (less the subscription token by file descriptor, which joins the subscription
# tokens) and credential_outside_every_pattern to the API keys. Three patterns make the names outside every pattern
# recorded. Round 3's tuples stay as they are (run_take.py's copies are bound to them, and run_take's refuse-if-present
# stop list is the box lane's); the environment record and the money line read the RECORD_ vocabulary below.
# tests/test_checker_constants.py binds round 3's names as a subset and the additions to the classified lists.
HARNESS_NAME_PATTERNS_2_1_296 = ("^CLAUDE_CODE_USE_(ANTHROPIC_AWS|ANTHROPIC_GOOGLE_CLOUD|MANTLE|GATEWAY)$",
                                 "^CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST$", "^CLAUDE_CODE_HOST_CREDS_FILE$")
API_KEY_VARIABLES_2_1_296 = ("ANTHROPIC_FOUNDRY_AUTH_TOKEN", "ANTHROPIC_IDENTITY_TOKEN", "ANTHROPIC_IDENTITY_TOKEN_FILE",
                             "ANTHROPIC_ENVIRONMENT_KEY", "ANTHROPIC_WORK_SECRET", "CLAUDE_CODE_GATEWAY_TOKEN",
                             "CLAUDE_CODE_HOST_CREDS_FILE")
BILLING_ROUTE_VARIABLES_2_1_296 = ("CLAUDE_CODE_USE_ANTHROPIC_AWS", "CLAUDE_CODE_USE_ANTHROPIC_GOOGLE_CLOUD",
                                   "CLAUDE_CODE_USE_MANTLE", "CLAUDE_CODE_USE_GATEWAY",
                                   "CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST", "ANTHROPIC_BEDROCK_BASE_URL",
                                   "ANTHROPIC_VERTEX_BASE_URL", "ANTHROPIC_FOUNDRY_BASE_URL", "ANTHROPIC_FOUNDRY_RESOURCE",
                                   "ANTHROPIC_AWS_BASE_URL", "ANTHROPIC_GOOGLE_CLOUD_BASE_URL",
                                   "ANTHROPIC_BEDROCK_MANTLE_BASE_URL", "ANTHROPIC_UNIX_SOCKET")
SUBSCRIPTION_TOKEN_VARIABLES_2_1_296 = ("CLAUDE_CODE_OAUTH_TOKEN_FILE_DESCRIPTOR",)
RECORD_HARNESS_NAME_PATTERNS = HARNESS_NAME_PATTERNS + HARNESS_NAME_PATTERNS_2_1_296
RECORD_API_KEY_VARIABLES = API_KEY_VARIABLES + API_KEY_VARIABLES_2_1_296
RECORD_BILLING_ROUTE_VARIABLES = BILLING_ROUTE_VARIABLES + BILLING_ROUTE_VARIABLES_2_1_296
RECORD_SUBSCRIPTION_TOKEN_VARIABLES = SUBSCRIPTION_TOKEN_VARIABLES + SUBSCRIPTION_TOKEN_VARIABLES_2_1_296
# Round 3's matched_by, never_stripped_problems and environment_record (and the money line through the record) read
# these four module names when called, and stay byte for byte round 3's (checks.d/w6e-drive-commit.txt:6), so the names
# are REBOUND here to the record vocabulary: from here on drive.HARNESS_NAME_PATTERNS and the three lists are round 3's
# extended with 2.1.296's. Round 3's literal assignments above are what run_take's copies are bound to (test_run_take
# reads them with ast); tests/test_checker_constants.py asserts each name IS its RECORD_ tuple and binds both halves.
HARNESS_NAME_PATTERNS = RECORD_HARNESS_NAME_PATTERNS
API_KEY_VARIABLES = RECORD_API_KEY_VARIABLES
BILLING_ROUTE_VARIABLES = RECORD_BILLING_ROUTE_VARIABLES
SUBSCRIPTION_TOKEN_VARIABLES = RECORD_SUBSCRIPTION_TOKEN_VARIABLES


if __name__ == "__main__":
    raise SystemExit(main())
