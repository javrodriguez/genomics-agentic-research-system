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
               with order_beacon.seed, never the review commit; the real freeze refuses a --beacon-reading file;
               ruling 1 of the lane orchestrator (24 Oct 2026): the seed is the round and its randomness alone, so
               two reviews freeze one order, and take_order_witness refuses unless GitHub's push records on the
               private GARS mirror hold the commits that registered the round and last changed the draft, stamped an
               hour or more before it is published (push_records on a stand-in gh; G9b.witness reads real scratch
               histories); the draft registers the beacon with its round PENDING; and prereg.py --order-from-beacon refuses
               before the round is published and reads a frozen file's reading. Witnesses: seed-ignores-randomness,
               relays-not-compared, witness-repo-aegis, push-lead-unchecked, push-holding-unchecked,
               preview-before-round.
  G9b.witness  The review of 53d0e9af, findings 1 and 2, on scratch histories: a docstring naming rounds registers
               nothing (registered_value parses the assignment); a round set twice, set back, set from another round
               or never None first is refused; a draft changed after the witnessed push is refused, and the witness
               (both commits, their pushes and GitHub's stamps) is what take_order_witness returns and the freeze writes
               (FREEZE_WRITTEN_KEYS); take_order_beacon_reading takes no review commit; gh api is pinned to github.com
               and refuses another GH_HOST. Witnesses: docstring-registers, history-unchecked, draft-unwitnessed,
               host-unpinned.
  G9c.branches The closure check of 84ab6393, finding 1, on scratch branch histories: a candidate draft on another
               pushed branch after the registration, a round registered on another pushed branch, a pushed sha this
               clone does not hold, and a merge that took another line's draft (draft_commit refuses two candidate
               lines) are each refused; another lane's branch from before the registration is no candidate; the
               residual names only a rewritten mirror or GitHub. Witnesses: foreign-round-admitted,
               foreign-draft-admitted, missing-push-admitted, draft-lines-unchecked.
  G10.nits     NITs 4, 6 and 7: prepare's docstring keeps the review commit out of the seed; a pinned file with
               uncommitted edits fails --check's pins leg; an unparseable grade.json counts as pending.
               Witnesses: dirty-pin-admitted, unreadable-grade-skipped.
  G2b.pending  m2: prepare refuses a draft holding any PENDING input even with its stats_design sentinel replaced.
               Lane gap-prebeacon-fix (28 Oct 2026): the live draft's only PENDING input is now the beacon's round,
               which the clause registers, so the refusal is proved on a PENDING-input fixture (the walk counts null,
               one input string PENDING), and the clause fails if its fixture holds none. Witness: pending-unchecked.
  G4.coverage  MAJOR 4 part 3: the freeze's coverage reading names the missing walks of arms A and O and none of the
               deferred arm G's, which it prints as recorded; freeze.main refuses on a coverage gap before prepare;
               freeze_rehearsal runs walk_plan.py --coverage --require-run-arms. Lane gap-freeze-gates-cover (28 Oct
               2026): the live line covers arms A and O since e4a0829f, so the refusal is proved on a coverage-gap
               fixture (one missing walk of each of arms A, O and G) and the live reading need only agree with
               walk_plan's. Witnesses: deferred-required, coverage-skipped, run-gap-admitted.
  G1.check     m1: freeze.py --check reads every leg (copy manifest, pending, holdout fields, expanded pins, the three
               vendor legs, coverage, prepare with a dummy review) and exits 1 on the committed draft, which the freeze
               refuses; 0 only when every leg holds. The coverage leg agrees with walk_plan's live reading and fails
               on the coverage-gap fixture (lane gap-freeze-gates-cover). Witnesses: check-legs-ignored,
               coverage-leg-dropped.
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
               aside, unclaimed since 96c1d959 and reported to the orchestrator); after the review of 53d0e9af
               (finding 3) a citation is a commit that resolves and changed the file after its copy commit: a bare
               date, a hash naming nothing, a commit that never touched it and its copy commit each refuse.
               After its closure check (finding 2) every cited commit must be on HEAD's line and an edit of the
               file: one good citation never covers a bad one. Witnesses: near-rewrite-unchecked,
               citation-unresolved-admitted, copy-commit-admitted, citation-one-covers-all,
               citation-off-head-admitted.

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


def unregistered(draft: dict) -> dict:
    """The draft with its round PENDING again, named in pending and the design withheld (lane gap-beacon-commit): a
    draft the freeze refuses, whatever round the committed draft registers."""
    import build_draft
    import stats
    d = copy.deepcopy(draft)
    d["take_order_beacon"] = dict(order_beacon.registration(), round="PENDING")
    d["pending"] = build_draft.pending(d)
    d[stats.DESIGN_KEY] = {"PENDING": sorted(d["pending"])}
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
        # + 2: CLAUDE.md and (lane pf1-l4-close, review m4) the approved price table, both outside the study folder
        want = len(claimed) - (1 if "prereg.json" in claimed else 0) + len(READERS) + 2
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


