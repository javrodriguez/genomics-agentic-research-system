#!/usr/bin/env python3
"""Freeze the reviewed round 4 rows, agent identities and complete owned build.

The review commit seeds a deterministic permutation of whole planned rows.
Versions come from the design; no vendor executable is run. All owned files,
including this builder, prose, checks and COPIED.d, carry committed byte pins.
The frozen file binds itself through its unique introducing commit.

Under glitch-f3's ruling w5b-3, COPIED.json is exactly derive() over the build
fragments before any output is written. COPIED.d/freeze.json claims COPIED.json,
prereg.json and itself as new. It is deliberately absent from the snapshot:
--check compares with nothing committed, so there is no circular snapshot.
The two generated non-self outputs are pinned inside prereg.json as well.
All three outputs belong to one freeze commit. Any existing output refuses a
second freeze, including an interrupted first write. Rehearsal/review evidence
must already match the committed draft and tree before the real --write.
Pass the disposable rehearsal report with --rehearsal-record; its content and
hash are retained in prereg.json, without adding that output to the build tree.
"""

from __future__ import annotations

import argparse
import copy
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
import copy_manifest  # noqa: E402
import order_beacon  # noqa: E402

DRAFT = HERE / "prereg-draft.json"
FROZEN = HERE / "prereg.json"


def output_fragment() -> dict:
    return {"lane": "freeze", "files": [
        {"path": path, "status": "new", "reason": "written once by freeze.py at the freeze"}
        for path in ("COPIED.json", "prereg.json", "COPIED.d/freeze.json")
    ]}


def outputs_exist(root: Path) -> bool:
    return any((root / p).exists() for p in ("COPIED.json", "prereg.json", "COPIED.d/freeze.json"))


def snapshot(manifest, folder: Path) -> dict:
    return manifest.derive(folder)


def write_outputs(frozen: dict, *, root=HERE, manifest=copy_manifest) -> tuple[Path, ...]:
    """Write the three outputs, for one subsequent commit; no partial write is retryable.

    The caller has checked the review, rehearsal, design and pins. This boundary
    independently checks the build's copy record before taking its snapshot.
    """
    root = Path(root)
    if outputs_exist(root):
        raise ValueError("a freeze output already exists; the freeze happens once")
    folder = root / "COPIED.d"
    bad = manifest.problems(folder)
    if bad:
        raise ValueError("cannot freeze the copy record: " + "; ".join(bad))
    copied = snapshot(manifest, folder)
    encoded = {"COPIED.json": json_bytes(copied), "COPIED.d/freeze.json": json_bytes(output_fragment())}
    frozen = copy.deepcopy(frozen)
    if "pinned_files" in frozen:
        frozen["pinned_files"].extend(generated_pins(encoded))
    encoded["prereg.json"] = json_bytes(frozen)
    for relative, data in encoded.items():
        (root / relative).write_bytes(data)
    return tuple(root / p for p in encoded)


def json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def generated_pins(outputs):
    return [{"path": study.rel(path), "sha256": hashlib.sha256(data).hexdigest(),
             "git_blob_sha": hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()}
            for path, data in sorted(outputs.items())]


def planned_order(draft, seed):
    import check_results
    rows = draft["rows"]
    check_results.validate_ledger([dict(row, attempt=1) for row in rows])
    if not rows:
        raise ValueError("the design has no planned rows")
    # Stable permutation of whole rows; the harness remains part of each cell.
    return sorted(copy.deepcopy(rows), key=lambda row: hashlib.sha256(seed.encode() + json_bytes(row)).hexdigest())


def draft_pending(draft) -> dict:
    """build_draft.pending over the draft itself: every PENDING input by its pointer (pre-freeze review 1, m2)."""
    import build_draft
    return build_draft.pending(draft)


def prepare(draft, *, review, parent, pins, frozen_at, beacon):
    """The frozen file from the reviewed draft. Pre-freeze review 1, m2: the stats_design sentinel was the only PENDING
    guard, so a copy with that one key replaced froze with 15 PENDING strings left; the draft's own pending() map must
    be empty. MAJOR 9: the order is seeded by order_beacon.seed over the review commit and the registered drand round's
    reading (`beacon`, read by take_order_beacon_reading), never by the review commit alone."""
    import stats
    import completeness
    left = draft_pending(draft)
    if left:
        raise ValueError(f"the draft holds {len(left)} PENDING input(s) ({', '.join(list(left)[:6])}"
                         + (", ..." if len(left) > 6 else "") + "); a design with any PENDING input is never frozen")
    stats.validate_design(draft[stats.DESIGN_KEY])
    completeness.pair_count(draft)
    round_no = order_beacon.registered_round(draft.get(BEACON_KEY))
    bad = order_beacon.reading_problems(beacon, round_no)
    if bad:
        raise ValueError("the take-order beacon reading is refused: " + "; ".join(bad))
    seed = order_beacon.seed(review, beacon)
    frozen = copy.deepcopy(draft)
    frozen.update(status="FROZEN", frozen_at=frozen_at, frozen_at_commit_parent=parent,
                  pre_freeze_review_commit=review, take_order_seed=seed, take_order_beacon_reading=copy.deepcopy(beacon),
                  take_order=planned_order(draft, seed), pinned_files=copy.deepcopy(pins))
    return frozen


