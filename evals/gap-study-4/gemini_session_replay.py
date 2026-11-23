"""Provisional Gemini 0.64.0 native JSONL replay, never production admission.

Derived from the installed bundle's createJsonlRecordAccumulator retained in
the box lane's gemini-native-session-source.json, not a recorded live session.
This returns raw replayed messages, NOT normalized checker facts. Message payload
fields remain uninterpreted until a separate reviewed semantic reader validates
them. The production registry reaches this replay only through gemini_projection,
the reviewed semantic reader (native_reader_registration's Gemini profile), and
only under a committed acceptance record whose reader_sources_sha256 holds
(lane vendor-b28, REVIEW-vendor-b28-DESIGN NIT 10: this line once said no
production registry imports it, written before registration existed).

Supports complete message upserts and ordinary content/tool-result patches.
Destructive history operations and unknown control records fail closed. Unlike
the vendor's recovery-oriented loader, malformed JSON and unknown patch targets
are never silently ignored.

Lane vendor-b25 (glitch-26's ruling 3; Gemini review BLOCKER 1): the resume
reorder. Read from the pinned package itself (@google/gemini-cli 0.64.0, tarball
sha256 891a794e..., bundle/chunk-NR7L3FXV.js sha256 d566e81b..., the chunk the
running CLI imports: bundle/gemini.js:10): on every chat start
GeminiChat.initialize calls ChatRecordingService.updateMessagesFromHistory
(chunk-NR7L3FXV.js:287151-287298), whose only $patch write is
appendRecord({$patch: patchPayload}) at :287265, patchPayload holding `updates`
(:287256-287258), `removeIds` (:287259-287261) and `orderIds`, the whole
history's ids in order (:287262-287264). The loader
(createJsonlRecordAccumulator, :286309-286455) applies a $patch in a fixed order:
the direct id patch, then `updates` (:286390-286399), then `removeIds`
(:286400-286414), then `orderIds` (:286415-286453): ids it lists move, in that
order, behind every id it does not list; an id listed twice keeps its first
place (Map.set on a present key, :286450-286452). Admitted here: exactly
{orderIds, updates}, every orderIds entry a string naming a known message, every
known message listed (a permutation, so no prefix is left), and an id listed
twice only when it is a `<gemini id>_response` id, which the resumed history
holds twice by construction (convertSessionToClientHistory, :286099-286194: the
synthetic `${msg.id}_response` turn at :286180-286188, and the stored message of
that id read back as a user turn at :286105-286117). removeIds (destructive),
orderIds without updates, and any other duplicate or unknown id refuse.

Lane vendor-b26 (glitch-26's rulings on the B26 design, lane-reports/vendor-b26-DESIGN.md; same pinned chunk):
the two-layer replay. Layer 1 replays as the loader does and labels every message: original (recorded live), resume
copy (a `<gemini id>_response` record first written inside a resume, after `$set {sessionId}`), or re-recorded copy.
Layer 2, `timeline`, is every original message at its state just before it left the loader's state (or at the end),
in first-record order; the projection reads facts from it only, never from a copy. Admitted `$patch` payloads are the
writer's only (:287254-287265: keys updates, removeIds, orderIds; a top-level id, content or toolCalls is never
written and refuses):
  * {updates}: content or tool-result changes only. Each update is the writer's getOrCreatePatch object
    (:287159-287166): {id} with content (the turn's parts array, :287168, :287182) and/or toolCalls (a list of
    {id, result}, result the user turn's parts array, :287202, :287223-287228); ids unique; each names a live message.
  * {orderIds, updates}: the resume reorder (lane vendor-b25), after which every live resume copy must sit directly
    after its gemini message and directly before a byte-identical original round trip, and the originals must keep
    their first-record order.
  * {orderIds, removeIds, updates} (shape B), inside a resume: removeIds names live original user prompts the resume
    dropped as ignored content (isIgnoredUserContent, :286096-286098, :286105-286110: the text, trimmed, empty or
    starting "/", "?", "<session_context>" or "<hook_context>"); applied in the loader's order (updates, removeIds,
    orderIds, :286390-286453). The removed prompt's fact state is frozen; it stays in the timeline.
  * {removeIds} or {removeIds, updates} (shape A): the re-record. GeminiClient.processTurn runs tryMaskToolOutputs
    before every model request (:348251, :348592-348597); a masking pass hands GeminiChat.setHistory the whole history
    without ids, coalesced (:333696-333712, :334192-334213), and setHistory records every turn again through
    recordSyntheticMessage (:333750-333762, :286934-286941) before updateMessagesFromHistory removes every older id
    (:287236, :287259-287261). Admitted only when: removeIds' first occurrences are the loader's state minus the
    survivors, in order, a repeat only of a `_response` id (the writer's messageOrder after a second resume); the
    survivors are exactly the messages first recorded since the previous `$patch`, at its end, each on the synthetic
    shape (user {id, timestamp, type, content}; gemini {id, timestamp, type, content, thoughts: [], tokens: null},
    :286910-286930); every update is a dead {id, toolCalls: [{id, result}]} write on a removed gemini message's own
    call (:287198-287229), verified and never applied to a fact; and the image check binds the run to the removed
    state: one survivor per coalesced role run; per run, equal multisets of function calls in full (id, name and
    arguments: the writer copies each call unchanged; glitch-f1's ruling 2 on REVIEW-vendor-b26-04c4e77 MINOR 2) and of
    function-response (id, name), where the first occurrence of a repeated `_response` id counts the concatenated
    toolCalls results of its base gemini message (the synthetic turn the CLI builds, :286158-286188; glitch-26's
    ruled deviation on ruling 5); every re-recorded response part equal to one of its id's originals or the masked
    form ({output} holding "<tool_output_masked", :344663, :344871-344877); equal user text parts and non-empty model
    text parts, in order. The removed originals' fact states are frozen as they stood before the patch.

Lane vendor-b28 (glitch-f1's B27 rulings 3 and 5 and B27 DECISION, 21 Oct 2026; observed on the pinned client against a
stub, lane vendor-b27's probe, never on the real API): road (a), the resume after a masking re-record, admitted on its
observed shapes (probe scenarios A1, A2, A3 and B2's masking span). The re-record deleted the context id from the
writer's index (:287237-287241); the next `-r` resume's chat start finds the stored context copy ignored
(convertSessionToClientHistory, :286096-286110), prepends a fresh context turn under deriveStableId(["environment-context"])
(getInitialChatHistory, :336356-336375) and updateMessagesFromHistory appends it as new (:287190-287196), then writes
$patch {orderIds, removeIds, updates} in the same initialize call (:333190-333192, :287254-287265). Admitted only when:
  * the re-entry is the first record after $set {sessionId}, of a retired context id, on newMessage's shape
    (:286901-286908: {id, timestamp, type, content}, type user) with one text part in the session-context wrapper
    (gemini_projection's ENV_CONTEXT_OPEN and ENV_CONTEXT_CLOSE); it becomes a copy ("resumed context turn", in
    `copies`), never a fact: the frozen original stays in the timeline;
  * the resume's patch is {orderIds, removeIds, updates} inside the window; every removed re-recorded copy is a user
    copy on text parts only whose trimmed text is ignored, exactly one of them the re-recorded context copy, and no
    such copy stays live (the completeness rule, glitch-f1's ruling O6); removed originals pass shape B's own check;
    after the reorder the context turn is first.
Refused by name: the re-entry anywhere else ("not the first record after its resume's $set {sessionId}"), off its shape
("off getInitialChatHistory's shape"), a context record while its resumed copy is live ("recorded again while its
resumed copy is live"), any other patch while it waits ("not consumed by its resume's {orderIds, removeIds, updates}
patch"; a re-record shape runs the re-record's checks first, so true compression keeps its name), the patch's removals
off the rule ("not ignored content", "exactly one re-recorded context copy", "keeps a re-recorded copy the CLI drops"),
the context turn off the front ("not first after the resume's reorder") and a snapshot ending before the patch
("without its resume's patch"), and any $set between the re-entry and its patch ("a $set between a re-entered
context turn and its resume's patch": the writer writes both in one initialize call, :333190-333192).
F-B26-9 (glitch-f1's 15:45 ruling, 21 Oct): inside a resume the writer appends only the context turn and `<gemini id>_response`
turns (:287190-287196 with :286099-286194), so any other message record closes the resume window.

Still refused by name (glitch-26's ruling 3 and glitch-f1's B27 rulings 1 and 2): a retired id other than the context
turn recorded again; true chat compression (the context turn survives a re-record, :337254-337292, :348563-348580),
both observed key sets: B1's {removeIds, updates} with the context turn live, and B2's {removeIds} after a road (a)
re-entry; and content truncation (a re-recorded response neither original nor masked). `properties` counts each road
per snapshot: re-records, masked parts, ignored-prompt resumes, resumes after a re-record.
The precedence before lane vendor-b28 (5457e75e), kept as history: B1 was refused by the unobserved resume-shape rule
({removeIds, updates} inside a resume) before the compression rule, and B2 by the retired-id rule at its re-entry;
now B1 meets the compression name through F-B26-9's close alone, and B2 through its road (a) re-entry, that close and
the re-record's checks run before the pending-patch refusal.
"""
import hashlib
import json
from collections import Counter
from copy import deepcopy

