"""box/stub_model_server.py and the scenario scripts (lane vendor-b27, glitch-f1's rulings 1 and 4, 21 Oct 2026).

Fakes only: a local test client that speaks the SDK's framing, never the CLI. What is bound (the B27 design's test plan):
  - the SSE framing parses under an independent check mirroring the SDK's responseLineRE (:267445) with no partial
    segment left (:267688-267691);
  - an unscripted request gets 400 with the Google error body and HOLDS the scenario (every later request refused);
  - an out-of-order request is refused (a wrong prompt, the wrong endpoint, responses that do not answer the stub's
    previous calls);
  - the inflated promptTokenCount is sent only where the scenario names it, every other count computed from the body;
  - call ids are call_<n> from the stub's counter, answered bare or as the CLI's <name>__<id>;
  - every final chunk carries finishReason, and a response without calls carries text;
  - the scenario JSON files are exactly make_scenarios.py's output, each a valid script whose every entry a client
    can reach in order, with one predicted verdict per process;
  - the request log, the bodies and the state file are written; the server answers on 127.0.0.1.
"""
import hashlib
import http.client
import importlib.util
import json
import os
import re
import sys
import tempfile
import threading
import unittest
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY))
from box import stub_model_server as sms  # noqa: E402

SCEN = STUDY / "box" / "stub_model_scenarios"
_spec = importlib.util.spec_from_file_location("b27_make_scenarios", SCEN / "make_scenarios.py")
mk = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mk)

# the SDK's responseLineRE, chunk-NR7L3FXV.js:267445, spelled independently here
RESPONSE_LINE = re.compile(r"^\s*data: (.*)(?:\n\n|\r\r|\r\n\r\n)")
STREAM = "/v1beta/models/gemini-3.8-flash:streamGenerateContent?alt=sse"
GENERATE = "/v1beta/models/gemini-3.8-flash:generateContent"


def sse_chunks(body: bytes) -> list:
    """Split the way the SDK does; a partial segment at the end refuses ("Incomplete JSON segment at the end")."""
    text, out = body.decode("utf-8"), []
    while text:
        m = RESPONSE_LINE.match(text)
        if not m:
            raise AssertionError("Incomplete JSON segment at the end")
        out.append(json.loads(m.group(1)))
        text = text[m.end():]
    return out


def user(text):
    return {"role": "user", "parts": [{"text": text}]}


def req(*contents):
    return json.dumps({"contents": [user("<session_context>synthetic</session_context>"),
                                    {"role": "model", "parts": [{"text": "Got it."}]}, *contents]}).encode()


def fn_turn(ids, prefixed=True):
    return {"role": "user", "parts": [{"functionResponse": {"id": (f"read_file__{i}" if prefixed else i),
                                                            "name": "read_file", "response": {"output": "x"}}}
                                      for i in ids]}


def script(*entries, name="T"):
    return {"schema": 1, "scenario": name, "requests": list(entries)}


ONE_READ = script(
    {"endpoint": "stream", "match": {"kind": "user_text", "text": "Read a."},
     "respond": {"thought": {"subject": "Reading", "description": "a"},
                 "calls": [{"name": "read_file", "args": {"file_path": "/t/a"}}]}},
    {"endpoint": "stream", "match": {"kind": "function_response"},
     "respond": {"text": "done", "prompt_tokens": 600000}},
)


class Framing(unittest.TestCase):
    def test_every_stream_body_parses_whole_and_the_final_chunk_finishes(self):
        stub = sms.Stub(ONE_READ)
        status, ctype, body = stub.handle("POST", STREAM, req(user("Read a.")))
        self.assertEqual((status, ctype), (200, "text/event-stream"))
        chunks = sse_chunks(body)
        self.assertEqual(len(chunks), 2)
        self.assertTrue(chunks[0]["candidates"][0]["content"]["parts"][0]["thought"])
        self.assertEqual(chunks[-1]["candidates"][0]["finishReason"], "STOP")
        self.assertEqual(set(chunks[-1]["usageMetadata"]),
                         {"promptTokenCount", "candidatesTokenCount", "cachedContentTokenCount", "thoughtsTokenCount",
                          "toolUsePromptTokenCount", "totalTokenCount"})
        self.assertTrue(body.endswith(b"\r\n\r\n"))

    def test_a_cut_body_is_caught_by_the_framing_check(self):
        _s, _c, body = sms.Stub(ONE_READ).handle("POST", STREAM, req(user("Read a.")))
        with self.assertRaises(AssertionError):
            sse_chunks(body[:-2])

    def test_the_thought_carries_a_subject_line(self):
        _s, _c, body = sms.Stub(ONE_READ).handle("POST", STREAM, req(user("Read a.")))
        self.assertTrue(sse_chunks(body)[0]["candidates"][0]["content"]["parts"][0]["text"].startswith("**Reading**"))