BEACON_KEY = "take_order_beacon"
BEACON_READING_KEY = "take_order_beacon_reading"
BEACON_NOT_REHEARSED = ("NOT REHEARSED: the take-order beacon (a disposable rehearsal given no --beacon-reading seeds "
                        "its order from a synthetic reading, marked synthetic in the frozen file)")
SYNTHETIC_SIGNATURE = hashlib.sha256(b"synthetic-rehearsal-not-a-drand-signature").hexdigest()


def synthetic_beacon_reading(round_no: int) -> dict:
    """A rehearsal's stand-in reading of the registered round, shaped like a real one and named synthetic by its
    signature (SYNTHETIC_SIGNATURE), which a real freeze refuses."""
    return {"chain_hash": order_beacon.CHAIN["chain_hash"], "round": round_no,
            "round_time": order_beacon.round_time(round_no), "signature": SYNTHETIC_SIGNATURE,
            "randomness": hashlib.sha256(bytes.fromhex(SYNTHETIC_SIGNATURE)).hexdigest(),
            "relays": list(order_beacon.RELAYS)}


def review_committed_at(review_commit: str) -> int:
    """The review commit's committer time (unix seconds), as git records it."""
    code, out = git("show", "-s", "--format=%ct", review_commit)
    if code != 0 or not out.strip().isdigit():
        raise ValueError(f"the review commit {review_commit[:12]}'s committer time cannot be read")
    return int(out.strip())


def take_order_beacon_reading(draft, review_commit, *, rehearsal=False, reading_file=None, opener=None, now=None):
    """MAJOR 9: the reading of the draft's registered drand round that seeds the order.

    The real freeze reads both relays itself (the network, on the Mac) and refuses a review whose committer time is not
    before the round's time. A disposable rehearsal reads a --beacon-reading file (checked offline: chain, round, time,
    randomness the sha256 of the signature) or, given none, a synthetic reading, and says so (BEACON_NOT_REHEARSED)."""
    try:
        round_no = order_beacon.registered_round(draft.get(BEACON_KEY))
        if rehearsal:
            if reading_file is None:
                print(BEACON_NOT_REHEARSED)
                return synthetic_beacon_reading(round_no)
            reading = json.loads(Path(reading_file).read_text(encoding="utf-8"))
            bad = order_beacon.reading_problems(reading, round_no)
            if bad:
                raise ValueError("the --beacon-reading file is refused: " + "; ".join(bad))
            return reading
        if reading_file is not None:
            raise ValueError("--beacon-reading is for a disposable rehearsal only; the real freeze reads both relays")
        committed = review_committed_at(review_commit)
        if committed >= order_beacon.round_time(round_no):
            raise ValueError(f"the review commit {review_commit[:12]} was committed at {order_beacon.iso(committed)}, "
                             f"not before drand round {round_no} ({order_beacon.iso(order_beacon.round_time(round_no))}):"
                             f" a review committed once the round's value is public could be re-made to choose the "
                             f"order")
        reading = order_beacon.read_relays(round_no, opener=opener, now=now)
        if reading["signature"] == SYNTHETIC_SIGNATURE:
            raise ValueError("the relays answered the rehearsal's synthetic signature")
        return reading
    except order_beacon.BeaconRefused as e:
        raise ValueError(f"the take-order beacon: {e}") from None

# All files present in the ownership record are pinned, including prose,
# checks files, the builder itself and COPIED.d. Runtime records are not part of
# the build. prereg.json binds itself through its unique introducing commit.
def owned_paths(manifest=copy_manifest, folder=None) -> list[str]:
    folder = HERE / "COPIED.d" if folder is None else folder
    entries, problems = manifest.load_fragments(folder)
    if problems:
        raise ValueError("invalid ownership record: " + "; ".join(problems))
    return sorted(entry["path"] for lane, entry in entries)


def _study_files() -> list[str]:
    return [study.rel(p) for p in owned_paths()]


NOT_PINNED_AND_WHY = {study.rel("prereg.json"): "the frozen file binds itself through its introducing commit"}
PINNED = [p for p in _study_files() if p not in NOT_PINNED_AND_WHY] + ["CLAUDE.md"]
GLOB_CHARS = ("*", "?", "[")


