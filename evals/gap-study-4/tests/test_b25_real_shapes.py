#!/usr/bin/env python3
"""Lane vendor-b25 (Gap Study round 4): the real-walk shapes the two reader reviews found, and a witness for each
admission's refusal side.

Fixtures: tests/fixtures/b25-real-shapes/, cut by its cut_structure.py from committed walks (w-o46, w-g21, w-g31) as
STRUCTURE ONLY: keys, order, ids, types, numbers, tool names, statuses, model names and the pinned sources' enum
values; every other string is "synthetic text <n>". No model text, prompt, tool output or OD57 byte is in them.

  Codex   ruling 1: world_state and thread_settings_applied on closed shapes, carrying no fact;
          ruling 2: the join binds each turn's recorded prompt and requested model to the launch side.
  Gemini  ruling 3: the resume-time $patch {orderIds, updates} and its byte-identical `<id>_response` copies;
          ruling 4: the session context turn is not an interaction;
          ruling 5: the join binds the stream's init session_id to the native sessionId;
          ruling 6: an empty final answer agrees only when the stream's is empty too.
"""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
for p in (HERE, HERE / "tests"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import test_codex_native as tcn  # noqa: E402

FIX = Path(__file__).resolve().parent / "fixtures" / "b25-real-shapes"


def fixture(name: str) -> bytes:
    return (FIX / name).read_bytes()


def lines(raw: bytes) -> list:
    return [json.loads(x) for x in raw.decode("utf-8").splitlines() if x.strip()]


def jl(records) -> bytes:
    return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records).encode("utf-8")


# ---- Codex ------------------------------------------------------------------------------------------------------------

def codex_shapes() -> dict:
    return json.loads(fixture("w-o46-codex-records.json"))


def codex_rollout(turns=2, world=None, settings=None, *, world_at=None, settings_at=None) -> list:
    """test_codex_native's synthetic rollout with w-o46's two record shapes where every real one sits: world_state in
    turn 1 just after task_started, the settings pair between turns (w-o46 ordinals 6, 39-40)."""
    shapes = codex_shapes()
    world = copy.deepcopy(shapes["world_state"][0]) if world is None else world
    pair = copy.deepcopy(shapes["thread_settings_applied"]) if settings is None else settings
    if settings is None:                            # a caller's own pair is used as given (its mutants included)
        for p in pair:
            p["thread_id"] = tcn.TID
    recs = tcn.rollout(turns=turns)
    starts = [i for i, r in enumerate(recs) if r["payload"].get("type") == "task_started"]
    second = starts[1] if settings_at is None else settings_at
    for p in reversed(pair):
        recs.insert(second, tcn.line(0, "event_msg", p))
    recs.insert(starts[0] + 1 if world_at is None else world_at, tcn.line(0, "world_state", world))
    for n, rec in enumerate(recs):
        rec["ordinal"] = n
    return recs