class CallIds(unittest.TestCase):
    def test_ids_are_call_n_and_the_cli_prefixed_answer_matches(self):
        stub = sms.Stub(ONE_READ)
        _s, _c, body = stub.handle("POST", STREAM, req(user("Read a.")))
        call = sse_chunks(body)[-1]["candidates"][0]["content"]["parts"][0]["functionCall"]
        self.assertEqual(call["id"], "call_1")
        status, _c, _b = stub.handle("POST", STREAM, req(user("Read a."), fn_turn(["call_1"])))
        self.assertEqual(status, 200)
        self.assertTrue(stub.state()["done"])

    def test_the_bare_id_answer_matches_too(self):
        stub = sms.Stub(ONE_READ)
        stub.handle("POST", STREAM, req(user("Read a.")))
        self.assertEqual(stub.handle("POST", STREAM, req(user("Read a."), fn_turn(["call_1"], prefixed=False)))[0],
                         200)

    def test_an_answer_to_another_call_is_refused(self):
        stub = sms.Stub(ONE_READ)
        stub.handle("POST", STREAM, req(user("Read a.")))
        self.assertEqual(stub.handle("POST", STREAM, req(user("Read a."), fn_turn(["call_9"])))[0], 400)
        self.assertIn("previous calls", stub.held)

    def test_a_helper_answer_does_not_reset_the_calls_to_answer(self):
        s = script(ONE_READ["requests"][0],
                   {"endpoint": "generate", "match": {"kind": "user_text_prefix", "prefix": "Generate a new"},
                    "respond": {"text": "<state_snapshot>s</state_snapshot>"}},
                   ONE_READ["requests"][1])
        stub = sms.Stub(s)
        stub.handle("POST", STREAM, req(user("Read a.")))
        self.assertEqual(stub.handle("POST", GENERATE, req(user("Generate a new <state_snapshot> x")))[0], 200)
        self.assertEqual(stub.handle("POST", STREAM, req(user("Read a."), fn_turn(["call_1"])))[0], 200)


