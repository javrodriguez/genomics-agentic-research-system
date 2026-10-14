# Typed identity evidence for routing (live harness step 3b)

Parent: `ebaa34c9`. Writer: Claude Code harness lane, 14 Oct 2026 00:24 EDT, under glitch-06's step-3 order.
This slice also folds the step-2 r2 rulings: docstring completeness note, fixture relabel, the quiescence kill flag on the executed-refusal road with a driver-level timed-out test, and the named departure D-3a-1 (`live-harness-next-integration-addendum-2026-10-14.md`).

## Problem, reproduced

Gemini CLI's stream `init` names a model and a session id only, so its adapter truthfully states `init=None`.
`harness_records` keeps that None, and routing's `differs_from_pin` (the init-mismatch row after the first turn) reads a missing init as a mismatch.
So every Gemini take that reached its first agent turn routed `harness-error`, whatever its records said.
Red evidence: `tests/test_identity_evidence.py` ran 9 tests with 18 errors before the change (`TurnResult` had no `identity` keyword, and `agent_adapter` had no `IDENTITY_SOURCES`).

## Change

- `agent_adapter`: `TurnResult.identity`, typed identity evidence. Per pin field it is `{value, source}`, and the source comes from a closed list: `stream-init`, `stream-stats`, `version-exec`, `submitted-argv`, `unobserved`. An unobserved field carries no value; any other source carries a nonempty string. `harness_records` carries an `identity` list only when some turn states one, so Claude's records are byte-for-byte the same shape as before.
- `routing`: `identity` is an optional record, one entry per turn, shape-checked.
  - `differs_from_pin` reads a turn as a mismatch when any of these holds:
    - its init is missing and it has no identity;
    - its present init differs;
    - its identity has a field that is unobserved, comes from a source not accepted for that field, or differs from the pin.
  - The accepted sources (`ACCEPTED_IDENTITY_SOURCES`, from D8's table) are:
    - model: `stream-init` or `stream-stats`;
    - version: `version-exec`;
    - mode: `submitted-argv`.
  - `present_differs_from_pin` (the pin refusal) also reads observed identity values.
  - Records without identity route exactly as before.
- `gemini_adapter.turn_identity` sets each field's source:
  - model: `init.model` (`stream-init`); without an init, the single `stats.models` key (`stream-stats`; any other key was already refused); else `unobserved`;
  - version: `gemini --version` in the take container, read before the exec (`version-exec`);
  - mode: the pinned mode's flags on the submitted argv (`submitted-argv`).
  - `init` stays None. Nothing is fabricated.

## Decision for review

Accepting `submitted-argv` as the mode evidence is the weakest link: Gemini records no mode anywhere.
The argv is bound to the launch journal by `vendor_provenance`, and the per-take settings pin is the box lane's.
Without this, no Gemini take after its first turn could ever route anything but `harness-error`.
Model is never accepted from the argv: the requested model on the argv is not evidence of what the stream reports.

## Verification (each run behind a fresh light gate)

- `tests/test_identity_evidence.py`: 9/9.
- Neighbours: `test_routing.py` 276/276, `test_agent_adapter.py` 35/35, `test_gemini_adapter.py` 138/138 after renumbering 8 `EQUIVALENT` keys (shifted lines only), `test_codex_adapter.py` 42/42, `test_claude_code_adapter.py` 19/19, `test_vendor_record_binding.py` 9/9, `test_batch.py` 118/118.
- r2 folds: `test_executed_turn_refusal.py` 9/9 (the new driver-level timed-out case is included); `test_gemini_projection.py` 6/6.
- Mutants, all killed by assertion with no errors and candidate bytes unchanged:
  - 3b: nine in-memory mutants. The first run left one survivor, "a matching identity hides a present init that differs"; a test was added, and the re-run killed it.
  - 3a: the re-run kills all eight 3a mutants, including the new "quiescence kill dropped".
- `copy_manifest.py --check`: ok, 374 files.

## Not run, owed

- `test_box_integration.py`, `test_walk_runner.py`, `test_drive_loop.py`, `test_gemini_adapter.py --generated-mutants`, and the full battery: these are for the merged-head athena suite.
- Codex's adapter does not state identity yet. Its rollout model and mode sources need their own slice.
- `routing.json`'s `pin_profiles` are still PENDING (CP5), so no real take routes until those profiles exist.
- Independent review.

## Addendum, 14 Oct 2026 00:35 EDT: review CHANGES (MAJOR) and the fix

The independent review of `6488380e` (`/Users/javrodher/aegis-builds/gap4-review-harness-step2-20261014/review-harness-3b.md`) found the mode evidence to be the pin echoed back. The text above stays as written; these corrections replace its claims.

- Wrong above: "the pinned mode's flags were on the submitted argv" and "the argv is bound to the launch journal by `vendor_provenance`". Nothing read the argv. `turn_identity` copied `self.mode`, which comes from the pin. `launch_facts` had no production caller, and this head's `run_turn` neither writes a journal nor returns the argv.
- Now: `gemini_adapter.submitted_mode` reads the turn's actual-submission journal at `<stream>.launch.json` after the exec. This is the box lane's schema-1 journal; the box writes it before its exec, and this head does not write it yet.
  - No journal, a link, or bytes that are not one JSON object: the mode is `unobserved`, so routing reads a mismatch (harness-error after the first turn, as before 3b).
  - A journal whose argv lacks the pinned flags is `no-mode-flags-submitted`.
  - Flags doubled, or another approval flag present, is `contradictory-mode-flags`. This is checked on the journal argv itself, so a regression in `argv()` cannot agree with itself.
  - A journal that `launch_facts` rejects against the registered invocation is `launch-differs-from-registered-invocation`.
  - None of these values equals a pin, so each is a mismatch.
  - Only the exact pinned flags, once, with `launch_facts` passing, give the pinned mode with source `submitted-argv`.
- Until the box's journal lands on this head, every Gemini turn's mode is `unobserved`, and Gemini routes harness-error after its first turn. That is the honest state, not a regression.
- Acceptance is keyed by `records["pin"]["harness"]`. Only `gemini` has a source table. An `identity` record on `claude-code` (whose mode must come from its init event) or `codex` refuses in `shape_problems`.
- Verification:
  - `tests/test_identity_mode_evidence.py` 8/8. Red first with 11 assertion failures; the wrong-argv-builder case was added later.
  - `test_identity_evidence` 9/9, with its Gemini expectation now `unobserved` mode and the table keyed by harness. `test_routing` 276, `test_gemini_adapter` 138 (8 `EQUIVALENT` keys renumbered), `test_batch` 118, `test_codex_adapter` 42, `test_agent_adapter` 35, `test_vendor_provenance` 6, `test_native_snapshot` 9, `test_executed_turn_refusal` 9.
  - The reviewer's `witness_3b.py` now fails: the finding is gone.
  - Five mutants killed: no-journal echoes the pin, absent flags accepted, doubled flags accepted, launch check skipped, acceptance global again.
- Not tested: a journal that is a symbolic link. The read uses `O_NOFOLLOW`, but no test drives it.
