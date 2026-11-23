#!/usr/bin/env python3
"""Lane vendor-b28 (Gap Study round 4; glitch-f1's B27 rulings 3 and 5, B27 DECISION O1-O8 and the rulings on
REVIEW-vendor-b28-DESIGN, 21 Oct 2026): road (a), the resume after a masking re-record, admitted on its exact observed
shapes, F-B26-9's window close, and what stays refused by name.

Fixtures: tests/fixtures/b28-road-a/, the RAW stub-model probe records (ruling O5; PROVENANCE.json): synthetic CLI output
of the pinned gemini-cli 0.64.0 against lane vendor-b27's scripted stub, never a study take. Each scenario's last
snapshot is stored once; snapshot k is rebuilt as its byte prefix and checked by sha256. F-B26-9's witness also reads
lane vendor-b26's committed structure-only fixtures (tests/fixtures/b26-rewrites/, real walks w-g47, w-g14, w-g32).

  RoadAReal        A1, A2, A3 and B2's masking span admitted, history joined, facts from the frozen originals, the
                   re-entered turns in `copies`, the scanner reading every copy;
  RoadAMutants     M1-M13 of the design plus the review's MINOR 4 additions, each refused by its own name;
  StillRefused     B1 and B2 (true compression) and C1 (truncation) by their names, C2 unchanged;
  FB269            the window closes at its first record that is neither the context turn nor a `_response` turn;
  Disjoint         the batch leaves the Codex reader as accepted (REVIEW-vendor-b28-DESIGN NIT 9);
  Fixtures         the fixtures are the probe's bytes and pass the B25/B26 leak check.

Interpreter state: the readers are imported in setUpModule (the study folder put on sys.path only if absent) and
tearDownModule puts sys.path back exactly as setUpModule found it (check_take's import adds entries of its own); modules
imported stay in sys.modules, as any lazy import does (none is removed or replaced: lane vendor-b27 stage 7); no test
changes os.environ or the cwd; temporary folders are removed.
"""
from __future__ import annotations

import copy
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
FIX = Path(__file__).resolve().parent / "fixtures" / "b28-road-a"
B26 = Path(__file__).resolve().parent / "fixtures" / "b26-rewrites"
CONTEXT_ID = hashlib.sha256(b"environment-context").hexdigest()[:32]
OD57_SHA256 = "0b85623f36eef7c6e7ca19c7900e865fd7ddbfe5853197b5c1d2e246d81df313"   # box/od57_rule.py RULED_LINES
_SAVED_PATH = []
rm = gp = nrr = ct = None

RETIRED = "a retired native message id is recorded again"
COMPRESSION = "native chat compression (the context turn survives a re-record)"
TRUNCATION = "a re-recorded function response is neither one of its originals nor masked"
OFF_SHAPE = "a re-entered context turn is off getInitialChatHistory's shape"
NOT_FIRST_RECORD = "a re-entered context turn is not the first record after its resume's $set {sessionId}"
AGAIN = "the context turn is recorded again while its resumed copy is live"
NOT_CONSUMED = "a context turn re-entered after a re-record is not consumed by its resume's {orderIds, removeIds, updates} patch"
NOT_FRONT = "the resumed context turn is not first after the resume's reorder"
NO_PATCH = "a context turn re-entered after a re-record without its resume's patch"
KEEPS = "a resume after a re-record keeps a re-recorded copy the CLI drops"
EXACTLY_ONE = "a resume after a re-record must drop exactly one re-recorded context copy"
NOT_IGNORED = "a resume after a re-record removes a re-recorded copy that is not ignored content"
RESUME_SHAPE = "writer-possible resume shape {removeIds, updates} inside a resume"
UNOBSERVED_OR = "writer-possible resume shape {orderIds, removeIds}"
SET_PENDING = "a $set between a re-entered context turn and its resume's patch"


