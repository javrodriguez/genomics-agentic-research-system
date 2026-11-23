VERDICT: CHANGES

# Review of T4 group (f), lane vendor-admission, range f628e9d8..981e8716

Fresh, independent reviewer (cloud), briefed by glitch-b5; written 2026-10-18 04:25 EDT. Head reviewed: 981e8716
(lane/vendor-admission; it did not move during the review). No code, test or fixture was changed. Every probe ran
from the scratchpad, outside the clone, against the head's own test builders (test_vendor_envelopes' roads), with
TMPDIR outside the clone.

Finding 3 and NITs 1 to 3 are closed at the cause. Edits B and C do what rounds 14 and 15 rule. Each edit is gated to
vendor harnesses. drive.py differs from f628e9d8 only by those two spans. Claude Code's road is byte for byte. A
masked codex or gemini take now counts account-email 1 and is not held. Every witness goes red for its own reason.

One MINOR, reproduced: edit C's record choice leaves the pre-scan sha256 of a masked file nowhere, because the
drive scan's own record is never written down (finding 1). Five NITs follow, including NIT 4 of review e-71a2b94,
which is not closed.

## Test counts (python3, TMPDIR outside the clone)

Red first. Each red commit changes tests, checks.d or COPIED.d only, so its code is its parent's. Each was run on
its own tree in a scratch worktree, and every count and reason matches the lane file:
- bb56bc61: test_vendor_body failures=3. They are the F3 case "the pre-registered row on another model" (both
  vendors added nothing), the witness "the model reading dropped" and the witness "the ledger-only model binding
  restored on the take road".
- 221b1da4: test_vendor_walk_road errors=2, both `TypeError: unhashable type: 'list'` (the digest in force, and its
  witness).
- ccc5d598: test_vendor_constants failures=1 errors=2. The errors are AttributeError on vendor_rows_block. The
  failure is P5-block, whose block is not its sources.
- 3069c042:
  - test_vendor_envelopes failures=3: EB-road on codex and on gemini ("the take folder holds no transcript.jsonl"),
    and the witnesses ("drive.py holds no edit B").
  - test_vendor_walk_road failures=1: R-9, "RegradeRefused: the committed walk has no transcript.jsonl".
  - check_vendor_sources EB drive.py: exit 1, "edit B: ... writes no turn envelopes".
- 1a6ad553:
  - test_vendor_envelopes failures=3: EC-mask on codex and on gemini, each "the masked take is held: CheckRefused:
    the <harness> reach could not be read (... native stream digest differs)", which is review e-71a2b94's
    reproduction. The third is the witnesses ("no edit B or no edit C").
  - check_vendor_sources EB: exit 1, "edit C: ... no `if` naming VENDOR_HARNESSES there".

Green at 981e8716:
- Every one of the 30 commands in checks.d/vendor-admission.txt exits 0. Among them: test_vendor_envelopes 4,
  test_vendor_walk_road 6, test_vendor_body 11, test_vendor_entries 8, test_vendor_session 5,
  test_vendor_constants 10, test_vendor_check 26, test_vendor_roads 13, test_take_checker_dispatch 5,
  test_vendor_admission 10, test_vendor_admission_regrade 3, test_freeze_shapes 9 and test_pin_for_vendor 2. Also
  green: vendor_check_fixtures --check, and every check_vendor_sources line (PF, P0, P0b, P1, P2 x3, P3, P4, P5 x3
  and EB).
- Named modules: test_pending_walk 23, test_pending_codex_walk 11, test_walk_plan 18, test_walk_recheck 17,
  test_recheck_coverage 5, test_checker_constants 27, test_vendor_checker_road 5, test_walk_grade_seam 3,
  test_checker_body 30, test_check_take 15, test_vendor_take_records 4, test_native_reader_registration 7,
  test_drive_loop 27, test_no_output_nudge 9, test_agent_tool 17, test_walk_wiring 20, test_walk_builders 88,
  test_scaffold 49, test_walk_runner 89, test_take_config 9, test_scan_record 101, test_box_integration 61 and
  test_codex_adapter 55.