def is_pattern(path: str) -> bool:
    return any(c in path for c in GLOB_CHARS)


def pattern_regex(pattern: str) -> re.Pattern:
    """An ownership pattern as a whole-path regex: `**` crosses folders, `*` and `?` stay inside one, `[` is literal
    (no fragment uses a class, so one is refused rather than read)."""
    if "[" in pattern:
        raise ValueError(f"the ownership pattern {pattern!r} uses a character class, which the freeze does not read")
    out, i = [], 0
    while i < len(pattern):
        if pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(out))


def committed_files(prefix: str) -> list[str]:
    """Every file committed at HEAD under `prefix` (a folder), repository-relative."""
    code, out = git("ls-tree", "-r", "--name-only", "HEAD", "--", prefix)
    if code != 0:
        raise ValueError(f"the committed files under {prefix} cannot be listed at HEAD")
    return [ln for ln in out.splitlines() if ln]


def pinned_paths(paths=None) -> list[str]:
    """Pre-freeze review 1, MAJOR 2: PINNED with every ownership pattern (native-readers/**, the one today) expanded into
    the files committed at HEAD that it matches, in order, so each acceptance record and review the freeze's leg (iii)
    reads gets a pin of its own. A pattern that matches no committed file is refused: it would pin nothing."""
    paths = PINNED if paths is None else paths
    out = []
    for p in paths:
        if not is_pattern(p):
            out.append(p)
            continue
        rx = pattern_regex(p)
        literal = p[:min(p.index(c) for c in GLOB_CHARS if c in p)]
        prefix = literal.rsplit("/", 1)[0] if "/" in literal else "."
        matched = sorted(f for f in committed_files(prefix) if rx.fullmatch(f))
        if not matched:
            raise ValueError(f"the ownership pattern {p} matches no committed file, so it would pin nothing")
        out.extend(m for m in matched if m not in out)
    return out


def pin_problems(pins) -> list[str]:
    """Each pin the freeze cannot write: a missing file or one not committed at HEAD."""
    return [f"{p['path']}: " + ("missing" if p.get("missing") else "not committed at HEAD")
            for p in pins if p.get("missing") or p.get("uncommitted")]


def git(*args: str) -> tuple[int, str]:
    out = subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True)
    return out.returncode, out.stdout.strip()


# ROUND 2, CP8. Everything the freeze WRITES, by top-level key or by the key it fills inside a task. The freeze commit's
# body carries the diff between the reviewed draft and the frozen file restricted to these keys, or the word `none`;
# a test asserts that the diff touches nothing else, so a freeze can never edit the design on the way out.
FREEZE_WRITTEN_KEYS = (
    "status", "frozen_at", "frozen_at_commit_parent", "draft_sha256_at_freeze", "pre_freeze_review_commit",
    "pre_freeze_review_file", "pre_freeze_review_sha256", "take_order_seed", "take_order", "pinned_files",
    "take_order_beacon_reading",          # pre-freeze review 1, MAJOR 9: the drand round the order is seeded by
    "nulls_at_freeze", "rehearsal_record", "rehearsed_study_tree_sha256",
    "holdout_salted_digests", "holdout_wordings_per_task_version",
)
FREEZE_FILLED_INSIDE = (
    "system_under_test.gars_tree_sha_at_freeze", "harness.claude_version_at_freeze",
    "tasks[].grader", "tasks[].grader_cases", "tasks[].positive.fixture", "tasks[].control.fixture",
)
# ROUND 2, CP8, review 1 blocker 2. A record bound the draft's bytes and nothing else, and the commit it named in
# prose had been rewritten away, so any code edit between the rehearsal and the freeze passed the gate. The record
# now carries the study tree it rehearsed as data (study_tree_sha), and the freeze requires HEAD's to be the same.
REHEARSAL_TREE_PREFIX = "study tree sha256: "
# what the binding leaves out, on both sides of every comparison: the records the rehearsal and the review write
# between the rehearsal and the freeze, the frozen file itself, and the regrade record the freeze commit rewrites
# (rehearsal 9 found the record's old bytes on one side and nothing on the other)
# and (REVIEW 3, the fact for the owner) PROGRESS.md: the slice line that records a green rehearsal is
# appended AFTER it and would invalidate it every time. It is append-only prose, never read by a take, a
# check or the result, so a line added to it is not a code edit the rehearsal failed to exercise.
TREE_BINDING_EXCLUDED = (re.compile(rf"/{study.VERIFY_DIR}/freeze-rehearsal-\d+(-clean-clone)?\.txt$"),
                         re.compile(rf"/{study.REVIEW_DIR}/prefreeze-\d+(-blindness)?\.(md|txt)$"),
                         re.compile(r"/prereg\.json$"),
                         re.compile(r"/COPIED\.json$"),
                         re.compile(r"/COPIED\.d/freeze\.json$"),
                         re.compile(r"/PROGRESS\.md$"),
                         re.compile(r"/verification/round1-regrade/environment\.json$"))
