# Codex road review fold (80d5aa2f and 840048ab, both PASS with MINORs)

Writer: Claude Code harness lane, 14 Oct 2026, under glitch-06's order after `review-codex-road.md`.
Parent: `75a8074d`. One commit, red first.
The reports `codex-identity-table-2026-10-14.md` and `codex-registration-road-2026-10-14.md` stay as written; this addendum corrects them.

## F1: what a reroute is

The reroute is now told apart from other error items as narrowly as the retained source allows:
- the message is exactly `model rerouted: <from> -> <to> (HighRiskCyberActivity)`;
- the reason is pinned to `ModelRerouteReason`'s one variant (`protocol/src/protocol.rs:2132-2134`);
- `from` must equal the turn's own `-m` model.

Anything else in that item shape is off the tables and refuses the turn, as before.

Added to the identity report's "never observed" section:
three other exec roads write the identical `item.completed` error-item shape (`collect_warning`, `ConfigWarning` rendered as `"{summary} ({details})"`, and `DeprecationNotice`; `exec/src/event_processor_with_jsonl_output.rs:409-472`).
Nothing in the item distinguishes them, and core's warning emitters are not in the retained source.
So a warning whose text is exactly that sentence about the requested model would read as a reroute.
A forged reroute naming a model off the pin still refuses (a mismatch).
A forged one naming the pin would read the model as observed when it was not.
That residual ambiguity is unresolvable locally.

## F2: one parser

- `codex_native.reroute_of(rec, model)` is the one parser, and `codex_adapter.reroute_of` is the same function.
- `read_exec` reads reroutes with it, against the turn's requested model.
- `read_exec` refuses two different reroutes in one exec. The adapter already did.

## F3: the ledger's served model is bound

- The Codex acceptance check (`codex_check`) re-derives each turn's served-model evidence from its own exec stream: `unobserved` with no value without a reroute, and `stream-reroute` with the `to` model with one.
- It refuses a ledger whose `served_model` says anything else.
- A served model claimed inside an accepted record, and not observed in its stream, no longer registers.

## F4: the profile-specific bindings, each by a single mutation

`test_pending_codex_walk.CodexProfileBindings`:
- an honest hand copy registers, so each refusal below is its own;
- `served_model` dropped from the ledger;
- a served model claimed without a reroute;
- a turn-2 journal naming another thread;
- a Codex reader source edited after acceptance;
- a dirty bound path.

## F5

The locator's tests list eleven folder-and-name refusals, plus four thread-id refusals and a link.
"Eight" in the slice report was wrong.

## Verification (behind a light gate)

- Red: the new tests against the parent's three modules.
  - `CodexProfileBindings`: 3 tests, 1 failure.
  - `test_codex_native`: 15 tests, 4 failures and 1 error.
  - `test_codex_adapter`: 48 tests, 4 failures.
- Mutants, all killed:
  - any reason accepted;
  - `from` unchecked;
  - two different reroutes admitted;
  - `read_exec` ignoring the requested model;
  - `served_model` unbound;
  - Gemini's sources hashed for Codex;
  - `served_model` dropped from the Codex ledger keys.
- Suites: see the commit message.
