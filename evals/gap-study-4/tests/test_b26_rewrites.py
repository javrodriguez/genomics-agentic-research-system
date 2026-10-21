#!/usr/bin/env python3
"""Lane vendor-b26 (Gap Study round 4): the Gemini history-rewrite roads glitch-26 ruled in on the B26 design
(lane-reports/vendor-b26-DESIGN.md), each with its refusal side.

Fixtures: tests/fixtures/b26-rewrites/, cut by its cut_structure.py from committed walks (w-g14, w-g32, w-g47) as
STRUCTURE ONLY (lane vendor-b25's cutter and four more rules); no model text, prompt, tool output or OD57 byte.

  ruling 1  the tool-output masking re-record (shape A) and the ignored-prompt resume (shape B): the two-layer replay,
            every fact read from the original messages; "tool outputs masked" a take property, never a fact;
  ruling 2  the loop-recovery feedback continues its interaction, never a sent line, on its exact pinned shape;
  ruling 3  the resume after a re-record, true compression and content truncation refuse by name;
  ruling 4  the scanner's copy of the session reads the originals a re-record masked;
  ruling 5  the image check: equal multisets per coalesced run, a repeated `_response` id's first occurrence counting
            its base gemini message's concatenated toolCalls results (glitch-26's ruled deviation);
  ruling 6  the Gemini history join requires each snapshot to be a byte prefix of the next;
  ruling 8  the $patch tightening: no top-level id, content or toolCalls; updates only in the writer's shape.

The fold of REVIEW-vendor-b26-04c4e77 (glitch-f1's rulings, 21 Oct 2026; the scanner witness of its MAJOR 1 is
tests/test_b26_scanner.py): FullCalls (ruling 2), ShapeBUpdateOnRemoved (ruling 3), UnobservedResumeShapes (ruling 4),
the lengthened off-closing loop case (ruling 5), RerecordListingCap (NIT 6).
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
for p in (HERE, HERE / "tests"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

FIX = Path(__file__).resolve().parent / "fixtures" / "b26-rewrites"
B25 = Path(__file__).resolve().parent / "fixtures" / "b25-real-shapes"
CONTEXT_ID = hashlib.sha256(b"environment-context").hexdigest()[:32]
MASK = "<tool_output_masked"


def fixture(name: str) -> bytes:
    return (FIX / name).read_bytes()


def lines(raw: bytes) -> list:
    return [json.loads(x) for x in raw.decode("utf-8").splitlines() if x.strip()]


def jl(recs) -> bytes:
    return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in recs).encode("utf-8")


def streams(walk: str, n: int) -> list:
    return [(FIX / f"{walk}-turn-{k}.jsonl").read_text(encoding="utf-8") for k in range(1, n + 1)]


def rm():
    import gemini_session_replay
    return gemini_session_replay


def gp():
    import gemini_projection
    return gemini_projection


def nrr():
    import native_reader_registration
    return native_reader_registration


def rerecord_index(recs) -> int:
    hits = [k for k, r in enumerate(recs) if "$patch" in r and "removeIds" in r["$patch"]
            and "orderIds" not in r["$patch"]]
    assert len(hits) == 1, hits
    return hits[0]


def run_of(recs, k):
    """The record indexes of the re-recorded run just before the re-record patch at k (its survivors)."""
    removed = set(recs[k]["$patch"]["removeIds"])
    start = max(j for j in range(k) if "$patch" in recs[j])
    return [j for j in range(start + 1, k) if "id" in recs[j] and "$set" not in recs[j] and recs[j]["id"] not in removed]


class Witness(unittest.TestCase):
    def refused(self, raw, why):
        with self.assertRaises((rm().ReplayRefused, gp().ProjectionRefused)) as cm:
            gp().project(raw)
        self.assertIn(why, str(cm.exception))

    def disagree(self, raw, walk, n, why):
        got = nrr().check_session(raw, streams(walk, n))
        self.assertEqual(got["status"], "DISAGREE", got)
        self.assertIn(why, got["why"])


class Rerecord(Witness):
    """Ruling 1, shape A: the masking re-record (red on the base: "unsupported native patch operation")."""

    def test_w_g47_replays_and_reads_facts_from_the_originals(self):
        recs = lines(fixture("w-g47-native-turn-2.jsonl"))
        got = rm().replay(jl(recs))
        k = rerecord_index(recs)
        images = {recs[j]["id"] for j in run_of(recs, k)}
        self.assertEqual(len(images), 200)
        self.assertTrue(images <= {m["id"] for m in got["messages"]}, "the loader's state holds the re-recorded run")
        self.assertFalse(images & {m["id"] for m in got["timeline"]}, "no re-recorded copy is ever a fact source")
        self.assertIn(CONTEXT_ID, {m["id"] for m in got["timeline"]})
        self.assertEqual(got["properties"]["history_rewrites"], 1)
        self.assertEqual(got["properties"]["tool_outputs_masked"], 40)

    def test_w_g47_projects_two_and_the_first_is_unchanged(self):
        one = gp().project(fixture("w-g47-native-turn-1.jsonl"))
        two = gp().project(fixture("w-g47-native-turn-2.jsonl"))
        self.assertEqual((len(one), len(two)), (1, 2))
        self.assertEqual(two[0], one[0], "the re-record changes no fact of interaction 1")

    def test_w_g14_projects_four_and_the_first_three_are_unchanged(self):
        three = gp().project(fixture("w-g14-native-turn-3.jsonl"))
        four = gp().project(fixture("w-g14-native-turn-4.jsonl"))
        self.assertEqual((len(three), len(four)), (3, 4))
        self.assertEqual(four[:3], three)

    def test_every_fixture_joins_its_streams_and_its_history(self):
        for walk, last in (("w-g47", 2), ("w-g14", 4), ("w-g32", 3)):
            with self.subTest(walk=walk):
                got = nrr().check_session(fixture(f"{walk}-native-turn-{last}.jsonl"), streams(walk, last))
                self.assertEqual((got["status"], got.get("interactions")), ("PASS", last), got)
                self.assertEqual(got["properties"]["history_rewrites"], 1)
                refs = [{"file": f"{walk}-native-turn-{n}.jsonl",
                         "sha256": hashlib.sha256(fixture(f"{walk}-native-turn-{n}.jsonl")).hexdigest()}
                        for n in (last - 1, last)]
                self.assertEqual(len(nrr().gemini_history(FIX, refs)), 2)

    def test_facts_come_from_the_originals(self):
        """An original's tool status edited before the re-record makes the join DISAGREE; the same kind of edit on
        the re-recorded copy only is refused by the image check."""
        recs = lines(fixture("w-g47-native-turn-2.jsonl"))
        k = rerecord_index(recs)
        j = next(j for j in range(k) if recs[j].get("type") == "gemini" and recs[j].get("toolCalls")
                 and recs[j]["toolCalls"][0].get("status") == "success")
        bad = copy.deepcopy(recs)
        bad[j]["toolCalls"][0]["status"] = "error"
        self.disagree(jl(bad), "w-g47", 2, "tool facts disagree")
        bad = copy.deepcopy(recs)
        first = run_of(bad, k)[0]
        bad[first]["content"][-1]["text"] = "synthetic text that differs"
        self.refused(jl(bad), "the user text differs")


class RerecordMutants(Witness):
    """Ruling 1, shape A's refusal side; each mutant on a real-shape fixture refuses with its own reason."""

    def setUp(self):
        self.recs = lines(fixture("w-g47-native-turn-2.jsonl"))
        self.k = rerecord_index(self.recs)
        self.run = run_of(self.recs, self.k)

    def mutate(self, edit):
        bad = copy.deepcopy(self.recs)
        edit(bad)
        return jl(bad)

    def test_m1_an_older_message_left_live(self):
        self.refused(self.mutate(lambda r: r[self.k]["$patch"]["removeIds"].pop(5)), "leaves an older message live")

    def test_m2_a_message_after_the_run_off_the_synthetic_shape(self):
        def edit(r):
            extra = dict(r[self.run[-1]], id="synthetic-extra-id", model="m")
            r.insert(self.k, extra)
        self.refused(self.mutate(edit), "recordSyntheticMessage shape")

    def test_m3_repeats_and_order(self):
        rem = self.recs[self.k]["$patch"]["removeIds"]
        plain = next(i for i in rem if not i.endswith("_response") and i != CONTEXT_ID)
        self.refused(self.mutate(lambda r: r[self.k]["$patch"]["removeIds"].append(plain)),
                     "repeats an id that is not")

        def swap(r):
            ids = r[self.k]["$patch"]["removeIds"]
            ids[3], ids[4] = ids[4], ids[3]
        self.refused(self.mutate(swap), "not the loader's order")

    def test_m4_orderids_on_a_rerecord(self):
        self.refused(self.mutate(lambda r: r[self.k]["$patch"].__setitem__(
            "orderIds", [r[j]["id"] for j in self.run])), "outside a resume")

    def test_m5_a_survivor_off_the_synthetic_shape(self):
        gem = next(j for j in self.run if self.recs[j]["type"] == "gemini")
        for why, edit in (("a model key", lambda m: m.__setitem__("model", "m")),
                          ("toolCalls", lambda m: m.__setitem__("toolCalls", [])),
                          ("non-empty thoughts", lambda m: m.__setitem__("thoughts", [{"subject": "s"}])),
                          ("a string content", lambda m: m.__setitem__("content", "x"))):
            with self.subTest(why=why):
                self.refused(self.mutate(lambda r: edit(r[gem])), "recordSyntheticMessage shape")

    def test_m6_the_image(self):
        gem = next(j for j in self.run if self.recs[j]["type"] == "gemini"
                   and any("functionCall" in p for p in self.recs[j]["content"]))
        usr = next(j for j in self.run if any("functionResponse" in p for p in self.recs[j]["content"])
                   and not any(MASK in json.dumps(p) for p in self.recs[j]["content"]))
        msk = next(j for j in self.run if any(MASK in json.dumps(p) for p in self.recs[j]["content"]))
        txt = next(j for j in self.run if self.recs[j]["type"] == "gemini"
                   and any(set(p) == {"text"} and p["text"] for p in self.recs[j]["content"]))

        def call_renamed(r):
            next(p for p in r[gem]["content"] if "functionCall" in p)["functionCall"]["id"] = "renamed-call"

        def response_changed(r):
            next(p for p in r[usr]["content"] if "functionResponse" in p)["functionResponse"]["response"] = {
                "output": "synthetic text that differs"}

        def mask_untagged(r):
            p = next(p for p in r[msk]["content"] if MASK in json.dumps(p))
            p["functionResponse"]["response"] = {"output": "untagged preview"}

        def model_text(r):
            next(p for p in r[txt]["content"] if set(p) == {"text"} and p["text"])["text"] = "differs"

        def split_run(r):
            r.insert(self.k, dict(r[self.run[-1]], id="synthetic-split-id"))
        for why, edit, reason in (("a call renamed", call_renamed, "function calls differ"),
                                  ("a response changed", response_changed, "neither one of its originals nor masked"),
                                  ("a masked part without the tag", mask_untagged, "neither one of its originals"),
                                  ("a model text changed", model_text, "the model text differs"),
                                  ("a role run split", split_run, "coalesced role runs differ")):
            with self.subTest(why=why):
                self.refused(self.mutate(edit), reason)

    def test_m7_dead_updates(self):
        survivor = self.recs[self.run[1]]["id"]
        for why, edit, reason in (
                ("on a survivor", lambda u: u.__setitem__("id", survivor), "not a dead toolCalls write"),
                ("a call its message lacks", lambda u: u["toolCalls"][0].__setitem__("id", "no-such-call"),
                 "names a call its message lacks"),
                ("carrying content", lambda u: u.__setitem__("content", []), "not a dead toolCalls write")):
            with self.subTest(why=why):
                self.refused(self.mutate(lambda r: edit(r[self.k]["$patch"]["updates"][0])), reason)

    def test_m9_a_retired_id_recorded_again(self):
        removed = self.recs[self.k]["$patch"]["removeIds"][1]
        original = next(r for r in self.recs if r.get("id") == removed and "type" in r)
        self.refused(self.mutate(lambda r: r.append(dict(original))), "retired native message id is recorded again")

    def test_m11_true_compression_refuses_by_name(self):
        """Source-built: the context turn survives the re-record (chunk-NR7L3FXV.js:337254-337292, :336356-336377)."""
        self.refused(self.mutate(lambda r: r[self.k]["$patch"]["removeIds"].remove(CONTEXT_ID)),
                     "native chat compression (the context turn survives a re-record)")