RULING_LINE = "**Ruling: DO FREEZE.**"
REVIEW_DIGEST_PREFIX = "prereg.json sha256: "     # line 1 of every report (review_kit/commit_review.report_problems)
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


# ROUND 2, CP8, review 3: the pinned files outside the study (CLAUDE.md and the first study's files the carried task
# rests on) are bound with it, so an edit to any of them after the rehearsal is refused at the gate too
BOUND_OUTSIDE = tuple(p for p in PINNED if not p.startswith(study.STUDY_REL + "/"))


def study_tree_sha(rev: str = "HEAD", also_excluded: tuple[str, ...] = ()) -> str:
    """The study's tree at a revision, plus every pinned file outside it, as `git ls-tree -r` prints them with the
    excluded records dropped, hashed.

    `also_excluded` names paths to drop as well, for a caller with a reason; the frozen file and the regrade record are
    already in TREE_BINDING_EXCLUDED, so check_results.py's comparison of the freeze commit with the rehearsal needs none.
    """
    code, out = git("ls-tree", "-r", rev, "--", study.STUDY_REL, *BOUND_OUTSIDE)
    if code != 0 or not out.strip():
        raise SystemExit(f"REFUSING: the study tree at {rev} cannot be listed ({out.strip()[:200]}). Nothing was written.")
    kept = [ln for ln in out.splitlines()
            if not any(p.search(ln) for p in TREE_BINDING_EXCLUDED) and ln.split("\t", 1)[-1] not in also_excluded]
    return hashlib.sha256("\n".join(kept).encode("utf-8")).hexdigest()


# W8B (lane w8b-holdout-digests), ruling W8B-gap4-1, Javier's own decision ("holdout digests A", Mon 12 Oct 2026
# 08:51 EDT): the holdout's salted digests and its per-version count enter this repository only here, in the freeze
# commit's frozen file, read from a digest-only source that lives in private aegis (--holdout-digests). The freeze
# refuses by name when that source is not given or is not a file, rather than write empty values; only a disposable
# rehearsal may go without it, and then writes neither field and says so. The draft never carries them
# (build_draft.prefreeze_holdout_problems, applied again here and by --check).
HOLDOUT_KEYS = ("holdout_salted_digests", "holdout_wordings_per_task_version")
HOLDOUT_SOURCE_KEY = "salted_sha256"
HOLDOUT_ABSENT = ("the holdout digest source is absent: the salted digests and their count live only in private aegis "
                  "until the freeze commit (ruling W8B-gap4-1); give --holdout-digests <file>. Nothing was written.")
HOLDOUT_NOT_REHEARSED = ("NOT REHEARSED: the holdout digests (a disposable rehearsal given no --holdout-digests writes "
                         "neither field)")


def holdout_source_problem(source, rehearsal: bool):
    """Why the freeze cannot read its holdout source, or None. Only a disposable rehearsal may go without one."""
    if source is None:
        return None if rehearsal else HOLDOUT_ABSENT
    if not Path(source).is_file():
        return HOLDOUT_ABSENT
    return None


def _unique_pairs(pairs):
    keys = [key for key, _ in pairs]
    if len(keys) != len(set(keys)):
        raise ValueError("the holdout digest source repeats a key")
    return dict(pairs)


# W8B-R1-1 (ruling W8B-close-1): the rehearsal's synthetic digests are made here, so the real freeze knows them: the
# sha256 of SYNTHETIC_PREFIX + task + "-" + index, index below SYNTHETIC_BOUND. A freeze that is not a disposable
# rehearsal refuses a source holding any of them, for any task of that source.
SYNTHETIC_PREFIX = "synthetic-rehearsal-not-a-wording-"
SYNTHETIC_BOUND = 8
SYNTHETIC_PER_TASK = 2


def synthetic_digest(task: str, index: int) -> str:
    return hashlib.sha256(f"{SYNTHETIC_PREFIX}{task}-{index}".encode()).hexdigest()


def synthetic_holdout_source(draft_file, out_file, per_task: int = SYNTHETIC_PER_TASK) -> dict:
    """A digest-only source for a rehearsal's freeze: synthetic hex digests, one list per task of the draft."""
    if not 0 < per_task <= SYNTHETIC_BOUND:
        raise ValueError(f"a synthetic source holds 1 to {SYNTHETIC_BOUND} digests per task")
    tasks = [task["id"] for task in json.loads(Path(draft_file).read_text())["tasks"]]
    source = {HOLDOUT_SOURCE_KEY: {task: [synthetic_digest(task, i) for i in range(per_task)] for task in tasks}}
    Path(out_file).write_text(json.dumps(source, indent=2) + "\n")
    return source


