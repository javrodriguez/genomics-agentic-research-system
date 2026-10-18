VERDICT: CHANGES

# Review of T4 group (e), lane vendor-admission, range 5d637f8d..71a2b948

Fresh, independent reviewer (cloud), briefed by glitch-b5; written 2026-10-18 02:33 EDT. Head reviewed: 71a2b948
(lane/vendor-admission; it did not move during the review). No code, test or fixture was changed. Every probe below
ran from the scratchpad, outside the clone, against the head's own test builders, with TMPDIR outside the clone.

The P5 code does what the plan and the round 13 rulings ask. Both group (d) folds are closed at the cause. The
merged digest, the vendor view, the vendor side, the model and environment readings, the walk road and R-9's road
behave as the lane says. Every plan mutant goes red for its own reason. Claude Code's road is unchanged byte for byte
(shown below). Three findings, all reproduced:
- one MAJOR: FOR THE REVIEWER point 1, the vendor checker cannot be reached in production;
- two MINOR: the drive's scan breaks the vendor sha256 bindings, and FOR THE REVIEWER point 2 is weaker than arm C.

None of them makes a vendor take pass where a Claude Code take would fail, except finding 3. Findings 1 and 2 fail
closed: no vendor take or walk can be counted, and a masked vendor take is held.

## Test counts (python3, TMPDIR outside the clone)

Red first. Each red commit changes tests or COPIED.d only, so its code is its parent's. Each was run on its own tree
in a scratch worktree. Every count and reason matches the lane file:
- 5a1bbe0c: test_vendor_body failures=3 and test_vendor_entries failures=4.
  - The new F3 and P3-unread case "a ledger-named snapshot missing" adds no refusal on either vendor.
  - The witnesses fail because their case is already red on the code. "the email marker unread" fails because its
    anchor moved, as named.
- 585e1bf8: test_vendor_session failures=6. The three own-path store cases per vendor add nothing, and the five
  witnesses fail on their case.
- cea6bd87:
  - test_vendor_constants failures=2 errors=11: AttributeError on VENDOR_CHECKER_CONSTANTS, vendor_view and
    checker_view, and the entries reading a plain view.
  - test_vendor_entries errors=16, test_vendor_body failures=37 errors=4 and test_vendor_session errors=15, all from
    vendor_view missing.
  - test_take_checker_dispatch 5 OK; its one change is a comment.
- c0813c64: test_vendor_body failures=5 (the model and environment cases and four witnesses) and
  test_vendor_constants failures=2 (P5-env and its witness).
- abde2ab8: test_vendor_walk_road failures=4 errors=2. The errors are TypeError, because nudge_count_problems takes
  no harness yet. The failures are the digest in force and the check road.
- 33e8a0da: test_vendor_walk_road failures=6. The R-9 test fails on "coverage None" for a regrade with no checker
  reading, and the witnesses fail on anchors that are absent. test_pending_walk errors=1 (no PENDING_UNCHECKED).

Green at 71a2b948:
- Every checks.d/vendor-admission.txt line exits 0 (25 lines). Among them: test_vendor_constants 9,
  test_vendor_walk_road 6, test_vendor_body 10, test_vendor_entries 8, test_vendor_session 5, test_vendor_check 26,
  test_vendor_roads 13, test_take_checker_dispatch 5, test_vendor_script 8, test_freeze_shapes 9,
  test_vendor_admission 10, test_vendor_admission_regrade 3, test_pin_for_vendor 2, vendor_check_fixtures --check,
  and every check_vendor_sources line (PF, P0, P0b, P1, P2 x3, P3, P4, P5 x2).
- Named modules: test_pending_walk 23, test_walk_plan 18, test_walk_recheck 17, test_recheck_coverage 5,
  test_checker_constants 27, test_no_output_nudge 9, test_agent_tool 17, test_pending_codex_walk 11,
  test_checker_body 30, test_check_take 15, test_vendor_checker_road 5, test_walk_grade_seam 3, test_walk_wiring 20,
  test_vendor_take_records 4, test_native_reader_registration 7, test_drive_loop 27, test_walk_builders 88,
  test_scaffold 49, test_walk_runner 89.