class CodexRealShapes(unittest.TestCase):
    def test_both_records_are_admitted_and_carry_no_fact(self):
        m = tcn.cn()
        plain = m.project(tcn.raw(tcn.rollout(turns=2)))
        got = m.project(tcn.raw(codex_rollout()))
        self.assertEqual(got, plain, "world_state and thread_settings_applied must add or change no fact")
        self.assertEqual(len(got), 2)

    def refuses(self, recs, why):
        m = tcn.cn()
        with self.assertRaises(m.ReaderRefused) as cm:
            m.read_rollout(tcn.raw(recs))
        self.assertIn(why, str(cm.exception))

    def test_world_state_off_its_shape_or_place_refuses(self):
        shape = codex_shapes()["world_state"][0]
        for why, edit in (("exactly {full: bool, state: object}", lambda w: w.pop("full")),
                          ("exactly {full: bool, state: object}", lambda w: w.__setitem__("full", "true")),
                          ("exactly {full: bool, state: object}", lambda w: w.__setitem__("state", [])),
                          ("exactly {full: bool, state: object}", lambda w: w.__setitem__("turn_id", "t1"))):
            w = copy.deepcopy(shape)
            edit(w)
            with self.subTest(why=why, keys=sorted(w)):
                self.refuses(codex_rollout(world=w), why)
        with self.subTest(place="before any turn"):
            self.refuses(codex_rollout(world_at=1), "world_state outside an open turn")
        self.assertTrue(isinstance(shape["full"], bool) and isinstance(shape["state"], dict))

    def test_thread_settings_applied_off_its_shape_or_place_refuses(self):
        def edited(edit):
            pair = copy.deepcopy(codex_shapes()["thread_settings_applied"])
            for p in pair:
                p["thread_id"] = tcn.TID
            edit(pair[0]["thread_settings"], pair[0])
            return pair
        cases = (
            ("keys are not exactly", lambda s, p: s.pop("model")),
            ("keys are not exactly", lambda s, p: s.pop("disabled_plugin_ids")),
            ("keys are not exactly", lambda s, p: s.__setitem__("sandbox_policy", {"type": "x"})),
            ("model and model_provider_id", lambda s, p: s.__setitem__("model", 7)),
            ("approval_policy", lambda s, p: s.__setitem__("approval_policy", {"granular": {}})),
            ("approval_policy", lambda s, p: s.__setitem__("approval_policy", "on-failure")),
            ("approvals_reviewer", lambda s, p: s.__setitem__("approvals_reviewer", "guardian_subagent")),
            ("permission_profile", lambda s, p: s.__setitem__("permission_profile", {"type": "managed"})),
            ("cwd is an absolute path", lambda s, p: s.__setitem__("cwd", "relative/tree")),
            ("runtime_workspace_roots", lambda s, p: s.__setitem__("runtime_workspace_roots", ["relative"])),
            ("reasoning_effort", lambda s, p: s.__setitem__("reasoning_effort", "")),
            ("reasoning_summary", lambda s, p: s.__setitem__("reasoning_summary", "verbose")),
            ("personality", lambda s, p: s.__setitem__("personality", "grumpy")),
            ("service_tier", lambda s, p: s.__setitem__("service_tier", 1)),
            ("active_permission_profile", lambda s, p: s.__setitem__("active_permission_profile", {"id": 1})),
            ("collaboration_mode", lambda s, p: s["collaboration_mode"].__setitem__("mode", "pair_programming")),
            ("collaboration_mode", lambda s, p: s["collaboration_mode"]["settings"].pop("developer_instructions")),
            ("disabled_plugin_ids", lambda s, p: s.__setitem__("disabled_plugin_ids", [1])),
            ("names another thread", lambda s, p: p.__setitem__("thread_id", "another-thread")),
            ("exactly {type, thread_id, thread_settings}", lambda s, p: p.pop("thread_id")),
            ("exactly {type, thread_id, thread_settings}", lambda s, p: p.__setitem__("extra", 1)))
        for why, edit in cases:
            with self.subTest(why=why):
                self.refuses(codex_rollout(settings=edited(edit)), why)
        with self.subTest(place="inside a turn"):
            recs = tcn.rollout(turns=2)
            starts = [i for i, r in enumerate(recs) if r["payload"].get("type") == "task_started"]
            self.refuses(codex_rollout(settings_at=starts[1] - 1), "thread_settings_applied inside an open turn")

    def test_the_admitted_optional_keys_and_values_read(self):
        m = tcn.cn()

        def fill(s, p):
            s.update(service_tier="flex", reasoning_summary="auto", personality="pragmatic",
                     active_permission_profile={"id": ":workspace"}, approval_policy="on-request",
                     approvals_reviewer="auto_review")
            s["collaboration_mode"]["mode"] = "plan"
        pair = copy.deepcopy(codex_shapes()["thread_settings_applied"])
        for p in pair:
            p["thread_id"] = tcn.TID
        fill(pair[0]["thread_settings"], pair[0])
        self.assertEqual(len(m.project(tcn.raw(codex_rollout(settings=pair)))), 2)