def synthetic_tasks(digests: dict) -> list[str]:
    """The tasks of a digest map whose list holds a synthetic digest of any of its tasks."""
    known = {synthetic_digest(task, i) for task in digests for i in range(SYNTHETIC_BOUND)}
    return sorted(task for task, values in digests.items() if isinstance(values, list) and known & set(values))


def holdout_fields(source, task_ids, *, rehearsal: bool = False) -> dict:
    """The two freeze-written holdout fields, from a source holding exactly {"salted_sha256": {task: [digest, ...]}}:
    no salt, wording or other key. The count is the source's, the same for every task version. Outside a disposable
    rehearsal, a source holding the rehearsal's synthetic digests is refused (W8B-R1-1)."""
    data = json.loads(Path(source).read_text(encoding="utf-8"), object_pairs_hook=_unique_pairs)
    if not isinstance(data, dict) or set(data) != {HOLDOUT_SOURCE_KEY}:
        raise ValueError(f"the holdout digest source holds exactly {HOLDOUT_SOURCE_KEY}: no salt, wording or other key")
    import build_draft
    count = build_draft.validate_digests(data[HOLDOUT_SOURCE_KEY], list(task_ids))
    synthetic = synthetic_tasks(data[HOLDOUT_SOURCE_KEY])
    if not rehearsal and synthetic:
        raise ValueError("the holdout digest source holds the rehearsal's synthetic digests (" + ", ".join(synthetic)
                         + "); a real freeze takes only the salted digests from private aegis (ruling W8B-gap4-1)")
    return {"holdout_salted_digests": data[HOLDOUT_SOURCE_KEY], "holdout_wordings_per_task_version": count}


# Lane vendor-admission T3 (glitch-b5, 16 Oct 2026), ruling Q-3 (glitch-2f, 12 Oct 2026; codex_adapter.py:9-14,
# gemini_adapter.py:9-14): arms O and G are built on DOCUMENTED stream shapes, and the freeze refuses any arm whose
# adapter has not been re-tested on a stream recorded at its first real walk. Each vendor harness's adapter module
# says which it is (SHAPES_SOURCE); it is imported only when the draft has a row of that harness.
SHAPES_ADAPTERS = {"codex": "codex_adapter", "gemini": "gemini_adapter"}
RECORDED_SHAPES = "recorded"


def unrecorded_shapes_problem(draft):
    """Why the freeze refuses the draft's vendor arms (each arm and leg named), or None. Lane vendor-admission T4 PF
    (lane-reports/vendor-T4-PLAN.md v4 section 7, ruled by glitch-b5 on 17 Oct 2026): a row whose harness is codex or
    gemini is frozen only when all three legs hold for that harness: (i) its adapter's SHAPES_SOURCE is "recorded"
    (T3); (ii) check_take.VENDOR_CHECK_SHAPES_SOURCE is "recorded" and every VENDOR_PENDING_ROWS row of the harness is
    settled; (iii) native_reader_registration.production_readers() holds the harness."""
    import importlib
    rows = draft.get("rows") or []
    bad = []
    for harness in sorted({(r.get("agent") or {}).get("harness") for r in rows} & set(SHAPES_ADAPTERS)):
        module = SHAPES_ADAPTERS[harness]
        legs = []
        adapter = importlib.import_module(module)
        source = adapter.SHAPES_SOURCE
        if source != RECORDED_SHAPES:
            legs.append(f"leg i: {module}.py's SHAPES_SOURCE is {source!r}")
        else:
            legs += [f"leg i: {p}" for p in shapes_binding_problems(harness, adapter, draft)]
        legs += [f"leg ii: {p}" for p in vendor_reader_problems(harness)]
        legs += [f"leg ii: {p}" for p in fixture_binding_problems(harness, draft)]
        legs += [f"leg iii: {p}" for p in registration_problems(harness)]
        arms = sorted({r.get("arm") for r in rows if (r.get("agent") or {}).get("harness") == harness}, key=str)
        bad += [f"arm {arm} ({harness}): {leg}" for arm in arms for leg in legs]
    if not bad:
        return None
    return ("the freeze refuses " + "; ".join(bad) + f"; each leg must read {RECORDED_SHAPES!r} or hold: an arm whose "
            "adapter and checker readers were never re-tested on a stream recorded at its first real walk, or whose "
            "native reader is not registered, is never frozen (ruling Q-3; T4 plan section 7)")


