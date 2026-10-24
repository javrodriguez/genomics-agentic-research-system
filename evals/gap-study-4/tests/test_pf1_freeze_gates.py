#!/usr/bin/env python3
"""Lane pf1-l1-freeze-gates (Gap Study round 4): the freeze gates pre-freeze review 1 found open.

The lane orchestrator's fold plan of Sat 24 Oct 2026 (FOLD-PLAN-prefreeze-1.md, lane L1), approved under Javier's
standing delegation. Each clause below was written red first: run against the freeze line 96c1d959 with only this file
added, every clause reads red (the lane's hand-back quotes the run). Each witness edits one line of the code a clause
guards and must turn that clause red alone.

  G2.pins      MAJOR 2: freeze.pinned_paths expands native-readers/** into exactly the four committed acceptance records
               and reviews, a pattern matching no committed file is refused, and the expanded count reconciles with
               the copy manifest's (fragment-claimed files plus reader records plus CLAUDE.md, less prereg.json).
               Witnesses: pattern-unexpanded, empty-pattern-admitted.
  G3.review    MAJOR 3: in a scratch repository, a DO FREEZE review whose line 1 names other bytes is refused by
               review_file_problems, and the same review naming the draft's bytes is admitted.
               Witness: review-digest-unchecked.
  G9.beacon    MAJOR 9: order_beacon reads drand quicknet rounds as published (the round the builder read from both
               relays on 24 Oct 2026 is the test vector); read_relays refuses an unpublished round without reading the
               network, a disagreement and a randomness that is not the signature's sha256; prepare seeds the order
               with order_beacon.seed, never the review commit; the real freeze refuses a review committed at or after
               a --beacon-reading file; ruling 1 of the lane orchestrator (24 Oct 2026): the seed is the round and its
               randomness alone, so two reviews freeze one order, and the real freeze reads the relays only once
               GitHub's push records on the aegis remote hold the commit that registered the round, stamped an hour
               or more before it is published (registering_commit on a scratch history, push_records on a stand-in
               gh); the draft registers the beacon with its round PENDING; and prereg.py --order-from-beacon refuses
               before the round is published and reads a frozen file's reading. Witnesses: seed-ignores-randomness,
               relays-not-compared, push-lead-unchecked, push-holding-unchecked, preview-before-round.
  G2b.pending  m2: prepare refuses a draft holding any PENDING input even with its stats_design sentinel replaced.
               Witness: pending-unchecked.
  G4.coverage  MAJOR 4 part 3: the freeze's coverage reading names the missing walks of arms A and O and none of the
               deferred arm G's, which it prints as recorded; freeze.main refuses on a coverage gap before prepare;
               freeze_rehearsal runs walk_plan.py --coverage --require-run-arms. Witnesses: deferred-required,
               coverage-skipped.
  G1.check     m1: freeze.py --check reads every leg (copy manifest, pending, holdout fields, expanded pins, the three
               vendor legs, coverage, prepare with a dummy review) and exits 1 on the committed draft, which the freeze
               refuses; 0 only when every leg holds. Witness: check-legs-ignored.
  G6.walkpins  m6: walk_pins.py holds every registered walk to the draft's version pins, image ids and pinned gars tree;
               a copy with one walk's version, image or tree changed is refused by name; freeze_rehearsal runs it.
               Witnesses: walk-version-unchecked, walk-image-unchecked.
  G7.regrade   m7: walk_regrade's report refuses outside a git repository, its gate refuses a register of walks of
               which nothing was re-derived and, once any regrade exists, a pending walk with none; --check prints
               the counts. Witnesses: outside-git-empty, vacuous-admitted.
  G3m.legs     m3: both vendor tables hold their registered items, every RECORDED fixture is held to its committed
               walk's bytes and the pinned CLI version, and leg i holds only with the adapter's SHAPES_RECORDED_ON
               fixture bound. Witnesses: minimum-dropped, binding-bytes-unchecked, shapes-word-alone.
  G8.copies    m8: copy_manifest --check refuses an edited copy that is a near-rewrite (above NEAR_REWRITE_SHARE of its
               lines changed) whose reason cites no lane record; the live record is clean of it (review_kit/rounds.json
               aside, unclaimed since 96c1d959 and reported to the orchestrator). Witness: near-rewrite-unchecked.

Reads the committed study and copies it into temporary folders; patched openers stand in for the network. No model,
no network, no container. --witnesses runs every witness and prints a line for each.
"""

from __future__ import annotations

import contextlib
import copy
import hashlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:      # kept: the gates import their siblings lazily (build_draft, completeness, stats)
    sys.path.insert(0, str(HERE))

import check_take as ct  # noqa: E402
import codex_adapter  # noqa: E402
import freeze  # noqa: E402
import freeze_rehearsal  # noqa: E402
import order_beacon  # noqa: E402
import prereg  # noqa: E402
import walk_pins  # noqa: E402
import walk_plan  # noqa: E402
import walk_regrade  # noqa: E402

# drand quicknet round 33356692 as api.drand.sh, drand.cloudflare.com and api2.drand.sh all answered it on Sat 24 Oct
# 2026 16:24-16:25 EDT (the lane builder's curl reads); published 2026-10-24T20:24:00Z.
ROUND = 33356692
SIGNATURE = ("923de5ea6ff8d8702585b65f992a8a991da6a8d37f6b8d9e6817b5be0b27b75c"
             "93d944a935689e1eec7985c5fb782ffc")
