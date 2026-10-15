# Gemini CLI 0.64.0 source lines, retained from the pinned image (addendum)

Written 14 Oct 2026 00:58 EDT by the harness lane, for rulings 5-7 (glitch-06) on step 2.
This adds to `gemini-0.64.0-source-retained-2026-10-14.md`; that report stays as written.

## How it was read

The read ran on athena as `javier`, with `DOCKER_HOST=unix:///run/user/1000/docker.sock`, over `ssh` with agent, X11 and port forwarding off. Athena was idle at the time.

The image was `sha256:4294b1ce3fc0f3c0a9ca7b789f73c613c2baa56e4e0381229a8db3301a707216`. It was already present, so nothing was pulled. The steps:
- `docker create --pull=never --network none <image> /bin/true`, never started;
- `docker cp` of `/usr/local/lib/node_modules/@google/gemini-cli/bundle` and `package.json` into a temporary folder;
- `docker rm` of the container, by its id. The two reads used containers `6afcd6a67ec8…` and `34d0bf4cabb5…`.

Python on athena (`python3 -I -S`) read and hashed the text, and the temporary folder was then deleted.

Gemini was never executed. No network, credential or login was involved.

Checks on what was read:
- `package.json` version: `0.64.0`.
- `chunk-J7SXW2FI.js`: 16,755,387 bytes, SHA-256 `e2aca15290b02dc9845704f3fed44c577919652508624f340974f0ff588f206e`. This equals the box lane's evidence, and both reads checked it.

Offsets below are character offsets in the decoded file.

## 1. GeminiChat's user-message recording (ruling 5)

Character offset 14254571 onward, in `sendMessageStream`:

```
    if (!isOriginalFunctionResponse) {
      const userMessageParts = userContent.parts || [];
      const userMessageContent = partListUnionToString(userMessageParts);
      let finalDisplayContent = void 0;
      if (displayContent !== void 0) {
        const displayParts = toParts(
          Array.isArray(displayContent) ? displayContent : [displayContent]
        );
        const displayContentString = partListUnionToString(displayParts);
        if (displayContentString !== userMessageContent) {
          finalDisplayContent = displayParts;
        }
      }
      if (!isContextManagementEnabled) {
        const id = this.chatRecordingService.recordMessage({
          model,
          type: "user",
          content: userMessageParts,
          displayContent: finalDisplayContent
        });
```

- `displayContent` is recorded only when its string differs from the sent parts' string. When it is equal it is undefined, and `JSON.stringify` drops it.
- So a recorded `displayContent` is never byte-equal to the sent text.
- Ruling 5's admission ("only when byte-equal") is implemented as ruled, but it never fires on a session this version writes. A present `displayContent` refuses.
- The false-refusal risk the reviewer inferred does not exist.

## 2. Tool-response turns: a "user" message of functionResponse parts (newly found)

Character offset 14256323 onward, in the same method's `else` branch, which runs when the turn sends tool results back (`isOriginalFunctionResponse`):

```
    } else {
      const id = this.chatRecordingService.recordSyntheticMessage(
        "user",
        userContent.parts || []
      );
```

- Every tool round trip records a `type: "user"` message whose content is the functionResponse parts. It sits between the gemini message that called the tools and the next one.
- Step 2's projection treated every user message as a new interaction, requiring one text part. It therefore refused every interaction that used a tool: a false refusal on the main road, not an edge case.
- When a binary injection is present, the same branch also records a synthetic gemini thought message, with `thoughtSignature` on a text part, and an `info` message. That shape stays refused.

## 3. The response parts (ruling 7 context)

`processStreamResponse` (character offset 14284598 onward) builds `modelResponseParts` with this push:

```
          modelResponseParts.push(
            ...content.parts.filter((part) => !part.thought).map((part) => {
```

- Thought parts never reach `consolidatedParts` or `rawResponseText`.
- So the recorded text never contains thoughts.

## 4. updateMessagesFromHistory: its caller and the parallel-result patch (ruling 6)

`GeminiChat.initialize`, character offset 14252516 onward:

```
  async initialize(resumedSessionData, kind = "main") {
    await this.chatRecordingService.initialize(resumedSessionData, kind);
    this.chatRecordingService.updateMessagesFromHistory(
      this.agentHistory.get()
    );
  }
```

Every chat start calls it. That includes every `gemini -p … -r <id>` resume of the legacy path, and also the rollback and abort paths in `sendMessageStream`.

The patch, character offset 12566400 (`ChatRecordingService.updateMessagesFromHistory`):

```
      for (const turn of history) {
        if (turn.content.role !== "user") continue;
        const turnParts = turn.content.parts || [];
        for (const part of turnParts) {
          if (part.functionResponse) {
            const callId = part.functionResponse.id;
            …
                  if (tc) {
                    tc.result = turnParts;
                  }
```

- A tool call's `result` becomes the whole user turn's parts, one functionResponse for each call of that round trip.
- The legacy path does reach it. So ruling 6 admits a result whose parts are all functionResponses that name this call exactly once, plus siblings of the same gemini message by id and name.

## Evidence kept

The raw JSON of both reads is in this session's scratch folder (`srcread/extract.json`, SHA-256 `6c6e3b15…`, and `srcread/extract2.json`, SHA-256 `c48070c8…`). It is not published. The lines above are the load-bearing quotes.

## Addendum, 14 Oct 2026 01:27 EDT: batch-5 review folds

**Finding 2 (provenance).** Both raw extracts and the exact read scripts are now retained, with their hashes, in `lane-reports/gemini-0.64.0-source-evidence-2026-10-14/`:

- `extract-1-markers.json`: SHA-256 `6c6e3b15…`, the marker windows from every bundle file.
- `extract-2-ranges.json`: SHA-256 `c48070c8…`, the exact character ranges.
- `read-1.sh` and `read-2.sh`.
- `SHA256SUMS`.

Both extracts record `package_version` 0.64.0 and `pinned_chunk_ok` true, and each quoted line above can be re-read from them.

**Finding 1 (check-weakening).** The rule I wrote above was too loose: "each (id, name) it answers must be a call recorded earlier in that interaction". The source records one round trip per tool-calling model message, holding exactly that message's responses. The projection now requires each of the following:

- A tool-response turn follows the gemini message it answers.
- It answers exactly that message's calls, each once.
- A tool-calling gemini message is followed by such a turn before the next gemini message.

The reviewer's three accepted shapes now refuse:

- the same call answered twice;
- an older round's call answered;
- a missing round-trip record.

## Addendum, 14 Oct 2026 01:37 EDT: N7, corrected offsets (batch-6 review)

Section 4 above cites two offsets that point at the wrong places. Both corrections were re-read from the retained extracts.

| What | Section 4 says | Correct offset | Read from |
|---|---|---|---|
| `GeminiChat.initialize` (`async initialize(resumedSessionData, kind = "main")`) | 14252516 | 14252358 | `extract-1-markers.json` |
| The patch block, `for (const turn of history) {` | 12566400 | 12565520 | `extract-2-ranges.json` |
| The patch block's role guard, `if (turn.content.role !== "user") continue;` | 12566400 | 12565558 | `extract-2-ranges.json` |
| The assignment `tc.result = turnParts` | 12566400 | 12566400 (unchanged) | `extract-2-ranges.json` |

The 14252516 that section 4 gives for `initialize` is the offset of its `updateMessagesFromHistory(` call, not of the method itself.