def vendor_reader_problems(harness):
    """Leg (ii): check_take's vendor readers were re-tested on a recorded walk (every READER item on a RECORDED
    fixture; round 8 ruling 3, lane vendor-admission T4 P2) and every PENDING row is settled."""
    import check_take
    if harness not in check_take.VENDOR_PENDING_ROWS:
        return [f"check_take.py's VENDOR_PENDING_ROWS has no {harness} block"]
    source = check_take.VENDOR_CHECK_SHAPES_SOURCE.get(harness)
    out = [] if source == RECORDED_SHAPES else [f"check_take.py's VENDOR_CHECK_SHAPES_SOURCE is {source!r}"]
    out += check_take.vendor_reader_items_problems(harness)
    return out + check_take.vendor_rows_problems(harness)


def pinned_cli(harness, draft):
    """The harness's CLI as its RECORDED fixtures must name it: "<cli> <version>", the version the draft's rows of the
    harness all carry (pre-freeze review 1, m3); None when the rows carry other than exactly one version."""
    import check_take
    versions = {(r.get("agent") or {}).get("version") for r in draft.get("rows") or []
                if (r.get("agent") or {}).get("harness") == harness}
    if len(versions) != 1 or not isinstance(next(iter(versions)), str):
        return None
    return f"{check_take.VENDOR_FIXTURE_CLI[harness]} {versions.pop()}"


def shapes_binding_problems(harness, adapter, draft):
    """Leg (i), pre-freeze review 1 m3: an adapter's SHAPES_SOURCE "recorded" holds only with its SHAPES_RECORDED_ON
    fixture a byte copy of a committed walk record on the pinned CLI (check_take.recorded_binding_problem)."""
    import check_take
    cli = pinned_cli(harness, draft)
    if cli is None:
        return [f"the draft's {harness} rows do not carry exactly one agent version"]
    fixture = getattr(adapter, "SHAPES_RECORDED_ON", None)
    problem = check_take.recorded_binding_problem(harness, fixture, cli)
    return [f"{adapter.__name__}.py's SHAPES_RECORDED_ON: {problem}"] if problem else []


def fixture_binding_problems(harness, draft):
    """Leg (ii), pre-freeze review 1 m3: both tables hold their registered items, and every RECORDED fixture their
    rows and items name is a byte copy of a committed walk record on the pinned CLI."""
    import check_take
    out = check_take.vendor_minimum_problems(harness)
    cli = pinned_cli(harness, draft)
    if cli is None:
        return out + [f"the draft's {harness} rows do not carry exactly one agent version"]
    for fixture in check_take.vendor_fixtures_named(harness):
        problem = check_take.recorded_binding_problem(harness, fixture, cli)
        if problem:
            out.append(problem)
    return out


def registration_problems(harness):
    """Leg (iii): Javier's committed acceptance registers the harness's native reader; a refusing registry is named,
    never a traceback, and so is one that cannot run (no git binary, or any other OSError; round 8 ruling 1)."""
    import native_reader_registration
    try:
        readers = native_reader_registration.production_readers()
    except native_reader_registration.RegistrationRefused as e:
        return [f"the native-reader registry refuses: {e}"]
    except OSError as e:
        return [f"the native-reader registry could not run ({type(e).__name__}: {e})"]
    return [] if harness in readers else [f"no native reader is registered for {harness} (no committed acceptance)"]


def coverage_problem(draft=None):
    """Pre-freeze review 1, MAJOR 4 part 3: why the walks the freeze rests on do not cover the design, or None.

    walk_plan's --coverage reading, in process (walk_plan.coverage_report): every required walk of an arm the freeze
    runs must be covered by a graded walk; a deferred arm's coverage is printed as recorded, not required (OD105:
    arm G runs exactly as registered, only after a later go, whose precondition is its complete coverage)."""
    import walk_plan
    try:
        rep = walk_plan.coverage_report()
    except (walk_plan.PlanRefused, walk_plan.RegisterUnreadable, OSError, ValueError, KeyError) as e:
        return f"the walk coverage cannot be read: {e}"
    for line in walk_plan.deferred_lines(rep["got"], rep["specs"], rep["deferred"]):
        print("freeze: " + line)
    gaps = walk_plan.run_arm_gaps(rep["got"], rep["deferred"])
    if not gaps:
        return None
    per: dict = {}
    for s in gaps:
        per[(s["arm"], s["model"])] = per.get((s["arm"], s["model"]), 0) + 1
    named = "; ".join(f"arm {a}, {m}: {n} missing" for (a, m), n in per.items())
    return (f"{len(gaps)} required walk(s) of the arms the freeze runs are not covered by a graded walk ({named}); "
            f"walk_plan.py --coverage --require-run-arms names each")


def draft_holdout_problem(draft):
    """A pre-freeze draft carrying a freeze-only holdout field is refused, here as in the writer."""
    import build_draft
    bad = build_draft.prefreeze_holdout_problems(draft)
    return ("the draft carries " + ", ".join(bad) + " before the freeze; they enter at the freeze commit only "
            "(ruling W8B-gap4-1)") if bad else None