RANDOMNESS = "ba6557025dd415aa63a9247283a8d471e877b8f9ab51d18acaf84abdbdcd53db"
ROUND_TIME = 1792873440
REVIEW = "f" * 40
OTHER_REVIEW = "0123456789abcdef0123456789abcdef01234567"
READERS = sorted(f"evals/gap-study-4/native-readers/{h}-{k}" for h in ("codex", "gemini")
                 for k in ("acceptance.json", "review.md"))


def reading(**edits) -> dict:
    out = {"chain_hash": order_beacon.CHAIN["chain_hash"], "round": ROUND, "round_time": ROUND_TIME,
           "randomness": RANDOMNESS, "signature": SIGNATURE, "relays": list(order_beacon.RELAYS)}
    out.update(edits)
    return out


def relay_opener(answers=None, seen=None):
    """A stand-in for the network: each relay answers `answers[relay]` (a dict), default the recorded round."""
    def opener(url):
        if seen is not None:
            seen.append(url)
        relay = next(r for r in order_beacon.RELAYS if url.startswith(r + "/"))
        doc = (answers or {}).get(relay, {"round": ROUND, "randomness": RANDOMNESS, "signature": SIGNATURE})
        return json.dumps(doc).encode()
    return opener


def committed_draft() -> dict:
    return json.loads((HERE / "prereg-draft.json").read_text())


def registered(draft: dict, round_no=ROUND) -> dict:
    d = copy.deepcopy(draft)
    d["take_order_beacon"] = dict(order_beacon.registration(), round=round_no)
    return d


@contextlib.contextmanager
def open_design(fz):
    """prepare's design checks stood down on the committed draft (its PENDING inputs are another lane's fills): only
    the seed and the pending guard under test run."""
    import completeness
    import stats
    with mock.patch.object(stats, "validate_design", lambda d: d), \
            mock.patch.object(completeness, "pair_count", lambda d: 0), \
            mock.patch.object(fz, "draft_pending", lambda d: {}):
        yield


def git(repo: Path, *args: str) -> str:
    out = subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                          "-c", "commit.gpgsign=false", *args], capture_output=True, text=True)
    if out.returncode != 0:
        raise AssertionError(f"git {args}: {out.stderr}")
    return out.stdout.strip()


# ------------------------------------------------------------------------------------------------------------- clauses
def g2_pins(fz, p="G2.pins") -> list:
    out = []
    try:
        paths = fz.pinned_paths(fz.PINNED)
        got = sorted(x for x in paths if x.startswith("evals/gap-study-4/native-readers/"))
        if got != READERS:
            out.append(f"{p}: native-readers/** pins {got}, wanted {READERS}")
        if any(fz.is_pattern(x) for x in paths):
            out.append(f"{p}: a pattern is still pinned literally")
        missing = [x for x in paths if not (fz.REPO / x).is_file()]
        if missing:
            out.append(f"{p}: pinned paths that are no file: {missing[:3]}")
        entries, _ = fz.copy_manifest.load_fragments()
        claimed = {e["path"] for _, e in entries if e["status"] in fz.copy_manifest.STATUSES}
        want = len(claimed) - (1 if "prereg.json" in claimed else 0) + len(READERS) + 1
        if len(paths) != want:
            out.append(f"{p}: {len(paths)} pinned paths, the manifest's count reconciles to {want}")
        try:
            fz.pinned_paths(["evals/gap-study-4/native-readers/no-such-*.json"])
            out.append(f"{p}: a pattern matching no committed file was admitted")
        except ValueError:
            pass
    except Exception as e:  # noqa: BLE001
        return [f"ERROR {p}: {type(e).__name__}: {str(e)[:240]}"]
    return out


def g3_review(fz, p="G3.review") -> list:
    out = []
    try:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            git(repo, "init", "-q")
            study_dir = repo / "evals" / "gap-study-4"
            (study_dir / "review_kit").mkdir(parents=True)
            draft = study_dir / "prereg-draft.json"
            draft.write_bytes(b'{"synthetic": "bytes B"}\n')
            other = hashlib.sha256(b'{"synthetic": "bytes A"}\n').hexdigest()
            here = hashlib.sha256(draft.read_bytes()).hexdigest()
            report = study_dir / "review_kit" / "prefreeze-1.md"
            for n, digest in ((1, other), (2, here)):
                report = study_dir / "review_kit" / f"prefreeze-{n}.md"
                report.write_text(f"prereg.json sha256: {digest}\n\n# synthetic review\n\n{fz.RULING_LINE}\n")
                git(repo, "add", "-A")
                git(repo, "commit", "-q", "-m", f"review {n}")
                sha = git(repo, "rev-parse", "HEAD")
                with mock.patch.object(fz, "REPO", repo), mock.patch.object(fz, "DRAFT", draft):
                    bad, name = fz.review_file_problems(sha)
                if n == 1 and not any("reviewed other bytes" in b for b in bad):
                    out.append(f"{p}: a review of other bytes seeds the freeze: {bad}")
                if n == 2 and (bad or name != "evals/gap-study-4/review_kit/prefreeze-2.md"):
                    out.append(f"{p}: the review of the draft's bytes is refused: {bad}")
    except Exception as e:  # noqa: BLE001
        return [f"ERROR {p}: {type(e).__name__}: {str(e)[:240]}"]
    return out