- test_nested_agent 35: only the two TheSweep failures (test_review_r15_reads and
  test_the_program_finds_each_session_shape_and_nothing_else), from this container's root user. The range touches
  neither that test nor the sweep code.
- lint_language on evals/gap-study-4/: clean, 115 inputs, 23 excused lines. lint_pooling: clean. copy_manifest
  --check: ok, 479 files from 60 fragments.
- Not run here: the whole battery, the --witnesses sweeps of test_walk_builders, test_walk_runner and test_walk_plan,
  and the generated sweeps. These are glitch-b5's, on the home server.

Scope item 5: `git diff --stat 5d637f8d 71a2b948` edits no READER_SOURCES or CODEX_SOURCES file, read from
native_reader_registration. READER_SOURCES is drive.py, gemini_projection.py, gemini_session_replay.py,
gemini_stream_join.py, native_reader_registration.py, transcript_gemini.py, transcript_view.py, vendor_provenance.py
and vendor_record_binding.py. CODEX_SOURCES is codex_native.py, drive.py, native_reader_registration.py,
native_snapshot.py and vendor_provenance.py. The code files changed are check_take.py, pending_walk.py,
walk_builders.py, walk_plan.py and walk_regrade.py, as plan section 9 names them. drive.py is untouched.

## Scope items, ruled

- Folds closed at the cause.
  - Finding 1: vendor_email_problems now reads each named file through _binding._regular_bytes, and returns
    transcript-unreadable by name when one cannot be read. vendor_event_counts raises CheckRefused on it, so no
    count is 0 on bytes never read.
  - Finding 2: the sweep filter drops only `f == [own_path, harness, vid]`. Any other record at that path reaches
    sweep_violations.
  - Both are pinned by cases and witnesses that went red on the parent.
- The merged digest moves on every block value. Probe: each of the 20 codex and 19 gemini leaves of the block,
  changed one at a time, moved vendor_checker_constants_sha256, and so did a dropped row. Both merged digests differ
  from checker_constants_sha256().
  - A block value of exactly PENDING makes the digest refuse and lands in the view's pending. The preamble then
    raises "still PENDING" and _vendor_side refuses, so a PENDING value holds every take.
  - A walk checked before a change reads stale, because constants_in_force recomputes the merged digest. See NIT 2
    for the row fields the digest does not carry.
- The vendor side refuses a plain view. A design that is not a vendor view has no merged digest, so _vendor_side and
  the entries' preamble refuse it. test_vendor_constants P5-side and P5-pre pin this, with witnesses.
- The model reading binds every turn. Four mutants were run against P2Cases in a scratch worktree, and each went red
  on its own case:
  - codex reading only the last rollout turn;
  - codex reading only the first rollout turn;
  - only the last envelope's stream (codex reroute, gemini init and stats);
  - only the first envelope's stream.
- Claude Code's road is byte for byte. drive.py, checker_for and the claude-code entry and side are not in the diff.
  - checker_view returns a claude-code Design unchanged.
  - A differential probe ran pending_walk.coverage_status and checker_standing on 60 walk folders on the parent tree
    (5d637f8d) and on the head. The folders cover no ledger, a claude-code ledger, an unreadable ledger, another
    harness and a ledger with no agent, crossed with six check.json states and graded or ungraded. The output, with
    checker_constants_sha256(), was byte-identical.
  - The one claude-code difference is a file access: the register-only road now opens each walk's
    driver-ledger.json. test_walk_plan P7's assertion was moved for that, as plan section 6 NIT 4 allows. NIT 1
    covers the one malformed-ledger exception.