def register_round(repo: Path, review_dir: Path, n: int) -> None:
    """Lane fold3/m1 (pre-freeze review 3, m2): the round's row committed alone in review_kit/rounds.json, then its
    blindness record naming the session id that commit derives, written for the review's own commit to carry."""
    import takes
    reg = review_dir / "rounds.json"
    rows = json.loads(reg.read_text())["rows"] if reg.is_file() else []
    # lane fold8/review-binding (review 6, M2): the launch commit, None in a repository with no commit yet
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "-q", "--verify", "HEAD"], capture_output=True, text=True)
    reg.write_text(json.dumps({"rows": rows + [{"n": n, "kind": "prefreeze", "launch_commit": head.stdout.strip() or None,
                                                "voids": None}]}) + "\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", f"register round {n}")
    sid = takes.session_id_for(git(repo, "rev-parse", "HEAD"))
    (review_dir / f"prefreeze-{n}-blindness.txt").write_text(f"session id: {sid}\n")


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
            # lane fold8/review-binding (review 6, M1): rounds 1-4 no longer seed (REPORT_DIGEST_GRANDFATHERED), so the
            # rig's rounds are 5 and 6, each blindness record stating its report's digest (fold5's rule), the draft pinned
            for n, digest in ((5, other), (6, here)):
                register_round(repo, study_dir / "review_kit", n)     # lane fold3/m1 (review 3, m2): its row first
                report = study_dir / "review_kit" / f"prefreeze-{n}.md"
                text = f"prereg.json sha256: {digest}\n\n# synthetic review\n\n{fz.RULING_LINE}\n"
                report.write_text(text)
                with (study_dir / "review_kit" / f"prefreeze-{n}-blindness.txt").open("a") as fh:
                    fh.write(fz._blindness().REPORT_DIGEST + hashlib.sha256(text.encode()).hexdigest() + "\n")
                git(repo, "add", "-A")
                git(repo, "commit", "-q", "-m", f"review {n}")
                sha = git(repo, "rev-parse", "HEAD")
                with mock.patch.object(fz, "REPO", repo), mock.patch.object(fz, "DRAFT", draft), \
                        mock.patch.object(fz, "PINNED", ["evals/gap-study-4/prereg-draft.json"]):
                    bad, name = fz.review_file_problems(sha)
                if n == 5 and not any("reviewed other bytes" in b for b in bad):
                    out.append(f"{p}: a review of other bytes seeds the freeze: {bad}")
                if n == 6 and (bad or name != "evals/gap-study-4/review_kit/prefreeze-6.md"):
                    out.append(f"{p}: the review of the draft's bytes is refused: {bad}")
    except Exception as e:  # noqa: BLE001
        return [f"ERROR {p}: {type(e).__name__}: {str(e)[:240]}"]
    return out