def g9_beacon(fz, ob, pr, p="G9.beacon") -> list:
    out = []
    try:
        if ob.round_time(ROUND) != ROUND_TIME or ob.round_at(
                __import__("datetime").datetime.fromtimestamp(ROUND_TIME - 1, __import__("datetime").timezone.utc)) \
                != ROUND:
            out.append(f"{p}: round {ROUND}'s time is not {ROUND_TIME}")
        if ob.reading_problems(reading(), ROUND):
            out.append(f"{p}: the recorded round reads wrong: {ob.reading_problems(reading(), ROUND)}")
        if not ob.reading_problems(reading(randomness="0" * 64), ROUND):
            out.append(f"{p}: a randomness that is not the signature's sha256 was admitted")
        got = ob.read_relays(ROUND, opener=relay_opener(), now=ROUND_TIME + 60)
        if got != reading():
            out.append(f"{p}: two agreeing relays read {got}")
        for answers, why in (({ob.RELAYS[1]: {"round": ROUND, "randomness": "a" * 64, "signature": "b" * 96}},
                              "disagree"), ({ob.RELAYS[0]: {"round": ROUND + 1, "randomness": RANDOMNESS,
                                                             "signature": SIGNATURE}}, "another round")):
            try:
                ob.read_relays(ROUND, opener=relay_opener(answers), now=ROUND_TIME + 60)
                out.append(f"{p}: relays that {why} were admitted")
            except ob.BeaconRefused:
                pass
        seen = []
        try:
            ob.read_relays(ROUND, opener=relay_opener(seen=seen), now=ROUND_TIME - 1)
            out.append(f"{p}: an unpublished round was read")
        except ob.BeaconRefused:
            if seen:
                out.append(f"{p}: the network was read for an unpublished round")
        s1 = ob.seed(reading())
        s3 = ob.seed(reading(randomness="c" * 64))
        s4 = ob.seed(reading(round=ROUND + 1))
        if len({s1, s3, s4}) != 3 or not ob.SEED_SHAPE.fullmatch(s1) or s1 != hashlib.sha256(
                f"gap-study-4 take order\n{ROUND}\n{RANDOMNESS}".encode()).hexdigest()[:40]:
            out.append(f"{p}: the seed is not SEED_RULE over the round and its randomness")
        d = registered(committed_draft())
        with open_design(fz):
            frozen = fz.prepare(d, review=REVIEW, parent="b" * 40, pins=[], frozen_at="t", beacon=reading())
            other = fz.prepare(d, review=OTHER_REVIEW, parent="b" * 40, pins=[], frozen_at="t", beacon=reading())
        if frozen["take_order_seed"] != s1 or frozen["take_order_beacon_reading"] != reading() or \
                frozen["take_order"] != fz.planned_order(d, s1):
            out.append(f"{p}: prepare does not seed the order with order_beacon.seed")
        if other["take_order"] != frozen["take_order"] or other["pre_freeze_review_commit"] != OTHER_REVIEW:
            out.append(f"{p}: the review commit moves the order")
        if fz.keys_outside_the_freeze(d, frozen):
            out.append(f"{p}: the freeze wrote keys outside its own: {fz.keys_outside_the_freeze(d, frozen)}")
        for bad_beacon in (None, reading(round=ROUND + 1), reading(signature="00")):
            try:
                with open_design(fz):
                    fz.prepare(d, review=REVIEW, parent="b" * 40, pins=[], frozen_at="t", beacon=bad_beacon)
                out.append(f"{p}: prepare admitted the beacon reading {bad_beacon!r:.60}")
            except (ValueError, TypeError):
                pass
        lead = ob.WITNESS_LEAD_S
        early, pushed = [(ROUND_TIME - lead - 60, "a" * 40)], "c" * 40
        holds = lambda commit, sha: (commit, sha) == (pushed, "a" * 40)  # noqa: E731
        for name, commit, pushes, contains in (
                ("no registering commit", None, early, holds),
                ("no push holding it", pushed, early, lambda c, s: False),
                ("a push under the lead", pushed, [(ROUND_TIME - lead + 60, "a" * 40)], holds),
                ("a push after the round", pushed, [(ROUND_TIME + 60, "a" * 40)], holds)):
            seen = []
            with mock.patch.object(fz, "registering_commit", lambda r, commit=commit: commit):
                try:
                    fz.take_order_beacon_reading(d, REVIEW, opener=relay_opener(seen=seen), now=ROUND_TIME + 120,
                                                 pushes=pushes, contains=contains)
                    out.append(f"{p}: the real freeze ran with {name}")
                except ValueError:
                    pass
            if seen:
                out.append(f"{p}: the relays were read with {name}")
        with mock.patch.object(fz, "registering_commit", lambda r: pushed):
            if fz.take_order_beacon_reading(d, REVIEW, opener=relay_opener(), now=ROUND_TIME + 60, pushes=early
                                            + [(ROUND_TIME + 5, "b" * 40)], contains=holds) != reading():
                out.append(f"{p}: the real freeze with an early witnessed push does not read the relays")
            with tempfile.TemporaryDirectory() as tmp:
                f = Path(tmp) / "reading.json"
                f.write_text(json.dumps(reading()))
                try:
                    fz.take_order_beacon_reading(d, REVIEW, reading_file=f, opener=relay_opener(), now=ROUND_TIME + 60)
                    out.append(f"{p}: the real freeze took a --beacon-reading file")
                except ValueError:
                    pass
                if fz.take_order_beacon_reading(d, REVIEW, rehearsal=True, reading_file=f) != reading():
                    out.append(f"{p}: a rehearsal's --beacon-reading file was not read")
            with contextlib.redirect_stdout(io.StringIO()) as said:
                synthetic = fz.take_order_beacon_reading(d, REVIEW, rehearsal=True)
            if synthetic["signature"] != fz.SYNTHETIC_SIGNATURE or fz.BEACON_NOT_REHEARSED not in said.getvalue():
                out.append(f"{p}: a rehearsal without a reading is not marked synthetic")
        live = committed_draft()
        if live.get("take_order_beacon") != order_beacon.registration() or live["take_order_beacon"]["round"] != \
                "PENDING" or "/take_order_beacon/round" not in live.get("pending", {}):
            out.append(f"{p}: the committed draft does not register the beacon with its round PENDING")
        if "cannot have been chosen to suit a result" in pr.__doc__:
            out.append(f"{p}: prereg.py still claims the order cannot have been chosen")
        future = registered(live, round_no=ob.round_at(__import__("datetime").datetime.now(
            __import__("datetime").timezone.utc)) + 100000)
        for design, why in ((dict(live, _frozen=False, _source="prereg-draft.json"), "PENDING"),
                            (dict(future, _frozen=False, _source="prereg-draft.json"), "not yet published")):
            seen = []
            with mock.patch.object(pr, "load", lambda design=design: design):
                try:
                    pr.order_from_beacon(opener=relay_opener(seen=seen))
                    out.append(f"{p}: --order-from-beacon previewed an order with its round {why}")
                except ob.BeaconRefused:
                    pass
            if seen:
                out.append(f"{p}: --order-from-beacon read the network for a round {why}")
        command = freeze_rehearsal.freeze_command(REVIEW, None, "/synthetic/reading.json")
        if command[-2:] != ("--beacon-reading", "/synthetic/reading.json") or \
                "--beacon-reading" in freeze_rehearsal.freeze_command(REVIEW, None):
            out.append(f"{p}: the rehearsal does not hand its freeze the --beacon-reading it was given: {command}")
        if freeze_rehearsal.beacon_written_problems(frozen) or not freeze_rehearsal.beacon_written_problems(
                dict(frozen, take_order_beacon_reading=fz.synthetic_beacon_reading(ROUND))):
            out.append(f"{p}: the rehearsal's beacon step does not fail a synthetic reading alone")
        frozen_doc = dict(frozen, _frozen=True, _source="prereg.json")
        with mock.patch.object(pr, "load", lambda: frozen_doc):
            if pr.order_from_beacon() != frozen["take_order"]:
                out.append(f"{p}: --order-from-beacon does not read the frozen file's order")
        with tempfile.TemporaryDirectory() as tmp:                     # registering_commit on a scratch history
            repo = Path(tmp)
            git(repo, "init", "-q")
            (repo / "evals" / "gap-study-4").mkdir(parents=True)
            shas = []
            for value in ("None", "123", "1234"):
                (repo / "evals" / "gap-study-4" / "order_beacon.py").write_text(
                    f"x = 1\nREGISTERED_ROUND: int | None = {value}\n")
                git(repo, "add", "-A")
                git(repo, "commit", "-q", "-m", value)
                shas.append(git(repo, "rev-parse", "HEAD"))
            with mock.patch.object(fz, "REPO", repo):
                got = [fz.registering_commit(r) for r in (123, 1234, 12)]
        if got != [shas[1], shas[2], None]:
            out.append(f"{p}: registering_commit reads {got}, wanted the commits that set 123 and 1234, none for 12")
        fake = types.SimpleNamespace(returncode=0, stdout=f"2026-10-24T20:00:00Z\t{'d' * 40}\n", stderr="")
        with mock.patch.object(fz.subprocess, "run", lambda argv, **k: fake if argv[:2] == ["gh", "api"] and
                               "repos/javrodriguez/aegis/activity?activity_type=push&per_page=100" in argv else None):
            if fz.push_records() != [(ROUND_TIME - 1440, "d" * 40)]:
                out.append(f"{p}: push_records does not read GitHub's push activity")
    except Exception as e:  # noqa: BLE001
        return [f"ERROR {p}: {type(e).__name__}: {str(e)[:300]}"]
    return out


