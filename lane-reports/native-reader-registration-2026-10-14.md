# Gemini native-reader registration road (live harness slice)

Parent: `c3ec5b54`. Writer: Claude Code harness lane, 14 Oct 2026 01:37 EDT, under glitch-06's order. Everything is built except the real evidence.

All fixtures are synthetic and labelled. No acceptance record was committed or written into the study folder.

## What exists now

**The reader candidate.** `native_reader_registration.gemini_reader` turns one interaction of a retained native snapshot into a fact in `vendor_provenance`'s schema. It wraps `gemini_projection.project`.

**The acceptance check.** `check_session(native, streams)` projects the snapshot and joins it to the streams one interaction at a time (`gemini_stream_join.join`). It returns PASS only when:
- there is exactly one interaction per stream;
- every join is clean;
- every interaction is complete.

The tool form is `python3 evals/gap-study-4/native_reader_registration.py check --native <snapshot> --stream <turn-1> [--stream …]`. It prints `PASS: n interaction(s) …` together with the reader-sources hash, or `DISAGREE: <the exact disagreement>`. The first Gemini walk will run this tool on its retained files.

**The registration gate.** `production_readers()` returns `{}` unless a committed acceptance record (`native-readers/gemini-acceptance.json`) re-derives in full. A record that exists but does not hold raises `RegistrationRefused`; it never falls back to an empty registry without saying so. The record binds:

| Field | What must hold |
|---|---|
| `reader_sources_sha256` | Matches the reader's seven source files as they stand, so any edit unregisters the reader. |
| `cli_version` | The pinned 0.64.0. |
| `walk` | Named once in the committed rehearsals register, under arm G. |
| `evidence_label` | Exactly `recorded-walk`; any other label refuses. |
| `native` | Bytes inside the walk folder, re-hashed and confined to `session/native-turn-N.jsonl`. |
| `streams` | Bytes inside the walk folder, re-hashed, and named exactly turns 1..n. |
| `join` | The re-derived check result (PASS, with the interaction count). |
| `review` | An independent review's PASS, its report re-hashed beside the record, and the reviewer named. |
| `accepted_by` | Present and non-empty. |

**The driver.**
- `native_history_record` reads the production registry, which is empty today, so the status stays `pending`.
- With a registered reader and a snapshot history that joins, `gemini_cross_check` runs D8's cross-check: each turn's stream is joined to that turn's interaction in the last snapshot, and extra or missing interactions are refused.
- Results: `agreed` makes `cross_check` `[]`, a real agreement. `refused` adds the reason, which the checker reports as readers-disagree. `pending` keeps the typed stop of D-INT-1.

## Verification (each run behind a fresh light gate)

**Red.** The new test module was run against HEAD `c3ec5b54` with the module absent: 6 errors (no module, no `drive._registration`). The module itself was written before the tests, so this red was taken by running the tests against HEAD's tree.

**Green.**

| Test file | Result |
|---|---|
| `test_native_reader_registration.py` | 6/6 |
| `test_vendor_checker_road.py` (including N8's Gemini through-batch twin) | 5/5 |
| `test_vendor_take_records` | 4 |
| `test_native_history_record` | 3 |
| `test_native_snapshot` | 9 |
| `test_gemini_projection` | 8 |
| `test_gemini_stream_join` | 8 |
| `test_drive_loop` | 27 |
| `test_executed_turn_refusal` | 10 |

**Refusal cases.** Fifteen forged, mismatched or synthetic record variants each refuse, and so does a record that is not JSON. The one positive registration runs inside a temporary copy of the sources with a temporary register.

**Mutants.** Nine in-memory mutants were each killed by assertion, with no errors:
- a synthetic label accepted;
- the reader sources unchecked;
- the join trusted instead of re-derived;
- the review file unchecked;
- any walk accepted;
- registration without a record;
- the evidence hashes unchecked;
- an incomplete interaction accepted;
- an extra native interaction accepted.

**Stopped by pid.** I started `test_walk_runner.py` in the neighbour batch, then remembered it is a broad suite reserved for athena. I stopped it with SIGINT by its pid (98621) before it finished. Its result is unrun.

## Not run, owed

- The real evidence: the first Gemini walk, its retained snapshot and streams, the acceptance check, and an independent review. A human then commits the acceptance record.
- `test_walk_runner.py`, `test_box_integration.py` and the full battery (merged-head athena suite).
- Independent review of this slice.