def setUpModule():
    global rm, gp, nrr, ct
    _SAVED_PATH[:] = [list(sys.path)]
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    import check_take
    import gemini_projection
    import gemini_session_replay
    import native_reader_registration
    rm, gp, nrr, ct = gemini_session_replay, gemini_projection, native_reader_registration, check_take


def tearDownModule():
    # check_take's own import adds to sys.path too; the path is put back exactly as setUpModule found it
    if _SAVED_PATH:
        sys.path[:] = _SAVED_PATH.pop()


PROV = json.loads((FIX / "PROVENANCE.json").read_text(encoding="utf-8"))


def snaps(name: str) -> list:
    """The scenario's snapshots, each rebuilt as a byte prefix of the stored last one and checked by its sha256."""
    entry = PROV["probe"]["scenarios"][name]
    last = (FIX / entry["file"]).read_bytes()
    out = []
    for row in entry["snapshots"]:
        raw = last[:row["bytes"]]
        assert hashlib.sha256(raw).hexdigest() == row["sha256"], row["source"]
        out.append(raw)
    return out


def lines(raw: bytes) -> list:
    return [json.loads(x) for x in raw.decode("utf-8").split("\n") if x.strip()]


def jl(recs) -> bytes:
    return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in recs).encode("utf-8")


def props(raw: bytes) -> tuple:
    p = rm.replay(raw)["properties"]
    return (p["history_rewrites"], p["tool_outputs_masked"], p["ignored_prompt_resumes"], p["resumes_after_rerecord"])


def is_set_session(r) -> bool:
    return set(r) == {"$set"} and "sessionId" in r["$set"]


def road_a(recs, which=-1):
    """(s, c, p): the indexes of a road (a) resume's $set {sessionId}, its re-entered context record (the next record)
    and its {orderIds, removeIds, updates} patch."""
    hits = [k for k in range(len(recs) - 1) if is_set_session(recs[k]) and recs[k + 1].get("id") == CONTEXT_ID]
    s = hits[which]
    p = next(k for k in range(s, len(recs)) if "$patch" in recs[k] and set(recs[k]["$patch"]) == {
        "orderIds", "removeIds", "updates"})
    return s, s + 1, p


def history(snapshots: list):
    d = Path(tempfile.mkdtemp(prefix="b28h-"))
    try:
        refs = []
        for k, raw in enumerate(snapshots, 1):
            (d / f"native-turn-{k}.jsonl").write_bytes(raw)
            refs.append({"file": f"native-turn-{k}.jsonl", "sha256": hashlib.sha256(raw).hexdigest()})
        return nrr.gemini_history(d, refs)
    finally:
        shutil.rmtree(d, ignore_errors=True)


class Witness(unittest.TestCase):
    def refused(self, raw, why):
        with self.assertRaises(rm.ReplayRefused) as cm:
            rm.replay(raw)
        self.assertIn(why, str(cm.exception))