def g2b_pending(fz, p="G2b.pending") -> list:
    out = []
    try:
        import completeness
        import stats
        d = registered(committed_draft())
        d[stats.DESIGN_KEY] = {"synthetic": "the sentinel replaced"}
        with mock.patch.object(stats, "validate_design", lambda x: x), \
                mock.patch.object(completeness, "pair_count", lambda x: 0):
            try:
                fz.prepare(d, review=REVIEW, parent="b" * 40, pins=[], frozen_at="t", beacon=reading())
                out.append(f"{p}: a draft with PENDING inputs froze once its sentinel was replaced")
            except ValueError as e:
                if "PENDING input" not in str(e):
                    out.append(f"{p}: refused, but not for its PENDING inputs: {e}")
    except Exception as e:  # noqa: BLE001
        return [f"ERROR {p}: {type(e).__name__}: {str(e)[:240]}"]
    return out


def g4_coverage(fz, wp, fr, p="G4.coverage") -> list:
    out = []
    try:
        with contextlib.redirect_stdout(io.StringIO()) as said:
            problem = fz.coverage_problem(committed_draft())
        rep = wp.coverage_report()
        gaps = wp.run_arm_gaps(rep["got"], rep["deferred"])
        if sorted(rep["deferred"]) != ["G"] or any(s["arm"] == "G" for s in gaps):
            out.append(f"{p}: the deferred arm's walks are required: deferred {sorted(rep['deferred'])}")
        if not gaps or not problem or f"{len(gaps)} required walk(s)" not in problem or "arm G" in problem:
            out.append(f"{p}: the coverage gap of arms A and O is not named: {problem!r:.200}")
        if "deferred arm G, gemini-3.8-flash" not in said.getvalue():
            out.append(f"{p}: arm G's coverage is not printed as recorded")
        if wp.run_arm_gaps(rep["got"], {}) == gaps:
            out.append(f"{p}: run_arm_gaps reads no deferred arm")
        complete = dict(rep, got=dict(rep["got"], missing=[]))
        with mock.patch.object(wp, "coverage_report", lambda: complete), contextlib.redirect_stdout(io.StringIO()):
            if fz.coverage_problem(committed_draft()) is not None:
                out.append(f"{p}: complete coverage still refused")
        if ("walk_plan.py", "--coverage", "--require-run-arms") not in fr.COMMANDS:
            out.append(f"{p}: freeze_rehearsal does not run the coverage gate")
        calls = []
        harness = MainHarness(fz, coverage=lambda d: "synthetic coverage gap", prepare_calls=calls)
        code, text = harness.run(["--review-commit", REVIEW, "--rehearsal"])
        if code != 1 or "synthetic coverage gap" not in text or calls:
            out.append(f"{p}: freeze.main does not refuse a coverage gap before prepare (exit {code}): {text[-200:]}")
    except Exception as e:  # noqa: BLE001
        return [f"ERROR {p}: {type(e).__name__}: {str(e)[:240]}"]
    return out