class CodexSentAndModel(unittest.TestCase):
    """Ruling 2 (Codex review M1): codex_join_session binds each turn's UserMessage to the line sent and its
    turn_context model to the take's requested model."""

    def join(self, recs, *, sent=("sent 1", "sent 2"), model="SYNTHETIC-MODEL"):
        import native_reader_registration as nrr
        return nrr.codex_join_session(tcn.raw(recs), [tcn.exec_stream(), tcn.exec_stream()], [0, 0],
                                      sent=list(sent), model=model)

    def test_a_matching_rollout_passes(self):
        got = self.join(codex_rollout())
        self.assertEqual((got["status"], got["interactions"]), ("PASS", 2), got)

    def test_a_replaced_prompt_or_model_disagrees(self):
        recs = codex_rollout()
        prompt = copy.deepcopy(recs)
        for r in prompt:
            item = r["payload"].get("item") if isinstance(r["payload"], dict) else None
            if isinstance(item, dict) and item.get("type") == "UserMessage" and item["id"] == "u2":
                item["content"][0]["text"] = "a replaced prompt"
        model = copy.deepcopy(recs)
        for r in model:
            if r["type"] == "turn_context":
                r["payload"]["model"] = "another-model"
        for why, got in (("sent prompt is not the line sent", self.join(prompt)),
                         ("requested model is not the take's", self.join(model)),
                         ("sent prompt is not the line sent", self.join(recs, sent=("sent 1", "other"))),
                         ("requested model is not the take's", self.join(recs, model="another-model")),
                         ("one sent line per stream", self.join(recs, sent=("sent 1",))),
                         ("no requested model", self.join(recs, model=None))):
            with self.subTest(why=why):
                self.assertEqual(got["status"], "DISAGREE", got)
                self.assertIn(why, got["why"])

    def test_codex_check_reads_both_from_the_ledger(self):
        import native_reader_registration as nrr
        ledger = {"turns": [{"exit": 0, "sent": "sent 1"}, {"exit": 0, "sent": "sent 2"}],
                  "model_requested": "SYNTHETIC-MODEL",
                  "served_model": [{"value": None, "source": "unobserved"}] * 2}
        streams = [tcn.exec_stream(), tcn.exec_stream()]
        self.assertEqual(nrr.codex_check(tcn.raw(codex_rollout()), streams, ledger)["status"], "PASS")
        for edit in (lambda d: d["turns"][1].__setitem__("sent", "other"),
                     lambda d: d.__setitem__("model_requested", "another-model")):
            bad = copy.deepcopy(ledger)
            edit(bad)
            with self.subTest(ledger=bad):
                self.assertEqual(nrr.codex_check(tcn.raw(codex_rollout()), streams, bad)["status"], "DISAGREE")


# ---- Gemini -----------------------------------------------------------------------------------------------------------

def gp():
    import gemini_projection
    return gemini_projection


def replay_mod():
    import gemini_session_replay
    return gemini_session_replay


def patch_line(recs) -> int:
    hits = [i for i, r in enumerate(recs) if "$patch" in r]
    assert len(hits) == 1, hits
    return hits[0]


class GeminiResumePatch(unittest.TestCase):
    def test_the_resume_patch_reorders_as_the_pinned_loader_does(self):
        recs = lines(fixture("w-g21-native-turn-2.jsonl"))
        got = replay_mod().replay(jl(recs))["messages"]
        order = recs[patch_line(recs)]["$patch"]["orderIds"]
        self.assertEqual([m["id"] for m in got][:len(order)], order,
                         "a permutation: the replayed order is orderIds, then what was recorded after the patch")
        copies = [k for k, m in enumerate(got) if m["id"].endswith("_response")]
        self.assertTrue(copies)
        for k in copies:
            self.assertEqual(got[k - 1]["id"] + "_response", got[k]["id"], "a copy sits right after its gemini")
            self.assertEqual(got[k]["content"], got[k + 1]["content"], "and right before its identical original")

    def test_a_second_resume_lists_each_response_copy_twice_and_keeps_its_first_place(self):
        recs = lines(fixture("w-g31-native-turn-3.jsonl"))
        patches = [r["$patch"] for r in recs if "$patch" in r]
        last = patches[-1]["orderIds"]
        self.assertGreater(len(last), len(set(last)), "the fixture holds the second resume's repeated ids")
        got = replay_mod().replay(jl(recs))["messages"]
        first = list(dict.fromkeys(last))
        self.assertEqual([m["id"] for m in got][:len(first)], first)

    def test_every_other_patch_shape_refuses(self):
        r = replay_mod()
        recs = lines(fixture("w-g21-native-turn-2.jsonl"))
        k = patch_line(recs)
        base = recs[k]["$patch"]
        known = [x for x in base["orderIds"]]
        gemini = next(x for x in known if x + "_response" in known)

        def variant(patch):
            out = copy.deepcopy(recs)
            out[k] = {"$patch": patch}
            return jl(out)
        cases = (
            # lane vendor-b26 (glitch-26's ruling 1, shape B): removeIds beside orderIds and updates is admitted only
            # inside a resume and only for an ignored user prompt; this one is neither
            ("removeIds (destructive)", dict(base, removeIds=[known[-1]]), "a resume removes a message that is not"),
            # lane vendor-b26 fold (glitch-f1's ruling 4 on REVIEW-vendor-b26-04c4e77 MINOR 4): inside a resume this
            # writer-possible, unobserved shape refuses by its own name
            ("orderIds without updates", {"orderIds": base["orderIds"]},
             "writer-possible resume shape {orderIds} (a resume with no update)"),
            # lane vendor-b26 (glitch-26's ruling 8): a top-level id is never written by the pinned recorder
            ("orderIds with id", dict(base, id=known[0]), "direct-id native patch"),
            ("a known id left out", dict(base, orderIds=known[:-1]), "not a permutation"),
            ("an unknown id", dict(base, orderIds=known + ["no-such-message"]), "names an unknown message"),
            ("a repeated gemini id", dict(base, orderIds=known + [gemini]), "repeats an id that is not"),
            ("a repeated prompt id", dict(base, orderIds=known + [known[1]]), "repeats an id that is not"),
            ("a non-string id", dict(base, orderIds=known + [7]), "array of ids"),
            ("empty updates", dict(base, updates=[]), "updates must be a nonempty array"),
            ("an update to an absent message", dict(base, updates=[{"id": "absent", "content": "x"}]),
             "patch target is absent"))
        for why, patch, reason in cases:
            with self.subTest(why=why), self.assertRaises(r.ReplayRefused) as cm:
                r.replay(variant(patch))
            self.assertIn(reason, str(cm.exception))