class RoadAReal(Witness):
    """The four observed road (a) spans (B27 EN: A1 r70/r113, A2 r91, A3 r77, B2 r70), admitted (red on 5457e75e:
    the retired-id refusal)."""

    def test_a1_every_snapshot_and_the_history(self):
        s = snaps("A1")
        self.assertEqual([props(x) for x in s], [(1, 2, 0, 0), (2, 5, 0, 1), (2, 5, 0, 2)])
        self.assertEqual(len(history(s)), 3)

    def test_a2_every_snapshot_and_the_history(self):
        s = snaps("A2")
        self.assertEqual([props(x) for x in s], [(0, 0, 0, 0), (1, 2, 0, 0), (2, 5, 0, 1)])
        self.assertEqual(len(history(s)), 3)

    def test_a3_every_snapshot_and_the_history(self):
        s = snaps("A3")
        self.assertEqual([props(x) for x in s], [(0, 0, 0, 0), (1, 7, 0, 0), (2, 9, 0, 1)])
        self.assertEqual(len(history(s)), 3)

    def test_b2_masking_span_is_admitted(self):
        """B2 records 1-112 (EN: H A0 L ... S(69) A-ctx(70) A-resp(71) P-resume(72) L, C×16 P-mask(106) L, U G T(112))."""
        recs = lines(snaps("B2")[-1])
        self.assertEqual(props(jl(recs[:112])), (2, 5, 0, 1))

    def test_facts_come_from_the_frozen_original_context_turn(self):
        raw = snaps("A1")[-1]
        recs = lines(raw)
        got = rm.replay(raw)
        self.assertEqual(got["timeline"][0], recs[1], "the timeline opens with the original context record (record 2)")
        reentries = [recs[k + 1] for k in range(len(recs) - 1) if is_set_session(recs[k])
                     and recs[k + 1].get("id") == CONTEXT_ID]
        self.assertEqual(len(reentries), 2)
        for r in reentries:
            self.assertNotEqual(r, recs[1])
            self.assertIn(r, got["copies"], "each re-entered context turn is a copy")
            self.assertNotIn(r, got["timeline"])

    def test_the_projection_keeps_every_earlier_interaction(self):
        for name in ("A1", "A2", "A3"):
            with self.subTest(name=name):
                facts = [gp.project(x) for x in snaps(name)]
                for k in range(1, len(facts)):
                    self.assertEqual(facts[k][:len(facts[k - 1])], facts[k - 1])

    def test_the_scanner_reads_every_original_and_every_copy(self):
        raw = snaps("A1")[-1]
        got = rm.replay(raw)
        wheres = {w for w, _, _ in ct._gemini_snapshot_records(raw, "s")}
        live = {m["id"] for m in got["messages"]}
        frozen = [m for m in got["timeline"] if m["id"] not in live and m.get("toolCalls")]
        self.assertTrue(frozen)
        for m in frozen:
            for i in range(len(m["toolCalls"])):
                self.assertIn(f"s message {m['id']!r} tool {i + 1}", wheres)
        turns = [m for m in got["copies"] if m["type"] == "user" and isinstance(m["content"], list) and m["content"]
                 and all(set(p) == {"functionResponse"} for p in m["content"])]
        self.assertTrue(turns)
        for m in turns:
            for i in range(len(m["content"])):
                self.assertIn(f"s message {m['id']!r} response {i + 1}", wheres)

    def test_the_context_wrapper_is_the_projection_s(self):
        self.assertEqual((rm.CONTEXT_OPEN, rm.CONTEXT_CLOSE), (gp.ENV_CONTEXT_OPEN, gp.ENV_CONTEXT_CLOSE))
        self.assertEqual(rm.CONTEXT_ID, gp.ENV_CONTEXT_ID)