class MainHarness:
    """freeze.main with git, the review, the tree and the writer faked, and the new gates stood in for."""

    def __init__(self, fz, *, coverage=lambda d: None, prepare_calls=None):
        self.fz, self.coverage, self.calls = fz, coverage, prepare_calls if prepare_calls is not None else []

    def run(self, argv):
        fz = self.fz
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "prereg-draft.json").write_text(json.dumps({"status": "DRAFT", "tasks": [], "rows": []}))
            fake_git = {("remote",): (0, ""), ("status", "--porcelain"): (0, ""), ("rev-parse", "HEAD"): (0, "b" * 40)}
            patches = ((fz, "HERE", tmp), (fz, "REPO", tmp), (fz, "DRAFT", tmp / "prereg-draft.json"),
                       (fz, "PINNED", []), (fz, "git", lambda *a: fake_git.get(a, (1, "no fake"))),
                       (fz, "prepare", lambda d, **k: self.calls.append(k) or dict(d, take_order=[])),
                       (fz, "review_file_problems", lambda c: ([], "review/prefreeze-1.md")),
                       (fz, "study_tree_sha", lambda *a, **k: "c" * 64),
                       (fz, "coverage_problem", self.coverage),
                       (fz, "take_order_beacon_reading", lambda *a, **k: reading()),
                       (fz, "owned_paths", lambda *a, **k: []),
                       (fz.copy_manifest, "problems", lambda *a, **k: []))
            out = io.StringIO()
            with contextlib.ExitStack() as stack:
                for module, name, value in patches:
                    stack.enter_context(mock.patch.object(module, name, value))
                stack.enter_context(contextlib.redirect_stdout(out))
                code = fz.main(argv)
            return code, out.getvalue()


def g1_check(fz, p="G1.check") -> list:
    out = []
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            legs = fz.check_legs(committed_draft())
        names = [n for n, _ in legs]
        for want in ("copy manifest", "pending", "holdout fields", "pins", "vendor legs i-iii", "walk coverage",
                     "prepare"):
            if not any(n.startswith(want) for n in names):
                out.append(f"{p}: --check reads no {want} leg: {names}")
        failing = {n.split(" (")[0] for n, problems in legs if problems}
        for want in ("pending", "walk coverage of the arms the freeze runs", "prepare"):
            if want not in failing:
                out.append(f"{p}: the {want} leg holds on a draft the freeze refuses")
        with mock.patch.object(fz, "check_legs", lambda d: legs), contextlib.redirect_stdout(io.StringIO()):
            code = fz.main(["--check"])
        if code != 1:
            out.append(f"{p}: freeze.py --check exits {code} on a draft the freeze refuses")
        held = [(n, []) for n in names]
        with mock.patch.object(fz, "check_legs", lambda d: held), contextlib.redirect_stdout(io.StringIO()) as said:
            code = fz.main(["--check"])
        if code != 0 or f"{len(names)} of {len(names)} legs hold" not in said.getvalue():
            out.append(f"{p}: --check is not green when every leg holds (exit {code})")
        one = [(n, ["synthetic"] if i == 3 else []) for i, n in enumerate(names)]
        with mock.patch.object(fz, "check_legs", lambda d: one), contextlib.redirect_stdout(io.StringIO()):
            if fz.main(["--check"]) != 1:
                out.append(f"{p}: one failing leg reads green")
    except Exception as e:  # noqa: BLE001
        return [f"ERROR {p}: {type(e).__name__}: {str(e)[:240]}"]
    return out