class Usage(unittest.TestCase):
    def test_the_inflated_count_only_where_named(self):
        stub = sms.Stub(ONE_READ)
        raw1 = req(user("Read a."))
        _s, _c, b1 = stub.handle("POST", STREAM, raw1)
        self.assertEqual(sse_chunks(b1)[-1]["usageMetadata"]["promptTokenCount"], len(raw1) // 4)
        _s, _c, b2 = stub.handle("POST", STREAM, req(user("Read a."), fn_turn(["call_1"])))
        self.assertEqual(sse_chunks(b2)[-1]["usageMetadata"]["promptTokenCount"], 600000)

    def test_every_scenario_names_the_inflated_count_only_on_the_design_s_entries(self):
        named = {}
        for name, s in mk.SCENARIOS.items():
            named[name] = sum(1 for e in s["requests"] if "prompt_tokens" in e["respond"])
            for e in s["requests"]:
                if "prompt_tokens" in e["respond"]:
                    self.assertEqual(e["respond"]["prompt_tokens"], 600000)
        # the design's table, section 3: none, none, none, one, one, two, two
        self.assertEqual(named, {"A1": 0, "A2": 0, "A3": 0, "B1": 1, "B2": 1, "C1": 2, "C2": 2})


class Refusals(unittest.TestCase):
    def test_an_unscripted_endpoint_gets_400_and_holds_the_scenario(self):
        stub = sms.Stub(ONE_READ)
        status, ctype, body = stub.handle("POST", "/v1beta/models/gemini-3.8-flash:countTokens", req(user("x")))
        self.assertEqual((status, json.loads(body)), (400, sms.ERROR_BODY))
        self.assertIsNotNone(stub.held)
        # held: even the right request is refused now
        self.assertEqual(stub.handle("POST", STREAM, req(user("Read a.")))[0], 400)
        self.assertFalse(stub.state()["done"])

    def test_a_get_and_a_stream_without_sse_are_refused(self):
        self.assertEqual(sms.Stub(ONE_READ).handle("GET", STREAM, b"")[0], 400)
        self.assertEqual(sms.Stub(ONE_READ).handle("POST", STREAM.split("?")[0], req(user("Read a.")))[0], 400)

    def test_an_out_of_order_request_is_refused(self):
        self.assertEqual(sms.Stub(ONE_READ).handle("POST", STREAM, req(user("Read b.")))[0], 400)
        self.assertEqual(sms.Stub(ONE_READ).handle("POST", GENERATE, req(user("Read a.")))[0], 400)
        stub = sms.Stub(ONE_READ)
        self.assertEqual(stub.handle("POST", STREAM, req(fn_turn(["call_1"])))[0], 400)

    def test_an_unscripted_endpoint_is_refused_even_with_the_next_entry_s_body(self):
        # REVIEW-vendor-b27-25ffff5 MINOR 2 (the reviewer's M3b survived): the body matches entry 1 exactly
        stub = sms.Stub(ONE_READ)
        status, _c, _b = stub.handle("POST", "/v1beta/models/gemini-3.8-flash:countTokens", req(user("Read a.")))
        self.assertEqual(status, 400)
        self.assertIn("unscripted endpoint", stub.held)
        self.assertEqual(stub.state()["next"], 1)

    def test_a_request_matching_a_later_entry_is_refused(self):
        # REVIEW-vendor-b27-25ffff5 MINOR 2 (the reviewer's M3c survived): no skipping ahead to a later match
        s = script({"endpoint": "stream", "match": {"kind": "user_text", "text": "First."}, "respond": {"text": "1"}},
                   {"endpoint": "stream", "match": {"kind": "user_text", "text": "Second."}, "respond": {"text": "2"}})
        stub = sms.Stub(s)
        self.assertEqual(stub.handle("POST", STREAM, req(user("Second.")))[0], 400)
        self.assertIsNotNone(stub.held)
        self.assertEqual(stub.state()["next"], 1)

    def test_a_request_after_the_last_entry_is_refused(self):
        stub = sms.Stub(ONE_READ)
        stub.handle("POST", STREAM, req(user("Read a.")))
        stub.handle("POST", STREAM, req(user("Read a."), fn_turn(["call_1"])))
        self.assertEqual(stub.handle("POST", STREAM, req(user("Read a.")))[0], 400)
        self.assertIn("after the script's last entry", stub.held)

    def test_a_script_off_its_shape_never_starts(self):
        bad = [
            {"schema": 2, "scenario": "x", "requests": [ONE_READ["requests"][0]]},
            script(),
            script({"endpoint": "stream", "match": {"kind": "user_text", "text": "a"}, "respond": {}}),
            script({"endpoint": "stream", "match": {"kind": "user_text", "text": "a"}, "respond": {"text": ""}}),
            script({"endpoint": "generate", "match": {"kind": "user_text", "text": "a"},
                    "respond": {"calls": [{"name": "read_file", "args": {}}]}}),
            script({"endpoint": "other", "match": {"kind": "user_text", "text": "a"}, "respond": {"text": "b"}}),
            script({"endpoint": "stream", "match": {"kind": "guess"}, "respond": {"text": "b"}}),
            script({"endpoint": "stream", "match": {"kind": "user_text", "text": "a"},
                    "respond": {"text": "b", "prompt_tokens": 0}}),
        ]
        for doc in bad:
            with self.subTest(doc=doc), self.assertRaises(sms.ScriptError):
                sms.Stub(doc)


class Generated(unittest.TestCase):
    def test_generated_text_is_exactly_its_length_with_its_wrapper(self):
        t = sms.generated_text({"chars": 2_600_000, "open": "<state_snapshot>", "close": "</state_snapshot>",
                                "seed": "c1"})
        self.assertEqual(len(t), 2_600_000)
        self.assertTrue(t.startswith("<state_snapshot>") and t.endswith("</state_snapshot>"))
        self.assertEqual(t, sms.generated_text({"chars": 2_600_000, "open": "<state_snapshot>",
                                                "close": "</state_snapshot>", "seed": "c1"}))

    def test_a_generate_answer_is_one_json_response(self):
        s = script({"endpoint": "generate", "match": {"kind": "user_text_prefix", "prefix": "Critically"},
                    "respond": {"text": "<state_snapshot>v</state_snapshot>"}})
        status, ctype, body = sms.Stub(s).handle("POST", GENERATE, req(user("Critically evaluate it")))
        doc = json.loads(body)
        self.assertEqual((status, ctype), (200, "application/json"))
        self.assertEqual(doc["candidates"][0]["finishReason"], "STOP")
        self.assertEqual(doc["candidates"][0]["content"]["parts"][0]["text"], "<state_snapshot>v</state_snapshot>")


class Records(unittest.TestCase):
    def test_the_log_bodies_and_state_are_written(self):
        with tempfile.TemporaryDirectory() as d:
            stub = sms.Stub(ONE_READ, d, clock=lambda: 1.0)
            raw = req(user("Read a."))
            stub.handle("POST", STREAM, raw)
            stub.handle("POST", STREAM, req(user("nope")))
            lines = [json.loads(x) for x in Path(d, "requests.jsonl").read_text().splitlines()]
            self.assertEqual([x["verdict"] for x in lines], ["answered", "refused"])
            self.assertEqual(lines[0]["body_sha256"], hashlib.sha256(raw).hexdigest())
            self.assertEqual(Path(d, "bodies", "req-1.json").read_bytes(), raw)
            state = json.loads(Path(d, "state.json").read_text())
            self.assertEqual((state["next"], state["requests"], state["done"]), (2, 2, False))
            self.assertIn("request 2", state["held"])

    def test_the_flags_name_the_masked_tag_and_the_truncation_text(self):
        stub = sms.Stub(ONE_READ)
        stub.handle("POST", STREAM, req(user("Read a."), user("<tool_output_masked>\np\n</tool_output_masked>"),
                                        user("Output too large. Showing first 8,000 and last 32,000 characters.")))
        self.assertEqual(stub.log[0]["flags"], {"masked_tag": True, "truncation_text": True, "state_snapshot": False})


class FakeFile(unittest.TestCase):
    def test_the_fake_records_are_the_stub_s_own_answers_one_per_entry(self):
        doc = json.loads((SCEN / "A1.json").read_text())
        recs = sms.fake_records(doc)
        self.assertEqual(len(recs), len(doc["requests"]))
        self.assertEqual({r["method"] for r in recs}, {"generateContentStream"})
        ids = [p["functionCall"]["id"] for r in recs for c in r["response"] for p in c["candidates"][0]["content"]
               ["parts"] if "functionCall" in p]
        self.assertEqual(ids, [f"call_{n}" for n in range(1, 8)])
        for r in recs:
            self.assertEqual(r["response"][-1]["candidates"][0]["finishReason"], "STOP")
            self.assertEqual(r["response"][-1]["usageMetadata"]["promptTokenCount"], sms.FAKE_PROMPT_TOKENS)

    def test_a_named_count_and_a_helper_answer_keep_their_form(self):
        doc = json.loads((SCEN / "B1.json").read_text())
        recs = sms.fake_records(doc)
        self.assertEqual([r["method"] for r in recs].count("generateContent"), 2)
        named = [r for r, e in zip(recs, doc["requests"]) if "prompt_tokens" in e["respond"]]
        self.assertEqual(named[0]["response"][-1]["usageMetadata"]["promptTokenCount"], 600000)


class Server(unittest.TestCase):
    def test_the_server_answers_on_loopback_one_response_per_connection(self):
        with tempfile.TemporaryDirectory() as d:
            server = sms.make_server(sms.Stub(ONE_READ, d), 0)
            self.assertEqual(server.server_address[0], "127.0.0.1")
            t = threading.Thread(target=server.serve_forever, daemon=True)
            t.start()
            try:
                conn = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=10)
                conn.request("POST", STREAM, body=req(user("Read a.")), headers={"Content-Type": "application/json"})
                resp = conn.getresponse()
                body = resp.read()
                self.assertEqual((resp.status, resp.getheader("Connection")), (200, "close"))
                self.assertEqual(len(sse_chunks(body)), 2)
                conn.close()
            finally:
                server.shutdown()
                server.server_close()

    def test_every_verb_is_logged_and_holds_the_scenario(self):
        # REVIEW-vendor-b27-25ffff5 NIT 7: HEAD, OPTIONS and PATCH reach the stub, not http.server's own 501
        for verb in ("HEAD", "OPTIONS", "PATCH"):
            with self.subTest(verb=verb), tempfile.TemporaryDirectory() as d:
                stub = sms.Stub(ONE_READ, d)
                server = sms.make_server(stub, 0)
                t = threading.Thread(target=server.serve_forever, daemon=True)
                t.start()
                try:
                    conn = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=10)
                    conn.request(verb, STREAM, body=b"" if verb == "HEAD" else req(user("Read a.")))
                    resp = conn.getresponse()
                    resp.read()
                    self.assertEqual(resp.status, 400)
                    conn.close()
                finally:
                    server.shutdown()
                    server.server_close()
                self.assertEqual([r["method"] for r in stub.log], [verb])
                self.assertIsNotNone(stub.held)