class GeminiProjection(unittest.TestCase):
    def test_w_g21_projects_one_then_two_interactions_and_the_first_is_unchanged(self):
        one = gp().project(fixture("w-g21-native-turn-1.jsonl"))
        two = gp().project(fixture("w-g21-native-turn-2.jsonl"))
        self.assertEqual((len(one), len(two)), (1, 2))
        self.assertEqual(two[0], one[0], "the resume's reorder and rewrite change no fact of interaction 1")
        self.assertFalse(one[0]["sent"].startswith("<session_context>"), "interaction 1 is the prompt")
        self.assertEqual(sum(o["kind"] == "tool" for o in one[0]["output"]), 34)

    def test_w_g31_after_two_resumes_projects_three(self):
        self.assertEqual(len(gp().project(fixture("w-g31-native-turn-3.jsonl"))), 3)

    def test_the_context_turn_is_recognised_only_on_its_exact_shape(self):
        m = gp()
        recs = lines(fixture("w-g21-native-turn-1.jsonl"))
        ctx = recs[1]
        self.assertEqual(ctx["id"], m.ENV_CONTEXT_ID)
        cases = (("another id", lambda c: c.__setitem__("id", "a-different-id")),
                 ("an added key", lambda c: c.__setitem__("displayContent", c["content"])),
                 ("another opening", lambda c: c["content"][0].__setitem__("text", "<session_context>\nOther.\n"
                                                                                    "</session_context>")),
                 ("no closing", lambda c: c["content"][0].__setitem__(
                     "text", c["content"][0]["text"][:-len(m.ENV_CONTEXT_CLOSE)])),
                 ("two parts", lambda c: c["content"].append({"text": "more"})),
                 ("a string content", lambda c: c.__setitem__("content", c["content"][0]["text"])))
        for why, edit in cases:
            bad = copy.deepcopy(recs)
            edit(bad[1])
            with self.subTest(why=why), self.assertRaises(m.ProjectionRefused) as cm:
                m.project(jl(bad))
            self.assertIn("lacks an assistant message", str(cm.exception),
                          "off its shape, the context turn stays an interaction (and has no reply)")
        moved = copy.deepcopy(recs)
        moved.insert(3, moved.pop(1))                   # not first: an interaction again
        with self.subTest(why="not first"), self.assertRaises(m.ProjectionRefused):
            m.project(jl(moved))

    def test_a_response_copy_is_admitted_only_byte_identical_and_in_place(self):
        m = gp()
        recs = lines(fixture("w-g21-native-turn-2.jsonl"))
        copies = [i for i, r in enumerate(recs) if r.get("id", "").endswith("_response") and "type" in r]
        k = copies[0]

        def refused(bad, why):
            with self.assertRaises(m.ProjectionRefused) as cm:
                m.project(jl(bad))
            self.assertIn(why, str(cm.exception))
        changed = copy.deepcopy(recs)
        changed[k]["content"][0]["functionResponse"]["response"] = {"output": "synthetic text that differs"}
        with self.subTest(why="a non-identical copy"):
            refused(changed, "not the resumed copy")
        retyped = copy.deepcopy(recs)
        retyped[k]["timestamp"] = "2026-01-01T00:00:00.000Z"
        self.assertEqual(len(m.project(jl(retyped))), 2, "a timestamp is not content: still byte-identical content")
        # the copy after its original instead of before it: swap the two in orderIds
        swapped = copy.deepcopy(recs)
        p = patch_line(swapped)
        order = swapped[p]["$patch"]["orderIds"]
        i = order.index(recs[k]["id"])
        order[i], order[i + 1] = order[i + 1], order[i]
        with self.subTest(why="the copy after its original"):
            refused(swapped, "not the resumed copy")
        # a copy whose name is another gemini message's
        other = copy.deepcopy(recs)
        gem = [r["id"] for r in recs if r.get("type") == "gemini"]
        wrong = recs[k]["id"]
        target = next(g + "_response" for g in gem if g + "_response" != wrong and g + "_response" not in
                      {r.get("id") for r in recs})
        text = jl(other).decode("utf-8").replace(json.dumps(wrong), json.dumps(target))
        with self.subTest(why="a copy named for another gemini message"):
            refused(lines(text.encode("utf-8")), "not the resumed copy")