class RoadAMutants(Witness):
    """Each mutant on a probe fixture refuses by its own name (design section 4; REVIEW-vendor-b28-DESIGN MINOR 4).
    A1 is snapshot 2 (re-entry at record 70, patch at 72); A2 is snapshot 3 (re-entry 91, patch 93)."""

    def setUp(self):
        self.a1 = lines(snaps("A1")[1])
        self.s, self.c, self.p = road_a(self.a1)
        self.assertEqual((self.s, self.c, self.p), (68, 69, 71))       # records 69, 70, 72 (EN)

    def mutate(self, edit, recs=None):
        recs = copy.deepcopy(self.a1 if recs is None else recs)
        edit(recs)
        return jl(recs)

    def text(self, r):
        return r[self.c]["content"][0]

    def test_unmutated_a1_snapshot_2_passes(self):
        self.assertEqual(props(jl(self.a1)), (2, 5, 0, 1))

    def test_m1_no_set_session_before_the_reentry(self):
        self.refused(self.mutate(lambda r: r.pop(self.s)), RETIRED)

    def test_m2_reentry_with_an_extra_key(self):
        self.refused(self.mutate(lambda r: r[self.c].__setitem__("displayContent", "x")), OFF_SHAPE)

    def test_m3_reentry_with_two_parts(self):
        self.refused(self.mutate(lambda r: r[self.c]["content"].append({"text": "x"})), OFF_SHAPE)

    def test_m3b_reentry_typed_gemini(self):
        self.refused(self.mutate(lambda r: r[self.c].__setitem__("type", "gemini")), OFF_SHAPE)

    def test_m3c_reentry_content_a_string(self):
        self.refused(self.mutate(lambda r: r[self.c].__setitem__("content", r[self.c]["content"][0]["text"])),
                     OFF_SHAPE)

    def test_m3g_reentry_content_a_one_key_object(self):
        self.refused(self.mutate(lambda r: r[self.c].__setitem__("content", {"text": "x"})), OFF_SHAPE)

    def test_m3d_reentry_text_not_opening_the_wrapper(self):
        self.refused(self.mutate(lambda r: self.text(r).__setitem__("text", self.text(r)["text"][1:])), OFF_SHAPE)

    def test_m3e_reentry_text_not_closing_the_wrapper(self):
        self.refused(self.mutate(lambda r: self.text(r).__setitem__("text", self.text(r)["text"][:-1])), OFF_SHAPE)

    def test_m3f_reentry_part_with_an_extra_key(self):
        self.refused(self.mutate(lambda r: self.text(r).__setitem__("thought", False)), OFF_SHAPE)

    def test_m3h_reentry_wrapper_second_line_altered(self):
        """REVIEW-vendor-b28-eeeed34 MINOR 2: the whole opening line pair of the wrapper is bound, not its first tag."""
        def alter(r):
            t = self.text(r)["text"]
            self.assertIn("This is the Gemini CLI.", t)
            self.text(r)["text"] = t.replace("This is the Gemini CLI.", "This is the Gemini KLI.", 1)
        self.refused(self.mutate(alter), OFF_SHAPE)

    def test_m15_a_second_set_session_after_the_reentry(self):
        """REVIEW-vendor-b28-eeeed34 NIT 4 (glitch-f1: default deny): the writer writes the re-entry and its patch in one
        initialize call, so no $set falls between them."""
        sid = self.a1[0]["sessionId"]
        self.refused(self.mutate(lambda r: r.insert(self.c + 1, {"$set": {"sessionId": sid}})), SET_PENDING)

    def test_m15b_a_set_last_updated_right_before_the_patch(self):
        ts = self.a1[self.c]["timestamp"]
        self.refused(self.mutate(lambda r: r.insert(self.p, {"$set": {"lastUpdated": ts}})), SET_PENDING)

    def test_m4_the_context_record_twice_in_one_resume(self):
        self.refused(self.mutate(lambda r: r.insert(self.c + 1, copy.deepcopy(r[self.c]))), AGAIN)

    def test_m4b_the_consumed_copy_upserted_after_its_patch(self):
        self.refused(self.mutate(lambda r: r.insert(self.p + 1, copy.deepcopy(r[self.c]))), AGAIN)

    def test_m4c_reentry_after_the_response_copy(self):
        def swap(r):
            self.assertTrue(r[self.c + 1]["id"].endswith("_response"))
            r[self.c], r[self.c + 1] = r[self.c + 1], r[self.c]
        self.refused(self.mutate(swap), NOT_FIRST_RECORD)

    def test_m14_a_new_turn_between_the_reentry_and_its_patch(self):
        """REVIEW-vendor-b28-DESIGN MINOR 2: once a new turn closes the window (F-B26-9) the pending re-entry still
        refuses any later patch by the pending name, not as a reorder outside a resume."""
        new = {"id": "synthetic-new-turn", "timestamp": self.a1[self.c]["timestamp"], "type": "user",
               "content": [{"text": "synthetic"}]}
        self.refused(self.mutate(lambda r: r.insert(self.c + 1, new)), NOT_CONSUMED)

    def test_m5_patch_without_remove_ids(self):
        self.refused(self.mutate(lambda r: r[self.p]["$patch"].pop("removeIds")), NOT_CONSUMED)

    def test_m6_context_id_moved_last(self):
        def last(r):
            o = r[self.p]["$patch"]["orderIds"]
            self.assertEqual(o[0], CONTEXT_ID)
            r[self.p]["$patch"]["orderIds"] = o[1:] + [CONTEXT_ID]
        self.refused(self.mutate(last), NOT_FRONT)

    def test_m7_snapshot_cut_right_after_the_reentry(self):
        self.refused(jl(copy.deepcopy(self.a1[:self.c + 1])), NO_PATCH)

    def test_m8_patch_without_updates(self):
        self.refused(self.mutate(lambda r: r[self.p]["$patch"].pop("updates")), UNOBSERVED_OR)

    def _a2(self):
        recs = lines(snaps("A2")[2])
        s, c, p = road_a(recs)
        self.assertEqual((s, c, p), (89, 90, 92))                       # records 90, 91, 93 (EN)
        first = {}
        for k, r in enumerate(recs):
            if "id" in r and r["id"] not in first:
                first[r["id"]] = k
        remove = recs[p]["$patch"]["removeIds"]
        texts = {i: "".join(x.get("text", "") for x in recs[first[i]]["content"]).strip() for i in remove}
        ctx = [i for i in remove if texts[i].startswith("<session_context>")]
        slash = [i for i in remove if texts[i].startswith("/")]
        self.assertEqual((len(remove), len(ctx), len(slash)), (2, 1, 1))
        return recs, p, ctx[0], slash[0]

    def test_m9_a2_keeps_the_slash_copy(self):
        recs, p, ctx, slash = self._a2()

        def keep(r):
            r[p]["$patch"]["removeIds"].remove(slash)
            r[p]["$patch"]["orderIds"].insert(1, slash)
        self.refused(self.mutate(keep, recs), KEEPS)

    def test_m10_a2_removes_only_the_slash_copy(self):
        recs, p, ctx, slash = self._a2()

        def only(r):
            r[p]["$patch"]["removeIds"].remove(ctx)
            r[p]["$patch"]["orderIds"].insert(1, ctx)
        self.refused(self.mutate(only, recs), EXACTLY_ONE)

    def test_m11_a2_also_removes_a_function_response_copy(self):
        recs, p, ctx, slash = self._a2()
        k = max(j for j in range(p) if "$patch" in recs[j] and set(recs[j]["$patch"]) <= {"removeIds", "updates"})
        prev = max(j for j in range(k) if "$patch" in recs[j])
        removed = set(recs[k]["$patch"]["removeIds"])
        fr = next(recs[j]["id"] for j in range(prev + 1, k) if "id" in recs[j] and recs[j]["id"] not in removed
                  and recs[j]["type"] == "user" and isinstance(recs[j]["content"], list)
                  and all(set(x) == {"functionResponse"} for x in recs[j]["content"]))

        def more(r):
            r[p]["$patch"]["removeIds"].append(fr)
            r[p]["$patch"]["orderIds"] = [i for i in r[p]["$patch"]["orderIds"] if i != fr]
        self.refused(self.mutate(more, recs), NOT_IGNORED)

    def test_a2_a_gemini_copy_whose_text_starts_with_a_slash_stays_admitted(self):
        """REVIEW-vendor-b28-eeeed34 MINOR 2: convertSessionToClientHistory drops only user messages with ignored text
        (:286105-286110), so a re-recorded gemini copy whose model text starts with "/" is kept and must not be demanded
        by the completeness rule. The text is changed consistently in every record holding it, so the re-records'
        image checks still hold."""
        recs, p, ctx, slash = self._a2()
        k = max(j for j in range(p) if "$patch" in recs[j] and set(recs[j]["$patch"]) <= {"removeIds", "updates"})
        prev = max(j for j in range(k) if "$patch" in recs[j])
        removed = set(recs[k]["$patch"]["removeIds"])
        live_at_p = set(recs[p]["$patch"]["orderIds"])
        copy_rec = next(recs[j] for j in range(prev + 1, k) if "id" in recs[j] and recs[j]["id"] not in removed
                        and recs[j]["id"] in live_at_p and recs[j]["type"] == "gemini"
                        and isinstance(recs[j]["content"], list) and recs[j]["content"]
                        and all(set(x) == {"text"} and x["text"] for x in recs[j]["content"]))
        old = copy_rec["content"][0]["text"]

        def swap(v):
            if isinstance(v, dict):
                return {k2: swap(x) for k2, x in v.items()}
            if isinstance(v, list):
                return [swap(x) for x in v]
            return "/" + old if v == old else v
        bad = [swap(r) for r in recs]
        self.assertEqual(sum(json.dumps(r).count(json.dumps("/" + old)) for r in bad) >= 2, True)
        self.assertEqual(props(jl(bad)), (2, 5, 0, 1))

    def test_ignored_copy_reads_user_copies_with_text_only(self):
        """REVIEW-vendor-b28-eeeed34 MINOR 2, each conjunct of _ignored_copy on its own: a user copy with no content
        and a gemini copy with ignored-looking text are not content the CLI drops; a user "/" copy is."""
        r = rm._Replay({"sessionId": "s", "projectHash": "p"})
        r.live = {"empty": {"id": "empty", "type": "user", "content": []},
                  "model": {"id": "model", "type": "gemini", "content": [{"text": "/srv is the path"}]},
                  "slash": {"id": "slash", "type": "user", "content": [{"text": "/srv is the path"}]}}
        r.kind = {i: rm.RERECORDED for i in r.live}
        self.assertEqual([r._ignored_copy(i) for i in ("empty", "model", "slash")], [False, False, True])

    def test_m13_a_retired_copy_id_reappended_inside_the_window(self):
        """A1 snapshot 3: the second resume (re-entry at record 113); the re-record at 106 retired the first resume's
        `_response` copy (record 71), which is re-appended inside the open window, right after the re-entry."""
        a1 = lines(snaps("A1")[2])
        s, c, p = road_a(a1)
        self.assertEqual((s, c, p), (111, 112, 113))                    # records 112, 113, 114 (EN)
        k = max(j for j in range(s) if "$patch" in a1[j] and "orderIds" not in a1[j]["$patch"])
        gone = next(i for i in a1[k]["$patch"]["removeIds"] if i.endswith("_response"))
        rec = next(r for r in a1 if r.get("id") == gone)
        self.refused(self.mutate(lambda r: r.insert(c + 1, copy.deepcopy(rec)), a1), RETIRED)


