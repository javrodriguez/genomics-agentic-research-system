# Departure D-INT-2: arm O's unobserved served model

Ruled by glitch-06 under the standing delegation, 14 Oct 2026; flagged first for Javier's review before the freeze.
Writer: Claude Code harness lane, 14 Oct 2026 04:42 EDT. Parent: `80d5aa2f` (Codex slice 2).

## What D8 says (quoted, `plans/gap-study-round-4/D8-non-claude-arms.md`)

Line 168, requested model, Codex column: "the rollout file's per-turn context in `$CODEX_HOME/sessions/` (exec JSON carries no model; issue #14736)".
Line 169, served model, Codex column: "only an INFO log line, "server reported model … (matches requested model)"; not in exec JSON or the rollout (issue #47779, open 24 Sep 2026); the walk confirms it reaches `log_dir` in exec mode".
Line 170, aggregate served-model check, Codex column: "the project's usage page by model, per day (API road only; a ChatGPT plan has no such ledger)".
Line 310: "The served model is verified per turn in arm A, per turn only through a log line in arm O (if the walk finds it written), and by name only in arm G; the aggregate usage-by-model checks cover the gap per day on the key road."

D8 does not accept the requested model as the served one.
It plans a per-turn log line (if the walk finds it) and an aggregate usage check on the API-key road.
On the subscription road now in force, the aggregate ledger does not exist, and no log line is read yet.
So the departure label stays.

## The ruling, as built

- For arm O (`codex`) only, a served model that is unobserved (no reroute) is accepted by the init-mismatch row (`routing.UNOBSERVED_ACCEPTED = {"codex": ("model",)}`); the requested model is then assumed.
- An observed reroute to a different model is still a mismatch, and the pin refusal still reads it before the first turn.
- Two reroutes naming different models still refuse the turn (`codex_adapter.read_stream`).
- Gemini and Claude rows, and Codex's mode and version, are unchanged.
- Each Codex turn's evidence is recorded per take in the driver ledger as `served_model`: identity's model entry per turn, `{"value": null, "source": "unobserved"}` without a reroute.
- The limit sentence, verbatim, is `routing.SERVED_MODEL_LIMIT`: "for the OpenAI arm, the served model is verified only when the CLI reports a reroute; otherwise the requested model is assumed".

Deviation, flagged: the sentence is not yet in `prereg-draft.json`'s limitations.
That list is round 3's eleven pinned lines, built by `build_draft.py` (lane w8b) from source documents whose sentences are hashed into the draft.
Adding a twelfth needs a sourced sentence in the plan and the draft owner's rebuild, so it is named here as a follow-up for that owner, not edited by this lane.

## Verification (behind a light gate)

- Red first: the new D-INT-2 test failed against the routing without the departure (1 failure, 4 tests).
- Green: `test_codex_identity` 5/5.
- Mutants killed:
  - (i) unobserved accepted for every harness;
  - (i) every unobserved Codex field accepted;
  - (ii) a reroute mismatch accepted;
  - no departure at all;
  - the ledger record dropped.
- Neighbours green: `test_routing` 276, `test_batch` 118, `test_vendor_take_records` 4, `test_vendor_checker_road` 5, `test_drive_loop` 27, `test_codex_adapter` 47.

## Addendum, Wed 14 Oct 2026 08:36 EDT: Javier's word on D-INT-2

Javier typed "D-INT-2 ok" at 08:06 EDT on Wed 14 Oct 2026, in glitch-06's window.
This record is relayed by glitch-06 to the harness lane, so it notes his word; it does not replace it.
The departure above is no longer only glitch-06's ruling flagged for review: Javier has accepted it.
Nothing in the code changes with this addendum; `routing.UNOBSERVED_ACCEPTED` and `served_model_rule.codex` stay as they are.
The limitations follow-up named above (the sentence is not yet in the draft's limitations) is still open for the draft owner.