def rehearsal_evidence(record, digest: str, tree: str) -> dict:
    """Bind an external rehearsal output without changing the rehearsed tree."""
    if record is None:
        raise ValueError("a green rehearsal record is required (--rehearsal-record)")
    record = Path(record)
    data = record.read_bytes()
    text = data.decode("utf-8")
    lines = text.rstrip().splitlines()
    if (not lines or lines[0] != digest or lines[-1] != REHEARSAL_LAST_LINE or
            [line for line in lines if line.startswith(REHEARSAL_TREE_PREFIX)] !=
            [REHEARSAL_TREE_PREFIX + tree]):
        raise ValueError("the rehearsal must be green for this draft and committed tree")
    return {"name": record.name, "sha256": hashlib.sha256(data).hexdigest(), "text": text}


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
               if re.search(rf"^{re.escape(study.rel(study.REVIEW_DIR))}/prefreeze-\d+\.md$", ln)]
    if len(reports) != 1:
        return [f"{review_commit[:12]} lands {len(reports)} pre-freeze review reports; the seed must land exactly one"], None
    code, hist = git("log", "--format=%H", "--", reports[0])
    if len(hist.split()) != 1:
        return [f"{reports[0]} was committed {len(hist.split())} times; the seed would be one of several candidates"], None
    # ROUND 2, CP8, review 1 follow-up: the seed's report must have ruled for the freeze, and must be the latest
    # review committed, so a freeze cannot seed from an earlier or a refusing review
    code, body = git("show", f"{review_commit}:{reports[0]}")
    if RULING_LINE not in body:
        return [f"{reports[0]} at {review_commit[:12]} carries no `{RULING_LINE}` line: the freeze runs only on a "
                f"review that ruled for it"], None
    # Pre-freeze review 1, MAJOR 3: the seed review must have read the bytes being frozen. Its line 1 names the sha256
    # of the prereg.json the reviewer was handed (review_kit/commit_review.py binds it to the kit's copy); a DO FREEZE
    # review of earlier bytes never seeds a freeze of later ones, so a criterion edited after review is not frozen.
    want = REVIEW_DIGEST_PREFIX + hashlib.sha256(DRAFT.read_bytes()).hexdigest()
    first = body.split("\n", 1)[0]
    if first != want:
        return [f"{reports[0]} at {review_commit[:12]} reviewed other bytes: its line 1 is {first[:90]!r}, and the draft "
                f"being frozen needs {want!r}; a review of other bytes cannot seed this freeze"], None
    code, names = git("ls-tree", "-r", "--name-only", "HEAD", "--", study.rel(study.REVIEW_DIR))
    numbers = [int(m.group(1)) for ln in names.splitlines() for m in [re.search(r"prefreeze-(\d+)\.md$", ln)] if m]
    n = int(re.search(r"prefreeze-(\d+)\.md$", reports[0]).group(1))
    if numbers and n != max(numbers):
        return [f"{reports[0]} is not the latest review committed (prefreeze-{max(numbers)}.md is): the freeze seeds "
                f"from the last ruling, not a chosen one"], None
    return [], reports[0]


DUMMY_REVIEW = "0" * 40
DUMMY_PARENT = "0" * 40


def check_legs(draft) -> list[tuple[str, list[str]]]:
    """Pre-freeze review 1, m1: what --check reads, leg by leg, each with its problems ([] when it holds). It runs what a
    freeze runs short of the review and the write: the draft's PENDING map, the holdout fields, every pin (patterns
    expanded), the three vendor legs, the walk coverage of the arms the freeze runs, and prepare on a copy of the draft
    with a dummy review and a synthetic beacon reading (no network, nothing written)."""
    legs = [("copy manifest", copy_manifest.problems())]
    left = draft_pending(draft)
    legs.append(("pending", [f"{len(left)} PENDING input(s): " + ", ".join(left)] if left else []))
    problem = draft_holdout_problem(draft)
    legs.append(("holdout fields", [problem] if problem else []))
    try:
        paths = pinned_paths(PINNED)
        legs.append((f"pins ({len(paths)} paths, patterns expanded)", pin_problems([pin(p) for p in paths])))
    except ValueError as e:
        legs.append(("pins", [str(e)]))
    problem = unrecorded_shapes_problem(draft)
    legs.append(("vendor legs i-iii", [problem] if problem else []))
    problem = coverage_problem(draft)
    legs.append(("walk coverage of the arms the freeze runs", [problem] if problem else []))
    try:
        reading = synthetic_beacon_reading(order_beacon.registered_round(draft.get(BEACON_KEY)))
        prepare(copy.deepcopy(draft), review=DUMMY_REVIEW, parent=DUMMY_PARENT, pins=[], frozen_at="check",
                beacon=reading)
        legs.append(("prepare (dummy review, synthetic beacon reading)", []))
    except Exception as e:      # noqa: BLE001 (every refusal of prepare is this leg's finding, by name)
        legs.append(("prepare (dummy review, synthetic beacon reading)", [f"{type(e).__name__}: {e}"]))
    return legs