import transcript_view as tv
from vendor_record_binding import _json, _jsonl_lines


class ReplayRefused(ValueError):
    """Native recording contains an unsupported or contradictory replay operation."""


METADATA_KEYS = {"sessionId", "projectHash", "startTime", "lastUpdated", "kind", "directories", "summary"}
MESSAGE_KINDS = {"user", "gemini", "info", "error", "warning"}
RESPONSE_SUFFIX = "_response"        # convertSessionToClientHistory's synthetic turn id, chunk-NR7L3FXV.js:286182
CONTEXT_ID = hashlib.sha256(b"environment-context").hexdigest()[:32]   # deriveStableId, :286041-286044, :336369
SYNTHETIC_USER_KEYS = {"id", "timestamp", "type", "content"}
SYNTHETIC_GEMINI_KEYS = {"id", "timestamp", "type", "content", "thoughts", "tokens"}
MASK_TAG = "<tool_output_masked"     # MASKING_INDICATOR_TAG, :344663
IGNORED_PREFIXES = ("/", "?", "<session_context>", "<hook_context>")
# JavaScript's String.prototype.trim: WhiteSpace and LineTerminator code points (as gemini_projection spells it).
JS_TRIM = ("\t\n\x0b\x0c\r \xa0            "
           "    　﻿")
