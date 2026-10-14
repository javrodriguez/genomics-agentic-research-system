# Gemini native-reader registration: the review fold (addendum)

Parent: `bcdc4bca`. Writer: Claude Code harness lane, 14 Oct 2026 01:59 EDT, under glitch-06's order after the `38b70ae8` review (CHANGES, finding 1 MAJOR: the road was self-certifying).
The original report, `native-reader-registration-2026-10-14.md`, stays as written; this addendum supersedes its record table and its claim of a positive registration.

All fixtures are synthetic and labelled. No acceptance record was committed or written into the study folder.

## What changed

**1. Committed tree only.**
Every bound input is read with `git show HEAD:<path>`: the acceptance record, the rehearsals register, the walk folder, the review and the reader's sources.
A bound path whose working tree differs from HEAD (modified, deleted or untracked) refuses.
A record on disk but not in HEAD refuses as uncommitted; a record outside any git repository refuses.
With no record on disk, `production_readers()` returns `{}` without running git, so a driver's take pays nothing; a committed record deleted from disk also reads `{}`, which keeps every Gemini take pending (the fail-closed side).

**2. A walk the runner wrote.**
The walk folder's committed blobs are written to a temporary folder (a link or submodule refuses) and must pass `drive.walk_files`.
Every commit that touched the folder must be exactly one, with the subject `drive.WALK_SUBJECT` ("Commit one walk; never counted"), the subject `WalkRepo._bind` writes.
The record's native snapshot must equal the last `native_snapshots` ref of that walk's own `driver-ledger.json` (file and sha256), and its streams must equal the ledger's `streams`, turns 1..n.
The ledger must carry a `native_history` record.
Each byte the record names is re-hashed on the committed bytes.

**3. The label is derived.**
`evidence_label` is no longer a key; a record that carries one refuses ("derived …, never asserted").
A case-insensitive `synthetic` in the native session metadata, the register entry, the review text or the record refuses.
This gate runs last, so each forged case in the tests refuses for its own reason first, and no labelled synthetic fixture can ever register.
Consequence, stated plainly: no test demonstrates a positive registration any more; one needs a real recorded walk.
Known false-refusal risk, fail closed: Gemini's own session `summary` is generated from the conversation, so a real walk whose task mentions synthetic data would refuse.

**4. Human steps.**
The acceptor must be `javier`; the reviewer must be a different principal.
`native_reader_registration.py verify` prints the registry, the acceptance record's commit SHA and author, the review's commit and HEAD.
These are local, unsigned git records: anyone able to commit can write them, author included.
The final guarantee is procedural: the acceptance commit is made in Javier's own window (the standing rule that owner-approval edits belong in his window).
Follow-up, not built: a hook-gated acceptance door (no engine hooks were touched).

**5. One shared join (finding 2).**
`join_session(raw, streams, reader)` is the one function both `check_session` (acceptance) and `drive.gemini_cross_check` (production) call.
An incomplete interaction is refused in both; an extra native interaction is refused in both.
`drive.py` and `vendor_provenance.py` join `READER_SOURCES` (now nine files), so an edit to the driver's cross-check or to provenance unregisters the reader.

**6. Coverage floor (finding 3).**
Acceptance needs at least 2 interactions (a resume) and at least 1 tool round trip, and the snapshot-history join (`vendor_provenance.session_history_facts`) must hold over every snapshot the ledger names, at least two.
The check tool's PASS line lists the shapes exercised (interactions, tool round trips, tool error statuses, object display results, multi-segment interactions) and names the rest unverified, including three shapes this check never counts: parallel calls from one model message, a turn killed or timed out mid-tool, and thoughts or thought signatures.

**7. N9.**
The PASS line prints `git rev-parse HEAD` beside the reader-sources hash.

## Verification (each batch behind a fresh light gate)

Red: the reworked `test_native_reader_registration.py` against HEAD `bcdc4bca`: 9 tests, 22 failures and 2 errors.

Green after the fix:

| Test file | Result |
|---|---|
| `test_native_reader_registration.py` | 9/9 (15 per-reason refusal subtests, 3 synthetic-marker placements) |
| `test_vendor_checker_road.py` | 5/5 |
| `test_vendor_take_records.py` | 4/4 |
| `test_native_history_record.py` | 3/3 |
| `test_native_snapshot.py` | 9/9 |
| `test_gemini_projection.py` | 8/8 |
| `test_gemini_stream_join.py` | 8/8 |
| `test_drive_loop.py` | 27/27 |
| `test_executed_turn_refusal.py` | 10/10 |
| `test_codex_native.py` | 10/10 |
| `test_vendor_record_kinds.py` | 2/2 |

`copy_manifest.py --check`: ok, 389 files.

A first green attempt broke three driver suites: `production_readers()` ran git on every take, which `test_box_integration`'s process guard refuses.
The fix above (no git without a record on disk) is the one behaviour change that came from it.

**Mutants.** Eighteen in-memory mutants, all killed:
the clean check removed; an uncommitted record accepted; `evidence_label` tolerated; any acceptor; the reviewer allowed to be the acceptor; `walk_files` skipped; any commit subject; the ledger's native ref unbound; the ledger's streams unbound; no coverage floor; no synthetic gate; the synthetic gate skipping the review; the synthetic gate skipping the register entry; an incomplete interaction accepted in the shared join; an extra native interaction accepted; the review hash unchecked; `drive.py` dropped from the bound sources; drive keeping its own join.

**The reviewer's witnesses.**
`witness_registration.py` run as is against the fixed checkout: 0 of 5 observations hold.
Four of them error before reaching the code, because they build on a fixture helper the reworked test module no longer has, so that run alone proves nothing for them.
The fifth (production agrees where acceptance disagrees) now gets `refused: interaction 1 is not complete`.
Each of the five attacks was therefore re-staged on the new fixture (scratch file, not committed): a SYNTHETIC-labelled session, a record outside git and uncommitted, a walk folder the runner did not write, free-string principals, and an incomplete production turn.
All five refuse, each for its own reason.

## Not run, owed

- A positive registration: needs the first real Gemini walk, the acceptance check on its retained files, an independent review, and Javier's acceptance commit in his own window.
- `test_walk_runner.py`, `test_box_integration.py` and the full battery: the merged-head athena suite.
- Independent review of this fold.