class F4Witnesses(Witness):
    """REVIEW-b28-gemini-reader-854f6c3 MINOR 1 and NITs 2-3 (the F4 reviewer's witnesses, scratch wit_f4.py, folded):
    each binds one default-deny conjunct no other test reached."""

    def setUp(self):
        self.a1 = lines(snaps("A1")[1])
        self.s, self.c, self.p = road_a(self.a1)

    def state(self, live, kinds):
        r = rm._Replay({"sessionId": "s", "projectHash": "p"})
        r.live, r.kind, r.ctx_pending = live, kinds, True
        return r

    def test_w22_a_set_last_updated_between_the_set_session_and_the_reentry(self):
        """resume_at comes from $set {sessionId} alone (the writer writes S then A-ctx, EN)."""
        r = copy.deepcopy(self.a1)
        r.insert(self.c, {"$set": {"lastUpdated": self.a1[self.c]["timestamp"]}})
        self.refused(jl(r), NOT_FIRST_RECORD)

    def test_w3_two_context_copies_removed(self):
        """The upper bound of "exactly one re-recorded context copy" (design section 3: "drops ... two")."""
        st = self.state({"c1": {"id": "c1", "type": "user", "content": [{"text": "<session_context>\na"}]},
                         "c2": {"id": "c2", "type": "user", "content": [{"text": "<session_context>\nb"}]}},
                        {"c1": rm.RERECORDED, "c2": rm.RERECORDED})
        with self.assertRaises(rm.ReplayRefused) as cm:
            st._context_copies(["c1", "c2"])
        self.assertIn(EXACTLY_ONE, str(cm.exception))

    def test_w19_a_pending_patch_still_checks_removed_originals(self):
        st = self.state({"o": {"id": "o", "type": "user", "content": [{"text": "a real prompt"}]},
                         "c1": {"id": "c1", "type": "user", "content": [{"text": "<session_context>\na"}]}},
                        {"o": rm.ORIGINAL, "c1": rm.RERECORDED})
        with self.assertRaises(rm.ReplayRefused) as cm:
            st._ignored_prompts(["c1", "o"])
        self.assertIn("a resume removes a message that is not an ignored user prompt", str(cm.exception))

    def test_w13_w15_ignored_copy_part_keys_and_whitespace(self):
        """W13: a part with an extra key is not ignored content; W15 (NIT 2): whitespace-only text is, as
        isIgnoredUserContent reads a trimmed length of 0 (:286096-286098)."""
        st = self.state({"x": {"id": "x", "type": "user", "content": [{"text": "/x", "thoughtSignature": "s"}]},
                         "w": {"id": "w", "type": "user", "content": [{"text": " \n "}]}},
                        {"x": rm.RERECORDED, "w": rm.RERECORDED})
        self.assertEqual((st._ignored_copy("x"), st._ignored_copy("w")), (False, True))

    def test_w17_reentry_text_part_not_a_string(self):
        """NIT 2: refused by name, never a crash."""
        r = copy.deepcopy(self.a1)
        r[self.c]["content"] = [{"text": 5}]
        self.refused(jl(r), OFF_SHAPE)

    def test_w18_an_original_context_upsert_reads_as_before_the_batch(self):
        """NIT 2: the live-copy guard is for the CONTEXT_COPY only; an upsert of the ORIGINAL context id is admitted
        exactly as at 5457e75e (a replace, Map.set)."""
        ctx = next(x for x in self.a1 if x.get("id") == CONTEXT_ID)
        rm.replay(jl([self.a1[0], ctx, copy.deepcopy(ctx)]))

    def test_w27_an_updates_patch_while_pending_refuses_by_the_pending_name(self):
        """NIT 3: without the pending refusal an {updates} patch would end refused only at the snapshot's end."""
        r = copy.deepcopy(self.a1)
        r[self.p]["$patch"] = {"updates": r[self.p]["$patch"]["updates"]}
        self.refused(jl(r), NOT_CONSUMED)