ORIGINAL, RESUME_COPY, RERECORDED = "original", "resume copy", "re-recorded copy"
# Lane vendor-b28 (road (a), glitch-f1's B27 rulings 3 and 5): the context turn re-appended by the resume after a masking
# re-record, under its stable id; a copy, never a fact source.
CONTEXT_COPY = "resumed context turn"
# getEnvironmentContext's wrapper, as gemini_projection spells it (ENV_CONTEXT_OPEN and ENV_CONTEXT_CLOSE); copied here so
# no other reader source changes, and pinned equal by tests/test_b28_resume_after_rerecord.py.
CONTEXT_OPEN = "<session_context>\nThis is the Gemini CLI. We are setting up the context for our chat.\n"
CONTEXT_CLOSE = "</session_context>"
# Lane vendor-b26 fold (glitch-f1's ruling 4, REVIEW-vendor-b26-04c4e77 MINOR 4; the orchestrator's 14:08 ruling): four
# resume $patch shapes the pinned writer can write (:287254-287265 writes each key only when it has entries) but no
# committed walk shows. By :286764-286783 and :286120-286150 a resume writes a content update for every gemini message
# carrying thoughts or tool calls, so each needs a take with neither. They stay refused, each by its own name, so a
# survey counts them apart from corrupt files (the false-refusal residual, recorded in the lane file).
UNOBSERVED_RESUME_SHAPES = {
    frozenset({"orderIds"}): "writer-possible resume shape {orderIds} (a resume with no update), unobserved in any "
                             "walk: refused by name (glitch-f1's ruling 4)",
    frozenset({"orderIds", "removeIds"}): "writer-possible resume shape {orderIds, removeIds} (an ignored prompt "
                                          "dropped, no update), unobserved in any walk: refused by name (glitch-f1's "
                                          "ruling 4)",
    frozenset({"removeIds", "updates"}): "writer-possible resume shape {removeIds, updates} inside a resume (an "
                                         "ignored prompt dropped, the order unchanged), unobserved in any walk: "
                                         "refused by name (glitch-f1's ruling 4)",
    # glitch-f1's ruling on the fold's question (21 Oct 2026): {removeIds} alone inside a resume, writer-possible for
    # the same reason (an ignored prompt dropped, no update, the order unchanged) and unseen in every walk.
    frozenset({"removeIds"}): "writer-possible resume shape {removeIds} alone inside a resume (an ignored prompt "
                              "dropped, no update, the order unchanged), unobserved in any walk: refused by name "
                              "(glitch-f1's ruling 4)",
}


def _string(value):
    return isinstance(value, str) and bool(value)


def _tools(message):
    tools = message.get("toolCalls", [])
    if not isinstance(tools, list):
        raise ReplayRefused("native toolCalls must be an array")
    ids = set()
    for tool in tools:
        if not isinstance(tool, dict) or not _string(tool.get("id")) or tool["id"] in ids:
            raise ReplayRefused("native tools need unique nonempty ids")
        ids.add(tool["id"])
    return tools


def _patch(messages, patch):
    """One writer patch object (module docstring): {id} with content and/or toolCalls, arrays only."""
    if (not isinstance(patch, dict) or not set(patch) <= {"id", "content", "toolCalls"}
            or not _string(patch.get("id")) or not ({"content", "toolCalls"} & set(patch))):
        raise ReplayRefused("unknown or empty native message patch")
    target = messages.get(patch["id"])
    if target is None:
        raise ReplayRefused("native message patch target is absent")
    if "content" in patch:
        if not isinstance(patch["content"], list):
            raise ReplayRefused("native patch content is not a part array (the recorder writes the turn's parts, "
                                "chunk-NR7L3FXV.js:287168, :287182)")
        target["content"] = deepcopy(patch["content"])
    if "toolCalls" in patch:
        if target["type"] != "gemini" or not isinstance(patch["toolCalls"], list):
            raise ReplayRefused("tool-result patch requires a Gemini message and array")
        tools = {tool["id"]: tool for tool in _tools(target)}
        for change in patch["toolCalls"]:
            if (not isinstance(change, dict) or set(change) != {"id", "result"}
                    or not _string(change["id"]) or change["id"] not in tools):
                raise ReplayRefused("native tool-result patch target or shape is unknown")
            if not isinstance(change["result"], list):
                raise ReplayRefused("native tool-result patch result is not a part array (the recorder writes the "
                                    "user turn's parts, chunk-NR7L3FXV.js:287202, :287227)")
            tools[change["id"]]["result"] = deepcopy(change["result"])