def drive(doc) -> sms.Stub:
    """A client that reaches every entry in order (prompt texts, the previous calls' answers, helper prefixes)."""
    stub = sms.Stub(json.loads(json.dumps(doc).replace("${RUN_TREE}", "/t")))
    history, ids = [], []
    for i, e in enumerate(doc["requests"], start=1):
        m = e["match"]
        if m["kind"] == "user_text":
            history.append(user(m["text"]))
            last = history[-1]
        elif m["kind"] == "function_response":
            last = fn_turn(ids)
            history.append(last)
        else:
            last = user(m["prefix"] + " (rest of the CLI's text)")
        path = STREAM if e["endpoint"] == "stream" else GENERATE
        status, _c, body = stub.handle("POST", path, req(*history[:-1], last) if m["kind"] != "user_text_prefix"
                                       else req(*history, last))
        if status != 200:
            raise AssertionError(f"entry {i}: {stub.held}")
        if e["endpoint"] == "stream":
            parts = sse_chunks(body)[-1]["candidates"][0]["content"]["parts"]
            ids = [p["functionCall"]["id"] for p in parts if "functionCall" in p]
            history.append({"role": "model", "parts": parts})
    return stub


class Scenarios(unittest.TestCase):
    def test_the_json_files_are_the_generator_s_output(self):
        built = mk.build()
        on_disk = {p.name: p.read_bytes() for p in SCEN.glob("*.json")}
        self.assertEqual(sorted(on_disk), sorted(built))
        for name, data in built.items():
            self.assertEqual(on_disk[name], data, name)

    def test_the_seven_scenarios_of_the_design(self):
        self.assertEqual(sorted(mk.SCENARIOS), ["A1", "A2", "A3", "B1", "B2", "C1", "C2"])
        self.assertEqual([n for n, s in mk.SCENARIOS.items() if s.get("fake_cross_check")], ["A1"])

    def test_every_scenario_is_reachable_in_order_and_predicts_each_process(self):
        for p in sorted(SCEN.glob("*.json")):
            doc = json.loads(p.read_text())
            with self.subTest(scenario=doc["scenario"]):
                stub = drive(doc)
                self.assertTrue(stub.state()["done"])
                self.assertEqual(len(doc["expect"]["snapshots"]), len(doc["processes"]))
                prompts = [e["match"]["text"] for e in doc["requests"] if e["match"]["kind"] == "user_text"]
                self.assertEqual(prompts, doc["processes"])
                for e in doc["requests"]:
                    for c in e["respond"].get("calls") or []:
                        self.assertIn(c["args"]["file_path"].split("/")[-1], doc["files"])

    def test_every_refused_prediction_names_its_reason(self):
        # REVIEW-vendor-b27-25ffff5 NIT 8: "" is in every reason, so a refused prediction must carry reason_contains
        for name, s in mk.SCENARIOS.items():
            for k, v in s["expect"]["snapshots"].items():
                if v["verdict"] != "PASS":
                    with self.subTest(scenario=name, snapshot=k):
                        self.assertTrue(v.get("reason_contains"))

    def test_every_call_names_a_distinct_file_and_every_text_is_distinct(self):
        for name, s in mk.SCENARIOS.items():
            files = [c["args"]["file_path"] for e in s["requests"] for c in e["respond"].get("calls") or []]
            texts = [e["respond"]["text"] for e in s["requests"] if e["endpoint"] == "stream"
                     and "text" in e["respond"]]
            with self.subTest(scenario=name):
                self.assertEqual(len(files), len(set(files)))
                self.assertEqual(len(texts), len(set(texts)))


if __name__ == "__main__":
    unittest.main()