class RepeatedResponseRun(Witness):
    """Ruling 5's ruled deviation, on w-g14's re-record: the first occurrence of a repeated `_response` id counts its
    base gemini message's concatenated toolCalls results (chunk-NR7L3FXV.js:286158-286188). Each mutant on a run
    holding one is DISAGREE."""

    def setUp(self):
        self.recs = lines(fixture("w-g14-native-turn-4.jsonl"))
        self.k = rerecord_index(self.recs)
        run = run_of(self.recs, self.k)
        rem = Counter(self.recs[self.k]["$patch"]["removeIds"])
        self.assertTrue(any(n > 1 and i.endswith("_response") for i, n in rem.items()), "the fixture holds repeats")
        self.j = next(j for j in run if self.recs[j]["type"] == "user"
                      and max(Counter(p["functionResponse"]["id"] for p in self.recs[j]["content"]
                                      if "functionResponse" in p).values(), default=0) >= 4)
        self.other = next(j for j in run if j != self.j and self.recs[j]["type"] == "user"
                          and any("functionResponse" in p for p in self.recs[j]["content"]))

    def check(self, edit, why):
        bad = copy.deepcopy(self.recs)
        edit(bad)
        self.disagree(jl(bad), "w-g14", 4, why)

    def test_the_real_run_agrees(self):
        self.assertEqual(nrr().check_session(jl(self.recs), streams("w-g14", 4))["status"], "PASS")

    def test_one_part_too_many(self):
        self.check(lambda r: r[self.j]["content"].append(copy.deepcopy(r[self.j]["content"][0])), "id or count")

    def test_one_part_too_few(self):
        self.check(lambda r: r[self.j]["content"].pop(), "id or count")

    def test_a_result_from_a_different_call(self):
        def edit(r):
            r[self.j]["content"][0] = copy.deepcopy(next(p for p in r[self.other]["content"] if "functionResponse" in p))
        self.check(edit, "id or count")

    def test_a_repeat_on_a_non_response_id(self):
        rem = self.recs[self.k]["$patch"]["removeIds"]
        plain = next(i for i in rem if not i.endswith("_response") and i != CONTEXT_ID)
        self.check(lambda r: r[self.k]["$patch"]["removeIds"].append(plain), "repeats an id that is not")


