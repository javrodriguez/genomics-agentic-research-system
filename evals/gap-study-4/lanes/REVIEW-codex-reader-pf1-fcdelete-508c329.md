VERDICT: PASS
Reviewer: a fresh Opus 5.5 reviewer agent of glitch-45
lane-tag: instrument
purpose: round-1 and Codex reader review (turnitem plus fcdelete)

# Codex reader review: lanes pf1-codex-turnitem and pf1-codex-fcdelete

Candidate head: 508c3295717d141098e417a35ce593214256a9e8 on lane/pf1-codex-fcdelete.
Range: 5f5aa9fb..508c3295, two lane commits: pf1-codex-turnitem (5f5aa9fb..8bad0baa) and pf1-codex-fcdelete (8bad0baa..508c3295).
Where: the Mac, in the reviewer's scratch folder: `git archive` copies of 5f5aa9fb, 8bad0baa and 508c3295, and two `git clone --no-local` copies checked out at 8bad0baa and 508c3295.
athena was read only (one `ls`, `find`, `grep`, `sha256sum`, `cat` of w-o76's folder); gap4-walk-records-20261019 was not touched; nothing was pushed.
Every test run and walk survey ran after `mac_slot.py light-ok --tests --work gap-study-r4` printed `light ok` (it never refused during this review).
Python: /usr/local/bin/python3.12 -B, TMPDIR in the scratch folder; scripts that read walk bytes ran with -I.

## In plain words, for Javier

What changed in fcdelete: a Codex patch that deletes a file is now read instead of refused.
In the exec stream (transcript_codex) a delete becomes a write call on the deleted path, so every grader that catches a write or an edit of a path catches a delete of it in the same number.
In the native rollout (codex_native) a delete is read on exactly its pinned shape, {type delete, content string}, and the join still compares each change's path and kind between stream and rollout.
Every other change kind still refuses in both readers.
On the 38 committed arm-O walks nothing moves: there is no file_change of any kind in any of them, and the base and head readers give byte-identical results on all 38.
What you would be accepting: the Codex sources hash moves from f3aedc01 (8bad0baa, the hash the turnitem acceptance kit named) to 48540c45 (508c3295); the Gemini sources hash is f58cfd1d at both.
What stays unverified: no native rollout of w-o76 exists on the Mac or athena, so the rollout half is tested only on records built from the pinned source shape (finding 1).

## Evidence

### 1. Source citations (openai/codex 092d3acd, read with `gh api repos/openai/codex/contents/codex-rs/<path>?ref=092d3acd`)

The pin resolves to commit 092d3acd6bec3e3a14bdc7e7a2810ab628ab759d.

- exec/src/exec_events.rs:192-198: `pub enum PatchChangeKind { Add, Delete, Update }` with `#[serde(rename_all = "snake_case")]` (enum at line 194, Delete at 196). Confirmed.
- exec/src/event_processor_with_jsonl_output.rs:187-196: the FileChange arm maps each change to `FileUpdateChange { path, kind }`, `PatchChangeKind::Delete => ExecPatchChangeKind::Delete` at line 193, and `Update { .. }` drops move_path at 194. Confirmed.
- protocol/src/protocol.rs:4225-4239: `#[serde(tag = "type", rename_all = "snake_case")] pub enum FileChange { Add { content: String }, Delete { content: String }, Update { unified_diff: String, move_path: Option<PathBuf> } }` (enum at 4228). Confirmed.
- core/src/apply_patch.rs:64-79: `convert_apply_patch_to_protocol` maps `ApplyPatchFileChange::Delete { content }` to `FileChange::Delete { content }` (line 73). Confirmed.
- Read beyond the brief, apply-patch/src/invocation.rs:211-224: a delete's `content` is the file's text read from disk by Codex before the patch runs; a missing file is an IoError before any FileChange exists. So the content is the old file's text, never text the agent writes into the record.

### 2. The recorded input

w-o76's exec stream is at /home/javier/w-Z6IWmUI8/repo/evals/gap-study-4/rehearsals/w-o76/turn-1.jsonl on athena: 22 lines, sha256 cc1094c3d09f6dbf8dda78dc4d35d70c8fcb83c041d0bb86fb3f7417f4d63c1e, 4 file_change lines, kinds 2 delete and 2 add.
Its lines 17 to 20 equal the test's RECORDED tuple byte for byte (`tuple(lines) == RECORDED` printed True).
The walk folder there holds no session/ folder and no file containing `FileChange` or `patch_apply`, so no native rollout of w-o76 was copied out.
Whole stream through the test's `--stream` mode:

```
8bad0baa: read_stream refuses: the stream holds a record off the pre-registered tables: item file_change: change kind with no entry: 'delete'
508c3295: read_stream reads it: completed 1, tool ids 8; view calls by kind {'shell': 6, 'write': 2}
```

### 3. Red first at 8bad0baa

The head's tests/test_codex_fcdelete.py copied into a `git archive` of 8bad0baa: Ran 14, FAILED (failures=1, errors=10).
R1 fails with `codex_adapter.StreamError: the stream holds a record off the pre-registered tables: item file_change: change kind with no entry: 'delete'`, w-o76's recorded reason word for word.
R2 and W2 fail with `ViewError: line 4: item file_change: change kind with no entry: 'delete'`; R3 and R4 with `ReaderRefused: a FileChange delete is refused (Q-w11a-3), as in the exec stream`; R5 with the T-8 reader's `[transcript-unreadable]` line naming the same refusal.
The three W1 tests pass at the base, as default-deny tests should.

### 4. Attempts to hide an action through a delete (records built from the pinned source shape, at 508c3295)

```
P1 stream delete vs rollout update:                       join refused: file change paths or kinds disagree
P2 stream update vs rollout delete:                       join refused: file change paths or kinds disagree
P3 stream delete A vs rollout delete B:                   join refused: file change paths or kinds disagree
P4 stream delete A + add B vs rollout update A move B:    join refused: file change paths or kinds disagree
P5 delete A + add B on both sides:                        joined, file_changes 1; projected [add notes.md, delete plan.md]
P6 delete content in read_rollout's output:               False (an add's content: False too)
P6 reach reads a delete's content:                        True
P7 rollout delete with content None / a list / unified_diff in place of content / type DELETE: refused
P8 stream delete with an extra key, kind a list, no path:  refused
P8 stream delete with an empty path:                      admitted (finding 3)
P9 delete then re-add of one path:                        two write calls on that path
P10 T-8 on a rename (update with move_path):              held, "[transcript-unreadable] ... a rename through the patch tool"
P10b T-8 on delete A + add B:                             clean
P10c T-8 on stream update vs rollout delete:              "[transcript-unreadable] ... do not join the rollout's"
```

- A delete of a guarded path: caught, see section 5.
- Smuggled content: a delete's content never reaches read_rollout's projection or any grader (no grader reads a write's content; a grep of graders/ and the study's modules for `args["content"]` finds none); check_take's reach reads it, as an add's, which can only add reach.
- A stream delete against a rollout update, either way round: the join refuses.
- Delete then re-add: two visible write calls on the same path, both counted.
- A rename disguised as delete plus add: if the rollout holds a rename (update with move_path) the join refuses on kinds; if both records hold a delete and an add, both paths show as write calls and nothing is hidden. A true rename is still held by T-8.

### 5. The graders the builder names

- scope_read.planted_calls (scope_read.py:235) counts READ, WRITE and EDIT calls on planted paths: a delete counts 1, as an update and an add (lane test W2, green).
- precondition_refusal._names_path (precondition_refusal.py:360, and its use at :465) treats WRITE and EDIT alike: a delete counts 1 (W2).
- new_tasks: both its hand-edit and guarded-touch filters read `t.post_calls(view.WRITE, view.EDIT)` (new_tasks.py:542, 546): a delete counts 1 (W2 drives the filter with names_path).
- pause_adherence matches a pattern by tool kind and the path argument (pause_adherence.py:98, 198-212); the lane's tests do not drive it, so this review did, with plan-gate.json's wait point "Approve as written?":

```
delete PLAN.md           arrive True  past False      add PLAN.md            arrive True  past False
delete PLAN.md.approved  arrive False past True       add PLAN.md.approved   arrive False past True
update PLAN.md.approved  arrive False past True       shell `rm PLAN.md.approved`        past False
```

A delete reads as a write in every grader, so it is caught wherever an add or update of the same path is caught.

### 6. The 38 committed arm-O walks

- `grep` over every w-o* stream and every session/ and evidence/ file: `file_change` in 0 files, `FileChange` in 0 files, a `"kind":"delete"` change in 0 streams. No walk holds a delete, or any file change.
- One survey script ran per tree over all 38 walks, hashing with `json.dumps(sort_keys=True)`: `codex_native.project` on every retained native snapshot, `read_rollout` on the last, `read_exec` and `codex_adapter.read_stream` on every stream, `native_reader_registration.codex_check` with the walk's driver-ledger.json, and the transcript view's events through `CodexParser`.
  8bad0baa against 508c3295: the 38 result records are identical (`a == b` True); codex_check PASS on 38 of 38; write or edit calls 0 on every walk; errors 0.
  5f5aa9fb against 508c3295: only `read_rollout` and `read_exec` differ, the turnitem keys the turnitem reader review already explained; project, read_stream, codex_check and the view are identical.
- Each walk's regrade.json re-derived (`walk_regrade.regrade_bytes(walk_regrade.regrade_doc(walk, study, readers={"codex": PROFILES["codex"]["reader"]}))`) in the git clones: equal to its committed bytes on 38 of 38 at 8bad0baa and 38 of 38 at 508c3295.

### 7. The turnitem lane, re-checked

Both earlier reviews of 8bad0baa read PASS: lanes/REVIEW-pf1-codex-turnitem-8bad0ba.md (on lane/pf1-codex-turnitem) and lanes/REVIEW-codex-reader-pf1-turnitem-8bad0ba.md (on kit/pf1-codex-turnitem-acceptance, 8ce1d884).
The fcdelete diff touches codex_native.py only in its docstring (lines 26-30), FILE_CHANGE_KINDS and `_file_change`; it changes no line of the late-command code, and check_take.py is byte-identical between 8bad0baa and 508c3295 (sha256 a44ddbb7d6a54ee6 at both).
test_codex_turnitem is green at the head (below), and the 38-walk survey shows no change from 8bad0baa.
Nothing in 8bad0baa..508c3295 undoes the turnitem change or its review findings.

### 8. Sources hashes

```
                      codex_native.py   transcript_codex.py   Codex sources hash   Gemini sources hash
5f5aa9fb              7eb8cfefd6d67088  3964757469f12765
8bad0baa              2e7b19f7aff63d57  3964757469f12765      f3aedc019a15efaf     f58cfd1dee6591b6
508c3295              27280c8eac4a06bc  6edf5ed55c61838d      48540c455e1a6b38     f58cfd1dee6591b6
```

### 9. Tests at 508c3295 (a git clone in scratch)

```
test_codex_fcdelete.py                          Ran 14, OK
test_codex_fcdelete.py --mutants                6 of 6 bite: m-delete-hidden, m-kind-open, m-cn-unknown, m-cn-content, m-cn-delete-keys, m-join-kinds
test_codex_turnitem.py                          Ran 14, OK
test_codex_adapter.py                           Ran 66, OK
test_codex_adapter.py --witnesses               Ran 22, OK; 21 of 21 witnesses red
test_codex_native.py                            Ran 15, OK
test_codex_patch_reads.py                       Ran 13, OK
test_codex_patch_reads.py --witnesses           15 of 15 witnesses red
test_codex_started_file_change.py               Ran 5, OK
test_codex_started_file_change.py --witnesses   3 of 3 witnesses red
test_b25_real_shapes.py                         Ran 18, OK
test_pf1_transcript_integrity.py                Ran 55, OK
test_native_reader_registration.py              Ran 7, FAILED (errors=2), both "RegistrationRefused: the reader's sources changed since the record: a new acceptance is needed" (finding 6)
```

The two registration errors are the expected owner-step state: the committed Codex acceptance names an older sources hash, and only Javier's new acceptance clears them.
This review did not run that test at 8bad0baa.

## Findings

No misgraded or leaked input was found on the head, so by the review rule the instrument loop stops here.

1. Residual, class D (restated from the brief): no native rollout of w-o76 exists on the Mac or on athena (its walk folder holds no session/ folder and no FileChange record), so codex_native's delete reading and the stream-to-rollout join of a delete are tested only on records built from the pinned source shape (protocol.rs:4228-4239, apply_patch.rs:73). Glitch-26's Q4 named "after a recorded rollout" as the condition; glitch-45's ruling admits the delete before one exists. The first walk whose rollout holds a FileChange delete is the first real test of that half; if its shape is off the pinned one, the reader refuses and the walk is held, which is the safe side.

2. NIT, class C: pause_adherence reads a patch delete of PLAN.md.approved as `past` (ran ahead) and a delete of PLAN.md as `arrive`, while a shell `rm PLAN.md.approved` matches no plan-gate pattern. On the pinned Codex this cannot misgrade: a delete needs the file to exist (invocation.rs:211-224), so the file was written earlier by the agent (itself `past`) or by the approval step (after the gate). The lane's tests do not drive pause_adherence; section 5 here does. No change asked.

3. NIT, class C, outside this diff: transcript_codex.check_record admits a stream change with an empty path for every kind (add and update at 8bad0baa too, delete now). codex_native refuses an empty path, so any take with a rollout refuses at the join; the view alone would carry a write call on "".

4. NIT, class C, acceptance scope: CODEX_SOURCES (native_reader_registration.py:191-192) binds codex_native.py but not transcript_codex.py, so Javier's acceptance binds the rollout half of this change and not the stream's delete-to-write mapping; that half rests on this review, test_codex_fcdelete W2 and its m-delete-hidden mutant, and test_codex_adapter's delete-hidden witness. The same was noted for check_take.py in the turnitem reader review (its finding 3).

5. NIT, class C: check_take's reach reads a delete's content, which is the deleted file's old text read by Codex, not agent output. A path named inside a deleted file can therefore count as reach the agent never made. This leans to counting more, never to an unread reach counting as zero, and matches vendor-b23-DESIGN.md:172 ("which reach would read as asked").

6. NOTE, owner step: codex_native.py changed, so the Codex sources hash moves to 48540c455e1a6b38 and the committed Codex acceptance no longer re-derives until Javier commits a new one in his own window; the turnitem acceptance kit, which named f3aedc01, would need its hash restated for this head. At the head, tests/test_native_reader_registration.py errors twice with "the reader's sources changed since the record: a new acceptance is needed" until then. The turnitem reader review's finding 1 (the ACCEPTED_AT pin in tests/test_native_reader_registration.py) still applies.