- test_nested_agent 35: only the two TheSweep failures (test_review_r15_reads and
  test_the_program_finds_each_session_shape_and_nothing_else), from this container's root user.
- lint_language on evals/gap-study-4/: clean, 115 inputs, 23 excused lines.
- lint_pooling --commits-since f628e9d8: clean, 11 commits.
- copy_manifest --check: ok, 480 files from 60 fragments.
- Not run here: the whole battery, the --witnesses sweeps and the generated sweeps. These are glitch-b5's, on the
  home server.

## Scope items, ruled

1. Red first for real: yes, as listed above.

2. drive.py.
   - `git diff f628e9d8..HEAD -- drive.py` is two hunks, both pure additions, with no removed line: +29 at 2607 and
     +32 at 2885.
   - Edit B lies inside `if vendor:`. Edit C is an `if` whose test is `harness in VENDOR_HARNESSES and ...`.
   - check_vendor_sources.without_edits(drive.py) equals `git show f628e9d8:evals/gap-study-4/drive.py` byte for
     byte. This was checked directly, not only through the stored digest.
   - EB-claude was rerun against a module compiled from that git text (not from without_edits). The ledger,
     transcript.jsonl, the listing and the returned records were identical in all three cases: with a session file,
     without one, and with the address masked.
   - No other READER_SOURCES or CODEX_SOURCES file is in the range. The code files changed are check_take.py,
     drive.py, pending_walk.py and walk_regrade.py, and of those only drive.py is listed.

3. Edit C's record choice.
   - No reader needs the pre-scan value. On EC-mask's masked codex and gemini takes I probed the readers directly:
     - the regrade's cross-check over the published bytes, with refs from the ledger as walk_regrade builds them,
       reads `agreed`;
     - vendor_provenance.session_history_facts over the ledger's rebound snapshots, the registration's
       snapshot-history join, reads clean.
   - A take tampered with after the scan still refuses. With the bytes changed just before the vendor entry reads
     them, vendor_event_counts raised CheckRefused in every case:
     - a masked snapshot's bytes: "session/native-turn-2.jsonl: its bytes are not the ones the ledger binds";
     - a masked stream's bytes: "native stream digest differs";
     - an envelope's sha256: "native stream digest differs";
     - the ledger's last snapshot sha256: "its bytes are not the ones the ledger binds".

     The untampered control counts account-email 1.
   - An unmasked take's ledger is left as before. On codex and gemini without the address, under drive.py and under
     drive.py with edit C taken out, driver-ledger.json, transcript.jsonl, the listing and the checker records are
     identical.
   - Whether the pre-scan sha256 is recorded where a person can audit it: no. See finding 1.

4. The drive road end to end. EB-road reaches checker_for and the vendor entry once, with no readers-disagree, on
   both vendors. EC-mask counts account-email 1 and is not held on both. The drive's own bound (the checker's count
   is not above the scan's masked email hits) runs for real. Each of the 8 witnesses printed red for its own reason:
   - the writer gated off: no transcript.jsonl, and the vendor entry is reached 0 times;
   - the writer run for claude-code: claude-code's transcript.jsonl differs, and so do the masked case's records;
   - sent from another row: "turn envelope differs from ledger";
   - the sha256 of another stream: "native stream digest differs";
   - the rebinding taken out: held, "native stream digest differs";
   - the envelopes left on the unmasked bytes: held, "native stream digest differs";
   - the snapshots left on the unmasked bytes: held, "session/native-turn-2.jsonl: its bytes are not the ones the
     ledger binds";
   - the rebinding run for claude-code: claude-code's transcript.jsonl differs.

5. Finding 3 is closed at the cause. vendor_model_problems binds the take road to rows[row_index]["model"] and
   refuses a model_requested that differs from it, and the walk road keeps model_requested. That is arm C's
   check():1772 binding. The NITs:
   - NIT 1 is closed at the cause: walk_harness returns None for a harness that is not a string.
   - NIT 2 is closed at the cause: vendor_rows_block enters each row whole.
   - NIT 3 is closed: table row 15 names the check.
   - NIT 4 is not closed; see NIT 1 below.

6. No READER_SOURCES or CODEX_SOURCES change beyond drive.py's two spans, and every check passes (above).