class StillRefused(Witness):
    """Roads (b) and (c) stay refused by name (glitch-f1's B27 rulings 1 and 2)."""

    def test_b1_true_compression(self):
        """B1 moves from the resume-shape name to the compression name by F-B26-9's window close alone."""
        for k, raw in enumerate(snaps("B1")[1:], 2):
            with self.subTest(snapshot=k):
                self.refused(raw, COMPRESSION)

    def test_b2_compression_after_a_road_a_reentry(self):
        """B2 reaches the compression name through the road (a) re-entry at record 114, F-B26-9's close at 115 and the
        re-record's own checks run before the pending-patch refusal (REVIEW-vendor-b28-DESIGN MINORs 2 and 6)."""
        for k, raw in enumerate(snaps("B2")[1:], 2):
            with self.subTest(snapshot=k):
                self.refused(raw, COMPRESSION)

    def test_c1_truncation(self):
        for k, raw in enumerate(snaps("C1")[1:], 2):
            with self.subTest(snapshot=k):
                self.refused(raw, TRUNCATION)

    def test_c2_unchanged(self):
        s = snaps("C2")
        self.assertEqual([props(x) for x in s], [(0, 0, 0, 0), (1, 0, 0, 0)])
        self.assertEqual(len(history(s)), 2)


class FB269(Witness):
    """F-B26-9 (glitch-f1's 15:45 ruling, 21 Oct): the B26 closure reviewer's construction, $set {sessionId} inserted after the
    last $patch before the re-record, on the three real fixtures (red on 5457e75e: the resume-shape name). The inserted
    record changes nothing: the window closes at the next new turn."""

    def test_the_three_real_walks(self):
        for name in ("w-g47-native-turn-2.jsonl", "w-g14-native-turn-4.jsonl", "w-g32-native-turn-3.jsonl"):
            with self.subTest(name=name):
                raw = (B26 / name).read_bytes()
                recs = lines(raw)
                rr = max(k for k, r in enumerate(recs) if "$patch" in r and "orderIds" not in r["$patch"]
                         and "removeIds" in r["$patch"])
                last = max(k for k in range(rr) if "$patch" in recs[k])
                bad = recs[:last + 1] + [{"$set": {"sessionId": recs[0]["sessionId"]}}] + recs[last + 1:]
                self.assertEqual(props(jl(bad)), props(raw))
                self.assertEqual(props(raw)[0], 1)