def g9_beacon(fz, ob, pr, p="G9.beacon") -> list:
    out = []
    try:
        # ruling 1 of 24 Oct, second hand-back: the witness is the private GARS mirror, under Javier's standing word
        # "mirror every verified gap study wave" (12 Oct 2026, plans/gap-study-round-4/next-slices-2026-10-11.md)
        if ob.WITNESS_REPO != "javrodriguez/gars-cloud-mirror":
            out.append(f"{p}: the witness repository is {ob.WITNESS_REPO}, not the private GARS mirror")
        reg = ob.registration()
        word = "mirror every verified gap study wave"
        if word not in reg["seed_rule"] or word not in reg["residual"]:
            out.append(f"{p}: the draft's beacon rule and residual do not cite the standing word")
        if reg.get("registration_order") != list(ob.REGISTRATION_ORDER) or len(ob.REGISTRATION_ORDER) != 5 or \
                not ob.REGISTRATION_ORDER[0].startswith("1. Fetch every mirror ref") or \
                not all(w in " ".join(ob.REGISTRATION_ORDER) for w in ("REGISTERED_ROUND", "athena", "gars-mirror.sh",
                                                                       "an hour", "read-only")):
            out.append(f"{p}: the draft does not order the registering steps: {reg.get('registration_order')}")
        gone = ob.push_witness_problem("c" * 40, ROUND, [], lambda c, x: True) or ""
        if "documents no retention" not in gone or "never passes" not in gone:
            out.append(f"{p}: a missing push record is not refused by name as possibly expired: {gone!r}")
        if out:
            return out      # the rest reads the draft's registration, which a wrong witness or rule already breaks
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
            with mock.patch.object(fz, "registering_commit", lambda r, commit=commit: commit), \
                    mock.patch.object(fz, "draft_commit", lambda: pushed), \
                    mock.patch.object(fz, "mirror_problem", lambda *a: None):     # G9c reads real branch histories
                try:
                    fz.take_order_witness(d, pushes=pushes, contains=contains)
                    out.append(f"{p}: the witness held with {name}")
                except ValueError:
                    pass
        if ob.push_witness_problem(pushed, ROUND, early, lambda c, s: False) is None:
            out.append(f"{p}: a push that does not hold the commit witnessed it")
        with mock.patch.object(fz, "registering_commit", lambda r: pushed), \
                mock.patch.object(fz, "draft_commit", lambda: pushed), \
                mock.patch.object(fz, "mirror_problem", lambda *a: None):     # G9c reads real branch histories
            w = fz.take_order_witness(d, pushes=early + [(ROUND_TIME + 5, "b" * 40)], contains=holds)
            if w.get("registering_push") != {"sha": "a" * 40, "stamp": early[0][0]}:
                out.append(f"{p}: an early witnessed push is not the witness: {w}")
            if fz.take_order_beacon_reading(d, opener=relay_opener(), now=ROUND_TIME + 60) != reading():
                out.append(f"{p}: the real freeze does not read the relays")
            with tempfile.TemporaryDirectory() as tmp:
                f = Path(tmp) / "reading.json"
                f.write_text(json.dumps(reading()))
                try:
                    fz.take_order_beacon_reading(d, reading_file=f, opener=relay_opener(), now=ROUND_TIME + 60)
                    out.append(f"{p}: the real freeze took a --beacon-reading file")
                except ValueError:
                    pass
                if fz.take_order_beacon_reading(d, rehearsal=True, reading_file=f) != reading():
                    out.append(f"{p}: a rehearsal's --beacon-reading file was not read")
            with contextlib.redirect_stdout(io.StringIO()) as said:
                synthetic = fz.take_order_beacon_reading(d, rehearsal=True)
            if synthetic["signature"] != fz.SYNTHETIC_SIGNATURE or fz.BEACON_NOT_REHEARSED not in said.getvalue():
                out.append(f"{p}: a rehearsal without a reading is not marked synthetic")
        live = committed_draft()
        # lane gap-beacon-commit: the committed draft holds order_beacon.REGISTERED_ROUND, with the round PENDING and
        # named in pending exactly while that is None
        unset = order_beacon.REGISTERED_ROUND is None
        if live.get("take_order_beacon") != order_beacon.registration() or \
                (live["take_order_beacon"]["round"] == "PENDING") != unset or \
                ("/take_order_beacon/round" in live.get("pending", {})) != unset:
            out.append(f"{p}: the committed draft does not register the beacon as order_beacon.REGISTERED_ROUND reads")
        if "cannot have been chosen to suit a result" in pr.__doc__:
            out.append(f"{p}: prereg.py still claims the order cannot have been chosen")
        future = registered(live, round_no=ob.round_at(__import__("datetime").datetime.now(
            __import__("datetime").timezone.utc)) + 100000)
        for design, why in ((dict(unregistered(live), _frozen=False, _source="prereg-draft.json"), "PENDING"),
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
        fake = types.SimpleNamespace(returncode=0, stdout=f"2026-10-24T20:00:00Z\t{'d' * 40}\n", stderr="")
        with mock.patch.object(fz.subprocess, "run", lambda argv, **k: fake if argv[:4] == ["gh", "api", "--hostname", "github.com"] and
                               "repos/javrodriguez/gars-cloud-mirror/activity?per_page=100"
                               in argv else None):
            if fz.push_records() != [(ROUND_TIME - 1440, "d" * 40)]:
                out.append(f"{p}: push_records does not read GitHub's push activity")
    except Exception as e:  # noqa: BLE001
        return [f"ERROR {p}: {type(e).__name__}: {str(e)[:300]}"]
    return out


def pending_fixture(draft: dict) -> dict:
    """The PENDING-input witness: the draft with two inputs PENDING by their producers' own shapes, whatever the live
    draft holds. Lane gap-prebeacon-fix (28 Oct 2026): since the walk counts were filled (lane gap-walk-counts), the
    committed draft's only PENDING input is the beacon's round, which `registered` fills, so the clause read on the
    live draft alone handed prepare a draft with nothing PENDING and could no longer see the guard refuse. Here the four
    walk counts are null, as build_draft.walk_counts_value writes them while walk_counts refuses, and one input string
    is PENDING, as build_draft writes an unsupplied value."""
    import build_draft
    d = copy.deepcopy(draft)
    d["walk_counts"] = dict(d["walk_counts"], on_path_closers=None, off_path_offers=None, inherited_shapes=[None, None])
    d["stats_design_inputs"] = dict(d["stats_design_inputs"], power=build_draft.PENDING + ": a fixture input")
    return d


def g2b_pending(fz, p="G2b.pending") -> list:
    out = []
    try:
        import completeness
        import stats
        d = pending_fixture(registered(committed_draft()))
        d[stats.DESIGN_KEY] = {"synthetic": "the sentinel replaced"}
        left = fz.draft_pending(d)
        if not left or [k for k in left if k.startswith("/take_order_beacon/")]:
            return [f"{p}: the fixture must hold a PENDING input and must not hold the beacon's (the clause registers "
                    f"it), or the refusal would not be the fixture's: {sorted(left)}"]
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


def coverage_gap_fixture(rep: dict) -> dict:
    """The coverage-gap witness: the live reading with one required walk of each arm (A, O and the deferred G) set
    missing and nothing else missing. Lane gap-freeze-gates-cover (28 Oct 2026): since e4a0829f the live line covers
    every walk of arms A and O, so a clause that reads the live line alone could no longer see the gate refuse; the
    gate is proved on this fixture, whatever the live line holds."""
    first = {}
    for s in rep["specs"]:
        first.setdefault(s["arm"], s)
    missing = [first[a] for a in ("A", "O", "G") if a in first]
    if len(missing) != 3:
        raise AssertionError(f"the plan holds no spec of arm(s) {sorted({'A', 'O', 'G'} - set(first))}")
    return dict(rep, got=dict(rep["got"], missing=missing))


def g4_coverage(fz, wp, fr, p="G4.coverage") -> list:
    out = []
    try:
        rep = wp.coverage_report()
        if sorted(rep["deferred"]) != ["G"]:
            out.append(f"{p}: the deferred arm's walks are required: deferred {sorted(rep['deferred'])}")
        # The live line: the freeze's reading agrees with walk_plan's, gap or none, and prints arm G as recorded.
        live_gaps = wp.run_arm_gaps(rep["got"], rep["deferred"])
        with mock.patch.object(wp, "coverage_report", lambda: rep), \
                contextlib.redirect_stdout(io.StringIO()) as said:
            live = fz.coverage_problem(committed_draft())
        if bool(live) != bool(live_gaps) or (live_gaps and f"{len(live_gaps)} required walk(s)" not in live):
            out.append(f"{p}: the live line's reading disagrees with walk_plan's {len(live_gaps)} gap(s): {live!r:.200}")
        if "deferred arm G, gemini-3.8-flash" not in said.getvalue():
            out.append(f"{p}: arm G's coverage is not printed as recorded")
        # The coverage-gap fixture: one missing walk of each of arms A, O and G, which the gate must refuse.
        gap = coverage_gap_fixture(rep)
        gaps = wp.run_arm_gaps(gap["got"], gap["deferred"])
        if sorted(s["arm"] for s in gaps) != ["A", "O"]:
            out.append(f"{p}: the deferred arm's walks are required: gaps of arms {sorted(s['arm'] for s in gaps)}")
        with mock.patch.object(wp, "coverage_report", lambda: gap), contextlib.redirect_stdout(io.StringIO()):
            problem = fz.coverage_problem(committed_draft())
        if (not problem or f"{len(gaps)} required walk(s)" not in problem or "arm A, " not in problem
                or "arm O, " not in problem or "arm G" in problem):
            out.append(f"{p}: the coverage gap of arms A and O is not named: {problem!r:.200}")
        if wp.run_arm_gaps(gap["got"], {}) == gaps:
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

    def __init__(self, fz, *, coverage=lambda d: None, prepare_calls=None, order_hash=None):
        self.fz, self.coverage, self.calls = fz, coverage, prepare_calls if prepare_calls is not None else []
        self.order_hash = order_hash if order_hash is not None else (lambda fz: fz.take_order_function_sha256())

    def run(self, argv):
        fz = self.fz
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            # pre-freeze review 2, m3 (lane fold2/lb's leg; this rig's draft by lane fold2/lc): a draft carries the
            # order function's hash, at the value this tree computes, as a built draft does, so freeze.main reaches
            # the gates this harness exercises; no gate is stood in for it
            (tmp / "prereg-draft.json").write_text(json.dumps({"status": "DRAFT", "tasks": [], "rows": [],
                                                               fz.ORDER_FUNCTION_HASH_KEY: self.order_hash(fz)}))
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
        import walk_plan as wp
        cover = "walk coverage of the arms the freeze runs"
        rep = wp.coverage_report()
        live_gaps = wp.run_arm_gaps(rep["got"], rep["deferred"])
        with mock.patch.object(wp, "coverage_report", lambda: rep), contextlib.redirect_stdout(io.StringIO()):
            legs = fz.check_legs(unregistered(committed_draft()))     # lane gap-beacon-commit: a refused draft
        names = [n for n, _ in legs]
        for want in ("copy manifest", "pending", "holdout fields", "pins", "vendor legs i-iii", "walk coverage",
                     "prepare"):
            if not any(n.startswith(want) for n in names):
                out.append(f"{p}: --check reads no {want} leg: {names}")
        failing = {n.split(" (")[0] for n, problems in legs if problems}
        for want in ("pending", "prepare"):
            if want not in failing:
                out.append(f"{p}: the {want} leg holds on a draft the freeze refuses")
        # Lane gap-freeze-gates-cover (28 Oct 2026): the live line covers arms A and O since e4a0829f, so the
        # coverage leg holds there; it must agree with walk_plan's reading, and fail on the coverage-gap fixture.
        if (cover in failing) != bool(live_gaps):
            out.append(f"{p}: the {cover} leg disagrees with walk_plan's {len(live_gaps)} gap(s) on the live line")
        with mock.patch.object(wp, "coverage_report", lambda: coverage_gap_fixture(rep)), \
                contextlib.redirect_stdout(io.StringIO()):
            gap_legs = fz.check_legs(committed_draft())
        if cover not in {n.split(" (")[0] for n, problems in gap_legs if problems}:
            out.append(f"{p}: the {cover} leg holds on a coverage gap of arms A and O")
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


def cm_first_commit(cm, path: str) -> str:
    """The commit that first added `path` under the study (its copy commit)."""
    got = subprocess.run(["git", "-C", str(HERE), "log", "--reverse", "--format=%H", "--", path],
                         capture_output=True, text=True).stdout.split()
    return got[0]


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
            # the review of 53d0e9af, finding 3: a citation must be a commit that resolves and edited the file after
            # its copy commit; a bare date, a hash that resolves to nothing, or a commit that never touched it refuses
            for why, cite, says in (("a bare date", "20261024", "resolves to no commit"),
                                    ("a hash that resolves to nothing", "deadbeefdeadbeef01", "resolves to no commit"),
                                    ("a commit that never touched result.py", "96c1d959932216ab9acd43003143348c9761a513",
                                     "change it after its copy commit"),
                                    ("result.py's own copy commit", cm_first_commit(cm, "result.py"),
                                     "change it after its copy commit")):
                frag = json.loads((HERE / "COPIED.d" / "w5b-cp5-pipeline.json").read_text())
                for e in frag["files"]:
                    if e["path"] == "result.py":
                        e["reason"] = e["reason"].split(" Pre-freeze review 1, m8")[0] + cm.CITATION_MARK + f": {cite}."
                (folder / "w5b-cp5-pipeline.json").write_text(json.dumps(frag))
                got = [x for x in cm.problems(folder) if "near-rewrite" in x]
                if [x.split(" ", 1)[0] for x in got] != ["result.py"] or says not in got[0]:
                    out.append(f"{p}: a near-rewrite citing {why} reads {got}")
        # the closure check of 84ab6393, finding 2: one good citation never covers a bad one, and a commit outside
        # HEAD's history is no citation
        good = subprocess.run(["git", "-C", str(HERE), "log", "-1", "--format=%H", "--", "result.py"],
                              capture_output=True, text=True).stdout.strip()
        bad = "96c1d959932216ab9acd43003143348c9761a513"       # on HEAD's line, never touched result.py
        mixed = cm.citation_problem("result.py", f"x.{cm.CITATION_MARK}: {good[:12]}, {bad}.")
        if not mixed or "did not change it" not in mixed:
            out.append(f"{p}: a good citation covered a bad one: {mixed!r}")
        # the second closure check of 2971d1d7, minor 2: an owner's token outside this lane's citation sentence needs
        # only to be a commit in HEAD's history
        owner = cm.citation_problem("result.py", f"review of {bad}.{cm.CITATION_MARK}: {good[:12]}.")
        dangling = cm.citation_problem("result.py", f"review of deadbeefdeadbeef01.{cm.CITATION_MARK}: {good[:12]}.")
        bare = cm.citation_problem("result.py", f"edited by {good[:12]}.")
        if owner is not None or not dangling or "resolves to no commit" not in dangling or not bare:
            out.append(f"{p}: the citation scope reads owner {owner!r}, dangling {dangling!r}, no sentence {bare!r}")
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            git(repo, "init", "-q", "-b", "main")
            f = repo / "evals" / "gap-study-4" / "x.py"
            f.parent.mkdir(parents=True)
            shas = []
            for text in ("one\n", "two\n"):
                f.write_text(text)
                git(repo, "add", "-A")
                git(repo, "commit", "-q", "-m", text.strip())
                shas.append(git(repo, "rev-parse", "HEAD"))
            git(repo, "checkout", "-q", "-b", "side")
            f.write_text("three\n")
            git(repo, "add", "-A")
            git(repo, "commit", "-q", "-m", "side")
            side = git(repo, "rev-parse", "HEAD")
            git(repo, "checkout", "-q", "main")
            with mock.patch.object(cm, "REPO", repo):
                on = cm.citation_problem("x.py", f"x.{cm.CITATION_MARK}: {shas[1]}.")
                off = cm.citation_problem("x.py", f"x.{cm.CITATION_MARK}: {side}.")
                off_owner = cm.citation_problem("x.py", f"review of {side}.{cm.CITATION_MARK}: {shas[1]}.")
            if on is not None or not off or "outside HEAD's history" not in off or not off_owner or \
                    "outside HEAD's history" not in off_owner:
                out.append(f"{p}: a citation on HEAD's line reads {on!r}, one on another branch {off!r}, an "
                           f"owner's on another branch {off_owner!r}")
        # the five owners' sha citations are back, byte for byte as they stood before this lane's folds
        for frag, path in (("review-kit-port", "review_kit/BRIEF.md"),
                           ("w3c-cp3-graders-confound-newtasks", "graders/confounded_design.py"),
                           ("w8a-walk-layout", "copy_manifest.py"), ("w8b-holdout-digests", "build_draft.py")):
            then = json.loads(subprocess.run(["git", "-C", str(HERE), "show", f"96c1d959:evals/gap-study-4/COPIED.d/"
                                              f"{frag}.json"], capture_output=True, text=True).stdout)
            now = json.loads((HERE / "COPIED.d" / f"{frag}.json").read_text())
            was = next(e["reason"] for e in then["files"] if e["path"] == path)
            got = next(e["reason"] for e in now["files"] if e["path"] == path)
            if got.split(" Pre-freeze review 1, m8")[0] != was:
                out.append(f"{p}: {frag}'s reason for {path} is not its owner's words before this lane")
    except Exception as e:  # noqa: BLE001
        return [f"ERROR {p}: {type(e).__name__}: {str(e)[:240]}"]
    return out


REGISTER_LINE = "REGISTERED_ROUND: int | None = {}\n"


def beacon_history(values, *, docstring=(), draft_after=False):
    """A scratch repository with evals/gap-study-4/order_beacon.py and prereg-draft.json, one commit per value of
    REGISTERED_ROUND in `values` (the first with the draft), optional docstring lines naming rounds as bare lines in the
    first commit, and, with `draft_after`, one more commit that changes only the draft. Returns (repo, [shas],
    draft sha)."""
    tmp = tempfile.mkdtemp(prefix="pf1-witness-")
    repo = Path(tmp)
    git(repo, "init", "-q")
    study_dir = repo / "evals" / "gap-study-4"
    study_dir.mkdir(parents=True)
    shas = []
    for i, v in enumerate(values):
        doc = "".join(REGISTER_LINE.format(r) for r in docstring) if i == 0 else ""
        (study_dir / "order_beacon.py").write_text(f'"""Synthetic.\n{doc}"""\nx = 1\n' + REGISTER_LINE.format(v))
        if i == 0:
            (study_dir / "prereg-draft.json").write_text('{"synthetic": 1}\n')
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", f"value {v}")
        shas.append(git(repo, "rev-parse", "HEAD"))
    draft = shas[0]
    if draft_after:
        (study_dir / "prereg-draft.json").write_text('{"synthetic": 2}\n')
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "draft moved")
        draft = git(repo, "rev-parse", "HEAD")
    return repo, shas, draft