class IgnoredPromptResume(Witness):
    """Ruling 1, shape B: w-g14's turn-4 resume drops turn 3's "/"-leading prompt (isIgnoredUserContent,
    chunk-NR7L3FXV.js:286096-286110); the prompt stays a fact and opens interaction 3."""

    def setUp(self):
        self.recs = lines(fixture("w-g14-native-turn-4.jsonl"))
        self.k = next(k for k, r in enumerate(self.recs) if "$patch" in r and set(r["$patch"]) == {
            "orderIds", "removeIds", "updates"})
        self.removed = self.recs[self.k]["$patch"]["removeIds"][0]

    def mutate(self, edit):
        bad = copy.deepcopy(self.recs)
        edit(bad[self.k]["$patch"], bad)
        return jl(bad)

    def test_the_removed_prompt_opens_interaction_3(self):
        facts = gp().project(jl(self.recs))
        prompt = next(r for r in self.recs if r.get("id") == self.removed)
        self.assertEqual(facts[2]["sent"], prompt["content"][0]["text"])
        self.assertTrue(facts[2]["sent"].startswith("/"))
        self.assertEqual(rm().replay(jl(self.recs))["properties"]["ignored_prompt_resumes"], 1)

    def test_m8_only_an_ignored_prompt_may_be_removed(self):
        users = [r for r in self.recs[:self.k] if r.get("type") == "user" and "id" in r]
        plain = next(r["id"] for r in users if r["id"] not in (self.removed, CONTEXT_ID)
                     and all(set(p) == {"text"} for p in r["content"]) and not r["content"][0]["text"].startswith("/"))
        rt = next(r["id"] for r in users if all("functionResponse" in p for p in r["content"])
                  and not r["id"].endswith("_response"))
        gem = next(r["id"] for r in self.recs[:self.k] if r.get("type") == "gemini")
        for why, ids, reason in (("a plain prompt", [plain], "not an ignored user prompt"),
                                 ("a tool-response turn", [rt], "not an ignored user prompt"),
                                 ("the context turn", [CONTEXT_ID], "not an ignored user prompt"),
                                 ("a gemini message", [gem], "not an ignored user prompt"),
                                 ("the prompt twice", [self.removed, self.removed], "distinct ids")):
            with self.subTest(why=why):
                self.refused(self.mutate(lambda p, r: p.__setitem__("removeIds", list(ids))), reason)

    def test_m8_outside_a_resume(self):
        def edit(p, r):
            sets = [j for j in range(self.k) if "$set" in r[j] and "sessionId" in r[j]["$set"]]
            r[sets[-1]] = {"$set": {"lastUpdated": r[sets[-1]]["$set"].get("lastUpdated", "2026-01-01T00:00:00Z")}}
        self.refused(self.mutate(edit), "outside a resume")

    def test_m10_the_originals_keep_their_order(self):
        def edit(p, r):
            order = p["orderIds"]
            a, b = order.index(CONTEXT_ID), next(i for i, x in enumerate(order) if x not in (CONTEXT_ID,)
                                                 and not x.endswith("_response"))
            order[a], order[b] = order[b], order[a]
        self.refused(self.mutate(edit), "order of original messages changed")