class Disjoint(unittest.TestCase):
    """REVIEW-vendor-b28-DESIGN NIT 9: the batch changes a Gemini-only reader source, and the Codex reader's sources
    still hash to its accepted record's value (native-readers/codex-acceptance.json)."""

    def test_the_changed_source_is_gemini_only(self):
        self.assertIn("gemini_session_replay.py", nrr.READER_SOURCES)
        self.assertNotIn("gemini_session_replay.py", nrr.CODEX_SOURCES)

    def test_the_codex_sources_are_as_accepted(self):
        record = json.loads((HERE / nrr.CODEX_ACCEPTANCE_FILE).read_text(encoding="utf-8"))
        self.assertEqual(nrr.reader_sources_sha256(HERE, sources=nrr.CODEX_SOURCES), record["reader_sources_sha256"])


class Fixtures(unittest.TestCase):
    """The fixtures are the probe's bytes (PROVENANCE.json) and carry nothing the B25/B26 leak check refuses."""

    def test_every_snapshot_rebuilds_to_its_recorded_sha256(self):
        for name in PROV["probe"]["scenarios"]:
            with self.subTest(name=name):
                self.assertEqual(len(snaps(name)), len(PROV["probe"]["scenarios"][name]["snapshots"]))

    def test_both_b27_heads_are_named(self):
        self.assertEqual(PROV["probe"]["b27_head"], "82da1830fa7dab843287ee0bd1efd91fd7946497")
        self.assertEqual(PROV["b27_merged_head"], "49c350a9b008e3ea15f83f3873fe62b3766722fe")
        self.assertIn("55d3382298bdb8cd3a539741f733f296127860bff44d520f21ff80f16be3c99d", PROV["b27_head_note"])

    def test_no_od57_line_and_no_dummy_key(self):
        def strings(v):
            if isinstance(v, dict):
                for x in v.values():
                    yield from strings(x)
            elif isinstance(v, list):
                for x in v:
                    yield from strings(x)
            elif isinstance(v, str):
                yield v
        sha = lambda b: hashlib.sha256(b).hexdigest()
        for f in sorted(FIX.glob("*.jsonl")):
            raw = f.read_bytes()
            self.assertNotIn(b"dummydummy", raw, f.name)
            for line in raw.split(b"\n"):
                self.assertNotIn(OD57_SHA256, (sha(line), sha(line + b"\n")), f.name)
                if line.strip():
                    for s in strings(json.loads(line)):
                        for part in [s] + s.split("\n"):
                            self.assertNotEqual(sha(part.encode()), OD57_SHA256, f.name)


if __name__ == "__main__":
    unittest.main()