def _updates(messages, updates):
    if not isinstance(updates, list) or not updates:
        raise ReplayRefused("native patch updates must be a nonempty array")
    ids = [u.get("id") if isinstance(u, dict) else None for u in updates]
    if len(set(map(str, ids))) != len(ids):
        raise ReplayRefused("native patch updates name one message twice (one patch per id, chunk-NR7L3FXV.js:287158-287166)")
    for update in updates:
        _patch(messages, update)


def _reorder(messages, order):
    """The resume's orderIds (lane vendor-b25): a permutation of the known messages, a repeat only of a
    `<gemini id>_response` id; the first occurrence keeps its place."""
    if not isinstance(order, list) or not order or not all(_string(i) for i in order):
        raise ReplayRefused("native orderIds must be a nonempty array of ids")
    if any(i not in messages for i in order):
        raise ReplayRefused("native orderIds names an unknown message")
    if set(order) != set(messages):
        raise ReplayRefused("native orderIds is not a permutation of the known messages")
    seen = set()
    for i in order:
        if i in seen and not _response_of_gemini(messages, i):
            raise ReplayRefused("native orderIds repeats an id that is not a <gemini id>_response turn")
        seen.add(i)
    # Lane vendor-b26 (B25 review MINOR 3): at most two listings. A resumed history holds a `_response` id once as the
    # synthetic turn (:286180-286188) and once as the stored copy read back as a user turn (:286105-286117); the
    # recorder's map keeps one message per id, so no later resume can list it a third time.
    if any(n > 2 for n in Counter(order).values()):
        raise ReplayRefused("native orderIds lists a <gemini id>_response turn more than twice")
    reordered = {}
    for i in order:
        if i not in reordered:                     # Map.set on a present key keeps its first place
            reordered[i] = messages[i]
    messages.clear()
    messages.update(reordered)


def _response_of_gemini(messages, i):
    base = i[:-len(RESPONSE_SUFFIX)] if i.endswith(RESPONSE_SUFFIX) else None
    return bool(base and messages[i]["type"] == "user" and base in messages and messages[base]["type"] == "gemini")


def _tool_response_turn(message):
    content = message.get("content")
    return (message.get("type") == "user" and isinstance(content, list) and bool(content)
            and all(isinstance(p, dict) and set(p) == {"functionResponse"} for p in content))


def _serialized(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False)


def _canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)


def _text_parts(message):
    content = message.get("content")
    if isinstance(content, str):
        return [content]
    return [p["text"] for p in content if isinstance(p, dict) and isinstance(p.get("text"), str)
            and not p.get("thought")] if isinstance(content, list) else []


def _calls(message):
    """A gemini message's calls in full, (id, name, arguments): its toolCalls, else its content's functionCall parts
    (a copy). Lane vendor-b26 fold (glitch-f1's ruling 2, REVIEW-vendor-b26-04c4e77 MINOR 2): the arguments are bound
    too, so a re-recorded copy can never carry arguments its original did not (the scanner reads the originals')."""
    if message["type"] != "gemini":
        return []
    if message.get("toolCalls"):
        return [(t["id"], t.get("name"), _canonical(t.get("args"))) for t in message["toolCalls"]]
    content = message.get("content")
    return [(p["functionCall"].get("id"), p["functionCall"].get("name"), _canonical(p["functionCall"].get("args")))
            for p in content if isinstance(p, dict) and isinstance(p.get("functionCall"), dict)
            ] if isinstance(content, list) else []


def _responses(message):
    content = message.get("content")
    return [p["functionResponse"] for p in content if isinstance(p, dict) and isinstance(p.get("functionResponse"), dict)
            ] if message["type"] == "user" and isinstance(content, list) else []


