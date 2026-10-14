# Gemini stream-side join (live harness slice 5)

Parent: `03a4f489`. Writer: Claude Code harness lane, 14 Oct 2026 00:46 EDT, under glitch-06's order for slice 5.
Unregistered: `vendor_provenance.NATIVE_SESSION_READERS` stays empty until a real recorded session is reviewed.

## Source grounding

The legacy non-interactive loop in the pinned 0.64.0 bundle (`gemini-legacy-content-source.json`) runs one model response per loop iteration:
- Each content event becomes an assistant `message` with `delta: true`. The text is ANSI-stripped unless raw output is configured.
- Each tool call request becomes a `tool_use`.
- The tools run, and their `tool_result`s are written before the next response starts.

The native recorder stores each response's text in `recorder_normalize`'s normal form, and stores nothing for a response whose normalized text is empty (`gemini-0.64.0-source-retained-2026-10-14.md`).

Inferred, not shown in the retained source: the stream's `tool_result` events come from the same loop iteration's tool execution. Only the `tool_use` emission and the loop structure are in the extract. The first recorded stream confirms or replaces this.

## Change

`gemini_stream_join.read_call` and `gemini_stream_join.join` work on one call's stream, read through `transcript_gemini.check_record`.

- **Text:** each response is every assistant delta after the previous `tool_result`. Responses are normalized per response with `recorder_normalize`, empty ones are dropped, and the list must equal the native `recorded-text` segments in order. Neither side is ever called displayed text.
- **Completeness:** an interaction is complete only with exactly one terminal `result`, which must be the stream's last record and have status success.
  - A failed result is kept with its error object, and the interaction counts as not complete.
  - No result, a cut stream, or any record after the result refuses.
- **Errors:** `error` events are kept in order.
- **Tools:** compared by id, name, order and status.
  - Every `tool_use` needs exactly one `tool_result` with its id.
  - Ids are never reused.
  - A `tool_result` naming no earlier `tool_use` refuses.
- **Sent text and model:** each is compared only when both sides have it. When the stream lacks one, it stays None.
- **Refused shapes:** non-delta assistant messages, a second init or user message, and an unknown native output item.

## Verification (each run behind a fresh light gate)

- Red: 6 tests, 20 errors (no module).
- Green: 8/8. The tool-order and call-reader tests were added after mutants.
- Two first-run test expectations were wrong, so I corrected the tests:
  - one case refused for a different reason than intended;
  - a second terminal result reads as "after the terminal result".
- `test_gemini_projection.py`: 6/6.
- Eleven in-memory mutants, each failing at least one assertion, candidate bytes unchanged. Five of them also raised errors in other tests:
  - stream text not normalized
  - responses joined
  - terminal optional
  - tool status ignored
  - tool order ignored
  - failed result counted complete
  - errors dropped
  - records after the result allowed
  - unknown native item ignored
  - missing `tool_result` allowed
  - sent not compared

## Not run, owed

- A real recorded 0.64.0 stream and session pair.
- The driver does not call the join yet. Wiring it in, and its registration, wait for that recording and its review.
- Independent review.

## Addendum, 14 Oct 2026 01:08 EDT: review nit 2

Tool arguments are now compared as well. Each stream `tool_use`'s `parameters` must equal the native tool fact's `args` as exact JSON: both are parsed, then spelled canonically with sorted keys. So `1`, `1.0` and `true` stay three different values, as JSON says they are, even where Python would call them equal.
A disagreement refuses with "tool arguments disagree".

The test gained four cases. They failed red with "JoinRefused not raised" before the change. Two mutants, "args not compared" and "Python equality", were killed by assertion.