def g9b_witness(fz, ob, p="G9b.witness") -> list:
    out = []
    import inspect
    try:
        r1, r2 = ROUND, ROUND + 1
        early = ROUND_TIME - ob.WITNESS_LEAD_S - 600
        # (a) a docstring naming rounds is no registration: the round is the parsed assignment's value
        got = []
        for text in ('"""\nREGISTERED_ROUND: int | None = 5\n"""\nREGISTERED_ROUND: int | None = None\n',
                     "REGISTERED_ROUND: int | None = 7\n"):
            try:
                got.append(ob.registered_value(text))
            except ob.BeaconRefused as e:
                got.append(f"refused: {e}")
        if got != [None, 7]:
            out.append(f"{p}: registered_value does not read the module's assignment: {got}")
        for bad in ("REGISTERED_ROUND = 1 + 2\n", "x = 1\n", "REGISTERED_ROUND = 3\nREGISTERED_ROUND = 4\n",
                    "REGISTERED_ROUND = True\n"):
            try:
                ob.registered_value(bad)
                out.append(f"{p}: registered_value read {bad!r}")
            except ob.BeaconRefused:
                pass
        repo, shas, _ = beacon_history([None, r1], docstring=[r1, r2])
        with mock.patch.object(fz, "REPO", repo):
            try:
                got = fz.registering_commit(r1)
            except ValueError as e:
                got = f"refused: {e}"
            if got != shas[1]:
                out.append(f"{p}: the docstring commit registered round {r1}: {got}")
        # (b) the value changes once, from None to the round, and never again
        for name, values, rnd in (("set twice", [None, r1, r2, r1], r1), ("back to None and again", [None, r1, None,
                                  r1], r1), ("another round first", [None, r2, r1], r1), ("never None", [r1], r1),
                                  ("left at another round", [None, r2], r1)):
            repo, shas, _ = beacon_history(values)
            with mock.patch.object(fz, "REPO", repo):
                try:
                    got = fz.registering_commit(rnd)
                    out.append(f"{p}: a history {name} registered round {rnd} at {got}")
                except ValueError:
                    pass
        # (c) the draft's last commit is witnessed too, and the witness is written into the frozen file
        draft = registered(committed_draft())
        for name, after, pushed in (("a draft changed after the push", True, "first"), ("both held", False, "last")):
            repo, shas, dsha = beacon_history([None, r1], draft_after=after)
            head = git(repo, "rev-parse", "HEAD")
            push_sha = shas[-1] if pushed == "first" else head
            contains = lambda c, s, repo=repo: subprocess.run(   # noqa: E731
                ["git", "-C", str(repo), "merge-base", "--is-ancestor", c, s], capture_output=True).returncode == 0
            with mock.patch.object(fz, "REPO", repo):
                try:
                    w = fz.take_order_witness(draft, pushes=[(early, push_sha)], contains=contains)
                except ValueError:
                    w = None
            if after and w is not None:
                out.append(f"{p}: {name} passed")
            if not after:
                want = {"repo": ob.WITNESS_REPO, "host": "github.com", "registering_commit": shas[1],
                        "registering_push": {"sha": head, "stamp": early}, "draft_commit": dsha,
                        "draft_push": {"sha": head, "stamp": early}}
                if w != want:
                    out.append(f"{p}: the witness reads {w}, wanted {want}")
        if "take_order_witness" not in fz.FREEZE_WRITTEN_KEYS:
            out.append(f"{p}: the freeze does not write take_order_witness")
        if "review_commit" in inspect.signature(fz.take_order_beacon_reading).parameters:
            out.append(f"{p}: take_order_beacon_reading still takes an unused review commit")
        # the witness read is pinned to github.com
        seen = []
        fake = types.SimpleNamespace(returncode=0, stdout="", stderr="")
        with mock.patch.object(fz.subprocess, "run", lambda argv, **k: seen.append(argv) or fake), \
                mock.patch.dict(fz.os.environ, {"GH_HOST": "github.com"}):
            fz.push_records()
        if not seen or seen[0][:4] != ["gh", "api", "--hostname", "github.com"]:
            out.append(f"{p}: gh api is not pinned to github.com: {seen[:1]}")
        with mock.patch.dict(fz.os.environ, {"GH_HOST": "ghe.example.invalid"}):
            try:
                fz.push_records()
                out.append(f"{p}: a GH_HOST of another host was followed")
            except ValueError:
                pass
        for line in (ob.residual(), Path(__file__).read_text().split("G9.beacon", 1)[1].split("G2b.pending", 1)[0]):
            if "review committed at or after" in line or "fixed before its value exists" in line and \
                    "draft" not in line:
                out.append(f"{p}: a text claims what the code does not enforce: {line[:120]!r}")
    except Exception as e:  # noqa: BLE001
        return [f"ERROR {p}: {type(e).__name__}: {str(e)[:300]}"]
    return out