class LoopFeedback(Witness):
    """Ruling 2: the loop-recovery message (chunk-NR7L3FXV.js:348601-348609) continues its interaction."""

    def setUp(self):
        self.recs = lines(fixture("w-g32-native-turn-2.jsonl"))
        self.j = next(j for j, r in enumerate(self.recs) if r.get("type") == "user"
                      and isinstance(r.get("content"), list) and r["content"]
                      and str(r["content"][0].get("text", "")).startswith(gp().LOOP_OPEN))

    def test_w_g32_projects_three_and_the_feedback_is_never_sent(self):
        facts, props = gp().project_with_properties(fixture("w-g32-native-turn-3.jsonl"))
        self.assertEqual(len(facts), 3)
        self.assertEqual(props["loop_feedback_injected"], 1)
        self.assertFalse(any(f["sent"].startswith(gp().LOOP_OPEN) for f in facts))
        self.assertEqual(len(gp().project(jl(self.recs))), 2)

    def test_off_its_shape_refuses(self):
        def edit(fn):
            bad = copy.deepcopy(self.recs)
            fn(bad[self.j])
            return jl(bad)
        # Lane vendor-b26 fold (glitch-f1's ruling 5): longer than LOOP_OPEN + LOOP_CLOSE, so only the closing check
        # refuses it.
        other = gp().LOOP_OPEN + "x" * (len(gp().LOOP_CLOSE) + 10) + ". Other."
        self.assertGreater(len(other), len(gp().LOOP_OPEN) + len(gp().LOOP_CLOSE))
        for why, fn in (("another closing", lambda m: m["content"][0].__setitem__("text", other)),
                        ("two parts", lambda m: m["content"].append({"text": "more"})),
                        ("an added key", lambda m: m.__setitem__("displayContent", "x")),
                        ("an empty detail", lambda m: m["content"][0].__setitem__(
                            "text", gp().LOOP_OPEN + gp().LOOP_CLOSE))):
            with self.subTest(why=why):
                self.refused(edit(fn), "loop-recovery feedback message is off its pinned shape")

    def test_not_after_a_tool_response_turn_refuses(self):
        bad = copy.deepcopy(self.recs)
        bad.insert(self.j + 1, dict(bad[self.j], id="synthetic-second-feedback"))
        self.refused(jl(bad), "loop-recovery feedback message is off its pinned shape or place")