## Findings

1. MINOR: the pre-scan sha256 of a masked vendor file is recorded nowhere, so the record edit C rewrites has no
   audit trail (evals/gap-study-4/drive.py:2885-2914).
   - Edit C overwrites the driver ledger's native_snapshots sha256 (and the envelopes' sha256) with the scan's
     sha256_after.
   - The scan's own record, which holds sha256_before, lives only in TakeDriver.drive's local `scan` (drive.py:2880).
     It is never written to the take folder, never returned, and batch.py stores no sha256_before.
     box/scan_record.scan_with_witness, the one form that keeps original_sha256, is not called on any production
     road.
   - Reproduced on EC-mask's codex and gemini takes. A spy on drive._scan_record.scan showed that the drive scan
     masked turn-1.jsonl, turn-2.jsonl, session/native-turn-1.jsonl and session/native-turn-2.jsonl. None of their
     four sha256_before values appears in any file of the take folder at the checker's read.
   - Before edit C, the ledger's native_snapshots sha256 was the one record of which bytes the drive's native
     cross-check and native_history joined (NATIVE_HISTORY_BASIS: "unmasked retained originals, before the drive
     scan").
   - Consequence for the study:
     - A masked vendor take's committed ledger carries native_history computed on unmasked bytes beside
       native_snapshots digests of the masked bytes. Nothing in the take says which snapshots were rebound, or
       from what.
     - A person auditing a counted O or G take cannot tie the take-time cross-check to the bytes it read. The
       readers re-derive correctly over the published bytes (scope item 3), so no count is wrong and nothing
       passes that should not.
     - Claude Code's take keeps its transcript's pre-scan digests in scrub.json (sha256_before and sha256_after), so on this point
       the vendor road keeps less than arm C, and does so silently.
     - The brief made a surviving pre-scan record a condition of this record choice, and the lane file does not
       name the loss.
   - Fix, for glitch-b5 to rule:
     - (a) accept the loss and name it in plan section 6 and the table's envelopes line: the drive scan's record is
       not kept; the readers re-derive over the published bytes; a pre-scan whole-file digest of a secret-bearing
       file is also what box/scan_record's docstring warns can test a guessed low-entropy value offline. No code.
     - (b) keep the drive scan's files record for a vendor take where a person can read it. That needs a record file
       (a TAKE_FILE_KINDS line, outside edits B and C) or a new ledger key (LEDGER_KEYS, a READER_SOURCES file), so
       it stops BLOCKED as section 6 says.
     - I recommend (a). It is honest about what is kept, and it keeps out a digest the scan module itself flags.

## NITs

1. evals/gap-study-4/walk_regrade.py:47: review e-71a2b94's NIT 4 is not closed at the cause. The wrap moved the
   overflow onto the next line, which is now 149 characters (the old line 46 was 146). check_take.py's line is
   fixed.
2. lane-reports/vendor-T4-PLAN.md:119: edit B's bullet still says piece EB admits drive.py "when drive.py with edit
   B's lines taken out is drive.py at f628e9d8". The check now takes out both edits' spans, and edit C's bullet
   (line 120) does not say EB covers it.
3. evals/gap-study-4/drive.py:3220-3221: native_history_record's docstring says "a re-join over published bytes
   refuses". After edit C the registration's and the regrade's re-joins run over the published bytes and agree
   (scope item 3). This is the prose FOR THE REVIEWER (1) puts to glitch-b5, and it is stale now.
4. evals/gap-study-4/tests/check_vendor_sources.py:61-76: edit_c_span admits any `if` whose test merely names
   VENDOR_HARNESSES, so `not in VENDOR_HARNESSES` would pass the piece. The gate's direction is held by EB-claude
   and the "rebinding run for claude-code" witness, not by EB itself.
5. evals/gap-study-4/drive.py:2614-2616 (edit B): an executed-refusal row has no entry in `turns`, so its envelope
   carries stream None and sha256 None, although take.executed_refusal names that stream. Such a take is held
   (DriveRefused after the scan), so nothing counts on it. tests/test_vendor_envelopes.py:12 runs to 143
   characters.