class GeminiJoin(unittest.TestCase):
    def streams(self):
        return [fixture("w-g21-turn-1.jsonl").decode("utf-8"), fixture("w-g21-turn-2.jsonl").decode("utf-8")]

    def test_w_g21_joins_both_turns(self):
        import native_reader_registration as nrr
        got = nrr.check_session(fixture("w-g21-native-turn-2.jsonl"), self.streams())
        self.assertEqual((got["status"], got.get("interactions")), ("PASS", 2), got)
        self.assertEqual(got["shapes"]["tool_round_trips"], 34)

    def test_another_or_absent_init_session_disagrees(self):
        import native_reader_registration as nrr
        s1, s2 = self.streams()
        recs = lines(s2.encode())
        other = jl([dict(r, session_id="another-session") if r["type"] == "init" else r for r in recs]).decode()
        absent = jl([r for r in recs if r["type"] != "init"]).decode()
        for why, stream in (("another id", other), ("no init", absent)):
            with self.subTest(why=why):
                got = nrr.check_session(fixture("w-g21-native-turn-2.jsonl"), [s1, stream])
                self.assertEqual(got["status"], "DISAGREE")
                self.assertIn("session identity disagrees", got["why"])


class EmptyAnswer(unittest.TestCase):
    """Ruling 6: w-g21's turn 2 (no tools, one answer) with the final answer emptied on one side, or both."""

    def cut(self, native_empty: bool, stream_empty: bool):
        import native_reader_registration as nrr
        recs = lines(fixture("w-g21-native-turn-2.jsonl"))
        if native_empty:
            final = [r for r in recs if r.get("type") == "gemini"][-1]
            final["content"] = ""
        s1 = fixture("w-g21-turn-1.jsonl").decode()
        s2 = lines(fixture("w-g21-turn-2.jsonl"))
        if stream_empty:
            s2 = [r for r in s2 if not (r["type"] == "message" and r.get("role") == "assistant")]
        return nrr.check_session(jl(recs), [s1, jl(s2).decode()])

    def test_both_empty_agrees(self):
        got = self.cut(True, True)
        self.assertEqual(got["status"], "PASS", got)

    def test_one_side_empty_disagrees(self):
        for native_empty, stream_empty in ((True, False), (False, True)):
            with self.subTest(native_empty=native_empty, stream_empty=stream_empty):
                got = self.cut(native_empty, stream_empty)
                self.assertEqual(got["status"], "DISAGREE", got)
                self.assertIn("recorded text disagrees", got["why"])


if __name__ == "__main__":
    unittest.main()