class B25ReviewGaps(Witness):
    """B25's review (REVIEW-vendor-b25-a76d86f.md) MINORs 2 and 3, on this lane's replay, where the copy check now lives."""

    def test_minor_2_an_original_with_a_key_its_copy_lacks(self):
        recs = lines((B25 / "w-g21-native-turn-2.jsonl").read_bytes())
        k = next(j for j, r in enumerate(recs) if r.get("id", "").endswith("_response") and "type" in r)
        original = next(j for j, r in enumerate(recs) if r.get("type") == "user" and r is not recs[k]
                        and not r["id"].endswith("_response") and r.get("content") == recs[k]["content"])
        bad = copy.deepcopy(recs)
        bad[original]["displayContent"] = "synthetic text"
        self.refused(jl(bad), "not the resumed copy")

    def test_minor_3_the_base_must_be_a_gemini_message(self):
        fr = [{"functionResponse": {"id": "c1", "name": "read_file", "response": {}}}]
        recs = [{"sessionId": "native-1", "projectHash": "project-1"},
                {"id": "u1", "type": "user", "content": [{"text": "x"}]},
                {"id": "u1_response", "type": "user", "content": fr},
                {"$patch": {"orderIds": ["u1", "u1_response", "u1_response"],
                            "updates": [{"id": "u1", "content": [{"text": "x"}]}]}}]
        with self.assertRaises(rm().ReplayRefused) as cm:
            rm().replay(jl(recs))
        self.assertIn("repeats an id that is not a <gemini id>_response turn", str(cm.exception))

    def test_minor_3_a_response_id_listed_at_most_twice(self):
        recs = lines((B25 / "w-g31-native-turn-3.jsonl").read_bytes())
        k = max(j for j, r in enumerate(recs) if "$patch" in r)
        order = recs[k]["$patch"]["orderIds"]
        twice = next(i for i, n in Counter(order).items() if n == 2)
        self.assertEqual(len(gp().project(jl(recs))), 3, "the real second resume, two listings, still reads")
        bad = copy.deepcopy(recs)
        bad[k]["$patch"]["orderIds"].append(twice)
        self.refused(jl(bad), "more than twice")


