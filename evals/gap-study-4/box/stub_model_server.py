#!/usr/bin/env python3
"""Lane vendor-b27 (glitch-f1's rulings on the B27 design, 21 Oct 2026): the scripted stub model for the stub-model
probe. NOT A MODEL AND NEVER A STUDY TAKE: it answers the pinned Gemini CLI's requests from a fixed scenario script, so
the CLI's own recorder writes the three history-rewrite roads (lane-reports/vendor-b27-DESIGN.md, sections 2 and 3).

Standard library only (the locked take-g image's python3 3.11.2 runs it as `python3 -I -S`), one file, importing
nothing of the study: box/stub_model_probe.py copies it alone into the run tree and starts it inside the take
container as the agent user, on 127.0.0.1 only.

Endpoints (the bundled SDK's request URLs, chunk-NR7L3FXV.js:267524-267564, :269036, :269099):
  POST /<version>/models/<model>:streamGenerateContent?alt=sse   the chat (every request of every turn)
  POST /<version>/models/<model>:generateContent                 the helper calls (the compression summary and its
                                                                 verification, :337194-337238)
Anything else, or a request that is not the script's next entry, gets HTTP 400 with a Google error body, which the
SDK raises as an ApiError (:267693-267707), so an unscripted call fails the CLI loudly; 400 and not 5xx so the CLI's
retry loop does not spin. After the first refusal the scenario is HELD: every later request is refused too, the
state file says why, and the request log keeps every request.

The SSE framing: each chunk `data: <one-line JSON>\\r\\n\\r\\n` (the SDK's responseLineRE, :267445), the body ending on
a whole segment (:267688-267691); Content-Type text/event-stream, HTTP/1.1, Connection: close.

The script (one JSON file per scenario; box/stub_model_scenarios/<name>.json):
  {"schema": 1, "scenario": <name>, "requests": [<entry>, ...], ...}
  entry  = {"endpoint": "stream" | "generate", "match": <match>, "respond": <respond>}
  match  = {"kind": "user_text", "text": <exact text of one part of the last user content>}
         | {"kind": "user_text_prefix", "prefix": <the last user content's last text part starts with it>}
         | {"kind": "function_response"}   (the last content is a user turn of functionResponse parts only, whose
                                            ids are exactly the call ids of the stub's previous stream response,
                                            bare or as the CLI's `<name>__<id>`, :333878-333880)
  respond = {"thought": {"subject", "description"} | absent, "text": <str> | absent,
             "text_generated": {"chars": <n>, "open": <str>, "close": <str>, "seed": <str>} | absent,
             "calls": [{"name", "args"}] | absent, "prompt_tokens": <int> | absent}
A response with calls carries no finishReason text requirement; one without calls must carry non-empty text (the CLI
raises InvalidStreamError otherwise, :333990-334020). Call ids are `call_<n>` from the stub's own counter (the real
API's form, design section 2). usageMetadata carries the six counts the walks' tokens record reads (:334024);
promptTokenCount is the request body's length // 4 (the CLI's own estimate rule, :312103, :312059) unless the entry
names prompt_tokens (the inflated count a compression scenario needs, design section 3).

Files it writes, all under --dir (the run tree's .stub-probe folder): requests.jsonl (one line per request: n, time,
method, path, model, endpoint, the entry matched or null, verdict, body sha256 and length, and flags for the masked
tag, the truncation text and a state snapshot in the body), bodies/req-<n>.json (each request body byte for byte),
state.json (rewritten after each request: next entry, held and why, call counter, done).

    python3 -I -S stub_model_server.py --scenario <file> --dir <folder> [--port 0] [--daemon]
With --daemon it binds first, then forks; the parent prints one JSON line {"ready": true, "port", "pid"} and exits 0.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time

HOST = "127.0.0.1"
SCHEMA = 1
ENDPOINTS = {"streamGenerateContent": "stream", "generateContent": "generate"}
_PATH = re.compile(r"/(v1beta|v1|v1alpha)/models/([A-Za-z0-9._-]+):(streamGenerateContent|generateContent)")
MASKED_TAG = "<tool_output_masked>"                    # MASKING_INDICATOR_TAG, :344663, :344871-344877
TRUNCATED_TEXT = "Output too large. Showing first "     # formatTruncatedToolOutput, :254171-254185
SNAPSHOT_TAG = "<state_snapshot>"
MATCH_KINDS = ("user_text", "user_text_prefix", "function_response")
RESPOND_KEYS = {"thought", "text", "text_generated", "calls", "prompt_tokens"}
ERROR_BODY = {"error": {"code": 400, "status": "INVALID_ARGUMENT", "message": "stub: unscripted request"}}


class ScriptError(ValueError):
    """The scenario file is off its shape; the stub never starts on it."""


def generated_text(spec: dict) -> str:
    """A deterministic synthetic text of exactly spec['chars'] characters: open, numbered lines, close."""
    chars, opener, closer, seed = spec["chars"], spec.get("open", ""), spec.get("close", ""), spec.get("seed", "g")
    body_len = chars - len(opener) - len(closer)
    if body_len < 0:
        raise ScriptError("text_generated is shorter than its open and close")
    lines, n, total = [], 0, 0
    while total < body_len:
        line = f"{seed} synthetic line {n:07d}\n"
        lines.append(line)
        total += len(line)
        n += 1
    return opener + "".join(lines)[:body_len] + closer


def check_script(doc) -> dict:
    """Refuse a scenario off its shape (named), before any request is served."""
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA or not isinstance(doc.get("scenario"), str):
        raise ScriptError("a scenario is {'schema': 1, 'scenario': <name>, 'requests': [...]}")
    reqs = doc.get("requests")
    if not isinstance(reqs, list) or not reqs:
        raise ScriptError("a scenario scripts at least one request")
    for i, e in enumerate(reqs):
        where = f"request {i + 1}"
        if not isinstance(e, dict) or set(e) - {"endpoint", "match", "respond", "note"} \
                or not {"endpoint", "match", "respond"} <= set(e):
            raise ScriptError(f"{where}: an entry is {{endpoint, match, respond}} (and an optional note)")
        if e["endpoint"] not in ENDPOINTS.values():
            raise ScriptError(f"{where}: the endpoint is stream or generate")
        m = e["match"]
        if not isinstance(m, dict) or m.get("kind") not in MATCH_KINDS:
            raise ScriptError(f"{where}: the match kind is one of {MATCH_KINDS}")
        if m["kind"] == "user_text" and (set(m) != {"kind", "text"} or not isinstance(m["text"], str) or not m["text"]):
            raise ScriptError(f"{where}: a user_text match names its exact text")
        if m["kind"] == "user_text_prefix" and (set(m) != {"kind", "prefix"} or not isinstance(m["prefix"], str)
                                                or not m["prefix"]):
            raise ScriptError(f"{where}: a user_text_prefix match names its prefix")
        if m["kind"] == "function_response" and set(m) != {"kind"}:
            raise ScriptError(f"{where}: a function_response match takes no other key")
        r = e["respond"]
        if not isinstance(r, dict) or not r or set(r) - RESPOND_KEYS:
            raise ScriptError(f"{where}: respond keys are {sorted(RESPOND_KEYS)}")
        if "text" in r and "text_generated" in r:
            raise ScriptError(f"{where}: text or text_generated, not both")
        calls = r.get("calls")
        if calls is not None:
            if e["endpoint"] != "stream" or not isinstance(calls, list) or not calls or not all(
                    isinstance(c, dict) and set(c) == {"name", "args"} and isinstance(c["name"], str)
                    and isinstance(c["args"], dict) for c in calls):
                raise ScriptError(f"{where}: calls are [{{name, args}}] on the stream endpoint only")
        elif not (r.get("text") or r.get("text_generated")):
            raise ScriptError(f"{where}: a response without calls carries non-empty text (InvalidStreamError, "
                              f":333990-334020)")
        if "text_generated" in r:
            g = r["text_generated"]
            if not isinstance(g, dict) or set(g) - {"chars", "open", "close", "seed"} or type(g.get("chars")) is not int \
                    or g["chars"] < 1:
                raise ScriptError(f"{where}: text_generated is {{chars, open, close, seed}}")
        if "thought" in r:
            t = r["thought"]
            if not isinstance(t, dict) or set(t) != {"subject", "description"} \
                    or not all(isinstance(v, str) and v for v in t.values()):
                raise ScriptError(f"{where}: a thought is {{subject, description}}")
        if "prompt_tokens" in r and (type(r["prompt_tokens"]) is not int or r["prompt_tokens"] < 1):
            raise ScriptError(f"{where}: prompt_tokens is a positive int")
    return doc


def _last_content(body: dict):
    contents = body.get("contents") if isinstance(body, dict) else None
    if not isinstance(contents, list) or not contents or not isinstance(contents[-1], dict):
        return None
    return contents[-1]


def _texts(content) -> list:
    return [p["text"] for p in content.get("parts") or [] if isinstance(p, dict) and isinstance(p.get("text"), str)]


class Stub:
    """The scripted model: handle(method, path, body bytes) -> (status, content type, body bytes). No socket here, so
    every rule is tested without a server."""

    def __init__(self, script: dict, out_dir: str | None = None, clock=time.time):
        self.script = check_script(script)
        self.out_dir = out_dir
        self.clock = clock
        self.next = 0
        self.n = 0
        self.calls_issued = 0
        self.last_calls: list = []
        self.held = None
        self.log: list = []
        if out_dir is not None:
            os.makedirs(os.path.join(out_dir, "bodies"), exist_ok=True)
            self._write_state()

    # ---------------------------------------------------------------------------------------------- matching
    def _matches(self, entry: dict, endpoint: str, body) -> str | None:
        """None when the request is this entry; else why not."""
        if endpoint != entry["endpoint"]:
            return f"endpoint {endpoint}, the script's next entry is {entry['endpoint']}"
        last = _last_content(body)
        if last is None:
            return "the request carries no contents"
        m = entry["match"]
        if last.get("role") != "user":
            return f"the last content's role is {last.get('role')!r}, not user"
        parts = last.get("parts") or []
        if m["kind"] == "function_response":
            if not parts or not all(isinstance(p, dict) and set(p) >= {"functionResponse"} for p in parts):
                return "the last content is not a turn of functionResponse parts only"
            got = sorted(str(p["functionResponse"].get("id")) for p in parts)
            # the CLI names each call `<name>__<id>` when the id lacks that prefix (:333878-333880), and answers it so
            if got != sorted(cid for _n, cid in self.last_calls) \
                    and got != sorted(f"{n}__{cid}" for n, cid in self.last_calls):
                return "the function responses do not answer exactly the stub's previous calls"
            return None
        texts = _texts(last)
        if m["kind"] == "user_text":
            return None if m["text"] in texts else "no part of the last user content is the scripted text"
        if not texts or not texts[-1].startswith(m["prefix"]):
            return "the last user text does not start with the scripted prefix"
        return None

    # --------------------------------------------------------------------------------------------- responses
    def _usage(self, raw: bytes, respond: dict, candidates_text: str) -> dict:
        prompt = respond.get("prompt_tokens", len(raw) // 4)
        out = max(1, len(candidates_text) // 4)
        thoughts = max(1, len(json.dumps(respond["thought"])) // 4) if "thought" in respond else 0
        return {"promptTokenCount": prompt, "candidatesTokenCount": out, "cachedContentTokenCount": 0,
                "thoughtsTokenCount": thoughts, "toolUsePromptTokenCount": 0,
                "totalTokenCount": prompt + out + thoughts}

    def _parts(self, respond: dict) -> tuple:
        parts, ids = [], []
        text = respond.get("text")
        if "text_generated" in respond:
            text = generated_text(respond["text_generated"])
        if text:
            parts.append({"text": text})
        for c in respond.get("calls") or []:
            self.calls_issued += 1
            cid = f"call_{self.calls_issued}"
            ids.append((c["name"], cid))
            parts.append({"functionCall": {"id": cid, "name": c["name"], "args": c["args"]}})
        return parts, ids, text or ""

    def _thought_part(self, respond: dict):
        t = respond.get("thought")
        if not t:
            return None
        return {"text": f"**{t['subject']}**\n\n{t['description']}", "thought": True}

    def _respond(self, endpoint: str, raw: bytes, respond: dict) -> tuple:
        thought = self._thought_part(respond)
        parts, ids, text = self._parts(respond)
        usage = self._usage(raw, respond, text + json.dumps([p for p in parts if "functionCall" in p]))
        if endpoint == "stream":         # a helper's answer never changes which calls the chat must answer next
            self.last_calls = ids
        if endpoint == "generate":
            doc = {"candidates": [{"content": {"role": "model", "parts": ([thought] if thought else []) + parts},
                                   "finishReason": "STOP", "index": 0}], "usageMetadata": usage}
            return 200, "application/json", json.dumps(doc).encode("utf-8")
        chunks = []
        if thought:
            chunks.append({"candidates": [{"content": {"role": "model", "parts": [thought]}, "index": 0}]})
        chunks.append({"candidates": [{"content": {"role": "model", "parts": parts}, "finishReason": "STOP",
                                       "index": 0}], "usageMetadata": usage})
        body = b"".join(b"data: " + json.dumps(c, separators=(",", ":")).encode("utf-8") + b"\r\n\r\n" for c in chunks)
        return 200, "text/event-stream", body

    # ------------------------------------------------------------------------------------------------ handle
    def handle(self, method: str, path: str, raw: bytes) -> tuple:
        self.n += 1
        entry_log = {"n": self.n, "at": self.clock(), "method": method, "path": path,
                     "body_sha256": hashlib.sha256(raw).hexdigest(), "body_bytes": len(raw),
                     "flags": {"masked_tag": MASKED_TAG.encode() in raw, "truncation_text": TRUNCATED_TEXT.encode() in raw,
                               "state_snapshot": SNAPSHOT_TAG.encode() in raw}}
        m = _PATH.fullmatch(path.split("?", 1)[0]) if isinstance(path, str) else None
        endpoint = ENDPOINTS.get(m.group(3)) if m else None
        entry_log.update(model=m.group(2) if m else None, endpoint=endpoint, entry=None)
        try:
            body = json.loads(raw.decode("utf-8")) if raw else None
        except (UnicodeDecodeError, ValueError):
            body = None
        why = None
        if self.held is not None:
            why = f"the scenario is held: {self.held}"
        elif method != "POST" or endpoint is None:
            why = f"unscripted endpoint {method} {path.split('?', 1)[0] if isinstance(path, str) else path!r}"
        elif endpoint == "stream" and "alt=sse" not in (path.split("?", 1)[1] if "?" in path else ""):
            why = "the stream endpoint without alt=sse"
        elif body is None:
            why = "the request body is not JSON"
        elif self.next >= len(self.script["requests"]):
            why = "a request after the script's last entry"
        else:
            why = self._matches(self.script["requests"][self.next], endpoint, body)
        if self.out_dir is not None:
            with open(os.path.join(self.out_dir, "bodies", f"req-{self.n}.json"), "wb") as fh:
                fh.write(raw)
        if why is not None:
            if self.held is None:
                self.held = f"request {self.n}: {why}"
            entry_log.update(verdict="refused", why=why)
            out = (400, "application/json", json.dumps(ERROR_BODY).encode("utf-8"))
        else:
            entry_log.update(verdict="answered", entry=self.next + 1)
            out = self._respond(endpoint, raw, self.script["requests"][self.next]["respond"])
            self.next += 1
            entry_log["call_ids"] = [cid for _n, cid in self.last_calls] if endpoint == "stream" else []
        self.log.append(entry_log)
        if self.out_dir is not None:
            with open(os.path.join(self.out_dir, "requests.jsonl"), "a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry_log, sort_keys=True) + "\n")
            self._write_state()
        return out

    def state(self) -> dict:
        return {"scenario": self.script["scenario"], "next": self.next + 1, "of": len(self.script["requests"]),
                "requests": self.n, "held": self.held, "calls_issued": self.calls_issued,
                "done": self.held is None and self.next == len(self.script["requests"])}

    def _write_state(self) -> None:
        tmp = os.path.join(self.out_dir, "state.json.tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self.state(), fh, sort_keys=True)
        os.replace(tmp, os.path.join(self.out_dir, "state.json"))


# ------------------------------------------------------------------------------------- the --fake-responses file
FAKE_PROMPT_TOKENS = 1000      # no request is seen in advance, so an unnamed count is this fixed small number


def fake_records(script: dict) -> list:
    """The same script as the pinned CLI's FakeContentGenerator file (chunk-NR7L3FXV.js:312557-312623): one record per
    entry, {"method": "generateContentStream", "response": [chunks]} or {"method": "generateContent", "response":
    {...}}, built by the stub's own response code, so the cross-check (glitch-f1's ruling 4) answers with the same
    parts, call ids and finish reasons. Usage counts the stub would compute from a request are FAKE_PROMPT_TOKENS here
    (a named difference: the fake road sees no request first); a named count is kept."""
    stub = Stub(script)
    out = []
    for e in stub.script["requests"]:
        respond = dict(e["respond"])
        respond.setdefault("prompt_tokens", FAKE_PROMPT_TOKENS)
        _status, _ctype, body = stub._respond(e["endpoint"], b"", respond)
        if e["endpoint"] == "stream":
            chunks = [json.loads(seg[len(b"data: "):]) for seg in body.split(b"\r\n\r\n") if seg]
            out.append({"method": "generateContentStream", "response": chunks})
        else:
            out.append({"method": "generateContent", "response": json.loads(body)})
    return out


# ------------------------------------------------------------------------------------------------------ the server
def make_server(stub: Stub, port: int = 0):
    """An http.server bound to 127.0.0.1 only, one response per connection (Connection: close)."""
    import http.server

    class Handler(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def _serve(self):
            n = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(n) if n > 0 else b""
            status, ctype, body = stub.handle(self.command, self.path, raw)
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(body)
            self.close_connection = True

        # every verb reaches the stub, so it is logged and holds the scenario (REVIEW-vendor-b27-25ffff5 NIT 7)
        do_POST = do_GET = do_PUT = do_DELETE = do_HEAD = do_OPTIONS = do_PATCH = _serve

        def log_message(self, *args):   # the request log is requests.jsonl; nothing on stderr
            return

    return http.server.HTTPServer((HOST, port), Handler)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="the stub-model probe's scripted model (lane vendor-b27)")
    p.add_argument("--scenario", required=True)
    p.add_argument("--dir", required=True)
    p.add_argument("--port", type=int, default=0)
    p.add_argument("--daemon", action="store_true")
    a = p.parse_args(argv)
    with open(a.scenario, encoding="utf-8") as fh:
        script = json.load(fh)
    stub = Stub(script, a.dir)
    server = make_server(stub, a.port)
    port = server.server_address[1]
    if a.daemon:
        pid = os.fork()
        if pid:
            print(json.dumps({"ready": True, "port": port, "pid": pid}), flush=True)
            os._exit(0)
        os.setsid()
        devnull = os.open(os.devnull, os.O_RDWR)
        for fd in (0, 1, 2):
            os.dup2(devnull, fd)
    else:
        print(json.dumps({"ready": True, "port": port, "pid": os.getpid()}), flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