def check() -> int:
    """freeze.py --check: every leg of check_legs printed, exit 1 when any has a problem."""
    draft = json.loads(DRAFT.read_text())
    legs = check_legs(draft)
    for name, problems in legs:
        print(f"freeze --check: {name}: " + ("ok" if not problems else "FAIL " + "; ".join(problems)[:1500]))
    entries, _ = copy_manifest.load_fragments()
    claimed = sum(1 for _, e in entries if e["status"] in copy_manifest.STATUSES)
    try:
        paths = pinned_paths(PINNED)
    except ValueError:
        paths = []
    readers = sum(1 for p in paths if copy_manifest.READER_RECORD.fullmatch(p[len(study.STUDY_REL) + 1:]))
    bad = sum(1 for _, problems in legs if problems)
    print(f"freeze: {claimed} fragment-claimed files and {readers} native-reader record(s) owned; "
          f"{len(legs) - bad} of {len(legs)} legs hold; no takes or freeze performed")
    return 1 if bad else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Freeze the full round 4 design once")
    parser.add_argument("--review-commit")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--rehearsal", action="store_true")
    parser.add_argument("--rehearsal-record", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--holdout-digests", type=Path)
    parser.add_argument("--beacon-reading", type=Path,
                        help="a disposable rehearsal only: a reading of the registered drand round, checked offline")
    args = parser.parse_args(argv)
    try:
        if args.check:
            return check()
        problems = copy_manifest.problems()
        if problems:
            raise ValueError("; ".join(problems))
        problem = holdout_source_problem(args.holdout_digests, args.rehearsal)
        if problem:
            raise ValueError(problem)
        if not args.review_commit:
            raise ValueError("a committed pre-freeze review is required")
        if outputs_exist(HERE):
            raise ValueError("a freeze output already exists; the freeze happens once")
        if args.rehearsal:
            code, remotes = git("remote")
            if code or remotes:
                raise ValueError("rehearsal requires a throwaway clone without remotes")
        code, dirty = git("status", "--porcelain")
        if code or dirty:
            raise ValueError("the complete repository must be committed before freezing")
        bad, review_file = review_file_problems(args.review_commit)
        if bad:
            raise ValueError("; ".join(bad))
        draft = json.loads(DRAFT.read_text())
        problem = draft_holdout_problem(draft)
        if problem:
            raise ValueError(problem)
        problem = unrecorded_shapes_problem(draft)
        if problem:
            raise ValueError(problem)
        holdout = ({} if args.holdout_digests is None else
                   holdout_fields(args.holdout_digests, [task["id"] for task in draft["tasks"]],
                                  rehearsal=args.rehearsal))
        digest = hashlib.sha256(DRAFT.read_bytes()).hexdigest()
        tree = study_tree_sha()
        record = None
        if args.write and not args.rehearsal:
            record = rehearsal_evidence(args.rehearsal_record, digest, tree)
        pins = [pin(p) for p in pinned_paths(PINNED)]
        bad = pin_problems(pins)
        if bad:
            raise ValueError("every owned build file must have a committed pin: " + "; ".join(bad[:6]))
        problem = coverage_problem(draft)
        if problem:
            raise ValueError(problem)
        beacon = take_order_beacon_reading(draft, args.review_commit, rehearsal=args.rehearsal,
                                           reading_file=args.beacon_reading)
        _, parent = git("rev-parse", "HEAD")
        frozen = prepare(draft, review=args.review_commit, parent=parent, pins=pins,
                         frozen_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(), beacon=beacon)
        frozen.update(draft_sha256_at_freeze=digest, pre_freeze_review_file=review_file,
                      pre_freeze_review_sha256=hashlib.sha256((REPO / review_file).read_bytes()).hexdigest(),
                      rehearsal_record=record if record else "rehearsal or preview",
                      rehearsed_study_tree_sha256=tree)
        frozen.update(holdout)
        if not holdout:
            print(HOLDOUT_NOT_REHEARSED)
        if keys_outside_the_freeze(draft, frozen):
            raise ValueError("freeze changed the registered design")
        if args.write:
            outputs = write_outputs(frozen)
            print("freeze: wrote " + ", ".join(p.name for p in outputs) + "; commit all three in one commit")
        else:
            print(json.dumps(frozen, indent=2))
        return 0
    except (ValueError, KeyError, OSError) as exc:
        print(f"freeze: REFUSE: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