class Scratch:
    """A scratch repository holding evals/gap-study-4/order_beacon.py and prereg-draft.json, for branch histories."""

    def __init__(self):
        self.repo = Path(tempfile.mkdtemp(prefix="pf1-branches-"))
        git(self.repo, "init", "-q", "-b", "main")
        (self.repo / "evals" / "gap-study-4").mkdir(parents=True)

    def commit(self, *, round_no="keep", draft=None, other=None, msg="c") -> str:
        d = self.repo / "evals" / "gap-study-4"
        if round_no != "keep":
            (d / "order_beacon.py").write_text("x = 1\n" + REGISTER_LINE.format(round_no))
        if draft is not None:
            (d / "prereg-draft.json").write_text(json.dumps({"draft": draft}) + "\n")
        if other is not None:
            (d / "other.txt").write_text(other + "\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", msg)
        return git(self.repo, "rev-parse", "HEAD")

    def contains(self, commit, sha) -> bool:
        return subprocess.run(["git", "-C", str(self.repo), "merge-base", "--is-ancestor", commit, sha],
                              capture_output=True).returncode == 0


def g9c_branches(fz, ob, p="G9c.branches") -> list:
    """The closure check of 84ab6393, finding 1: candidates on parallel pushed branches, and a draft taken by a merge."""
    out = []
    try:
        r1, r2 = ROUND, ROUND + 1
        early = ROUND_TIME - ob.WITNESS_LEAD_S - 600
        draft = registered(committed_draft())

        def witness(sc, tips):
            with mock.patch.object(fz, "REPO", sc.repo):
                try:
                    return fz.take_order_witness(draft, pushes=[(early, t) for t in tips], contains=sc.contains)
                except ValueError as e:
                    return f"refused: {e}"

        # a candidate draft on another pushed branch, after the registering commit
        sc = Scratch()
        sc.commit(round_no=None, draft="v0")
        reg = sc.commit(round_no=r1)
        git(sc.repo, "branch", "candB")
        a = sc.commit(draft="A")
        git(sc.repo, "checkout", "-q", "candB")
        b = sc.commit(draft="B")
        git(sc.repo, "checkout", "-q", "main")
        got = witness(sc, [a, b])
        if not (isinstance(got, str) and "candidate draft on another pushed branch" in got):
            out.append(f"{p}: a candidate draft on a pushed branch is not refused: {got}")
        # another round registered on another pushed branch
        sc = Scratch()
        base = sc.commit(round_no=None, draft="v0")
        sc.commit(round_no=r1)
        tip = sc.commit(draft="A")
        git(sc.repo, "checkout", "-q", "-b", "candR", base)
        cand = sc.commit(round_no=r2)
        git(sc.repo, "checkout", "-q", "main")
        got = witness(sc, [tip, cand])
        if not (isinstance(got, str) and f"sets REGISTERED_ROUND to {r2}" in got):
            out.append(f"{p}: a round registered on a pushed branch is not refused: {got}")
        # the merge-late case: a merge takes the side branch's draft after the round
        sc = Scratch()
        sc.commit(round_no=None, draft="v0")
        sc.commit(round_no=r1)
        git(sc.repo, "branch", "candB")
        a = sc.commit(draft="A")
        git(sc.repo, "checkout", "-q", "candB")
        b = sc.commit(draft="B")
        git(sc.repo, "checkout", "-q", "main")
        git(sc.repo, "merge", "-q", "--no-ff", "-X", "theirs", "-m", "merge candB", "candB")
        merge = git(sc.repo, "rev-parse", "HEAD")
        with mock.patch.object(fz, "REPO", sc.repo):
            got = fz.draft_commit()
        if got != merge:
            out.append(f"{p}: a merge that took another line's draft is not the draft commit: {got[:12]}")
        got = witness(sc, [a, b])
        if not (isinstance(got, str) and "the draft commit" in got):
            out.append(f"{p}: the merge-late case (its merge never pushed before the round) is witnessed: {got}")
        # two candidate lines: both parents changed the draft to the same bytes, so the merge changes nothing
        sc = Scratch()
        sc.commit(round_no=None, draft="v0")
        sc.commit(round_no=r1)
        git(sc.repo, "branch", "candB")
        sc.commit(draft="same", msg="A")
        git(sc.repo, "checkout", "-q", "candB")
        sc.commit(draft="same", other="b", msg="B")
        git(sc.repo, "checkout", "-q", "main")
        git(sc.repo, "merge", "-q", "--no-ff", "-m", "merge candB", "candB")
        with mock.patch.object(fz, "REPO", sc.repo):
            try:
                got = fz.draft_commit()
                out.append(f"{p}: two candidate draft lines give draft_commit {got[:12]}")
            except ValueError as e:
                if "two candidate lines" not in str(e):
                    out.append(f"{p}: two candidate lines are refused for another reason: {e}")
        # a pushed sha this clone does not hold
        sc = Scratch()
        sc.commit(round_no=None, draft="v0")
        sc.commit(round_no=r1)
        tip = sc.commit(draft="A")
        got = witness(sc, [tip, "e" * 40])
        if not (isinstance(got, str) and "not in this clone" in got):
            out.append(f"{p}: a pushed sha missing from the clone is not refused: {got}")
        # the clean case: another lane's branch from before the registration, touching the draft, is no candidate
        sc = Scratch()
        base = sc.commit(round_no=None, draft="v0")
        reg = sc.commit(round_no=r1)
        tip = sc.commit(draft="A")
        git(sc.repo, "checkout", "-q", "-b", "other", base)
        other = sc.commit(draft="their own", other="x")
        git(sc.repo, "checkout", "-q", "main")
        got = witness(sc, [tip, other])
        want = {"repo": ob.WITNESS_REPO, "host": "github.com", "registering_commit": reg,
                "registering_push": {"sha": tip, "stamp": early}, "draft_commit": tip,
                "draft_push": {"sha": tip, "stamp": early}}
        if got != want:
            out.append(f"{p}: the clean case reads {got}")
        if "rewritten" in ob.residual().split("The remaining road", 1)[0] or \
                "a mirror whose history someone rewrites, or GitHub itself" not in ob.residual() or \
                "a deleted branch" not in ob.residual() or "goes unseen" not in ob.residual():
            out.append(f"{p}: the residual does not name the remaining road alone")
    except Exception as e:  # noqa: BLE001
        return [f"ERROR {p}: {type(e).__name__}: {str(e)[:300]}"]
    return out