class FullCalls(Witness):
    """glitch-f1's ruling 2 (REVIEW-vendor-b26-04c4e77 MINOR 2): the image binds each function call in full (id, name
    and arguments). A re-recorded copy whose call differs from its original only in an argument is refused (red on
    04c4e774: admitted, and the scanner never read that argument)."""

    def test_an_argument_changed_in_a_copy_only(self):
        recs = lines(fixture("w-g47-native-turn-2.jsonl"))
        k = rerecord_index(recs)
        gem = next(j for j in run_of(recs, k) if recs[j]["type"] == "gemini"
                   and any("functionCall" in p for p in recs[j]["content"]))
        bad = copy.deepcopy(recs)
        call = next(p for p in bad[gem]["content"] if "functionCall" in p)["functionCall"]
        call["args"] = dict(call.get("args") or {}, synthetic_canary="/synthetic/canary/path")
        self.refused(jl(bad), "function calls differ")

    def test_the_real_copies_carry_their_originals_arguments(self):
        for walk, last in (("w-g47", 2), ("w-g14", 4), ("w-g32", 3)):
            with self.subTest(walk=walk):
                self.assertEqual(rm().replay(fixture(f"{walk}-native-turn-{last}.jsonl"))["properties"]
                                 ["history_rewrites"], 1)


class ShapeBUpdateOnRemoved(Witness):
    """glitch-f1's ruling 3 (MINOR 3): shape B never updates the prompt it removes; the writer patches content only for
    history turns (chunk-NR7L3FXV.js:287167-287183). Red on 04c4e774: admitted, the patched text frozen as `sent`."""

    def test_an_update_on_the_removed_prompt(self):
        recs = lines(fixture("w-g14-native-turn-4.jsonl"))
        k = next(k for k, r in enumerate(recs) if "$patch" in r and set(r["$patch"]) == {
            "orderIds", "removeIds", "updates"})
        removed = recs[k]["$patch"]["removeIds"][0]
        bad = copy.deepcopy(recs)
        bad[k]["$patch"]["updates"].append({"id": removed, "content": [{"text": "/synthetic patched prompt"}]})
        self.refused(jl(bad), "updates the prompt it removes")
        self.refused(jl(bad), "287167-287183")