class _Replay:
    def __init__(self, metadata):
        self.metadata = metadata
        self.live = {}            # the loader's state, Map order
        self.kind = {}            # id -> ORIGINAL | RESUME_COPY | RERECORDED
        self.first = {}           # id -> record number of its first write
        self.frozen = {}          # original id -> its fact state when it left the loader's state
        self.retired = set()      # every id a removal took out
        self.since = []           # ids first written since the last $patch
        self.resume = False       # inside a resume: after $set {sessionId}, before its $patch
        self.others = []          # every non-original message that left the loader's state (for the scanner)
        self.dead = []            # every dead re-record update's tool results (for the scanner)
        self.props = Counter()
        self.verified = set()     # resume copies checked at their resume's reorder
        self.resume_at = None     # the record number of the last $set {sessionId} (lane vendor-b28)
        self.ctx_pending = False  # the context turn re-entered in this resume, awaiting its patch (lane vendor-b28)

    # ---- the patches ------------------------------------------------------------------------------------------------
    def patch(self, patch):
        if not isinstance(patch, dict) or not patch:
            raise ReplayRefused("unsupported native patch operation")
        keys = set(patch)
        if keys & {"id", "content", "toolCalls"}:
            raise ReplayRefused("a direct-id native patch is never written by the pinned recorder "
                                "(chunk-NR7L3FXV.js:287254-287265)")
        if self.resume and frozenset(keys) in UNOBSERVED_RESUME_SHAPES:
            raise ReplayRefused(UNOBSERVED_RESUME_SHAPES[frozenset(keys)])
        # Lane vendor-b28 (REVIEW-vendor-b28-DESIGN MINOR 2, ruled): a re-entered context turn is consumed only by its
        # resume's {orderIds, removeIds, updates} patch inside the open window; any other patch refuses, whatever the
        # window's state. A re-record shape runs the re-record's own checks first, so true compression keeps its name.
        if self.ctx_pending and not (self.resume and keys == {"orderIds", "removeIds", "updates"}):
            if keys in ({"removeIds"}, {"removeIds", "updates"}):
                self._rerecord(patch)
            raise ReplayRefused("a context turn re-entered after a re-record is not consumed by its resume's {orderIds, "
                                "removeIds, updates} patch (chunk-NR7L3FXV.js:333190-333192, :287254-287265)")
        if keys == {"updates"}:
            _updates(self.live, patch["updates"])
        elif keys == {"orderIds", "updates"}:
            _updates(self.live, patch["updates"])
            self._resume_order(patch["orderIds"])
        elif keys == {"orderIds", "removeIds", "updates"}:
            if not self.resume:
                raise ReplayRefused("native patch removes and reorders outside a resume")
            # Lane vendor-b26 fold (glitch-f1's ruling 3): each removed id is checked first, then no update may name
            # one, so the removed prompts read the same before and after the loader's updates (:286390-286399).
            self._ignored_prompts(patch["removeIds"])
            if self.ctx_pending:
                self._context_copies(patch["removeIds"])
            if isinstance(patch["updates"], list) and any(
                    isinstance(u, dict) and u.get("id") in patch["removeIds"] for u in patch["updates"]):
                raise ReplayRefused("a resume updates the prompt it removes (the recorder writes content patches only "
                                    "for history turns, chunk-NR7L3FXV.js:287167-287183, and a removed prompt is not "
                                    "one)")
            _updates(self.live, patch["updates"])
            self._retire(patch["removeIds"])
            self._resume_order(patch["orderIds"])
            if self.ctx_pending:
                if list(self.live)[:1] != [CONTEXT_ID]:
                    raise ReplayRefused("the resumed context turn is not first after the resume's reorder "
                                        "(getInitialChatHistory, chunk-NR7L3FXV.js:336366-336375)")
                self.ctx_pending = False
                self.props["resumes_after_rerecord"] += 1
            else:
                self.props["ignored_prompt_resumes"] += 1
        elif keys in ({"removeIds"}, {"removeIds", "updates"}):
            self._rerecord(patch)
        else:
            raise ReplayRefused("unsupported native patch operation")
        self.since = []
        self.resume = False       # the resume window closes at its $patch, whatever its shape (lane vendor-b26 fold)

    def _resume_order(self, order):
        _reorder(self.live, order)
        self.resume = False
        ids = list(self.live)
        for k, i in enumerate(ids):
            if self.kind[i] != RESUME_COPY:
                continue
            gemini = self.live[ids[k - 1]] if k else None
            following = self.live[ids[k + 1]] if k + 1 < len(ids) else None
            copy = self.live[i]
            if not (gemini is not None and gemini["type"] == "gemini" and i == gemini["id"] + RESPONSE_SUFFIX
                    and _tool_response_turn(copy) and following is not None
                    and self.kind[following["id"]] == ORIGINAL and _tool_response_turn(following)
                    and set(following) == set(copy) and _serialized(following["content"]) == _serialized(copy["content"])):
                raise ReplayRefused("a <gemini id>_response turn is not the resumed copy of the round trip that "
                                    "follows it (byte-identical, directly after its gemini message)")
            self.verified.add(i)
        originals = [i for i in ids if self.kind[i] == ORIGINAL]
        if originals != sorted(originals, key=self.first.get):
            raise ReplayRefused("the native order of original messages changed")

    def _retire(self, ids):
        for i in ids:
            if i not in self.live:
                continue
            message = self.live.pop(i)
            self.retired.add(i)
            if self.kind[i] == ORIGINAL:
                self.frozen[i] = message
            else:
                self.others.append(message)

    def _ignored_prompts(self, remove):
        """Check every removed id is a live original ignored user prompt; the caller retires them."""
        if not isinstance(remove, list) or not remove or not all(_string(i) for i in remove) \
                or len(set(remove)) != len(remove):
            raise ReplayRefused("native resume removeIds must be a nonempty array of distinct ids")
        for i in remove:
            message = self.live.get(i)
            if message is None:
                raise ReplayRefused("native resume removes an unknown message")
            text = "".join(_text_parts(message)).strip(JS_TRIM)
            if self.ctx_pending and self.kind[i] == RERECORDED:
                continue                  # road (a): checked by _context_copies (lane vendor-b28)
            if self.kind[i] == RERECORDED and message["type"] == "user" and text.startswith("<session_context>"):
                raise ReplayRefused("the resume after a history re-record (it drops the re-recorded context turn): "
                                    "source-predicted, unobserved; refused by name (glitch-26's ruling 3)")
            content = message.get("content")
            if not (self.kind[i] == ORIGINAL and message["type"] == "user" and i != CONTEXT_ID
                    and isinstance(content, list) and content
                    and all(isinstance(p, dict) and set(p) == {"text"} and isinstance(p["text"], str) for p in content)
                    and (not text or text.startswith(IGNORED_PREFIXES))):
                raise ReplayRefused("a resume removes a message that is not an ignored user prompt "
                                    "(isIgnoredUserContent, chunk-NR7L3FXV.js:286096-286110)")

    def _ignored_copy(self, i):
        """A re-recorded user copy convertSessionToClientHistory drops: text parts only, and its joined text, trimmed,
        empty or starting with an ignored prefix (chunk-NR7L3FXV.js:286096-286110)."""
        m = self.live[i]
        content = m.get("content")
        text = "".join(_text_parts(m)).strip(JS_TRIM)
        return (self.kind.get(i) == RERECORDED and m["type"] == "user" and isinstance(content, list) and bool(content)
                and all(isinstance(p, dict) and set(p) == {"text"} and isinstance(p["text"], str) for p in content)
                and (not text or text.startswith(IGNORED_PREFIXES)))

    def _context_copies(self, remove):
        """Road (a)'s removals (lane vendor-b28): every removed re-recorded copy is one the CLI drops, exactly one of
        them the re-recorded context copy, and no such copy stays live (glitch-f1's ruling O6, the completeness rule:
        convertSessionToClientHistory drops every one, :286105-286110, and the writer removes every id the history
        lacks, :287232-287236)."""
        copies = [i for i in remove if self.kind.get(i) == RERECORDED]
        if not all(self._ignored_copy(i) for i in copies):
            raise ReplayRefused("a resume after a re-record removes a re-recorded copy that is not ignored content "
                                "(convertSessionToClientHistory keeps it, chunk-NR7L3FXV.js:286105-286117)")
        heads = [i for i in copies if "".join(_text_parts(self.live[i])).strip(JS_TRIM).startswith("<session_context>")]
        if len(heads) != 1:
            raise ReplayRefused("a resume after a re-record must drop exactly one re-recorded context copy")
        if any(i not in remove and self._ignored_copy(i) for i in self.live):
            raise ReplayRefused("a resume after a re-record keeps a re-recorded copy the CLI drops "
                                "(chunk-NR7L3FXV.js:286105-286110, :287232-287236)")

    def _rerecord(self, patch):
        remove = patch["removeIds"]
        if not isinstance(remove, list) or not remove or not all(_string(i) for i in remove):
            raise ReplayRefused("native re-record removeIds must be a nonempty array of ids")
        if any(i not in self.live for i in remove):
            raise ReplayRefused("native re-record removes an unknown message")
        counts = Counter(remove)
        if any(n > 1 and not _response_of_gemini(self.live, i) for i, n in counts.items()):
            raise ReplayRefused("native re-record repeats an id that is not a <gemini id>_response turn")
        if any(n > 2 for n in counts.values()):
            raise ReplayRefused("native re-record lists a <gemini id>_response turn more than twice")
        survivors = [i for i in self.live if i not in counts]
        if list(dict.fromkeys(remove)) != [i for i in self.live if i in counts]:
            raise ReplayRefused("native re-record's removeIds is not the loader's order")
        run_ok = bool(survivors) and survivors == self.since[-len(survivors):]
        if not run_ok and survivors and survivors[0] == CONTEXT_ID and len(survivors) > 1 \
                and survivors[1:] == self.since[-(len(survivors) - 1):]:
            raise ReplayRefused("native chat compression (the context turn survives a re-record): source-predicted, "
                                "unobserved; refused by name (glitch-26's ruling 3)")
        if not run_ok:
            raise ReplayRefused("native re-record leaves an older message live, or its survivors are not the messages "
                                "recorded just before it")
        run = [self.live[i] for i in survivors]
        for m in run:
            keys = SYNTHETIC_USER_KEYS if m["type"] == "user" else SYNTHETIC_GEMINI_KEYS
            if (m["type"] not in ("user", "gemini") or set(m) != keys or not isinstance(m["content"], list)
                    or (m["type"] == "gemini" and (m["thoughts"] != [] or m["tokens"] is not None))):
                raise ReplayRefused("a re-recorded message is not on the recordSyntheticMessage shape "
                                    "(chunk-NR7L3FXV.js:286910-286941)")
        if "updates" in patch and (not isinstance(patch["updates"], list) or not patch["updates"]):
            raise ReplayRefused("native patch updates must be a nonempty array")
        dead = []
        for update in patch.get("updates", []):
            target = self.live.get(update.get("id")) if isinstance(update, dict) else None
            if (target is None or set(update) != {"id", "toolCalls"} or update["id"] not in counts
                    or target["type"] != "gemini" or not isinstance(update["toolCalls"], list) or not update["toolCalls"]):
                raise ReplayRefused("a re-record update is not a dead toolCalls write on a removed gemini message")
            own = {t["id"] for t in _tools(target)}
            for change in update["toolCalls"]:
                if (not isinstance(change, dict) or set(change) != {"id", "result"} or change.get("id") not in own
                        or not isinstance(change["result"], list)):
                    raise ReplayRefused("a re-record update names a call its message lacks, or is off its shape")
                dead.append({"id": change["id"], "result": deepcopy(change["result"])})
        masked = self._image(remove, counts, run)
        self.dead += dead
        self._retire(list(counts))
        for i in survivors:
            self.kind[i] = RERECORDED
        self.props["history_rewrites"] += 1
        self.props["tool_outputs_masked"] += masked

    def _image(self, remove, counts, run):
        """The image check (module docstring); returns the number of masked parts."""
        pre = [self.live[i] for i in remove]
        if any(m["type"] not in ("user", "gemini") for m in pre):
            raise ReplayRefused("native re-record removes a message that is neither user nor gemini")
        groups = []
        for m in pre:
            if not groups or groups[-1][0] != m["type"]:
                groups.append((m["type"], []))
            groups[-1][1].append(m)
        if [g[0] for g in groups] != [m["type"] for m in run]:
            raise ReplayRefused("native re-record image: its coalesced role runs differ")
        masked, seen = 0, set()
        for (role, messages), image in zip(groups, run):
            expected = []
            for m in messages:
                if m["id"].endswith(RESPONSE_SUFFIX) and counts[m["id"]] > 1 and m["id"] not in seen:
                    base = self.live[m["id"][:-len(RESPONSE_SUFFIX)]]
                    expected += [p["functionResponse"] for t in base.get("toolCalls") or []
                                 for p in t.get("result") or [] if isinstance(p, dict) and "functionResponse" in p]
                else:
                    expected += _responses(m)
                seen.add(m["id"])
            got = _responses(image)
            if Counter(_calls(image)) != Counter(c for m in messages for c in _calls(m)):
                raise ReplayRefused("native re-record image: a run's function calls differ")
            pair = lambda r: (r.get("id"), r.get("name"))
            if Counter(map(pair, got)) != Counter(map(pair, expected)):
                raise ReplayRefused("native re-record image: a run's function responses differ in id or count")
            originals = {}
            for r in expected:
                originals.setdefault(r.get("id"), set()).add(_canonical(r))
            for r in got:
                if _canonical(r) in originals.get(r.get("id"), ()):
                    continue
                out = r.get("response")
                if set(r) == {"id", "name", "response"} and isinstance(out, dict) and set(out) == {"output"} \
                        and isinstance(out["output"], str) and MASK_TAG in out["output"]:
                    masked += 1
                    continue
                raise ReplayRefused("a re-recorded function response is neither one of its originals nor masked "
                                    "(content truncation stays refused by name until observed)")
        users = lambda ms: [t for m in ms if m["type"] == "user" for t in _text_parts(m)]
        models = lambda ms: [t for m in ms if m["type"] == "gemini" for t in _text_parts(m) if t]
        if users(run) != users(pre):
            raise ReplayRefused("native re-record image: the user text differs")
        if models(run) != models(pre):
            raise ReplayRefused("native re-record image: the model text differs")
        return masked

    # ---- the records -----------------------------------------------------------------------------------------------
    def message(self, n, record):
        i = record["id"]
        # F-B26-9 (glitch-f1's 15:45 ruling, 21 Oct; lane vendor-b28): inside a resume the writer appends only the context turn
        # and `<gemini id>_response` turns (chunk-NR7L3FXV.js:287190-287196 with :286099-286194), so any other record
        # closes the window.
        if self.resume and i != CONTEXT_ID and not i.endswith(RESPONSE_SUFFIX):
            self.resume = False
        if i == CONTEXT_ID and self.kind.get(i) == CONTEXT_COPY and i in self.live:
            raise ReplayRefused("the context turn is recorded again while its resumed copy is live (the writer patches "
                                "an indexed id, chunk-NR7L3FXV.js:287170-287188, and appends it once)")
        if i == CONTEXT_ID and i in self.retired and self.resume:
            self._context_reentry(n, record)
            return
        if i in self.retired:
            raise ReplayRefused("a retired native message id is recorded again (the resume after a history "
                                "re-record: source-predicted, unobserved; refused by name, glitch-26's ruling 3)")
        previous = self.live.get(i)
        if previous is not None and previous["type"] != record["type"]:
            raise ReplayRefused("native message role changed under the same id")
        _tools(record)
        if i not in self.kind:
            self.kind[i] = RESUME_COPY if self.resume and i.endswith(RESPONSE_SUFFIX) else ORIGINAL
            self.first[i] = n
            self.since.append(i)
        # Python dict assignment mirrors Map.set: replacing a value retains order.
        self.live[i] = record

    def _context_reentry(self, n, record):
        """Road (a) (lane vendor-b28): the context turn a masking re-record retired, re-appended by the next resume's
        chat start as the first record after its $set {sessionId}, on newMessage's shape (:286901-286908) holding
        getInitialChatHistory's one text part (:336356-336375). It becomes a copy (to `copies`, read by the scanner); the
        frozen original stays the fact. Its resume's patch must consume it (patch, result)."""
        if n - 1 != self.resume_at:
            raise ReplayRefused("a re-entered context turn is not the first record after its resume's $set {sessionId} "
                                "(the history starts with it, chunk-NR7L3FXV.js:287167-287196, :336366-336375)")
        content = record.get("content")
        if not (set(record) == SYNTHETIC_USER_KEYS and record["type"] == "user" and isinstance(content, list)
                and len(content) == 1 and isinstance(content[0], dict) and set(content[0]) == {"text"}
                and isinstance(content[0]["text"], str) and content[0]["text"].startswith(CONTEXT_OPEN)
                and content[0]["text"].endswith(CONTEXT_CLOSE)):
            raise ReplayRefused("a re-entered context turn is off getInitialChatHistory's shape (one user text part "
                                "in the session-context wrapper, chunk-NR7L3FXV.js:336356-336375, :286901-286908)")
        self.retired.discard(CONTEXT_ID)
        self.kind[CONTEXT_ID] = CONTEXT_COPY
        self.live[CONTEXT_ID] = record
        self.ctx_pending = True

    def result(self):
        if self.ctx_pending:
            raise ReplayRefused("a context turn re-entered after a re-record without its resume's patch "
                                "(the writer writes both in one initialize call, chunk-NR7L3FXV.js:333190-333192)")
        if any(k == RESUME_COPY and i not in self.verified for i, k in self.kind.items()):
            raise ReplayRefused("a <gemini id>_response turn is not the resumed copy of the round trip that follows it "
                                "(no resume reorder placed it)")
        facts = dict(self.frozen)
        facts.update({i: m for i, m in self.live.items() if self.kind[i] == ORIGINAL})
        timeline = [facts[i] for i in sorted(facts, key=self.first.get)]
        others = [m for i, m in self.live.items() if self.kind[i] != ORIGINAL] + self.others
        return {"metadata": self.metadata, "messages": list(self.live.values()), "timeline": timeline,
                "copies": others, "dead_results": self.dead,
                "properties": {k: self.props[k] for k in ("history_rewrites", "tool_outputs_masked",
                                                          "ignored_prompt_resumes", "resumes_after_rerecord")}}