- Mutants. Each plan mutant goes red, and the reason was printed for each one:
  - P5: model mismatch admitted (test_vendor_body), a PENDING billing-route variable defaulted and a vendor key
    shadowing CHECKER_CONSTANTS admitted (test_vendor_constants).
  - Walk road: a vendor walk read as current under the Claude-only digest. Its codex and gemini walks under the
    merged digest read stale, and those under the Claude-only digest read current.
  - The pending branch counting on "graded" alone: coverage None three times.
  - RECHECK_HARNESSES left Claude-only: "no recheck road for harness 'codex'".
  - The recheck reading the ledger's pending cross_check: NativeCrossCheckPending.
  - The pending road admitting constant-bound reasons, and leaving the digest unchecked.
  - Also red: the counts read with Claude Code's readers, and the check road dropping the harness.

## Findings

1. MAJOR: the vendor checker cannot be reached in production. drive.py:2595 sets src to None for a vendor
   harness, so drive.py:2664 records transcript null and no transcript.jsonl is written. drive.py:3599 then returns
   readers-disagree before checker_for, and walk_regrade.py:584 refuses the recheck. This is FOR THE REVIEWER point
   1; the section below gives the reproduction and the outline of the fix.
   - Consequence for the study:
     - Every codex and gemini take routes readers-disagree, which is harness-error after the first agent turn.
     - Every vendor walk carries readers-disagree, which is in CONSTANT_BOUND_REASONS, so it never counts.
     - A pending vendor walk can never get the recheck R-9 requires, so it reads "pending: regraded, no checker
       reading under the constants in force" forever.
   - The result fails closed: nothing is weaker than arm C. But none of P1 to P5's vendor readers ever runs on a
     real take, and arms O and G cannot produce one checked take or one counted walk.
   - The fix is a second drive.py edit, which plan section 6 says stops the build `blocked`. It needs glitch-b5's
     ruling and must land before Javier's acceptance commit.

2. MINOR: the drive's scan masks a vendor turn stream or snapshot after its sha256 is bound. The vendor readers then
   hold the take where T-9 says the email is counted. The order is drive.py:2849-2851: records first, then the scan.
   The scan masks MASKABLE kinds (stream and session) in place, and the checker runs after the scan.
   - Readers that compare the bound sha256 with the bytes now on disk:
     - check_take.py:4221 (_vendor_stream);
     - check_take.py:4236 (_vendor_last_snapshot, against the ledger's pre-scan native_snapshots sha256);
     - vendor_record_binding.py bound_items ("native stream digest differs").
   - Reproduced on the test builders' clean codex and gemini takes. An account address was put in turn 1's agent
     text, and the real box/scan_record.scan masked it in turn-1.jsonl. check4_vendor then raises CheckRefused
     ("the codex reach could not be read ([transcript-unreadable] ... native stream digest differs)"), and the same
     for gemini.
   - The tests never meet this. marker_in writes the marker into the parts before the fixture writer hashes them,
     so the bindings are over masked bytes, which the drive's order never produces.
   - The code predates this range (P1 to P3). It reaches production only once finding 1 is fixed, and it constrains
     that fix.
   - Consequence for the study:
     - A vendor take whose records carry the operator's or the vendor account's address is held for a human ruling,
       never counted as account-email 1. Arm C counts the same event and routes it.
     - That is stricter, not weaker. But T-9 says SAME with "masked and counts 1", which is unreachable on the drive
       road, and the table does not say so.
     - If a vendor CLI prints its signed-in account in its stream, every take of that arm is held.
   - Fix, for glitch-b5 to choose with finding 1:
     - (a) bind what the checker reads: write the envelopes and their sha256 after the drive scan, from the masked
       bytes. Also record the scan's per-file sha256_after (box/scan_record's "files" records) in a record the
       vendor readers accept for the ledger-named snapshots;
     - or (b) rule that a masked vendor take is held, and give T-9 that line.
     - Either way, add a drive-road case: an address in a codex stream and a gemini stream, scanned, then checked.