class UnobservedResumeShapes(Witness):
    """glitch-f1's ruling 4 (MINOR 4, the orchestrator's 14:08 ruling): the three writer-possible resume shapes no walk
    shows stay refused, each by its own name, so a survey counts them (red on 04c4e774: generic or wrong reasons)."""

    def setUp(self):
        self.recs = lines(fixture("w-g14-native-turn-4.jsonl"))
        self.k = next(k for k, r in enumerate(self.recs) if "$patch" in r and set(r["$patch"]) == {
            "orderIds", "removeIds", "updates"})

    def shape(self, drop):
        bad = copy.deepcopy(self.recs)
        for key in drop:
            del bad[self.k]["$patch"][key]
        return jl(bad)

    def test_order_ids_alone(self):
        self.refused(self.shape(("removeIds", "updates")), "writer-possible resume shape {orderIds} (a resume")

    def test_order_ids_and_remove_ids(self):
        self.refused(self.shape(("updates",)), "writer-possible resume shape {orderIds, removeIds}")

    def test_remove_ids_and_updates_inside_a_resume(self):
        self.refused(self.shape(("orderIds",)), "writer-possible resume shape {removeIds, updates} inside a resume")

    def test_remove_ids_alone_inside_a_resume(self):
        """glitch-f1's ruling on the fold's question: {removeIds} alone inside a resume is named too (red on f7f868cf:
        the generic re-record reason)."""
        self.refused(self.shape(("orderIds", "updates")), "writer-possible resume shape {removeIds} alone inside a resume")

    def test_the_window_closes_at_the_resume_patch(self):
        """An updates-only resume patch closes the resume window, so a later patch is never read as a resume shape."""
        recs = [{"sessionId": "native-1", "projectHash": "project-1"},
                {"id": "u1", "type": "user", "content": [{"text": "x"}]},
                {"id": "a1", "type": "gemini", "content": [{"text": "y"}]},
                {"$set": {"sessionId": "native-1"}},
                {"$patch": {"updates": [{"id": "a1", "content": [{"text": "y"}]}]}},
                {"$patch": {"orderIds": ["u1", "a1"]}}]
        with self.assertRaises(rm().ReplayRefused) as cm:
            rm().replay(jl(recs))
        self.assertEqual(str(cm.exception), "unsupported native patch operation")


class RerecordListingCap(Witness):
    """NIT 6: inside a re-record a `_response` id is listed at most twice (gemini_session_replay.py, the re-record's
    cap); w-g14's re-record lists repeats, and a third listing refuses by that cap's own reason."""

    def test_a_third_listing_in_a_rerecord(self):
        recs = lines(fixture("w-g14-native-turn-4.jsonl"))
        k = rerecord_index(recs)
        twice = next(i for i, n in Counter(recs[k]["$patch"]["removeIds"]).items() if n == 2)
        bad = copy.deepcopy(recs)
        bad[k]["$patch"]["removeIds"].append(twice)
        self.refused(jl(bad), "native re-record lists a <gemini id>_response turn more than twice")


class Scanner(unittest.TestCase):
    """Ruling 4: check_take's copy of the session reads the original a re-record masked (base: VendorUnreadable)."""

    def test_a_masked_output_never_hides_its_original(self):
        import check_take
        raw = fixture("w-g47-native-turn-2.jsonl")
        recs = lines(raw)
        k = rerecord_index(recs)
        masked = next(p["functionResponse"] for j in run_of(recs, k) for p in recs[j]["content"]
                      if "functionResponse" in p and MASK in json.dumps(p))
        got = check_take._gemini_snapshot_records(raw, "session/native-turn-2.jsonl")
        parts = [ret.get("functionResponse") for _, _, ret in got if isinstance(ret, dict) and "functionResponse" in ret]
        unmasked = [r for r in parts if r.get("id") == masked["id"] and MASK not in json.dumps(r)]
        self.assertTrue(unmasked, "the original response of a masked call is read")
        tools = [ret for _, _, ret in got if isinstance(ret, dict) and "functionResponse" not in ret]
        self.assertTrue(tools, "the originals' toolCalls are read")


