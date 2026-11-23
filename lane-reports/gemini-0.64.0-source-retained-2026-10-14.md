# Gemini CLI 0.64.0 source lines the projection relies on

Written 14 Oct 2026 00:14 EDT by the harness lane, for review finding 1 and rulings 5-7 (glitch-06) on step 2.
Nothing here was downloaded; every line is quoted from the box lane's retained extracts of the pinned image's bundle.

Bundle file: `/usr/local/lib/node_modules/@google/gemini-cli/bundle/chunk-J7SXW2FI.js`, 16,755,387 bytes, SHA-256 `e2aca15290b02dc9845704f3fed44c577919652508624f340974f0ff588f206e`, read inside image `sha256:4294b1ce3fc0f3c0a9ca7b789f73c613c2baa56e4e0381229a8db3301a707216` by the box lane (`docker run --pull=never --network none`, argv in each evidence file).
Offsets below are character offsets in the decoded bundle as each evidence file records them, plus the index inside that extract.

## Retained

### 1. The recorder's normalization of model text (finding 1)

Evidence: `/Users/javrodher/aegis-builds/gap4-live-box-20261013/lane-reports/live-box-evidence-2026-10-13/gemini-tool-result-source.json` (SHA-256 `a90d436893aba02053e8711be3956fc8777e20559ae6d7a9f898905ecc04267c`), source chunk-J7SXW2FI.js, extract with marker `.recordToolCalls(` at offset 14292223, index 347:

```
const rawResponseText = consolidatedParts.filter((part) => part.text).map((part) => part.text).join("");
    let responseText = rawResponseText.replace(
      /[​-‍﻿‎‏]/g,
      ""
    );
    let previous;
    do {
      previous = responseText;
      responseText = responseText.replace(/<!--[\s\S]*?-->/g, "");
    } while (responseText !== previous);
    responseText = responseText.trim();
```

and later in the same extract:

```
    if (responseText || hasThoughts || hasToolCall) {
      id = this.chatRecordingService.recordMessage({
        model,
        type: "gemini",
        content: responseText
      });
    } else {
      id = this.chatRecordingService.recordSyntheticMessage(
        "gemini",
        consolidatedParts
      );
    }
```

`gemini_projection.recorder_normalize` implements exactly this, with JavaScript's `trim` code-point set spelled out.
Note: `rawResponseText` takes every part that has `text`, and only the consolidation step uses `isValidNonThoughtTextPart`; whether `modelResponseParts` can hold thought parts is in the unretained construction (below).

### 2. thoughtSignature on functionCall parts (ruling 7)

Evidence: `.../gemini-execution-path-source.json` (SHA-256 `a72a0a3f5f2b507585f4a499524dfc39bb483b64b72e69396f35db2d3a73ef85`), chunk-J7SXW2FI.js, extract with marker `displayContentToString` at offset 14300382, index 34:

```
function stripThoughts2(history) {
  return history.map((turn) => {
    if (!turn.content.parts) return turn;
    const hasThought = turn.content.parts.some((p) => p && p.thought);
    if (!hasThought) return turn;
    const nonThoughtParts = turn.content.parts.filter((p) => p && !p.thought);
    let patchedFirstCall = false;
    const finalParts = turn.content.role === "model" ? nonThoughtParts.map((p) => {
      if (!patchedFirstCall && p.functionCall) {
        patchedFirstCall = true;
        if (!p.thoughtSignature) {
          return {
            ...p,
            thoughtSignature: SYNTHETIC_THOUGHT_SIGNATURE2
          };
```

Model `functionCall` parts carry `thoughtSignature` in this version, so the projection admits it as a known key on a functionCall part (a nonempty string), never emitted as output.

### 3. updateMessagesFromHistory itself (finding 6, context only)

Evidence: `.../gemini-native-session-source.json`, chunk-J7SXW2FI.js, extract with marker `ChatRecordingService = class` at offset 12544742, index 18782: `updateMessagesFromHistory(history) { … for (const turn of history) { const turnParts = turn.content.parts || []; …`.
The method's body is retained; its callers are not.

## Not retained: known false-refusal risks for the first recorded walk

The three lines ruling 5-7 asked for are not in any retained extract.
I searched all 162 extracts in the box lane's `gemini-*.json` evidence files for `recordMessage({`, `displayContent`, `modelResponseParts` and `.updateMessagesFromHistory(`.
The pinned image could not be read again here: the Mac's Docker daemon is not running, and I did not start it or pull anything.

- GeminiChat's user-message recording (does it pass `displayContent`?). Ruling 5 cannot be applied, so user `displayContent` keeps refusing. Inference from the retained `Turn.run` → `chat.sendMessageStream(…, displayContent, …)` and the legacy loop's `turnCount === 1 ? input : void 0`: every real user message plausibly carries it, so this is the most likely false refusal.
- The `modelResponseParts` construction (whether thought parts reach `rawResponseText`, and which part shapes a synthetic part-array content holds).
- The caller of `updateMessagesFromHistory` on the legacy non-interactive path. Ruling 6 cannot be applied, so history-patched parallel results (`tc.result = turnParts` holding several calls' responses) keep refusing.

Retaining them needs one read of the same image by the box lane's recipe (markers `recordMessage({`, `modelResponseParts`, `updateMessagesFromHistory(`), on a host whose Docker daemon is up.