def replay(raw):
    """Replay one retained native snapshot; no prompt/output/terminal claims. `messages` is the loader's state,
    `timeline` the original messages the projection reads (module docstring)."""
    if not isinstance(raw, bytes):
        raise ReplayRefused("native replay requires retained bytes")
    try:
        records = [_json(line) for line in _jsonl_lines(raw.decode("utf-8"))]
    except (UnicodeError, tv.ViewError):
        raise ReplayRefused("native session is not complete UTF-8 JSONL") from None
    if not records:
        raise ReplayRefused("native session is empty")
    metadata = records[0]
    if (not isinstance(metadata, dict) or not set(metadata) <= METADATA_KEYS
            or not all(_string(metadata.get(k)) for k in ("sessionId", "projectHash"))):
        raise ReplayRefused("native session must begin with identity metadata")
    state = _Replay(metadata)
    for n, record in enumerate(records[1:], 2):
        if not isinstance(record, dict):
            raise ReplayRefused("native session record is not an object")
        controls = [key for key in record if key.startswith("$")]
        if controls:
            if len(record) != 1:
                raise ReplayRefused("mixed native control record")
            if "$set" in record:
                if state.ctx_pending:
                    raise ReplayRefused("a $set between a re-entered context turn and its resume's patch (the writer "
                                        "writes both in one initialize call, chunk-NR7L3FXV.js:333190-333192)")
                update = record["$set"]
                if not isinstance(update, dict) or not update or not set(update) <= {"sessionId", "lastUpdated"}:
                    raise ReplayRefused("unsupported native metadata update")
                if any(not _string(value) for value in update.values()):
                    raise ReplayRefused("native metadata update is not a nonempty string")
                if update.get("sessionId", metadata["sessionId"]) != metadata["sessionId"]:
                    raise ReplayRefused("native session identity changed")
                metadata.update(update)
                if "sessionId" in update:
                    state.resume = True
                    state.resume_at = n
            elif "$patch" in record:
                state.patch(record["$patch"])
            else:
                raise ReplayRefused("unsupported destructive or unknown native operation")
        else:
            if (not _string(record.get("id")) or not isinstance(record.get("type"), str)
                    or record["type"] not in MESSAGE_KINDS or "content" not in record):
                raise ReplayRefused("unknown native message record")
            state.message(n, record)
    return state.result()