3. MINOR: on the take road, a vendor take's model is bound to the driver's own record, never to the pre-registered
   row. check_take.py:4625 binds to the driver ledger's model_requested. Claude Code's check() binds to the takes
   row's model (check_take.py:1772). Nothing on the vendor take road binds model_requested to the row.
   vendor_take_binding_problems (check_take.py:4550) loads rows[row_index] but checks only task, half and commit.
   This is FOR THE REVIEWER point 2's departure.
   - Reproduced: the test world's row 0 is scope-read/trap, arm A, claude-opus-5-5. A codex or gemini take on that
     row passes model-binding with model_requested and every CLI record set to gpt-6.1-sol, gemini-3.8-flash or
     "synthetic-unregistered-model". The routed reasons are identical to the clean take's in all four cases.
   - Consequence for the study: the cells are published per model. A routing or driver fault that sends an O or G
     row to a model other than its pre-registration passes the vendor check. The same fault on arm C fails
     model-binding. This is silently weaker, and the table has no NOT COMPARABLE line for it. The walk road is fine:
     check_walk also binds model_requested.
   - Fix, red first:
     - on the take road, bind the CLI's records to rows[row_index]["model"], which vendor_take_binding_problems
       already loads, and refuse a model_requested that differs from it. Keep model_requested on the walk road;
     - give the test rig a vendor row, as test_vendor_body's design already makes the draft row a vendor row;
     - add a case (the row on one model, the ledger and the CLI on another) and a witness that restores the
       ledger-only binding.

## FOR THE REVIEWER point 1: the missing host-turn envelopes

Reproduced, statically and live:
- No production code writes a "harness-turn" record. A grep of evals/gap-study-4 outside tests/ finds the string
  only in vendor_record_binding.py, the reader.
- In _take_records, drive.py:2595 sets src to None for any VENDOR_HARNESSES row, so nothing is published as
  transcript.jsonl and the ledger records transcript null (drive.py:2664).
- Live probe: test_pending_codex_walk's codex_road was driven through TakeDriver with the fake box. walk-g1's folder
  holds 21 files and no transcript.jsonl, and its ledger records transcript None.
  - drive.take_checker on that folder, with cross_check [], returned {checker_reasons: [readers-disagree], events
    all 0} without calling design_for.
  - After road.accept() and a committed, verified graded-true regrade, coverage_status read "pending: regraded, no
    checker reading under the constants in force".
  - write_recheck refused: "the committed walk has no transcript.jsonl".
- The R-9 test reaches its recheck only through walk-g2, a hand copy with envelopes written by the test.

Reachable in production without it? No. On the take road, C3 (drive.py:3598-3600) returns before edit A's
checker_for, so check4_vendor, check4_walk_vendor and _vendor_side never run. On the walk road, recheck_doc refuses
first. Every vendor reading in P1 to P5 is exercised only by tests that write the envelopes themselves. The study
cannot check or count one vendor take or walk until the envelopes exist. This is finding 1.