def g6_walkpins(wpins, fr, p="G6.walkpins") -> list:
    out = []
    try:
        problems, n = wpins.check()
        if problems or n != len(json.loads((HERE / "rehearsals" / "register.json").read_text())["walks"]) or n == 0:
            out.append(f"{p}: the committed walks read {n}, {problems[:3]}")
        if ("walk_pins.py", "--check") not in fr.COMMANDS:
            out.append(f"{p}: freeze_rehearsal does not run walk_pins")
        reg = json.loads((HERE / "rehearsals" / "register.json").read_text())
        picks = ["w125", "w-o46", "w-g21"]

        def edited(walk, fname, edit):
            with tempfile.TemporaryDirectory() as tmp:
                base = Path(tmp) / "rehearsals"
                base.mkdir()
                (base / "register.json").write_text(json.dumps(
                    dict(reg, walks=[e for e in reg["walks"] if e["walk"] in picks])))
                for w in picks:
                    for f in ("driver-ledger.json", "launch.json"):
                        (base / w).mkdir(exist_ok=True)
                        shutil.copyfile(HERE / "rehearsals" / w / f, base / w / f)
                doc = json.loads((base / walk / fname).read_text())
                edit(doc)
                (base / walk / fname).write_text(json.dumps(doc))
                return wpins.check(base=base)

        got, n = edited("w125", "driver-ledger.json", lambda d: None)
        if got or n != 3:
            out.append(f"{p}: three committed walks copied read {n}, {got}")
        got, _ = edited("w-o46", "driver-ledger.json", lambda d: d["agent"].update(version="0.161.0"))
        if not any("w-o46" in x and "agent version" in x for x in got):
            out.append(f"{p}: a walk on another CLI version passed: {got}")
        got, _ = edited("w-g21", "driver-ledger.json", lambda d: d.update(gars_tree_sha="0" * 40))
        if not any("w-g21" in x and "gars tree" in x for x in got):
            out.append(f"{p}: a walk on another gars tree passed: {got}")

        def other_image(d):
            for s in d["steps"]:
                if s.get("step") == "take-create":
                    s["argv"] = [("sha256:" + "1" * 64) if walk_pins.IMAGE_ID.fullmatch(str(a)) else a
                                 for a in s["argv"]]
        got, _ = edited("w125", "launch.json", other_image)
        if not any("w125" in x and "take-create" in x for x in got):
            out.append(f"{p}: a walk from another take image passed: {got}")
    except Exception as e:  # noqa: BLE001
        return [f"ERROR {p}: {type(e).__name__}: {str(e)[:240]}"]
    return out


def g7_regrade(wr, p="G7.regrade") -> list:
    out = []
    try:
        with tempfile.TemporaryDirectory() as tmp:
            problems, counts = wr.regrade_report(Path(tmp))
        if not any("not inside a git repository" in x for x in problems):
            out.append(f"{p}: outside a git repository the report is {problems}")
        base = {"walks": 5, "regrades": 0, "recheck_walks": 0, "counts": 0, "pending": 2,
                "pending_unregraded": ["w-a", "w-b"]}
        if not any("nothing was re-derived" in x for x in wr.gate_problems([], base)):
            out.append(f"{p}: a register of walks with nothing re-derived reads green")
        if wr.gate_problems([], dict(base, counts=3)):
            out.append(f"{p}: counts re-derived before any regrade read red")
        begun = wr.gate_problems([], dict(base, regrades=1, pending_unregraded=["w-b"]))
        if not any("w-b" in x and "regrade has begun" in x for x in begun):
            out.append(f"{p}: a partial regrade reads green: {begun}")
        if wr.gate_problems([], dict(base, walks=0)):
            out.append(f"{p}: an empty register reads red")
        with mock.patch.object(wr, "regrade_report", lambda *a, **k: ([], dict(base, counts=4))), \
                contextlib.redirect_stdout(io.StringIO()) as said:
            code = wr.main(["--check"])
        if code != 0 or "re-derived 0 regrade.json file(s), 0 walk(s)' recheck chains and 4 check.json count(s)" \
                not in said.getvalue():
            out.append(f"{p}: --check does not print the counts: {said.getvalue()[-300:]}")
    except Exception as e:  # noqa: BLE001
        return [f"ERROR {p}: {type(e).__name__}: {str(e)[:240]}"]
    return out


def g3m_legs(fz, ctm, ca, p="G3m.legs") -> list:
    out = []
    try:
        for h in ("codex", "gemini"):
            if ctm.vendor_minimum_problems(h):
                out.append(f"{p}: the live {h} tables miss registered items")
            cli = fz.pinned_cli(h, committed_draft())
            for fx in ctm.vendor_fixtures_named(h):
                if ctm.recorded_binding_problem(h, fx, cli):
                    out.append(f"{p}: {fx}: {ctm.recorded_binding_problem(h, fx, cli)}")
            if not ctm.recorded_binding_problem(h, ctm.vendor_fixtures_named(h)[0], f"{ctm.VENDOR_FIXTURE_CLI[h]} 0.0.1"):
                out.append(f"{p}: a label on another version of {h} was admitted")
        if fz.unrecorded_shapes_problem(committed_draft()) is not None:
            out.append(f"{p}: the committed draft's legs do not hold")
        for table in ("VENDOR_PENDING_ROWS", "VENDOR_READER_ITEMS"):
            emptied = dict(getattr(ctm, table), codex={})
            with mock.patch.object(ctm, table, emptied):
                got = fz.unrecorded_shapes_problem(committed_draft()) or ""
            if "has no registered" not in got:
                out.append(f"{p}: {table} emptied for codex leaves leg ii open: {got[:160]!r}")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            name = "recorded-codex-w-o46"
            shutil.copytree(HERE / "tests" / "fixtures" / name, root / "tests" / "fixtures" / name)
            (root / "rehearsals" / "w-o46").mkdir(parents=True)
            src = root / "rehearsals" / "w-o46" / "transcript.jsonl"
            shutil.copyfile(HERE / "rehearsals" / "w-o46" / "transcript.jsonl", src)
            with mock.patch.object(ctm, "HERE", root):
                cli = "codex-cli 0.162.1"
                if ctm.recorded_binding_problem("codex", f"{name}/transcript.jsonl", cli):
                    out.append(f"{p}: the copied fixture does not bind")
                src.write_bytes(src.read_bytes() + b"\n")
                if not ctm.recorded_binding_problem("codex", f"{name}/transcript.jsonl", cli):
                    out.append(f"{p}: a fixture whose walk record moved still binds")
        with mock.patch.object(ca, "SHAPES_RECORDED_ON", None):
            got = fz.unrecorded_shapes_problem(committed_draft()) or ""
        if "leg i: codex_adapter.py's SHAPES_RECORDED_ON" not in got:
            out.append(f"{p}: SHAPES_SOURCE 'recorded' holds leg i with no bound fixture: {got[:160]!r}")
    except Exception as e:  # noqa: BLE001
        return [f"ERROR {p}: {type(e).__name__}: {str(e)[:240]}"]
    return out