class SnapshotPrefix(unittest.TestCase):
    """Ruling 6: the Gemini history join requires each snapshot to be a byte prefix of the next."""

    def test_a_later_snapshot_that_is_not_an_extension_refuses(self):
        import drive
        one, two = (B25 / "w-g21-native-turn-1.jsonl").read_bytes(), (B25 / "w-g21-native-turn-2.jsonl").read_bytes()
        recs = lines(one)
        last = max(j for j, r in enumerate(recs) if "timestamp" in r and "type" in r)
        recs[last]["timestamp"] = "2026-01-01T00:00:00.000Z"      # not a fact: the facts still join
        edited = jl(recs)
        with tempfile.TemporaryDirectory() as tmp:
            for name, raw in (("native-turn-1.jsonl", edited), ("native-turn-2.jsonl", two)):
                (Path(tmp) / name).write_bytes(raw)
            refs = [{"file": n, "sha256": hashlib.sha256((Path(tmp) / n).read_bytes()).hexdigest()}
                    for n in ("native-turn-1.jsonl", "native-turn-2.jsonl")]
            import vendor_provenance as vp
            vp.session_history_facts("gemini", Path(tmp), [dict(r) for r in refs],
                                     readers={"gemini": nrr().gemini_reader})   # the facts alone still join
            with self.assertRaises(vp.ProvenanceRefused) as cm:
                nrr().gemini_history(Path(tmp), refs)
            self.assertIn("not a byte extension", str(cm.exception))
            got = drive.native_history_record("gemini", tmp, refs, readers={"gemini": nrr().gemini_reader})
            self.assertEqual(got["status"], "refused", got)
            self.assertIn("not a byte extension", got["why"])

    def test_the_real_pair_is_an_extension(self):
        one, two = (B25 / "w-g21-native-turn-1.jsonl").read_bytes(), (B25 / "w-g21-native-turn-2.jsonl").read_bytes()
        self.assertTrue(two.startswith(one))


class Tightening(unittest.TestCase):
    """Ruling 8: the pinned writer's one $patch (chunk-NR7L3FXV.js:287254-287265) never carries a top-level id."""

    def base(self):
        return [{"sessionId": "native-1", "projectHash": "project-1"},
                {"id": "u1", "type": "user", "content": [{"text": "x"}]},
                {"id": "a1", "type": "gemini", "content": "y", "toolCalls": [{"id": "t1", "name": "read_file",
                                                                               "args": {}}]}]

    def test_off_writer_patches_refuse(self):
        for why, patch, reason in (
                ("a well-formed direct patch", {"id": "a1", "content": [{"text": "z"}]}, "direct-id"),
                ("a direct patch beside updates", {"id": "a1", "content": [{"text": "z"}],
                                                   "updates": [{"id": "u1", "content": [{"text": "z"}]}]}, "direct-id"),
                ("a string content", {"updates": [{"id": "a1", "content": "z"}]}, "not a part array"),
                ("a string result", {"updates": [{"id": "a1", "toolCalls": [{"id": "t1", "result": "r"}]}]},
                 "not a part array"),
                ("one id twice", {"updates": [{"id": "u1", "content": []}, {"id": "u1", "content": []}]},
                 "name one message twice")):
            with self.subTest(why=why), self.assertRaises(rm().ReplayRefused) as cm:
                rm().replay(jl(self.base() + [{"$patch": patch}]))
            self.assertIn(reason, str(cm.exception))

    def test_the_writer_shapes_stay_admitted(self):
        fr = [{"functionResponse": {"id": "t1", "name": "read_file", "response": {"output": "r"}}}]
        got = rm().replay(jl(self.base() + [{"$patch": {"updates": [{"id": "a1", "content": [{"text": "z"}],
                                                                       "toolCalls": [{"id": "t1", "result": fr}]}]}}]))
        self.assertEqual(got["messages"][1]["toolCalls"][0]["result"], fr)


if __name__ == "__main__":
    unittest.main()