def g10_nits(fz, wr, p="G10.nits") -> list:
    out = []
    try:
        if "review commit" in (fz.prepare.__doc__ or "").split("MAJOR 9", 1)[-1].split(".")[0]:
            out.append(f"{p}: prepare's docstring still puts the review commit in the seed")
        # 6: a pinned file with uncommitted edits is a --check failure
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            git(repo, "init", "-q")
            (repo / "a.txt").write_text("one\n")
            git(repo, "add", "-A")
            git(repo, "commit", "-q", "-m", "a")
            with mock.patch.object(fz, "REPO", repo):
                clean = fz.pin_problems([fz.pin("a.txt")])
                (repo / "a.txt").write_text("two\n")
                dirty = fz.pin_problems([fz.pin("a.txt")])
            if clean or not any("uncommitted edits" in x for x in dirty):
                out.append(f"{p}: a pinned file with uncommitted edits reads {dirty} (clean {clean})")
        # 7: a grade.json that does not parse counts as pending
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            git(repo, "init", "-q")
            (repo / "rehearsals" / "w-x1").mkdir(parents=True)
            (repo / "rehearsals" / "w-x1" / "grade.json").write_text("{not json")
            git(repo, "add", "-A")
            git(repo, "commit", "-q", "-m", "walk")
            problems, counts = wr.regrade_report(repo)
            if counts["pending"] != 1 or counts["pending_unregraded"] != ["w-x1"]:
                out.append(f"{p}: an unparseable grade.json is skipped: {counts}")
    except Exception as e:  # noqa: BLE001
        return [f"ERROR {p}: {type(e).__name__}: {str(e)[:300]}"]
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
            "G9b.witness": lambda: g9b_witness(m["freeze"], m["order_beacon"]),
            "G10.nits": lambda: g10_nits(m["freeze"], m["walk_regrade"]),
            "G9c.branches": lambda: g9c_branches(m["freeze"], m["order_beacon"]),
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
    "witness-repo-aegis": ("G9.beacon", "order_beacon", (('WITNESS_REPO = "javrodriguez/gars-cloud-mirror"\n',
                                                          'WITNESS_REPO = "javrodriguez/aegis"\n'),)),
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
    "run-gap-admitted": ("G4.coverage", "freeze", (("    if not gaps:\n        return None\n", "    return None\n"),)),
    "check-legs-ignored": ("G1.check", "freeze", (("    return 1 if bad else 0\n", "    return 0\n"),)),
    "coverage-leg-dropped": ("G1.check", "freeze", (('    legs.append(("walk coverage of the arms the freeze runs", '
                                                     '[problem] if problem else []))\n',
                                                     '    legs.append(("walk coverage of the arms the freeze runs", '
                                                     '[]))\n'),)),
    "walk-version-unchecked": ("G6.walkpins", "walk_pins", (('    if agent.get("version") != want or '
                                                             'ledger.get("claude_version") != want:\n',
                                                             "    if False:\n"),)),
    "walk-image-unchecked": ("G6.walkpins", "walk_pins", (("        if ids != [lock]:\n", "        if False:\n"),)),
    "outside-git-empty": ("G7.regrade", "walk_regrade", (("        return [NOT_A_REPOSITORY.format(study=study)]\n",
                                                          "        return []\n"),)),
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
    "docstring-registers": ("G9b.witness", "order_beacon", (("    found = []\n",
                                                            "    found = [ast.Constant(int(m)) for m in re.findall("
                                                            "r\"REGISTERED_ROUND: int \\| None = (\\d+)\", source)]\n"),)),
    # pre-freeze review 2, option A+ (lane fold2-lb): the history rule now reads [None, *superseded rounds, round_no]
    "history-unchecked": ("G9b.witness", "order_beacon", (("    if changes != [None, *rounds, round_no]:\n",
                                                          "    if round_no not in changes:\n"),)),
    "draft-unwitnessed": ("G9b.witness", "freeze", (('(("registering", registering), ("draft", draft_commit())):',
                                                     '(("registering", registering),):'),)),
    "host-unpinned": ("G9b.witness", "freeze", (('    got = subprocess.run(["gh", "api", "--hostname", WITNESS_HOST, '
                                                 '"--paginate",', '    got = subprocess.run(["gh", "api", "--paginate",'),)),
    "dirty-pin-admitted": ("G10.nits", "freeze", (('            out.append(f"{p[\'path\']}: uncommitted edits (its bytes '
                                                   'are not its HEAD blob)")\n', "            pass\n"),)),
    "unreadable-grade-skipped": ("G10.nits", "walk_regrade", (("            doc = None          # the review of "
                                                                "53d0e9af, NIT 7",
                                                                "            continue          # the review of "
                                                                "53d0e9af, NIT 7"),)),
    "citation-unresolved-admitted": ("G8.copies", "copy_manifest", (('            return f"its reason cites {t}, '
                                                                     'which resolves to no commit"\n',
                                                                     "            continue\n"),)),
    "copy-commit-admitted": ("G8.copies", "copy_manifest", (("    edits = set(history[:-1])",
                                                             "    edits = set(history)"),)),
    "foreign-round-admitted": ("G9c.branches", "freeze", (("        if value is not None:\n            return (f\"the "
                                                            "mirror holds", "        if False:\n            return (f\"the "
                                                            "mirror holds"),)),
    "foreign-draft-admitted": ("G9c.branches", "freeze", (("        if history_contains(registering, c):\n",
                                                           "        if False:\n"),)),
    "missing-push-admitted": ("G9c.branches", "freeze", (("    if missing:\n        return (f\"{len(missing)}",
                                                          "    if False:\n        return (f\"{len(missing)}"),)),
    "draft-lines-unchecked": ("G9c.branches", "freeze", (("    if apart:\n", "    if False:\n"),)),
    "citation-one-covers-all": ("G8.copies", "copy_manifest", (("        if must_edit and full not in edits:\n            return "
                                                               "f\"its reason cites {t}, which did not",
                                                               "        if False:\n            return "
                                                               "f\"its reason cites {t}, which did not"),)),
    "citation-off-head-admitted": ("G8.copies", "copy_manifest", (('        if git("merge-base", "--is-ancestor", '
                                                                   'full, "HEAD").returncode != 0:\n',
                                                                   "        if False:\n"),)),
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

    def test_g9b_the_round_and_the_draft_are_witnessed(self):
        self.check("G9b.witness")

    def test_g10_the_reviews_nits(self):
        self.check("G10.nits")

    def test_g9c_candidates_on_other_branches_are_refused(self):
        self.check("G9c.branches")


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