def g8_copies(cm, p="G8.copies") -> list:
    out = []
    try:
        if abs(cm.changed_share(b"a\nb\nc\nd\n", b"a\nB\nc\nd\n") - 0.25) > 1e-9 or cm.changed_share(b"x\n", b"x\n"):
            out.append(f"{p}: changed_share is not the changed lines over the longer side")
        live = [x for x in cm.problems() if "review_kit/rounds.json" not in x]
        if live:
            out.append(f"{p}: the live copy record has problems: {live[:3]}")
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "COPIED.d"
            shutil.copytree(HERE / "COPIED.d", folder)
            frag = json.loads((folder / "w5b-cp5-pipeline.json").read_text())
            for e in frag["files"]:
                if e["path"] in ("result.py", "takes.py"):
                    e["reason"] = e["reason"].split(" Pre-freeze review 1, m8")[0]
            (folder / "w5b-cp5-pipeline.json").write_text(json.dumps(frag))
            got = [x for x in cm.problems(folder) if "near-rewrite" in x]
            if sorted(x.split(" ", 1)[0] for x in got) != ["result.py", "takes.py"]:
                out.append(f"{p}: two near-rewrites with their citations removed read {got}")
    except Exception as e:  # noqa: BLE001
        return [f"ERROR {p}: {type(e).__name__}: {str(e)[:240]}"]
    return out


# ------------------------------------------------------------------------------------------------------------ witnesses
def witness_module(real: types.ModuleType, edits: tuple) -> types.ModuleType:
    src = Path(real.__file__).read_text(encoding="utf-8")
    for old, new in edits:
        if src.count(old) != 1:
            raise AssertionError(f"witness anchor occurs {src.count(old)} times in {real.__name__}: {old[:70]!r}")
        src = src.replace(old, new)
    mod = types.ModuleType(real.__name__)
    mod.__file__ = real.__file__
    path, modules = list(sys.path), dict(sys.modules)
    try:
        sys.path.insert(0, str(HERE))
        exec(compile(src, real.__file__ + " (witness)", "exec"), mod.__dict__)  # noqa: S102
    finally:
        sys.path[:] = path
        for name in set(sys.modules) - set(modules):
            del sys.modules[name]
        sys.modules.update(modules)
    return mod


def run_clause(clause: str, swap: dict | None = None) -> list:
    m = {"freeze": freeze, "order_beacon": order_beacon, "prereg": prereg, "walk_plan": walk_plan,
         "freeze_rehearsal": freeze_rehearsal, "walk_pins": walk_pins, "walk_regrade": walk_regrade,
         "check_take": ct, "codex_adapter": codex_adapter, "copy_manifest": freeze.copy_manifest}
    swap = swap or {}
    with contextlib.ExitStack() as stack:
        for name, mod in swap.items():
            stack.enter_context(mock.patch.dict(sys.modules, {name: mod}))
            m[name] = mod
            if name != "freeze" and hasattr(m["freeze"], name):
                stack.enter_context(mock.patch.object(m["freeze"], name, mod))
        return {
            "G2.pins": lambda: g2_pins(m["freeze"]),
            "G3.review": lambda: g3_review(m["freeze"]),
            "G9.beacon": lambda: g9_beacon(m["freeze"], m["order_beacon"], m["prereg"]),
            "G2b.pending": lambda: g2b_pending(m["freeze"]),
            "G4.coverage": lambda: g4_coverage(m["freeze"], m["walk_plan"], m["freeze_rehearsal"]),
            "G1.check": lambda: g1_check(m["freeze"]),
            "G6.walkpins": lambda: g6_walkpins(m["walk_pins"], m["freeze_rehearsal"]),
            "G7.regrade": lambda: g7_regrade(m["walk_regrade"]),
            "G3m.legs": lambda: g3m_legs(m["freeze"], m["check_take"], m["codex_adapter"]),
            "G8.copies": lambda: g8_copies(m["copy_manifest"]),
        }[clause]()