The smallest drive.py change, for vendor harnesses only, with edit A as the precedent:
- In TakeDriver._take_records, inside the existing `if vendor:` branch (drive.py:2604-2606), write transcript.jsonl:
  one schema-1 envelope per ledger turn row, recovery rows included, since bound_items requires len(turns) ==
  len(envelopes). Each envelope is:
  - {"type": "harness-turn", "harness": harness, "session_id": ident["session_id"];
  - "vendor_session_id": the CLI's own id, read from that turn's stream (codex thread.started thread_id, gemini
    init session_id), which bound_items checks again against the native bytes;
  - "n": the ordinal, "sent": the row's sent, "stream": the stream's basename, "sha256": the stream's sha256}.
- Then record "transcript": "transcript.jsonl" for a vendor take. That is the one line at drive.py:2664, as
  `src is not None or vendor`.
- Nothing on the claude-code branch moves: src, publish_transcript, the cost reader and the ledger keys are only
  read under `not vendor` or `cc`.
- Finding 2 decides when the sha256 is taken. Written where the ledger binds the snapshots (before the scan), any
  masked stream refuses. The coherent version writes or rebinds the envelopes from the scanned bytes. The envelope
  file is TAKE_FILE_KINDS "transcript", so TakeRepo's commit scan still scans it.
- The schema is vendor_record_binding.py's. Neither that file nor transcript_view.py changes.

Tests that would prove it:
- Vendor road:
  - A codex and a gemini take driven through TakeDriver with the fake boxes (test_pending_codex_walk's CodexBox and
    test_pending_walk's gemini road) get a transcript.jsonl that vendor_record_binding.bound_items reads without
    ViewError, and their ledger names it.
  - drive.take_checker then reaches checker_for and the vendor entry: the fake reader is called, and C3's
    readers-disagree is not added.
  - R-9's test moves from walk-g2 to the road's own walk-g1.
- Claude Code byte for byte:
  - A claude-code take driven through test_drive_loop's or test_box_integration's road gives byte-identical
    driver-ledger.json, transcript.jsonl and take-folder listing before and after. This is the P0 test's "equal
    before and after" shape.
  - A check_vendor_sources-style line names the drive.py hunk and asserts it lies inside the vendor branch.
- Mutants:
  - the writer gated off: C3 returns readers-disagree again;
  - the writer run for claude-code: the claude-code golden goes red;
  - an envelope's sent taken from somewhere other than the ledger row: readers-disagree;
  - an envelope's sha256 of another stream: transcript-unreadable;
  - the drive-road masked-address case from finding 2.
- drive.py is in READER_SOURCES and CODEX_SOURCES. The edit must be ruled by glitch-b5 and land before Javier's
  acceptance commit.

## The other FOR THE REVIEWER points

2. A finding: finding 3. The test rigs' Claude Code rows are a test-rig limit, not a reason for the production
   reading to trust the driver ledger. check() binds the row on the take road, and the rig can carry a vendor row.
3. Acceptable, as round 13 ruling (4). F1 and F2 are read only by the byte compare and the P1 view, never by a check
   that reads an environment record. The test takes carry environment.json and bind it in their ledgers.
4. Acceptable, with NIT 2. Every block value comes from its code: test_vendor_constants P5-block re-derives each one.
   A settled row's state moves the digest. The billing-route PENDING is a routed VENDOR_PENDING_ROWS refusal, never
   a held block value, and P5-view binds that.
5. Acceptable. pending_standing applies checker_standing's rules to the latest recheck: the vocabulary, no
   constant-bound reason, the digest in force, a valid nudge count and Agent summary, and latest_recheck's register
   binding. Two R-9 witnesses pin it. checker_standing's claude-code branch changes only in `now`, which
   constants_in_force returns unchanged for claude-code (see the differential probe).
6. Acceptable. Plan section 6 fixes the side contract. nested_cli_calls is the same sum over vendor_shell_commands
   that the drive writes into session-store.json, and P4 already re-derives that count.
7. Acceptable. The two TheSweep failures reproduce here as root-user failures, outside the range.

## NITs

1. evals/gap-study-4/pending_walk.py:281: a driver-ledger.json whose agent.harness is a list raises TypeError
   (unhashable) in constants_in_force, through coverage_status and checker_standing. Before P5, checker_standing
   never read the ledger. Only a malformed ledger reaches it, and it fails loud, but walk_harness could return None
   for a value that is not a str.
2. evals/gap-study-4/check_take.py:5139: each VENDOR_PENDING_ROWS row enters the block as "<reason>: <state>" only.
   A SAME row's reader or fixture, or a NOT COMPARABLE row's ruling or reader, can move without moving the merged
   digest. That is no weaker than arm C, whose digest carries no reader either. But "any row moves the digest" holds
   only for reason and state. Encoding the whole row would close it.
3. evals/gap-study-4/check_take.py:4645-4656: gemini's reading takes every stats.models key as a served model. The
   shape is documented-only. When the recorded re-test (plan section 8) settles T-15 for G, check that the CLI lists
   no helper model there; if it does, every gemini take reads model-binding.
4. Two added lines run past the file width: evals/gap-study-4/walk_regrade.py:46 (146 characters) and
   evals/gap-study-4/check_take.py:5168 (122 characters).