# name: (clause, module name, ((anchor, replacement), ...))
WITNESSES = {
    "pattern-unexpanded": ("G2.pins", "freeze", (("        if not is_pattern(p):\n            out.append(p)\n"
                                                  "            continue\n",
                                                  "        out.append(p)\n        continue\n"),)),
    "empty-pattern-admitted": ("G2.pins", "freeze", (("        if not matched:\n            raise ValueError(",
                                                      "        if False:\n            raise ValueError("),)),
    "review-digest-unchecked": ("G3.review", "freeze", (("    if first != want:\n", "    if False:\n"),)),
    "seed-ignores-randomness": ("G9.beacon", "order_beacon", (('    text = f"{SEED_PREFIX}{reading[\'round\']}\\n'
                                                               '{reading[\'randomness\']}"\n',
                                                               '    text = f"{SEED_PREFIX}{reading[\'round\']}"\n'),)),
    "relays-not-compared": ("G9.beacon", "order_beacon", (("    if len(set(answers)) != 1:\n", "    if False:\n"),)),
    "push-lead-unchecked": ("G9.beacon", "order_beacon", (("    if held[0] > deadline:\n", "    if False:\n"),)),
    "push-holding-unchecked": ("G9.beacon", "order_beacon", (("    held = sorted(t for t, sha in pushes if "
                                                              "contains(commit, sha))\n",
                                                              "    held = sorted(t for t, sha in pushes)\n"),)),
    "preview-before-round": ("G9.beacon", "prereg", (("        reading = order_beacon.read_relays(round_no, "
                                                      "opener=opener, now=now)\n",
                                                      "        reading = {'round': round_no, 'randomness': '0'}\n"),)),
    "pending-unchecked": ("G2b.pending", "freeze", (("    if left:\n        raise ValueError(f\"the draft holds",
                                                     "    if False:\n        raise ValueError(f\"the draft holds"),)),
    "deferred-required": ("G4.coverage", "walk_plan", (('    return [s for s in got["missing"] if s["arm"] not in '
                                                        'deferred]\n', '    return list(got["missing"])\n'),)),
    "coverage-skipped": ("G4.coverage", "freeze", (("        problem = coverage_problem(draft)\n        if problem:\n"
                                                    "            raise ValueError(problem)\n", ""),)),
    "check-legs-ignored": ("G1.check", "freeze", (("    return 1 if bad else 0\n", "    return 0\n"),)),
    "walk-version-unchecked": ("G6.walkpins", "walk_pins", (('    if agent.get("version") != want or '
                                                             'ledger.get("claude_version") != want:\n',
                                                             "    if False:\n"),)),
    "walk-image-unchecked": ("G6.walkpins", "walk_pins", (("        if ids != [lock]:\n", "        if False:\n"),)),
    "outside-git-empty": ("G7.regrade", "walk_regrade", (("        return [NOT_A_REPOSITORY.format(study=study)], "
                                                          "counts\n", "        return [], counts\n"),)),
    "vacuous-admitted": ("G7.regrade", "walk_regrade", (('    if counts["walks"] and not derived:\n',
                                                         "    if False:\n"),)),
    "minimum-dropped": ("G3m.legs", "freeze", (("    out = check_take.vendor_minimum_problems(harness)\n",
                                                "    out = []\n"),)),
    "binding-bytes-unchecked": ("G3m.legs", "check_take", (("            return f\"its fixture {fixture!r} differs "
                                                            "from the committed walk record {source}\"\n",
                                                            "            pass\n"),)),
    "shapes-word-alone": ("G3m.legs", "freeze", (("            legs += [f\"leg i: {p}\" for p in "
                                                  "shapes_binding_problems(harness, adapter, draft)]\n",
                                                  "            pass\n"),)),
    "near-rewrite-unchecked": ("G8.copies", "copy_manifest", (("            if share > NEAR_REWRITE_SHARE:\n",
                                                               "            if False:\n"),)),
}
MODULES = {"copy_manifest": freeze.copy_manifest, "freeze": freeze, "order_beacon": order_beacon, "prereg": prereg, "walk_plan": walk_plan,
           "walk_pins": walk_pins, "walk_regrade": walk_regrade, "check_take": ct}


class TestPf1FreezeGates(unittest.TestCase):
    def check(self, clause):
        self.assertEqual(run_clause(clause), [], clause)

    def test_g2_pins_expand_patterns(self):
        self.check("G2.pins")

    def test_g3_review_must_have_read_the_frozen_bytes(self):
        self.check("G3.review")

    def test_g9_beacon_seeds_the_order(self):
        self.check("G9.beacon")

    def test_g2b_prepare_refuses_pending(self):
        self.check("G2b.pending")

    def test_g4_coverage_gates_the_freeze(self):
        self.check("G4.coverage")

    def test_g1_check_reads_every_leg(self):
        self.check("G1.check")

    def test_g6_walks_held_to_their_pins(self):
        self.check("G6.walkpins")

    def test_g7_regrade_gate_is_not_vacuous(self):
        self.check("G7.regrade")

    def test_g3m_vendor_legs_bound_to_bytes(self):
        self.check("G3m.legs")

    def test_g8_near_rewrites_cite_a_record(self):
        self.check("G8.copies")


class TestWitnesses(unittest.TestCase):
    def test_each_witness_is_red_by_its_clause(self):
        for name, (clause, module, edits) in WITNESSES.items():
            with self.subTest(witness=name):
                mutant = witness_module(MODULES[module], edits)
                got = run_clause(clause, {module: mutant})
                errors = [x for x in got if x.startswith("ERROR")]
                self.assertEqual(errors, [], f"{name}: errored: {errors}")
                self.assertTrue([x for x in got if x.startswith(clause + ":")], f"{name}: survived")
                print(f"\nWITNESS {name}: red by {clause}", end=" ", file=sys.stderr, flush=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
